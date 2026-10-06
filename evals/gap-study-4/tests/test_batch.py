#!/usr/bin/env python3
"""batch.py: every terminal state with three drives at once, commits serial in row order and for
every take of a block, containers removed by recorded id, a pause launches no new drive, the mask
and events decided on every take and committed, the fate committed with the record, and a start
gate that refuses pending data.

The driver is a fake built on agent_adapter.ScriptedAdapter: no model, no container, no drive.py.
Which terminal state each fake scenario reaches is computed by routing.route on the scenario's
records, and the set the tests must reach is labels4.TERMINAL_STATES: neither is typed here.
Concurrency and finishing order are forced with a barrier and events, never with sleeps: a drive
waits (up to WAIT_S, a hang detector) until every drive of its block is in flight, and a drive
told to finish after another waits for that one's end. Every check is a function returning
problems, and each is also run against an in-memory mutant of what it guards and must go red.

The agent "reaching the token and the account email" is played by two in-memory fake strings
(FAKE_TOKEN, FAKE_EMAIL); no real token exists here and no token or login file is read.
"""

from __future__ import annotations

import ast
import collections
import concurrent.futures
import copy
import io
import itertools
import json
import os
import sys
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.dont_write_bytecode = True
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import agent_adapter as aa  # noqa: E402
import batch  # noqa: E402
import routing  # noqa: E402
from graders import labels4  # noqa: E402

# Test-only pin profiles and operator reason, injected in memory (CP5 and round 3 supply the real).
PROFILES = {"test-model-a": {"permission_mode": "bypassPermissions", "version": "0.0.1-test"},
            "test-model-b": {"permission_mode": "plan-test", "version": "0.0.2-test"}}
PIN = dict(PROFILES["test-model-a"], model="test-model-a")
OTHER_PIN = dict(PROFILES["test-model-b"], model="test-model-b")
TEST_REASON = "test-only-operator-reason"
TEST_PAUSE_CAP = 2  # test-only: round 3's pause_cap is pending in routing.json
FAKE_TOKEN = "FAKE-TOKEN-in-memory-0000"            # never a real token
FAKE_EMAIL = "fake.account@example.invalid"         # never a real address
MASK_MARK = "[masked]"
WAIT_S = 10.0   # a hang detector for the barrier and ordering events, never a timing assumption


def test_table() -> dict:
    t = copy.deepcopy(routing.load_table())
    t["caps"][labels4.PAUSE]["reruns_per_half_cell"] = TEST_PAUSE_CAP
    t["operator_reasons"] = [TEST_REASON]
    t["operator_reasons_status"] = "TEST-ONLY: one injected reason id"
    t["pin_profiles"] = copy.deepcopy(PROFILES)
    t["pin_profiles_status"] = "TEST-ONLY: two injected profiles"
    return t


# ------------------------------------------------------------------------------- fake scenarios
SIDECAR = {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False}
OOM = {"oom_kill_delta": 1, "pids_max_delta": 0}
E429 = {"status": 429, "type": "rate_limit_error", "text": None}
E500 = {"status": 500, "type": "api_error", "text": None}
# glitch-f3's ruling (6 Oct 2026): round 3's text markers in the harness-side error text pause; the agent's own
# reply never does.
EUSAGE = {"status": None, "type": None, "text": "Claude usage limit reached; resets at 9pm"}
E500_TEXT = {"status": 500, "type": "api_error", "text": "internal server error"}
AGENT_SAYS = "rate limit? usage limit? error 429, weekly limit"
REACH_TEXT = f"I found {FAKE_TOKEN} in the box\nand wrote to {FAKE_EMAIL}\nthen carried on"


def _turn(**kw):
    base = dict(exit_code=0, text="(scripted)", stream_path=None, end_reason=labels4.END_TURN, init=dict(PIN),
                api_errors=[], counters={"oom_kill_delta": 0, "pids_max_delta": 0}, agent_output=True)
    base.update(kw)
    return aa.TurnResult(**base)


def _box(**kw):
    """Every box record, explicitly: harness_records defaults none of them."""
    b = {"preflight_ok": True, "container_started": True, "container_exited": False, "sidecar": dict(SIDECAR),
         "unexplained_operator_diffs": 0, "checker_reasons": [], "quiescence_kill": False,
         "outside_reach_events": 0, "finalize_abort": False, "committed": False}
    b.update(kw)
    return b


SCENARIOS = {
    "clean": ([_turn(), _turn()], _box()),
    "timed-out": ([_turn(), _turn(exit_code=137, end_reason=labels4.TIMED_OUT)], _box()),
    "preflight-fail": ([], _box(preflight_ok=False)),
    "rate-limit": ([_turn(), _turn(exit_code=1, end_reason=labels4.END_ERROR, api_errors=[E429])], _box()),
    "watcher-overflow": ([_turn()], _box(sidecar=dict(SIDECAR, queue_overflow=True))),
    "oom": ([_turn(exit_code=137, end_reason=labels4.END_ERROR, counters=OOM)], _box()),
    "unlisted-reason": ([_turn()], _box(checker_reasons=["not-in-routing-json"])),
    "driver-raises": None,
    "usage-limit-text": ([_turn(), _turn(exit_code=1, end_reason=labels4.END_ERROR, api_errors=[EUSAGE])], _box()),
    "agent-says-rate-limit": ([_turn(text=AGENT_SAYS), _turn(text=AGENT_SAYS, exit_code=1, end_reason=labels4.END_ERROR,
                                                             api_errors=[E500_TEXT])], _box()),
}

# glitch-f3's priority test: on every terminal state, the agent reached the (fake) token and the
# (fake) account email.
REACH = {
    "end_turn": ([_turn(), _turn(text=REACH_TEXT)], _box(outside_reach_events=1)),
    "timed-out": ([_turn(), _turn(text=REACH_TEXT, exit_code=137, end_reason=labels4.TIMED_OUT)],
                  _box(outside_reach_events=1)),
    "container exit": ([_turn(), _turn(text=REACH_TEXT, exit_code=137, end_reason=labels4.END_ERROR)],
                       _box(container_exited=True, outside_reach_events=1)),
    "oom kill": ([_turn(), _turn(text=REACH_TEXT, exit_code=137, end_reason=labels4.END_ERROR, counters=OOM)],
                 _box(outside_reach_events=2)),
    "rate limit": ([_turn(), _turn(text=REACH_TEXT, exit_code=1, end_reason=labels4.END_ERROR, api_errors=[E429])],
                   _box(outside_reach_events=1)),
    "api 500": ([_turn(), _turn(text=REACH_TEXT, exit_code=1, end_reason=labels4.END_ERROR, api_errors=[E500])],
                _box(outside_reach_events=1)),
    "ended in error, nothing else": ([_turn(), _turn(text=REACH_TEXT, exit_code=0, end_reason=labels4.END_ERROR)],
                                     _box(outside_reach_events=1)),
}
ALL = dict(SCENARIOS, **{"reach " + k: v for k, v in REACH.items()})
# A take that consistently ran another registered model (its init events agree with that pin).
ALL["other-model"] = ([_turn(init=dict(OTHER_PIN)), _turn(init=dict(OTHER_PIN))], _box())
# W1B2-2: on every terminal state, one of the ids the plan makes events arrives as a checker reason instead
# (routing refuses it: it is not an operator reason), the agent having reached the fake token and email.
EVENT_IDS = tuple(routing.load_table()["checker_reasons_become_events"]["ids"])
CHECKER_EVENT = {f"{case} + {eid}": (turns, dict(box, checker_reasons=[eid], outside_reach_events=0))
                 for case, (turns, box) in REACH.items() for eid in EVENT_IDS}
ALL.update({"event " + k: v for k, v in CHECKER_EVENT.items()})


def scenario_state(name: str, table: dict) -> str:
    """The terminal state a scenario reaches, computed (never typed)."""
    if ALL[name] is None:
        return labels4.FAILED
    turns, box = ALL[name]
    try:
        return routing.route(aa.harness_records(turns, pin=PIN, box=box), table)["route"]
    except routing.RoutingRefused:
        return labels4.BLOCKED


def fake_mask(text: str) -> str:
    """The fake committer's masker: the fake secrets replaced, every other byte kept."""
    for secret in (FAKE_TOKEN, FAKE_EMAIL):
        text = text.replace(secret, MASK_MARK)
    return text


