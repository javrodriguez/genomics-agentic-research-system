# Project: demo-project

| Field | Value |
|---|---|
| Created | 2026-08-18 |
| Template version | v0.4.0 |

## Assays

| Assay | Assay ID | Data directory | Files | Samples |
|---|---|---|---|---|
| Bulk RNA-seq | rnaseq_bulk | `00_data/rnaseq_bulk/` | 24 | 6 |

## Raw data sources

| Assay ID | Source path | Files linked |
|---|---|---|
| rnaseq_bulk | `/path/to/sequencing/run_2026_03/` (synthetic — no such path) | 24 |

Raw data is symlinked, never copied. The source path is recorded so a broken link can be traced.

## Stage state

State is not recorded here. It is derivable from the filesystem:

| Question | Answer from |
|---|---|
| Is the design complete? | `00_data/<Assay ID>/samples.csv` — experimental columns filled |
| Have samplesheets been emitted? | `01_samplesheets/` |
| How far has an assay run? | `02_bioinformatics/<Assay ID>/<sub-stage>/STATUS` |
| What did a sub-stage produce? | that sub-stage's `OUTPUTS.tsv` |

`HISTORY.md` records what happened and when. This file records what the project *is*.

## Configuration

`_config/<Assay ID>.yaml` and `_config/nextflow.slurm.config` are written by the user before
stage 02 runs. Schema: `_references/config_schema.md`. Nothing writes them automatically —
every key is a scientific decision the system must not make on the user's behalf.
