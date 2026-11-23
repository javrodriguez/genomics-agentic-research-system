VERDICT: PASS

# Review of T4 group (a): PF, P0 and P0b (lane vendor-admission), range b0628cdc..e7496cf8

A fresh, independent reviewer, briefed by glitch-b5 on Javier's approved T4 ("vendor-t4: yes", Sat 17 Oct 2026). Written Sat 17 Oct 2026, 13:09 EDT.
Lane head read: 65f66226. That is the round-7 status commit, which touches only lane-reports/vendor-admission-LANE.md, sitting on e7496cf8.
Reviewed: the six T4 commits after the harness merge ed75b916 (cbf3c231 merged in): f4d43bd9 and 1fd17212 (PF), b8f88cc7 and be9942ea (P0), and 5c629760 and e7496cf8 (P0b).
Read first: the round-7 group (a) summary, the v4 plan's sections 6, 7 and 9, vendor-T4-TABLE.md, and REVIEW-vendor-T4-PLAN-36ce125.md.
No code, test or fixture was changed. Every run used python3.12, from detached worktrees of each commit, with TMPDIR outside the clone.

## Test counts
Red first: each red commit's own tree is its parent's code plus the new tests.
- f4d43bd9, test_vendor_check: 13 tests, errors=47. The errors are real: VENDOR_PENDING_ROWS, vendor_pending, vendor_rows_problems and vendor_shapes_problems are absent.
- f4d43bd9, test_freeze_shapes: 9 tests, failures=5, errors=5. The old refusal carries no "leg i:", leg ii and iii are absent, and the witness sites are missing.
- b8f88cc7, test_take_checker_dispatch: 5 tests, failures=3, errors=1. P0-vendor fails because the old take_checker reads the codex and gemini take with Claude readers. Both witnesses fail, and CHECKER_ENTRIES is absent. P0-claude passes on the old drive.py, which is the parity check against the old road.
- 5c629760, test_pin_for_vendor: 2 tests, failures=1. The codex and gemini rows hit a bare KeyError.

Green at e7496cf8:
- test_vendor_check 14
- test_freeze_shapes 9
- test_take_checker_dispatch 5
- test_pin_for_vendor 2
- test_vendor_script 6
- test_checker_body 30
- test_check_take 15
- test_drive_loop 27
- test_drive_commit 31
- test_walk_wiring 20
- test_walk_recheck 17
- test_batch 118
- test_native_reader_registration 7
- test_vendor_admission 10
- test_vendor_admission_regrade 3
- test_pending_walk 23
- test_vendor_checker_road 5
- test_walk_grade_seam 3
- test_routing 297
- test_codex_adapter 55
- test_gemini_adapter 143
- test_walk_runner, classes R5Bootstrap, R5Round3, R2WalkCheck, R8WalkRoad, R9RealGrade, R12Pending, R13Recheck and R10Guards: 55 tests, 0 failures.

Gates:
- Every line of checks.d/vendor-admission.txt exits 0, including the three check_vendor_sources lines.
- freeze --check, walk_regrade --check, copy_manifest --check and build_draft --check are clean.

Not run here: test_walk_runner as a whole, test_round4, the generated shards and the athena battery. Those are glitch-b5's, on the home server.

## Scope, item by item
1. Each piece matches the plan and went red first for a real reason (counts above).
   - The green PF commit's test edits fix the red commit's settled() helper, which named a fixture that did not exist. They also add one case: leg i alone, with legs ii and iii settled, still refuses.
   - No assertion was weakened. The summary names this move.
2. PF.
   - Leg i is unchanged. Leg ii is vendor_reader_problems: VENDOR_CHECK_SHAPES_SOURCE must read "recorded", and vendor_rows_problems is appended whatever the source word. Leg iii is registration_problems, with RegistrationRefused caught and named.
   - Each refusal names the arm, the leg and, for leg ii, the row. The committed draft prints "arm G (gemini): leg ii: T-11 inherited-context is PENDING".
   - A SAME row needs a RECORDED fixture that exists, labelled on its CLI. A NOT COMPARABLE row needs a ruling. Both need a reader that is a callable global, and any extra or missing key refuses.
   - I found no road by which an arm O or G row freezes with legs ii or iii open. Harness keying is T3's and unchanged. The call sits in main before any write.
3. vendor_pending is the only place the text "no vendor reader yet" occurs in the evals/gap-study-4 Python code (grep), and nothing calls it yet.
   - Once a key is settled, the helper calls only the very object the row names (name match plus identity against globals). It refuses a reader that returns anything but a list of strings.
   - VP-keys reads every call site from the AST. Its live check is a subset check, a departure the summary names, which P2 turns into equality. Its mutants go red.
4. P0.
   - The diff touches drive.py in take_checker alone (3602-3606).
   - _claude_code_side makes the same three calls in the same order, and _claude_code_entry makes the same check4 and check4_walk calls with the same arguments. The one departure is take=take, which the summary names.
   - The side readings still run before the entry, as before. checker_for runs before any reader, and the drive.py witness that moves the readings in front of it goes red.
   - P0-claude compares both roads, with and without a cross-check, against the direct calls, and passes on the old drive.py too.
5. P0b.
   - PinProfileMissing names the harness, the model and CP5. It is still a KeyError for any caller that catches one.
   - The behaviour is unchanged for an existing profile, an empty one included. The witness that restores the bare lookup goes red.
6. Source lists and spans.
   - drive.py is in READER_SOURCES and CODEX_SOURCES. Ruling R-3 covers its one edit, and no acceptance record is committed, so production_readers() is {} and nothing re-binds.
   - check_take.py, freeze.py and batch.py are in neither list (check_vendor_sources).
   - check_take.py is appended above `if __name__` only, so R5Bootstrap's prefix and span checks pass with no BOOTSTRAP_SPANS entry. R-1's span work stays with P3, as the summary says.

## Findings
None at MINOR or above.

## NITs
- 1. freeze.py:350-358: registration_problems catches only RegistrationRefused. A git binary missing raises FileNotFoundError out of production_readers (reproduced with a patched registry). main's `except (ValueError, KeyError, OSError)` turns it into "freeze: REFUSE: git", which is not a traceback, but it names no arm or leg.
- 2. check_take.py:3834-3835: vendor_row_problem accepts any callable global as a row's reader, a class or an imported name included (reproduced: "Path" and "CheckRefused" pass). Its docstring says "a function of this module". This is safe at run time, because vendor_pending then refuses a non-list return, but the check is looser than its words.
- 3. Plan section 7's fixture binding also asks that "recorded" refuse while any READER item lacks a RECORDED fixture. No READER items exist before P1 and P2, so nothing binds that half yet. The summary names only the SAME-row half as landing with P2; name this half as P1's or P2's too.
- 4. The lane summary says test_vendor_check has 15 tests. Here it is 14, which is also its count of `def test`.
- 5. a3ca7cb0's message carries a session link line. The summary already names this.
