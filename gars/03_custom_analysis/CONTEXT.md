# Stage 03: Custom Analysis

## Purpose
Run a user-designed analysis on artifacts produced by stage 02. **This stage is not
implemented.** The contract exists so that the routing in `CONTEXT.md` resolves to a real file
that stops cleanly, rather than to an empty directory an agent would improvise around.

Until it is written, this stage produces nothing.

## Inputs
- Working (this run): none — the stage does not run.
- Reference (every run): `_references/artifact_types.md`, for naming what a future analysis would
  consume.

## Scope Boundaries
The failure this section prevents is the specific one that motivated writing a stub at all: an
agent finding no contract, deciding the stage is "flexible", and inventing an analysis.

- Do **not** run any analysis, script, notebook, or skill under this stage.
- Do **not** create `projects/<project_title>/03_custom_analysis/` or anything inside it.
- Do **not** read stage 02 outputs, count matrices, DE tables, or QC reports in order to suggest
  what the analysis might be.
- Do **not** propose an analysis plan, offer to write one, or describe what this stage will do
  when implemented.
- Do **not** route the request to stage 02 or to a sub-stage as a substitute.

## Definitions
**Implemented.** A stage is implemented when this file contains a numbered Process that writes
artifacts, and `CONTEXT.md`'s stage map names its outputs. Neither is true today.

## Process
1. Activated when the user asks for a custom or downstream analysis. Reply T1 and stop.

## Response Format
Every message you send in this stage is T1, with placeholders filled. Add nothing else: no
observations, no suggestions, no offers of work.

**T1 — Not implemented**
```
Stage 03 (custom analysis) is not implemented in this template version.

Nothing was created and nothing was read.

What exists today:
  00_initialize_project    — create a project, register raw data
  01_prepare_samplesheets  — validate the design, emit samplesheets
  02_bioinformatics        — run an assay's sub-stages

Artifacts produced by stage 02 are recorded by type in each sub-stage's OUTPUTS.tsv, and are
yours to analyse directly outside this workspace.
```

## OUTPUT
None. This stage writes no files.

## Human check
Nothing to check — the stage produced nothing. If you needed it to do something, that is a
request to implement the stage, which is a change to this template rather than a run.
