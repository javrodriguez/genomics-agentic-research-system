# The nightly stop rule (live harness step 4)

Parent: `91eb1754`. Writer: Claude Code harness lane, 14 Oct 2026 00:41 EDT, under glitch-06's ruling to build it as step 4.

## Registered text, quoted

`/Users/javrodher/glitch/plans/gap-study-round-4.md`:
- Line 904: "Routing follows the pre-registered table, and three `harness-error`s in one night stop the run for a ruling."
- Line 560: "Every turn's `system`/`init` event is checked for model id, permission mode, tools and version. A mismatch is routed by the routing table: a rehearsal before the first turn, `harness-error` after it. Three in one night stop the run for a ruling."
- Line 196: a pause is "re-run in the same slot under round 3's `pause_cap`, outside the nightly stop rule".

Before this slice the rule had no code at all, which the 3b reviewer confirmed independently.

## Change (`batch.py`, THE NIGHTLY STOP)

- `NIGHTLY_HARNESS_ERRORS = 3`. The loop counts the `harness-error` outcomes it commits.
- When the count reaches 3, the block's last committed outcome carries `stop` = `nightly stop rule: …`, `stopped` says so, and nothing further is registered. Re-runs already granted stay owed to a restart.
- Pauses are never counted (line 196).
- A take `failed` after its drive started (the executed-refusal road) is counted apart in `night_counts["failed_after_drive_started"]` and never consumed by the rule. D-3a-1 found it is no registered harness-error, and it stops the loop on its own anyway.
- Lines 560 and 904 together count `harness-error` outcomes. My reading: line 560's "three" may mean init mismatches only, which are routed to harness-error and so are a subset; counting every harness-error satisfies both lines and is the stricter reading.

## Named departures (the registered text is silent here)

- **D-4-1, the counting window.** No registered text defines "night", and no committed outcome carries a time (`OUTCOME_KEYS` is closed).
  - The window is every harness-error committed since the last committed nightly stop, or since the history began. A restart rebuilds the count from the history.
  - Any three harness-errors in one night are also three since the last stop, so this never stops later than any reading of "one night".
  - It can stop earlier, when harness-errors from different nights add up. That costs a ruling, never a weaker check.
  - Harness-errors committed in the same block after the take that reached the count are counted toward the next window.
- **D-4-2, the ruling.** The closed ruling record (`RULING_KEYS`, per slot and attempt) has no road for a run-level stop.
  - The ruling is the person named by `Batch(..., nightly_stop_ruled_by=…)` at the restart. It is never inferred, and it is not committed.
  - A restart after a committed nightly stop refuses without it (`BatchConfigError`).
  - Naming a ruling when no stop is pending refuses.
  - "Pending" means the last committed outcome carries the stop.
  - Committing that ruling as a record is a later CP5 tooling item, if the orchestrator wants one.

## Verification (each run behind a fresh light gate)

- Red: `tests/test_nightly_stop.py` ran 9 tests with 1 failure and 8 errors (no constant, no counts, no keyword). The one real failure: three harness-errors in one block were each re-run and graded, with no stop.
- Green: `test_nightly_stop.py` 10/10 (the reaching-take case was added after a mutant survived).
- Neighbours green:
  - `test_batch.py` 118/118. `test_harness_error_two_reruns_per_half_cell` now reads the two granted re-runs from the committed fates, because its three harness-errors in one block now stop the run.
  - `test_spend_wiring` 25, `test_cp6_wiring` 5, `test_drive_commit` 31, `test_routing` 276, `test_executed_turn_refusal` 9, `test_native_snapshot` 9.
- Seven in-memory mutants, all killed by assertion, candidate bytes unchanged:
  - count of four (errors besides the failures);
  - pauses counted;
  - failed takes consumed by the rule;
  - a restart resets the count;
  - no ruling gate;
  - the stop not committed (errors besides the failures);
  - the stop on the reaching take rather than the block's last.
- The first witness run showed that `test_batch.run`'s default `cls` binds the real class, so the tests now pass `cls=batch.Batch` explicitly.

## Not run, owed

- `test_box_integration.py`, `test_drive_loop.py`, `test_walk_runner.py`, `test_pipeline.py` and the full battery: these go to the merged-head athena suite.
- A committed ruling record for the nightly stop (D-4-2).
- Independent review.

## Addendum, 14 Oct 2026 00:54 EDT: review CHANGES (MAJOR) and the fix; D-4-2 superseded

The independent review of `eacd901f` (`/Users/javrodher/aegis-builds/gap4-review-harness-step2-20261014/review-harness-step4.md`) found a crash bypass. The text above stays as written, and this addendum corrects it.

What was wrong, and the fix:
- **Wrong above:** "a stop is pending when the last committed outcome carries the stop". The take that reaches 3 commits first, and the stop text rode only on the block's last outcome, which commits later.
  - A crash in between, or a failed commit of that outcome (which rewrote `stop` to "commit failed"), left three harness-errors and no carrier.
  - The restart then ran on with no ruling. The reviewer's `witness_step4.py` showed this.
