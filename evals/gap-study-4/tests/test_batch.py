#!/usr/bin/env python3
"""batch.py: every terminal state with three drives at once, commits serial in row order,
containers removed by recorded id, and a pause launches no new drive.

The driver is a fake built on agent_adapter.ScriptedAdapter: no model, no container, no drive.py.
Which terminal state each fake scenario reaches is computed by routing.route on the scenario's
records, and the set the tests must reach is labels4.TERMINAL_STATES: neither is typed here.
Every check is a function returning problems, and each is also run against an in-memory mutant of
what it guards and must go red.
"""

from __future__ import annotations

import ast
import collections
import copy
import itertools
import os
import sys
import threading
import time
import unittest
from unittest import mock

sys.dont_write_bytecode = True
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import agent_adapter as aa  # noqa: E402
import batch  # noqa: E402
import routing  # noqa: E402
from graders import labels4  # noqa: E402

PIN = {"model": "pinned-model", "permission_mode": "bypassPermissions", "version": "1.0.0"}
TEST_PAUSE_CAP = 2  # test-only: round 3's pause_cap is pending in routing.json


def test_table() -> dict:
    t = copy.deepcopy(routing.load_table())
    t["caps"][labels4.PAUSE]["reruns_per_half_cell"] = TEST_PAUSE_CAP
    return t


# ------------------------------------------------------------------------------- fake scenarios
def _turn(**kw):
    base = dict(exit_code=0, text="(scripted)", stream_path=None, end_reason=aa.END_TURN, init=dict(PIN))
    base.update(kw)
    return aa.TurnResult(**base)


def _box(**kw):
    b = {"preflight_ok": True, "container_started": True,
         "sidecar": {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False}}
    b.update(kw)
    return b


SCENARIOS = {
    "clean": ([_turn(), _turn()], _box()),
    "preflight-fail": ([], _box(preflight_ok=False)),
    "rate-limit": ([_turn(), _turn(exit_code=1, end_reason=aa.END_ERROR,
                                   api_error={"status": 429, "type": "rate_limit_error"})], _box()),
    "watcher-overflow": ([_turn()], _box(sidecar={"start_record": True, "stop_record": True,
                                                  "exit_code": 0, "queue_overflow": True})),
    "oom": ([_turn(exit_code=137, end_reason=aa.END_ERROR, counters={"oom_kill_delta": 1, "pids_max_delta": 0})], _box()),
    "unlisted-reason": ([_turn()], _box(checker_reasons=["not-in-routing-json"])),
    "driver-raises": None,
}


def scenario_state(name: str, table: dict) -> str:
    """The terminal state a scenario reaches, computed (never typed)."""
    if SCENARIOS[name] is None:
        return labels4.FAILED
    turns, box = SCENARIOS[name]
    try:
        return routing.route(aa.harness_records(turns, pin=PIN, box=box), table)["route"]
    except routing.RoutingRefused:
        return labels4.BLOCKED


# ----------------------------------------------------------------------------------- fake world
class World:
    def __init__(self):
        self.events = []
        self.lock = threading.Lock()

    def log(self, *e):
        with self.lock:
            self.events.append((time.monotonic(),) + e)


class FakeDriver:
    """launch / drive / remove, on ScriptedAdapter. `plan` maps (slot, attempt) to a scenario."""

    def __init__(self, world, plan=None, delays=None):
        self.world, self.plan, self.delays = world, plan or {}, delays or {}
        self.launched, self.removed = [], []
        self.pattern_removals = 0
        self.in_flight = self.max_in_flight = 0
        self._lock = threading.Lock()
        self._attempts = collections.Counter()
        self._ids = itertools.count(1)

    def launch(self, row):
        cid = f"ctr-{next(self._ids):04d}-{os.urandom(3).hex()}"
        self.launched.append(cid)
        self.world.log("launch", row["slot"], cid)
        return cid

    def drive(self, row, cid):
        with self._lock:
            self._attempts[row["slot"]] += 1
            attempt = self._attempts[row["slot"]]
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        self.world.log("drive-start", row["slot"], attempt)
        try:
            time.sleep(self.delays.get(row["slot"], 0.05))
            name = self.plan.get((row["slot"], attempt), "clean")
            if SCENARIOS[name] is None:
                raise RuntimeError("scripted driver failure")
            turns, box = SCENARIOS[name]
            adapter = aa.ScriptedAdapter(turns, container_id=cid)
            adapter.start_take(row)
            results = [adapter.turn(f"line {i}", first=(i == 0), budget_s=1) for i in range(len(turns))]
            adapter.end_take()
            return aa.harness_records(results, pin=PIN, box=box)
        finally:
            with self._lock:
                self.in_flight -= 1
            self.world.log("drive-end", row["slot"], attempt)

    def remove(self, cid):
        if cid not in self.launched:
            raise AssertionError(f"remove of an id never launched: {cid}")
        self.removed.append(cid)
        self.world.log("remove", cid)

    def remove_matching(self, pattern):  # never to be called: removal is by recorded id only
        self.pattern_removals += 1


class FakeRepo:
    def __init__(self, world):
        self.world = world
        self._busy = threading.Lock()
        self.overlaps = 0

    def _one_commit(self, *e):
        if not self._busy.acquire(blocking=False):
            self.overlaps += 1
            self._busy.acquire()
        try:
            self.world.log(*e)
            time.sleep(0.001)
        finally:
            self._busy.release()

    def register(self, row, attempt):
        self._one_commit("register", row["slot"], attempt)

    def commit_records(self, row, attempt, outcome):
        self._one_commit("commit", row["slot"], attempt, outcome["state"])


