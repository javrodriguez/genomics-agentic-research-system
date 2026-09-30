# History: rna-test

Append-only. One dated entry per stage action, newest last. Every stage appends here; no stage
rewrites or removes an earlier entry.

Entry format:

```
## <ISO-8601 date> — <stage or sub-stage> — <outcome>
<what was done, what was written, and where any input came from>
```

---

## 2026-09-29 — 00_initialize_project — project created

Template version: v0.10.0
Model: claude-opus-5-5
File integrity check: `quick`

| Assay ID | Source path | Files linked |
|---|---|---|
| rnaseq_bulk | `/fixture-workspace` | 8 |

## 2026-09-29 — 02.01 nfcore-rnaseq-wrapper — complete

Artifacts declared in `02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/OUTPUTS.tsv`.

## 2026-09-29 — 02.02 rnaseq-de — complete

Artifacts declared in `02_bioinformatics/rnaseq_bulk/02_rnaseq-de/OUTPUTS.tsv`.

## 2026-09-29 — 03_custom_analysis/01_fixture-followup — analysis complete

Template version: v0.10.0
Model: claude-opus-5-5
Plan: 03_custom_analysis/01_fixture-followup/PLAN.md (approved 2026-09-29)
Goal: Synthetic fixture: tabulate the fixture differential expression table by adjusted p-value.
Outputs: `results/table.tsv` (table)
