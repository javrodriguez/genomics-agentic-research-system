# Stage 01: Prepare Samplesheets

## Purpose
Validate the experimental design the user completed in each assay's `samples.csv`, join it to
that assay's `files.csv`, and emit a workflow-ready samplesheet and design table per assay.
This stage writes no data and modifies no input; it is the gate between raw data registration
(stage 00) and processing (stage 02).

## Inputs
1. **Project title**
2. **A completed `00_data/<Assay ID>/samples.csv` per assay** — `condition`, `group`, and
   `replicate` filled in by the user, one row per sample
3. **`00_data/<Assay ID>/files.csv` per assay** — written by stage 00, read-only here

## Scope Boundaries
This stage performs the steps in Process and nothing else.

- Filesystem reads are limited to: this workspace's own files, and inside the named project
  its `CONTEXT.md`, `HISTORY.md`, `_config/`, and `00_data/`. Do not read or search elsewhere.
- **Never modify `samples.csv` or `files.csv`.** `samples.csv` is the user's file; `files.csv`
  is stage 00's. Report every problem found and stop; never silently correct, reformat, or
  fill a value in either.
- Never infer a missing experimental value. A blank `condition`, `group`, or `replicate` is a
  validation failure, not something to guess from sample names.
- Never create, re-link, move, or delete anything under `00_data/`. Stage 00 owns it.
- Never run a bioinformatics workflow, aligner, or QC tool, and never read FASTQ contents.
  That is stage 02's work.
- Do not report incidental observations about the user's filesystem or prior analyses.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Definitions

**Complete design row.** A `samples.csv` row where `sample_id`, `condition`, `group`, and
`replicate` are all non-empty.

**Resolvable file row.** A `files.csv` row whose `fastq_1` and, if present, `fastq_2` paths
exist relative to the project directory and resolve to a readable file. `fastq_2` may be empty
only when the assay's data is single-end.

**Referential integrity.** The two directions mean different things and are handled differently:

| Direction | Meaning | Handling |
|---|---|---|
| `sample_id` in `samples.csv` but not `files.csv` | The user invented a row, or mistyped an ID | **Failure.** Report and stop. |
| `sample_id` in `files.csv` but not `samples.csv` | The user deliberately dropped the sample from the analysis | **Exclusion.** Legal, but never silent — see below. |

**Exclusion.** Removing a sample's row from `samples.csv` is how the user narrows a project to a
subset. It is the only supported way to do so. The excluded sample keeps its raw symlinks and
its `files.csv` rows — nothing on disk is deleted, so the choice stays reversible and
`files.csv` remains a faithful record of what was ingested. Excluded samples are omitted from
the samplesheet and the design table, and must be confirmed by the user before anything is
written.

**Valid design.** All of:
- every `group` contains at least 2 distinct `sample_id` values — a group of one cannot be
  tested for differential expression;
- within a given `group` and `condition`, no `replicate` value repeats for distinct samples;
- no `sample_id` appears more than once in `samples.csv`;
- no `(sample_id, lane)` pair appears more than once in `files.csv`.

**Samplesheet.** `01_samplesheets/<Assay ID>_samplesheet.csv`, nf-core compatible, header
`sample,fastq_1,fastq_2,strandedness`. Built by joining `files.csv` to `samples.csv` on
`sample_id`: one row per `files.csv` row, `sample` = `sample_id`, paths absolute.
`strandedness` is read from `_config/<Assay ID>.yaml` if that file defines it, and is
otherwise `auto`. Multiple rows sharing a `sample` value are merged by nf-core as technical
replicates, which is the intended handling of multi-lane samples.

**Design table.** `01_samplesheets/<Assay ID>_design.csv`, header
`sample_id,condition,group,replicate`. One row per distinct `sample_id`. Consumed by the
differential-expression sub-stage of 02_bioinformatics.

## Process
1. This process is activated when the user asks to prepare samplesheets or to proceed past
   stage 00. Reply with T1.
2. Resolve the project directory from the title. If it does not exist, reply with T6 and stop.
3. Enumerate the assay directories under `00_data/`. If there are none, or a directory is
   missing either `files.csv` or `samples.csv`, reply with T6 and stop.
4. For each assay, read `samples.csv` and check every row is a **complete design row**. Collect
   the row numbers and column names of all blanks.
5. For each assay, read `files.csv` and check every row is a **resolvable file row**. Collect
   the row numbers and paths of anything missing or broken.
