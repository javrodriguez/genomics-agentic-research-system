# Stage 02: Bioinformatics

## Purpose
Run the standardized processing workflow for one assay by executing its sub-stages in the order
declared in `_references/assay_stage_skill_map.md`. This stage is a router: it resolves which
sub-stages apply, checks that each one's predecessor has completed, and hands control to that
sub-stage's own contract. It runs no analysis itself.

## Inputs
1. **Project title**
2. **Assay ID** — which assay to process
3. **`01_samplesheets/<Assay ID>_samplesheet.csv` and `_design.csv`** — written by stage 01
4. **`_config/<Assay ID>.yaml`** — reference genome and runtime settings

## Scope Boundaries
This stage performs the steps in Process and nothing else.

- Never invent, reorder, skip, or merge sub-stages. The Sub-stages column of
  `_references/assay_stage_skill_map.md` is the only source of what runs and in what order.
- Never run a sub-stage before its predecessor has reached status `COMPLETE`.
- Never modify anything under `00_data/` or `01_samplesheets/`. Stages 00 and 01 own them.
- Never edit, patch, or work around skill code. It belongs to the installed `clawbio` package
  and is read-only here. If a skill fails, report its error verbatim and stop.
- Never run an analysis step yourself. If a sub-stage's skill cannot run, say so and stop; do
  not substitute a hand-written command, another tool, or a manual workaround.
- Never launch a long-running job in the foreground. Submit it and return.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Scope Boundaries additions for the config

- **Never type a reference path or a contrast into the config yourself.** Both come from menus
  `configure.py` builds — the genome registry and the levels present in the design table. A path
  typed by hand can pair a FASTA with a mismatched annotation; a contrast typed by hand can name a
  level the design does not contain. Selection from a closed set makes both unreachable.
- **Never add a genome to `_references/genomes.md`** to satisfy a request. Registering a reference
  is a change to the workspace, verified separately; if the one the user wants is absent, say so
  and stop.
- **Never accept a contrast the script marks `testable: false`.** A level with one sample cannot
  be tested, and running anyway produces a result that looks like an answer.
- `de.formula` defaults to `~ condition`. It is a *presented* default: T9 shows it before anything
  is written. Change it only to a formula the user gave you.

## Definitions

**Sub-stage.** A directory `02_bioinformatics/<Assay ID>/<NN_name>/` in this workspace holding a
`CONTEXT.md` contract. The ordered list for an assay is the Sub-stages column of the assay map.

**Sub-stage output directory.** `projects/<project_title>/02_bioinformatics/<Assay ID>/<NN_name>/`.
Created by the sub-stage, owned by it, and never written to by any other sub-stage.

**STATUS file.** `<sub-stage output directory>/STATUS`, a single line, one of:
`SUBMITTED <job_id> <iso8601>`, `RUNNING <job_id> <iso8601>`, `COMPLETE <iso8601>`,
`FAILED <iso8601> <error_code>`. It is the only authority on a sub-stage's state — never infer
state from the presence of output files.

**Artifact.** A file a sub-stage produced, declared by type in its `OUTPUTS.tsv`. The closed
vocabulary, the `native`/`adapted` distinction and the resolution rule are defined in
`_references/artifact_types.md`, and implemented by `_system/resolve_artifact.py`. Sub-stages find
their inputs **by type, not by path**, so a change in where a producer writes does not break its
consumers.

`resolve_artifact.py` searches only sub-stages whose `STATUS` reads `COMPLETE`, in reverse
sub-stage order, and takes the first `native` match; `samplesheet` and `design` come from stage
01. A sub-stage whose own contract asks for an adaptation it produced passes
`--prefer-adapted-from <its own directory name>`. `--list` shows everything declared so far, which
is the quickest way to answer "what does this project have".

**Genome registry.** `_references/genomes.md`, one row per reference the workspace can align
against. A row pairs a FASTA, its matching GTF and, when built, the version-keyed index cache —
so choosing a genome sets all three together and they cannot be mismatched. Only verified
references are listed: the iGenomes `GRCh38` is the NCBI build with no `gene_biotype` and fails
*after* counts are written, which is the kind of thing the registry exists to keep out.

**Contrast menu.** Built from `01_samplesheets/<Assay ID>_design.csv` — the levels the user
actually wrote, not levels imagined. Every ordered pair is offered, because direction is a
decision: `condition,MT,WT` measures MT relative to WT, and reversing it reverses the sign of
every fold change. A pair whose levels do not both have at least 2 samples is marked
`testable: false` and is not a choice.

