# Row 5 repository change report

2026-09-14 · producer: Codex · branch `build/gars-row-05-backup`.
Repository implementation only. **The §18 row-5 exit is NOT met.** No real database
was touched, no Node 1 drill or outside exposure run occurred, and neither committed
operational log contains a PASS row. Independent review and owner merge remain pending.

## Requirement → implementation → acceptance evidence

| Requirement | Changed files | Acceptance test and observed result | Red-on-fault seen? |
|---|---|---|---|
| R-131 backup | `infra/backup/pg_backup.sh`, `infra/backup/row05.py`, `infra/backup/backup.env.example`, `.gitignore` | Real gpg encryption and rsync to two scratch destinations; matching encrypted bytes, SHA-256 sidecars, manifest, readability pipeline; empty-directory first run; 16→14 retention; absent second destination; encrypted EXTRA_PATHS snapshot identical at both destinations | **Yes**, killed stub dump producer returns `dump_interrupted`, no archive/PASS; bad metadata/digests and unsafe paths refuse. Actual PostgreSQL dump/list integration **not watched red**, Docker gate failed |
| R-131 restore | `infra/backup/restore_drill.sh`, `infra/backup/row05.py`, `infra/backup/canary.example`, `docs/ops/restore-log.md` | Independent-file format/CRLF, candidate state grid, both guards and cluster-alias guard, count/checksum/canary/empty/stale/restore-failure state machine, RTO bound and stdout/log equality pass without a database | **Yes** at parser/guard/state-machine seams; relational operations are doubles. **No** real PostgreSQL restore-fault evidence; 17 database cases skipped |
| R-097 | `infra/backup/test_exposure.sh`, `infra/backup/row05.py`, `docs/ops/exposure-log.md` | Actual local IPv4 target and IPv6 control listeners: open port FAIL, closed port PASS, failed control INCONCLUSIVE, tailnet stub INCONCLUSIVE with note; empty source IP refuses; result line matches scratch log | **Yes**, observed nonzero results on each injected exposure fault. Real outside exposure **NOT met** |
| R-132 | `docs/ops/HARDWARE.md` | Spec reference profiles distinguished from unrecorded machine facts; ≥5 Stage-1 placeholders; no invented inventory | **No** hardware measurement; documentation check only |
| R-137 Stage 1 | `infra/compose/postgres.compose.yml`, `infra/compose/README.md` | `docker compose ... config` exit 0, one postgres:16 service, secret file, default loopback bind, healthcheck, restart policy, explicit scratch-bindable named volume | **No** running-stack evidence: `docker info: exit 1`. Provisioning and Stage-1 entry **NOT met** |
| R-134 Stage-1 backup-restore row | Restore files and `tests/test_row05_backup.py` | Backup/restore failure logic implemented, retained scratch diagnostics; database-backed execution skipped | **Yes** for the offline fault decisions above; **no** hardware acceptance |
| R-136 / §21 Q6, Q7, Q9 | `docs/decisions/0044-row-5-backup-defaults-and-drill-semantics.md`, generated `docs/decisions/CONTEXT.md`, environment example | Defaults and conflicts recorded, Q9 verbatim; second destination explicitly unconfigured pending row 8 | **No** approved sensitive-data route or external seal claimed |
| Test discovery/status | `tests/test_row05_backup.py`, one import in `tests/run_tests.py`, count sentence in `README.md`, status/counts in `DEVELOPMENT.md`, this report | Runner: **Ran 156 tests**, **OK (skipped=26)**. New module contributes 31 cases: 14 offline, 17 database-gated. Runner reachability and forced-skip subprocess both checked | **Yes**, count guard first rejected stale 125 claims; only the documents were corrected |

No files under `gars/`, `evals/` or `.github/` changed; CI jobs are byte-identical.
No README evidence table or ledger was created/edited. Decision 0043 is on the other
branch, absent here. The spec's data-handling filename collides with existing 0001;
0044 records that row 8 must choose a free number.

## Test inventory and limits

