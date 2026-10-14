# Codex parity for executed refusals (live harness slice 6)

Parent: `04d50af0`. Writer: Claude Code harness lane, 14 Oct 2026 00:51 EDT, under glitch-06's order for slice 6.

## Problem, reproduced

The Codex adapter read its stream, checked the resumed thread, and fetched and read the rollout, all before keeping anything of the exec.
A refusal at any of those points lost the exit code, timeout status and times.
It raised as a bare `StreamError`; a missing rollout raised as an `OSError`.

Red evidence: `tests/test_codex_executed_refusal.py` ran 4 tests, with 3 failures and 2 errors.
- The refusals were untyped.
- An unreadable rollout raised `StreamError not raised`.
- `CodexAdapter` had no `executed_turns`.

## Change

- `codex_adapter._turn` keeps the exec in `executed_turns` before any read: n, exit, timeout, times, stream path, counters.
- `_read_turn` holds the stream read, the resumed-thread check and the rollout read, moved verbatim. The w11a witness anchors are unchanged.
- A refusal raised from `_read_turn` becomes `ExecutedStreamRefused`. That covers `StreamError`, `OSError` and other `ValueError`s, including the rollout callback's.
  - `ExecutedStreamRefused` is both a codex `StreamError` and an `agent_adapter.ExecutedTurnRefused`, so the driver's 3a road applies unchanged.
- Any other exception type still propagates as a defect. The drive then fails, and batch records it as failed after drive start, which needs a ruling.
- No Codex identity-source table was added. An `identity` on a codex record stays refused, pending the rollout source audit.

## Verification (each run behind a fresh light gate)

- `tests/test_codex_executed_refusal.py`: 4/4.
  - After a mutant showed that an escaped `OSError` was judged only as an error, the refusal helper was strengthened to judge any escape by assertion.
- `tests/test_codex_adapter.py`: 42/42.
- `tests/test_executed_turn_refusal.py`: 9/9.
- Four in-memory mutants, each killed by assertion with no errors, candidate bytes unchanged:
  - exec kept after the read;
  - refusal untyped;
  - a failed rollout fetch not caught;
  - the reason not kept.

## Not run, owed

- `test_codex_adapter.py --generated-mutants`.
- The merged-head athena suite.
- Independent review.
