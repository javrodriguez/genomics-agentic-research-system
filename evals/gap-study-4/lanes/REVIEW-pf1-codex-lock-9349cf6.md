VERDICT: PASS
lane-tag: instrument
purpose: round-1

# Review of lane pf1-codex-lock at 9349cf60 (base 3d278db9)

Reviewer: a fresh Opus 5.5 session, Tue 27 Oct 2026, assigned by glitch-45.
No code was changed; this file is the only write.
Experiments ran on `git archive` copies of the base and the head in the reviewer's scratch folder, and the git-dependent suite in the clone (left clean).
Every test run was preceded by `mac_slot.py light-ok --tests --work gap-study-r4`, which answered "light ok" each time (load1 2.00 to 5.72).
Interpreter `/usr/local/bin/python3.12`, `TMPDIR` set to a canonical scratch path.

No real misgraded or leaked input was found on the head, so under the review rule the loop stops here.

## Findings

1. Evidence matches the claim (verified). On athena, read-only, `/home/javier/w-QKegwCAD/walk.log` ends with w-o58 `held`: "pre-2: the config folder: .sqlite-maintenance.lock: neither placed nor on codex's allow-list". The recorded listing in that child's `repo/evals/gap-study-4/rehearsals/w-o58/postflight.json` (`recorded.listing`, 107 paths) holds the lock at the folder root. With the 70 paths under `skills/.system/` set aside, it is exactly the test's `HELD_W_O58`: 37 names, compared one by one.

2. The row is exactly as narrow as its siblings (verified). `r"\.sqlite-maintenance\.lock"`, kind `file`, read rule `None` is the same shape as the state-database row and the two existing lock rows (`tmp/arg0/codex-arg0XXXXXX/.lock`, `thread-writer-locks/(.coordination|<uuid>).lock`). `_allowed` uses `re.fullmatch` with no flags (run_take.py 2536), so it matches only the root name: no nesting, no prefix or suffix, case-sensitive. `config_folder_problems` (2541-2600) gives every admitted row the same shape checks: `other` (fifo, socket) refuses first, a directory or a link refuses because the kind is `file` ("admits only a file"), and a second hard link refuses with `nlink != 1`. The named-refusal list is checked first and has no pattern this name matches. Before turn 1, the lock refuses as "not placed". The row is codex-only; `GEMINI_ALLOWED` is unchanged (the test checks its digest). C15's witnesses `lock-name-suffix`, `-nested`, `-any-case`, `-any-lock`, `-any`, `lock-row-a-dir`, `lock-row-read` and `lock-gemini-admitted` were each RED when I ran them (finding 6).

3. Content channel: an agent can write bytes into the lock between turns, but that is no worse than what is already admitted (no finding). The row reads nothing and checks no size. An agent with write access to CODEX_HOME could therefore hide content in the lock from one turn to the next. The same holds today for the six already-admitted state databases and their `-wal`/`-shm` files, which are unread and unbounded. Those already carry far more data and are expected to change every turn. The two lock rows and the `.tmpXXXXXX` row are also unread. The lock adds no reader: the operator never reads it (C15 checks that its bytes are not in `t.box.reads()`), and postflight records only the name. So it creates no path out of the take that the databases do not already give. A link that escapes is refused by kind. Optional hardening, not required: the census already records `size`, and Codex never writes this file (finding 4). A size-0 rule, like the exact bytes the marker row checks, would close this one file cheaply. It would not change the overall channel while the databases stay unread. It is the owner's call, not this lane's.

4. The source citation is real (verified with `gh api`, read-only). Tag `rust-v0.162.1` dereferences to commit `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`. The cited lines check out:
   - `codex-rs/state/src/runtime/reclamation.rs` at that ref: line 17 has `IDLE_INTERVAL = 60 s`; lines 28-30 hold the per-home lock doc comment; lines 37-67 are the spawn loop, which sleeps first and then calls `try_ownership(sqlite.home())`; lines 115-129 are `try_ownership`, which opens `home.join(".sqlite-maintenance.lock")` with read, write, create and `truncate(false)`, then `try_lock`.
   - `state/src/runtime.rs` line 258 spawns `SqliteReclamationWorker`.
   - A code search of the repo for `sqlite-maintenance` finds only `reclamation.rs`. In that file, the handle is used only to lock, never written. That supports "never written", which I checked for this file only.

5. Red first, for w-o58's exact reason (reproduced). The base 3d278db9, archived, with the head's `tests/test_config_folder.py` dropped in: `C15MaintenanceLock C14SandboxMarker` gives 14 run, 5 failures. `PF1-LOCK.held` fails with `[".sqlite-maintenance.lock: neither placed nor on codex's allow-list"]`, the one and only problem. `PF1-LOCK.e2e` fails with "turn 2 was refused before its exec: pre-2: the config folder: .sqlite-maintenance.lock: neither placed nor on codex's allow-list", word for word w-o58's refusal. `PF1-LOCK.table` and two `PF1-LOCK.shape` subtests also fail. C14 stays green at the base, as it should.

6. Tests at the head (run):
   - `test_config_folder` (all): 40 run, 0 failures, 1 error. The error is `C7Shapes.test_shape_rules`, `OSError: [Errno 92] Illegal byte sequence` creating `bad-\xff`. The Mac's APFS refuses a name that is not UTF-8. The same error occurs at the base, and C7 is untouched by this lane, so it is not a finding. That subtest could not be exercised on this Mac; it needs athena's ext4.
   - The lane's own checks line `C15MaintenanceLock C14SandboxMarker` passes, as part of the full run.
   - `--witnesses` with the 14 listed names: "14/14 red; registry 65".
   - `check_vendor_sources.py P2 box/run_take.py check_take.py tests/test_config_folder.py checks.d/pf1-codex-lock.txt`: exit 0, no REFUSE.
   - `test_run_take` under `env -u CLAUDE_CODE_MESSAGING_TOKEN`, in the clone: "Ran 68 tests ... OK", 193 mutants red. It cannot run from an archive copy, because it calls `git show` on a past commit.
   - `test_vendor_check`, which binds the edited VENDOR_PENDING_ROWS shape: 33 tests, OK.
   - The clone's `git status` was clean after all runs.

7. Citation moves in check_take.py are right, and nothing live was missed (verified). The three moved citations name the same lines as before, two lines lower:
   - base 2413 and head 2415 are the `\.env` named-refusal row;
   - base 2381-2437 and head 2383-2439 are `GEMINI_ALLOWED (` through the close of `CONFIG_FOLDER_NAMED`;
   - base 2429-2430 and head 2431-2432 are the two Gemini memory refusals.

   I searched the head for every `run_take.py` line citation at or past 2340 outside run_take.py itself. The only live code citations are those three in check_take.py. The others are dated records under `lane-reports/` (B20-DESIGN.md, older REVIEW files, stub-take run logs) and earlier `COPIED.d` fragments. Those are historical, rightly not rewritten. No test pins a digest of the edited prose.

8. Test bookkeeping (MINOR, no class needed). C14's B20-4 base digest now drops the lock row by name, and C15 pins its own base digest (`5ecabab...`), so the two together still bind the table to base + marker + lock. A future lane will need to add its row to both filters. That is a maintenance cost, not a defect.