`Row05OfflineTests` (all run): `test_missing_variables_each_script` (including
container-only variables), `test_poison_environment_is_scrubbed` (parent real-name
poison removed, missing database refuses, bypass flag refused),
`test_required_scratch_and_no_system_temp`, `test_no_encryption_tool_refuses`,
`test_path_guards_and_injection`, `test_manifest_state_grid`,
`test_canary_example_crlf_and_duplicates`, `test_retention_cold_start_and_scope`,
`test_stream_encryption_cold_backup_and_failed_dump`,
`test_stdout_log_equality_and_rto_threshold`,
`test_identity_and_marker_guards_without_database`,
`test_restore_fault_decisions_without_database`,
`test_exposure_local_listeners_and_controls`, `test_runner_reachability_and_skip_path`.
Every fault assertion requires failure and rejects a PASS result token. A single
test-owned regex validates backup, restore, exposure and diagnostic result lines;
the offline encryption fixture exercises auto-detection selecting gpg. Source-IP and
tailscale commands are stubbed; exposure connections stay on loopback. The gpg and rsync
calls are real, while the offline archive producer/listing commands are explicitly stubs.

`Row05DatabaseTests` (each prints **SKIPPED: docker info: exit 1**):
`test_dry_run_and_cold_destroy`, `test_unmarked_target`, `test_primary_identity`,
`test_canary_missing`, `test_count_mismatch`, `test_checksum_mismatch_same_count`,
`test_corrupt_destination`, `test_stray_and_no_scheduled`, `test_after_start_ignored`,
`test_timestamp_drift`, `test_stale_backup_still_restores_fail`, `test_empty_database`,
`test_zero_rows`, `test_truncated_archive`, `test_missing_canary_file`,
`test_duplicate_manifest`, `test_second_unset_and_crlf`.
These cases, including the SQL checksum contract, actual drop/restore, unchanged dry-run
state and real source preservation, **were not watched red against PostgreSQL**.
A healthy runner must execute them before database correctness is claimed. The fixture
owns a unique compose project, random loopback port, scratch-bound named volume and
mode-600 random password; `down -v` runs in a finally. A separate forced-skip run
prints `SKIPPED: GARS_TEST_NO_CONTAINER=1` per case and exits 0.

Per-case repository-byte snapshots (including both operational logs) remain unchanged;
PASS-row counts are zero. Every child case starts from a scrubbed environment.
The plan's proposed system-temp directory listings were **not performed**: they would
violate the owner's read boundary. Scratch confinement is checked through paths,
environment and repository invariants, not an OS-wide filesystem audit (0044).

Initial tests exposed and corrected a macOS-incompatible loopback fixture, an assertion
that confused PGPASSFILE with a PASS token, and gpg's implicit agent calibration request.
The resulting gpg invocation uses explicit S2K iterations, no agent startup, no keyring
and no random-seed file. Additional review fixed exclusive-create cleanup and ensured
both destinations receive one identical encrypted EXTRA_PATHS snapshot. The changed
copy/interruption case was rerun successfully with real gpg/rsync. A final row-module
run (`row05-final.log`) exercises the strengthened result grammar, auto-detection and
repository snapshot assertions after the full runner's row-5 group completed.
Two final edge assertions were watched red (`row05-edge-red.log`): empty source-IP
command lacked a reason token, and parent SIGINT returned operation_failed. The
empty-argv refusal and catchable-interrupt handler were fixed; both targeted cases
then passed (`row05-edge-green.log`). These focused follow-ups occurred after the
full-suite run; the suite count is unchanged.

## Commands and execution environment

All commands ran from the repository root. Each mutating/test shell exported
`GARS_ROW5_SCRATCH` to the owner-designated sibling scratch directory and set `TMPDIR`,
`TEMP`, `TMP` to that same value. Literal machine paths are intentionally omitted from
this committed report. Test runs also set `PYTHONDONTWRITEBYTECODE=1`; the full-suite
child environment set `GARS_PIPELINES` and `GARS_REFS` to absent fixture locations
under scratch, avoiding real external pipeline/reference trees. No operational PG,
backup, drill, exposure or log values are inherited by row-5 child cases.
The sandbox initially rejected writes to the requested sibling scratch folder;
subsequent test/validation commands used the explicit filesystem approval route.