**Skill.** The executable implementation shipped by the installed `clawbio` package. GARS does
not vendor skill code: this workspace holds contracts only, and a sub-stage directory contains a
`CONTEXT.md`, never a `.py`.

`_system/gars-env.sh` resolves the skills directory at runtime and exports it as `$GARS_SKILLS`,
along with `$GARS_PY`, `PATH`, `JAVA_HOME` and the caches. Source it rather than hardcoding
anything — the literal site-packages path embeds a Python version that changes whenever the
environment is rebuilt.

```bash
source "$WS/_system/gars-env.sh"
cd "$GARS_SKILLS/nfcore-rnaseq-wrapper"    # skills run from inside their own directory
```

Each skill runs as a bare script from within its own directory, because it imports its siblings
by top-level name. Skill versions are therefore pinned by `clawbio` in
`_references/gars-bio.lock.txt`; upgrading `clawbio` changes the skills, which is a deliberate
and recorded act rather than an untracked edit.

## Process
1. Activated when the user asks to run bioinformatics, or names an assay to process. Reply T1.
2. Resolve the project and the Assay ID. If the project does not exist, or the Assay ID is not
   in the assay map, reply T5 and stop.
3. Check preconditions: `01_samplesheets/<Assay ID>_samplesheet.csv` and `_design.csv` exist and
   are non-empty. If not, reply T5 and stop — stage 01 has not run.
3a. **Complete the config before routing anything.** Stage 00 seeded
   `_config/<Assay ID>.yaml` with every derivable value filled and the scientific decisions marked
   `<REQUIRED>`. Resolve them by menu, never by asking the user to type a path or a level name:

   ```bash
   python3 _system/configure.py genomes
   python3 _system/configure.py contrasts --project projects/<title> --assay <Assay ID>
   ```

   Reply T8 rendering both. Wait. Then, with the numbers the user gave:

   ```bash
   python3 _system/configure.py apply --project projects/<title> --assay <Assay ID> \
       --genome <n> --contrast <n> [--formula "<theirs>"] --dry-run
   ```

   Reply T9 showing what it would write and **wait for confirmation**. On confirmation, re-run
   without `--dry-run`. Exit 1 → report its `error` and return to T8; never retry with a value the
   user did not choose.

   Skip 3a entirely when the config has no `<REQUIRED>` markers left — a completed config is not
   a question to re-ask.
4. Read the Sub-stages column for this assay from `_references/assay_stage_skill_map.md`.
5. Read each sub-stage's STATUS file, treating a missing file as `NOT_STARTED`. Reply T2 with
   the full sub-stage status table.
6. Identify the first sub-stage that is not `COMPLETE`. If every sub-stage is `COMPLETE`, reply
   T4 and stop.
7. If that sub-stage is `SUBMITTED` or `RUNNING`, reply T3 with how to check on it, and stop.
   Do not resubmit.
8. If that sub-stage is `FAILED`, reply T6 with its recorded error and stop. Resolving a failure
   is the user's decision, not an automatic retry.
9. If that sub-stage is `NOT_STARTED`, read its `Consumes` column from the assay map and resolve
   every listed type:

   ```bash
   python3 _system/resolve_artifact.py --project projects/<title> --assay <Assay ID> \
       --consumes <type> [<type> ...]
   ```

   Do not perform this search yourself — the reverse-order scan, the `native` preference and the
   STATUS gate are the script's, and reading `OUTPUTS.tsv` by eye is how a consumer silently picks
   a matrix reshaped for someone else's parser. Exit 1 → reply T7 naming its `missing` and
   `declared_but_absent` entries and stop. **Never dispatch a sub-stage whose inputs are absent,
   and never regenerate a missing artifact.**
10. Read `02_bioinformatics/<Assay ID>/<NN_name>/CONTEXT.md` and execute that contract. It owns
    everything from here, including its own response templates.

## Response Format
Every message you send in this stage is one of the templates below, with placeholders filled.
Add nothing else: no observations, no suggestions, no offers, no commentary about the data.
Once control passes to a sub-stage at step 9, that sub-stage's templates apply instead.

One standing exception, from `_references/contract_standard.md` ("the bounded voice"): if the user asks a direct question, answer it from this workspace's own files — the contracts, `_references/`, and the current project's directory — read-only, in a short paragraph, then restate the pending wait point. Never let the answer become an action, a recommendation to deviate, or a reason to skip a step.

**T1 — Start**
```
Starting stage 02: Bioinformatics.
Project: <title>
Assay: <Assay ID>
```

