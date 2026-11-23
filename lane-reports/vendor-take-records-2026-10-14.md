# Vendor take records (live harness integration slice)

Parent: `beecc274`. Writer: Claude Code harness lane, 14 Oct 2026 01:15 EDT, under glitch-06's go for the vendor `_take_records` path.

## Problem, reproduced

`_take_records` looked for Claude Code's session file on every take.
A Gemini or Codex take therefore always recorded `cross_check: ["no session file for …"]`, and appended "— no session file" to its outcome, as if its own evidence were missing.

Red evidence: `tests/test_vendor_take_records.py` ran 4 tests, with 2 failures ("no session file" found in the Gemini and Codex ledgers) and 1 error (no `cross_check_status`).

## Change (`drive.py`)

For a take whose row harness is in `VENDOR_HARNESSES` (codex, gemini):
- Claude's session file is never looked up, no transcript is published, and the outcome keeps no "no session file" suffix.
- The cross-check comes from the harness's own native evidence, through `vendor_cross_check_status`.
- Every vendor ledger gains `cross_check_status: {status, why}`.

| Harness | Native evidence state | `cross_check_status` | Ledger `cross_check` |
|---|---|---|---|
| Gemini | No reviewed reader is registered (today) | `pending`, with the registry's reason | `None` |
| Gemini | Snapshots missing, unreadable or inconsistent | `refused` | `[why]`, a real problem, so the checker reads readers-disagree |
| Gemini | Snapshots join | `pending`: the stream join to them is still unregistered | `None` |
| Codex | Any | `pending` until the rollout source audit lands | `None` |

`cross_check` is never `[]` (a fabricated pass) and never "no session file". Codex states no `native_history`. Claude takes are unchanged.

## Verification (each run behind a fresh light gate)

- `test_vendor_take_records.py`: 4/4.
  - The fakes patch the vendors' PENDING billing-route names to empty, test-only, exactly as `test_gemini_adapter` does.
- Neighbours:
  - `test_native_history_record` 3/3.
  - `test_native_snapshot` 9/9.
  - `test_executed_turn_refusal` 10/10.
  - `test_drive_loop` 27/27, which exercises the Claude road through the real adapter.
- Four in-memory mutants, each failing at least one assertion:
  - a vendor reads Claude's file (one test also errored);
  - pending recorded as a pass (`[]`);
  - a refusal not recorded as a problem;
  - Codex passing.
- A note on the tooling: the secret-output hook flagged a high-entropy string in one debug output. It was the macOS temporary-folder path (`/private/var/folders/…/T/…`), not a credential.

## Not run, owed

- The checker (`take_checker`) still returns readers-disagree for any take without `transcript.jsonl`, so every vendor take reads readers-disagree there. A vendor checker road (a vendor transcript, or a typed pending) is the next item.
- The merged-head athena suite.
- Independent review.
