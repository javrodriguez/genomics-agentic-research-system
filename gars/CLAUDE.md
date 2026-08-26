# Genomics Agentic Research System (GARS)

A workspace for running genomics research projects through dialogue with an LLM agent. The
filesystem is the architecture; the agent is the navigator. Built on the Interpretable Context
Methodology (ICM), with bioinformatics executed by ClawBio skills.

> **Scope of this file.** Orientation for *using* a GARS workspace. If you are developing GARS
> itself — editing contracts, docs or the template — the entry point is the `CLAUDE.md` at the
> root of the GARS source repository, not this one.

## Agent entry point

Before responding to any request: read `CONTEXT.md` for the stage map, then read the `CONTEXT.md`
of the stage the request maps to. Execute that contract literally.

- Its **Scope Boundaries** are binding. Do not read, search, or act outside them, however helpful
  the deviation would seem.
- Its **Response Format** templates are the only messages to send. Add no observations,
  suggestions, or offers of work. One exception: a direct user question may be answered from
  the workspace's own files, read-only, before restating the current wait point — the bounded
  voice rule in `_references/contract_standard.md`.
- If a step appears to need deviation, stop and ask. Never act first and report afterwards.

## Where things live

| Path | Holds | Layer |
|---|---|---|
| `CONTEXT.md` | stage map, how stages connect, directory ownership | L1 |
| `00_initialize_project/` … `03_custom_analysis/` | one contract per stage; the numbering is the order | L2 |
| `02_bioinformatics/<Assay ID>/<NN_name>/` | one contract per sub-stage of an assay | L2 |
| `_references/` | domain knowledge shared by every project — assay map, artifact vocabulary, config schema, runtime | L3 |
| `_templates/` | the stamps stages copy; `project/` is the shape of a new project | L3 |
| `_system/` | `gars-env.sh` (the execution environment), the stage helpers that compute deterministic artifacts, the index builder | L3 |
| `projects/` | the work: one directory per project, plus a generated `_index.md` | L4 |

Skills are **not vendored**. They ship with the installed `clawbio` package and are read-only; a
sub-stage directory holds a `CONTEXT.md`, never a `.py`. `_system/gars-env.sh` resolves them at
runtime as `$GARS_SKILLS`.

**Derived artifacts are computed by code, not written by you.** Samplesheets, design tables, the
project index and artifact resolution come from `_system/` scripts. A contract that names one is
telling you to run it and report what it returns — not to reproduce its work. The stage 00/01
helpers and the resolver need no conda environment; stage 02's skills do.

## Using this workspace

1. Clone the GARS repository; **this folder, `gars/`, is your workspace** — work here directly.
   `git pull` before starting a project to pick up fixes; `git checkout <tag>` to pin a release.
2. Tell the agent you want to start a new project → stage 00 creates `projects/<title>/` from
   `_templates/project/`, symlinks your raw data, and writes `files.csv` + `samples.csv` per assay.
3. **Fill in `00_data/<Assay ID>/samples.csv`** — one row per sample, so each experimental value
   is entered once. To analyse a subset, delete the other rows: stage 01 treats a sample with no
   row as excluded and leaves its raw data in place, so the choice is reversible.
4. `_config/` is already seeded — stage 00 filled every derivable value and marked the
   scientific decisions `<REQUIRED>`. Stage 02 completes those from menus (genome; contrast
   and formula, or peak type, per assay) and asks you to confirm before writing. Schema and rationale:
   `_references/config_schema.md`.
5. Run stages 01 → 02 → 03 in order, reading the output between each.

## State

There is no status file for the workspace. State is the filesystem:

| Question | Answered by |
|---|---|
| What projects exist, how far did each get? | `projects/_index.md` (generated — rebuild with `bash _system/build_projects_index.sh`) |
| Is a design complete? | `00_data/<Assay ID>/samples.csv` |
| Has a sub-stage run? | `02_bioinformatics/<Assay ID>/<NN_name>/STATUS` — the only authority |
| What did it produce? | that sub-stage's `OUTPUTS.tsv` |
| What happened, and when? | the project's `HISTORY.md` |
