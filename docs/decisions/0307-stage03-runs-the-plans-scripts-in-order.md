---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/stage03_analysis.py
  - gars/_system/executorlib.py
  - gars/03_custom_analysis/CONTEXT.md
  - gars/tests/test_stage03_order.py
symptoms:
  - "R-073: the plan orders its scripts; submit scripts/run_all.sh"
  - "<output> older than the run that should have produced it" from stage 03 verify
  - "is under scripts/ but not in the Scripts list" from approve
  - "the plan orders its scripts, and scripts/run_all.sh never ran"
---
# Stage 03 runs the plan's scripts in its order, as one job

Item S03-order of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner ("The plan lists its scripts in order, and GARS runs them as one job, or with declared dependencies"); one job is the plan's recommended path, so no new submit flag and no registry change. Wording is the lane's (gars-t74), under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing. It builds on 0306 (the scripts are approved with the plan).

## Context

A plan named no script order. The agent submitted each script as its own job, in an order it chose, so a script reading another's output could run before it, or after a failed one, and read a copy left by an earlier attempt; verify checked only that each declared output existed and was not empty.

**Reproduction.** At cacefffa, `gars/tests/test_stage03_order.py` fails six tests (`FAILED (failures=5, errors=1)`): approve writes no runner (`KeyError: 'runner'`), a Scripts list that misses a file under `scripts/` is approved (`0 != 2`), there is no runner to submit, and one script of a two-step plan reaches the backend on its own. The control (a plan with no Scripts section submits single scripts) is green.

## Decision

1. The PLAN.md skeleton gains a `## Scripts` section: a numbered list, one script per line, in run order.
2. `approve` refuses a Scripts list not numbered 1 to n, or not naming exactly the files under `scripts/`, and writes `scripts/run_all.sh`, which runs the listed scripts in that order with `set -euo pipefail`, so it stops at the first failure. The runner is written before the record is made, so 0306 binds it with the other scripts.
3. `executorlib submit` refuses any script of an ordered plan but the runner, before any launcher or backend call.
4. `verify` of an ordered plan refuses when the runner never ran, and when a declared output is older than the runner's submission (one second of tolerance for a coarse file-system clock): a stale copy from an earlier attempt is not this run's result.
5. The stage 03 contract: step 3 lists the scripts in run order; step 7 submits the runner once.

## What this does not close

- **A plan without a Scripts section** (written by hand, or before 0307) keeps single submissions and no staleness check; `create`'s skeleton always carries the section, and its `<FILL:` marker blocks approval until it is written.
- **Staleness is by time, not content.** An output a script rewrites with the same stale content still counts as this run's; one written less than a second before the submission is accepted.
- **S03-assay** (every assay's results listed, and an Assay column in the plan's Inputs) is the next item.

## Test

`gars/tests/test_stage03_order.py` (7 tests): the runner in plan order and bound; a mismatched list refused; the runner runs in order and verifies, and stops at the first failure; a single script of an ordered plan refused; a stale output refused by verify; the control.
Mutations: the staleness check off `FAILED (failures=1)`; the list gate off `FAILED (failures=1)`; the submit check off `FAILED (failures=1)`; the runner in reverse order `FAILED (failures=3)`.

## Status

Standing.

## Date

2026-10-17
