# Lane bootstrap-constants (Gap Study round 4): the first-walk bootstrap

_Started Thu 15 Oct 2026 01:08 EDT (`date`) by the bootstrap builder, assigned by glitch-6b (Lane-orchestrator) under Javier's standing delegation.
Clone `~/aegis-builds/gap4-bootstrap-20261015`, branch `gap4/bootstrap-constants-20261015`, base 89525f03 (the harness lane's head).
Ruling built: `plans/gap-study-round-4/first-walk-bootstrap-ruling-2026-10-15.md` (01:07 EDT) and glitch-6b's addition of the same morning (the 2.1.296 vocabulary from box ba6d7f14; auto-continuation stays off the origin list)._

## RESUME HERE

- 04:09 EDT: head d7b27cda; nothing pushed. After af1e7fc6: 9229d10b (review fold: MAJOR 1, MINOR 2-5), b2946723 (second sweep fold), d7b27cda (athena merged-battery fold: sys.path leak, w6e-drive-commit.txt:6).
- MAJOR 1: R5's six bootstrap regions pinned by sha256, the constants region parsed to exactly one CHECKER_CONSTANTS assignment; the reviewer's inserted lambda passed the old R5 and is red now (gap4-bootstrap-tools/probe_r5.py).
- sys.path: the module imports the study in setUpModule; the stale-snapshot reproduction (gap4-bootstrap-tools/stale_snapshot.py) was red, is green; full discovery then this module and test_confounded_design in one process: green, evals off sys.path.
- w6e line 6: red at b2946723, green at d7b27cda (round 3's three functions byte-identical again; the appended block rebinds the four vocabulary names).
- Branch and merged scratch (383e5c2f + every commit as patches, a517c427): the touched and reading modules green, one at a time.
- Owed to athena: test_round4.py and every checks.d line on the head and on the merged tree; the unrestricted sweeps of check4, check4_walk and environment_record.
- Handed to the harness lane by glitch-6b: walk_builders.py 36-38 and 552-556.
- Next: the same reviewer checks closure; then the admission merge.

## What was built

- B1: `check_take.CHECKER_CONSTANTS` holds the ruled values, each with its source inline; `budgets` gains `finalize_wait_s` 180 and `poll_s` 3.
- 2.1.296 addition: `drive.py`'s RECORD_ vocabulary (round 3's plus three patterns, thirteen billing routes, seven API keys, one subscription token), appended at the end of drive.py so no cited line moves; round 3's tuples (bound to run_take's copies) unchanged.
- B2: `tests/test_checker_constants.py`: nine bindings plus K-closed, one witness per binding (21 witnesses, all red), the pinned-tree export sweep.
- B4: `finalize_wait_s` and `poll_s` in the take and walk ledger; `check_take.ledger_budget_problems` binds them from check4 and check4_walk.
- B5: check.json carries `checker_constants_sha256`; `pending_walk.checker_standing` keeps a graded walk out of coverage when it names a constant-bound reason, carries another or no digest, or has no readable check.json.
- B6: `prereg-draft.json` `checker_constants_ruling`, built by build_draft.py.
