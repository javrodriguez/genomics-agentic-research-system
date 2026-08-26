---
date: 2026-08-25
status: standing
touches:
  - gars/_system/wrappers/nfcore-chipseq-wrapper/
  - gars/_system/wrappers/nfcore-cutandrun-wrapper/
  - gars/_system/wrappers/nfcore-methylseq-wrapper/
  - gars/_system/stage01_samplesheet.py
  - gars/_system/configure.py
  - gars/_references/assay_stage_skill_map.md
  - gars/_references/artifact_types.md
---
# Wrappers #3–#5: every planned assay is wired, and validation went per-assay

## What happened

With the wrapper pattern proven ([0028](0028-wrappers-are-thin-system-helpers.md)) and the
design table assay-aware ([0030](0030-the-design-table-is-assay-aware.md)), the remaining
three assays followed in one pass: `nfcore-chipseq-wrapper` (nf-core/chipseq 2.1.0),
`nfcore-cutandrun-wrapper` (nf-core/cutandrun 3.2.2), `nfcore-methylseq-wrapper`
(nf-core/methylseq 4.2.0). Each pipeline was cloned over the git protocol at its pinned tag,
and every samplesheet column, parameter name and output path was read from the checkout —
`assets/schema_input.json`, `nextflow_schema.json`, `docs/output.md`, `conf/modules.config` —
never remembered. That discipline caught what memory would have missed: **chipseq 2.1.0 calls
peaks with MACS3**, not MACS2; its consensus sets are **per antibody**; cutandrun's outputs
live under numbered directories with MultiQC at `04_reporting/multiqc/`.

## Per-assay facts now encoded

- **chipseq**: `control_replicate` is *derived* by stage 01 (the replicate of the referenced
  control sample) — a computable value is never typed ([0011](0011-deterministic-artifacts-in-stages-00-01.md)).
  `check` refuses a sheet with no IPs, or an IP without a control.
- **cutandrun**: the sheet is group-shaped and `control` names the IgG **group**; spike-in
  calibration is the assay's signature, so `spikein.fasta` ships in the seeded config pointing
  at the local E. coli K12 mirror, with `peakcaller`/`normalisation`/`use_control` as
  presented defaults. No derived cache yet — the first live run establishes what is worth
  harvesting.
- **methylseq**: FASTA only, no annotation, no second config decision. The exit gate demands
  a coverage file **per sample**. The first run builds the Bismark index (none exists for
  plain human here, verified 2026-08-14); the seeded compute block budgets for it.
- Artifact vocabulary +3 (`methylation_coverage`, `methylation_calls`, `bedgraph`), through
  the sanctioned extension route.

## Two validation rules became per-assay, caught by the tests

Both were RNA-era rules silently encoding bulk-RNA assumptions — exactly the class
DEVELOPMENT.md's "does the design generalise?" worry named:

1. **Replicate uniqueness** was keyed on `(group, condition, replicate)`; a ChIP IP and its
   input share all three and are distinguished by `antibody`. The identity key now includes
   the assay's extra design columns except `control` (a pointer, not identity).
2. **The group-of-one refusal** ("cannot be tested for differential expression") is
   meaningless where no DE happens, and wrong for cutandrun, where a one-sample IgG group is
   normal. It now applies to `rnaseq_bulk` only.

The generalisation question is thereby part-answered: the assay map, artifact vocabulary and
router extended without structural change; the two hidden assumptions found were in stage 01
validation prose-adjacent code, and the offline test suite (34 tests) found both on the first
run of the new fixtures.

## What a live run must still prove

Everything mechanical is offline-tested (config seeding → menus → emission → check/prepare →
faked-results collect, per assay). What no test can prove: the pipelines completing on this
cluster under these params, the real output trees matching the gates built from their docs,
and the ChIP/CUT&RUN control semantics surviving contact with nf-core's own samplesheet
validation. One live run per assay is the outstanding item, recorded in DEVELOPMENT.md.
