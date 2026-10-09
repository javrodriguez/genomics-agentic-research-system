VERDICT: PASS

Lane `w4i-cp4-task-scope-read`, review round 3, by a fresh opus-medium reviewer. I did not write this lane and did not review rounds 1 or 2. Head bb4dd668eb62cc2cfef3d85cde1e807ed8acd786, base 62181cbe. Written Fri 09 Oct 2026 04:12 UTC (from `date`). No report file was written, because sub-agents may not write report files. My probes are in /tmp/claude-0/review/w4i-cp4-task-scope-read-r3/ (`probes/swap.py`, `base/`, `swap/`).

## Rules

| rule | holds? | evidence |
|---|---|---|
| Only owned files changed | yes | `git diff --stat 62181cbe..HEAD` lists 8 files: the 6 owned files, plus the r1 and r2 review copies that the cloud lead commits under REVIEW_COMMON |
| Wave 1-3 and w4d files byte-unchanged | yes | I limited the diff to these paths and it is empty: evals/gap-study{,-2,-3}, evals/graders, evals/fixtures, evals/gap-study-intervals, gars, docs, tests, .github, DEVELOPMENT.md, README.md, variants.py, check_task.py, gap-study-4/graders, gap-study-4/fixtures, and w4d's checks file |
| Task data unchanged by the folds | yes | `git diff 50334471..HEAD -- tasks variants` is empty. Every fold since round 1 adds a guard or a pin in the test file only |
| `check_task.py scope-read` | yes | `check_task: scope-read: ok (12 checks)`, rc 0 |
| Lane test file, run alone | yes | `Ran 39 tests in 1.913s` / `OK` |
| `test_pause_adherence.py` | yes | `Ran 30 tests in 1.841s` / `OK` |
| Interfaces 1-3, 6, 8, 9, 10 | yes | The grader is per-half with trap/normal. The spec fields are exactly scope_read's (`half`, `probe_line`, `wait_point`, `planted`, and `answer_rule` on the normal half only). The fixture is `generated` with exactly its kind's keys, plus `note`. Modules are loaded by path with `__file__` asserted. There are no skips. The fragment claims all 5 files under evals/gap-study-4/, and checks.d holds the two commands the shared rules name |
| Protocol reply `05` is still bulk RNA-seq at 844a4ce | yes | `stage00_register.py:129` numbers `sorted(catalog)`. `assay_stage_skill_map.md` gives atacseq_bulk, chipseq_bulk, cutandrun, methylseq, rnaseq_bulk, ..., so 05 is rnaseq_bulk |
| Markers in the pinned contract | yes | All four step and recovery markers are in `gars/00_initialize_project/CONTEXT.md` at 844a4ce (lines 263, 287, 301, 312) |
| Round 1 and round 2 folds hold | yes | Every mutant that round 1 or round 2 found green is red now in a whole-file swap (case table) |
| The canonical-sha256 whole-file pin is sound | yes | It hashes the parsed JSON (`json.dumps(sort_keys=True, ensure_ascii=False)`), which is exactly what `variants`/`check_task` load. A formatting-only rewrite (indent 4, every object's keys reversed) stays green. Every content edit I tried is red. See the pin judgment below |
| No model, container, vendor CLI or separate author's material | yes | None in the diff. The only builds are check_task's own, in temp folders |
| Leak-word rule | yes | The wordings hold none of the lane's list. `leak_grep.py` takes no path argument, as the lane reports |
| Sealed paths untouched | yes | I opened none, and the diff touches none |
| Worktree clean, HEAD unchanged | yes | `status --porcelain --ignored` is empty, and HEAD is bb4dd668 |

## Cases

Each case is a whole-file swap of `tasks/scope-read.json` and/or `variants/scope-read.json` in my own copy (`git archive HEAD evals/gap-study-4 evals/gap-study-2/prereg.json`, with GIT_DIR set to the mirror's common .git for the read-only `git show`). For each case I ran the WHOLE lane test file and then `check_task.py scope-read`, one at a time under the flock. check_task stays `ok (12 checks)` in every case. Each red result below comes from the lane's own test file, which is the point of its guards.

| case | expected | actual |
|---|---|---|
| baseline | green / ok | OK (39) / ok |
| formatting only (indent 4, keys reversed) | green, since the pin must not block a reformat | OK (39) / ok |
| r1: trap w1 `read qc/multiqc_report.txt ...` | red | red: no_path_in_wordings, pins_hold |
| r1: trap w2 `open src/qc/multiqc_report.txt ...` | red | red: no_path_in_wordings, pins_hold |
| r1: normal half forbids nothing | red | red: forbidden_both_halves, pins_hold |
| r1: trap forbidden.post = [] | red | red: forbidden_both_halves, pins_hold |
| r1: trap forbidden.pre = [] | red | red: forbidden_both_halves, pins_hold |
| r1: normal w4 `how many samples does the source hold?` | red | red: slots, normal_questions_pinned, pins_hold |
| r1: opening w2 names multiqc_report.txt | red | red: slots, pins_hold |
| r1/r2: trap w5 adds "though it is not needed" (green in rounds 1 and 2) | red | red: pins_hold |
| r2: normal w5 `Which FASTQ files will be linked?` (W4I2-1) | red | red: slots, normal_questions_pinned, pins_hold |
| r2: normal w3 `which files does the stage link first?` (W4I2-1) | red | red: same three |
| r2: normal w2 names "the MultiQC report" (W4I2-2) | red | red: slots, normal_questions_pinned, pins_hold |
| r2: normal w3 names "the MultiQC summary" (W4I2-2) | red | red: same |
| r2: normal w2 adds "the quality-control report" (W4I2-2) | red | red: same |
| r2: trap w1 backslash path `qc\multiqc_report.txt` (W4I2-3) | red | red: no_path_in_wordings, pins_hold |
| r2: trap w5 `Do not open multiqc_report.txt ...` (W4I2-3) | red | red: pins_hold |
| r2: recovery `at_most` dropped on step 1 (round 2 called green fine) | either | red: pins_hold (stricter, and harmless) |
| new: normal w4 `... do the originals stay where they are?` (asks the fate, no copy or move word) | red | red: slots, normal_questions_pinned, pins_hold |
| new: answer_rule `hedges` loosened to `\bzzz\b` | red | red: round2_binding, pins_hold |
| new: probe step line `{probe} Thanks.` on both halves | red | red: round2_binding, pins_hold |
| new: `seed_sensitive` false on both halves | red | red: seed_insensitive_check_6, pins_hold |
| new: one decision's text edited | red under the file pin only, by design | red: pins_hold only |

## Clause mutants

| clause | mutant | whole-file run | committed in a test? |
|---|---|---|---|
| check 1, five wordings | drop one | red (in memory, through the module) | yes |
| check 2, relative start | `data/...` in a trap slot | red | yes |
| check 3, slot once / texts differ / one fixture / markers before the probe | four mutants | red | yes |
| check 4, one act and one hold / grader labels | two mutants | red | yes |
| check 6, seed / pin / seed-sensitive | three mutants, plus the swap above | red | yes |
| check 7, unbound pattern / typed project / trap forbids nothing | three mutants | red | yes |
| check 8, exclusion hides a path / empty graded set | test table, and `task_graded_paths` patched to empty | red | yes (W4I2-4 fold) |
| check 9, `{source}` in the probe | `{probe} ({source})` | red | yes |
| check 10, marker text | wait_point altered | red | yes |
| lane W4I1-1, no path (`/` or `\`) in a wording | 6 mutants | red, and red in a swap | yes |
| lane W4I1-2, forbidden pinned on both halves | 4 mutants | red, and red in a swap | yes |
| lane W4I1-3 / W4I2-1, normal question pinned and asks the fate | 2 mutants, through both guards | red, and red in a swap | yes |
| lane W4I2-2, planted file named in words | 3 mutants | red, and red in a swap | yes |
| value walk, PINS | one generic mutant per pinned path | red under both value and file pin | yes |
| value walk, file pin | decision text, fixture note | red under the file pin | yes |

## The canonical-sha256 pin

The pin is sound.
- **What it reads.** It hashes the same parsed object that the runtime loads. So it catches every content change, and it ignores whitespace and key order (both checked by swap above).
- **No floats.** Neither file holds a float, so the hash does not depend on the interpreter.
- **Non-ASCII bytes.** The answer rule's `—` is hashed as UTF-8, the same way every time.

It blocks every content change, a legitimate one included, until `PINS`/`FIXTURE` and `FILE_SHA256` are updated in the same commit. Some examples:
- a freeze re-pin of `sha256` after a generator change;
- a w4d close that adds a schema key;
- a CP5 edit to a decision.

That is the tripwire the cloud lead asked for, not a wrong block:
- The failure prints the new hash (`hashes to X, not the pinned Y`), so the re-pin is mechanical.
- check 6 pins the same `sha256` on its own.
- A freeze that leaves the value equal (it is already round 2's published pin) changes nothing.

The only cost is that a later checkpoint editing `tasks/scope-read.json` must also edit this lane's test file. The test's docstring does not say so. That is NIT W4I3-1 below.

## Findings

```
id: W4I3-1
severity: NIT
where: evals/gap-study-4/tests/test_task_scope_read.py:27-28, 352-356 (FILE_SHA256 and its docstring line)
finding: The whole-file pin makes every later content change to the two task files red until the test's constants
  are updated. That includes a ruled one, such as a freeze re-pin of fixture.sha256 or a w4d schema change. This is
  by design, and the failure message prints the new hash. But nothing in the file tells a later checkpoint that it
  must re-pin here, or which constants move together (FIXTURE["sha256"], the PINS entry, FILE_SHA256). A later
  editor who meets the red test could read it as a regression in its own change.
fix: One docstring sentence: "A ruled change to either file updates PINS (or FIXTURE, or the wording tuples) and
  FILE_SHA256 in the same commit; the failure prints the new hash."
```

```
id: W4I3-2
severity: NIT
where: evals/gap-study-4/tests/test_task_scope_read.py:763-768 (test_free_text_held_by_file_pin)
finding: The test asserts value_pin_problems(t, doc) == [] after a decision edit, on the task as loaded from disk. So
  any on-disk deviation of a value pin also fails this test. 12 of my 22 swaps failed it alongside test_pins_hold,
  for example a trap-slot path. That gives a second, misleading failure name. It never makes anything green.
fix: Optional. Compute the baseline value_pin_problems(task, doc) first, and assert the decision edit adds nothing
  to it, instead of asserting it is empty.
```

Cross-lane, already routed to the lane lead and not charged here: w4d's checks.d `--all` empty-gate line (checks.d/w4d-cp4-variants.txt:5), and `test_variants.py::test_cli_all_on_this_tree_is_an_empty_gate`.

Named residuals that stay with the walk (CP6), as rounds 1 and 2 left them:
- w4's normal question ("what exactly ends up in the project?") invites the rule's sources-not-copied-or-moved concept less directly than the other four.
- The trap names the file only in words plus its file name (decision probe-names-no-source).

## What I verified and how

- I read REVIEW_COMMON.md, STANDING_RULES.md and the brief in full, with `git show gap4/cloud-second-set:<path>`.
- I read the round 2 report and the lane report with its Reviews section, and all of the diff's files: task, variants, fragment, checks file, and the whole test file.
- I read scope_read.py's docstring at 62181cbe, the stage 00 contract's marker lines and assay menu at 844a4ce, the stage00_register.py catalog numbering, and assay_stage_skill_map.md at 844a4ce.
- Gates ran in W, each alone under `flock /tmp/claude-0/lanes/test.lock` in the foreground, with single-threaded BLAS, `-B -W ignore` and PYTHONDONTWRITEBYTECODE=1:
  - the lane test file: 39 tests, OK;
  - `check_task.py scope-read`: ok (12 checks), rc 0;
  - `test_pause_adherence.py`: 30 tests, OK.
- Whole-file swaps: 22 swaps plus the baseline, in my own archived copy, one process at a time under the flock (the case table).
  - Every mutant that round 1 or round 2 found green is red now, so the folds hold.
  - A formatting-only rewrite stays green, so the pin does not over-block.
- Not run, by rule: the whole suite, test_round4.py, run_checks.py, copy_manifest.py --check (not on REVIEW_COMMON's list of runs for reviewers), --whole-file-audit and --against.
- At the end, `git -C W status --porcelain --ignored` was empty and HEAD was still bb4dd668.
- $PY = /usr/bin/python3.13 (Python 3.13.16). These results are provisional; the battery owed on return is the binding run.
