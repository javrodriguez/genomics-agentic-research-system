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

**Title sanitization.** The script derives a directory-safe title and reports it as
`sanitized_title`. Show the user both forms; never construct one yourself.

**Assay ID.** The directory-safe assay name, from the Assay ID column of
`_references/assay_stage_skill_map.md` — the definitive list of supported assays. The script
matches the user's phrase against that table after normalisation, so `rnaseq-bulk`, `RNAseq Bulk`
and `Bulk RNA-seq` all resolve to `rnaseq_bulk`.

It is normalisation, **not fuzzy matching**: a near miss such as `rnaseq` alone, or a skill name
such as `rnaseq-de`, is refused rather than resolved, and a phrase matching two assays is refused
as ambiguous. That refusal is the point — a wrong assay silently builds the wrong pipeline — so
report it and let the user choose. Never resolve a phrase yourself.

**Menu number.** The `01`, `02` … the `assays` subcommand hands out. **Presentation only.** They
are assigned from a deterministic sort and regenerated on every call, so the numbering offered is
always the numbering `--select` resolves against — but adding an assay to the map renumbers them.
A number must never be written to disk, recorded in `HISTORY.md`, used as a directory name, or
carried across turns. The Assay ID is the durable identifier; convert as soon as the user answers,
and refer to assays by ID and name from then on.

**Raw NGS file.** `*.fastq.gz`, `*.fq.gz`, `*.fastq` or `*.fq`, **at the top level only** of the
given directory. Everything else is reported as excluded. The script never descends.

**Sample ID and sample-lane unit.** Sample IDs come from the Illumina bcl2fastq convention; a
sample-lane unit is one `(sample_id, lane)` pair, the grain of `files.csv`. **Filenames matching
no convention are refused, never guessed** — the script reports the ones it could not read, and
only a pattern the *user* supplies via `--sample-id-pattern` resolves them.

**Read pairing.** Wholly paired-end or wholly single-end. A mixed set is refused.

**File integrity.** A linked raw file passes when its symlink resolves, the target is non-empty,
and — for `.gz` files — a full decompression succeeds. This is the only check performed on file
contents at this stage.

`--integrity` selects the depth, and the choice is **recorded in the project's `HISTORY.md`**, so
a project can always name the verification it received:

| Mode | Checks | Cost |
|---|---|---|
| `quick` (default) | resolves, non-empty, gzip magic | metadata only |
| `full` | additionally decompresses every `.gz` | O(data) — see below |
| `skip` | resolves, non-empty | metadata only |

**The default is `quick`, and that is deliberate.** This stage registers everything the user
pointed at; the user does not choose which samples to analyse until the 00 → 01 gate. Deep
verification here would spend its cost on files that are about to be excluded — on a real cohort,
48 GB of reading to validate a 4-sample pilot. Deep verification of the files that will actually
be analysed belongs to **stage 01**, which offers it. See
`docs/decisions/0013-integrity-verification-moves-to-stage-01.md`.

If the user asks for `full` here anyway, quote the cost from `inspect`'s `total_gb` and
`full_check_estimate_min`, and **submit it with `sbatch` when `total_bytes` exceeds ~10 GB** —
reading tens of GB on a shared login node is not this stage's to do, and the node's per-user
memory cgroup will kill whatever is running rather than whatever is at fault.

**Never downgrade the mode on your own initiative** to make a slow step finish. Report the cost
and let the user choose.

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
| `assays` | offer the supported assays; resolve the user's selection | T3 |
| `create` | sanitize title, copy the stamp, make `raw/` dirs | T3b |
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
3. **Always offer the menu, whether or not the user named an assay.** Run:

   ```bash
   python3 _system/stage00_register.py assays
   ```

   Reply T3, rendering every entry of its `assays` array. Do this even when the request already
   names an assay unambiguously — the menu is what makes the set of choices visible, and this is
   the last moment before any directory exists when a correction is free. If the user did name
   one, say which menu entry it matches so confirming costs one word.
4. Receive the selection and resolve it:

   ```bash
   python3 _system/stage00_register.py assays --select "<exactly what the user replied>"
   ```

   Pass their reply through **unchanged**. It accepts menu numbers, Assay IDs and assay names, in
   any mixture; resolving is the script's job, and doing it yourself is how the wrong assay gets
   created.
