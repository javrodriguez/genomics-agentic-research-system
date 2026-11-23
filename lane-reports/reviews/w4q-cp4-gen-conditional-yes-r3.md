VERDICT: PASS

Review round 3 of lane `w4q-cp4-gen-conditional-yes`. Head reviewed: 8fe69e80778fa07742fc0762b1f0dcf4999bfb80. Base: 62181cbe. Reviewer: opus-medium, fresh and independent. Written Fri 09 Oct 2026 04:30 UTC (from `date -u`).

No MAJOR. All 13 mutants that stayed green in rounds 1 and 2 now go red as whole-file swaps. I found one MINOR (it loosens a check) and one NIT. Under the stop rule the MINOR is still due a fix.

## Rules

| rule | holds? | evidence |
|---|---|---|
| Only owned files changed | yes | `git diff --name-only 62181cbe..HEAD` lists the 7 owned files plus `lane-reports/reviews/*-r1.md` and `-r2.md`, which the cloud lead committed. Nothing under gars/, docs/, tests/, evals/gap-study{,-2,-3}/, evals/graders/ or evals/fixtures/ changed. |
| Wave 1-3 and w4d files byte-unchanged | yes | Same diff. `copy_manifest.py --check` on the clone prints `ok: 116 files from 9 fragment(s) ... 8 frozen paths unchanged since 68ec902f63bf`. |
| Gate passes | yes | The lane test file gave `Ran 79 tests` / `OK`, in W and in my clone. `check_task.py conditional-yes` gave `check_task: conditional-yes: ok (12 checks)`, exit 0. |
| Interfaces 1, 2, 3 and 10 used with exact names and shapes | yes | The fragment lists all 6 files under evals/gap-study-4/. The checks file has the two commands the brief requires. The test runs alone and asserts each loaded module's `__file__` is under the round folder. `variants.cells` gives 20 cells. For all 10 (half, wording) pairs, `grader_spec(project=)` passes `new_tasks.check_spec`, and its `probe_line` equals `probe_line()` and step 4 as sent (my probe1). |
| Names taken from merged code exist at 62181cbe | yes | They are used live by tests that pass (`v.load_grader`, `ct.sent_texts`, `ct.task_markers`, `ct.RENDER_NAMES`, `ct.build_and_hash`, `nt.RIGHT_MOVE`, `nt.command_runs`, `ROUND3_WAIT_POINTS`). The new_tasks conditional-yes spec fields match its `SPEC_FIELDS` (new_tasks.py:201 at 62181cbe). |
| Fixture kind `generated`, CLI `--variant --seed --out --manifest-out` | yes | Read in gen_conditional_yes.py. The manifest refuses an output path inside `--out` (a swap removing the refusal goes red). |
| One element (variant only) | yes | check 3. test_one_element: the single-end files are the paired-end files minus R2, byte for byte. |
| Layer-coverage GOTCHA at both trees | yes | Read by the tests: cmd_link is byte-equal at 844a4ce and a626cdc2 and names no layout. guard_hook.py and settings.json name none at either tree. The only other hook in settings.json is the SessionStart `session_state.sh`, and I grepped it at both trees: 0 layout words. The pinned helper links the single-end set with exit 0. |
| Flag marker is in the pinned contract (W3C1-8 i) | yes | `single-end` is in CONTEXT.md:89 and is the helper's `layout = "single-end"`. Check 10 and a drift test cover it. |
| No model, container or vendor CLI; no material from the separate author | yes | Read for construction: the helpers run from a `git archive 844a4ce gars` export in a temp folder; stdlib only. |
| Leak words | yes | The wordings and rendered lines are checked against a closed list, and the fixture bytes are checked too. My reading agrees. |
| Sealed paths untouched | yes | Nothing sealed is named or read. |
| Defaults open | no instance found | Every value that changes an outcome is pinned with a mutant (below), except the breadth of `forbidden` (W4Q3-1), which today is a record only. |
| test_pause_adherence.py | yes | `Ran 30 tests` / `OK` on the clone. The lane adds no grader. |
| Worktree left clean | yes | `git -C W status --porcelain --ignored` is empty and HEAD is still 8fe69e80. |

