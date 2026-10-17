---
date: 2026-10-16
status: standing
kind: decision
touches:
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/02_bioinformatics/CONTEXT.md
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
  - on a non-public project a stage 01-03 step tells the agent to Read a file the guard refuses, and the contract says nothing about what to do next
  - the agent appends to HISTORY.md on a non-public project and the guard refuses the Read the append needs
---
# Stage 01-03 contracts name a door or the user's message on a non-public project

Follow-up to [0107](0107-pg-nonpublic-projects-closed-to-reads.md) (item 11) and [0141](0141-row-13-closed-project-doors.md) (item 12), whose guard behaviour is unchanged.
Every ruling here is **the lane's** (gars-ms21, task G3 T44a), made under the owner's standing delegation; no sentence in this record is the owner's.

## Context

0107 closed non-public projects to reads: on such a project the guard refuses every Read of a file in it except `00_data/dataset.tsv` and the `STATUS` files, every write there, and every typed call; 0141 then opened the doors in `guard_hook.CLOSED_PROJECT_DOORS`, reached only through `_system/tool_call.py`, their output filtered.
Both records named the stage 01-03 contracts as a follow-up: they still told the agent to Read stage 01's config, design and samplesheet, to check stage 02's config and route on `OUTPUTS.tsv`, to resolve and draft stage 03's inputs and plan, and to append to `HISTORY.md` after a Read, with no word of what happens on a non-public project.
An agent following them hit a guard refusal mid-stage, and the contract gave it neither the door to use nor the message to send.

**Reproduction.** At public `main` `a97fa9cd`, the new `test_every_refused_read_names_a_door_or_the_users_message` checks 23 Process steps across the 13 contracts and finds all 23 silent.

## Decision

**Ruling 0291 (the lane's).**

1. Every stage 01-03 contract that has such a step gains a **Non-public project** paragraph in Definitions: how to tell (the dataset row's `data_class`, readable on any project), what the guard refuses, which doors the stage has and their dispatcher spelling, and that a step no door covers is the user's.
2. Each contract gains one **Non-public project** template (stage 01 and stage 02: T10; each sub-stage and stage 03: T7) that tells the user why the step cannot run, that nothing was read or written, and what to run themselves from the workspace root.
3. Each Process step that names a refused file, or `resolve_artifact`, names either its door's dispatcher spelling or that template: stage 02's precondition check and routing and stage 03's listing use the `resolve_artifact` door; the DE sub-stage's steps use `rnaseq_de.*` and `executor.*`; stage 01, stage 02's config menus, the nf-core and analysis-wrapper sub-stages after their STATUS read, stage 03 from `create` on, and every `HISTORY.md` append go to the template.
4. The DE door's output keeps no `history_entry`, so its template has the user re-run `collect` in their own terminal, which re-runs the exit gate on the finished run and prints the entry.
5. Prose only: no code, guard rule, registry entry or door changes.

In-spec choices (the lane's): the detector is lexical (a step naming an in-project file the guard refuses, or `resolve_artifact`) and is backed by a fixed list of the steps 0107 item 11 names, so a rewording cannot silently drop one; the doors' direct-spelling refusal while any non-public project exists, which reaches public projects too, is stated in the Definitions paragraphs; steps the detector does not reach (the nf-core wrappers' `check` to `collect`) are covered by stopping at step 2 rather than by a sentence each.

Rejected alternatives: a new contract section (the standard would require it in every contract); composing the DE history entry from the door's filtered fields (the contracts require the entry verbatim); widening the detector to every executor spelling (outside 0107 item 11's list; recorded below).

## What this does not close

- **R1** Outside the DE sub-stage, the executor steps still give the direct `executorlib.py submit` and `status` spellings, which the guard refuses for every project while any non-public project exists; the Definitions paragraphs say so, but those steps do not each name the `executor.*` door.
- **R2** The detector is lexical: a future step that reads a refused file without naming one of its listed names is caught only if it is one of 0107 item 11's listed steps.
- **R3** No live session has walked a non-public project through stages 01-03 under the guard; the prose is checked by the test, not by a run.

## Test

`gars/tests/test_closed_project_contracts.py` splits each of the 13 contracts' Process sections into numbered steps, selects every step that names an in-project file the guard refuses on a non-public project (`_config/`, `samples.csv`, `files.csv`, `01_samplesheets/`, the samplesheet and design, `OUTPUTS.tsv`, `HISTORY.md`, `PLAN.md`) or `resolve_artifact`, adds 0107 item 11's steps from a fixed list, and requires each to name `tool_call.py <door>` for a door in `CLOSED_PROJECT_DOORS` or the contract's `Non-public project` template.
It prints how many steps it checked, so a detector that sees nothing cannot pass; renaming stage 02's template heading turns it red with one silent step.
`tests/check_contracts.py`, `gars/tests/test_lifecycle_contracts.py` and `gars/tests/test_wrapper_contract.py` stay green.

## Status

Standing. The change record for the stage 01-03 contracts' non-public project prose.

## Date

2026-10-16
