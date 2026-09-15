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

## Review round 1 fixes

2026-09-15 · review: `docs/reviews/row_5_review.md` · producer: Codex.
The original report above is retained as a historical record. **Correction to its
R-134 wording: backup restore is implemented, acceptance unverified; no Stage-1
failure-matrix row is accepted.** The other four rows remain missing.
The §18 row-5 exit remains **NOT met**.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| R5-F1 BLOCKER: in-process bytecode | `tests/test_row05_backup.py`, `infra/compose/README.md`, `docs/decisions/0045-row-5-review-reliability-addendum.md` | `Row05OfflineTests.test_runner_reachability_and_skip_path` in fresh scratch fixtures without `PYTHONDONTWRITEBYTECODE` or `PYTHONPYCACHEPREFIX` | **Yes:** original code failed its repository-byte invariant; fixed code passed in a fresh copy of all tracked working-tree files and produced zero `.pyc` files. `sys.dont_write_bytecode` precedes dynamic imports; scratch refusal and byte assertions remain. Code defect closed; protected CI portion deferred below. |
| R5-F2 MAJOR: slow backup rejected | `infra/backup/row05.py`, `tests/test_row05_backup.py`, `infra/compose/README.md`, new 0045 | `test_slow_backup_remains_selectable`, existing manifest grid and real gpg/rsync test | **Yes:** new regression first raised `timestamp_drift`; now real publication/copy/selection accepts successive simulated 20- and 10-minute backups, including retained older archives. Archive mtime is normalized to dump start; sidecar completion mtime excludes backups completed during the drill. RPO remains start-based and the 300-second guard is unchanged. Pipeline/clock are doubles in the duration test; no long sleep. Closed. |
| R5-F3 MAJOR: interrupted destructive restore loses FAIL | `infra/backup/row05.py`, `tests/test_row05_backup.py`, `infra/compose/README.md`, new 0045 | `test_restore_interrupt_after_destruction`, `test_restore_log_validated_before_destruction`, existing fault/RTO tests | **Yes:** KeyboardInterrupt/SIGINT initially emitted only `operation_failed`; SIGTERM/SIGHUP emitted no result. All four now return nonzero with `restore_interrupted` and a dated FAIL row identical to stdout after synthetic DROP/CREATE; real pipeline children are reaped. An invalid log initially failed after destruction; now it refuses before any SQL. Documentation excludes uncatchable process/host loss and later log-storage loss from the logging guarantee. Closed. |
| R5-N1 NOTE: connections not pinned across routing changes | `infra/compose/README.md`, new 0045 | Source inspection of `Config.sql`, `guards`, `destructive_restore`; existing alias/marker test | **No new mutation test:** operational docs explicitly require direct stable endpoints, distinguish the admin `postgres` connection, and require stronger binding before supporting connection-routing proxies. No routing-change protection claimed. Documentation fix closed. |
| R5-N2 NOTE: PG_DATA_DIR scrubbed | `infra/backup/row05.py`, `tests/test_row05_backup.py`, new 0045 | `test_container_storage_survives_runtime_scrub`; synthetic `docker compose ... config`; database module gate | **Yes:** observer initially failed with `KeyError: PG_DATA_DIR`; main now retains it and container configuration requires an existing absolute directory outside Git without symlink components. Missing, in-repository and absent-directory inputs refuse. Compose resolves the synthetic device path. Code fix closed; live container-client verification remains unverified because `docker info` exits 1. |

Supporting status/count changes: `README.md`, `DEVELOPMENT.md`; decision index
regenerated with `docs/decisions/build_index.sh`. Four additive test methods bring
the runner to 160 cases (18 offline row-5 cases and 17 database-gated cases).
No threshold, test or guard was weakened. Decision 0044 is byte-identical; 0045
is its dated addendum. Both committed operational logs remain byte-identical and
contain zero PASS rows. No protected tree changed.

### Commands and observed summaries

Every shell set `TMPDIR`, `TEMP`, and `TMP` to this repository's sibling
`gars-row-5-scratch/` before commands. Test shells also set `GARS_ROW5_SCRATCH`
there and `GARS_PIPELINES`/`GARS_REFS` to absent scratch paths. Python bytecode
was disabled except in the deliberate fresh-fixture experiments. Fixture copies,
logs and the commit-message file stay in sibling scratch. Local socket access and
sibling-folder writes used the filesystem approval route. No real database was
contacted and no daemon was started.

