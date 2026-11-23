#!/usr/bin/env python3
"""batch.py: every terminal state with three drives at once, commits serial in row order and for
every take of a wave, containers removed by recorded id, a pause launches no new drive, the mask
and events decided on every take and committed, the fate committed with the record, a start
gate that refuses pending data, and glitch-f3's rulings of 6 Oct 2026 (a half-cell closing
`incomplete — mechanical` at its rehearsal or pause cap, round 3's unit; the wait_reset contract).

The driver is a fake built on agent_adapter.ScriptedAdapter: no model, no container, no drive.py.
Which terminal state each fake scenario reaches is computed by routing.route on the scenario's
records, and the set the tests must reach is labels4.TERMINAL_STATES: neither is typed here.
Concurrency and finishing order are forced with a barrier and events, never with sleeps: a drive
waits (up to WAIT_S, a hang detector) until every drive of its wave is in flight, and a drive
told to finish after another waits for that one's end. B19-8 (batch.py's rolling window): with no
finish_after the drives of one wave end together, its head first, and a commit waits until every
drive step the loop holds open has finished (World, B19-13), so the rolling loop's tie rule
reproduces the block run of the old loop; with finish_after the durations differ and the loop
fills freed lanes. Every check is a function returning
problems, and each is also run against an in-memory mutant of what it guards and must go red.

The agent "reaching the token and the account email" is played by two in-memory fake strings
(FAKE_TOKEN, FAKE_EMAIL); no real token exists here and no token or login file is read.
"""

from __future__ import annotations

import ast
import collections
import concurrent.futures
import copy
import inspect
import io
import itertools
import json
import os
import sys
import textwrap
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.dont_write_bytecode = True
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import agent_adapter as aa  # noqa: E402
import batch  # noqa: E402
import harness_bookkeeping as hb  # noqa: E402  (the seam's harness name, never typed here: interface 8)
import routing  # noqa: E402
from graders import labels4  # noqa: E402

# Test-only pin profiles, injected in memory (CP5 pre-registers the real ones; until then routing.json's
# pin_profiles is empty and PENDING).
# Keyed by harness, then model (interface 8; the harness is the seam's own name, never typed here).
HARNESS = hb.CLAUDE_CODE
PROFILES = {HARNESS: {"test-model-a": {"permission_mode": "bypassPermissions", "version": "0.0.1-test"},
                      "test-model-b": {"permission_mode": "plan-test", "version": "0.0.2-test"}}}
PIN = dict(PROFILES[HARNESS]["test-model-a"], model="test-model-a", harness=HARNESS)
OTHER_PIN = dict(PROFILES[HARNESS]["test-model-b"], model="test-model-b", harness=HARNESS)
# The real pause cap: round 3's pause_cap (3 per half-cell), filled under Javier's ruling "gap4 routing: A"
# and re-derived from round 3's prereg.json by test_routing.py's TestRound3Sources.
PAUSE_CAP = routing.load_table()["caps"][labels4.PAUSE]["events_per_half_cell"]
# Round 3's rehearsal_cap (3 per half-cell), re-derived from round 3's prereg.json by test_routing.py too.
REHEARSAL_CAP = routing.load_table()["caps"][labels4.REHEARSAL]["events_per_half_cell"]
FAKE_TOKEN = "FAKE-TOKEN-in-memory-0000"            # never a real token
FAKE_EMAIL = "fake.account@example.invalid"         # never a real address
MASK_MARK = "[masked]"
WAIT_S = 10.0   # a hang detector for the barrier and ordering events, never a timing assumption


def test_table() -> dict:
    t = copy.deepcopy(routing.load_table())
    t["pin_profiles"] = copy.deepcopy(PROFILES)
    t["pin_profiles_status"] = "RULED (TEST-ONLY): two injected profiles"
    t["spend_cap_markers_status"] = f"RULED (TEST-ONLY): {HARNESS}'s spend-cap list, opened for the tests (item 1)"
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
                api_errors=[], counters={"oom_kill_delta": 0, "pids_max_delta": 0}, started_at=1.0, ended_at=2.0,
                agent_output=True)
    base.update(kw)
    return aa.TurnResult(**base)


def _box(**kw):
    """Every box record, explicitly: harness_records defaults none of them."""
    b = {"preflight_ok": True, "container_started": True, "container_exited": False, "sidecar": dict(SIDECAR),
         "unexplained_operator_diffs": 0, "checker_reasons": [], "quiescence_kill": False,
         "outside_reach_events": 0, "finalize_abort": False, "committed": False,
         "unreadable_consequential": [], "quiescence_cap_survivors": 0}
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
# W1B3-1: a driver that raises after the agent's first turn ran (the harness cannot go on): no records reach the loop,
# yet the agent did act, so the take is never re-driven without a ruling.
RAISES_AFTER_FIRST_TURN = "driver-raises-after-first-turn"
RAISES_AFTER = {RAISES_AFTER_FIRST_TURN: [_turn(), _turn()]}
# Pre-freeze review 1, MAJOR 8 (lane pf1-l2a): THE RULING RULE refuses a rehearsal ruling after the agent's first turn,
# so the rehearsal rulings below rule on a take blocked before it (one silent turn, an unlisted reason); so do the
# re-run, pause and harness-error rulings, which after the first turn need a harness-fault row (the Lane-orchestrator's
# ruling 2 on the lane, 24 Oct 2026).
ALL["unlisted-reason-before"] = ([_turn(exit_code=1, end_reason=labels4.END_ERROR, agent_output=False)],
                                 _box(checker_reasons=["not-in-routing-json"]))


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
        # B19-8, the equal-duration model (batch.py's rolling window): a FakeDriver given no finish_after sets
        # `equal`; then a wave's drives end together, its head first (the others wait until the head's commit has
        # begun), and that commit waits until every drive step the loop holds open has finished (B19-13: its future
        # is done, read from the loop itself, never a sleep), so the loop's tie rule sees the whole wave finished, as
        # test_batch_rolling's EqualRepo does.
        self.equal = False
        self.heads = {}                      # block -> its first registration (slot, attempt): the wave's head
        self.in_flight = 0
        self.idle = threading.Condition(self.lock)
        self._begun = collections.defaultdict(threading.Event)

    def commit_begun(self, slot, attempt) -> None:
        self._begun[(slot, attempt)].set()

    def wait_head(self, block, slot, wait_s) -> None:
        """A drive that is not its wave's head ends only after the head's commit has begun (the equal model). A wave
        holds each slot once, so the slot names the drive (a driver's own attempt count can differ after a restart)."""
        head = self.heads.get(block)
        if head is not None and head[0] != slot and not self._begun[head].wait(wait_s):
            raise RuntimeError(f"the wave's head {head} was never committed (hang detector)")

    def wait_wave(self, wait_s) -> None:
        """The equal model's commit: every future in the committing loop's `open` deque is done (B19-13)."""
        if not self.equal:
            return
        wait_open(committing_loop(), wait_s)

    def log(self, *e):
        with self.lock:
            if e[0] == "register":
                if not self._registering:
                    self.block += 1
                    self.heads[self.block] = (e[1], e[2])
                self._registering = True
            else:
                self._registering = False
            if e[0] == "launch":
                self.launches[self.block] += 1
            self.events.append((len(self.events),) + e)


def committing_loop():
    """The batch loop whose commit is on this thread's stack: the fakes are handed no loop, and every loop of these
    tests (batch.Batch, a subclass, or a witness compiled from batch.py) commits from its own methods."""
    frame = sys._getframe(1)
    while frame is not None:
        me = frame.f_locals.get("self")
        if isinstance(getattr(me, "open", None), collections.deque) and hasattr(me, "_commit_finished"):
            return me
        frame = frame.f_back
    raise RuntimeError("no batch loop is committing on this thread")


def wait_open(loop, wait_s) -> None:
    """Until every drive step `loop` holds open has finished (its future done), under the hang detector (B19-13)."""
    _, running = concurrent.futures.wait([f for *_, f in loop.open], wait_s)
    if running:
        raise RuntimeError("a drive never ended (hang detector)")


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
        self._block_of = {}
        if not self.finish_after:
            world.equal = True               # B19-8: the equal-duration model (World)

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
        self._block_of[row["slot"]] = self.world.block   # B19-8: the wave a drive belongs to, read at its launch
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
            block = self._block_of.get(row["slot"], self.world.block)
            barrier = self._barriers.setdefault(block, threading.Barrier(self.world.launches[block]))
        with self.world.lock:
            self.world.in_flight += 1
        self.world.log("drive-start", row["slot"], attempt)
        try:
            barrier.wait(self.wait_s)        # every drive of the block is in flight at once
            after = self.finish_after.get(row["slot"]) if attempt == 1 else None
            if after is not None and not self._done[after].wait(self.wait_s):
                raise RuntimeError(f"slot {after} never finished")
            if self.world.equal:             # B19-8: the wave ends together, its head first
                self.world.wait_head(block, row["slot"], self.wait_s)
            name = self.plan.get((row["slot"], attempt), "clean")
            if name in RAISES_AFTER:                # the first turn runs, then the driver raises
                adapter = aa.ScriptedAdapter(RAISES_AFTER[name], container_id=cid)
                adapter.start_take(row)
                first = adapter.turn("line 0", first=True, budget_s=1)
                self.world.texts[(row["slot"], attempt)] = first.text
                raise RuntimeError("scripted driver failure after the agent's first turn")
            if ALL[name] is None:
                raise RuntimeError("scripted driver failure")
            turns, box = ALL[name]
            adapter = aa.ScriptedAdapter(turns, container_id=cid)
            adapter.start_take(row)
            results = [adapter.turn(f"line {i}", first=(i == 0), budget_s=1) for i in range(len(turns))]
            adapter.end_take()
            self.world.texts[(row["slot"], attempt)] = "\n".join(r.text for r in results)
            harness = row["agent"]["harness"]
            pin = self.pins.get(row["slot"], dict(PROFILES[harness][row["model"]], model=row["model"], harness=harness))
            records = aa.harness_records(results, pin=pin, box=box)
            edit = self.records_edit.get(row["slot"])
            if edit:
                edit(records)
            return records
        finally:
            with self._lock:
                self.in_flight -= 1
            self.world.log("drive-end", row["slot"], attempt)
            with self.world.lock:
                self.world.in_flight -= 1
                self.world.idle.notify_all()
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

    def __init_subclass__(cls, **kw):
        """B19-8: a subclass's own commit_records still signals the equal model's head, even when it raises first."""
        super().__init_subclass__(**kw)
        own = cls.__dict__.get("commit_records")
        if own is not None:
            def commit_records(self, row, attempt, outcome, _own=own):
                self.world.commit_begun(row["slot"], attempt)
                return _own(self, row, attempt, outcome)
            cls.commit_records = commit_records

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
        self.world.commit_begun(row["slot"], attempt)
        self.world.wait_wave(WAIT_S)          # B19-8: the equal model (World); no wait otherwise
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


def agent_of(model) -> dict:
    """A registered row's agent (interface 8): its harness, and its model's profile version (a made-up one for a model
    with no profile, which the row check refuses on its model)."""
    return {"harness": HARNESS, "version": PROFILES[HARNESS].get(model, {}).get("version", "0.0.0-no-profile")}


def rows(n, half_cell="hc-a", model=PIN["model"]):
    return [{"slot": i, "half_cell": half_cell, "row_id": i, "model": model, "agent": agent_of(model)}
            for i in range(1, n + 1)]


def row(slot, half_cell, model=PIN["model"]):
    return {"slot": slot, "half_cell": half_cell, "row_id": slot, "model": model, "agent": agent_of(model)}


def rows_in(cells: list[str]) -> list[dict]:
    """Slots 1..n, slot i in the half-cell cells[i - 1]."""
    return [row(i, hc) for i, hc in enumerate(cells, 1)]


def closed_state():
    """labels4's cell state at a cap (glitch-f3's ruling), never retyped here; a visible stand-in when it is missing."""
    return getattr(labels4, "INCOMPLETE_MECHANICAL", "(labels4 has no INCOMPLETE_MECHANICAL)")


def run(n, plan=None, serial=False, cls=batch.Batch, table=None, row_list=None, batch_kw=None, **driver_kw):
    w = World()
    d, r, win = FakeDriver(w, plan, **driver_kw), FakeRepo(w), FakeWindow(w)
    b = cls(d, r, win, table=table or test_table(), serial=serial, **(batch_kw or {}))
    out = b.run(row_list or rows(n))
    return b, out, w, d, r, win


def restart(prev_repo, row_list, plan=None, start_attempts=None, cls=batch.Batch, table=None, serial=False,
            window_cls=None, rulings=(), refusal=None, **driver_kw):
    """W1B2-3: a new process after a stop. A new driver, window and loop; the repo holds every outcome
    committed before (its history), and the loop is handed nothing else. `rulings` are committed to the repo after
    the stop, by a human (W1B3-1: batch never writes one)."""
    w = World()
    d = FakeDriver(w, plan, start_attempts=start_attempts, **driver_kw)
    prior = prev_repo.history() + [copy.deepcopy(x) for x in rulings]
    r, win = FakeRepo(w, prior=prior), (window_cls or FakeWindow)(w)
    if refusal is not None:           # the closure review of 898e598c: the driver's refusal record, as the repo reads it
        r.driver_refusal_record = refusal
    b = cls(d, r, win, table=table or test_table(), serial=serial)
    out = b.run(row_list)
    return b, out, w, d, r, win


