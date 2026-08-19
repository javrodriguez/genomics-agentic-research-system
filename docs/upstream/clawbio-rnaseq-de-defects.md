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

`rnaseq-de`: three defects in the declared `nfcore-rnaseq-wrapper` → `rnaseq-de` handoff, one silent

## Body

The catalogue declares `nfcore-rnaseq-wrapper` and `rnaseq-de` as chaining partners, but their
formats do not meet. Running the handoff on real data surfaced three separate breaks. The second
is the serious one: it produces a complete, plausible, **wrong** result with no error and no
warning.

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

### Suggested acceptance test

An end-to-end test that feeds `nfcore-rnaseq-wrapper`'s **native** `salmon.merged.gene_*.tsv`
straight into `rnaseq-de` and asserts the output's first column is populated would catch all three.
The declared chaining relationship is currently unverified in CI.
