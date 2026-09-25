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

## Review round 2 fixes (rc)

2026-09-25. Fixes for the round-1 independent review of item 1 (not committed; verdict
APPROVE WITH CHANGES: one MAJOR, two MINOR, two NOTE). The record change is a dated addendum
appended to [0105](../decisions/0105-rc-restore-log-reader-reads-the-table.md); its earlier
bytes are unchanged (a byte-prefix `cmp` against the round-1 file passes), and 0106 was not
written. The index was re-run (`bash docs/decisions/build_index.sh`); 0105's front matter is
unchanged, so the index did not change.

| Finding | Changed files | Test | Result (red-on-fault seen) |
|---|---|---|---|
| F1 MAJOR: Seal, Target and Data not bound to the record | `scripts/release_check.py` (`BOUND_CLAIMS`; `restore_qualifies` builds the quoted row; `restore_record_fails` requires it); `tests/test_release_check.py`; 0105 addendum (Q3; the "binds the transcription" sentence narrowed) | new `test_repository_provenance_bound_to_0054` (the real log and 0054: Seal `external_human_seal`, Target `primary`, Data `real` each → `not qualifying`); grid rows [external seal, record negates it], [target primary, row not quoted], [data real, row not quoted] → `not qualifying`; [target primary, row quoted] → qualifies | green. Red: yes, the six controls fail against the round-1 reader, and mutation N1 (quoted-row check dropped) fails the same six |
| F2 MINOR: an indented table row or CSV line skipped silently | `scripts/release_check.py` (`restore_records` tests the date-led and `\|`-led patterns on `line.lstrip()`; an indented date-led line raises); 0105 addendum | `test_restore_table_strict` [indented table], [indented CSV] (the review's P3 and P5) → `ValueError` | green. Red: yes, both fail against the round-1 reader; mutation N3 (the strip dropped) fails both |
| F3 MINOR: unpadded stamps accepted and mis-ordered | `scripts/release_check.py` (`STAMP_PATTERN`, checked in `restore_cells` and `restore_result_record`, so CSV and table); 0105 addendum | `test_restore_table_strict` [unpadded table stamp] (the review's P4), [unpadded CSV stamp] → `ValueError` | green. Red: yes, both fail against the round-1 reader; mutation N4 (pattern made permissive) fails both |
| F4 NOTE: the cell shows no age | 0105 addendum; this section's residual list | none (documentation) | fixed: residual line added below |
| F5 NOTE: Q2 lets the §17 row pass without primary deletion | 0105 addendum | none (policy visibility) | answered: Q2 stays the lane's ruling under the owner's standing delegation of 23 Sep 2026, listed for the owner's sight at merge; no ruling is needed to proceed |

A design note on F1: the review offered two forms, binding the stronger claims to a statement
a negation cannot satisfy, or keeping them non-qualifying. The first was taken, in the same
shape as the existing evidence-line rule (the record quotes the transcription verbatim), because
the brief's grid expects `external_human_seal` and Data `real` to qualify when the record
supports them; keeping them non-qualifying would have changed those expectations. The quoted
form is recorded as the lane's ruling Q3 in the 0105 addendum. The weaker claims keep the
round-1 checks, so 0054 qualifies for what it states and nothing more.

While running the mutations, a separate in-block "indented row" check turned out to be redundant
with the stripped outside-block check (mutating it alone left the suite green), so it was
removed rather than kept as untested code; the strip alone makes both indented probes raise.

### Rules-4 (round 2)

| Existing expectation | Changed? |
|---|---|
| The five pre-lane tests | No (byte-identical, green) |
| Round-1 grid rows [inclusive bounds, external seal] and [real data] | Expectation unchanged (qualifies); the fixture record now quotes the provenance row, as the new rule requires for these claims. A new sixth column in the grid's record tuple says so; every other row has it `False` |
| Round-1 `test_restore_table_strict` probes and header-only case | No; four probes added |
| Every other round-1 test | No |
| §17 thresholds and the 14-day tag rule | No |
| The generated DoD cell (line 16 of `dod_current.md`) | No; regeneration left it byte-identical |

`git diff f3f767d -- tests/test_release_check.py` removes only the lines rewritten to add the
grid's sixth column, the fixture writer's unpacking and seal branch, and the grid comment.

### Red at parent and mutations (round 2)

The round-2 test file was run against the round-1 reader (a `git archive` of f3f767d in the
scratch folder). Each mutation ran on a disposable copy with a byte backup, was watched red, and
was restored and watched green (`OK`); the script asserts the restored bytes equal the backup.

| Control | Result when faulted | Restored |
|---|---|---|
| Red at parent (f3f767d reader) | `FAILED (failures=10)`: `test_repository_provenance_bound_to_0054` [seal external_human_seal], [target primary], [data real]; grid [external seal, record negates it], [target primary, row not quoted], [data real, row not quoted]; strict [indented table], [indented CSV], [unpadded table stamp], [unpadded CSV stamp]. Every other test and subtest passes | n/a |
| N1 quoted-row check dropped | `FAILED (failures=6)`: the three repository-bound subtests and the three grid rows above | `OK` |
| N3 leading-whitespace strip dropped | `FAILED (failures=2)`: strict [indented CSV], [indented table] | `OK` |
| N4 padding pattern made permissive | `FAILED (failures=2)`: strict [unpadded CSV stamp], [unpadded table stamp] | `OK` |
| M1 date-only filter restored (re-run) | `FAILED (failures=39)` | `OK` |
| M2 malformed table row skipped (re-run) | `FAILED (failures=4)`: strict [five cells], [NaN], [bad stamp], [unpadded table stamp] | `OK` |
| M3 `meets` true without provenance (re-run) | `FAILED (failures=4)`: grid [no provenance row], `test_restore_table_rows_read`, two pre-lane tests | `OK` |
| M4a / M4b RPO / RTO bound exclusive (re-run) | `FAILED (failures=1)` each: grid [inclusive bounds, external seal] | `OK` |
| M5 any seal accepted (re-run) | `FAILED (failures=1)`: grid [seal none] | `OK` |
| M6 record check dropped (re-run) | `FAILED (failures=1)`: grid [record 9999 absent] | `OK` |
| M7 qualifying text gains `unmeasured` (re-run) | `FAILED (failures=5)`, incl. `test_restore_qualified_tag_path` | `OK` |
| M8 record-body check dropped (re-run) | `FAILED (failures=1)`: grid [record body lacks the CSV line] | `OK` |

### Commands (round 2)

Run from the repository root with `TMPDIR`, `TEMP` and `TMP` set to the lane's scratch folder.

| Command | Summary line |
|---|---|
| `python3 -m py_compile scripts/release_check.py tests/test_release_check.py` | exit 0, no output |
| `python3 tests/test_release_check.py` | `Ran 14 tests in 0.789s` / `OK` |
| `python3 tests/test_decision_links_resolve.py` | `citations: 345/345 resolve`; `Ran 3 tests in 1.298s` / `OK` |
| `python3 tests/check_counts.py` | `suite: 588 tests, from unittest's loader`; `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 scripts/release_check.py --check` | `DoD cells verified: 13/13 byte-stable` (exit 0) |
| `python3 scripts/release_check.py --tag` | `DoD cells verified: 13/13 byte-stable`, then 24 `release tag: REFUSED (…)` lines, none for `restore drill`; exit 1 |
| `git diff 452fe33 -- docs/ops/restore-log.md \| grep -c '^-[^-]'` | `0` |

README and DEVELOPMENT: the three current test-count statements, 587 → 588 (one test added).
Scope: lines 1-14 and everything from `def reviewer_measurement` to the end of
`scripts/release_check.py` are byte-identical to 452fe33 (`cmp`), as is the legacy
`venue/canary unmeasured` value line. `tests/run_tests.py` was not run, by the lane's machine
budget.

### Residual gaps (after round 2)

- The DoD cell shows no age: after 22 Oct 2026 it still reads `PASS` for this drill; §17's
  30-day limit is enforced only at tag time, by the 14-day rule. NOT met in the cell (F4).
- `independent_context` is still bound by a token test, which a record naming it only in a
  negation would pass. NOT a positive binding.
- The README public row, `external_human_seal`, §13.2 primary deletion, the release tag, the
  manual transcription and RTO at real scale: NOT met, unchanged from round 1.
- Whole-suite run (`tests/run_tests.py`) and `tests/test_row05_backup.py`: NOT verified in this
  round.

## Owner rulings needed

None.

## Review round 3 fixes (rc)

2026-09-25. Fixes for the round-2 independent review of item 1 (`docs/reviews/lane_rc_review2.md`,
not committed; verdict APPROVE WITH CHANGES: one MINOR, three NOTE). The record change is a dated
addendum appended to [0105](../decisions/0105-rc-restore-log-reader-reads-the-table.md) after its
last byte; its earlier bytes are unchanged (a byte-prefix `cmp` against the round-2 file passes,
and its diff has zero removed lines), and 0106 was not written. The index was re-run
(`bash docs/decisions/build_index.sh`); 0105's front matter is unchanged, so the index did not
change. `docs/implementation/dod_current.md` was regenerated and is byte-identical: the
repository cell still reads the qualifying text for the 22 Sep drill.

| Finding | Changed files | Test | Result (red-on-fault seen) |
|---|---|---|---|
| R2-F1 MINOR: unpadded date-led lines routed past `STAMP_PATTERN` | `scripts/release_check.py` (`DATE_LED = r'^\d{1,4}-\d{1,2}-\d{1,2}'` routes the CSV branch and the outside-table `\|` branch); 0105 addendum | `test_restore_table_strict` [probe A unpadded month], [probe A2 unpadded day], [probe B unpadded row outside a table], [unpadded date-only CSV], [unpadded date-only row outside a table] → `ValueError` | green. Red: yes, all five fail against the round-2 reader (copy of HEAD c3b6872 with the new test file); mutation N5 (routing padded again) fails the two date-only probes, which carry no stamp token and so test the routing alone |
| R2-F2 NOTE: list items and block quotes skipped | `scripts/release_check.py` (`STAMP_TOKEN`; any unread line holding a stamp-shaped token raises); 0105 addendum | `test_restore_table_strict` [probe C list item], [probe D block quote] → `ValueError`; a prose line with dates but no stamp → `unmeasured` | fixed (fail-closed). Red: yes, C and D fail against the round-2 reader; mutation N6 (refusal dropped) fails both; mutation N7 (token widened to any date) fails the prose control and every test reading the committed log |
| R2-F3 NOTE: "which a negation cannot satisfy" overstated | 0105 addendum ("harder to satisfy by accident", a substring test, not a positive reading) | none (documentation) | fixed |
| R2-F4 NOTE: Q1–Q3 not listed in one line for the owner | this section's last line; 0105 addendum | none (documentation) | fixed |

### Red at parent and mutations (round 3)

The round-3 test file on a `git archive` copy of c3b6872 (the round-2 reader): `Ran 14 tests` /
`FAILED (failures=7)`, exactly [probe A unpadded month], [probe A2 unpadded day], [probe B unpadded
row outside a table], [probe C list item], [probe D block quote], [unpadded date-only CSV],
[unpadded date-only row outside a table]; every other test and subtest passes. Mutations ran on a
disposable copy under the scratch folder with a byte backup; each was restored and watched green,
and the restored file is `cmp`-equal to the working tree.

| Control | Result when faulted | Restored |
|---|---|---|
| N5 routing padded again (`DATE_LED` back to `^\d{4}-\d{2}-\d{2}`) | `FAILED (failures=2)`: strict [unpadded date-only CSV], [unpadded date-only row outside a table] | `OK` |
| N6 stamp-token refusal dropped | `FAILED (failures=2)`: strict [probe C list item], [probe D block quote] | `OK` |
| N7 stamp token widened to any date | `FAILED (failures=1, errors=7)`: strict (the prose control), `test_repository_restore_cell`, `test_repository_table_regenerated`, `test_restore_qualified_cli`, `test_restore_qualified_tag_path`, three `test_repository_provenance_bound_to_0054` subtests | `OK` |
| N4 padding pattern made permissive (re-run) | `FAILED (failures=4)`: strict [probe A unpadded month], [probe A2 unpadded day], [unpadded CSV stamp], [unpadded table stamp] | `OK` |
| M1 date-only filter restored (re-run) | `FAILED (failures=46)` | `OK` |
| M5 any seal accepted (re-run) | `FAILED (failures=1)`: grid [seal none] | `OK` |

M2–M4, M6–M8, N1 and N3 were not re-planted in round 3; the round-3 change touches only the
routing and the new refusal in `restore_records`.

### Commands (round 3)

Run from the repository root with `TMPDIR`, `TEMP` and `TMP` set to the lane's scratch folder.

| Command | Summary line |
|---|---|
| `python3 -m py_compile scripts/release_check.py tests/test_release_check.py` | exit 0, no output |
| `python3 tests/test_release_check.py` | `Ran 14 tests in 0.971s` / `OK` |
| `python3 tests/test_decision_links_resolve.py` | `citations: 345/345 resolve`; `Ran 3 tests in 1.444s` / `OK` |
| `python3 tests/check_counts.py` | `suite: 588 tests, from unittest's loader`; `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 scripts/release_check.py` | `DoD cells regenerated: 13/13`; `dod_current.md` unchanged |
| `python3 scripts/release_check.py --check` | `DoD cells verified: 13/13 byte-stable` (exit 0) |
| `python3 scripts/release_check.py --tag` | `DoD cells verified: 13/13 byte-stable`, then 24 `release tag: REFUSED (…)` lines, none naming `restore`; exit 1 |
| `git diff 452fe33 -- docs/ops/restore-log.md \| grep -c '^-[^-]'` | `0` |

The suite count is unchanged at 588 (round 3 adds subtests, not tests), so README and
DEVELOPMENT are untouched. Scope: lines 1-14 and everything from `def reviewer_measurement` to
the end of `scripts/release_check.py` are unchanged in this round. `tests/run_tests.py` was not
run, by the lane's machine budget.

### Residual gaps (after round 3)

- The DoD cell shows no age: after 22 Oct 2026 it still reads `PASS` for this drill; §17's
  30-day limit is enforced only at tag time, by the 14-day rule. NOT met in the cell.
- `independent_context` is bound by a token test and the stronger claims by a quoted-row
  substring test; a record quoting either inside a negation would pass. NOT a positive binding.
- A date-time written without the `T` separator or in another format (for example
  `2026-09-23 10:00`) inside a list item or block quote is not stamp-shaped by `STAMP_TOKEN` and
  is still ignored as prose. NOT covered.
- The README public row, `external_human_seal`, §13.2 primary deletion, the release tag after
  6 Oct 2026, the manual transcription and RTO at real scale: NOT met, unchanged from round 1.
- Whole-suite run (`tests/run_tests.py`) and `tests/test_row05_backup.py`: NOT verified in this
  round.

For the owner's sight at merge, the lane's delegated rulings (the lane, under the owner's standing delegation of 23 Sep 2026): Q1 `independent_context` qualifies the §17 cell, the README public row stays `unmeasured`; Q2 the §13.2 primary deletion is recorded, not gating; Q3 the stronger claims need the cited record to quote the whole provenance row.

## Owner rulings needed

None.

## Review round 4 fixes (rc)

2026-09-25. Fixes for the round-3 independent review of item 1 (`docs/reviews/lane_rc_review3.md`,
not committed; verdict APPROVE WITH CHANGES: one MINOR, one NOTE). Documentation only: no script,
test, log, generated table, README or DEVELOPMENT change. The record change is a dated addendum
appended to [0105](../decisions/0105-rc-restore-log-reader-reads-the-table.md) after its last
byte; its earlier bytes are unchanged (a byte-prefix `cmp` against the round-3 file passes). The
index was re-run (`bash docs/decisions/build_index.sh`); 0105's front matter is unchanged, so the
index did not change.

| Finding | Changed files | Test | Result (red-on-fault seen) |
|---|---|---|---|
| R3-F1 MINOR: the round-3 residual understated which result-shaped lines are skipped | 0105 addendum (round 4); this section's residual | none (documentation, the review's first option) | fixed as documentation. Red: n/a, no code changed; the review's probes P1, P3, P8 and P11 were re-run on a `git archive` copy of 96680d8 and each left the 22 Sep `PASS` in the cell, which is the behaviour the widened residual now states |
| R3-F2 NOTE: the comment at `DATE_LED`/`STAMP_TOKEN` (`scripts/release_check.py:29-30`) says more than the constants do ("no line with a stamp in the log's UTC form reaches the skip" is the accurate reading) | none | none | stays until the file is next touched: this round is documentation only |

### Commands (round 4)

Run from the repository root with `TMPDIR`, `TEMP` and `TMP` set to the lane's scratch folder.

| Command | Summary line |
|---|---|
| `python3 tests/test_decision_links_resolve.py` | `citations: 345/345 resolve`; `Ran 3 tests in 1.250s` / `OK` |
| `python3 tests/check_counts.py` | `suite: 588 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |

`tests/run_tests.py`, `tests/test_release_check.py` and the release checks were not run in this
round: no code or generated file changed.

### Residual gaps (after round 4)

- Any line whose date or date-time is not in the log's `YYYY-MM-DD` form with `T` and seconds
  (for example a slash-separated or compact stamp), or a date-only result that is not led by the
  date (for example a list item), is ignored. The exposure is a hand edit, since row 5's writer
  emits padded ISO stamps. NOT covered. This replaces round 3's narrower third residual.
- The DoD cell shows no age: after 22 Oct 2026 it still reads `PASS` for this drill; §17's
  30-day limit is enforced only at tag time, by the 14-day rule. NOT met in the cell.
- `independent_context` is bound by a token test and the stronger claims by a quoted-row
  substring test; a record quoting either inside a negation would pass. NOT a positive binding.
- The README public row, `external_human_seal`, §13.2 primary deletion, the release tag after
  6 Oct 2026, the manual transcription and RTO at real scale: NOT met, unchanged from round 1.
- Whole-suite run (`tests/run_tests.py`) and `tests/test_row05_backup.py`: NOT verified.

## Owner rulings needed

None.

## Item 2 (pg)

The non-public read block in `gars/_system/guard_hook.py`, a row 4 addendum with a
human-declared registration opening for public data, recorded in
[0107](../decisions/0107-pg-nonpublic-projects-closed-to-reads.md). Base: public main `0754ec6`.
The rulings in this item are the lane's, under the owner's standing delegation of 23 Sep 2026.

### Base re-derivations (written before building)

- **The format `finalize` writes.** `00_data/dataset.tsv`, tab-separated, LF, header plus one data
  row, eight columns `data_class purpose agreement_ref input_data_location permitted_backends
  provider_exposure retention expiry` (`DATASET_BASE_FIELDS + DATASET_ROUTE_FIELDS`), mode 0444
  through `ws.atomic_open`. A four-column row-6 file is migrated in place by
  `write_dataset_record`. `finalize` refuses `identifiable` (`class_not_permitted`), requires
  `--expiry YYYY-MM-DD` for `deidentified_under_agreement`, refuses a non-public class on a
  `homelab` venue (the marker `/etc/gars/homelab`, absent on this Mac), and requires `--purpose`.
- **Every writer** (`git grep -n "dataset.tsv" -- gars/_system scripts`, then the callers of
  `write_dataset_record`): `stage00_register.write_dataset_record` (called by `finalize`);
  `scripts/backend_bench.py` (a fixed `public`/`fixture` row in a project it creates;
  unregistered, residual 13); `gars/tests/support.py` `write_fixture_dataset` and
  `gars/tests/test_venue_policy.py` (tests only). Readers: `wrapperlib.dataset_record`
  (executorlib, manifest facts, `scripts/rerun_check.py`), `venue_policy.py`,
  `stage00_register.dataset_values`.
- **Tests that drive `finalize` or a project read through the hook at the base.** Through the
  hook: `test_protected_paths.test_normal_project_edit_positive_control` (Read/Glob/Grep `.` at
  `gars/`, the only one that reads a project tree; red in any working copy holding a closed
  project, hence moved); `test_data_class_required.test_guard_dataset_entry_and_sibling_control`,
  `test_guard_hook`, `test_status_writer`, `test_stage03_execution`, `test_lifecycle_cancel`,
  `test_manifest_groups` and `tests/run_tests.py`'s guard tests send writes or Bash calls naming
  projects that do not exist in their root, so no closed project is in play. Direct `finalize`
  drivers (not through the hook): `test_data_class_required`, `tests/run_tests.py`'s
  `WorkspaceFixture` chains, `test_venue_policy`, `test_backend_bench`.
- **`create`'s stamp**, from the real `create` in a scratch root (one and three assays):
  `00_data`, `00_data/.gitkeep`, `00_data/<assay>`, `00_data/<assay>/raw`, `CONTEXT.md`,
  `HISTORY.md`, `_config`, `_config/.gitkeep`, `_config/executor.yaml`,
  `_config/nextflow.slurm.config`, `_config/<assay>.yaml`; paths are project-relative, so the
  title appears only in the project's own name. That is `CREATE_STAMP`.
- **The contracts' in-project reads** (stage 00 Process and the bounded voice; stage 01's design
  and samplesheet; stage 02's config, OUTPUTS and STATUS routing; stage 03's plan and inputs)
  are the R-042 items 5, 6 and 11 in 0107.
- **`project_state.py`** prints the fields listed in 0107's residual 2; `projects/_index.md`
  (rebuilt by the same hook, readable by Read) carries a subset.

### What changed

- `gars/_system/guard_hook.py`, additions only (0 removed lines): constants after
  `PROTECTED_PREFIXES` (`DATASET_ROW`, `DECLARATIONS`, `DECLARATIONS_HEADER`,
  `OPEN_IN_CLOSED_EXACT`, `OPEN_IN_CLOSED_BASENAME`, `CLOSED_PROJECT_DOORS = ()`,
  `CREATE_STAMP`, `RECURSIVE_FS`, `SHELL_GLOB`, `KNOWN_CLASSES`, the three stage 00 names,
  `CLOSED_WHY`); module-level helpers after `destinations()` (the binding names `static_prefix`,
  `project_is_public`, `closed_projects`, `closed_hit`, `declared_sources`, `inside_declared`,
  `registrable`, `declared_registration`, `first_public_classification`, plus private helpers
  and the two call-site functions `closed_read_refusal`, `closed_bash_refusal`); one call in
  `main()`'s Read/Glob/Grep branch after the R-073 check; one call in `check_bash` after
  `authorize`, inside its `try`; the `data_sources.tsv` branch in `check_write_tool` before the
  generic fallback; one `READ_ONLY` line `"data_sources.tsv"` before the closing `]`.
  `policy.py`, `tool_call.py` and `registry.json` are untouched.
- `gars/.claude/settings.json`: `"Edit(data_sources.tsv)"` and `"Write(data_sources.tsv)"`
  after row 6's `dataset.tsv` pair.
- `.gitignore`: `gars/data_sources.tsv` after `gars/projects/_index.md`.
- `gars/tests/test_nonpublic_read_block.py` (new, 19 tests).
- `gars/tests/test_protected_paths.py`: `test_normal_project_edit_positive_control` only.
- `docs/decisions/0107-…` and `docs/decisions/CONTEXT.md` (regenerated with
  `bash docs/decisions/build_index.sh`, one row added).
- `README.md`, `DEVELOPMENT.md`: the three current test counts, 660 → 679. The README
  parenthetical and DEVELOPMENT line 156 still name the run context of the 660-test run (13
  environment skips, "at the 2026-09-25 merge of row 8 step B"); the lane's solo suite run
  restates it. `test_case_variant` adds one named skip on a case-sensitive filesystem (Linux).

Two builder choices inside the specification: the static prefix of a `SHELL_GLOB` candidate is
judged from the session cwd only, where the shell expands it (the literal candidate is still
judged on both bases); the specification's cost cases, allowed from `_system/`, need exactly
that. In `registrable`, the walk skips `00_data/dataset.tsv` because the precondition above it
judges that file on `lexists`; without the skip P26 would be masked by the walk.

### Rules-4: existing expectations

| Existing expectation | Changed? |
|---|---|
| `test_protected_paths.test_normal_project_edit_positive_control` | **Yes, the one named change**: the same Edit and Read/Glob/Grep calls, sent to a temp workspace root with no `projects/` (the `test_resolved_symlink_escape` pattern); purpose unchanged |
| every other test in `test_protected_paths.py`, `test_settings_equal_guard_patterns` included | No (byte-identical, green with the new pair) |
| `test_guard_hook.py`, `test_policy_attacks.py`, `test_data_class_required.py` | No (byte-identical, green) |

`git diff 0754ec6 -- gars/tests/test_protected_paths.py` removes three lines, all inside that
one test. No other existing test was edited. The whole suite was not run here (machine budget);
the lane runs it solo.

### `rg --pre` shown red first

On a disposable folder under the scratch folder, ripgrep 12.1.1: `rg --pre <scratch>/pre.sh
hello STATUS` printed `hello` and the script wrote its marker file, so `--pre` runs a program.
The hook then refused `rg hello STATUS --pre=<script>`, `rg --pre <script> hello STATUS` and
`rg --pre-glob '*' hello STATUS` (exit 2, marker not written). Those three bare spellings were
already refused at the base by the registry's schema (`paths cannot be options or stdin`;
`value is outside the declared vocabulary`), so the new check's own refusals are the spellings
that pass the schema: the dispatcher `fs.inspect` with pattern `--pre=bash`, and a free string
value `--pre` (`stage00_register.py assays --select --pre`). P11 goes red on those.

### Red at parent and mutations

Red at parent: the final module copied into a clean clone of `0754ec6` under the scratch folder
gives `FAILED (failures=473, errors=25)`; 17 of 19 tests fail, the four new-helper tests with
`AttributeError` (`project_is_public`, `CREATE_STAMP`, `CLOSED_PROJECT_DOORS`,
`declared_sources`); `test_class_flip_bound_to_row_6` (row 6's line exists at the base) and
`test_path_free_calls_stay_open` pass.

Each mutation ran on a disposable clone (the working-tree files overlaid), with a byte backup of
`guard_hook.py`; the target test was run, the bytes restored and their sha256 compared to the
original (equal every time). After the last mutation the whole module ran green on the restored
copy (`Ran 19 tests`, `OK`), whose `guard_hook.py` and test file `cmp` equal to the commit's.

| Mutation | Target test | Result | First failing case |
|---|---|---|---|
| P1 Read-branch call removed | `test_reads` | `FAILED (failures=13)` | Read `projects/pilot/00_data/rnaseq_bulk/samples.csv` |
| P2 `check_bash` call removed | `test_reads` | `FAILED (failures=28)` | `cat projects/pilot/…/samples.csv` |
| P3 missing `dataset.tsv` public | `test_reads` | `FAILED (failures=2)` | `cat projects/fresh/CONTEXT.md` |
| P4 class casefolded/stripped | `test_reads` | `FAILED (failures=2)` | `cat projects/bad-Public/CONTEXT.md` |
| P5 ancestor rule dropped | `test_reads` | `FAILED (failures=5)` | Glob `**/*.csv` from the root |
| P6 resolved form dropped | `test_reads` | `FAILED (failures=2)` | `cat projects/open1/lnk-pilot/rnaseq_bulk/samples.csv` |
| P7 normalized form dropped | `test_reads` | `FAILED (failures=1)` | `cat projects/pilot/lnk-open/CONTEXT.md` |
| P8 root base dropped | `test_reads` | `FAILED (failures=1)` | dispatcher `fs.read` of the pilot file from cwd `projects/open1` |
| P9 sweep reduced to `paths` | `test_every_registered_tool` | `FAILED (failures=121)` | dispatcher `stage00_register.finalize` on `projects/pilot` |
| P10 row 6's `READ_ONLY` line removed | `test_class_flip_bound_to_row_6` | `FAILED (failures=1)` | Write on `projects/pilot/00_data/dataset.tsv` (exit 0); the `tee` case run by hand under P10 stays refused, `unregistered helper` |
| P11 `--pre` refusal removed | `test_rg_pre` | `FAILED (failures=2)` | dispatcher `fs.inspect` pattern `--pre=bash` |
| P12 `SHELL_GLOB` branch dropped | `test_shell_expansion` | `FAILED (failures=7)` | `cat projects/pil*/00_data/rnaseq_bulk/samples.csv` |
| P13 `~` refusal dropped | `test_shell_expansion` | `FAILED (failures=3)` | `cat ~/x` |
| P14 Q8 dropped | `test_q8_alone` | `FAILED (failures=1)` | finalize `--data-class public` on `fresh` with finalize a door |
| P15 cluster-suffix sweep dropped | `test_reads` | `FAILED (failures=1)` | `finalize … --model -mprojects/pilot/…/samples.csv` on `open1` |
| P16 path boundary → bare `startswith` | `test_reads` | `FAILED (failures=2)` | Read `projects/pilot-2/…/samples.csv` |
| P17 STATUS exemption → project-root `STATUS` | `test_reads` | `FAILED (failures=3)` | Read the sub-stage `STATUS` |
| P18 every-tool rule → `fs.*` only | `test_every_registered_tool` | `FAILED (failures=121)` | dispatcher `stage00_register.finalize` on `projects/pilot` |
| P19 every tool a door | `test_reads` | `FAILED (failures=28)` | `cat projects/pilot/…/samples.csv` |
| P20 declaration ignored | `test_declared_registration` | `FAILED (failures=5)` | `inspect --source <R1>/decl` |
| P21a regular-file clause | `test_invalid_declarations` | `FAILED (failures=18)` | variant `symlinked file`, `inspect --source <R1>/decl` |
| P21b CRLF clause | `test_invalid_declarations` | `FAILED (failures=6)` | variant `CRLF row` |
| P21c header clause | `test_invalid_declarations` | `FAILED (failures=6)` | variant `wrong header` |
| P21d duplicate clause | `test_invalid_declarations` | `FAILED (failures=6)` | variant `duplicate source` |
| P21e nested clause | `test_invalid_declarations` | `FAILED (failures=6)` | variant `nested sources` |
| P21f containment clause (equal/contain/inside) | `test_invalid_declarations` | `FAILED (failures=36)` | variant `equal to projects/` |
| P21g absolute-path clause | `test_invalid_declarations` | `FAILED (failures=5)` | variant `relative source` |
| P21h class-`public`-only clause | `test_invalid_declarations` | `FAILED (failures=12)` | variant `non-public class` |
| P22 raw-entry resolution dropped | `test_declared_registration` | `FAILED (failures=2)` | finalize public on `dangling` (and `undeclraw`) |
| P23 registration class check dropped | `test_declared_registration` | `FAILED (failures=1)` | finalize `deidentified_under_agreement` on `ready` |
| P24 new `READ_ONLY` line removed | `test_declaration_protected` | `FAILED (failures=4)` | Write `data_sources.tsv` |
| P25 at-least-one raw entry dropped | `test_declared_registration` | `FAILED (failures=1)` | finalize public on `fresh` (no raw entries) |
| P26 no-`dataset.tsv` precondition dropped | `test_declared_registration` | `FAILED (failures=2)` | finalize public on `stamped` (stamp + raw + a `dataset.tsv`) |
| P27 `registrable` → "no dataset.tsv" | `test_declared_registration` | `FAILED (failures=2)` | finalize public on `legacy` |
| P28 exemption widened to the whole call | `test_declared_registration` | `FAILED (failures=1)` | finalize public on `ready` with `--model projects/pilot/00_data/rnaseq_bulk` |
| P29 inspect's declared-source check dropped | `test_declared_registration` | `FAILED (failures=2)` | `inspect --source <R1>/undecl` |
| P30 link on a public project allowed | `test_declared_registration` | `FAILED (failures=1)` | `link --project projects/open1 --source <R1>/decl` |
| P31 dangling/outward entry declared | `test_declared_registration` | `FAILED (failures=4)` | `link --project projects/fresh --source <R1>/decl/outward` |

P21a–P21h were first run while the test checked `declared_sources` in-process before the hook
calls, so they went red on that assertion (`failures=1` each, P21g excepted). The test was
reordered so the hook-decision subtests come first; the table shows the re-run, each red on a
hook decision naming its variant.

P28 note: the specification names "the source-reaches-a-closed-project case" for P28. That case
(`--source projects/pilot/lnk-decl`, a link in `pilot` to `decl/`) stays refused under P28,
because `declared_registration` also refuses a source that reaches any project (point 4's "S must
reach no project at all"), so no exemption is granted. P28 goes red on a non-source token instead
(`--model` naming `pilot`); the two layers are independent.

### Commands

Run from the repository root with `TMPDIR`, `TEMP` and `TMP` set to the lane's scratch folder.

| Command | Summary line |
|---|---|
| `python3 -m py_compile gars/_system/guard_hook.py gars/tests/test_nonpublic_read_block.py` | exit 0, no output |
| `python3 gars/tests/test_nonpublic_read_block.py` | `Ran 19 tests in 69.403s` / `OK` |
| `python3 gars/tests/test_guard_hook.py` | `Ran 4 tests in 1.311s` / `OK` |
| `python3 gars/tests/test_protected_paths.py` | `Ran 5 tests in 14.569s` / `OK` |
| `python3 gars/tests/test_policy_attacks.py` | `Ran 19 tests in 1.851s` / `OK` |
| `python3 gars/tests/test_data_class_required.py` | `Ran 4 tests in 2.466s` / `OK` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/check_counts.py` | `suite: 679 tests, from unittest's loader`; `clean — every current claim matches the suite` |
| `python3 tests/test_decision_links_resolve.py` | `citations: 366/366 resolve`; `Ran 3 tests in 1.184s` / `OK` |
| `git diff -U0 0754ec6 -- gars/_system/guard_hook.py gars/.claude/settings.json .gitignore \| grep -c '^-[^-]'` | `0` |

### Residual gaps

Each is NOT met; 0107 states them in full.

- Residuals 1-17 of 0107's threat model: typed helpers' output; the SessionStart hook and
  `projects/_index.md`; links followed below a search root; files named inside files;
  unmodelled spellings and expansions; tools the matcher does not name; sub-agents; processes
  outside the session; data outside the project layout; Edit's echo; R-074's approval-gated
  exposure; approved execution; human-run `finalize` and unregistered writers; the honesty of a
  declared folder; agent-authored raw data in a declared folder; time of check; typed-tool path
  arguments outside `projects/`.
- No independent pre-build reviewer attacked the token spellings; coverage is the builder's
  red-first grid. Producer and reviewer are both Opus 5.5 sessions in separate contexts.
- The whole suite was not run in this item; the lane runs it solo.
- The lane's rulings Q4 to Q7 and Amendment 1's review-round-3 fixes reached this producer only
  as the specification text 0107 states; 0107 names them without restating their individual
  wording, which this producer did not have.
- The gate against a working copy that holds live projects (the lane's 36-project census) was
  not exercised here: this repository's `gars/projects/` holds none, and the producer does not
  read outside it.

## Owner rulings needed

None.
