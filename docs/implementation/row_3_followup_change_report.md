# Row 3 follow-up change report: a stronger R-164 suite, test-only

Decision: [0087](../decisions/0087-row-3-followup-suite-strengthening.md).
Branch `build/gars-row-3-followup`, base `2a81999`.
Rulings in this report are the lane's, under the owner's standing delegation of 23 Sep 2026.
This report claims no exit and states no mutation score.

## Coverage map (written before building)

Every function below was read at `2a81999` and is observed only through its import, its CLI or its written artifacts.

| Class | Module (new) | Functions covered |
|---|---|---|
| 1. Exact-bytes identity | `gars/tests/test_r164_exact_bytes.py` | `wrapperlib.sha256`; `wrapperlib.input_key` (`stage01-v1`, `downstream-v1`); `wrapperlib.output_evidence` (file and `sha256-tree:` directory); `wrapperlib.reference_sha256`; `wrapperlib.write_reproducibility` (`<label>_sha256` fields); `tools.execution.config_holds`; `claims.evidence_check.artifact_problem` |
| 2. Failure-path recovery | `gars/tests/test_r164_failure_recovery.py` | `workspace.atomic_open` (exception in the body, at `fsync`, at `os.replace`); `wrapperlib.write_params_yaml` interrupted mid-write; `wrapperlib.write_status` (`fsync` and `os.replace` failures); `wrapperlib.harvest_cache` (rename lost, populated cache never overwritten, no incoming sibling left); the generated `submit.sh` guard's three states (fresh, Nextflow state present, completion marker present) |
| 3. Parameter mapping | `gars/tests/test_r164_params_mapping.py` | `build_params` of all seven nf-core wrappers (atacseq, chipseq, cutandrun, methylseq, rnaseq, scrnaseq, spatialvi); `cmd_prepare` of the three downstream wrappers (rnaseq-de, scrna-qc-cluster, spatial-cluster-count): manifest params and the generated script's constants; `executorlib.header_lines` (partition, time, cpus, mem) |
| 4. Data-keyed lookups | `gars/tests/test_r164_keyed_lookups.py` | `nfcore_scrnaseq_wrapper.supported_protocols` and its use in `run_checks`; `INDEX_PARAM` by aligner in the atacseq, chipseq and scrnaseq builders; `workspace.design_columns`, `files_header`; `wrapperlib.pipeline_checkout` by assay; `NEXTFLOW_LEGACY_PARSER` in the generated `submit.sh`; `wrapperlib.reference_evidence` by genome row; `executorlib.load` / `nextflow_config_path` / `nextflow_profile` / `header_lines` by backend |
| 5. Boundaries | `gars/tests/test_r164_boundaries.py` | `spatial_cluster_count.cmd_collect` (`n_obs`, `n_clusters` at 0, 1, −1, missing, extra sample; table sums); `spatial_cluster_count.resolve_inputs` (zero-byte, one-byte); `nfcore_spatialvi_wrapper.cmd_collect` (processed object zero/one byte, raw-only); `nfcore_scrnaseq_wrapper.cmd_collect` (combined matrix zero/one byte); `rnaseq_de.run_checks` (contrast level with 1 and 2 samples); `rnaseq_de.check_table` (BH tolerance on both sides, `p <= q`, `q <= 1`); `wrapperlib.is_commit_pin` (6/7 and 40/41 characters); `integrity.needs_scheduling` and `estimate_minutes` |
| 6. Gate and guard | none added | Already covered: `test_pre_push.py` refuses a planted failure and each empty tree; `test_guard_hook.py` and `test_protected_paths.py` refuse each protected shape. |

Class 6 gets no new module, by the brief's "only where not already covered".

## Existing tests changed

None. No existing test was edited, weakened or removed; the count goes from 703 to 757 (54 new tests).

## Plant table

Every plant was applied in a disposable `rsync -a --exclude .git` copy of the working tree under `<scratch>`, never in this repository; only the named module ran (`python3 gars/tests/<module>.py`, with `TMPDIR`, `TEMP` and `TMP` at `<scratch>`), and the copy was deleted afterwards.
The unplanted copy printed `OK` for all five modules (`test_r164_exact_bytes` 8 tests, `test_r164_failure_recovery` 9, `test_r164_params_mapping` 11, `test_r164_keyed_lookups` 8, `test_r164_boundaries` 18).
"Failing test" names the new test that went red; where more than one did, all are listed.
Survivor diffs M03, M05, M08 and M10 were applied with `git apply` as the brief gives them; M07 does not apply at `2a81999` and was re-planted by hand with the same behaviour.

