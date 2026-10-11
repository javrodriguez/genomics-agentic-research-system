status: handed back for review round 1, partly complete (see "Not built")
head: ef41fb8e (code). Base 48ca93fa (the wave 6 merge head carrying S1-S7), branch gap4/w6i-checker-body, worktree /Users/javrodher/aegis-builds/gap4-w6i.

# Lane w6i-checker-body: Gap Study round 4, slice S6b, the checker body (records side)

_Written Sun 11 Oct 2026 19:47 EDT (`date`) by the slice's sole writer (Claude Opus 5.5 sub-agent), assigned by glitch-1b under Javier's standing delegation. Spec: plans/gap-study-round-4/s6b-checker-body-plan-2026-10-11.md with its rulings D1-D8 and named limit L-S6-1._

No image or container was built or run.
No model was run, and no test used a network.
No login, `.env`, sealed, holdout, brief, grader-source or saved-output path was read.
Nothing was pushed, merged or dispatched.

## Commits

| sha | stage |
|---|---|
| 583b58c1 | 1: the round-4 design view, the mode from the routing pin, the first-turn rule, the harness guard (L-S6-1's acceptance) |
| 08f1b624 | 2: the carried driver items (d), (e), Q6, W6H-R2-1, R-S6-net |
| c55293f3 | 3: mode_binding.py by harness and model (Q2) |
| ef41fb8e | 4: the operator side of the drive loop (C9-C12) |

## What each piece does, with its test

`check_take.py` (moved w6h to w6i under ruling S6b-gap4-1).
- R4C-7, the design view (D2, D3): `design_view(row, pin=, run_tree=, constants=)` builds check()'s spec from tasks/<task>.json's trap and normal halves (variants.HALF_KEYS).
  It builds pre from the draft in force plus a closed CHECKER_CONSTANTS block.
  It also carries the take's own wording's script (variants.operator_steps) and its source (the task's source_template, rendered with the run tree).
  check() reads it through one keyword, `design=`.
- Seven more lines changed in place, each marked ROUND 4:
  - 1569 and 1571: the view's spec and pre;
  - 1592 and 1594: the first-turn rule;
  - 1611: the view's source;
  - 1651: completion_problems on the design in force (it read prereg.load() a second time);
  - 1718: the walk branch's other half for trap and normal;
  - 1567: the signature again.
- The round-3 byte binding moved from w6h's checks.d to `checks.d/w6i-checker-body.txt`, re-indexed to (901, 1566, 1568, 1570, 1591, 1593, 1603, 1610, 1650, 1717), rc 0.
- CHECKER_CONSTANTS:
  - known values: driver_outcome_shapes (round 3's vocabulary), and system_under_test.gars_tree_sha = 8a54e0f8cd91caf558d0d168f1b87e36d0bc0b74 (`git rev-parse 844a4ce:gars`, run on this worktree);
  - PENDING: budgets.turn_timeout_s, driver_constants.stripped_env, run_location, harness_delivered_user_records and environment_record.
  - check4 raises CheckRefused naming every PENDING constant; nothing is defaulted.
  - A draft that grows one of these keys is refused, never shadowed.
- D1: the permission mode is the take's routing pin, written into the view's driver_constants.permission_mode_by_arm for the take's arm only.
  A PENDING mode reads as unpinned, so line 902 and recorded_mode_problems never bind it.
- R4C-8: `agent_output_count`: no-first-agent-turn only when no assistant record holds text or a tool call.
- R4C-9: `harness_guard`: only claude-code is read; design_view and check4 refuse any other harness.
- check4 now requires a Design, the view's task and half, and the wording script the view rendered.
- `Design` is a plain class: test_scaffold's import probe runs the file unregistered, which breaks a dataclass.

`tests/test_checker_body.py` (new) drives check4 on the REAL design with no patched design.
It uses scope-read / trap / w3 / arm A, the draft's own row, and the real tasks, variants, draft and source template.
The test supplies, as data:
- the routing pin (pin_profiles are still PENDING), as the driver passes pin_for(row);
- the five walk-measured constants, whose production value is PENDING and refuses (tested);
- the row ledger and commit (takes.load_rows and takes.row_commits run git, which the guard refuses); the session id is takes.session_id_for of that sha.

A probe, not committed, showed the real-design path is live.
One mutation each of the fixture hash, source, budget, gars tree, outcome, environment.json, a missing operator line, a leak word, the model id and a study read raised its own reason or event.

`drive.py` (moved w6h to w6i):
- (d) D6: the driver ends the adapter by its own flag (`_Take.adapter_open`, set once start_take returned).
- (e) preflight.postflight runs in drive()'s finally, after the cleanup and before the scan.
  It is written as postflight.json; a record that is not ok, or that did not run, raises DriveRefused, and the config folder is kept.
- Q6, D5: a failed config-folder deletion in `published` is recorded, and the next launch refuses naming the slot.
- W6H-R2-1: leaked_ids refuses an outcome without either leak key (HistoryRefused), never a bare KeyError.
- R-S6-net: a leaked network is carried as `network:<id>` in the leak's leaked_ids (batch commits it in leaked_containers).
  The restart lists networks for those ids only, so w6e's one-listing C4 is unchanged.
- C10: the evidence ledger (endstate's ledger.jsonl):
  - the take record, before the sidecar's begin;
  - a turn record for each line;
  - a background record for each cap survivor, before post-n;
  - an operator record for each event.
- C9, D8: the closed OPERATOR_STEPS table:
  - explain-not-act's save after line 2 (gen_explain_not_act.operator_save);
  - confounded-design's wait for samples.csv and copy of the design table after line 3.

  Each step is done host-side between post-n and pre-(n+1) and logged; a write on an excluded path is refused.
- C12: no samples.csv within finalize_wait_s (injected clock) is round 3's finalize abort; nothing further is sent.
- C11: endstate's operator_check runs after finish and is written as operator-check.json.
  Evidence that does not load counts one, never zero.
  CHECKER_KEYS shrinks to reasons and events, and TakeDriver takes `project_for`.

`mode_binding.py` (moved w1a to w6i, identical to edited): expected() reads {(harness, model): mode} from routing.json's pin_profiles.
A PENDING or absent mode is a problem, so --check exits 1 naming it.
judge() keys by the take's harness and model, and attempts() reads TAKE_ROOTS.
The empty gate still prints.

## Red first, then green (Mac, `mac_slot.py light-ok &&`, `env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV`, `timeout -s INT 90`, Python 3.13.2, `-B -W ignore`)

Every red run below used a byte backup, restored, with `shasum -c` OK, and every module failed by assertion with 0 errors.
- test_checker_body on 48ca93fa's check_take.py: `Ran 17`, failures 15, 0 errors, rc 1.
  R1 records L-S6-1 itself: "check4 on the real design raised KeyError: 'trap'".
- B10-B14 on 48ca93fa's drive.py: `Ran 5`, failures 5, 0 errors, rc 1.
- B15-B18 on c55293f3's drive.py and on 48ca93fa's: `Ran 4`, failures 4, 0 errors, rc 1 each.
- test_mode_binding on 48ca93fa's mode_binding.py: `Ran 6`, failures 4, 0 errors, rc 1.
  A first draft errored by TypeError; a signature assertion replaced the call.

Green at ef41fb8e (each rc 0, each ending in a bare `OK`):
- test_checker_body 17;
- test_check_take 15;
- test_mode_binding 6;
- test_box_integration by class: TestBoundChecks 18, TestTheTakePath 17, guard and stub 3;
- test_drive_commit 31;
- test_scaffold TheManifest.test_check_passes_on_the_folder and TheImports (3), plus test_a_copy_that_differs_without_an_edited_entry_is_refused (at c55293f3);
- copy_manifest --check: 247 files, 35 fragments;
- probes4 --check: 1690 cells, 0 defects;
- build_draft --check;
- freeze --check;
- checks.d: w6i's byte binding and w6e's prefix binding, both rc 0.

Witnesses: each was red by its own check, with 0 collateral and 0 errors.

| file | witnesses (own lines) |
|---|---|
| check_take.py, new | no-design-view R1 (1); first-wording-always R1 (1); pending-ignored R1 (1); draft-mode-table R2 (1); text-only-first-turn R3 (1); no-harness-guard R4 (4) |
| check_take.py, S6's, unchanged counts | one-mode-constant K1 (4); ledger-arm-unbound K1 (2); the-halfs-script K2 (2); nothing-lifted K3 (1); recorded-mode-unchecked K4 (5) |
| drive.py, new | adapter-private-state B10 (3); no-postflight B11 (4); launch-ignores-publish-problems B12 (1); bare-keyerror B13 (2); restart-lists-containers-only B14 (2); unlogged-save B15 (2); log-excluded-write B16 (1); no-finalize-wait B17 (2); no-background-line B18 (1) |
| drive.py, S6's eleven, unchanged counts | 3, 1, 3, 1, 26, 3, 7, 1, 4, 2, 2 |
| test_drive_commit, w6e's ten | all still red |
| mode_binding.py | model-only M1 (1) |

Not run on the Mac: the whole test_scaffold, test_pipeline and run_checks (athena's).

## Departures and questions for glitch-1b

- **Departure s6b-1:** seven in-place lines in check_take.py, not D3's two.
  The two extra are 1611 (source) and 1651 (completion_problems).
  Without 1651, completion_problems read the draft's absent driver_outcome_shapes and returned [] on every real take, which is a silent loosening.
  Without 1611, every {source} line rendered empty.
  All the lines are bound by the re-indexed checks line.
- **Departure w6i-1:** test_scaffold's copied_modules also reads w6i's fragment; this is recorded in w1a's entry, in the shape of w6e-1 and w6h-1.
- **Departure s6b-2:** CHECKER_KEYS dropped unexplained_operator_diffs and finalize_abort, because the driver now measures both (plan 566).
  TakeDriver gained a required `project_for`.
- **Departure s6b-3:** leaked_containers can hold `network:<id>`, which is the only road batch.py offers without editing it.
- Q-w6i-1: mode_binding's TAKE_ROOTS is set to `takes/`, but production take_folder is not fixed yet.
- Q-w6i-2: confounded-design's design table is read from round 3's place, data/staging/{project}/samples.csv, while round 4's source template is data/staging/{project}/src.
  The round-4 fixture layout must confirm this.
- Q-w6i-3: the DuckAdapter ending rule only sets the flag when start_take returned, so a start_take that raises after opening is not ended.
  Teardown still removes the containers.
- Q-w6i-4, named limit: instruction_content_problems binds loaded files to the repository's working tree, not to the pinned tree 844a4ce; this has to be settled before CP6.
  The round-3 CLI (`main`, choices positive/control) is unchanged and unused by round 4.
- Q-w6i-5: design_view takes the run tree from the caller, so it is not cross-checked against the transcript's working directory.

## Not built (remaining S6b items, with why)

- C7 driver-ledger.json, C8 environment.json and C6 (the session file copied out of the config folder through scrub.py and cross-checked with the stream) are not built.
  Each needs records only the Claude Code adapter (S6c) produces:
  - the session id from the row commit;
  - the harness version;
  - apiKeySource per turn;
  - the stream-json event shapes the cross-check compares.

  Building them on ScriptedAdapter would invent those shapes.
- A production `checker` callable wiring check4 and design_view into TakeDriver is not built for the same reason.
  The acceptance's "real checker body, no spy" take through TakeDriver therefore remains, and until C7 lands check4 reads every real take as constant-binding.

  Recommendation: fold these into S6c, or into an S6b-2 on S6c's head.
  The design view, the constants and the evidence ledger they would feed are in place.

## Writer release

The tree is clean at this report's commit, and no `__pycache__` was written.
Scratch outputs are in the session scratchpad under `w6i/`.

RESUME HERE: hand-back at ef41fb8e
