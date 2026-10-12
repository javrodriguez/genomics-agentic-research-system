status: hand-back for review; code complete for P2 (see "Not built")
head: see RESUME HERE. Base d051bece (the wave 6 merge head), branch gap4/w7b-walk-wiring, worktree /Users/javrodher/aegis-builds/gap4-w7b.

# Lane w7b-walk-wiring: Gap Study round 4, wave 7 piece P2, the CP6 walk wiring

_Written Sun 11 Oct 2026 23:53 EDT (`date`) by the piece's sole writer (Claude Opus 5.5 sub-agent), assigned by glitch-1b under Javier's standing delegation. Spec: plans/gap-study-round-4/cp6-readiness-2026-10-11.md (row 3, section 2), the "Wave 7 started" block of next-slices-2026-10-11.md, W6J-close-1's C6-strict item, Q-w6i-1, Q-w6i-5, the end-to-end take (L-S6-1, w6j "Not built"), W6B-R1-3._

No image or container was built or run.
No model was run, no API was called, and no test used a network.
No login, `.env`, sealed, holdout, brief or saved-output path was read.
Nothing was pushed, merged or dispatched.
build_draft.py, prereg.py and the draft were not touched (P1's).

## What each item does, with its test

- **C6-strict.** `drive.walk_driver(...)` is the production road: it builds `WalkDriver` (a TakeDriver) with the Claude Code adapter, `script_from_design` and `take_checker`, all fed by one `design_for(row, run_tree)`.
  Its script is strict by construction: the factory takes no `strict_script`, `WalkDriver(strict_script=...)` raises TypeError, and assigning any value but True raises DriveRefused.
  Test W1-strict (tests/test_walk_wiring.py): a bare operator line through the walk driver is refused naming the bare line, before any turn is sent. Witnesses walk-not-strict, walk-strict-settable.
- **Q-w6i-1.** `mode_binding.TAKES_DIR = "takes"` is the one name; `TAKE_ROOTS = (TAKES_DIR,)`; `drive.TAKES_DIR` reads it and `drive.take_folder_in(root)` gives `<root>/takes/<slot>/<k>` (k the next unused attempt; a slot that is not one path segment refuses).
  Found on the way: `mode_binding.judge()` read the harness from a top-level `harness` key the round-4 driver never writes (driver-ledger.json has `agent.harness`), so every real take would have failed `--check` as "no profile under harness '?'". Now `ledger_harness()` reads the driver's shape; test_mode_binding's synthetic ledgers carry it.
  Tests W2-folder; M3-folder (test_mode_binding). Witnesses folder-renamed (drive), top-level-harness (mode_binding), and both again end to end.
- **Q-w6i-5.** check4 refuses a design view naming no run tree (CheckRefused), and `check_take.design_tree_problems` reads the session's own working directory (`session_run_tree`) against the view's run tree: a mismatch is `[readers-disagree]` naming both trees, so routing gives a rehearsal before the first agent turn and harness-error after it. Readers-disagree was chosen over a refusal because the plan routes a disagreement of two readers of one take that way (the meaning widened as Q-w6j-4 already widened it); a session recording no working directory is checkout-binding already.
  Tests R9-tree (test_checker_body) and E2-tree (end to end). Witnesses tree-unchecked, tree-none-admitted, tree-unchecked-end-to-end.
- **W6B-R1-3.** w6b folded it as a docstring plus a named residual: "any persisted stub take must stamp the stub's identity". A take is persisted only through TakeDriver, whose records name the row's harness. One line in TakeDriver.drive now calls `adapter_identity_problems(adapter, row)`: an adapter whose own `name` is not the row's harness (a stub under a claude-code row, or an adapter naming none) raises AdapterIdentityRefused, a stop and never a rehearsal, before it starts. So a persisted stub take names the stub.
  Test W3-identity. Witness identity-unchecked. On d051bece a stub adapter under a claude-code row was started and driven.
- **The end-to-end take (E1-take).** batch.Batch drives the walk driver: the real Claude Code adapter on a fake box that answers in the recorded stream shape and writes a session file, preflight through S1's entry point (spied), the real check4 on round 4's real design (scope-read / trap / w3 / arm A) through take_checker, routing, and TakeRepo's commit into a scratch repository.
  It is GRADED, and the committed take folder `takes/<slot>/1/` holds driver-ledger.json, environment.json, transcript.jsonl (the session copy, account email scrubbed) with scrub.json, operator-check.json, launch, preflight, postflight, teardown, turn-1.jsonl and evidence/ledger.jsonl; mode_binding reads it from TAKES_DIR with no problem.
  Test data, labelled in the module and never written into production: the six checker constants (environment_record mirrors drive.py's published vocabulary; budget 600 = the driver's), one claude-code routing pin for the row's model, the row's agent version, a synthetic row commit and its session id, and `fixture_record()`, a synthetic fixture builder (hashed fixtures only). Production constants stay PENDING (a test says so).
- Binding W6M1 for the new module (its tearDownModule puts sys.path back), by test_wave6_bindings' own probe.

## Red first, then green (Mac, `mac_slot.py light-ok`, `timeout -s INT 120`, Python 3.13.2 at /usr/local/bin/python3.13, `-B -W ignore`)

Red used byte backups of drive.py, check_take.py and mode_binding.py with d051bece's bytes put in place, then restored; `shasum -a 256 -c` OK on all three. Every red was by assertion, 0 errors.
- test_walk_wiring TestTheWalkWiring + TestTheEndToEndTake: Ran 6, failures 5, rc 1 (W1, W2, E1, E2: the walk API absent; W3: a stub adapter under a claude-code row was not refused, it was started).
- test_mode_binding TestModeBinding: Ran 4, failures 3, rc 1 (M1, M2: harness '?'; M3: no TAKES_DIR).
- test_checker_body TestTheRealDesign: Ran 14, failures 1, rc 1 (R9: reasons operator-lines, fixture-binding, no readers-disagree).
- Which link fails on d051bece: a probe (not committed) joined the base pieces with a test-side shim of the walk wiring (TakeDriver(strict_script=True), claude_code_adapter_for, script_from_design, take_checker, a takes/ folder). The end-to-end take itself graded on the base and left its records; the two failing links were mode_binding (`routing.json pins no profile for 'claude-opus-5-5' under harness '?'`) and a session that opened outside its run tree, which was GRADED.

Green at 4749620c, each rc 0 ending in a bare OK:
- test_walk_wiring 15 (7 witnesses red: walk-not-strict, walk-strict-settable, folder-renamed, identity-unchecked, folder-renamed-end-to-end, top-level-harness-end-to-end, tree-unchecked-end-to-end; W6M1 binding for this module);
- test_checker_body 29 (13 witnesses red, tree-unchecked and tree-none-admitted new); test_mode_binding 8 (model-only, top-level-harness red);
- test_check_take 15 (5 witnesses, counts unchanged); test_drive_loop 27 (16 witnesses, counts unchanged); test_box_integration TestGuardArmed + TestTheTakePath + TestRealBoxStub 20, TestBoundChecks 19, its 21 witnesses in six groups, all red with S6/S6b counts unchanged;
- test_drive_commit 31 (10 witnesses); test_claude_code_adapter 19 (9); test_wave6_bindings 2; test_scaffold TheManifest.test_check_passes_on_the_folder and TheImports (3); test_build_draft Claims 2;
- copy_manifest --check (258 files, 38 fragments), freeze --check (258), probes4 --check (1690 cells, 0 defects), mode_binding --check (graded 0), build_draft --check; the check_take.py round-3 byte binding and w6e's drive.py prefix binding, rc 0;
- lint_language: no new finding in any touched file (drive.py 12, check_take.py 7, mode_binding.py 2, test_checker_body.py 5, as on d051bece).

## Departures (for glitch-1b)

- w7b-1: ownership transfer under ruling W7B-gap4-1 (COPIED.d/w7b-walk-wiring.json): drive.py, check_take.py, tests/test_checker_body.py, tests/test_box_integration.py from w6j; mode_binding.py, tests/test_mode_binding.py, tests/test_check_take.py from w6i (transfers named in both old fragments). test_scaffold's copied_modules and test_build_draft's Claims hand list also read the w7b fragment (recorded in w1a's and w5c's entries); the floor holds at 31. This touches test_build_draft.py's hand list, which P1 (W6-claims-1) replaces with a derived list: a one-line merge conflict, resolved by taking P1's derived list.
- w7b-2: the transferred modules' commands stay in w6h's, w6i's and w6j's checks.d files (moving test_mode_binding would leave w6i's file with no command, which run_checks counts as a failure); checks.d/w7b-walk-wiring.txt adds test_walk_wiring and `mode_binding.py --check`.
- w7b-3: test_check_take's synthetic design names a run tree (`/work/run`); test_box_integration's DuckAdapter names its harness.
- w7b-4: one code commit (the items are interlocked through test_walk_wiring), then this report commit, in place of a commit per item.

## Questions for glitch-1b

- Q-w7b-1: a stub take through TakeDriver (the CP6 real-box stub run) reaches `_environment`, which reads `run_take.LOGIN_VARIABLE[harness]`; there is none for "stub", so a stub take rehearses there. The real-box stub run needs a stub branch (no login) in run_take/drive; not built here (no recorded shape for it).
- Q-w7b-2: readers-disagree for a run-tree mismatch, rather than a CheckRefused stop: accepted reading of the plan's routing, as Q-w6j-4 widened it; confirm.
- Q-w7b-3: `batch.main` still prints "no driver exists yet"; the CLI entry that builds walk_driver from the real box (DockerRuntime, the login file, the counters reader, the identity from the registration and run-tree builder) needs those CP2/CP6 values and is not wired.

## Not built, and why

- The real fixture builder and run-tree builder (identity_for in production): the test's synthetic fixture builder covers hashed fixtures only; project fixtures need stage 01's exits.
- Walk-measured values: every PENDING constant stays PENDING; the end-to-end take proves the joint with labelled test data only.

Not run on the Mac: the whole test_scaffold, test_pipeline and run_checks (athena's). test_box_integration's 21 witnesses ran in six groups (each under 120 s).

## Fold of review round 1 (W7B-close-1, glitch-1b, 12 Oct)

Round 1 passed with no MAJOR (plans/gap-study-round-4/w7b-review-r1-2026-10-12.md). Folded at 8178b30d (written Mon 12 Oct 2026 00:20 EDT, `date`); R1-3, R1-4 and R1-5 are carried to CP6 by the ruling and not touched.
- W7B-R1-2: walk_driver refuses a root that is not mode_binding.HERE. Test W4-root; witness root-unchecked.
- W7B-R1-1: W5-one-road reads every non-test .py under evals/gap-study-4 by AST and refuses a TakeDriver( call or a TakeDriver subclass other than WalkDriver. Witnesses added-construction and added-subclass (batch.py's source extended in memory).
- W7B-R1-6: W6-pending requires the six walk-measured checker constants to be PENDING, every other entry to be one of the two known values, and routing.json's pin_profiles to be {}. Witnesses constant-filled and pin-filled.

Red first on 4749620c's drive.py (byte backup restored, `shasum -c` OK): TestTheWalkWiring + TestTheEndToEndTake ran 10, failures 1 (W4: another root accepted), 0 errors, rc 1. W5 and W6 hold on that code as well; their red is their witnesses.
Green at 8178b30d: test_walk_wiring 20, rc 0, bare OK, 14 witnesses red (0 NOT KILLED); copy_manifest (258 files, 38 fragments), freeze, mode_binding --check, both byte bindings rc 0; lint_language adds no finding.

RESUME HERE: hand-back at 8178b30d
