---
name: scrna-qc-cluster
description: >
  GARS-authored single-cell QC and clustering for sub-stage 02.02: filters cells and genes,
  normalises, selects highly variable genes, PCA, neighbours, Leiden clusters and Wilcoxon
  markers. The sibling of rnaseq-de, and the place cell-level content checks can honestly live.
metadata:
  openclaw:
    source: gars                    # versioned in this repo (decision 0012)
    # The analysis engine, named the way rnaseq-de names pydeseq2: this wrapper drives a
    # library under $GARS_PY, not an nf-core workflow. The version is the one the analysis was
    # validated against and the one gars-bio must be pinned to when scanpy is added to it.
    pipeline: scanpy (gars-bio)
    pipeline_version: "1.11.5"
    consumes: h5ad
    requires:
      bins: [python3]
      python: ">=3.6 (stdlib only) for the wrapper; $GARS_PY for the analysis"
      analysis_packages: [scanpy, anndata, leidenalg, python-igraph, scikit-learn,
                          matplotlib, pandas, numpy]
    install: >
      Nothing to install for the wrapper itself. The ANALYSIS needs scanpy and leidenalg in
      the gars-bio environment; as shipped that environment carries anndata but neither of
      them. They are a pinned environment addition (_references/environment.md) -- never a
      run-time pip install. `check` refuses by name when they are absent.
---

# scrna-qc-cluster

One stdlib Python file, JSON on stdout, exit codes `0 ok / 1 failure / 2 refused / 3 usage`.
The sub-stage contract at `02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md`
orchestrates it; nothing here is invoked directly by a user.

```
python3 scrna_qc_cluster.py check   --project projects/<title> --h5ad <path>
python3 scrna_qc_cluster.py prepare --project projects/<title> --h5ad <path>
sbatch <substage>/submit.sh                       # written by prepare
python3 scrna_qc_cluster.py collect --project projects/<title> --model "<model id>" \
    --h5ad-from 01_nfcore-scrnaseq-wrapper
```

`--h5ad` is the path stage 02's router resolved **by artifact type** from 02.01's
`OUTPUTS.tsv` (`_system/resolve_artifact.py`). This wrapper never searches for its input.

## Why this sub-stage exists

02.01 is stdlib-only, so its exit gate cannot open an HDF5 file: it can prove every sample
produced a matrix, and no more. **Cell counts are only checkable here**, where the analysis runs
under `$GARS_PY`.

The mechanism matters. The generated script writes `run/summary.json` — cells in, cells after
QC per sample, cluster count, and the thresholds that produced them — and this stdlib wrapper
then checks those numbers **against the samplesheet**, an independent source. A summary that is
merely self-reported and trusted would gate nothing.

## The analysis

Generated verbatim into `scripts/run_scrna.py` at `prepare` time, from a template in the
wrapper, so the script version is pinned by the template version in the manifest. It takes no
arguments and embeds its exact inputs — reproducible by `python run_scrna.py` alone.

QC (`min_genes`, `min_cells`, `max_mito_pct`) → normalise to 1e4 → log1p → highly variable
genes → scale → PCA → neighbours → UMAP → **Leiden** → Wilcoxon rank-sum markers per cluster.

Every threshold comes from `_config/scrnaseq.yaml` and is **recorded in `summary.json` and the
report beside the numbers it produced**, so a reader can see what was removed and why.

## Produced artifacts

| Type | Path |
|---|---|
| `h5ad` | `run/data/processed.h5ad` |
| `table` | `run/tables/cluster_markers.csv` |
| `figure` | `run/figures/umap_clusters.png` |
| `report` | `run/report.md` |

Both this sub-stage and 02.01 produce `h5ad`. That is correct and unambiguous: the resolver
takes the first `native` match in **reverse sub-stage order**, so a later consumer gets the
*processed* object, which is what it means.

## What this refuses, and why

**A missing analysis package, by name.** `gars-bio` as shipped has `anndata` but not `scanpy`
or `leidenalg`. `check` probes `$GARS_PY` and reports exactly which are absent, because the
alternative is a raw `ImportError` an hour into a Slurm job — the rule stated in
`assay_stage_skill_map.md`.

**An anonymous marker table.** The identifier column is written first and named `gene`, and the
gate rejects any empty identifier. The bulk sibling once published a complete, plausible DE
table in which every gene was anonymous (decision 0010).

**A sample with no cells left.** Checked against the samplesheet, not against itself. A sample
that filters to nothing disappears from every downstream result and nothing else would flag it.

**Every cell filtered out.** The analysis exits with the message *"This is a result to report,
not a threshold to lower."* Loosening a QC threshold until a poor sample survives is
manufacturing a result, and the contract forbids it in those words.

## One matching rule worth knowing

nf-core/scrnaseq labels cells in the combined matrix with the sample id **plus its input
type** — `Sample_X_filtered`, not `Sample_X`. Verified on a real run. The gate therefore counts
a label for a sample when it is the id or the id followed by an underscore-qualifier; an exact
match would have declared every sample lost on a perfectly good result.

## Validation status

Validated end to end against the matrix nf-core/scrnaseq actually produced (8,672 cells ×
1,100 genes, mouse chr19 test subset): `check` refuses by name without the packages and passes
with them, `prepare` is byte-identical across runs, the generated analysis completes, and the
gate catches an anonymous gene, a zero-cell sample and a missing processed object — then passes
again when restored.

Two things that validation does **not** show, said plainly:

- The clustering was run with thresholds suited to a miniature test matrix (`min_genes: 1`),
  because the shipped production defaults correctly filter that dataset to nothing. The
  numbers are recorded in `summary.json` either way. The 198 clusters it produced are an
  artefact of test data averaging one gene per cell, not a result.
- The analysis has **not** been run under `gars-bio` itself, because that environment does not
  yet carry scanpy. It was run under an equivalent pinned environment. Adding the packages to
  `gars-bio` is an outstanding, named prerequisite.
