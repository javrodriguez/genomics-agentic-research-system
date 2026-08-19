---
date: 2026-08-12
status: standing
touches:
  - gars/_references/artifact_types.md
  - gars/_references/assay_stage_skill_map.md
  - gars/02_bioinformatics/CONTEXT.md
---
# Artifact reuse across sub-stages: OUTPUTS.tsv and a closed type vocabulary

**Question:** do different sub-stages and skills consume the same processed data (trimmed FASTQ,
BAM, counts), and can GARS recycle it instead of reprocessing?

**Method.** All 96 installed ClawBio skills, checked three ways. Frontmatter alone is not
trustworthy: only 53 of 96 declare `inputs`/`outputs`, and those undercount badly — exactly one
skill declares BAM input. So argparse flags were parsed from every script (83 skills) and the
`Input Formats` tables read from each SKILL.md.

**There is no machine-readable type system to build on.** 56 of 83 skills take a generic
`--input` and infer the type. Any typing must come from GARS.

**Finding 1 — the catalogue is mostly not NGS preprocessing.** Of 96 skills only ~17 touch NGS
data, and just three consume FASTQ: the nfcore-rnaseq, nfcore-sarek and nfcore-scrnaseq
wrappers. The other ~79 operate on already-derived data. The opportunity is therefore
**derived-artifact fan-out**, not raw-data reprocessing.

**Finding 2 — where consumers actually converge:**

| Artifact | Direct consumers | Size | Value |
|---|---|---|---|
| VCF | 10 | MB | highest |
| Count matrix | ~8 | MB | highest |
| FASTQ samplesheet | 4 | KB | high |
| h5ad | 4 | GB | medium |
| BAM | **~0 directly** | 17 GB/sample | see below |

Most-depended-on skills by in-degree: `scrna-orchestrator` (5), `diff-visualizer` (4),
`rnaseq-de` (3) — all consuming tabular output, not alignments.

**Finding 3 — almost nothing consumes BAMs directly.** The only real path is nf-core/rnaseq's
`--skip-alignment` with a `samplesheet_with_bams.csv`, which re-quantifies against a different
annotation without re-aligning. That samplesheet is produced **only** when the original run used
`--save-align-intermeds`.

**Decision: `--save-align-intermeds` was declined** (2026-08-12). Consequence, recorded
deliberately: BAMs from run 26341149 cannot be re-quantified, so changing annotation means a
full rerun. Revisit if re-quantification becomes routine.

**Design, implemented 2026-08-14.** One new file per sub-stage, one controlled vocabulary. No
database, no daemon, no copying. The design below is live: `_references/artifact_types.md` holds
the vocabulary and the `native`/`adapted` roles, and stage 02's router checks `Consumes` before
dispatching. Not yet exercised: no sub-stage has *resolved* an input through `OUTPUTS.tsv` at
run time — 02.02 was handed its counts path directly.

1. `_references/artifact_types.md` — a closed vocabulary: `samplesheet`, `design`,
   `counts_gene`, `counts_transcript`, `bam_genome`, `bam_transcriptome`, `vcf`, `h5ad`,
   `qc_multiqc`. Nothing outside it may be declared.
2. Each sub-stage writes `OUTPUTS.tsv` beside its `STATUS`: `<type>\t<path>`, **paths only,
   never copies**. This mirrors the existing STATUS convention rather than adding a mechanism.
3. The assay map gains `Consumes` / `Produces` columns, so stage 02's router can verify required
   artifacts exist before dispatching — reusing the gate pattern it already applies to STATUS.
4. Resolution rule, stated once in `02_bioinformatics/CONTEXT.md`: a sub-stage needing type T
   searches completed sub-stages' `OUTPUTS.tsv` in reverse order, takes the first match, and
   records the supplying sub-stage in `HISTORY.md`. If none exists it **stops and reports** —
   never regenerates silently, because silent regeneration is how a project ends up with two
   count matrices that disagree.

**Explicitly rejected:**

- *Cross-project artifact sharing* — one project's provenance would depend on another's
  lifecycle. The reference cache is safe only because references are immutable and version-keyed;
  sample data is neither.
- *A content-addressed store* — Nextflow already does this inside `work/`; duplicating it adds
  hashing and garbage collection for no gain.
- *Automatic copying of artifacts* — paths and symlinks only, or the 612 GB problem returns.
