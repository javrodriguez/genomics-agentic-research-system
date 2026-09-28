---
date: 2026-09-28
status: standing
kind: decision
touches:
  - gars/_system/executorlib.py
  - gars/tests/test_local_exit_record.py
  - gars/tests/test_lifecycle_cancel.py
symptoms:
  - a local job that finished is recorded as a bare FAILED with no exit code, and no later poll repairs it
  - a local job that exited 0 reads FAILED; a transient exit code reads as a workflow failure, and R-152 refuses the retry it should allow
  - test_execution_policy's test_prepared_local_failure_refuses_unclassified_retry reads FAILED where it expects FAILED:EXIT_17, rarely and under load
---
# The local executor publishes its exit record by rename, and an empty record is not a verdict

Follow-up to the executor-env lane ([0170](0170-executor-env-allow-list-read-from-gars-env.md)) and to the defect named in [0181](0181-science-fault-module-one-control-per-case-and-a-bounded-pool.md) and [0186](0186-fs-vocabulary-0185-delegated-approval-of-protected-change.md), whose bytes are unchanged.
Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 and ruled by the lane's coordinator on 28 September 2026; no sentence in this record is the owner's.
0196 is the lane's delegated approval of the protected change; this record does not write it.

## Context

The `local` backend detaches `LOCAL_RUNNER` (`gars/_system/executorlib.py`), which ended with `wait "$worker"; echo $? > "$3"`.
`_local_submit` unlinks any old exit record first, so the redirection **creates** an empty file and the builtin `echo` fills it a moment later; the TERM trap's `echo 143 > "$3"` has the same shape.
`_local_status` returned `"COMPLETED" if code == "0" else ('FAILED:EXIT_' + code if code.isdigit() else 'FAILED')` for any existing record, so an existing but empty record read as a bare `FAILED`, and the pid check below it was never reached (the runner subshell, whose pid is the job id, is still alive during the `echo`).

What a poll in that window did, all through `_scheduler_status`:

1. **`status()` (the durable harm).** The job record was not yet terminal, so it stored `FAILED`, `record_failure` wrote the class `classify('FAILED', None)` = `workflow`, and the stage's `STATUS` became terminal. Every later poll skips a terminal record, so the verdict was permanent: an exit 0 read `FAILED`, `EXIT_17` lost its code, a transient code (104, 130-145) became `workflow`, and `submit()`'s retry path refused (R-152, "only transient failures retry") a retry the real code would allow.
2. **`cancel()`.** The torn read made the job look terminal, `FAILED` was persisted as above, and cancel answered "cancel refused: recorded state FAILED". A job ended by a stray TERM could be recorded bare `FAILED` instead of `FAILED:EXIT_143` (`transient`).
3. **Stage 03 and the completion gate (transient, not persisted).** The analysis resubmit check read the torn record as terminal (the worker had in fact ended, so no overlap follows); the marker check and `wrapperlib`'s completion gate refused once (R-135, `completion_gate`), and a later call passed.
4. Nothing raised and nothing looped; the harm is a wrong, sticky verdict (1) and a one-off refusal (3).

The window is microseconds per job, and it had already turned two evidence runs red: 0181's first mode B run and 0186's first mode C run, each paid for with a solo re-run.
`gars/tests/test_executor_env.py` already polled with `exit_file.is_file() and exit_file.read_text().strip()`, a test-side workaround for the same empty read.

**Reproduction.** Run the real `LOCAL_RUNNER` under `ulimit -f 0`: the redirection's `open` succeeds and the first byte ends the runner with SIGXFSZ, which freezes the state a racing reader would see.
At `81c0d71`, with a job body `exit 17` and with a body that TERMs its runner, the record was left existing and **empty** once the runner had gone, on the development Mac (bash 3.2.57) and on the build node's owner account (bash 5.2.37), 28 September 2026.

## Decision

