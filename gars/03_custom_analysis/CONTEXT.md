# Stage 03: Custom Analysis

## Purpose
Run a user-defined analysis on artifacts the earlier stages produced — the one stage whose
content is designed in dialogue rather than fixed by a contract. The control that makes this
safe is a **plan file**: the agent drafts `PLAN.md` as a reviewable document, a person approves
it, and only the approved plan executes. Intent gets a human gate exactly the way the design
table did in stage 01.

**The rails are not yours.** `_system/stage03_analysis.py` allocates the analysis directory,
enforces the approval gate, verifies the declared outputs and writes `OUTPUTS.tsv`, `STATUS`
and the history entry. Your judgment goes into the *content* of the plan and the scripts that
implement it — nowhere else. See `docs/decisions/0026-stage-03-is-plan-gated.md` in the GARS
repository for why.

## Inputs
- Working (this run): the project (`projects/<project_title>/`), the user's stated goal, and
  the artifacts resolvable through `_system/resolve_artifact.py` — never paths guessed or
  remembered.
- Reference (every run):
  - `_references/artifact_types.md` — the closed vocabulary the plan's Outputs table may use
  - `_system/stage03_analysis.py` — the rails: `create`, `approve`, `verify`
  - `_system/resolve_artifact.py` — how every input is found
  - `_system/gars-env.sh` — the execution environment (`gars-bio` unless the plan says otherwise)

## Scope Boundaries
The failure this stage is built around: an ungoverned agent, asked for "a quick look at the
data", improvising an analysis nobody reviewed and nobody can reproduce.

- Do **not** execute anything — no script, notebook, one-liner, or skill — before the user's
  own `stage03_analysis.py approve` has succeeded on the plan. Drafting is free; running is gated.
- Do **not** run `approve` yourself, ever. It is the user's command, run in their own terminal
  outside this session; the guard refuses it for an agent session, and its actor is whoever
  launched the process (R-073, R-093; decision 0059). Your part is to hand the user the exact
  command in T2 and wait.
- Do **not** resolve an input any way other than `resolve_artifact.py`. No globbing around
  `02_bioinformatics/`, no paths recalled from earlier turns.
- Do **not** write outside this analysis's own directory
  (`03_custom_analysis/<NN_slug>/`). Inputs are read-only; upstream artifacts are never
  modified, moved, or "fixed".
- Do **not** edit `PLAN.md` after approval. A change of mind is a new analysis — run `create`
  again; the superseded one keeps its record.
- Do **not** install anything (`pip`, `conda`, `mamba`). If the method needs a tool the
  environments lack, the plan is blocked on that fact: say so and stop.
- Do **not** re-run, repair, or substitute for a stage 02 sub-stage. If the needed artifact is
  missing, resolution fails and that is the report.
- Do **not** interpret results beyond what the plan's Goal asks. The templates report what was
  produced; the science of what it *means* is the user's.

## Definitions
**Analysis.** One directory `03_custom_analysis/<NN_slug>/`, holding `PLAN.md`, `scripts/`,
`results/`, and after completion `OUTPUTS.tsv` + `STATUS`. `NN` is allocated by `create`, in
order; a project accumulates analyses the way it accumulates history.

**Plan.** `PLAN.md`: Goal, Inputs, Method, Outputs, Execution. Drafted by you from the user's
words and the resolvable artifacts; it is the record of intent, and after approval it is
frozen. The skeleton's `<FILL: ...>` markers name what each section must contain — `approve`
refuses while any marker survives, so an empty plan cannot slip through on charm.

