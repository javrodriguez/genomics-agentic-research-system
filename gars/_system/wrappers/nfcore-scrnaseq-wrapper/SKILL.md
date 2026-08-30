---
name: nfcore-scrnaseq-wrapper
description: >
  GARS-authored wrapper around nf-core/scrnaseq 4.2.0: preflight, audited params translation,
  Slurm submission script with requeue guard, content-checking exit gate and
  artifact registry rows.
metadata:
  openclaw:
    source: gars                    # versioned in this repo (decision 0012)
    pipeline: nf-core/scrnaseq
    pipeline_version: "4.2.0"
    requires:
      bins: [python3, nextflow, java, git]
      python: ">=3.6 (stdlib only)"
    install: >
      Nothing to install for the wrapper itself. Runtime needs the gars-nxf conda
      environment on PATH at submit time, and a pinned local checkout of
      nf-core/scrnaseq 4.2.0.
---

# nfcore-scrnaseq-wrapper

One stdlib Python file, JSON on stdout, exit codes `0 ok / 1 failure / 2 refused /
3 usage`. The sub-stage contract at
`02_bioinformatics/scrnaseq/01_nfcore-scrnaseq-wrapper/CONTEXT.md` orchestrates it;
nothing here is invoked directly by a user.

```
python3 nfcore_scrnaseq_wrapper.py check   --project projects/<title>
python3 nfcore_scrnaseq_wrapper.py prepare --project projects/<title>
sbatch <substage>/submit.sh                       # written by prepare
python3 nfcore_scrnaseq_wrapper.py collect --project projects/<title> --model "<model id>"
```

- `check` — preflight: config complete and sane, samplesheet header and paths,
  pinned checkout tag verified, executor config carries no `params` block, `run/`
  safe to use. Writes `preflight/check_result.json`.
- `prepare` — re-validates, then writes `params.yaml`, `submit.sh` and
  `reproducibility/{manifest.json,commands.sh}`. Deterministic bytes.
- `collect` — the exit gate: **every sample in the samplesheet must have produced its own
  converted matrix**, and the combined matrix and MultiQC report must be non-empty. Writes
  `OUTPUTS.tsv` and `STATUS`, returns the `history_entry` to append verbatim.

## Produced artifacts

`<aligner>` below is the configured quantifier — `simpleaf`, `star` or `kallisto`.

| Type | Path |
|---|---|
| `h5ad` | `run/results/<aligner>/mtx_conversions/combined_*.h5ad` |
| `qc_multiqc` | `run/results/multiqc/multiqc_report.html` |

Per-sample matrices sit alongside at `mtx_conversions/<sample>/`; the exit gate reads that set
to prove no sample was lost. Paths were read from the pinned checkout's `conf/modules.config`,
not from the docs.

## Two things this wrapper refuses, and why

**A protocol the chosen aligner does not support.** nf-core/scrnaseq passes an unrecognised
`--protocol` to the aligner *verbatim* rather than rejecting it (`docs/usage.md`), so a wrong
chemistry runs to completion and publishes a scrambled matrix. `check` reads the supported set
from the checkout's own `assets/protocols.json`, so the wrapper cannot disagree with the
version it is pinned to. `auto` is never valid here — it works only with the cellranger
aligners.

**A duplicate sample id.** This pipeline's `sample` column carries `meta: ["id"]` — it is the
sample id, unlike the ATAC/ChIP-family sheets where `sample` is the group and rows repeat per
replicate (decision 0035). Two rows sharing an id would be merged into one barcode space.

## Deliberately not offered

The `cellranger`, `cellrangerarc` and `cellrangermulti` aligners. All three need the
proprietary Cell Ranger binary, which cannot be shipped in a container and requires a per-site
licence acceptance. An option that cannot run is worse than three that can.

A `.h5ad` is HDF5 and this wrapper is stdlib-only, so no cell-level check is attempted here.
Cell counts and QC thresholds belong to a downstream analysis sub-stage running under
`gars-bio`, which can open the file.
