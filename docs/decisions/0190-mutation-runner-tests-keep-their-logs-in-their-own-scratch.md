---
date: 2026-10-16
status: standing
kind: defect
touches:
  - gars/tests/test_mutation_runner.py
  - gars/tests/test_temp_hygiene.py
symptoms:
  - gars-mutation-logs-* folders pile up in TMPDIR, five per run of test_mutation_runner.py
---
# The mutation runner's tests keep its suite logs in a scratch of their own

Follow-up to [0050](0050-row-3-test-suite-gate-and-mutants.md) and [0051](0051-row-5-tests-skip-without-scratch-outside-ci.md), whose behaviour is unchanged.
Every ruling here is **the lane's** (gars-ms21, task G1 T49), made under the owner's standing delegation; no sentence in this record is the owner's.

## Context

`evals/mutate.py`'s `measure()` takes its scratch only from an explicit `TMPDIR` (0050), and it keeps a `gars-mutation-logs-*` folder there on purpose: the suite logs are the run's evidence and must outlive it.
`gars/tests/test_mutation_runner.py` calls `measure()` five times (four tests, one of them twice) and left `TMPDIR` as the caller's, so every run of the module, and so every suite run, left five evidence folders in the caller's temp directory that nothing removed.

**Reproduction.** At public `main` `a97fa9cd`, a run of the module with a fresh `TMPDIR` printed five `mutation suite logs: ` lines and left five `gars-mutation-logs-*` folders in it.
The new `test_no_gars_dir_survives_a_module_run` fails there with `Lists differ: ['gars-mutation-logs-...', ...] != []`.

## Decision

**Ruling 0190 (the lane's).**

1. When `TMPDIR` is set, the module's `setUp` points it at `scratch/` under the test's own temporary base, through `mock.patch.dict` undone by `addCleanup`; the base, scratch and logs included, is removed with the test.
2. When `TMPDIR` is unset, `setUp` patches nothing, so 0051's rule holds: outside CI the four `measure()` tests skip, and under CI they run and `measure()` refuses.
3. `evals/mutate.py` is untouched: keeping the evidence folder is its contract, and the tests, not the runner, own where a test's evidence goes.

Rejected alternatives: removing the folder in `measure()` (it is the run's evidence); patching `TMPDIR` unconditionally (under CI with `TMPDIR` unset it would make `measure()` succeed, the hollow pass 0051 forbids); a scratch made with `tempfile.mkdtemp` beside the base (it would itself be left behind).

## What this does not close

- **R1** A real `measure()` run (`evals/mutate.py --require`) still keeps its evidence folder in `TMPDIR`, by design.
- **R2** Other modules may leave entries of other names in `TMPDIR`; this record and its test cover the `gars-*` folders of this module only.

## Test

`gars/tests/test_temp_hygiene.py` holds two tests, each running `gars/tests/test_mutation_runner.py` in a subprocess.
`test_no_gars_dir_survives_a_module_run` gives it a fresh `TMPDIR`, requires a passing run with exactly five `mutation suite logs: ` lines, so skipped tests cannot satisfy it, and requires no `gars-*` entry left behind.
`test_ci_without_tmpdir_still_refuses` unsets `TMPDIR` and sets `CI=true`, and requires a failing run with four `measure()` refusals and no log line.
They must fail when the patch is dropped, when it is applied unconditionally, when `needs_tmpdir` always skips, and when the scratch is made outside the test's base; the lane's mutation proof killed all four.

## Status

Standing. The change record for the mutation runner tests' leaked suite logs.

## Date

2026-10-16
