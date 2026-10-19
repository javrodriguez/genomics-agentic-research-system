VERDICT: PASS

Review of lane vendor-b19 round 3, range 756686f9..149cb980 (lane/vendor-b19), against glitch-26's rulings B19-12 to
B19-17 and the lane file's ROUND 3 SUMMARY FOR REVIEW. Fresh cloud reviewer for glitch-26; I did not write this change.
The change is to the evaluation harness's take loop (sealed containers, planted analysis faults and clean controls).
No agent, take, container or model call was launched for this review. Line numbers are at 149cb980.

## The round 2 review's findings

1. MINOR, holds unpinned behind a slow head: CLOSED.
   - tests/test_batch_rolling.py:719 and its neighbours add three checks: stop_hold_problems, nightly_hold_problems
     and closing_hold_problems, each with a slow head (units {1: SLOW}). They are pinned by TestHoldsBehindASlowHead.
     Each check also checks that its scenario actually happened (drive-end order), so a check cannot pass
     vacuously.
   - Each of the five witnesses, run alone through unittest, is red against its bound check, and that check is green
     on the tree first: held-stops-dropped (3 problems), held-nightly-dropped (1), held-pause-only-stops (3),
     held-pause-only-nightly (1), closing-cells-empty (2).
   - I applied the review's third mutant as a file edit on a scratch copy, outside the witness machinery: `_held`
     ignoring finished drives (`return False` before the finished reading). It is red in 2 of the 3 holds tests.
   - The closing hold for a pause is still unpinned; see NIT 2.
2. MINOR, equal-duration equivalence non-deterministic: CLOSED.
   - tests/test_batch.py's `wait_open` and `committing_loop`, World.wait_wave and EqualRepo.commit_records now wait on
     the loop's own open futures. The SETTLE sleep is gone from both modules.
   - When `equal` is set, TimedDriver ends a wave's other drives only after the head's commit has begun.
   - TestEqualDurations: 30 of 30 runs green.
   - The tie-rule mutant (`while` to `if` in `_commit_finished`, batch.py:952) still turns both scenarios red, so the
     test passes for the right reason.
   - The note's section 2, section 3's opening and the B19-6 Rulings line are reworded as ruled.
3. NIT, nightly carrier set before the gate: CLOSED. batch.py:1024 sets the carrier after the wave's launches.
   TestNightlyCarrier (test_batch_rolling.py:632) was red at 756686f9 in both subtests, per the summary, and it is red
   again under my revert mutant.
4. NIT, `_drain`'s throwaway queue: CLOSED. The docstring is at batch.py:1027-1029.
5. NIT, `_front` not reset by run(): CLOSED (batch.py:931).
6. NIT, prose: CLOSED. takes.py's guard_registration docstring, costs.py:13 and test_batch's header are reworded. The
   items the round 2 review said to keep are kept.
7. NIT, production driver and repo never overlapped: FOLLOW-UP. B19-16 records it for the rehearsal walk on athena.
8. NIT, a ruled pause counted as its own event: FOLLOW-UP. B19-17 records it as ruled; nothing changed.

## Threat model

(1) Covered above: both MINOR findings are closed, each with tests, and every witness is red alone.

(2) The equivalence now passes for the right reason: it is deterministic, and the tie-rule mutant still kills it.
- The timed fake's change hides one thing: a reading that sees part of a wave finished, with the rest unfinished.
  That is exactly the rolling of equal-length real drives, which the reworded claim already concedes. It hides
  nothing beyond that.
- The holds read from finished but uncommitted drives are what the equal model can no longer reach. They are now
  exercised by the slow-head checks, which run without `equal`.
- The other uneven-time tests are unaffected, because `equal` defaults to False.

(3) The carrier keeps the nightly stop's meaning.
- The carrier is set only after `_launch_paid_checked` has run for every row of the wave, and the main thread does no
  commit between registration and that point.
- On a gate refusal or a register failure, the function returns before the carrier line. The carrier stays on the
  last take of the previous launched wave, which is committed through the drain.
