# Stage 00: Initialize Project

## Purpose
Create a project workspace and register its raw data. This stage collects the project title, the
assay types to be analyzed, and one raw data path per assay; it then copies the project stamp,
symlinks the raw files, and writes the project's `CONTEXT.md`, `HISTORY.md` and per-assay
`files.csv` and `samples.csv`.

**The computation is not yours.** `_system/stage00_register.py` sanitizes the title, validates the
assays, copies the stamp, scans each source directory, derives sample IDs, creates the symlinks,
writes both metadata files, substitutes the placeholders and runs the exit gate. Your job is the
dialogue between its phases, and the confirmations it refuses to assume. See
`docs/decisions/0011-deterministic-artifacts-in-stages-00-01.md` in the GARS repository for why.

## Inputs
- Working (this run), collected from the user:
  1. **Project title**
  2. **Assay type/s to be analyzed**
  3. **One raw data directory path per supported assay**
- Reference (every run):
  - `_system/stage00_register.py` — the registrar
  - `_references/assay_stage_skill_map.md` — the definitive list of supported assays
  - `_references/VERSION` — the template version stamped into the project
  - `_templates/project/` — the stamp the script copies

## Scope Boundaries
This stage performs the steps in Process and nothing else.

- **Never compute a result the script computes.** Do not count files, derive a sample ID, decide
  a layout, build `files.csv`, or fill a placeholder yourself — not to double-check it, and not
  when the cohort is small enough that it would be quick. Its JSON is the only source of truth.
- **Never invent a `--sample-id-pattern`.** If filenames do not match the convention the script
  refuses rather than guessing. Report the naming you were shown, ask the user how to read it,
  and pass back only a pattern they gave you.
- **Never pass `--force` to `link`.** It re-links a populated `raw/`, which is how an existing
  project gets narrowed. If `link` refuses, report it and stop.
- Never search for data. The script inspects only the top level of the path the user gives. Do
  not look in subdirectories, do not infer a likely alternative location, and do not read sample
  sheets, settings files, QC reports, or pipeline outputs found there.
- Filesystem reads are limited to this workspace's own files and the exact paths the user
  provides. Do not list, read, or search any other location.
- Report only what the script returns. Do not report incidental observations about the user's
  filesystem, about prior analyses, or about the content of the data.
- Never offer to do work belonging to another stage. If the user asks for it, name the stage that
  owns it and stop.
- **Never narrow an existing project.** Once `files.csv` is written and symlinks exist, do not
  edit `files.csv`, do not delete symlinks, and do not remove samples — not even when the user
  asks to "drop", "discard", or "only analyze" a subset. Sample selection is expressed by removing
  rows from `samples.csv`, which stage 01 honours as an exclusion; the raw data stays in place so
  the choice is reversible. Direct the user there and stop.
- **Never edit `_templates/project/`.** It is the stamp every project is copied from; changing it
  changes every future project.
- Do not perform QC, analysis, or interpretation of the data.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Definitions

The script owns these rules; they are stated here so you can explain a refusal, not so you can
perform the check.

**Title sanitization.** Keep characters matching `[A-Za-z0-9_-]`. Replace each space with `_`.
Drop every other character. Collapse runs of `_` into one, and strip leading/trailing `_` and `-`.
Example: `Macrophage Polarization (Study #2)` -> `Macrophage_Polarization_Study_2`.

**Assay ID.** The directory-safe assay name, from the Assay ID column of
`_references/assay_stage_skill_map.md`. An assay is supported if the user's phrase matches that
table's **Assay** or **Assay ID** column after normalisation — case-folded, with every
non-alphanumeric character dropped. So `rnaseq-bulk`, `rnaseq_bulk`, `RNAseq Bulk`, `Bulk RNA-seq`
and `bulk rna seq` all resolve to `rnaseq_bulk`.

