---
date: 2026-08-12
status: standing
touches:
  - gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md
  - gars/_references/config_schema.md
---
# Execution: the six pipeline failures and what each one changed

Each of these was found by running, not by reading.

| # | Failure | Cause | Fix |
|---|---|---|---|
| 1 | Pipeline fetch failed | GitHub REST API rate limit (60/hr, shared site IP) | Clone via git protocol; `--pipeline-local` |
| 2 | Valid checkout rejected as version `master` | **Upstream bug**: `_MANIFEST_VERSION_RE` lookbehind `(?<![A-Za-z])` fails to exclude `custom_config_version` | `--allow-pipeline-version-override` after verifying `git describe --tags`; reported as [ClawBio#333](https://github.com/ClawBio/ClawBio/issues/333) |
| 3 | Task killed mid-run | `NODE_FAIL`; Nextflow dispatched child jobs to an unintended partition | `_config/nextflow.slurm.config` setting `process.queue` + `maxRetries=3` |
| 4 | Resume rejected | Guard keyed on a Nextflow session; wrapper requires `reproducibility/manifest.json`, written only on success | Guard branches on manifest; a crashed run cannot be resumed and must exit clearly |
| 5 | `SUBREAD_FEATURECOUNTS` failed after counts were written | iGenomes GRCh38 is **NCBI** and has no biotype attribute | Ensembl GRCh38 r116, which provides `gene_biotype` |
| 5b | STAR rejected the index | Prebuilt site index built with STAR 2.7.1a; nf-core runs 2.7.11b | Let nf-core build the index; never reuse one without checking its version |

**Contract defects found the same way:** preflight and the real run pointed at the same output
directory (wrapper rejects a populated `--output`); no verification that samplesheet absolute
paths still resolve after a project move.

**Preemption was a red herring.** A "preemption ratio" was used to choose partitions before
checking `scontrol show config` — which reports `PreemptMode = OFF`. Preemption is not enabled
on this cluster; every infrastructure failure was hardware. The metric accidentally correlated
with node-failure rate, which is why the partition switch still helped.
