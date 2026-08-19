# Stage 01: Prepare Samplesheets

## Purpose
Validate the experimental design the user completed in each assay's `samples.csv`, join it to
that assay's `files.csv`, and emit a workflow-ready samplesheet and design table per assay.
This stage writes no data and modifies no input; it is the gate between raw data registration
(stage 00) and processing (stage 02).

**The computation is not yours.** `_system/stage01_samplesheet.py` performs every check and
writes every artifact. Your job is to run it, hold the two human gates it refuses to cross on
its own, and report what it found. See
`docs/decisions/0011-deterministic-artifacts-in-stages-00-01.md` in the GARS repository for why.

## Inputs
- Working (this run):
  1. **Project title**
  2. **A completed `00_data/<Assay ID>/samples.csv` per assay** — `condition`, `group` and
     `replicate` filled in by the user, one row per sample
  3. **`00_data/<Assay ID>/files.csv` per assay** — written by stage 00, read-only here
  4. **`_config/<Assay ID>.yaml`** — read for `strandedness` only; absent is legal
- Reference (every run):
  - `_system/stage01_samplesheet.py` — the validator and emitter

## Scope Boundaries
This stage performs the steps in Process and nothing else.

- **Never compute a result the script computes.** Do not count rows, resolve paths, check group
  sizes, derive a layout, or build a samplesheet yourself — not to double-check it, not when it
  seems obvious, and not when the project is small enough that it would be quick. Its JSON is the
  only source of truth for what is in these files.
- **Never write, edit, or repair `01_samplesheets/` by hand.** If the script cannot produce an
  artifact, the stage has failed; report it and stop.
- **Never modify `samples.csv` or `files.csv`.** `samples.csv` is the user's file; `files.csv` is
  stage 00's. Report every problem found and stop; never silently correct, reformat, or fill a
  value in either.
- Never infer a missing experimental value. A blank `condition`, `group` or `replicate` is a
  validation failure, not something to guess from sample names.
- Never create, re-link, move, or delete anything under `00_data/`. Stage 00 owns it.
- **Never pass `--confirm-exclusions` or `--force` without an explicit user confirmation in this
  conversation.** They are the two human gates; supplying either on the user's behalf is the one
  way this stage can destroy work irreversibly.
- Never run a bioinformatics workflow, aligner, or QC tool, and never read FASTQ contents. That
  is stage 02's work.
- Filesystem reads are limited to: this workspace's own files, and inside the named project its
  `CONTEXT.md`, `HISTORY.md`, `_config/` and `00_data/`. Do not read or search elsewhere.
- Do not report incidental observations about the user's filesystem or prior analyses.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Definitions

These are the terms the script's failures are named with. They are here so you can explain a
failure, not so you can perform the check.

**Complete design row.** A `samples.csv` row where `sample_id`, `condition`, `group` and
`replicate` are all non-empty. Violation → `incomplete_design`.

**Resolvable file row.** A `files.csv` row whose `fastq_1` and, if present, `fastq_2` resolve
relative to the project directory to a readable file. Violation → `unresolvable_path`.

**Referential integrity.** The two directions mean different things:

| Direction | Meaning | Handling |
|---|---|---|
| `sample_id` in `samples.csv` but not `files.csv` | the user invented a row, or mistyped an ID | **failure** → `referential_integrity` |
| `sample_id` in `files.csv` but not `samples.csv` | the user deliberately dropped the sample | **exclusion** — legal, but never silent |

**Exclusion.** Removing a sample's row from `samples.csv` is how the user narrows a project to a
subset, and the only supported way to do so. The excluded sample keeps its raw symlinks and its
`files.csv` rows — nothing on disk is deleted, so the choice stays reversible and `files.csv`
remains a faithful record of what was ingested. Excluded samples are omitted from the samplesheet
and design table, and **must be confirmed by the user before anything is written**.

**Valid design.** All of, considering included samples only. Violations → `invalid_design`.
- every `group` contains at least 2 distinct `sample_id` values — a group of one cannot be tested
  for differential expression;
- within a given `group` and `condition`, no `replicate` repeats for distinct samples;
- no `sample_id` appears more than once in `samples.csv`;
- no `(sample_id, lane)` pair appears more than once in `files.csv`;
- an assay is wholly paired-end or wholly single-end, never mixed.

**Samplesheet.** `01_samplesheets/<Assay ID>_samplesheet.csv`, nf-core compatible, header
`sample,fastq_1,fastq_2,strandedness`. One row per included `files.csv` row, paths absolute **and
inside the project** — they point at the symlinks in `00_data/<Assay ID>/raw/`, never at the
original sequencing run. Following the symlink would bypass the project's own registration of its
data; this is why 02.01 warns that moving a project invalidates its samplesheet.
`strandedness` comes from `_config/<Assay ID>.yaml` if it defines a top-level value, else `auto`;
an unrecognised value is a `config` failure rather than a silent default. Multiple rows sharing a
`sample` value are merged by nf-core as technical replicates, which is the intended handling of
multi-lane samples.

**Malformed input.** Two failures mean the file itself is unusable rather than the design wrong:
`header` (a metadata CSV's columns are not the expected set) and `preconditions` (a metadata CSV
is missing, empty, or unreadable). Both mean stage 00's output was edited or damaged — direct the
user there rather than to `samples.csv`.

