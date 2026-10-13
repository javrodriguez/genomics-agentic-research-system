Status: review round 3 CHANGES folded (ruling w10-R3-fold, 61cce6ec); generated mutation built, the full sweep is athena's

RESUME HERE: review round 4 + athena generated run

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

## Fold w10-R1-fold, Mon 12 Oct 2026 14:07 EDT (`date`)

Review round 1 (866586d4, lane-reports/w10-walk-runner-review-r1.md) found CHANGES: W10-R1-1 (MAJOR) and W10-R1-2 (MINOR).
Ruling w10-R1-fold (glitch-2f) asked for both folds, check.json's "checked", and Q-w10-1's real-grader test.
Code commit `f0af28ee`; this report is in its own commit.

What changed:
- W10-R1-1, root cause 2: new class R8WalkRoad.
  It runs one clean walk, then for each guard copies the folder and changes ONE fact.
  Where another record cross-binds that fact, the other record is forged to agree: the environment record for the ledger's half and model, and the instruction paths for the working directory.
  `check4_walk` reads the copy, and the lines it adds over the clean copy must all be the bound guard's.
  A baseline test proves the clean copy reads clean.
  check_walk's tail now reads through `walk_pre` with a `D1` comment per line, so every guard has a unique anchor; behaviour is unchanged.
  R2 gains the walk's own session id with row 0 alone, and with a row commit alone, each refused at launch.
- W10-R1-1, root cause 1: I could not reproduce it.
  A scratch probe (`.../scratchpad/w10/probe_machinery.py`) compiled a check_take mutant that raises at the top of `check4_walk` through the test module's own machinery and ran R1.
  The walk was held: "drive raised RuntimeError: PROBE: the mutant reached".
  So the drive's call-time `import check_take` already resolves to the compiled witness (compile_module puts it in sys.modules).
  The reviewer's nine mutants survived because no test fed a bad walk (root cause 2), not because the machinery missed the drive.
  It is now bound anyway: `test_the_design_tree_through_the_drive` asserts that `sys.modules["check_take"]` is the module under test, then drives a walk in another tree.
  Witness `walk-tree-unchecked-through-drive` goes red through the drive path.
- W10-R1-2: `_publish` runs only once `driver.launch` was reached for this row (a `reached` marker set just before the call).
  The config folder is kept whenever `postflight.json` exists and is not ok, or when the drive ran (teardown.json written) and no postflight record exists.
  New tests: the reviewer's slot probe (a refused w-0002 with slot w-0001 leaves w-0001's kept folder alone), and a failed `teardown.json` write under a failing postflight still keeps the folder.
- Note → done: check.json carries `"checked"`, true exactly when the driver wrote its ledger (that is, when the checker ran). R1 asserts true and R3 asserts false.
- Q-w10-1: new class R9RealGrade.
  The fake sidecar's `watched.json` lists the half's planted paths (`variants.grader_spec(...)["planted"]`).
  The REAL v4 grader (graders/scope_read.py) grades the fake walk, the walk is committed, and `run.walk_problems` (the real grader again) gives `([], 1)`.
  Without the watched paths the same walk was held on `EvidenceError ... not a watched path` (the earlier scratch run).

The reviewer's nine guards, each removed (the 2278-2280 group is three guards):

| Reviewer line | Guard | Witness | Bound test | Result |
|---|---|---|---|---|
| check_take 2241 | row-needed assertion | walk-row-needed-unasserted | R8 test_the_row_needed_line_is_asserted | RED |
| check_take 2257 | ledger task/half | walk-ledger-cell-unbound | R8 test_the_ledger_cell | RED |
| check_take 2263 | ledger row | walk-ledger-row-unbound | R8 test_the_ledger_row | RED |
| check_take 2263 | ledger row_commit | walk-ledger-row-commit-unbound | R8 test_the_ledger_row_commit | RED |
| check_take 2265 | environment_problems | walk-environment-unread | R8 test_the_environment_record | RED |
| check_take 2271 | environment row | walk-environment-row-unbound | R8 test_the_environment_row | RED |
| check_take 2271 | environment row_commit | walk-environment-row-commit-unbound | R8 test_the_environment_row_commit | RED |
| check_take 2275 | model_problems | walk-model-unbound | R8 test_the_model | RED |
| (beside 2275) | no model in the ledger | walk-model-missing-admitted | R8 test_no_model | RED |
| check_take 2278 | constant_problems | walk-constants-unread | R8 test_the_constants | RED |
| check_take 2279 | checkout_problems | walk-checkout-unread | R8 test_the_checkout | RED |
| check_take 2280 | pinned_instruction_problems | walk-instructions-unread | R8 test_the_instructions | RED |
| check_take 2321 | recorded_mode_problems | walk-mode-unread | R8 test_the_permission_mode | RED |
| check_take 2322 | design_tree_problems | walk-tree-unchecked | R8 test_the_design_tree | RED |
| check_take 2322 | the same, through the drive | walk-tree-unchecked-through-drive | R8 test_the_design_tree_through_the_drive | RED |
| check4_walk | ledger arm | walk-arm-unbound | R8 test_the_arm | RED |
| drive 3295 | identity row | walk-identity-row-admitted | R2 test_a_walk_identity_with_a_row_is_refused | RED |
| drive 3296 | identity row_commit | walk-identity-row-commit-admitted | R2 test_a_walk_identity_with_a_row_is_refused | RED |

