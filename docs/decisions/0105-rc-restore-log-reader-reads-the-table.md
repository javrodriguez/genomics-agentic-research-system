---
date: 2026-09-25
status: standing
kind: defect
touches:
  - scripts/release_check.py
  - tests/test_release_check.py
  - docs/ops/restore-log.md
  - docs/implementation/dod_current.md
symptoms:
  - the 22 Sep restore drill PASS reads unmeasured in the DoD table
  - a markdown result row in the restore log is skipped silently
---
# The restore-log reader reads the result table and a provenance table

## Context

Row 5's evidence in [restore-log.md](../ops/restore-log.md) is a markdown table:
`| 2026-09-22T16:55:13Z | 13.167400 | 0.284136 | PASS |`. The reader in
`scripts/release_check.py` kept only lines that start with a date, so it skipped that row
without a word, and the generated [dod_current.md](../implementation/dod_current.md) showed the
passed drill of 22 Sep (RPO 13.17 h, RTO 17 s, run on Node 1, [0054](0054-row-5-on-node-1.md))
as `unmeasured`. A filter that drops its input and reports zero.

The root cause is a date-led line filter applied to a log whose one real record is a table row.
Behind it sat a second gap, named in [0062](0062-row-11-raw-git-and-terminal-restore-addendum.md)
and the reader's docstring: the four CSV fields cannot establish venue, off-machine source or
canary provenance, so even a parsed row could never qualify. No machine-readable provenance
existed anywhere.

## Decision

**Shapes read.** The reader now reads three shapes from the log, in line order:

- the legacy CSV line `date, RPO_h, RTO_min, PASS|FAIL`, parsed exactly as before;
- the result table, which starts at the exact header `| Date | RPO_h | RTO_min | Result |` and
  its separator and runs until the first line not starting with `|`;
- the provenance table, which starts at the exact header
  `| Date | Venue | Source | Target | Data | Seal | Record |` and its separator.

Inside a table every row must have exactly the table's cell count, a `%Y-%m-%dT%H:%M:%SZ` stamp
and valid values, or the reader raises `ValueError`. The provenance vocabularies are closed:
Venue `node1`; Source `scheduled-offmachine`; Target `recovery-db` or `primary`; Data
`synthetic` or `real` (printed, never gating); Seal `independent_context`,
`external_human_seal` or `none`; Record four digits. A date-led `|` row outside a known table
raises too. The silent skip is no longer possible: every date-led line is read or refused.

**Selection** is unchanged: the latest stamp wins, and the last-appended row wins a tie, across
both result shapes.

**Provenance join.** One provenance row per stamp; a duplicate raises. A provenance row whose
stamp has no result raises, which catches a mistyped stamp. A result without a provenance row
is legal and keeps today's text, ending `venue/canary unmeasured`.

**Qualification.** The §17 restore cell qualifies only when all hold: status `PASS`;
RPO ≤ 24 h and RTO ≤ 60 min, compared as `Decimal` with inclusive bounds as §17 writes them;
venue `node1` and source `scheduled-offmachine`; the seal is in `ACCEPTED_SEALS`
(`independent_context`, `external_human_seal`); and the cited record exists exactly once as
`docs/decisions/<Record>-*.md`, has `status: standing`, lists `docs/ops/restore-log.md` under
`touches:`, and its body carries both the drill's CSV evidence line, built from the table's raw
cell strings, and the seal token. That last check binds the transcription to the record that
witnessed the drill: another standing record that merely touches the log cannot vouch for it.
This record is one such, and it deliberately does not quote the evidence line. A failed rule
gives `not qualifying: <rule>` and `meets` false.

**Age is not in the cell.** A date-dependent cell would break `--check`'s byte stability, so the
reader returns the drill's date and `release_failures` applies age at tag time, where the
stricter 14-day rule already covers §17's 30 days.

**The transcription.** One provenance row was appended to the log below its existing text,
which is unchanged. Its sources:

- `node1`, the timer-made archive, `recovery-db`, `synthetic` and `independent_context` come
  from 0054; `recovery-db` rests on 0044's supported target.
- `scheduled-offmachine` rests on two sources together. 0054 says the drill restored "the newest
  timer-made archive" and that "the engine re-hashed the off-machine copy". The read *from* the
  off-machine destination is shown by the code: `drill()` in `infra/backup/row05.py` selects the
  archive with `candidate(config.off, …)` and streams it through `config.off.reader(name)`. The
  cell does not claim to quote 0054 alone.

