# Sub-stage 02.02 (spatialvi): Spatial Cluster Count

## Purpose
Count how many distinct clusters nf-core/spatialvi already assigned, per sample, by reading the
`obs["clusters"]` column of the processed object 02.01 produced, through `spatial-cluster-count`
(decision 0028). This sub-stage submits the job and returns; it does not wait for completion. A
later invocation reads `STATUS` and collects results.

**The computation is not yours.** The wrapper's `check` validates, `prepare` generates
`scripts/count_clusters.py` and `submit.sh`, and `collect` runs the exit gate and writes
`OUTPUTS.tsv` and `STATUS`. Your job is the dialogue between those calls and the verbatim
reporting of what they return.

## Inputs
1. **The `h5ad` from 02.01** — resolved by artifact type by stage 02's router
   (`_system/resolve_artifact.py`) and passed as `--h5ad`. Never located by hand. 02.01
   registers its results **directory**; see Definitions for the file-or-directory rule.
2. **`_config/spatialvi.yaml`** — only its `compute.*` keys; this skill has no thresholds
3. **`01_samplesheets/spatialvi_samplesheet.csv`** — the independent source the exit gate checks
   the analysis's sample set against
4. **The wrapper** — `$GARS_WRAPPERS/spatial-cluster-count/spatial_cluster_count.py`
5. Reference (every run): `_references/artifact_types.md`, `_system/gars-env.sh`

## Scope Boundaries
This sub-stage performs the steps in Process and nothing else.

- Never edit `scripts/count_clusters.py`. `prepare` generates it, and a hand-edit makes the
  manifest a lie. If the analysis needs to change, that is a wrapper change to report.
- **Never re-cluster.** The count is of the assignment nf-core/spatialvi wrote. Do not run
  Leiden, Louvain, scanpy or any clustering yourself, in any venue, to "check" or "improve" the
  number. A different resolution is a re-run of 02.01, not something this sub-stage does.
- **Never name a cluster.** No cell type, no tissue region, no "probably tumour". Report the
  count and the per-cluster spot tallies only. Naming is stage 03's business, with a plan.
- **Never read a `var` (gene) name** from the object, and never report one. This skill reads
  one `obs` column and nothing else; the report you send contains no gene.
- **Never substitute another obs column.** If the analysis refuses because `obs` has no
  `clusters` column, that is the result: 02.01's object carries no clustering under the name the
  pipeline writes. Do not pick `leiden`, `louvain` or anything else from the columns it lists.
  Report and stop.
- **Never lower a threshold.** This skill has none; 02.01's QC thresholds decide which spots are
  real. A sample with no spots is a finding to report, not a parameter to tune.
- **Never pip- or conda-install a missing package.** If `check` reports the analysis
  environment is missing `anndata`, that is an environment rebuild from the lockfile, not
  something to fix in the moment. Report and stop.
- Never open the `.h5ad` yourself, and never run the analysis in the foreground to "just see"
  the number.
- Never run in the foreground, never poll in a loop, never resubmit a `SUBMITTED`/`RUNNING` job.
- Never delete or move a populated `run/` directory; `check` refuses it for a reason.
- Never modify the samplesheet, `00_data/`, `01_samplesheets/` or 02.01's directory.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Definitions

**Wrapper invocation.** From the workspace root, on stock python — the analysis's own
environment arrives via `$GARS_PY` inside `submit.sh`:

```bash
python3 _system/wrappers/spatial-cluster-count/spatial_cluster_count.py <subcommand> \
    --project projects/<title> --h5ad <resolved path>
```

Exit codes are the stage-helper standard: 0 ok, 1 failure (the JSON lists every failure),
2 refused (a gate), 3 usage. Branch on them; never re-interpret a failure as something to fix
silently.

**Failure vocabulary.** `preconditions` (`--h5ad` absent or not resolving to one processed
object per sample, the samplesheet or config absent, or the analysis environment lacks
`anndata`), `config` (a `compute.*` key is absent), `config_unfilled` (`<REQUIRED>` markers
remain), `samplesheet` (wrong header, or no samples), `output_dir` (a populated `run/` with no
completion marker). `collect` uses `summary` (the sample-set and count checks against
`summary.json`), `table` (the artifact type name, for `clusters.tsv`), `report`.