**Approved.** The user runs `approve` in their own terminal, and it passes its gates: no
skeleton markers, a non-empty Outputs table, every output type in the closed vocabulary, every
output path relative. It stamps `Status: APPROVED <date>` into `PLAN.md` and writes the approval
record `{actor, timestamp, plan_sha256, expiry, plan_path}` into the approval store, the
`.gars-approvals/` folder beside the workspace, outside it and out of your reach (decision
0059). The record lasts 24 hours from approval. `verify` and `submit` read only that record, so
a `Status: APPROVED` line, a `PLAN.md.approved` file in the workspace, a plan edited after
approval, or an expired record are never evidence of approval. Approval is durable for its
lifetime — it lives in the store, not in the conversation. Never read, write, copy or move
anything in the approval store.

**Execution venue.** The plan's Execution section opens with a `Runs:` line, and `approve`
refuses any value outside this vocabulary: `Runs: batch` — the workspace's configured
executor (`_config/executor.yaml`, decision 0039; Slurm on this cluster), the default for
**every** analysis, whatever its size — or `Runs: login-node (user-requested)`, allowed only
when the user explicitly asked for login-node execution in this analysis's dialogue. `sbatch`
is accepted as `batch`'s Slurm-era spelling and means exactly the same thing, so every plan
already written on the cluster still approves. Whether a job is
"small enough" for the login node is not a judgment this stage makes: the login node's cgroup
kills whatever is running when memory runs short, not whatever is at fault, and a wrong size
estimate is exactly the mistake a default cannot make (decision 0027).

**Complete.** `verify` exit 0: execution has written `run/.gars_run_complete` after success,
every declared output exists and is non-empty, `OUTPUTS.tsv`
and `STATUS` are written. An analysis whose outputs are missing is FAILED, whatever the
scripts' exit codes claimed.

## Process
1. Activated when the user asks for a custom or downstream analysis of an existing project.
   Identify the project; run
   `python3 _system/resolve_artifact.py --project projects/<title> --assay <Assay ID> --list`
   for the relevant assay. If nothing is resolvable — no completed sub-stage declares any
   artifact and stage 01 has emitted nothing — reply T1 and stop.
2. Run `python3 _system/stage03_analysis.py create --project projects/<title> --slug <slug>`,
   with a short kebab-case slug named after the goal.
3. Draft the plan: replace every `<FILL: ...>` marker in the created `PLAN.md`. Inputs come
   from step 1's resolution; Outputs use the closed vocabulary, preferring a specific type
   (`counts_gene`, `de_results`, …) over a generic one (`table`, `figure`, `report`) wherever
   one fits; Execution keeps its `Runs: batch` line unless the user explicitly asked for the
   login node. This is the step where your judgment belongs — spend it here, not at the
   keyboard later.
4. Reply T2 and stop. The user reads the plan, edits it if they wish, and answers.
5. If the user asks for changes, apply them to `PLAN.md` (it is still DRAFT), then reply T2
   again with what changed. If they decline the analysis, stop; the DRAFT directory remains as
   the record that it was considered.
6. The user approves by running the command T2 gave them, in their own terminal. If they
   report that it refused (exit 2), ask for its `blocked` reasons, reply T3 with them verbatim,
   fix the plan (that is a draft edit, allowed), and return to step 4. Never argue past the
   gate, and never run `approve` yourself.
7. Execute the approved plan literally: write the scripts it describes under `scripts/` and
   submit them through the executor door —
   `python3 <workspace>/_system/executorlib.py submit --workspace <project dir> <script>` —
   in the environment the plan names; a login-shell run happens only when the plan's `Runs:`
   line reads `login-node (user-requested)`. `submit` checks the approval record: if it
   refuses for approval (none, changed plan, or expired), reply T3 with its reason verbatim and
   stop; a new approval is the user's. On submission reply
   T4 and monitor the job. The execution script writes `run/.gars_run_complete` only after
   all its commands succeed. Steps not in the plan do not happen.
8. If execution fails, call `python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>`, reply T5 with the actual error,
   and stop. Do not patch around the failure and re-run: diagnosis goes to the user, and a
   changed method is a new plan.