6. For each assay, check **referential integrity**. A `sample_id` in `samples.csv` with no rows
   in `files.csv` is a failure. A `sample_id` in `files.csv` with no row in `samples.csv` is an
   **exclusion** — collect it, do not treat it as a failure.
7. For each assay, check the design is a **valid design**, considering only included samples.
   Collect each rule violated, with the groups or samples responsible.
8. If any check in steps 4-7 failed for any assay, reply with T3 listing every failure found
   across all assays, and stop. Write nothing. Do not partially proceed with the assays that
   passed.
9. If any sample is excluded, reply with T7 listing every excluded sample and wait for explicit
   confirmation. Never proceed on a silent exclusion, and never infer that a missing row was an
   oversight — ask.
10. If `01_samplesheets/` already contains files for an assay about to be written, reply with T5
    and wait for confirmation before overwriting.
11. Reply with T2, then create `01_samplesheets/` and write the **samplesheet** and **design
    table** for each assay, containing included samples only.
12. Append a dated entry to the project's `HISTORY.md` recording the assays processed, the row
    and sample counts written, the files created, and every excluded `sample_id`.
13. Run the exit gate: every expected samplesheet and design table exists and is non-empty; the
    samplesheet row count equals the `files.csv` row count **for included samples only**; the
    design table row count equals the `samples.csv` row count. If any check fails, report
    exactly which one and stop; do not claim completion.
14. Reply with T4.

## Response Format
Every message you send in this stage is one of the templates below, with placeholders filled.
Add nothing else: no observations, no suggestions, no offers, no commentary about the data or
about anything encountered on the filesystem.

**T1 — Start**
```
Starting stage 01: Prepare Samplesheets.
Project: <title>
Validating the completed samples.csv for each assay before writing any samplesheet.
```

**T2 — Validation passed**
```
| Assay | Rows | Samples | Groups | Layout |
|---|---|---|---|---|
| <Assay ID> | <n> | <n> | <n> | paired-end / single-end |

All checks passed. Writing samplesheets.
```

**T3 — Validation failed**
```
Validation failed. Nothing was written; no input file was modified.

| Assay | Check | Detail |
|---|---|---|
| <Assay ID> | Incomplete design / Unresolvable paths / Referential integrity / Invalid design | <rows, columns, samples, or groups responsible> |

Correct 00_data/<Assay ID>/samples.csv and run stage 01 again.
```

**T4 — Stage complete**
```
Stage 01 complete. Samplesheets written to projects/<title>/01_samplesheets/.

| Assay | Samplesheet rows | Design rows | Files |
|---|---|---|---|
| <Assay ID> | <n> | <n> | <Assay ID>_samplesheet.csv, <Assay ID>_design.csv |

Next: run 02_bioinformatics for <Assay ID>.
```

**T5 — Existing samplesheets**
```
01_samplesheets/ already contains files for <Assay ID>:
<file list>

Confirm to overwrite, or reply `cancel` to stop.
```

**T6 — Preconditions not met**
```
Cannot start stage 01.

| Requirement | Status |
|---|---|
| projects/<title>/ exists | Yes / No |
| 00_data/<Assay ID>/files.csv exists | Yes / No |
| 00_data/<Assay ID>/samples.csv exists | Yes / No |

Run 00_initialize_project first.
```

**T7 — Samples excluded, awaiting confirmation**
```
<n> sample(s) have raw data but no row in samples.csv, and will be excluded from the analysis:

| sample_id | Files in files.csv |
|---|---|
| <sample_id> | <n> |

Proceeding with <n> of <n> samples. Raw data and files.csv are left untouched, so this is
reversible: add the rows back to samples.csv and run stage 01 again.

Confirm to proceed with the reduced set, or reply `cancel`.
```

# OUTPUT
Written to `projects/<project_title>/01_samplesheets/`:

| Artifact | Contents |
|---|---|
| `<Assay ID>_samplesheet.csv` | nf-core compatible: `sample,fastq_1,fastq_2,strandedness`. One row per sample-lane, absolute paths. Consumed by 02_bioinformatics. |
| `<Assay ID>_design.csv` | `sample_id,condition,group,replicate`. One row per sample. Consumed by the differential-expression sub-stage of 02_bioinformatics. |

Also appends one dated entry to `projects/<project_title>/HISTORY.md`.

`00_data/` is never modified by this stage.
