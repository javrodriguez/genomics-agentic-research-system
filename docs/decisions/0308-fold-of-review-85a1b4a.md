---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/stage03_analysis.py
  - gars/03_custom_analysis/CONTEXT.md
  - gars/tests/test_stage03_order.py
  - gars/_system/resolve_artifact.py
  - gars/_system/wrappers/rnaseq-de/rnaseq_de.py
  - gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py
  - gars/_system/wrappers/spatial-cluster-count/spatial_cluster_count.py
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
  - gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md
  - gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md
  - gars/tests/test_downstream_input.py
  - tests/run_tests.py
  - gars/_system/authoring/create_bioinformatics_skill.py
  - gars/tests/test_history_model.py
symptoms:
  - "disagrees across the scripts" from stage 03 approve
  - "--time is given by ... but not by" from stage 03 approve
  - an ordered plan's job runs on scheduler defaults, or a login-node job above 8 GiB is accepted
  - "--counts ... is not the counts_gene the resolver found" from rnaseq-de prepare
  - "Counts supplied by: unknown" or "Matrix supplied by: unknown" though a producer completed
  - "cmd_collect reads args.model outside its ws.history_model( call" from conform
---
# The fold of REVIEW-85a1b4a: the runner's directives, the supplier bound to the input read, conform's flag rule

The fold of the fresh review of lane gars-t74's run 5 (`lanes/gars-t74/REVIEW-85a1b4a.md`), under glitch-b5's rulings of Sat 17 Oct 2026 (`lanes/gars-t74/RULINGS.md`). Wording is the lane's, under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing. It builds on 0307 (the ordered runner), which is not edited.

## Context

**Finding 1 (MAJOR).** 0307's generated `scripts/run_all.sh` carried no `#SBATCH` lines, and the launcher and the venue policy read the submitted script's. An ordered plan's job therefore ran on the scheduler's defaults whatever its scripts asked, and on the local venue a runner whose script asked `--mem=64G` was accepted where the script alone is refused (`venue_not_permitted: venue local memory rule: above 8 GiB`).

**Finding 2 (MINOR).** 0305 made each collect's "supplied by" line name the resolver's producer, asked afresh at collect. rnaseq-de's prepare took any `--counts` with no resolver check, so the line could name a sub-stage that supplied nothing: prepare read counts outside the project, a producer declaring other counts completed later, and the entry said `Counts supplied by: 01_nfcore-rnaseq-wrapper`. The same held for the h5ad wrappers in 0305's residual (nothing resolved at prepare, an explicit path used, an upstream completed before collect).

**Finding 3 (MINOR).** conform's flag rule (0304's fold) matched line by line: a collect that kept `model = ws.history_model(WORKSPACE, args.model)` and added `model = args.model or model` after it passed with no failure, and the history entry and manifest carried the agent's value.

