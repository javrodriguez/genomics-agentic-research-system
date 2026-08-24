# GARS architecture

How the system works as it stands at **v0.4.0**. This is a map: it explains how the pieces relate
and points at the file that owns each fact. Where it disagrees with a contract, the contract is
right — tell someone, do not patch around it.

Read this to re-orient. Read [decisions/](decisions/CONTEXT.md) to learn *why* any of it is the
way it is; every rule below names the decision that produced it, usually from a failure.

---

## The model in one paragraph

A **workspace** is a git checkout of this repository; you work in `gars/`. Inside it, numbered
folders are pipeline **stages**, each holding a `CONTEXT.md` **contract** — a prose specification
an LLM agent executes literally. The agent runs the dialogue and holds the gates; **deterministic
work is done by scripts in `_system/`**, not by the agent. Analysis is delegated to external
ClawBio **skills**, which are installed and read-only. State lives entirely in files: a project's
`HISTORY.md` says what happened, `STATUS` files say how far a run got, and `OUTPUTS.tsv` says what
each sub-stage produced.

---

## The pipeline

| Stage | Owns | Produces | Helper |
|---|---|---|---|
| `00_initialize_project` | registering raw data | `00_data/<assay>/` — symlinks, `files.csv`, `samples.csv`, and a seeded `_config/` | `stage00_register.py` |
| `01_prepare_samplesheets` | validating the design | `01_samplesheets/` — samplesheet + design table | `stage01_samplesheet.py` |
| `02_bioinformatics` | routing an assay to its sub-stages | `02_bioinformatics/<assay>/<NN_name>/` | `configure.py`, `resolve_artifact.py` |
| `03_custom_analysis` | **not implemented** — its contract replies and stops | nothing | — |

**Ownership is exclusive and encoded in the number.** A project directory named `NN_*` is written
by the stage named `NN_*` and by no other. `CONTEXT.md`, `HISTORY.md` and `_config/` carry no
prefix: they are project metadata, and `HISTORY.md` is the one file every stage appends to
([0001](decisions/0001-layered-context-and-stage-ownership.md)).

**Stage boundaries sit where a human must decide.** Stage 00 registers data; the user fills in the
experimental design; stage 01 validates it. Modelling that pause as a boundary rather than a wait
inside one stage is what makes progress legible from the directory tree
([0003](decisions/0003-data-model-files-and-samples-split.md)).

---

## The five rules that shape everything

Each was learned from a failure, and each is enforced by a mechanism rather than an instruction.

### 1. The contract orchestrates; code computes

Anything with one correct answer — deriving sample IDs, joining a samplesheet, reshaping a count
matrix, resolving an artifact — is a script in `_system/`. Contracts run them and branch on their
**exit codes**, and Scope Boundaries forbid the agent recomputing what a script computes.

This exists because positive instructions do not constrain an agent
([0002](decisions/0002-agent-control-negative-scope-and-templates.md)), and because an agent
emitting a 76-row CSV by hand is a transcription risk with no upside
([0011](decisions/0011-deterministic-artifacts-in-stages-00-01.md)).

The helpers are **stdlib only** and run on stock `python3` — stages 00 and 01 need no conda
environment at all. Only stage 02's skills do.

### 2. Machine-owned and user-owned files are different things

| File | Owner | Enforcement |
|---|---|---|
| `files.csv` | stage 00 | written mode `0444` — the filesystem refuses your edit |
| `samples.csv` | you | written once at creation, never overwritten |
| `_config/<assay>.yaml` | you | seeded with derivable values; decisions marked `<REQUIRED>` |

Narrowing a cohort is done by **deleting rows from `samples.csv` only**. Stage 01 reports the
dropped samples as exclusions and asks you to confirm; the raw data stays linked, so it is
reversible ([0003](decisions/0003-data-model-files-and-samples-split.md),
[0018](decisions/0018-machine-ownership-is-enforced-not-advised.md)).

### 3. Derived artifacts are verified against reality, never trusted

Two derived files agreeing with each other proves nothing when both are wrong. Stage 01 re-checks
`files.csv` against the actual symlinks in `raw/` before believing it. Every generated file is
written atomically, so a killed process leaves the previous complete file rather than a prefix
([0017](decisions/0017-machine-owned-files-are-verified-not-trusted.md)).

