# Lane rc/pg change report

## Item 1 (rc)

The restore-log reader in `scripts/release_check.py`, recorded in
[0105](../decisions/0105-rc-restore-log-reader-reads-the-table.md). The rulings in this item are
the lane's, under the owner's standing delegation of 23 Sep 2026.

### What changed

- `scripts/release_check.py`: new constants after `RESTORE` (`RESULT_HEADER`,
  `PROVENANCE_HEADER`, `ACCEPTED_SEALS`, `DECISIONS`); new helpers between `clauses()` and
  `restore_measurement()` (`restore_cells`, `restore_result_record`, `restore_records`,
  `restore_qualifies`, `restore_record_fails`); `restore_measurement` now reads CSV lines, the
  result table and the provenance table, refuses malformed or stray date-led table rows, and
  returns a qualifying cell only when the provenance row and the cited decision record hold.
  Lines 1-14, `reviewer_measurement`, `measurements`, `render`, `release_failures` and `main`
  are byte-identical, as are the legacy `value = …venue/canary unmeasured…` line and its return.
- `docs/ops/restore-log.md`: appended one sentence and a provenance table with one row for the
  22 Sep drill (`node1 | scheduled-offmachine | recovery-db | synthetic | independent_context |
  0054`). No existing line changed; no new line contains `PASS`.
- `docs/implementation/dod_current.md`: regenerated with `python3 scripts/release_check.py`;
  only line 16 (restore drill) changed, from `unmeasured` to
  `2026-09-22T16:55:13Z; RPO 13.167400 h; RTO 0.284136 min; PASS; Node 1 from the scheduled
  off-machine copy; target recovery-db; synthetic data; seal independent_context (0054); public
  seal pending (external_human_seal)`.
- `tests/test_release_check.py`: eight tests added after the existing five, which are unchanged.
- `docs/decisions/0105-…`, and `docs/decisions/CONTEXT.md` regenerated with
  `bash docs/decisions/build_index.sh` (one row added).
- `README.md`, `DEVELOPMENT.md`: the three current test-count statements, 579 → 587. The README
  public evidence row "Restore-drill minutes and age" stays `unmeasured`.

### Rules-4: existing expectations

| Existing expectation | Changed? |
|---|---|
| `test_regeneration_and_hand_edit` | No (byte-identical, green) |
| `test_stale_release_row_and_threshold` | No (byte-identical, green) |
| `test_existing_restore_output_format` (CSV result without provenance: `meets` false) | No (byte-identical, green) |
| `test_terminal_restore_correction_same_timestamp` (`venue/canary unmeasured` text, tag refuses) | No (byte-identical, green) |
| `test_repository_table_regenerated` | No (byte-identical, green) |
| Row 5's `^\| .*PASS.*$` restore-log snapshot | No (no new line contains `PASS`) |
| §17 thresholds (≤ 30 days, RPO ≤ 24 h, RTO ≤ 60 min) and the 14-day tag rule | No |

`git diff 452fe33 -- tests/test_release_check.py | grep -c '^-[^-]'` gives `0`.

### Red at parent and mutations

The new test file was copied onto a scratch extraction of 452fe33 (`git archive`) and run there;
each mutation ran on a disposable copy under the scratch folder with a byte backup, was watched
red, and was restored and watched green (`OK`).

| Control | Result when faulted | Restored |
|---|---|---|
| Red at parent (452fe33 reader) | `FAILED (failures=28)`: every new test fails; `test_restore_table_rows_read` with `'unmeasured' != '2026-09-22T16:55:13Z; RPO 13.167400 h; …'`, `test_repository_restore_cell` with `('unmeasured', None, False) != …`; the five old tests `ok` | n/a |
| M1 date-only filter restored | `FAILED (failures=29)`: all table tests, incl. `test_restore_table_rows_read`, `test_repository_restore_cell`, grid, strict, CLI | `OK` |
| M2 malformed table row skipped | `FAILED (failures=3)`: `test_restore_table_strict` [five cells], [NaN], [bad stamp] | `OK` |
| M3 `meets` true without provenance | `FAILED (failures=4)`: grid [no provenance row], `test_restore_table_rows_read`, and two old tests | `OK` |
| M4a RPO bound exclusive | `FAILED (failures=1)`: grid [inclusive bounds, external seal] | `OK` |
| M4b RTO bound exclusive | `FAILED (failures=1)`: grid [inclusive bounds, external seal] | `OK` |
| M5 any seal accepted | `FAILED (failures=1)`: grid [seal none] | `OK` |
| M6 record check dropped | `FAILED (failures=1)`: grid [record 9999 absent] | `OK` |
| M7 qualifying text gains `unmeasured` | `FAILED (failures=5)`: `test_restore_qualified_tag_path`, `test_repository_restore_cell`, `test_restore_crlf`, `test_restore_qualified_cli`, `test_repository_table_regenerated` | `OK` |
| M8 record-body check dropped | `FAILED (failures=1)`: grid [record body lacks the CSV line] | `OK` |

A further check: pointing the provenance row's Record at `0105` gives `not qualifying: record
0105 lacks the evidence line`, so this record cannot vouch for the drill.

### Commands

Run from the repository root with `TMPDIR`, `TEMP` and `TMP` set to the lane's scratch folder.

| Command | Summary line |
|---|---|
| `python3 -m py_compile scripts/release_check.py tests/test_release_check.py` | exit 0, no output |
| `python3 tests/test_release_check.py` | `Ran 13 tests in 0.694s` / `OK` |
| `python3 tests/test_decision_links_resolve.py` | `citations: 345/345 resolve`; `Ran 3 tests in 1.522s` / `OK` |
| `python3 tests/check_counts.py` | `suite: 587 tests, from unittest's loader`; `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 scripts/release_check.py --check` | `DoD cells verified: 13/13 byte-stable` (exit 0) |
| `python3 scripts/release_check.py --tag` | `DoD cells verified: 13/13 byte-stable`, then 24 `release tag: REFUSED (…)` lines for the twelve other rows, none for `restore drill`; exit 1 |
| `git diff 452fe33 -- docs/ops/restore-log.md \| grep -c '^-[^-]'` | `0` |

`tests/run_tests.py` (the whole suite) was not run, by the lane's machine budget; the lane runs
it solo later.

### Residual gaps

- The README public evidence row "Restore-drill minutes and age": NOT met; stays `unmeasured`.
- `external_human_seal` drill: NOT met.
- §13.2 primary deletion: NOT met; not performed, recorded as `recovery-db` in `Target`.
- Release tag: NOT met; twelve other rows are unmeasured, and after 6 Oct 2026 the 14-day rule
  also refuses on this drill.
- Transcription automation: NOT met; the node's CSV line and 0054's facts reach the repository
  by a human step.
- RTO at real scale: NOT met; measured on synthetic data only.
- Whole-suite run: NOT verified in this item (see above).

## Owner rulings needed

None.
