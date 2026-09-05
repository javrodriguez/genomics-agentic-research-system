---
name: spatial-cluster-count
description: >
  GARS-authored cluster COUNT for sub-stage 02.02 of spatialvi: reads the `clusters` obs
  column nf-core/spatialvi already wrote and reports how many distinct clusters there are, per
  sample. It never clusters, never names a cell type, never reads a gene, and has no fallback
  column. The promotion of a bare demo script into a registered, linted, gated skill.
metadata:
  openclaw:
    source: gars                    # versioned in this repo (decision 0012)
    # The analysis engine, named the way scrna-qc-cluster names scanpy: this wrapper drives a
    # library under $GARS_PY, not an nf-core workflow. The version is the gars-bio pin.
    pipeline: anndata (gars-bio)
    pipeline_version: "0.13.2"
    consumes: h5ad
    requires:
      bins: [python3]
      python: ">=3.6 (stdlib only) for the wrapper; $GARS_PY for the analysis"
      analysis_packages: [anndata]
    install: >
      Nothing to install for the wrapper itself. The ANALYSIS needs anndata under $GARS_PY,
      and anndata is already PINNED in _references/gars-bio.lock.txt (0.13.2) -- the
      environment that carries gars-bio already has it. It is never installed at run time;
      `check` refuses by name if the interpreter it probes cannot import it.
---

# spatial-cluster-count

One stdlib Python file, JSON on stdout, exit codes `0 ok / 1 failure / 2 refused / 3 usage`.
The sub-stage contract at `02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md`
orchestrates it; nothing here is invoked directly by a user.

```
python3 spatial_cluster_count.py check   --project projects/<title> --h5ad <path>
python3 spatial_cluster_count.py prepare --project projects/<title> --h5ad <path>
sbatch <substage>/submit.sh                       # written by prepare
python3 spatial_cluster_count.py collect --project projects/<title> --model "<model id>" \
    --h5ad-from 01_nfcore-spatialvi-wrapper
```

`--h5ad` is the path stage 02's router resolved **by artifact type** from 02.01's
`OUTPUTS.tsv` (`_system/resolve_artifact.py`). This wrapper never searches for its input.

## What it does, and only this

nf-core/spatialvi clusters every spot and writes the assignment to `obs["clusters"]`
(`leiden_key_added = 'clusters'` in the pipeline's workflow at the pin). This skill opens the
processed object, counts the distinct values in that one column, and reports the number per
sample, with a per-cluster spot tally.

It **never** re-clusters, never reads a `var` (gene) name, never names a cluster a cell type or
a region, and never lowers a threshold (it has none). It has **no fallback column list**: if
`obs` carries no `clusters` column the analysis refuses with exit 2 and lists the columns that
do exist. A fallback that silently picked another column would report a count from a
clustering nobody asked for.

## The input: a file or a directory

02.01 registers its results **directory** as the `h5ad` artifact (the set is the artifact), so
that is what the router hands over; the per-sample object sits at
`<dir>/<sample>/data/<sample>.h5ad`, the same name 02.01's own gate checks, and
`<sample>-raw.h5ad` beside it is never substituted. With a directory, `check` resolves one file
per samplesheet sample and refuses naming any that is missing. A single-sample driver may hand
over one `.h5ad` file instead; then the samplesheet must list exactly one sample, or `check`
refuses rather than guess which sample the file is.

## The analysis

Generated verbatim into `scripts/count_clusters.py` at `prepare` time, from a `%`-formatted
template in the wrapper, so the script version is pinned by the template version in the
manifest. It takes no arguments and embeds its exact inputs — reproducible by
`python count_clusters.py` alone. It writes:

- `run/summary.json` — `obs_column`, and `samples: {<sample>: {n_clusters, n_obs}}`. With
  **one** sample it also carries top-level `n_clusters` and `n_obs`; with more than one it does
  not, because cluster ids are per sample and not comparable, so there is no honest total.
  `n_obs` counts **spots**. The file never carries a key named `n_cells_in`, `n_cells_out` or
  `marker_rows` — a reader that assumed the scrnaseq sibling's shape would print cell-count
  labels for a spot count.
- `run/clusters.tsv` — `sample, cluster, n_spots`; `cluster` is the pipeline's own id, never a
  name.
- `run/report.md` — the counts, the column read, the file(s) read, and what this skill
  deliberately does not do.
- `run/.gars_run_complete`, last.

## Produced artifacts

| Type | Path |
|---|---|
| `table` | `run/clusters.tsv` |
| `report` | `run/report.md` |

**Never an `h5ad` row.** This sub-stage produces no object, and a row here would shadow 02.01's
for every later consumer, because the resolver takes the newest `native` match.

## The exit gate, in two kinds

`collect` refuses without `run/.gars_run_complete`, then:

- **Independent:** the sample set in `summary.json` must equal the samplesheet's — every
  listed sample counted, nothing unlisted present. The samplesheet is a source the analysis
  did not write.
- **Internal consistency:** `clusters.tsv` must agree with `summary.json` — rows per sample
  equal `n_clusters`, `n_spots` per sample sum to `n_obs`. Both files came from the same
  script, so this proves the table is whole and unedited; it proves nothing about the
  pipeline's clustering and is not an independent check.

Then `OUTPUTS.tsv` (the two rows above), `STATUS COMPLETE`, and a history entry naming the
template version, `--model`, the method, the obs column, and `Matrix supplied by:
<--h5ad-from>`.

## Validation status

The bare script this promotes (`h5ad_clusters.py` in the demo) read `obs["clusters"]` on the
object the cluster's own 02.01 produced and reported 23 clusters over 834 spots; the same
formulas (`nunique()` over the values, `obs.shape[0]`) are kept here so that number is
unchanged. The wrapper's `check`/`prepare`/`collect` path is exercised offline in
`tests/run_tests.py` against faked run outputs shaped like the real ones; the generated script
is run there against a tiny synthetic object only when anndata is importable in the test
interpreter, and the test says so when it is not.
