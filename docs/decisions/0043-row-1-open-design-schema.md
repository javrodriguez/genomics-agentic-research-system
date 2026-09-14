---
date: 2026-09-13
status: open
kind: decision
touches:
  - gars/_system/stage01_samplesheet.py
  - gars/01_prepare_samplesheets/CONTEXT.md
  - tests/test_stage01_design.py
symptoms:
  - "subject nesting has no declared nesting relation"
  - "reference release has no config field"
---
# Row 1 design schema requires owner decisions

## Context
R-072 defines scientific refusals but not the metadata schema needed to distinguish
subject nesting from a legitimate paired design, or identifiers from arbitrary candidate
covariates. Existing designs have four base columns; `group` and `replicate` have pipeline
identity semantics (0030/0035). Treating all columns as nuisance factors would reject correct
existing designs. `batch` is explicitly a candidate covariate in §7.2 and is now supported.
The existing reference menu is in stage 02 (0020); config stores FASTA/GTF paths, not a
release field. A path substring is not a declaration. Statistical-test records and the
manifest consumer are not yet defined by Row 1's implementation.

## Decision
OPEN — no defaults applied to these material choices. Owner questions:
- How are arbitrary candidate covariates distinguished from identifiers, and how are
  `Subject`, the nesting relation, and the replication unit declared? A subject occurring
  across conditions must not be assumed to violate nesting: it may be paired.
- Where is reference release declared, and when is it chosen without moving the current
  stage-02 reference menu? R-072 check 8 remains pending this answer.
- What Row 1 record carries `unit_of_replication` and the design-check output until the
  manifest's implementation row? No statistical record or manifest is fabricated here.

D-23 and D-24 remain open in the gap assessment. Formula/rank/contrast checks are not moved
into stage 01, and explicit `strandedness: auto` remains accepted. This record does not
resolve either question. Missing RNA strandedness is distinct from explicit `auto`.

## Test-that-proves-it
`python3 tests/test_stage01_design.py` covers the implemented batch, ATAC floor,
strandedness and duplicate-ID behaviors using unsealed development fixtures.
Subject nesting, broader covariates, reference release, statistical records, and full 9/9
acceptance remain unmeasured. Add acceptance cases after the schema decisions are made.

## Status
Open; owner decision required for the listed parts. No self-approval.

## Date
2026-09-13