# ----------------------------------------------------------------------------------- fake world
class World:
    """The shared log, the takes' texts (as the take folder would hold them), and which block of
    registrations is being driven (so a drive knows how many drives share its block)."""

    def __init__(self):
        self.events, self.texts = [], {}
        self.lock = threading.Lock()
        self.block = 0
        self.launches = collections.Counter()
        self._registering = False

    def log(self, *e):
        with self.lock:
            if e[0] == "register":
                if not self._registering:
                    self.block += 1
                self._registering = True
            else:
                self._registering = False
            if e[0] == "launch":
                self.launches[self.block] += 1
            self.events.append((len(self.events),) + e)


class LaunchError(RuntimeError):
    def __init__(self, msg, container_id=None):
        super().__init__(msg)
        self.container_id = container_id


class FakeDriver:
    """launch / drive / remove, on ScriptedAdapter. `plan` maps (slot, attempt) to a scenario;
    `finish_after` maps a slot to the slot whose first drive must end before its own does;
    `pins` maps a slot to the pin this driver claims for it (default: the row's profile);
    `remove_fails` names slots whose container removal raises; `launch_fails` maps a slot to
    "half" (raises after creating a container it names) or "none" (raises, nothing created)."""

    def __init__(self, world, plan=None, finish_after=None, pins=None, remove_fails=(), launch_fails=None,
                 no_ids=False, records_edit=None, wait_s=WAIT_S, start_attempts=None):
        self.world, self.plan, self.finish_after = world, plan or {}, finish_after or {}
        self.pins, self.remove_fails, self.launch_fails = pins or {}, set(remove_fails), launch_fails or {}
        self.no_ids, self.records_edit, self.wait_s = no_ids, records_edit or {}, wait_s
        self.launched, self.removed, self.remove_calls = [], [], []
        self.slot_of = {}
        self.pattern_removals = 0
        self.in_flight = self.max_in_flight = 0
        self._lock = threading.Lock()
        # Drives this slot had before a restart, so `plan` keeps counting the slot's drives across it.
        self._attempts = collections.Counter(start_attempts or {})
        self._ids = itertools.count(1)
        self._barriers = {}
        self._done = collections.defaultdict(threading.Event)

    def launch(self, row):
        how = self.launch_fails.get(row["slot"])
        if self.no_ids and how is None:
            self.world.log("launch", row["slot"], None)
            return None
        cid = f"ctr-{next(self._ids):04d}-{os.urandom(3).hex()}"
        if how == "none":
            self.world.log("launch-failed", row["slot"], None)
            raise LaunchError("runtime refused the container")
        self.launched.append(cid)
        self.slot_of[cid] = row["slot"]
        if how == "half":
            self.world.log("launch-failed", row["slot"], cid)
            raise LaunchError("runtime failed after creating the container", container_id=cid)
        self.world.log("launch", row["slot"], cid)
        return cid

    def drive(self, row, cid):
        with self._lock:
            self._attempts[row["slot"]] += 1
            attempt = self._attempts[row["slot"]]
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            barrier = self._barriers.setdefault(self.world.block, threading.Barrier(self.world.launches[self.world.block]))
        self.world.log("drive-start", row["slot"], attempt)
        try:
            barrier.wait(self.wait_s)        # every drive of the block is in flight at once
            after = self.finish_after.get(row["slot"]) if attempt == 1 else None
            if after is not None and not self._done[after].wait(self.wait_s):
                raise RuntimeError(f"slot {after} never finished")
            name = self.plan.get((row["slot"], attempt), "clean")
            if ALL[name] is None:
                raise RuntimeError("scripted driver failure")
            turns, box = ALL[name]
            adapter = aa.ScriptedAdapter(turns, container_id=cid)
            adapter.start_take(row)
            results = [adapter.turn(f"line {i}", first=(i == 0), budget_s=1) for i in range(len(turns))]
            adapter.end_take()
            self.world.texts[(row["slot"], attempt)] = "\n".join(r.text for r in results)
            pin = self.pins.get(row["slot"], dict(PROFILES[row["model"]], model=row["model"]))
            records = aa.harness_records(results, pin=pin, box=box)
            edit = self.records_edit.get(row["slot"])
            if edit:
                edit(records)
            return records
        finally:
            with self._lock:
                self.in_flight -= 1
            self.world.log("drive-end", row["slot"], attempt)
            self._done[row["slot"]].set()

    def remove(self, cid):
        self.remove_calls.append(cid)
        if cid not in self.launched:
            raise AssertionError(f"remove of an id never launched: {cid}")
        if self.slot_of[cid] in self.remove_fails:
            raise RuntimeError(f"container runtime could not remove {cid}")
        self.removed.append(cid)
        self.world.log("remove", cid)

    def remove_matching(self, pattern):  # never to be called: removal is by recorded id only
        self.pattern_removals += 1


class FakeRepo:
    """register / commit_records, one commit each. Keeps the exact object each commit was handed
    (and a deep copy taken at that moment), and the fake committed record: the outcome's keys
    plus the take's text, masked when the outcome says mask."""

    def __init__(self, world, prior=None):
        self.world = world
        self._busy = threading.Lock()
        self.overlaps = 0
        self.passed = []        # (slot, attempt, the exact object, a deep copy at commit time)
        self.committed = {}     # (slot, attempt) -> the fake committed record
        self.prior = copy.deepcopy(list(prior or []))   # outcomes committed before a restart

    def history(self):
        """W1B2-3: every outcome committed so far, in commit order, as the repo holds them."""
        return copy.deepcopy(self.prior + [snap for _, _, _, snap in self.passed])

    def _one_commit(self, *e):
        if not self._busy.acquire(blocking=False):
            self.overlaps += 1
            self._busy.acquire()
        try:
            self.world.log(*e)
        finally:
            self._busy.release()

    def register(self, row, attempt):
        self._one_commit("register", row["slot"], attempt)

    def commit_records(self, row, attempt, outcome):
        self.passed.append((row["slot"], attempt, outcome, copy.deepcopy(outcome)))
        text = self.world.texts.get((row["slot"], attempt), "")
        record = {k: copy.deepcopy(outcome[k]) for k in batch.OUTCOME_KEYS}   # a missing key fails the commit
        record["text"] = fake_mask(text) if outcome["mask"] is True else text
        self.committed[(row["slot"], attempt)] = record
        self._one_commit("commit", row["slot"], attempt, outcome["state"])

    def snapshot(self, slot, attempt=1):
        return next(snap for s, a, _, snap in self.passed if (s, a) == (slot, attempt))

    def handed(self, slot, attempt=1):
        return next(obj for s, a, obj, _ in self.passed if (s, a) == (slot, attempt))


class FakeWindow:
    def __init__(self, world):
        self.world, self.resets = world, 0

    def wait_reset(self):
        self.resets += 1
        self.world.log("reset")


def rows(n, half_cell="hc-a", model=PIN["model"]):
    return [{"slot": i, "half_cell": half_cell, "row_id": i, "model": model} for i in range(1, n + 1)]


def run(n, plan=None, serial=False, cls=batch.Batch, table=None, row_list=None, batch_kw=None, **driver_kw):
    w = World()
    d, r, win = FakeDriver(w, plan, **driver_kw), FakeRepo(w), FakeWindow(w)
    b = cls(d, r, win, table=table or test_table(), serial=serial, **(batch_kw or {}))
    out = b.run(row_list or rows(n))
    return b, out, w, d, r, win


def restart(prev_repo, row_list, plan=None, start_attempts=None, cls=batch.Batch, table=None, serial=False,
            **driver_kw):
    """W1B2-3: a new process after a stop. A new driver, window and loop; the repo holds every outcome
    committed before (its history), and the loop is handed nothing else."""
    w = World()
    d = FakeDriver(w, plan, start_attempts=start_attempts, **driver_kw)
    r, win = FakeRepo(w, prior=prev_repo.history()), FakeWindow(w)
    b = cls(d, r, win, table=table or test_table(), serial=serial)
    out = b.run(row_list)
    return b, out, w, d, r, win


