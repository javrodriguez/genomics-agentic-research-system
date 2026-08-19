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

Next: 03_custom_analysis, or run stage 02 for another assay.
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
