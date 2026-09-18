---
date: 2026-09-15
status: standing
kind: defect
touches:
  - infra/backup/row05.py
  - infra/compose/README.md
  - tests/test_row05_backup.py
symptoms:
  - successful slow backup rejected as timestamp_drift
  - interrupted destructive drill leaves no dated FAIL row
  - fresh test imports change repository bytes
  - runtime scrub removes PG_DATA_DIR
---
# Row 5 review reliability addendum to 0044

Decision 0044 remains unchanged. This dated addendum clarifies its timestamp,
connection and failed-restore statements after review R5-F1–F3 and R5-N1–N2.

- Archive mtime is deliberately normalized to dump start before publication.
  Filename, manifest and archive mtime therefore retain the existing 300-second
  agreement guard regardless of dump duration. RPO still uses manifest dump start.
  The existing SHA-256 sidecar retains completion mtime; candidates whose sidecar
  completed at or after drill start are excluded. No manifest schema changes.
  rsync preserves both timestamps. Destination clocks and metadata are trusted
  operator inputs, not authenticated scheduler evidence.
- The restore log is opened for append before destruction and its handle retained
  through the result. Catchable interrupts (SIGINT, SIGTERM, SIGHUP and Python's
  KeyboardInterrupt) after destruction begins produce `restore_interrupted` plus
  the standard dated FAIL row, after pipeline child cleanup. Other recoverable
  restore errors likewise fail. The unconditional failed-restore wording in 0044
  does not cover SIGKILL, host/power loss or failure of log storage after opening.
  Missing results never establish a successful drill.
- Identity comparisons cover stable aliases. Separate connections are not pinned
  to a checked server across DNS/proxy changes or database-dependent routing of
  the `postgres` admin connection. Only direct, stable endpoints are supported;
  stronger binding is needed before supporting connection-routing proxies.
- Container mode preserves PG_DATA_DIR in the runtime scrub and requires an
  existing, absolute directory outside Git with no symlink components, consistent
  with the explicit Compose storage contract in 0044.
- The test module sets `sys.dont_write_bytecode` before dynamic imports. Mandatory
  scratch refusal and repository-byte invariants remain intact. No CI file is
  changed: the exact single-setting merge action remains an owner ruling, recorded
  in the round-1 change report.

Regression evidence and remaining operational limits are recorded in
`docs/implementation/row_5_change_report.md`. These changes do not establish
PostgreSQL integration, hardware acceptance or an external-human seal.