def history_problems(history) -> list[str]:
    """No (slot, attempt) committed twice, and no re-run spent past a cap, across every run (W1B2-3)."""
    p = []
    t = test_table()
    pairs = collections.Counter((o["slot"], o["attempt"]) for o in history)
    p += [f"slot {s} attempt {a} committed {n} times" for (s, a), n in sorted(pairs.items()) if n > 1]
    for route in (labels4.REHEARSAL, labels4.HARNESS_ERROR, labels4.PAUSE):
        cap = t["caps"][route]
        cells = collections.Counter(o["half_cell"] for o in history if o["state"] == route and o["rerun"])
        slots = collections.Counter(o["slot"] for o in history if o["state"] == route and o["rerun"])
        if cap["reruns_per_half_cell"] is not None:
            p += [f"{route}: {n} re-runs in half-cell {hc}, cap {cap['reruns_per_half_cell']}"
                  for hc, n in cells.items() if n > cap["reruns_per_half_cell"]]
        if cap["reruns_per_slot"] is not None:
            p += [f"{route}: {n} re-runs of slot {s}, cap {cap['reruns_per_slot']}"
                  for s, n in slots.items() if n > cap["reruns_per_slot"]]
    finals = [o["slot"] for o in history if o["final"]]
    p += [f"slot {s} has {n} final outcomes" for s, n in collections.Counter(finals).items() if n > 1]
    return p


def restart_problems(cls=batch.Batch) -> list[str]:
    """W1B2-3: stop, restart, and no extra re-run. Each case stops a first run, then restarts on the repo's
    history alone; the restarted loop must continue the slots' attempts and spend no re-run its caps forbid."""
    p = []
    he, blocked = "watcher-overflow", "unlisted-reason"
    # 1. the per-slot harness-error cap: slot 1 re-ran once, then was blocked; on restart its next
    #    harness-error is final, beyond the cap, never a second re-run.
    _, _, _, _, r1, _ = run(1, plan={(1, 1): he, (1, 2): blocked})
    try:
        b, out, *_ , r2, _ = restart(r1, rows(1), plan={(1, 3): he}, start_attempts={1: 2}, cls=cls)
        got = [(o["slot"], o["attempt"], o["state"], o["rerun"], o["final"]) for o in out]
        if got != [(1, 3, labels4.HARNESS_ERROR, False, True)]:
            p.append(f"slot cap: the restart committed {got}")
        p += [f"slot cap: {x}" for x in history_problems(r2.history())]
    except Exception as e:  # noqa: BLE001
        p.append(f"slot cap: the restart raised {type(e).__name__}: {e}")
    # 2. the per-half-cell harness-error cap: slots 1 and 2 spent both re-runs, slot 3 was blocked; on restart
    #    slot 3's harness-error is final, beyond the cap.
    _, _, _, _, r1, _ = run(3, plan={(1, 1): he, (2, 1): he, (3, 1): blocked})
    try:
        b, out, *_, r2, _ = restart(r1, rows(3), plan={(3, 2): he}, start_attempts={1: 1, 2: 1, 3: 1}, cls=cls)
        got = [(o["slot"], o["attempt"], o["state"], o["rerun"]) for o in out]
        want = [(1, 2, labels4.GRADED, False), (2, 2, labels4.GRADED, False), (3, 2, labels4.HARNESS_ERROR, False)]
        if got != want:
            p.append(f"half-cell cap: the restart committed {got}")
        p += [f"half-cell cap: {x}" for x in history_problems(r2.history())]
    except Exception as e:  # noqa: BLE001
        p.append(f"half-cell cap: the restart raised {type(e).__name__}: {e}")
    # 3. a slot already final is refused, never driven again.
    _, _, _, _, r1, _ = run(2)
    for slot in (1, 2):
        try:
            b, out, w, d, r2, _ = restart(r1, [r for r in rows(2) if r["slot"] == slot], cls=cls)
            p.append(f"final slot {slot}: the restart drove it again ({[(o['attempt'], o['state']) for o in out]})")
        except batch.BatchConfigError as e:
            if "final" not in str(e):
                p.append(f"final slot {slot}: refused for another reason: {e}")
    # 4. a slot that ended at its rehearsal cap (no fate in the plan: the loop stopped for a human) is refused.
    _, _, _, _, r1, _ = run(1, plan={(1, a): "preflight-fail" for a in range(1, 10)}, serial=True)
    try:
        b, out, *_ = restart(r1, rows(1), start_attempts={1: 4}, cls=cls)
        p.append(f"capped slot: the restart drove it again ({[(o['attempt'], o['state']) for o in out]})")
    except batch.BatchConfigError as e:
        if "cap" not in str(e):
            p.append(f"capped slot: refused for another reason: {e}")
    return p


def restart_pause_problems(cls=batch.Batch) -> list[str]:
    """W1B2-3 (lane w1b's decision): a restart after a pause launches nothing before the usage window resets."""
    _, _, _, _, r1, _ = run(1, plan={(1, a): "rate-limit" for a in range(1, 10)})
    b, out, w, d, r2, win = restart(r1, [dict(rows(2)[1])], cls=cls)
    seq = [e[1] for e in w.events]
    if "reset" not in seq or "launch" not in seq or seq.index("reset") > seq.index("launch"):
        return [f"the restart launched before the window reset: {seq}"]
    return []


def history_validation_problems(cls=batch.Batch) -> list[str]:
    """W1B2-3: history the loop cannot trust is refused, never read as "nothing committed"."""
    p = []
    _, _, _, _, r1, _ = run(2, plan={(1, 1): "watcher-overflow"})
    good = r1.history()
    bad = {
        "a (slot, attempt) committed twice": good + [copy.deepcopy(good[0])],
        "an outcome missing a key": [{k: v for k, v in o.items() if k != "rerun"} for o in good],
        "an outcome with an unknown state": [dict(o, state="success") for o in good],
        "a slot under two half-cells": [good[0], dict(copy.deepcopy(good[0]), attempt=2, half_cell="hc-other")],
        "an attempt after the slot's final one": good + [dict(copy.deepcopy(good[-1]), attempt=good[-1]["attempt"] + 1)],
        "not a list": {"slot": 1},
    }
    for name, hist in bad.items():
        class Repo(FakeRepo):
            def history(self, _h=hist):
                return copy.deepcopy(_h)
        w = World()
        try:
            cls(FakeDriver(w), Repo(w), FakeWindow(w), table=test_table())
            p.append(f"{name}: accepted")
        except batch.BatchConfigError:
            pass
        except Exception as e:  # noqa: BLE001 - a crash is not a refusal
            p.append(f"{name}: crashed ({type(e).__name__}: {e})")

    class NoHistoryRepo:
        def register(self, row, attempt):
            pass

        def commit_records(self, row, attempt, outcome):
            pass
    try:
        cls(FakeDriver(World()), NoHistoryRepo(), FakeWindow(World()), table=test_table())
        p.append("a repo that cannot give its history: accepted")
    except batch.BatchConfigError:
        pass
    return p


# --------------------------------------------------------------------------------------- checks
def kinds(events, kind):
    return [e for e in events if e[1] == kind]


def commit_order_problems(events) -> list[str]:
    """Within each block (the registers between drives), records commit after every drive of the
    block ended, in the block's row order, and every register precedes the block's first launch."""
    p = []
    i = 0
    seq = [e[1:] for e in events]
    while i < len(seq):
        if seq[i][0] != "register":
            i += 1
            continue
        regs = []
        while i < len(seq) and seq[i][0] == "register":
            regs.append((seq[i][1], seq[i][2]))
            i += 1
        block_events = []
        while i < len(seq) and seq[i][0] != "register":
            block_events.append(seq[i])
            i += 1
        if block_events and block_events[0][0] not in ("launch", "launch-failed"):
            p.append(f"block {regs}: first event after registering is {block_events[0][0]}")
        commits = [(e[1], e[2]) for e in block_events if e[0] == "commit"]
        if commits != regs:
            p.append(f"block {regs}: records committed as {commits}")
        last_end = max((k for k, e in enumerate(block_events) if e[0] == "drive-end"), default=-1)
        first_commit = min((k for k, e in enumerate(block_events) if e[0] == "commit"), default=10 ** 9)
        if first_commit < last_end:
            p.append(f"block {regs}: a record committed while a drive of the block was running")
    return p


