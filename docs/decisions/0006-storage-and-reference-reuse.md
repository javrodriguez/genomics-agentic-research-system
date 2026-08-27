---
date: 2026-08-12
status: standing
kind: decision
symptoms:
  - "612 GB of scratch consumed by failed runs"
  - "indexes rebuilt every run"
touches:
  - gars/_references/config_schema.md
  - gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md
---
# Storage and reference reuse: work_dir on scratch, version-keyed index cache

Four failed runs consumed **612 GB**. Accounting for one 10-sample run:

| Item | Size |
|---|---|
| STAR index, Salmon index, transcripts FASTA, decompressed genome | ~46 GB, **rebuilt every run** |
| Merged (`CAT_FASTQ`) + trimmed FASTQs | ~56 GB |
| Genome / transcriptome / sorted / markdup BAMs | ~17 GB per sample |

Two structural causes:

1. **`work/` never cleans up.** Nextflow keeps every process output so `-resume` can reuse it,
   so the trimmed FASTQ, unsorted BAM, sorted BAM and deduplicated BAM all coexist. It also
   defaulted to `<output>/upstream/work` — *inside the project*.
2. **Derived references are discarded.** `save_reference = false` means the STAR/Salmon indices
   are built into `work/` and never published, so they are regenerated on every run and deleted
   with it. Three runs rebuilt them: ~130 GB of pure repetition.

Note the raw FASTQs are **not** duplicated — GARS symlinks them and Nextflow's default
`stageInMode` is also symlink. `results/` is safe to keep alone because
`publish_dir_mode = 'copy'` gives it real files, not pointers into `work/`.

Fixes applied to the config schema and the 02.01 contract:

- **`compute.work_dir`** — required, on scratch, never inside the project.
- **`reference.derived_dir`** — optional cache of built indices. Populate it once via
  `--save-reference`, reuse thereafter.
- **The cache is keyed by pipeline version** (`derived/nf-core-rnaseq-3.26.0/`), because a STAR
  index built by a different STAR version is rejected outright. Keying by genome build alone
  recreates the exact trap that killed run 26310826.
- 02.01 must read `versionGenome` from `genomeParameters.txt` before reusing a cached index.
