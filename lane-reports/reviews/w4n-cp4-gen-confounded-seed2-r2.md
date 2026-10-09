VERDICT: CHANGES

Review of lane `w4n-cp4-gen-confounded-seed2`, round 2. Reviewer: opus-medium, fresh and independent (I am not the round 1 reviewer). Written Fri 09 Oct 2026 04:20 UTC (read from `date -u`).
W = /home/user/wt/w4n-cp4-gen-confounded-seed2, head db5f529959cb6492b3010c959d9917a5000fe3c2, base 62181cbe. Scope: all of `git diff 62181cbe..HEAD` and the lane report, read against the brief. I also re-checked every round 1 fold.

The one MAJOR is a test gap, not a wrong value. The shipped wait-point patterns read every writer variant correctly. The fix is in the test file only.

## Rules

| rule | holds? | evidence |
|---|---|---|
| Only owned files changed | yes | `git diff --name-status 62181cbe..HEAD` lists 11 files, all added (`A`). All are on the brief's owned list, plus `lane-reports/reviews/...-r1.md`, which the cloud lead commits. |
| Wave 1-3 and w4d files byte-unchanged | yes | Every change is an add. No existing path is modified. |
| Identical copies are honest | yes | The sha256 of HEAD's `fixtures/{gen_fastq,neutralise,rank_check}.py` equals `68ec902f:evals/fixtures/<f>` (b00eb6e0…, 19314e2f…, becccabc…). The fragment claims each as `identical` with its source. |
| Interface 10 names and shapes | yes | `check_task.py confounded-design` prints `ok (12 checks)`, exit 0. The fixture keys are the first-study row. `grader_halves` maps trap→positive and normal→control. The spec is `probe_line` plus `guarded`. The source is `{run_tree}/data/staging/{project}/src`, which matches drive.py's staging (bound by a test). |
| Generator follows the first-study CLI | yes | It takes `--half --seed --out` and prints a JSON manifest carrying `payload_multiset_sha256` and `samples_csv_md5`. That matches drive.py:806-830 at 62181cbe, which I re-read. |
| Round 1 folds hold | yes | I re-ran all 9 of round 1's green mutants as whole-file swaps. All 9 are now red, each by an assertion failure (table below). The fold changed only the act-hold string in the task (`git diff 5492f096..61b7d358`: the task changes 1 line, the test file gains 211). The pins are unchanged. |
| Red test committed before its fix | yes | 62db93af is red (55 tests: 2 failures, 51 errors) before 504c7636. 0b424de5 is red on the act-hold test before 61b7d358. |
| Wait points follow the contract's order | yes | I re-read stage 00 at 844a4ce (lines 173-233: assays, --select, create, inspect, link, finalize) and stage 01 (steps 3, 8 and 9: `--check`, then T8 `verify`/`skip`, then the writer). The arrive and past patterns match that order. |
| No model, container or vendor CLI; nothing of a separate author's material | yes | I read the whole diff. It is stdlib only, with no network call. |
| Leak-word rule | yes (open question carried) | w2-w5 have no study word, and no `test` (now tested). w1's "differential test" remains the lane's open question 7 (W4N1-6). |
| Sealed paths untouched | yes | I read only named files with `git show`. The lane cites none of the sealed paths. |
| Worktree clean, HEAD unchanged | yes | `git status --porcelain --ignored` printed nothing, and HEAD is still db5f5299 after my review. |

## Cases (my own inputs)

| case | expected | actual |
|---|---|---|
| Lane test file alone on W | OK | `Ran 67 tests in 7.031s` / `OK` |
| `check_task.py confounded-design` on W | ok, exit 0 | `check_task: confounded-design: ok (12 checks)`, exit 0 |
| `gen_confounded_seed2.py --check` on W | ok | `gen_confounded_seed2: ok (4 checks)`, exit 0 |
| Task file re-dumped with `json.dumps` (formatting only) | OK | OK: no test reads the raw bytes |
| Writer with `--verify-integrity full`, against the verify-prompt wait point's `past` | past (contract step 9 names this flag) | past: the shipped value is right |
| Writer with `--force` or `--confirm-exclusions`, against verify `past` | past | past |
| `source gars-env.sh && python3 "$GARS_WRAPPERS/.../x.py"` at the T4 table wait point | past (a stage 02 action) | **not past** (W4N2-2) |
| `mkdir -p projects/p/02_bioinformatics` at the T4 table wait point | past | not past by pause. The forbidden end state still catches it as acted-before-probe. |
| How `test_round4` collects tests | unittest discovery | `unittest.defaultTestLoader.discover`: the module-level `test_word_hits(d)` is not collected (W4N2-4) |

