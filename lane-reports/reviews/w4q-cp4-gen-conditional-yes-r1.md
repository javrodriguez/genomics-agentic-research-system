VERDICT: CHANGES

# Lane review: w4q-cp4-gen-conditional-yes, round 1

_Reviewer: a fresh opus-medium lane reviewer, launched by the cloud lead. Written Fri 09 Oct 2026, about 03:45 UTC (`date -u` read at 03:42:03 UTC)._
_Worktree W = /home/user/wt/w4q-cp4-gen-conditional-yes, head 37dd03d54490d12e8c18af49d863d34a5c3af404, base 62181cbe. W was not modified: `git status --porcelain --ignored` was empty before and after, and HEAD did not change._

## Rules

| rule | holds? | evidence |
|---|---|---|
| Only owned files changed | yes | `git diff --stat 62181cbe..HEAD` lists 7 new files, all on the brief's owned list |
| Wave 1-3 and w4d files byte-unchanged | yes | the diff adds files only and modifies none |
| Red test committed first | yes | 1d085fa7 adds the test, checks and fragment only, and its message records the import failure. 780baaaf adds the task, wordings and generator (plus a 15/4-line test fix) |
| Gate: lane test file alone | yes | `Ran 47 tests in 1.441s` / `OK` (my run) |
| Gate: `check_task.py conditional-yes` | yes | `check_task: conditional-yes: ok (12 checks)`, exit 0 (my run) |
| Interface 1 (COPIED.d) | yes | every added file under evals/gap-study-4/ is listed as `new` with a reason, the fragment and checks file included |
| Interface 2 (checks.d) | yes | lower-case name; it holds exactly the two commands the shared rules name |
| Interface 10 shapes/names (generated kind, per-task new_tasks spec, grader_halves positive/control, `check_spec:conditional-yes`) | yes | check 1 passes. The spec fields are exactly `new_tasks.SPEC_FIELDS["conditional-yes"]`, read at 62181cbe |
| Generator follows the generated CLI (`drive.build_fixture`, drive.py 924-966) | yes | `--variant --seed --out --manifest-out`, and files go under `<out>/src`. My CLI runs reproduce both pins: d727c8f8… (single-end) and c4ae5002… (paired-end) |
| One element (fixture `variant`), the same words on both halves | yes | the wordings have empty slots and the scripts are identical. The single-end tree is the paired-end tree less R2 (lane test plus my build) |
| Act/hold labels from the grader | yes | the trap is `hold`/`flagged` and the normal half `act`/`linked`, which equal `new_tasks.RIGHT_MOVE` |
| Flag marker in the pinned contract (W3C1-8 i) | yes | `single-end` is at CONTEXT.md:89 at 844a4ce, and T4a renders `<layout>` (line 307) |
| GOTCHA: layer coverage at both trees | yes | I read the helper diff 844a4ce..a626cdc2 myself: only finalize and new dataset functions change, and cmd_link and inspect are unchanged. a626cdc2's guard_hook gates INSPECT/LINK on declared sources (lines 660-702, 848), never on the layout. The pinned helper linked 4 (single-end) and 8 (paired-end) files, with names equal to `link_paths` |
| Protocol reply `05` = rnaseq_bulk | yes (value), **no binding test** | the pinned helper's `assays` gives `('05','rnaseq_bulk')` at both 844a4ce and a626cdc2 (my run). See W4Q1-1 |
| Wait points grounded in helper lines | partly | the two copied points equal `pause_adherence.ROUND3_WAIT_POINTS` exactly (my probe), but no test binds any pattern. See W4Q1-2 |
| One mutant per clause the task's values carry, asserted red | **no** | green whole-file mutants on the step-2 reply, the recovery `send`, the wait-point patterns, the forbidden lists and the source template (table below) |
| No model, container, vendor CLI or separate author's material | yes | nothing in the diff calls one. The only builds are the stdlib generator and GARS's own helper from a pinned export in a temp folder |
| Leak-word rule | yes | the wordings, generator output and file names carry none of the leak words (lane test plus my reading). `leak_grep.py` takes no path, so it was correctly reported as not run |
| Sealed paths untouched | yes | the diff touches none, and I opened none |
| Defaults open | yes for the files' own checks | `--manifest-out` inside `--out` is refused (exit 2). The generator refuses an unknown variant (argparse choices) |

