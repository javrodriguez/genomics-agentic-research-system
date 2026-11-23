# Lane w10-walk-runner: review round 3

Written Mon 12 Oct 2026, 15:24 EDT (`date`), by a fresh reviewer (Claude Opus 5.5), assigned by the Lane-orchestrator.
Reviewed: `f76d5c65..2cef87d0` on `gap4/w10-walk-runner` (fold 4858c41e, report 2cef87d0), against base f14ab57b.
No code was edited; this file is the only change.
Nothing was pushed, merged or spent; no model, network, container, credential, salt or holdout was used.

## Verdict

CHANGES (one MAJOR, four MINORs that loosen a check).

## What was verified (Mac, each run behind `mac_slot.py light-ok`, `timeout -s INT 120`, python3.13)

- Green: `tests/test_walk_runner.py`: 43 run, 0 failures, 0 errors, 0 skipped.
- check_take.py append-only against f14ab57b: the base's bytes up to `if __name__` are a byte prefix of 2cef87d0's, the two `__main__` tails are equal, 8,846 bytes are appended, the working file is the committed one (sha256 prefix 31e6b5ba0363e896), and the file is unchanged since adea27d3 (round 2 checked the same bytes).
  R5 (round 3's walks under the base and this module) is green in the run above, so round 3 stays byte-identical.
- DELETIONS witnesses through the whole real suite (not the bound method alone), 13 of 31 across all three functions, via a scratch harness that sets the module's own `SELECTED` and runs every test class (`scratchpad/w10r3/mut.py`):
  - check_walk: del-cw-session, del-cw-no-ledger, del-cw-environment-row, del-cw-checkout, del-cw-snapshot, del-cw-memory;
  - check4_walk: del-c4-cell, del-c4-script, del-c4-pending, del-c4-event-disagree, del-c4-tree;
  - walk_identity_problems: del-wi-unreadable, del-wi-not-own.
  Ten ran the whole suite inside the 120 s cap: each red by assertion, 0 errors, failing C1Coverage plus its bound method (and, for del-cw-environment-row, both environment row tests; for del-wi-not-own, both identity tests).
  Three (del-c4-pending, del-c4-event-disagree, del-c4-tree) hit the 120 s cap while the Mac's load rose above 16; each was re-run through the module's own `--witnesses` (bound method only) and is RED.
  Note: every deletion in the three functions is also red by C1 alone, so the whole-suite run proves the behavioural binding only through the bound method's presence in the failure list, which held in all ten.
- Fail-closed keep guard (W10-R2-2 fold): no clean walk is blocked by it.
  A kept config folder is never re-used (`make_config_dir` makes a fresh `cfg-<hex>` per take) and no launch reads the leftover; a retry is a new walk id and a new slot.
  The teardown record's `problems` is `take.cleanup` at teardown time (drive.py:2249), so a postflight failure written later does not make a clean drive look dirty.
- Ledgerless refusal (W10-R2-3 fold): drive.py writes the driver ledger exactly when `ok and turns` (drive.py:2323-2324), and turn records and the published transcript exist only on that road, so a legitimate pre-turn death never holds `transcript.jsonl` or `turn-N.jsonl`; no clean walk is refused by it.
  run.py's turn-name test (`turn-*.jsonl`) is broader than drive's `STREAM_NAME`, which is fail-safe.

## Findings

### W10-R3-1 MAJOR: everything the base check() finds on a walk can be discarded with the suite green

check_take.py:2244, in `check_walk`: `problems = problems[:-1]`.
It is an assignment, so C1's parse (append, `+=`, raise, `harness_guard`) never sees it, and no test feeds a walk whose fault is check()'s own (operator lines, fixture, leak, context, reach, project).
Every R8 single-change test targets a line check_walk or check4_walk adds after the call.
Mutant `problems = problems[:-1]` -> `problems = []` (scoped to check_walk): the whole suite, 43 run, 0 failures, 0 errors.
Repro on real data (`scratchpad/w10r3/probe_wiped.py`, the R8 rig, check4_walk on a copy of the committed w-0001):
- unmutated: the last operator prompt dropped reads `[operator-lines] operator turn 3 was never sent: ...`; one extra prompt appended reads `[operator-lines] operator turn 4 is not on the script: ... the operator improvising.`;
- mutated: both read `[]`, as clean as the clean copy.
So an operator who improvised, or a walk missing a scripted turn, is committed with `checker_reasons: []`.
This is D1's core ("read as a take is read"), and the same class rounds 1 and 2 found: C1 binds statement shapes, not the data flow from `check()` to the result.
Fix direction: R8 single-change tests for faults only check() sees (at least one operator-line fault and one fixture fault through check4_walk, plus one through the drive into check.json), and a C1 rule that the result of `check(...)` reaches the return only through the asserted slice (or a witness for that assignment).

### W10-R3-2 MINOR (loosens D2's launch guard): the identity's session clause can be deleted with the suite green

drive.py:3301, `walk_identity_problems`: `ident.get("session_id") != want or`.
C1 registers the `raise`, not its condition's clauses; R2's take-identity test has a row as well, so the row clause alone refuses it.
Mutant: that clause removed: 43 run, 0 failures.
Repro (`scratchpad/w10r3/probe_ident.py`): identity with w-0009's session id, row and row_commit None, run as w-0001.
Unmutated: `launch-refused` ("the walk's identity is not its own (ruling D2)").
Mutated: `committed`, registered as w-0001, with checker reasons operator-lines x2, fixture-binding, project-name, session-binding x2.
The checker still reads it as bad, so this is a second line lost, not a clean read; but D2 says a walk launches only under its own identity, and here one is committed under another's.
Fix direction: an R2 test with the wrong session id alone (row and row_commit None).

### W10-R3-3 MINOR (loosens a check): check4_walk's design-view cell binds only the half

check_take.py:2305: `(design.task_id, design.half) != (task_id, half_name)` -> `design.half != half_name`: 43 run, 0 failures.
R8's design-refusal case changes only the half.
On the drive road the script refusal just below it is vacuous (take_checker passes `wording_script=design.script`, drive.py:2680), so this cell check is the only binding of the design view to the row's task.
Fix direction: a design-refusal case with another task id and the same half.

### W10-R3-4 MINOR (loosens the fold's fail-closed keep): a teardown record with problems is read as clean by the tests

walk_runner.py:103, `clean_drive`: dropping ` and tear.get("problems") == []`, or dropping `tear.get("teardown") is not None and `: each 43 run, 0 failures.
The existing witness `teardown-unread` replaces the whole line, so neither clause is bound.
With either clause gone, a drive whose teardown recorded a problem (a container not removed, leftover agent processes, `end_take` failing) or recorded no teardown at all deletes the config folder, which the fold's own docstring says must be kept.
Fix direction: two R4 tests, a teardown record with one problem and one with `teardown: null`, each keeping the folder.

### W10-R3-5 MINOR (loosens D3's closed map and record): two D3 lines outside C1 are unbound

- drive.py:2930, `walk_files`: `if LEDGER_FILE not in tops and not (tops & set(WALK_PRE_TURN)):` -> `if False:`: 43 run, 0 failures.
  A folder with only grade.json and check.json (no ledger, no preflight, no refusal) then passes the closed map and the register's content rule; D3 says such a folder still refuses.
  The existing witness `dead-walk-ledger-required` only tightens the condition, so the deletion side is unbound.
- run.py:306, `died_before_turn_one`: `if doc.get("ok") is not True:` -> `if False:`: 43 run, 0 failures.
  A walk whose preflight failed is then committed with grade.json saying "its preflight passed and no turn ran"; R3 asserts only the word "preflight".
Neither is reachable through the runner today (only a hand-built folder reaches the first; the second needs the edit), and walks are never counted.
Fix direction: a hand-built recordless folder refused by walk_files; R3 asserting "preflight failed" in grade.json's why.

## Other mutants, not findings

- check4_walk `reasons.append(named[0])` -> `pass`, and walk_runner's check.json `checker_reasons` -> `[]`: each red, but only by `test_the_design_tree_through_the_drive` (the one test that reads a non-empty reason out of the drive).
- check4_walk `None in (design.half, design.script)` -> half only: green, but fail-safe (a None script is refused by the script check).
- walk_runner's reason guard (`if not isinstance(reason, str) or not walk_register.visible(reason)`) -> `if False:`: green; not probed further (WalkRepo's commit is the second line), named here as unverified.
- Kept from round 1's accepted design: after a drive-scan refusal the config folder is deleted (R4 binds it), a departure from S6b (e)'s "it goes only after a commit".

## Reviewer probes

`.../scratchpad/w10r3/`: mut.py and mut_extra.py (11 extra mutants), probe_wiped.py, probe_ident.py, batch.log and batch2.log, out-*.txt per run.

## Modules athena must run

- None beyond the lane's list; this commit is a review file only.
