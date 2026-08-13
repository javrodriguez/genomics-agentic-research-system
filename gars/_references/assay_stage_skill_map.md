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
