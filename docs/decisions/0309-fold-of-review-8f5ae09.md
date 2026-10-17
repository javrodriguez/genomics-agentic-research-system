---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/stage03_analysis.py
  - gars/03_custom_analysis/CONTEXT.md
  - gars/tests/test_stage03_order.py
  - gars/_system/authoring/create_bioinformatics_skill.py
  - gars/tests/test_history_model.py
  - gars/tests/test_execution_policy.py
symptoms:
  - "--mem (...) and --mem-per-cpu (...) are mixed across the scripts" from stage 03 approve
  - sbatch refuses an ordered plan's job that asks both --mem and --mem-per-cpu
  - "memory is a number with a unit of K, M, G or T" from stage 03 approve
  - "cmd_collect reads the model flag from args outside its ws.history_model( call" from conform
  - test_execution_policy test_prepared_content_regressions says "Matrix supplied by: unknown"
---
# The fold of REVIEW-8f5ae09: one memory request per runner, conform's flag rule on the parsed tree

The fold of the fresh review of lane gars-t74's run 6 (`lanes/gars-t74/REVIEW-8f5ae09.md`), under glitch-b5's rulings of Sat 17 Oct 2026 (`lanes/gars-t74/RULINGS.md`). Wording is the lane's, under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing. It builds on 0308, which is not edited.

## Context

**Finding 1 (MINOR).** 0308 binds the supplier line to the input prepare recorded. `test_execution_policy`'s stand-in collect fixture wrote a manifest recording only `config`, so the reused run_tests cases (ScrnaQcClusterTests test_02, SpatialClusterCountTests test_08) saw `unknown` where they assert the producer, and the module went red though the classes pass when run_tests.py runs them directly.

**Finding 2 (MINOR).** 0308 takes the largest value per directive. Two scripts that ask `--mem=8G` and `--mem-per-cpu=4G` were approved as one runner carrying both, which Slurm documents as mutually exclusive and sbatch refuses; the venue policy also read only the 8G.

**Finding 3 (MINOR).** 0308's conform rule counted the substring `args.model`. `getattr(args, "model")`, `vars(args)["model"]`, `args.__dict__["model"]` and `args .model` read the flag without that text, and conform passed each. This was the third round on the rule.

**NIT 2.** Approve refuses Slurm's unitless megabytes and lowercase units, as the venue policy refuses them for a single script, without saying which forms it reads.

## Decision

1. **The stand-in records its input (ruling 1).** The stand-in manifest of `test_prepared_content_regressions` records the resolved producer artifact under the label the real prepare uses (`h5ad` for scrna-qc-cluster and spatial-cluster-count, `counts` for rnaseq-de), as a real prepare does. No assertion changed. No other stand-in manifest in the gars tests tree is read by a supplier assertion.
2. **One memory request per runner (ruling 2).** Approve refuses a plan whose listed scripts mix `--mem` and `--mem-per-cpu`, naming the scripts on each side and both directives: exit 2, nothing written. The stage 03 contract's step 3 says to ask memory one way in every script.
3. **conform's flag rule is an allow-list on the parsed tree (ruling 3).** conform parses `cmd_collect` with `ast` and fails any read of `model` from `args` that is not inside the argument list of a `ws.history_model` call: an attribute `model` or `__dict__` on the name `args` in any spacing, `getattr(args, ...)` naming `model` or `__dict__` or a computed name, and `vars(args)`. The one permitted place is the rule; the spellings are its test rows.
4. **The memory refusal names its forms (ruling 4, NIT 2).** A memory value approve cannot read is refused as before, and the refusal says memory is a number with a unit of K, M, G or T, upper case. What is accepted does not change.

## What this does not close

- conform follows the name `args` only: binding it to another name (`a = args`) or passing the whole namespace to a helper that reads the flag is not traced.
- Two spellings of one memory amount in the same directive are still compared by size, not refused (0308's residual stands).

## Test

`gars/tests/test_execution_policy.py` `test_prepared_content_regressions`: red at 40e1dc1a (`FAILED (failures=1)`), green with the fixture change.

`gars/tests/test_stage03_order.py` `RunnerDirectiveTests` (2 new, 16 in the module): `--mem` in one script and `--mem-per-cpu` in the other refused, naming both; `64000` and `64g` refused with the accepted forms named. Mutation: the mix check off `FAILED (failures=1)`.

`gars/tests/test_history_model.py` `AuthoringTests`: five more rows (getattr, getattr with a default, vars, `__dict__`, a spaced attribute), no test added; every shipped wrapper still conforms. Mutations: the attribute read off `FAILED (failures=3)`; the getattr read off `FAILED (failures=2)`; the allow-list off `FAILED (failures=1)`.

## Status

Standing.

## Date

2026-10-17
