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
