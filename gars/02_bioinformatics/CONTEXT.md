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
- Never edit, patch, or work around skill code — neither the installed `clawbio` skills nor
  the GARS wrappers under `_system/wrappers/` (template code, updated only by `git pull`). If
  a skill fails, report its error verbatim and stop.
- Never run an analysis step yourself. If a sub-stage's skill cannot run, say so and stop; do
  not substitute a hand-written command, another tool, or a manual workaround.
- Never launch a long-running job in the foreground. Submit it and return.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Scope Boundaries additions for the config

- **Never type a reference path or a contrast into the config yourself.** Both come from menus
  `configure.py` builds — the genome registry and the levels present in the design table. A path
  typed by hand can pair a FASTA with a mismatched annotation; a contrast typed by hand can name a
  level the design does not contain. Selection from a closed set makes both unreachable.
- **Never edit `compute.mem` yourself to make a venue accept a run.** Step 3b's
  `configure.py lower` fits it to the venue's own table and can only lower it; a run the venue
  still refuses needs another venue, not a smaller number typed in (decision 0293).
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
`SUBMITTED <job_id> <iso8601>`, `RUNNING <job_id> <iso8601>`,
`VALIDATING <iso8601>`, `ARTIFACT_MISSING <iso8601>`, `STALE <iso8601>`,
`COMPLETE <iso8601>`, `FAILED:<reason> <iso8601>` or `CANCELLED <iso8601>` (the closed enum is in
`wrapperlib.write_status()`, spec §15). Only code writes this file; use the typed
`python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>`
call to refresh scheduler state. It is the only authority on a sub-stage's state — never infer
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
against. A row pairs a FASTA, its matching GTF, the derived-cache root (keyed per assay to that
assay's pinned pipeline version), and the genome-derived facts an assay needs — mitochondrial
contig name, MACS effective genome size — so choosing a genome sets all of them together and
they cannot be mismatched. Only verified
references are listed: the iGenomes `GRCh38` is the NCBI build with no `gene_biotype` and fails
*after* counts are written, which is the kind of thing the registry exists to keep out.

**Contrast menu.** Built from `01_samplesheets/<Assay ID>_design.csv` — the levels the user
actually wrote, not levels imagined. Every ordered pair is offered, because direction is a
decision: `condition,MT,WT` measures MT relative to WT, and reversing it reverses the sign of
every fold change. A pair whose levels do not both have at least 2 samples is marked
`testable: false` and is not a choice.

**Skill.** The executable implementation a sub-stage invokes. Every sub-stage's Source in
the assay map is `gars` (decisions 0012, 0029): wrappers are versioned in this workspace under
`_system/wrappers/`, resolve via `$GARS_WRAPPERS`, and run from anywhere on stock python. A
sub-stage directory contains a `CONTEXT.md`, never a `.py` — the wrapper code lives in
`_system/`, not in the contract tree. A gars wrapper is versioned with the template, so its
version IS the template version.

`_system/gars-env.sh` provides the execution environment — `$GARS_PY`, `PATH`, `JAVA_HOME`
and the caches. Source it rather than hardcoding anything — the literal site-packages path
embeds a Python version that changes whenever the environment is rebuilt.

```bash
source "$WS/_system/gars-env.sh"
python3 _system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py ...   # wrappers run from anywhere
```

**Venue preflight (0100, R-062/R-064).** Both executor submit paths read
`00_data/dataset.tsv` and the executed descriptor before reservation or launcher
creation. `dataset_unclassified` refuses an absent or unreadable row;
`class_not_permitted` refuses identifiable data; `dataset_expired` refuses an
expired or malformed expiry and an agreement dataset with no expiry.
`venue_not_permitted` reports every violated route, purpose, local memory or
FASTQ rule. Local permits exactly public/fixture FASTQ inputs, at most 8 GiB
of declared memory, and no declaration only for public/fixture.
`resource_undeclared` names other absent local memory declarations;
`resource_unparseable` names an invalid K/M/G/T declaration; `input_missing`
names an unreadable policy input or a missing listed input. The FASTQ rule
reads fastq_1/fastq_2; analysis inputs are artifacts. A memory refusal names
the value the venue accepts; on this stage it is fixed by step 3b's
`configure.py lower`, never by a hand edit of `compute.mem` (decision 0293).
`venue_too_small` names a dataset whose summed inputs exceed the venue's byte
budget: it needs a bigger venue (no venue has a budget until its host size is
measured). The machine-owned
homelab marker changes the local descriptor's venue without adding a backend.
Group 11 records the prepare-time venue; submission records the executed venue.
Login-node analysis records executor local and the pre-swap descriptor's venue.
Report every refusal and stop; no override is available.

**Non-public project (decisions 0107, 0141).** A project is non-public unless every data row of
its `00_data/dataset.tsv` reads exactly `public` in `data_class`; an absent or unreadable row
counts as non-public, and the session's catch-up prints the label. On a non-public project the
guard refuses every Read of a file in it except that dataset row and the `STATUS` files, every
write or append there (`HISTORY.md` included), and every typed call that names the project except the doors in
`CLOSED_PROJECT_DOORS` (`_system/guard_hook.py`): here `resolve_artifact`, and in the sub-stages
`rnaseq_de.*` and `executor.*`. A door runs only as `python3 _system/tool_call.py <door> '<json>'`
from the workspace root, its output filtered to a keep-list; while any non-public project exists
in the workspace, a door's direct spelling (`python3 _system/resolve_artifact.py ...`) is refused
for every project, public ones included. A step no door covers is the user's on a non-public
project: reply T10 and stop; step 3a first asks with T11 whether the user has completed the
config. Never work around a refusal.

## Process
1. Activated when the user asks to run bioinformatics, or names an assay to process. Reply T1.
2. Resolve the project and the Assay ID. If the project does not exist, or the Assay ID is not
   in the assay map, reply T5 and stop.
3. Check preconditions: `01_samplesheets/<Assay ID>_samplesheet.csv` and `_design.csv` exist and
   are non-empty. If not, reply T5 and stop — stage 01 has not run.
   On a non-public project these files are refused to a Read; check them through the door instead:
   `python3 _system/tool_call.py resolve_artifact '{"project": "projects/<title>", "assay":
   "<Assay ID>", "consumes": ["samplesheet", "design"]}'`, and `ok: false` → T5.
3a. **Complete the config before routing anything.** Stage 00 seeded
   `_config/<Assay ID>.yaml` with every derivable value filled and the scientific decisions marked
   `<REQUIRED>`. Resolve them by menu, never by asking the user to type a path or a level name:

   The decisions are per-assay (`ASSAY_DECISIONS` in `_system/configure.py`): every assay
   chooses a genome; an assay with a `de` block additionally chooses a contrast (and may give a
   formula); an assay with a `peaks` block chooses a peak type.

   ```bash
   python3 _system/configure.py genomes --assay <Assay ID>
   python3 _system/configure.py contrasts --project projects/<title> --assay <Assay ID>   # de assays
   python3 _system/configure.py peaks                                                     # peaks assays
   ```

   Reply T8 rendering the genome menu plus this assay's decision menu. Wait. Then, with the
   numbers the user gave:

   ```bash
   python3 _system/configure.py apply --project projects/<title> --assay <Assay ID> \
       --genome <n> [--contrast <n>] [--formula "<theirs>"] [--peaks-type <n>] --dry-run
   ```

   Reply T9 showing what it would write and **wait for confirmation**. On confirmation, re-run
   without `--dry-run`. Exit 1 → report its `error` and return to T8; never retry with a value the
   user did not choose.

   Skip 3a entirely when the config has no `<REQUIRED>` markers left — a completed config is not
   a question to re-ask.
   On a non-public project the config is refused to a Read, so the skip rule cannot be tested,
   and neither the menus nor `apply` is a door. Reply T11 and wait. Yes (or the user saying the
   config is done after T10) → continue to step 3b and then step 4: the sub-stage's own `check` still refuses a
   config left unfilled with `config_unfilled`, in the user's terminal or through the
   `rnaseq_de.check` door, whose output keeps `failures`. No → reply T10 naming this step, and
   stop.
3b. **Fit the memory request to the venue** (decision 0293), whether or not 3a ran, and after
   3a's write when it ran: a separate question, never merged into T9. `compute.mem` is
   infrastructure; this step changes nothing else and decides no science.

   ```bash
   python3 _system/configure.py lower --project projects/<title> --assay <Assay ID> --dry-run
   ```

   `lowered: null` (the venue has no ceiling, or the request is within it) → continue to step 4
   silently. A `lowered` object → Reply T12 and **wait**. On confirmation re-run without
   `--dry-run`, append its `history_entry` to `HISTORY.md` verbatim (with `<ISO-8601 date>`
   replaced by today's date), and continue to step 4. Declined → stop: nothing was written, and
   the submit will refuse this request on this venue. Exit 1 with `needs_venue` → report its
   `error` and `needs_venue` verbatim and stop: this venue refuses the run whatever its memory.
   Any other non-zero exit → report its `error` and stop. Never edit `compute.mem` by hand
   instead.
   On a non-public project neither the config nor `_config/executor.yaml` can be read, and
   `lower` is not a door. Reply T13 and wait. Yes → continue to step 4. No → reply T10 naming
   this step and its one command, and stop.
4. Read the Sub-stages column for this assay from `_references/assay_stage_skill_map.md`.
5. Read each sub-stage's STATUS file, treating a missing file as `NOT_STARTED`. Reply T2 with
   the full sub-stage status table, including VALIDATING, ARTIFACT_MISSING and STALE.
   STATUS files stay readable on a non-public project.
6. Identify the first sub-stage that is not `COMPLETE`. If every sub-stage is `COMPLETE`, reply
   T4 and stop. VALIDATING, ARTIFACT_MISSING and STALE continue to step 10,
   where the sub-stage contract runs its collect step and reports its gate result.
7. If that sub-stage is `SUBMITTED` or `RUNNING`, reply T3 with how to check on it, and stop.
   Do not resubmit. After polling, VALIDATING, ARTIFACT_MISSING and STALE go to step 10.
8. If that sub-stage is `FAILED:<reason>` or `CANCELLED`, reply T6 with its recorded error and stop. Resolving a failure
   or cancellation is the user's decision, not an automatic retry. VALIDATING,
   ARTIFACT_MISSING and STALE instead go to step 10.
9. If that sub-stage is `NOT_STARTED`, read its `Consumes` column from the assay map and resolve
   every listed type; VALIDATING, ARTIFACT_MISSING and STALE bypass this initial-input
   routing and go to step 10's collect hand-off:

   ```bash
   python3 _system/resolve_artifact.py --project projects/<title> --assay <Assay ID> \
       --consumes <type> [<type> ...]
   ```

   Do not perform this search yourself — the reverse-order scan, the `native` preference and the
   STATUS gate are the script's, and reading `OUTPUTS.tsv` by eye is how a consumer silently picks
   a matrix reshaped for someone else's parser. Exit 1 → reply T7 naming its `missing` and
   `declared_but_absent` entries and stop. **Never dispatch a sub-stage whose inputs are absent,
   and never regenerate a missing artifact.**
   On a non-public project, or while any exists in the workspace, use the door's dispatcher
   spelling instead: `python3 _system/tool_call.py resolve_artifact '{"project":
   "projects/<title>", "assay": "<Assay ID>", "consumes": ["<type>", ...]}'`; its output keeps
   only `ok`, `missing` and `resolved`, so name the `missing` entries in T7.
10. Read `02_bioinformatics/<Assay ID>/<NN_name>/CONTEXT.md` and execute that contract. It owns
    everything from here, including its own response templates.

## Response Format
Every message you send in this stage is one of the templates below, with placeholders filled.
Add nothing else: no observations, no suggestions, no offers, no commentary about the data.
Once control passes to a sub-stage at step 10, that sub-stage's templates apply instead.

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
| <n> | <NN_name> | <skill> | NOT_STARTED / SUBMITTED / RUNNING / VALIDATING / ARTIFACT_MISSING / STALE / COMPLETE / FAILED:<reason> / CANCELLED |

Next: <NN_name>; VALIDATING / ARTIFACT_MISSING / STALE → step 10 and its collect step.
```

**T3 — Already running**
```
<NN_name> is <SUBMITTED|RUNNING> as job <job_id> since <timestamp>. Nothing was resubmitted.

Check progress: squeue -j <job_id>
After polling, VALIDATING / ARTIFACT_MISSING / STALE → step 10 and the sub-stage's collect step.
FAILED:<reason> / CANCELLED → the user's decision (T6).
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

<the assay's second decision menu>

Reply with one genome number and one number from the second menu, e.g. `01, 02`.
```

Render the genome block from `configure.py genomes --assay <Assay ID>` and the second block
from this assay's decision menu — `contrasts` for a de assay (every ordered level pair with
its meaning, plus the formula default), `peaks` for a peaks assay (narrow | broad with their
meanings) — **all verbatim from their JSON**. Do not add a reference that is not in the
registry, and do not offer a contrast the design does not support. A contrast marked
`testable: false` is shown with the reason, never as a choice.

**T9 — Config to confirm**
```
This is what I will write to _config/<Assay ID>.yaml:

  reference: <genome id> (<species>, <source>)
    fasta:       <path>
    gtf:         <path>
    derived_dir: <path or "none — indices will be built, ~40 min and 43 GB">
  <this assay's decision lines: de.formula + de.contrast, or peaks.type — with meanings,
   and for a peaks assay the genome-derived macs_gsize and mito_name being set with it>

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

**T6 — Sub-stage failed or cancelled**
```
<NN_name> is <FAILED:<reason>|CANCELLED> at <timestamp> with <error_code>.

<verbatim error from the sub-stage log>

Nothing was retried or deleted. Decide how to resolve the cause; corrected inputs need
prepare again before another submission.
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

**T10 — Non-public project**
```
<title> is a non-public project (data_class <label>), so I cannot complete
_config/<Assay ID>.yaml for it: the configure.py commands read files the guard keeps out of a
hosted-model prompt (decision 0107), and no door covers them. Nothing was read or written.

That step is yours. From the workspace root, run the commands that step names.

For step 3a, run the menus and choose from them:

  python3 _system/configure.py genomes --assay <Assay ID>
  <this assay's decision menu: configure.py contrasts --project projects/<title> --assay <Assay ID> | configure.py peaks>
  python3 _system/configure.py apply --project projects/<title> --assay <Assay ID> --genome <n> [--contrast <n>] [--formula "<yours>"] [--peaks-type <n>]

For step 3b, run only this; it lowers compute.mem to what this venue accepts, or changes
nothing, and if it prints a history_entry, append that to HISTORY.md:

  python3 _system/configure.py lower --project projects/<title> --assay <Assay ID>

Tell me when that step is done; I then continue to the sub-stage table, which reads only the
STATUS files.
```

**T11 — Non-public config**
```
<title> is a non-public project (data_class <label>), so I cannot read _config/<Assay ID>.yaml
to see whether its decisions are made (decision 0107). If it is not complete, the sub-stage's
own check refuses it.

Have you completed _config/<Assay ID>.yaml with the configure.py menus and apply in your own terminal?
```

**T12 — Memory to lower**
```
This venue (<venue>) accepts at most <accepts_up_to> of memory per job, and
_config/<Assay ID>.yaml asks for <from>. I will change one line:

  compute.mem: <from>  ->  <to>

Nothing else in the file changes, and no scientific setting is touched. Confirm to write it,
or say no and I stop here: the submit refuses a request above <accepts_up_to> on this venue.
```

**T13 — Non-public memory request**
```
<title> is a non-public project (data_class <label>), so I cannot read _config/<Assay ID>.yaml
or _config/executor.yaml to see whether this venue accepts its memory request (decision 0107).
The command below lowers compute.mem to what this venue accepts, or changes nothing; it never
raises it and touches nothing else. If it prints a history_entry, append that to HISTORY.md.

Have you run python3 _system/configure.py lower --project projects/<title> --assay <Assay ID> in your own terminal?
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