Every witness above is red by AssertionError carrying its clause, only its bound method run.

Evidence (Mac, each run behind `mac_slot.py light-ok` and `timeout -s INT 100/115`, python3.13):
- Red first: the new test file against 866586d4's code (a detached scratch worktree, test file only) gave `test_walk_runner: 31 run, 4 failures, 0 errors`, each by assertion:
  - R1 and R3: `"checked"` absent;
  - R4 slot probe: "0 != 1 ... deleted another walk's kept config folder";
  - R4 teardown: "0 != 1 ... the config folder was not kept".
  The R8 and R9 tests pass on the old code by design: the guards existed but were unbound. Their red is their witnesses (the table above). R9's red is the unwatched run.
- Green: `test_walk_runner: 31 run, 0 failures, 0 errors, 0 skipped`.
- Witnesses: 38/38 RED in five batches (8, 8, 8, 7, 7), exit 0 each; the registry is 38.
- Neighbours:
  - test_check_take: Ran 15, OK. test_checker_body: Ran 29, OK. test_walk_wiring: Ran 20, OK.
  - test_cp6_wiring, test_cp8_prep, test_walk_layout and test_rehearsals: each 0 failures.
  - Anchor sweep: no test anchor that occurred once at the base now occurs twice (the known exceptions are the file name 'driver-ledger.json' and test_endstate's assertRaisesRegex text).
  - check_take's round-3 byte binding (w6j) still holds.
- Gates: copy_manifest --check exit 0 (299 files, 48 fragments); build_draft --check exit 0 (no input moved); freeze.py --check exit 0; walk_register --check exit 0; run.py --walks --check exit 0.
- Lints: lint_language clean (92 inputs); lint_pooling clean (92 files).

Athena's module list is unchanged; test_walk_runner now runs 31 tests with 38 witnesses.

## Fold w10-R2-fold, Mon 12 Oct 2026 14:41 EDT (`date`)

Review round 2 (f76d5c65, lane-reports/w10-walk-runner-review-r2.md) found CHANGES: W10-R2-1 (MAJOR), W10-R2-2 and W10-R2-3 (MINOR).
Ruling w10-R2-fold asked for class-level fixes.
Code commit `4858c41e`; this report is in its own commit.

What changed:
- W10-R2-1, the class fix: C1Coverage.
  It parses, by AST, every statement in `check_walk`, `check4_walk` and `walk_identity_problems` that adds a problem or refuses: `problems.append`, `problems +=`, `raise`, and a call to `harness_guard`.
  It requires those statements and the DELETIONS registry to match one to one, each entry a witness that replaces exactly that statement with `pass` inside its own function.
  So a new guard without a witness, or a witness whose statement changed or went, is red.
  Witnesses `coverage-guard-added` and `coverage-statement-changed` prove both directions.
  The registry holds 31 statements: 15 in check_walk, 14 in check4_walk and 2 in walk_identity_problems.
  The mutant machinery now applies a replacement inside a named function (`apply_mutant`), because some statements are textually the same in the base `check()` and `check4()`.
- New single-change tests, so that every deletion goes red by assertion through the real suite:
  - no driver ledger;
  - no prompt snapshot;
  - the memory section offered;
  - the row-needed line first with a real problem after it, and the row-needed line twice (the reviewer's two clause survivors);
  - check4_walk's nine design refusals, each on one bad input (script list, design type, half/script, harness, pending, cell, script, run tree, event ids), checked by their own words;
  - the reason-id refusal and the event-disagreement refusal;
  - an identity builder that raises, refused at launch.
- The round-2 reviewer's fifteen mutants (`scratchpad/w10r2/mut.py`) are registry witnesses under their own names, with their anchors verbatim (REVIEWER, REVIEWER_BOUND).
- W10-R2-2: the keep guard is inverted to fail closed.
  `clean_drive` is true only when `postflight.json` is present, readable and ok, and `teardown.json` is present, readable, records a teardown and has no problem.
  The config folder is deleted only then; every other state keeps it.
  A row whose launch made no walk folder touches nothing.
  Tests:
  - the reviewer's probe: both records' writes refused under a failing postflight, so the folder is kept (witness keep-by-default-dropped);
  - a clean postflight whose teardown write is refused: the walk is committed and its folder kept (witness teardown-unread);
  - the existing postflight test (witness postflight-config-deleted, re-anchored).
  The `keep-keyed-on-teardown` witness is replaced by `teardown-unread`.
- The `reached` guard: under fail-closed, the old slot probe no longer isolated it (witness published-before-launch first survived, because the new folder check also stops it).
  The test now commits w-0002 clean first, holds w-0001, then refuses a row with walk w-0002 and slot w-0001.
  Only `reached` stands between that row and w-0001's kept folder, and the witness is red.
- W10-R2-3: `drive.walk_files` (the register's content rule too) refuses a folder that holds `transcript.jsonl` or a `turn-N.jsonl` but no driver ledger.
  `run.died_before_turn_one` raises for such a folder.
  The pre-turn alternative now applies only to a walk with neither.
  Test: the reviewer's ledgerless probe (a committed walk copied, its ledger removed). Witnesses: ledgerless-turns-admitted and ledgerless-graded.

Evidence (Mac, each run behind `mac_slot.py light-ok` and `timeout -s INT 100/115`, python3.13):
- Red first: the new test file against f76d5c65's code (scratch worktree, test file only) gave `43 run, 3 failures, 0 errors`, each by assertion:
  - R3 "a ledgerless walk whose turns ran passes the closed map";
  - R4 teardown and R4 both-refused, each "0 != 1 ... the config folder was not kept".
  The rest of the new tests bind guards that already existed, so their red is their witnesses: the reviewer's 5 survivors (x-snapshot-gone, x-memory-offered-gone, x-row-needed-last-clause, x-row-needed-count-clause, x-no-ledger-silent) are all red now.
- Green: `test_walk_runner: 43 run, 0 failures, 0 errors, 0 skipped`.
- Witnesses: 89/89 RED, in ten batches of up to 9, exit 0 each; the registry is 89.
  One batch first had published-before-launch survive; it was fixed as above and its batch re-run 9/9.
- Neighbours:
  - test_walk_layout: 14 run, 0 failures. test_cp8_prep: 4 run, 0 failures. test_rehearsals: 9 run, 0 failures. test_cp6_wiring: 5 run, 0 failures.
  - test_check_take: Ran 15, OK.
  - Anchor sweep against adea27d3: no other test's mutant anchor doubled.
- Gates: copy_manifest --check exit 0 (299 files, 48 fragments); build_draft --check exit 0 (no input moved); freeze.py --check exit 0; walk_register --check exit 0; run.py --walks --check exit 0.
- Lints: lint_language clean (92 inputs); lint_pooling clean (92 files).
- Ownership: the fold is recorded in COPIED.d/w10-walk-runner.json.
  run.py, walk_register.py and rehearsals/README.md were edited again under departures w10-1, w10-5 and w10-6, each noted in its owner's entry.

Athena's module list is unchanged; test_walk_runner now runs 43 tests with 89 witnesses.

## Fold w10-R3-fold, Mon 12 Oct 2026 19:36 EDT (`date`)

Review round 3 (250401c8) found CHANGES: W10-R3-1 (MAJOR, `problems = problems[:-1]` → `[]` green) and W10-R3-2..5 (MINOR).
Ruling w10-R3-fold replaced shape lists with generated, exhaustive mutation.
Code commit `61cce6ec`; this report is in its own commit.

What changed:
- `tests/walk_mutation.py` (new, stdlib only) generates the walk road's mutants:
  - every statement deleted (replaced by `pass`);
  - every if/while condition set to True and to False;
  - every and/or operand dropped;
  - every comparison negated;
  - every assignment's right-hand side replaced by an empty value of its kind.
  Each mutant is spliced into the module's own bytes at the node's position, so the rest of the file is unchanged, and each has a stable id (module, function, kind, relative line, column, hash).
  The road covered:
  - check_take: walk_session_id, check_walk, check4_walk;
  - drive: walk_identity_problems, walk_files;
  - run: died_before_turn_one, grade_walk, walk_row;
  - walk_runner: every function.
  Not mutated, because other lanes' suites bind them: shared take-and-walk code (record_kind, take_checker, TakeDriver, WalkRepo's commit step) and lane w9's walk_launch_problems.
  Count: **533 generated**, 0 dropped for not compiling.
- `test_walk_runner.py --generated-mutants [--shard i/n] [--sample k] [--only id,id] [--ids file] [--timeout s]` runs each mutant in its own process over the whole module, with failfast and the cheapest classes first (GENERATED_ORDER).
  A mutant is killed when any test fails by assertion; a failfast stop on an error alone is re-run without failfast.
  The run fails on a survivor not in EQUIVALENT, on a listed one that is killed, and on an inconclusive (timed-out) one.
  G1Generated (always in the suite) fails on an EQUIVALENT entry that names no generated mutant, or one without a reason.
- C1Coverage and its DELETIONS registry are removed.
  They are superseded, and they masked behaviour: C1 alone killed every deletion in its three functions.
- New tests:
  - W10-R3-1: an operator line never sent; an improvised operator line; a fixture fault (each through check4_walk); a fixture fault through the drive into check.json.
  - W10-R3-2: another walk's session id alone, refused at launch.
  - W10-R3-3: a design view of another task with the right half; also a None script.
  - W10-R3-4: a teardown problem through the drive (config folder kept); clean_drive record by record (both records ok; postflight not ok, missing or unreadable; teardown missing, null or with a problem).
  - W10-R3-5: a recordless folder refused by walk_files; R3 asserts "preflight failed" in the dead walk's grade.
  - From the reviewer's unverified item: a walk with no reason (empty, or only invisible characters) refused.
  - From the Mac sample: R10Guards (run_walks' driver and repo guards, walk_session_id's guard, _remove), and R1 asserts check.json's route "graded".
- The round-3 reviewer's eleven mutants are registry witnesses (REVIEWER3); there are 67 hand witnesses.
- walk_runner.run_walks lost a dead line, `table = routing.load_table() if table is None else table`. A generated mutant showed it equivalent: routing.route reads routing.json itself when handed None.
  No behaviour changed.

EQUIVALENT (1 entry): `drive.walk_files:delete:L8:C8:a9b7cb72` (`dirs.sort()`).
Its reason: the list is read as a mapping by path (TakeRepo._take_files, then sorted) and by content_problems for its refusal alone, so order does not matter.

Generated sweep on the Mac (samples and targeted runs only, light-ok before each; stopped at your 18:5x word after the then-current part finished):
- First sample: 90 mutants (shards 1, 7, ..., 55 of 60) at 115 s each.
  49 killed, 1 survived (the dirs.sort() above, now listed), and 40 inconclusive (timed out).
  At load 13-19 the whole module takes about 2-3 min, so a survivor or a late kill cannot finish inside the cap.
- Re-run of the inconclusive ones with the cheapest-first order: 20 more before the stop. 1 killed (`clean_drive:drop-0`), the rest still timed out.
- Targeted runs after R10Guards: 31 mutants.
  25 killed: all 7 of walk_session_id, all 13 of _remove and run_walks' guards.
  6 timed out: run_walks' table and route_fn defaults; the table line has since been removed as equivalent.
- So the Mac shows no survivor beyond the listed one, but about 60 sampled mutants are inconclusive at this load.
  The full 533 need athena: `python3 -B -W ignore evals/gap-study-4/tests/test_walk_runner.py --generated-mutants --shard i/n` for i = 1..n, with no 115 s cap (the default --timeout is 600).
  Its survivors are the next triage: a test, or an EQUIVALENT entry with a reason.

Evidence (Mac, light-ok before each run, `timeout -s INT 110/115`):
- test_walk_runner, in class groups because the whole module exceeds 115 s at this load: 14 + 29 + 12 = 55 run, 0 failures, 0 errors.
  The groups were R10/R6/R7/G1/R1/R4; R8; and R2/R3/R5/R9/TestSysPath.
- Hand witnesses: 67/67 RED in nine batches (8 x 8 + 3) before the R10 additions. No witness anchor changed after that.
- Red first: there is no production behaviour change this round; the one code edit removes an equivalent line.
  The new tests' red is the reviewer's mutants, each a registry witness and red.
- Gates: copy_manifest --check exit 0 (300 files, 48 fragments; tests/walk_mutation.py claimed new); build_draft --check exit 0 (no input moved); freeze.py --check exit 0; walk_register --check exit 0; run.py --walks --check exit 0.
- Lints: lint_language clean (92 inputs); lint_pooling clean (92 files).
- Not re-run this round: the neighbour modules. No production code they read changed: walk_runner is imported only by test_walk_runner.

## Modules athena must run (updated)

- tests/test_walk_runner.py whole (55 tests), `--witnesses` (67), and `--generated-mutants`, sharded, whole (533; report generated, killed, equivalent, survived).
- The rest as listed before:
  - test_box_integration, test_pipeline, test_scaffold and test_round4, each whole;
  - test_walk_layout, test_cp8_prep, test_cp6_wiring and test_rehearsals, each with `--witnesses`;
  - test_walk_wiring, test_check_take, test_checker_body, test_drive_commit, test_drive_loop, test_mode_binding and test_wave6_bindings;
  - the gates, the w6j and w6e byte bindings, and both lints.
