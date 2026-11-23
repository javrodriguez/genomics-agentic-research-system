# Lane report: wave6-merge (Gap Study round 4, wave 6 integration merge)

Sole writer of `gap4/wave6-merge`, assigned by glitch-1b under ruling W6-merge-1 (`plans/gap-study-round-4/next-slices-2026-10-11.md`).
Base: `28e1be3e`, the athena-verified w5c merge.
Written Sun 11 Oct 2026, merges 18:24 to 18:30 EDT (clock read with `date`).
Nothing pushed, nothing amended or rebased.

## Merges (in order, each `git merge --no-ff`, each tip verified before merging)

| # | Slice | Branch | Tip merged | Ruling | Merge commit | Conflicts | copy_manifest --check |
|---|---|---|---|---|---|---|---|
| 1 | S4 | gap4/w6c-w5c-nits | 3869f7648bd9 | W6C-close-1 | 9d681e1c8850 | none | exit 0 (29 fragments, 224 files) |
| 2 | S3 | gap4/w6d-prereg-order | 07c79075 | W6D-close-1 | 591367204503 | none (w1a-cp1-scaffold.json auto-merged) | exit 0 (30 fragments) |
| 3 | S2 | gap4/w6b-cp6-stub-agents | aca93d1b | W6B-close-1 | ce3211530596 | none | exit 0 (31 fragments) |
| 4 | S5 incl. S1 4dd1e8e6 | gap4/w6e-drive-commit | ddebb57e | W6A-close-1, W6E-close-1 | 168bc1ffbe02 | tests/test_scaffold.py (resolved below) | exit 0 (32 fragments; 37 identical, 16 edited, 184 new) |

S2's branch name was found with `git branch --contains aca93d1b`: `gap4/w6b-cp6-stub-agents`.
`4dd1e8e6` (S1) was confirmed an ancestor of `ddebb57e` before merge 4.
No tip had moved from the sha the assignment named.

## Conflict and resolution

Only one conflict, in merge 4, in `evals/gap-study-4/tests/test_scaffold.py`, inside `copied_modules()`.
HEAD (from w5c) read fragments `(OWN_FRAGMENT, w5c-draft-ci.json)`; w6e (based on 89b54db4, before w5c) read `(OWN_FRAGMENT, w6e-drive-commit.json)` with its departure w6e-1 comment.
Resolved by keeping both intents: the comment kept, and the tuple now reads all three fragments, `OWN_FRAGMENT`, `w5c-draft-ci.json` and `w6e-drive-commit.json`, so `build_draft.py`, `study.py` (w5c, edited) and `drive.py` (w6e, edited) all stay probed.

Identical-copy examples after all merges: the two slices changed two different tests, so both stand with no choice needed.
S3's swap (`round2.py` in the "a copy must say so" test) and S5's swap (`denials.py` in the "differs without an edited entry" test) each name a file still recorded `identical` in `w1a-cp1-scaffold.json` at the merge head.
`BLOCKED` stays empty as w5c left it (prereg-draft.json exists, so drive.py imports); w6e's older `drive.py` entry did not come back.

No conflict reached production code; w6e's changes to `drive.py` and `box/preflight.py` merged cleanly.

## Ownership after all merges (read from the fragments at 168bc1ff)

