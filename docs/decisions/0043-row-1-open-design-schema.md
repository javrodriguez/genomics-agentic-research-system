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

## Owner rulings, 14 Sep 2026

**D-27 — owner ruling 1A:** The floors count distinct `sample_id`, so subject-level pseudoreplication passes stage 01 when `unit_of_replication: subject`. The fix (count distinct subjects per level when the unit is `subject`) belongs to a later row with its own planted fixture. This row retains the floors and records D-27 beside D-23 and D-24.

**Owner ruling 2A:** When the agent writes `unit_of_replication`, `reference_release` or `paired`, stage 01's contract requires a HISTORY.md entry quoting the user's answer verbatim and naming the key and value. The design-check record adds declarations for those keys and RNA strandedness, with value, provenance and history_ref. Provenance compares the config scalar with the stage-00 template seed; it describes config origin, not verified human authorship. Missing keys are absent; exact seed values are seeded_default (including unfilled required placeholders, whose validated value is empty); other supplied values are declared_in_config. history_ref identifies the last HISTORY.md line naming `key: value`, including its line number and text, or null. This lookup does not authenticate who wrote the entry or verify that the quotation is faithful. Pairing without such a reference records and reports `paired declared without a HISTORY entry quoting the user` without refusal. No menu or guard rule is added. Tests: `test_seeded_declarations`, `test_declared_provenance`, `test_paired_history_provenance`, `test_paired_without_history_warning`, and `test_record_exit_gate_detects_tampering`.

**Partial supersession (F2):** This record partially supersedes 0011's missing-strandedness default and 0019/0020's assumption that all these scientific values are already seeded or supplied through stage-02 menus. Stage 00 still seeds RNA `strandedness: auto`; stage 01 accepts that seed, but refuses missing/blank strandedness. RNA/ATAC templates now seed required placeholders for replication unit and reference release so stage 00 and T4 expose the questions early. Stage 01 obtains user declarations through T9 and records their provenance; stage-02 reference/formula/contrast menus and deterministic artifact ownership remain intact. The in-place historical rewrites in ec2006c are withdrawn: original bodies and reviewed documents are restored to f7cf4d6, with only the superseded status lines changed in 0011/0019/0020. Reviewed-document commentary lives in separate dated addenda.

**F4 boundary:** The sealed runner prints only the count of failures outside the expected reason for each numbered project, without changing catch semantics or the seal interface. Independent resealing against the updated interface remains the owner's work.