This is normalisation, **not fuzzy matching**: no edit distance, no substring, no stemming.
`rnaseq` alone is still refused, and so is a skill name such as `rnaseq-de`. If a phrase normalises
onto two assays, the script refuses and asks for the Assay ID rather than choosing — a wrong assay
silently builds the wrong pipeline.

**Raw NGS file.** A file matching `*.fastq.gz`, `*.fq.gz`, `*.fastq`, or `*.fq` **at the top level
only** of the given directory. Everything else is excluded and reported as excluded.

**Sample ID and sample-lane unit.** Derived from the Illumina bcl2fastq convention
`<sample>_S<n>[_L<lane>]_R<1|2>_<nnn>.fastq.gz`: the sample is the part before `_S<n>`, and a
sample-lane unit is one `(sample_id, lane)` pair — the grain of `files.csv`. Filenames carrying no
lane token yield one unit per sample, with the lane column empty. Filenames matching no
convention are **refused**, never guessed; see `--sample-id-pattern` below.

**Read pairing.** An assay directory is paired-end when every sample-lane unit has both reads,
single-end when none do. Anything else is a mixed/incomplete set and is refused.

**File integrity.** A linked raw file passes when its symlink resolves, the target is non-empty,
and — for `.gz` files — a full decompression succeeds, exactly as `gzip -t` does. This is the only
check performed on file contents at this stage, and it is O(data): expect minutes on a real
cohort.

**Project stamp.** `_templates/project/`, the blank skeleton every project starts as. The script
copies it and substitutes `{{placeholders}}`; it never assembles a project file from scratch. The
stamp is the schema — if a project needs a new file, it is added to the stamp, not to this
Process.

**Template version.** Read from `_references/VERSION`, or `unknown` if absent. Recorded in both
`CONTEXT.md` and `HISTORY.md`, because a project that cannot name the contract version that
produced it is not reproducible. `unknown` is an honest value; a fabricated version is not.

**The two metadata files.** Sample metadata is split by grain and by owner:

| File | Grain | Written by | Edited by user |
|---|---|---|---|
| `files.csv` | one row per sample-lane unit | the script | never |
| `samples.csv` | one row per distinct sample | the script (IDs only) | yes — the experimental columns |

Keeping them separate means the user enters each experimental value exactly once, and makes "the
same sample carries conflicting conditions" structurally impossible rather than a check.

**The script's four subcommands** are this contract's own phases, so a conversation turn sits
between each:

| Subcommand | Does | Backs |
|---|---|---|
| `create` | sanitize title, validate assays, copy the stamp, make `raw/` dirs | T2, T3 |
| `inspect` | read-only scan of one source directory | T4a |
| `link` | symlink one assay's raw files | T4b |
| `finalize` | `files.csv`, `samples.csv`, placeholders, exit gate | T6, T9 |

**The script's exit codes.** These, and not your reading of its output, determine the branch:

| Code | Meaning | Reply |
|---|---|---|
| 0 | ok | continue |
| 1 | failure; report and stop | T9 |
| 2 | refused; its `template` field names the reply | T5 / T7 / T8 |
| 3 | usage or precondition error | T9 |

## Process
1. Activated when the user says they want to start a new project. Reply T1.
2. Receive the project title. Reply T2 with it.
3. Reply T3, asking for the assay types.
4. Receive the assay types. Run, from the workspace root:

   ```bash
   python3 _system/stage00_register.py create --title "<title>" --assays "<assay>" ["<assay>" ...]
   ```

   It needs no conda environment. Pass the user's phrases through unchanged — resolving them to
   Assay IDs is the script's job, and guessing on its behalf is how the wrong assay gets created.
5. Exit 2 with `template: T7` → the project exists. Reply T7 and wait for a different title.
   Nothing was created.
6. Exit 2 with `template: T8` → no requested assay is supported. Reply T8 using its `assays` and
   `supported_assays`. Nothing was created. Stop.
7. Exit 0 → the stamp is copied and `00_data/<Assay ID>/raw/` exists for each supported assay.
   Reply T3's validation table, then ask for the raw data path of the **first** supported assay.
   Handle assays strictly one at a time, never asking for the next until the current is resolved.