**T2 — Sub-stage status**
```
| # | Sub-stage | Skill | Status |
|---|---|---|---|
| <n> | <NN_name> | <skill> | NOT_STARTED / SUBMITTED / RUNNING / COMPLETE / FAILED |

Next: <NN_name>
```

**T3 — Already running**
```
<NN_name> is <SUBMITTED|RUNNING> as job <job_id> since <timestamp>. Nothing was resubmitted.

Check progress: squeue -j <job_id>
Re-run stage 02 when it finishes to continue.
```

**T4 — All sub-stages complete**
```
All sub-stages complete for <Assay ID>.

| Sub-stage | Output |
|---|---|
| <NN_name> | 02_bioinformatics/<Assay ID>/<NN_name>/ |

For anything beyond the pipeline — a custom figure, a signature score, an integration — ask
for a custom analysis: stage 03 drafts a plan for your approval and runs it against these
artifacts by type.

Say the word if you want another assay processed.
```

**T8 — Config decisions**
```
Before running <Assay ID>, <n> decisions in _config/<Assay ID>.yaml. Nothing is guessed: a wrong
reference or contrast produces a confident wrong answer rather than an error.

Reference genome — picking one sets the FASTA, the annotation and the prebuilt index cache
together, so they cannot be mismatched:

  01  GRCh38  Homo sapiens, Ensembl release 116   [indices cached: yes]

Contrast — the levels below are the ones actually in your design table:

  01  condition,MT,WT   MT relative to WT -- positive log2FC means higher in MT
  02  condition,WT,MT   WT relative to MT -- positive log2FC means higher in WT

Design formula: ~ condition  (the default; say so if you need something else, e.g.
"~ batch + condition" to control for a batch effect)

Reply with one genome number and one contrast number, e.g. `01, 02`.
```

Render the genome block from `configure.py genomes` and the contrast block from
`configure.py contrasts` — **both verbatim from their JSON**. Do not add a reference that is not
in the registry, and do not offer a contrast the design does not support. A contrast marked
`testable: false` is shown with the reason, never as a choice.

**T9 — Config to confirm**
```
This is what I will write to _config/<Assay ID>.yaml:

  reference: <genome id> (<species>, <source>)
    fasta:       <path>
    gtf:         <path>
    derived_dir: <path or "none — indices will be built, ~40 min and 43 GB">
  de.formula:  <formula>
  de.contrast: <spec>   — <meaning>

Nothing else in the file changes. Confirm to write it, or say what to change.
```

**T5 — Preconditions not met**
```
Cannot start stage 02.

| Requirement | Status |
|---|---|
| projects/<title>/ exists | Yes / No |
| <Assay ID> present in assay map | Yes / No |
| 01_samplesheets/<Assay ID>_samplesheet.csv exists | Yes / No |
| 01_samplesheets/<Assay ID>_design.csv exists | Yes / No |

Run 01_prepare_samplesheets first.
```

**T6 — Sub-stage failed**
```
<NN_name> failed at <timestamp> with <error_code>.

<verbatim error from the sub-stage log>

Nothing was retried and nothing was deleted. Resolve the cause, clear the sub-stage output
directory, and run stage 02 again.
```

**T7 — Required artifacts missing**
```
Cannot start <NN_name>: required artifacts are not available.

| Type | Status | Supplied by |
|---|---|---|
| <type> | missing / found | <sub-stage or -> |

Nothing was run and nothing was regenerated. Complete the sub-stage that produces the missing
type, then run stage 02 again.
```

## OUTPUT
Written to `projects/<project_title>/02_bioinformatics/<Assay ID>/`:

| Artifact | Contents |
|---|---|
| `<NN_name>/` | One directory per sub-stage, created and owned by that sub-stage. |
| `<NN_name>/STATUS` | The sub-stage's state. The only authority on whether it has completed. |
| `<NN_name>/OUTPUTS.tsv` | Artifacts the sub-stage produced: `type`, `role`, path relative to the sub-stage directory. How later sub-stages find their inputs. |

This stage writes no analysis output of its own. `00_data/` and `01_samplesheets/` are never
modified.

## Human check
Before dispatching the first sub-stage of an assay, read `_config/<Assay ID>.yaml` once and
confirm the reference build, the aligner, and — for a DE sub-stage — `de.formula` and
`de.contrast`. Nothing downstream can detect a wrong contrast: it produces a complete, confident,
wrong result. This is the only gate on it.

Between sub-stages, read the finished one's `OUTPUTS.tsv` and confirm the artifacts it lists are
the ones the next sub-stage should consume.