**Design table.** `01_samplesheets/<Assay ID>_design.csv`, header
`sample_id,condition,group,replicate`. One row per included `sample_id`. Consumed by the
differential-expression sub-stage of 02_bioinformatics.

**The script's exit codes.** These, and not your reading of its output, determine the branch:

| Code | Meaning | Reply |
|---|---|---|
| 0 | clean (checked, or written) | T2 then T4 |
| 1 | validation failed; nothing written | T3 |
| 2 | a human gate is uncleared; nothing written | T7 and/or T5 |
| 3 | preconditions not met | T6 |

## Process
1. Activated when the user asks to prepare samplesheets or to proceed past stage 00. Reply T1.
2. Resolve the project directory from the title.
3. Run the validator, from the workspace root:

   ```bash
   python3 _system/stage01_samplesheet.py --project projects/<title> --check
   ```

   It needs no conda environment. Parse its JSON; branch on its **exit code** per Definitions.
4. Exit 3 → reply T6 using its `error` field, and stop.
5. Exit 1 → reply T3, rendering every entry of every assay's `failures` array verbatim in the
   table. Write nothing, and do not offer to fix any of it. Stop.
6. Exit 0 with `exclusions_pending: true` → reply T7 listing every assay's `exclusions`, and wait.
   Never proceed on a silent exclusion, and never infer that a missing row was an oversight.
   On `cancel`, stop.
7. Exit 0 with a non-empty `existing_outputs` → reply T5 listing them, and wait. On `cancel`, stop.
8. Once every applicable gate is confirmed, run the writer with exactly the flags the user
   cleared — `--confirm-exclusions` only if step 6 happened, `--force` only if step 7 did:

   ```bash
   python3 _system/stage01_samplesheet.py --project projects/<title> [--confirm-exclusions] [--force]
   ```

9. Exit 2 → a gate you believed cleared was not. Reply T5 or T7 as its `blocked` array indicates
   and return to step 6. Never re-run adding a flag the user did not confirm.
10. Exit 1 at this point means the **exit gate** failed: the artifacts were written and then found
    wrong on re-read. Reply T3 with the `exit_gate` failures and stop. Do not repair them.
11. Exit 0 → reply T2 using each assay's `counts`.
12. Append the script's `history_entry` to the project's `HISTORY.md` **verbatim**, replacing
    `<ISO-8601 date>` with today's date. Do not restate its numbers in your own words — they are
    the script's counts, not your recollection.
13. Reply T4 using `wrote` and each assay's `counts`.

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
| Assay | Rows | Samples | Groups | Layout | Strandedness |
|---|---|---|---|---|---|
| <Assay ID> | <samplesheet_rows> | <samples_included> of <samples_total> | <groups> | <layout> | <strandedness> |

All checks passed. Writing samplesheets.
```

**T3 — Validation failed**
```
Validation failed. Nothing was written; no input file was modified.

| Assay | Check | Detail |
|---|---|---|
| <Assay ID> | <check> | <detail> |

Correct 00_data/<Assay ID>/samples.csv and run stage 01 again.
```

**T4 — Stage complete**
```
Stage 01 complete. Samplesheets written to projects/<title>/01_samplesheets/.

| Assay | Samplesheet rows | Design rows | Files |
|---|---|---|---|
| <Assay ID> | <samplesheet_rows> | <design_rows> | <Assay ID>_samplesheet.csv, <Assay ID>_design.csv |

Next: run 02_bioinformatics for <Assay ID>.
```

**T5 — Existing samplesheets**
```
01_samplesheets/ already contains files for <Assay ID>:
<existing_outputs>

Confirm to overwrite, or reply `cancel` to stop.
```

**T6 — Preconditions not met**
```
Cannot start stage 01.

<error>

Run 00_initialize_project first.
```

**T7 — Samples excluded, awaiting confirmation**
```
<n> sample(s) have raw data but no row in samples.csv, and will be excluded from the analysis:

| sample_id | Files in files.csv |
|---|---|
| <sample_id> | <file_rows> |

Proceeding with <samples_included> of <samples_total> samples. Raw data and files.csv are left
untouched, so this is reversible: add the rows back to samples.csv and run stage 01 again.

Confirm to proceed with the reduced set, or reply `cancel`.
```

## OUTPUT
Written to `projects/<project_title>/01_samplesheets/`, by the script and never by hand:

| Artifact | Contents |
|---|---|
| `<Assay ID>_samplesheet.csv` | nf-core compatible: `sample,fastq_1,fastq_2,strandedness`. One row per included sample-lane, absolute paths. Consumed by 02_bioinformatics. |
| `<Assay ID>_design.csv` | `sample_id,condition,group,replicate`. One row per included sample. Consumed by the differential-expression sub-stage of 02_bioinformatics. |

The agent appends the script's `history_entry` to `projects/<project_title>/HISTORY.md`.

`00_data/` is never modified by this stage. Re-running on unchanged inputs reproduces both files
byte for byte.

## Human check
Open `<Assay ID>_samplesheet.csv` and spot-check that the FASTQ paths in the first and last rows
resolve, and that the number of rows matches the sample-lane count you expect. Then open
`<Assay ID>_design.csv` and confirm the group sizes are the ones you intend to contrast — a
design with the wrong replicate counts runs to completion and answers the wrong question.

The script verifies structure; only you can verify intent.

Both files are yours to edit before stage 02 reads them.