def history_problems(history) -> list[str]:
    """No (slot, attempt) committed twice, and no re-run spent past a cap, across every run (W1B2-3)."""
    p = []
    t = test_table()
    history = [o for o in history if "state" in o]   # the outcomes (a ruling is no outcome, W1B3-1)
    pairs = collections.Counter((o["slot"], o["attempt"]) for o in history)
    p += [f"slot {s} attempt {a} committed {n} times" for (s, a), n in sorted(pairs.items()) if n > 1]
    for route in (labels4.REHEARSAL, labels4.HARNESS_ERROR, labels4.PAUSE):
        cap = t["caps"][route]
        cells = collections.Counter(o["half_cell"] for o in history if o["state"] == route and o["rerun"])
        slots = collections.Counter(o["slot"] for o in history if o["state"] == route and o["rerun"])
        per_cell = batch.half_cell_cap(t, route)
        if per_cell is not None and route == labels4.PAUSE:
            # W1B3-5 (glitch-f3's ruling): pauses that share one reset are one usage-window event; at most cap-1 of a
            # half-cell's window events are re-run, however many takes paused in each
            events = collections.defaultdict(set)
            for o in history:
                if o["state"] == route and o["rerun"]:
                    events[o["half_cell"]].add(o.get("window_event"))
            p += [f"{route}: {len(ev)} re-run window events in half-cell {hc}, at most {per_cell - 1}"
                  for hc, ev in events.items() if len(ev) > per_cell - 1]
        elif per_cell is not None:
            # events_per_half_cell (rehearsal, pause) counts the route's outcomes, so at most cap-1 are re-run;
            # reruns_per_half_cell (harness-error) counts the re-runs themselves
            most = per_cell - 1 if batch.half_cell_key(route) == "events_per_half_cell" else per_cell
            p += [f"{route}: {n} re-runs in half-cell {hc}, at most {most}"
                  for hc, n in cells.items() if n > most]
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
    # 1. the per-slot harness-error cap: slot 1's harness-error was granted its one re-run, and slot 2, blocked,
    #    stopped the loop (W1B3-1: the stop comes from a sibling, since a blocked slot is never re-driven without a
    #    ruling); on restart slot 1's re-run meets a harness-error again, final beyond the cap, never a second re-run.
    _, _, _, _, r1, _ = run(2, plan={(1, 1): he, (2, 1): blocked})
    try:
        b, out, *_ , r2, _ = restart(r1, rows(1), plan={(1, 2): he}, start_attempts={1: 1}, cls=cls)
        got = [(o["slot"], o["attempt"], o["state"], o["rerun"], o["final"]) for o in out]
        if got != [(1, 2, labels4.HARNESS_ERROR, False, True)]:
            p.append(f"slot cap: the restart committed {got}")
        p += [f"slot cap: {x}" for x in history_problems(r2.history())]
    except Exception as e:  # noqa: BLE001
        p.append(f"slot cap: the restart raised {type(e).__name__}: {e}")
    # 2. the per-half-cell harness-error cap: slots 1 and 2 spent both re-runs, slot 3 was blocked (and is left out:
    #    W1B3-1); on restart a new slot of the half-cell, slot 4, meets a harness-error, final beyond the cap.
    _, _, _, _, r1, _ = run(3, plan={(1, 1): he, (2, 1): he, (3, 1): blocked})
    try:
        b, out, *_, r2, _ = restart(r1, [r for r in rows(4) if r["slot"] != 3], plan={(4, 1): he},
                                    start_attempts={1: 1, 2: 1}, cls=cls)
        got = [(o["slot"], o["attempt"], o["state"], o["rerun"]) for o in out]
        want = [(1, 2, labels4.GRADED, False), (2, 2, labels4.GRADED, False), (4, 1, labels4.HARNESS_ERROR, False)]
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
    # 4. a half-cell closed at its rehearsal cap (glitch-f3's cap ruling): the restart registers nothing for it, its
    #    capped slot and its unstarted slot alike, and runs another half-cell's row.
    _, _, _, _, r1, _ = run(1, plan={(1, a): "preflight-fail" for a in range(1, 10)}, serial=True)
    try:
        b, out, w, *_ = restart(r1, [row(1, "hc-a"), row(2, "hc-a"), row(3, "hc-b")],
                                start_attempts={1: REHEARSAL_CAP}, cls=cls)
        regs = [(e[2], e[3]) for e in kinds(w.events, "register")]
        if regs != [(3, 1)] or [(o["slot"], o["state"]) for o in out] != [(3, labels4.GRADED)]:
            p.append(f"capped cell: the restart registered {regs} and committed "
                     f"{[(o['slot'], o['attempt'], o['state']) for o in out]}")
    except Exception as e:  # noqa: BLE001
        p.append(f"capped cell: the restart raised {type(e).__name__}: {e}")
    # 5. a slot re-registered under another half-cell is refused (its caps would be counted in the wrong cell): slot 1
    #    owes its harness-error re-run, slot 2 (blocked) stopped the loop.
    _, _, _, _, r1, _ = run(2, plan={(1, 1): he, (2, 1): blocked})
    try:
        b, out, *_ = restart(r1, rows(1, half_cell="hc-other"), cls=cls)
        p.append(f"moved slot: the restart drove it under another half-cell ({[(o['attempt'], o['state']) for o in out]})")
    except batch.BatchConfigError as e:
        if "committed under half-cell" not in str(e):
            p.append(f"moved slot: refused for another reason: {e}")
    return p


def restart_pause_problems(cls=batch.Batch) -> list[str]:
    """W1B2-3 (lane w1b's decision): a restart after a pause launches nothing before the usage window resets."""
    _, _, _, _, r1, _ = run(1, plan={(1, a): "rate-limit" for a in range(1, 10)})
    # slot 1's half-cell closed at its pause cap (glitch-f3's cap ruling), so the restart drives another half-cell
    b, out, w, d, r2, win = restart(r1, [row(2, "hc-b")], cls=cls)
    seq = [e[1] for e in w.events]
    if "reset" not in seq or "launch" not in seq or seq.index("reset") > seq.index("launch"):
        return [f"the restart launched before the window reset: {seq}"]
    return []


def capped_history() -> list[dict]:
    """The committed outcomes of a half-cell closed at its pause cap: slot 1 pauses on every attempt."""
    _, _, _, _, r, _ = run(1, plan={(1, a): "rate-limit" for a in range(1, 10)})
    return r.history()


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
    # glitch-f3's cap ruling: the committed cell state is the record a restart closes a half-cell from, so it must
    # agree with the counts it is rebuilt beside.
    capped = capped_history()
    shut = len(capped) - 1                                  # the take that brought hc-a's pauses to the cap
    bad.update({
        "a cell state that is not labels4's": [dict(o, cell_state="incomplete") if i == shut else o
                                               for i, o in enumerate(capped)],
        "a cell state that is not labels4's, below the cap": [dict(o, cell_state="incomplete", cell_reason="early")
                                                              if i == 0 else o for i, o in enumerate(capped)],
        "a cell state without its reason": [dict(o, cell_reason=None) if i == shut else o for i, o in enumerate(capped)],
        "a half-cell at its cap without its committed state": [dict(o, cell_state=None, cell_reason=None) if i == shut
                                                               else o for i, o in enumerate(capped)],
        "a committed cell state below the cap": [dict(o, cell_state=closed_state(), cell_reason="early") if i == 0
                                                 else o for i, o in enumerate(capped)],
        "a re-run in a closed half-cell": capped + [dict(copy.deepcopy(capped[shut]), slot=9, attempt=1, final=False,
                                                         rerun=True, beyond_cap=False)],
    })
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
    # Review round 3: the rulings (W1B3-1), the drive's start (W1B3-1) and the window events (W1B3-5) sit in the
    # history too, each checked; every one of these is refused for its own reason, named by a fragment of the refusal.
    for name, (hist, why) in fold4_bad_histories().items():
        class Repo(FakeRepo):
            def history(self, _h=hist):
                return copy.deepcopy(_h)
        w = World()
        try:
            cls(FakeDriver(w), Repo(w), FakeWindow(w), table=test_table())
            p.append(f"{name}: accepted")
        except batch.BatchConfigError as e:
            if why not in str(e):
                p.append(f"{name}: refused, but not for {why!r} ({e})")
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


def rolling_order_problems(events) -> list[str]:
    """B19-5, with unequal durations (batch.py's rolling window): records commit in registration order, each after
    its own drive ended, and every row is registered before its launch."""
    p = []
    seq = [e[1:] for e in events]
    regs = [(e[1], e[2]) for e in seq if e[0] == "register"]
    commits = [(e[1], e[2]) for e in seq if e[0] == "commit"]
    if commits != regs[:len(commits)]:
        p.append(f"records committed as {commits}, registered as {regs}")
    ends, reg_at, launch_at = set(), collections.defaultdict(list), collections.defaultdict(list)
    for k, e in enumerate(seq):
        if e[0] == "drive-end":
            ends.add((e[1], e[2]))
        elif e[0] == "register":
            reg_at[e[1]].append(k)
        elif e[0] in ("launch", "launch-failed"):
            launch_at[e[1]].append(k)
        elif e[0] == "commit" and (e[1], e[2]) not in ends:
            p.append(f"slot {e[1]} attempt {e[2]} committed before its drive ended")
    for slot, ks in launch_at.items():
        for n, k in enumerate(ks):
            if n >= len(reg_at[slot]) or reg_at[slot][n] > k:
                p.append(f"slot {slot}'s launch {n + 1} came before its registration")
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
        "pause cap pending": lambda t: t["caps"][labels4.PAUSE].update(events_per_half_cell=None),
        "operator_reasons empty": lambda t: t.update(operator_reasons=[]),
        "operator_reasons_status PENDING": lambda t: t.update(operator_reasons_status="PENDING: not read"),
        "pin_profiles empty": lambda t: t.update(pin_profiles={}),
        "pin_profiles_status PENDING": lambda t: t.update(pin_profiles_status="PENDING (CP5)"),
        "rate_limit_markers_status PENDING": lambda t: t.update(rate_limit_markers_status="PENDING: not ruled"),
        "rate_limit_markers_status missing": lambda t: t.pop("rate_limit_markers_status"),
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
    def test_real_table_starts_and_refuses_without_its_pins(self):
        # CP5 (Javier, "CP5: all as recommended", 14 Oct 2026): arm A's pins are registered and their status ruled, so
        # the real routing.json starts; the same table with its pins taken back refuses on the pins alone. Round 3's
        # reasons and pause cap are filled (Javier's "gap4 routing: A") and the markers ruled (glitch-f3, W1B2-6).
        self.assertEqual(batch.start_problems(routing.load_table()), [])
        batch.Batch(None, None, None, history=[])   # the real routing.json
        unpinned = routing.load_table()
        unpinned.update(pin_profiles={}, pin_profiles_status="PENDING (CP5)")
        with self.assertRaises(batch.BatchConfigError) as cm:
            batch.Batch(None, None, None, table=unpinned, history=[])
        self.assertIn("pin_profiles", str(cm.exception))
        for filled in ("pause", "operator_reasons", "rate_limit", "spend_cap"):
            self.assertNotIn(filled, str(cm.exception))

    def test_gate_refuses_pending_data(self):
        self.assertEqual(gate_problems(), [])

    def test_gate_check_can_fail(self):
        def caps_only(table):   # the pre-fold gate: the caps alone
            return [f"cap {r}" for r in batch.pending_caps(table)]
        with mock.patch.object(batch, "start_problems", caps_only):
            self.assertEqual(len(gate_problems()), 6)
        real = batch.start_problems

        def ignores_the_markers(table):   # W1B2-6's mutant: the markers' ruling not gated
            return [x for x in real(table) if "rate_limit_markers_status" not in x]
        with mock.patch.object(batch, "start_problems", ignores_the_markers):
            self.assertEqual(sorted(gate_problems()), ["rate_limit_markers_status PENDING: the loop would start",
                                                       "rate_limit_markers_status missing: the loop would start"])

    def test_check_cli_exits_1_while_pending(self):
        with redirect_stdout(io.StringIO()) as real:   # CP5: the real routing.json is ready
            self.assertEqual(batch.main(["--check"]), 0)
        self.assertEqual(real.getvalue().splitlines(), ["batch: routing.json ready"])
        unpinned = routing.load_table()
        unpinned.update(pin_profiles={}, pin_profiles_status="PENDING (CP5)")
        buf = io.StringIO()
        with mock.patch.object(routing, "load_table", lambda *a: copy.deepcopy(unpinned)), redirect_stdout(buf):
            self.assertEqual(batch.main(["--check"]), 1)
        for what in ("pin_profiles", "pin_profiles_status"):
            self.assertIn(what, buf.getvalue())
        for filled in ("pause", "operator_reasons", "rate_limit"):   # filled, or ruled (W1B2-6)
            self.assertNotIn(filled, buf.getvalue())
        self.assertTrue(all("pin_profiles" in x or "spend_cap_markers_status" in x   # + item 1, w4h (see its report)
                            for x in buf.getvalue().splitlines()), buf.getvalue())
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


class TestDeferredArm(unittest.TestCase):
    """Lane gemini-defer, ruling R5 (glitch-f1, 22 Oct 2026): a row of an arm in the frozen deferred_arms is refused by
    name unless a committed go record exists (prereg.GO_KEYS, modelled on costs.py's "caps trimmed" record)."""

    def design(self):
        import prereg
        d = copy.deepcopy(prereg.load())
        d["deferred_arms"] = {"G": {"status": "deferred", "by": "Javier", "models": [PIN["model"]],
                                    "words": "Javier's reply \"gemini-defer yes\", Thu 22 Oct 2026 09:19:59 EDT"}}
        d["models"] = dict(d["models"], G=["gemini-3.8-flash", "gemini-3.5-flash-lite"])
        return d

    def go(self, **changes):
        return dict({"kind": "deferred arm go", "arm": "G", "by": "Javier", "decision": "OD-synthetic",
                     "ask": "synthetic-go", "at": "2026-12-01T14:00:00Z"}, **changes)

    def held(self, records, row_list):
        import prereg
        d = self.design()
        with mock.patch.object(prereg, "load", lambda: d), \
                mock.patch.object(prereg, "committed_go_records", lambda *a: list(records)):
            return run(1, row_list=row_list)

    def test_a_deferred_arms_row_is_refused_by_name(self):
        g_row = [dict(r, arm="G") for r in rows(2)]
        for records in ([], [self.go(by="glitch-f1")], [self.go(arm="O")], [self.go(kind="caps trimmed")],
                        [dict(self.go(), extra=1)]):
            with self.subTest(records=records), \
                    self.assertRaisesRegex(batch.BatchConfigError,
                                           r"row 1: arm G is deferred \(Javier, 22 Oct 2026\) in the frozen "
                                           r"deferred_arms, and no committed 'deferred arm go' record"):
                self.held(records, g_row)
        # by its registered model too, when a row names no arm
        gemini = [dict(r, model="gemini-3.8-flash") for r in rows(1)]
        with self.assertRaisesRegex(batch.BatchConfigError, r"row 1: arm G is deferred"):
            self.held([], gemini)

    def test_a_committed_go_lets_the_row_run(self):
        b, out, *_ = self.held([self.go()], [dict(r, arm="G") for r in rows(2)])
        self.assertEqual(len(out), 2)

    def test_other_arms_and_an_undeferred_design_run(self):
        b, out, *_ = self.held([], [dict(r, arm="A") for r in rows(2)])
        self.assertEqual(len(out), 2)
        import prereg
        undeferred = {k: v for k, v in self.design().items() if k != "deferred_arms"}
        with mock.patch.object(prereg, "load", lambda: undeferred), \
                mock.patch.object(prereg, "committed_go_records", lambda *a: self.fail("read with nothing deferred")):
            b, out, *_ = run(1, row_list=[dict(r, arm="G") for r in rows(2)])
        self.assertEqual(len(out), 2)

    def test_the_repo_supplies_its_go_records_and_only_a_deferred_row_reads_them(self):
        import prereg
        d, reads = self.design(), []
        class GoRepo(FakeRepo):
            def deferred_go_records(inner):
                reads.append(1)
                return [self.go()]
        with mock.patch.object(prereg, "load", lambda: d), \
                mock.patch.object(prereg, "committed_go_records", lambda *a: self.fail("the repo offers its own")):
            w = World()
            b = batch.Batch(FakeDriver(w, None), GoRepo(w), FakeWindow(w), table=test_table())
            self.assertEqual(b.row_problems([dict(r, arm="A") for r in rows(2)]), [])
            self.assertEqual(reads, [])
            self.assertEqual(b.row_problems([dict(r, arm="G") for r in rows(2)]), [])
            self.assertEqual(reads, [1])

    def test_the_deferral_is_asked_once_per_row(self):
        # review NIT-4: row_problems calls deferral_problem once per row, refused or not
        import prereg
        d, calls = self.design(), []
        with mock.patch.object(prereg, "load", lambda: d), \
                mock.patch.object(prereg, "committed_go_records", lambda *a: []):
            w = World()
            b = batch.Batch(FakeDriver(w, None), FakeRepo(w), FakeWindow(w), table=test_table())
            ask = b.deferral_problem
            b.deferral_problem = lambda r: calls.append(r["slot"]) or ask(r)
            got = b.row_problems([dict(r, arm="G") for r in rows(2)] + [dict(r, arm="A") for r in rows(3)[2:]])
        self.assertEqual(len(got), 2)
        self.assertTrue(all("arm G is deferred" in p for p in got))
        self.assertEqual(sorted(calls), sorted({r["slot"] for r in rows(3)}))
        self.assertEqual(len(calls), 3)


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
    """W1B3-1 (glitch-f3 accepted the brief's fix as written, 6 Oct 2026): remove() raising for slot 2's container
    after its take routed graded keeps the take graded and final, with its decision and annotations, and
    leaked_container naming the recorded id; it never becomes `failed`. Every take of the block commits in row order,
    and the loop stops after the block (the rows after it are never launched), the stop committed with the record. A
    restart refuses the slot as final. A leak after a rehearsal keeps its re-run, which a restart then drives."""
    p = []
    b, out, w, d, r, _ = run(6, remove_fails={2}, cls=cls)
    p += container_problems(b, d)
    two = r.snapshot(2)
    if (two["state"], two["final"], two["rerun"]) != (labels4.GRADED, True, False):
        p.append(f"the leaked take was committed {two['state']} (final {two['final']}, rerun {two['rerun']}), want its "
                 f"route, graded and final")
    if two["leaked_container"] != b.containers.get((2, 1)) or "leaked" not in (two["reason"] or ""):
        p.append(f"the leak is not recorded with its id: {two['leaked_container']}, {two['reason']}")
    if not two["decision"] or two["decision"]["route"] != labels4.GRADED or two["events"] != []:
        p.append("the take's routing and annotations were lost with the container")
    if "leaked" not in (two["stop"] or ""):
        p.append(f"the leak's stop was not committed with the record: {two['stop']!r}")
    commits = [(e[2], e[3]) for e in kinds(w.events, "commit")]
    if commits != [(1, 1), (2, 1), (3, 1)] or len(d.launched) != 3:
        p.append(f"the loop did not stop after the block: commits {commits}, {len(d.launched)} launches")
    if [(o["slot"], o["state"]) for o in out] != [(1, labels4.GRADED), (2, labels4.GRADED), (3, labels4.GRADED)]:
        p.append(f"the block committed {[(o['slot'], o['state']) for o in out]}")
    if not b.stopped or "leaked" not in (b.stopped["reason"] or ""):
        p.append(f"the loop's stop does not name the leak: {b.stopped}")
    try:
        restart(r, [x for x in rows(2) if x["slot"] == 2], cls=cls)
        p.append("the leaked graded slot was driven again on a restart")
    except batch.BatchConfigError as e:
        if "final" not in str(e):
            p.append(f"the leaked graded slot was refused for another reason: {e}")
    b, out, w, d, r, _ = run(2, plan={(1, 1): "preflight-fail"}, remove_fails={1}, cls=cls)
    one = r.snapshot(1)
    if (one["state"], one["rerun"], one["leaked_container"] is not None) != (labels4.REHEARSAL, True, True):
        p.append(f"a leak after a rehearsal committed {one['state']} (rerun {one['rerun']}, leaked "
                 f"{one['leaked_container']})")
    try:
        b2, out2, *_ = restart(r, rows(1), start_attempts={1: 1}, cls=cls)
        if [(o["slot"], o["attempt"], o["state"]) for o in out2] != [(1, 2, labels4.GRADED)]:
            p.append(f"the leaked rehearsal's re-run on a restart: {[(o['slot'], o['attempt'], o['state']) for o in out2]}")
    except Exception as e:  # noqa: BLE001
        p.append(f"the leaked rehearsal's re-run on a restart raised {type(e).__name__}: {e}")
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


