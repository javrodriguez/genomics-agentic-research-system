# Stage 00: Initialize Project

## Purpose
Create a project workspace and register its raw data. This stage collects the project title,
the assay types to be analyzed, and one raw data path per assay; it then **copies the project
stamp** from `_templates/project/`, symlinks the raw files, and fills in the stamp's placeholders
plus the per-assay files.csv and samples.csv.

## Inputs
- Working (this run), collected from the user:
  1. **Project title**
  2. **Assay type/s to be analyzed**
  3. **One raw data directory path per supported assay**
- Reference (every run):
  - `_references/assay_stage_skill_map.md` — the definitive list of supported assays
  - `_references/VERSION` — the template version stamped into the project
  - `_templates/project/` — the stamp this stage copies

## Scope Boundaries
This stage performs the steps in Process and nothing else.

- Filesystem reads are limited to this workspace's own files and the exact paths the user
  provides. Do not list, read, or search any other location.
- Never search for data. Inspect only the top level of the path the user gives. If it holds
  no raw NGS files, stop and reply with T5. Do not look in subdirectories, do not infer a
  likely alternative location, and do not read sample sheets, settings files, QC reports, or
  pipeline outputs found there.
- Report only what Process produces. Do not report incidental observations about the user's
  filesystem, about prior analyses, or about the content of the data.
- Never offer to do work belonging to another stage. If the user asks for it, name the stage
  that owns it and stop.
- **Never narrow an existing project.** Once `files.csv` is written and symlinks exist, do not
  edit `files.csv`, do not delete symlinks, and do not remove samples — not even when the user
  asks to "drop", "discard", or "only analyze" a subset. Sample selection is expressed by
  removing rows from `samples.csv`, which stage 01 honours as an exclusion; the raw data stays
  in place so the choice is reversible. Direct the user there and stop.
- **Never edit `_templates/project/`.** It is the stamp every project is copied from; changing
  it changes every future project. Fill the placeholders in the *copy*, never in the stamp.
- Do not perform QC, analysis, or interpretation of the data.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Definitions

**Title sanitization.** Keep characters matching `[A-Za-z0-9_-]`. Replace each space with `_`.
Drop every other character. Collapse runs of `_` into one, and strip leading/trailing `_` and
`-`. Example: `Macrophage Polarization (Study #2)` -> `Macrophage_Polarization_Study_2`.

**Assay ID.** The directory-safe assay name, taken from the Assay ID column of
`_references/assay_stage_skill_map.md`. Used for `00_data/<Assay ID>/` and wherever an assay is
named on disk. Never use the free-text assay name.

**Raw NGS file.** A file matching `*.fastq.gz`, `*.fq.gz`, `*.fastq`, or `*.fq` at the top
level of the given directory. Everything else is excluded and reported as excluded.

**Read pairing.** Files are paired when names differ only in `_R1_`/`_R2_` (or `_1.`/`_2.`).
A directory is paired-end if every raw file has a partner, single-end if none do. Any other
result is a mixed/incomplete set: report the unpaired filenames and use T5.

**File integrity.** A linked raw file passes integrity when its symlink resolves, the target
is non-empty, and — for `.gz` files — `gzip -t` reports no error. These are the only checks
performed on file contents at this stage.

**Project stamp.** `_templates/project/`, the blank skeleton every project starts as. This
stage **copies it and substitutes placeholders**; it never assembles a project file from
scratch. The stamp is the schema — if a project needs a new file, it is added to the stamp, not
to this Process. Placeholders are `{{name}}` and are listed in `_templates/CONTEXT.md`.

**Template version.** The GARS revision that created the project, recorded so a project can
always name the contract version that produced it. A workspace is a copy of the template, so
this cannot be inferred later — it must be captured at creation.

Resolve it from `_references/VERSION` if present, otherwise from git if the workspace was copied
from a checkout, otherwise record `unknown`:

```bash
V=$(cat _references/VERSION 2>/dev/null || git -C <template> describe --always --dirty 2>/dev/null || echo unknown)
```

Never guess or omit it. `unknown` is an acceptable and honest value; a fabricated version is not.

**Sample ID.** The filename prefix preceding the read/lane suffix. For Illumina bcl2fastq
output (`<sample>_S<n>_L<lane>_R<1|2>_001.fastq.gz`) this is the part before `_S<n>`. If the
filenames do not match this convention, do not guess: report the naming you observe and ask
the user how to derive sample IDs.

