---
date: 2026-09-19
status: standing
kind: defect
touches:
  - tests/test_row05_backup.py
  - .github/workflows/ci.yml
  - README.md
symptoms:
  - "RuntimeError: GARS_ROW5_SCRATCH is required; no system-temp fallback"
  - run_tests.py fails from a cold clone with 23 errors, all in test_row05_backup.py
---
# Row 5 tests skip without a scratch folder, except under CI

## Context

Decision 0044 made a missing `GARS_ROW5_SCRATCH` a refusal, so row 5's tests never write to the system temp folder.
CI supplies the variable, so CI stayed green.
A stranger does not: at public `main` `e9d046c`, `python3 tests/run_tests.py` from a clean clone in a clean environment gave `Ran 219 tests · FAILED (errors=23, skipped=11)`, exit 1.
All 23 errors were `test_row05_backup.py`: the 22 offline tests and the database class's `setUpClass`, each raising the refusal.
The README says the suite runs green from a cold clone with no setup, so the first thing a visitor runs contradicted the first thing they read.
Found by the demo site's clean-clone walk (gars-demo-v2 slice 9, 18 Sep), which then pinned the site to the Gap Study's done commit `e866cce`.

## Decision

Both row 5 classes carry `needs_scratch`.
With `GARS_ROW5_SCRATCH` unset and outside CI, the class skips with the reason `environment: GARS_ROW5_SCRATCH unset; ...`, the same shape as `needs_pipeline`'s environment skips.
Under CI (`CI` set to `1`, `true` or `yes`) the class always runs, so a job that loses the variable fails on 0044's refusal rather than passing with row 5 skipped.
A variable that is set but names a missing folder, or a folder inside the repository, still refuses everywhere.
The README's verify block names the variable and how to set it.

## Why

0044's point was never "error on a cold clone"; it was "no system-temp fallback", and a skip keeps that: no row 5 test touches any temp folder unless a scratch folder is named.
A plain skip everywhere would let CI go green with row 5 unexercised, which is the hollow pass this repository has been bitten by before; the CI clause closes that.
0044 stays standing for everything else it decides; this record narrows only its "missing variable is a refusal" clause to CI and to invalid values.

## Evidence

The walk from a clean clone is recorded in the commit that introduced this decision: unset outside CI, set as CI sets it, and unset with `CI=true`.
