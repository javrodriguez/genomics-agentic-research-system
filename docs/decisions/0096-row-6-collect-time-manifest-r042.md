---
date: 2026-09-24
status: standing
kind: decision
touches:
  - evals/bench.py
  - tests/test_registry_columns.py
  - gars/_system/wrapperlib.py
  - gars/_system/executorlib.py
  - gars/_system/stage00_register.py
  - gars/_system/configure.py
  - gars/_system/resolve_artifact.py
  - gars/_templates/config/nextflow.slurm.config
  - gars/_system/wrappers/rnaseq-de/rnaseq_de.py
  - gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py
  - gars/tests/test_manifest_groups.py
  - gars/tests/test_data_class_required.py
symptoms:
  - collect reports completion without the required manifest evidence
  - output indexes lack per-file hashes and artifact classes
  - finalize permits unclassified datasets
  - reference preflight does not compare registered content hashes
---
# Row 6 Step A: collect-time manifest changes under R-042

## Context

The lane implements the specification recorded in 0095 under the owner's standing
delegation. R-042 requires each changed behavior to name a test that passes with
the change and fails without it. This is an implementation record, not the owner's
protected-path approval. That approval belongs to the owner's record 0099 at merge.

## Decision

| Existing behavior changed | Resulting behavior | Test that distinguishes old and new |
|---|---|---|
| Prepare alone writes manifest.json | Collect atomically extends the same file before STATUS on success and failure, preserving every prepare key/value | `test_rnaseq_de_cold_start_and_idempotent_collect`, `test_failure_collect_preserves_prepare_facts`, `test_all_ten_wrappers_both_backends` |
| Collect failure writes FAILED with an EXIT suffix | Collect writes the FAILED state token used by predicate_facts, retaining the classified failure in the executor record and failure artifacts; scheduler failures retain their separate reason-bearing states | `test_failure_collect_preserves_prepare_facts` |
| Three routing columns in wrapper OUTPUTS.tsv | Two trailing columns contain file/tree SHA-256 and durable/intermediate class; routing paths are unchanged; legacy three-column readers are retained | `test_output_hash_invariant_and_complete_gate`, `test_all_ten_wrappers_both_backends` |
| Evaluation registry reader requires exactly three columns | R8 accepts exactly three or five, reading only the first three; four and six refuse; scores ignore trailing metadata even when wrong | `RegistryColumnsTests.test_three_and_five_columns_pass`, `test_four_and_six_columns_are_refused`, `test_trailing_values_never_change_scores`; the new module is red on the parent reader |
| COMPLETE checks scheduler and artifact marker/index presence | COMPLETE also recomputes and matches OUTPUTS and manifest hashes, including idempotent COMPLETE requests | `test_output_hash_invariant_and_complete_gate` |
| Local executor does not retain completion timestamp | First observed completed job records completed_at; repeated collect reuses it | `test_rnaseq_de_cold_start_and_idempotent_collect` |
| Submission does not carry approval references for a gated retry | A destructive retry that passed the existing approval gate records its approval id and hash | Existing retry gate plus manifest group 12 coverage; no new approval action |
| Finalize can omit dataset classification | Named refusals for missing/unknown data class or purpose and unknown agreement reference; machine-owned mode-0444 dataset.tsv; same values preserve bytes/mtime and different values refuse | `test_missing_or_unknown_data_class_refused`, `test_purpose_and_agreement_ref_required`, `test_valid_class_writes_read_only_and_refinalize_is_immutable` |
| Session tools can target dataset.tsv | Its one READ_ONLY entry and two matching settings denies protect it; sibling files remain editable | `test_guard_dataset_entry_and_sibling_control` |
| Genome configuration carries only paths | Configure carries registry hashes; common preflight compares actual content with registry hashes; UNKNOWN is incomplete provenance, a known mismatch refuses | `test_reference_hash_mismatch_refused_and_unknown_is_incomplete` |
| Local stochastic calls omit an explicit seed argument | Every seed-capable local stochastic call receives the wrapper's fixed integer 0; manifest records the call and value | Generated-call binding in `test_rnaseq_de_cold_start_and_idempotent_collect` and the all-wrapper fixture tests |
| Local scripts do not write version evidence | Generated scripts write versions.json with interpreter and imported-package versions | Generated-script checks and all-wrapper fixture tests; analysis execution itself is synthetic here |
| Nextflow template has no trace/report/timeline | Fixed relative pipeline_info paths enable all three; trace overwrites and uses fixed container/start/complete/resource fields | Groovy template grammar tests and trace evidence fixtures |

