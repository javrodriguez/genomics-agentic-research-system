---
date: 2026-09-14
status: superseded # partially by 0051-row-5-tests-skip-without-scratch-outside-ci.md
kind: decision
touches:
  - infra/backup/pg_backup.sh
  - infra/backup/restore_drill.sh
  - infra/backup/test_exposure.sh
  - infra/backup/row05.py
  - infra/backup/backup.env.example
  - infra/backup/canary.example
  - infra/compose/postgres.compose.yml
  - infra/compose/README.md
  - docs/ops/HARDWARE.md
  - docs/ops/restore-log.md
  - docs/ops/exposure-log.md
  - tests/test_row05_backup.py
  - tests/run_tests.py
  - .gitignore
  - README.md
  - DEVELOPMENT.md
  - docs/implementation/row_5_change_report.md
---
# Row 5 backup defaults and drill semantics

## Context

The frozen v1.0.1 guideline §18 row 5 and gap-review m-2 distinguish buildable
repository artifacts from the hardware exit. No homelab exists at implementation time.
0043 lives on `build/gars-row-01-design` and is not in this history.
Number note: the spec's `0001-data-handling.md` collides with the existing
0001 (layered context); row 8 must use the next free number. References to data
handling here mean that future record, never decision 0001.

## Decision

- Q6: MacBook over the tailnet; RTO 60 min / RPO 24 h. Drill freshness remains
  ≤ 30 days. Retain 14 encrypted archives per destination; never prune manifest history.
- Q7: Debian directly unless learning virtualization is declared a goal.
- Q9, verbatim: Who provides the external-human seal for public benchmark/fault claims and the public restore canary before pilot 2? *Default: development may use a reviewer agent in an `independent_context` sealed session, but public credibility claims remain `unmeasured` until a trusted scientist provides `external_human_seal` evidence.*
- `ENC_TOOL=auto` selects gpg, then age, or refuses `encryption_unavailable`.
  gpg is present on the build machine and CI; age is absent. gpg uses a symmetric
  passphrase file, age a recipients file and a separate identity file. Keys and
  passfiles stay outside git. No plaintext dump is written, including during restore.
- Container clients are the default: the host's pg_dump 14 cannot dump PostgreSQL 16.
  The container reads its secret; host mode uses PGPASSFILE and requires matching majors.
- A person or independent session writes `DRILL_CANARY_FILE` before destruction.
  Neither backup nor drill writes it. First non-comment CSV record is
  `canary,schema.table,column,value`; subsequent records are `schema.table,count,md5`.
  CRLF is accepted. All ordinary user tables must be covered exactly, excluding only
  `public.gars_drill_target`. Partition roots are counted once. Tables require primary
  keys; checksum_table hashes the ordered JSON row representation in PostgreSQL.
  Unsupported identifiers, missing keys, duplicated records and incomplete coverage refuse.
- Dry-run is default: validates configuration, candidate, archive readability, canary
  and both target guards, with no writes (including no log or fetched archive).
  `--destroy` requires the human-written `public.gars_drill_target` table and distinct
  resolved source/target address, port and database. No override exists. Guard queries
  and drop execute against the same configured endpoint, with bounded connections. Also compare PostgreSQL system
  identifiers plus database name, catching IPv4/IPv6 and interface aliases; both
  roles need read access to pg_control_system(), otherwise refuse.
- **Specification conflict:** §13.2 deletes the primary, whereas the owner's explicit
  safety rule prohibits restoring onto an identity equal to the source. The safety
  rule governs this implementation. A marked, distinct recovery database on Node 1
  is supported; deletion of the actual source primary is deliberately refused. The
  literal primary-deletion exit remains NOT met; it cannot be silently claimed by
  relabelling a fixture. Human marker creation is a separate, still-unperformed pre-step.
