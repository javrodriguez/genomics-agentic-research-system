VERDICT: CHANGES

Review of lane vendor-b19, range 7dc0cf9e..27249def (the whole lane), against the design note's Rulings section
(lane-reports/B19-DESIGN-NOTE.md section 10) and the lane file's ROUND 1 and ROUND 2 summaries. Fresh cloud reviewer
for glitch-26; I did not write this change. The change is to the evaluation harness's take loop (sealed containers,
planted analysis faults and clean controls); no agent, take, container or model call was launched for this review.
Line numbers are at 27249def unless stated.

## Findings

1. MINOR. The stop and cap holds read at a drive's finish are pinned by no test; mutants that remove them survive
   every module this review ran. evals/gap-study-4/batch.py:980-984 (`_held`: blocked, failed or a leak seen
   finished, and THE NIGHTLY STOP's count in prospect) and batch.py:986-997 with 1007-1009 (`_closing_cells`, the
   closing half-cell hold B19-5 adds to glitch-f3's cap ruling). The re-pinning moved test_batch's fakes to the
   equal-duration model (World, test_batch.py:186-213). Under that model every wave is committed before the next
   fill, so the finished-but-uncommitted reading is always empty and these holds never fire. The block-era stop and
   cap tests still pass, but they no longer run the code that carries those rules under real, uneven drive times.
   That makes the re-pinning a weakened check for item (5) of the threat model. Mutants on a scratch copy outside the
   clone, run against test_batch, test_batch_rolling, test_nightly_stop and (the third) test_spend_wiring:
   - `_closing_cells` replaced by an empty set: all green. The one red in the first run was the equivalence flake of
     finding 2; it was green on 3 of 3 reruns.
   - `_held` keeping only the pause reading (no blocked, failed, leak or nightly prospect): all green.
   - `_held` ignoring finished drives entirely: only test_batch's test_pause_launches_no_new_drive_until_reset is red.

   By reading, the code is right: no invariant breaks today (see "Invariants traced" below). But a regression that
   launches new drives after a blocked, failed or leaking take, after the nightly count is reached, or into a
   half-cell about to close would pass the battery.
   Missing checks, all in tests/test_batch_rolling.py, with a slow head (units={1: SLOW}):
   - a later row ends blocked, failed or leaking behind the slow head, and no row is registered after its drive-end;
   - a harness-error behind the slow head brings the count to NIGHTLY_HARNESS_ERRORS, and nothing is registered after
     it; the stop is carried by the last take launched;
   - a rehearsal or pause behind the slow head would close its half-cell, and no further row of that half-cell is
     registered before its commit.

   Each should go red under the matching mutant above.

2. MINOR. The equal-duration equivalence (B19-1, B19-6) is non-deterministic, and on unmodified code it sometimes
   reproduces a history that differs from the block run's. tests/test_batch_rolling.py:111-119 (EqualRepo: wait idle,
   then `time.sleep(SETTLE)`, SETTLE = 0.05 at line 55) and 297-306 (TestEqualDurations). On this container, with
   batch.py unmodified, TestEqualDurations failed 1 run in 12 in a dedicated loop, plus once more in about 8 other
   runs of the module. Failing case: "reruns, a shared pause and an abort", with registrations `..., (7, 1), (7, 2),
   (8, 1), (9, 1)` against the block run's `..., (7, 1), (8, 1), (9, 1), (7, 2)`.

   When a wave's drives end a few milliseconds apart and the loop reads the futures inside that skew, it correctly
   fills the freed lane. That is the rolling design working, and the lane summary says as much ("real equal ends are
   ties in time"). The consequence is that the equivalence holds only under the fake's settle model, not for real
   drives of equal length. On real near-equal times, registration order, re-run placement and so which pauses share a
   window event (the published pause count per half-cell) can differ from the block run's.

   Two things are needed:
   - Make the check deterministic. EqualRepo.commit_records, and test_batch's World.wait_wave
     (test_batch.py:206-213), should wait until every future in the loop's `open` deque is `done()` rather than
     sleeping SETTLE. The test can reach `b.open`.
   - Have glitch-26 rule on the claim's wording. The note's section 2 and the Rulings' B19-6 line should read: "equal
     durations" means drives the loop observes finished at one reading, and real drives of equal length may roll.

   test_batch was stable: 7 of 7 runs green.

3. NIT. The nightly stop's carrier is set before the money gate and registration (batch.py:1016, then 1017 and 1019).
   On a gate refusal or a register failure, `_block_last` names a row that is never committed. If the open takes
   drained afterwards (batch.py:1098, or the loop's own drain after a refusal) bring the count to
   NIGHTLY_HARNESS_ERRORS, no committed outcome carries the NIGHTLY_STOP text. The replay recomputes the count, so no
   fate or count moves; the block loop could not meet this, because nothing was open at its gate. Set the carrier
   after the wave is launched (batch.py:1021).

4. NIT. `_drain` commits into a throwaway queue (batch.py:1029). A re-run decided while draining after a register
   failure is never put back on the live queue, and `_front` is bumped against the wrong deque. This is harmless,
   since the loop has stopped and the restart owes the re-run from the history (W1B3-6), but say so in the docstring.

5. NIT. `run()` resets `self.open` but not `self._front` (batch.py:930). A second `run()` on one Batch would start
   with a stale front count. Production calls it once.

6. NIT. Prose still naming the block:
   - takes.py:244 (guard_registration's docstring, "registered by this instance in its current block");
   - the name `outside_live_block`;
   - costs.py:13;
   - drive.py's TakeRepo docstring (the last two left on purpose, per note 5.4);
   - `_money_gate`'s refusal text, "refuses the block" (batch.py:1056; the docstring says it is kept).
   test_batch.py:11 still says "never with sleeps" while World now sleeps SETTLE (line 213).

7. NIT. Concurrency outside the fakes. A real `TakeDriver.launch`, and `TakeRepo.register` / `commit_records`, now
   run while other takes' `drive()` is in flight; in the block loop a launch never overlapped a drive. TakeDriver
   guards its maps with `_lock` (drive.py:2145, 2164, 2172), and commit_records stages only declared names
   (drive.py:1697-1705), so another open take's folder cannot reach a commit. Even so, no test exercises the
   production driver or repo under that overlap: every overlap test uses the fakes. A rehearsal walk on athena would
   be the first.

8. NIT (ruled, recorded for completeness). B19-6 makes publication count a ruled pause as its own event
   (check_results.py pause_event). For a history with a ruled pause, the published per-half-cell count can therefore
   differ from what the block-era publication read (test_pipeline's former ..._its_existing_block_once). The ruling
   accepts this. The equivalence scenarios hold no ruling, so B19-6's "equal" covers runs, not ruled histories.
   test_pipeline.py:1115 now checks the strict-close label only under a patched block reading of pause_event. With
   the new pause_event, publication and batch agree, so that label may be unreachable unpatched; worth a line in the
   test.

## Threat model, item by item

(1) Invariants under uneven drive times. I traced them by reading `run`, `_commit_finished`, `_finished`, `_held`,
`_fill`, `_register` and `_drain`; the drive steps touch no loop state, and the main thread alone registers,
launches and commits.
- At most BLOCK drives: the pool has `max_workers=self.block`, and `free = block - (open - finished)` counts only
  futures read done, so a drive ending after the reading frees no lane.
- At most MAX_OPEN open: `n <= MAX_OPEN - len(open)` (batch.py:1006), and a wave is registered whole before any
  launch, so registered-but-uncommitted takes are at most 12. A register-failure wave counts inside the same bound.
- Launch after registration: `_register(wave)` finishes before any `_launch_paid_checked`.
- Commit order: only the head of `open` is committed (`while open[0].done()`), and launch order is queue order. The
  register-failure path drains the older open takes before the wave's registered rows.
- Re-runs requeued first: `queue.insert(_front)`, with `_front` decremented by each wave's take and recomputed by
  `_drop_closed`.
- Driven twice or never: a row leaves the queue only into a wave. A wave refused by the gate is unregistered and the
  loop stops, as in the block loop. A slot cannot have two open takes, because its re-run is queued only at its
  commit.
- Races: a pause, stop or harness-error that finishes during a registration or commit is seen at the next reading.
  The wave already decided still launches; that is within the rulings, since the hold is read at a finish. No more
  than BLOCK pauses can share an event: the takes launched before the first pause is seen number at most the drives
  in flight at the last fill.
- No busy loop or deadlock: the wait runs only when the head is unfinished and something runs; with nothing open,
  every hold reads empty.
- Mutants:
  - open bound (`MAX_OPEN + 1`): red in 3 tests of test_batch_rolling;
  - commit order (commit any finished take, not only the oldest): red in 6 of test_batch_rolling and 9 subtests of
    test_batch;
  - tie rule (one commit per pass): red in TestEqualDurations and 6 of test_batch.

(2) Equal times. Under the fakes' model, the rolling run's registrations, launches, commits (every fate key and
window_event), waits, window problems, window events and pause counts per half-cell equal the block run's traces read
from 7dc0cf9e and 94963ea7. The comparison can fail (the serial mutant, and the tie-rule mutant above). It is not
meaningful beyond the settle model, and it flakes: finding 2.

(3) Restart with twelve open. After the first pause is seen, at most 11 outcomes can be committed after it. A pause
take is open until it commits, every later commit was launched after it, open + wave <= 12, and nothing launches
after the hold. So `restart_waits` over `[-MAX_OPEN:]` (batch.py:347) always sees it.
TestRestartOwesTheOpenTakes stops with twelve open, owes slots 1 to 12 at attempt 2, waits for the window and
re-registers them in row order before slot 13. The old `[-BLOCK:]` span is a mutant there and goes red. Owed drives
are refused when left out of the rows (W1B3-6).

(4) Loosened tests? Each re-pinned check still fails on the fault it was written for, except where findings 1 and 8
say otherwise.
- test_batch:
  - test_commits_land_serially_in_row_order now uses rolling_order_problems over the run, with two can-fail mutations,
    and is red under my commit-order mutant.
  - The restart_waits mutants are re-anchored on `[-MAX_OPEN:]`, and the old BLOCK span is pinned red in
    test_batch_rolling.
  - The equal-model fakes keep the block-era tests green, but at the cost in finding 1.
- test_pipeline:
  - finishing-block now restores the old refusal and goes red;
  - past-max-open is OPEN_LIMIT = MAX_OPEN + 1;
  - pause-count-refusal, pause-event-identity and pause-note-other-cell are re-anchored on the new pause_event;
  - the stale-row (outside the live set) check is unchanged;
  - the three renamed tests assert the ruled behaviour, not less of it.
- test_spend_wiring: gate-never-called and gate-after-register are the same mutations on the wave's text, and both
  are red (the module is green with its witnesses).

(5) Meaning against the Rulings.
- Money gate: per wave, before registration, with the per-launch re-check unchanged (W7C-gap4-1 as re-ruled).
- Nightly stop: the count and replay are unchanged, and the carrier is the last take launched; see finding 3.
- Cap and closed-cell drops: `_drop_closed` runs before every fill. An open take of a closing half-cell is committed
  with the cell state.
- Usage-window pause: an event is the pauses between two waits, the wait comes only with nothing open, and
  `_block_event` is cleared after it.

The meaning matches B19-5. The holds that enforce it under uneven times are unpinned (finding 1).

(6) routing.json. Parsed before and after: equal in every key except `caps.pause.source`, which is prose. No rule,
cap, value or route moved. The sha256 values match the summary: routing.json e69f468e…3e43387, prereg-draft.json
0aed2a2c…0257ae.

## Checks

Each ran in the foreground under `env -i` with only PATH, HOME, LANG and TMPDIR (a `mktemp -d` outside the clone),
from evals/gap-study-4 at 27249def.

| Check | Result |
|---|---|
| tests.test_batch_rolling | 26 tests, OK (flaky on reruns: finding 2) |
| tests.test_batch | 118 tests, OK; 7 more runs, all OK |
| tests.test_pipeline | 85 tests, OK |
| tests.test_spend_wiring | 25 tests, OK |
| tests.test_routing | 297 tests, OK |
| tests.test_nightly_stop | 13 tests, OK |
| copy_manifest.py --check | ok: 489 files from 60 fragments |
| build_draft.py --check | ok: the committed draft is what build_draft.py builds |
| routing.json structural diff vs 7dc0cf9e | only caps.pause.source differs |
| mutant: open bound (`MAX_OPEN + 1` at batch.py:1006) | red: test_batch_rolling, 3 failures |
| mutant: commit order (commit any finished take) | red: test_batch_rolling, 6; test_batch, 9 |
| extra mutant: tie rule (`while` to `if`, batch.py:956) | red: TestEqualDurations; test_batch, 6 |
| extra mutant: no prospective holds in `_held` | red only in test_batch's pause test (finding 1) |
| extra mutant: pause-only `_held` | survives all four modules run (finding 1) |
| extra mutant: no closing half-cell hold | survives (finding 1) |
| TestEqualDurations, 12 runs, unmodified | 11 OK, 1 FAIL (finding 2) |

Mutants ran on a `git archive` copy at /tmp/tmp.meHcljXxa6, outside the clone, which is left in place. batch.py was
restored after each mutant and checked byte-identical with cmp. Whole GARS suites were not run, as instructed.
