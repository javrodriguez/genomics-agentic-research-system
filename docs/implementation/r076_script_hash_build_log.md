# R-076 script-hash build log

This is producer evidence for the R-076 script-binding lane (0205), not a decision record, approval or merge.
The baseline is public main `81c0d71`; the producer is a Claude Opus 5.5 session, and the lane review is a separate fresh Opus 5.5 context, so review independence rests on a fresh context, not model diversity.
Every Python command set TMPDIR to the lane's own scratch folder, and ran one test module at a time.

## Reproduction (red first)

Red-first commit `25011b6` adds only `gars/tests/test_r076_script_binding.py`.
At the baseline system code, on Python 3.13.2, the module gave `Ran 9 tests`, `FAILED (failures=15, errors=3)`.
Every one of the three downstream wrappers (rnaseq-de, scrna-qc-cluster, spatial-cluster-count) submitted a changed, added-to, deleted or symlinked script with `('42', None)` and the backend called once, and `stage_record` still bound after a change made once the job was submitted.
The three errors are the formula tests, which name `downstream-v2`, unknown at the baseline.
The re-prepare control (C4) passed at the baseline, as it should.
The module as strengthened in the fix commit (same-size change in C1, linked `scripts/` in G3) reads the same, `FAILED (failures=15, errors=3)`, when run against the baseline's `gars/_system`.

## Fix

Fix commit `668daa1` changes `gars/_system/wrapperlib.py` (the `downstream-v2` formula and `scripts_tree_digest`, and prepare recording v2) and `gars/_system/executorlib.py` (submit refuses a `downstream-v1` stage).
Tests changed with it: the new module, `test_downstream_keys.py` (the formula name) and `test_rerun_check.py`.
The last one asserted that a replay in a fresh project has the original's key.
The generated script names its own project and stage, so a v2 key is bound to its location; the replay check now asserts the replay's key is its own recomputed v2 key and that the relocation-invariant part (inputs and params, the v1 key) is equal.

## Affected modules at the fix (Mac, one at a time)

On Python 3.13.2, each of these 29 modules read OK at `668daa1`: test_approval_forgery, test_bring_home, test_downstream_keys, test_execution_policy, test_executor_env, test_executorlib_resume, test_failure_classification, test_lifecycle_cancel, test_lifecycle_executor, test_lifecycle_faults, test_manifest_groups, test_no_false_completion, test_planted_defects (skipped=1), test_r076_script_binding, test_r164_exact_bytes, test_r164_failure_recovery, test_r164_keyed_lookups, test_r164_params_mapping, test_r164_writer_recovery, test_secret_containment, test_stage03_execution, test_tool_schema_refusal, test_venue_policy, test_wrapper_contract, test_wrapperlib_prepare, test_rerun_check (26 tests), test_unit_economics, test_backend_bench, test_bio_faults_core.
Before its assertion change, test_rerun_check read `FAILED (failures=6)`, each at a replay-key equality.
On Python 3.9.6, test_r076_script_binding, test_downstream_keys and test_r164_exact_bytes read OK.
The whole suite, the contract and count checks and the other hosts are the evidence step's, on the merge candidate.

## Mutations (Mac, Python 3.13.2)

Each mutation edits the imported file through a substring that occurs exactly once, runs the one module, and is restored from a byte backup verified by SHA-256.
`7 of 7 killed by the named test`: (i) v2 skips the walk, (ii) files framed without their digest, (iii) links followed, (iv) folders not framed, (v) prepare writes v1, (vi) submit accepts v1, (vii) a linked `scripts/` folder is walked.
