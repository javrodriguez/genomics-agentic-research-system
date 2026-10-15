# Native snapshot retention before each resume (live harness step 3c)

Parent: `6488380e`. Writer: Claude Code harness lane, 14 Oct 2026 00:31 EDT, under glitch-06's go for 3c.
Timestamp correction (glitch-06's ruling 4): the addendum committed in `ebaa34c9` to `gemini-projection-record-kinds-2026-10-14.md` is stamped 00:20 EDT; it was written at about 00:16 EDT (the clock read 00:14 shortly before and 00:17 at the commit).

## Problem

A resumed Gemini session appends to one file. What it held after turn n survives only until turn n+1 writes, and the driver's `_take_records` runs after the last turn: too late.
No collector existed, and step 1's `session_history_facts` had no retained snapshots to join.
Red evidence: `tests/test_native_snapshot.py` ran 9 tests with 2 failures and 6 errors (no `native_snapshot` module; nothing retained between turns, `[[], [], []]`; a failed retention graded).

## Source grounding

From chunk-J7SXW2FI.js (sha256 `e2aca152…f206e`), in the box lane's `gemini-storage-source.json` and `gemini-native-session-source.json`:
- `homedir()` returns `GEMINI_CLI_HOME` when it is set.
- `getGlobalGeminiDir` is `<home>/.gemini`, and `getProjectTempDir` is `join(getGlobalTempDir(), projectIdentifier)`.
- The `ChatRecordingService` constructor builds `chatsDir = join(storage.getProjectTempDir(), "chats")`.
- The file name is ``session-${ISO minute, ':'→'-'}-${sanitized id .slice(0,8)}.jsonl``, with `-<k>-` before the short id on a collision.
- On resume, `initialize(resumedSessionData)` keeps `resumedSessionData.filePath`.

Assumed, not shown in the retained source:
- `getGlobalTempDir()` is `<home>/.gemini/tmp`. `TMP_DIR_NAME = "tmp"` is retained, but the method body is not.
- `SANDBOX` is not `sandbox-exec`.
- The take's config folder on the host is the container's `GEMINI_CLI_HOME`.
These three are boundary items for the box lane to confirm.

## Change

- `native_snapshot.gemini_session_file(home, session_id)`:
  - It reads directory names only under `<home>/.gemini/tmp/*/chats`, and never reads file content or any other part of the home.
  - Every directory on the way must be a real directory, and the file must be a regular file.
  - None, two or more matches, a link, or a malformed id refuses.
- `native_snapshot.retain(take, n, source)` copies the file:
  - It opens the source without following a link, from a regular file only.
  - It writes `session/native-turn-<n>.jsonl` with `O_EXCL`, so a snapshot is never overwritten.
  - It returns `{file, sha256}`, the reference `session_history_facts` reads.
- `GeminiAdapter.native_session_path(home)` locates the file by the session id from turn 1's init. The method is appended after `_end`, so no other line moved.
- `TakeDriver`:
  - For an adapter that names a native session, it retains turn n's snapshot after the post-n sidecar snapshot and before any next resume.
  - If retention fails, nothing further is sent; cleanup, ledger and scan run, then `DriveRefused` (batch `failed`, a ruling needed, never re-run).
  - The ledger gains `native_snapshots` and `native_snapshot_refusal` only for such adapters, so Claude takes are unchanged.
  - The executed-refusal road also tries to retain its snapshot, but never raises over the refusal.
- Snapshots sit under `session/`, which is a maskable scan kind. Masking can change their bytes after the reference is taken. That is the open masking-provenance design, owned by the box witness; it is not implemented here.

## Verification (each run behind a fresh light gate)

- `tests/test_native_snapshot.py` 9/9.
- `test_executed_turn_refusal.py` 9/9.
- `test_gemini_adapter.py` 138/138; no `EQUIVALENT` key moved.
- The join test retains three real snapshots through the driver and joins them through `session_history_facts`. Rewriting snapshot 2's first interaction refuses.
- Nine in-memory mutants, candidate bytes unchanged. Eight were killed by assertion with no errors.
  - The ninth, "any session id prefix", failed 2 tests by assertion and also raised 3 errors.
  - I did not inspect the 3 errors; the 2 assertion failures are enough to call it killed.
- `copy_manifest.py --check` passes: 376 files.

## Not run, owed

- `test_box_integration.py`, `test_walk_runner.py`, `test_drive_loop.py` and the full battery are left for the merged-head athena suite.
- Codex has no collector: its rollout callback returns text, not a durable reference.
- A production native reader is still unregistered, so `session_history_facts` stays `ProvenancePending` in production.
- Independent review.