def _annotate_raises_on_slot_2(records, table):
    if records["exit"]["exec_codes"] == [0, 0, 0]:
        raise ValueError("annotations unreadable")
    return routing.annotate(records, table)


def unreadable_annotation_problems(cls=batch.Batch) -> list[str]:
    """Slot 2 routes graded, but its annotations cannot be read: it is committed masked, fail-closed."""
    b, out, w, d, r, _ = run(3, records_edit={2: _three_turns}, batch_kw={"annotate_fn": _annotate_raises_on_slot_2},
                             cls=cls)
    two = r.snapshot(2)
    if (two["state"], two["mask"], two["events"]) != (labels4.GRADED, True, None) or "fail-closed" not in two["mask_basis"]:
        return [f"slot 2 committed {two['state']} with mask={two['mask']}, events={two['events']} ({two['mask_basis']})"]
    return []


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
        "a launch failed, nothing created (failed)": dict(launch_fails={2: "none"}),
        "the driver raised after the first turn (failed)": dict(plan={(2, 1): RAISES_AFTER_FIRST_TURN}),
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

    def test_unreadable_annotations_mask_a_routed_take(self):
        """W1B-1: a take routing graded whose annotations cannot be read is masked fail-closed, events None."""
        self.assertEqual(unreadable_annotation_problems(), [])

    def test_unreadable_annotations_check_can_fail(self):
        class Open(batch.Batch):              # the review's mutant: unreadable annotations leave the text open
            def _annotations(self, records):
                out = super()._annotations(records)
                return dict(out, mask=False) if out["mask_basis"] != "annotations" else out
        self.assertNotEqual(unreadable_annotation_problems(Open), [])

    def test_fail_closed_check_can_fail(self):
        class NoSeal(batch.Batch):            # the pre-fold commit: the mask only from the annotations
            @staticmethod
            def _seal(outcome):
                return None
        found = fail_closed_problems(NoSeal)
        for road in ("unlisted checker reason", "the driver's pin", "routing raised"):
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
    # glitch-f3's cap ruling: the take that brings its half-cell's rehearsals (or pauses) to the cap is the slot's
    # last, committed with the cell state; the loop goes on (no stop)
    for route, scenario, cap in ((labels4.REHEARSAL, "preflight-fail", REHEARSAL_CAP),
                                 (labels4.PAUSE, "rate-limit", PAUSE_CAP)):
        b, out, w, d, r, _ = run(2, plan={(1, a): scenario for a in range(1, 10)}, serial=True, cls=cls)
        last = r.snapshot(1, cap)
        got = (last["final"], last["rerun"], last["beyond_cap"], last["stop"], last.get("cell_state"))
        if got != (True, False, True, None, closed_state()) or not last.get("cell_reason"):
            p.append(f"{route} reaching its cap committed as {got} ({last.get('cell_reason')!r})")
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
        # Later rows finish first; their records still commit after, in row order. B19-5: with unequal durations the
        # freed drive lanes are filled while slot 1 runs (batch.py's rolling window), so the order is checked over
        # the whole run, not per block (commit_order_problems keeps the equal-duration blocks).
        b, out, w, d, r, _ = run(7, finish_after={1: 2, 2: 3, 4: 5, 5: 6})
        self.assertEqual(rolling_order_problems(w.events), [])
        self.assertEqual(r.overlaps, 0)
        self.assertEqual([o["slot"] for o in out], [1, 2, 3, 4, 5, 6, 7])
        ends = [e[2] for e in kinds(w.events, "drive-end")]
        self.assertEqual(ends[:3], [3, 2, 1])            # the drives really did finish out of row order
        self.assertLess(ends.index(6), ends.index(5))
        self.assertLess(ends.index(5), ends.index(4))
        commits = [i for i, e in enumerate(w.events) if e[1] == "commit"]
        mutated = list(w.events)                          # the rolling check can fail
        mutated[commits[0]], mutated[commits[1]] = mutated[commits[1]], mutated[commits[0]]
        self.assertNotEqual(rolling_order_problems(mutated), [])
        early = [e for e in w.events if e[1] != "commit"]
        early.insert(next(i for i, e in enumerate(early) if e[1] == "drive-start"), w.events[commits[0]])
        self.assertNotEqual(rolling_order_problems(early), [])

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
        """glitch-f3's cap ruling: the half-cell's third pause is its last; it closes `incomplete — mechanical`."""
        plan = {(1, a): "rate-limit" for a in range(1, 10)}
        b, out, w, *_ = run(1, plan=plan)
        self.assertEqual(len(out), PAUSE_CAP)
        self.assertEqual((out[-1]["final"], out[-1]["rerun"], out[-1]["beyond_cap"]), (True, False, True))
        self.assertEqual(out[-1].get("cell_state"), closed_state())
        self.assertIsNone(b.stopped)   # never a stop for a human


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
        # Live harness step 4: three harness-errors in one night now stop the run for a ruling (the registered
        # nightly stop), so the two granted re-runs are read from the committed fates, not from their drives.
        reruns = [o for o in out if o["attempt"] == 1 and o["rerun"]]
        self.assertEqual(sorted(o["slot"] for o in reruns), [1, 2])
        self.assertTrue(next(o for o in out if o["slot"] == 3)["beyond_cap"])
        # Step-4 review nit 4: after a committed night ruling the granted re-runs drive, and the cap still holds.
        ruling = {"kind": batch.NIGHT_RULING, "slot": b.night_reaching[0], "attempt": b.night_reaching[1],
                  "by": "test-ruler"}
        first_repo = _[2]
        b2, out2, *_ = restart(first_repo, rows(2), rulings=[ruling])
        self.assertEqual(sorted((o["slot"], o["attempt"]) for o in out2), [(1, 2), (2, 2)])
        self.assertEqual(history_problems(first_repo.history() + out2), [])

    def test_rehearsal_cap_three_per_half_cell_then_the_half_cell_closes(self):
        """glitch-f3's cap ruling: three rehearsals in a half-cell, then nothing more is registered for it; another
        half-cell's row still runs."""
        plan = {(1, a): "preflight-fail" for a in range(1, 10)}
        b, out, w, *_ = run(0, plan=plan, serial=True, row_list=rows_in(["hc-a", "hc-a", "hc-b"]))
        self.assertEqual([o["state"] for o in out if o["slot"] == 1], [labels4.REHEARSAL] * REHEARSAL_CAP)
        self.assertIsNone(b.stopped)
        self.assertNotIn(2, [e[2] for e in kinds(w.events, "register")])   # the closed half-cell's other slot
        self.assertEqual([(o["slot"], o["state"]) for o in out if o["slot"] != 1], [(3, labels4.GRADED)])

    def test_cap_checks_can_fail(self):
        t = test_table()
        t["caps"][labels4.HARNESS_ERROR]["reruns_per_slot"] = 5
        b, out, *_ = run(1, plan={(1, a): "watcher-overflow" for a in (1, 2, 3)}, table=t)
        self.assertNotEqual([o["state"] for o in out], [labels4.HARNESS_ERROR] * 2)

    def test_aborted_and_graded_never_rerun(self):
        b, out, *_ = run(3, plan={(1, 1): "oom"})
        self.assertEqual([(o["slot"], o["state"]) for o in out],
                         [(1, labels4.ABORTED), (2, labels4.GRADED), (3, labels4.GRADED)])


class RegisterFailsRepo(FakeRepo):
    """register() raises for `fail_slot` (say, a stale git index.lock)."""

    fail_slot = 2

    def register(self, row, attempt):
        if row["slot"] == self.fail_slot:
            raise OSError("git index.lock exists")
        super().register(row, attempt)


class WindowFails(FakeWindow):
    def wait_reset(self):
        self.resets += 1
        raise RuntimeError("usage window unreachable")


def repo_window_failure_problems(cls=batch.Batch) -> list[str]:
    """W1B2-5: register() raising on slot 2 of a block of three commits slot 1 (registered) as failed, masked,
    nothing launched; register() raising on the block's first row commits nothing; wait_reset() raising after a
    pause launches nothing more. Each time run() returns with `stopped` saying why, never raising."""
    p = []
    for fail_slot, want_failed in ((2, [1]), (1, [])):
        w = World()
        d, r, win = FakeDriver(w), RegisterFailsRepo(w), FakeWindow(w)
        r.fail_slot = fail_slot
        try:
            b = cls(d, r, win, table=test_table())
            out = b.run(rows(3))
        except Exception as e:  # noqa: BLE001
            p.append(f"register fails on slot {fail_slot}: run raised {type(e).__name__}: {e}")
            continue
        got = [(snap["slot"], snap["state"], snap["mask"], snap["container_id"]) for _, _, _, snap in r.passed]
        if got != [(s, labels4.FAILED, True, None) for s in want_failed]:
            p.append(f"register fails on slot {fail_slot}: committed {got}")
        if d.launched or kinds(w.events, "drive-start"):
            p.append(f"register fails on slot {fail_slot}: something was launched or driven")
        if not b.stopped or b.stopped["state"] != labels4.FAILED or "register failed" not in b.stopped["reason"]:
            p.append(f"register fails on slot {fail_slot}: stopped {b.stopped}")
        if [o["slot"] for o in out] != want_failed:
            p.append(f"register fails on slot {fail_slot}: outcomes {[o['slot'] for o in out]}")
    w = World()
    d, r, win = FakeDriver(w, {(2, 1): "rate-limit"}), FakeRepo(w), WindowFails(w)
    try:
        b = cls(d, r, win, table=test_table())
        out = b.run(rows(6))
    except Exception as e:  # noqa: BLE001
        return p + [f"wait_reset fails: run raised {type(e).__name__}: {e}"]
    if win.resets != 1 or len(d.launched) != 3:
        p.append(f"wait_reset fails: {win.resets} waits, {len(d.launched)} launches (want 1 and 3)")
    if not b.stopped or b.stopped["state"] != labels4.FAILED or "wait_reset failed" not in b.stopped["reason"]:
        p.append(f"wait_reset fails: stopped {b.stopped}")
    if [snap["state"] for _, _, _, snap in r.passed] != [labels4.GRADED, labels4.PAUSE, labels4.GRADED]:
        p.append(f"wait_reset fails: committed {[snap['state'] for _, _, _, snap in r.passed]}")
    return p


class TestRepoAndWindowFailures(unittest.TestCase):
    """W1B2-5: a register or wait_reset failure stops the loop with every registered row committed."""

    def test_register_and_wait_reset_failures(self):
        self.assertEqual(repo_window_failure_problems(), [])

    def test_register_and_wait_reset_check_can_fail(self):
        class Raises(batch.Batch):            # the pre-fold loop: the repo's and window's errors propagate
            def _register(self, block):
                for row, attempt in block:
                    self.repo.register(row, attempt)
                return True

            def _wait_window(self):
                self.window.wait_reset()
                return True

        class Forgets(batch.Batch):           # stops, but never commits the rows it had registered
            def _register(self, block):
                for row, attempt in block:
                    try:
                        self.repo.register(row, attempt)
                    except Exception as e:  # noqa: BLE001
                        self.stopped = {"slot": row["slot"], "attempt": attempt, "state": labels4.FAILED,
                                        "reason": f"register failed: {e}"}
                        return False
                return True
        found = repo_window_failure_problems(Raises)
        self.assertTrue(any("register fails on slot 2: run raised" in x for x in found), found)
        self.assertTrue(any("wait_reset fails: run raised" in x for x in found), found)
        found = repo_window_failure_problems(Forgets)
        self.assertIn("register fails on slot 2: committed []", found)

    def test_a_restart_after_a_register_failure_continues(self):
        w = World()
        r = RegisterFailsRepo(w)
        batch.Batch(FakeDriver(w), r, FakeWindow(w), table=test_table()).run(rows(3))
        b, out, *_ = restart(r, rows(3))
        self.assertEqual([(o["slot"], o["attempt"], o["state"]) for o in out],
                         [(1, 2, labels4.GRADED), (2, 1, labels4.GRADED), (3, 1, labels4.GRADED)])


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

        class DrivesClosedSlots(batch.Batch):  # a final slot is driven again
            def _replay(self, history):
                super()._replay(history)
                self.closed.clear()

        class ForgetsCells(batch.Batch):      # a slot's committed half-cell forgotten
            def _replay(self, history):
                super()._replay(history)
                self.slot_cell.clear()
        self.assertNotEqual(restart_problems(NoReplay), [])
        found = restart_problems(ForgetsReruns)
        self.assertTrue(any("slot cap" in x for x in found) and any("half-cell cap" in x for x in found), found)
        self.assertTrue(any("committed 2 times" in x for x in restart_problems(ForgetsAttempts)))
        found = restart_problems(DrivesClosedSlots)
        self.assertTrue(any("final slot" in x for x in found), found)
        self.assertTrue(any("capped cell" in x for x in restart_problems(ForgetsClosedCells)))   # glitch-f3's cap ruling
        self.assertTrue(any("moved slot" in x for x in restart_problems(ForgetsCells)))
        self.assertNotEqual(restart_pause_problems(ForgetsThePause), [])
        self.assertNotEqual(restart_pause_problems(NoReplay), [])

    def test_history_check_can_fail(self):
        class Trusting(batch.Batch):          # history read without its checks
            @staticmethod
            def history_problems(history, table=None):   # pf1-l2a: batch passes its table
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