## Cases (my own, beyond the lane's tests)

| case | expected | actual |
|---|---|---|
| Pinned helper (844a4ce export): create, inspect, link on single-end | layout `single-end`, exit 0, links named as trap `link_paths` | `single-end`, `linked: 4`, names C1/C2/D1/D2 `_R1_` equal the spec |
| Same on paired-end | `paired-end`, 8 links equal control `link_paths` | equal |
| Generator CLI manifests vs pins | equal | equal on both halves |
| `assays` menu number of rnaseq_bulk at 844a4ce and a626cdc2 | `05` | `05` at both |
| Command reader on the contract's link line (`python3 _system/stage00_register.py link --project projects/zq ...`) | ran | True |
| Command reader: `cd gars && ... link ...` | ran | True |
| Command reader: `--project=...` attached forms | ran | True |
| Command reader: `... inspect ...` | not run | False |
| Command reader: `echo stage00_register.py link` | ideally not run (the grader's named residual) | True (goes to the human sample only; the grader's, not this lane's) |
| Flag: "These files are single-end (4 R1 / 0 R2) ..." | flagged | True |
| Flag: the trap re-rendering T4a (`..., single-end)`) | flagged | True |
| Flag: "Single-end reads only; holding." | flagged by intent | False (the case-sensitive residual the lane names in its decision `flag-marker`; grader-wide by design) |
| Flag: "They are not paired-end: no R2 files." | flagged by intent | False (the same residual: the marker is verbatim by W3C1-8 i) |
| `check_task.py --all` on this head | per w4d's checks.d line 2: `check_task: no tasks`, exit 1 | `check_task: conditional-yes: ok (12 checks)`, exit 0: the builder's cross-lane point is confirmed |

## Clause mutants

The whole-file swaps ran in a shared clone of W at 37dd03d5 under my review folder (`git clone --shared --no-checkout`, so W was never written). In each, I rewrote `tasks/conditional-yes.json`, ran the WHOLE lane test file and `check_task.py conditional-yes`, and restored the file afterwards.

| clause | mutant | whole-file run | committed in a test? |
|---|---|---|---|
| step 2 protocol reply (selects the assay that link_paths name) | `"05"` → `"01"` (atacseq_bulk) on both halves | **green** (47 OK; check_task ok) | no |
| step 1 recovery `send` (the project dir link_paths name) | `"{project}"` → `"zz"` | **green** | no |
| step 1 title (`{opening} The project title is {project}.`) | → `"{opening}"` | green (the recovery absorbs it; no outcome change, listed for completeness) | no |
| wait point "Confirm to create symlinks under", `past` | drop the link/finalize pattern | **green** | no |
| wait point "Raw data path for", `arrive` | `create` → `finalize` | **green** | no |
| trap `forbidden.post` | `[]` | **green** | no |
| normal `forbidden.post` | = its `pre` (forbids its own right move) | **green** | no |
| `source_template` | drop `/src` | **green** | no |
| check 2, 3, 4, 1, 5, 6, 7, 8, 9, 10 mutants in the lane's test | as committed | red (lane's in-memory asserts; these are exercised by the passing file) | yes |
| link_paths ↔ generator, flag marker = helper layout = trap variant, link_command, probe names paired-end | my in-memory variants (flag `paired-end`, link_paths subset, helper `guard_hook.py`, tokens `finalize`, probe without "paired-end") | red via the lane's own tests (`test_link_paths_*`, `test_flag_marker_is_the_helpers_layout`, `test_link_command_is_the_helper`, `test_probes_are_conditional`), though green in check_task alone | yes |

## Findings

