# Executed turn refusal (live harness step 3a)

Parent: `f0546df8`.
Writer: Claude Code harness lane, 14 Oct 2026 00:12 EDT, under glitch-06's step-3 order and its ruling on launch journals.

## Problem, reproduced

Gemini's adapter read its stream, checked the exit code and the resumed session before it kept anything of the exec.
A refusal there (an off-table stream, an exit code off D8's table, an init or served model other than the row's, another session resumed) raised a bare `StreamError` out of the driver's turn loop.
The exit, timeout and times were lost, and the driver never wrote its evidence line, quiescence record, ledger row or driver ledger for that turn.
`pre_turn_refusal` reads any `ValueError` as a pre-turn refusal (a rehearsal), so the type alone was one wrong catch away from a free replacement take.
A walk folder holding only a launch journal did not make the driver ledger mandatory.
Red evidence: the new module failed 9 subtests and 1 error before the type existed, then 9 failures by assertion once `agent_adapter.ExecutedTurnRefused` existed and nothing used it (adapter refusals untyped, drive reason "drive failed: synthetic…", the walk folder accepted).

## Change

- `agent_adapter.ExecutedTurnRefused` (with `EXECUTED_FIELDS`): raised only after an exec ran, carrying exactly n, exit_code, timed_out, started_at, ended_at, stream_path, counters, refused.
- `gemini_adapter`: the exec is appended to `executed_turns` before anything is read; the read and the resumed-session check moved verbatim into `_read_turn` (the w11b witnesses' anchors are unchanged); a refusal from there is `ExecutedStreamRefused` (both a `StreamError` and an `ExecutedTurnRefused`). A refusal before the exec (argv) stays a plain `StreamError` and keeps nothing.
- `drive.pre_turn_refusal` returns False for any `ExecutedTurnRefused`, even one that is also a `ValueError`.
- `TakeDriver.drive`: an executed refusal on turn n gets its evidence line from the kept times, quiescence (killed at once when it timed out), the post-n snapshot and a ledger row (`end` None, `refused` named); nothing further is sent; cleanup and postflight run; the driver ledger is written even when it was turn 1, with `first_agent_turn` None (unknown, never False), `executed_refusal`, its stream listed and outcome `incomplete — turn n executed and its record was refused: …`; the scan runs; then `DriveRefused`. Batch records `failed` after the drive started, which needs a ruling, and never re-runs it. The checker never reads it. A walk is held, never committed.
- `walk_files` counts `turn-N.jsonl.launch.json` as a turn that ran, so a walk folder holding one without `driver-ledger.json` refuses.
- `test_gemini_adapter.py`: 14 `EQUIVALENT` keys renumbered for the shifted lines only.

## Verification (each run behind a fresh light gate)

- `tests/test_executed_turn_refusal.py`: 8/8.
- `tests/test_gemini_adapter.py`: 138/138; `tests/test_agent_adapter.py`: 35/35.
- Seven in-memory source mutants, each killed by assertion with no errors: the pre-turn guard dropped; the stop after the scan dropped; unknown output read as False; the ledger skipped on turn 1; the launch journal not a turn; the exec kept after the read; the refusal untyped. Candidate bytes unchanged.
- `copy_manifest.py --check`: ok, 373 files.

## Not run, owed

- `test_box_integration.py`, `test_walk_runner.py`, `test_drive_loop.py`, `test_gemini_adapter.py --generated-mutants` and the full battery (merged-head athena suite).
- Codex's adapter does not yet raise `ExecutedTurnRefused`; its parse ordering needs the same treatment in its own slice.
- `counter_delta` is still computed before the exec is kept; a counter read failure after the exec would lose the exec record (a harness defect road, not the parse road).
- Independent review.
