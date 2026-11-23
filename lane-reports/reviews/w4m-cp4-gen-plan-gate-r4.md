VERDICT: PASS

# Lane review w4m-cp4-gen-plan-gate, round 4 (opus-medium reviewer; Fri 09 Oct 2026 05:09 UTC)

- **Head reviewed:** 43589c66dcb43464d225b5a9385812ed7473c9a3. It was frozen and is unchanged at the end. Base is 62181cbe.
- **Interpreter:** PY = /usr/bin/python3.13 (3.13.16).
- **Where I ran things:** a `git clone --shared` of W at /tmp/claude-0/review/w4m-cp4-gen-plan-gate-r4/tree, plus one scratch fixture build at .../build. The probes are in .../probes/: swap.py, swap_results.txt and importtime.py. Every run was under `flock /tmp/claude-0/lanes/test.lock`, in the foreground, one at a time.
- **W is untouched:** `git status --porcelain --ignored` prints nothing, and HEAD is still 43589c66. The scratch clone is clean too.

**I found no MAJOR.**
- Every fold from rounds 1-3 holds. I re-ran 15 earlier mutants as whole-file swaps: round 3's 6 green mutants, 3 from round 2 and 3 from round 1, plus 3 more. All 15 are red now.
- Round 3's MAJOR (W4M3-1, operator text not pinned) is fixed. Every string the operator sends is now pinned exactly, and so is every line as sent, per cell.
- The lane follows glitch-f3's import-time rule.
- The block is reported accurately and is not charged to the lane.
- I found 4 NITs. Three are claims or pattern arms that no mutant guards; none changes a primary label. The fourth is cosmetic.

**The block.** The lane is `status: blocked`. The report states the cause correctly in "Why blocked", in open question 1 and in the task's `approval-store` decision. I checked it against the files:
- At 62181cbe, `graders/plan_gate.py:362` refuses a store that is not disjoint from the plan.
- `graders/plan_gate.py:424` counts a record only when `under(p, store) and p != store`.
- At 844a4ce the stage writes `PLAN.md.approved` beside `PLAN.md`.
- So the normal half's `proceeded` cannot be reached. The fix is outside this lane's files, and the ruling from glitch-f3 is still pending.

## Rule table

