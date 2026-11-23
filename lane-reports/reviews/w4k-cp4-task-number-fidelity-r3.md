VERDICT: PASS

Lane `w4k-cp4-task-number-fidelity`, review round 3. Reviewer: opus-medium, cloud. Written Fri 9 Oct 2026, 04:11 UTC (read from `date`). Head reviewed: `a36e5d1619d3e0ab015a2307a49dee13231c0aae`. Base: `62181cbe`. Sub-agents cannot write report files, so this message is the whole report. The probes are in /tmp/claude-0/review/w4k-cp4-task-number-fidelity-r3/probes/ (driver: `mut.py`).

**Summary:** no MAJOR and no MINOR finding. Every fold from rounds 1 and 2 holds: all 20 earlier green mutants are now red when re-run as whole-file swaps. Of 9 new swaps, 4 stayed green, and none of them changes what a take does. One NIT is filed (W4K3-1).

## Rules

| rule | holds? | evidence |
|---|---|---|
| Only owned files changed | yes | `git diff --stat 62181cbe..HEAD` lists the 6 owned files plus `lane-reports/reviews/...-r1.md` and `-r2.md`, which the cloud lead committed as REVIEW_COMMON says to |
| Wave 1-3 and w4d files byte-unchanged | yes | the diff touches nothing else; `copy_manifest.py --check` gives `8 frozen paths unchanged since 68ec902f63bf`, exit 0 |
| `check_task.py number-fidelity` | yes | `check_task: number-fidelity: ok (12 checks)`, exit 0 |
| Lane test file alone | yes | `Ran 74 tests in 2.760s` / `OK`, exit 0 |
| `copy_manifest.py --check` | yes | `ok: 115 files from 9 fragment(s) ...: 44 identical and 5 edited ..., 66 new; 5 fixture builders byte-identical; 8 frozen paths unchanged`, exit 0 |
| `test_pause_adherence.py` | yes | `Ran 30 tests in 2.036s` / `OK` |
| Interface 1 (the fragment) | yes | all 5 files under `evals/gap-study-4/` are claimed `new`, each with a reason |
| Interface 2 (checks.d) | yes | exactly the two lines the shared rules give |
| Interface 3 (each test file runs alone, no skip) | yes | the file puts `evals/gap-study-4` on `sys.path` itself; no skip; it fails loudly in a shallow clone |
| Interface 8 (only the seam names a harness) | yes | no `claude-code` or `harness_types` in any lane file; the test builds events through `transcript_view`'s own kinds |
| Interface 10 names | yes | every `v.*` and `ct.*` name resolves at the base (the file runs green with `variants.py` and `check_task.py` untouched). Several are w4d internals outside the published API list (NIT W4K3-1) |
| Spec is exactly SPEC_FIELDS | yes | trap 8/4 against true 12/6, pushback 8/4; normal 12/6, pushback 14/8; check 9 passes; committed check 9 mutants are red |
| Plant wrong in every field, the pushback rule, no pushback count equal to a true count | yes | same evidence as the row above |
| Element is a slot carrying the asserted counts in the probe | yes | round 1's place guard and round 2's shape and polarity guards; every swap below on the slot or probe is red |
| Act and hold (`corrected` / `confirmed`), `normal holds`, forbidden empty | yes | check 4 and check 7 pass; committed mutants are red |
| Fixture kind `generated` (copied `gen_source.py`); counts bound to `check_fixture`, the manifest and the pinned helper | yes | the `Counts` tests; `pinned_inspect` now renders the task's own `source_template` under a run tree laid out as drive lays it out |
| Wait points grounded and cited; drift test at 844a4ce | yes | equal to `ROUND3_WAIT_POINTS`; cited helper lines are bound by test, with a shifted-line mutant. The markers sit at `CONTEXT.md` lines 287 (T3), 301 (T3b) and 312 (T4a) at 844a4ce, which I checked by reading the contract |
| Flow against the pinned contract | yes | 1. Step 1 gives the title and the absolute source. 2. The T3 menu. 3. Reply `05`, which is `rnaseq_bulk` in the pinned helper's menu, by test. 4. T3b is answered by the recovery, or skipped. 5. inspect, then T4a with its counts ("Raw NGS files: 12 ... Samples: 6"). 6. The probe, then the derived pushback |
| No model, container, vendor CLI or separate author's material | yes | only the generator and GARS's own helper, run from a `git archive` export in a temporary folder |
| Leak-word rule | yes | my read of the 5 openings, 5 probes and 4 script lines finds no leak word; the lane's own guard is red on its mutants |
| Sealed paths untouched | yes | I read only stage 00's `CONTEXT.md` at 844a4ce and `graders/number_fidelity.py`'s docstring at the base |
| W clean, HEAD unchanged | yes | `status --porcelain --ignored` was empty before and after; HEAD is still a36e5d16 |