| Plant | Class | file:function | Diff, in one line | Module run | Failing test(s) | Red seen |
|---|---|---|---|---|---|---|
| M03 | survivor (1) | `gars/_system/wrapperlib.py:sha256` | `h.update(chunk)` → `h.update(chunk.rstrip())` | `test_r164_exact_bytes` | `test_sha256_is_the_digest_of_the_exact_bytes`, `test_downstream_key_separates_every_byte_difference`, `test_output_evidence_file_and_tree_digests`, `test_reference_digest_follows_the_bytes`, `test_reproducibility_records_exact_input_digests` (`FAILED (failures=13)`) | yes |
| M05 | survivor (2) | `gars/_system/workspace.py:atomic_open` | `tmp.unlink()` → `path.unlink()` | `test_r164_failure_recovery` | `test_atomic_open_keeps_previous_artifact_at_every_step`, `test_atomic_open_first_write_interrupted_leaves_nothing`, `test_params_yaml_interrupted_mid_write_keeps_previous` (`FAILED (failures=1, errors=4)`) | yes |
| M07 | survivor (3) | `gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py:build_params` | `("star_index", str(star.resolve())), ("salmon_index", str(salmon.resolve()))` → the two values exchanged | `test_r164_params_mapping` | `test_rnaseq_indices_are_not_exchanged` (`FAILED (failures=1)`) | yes |
| M08 | survivor (4) | `gars/_system/wrappers/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py:supported_protocols` | `data.get(aligner)` → `data.get("simpleaf")` | `test_r164_keyed_lookups` | `test_scrnaseq_protocols_are_read_for_the_selected_aligner`, `test_scrnaseq_preflight_judges_protocol_against_its_own_aligner` (`FAILED (failures=7)`) | yes |
| M10 | survivor (5) | `gars/_system/wrappers/spatial-cluster-count/spatial_cluster_count.py:cmd_collect` | `n_obs <= 0` → `n_obs < 0` | `test_r164_boundaries` | `test_spot_count_boundary` (`FAILED (failures=1)`) | yes |
| P1a | 1 | `gars/_system/wrapperlib.py:input_key` | stage01-v1 `digest.update(chunk)` → `digest.update(chunk.rstrip(b"\n"))` | `test_r164_exact_bytes` | `test_stage01_key_is_the_ordered_concatenation`, `test_reproducibility_records_exact_input_digests` (`FAILED (failures=8)`) | yes |
| P1b | 1 | `gars/_system/tools/execution.py:config_holds` | `hashlib.sha256(path.read_bytes())` → `hashlib.sha256(path.read_bytes().strip() + b"\n")` | `test_r164_exact_bytes` | `test_config_rehash_refuses_whitespace_only_edits` (`FAILED (errors=3)`) | yes |
| P1c | 1 | `gars/_system/claims/evidence_check.py:artifact_problem` | `digest.update(chunk)` → `digest.update(chunk.rstrip())` | `test_r164_exact_bytes` | `test_claim_evidence_digest_is_exact` (`FAILED (failures=9)`) | yes |
| P2a | 2 | `gars/_system/wrapperlib.py:write_status` | `finally:` cleanup `os.unlink(temporary)` → `pass` | `test_r164_failure_recovery` | `test_status_write_failure_keeps_previous_status` (`FAILED (failures=2)`) | yes |
| P2b | 2 | `gars/_system/wrapperlib.py:harvest_cache` | `shutil.rmtree(tmp, ignore_errors=True)` → `pass` | `test_r164_failure_recovery` | `test_harvest_publishes_whole_and_leaves_no_incoming`, `test_harvest_lost_rename_leaves_no_partial_cache` (`FAILED (failures=2)`) | yes |
| P3a | 3 | `gars/_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py:build_params` | `spikein_fasta` and `spikein_bowtie2` values exchanged | `test_r164_params_mapping` | `test_cutandrun_every_field` (`FAILED (failures=1)`) | yes |
| P3b | 3 | `gars/_system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py:build_params` | `qc_min_counts` and `qc_min_genes` values exchanged | `test_r164_params_mapping` | `test_spatialvi_every_field` (`FAILED (failures=1)`) | yes |
| P3c | 3 | `gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py:cmd_prepare` | `min_genes=cfg["qc.min_genes"], min_cells=cfg["qc.min_cells"]` → exchanged | `test_r164_params_mapping` | `test_scrna_qc_cluster_thresholds` (`FAILED (failures=1)`) | yes |
| P4a | 4 | `gars/_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py:build_params` | `INDEX_PARAM[aligner]` → `INDEX_PARAM["bwa"]` | `test_r164_keyed_lookups` | `test_index_parameter_is_the_selected_aligners` (`FAILED (failures=3)`) | yes |
| P4b | 4 | `gars/_system/executorlib.py:nextflow_profile` | `... if value is None else value` → `... if not value else value` | `test_r164_keyed_lookups` | `test_executor_descriptor_by_backend` (`FAILED (failures=1)`) | yes |
| P4c | 4 | `gars/_system/workspace.py:design_columns` | `EXTRA_DESIGN_COLUMNS.get(assay, [])` → `.get(assay, EXTRA_DESIGN_COLUMNS["cutandrun"])` | `test_r164_keyed_lookups` | `test_design_columns_and_input_kind_by_assay` (`FAILED (failures=1)`) | yes |
| P5a | 5 | `gars/_system/wrappers/rnaseq-de/rnaseq_de.py:run_checks` | `counts_by_level.get(level, 0) < 2` → `< 1` | `test_r164_boundaries` | `test_contrast_level_needs_two_samples` (`FAILED (failures=1)`) | yes |
| P5b | 5 | `gars/_system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py:cmd_collect` | `proc.stat().st_size == 0` → `proc.stat().st_size < 0` | `test_r164_boundaries` | `test_processed_object_byte_boundary_and_raw_never_substitutes` (`FAILED (failures=1)`) | yes |
| P5c | 5 | `gars/_system/wrappers/rnaseq-de/rnaseq_de.py:check_table` | `> BH_RELATIVE_TOLERANCE * abs(corrected)` → `> 10 * BH_RELATIVE_TOLERANCE * abs(corrected)` | `test_r164_boundaries` | `test_bh_tolerance_on_both_sides` (`FAILED (failures=1)`) | yes |
| P5d | 5 | `gars/_system/wrapperlib.py:is_commit_pin` | `7 <= len(version) <= 40` → `6 <= len(version) <= 40` | `test_r164_boundaries` | `test_commit_pin_length_boundaries` (`FAILED (failures=1)`) | yes |