**The input is a file or a directory.** 02.01 registers its results **directory** as the
`h5ad` artifact — the set is the artifact — so that is what the router resolves and what
`--h5ad` normally receives; the per-sample object sits at `<dir>/<sample>/data/<sample>.h5ad`,
the same name 02.01's own gate checks, and `<sample>-raw.h5ad` beside it is never substituted.
With a directory, `check` resolves one file per samplesheet sample and refuses naming any that
is missing. `--h5ad` may instead name a single `.h5ad` **file**; then the samplesheet must list
exactly one sample, or `check` refuses rather than guess which sample the file is.

**The column read.** `obs["clusters"]`, the name nf-core/spatialvi writes
(`leiden_key_added = 'clusters'` in its workflow at the pin). There is no fallback list. The
count is `nunique()` over the values a spot actually carries, never a categorical's declared
categories; `n_obs` is the number of **spots** (rows of `obs`).

**`run/summary.json`.** `obs_column`, and `samples: {<sample>: {n_clusters, n_obs}}`. With
**one** sample it also carries top-level `n_clusters` and `n_obs`. With more than one sample
those top-level keys are **absent**, because cluster ids are per sample and not comparable
across samples — there is no honest total, and T6 reports per sample. The file never carries
`n_cells_in`, `n_cells_out` or `marker_rows`: `n_obs` is a spot count, and a cell-count label
on it would be wrong.

**Two kinds of gate, and which is which.** `collect` refuses without `run/.gars_run_complete`,
then makes two checks that must not be confused:

- **Independent:** the sample set in `summary.json` must equal the samplesheet's — every listed
  sample counted, nothing unlisted present. The samplesheet is a source the analysis did not
  write, so this is the check that means something.
- **Internal consistency:** `clusters.tsv` must agree with `summary.json` — rows per sample
  equal `n_clusters`, `n_spots` per sample sum to `n_obs`. Both files were written by the same
  script from the same values, so agreement proves the table is whole and unedited. It proves
  nothing about the pipeline's clustering and is **not** an independent check; never describe
  it as one.

**Execution venue.** Always `sbatch` (decisions 0005, 0027). Opening a processed spatial object
is not login-node work.