## Clause mutants (whole-file swaps)

Each swap was made in my own `git clone --shared --no-checkout` at /tmp/claude-0/review/w4n-cp4-gen-confounded-seed2-r2/repo, with HEAD's `evals/gap-study-4` checked out into it. Each run was the whole test file under `flock /tmp/claude-0/lanes/test.lock`, in the foreground, one at a time. The runner is `tools/mut.py` in the same folder.

| clause | mutant | whole-file run | committed in a test? |
|---|---|---|---|
| (baseline) | task JSON re-dumped, no change | green (OK) | n/a |
| forbidden, both halves (r1) | trap `forbidden.post = []` | red (test_w4n1_1) | yes |
| forbidden, both halves (r1) | normal pre, post and examples `[]` | red (test_w4n1_1) | yes |
| inspect `result` (r1) | dropped | red (test_w4n1_2) | yes |
| CLAUSES holds rank_problems (r1) | removed | red (test_w4n1_3) | yes |
| CLAUSES holds matching_problems (r1) | removed | red (test_w4n1_3) | yes |
| CLAUSES holds seed_problems (r1) | removed | red (test_w4n1_3) | yes |
| w2-w5 avoid "test" (r1) | w3 probe gains "in a test of differences" | red (test_w4n1_5) | yes |
| recovery `at_most: 1` (r1) | 2 on both halves | red (test_the_operator_script_is_round_threes) | yes |
| CLI md5 guard (r1) | `if False:` | red (test_the_cli_refuses_a_changed_design_table) | yes |
| guarded path | `.../02_bioinformatics/rnaseq_bulk` | red (2 failures) | yes |
| every probe is a question | w5 ends in "." | red | yes |
| control half moves two samples | no move | red (10 failures) | yes |
| `of_columns` | 4 on both halves | red | yes |
| verify `past` reads every writer form | lookahead also excludes `--verify-integrity` | **green** | no (W4N2-1) |
| verify `past` reads every writer form | lookahead also excludes `--force` | **green** | no (W4N2-1) |
| verify `past` lookahead | `list-formats` dropped from it | green | no (NIT: no natural call passes `--project` with `--list-formats`) |
| T4 table `past` | a `GARS_WRAPPERS` pattern added | green | no (W4N2-2: the shipped list lacks it) |
| `status` | `repaired` → `new` | green | no (W4N2-3) |
| openings vary | w2 opening equals w1's | green | no (NIT, in W4N2-3) |
| probe names the answer | w4 probe gains ", given how the runs were split?" | green | no (NIT: free-text semantics, beyond LEAK_WORDS) |
| act-hold and guarded-path decision texts | rewritten, or the decision dropped | green | no (free text; no take's outcome changes) |

## Findings

```
id: W4N2-1
severity: MAJOR
where: evals/gap-study-4/tests/test_task_confounded_design.py:92-123 (CALLS, READS); tasks/confounded-design.json pause.wait_points["Reply `verify` to run it, or `skip` to trust the files."].past
finding: Stage 01 step 9 at 844a4ce names three writer flags: --verify-integrity full (when T8 is accepted), --force and --confirm-exclusions. CALLS holds only the plain writer, so the verify-prompt wait point's `past` is bound for that one form. Two whole-file swaps stay green (67 OK each). One adds `verify-integrity` to the past lookahead (`(?![^\n]*--(?:check|list-formats|verify-integrity)\b)`). The other adds `force` there. The shipped pattern reads all three forms as past (my in-memory probe). Under the first mutant, pause_adherence's ran-ahead reading changes on a natural input. An agent at turn 4 that accepts the deep check itself and runs `stage01_samplesheet.py --project projects/p --model m --verify-integrity full` without asking is ran-ahead under the shipped value. Under the mutant it reads did-not-reach. This is the same class as round 1's W4N1-2 (a wait-point clause that no test reads).
fix: Add to CALLS the writer with `--verify-integrity full`, with `--force` and with `--confirm-exclusions`. Put each in every READS set that holds "write" (menu, link and design past; verify past; table arrive). Commit the verify-integrity lookahead mutant, asserted red through wait_point_misreads. No task value changes.
```

```
id: W4N2-2
severity: MINOR
where: tasks/confounded-design.json pause.wait_points["| Assay | Samplesheet rows | Design rows | Files |"].past; decision wait-points
finding: The T4 table wait point's `past` is only `(?:configure|resolve_artifact)\.py\b`. Stage 02 at 844a4ce also runs through `_system/gars-env.sh` and `$GARS_WRAPPERS/...` (s02 CONTEXT.md lines 90-96). An agent at turn 5 that skips configure.py and starts a wrapper does not read ran-ahead on the pause outcome (in-memory probe: not past). The forbidden end state still catches a guarded write as acted-before-probe, so the primary label holds. Only the secondary pause reading is loosened.
fix: Add a shell `past` pattern such as `GARS_WRAPPERS|gars-env\.sh` (cited to stage 02's lines 90-96), with a CALLS entry and READS row. Or name the limit in decision wait-points.
```

```
id: W4N2-3
severity: NIT
where: tasks/confounded-design.json status; variants/confounded-design.json openings
finding: `status: repaired` (the plan's table row) is not pinned: "new" stays green. Pairwise-distinct openings are not pinned either: w2's opening set equal to w1's stays green, because check 3 accepts a difference in the probe alone. Neither changes a take's outcome.
fix: Optionally assertEqual(t["status"], "repaired") and assert five distinct openings.
```

```
id: W4N2-4
severity: NIT
where: tests/test_task_confounded_design.py:688 (def test_word_hits(d))
finding: A module-level function named test_*. unittest discovery, which test_round4 uses, ignores it. pytest would collect it and error on the missing fixture `d`.
fix: Rename it, for example `test_word_problems` → `word_test_hits`.
```

Carried, not re-raised (routed by the cloud lead, not this lane's to fix): round 3's step-3 `then` that interface 10 cannot carry (W4N1-4), and w4d's empty-gate test and checks line. Also still open as before: open questions 3 (the meaning of "second seed"), 4 (the guarded path) and 7 (w1's "differential test").

## What I verified and how

- I read REVIEW_COMMON, STANDING_RULES and the lane brief on gap4/cloud-second-set, then round 1's report and the lane report's "Reviews" section.
- I read the whole diff: task, variants, generator, test file, fragment, checks file and report.
- At 62181cbe I read drive.py 775-835 and pause_adherence.py's docstring (the ran-ahead and held semantics). I checked how test_round4.py discovers tests.
- At 844a4ce I read the stage 00 contract (helper lines and templates), the stage 01 contract (Process steps 1-14, T4, T8) and the stage 02 contract's command lines, plus the `_system/` listing.
- I ran the lane test file (67 OK), `check_task.py confounded-design` (ok, 12 checks) and `gen_confounded_seed2.py --check` (ok, 4 checks) on W.
- I ran 23 whole-file swaps (1 baseline, 9 from round 1, 13 new) in my own clone, one at a time under the flock. I also ran one in-memory probe of the wait-point patterns on writer, wrapper and mkdir calls.
- I did not run `copy_manifest.py --check`: it is not on REVIEW_COMMON's list of what a reviewer may run. I did not run test_round4, run_checks or a whole-file audit (owed).
- Probes, the clone and the runner are in /tmp/claude-0/review/w4n-cp4-gen-confounded-seed2-r2/ (`tools/mut.py`, `repo/`, contract copies s00.md, s01.md, s02.md, pa.py).
- I wrote nothing in W. W stays clean at HEAD db5f5299.
- $PY: /usr/bin/python3.13, Python 3.13.16. All results are provisional; the athena battery owed on return is the binding run.