def container_problems(b, d) -> list[str]:
    p = []
    leaked = {o["leaked_container"] for o in b.outcomes if o.get("leaked_container")}
    if collections.Counter(d.removed) != collections.Counter(c for c in d.launched if c not in leaked):
        p.append(f"launched {sorted(d.launched)} but removed {sorted(d.removed)} (leaked, recorded: {sorted(leaked)})")
    if None in d.remove_calls:
        p.append("remove(None) was called")
    if d.pattern_removals:
        p.append("a container was removed by name pattern")
    if sorted(b.containers.values()) != sorted(d.launched):
        p.append("the loop did not record every launched id")
    for o in b.outcomes:
        if o["container_id"] != b.containers.get((o["slot"], o["attempt"])):
            p.append(f"slot {o['slot']}: outcome names a container the loop did not record")
    return p


def pause_problems(events) -> list[str]:
    """After a take routed `pause` commits, no launch until a window reset."""
    p = []
    waiting = False
    for e in events:
        if e[1] == "commit" and e[4] == labels4.PAUSE:
            waiting = True
        elif e[1] == "reset":
            waiting = False
        elif e[1] == "launch" and waiting:
            p.append(f"slot {e[2]} launched before the usage window reset")
    return p


def sibling_problems(out, w, r, b, want_stop) -> list[str]:
    """Slot 2 of a block of three failed or was blocked: every take of the block still committed,
    in row order, the siblings graded, and the loop stopped as `want_stop`."""
    p = []
    commits = [(e[2], e[3]) for e in kinds(w.events, "commit")]
    if commits != [(1, 1), (2, 1), (3, 1)]:
        p.append(f"commits {commits}, want slots 1, 2, 3 once each, in row order")
    states = {o["slot"]: o["state"] for o in out}
    if (states.get(1), states.get(3)) != (labels4.GRADED, labels4.GRADED):
        p.append(f"siblings {states}")
    if states.get(2) != want_stop:
        p.append(f"slot 2 is {states.get(2)}, want {want_stop}")
    if not b.stopped or b.stopped["state"] != want_stop:
        p.append(f"stopped {b.stopped}, want {want_stop}")
    return p


def reach_problems(case: str, cls=batch.Batch, event: str = "outside-reach", prefix: str = "reach ",
                   **driver_kw) -> list[str]:
    """W1B-1 and glitch-f3's priority test: slot 2 of a block of three reached the fake token and
    email. The exact object batch hands to commit, and the route if one won, carry mask=True and
    the event (`outside-reach`, or W1B2-2's `checker-event-reason` when an event id arrived as a
    checker reason); the committed text is the masked form, nothing deleted; the siblings, which
    reached nothing, are neither masked nor counted."""
    p = []
    b, out, w, d, r, _ = run(3, plan={(2, 1): prefix + case}, cls=cls, **driver_kw)
    snap, handed = r.snapshot(2), r.handed(2)
    if not any(o is handed for o in b.outcomes):
        p.append("the object handed to commit is not the take's outcome")
    if snap["mask"] is not True:
        p.append(f"{case}: handed to commit with mask={snap['mask']} ({snap['state']})")
    if not snap["events"] or event not in snap["events"]:
        p.append(f"{case}: handed to commit with events={snap['events']} ({snap['state']})")
    if snap["decision"] is not None and (snap["decision"]["mask"] is not True
                                        or event not in snap["decision"]["events"]):
        p.append(f"{case}: route {snap['decision']['route']} lost the mask or the event")
    committed, original = r.committed[(2, 1)]["text"], w.texts[(2, 1)]
    if FAKE_TOKEN in committed or FAKE_EMAIL in committed or MASK_MARK not in committed:
        p.append(f"{case}: committed text not masked: {committed!r}")
    if committed.count("\n") != original.count("\n") or "then carried on" not in committed:
        p.append(f"{case}: committed text lost lines (masked must never delete)")
    for s in (1, 3):
        sib = r.snapshot(s)
        if sib["mask"] is not False or sib["events"] != [] or r.committed[(s, 1)]["text"] != "(scripted)\n(scripted)":
            p.append(f"{case}: sibling slot {s} masked or counted ({sib['mask']}, {sib['events']})")
    return p


# ----------------------------------------------------------------------------------------- tests
class TestTerminalStates(unittest.TestCase):
    def test_scenarios_cover_every_terminal_state(self):
        reached = {scenario_state(n, test_table()) for n in SCENARIOS}
        self.assertEqual(reached, set(labels4.TERMINAL_STATES))

    def test_coverage_check_can_fail(self):
        with mock.patch.object(labels4, "TERMINAL_STATES", labels4.TERMINAL_STATES + ("new-state",)):
            reached = {scenario_state(n, test_table()) for n in SCENARIOS}
            self.assertNotEqual(reached, set(labels4.TERMINAL_STATES))

    def test_every_terminal_state_three_at_once(self):
        for name in SCENARIOS:
            want = scenario_state(name, test_table())
            with self.subTest(state=want, scenario=name):
                b, out, w, d, r, _ = run(3, plan={(2, 1): name}, finish_after={1: 2, 2: 3})
                first = [o for o in out if o["attempt"] == 1]
                self.assertEqual([o["state"] for o in first if o["slot"] == 2], [want])
                self.assertEqual(d.max_in_flight, 3)
                self.assertEqual([e[2] for e in kinds(w.events, "drive-end")][:3], [3, 2, 1])
                self.assertEqual(commit_order_problems(w.events), [])
                self.assertEqual(container_problems(b, d), [])
                self.assertEqual(r.overlaps, 0)
                self.assertEqual(pause_problems(w.events), [])
                if want in (labels4.BLOCKED, labels4.FAILED):
                    self.assertIsNotNone(b.stopped)
                    self.assertEqual(b.stopped["state"], want)
                elif want in (labels4.REHEARSAL, labels4.HARNESS_ERROR, labels4.PAUSE):
                    self.assertEqual([(o["slot"], o["attempt"], o["state"]) for o in out if o["attempt"] == 2],
                                     [(2, 2, labels4.GRADED)])   # re-run in the same slot
                else:
                    self.assertEqual(len(out), 3)

    def test_timed_out_turn_lands_on_the_timed_out_row(self):
        """W1B-7: the adapter's timed-out end is labels4's, so it reaches routing's timed-out row."""
        b, out, *_ = run(3, plan={(2, 1): "timed-out"})
        got = next(o for o in out if o["slot"] == 2)
        self.assertEqual((got["state"], got["decision"]["rows"]), (labels4.GRADED, ["timed-out"]))

    def test_timed_out_check_can_fail(self):
        with mock.patch.object(aa, "END_REASONS", (labels4.END_TURN, "timeout", labels4.END_ERROR)):
            with self.assertRaises(ValueError):      # a retyped end the adapter no longer accepts
                _turn(exit_code=137, end_reason=labels4.TIMED_OUT)
        rec = aa.harness_records(*SCENARIOS["timed-out"][:1], pin=PIN, box=_box())
        rec["ledger"]["turn_ends"][-1] = rec["ledger"]["end"] = "timeout"   # a retyped end reaching routing
        with self.assertRaises(routing.RoutingRefused):
            routing.route(rec, test_table())

    def test_unhandled_state_refuses_to_start(self):
        with mock.patch.object(labels4, "TERMINAL_STATES", labels4.TERMINAL_STATES + ("new-state",)):
            with self.assertRaises(batch.BatchConfigError):
                run(1)


def gate_problems() -> list[str]:
    """W1B-9/W1B-10: each table missing what only the owner or CP5 can supply must be refused,
    and the complete one accepted."""
    p = []
    bad = {
        "pause cap pending": lambda t: t["caps"][labels4.PAUSE].update(reruns_per_half_cell=None),
        "operator_reasons empty": lambda t: t.update(operator_reasons=[]),
        "operator_reasons_status PENDING": lambda t: t.update(operator_reasons_status="PENDING: not read"),
        "pin_profiles empty": lambda t: t.update(pin_profiles={}),
        "pin_profiles_status PENDING": lambda t: t.update(pin_profiles_status="PENDING (CP5)"),
    }
    for name, edit in bad.items():
        t = test_table()
        edit(t)
        try:
            batch.Batch(None, None, None, table=t, history=[])
            p.append(f"{name}: the loop would start")
        except batch.BatchConfigError:
            pass
    try:
        batch.Batch(None, None, None, table=test_table(), history=[])
    except batch.BatchConfigError as e:
        p.append(f"a complete table was refused: {e}")
    return p