**Sample-lane unit.** One `(sample_id, lane)` pair — for paired-end data, the R1 and R2 files
of a single sample on a single lane. It is the grain of `files.csv`.

**The two metadata files.** Sample metadata is split by grain and by owner, and the split is
deliberate:

| File | Grain | Written by | Edited by user |
|---|---|---|---|
| `files.csv` | one row per sample-lane unit | stage 00 | never |
| `samples.csv` | one row per distinct sample | stage 00 (IDs only) | yes — the experimental columns |

Keeping them separate means the user enters each experimental value exactly once, and it makes
"the same sample carries conflicting conditions" structurally impossible rather than a check.

## Process
1. This process is activated when the user says he wants to start a new project. Reply with T1.
2. Receive the project title. Sanitize it per Definitions.
3. If `projects/<sanitized_title>/` already exists, stop and reply with T7. Never overwrite,
   merge into, or delete an existing project. Wait for the user to supply a different title.
4. Reply with T2, asking for the assay types.
5. Receive the assay types. An assay is supported if and only if it appears in the Assay
   column of `_references/assay_stage_skill_map.md`.
6. If no requested assay is supported, reply with T8 and stop. Create nothing.
7. Copy the stamp: `cp -r _templates/project projects/<sanitized_title>`. Then create one
   `00_data/<Assay ID>/raw/` per supported assay. Create nothing for unsupported assays, and
   add no file the stamp does not contain.
8. Reply with T3: the validation table, then a request for the raw data path of the first
   supported assay. If there is more than one supported assay, handle them strictly one at a
   time, never asking for the next until the current one is resolved.
9. Receive a path. Inspect only its top level. Count raw NGS files, determine pairing, and
   derive sample IDs, all per Definitions.
10. If there are no raw NGS files, reply with T5 and stop for this assay. Create no symlinks.
    Accept either a replacement path or `skip`.
11. If raw NGS files are present, reply with T4a: the file/sample counts and the derived
    sample ID list, and ask the user to confirm before anything is written. Do not create
    symlinks yet.
12. On confirmation, create one symlink per raw NGS file in `00_data/<Assay ID>/raw/`, pointing
    at the source file. Never copy or move source files. Verify every link resolves. Reply
    with T4b.
13. Repeat steps 9-12 for each remaining supported assay.
14. Write `00_data/<Assay ID>/files.csv` per assay, one row per sample-lane unit, header
    `sample_id,lane,fastq_1,fastq_2`. `fastq_1`/`fastq_2` hold the symlink paths relative to the
    project directory; `fastq_2` is empty for single-end. This file is machine-owned — say so
    in a comment on the first line: `# generated by stage 00 — do not edit`.
15. Write `00_data/<Assay ID>/samples.csv` per assay, one row per distinct `sample_id`, header
    `sample_id,condition,group,replicate`. Fill `sample_id` only; leave `condition`, `group`,
    and `replicate` blank for the user to complete.
16. Resolve the **template version** per Definitions. Both `CONTEXT.md` and `HISTORY.md` carry
    it — a project that cannot name the contract version that produced it is not reproducible.
17. Substitute the placeholders in the copied `CONTEXT.md`: `{{project_title}}`, `{{created}}`,
    `{{template_version}}`, `{{assay_table}}` (one row per supported assay: assay name, Assay ID,
    data directory, file count, sample count) and `{{source_paths}}` (one row per assay: Assay
    ID, source path, files linked). Change nothing else in the file — its remaining sections are
    the stamp's, not this stage's.
18. Substitute the same placeholders in the copied `HISTORY.md`. Append nothing beyond the
    creation entry the stamp already carries.
19. Run the exit gate. All of: `CONTEXT.md` exists; `HISTORY.md` exists; `_config/` exists;
    **no file under the project contains a literal `{{`** — an unsubstituted placeholder means
    the stamp was copied but never filled, which produces a project that looks complete and is
    not; every supported assay has a non-empty `files.csv` and `samples.csv`; the distinct
    `sample_id` count in `files.csv` equals the row count of `samples.csv`; every linked file
    passes **file integrity**; pairing is complete for every paired-end assay; no `sample_id` is
    empty. If any check fails, reply with T9 naming exactly which files failed and stop. Do not
    claim completion, and do not delete what was created — the user decides whether to fix or
    discard.