8. Receive a path. Inspect it, writing nothing:

   ```bash
   python3 _system/stage00_register.py inspect --assay <Assay ID> --source <path>
   ```

9. Exit 2 → reply T5 with its `error`. Accept either a replacement path or `skip`. If the error
   names unmatched filenames, show them, ask the user how sample IDs should be read, and re-run
   `inspect` with `--sample-id-pattern '<their answer as a regex with named groups sample, read
   and optionally lane>'`. Never compose that pattern from your own reading of the filenames.
10. Exit 0 → reply T4a with its counts and `sample_ids`, and **ask the user to confirm before
    anything is written**. Do not link yet.
11. On confirmation, link:

    ```bash
    python3 _system/stage00_register.py link --project projects/<title> --assay <Assay ID> --source <path>
    ```

    Never add `--force`. Exit 1 → report its `error` and stop; the raw directory is already
    populated and narrowing an existing project is not this stage's to do.
12. Exit 0 → reply T4b with its `linked` count.
13. Repeat steps 8-12 for each remaining supported assay.
14. When every assay is linked, finalize:

    ```bash
    python3 _system/stage00_register.py finalize --project projects/<title>
    ```

    Add the same `--sample-id-pattern` if one was used at step 9. This writes `files.csv` and
    `samples.csv`, substitutes the stamp's placeholders, and runs the exit gate.
15. Exit 1 or 3 → reply T9 listing every entry of its `failures` array. Do not claim completion,
    do not repair anything, and do not delete what was created — the user decides whether to fix
    or discard.
16. Exit 0 → reply T6 using its `assays` map and `template_version`.

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
<error>

Nothing was created or linked.
<if the error names unmatched filenames, list them and ask how sample IDs should be read>

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
| <name> | Not supported<, or: ambiguous between <ids>> |

None of the requested assays are supported, so no project was created.

Supported assays — either column is accepted:

| Assay | Assay ID |
|---|---|
| <assay> | <assay_id> |
```
Render the table from the script's `supported_assays`, which carries both forms. Listing only the
display name leaves a user who typed an ID-like phrase with nothing to correct against.

## OUTPUT
Written to `projects/<project_title>/` by the script, and never by hand:

| Artifact | Contents |
|---|---|
| `CONTEXT.md` | The stamp's `CONTEXT.md` with placeholders filled: title, creation date, template version, assays and Assay IDs, raw data source paths, per-assay file and sample counts. The project's L1 context file. |
| `HISTORY.md` | The stamp's `HISTORY.md` with placeholders filled: a dated creation entry naming the template version, assays, source paths and per-assay file counts. |
| `_config/` | Empty, from the stamp. The user writes it before stage 02 — schema in `_references/config_schema.md`. |
| `00_data/<Assay ID>/raw/` | Symlinks to the source raw NGS files. Sources are never copied or moved. |
| `00_data/<Assay ID>/files.csv` | `sample_id,lane,fastq_1,fastq_2`. One row per sample-lane unit, paths relative to the project directory. Machine-owned; never hand-edited. |
| `00_data/<Assay ID>/samples.csv` | `sample_id,condition,group,replicate`. One row per distinct sample. `sample_id` filled; the rest blank for the user to complete. |

Re-running `finalize` on unchanged inputs reproduces `files.csv`, `samples.csv`, `CONTEXT.md` and
`HISTORY.md` byte for byte.

## Human check
Open each `00_data/<Assay ID>/samples.csv` and confirm the `sample_id` column lists the samples
you expect, spelled as you expect — this is the last point at which a mis-derived sample ID is
cheap to fix. The script verifies that every file resolves and decompresses; only you can verify
that these are the right files. Then fill `condition`, `group` and `replicate`, one row per sample, and delete the
rows of any sample you do not want analysed.

Stage 01 reads whatever you leave there. Do not proceed until `CONTEXT.md` exists and at least
one assay has both `files.csv` and `samples.csv`.
