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

## Review round 1 fold (ruling w11d-R1-fold), Mon 12 Oct 2026 19:03 EDT (`date`)

Review: `lane-reports/w11d-labelling-tools-review-r1.md` (78e57de3), CHANGES, 2 MAJOR, 5 MINOR, every finding folded.
Correction to the report above: the sweep's skipped message-text strings were 79 at `bc0f0c0c`, not 76 (the reviewer's count, R1-7); at the fold head the count is 81.

- **R1-1 MAJOR.**
  - With no labels.json, `agreement.py --check` now fails while AGREEMENT.md stands, and fails while any commit in `git log --full-history` ever touched labels.json (`gone_problems`); a shallow clone refuses.
  - `sample.py --check` fails when sample.json stands with nothing to derive it from.
  - Tests: G5 (the no-labels case is now a refusal while the page stands; then committed-and-deleted; then shallow), G6R (a real repository whose labels were deleted after their commit), C1 (a stray sample).
  - Witnesses: page-without-labels-admitted, deleted-labels-admitted, gone-shallow-admitted, stray-sample-admitted.
- **R1-2 MAJOR.**
  - `sheet.hidden_set` builds the hidden set from the design's own ids.
    Each whole id is matched with -, _, . and a space interchangeable.
    Every alphabetic part of three or more letters of a model id is matched as a word (sol, luna, flash, lite, haiku, opus, sonnet, gpt, claude, gemini).
    The vendor and harness names stay.
  - `leak_problems` refuses a version number after the mask and the mask beside another id part.
  - On prereg-draft's real harness_models, the reviewer's four strings now give:
    - "I am GPT-6.1 Sol, running in Codex CLI" is masked whole: "I am [hidden], running in [hidden] CLI";
    - "As Gemini 3.5 Flash-Lite I stop here" is masked whole: "As [hidden] I stop here";
    - "Claude Haiku 4.5 here" is refused (a version after the mask, and the id part 4 beside it);
    - "I am Luna" becomes "I am [hidden]".
  - "a solution, flashing, literally" stays untouched.
  - Witnesses: id-parts-unhidden, id-separators-strict, version-after-mask-admitted, residual-neighbour-admitted.
- **R1-3.**
  - `HARNESS_WORDS` per harness: Claude Code's are derived from `transcript_view.CC_TOOLS` plus the names its reader has not met; Codex's and Gemini's are copied from lanes w11a and w11b, whose tables are not on this base (Q-w11d-6 below).
  - Any of them in an action is refused.
  - In text, the ones no plain sentence uses are refused: an underscore, a dot or a CamelCase name, such as update_plan, AGENTS.md or TodoWrite.
  - The docstring names the CP8 reader's acceptance test: write_sheet over every sampled take, with no refusal.
  - K4 has one case per harness, plus neutral actions that share a tool's spelling.
  - Witness: harness-words-admitted.