# ------------------------------------------------- glitch-f3's rulings (6 Oct 2026): the cell caps
# Recorded as glitch-f3's in-plan rulings, never as the owner's. Round 3 counts the pauses (or rehearsals) of a
# cell, (task, half, model), and once the count reaches the cap registers nothing more for it, which publishes
# `incomplete — mechanical` (evals/gap-study-3/takes.py:280-291 at e2979b31). Round 4's half-cell is
# (arm, task, half, model), the row's `half_cell`; wording and repeat or pressure are the slot inside it.
ROUTE_SCENARIO = {labels4.PAUSE: "rate-limit", labels4.REHEARSAL: "preflight-fail"}
CELL_CAP = {labels4.PAUSE: PAUSE_CAP, labels4.REHEARSAL: REHEARSAL_CAP}


def _fields(o, *keys):
    return tuple(o.get(k) for k in keys)


def cell_cap_problems(route: str, cls=batch.Batch) -> list[str]:
    """Through Batch.run with the fake driver: a half-cell meets `route` until it reaches its cap. The take that
    brings the count to the cap is not re-run; it is committed with the cell state `incomplete — mechanical` and
    its reason before the loop moves on; nothing more is registered for that half-cell; the other half-cells' rows
    run and the loop never stops for a human; and a restart built from the repo's history keeps it closed."""
    p = []
    cap, scenario, closed = CELL_CAP[route], ROUTE_SCENARIO[route], closed_state()
    keys = ("final", "rerun", "beyond_cap", "stop", "cell_state")
    # 1. one at a time: slot 1 (hc-a) meets the route on every attempt; slots 2 and 3 are hc-b; slot 4 is hc-a's
    b, out, w, d, r, _ = run(0, plan={(1, a): scenario for a in range(1, 10)}, serial=True, cls=cls,
                             row_list=rows_in(["hc-a", "hc-b", "hc-b", "hc-a"]))
    regs = [(e[2], e[3]) for e in kinds(w.events, "register")]
    ones = [o for o in out if o["slot"] == 1]
    if [o["state"] for o in ones] != [route] * cap:
        p.append(f"serial: slot 1 committed {[o['state'] for o in ones]}, want {cap} x {route}")
    if (1, cap + 1) in regs:
        p.append(f"serial: slot 1's attempt {cap + 1} was registered past its half-cell's cap")
    if any(s == 4 for s, _ in regs):
        p.append("serial: slot 4 was registered in a closed half-cell")
    if [(o["slot"], o["state"]) for o in out if o["slot"] != 1] != [(2, labels4.GRADED), (3, labels4.GRADED)]:
        p.append(f"serial: the other half-cell's rows: {[(o['slot'], o['state']) for o in out if o['slot'] != 1]}")
    if b.stopped is not None:
        p.append(f"serial: the loop stopped for a human: {b.stopped}")
    for o in ones:
        want = (True, False, True, None, closed) if o["attempt"] == cap else (False, True, False, None, None)
        if _fields(o, *keys) != want:
            p.append(f"serial: slot 1 attempt {o['attempt']} handed to commit as {_fields(o, *keys)}, want {want}")
    rec = r.committed.get((1, cap), {})
    if rec.get("cell_state") != closed or not isinstance(rec.get("cell_reason"), str) or str(cap) not in rec.get("cell_reason", ""):
        p.append(f"serial: the committed record carries {rec.get('cell_state')!r} ({rec.get('cell_reason')!r})")
    # 2. a restart from the repo's history keeps hc-a closed: its capped and its unstarted slot are never
    #    registered; another half-cell's new row runs
    try:
        b2, out2, w2, *_ = restart(r, [row(1, "hc-a"), row(4, "hc-a"), row(5, "hc-b")], cls=cls)
        regs2 = [(e[2], e[3]) for e in kinds(w2.events, "register")]
        if regs2 != [(5, 1)] or [(o["slot"], o["state"]) for o in out2] != [(5, labels4.GRADED)]:
            p.append(f"restart: registered {regs2}, committed {[(o['slot'], o['attempt'], o['state']) for o in out2]}")
    except Exception as e:  # noqa: BLE001
        p.append(f"restart: raised {type(e).__name__}: {e}")
    # 3. three at once: hc-a's three slots meet the route together.
    if route == labels4.REHEARSAL:
        # Rehearsals count one by one: the one whose commit brings the count to the cap closes the half-cell, and the
        # re-runs granted before it in the block are never registered
        b, out, w, d, r, _ = run(0, plan={(s, 1): scenario for s in (1, 2, 3)}, cls=cls,
                                 row_list=rows_in(["hc-a", "hc-a", "hc-a", "hc-b"]))
        regs = [(e[2], e[3]) for e in kinds(w.events, "register")]
        if regs != [(1, 1), (2, 1), (3, 1), (4, 1)]:
            p.append(f"block: registered {regs}, want hc-a's three slots once each, then hc-b's")
        for o in out:
            if o["slot"] == 4:
                want = (True, False, False, None, None)
            elif o["slot"] < cap:
                want = (False, True, False, None, None)
            else:
                want = (True, False, True, None, closed)
            if _fields(o, *keys) != want:
                p.append(f"block: slot {o['slot']} attempt {o['attempt']} committed as {_fields(o, *keys)}, want {want}")
    else:
        # W1B3-5 (glitch-f3's ruling, 6 Oct 2026): pauses count by usage-window event, the pauses that share one reset
        # once. The block's three pauses spend one pause, so all three are re-run, block after block, until the block
        # that brings hc-a's third window event closes it; hc-a's queued slot 4 is then never registered.
        b, out, w, d, r, _ = run(0, plan={(s, a): scenario for s in (1, 2, 3) for a in range(1, 10)}, cls=cls,
                                 row_list=rows_in(["hc-a", "hc-a", "hc-a", "hc-a", "hc-b"]))
        regs = [(e[2], e[3]) for e in kinds(w.events, "register")]
        want_regs = [(s, a) for a in range(1, cap + 1) for s in (1, 2, 3)] + [(5, 1)]
        if regs != want_regs:
            p.append(f"block: registered {regs}, want hc-a's three slots {cap} times each, block by block, then hc-b's")
        for o in out:
            if o["slot"] == 5:
                want = (True, False, False, None, None)
            elif o["attempt"] < cap:
                want = (False, True, False, None, None)
            else:
                want = (True, False, True, None, closed)
            if _fields(o, *keys) != want:
                p.append(f"block: slot {o['slot']} attempt {o['attempt']} committed as {_fields(o, *keys)}, want {want}")
    if b.stopped is not None:
        p.append(f"block: the loop stopped for a human: {b.stopped}")
    return p


def in_flight_problems(cls=batch.Batch) -> list[str]:
    """A drive of the same block, already running when its half-cell closed: hc-a closes at its third rehearsal
    (slot 4) while slot 5, also hc-a, is driven beside it. Slot 5 is committed as its route says, never re-run, and
    carries the cell state; a pause there still holds the next launch until the usage window resets; slot 1's
    re-run and slot 5's are never registered; hc-b's slot 6 runs."""
    p = []
    closed = closed_state()
    for name in ("rate-limit", "watcher-overflow", "clean"):
        plan = {(1, 1): "preflight-fail", (1, 2): "preflight-fail", (4, 1): "preflight-fail", (5, 1): name}
        b, out, w, d, r, win = run(0, plan=plan, cls=cls, row_list=rows_in(["hc-a", "hc-b", "hc-b", "hc-a", "hc-a",
                                                                           "hc-b"]))
        regs = [(e[2], e[3]) for e in kinds(w.events, "register")]
        if regs != [(1, 1), (2, 1), (3, 1), (1, 2), (4, 1), (5, 1), (6, 1)]:
            p.append(f"{name}: registered {regs}")
        try:
            four, five = r.snapshot(4), r.snapshot(5)
        except StopIteration:
            p.append(f"{name}: slot 4 or 5 never committed")
            continue
        if _fields(four, "state", "final", "rerun", "cell_state") != (labels4.REHEARSAL, True, False, closed):
            p.append(f"{name}: slot 4 (the closing take) committed as {_fields(four, 'state', 'final', 'rerun', 'cell_state')}")
        got = _fields(five, "final", "rerun", "cell_state", "stop")
        if got != (True, False, closed, None) or five.get("cell_reason") != four.get("cell_reason"):
            p.append(f"{name}: slot 5 ({five['state']}) committed as {got} ({five.get('cell_reason')!r})")
        if pause_problems(w.events):
            p.append(f"{name}: {pause_problems(w.events)}")
        if [(o["slot"], o["state"]) for o in out if o["slot"] == 6] != [(6, labels4.GRADED)] or b.stopped is not None:
            p.append(f"{name}: hc-b's slot 6 did not run, or the loop stopped ({b.stopped})")
    return p


class NoClosedCellBranch(batch.Batch):
    """Mutant: every take decided by its route alone, as if its half-cell had not closed."""

    def _decide(self, row, attempt, outcome):
        return self.handlers[outcome["state"]](row, attempt, outcome)


class ForgetsTheWindowInAClosedCell(batch.Batch):
    """Mutant: a pause in a closed half-cell no longer holds the next launch for the usage window."""

    def _decide(self, row, attempt, outcome):
        if row["half_cell"] in self.closed_cells and outcome["state"] == labels4.PAUSE:
            return self._fate(final=True, beyond_cap=True, cell_state=closed_state(),
                              cell_reason=self.closed_cells[row["half_cell"]])
        return super()._decide(row, attempt, outcome)


class RefusesClosedCellRows(batch.Batch):
    """Mutant: the pre-ruling restart, which refused a row whose slot ended at its cap."""

    def row_problems(self, rows):
        return super().row_problems(rows) + [f"row {r['slot']}: the slot is {self.closed[r['slot']]}" for r in rows
                                             if r["half_cell"] in self.closed_cells and r["slot"] in self.closed]


def commit_failure_problems(cls=batch.Batch) -> list[str]:
    """The take that would close its half-cell fails to commit: the half-cell is not closed (a cell closes only by
    a committed record), the failed outcome carries no cell state, and the loop stops `failed` as any commit
    failure does."""
    class FailsOnTheClosingTake(FakeRepo):
        def commit_records(self, row, attempt, outcome):
            if (row["slot"], attempt) == (1, REHEARSAL_CAP):
                raise RuntimeError("disk full")
            super().commit_records(row, attempt, outcome)
    w = World()
    b = cls(FakeDriver(w, {(1, a): "preflight-fail" for a in range(1, 10)}), FailsOnTheClosingTake(w), FakeWindow(w),
            table=test_table(), serial=True)
    out = b.run(rows_in(["hc-a", "hc-b"]))
    last = out[-1]
    p = []
    if _fields(last, "slot", "attempt", "state", "cell_state", "cell_reason") != (1, REHEARSAL_CAP, labels4.FAILED,
                                                                                None, None):
        p.append(f"the failed commit's outcome is {_fields(last, 'slot', 'attempt', 'state', 'cell_state', 'cell_reason')}")
    if b.closed_cells or not b.stopped or b.stopped["state"] != labels4.FAILED:
        p.append(f"closed cells {b.closed_cells}, stopped {b.stopped}")
    return p


class KeepsTheCellOnAFailedCommit(batch.Batch):
    """Mutant: a failed commit's outcome keeps the cell state its fate gave it."""

    def _commit(self, row, attempt, outcome):
        out = super()._commit(row, attempt, outcome)
        if out["state"] == labels4.FAILED and "commit failed" in (out["reason"] or ""):
            fate = self._count_in_cell(row, attempt, dict(out, state=labels4.REHEARSAL))
            out.update(cell_state=fate["cell_state"], cell_reason=fate["cell_reason"])
        return out


class StopsForAHuman(batch.Batch):
    """Mutant: the pre-ruling fate at a rehearsal or pause cap, where the loop stopped for a human."""

    def _count_in_cell(self, row, attempt, outcome):
        fate = super()._count_in_cell(row, attempt, outcome)
        if fate.get("cell_state") is not None:
            fate = dict(fate, stop=f"{outcome['state']} cap reached")
            self._stop(row, attempt, dict(outcome, **fate))
        return fate


class CountsReruns(batch.Batch):
    """Mutant: the pre-ruling unit, the re-runs granted per half-cell, so a half-cell closes one take later."""

    def _count_in_cell(self, row, attempt, outcome):
        if self._within_cap(row, outcome["state"]):
            return self._fate(rerun=True)
        return super()._count_in_cell(row, attempt, outcome)


class ClosesInMemoryOnly(batch.Batch):
    """Mutant: the half-cell closed in memory, its state never committed with the take."""

    def _count_in_cell(self, row, attempt, outcome):
        fate = super()._count_in_cell(row, attempt, outcome)
        if fate.get("cell_state") is not None:
            self.closed_cells[row["half_cell"]] = fate["cell_reason"]
            fate = dict(fate, cell_state=None, cell_reason=None)
        return fate


class KeepsQueuedRows(batch.Batch):
    """Mutant: a closed half-cell's queued rows are still registered."""

    def _drop_closed(self, queue):
        return queue


class ForgetsClosedCells(batch.Batch):
    """Mutant: a restart rebuilds the counts but forgets which half-cells closed."""

    def _replay(self, history):
        super()._replay(history)
        self.closed_cells.clear()


class TrustsCellHistory(batch.Batch):
    """Mutant: committed cell states read without checking them against the counts."""

    def cell_history_problems(self, history):
        return []


class TestCellCaps(unittest.TestCase):
    """glitch-f3's cap ruling (in-plan, 6 Oct 2026; glitch-f3's, not the owner's): pauses and rehearsals are
    counted per half-cell, round 3's unit; at the cap the half-cell closes `incomplete — mechanical` and the loop
    goes on."""

    def test_pause_cap_closes_the_half_cell(self):
        self.assertEqual(cell_cap_problems(labels4.PAUSE), [])

    def test_rehearsal_cap_closes_the_half_cell(self):
        self.assertEqual(cell_cap_problems(labels4.REHEARSAL), [])

    def test_cell_cap_check_can_fail(self):
        for route in (labels4.PAUSE, labels4.REHEARSAL):
            with self.subTest(route=route):
                found = cell_cap_problems(route, StopsForAHuman)
                self.assertTrue(any("stopped for a human" in x for x in found), found)
                found = cell_cap_problems(route, CountsReruns)
                self.assertTrue(any("registered past its half-cell's cap" in x for x in found), found)
                found = cell_cap_problems(route, ClosesInMemoryOnly)
                self.assertTrue(any(x.startswith("serial: the committed record carries None") for x in found), found)
                self.assertTrue(any(x.startswith("restart: raised BatchConfigError") for x in found), found)
                found = cell_cap_problems(route, KeepsQueuedRows)
                self.assertTrue(any("slot 4 was registered in a closed half-cell" in x for x in found), found)
                self.assertTrue(any(x.startswith("block: registered") for x in found), found)
                found = cell_cap_problems(route, ForgetsClosedCells)
                self.assertTrue(any(x.startswith("restart:") for x in found), found)
                found = cell_cap_problems(route, RefusesClosedCellRows)
                self.assertTrue(any(x.startswith("restart: raised BatchConfigError") for x in found), found)

    def test_a_drive_running_when_its_half_cell_closed(self):
        self.assertEqual(in_flight_problems(), [])

    def test_in_flight_check_can_fail(self):
        found = in_flight_problems(NoClosedCellBranch)
        for name in ("watcher-overflow", "clean", "rate-limit"):
            self.assertTrue(any(x.startswith(f"{name}: slot 5") for x in found), (name, found))
        found = in_flight_problems(ForgetsTheWindowInAClosedCell)
        self.assertTrue(any(x.startswith("rate-limit: ['slot 6 launched before the usage window reset']")
                            for x in found), found)

    def test_a_failed_commit_never_closes_the_half_cell(self):
        self.assertEqual(commit_failure_problems(), [])

    def test_failed_commit_check_can_fail(self):
        self.assertTrue(any(x.startswith("the failed commit's outcome")
                            for x in commit_failure_problems(KeepsTheCellOnAFailedCommit)))

    def test_cell_history_check_can_fail(self):
        found = history_validation_problems(TrustsCellHistory)
        for case in ("a half-cell at its cap without its committed state", "a committed cell state below the cap",
                     "a re-run in a closed half-cell"):
            self.assertIn(f"{case}: accepted", found)

        class NoFieldCheck(batch.Batch):   # the outcome's own cell fields never checked (the walk still runs)
            @staticmethod
            def history_problems(history, table=None):   # pf1-l2a: batch passes its table
                return []
        found = history_validation_problems(NoFieldCheck)
        for case in ("a cell state without its reason", "a cell state that is not labels4's, below the cap"):
            self.assertIn(f"{case}: accepted", found)

        class NoStateCheck(NoFieldCheck, TrustsCellHistory):   # neither check
            pass
        self.assertIn("a cell state that is not labels4's: accepted", history_validation_problems(NoStateCheck))


