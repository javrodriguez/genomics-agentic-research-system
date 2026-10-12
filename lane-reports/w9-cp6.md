Status: review round 1 PASS (d5b181fa); w9-close-1 folded; ready for athena

RESUME HERE: athena

# Lane w9-cp6: Gap Study round 4, CP6 wiring

Written Mon 12 Oct 2026, 12:12 EDT (`date`), by the lane's only writer (Claude Opus 5.5), assigned under glitch-2f's wave 9 ruling (the Lane-orchestrator, under Javier's standing delegation).
Branch `gap4/w9-cp6`, base `9961d0a2` (the wave 8 merge, athena PASS).
Code commit `09fd22d0`; this report is in its own commit.
Nothing was pushed or merged, and nothing was spent.
No model, walk, network, Docker, credential, salt or real holdout folder was used.

## What was built

1. K1-launch (Q-w8d-1): a take is checked against its records before launch.
   `WalkDriver.launch` calls `drive.launch_problems` before any take folder, config folder or container exists and before `run_take.launch`.
   A refusal is `drive.LaunchRefused` (a `DriveRefused`), and Batch records it as `failed` with `drive_started` false.
   For a take (`records="takes"`):
   - the slot must have exactly one open registration in the committed takes.json (registered, with no committed outcome), and it must be the slot's latest;
   - every field in the allow-list `LAUNCH_FIELDS` (`stats.TAKE_FIELDS[:8]` plus `slot` and `half_cell`) must be present in both the row and the registration, and equal;
   - the row must be the frozen pre-registration's planned row (`takes.require_planned_row`);
   - the take folder must be `<root>/takes/<slot>/<that attempt>`.
   For a walk (`records="walks"`), the check is the sibling arm.
   The walk is refused if prereg.json exists, if `walk_register.entry_problems` refuses its task, half, wording, arm or model against the design in force, or if its id is already registered (casefold).
   `WalkDriver` now takes `records`, and `walk_driver` passes it.
2. W8B-R2-2: `check_results.synthetic_digest_problems`, called by `check_frozen_content`, re-applies `freeze.synthetic_tasks` to the committed prereg.json.
   It checks the file both as its freeze commit wrote it and as it stands on disk.
   The rehearsal's synthetic digests are refused, naming W8B-gap4-1.
   Under `--rehearsal-plan` they are printed NOT CHECKED.
3. freeze_rehearsal now has a `--holdout-tool` option for the aegis `holdout/tools/holdout.py` (S9b, aegis master 76ec9f5).
   With it, the `holdout.py --check` gate runs that tool's `--check` with these arguments:
   - `--holdout <clone>/evals/gap-study-4/fixtures/holdout-rehearsal`, a SYNTHETIC fixture committed here;
   - `--gars <clone>`;
   - `--sha <clone HEAD>`.
   The tool path is refused if it is relative, not named holdout.py, missing, or inside this repository.
   The rehearsal has no holdout-folder option, and the parser takes no abbreviation.
   It never runs `--digests` or `--make-salt`: salt and digests happen at the freeze only (W8B-gap4-1 A).
   Without `--holdout-tool`, the step stays OWED and the run is not all green, so H11 is unchanged.
   The fixture holds one file per draft task, with ids h1-h3 and obviously fake wordings built to the S9b pack's shapes and word bands.
   The real tool accepts it: `load: ok, 9 task files, 27 wordings` and `check: ok, 84 held-out fields, 0 shared runs (against 352 public sources, 18 right_move.why texts)`, exit 0, at 9961d0a2 and again at 09fd22d0.

## Evidence (Mac, each run behind `mac_slot.py light-ok` and `timeout -s INT 120`, /usr/local/bin/python3.13)

- Red first: the new tests/test_cp6_wiring.py ran against the base's drive.py, check_results.py and freeze_rehearsal.py, restored afterwards byte for byte (cmp).
  Result: 5 run, 5 failures, 0 errors, exit 1, every failure by assertion with its clause token.
- Green: test_cp6_wiring printed "5 run, 0 failures, 0 errors, 0 skipped", exit 0.
- Witnesses: 17/17 RED, in three batches (3/3, 6/6, 8/8), exit 0 each; the registry is 17.
- The neighbours, each one module, printed:
  - test_cp8_prep: 4 run, 0 failures; its witnesses 15/15 red.
  - test_walk_wiring: Ran 20, OK.
  - test_walk_layout: 14 run, 0 failures; its witnesses 21/21 red.
  - test_holdout_digests: 12 run, 0 failures; its witnesses 18/18 red.
  - test_rehearsals: 9 run, 0 failures; its witnesses 20/20 red.
  - test_drive_commit: Ran 31, OK. test_drive_loop: Ran 27, OK.
  - test_build_draft: Ran 45, OK; its Claims class 2 run.
  - test_ci_job: Ran 23, OK. test_mode_binding: Ran 8, OK.
  - test_scaffold, TheManifest.test_check_passes_on_the_folder and TheImports: Ran 4, OK.
- test_walk_layout's L1 (one name for record roots) first failed on my `("takes", "walks")` tuple.
  It now reads `RECORD_FOLDERS`, and L1 is green.
- test_box_integration timed out at 120 s here (rc 124), which is not a failure; it is owed to athena.
- Gates: copy_manifest --check exit 0 (295 files, 47 fragments); build_draft --check exit 0 (no draft input moved, so prereg-draft.json is untouched); freeze.py --check exit 0 (295 owned paths); walk_register --check exit 0 (0-walk line).
- lint_language reports "clean, 91 input(s)" and lint_pooling "clean, 91 file(s)", both exit 0.

## Ownership

- `COPIED.d/w9-cp6.json` claims these files:
  - drive.py, transferred from w8d-cp8-prep (the note is in w8d's self-entry);
  - tests/test_cp6_wiring.py;
  - checks.d/w9-cp6.txt;
  - the nine fixture files;
  - itself.
- These edits were made without a transfer, each recorded in its owner's entry:
  - departure w9-1, check_results.py (w5b-cp5-pipeline);
  - departure w9-2, freeze_rehearsal.py (w8b-holdout-digests). Both stay with their owners because tests/test_pipeline.py's PipelineOwnership binds them there.
  - tests/test_walk_wiring.py (w7b-walk-wiring): W1-strict now registers its row before it launches.

## Open questions

- Q-w9-1 (RULED w9-Q1, folded below), the stuck slot: take_folder_in still counts the folders on disk (Q-w6i-1).
  After a launch is refused before its folder exists (W7C-R1-3's month-turn hold), every later attempt of that slot is now refused before launch. Before this lane, it ran (paid) and was refused at the commit.
  The slot stays blocked, at no cost, until someone rules.
  Proposed answer: make the production take folder `takes/<slot>/<registered attempt>`, read from the open registration this lane already reads, and refuse when that folder exists.
  That is a one-line change to how the folder is chosen. It needs a ruling because it reverses Q-w6i-1's "next unused k".
- Q-w9-2 (RULED, accepted: no change now; owed to the walk-runner slice, which gets the check through `walk_driver(records="walks")`): the walk arm is wired, but nothing drives walks through it yet: WalkRepo refuses `register`, so no Batch drives a walk.
  Proposed answer: the walk runner (CP6) calls `walk_driver(records="walks")` and gets this check for free; no change now.
- Q-w9-3 (RULED, accepted: regenerated only when the aegis tool refuses it, and that red is correct): the synthetic fixture is static.
  If a task's wording shape or word band changes, the rehearsal's holdout step goes red. That is a correct red, and the fix is to re-derive the fixture.
  Proposed answer: keep it static; regenerate it only when the aegis tool refuses it.

## Modules athena must run

- tests/test_cp6_wiring.py and `--witnesses`
- tests/test_box_integration.py (timed out on the Mac)
- tests/test_pipeline.py (never run here, by rule; PipelineOwnership and the check_results and freeze_rehearsal mutants)
- tests/test_scaffold.py (whole)
- test_round4.py (the battery)
- tests/test_cp8_prep.py, tests/test_walk_wiring.py, tests/test_walk_layout.py, tests/test_holdout_digests.py and tests/test_rehearsals.py, each with its `--witnesses`
- tests/test_drive_commit.py, tests/test_drive_loop.py and tests/test_build_draft.py (with `--witnesses` 1 to 6)
- The gates: copy_manifest --check, build_draft --check, freeze.py --check, walk_register --check, lint_language and lint_pooling over the folder
- Optional, where aegis is present: freeze_rehearsal.py with `--holdout-tool <aegis>/holdout/tools/holdout.py`

## Rulings (glitch-2f, the Lane-orchestrator under Javier's delegation, Mon 12 Oct 2026)

- w9-Q1: Q-w9-1 accepted as proposed. A take's folder comes from the open registration's attempt, and the launch is refused by name if that folder already exists.
  This reverses Q-w6i-1 because the facts changed: a launch is now refused before its folder exists, so counting folders on disk would strand the slot.
  The ruling said to fold it in this slice.
- Q-w9-2 accepted: no change now; owed to the walk-runner slice.
- Q-w9-3 accepted: the fixture is regenerated only when the aegis tool refuses it.
- Departures w9-1 and w9-2, and the change to test_walk_wiring's W1 check, are accepted.

## Fold w9-Q1, Mon 12 Oct 2026 12:20 EDT (`date`)

- `take_launch_problems` now returns `<root>/takes/<slot>/<the open registration's attempt>` and refuses it by name ("... already exists ... (ruling w9-Q1)") when it exists.
  The comparison with the counting `take_folder` is gone.
- `WalkDriver.launch` hands that folder to `TakeDriver.launch` through one in-place edit: a private `_folder` keyword, where None still reads `take_folder`.
  A walk keeps `walk_folder_in`'s folder.
- `take_folder_in` itself is unchanged, so its readers (test_walk_wiring W2, test_walk_layout L2, test_cp8_prep K1) are untouched.
  K1 at the commit (`take_k_problems`) stays as the second guard.
- Tests: K1 case 2 is now the stuck slot.
  Attempt 1 is committed `failed` with `drive_started` false, then attempt 2 is registered and launches into takes/s1/2, and takes/s1/1 is never made.
  New case 2b: when the registered attempt's folder already exists, the launch is refused by name with nothing made or launched.
  Case 5 (through a real Batch) now asserts "already exists".
  The swapped-take_folder case is gone, because launch no longer reads take_folder for a take.
- Witnesses: launch-folder-unchecked is replaced by launch-folder-counted (the folder taken from the count again) and launch-folder-exists-admitted.
  launch-unchecked was re-anchored. The registry is now 18.

Evidence (Mac, `mac_slot.py light-ok` and `timeout -s INT 120`, python3.13):
- Red first: the new tests against 09fd22d0's code gave `test_cp6_wiring: 1 run, 1 failures, 0 errors` (K1Launch only).
  The failure was by assertion: "K1.launch: the stuck slot's attempt 2 was refused: LaunchRefused: the take folder would be .../takes/s1/1, and slot 's1''s open registration is attempt 2 ...".
- Green: `test_cp6_wiring: 5 run, 0 failures, 0 errors, 0 skipped`.
  Witnesses: 18/18 RED in three batches (6/6 each), exit 0.
- test_walk_wiring: Ran 20, OK. test_drive_commit: Ran 31, OK. test_drive_loop: Ran 27, OK.
- test_cp8_prep: 4 run, 0 failures, with 15/15 witnesses red. test_walk_layout: 14 run, 0 failures.
- Gates: copy_manifest --check exit 0 (295 files, 47 fragments); build_draft --check exit 0; freeze.py --check exit 0; walk_register --check exit 0 (0-walk line).
- lint_language: clean, 91 inputs. lint_pooling: clean, 91 files.

The athena module list above is unchanged; test_cp6_wiring's witnesses now number 18 (20 after the w9-close-1 fold below).

## Fold w9-close-1, Mon 12 Oct 2026 12:31 EDT (`date`)

Review round 1 passed at d5b181fa (lane-reports/w9-cp6-review-r1.md).
Ruling w9-close-1 (glitch-2f) asked for two cheap items, then athena.

- W9-R1-1: K1 gains case 2c.
  takes.json is appended by hand, one row per commit, with attempts 1 and 2 of slot s1; only attempt 2 has a committed outcome.
  The launch is refused: the open registration (attempt 1) is not the slot's latest.
  Batch cannot reach this state (`takes.guard_registration` refuses it), so the guard is defence in depth, now bound.
  New witness: launch-latest-unchecked.
- Honesty of the record: with `--holdout-tool`, freeze_rehearsal names the step `HOLDOUT_STEP_LABEL`.
  The label reads "holdout.py --check on the synthetic fixture evals/gap-study-4/fixtures/holdout-rehearsal, not the real holdout".
  It is used in both places the step is written: stdout, and the report that a freeze records as its rehearsal record.
  R1 asserts the label in both, and that no line names the step without it.
  New witness: tool-label-dropped.
  Without `--holdout-tool` the OWED step keeps its plain name, so H11 is unchanged.

Evidence (Mac, `mac_slot.py light-ok` and `timeout -s INT 120`, python3.13):
- Red first, label: the new R1 assertions against the unfolded freeze_rehearsal.py gave `test_cp6_wiring: 5 run, 1 failures, 0 errors`.
  The failure was by assertion: "'[0] holdout.py --check on the synthetic fixture ..., not the real holdout\n    ok' not found".
- Red first, latest guard: the guard already existed, so the new case passed on the unfolded code.
  Its red is the mutant: launch-latest-unchecked (the guard set to `if False:`) gave "K1.launch: RED", 1/1. The reviewer had reported SURVIVED before this case.
- Green: `test_cp6_wiring: 5 run, 0 failures, 0 errors, 0 skipped`.
  Witnesses: 20/20 RED in three batches (7/7, 7/7, 6/6), exit 0 each; the registry is 20.
- test_rehearsals: 9 run, 0 failures; witnesses 20/20 red. test_holdout_digests: 12 run, 0 failures.
- Gates: copy_manifest --check exit 0 (295 files, 47 fragments); build_draft --check exit 0; freeze.py --check exit 0; walk_register --check exit 0 (0-walk line).
- lint_language: clean, 91 inputs. lint_pooling: clean, 91 files.

Athena runs the module list above; test_cp6_wiring's witnesses now number 20.
