# Sub-stage 02.02 (scrnaseq): Single-cell QC and Clustering

## Purpose
Turn the count matrix produced by 02.01 into a filtered, clustered, annotated AnnData object
with per-cluster markers, through `scrna-qc-cluster` (decisions 0028, 0039). This sub-stage
submits the job and returns; it does not wait for completion. A later invocation reads `STATUS`
and collects results.

**The computation is not yours.** The wrapper's `check` validates, `prepare` generates
`scripts/run_scrna.py` and `submit.sh`, and `collect` runs the exit gate and writes
`OUTPUTS.tsv` and `STATUS`. Your job is the dialogue between those calls and the verbatim
reporting of what they return.

## Inputs
1. **The `h5ad` from 02.01** — resolved by artifact type by stage 02's router
   (`_system/resolve_artifact.py`) and passed as `--h5ad`. Never located by hand.
2. **`_config/scrnaseq.yaml`** — the QC thresholds, HVG count and clustering resolution
3. **`01_samplesheets/scrnaseq_samplesheet.csv`** — the independent source the exit gate checks
   the analysis's per-sample cell counts against
4. **The wrapper** — `$GARS_WRAPPERS/scrna-qc-cluster/scrna_qc_cluster.py`

## Scope Boundaries
This sub-stage performs the steps in Process and nothing else.

- Never edit `scripts/run_scrna.py`. `prepare` generates it, and a hand-edit makes the manifest
  a lie. If the analysis needs to change, that is a wrapper change to report.
- **Never lower a QC threshold to make a sample survive.** `qc.min_genes`, `qc.min_cells` and
  `qc.max_mito_pct` decide which cells are real. Loosening one until a poor sample passes is
  manufacturing a result. A sample that filters down to nothing is a **finding to report**.
- Never raise `cluster_resolution` to reach a cluster count someone expected, and never lower
  it to merge clusters that look untidy. Resolution is recorded in `HISTORY.md`; changing it is
  a re-analysis, not a tweak.
- **Never pip- or conda-install a missing package.** If `check` reports the analysis
  environment is missing `scanpy` or `leidenalg`, that is a pinned environment change
  (`_references/environment.md`), not something to fix in the moment. Report and stop.
- Never open, filter or re-cluster the produced `.h5ad` yourself, and never re-run the analysis
  in the foreground to "just see" a number.
- Never interpret the clusters biologically. Report counts, paths and the report location only.
  Naming a cluster a cell type is stage 03's business, with a plan.
- Never run in the foreground, never poll in a loop, never resubmit a `SUBMITTED`/`RUNNING` job.
- Never delete or move a populated `run/` directory; `check` refuses it for a reason.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Definitions

**Wrapper invocation.** From the workspace root, on stock python — the analysis's own
environment arrives via `$GARS_PY` inside `submit.sh`:

```bash
python3 _system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py <subcommand> \
    --project projects/<title> --h5ad <resolved path>
```

Exit codes are the stage-helper standard: 0 ok, 1 failure, 2 refused (a gate), 3 usage.

**Failure vocabulary.** `preconditions` (the h5ad is missing, the samplesheet is absent, or the
analysis environment lacks a named package), `config` (a threshold is absent or not a number),
`config_unfilled`, `output_dir`. `collect` reuses the artifact type names — `table`, `h5ad`,
`figure`, `report` — plus `summary`, for the cross-check described below.

**Why the cell-level checks live here.** 02.01's wrapper is stdlib-only and cannot open an HDF5
file, so its gate can prove only that every sample produced *a* matrix. Here the analysis runs
under `$GARS_PY` and writes `run/summary.json` — cells in, cells after QC per sample, cluster
count, and the thresholds used. `collect` checks those numbers **against the samplesheet**. A
self-reported summary trusted on its own would gate nothing.

**The sample-label suffix.** nf-core/scrnaseq labels cells with the sample id plus its input
type — `Sample_X_filtered`, not `Sample_X` (verified on a real run). The gate matches a label to
a sample when it is the id or the id followed by an underscore-qualifier. If you see a
`summary` failure naming a label that matches no sample, that is a real mismatch, not this rule.

**Execution venue.** Always `sbatch` (decisions 0005, 0027). Clustering a real matrix is not
login-node work — a pure-Python analysis step was SIGKILLed on a login node once.

**Produced artifacts.** `h5ad`, `table`, `figure`, `report` — see `_references/artifact_types.md`.
Both this sub-stage and 02.01 produce `h5ad`; the resolver takes the first `native` match in
reverse sub-stage order, so a later consumer gets the **processed** object, which is what it
means.

## Process
1. Reply T1.
2. Read the STATUS file. If it is `SUBMITTED`, `RUNNING`, or `COMPLETE`, stop — stage 02's
   router already handles those states and should not have routed here.
