#!/usr/bin/env python3
"""batch.py's rolling window (lane vendor-b19, glitch-26's rulings B19-1 and B19-3): red tests, no green yet.

B19-1: at most three drives at once, and a new row starts as soon as any drive finishes, in the frozen row order;
registration stays serial and in row order before each launch; commits stay serial and in row order (a drive that
finishes before an earlier row's drive waits for it); re-runs are requeued first, in row order; and with every drive's
duration equal, the rolling run drives, registers and commits exactly the rows, attempts and outcomes the block run
does, in the same order. The design note is lane-reports/B19-DESIGN-NOTE.md.

The drives are stubs on agent_adapter.ScriptedAdapter (test_batch's scenarios): no model, no container, no drive.py.
A drive's duration is a number of UNITs of sleep; one drive in three is ten times slower than the others. Equal
durations are modelled as drives of one launch wave that end together: the stub repo's commit waits (up to WAIT_S, a
hang detector) until no drive is in flight and then SETTLE more, so a loop that commits every drive that has ended,
in row order, before it fills a slot sees the whole wave ended (the tie rule, design note section 3).

On today's code (blocks of three) the tests that pin the rolling start are red, by design: the block waits for its
slowest drive before it registers the next row. The rest are green today and pin what the rolling window keeps.
"""

from __future__ import annotations

import collections
import copy
import itertools
import os
import sys
import threading
import time
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agent_adapter as aa  # noqa: E402
import batch  # noqa: E402
from graders import labels4  # noqa: E402
import test_batch as tb  # noqa: E402  (its scenarios, rows, table, repo and window fakes)

UNIT = 0.1         # one fast drive's duration, in seconds
SLOW = 10          # the slow drive's duration, in UNITs: ten times slower
SETTLE = 0.05      # equal durations: how long after the wave's last drive ends the commit waits
WAIT_S = 30.0      # a hang detector, never a timing assumption
RUN_S = 120.0      # the whole run's hang detector


class TimedDriver:
    """launch / drive / remove, each drive taking `units` UNITs of sleep (slot -> UNITs for its first attempt; every
    other drive takes one). `plan` maps (slot, attempt) to a test_batch scenario (default clean)."""

    def __init__(self, world, plan=None, units=None):
        self.world, self.plan, self.units = world, plan or {}, units or {}
        self.in_flight = self.max_in_flight = 0
        self.lock = threading.Lock()
        self.idle = threading.Condition(self.lock)
        self.attempts = collections.Counter()
        self.ids = itertools.count(1)

    def launch(self, row):
        cid = f"ctr-{next(self.ids):04d}"
        self.world.log("launch", row["slot"], cid)
        return cid

    def drive(self, row, cid):
        with self.lock:
            self.attempts[row["slot"]] += 1
            attempt = self.attempts[row["slot"]]
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            self.world.log("drive-start", row["slot"], attempt, self.in_flight)
        try:
            time.sleep(UNIT * (self.units.get(row["slot"], 1) if attempt == 1 else 1))
            name = self.plan.get((row["slot"], attempt), "clean")
            turns, box = tb.ALL[name]
            adapter = aa.ScriptedAdapter(turns, container_id=cid)
            adapter.start_take(row)
            results = [adapter.turn(f"line {i}", first=(i == 0), budget_s=1) for i in range(len(turns))]
            adapter.end_take()
            self.world.texts[(row["slot"], attempt)] = "\n".join(r.text for r in results)
            harness = row["agent"]["harness"]
            pin = dict(tb.PROFILES[harness][row["model"]], model=row["model"], harness=harness)
            return aa.harness_records(results, pin=pin, box=box)
        finally:
            with self.lock:
                self.in_flight -= 1
                self.world.log("drive-end", row["slot"], attempt)
                self.idle.notify_all()

    def remove(self, cid):
        self.world.log("remove", cid)

    def wait_idle(self) -> None:
        with self.lock:
            if not self.idle.wait_for(lambda: self.in_flight == 0, WAIT_S):
                raise RuntimeError("a drive never ended (hang detector)")


class EqualRepo(tb.FakeRepo):
    """Equal durations: a commit waits until the whole launch wave has ended, and SETTLE more (the tie rule)."""

    driver = None

    def commit_records(self, row, attempt, outcome):
        self.driver.wait_idle()
        time.sleep(SETTLE)
        super().commit_records(row, attempt, outcome)


def drive_run(row_list, plan=None, units=None, equal=False):
    """One run of batch.Batch on the stubs, under the hang detector: (loop, outcomes, world, driver, repo, window)."""
    w = tb.World()
    d = TimedDriver(w, plan, units)
    r = EqualRepo(w) if equal else tb.FakeRepo(w)
    r.driver = d
    win = tb.FakeWindow(w)
    b = batch.Batch(d, r, win, table=tb.test_table())
    got = {}
    t = threading.Thread(target=lambda: got.setdefault("out", b.run(row_list)), daemon=True)
    t.start()
    t.join(RUN_S)
    if t.is_alive():
        raise AssertionError("the run never ended (hang detector)")
    return b, got["out"], w, d, r, win


