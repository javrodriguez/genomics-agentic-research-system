---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/resolve_artifact.py
  - gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py
  - gars/_system/wrappers/spatial-cluster-count/spatial_cluster_count.py
  - gars/_system/wrappers/rnaseq-de/rnaseq_de.py
  - gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md
  - gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
  - gars/tests/test_downstream_input.py
  - tests/run_tests.py
symptoms:
  - "input_not_resolved: --h5ad ... is not the h5ad the resolver found for this sub-stage"
  - "note: --h5ad-from is ignored; the supplier comes from the resolver (decision 0305)"
  - "note: --counts-from is ignored; the supplier comes from the resolver (decision 0305)"
  - "Matrix supplied by: unknown" or "Counts supplied by: unknown" in a history entry
---
# A downstream analysis finds its own input, and names its supplier, with the resolver

Items D-input and D-supplier of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner ("Each analysis finds its own input with GARS's resolver"; "The collecting step takes the producer's name from the resolver, not from the agent"). Wording is the lane's (gars-t74), under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing.

## Context

scrna-qc-cluster and spatial-cluster-count took their input as `--h5ad <path>`, the path the agent carried over from the router's resolution, and used whatever path it passed: given a second object from the same run (`S1/matrix.h5ad` beside the combined matrix, or an older results directory), prepare wrote it into the analysis script. rnaseq-de, scrna-qc-cluster and spatial-cluster-count wrote "Counts supplied by" / "Matrix supplied by" from the agent's `--counts-from` / `--h5ad-from` words, or `unknown`.

**Reproduction.** At e5399527, `gars/tests/test_downstream_input.py` fails ten tests (`FAILED (failures=10)`): prepare with no path `1 != 0` (`--h5ad was not supplied`); the wrong object from the same run is used (`0 != 2`) and passes check (`0 != 1`); the history entries carry `made-up-stage`. The two controls (the resolver's own path accepted) are green.

## Decision

1. `resolve_artifact.upstream(project, assay, type, before)` resolves by the existing rule among the completed sub-stages ordered before the consumer, so a sub-stage's own outputs (scrna-qc-cluster also produces `h5ad`) never answer for its input; a declared but absent artifact is no answer.
2. scrna-qc-cluster and spatial-cluster-count `check` and `prepare` resolve their `h5ad` themselves (`choose_input`). With no `--h5ad`, they use the resolver's artifact. A `--h5ad` that is not the resolver's is refused: `prepare` exits 2 (`input_not_resolved`, nothing written) and `check` lists it as a failure. The resolver's own path is still accepted.
3. Every collect's "supplied by" line names the sub-stage the resolver finds for that type, or `unknown`; `--h5ad-from` and `--counts-from` are ignored with a note on stderr, kept declared so the pinned registry validates: no registry change.
4. The three sub-stage contracts pass no `--h5ad`, `--h5ad-from` or `--counts-from` (rnaseq-de's typed collect call drops its `counts-from` key) and name `input_not_resolved` in their failure vocabulary.
5. Fixtures, no assertion changed: three run_tests collects that assert the supplier their flag names (RnaseqGarsWrapperTests test_04, ScrnaQcClusterTests test_02, SpatialClusterCountTests test_08) now build the completed upstream sub-stage the resolver reads (`completed_upstream`); they still pass the same flag, so they no longer tell flag from resolver, which `test_downstream_input.py` does.

## What this does not close

- **Nothing resolved, an explicit path stands.** When no completed sub-stage before the consumer declares an `h5ad`, a `--h5ad` path is still used as given (the suite's single-sample drivers and fixtures rely on it, and making it a refusal would change the assertions of run_tests SpatialClusterCountTests test_03 and the fixtures of test_manifest_groups, test_rerun_check and the frozen writer-recovery rows). The router routes to these sub-stages only when the resolver finds their input, so the residual is an agent bypassing the router; a ruling can make it strict.
- **rnaseq-de's counts** are still the path the agent passes (D-input names the two h5ad consumers); its supplier line names the resolver's producer, which is the input only when the agent passed the resolver's path.
- **The supplier is resolved at collect time.** An upstream re-run between prepare and collect makes the entry name the newer producer.
- **Pinned SKILL.md files** (scrna-qc-cluster, spatial-cluster-count) still show `--h5ad <path>` and `--h5ad-from`; their hunks are in `lanes/gars-t74/pin-skills.patch` with the re-pin, applied by glitch-b5 at landing.

## Test

`gars/tests/test_downstream_input.py` (12 tests) on the suite's real wrapper fixtures (test_manifest_groups): for each h5ad consumer, prepare with no path, refusal of another object from the same run with nothing written, check's `input_not_resolved`, the resolver's own path accepted, and collect's supplier; for rnaseq-de, the resolver's producer and `unknown`, never the flag.
Mutations: the mismatch refusal disabled `FAILED (failures=4)`; the supplier taken from the flag `FAILED (failures=4)`.

## Status

Standing.

## Date

2026-10-17
