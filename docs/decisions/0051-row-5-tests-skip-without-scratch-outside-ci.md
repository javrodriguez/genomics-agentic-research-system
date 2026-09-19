---
date: 2026-09-19
status: standing
kind: defect
touches:
  - tests/test_row05_backup.py
  - gars/tests/test_mutation_runner.py
  - .github/workflows/ci.yml
  - infra/compose/README.md
  - README.md
symptoms:
  - "RuntimeError: GARS_ROW5_SCRATCH is required; no system-temp fallback"
  - run_tests.py fails from a cold clone with 23 errors, all in test_row05_backup.py
  - "ValueError: TMPDIR must name an existing scratch directory" from test_mutation_runner.py on Linux
---
# Tests that need a named scratch folder skip without one, except under CI

## Context

Decision 0044 made a missing `GARS_ROW5_SCRATCH` a refusal, so row 5's tests never write to the system temp folder.
CI supplies the variable, so CI stayed green.
A stranger does not: at public `main` `e9d046c`, `python3 tests/run_tests.py` from a clean clone in a clean environment gave `Ran 219 tests · FAILED (errors=23, skipped=11)`, exit 1.
All 23 errors were `test_row05_backup.py`: the 22 offline tests and the database class's `setUpClass`, each raising the refusal.
The README says the suite runs green from a cold clone with no setup, so the first thing a visitor runs contradicted the first thing they read.
Found by the demo site's clean-clone walk (gars-demo-v2 slice 9, 18 Sep), which then pinned the site to the Gap Study's done commit `e866cce`.
The fix's review found the same class one layer down: `evals/mutate.py`'s `measure()` takes scratch only from an explicit `TMPDIR` (decision 0050), macOS always sets one and Linux does not, so with `TMPDIR` also unset two tests in `gars/tests/test_mutation_runner.py` still failed (`Ran 236 · FAILED (errors=2, skipped=50)`).

## Decision

Both row 5 classes carry `needs_scratch`.
With `GARS_ROW5_SCRATCH` unset and outside CI, the class skips with the reason `environment: GARS_ROW5_SCRATCH unset; ...`, the same shape as `needs_pipeline`'s environment skips.
Under CI (`CI` set to `1`, `true` or `yes`) the class always runs, so a job that loses the variable fails on 0044's refusal rather than passing with row 5 skipped.
A variable that is set but names a missing folder, or a folder inside the repository, still refuses everywhere.
The two mutation-runner tests that run a full `measure()` carry `needs_tmpdir`, the same rule keyed on `TMPDIR`; `measure()` itself is unchanged and still refuses without it.
The README's verify block names the variable and how to set it.

## Why

0044's point was never "error on a cold clone"; it was "no system-temp fallback", and a skip keeps that: no row 5 test touches any temp folder unless a scratch folder is named.
A plain skip everywhere would let CI go green with row 5 unexercised, which is the hollow pass this repository has been bitten by before; the CI clause closes that.
0044 is marked partially superseded by this record: it stands for everything else it decides, and only its "missing variable is a refusal" clause is narrowed to CI and to invalid values.
0050's explicit-`TMPDIR` rule is untouched; only the tests that exercise it skip on a machine that sets none.

## Evidence

Walked on 2026-09-19 at `0799749`, each from a fresh clone, Python 3.13.2 on macOS, with `GARS_ROW5_SCRATCH`, `CI`, `TMPDIR`, `TEMP` and `TMP` removed before each walk set its own:

| Walk | Set | Result |
|---|---|---|
| a stranger on Linux | nothing | `Ran 236 · OK (skipped=52)`, exit 0 |
| a stranger on macOS | `TMPDIR` | `Ran 236 · OK (skipped=50)`, exit 0 |
| CI with its settings lost | `CI=true` | `Ran 219 · FAILED (errors=25)`, exit 1: row 5's 22 offline tests and `setUpClass`, and the two mutation-runner tests, each refusing |
| as CI sets it | `CI=true`, `GARS_ROW5_SCRATCH`, `TMPDIR` | the offline and mutation-runner tests pass; this machine's Docker answered, so the 17 live-Postgres tests ran, and 4 errored with `command_failed` in `setUp` |

The live-Postgres errors predate this record: the same class run alone at `e9d046c`, with the variable set, gave `Ran 17 · FAILED (errors=2)` with the same `command_failed`, and the set of failing tests moves between runs.
With Docker not answering they skip, as they do in CI's 28, and this record does not touch them.
`check_counts.py` (clean, enforced=3), `check_contracts.py` (14 contracts clean) and `evals/test_harness.py` (`Ran 44 · OK`) pass at `0799749`.
