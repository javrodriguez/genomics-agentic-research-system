Status: built on glitch-2f's rulings D1, D2, D3 (see the build section at the end); ready for review

RESUME HERE: review round 1, then athena

# Lane w10-walk-runner: Gap Study round 4, the CP6 walk runner (proposal)

Written Mon 12 Oct 2026, 13:05 EDT (`date`), by the lane's only writer (Claude Opus 5.5), assigned by the Lane-orchestrator under Javier's standing delegation.
Branch `gap4/w10-walk-runner`, base `f14ab57b` (wave 9, review PASS; athena running).
This commit holds this report only.
Nothing was pushed, merged or spent.
No model, network, Docker, credential, salt or holdout was used.

## What the records already fix

- The chain is named by Q-w8a-6: walk rows → `walk_driver(records="walks")` → `run.write_walk_grade` → `WalkRepo.commit_walk`.
- Q-w9-2 (ruled): the runner calls `walk_driver(records="walks")` and so gets the W1 pre-launch check (`walk_launch_problems`) for free.
- Layout A (ruling W8-layout-1): one walk is one folder, `rehearsals/<walk>/`; a retry is a new walk id; "a walk that dies is still a walk, committed with its reason" (rehearsals/README.md).
- Plan CP6 (line 877-878): every walk is graded but never counted, and "the v4 graders and the evidence readers meet real box end states before the freeze, and their outputs are read".
- Q-w7b-3: the CLI that builds `walk_driver` from the real box (DockerRuntime, login file, counters, identity and run-tree builders) needs CP2/CP6 values and is not wired.

## What a probe showed

Scratch probe (outside the repository): `/private/tmp/claude-501/-Users-javrodher-glitch/e9abd60b-365d-4ad4-ada0-6d50eeb54887/scratchpad/w10/probe_walk.py`.
It drives one walk on test_walk_wiring's fake box (the REAL Claude Code adapter and the REAL check4 on the real design, as E1 does) with `records="walks"`, then `write_walk_grade` (a stand-in grader) and `WalkRepo.commit_walk` in a scratch repository.
Each run was behind `mac_slot.py light-ok` and `timeout -s INT 120`, with python3.13, and exited 0.