Exit gates check **content, not existence** — a file-exists check passes happily on a DE table
whose gene column was silently dropped
([0010](decisions/0010-skill-chaining-defects-and-adaptation.md)).

### 4. Choices come from closed menus; the system never guesses science

Assays, reference genomes and contrasts are all **selected from sets built by code**, never typed:

- the assay menu comes from `_references/assay_stage_skill_map.md`
- the genome menu from `_references/genomes.md`, where one row pairs FASTA + GTF + index cache so
  they cannot be mismatched
- the contrast menu from the levels **actually present** in the emitted design table, offered as
  ordered pairs because direction is itself a decision
  ([0020](decisions/0020-config-decisions-come-from-menus.md))

Menu numbers are **presentation-only** — regenerated per call, resolved in the same call, never
written to disk.

What the system will not do: choose a reference, a formula or a contrast for you. A wrong contrast
produces a confident wrong answer rather than an error, so a missing value stops the stage and
asks. Defaults are allowed only when **shown before they take effect**.

### 5. Heavy work is scheduled, not run on the login node

Anything O(data) — deep integrity verification, any pipeline — goes through `sbatch`. A login
node's per-user memory cgroup kills whatever is running rather than whatever is at fault
([0010](decisions/0010-skill-chaining-defects-and-adaptation.md),
[0013](decisions/0013-integrity-verification-moves-to-stage-01.md)).

---

## Where things live

| Path | Holds |
|---|---|
| `gars/CLAUDE.md` | L0 — orientation, always loaded |
| `gars/CONTEXT.md` | L1 — stage map, how stages connect, directory ownership |
| `gars/<stage>/CONTEXT.md` | L2 — the contract; the control surface of the whole system |
| `gars/_references/` | L3 — assay map, genome registry, artifact vocabulary, config schema, contract standard, runtime + lockfiles |
| `gars/_templates/` | the stamps stages copy: `project/` and `config/` |
| `gars/_system/` | `gars-env.sh` and the deterministic helpers |
| `gars/projects/` | L4 — the work; gitignored, so real data never enters git |

Every contract has the same **eight sections**, defined in
[`contract_standard.md`](../gars/_references/contract_standard.md): Purpose, Inputs, Scope
Boundaries, Definitions, Process, Response Format, OUTPUT, Human check. Three of them —
negatively-stated Scope Boundaries, fixed Response Format templates, and one concrete Human check —
exist because prose alone failed to constrain a real agent.

---

## How a run actually flows

```
you: "start a new project"
  00  menu of assays → you pick → project created from _templates/project/, _config/ seeded
      → inspect the data path (writes nothing) → you confirm the sample IDs → symlinks
      → finalize: files.csv + samples.csv, placeholders, exit gate
  ── you fill in condition/group/replicate; delete rows to exclude samples ──
  01  validate design, check files.csv against raw/, confirm exclusions
      → samplesheet + design table
  02  complete the config from menus (genome, contrast) → you confirm the file
      → route to sub-stages in order, each resolving its inputs by artifact type
      02.01 nf-core/rnaseq via sbatch → counts, BAMs, MultiQC
      02.02 adapt the matrix → differential expression
```

Each stage stamps the template version it ran under into `HISTORY.md`, so a `git pull` mid-analysis
is recorded rather than invisible ([0014](decisions/0014-workspace-upgrade-path.md), superseded in
its mechanism by [0016](decisions/0016-workspaces-are-checkouts.md) but not in this part).

---

## Constraints worth knowing before you change anything

- **Skills are never vendored.** They ship with the installed `clawbio` package and are read-only.
  GARS-authored wrappers would live in `_system/wrappers/`
  ([0012](decisions/0012-gars-authored-wrappers-live-in-system.md)).
- **Only one assay exists.** `rnaseq_bulk`. The four planned assays have their samplesheet columns
  registered as `planned` and are refused until a wrapper exists.
- **`03_custom_analysis` is a stub** and deliberately so — nothing has repeated enough to justify
  building it.
- **When you change how something works, grep for its *description*, not its identifier.** The
  mechanism and the prose describing it live in different files, and the prose does not break — it
  becomes a lie. This has caused several bugs in a single day.
