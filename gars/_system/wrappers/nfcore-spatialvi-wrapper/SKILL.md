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

## Validation status

Fully validated, in two venues.

**Tier A (macOS, Docker):** the pipeline ran at the pin in downstream mode on its own public
test data — 49 of 51 processes completed. The `h5ad` and `report` gates were proven against
that real tree with negative controls (a removed processed matrix refused with the raw object
present and deliberately unused; a removed report refused). MultiQC could not execute there:
Polars dies with `Illegal instruction` under Rosetta x86-64 emulation, and spatialvi exposes no
`skip_multiqc` — so the `qc_multiqc` gate's passing path was, at that point, honestly recorded
as unproven.

**Tier B (BigPurple, Slurm + Apptainer, native x86-64, 2026-08-30):** a real GARS project was
driven through stage 00 → 01 → check → prepare → `sbatch` → collect. The run completed
(45m50s) and `collect` returned ok on every gate — **including `qc_multiqc`, against a real
4.8 MB MultiQC report**. The two per-sample processed AnnData objects and reports resolved at
their exact names.

That tier-B pass came after two live catches, both fixed and tested:

- the first run died at apptainer's default 20-minute pull budget converting the fat
  harmonypy+scanorama wave container — the executor template now carries
  `apptainer.pullTimeout = 90m`;
- the second died in `SDATA_READ_VISIUM` because the preflight accepted a sample directory
  that merely *held* `outs/` — the pipeline reads the outs level directly, and `check` now
  refuses that layout naming `<dir>/outs` as the fix.