5. Exit 2 → reply T3 again, naming its `invalid` entries, and wait. Never proceed on a partial
   selection, and never substitute the entry you think was meant.
6. Exit 0 → take its **`assay_ids`**. Create the project:

   ```bash
   python3 _system/stage00_register.py create --title "<title>" --assays <assay_id> [<assay_id> ...]
   ```

   Pass Assay IDs, **never menu numbers**. The numbers are a display convenience regenerated on
   every call; an assay added to the map renumbers them, so a number that reaches disk or a later
   turn means something else.
7. Exit 2 with `template: T7` → the project exists. Reply T7 and wait for a different title.
   Nothing was created. Exit 2 with `template: T8` → reply T8; nothing was created; stop.
8. Exit 0 → the stamp is copied and `00_data/<Assay ID>/raw/` exists for each assay. Reply T3b
   confirming what was created **by Assay ID and name**, then ask for the raw data path of the
   **first** assay. Handle assays strictly one at a time, never asking for the next until the
   current is resolved.
9. Receive a path. Inspect it, writing nothing:

   ```bash
   python3 _system/stage00_register.py inspect --assay <Assay ID> --source <path>
   ```

10. Exit 2 → reply T5 with its `error`. Accept either a replacement path or `skip`. If the error
   names unmatched filenames, show them, ask the user how sample IDs should be read, and re-run
   `inspect` with `--sample-id-pattern '<their answer as a regex with named groups sample, read
   and optionally lane>'`. Never compose that pattern from your own reading of the filenames.
11. Exit 0 → reply T4a with its counts and `sample_ids`, and **ask the user to confirm before
    anything is written**. Do not link yet.
12. On confirmation, link:

    ```bash
    python3 _system/stage00_register.py link --project projects/<title> --assay <Assay ID> --source <path>
    ```

    Never add `--force`. Exit 1 → report its `error` and stop; the raw directory is already
    populated and narrowing an existing project is not this stage's to do.
13. Exit 0 → reply T4b with its `linked` count.
14. Repeat steps 9-13 for each remaining assay.
15. When every assay is linked, finalize. **This is the slow step** — minutes on a real cohort —
    so run it in the background rather than in a foreground call that a command timeout will
    kill, and tell the user it is running:

    ```bash
    python3 _system/stage00_register.py finalize --project projects/<title>
    ```

    Add the same `--sample-id-pattern` if one was used at step 9. This writes `files.csv` and
    `samples.csv`, substitutes the stamp's placeholders, and runs the exit gate. It is
    deterministic and re-runnable: on unchanged inputs it reproduces the four files byte for
    byte, so a killed run costs only time.

    It runs `--integrity quick` by default — metadata only, fast. Pass a different depth **only
    if the user asked for one**, and never downgrade on your own initiative.
16. Exit 1 or 3 → reply T9 listing every entry of its `failures` array. Do not claim completion,
    do not repair anything, and do not delete what was created — the user decides whether to fix
    or discard.
17. Exit 0 → reply T6 using its `assays` map and `template_version`.

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

**T3 — Assay menu**

Sent whether or not the user named an assay. Render one block per entry of the script's `assays`
array, in the order given. The sub-stage list comes from that entry's `substages` and is the
pipeline that assay would run — do not describe it in your own words, and do not add assays,
capabilities, or timelines that are not in the array.

```
Supported assays:

  01  Bulk RNA-seq  (rnaseq_bulk)
      pipeline: 01_nfcore-rnaseq-wrapper -> 02_rnaseq-de
      skills:   nfcore-rnaseq-wrapper, rnaseq-de

<repeat per entry>

<if the request already named one: "Your request matches 01.">
<if re-asking after an unresolved reply: "Could not resolve: <invalid>.">

Reply with a comma-separated list of IDs (e.g. `01` or `01,02`). Assay names work too.
```

The numbers are for this message only. Everything after this point — the confirmation, the
directories, `HISTORY.md` — uses the Assay ID.

**T3b — Project created**
```
Created: projects/<title>/

| Assay | Assay ID | Data directory |
|---|---|---|
| <assay> | <assay_id> | 00_data/<assay_id>/ |

Raw data path for <assay_id>?
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

File integrity: <integrity.files_checked> files checked, mode <integrity.mode>.

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