Counts: 5 survivors, all red; own plants per class 1: 3, 2: 2, 3: 3, 4: 3, 5: 4 (15), none of them in a function a survivor touches, all red; 20 of 20 red.
The plant driver is `<scratch>/plants/drive.py` (not committed); each of its runs took 1.5 to 3 minutes, most of it the `rsync` copies.

## Commands and summary lines

Run from the repository root with `TMPDIR`, `TEMP` and `TMP` at `<scratch>`, on macOS (Darwin 25.6.0).
`python3` on this machine's `PATH` is Python 3.8.2; `/usr/local/bin/python3` is Python 3.13.2.

New modules, `/usr/bin/time -p python3 gars/tests/<module>.py` (3.8.2):

| Module | Summary line | `real` (s) |
|---|---|---|
| `test_r164_exact_bytes` | `Ran 8 tests in 0.394s` / `OK` | 0.61 |
| `test_r164_failure_recovery` | `Ran 9 tests in 0.108s` / `OK` | 0.32 |
| `test_r164_params_mapping` | `Ran 11 tests in 0.280s` / `OK` | 0.49 |
| `test_r164_keyed_lookups` | `Ran 8 tests in 0.255s` / `OK` | 0.47 |
| `test_r164_boundaries` | `Ran 18 tests in 0.249s` / `OK` | 0.47 |

Sum: 2.36 s. The same five under `/usr/local/bin/python3` (3.13.2): `OK` each, 0.69 + 0.37 + 0.62 + 0.56 + 0.47 = 2.71 s.
All five files parse under the Python 3.6 grammar (`ast.parse(..., feature_version=(3, 6))` on the test files themselves).

