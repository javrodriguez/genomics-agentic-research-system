VERDICT: PASS
lane-tag: instrument
purpose: round-1 (re-run; the earlier file is discarded under the language protocol)

Reviewer: a fresh Opus 5.5 context, assigned by glitch-45.
Candidate: 3d278db97c57060f9d1914969c2dd357db3f19eb..9349cf60ef2be5c8756d0f81fd16e64379382711 on merge/pf1-l6e, one commit (9349cf60), 5 files.
The earlier review of this head was not read.

## The defect, read on athena (read only)

- `tail -c 4000 /home/javier/w-QKegwCAD/walk.log` ends with walk w-o58 held: "drive raised DriveRefused: pre-2: the config folder: .sqlite-maintenance.lock: neither placed nor on codex's allow-list".
- `rehearsals/w-o58/postflight.json`, `recorded.listing`, holds 107 paths, 70 of them under `skills/.system/`; `.sqlite-maintenance.lock` sits at the folder root beside the state databases.
- C15's `HELD_W_O58` holds the 37 paths outside `skills/.system/`, the same names as the recorded listing.

## The source citation (gh api, read only)

- Tag `rust-v0.162.1` resolves to commit 092d3acd6bec3e3a14bdc7e7a2810ab628ab759d.
- `codex-rs/state/src/runtime/reclamation.rs` at that commit: line 17 `IDLE_INTERVAL = 60 s`; lines 28-30 name "a per-home file lock elects one active worker"; lines 37-67 are `spawn`, which sleeps first and then calls `try_ownership(sqlite.home())`; lines 115-129 are `try_ownership`, which opens `home.join(".sqlite-maintenance.lock")` with read, write, create and truncate false, then `try_lock()`.
- Nothing in that file writes to or reads from the lock's bytes; the handle is kept only to hold the lock.
- `codex-rs/state/src/runtime.rs` line 258 is `reclamation: reclamation::SqliteReclamationWorker::spawn(sqlite.clone())`.
- Every cited line range matches the pinned source.
- The w-o58 listing confirms the sqlite home is CODEX_HOME in the walks (the lock lies at the root, next to `state_5.sqlite`).

## Findings

1. PASS: the row is narrow.
   - Name: `r"\.sqlite-maintenance\.lock"` under `re.fullmatch` against the path relative to the folder, so it admits exactly one root-level name; both dots are escaped; there is no `(?i)` flag, so case is exact.
   - Nesting: a full match with no `/` in the pattern admits no nested copy (`tmp/`, `sessions/`, `cache/` copies refuse; C15 checks each).
   - Kind: `"file"`; a folder or a link at that name gets "a dir/link where the allow-list admits only a file" (run_take.py 2586-2588 at H).
   - Fifos, sockets and devices: the census lists them as kind `other` (ownership.py 448), refused before the allow-list is read (run_take.py 2573-2576).
   - Hard links: a file with `nlink != 1` refuses (run_take.py 2593-2595), so the lock cannot alias another admitted file.
   - Read rule `None`: the lock's bytes are never read by the checker, like the six admitted state databases and the arg0 `.lock` row.
   - Codex only: the row sits in `CODEX_ALLOWED`; Gemini's table is unchanged and a lock in a Gemini folder refuses.
   - Before turn 1 the lock refuses, since the folder must hold the placed set only.
   - The named-refusal list (`CONFIG_FOLDER_NAMED`) is read before the allow-list, and no named pattern matches this name, so no refusal is shadowed.

2. MINOR (no class needed): the lock's content is never read and its size is not bounded, like the other unread rows (`tmp/arg0/.../.lock`, `.tmpXXXXXX`, the state databases).
   - Why this is no content channel under the threat model: Codex opens the file only to `flock` it and never reads its bytes, so nothing the agent writes there reaches the model through Codex; the config folder is deleted by `remove_config_dir` once the take's records publish (run_take.py 1695-1707), so nothing leaves the take through it; and the agent, running in bypass mode, already keeps its own work tree between turns, so a write into this file gives it nothing it lacks.
   - Optional hardening for a later lane, not a blocker: since the pinned Codex never writes the file, a read rule that checks `size == 0` from the census facts (no byte read) would close even the agent-to-agent path through it.

