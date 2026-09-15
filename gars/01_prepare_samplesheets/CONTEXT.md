# Stage 01: Prepare Samplesheets

## Purpose
Validate the experimental design the user completed in each assay's `samples.csv`, join it to
that assay's `files.csv`, and emit a workflow-ready samplesheet and design table per assay.
This stage writes no raw data; user-supplied declarations may be written to config; it is the gate between raw data registration
(stage 00) and processing (stage 02).

**The computation is not yours.** `_system/stage01_samplesheet.py` performs every check and
writes every artifact. Your job is to run it, hold the two human gates it refuses to cross on
its own, and report what it found. See
`docs/decisions/0011-deterministic-artifacts-in-stages-00-01.md` in the GARS repository for why.

## Inputs
- Working (this run):
  1. **Project title**
  2. **A completed `00_data/<Assay ID>/samples.csv` per assay** — the assay's design
     columns filled in by the user, one row per sample. The base four are
     `sample_id,condition,group,replicate`; ChIP-family assays add e.g. `control`
     (decision 0030)
  3. **`00_data/<Assay ID>/files.csv` per assay** — written by stage 00, read-only here
  4. **`_config/<Assay ID>.yaml`** — RNA `strandedness`; RNA/ATAC `unit_of_replication`,
     `reference_release`, and optional `paired` declarations (see Definitions)
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
- Never infer a missing experimental value. A blank base column (`condition`, `group`,
  `replicate`) is a
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

**Complete design row.** A `samples.csv` row where the base columns (`sample_id`,
`condition`, `group`, `replicate`) are all non-empty. Violation → `incomplete_design`. An
assay's extra columns (e.g. `control`, decision 0030) may be blank — a ChIP input or IgG
sample has no control of its own — but a non-blank `control` must name a `sample_id` present
in this design. Violation → `referential_integrity`.

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
- for `rnaseq_bulk`: every `group` contains at least 2 distinct `sample_id` values — a group
  of one cannot be tested for differential expression;
