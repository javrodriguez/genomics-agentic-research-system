---
date: 2026-08-13
status: standing
touches:
  - gars/_references/artifact_types.md
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
---
# Skill chaining is not guaranteed to work: the adaptation layer

`nfcore-rnaseq-wrapper` and `rnaseq-de` declare each other as chaining partners in the ClawBio
catalogue. Their formats do not meet. Three separate defects surfaced running the handoff:

1. **Non-numeric column.** nf-core emits `gene_id`, `gene_name`, then samples. `rnaseq-de`
   documents "first column is gene identifier" and coerces every later column to numeric, so
   `gene_name` raises `Count matrix contains non-numeric entries`.
2. **Silent loss of gene identifiers.** `rnaseq_de.py:288` does
   `results_df.reset_index().rename(columns={"index": "gene"})`, assuming an *unnamed* index.
   With a named index the rename is a no-op and the identifier column is dropped from the output
   selection — **no error, no warning**. The first DE run produced a complete, plausible
   `de_results.csv` in which every gene was anonymous. It only surfaced because a later line
   crashed on `row.gene`. Naming the column `gene`, as the skill's own demo data does, fixes it.
3. **`FileExistsError` on rerun.** The skill refuses a populated `--output`, so a rerun must move
   the previous directory aside.

**Consequences for the architecture:**

- A sub-stage may need an **adaptation layer** between an upstream artifact and its skill. That
  adaptation belongs in the consuming sub-stage's own directory, never as a modification of the
  producer's output. 02.02 writes `adapted/counts_gene.tsv` and keeps
  `adapted/gene_id_to_name.tsv` so results can be annotated later.
- **Analysis sub-stages need scheduled allocations too.** Running 02.02 in the foreground got it
  SIGKILLed (exit 137) on a login node. The contract now requires `sbatch`, as 02.01 does.
- Defect 2 is the strongest argument yet for exit gates that check *content*, not just existence.
  A file-exists check passes happily on a DE table with no gene column.
