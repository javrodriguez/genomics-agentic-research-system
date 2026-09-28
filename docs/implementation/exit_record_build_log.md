# Local exit-record build log

This is producer evidence for the local exit-record lane (change record 0195), not a decision record, approval, or merge.
The branch is `exit-record` and the baseline is `81c0d71`.
The producer is Claude (`claude-opus-5-5`), not Codex, by the coordinator's ruling for this run; the same-model cost is stated in 0196.
Every clock time below was read from `date` on the host named, 28 September 2026, US Eastern time.
Every Python command ran with `TMPDIR` set to the lane's own scratch folder, outside the clone's git tree and outside the system temp folder.

## Pre-flight: the freeze reproduces at the baseline

A probe ran the baseline's own `LOCAL_RUNNER` string under `ulimit -f 0` with a job body `exit 17` (normal path) and a body that TERMs its runner (trap path), and read the exit record once the runner's pid had gone.
Development Mac, bash 3.2.57, Python 3.8.2, 05:34:35: both paths left the record existing and empty.
Build node owner account, bash 5.2.37, Python 3.13.5, 05:34:58, a bundle clone of `81c0d71`: both paths left the record existing and empty.
The primary freeze (C1, C5) was therefore used; the controlled-runner fallback was not needed.

## Red commit `b9b69fb`

Adds `gars/tests/test_local_exit_record.py` (C1-C5) and the empty-record subtest in `test_lifecycle_cancel.py`.
Development Mac, 05:40:43: `test_local_exit_record` `Ran 5 tests`, `FAILED (failures=4)` (C1, C2, C3, C5; C4 passed as the honest control); `test_lifecycle_cancel` `Ran 11 tests`, `FAILED (failures=1)` (the `code=''` subtest).
Build node owner account, 05:40:34: `test_local_exit_record` `Ran 5 tests`, `FAILED (failures=4)`, the same four.
C3 is red at the baseline as well as C2: besides the state it asserts that the pid is checked once, which the baseline never reaches for an existing record.

## Fix commit `505b0ac`

Changes only `gars/_system/executorlib.py`: the runner string, one comment, and the reader's empty-record branch.
Under the same freeze at the fix, both paths leave no record and one empty `submit.sh.local.exit.XXXXXX` sibling (R1), on both hosts.
Development Mac, 05:38:59-05:40:04, one module at a time, each `OK`: `test_local_exit_record` (5), `test_lifecycle_cancel` (11), `test_executor_env` (6), `test_execution_policy` (7), `test_lifecycle_executor` (16), `test_approval_forgery` (12), `test_protected_paths` (6), `test_policy_pins` (4), `test_stage03_execution` (17), `test_status_writer` (10), `test_failure_classification` (5).
Build node owner account, 05:40:32: `test_local_exit_record` (5) and `test_lifecycle_cancel` (11) `OK`.
No whole suite has run on this branch; the landing's suite runs, once, on the final merge.

## Mutation proof at the fix head

Each mutation edits `gars/_system/executorlib.py` (the file the tests import) through a substring asserted to occur exactly once, runs `test_local_exit_record` alone, and is restored from a byte backup verified by sha256 (`e3d16bf0b4b60bf7a3b42a52098351541553615c4cfe3d7e1798ed3ca693fbeb` at `505b0ac`).
Development Mac, 05:41:18-05:41:30, all six killed by the named test:
(i) the writer back to `echo $? > "$3"`, killed by C1;
(ii) the `&& mv` dropped, killed by C4;
(iii) the trap back to `echo 143 > "$3"`, killed by C5;
(iv) the reader returning `FAILED` for an empty record, killed by C2 (and C3);
(v) the reader returning `RUNNING` without the pid check, killed by C3;
(vi) `code=$?` captured after `mktemp`, killed by C4.
