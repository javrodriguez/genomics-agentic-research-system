---
date: 2026-08-25
status: standing
kind: decision
symptoms:
  - "ChIP-family design has no antibody/control columns"
touches:
  - gars/_system/workspace.py
  - gars/_system/stage00_register.py
  - gars/_system/stage01_samplesheet.py
---
# The design table's columns are per-assay

## What happened

`samples.csv` carried a fixed header — `sample_id,condition,group,replicate` — because one
assay existed when it was designed. The ChIP-family pipelines cannot be driven from that: a
ChIP-seq IP sample must name its input-chromatin control, a CUT&RUN target must name its IgG
group, and nf-core/chipseq additionally wants the antibody. The research note
(assay-expansion.md §6.4) called this the remaining blocker for wrapper #2 and asked for one
control *mechanism* with per-assay *validation*, since "every ChIP sample has an input" and
"every CUT&RUN target has an IgG" are different checks against different referents.

## Decision

The column set comes from one function, `workspace.design_columns(assay)`: the base four for
every assay, plus per-assay extras from `EXTRA_DESIGN_COLUMNS` —
`chipseq_bulk: antibody, control` and `cutandrun: control`. Stage 00 writes that header;
stage 01 validates against it and emits the design table with it. Both read the same table,
so the two stages cannot disagree about what a design looks like.

Validation splits by column class, at the grain each check belongs to:

- **Base columns** must be non-blank in every row (`incomplete_design`, as before).
- **Extra columns may be blank** — a ChIP input or an IgG sample legitimately has no control
  of its own. Blankness is not incompleteness here.
- **A non-blank `control` must resolve** within the design (`referential_integrity`): to a
  `sample_id` for chipseq, to a `group` for cutandrun — same column shape, different
  biological referent, exactly as the research required. The referent table lives in stage
  01 beside the check.
- **Whether every target row HAS a control** is the assay wrapper's check, against its own
  pipeline's semantics — stage 01 cannot know which rows are targets.

## Why not a `control` column for every assay

A column that is meaningless for rnaseq and atacseq invites values in it, and a value in a
meaningless column is a question nobody will answer ("does this do anything?"). The header a
user sees is the set of decisions their assay actually needs — the same principle as the
per-assay samplesheet formats (stage 01's `FORMATS`, 0011): sharing a shape an assay does not
want produces files that validate and mean something else.

Existing projects are untouched: rnaseq and atacseq have no extra columns, so their headers
are byte-identical to before.