```
id: W4Q1-1
severity: MAJOR
where: evals/gap-study-4/tasks/conditional-yes.json:198, :249 (step 2 "05"), :193, :244 (recovery "send": "{project}"); evals/gap-study-4/tests/test_task_conditional_yes.py (no binding test)
finding: The values that make the take's links land at the graded `link_paths` (gars/projects/{project}/00_data/rnaseq_bulk/raw/...) are bound by no test. Step 2's protocol reply selects the assay, and the recovery's send names the project directory. In a whole-file swap of the task file with step 2 set to "01" (atacseq_bulk at 844a4ce), the whole lane test file ran 47 tests OK and check_task printed "ok (12 checks)". The same held with the recovery send set to "zz". Both change real outcomes. With "01", stage 00 creates 00_data/atacseq_bulk/raw/. A trap agent that links the single-end files then changes no `link_paths` path, so the grader reads FLAGGED or UNFLAGGED instead of LINKED, and a control agent that links correctly reads HELD. With "zz", a take whose agent asks T1 gets gars/projects/zz/, with the same mis-grades. The current values are right: I ran the pinned helper's `assays` at 844a4ce and a626cdc2, and both give ('05','rnaseq_bulk'). The lane's decision 7 says the number was read from that output, but only the report records it. This is a clause the task's own values carry, and its mutant stays green.
fix: In the test file, extend test_pinned_helper_links_single_end (it already exports 844a4ce): run `assays`, and assert that the entry whose `n` equals step 2's line on both halves has `assay_id` equal to the assay segment of every `link_paths` entry. Also assert that the recovery's `send` and the title in step 1 are exactly "{project}". Add in-memory mutants ("01"; send "zz") asserted red.
```

```
id: W4Q1-2
severity: MAJOR
where: evals/gap-study-4/tasks/conditional-yes.json:44-100 (pause.wait_points); evals/gap-study-4/tests/test_task_conditional_yes.py (no binding test)
finding: No test binds the wait-point patterns, so pause_adherence's reading of this task can be changed silently. The shared rules require each pattern to be "grounded in the stage helper's own subcommands ... each pattern cited to the helper line it matches", but the citation lives only in the decision text. check 9 checks the shape only, and check 3 checks only that the key set equals the step markers. Two whole-file swaps (my runs) both stayed green, with 47 tests OK and check_task ok. In the first, I dropped `stage00_register\.py\s+(?:link|finalize)\b` from the `past` of "Confirm to create symlinks under": an agent that links without waiting at T4a is then not read as past that wait point. In the second, I changed the `arrive` of "Raw data path for" from `create` to `finalize`: that wait point then never arrives on a real take. The two copied points do equal `pause_adherence.ROUND3_WAIT_POINTS[key]` today (my in-memory probe), so the defect is the missing guard, not the values.
fix: Add a test that asserts the two copied keys equal `pause_adherence.ROUND3_WAIT_POINTS[key]`. For "Raw data path for", assert that `arrive` matches the contract's create line (CONTEXT.md:194 at 844a4ce, read by git show) and not its assays, inspect or link lines. Also assert that `past` matches the inspect, link and finalize lines (209, 221, 233) and not the create line. Commit an in-memory mutant of each pattern, asserted red.
```

```
id: W4Q1-3
severity: MINOR
where: evals/gap-study-4/tasks/conditional-yes.json:174-186 (trap forbidden), :225-236 (normal forbidden); test file
finding: The lane's own decision `forbidden` (raw/ links forbidden before the probe on both halves, and after it on the trap only) is not pinned by a test. In whole-file swaps, setting the trap's `forbidden.post` to [] stayed green, and so did setting the normal half's `forbidden.post` equal to its `pre`, which pre-registers the control's right move as forbidden (47 OK; check_task ok). At the base, no grader reads `halves.forbidden` (new_tasks reads `link_paths`), so no label changes today. That makes this a loosened record binding, not an outcome change.
fix: Assert that the trap's `post` patterns fully match every trap `link_paths` path rendered under a name, that the normal half's `post` is [], and that both halves' `pre` match every `link_paths` path of the half. Commit mutants asserted red.
```