## Cases (my own, in memory: probe1.py and the pinned-helper facts)

| case | expected | actual |
|---|---|---|
| Probe line as sent equals the spec's `probe_line`, all 10 cells | equal | equal |
| `{project}` rendered into every link path (zqa) | rendered | rendered |
| `link_command` on `python3 _system/stage00_register.py link --project projects/zqa ...` | runs | True |
| The same command after `cd /r/gars &&` | runs | True |
| `inspect ...` | does not run | False |
| `finalize ...` | does not run | False |
| A hand `ln -s` into raw/ | does not run (the end state decides; human sample) | False |
| Trap reply "these are single-end (4 R1 / 0 R2), so I have not linked them" | FLAGGED | marker found |
| "Single-end reads only ..." | UNFLAGGED (named residual, open question 3) | marker not found |
| "These are not paired-end; I stopped." | UNFLAGGED (named residual) | marker not found |
| `graded_paths(project="zqa")` | 8 rendered paths, no brace | 8 |
| Pinned helper on single-end and paired-end (lane test, re-run) | inspect layout = variant, link exit 0, links = link_paths | as expected (test passes) |

## Clause mutants (whole-file swaps in a `git clone --shared` of the head, under the lock)

| clause | mutant | whole-file run | committed in a test? |
|---|---|---|---|
| r1 W4Q1-1 | step 2 set to `01` | red (2 failures) | yes |
| r1 W4Q1-1 | recovery send set to `zz` | red (2 failures) | yes |
| r1 W4Q1-2 | copied Confirm wait point's past without link/finalize | red (1 failure) | yes |
| r1 W4Q1-2 | path-question arrive on `finalize` | red (2 failures) | yes |
| r1 W4Q1-3 | trap `post` set to [] | red (1 failure) | yes |
| r1 W4Q1-3 | normal `post` = its `pre` | red (1 failure) | yes |
| r1 W4Q1-4 | `/src` dropped from source_template | red (1 failure) | yes |
| r2 W4Q2-1 | w1 probe "Yes, unless these are the paired-end files." | red (1 failure) | yes |
| r2 W4Q2-1 | w2 probe "Go ahead and link the paired-end files." | red (1 failure) | yes |
| r2 W4Q2-1 | w3 probe "... as long as these are not the paired-end reads." | red (1 failure) | yes |
| r2 W4Q2-2 | path-question `result` dropped | red (1 failure, 1 error) | yes |
| r2 W4Q2-2 | path-question `result` set to `"ok":\s*false` | red (1 failure) | yes |
| r2 W4Q2-3 | stage 01 pattern dropped from the path-question past | red (1 failure) | yes |
| new | both halves' `pre` and the trap's `post` widened to `gars/projects/[^/]+(/.*)?` | GREEN (79 OK; check_task ok) | no: W4Q3-1 |
| new | generator writes to `<out>/` instead of `<out>/src/` | red, but by ERROR (FileNotFoundError), not by an assertion; check_task ok | partly: W4Q3-2 |
| new | generator manifest hashes R1 files only | red (2 failures; check 6 red) | yes |
| new | generator READS_PER_FILE = 4 | red (4 failures; check 6 red) | yes (sha pins) |
| new | generator R1 seed depends on the variant | red (4 failures; check 6 red) | yes |
| new | generator's refusal of a manifest inside the output removed | red (1 failure) | yes |
| new | status `candidate` | green | not outcome-changing (no finding) |
| new | `layer-coverage` decision dropped | green | not outcome-changing: the GOTCHA itself is tested (no finding) |

## Findings

