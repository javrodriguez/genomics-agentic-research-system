# Worked example — synthetic project

A 6-sample paired-end bulk RNA-seq project, 2 lanes per sample, two conditions with three
replicates each. **All data is synthetic**: sample IDs are fabricated and paths are placeholders.
Nothing here comes from a real dataset.

It exists to show what each stage writes, without needing a cluster.

## Stage 00 — `00_data/rnaseq_bulk/`

| File | Grain | Owner |
|---|---|---|
| `files.csv` | one row per sample-lane (12 rows) | machine — carries `# do not edit` |
| `samples.csv` | one row per sample (6 rows) | the user |
| `raw/` | symlinks to source FASTQs; never copies | machine |

The split is the point. Twelve file rows, six design rows: the user fills `condition`, `group`,
and `replicate` once per sample rather than once per file.

## The human gate

Between stages 00 and 01 a person completes the experimental columns in `samples.csv`. To
analyse a subset, delete rows — stage 01 reports the exclusions, asks for confirmation, and
leaves the raw data in place.

## Stage 01 — `01_samplesheets/`

| File | Consumed by |
|---|---|
| `rnaseq_bulk_samplesheet.csv` | nf-core/rnaseq — `sample,fastq_1,fastq_2,strandedness` |
| `rnaseq_bulk_design.csv` | the differential-expression sub-stage |

The samplesheet is one row per sample-lane with absolute paths. Repeated `sample` values are
merged by nf-core as technical replicates, which is exactly how multi-lane samples should be
handled — verified against a real run, where 12 file rows produced 6 `CAT_FASTQ` processes.

## Configuration — `_config/`

| File | Purpose |
|---|---|
| `rnaseq_bulk.yaml` | reference, aligner, compute, DE formula and contrast |
| `nextflow.slurm.config` | executor settings — which queue pipeline tasks are dispatched to |

Both are written by the user. No stage invents a reference genome or a contrast.

## Stage 02 — `02_bioinformatics/rnaseq_bulk/`

Each sub-stage declares what it produced in `OUTPUTS.tsv`, so the next one finds its inputs
**by type rather than by path**:

| Column | Meaning |
|---|---|
| `type` | From the closed vocabulary in `_references/artifact_types.md` |
| `role` | `native` = exactly what the tool emitted; `adapted` = reshaped for a specific consumer |
| `path` | Relative to the sub-stage directory, so projects stay relocatable |

The `role` column exists because of a real failure. nf-core emits `gene_id, gene_name, <samples>`
while `rnaseq-de` requires the identifier column to be named `gene` and everything after it to be
numeric — so 02.02 must reshape the matrix before its skill will accept it. Without the
distinction the registry would list two `counts_gene` artifacts with no way to tell which is
authoritative, and a later consumer could silently pick a matrix reshaped for someone else's
parser.

Adaptations are written into the adapting sub-stage's **own** directory and may only reshape —
rename or drop columns, change numeric type. Never filter rows, alter values, or aggregate.
