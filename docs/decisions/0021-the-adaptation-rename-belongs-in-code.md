---
date: 2026-08-24
status: standing
touches:
  - gars/_system/adapt_counts.py
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
---
# The adaptation's rename belongs in code, not in a contract's prose

## What happened

A real 10-sample run reached 02.02, analysed 22,783 genes through PyDESeq2, and crashed writing
its report:

```
AttributeError: 'Pandas' object has no attribute 'gene'
```

The agent concluded this was a defect inside the installed `rnaseq-de` skill, which it does not
patch, and recorded `FAILED` with the resolution being to fix or upgrade `clawbio`.

**That was wrong.** `de_results.csv` had been written with columns
`baseMean,log2FoldChange,pvalue,padj` — 22,783 rows and **no gene identifier at all**. The crash
was not the failure; it was the only thing that revealed it.

## This was already known

[0010](0010-skill-chaining-defects-and-adaptation.md), written eight decisions earlier, describes
this exact defect and states the fix in one sentence: *"Naming the column `gene`, as the skill's
own demo data does, fixes it."*

The contract's **Adapted count matrix** definition described dropping `gene_name` and rounding
counts. It never mentioned the rename. The adaptation itself lived as a heredoc inside a
generated `submit.sh`, so the agent wrote what the Definition described, kept `gene_id`, and
reproduced the bug faithfully.

**A decision recorded a fix that the contract never encoded, and a heredoc is where that gap
became a wrong result.**

## The mechanism, verified

`rnaseq_de.py` does `results_df.reset_index().rename(columns={"index": "gene"})`, which assumes an
*unnamed* index. Confirmed directly against both matrix shapes:

| Index name | `"gene" in res.columns` after the rename | Surviving identifier column |
|---|---|---|
| `gene_id` | `False` | none |
| `gene` | `True` | `gene` |

And end to end, running the real skill on 400 real genes via Slurm:

| Adapted matrix | Exit | `de_results.csv` columns |
|---|---|---|
| `gene_id` | 1, `AttributeError … 'gene'` | `baseMean,log2FoldChange,pvalue,padj` |
| `gene` | 0 | `gene,baseMean,log2FoldChange,pvalue,padj` |

## Decision

The reshape moves into `_system/adapt_counts.py`. It drops `gene_name`, rounds counts, **renames
the identifier to `gene`**, and re-reads its own output to confirm the header before returning.
The contract calls it; writing the reshape inline is forbidden.

This is [0011](0011-deterministic-artifacts-in-stages-00-01.md) applied to the one deterministic
step that had been left in prose. The reshape has a single correct answer, so it is code; the
Definition keeps the vocabulary needed to explain a refusal.

Scope Boundaries also now name the symptom directly: `AttributeError: 'Pandas' object has no
attribute 'gene'` is **not** an upstream defect to escalate, it is an adapted matrix whose first
column is not `gene`. Check that column before concluding anything about the skill.

## The lesson

**A decision is not an implementation.** 0010 diagnosed this correctly, prescribed the fix
correctly, and the fix never reached the file that generates the artifact. The `touches:`
frontmatter exists to make a decision findable from the paths it constrains — 0010 named
`02_rnaseq-de/CONTEXT.md`, and the contract still shipped without the rename.

When a decision prescribes a change to behaviour, the change belongs in the same commit, in code
where the behaviour lives. Prose recording what should happen is not a mechanism that makes it
happen.
