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

## Review round 2 fixes

Dated 2026-09-25. Answers the independent review of `01eed13` (`docs/reviews/row3fu_review1.md`, left untracked and unchanged). The sections above are unchanged; 0087 carries a dated addendum after its last byte, and `bash docs/decisions/build_index.sh` was re-run (the index is byte-identical, since 0087's frontmatter did not change).
Rulings in this section are the lane's, under the owner's standing delegation of 23 Sep 2026.

### Findings

| Finding | Changed files | Test(s) | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| F1 MAJOR, class 2 reach | `gars/tests/test_r164_failure_recovery.py` (new class `CollectWriterRecoveryTests`) | `test_complete_manifest_interrupted_keeps_previous_manifest` (faults at `json.dump`, `fsync`, `os.replace`); `test_submission_record_interrupted_keeps_previous_record` (`executorlib._save_record`: unserialisable value, `fsync`, `os.replace`); `test_report_render_interrupted_keeps_previous_report` (`render_report.main`: at the write, at `os.replace`) | fixed; yes: G2a red on the manifest test, G2b red on the report test, M05 also red on the record test (plant table below) |
| F2 MAJOR, class 5 reach | new `gars/tests/test_r164_collect_gates.py`; `gars/tests/test_r164_boundaries.py` | collect gates of rnaseq, atacseq, chipseq, cutandrun, methylseq, rnaseq-de and scrna-qc-cluster (complete layout passes; each byte-gated artifact at 0 and 1 byte; each required artifact absent; each per-sample content check; scrna-qc-cluster totals at 1, 0, −1 and per-sample cells missing/zero/extra); `test_check_one_byte_boundary_in_every_mode`; `test_failed_exit_code_split` (`0:0`, `1:0`, `2:0`, `137:9`, `0:15`, empty); `test_a_contrast_needs_two_levels` (0, 1, 2 levels) | fixed; yes: G5a, G5b, G5c, G5d and Q5a–Q5f red |
| F3 MINOR, classes 1, 3, 4 one call away | `test_r164_exact_bytes.py`, `test_r164_params_mapping.py`, `test_r164_keyed_lookups.py` | `test_executor_script_digest_is_exact` (`executorlib._sha256` over the shared payload set); `test_legacy_prepared_key_is_the_exact_concatenation`; `test_scrnaseq_protocol_and_aligner_land_in_their_own_keys` and `test_peaks_type_gsize_and_mito_land_in_their_own_keys` (`configure.py apply`, two genomes with distinct values); `Stage01FormatByAssayTests` (rnaseq, methylseq, atacseq sheets); `SchedulerStateMapTests` (own map with distinct values, and the Slurm tokens as sacct prints them) | fixed; yes: G1a, G1c, G3b, Q3a, G4a, G4b red |
| F4 MINOR, README skip sentence | `README.md:322` | `python3 tests/check_counts.py` | fixed: the line now says 806 tests at 0087 (no new skip) and attributes the skip figures to 0110, "when the suite numbered 703"; written without the "N tests" shape so the guard does not read the historical figure as a current claim; clean |
| F5 NOTE, threshold read from the module | `test_r164_boundaries.py:test_login_node_threshold` | the same test | fixed: now also pins 10 × 1000³ bytes, the "~10 GB" that stages 00 and 01 state as policy, on both sides; the module-constant assertions stay |
| F6 NOTE, whole-list `build_params` equality | none | none | stays: the review requires no fix, and whole-list equality is what catches an exchange or a drop; a legitimately added parameter should make the test fail and be re-read |

Existing tests changed: none from before this item. One round-1 test of this item changed, `test_login_node_threshold` (F5): assertions added, none removed.

### Plant table, round 2

Same method as round 1 (driver `<scratch>/plants/drive_r2.py`, not committed): each plant in a fresh `rsync -a --exclude .git` copy under `<scratch>`, a one-occurrence string replacement asserted unique, only the named module run, the copy deleted. The unplanted copy printed `OK` for all six modules (10, 12, 13, 13, 22 and 33 tests). G-ids are the review's own faults, re-planted as it describes them; Q-ids are this round's own. G1b and G3a are not re-planted: the review found existing tests already kill them.

| Plant | Class | file:function | Diff, in one line | Module run | Failing test(s) | Red seen |
|---|---|---|---|---|---|---|
| M03 | survivor (1) | `wrapperlib.py:sha256` | `h.update(chunk)` → `h.update(chunk.rstrip())` | `test_r164_exact_bytes` | `test_sha256_is_the_digest_of_the_exact_bytes` and four others, as round 1 (`FAILED (failures=13)`) | yes |
| M05 | survivor (2) | `workspace.py:atomic_open` | `tmp.unlink()` → `path.unlink()` | `test_r164_failure_recovery` | round 1's three, plus `test_submission_record_interrupted_keeps_previous_record` (`FAILED (failures=1, errors=7)`) | yes |
| M07 | survivor (3) | `nfcore_rnaseq_wrapper.py:build_params` | the two index values exchanged | `test_r164_params_mapping` | `test_rnaseq_indices_are_not_exchanged` (`FAILED (failures=1)`) | yes |
| M08 | survivor (4) | `nfcore_scrnaseq_wrapper.py:supported_protocols` | `data.get(aligner)` → `data.get("simpleaf")` | `test_r164_keyed_lookups` | `test_scrnaseq_protocols_are_read_for_the_selected_aligner`, `test_scrnaseq_preflight_judges_protocol_against_its_own_aligner` (`FAILED (failures=7)`) | yes |
| M10 | survivor (5) | `spatial_cluster_count.py:cmd_collect` | `n_obs <= 0` → `n_obs < 0` | `test_r164_boundaries` | `test_spot_count_boundary` (`FAILED (failures=1)`) | yes |
| G1a | 1 | `executorlib.py:_sha256` | `read_bytes()` → `read_bytes().rstrip()` | `test_r164_exact_bytes` | `test_executor_script_digest_is_exact` (`FAILED (failures=8)`) | yes |
| G1c | 1 | `executorlib.py:prepared_key` (legacy branch) | `digest.update(chunk)` → `digest.update(chunk.rstrip())` | `test_r164_exact_bytes` | `test_legacy_prepared_key_is_the_exact_concatenation` (`FAILED (failures=1, errors=5)`) | yes |
| G2a | 2 | `wrapperlib.py:complete_manifest` | `finally:` `os.unlink(temporary)` → `os.unlink(str(path))` | `test_r164_failure_recovery` | `test_complete_manifest_interrupted_keeps_previous_manifest` (`FAILED (errors=4)`) | yes |
| G2b | 2 | `claims/render_report.py:main` | `finally:` `os.unlink(temporary)` → `pass` | `test_r164_failure_recovery` | `test_report_render_interrupted_keeps_previous_report` (`FAILED (failures=3)`) | yes |
| G3b | 3 | `configure.py:cmd_apply` (scrnaseq) | `protocol` and `aligner` values exchanged | `test_r164_params_mapping` | `test_scrnaseq_protocol_and_aligner_land_in_their_own_keys` (`FAILED (failures=3)`) | yes |
| Q3a | 3 | `configure.py:cmd_apply` (peaks) | `macs_gsize` and `mito_name` values exchanged | `test_r164_params_mapping` | `test_peaks_type_gsize_and_mito_land_in_their_own_keys` (`FAILED (failures=2)`) | yes |
| G4a | 4 | `executorlib.py:_scheduler_status` | `status_map.get(token)` → `.get("COMPLETED")` | `test_r164_keyed_lookups` | `test_each_token_reads_its_own_entry`, `test_slurm_tokens_as_sacct_prints_them` (`FAILED (failures=10)`) | yes |
| G4b | 4 | `stage01_samplesheet.py:validate_assay` | `FORMATS.get(assay)` → `FORMATS.get("rnaseq_bulk") if assay in FORMATS else None` | `test_r164_keyed_lookups` | `test_methylseq_sheet_has_no_rna_column`, `test_atacseq_sheet_names_the_group_and_replicate` (`FAILED (failures=2)`) | yes |
| G5a | 5 | `configure.py:cmd_contrasts` | `len(levels) < 2` → `< 1` | `test_r164_boundaries` | `test_a_contrast_needs_two_levels` (`FAILED (failures=1)`) | yes |
| G5b | 5 | `integrity.py:check_one` | `st_size == 0` → `st_size < 0` | `test_r164_boundaries` | `test_check_one_byte_boundary_in_every_mode` (`FAILED (failures=6)`) | yes |
| G5c | 5 | `nfcore_rnaseq_wrapper.py:cmd_collect` | counts `st_size == 0` → `st_size < 0` | `test_r164_collect_gates` | `test_counts_matrix_byte_boundary_and_sample_columns` (`FAILED (errors=1)`) | yes |
| G5d | 5 | `executorlib.py:_scheduler_status` | `int(exit_code) > 0` → `> 1` | `test_r164_boundaries` | `test_failed_exit_code_split` (`FAILED (failures=1)`) | yes |
| Q5a | 5 | `nfcore_atacseq_wrapper.py:cmd_collect` | multiqc `st_size == 0` → `< 0` | `test_r164_collect_gates` | `AtacseqCollectGateTests.test_each_byte_gate_at_zero_and_one_byte` (`FAILED (failures=1)`) | yes |
| Q5b | 5 | `nfcore_chipseq_wrapper.py:cmd_collect` | multiqc `st_size == 0` → `< 0` | `test_r164_collect_gates` | `ChipseqCollectGateTests.test_each_byte_gate_at_zero_and_one_byte` (`FAILED (failures=1)`) | yes |
| Q5c | 5 | `nfcore_cutandrun_wrapper.py:cmd_collect` | target-group peak check → `missing = []` | `test_r164_collect_gates` | `test_a_target_group_without_peaks_is_named` (`FAILED (failures=1)`) | yes |
| Q5d | 5 | `nfcore_methylseq_wrapper.py:cmd_collect` | per-sample coverage check → `missing = []` | `test_r164_collect_gates` | `test_a_sample_without_coverage_is_named` (`FAILED (failures=1)`) | yes |
| Q5e | 5 | `rnaseq_de.py:cmd_collect` | report `st_size == 0` → `< 0` | `test_r164_collect_gates` | `RnaseqDeCollectGateTests.test_each_byte_gate_at_zero_and_one_byte` (`FAILED (failures=1)`) | yes |
| Q5f | 5 | `scrna_qc_cluster.py:cmd_collect` | `n_cells_out <= 0` → `< 0` | `test_r164_collect_gates` | `test_cell_and_cluster_totals_at_one_zero_and_minus_one` (`FAILED (failures=1)`) | yes |

Counts: 5 survivors re-checked, all red; 18 plants outside round 1's coverage map, all red (class 1: 2, class 2: 2, class 3: 2, class 4: 2, class 5: 10); 23 of 23 red. The driver run took 1 min 50 s.
This is development evidence, not a mutation score; the review's F1–F3 survivals were "in the modules it ran", and these kills are likewise in the named modules only.

### Commands and summary lines, round 2

From the repository root with `TMPDIR`, `TEMP` and `TMP` at `<scratch>`, macOS, `python3` = 3.8.2.

| Module | Summary line | `real` (s) |
|---|---|---|
| `test_r164_exact_bytes` | `Ran 10 tests in 0.414s` / `OK` | 0.61 |
| `test_r164_failure_recovery` | `Ran 12 tests in 0.209s` / `OK` | 0.38 |
| `test_r164_params_mapping` | `Ran 13 tests in 0.274s` / `OK` | 0.45 |
| `test_r164_keyed_lookups` | `Ran 13 tests in 0.313s` / `OK` | 0.50 |
| `test_r164_boundaries` | `Ran 22 tests in 0.260s` / `OK` | 0.44 |
| `test_r164_collect_gates` (new) | `Ran 33 tests in 0.646s` / `OK` | 0.82 |

Sum: 3.20 s for the six modules (103 tests, no skip). Under `/usr/local/bin/python3` (3.13.2) each printed `OK` with the same counts. All six files parse under `ast.parse(..., feature_version=(3, 6))`.

Existing modules over the newly covered sources (no source changed, so these characterise the base):

| Module | Summary line | `real` (s) |
|---|---|---|
| `gars/tests/test_render_report.py` | `Ran 14 tests in 50.635s` / `OK` | 50.80 |
| `gars/tests/test_integrity_records.py` | `Ran 2 tests in 0.290s` / `OK` | 0.47 |
| `gars/tests/test_executorlib_resume.py` | `Ran 2 tests in 0.079s` / `OK` | 0.27 |
| `gars/tests/test_lifecycle_executor.py` | `Ran 16 tests in 5.752s` / `OK` | 5.95 |
| `gars/tests/test_failure_classification.py` | `Ran 5 tests in 1.449s` / `OK` | 1.65 |
| `gars/tests/test_no_false_completion.py` | `Ran 5 tests in 0.595s` / `OK` | 0.80 |
| `tests/test_stage01_design.py` | `Ran 23 tests in 8.373s` / `OK (skipped=1)` (the skip is the pre-existing sealed-fixture skip) | 8.54 |

Checks:

- `python3 tests/check_contracts.py`: `14 contracts clean: sections, wait points, vocabulary.`
- `python3 tests/check_counts.py`: `collected 360 tests from tests`, `collected 446 tests from gars/tests`, `suite: 806 tests, from unittest's loader`, `clean — every current claim matches the suite`.
- `/usr/local/bin/python3 evals/test_harness.py` (3.13.2): `Ran 44 tests in 191.146s` / `OK`. Not re-run under 3.8.2 this round; round 1 showed it needs Python 3.9 or later there, and nothing under `evals/` changed.
- `python3 evals/check_results.py --controls --lexicon`: `clean — graded=1`.
- `python3 tests/test_decision_links_resolve.py`, after `bash docs/decisions/build_index.sh`: `Ran 3 tests in 1.390s` / `OK`, `citations: 376/376 resolve`.
- `git diff --stat 2a81999 HEAD -- gars/_system gars/02_bioinformatics gars/_references gars/_templates gars/.claude .github benchmarks evals`: prints nothing (checked after the commit).

Not run, by the brief: the whole suite, the mutation runner and every `test_review_faults_*` module.

## Owner rulings needed

None.

## Residual gaps after round 2

- The kills above are in the named modules only; whether the whole suite stays green in modes B and C, and its added wall time on the lane's node, are the lane's to measure.
- The scrnaseq, spatialvi and spatial-cluster-count collect gates are covered as round 1 left them. Every wrapper's collect is exercised with the lifecycle writers stubbed.
- `executorlib._scheduler_status` is exercised through a stub status command (`/bin/echo`), not `sacct`; the local backend's `_local_status` is covered by the existing lifecycle suites, not here.
- `render_report.main` is covered at the write and at `os.replace`; a fault inside `render` itself is the existing `test_render_report`'s.
- Producer and reviewer share a model (0087, Context).

## Review round 3 fixes

Dated 2026-09-25. Answers the independent review of `51b0e47` (`docs/reviews/row3fu_review2.md`, left untracked and unchanged). The sections above are unchanged; 0087 carries a second dated addendum after its last byte, and `bash docs/decisions/build_index.sh` was re-run (the index is byte-identical, since 0087's frontmatter did not change).
Rulings in this section are the lane's, under the owner's standing delegation of 23 Sep 2026.

### Findings

| Finding | Changed files | Test(s) | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| F1 MAJOR, class 2 reach stops at the named writers | `gars/tests/test_r164_failure_recovery.py` (new class `CallSiteRecoveryTests`, helper `replace_refused_for`) | `test_refused_first_submission_leaves_no_record` and `test_refused_retry_restores_the_failed_record` (`executorlib.submit` with `_submit_once` returning a `SubmissionFailure`: first submission leaves no record and the stage `STALE`; a retry leaves the failed record's exact bytes, the listing and `STATUS` unchanged, and the next retry's lineage names only the first attempt); `test_emit_report_leaves_no_snapshot_on_any_exit` (`emit_report.main --from-db`: preflight refuses, preflight raises, renderer fails, export fails, success; each leaves only the previous `report.md`); `test_stage01_interrupted_keeps_each_previous_file` (stage 01 `main --force` with `os.replace` refused at the sheet, the design table and the check record in turn); `test_finalize_interrupted_keeps_each_previous_file` (stage 00 `finalize` refused at `samples.csv` on the first run, then at `files.csv`, `CONTEXT.md` and `HISTORY.md`) | fixed; yes: N2a, N2b, N2c and R2a–R2e red (plant table below) |
| F2 MINOR, stage 01 control columns | `gars/tests/test_r164_keyed_lookups.py` (`Stage01FormatByAssayTests`: `fixture`/`emitted` take a samples table and drop the fastq columns by name) | `test_chipseq_control_columns_are_the_controls_group_and_replicate` (crossed controls: IP rep 1 → input rep 2, so own group, own replicate, control group and control replicate all differ); `test_cutandrun_control_is_each_rows_own_igg_group` (two targets with two IgG groups) | fixed; yes: N3a, R3a and R3b red |
| F3 MINOR, "eight further plants" | `docs/decisions/0087-row-3-followup-suite-strengthening.md` (appended addendum) | `python3 tests/test_decision_links_resolve.py` | fixed by a dated correction in the new addendum ("should read seven"); the round-1 addendum's bytes are not edited, as the round's rules require |
| F4 MINOR, `touches` misses `test_r164_collect_gates.py` | none | none | **waits on the owner**: both fixes the review offers are closed to this round (the frontmatter is 0087's existing bytes; a follow-up record needs a record number, and 0087 is this lane's only one). See `## Owner rulings needed` below |
| F5 NOTE, N1a near-equivalent | none | none | stays: the review requires no fix; the name is derived by the same function on write and read and the content is checked separately, and the optional assertion it suggests belongs in an existing approval test, which this lane may change only if it is wrong |

Existing tests changed: none from before this item. Two helpers of this item's own round-1 class changed, `Stage01FormatByAssayTests.fixture` and `.emitted`: an optional samples table was added and the fastq columns are dropped by name instead of by position (identical rows for the three existing formats); the three existing tests are unchanged and still pass.

### Plant table, round 3

Same method as rounds 1 and 2 (driver `<scratch>/plants/drive_r3.py`, not committed): each plant in a fresh `rsync -a --exclude .git` copy under `<scratch>`, a one-occurrence string replacement asserted unique, only the named module run, the copy deleted. The unplanted copy printed `OK` for all six modules. N-ids are the review's own fresh faults, re-planted as it describes them; R-ids are this round's own, each in a function no earlier test of this item names. The whole driver run took 1 min 10 s.

| Plant | Class | file:function | Diff, in one line | Module run | Failing test(s) | Red seen |
|---|---|---|---|---|---|---|
| M03 | survivor (1) | `wrapperlib.py:sha256` | `h.update(chunk)` → `h.update(chunk.rstrip())` | `test_r164_exact_bytes` | `test_sha256_is_the_digest_of_the_exact_bytes` and four others (`FAILED (failures=13)`) | yes |
| M05 | survivor (2) | `workspace.py:atomic_open` | `tmp.unlink()` → `path.unlink()` | `test_r164_failure_recovery` | round 2's four, plus `test_stage01_interrupted_keeps_each_previous_file`, `test_finalize_interrupted_keeps_each_previous_file` (`FAILED (failures=2, errors=10)`) | yes |
| M07 | survivor (3) | `nfcore_rnaseq_wrapper.py:build_params` | the two index values exchanged, by hand | `test_r164_params_mapping` | `test_rnaseq_indices_are_not_exchanged` (`FAILED (failures=1)`) | yes |
| M08 | survivor (4) | `nfcore_scrnaseq_wrapper.py:supported_protocols` | `data.get(aligner)` → `data.get("simpleaf")` | `test_r164_keyed_lookups` | `test_scrnaseq_protocols_are_read_for_the_selected_aligner`, `test_scrnaseq_preflight_judges_protocol_against_its_own_aligner` (`FAILED (failures=7)`) | yes |
| M10 | survivor (5) | `spatial_cluster_count.py:cmd_collect` | `n_obs <= 0` → `n_obs < 0` | `test_r164_boundaries` | `test_spot_count_boundary` (`FAILED (failures=1)`) | yes |
| N2a | 2 | `claims/emit_report.py:main` | on a preflight refusal, `temporary = None` before `return code` | `test_r164_failure_recovery` | `test_emit_report_leaves_no_snapshot_on_any_exit` (`FAILED (failures=5)`) | yes |
| N2b | 2 | `stage01_samplesheet.py:write_assay` | design table `ws.atomic_open(design)` → plain `open(str(design), "w", ...)` | `test_r164_failure_recovery` | `test_stage01_interrupted_keeps_each_previous_file` (`FAILED (failures=2)`) | yes |
| N2c | 2 | `executorlib.py:submit` | on a refused retry, `_save_record(path, retry)` → `pass` | `test_r164_failure_recovery` | `test_refused_retry_restores_the_failed_record` (`FAILED (failures=1)`) | yes |
| N3a | 3 | `stage01_samplesheet.py:write_assay` (`lookup:control_group`) | the control's `group` → its `replicate` | `test_r164_keyed_lookups` | `test_chipseq_control_columns_are_the_controls_group_and_replicate` (`FAILED (failures=1)`) | yes |
| R2a | 2 | `executorlib.py:submit` | on a refused first submission, `path.unlink()` → `pass` | `test_r164_failure_recovery` | `test_refused_first_submission_leaves_no_record` (`FAILED (failures=1)`) | yes |
| R2b | 2 | `stage00_register.py:cmd_finalize` | `samples.csv` `ws.atomic_open` → plain `open` | `test_r164_failure_recovery` | `test_finalize_interrupted_keeps_each_previous_file` (`FAILED (failures=1)`) | yes |
| R2c | 2 | `stage01_samplesheet.py:write_assay` | design-check record `ws.atomic_open(record)` → plain `open` | `test_r164_failure_recovery` | `test_stage01_interrupted_keeps_each_previous_file` (`FAILED (failures=1)`) | yes |
| R2d | 2 | `stage00_register.py:cmd_finalize` | `CONTEXT.md`/`HISTORY.md` placeholder write `ws.atomic_open` → plain `open` | `test_r164_failure_recovery` | `test_finalize_interrupted_keeps_each_previous_file` (`FAILED (failures=2)`) | yes |
| R2e | 2 | `claims/emit_report.py:main` | on a renderer failure, `temporary = None` | `test_r164_failure_recovery` | `test_emit_report_leaves_no_snapshot_on_any_exit` (`FAILED (failures=3)`) | yes |
| R3a | 3 | `stage01_samplesheet.py:write_assay` (`lookup:control_replicate`) | the control's replicate → the row's own (`d.get("replicate", "")`) | `test_r164_keyed_lookups` | `test_chipseq_control_columns_are_the_controls_group_and_replicate` (`FAILED (failures=1)`) | yes |
| R3b | 3 | `stage01_samplesheet.py:FORMATS["cutandrun"]` | `("control", "design:control")` → `("control", "design:group")` | `test_r164_keyed_lookups` | `test_cutandrun_control_is_each_rows_own_igg_group` (`FAILED (failures=1)`) | yes |

Counts: 5 survivors re-checked, all red; 11 plants outside the earlier coverage map, all red (class 2: 8, class 3: 3); 16 of 16 red.
This is development evidence, not a mutation score; these kills are in the named modules only.

### Commands and summary lines, round 3

From the repository root with `TMPDIR`, `TEMP` and `TMP` at `<scratch>`, macOS, `python3` = 3.8.2.

| Module | Summary line | `real` (s) |
|---|---|---|
| `test_r164_exact_bytes` | `Ran 10 tests in 0.496s` / `OK` | 0.71 |
| `test_r164_failure_recovery` (changed) | `Ran 17 tests in 0.607s` / `OK` | 0.84 |
| `test_r164_params_mapping` | `Ran 13 tests in 0.289s` / `OK` | 0.49 |
| `test_r164_keyed_lookups` (changed) | `Ran 15 tests in 0.384s` / `OK` | 0.59 |
| `test_r164_boundaries` | `Ran 22 tests in 0.302s` / `OK` | 0.51 |
| `test_r164_collect_gates` | `Ran 33 tests in 0.743s` / `OK` | 0.95 |

Sum: 4.09 s for the six modules (110 tests, no skip). Under `/usr/local/bin/python3` (3.13.2) the two changed modules printed `Ran 17 tests in 0.409s` / `OK` and `Ran 15 tests in 0.254s` / `OK`. All six files parse under `ast.parse(..., feature_version=(3, 6))`.

Existing modules over the newly reached sources (no source changed, so these characterise the base):

| Module | Summary line | `real` (s) |
|---|---|---|
| `gars/tests/test_emit_report.py` | `Ran 12 tests in 127.012s` / `OK` | 127.22 |
| `gars/tests/test_claim_constraints.py` | `Ran 21 tests in 0.004s` / `OK (skipped=18)` (pre-existing skips) | 0.19 |
| `gars/tests/test_lifecycle_executor.py` | `Ran 16 tests in 5.259s` / `OK` | 5.44 |
| `gars/tests/test_failure_classification.py` | `Ran 5 tests in 1.269s` / `OK` | 1.45 |
| `gars/tests/test_executorlib_resume.py` | `Ran 2 tests in 0.075s` / `OK` | 0.25 |
| `tests/test_stage01_design.py` | `Ran 23 tests in 7.264s` / `OK (skipped=1)` (the pre-existing sealed-fixture skip) | 7.42 |

`stage00_register`'s own existing tests are inline in `tests/run_tests.py`, which this lane does not run on this machine.

Checks:

- `python3 tests/check_contracts.py`: `14 contracts clean: sections, wait points, vocabulary.`
- `python3 tests/check_counts.py`: `collected 360 tests from tests`, `collected 453 tests from gars/tests`, `suite: 813 tests, from unittest's loader`, `clean — every current claim matches the suite` (after README line 322 and DEVELOPMENT lines 156 and 175 were moved from 806 to 813; nothing else in those files changed).
- `/usr/local/bin/python3 evals/test_harness.py` (3.13.2): `Ran 44 tests in 165.976s` / `OK`.
- `python3 evals/check_results.py --controls --lexicon`: `clean — graded=1`.
- `python3 tests/test_decision_links_resolve.py`, after `bash docs/decisions/build_index.sh`: `Ran 3 tests in 1.460s` / `OK`, `citations: 376/376 resolve`.
- `git diff --stat 2a81999 HEAD -- gars/_system gars/02_bioinformatics gars/_references gars/_templates gars/.claude .github benchmarks evals`: prints nothing (checked after the commit).

Not run, by the brief: the whole suite, the mutation runner and every `test_review_faults_*` module.

## Owner rulings needed

- **F4, 0087's `touches` and `gars/tests/test_r164_collect_gates.py`.** The index cannot find the module's record. The review offers two fixes: (a) while 0087 is still unmerged, add the path to its `touches` and re-run `bash docs/decisions/build_index.sh`; (b) if the lane rules that the frontmatter is frozen, a one-line follow-up record that touches the module. This round's rules close both: 0087's existing bytes are never edited, and no record number other than 0087 is this lane's to write. Which one, if either, is the owner's (or the lane's) to decide.

## Residual gaps after round 3

- The kills above are in the named modules only; whether the whole suite stays green in modes B and C, and its added wall time on the lane's node, are the lane's to measure.
- Class 2's call-site faults are injected at `os.replace` by destination name; a fault at `fsync` or mid-body inside stage 00, stage 01 and `emit_report` is covered only through `atomic_open`'s own tests.
- `executorlib.submit`'s refusal branches are driven with `_submit_once` stubbed, not through a real scheduler.
- `test_r164_collect_gates.py` is not in 0087's `touches` or the index (F4, above).
- Producer and reviewer share a model (0087, Context).

## Review round 4 fixes

Dated 2026-09-25. This section answers the lane's extra round (`docs/reviews/row3fu_lane_extra_round.md`, left untracked and unchanged) and builds on fix round 3 (`6c89d9a`) as it stands. The sections above are unchanged. 0087 carries a third dated addendum after its last byte, 0111 is new, and `bash docs/decisions/build_index.sh` was re-run: the index gains 0111's row and nothing else changes.
Rulings in this section are the lane's, under the owner's standing delegation of 23 Sep 2026.

### Findings

| Finding | Changed files | Test(s) | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| E1 MINOR, `test_r164_collect_gates.py` is in no record's `touches` (the lane's ruling (b) on round 3's F4) | `docs/decisions/0111-row-3-followup-suite-index-addendum.md` (new, frontmatter in 0087's shape; `touches` lists `gars/tests/test_r164_collect_gates.py` and this round's `gars/tests/test_r164_writer_recovery.py`); `docs/decisions/CONTEXT.md` (regenerated) | `python3 tests/test_decision_links_resolve.py`; the index row for 0111 names both paths | fixed. 0087's bytes are not edited: its round-3 bytes are a byte-identical prefix of the new file (checked with a byte comparison against a copy taken before the append). Red-on-fault: not applicable (a record) |
| E2 MAJOR, class 2 by principle, not per function | `gars/tests/test_r164_writer_recovery.py` (new) | `WriterRecoveryTests`: one generated test per table row (46 rows, 84 destination files, 417 fault runs as subtests) plus `test_the_table_names_every_wrapper` | fixed; yes: W1–W12 (twelve writers no earlier test named), N2b, R2b, R2d and M05 all went red on the new module in disposable copies (plant table below) |

Existing tests changed: none.

### How the table works

Each row is `Writer(name, setup, destinations, ...)`. `setup` builds a fixture under a fresh temporary folder and returns a zero-argument call that drives the entry point through its public interface: the function itself, the wrapper's `cmd_check`, `cmd_prepare` or `cmd_collect`, or the stage helper's `main`.
A row that is primed runs cleanly once. Then, for each destination file and each step, the row runs again with one fault. Every such run must meet three conditions:

- the fault fired, so the step was actually reached;
- the fault surfaced, as an exception or a result other than the row's success value;
- the destination's bytes equal the prior bytes exactly, or it is still absent on a first write, and the set of files in the whole fixture tree is unchanged.

The steps are:

- `open`: an open-for-write of the destination or of its temporary is refused (`builtins.open`, `io.open` and `tempfile.mkstemp`).
- `write`: the first write lands half its data and then raises.
- `fsync`: the fsync is refused on the file descriptor opened for that destination.
- `replace`: `os.replace` or `os.rename` to that destination is refused.
- `first-write`: the destination is removed first, then the write fault is injected.
- Named extras: `prepare_manifest_facts` raising before `write_reproducibility` writes anything, `write_reproducibility` raising inside each nf-core `prepare`, and the hook installer's copy (half-written) and chmod.

Faults are matched by the destination's folder and name, including the `name.tmp` and `.stem-XXXX` temporaries, and never by the writer. A writer that bypasses `ws.atomic_open` for a plain `open` or `write_text` therefore meets the same fault on its own file. That is what W1–W12 plant.
Two fixture shortcuts are used, each named in the module. `run_checks` and `build_params` are stubbed in the wrapper rows, because they are class 3's, and the collect-side lifecycle writers are stubbed by the shared collect harness, as in rounds 1–3. Inside `prepare`, `git rev-parse` on the pipeline checkout is answered in-process, because the commit value is not observed and one subprocess per fault run cost about 5 s. `test_the_table_names_every_wrapper` fails if a wrapper directory on disk has no `prepare` or `collect` row, or no `check` row when its check writes a record.

### Writer inventory

The inventory was derived by searching `gars/_system/` for `atomic_open`, `os.replace`, `os.rename`, `.rename(`, `open(..., 'w'/'wb'/'a'/'x')`, `write_text`, `write_bytes`, `json.dump(`, `shutil.move/copy*`, `mkstemp` and `NamedTemporaryFile`, and its shell scripts for `>` redirections.

In the table (46 rows):

| Entry point | Destinations |
|---|---|
| `wrapperlib.write_params_yaml`, `write_submit_sh` | `params.yaml`, `submit.sh` |
| `wrapperlib.write_reproducibility` | `submit.sh`, `reproducibility/manifest.json`, `reproducibility/commands.sh` |
| `wrapperlib.complete_output_index`, `write_status`, `complete_manifest`, `harvest_cache` | `OUTPUTS.tsv`, `STATUS`, `reproducibility/manifest.json`, `PROVENANCE` |
| `executorlib._save_record`, `record_failure` | the submission record; `logs/failure-<job>.log` and `.class` |
| `stage00_register.write_dataset_record`; `finalize` (re-run; first run) | `00_data/dataset.tsv`; `files.csv`, `CONTEXT.md`, `HISTORY.md`; `samples.csv` |
| `stage01_samplesheet main` | the samplesheet, the design table, the design-check record |
| `stage03_analysis create` | `PLAN.md` |
| `configure.py apply`; `adapt_counts.py main` | `_config/<assay>.yaml`; `adapted/counts_gene.tsv`, `adapted/gene_id_to_name.tsv` |
| `hooks/install.py install_hook` | the installed `pre-push` (with rollback to the user's own hook) |
| `cmd_check` of the seven nf-core wrappers, `scrna-qc-cluster` and `spatial-cluster-count` | `preflight/check_result.json` |
| `cmd_prepare` of all ten wrappers | `params.yaml` (nf-core), `scripts/<script>.py` (downstream), `submit.sh`, `reproducibility/manifest.json`, `reproducibility/commands.sh` |
| `cmd_collect` of all ten wrappers | `OUTPUTS.tsv` |

Left out, with the reason for each:

| Writer | Reason |
|---|---|
| `workspace.atomic_open`, `claims/render_report.py main`, `claims/emit_report.py main`, `executorlib.submit` (refusal branches) | Already covered by `test_r164_failure_recovery.py` at each step. `render_report` writes through `NamedTemporaryFile`, which opens by descriptor and so is outside this injector; that module injects its write and replace faults directly. |
| `rnaseq-de cmd_check` | It writes no file. |
| `executorlib._local_submit`, job record `jobs/<pid>.json` (plain `open`, `w`) | A fault leaves a partial record, and the job has already started. Probed; see `## Owner rulings needed`. |
| `executorlib._analysis_launcher`, `run/launch-<uuid>.sh` (`write_bytes`) | A fault leaves a partial launcher behind. Probed; see `## Owner rulings needed`. |
| `executorlib._submit_analysis`, `ANALYSIS_SUBMISSIONS` (append plus fsync) | An append log never rewrites prior bytes. A fault mid-append leaves a torn final line, by inspection only (not probed); the same question is in `## Owner rulings needed`. |
| `stage03_analysis` `approve` (`PLAN.md` and the `O_EXCL` approval record) and `verify` (`OUTPUTS.tsv`, `STATUS`); `executorlib` action approval records (`O_EXCL`) | The approval store is derived from the installed workspace (its parent folder), so driving these writes outside any fixture tree. `O_EXCL` creation refuses to overwrite by construction, and the code's own comment says "a crash leaves an invalid record, never approval". These writers are owned by `test_approval_forgery.py` and `test_stage03_execution.py`. |
| `stage00_register` project creation (`copytree` of the stamp, `_config` seeding via `write_text` and `copy2`) | Creation-only, into a project folder that did not exist, so there are no prior bytes. A fault mid-creation leaves a partial project, by inspection only; the same question is in `## Owner rulings needed`. |
| `authoring/create_bioinformatics_skill.py` (`write_text` of a new wrapper's source and `SKILL.md`) | A developer scaffolding tool that writes new source files, not a recorded state of any project. |
| The generated job scripts' own writes (`versions.json`, `report.md`, the markers table, `summary.json`) | These run inside the job with numpy, scanpy or anndata, which the offline suite does not have. Their outputs are what the collect gates (classes 5 and 2) judge. |
| `build_projects_index.sh` (`> "$OUT"`) | A generated render, rebuilt on every session boot, and not a record (`gars/CLAUDE.md`, "State"). |

### Plant table, round 4

Same method as rounds 1–3. The driver is `<scratch>/plants/drive_r4.py` and is not committed. Each plant gets a fresh `rsync -a --exclude .git` copy under `<scratch>` and a one-occurrence string replacement asserted unique. Only the named module is run, and the copy is deleted afterwards. The unplanted copy printed `OK` for all seven R-164 modules. W-ids are this round's plants, each in a writer that no earlier test of this item named. N2b, R2b and R2d are round 3's plants, re-run against the new module, and M05w is M05 run against the new module. The whole driver run took 2 min 12 s.

| Plant | Class | file:function | Diff, in one line | Module run | Failing test(s) | Red seen |
|---|---|---|---|---|---|---|
| M03 | survivor (1) | `wrapperlib.py:sha256` | `h.update(chunk)` → `h.update(chunk.rstrip())` | `test_r164_exact_bytes` | `test_sha256_is_the_digest_of_the_exact_bytes` and four others (`FAILED (failures=13)`) | yes |
| M05 | survivor (2) | `workspace.py:atomic_open` | `tmp.unlink()` → `path.unlink()` | `test_r164_failure_recovery` | six tests (`FAILED (failures=2, errors=10)`) | yes |
| M07 | survivor (3) | `nfcore_rnaseq_wrapper.py:build_params` | the two index values exchanged, by hand | `test_r164_params_mapping` | `test_rnaseq_indices_are_not_exchanged` (`FAILED (failures=1)`) | yes |
| M08 | survivor (4) | `nfcore_scrnaseq_wrapper.py:supported_protocols` | `data.get(aligner)` → `data.get("simpleaf")` | `test_r164_keyed_lookups` | `test_scrnaseq_protocols_are_read_for_the_selected_aligner`, `test_scrnaseq_preflight_judges_protocol_against_its_own_aligner` (`FAILED (failures=7)`) | yes |
| M10 | survivor (5) | `spatial_cluster_count.py:cmd_collect` | `n_obs <= 0` → `n_obs < 0` | `test_r164_boundaries` | `test_spot_count_boundary` (`FAILED (failures=1)`) | yes |
| M05w | survivor (2) | `workspace.py:atomic_open` | as M05 | `test_r164_writer_recovery` | 43 of the 47 tests (`FAILED (failures=174, errors=37)`) | yes |
| W1 | 2 | `nfcore_atacseq_wrapper.py:cmd_check` | `check_result.json` `ws.atomic_open` → plain `open(..., "w")` | `test_r164_writer_recovery` | `test_nfcore_atacseq_wrapper_check` (`FAILED (failures=4)`) | yes |
| W2 | 2 | `spatial_cluster_count.py:cmd_collect` | `OUTPUTS.tsv` `ws.atomic_open` → plain `open` | `test_r164_writer_recovery` | `test_spatial_cluster_count_collect` (`FAILED (failures=4)`) | yes |
| W3 | 2 | `executorlib.py:record_failure` | `wl.ws.atomic_open(logs / ...)` → plain `open` | `test_r164_writer_recovery` | `test_executorlib_record_failure` (`FAILED (failures=8)`) | yes |
| W4 | 2 | `configure.py:cmd_apply` | `ws.atomic_open(cfg, newline=None)` → plain `open` | `test_r164_writer_recovery` | `test_configure_py_apply` (`FAILED (failures=3)`) | yes |
| W5 | 2 | `adapt_counts.py:main` | `gene_id_to_name.tsv` `ws.atomic_open` → plain `open` | `test_r164_writer_recovery` | `test_adapt_counts_py_main` (`FAILED (failures=4)`) | yes |
| W6 | 2 | `hooks/install.py:install_hook` | rollback `previous.rename(target)` → `pass` | `test_r164_writer_recovery` | `test_hooks_install_py_install_hook` (`FAILED (failures=3)`) | yes |
| W7 | 2 | `wrapperlib.py:write_reproducibility` | `commands.sh` `ws.atomic_open` → plain `open` | `test_r164_writer_recovery` | the ten `prepare` rows and `test_wrapperlib_write_reproducibility` (`FAILED (failures=44)`) | yes |
| W8 | 2 | `stage03_analysis.py:cmd_create` | `PLAN.md` `ws.atomic_open` → plain `open` | `test_r164_writer_recovery` | `test_stage03_analysis_create` (`FAILED (failures=3)`) | yes |
| W9 | 2 | `wrapperlib.py:complete_output_index` | `OUTPUTS.tsv` `ws.atomic_open` → plain `open` | `test_r164_writer_recovery` | `test_wrapperlib_complete_output_index` (`FAILED (failures=3)`) | yes |
| W10 | 2 | `rnaseq_de.py:cmd_prepare` | `scripts/run_de.py` `ws.atomic_open` → plain `open` | `test_r164_writer_recovery` | `test_rnaseq_de_prepare` (`FAILED (failures=4)`) | yes |
| W11 | 2 | `stage00_register.py:write_dataset_record` (first write) | `ws.atomic_open(path, mode=...)` → plain `open` | `test_r164_writer_recovery` | `test_stage00_register_write_dataset_record` (`FAILED (failures=3)`) | yes |
| W12 | 2 | `nfcore_methylseq_wrapper.py:cmd_collect` | `OUTPUTS.tsv` `ws.atomic_open` → plain `open` | `test_r164_writer_recovery` | `test_nfcore_methylseq_wrapper_collect` (`FAILED (failures=4)`) | yes |
| N2b | 2 | `stage01_samplesheet.py:write_assay` | design table `ws.atomic_open` → plain `open` | `test_r164_writer_recovery` | `test_stage01_samplesheet_main` (`FAILED (failures=4)`) | yes |
| R2b | 2 | `stage00_register.py:cmd_finalize` | `samples.csv` `ws.atomic_open` → plain `open` | `test_r164_writer_recovery` | `test_stage00_register_finalize__first_run` (`FAILED (failures=3)`) | yes |
| R2d | 2 | `stage00_register.py:cmd_finalize` | `CONTEXT.md`/`HISTORY.md` `ws.atomic_open` → plain `open` | `test_r164_writer_recovery` | `test_stage00_register_finalize__re_run` (`FAILED (failures=6)`) | yes |

Counts:

- The 5 survivors were re-checked on their own modules, and all went red.
- 12 class-2 plants were made in writers that no earlier test named, and all went red.
- 4 earlier plants (M05, N2b, R2b, R2d) were re-run against the new module, and all went red.
- In total, 21 of 21 plants went red.

This is development evidence, not a mutation score, and these kills are in the named modules only.

### Commands and summary lines, round 4

All commands were run from the repository root with `TMPDIR`, `TEMP` and `TMP` at `<scratch>`, on macOS, with `python3` = 3.8.2.

| Module | Summary line | `real` (s) |
|---|---|---|
| `test_r164_exact_bytes` | `Ran 10 tests in 0.440s` / `OK` | 0.62 |
| `test_r164_failure_recovery` | `Ran 17 tests in 0.589s` / `OK` | 0.79 |
| `test_r164_params_mapping` | `Ran 13 tests in 0.267s` / `OK` | 0.46 |
| `test_r164_keyed_lookups` | `Ran 15 tests in 0.350s` / `OK` | 0.55 |
| `test_r164_boundaries` | `Ran 22 tests in 0.291s` / `OK` | 0.49 |
| `test_r164_collect_gates` | `Ran 33 tests in 0.748s` / `OK` | 0.95 |
| `test_r164_writer_recovery` (new) | `Ran 47 tests in 4.090s` / `OK` | 4.31 |

The seven modules sum to 8.17 s (157 tests, no skip). The new module's wall time varied between 2.9 s and 4.5 s across runs on this shared machine. Under `/usr/local/bin/python3` (3.13.2) it printed `Ran 47 tests in 3.955s` / `OK`. The new file parses under `ast.parse(..., feature_version=(3, 6))`.

Existing modules over the newly reached sources:

| Module | Summary line | `real` (s) |
|---|---|---|
| `gars/tests/test_pre_push.py` (the hook installer) | `Ran 7 tests in 14.445s` / `OK` | 14.61 |
| `gars/tests/test_lifecycle_executor.py` | `Ran 16 tests in 6.005s` / `OK` | 6.20 |
| `gars/tests/test_wrapper_contract.py` | `Ran 1 test in 3.547s` / `OK` | 3.70 |

Checks:

- `python3 tests/check_contracts.py`: `14 contracts clean: sections, wait points, vocabulary.`
- `python3 tests/check_counts.py`: `collected 360 tests from tests`, `collected 500 tests from gars/tests`, `suite: 860 tests, from unittest's loader`, `clean — every current claim matches the suite`. This was after README line 322 and DEVELOPMENT lines 156 and 175 were moved from 813 to 860; nothing else in those files changed.
- `/usr/local/bin/python3 evals/test_harness.py` (3.13.2): `Ran 44 tests in 166.222s` / `OK`.
- `python3 evals/check_results.py --controls --lexicon`: `clean — graded=1`.
- `python3 tests/test_decision_links_resolve.py`, after `bash docs/decisions/build_index.sh`: `Ran 3 tests in 1.435s` / `OK`, `citations: 376/376 resolve`.
- `git diff --stat 2a81999 HEAD -- gars/_system gars/02_bioinformatics gars/_references gars/_templates gars/.claude .github benchmarks evals`: prints nothing (checked after the commit).

Not run, as the brief requires: the whole suite, the mutation runner and every `test_review_faults_*` module. The round-4 plant driver ran longer than the tool's two-minute foreground limit, and the harness moved it to a background task, which the brief does not allow. The driver ran to completion (exit 0), and its results, above, were read from its output file in `<scratch>`.

## Owner rulings needed

- **Non-atomic writers of recorded state (found by E2's principle; not fixed and not tested around, per the brief's rule 2).** Scratch probes (`<scratch>/r4/probe_local.py`, `<scratch>/r4/probe_launcher.py`, not committed) drove this round's injector against two writers outside the table:
  - `executorlib._local_submit` writes the local job record `jobs/<pid>.json` with plain `open(..., "w")` after the job has started. A write fault leaves the record present and torn: the probe observed `31848.json b''`, with the exception raised.
  - `executorlib._analysis_launcher` writes `run/launch-<uuid>.sh` with `write_bytes`. A write fault leaves a partial launcher behind (the probe observed `#!/bin/bash\ncd ...` truncated). `_submit_analysis` then reports an R-135 refusal.

  Two further writers have the same shape by inspection only (not probed): `_submit_analysis`'s append to `ANALYSIS_SUBMISSIONS` could leave a torn final line, and stage 00's project creation could leave a partial project.
  Options, as E2 frames class 2: (a) rule these to be defects, to be fixed in `gars/_system/` by a later, non-test-only item, and add their rows to `test_r164_writer_recovery.py` then; or (b) rule them to be outside the principle (a started job's record, a per-attempt launcher, an append log, a creation-only project) and record that ruling so the table's exclusions are the owner's, not the producer's.

## Residual gaps after round 4

- The kills above are in the named modules only. Whether the whole suite stays green in modes B and C, and its added wall time on the lane's node, are for the lane to measure. The seven R-164 modules now take about 8.2 s here, against the 15 s allowance.
- Descriptor-level faults (`os.write` on a raw descriptor, `NamedTemporaryFile`) are outside the table's injector. The two writers that use them, `render_report` and `emit_report`, are covered by `test_r164_failure_recovery.py`.
- `chmod` after the rename (`MACHINE_OWNED_MODE`) is not faulted: a chmod failure after the replace leaves the new bytes in place, which is not a prior-bytes situation.
- The writers listed in the "Left out" table above.
- Producer and reviewer share a model (0087, Context).

## Review round 5 fixes

Dated 2026-09-25. This round answers `docs/reviews/row3fu_ruling_round5.md`, a ruling round with no code. The ruling is the coordinator's, under the owner's standing delegation of 23 Sep 2026; it is not the owner's own words.

**The ruling on round 4's owner question (R1): option (a).** The four non-atomic writers of recorded state that round 4 found are real R-164 failure-path defects: a torn job record or launcher after a write fault is exactly class 2's shape. They are not fixed in this test-only follow-up, and they are not tested around: a test for them would fail on current code, which the test-only rule forbids. Each is a class-2 residual, untestable as built:

| Writer | What goes wrong | Evidence |
|---|---|---|
| `executorlib._local_submit`, `jobs/<pid>.json` | left torn after a write fault once the job has started | observed (round-4 scratch probe) |
| `executorlib._analysis_launcher`, `run/launch-*.sh` | left truncated after a write fault | observed (round-4 scratch probe) |
| `_submit_analysis`, append to `ANALYSIS_SUBMISSIONS` | could leave a torn final line | code-derived, not probed |
| stage 00's project creation | could leave a partial project | code-derived, not probed |

A later item that is not test-only, with its own approval record, fixes these writers under `gars/_system/` and then adds their rows to `gars/tests/test_r164_writer_recovery.py`. The second seal's class-2 result is read with these residuals in mind.

| Finding | Changed files | Test | Result |
|---|---|---|---|
| R1 (ruling recorded) | `docs/decisions/0087-row-3-followup-suite-strengthening.md` (dated addendum after its last byte), this report (this section) | `tests/test_decision_links_resolve.py`, `tests/check_counts.py`, `tests/check_contracts.py` | pass. Red-on-fault: not applicable, because nothing in this row changes behaviour |
| Found while running the named checks: 0111 lacked its required sections | `docs/decisions/0111-row-3-followup-suite-index-addendum.md` (dated addendum and the five required sections after its last byte; the earlier bytes are unchanged) | `tests/test_decision_links_resolve.py` | pass after the fix. Red-on-fault seen: yes. On `167e7db` plus the 0087 addendum, the test printed `decision links: REFUSED (docs/decisions/0111-row-3-followup-suite-index-addendum.md: new record missing Context)`, `Ran 3 tests` / `FAILED (failures=1)` |

Round 4 reported this test as `OK`. That was wrong for the committed tree: the check reads tracked files only, so it probably ran before 0111 was tracked. No pre-commit hook is installed in the build checkout, so nothing refused the commit.

`bash docs/decisions/build_index.sh` was re-run, and the index is byte-identical: neither record's frontmatter changed. No code or test changed, and the test count stays 860.

### Commands and summary lines, round 5

All commands were run from the repository root with `TMPDIR`, `TEMP` and `TMP` at `<scratch>`.

- `python3 tests/test_decision_links_resolve.py`: `Ran 3 tests in 1.175s` / `OK`, `citations: 376/376 resolve`.
- `python3 tests/check_counts.py`: `collected 360 tests from tests`, `collected 500 tests from gars/tests`, `suite: 860 tests, from unittest's loader`, `clean — every current claim matches the suite`.
- `python3 tests/check_contracts.py`: `14 contracts clean: sections, wait points, vocabulary.`

Not run, as the ruling names only these three and no code changed: the whole suite, the R-164 modules, `evals/test_harness.py` and `evals/check_results.py`.

## Owner rulings needed

None.

## Residual gaps after round 5

- The four class-2 residuals in the table above wait on a later item that is not test-only.
- The whole suite in modes B and C, and its added wall time, are for the lane to measure on its node.
- Descriptor-level faults, `chmod` after the rename, and the writers in round 4's "Left out" table remain as round 4 stated them.
- Producer and reviewer share a model (0087, Context).
