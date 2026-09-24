---
date: 2026-09-23
status: standing
kind: decision
touches:
  - gars/_system/claims/claims.sql
  - gars/_system/claims/render_report.py
  - gars/_system/claims/report_template.md
symptoms:
  - row 7's new claim store and report renderer live under the protected prefix gars/_system/ with no owner approval record
  - 0075 reserves 0079 for the owner's approval at merge; the owner delegated it on 23 September 2026
---
# Row 7: approval of its protected additions, under the owner's delegation

Addendum to [0075](0075-row-7-claims-and-report-renderer.md), which stays byte-identical.
Every file this record touches is new code under the protected prefix `gars/_system/` (spec line 225), so it needs an owner-approval record. The owner delegated that approval on 23 September 2026 ("I delegate every decision to you, use your best judgement … just get things done", recorded in aegis STATE under Carried rules), so this record is written by Glitch under that delegation and labelled as such; it is not in the owner's words.
Its shape follows row 12's [0066](0066-row-12-owner-approval-of-protected-changes.md).
The files themselves arrive with row 7's merge; this commit adds only this record and the regenerated decision index.

## Context

Row 7 (report template → `claims.sql` → `render_report.py`) was built on its own branch from public main `701368f` in three producer commits: the build, a ruling round and one review-fix round.
The owner's words for the row, quoted in 0075, were: "D-10 yes (throwaway local PostgreSQL; R-131 binds only the authoritative DB), methods/reproduction sections left to row 6, decisions 0075-0079, fresh Claude review, push on my word."
During the build the producer stopped on one question, who may register a run that can carry claims, and the owner answered "1": the owner only; a run the writer registers is always exploratory.
0075's first addendum records that ruling.
The row's first independent review (Claude Code, fresh context, round 1 on `9164bae`) was APPROVE WITH CHANGES with one MAJOR (the writer could rewrite committed claims' evidence links), two MINOR findings and three NOTEs.
The final review (round 2 on `554c984`) was APPROVE, with every round-1 finding closed or answered and two NOTEs.
Its SHA-256 is `506bee53bdfffe6b47cb3737faa372e109e2f81a5d96f7aceb86db27874d2268`, and round 1's is `84b089675c8082feb3214c1a1ee01418c01f90a037fc470d69a3996c0cc3b727`; both are kept outside the repository.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected additions as merged, on 2026-09-23. Only the quoted sentences in this record are the owner's words.

1. **The claim store (`gars/_system/claims/claims.sql`, R-080, R-081, R-087).** PostgreSQL 16, applied in one transaction, refusing re-application to a database that already holds it.
   A `claims` schema owned by `gars_claims_owner`, with a writer role `gars_claims_writer` that is neither owner nor superuser.
   Claims are created only through `claim_insert`, which inserts the claim and at least one evidence link in the same transaction; a deferred constraint trigger checks at commit that every claim keeps at least one link.
   The writer holds no TRUNCATE, no direct INSERT on `claim` or `run`, no DELETE on `evidence`, and no UPDATE or DELETE on `claim_evidence`, so a committed claim's evidence cannot be rewritten by the writer.
   `run_register` (the writer's) always creates an exploratory run; `run_register_eligible` (the owner's only) creates a run that can carry claims, and `claim_insert` refuses an exploratory run.
   Confidence is two JSON groups, never a scalar: `bio_support` and `process_risk`, each restricted to its named keys.
2. **The `process_risk` departure (lane call 8, approved by the owner on 23 September 2026).** `process_risk` accepts `qc_disposition` and `limitation` beyond §7.8's three process-risk dimensions; they carry R-141's DEGRADE disposition and its limitation text.
3. **The renderer (`gars/_system/claims/render_report.py`, R-082, R-083, R-141, §8.3).** Stdlib only and Python 3.6-parseable; it reads exactly three inputs: a `claims_export` snapshot (or the database through the container client), the run's manifest, and the shipped template.
   It refuses to emit a report that is missing a section, a HYPOTHESIS carrying an observation verb in any rendered cell, a DEGRADE claim without its limitation, or a claim with no evidence, and on refusal it writes nothing and leaves an existing output untouched.
   A section whose source is absent renders present as `UNKNOWN (owned by …)`; limitations render directly under the claims they affect; differing reference releases render a visible mismatch flag.