| Command/check | Verbatim summary or exit result | Scratch log |
|---|---|---|
| Four new round-1 regression methods, before fixes | `Ran 4 tests in 5.733s`; `FAILED (failures=4, errors=3)` | `round1-regression-red.log` |
| Same four methods, after fixes | `Ran 4 tests in 5.329s`; `OK` | `round1-regression-green.log` |
| Fresh relevant-file fixture, ordinary interpreter, targeted runner-reachability case before fix | `Ran 1 test in 0.447s`; `FAILED (failures=1)` | `round1-ci-red.log` |
| Fresh tracked-file fixture, ordinary interpreter, same targeted case after fix | `Ran 1 test in 2.306s`; `OK`; zero bytecode files | `round1-ci-green.log` |
| `python3 tests/run_tests.py` | `Ran 160 tests in 103.697s`; `OK (skipped=26)` | `round1-full.log` |
| `python3 tests/test_row05_backup.py` | `Ran 35 tests in 90.369s`; `OK (skipped=17)` | `round1-row-module.log` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | `round1-contracts.log` |
| `python3 tests/check_counts.py` | `enforced=4`; `clean — every current claim matches the suite` | `round1-counts.log` |
| `python3 evals/test_harness.py` | `Ran 44 tests in 174.147s`; `OK` | `round1-eval-harness.log` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` | `round1-eval-results.log` |
| `bash -n infra/backup/pg_backup.sh infra/backup/restore_drill.sh infra/backup/test_exposure.sh` | Exit 0, no output | `round1-bash.log` |
| `docker compose -f infra/compose/postgres.compose.yml config` with synthetic settings | Exit 0; expected scratch `PG_DATA_DIR` is the device path | `round1-compose.log` |
| `docker info` | Exit 1; database tests print `SKIPPED: docker info: exit 1` | `round1-docker-info.log`, suite logs |
| `ast.parse(..., feature_version=(3, 6))` on both changed Python files | `Python 3.6 grammar: 2 files clean` | Tool output; syntax only |
| `bash docs/decisions/build_index.sh` | Exit 0; generated 0045 index row | Tool output |
| `git diff --check`; scoped diff of `gars/`, `evals/`, `.github/` | Clean; no protected-tree diff | Tool output |
| `git check-ignore` on backup.env, archive, sidecar, manifest | All four ignored | Tool output |
| Availability probes | `shellcheck: unavailable`; `age: unavailable`; `python3.6: unavailable` | Tool output |

The red runs above are deliberate fault demonstrations, not hidden failed final
runs. Final suite skips comprise 17 PostgreSQL cases and 9 existing environment
skips. The forced-container-skip path runs inside the reachability case.
The review remains untracked and unchanged (SHA-256
`2b07b312d776ee5fdf1c793ad6f719945d32e40ed0e903d471cf336e6d9cb208`).

## Owner rulings needed

**R5-F1 protected CI portion:** At the authorized merge after the study finishes,
will the owner add the review's exact single setting to the existing Test suite
step? The review specifies this option, with no alternative CI design:

```yaml
      - name: Test suite
        env:
          GARS_ROW5_SCRATCH: ${{ runner.temp }}
        run: python3 tests/run_tests.py
