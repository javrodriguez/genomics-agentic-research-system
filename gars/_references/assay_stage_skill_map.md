## Assay -> Stage -> Sub-Stage -> Skill Map

The Assay column is the definitive list of assays this system supports. The Assay ID is the
directory-safe name used for that assay everywhere on disk: `00_data/<Assay ID>/` in a project,
and `02_bioinformatics/<Assay ID>/` for its sub-stages.

| Assay | Assay ID | Stage | Sub-stage | Skill | Consumes | Produces |
|---|---|---|---|---|---|---|
| Bulk RNA-seq | rnaseq_bulk | 02_bioinformatics | 01_nfcore-rnaseq-wrapper | nfcore-rnaseq-wrapper | samplesheet | counts_gene, counts_transcript, tpm_gene, bam_genome, qc_multiqc |
| Bulk RNA-seq | rnaseq_bulk | 02_bioinformatics | 02_rnaseq-de | rnaseq-de | counts_gene, design | de_results |

Sub-stages run in the order listed. `Consumes` and `Produces` use the closed vocabulary in
`artifact_types.md`; stage 02's router checks that every consumed type is available before
dispatching a sub-stage.

## Skill requirements

What each skill needs in order to run. A sub-stage that finds a requirement missing reports it
as a preconditions failure **naming the requirement**, rather than surfacing a raw `ImportError`.

| Skill | Python | System binaries | Python packages | Provided by |
|---|---|---|---|---|
| nfcore-rnaseq-wrapper | >=3.10 | `python3`, `nextflow`, `java` | (via `clawbio`) | `gars-bio` + `gars-nxf` |
| rnaseq-de | (unpinned) | `python3` | `pandas`, `numpy`, `matplotlib`, `scikit-learn` | `gars-bio` |

Notes on requirements that are otherwise easy to mistake for unused and prune:

- **`scikit-learn`** is used by `rnaseq-de` for exactly one thing — `PCA(n_components=2)` in
  `run_pca()`, producing `figures/pca.png`. The skill fails at import without it.
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

The authoritative source is each skill's own `SKILL.md` frontmatter
(`metadata.openclaw.requires.bins` and `metadata.openclaw.install`). This table summarises only
the skills GARS actually invokes; regenerate it when the assay map gains a sub-stage or when
`clawbio` is upgraded:

```bash
BIO=~/install/miniconda_clean/envs/gars-bio
SKILLS=$($BIO/bin/python -c "import clawbio, pathlib; print(pathlib.Path(clawbio.__file__).parent / 'skills')")
# read metadata.openclaw from $SKILLS/<skill>/SKILL.md
```

Coverage caveat: across the 95 installed skills, `catalog.json` populates `dependencies` for
only 44, while the `SKILL.md` frontmatter covers 91. Prefer the frontmatter.
