---
date: 2026-10-18
status: standing
kind: decision
touches:
  - gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md
  - gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
  - gars/02_bioinformatics/scrnaseq/01_nfcore-scrnaseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md
  - gars/02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md
  - gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md
  - gars/03_custom_analysis/CONTEXT.md
  - gars/tests/test_closed_project_contracts.py
symptoms:
  - "Blocked: executor.submit is a door reached only through the dispatcher while a non-public project exists" on a public project's step 5
  - "Blocked: executor.status is a door reached only through the dispatcher while a non-public project exists" on a public project's status step
  - a public project's sub-stage stops at its submit step in a workspace that also holds a non-public project, and the contract names no way on
---
# Executor steps name the executor door while any project is non-public

Closes [0291](0291-stage-01-03-contracts-name-a-door-or-the-user-on-a-non-public-project.md)'s R1. The guard rule it follows is [0141](0141-row-13-closed-project-doors.md)'s ruling D-vii b, unchanged.
Rulings are glitch-b5's (lane gars-ms21b, task T44b, round 2), made under the owner's standing delegation; no sentence in this record is the owner's.

## Context

While any non-public project exists in a workspace, the guard refuses a door's direct spelling for every project, public ones included (0141 D-vii b), and `executor.submit` and `executor.status` are doors.
0291 said so in each contract's Definitions, but outside the DE sub-stage the executor steps still gave only `python3 <workspace>/_system/executorlib.py submit` and `status`.
So a public project's sub-stage, followed in a workspace that also holds a non-public project, was refused at its submit step, and the contract gave the agent no way on; the user saw a refusal the template does not explain.

**Reproduction.** On the lane's base (f047180c), a guard probe through `pilot_fixture` in a workspace with a closed project: the direct `executorlib.py submit` and `status` spellings for the public project exit 2 (`Blocked: executor.submit is a door reached only through the dispatcher while a non-public project exists, because only the dispatcher filters its output`); the same spellings exit 0 in a workspace with none; the `tool_call.py executor.submit` and `executor.status` spellings exit 0 in both. At the red commit the new contract test printed `door steps: 32 checked, 30 without the dispatcher spelling`: 27 steps in 10 contracts gave no dispatcher spelling, and the DE sub-stage's steps 3, 6 and 7 gave it only "On a non-public project".

## Decision

1. Each Process step that spells an executor door directly gains, beside the direct spelling, the door's dispatcher spelling in the DE sub-stage's shape (ruling Q2): "While any non-public project exists in the workspace, the direct submit call is refused (decision 0141): `python3 _system/tool_call.py executor.submit '{"workspace": "<project dir>", "script": "<sub-stage dir>/submit.sh"}'`; `job_id` is in the JSON of its `stdout`", and the same for `executor.status` with `"job-id": "<job_id>"`. Stage 03's submit names `<script>` as its step 7 does. The direct spelling stays the first one, so nothing changes on a workspace with only public projects.
2. The steps: the seven nf-core wrappers' step 5 (submit) and step 7 (status), scrnaseq's and spatialvi's also step 6; the two analysis-wrapper sub-stages' step 5 (submit) and steps 6, 7, 8 (status); stage 03's steps 7 (submit) and 8 (status).
3. The DE sub-stage's dispatcher lines (steps 3, 6, 7, 8) read "On a non-public project, or while any exists in the workspace", as its Definitions already said; step 8 spells its `executor.status` call instead of "as in step 7".
4. Each touched contract's Non-public project paragraph says which steps give the `executor.*` dispatcher spelling and why, and that on a public project its output is unfiltered.
5. Prose and a contract test only: no code, guard rule, registry entry or door changes.

Rejected (ruling Q2): the dispatcher spelling alone everywhere. It would change what the agent parses on every public project in every workspace (the JSON moves inside `stdout`) to serve the mixed-workspace case.

## What this does not close

- **R1** Response Format lines that tell the user to check progress with `executorlib.py status` keep the direct spelling: they are for the user's own terminal, which the guard does not see.
- **R2** The detector is lexical: a door spelled other than by its script basename and verb (for example through a shell variable) is not seen; the pinned set of 32 step-door pairs catches a detector that goes blind on today's steps, not a new spelling.
- **R3** No live session has walked a mixed workspace (one public and one non-public project) through a sub-stage under the guard; 0291's R3 holds.
- **R4** The wrapper verbs (`check`, `prepare`, `collect`) of the nf-core and analysis-wrapper sub-stages are not doors; on a public project in a mixed workspace their direct spellings name only that project and are not refused by D-vii b (the same probe: `nfcore_rnaseq_wrapper.py check` and `scrna_qc_cluster.py prepare` on the public project exit 0), so they keep one spelling.

## Test

`gars/tests/test_closed_project_contracts.py`, `test_every_door_step_names_its_dispatcher_spelling`: for every Process step of every contract under `gars/` and every door in `guard_hook.CLOSED_PROJECT_DOORS`, a step that spells the door's registry argv directly (script basename and verb, either wrapped; a verbless script only when an option follows) must also give `tool_call.py <door>` with a JSON literal whose keys the door's `input_schema` admits and which holds its `required` keys, and must state the workspace-wide condition. It prints `door steps: <n> checked, <m> without the dispatcher spelling` and pins the checked set to the 32 pairs of the plan's sweep. Red at debb4899 (32 checked, 30 without); green after the prose (32 checked, 0 without).
`test_the_door_step_mutants_turn_the_detector_red` applies four mutants in memory, each red: scrna-qc-cluster's status dispatcher lines deleted (3 without), `executor.submit` misspelled in the DE step 6 (no dispatcher spelling), `job_id` for `job-id` in stage 03 step 8 (keys outside the schema), `script` dropped from an nf-core submit (required keys missing).
Two detector mutants were run by hand on a scratch copy of the module, each red: the door list emptied (0 checked, the pinned set fails) and the step splitter reading only a step's first line (19 checked, 19 without).

## Status

Standing. The change record for T44b; implementation only, its approval is glitch-b5's at landing.

## Date

2026-10-18