```

`.github/` is protected for this round, so this part stops here. No CI edit was
made. The test-module bytecode correction is complete; the actual hosted CI job
and Docker-enabled branch still need execution after the authorized merge.

### Residual gaps still open

- R5-F1's CI integration remains deferred as above. R5-N2's default container
  client path has no live database evidence: the Docker availability probe failed.
- Real Node 1 restore, human marker pre-step, dated PASS/freshness, RPO ≤24 h,
  RTO ≤60 min and outside-host exposure 0 remain unverified. Offline doubles and
  loopback probes do not satisfy those exits.
- Scheduled nightly execution, remote SSH/tailnet copies, age encryption, Python
  3.6 runtime execution, and shellcheck remain unverified. SIGKILL/host loss and
  log-storage loss are not guaranteed to leave a dated result.
- Authorized second sensitive-data destination (row 8), public external-human
  sealing, actual Brain memory/vault backup and restore, the other four Stage-1
  failure rows, and row-1 evidence/ledger integration remain open as recorded above.
  No later deployment stage was implemented; no public evidence was promoted.

## Review round 2 fixes

2026-09-15 · review: `docs/reviews/row_5_review_round2.md` · producer: Codex.

**Correction:** round 1's R5-F3 “Closed” conclusion was too broad. Its regression
covered interruption in the restore pipeline, but result finalization remained
outside the protected scope. Round 2 reproduced the missing dated FAIL and
PASS-only retained evidence, then extended protection through result publication
and log close. Prior records remain unchanged; new decision 0046 records the
correction beside 0045. **The §18 row-5 exit remains NOT met.**

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| R5-F3 MAJOR: interruption during finalization | `infra/backup/row05.py`, `tests/test_row05_backup.py`, `infra/compose/README.md`, `docs/decisions/0046-row-5-terminal-result-addendum.md` | New `Row05OfflineTests.test_restore_finalization_signals`; existing `test_restore_interrupt_after_destruction`, `test_restore_log_validated_before_destruction`, `test_stdout_log_equality_and_rto_threshold`; full runner | **Yes:** all nine subcases failed before the fix: SIGINT/SIGTERM/SIGHUP at entry to result writing, after real log flush before stdout publication, and after stdout publication before return. All now pass: nonzero exit, dated terminal FAIL, preserved history and terminal stdout/log agreement. Any appended PASS remains and is followed by FAIL with the same start date and RPO. Real child cleanup and RTO regressions also pass. Repository defect closed by these tests; independent re-review pending. |
| R5-F1: already closed at repository level in round-2 review | No further code change | `test_runner_reachability_and_skip_path` in full runner | **No new fault planting:** passes; bytecode suppression and mandatory scratch refusal remain unchanged. CI action is already authorized and deferred below. |
| R5-F2: already closed in round-2 review | No further code change | `test_slow_backup_remains_selectable`, `test_manifest_state_grid` in full runner | **No new fault planting:** both pass; dump-start RPO, sidecar completion selection and 300-second guard unchanged. |
| R5-N1 NOTE: routing limit documented | No further routing change; operational explanation retained | Inspection of `infra/compose/README.md`; `test_identity_and_marker_guards_without_database` in full runner | **No new fault planting:** stable/direct endpoint limitation remains explicit; alias/marker test passes. No connection-routing protection claimed. |
| R5-N2 NOTE: live container path unverified | No further code change | `test_container_storage_survives_runtime_scrub`; synthetic Compose config; database gate | **No new fault planting:** scrub test passes; Compose resolves scratch PG_DATA_DIR. Live execution remains unverified because `docker info` exits 1; all 17 PostgreSQL cases skip. |

Supporting changes: `README.md` and `DEVELOPMENT.md` reflect 161 measured cases
(19 offline row-5 cases, 17 database-gated cases); the generated decision index
`docs/decisions/CONTEXT.md` includes 0046. This appended report is the eighth
changed file. No test, threshold, guard or result/manifest schema was weakened
or changed to close the finding.

### Terminal-result policy and limits

The protected scope includes destructive work, result publication and closing
the retained append handle. An interrupt escaping that scope appends/publishes
terminal FAIL. SIGINT/SIGTERM/SIGHUP are blocked during fallback recording; the
previous mask is restored afterward. Stdout is explicitly flushed inside the
protected phase. A pending signal may then produce another failure diagnostic,
after the dated FAIL already exists.

Filesystem and stdout publication are not atomic. If PASS already reached either
destination, preserve those bytes and append FAIL for the same invocation. The
terminal row and nonzero exit govern its outcome; an earlier PASS is not acceptance
evidence. POSIX signal masking uses the existing Bash/macOS/Linux surface.
SIGKILL, host/power loss and subsequent log-storage loss remain outside the
guarantee. Log paths remain trusted operator inputs. The new test uses real
signals and filesystem writes but doubled SQL, checksums and archive operations;
it proves result handling, not live PostgreSQL recovery.

### Commands and observed summaries

Every shell set TMPDIR, TEMP and TMP to sibling `gars-row-5-scratch/` before
work. Tests also set GARS_ROW5_SCRATCH there and disabled bytecode; full/check runs
used absent scratch paths for GARS_PIPELINES/GARS_REFS. Python 3.13.2 was selected
for the existing evaluation APIs. Fixtures, logs and the commit-message file stay
in sibling scratch. The supplied review sufficed to recreate the signal tests;
no external reviewer files or conversations were requested or read. No daemon
was started or real database contacted.

| Command/check | Verbatim summary or exit result | Scratch record |
|---|---|---|
| New boundary test against pre-fix engine | `Ran 1 test in 8.409s`; `FAILED (failures=9)` | `round2-signals-red.log` |
| New boundary test plus three existing regressions named above | `Ran 4 tests in 16.901s`; `OK` | `round2-signals-green.log` |
| `python3 tests/run_tests.py` | `Ran 161 tests in 281.085s`; `OK (skipped=26)` | `round2-full.log` |
| `python3 evals/test_harness.py` | `Ran 44 tests in 308.151s`; `OK` | `round2-harness.log` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | `round2-contracts.log` |
| `python3 tests/check_counts.py` | `enforced=4`; `clean — every current claim matches the suite` | `round2-counts.log` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` | `round2-eval-results.log` |
| Named combined `bash -n` command plus individual checks of all wrappers | Exit 0; `Bash syntax: 3 wrappers clean` | `round2-bash.log`; tool output |
| `docker compose -f infra/compose/postgres.compose.yml config` with synthetic settings | Exit 0; `Compose device resolves to synthetic scratch PG_DATA_DIR` | `round2-compose.log` |
| `docker info` | Exit 1; tests report `SKIPPED: docker info: exit 1` | `round2-docker-info.log`; full log |
| Grammar via `ast.parse(..., feature_version=(3, 6))` | `Python 3.6 grammar: 2 files clean` | Tool output; syntax only |
| `bash docs/decisions/build_index.sh`, then byte comparison | `Decision index regeneration: byte-identical`; 0044/0046 each have one complete index row | Tool output; post-commit clean-diff check remains a completion check |
| `git diff --quiet c423366 -- gars/ evals/ .github/`; `git diff --check` | Exit 0; protected-tree diff empty; whitespace clean | Tool output |
| `git check-ignore`: backup.env, archive, sidecar, `infra/backup/manifest.tsv` | All four paths printed as ignored | Tool output |
| Environment example; hardware placeholders; Compose README vocabulary | `36` assignments (minimum 26); `7` Stage-1 placeholders (minimum 5); all 9 Compose variables named | Tool output |
| Prior decisions / operational logs / review preservation; PASS-row scan | 0044/0045 and both operational logs byte-identical; review unchanged; zero operational PASS rows in each log | Tool output |
| Added-line identifying-path/credential-pattern scan | `0 hits` (not a dedicated secret scanner) | Tool output |
| Availability probes | `shellcheck: unavailable`; `age: unavailable`; `python3.6: unavailable` | Tool output |