class FakeWindow:
    def __init__(self, world):
        self.world, self.resets = world, 0

    def wait_reset(self):
        self.resets += 1
        self.world.log("reset")


def rows(n, half_cell="hc-a"):
    return [{"slot": i, "half_cell": half_cell, "row_id": i} for i in range(1, n + 1)]


def run(n, plan=None, delays=None, serial=False, cls=batch.Batch, table=None, row_list=None):
    w = World()
    d, r, win = FakeDriver(w, plan, delays), FakeRepo(w), FakeWindow(w)
    b = cls(d, r, win, table=table or test_table(), serial=serial)
    out = b.run(row_list or rows(n))
    return b, out, w, d, r, win


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
        if block_events and block_events[0][0] != "launch":
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
    if collections.Counter(d.removed) != collections.Counter(d.launched):
        p.append(f"launched {sorted(d.launched)} but removed {sorted(d.removed)}")
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
                b, out, w, d, r, _ = run(3, plan={(2, 1): name}, delays={1: 0.15, 2: 0.10, 3: 0.05})
                first = [o for o in out if o["attempt"] == 1]
                self.assertEqual([o["state"] for o in first if o["slot"] == 2], [want])
                self.assertEqual(d.max_in_flight, 3)
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

    def test_unhandled_state_refuses_to_start(self):
        with mock.patch.object(labels4, "TERMINAL_STATES", labels4.TERMINAL_STATES + ("new-state",)):
            with self.assertRaises(batch.BatchConfigError):
                run(1)

    def test_pending_pause_cap_refuses_to_start(self):
        with self.assertRaisesRegex(batch.BatchConfigError, "pause"):
            batch.Batch(None, None, None)   # the real routing.json: pause cap pending


class TestOrderAndContainers(unittest.TestCase):
    def test_commits_land_serially_in_row_order(self):
        # Later rows finish first; their records still commit after, in row order.
        b, out, w, d, r, _ = run(7, delays={1: 0.2, 2: 0.1, 3: 0.02, 4: 0.15, 5: 0.01, 6: 0.05, 7: 0.01})
        self.assertEqual(commit_order_problems(w.events), [])
        self.assertEqual(r.overlaps, 0)
        self.assertEqual([o["slot"] for o in out], [1, 2, 3, 4, 5, 6, 7])
        ends = [e[2] for e in kinds(w.events, "drive-end")][:3]
        self.assertNotEqual(ends, [1, 2, 3])   # the drives really did finish out of row order

    def test_commit_order_check_can_fail(self):
        _, _, w, *_ = run(3, delays={1: 0.1, 2: 0.05, 3: 0.01})
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
        class Leaky(batch.Batch):
            def _drive_step(self, row, attempt, cid, err):
                d = self.driver
                self.driver = mock.Mock(drive=d.drive, remove=lambda c: None)
                try:
                    return super()._drive_step(row, attempt, cid, err)
                finally:
                    self.driver = d
        b, out, w, d, *_ = run(3, cls=Leaky)
        self.assertNotEqual(container_problems(b, d), [])
        d.removed = list(d.launched)
        d.pattern_removals = 1
        self.assertNotEqual(container_problems(b, d), [])

    def test_serial_fallback_drives_one_at_a_time(self):
        b, out, w, d, *_ = run(4, serial=True)
        self.assertEqual(d.max_in_flight, 1)
        self.assertEqual(len(out), 4)
        self.assertEqual(commit_order_problems(w.events), [])

    def test_concurrency_check_can_fail(self):
        _, _, _, d, *_ = run(3, serial=True)
        self.assertNotEqual(d.max_in_flight, 3)


class TestPause(unittest.TestCase):
    def test_pause_launches_no_new_drive_until_reset(self):
        b, out, w, d, r, win = run(6, plan={(2, 1): "rate-limit"}, delays={1: 0.1, 2: 0.01, 3: 0.1})
        self.assertEqual(pause_problems(w.events), [])
        self.assertEqual(win.resets, 1)
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
                super()._pause(row, attempt, outcome)
                self.paused = False   # forgets to wait for the window
                return True
        b, out, w, d, r, win = run(6, plan={(2, 1): "rate-limit"}, cls=Impatient)
        self.assertEqual(win.resets, 0)
        self.assertNotEqual(pause_problems(w.events), [])

    def test_pause_cap(self):
        plan = {(1, a): "rate-limit" for a in range(1, 10)}
        b, out, w, *_ = run(1, plan=plan)
        self.assertEqual(len(out), TEST_PAUSE_CAP + 1)
        self.assertTrue(out[-1].get("beyond_cap"))
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
                    "from agent_adapter import ScriptedAdapter"):
            self.assertNotEqual(import_problems(src), [], src)

    def test_handlers_keyed_by_labels4(self):
        b = batch.Batch(None, None, None, table=test_table())
        self.assertEqual(set(b.handlers), set(labels4.TERMINAL_STATES))


class TestCli(unittest.TestCase):
    def test_states_and_check(self):
        import io
        import json
        from contextlib import redirect_stdout, redirect_stderr
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(batch.main(["--states"]), 0)
        got = json.loads(buf.getvalue())
        self.assertEqual(tuple(got["routes"]) + tuple(got["batch"]), labels4.TERMINAL_STATES)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(batch.main(["--check"]), 1)   # pause cap pending
        with mock.patch.object(batch, "under_nohup", lambda: False), redirect_stderr(io.StringIO()) as err:
            self.assertEqual(batch.main([]), 2)
        self.assertIn("nohup", err.getvalue())


if __name__ == "__main__":
    unittest.main()