9. On execution success, run
   `python3 _system/stage03_analysis.py verify --project projects/<title> --analysis <NN_slug> --model "<model id>"`.
   `--model` is the exact model id you are running as (decision 0024); omit only if you cannot
   name it. Exit 1 → declared outputs are missing or empty: reply
   T5, stop. Exit 2 → the plan has no valid approval record (never approved, edited since, or
   expired); treat as step 8's failure — something ran that should not have.
10. Exit 0 → append the returned `history_entry` to the project's `HISTORY.md` **verbatim**,
    replacing `<ISO-8601 date>` with today's date, and reply T6.

## Response Format
Every message you send in this stage is one of the templates below, with placeholders filled.
Add nothing else: no observations, no suggestions, no interpretation of results.

One standing exception, from `_references/contract_standard.md` ("the bounded voice"): if the
user asks a direct question, answer it from this workspace's own files — the contracts,
`_references/`, and the current project's directory — read-only, in a short paragraph, then
restate the pending wait point. Never let the answer become an action, a recommendation to
deviate, or a reason to skip a step.

**T1 — Nothing to analyse**
```
Stage 03 needs artifacts from the earlier stages, and none are resolvable in
projects/<project_title>/ yet:

<resolver problems / skipped sub-stages, verbatim>

Complete the stage named above first; its artifacts will then resolve here by type.
```

**T2 — Plan ready for review**
```
Analysis plan drafted: projects/<project_title>/03_custom_analysis/<NN_slug>/PLAN.md

Goal: <the Goal section's first sentence>
Inputs: <n> artifact(s) — <types, comma-separated>
Outputs: <n> declared — <types, comma-separated>
Execution: <login node | batch>, per the plan.

Read the plan file — Goal, Method, Outputs. Edit anything directly, or tell me the changes.
Nothing runs until you approve it. To approve it as written, run this in your own terminal,
outside this session, from the workspace root:

    python3 _system/stage03_analysis.py approve --project projects/<project_title> --analysis <NN_slug>

Then tell me it is done. The approval lasts 24 hours.
```

**T3 — Approval blocked**
```
The approval gate refused the plan:

<blocked reasons, verbatim>

I will fix the plan and show it to you again.
```

**T4 — Scheduled**
```
Analysis <NN_slug> submitted: job <jobid>, per the plan's Execution section.
I will report when it completes; STATUS in the analysis directory is the authority meanwhile.
```

**T5 — Failed**
```
Analysis <NN_slug> FAILED at <step>:

<the actual error, verbatim>

STATUS records the failure. The plan is unchanged; say how you want to proceed — a revised
method is a new plan for your review, not a silent retry.
```

**T6 — Complete**
```
Analysis <NN_slug> complete.

| Output | Type |
|---|---|
| <path> | <type> |

Recorded in OUTPUTS.tsv and HISTORY.md. The plan that produced this is frozen at
03_custom_analysis/<NN_slug>/PLAN.md.
```

## OUTPUT

| Artifact | Contents |
|---|---|
| `03_custom_analysis/<NN_slug>/PLAN.md` | the approved plan — goal, inputs, method, outputs, execution; the record of intent |
| `03_custom_analysis/<NN_slug>/scripts/` | every script the analysis ran, exactly as run |
| `03_custom_analysis/<NN_slug>/results/` | the outputs the plan declared |
| `03_custom_analysis/<NN_slug>/OUTPUTS.tsv` | declared artifacts by type, written by `verify` |
| `03_custom_analysis/<NN_slug>/STATUS` | `COMPLETE <iso8601>` or `FAILED <iso8601>` — the only authority |
| `HISTORY.md` entry | template version, model, plan reference, goal, outputs |

## Human check
Open `PLAN.md` before approving and read Goal, Method and Outputs. Approve it yourself, with the
command T2 gives you, and only if it is the
analysis you asked for, computed the way you would defend in a lab meeting — approval is the
moment your intent freezes, and everything after it is mechanical.