- **R1-4.**
  - `inside_study` compares real paths, with normcase and casefold, over the whole study.
  - K6 tries `--out` in labelling/, in the study root, deeper in the study, in swapped case, in upper case and at the study itself.
  - A sibling folder and the parent are not inside.
  - Witnesses: out-guard-labelling-only (the reviewer's `_HERE` mutant) and out-guard-case-sensitive.
- **R1-5.** G4 adds a row holding a take of its own model's other task. Witness: pool-row-task-unchecked.
- **R1-6.** G9 adds rows of one take, with the exact bounds pinned as literals: 1 of 1 is 0.025 to 1.000, and 0 of 1 is 0.000 to 0.975. Witness: one-take-bounds-widened.
- **R1-7.** G6 adds a failing `git show` on an empty file, killing `bool-drop#0` of `rc != 0 or blob != disk`.
- **Residual: rows that are missing.** Every frame cell the draw left empty prints "unsampled: no take drawn" and no figure (G9). Witness: unsampled-cells-dropped.
- **Residual: blindness by procedure.** The sheet docstring now says it, and this report says it for the CP8 brief: whoever runs sheet.py is not the labeller, and the labeller never opens sample.json or the --contents file.

**Evidence (Mac, behind light-ok, `timeout -s INT 120`):**
- Red first, `60b114bf` against the reviewed code: 87 run, 28 failures by assertion, 0 errors.
- Green on the fold head: 89 run, OK.
- Witnesses: 48 of 48 red.
- Gates and both lints: exit 0, unchanged counts.
- Sweep, sampled only (the Mac reached load 57; glitch-2f's word):
  - shards 4, 12, 20, 28, 36 and 40 of 40 on the fold code; 1913 mutants generated, 81 message strings skipped by rule;
  - two survivors were killed by test cases and confirmed by targeted runs: shard 40, `return out + [...]` after a failing `git log` in gone_problems (a G6 case); shard 28, the undrawn stratum's agreeing default (G3 now checks each stratum's agreeing count);
  - EQUIVALENT was regenerated by targeted runs: 24 import-plumbing and 3 identical `return None` entries, at their new lines.
- Test expectations adjusted after the red run: a few K2 expected leak lists, now the code's truthful output.
  The separator-insensitive id match masks two of the reviewer's strings whole, and a digit beside the mask reports both the version rule and the id-part rule.

**Q-w11d-6 (new): the Codex and Gemini tool-name lists.**
- They are copied from w11a and w11b's tables, which are not on this base.
- Proposed: at the merge after waves 10 and 11, HARNESS_WORDS reads `transcript_gemini.GEMINI_TOOLS` and Codex's item and tool names from their modules, with a test that every table name is in the list.
- CLAUDE.md is refused in actions per the ruling, although D8:287 makes it every arm's workspace instruction file (in text it is masked as a vendor word anyway).

RESUME HERE: review round 2 on `gap4/w11d-labelling-tools` (this commit), then the whole sweep and the athena module list above.

## Review round 2 fold (ruling w11d-R2-fold), Mon 12 Oct 2026 20:00 EDT (`date`)

Review: round 2 in `lane-reports/w11d-labelling-tools-review-r1.md` (19a87790), CHANGES, 1 MAJOR, 3 MINOR.
The ruling replaced the separator-list approach, and every item is folded.

- **R2-1 MAJOR: the token road.**
  `sheet.tokens` reads the content as tokens over the original character positions.
  Each character is NFKC-normalised and casefolded; every character that is not a letter or a digit is a separator (every Unicode dash and space, punctuation, line breaks); and letters and digits are split apart.
  `hidden_set` holds token sequences:
  - every vendor word, harness name, model id and take id, whole;
  - every part of three or more characters of a design id or harness name;
  - every design version wherever it stands (`versions()`: each digit run of a model id and its stretches of two or more, that is 5 5, 4 5 20251001, 4 5, 5 20251001, 6 1, 6, 3 8, 3 5);
  - the furniture tokens cli, entrypoint and toml.

  `mask` replaces each sequence over its original span.
  `leak_problems` is the backstop on the token stream: any hidden sequence left, a short id part beside a mark, or a harness word refuses the sheet.
  The reviewer's strings are each masked whole and then pass the backstop, and each raw string is refused: U+2011, U+2010, NBSP, en and em dashes, full-width forms, "v4.5", "Haiku: 4.5", "I am Haiku, version 4.5", "Sonnet (5.5)", "Opus\n5.5", and ids split across lines.
  Ordinary words and numbers ("solution", "16 files", "4 cats", "step 45") are untouched.
  Over-masking is the price: every lone "6" is masked (gpt-6-luna's version), and so is the word "code" (from claude-code).
- **Residual: "a version on its own".** This is closed by masking each design version wherever it stands ("I'm version 4.5" becomes "I'm version [hidden]").
- **Residual: furniture.**
  "codex-cli 0.144" becomes "[hidden]-[hidden] 0.144"; "~/.codex/config.toml" becomes "~/.[hidden]/config.[hidden]"; "CODEX_ENTRYPOINT" becomes "[hidden]_[hidden]"; "Gemini CLI" becomes "[hidden] [hidden]".
  A harness's version string ("0.144") and its home-folder layout are named in the docstring as the CP8 reader's acceptance test (Q-w11d-2).
- **R2-2.** K4 refuses "run <w>" for every word of every list, and pins each list literally (a renamed entry, such as the sweep's 'WebSearch', now fails). `harness_word` returns the `any(...)`.
- **R2-3.** G9 runs on a frame whose m-gamma task-two cell holds five all-right takes, which about_n 4 leaves undrawn. The rows must equal every frame cell. The reviewer's `verdict == "wrong"` cells mutant is a witness (cells-only-failed).
- **R2-4.** K2 refuses a short id part beside the mask ("m [hidden]", "[hidden]-M", "I'm [hidden]"), and K6 refuses an `--out` that reaches labelling/ through a symlink (witness out-guard-abspath).

**Evidence (Mac, light-ok before each batch, `timeout -s INT 120`):**
- Red first, `99ae098d` against 5958190f: 95 run, 14 failures by assertion, 0 errors. K4, G9 and K6 passed there, because they kill reviewer mutants and not code defects.
- After the red run, three test expectations were corrected, each a test error:
  - "codex-cli 0.144" masks to "[hidden]-[hidden] 0.144" (two spans), not "[hidden] 0.144";
  - the U+2011 witness compares against U+2010, because NFKC maps U+2011 to U+2010;
  - the token code was restructured to remove equivalent mutants (`tokens` without start and end, `versions` via groupby, no `discard`, no plain copy), with tests added that kill the survivors: bracketed non-marks, the date part, the exact version set, the harness-word line and the pinned lists.
- Green: 95 run, OK.
- Witnesses: 54 of 54 red.
- Gates and both lints: exit 0 (301 files, 48 fragments).
- Sweep, samples only:
  - targeted runs over every new token-code line in sheet.py, all killed (101 mutants, after the folds above);
  - shards 7, 23 and 39 of 40 (2008 mutants generated, 81 message strings skipped), with shard 23's 'WebSearch' survivor killed by the pinned lists.
- EQUIVALENT was regenerated: 24 import-plumbing and 3 identical `return None` entries.

RESUME HERE: review round 3 on `gap4/w11d-labelling-tools` (this commit), then athena's whole sweep and module list.

## Review round 3 fold (ruling w11d-R3-fold), Mon 12 Oct 2026 20:27 EDT (`date`)

Review: round 3 in `lane-reports/w11d-labelling-tools-review-r1.md` (91538337), CHANGES, 1 MAJOR, 1 MINOR.
Every item is folded, and the fold touches nothing beyond them.

- **R3-1 MAJOR: a number beside a mark is refused again.**
  The tests-first commit of round 2 (`99ae098d`) had dropped this refusal, so I restored it.
  `leak_problems` refuses any digit token next to a mark in the token stream (only separators between them).
  K2 covers each of the reviewer's strings: "I am Gemini 3", "Gemini 3 Flash here", "I'm Claude 4", "Haiku 4", "I am Sonnet 5", "Claude Opus 5", "Gemini 3.x" and "Gemini 3-series".
  It also covers "codex-cli 0.144", which is now refused rather than passed.
  Numbers away from a mark stay untouched ("[hidden] has 16 files", "4 cats and a [hidden] here").
  Witness: number-beside-mark-admitted.
- **R3-2.** `tokens` drops invisible format characters (Unicode category Cf) before grouping.
  "Hai" plus U+00AD, U+200D or U+200B plus "ku", and "Gem" plus U+2060 plus "ini", are each masked whole, and each raw string is refused.
  Witness: format-characters-kept.
- **The fence escape.** The text and the actions each sit in a code fence one backtick longer than any backtick run in them (`fence(*texts)`).
  So a take whose text holds ``` cannot close its fence, and an action such as "read &#72;aiku" shows as written.
  K5 tests a text holding ``` and a five-backtick run, actions with an entity and markup, and an action holding a four-backtick run.
  The golden sheet's sha changed by design, because actions are now fenced.
  Witnesses: fence-fixed, actions-unfenced.
- **Residuals for Javier**, now named in the sheet docstring: look-alike letters from other scripts (NFKC does not fold scripts; a TR39 confusables fold would, and that is his call), names spelled out letter by letter, number words ("four point five"), misspellings, and digits from other scripts.

**Evidence (Mac, light-ok before each batch, `timeout -s INT 120`):**
- Red first, `a64fe4f7` against 4be4269e: 99 run, 20 failures by assertion, 0 errors.
- Green: 99 run, OK.
- Witnesses: 58 of 58 red.
- Gates and both lints: exit 0.
- Mutants:
  - targeted runs over every changed line: all killed, after two restructurings (`fence` over several texts with no default; the free-text word filter as "underscore, or a case that is neither all lower nor capitalised", with the free-text list pinned in K4);
  - shards 11 and 31 of 40: shard 31's survivor (`w[1:]` to `w[2:]`) was removed by that restructuring;
  - EQUIVALENT was regenerated: 24 import-plumbing and 3 identical `return None` entries.

RESUME HERE: athena. Run the whole generated sweep and the module list above on this commit. There is no round 4 unless athena finds something.

## Before athena (glitch-2f's word), Mon 12 Oct 2026 20:29 EDT (`date`)

`checks.d/w11d-labelling-tools.txt` now carries the generated sweep as 16 shard lines (`--generated-mutants --shard i/16`).
That is about 128 mutants each of 2037, so every line stays well under run_checks' per-line limit (TIMEOUT_S, 3600 s).
The lines beside them are the whole module, `--witnesses`, `sample.py --check` and `agreement.py --check`, 20 lines in all.
`run_checks.file_problems()` is empty and `commands()` reads all 20.
The lane-file test pins the new list.
Tests: 99 run, OK.
Gates and lints: exit 0.

RESUME HERE: athena on this commit (athena_suite runs the 20 lines).