- for the group-as-sample assays (`atacseq_bulk`, `chipseq_bulk`, `cutandrun` — decision 0035:
  the pipeline's sample unit IS the group): every `replicate` is a positive integer;
  `(group, replicate)` is unique outright; replicate ids within each group are exactly
  `1..N`; and a `chipseq_bulk` group is antibody-homogeneous — an IP and its input never
  share a group (corrects 0030's shared-group clause);
- for the other assays: within a given `group` and `condition` (plus the assay's identity
  columns), no `replicate` repeats for distinct samples;
- no `sample_id` appears more than once in `samples.csv`;
- no `(sample_id, lane)` pair appears more than once in `files.csv`;
- an assay is wholly paired-end or wholly single-end, never mixed.

**Row 1 design checks (R-072, R-143).** RNA and ATAC designs may append `batch`
after their base columns; it must be filled and is preserved in the emitted design table.
If every batch belongs to exactly one condition and multiple conditions exist, refuse with
`confounded_condition`. `sample_id` is never tested as a covariate. Other candidate
covariates remain outside this row; this is not the complete §7.2 check.
ATAC requires at least two distinct biological `sample_id` values per `condition`;
violation → `insufficient_biological_replicates`. Lanes never increase this count.

**Owner declarations (0043, 2026-09-13, 2A).** For RNA/ATAC, optional `subject`
(donor / patient / model) is preserved alongside optional `batch`, in either order after
base columns. Blank subject for any included sample → `subject_undeclared`.
A subject crossing conditions → `subject_nesting` unless `_config/<Assay ID>.yaml`
contains `paired: paired`. Allowed pairing values are `paired` and `unpaired`;
absent/blank means no paired declaration, never permission to cross conditions.
This describes experimental pairing, independently of paired-end FASTQ layout.
`unit_of_replication` must be `sample`, `subject`, or `cell_pseudobulk`;
missing/blank → `unit_of_replication_undeclared`. `subject` requires the subject column
(`subject_undeclared`). No replication unit is inferred. `reference_release` must be a
nonblank declared scalar; missing/blank → `reference_release_undeclared`.
Unfilled `<REQUIRED>` and YAML null markers count as undeclared. Invalid enumerated values
→ `config`. Stage 01 checks release declaration only, with no genome-registry validation.
Stage 02 retains its reference menu (0020). Existing sample-ID replication floors remain.

**Declaration provenance.** Declaration entries carry value, provenance (seeded_default,
declared_in_config, or absent), and history_ref (last exact matching HISTORY.md line
with its line number and text, or null). Declaration lines use `key: value` with an
optional prefix ending in a space or tab, and end after the value (ignoring trailing
spaces/tabs) or continue with `;` and commentary. Keys and values are matched in full;
`not-paired: paired` does not declare `paired`, and release `synthetic-v1.1` does not
match `synthetic-v1`. Example:
`2026-09-15 rnaseq_bulk paired: paired; user answer: "These samples are paired."`
This format locates a declaration; it does not authenticate the entry's author.
The JSON report and record expose provenance_warning when paired: paired lacks a
matching history entry; this warning does not refuse the project.

**Design-check record.** `01_samplesheets/<Assay ID>_design_check.json` contains each
executed validation check group, outcome (`pass`/`fail`) and findings, plus the declared
`unit_of_replication`, `reference_release`, and `paired` for RNA/ATAC (empty pairing means
undeclared). It is emitted only with the other outputs, after all write gates, and re-read
for full content equality at the exit gate (`exit_gate`, 0010). Check-only and refusals do
not write it. The later manifest row will consume it; this stage builds no manifest.

**Samplesheet.** `01_samplesheets/<Assay ID>_samplesheet.csv`. One row per included `files.csv`
row, with **columns determined by the assay**, because the samplesheet is the upstream pipeline's
contract and differs per pipeline. `python3 _system/stage01_samplesheet.py --list-formats` prints
the registered formats; all five assays are registered, each with its pipeline's own columns
and semantics (for the group-as-sample assays, `sample`/`group` carries the design's `group`
— decision 0035).

An assay with no registered format is **refused** (`unsupported_assay`). It never inherits another
assay's columns: `strandedness` is RNA-only, and a samplesheet carrying the wrong columns can
validate upstream while meaning something else entirely.

Paths are absolute **and inside the project** — they point at the symlinks in
`00_data/<Assay ID>/raw/`, never at the original sequencing run. Following the symlink would
bypass the project's own registration of its data; this is why 02.01 warns that moving a project
invalidates its samplesheet.

RNA `strandedness` must be explicitly declared in `_config/rnaseq_bulk.yaml`.
Missing file, missing key, or blank value → `strandedness_undeclared`; an unrecognised value
remains a `config` failure. Explicit `auto` remains accepted pending D-24. Multiple rows sharing a `sample` value are merged by nf-core as
technical replicates, which is the intended handling of multi-lane samples.

**Deep file-integrity verification.** Optional, **off by default**, and the reason this stage
offers it rather than stage 00: this is the first moment the *included* subset exists, and the
last cheap moment before hours of pipeline compute. Stage 00 already confirmed that every link
resolves and carries the gzip magic; what `--verify-integrity full` adds is decompressing each
included file, which is the only way to catch a truncated FASTQ.

It is off by default because FASTQs normally arrive already validated by a sequencing core.
**Ask the user**, quoting `included_gb` and `full_check_estimate_min` from `--check`. Record the
answer — the script writes `Deep file-integrity verification: full|none` into `HISTORY.md`, so a
project can always name the verification it received. Violation → `integrity`.

**Above ~10 GB it is scheduled work, not login-node work.** `--check` reports
`full_check_needs_scheduling`; when it is true, submit with `sbatch` rather than running inline.
Sub-stage 02.02 learned this the hard way — a pure-Python step SIGKILLed on a login node — and a
login node's per-user memory cgroup kills whatever is running, not whatever is at fault.

**Unsupported assay.** The assay has no registered samplesheet format. Adding one is a change to
`_system/stage01_samplesheet.py`'s `FORMATS` table — a row, not a rewrite — and belongs with the
work of adding that assay's wrapper. Violation → `unsupported_assay`.

**Registry integrity.** `files.csv` is machine-owned and derived from `00_data/<Assay ID>/raw/`.
Before anything else, the script compares the two: every file in `raw/` must be named in
`files.csv` and vice versa. Violation → `registry`.

This exists because two derived files agreeing with each other proves nothing when both are
damaged. A real project had `files.csv` accounting for 40 of 152 linked FASTQs; the design
validated cleanly against it and stage 01 reported 10 samples as the truth.

**A `registry` failure is never an exclusion.** Report the script's message verbatim — it names
the remedy — and **never offer to proceed with the reduced sample set**. Confirming a damaged
registry as if it were a deliberate choice is how a quarter-cohort analysis gets published.

The usual cause is not damage but a reasonable mistake: the user narrowed the cohort by editing
`files.csv` as well as `samples.csv`, because two files list samples and editing both looks
right. `files.csv` is now mode `0444`, so that edit is refused by the filesystem at the moment it
is attempted — but a project created before that, or an editor that forces the write, still
reaches here. Say plainly that subsetting is `samples.csv` only, and that re-running `finalize`
restores `files.csv` **without touching their design**.

**Malformed input.** Two failures mean the file itself is unusable rather than the design wrong:
`header` (a metadata CSV's columns are not the expected set) and `preconditions` (a metadata CSV
is missing, empty, or unreadable). Both mean stage 00's output was edited or damaged — direct the
user there rather than to `samples.csv`.

**Design table.** `01_samplesheets/<Assay ID>_design.csv`, header
`sample_id,condition,group,replicate` (plus optional `batch` and `subject` for RNA/ATAC). One row per included `sample_id`. Consumed by the
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
2. Resolve the project directory from the title. Read each assay config for the declarations
   above. For each undeclared RNA strandedness or RNA/ATAC replication unit or reference
   release, send T9 listing only missing keys and wait for the user's values. Write exactly
   their supplied values into the existing `_config/<Assay ID>.yaml` path (0019), adding
   missing top-level keys and preserving other settings. Never invent values or use
   `configure.py apply` to supply these: its stage-02 menus do not write them. If the user
   declares experimental pairing, record `paired: paired` (or explicit `unpaired`).
   Whenever the agent writes unit_of_replication, reference_release or paired, append
   a HISTORY.md entry quoting the user's answer verbatim and naming each key and value
   using the declaration-line format in Definitions, one key per line. This applies
   to T9 and unsolicited pairing declarations.
   Reference paths and the genome menu remain stage 02's responsibility. Then validate.
3. Run the validator, from the workspace root:

   ```bash
   python3 _system/stage01_samplesheet.py --project projects/<title> --check
   ```

   It needs no conda environment, decompresses nothing, and is fast. Parse its JSON; branch on its
   **exit code** per Definitions.
4. Exit 3 → reply T6 using its `error` field, and stop.
5. Exit 1 → reply T3, rendering every entry of every assay's `failures` array verbatim in the
   table. Write no outputs. For undeclared config values, return to step 2 and T9;
   for other failures, stop and await the user’s correction. Never repair design rows.
6. Exit 0 with `exclusions_pending: true` → reply T7 listing every assay's `exclusions`, and wait.
   Never proceed on a silent exclusion, and never infer that a missing row was an oversight.
   On `cancel`, stop.
7. Exit 0 with a non-empty `existing_outputs` → reply T5 listing them, and wait. On `cancel`, stop.
8. Reply T8 offering the optional deep integrity check, quoting `included_gb` and
   `full_check_estimate_min` from step 3, and wait. Ask even when the cohort is small; the answer
   is recorded, so it must be the user's. If they accept and `full_check_needs_scheduling` is
   true, submit the step-9 command with `sbatch` instead of running it inline.
9. Once every applicable gate is confirmed, run the writer with exactly the flags the user
   cleared — `--confirm-exclusions` only if step 6 happened, `--force` only if step 7 did, and
   `--verify-integrity full` only if step 8 was accepted:

   ```bash
   python3 _system/stage01_samplesheet.py --project projects/<title> --model "<model id>" [--confirm-exclusions] [--force]
   ```

   `--model` is the exact model id you are running as; it lands in the `history_entry` beside
   the template version. Omit it only if you cannot name your model — the script then records
   `unknown`.

10. Exit 2 → a gate you believed cleared was not. Reply T5 or T7 as its `blocked` array indicates
   and return to step 6. Never re-run adding a flag the user did not confirm.
11. Exit 1 at this point means the **exit gate** failed: the artifacts were written and then found
    wrong on re-read. Reply T3 with the `exit_gate` failures and stop. Do not repair them.
12. Exit 0 → reply T2 using each assay's `counts`.
13. Append the script's `history_entry` to the project's `HISTORY.md` **verbatim**, replacing
    `<ISO-8601 date>` with today's date. Do not restate its numbers in your own words — they are
    the script's counts, not your recollection.
14. Reply T4 using `wrote`, each assay's `counts`, and its `config_unfilled` — the scientific
    decisions still outstanding in `_config/<Assay ID>.yaml`. Stage 00 seeded that file, so the
    user is completing it, not authoring it. Offer to write values they give you; never choose
    one yourself.

## Response Format
Every message you send in this stage is one of the templates below, with placeholders filled.
Add nothing else: no observations, no suggestions, no offers, no commentary about the data or
about anything encountered on the filesystem.

One standing exception, from `_references/contract_standard.md` ("the bounded voice"): if the user asks a direct question, answer it from this workspace's own files — the contracts, `_references/`, and the current project's directory — read-only, in a short paragraph, then restate the pending wait point. Never let the answer become an action, a recommendation to deviate, or a reason to skip a step.

**T9 — Missing declarations**
```
Stage 01 needs your declarations in _config/<Assay ID>.yaml:
<missing keys, with allowed values: strandedness auto/forward/reverse/unstranded;
unit_of_replication sample/subject/cell_pseudobulk; reference_release nonblank release name>

Provide each listed value and I will write it to the project config, append a HISTORY.md
entry quoting your answer verbatim and naming each key and value, then validate.
```

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

Correct the named design or config declaration; tell me when ready and I will validate again.
```

**T4 — Stage complete**
```
Stage 01 complete. Samplesheets written to projects/<title>/01_samplesheets/.

| Assay | Samplesheet rows | Design rows | Files |
|---|---|---|---|
| <Assay ID> | <samplesheet_rows> | <design_rows> | <Assay ID>_samplesheet.csv, <Assay ID>_design.csv, <Assay ID>_design_check.json |

Before stage 02 runs, <n> decisions remain in _config/<Assay ID>.yaml: <config_unfilled, comma
separated>. Nothing is guessed — a wrong reference or contrast produces a confident wrong answer
rather than an error.

You do not have to look them up. When you start stage 02 I will offer the registered reference
genomes, and the contrasts your design table actually supports, as numbered choices — and show
you the finished file before anything runs.

Say when you are ready and I will start the bioinformatics for <Assay ID>.
```

**T4 note.** Name the `config_unfilled` keys and stop there. **Do not offer to take values in
free text, and do not explain what each key means** — stage 02 resolves them from menus built by
`_system/configure.py`, so a reference is chosen from the registry and a contrast from the levels
the design contains. Describing them here as things to look up sends the user to do work the next
stage does for them. If `config_unfilled` is empty, omit the paragraph entirely and simply say you
are ready to start stage 02 on their word.

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

**T8 — Deep integrity check offered**
```
Design validated. Before writing the samplesheet:

Optional deep file-integrity check — decompresses each of the <samples_included> included
sample(s) to catch a truncated or corrupt FASTQ. Stage 00 already confirmed every link resolves
and is a real gzip; this is the stronger check.

  Data to verify: <included_gb> GB
  Estimated time: ~<full_check_estimate_min> min<, submitted to Slurm if needs_scheduling>

Most FASTQs arrive already validated by the sequencing core, so this is off by default.

Reply `verify` to run it, or `skip` to trust the files.
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
| `<Assay ID>_samplesheet.csv` | Columns per the assay's registered format; one row per included sample-lane, absolute paths inside the project. Consumed by 02_bioinformatics. |
| `<Assay ID>_design.csv` | `sample_id,condition,group,replicate`, preserving optional RNA/ATAC `batch` and `subject`. One row per included sample. Consumed by the differential-expression sub-stage of 02_bioinformatics. |

| `<Assay ID>_design_check.json` | Executed checks and outcomes, declared replication unit, release and pairing; re-read at the exit gate. |

The `HISTORY.md` entry records the **template version this stage ran under** and
`Deep file-integrity verification: full|none`. The version is stamped per stage, not only at
project creation: a workspace is a git checkout, so `git pull` can move the contracts between a
project's stages, and this stamp is what makes that visible afterwards.

The agent appends the script's `history_entry` to `projects/<project_title>/HISTORY.md`.

`00_data/` is never modified by this stage. Re-running on unchanged inputs reproduces the output files
byte for byte.

## Human check
If you declined the deep integrity check, that is the assumption you carried forward: these files
are what the sequencing core produced and nobody has truncated them since. It is usually right,
and `HISTORY.md` records that you chose it.

Open `<Assay ID>_samplesheet.csv` and spot-check that the FASTQ paths in the first and last rows
resolve, and that the number of rows matches the sample-lane count you expect. Then open
`<Assay ID>_design.csv` and confirm the group sizes are the ones you intend to contrast — a
design with the wrong replicate counts runs to completion and answers the wrong question.

The script verifies structure; only you can verify intent.

Both files are yours to edit before stage 02 reads them.
