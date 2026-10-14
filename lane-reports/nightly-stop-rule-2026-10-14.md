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