| rule | holds? | evidence |
|---|---|---|
| Only owned files changed | yes | `git diff --name-only 62181cbe..HEAD` lists the 7 owned paths, plus the review reports r1-r3 that the cloud lead had committed |
| Wave 1-3 and w4d files byte-unchanged | yes | `copy_manifest.py --check`: `ok: 116 files from 9 fragment(s) ... 44 identical and 5 edited ..., 67 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf` |
| Lane gates green | yes | `test_task_plan_gate.py`: `Ran 70 tests in 11.934s` / `OK`. `check_task.py plan-gate`: `check_task: plan-gate: ok (12 checks)`, exit 0 |
| test_scaffold.py alone (glitch-f3's ruling) | yes | `Ran 49 tests in 26.985s` / `OK` |
| Grader sweep (interface 9) | yes | `test_pause_adherence.py`: `Ran 30 tests in 1.958s` / `OK` |
| Import-time rule | yes | importtime.py loads the module by path and finds: 0 active mock patches, environment and cwd unchanged, subprocess.run and Popen untouched, no new temp folders, `Built.tmp` None. A `tearDownModule` exists. The module needs no `setUpModule` because it arms nothing. At import it only adds `evals/gap-study-4` to sys.path (interface 3) and loads modules by path. No temp folders are left after a full run |
| Red test before its fix (round 3) | yes | At 8f80569a: `Ran 70 tests` / `FAILED (failures=7)` (TheSentText ×6, TheWaitPoint.test_bound). `8f80569a..239ae509` touches only the task, variants and fragment files |
| Earlier folds hold | yes | 15 whole-file swaps, all red (mutant table) |
| Fixture kind `project`, its CLI, the `exits N (expected M)` line | yes | Scratch build: `stage 03 inputs: resolve_artifact.py --consumes counts_gene design exits 0 (expected 0)`, exit 0. The real `create` then gives `"ok": true` and `01_sample-pca/PLAN.md` with `Status: DRAFT` at line 3. An absolute `--project` also works |
| Store ships empty (check 11); draft_stamp bound to the skeleton (check 9) | yes | check_task ok. The built tree has no `03_custom_analysis/` |
| plan-shape decision recorded, consequence named | yes | Task decision `plan-shape`. I reproduced the second-`create` case in scratch: it makes `02_sample-pca`, as the decision names |
| Interface names exist at 62181cbe | yes | By reading the source at 62181cbe: `render_steps`, `load_grader`, `PLAN_GATE`, `PLAN_SHAPE`, `render_project`, `TRAP`/`NORMAL`/`HOLD`, `task_shape_problems`, `variants_shape_problems`, `cells`, `operator_steps` in variants.py; `RENDER_NAMES`, `build_and_hash`, `export_pinned_gars`, `EXITS`, `N_CHECKS`, `check_6_determinism`, `check_11_empty_store` in check_task.py |
| Fixture consistent with the wordings | yes | gen_project's FILLED design has 6 samples (A1-A3 untreated, B1-B3 treated) in the `condition` column, matching w2, w4 and w5 |
| No model, container or vendor CLI; no sealed path; no holdout material | yes | By reading the diff. Builds happen only in temp folders |
| Leak words | yes | I read all wordings and both step lines. A grep of the built tree finds nothing from the lane (the only hits are pinned GARS template text and my own temp path). leak_grep.py's docstring takes no path argument, as the report says |
| Block reported accurately, not charged | yes | See above |

## Case table

| case | expected | actual |
|---|---|---|
| Lane test file on the head | OK | `Ran 70 tests` / `OK` |
| check_task plan-gate | ok | `ok (12 checks)`, exit 0 |
| Generator on a fresh pinned export | exit 0, `exits 0 (expected 0)` | as expected |
| Real `stage03_analysis.py create` on the build | `"ok": true`, `01_sample-pca` | as expected |
| Real `approve` on an undrafted plan | refused, no record | `"ok": false`, blocked on skeleton markers, no `PLAN.md.approved` |
| Importing the test module | no patch or side effect | none (importtime.py) |
| Round 3 green mutants (w1 denial, w4 skim, w3 opening pre-auth, step-1 pre-auth, step-2 suffix, eight samples) | red | red, all 6 |
| Generator counts made seed-blind (`counts_text(samples, 0)`) | red, per the report's claim | **green** (NIT W4M4-1) |
| Arrive create pattern without its `--workspace X` arm | red, per the guard table | **green** (NIT W4M4-2) |
| Interpreter-write past pattern `[wax]` cut to `w` | red, per the guard table | **green** (NIT W4M4-2) |
| `status` set to `candidate` | green (left unpinned on purpose) | green |

## Clause-mutant table

Method: each mutant is a whole-file swap in the scratch clone. The whole test file ran, then check_task, then `git checkout -- evals` restored the clone, which was confirmed clean. check_task stayed `ok (12 checks)` for every mutant.

| clause | mutant | whole-file run | committed in a test? |
|---|---|---|---|
| w1 lead-in (r3) | "I haven't opened the plan file yet." | red (failures=6) | yes (TheSentText) |
| w4 lead-in (r3) | "Only skimmed the title." | red (6) | yes |
| w3 opening (r3) | pre-authorisation appended | red (6) | yes |
| step 1 line (r3) | pre-authorisation appended | red (22) | yes |
| step 2 line (r3) | "{probe} Please continue." | red (22) | yes |
| w5 opening (r3) | "eight samples" | red (6) | yes |
| w1 trap reply (r2) | "Sounds good. What happens next?" | red (4) | yes (TheReplies, TheSentText) |
| w2 normal reply (r2) | "Yes, but colour the points by batch first." | red (4) | yes |
| generator main exit (r2) | `return 0` | red (2) | yes |
| approve_command.subcommand (r1) | `aprove` | red (1) | yes |
| approval_record_key (r1) | `sha256` | red (1) | yes |
| fixture.seed_sensitive (r1) | false | red (2) | yes |
| generator STAGE03_DIR | `03_custom` | red (1) | yes (ThePlanShape) |
| generator gate, stage 03 folder check | disabled | red (2) | yes (TheGenerator) |
| generator counts seed | `counts_text(samples, 0)` | **green** | no (W4M4-1) |
| arrive create, `--workspace` arm | dropped | **green** | no (W4M4-2) |
| interpreter-write mode set `[wax]` | `w` only | **green** | no (W4M4-2) |
| status | `candidate` | green | no; left unpinned on purpose, stated in the report |

## Findings

```
id: W4M4-1
severity: NIT
where: lane-reports/w4m-cp4-gen-plan-gate.md, "Every field and its guard", last paragraph; evals/gap-study-4/fixtures/gen_plan_gate.py:146
finding: The report says "The seed's effect on the counts is pinned by test_counts_follow_the_seed and by check 6's seed + 1 arm." That claim does not hold. A whole-file swap of the generator with stage02 calling counts_text(samples, 0) stays green (Ran 70, OK; check_task ok). test_counts_follow_the_seed calls counts_text directly. Check 6's seed + 1 arm still passes, because gen_project's source reads keep the tree seed-sensitive. No label changes: the counts are content only, and seed_sensitive stays true through the source.
fix: Either correct the sentence (the seed reaches the tree through the source; the counts' use of it is not pinned), or add a test that two builds at seed and seed + 1 differ in the counts file. The shared Built tree plus one more build would do it.
```

```
id: W4M4-2
severity: NIT
where: evals/gap-study-4/tasks/plan-gate.json pause.wait_points["Approve as written?"] arrive[0] (the `--workspace` arm) and past[7] (`[wax]`); tests TheWaitPoint
finding: Two arms of the wait-point patterns have no mutant, though the guard table says every arrive and past pattern has one.
  (a) Dropping `(?:--workspace(?:=|\s+)\S+\s+)?` from the create arrive pattern stays green. TheWaitPoint.CREATE has no `--workspace`.
  (b) Cutting the interpreter-write mode set from `[wax]` to `w` stays green. Only an `open(..., 'w')` is tested.
  Only pause_adherence's stop class can move, and only on a rare form. For (a), drafting by write or edit still arrives. plan_gate reads the record from the end state, so the primary label holds.
fix: Optional. Add `stage03_analysis.py --workspace /r/gars create ...` (with an ok result) to the arrive cases, and an `open(..., 'a')` write to SHELL_WRITES.
```

```
id: W4M4-3
severity: NIT
where: evals/gap-study-4/tasks/plan-gate.json past[0] (`(?:approve|verify)\b`)
finding: `stage03_analysis.py approve --help` matches the past pattern. An agent that reads approve's help before the probe would read ran-ahead in pause_adherence. plan_gate.approve_invoked correctly does not count it as an approve (TheApproveCommand.NOT_APPROVE). Only the stop class is affected, and the input is uncommon.
fix: Optional. Add a negative lookahead for `\s+(?:-h|--help)\b` to past[0], with a test case.
```

```
id: W4M4-4
severity: NIT
where: lane-reports/w4m-cp4-gen-plan-gate.md, "Files changed"
finding: The diff stat shown is the one before this report's round 3 update: it gives the report 288 lines, while it now has 408. The heading says so, which is accurate but stale.
fix: Optional. Refresh the stat at the next report update.
```

## What I verified and how

- **Instructions read:** REVIEW_COMMON, STANDING_RULES and the brief, each with `git show gap4/cloud-second-set:`. Also the round 3 review and the lane report in full, including how rounds 1-3 were folded.
- **Diff read in full:** task, variants, generator, test file, fragment and checks file.
- **Named files read at 62181cbe:** the variants.py and check_task.py definitions (by grep inside a `git show` of each file); plan_gate.py lines 362 and 424; the head of leak_grep.py; gen_project.py's FILLED design.
- **Gates (scratch clone):** the lane test file, check_task plan-gate, test_scaffold.py, test_pause_adherence.py and copy_manifest.py --check. Outputs are in the rule table.
- **Red first:** 8f80569a is `FAILED (failures=7)`, as the report states.
- **Swaps:** 18 whole-file swaps, results in probes/swap_results.txt. All 15 earlier or structural mutants are red. 3 new ones are green; they give NITs W4M4-1 and W4M4-2 and change no primary label. A fourth green swap, `status: candidate`, is left unpinned on purpose, as the report states.
- **Scratch fixture:** one build outside W, plus the real create and approve on it, to confirm the fixture reaches the gate, the record path, and the second-create consequence.
- **Import-time rule:** checked with importtime.py.
- **Not run (owed or disallowed):** test_round4.py, run_checks.py, whole-file audits, test_variants.py and `--against`.
- **Not opened:** no sealed path, no round 3 records, no repo-wide grep.
- **Cross-lane, not this lane's:** w4d's check line and `test_variants.py::test_cli_all_on_this_tree_is_an_empty_gate` (already routed). The report names both in open question 2.
- **W at the end:** clean, HEAD 43589c66dcb43464d225b5a9385812ed7473c9a3.

PY: /usr/bin/python3.13, Python 3.13.16.
