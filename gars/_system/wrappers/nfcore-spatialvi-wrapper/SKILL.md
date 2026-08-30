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

## The pin is a commit, and says so

nf-core/spatialvi has no current release. Its only tag, `v0.1.0`, is dated 2023-03-31 and
`git describe` places it **1,014 commits** behind `dev` — it predates Visium HD support and most
of the present pipeline. GARS pins commit `ccdfb48` and `wrapperlib.check_pipeline` verifies it
with `git rev-parse` rather than `git describe --tags`, because `describe` on a detached commit
reports the nearest *ancestor tag*, which is a fact about history and not about the pin.

The `HISTORY.md` entry this wrapper returns says "a development snapshot" in those words. A user
asking what version they ran gets the truth, not an implied release.

## Downstream mode only — Space Ranger is not run here

The input is a Space Ranger output tree per sample, already produced. Running Space Ranger would
need 10x's proprietary binary, a licence acceptance, 64 GB and 8 threads, and supports human and
mouse only — the same exclusion already made for the cellranger aligners in `scrnaseq`.

This is why the assay's `files.csv` carries `sample_id, spaceranger_dir` rather than FASTQ
columns (`workspace.INPUT_KINDS`), and why there are no lanes: one directory per sample, and a
repeated sample id is an error.

## Produced artifacts

| Type | Path |
|---|---|
| `h5ad` | `run/results (per-sample: <sample>/data/<sample>.h5ad)` |
| `report` | `run/results (per-sample: <sample>/reports/report-<sample>.html)` |
| `qc_multiqc` | `run/results/multiqc/multiqc_report.html` |


## The raw AnnData is never substituted for the processed one

spatialvi writes `<sample>-raw.h5ad` beside `<sample>.h5ad`. The raw object is the pre-analysis
extraction; the processed one carries QC, clustering, differential expression and the spatial
results. A `*.h5ad` glob matches both.

The exit gate therefore builds both names explicitly and accepts only the processed file. When
the raw object is the only one present, the refusal says so by name. This rule is here because
the `scrnaseq` wrapper shipped exactly that defect and it was caught only by running the real
pipeline: a glob over `combined_*.h5ad` silently published a 114 MB raw matrix in place of a
1.3 MB filtered one.

## Validation status — honest, and partial on this hardware

The pipeline was run at the pin, in downstream mode, on its own public test data
(`-profile test_downstream,docker`): **49 processes completed, 2 failed.**

- **`h5ad` and `report` are validated against the real output tree.** Both pass when the tree is
  correct, and both fail correctly when a sample's processed matrix or report is removed — the
  raw object present and deliberately not used.
- **`qc_multiqc` is NOT positively validated on Apple Silicon.** MultiQC dies with `Illegal
  instruction`: Polars executes an unsupported CPU instruction under Rosetta x86-64 emulation.
  spatialvi exposes no `skip_multiqc`, so the step is mandatory and there is no honest way
  around it on this machine. The gate behaves correctly — it refuses, because the artifact
  genuinely is absent — but the passing path for that one leg is covered by the offline test
  only, and is outstanding until a run on native x86-64 (the cluster).

No report was fabricated to make that leg green.
