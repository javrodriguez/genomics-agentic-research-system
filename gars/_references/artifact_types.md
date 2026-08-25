# Artifact Types

The closed vocabulary a sub-stage may use to declare what it produced. A sub-stage records its
artifacts in `OUTPUTS.tsv`; a later sub-stage finds its inputs by type instead of by hardcoded
path.

**Closed means closed.** A sub-stage that needs a type not listed here stops and asks for the
vocabulary to be extended. Inventing a type defeats the point: the value is that a consumer can
rely on a name meaning one thing.

## Vocabulary

| Type | Contents | Typical producer |
|---|---|---|
| `samplesheet` | Workflow-ready sample manifest, assay-specific columns | 01_prepare_samplesheets |
| `design` | `sample_id,condition,group,replicate`, one row per sample | 01_prepare_samplesheets |
| `counts_gene` | Gene-level count matrix, genes x samples | 02.01 |
| `counts_transcript` | Transcript-level count matrix | 02.01 |
| `tpm_gene` | Gene-level TPM matrix | 02.01 |
| `bam_genome` | Coordinate-sorted, deduplicated genome alignments | 02.01 |
| `bam_transcriptome` | Transcriptome-space alignments | 02.01 |
| `vcf` | Variant calls | variant-calling sub-stages |
| `h5ad` | AnnData single-cell matrix | single-cell sub-stages |
| `de_results` | Differential expression table, one row per gene | 02.02 |
| `qc_multiqc` | Aggregated MultiQC HTML report | 02.01 |
| `gene_id_map` | Identifier translation table, e.g. `gene_id` -> `gene_name` | any adapter |
| `table` | A tabular result of a custom analysis | 03_custom_analysis |
| `figure` | A plot or image produced by a custom analysis | 03_custom_analysis |
| `report` | A human-readable document (md/html/pdf) summarising an analysis | 03_custom_analysis |

The three stage-03 types are deliberately generic: a custom analysis's semantics live in its
`PLAN.md`, which sits beside its `OUTPUTS.tsv` — a consumer that needs to know *what* a `table`
contains reads the plan that produced it. The specific types above them stay preferred wherever
one fits: an analysis that produces a count matrix declares `counts_gene`, not `table`.

## OUTPUTS.tsv

Written by a sub-stage on completion, beside its `STATUS`. Tab-separated, three columns, one
row per artifact:

```
# type          role      path
counts_gene     native    run/upstream/results/star_salmon/salmon.merged.gene_counts_length_scaled.tsv
qc_multiqc      native    run/upstream/results/multiqc/star_salmon/multiqc_report.html
counts_gene     adapted   adapted/counts_gene.tsv
gene_id_map     native    adapted/gene_id_to_name.tsv
```

Paths are **relative to the sub-stage output directory**, so a project stays relocatable. They
are references, never copies — an artifact is recorded where its producer wrote it.

### The `role` column

This is the one thing the design gained from running the 02.01 -> 02.02 handoff for real.

| Role | Meaning |
|---|---|
| `native` | Exactly what the producing tool emitted. Authoritative. |
| `adapted` | A reshaping of another artifact, made to satisfy a specific consumer's input contract. |

An adaptation was unavoidable: nf-core emits `gene_id, gene_name, <samples>` while `rnaseq-de`
requires the identifier column to be named `gene` and every later column to be numeric. Without
the distinction, a registry would list two `counts_gene` artifacts with no way to tell which is
the real one — and a later consumer could silently pick a matrix reshaped for someone else's
parser.

Rules:

- An `adapted` artifact is written into the **adapting sub-stage's own directory**, never over
  the producer's output.
- Resolution prefers `native` unless a contract explicitly asks for an adaptation it created.
- An adaptation may only reshape: rename columns, drop non-essential columns, change numeric
  type. It may never filter rows, alter values, or aggregate. Anything beyond reshaping is
  analysis and belongs in a sub-stage's Process, recorded in `HISTORY.md`.

## Resolution

A sub-stage needing type T searches the `OUTPUTS.tsv` of completed sub-stages in **reverse
sub-stage order** and takes the first `native` match, unless its own contract names an
`adapted` one it produced.

If no match exists it **stops and reports**. It never regenerates the artifact itself — silent
regeneration is how a project ends up with two count matrices that disagree, and no record of
which fed which result.

The supplying sub-stage is recorded in `HISTORY.md`, so every downstream result can name where
its inputs came from.
