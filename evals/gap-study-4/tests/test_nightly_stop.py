#!/usr/bin/env python3
"""Step 4: the registered nightly stop rule, on test_batch's fakes.

Registered text (plans/gap-study-round-4.md):
  line 904  "Routing follows the pre-registered table, and three `harness-error`s in one night stop the run for a
             ruling."
  line 560  "A mismatch is routed by the routing table: a rehearsal before the first turn, `harness-error` after it.
             Three in one night stop the run for a ruling."
  line 196  pause: "re-run in the same slot under round 3's `pause_cap`, outside the nightly stop rule"

"Night" and the counting window are not defined in registered text, and no committed outcome carries a time. Named
departure D-4-1 (lane-reports/nightly-stop-rule-2026-10-14.md): the window is every `harness-error` outcome committed
since the last nightly stop (or since the history began), which stops no later than any reading of "one night". Named
departure D-4-2: the stop's ruling is the person named by `nightly_stop_ruled_by` when the loop is restarted; a
restart without it after a committed nightly stop refuses, and one with it when no stop is pending refuses.
Pauses are never counted. A take failed after its drive started (the executed-refusal road, D-3a-1) is not a
registered harness-error: it is counted separately, reported, and never consumed by the rule (it stops the loop on
its own anyway).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import batch  # noqa: E402
import test_batch as tb  # noqa: E402
from graders import labels4  # noqa: E402

HE = "watcher-overflow"          # test_batch's scenario that routes harness-error after the first turn


def cells(n):
    return tb.rows_in([f"hc-{i}" for i in range(1, n + 1)])


class TheRule(unittest.TestCase):
    def test_the_registered_constant(self):
        self.assertEqual(batch.NIGHTLY_HARNESS_ERRORS, 3)
        self.assertTrue(batch.NIGHTLY_STOP.startswith("nightly stop rule"))

    def test_three_harness_errors_stop_the_run_for_a_ruling(self):
        plan = {(s, 1): HE for s in (1, 2, 3)}
        b, out, w, d, r, win = tb.run(3, plan=plan, row_list=cells(3), cls=batch.Batch)
        self.assertEqual([o["state"] for o in out], [labels4.HARNESS_ERROR] * 3)
        self.assertIsNotNone(b.stopped)
        self.assertTrue(b.stopped["reason"].startswith(batch.NIGHTLY_STOP))
        self.assertTrue(out[-1]["stop"].startswith(batch.NIGHTLY_STOP), "the stop is committed with the block's last")
        self.assertTrue(all(o["stop"] is None for o in out[:-1]))
        self.assertEqual(len(tb.kinds(w.events, "register")), 3, "no re-run is registered after the stop")
        self.assertEqual(b.night_counts, {"harness_error": 3, "failed_after_drive_started": 0})

    def test_the_stop_rides_on_the_blocks_last_take_not_the_one_that_reached_the_count(self):
        plan = {(1, 1): HE, (2, 1): HE, (1, 2): HE}          # the third arrives first in the second block
        b, out, *_ = tb.run(3, plan=plan, row_list=cells(3), cls=batch.Batch)
        carried = [(o["slot"], o["attempt"]) for o in out if (o["stop"] or "").startswith(batch.NIGHTLY_STOP)]
        second_block = [(o["slot"], o["attempt"]) for o in out if o["attempt"] == 2]
        self.assertEqual(second_block[0], (1, 2))
        self.assertEqual(carried, [second_block[-1]])
        self.assertGreater(len(second_block), 1)

    def test_two_do_not_stop(self):
        plan = {(1, 1): HE, (2, 1): HE}
        b, out, *_ = tb.run(3, plan=plan, row_list=cells(3), cls=batch.Batch)
        self.assertIsNone(b.stopped)
        self.assertEqual(b.night_counts["harness_error"], 2)

    def test_serial_blocks_count_across_the_night(self):
        plan = {(s, 1): HE for s in (1, 2, 3)}
        b, out, w, *_ = tb.run(3, plan=plan, row_list=cells(3), serial=True, cls=batch.Batch)
        self.assertTrue(b.stopped["reason"].startswith(batch.NIGHTLY_STOP))
        stops = [o for o in out if o["stop"]]
        self.assertEqual(len(stops), 1)
        self.assertEqual(sum(o["state"] == labels4.HARNESS_ERROR for o in out), 3)

    def test_pauses_are_outside_the_rule(self):
        plan = {(s, 1): "rate-limit" for s in (1, 2, 3)}
        b, out, *_ = tb.run(3, plan=plan, row_list=cells(3), cls=batch.Batch)
        self.assertEqual(b.night_counts["harness_error"], 0)
        self.assertFalse(any((o["stop"] or "").startswith(batch.NIGHTLY_STOP) for o in out))

    def test_a_failed_take_after_its_drive_is_counted_apart(self):
        plan = {(1, 1): "driver-raises", (2, 1): HE, (3, 1): HE}
        b, out, *_ = tb.run(3, plan=plan, row_list=cells(3), cls=batch.Batch)
        self.assertEqual(b.night_counts, {"harness_error": 2, "failed_after_drive_started": 1})
        self.assertFalse(any((o["stop"] or "").startswith(batch.NIGHTLY_STOP) for o in out))


class TheRestart(unittest.TestCase):
    def stopped_repo(self):
        plan = {(s, 1): HE for s in (1, 2, 3)}
        b, out, w, d, r, win = tb.run(3, plan=plan, row_list=cells(3), cls=batch.Batch)
        self.assertTrue(b.stopped["reason"].startswith(batch.NIGHTLY_STOP))
        return r

    def new(self, prior, **kw):
        w = tb.World()
        return batch.Batch(tb.FakeDriver(w), tb.FakeRepo(w, prior=prior), tb.FakeWindow(w), table=tb.test_table(),
                           **kw)

    def test_a_restart_after_the_stop_needs_its_ruling(self):
        r = self.stopped_repo()
        with self.assertRaises(batch.BatchConfigError):
            self.new(r.history())
        for bad in ("", "   ", 3):
            with self.subTest(bad=bad), self.assertRaises(batch.BatchConfigError):
                self.new(r.history(), nightly_stop_ruled_by=bad)
        b = self.new(r.history(), nightly_stop_ruled_by="Javier")
        self.assertEqual(b.night_counts["harness_error"], 0)

    def test_a_ruling_with_no_stop_pending_refuses(self):
        b, out, w, d, r, win = tb.run(1, row_list=cells(1), cls=batch.Batch)
        with self.assertRaises(batch.BatchConfigError):
            self.new(r.history(), nightly_stop_ruled_by="Javier")

    def test_a_restart_without_a_stop_keeps_counting(self):
        plan = {(1, 1): HE, (2, 1): HE}
        b, out, w, d, r, win = tb.run(3, plan=plan, row_list=cells(3), cls=batch.Batch)
        self.assertIsNone(b.stopped)
        b2 = self.new(r.history())
        self.assertEqual(b2.night_counts["harness_error"], 2, "a restart never resets the count (D-4-1)")


if __name__ == "__main__":
    unittest.main()