4. **The template (`gars/_system/claims/report_template.md`, R-082).** The §7.8 sections in verification order, with a drift test binding the order to the spec copy.

## What this does not close

Copied from 0075, with the run-registration item closed by the owner's ruling 1:

- Deployment to the authoritative database; it waits on R-131's standing verified restore.
- R-120 and R-122: the result-class memory store and `test_memory_no_laundering.py` are not built.
- R-089 STALE on workflow deprecation.
- §8.3's pairing test and R-090, which belong to row 6; the rendered mismatch flag is not the pairing test.
- Row 6's methods and reproduction fields, checks and reruns.
- Per-run cost figures.
- The pilot-1 orphan-claims measurement; README keeps `unmeasured` for that metric, because a synthetic fixture does not meet §17's pilot threshold.
- Superuser and owner containment: those principals can disable triggers. Content truth and concurrency beyond PostgreSQL transaction semantics are outside the threat model.
- Availability guarantees, authentication of supplied snapshot files, and cross-script homoglyph classification.
- The final review's NOTEs: a snapshot evidence list whose elements are empty (`[null]`, `[{}]`) still renders, though the database can never export one (R7R2-01); the producer's fault drivers live outside the repository, so a reader of the branch cannot rerun them (R7R2-02).
- Execution on Python 3.6.8 and on the cluster is not evidenced.
- A review in a fresh context on the same machine and OS user is `independent_context`, not `external_human_seal`.

## Test

The full checks ran at the merge head `bc1ad2b` (row 7 merged onto `dc6a72a`, counts re-derived), with every protected addition this record approves in place, on 23 September 2026, from a fresh clone:
`python3 tests/run_tests.py` in the three CI suite modes printed `Ran 456 tests` and `OK` in each (skipped 11, 73 and 104, the figures README now states; `canary: 0/9` in modes A and B); mode A ran all 21 database tests against a throwaway `postgres:16` stack with none skipped and printed `orphan claims: 0/4`, and `orphan claims: 0/5` after the positive control; `python3 tests/check_contracts.py`: `14 contracts clean`; `python3 tests/check_counts.py`: 456, `enforced=3`, clean; the harness `Ran 44 tests`, `OK`; the pre-registration check clean with `graded=1`; no system-temp leak, and a before/after listing of every Docker container and volume showed nothing new.
At the parent `701368f` both new test modules fail at import, naming the missing `gars/_system/claims/` files; at `554c984` they print `Ran 21 tests … OK` and `Ran 14 tests … OK`.
An independent mutation proof at `554c984` planted twelve faults, one at a time in a disposable copy with byte-for-byte restores: the deferred trigger dropped, TRUNCATE or INSERT on `run` or UPDATE on `claim_evidence` granted to the writer, the exactly-one evidence check dropped, the evidence foreign key made CASCADE, `confidence` accepted with the reserved-key check disabled, a template section removed, an observation-verb family removed, the DEGRADE rule removed, a fourth input file read, and the fixture changed without regenerating its snapshot.
Each turned its named test red and went green again once restored.
Accepting `confidence` in the `bio_support` allow-list alone stays green, because `no_reserved_keys` refuses it at any depth; that second layer is by design.
The secret sweep over `dc6a72a..bc1ad2b` found 0 findings under both rulesets, and no IPv4 address in the added lines.
This record changes no code; with it placed and `bash docs/decisions/build_index.sh` re-run, the record checks and the contracts and counts checks stay clean.

## Status

standing

## Date

2026-09-23
