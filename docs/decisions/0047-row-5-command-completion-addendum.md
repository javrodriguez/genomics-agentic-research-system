---
date: 2026-09-15
status: standing
kind: defect
touches:
  - infra/backup/row05.py
  - infra/compose/README.md
  - tests/test_row05_backup.py
symptoms:
  - signal at drill or main return leaves PASS-only restore evidence
  - broken stdout pipe prevents retained FAIL correction
---
# Row 5 command-completion addendum to 0046

0044–0046 remain unchanged. Round-3 review R5-F3 demonstrated that protecting
result writing and log close did not protect return events from drill or main.
It also reproduced a broken stdout pipe that left only a retained PASS.

The destructive invocation retains its start, monotonic start, RPO, failures and
append handle on its configuration. The CLI signal-handler closure keeps that
configuration alive through command exit. While the handle is open, signals unwind
through the existing restore and child-cleanup handlers. Once the handle is closed,
the signal handler itself appends the dated FAIL correction, then exits nonzero.
It does not depend on a returning function catching an exception at its return event.
The closed-handle branch runs after pipeline cleanup; it performs no database work.

Restore result rows are appended before stdout diagnostics. An OSError during
stdout publication disables the failed stdout stream (including its shutdown flush),
appends a dated FAIL with stdout publication disabled, and returns nonzero. The
correction retains the original start and RPO and measures RTO again. Failure
recording blocks SIGINT, SIGTERM and SIGHUP and restores the previous mask afterward.
A writable stdout receives the usual diagnostics and result; retained failure
evidence does not depend on stdout being writable.

Existing PASS/history bytes are preserved. The terminal row and command exit status
govern the invocation. The four-column schema, 24-hour RPO, 60-minute RTO and all
guards remain unchanged. Log paths/storage remain trusted operator inputs. SIGKILL,
host/power loss and loss or replacement of log storage remain outside the guarantee.

`test_restore_command_completion_signals` delivers SIGINT, SIGTERM and SIGHUP at
the drill return, main return and the caller's handoff to sys.exit. It verifies each
signal fired, nonzero exit, synthetic DROP/CREATE, preserved history, appended FAIL,
original start/RPO and terminal stdout agreement. `test_restore_closed_stdout_pipe`
closes a real pipe's only reader before launching the child, then verifies nonzero
exit and the retained PASS/FAIL correction. Both tests failed against the round-2
engine. Existing finalization, pipeline-child cleanup, log-preflight and RTO tests
also pass. SQL/archive/checksum work in the new tests is doubled; live PostgreSQL
and operational acceptance remain unverified.
