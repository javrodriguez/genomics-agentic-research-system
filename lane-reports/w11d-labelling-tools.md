status: open (review round 1 pending)

# Lane w11d-labelling-tools: Gap Study round 4, CP8's blind sample, blind sheet and agreement table

Written Mon 12 Oct 2026, 18:12 EDT (`date`), by the lane's sole writer (Claude Opus 5.5), assigned by glitch-2f (Lane-orchestrator) under Javier's standing delegation.
Branch `gap4/w11d-labelling-tools`, base `f14ab57b`, worktree `/Users/javrodher/aegis-builds/gap4-w11d`.
Commits: `b9436d88` (tests first, red; fragment and checks file), `f4c6c693` (more tests first, red), `dfe33600` (the code, green), and the commit carrying this report and one test fold (G4's exact row line).
Nothing was pushed, merged or dispatched.
No take, model, network, Docker, credential, `.env`, salt, holdout, brief, saved output or sealed path was used; nothing under the three holdout paths was read, listed or touched.

## What was built (each item with its tests)

1. `labelling/sample.py`: the seeded, stratified draw (plan CP8 lines 924-932, D6 A, D8 lines 497 and 671).
   The frame (`labelling/frame.json`, written at CP8) holds one entry per graded take: its id, whether the access log and the tool-call reader agree, and its results record unchanged.
   The frame binds to the committed results both ways.
   A stratum is (arm, harness, model, task, strict-view verdict, readers).
   Every cell gets an equal share of `about_n`, with a seeded remainder.
   Inside a cell, the share is split by largest remainder in proportion to size times factor, where failures and disagreements each carry their pinned factor, never past a stratum's size.
   Every design model must be drawn.
   The drawn takes are shuffled before numbering, so the sheet's order says nothing about the strata.
   `--pin` prints the seed, the strata, the canonical design and its sha256, so the freeze can pin them.
   `--check` re-derives the sample from the frame, the results and `prereg.json`'s `labelling_design` and refuses drift.
   Tests: D1, F1, B1, A1, S1 (with a pinned golden draw), O1, M1, W1, P1, C1, C2.
2. `labelling/sheet.py`: the blind sheet.
   Items hold exactly sheet id, task, text and actions, and `render` refuses any other key.
   The sheet id is the sample's shuffled number, never the take's id.
   Model ids, harness names, vendor and family words, and take ids are masked case-insensitively, and `write_sheet` refuses a sheet in which any of them is still found.
   Each action must already be neutral, meaning one of read, write, delete or run followed by its object, so no harness's own tool names reach the sheet.
   Label definitions must equal each task's grader labels plus labels4's reserved ones.
   The stop-cause column uses `labels4.STOPS`.
   `--out` inside the study folder is refused.
   Tests: K1 (every hidden field of a frame set to a sentinel, none reaching items or sheet), K2, K3, K3R (the real graders), K4, K5 (golden sheet), K6, K7.
3. `labelling/agreement.py`: the agreement table.
   It has one row per (arm, harness, model, task) and never rows across them.
   `pool_problems` refuses an unnamed row, a repeated key, or a row holding another row's take, and `render` refuses any such rows.
   Each row prints:
   - agreeing x of n, with `stats.bound`'s exact bounds;
   - the figure carried back to the frame: each stratum weighted by its frame size, with Bonferroni-level Clopper-Pearson bounds carried back by the same weights, or "a stratum unsampled" with no figure;
   - the confusion matrix of grader label, Javier's label and his stop cause.

   `--check` re-derives every number from `labels.json` and compares AGREEMENT.md byte for byte.
   It also requires the labels to be committed exactly once and unchanged on disk, and refuses a shallow clone.
   `--unmeasured` prints `grader agreement unmeasured` and nothing else.
   Tests: G1-G8, G6R (a real temporary repository), L1, X1, N1.
4. `tests/test_labelling.py`, `COPIED.d/w11d-labelling-tools.json` (six new files), `checks.d/w11d-labelling-tools.txt` (the tests, the witnesses, `sample.py --check`, `agreement.py --check`).

## Evidence (Mac, each run behind `mac_slot.py light-ok` and `timeout -s INT 120`, /usr/local/bin/python3.13)

- **Red first** (`b9436d88`, no `labelling/` code): 68 run, 65 failures, 0 errors, exit 1.
  The 3 that passed are the lane-file tests, which read this commit's own fragment and checks file.
- **Red again** (`f4c6c693`, the grown tests, with `labelling/` held outside the tree): 74 run, 71 failures, 0 errors, exit 1.
  The same 3 lane-file tests passed.
- **Green** (`dfe33600` plus the G4 fold): 74 run, OK, exit 0.
- **Witnesses**: 34 of 34 red, each by its own bound check's assertion (exit 0).
  The bound check is in brackets.
  - The brief's six:
    - model-name-in-sheet (K1);
    - model-name-in-sheet-unguarded (K1, with the leak check off: the sentinel scan itself sees the model in the items and the sheet);
    - unseeded-draw (S1);
    - failures-not-oversampled (O1);
    - weights-dropped (G3);
    - pooled-row-unlabelled (G4);
    - check-passes-edited-labels (G5).
  - sample.py:
    - disagree-not-oversampled (O1);
    - seed-unchecked (D1);
    - strata-unpinned (D1);
    - harness-error-admitted (F1);
    - model-harness-unchecked (F1);
    - missing-model-admitted (F1);
    - binding-one-way (B1);
    - cap-ignored (A1);
    - sheet-order-unshuffled (S1);
    - frame-size-wrong (W1);
    - sample-check-uncompared (C1).
  - sheet.py:
    - take-id-as-sheet-id (K1);
    - mask-off (K2);
    - mask-case-sensitive (K2);
    - take-ids-unhidden (K2);
    - leak-check-off (K6);
    - item-keys-unchecked (K5);
    - defs-label-subset (K3);
    - out-in-study-admitted (K6).
  - agreement.py:
    - bonferroni-dropped (G3);
    - pool-check-off (G4);
    - pool-take-unchecked (G4);
    - history-unchecked (G5);
    - history-shallow-admitted (G6);
    - unmeasured-words (G7);
    - label-off-definitions (G1);
    - unlabelled-admitted (G1).
- **Generated mutation sweep** (`--generated-mutants --shard i/40`), sampled on the Mac.
  - The sweep generates 1664 mutants over the three files.
    76 message-text strings inside `raise` statements are skipped by the stated rule.
  - Sampled on the final code: shards 1, 2, 6, 9, 10, 13, 14, 17, 18, 22, 26, 29, 30, 33, 34, 35 and 38 of 40, about 700 mutants, all killed or listed EQUIVALENT.
    The two survivors found there were killed by test folds before this report: a tuple of models (shard 18) and the "a stratum unsampled" words (shard 29).
    Each was confirmed killed by a targeted run.
  - Sampled earlier on code since folded: shards 3, 5, 7, 11, 15, 19, 21, 23, 25, 27, 31, 37 and 39 of 40.
    Every survivor found there was folded: CLI paths, `--help` descriptions, neutral actions, list and tuple shapes, a quota of one, the `split` loop, `design_pin`, and labels with no sample.
  - EQUIVALENT holds 27 entries:
    - 24 import-plumbing entries (the `__future__` import and the sys.path loop of each file), each confirmed surviving by a targeted run;
    - 3 identical-mutant entries (`return None` written as `return None`).
  - Each mutant runs against a 30-second clock, so a loop that never ends is a kill and never hangs the sweep.
  - The whole sweep is athena's.
- **Gates** (exit 0 each):
  - `copy_manifest.py --check` (301 files, 48 fragments);
  - `build_draft.py --check`;
  - `freeze.py --check` (301 owned paths);
  - `walk_register.py --check` (0 walks);
  - `lint_language.py evals/gap-study-4/` clean (92 inputs, 23 excused on record, none added);
  - `lint_pooling.py evals/gap-study-4/` clean (92 files);
  - `lint_language`/`lint_pooling --commits-since f14ab57b` clean (3 commits);
  - `sample.py --check` and `agreement.py --check` exit 0 with their "nothing yet" lines, which are not a pass on data.
- **Not run on the Mac** (rule): `test_round4.py`, the whole `test_scaffold.py`, `test_pipeline.py`, `test_box_integration.py`, the whole generated sweep.

## Ownership

Six new files, all claimed in `COPIED.d/w11d-labelling-tools.json`.
No file of another lane was edited.
None of drive.py, walk_runner.py, check_take.py, run.py, walk_register.py, mode_binding.py, rehearsals/, prereg-draft.json or build_draft.py was touched.

## Open questions (each with a proposed answer; none blocks the merge)

- **Q-w11d-1: where the freeze pins the design.**
  sample.py reads `prereg.json`'s `labelling_design`, but build_draft.py, which this lane may not touch, does not write it yet.
  Proposed: a later build_draft slice adds `labelling_design`, copying `sample.PROPOSED` (seed 20261012, about_n 80, factors 3 and 3, the six strata) and the draft's `harness_models`.
  The freeze then pins it, and its sha256 is the one `--pin` prints.
  The seed was chosen before any take existed.
- **Q-w11d-2: who writes the frame's `readers` and the post-probe content.**
  Nothing in round 4 records yet whether the access log and the tool-call reader agree for a take, and nothing renders a take's post-probe text and actions in the neutral format.
  Proposed: one CP8 slice reads each take folder with `transcript_view` and the end-state Evidence's watcher log.
  It would write `frame.json` (the record with its `readers`) and the post-probe content, with actions mapped to read, write, delete or run.
  sheet.py refuses any other action shape, so a harness's tool names cannot leak through.
- **Q-w11d-3: where the sheet lives.**
  The sheet holds agent text, which is a record and not the study's prose, so it would trip lint_language if kept in the study folder.
  Proposed: it is written outside the study folder (the CLI refuses an `--out` inside it), and only `labels.json` and AGREEMENT.md are committed.
- **Q-w11d-4: the brief says agreement "per task"; the orchestrator's added rule says never pool across models or arms.**
  Built: one row per task inside each (arm, harness, model), with no row, line or figure across them.
  At about 80 takes over 7 models and 9 tasks, most rows will hold 1 to 3 labelled takes, and many will print "a stratum unsampled" in place of the carried-back figure.
  Proposed: publish it as built (every row is exact and labelled).
  Any per-task figure across models would be a new, pre-registered descriptive line under Javier's word, not this table.
- **Q-w11d-5: a stop the ledger decides.**
  The label definitions include labels4's reserved labels (did-not-reach, asked-to-proceed, timed-out, aborted), so Javier can label a take that stopped.
  His stop cause is printed in the confusion matrix but is not scored.
  Proposed: keep it descriptive in round 4.

## Review

One fresh opus-medium round on construction, per the brief; to be assigned by glitch-2f.

RESUME HERE: review round 1 on `gap4/w11d-labelling-tools` (head after this report's commit), then fold.
Athena module list:
- `python3 -B -W ignore evals/gap-study-4/tests/test_labelling.py`
- `python3 -B -W ignore evals/gap-study-4/tests/test_labelling.py --witnesses`
- `python3 -B -W ignore evals/gap-study-4/tests/test_labelling.py --generated-mutants` (whole; or `--shard i/n` over n workers)
- `evals/gap-study-4/test_round4.py` (the battery, which discovers test_labelling)
- `evals/gap-study-4/tests/test_scaffold.py` (whole)
- the gates: `copy_manifest.py --check`, `build_draft.py --check`, `freeze.py --check`, `walk_register.py --check`, `lint_language.py evals/gap-study-4/`, `lint_pooling.py evals/gap-study-4/`, `labelling/sample.py --check`, `labelling/agreement.py --check`
