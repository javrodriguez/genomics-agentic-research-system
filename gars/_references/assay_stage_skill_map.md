## Assay -> Stage -> Sub-Stage -> Skill Map

The Assay column is the definitive list of assays this system supports. The Assay ID is the
directory-safe name used for that assay everywhere on disk: `00_data/<Assay ID>/` in a project,
and `02_bioinformatics/<Assay ID>/` for its sub-stages.

| Assay | Assay ID | Stage | Sub-stage | Skill | Source | Consumes | Produces |
|---|---|---|---|---|---|---|---|
| Bulk RNA-seq | rnaseq_bulk | 02_bioinformatics | 01_nfcore-rnaseq-wrapper | nfcore-rnaseq-wrapper | gars | samplesheet | counts_gene, counts_transcript, tpm_gene, bam_genome, qc_multiqc |
| Bulk RNA-seq | rnaseq_bulk | 02_bioinformatics | 02_rnaseq-de | rnaseq-de | gars | counts_gene, design | de_results |
| ATAC-seq (bulk) | atacseq_bulk | 02_bioinformatics | 01_nfcore-atacseq-wrapper | nfcore-atacseq-wrapper | gars | samplesheet | peaks, peaks_consensus, counts_peaks, bigwig, bam_genome, qc_multiqc |
| ChIP-seq (bulk) | chipseq_bulk | 02_bioinformatics | 01_nfcore-chipseq-wrapper | nfcore-chipseq-wrapper | gars | samplesheet | peaks, peaks_consensus, counts_peaks, bigwig, bam_genome, qc_multiqc |
| CUT&RUN / CUT&Tag | cutandrun | 02_bioinformatics | 01_nfcore-cutandrun-wrapper | nfcore-cutandrun-wrapper | gars | samplesheet | peaks, peaks_consensus, bigwig, bam_genome, qc_multiqc |
| Bisulfite (WGBS/RRBS) | methylseq | 02_bioinformatics | 01_nfcore-methylseq-wrapper | nfcore-methylseq-wrapper | gars | samplesheet | methylation_coverage, methylation_calls, bedgraph, qc_multiqc |

The **Source** column says where a skill's code lives (decision 0012). Every current row is
`gars`: wrappers versioned in this repository under `_system/wrappers/`, resolved via
`$GARS_WRAPPERS`. (`clawbio` was the earlier kind — retired by decision 0029.)

Sub-stages run in the order listed. `Consumes` and `Produces` use the closed vocabulary in
`artifact_types.md`; stage 02's router checks that every consumed type is available before
dispatching a sub-stage.

## Skill requirements

What each skill needs in order to run. A sub-stage that finds a requirement missing reports it
as a preconditions failure **naming the requirement**, rather than surfacing a raw `ImportError`.

| Skill | Python | System binaries | Python packages | Provided by |
|---|---|---|---|---|
| nfcore-rnaseq-wrapper (gars) | >=3.6 (stdlib only) | `python3`, `nextflow`, `java`, `git` | none | stock python + `gars-nxf` at submit time |
| rnaseq-de (gars) | wrapper: >=3.6 stdlib; analysis: `$GARS_PY` | `python3`, `git` | `pandas`, `numpy`, `pydeseq2`, `matplotlib`, `scikit-learn` (analysis only) | stock python + `gars-bio` at run time |
| nfcore-atacseq-wrapper | >=3.6 (stdlib only) | `python3`, `nextflow`, `java`, `git` | none | stock python + `gars-nxf` at submit time |
| nfcore-chipseq-wrapper | >=3.6 (stdlib only) | `python3`, `nextflow`, `java`, `git` | none | stock python + `gars-nxf` at submit time |
| nfcore-cutandrun-wrapper | >=3.6 (stdlib only) | `python3`, `nextflow`, `java`, `git` | none | stock python + `gars-nxf` at submit time |
| nfcore-methylseq-wrapper | >=3.6 (stdlib only) | `python3`, `nextflow`, `java`, `git` | none | stock python + `gars-nxf` at submit time |

The clawbio `nfcore-rnaseq-wrapper` and `rnaseq-de` skills are retired (decision 0029) and
remain installed with the package but uninvoked; their deprecated procedure files were deleted
2026-08-27 after all three switchover criteria were met on a live run.

- **`scikit-learn`** is used by the DE analysis for exactly one thing — `PCA(n_components=2)`
  producing `figures/pca.png`. The generated script fails at import without it.

Notes on requirements that are otherwise easy to mistake for unused and prune:

- **`nextflow` and `java`** live in `gars-nxf`, not `gars-bio`. They cannot share an environment
  with `clawbio`: conflicting `c-ares` constraints make the solve unsatisfiable. Both are on
  `PATH` when a sub-stage runs.
- **`apptainer` and `squashfuse` are not skill requirements.** They are the container runtime the
  pipeline needs, and belong to the execution substrate rather than to any skill. Without
  `squashfuse`, Apptainer cannot mount SIF images and unpacks each multi-GB image on every
  container launch.

Note also that the skills do **not** carry the pipeline's own tool dependencies. nf-core/rnaseq
declares a container per module — all 78 of them — so STAR, Salmon, samtools and the rest are
supplied by images, not by this environment. That is why `gars-bio` contains no aligner.

The authoritative source is each wrapper's own `SKILL.md` frontmatter under
`_system/wrappers/<name>/`. This table summarises only the skills GARS actually invokes;
regenerate it when the assay map gains a sub-stage.

Coverage caveat: across the 95 installed skills, `catalog.json` populates `dependencies` for
only 44, while the `SKILL.md` frontmatter covers 91. Prefer the frontmatter.