- **Now:** on replay a stop is pending whenever the harness-errors committed since the last committed night ruling are already at 3. The stop text is a marker for a reader, never what the replay trusts. A restart with a pending stop always refuses (`BatchConfigError`).
- **Commit failures:** a failed commit of the carrier keeps the nightly text, as `nightly stop rule: …; commit failed: …`.
- **D-4-2 is superseded and retired.** The `nightly_stop_ruled_by` restart argument is gone. A stop is resolved only by a committed, closed run-level record, `{"kind": "nightly-stop-ruling", "slot", "attempt", "by"}`:
  - It must name the harness-error that brought the window to 3, and it must come while the count stands there.
  - Its `by` is checked exactly as batch's existing take rulings check theirs (a non-empty string). Note that those rulings have no closed principal set either, so I did not invent one.
  - The record closes the window, and the next one starts at 0.
  - The loop reads it and never writes one.
- **D-4-1 sentence, corrected:** I wrote that harness-errors committed in the same block after the reaching take "are counted toward the next window". Wrong: in-process the loop stops after the block, and on replay those harness-errors fall in the stopped window, which only a night ruling closes.

Verification, each run behind a fresh light gate:
- **Red:** the new `test_nightly_stop.py` run against `03a4f489`'s module gave 2 assertion failures (crash bypass, lost stop text) and 3 errors (no night ruling API).
- **Green:**
  - `test_nightly_stop.py` 13/13.
  - `test_batch.py` 118/118. The cap test now also restarts after a committed night ruling and drives exactly the granted re-runs (1,2) and (2,2), with `history_problems` clean (nit 4).
  - `test_spend_wiring` 25, `test_cp6_wiring` 5, `test_drive_commit` 31.
- **The reviewer's `witness_step4.py`:** the crash witness now errors with `BatchConfigError` (the finding is gone). Its mutant witnesses still kill.
- **Ten in-memory mutants**, tests passing `batch.Batch` at call time. Nine are killed by assertion; "count of four" fails 4 tests and also raises errors in others.
  - The killed mutants: pending only with a committed carrier, a ruling for any take, a ruling by anyone, a ruling that keeps the count, a failed commit that drops the stop, pauses counted, failed takes consumed, the stop on the reaching take, and count of four.
  - One survives as equivalent: "a ruling with no stop pending". The reaching take is set only when the count reaches 3 and is cleared with it, so the name check already refuses. The guard stays for its clearer message.

## Addendum, 14 Oct 2026 01:04 EDT: the night ruling through the production history

Review `review-harness-step4fix-5-6.md` passed `02682294`, but found that a committed night ruling would make the production history unreadable.
- `takes.read_history` and `Batch.history_problems` refused it as a malformed outcome.
- `takes.commit_ruling` can only write take rulings.
- Every reader that filtered with `not is_ruling` would have read it as an outcome.

The fix:
- `batch.is_outcome` is the one shared predicate for a committed outcome. It excludes take rulings and night rulings, and every outcome reader now uses it:
  - `batch.restart_waits` and the final-attempt checks;
  - `check_results` (two outcome lists and the publication walk);
  - `takes` (the done maps and `registration_outcomes`);
  - `run.py`'s outcome check;
  - `drive.py`'s `leaked_ids` and launch registration map.
- `effective_route` returns None for a night ruling.
- `Batch.history_problems` reads a night ruling by its kind and checks it through `_night_walk`. That walk runs the loop's own `_count_night` on a bare state object, so one counter serves both the loop and every reader.
- `takes.commit_night_ruling` is the one door for a night ruling, with `commit_ruling`'s discipline:
  - `by` is required and never defaulted;
  - the record is checked against the committed history before anything is written;
  - the tree must be clean;
  - the commit needs an identity;
  - it is one commit.

Verification, each run behind a fresh light gate:
- **Red:** `tests/test_night_ruling_history.py`, which uses a throwaway git repository and the real `read_history`, ran 3 tests with 2 failures and 1 error. The real reader refused a committed night ruling, and there was no door.
- **Green:** 3/3. Neighbours: `test_nightly_stop` 13, `test_batch` 118, `test_drive_commit` 31, `test_pipeline` 85, `test_cp6_wiring` 5, `test_spend_wiring` 25.
- **Mutants:** three attribute-level mutants were killed:
  - `is_outcome` counts a night ruling;
  - `history_problems` skips the night semantics;
  - the door writes unchecked.
  A fourth was malformed (it recursed into itself) and was dropped, not counted.

## Addendum, 14 Oct 2026 01:27 EDT: batch-5 review finding 3

`cell_history_problems` skipped only take rulings, so it read a night ruling as an outcome and raised `KeyError: 'half_cell'`. `check_results.publication`, and through it `run.produce`, therefore crashed on any history holding a committed night ruling.

Fix: `cell_history_problems` now skips any entry that `is_outcome` rejects.

Test: `test_night_ruling_history.test_publication_reads_a_history_holding_a_night_ruling`, which uses the real repo and the real door.
- Red against the unfixed `batch.py`: 1 failure.
- Green: 4/4.
- The publication equals the one without the ruling.
