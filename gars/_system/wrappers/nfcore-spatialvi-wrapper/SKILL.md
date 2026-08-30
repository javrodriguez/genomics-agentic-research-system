---
name: nfcore-spatialvi-wrapper
description: >
  GARS-authored wrapper around nf-core/spatialvi ccdfb48: preflight, audited params translation,
  Slurm submission script with requeue guard, content-checking exit gate and
  artifact registry rows.
metadata:
  openclaw:
    source: gars                    # versioned in this repo (decision 0012)
    pipeline: nf-core/spatialvi
    pipeline_version: "ccdfb48"
    requires:
      bins: [python3, nextflow, java, git]
      python: ">=3.6 (stdlib only)"
    install: >
      Nothing to install for the wrapper itself. Runtime needs the gars-nxf conda
      environment on PATH at submit time, and a pinned local checkout of
      nf-core/spatialvi ccdfb48.
---

# nfcore-spatialvi-wrapper

One stdlib Python file, JSON on stdout, exit codes `0 ok / 1 failure / 2 refused /
3 usage`. The sub-stage contract at
`02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md` orchestrates it;
nothing here is invoked directly by a user.

```
python3 nfcore_spatialvi_wrapper.py check   --project projects/<title>
python3 nfcore_spatialvi_wrapper.py prepare --project projects/<title>
sbatch <substage>/submit.sh                       # written by prepare
python3 nfcore_spatialvi_wrapper.py collect --project projects/<title> --model "<model id>"
```

- `check` — preflight: config complete and sane, samplesheet header and paths,
  pinned checkout tag verified, executor config carries no `params` block, `run/`
  safe to use. Writes `preflight/check_result.json`.
- `prepare` — re-validates, then writes `params.yaml`, `submit.sh` and
  `reproducibility/{manifest.json,commands.sh}`. Deterministic bytes.
- `collect` — the exit gate: content-checked, not existence-checked. Writes
  `OUTPUTS.tsv` and `STATUS`, returns the `history_entry` to append verbatim.

## Produced artifacts

| Type | Path |
|---|---|
| `h5ad` | `run/results (per-sample: <sample>/data/<sample>.h5ad)` |
| `report` | `run/results (per-sample: <sample>/reports/report-<sample>.html)` |
| `qc_multiqc` | `run/results/multiqc/multiqc_report.html` |
