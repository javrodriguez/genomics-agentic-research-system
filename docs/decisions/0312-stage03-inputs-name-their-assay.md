---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/stage03_analysis.py
  - gars/03_custom_analysis/CONTEXT.md
  - gars/tests/test_stage03_order.py
symptoms:
  - "input <type> names no assay; this project has more than one" from stage 03 approve
  - "the Inputs table has no Assay column" from stage 03 approve
  - "names assay <x>, which this project does not have" from stage 03 approve
  - stage 03 listed one assay's results in a multi-assay project
---
# Stage 03 lists every assay's results, and each input names its assay

Item S03-assay of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner. Wording is the lane's (gars-t74), under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing. It builds on 0306 and 0307 (the scripts are approved with the plan, in its order).

## Context

Stage 03's step 1 resolved artifacts "for the relevant assay", so in a project with two assays the agent listed one and the plan could be drafted without the other's results in view. The plan's Inputs table had no Assay column: an input resolved under one assay could not be told from the same type resolved under another, and nothing checked that a named assay existed.

**Reproduction.** At f264b78f, `gars/tests/test_stage03_order.py` `AssayInputTests` fails four of six (`FAILED (failures=4)`): in a two-assay project, an input naming no assay and an Inputs table with no Assay column are approved (`0 != 2`); an input naming an assay the project lacks is approved (`0 != 2`); the skeleton's Inputs header has no Assay column. The two controls (every input names its assay; a one-assay project's three-column table) are green.

## Decision

1. The PLAN.md skeleton's Inputs table is `| Artifact type | Assay | Resolved from | Path |`; Assay is the `--assay` the input resolved under.
2. `approve` refuses, with nothing written, an Inputs row naming no assay, or an Inputs table with no Assay column, in a project with more than one directory under `00_data/`; and in any project a row naming an assay that is not one of those directories.
3. A one-assay project may leave the assay implied (an empty cell or the old three-column table), so its plans approve as before.
4. The gate is `approve`'s alone, beside the Scripts gate; `verify` does not apply it, so an analysis approved before this change still verifies.
5. The stage 03 contract: step 1 resolves for every assay of the project; step 3 says each input names its assay; T2's Inputs line shows each input as assay: type.

## What this does not close

- **The assay a row names is not checked against the resolver.** A row may name an assay the project has while its path came from another; the resolver's per-assay listing is the agent's source, and the plan is the user's to read.
- **A plan with no Inputs rows** is not refused; the Outputs and Scripts gates are unchanged.

## Test

`gars/tests/test_stage03_order.py` `AssayInputTests` (6 tests): the three refusals and the skeleton and contract row, red at f264b78f, green at head; the two controls green throughout.
Mutation: approve skips the assay gate `FAILED (failures=4)`.

## Status

Standing.

## Date

2026-10-17
