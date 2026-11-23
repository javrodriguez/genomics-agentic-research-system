# The driver ledger's native history record (live harness integration slice)

Parent: `d56cebf0`. Writer: Claude Code harness lane, 14 Oct 2026 01:11 EDT, under glitch-06's order for the shared-integration items that need no box-branch code.

## What it adds

For an adapter that names a native session (Gemini), `TakeDriver._take_records` now writes `native_history` into the driver ledger.

`drive.native_history_record` runs step 1's `vendor_provenance.session_history_facts` over the take's retained snapshots (3c) through the production reader registry. The result is one of three statuses:

| Status | When | What the record holds |
|---|---|---|
| `pending` | No reviewed native-session reader is registered. This is the state today, and it stays this way until a recorded session is reviewed. | The registry's own reason. |
| `refused` | The snapshots cannot be read, are missing, or a later snapshot rewrites an earlier interaction. | The reason. |
| `joined` | Every later snapshot reproduces every earlier interaction. | The interaction count. |

`joined` is a stability join only. It never admits the take, and nothing routes on it yet.

Claude takes carry no such key, so their ledgers are unchanged.

## N3 confirmation (box lane's answer)

The box lane gives the Gemini temp folder as `GEMINI_CLI_HOME/.gemini/tmp/<project id>`, where `GEMINI_CLI_HOME` is `CONFIG_MOUNT=/opt/cfg`, the take's config folder.

`native_snapshot.gemini_session_file(home, …)` looks under `<home>/.gemini/tmp/*/chats/` for `session-<minute>[-k]-<id8>.jsonl`. The driver passes `take.config_dir` as `home`.

This matches exactly, so no fix was needed. The box also says no `SANDBOX` is set by construction, which retires the third assumption.

## Verification (each run behind a fresh light gate)

- Red: `tests/test_native_history_record.py` ran 3 tests with 1 failure (no key in the ledger) and 2 errors (no function).
- Green: 3/3. `test_native_snapshot` 9/9, `test_executed_turn_refusal` 10/10, `test_drive_commit` 31/31.
- Three in-memory mutants were killed by assertion:
  - pending read as joined;
  - a rewrite not refused;
  - the key written on every take.

## Not run, owed

- The merged-head athena suite.
- Independent review.
- Wiring a status into routing or the checker. That waits for a registered reader and the integration merge.
