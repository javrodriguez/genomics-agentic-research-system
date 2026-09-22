---
date: 2026-09-22
status: standing
kind: decision
touches:
  - docs/decisions/TEMPLATE.md
  - tests/test_decision_links_resolve.py
  - gars/_system/hooks/pre-commit
  - gars/_system/hooks/pre-push
  - gars/tests/test_hooks_records.py
  - gars/tests/test_hooks_gitleaks.py
  - gars/tests/test_secret_containment.py
  - scripts/release_check.py
  - tests/test_release_check.py
  - docs/implementation/dod_current.md
  - docs/implementation/row_11_change_report.md
symptoms:
  - dangling plural citation passes a singular-only scan
  - unstaged repair hides a dangling staged citation
  - committing and reviewing sessions are equal
  - hand-typed current-value cell survives regeneration
---
# Row 11 records, links, trailers and release check

## Context

R-001, R-163, R-165, R-116 and R-170 govern this repository-side row.
The starting commit is `af4159a653db5c4ee14bc6415090d718c580a9db`, row 15's
approved but unmerged head. The owner retains approval and merge authority.
Existing records and the frozen specification remain unchanged.

Number note: 0052–0057 belong to rows 15, 4 and 12 on other branches;
renumbering at merge is the owner's. Some of those records are already inherited
on this branch. This record uses 0058 without renumbering any other record.

## Decision

The owner, 22 September 2026, ruled **D-7, 7A**:

> the link checker's citation forms are `decision NNNN` and `decisions NNNN` (case-insensitive, the method the gap assessment's review m-4 states: code = `.py .sh .yml .yaml .toml` and `.gitignore`, contracts = `gars/**.md`, excluding `*.jsonl` transcripts and `docs/specs/`); a bare `(NNNN)` is not a citation, because it collides with years and sample identifiers. Every counted citation must resolve to a file in `docs/decisions/`. The measured count replaces the spec's "210" in this row's decision record, never in the frozen spec.

The owner, 22 September 2026, ruled **D-8, 8A**:

> the legacy records are accepted as legacy. The checker reads a legacy record's frontmatter `date` and `status` as R-001's Date and Status, and requires Context / Decision / Test / Status / Date only of records dated on or after this row's own record; no legacy record is edited, so the log stays append-only. The new template in `docs/decisions/` carries all five sections.

The measured baseline is `citations: 287/287 resolve`, not the frozen spec's
"210". The final measured count is `citations: 288/288 resolve`: one additional counted
occurrence is the uppercase plural fixture in the acceptance module.
The command uses Git's tracked paths and `\bdecisions?\s+(\d{4})\b` with
case-insensitive matching. Occurrences count separately, including code comments
and fixture-source text. Bare years do not count.

`TEMPLATE.md` is the one template. The field check validates every numbered record,
not just cited ones. Records dated before 2026-09-22 pass on their valid frontmatter
Date and Status. New records need nonempty Context, Decision, Test, Status and Date
sections. The specification's `Test-that-proves-it` spelling is accepted as Test;
this also preserves the inherited same-day 0055 record without an edit.

The pre-commit checker reads index object IDs and blobs, including staged additions
and deletions, rather than falling back to unstaged files. The standalone acceptance
uses the same checker on tracked working bytes. Missing/unreadable decisions,
unmerged indexes, duplicate numbers, nonregular inputs and read errors refuse.
The existing marker, previous-hook preservation and gitleaks veto remain intact;
all gates execute even when another gate refuses. Installation is still row 15's
complete-content installer; a differing marker-bearing installation refuses an
implicit upgrade. No hook is installed in the producer clone.

### Trailer activation and evidence

The activation point is this row's own commit, identified by the first introduction
of this record. It is inclusive: that commit must satisfy R-165 before it is pushed.
Earlier history is exempt and is never rewritten. The producer cannot manufacture
an independent review or benchmark record to make its own commit pushable.

The smallest review format, pre-authorised by the owner, is one `session: ID` line
in the review file. The committing session is the `Session:` trailer. IDs are
nonempty tokens compared exactly, and equality refuses; no session registry is
implied. Duplicate or missing required trailers or review session lines refuse.
The existing benchmark JSON field `git_sha` supplies the commit binding.
The owner, 22 September 2026, settled open ruling 1:

> REQUIRE A LATER COMMITTED EVIDENCE SNAPSHOT. Pre-push reads the Review and Bench records from committed git objects only, never from working-tree files, so whatever the gate accepted is reconstructible from the repository's own history; Bench's `git_sha` must still match the examined commit, and reading a self-hash-bearing evidence record out of the examined commit itself stays refused as self-referential.

The owner accepts the cost: a commit touching `_system/**` becomes pushable only
once its evidence snapshot is itself committed. The ordinary order is
**code commit -> evidence commit -> push**. Evidence-only commits do not touch
`_system/` and therefore do not require their own Bench records.

Production pre-push now runs the trailer gate beside the inherited previous-hook,
gitleaks and whole-suite gates; any veto refuses and all gates still execute.
For each outgoing ref, its local tip's resolved commit is the evidence snapshot
for the examined commits in that ref's range. It must be a strict descendant of
an examined system commit. Both records are read as regular Git blobs from that
snapshot, with repository-relative paths; absent blobs, symlinks, path traversal,
invalid content and Git read failures refuse. HEAD, working files and the index
cannot supply or repair evidence. Each outgoing ref must pass independently.
The snapshot commit and the trailer paths reconstruct exactly the bytes checked.
A system commit at the outgoing tip refuses until a later evidence commit exists.

Open ruling 2 was already settled by the owner's original rule 4: extend the
inherited hook fixtures while preserving every assertion. It needs no further
ruling; no existing assertion is removed or weakened.

### Generated definition of done

`scripts/release_check.py` copies all thirteen clause/test/threshold rows verbatim
from frozen §17 and regenerates their current-value cells into
`docs/implementation/dod_current.md`. No acceptance threshold is changed.
No wall-clock generation stamp is included, so identical inputs produce identical
bytes. `--check` detects any manual cell change. `--tag` first verifies those bytes
and refuses incomplete, below-threshold, future-dated or over-14-day-old evidence.
It is an eligibility command, not permission to tag or an installation of a global
Git policy. Raw `git tag` interception is not built.

The existing row 5 CSV output (`date, RPO_h, RTO_min, PASS|FAIL`) is parsed without
substituting file modification time for evidence time. Even a numeric PASS in that
format cannot establish Node 1, off-machine-copy and independent-canary provenance;
the missing part remains unmeasured. The current log contains no drill record.
Existing benchmark task records and historical control-test prose do not establish
the other full §17 thresholds. Absent qualifying producers/records remain
`unmeasured`; synthetic unit-test outputs are never published as evidence.
Future row-specific evidence adapters must arrive with their producers and tests;
this row does not invent their wire formats or run other rows' scientific work.

## What this does not close

- **NOT met:** full release eligibility; every current §17 row lacks qualifying
  complete evidence. Regeneration is distinct from meeting those thresholds.
- **NOT met:** full R-116's `gars doctor`, session-registry hour total and its ledger
  cross-check. No implementation row builds that registry; neither is built here.
- **NOT met here:** R-117's README evidence table and `make demo`.
- **NOT met:** independent review and Bench evidence for this producer commit;
  no self-approval, push or merge is performed.
- **NOT met:** expanded-suite execution on Python 3.6.8 or the cluster. New code uses
  the standard library and the 3.6 API/language surface; executed versions are reported.
- **NOT met:** raw Git tag interception, evidence authentication or future producer
  formats. The explicit release eligibility command fails closed on missing evidence.
- **Standing ruling of the owner:** merge only after the separate study's done
  commit. Protected source, evals, benchmarks and frozen specification stay unchanged.

## Test

`python3 tests/test_decision_links_resolve.py`,
`python3 tests/test_release_check.py`, `python3 gars/tests/test_hooks_records.py`,
`python3 scripts/release_check.py`, `python3 scripts/release_check.py --check`,
and `python3 scripts/release_check.py --tag` (expected refusal on this tree).
The change report records the full-suite and other required command summaries,
positive controls, each planted fault and the regenerated table verbatim.

## Status

standing; repository-side implementation complete under the owner's rulings,
subject to independent review and the owner's approval. The change report records
this run's results; residual requirements remain explicitly NOT met.

## Date

2026-09-22