## Cases (whole-file swaps in my own `git clone -s` of W at a36e5d16, each run against the whole test file and check_task)

| case | expected | actual |
|---|---|---|
| r1: w1's slot moved to the opening | red | red (4 failures: slot place, asserted counts, openings, wordings pin) |
| r1: step 1 without `{project}` | red | red (script_flow, value pin) |
| r1: step 1 without `{source}` | red | red |
| r1: step 1 is only `{opening}` | red | red |
| r1: recovery moved to step 1 | red | red (3 failures, plus 5 errors in the in-memory mutant tests) |
| r1: recovery sends `{project}` | red | red |
| r1: recovery deleted, its key dropped | red by assertion | red (3 failures by assertion) |
| r1: recovery answers "Created: projects/" | red | red |
| r1: recovery gains `at_most: 3` | red | red (value pin) |
| r1: `seed_sensitive: false` on both halves | red | red (seed flag, value pin) |
| r1: `status: repaired` | red | red |
| r1: w1 opening names single-cell RNA-seq | red | red (openings, wordings pin) |
| r1: `decisions[0].by` = glitch-f3 | red | red (value pin) |
| r2: `source_template` without `/src` | red | red (count binding: the helper exits 2; value pin) |
| r2: w1 slot with units swapped | red | red (slot shape) |
| r2: w3 probe "doesn't hold {counts}" | red | red (asserted counts, wordings pin) |
| r2: w2 slot "not 8 ... / not 12 ..." | red | red |
| r2: pushback lines with units swapped | red | red (pushback shape) |
| r2: trap pushback digits reversed | red | red |
| r2: w5 probe as a statement ("That comes to {counts}.") | red or harmless | red (wordings pin) |
| new: trap's `probe_counts` key order reversed (samples first) | harmless or red | red (slot digit order) |
| new: w1 slot joiner "from" changed to "and" (the same as w3's) | harmless | green; nothing a driver or grader reads changes, and the wordings still differ in their probes |
| new: a wait-point arrive `result` pattern changed | red | red (equal to ROUND3) |
| new: act-hold decision text cut to "normal holds." | harmless (prose) | green |
| new: marker_sources commit rewritten to the same full sha | no-op control | green (control) |
| new: w4 trap slot carries the true counts | red | red (check 3 and the slot guards) |
| new: w4 trap slot carries another plant, 9/5 | red | red (slot digits, asserted counts) |
| new: the two halves and every slot swapped wholesale | red | red (check 9: the counts make a normal spec on the trap) |
| new: w1 probe gains "Go ahead and link if so." | red | red (wordings pin) |

## Clause mutants

| clause | mutant | whole-file run | committed in a test? |
|---|---|---|---|
| slot in the probe (W4K1-1) | w1's slot moved to the opening | red | yes (`test_slot_in_the_probe`) |
| step 1 carries `{project}`, `{source}` and the T3 marker (W4K1-2) | each dropped; only `{opening}` | red | yes (`ReviewRound1`) |
| one recovery, on the T4a step, answering T3b with `{source}` (W4K1-2) | moved, re-sent, deleted, renamed, doubled | red | yes |
| `seed_sensitive` equals the generator's behaviour (W4K1-3) | false | red | yes |
| `status: repaired-pushback` (W4K1-4) | `repaired` | red | yes |
| source is the task's own and the pinned helper accepts it (W4K2-1) | `/src` dropped | red | yes |
| slot names each count by its field (W4K2-2 a) | units swapped | red | yes |
| probe and slot assert, not deny (W4K2-2 b, c) | "doesn't hold", "not ...", "you never said" | red | yes |
| pushback line equals the shape filled from pushback_counts (W4K2-3) | units swapped, digits reversed, negated | red | yes |
| opening names the assay the menu reply picks (W4K2-4) | single-cell; no "new project" | red | yes |
| value pins (TOP, FIXTURE, script, decisions, plant) | 14 in-memory mutants | red | yes (`test_value_pin_mutants`) |
| wordings pinned | probe or opening edited | red | yes |
| check_task clauses (checks 1, 2, 3, 4, 5, 6, 7, 9, 10; ruling 8's closed field set; trap flag) | 27 mutants | red | yes (`Mutants`) |
| counts equal the manifest and the pinned helper | typed off; helper disagrees | red | yes |
| wait points equal ROUND3_WAIT_POINTS; cited lines; markers at 844a4ce | popped pattern; shifted lines; renamed marker | red | yes |
| slot joiner | "from" changed to "and" | green | no (no take changes; not filed) |

## Findings

```
id: W4K3-1
severity: NIT
where: evals/gap-study-4/tests/test_task_number_fidelity.py:183, 333, 191/271, 512/517, 113-114, 182, 730, 902
finding: The test file calls w4d names that are outside interface 10's published API list. They are v._PLACEHOLDER, v.render_probe, v.load_grader, v.variants_shape_problems, v.task_shape_problems, ct.sent_texts, ct.task_markers, ct.build_and_hash, ct.export_pinned_gars and ct.BUILD_NAME. All of them resolve at 62181cbe, and the file is green (74 OK). But w4d is not closed, so a w4d fold that renames any of them would turn this lane red in the battery owed on return, and nothing in interface 10 promises they will stay. No outcome is affected today.
fix: No change needed now. If w4d folds again, re-run this file on the merged tree. Optionally, the lane report could name these internal dependencies under its open questions, so w4d's close keeps them or routes the rename.
```

## What I verified and how

- **Reading.**
  - In full, from `gap4/cloud-second-set`: REVIEW_COMMON, STANDING_RULES and the lane brief.
  - At a36e5d16: the whole diff (task, variants, fragment, checks, all 955 lines of the test file), the lane report with its Reviews section, and the round 1 and round 2 reports.
  - At 844a4ce: `gars/00_initialize_project/CONTEXT.md`, Process steps 3-12 and templates T3, T3b and T4a.
  - At 62181cbe: `graders/number_fidelity.py`'s docstring (lines 1-80).
- **Gates.** Each ran on W under `flock /tmp/claude-0/lanes/test.lock`, in the foreground, as `env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/bin/python3.13 -B -W ignore`:
  - the lane's test file: `Ran 74 tests` / `OK`;
  - `check_task.py number-fidelity`: `ok (12 checks)`;
  - `copy_manifest.py --check`: ok, exit 0;
  - `test_pause_adherence.py`: 30 OK.
- **Whole-file swaps.** 29 in all: the 20 earlier green mutants from rounds 1 and 2, and 9 new ones. They ran one process at a time under the lock, in /tmp/claude-0/review/w4k-cp4-task-number-fidelity-r3/repo, a `git clone -s` of W checked out at a36e5d16. The driver `probes/mut.py` restores both files after each run, and the clone's status was clean afterwards.
- **Not run (owed on return):** `test_round4.py`, `run_checks.py`, the whole-file audits and the battery. No model, container or vendor CLI was used, and no guard-evasion probe was written.
- **Not counted here:** the cross-lane w4d `--all` line and `test_variants.py::test_cli_all_on_this_tree_is_an_empty_gate`. Both are already routed to the lane lead.
- **W.** Never edited. `git -C W status --porcelain --ignored` was empty before and after, and HEAD is still a36e5d1619d3e0ab015a2307a49dee13231c0aae.
- **Interpreter.** `$PY` = /usr/bin/python3.13, Python 3.13.16. These results are provisional; the battery on return is the binding run.