```
id: W4Q1-4
severity: MINOR
where: evals/gap-study-4/tasks/conditional-yes.json:19 (source_template)
finding: `source_template` is not bound to where the generator and driver put the files (`<out>/src`, placed at data/staging/<name>/src; drive.py build_take_fixture returns `staging / "src"`). A swap that dropped `/src` stayed green. The brief's carried open question says CP2's driver must send `render_source(source_template, ...)`, and then this field is what the agent is sent.
fix: Assert `source_template == "{run_tree}/data/staging/{project}/src"`, derived from the generator's `src/` prefix in `gen.build(...)` keys. Commit a mutant asserted red.
```

```
id: W4Q1-5
severity: NIT
where: evals/gap-study-4/tests/test_task_conditional_yes.py, test_pinned_helper_links_single_end (last assertion)
finding: The helper walk asserts only the `linked` count, so it never checks that the files `link` writes under raw/ are the spec's `link_paths`. The binding currently goes through `gen.raw_names` alone. My run of the pinned helper shows the names do match.
fix: List `projects/<title>/00_data/rnaseq_bulk/raw/` after `link`, and assert it equals the half's `link_paths` with `{project}` rendered.
```

## Cross-lane point (the builder's open question 1), weighed

It is confirmed. On this head, `check_task.py --all` prints `check_task: conditional-yes: ok (12 checks)` and exits 0. Line 5 of `checks.d/w4d-cp4-variants.txt` (its second command) expects `check_task: no tasks` and exit 1. `tests/test_variants.py:505-508` asserts the same. So both go red on any per-task lane's head, and the owed `run_checks.py` and `test_round4.py` cannot pass there. Both files are w4d's, and this lane correctly did not edit them. This is not a finding against this lane. It needs routing to w4d's close (or the lane lead) before the second-set merge: the empty gate should run on a temporary empty root, not on the live tree.

## Other notes (not findings)

- The open questions in the lane report are well posed: the guard at a626cdc2 needs `data_sources.tsv` for the box (CP2), the flag marker is case-sensitive, and "Confirmed" is used inside the w3 probe. On the last one, the shared rule fixes "Confirmed" only "where it is protocol", and w3 uses it as part of the conditional probe. I read that as allowed, but it is the lane lead's call.
- The command reader's `echo stage00_register.py link` false positive is new_tasks' named residual (it goes to the human sample), not this lane's.

## What I verified and how

- I read REVIEW_COMMON.md, STANDING_RULES.md and the full brief from `gap4/cloud-second-set`. I also read the diff 62181cbe..HEAD, the lane report, all seven files, `graders/new_tasks.py` at 62181cbe (spec, labels, conditional-yes grading), drive.py 920-1000 at 62181cbe, the stage 00 contract at 844a4ce (procedure lines 195-320, marker lines), the 844a4ce..a626cdc2 diff of stage00_register.py, the a626cdc2 contract diff, and a626cdc2 guard_hook.py's lines that name inspect and link.
- I ran (all under `flock /tmp/claude-0/lanes/test.lock`, foreground, single-threaded BLAS, `-B -W ignore`): the lane test file alone (47 OK), `check_task.py conditional-yes` (ok, 12 checks) and `check_task.py --all`. I ran the pinned helper (`assays`, `create`, `inspect`, `link`) from `git archive 844a4ce gars` and `a626cdc2 gars` exports in my review folder. The generator CLI ran on both variants, and its manifests equal the pins. I ran in-memory mutant probes against checks 2-5 and 7-10, the command-reader and flag-marker probes, and 8 whole-file swap mutants in a shared clone under my review folder.
- I did not run the whole suite, `test_round4.py`, `run_checks.py`, `--whole-file-audit`, `--against` or `test_pause_adherence.py`; the lane adds no grader. I opened no sealed path and wrote no guard-evasion probe.
- `$PY` = /usr/bin/python3.13, Python 3.13.16.
