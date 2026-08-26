# Draft: upstream defect report for `rnaseq-de`

**Status: drafted, not filed.** Filing this creates a public issue on a third-party project under
the maintainer's name. That is a decision for a person, not an agent — so it is written out here,
ready to paste, and left unsent. Target: <https://github.com/ClawBio/ClawBio/issues>, the same
tracker as ClawBio#333.

Found while running `nfcore-rnaseq-wrapper` → `rnaseq-de`, the pair the catalogue declares as
chaining partners. Detail and the architectural consequences are in
[decision 0010](../decisions/0010-skill-chaining-defects-and-adaptation.md).

---

## Title

`rnaseq-de`: four defects in the declared `nfcore-rnaseq-wrapper` → `rnaseq-de` handoff, two silent

## Body

The catalogue declares `nfcore-rnaseq-wrapper` and `rnaseq-de` as chaining partners, but their
formats do not meet. Running the handoff on real data surfaced four separate breaks. The second
and fourth are the serious ones: each produces a complete, plausible, **wrong** result with no
error and no warning.

**Environment:** `clawbio==0.6.1`, Python 3.12, Linux (Slurm HPC), nf-core/rnaseq 3.26.0,
`--backend pydeseq2`.

### 1. Non-numeric column rejected

nf-core/rnaseq emits `gene_id`, `gene_name`, then one column per sample. `rnaseq-de` documents
"first column is gene identifier" and coerces every later column to numeric, so `gene_name`
raises:

```
Count matrix contains non-numeric entries
```

A consumer of the declared partner's native output cannot use it unmodified.

### 2. Silent loss of gene identifiers — **the important one**

`rnaseq_de.py:288`:

```python
results_df.reset_index().rename(columns={"index": "gene"})
```

This assumes the index is *unnamed*. When the count matrix was read with a **named** index, the
rename is a no-op, the `gene` column never appears, and the identifier is dropped from the output
column selection.

**There is no error and no warning.** The first run produced a complete, well-formed
`de_results.csv` — correct row count, correct statistics — in which every gene was anonymous. It
surfaced only because a later line happened to crash on `row.gene`. Had that line not existed, the
result would have looked publishable.

Naming the identifier column `gene`, as the skill's own demo data does, avoids it. Suggested fix:
select the identifier column explicitly rather than relying on the index being unnamed, and fail
loudly if it is absent after the rename.

### 3. `FileExistsError` on rerun

The skill refuses a populated `--output` directory, so a rerun requires moving the previous
directory aside. That is defensible as a guard, but combined with (2) it means the natural
recovery loop — fix input, rerun — needs manual filesystem work.

### 4. Published `log2FoldChange` does not reflect the data — **also silent**

Found while validating an independent PyDESeq2 reimplementation against `rnaseq-de`'s output on
a real 10-sample dataset (78,941-gene nf-core count matrix, two-level contrast). The skill's
p-values are correct — an independent run reproduces them to `padj` r = 0.99998 with an
identical significant set (265/265 at padj < 0.05). Its `log2FoldChange` column is not:

- Correlation of `rnaseq-de`'s LFC with log2 ratios computed directly from the DESeq2
  normalized counts: **0.33**. (The reimplementation's Wald-MLE LFC: **0.99**.)
- Concrete case: a gene at `padj` ≈ 1e-12 is published with `log2FoldChange` = −0.051 (a 1.04×
  change) while its actual normalized group means differ ~70×. Several of the top-ten genes by
  `padj` carry |LFC| < 0.05.

Mechanism, from reading the source: `run_deseq2()` attempts `stats.lfc_shrink(coeff=...)` via
`_resolve_shrinkage_coeff()`, which searches the fitted LFC columns for the contrast
**numerator**. With pydeseq2 ≥ 0.5's formulaic design (`condition[T.<level>]` columns, reference
= first level alphabetically), a contrast whose numerator IS the reference level resolves no
coefficient — and when it does resolve one, the shrunk column belongs to the fitted coefficient,
which for the opposite orientation is **sign-flipped** relative to the requested contrast. The
published values on this dataset match neither the MLE, apeglm shrinkage of either coefficient
sign, nor naive ratios; whatever estimator produced them, the reported effect sizes are not the
requested contrast's. A reader who filters by fold change — the most common downstream move —
silently loses true positives.

Suggested fix: publish the unshrunk Wald MLE for the requested contrast, or re-level the design
so the shrinkage coefficient is exactly the contrast, and fail loudly when the coefficient
cannot be resolved instead of proceeding.

### Suggested acceptance test

An end-to-end test that feeds `nfcore-rnaseq-wrapper`'s **native** `salmon.merged.gene_*.tsv`
straight into `rnaseq-de`, asserts the output's first column is populated, and checks the
published `log2FoldChange` against ratios of the normalized group means (they should correlate
near 1, not 0.33) would catch all four. The declared chaining relationship is currently
unverified in CI.
