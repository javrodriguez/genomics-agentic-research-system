# Lane bootstrap-constants (Gap Study round 4): the first-walk bootstrap

_Started Thu 15 Oct 2026 01:08 EDT (`date`) by the bootstrap builder, assigned by glitch-6b (Lane-orchestrator) under Javier's standing delegation.
Clone `~/aegis-builds/gap4-bootstrap-20261015`, branch `gap4/bootstrap-constants-20261015`, base 89525f03 (the harness lane's head).
Ruling built: `plans/gap-study-round-4/first-walk-bootstrap-ruling-2026-10-15.md` (01:07 EDT) and glitch-6b's addition of the same morning (the 2.1.296 vocabulary from box ba6d7f14; auto-continuation stays off the origin list)._

## RESUME HERE

- 02:06 EDT: build commit 93a98927 (B1, B2, B4, B5, B6 and the 2.1.296 vocabulary) is in; nothing pushed.
- Branch battery (one module at a time, light-ok before each) green on the touched and reading modules; a wider set was running at 02:06.
- Merged scratch `~/aegis-builds/gap4-bootstrap-scratch` (383e5c2f + this commit as a patch, draft rebuilt by build_draft, identical) built; its battery and the generated-mutant sweeps follow.
- Next: scratch battery, sweeps under a heavy slot, then the final report to glitch-6b and a fresh opus-medium review (the ruling's threat model).

## What was built

- B1: `check_take.CHECKER_CONSTANTS` holds the ruled values, each with its source inline; `budgets` gains `finalize_wait_s` 180 and `poll_s` 3.
- 2.1.296 addition: `drive.py`'s RECORD_ vocabulary (round 3's plus three patterns, thirteen billing routes, seven API keys, one subscription token), appended at the end of drive.py so no cited line moves; round 3's tuples (bound to run_take's copies) unchanged.
- B2: `tests/test_checker_constants.py`: nine bindings plus K-closed, one witness per binding (21 witnesses, all red), the pinned-tree export sweep.
- B4: `finalize_wait_s` and `poll_s` in the take and walk ledger; `check_take.ledger_budget_problems` binds them from check4 and check4_walk.
- B5: check.json carries `checker_constants_sha256`; `pending_walk.checker_standing` keeps a graded walk out of coverage when it names a constant-bound reason, carries another or no digest, or has no readable check.json.
- B6: `prereg-draft.json` `checker_constants_ruling`, built by build_draft.py.