Existing modules that exercise the same source files, `python3 gars/tests/<module>.py`:

| Module | Summary line | `real` (s) |
|---|---|---|
| `test_wrapperlib_prepare` | `Ran 1 test in 9.155s` / `OK` | 9.49 |
| `test_wrapper_contract` | `Ran 1 test in 7.695s` / `OK` | 8.00 |
| `test_executorlib_resume` | `Ran 2 tests in 0.156s` / `OK` | 0.53 |
| `test_downstream_keys` | `Ran 3 tests in 0.802s` / `OK` | 1.25 |
| `test_status_writer` | `Ran 10 tests in 9.637s` / `OK` | 10.00 |
| `test_execution_policy` | `Ran 7 tests in 45.867s` / `OK` | 46.26 |
| `test_integrity_records` | `Ran 2 tests in 0.549s` / `OK` | 0.85 |
| `test_planted_faults` | `Ran 3 tests in 16.988s` / `OK` | 17.38 |
| `test_emit_report` | `Ran 12 tests in 174.273s` / `OK` | 174.67 |
| `test_claim_constraints` | `Ran 21 tests in 0.007s` / `OK (skipped=18)` | 0.34 |

Checks:

- `python3 tests/check_contracts.py`: `14 contracts clean: sections, wait points, vocabulary.`
- `python3 tests/check_counts.py`: `suite: 757 tests, from unittest's loader`, then `clean — every current claim matches the suite` (`collected 360 tests from tests`, `collected 397 tests from gars/tests`).
- `python3 evals/test_harness.py` (3.8.2): `Ran 44 tests in 213.631s` / `FAILED (errors=13)`. Every error is an `AttributeError` for `str.removesuffix`, `str.removeprefix` or `ast.unparse`, which need Python 3.9 or later; this build changes nothing under `evals/`.
  The same command with `/usr/local/bin/python3` (3.13.2, the interpreter 0086 used): `Ran 44 tests in 192.574s` / `OK`.
- `python3 evals/check_results.py --controls --lexicon`: `clean — graded=1`.
- `python3 tests/test_decision_links_resolve.py`, after `bash docs/decisions/build_index.sh`: `Ran 3 tests in 1.629s` / `OK`, `citations: 376/376 resolve`.
- Row 11's record checker (`record_fields` and `decision_links` in `gars/_system/hooks/pre-commit`), called on 0087: `{'date': '2026-09-25', 'status': 'standing'}` and `True`.
- `git diff --stat 2a81999 HEAD -- gars/_system gars/02_bioinformatics gars/_references gars/_templates gars/.claude .github benchmarks evals`: prints nothing.

Not run, by the brief: the whole suite (`tests/run_tests.py`), the mutation runner and every `test_review_faults_*` module. The whole-suite runs (modes B and C, timed) are the lane's.

## Deviations, named

- **M10's hunk was one context line short as transcribed.** Its header says seven old lines and the text carried six; the next source line (`if n_clusters is not None and n_clusters <= 0:`) was added as context. The removed and added lines are the brief's, unchanged.
- **The shared-model precedent.** The brief says the shared model is "a named cost, as in 0013/0014"; in this repository 0013 and 0014 are the integrity and upgrade-path records and say nothing about models. 0087 cites 0108, which names the same cost for lane pg.
- **README count line.** The line said "703 tests … at the row 3 mutation-runner commit (0110)"; it now says 757 tests at this commit, which adds no skip, and keeps the skip figures as measured at 0110. Only that line and DEVELOPMENT's two count lines changed.
- **`evals/test_harness.py` on this `PATH`** needs Python 3.9 or later (see Commands); it was also run under 3.13.2.

## Residual gaps

- Class 2: `complete_manifest`'s own temporary write and the executor's record writes (`_save_record`) get no injected fault here; their callers are exercised by existing lifecycle suites.
- Class 4: the Slurm state map (`status_map`) needs `sacct` output and is not covered.
- Class 5: the rnaseq and atacseq collect gates' per-sample column checks are not re-covered here beyond the existing suite.
- The generated `submit.sh` guard is exercised with a stub body, not real Nextflow; that is 0050's stated limit.
- Producer and reviewer share a model (0087, Context).

## Owner rulings needed

None.
