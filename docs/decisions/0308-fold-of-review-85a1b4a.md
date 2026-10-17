---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/stage03_analysis.py
  - gars/03_custom_analysis/CONTEXT.md
  - gars/tests/test_stage03_order.py
symptoms:
  - "disagrees across the scripts" from stage 03 approve
  - "--time is given by ... but not by" from stage 03 approve
  - an ordered plan's job runs on scheduler defaults, or a login-node job above 8 GiB is accepted
---
# The fold of REVIEW-85a1b4a: the runner's directives

The fold of the fresh review of lane gars-t74's run 5 (`lanes/gars-t74/REVIEW-85a1b4a.md`), under glitch-b5's rulings of Sat 17 Oct 2026 (`lanes/gars-t74/RULINGS.md`). Wording is the lane's, under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing. It builds on 0307 (the ordered runner), which is not edited.

## Context

**Finding 1 (MAJOR).** 0307's generated `scripts/run_all.sh` carried no `#SBATCH` lines, and the launcher and the venue policy read the submitted script's. An ordered plan's job therefore ran on the scheduler's defaults whatever its scripts asked, and on the local venue a runner whose script asked `--mem=64G` was accepted where the script alone is refused (`venue_not_permitted: venue local memory rule: above 8 GiB`).

**Reproduction.** At 47146581, `RunnerDirectiveTests` in `gars/tests/test_stage03_order.py` fails all seven (`FAILED (failures=7)`): `'#SBATCH --mem=64G' not found in '#!/bin/bash'`, the runner submitted locally reaches the backend, and approve exits 0 on a disagreement.

## Decision

1. **The runner's directives are the scripts' (ruling 1).** `approve` reads each listed script's leading `#SBATCH` lines (up to the first line that is neither blank nor a comment, as the launcher reads them; Slurm's common short spellings such as `-t` and `-c` are the long ones) and writes one value per directive into the runner, after its shebang, because the scripts run one after another in one job: `--time` is the sum of the scripts' times, and a time on some scripts but not others is refused; `--mem`, `--mem-per-cpu` and `--cpus-per-task` take the largest value; every other directive must have the same value in every script that names it. A disagreement, a directive named twice in one script with different values, or a value approve cannot read (memory in the venue policy's K/M/G/T form, time in Slurm's forms, CPUs an integer) makes approve refuse with exit 2, naming the scripts and the directive, and write nothing: no runner, no stamp, no record. The launcher and the venue policy then read the runner's directives, as they read a single script's; neither changed.
2. The stage 03 contract's step 3 says so.

## What this does not close

- A directive approve does not know the meaning of is compared as text: `--mem=4G` against `--mem=4096M` is the largest of two, but two spellings of one partition list disagree.

## Test

`gars/tests/test_stage03_order.py` `RunnerDirectiveTests` (7 tests): the slurm launcher's header carries the directives; the local venue refuses the runner exactly as it refuses the script alone; 12:00:00 twice is 24:00:00; the largest memory and CPUs win; a disagreement, a time on some scripts only, and an unreadable value are refused with nothing written.
Mutations: the runner without directives `FAILED (failures=4)`; times by the largest, not the sum, `FAILED (failures=2)`; the agreement check off, the largest memory off, and the missing-time check off, `FAILED (failures=1)` each.

## Status

Standing.

## Date

2026-10-17