1. `faked` (E1's world, where `takes.load_rows()` answers a registered row): the walk launches into `rehearsals/w-probe-1/`, 3 turns, `checker_reasons: []`, and is committed as "Commit one walk; never counted" with 25 files.
   The mechanical chain works.
2. `prefreeze` (`takes.load_rows()` and `row_commits()` answer nothing, which is how a real study stands before the freeze): the same walk gives `checker_reasons: ['session-binding']`, and it is still committed.
   That reading is computed, then dropped: it is in the dict `drive()` returns and in no file of the walk folder.
3. `preflightfail` (preflight fails): the folder holds launch, preflight, postflight, teardown, proxy.log and evidence/, and no `driver-ledger.json`.
   `write_walk_grade` raises `FileNotFoundError ... driver-ledger.json`, so the walk cannot be committed.
   Its folder stays unregistered under `rehearsals/`, which makes `walk_register --check` fail.
4. In every variant the per-take config folder is left behind (`cfg-...`), because nothing calls `driver.published`.

Code reads behind 2 and 3:
- `drive.take_checker` always calls `check4(..., take.identity["row"], False, ...)`, so a walk is checked as a take against takes.json.
  check4's `is_walk=True` is round 3's meaning: no ledger row, AND the script truncated before the probe (check_take.py:1610).
  A round-4 walk sends the whole script, probe included, because it must be graded.
- `driver-ledger.json` is written only in `_take_records`, reached only `if ok and turns` (drive.py `TakeDriver.drive`).
  `WALK_REQUIRED` and `walk_register`'s content rule both require it.
- The readers count a walk by its `transcript.jsonl` (`mode_binding.record_transcripts`), so a walk that dies without one is in the register and invisible to mode_binding, fixture_walk, build_cases and leak_grep (L9's "readers agree").

## Open design choices (options, recommendation)

D1. How a walk is checked, and where the reading lives.
- (a) check4 gains a round-4 walk road: no takes.json row, the FULL wording script, the session id bound to the walk's identity (D2), and the ledger, model, environment and tree checks as for a take.
  `take_checker` uses it when the driver's `records` is "walks".
  The reading (reasons, events, and the route `routing.route` gives the records) is written into a new walk record, `check.json`, in the closed map (kind ledger) and required.
- (b) The take road stays, and the reading is persisted as it is; every walk then carries `session-binding`, which drowns the reasons that matter.
- (c) Walks are not checked; only graded.
  This contradicts plan line 878.
- Recommendation: (a).
  `check.json` stays apart from `grade.json` because `run.py --walks --check` regrades `grade.json` byte for byte, and the checker's reading needs the design view and pin, which the regrade does not have.

D2. A walk's identity (the caller's `identity_for`; no production builder exists yet, Q-w7b-3).
- (a) `session_id = uuid5(takes.namespace(), "walk/" + <walk id>)`, `row` None, `row_commit` None (check_take already models `row_commit` None for a walk); the project name follows from the session id as for a take.
- (b) The session id from the commit that adds the walk's register entry.
  That commit is made after the walk runs, so it cannot be known at launch.
- Recommendation: (a). The binding is deterministic and checkable from the walk id alone, and D1's walk road checks it.

D3. A walk that dies before its driver ledger exists.
- (a) The driver writes `driver-ledger.json` on every road where the record folder exists (pre-turn refusals included).
  This touches TakeDriver for takes too, and the ledger readers would meet a ledger without turns.
- (b) Walks only: the required set becomes `grade.json` plus either `driver-ledger.json` or `preflight.json`/`refusal.json`.
  `grade_walk` writes `{"graded": false, "why": ...}` from refusal.json or preflight.json.
  The readers count walks from the register, so a transcript-less walk is counted the same way everywhere (L9).
- (c) Such a walk is never committed: the runner reports it and leaves the folder for a human.
  This contradicts "a walk that dies is still a walk, committed with its reason".
- Recommendation: (b), for pre-turn refusals only.
  A `DriveRefused` from the drive scan or postflight is different: it may mean an unmasked secret or a credential left behind.
  It is never committed, the folder is kept for a human, and `walk_register --check` going red is the correct signal.
  A `LaunchRefused` (W1) makes no folder, so there is nothing to commit; the runner reports it and moves on.

## Settled in-plan (no ruling needed; how I would build it)

- A new module `walk_runner.py` with a library function that runs walks serially, one at a time.
  For each walk it does: W1 launch (through `walk_driver(records="walks")`), drive, remove, `write_walk_grade`, `WalkRepo.commit_walk`, then `driver.published` (finding 4).
  It does not use `batch.Batch`, whose slot, registration and window machinery is take-only (WalkRepo refuses `register`).
- A walk spec is the register entry's fields plus the cell (pressure or repeat) and the agent.
  The row is built from it, with `slot` equal to the walk id, because the driver keys its takes by slot.
- Claude walks only.
  `walk_driver` admits only the production ClaudeCodeAdapter, so arm O and G walks need their adapters and w7c's spend gate first.
- The CLI refuses, naming Q-w7b-3, until the production builders exist.
- Tests on the fake box, red first, each with a witness: the chain end to end; W1 reached through the runner; a pre-turn death committed with its reason (D3); a scan refusal never committed; no file under `takes/`; the config folder deleted; `walk_register --check` "ok: 1 registered walk(s)".

## Not covered

- Coverage (README Q3) and publication (Q6) stay open.
- Q-w8a-5 still applies: `mode_binding --walks --check` fails on any real walk until the pins are filled.

## Modules athena must run

- None for this commit, which is a report only.

## Rulings (glitch-2f, the Lane-orchestrator under Javier's delegation, Mon 12 Oct 2026)

- D1 accepted: a round-4 walk mode in check4, `take_checker` uses it for walks, and the result goes in a required `check.json`; round 3's `is_walk` is untouched, with a test showing it is byte-identical.
- D2 accepted: `session_id = uuid5(takes.namespace(), "walk/" + id)`, with row and row_commit None.
- D3 accepted as written.
- The in-plan choices stand: `walk_runner.py` runs one walk at a time, slot equals the walk id, Claude only, the CLI refuses naming Q-w7b-3, and `driver.published` is called on every road.

## Build, Mon 12 Oct 2026 13:35 EDT (`date`)

Commits `cb53102e` (code and tests) and `17e7e129` (ownership records, checks.d, register and README text).

What was built:
- `walk_runner.py` (new): `run_walks(driver, repo, walks)`.
  For each walk it launches through the walk arm, drives, removes the containers, writes `check.json`, writes `grade.json`, commits through `WalkRepo.commit_walk`, then calls `driver.published`.
  A walk refused before launch is reported, and the runner moves on.
  A walk whose launch failed after making things, whose drive raised, whose containers could not all be removed, or whose grade or commit was refused is never committed; its folder is left for a human, and the runner stops.
  The CLI refuses (exit 2), naming Q-w7b-3.
- `check_take.py` (D1, D2), appended above `if __name__` only:
  - `walk_session_id`;
  - `check_walk`, which runs `check()` as a take with no row, asserts it ends at exactly one row-needed line, replaces that line with the walk's binding, and keeps the take's tail;
  - `check4_walk`.
  The round-3 byte binding (checks.d/w6j-claude-adapter.txt) still holds.
- `drive.py`:
  - `take_checker(records=...)` reads a walk by `check4_walk`;
  - the walk folder's closed map gains `check.json` (required);
  - D3: a walk folder with no driver ledger must hold `preflight.json` or `refusal.json`;
  - `walk_identity_problems` (D2) runs at the end of `walk_launch_problems`.
  The round-3 byte binding (checks.d/w6e-drive-commit.txt) still holds.
- `run.py` (D3): `grade_walk` gives a walk with no driver ledger "not graded, because ..." from its refusal.json or preflight.json.

Departure from the ruling's wording, named here: `driver.published` is called on every road except one.
When the drive ran (teardown.json written) and its postflight did not pass, the config folder is kept for a human.
That is the driver's own postflight stop (S6b (e): "the config folder is kept for a human"); deleting it would destroy the credential-like file the stop is about.
R4 binds both sides: after a postflight refusal the config folder is kept, and after a drive-scan refusal it is deleted.

Evidence (Mac, each run behind `mac_slot.py light-ok` and `timeout -s INT 115/120`, python3.13):
- Red first, against a detached worktree of f14ab57b holding only the new test file: `test_walk_runner: 9 run, 9 failures, 0 errors`, every failure by assertion with its clause.
  With `walk_runner.py` also copied in, so that only the base's drive, check_take and run were missing the change: `9 run, 5 failures, 0 errors`, each failure `KeyError: 'WALK_CHECK'` by assertion (R1, R2 x2, R3, R5).
- Green: `test_walk_runner: 10 run, 0 failures, 0 errors, 0 skipped` (9 plus TestSysPath W6M1).
- Witnesses: 16/16 RED in two batches of 8, exit 0 each.
  Two first survived and were fixed in the test, not the code:
  - walk-session-unbound: the ledger's session check covered it. R2 now shows each binding alone, on a copy whose ledger names another walk's session, and a witness walk-ledger-session-unbound was added.
  - check-file-optional: walk_register imports the real drive module, not the witness. R3 now asserts the driver module's own `walk_files`.
- The probe's four variants are now tests: faked and the chain → R1; prefreeze → R2; preflightfail → R3; the leftover config folder → R1, R3 and R4.
- Neighbours:
  - test_walk_layout: 14 run, 0 failures; its witnesses 21/21 red.
  - test_cp8_prep: 4 run, 0 failures; its witnesses 15/15 red.
  - test_cp6_wiring: 5 run, 0 failures; its witnesses 20/20 red.
  - test_rehearsals: 9 run, 0 failures; its witnesses 20/20 red.
  - test_walk_wiring: Ran 20, OK. test_check_take: Ran 15, OK. test_checker_body: Ran 29, OK.
  - test_drive_commit: Ran 31, OK. test_drive_loop: Ran 27, OK. test_mode_binding: Ran 8, OK. test_ci_job: Ran 23, OK.
  - test_scaffold: TheManifest.test_check_passes_on_the_folder and TheImports, Ran 4, OK; TheBinding, Ran 2, OK. Whole TheManifest hit rc 124 (owed to athena).
  - test_pipeline: PipelineOwnership and PublishedArtifacts only, Ran 6, OK.
- Before the fixture edits, test_walk_layout went red on L3, L4 and L10 and test_cp8_prep on H1, because check.json is now required. That is the expected red; the fix adds one fixture line each, and no assertion or witness changed.
- Anchor sweep: every test string that occurred once in the base's check_take, drive, run, walk_register or mode_binding still occurs once, apart from the file name 'driver-ledger.json' in run.py, which no mutant anchors on.
  Two test_check_take witnesses (ledger-arm-unbound, nothing-lifted) and four test_checker_body anchors first doubled because of check4_walk's copied lines; those lines were reworded.
- Gates: copy_manifest --check exit 0 (299 files, 48 fragments); build_draft --check exit 0 (no input moved, so prereg-draft.json is untouched); freeze.py --check exit 0 (299 owned paths); walk_register --check exit 0 (0-walk line).
  Also exit 0: run.py --walks --check, mode_binding.py --walks --check and fixture_walk.py --check (0-walk lines).
- lint_language: clean, 92 inputs, 23 excused. lint_pooling: clean, 92 files.
- One real-grader run (scratch, not a test): the fake box's walk reached the REAL v4 grader, which raised `EvidenceError: ... is not a watched path (watched.json)`.
  The fake sidecar's watched set does not cover the grader's path.
  The runner held the walk, uncommitted, as designed.
  So the real grade road is wired but not yet shown green on the fake box; the tests use a labelled stand-in grade.

## Ownership

- Transfers, under rulings D1-D3: drive.py from w9-cp6, and check_take.py from w7b-walk-wiring.
- New: walk_runner.py, tests/test_walk_runner.py, checks.d/w10-walk-runner.txt, COPIED.d/w10-walk-runner.json.
- Departures (edited without transfer, each recorded in its owner's entry):
  - w10-1 run.py (w8a; PipelineOwnership binds it there);
  - w10-2 tests/test_walk_layout.py (w8a);
  - w10-3 tests/test_cp8_prep.py (w8d);
  - w10-4 tests/test_cp6_wiring.py (w9; W1's admitted walk gets its own identity);
  - w10-5 walk_register.py (w8d; docstring only);
  - w10-6 rehearsals/README.md (w8a).

## Open questions (proposed answers)

- Q-w10-1: the real v4 grader refuses the fake box's evidence (path not watched).
  Proposed: before the first real walk, one fake-box test grades a walk through the real grader with a watched set covering the half's paths. Alternatively, accept that the first real Haiku walk is the proof (plan line 1040: "one real walk per model in the box, read end to end").
- Q-w10-2: the checker's constants are still PENDING, so on real walks check4_walk raises CheckRefused, the drive raises, and the walk is held (Q-w8a-5's twin).
  Proposed: as for takes, the first walks are run with the constants measured, or the checker step is ruled for the very first walk; this is not changed here.
- Q-w10-3: `check.json` cannot be regraded (it needs the design view and pin), unlike `grade.json`.
  Proposed: accept, as with driver-ledger.json; CP8's walk_register step in CI binds its bytes to the walk commit.

## Modules athena must run

- tests/test_walk_runner.py and `--witnesses` (16)
- tests/test_box_integration.py (whole; it exceeds 120 s on the Mac)
- tests/test_pipeline.py (whole; PipelineOwnership with run.py's departure)
- tests/test_scaffold.py (whole) and test_round4.py (the battery)
- tests/test_walk_layout.py, test_cp8_prep.py, test_cp6_wiring.py and test_rehearsals.py, each with `--witnesses`
- tests/test_walk_wiring.py, test_check_take.py, test_checker_body.py, test_drive_commit.py, test_drive_loop.py, test_mode_binding.py and test_wave6_bindings.py
- The gates: copy_manifest --check, build_draft --check, freeze.py --check, walk_register --check, run.py --walks --check, mode_binding.py --walks --check, fixture_walk.py --check, the checks.d byte bindings (w6j check_take, w6e drive), and lint_language and lint_pooling over the folder
