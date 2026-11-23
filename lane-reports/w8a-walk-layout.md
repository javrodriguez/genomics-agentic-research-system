status: closed

# Lane w8a-walk-layout: Gap Study round 4, the walk layout (ruling W8-layout-1, Option A)

Written Mon 12 Oct 2026, 01:32 EDT (`date`), by the lane's sole writer (Claude Opus 5.5), assigned by glitch-1b under Javier's standing delegation.
Branch `gap4/w8a-walk-layout`, base `818ccb70` (the full wave 7 merge).
Code commits `01b53dbb` (code and tests) and `b45329d4` (ownership records, checks.d, README); this report is report-only.
Nothing was pushed, merged or dispatched, and no walk, model, network, Docker, credential, brief, saved output, holdout or sealed path was used.
`ci.yml` and the plan were not touched.

## What was built (each item with its test in `tests/test_walk_layout.py`)

1. One walk, one folder: `rehearsals/<walk>/` holds a take folder's records plus `grade.json` (`run.grade_walk`: `run.regrade()`'s output with a study-relative `graded_by`, or `{"graded": false, "why": ...}` from the driver ledger when there was no first agent turn). `drive.walk_files` is the closed map (take_files' kinds, now shared through `record_kind`, plus `grade.json`; `driver-ledger.json` and `grade.json` required). `walk_driver(records="walks")` launches into `rehearsals/<walk>/` (`walk_folder_in`; bad id or existing folder refused), `records="takes"` keeps `takes/<slot>/<k>`, any other value refuses. L2, L10.
2. `drive.WalkRepo.commit_walk(entry)`: one commit holding `rehearsals/<walk>/**` and the new `register.json` entry, through `scan_record`, re-stage, tree binding and blob check, subject "Commit one walk; never counted"; refused once `prereg.json` exists; `register`/`commit_records` refuse (a walk is never a take). TakeRepo stays post-freeze (`takes.commit_registration` → `prereg.require_frozen`). L3, L4.
3. `copy_manifest`: a file inside `rehearsals/<walk>/` is claimed exactly when the register lists the walk (and `takes/<slot>/<k>/**` when `outcomes.json` names it; empty today); an unregistered walk folder's files still fail; a fragment claiming a record path is refused. L7.
4. One name: `mode_binding` defines `TAKES_DIR`, `WALKS_DIR`, `RECORD_ROOTS`, `RECORD_DEPTH`, `WALK_GRADE`, `record_transcripts`, `record_parts`; drive, walk_register, run, copy_manifest, lint_language (closes W7B-R1-3), fixture_walk, build_cases and leak_grep import them. Round 3's host road (`drive.main --walk`, `route_attempt`) is shadowed by refusals naming the walk runner, its bytes kept and reachable only through `ROUND3_ONLY`; round 3 roots that remain elsewhere are listed in L1's `EXEMPT` with reasons (other studies' folders; `denials.py`, Q-w8a-1). `mode_binding --walks` now judges walks against their pins as takes are judged (round 3's superseded-walk rule removed). L1, L8, L9.
5. `run.grade_committed` binds `record_dir` to `takes/`: a walk folder is never graded into results; `run.py --walks --check` regrades every registered walk and requires `grade.json` byte-identical. L5, L6.
6. `freeze_rehearsal.COMMANDS` gains `walk_register.py --check`, `mode_binding.py --walks --check`, `fixture_walk.py --check`, `run.py --walks --check`. L11.
7. `rehearsals/README.md`: Q1, Q2, Q4, Q5 closed with their evidence; Q3 (coverage) and Q6 (publication) open.

## Evidence (Mac, each command prefixed by `mac_slot.py light-ok &&` and `timeout -s INT 120`, Python 3.13.2, `env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV`)

- Red first on `818ccb70` (a detached worktree of the base with only the new test file added): 14 run, 14 failures, 0 errors, exit 1. L5's red is the finding itself: "L5.never-results: rehearsals/w-0001 reached the grader".
- Green: 14 run, 0 failures, 0 errors, exit 0.
- Witnesses (rule B, each mutant compiled in memory, only its bound test run, red only by that test's AssertionError carrying its clause): 13/13 RED, run as two batches (10 + 3), exit 0 each: leak-grep-own-root (L1), walk-folder-under-takes (L2), freeze-unchecked (L3), register-in-another-commit (L4), binding-to-the-study (L5), regrade-uncompared (L6), record-claims-dropped, unregistered-claimed, fragment-record-admitted (L7), take-roots-respelled (L8), walks-read-two-levels (L9), content-rule-skipped (L10), gate-dropped (L11).
- Gates: `copy_manifest --check` exit 0 (273 files, 42 fragments); `freeze.py --check` exit 0 (273 owned paths); `walk_register --check` exit 0 (0 walks line); `probes4 --check` exit 0; `batch --check` exit 1 on its three not-ready lines (pin_profiles empty, pin_profiles_status, spend_cap_markers_status), identical to the base; `mode_binding --walks --check`, `run.py --walks --check`, `fixture_walk --check` exit 0 with their 0-walk lines; `leak_grep --check` exit 1 on 0 sessions, as on the base.
- Regressions: test_rehearsals 9/9 and its 20/20 witnesses; test_mode_binding 8/8; test_walk_wiring 20/20 (its witnesses included); test_drive_commit 31/31 (three of its witness anchors first occurred twice because WalkRepo repeated their lines; WalkRepo's lines were reworded, then green); test_box_integration run class by class and witness by witness (the module exceeds 120 s whole): 4 classes and 21 witnesses, exit 0 each; test_pipeline FreezeCoverage, PipelineOwnership, PublishedArtifacts 16/16 (the disposable rehearsal clone now copies mode_binding.py and walk_register.py, which run.py and copy_manifest.py import); test_scaffold TheManifest, TheImports, TheBinding method by method: 34 methods, exit 0 each.
- Lint: README and register clean; the whole study shows the base's 27 findings, one of them (the word "always" in the drive.py entry's carried reason) moved from w7b's fragment to w8a's.
- Not run: whole test_scaffold, test_pipeline (except as noted below), run_checks, test_round4; freeze_rehearsal.py itself (remote runner only, per its docstring).
- Note: one attempt to run three test_pipeline classes by argument ran the whole module three times (its `__main__` ignores argv): 85 tests each, the two failures then fixed by the clone list above. That broke the "never the whole test_pipeline" rule by accident; recorded here.

## Ownership (ruling W8A-gap4-1) and departures

- New fragment `COPIED.d/w8a-walk-layout.json`: drive.py, mode_binding.py (from w7b); walk_register.py, rehearsals/README.md (from w7d); copy_manifest.py, lint_language.py, fixture_walk.py, build_cases.py, leak_grep.py (from w1a, the last three now `edited`); run.py, freeze_rehearsal.py, tests/test_pipeline.py (from w5b); tests/test_walk_layout.py, checks.d/w8a-walk-layout.txt and the fragment. Each transfer is named in the old owner's own fragment entry.
- Departure w8a-1: rehearsals/README.md moved with walk_register.py (item 7 edits it).
- Departure w8a-2: tests/test_pipeline.py moved and edited (take folder `artifacts/s1` → `takes/s1/1`; expected COMMANDS; pipeline-ownership lane; the clone's module list), forced by the run.py and freeze_rehearsal.py changes.
- `checks.d/w8a-walk-layout.txt`: test_walk_layout, its --witnesses, walk_register --check, run.py --walks --check, mode_binding --walks --check.

## Open questions for glitch-1b

- Q-w8a-1: `denials.py` still reads `transcripts/*/*/*/*/transcript.jsonl` under this study (round 3's take layout, w1a's, a CP7 concern); nothing in round 4 writes there now. Exempted in L1 by name.
- Q-w8a-2: WalkRepo repeats TakeRepo's scan, re-stage, tree-binding and blob-check block (reworded so w6e's witness anchors stay unique). Folding both into one helper would move w6e's anchors; L4 covers the walk copy's one-commit property only, not each of its guards.
- Q-w8a-3: `grade.json` rides the scan as kind `ledger` (w4c's call whether it deserves its own kind).
- Q-w8a-4: a register entry carries no pressure or repeat; a graded walk's cell is read back from its own `grade.json` row, so those two fields are self-asserted (task, half, wording, arm and model are bound to the register, agent and project to the driver ledger).
- Q-w8a-5: `mode_binding --walks --check` now judges walks against routing pins, which stay PENDING until walks measure them, so it fails on any real walk until the pins are filled; in the freeze rehearsal (post-freeze) that is the intended state.
- Q-w8a-6: the walk runner itself (walk rows → `walk_driver(records="walks")` → `write_walk_grade` → `WalkRepo.commit_walk`) is not built; batch.Batch keys its driver by slot and has no walk road.
- Proposed plan amendment for Javier (not applied): append `walk_register.py --check` to CP6's VALIDATE line (893). The CI walk step waits for CP8 (w5c's contract).

## Not built

- L11's second half (freeze_rehearsal.py in a throwaway clone with one committed walk, ending "all green"): remote runner only.
- L4 drives synthetic walk records into WalkRepo, not an end-to-end fake drive through check4 (w7b's E1 already covers the drive road into takes/).
- L5's `check_results --ledger` half: only `stats.load_results` is shown reading 0 records from a tree holding a walk.

RESUME HERE: hand-back at b45329d4

## Appendix: fold W8A-close-1 (review round 1: 1 MAJOR, 2 MINOR, 2 NIT)

Written Mon 12 Oct 2026, 01:55 EDT (`date`), by the same writer, on glitch-1b's ruling W8A-close-1 (table `plans/gap-study-round-4/w8a-review-r1-2026-10-12.md` in the Brain).
Base `e7f1aacd`; fold code commit `ebdebd10`.

- R1-1 (MAJOR): after `head = rev-parse HEAD`, WalkRepo refuses when `git cat-file -e <head>:<study>/prereg.json` succeeds, and again for the written tree; the disk check stays. L3: a freeze committed then deleted on disk only is refused by the HEAD reading (HEAD unmoved, nothing staged, register restored). Witness freeze-at-head-unchecked. The tree reading has no witness of its own: behind the staged-names check, the index differs from HEAD only by the walk's declared files, so it fires only on a race.
- R1-2: the driver ledger records the row's `pressure` and `repeat`; `walk_row` takes the cell from the ledger and refuses any other cell handed in (from the writer or from `grade.json`), and a ledger without them. L6 + witness cell-from-grade-unchecked.
- R1-3: `grade_committed` requires `takes/<slot>/<k>` exactly (RECORD_DEPTH parts), equal to the row's slot and attempt. L5 (takes/s1, takes/s1/1/evidence, takes/s2/1, takes/s1/2 refused) + witness take-folder-depth-unchecked.
- R1-4: the L1 scan also flags module-level string constants that start with a root name; `template_offer_reading.TASK_DIR` exempted (the earlier rounds' folders). Witness module-constant-root.
- R1-5: no change; recorded for the CP8 CI step.

Evidence (same Mac conditions):
- Reviewer's probes reproduced on e7f1aacd: P1 committed a walk on a frozen HEAD, P2 `([], 1)` under an invented pressure, P3 takes/s1 and takes/s1/1/evidence reached the grader, P4 and P5 as the review says. On ebdebd10: P1 refused, P2 refused (ValueError naming the ledger's cell), P3 all four refused, P4 and P5 unchanged.
- Red first (new tests against e7f1aacd): 14 run, 3 failures (L3, L5, L6), 0 errors, exit 1. R1-4 is a test-side rule, so its red is its witness.
- Green: 14 run, 0 failures, 0 errors, exit 0. Witnesses 17/17 RED (14 + 3 batches, exit 0).
- Regressions green: test_drive_commit 31, test_walk_wiring 20, test_rehearsals 9, test_mode_binding 8, test_drive_loop 27, test_box_integration TestTheTakePath 17 and TestBoundChecks 19, test_pipeline PublishedArtifacts and FreezeCoverage 15.
- Gates: copy_manifest --check, freeze --check, walk_register --check, probes4 --check exit 0; batch --check exit 1 on its three not-ready lines.

## Appendix: fold W8A-close-2 (review round 2 PASSED; three cheap items)

Written Mon 12 Oct 2026, 02:08 EDT (`date`), by the same writer, on glitch-1b's ruling W8A-close-2.
Base `1aa15486`; fold code commit `98c3a3a2`.

- R2-1: WalkRepo also refuses when `git log -1 --format=%H <head> -- <study>/prereg.json` is non-empty (or git cannot read the history). L3: a freeze committed, then removed by `git rm` and a commit, then a walk: refused, HEAD unmoved. Witness history-unchecked.
- R2-3: `grade_committed` reads `row["slot"]` and `row["attempt"]`; a row without either raises KeyError (L5). Witness slot-defaulted.
- R2-4: the L1 scan also matches a bare root name and annotated assignments at module level (mode_binding.py, which defines them, is skipped). Witness bare-root-constant. A walk's driver-ledger cell must hold exactly one of pressure and repeat as None (stats._one_level); L6 refuses both None and both set. Witness cell-level-unchecked.
- R2-2: no change; recorded for CP8 with R1-5.

Evidence (same Mac conditions):
- Red first (new tests against 1aa15486): 14 run, 3 failures (L3, L5, L6), 0 errors, exit 1. R2-4's scan half is a test-side rule; its red is its witness.
- Green: 14 run, 0 failures, 0 errors, exit 0. Witnesses 21/21 RED (14 + 7, exit 0 each).
- Regressions green: test_drive_commit 31, test_walk_wiring 20, test_pipeline PublishedArtifacts 5.
- Gates: copy_manifest --check, freeze --check, walk_register --check, probes4 --check exit 0; batch --check exit 1 on its three not-ready lines.

RESUME HERE: w8a closed at 98c3a3a2
