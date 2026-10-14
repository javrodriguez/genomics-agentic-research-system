# Adapter generated-mutant survivors bound in the adapters' own checks (integration item A4, extended)

Writer: Claude Code harness lane, 14 Oct 2026 03:18 EDT.
Source: the athena subset `gap4-harness-ab-86ca78e-20261014T063637Z` (fetched on the Mac; verdict FAIL, `run_checks: 21 of 39`).
It showed the A4 fix (`eace8897`, submitted_mode) was not the whole gap.

- In `test_gemini_adapter --generated-mutants`, all 16 shards were red: survivors in `turn_identity`, the executed-turn road of `_turn`, the journal expectation passed to `submitted_mode`, and `native_session_path`.
  These were bound only by other test files (3a, 3b and 3c), never by this module's own checks.
- In `test_codex_adapter --generated-mutants`, 9 survivors in the executed-turn road of `CodexAdapter._turn`.
- The `test_walk_runner --witnesses` line failed only on the new A3 witness's binding.
  That is fixed in `154293616` (METHOD maps it to its own test).
- Every `test_walk_runner` generated shard passed, shard 8 included (A3).

Bound now, each in the module's own check list, spelled from the rulings and never read from the module:

| Module | Checks added |
|---|---|
| `test_gemini_adapter` | A11-identity, A12-executed, A13-native, A14-journal |
| `test_codex_adapter` | B12-executed |

One new EQUIVALENT category in `test_gemini_adapter`, `unreachable-fallback`, covers two survivors on `self.session_id or 'first-turn'`.
Turn 1's `_read_turn` sets `session_id` before that line reads it, so the fallback is never taken, and `launch_facts` ignores the session on turn 1.
The entry is tied to its line token.

Verification on the Mac (behind a light gate):
- `test_gemini_adapter` 143/143; `test_codex_adapter` 44/44.
- Generated mutants of `gemini_adapter.py`, restricted to the functions concerned, through the module's own sweep code: `turn_identity` 47, `_turn` 126, `native_session_path` 3, `submitted_mode` 106, with 0 survivors.
- The full Gemini and Codex sweeps are athena's and are not run here.

A hook flagged a high-entropy string in one Mac test output. It was a macOS temporary folder path (`/private/var/folders/...`), not a secret.
