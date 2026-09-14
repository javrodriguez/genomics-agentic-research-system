---
date: 2026-09-13
status: standing
kind: decision
touches:
  - gars/_system/stage01_samplesheet.py
  - gars/01_prepare_samplesheets/CONTEXT.md
  - tests/test_stage01_design.py
symptoms:
  - "subject nesting has no declared nesting relation"
  - "reference release has no config field"
---
# Row 1 design schema: owner ruling 2A

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
Owner ruling **2A, 13 September 2026**:
1. RNA/ATAC `samples.csv` may append optional `subject` (donor / patient / model),
   alongside optional `batch`, in either order. Any included blank subject is refused.
   A subject in multiple conditions is refused unless `_config/<assay>.yaml` declares
   `paired: paired`. The key `paired` allows `paired` or `unpaired`; missing/blank
   carries no paired authorization. This is experimental pairing, not read layout.
2. `_config/<assay>.yaml` declares `unit_of_replication`: `sample`, `subject`, or
   `cell_pseudobulk`. Missing/blank is refused; `subject` requires a subject column.
   No default is inferred. Existing sample-ID floors are retained in this row.
3. `_config/<assay>.yaml` declares `reference_release`. Stage 01 refuses missing/blank
   declarations, including unfilled placeholders/nulls, and checks only declaration.
   No genome registry validation is added. Stage 02 keeps the reference menu (0020).
4. Stage 01 writes `01_samplesheets/<assay>_design_check.json` only alongside its
   other outputs, after the write gates. It records every executed validation check
   group, its outcome and findings, and declared replication unit, reference release,
   and pairing. The exit gate re-reads and compares its full content (0010).
   A later manifest row consumes it; no manifest is built here.

These Row 1 declarations apply to rnaseq_bulk and atacseq_bulk. Agents ask for missing
values and write user-supplied declarations through the existing project config path
(0019); they do not invent values or move stage 02 menus. RNA strandedness is explicitly
required; explicit `auto` remains accepted pending D-24. D-23 (formula/rank/contrast)
and broader candidate covariate roles are not resolved by this ruling.

## Test-that-proves-it
`python3 tests/test_stage01_design.py`, unsealed `DevelopmentDesignTests`:
- `test_subject_nesting_and_pairing`, `test_subject_required_and_blank`
- `test_required_declarations`, `test_declaration_values`
- `test_record_write_gates_and_contents`, `test_record_exit_gate_detects_tampering`
- Existing batch, ATAC floor, strandedness, duplicate-ID and clean-design tests.
`SealedDesignTests.test_row_1_recall` retains its interface and 3/3 threshold;
unset sealed fixtures remain SKIPPED, and full 9/9 acceptance remains unmeasured.

## Status
Standing, owner ruling 2A; implementation is not self-approval of Row 1 exit.

## Date
2026-09-13
