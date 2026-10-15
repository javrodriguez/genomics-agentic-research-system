# Lane bootstrap-constants (Gap Study round 4): the first-walk bootstrap

_Started Thu 15 Oct 2026 01:08 EDT (`date`) by the bootstrap builder, assigned by glitch-6b (Lane-orchestrator) under Javier's standing delegation.
Clone `~/aegis-builds/gap4-bootstrap-20261015`, branch `gap4/bootstrap-constants-20261015`, base 89525f03 (the harness lane's head).
Ruling built: `plans/gap-study-round-4/first-walk-bootstrap-ruling-2026-10-15.md` (01:07 EDT) and glitch-6b's addition of the same morning (the 2.1.296 vocabulary from box ba6d7f14; auto-continuation stays off the origin list)._

## RESUME HERE

- 03:01 EDT: commits 93a98927 (build), 14f17457 (B4 on the check roads, walk_plan fixtures), aed13f75 (sweep fold); nothing pushed.
- Branch: every touched or constant-reading module green, one at a time after light-ok (logs in ~/aegis-builds/gap4-bootstrap-tools/logs-b1..b4).
- Merged scratch ~/aegis-builds/gap4-bootstrap-scratch = 383e5c2f + the three commits as patches (applied cleanly; build_draft rebuilt the draft byte-identical): 18 modules green (logs-s1), test_checker_constants green after patch 3; there box/preflight.STUDY_PATHS is filled and equals run_location's paths.
- Constants digest (both trees): 8fd8c39b2baf1050d9fbe6253dbfab2e3c93030f93da8059730be45ce4f37d7e.
- Sweeps under one heavy slot (bootstrap-6b, 02:36-03:00, released): every changed function or changed line; after the fold the only survivors are checker_standing's final `return None` (equivalent: the function ends there) and two mutants of environment_record's pre-existing stripped_names line (equivalent while drive.STRIPPED_ENV is empty; not this lane's line).
- Owed to athena: test_round4.py on the branch head and on the scratch; the unrestricted generated sweeps of check4, check4_walk and environment_record (this lane swept only its changed lines there).
- Next: glitch-6b's fresh opus-medium review (the ruling's threat model), then the integration lane merges this branch with the harness lane's.

## What was built

- B1: `check_take.CHECKER_CONSTANTS` holds the ruled values, each with its source inline; `budgets` gains `finalize_wait_s` 180 and `poll_s` 3.
- 2.1.296 addition: `drive.py`'s RECORD_ vocabulary (round 3's plus three patterns, thirteen billing routes, seven API keys, one subscription token), appended at the end of drive.py so no cited line moves; round 3's tuples (bound to run_take's copies) unchanged.
- B2: `tests/test_checker_constants.py`: nine bindings plus K-closed, one witness per binding (21 witnesses, all red), the pinned-tree export sweep.
- B4: `finalize_wait_s` and `poll_s` in the take and walk ledger; `check_take.ledger_budget_problems` binds them from check4 and check4_walk.
- B5: check.json carries `checker_constants_sha256`; `pending_walk.checker_standing` keeps a graded walk out of coverage when it names a constant-bound reason, carries another or no digest, or has no readable check.json.
- B6: `prereg-draft.json` `checker_constants_ruling`, built by build_draft.py.