**Produced artifacts.** `table` (`run/clusters.tsv`: `sample, cluster, n_spots`, where
`cluster` is the pipeline's own id, never a name) and `report` (`run/report.md`) — see
`_references/artifact_types.md`. **Never an `h5ad` row**: this sub-stage produces no object, and
a row would shadow 02.01's for every later consumer, because the resolver takes the newest
`native` match.

## Process
1. Reply T1.
2. Read the STATUS file. If it is `SUBMITTED`, `RUNNING`, or `COMPLETE`, stop — stage 02's
   router already handles those states and should not have routed here.
3. Run the wrapper's `check` with the resolved `--h5ad`. Exit 1 → reply T5 with its `failures`
   verbatim and stop. Do not fix causes yourself: a missing package is an environment change,
   a missing per-sample object means 02.01 has not completed for that sample.
4. Run `prepare`. Exit 1 → reply T5 (same rule). Exit 0 → it wrote the script, `submit.sh` and
   the reproducibility bundle; report nothing yet.
5. Submit with `sbatch <sub-stage dir>/submit.sh`. Capture the job ID.
6. Write `STATUS` as `SUBMITTED <job_id> <iso8601>`. Reply T2 and stop. Do not wait or poll.
7. **On a later invocation** where STATUS is `SUBMITTED` or `RUNNING`: query `sacct`/`squeue`.
   If still active, update STATUS to `RUNNING <job_id> <iso8601>`, reply T3, stop.
8. If the job has finished, run `collect` with `--model "<the exact model id you are running
   as>"` and `--h5ad-from <the sub-stage that supplied the object>` (decision 0024). Exit 2 →
   the run did not complete: write `STATUS` as `FAILED <iso8601>`, reply T4, stop. If the
   analysis log says `obs has no 'clusters' column`, T4 carries that line verbatim and the
   columns it listed; choosing another column is not a retry. Exit 1 → the exit gate failed:
   write `FAILED`, reply T4 with its `failures` verbatim, stop.
9. Exit 0 → append its `history_entry` to the project's `HISTORY.md` **verbatim**, replacing
   `<ISO-8601 date>` with today's date, and reply T6.

## Response Format
Every message you send in this sub-stage is one of the templates below, with placeholders
filled. Add nothing else: no observations, no suggestions, no biological interpretation, no
cluster names, no gene names.

One standing exception, from `_references/contract_standard.md` ("the bounded voice"): if the
user asks a direct question, answer it from this workspace's own files — read-only, in a short
paragraph — then restate the pending wait point.

**T1 — Start**
```
Sub-stage 02.02: spatial cluster count.
Assay: spatialvi
Input: <h5ad path> (supplied by <sub-stage>; <n> sample(s))
Column read: obs["clusters"], as written by nf-core/spatialvi
This sub-stage counts the pipeline's clusters. It does not re-cluster, name or read genes.
```

**T2 — Submitted**
```
Checks passed. Submitted to Slurm as job <job_id>.

Output: 02_bioinformatics/spatialvi/02_spatial-cluster-count/run/
Status: 02_bioinformatics/spatialvi/02_spatial-cluster-count/STATUS

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

STATUS set to FAILED. Nothing was retried, nothing was deleted, no other column was read.
Log: 02_bioinformatics/spatialvi/02_spatial-cluster-count/logs/<log file>
```

**T5 — Preconditions not met**
```
Cannot start sub-stage 02.02.

<the wrapper's failures, verbatim, one line each: check + detail>

<what the user must do: complete 02.01 for the named sample(s) / rebuild the analysis
environment from the lockfile / fill the config>
```

**T6 — Complete**
```
Sub-stage 02.02 complete.

| Sample | Spots | Clusters |
|---|---|---|
| <sample> | <n_obs> | <n_clusters> |

Column read: obs["clusters"]. Cluster ids are the pipeline's own; none is named here.
<with more than one sample: "Cluster ids are per sample and not comparable, so no total is
reported.">

| Artifact | Path |
|---|---|
| Per-cluster spot counts | <table path> |
| Report | <report path> |

Read the report before anything consumes these counts — see Human check.
```

The `history_entry` returned by `collect` (step 9) has this shape; append it as returned:

```
## <ISO-8601 date> — 02_bioinformatics/spatialvi/02_spatial-cluster-count — cluster count complete

Template version: <version>
Model: <model id>
Method: count of distinct values in obs['clusters'] as written by nf-core/spatialvi, read with anndata via the gars spatial-cluster-count wrapper; nothing re-clustered, nothing named, no gene read
Obs column: clusters
Matrix supplied by: <--h5ad-from>
Samples: <n> (<sample>: <n_clusters> clusters / <n_obs> spots, ...)
Outputs: `table`, `report`
```

## OUTPUT
Written to `projects/<project_title>/02_bioinformatics/spatialvi/02_spatial-cluster-count/`:

| Artifact | Contents |
|---|---|
| `STATUS` | Sub-stage state. The authority on completion. |
| `scripts/count_clusters.py` | The generated analysis. Re-runnable alone; never hand-edited. |
| `submit.sh` | The generated Slurm script. |
| `preflight/check_result.json` | Preflight verdict. Diagnostic only. |
| `reproducibility/` | `manifest.json` (input checksums, the column read), `commands.sh`. |
| `logs/` | Slurm stdout/stderr. |
| `run/summary.json` | `obs_column`, per-sample `n_clusters` and `n_obs`; top-level `n_clusters`/`n_obs` only with one sample. |
| `run/clusters.tsv` | `sample, cluster, n_spots` — the pipeline's own cluster ids. |
| `run/report.md` | The counts, the column and file(s) read, what this skill deliberately does not do. |
| `OUTPUTS.tsv` | `table` and `report`, written by `collect`. Never an `h5ad` row. |

`00_data/`, `01_samplesheets/` and 02.01's directory are never modified.

## Human check
Open `run/report.md` and compare each sample's **spot count** against the spots retained in
02.01's per-sample report (`run/results/<sample>/reports/report-<sample>.html`). They must be
the same number: a mismatch means this count was taken from a different object than the one
02.01 gated, and every downstream use of the cluster count would describe the wrong file.
