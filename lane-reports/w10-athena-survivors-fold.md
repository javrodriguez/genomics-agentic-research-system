# Lane w10-walk-runner: fold of athena run gap4-w10-5ff8b2e-20261013T003648Z

Written Tue 13 Oct 2026, 00:15 EDT (`date`), by the lane's only writer (Claude Opus 5.5), sent by glitch-2f (the Lane-orchestrator, under Javier's standing delegation).
Branch `gap4/w10-walk-runner`, base `5ff8b2e7`.
Nothing was pushed, merged or spent; no athena run was started.
No model, network, Docker, credential, salt or holdout was used.

## What athena found

The run (log `athena-suites/gap4-w10-5ff8b2e-20261013T003648Z/run.log`) failed for two reasons.

1. test_round4's battery rule: `walk_mutation.py is not test_*.py; the battery would never run it` (test_scaffold.TheBattery.test_a_module_with_no_test_fails_even_beside_a_live_one).
2. The generated sweep: 533 mutants in 12 shards, 101 unique unlisted survivors.

A third fact, not a w10 test failure: step 2 (run_checks) ended `rc 124 reason timeout`.
The 12 shards took about 64 minutes of it (303-331 s each).

## 1. The battery rule

`test_round4.module_problems` fails any `.py` in `tests/` that is neither `test_*.py` nor named in `HELPERS`.
`HELPERS` is the rule's own place for a helper, and `walk_mutation.py` is one: test_walk_runner imports and runs it (G1, `--generated-mutants`).
So `HELPERS = ("walk_mutation.py",)`, with a comment naming the module that runs it.
The rule itself is unchanged: any other non-test `.py` in `tests/` still fails it.
test_round4.py is lane w1a's file; the edit is recorded as departure w10-7 in w1a's fragment (no ownership transfer), and named in this lane's fragment.

## 2. The 101 survivors

They fell into five classes, so the fold is one test design, not 101 one-offs.
`R11Units` (new) feeds each walk-road function one bad input directly, with no walk, and reads the refusal's type and words; it runs first under `--gen-mutant`.
R8WalkRoad gains six tests for the check_take survivors.

Killed by class (94):
- **Readers with no direct refusal test (55).**
  Each was reached only on its clean road.
  - `run.walk_row` (14): each ledger key off its entry, pressure or repeat missing, both None, both set, a cell that is not the ledger's.
  - `run.died_before_turn_one` (18): a refusal record, a failed preflight with and without named checks, a passed one, a turn record, other `.jsonl` and `turn-` names, an empty folder.
  - `run.grade_walk` (4): a folder given as a string; a ledger with no first agent turn.
  - `drive.walk_files` (13): a symlinked folder, a file in place of the folder, a relative path, a symlinked record, a FIFO record, a ledger with no pre-turn record, a turn record with no ledger.
  - `walk_runner.check_record` (6): no records, `checker_reasons: null`, a route refusal's text.
- **Type guards only ever handed the right type (13).**
  - check4_walk: a tuple script, a Path run tree, an empty run tree (3).
  - walk_identity_problems: an identity that is a list or a string, and the identity shown in the refusal (2).
  - `_run_one`: a row of None or a walk id of 5 (4); a reason of 5 (1).
  - check_walk: check() returning nothing (1); an environment record that is missing or a list (2).
- **Runner roads with no test (19).**
  A launch that failed after making things (with and without a removal failure), a container that could not be removed, a driver with another check file, a grade refusal, a committed walk's result.
  Also `_publish` on a missing folder (3) and a failed deletion (1), and `run_walks` with two committed walks (1).
- **Values never read back (7).**
  The walk id in run_one's result; write_check's returned path; check4_walk's event counting (2); the design's pre put back after check4_walk; the environment record named by the pre's `file`, and the default name when the pre has no block (2).

One-off: none.
Every kill above is one of the class tests, by assertion (counts by test are in the evidence below).

EQUIVALENT (7), each listed in `EQUIVALENT` with its reason:
- `walk_runner._publish:delete:L14:C4:e3e767f5`, `walk_runner._remove:delete:L7:C4:e3e767f5`: a function's last `return None`; deleted, it falls off its end and returns None.
- `walk_runner._record:delete:L4:C8:e3e767f5`: `return None` in the last except; deleted, control falls off the function's end, which returns None.
- `walk_runner._run_one:drop-0:L2:C7:2b55246e`: run_one, the only caller, passes `walk = row.get('walk')` only when row is a dict, else None, so `not isinstance(walk, str)` alone already holds for a non-dict row.
- `walk_runner.run_walks:cond-false:L12:C11:aa50c7d9`, `delete:L12:C8:35f36fd2`, `delete:L13:C12:93cfda8b`: the `if launch-refused: continue` is the loop body's tail but for the HELD test, which a launch-refused state never meets.
  If the reviewer prefers, the three go away by deleting the redundant `if` (no behaviour change); I kept the documented branch.

No code bug was found: every survivor was a test gap or an equivalence.
No production code changed in this fold.

Order: `GENERATED_ORDER` now runs R11Units first and R8WalkRoad (one walk for all its tests) before R4Held and R3DeadWalk (one or more walks per test).
On the Mac a check_take mutant took about 2 minutes to reach R8 behind R4 and R3; now it reaches R8 after one walk.
This should shorten athena's shards too, which matters given step 2's timeout.

## Evidence (Mac, python 3.13, `mac_slot.py light-ok` before each batch)

- `test_walk_runner.py` whole, on the code: `75 run, 0 failures, 0 errors, 0 skipped` (55 before, 20 new).
- The 94 target survivors, `--generated-mutants --timeout 480 --only <94 ids>`: `533 generated (0 dropped, not compiling), 94 run, 94 killed, 0 equivalent (listed), 0 survived unlisted, 0 listed but killed, 0 inconclusive`.
  Each kill is by a new test (R11Units 83, R8WalkRoad's new tests 11; the counts are by first failing test).
- The 7 equivalents, `--only <7 ids>` (each runs the whole module): `533 generated (0 dropped, not compiling), 7 run, 0 killed, 7 equivalent (listed), 0 survived unlisted, 0 listed but killed, 0 inconclusive`.
- The battery rule: `test_round4.module_problems()` returns `[]`; `test_scaffold.py TheBattery.test_a_module_with_no_test_fails_even_beside_a_live_one` OK (athena's red is the run log).
- Gates: `copy_manifest.py --check` exit 0 (300 files, 48 fragments); `lint_language.py` clean (92 inputs); `lint_pooling.py` clean (92 files).
- Not run on the Mac: the whole battery and the full 533-mutant sweep (athena's).

## checks.d

`checks.d/w10-walk-runner.txt` is unchanged: the twelve shard lines still cover all 533 mutants, and the new tests run inside every line.

## What athena must run

- The full battery again on the new head, including test_round4 (the battery rule) and the 12 shard lines.
- Expected: test_round4 clean of the helper line; each shard `0 survived unlisted`, with the 8 EQUIVALENT entries (1 old, 7 new) reported as equivalent.
- The run_checks timeout (rc 124) is the orchestrator's call: the shards may be faster with the new order, but I have not measured that on athena.