**Rulings** (the lane, under the owner's standing delegation of 23 Sep 2026):

- **Q1.** `independent_context` qualifies the §17 DoD cell: §17's test column asks for a canary
  supplied outside the operator context, and §13.2 says `independent_context` is sufficient for
  development drills. The cell names the seal and adds "public seal pending
  (external_human_seal)". The README's public evidence row "Restore-drill minutes and age" stays
  `unmeasured`, because public claims need an `external_human_seal`.
- **Q2.** §13.2's primary deletion is recorded in the `Target` column, not gated on.

## What this does not close

- **The README's public row** "Restore-drill minutes and age" stays `unmeasured`: NOT met.
- **`external_human_seal`:** no such drill exists, so the public restore-credibility claim is
  NOT met.
- **§13.2 primary deletion not performed:** the target is a distinct recovery database. NOT
  closed.
- **The 14-day tag rule:** a tag after 6 Oct 2026 refuses on this drill, and every other §17 row
  is still unmeasured, so `--tag` refuses today. NOT met.
- **The transcription is a human step:** the node's CSV line and 0054's facts reach the
  repository by hand; no tool carries them. NOT automated.
- **RTO at real scale:** 17 s on about 470,000 synthetic rows is not a measurement at real
  scale. NOT met.

## Test

`python3 tests/test_release_check.py` adds eight tests beside the five existing ones, which are
unchanged and green:

- `test_restore_table_rows_read` and `test_repository_restore_cell` read the committed table
  shape and the repository's log; against the parent reader both fail on `unmeasured`.
- `test_restore_table_strict`, `test_restore_mixed_shapes`, `test_restore_crlf`,
  `test_restore_qualification_grid` (eighteen literal rows), `test_restore_qualified_tag_path`
  and `test_restore_qualified_cli` cover the strict parse, cross-shape selection, CRLF, each
  qualification rule, the tag-time age and the CLI's byte stability.

Red at parent: the new test file run against the 452fe33 reader fails every new test (28
failures, the table tests naming the `unmeasured` cell); the five old tests pass. Each mutation
below was run on a disposable copy, watched red, and restored green:

- M1 the date-only filter restored: the table tests fail.
- M2 a malformed table row skipped: `test_restore_table_strict` fails.
- M3 `meets` true without a provenance row: the grid's no-provenance row fails.
- M4 the RPO bound, and separately the RTO bound, made exclusive: the grid's boundary row fails.
- M5 any seal accepted: the grid's `none`-seal row fails.
- M6 the record-existence check dropped: the grid's `9999` row fails.
- M7 the qualifying text gaining `unmeasured`: `test_restore_qualified_tag_path` fails.
- M8 the record-body check dropped: the grid's "body lacks the CSV line" row fails.

## Status

standing; the implementation is the lane's, subject to independent review. The rulings are the
lane's, under the owner's standing delegation of 23 Sep 2026.

## Date

2026-09-25

## Addendum — review round 2, 2026-09-25

The independent review of round 1 found three gaps; the text above stays as written, and this
addendum narrows two of its sentences.

**The binding was narrower than stated (F1).** The sentence "That last check binds the
transcription to the record that witnessed the drill" held for the stamp, RPO, RTO and status
(the CSV evidence line), not for Seal, Target or Data. The seal check was a substring test, and
0054 passes it for `external_human_seal` because it says "`independent_context`, not
`external_human_seal`". A one-cell edit to the provenance row turned the cell into
`seal external_human_seal`, `target primary` or `real data`, each still qualifying, claims 0054
denies. Now `BOUND_CLAIMS = ('external_human_seal', 'primary', 'real')`: when the row makes any
of these claims, the cited record's body must also quote the whole provenance row, in the form
`| <stamp> | <venue> | <source> | <target> | <data> | <seal> | <record> |`, which a negation
cannot satisfy. The weaker claims (`independent_context`, `recovery-db`, `synthetic`) keep the
checks above, so 0054, which predates the quoted form, still qualifies for exactly what it
witnesses. Ruling Q3 (the lane, under the owner's standing delegation of 23 Sep 2026): the quoted
row is the record form for the stronger claims, the same rule the evidence line already follows.
It is a rule for future records, not an edit to any existing one.

**Indented lines (F2).** The sentence "every date-led line is read or refused" held only for
lines starting in column 0. A result row or CSV line with leading spaces still renders, yet it
ended the table and matched no check, so it was skipped. The reader now tests the date-led and
`|`-led patterns on the line with leading whitespace stripped; an indented date-led line or
table row raises `ValueError`. With that, every date-led line, indented or not, is read or
refused.

**Unpadded stamps (F3).** `strptime` accepts `2026-9-3T1:2:3Z`, and selection compares stamps
as strings, so an unpadded stamp sorted after a padded later one. Every stamp, table or CSV, must
now fully match `STAMP_PATTERN`, zero-padded, or it raises. Row 5's writer emits padded stamps,
so no committed line changes reading.

**Age (F4).** The cell carries no age: after 22 Oct 2026 it still reads `PASS` for this drill.
§17's 30-day limit is enforced only at tag time, by the stricter 14-day rule. NOT met in the cell.

**Q2 (F5).** Q2 lets a fresh drill with Target `recovery-db` satisfy the §17 restore row at tag
time without §13.2's primary deletion, which 0044 recorded as NOT met under the owner's safety
rule. It stands as the lane's, under the owner's standing delegation of 23 Sep 2026, and is
listed for the owner's sight at merge.

**Still open.** The `independent_context` check stays a token test: a record that names
`independent_context` only in a negation would pass it. That is not an upgrade over what 0054
states, but it is not a positive binding either.

**Test.** `test_repository_provenance_bound_to_0054` edits the real log's Seal, Target and Data
in turn against the real 0054 and expects `not qualifying`. The grid gains four rows (a
0054-like body that negates `external_human_seal`; Target `primary` and Data `real` without the
quoted row; Target `primary` with it, qualifying), and the rows for `external_human_seal` and
Data `real` now quote the row. `test_restore_table_strict` gains an indented table row, an
indented CSV line, and an unpadded stamp in each shape. Against the round-1 reader these fail
(10 failures, only the new controls). Mutations, each watched red and restored green: the
quoted-row check dropped (6 failures); the leading-whitespace strip dropped (the two indented
probes); the padding pattern dropped (the two unpadded probes). M1 to M8 were re-run on this
reader and each is still red.