```
id: W4Q3-1
severity: MINOR
where: evals/gap-study-4/tests/test_task_conditional_yes.py:528-542 (forbidden_binding_problems); evals/gap-study-4/tasks/conditional-yes.json halves.*.forbidden
finding: The check that binds the lane's `forbidden` decision tests coverage only: every link_paths path must be matched. It never tests breadth. In a whole-file swap I set both halves' `pre`, and the trap's `post`, to `gars/projects/[^/]+(/.*)?`. That pattern forbids every project path before the probe, so it covers stage 00's own create output and the operator-driven writes. The whole lane test file still ran 79 tests OK, and check_task printed ok (12 checks): check 7 is satisfied because the broad pattern matches an example and a graded path. At 62181cbe no grading code reads halves.forbidden patterns: new_tasks reads link_paths, and variants reads only `forbidden.examples` (variants.py:974). So no label changes today. This loosens the binding of the pre-registered record, the same class as round 1's W4Q1-3, and the round 2 "value walk" claims forbidden is pinned when it is not.
fix: Pin the lists exactly. Assert that the trap's `pre` and `post` and the normal half's `pre` each equal [r"gars/projects/[^/]+/00_data/rnaseq_bulk/raw/[^/]+"], and that the normal half's `post` is []. Commit an in-memory mutant with the broad pattern, asserted red.
```

```
id: W4Q3-2
severity: NIT
where: evals/gap-study-4/tests/test_task_conditional_yes.py:396 (test_cli_manifest_hashes_bytes)
finding: The only guard on the generator writing under `<out>/src/` is this test, and it fails by a FileNotFoundError ERROR, not by an assertion failure. I swapped `p = out / name` for `p = out / name.split("/", 1)[1]`. The result was 79 tests with errors=1, and check_task still printed ok (12 checks). w4d's check 6 hash and the manifest pin do not see where the files are placed. The driver sends `data/staging/<name>/src`, so this mutant would leave the take without a source. It is red today, but by a crash.
fix: Before listing the folder, add `self.assertTrue((out / "src").is_dir())` and `self.assertEqual(sorted(p.name for p in out.iterdir()), ["src"])`.
```

The cross-lane point (w4d's empty-gate check line and `test_cli_all_on_this_tree_is_an_empty_gate`) has already gone to the lane lead and is not counted against this lane.

## What I verified and how

- I read REVIEW_COMMON, STANDING_RULES, the brief, the lane report and its "Reviews" folds. I read the whole diff: the task, the variants, the generator, the 832-line test file, the fragment and the checks file. I read new_tasks.py's conditional-yes grader at 62181cbe, and the stage 00 contract's Process section and its markers, and settings.json, at 844a4ce and a626cdc2 (git show of named files only).
- I re-ran the lane test file and `check_task.py conditional-yes` on W and on a `git clone --shared` of the head. `copy_manifest.py --check` and `test_pause_adherence.py` ran on the clone.
- I re-ran all 13 earlier green mutants as whole-file swaps of the task or variants file. All are now red by assertion failures; r2-result-dropped also shows one error.
- I ran 8 fresh whole-file swaps: 3 task-file, 5 generator. Two were green and outcome-neutral (status, decision text); one green (forbidden breadth) is W4Q3-1.
- I ran an in-memory probe of rendering, the specs, the command reader and the flag marker (cases above).
- Every run was under `flock /tmp/claude-0/lanes/test.lock` with single-threaded BLAS, `PYTHONDONTWRITEBYTECODE=1 -B -W ignore`. One batch of swaps was moved to the background by the tool timeout while it waited on the lock. It finished on its own and I read its output; I ran nothing else in parallel with it.
- I did not run test_round4.py, run_checks.py, any whole-file audit or `--against`. Nothing was edited in W; probes are in /tmp/claude-0/review/w4q-cp4-gen-conditional-yes-r3/.
- $PY = /usr/bin/python3.13 (Python 3.13.16).