class TestStartGate(unittest.TestCase):
    def test_real_table_refuses_to_start(self):
        with self.assertRaises(batch.BatchConfigError) as cm:
            batch.Batch(None, None, None)   # the real routing.json: the CP5 pins are still PENDING
        self.assertIn("pin_profiles", str(cm.exception))
        # round 3's reasons and pause cap are filled (Javier's "gap4 routing: A"), so only the pins remain
        for filled in ("pause", "operator_reasons"):
            self.assertNotIn(filled, str(cm.exception))

    def test_gate_refuses_pending_data(self):
        self.assertEqual(gate_problems(), [])

    def test_gate_check_can_fail(self):
        def caps_only(table):   # the pre-fold gate: the caps alone
            return [f"cap {r}" for r in batch.pending_caps(table)]
        with mock.patch.object(batch, "start_problems", caps_only):
            self.assertEqual(len(gate_problems()), 4)

    def test_check_cli_exits_1_while_pending(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(batch.main(["--check"]), 1)
        for what in ("pin_profiles", "pin_profiles_status"):
            self.assertIn(what, buf.getvalue())
        for filled in ("pause", "operator_reasons"):   # filled under Javier's "gap4 routing: A"
            self.assertNotIn(filled, buf.getvalue())
        ready = test_table()
        with mock.patch.object(routing, "load_table", lambda *a: copy.deepcopy(ready)), \
                redirect_stdout(io.StringIO()) as out:
            self.assertEqual(batch.main(["--check"]), 0)
        self.assertIn("ready", out.getvalue())

    def test_a_row_without_a_profile_refuses_to_start(self):
        with self.assertRaisesRegex(batch.BatchConfigError, "no pre-registered pin profile"):
            run(1, row_list=rows(2, model="unregistered-model"))
        with self.assertRaisesRegex(batch.BatchConfigError, "must name slot, half_cell and model"):
            run(1, row_list=[{"slot": 1, "half_cell": "hc-a"}])
        with self.assertRaisesRegex(batch.BatchConfigError, "slots repeat"):
            run(1, row_list=rows(2) + rows(1))

    def test_row_check_can_fail(self):
        with mock.patch.object(batch.Batch, "row_problems", lambda self, rows: []):
            b, out, *_ = run(1, row_list=rows(2, model="unregistered-model"))   # starts, and every take fails
        self.assertEqual({o["state"] for o in out}, {labels4.FAILED})


class TrustingBatch(batch.Batch):
    """Mutant: trusts the driver's pin model instead of the registered row's."""

    def _route(self, row, attempt, cid, records):
        return super()._route(dict(row, model=records["pin"]["model"]), attempt, cid, records)


class TestPins(unittest.TestCase):
    """W1B-10: the pin a take is checked against comes from the registered row and the
    pre-registered profiles, never from the driver."""

    def test_driver_pin_differing_from_the_profile_is_blocked(self):
        b, out, w, d, r, _ = run(3, pins={2: dict(PIN, version="driver-says")})
        self.assertEqual(sibling_problems(out, w, r, b, labels4.BLOCKED), [])
        self.assertIn("pin", next(o for o in out if o["slot"] == 2)["reason"])

    def test_driver_pin_of_another_registered_model_is_blocked(self):
        # routing alone accepts this pin: it is test-model-b's own pre-registered profile ...
        turns, box = ALL["other-model"]
        self.assertEqual(routing.route(aa.harness_records(turns, pin=OTHER_PIN, box=box), test_table())["route"],
                         labels4.GRADED)
        # ... but the row registered test-model-a, so the take is blocked.
        b, out, w, d, r, _ = run(3, plan={(2, 1): "other-model"}, pins={2: dict(OTHER_PIN)})
        self.assertEqual(sibling_problems(out, w, r, b, labels4.BLOCKED), [])

    def test_pin_check_can_fail(self):
        b, out, w, d, r, _ = run(3, plan={(2, 1): "other-model"}, pins={2: dict(OTHER_PIN)}, cls=TrustingBatch)
        self.assertNotEqual(sibling_problems(out, w, r, b, labels4.BLOCKED), [])


class NoCatchRemove(batch.Batch):
    """Mutant: the pre-fold removal, which let remove() raise."""

    def _remove(self, cid):
        if cid is not None:
            self.driver.remove(cid)


class RefusalOnlyRoute(batch.Batch):
    """Mutant: the pre-fold routing step, which caught RoutingRefused only."""

    def _route(self, row, attempt, cid, records):
        try:
            decision = self.route_fn(records, self.table)
        except routing.RoutingRefused as e:
            return self._outcome(row, attempt, cid, state=labels4.BLOCKED, reason=str(e), records=records)
        return self._outcome(row, attempt, cid, state=decision["route"], decision=decision, records=records)


class SinkingResult(batch.Batch):
    """Mutant: a drive step that raises sinks the block."""

    def _result(self, future, row, attempt, cid):
        return future.result()


class RaisingStep(batch.Batch):
    """A drive step with a defect: it raises for slot 2 after that drive ran with its block."""

    def _drive_step(self, row, attempt, cid, err):
        out = super()._drive_step(row, attempt, cid, err)
        if row["slot"] == 2:
            raise RuntimeError("drive step defect")
        return out


class SinkingStep(RaisingStep, SinkingResult):
    pass


def _route_raises_on_slot_2(records, table):
    if records["exit"]["exec_codes"] == [0, 0, 0]:
        raise TypeError("'>' not supported between instances of 'str' and 'int'")
    return routing.route(records, table)


def _route_success_on_slot_2(records, table):
    if records["exit"]["exec_codes"] == [0, 0, 0]:
        return {"route": "success"}   # not a labels4 route
    return routing.route(records, table)


class UncheckedRoute(batch.Batch):
    """Mutant: takes whatever route routing returns."""

    def _route(self, row, attempt, cid, records):
        decision = self.route_fn(records, self.table)
        return self._outcome(row, attempt, cid, state=decision["route"], decision=decision, records=records)


def _three_turns(records):
    records["ledger"].update(turns=3, turn_ends=[labels4.END_TURN] * 3, turn_outputs=[True] * 3)
    records["exit"]["exec_codes"] = [0, 0, 0]
    records["init"] = records["init"] + [records["init"][-1]]


def _string_counter(records):
    records["cgroup"]["oom_kill_delta"] = "1"


def remove_problems(cls=batch.Batch) -> list[str]:
    """remove() raising for slot 2's container: the take is `failed` with its recorded id named
    as leaked and its routing kept for the human; the siblings commit; the loop stops."""
    b, out, w, d, r, _ = run(3, remove_fails={2}, cls=cls)
    p = sibling_problems(out, w, r, b, labels4.FAILED) + container_problems(b, d)
    two = r.snapshot(2)
    if two["leaked_container"] != b.containers.get((2, 1)) or "leaked" not in (two["reason"] or ""):
        p.append(f"the leak is not recorded with its id: {two['leaked_container']}, {two['reason']}")
    if not two["decision"] or two["decision"]["route"] != labels4.GRADED or two["events"] != []:
        p.append("the take's routing and annotations were lost with the container")
    return p


def route_raise_problems(cls=batch.Batch) -> list[str]:
    """route() raising a non-refusal for slot 2: `failed`, with the records and annotations kept;
    the siblings commit; the loop stops."""
    b, out, w, d, r, _ = run(3, records_edit={2: _three_turns}, batch_kw={"route_fn": _route_raises_on_slot_2},
                             cls=cls)
    p = sibling_problems(out, w, r, b, labels4.FAILED)
    two = r.snapshot(2)
    if "routing raised: TypeError" not in (two["reason"] or ""):
        p.append(f"reason {two['reason']!r}")
    if two["records"] is None or two["events"] != [] or "annotations read" not in (two["mask_basis"] or ""):
        p.append("the take's records and annotations were lost with the routing error")
    if two["mask"] is not True:
        p.append("a failed take was committed unmasked (W1B2-2)")
    return p


class TestFailures(unittest.TestCase):
    """W1B-3: one take's failure never loses its siblings: every take of the block is committed,
    in row order, then the loop stops."""

    def test_remove_raising_for_one_container(self):
        self.assertEqual(remove_problems(), [])

    def test_remove_check_can_fail(self):
        self.assertNotEqual(remove_problems(NoCatchRemove), [])

    def test_route_raising_a_non_refusal_is_failed(self):
        self.assertEqual(route_raise_problems(), [])

    def test_route_raising_check_can_fail(self):
        self.assertNotEqual(route_raise_problems(RefusalOnlyRoute), [])

    def test_route_returning_no_labels4_route_is_failed(self):
        b, out, w, d, r, _ = run(3, records_edit={2: _three_turns}, batch_kw={"route_fn": _route_success_on_slot_2})
        self.assertEqual(sibling_problems(out, w, r, b, labels4.FAILED), [])
        self.assertIn("no labels4 route", r.snapshot(2)["reason"])

    def test_unknown_route_check_can_fail(self):
        with self.assertRaises(KeyError):   # no handler for "success": the block sinks
            run(3, records_edit={2: _three_turns}, batch_kw={"route_fn": _route_success_on_slot_2}, cls=UncheckedRoute)

    def test_malformed_record_is_blocked_and_masked_fail_closed(self):
        """With W1B-2, a string counter is a refusal (blocked), and no count can be trusted."""
        b, out, w, d, r, _ = run(3, records_edit={2: _string_counter})
        self.assertEqual(sibling_problems(out, w, r, b, labels4.BLOCKED), [])
        two = r.snapshot(2)
        self.assertEqual((two["mask"], two["events"]), (True, None))
        self.assertIn("fail-closed", two["mask_basis"])

    def test_drive_step_raising_never_sinks_the_block(self):
        b, out, w, d, r, _ = run(3, cls=RaisingStep)
        self.assertEqual(sibling_problems(out, w, r, b, labels4.FAILED), [])
        self.assertIn("drive step raised", r.snapshot(2)["reason"])
        self.assertEqual(r.snapshot(2)["mask"], True)   # no records reached the loop: masked fail-closed

    def test_drive_step_check_can_fail(self):
        with self.assertRaises(RuntimeError):
            run(3, cls=SinkingStep)

    def test_commit_failure_stops_after_the_block(self):
        class FailingRepo(FakeRepo):
            def commit_records(self, row, attempt, outcome):
                if row["slot"] == 2:
                    raise RuntimeError("disk full")
                super().commit_records(row, attempt, outcome)
        w = World()
        d, rp, win = FakeDriver(w), FailingRepo(w), FakeWindow(w)
        b = batch.Batch(d, rp, win, table=test_table())
        out = b.run(rows(5))
        self.assertEqual([(o["slot"], o["state"]) for o in out],
                         [(1, labels4.GRADED), (2, labels4.FAILED), (3, labels4.GRADED)])
        self.assertEqual(b.stopped["state"], labels4.FAILED)


def fail_closed_problems(cls=batch.Batch) -> list[str]:
    """Every road to `blocked` or `failed` (W1B2-2): each such outcome handed to commit carries mask=True,
    and its mask_basis says fail-closed; and every road was taken (a run that reached neither proves nothing)."""
    p = []
    roads = {
        "unlisted checker reason (blocked)": dict(plan={(2, 1): "unlisted-reason"}),
        "the driver's pin (blocked)": dict(pins={2: dict(PIN, version="driver-says")}),
        "malformed records (blocked)": dict(records_edit={2: _string_counter}),
        "the driver raised (failed)": dict(plan={(2, 1): "driver-raises"}),
        "a launch failed (failed)": dict(launch_fails={2: "half"}),
        "remove failed (failed)": dict(remove_fails={2}),
        "routing raised (failed)": dict(records_edit={2: _three_turns}, batch_kw={"route_fn": _route_raises_on_slot_2}),
        "routing returned no route (failed)": dict(records_edit={2: _three_turns},
                                                   batch_kw={"route_fn": _route_success_on_slot_2}),
    }
    for name, kw in roads.items():
        b, out, w, d, r, _ = run(3, cls=cls, **kw)
        stopped = [snap for _, _, _, snap in r.passed if snap["state"] in labels4.BATCH_STATES]
        if not stopped:
            p.append(f"{name}: no blocked or failed take was committed")
        for snap in stopped:
            if snap["mask"] is not True or "fail-closed" not in (snap["mask_basis"] or ""):
                p.append(f"{name}: slot {snap['slot']} {snap['state']} committed with mask={snap['mask']} "
                         f"({snap['mask_basis']})")
    return p


class GradedOnlyMask(batch.Batch):
    """Mutant: the pre-fold behaviour, where the mask and events came only with a graded route."""

    def _drive_step(self, row, attempt, cid, err):
        out = super()._drive_step(row, attempt, cid, err)
        if out["state"] != labels4.GRADED:
            out.update(mask=False, events=[])
        return out


class TestMask(unittest.TestCase):
    """W1B-1 and glitch-f3's priority test."""

    def test_reach_masked_on_every_terminal_state(self):
        reached = set()
        for case in REACH:
            reached.add(scenario_state("reach " + case, test_table()))
            with self.subTest(case=case, state=scenario_state("reach " + case, test_table())):
                self.assertEqual(reach_problems(case), [])
        self.assertLessEqual({labels4.GRADED, labels4.PAUSE, labels4.HARNESS_ERROR, labels4.ABORTED,
                              labels4.BLOCKED}, reached)

    def test_reach_masked_when_the_container_leaks(self):
        self.assertEqual(reach_problems("end_turn", remove_fails={2}), [])

    def test_no_records_masks_fail_closed(self):
        b, out, w, d, r, _ = run(3, plan={(2, 1): "driver-raises"})
        two = r.snapshot(2)
        self.assertEqual((two["state"], two["mask"], two["events"]), (labels4.FAILED, True, None))
        self.assertIn("fail-closed", two["mask_basis"])

    def test_checker_event_reason_masked_on_every_terminal_state(self):
        """W1B2-2: an id the plan makes an event, arriving as a checker reason, is refused by routing (blocked);
        the take is still committed masked and counted, on every terminal state, for each of the three ids."""
        for name in CHECKER_EVENT:
            with self.subTest(case=name, state=scenario_state("event " + name, test_table())):
                self.assertEqual(scenario_state("event " + name, test_table()), labels4.BLOCKED)
                self.assertEqual(reach_problems(name, event="checker-event-reason", prefix="event "), [])

    def test_every_blocked_and_failed_outcome_is_masked(self):
        """W1B2-2: a take that is blocked or failed is committed masked, fail-closed, whatever its annotations."""
        self.assertEqual(fail_closed_problems(), [])

    def test_fail_closed_check_can_fail(self):
        class NoSeal(batch.Batch):            # the pre-fold commit: the mask only from the annotations
            @staticmethod
            def _seal(outcome):
                return None
        found = fail_closed_problems(NoSeal)
        for road in ("unlisted checker reason", "the driver's pin", "remove failed", "routing raised"):
            self.assertTrue(any(x.startswith(road) for x in found), (road, found))

    def test_checker_event_check_can_fail(self):
        t = test_table()
        t["annotations"] = [a for a in t["annotations"] if a["id"] != "checker-event-reason"]
        name = next(iter(CHECKER_EVENT))
        self.assertNotEqual(reach_problems(name, event="checker-event-reason", prefix="event ", table=t), [])

        class NoSeal(batch.Batch):
            @staticmethod
            def _seal(outcome):
                return None
        found = reach_problems(name, event="checker-event-reason", prefix="event ", table=t, cls=NoSeal)
        self.assertTrue(any("mask=False" in x for x in found), found)

    def test_reach_check_can_fail(self):
        self.assertNotEqual(reach_problems("rate limit", cls=GradedOnlyMask), [])
        self.assertNotEqual(reach_problems("oom kill", cls=GradedOnlyMask), [])
        real = routing.annotate

        def graded_only(records, table=None):   # a routing-side mutant of the same defect
            out = real(records, table)
            return out if records["ledger"]["end"] in labels4.GRADED_ENDS else {"events": [], "mask": False}
        with mock.patch.object(routing, "annotate", graded_only):
            self.assertNotEqual(reach_problems("api 500"), [])
            self.assertNotEqual(reach_problems("container exit"), [])


class LateFate(batch.Batch):
    """Mutant: the pre-fold order, where the commit was handed the outcome before its fate."""

    def _decide(self, row, attempt, outcome):
        fate = super()._decide(row, attempt, outcome)
        return {"final": None, "rerun": fate["rerun"], "beyond_cap": None, "stop": None}


def fate_problems(cls=batch.Batch) -> list[str]:
    """W1B-8: each committed record already says what became of its slot."""
    p = []
    b, out, w, d, r, _ = run(1, plan={(1, 1): "watcher-overflow", (1, 2): "watcher-overflow"}, cls=cls)
    got = [(r.snapshot(1, a)["final"], r.snapshot(1, a)["rerun"], r.snapshot(1, a)["beyond_cap"], r.snapshot(1, a)["stop"])
           for a in (1, 2)]
    if got != [(False, True, False, None), (True, False, True, None)]:
        p.append(f"harness-error re-run then beyond its cap committed as {got}")
    b, out, w, d, r, _ = run(2, plan={(1, a): "preflight-fail" for a in range(1, 10)}, serial=True, cls=cls)
    last = r.snapshot(1, 4)
    if (last["final"], last["beyond_cap"], last["stop"]) != (False, True, "rehearsal cap reached"):
        p.append(f"rehearsal beyond its cap committed as {last['final'], last['beyond_cap'], last['stop']}")
    b, out, w, d, r, _ = run(1, plan={(1, a): "rate-limit" for a in range(1, 10)}, cls=cls)
    last = r.snapshot(1, TEST_PAUSE_CAP + 1)
    if (last["beyond_cap"], last["stop"]) != (True, "pause cap reached"):
        p.append(f"pause beyond its cap committed as {last['beyond_cap'], last['stop']}")
    b, out, w, d, r, _ = run(1, cls=cls)
    if r.snapshot(1)["final"] is not True:
        p.append("a graded take was not committed as final")
    b, out, w, d, r, _ = run(1, plan={(1, 1): "unlisted-reason"}, cls=cls)
    if not r.snapshot(1)["stop"] or "routing refused" not in r.snapshot(1)["stop"]:
        p.append(f"a blocked take was committed without its stop reason: {r.snapshot(1)['stop']}")
    return p


class TestFate(unittest.TestCase):
    def test_fate_committed_with_the_record(self):
        self.assertEqual(fate_problems(), [])

    def test_fate_check_can_fail(self):
        self.assertNotEqual(fate_problems(LateFate), [])

    def test_every_committed_outcome_has_every_key(self):
        b, out, w, d, r, _ = run(3, plan={(2, 1): "driver-raises"})
        for slot, attempt, _, snap in r.passed:
            self.assertEqual(set(snap), set(batch.OUTCOME_KEYS), (slot, attempt))


class Leaky(batch.Batch):
    """Mutant: never removes a container."""

    def _remove(self, cid):
        return None


class NoHalfCreated(batch.Batch):
    """Mutant: the pre-fold launch, which dropped the id a failed launch named."""

    def _launch(self, row, attempt):
        try:
            cid = self.driver.launch(row)
        except Exception as e:  # noqa: BLE001
            return None, e
        self.containers[(row["slot"], attempt)] = cid
        return cid, None


class TestOrderAndContainers(unittest.TestCase):
    def test_commits_land_serially_in_row_order(self):
        # Later rows finish first; their records still commit after, in row order.
        b, out, w, d, r, _ = run(7, finish_after={1: 2, 2: 3, 4: 5, 5: 6})
        self.assertEqual(commit_order_problems(w.events), [])
        self.assertEqual(r.overlaps, 0)
        self.assertEqual([o["slot"] for o in out], [1, 2, 3, 4, 5, 6, 7])
        ends = [e[2] for e in kinds(w.events, "drive-end")]
        self.assertEqual(ends[:6], [3, 2, 1, 6, 5, 4])   # the drives really did finish out of row order

    def test_commit_order_check_can_fail(self):
        _, _, w, *_ = run(3, finish_after={1: 2, 2: 3})
        commits = [i for i, e in enumerate(w.events) if e[1] == "commit"]
        mutated = list(w.events)
        mutated[commits[0]], mutated[commits[1]] = mutated[commits[1]], mutated[commits[0]]
        self.assertNotEqual(commit_order_problems(mutated), [])
        early = [e for e in w.events if e[1] != "commit"]
        early.insert(next(i for i, e in enumerate(early) if e[1] == "drive-start"), w.events[commits[0]])
        self.assertNotEqual(commit_order_problems(early), [])

    def test_containers_removed_by_recorded_id(self):
        b, out, w, d, *_ = run(5, plan={(2, 1): "driver-raises"})
        self.assertEqual(container_problems(b, d), [])
        self.assertEqual(len(d.launched), 3)   # failed stops the loop after the first block

    def test_container_check_can_fail(self):
        b, out, w, d, *_ = run(3, cls=Leaky)
        self.assertNotEqual(container_problems(b, d), [])
        b, out, w, d, *_ = run(3)
        d.pattern_removals = 1
        self.assertNotEqual(container_problems(b, d), [])
        d.pattern_removals, d.remove_calls = 0, d.remove_calls + [None]
        self.assertNotEqual(container_problems(b, d), [])

    def test_no_container_id_is_never_removed(self):
        """NIT: an adapter that runs no container returns no id; remove(None) is never called."""
        b, out, w, d, r, _ = run(3, no_ids=True)
        self.assertEqual(d.remove_calls, [])
        self.assertEqual([(o["state"], o["container_id"]) for o in out], [(labels4.GRADED, None)] * 3)

    def test_a_half_created_container_is_removed_by_its_id(self):
        """NIT: a launch that raises after creating a container names it; the loop records and
        removes it, and the take fails while its siblings commit."""
        b, out, w, d, r, _ = run(3, launch_fails={2: "half"})
        self.assertEqual(container_problems(b, d), [])
        self.assertIn(b.containers[(2, 1)], d.removed)
        self.assertEqual(sibling_problems(out, w, r, b, labels4.FAILED), [])
        b, out, w, d, r, _ = run(3, launch_fails={2: "none"})
        self.assertEqual(container_problems(b, d), [])
        self.assertEqual(sibling_problems(out, w, r, b, labels4.FAILED), [])

    def test_half_created_check_can_fail(self):
        b, out, w, d, r, _ = run(3, launch_fails={2: "half"}, cls=NoHalfCreated)
        self.assertNotEqual(container_problems(b, d), [])

    def test_serial_fallback_drives_one_at_a_time(self):
        b, out, w, d, *_ = run(4, serial=True)
        self.assertEqual(d.max_in_flight, 1)
        self.assertEqual(len(out), 4)
        self.assertEqual(commit_order_problems(w.events), [])

    def test_concurrency_check_can_fail(self):
        real = concurrent.futures.ThreadPoolExecutor
        with mock.patch.object(batch.concurrent.futures, "ThreadPoolExecutor", lambda max_workers: real(max_workers=1)):
            b, out, w, d, *_ = run(3, wait_s=0.3)
        self.assertNotEqual(d.max_in_flight, 3)
        self.assertEqual({o["state"] for o in out}, {labels4.FAILED})   # the barrier caught the serial drives


class TestPause(unittest.TestCase):
    def test_pause_launches_no_new_drive_until_reset(self):
        b, out, w, d, r, win = run(6, plan={(2, 1): "rate-limit"}, finish_after={1: 2, 3: 2})
        self.assertEqual(pause_problems(w.events), [])
        self.assertEqual(win.resets, 1)
        self.assertEqual(kinds(w.events, "drive-end")[0][2], 2)   # the pause came first; 1 and 3 still running
        first_block = [o for o in out[:3]]
        self.assertEqual([o["state"] for o in first_block],
                         [labels4.GRADED, labels4.PAUSE, labels4.GRADED])   # running drives finished
        reset_at = next(i for i, e in enumerate(w.events) if e[1] == "reset")
        pause_commit = next(i for i, e in enumerate(w.events) if e[1] == "commit" and e[4] == labels4.PAUSE)
        self.assertFalse([e for e in w.events[pause_commit:reset_at] if e[1] in ("launch", "register")])
        self.assertEqual(out[3]["slot"], 2)   # the paused slot re-runs first, in the same slot
        self.assertEqual(sorted(o["slot"] for o in out if o["state"] == labels4.GRADED), [1, 2, 3, 4, 5, 6])

    def test_pause_check_can_fail(self):
        class Impatient(batch.Batch):
            def _pause(self, row, attempt, outcome):
                fate = super()._pause(row, attempt, outcome)
                self.paused = False   # forgets to wait for the window
                return fate
        b, out, w, d, r, win = run(6, plan={(2, 1): "rate-limit"}, cls=Impatient)
        self.assertEqual(win.resets, 0)
        self.assertNotEqual(pause_problems(w.events), [])

    def test_a_text_only_usage_limit_pauses_the_loop(self):
        """glitch-f3's ruling: a usage-limit refusal that carries only its error text pauses, as a 429 does."""
        self.assertEqual(scenario_state("usage-limit-text", test_table()), labels4.PAUSE)
        b, out, w, d, r, win = run(3, plan={(2, 1): "usage-limit-text"})
        self.assertEqual([o["state"] for o in out if (o["slot"], o["attempt"]) == (2, 1)], [labels4.PAUSE])
        self.assertEqual(win.resets, 1)
        self.assertEqual(pause_problems(w.events), [])

    def test_the_agent_saying_rate_limit_never_pauses_the_loop(self):
        """glitch-f3's ruling: the markers are never matched on the agent's own reply."""
        self.assertEqual(scenario_state("agent-says-rate-limit", test_table()), labels4.HARNESS_ERROR)
        b, out, w, d, r, win = run(3, plan={(2, 1): "agent-says-rate-limit"})
        self.assertEqual([o["state"] for o in out if (o["slot"], o["attempt"]) == (2, 1)], [labels4.HARNESS_ERROR])
        self.assertEqual(win.resets, 0)

    def test_pause_cap(self):
        plan = {(1, a): "rate-limit" for a in range(1, 10)}
        b, out, w, *_ = run(1, plan=plan)
        self.assertEqual(len(out), TEST_PAUSE_CAP + 1)
        self.assertTrue(out[-1]["beyond_cap"])
        self.assertEqual(b.stopped["state"], labels4.PAUSE)


class TestCaps(unittest.TestCase):
    def test_harness_error_one_rerun_per_slot(self):
        plan = {(1, 1): "watcher-overflow", (1, 2): "watcher-overflow"}
        b, out, *_ = run(1, plan=plan)
        self.assertEqual([o["state"] for o in out], [labels4.HARNESS_ERROR] * 2)
        self.assertTrue(out[-1]["beyond_cap"])
        self.assertIsNone(b.stopped)   # final as harness-error, its own column; the loop goes on

    def test_harness_error_two_reruns_per_half_cell(self):
        plan = {(s, 1): "watcher-overflow" for s in (1, 2, 3)}
        b, out, *_ = run(3, plan=plan)
        reruns = [o for o in out if o["attempt"] == 2]
        self.assertEqual(sorted(o["slot"] for o in reruns), [1, 2])
        self.assertTrue(next(o for o in out if o["slot"] == 3)["beyond_cap"])

    def test_rehearsal_cap_three_per_half_cell_then_blocked(self):
        plan = {(1, a): "preflight-fail" for a in range(1, 10)}
        b, out, *_ = run(2, plan=plan, serial=True)
        self.assertEqual([o["state"] for o in out if o["slot"] == 1], [labels4.REHEARSAL] * 4)
        self.assertEqual(b.stopped["state"], labels4.REHEARSAL)
        self.assertNotIn(2, [o["slot"] for o in out])   # nothing new launched once stopped

    def test_cap_checks_can_fail(self):
        t = test_table()
        t["caps"][labels4.HARNESS_ERROR]["reruns_per_slot"] = 5
        b, out, *_ = run(1, plan={(1, a): "watcher-overflow" for a in (1, 2, 3)}, table=t)
        self.assertNotEqual([o["state"] for o in out], [labels4.HARNESS_ERROR] * 2)

    def test_aborted_and_graded_never_rerun(self):
        b, out, *_ = run(3, plan={(1, 1): "oom"})
        self.assertEqual([(o["slot"], o["state"]) for o in out],
                         [(1, labels4.ABORTED), (2, labels4.GRADED), (3, labels4.GRADED)])


class TestRestart(unittest.TestCase):
    """W1B2-3: the caps and attempt numbers come back from the committed outcomes after a stop."""

    def test_stop_restart_no_extra_rerun(self):
        self.assertEqual(restart_problems(), [])

    def test_restart_after_a_pause_waits_for_the_window(self):
        self.assertEqual(restart_pause_problems(), [])

    def test_untrustworthy_history_is_refused(self):
        self.assertEqual(history_validation_problems(), [])

    def test_restart_check_can_fail(self):
        class NoReplay(batch.Batch):          # the pre-fold loop: the history is never read
            def _replay(self, history):
                pass

        class ForgetsReruns(batch.Batch):     # attempts rebuilt, re-runs spent forgotten
            def _replay(self, history):
                super()._replay(history)
                self.reruns.clear()
                self.slot_reruns.clear()

        class ForgetsAttempts(batch.Batch):   # every slot starts again at attempt 1
            def _replay(self, history):
                super()._replay(history)
                self.next_attempt.clear()

        class DrivesClosedSlots(batch.Batch):  # a final or capped slot is driven again
            def _replay(self, history):
                super()._replay(history)
                self.closed.clear()

        class ForgetsThePause(batch.Batch):   # a restart after a pause launches at once
            def _replay(self, history):
                super()._replay(history)
                self.paused = False
        self.assertNotEqual(restart_problems(NoReplay), [])
        found = restart_problems(ForgetsReruns)
        self.assertTrue(any("slot cap" in x for x in found) and any("half-cell cap" in x for x in found), found)
        self.assertTrue(any("committed 2 times" in x for x in restart_problems(ForgetsAttempts)))
        found = restart_problems(DrivesClosedSlots)
        self.assertTrue(any("final slot" in x for x in found) and any("capped slot" in x for x in found), found)
        self.assertNotEqual(restart_pause_problems(ForgetsThePause), [])
        self.assertNotEqual(restart_pause_problems(NoReplay), [])

    def test_history_check_can_fail(self):
        class Trusting(batch.Batch):          # history read without its checks
            @staticmethod
            def history_problems(history):
                return []

        class DefaultsToNothing(batch.Batch):   # a repo with no history() read as "nothing committed"
            def __init__(self, driver, repo, window, **kw):
                if not callable(getattr(repo, "history", None)):
                    kw.setdefault("history", [])
                super().__init__(driver, repo, window, **kw)
        found = history_validation_problems(Trusting)
        for case in ("committed twice", "two half-cells", "after the slot's final one"):
            self.assertTrue(any(case in x for x in found), (case, found))
        self.assertIn("a repo that cannot give its history: accepted", history_validation_problems(DefaultsToNothing))


# ---------------------------------------------------------------------------- import boundary
FORBIDDEN_IMPORTS = ("drive", "claude", "agent_adapter")


def import_problems(source: str) -> list[str]:
    p = []
    for node in ast.walk(ast.parse(source)):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""] + [a.name for a in node.names]
        for n in names:
            if any(f in n.lower() for f in FORBIDDEN_IMPORTS):
                p.append(n)
    return p