- A take refused at the per-launch re-check (W7C-R1-3) is still committed `failed`, so the carrier never names an
  uncommitted row.
- Commit order is launch order, so any take whose commit reaches the count is committed no later than the carrier.
  The carrier therefore always commits after `_night_reached` is set.

Mutants on the carrier:
- Carrier moved back before the gate (my mutant): red in both TestNightlyCarrier subtests.
- Carrier on the wave's first row: red in TestNightlyCarrier, and test_nightly_stop hangs (see NIT 1).
- Carrier set once and never updated: the batch hangs (see NIT 1).

(4) Nothing was loosened. EQUAL's expected traces are unchanged. No assertion in test_batch or test_batch_rolling was
removed or relaxed. The serial mutant test only sets `equal` on its driver. The only test_batch change is to the
fakes' wait.

## New findings

1. NIT. Two gaps around the carrier.
   - batch.py:933-952 (the run loop). If `_night_reached` is set and the carrier has already committed, `_held` returns
     True with nothing open and a non-empty queue. The loop then spins: no fill, no wait, no exit.
     - This is unreachable on the tree, by the ordering argument in (3).
     - Under a carrier mutant it shows up as a hang, not a red test. tests/test_nightly_stop.py has no hang detector,
       and test_batch_rolling's checks rely on RUN_S.
   - Missing check: with nothing open, a hold that cannot clear should stop the loop rather than spin, or the module
     should have a hang detector.
   - Separately, nightly_hold_problems (test_batch_rolling.py:719) cannot tell "last of the wave" from "first of the
     wave": its carrier wave is one row. The carrier-first mutant passes it and is caught only by TestNightlyCarrier.
     Missing check: a nightly scenario whose last wave holds more than one row.
2. NIT. `_closing_cells`' pause branch (batch.py:993-995) is unpinned behind a slow head.
   - The summary's argument holds: `_held` (batch.py:981) already holds every launch on a finished pause, so the
     closing hold cannot be observed for a pause.
   - The cost is that a regression to the pause event key there would show up only if `_held`'s pause reading were
     also removed.
   - No hold can be skipped today.
3. NIT. TimedDriver.wait_idle (tests/test_batch_rolling.py:118) is unused, as the summary says. It could go in a later
   tidy.

No MAJOR or MINOR finding is open.

## Checks

Each ran in the foreground under `env -i` with only PATH, HOME, LANG and TMPDIR (a `mktemp -d`, /tmp/tmp.mZRF79C7kY,
outside the clone), from evals/gap-study-4 at 149cb980.

| Check | Result |
|---|---|
| tests.test_batch_rolling | 36 tests, OK |
| tests.test_batch | 118 tests, OK (3.3 s) |
| tests.test_nightly_stop | 13 tests, OK |
| tests.test_pipeline | 85 tests, OK |
| tests.test_spend_wiring | 25 tests, OK |
| witness held-stops-dropped, alone | red (stop-hold, 3 problems) |
| witness held-nightly-dropped, alone | red (nightly-hold, 1) |
| witness held-pause-only-stops, alone | red (stop-hold, 3) |
| witness held-pause-only-nightly, alone | red (nightly-hold, 1) |
| witness closing-cells-empty, alone | red (closing-hold, 2) |
| TestEqualDurations, 30 runs in a loop, unmodified | 30 OK, 0 FAIL |
| mutant: carrier set before the money gate (round 2's place) | red: TestNightlyCarrier, both subtests |
| mutant: carrier on the wave's first row | red: TestNightlyCarrier; test_nightly_stop hangs (NIT 1); nightly-hold check survives |
| mutant: carrier set once, never updated | batch hangs under the 400 s cap (NIT 1) |
| mutant: `_held` ignores finished drives | red: 2 of 3 TestHoldsBehindASlowHead |
| mutant: tie rule (`while` to `if`, batch.py:952) | red: TestEqualDurations, both scenarios |

Mutants ran on a `git archive` copy at /tmp/tmp.tJQyvF68bJ, outside the clone, which is left in place. batch.py was
restored after each mutant and checked byte-identical to the tree's with cmp.