**Reproduction.** At 47146581, `RunnerDirectiveTests` in `gars/tests/test_stage03_order.py` fails all seven (`FAILED (failures=7)`): `'#SBATCH --mem=64G' not found in '#!/bin/bash'`, the runner submitted locally reaches the backend, and approve exits 0 on a disagreement. At 08a9cb0a, `gars/tests/test_downstream_input.py` fails five (`FAILED (failures=5)`): rnaseq-de prepare with the outside counts `0 != 2`, and the supplier named where `unknown` is expected for rnaseq-de (outside path; a recorded sha256 that differs) and for both h5ad wrappers (the residual); the control (prepare read the producer's artifact) is green. At b3097d30, the reviewer's mutant as one more row of `test_conform_refuses_the_flag_on_an_entry_or_manifest_line` fails (`0 != 1`, conform `ok: true`).

## Decision

1. **The runner's directives are the scripts' (ruling 1).** `approve` reads each listed script's leading `#SBATCH` lines (up to the first line that is neither blank nor a comment, as the launcher reads them; Slurm's common short spellings such as `-t` and `-c` are the long ones) and writes one value per directive into the runner, after its shebang, because the scripts run one after another in one job: `--time` is the sum of the scripts' times, and a time on some scripts but not others is refused; `--mem`, `--mem-per-cpu` and `--cpus-per-task` take the largest value; every other directive must have the same value in every script that names it. A disagreement, a directive named twice in one script with different values, or a value approve cannot read (memory in the venue policy's K/M/G/T form, time in Slurm's forms, CPUs an integer) makes approve refuse with exit 2, naming the scripts and the directive, and write nothing: no runner, no stamp, no record. The launcher and the venue policy then read the runner's directives, as they read a single script's; neither changed.
2. The stage 03 contract's step 3 says so.
3. **rnaseq-de prepare resolves `--counts` (ruling 2a).** Through `choose_input`, as the h5ad wrappers do: once a completed sub-stage before it declares `counts_gene`, a `--counts` other than that artifact is refused with exit 2 (`input_not_resolved`, naming the resolved path) and nothing is written. `--counts` stays required, so the pinned registry still validates; `check` is unchanged, since its public output is held byte-identical to the base (`test_closed_project_outputs`).
4. **The supplier line names what was read (ruling 2b).** For rnaseq-de and the two h5ad wrappers, collect's "supplied by" names a producer only when the input prepare recorded in `reproducibility/manifest.json` (`inputs`, else `params`, under `counts` or `h5ad`) is that producer's artifact: the same resolved path, and the same sha256 where both the manifest and the producer's OUTPUTS.tsv record one. Otherwise it says `unknown`. This closes 0305's residual: an explicit path used when nothing resolved names no supplier, whatever completes later.
5. The three sub-stage contracts say so; rnaseq-de's names `input_not_resolved`.
6. **conform's flag rule (ruling 3).** In `cmd_collect`, `args.model` may appear only inside the `ws.history_model(` call; conform fails any other occurrence. The earlier line rule stays.

## What this does not close

- A directive approve does not know the meaning of is compared as text: `--mem=4G` against `--mem=4096M` is the largest of two, but two spellings of one partition list disagree.
- A directory input (spatial-cluster-count) records no single sha256 in the manifest, so its producer is bound by path alone.
- An explicit path still stands at prepare when nothing resolves; it is recorded honestly as supplied by `unknown`.
- **0304's byte-for-byte revert (NIT 4).** After a write, a user who reverts the config byte for byte to the state the dry run read can have the shown apply written again with no new dry run.
- **A helper outside `scripts/` (NIT 5, for 0306).** A script under `scripts/` can call a file outside it (for example `Rscript ../analysis.R`), which no approval binds.

## Test

`gars/tests/test_stage03_order.py` `RunnerDirectiveTests` (7 tests): the slurm launcher's header carries the directives; the local venue refuses the runner exactly as it refuses the script alone; 12:00:00 twice is 24:00:00; the largest memory and CPUs win; a disagreement, a time on some scripts only, and an unreadable value are refused with nothing written.
Mutations: the runner without directives `FAILED (failures=4)`; times by the largest, not the sum, `FAILED (failures=2)`; the agreement check off, the largest memory off, and the missing-time check off, `FAILED (failures=1)` each.

`gars/tests/test_downstream_input.py` (17 tests; 5 new): rnaseq-de prepare refuses other counts with nothing written; the producer named when prepare read its artifact; a producer whose recorded sha256 differs is not named; the reviewer's outside-path case is `unknown` (the assertion of `test_the_resolvers_producer_never_the_flag` changed under glitch-b5's named ruling 2); the residual for both h5ad wrappers. `tests/run_tests.py` `test_04_de_prepare_and_collect` now completes the producer before prepare and prepares with its counts, so its unchanged assertion (the producer named) holds.
Mutations: the rnaseq-de refusal off `FAILED (failures=1)`; the path check off `FAILED (failures=3)`; the sha256 check off `FAILED (failures=1)`.

`gars/tests/test_history_model.py` `AuthoringTests`: the reviewer's mutant is one more row (no test added); every shipped wrapper still conforms. Mutation: the new rule off `FAILED (failures=1)`.

## Status

Standing.

## Date

2026-10-17
