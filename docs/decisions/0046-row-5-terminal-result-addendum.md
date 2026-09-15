---
date: 2026-09-15
status: standing
kind: defect
touches:
  - infra/backup/row05.py
  - infra/compose/README.md
  - tests/test_row05_backup.py
symptoms:
  - signal during result finalization leaves empty restore log
  - failing restore invocation leaves PASS-only evidence
---
# Row 5 terminal-result addendum to 0045

0044 and 0045 remain byte-identical historical records. Round-2 review R5-F3
showed that 0045's catchable-interrupt guarantee exceeded its implementation:
result writing occurred outside the destructive phase's exception handler.

The interrupt-protected scope now includes the destructive restore, result
writing, stdout flushing and closing the retained append handle. A catchable
SIGINT, SIGTERM, SIGHUP or KeyboardInterrupt escaping that scope produces
`restore_interrupted` and a dated terminal FAIL with a nonzero exit. Pipeline
cleanup still occurs before recording the failure.

Result publication spans a filesystem log and stdout and is not atomic. If PASS
has already reached either destination, it cannot be retracted. Preserve those
bytes and append a terminal FAIL correction using the invocation's original start
date and RPO, with RTO measured at the correction. Its final row and nonzero exit
control the outcome; an earlier PASS for that invocation is not acceptance evidence.
The four-column result format, thresholds and destroy guards remain unchanged.

During this fallback, block SIGINT/SIGTERM/SIGHUP while reopening the append log
and recording/flushing FAIL. Restore the previous signal mask afterward; a pending
signal can still cause a failure diagnostic, but only after the dated FAIL exists.
This uses POSIX signal masking, consistent with the Bash/macOS/Linux execution
surface. It does not guarantee records after SIGKILL, host/power loss, or loss of
log storage. Concurrent operator replacement of trusted log paths is not supported.

`test_restore_finalization_signals` sends real OS signals through `main()` at
entry to result writing, after the filesystem log flush before stdout publication,
and after stdout publication before return. All three signals run at each boundary.
It checks nonzero status, preserved history, a terminal dated FAIL, stdout agreement
and append-only correction of any earlier PASS. SQL, checksum and archive work are
doubled; this proves result handling, not live PostgreSQL recovery. Existing tests
continue to exercise actual pipeline-child cleanup and RTO enforcement.