| Command (from root) | Result / scratch record |
|---|---|
| `python3 tests/test_row05_backup.py` | Initial failures retained in `row05-first.log` and `row05-second.log`, corrected rather than skipped |
| `python3 tests/test_row05_backup.py Row05OfflineTests.test_stream_encryption_cold_backup_and_failed_dump` | OK; `row05-extra-copy.log`, real encryption/copies including encrypted extra bundle |
| `python3 tests/run_tests.py` | Ran 156 tests; OK (skipped=26); `tests-run_tests.py.log`; final run in `tests-run_tests-final.log` |
| `python3 tests/check_contracts.py` | Exit 0; 14 contracts clean; `tests-check_contracts.py.log` |
| `python3 tests/check_counts.py` | Initial 125→156 drift refused; corrected document claims, final check clean |
| `python3 evals/test_harness.py` | Exit 0; Ran 44 tests; OK; `evals-test_harness.py.log` |
| `python3 evals/check_results.py --controls --lexicon` | Exit 0; clean, graded=1; `evals-check_results.py.log` |
| `bash -n infra/backup/pg_backup.sh infra/backup/restore_drill.sh infra/backup/test_exposure.sh` | Exit 0 (each wrapper also checked individually) |
| `docker compose -f infra/compose/postgres.compose.yml config` | Exit 0; one service; synthetic PGUSER/PGDATABASE/COMPOSE_PROJECT and scratch PG_PASSWORD_FILE/PG_DATA_DIR; `compose-config-*/config.log` |
| `docker info` | Exit 1, as probed by test gate; no database started |
| `bash docs/decisions/build_index.sh` | Generated index, complete 0044 row; post-commit regeneration checked for no diff |
| `git diff --stat c423366 -- gars/ evals/ .github/` | Empty |
| `git diff --check` | Clean |
| `git check-ignore` on backup.env, encrypted dump, sidecar and manifest probes | Ignored |
| PASS-row grep of both committed log templates | 0 in each |

Tools: gpg and rsync exercised; age absent, its encrypted-archive path **not exercised**.
With both encryption tools unavailable, the test observes `encryption_unavailable`, never
plaintext fallback. Host pg_dump 14.17 is incompatible with postgres:16, so database tests
use `PG_CLIENT_MODE=container`. Docker is installed but its daemon probe fails; Podman
absent. **Shellcheck was absent and did not run**; no shellcheck pass is claimed.
The five required validation commands were initially launched concurrently as separate
subprocesses with individual scratch logs; targeted follow-ups and the final runner/count
checks were sequential. Every git add is path-limited; the one commit message is read from
a scratch file. No push, remote, PR, approval or merge action was performed.

## Hours and residual gaps

Approximately **1.1 producer hours** of elapsed implementation/validation work on this
branch (rounded session estimate, including tool waits; excludes earlier plan preparation,
human review and hardware work). No metered-cost figure is inferred. Hours stay in this
report until row 1's ledger exists.

- **NOT met: the exit test and its marker pre-step.** No real Node 1 exists. Dated PASS
  ≤30 days, RPO ≤24 h, RTO ≤60 min and exposure 0 ports from outside remain unmeasured.
  The human marker has not been written. The spec's literal primary-deletion instruction
  conflicts with the owner's mandatory distinct-source guard; 0044 records that the guard
  wins. A distinct recovery database is supported; literal source-primary deletion is refused.
- **NOT met: second destination for real data**, awaiting the data-handling decision,
  §18 row 8 / R-136. The second scratch copy proves mechanics, not an authorized data route.
- **NOT met: the `external_human_seal` drill, Q9.** Public restore credibility stays
  unmeasured. Fixture canaries authored in this producer context are test inputs, not seals.
- Plan coverage wording, referring only to implemented repo logic:
  **R-134: 1 of 5 Stage-1 rows met (backup restore); process stops, network path interrupted, disk approaches capacity and invalid deployment remain MISSING and are not claimed**.
  Hardware acceptance of even the implemented backup-restore row is **NOT met**.
- **NOT met: the `glitch-main` copy, R-126.** EXTRA_PATHS is an encrypted copy hook;
  no Brain memory or vault was read or copied, and restoration of those artifacts is untested.
- **NOT met: scheduled nightly operation, remote SSH-copy validation, age-tool validation,
  and running PostgreSQL integration evidence.** Operator setup is documented; no scheduler
  was installed. CI's jobs are intentionally unchanged and require scratch environment
  configuration by their operator; an unset GARS_ROW5_SCRATCH deliberately refuses.
- **NOT met: row 1's README evidence/ledger integration.** Neither exists on this branch;
  its `Restore-drill minutes and age` row must remain `unmeasured` after merge. Only README's
  existing test-count sentence changed here. No later deployment stage was implemented.