- `drive.py` → w6e-drive-commit (edited), one owner.
- `run_checks.py` → w6c-w5c-nits (new), one owner.
- `prereg.py` → w1a-cp1-scaffold (edited, S3's reason), one owner.
- `build_draft.py` → w5c-draft-ci (edited).
- No path is claimed by more than one fragment.
- Transfer notes carried by merge 4 (CP2-preflight-5, w6a-1, W6A-R1-2): `box/preflight.py`, `tests/test_preflight.py` and `tests/test_run_take.py` stay in w4b's fragment, and `tests/test_wave4_bindings.py` in wave4-merge's, each with its "Owner since 11 Oct 2026: lane w6a" note; consistent with W6A-close-1.

## Checks on the merge head 168bc1ff (Mac, Python 3.13.2, each behind `mac_slot.py light-ok` and `timeout -s INT 60`)

| Check | Exit | Result |
|---|---|---|
| build_draft.py --check | 0 | the committed draft is what build_draft.py builds |
| freeze.py --check | 0 | 237 owned paths checked; no takes or freeze performed |
| probes4.py --check | 0 | 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems |
| tests/test_ci_job.py | 0 | Ran 23, OK |
| tests/test_build_draft.py WitnessEvidence | 0 | Ran 3, OK |
| tests/test_prereg_order.py | 0 | Ran 10, OK |
| tests/test_stub_agents.py | 0 | Ran 18, OK |
| tests/test_drive_commit.py | 124, then 0 | first run killed by the 60 s cap at load1 about 14; rerun at load1 8.1: Ran 31, OK in 54.8 s |
| tests/test_preflight.py | 0 | Ran 43, OK |

The test_drive_commit timeout is the cap, not a failure: w6e's own report gives about 66 s for the module, so a 60 s whole-module cap on a loaded Mac is too tight.
athena's run should give it its usual budget.
Not run on the Mac, by rule: the whole test_scaffold, test_pipeline and run_checks; those belong to athena.

RESIDUAL: the merge head has not had athena's solo run_checks; it is the evidence for every slice in it under W6-merge-1.

Superseded by the S7 addendum below.

## Addendum: S7 joined (glitch-1b's word, Sun 11 Oct 2026 about 18:34 EDT)

Merge 5, `--no-ff`: S7 `gap4/w6g-endstate-carries`, tip f0c4253b2af4 (verified before merging; contains code 31caf0de), ruling W6G-close-1 (`s7-endstate-interface-options-2026-10-11.md`), merge commit 97eaf2d6f982 on top of report commit 239b75c1.
No conflicts: the S7 fragment and checks file are new, the four fragment reason edits (w2a, w3b, w4c, w5b) and the production files (box/sidecar.py, graders/endstate.py, graders/plan_gate.py, one fixture line in tests/test_pipeline.py) merged cleanly, disjoint from S5's drive.py and box/preflight.py.
No path is claimed by more than one fragment after the merge (33 fragments).

Checks on 97eaf2d6 (Mac, Python 3.13.2, each behind `mac_slot.py light-ok` and `timeout -s INT 90`, load1 under 5):

| Check | Exit | Result |
|---|---|---|
| copy_manifest.py --check | 0 | 239 files from 33 fragments |
| probes4.py --check | 0 | 1690 cells graded, 0 defects, 0 problems |
| build_draft.py --check | 0 | the committed draft is what build_draft.py builds |
| freeze.py --check | 0 | 239 owned paths checked |
| tests/test_endstate.py | 0 | Ran 80, OK |
| tests/test_sidecar.py | 0 | Ran 154, OK |
| tests/test_plan_gate.py | 0 | Ran 49, OK |
| tests/test_preflight.py | 0 | Ran 43, OK |

Superseded by the S6 addendum below.

## Addendum: S6 joined (glitch-1b's word, Sun 11 Oct 2026 about 19:05 EDT)

Merge 6, `--no-ff`: S6 `gap4/w6h-drive-lifecycle`, tip ff073698deec (verified before merging; contains code b4146510 and S5 ddebb57e), rulings W6H-close-1 and S6-gap4-2, review round 2 PASS (`w6h-review-r1-2026-10-11.md`), merge commit 2511de8a2253.
Production files (batch.py, check_take.py, drive.py) and the fragment edits (w1a, w1b, w6e) merged without conflict.
One bookkeeping conflict, again in `tests/test_scaffold.py` `copied_modules()`: HEAD read w1a, w5c-draft-ci and w6e; w6h read w1a and w6h with a comment naming departures w6e-1 and w6h-1.
Resolved by keeping w6h's comment and reading all four fragments (w1a, w5c-draft-ci, w6e-drive-commit, w6h-drive-lifecycle).
After the merge: drive.py and check_take.py are owned by w6h (edited), batch.py by w1b, and no path is claimed twice.
The "differs without an edited entry" test now uses denials.py, allowlist.py, lexicons/permission-stop.json and review_kit/rounds.py, all still recorded identical in w1a.

Checks on 2511de8a (Mac, Python 3.13.2, `mac_slot.py light-ok`, `timeout -s INT 90`, load1 under 5):

| Check | Exit | Result |
|---|---|---|
| copy_manifest.py --check | 0 | 36 identical, 17 edited, 190 new |
| tests/test_box_integration.py TestTheTakePath | 0 | Ran 17, OK |
| tests/test_check_take.py | 0 | Ran 15, OK |

Superseded by the integration-fix addendum below.

## Addendum: integration fixes after athena's run on 48ca93fa (Sun 11 Oct 2026, 20:26 to 20:37 EDT)

athena's run_checks on 48ca93fa (run `gap4-wave6-merge-48ca93fa-48ca93f-20261011T231424Z`) passed 116 of 124.
The 8 failures had two causes, and both came from slices meeting in this merge.
Fix commit: 104fa58db183.

Cause 1, R38 (test_ci_job.py and its witnesses 1 to 3, and test_round4 through it).
S6 added `tests/test_box_integration.py`, but `.github/workflows/ci.yml` still carried the "omitted until it exists" comment in place of its step.
Fix: ci.yml now runs `python3 -W ignore evals/gap-study-4/tests/test_box_integration.py` as its own step ("Box integration", the contract's exact BOX_STEP), before Pipeline integration, as the plan's Level 3 list orders it.
Lines removed from the workflow since the kickoff: still 0, because the two comment lines postdate ad88d14d.
The contract and its mutation cases are unchanged.
One witness needed the present state: `box-landed` had built its mutant from the old deferred workflow, so with the step in place it was not red.
It now takes the step back out (file present, workflow deferred) and is red by R38.command again; the change is in test_ci_job.py setUpModule.
The four box-deferred mutants (box-owner, box-ruling, box-premature, box-indented) drop out, because the test itself skips them once the comment is gone; command-05 enters.
The witness registry now holds 113.

Cause 2, test_build_draft Claims.test_relocated_claims (and witness groups 3 and 4, which run it first).
The test read only the w1a and w5c fragments.
drive.py moved to w6e (S5-gap4-1) and then, with check_take.py, to w6h (S6-gap4-1), so those two fragments counted 29.
copied_modules() now reads four fragments (w1a, w5c-draft-ci, w6e-drive-commit, w6h-drive-lifecycle).
Fix: the test's expected fragment list now matches copied_modules(); the floor of more than 30 is unchanged and holds at 31 (27 + 2 + 0 + 2).
No claim was lost.

Checks on 104fa58d (Mac, Python 3.13.2, `mac_slot.py light-ok`, `timeout -s INT 120`):

| Check | Exit | Result |
|---|---|---|
| copy_manifest.py --check | 0 | 34 fragments |
| build_draft.py --check | 0 | the committed draft is what build_draft.py builds |
| tests/test_ci_job.py | 0 | Ran 23, OK |
| tests/test_ci_job.py --witnesses 1 / 2 / 3 | 0 / 0 / 0 | 38/38, 38/38, 37/37 red; registry 113 (before the box-landed fix, group 2 exited 1 on box-landed) |
| tests/test_build_draft.py | 0 | Ran 41, OK |
| tests/test_build_draft.py Claims | 0 | Ran 2, OK |
| tests/test_build_draft.py --witnesses 3 / 4 | 124 / 124 | the 120 s cap cut each off after 3 witnesses, all red with none failed; athena takes about 350 s per group, so these two are athena's |

RESIDUAL: the full test_round4 battery and build_draft witness groups 3 and 4 run on athena only.

Superseded by the S6b/S6c addendum below.

## Addendum: S6b and S6c joined (glitch-1b's word, Sun 11 Oct 2026, 21:47 to 21:50 EDT)

Merge 7, `--no-ff`: S6c `gap4/w6j-claude-adapter`, tip aac82148804b (verified before merging; contains code ea091e59, S6b `gap4/w6i-checker-body` at d56f87081, and 48ca93fa), rulings W6J-close-1 and W6I-close-1, merge commit 77996eb4.
No textual conflict.
w6j had already updated `tests/test_scaffold.py` copied_modules() to read six fragments (w1a, w5c-draft-ci, w6e, w6h, w6i, w6j), and that change merged cleanly over this branch's version.
Production files (check_take.py, drive.py, mode_binding.py, claude_code_adapter.py) merged cleanly.
Ownership now: drive.py and check_take.py → w6j, and mode_binding.py → w6i (all edited); no path is claimed twice (36 fragments).

There was one semantic follow-on, and it is bookkeeping: test_build_draft Claims.test_relocated_claims read only four fragments, so it would have counted 28 against its floor of more than 30.
Fix commit 66e1ede1: its fragment list now matches copied_modules()'s six; the floor is unchanged and holds at 31 (26 + 2 + 0 + 0 + 1 + 2).

Checks on 66e1ede1 (Mac, Python 3.13.2, `mac_slot.py light-ok`, `timeout -s INT 120`):

| Check | Exit | Result |
|---|---|---|
| copy_manifest.py --check | 0 | 252 files from 36 fragments |
| probes4.py --check | 0 | 1690 cells graded, 0 defects, 0 problems |
| build_draft.py --check | 0 | the committed draft is what build_draft.py builds |
| freeze.py --check | 0 | 252 owned paths checked |
| mode_binding.py --check | 0 | graded 0 attempts; none committed yet |
| tests/test_ci_job.py | 0 | Ran 23, OK |
| tests/test_build_draft.py Claims | 0 | Ran 2, OK |
| tests/test_drive_loop.py | 0 | Ran 27, OK |
| tests/test_checker_body.py | 0 | Ran 26, OK |
| tests/test_claude_code_adapter.py | 0 | Ran 19, OK |

Superseded by the sys.path addendum below.

## Addendum: the sys.path leak after athena's run on 7e057eb2 (Sun 11 Oct 2026, 21:59 to 22:16 EDT)

athena's run_checks on 7e057eb2 (`gap4-wave6-merge-7e057eb2-7e057eb-20261012T003714Z`) passed 123 of 124.
The one failure was test_round4: `test_confounded_design.TheContractDrift.test_the_reimplemented_helpers_equal_stated_counts` (line 644) found `<repo>/evals` on sys.path.

Culprit: check_take.py, a round 3 copy, puts `evals/` at the front of sys.path on import (line 70).
S6 introduced the leak, not an older slice: its new `tests/test_check_take.py` imports check_take.py in setUpModule and never restores sys.path.
`tests/test_box_integration.py` reaches it through drive.py, and `test_drive_loop` leaks through that module's setUp.
S6b's `tests/test_checker_body.py` (merged after 7e057eb2) does the same.
test_round4 runs every module in one process, alphabetically, so these run before test_confounded_design.
test_mode_binding and test_claude_code_adapter do not leak; the evidence is a one-process run of each before test_confounded_design, ending with 0 `evals/` entries on the path.
Reproduced on the Mac (a scratch runner, one process, discovery as test_round4 does it):

| Run | Exit | evals/ left on sys.path |
|---|---|---|
| test_confounded_design alone | 0 | 0 |
| test_check_take, then test_confounded_design | 1 (the line 644 failure) | 6 |
| test_checker_body, then test_confounded_design | 1 | 11 |
| test_drive_loop, then test_confounded_design | 1 | 1 |
| test_mode_binding, then test_confounded_design | 0 | 0 |
| test_claude_code_adapter, then test_confounded_design | 0 | 0 |

Fix (commit 664d9b00), line 644 untouched: in test_box_integration, test_check_take and test_checker_body, setUpModule first registers `_STACK.callback(sys.path.__setitem__, slice(None), list(sys.path))`.
Being registered first, it runs last when tearDownModule closes the stack, and it puts sys.path back in place.
The check is new `tests/test_wave6_bindings.py` (binding W6M1).
In a fresh interpreter per module it runs setUpModule, then the check_take.py import, then tearDownModule, and requires sys.path back exactly; a non-vacuity test shows the import does insert `evals/`.
It is claimed by the new `COPIED.d/wave6-merge.json`, with `checks.d/wave6-merge.txt`.
Red first: before the fix it failed on all three modules by assertion (`W6M1.evals-left:<module>`), and the non-vacuity test passed.

Checks on 664d9b00 (Mac, Python 3.13.2, `mac_slot.py light-ok`, `timeout -s INT 120`):

| Check | Exit | Result |
|---|---|---|
| tests/test_wave6_bindings.py (before the fix) | 1 | 3 failures, one per module |
| tests/test_wave6_bindings.py | 0 | Ran 2, OK |
| test_check_take, then test_confounded_design (one process) | 0 | Ran 44; 0 evals/ left |
| test_checker_body, then test_confounded_design | 0 | Ran 55; 0 left |
| test_drive_loop, then test_confounded_design | 0 | Ran 56; 0 left |
| tests/test_check_take.py | 0 | Ran 15, OK |
| tests/test_checker_body.py | 0 | Ran 26, OK |
| tests/test_box_integration.py TestGuardArmed, TestTheTakePath, TestBoundChecks, TestRealBoxStub | 0 each | 2, 17, 19, 1 OK |
| tests/test_box_integration.py TestWitnesses | 124 | exceeds the 120 s cap; athena's |
| copy_manifest.py --check | 0 | 255 files from 37 fragments |
| freeze.py --check | 0 | 255 owned paths |

lint_language and lint_pooling, run by absolute path over the folder, report pre-existing findings in other lanes' files (26 and 8), none in a file this commit touches.
I did not chase them; CI runs them from the repository root, and athena's run_checks is the authority.

RESIDUAL: a later module in the battery that had passed only because of the leaked path would now fail. None was found on the Mac, but the full test_round4 battery is athena's.

RESUME HERE: merge head 664d9b0080461ed1e38dfd04a27c16597c590d1c; athena run_checks owed (orchestrator)