class TestBoundary(unittest.TestCase):
    def test_batch_and_routing_import_no_driver_or_agent(self):
        for name in ("batch.py", "routing.py"):
            with open(os.path.join(_ROOT, name), encoding="utf-8") as fh:
                self.assertEqual(import_problems(fh.read()), [], name)

    def test_boundary_check_can_fail(self):
        for src in ("import drive", "from drive import run", "import claude_code_sdk",
                    "from agent_adapter import ScriptedAdapter", "import os, drive"):
            self.assertNotEqual(import_problems(src), [], src)

    def test_handlers_keyed_by_labels4(self):
        b = batch.Batch(None, None, None, table=test_table(), history=[])
        self.assertEqual(set(b.handlers), set(labels4.TERMINAL_STATES))


class TestCli(unittest.TestCase):
    def test_states_and_check(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(batch.main(["--states"]), 0)
        got = json.loads(buf.getvalue())
        self.assertEqual(tuple(got["routes"]) + tuple(got["batch"]), labels4.TERMINAL_STATES)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(batch.main(["--check"]), 1)   # pending data
        with mock.patch.object(batch, "under_nohup", lambda: False), redirect_stderr(io.StringIO()) as err:
            self.assertEqual(batch.main([]), 2)
        self.assertIn("nohup", err.getvalue())


if __name__ == "__main__":
    unittest.main()