3. Run the wrapper's `check` with the resolved `--h5ad`. Exit 1 → reply T5 with its `failures`
   verbatim and stop. Do not fix causes yourself: a missing package is an environment change,
   a missing h5ad means 02.01 has not completed.
4. Run `prepare`. Exit 1 → reply T5 (same rule). Exit 0 → it wrote the script, `submit.sh` and
   the reproducibility bundle; report nothing yet.
5. Submit with `sbatch <sub-stage dir>/submit.sh`. Capture the job ID.
6. Write `STATUS` as `SUBMITTED <job_id> <iso8601>`. Reply T2 and stop. Do not wait or poll.
7. **On a later invocation** where STATUS is `SUBMITTED` or `RUNNING`: query `sacct`/`squeue`.
   If still active, update STATUS to `RUNNING <job_id> <iso8601>`, reply T3, stop.
8. If the job has finished, run `collect` with `--model "<the exact model id you are running
   as>"` and `--h5ad-from <the sub-stage that supplied the matrix>` (decision 0024). Exit 2 →
   the run did not complete: write `STATUS` as `FAILED <iso8601>`, reply T4, stop. Exit 1 →
   the exit gate failed: write `FAILED`, reply T4 with its `failures` verbatim, stop.
9. Exit 0 → append its `history_entry` to the project's `HISTORY.md` **verbatim**, replacing
   `<ISO-8601 date>` with today's date, and reply T6.

## Response Format
Every message you send in this sub-stage is one of the templates below, with placeholders
filled. Add nothing else: no observations, no suggestions, no biological interpretation.

One standing exception, from `_references/contract_standard.md` ("the bounded voice"): if the
user asks a direct question, answer it from this workspace's own files — read-only, in a short
paragraph — then restate the pending wait point.

**T1 — Start**
```
Sub-stage 02.02: single-cell QC and clustering.
Assay: scrnaseq
Matrix: <h5ad path> (supplied by <sub-stage>)
Thresholds: min_genes <n> | min_cells <n> | max_mito <n>% | HVG <n>
Clustering: Leiden, resolution <r>
```

**T2 — Submitted**
```
Checks passed. Submitted to Slurm as job <job_id>.

Output: 02_bioinformatics/scrnaseq/02_scrna-qc-cluster/run/
Status: 02_bioinformatics/scrnaseq/02_scrna-qc-cluster/STATUS

Check progress: squeue -j <job_id>
Run stage 02 again when it finishes to collect results.
```

**T3 — Still running**
```
Job <job_id> is <state>, submitted <timestamp>. Nothing was resubmitted.

Check progress: squeue -j <job_id>
```

**T4 — Failed**
```
Sub-stage 02.02 failed at <stage: analysis|exit gate>.

<verbatim wrapper failures or Slurm error>

STATUS set to FAILED. Nothing was retried, nothing was deleted.
Log: 02_bioinformatics/scrnaseq/02_scrna-qc-cluster/logs/<log file>
```

**T5 — Preconditions not met**
```
Cannot start sub-stage 02.02.

<the wrapper's failures, verbatim, one line each: check + detail>

<what the user must do: complete 02.01 / add the named packages to the analysis environment /
fill the config>
```

**T6 — Complete**
```
Sub-stage 02.02 complete.

| Measure | Value |
|---|---|
| Cells in | <n> |
| Cells after QC | <n> |
| Clusters | <n> (resolution <r>) |
| Marker rows | <n> |

| Artifact | Path |
|---|---|
| Processed matrix | <h5ad path> |
| Cluster markers | <table path> |
| UMAP | <figure path> |
| Report | <report path> |

Per-sample cells retained are in the report. Read it before anything consumes these clusters —
see Human check.
```

## OUTPUT
Written to `projects/<project_title>/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/`:

| Artifact | Contents |
|---|---|
| `STATUS` | Sub-stage state. The authority on completion. |
| `scripts/run_scrna.py` | The generated analysis. Re-runnable alone; never hand-edited. |
| `submit.sh` | The generated Slurm script. |
| `preflight/check_result.json` | Preflight verdict. Diagnostic only. |
| `reproducibility/` | `manifest.json` (input checksums, thresholds), `commands.sh`. |
| `logs/` | Slurm stdout/stderr. |
| `run/summary.json` | Cells in/out per sample, clusters, and the thresholds used. |
| `run/report.md` | The human-readable summary, including per-sample retention. |
| `OUTPUTS.tsv` | Artifacts by type, written by `collect`. |

`00_data/`, `01_samplesheets/` and 02.01's directory are never modified.

## Human check
Open `run/report.md` and compare **cells retained against cells in, per sample**. Confirm no
sample lost a far larger share than its siblings — one sample retaining a tenth of the cells the
others kept is a failed library or a wrong chemistry, and every cluster downstream will still
look clean. Then open `run/figures/umap_clusters.png` and confirm the clusters are not simply
one per sample: clusters that track the sample label rather than biology mean a batch effect
that this sub-stage does not correct.
