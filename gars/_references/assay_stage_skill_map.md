## Assay -> Stage -> Sub-Stage -> Skill Map

The Assay column is the definitive list of assays this system supports. The Assay ID is the
directory-safe name used for that assay everywhere on disk: `00_data/<Assay ID>/` in a project,
and `02_bioinformatics/<Assay ID>/` for its sub-stages.

| Assay | Assay ID | Stage | Sub-stages (ordered) | Skills |
|---|---|---|---|---|
| Bulk RNA-seq | rnaseq_bulk | 02_bioinformatics | 01_nfcore-rnaseq-wrapper, 02_rnaseq-de | nfcore-rnaseq-wrapper, rnaseq-de |
