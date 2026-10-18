---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/stage03_analysis.py
  - gars/_system/executorlib.py
  - gars/03_custom_analysis/CONTEXT.md
  - gars/tests/test_stage03_script_approval.py
  - gars/tests/test_stage03_execution.py
  - gars/tests/test_approval_forgery.py
  - gars/tests/test_render_methods.py
  - gars/tests/test_history_model.py
  - gars/tests/test_r164_keyed_lookups.py
  - gars/tests/test_venue_policy.py
  - gars/tests/fixtures/methods/approval.json
  - tests/run_tests.py
symptoms:
  - "R-073: scripts/<name> was not approved with the plan"
  - "R-073: scripts/<name> changed since the plan was approved"
  - "R-073: <name> is not under scripts/: a stage 03 script is written there and approved with the plan"
  - "the run is not the approved analysis" from stage 03 verify
---
# A stage 03 analysis's scripts are approved with its plan

Item S03-scripts of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner ("Show the scripts for approval too, and lock their fingerprints into the approval record the way the plan's already is"). Wording is the lane's (gars-t74), under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing. It extends 0042 (a plan edited after approval is a new analysis) to the scripts.

## Context

`approve` bound only `PLAN.md`; the contract had the agent write the scripts after approval (old step 7), so the user approved a method and never saw the code that ran it, and a script could be edited, or a new one written, between approval and submission. `executorlib submit` and `verify` checked the plan's approval and the run's own hashes, never that the script was the one the user saw.

**Reproduction.** At bd8a12b6, `gars/tests/test_stage03_script_approval.py` fails four tests (`FAILED (failures=3, errors=1)`): the approval record carries no `scripts` (`KeyError`); a script edited after approval, and one written after it, reach the backend (`_local_submit` called once); verify accepts the edited script's run (`0 != 2`).

## Decision

1. `approve` records `scripts`, the sha256 of every file under the analysis's `scripts/` (recursive), beside `plan_sha256` in the human-owned approval record, and lists them in its result.
2. Submit (`_analysis_approval`, the same gate as the plan's) refuses when any file under `scripts/` was added or changed since approval, and refuses a script outside `scripts/`; both before any launcher, record or backend call.
3. `verify`, after the execution evidence, refuses when a submitted script is not one the approval bound, byte for byte.
4. The stage 03 contract: step 3 writes the scripts with the plan, T2 shows them and says approval covers both, step 7 submits only approved scripts; a changed script is a new analysis.
5. Fixtures, no assertion changed: the tests that wrote scripts after approval now write them before it (test_stage03_execution's setUp and four of its tests through a `reapprove` helper, test_r164_keyed_lookups' analysis fixture through it, test_history_model, run_tests WorkspaceFixture test_12a), scripts outside `scripts/` moved under it (test_approval_forgery, test_render_methods, test_venue_policy), and the methods fixture's approval record gained the `scripts` key the producer now writes (test_render_methods compares the two shapes). test_stage03_execution.py was changed by Landing A; the overlap is named in the commit.

## What this does not close

- **Approvals written before 0306** carry no `scripts` key and bind no scripts: such an analysis submits and verifies as before until it is re-created. Records are written only by `approve` into the human-owned store, never by the agent. The bio-faults evaluation harness (frozen under `evals/`) drives verify with such historical records and stays green.
- **A script removed after approval** is not refused: it runs nothing.
- **Files outside `scripts/` that a script reads** (a helper module beside it, data) are not bound unless they live under `scripts/`.
- **S03-order** (the plan's ordered Scripts list and one job running them in order) is the next item; this one binds bytes, not order.

## Test

`gars/tests/test_stage03_script_approval.py` (5 tests): the record lists every script with its sha256; an edited and a late script refused before the backend; verify refuses a run of an edited script; the approved script runs and verifies.
Mutations: submit's drift check off `FAILED (failures=2)`; verify's script check off `FAILED (failures=1)`.

## Status

Standing.

## Date

2026-10-17