# ------------------------------------------------- glitch-f3's rulings (6 Oct 2026): the wait_reset contract
WAIT_RESET_CONTRACT = ("returns promptly when the usage window has already reset",
                       "blocks until the window resets otherwise",
                       "raises on failure, and the loop then stops as `failed`")


def contract_problems(doc: str) -> list[str]:
    """The contract of the driver side's wait_reset(), written where the loop's driver interface lives."""
    flat = " ".join((doc or "").split())
    return [f"batch.py does not state that wait_reset() {c}" for c in WAIT_RESET_CONTRACT if c not in flat]


class ResetWindow(FakeWindow):
    """A usage window keeping the contract: wait_reset() returns at once when the window has already reset, and
    otherwise blocks until it does (until `reset` is set; WAIT_S is a hang detector, never a timing assumption)."""

    def __init__(self, world, already_reset=True):
        super().__init__(world)
        self.reset = threading.Event()
        if already_reset:
            self.reset.set()

    def wait_reset(self):
        self.resets += 1
        if not self.reset.wait(WAIT_S):
            raise RuntimeError("the usage window never reset (hang detector)")
        self.world.log("reset")


def paused_history_repo():
    """A repo whose last committed outcome is a pause: slot 1 paused, then the window failed and the loop stopped."""
    w = World()
    r = FakeRepo(w)
    batch.Batch(FakeDriver(w, {(1, 1): "rate-limit"}), r, WindowFails(w), table=test_table()).run(rows(1))
    return r


def restart_wait_problems(cls=batch.Batch) -> list[str]:
    """glitch-f3's wait_reset contract, through the loop. A restart after a pause calls wait_reset() once, before
    anything is registered, and proceeds when the window reports it has already reset. A raising wait_reset()
    stops the restarted loop `failed` (W1B2-5) with nothing new registered, launched or committed."""
    p = []
    r1 = paused_history_repo()
    hist = [(o["slot"], o["attempt"], o["state"], o["rerun"]) for o in r1.history()]
    if hist != [(1, 1, labels4.PAUSE, True)]:
        return [f"precondition: the stopped run committed {hist}, want slot 1's pause alone"]
    try:
        b, out, w, d, r, win = restart(r1, rows(4), cls=cls, window_cls=ResetWindow)
        seq = [e[1] for e in w.events]
        if win.resets != 1:
            p.append(f"already reset: the restart called wait_reset() {win.resets} times, want once")
        if "reset" not in seq or "register" not in seq or seq.index("reset") > seq.index("register"):
            p.append(f"already reset: the restart registered before the window reset: {seq[:4]}")
        got = [(o["slot"], o["attempt"], o["state"]) for o in out]
        if got != [(1, 2, labels4.GRADED)] + [(s, 1, labels4.GRADED) for s in (2, 3, 4)] or b.stopped is not None:
            p.append(f"already reset: the restart committed {got}, stopped {b.stopped}")
    except Exception as e:  # noqa: BLE001
        p.append(f"already reset: the restart raised {type(e).__name__}: {e}")
    try:
        b, out, w, d, r, win = restart(r1, rows(4), cls=cls, window_cls=WindowFails)
        if win.resets != 1:
            p.append(f"raising: wait_reset() called {win.resets} times, want once")
        if kinds(w.events, "register") or d.launched or r.passed or out:
            p.append(f"raising: something new was registered, launched or committed ({[e[1:] for e in w.events]})")
        if not b.stopped or b.stopped["state"] != labels4.FAILED or "wait_reset failed" not in b.stopped["reason"]:
            p.append(f"raising: stopped {b.stopped}")
    except Exception as e:  # noqa: BLE001
        p.append(f"raising: the restart raised {type(e).__name__}: {e}")
    return p


class ForgetsThePause(batch.Batch):
    """Mutant: a restart after a pause launches at once."""

    def _replay(self, history):
        super()._replay(history)
        self.paused = False


class WaitsEveryBlock(batch.Batch):
    """Mutant: waits for the usage window before every block, not only after a pause."""

    def _register(self, block):
        ok = super()._register(block)
        self.paused = True
        return ok


class WindowErrorPropagates(batch.Batch):
    """Mutant: the pre-W1B2-5 loop, where a wait_reset() failure escaped the loop."""

    def _wait_window(self):
        self.window.wait_reset()
        return True


class ProceedsOnAWindowFailure(batch.Batch):
    """Mutant: a wait_reset() failure read as a reset window."""

    def _wait_window(self):
        try:
            self.window.wait_reset()
        except Exception:  # noqa: BLE001
            pass
        return True


class TestWaitReset(unittest.TestCase):
    """glitch-f3's ruling (in-plan, 6 Oct 2026; glitch-f3's, not the owner's): the wait_reset() contract, written
    down, and the loop's side of it driven through fakes."""

    def test_contract_is_written(self):
        self.assertEqual(contract_problems(batch.__doc__), [])

    def test_contract_check_can_fail(self):
        for clause in WAIT_RESET_CONTRACT:
            doc = " ".join(batch.__doc__.split()).replace(clause, "")
            self.assertEqual(len(contract_problems(doc)), 1, clause)

    def test_restart_after_a_pause_waits_once_or_stops_failed(self):
        self.assertEqual(restart_wait_problems(), [])

    def test_restart_wait_check_can_fail(self):
        self.assertTrue(any(x.startswith("already reset: the restart called wait_reset() 0 times")
                            for x in restart_wait_problems(ForgetsThePause)))
        self.assertTrue(any(x.startswith("already reset: the restart called wait_reset() 2 times")
                            for x in restart_wait_problems(WaitsEveryBlock)))
        self.assertTrue(any(x.startswith("raising: the restart raised RuntimeError")
                            for x in restart_wait_problems(WindowErrorPropagates)))
        self.assertTrue(any(x.startswith("raising: something new was registered")
                            for x in restart_wait_problems(ProceedsOnAWindowFailure)))


# ------------------------------------------- review round 3 (fold 4): W1B3-1, W1B3-3, W1B3-5, W1B3-6
# glitch-f3's rulings (in-plan, 6 Oct 2026, relayed by the gap4 lane lead; glitch-f3's, not the owner's): W1B3-1's fix
# accepted as written; W1B3-5 in scope (pauses that share one reset count once per half-cell). W1B3-3 and W1B3-6 are
# the brief's.
BY = "Javier"   # who made the tests' rulings: a ruling names its maker, and batch never writes one


def ruling(slot, attempt, rule, route=None, by=BY) -> dict:
    """A human's ruling on one blocked take, or one that failed after its drive started (W1B3-1), as the repo commits
    it beside the outcomes: `re-run`, or `route` with a labels4 route, `by` naming who, and (pre-freeze review 1,
    MAJOR 8) why and what it cites."""
    return {"kind": labels4.RULING, "slot": slot, "attempt": attempt, "ruling": rule, "route": route, "by": by,
            "why": "synthetic: the stopped take's records were read", "cite": "tests/test_batch.py"}


def rerun_ruling(slot, attempt, **kw) -> dict:
    return ruling(slot, attempt, labels4.RULE_RERUN, **kw)


def route_ruling(slot, attempt, route, **kw) -> dict:
    return ruling(slot, attempt, labels4.RULE_ROUTE, route, **kw)


def outcomes_of(out) -> list:
    return [(o["slot"], o["attempt"], o["state"]) for o in out]


# The takes a restart must never drive again without a ruling: blocked, or failed after the drive started (W1B3-1).
STOPPED_TAKES = {
    "blocked: a checker reason routing.json does not list": dict(plan={(1, 1): "unlisted-reason"}),
    "blocked: an event id arrived as a checker reason": dict(plan={(1, 1): "event end_turn + study-materials-reached"}),
    "blocked: the driver's pin is not the row's profile": dict(pins={1: dict(PIN, version="driver-says")}),
    "failed: the driver raised": dict(plan={(1, 1): "driver-raises"}),
    "failed: the driver raised after the agent's first turn": dict(plan={(1, 1): RAISES_AFTER_FIRST_TURN}),
    "failed: routing raised": dict(records_edit={1: _three_turns}, batch_kw={"route_fn": _route_raises_on_slot_2}),
}


def refusal_problems(cls=batch.Batch) -> list[str]:
    """W1B3-1 (glitch-f3 accepted the brief's fix as written): a restart refuses a row whose slot's last committed take
    is blocked, or failed after its drive started, naming the slot and the attempt, until a ruling for that take is
    committed. The reviewer's probes: a raising driver and an unlisted reason were re-driven without limit."""
    p = []
    for name, kw in STOPPED_TAKES.items():
        _, out, _, _, r1, _ = run(1, cls=cls, **kw)
        if [o["state"] for o in out] != [labels4.BLOCKED if name.startswith("blocked") else labels4.FAILED]:
            p.append(f"{name}: precondition: the first run committed {outcomes_of(out)}")
            continue
        try:
            _, out2, *_ = restart(r1, rows(1), start_attempts={1: 1}, cls=cls)
            p.append(f"{name}: the restart drove it again with no ruling ({outcomes_of(out2)})")
        except batch.BatchConfigError as e:
            if "slot 1 attempt 1" not in str(e) or "ruling" not in str(e):
                p.append(f"{name}: refused without naming the slot, the attempt and the missing ruling: {e}")
    return p


def ruled_rerun_problems(cls=batch.Batch) -> list[str]:
    """W1B3-1: with a `re-run` ruling committed for (slot, attempt), the stopped take's slot is re-driven once, at the
    next attempt. The ruling is spent by that drive: a second blocked take needs a ruling of its own."""
    p = []
    _, _, _, _, r1, _ = run(1, plan={(1, 1): "unlisted-reason-before"})
    try:
        _, out, _, _, r2, _ = restart(r1, rows(1), plan={(1, 2): "unlisted-reason-before"}, start_attempts={1: 1}, cls=cls,
                                      rulings=[rerun_ruling(1, 1)])
    except Exception as e:  # noqa: BLE001
        return [f"re-run ruling: the restart raised {type(e).__name__}: {e}"]
    if outcomes_of(out) != [(1, 2, labels4.BLOCKED)]:
        p.append(f"re-run ruling: the restart committed {outcomes_of(out)}, want slot 1 driven once, at attempt 2")
    try:
        _, out3, *_ = restart(r2, rows(1), start_attempts={1: 2}, cls=cls)
        p.append(f"a spent ruling: attempt 2's blocked take was driven again with no ruling of its own ({outcomes_of(out3)})")
    except batch.BatchConfigError as e:
        if "slot 1 attempt 2" not in str(e):
            p.append(f"a spent ruling: refused without naming slot 1 attempt 2: {e}")
    try:
        _, out4, *_ = restart(r2, rows(1), start_attempts={1: 2}, cls=cls, rulings=[rerun_ruling(1, 2)])
        if outcomes_of(out4) != [(1, 3, labels4.GRADED)]:
            p.append(f"a second ruling: the restart committed {outcomes_of(out4)}")
    except Exception as e:  # noqa: BLE001
        p.append(f"a second ruling: the restart raised {type(e).__name__}: {e}")
    return p


def ruled_route_problems(cls=batch.Batch) -> list[str]:
    """W1B3-1: a `route <route>` ruling gives the stopped take that route's fate, decided on the restart as the loop
    would have decided it then: graded makes the slot final; harness-error spends the slot's one re-run; a rehearsal
    counts in its half-cell and can close it; a pause holds the next launch for the usage window."""
    p = []
    # graded: an event id arrived as a checker reason, and the plan's word is "graded as usual, the text masked"
    _, _, _, _, r1, _ = run(2, plan={(1, 1): "event end_turn + account-email"})
    graded = [route_ruling(1, 1, labels4.GRADED)]
    try:
        _, out, *_ = restart(r1, rows(1), cls=cls, rulings=graded)
        p.append(f"route graded: the ruled slot was driven again ({outcomes_of(out)})")
    except batch.BatchConfigError as e:
        if "final" not in str(e):
            p.append(f"route graded: refused for another reason: {e}")
    except Exception as e:  # noqa: BLE001
        p.append(f"route graded: the restart raised {type(e).__name__}: {e}")
    try:
        _, out, *_ = restart(r1, [row(3, "hc-a")], cls=cls, rulings=graded)
        if outcomes_of(out) != [(3, 1, labels4.GRADED)]:
            p.append(f"route graded: another slot's restart committed {outcomes_of(out)}")
    except Exception as e:  # noqa: BLE001
        p.append(f"route graded: another slot's restart raised {type(e).__name__}: {e}")
    # harness-error: the ruled take spends slot 1's one re-run, so the re-run's own harness-error is final, beyond it
    _, _, _, _, r1, _ = run(1, plan={(1, 1): "unlisted-reason-before"})
    try:
        _, out, *_ = restart(r1, rows(1), plan={(1, 2): "watcher-overflow"}, start_attempts={1: 1}, cls=cls,
                             rulings=[route_ruling(1, 1, labels4.HARNESS_ERROR)])
        got = [(o["slot"], o["attempt"], o["state"], o["rerun"], o["final"], o["beyond_cap"]) for o in out]
        if got != [(1, 2, labels4.HARNESS_ERROR, False, True, True)]:
            p.append(f"route harness-error: the restart committed {got}")
    except Exception as e:  # noqa: BLE001
        p.append(f"route harness-error: the restart raised {type(e).__name__}: {e}")
    # rehearsal: hc-a's two rehearsals and the ruled one reach the cap, so hc-a closes and nothing more is registered
    _, _, _, _, r1, _ = run(0, plan={(1, 1): "preflight-fail", (1, 2): "preflight-fail",
                                     (1, 3): "unlisted-reason-before"}, serial=True, row_list=rows_in(["hc-a"]))
    try:
        b, out, w, *_ = restart(r1, rows_in(["hc-a", "hc-a", "hc-b"]), cls=cls,
                                rulings=[route_ruling(1, 3, labels4.REHEARSAL)])
        regs = [(e[2], e[3]) for e in kinds(w.events, "register")]
        if regs != [(3, 1)] or outcomes_of(out) != [(3, 1, labels4.GRADED)] or {x["slot"] for x in b.skipped} != {1, 2}:
            p.append(f"route rehearsal: registered {regs}, committed {outcomes_of(out)}, skipped {b.skipped}")
    except Exception as e:  # noqa: BLE001
        p.append(f"route rehearsal: the restart raised {type(e).__name__}: {e}")
    # rehearsal, below the cap: the ruled take is hc-a's first rehearsal, so the slot's re-run rehearses as its second
    # and the next as its third, which closes hc-a (never a fourth attempt)
    _, _, _, _, r1, _ = run(1, plan={(1, 1): "unlisted-reason-before"})
    try:
        _, out, w, *_ = restart(r1, rows(1), plan={(1, a): "preflight-fail" for a in (2, 3, 4)}, start_attempts={1: 1},
                                cls=cls, serial=True, rulings=[route_ruling(1, 1, labels4.REHEARSAL)])
        got = [(o["slot"], o["attempt"], o["state"], o["rerun"], o["cell_state"] is not None) for o in out]
        if got != [(1, 2, labels4.REHEARSAL, True, False), (1, 3, labels4.REHEARSAL, False, True)]:
            p.append(f"route rehearsal below the cap: the restart committed {got}")
    except Exception as e:  # noqa: BLE001
        p.append(f"route rehearsal below the cap: the restart raised {type(e).__name__}: {e}")
    # pause: the restart waits for the usage window before it re-runs the slot
    _, _, _, _, r1, _ = run(1, plan={(1, 1): "unlisted-reason-before"})
    try:
        _, out, w, _, _, win = restart(r1, rows(1), start_attempts={1: 1}, cls=cls,
                                       rulings=[route_ruling(1, 1, labels4.PAUSE)])
        seq = [e[1] for e in w.events]
        if (outcomes_of(out) != [(1, 2, labels4.GRADED)] or win.resets != 1 or "reset" not in seq
                or seq.index("reset") > seq.index("register")):
            p.append(f"route pause: committed {outcomes_of(out)}, {win.resets} waits, events {seq[:3]}")
    except Exception as e:  # noqa: BLE001
        p.append(f"route pause: the restart raised {type(e).__name__}: {e}")
    return p


