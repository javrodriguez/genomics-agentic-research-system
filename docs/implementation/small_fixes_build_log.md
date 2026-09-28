# Small-fixes bundle build log

This is producer evidence for the small-fixes bundle (change record 0200), not a decision record, approval, or merge.
The branch is `small-fixes` and the baseline is `0d9954c` (the local exit-record landing, 0195).
The producer is Claude (`claude-opus-5-5`), not Codex, by the coordinator's ruling for this run; the same-model cost is stated in 0201.
Every clock time below was read from `date` on the development Mac, 28 September 2026, US Eastern time.
Every Python command ran with `TMPDIR` set to the lane's own scratch folder, outside the clone's git tree and outside the system temp folder.

## Scope of the bundle

Three items were brought to this lane; one is built.

1. **Built:** the local job record and the stage-03 launcher, published by rename (0200).
2. **Not built:** the two gap-study-2 scripts that call stage 00 `finalize` without `--data-class` and `--purpose` (`controls/run_controls.py`, `fixtures/gen_project.py`) are pinned by git blob and sha256 in that study's frozen `prereg.json`, and listed in its `freeze.py`; both equal their pins at the baseline. Editing them would move a frozen pin.
3. **Not built:** the status line "pre-freeze. Nothing here has been graded" in `evals/gap-study/` and `evals/gap-study-2/` (README and PROTOCOL of each). Round 3's `evals/gap-study-3/copy_manifest.py` pins both folders whole to `bf065fe`, in the committed and the working tree; one appended line in round 2's README made its `--check` exit 1 (09:30, restored byte-for-byte). The graded results are published in `docs/EVALS.md`.

## Red commit `a09b829`

Adds two rows to `gars/tests/test_r164_writer_recovery.py`: `executorlib._local_submit` (the detach answered in-process with pid 4242, so no job starts) and `executorlib._analysis_launcher` (the uuid pinned; a kept `#SBATCH` directive carries a byte that is not UTF-8).
Python 3.13.2, 09:32: the two rows `Ran 2 tests`, `FAILED (failures=8)`: for each row the write, fsync, replace and first-write steps fail (a half write on the published name; the fsync and rename faults never reached); the refused open passes, the honest control.

## Fix commit `03ea07c`

Changes only `gars/_system/executorlib.py`: the job record through `workspace.atomic_open`, the launcher through the new `_publish_bytes`.
The two rows, 09:33: `Ran 2 tests`, `OK`.
One module at a time, 09:33:51-09:34:40, Python 3.13.2, each `OK`: `test_lifecycle_executor` (16), `test_lifecycle_cancel` (11), `test_local_exit_record` (5), `test_executor_env` (6), `test_status_writer` (10), `test_venue_policy` (16), `test_stage03_execution` (17), `test_execution_policy` (7), `test_r164_writer_recovery` (51).
`test_r164_writer_recovery` (51) is also `OK` under Python 3.9.6 and 3.12.
No whole suite has run on this branch; the landing's suite runs, once, on the final merge, and the README and DEVELOPMENT totals are measured there.

## Mutation proof at the fix head

Each mutation edits `gars/_system/executorlib.py` (the file the tests import) through a substring asserted to occur exactly once, runs the two new rows alone, and is restored from a byte backup verified by sha256 (`f1d97ada05ca872c45e7b8a676046fa8855a9eebee0e72543d2e9ec99aef67e9` at `03ea07c`).
Development Mac, 09:35, all five killed:
(i) the job record back to a plain `open`, killed by the record row (write, fsync, replace, first-write);
(ii) the launcher back to `write_bytes`, killed by the launcher row (write, fsync, replace, first-write);
(iii) `_publish_bytes` without its fsync, killed by the launcher row (fsync);
(iv) `_publish_bytes` keeping its temp on failure, killed by the launcher row (write);
(v) `_publish_bytes` writing the published name directly, killed by the launcher row (open, first-write).

## Review round 1 fixes

Review r1 (a fresh Claude Code context, Opus 5.5, no-remote checkout) read APPROVE WITH CHANGES: one MINOR, four NOTE.
F-1 MINOR: 0200 said the truncated launcher was "later" refused with R-135, as 0087 observed; 0087 never names R-135, and `_submit_analysis` catches the write error and refuses that same submission at once. Both passages are reworded.
F-2 NOTE, taken: the launcher row's clean run now asserts the kept directives, including the byte that is not UTF-8, survive byte-for-byte.
F-3 to F-5 NOTE, no change: the shared fixture lets a leaked temp mask later steps (the table's existing shape; mutation (iv) is still killed); the index row and 0201 are written at landing; temps left by a SIGKILL are harmless and inside the guard's protected paths.
After the fixes: `test_r164_writer_recovery` `Ran 51 tests`, `OK`; the mutation proof re-run killed 5 of 5.
