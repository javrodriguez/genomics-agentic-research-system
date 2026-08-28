---
date: 2026-08-28
status: standing
kind: lesson
touches:
  - gars/_system/stage01_samplesheet.py
  - gars/01_prepare_samplesheets/CONTEXT.md
  - docs/decisions/0030-the-design-table-is-assay-aware.md
symptoms:
  - "Replicate ids must start with 1..<num_replicates>"
  - "SAMPLESHEET_CHECK failed"
  - "every replicate appears as its own sample"
  - "IP and input merged into one pipeline sample"
---
# The samplesheet's sample column is the pipeline's, not ours

## What happened

The campaign's second ATAC dispatch (job 26863963) cleared the parser (0034) and then died in
the pipeline's own first process: `Replicate ids must start with 1..<num_replicates>! Sample:
'DKO_rep2, replicate ids: 2'`. nf-core/atacseq 2.x's `sample` column is the GROUP — rows
repeat it per biological replicate, its checker enforces replicate ids exactly 1..N within
each, and repeated (sample, replicate) rows are technical replicates. Our emitter wrote
`sample = sample_id`, so every replicate looked like its own group carrying an illegal
replicate number. The offline promotion (0031) verified the schema's *columns* against the
checkout but assumed the *semantics* — precisely the generalization risk the live runs exist
to catch. chipseq 2.x shares the semantics (its checker matches controls by control GROUP +
`control_replicate`); cutandrun's format had them right all along (its column is literally
named `group`).

## Decision

Read from each pipeline's own `bin/check_samplesheet.py` at the pinned tag, and encoded in
stage 01:

1. atacseq and chipseq emit `sample = design:group`. cutandrun was already correct.
2. chipseq's samplesheet `control` is the control's GROUP, derived from the design's
   sample_id pointer (`lookup:control_group`) beside the existing `control_replicate`.
3. Stage 01 enforces the pipeline's laws early, per group-as-sample assay: (group, replicate)
   unique outright; replicate ids exactly 1..N within each group; and a chipseq group must be
   antibody-homogeneous. A refusal at stage 01 costs seconds; the same refusal inside a Slurm
   job cost an hour of queue and a forensics pass.

## Correction to 0030

0030 ruled that a ChIP IP and its input "legitimately share group, condition AND replicate,
distinguished by antibody". Under sample_id emission that was harmless; under the pipeline's
actual group semantics it would merge IP and input into one pipeline sample. nf-core's own
worked example gives inputs their own sample name (`SPT5_INPUT`). Inputs now take their own
group, and the shared-group clause is corrected in place (the 0017-style dated note).

## The lesson

A column's name is not its meaning. Promotion of an assay format must read the pipeline's
*checker*, not only its schema — the checker is where semantics live, and it is in the pinned
checkout, one file away from the schema that was read.