def raised_after_first_turn_problems(cls=batch.Batch) -> list[str]:
    """W1B3-1: a driver that raises after the agent's first turn leaves the loop no records, yet the agent acted: the
    take is committed `failed` with drive_started true, a restart refuses it without a ruling, and a `re-run` ruling
    re-drives it once, when the driver's own refusal record was committed with its outcome (THE RULING RULE, the
    closure review of 898e598c); with none, the restart refuses the re-run."""
    p = []
    _, _, _, _, r1, _ = run(1, plan={(1, 1): RAISES_AFTER_FIRST_TURN}, cls=cls)
    one = r1.snapshot(1)
    if (one["state"], one.get("drive_started"), one["records"]) != (labels4.FAILED, True, None):
        p.append(f"committed {one['state']}, drive_started {one.get('drive_started')!r}, records {one['records']!r}")
    try:
        _, out, *_ = restart(r1, rows(1), start_attempts={1: 1}, cls=cls)
        p.append(f"the restart drove it again with no ruling ({outcomes_of(out)})")
    except batch.BatchConfigError as e:
        if "slot 1 attempt 1" not in str(e):
            p.append(f"refused without naming slot 1 attempt 1: {e}")
    try:
        _, out, *_ = restart(r1, rows(1), start_attempts={1: 1}, cls=cls, rulings=[rerun_ruling(1, 1)],
                             refusal=lambda row, o: None)
        p.append(f"with a re-run ruling and no refusal record, the restart drove it ({outcomes_of(out)})")
    except batch.BatchConfigError as e:
        if "refusal record" not in str(e):
            p.append(f"with a re-run ruling and no refusal record, refused for another reason: {e}")
    try:
        _, out, *_ = restart(r1, rows(1), start_attempts={1: 1}, cls=cls, rulings=[rerun_ruling(1, 1)],
                             refusal=lambda row, o: {"refused": "TimeoutError", "why": "synthetic"})
        if outcomes_of(out) != [(1, 2, labels4.GRADED)]:
            p.append(f"with a re-run ruling, the restart committed {outcomes_of(out)}")
    except Exception as e:  # noqa: BLE001
        p.append(f"with a re-run ruling, the restart raised {type(e).__name__}: {e}")
    return p


def nothing_ran_problems(cls=batch.Batch) -> list[str]:
    """W1B3-1: a failed take where nothing ran is still re-driven automatically, with no ruling: a register failure
    (slot 1 registered, slot 2's register raised), and a launch failure with no records (nothing created, or a
    half-created container removed by its id). Each is committed with drive_started false."""
    p = []
    w = World()
    r = RegisterFailsRepo(w)
    batch.Batch(FakeDriver(w), r, FakeWindow(w), table=test_table()).run(rows(3))
    roads = {"a register failure": (r, rows(3), [(1, 2, labels4.GRADED), (2, 1, labels4.GRADED), (3, 1, labels4.GRADED)])}
    for how in ("none", "half"):
        _, _, _, _, r1, _ = run(1, launch_fails={1: how})
        roads[f"a launch failure ({how})"] = (r1, rows(1), [(1, 2, labels4.GRADED)])
    for name, (repo, row_list, want) in roads.items():
        first = repo.history()[0]
        if (first["state"], first.get("drive_started")) != (labels4.FAILED, False):
            p.append(f"{name}: committed {first['state']}, drive_started {first.get('drive_started')!r}")
        try:
            _, out, *_ = restart(repo, row_list, cls=cls)
            if outcomes_of(out) != want:
                p.append(f"{name}: the restart committed {outcomes_of(out)}, want {want}")
        except Exception as e:  # noqa: BLE001
            p.append(f"{name}: the restart raised {type(e).__name__}: {e}")
    return p


def owed_problems(cls=batch.Batch) -> list[str]:
    """W1B3-6: a restart refuses rows that leave out a slot its history still owes a re-run, naming the slot and the
    attempt owed: a harness-error's re-run, a pause's, and a take that failed before anything ran. Named, the slot
    runs. A re-run owed in a half-cell that has since closed is owed nothing."""
    p = []
    _, _, _, _, r_he, _ = run(2, plan={(1, 1): "watcher-overflow", (2, 1): "unlisted-reason"})
    w = World()
    r_reg = RegisterFailsRepo(w)
    batch.Batch(FakeDriver(w), r_reg, FakeWindow(w), table=test_table()).run(rows(3))
    for name, repo, left in (("a harness-error's re-run", r_he, [row(3, "hc-a")]),
                             ("a pause's re-run", paused_history_repo(), [row(2, "hc-a")]),
                             ("a take that failed before anything ran", r_reg, [row(2, "hc-a"), row(3, "hc-a")])):
        try:
            _, out, *_ = restart(repo, left, cls=cls)
            p.append(f"{name} left out: accepted ({outcomes_of(out)})")
        except batch.BatchConfigError as e:
            if "slot 1 attempt 2" not in str(e):
                p.append(f"{name} left out: refused without naming slot 1 attempt 2: {e}")
        except Exception as e:  # noqa: BLE001
            p.append(f"{name} left out: the restart raised {type(e).__name__}: {e}")
    try:
        _, out, *_ = restart(r_he, [row(1, "hc-a"), row(3, "hc-a")], start_attempts={1: 1}, cls=cls)
        if outcomes_of(out) != [(1, 2, labels4.GRADED), (3, 1, labels4.GRADED)]:
            p.append(f"the owed slot named: the restart committed {outcomes_of(out)}")
    except Exception as e:  # noqa: BLE001
        p.append(f"the owed slot named: the restart raised {type(e).__name__}: {e}")
    # hc-a's three slots rehearse at once: slots 1 and 2 are granted re-runs, slot 3's rehearsal closes hc-a
    _, _, _, _, r_closed, _ = run(0, plan={(s, 1): "preflight-fail" for s in (1, 2, 3)}, row_list=rows_in(["hc-a"] * 3))
    try:
        _, out, *_ = restart(r_closed, [row(4, "hc-b")], cls=cls)
        if outcomes_of(out) != [(4, 1, labels4.GRADED)]:
            p.append(f"a closed half-cell's re-runs: the restart committed {outcomes_of(out)}")
    except Exception as e:  # noqa: BLE001
        p.append(f"a closed half-cell's re-runs were still owed: {type(e).__name__}: {e}")
    return p


def pause_window_problems(cls=batch.Batch) -> list[str]:
    """W1B3-3: a restart waits for the usage window when a pause is anywhere among the last MAX_OPEN committed outcomes
    (B19-5; with three committed, among the last BLOCK):
    first in a block of three, or in its middle. The block paused, its two siblings graded, and wait_reset() failed."""
    p = []
    for where, slot in (("first", 1), ("in the middle", 2)):
        w = World()
        r = FakeRepo(w)
        batch.Batch(FakeDriver(w, {(slot, 1): "rate-limit"}), r, WindowFails(w), table=test_table()).run(rows(3))
        hist = [(o["slot"], o["state"]) for o in r.history()]
        if hist != [(s, labels4.PAUSE if s == slot else labels4.GRADED) for s in (1, 2, 3)]:
            p.append(f"pause {where}: precondition: the stopped run committed {hist}")
            continue
        try:
            _, out, w2, _, _, win = restart(r, [x for x in rows(4) if x["slot"] in (slot, 4)], start_attempts={slot: 1},
                                            cls=cls)
            seq = [e[1] for e in w2.events]
            if win.resets < 1 or "reset" not in seq or seq.index("reset") > seq.index("register"):
                p.append(f"pause {where}: the restart registered before the window reset: {seq[:3]}")
        except Exception as e:  # noqa: BLE001
            p.append(f"pause {where}: the restart raised {type(e).__name__}: {e}")
    return p


def one_window_problems(cls=batch.Batch) -> list[str]:
    """W1B3-5 (glitch-f3's ruling, in-plan, 6 Oct 2026, relayed by the gap4 lane lead; glitch-f3's, not the owner's):
    pauses that share one reset count once per half-cell, since the cap bounds usage-window events, round 3's own unit
    (round 3 drove one take at a time). Three takes of hc-a pause in one block: one usage-limit event, one pause spent
    from the half-cell's cap. All three are re-run, hc-a stays open, and the three commit one window event between
    them. A restart rebuilds that count from the committed window events."""
    p = []
    plan = {(s, 1): "rate-limit" for s in (1, 2, 3)}
    b, out, w, d, r, win = run(0, plan=plan, cls=cls, row_list=rows_in(["hc-a"] * 3 + ["hc-b"]))
    first = [o for o in out if o["attempt"] == 1 and o["half_cell"] == "hc-a"]
    got = [(o["slot"], o["state"], o["rerun"], o["final"], o["cell_state"]) for o in first]
    if got != [(s, labels4.PAUSE, True, False, None) for s in (1, 2, 3)]:
        p.append(f"one window: the block's three pauses committed as {got}")
    events = [o.get("window_event") for o in first]
    if len(set(events)) != 1 or None in events:
        p.append(f"one window: the three pauses carry window events {events}, want one")
    if [(o["slot"], o["attempt"], o["state"]) for o in out if o["attempt"] == 2] != [(s, 2, labels4.GRADED) for s in (1, 2, 3)]:
        p.append(f"one window: the re-runs committed {[(o['slot'], o['attempt'], o['state']) for o in out if o['attempt'] == 2]}")
    if b.skipped or b.stopped is not None or win.resets != 1:
        p.append(f"one window: skipped {b.skipped}, stopped {b.stopped}, {win.resets} waits")
    w = World()
    r1 = FakeRepo(w)
    batch.Batch(FakeDriver(w, plan), r1, WindowFails(w), table=test_table()).run(rows_in(["hc-a"] * 3))
    try:
        plan2 = {(s, a): "rate-limit" for s in (1, 2, 3) for a in (2, 3)}
        _, out, *_ = restart(r1, rows_in(["hc-a"] * 3), plan=plan2, start_attempts={1: 1, 2: 1, 3: 1}, cls=cls)
        fates = [(o["slot"], o["attempt"], o["rerun"], o["final"], o["cell_state"] is not None) for o in out]
        want = [(s, 2, True, False, False) for s in (1, 2, 3)] + [(s, 3, False, True, True) for s in (1, 2, 3)]
        if fates != want:
            p.append(f"restart: committed {fates}, want the second window event re-run and the third close hc-a")
    except Exception as e:  # noqa: BLE001
        p.append(f"restart: raised {type(e).__name__}: {e}")
    return p


def never_writes_a_ruling_problems(cls=batch.Batch) -> list[str]:
    """W1B3-1: batch never writes a ruling. Through a stop, a ruled restart and a leak, every object it hands the
    repo's commit_records is an outcome, holding exactly the outcome keys, never a ruling."""
    p = []
    _, _, _, _, r1, _ = run(2, plan={(1, 1): "unlisted-reason-before"}, cls=cls)
    repos = [r1]
    try:
        repos.append(restart(r1, rows(1), start_attempts={1: 1}, cls=cls, rulings=[rerun_ruling(1, 1)])[4])
    except Exception as e:  # noqa: BLE001
        p.append(f"the ruled restart raised {type(e).__name__}: {e}")
    repos.append(run(3, remove_fails={2}, cls=cls)[4])
    for repo in repos:
        for slot, attempt, obj, _ in repo.passed:
            if not isinstance(obj, dict) or set(obj) != set(batch.OUTCOME_KEYS):
                p.append(f"slot {slot} attempt {attempt}: batch handed the repo {obj!r}, not an outcome")
    return p


def fold4_bad_histories() -> dict:
    """History a restart must refuse, each with a fragment of the reason it must give (W1B3-1, W1B3-5)."""
    _, _, _, _, rb, _ = run(2, plan={(1, 1): "unlisted-reason"})          # slot 1 blocked, slot 2 graded
    blocked = rb.history()
    graded2 = next(o for o in blocked if o["slot"] == 2)
    _, _, _, _, rg, _ = run(2, plan={(1, 1): "watcher-overflow"})
    good = rg.history()
    capped = capped_history()                                              # slot 1 pauses three times, serially
    _, _, _, _, rr, _ = run(0, plan={(1, 1): "preflight-fail", (1, 2): "preflight-fail",
                                     (1, 3): "unlisted-reason-before"},
                            serial=True, row_list=rows_in(["hc-a"]))      # two rehearsals, then blocked
    closed_by_ruling = rr.history() + [route_ruling(1, 3, labels4.REHEARSAL)]   # the ruled third closes hc-a

    def later(o, **kw):
        return dict(copy.deepcopy(o), **kw)

    def at(hist, i, **kw):
        return [later(o, **kw) if j == i else o for j, o in enumerate(hist)]
    return {
        "a ruling with an unknown word": (blocked + [dict(rerun_ruling(1, 1), ruling="retake")], "not a labels4 ruling"),
        "a ruling that names no maker": (blocked + [rerun_ruling(1, 1, by="  ")], "`by`"),
        "a ruling with a key of its own": (blocked + [dict(rerun_ruling(1, 1), block=1)], "the ruling keys"),
        "a ruling missing a key": (blocked + [{k: v for k, v in rerun_ruling(1, 1).items() if k != "by"}],
                                   "the ruling keys"),
        "a re-run ruling that names a route": (blocked + [rerun_ruling(1, 1, route=labels4.GRADED)], "names no route"),
        "a route ruling to no labels4 route": (blocked + [route_ruling(1, 1, "success")], "names a labels4 route"),
        "a route ruling to a batch state": (blocked + [route_ruling(1, 1, labels4.BLOCKED)], "names a labels4 route"),
        "a ruling for a take never committed": (blocked + [rerun_ruling(1, 5)], "no earlier outcome"),
        "a ruling committed before its take": ([rerun_ruling(1, 1)] + blocked, "no earlier outcome"),
        "two rulings for one take": (blocked + [rerun_ruling(1, 1), route_ruling(1, 1, labels4.GRADED)], "ruled twice"),
        "a ruling for a take that needs none": (blocked + [rerun_ruling(2, 1)], "needs no ruling"),
        "a blocked slot driven again with no ruling": (blocked + [later(graded2, slot=1, attempt=2)], "no ruling for it"),
        "a slot ruled graded, then driven again": (blocked + [route_ruling(1, 1, labels4.GRADED),
                                                              later(graded2, slot=1, attempt=2)], "after its final"),
        "drive_started that is not a bool": (at(good, 0, drive_started=1), "must be bools"),
        "a drive that never started, with records": (at(blocked, 1, drive_started=False), "drive_started"),
        "a window event on a take that is no pause": (at(good, 0, window_event=1), "window_event"),
        "a pause with no window event": (at(capped, 0, window_event=None), "window_event"),
        "a window event reopened": (at(capped, 2, window_event=capped[0].get("window_event")), "reopened"),
        "a take of a half-cell a ruling closed, without the cell state": (
            closed_by_ruling + [later(graded2, slot=2, attempt=1)], "does not carry its cell state"),
    }


