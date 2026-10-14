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
since the last committed night ruling (or since the history began), which stops no later than any reading of "one
night". A restart refuses whenever that count is already at three, whether or not the stop text was committed (a
crash or a failed commit can lose the carrier; step-4 review finding 1). The stop is resolved only by a committed,
closed night ruling naming the harness-error that reached the count (D-4-2, a restart argument, is superseded).
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
    PLAN = {(1, 1): HE, (2, 1): HE, (1, 2): HE}      # the third arrives first in the second block

    def stopped(self):
        b, out, w, d, r, win = tb.run(3, plan=self.PLAN, row_list=cells(3), cls=batch.Batch)
        self.assertTrue(b.stopped["reason"].startswith(batch.NIGHTLY_STOP))
        return b, out, r

    def new(self, prior):
        w = tb.World()
        return batch.Batch(tb.FakeDriver(w), tb.FakeRepo(w, prior=prior), tb.FakeWindow(w), table=tb.test_table()), w

    def ruling(self, b, **over):
        return dict({"kind": batch.NIGHT_RULING, "slot": b.night_reaching[0], "attempt": b.night_reaching[1],
                     "by": "Javier"}, **over)

    def test_a_restart_after_the_stop_needs_its_committed_ruling(self):
        b, out, r = self.stopped()
        with self.assertRaises(batch.BatchConfigError):
            self.new(r.history())
        self.assertEqual(b.night_reaching, (1, 2))

    def test_a_crash_before_the_stop_carrier_commits_still_refuses(self):
        b, out, r = self.stopped()
        hist = r.history()
        carrier = [o for o in hist if (o.get("stop") or "").startswith(batch.NIGHTLY_STOP)]
        self.assertEqual(len(carrier), 1)
        crashed = [o for o in hist if o is not hist[hist.index(carrier[0])]]
        self.assertFalse(any((o.get("stop") or "").startswith(batch.NIGHTLY_STOP) for o in crashed))
        with self.assertRaises(batch.BatchConfigError):
            self.new(crashed)

    def test_a_failed_carrier_commit_keeps_the_stop_text(self):
        class FailingRepo(tb.FakeRepo):
            def commit_records(self, row, attempt, outcome):
                if (outcome.get("stop") or "").startswith(batch.NIGHTLY_STOP):
                    raise RuntimeError("synthetic commit failure")
                super().commit_records(row, attempt, outcome)
        w = tb.World()
        b = batch.Batch(tb.FakeDriver(w, self.PLAN), FailingRepo(w), tb.FakeWindow(w), table=tb.test_table())
        out = b.run(cells(3))
        failed = [o for o in out if o["state"] == labels4.FAILED]
        self.assertEqual(len(failed), 1)
        self.assertTrue(failed[0]["stop"].startswith(batch.NIGHTLY_STOP))
        self.assertIn("commit failed", failed[0]["stop"])

    def test_a_forged_or_free_ruling_refuses(self):
        b, out, r = self.stopped()
        hist = r.history()
        for name, rul in (("another take", self.ruling(b, slot=2, attempt=1)),
                          ("empty by", self.ruling(b, by="  ")),
                          ("not a string by", self.ruling(b, by=7)),
                          ("an extra key", dict(self.ruling(b), note="x")),
                          ("a missing key", {k: v for k, v in self.ruling(b).items() if k != "by"})):
            with self.subTest(name), self.assertRaises(batch.BatchConfigError):
                self.new(hist + [rul])
        early = tb.run(2, plan={(1, 1): HE}, row_list=cells(2), cls=batch.Batch)[4].history()
        with self.assertRaises(batch.BatchConfigError):
            self.new(early + [{"kind": batch.NIGHT_RULING, "slot": 1, "attempt": 1, "by": "Javier"}])

    def test_a_ruled_restart_opens_a_new_window_and_drives_exactly_the_granted_reruns(self):
        b, out, w, d, r, win = tb.run(3, plan={(s, 1): HE for s in (1, 2, 3)}, row_list=cells(3), cls=batch.Batch)
        self.assertTrue(b.stopped["reason"].startswith(batch.NIGHTLY_STOP))
        granted = sorted((o["slot"], o["attempt"] + 1) for o in out if o["rerun"])
        self.assertEqual(granted, [(1, 2), (2, 2), (3, 2)])     # one re-run per slot, three half-cells
        try:
            b2, w2 = self.new(r.history() + [self.ruling(b)])
        except batch.BatchConfigError as exc:
            self.fail(f"a committed night ruling did not open a new window: {exc}")
        self.assertEqual(b2.night_counts["harness_error"], 0)
        out2 = b2.run(cells(3))
        driven = sorted((o["slot"], o["attempt"]) for o in out2)
        self.assertEqual(driven, granted)
        self.assertEqual(tb.history_problems(r.history() + [o for o in out2]), [])

    def test_a_restart_without_a_stop_keeps_counting(self):
        plan = {(1, 1): HE, (2, 1): HE}
        b, out, w, d, r, win = tb.run(3, plan=plan, row_list=cells(3), cls=batch.Batch)
        self.assertIsNone(b.stopped)
        b2, _ = self.new(r.history())
        self.assertEqual(b2.night_counts["harness_error"], 2, "a restart never resets the count (D-4-1)")


if __name__ == "__main__":
    unittest.main()