The initial driver attempt had a string-escaping error: `Ran 1 test in 3.890s`;
`FAILED (errors=9)`. That fixture error was corrected before the nine valid
fault reproductions and is not red-on-fault evidence. An initial ignore probe
used root `manifest.tsv`; the corrected required path
`infra/backup/manifest.tsv` matched. No final validation failed.
The full suite skipped 17 PostgreSQL cases plus nine existing environment cases.
Reachability, forced-container skipping and local loopback exposure passed.

Round-2 review SHA-256: `9d5b3767d54943fe6494ef9fa2b8775340fe653abccfb5291b33fe0e4df22c33`; unchanged and untracked. The other existing
untracked review remains unstaged too. The single commit uses explicit paths and
a scratch message file. No push, remote operation, merge or pull request occurred.

## Owner rulings needed

**None newly needed for round 2.** The review confirms the CI setting is already
authorized for the owner's later merge after the study. It is not an unresolved
finding or a fresh permission request. The existing exact
`GARS_ROW5_SCRATCH: ${{ runner.temp }}` setting remains deferred; no protected CI file changed.

### Residual gaps still open

- Live PostgreSQL DROP/CREATE/content verification and container-client storage
  remain unverified because the Docker gate failed.
- Real Node 1 recovery and human marker, dated PASS/freshness, RPO ≤24 h,
  RTO ≤60 min and outside-host exposure 0 remain unmeasured. No Stage-1
  failure-matrix row is accepted: backup restore is implemented with acceptance
  unverified; the other four rows remain missing.
- Hosted CI and its authorized merge setting, nightly scheduling, remote
  SSH/tailnet copies, age encryption, Python 3.6 runtime and shellcheck remain
  unverified. Grammar validation is not runtime evidence.
- Row 8's permitted second sensitive-data destination, public external-human
  sealing, actual memory/vault backup and restore, and row-1 evidence/ledger
  integration remain open. No operational PASS row or public claim was promoted.
- Independent review of this round remains pending. No OS-wide filesystem audit
  or uncatchable-loss guarantee is claimed.