20. Reply with T6.

## Response Format
Every message you send in this stage is one of the templates below, with placeholders filled.
Add nothing else: no observations, no suggestions, no offers, no commentary about the data or
about anything encountered on the filesystem.

**T1 — Start**
```
Starting stage 00: Initialize Project.
I will collect, in order: (1) project title, (2) assay types, (3) one raw data path per assay.

Project title?
```

**T2 — Title accepted**
```
Project title: <raw> -> directory <sanitized>

Which assay types will this project include?
Supported: <Assay column values>
```

**T3 — Assay validation**
```
| Requested | Status | Data directory |
|---|---|---|
| <name> | Supported / Not supported | 00_data/<Assay ID>/ or - |

Created: projects/<title>/
Raw data path for <Assay ID>?
```

**T4a — Path inspected, awaiting confirmation**
```
Path: <path>
Raw NGS files: <n> (<n> R1 / <n> R2, <layout>)
Excluded (not raw NGS): <list or "none">
Samples: <n>
<sample id list>

Confirm to create symlinks under 00_data/<Assay ID>/raw/, or provide a different path.
```

**T4b — Symlinks created**
```
Linked <n> files into 00_data/<Assay ID>/raw/. Broken links: <n>.
<next prompt, or proceed to T6 if this was the last assay>
```

**T5 — Path rejected**
```
Path: <path>
No raw NGS files found at the top level of this path. Nothing was created or linked.

Provide a different path for <Assay ID>, or reply `skip` to omit this assay.
```

**T6 — Stage complete**
```
Stage 00 complete. Project <title> initialized at projects/<title>/.

| Assay | Files linked | Samples | Source |
|---|---|---|---|
| <Assay ID> | <n> | <n> | <path> |

Written: CONTEXT.md, HISTORY.md, and per assay files.csv + samples.csv.

Next: fill condition, group, and replicate in each 00_data/<Assay ID>/samples.csv — one row per
sample. Then run 01_prepare_samplesheets.
```

**T9 — Exit gate failed**
```
Stage 00 did not complete. The project was created but failed its exit checks.

| Check | Status | Detail |
|---|---|---|
| <check> | Failed | <files or assays responsible> |

Nothing was deleted. Resolve the above, or remove projects/<title>/ and start again.
```

**T7 — Project already exists**
```
projects/<sanitized>/ already exists. Nothing was created or modified.

Provide a different project title.
```

**T8 — No supported assay**
```
| Requested | Status |
|---|---|
| <name> | Not supported |

None of the requested assays are supported, so no project was created.
Supported assays: <Assay column values>
```

## OUTPUT
Written to `projects/<project_title>/`:

| Artifact | Contents |
|---|---|
| `CONTEXT.md` | The stamp's `CONTEXT.md` with placeholders filled: title, creation date, template version, assays and Assay IDs, raw data source paths, per-assay file and sample counts. The project's L1 context file. |
| `HISTORY.md` | The stamp's `HISTORY.md` with placeholders filled: a dated creation entry naming the template version, assays, source paths and per-assay file counts. |
| `_config/` | Empty, from the stamp. The user writes it before stage 02 — schema in `_references/config_schema.md`. |
| `00_data/<Assay ID>/raw/` | Symlinks to the source raw NGS files. Sources are never copied or moved. |
| `00_data/<Assay ID>/files.csv` | `sample_id,lane,fastq_1,fastq_2`. One row per sample-lane unit, paths relative to the project directory. Machine-owned; never hand-edited. |
| `00_data/<Assay ID>/samples.csv` | `sample_id,condition,group,replicate`. One row per distinct sample. `sample_id` filled; the rest blank for the user to complete. |

## Human check
Open each `00_data/<Assay ID>/samples.csv` and confirm the `sample_id` column lists the samples
you expect, spelled as you expect — this is the last point at which a mis-derived sample ID is
cheap to fix. Then fill `condition`, `group` and `replicate`, one row per sample, and delete the
rows of any sample you do not want analysed.

Stage 01 reads whatever you leave there. Do not proceed until `CONTEXT.md` exists and at least
one assay has both `files.csv` and `samples.csv`.
