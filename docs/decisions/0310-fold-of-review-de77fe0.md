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
symptoms:
  - "are mixed across the scripts; they run as one job, which Slurm refuses with more than one of --mem, --mem-per-cpu, --mem-per-gpu" from stage 03 approve
  - sbatch refuses an ordered plan's job that asks --mem-per-gpu beside --mem or --mem-per-cpu
  - "args may only be read as args.<field>, and the flag only as a whole argument of that call" from conform
---
# The fold of REVIEW-de77fe0: one memory family per runner, conform's args rule as an allow-list

The fold of the fresh review of lane gars-t74's run 7 (`lanes/gars-t74/REVIEW-de77fe0.md`), under glitch-b5's rulings of Sat 17 Oct 2026 (`lanes/gars-t74/RULINGS.md`). Wording is the lane's, under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing. It builds on 0309, which is not edited.

## Context

**Finding 1 (MINOR).** 0309 refused `--mem` beside `--mem-per-cpu` only. Slurm documents `--mem`, `--mem-per-cpu` and `--mem-per-gpu` as mutually exclusive, so a plan with `--mem=8G` (or `--mem-per-cpu=8G`) in one script and `--mem-per-gpu=4G` in the next was approved as one runner carrying both, which sbatch refuses at submit.

**Finding 2 (MINOR).** 0309's conform rule still named forbidden shapes on the name `args` and admitted anything inside the `ws.history_model` call. An alias (`a = args`), a lambda parameter, `builtins.getattr`, `getattr` or `vars` through another name, a starred `getattr`, `args.__getattribute__`, `object.__getattribute__`, `operator.attrgetter`, `args._get_kwargs()` and a walrus inside the permitted call each read the flag with conform green. The review counts this as one more round on the rule after 0309.

**NIT 1.** The memory refusal said "the venue policy's form" without naming the file. **NIT 2.** 0309's "What this does not close" named the alias and the helper as residual.

## Decision

1. **One memory family per runner (ruling 1).** `--mem`, `--mem-per-cpu` and `--mem-per-gpu` are one family: approve refuses a plan when more than one of them appears across the listed scripts, naming each with its scripts, exit 2, nothing written. 0309's pair is one case of it. The stage 03 contract's step 3 names the three.
2. **conform's args rule is an allow-list (ruling 2).** In `cmd_collect`, every load of the name `args` must be the receiver of an attribute whose name is not `model` and does not start with `_`. The one exception is `args.model` as a whole positional or keyword argument of the `ws.history_model(...)` call, when no assignment expression appears anywhere in that call. Anything else fails: `args` bare, passed, aliased, subscripted, starred, a dunder or private attribute, a walrus. Every shipped wrapper conforms unchanged.
3. **The memory refusal names its policy file (ruling 3, NIT 1).** The accepted-forms clause ends "the form of `_system/venue_policy.py`". What is accepted does not change.

## What 0309's residual section now closes

- **The alias and the helper: closed.** Binding `args` to another name, or passing the whole namespace to a helper (a function, a lambda, `operator.attrgetter`), is a bare use of `args` and fails, so neither needs tracing any more. Only `args.<field>` reads and the one argument of `ws.history_model` remain.
- **Two spellings of one memory amount: not closed.** The same directive given as `16G` in one script and `16384M` in another is still compared by size (0308's residual stands, and 0309 restated it).

## What this does not close

- conform reads `cmd_collect` only; a module-level helper that reads `sys.argv` or re-parses the arguments is outside the rule, as it was under 0303.
- The family check reads the listed scripts' leading `#SBATCH` lines; a memory request given by other means (an environment variable read by sbatch) is not seen, as under 0308.

## Test

`gars/tests/test_stage03_order.py` `RunnerDirectiveTests` (2 new, 18 in the module): `--mem=8G` and `--mem-per-cpu=8G` each beside `--mem-per-gpu=4G` with `--gpus=1`, refused naming each directive with its scripts; red at 3039da0e (`FAILED (failures=2)`, each `0 != 2`). `test_a_refused_memory_value_names_the_accepted_forms` also asks for `_system/venue_policy.py` (ruling 3); red before the fix (`FAILED (failures=2)`).

`gars/tests/test_history_model.py` `AuthoringTests` (1 new, 21 in the module): the review's eleven reproductions, red at 5cb3a1c5 (`FAILED (failures=11)`), plus a witness row for the assignment-expression clause (`args.model` a whole argument, a walrus elsewhere in the call). Mutations: the underscore check off `FAILED (failures=3)`; the `model` check off `FAILED (failures=3)`; the attribute check off `FAILED (failures=17)`; the assignment-expression clause off `FAILED (failures=1)`.

## Status

Standing.

## Date

2026-10-17