- The TSV manifest fields are `file, sha256, dump_started_utc, source_host, source_db`.
  Manifest time is RPO authority, filename/mtime must agree within 300 seconds.
  Only archives existing before drill start are eligible. Unregistered strays are ignored
  with a named diagnostic; registered digest mismatches fail `unregistered_backup`;
  duplicate registrations fail `manifest_ambiguous`. This resolves the plan's conflicting
  instructions to both ignore and refuse unregistered strays. Manifest registration proves
  backup-script provenance, not an authenticated scheduler: protect destination write access.
- Backups use a lock in BACKUP_WORK_DIR, exclusive archive creation, and publication of
  the manifest last. A failed pipeline deletes its partial archive. Retention deletes only
  validated archive basenames belonging to the configured database, within each configured
  root, oldest timestamp first; symlinks refuse. Off-machine destinations support local
  absolute paths (test stand-ins) or `user@host:/absolute/path` over SSH; remote paths use
  a restricted charset and shell quoting. Reads re-hash the destination bytes independently.
  No rsync `--delete`. EXTRA_PATHS (newline-separated files/directories) streams tar through encryption
  once and copies the identical encrypted bundle to both locations, verifying SHA-256; its destination is `extras/`. This is only R-126's hook.
- Bash entry points use strict mode and a shared Python 3.6 stdlib engine (`row05.py`).
  This deliberate plan implementation change keeps CSV/time/path validation portable,
  uses argument arrays instead of interpolated SQL/shell, and checks both pipeline exits
  (the equivalent of pipefail). The named compose volume binds the required PG_DATA_DIR (test volumes stay under
  scratch); this explicit location extends the plan. No scripts consult TMPDIR: gpg's private home is under
  BACKUP_WORK_DIR; encryption uses no agent or persistent keyring (explicit gpg S2K count 65011712). Operations emit reason
  tokens without subprocess stderr, which could contain secrets or row values.
- The restore result is exactly `date, RPO_h, RTO_min, PASS|FAIL` on stdout and in
  RESTORE_LOG, from one function. Separate diagnostics carry `result=FAIL reason=...`.
  Once destruction starts, even a failed restore writes FAIL. Stale backups still restore
  but cannot PASS. RTO uses a monotonic clock and enforces 60 minutes without rounding
  before comparison. A dry-run never prints PASS. Logs are required explicit paths.
- Exposure scans use a three-second TCP timeout, a distinct third-host control and
  source-IP command parsed as argv (no shell expansions). A working tailscale status,
  unreachable control or unknown network error is INCONCLUSIVE. Refused/time-out target
  ports are closed for this probe; any open port is FAIL. The declared port list bounds
  the claim; operators must also audit all listening services and default-deny firewall.
- **Count/document conflict:** the plan says to defer README's count until merge, but
  requires check_counts.py to pass now. Update only its count sentence, never an evidence
  table; re-derive after merge. CI is byte-identical; its operator must supply scratch via
  job environment before running this module. Missing GARS_ROW5_SCRATCH is a refusal,
  not an implicit system-temp fallback.
- **Read-boundary conflict:** the plan requests before/after listings of system temp
  folders; the owner forbids reading outside the repository and designated scratch.
  Tests therefore compare repository bytes, constrain every fixture/volume/log to
  scratch and assert the temp environment. No system-temp directory listing or OS-wide
  filesystem audit is claimed. Gpg disables keyrings, random-seed files and agent startup.

## What this does not close (stated, not implied)

Hardware exit and marker pre-step; public `external_human_seal`; approved second destination
(§18 row 8 / R-136); real `glitch-main` copy (R-126); the other four Stage-1 failure rows;
later deployment stages. Scheduling and provisioning are documented operator steps, not
actions performed on this machine. No sensitive biomedical data route is authorized here.

## Test

`tests/test_row05_backup.py`, imported by `tests/run_tests.py`: scrubbed subprocess
environments, throwaway compose lifecycle, backup and restore faults, local exposure probes,
manifest state grid and invariant sweeps. Database skips must name the failed container probe.
The change report distinguishes observed red results from unexecuted database cases.

## Status

standing; repository implementation only, real exit unmeasured.

## Date

2026-09-14