3. PASS: red first, reproduced on a git-archive copy.
   - Copy A: `git archive 9349cf60 evals/gap-study-4` with `box/run_take.py` taken from 3d278db9 (the head's test, the base's table); the only difference between the two run_take.py files is the two added lines.
   - Result on copy A, `test_config_folder.py C15MaintenanceLock`: 6 tests ran, FAILED (failures=5).
   - The held-folder test fails with `[".sqlite-maintenance.lock: neither placed nor on codex's allow-list"] != []`, the exact text of w-o58's hold.
   - The end-to-end test fails with "PF1-LOCK.e2e: turn 2 was refused before its exec: pre-2: the config folder: .sqlite-maintenance.lock: neither placed nor on codex's allow-list", the same stage and words as w-o58's walk.log line.
   - The table test and the two shape subtests (a folder, a link) fail because the row is absent; the deny and Gemini tests pass, as they should at the base.
   - Copy B, `git archive 9349cf60 evals/gap-study-4` unchanged: 6 tests ran, OK.

4. PASS: the check_take.py citation moves.
   - The row adds two lines at run_take.py 2347-2348, so every cited line after 2346 moves by two.
   - At H: 2415 is the `\.env` refusal (2413 at the base); 2383-2439 run from `GEMINI_ALLOWED = (` to the closing `),` of `CONFIG_FOLDER_NAMED` (2381-2437 at the base); 2431-2432 are the two Gemini memory refusals (2429-2430 at the base).
   - A `git grep` of `run_take.py[: ]` followed by a line number at or past 2350, across `evals/gap-study-4` (lanes and COPIED.d left out), finds only these three citations; the other run_take.py citations (85-86, 172-174, 508, 511, 963-973, 2267) sit before the insertion and stay right.

5. PASS: the tests, run in the clone.
   - `mac_slot.py light-ok --tests --work gap-study-r4` first refused (CPU speed limit 75 below 80); polled until it read "light ok" at 04:44 EDT, then ran.
   - All runs with /usr/local/bin/python3.12 and TMPDIR set to a scratch path.
   - `test_config_folder.py` (all cases): 40 tests ran, FAILED (errors=1); the one error is C7 `test_shape_rules` creating `bad-\xff` (OSError 92, Illegal byte sequence), the known Mac disk limit, outside this lane.
   - `test_config_folder.py --witnesses` with the 14 names in `checks.d/pf1-codex-lock.txt`: baseline green, then 14 of 14 witnesses red (registry 65), each naming its own method and clause.
   - `env -u CLAUDE_CODE_MESSAGING_TOKEN ... tests/test_run_take.py`: 68 tests ran, OK.
   - `tests/check_vendor_sources.py P2 box/run_take.py check_take.py tests/test_config_folder.py checks.d/pf1-codex-lock.txt`: exit 0, no output.

6. PASS: test design.
   - C15 rebuilds w-o58's listing and asserts the rebuilt folder holds exactly those names before checking it, so the test is bound to the recorded folder and not to a hand-picked one.
   - The deny case covers a suffix, a case variant, a misspelling, a missing leading dot, a prefix, three nested copies, another lock name and an unrelated name; each refuses with "neither placed nor on codex's allow-list".
   - The twelve registered witnesses each weaken one clause (row absent, row read, suffix, nesting, any case, any lock, any name, a dir kind, Gemini admission, two sibling-table moves) and each names the method that must go red.
   - C14's base digest now drops the lock row by its exact pattern, and C15 pins the table as the 3d278db9 base plus that one row, so a second added row still turns one of the two red.

## Review rule

This round shows no misgraded or leaked input on the head, so under the instrument rule the loop stops here.
