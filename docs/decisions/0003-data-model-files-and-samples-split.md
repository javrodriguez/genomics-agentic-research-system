---
date: 2026-08-10
status: standing
touches:
  - gars/00_initialize_project/CONTEXT.md
  - gars/01_prepare_samplesheets/CONTEXT.md
---
# Data model: files.csv and samples.csv, and subsetting by deletion

**`metadata.csv` split into `files.csv` + `samples.csv`.** One file was carrying two grains.
Now: `files.csv` is machine-owned, one row per sample-lane; `samples.csv` is user-owned, one row
per sample. The user enters each experimental value once instead of once per file, and
"same sample, conflicting condition" becomes structurally impossible rather than a validation
rule. Rejected the alternative of a list-of-paths column — multi-value CSV cells cannot be
validated per-cell and nf-core cannot consume them.

**Subsetting by deletion, never by destruction.** Referential integrity is asymmetric: a sample
in `samples.csv` but not `files.csv` is an error; a sample in `files.csv` but not `samples.csv`
is a deliberate **exclusion**, confirmed via template T7. Raw symlinks and `files.csv` are left
untouched, so the choice is reversible. The earlier symmetric rule left the agent no legal way
to honour "analyse only these ten," so it deleted 112 symlinks and corrupted a machine-owned
file to satisfy the rule.

**Stage boundaries fall on human gates.** Stage 00 registers data; the user then fills in the
design; stage 01 validates it. Modelling that pause as a stage boundary rather than a wait
inside one stage makes resumability legible from the directory tree. Validation splits on the
same line: file-level checks in 00 (where files are touched), design-level checks in 01 (the
design does not exist until the user writes it).

**`01_ingest_data` renamed `01_prepare_samplesheets`** with its own output directory
`01_samplesheets/`. Stage 00 does the ingestion when it symlinks, so the old name described the
wrong stage.

**Scientific parameters are never defaulted.** No stage substitutes a value for `reference`,
`de.formula`, or `de.contrast`. A wrong contrast yields a confident wrong answer rather than an
error, so a missing key stops the stage and asks.