def at(events, *head):
    """The log index of the first event that starts with `head`."""
    for e in events:
        if e[1:1 + len(head)] == head:
            return e[0]
    raise AssertionError(f"no event {head!r} in the log")


def trace(events, outcomes):
    """What B19-1's equivalence compares: the registrations, the launches, the commits (with every fate key) and the
    window waits (as the number of registrations before each), each in its order."""
    regs = [e[2:4] for e in events if e[1] == "register"]
    launches = [e[2] for e in events if e[1] == "launch"]
    commits = [(o["slot"], o["attempt"], o["state"], o["final"], o["rerun"], o["beyond_cap"], o["window_event"],
                o["stop"], o["cell_state"]) for o in outcomes]
    n, waits = 0, []
    for e in events:
        if e[1] == "register":
            n += 1
        elif e[1] == "reset":
            waits.append(n)
    return {"registrations": regs, "launches": launches, "commits": commits, "waits": waits}


def slow_head_rows(n=9):
    return tb.rows_in(["hc-a", "hc-b", "hc-c"] * (n // 3))


class TestRollingStart(unittest.TestCase):
    """One drive in three is ten times slower: the next rows start before it ends (red on the block loop)."""

    def setUp(self):
        self.b, self.out, self.w, self.d, self.r, self.win = drive_run(slow_head_rows(), units={1: SLOW})

    def test_the_next_row_starts_before_the_slow_drive_ends(self):
        ev = self.w.events
        self.assertLess(at(ev, "drive-start", 4), at(ev, "drive-end", 1, 1),
                        "slot 4's drive starts only after slot 1's slow drive ends: the block waits for its slowest")

    def test_both_freed_slots_are_filled_while_the_slow_drive_runs(self):
        ev = self.w.events
        end1 = at(ev, "drive-end", 1, 1)
        for slot in (4, 5):
            self.assertLess(at(ev, "register", slot, 1), end1, f"slot {slot} is registered only after slot 1 ends")
            self.assertLess(at(ev, "drive-start", slot), end1, f"slot {slot}'s drive starts only after slot 1 ends")

    def test_three_drives_run_beside_the_slow_one_after_its_block_mates_end(self):
        ev = self.w.events
        end1 = at(ev, "drive-end", 1, 1)
        after_mates = max(at(ev, "drive-end", 2, 1), at(ev, "drive-end", 3, 1))
        full = [e for e in ev if e[1] == "drive-start" and after_mates < e[0] < end1 and e[4] == 3]
        self.assertTrue(full, "no third drive runs beside slot 1 once slots 2 and 3 have ended")

    def test_never_more_than_three_drives_at_once(self):
        self.assertLessEqual(self.d.max_in_flight, batch.BLOCK)
        self.assertEqual(self.d.max_in_flight, batch.BLOCK)

    def test_every_row_is_driven_once_and_graded(self):
        self.assertEqual([(o["slot"], o["attempt"], o["state"]) for o in self.out],
                         [(s, 1, labels4.GRADED) for s in range(1, 10)])
        self.assertIsNone(self.b.stopped)


class TestRowOrder(unittest.TestCase):
    """Registration before launch and commits, each serial and in row order, with a slow head (green today)."""

    def setUp(self):
        self.b, self.out, self.w, self.d, self.r, self.win = drive_run(slow_head_rows(), units={1: SLOW})

    def test_commits_in_row_order_and_a_finished_drive_waits_for_an_earlier_row(self):
        ev = self.w.events
        self.assertEqual([e[2:4] for e in ev if e[1] == "commit"], [(s, 1) for s in range(1, 10)])
        end1 = at(ev, "drive-end", 1, 1)
        self.assertLess(at(ev, "drive-end", 2, 1), end1)
        self.assertGreater(at(ev, "commit", 2, 1), at(ev, "commit", 1, 1))
        for e in ev:
            if e[1] == "commit":
                self.assertGreater(e[0], at(ev, "drive-end", e[2], e[3]), f"slot {e[2]} committed before its end")

    def test_registration_in_row_order_and_before_each_launch(self):
        ev = self.w.events
        self.assertEqual([e[2:4] for e in ev if e[1] == "register"], [(s, 1) for s in range(1, 10)])
        self.assertEqual([e[2] for e in ev if e[1] == "launch"], list(range(1, 10)))
        for s in range(1, 10):
            self.assertLess(at(ev, "register", s, 1), at(ev, "launch", s))

    def test_registrations_and_commits_never_overlap(self):
        self.assertEqual(self.r.overlaps, 0)


class TestRerunRequeue(unittest.TestCase):
    """A re-run is requeued first, in row order, before every row not yet registered, with a slow head."""

    def test_the_rerun_is_the_next_registration_after_its_commit(self):
        plan = {(2, 1): "preflight-fail"}                     # a rehearsal: re-run in the same slot
        self.assertEqual(tb.scenario_state("preflight-fail", tb.test_table()), labels4.REHEARSAL)
        b, out, w, d, r, win = drive_run(slow_head_rows(), plan=plan, units={1: SLOW})
        ev = w.events
        c = at(ev, "commit", 2, 1)
        nxt = [e[2:4] for e in ev if e[1] == "register" and e[0] > c]
        self.assertEqual(nxt[0], (2, 2), "the re-run is not the next row registered after its commit")
        self.assertEqual(sorted((o["slot"], o["attempt"]) for o in out),
                         sorted([(s, 1) for s in range(1, 10)] + [(2, 2)]))


# The block run's trace for each equal-duration scenario, read from batch.py at 7dc0cf9e (blocks of three): the rows,
# attempts and outcomes the rolling run must reproduce, in the same order (B19-1).
G, R, P, H, A = labels4.GRADED, labels4.REHEARSAL, labels4.PAUSE, labels4.HARNESS_ERROR, labels4.ABORTED
NIGHT = (f"{batch.NIGHTLY_STOP}: 3 harness-errors committed this night (D-4-1), the registered count is "
         f"{batch.NIGHTLY_HARNESS_ERRORS}; the run stops for a ruling")
EQUAL = {
    "reruns, a shared pause and an abort": (
        9,
        {(2, 1): "preflight-fail", (3, 1): "oom", (4, 1): "rate-limit", (5, 1): "usage-limit-text",
         (7, 1): "watcher-overflow"},
        {"registrations": [(1, 1), (2, 1), (3, 1), (2, 2), (4, 1), (5, 1), (4, 2), (5, 2), (6, 1), (7, 1), (8, 1),
                           (9, 1), (7, 2)],
         "launches": [1, 2, 3, 2, 4, 5, 4, 5, 6, 7, 8, 9, 7],
         "commits": [(1, 1, G, True, False, False, None, None, None),
                     (2, 1, R, False, True, False, None, None, None),
                     (3, 1, A, True, False, False, None, None, None),
                     (2, 2, G, True, False, False, None, None, None),
                     (4, 1, P, False, True, False, 1, None, None),
                     (5, 1, P, False, True, False, 1, None, None),
                     (4, 2, G, True, False, False, None, None, None),
                     (5, 2, G, True, False, False, None, None, None),
                     (6, 1, G, True, False, False, None, None, None),
                     (7, 1, H, False, True, False, None, None, None),
                     (8, 1, G, True, False, False, None, None, None),
                     (9, 1, G, True, False, False, None, None, None),
                     (7, 2, G, True, False, False, None, None, None)],
         "waits": [6]}),
    "the nightly stop carried by the wave's last row": (
        6,
        {(1, 1): "watcher-overflow", (2, 1): "agent-says-rate-limit", (1, 2): "watcher-overflow"},
        {"registrations": [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (4, 1)],
         "launches": [1, 2, 3, 1, 2, 4],
         "commits": [(1, 1, H, False, True, False, None, None, None),
                     (2, 1, H, False, True, False, None, None, None),
                     (3, 1, G, True, False, False, None, None, None),
                     (1, 2, H, True, False, True, None, None, None),
                     (2, 2, G, True, False, False, None, None, None),
                     (4, 1, G, True, False, False, None, NIGHT, None)],
         "waits": []}),
}


class TestEqualDurations(unittest.TestCase):
    """With every drive's duration equal, the rolling run is the block run: rows, attempts, outcomes, in order."""

    def test_each_scenario_reproduces_the_block_run(self):
        for name, (n, plan, want) in EQUAL.items():
            with self.subTest(name):
                b, out, w, d, r, win = drive_run(tb.rows_in(["hc-a", "hc-b", "hc-c"] * (n // 3)), plan=plan,
                                                 equal=True)
                self.assertEqual(trace(w.events, out), want)
                self.assertEqual(r.overlaps, 0)

    def test_the_equivalence_check_can_fail(self):
        """A mutant that drives one row at a time (serial) breaks the waits' places, so the comparison goes red."""
        n, plan, want = EQUAL["reruns, a shared pause and an abort"]
        w = tb.World()
        d = TimedDriver(w, plan)
        r = EqualRepo(w)
        r.driver = d
        b = batch.Batch(d, r, tb.FakeWindow(w), table=tb.test_table(), serial=True)
        out = b.run(tb.rows_in(["hc-a", "hc-b", "hc-c"] * (n // 3)))
        self.assertNotEqual(trace(w.events, out), want)


if __name__ == "__main__":
    unittest.main()