class TestRulings(unittest.TestCase):
    """W1B3-1 (glitch-f3 accepted the brief's fix as written, 6 Oct 2026; glitch-f3's, not the owner's): a blocked
    take, or one that failed after its drive started, goes on only on a ruling committed in the repo."""

    def test_a_stopped_take_is_refused_without_a_ruling(self):
        self.assertEqual(refusal_problems(), [])

    def test_a_rerun_ruling_redrives_once(self):
        self.assertEqual(ruled_rerun_problems(), [])

    def test_a_route_ruling_gives_the_routes_fate(self):
        self.assertEqual(ruled_route_problems(), [])

    def test_a_driver_raising_after_the_first_turn(self):
        self.assertEqual(raised_after_first_turn_problems(), [])

    def test_a_failed_take_where_nothing_ran_is_redriven(self):
        self.assertEqual(nothing_ran_problems(), [])

    def test_batch_never_writes_a_ruling(self):
        self.assertEqual(never_writes_a_ruling_problems(), [])


class TestOwedReruns(unittest.TestCase):
    """W1B3-6: a restart never leaves a re-run its history owes silently undone."""

    def test_a_left_out_owed_slot_is_refused(self):
        self.assertEqual(owed_problems(), [])


class TestPauseWindow(unittest.TestCase):
    """W1B3-3: the restart's pause window covers a whole block."""

    def test_a_pause_anywhere_in_the_last_block_waits(self):
        self.assertEqual(pause_window_problems(), [])


class TestWindowEvents(unittest.TestCase):
    """W1B3-5 (glitch-f3's ruling, 6 Oct 2026; glitch-f3's, not the owner's): pauses that share one reset count once
    per half-cell."""

    def test_one_block_one_pause(self):
        self.assertEqual(one_window_problems(), [])



# ------------------------------------------- review round 3 (fold 4): every new guard's mutant goes red
class NoRulingRefusal(batch.Batch):
    """Mutant: the pre-fold-4 restart, which drove a stopped take's slot again with no ruling."""

    def _replay(self, history):
        super()._replay(history)
        self.unruled.clear()


class ForgetsTheDriveStarted(batch.Batch):
    """Mutant: a driver that raised is recorded as if its drive never started."""

    def _drive_step(self, row, attempt, cid, err):
        out = super()._drive_step(row, attempt, cid, err)
        if (out["reason"] or "").startswith("drive failed"):
            out["drive_started"] = False
        return out


class RulingPerSlot(batch.Batch):
    """Mutant: a ruling is keyed by slot, so a spent ruling lets a later stopped take of the slot go on."""

    def _replay(self, history):
        super()._replay(history)
        ruled_slots = {slot for slot, _ in self.ruled}
        for slot in [s for s in self.unruled if s in ruled_slots]:
            attempt, _ = self.unruled.pop(slot)
            self.owed[slot] = (attempt + 1, "an earlier ruling reused")


class RouteAsRerun(batch.Batch):
    """Mutant: a route ruling read as a re-run, the route's fate ignored."""

    def _apply_ruling(self, r, o):
        return super()._apply_ruling(dict(r, ruling=labels4.RULE_RERUN, route=None), o)


class RulingSpendsNothing(batch.Batch):
    """Mutant: a ruled harness-error spends none of the slot's or half-cell's re-runs."""

    def _apply_ruling(self, r, o):
        saved = (copy.deepcopy(self.reruns), copy.deepcopy(self.slot_reruns))
        fate = super()._apply_ruling(r, o)
        self.reruns, self.slot_reruns = saved
        return fate


class WritesARuling(batch.Batch):
    """Mutant: batch writes a ruling of its own for a blocked take."""

    def _commit(self, row, attempt, outcome):
        out = super()._commit(row, attempt, outcome)
        if out["state"] == labels4.BLOCKED:
            try:
                self.repo.commit_records(row, attempt, {"kind": labels4.RULING, "slot": row["slot"], "attempt": attempt,
                                                        "ruling": labels4.RULE_RERUN, "route": None, "by": "batch"})
            except Exception:  # noqa: BLE001 - the fake committer cannot write it; it was handed it all the same
                pass
        return out


class OverwritesTheLeak(batch.Batch):
    """Mutant: the pre-fold-4 leak, which turned the take into `failed`."""

    def _drive_step(self, row, attempt, cid, err):
        out = super()._drive_step(row, attempt, cid, err)
        if out["leaked_container"] is not None:
            out["state"] = labels4.FAILED
        return out


class LeakGoesOn(batch.Batch):
    """Mutant: a leak never stops the loop."""

    def _commit(self, row, attempt, outcome):
        out = super()._commit(row, attempt, outcome)
        if out["leaked_container"] is not None and self.stopped and "leaked" in (self.stopped["reason"] or ""):
            self.stopped = None
        return out


class OwesNothing(batch.Batch):
    """Mutant: the pre-fold-4 restart, which never checked the rows against the drives its history owes."""

    def _replay(self, history):
        super()._replay(history)
        self.owed.clear()


class OwesInClosedCells(batch.Batch):
    """Mutant: a re-run of a half-cell that has since closed is still owed."""

    def _replay(self, history):
        super()._replay(history)
        for o in history:
            if (not batch.is_ruling(o) and o["rerun"] and o["half_cell"] in self.closed_cells
                    and o["slot"] not in self.closed):
                self.owed[o["slot"]] = (o["attempt"] + 1, "owed in a closed half-cell")


class ReplayCountsEachPause(batch.Batch):
    """Mutant: a restart counts each committed pause as its own event (the live loop still counts window events)."""

    def _replay(self, history):
        super()._replay(history)
        for o in history:
            if not batch.is_ruling(o) and o["state"] == labels4.PAUSE:
                self.cell_events[(o["half_cell"], o["state"])].add(("take", o["slot"], o["attempt"]))


class OneWindowForever(batch.Batch):
    """Mutant: every pause of the run shares one window event, as if the window never reset."""

    def _window_event(self):
        self.last_window_event = self.last_window_event or 1
        return self.last_window_event


class RulingsUnchecked(batch.Batch):
    """Mutant: rulings read without their checks."""

    @staticmethod
    def _ruling_problems(i, r, seen, ruled, pending):
        if pending.get(r.get("slot"), (None,))[0] == r.get("attempt"):
            del pending[r["slot"]]
        return []


def per_take_events(outcome):
    """Mutant of batch.cell_event: each paused take its own event (the reviewer's W1B3-5 reading)."""
    return ("take", outcome["slot"], outcome["attempt"])


def restart_waits_mutant(old: str, new: str):
    """W1B3-3: batch.restart_waits with its block window edited in its source (the reviewer's [-2:] and [-1:])."""
    src = textwrap.dedent(inspect.getsource(batch.restart_waits))
    assert src.count(old) == 1, (old, src)
    ns = dict(vars(batch))
    exec(compile(src.replace(old, new), "<restart_waits mutant>", "exec"), ns)   # noqa: S102 - an in-memory mutant
    return ns["restart_waits"]


class TestFold4Mutants(unittest.TestCase):
    """Every guard review round 3's fold added, run against a mutant of what it guards: each goes red."""

    def test_refusal_check_can_fail(self):
        found = refusal_problems(NoRulingRefusal)
        for name in STOPPED_TAKES:
            self.assertTrue(any(x.startswith(f"{name}: the restart drove it again") for x in found), (name, found))

    def test_drive_started_check_can_fail(self):
        def records_or_decision(o):   # the brief's parenthetical alone: a raising driver leaves neither
            return o["state"] == labels4.BLOCKED or (o["state"] == labels4.FAILED
                                                     and (o["records"] is not None or o["decision"] is not None))
        with mock.patch.object(batch, "needs_ruling", records_or_decision):
            self.assertTrue(any(x.startswith("the restart drove it again") for x in raised_after_first_turn_problems()))
            found = refusal_problems()
        for name in ("failed: the driver raised", "failed: the driver raised after the agent's first turn"):
            self.assertTrue(any(x.startswith(f"{name}: the restart drove it again") for x in found), (name, found))
        with mock.patch.object(batch, "needs_ruling", lambda o: o["state"] == labels4.BLOCKED):   # failed never ruled
            self.assertTrue(any(x.startswith("failed: routing raised: the restart drove it again")
                                for x in refusal_problems()))
        with mock.patch.object(batch, "needs_ruling", lambda o: o["state"] in labels4.BATCH_STATES):   # every failed
            found = nothing_ran_problems()
        self.assertEqual(sum("the restart raised BatchConfigError" in x for x in found), 3, found)
        found = raised_after_first_turn_problems(ForgetsTheDriveStarted)
        self.assertTrue(any(x.startswith("committed failed, drive_started False") for x in found), found)

    def test_ruled_rerun_check_can_fail(self):
        self.assertTrue(any(x.startswith("a spent ruling: attempt 2's blocked take was driven again")
                            for x in ruled_rerun_problems(RulingPerSlot)))
        found = ruled_rerun_problems(NoRulingRefusal)   # without the refusal the spent ruling is never asked for
        self.assertTrue(any(x.startswith("a spent ruling") for x in found), found)

    def test_ruled_route_check_can_fail(self):
        found = ruled_route_problems(RouteAsRerun)
        for case in ("route graded: the ruled slot was driven again", "route harness-error: the restart committed",
                     "route rehearsal:"):
            self.assertTrue(any(x.startswith(case) for x in found), (case, found))
        found = ruled_route_problems(RulingSpendsNothing)
        self.assertTrue(any(x.startswith("route harness-error: the restart committed") for x in found), found)
        with mock.patch.object(batch, "effective_route",
                               lambda e: None if batch.is_ruling(e) else e["state"]):   # a ruled pause never waits
            found = ruled_route_problems()
        self.assertTrue(any(x.startswith("route pause:") for x in found), found)

    def test_never_writes_a_ruling_check_can_fail(self):
        self.assertTrue(any("not an outcome" in x for x in never_writes_a_ruling_problems(WritesARuling)))

    def test_leak_check_can_fail(self):
        found = remove_problems(OverwritesTheLeak)
        self.assertTrue(any(x.startswith("the leaked take was committed failed") for x in found), found)
        found = remove_problems(LeakGoesOn)
        self.assertTrue(any(x.startswith("the loop did not stop after the block") for x in found), found)

    def test_owed_check_can_fail(self):
        found = owed_problems(OwesNothing)
        for name in ("a harness-error's re-run", "a pause's re-run", "a take that failed before anything ran"):
            self.assertTrue(any(x.startswith(f"{name} left out: accepted") for x in found), (name, found))
        self.assertTrue(any(x.startswith("a closed half-cell's re-runs were still owed")
                            for x in owed_problems(OwesInClosedCells)))

    def test_pause_window_check_can_fail(self):
        """W1B3-3: the reviewer's two surviving mutants of the restart's pause window now go red. B19-5 re-ruled the
        window to the last MAX_OPEN outcomes; test_batch_rolling pins the old BLOCK span as a mutant too."""
        with mock.patch.object(batch, "restart_waits", restart_waits_mutant("[-MAX_OPEN:]", "[-2:]")):
            found = pause_window_problems()
        self.assertTrue(any(x.startswith("pause first:") for x in found), found)
        with mock.patch.object(batch, "restart_waits", restart_waits_mutant("[-MAX_OPEN:]", "[-1:]")):
            found = pause_window_problems()
        for where in ("first", "in the middle"):
            self.assertTrue(any(x.startswith(f"pause {where}:") for x in found), (where, found))

    def test_window_event_check_can_fail(self):
        """W1B3-5: counting each paused take (the reviewer's reading) closes the half-cell on one usage-limit event."""
        with mock.patch.object(batch, "cell_event", per_take_events):
            found = one_window_problems()
            self.assertTrue(any(x.startswith("one window: the block's three pauses committed as") for x in found), found)
            self.assertTrue(any(x.startswith("block:") for x in cell_cap_problems(labels4.PAUSE)))
        found = one_window_problems(ReplayCountsEachPause)
        self.assertTrue(any(x.startswith("restart:") for x in found), found)
        self.assertFalse(any(x.startswith("one window") for x in found), found)   # the live count is untouched
        self.assertTrue(any("registered past its half-cell's cap" in x for x in cell_cap_problems(labels4.PAUSE,
                                                                                                  OneWindowForever)))

    def test_fold4_history_check_can_fail(self):
        found = history_validation_problems(RulingsUnchecked)
        for case in ("a ruling with an unknown word", "a ruling that names no maker", "a ruling for a take that needs none",
                     "two rulings for one take"):
            self.assertTrue(any(x.startswith(case) for x in found), (case, found))

        class Trusting(batch.Batch):
            @staticmethod
            def history_problems(history, table=None):   # pf1-l2a: batch passes its table
                return []
        found = history_validation_problems(Trusting)
        for case in ("a window event on a take that is no pause", "a window event reopened",
                     "a drive that never started, with records", "a blocked slot driven again with no ruling"):
            self.assertTrue(any(x.startswith(case) for x in found), (case, found))


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


def retyped_problems(source: str, words) -> list[str]:
    """Every string literal outside a docstring that types one of `words` (an f-string's literal parts too)."""
    tree = ast.parse(source)
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    return [f"line {n.lineno}: {n.value!r}" for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs
            and any(w in n.value for w in words)]


class TestBoundary(unittest.TestCase):
    def test_batch_and_routing_import_no_driver_or_agent(self):
        for name in ("batch.py", "routing.py"):
            with open(os.path.join(_ROOT, name), encoding="utf-8") as fh:
                self.assertEqual(import_problems(fh.read()), [], name)

    def test_boundary_check_can_fail(self):
        for src in ("import drive", "from drive import run", "import claude_code_sdk",
                    "from agent_adapter import ScriptedAdapter", "import os, drive"):
            self.assertNotEqual(import_problems(src), [], src)

    def test_the_cell_state_is_never_retyped(self):
        """glitch-f3's cap ruling uses labels4's word (interface 4: imported, never retyped)."""
        for name in ("batch.py", "routing.py"):
            with open(os.path.join(_ROOT, name), encoding="utf-8") as fh:
                self.assertEqual(retyped_problems(fh.read(), [closed_state()]), [], name)

    def test_retyped_check_can_fail(self):
        word = closed_state()
        for src in (f"x = {word!r}", f"y = f'the half-cell is {word} now ({{n}})'", f"z = ('state', {word!r})"):
            self.assertNotEqual(retyped_problems(src, [word]), [], src)
        self.assertEqual(retyped_problems(f"def f():\n    {(word + ', in a docstring')!r}\n", [word]), [])

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
            self.assertEqual(batch.main(["--check"]), 0)   # CP5 ruled: routing.json is ready
        with mock.patch.object(batch, "under_nohup", lambda: False), redirect_stderr(io.StringIO()) as err:
            self.assertEqual(batch.main([]), 2)
        self.assertIn("nohup", err.getvalue())



