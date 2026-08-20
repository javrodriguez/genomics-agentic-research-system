# History: demo-project

Append-only. One dated entry per stage action, newest last. Every stage appends here; no stage
rewrites or removes an earlier entry.

Entry format:

```
## <ISO-8601 date> — <stage or sub-stage> — <outcome>
<what was done, what was written, and where any input came from>
```

---

## 2026-08-18 — 00_initialize_project — project created

Template version: v0.3.0

| Assay ID | Source path | Files linked |
|---|---|---|
| rnaseq_bulk | `/path/to/sequencing/run_2026_03/` (synthetic) | 24 |

Wrote `00_data/rnaseq_bulk/files.csv` (12 sample-lane rows) and `samples.csv` (6 sample rows,
experimental columns blank).

## 2026-08-18 — 01_prepare_samplesheets — samplesheets emitted

Design validated: 6 samples, 2 conditions, 3 replicates each, no exclusions. Wrote
`01_samplesheets/rnaseq_bulk_samplesheet.csv` (12 rows) and `rnaseq_bulk_design.csv` (6 rows).

## 2026-08-18 — 02.01 nfcore-rnaseq-wrapper — complete

Artifacts declared in `02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/OUTPUTS.tsv`.

## 2026-08-18 — 02.02 rnaseq-de — complete

Counts resolved by type `counts_gene` from sub-stage `01_nfcore-rnaseq-wrapper`, reshaped into
`adapted/counts_gene.tsv`. Artifacts declared in `OUTPUTS.tsv`.

*(This is a synthetic example. No pipeline was run and no real data exists here.)*