**Ruling 0195 (the lane's).**

1. **Writer: publish by rename.** `LOCAL_RUNNER` captures the job's status into `code` before anything else runs, writes it into `mktemp "$3.XXXXXX"` (a sibling in the same directory, with an unpredictable name, created exclusively, so a planted link cannot redirect it) and renames that onto the record with `mv -f`; rename within one directory is atomic. The TERM trap publishes 143 the same way. A reader now sees either no record (the pid check decides: `RUNNING` while the runner lives) or one full line.
2. **Reader: an empty record is not a verdict.** `_local_status` treats an existing but empty record as no record and falls through to the pid check: runner alive, `RUNNING`; runner gone, `FAILED` (a runner killed before it published left no code, the honest reading, as for an absent record). Non-empty, non-digit content still reads `FAILED`. This half covers jobs detached by the old runner string before this lands, and it is the one branch that turned a torn read into a sticky verdict.
3. The comment above `LOCAL_RUNNER` names the rename and this record.

In-spec choices (the lane's): writer and reader both, not the writer alone (jobs already detached keep the old writer until they end); a `mktemp` sibling, not a fixed `"$3.part"` name (a plantable path outside the protected list); the exit record only, not the local job record `jobs/<pid>.json` or the other non-atomic writers, which stay their own item.

Rejected alternatives: a `sync` or a pause in the reader (still racy); a lock file (a second record to tear); writing in `$TMPDIR` and moving it (not atomic across filesystems).

## What this does not close

- **R1** A runner killed between `mktemp` and `mv` leaves a `submit.sh.local.exit.XXXXXX` file beside the script. No reader reads it and `_local_submit` does not sweep it.
- **R2** The temp name is not in the guard's protected-path list (`guard_hook.py`) or `gars/.claude/settings.json`'s; it exists for microseconds under an unpredictable name and is created exclusively, and the published name stays protected. Widening those lists is a guard change, out of scope.
- **R3** Pid reuse after the runner exits (pre-existing, unchanged).
- **R4** A partial digit string (`1` of `17`) cannot be told from a full code by any reader; the writer half is what closes it, and the reader half covers the empty case only.
- **R5** `mktemp` creates the record with mode 0600 where the redirection used the umask (typically 0644); every reader runs as the job's owner.

## Test

`gars/tests/test_local_exit_record.py` is new, five tests:
C1 `test_torn_write_never_publishes_an_empty_record` and C5 `test_cancel_record_is_published_whole` freeze the real runner under `ulimit -f 0` (normal path, trap path) and require the record to be absent or one full integer line;
C2 `test_empty_record_with_live_runner_reads_running` and C3 `test_empty_record_with_dead_runner_reads_failed` hold an empty record with a live pid (`RUNNING`) and a dead one (`FAILED`, the pid checked once);
C4 `test_status_keeps_the_exit_code` submits a prepared local stage that exits 17 and polls `status` with no pause until terminal, requiring `FAILED:EXIT_17` and the stored class `classify('FAILED:EXIT_17', None)`.
`gars/tests/test_lifecycle_cancel.py`'s `test_local_exit_file_and_dead_pid_are_terminal` gains an empty-record subtest (dead pid, `FAILED`, the pid checked once).
At the red commit C1, C2, C3, C5 and the new subtest fail on both hosts; C4 passes there, as the honest control (tight polling makes the race likely, never certain).
They must fail when the writer goes back to `echo $? > "$3"` (C1), when the `mv` is dropped (C4), when the trap goes back to `echo 143 > "$3"` (C5), when the reader returns `FAILED` for an empty record (C2), when it returns `RUNNING` without the pid check (C3), and when `code=$?` is captured after `mktemp` (C4).
The lane's mutation proof at the branch head killed all six, each by its named test.
The landing's evidence is recorded in 0196.

## Status

Standing. The change record for the local exit-record race; its protected-change approval is 0196.

## Date

2026-09-28