No previous library default seed is asserted: the suite cannot verify it. A called
API without seed control is named in group 13 with determinism unknown. Thread
counts come from config; this records requested threads and does not measure every
library's worker usage.

### Template grammar and manual migration

R-075's charset governs substitutable single-quoted values. The trace `fields`
value is one fixed double-quoted constant with no dollar sign. It is locked by
check_groovy's template shape comparison; a project cannot substitute another
field list. The fixed filenames use only charset-legal characters and are relative
to the Nextflow launch directory, which the wrappers set to run/. No interpolated
params.outdir or Groovy validator change is introduced.

**R-042 compatibility change:** an existing project's seeded
`_config/nextflow.slurm.config` has the old grammar and now refuses as
“unregistered Groovy grammar”. Stage 00 seeds templates at project creation;
configure.py applies selected scalar choices to assay YAML and provides no re-seed
verb. The migration is **manual**: the owner reviews the project's site-specific
scalar settings, copies the current `_templates/config/nextflow.slurm.config` into
the project's `_config/nextflow.slurm.config`, and reapplies reviewed site scalars
within the allowed grammar. This is not presented as an existing command or a new
verb. Fixed trace fields stay identical in all seeded copies.

Existing fixture finalize calls now explicitly supply `--data-class public
--purpose fixture`. They do not rely on implicit defaults. The change report
lists every expectation adjustment separately from implementation defects.

## What this does not close

All residuals in 0095 remain NOT met. In particular this is not an n = 2 reproduction
measurement, no tolerances or re-run comparator exists, and the public README
manifest/re-run evidence row remains unmeasured. Real trace/accounting evidence and
the truth of model/version values reported by a caller are outside these fixtures.
The lane's R8 resolves the evaluator reader boundary. Its exact two-line change
is evaluation code, listed for the owner's protected approval in 0099 at merge.
It lands as the first commit with root tests and matching counts; Step A lands
second. Benchmark source-pin validation remains NOT met, owned by row 2's run
commit; no benchmark task pin or evaluation threshold changes here.

## Test

The two direct Row 6 modules, full suite, contracts/count checks and unchanged
evaluation commands are recorded verbatim in the change report. Twelve disposable
fault plants and the two parent-red checks establish failure sensitivity separately
from ordinary positive fixture results. No acceptance threshold is reduced.

## Status

Standing R-042 record of the lane's Step A changes, with the lane's R8 recorded in 0095. The owner's protected approval remains reserved for 0099 at merge. The producer does not approve or merge them.

## Date

2026-09-24


## Addendum — review round 2, 2026-09-24

R-042 / F3: `ManifestGroupsTests.test_design_check_missing_cannot_shrink_denominator`
prepares a design-consuming run without its check, collects it, and requires
group 14 to remain applicable but missing. Adding the check makes the same
manifest complete without changing the denominator; removing it after prepare
makes it incomplete again. Existing positive fixtures now supply their check.
Collect continues preserving every prepare field. Replay verifies the recorded
check hash and links that evidence into the fresh project from its original
manifest location. No check is synthesized to complete a real run.


## Addendum — ruling answered on fix round 2, 2026-09-24

R-042 implementation account for the lane's R12/R13 under the owner's standing
delegation, recorded in the dated 0095/0097 addenda. Earlier bytes are preserved.
Prepare adds agreement_ref from the machine-owned dataset row; absent evidence
is null, never inferred as `none`. Group 11 requires the field and applies the
existing finalize value grammar. Collect preserves this prepare key unchanged.
Older completed manifests without it grade group 11 missing and replay refuses
`no agreement_ref recorded`. Prepare and complete a new original under the new
writer; do not retrofit a historical manifest from today's dataset row.

`test_agreement_ref_is_required_prepare_evidence` checks capture, preservation,
missing-source behavior, schema membership and missing/invalid-field grading.
`test_collect_evidence_guard_refuses_session_writes` checks the honest mutable
trace, real hook refusals for both evidence files, and allowed sibling control.
The report records full-suite/guard/tool-call checks and assertion-level fault
plants. No legitimate agent path was newly refused in those passing checks.

The replay instrument self-test now creates its original registration through
real finalize and checks every replay's three values, complete dataset bytes
and mode 0444. Synthetic raw sources retain valid registration names instead
of collapsing eight links onto one arbitrarily named fixture source. The replay
refusal sweep now expects R13's specific reason for group 11; its failure and
no-output assertions remain intact. No test threshold or guard is weakened.