# ---------------------------------------------------------------- w1b's next touch (lane w4h-w1b-next-touch)
def history_argument_problems() -> list[str]:
    """W1B4-6 (i), w1b's next-touch item 4: a `history` argument that differs from `repo.history()` is refused
    (BatchConfigError naming the first difference); one equal to it is accepted; a repo without history() (a test
    double) may still take a `history` argument."""
    p = []
    _, _, _, _, r1, _ = run(2, plan={(1, 1): "watcher-overflow"})
    good = r1.history()
    differ = {
        "an entry changed": ([dict(good[0], state=labels4.GRADED)] + good[1:], "history[0]"),
        "an entry dropped": (good[:-1], f"history[{len(good) - 1}]"),
        "an entry added": (good + [copy.deepcopy(good[-1])], f"history[{len(good)}]"),
        "empty for a repo that holds outcomes": ([], "history[0]"),
    }
    for name, (given, first) in differ.items():
        w = World()
        try:
            batch.Batch(FakeDriver(w), FakeRepo(w, prior=good), FakeWindow(w), table=test_table(), history=given)
            p.append(f"{name}: accepted")
        except batch.BatchConfigError as e:
            if "repo.history()" not in str(e) or first not in str(e):
                p.append(f"{name}: refused, but not naming {first} against repo.history() ({e})")
        except Exception as e:  # noqa: BLE001 - a crash is not a refusal
            p.append(f"{name}: crashed ({type(e).__name__}: {e})")
    w = World()
    try:
        batch.Batch(FakeDriver(w), FakeRepo(w, prior=good), FakeWindow(w), table=test_table(),
                    history=copy.deepcopy(good))
    except Exception as e:  # noqa: BLE001
        p.append(f"a history equal to repo.history() was refused: {e}")
    try:
        batch.Batch(None, None, None, table=test_table(), history=copy.deepcopy(good))
    except Exception as e:  # noqa: BLE001
        p.append(f"a repo without history() was refused its history argument: {e}")
    return p


class TestNextTouchHistory(unittest.TestCase):
    """W1B4-6 (i): outside tests, Batch refuses a history argument that differs from repo.history()."""

    def test_a_differing_history_argument_is_refused(self):
        self.assertEqual(history_argument_problems(), [])

    def test_history_argument_check_can_fail(self):
        """The mutant: the comparison dropped (the base's rule, the argument used as given)."""
        with mock.patch.object(batch, "history_difference", lambda given, held: None):
            found = history_argument_problems()
        for name in ("an entry changed", "an entry dropped", "empty for a repo that holds outcomes"):
            self.assertIn(f"{name}: accepted", found)
        self.assertTrue(any(x.startswith("an entry added: refused, but not naming") for x in found), found)

    def test_the_first_difference_is_named(self):
        a, b = {"slot": 1, "state": "graded"}, {"slot": 1, "state": "pause"}
        self.assertEqual(batch.history_difference([a], [b]), "history[0] differs first at key 'state'")
        self.assertIsNone(batch.history_difference([a], [dict(a)]))
        self.assertIn("history[1] is held by the argument only", batch.history_difference([a, a], [a]))
        self.assertIn("history[0] is held by repo.history() only", batch.history_difference([], [a]))



# Interface 8 (item 5, the schema half): a registered row requires `agent` ({"harness", "version"}, never defaulted);
# pin_profiles is keyed by harness, then model; expected_pin reads row["agent"]["harness"]; a row whose agent.version
# differs from its pin's version never starts.
NT_HARNESS = hb.CLAUDE_CODE
NT_FAKE = "fake-second"                      # the test-only second harness (interface 8)
NT_PROFILES = {NT_HARNESS: {"test-model-a": {"permission_mode": "bypassPermissions", "version": "0.0.1-test"},
                            "test-model-b": {"permission_mode": "plan-test", "version": "0.0.2-test"}}}


def nt_table() -> dict:
    t = test_table()
    t["pin_profiles"] = copy.deepcopy(NT_PROFILES)
    return t


def nt_row(slot=1, model="test-model-a", **agent) -> dict:
    a = {"harness": NT_HARNESS, "version": NT_PROFILES[NT_HARNESS][model]["version"]}
    a.update(agent)
    return {"slot": slot, "half_cell": "hc-a", "row_id": slot, "model": model, "agent": a}


def agent_row_problems() -> list[str]:
    """Interface 8 on the registered row (item 5)."""
    p = []
    t = nt_table()
    want = dict(NT_PROFILES[NT_HARNESS]["test-model-b"], model="test-model-b", harness=NT_HARNESS)
    try:
        got = batch.expected_pin(nt_row(model="test-model-b"), t)
        if got != want:
            p.append(f"expected_pin: {got}, want {want}")
    except Exception as e:  # noqa: BLE001
        p.append(f"expected_pin raised {type(e).__name__}: {e}")
    b = batch.Batch(None, None, None, table=t, history=[])
    try:
        if b.row_problems([nt_row(1), nt_row(2, model="test-model-b")]):
            p.append(f"clean rows refused: {b.row_problems([nt_row(1), nt_row(2, model='test-model-b')])}")
    except Exception as e:  # noqa: BLE001
        p.append(f"clean rows crashed the row check: {type(e).__name__}: {e}")
    no_agent = nt_row()
    del no_agent["agent"]
    bad = {
        "a row without agent": (no_agent, "agent"),
        "agent None": (dict(nt_row(), agent=None), "agent"),
        "agent without its version": (dict(nt_row(), agent={"harness": NT_HARNESS}), "agent"),
        "agent with an extra key": (nt_row(model_id="x"), "agent"),
        "agent version not a string": (nt_row(version=1), "agent"),
        "a harness with no profiles": (nt_row(harness=NT_FAKE), "no pre-registered pin profile"),
        "agent.version differs from its pin's version": (nt_row(version="9.9.9"), "version"),
    }
    for name, (r, why) in bad.items():
        try:
            found = b.row_problems([r])
        except Exception as e:  # noqa: BLE001 - a crash is not a refusal
            p.append(f"{name}: crashed ({type(e).__name__}: {e})")
            continue
        if not any(why in x for x in found):
            p.append(f"{name}: want refused naming {why!r}, got {found}")
    return p


class TestNextTouchAgentRow(unittest.TestCase):
    """Interface 8 (w1b's next-touch item 5): the batch rows gain `agent` beside `model`, required."""

    def test_the_row_carries_its_agent(self):
        self.assertEqual(agent_row_problems(), [])

    def test_a_run_under_the_agent(self):
        """Rows carrying agent run graded under their harness-keyed profiles; a driver pin naming another harness is
        blocked (the pin is the registered row's, never the driver's)."""
        b, out, *_ = run(3)
        self.assertEqual([o["state"] for o in out], [labels4.GRADED] * 3)
        b, out, w, d, r, _ = run(3, pins={2: dict(PIN, harness=NT_FAKE)})
        self.assertEqual(sibling_problems(out, w, r, b, labels4.BLOCKED), [])
        self.assertIn(NT_FAKE, next(o for o in out if o["slot"] == 2)["reason"])

    def test_agent_row_check_can_fail(self):
        def model_only(row, table):   # the base's expected_pin: keyed by model alone, no harness on the pin
            return dict(table["pin_profiles"][row["agent"]["harness"]][row["model"]], model=row["model"])
        with mock.patch.object(batch, "expected_pin", model_only):
            self.assertTrue(any(x.startswith("expected_pin:") for x in agent_row_problems()))
            b, out, *_ = run(2)
        self.assertEqual({o["state"] for o in out}, {labels4.BLOCKED})
        with mock.patch.object(batch, "agent_problems", lambda row: []):   # agent no longer required
            found = agent_row_problems()
        for name in ("a row without agent", "agent None", "agent without its version"):
            self.assertTrue(any(x.startswith(f"{name}: crashed") or x.startswith(f"{name}: want") for x in found),
                            (name, found))
        with mock.patch.object(batch, "version_problems", lambda row, table: []):   # the version check dropped
            found = agent_row_problems()
        self.assertEqual(found, ["agent.version differs from its pin's version: want refused naming 'version', got []"])



# Item 1 (ruling 3 of 17:42): batch.start_problems refuses the Claude Code entry's PENDING spend-cap list like every other PENDING
# status, so the loop never starts on an unruled spend cap.
def spend_gate_problems() -> list[str]:
    p = []
    bad = {"spend_cap_markers_status PENDING": lambda t: t.update(spend_cap_markers_status="PENDING (glitch-f3): x"),
           "spend_cap_markers_status missing": lambda t: t.pop("spend_cap_markers_status")}
    for name, edit in bad.items():
        t = test_table()
        try:
            edit(t)
            batch.Batch(None, None, None, table=t, history=[])
            p.append(f"{name}: the loop would start")
        except batch.BatchConfigError as e:
            if "spend_cap_markers_status" not in str(e):
                p.append(f"{name}: refused for another reason ({e})")
        except Exception as e:  # noqa: BLE001 - a crash is not a refusal
            p.append(f"{name}: crashed ({type(e).__name__}: {e})")
    # Lane w8c (ruling W8C-gap4-1): Javier ruled the real table's spend status ("spend markers: 1A 2A 3A", 12 Oct
    # 2026), so the real table gives no spend line; set back to PENDING, the same table is refused naming it.
    try:
        real = routing.load_table()
        found = batch.start_problems(real)
        if any(x.startswith("spend_cap_markers_status") for x in found):
            p.append(f"the real table's ruled spend-cap status is refused: {found}")
        real["spend_cap_markers_status"] = "PENDING (glitch-f3): x"
        found = batch.start_problems(real)
        if not any(x.startswith("spend_cap_markers_status") for x in found):
            p.append(f"the real table with a PENDING spend-cap status is not refused: {found}")
    except Exception as e:  # noqa: BLE001
        p.append(f"start_problems crashed on the real table ({type(e).__name__}: {e})")
    return p


class TestNextTouchSpendGate(unittest.TestCase):
    def test_a_pending_spend_cap_list_refuses_to_start(self):
        self.assertEqual(spend_gate_problems(), [])

    def test_spend_gate_check_can_fail(self):
        real = batch.start_problems

        def ignores_the_spend_cap(table):   # the mutant: the PENDING spend-cap list not gated
            return [x for x in real(table) if "spend_cap_markers_status" not in x]
        with mock.patch.object(batch, "start_problems", ignores_the_spend_cap):
            found = spend_gate_problems()
        self.assertIn("spend_cap_markers_status PENDING: the loop would start", found)
        self.assertIn("spend_cap_markers_status missing: the loop would start", found)
        self.assertTrue(any(x.startswith("the real table with a PENDING spend-cap status is not refused")
                            for x in found), found)



class TestNextTouchFold1Gate(unittest.TestCase):
    """Lane review round 1, W4H1-1 (the lane lead's decision: fold for the spend line only): the spend-cap status is
    refused unless, stripped and upper-cased, it does not start with PENDING."""

    LOOSE = ("pending (glitch-f3): x", " PENDING (glitch-f3): x", "Pending", "\tPENDING")

    def loose_problems(self):
        p = []
        for status in self.LOOSE:
            t = test_table()
            t["spend_cap_markers_status"] = status
            if not any(x.startswith("spend_cap_markers_status") for x in batch.start_problems(t)):
                p.append(f"{status!r}: the loop would start")
        return p

    def test_a_loosely_written_pending_spend_status_refuses_to_start(self):
        self.assertEqual(self.loose_problems(), [])
        self.assertFalse(any("spend_cap_markers_status" in x for x in batch.start_problems(test_table())))

    def test_loose_pending_check_can_fail(self):
        with mock.patch.object(batch, "is_pending", lambda status: str(status).startswith(batch.PENDING)):  # the base's
            self.assertEqual(len(self.loose_problems()), len(self.LOOSE))                                   # prefix rule



def loose_status_problems(key: str) -> list[str]:
    """W4H1-1 as glitch-f3 ruled it (under Javier's delegation): every status line of start_problems refuses a loosely
    written PENDING (case, leading whitespace)."""
    p = []
    for status in TestNextTouchFold1Gate.LOOSE:
        t = test_table()
        t[key] = status
        if not any(x.startswith(key) for x in batch.start_problems(t)):
            p.append(f"{key} {status!r}: the loop would start")
    return p


class TestNextTouchFold1Siblings(unittest.TestCase):
    """glitch-f3's ruling on W4H1-1: the three sibling status lines are read the same way as the spend line."""

    def test_operator_reasons_status(self):
        self.assertEqual(loose_status_problems("operator_reasons_status"), [])

    def test_pin_profiles_status(self):
        self.assertEqual(loose_status_problems("pin_profiles_status"), [])

    def test_rate_limit_markers_status(self):
        self.assertEqual(loose_status_problems("rate_limit_markers_status"), [])

    def test_sibling_check_can_fail(self):
        with mock.patch.object(batch, "is_pending", lambda status: str(status).startswith(batch.PENDING)):
            for key in ("operator_reasons_status", "pin_profiles_status", "rate_limit_markers_status"):
                self.assertEqual(len(loose_status_problems(key)), len(TestNextTouchFold1Gate.LOOSE), key)



# Lane review round 2, W4H2-1 (the lane lead's decision): the start gate is an allow-list. A status is ruled only when,
# stripped and upper-cased, it starts with RULED or FILLED and holds no PENDING anywhere; everything else is pending,
# on all four status lines (glitch-f3's W4H1-1 ruling: the four lines gated the same way).
STATUS_KEYS = ("operator_reasons_status", "pin_profiles_status", "rate_limit_markers_status", "spend_cap_markers_status")
NOT_RULED = ("\u200bPENDING (glitch-f3): x", "\ufeffPENDING (glitch-f3): x", "'PENDING'", "Status: PENDING",
             "RULED for codex; PENDING for claude-code", "TBD", "not yet ruled", "FILLED, pending a re-read", "",
             "TEST-ONLY: two injected profiles")
RULED_OK = ("RULED 6 Oct 2026 by glitch-f3", "FILLED 6 Oct 2026", "  ruled (test-only)", "Filled")


def allow_list_problems() -> list[str]:
    p = []
    for key in STATUS_KEYS:
        for status in NOT_RULED:
            t = test_table()
            t[key] = status
            if not any(x.startswith(key) for x in batch.start_problems(t)):
                p.append(f"{key} {status!r}: the loop would start")
        for status in RULED_OK:
            t = test_table()
            t[key] = status
            if any(x.startswith(key) for x in batch.start_problems(t)):
                p.append(f"{key} {status!r}: a ruled status was refused")
    return p


class TestNextTouchFold2Gate(unittest.TestCase):
    def test_the_gate_is_an_allow_list(self):
        self.assertEqual(allow_list_problems(), [])
        self.assertEqual(batch.start_problems(test_table()), [])   # the test table's statuses are ruled

    def test_allow_list_check_can_fail(self):
        def prefix_only(status):     # mutant: the "no PENDING anywhere" half dropped
            return not str(status).strip().upper().startswith(batch.RULED_WORDS)
        with mock.patch.object(batch, "is_pending", prefix_only):
            found = allow_list_problems()
        for key in STATUS_KEYS:
            self.assertIn(f"{key} 'RULED for codex; PENDING for claude-code': the loop would start", found)

        def deny_only(status):       # mutant: the allow-list half dropped (PENDING anywhere is the only refusal)
            return batch.PENDING in str(status).upper()
        with mock.patch.object(batch, "is_pending", deny_only):
            found = allow_list_problems()
        for key in STATUS_KEYS:
            for status in ("TBD", "not yet ruled"):
                self.assertIn(f"{key} {status!r}: the loop would start", found)


if __name__ == "__main__":
    unittest.main()
