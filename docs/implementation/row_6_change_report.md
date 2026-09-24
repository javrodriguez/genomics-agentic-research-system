## Step A: manifest

Status: Step A implemented, with the lane's R8 resolving the reader boundary.
The reader compatibility change lands first; the manifest implementation lands
second. No remote, push, merge, owner approval, Step B comparator, tolerances,
or n = 2 reproduction was added.

Parent: `2f891d8`; branch: `build/gars-row-6-manifest`. The owner's words and the
lane's specification/rulings are distinguished in decision 0095. Decision 0096
records R-042 behavior changes. Protected approval belongs to the owner in 0099;
0097 and 0098 remain reserved and unwritten.

### Requirements and acceptance

| Requirement | Changed files | Acceptance test | Result and red-on-fault |
|---|---|---|---|
| R-084, R-085, R-086: 18 groups, sources, applicability and completeness | manifest_check.py, manifest_schema.json, wrapperlib.py, all ten wrapper Python files, nextflow.slurm.config | all-ten/both-backend fixtures; group removal; predicate sweep; schema/spec drift; cold start and re-collect | Direct module green (14 tests); twenty EXIT lines below. Faults 1–7 and 12 red: yes |
| R-060: explicit machine-owned classification | stage00_register.py, finalize registry entry and contract, guard_hook.py, settings.json | test_data_class_required.py, including real hook payloads and sibling control | Four direct tests green; faults 8–9 red: yes |
| R-067 manifest fields | wrapperlib.py, manifest_schema.json | per-input hash/location and immutable prepare facts in each real prepare/collect fixture | Covered in all twenty fixtures; prepare mutation fault 3 red: yes |
| R-068 manifest fields and per-file SHA | wrapperlib.py, resolve_artifact.py, artifact_types.md, wrapper collectors | invariant sweep, tree/symlink fixture, COMPLETE refusal on drift; legacy reader compatibility | All readers covered; fault 11 red: yes. R8 reader compatibility and score invariance pass |
| R-090 hash half | appended genomes.md table, configure.py, common preflight and wrapper failure-code contracts | known mismatch refusal and UNKNOWN incompleteness | Direct test green; fault 10 red: yes. Real GRCh38 hashes remain UNKNOWN |
| R-042 | decision 0096, tests/run_tests.py, lifecycle fixtures and failure-class expectations | parent writer red, named regression checks, expectation table below | Parent and all twelve fault reds observed; targeted existing regressions green |

`project_state.py` already consumes rows with at least three columns and uses their
routing fields, so it needs no edit. `resolve_artifact.py` accepts exactly three or
five columns; routing paths and directory handoffs are preserved. The pre-existing
write_reproducibility signature, key formula, input keys and pipeline_commit write
remain intact. workspace.PIPELINES and wrapperlib.check_pipeline are byte-identical.

### Protected files touched

- `evals/bench.py` (evaluation code; R8; approval in 0099 at merge)

- `gars/.claude/settings.json`
- `gars/00_initialize_project/CONTEXT.md`
- `gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md`
- `gars/02_bioinformatics/scrnaseq/01_nfcore-scrnaseq-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md`
- `gars/02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md`
- `gars/_references/artifact_types.md`
- `gars/_references/genomes.md`
- `gars/_references/manifest_schema.json`
- `gars/_system/configure.py`
- `gars/_system/executorlib.py`
- `gars/_system/guard_hook.py`
- `gars/_system/manifest_check.py`
- `gars/_system/resolve_artifact.py`
- `gars/_system/stage00_register.py`
- `gars/_system/tools/registry.json`
- `gars/_system/wrapperlib.py`
- `gars/_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py`
- `gars/_system/wrappers/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py`
- `gars/_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py`
- `gars/_system/wrappers/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py`
- `gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py`
- `gars/_system/wrappers/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py`
- `gars/_system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py`
- `gars/_system/wrappers/rnaseq-de/rnaseq_de.py`
- `gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py`
- `gars/_system/wrappers/spatial-cluster-count/spatial_cluster_count.py`
- `gars/_templates/config/nextflow.slurm.config`

The guard diff is exactly one added READ_ONLY entry. The settings diff is exactly
two matching denies. Registry edits affect only finalize. The inherited genome
table and its GRCh38 row remain byte-identical; the new keyed hash table is appended.
Contract edits add only the new failure code or finalize flags and their refusal
semantics. No SKILL.md, tool pin, other tool implementation, hook or authoring code
changed. The producer does not claim the owner's 0099 approval.

### Measured fixture completeness

The suite constructs offline Git checkouts under its disposable GARS_PIPELINES.
Release tags and spatialvi's actual synthetic commit prefix are fixture identities,
not production pipeline executions. Production pin verification runs unchanged;
a mismatched commit is independently refused. Local import-name stubs allow
preflight; analysis, trace, images, software versions and sacct results are synthetic.
No skip is accepted in the manifest module.

Synthetic pins for the twenty-run acceptance fixture:

```json
{"atacseq_bulk": "nf-core-atacseq-2.1.2", "chipseq_bulk": "nf-core-chipseq-2.1.0", "cutandrun": "nf-core-cutandrun-3.2.2", "methylseq": "nf-core-methylseq-4.2.0", "rnaseq_bulk": "nf-core-rnaseq-3.26.0", "scrnaseq": "nf-core-scrnaseq-4.2.0", "spatialvi": "nf-core-spatialvi-c7300cb"}
```

Verbatim runner completeness lines (including the separate cold-start fixture):

```text
manifest completeness: 15/15 required groups
manifest completeness: 16/16 required groups
manifest completeness: 15/15 required groups
manifest completeness: 16/16 required groups
manifest completeness: 15/15 required groups
manifest completeness: 16/16 required groups
manifest completeness: 15/15 required groups
manifest completeness: 16/16 required groups
manifest completeness: 14/14 required groups
manifest completeness: 15/15 required groups
manifest completeness: 15/15 required groups
manifest completeness: 16/16 required groups
manifest completeness: 14/14 required groups
manifest completeness: 15/15 required groups
manifest completeness: 15/15 required groups
manifest completeness: 16/16 required groups
manifest completeness: 13/13 required groups
manifest completeness: 14/14 required groups
manifest completeness: 14/14 required groups
manifest completeness: 15/15 required groups
manifest completeness: 13/13 required groups
```

Verbatim reserved exit lines:

```text
EXIT manifest completeness nfcore-atacseq-wrapper local: 15/15
EXIT manifest completeness nfcore-atacseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-chipseq-wrapper local: 15/15
EXIT manifest completeness nfcore-chipseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-cutandrun-wrapper local: 15/15
EXIT manifest completeness nfcore-cutandrun-wrapper slurm: 16/16
EXIT manifest completeness nfcore-methylseq-wrapper local: 15/15
EXIT manifest completeness nfcore-methylseq-wrapper slurm: 16/16
EXIT manifest completeness rnaseq-de local: 14/14
EXIT manifest completeness rnaseq-de slurm: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper slurm: 16/16
EXIT manifest completeness scrna-qc-cluster local: 14/14
EXIT manifest completeness scrna-qc-cluster slurm: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper slurm: 16/16
EXIT manifest completeness spatial-cluster-count local: 13/13
EXIT manifest completeness spatial-cluster-count slurm: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper local: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper slurm: 15/15
```

### Expectation changes (Rule 4)

| Existing expectation | Required new expectation | Test and reason |
|---|---|---|
| Existing finalize fixtures omit classification | Every existing successful finalize call supplies public/fixture explicitly | tests/run_tests.py's ten call sites; R-060 now refuses omission |
| Spatial cluster output assertion expects exactly three cells | Its original routing assertion compares the first three cells; the new invariant suite independently requires and recomputes all five | SpatialClusterCountTests.test_08_collect_accepts_a_good_run_and_registers_only_table_and_report; R-068 |
| Every built-in SLURM descriptor key except prose is present in raw executor.yaml | resources_argv is also a fixed built-in default; a separate assertion verifies the loaded descriptor receives it | ExecutorSeamTests.test_01_shipped_template_resolves_to_the_builtin; executor.yaml is outside this step's allowed edits |
| Collect artifact failure state is FAILED:EXIT_1 | The collect gate records FAILED, matching predicate_facts.status; failure class/artifact and scheduler_state are retained | test_scheduler_success_then_collect_failure and new failure collect test; R2 |
| Two lifecycle fixtures can COMPLETE with a header-only index | They now supply one real hashed artifact and matching manifest evidence, preserving the original scheduler identity assertions | test_forged_record_cannot_collect_another_stages_job and test_reviewer_status_preserves_collected_terminal_state; the original identity fault still produces its named red |
| Benchmark registry reader only accepts three columns | Accept exactly three or five, refuse four or six, score only the first three fields | RegistryColumnsTests; lane R8, exact two-line evaluation reader change |
| A project can retain the old seeded Groovy grammar | It must receive the current trace-enabled template through the manual migration in 0096 | test_trace_template_grammar_and_manual_migration; R6; no new verb |
| Local stochastic calls omit a seed argument | Each seed-capable call receives the recorded constant 0 | generated-call binding tests; no claim about earlier defaults |

The first full suite was red: `Ran 472 tests in 295.393s`,
`FAILED (failures=5, errors=3, skipped=73)`. The new repeated-COMPLETE hash check
incorrectly reached stage 03 without a manifest; the implementation was corrected
to preserve that explicitly deferred writer. The remaining failures identified the
expectation changes above. None was suppressed. The targeted existing regression
run printed `Ran 56 tests in 61.880s` and `OK`, including the original lifecycle and
policy fault witnesses. Two additional new tests brought the collection to 474.

### Red-on-fault evidence

Each mutation was made in a separate disposable repository copy. The named test
ran normally against that copy; a non-zero result and unittest FAILED were required,
with syntax errors rejected as evidence. No production mutation was retained.

| # | Planted fault | Named test | Red observed |
|---|---|---|---|
| 1 | failure-path completion omitted | `gars/tests/test_manifest_groups.py ManifestGroupsTests.test_failure_collect_preserves_prepare_facts` | yes, exit 1 |
| 2 | missing fact treated as inapplicable | `gars/tests/test_manifest_groups.py ManifestGroupsTests.test_predicates_and_missing_facts_fail_closed` | yes, exit 1 |
| 3 | prepare fact changed at collect | `gars/tests/test_manifest_groups.py ManifestGroupsTests.test_rnaseq_de_cold_start_and_idempotent_collect` | yes, exit 1 |
| 4 | mutable container tag accepted | `gars/tests/test_manifest_groups.py ManifestGroupsTests.test_mutable_tag_and_immutable_trace_evidence` | yes, exit 1 |
| 5 | unknown model sentinel accepted | `gars/tests/test_manifest_groups.py ManifestGroupsTests.test_model_sentinels_and_known_prefix` | yes, exit 1 |
| 6 | predicate reads governed group | `gars/tests/test_manifest_groups.py ManifestGroupsTests.test_group_removal_sweep` | yes, exit 1 |
| 7 | unparseable manifest skipped | `gars/tests/test_manifest_groups.py ManifestGroupsTests.test_unparseable_manifest_is_never_skipped` | yes, exit 1 |
| 8 | missing data class accepted | `gars/tests/test_data_class_required.py DataClassRequiredTests.test_missing_or_unknown_data_class_refused` | yes, exit 1 |
| 9 | dataset guard entry removed | `gars/tests/test_data_class_required.py DataClassRequiredTests.test_guard_dataset_entry_and_sibling_control` | yes, exit 1 |
| 10 | genome mismatch ignored | `gars/tests/test_manifest_groups.py ManifestGroupsTests.test_reference_hash_mismatch_refused_and_unknown_is_incomplete` | yes, exit 1 |
| 11 | OUTPUTS hash differs from manifest | `gars/tests/test_manifest_groups.py ManifestGroupsTests.test_output_hash_invariant_and_complete_gate` | yes, exit 1 |
| 12 | group class changed | `gars/tests/test_manifest_groups.py ManifestGroupsTests.test_schema_matches_lane_table_and_spec` | yes, exit 1 |

`RED-ON-FAULT: 12/12 observed`

At parent `2f891d8`, copying the new test modules alone gave:

```text
PARENT import red: manifest_check absent; exit 1
```

A separate parent copy received only the new checker and schema. Its unchanged
RnaseqGarsWrapperTests.test_04_de_prepare_and_collect completed through the real
parent prepare and collect verbs. The instrument then refused its manifest with
`predicate_facts missing or not an object`:

```text
PARENT writer red: real collect succeeded; instrument grades incomplete
```

Thus the instrument-absent and writer-absent reds are distinct. Green results below
cover the authorized implementation; the final backend-consistency assertion was
checked by the direct fourteen-test manifest module after the initial full-suite
run. The R8 and final Step A checks below supersede that initial collection.

### Initial Step A commands and summaries

All commands ran from the repository root unless an individual disposable fixture
set its own working directory. All subprocesses inherited scratch TMPDIR, TEMP and
TMP; no system temporary directory, download or installation was used. Paths here
are repo-relative. Python was **3.13.2**, satisfying the harness's 3.9+ requirement.
Changed Python files also passed Python 3.6 grammar parsing; a 3.6 runtime was not
available for execution evidence.

```bash
export TMPDIR="$PWD/../gars-row-6-scratch/"
export TEMP="$TMPDIR" TMP="$TMPDIR"
GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py
python3 tests/check_contracts.py
python3 tests/check_counts.py
python3 evals/test_harness.py
python3 evals/check_results.py --controls --lexicon
python3 gars/tests/test_manifest_groups.py
python3 gars/tests/test_data_class_required.py
bash docs/decisions/build_index.sh
```

Commands were captured individually in scratch logs. Full suites ran sequentially.
Focused verification used the same interpreter and environment, with a unittest
Class.test_method argument where the table names one. The recorded fault driver
ran as `python3 ../gars-row-6-scratch/row6_faults.py`; it copied the repository,
replaced the named behavior for each row, invoked that row's direct test command,
and required failure. The parent driver ran as
`python3 ../gars-row-6-scratch/row6_parent.py`; it used `git archive 2f891d8` and
extracted into disposable scratch copies, then ran the two distinct checks above.
The evaluator scope probe ran as
`python3 ../gars-row-6-scratch/row6-output-reader-probe.py`: it first ran the existing
positive test unchanged and then changed only its disposable OUTPUTS rows to five
columns. The control passed and the five-column case failed at assert_registry.

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
Ran 474 tests in 283.801s
OK (skipped=73)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
collected 223 tests from tests
collected 251 tests from gars/tests
suite: 474 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 115.694s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 gars/tests/test_manifest_groups.py`

```text
Ran 14 tests in 34.773s
OK
```

`python3 gars/tests/test_data_class_required.py`

```text
Ran 4 tests in 2.312s
OK
```

### Hours

Instrumented build and verification elapsed time: **0.79 hours**, measured from
the first schema-build script timestamp to report assembly. Earlier specification
and decision reading was not timed. This is elapsed wall time, not a claim about
human labor hours. R8 continuation and verification took a further
**0.23 hours** from the saved-snapshot timestamp to this report assembly;
the later unchanged-commit verification is outside that interval.

### Residual gaps

- NOT met: benchmark task source-pin validation. `python3 evals/bench.py validate`
  refuses the inherited task pins after the authorized source changes. Row 2 owns
  re-pinning at its run commit. No file under benchmarks/ changes here.
- NOT met: real-cluster trace and sacct, row 13.
- NOT met: real GRCh38 hash evidence; both new hash cells remain UNKNOWN.
- NOT met: R-062 venue refusal and §6.1 permitted backends, provider exposure,
  retention and expiry; row 8 / D-3 owns that data-handling record.
- NOT met: R-087/R-088 registry validation, R-069 artifact liveness, and
  test_reference_pairing.py's comparison against row 7's claims.
- NOT met: wiring the report methods/reproduction renderer to these fields.
- NOT met: manifests from stage 03 and the authoring scaffold's three-column
  OUTPUTS writer; neither calls complete_manifest, so they grade incomplete.
- NOT met: protection against a human shell or other unguarded process that chmods
  and rewrites dataset.tsv; the guard sees only session tool calls.
- NOT met: truth beyond reported harness values, protected-source editing, or an
  externally forged manifest; the exact threat-model exclusions are in 0095.
- NOT met: pilot-1 and §17 real-run measurement. README's Manifest completeness and
  re-run diff row remains unmeasured.
- NOT met: reproduction n = 2, tolerances and comparator modes. This is Step B,
  intentionally absent here.

### Commit 1: R8 standalone verification

`bcc50b5` contains only evals/bench.py, tests/test_registry_columns.py, README.md,
and DEVELOPMENT.md. The full suite ran on that exact file tree immediately before
commit; check_counts also ran on the clean commit before restoring Step A.
All commands used the environment and Python 3.13.2 documented above.

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
Ran 459 tests in 241.781s
OK (skipped=73)
```

`python3 tests/check_counts.py`

```text
collected 226 tests from tests
collected 233 tests from gars/tests
suite: 459 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 tests/test_registry_columns.py`

```text
Ran 3 tests in 0.058s
OK
```

The same root test module against a disposable copy of the parent reader failed:

```text
Ran 3 tests in 0.045s
FAILED (failures=7)
```

The parent-reader check extracted `git show 2f891d8:evals/bench.py` into
`../gars-row-6-scratch/r8-parent-red/evals/bench.py`, copied the new test module to
that disposable tree, and ran
`python3 ../gars-row-6-scratch/r8-parent-red/tests/test_registry_columns.py`.
No production pin, stored score, or evaluation threshold was edited.

`python3 evals/bench.py validate` after restoring Step A exits nonzero, as expected:

```text
refused: input sha256 mismatch: gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md
```

This is the benchmark source-pin residual owned by row 2, not an accepted test
failure. The required evaluator harness and result checks are separate below.

### Step A verification on the complete second-commit tree

All seven Rule 6 commands were repeated after R8, using Python 3.13.2 and the
same scratch environment. These summaries record the tree immediately before
commit 2; a further unchanged-commit pass is reported in the handoff. Full suites
never overlap. No Row 6 test skipped.

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
collected 226 tests from tests
collected 251 tests from gars/tests
Ran 477 tests in 282.082s
OK (skipped=73)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
collected 226 tests from tests
collected 251 tests from gars/tests
suite: 477 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 113.684s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 gars/tests/test_manifest_groups.py`

```text
Ran 14 tests in 34.666s
OK
```

`python3 gars/tests/test_data_class_required.py`

```text
Ran 4 tests in 2.135s
OK
```

The direct manifest module and full suite printed the same twenty EXIT lines
listed above, one for every wrapper/backend pair. The scope audit confirmed the
exact R8 diff, one guard addition, two settings additions, inherited genome bytes,
and unchanged production pipeline pins and check_pipeline. Changed Python sources
parse under the Python 3.6 grammar. All twelve earlier fault witnesses and both
parent-red checks apply to the unchanged manifest implementation.

Commit messages were read from `../gars-row-6-scratch/r8-commit-message.txt` and
`../gars-row-6-scratch/row6-commit-message.txt`. Each git add names only the files
for that commit; neither staging operation uses git add -A. The tiny text image
fixture is explicitly staged with `git add -f --
gars/tests/fixtures/manifest/fixture.sif` because the inherited *.sif ignore rule
would otherwise omit this required offline fixture. The broad path-list add
reported an ignored parent directory but staged its tracked contract; the exact
staged path set was verified before committing. No remote was added
and neither commit was pushed, approved or merged by the producer.

## Owner rulings needed

none — item 1 is resolved by the lane's R8 below.

### Original question (preserved; the pending statements describe the earlier stop)

1. **The five-column output format requires an edit outside the permitted paths.**
   Deliverable 2 requires every reader of `OUTPUTS.tsv` to accept the two new
   trailing columns. `evals/bench.py:174-175`, in `assert_registry`, requires
   exactly three columns and unpacks the entire row into three variables.
   `score_task` calls it for `artifact_registry` outputs. The boundary explicitly
   says “Do not touch `evals/`”. A five-column row therefore fails this existing
   production reader even when its original three columns and all artifact
   contents are unchanged. This reader is separate from the two deliberately
   deferred three-column **writers** named in deliverable 12.

   The incompatibility was reproduced with the existing
   `BenchmarkTests.test_nfcore_artifact_contracts_accept_and_reject_content`:
   its three-column fixture passes; changing only the disposable fixture's rows
   to five columns makes its positive assertion fail. No production code or
   existing assertion was modified. The extra hash value is synthetic; the
   refusal occurs at column count before it could inspect that value.

   Options for the owner:

   - **A: authorize the narrow compatibility edit to `evals/bench.py` in Step A.**
     Accept exactly three or five columns, then unpack `row[:3]`. Retain every
     existing roster, path, role, artifact-content and reference comparison.
     Add both-format and invalid-width coverage in the allowed root test tree.
     No benchmark pin, scorer threshold or stored result needs to change.
   - **B: retain the boundary and supply that reader compatibility change as a
     separate prerequisite.** Step A resumes after the prerequisite is available;
     it does not claim the every-reader deliverable while this reader still
     rejects its output format.

   The concrete reader change proposed for A is:

   ```diff
   -        case.assertEqual(len(row), 3, 'registry needs type, role, path')
   -        typ, role, target = row
   +        case.assertIn(len(row), (3, 5), 'registry needs 3 or 5 columns')
   +        typ, role, target = row[:3]
   ```

No additional ruling was identified in the deliverable, group and threat-model
survey. R1–R7 are accepted as given and are not reopened. The compatibility change
above has not been applied, including in the production evaluator.


### Answer to item 1: R8

The lane, under the owner's standing delegation of 23 September 2026, authorizes
option A with the exact proposed two-line change and no other evaluation-code
edit. This is the lane's ruling, not additional words attributed to the owner.
The original pending statements above are superseded by this answer.

The reader and root tests land as commit 1 with matching README/DEVELOPMENT counts.
Three- and five-column registries pass; four and six refuse. The complete partition
score is identical after cutting five-column rows to three, including wrong
hash/class values and both valid and damaged artifact content. The manifest work
lands as commit 2, without another evals/bench.py change. Each commit is checked
independently; final Step A repeats every Rule 6 command, one full suite at a time.
Evaluation-code approval is listed above and belongs to the owner in 0099 at merge.
The producer neither writes that record nor approves or merges its work.
Benchmark task pins remain unchanged; row 2 owns re-pinning at its run commit.

## Step B: reproduction

Status: **blocked before implementation**, under the Step B instruction to stop
and raise a ruling if replay needs a change to Step A, and the boundary excluding
all existing `_system/` files. Parent: `94249c5` (Step A). This section is appended;
every byte of the earlier report remains unchanged.

### Requirements and acceptance

| Requirement | Files examined or changed | Test / probe | Result |
|---|---|---|---|
| R-091: re-execute from the manifest alone | Existing Nextflow prepares, wrapperlib.py, executorlib.py and manifest schema examined; only this report changed | Disposable real prepare/collect probe described below | Blocked: execution settings needed for replay are neither recorded nor hashed in the manifest |
| R-042: preserve existing behavior | No implementation file changed | Existing suite and direct manifest module, below | Baseline verification only; no expectation changes |
| Instrument self-test, comparison modes and fault sensitivity | No instrument, fixture or tolerance file created | Not run: implementation stopped at the prerequisite boundary | NOT met; no fixture result or reproduction result is claimed |

### Measured blocker: execution configuration is not recoverable from the manifest

All seven Nextflow wrappers give `write_reproducibility` only `samplesheet` and
`config` inputs. The latter is the assay YAML. Prepare also reads the project's
`_config/executor.yaml` and the Nextflow config selected by that descriptor, usually
`_config/nextflow.slurm.config`. Neither is a manifest input. The manifest contains
only the backend name, not the resolved descriptor. The recorded `commands.sh`
contains the submission command naming `submit.sh`; its hash does not cover
`submit.sh` or the Groovy file that Nextflow will read.

This is a replay prerequisite, not a proposed change to scientific tolerances.
`executorlib.load` permits descriptor overrides of `nextflow_profile` and
`nextflow_config`. `wrapperlib.check_groovy` permits scalar substitutions in the
shipped grammar, including its process executor. Inferring current sibling files
from the assay-config path would use unrecorded mutable state. Substituting the
shipped defaults would guess the original execution settings. Hashing those files
only when starting a re-run cannot recover the settings of a completed original.

The disposable probe reuses `ManifestGroupsTests`' offline pipeline checkout,
project, synthetic trace/accounting and real wrapper verbs. It executes no
bioinformatics pipeline and contacts no institutional scheduler. It prepares an
RNA-seq Slurm fixture, changes only Groovy `executor = 'slurm'` to
`executor = 'local'`, and prepares again. Both prepares pass, and the **entire**
prepare manifest is equal, including every re-preparation equality witness
requested for Step B. It then restores the original config, supplies the existing
synthetic completion evidence, submits through the existing fixture helper and
calls real collect with `--model none`. That manifest grades complete. Repeating
the Groovy mutation leaves the complete manifest, all recorded input hashes and
both Git commits valid. A separate valid descriptor override selects Docker in
place of Apptainer, also without changing any recorded input hash.

Verbatim probe output:

```text
PROBE Groovy executor slurm -> local: both real prepare calls pass
PROBE entire prepare manifest, params, config_sha256, commands.sh sha256 and idempotency_key: unchanged
PROBE original synthetic completed run: COMPLETE; manifest grades complete
PROBE after Groovy executor drift: COMPLETE, manifest grade, every recorded input hash and both commits still pass
PROBE descriptor profile apptainer -> docker: descriptor valid; manifest grade and every recorded input hash still pass
PROBE execution config is absent from manifest inputs: config, samplesheet
```

Probe command: `python3 ../gars-row-6-scratch/row6b-replay-probe.py`.
The driver and captured output remain in the designated scratch directory. Its
assertions use the existing `configure_wrapper('rnaseq_bulk', 'slurm', ...)`,
`wrapper_argv('prepare')`, `fake_wrapper_run()`, `submit()` and
`wrapper_argv('collect', ['--model', 'none'])` helpers, `manifest_check.grade`,
per-input SHA-256 recomputation and `git rev-parse HEAD` for both fixture repos.
This is evidence of the blocked prerequisite, not a Step B acceptance test or any
of the seven required red-on-fault witnesses.

The complete probe driver is preserved here for review and replay; save it at the
scratch filename above and run from the repository root with the stated scratch
environment. All generated projects and checkouts are disposable.

```python
import contextlib
import io
import json
import sys
from pathlib import Path
repo = Path.cwd()
sys.path.insert(0, str(repo / 'gars/tests'))
from test_manifest_groups import ManifestGroupsTests, checked, sha, mc
import wrapperlib as wl
import executorlib as ex
case = ManifestGroupsTests('test_all_ten_wrappers_both_backends')
try:
    with contextlib.redirect_stdout(io.StringIO()):
        case.setUp()
        case.pipeline_fixtures()
        case.configure_wrapper('rnaseq_bulk', 'slurm', case.project)
    before = case.prepared
    command = sha(case.stage / 'reproducibility/commands.sh')
    groovy = case.project / '_config/nextflow.slurm.config'
    original = groovy.read_text()
    assert "executor = 'slurm'" in original
    groovy.write_text(original.replace("executor = 'slurm'", "executor = 'local'"))
    fails = []
    wl.check_groovy(groovy, fails)
    assert not fails, fails
    checked(case.wrapper_argv('prepare'), cwd=case.ws, env=case.env)
    after = json.loads(case.manifest_path.read_text())
    assert before == after
    assert command == sha(case.stage / 'reproducibility/commands.sh')
    print('PROBE Groovy executor slurm -> local: both real prepare calls pass')
    print('PROBE entire prepare manifest, params, config_sha256, commands.sh sha256 and idempotency_key: unchanged')
    groovy.write_text(original)
    case.fake_wrapper_run()
    case.submit()
    checked(case.wrapper_argv('collect', ['--model', 'none']), cwd=case.ws, env=case.env)
    manifest = json.loads(case.manifest_path.read_text())
    assert mc.grade(manifest)['ok']
    assert wl.read_status(case.stage) == 'COMPLETE'
    assert all(sha(Path(path)) == manifest[key + '_sha256'] for key, path in manifest['inputs'].items())
    print('PROBE original synthetic completed run: COMPLETE; manifest grades complete')
    groovy.write_text(original.replace("executor = 'slurm'", "executor = 'local'"))
    assert mc.grade(manifest)['ok']
    assert all(sha(Path(path)) == manifest[key + '_sha256'] for key, path in manifest['inputs'].items())
    assert wl.git_value(Path(manifest['checkout']), 'rev-parse', 'HEAD') == manifest['pipeline_commit']
    assert wl.git_value(case.repo, 'rev-parse', 'HEAD') == manifest['gars_commit']
    print('PROBE after Groovy executor drift: COMPLETE, manifest grade, every recorded input hash and both commits still pass')
    descriptor = case.project / '_config/executor.yaml'
    descriptor.write_text('name: slurm\nnextflow_profile: docker\n')
    assert not ex.validate(ex.load(case.project))
    assert ex.load(case.project)['nextflow_profile'] == 'docker'
    assert mc.grade(manifest)['ok']
    assert all(sha(Path(path)) == manifest[key + '_sha256'] for key, path in manifest['inputs'].items())
    print('PROBE descriptor profile apptainer -> docker: descriptor valid; manifest grade and every recorded input hash still pass')
    print('PROBE execution config is absent from manifest inputs: ' + ', '.join(sorted(manifest['inputs'])))
finally:
    case.doCleanups()
```

### Protected files touched

None. Only this append-only report changes. Step A's manifest groups, schema,
sentinels, predicates, writer and records 0095/0096 remain byte-identical. README
and DEVELOPMENT counts remain unchanged because no tests were added. README's
manifest/re-run evidence row stays `unmeasured`.

### Expectation changes

None. No tests, acceptance thresholds or production defaults changed.

### Residuals

- NOT met: the reproduction instrument, tolerance file, test-only wrapper and
  instrument self-test. No `reproduction:` result line was produced.
- NOT met: the seven Step B red-on-fault witnesses or the new test's parent-red and
  implementation-green checks. An absent implementation is not credited as green.
- NOT met: the owner's two real Slurm re-runs; only the owner records those in 0098.
- NOT met: §8.4's second backend, §17's ≥ 4/5 on test data, the external pilot-1
  re-run and real-wrapper re-execution. The suite has no bio environment.
- NOT met: model-mediated typed claim-set comparison, which depends on row 7.
- 0097 remains unwritten pending this ruling; 0098 and 0099 remain reserved for the
  owner. No protected-path approval, push or merge is performed.

## Owner rulings needed

**B-1: authorize or supply a prerequisite that records execution configuration at
original prepare time.** The evidence above shows that replay from the manifest
alone cannot recover the original Nextflow executor settings under the current
writer. The Step B boundary forbids changing that writer or its wrapper callers.
This is the producer's finding and proposed resolution, not an owner ruling.

- **A: authorize a narrow prerequisite to capture the resolved executor descriptor
  and the selected Nextflow config as immutable, hash-bound prepare evidence.**
  The likely edit surface is `gars/_system/wrapperlib.py`, necessary wrapper
  prepare callers and their tests, all currently outside Step B's boundary.
  Preserve Step A's group classifications, predicates and sentinels. Require a
  named replay refusal for older manifests lacking the original evidence; do not
  retrofit them by guessing from today's files. Add R-042 tests showing that
  changed Groovy/descriptor settings cannot silently replay. The exact format and
  authorized file list must be settled before implementation resumes.
- **B: provide that prerequisite in a separate owner-authorized change**, then
  resume the reproduction half on top of it with the current Step B boundary.

The report-only commit records this stop; it does not substitute for the requested
Step B implementation commit or establish the row's exit.

### Step B stop-point commands and baseline summaries

All commands run from the repository root, one suite at a time, under Python
**3.13.2** (the evaluator harness requires Python ≥ 3.9). TMPDIR, TEMP and TMP use
the designated sibling scratch directory; no installation or download occurs.
Logs use the scratch prefix `row6b-baseline-`.

```bash
export TMPDIR="$PWD/../gars-row-6-scratch/"
export TEMP="$TMPDIR" TMP="$TMPDIR"
export PYTHONDONTWRITEBYTECODE=1
python3 ../gars-row-6-scratch/row6b-replay-probe.py
GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py
python3 tests/check_contracts.py
python3 tests/check_counts.py
python3 evals/test_harness.py
python3 evals/check_results.py --controls --lexicon
python3 gars/tests/test_rerun_check.py
python3 gars/tests/test_manifest_groups.py
```

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
collected 226 tests from tests
collected 251 tests from gars/tests
Ran 477 tests in 285.675s
OK (skipped=73)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
collected 226 tests from tests
collected 251 tests from gars/tests
suite: 477 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 114.220s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 gars/tests/test_rerun_check.py`

Exit **2**: the requested test file is absent because Step B implementation
stopped before creating it. No test ran and no unittest summary or instrument
self-test line printed. The interpreter error includes local absolute paths,
so its raw text is retained only in the scratch log. This is **not green**.

`python3 gars/tests/test_manifest_groups.py`

```text
Ran 14 tests in 34.592s
OK
```

### Hours

Measured elapsed time from writing the diagnostic driver through baseline-summary
assembly: **0.15 hours**. Earlier required reading was not timed. This is
wall time for diagnosis and verification, not implementation or human labor.

### Commit procedure

Only this report is staged with `git add -- docs/implementation/row_6_change_report.md`.
The commit message is read with `git commit -F ../gars-row-6-scratch/row6b-stop-commit-message.txt`.
The scope audit verifies the original report as an exact byte prefix and no
other changed tracked paths. No remote is added; no push, approval or merge occurs.

## Owner ruling answered (step B (the reproduction build))

2026-09-24, round **ruling-b**, on parent `1e2e560`. The supplied ruling is
**R9 — the lane, under the owner's standing delegation of 23 September 2026**;
it is not an independent review and is never quoted as additional owner words.
The earlier report is preserved as an exact byte prefix. Records 0095 and 0096
remain byte-identical. Record 0097 did not exist at this round's parent; the new
record states the lane's specification and includes a dated R9 addendum.

### B-1 answered (R9)

Original question, preserved:

**B-1: authorize or supply a prerequisite that records execution configuration at
original prepare time.** The evidence above shows that replay from the manifest
alone cannot recover the original Nextflow executor settings under the current
writer. The Step B boundary forbids changing that writer or its wrapper callers.
This is the producer's finding and proposed resolution, not an owner ruling.

- **A: authorize a narrow prerequisite to capture the resolved executor descriptor
  and the selected Nextflow config as immutable, hash-bound prepare evidence.**
  The likely edit surface is `gars/_system/wrapperlib.py`, necessary wrapper
  prepare callers and their tests, all currently outside Step B's boundary.
  Preserve Step A's group classifications, predicates and sentinels. Require a
  named replay refusal for older manifests lacking the original evidence; do not
  retrofit them by guessing from today's files. Add R-042 tests showing that
  changed Groovy/descriptor settings cannot silently replay. The exact format and
  authorized file list must be settled before implementation resumes.
- **B: provide that prerequisite in a separate owner-authorized change**, then
  resume the reproduction half on top of it with the current Step B boundary.

R9's answer: **Option A**, narrowed to wrapperlib.py, group 3's execution_config
field, the checker support for that field, and tests, beyond brief B's files.
The common submit-script generator captures the descriptor and actual Nextflow
config/profile argv that prepare uses. It hands immutable file hashes and resolved
values to the unchanged write_reproducibility signature. No wrapper call site or
idempotency-key formula changes. Old manifests lack the required group-3 evidence;
the instrument names the refusal instead of guessing today's configuration.
R9 closes B-1. The separate newly demonstrated samplesheet prerequisite B-2 below
is not covered by this execution-configuration ruling.

## Step B: reproduction

2026-09-24 continuation: the instrument, fixture, tolerance parser/comparator and
R9 execution evidence are implemented. **Step B is not fully closed:** replay of
scrna-qc-cluster stops for B-2. The owner's two institutional Slurm re-runs remain
unmeasured; only the local fixture result is the instrument's self-test.

### Requirements and acceptance

| Requirement | Changed files | Test | Result / red-on-fault |
|---|---|---|---|
| R-091 real prepare → executor submit/status → real collect; two fresh fixture runs | scripts/rerun_check.py; gars/tests/fixtures/rerun-fixture/rerun_fixture.py; gars/tests/test_rerun_check.py | test_instrument_self_test | Instrument self-test only; nine fault witnesses below |
| Exact bytes, numeric canonicalization, named pre-committed threshold, strict default | scripts/rerun_check.py; gars/_references/tolerances.yaml | test_numeric_threshold_and_canonicalization; test_byte_change_one_of_two; test_unlisted_defaults_to_exact_bytes; test_tolerance_refusals | Under threshold green, over threshold red; planted byte change yields reproduction: 1/2; faults 1–4 red: yes |
| No incomplete/drifted/failed original, no silently omitted output | scripts/rerun_check.py; gars/tests/test_rerun_check.py | test_all_refusals_and_contract_agreement; test_slurm_unavailable; test_instrument_self_test | Refusals create no output folder; exact OUTPUTS inventory covered; faults 5–7 red: yes |
| R9 / R-042 immutable prepare execution files | wrapperlib.py; manifest_schema.json; manifest_check.py; tests | test_execution_config_immutable_and_drift_refused; test_execution_config_shapes; test_all_real_wrapper_repreparations_and_execution_evidence | Descriptor/Groovy drift refused; both paths retain evidence at collect; old manifests grade group 3 missing; faults 8–9 red: yes |
| Real-wrapper re-preparation equality | gars/tests/test_rerun_check.py | test_all_real_wrapper_repreparations_and_execution_evidence | All ten wrappers × both fixture backends preserve params, config hash, commands.sh hash and key in place. Fresh-folder prepare verified for nine × both backends; scrna-qc-cluster exposes B-2 |
| R-042 records, counts and status | 0097; generated CONTEXT; report; README; DEVELOPMENT; test_manifest_groups.py positive fixture | Direct modules, whole suite, contracts and count checks | Summaries below; no real-run evidence promotion |

The only tolerance entry is for the fixture's numeric TSV. It documents deliberate
row/column shuffling and noise bounded by 1e-7 per cell; the threshold is 0.000001.
Each disposable self-test checkout commits the tolerance file before executing the
two re-runs; a changed uncommitted file refuses. The actual fixture seed comes from
os.urandom(16) at prepare, is recorded in the manifest, is passed to the worker,
and is independently checked against the worker's seed.json. No production wrapper
tolerance or scientific threshold is invented. The comparator retains both hashes
but does not use hashes to decide numeric tolerance.

### Protected files touched in this round

- gars/_system/wrapperlib.py — capture prepare's execution evidence only.
- gars/_references/manifest_schema.json — group 3's field list only.
- gars/_system/manifest_check.py — grade the new group-3 field only.
- gars/_references/tolerances.yaml — fixture-only entry, for the owner's 0099.

No wrapper call site, executor, guard, settings, evaluator, benchmark, CI, study,
template, tool registry or pin changes. No 0098/0099 is written. The owner's
protected-path approval at merge is not supplied or claimed by this producer.

### Expectation changes

| Earlier fixture/behavior | Required change | Why assertions remain meaningful |
|---|---|---|
| The all-groups positive control changes local to Nextflow but has only a descriptor | Add one synthetic nextflow_config entry to that synthetic manifest | R9 makes it required; every positive, field-removal and predicate-independence assertion is retained |
| Old complete manifests have no execution_config | Group 3 now grades missing; rerun_check refuses no execution config recorded | Explicit R9 migration; no sentinel or classification changes |

The first full run printed `Ran 488 tests in 314.595s` and
`FAILED (failures=1, skipped=73)`: the all-groups synthetic positive control above.
It was repaired by adding evidence, not by weakening the checker or an assertion.
The final required checks are recorded below. A preliminary direct run briefly
overlapped that initial suite; its results are not used as the final sequential
verification. No threshold or guard was weakened.

### Red-on-fault evidence

Each plant was made only in its own disposable scratch copy. Each named test
returned exit 1 with unittest `FAILED (failures=...)`; syntax/import errors were
rejected for these fault witnesses. No mutation remains in production.

| # | Plant | Named test in gars/tests/test_rerun_check.py | Red-on-fault seen |
|---|---|---|---|
| 1 | numeric_tolerance compared by SHA-256 | RerunCheckTests.test_numeric_threshold_and_canonicalization | yes; tolerance-positive assertion fails |
| 2 | byte_stable compared after canonicalization | RerunCheckTests.test_byte_change_one_of_two | yes; byte-order-only change must yield reproduction: 1/2 |
| 3 | unlisted output defaults to numeric | RerunCheckTests.test_unlisted_defaults_to_exact_bytes | yes; strict-default assertion fails |
| 4 | cause/evidence check removed | RerunCheckTests.test_tolerance_refusals | yes; named refusal assertion fails |
| 5 | incomplete-manifest refusal removed | RerunCheckTests.test_all_refusals_and_contract_agreement | yes; checker/refusal agreement fails |
| 6 | output silently skipped | RerunCheckTests.test_instrument_self_test | yes; complete comparison/self-test fails |
| 7 | --runs 2 executes once | RerunCheckTests.test_instrument_self_test | yes; run count/result fails |
| 8 | execution-config drift ignored | RerunCheckTests.test_execution_config_immutable_and_drift_refused | yes; named drift refusal fails |
| 9 | execution_config omitted at prepare | RerunCheckTests.test_execution_config_immutable_and_drift_refused | yes; completed fixture fails required group 3 |

`RED-ON-FAULT: 9/9 observed`

The parent checks copy only the new direct test module into `git archive` trees:

```text
PARENT 94249c5: new direct module red; exit 1; implementation prerequisite absent
PARENT 2f891d8: new direct module red; exit 1; implementation prerequisite absent
```

These are explicitly **import-level reds**, with missing rerun_check.py, not
claims that old implementations exercised the new assertions. The nine fault
plants separately establish assertion-level failure sensitivity.

### B-2 evidence: in-place equality does not establish fresh replay

The real scrna-qc-cluster prepare consumes a samplesheet and collect checks its
sample set. The wrapper's write_reproducibility call supplies only config and
h5ad. Its completed synthetic manifest grades complete, but a fresh project built
only from its manifest lacks that samplesheet. The real wrapper refuses before
submission on both fixture backends. Borrowing an unrecorded sibling file would
violate replay from the manifest and evade the recorded-input hash check.

The direct real-wrapper regression prints:

```text
PROBE scrna-qc-cluster local: fresh real prepare refuses no samplesheet
REPLAY BLOCKED scrna-qc-cluster local: samplesheet absent from manifest inputs
PROBE scrna-qc-cluster slurm: fresh real prepare refuses no samplesheet
REPLAY BLOCKED scrna-qc-cluster slurm: samplesheet absent from manifest inputs
```

The instrument refuses this case with
`manifest lacks required samplesheet input: scrna-qc-cluster` before creating the
output directory. B-2 was identified during fresh-project validation in this
round; it was not included in the preceding execution-configuration probe. It
has been put to the owner; no authorization has been received or inferred.

### Final verification commands and summaries

Python **3.13.2**; stdlib implementation and Python 3.6 grammar checks passed.
Python 3.6 runtime execution is not claimed. The final verification commands ran
sequentially, with no overlapping suite. TMPDIR, TEMP and TMP use the designated
sibling scratch directory; logs are retained there under `r9-final-`.

```bash
export TMPDIR="$PWD/../gars-row-6-scratch/"
export TEMP="$TMPDIR" TMP="$TMPDIR"
export PYTHONDONTWRITEBYTECODE=1
python3 ../gars-row-6-scratch/r9-faults.py
python3 ../gars-row-6-scratch/r9-parent.py
GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py
python3 tests/check_contracts.py
python3 tests/check_counts.py
python3 evals/test_harness.py
python3 evals/check_results.py --controls --lexicon
python3 gars/tests/test_rerun_check.py
python3 gars/tests/test_manifest_groups.py
bash docs/decisions/build_index.sh
```

`r9-verify.py` in scratch invokes this sequence with each stdout/stderr captured
separately. `r9-faults.py` copies tracked files plus this round's new sources into
disposable scratch repositories and changes only the listed behavior for each
plant. `r9-parent.py` extracts the two named Git archives and copies only the new
test module. Parent import reds and fault assertion reds are deliberately distinct.
The index builder reports its output using a local absolute path; that raw line
is kept only in the scratch log, never copied into a committed record.

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
collected 226 tests from tests
collected 262 tests from gars/tests
MEASURE instrument self-test run 1: max_absolute_error=4.8673E-8; bytes differ
MEASURE instrument self-test run 2: max_absolute_error=1.25052E-7; bytes differ
reproduction: 2/2
EXIT instrument self-test (fixture, local): reproduction 2/2
Ran 488 tests in 351.033s
OK (skipped=73)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
collected 226 tests from tests
collected 262 tests from gars/tests
suite: 488 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 130.758s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 gars/tests/test_rerun_check.py`

```text
Ran 11 tests in 35.113s
OK
MEASURE instrument self-test run 1: max_absolute_error=1.59673E-7; bytes differ
MEASURE instrument self-test run 2: max_absolute_error=1.16232E-7; bytes differ
reproduction: 2/2
EXIT instrument self-test (fixture, local): reproduction 2/2
```

`python3 gars/tests/test_manifest_groups.py`

```text
Ran 14 tests in 40.840s
OK
EXIT manifest completeness nfcore-atacseq-wrapper local: 15/15
EXIT manifest completeness nfcore-atacseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-chipseq-wrapper local: 15/15
EXIT manifest completeness nfcore-chipseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-cutandrun-wrapper local: 15/15
EXIT manifest completeness nfcore-cutandrun-wrapper slurm: 16/16
EXIT manifest completeness nfcore-methylseq-wrapper local: 15/15
EXIT manifest completeness nfcore-methylseq-wrapper slurm: 16/16
EXIT manifest completeness rnaseq-de local: 14/14
EXIT manifest completeness rnaseq-de slurm: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper slurm: 16/16
EXIT manifest completeness scrna-qc-cluster local: 14/14
EXIT manifest completeness scrna-qc-cluster slurm: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper slurm: 16/16
EXIT manifest completeness spatial-cluster-count local: 13/13
EXIT manifest completeness spatial-cluster-count slurm: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper local: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper slurm: 15/15
```

The comparator also checks the original output against its recorded hash and
symlink inventory at comparison time, so a re-run cannot change the original
artifact and thereby move its own baseline. The strict-default regression plants
that change and requires `original output drifted`. The final run above includes
that regression and the fixture's actual-seed binding assertions. No Row 6 test
skipped. The 73 whole-suite skips are environment-dependent inherited skips.

### Hours

Measured verification/build-continuation elapsed time from the first fixture-test
log to this report assembly: **0.51 hours**. Earlier reading and implementation
before that log were not timed. This is wall time, not human labor time.

### Commit procedure and scope audit

One round commit, with an explicit thirteen-file `git add --` list and the message
read from `../gars-row-6-scratch/r9-commit-message.txt`. The scope audit checks the
report's original bytes as an exact prefix; the supplied ruling stays unchanged
and untracked. It checks records 0095/0096 and the frozen evaluator/guard/settings
files byte for byte, group 3 as the schema's sole edit, unchanged input_key and
check_pipeline functions, no 0098/0099, Python 3.6 grammar, and absence of session
identifiers in additions. No remote, push, merge, pull request, installation or
owner approval occurs.

## Review round ruling-b fixes

2026-09-24. This round applies a lane ruling supplied as the REVIEW file, not an
independent review. There are no BLOCKER/MAJOR/MINOR/NOTE classifications to infer.

| Finding / requirement | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| B-1 / R9: replay lacked immutable execution configuration | wrapperlib.py; manifest_schema.json; manifest_check.py; 0097; index; tests | execution-config drift, older-manifest refusal, real-wrapper equality and collect preservation | closed; yes, faults 8–9 fail their named regression |
| Step B comparison instrument and self-test | rerun_check.py; fixture; tolerances.yaml; test_rerun_check.py | instrument self-test, refusal matrix, threshold edges, output sweep | implemented for available manifest inputs; yes, faults 1–7; the fixture result is not the owner's n = 2 |
| Synthetic group-removal positive control under R9 | test_manifest_groups.py | test_group_removal_sweep | fixed; yes, original missing Nextflow evidence made the full suite red; every assertion remains |
| Current counts/status and durable account | README; DEVELOPMENT; 0097; index; report | check_counts; scope audit; required verification above | counts pass; red-on-fault no, documentation follows measured results |
| B-2: scrna-qc-cluster requires an unrecorded samplesheet | instrument's named refusal; new real-wrapper probe; 0097; report | real fresh-project prepare on both fixture backends | stopped for the owner; red-on-fault no, this is a measured missing prerequisite, not a passing replay |

## Owner rulings needed

**B-2: authorize or supply the missing scrna-qc-cluster samplesheet input.**
R9 closes execution configuration but preserves existing wrapper calls and
idempotency-key behavior. This wrapper's real prepare/collect need its samplesheet,
which is absent from the manifest. Replaying it from an unrecorded sibling is not
permitted. The reproduction instrument therefore stops that case before execution.

- **A: authorize the narrow input fix** in
  `gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py`: add the consumed
  samplesheet to write_reproducibility's inputs, with an R-042 regression and
  migration record. This changes that wrapper's downstream idempotency key by
  including the new input; the owner must authorize that consequence explicitly.
  Test fresh-project replay prepare, samplesheet drift refusal, and the new key.
- **B: retain this round's boundary and supply a separate prerequisite** with the
  required input and key/migration behavior decided by the owner. Keep the named
  refusal until that prerequisite is available; do not claim full Step B closure.

The question has been submitted to the owner. No response is assumed from elapsed
time. B-1 is answered above; B-2 remains the only new open ruling and stops the lane.

## Residual gaps

- scrna-qc-cluster replay is stopped on B-2. Nine other real wrappers have fresh
  prepare evidence on both fixture backends, not biological re-execution evidence.
- The owner's two real institutional Slurm re-runs, recorded only by the owner in
  0098, are NOT measured; whole-row reproduction exit is NOT claimed.
- §8.4 second-backend behavior, §17's ≥ 4/5 on test data, the external pilot-1 re-run,
  real-wrapper analysis execution, and model-mediated typed claim-set equality
  remain NOT met. No bio environment is available in the suite.
- The owner's separate protected-path approval 0099 remains pending at merge.
  README's Manifest completeness and re-run diff row remains unmeasured.
- All other Step A residuals remain, including real trace/sacct and GRCh38 hashes,
  real-run completeness, deferred stage-03/authoring manifests, row-7 rendering,
  data-handling/registry/liveness requirements and row-2 benchmark re-pinning.
- Python 3.6 grammar is verified; Python 3.6 runtime and real scheduler behavior are
  not verified. No protected-path approval, push, merge or release is claimed.


## Ruling answered (step B's ruling round b (the reproduction build))

2026-09-24, round **ruling-b2**, parent `9def5b3`. **R10 — the lane, under
the owner's standing delegation of 23 September 2026**, authorizes option A of
B-2. This is a supplied lane ruling, not an independent review or additional
words attributed to the owner. The earlier report and 0097 remain exact byte
prefixes. Records 0095/0096 are unchanged; 0098/0099 are never written here.

R10's scrna-qc-cluster change is implemented and verified below. The required
survey found a separate rnaseq-de input mismatch, B-3; that part stops for a ruling.
Neither full Step B closure nor the owner's real Slurm reproduction exit is claimed.

## Review round ruling-b2 fixes

2026-09-24. No BLOCKER/MAJOR/MINOR/NOTE severity is invented for this ruling.

| Finding / requirement | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| R10 / B-2: record the samplesheet actually consumed | scrna_qc_cluster.py; test_rerun_check.py; test_manifest_groups.py | RealWrapperReplayTests.test_scrna_samplesheet_replay_and_drift; ManifestGroupsTests.test_all_ten_wrappers_both_backends | Closed; yes, dropping the one input makes the explicit membership assertion fail |
| Fresh-project scrna replay, with missing-input refusal retained for legacy manifests | test_rerun_check.py | test_scrna_samplesheet_replay_and_drift | Two fresh projects pass real prepare/submit/status/collect/comparison with a synthetic worker; legacy refusal still tested; yes, fault 10 |
| Samplesheet drift after prepare | test_rerun_check.py | test_scrna_samplesheet_replay_and_drift | `input hash changed: samplesheet` before output creation; prepared_key independently refuses changed bytes; yes, dropping the declaration fails the named test |
| Authorized new key, migration and unchanged other-nine keys | test_rerun_check.py; 0097 addendum | test_all_real_wrapper_repreparations_and_execution_evidence | All ten × both fixture backends compared to real base-source preparation at identical paths; only scrna key changes; yes, dropping the declared input defeats its membership/key assertions |
| Manifest invariant includes new input | test_manifest_groups.py | test_all_ten_wrappers_both_backends | Every input hash recomputed and location checked; deleting each hash makes group 1 missing; yes, declaration omission fails the scrna membership assertion |
| Step B comparator/refusal fault sensitivity | No implementation changes; scratch mutation driver | Nine original RerunCheckTests fault witnesses plus new RealWrapperReplayTests witness | `RED-ON-FAULT: 10/10 observed`; yes, assertion-level failures, not import/syntax errors |
| R10 survey of other nine wrappers | Report; 0097 addendum; DEVELOPMENT; README | Real-wrapper base/fresh preparation sweep and r10-survey.py | Survey complete; B-3 found and stopped, not fixed; red-on-fault no, diagnostic evidence of an existing gap |
| R-042 record, current counts and boundaries | 0097 addendum; report; README; DEVELOPMENT; regenerated index | Required commands below; r10-audit.py | Original bytes preserved; scope and counts checked; red-on-fault no, documentation follows measured evidence |

### Protected files and expectation changes

The sole protected implementation edit is
`gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py`: add the samplesheet
to its existing write_reproducibility input dictionary. The common writer supplies
its hash/location and includes it in the unchanged downstream key formula. No other
wrapper, common helper, schema, tolerance, template, guard, setting, registry, pin,
CI, evaluator, benchmark or study changes. The owner's separate approval remains
0099 at merge. The producer does not provide it.

`scripts/rerun_check.py` is byte-identical: its existing B-2 condition already
accepts a manifest with the samplesheet, and still refuses the missing-input case.
The index was regenerated with the required builder; unchanged frontmatter makes
the generated index byte-identical, so no artificial index edit is committed.

| Previous expectation | R10 expectation | Why this is not weakened |
|---|---|---|
| Fresh scrna prepare refuses `no samplesheet`; completed manifest lacks it | Fresh prepare validates on both fixture backends; completed manifest contains its path/hash/location | Real prepare and collect still run; all previous equality and execution-evidence assertions remain |
| All current scrna prepares retain the legacy key | New key differs from base because the samplesheet is framed into downstream-v1 | Real base/current preparations use identical files; dropping only that input reconstructs the base key; other-nine equality is asserted |
| Old scrna manifests receive the B-2 refusal | Same refusal for the old case; successful recorded case and drift refusal added | The production guard is unchanged, and the old case remains a negative test |

A prepared-but-unsubmitted scrna stage must re-run its normal `prepare` with the
recorded matrix before submission. A legacy manifest/script can still pass the
unchanged prepared_key check; the code does not automatically detect that it needs
the migration. The new prepare replaces the manifest and script comment with the
new key, which submit accepts. Completed old manifests must not be hand-retrofitted.
This change does not authorize resetting active or terminal stages.

### Survey of the other nine wrappers

The source survey followed prepare/check/collect reads, declared writer inputs,
and shared configuration/provenance helpers; the real base/current and fresh-project
prepare sweep runs on both fixture backends. Generated results, lifecycle records
and pinned code resources are identified separately from original analysis inputs.

| Wrapper | Consumed analysis/configuration files and binding | Finding |
|---|---|---|
| nfcore-atacseq-wrapper | samplesheet and assay config in inputs; selected executor/Groovy in execution_config; reference paths in config | No additional project input found |
| nfcore-chipseq-wrapper | samplesheet (including antibody/control checks), config and execution configuration | No additional project input found |
| nfcore-cutandrun-wrapper | samplesheet used by prepare and collect, config including reference/spike-in paths, execution configuration | No additional project input found |
| nfcore-methylseq-wrapper | samplesheet sample set, config and execution configuration | No additional project input found |
| nfcore-rnaseq-wrapper | samplesheet, config including reference/cache paths, execution configuration | No additional project input found |
| nfcore-scrnaseq-wrapper | samplesheet, config and execution configuration; assets/protocols.json is a resource in the recorded pipeline checkout | No additional project input found; pipeline-source integrity remains the existing threat boundary |
| nfcore-spatialvi-wrapper | samplesheet including spatial input paths, config and execution configuration | No additional project input found |
| spatial-cluster-count | samplesheet, config and each resolved h5ad file in inputs; executor descriptor in execution_config | No additional project input found |
| rnaseq-de | prepare's counts, supplied design and config are inputs; collect separately opens the canonical design path | **B-3: alternate --design leaves a consumed canonical file unrecorded** |

The shared writer reads dataset classification into prepare facts; collect also
reads its generated outputs, versions, trace/accounting, design-check evidence,
and model context into their existing manifest groups. This survey does not claim
real execution, recursive hashing of all pipeline data dependencies, or immutable
external environment resources. None of those existing boundaries is widened here.

The B-3 probe uses a disposable fixture, the actual prepare and collect verbs and
the existing synthetic completion helper. The supplied alternate design initially
has the same bytes as the canonical design; changing only the canonical file adds
an unmatched sample. Every input that the manifest records retains its hash.

Command: `python3 ../gars-row-6-scratch/r10-survey.py`

```text
SURVEY rnaseq-de: prepare accepts alternate --design; canonical design absent from inputs
SURVEY rnaseq-de: canonical design changed; every recorded input hash unchanged
SURVEY rnaseq-de: collect exit 1; {"check": "de_results", "detail": "normalized_counts.csv lacks sample(s): UNRECORDED"}
```

Source evidence: rnaseq_de.py's writer call records `Path(args.design)` at lines
308–314; collect derives and opens `01_samplesheets/rnaseq_bulk_design.csv` at
lines 359–365. `bind_project` restores the recorded design to that canonical name,
so it cannot reconstruct a different unrecorded collect-time design. The probe is
a diagnostic, not a passing reproduction exit. No fix or new refusal is inferred.

### Red-on-fault evidence for this round

`python3 ../gars-row-6-scratch/r10-faults.py` repeats all nine step B plants and
adds plant 10, `samplesheet dropped from scrna-qc-cluster inputs`. Each mutation
runs only in a separate disposable scratch copy and exits 1 with unittest
`FAILED (failures=...)`; syntax/import errors do not count. Plants 1–9 use the
same named tests listed in the preceding step B table. Plant 10 runs
`RealWrapperReplayTests.test_scrna_samplesheet_replay_and_drift` and fails
`assertIn('samplesheet', original['inputs'])`.

The first plant-10 attempt exposed a KeyError in the test before its membership
assertion existed. That error was rejected as an assertion-level witness. An
explicit membership assertion was added; the entire ten-plant driver then passed.
No production mutant remains and no threshold or guard was weakened.

```text
RED-ON-FAULT: 10/10 observed
```

### Required verification commands and verbatim summaries

Python **3.13.2**. Commands ran sequentially, one suite at a time. TMPDIR, TEMP and
TMP point to the designated sibling scratch folder, and PYTHONDONTWRITEBYTECODE=1.
The scratch driver `r10-verify.py` retains individual stdout/stderr logs under
`r10-final-`. No row-6 test is skipped. Whole-suite skips are inherited environment
skips. Python 3.6 grammar is checked; Python 3.6 runtime is not claimed.

Preliminary targeted command: `python3 gars/tests/test_rerun_check.py RealWrapperReplayTests`

```text
Ran 2 tests in 29.710s
OK
```

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
collected 226 tests from tests
collected 263 tests from gars/tests
SCRNA replay fixture: 2/2; real prepare/submit/status/collect, synthetic worker
MEASURE instrument self-test run 1: max_absolute_error=1.48955E-7; bytes differ
MEASURE instrument self-test run 2: max_absolute_error=9.2513E-8; bytes differ
reproduction: 2/2
EXIT instrument self-test (fixture, local): reproduction 2/2
Ran 489 tests in 328.397s
OK (skipped=73)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
collected 226 tests from tests
collected 263 tests from gars/tests
suite: 489 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 115.003s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 gars/tests/test_rerun_check.py`

```text
Ran 12 tests in 40.314s
OK
SCRNA replay fixture: 2/2; real prepare/submit/status/collect, synthetic worker
MEASURE instrument self-test run 1: max_absolute_error=1.48559E-7; bytes differ
MEASURE instrument self-test run 2: max_absolute_error=1.69052E-7; bytes differ
reproduction: 2/2
EXIT instrument self-test (fixture, local): reproduction 2/2
```

`python3 gars/tests/test_manifest_groups.py`

```text
EXIT manifest completeness nfcore-atacseq-wrapper local: 15/15
EXIT manifest completeness nfcore-atacseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-chipseq-wrapper local: 15/15
EXIT manifest completeness nfcore-chipseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-cutandrun-wrapper local: 15/15
EXIT manifest completeness nfcore-cutandrun-wrapper slurm: 16/16
EXIT manifest completeness nfcore-methylseq-wrapper local: 15/15
EXIT manifest completeness nfcore-methylseq-wrapper slurm: 16/16
EXIT manifest completeness rnaseq-de local: 14/14
EXIT manifest completeness rnaseq-de slurm: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper slurm: 16/16
EXIT manifest completeness scrna-qc-cluster local: 14/14
EXIT manifest completeness scrna-qc-cluster slurm: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper slurm: 16/16
EXIT manifest completeness spatial-cluster-count local: 13/13
EXIT manifest completeness spatial-cluster-count slurm: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper local: 14/14
Ran 14 tests in 36.435s
OK
EXIT manifest completeness nfcore-spatialvi-wrapper slurm: 15/15
```

`python3 gars/tests/test_data_class_required.py`

```text
Ran 4 tests in 2.047s
OK
```

`bash docs/decisions/build_index.sh` exited 0 and regenerated a byte-identical index.
Its raw absolute-path output is retained only in the scratch log.

`python3 ../gars-row-6-scratch/r10-verify.py`

```text
REQUIRED VERIFICATION: 8/8 commands passed
```

### Hours

Measured elapsed time from the first R10 edit through report assembly: **0.21 hours**.
Earlier reading is not timed. This is wall time, not human labor time.

### Scope audit and commit procedure

`python3 ../gars-row-6-scratch/r10-audit.py` checks the exact allowed path set,
report/0097 prefix preservation, byte-identical 0095/0096 and frozen implementation
files, unchanged/untracked supplied ruling, the exact one-input wrapper diff,
absence of 0098/0099 and session identifiers in additions, Python 3.6 grammar and
`git diff --check`.

```text
SCOPE AUDIT: allowed paths only; append-only prefixes intact; protected files and ruling unchanged
WRAPPER DIFF: samplesheet input addition only; scripts/rerun_check.py unchanged
PRIVACY/GRAMMAR: no session identifiers in additions; changed Python parses as 3.6
```

One commit on `9def5b3`, staged with an explicit seven-file `git add --` list;
message read from `../gars-row-6-scratch/r10-commit-message.txt`. The regenerated
index has no diff. Both pre-existing untracked ruling files remain untracked;
the supplied ruling-b2 file is hash-checked unchanged. No push, remote, merge,
pull request, owner approval, installation or download occurs.

## Owner rulings needed

**B-3: choose rnaseq-de's design identity for collect when `--design` names a
noncanonical file.** R10 requires this newly surveyed consumed-input gap to stop.
The evidence above shows that prepare accepts and records the alternate design,
while collect reads another file without its hash being a declared input. Replay
binds the recorded design at the canonical path and can therefore use a different
collect gate from the original. No implementation choice below is made here.

- **A: authorize collect to use the manifest's recorded design input**, with
  tests for alternate paths, input drift and migration of existing preparations.
  Decide how existing completed runs whose collect used another design are handled.
- **B: require prepare's supplied design to resolve to the canonical project
  design**, with an explicit refusal for alternatives and migration/regression
  coverage for existing alternate-path prepares.
- **C: record the separate canonical collect design as an additional consumed
  input**, explicitly authorizing the key change and migration, and decide how
  replay reconstructs both identities when they differ or the canonical file is
  absent.

The lane stops this part for a ruling. The report cannot truthfully close this
section with `none`. No answer or authorization is inferred.

### B-2 answered (R10)

R10 authorizes option A for scrna-qc-cluster. Its samplesheet is now recorded,
hashed and included in its new preparation key. Fresh recorded-case replay,
changed-input refusal, legacy missing-input refusal, base/current key comparison,
submit acceptance and the manifest invariant sweep are verified above. The
migration is re-running prepare on an existing prepared-but-unsubmitted stage;
0097 records the exact legacy behavior. This answer is the lane's ruling under
the owner's standing delegation, not additional words attributed to the owner.

## Residual gaps

- B-3 is the only newly identified implementation ruling; rnaseq-de's alternate
  design/collect identity remains unresolved. Full Step B closure is not claimed.
- The owner's two institutional Slurm re-runs remain unmeasured and belong solely
  in 0098. Fixture 2/2 is the instrument self-test, not that exit condition.
- Scrna replay here uses a synthetic worker. Biological execution, actual scheduler
  behavior, §8.4 second-backend behavior, §17's ≥ 4/5 on test data, external pilot-1
  reproduction and model-mediated typed claim-set equality remain unverified.
- The owner's 0099 approval of protected changes/tolerances and confirmation of
  the lane's D-16 classification remain pending at merge. The public manifest and
  re-run evidence row remains unmeasured.
- Earlier Step A residuals remain: real trace/sacct and GRCh38 hashes, real-run
  completeness, stage-03/authoring manifests, row-7 methods/rendering/claim wiring,
  data-handling/registry/liveness requirements and row-2 benchmark re-pinning.
- Python 3.6 grammar passes; Python 3.6 runtime is not available for verification.
  No producer approval, merge, push or release is claimed.


## Ruling answered (step B's ruling round b2 (the reproduction build))

2026-09-24, round **ruling-b3**, parent `6039276`. **R11 — the lane, under
the owner's standing delegation of 23 September 2026** — authorizes option B
of B-3. This supplied file is a ruling, not an independent review or additional
words attributed to the owner. No finding severity is invented. This section and
the 0097 addendum follow their records' previous last bytes. Records 0095/0096
remain unchanged; the producer never writes 0098/0099.

## Review round ruling-b3 fixes

2026-09-24.

| Finding / requirement | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| B-3 / R11: prepare and collect must share design identity | rnaseq_de.py; its contract; test_rerun_check.py | RealWrapperReplayTests.test_rnaseq_design_prepare_identity | Closed; yes, plant 11 bypasses the refusal and fails the expected exit-2 assertion |
| Alternate design refused without writes | test_rerun_check.py | Same test, identical-byte alternate file, populated and absent stage | Closed; yes, plant 11; file bytes/mtimes, symlinks and directory inventory are unchanged on refusal |
| Canonical, relative and symlink designs retain prior behavior | test_rerun_check.py | Same test runs actual parent and current prepare at identical paths | Closed; full manifest, key, submit.sh, analysis script and commands.sh equal per spelling; red-on-fault no, positive compatibility comparison |
| Legacy COMPLETE alternate-design run must never replay | rerun_check.py; test_rerun_check.py; 0097 addendum | RealWrapperReplayTests.test_rnaseq_design_replay_and_legacy_refusal | Closed; legacy manifest made with real parent prepare; named refusal before output creation/submission; yes, extra replay-refusal plant 12 |
| Canonical case replays through the instrument | test_rerun_check.py | Same test, separate canonical original and two fresh replay projects | Closed; real prepare/submit/status/collect/comparison with synthetic worker; no biological-execution claim; red-on-fault no for this positive case |
| R10 other-nine-wrapper re-survey disposition | Appended report and 0097; DEVELOPMENT | Preserved R10 wrapper-by-wrapper source survey and current all-wrapper preparation test | COMPLETE; B-3 was its only finding; no other finding or owner question; red-on-fault no, survey disposition |
| Existing downstream submission fixture | test_downstream_keys.py | DownstreamKeyTests.test_rnaseq_de_submit | Fixed canonical path only; all existing assertions retained; red-on-fault yes, the initial suite failed with the old alternate-path fixture |
| Migration, append-only record and current counts | 0097 addendum; appended report; README; DEVELOPMENT; regenerated index | Required commands and scope audit below | Closed; counts verified; original record prefixes retained; index byte-identical; red-on-fault no, documentation reflects measured results |

### Expectation change and initial suite result

The first full suite printed `Ran 491 tests in 333.562s` and
`FAILED (failures=1, skipped=73)`. The sole failure was
`DownstreamKeyTests.test_rnaseq_de_submit`: its mocked-preflight fixture supplied
`root/design`, which R11 now correctly refuses. The fixture in
`gars/tests/test_downstream_keys.py` now supplies the canonical project path for
rnaseq-de. All original key, ordering, unrelated-input, wrong-config,
duplicate-submission and input-drift assertions remain unchanged. No production
behavior was relaxed. The final whole-suite run below supersedes this initial run.

### Behavior, migration and boundaries

Collect derives `project / "01_samplesheets" / ("%s_design.csv" % ASSAY)` with
ASSAY `rnaseq_bulk`; prepare now derives that same path and compares resolved
real paths before run_checks or any write. A different file returns exit 2 with
`design_not_canonical` and `design is not the canonical project design`.
Identical content at an alternate real path does not establish design identity.
The contract change is only the new failure code and refusal semantics.

An existing prepared-but-unsubmitted stage naming an alternate design must be
re-prepared against the canonical project design before submission. No new
submit-time legacy detector is authorized or claimed. Do not hand-edit a manifest
or key; no running or terminal stage reset is authorized. An existing COMPLETE
alternate-design original is refused by the instrument with the named reason,
without a replay directory or submission. Prepare and complete a new canonical
original for reproduction evidence. Collect and the key formula are unchanged.

The R10 re-survey of the other nine wrappers is **COMPLETE**. **B-3 was its only
finding**; the preserved preceding round's table and diagnostic command are the
evidence. R11 answers B-3. The current all-wrapper test again exercises all ten
wrappers on both fixture backends. No additional finding was identified here.

Protected implementation changes are limited to rnaseq_de.py and its contract.
No other `_system`, `_references`, `_templates`, guard, settings, evaluator,
benchmark, CI, study, registry or pin changes. 0095/0096 remain byte-identical;
0097 is appended only. The supplied ruling and both pre-existing untracked ruling
files remain untracked and unchanged. The owner's separate protected approval
remains in 0099 at merge. No threshold, test assertion or guard is weakened.

The first targeted invocation exposed a missing fixture setup call (`spatial_pin`
absent): `Ran 2 tests in 1.002s`, `FAILED (errors=2)`. Both new tests now initialize the existing pipeline fixture helper; no
production change or weakened assertion was used to resolve that test error.
The successful initial targeted run follows; the later full suite also covers the added prepared-stage migration assertion. All required suites then ran sequentially.

### Required verification commands and verbatim summaries

The existing submission module after the fixture adjustment:
`python3 gars/tests/test_downstream_keys.py`

```text
Ran 3 tests in 0.156s
OK
```

Python 3.13.2. TMPDIR, TEMP and TMP point to the designated sibling scratch
folder; PYTHONDONTWRITEBYTECODE=1. No row-6 test skipped. The whole-suite skips
are inherited environment skips. Logs are retained under `r11-final-` in scratch.

`python3 gars/tests/test_rerun_check.py RealWrapperReplayTests.test_rnaseq_design_prepare_identity RealWrapperReplayTests.test_rnaseq_design_replay_and_legacy_refusal`

```text
Ran 2 tests in 6.220s
OK
RNASEQ design replay fixture: 2/2; real prepare/submit/status/collect, synthetic worker
```

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
collected 226 tests from tests
collected 265 tests from gars/tests
EXIT manifest completeness nfcore-atacseq-wrapper local: 15/15
EXIT manifest completeness nfcore-atacseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-chipseq-wrapper local: 15/15
EXIT manifest completeness nfcore-chipseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-cutandrun-wrapper local: 15/15
EXIT manifest completeness nfcore-cutandrun-wrapper slurm: 16/16
EXIT manifest completeness nfcore-methylseq-wrapper local: 15/15
EXIT manifest completeness nfcore-methylseq-wrapper slurm: 16/16
EXIT manifest completeness rnaseq-de local: 14/14
EXIT manifest completeness rnaseq-de slurm: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper slurm: 16/16
EXIT manifest completeness scrna-qc-cluster local: 14/14
EXIT manifest completeness scrna-qc-cluster slurm: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper slurm: 16/16
EXIT manifest completeness spatial-cluster-count local: 13/13
EXIT manifest completeness spatial-cluster-count slurm: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper local: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper slurm: 15/15
RNASEQ design replay fixture: 2/2; real prepare/submit/status/collect, synthetic worker
SCRNA replay fixture: 2/2; real prepare/submit/status/collect, synthetic worker
MEASURE instrument self-test run 1: max_absolute_error=1.13799E-7; bytes differ
MEASURE instrument self-test run 2: max_absolute_error=7.3737E-8; bytes differ
reproduction: 2/2
EXIT instrument self-test (fixture, local): reproduction 2/2
Ran 491 tests in 333.491s
OK (skipped=73)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
collected 226 tests from tests
collected 265 tests from gars/tests
suite: 491 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 114.273s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 gars/tests/test_rerun_check.py`

```text
Ran 14 tests in 47.055s
OK
RNASEQ design replay fixture: 2/2; real prepare/submit/status/collect, synthetic worker
SCRNA replay fixture: 2/2; real prepare/submit/status/collect, synthetic worker
MEASURE instrument self-test run 1: max_absolute_error=1.85259E-7; bytes differ
MEASURE instrument self-test run 2: max_absolute_error=1.85249E-7; bytes differ
reproduction: 2/2
EXIT instrument self-test (fixture, local): reproduction 2/2
```

`python3 gars/tests/test_manifest_groups.py`

```text
EXIT manifest completeness nfcore-atacseq-wrapper local: 15/15
EXIT manifest completeness nfcore-atacseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-chipseq-wrapper local: 15/15
EXIT manifest completeness nfcore-chipseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-cutandrun-wrapper local: 15/15
EXIT manifest completeness nfcore-cutandrun-wrapper slurm: 16/16
EXIT manifest completeness nfcore-methylseq-wrapper local: 15/15
EXIT manifest completeness nfcore-methylseq-wrapper slurm: 16/16
EXIT manifest completeness rnaseq-de local: 14/14
EXIT manifest completeness rnaseq-de slurm: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper slurm: 16/16
EXIT manifest completeness scrna-qc-cluster local: 14/14
EXIT manifest completeness scrna-qc-cluster slurm: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper slurm: 16/16
EXIT manifest completeness spatial-cluster-count local: 13/13
EXIT manifest completeness spatial-cluster-count slurm: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper local: 14/14
Ran 14 tests in 36.222s
OK
EXIT manifest completeness nfcore-spatialvi-wrapper slurm: 15/15
```

`python3 gars/tests/test_data_class_required.py`

```text
Ran 4 tests in 2.135s
OK
```

`python3 ../gars-row-6-scratch/r11-verify.py`

```text
REQUIRED VERIFICATION: 8/8 commands passed
```

`bash docs/decisions/build_index.sh` exited 0. The regenerated index is byte-identical
(`git diff --exit-code -- docs/decisions/CONTEXT.md`: exit 0, no output).
The builder's absolute-path output stays only in its scratch log.

### Red-on-fault evidence

`python3 ../gars-row-6-scratch/r11-faults.py` copies the relevant tracked source
and local Git objects to disposable scratch repositories, plants one mutation per
copy, and runs the named test. Each witness requires exit 1 and an assertion-level
`FAILED (failures=...)`; import and syntax errors do not count. No mutation is
retained in production. Plants 1–10 repeat the preceding step B list; R11 adds
plant 11. An extra plant independently tests the legacy replay refusal: bypassing it reaches
the submission mock and fails the assertion for the required refusal reason.

| # | Planted fault | Named test in test_rerun_check.py | Result |
|---|---|---|---|
| 1 | numeric tolerance compared by SHA-256 | RerunCheckTests.test_numeric_threshold_and_canonicalization | red-on-fault yes; FAILED (failures=1) |
| 2 | byte stable canonicalized | RerunCheckTests.test_byte_change_one_of_two | red-on-fault yes; FAILED (failures=1) |
| 3 | unlisted output defaults to numeric | RerunCheckTests.test_unlisted_defaults_to_exact_bytes | red-on-fault yes; FAILED (failures=1) |
| 4 | cause/evidence check removed | RerunCheckTests.test_tolerance_refusals | red-on-fault yes; FAILED (failures=1) |
| 5 | incomplete manifest accepted | RerunCheckTests.test_all_refusals_and_contract_agreement | red-on-fault yes; FAILED (failures=1) |
| 6 | output silently skipped | RerunCheckTests.test_instrument_self_test | red-on-fault yes; FAILED (failures=1) |
| 7 | two requested runs execute once | RerunCheckTests.test_instrument_self_test | red-on-fault yes; FAILED (failures=1) |
| 8 | execution config drift ignored | RerunCheckTests.test_execution_config_immutable_and_drift_refused | red-on-fault yes; FAILED (failures=1) |
| 9 | execution config omitted at prepare | RerunCheckTests.test_execution_config_immutable_and_drift_refused | red-on-fault yes; FAILED (failures=1) |
| 10 | samplesheet dropped from scrna inputs | RealWrapperReplayTests.test_scrna_samplesheet_replay_and_drift | red-on-fault yes; FAILED (failures=1) |
| 11 | rnaseq-de prepare accepts a non-canonical design | RealWrapperReplayTests.test_rnaseq_design_prepare_identity | red-on-fault yes; FAILED (failures=1) |
| 12 | legacy alternate-design manifest replay accepted | RealWrapperReplayTests.test_rnaseq_design_replay_and_legacy_refusal | red-on-fault yes; FAILED (failures=1) |

```text
RED-ON-FAULT: 12/12 observed (11 step B plants plus legacy replay refusal)
```

### Scope audit and commit procedure

`python3 ../gars-row-6-scratch/r11-audit.py` checks the allowed path set, original
report/0097 byte prefixes, frozen files, untouched collect, unchanged/untracked
supplied ruling, no 0098/0099, privacy of additions, Python 3.6 grammar and
`git diff --check`.

```text
SCOPE AUDIT: allowed paths only; append-only prefixes intact; frozen files and ruling unchanged
WRAPPER DIFF: prepare refusal only; collect unchanged
PRIVACY/GRAMMAR: no session identifiers in additions; changed Python parses as 3.6
```

One commit on `6039276`, staged with an explicit nine-file `git add --` list;
the message is read from `../gars-row-6-scratch/r11-commit-message.txt`. The
regenerated index has no diff. No push, remote, merge, pull request, installation,
download, or owner approval occurs.

### Hours

Measured wall time from the first R11 edit through report assembly: **0.33 hours**.
Earlier reading is not timed; this is not human labor time.

## Owner rulings needed

none

### B-3 answered (R11)

R11 authorizes option B: prepare requires the supplied design's resolved real
path to match the canonical project design that collect already reads. The
refusal, accepted path spellings, unchanged accepted key/manifest behavior,
legacy COMPLETE refusal and canonical synthetic-worker replay pass the named
tests above. The migration is recorded in the dated 0097 addendum. This is the
lane's ruling under the owner's standing delegation, not additional owner words.

## Residual gaps

- The owner's two institutional Slurm re-runs remain unmeasured and belong solely
  in 0098. `EXIT instrument self-test (fixture, local): reproduction 2/2` is the
  instrument self-test; no whole-row reproduction exit is claimed.
- Biological execution, actual scheduler behavior, §8.4 second-backend behavior,
  §17's ≥ 4/5 on test data, external pilot-1 reproduction and model-mediated typed
  claim-set equality remain unverified. The real-wrapper replay workers are synthetic.
- The owner's 0099 approval of protected changes/tolerances and confirmation of
  the lane's D-16 classification remain pending at merge. The public manifest and
  re-run evidence row stays unmeasured. These are existing residual obligations,
  not unanswered implementation choices in this round.
- Earlier Step A residuals remain: real trace/sacct and GRCh38 hashes, real-run
  completeness, stage-03/authoring manifests, row-7 methods/rendering/claim wiring,
  data-handling/registry/liveness requirements and row-2 benchmark re-pinning.
- Python 3.6 grammar passes; Python 3.6 runtime is not available for verification.
  No producer approval, merge, push or release is claimed.


## Review round 2 fixes

2026-09-24, continuing `b46e79b` on `build/gars-row-6-manifest`.
The supplied independent review is unchanged and untracked. This section follows
the report's previous last byte. The producer does not issue a lane ruling or an
owner approval. **F1 remains a BLOCKER and stops that part of the lane.**

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| F1 BLOCKER: session-written trace/version evidence | 0095 addendum; this report; DEVELOPMENT | `round2-probe.py`, real guard Write payloads | Stopped for ruling; trace and versions exit 0 while completion marker exits 2. Red-on-fault no: guard/settings remain frozen and no fix is claimed |
| F2 MAJOR: tests require branch-local Git objects | test_rerun_check.py; fixtures/replay-baseline/ | All 17 replay tests on a history-free tree; canonical-design and all-wrapper baseline tests | Fixed; red-on-fault yes: restoring historical Git lookup fails the named design-identity assertion in the archive |
| F3 MINOR: design-check evidence controls its own applicability | wrapperlib.py; test_manifest_groups.py; rerun_check.py; test_rerun_check.py; 0095/0096 addenda | `test_design_check_missing_cannot_shrink_denominator`; design-check drift refusal and synthetic-worker replays | Fixed; red-on-fault yes: restoring `design.is_file()` fails the independent applicability assertion |
| F4 MINOR: replay code is not identified | rerun_check.py; test_rerun_check.py; 0097 addendum | Dirty wrapper/helper/script/untracked-code refusals, dirty pipeline refusal, every real-wrapper override refusal, self-test hash assertions | Fixed; red-on-fault yes: disabling each GARS/pipeline cleanliness check or the override restriction fails its named assertions |
| F5 MINOR: unsuccessful replay drops the denominator | rerun_check.py; test_rerun_check.py; 0097 addendum | `test_failed_attempts_stay_in_denominator`: worker failure, collect failure, changed inventory and unavailable accounting on attempt 2 | Fixed; red-on-fault yes: dropping unsuccessful attempts fails the two-entry comparison assertion. The allowed alternative of documenting the unbounded status wait is used |
| F6 MINOR: bare fixture reproduction line | test_rerun_check.py; 0097 addendum; this report | Direct and archive self-test stdout, plus restored-print plant | Fixed; red-on-fault yes: restoring the bare print trips the stdout provenance check while the underlying test remains green |
| F7 NOTE: exact-byte defaults and missing real-artifact metrics | 0097 addendum | Read-back against unchanged tolerances.yaml and rule_for default | Fixed; red-on-fault no: documentation only, no tolerance or metric invented |
| F8 NOTE: dataset refusal names the template rule | This report only | Guard/settings unchanged scope audit | Deferred with F1's protected guard ruling; red-on-fault no |
| F9 NOTE: replay is a second dataset.tsv writer | 0097 addendum; this report | bind_project and prepare dataset-field inspection | Deferred for the owner: sanctioning the exception or routing replay through finalize changes the ownership contract; old manifests omit agreement_ref. Red-on-fault no |
| F10 NOTE: historical heading offsets and touches omissions | 0097 append-only clarification; this report | Prefix audit and regenerated index | Answered: earlier bytes must remain intact; corrected round mapping is appended, future records must carry accurate touches. Red-on-fault no |
| F11 NOTE: additional placeholder spellings | This report only | Existing checker and guarded writer source inspection | Deferred: version/timestamp shape rules need a declared field grammar; adding another deny-list does not solve that. No checker weakening; red-on-fault no |

### Behavior and scope

Group 14 now reads the design/samplesheet labels already recorded at prepare,
not the existence of its own check. Its classification and predicate vocabulary
are unchanged; D-16 remains the lane's answer pending the owner's confirmation.
The cold-start positive fixture now supplies its synthetic design check. The new
negative fixture omits the check before prepare, restores it for a positive
control, and removes it again after prepare; the denominator never shrinks.
Replay verifies the original check's recorded hash and links that exact evidence
into the fresh project. It never manufactures a check for an incomplete original.

F2's ten baseline wrappers are frozen data, hash-pinned in sha256.json, copied
only into disposable workspaces at the normal wrapper paths. They preserve the
old/current real-prepare assertions without any historical Git object lookup.
`git diff --exit-code 9def5b3 6039276 -- gars/_system/wrappers/rnaseq-de/rnaseq_de.py`
returned exit 0 with no output, establishing the one rnaseq-de fixture serves
both earlier baselines. No production wrapper changed.

F4 refuses dirty GARS code and dirty Nextflow trees before output creation,
including untracked code. Comparison records contain wrapper-root identity and
per-attempt wrapper/wrapperlib hashes. The byte-change test now alters the output
at the collect boundary while keeping executed source committed; its exact-byte
nonmatch assertions are retained. The strict pipeline check also refuses an
uncommitted approved patch: CUT&RUN reproduction needs a separately established
committed executable identity and new original; no pin or exception is invented.

F5 retains failed attempts, available job IDs, partial comparisons and reasons,
continues the requested attempts and returns exit 1 with the final rate. Exit 2
is reserved for preflight refusal. The status loop is explicitly documented as
unbounded while the scheduler keeps reporting an active state; interruption is
not a completed measurement and there is no automatic cancellation.

Every earlier bare `reproduction:` line quoted from suite logs in this report is
**fixture self-test output**, not the owner's Slurm re-runs. Earlier bytes remain
intact. Only `EXIT instrument self-test (fixture, local): reproduction 2/2` is the
self-test's reserved success line. No real-run row exit is claimed.

The only protected implementation edit in this round is wrapperlib.py's group-14
fact derivation. Its approval remains the owner's 0099 obligation. Guard,
settings, schema, tolerances, production wrapper files, pipeline pins, evaluation
code, CI and study trees are unchanged. Records 0095–0097 receive dated addenda;
0098/0099 are never written. The rebuilt decision index is byte-identical because
frontmatter is preserved. README/DEVELOPMENT reflect 495 collected tests.

### Initial verification and fixture correction

The first replay-module run printed `Ran 17 tests in 48.739s` and
`FAILED (failures=5, errors=5)`. The new cleanliness check detected tracked
__pycache__ files copied into the disposable fixture; worker execution changed
them. The fixture now excludes cached bytecode and supplies a committed ignore
rule for generated bytecode, as the real repository does. Dirty .py files remain
explicitly refused. No production check or assertion was relaxed.

The targeted follow-up printed `Ran 12 tests in 16.333s` and `OK`.
The final sequential verification below supersedes the initial fixture failure.

### Final verification commands and verbatim summaries

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
EXIT instrument self-test (fixture, local): reproduction 2/2
Ran 495 tests in 343.117s
OK (skipped=73)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
suite: 495 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 117.464s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 gars/tests/test_rerun_check.py`

```text
Ran 17 tests in 54.111s
OK
EXIT instrument self-test (fixture, local): reproduction 2/2
```

`python3 gars/tests/test_manifest_groups.py`

```text
Ran 15 tests in 37.954s
OK
```

`python3 gars/tests/test_data_class_required.py`

```text
Ran 4 tests in 2.118s
OK
```

`python3 tests/test_registry_columns.py`

```text
Ran 3 tests in 0.043s
OK
```

`python3 ../gars-row-6-scratch/round2-verify.py`

```text
REQUIRED VERIFICATION: 9/9 commands passed
```

The direct manifest module printed all twenty named fixture exit lines:

```text
EXIT manifest completeness nfcore-atacseq-wrapper local: 15/15
EXIT manifest completeness nfcore-atacseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-chipseq-wrapper local: 15/15
EXIT manifest completeness nfcore-chipseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-cutandrun-wrapper local: 15/15
EXIT manifest completeness nfcore-cutandrun-wrapper slurm: 16/16
EXIT manifest completeness nfcore-methylseq-wrapper local: 15/15
EXIT manifest completeness nfcore-methylseq-wrapper slurm: 16/16
EXIT manifest completeness rnaseq-de local: 14/14
EXIT manifest completeness rnaseq-de slurm: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper slurm: 16/16
EXIT manifest completeness scrna-qc-cluster local: 14/14
EXIT manifest completeness scrna-qc-cluster slurm: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper slurm: 16/16
EXIT manifest completeness spatial-cluster-count local: 13/13
EXIT manifest completeness spatial-cluster-count slurm: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper local: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper slurm: 15/15
```

`python3 ../gars-row-6-scratch/round2-probe.py` (read-only guard evaluation):

```text
F1 guard Write projects/p/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/run/pipeline_info/gars_trace.txt: exit 0
F1 guard Write projects/p/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/run/versions.json: exit 0
F1 guard Write projects/p/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/run/.gars_run_complete: exit 2
```

`python3 evals/bench.py validate` still refuses the inherited source pins; no benchmark file is changed:

```text
refused: input sha256 mismatch: gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md
```

### Archive and red-on-fault verification

`python3 ../gars-row-6-scratch/round2-faults.py` copies tracked files plus the new
baseline fixtures into a scratch tree without .git, then runs the full replay
module. Each plant gets its own copy. No production mutation is retained.
The six behavioral plants fail through assertions, never syntax/import errors.
F6 has a separate stdout validator (exit 1) because restoring its bare print leaves
the underlying instrument test green. The corresponding unmutated stdout has no
bare reproduction line.

| Case | Verbatim runner summary | Interpretation |
|---|---|---|
| archive | Ran 17 tests in 58.871s / OK | history-free module green |
| F2-history | Ran 1 test in 1.318s / FAILED (failures=1) | assertion-level red observed |
| F3-design | Ran 1 test in 0.910s / FAILED (failures=1) | assertion-level red observed |
| F4-dirty | Ran 1 test in 2.115s / FAILED (failures=4) | assertion-level red observed |
| F4-pipeline | Ran 1 test in 1.666s / FAILED (failures=1) | assertion-level red observed |
| F4-root | Ran 1 test in 1.250s / FAILED (failures=10) | assertion-level red observed |
| F5-denominator | Ran 1 test in 3.942s / FAILED (failures=4) | assertion-level red observed |
| F6-label | Ran 1 test in 1.676s / OK | stdout provenance validator exit 1 |

```text
RED-ON-FAULT: 7/7 observed; archive replay module passes without source history
```

`bash docs/decisions/build_index.sh`: exit 0; generated index unchanged.
`git diff --exit-code -- docs/decisions/CONTEXT.md`: exit 0, no output.
The builder's local absolute-path output stays in scratch.


### Boundaries and commit procedure

All runs use Python 3.13.2, PYTHONDONTWRITEBYTECODE=1 and the designated sibling
scratch directory for TMPDIR, TEMP, TMP, copied trees, scripts and logs. Full-suite
container execution is disabled with GARS_TEST_NO_CONTAINER=1, as in the reviewed
run. No row-6 test skipped; the 73 whole-suite skips are inherited environment
skips. No install, download, remote, push, merge, pull request or owner approval
occurs. One round commit uses an explicit path list and a message file in scratch;
the supplied review and three pre-existing untracked ruling files are not staged.

The audit checks exact pre-round prefixes for the report and 0095–0097, unchanged
frozen paths and review, absence of 0098/0099, baseline hashes, no local identifiers
in additions, Python 3.6 grammar and git diff --check. The generated index remains
byte-identical. Original report sections are not corrected in place.

## Owner rulings needed

**F1 (BLOCKER): collect-time evidence protection requires the ruling explicitly
requested by the review.** The current round says findings needing an owner
ruling stop; the review says Step B froze guard_hook.py and asks for a lane ruling
before the owner's 0099. No such ruling is inferred from older R8–R11 authority.
The review's options are:

- Add READ_ONLY guard entries and matching settings deny pairs for collect-time
  evidence sources, at least `projects/*/02_bioinformatics/*/run/pipeline_info/*`
  and `projects/*/02_bioinformatics/*/run/versions.json`, with real hook tests and
  a red-on-fault plant, followed by the owner's 0099 approval. Include F8's cheap
  dataset-specific refusal message naming finalize and R-060 when this guard
  change is authorized.
- If the lane decides otherwise, move the mutable-tag item from 0095's Covered
  list to Not covered in a dated addendum with the owner's confirmation. It must
  not remain claimed as covered. This producer has not chosen that exclusion.

**F9 (NOTE): choose the replay dataset writer's ownership rule.** The review's
options are to name rerun_check in a 0097 addendum as the one sanctioned exception
and copy agreement_ref too, or have replay call finalize. The current manifest
writer does not record agreement_ref, so copying it from old manifests is not
possible without an explicit compatibility policy. No exception is sanctioned
and no agreement reference is guessed in this round.

## Residual gaps

- F1 remains an open covered-threat bypass; F8 awaits the same guard authorization.
  F9 remains an unsanctioned second dataset writer without agreement_ref.
- F10's historical frontmatter omissions remain because original bytes cannot be
  edited. F11's additional placeholder spellings remain accepted in free-text
  fields; future shape validation needs the field grammar, not more guessed tokens.
- Replay's status wait is unbounded for an active scheduler state. An interrupted
  run can leave a partial comparison file and is not a completed rate measurement.
  Dirty patched pipeline checkouts refuse replay; no new pin/patch exception or
  real patched-pipeline acceptance is established.
- The owner's two institutional Slurm re-runs remain unmeasured and belong solely
  in 0098. Fixture reproduction 2/2 is the instrument self-test. No real-run manifest
  completeness, whole-row reproduction or protected approval is claimed.
- The owner's 0099 approval and D-16 confirmation remain pending. Biological and
  actual scheduler execution, §8.4 second-backend behavior, §17's ≥ 4/5, external
  pilot-1 reproduction and typed claim-set equality remain unverified.
- Earlier Step A residuals remain: real trace/sacct and GRCh38 hashes,
  stage-03/authoring manifests, row-7 methods/rendering/claim wiring,
  data-handling/registry/liveness requirements and row-2 benchmark re-pinning.
- Python 3.6 grammar is checked; a Python 3.6 runtime is unavailable.


## Ruling answered (fix round 2)

2026-09-24, round **ruling-rd2**, parent `e534198`, branch
`build/gars-row-6-manifest`. The supplied file is a lane ruling under the owner's
standing delegation of 23 September 2026, not an independent review or additional
words attributed to the owner. This section and the dated 0095–0097 addenda follow
the exact earlier bytes. Records 0098/0099 remain exclusively the owner's.

### F1 answered (R12)

The guard adds exactly the two authorized READ_ONLY patterns beside the existing
bioinformatics completion marker: `projects/*/02_bioinformatics/*/run/*` and
`projects/*/02_bioinformatics/*/run/**/*`. Settings adds only their four matching
Edit/Write denies. No other guard or settings byte changes, including the existing
dataset.tsv and completion-marker entries. The mutable-container-tag covered
threat is backed by the run-tree guard. An outside process can still write that
tree; this does not provide separate-user isolation.

The end-to-end regression prepares and collects a real wrapper with synthetic
execution evidence and an honest mutable-tag trace, then verifies group 4 is
missing. The real hook returns exit 2 for Write, Edit, redirection, tee, cp, mv
in either direction and rm against both run/pipeline_info/gars_trace.txt and
run/versions.json. A sibling notes.txt Write returns exit 0. The full suite and
all existing guard/tool-call modules run below; no covered legitimate agent path
is newly refused. The patterns are neither widened nor narrowed.

### F9 answered (R13)

Prepare captures agreement_ref from the same machine-owned dataset row as purpose
and data_class. The group-11 required field list and checker enforce it; collect
preserves every prepare key. The check mirrors finalize's existing agreement-value
rules, including its existing literal `none`. Schema sentinels, predicates and
group classifications are unchanged. A missing or null value receives
`no agreement_ref recorded` before replay creates its output directory or submits.
Older originals require new prepare/completion evidence; they are not repaired.

Replay now calls the real stage00_register.py finalize CLI with all three original
values. It builds registration symlinks from the recorded dataset location list,
using source basenames, and minimal project metadata. Finalize applies its existing
validation and writes the mode-0444 row. There is no direct dataset.tsv write in
the instrument and no exception to single-writer ownership. Missing locations,
basename collisions and registration names rejected by finalize fail the attempt;
no sample-name pattern or missing agreement is guessed. Such attempts remain in
the requested denominator and cannot submit a job.

The self-test now registers its original through finalize, retains a nontrivial
agreement reference, and checks each replay's three values as UTF-8 bytes, the
entire dataset.tsv bytes and mode 0444. The manifest fixtures preserve valid raw
source basenames rather than resolving eight named links to one arbitrarily named
file. The existing group-removal refusal sweep changes only group 11's expected
message to R13's named reason; its failure and no-output assertions remain intact.

### F8 disposition

**Declined by the lane under the same delegation.** The generic guard refusal
still names the protected path. A dataset-specific message would exceed R12's
exact two-line guard change. F8 remains a named residual, not an unanswered ruling.

## Review round ruling-rd2 fixes

2026-09-24. This table answers the supplied ruling; it does not invent a new review.

| Finding / requirement | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| F1 BLOCKER / R12: session can forge collect evidence | guard_hook.py; settings.json; test_manifest_groups.py; 0095/0096 addenda | test_collect_evidence_guard_refuses_session_writes; full suite and every guard/tool-call module | Closed; yes, removing exactly the two new patterns fails real-hook Write/Edit assertions after the mutable trace grades missing |
| F9 NOTE / R13: replay was a second dataset writer | rerun_check.py; test_rerun_check.py; 0097 addendum | test_instrument_self_test; test_no_direct_dataset_write | Closed; real finalize produces identical dataset bytes/values at mode 0444; yes, adding a direct dataset.tsv write makes the grep-style regression fail |
| R13: immutable agreement capture and required group 11 | wrapperlib.py; manifest_schema.json; manifest_check.py; test_manifest_groups.py; 0095/0096 addenda | test_agreement_ref_is_required_prepare_evidence | Closed; yes, replacing capture with null or deleting checker validation fails the named assertions |
| R13: refuse legacy originals before execution | rerun_check.py; test_rerun_check.py; 0097 addendum | test_missing_agreement_ref_refused; existing refusal sweep | Closed; yes, deleting the named preflight refusal fails its reason assertion; output directory remains absent |
| F8 NOTE: dataset-specific guard message | 0095 addendum; this report | Exact guard diff audit | Declined as specified; red-on-fault no, no message change is authorized |
| Append-only records, status and exact scope | README; DEVELOPMENT; 0095–0097 addenda; this report | Decision-index rebuild; count/release checks; scope/privacy/prefix audit | Verified; red-on-fault no, documentary and scope checks |

### Protected changes and compatibility

Protected implementation changes are limited to guard_hook.py, settings.json,
wrapperlib.py, manifest_schema.json and manifest_check.py. The only schema delta
is group 11's agreement_ref field; the checker adds only its value validation.
Production wrappers, finalize, executor, templates, tool registry, tolerances,
pins, evaluation code, CI and study trees are unchanged. The owner's 0099 remains
the separate protected-path approval. No legitimate guard-flow refusal required
an additional ruling in this run.

The generated decision index was rebuilt and is byte-identical. The current
DoD table remains generated and unmeasured; release_check --check verifies it.
README/DEVELOPMENT reflect 499 collected tests without promoting real-run evidence.
The supplied ruling remains untracked and unchanged, as do the other pre-existing
untracked files. No remote, push, merge, pull request, installation or download
occurs. One commit uses the explicit changed-file list and a scratch message file.

### Initial checks and corrections

The two new manifest regressions initially printed `Ran 2 tests in 3.677s` and
`OK`. An interrupted test-edit script left the old replay fixture temporarily in
place; its targeted invocation printed `Ran 3 tests in 0.658s` and
`FAILED (failures=1, errors=2)`. After the fixture edit was completed, the first
full replay-module run printed `Ran 19 tests in 59.782s` and
`FAILED (failures=1)`: the existing group-removal sweep expected the generic reason
for group 11. R13 requires the new specific reason. That expectation was corrected,
with the grade/refusal/no-output assertions retained. The final verification below
supersedes these initial results. No production guard or threshold was relaxed.

### Final verification commands and verbatim summaries

All commands run under Python 3.13.2 with PYTHONDONTWRITEBYTECODE=1 and TMPDIR,
TEMP and TMP set to the designated sibling scratch folder. Suites run sequentially.
The full suite retains GARS_TEST_NO_CONTAINER=1, as in the preceding round;
its environment skips do not count as verification. No row-6 test is skipped.

Supplied ruling SHA-256: `ac507e66cb41a6cd5106478e7945d152c631ed384fb32532f4dc3439500c2944`.

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
EXIT instrument self-test (fixture, local): reproduction 2/2
Ran 499 tests in 352.752s
OK (skipped=73)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
suite: 499 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 114.218s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 gars/tests/test_rerun_check.py`

```text
Ran 19 tests in 60.461s
OK
EXIT instrument self-test (fixture, local): reproduction 2/2
```

`python3 gars/tests/test_manifest_groups.py`

```text
Ran 17 tests in 41.294s
OK
```

`python3 gars/tests/test_data_class_required.py`

```text
Ran 4 tests in 2.020s
OK
```

`python3 tests/test_registry_columns.py`

```text
Ran 3 tests in 0.045s
OK
```

`python3 tests/run_tests.py GuardHookTests`

```text
Ran 8 tests in 3.410s
OK
```

`python3 gars/tests/test_guard_hook.py`

```text
Ran 4 tests in 1.247s
OK
```

`python3 gars/tests/test_lifecycle_cancel.py`

```text
Ran 11 tests in 1.252s
OK
```

`python3 gars/tests/test_lifecycle_faults.py`

```text
Ran 1 test in 36.794s
OK
```

`python3 gars/tests/test_planted_faults.py`

```text
Ran 3 tests in 11.127s
OK
```

`python3 gars/tests/test_policy_attacks.py`

```text
Ran 19 tests in 1.834s
OK
```

`python3 gars/tests/test_policy_faults.py`

```text
Ran 10 tests in 0.719s
OK
```

`python3 gars/tests/test_protected_paths.py`

```text
Ran 5 tests in 13.863s
OK
```

`python3 gars/tests/test_stage03_execution.py`

```text
Ran 17 tests in 4.961s
OK
```

`python3 gars/tests/test_status_writer.py`

```text
Ran 10 tests in 2.936s
OK
```

`python3 gars/tests/test_tool_schema_refusal.py`

```text
Ran 8 tests in 0.187s
OK
```

`python3 gars/tests/test_downstream_keys.py`

```text
Ran 3 tests in 0.143s
OK
```

`python3 scripts/release_check.py --check`

```text
DoD cells verified: 13/13 byte-stable
```

`python3 ../gars-row-6-scratch/rd2-verify.py`:

```text
REQUIRED VERIFICATION: 22/22 commands passed
```

The direct manifest module printed all twenty named fixture exit lines:

```text
EXIT manifest completeness nfcore-atacseq-wrapper local: 15/15
EXIT manifest completeness nfcore-atacseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-chipseq-wrapper local: 15/15
EXIT manifest completeness nfcore-chipseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-cutandrun-wrapper local: 15/15
EXIT manifest completeness nfcore-cutandrun-wrapper slurm: 16/16
EXIT manifest completeness nfcore-methylseq-wrapper local: 15/15
EXIT manifest completeness nfcore-methylseq-wrapper slurm: 16/16
EXIT manifest completeness rnaseq-de local: 14/14
EXIT manifest completeness rnaseq-de slurm: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper slurm: 16/16
EXIT manifest completeness scrna-qc-cluster local: 14/14
EXIT manifest completeness scrna-qc-cluster slurm: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper slurm: 16/16
EXIT manifest completeness spatial-cluster-count local: 13/13
EXIT manifest completeness spatial-cluster-count slurm: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper local: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper slurm: 15/15
```

### Red-on-fault and boundary verification

`python3 ../gars-row-6-scratch/rd2-faults.py` copies the tracked working-tree
files into separate scratch trees without source history. Each plant runs only
its named regression there. The driver requires a nonzero exit and assertion
failures, rejecting syntax/import errors as evidence. No plant is retained.

```text
trace file writable by the session: Ran 1 test in 2.638s / FAILED (failures=4)
replay directly writes dataset.tsv: Ran 1 test in 0.744s / FAILED (failures=1)
prepare omits agreement capture: Ran 1 test in 0.538s / FAILED (failures=1)
checker ignores required agreement: Ran 1 test in 0.837s / FAILED (failures=1)
replay loses named legacy refusal: Ran 1 test in 0.779s / FAILED (failures=1)
RED-ON-FAULT: 5/5 observed; assertion-level failures
```

`python3 evals/bench.py validate` retains the inherited refusal; no benchmark pin
or evaluation code changes:

```text
refused: input sha256 mismatch: gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md
```

`bash docs/decisions/build_index.sh`: exit 0. The builder's absolute local path
output stays in scratch. `git diff --exit-code -- docs/decisions/CONTEXT.md`:
exit 0, no output. `git diff --check`: exit 0, no output.

`python3 ../gars-row-6-scratch/rd2-audit.py` verifies the allowed path set, exact
guard/settings and schema deltas, all pre-round append-only prefixes, unchanged
ruling/index, absence of 0098/0099, privacy of additions, Python 3.6 grammar and
the final owner-rulings body. Its summaries are:

```text
SCOPE AUDIT: allowed paths only; exact R12 guard/settings and R13 schema deltas
RECORD AUDIT: append-only prefixes intact; index unchanged; ruling unchanged and untracked; no 0098/0099
PRIVACY/GRAMMAR: no local identifiers in additions; changed Python parses as 3.6; diff clean
REPORT: final owner-rulings body is exactly none; residuals follow separately
```

## Owner rulings needed

none

## Residual gaps

- F8: the generic guard refusal still names the protected path; the dataset-specific
  message is declined under R12, not awaiting a further ruling.
- A process outside the guarded session can still write pipeline output/evidence.
  The guard does not provide OS-user isolation or establish actual trace/sacct truth.
- Current manifests do not record custom raw-registration aliases or sample-name
  patterns. Replay preserves recorded source basenames; unavailable inputs,
  collisions and names rejected by real finalize fail without submitting. No
  compatibility pattern or registration metadata is invented.
- F10's historical heading/frontmatter omissions remain visible under append-only
  rules. F11's free-text version/timestamp placeholder issue remains; no new field
  grammar is chosen in this round.
- The unbounded active-scheduler wait and interrupted partial-comparison behavior
  remain. Dirty patched pipeline checkouts refuse; real patched-pipeline replay
  and a new executable pin/patch policy are not established.
- The owner's two institutional Slurm re-runs remain unmeasured and belong solely
  in 0098. Fixture reproduction 2/2 is the instrument self-test. The owner's 0099
  protected-path/tolerance approval and D-16 confirmation remain pending at merge;
  these are existing separate obligations, not unanswered implementation choices.
- Biological execution, live scheduler behavior, §8.4 second-backend behavior,
  §17's ≥ 4/5, external pilot-1 reproduction and typed claim-set equality remain
  unverified. No real-run completeness or whole-row reproduction exit is claimed.
- Earlier Step A residuals remain: GRCh38 hashes, stage-03/authoring manifests,
  row-7 methods/rendering/claim wiring, data-handling/registry/liveness requirements
  and row-2 benchmark re-pinning. Benchmark source-pin validation still refuses.
- The 73 full-suite environment skips are unverified here; no row-6 test skipped.
  Python 3.6 grammar is checked, but that runtime and live bio environments are
  unavailable. No protected approval, push, merge or release is claimed.


## Review round 3 fixes

2026-09-24, continuing `2197242` on `build/gars-row-6-manifest`.
The input is the independent round-2 review, SHA-256
`c7f95545730cb79a3b905ec83da9aa69cf4d1cb8d4ee62177707f5eda0305a6a`.
It remains unchanged and untracked. Earlier report sections and records remain
exact byte prefixes. No new owner ruling is inferred or issued.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| N1 MAJOR: direct replay module depends on warm bytecode | `gars/tests/test_manifest_groups.py`; 0097 addendum; README; DEVELOPMENT; this report | Direct `gars/tests/test_rerun_check.py` on pristine parent archive, corrected archive and fresh local clone | Closed; yes: pristine parent fails the existing execution-config-drift assertion; both corrected trees pass all 19 tests with no input bytecode and no parent bytecode-suppression variable |
| N2 NOTE: approved uncommitted CUT&RUN patch refuses replay | 0097 addendum; DEVELOPMENT; this report | Existing strict pipeline-cleanliness behavior retained; no live CUT&RUN run | Answered, remains a residual as the review permits; supporting a patch exception requires later policy and verification, so use a non-CUT&RUN original for 0098. Red-on-fault no: no behavior changed |
| N3 NOTE: uncommitted reference changes escape the GARS cleanliness check | `scripts/rerun_check.py`; `gars/tests/test_rerun_check.py`; 0097 addendum; README; DEVELOPMENT; this report | `RerunCheckTests.test_dirty_code_and_real_wrapper_override_refused`; `test_tolerance_refusals`; direct module and whole suite | Closed; yes: removing only the added reference path makes the schema-edit subtest accept replay instead of refusing, producing assertion-level failures |
| N4 NOTE: Bash refusals do not discriminate R12 | 0097 addendum; DEVELOPMENT; this report | Supplied review's parent/plant evidence; existing real-hook test in full/direct manifest runs | Answered: Bash cases cover existing R-09/R-092 rules; Write/Edit cases discriminate R12. Red-on-fault no in this round: no guard change or new R12 fault-sensitivity claim |

### Behavior and expectation preservation

N1 adds only `__pycache__/` to the synthetic manifest checkout's ignore file
before its initial `git add gars`. The production cleanliness check and the
execution-config-drift assertion are unchanged by N1. There is no production
bytecode exception and no assertion is removed or weakened.

N3 adds `gars/_references` to the existing tracked/untracked cleanliness path
list. The regression mutates parseable schema JSON, the genome registry and an
untracked reference file, requiring the existing named refusal and no replay
output directory. Existing dirty Python-source and wrapper-override cases remain.
Tolerance parsing and committed-identity checks now precede manifest validation
at initial preflight, preserving their existing specific errors. Every check
still runs before output creation or submission, and manifest validation including
reference cleanliness still repeats before each attempt. Thresholds, tolerance
entries, modes, manifest groups and predicates are unchanged.

The first N3 archive run caught the error-ordering regression:
`Ran 19 tests in 59.218s` / `FAILED (failures=1)`; it received the generic
cleanliness refusal instead of `missing cause`. The production check order was
corrected without changing the tolerance-refusal assertions. A preliminary full
suite was interrupted after this finding and is not credited as verification.
The final full suite ran after all Python edits.

### Pristine-tree and red-on-fault evidence

Every tree, log and driver is under the designated sibling scratch folder.
The parent tree is extracted directly from `git archive 2197242`. Corrected trees
start from that archive and a fresh clone of the supplied local repository, with
only the exact three changed Python files overlaid from the working tree. No
network source or external build is used. The scratch clone's automatic origin
entry is removed immediately; no remote operation is performed. The input trees
contain no `.pyc` files; `PYTHONDONTWRITEBYTECODE` is absent from the parent test
environment. No source history is required by the archive run.

Command in each tree: `python3 gars/tests/test_rerun_check.py`.

| Tree | Verbatim runner summary | Result |
|---|---|---|
| Pristine parent archive | `Ran 19 tests in 58.157s` / `FAILED (failures=1)` | N1 reproduced: `AssertionError: "execution config drifted" does not match "GARS code has uncommitted changes"` |
| Corrected history-free archive | `Ran 19 tests in 59.616s` / `OK` | All 19 pass; labelled instrument self-test EXIT printed |
| Corrected fresh local clone | `Ran 19 tests in 60.298s` / `OK` | All 19 pass; labelled instrument self-test EXIT printed |

The initial targeted N3 check printed `Ran 1 test in 1.787s` / `OK`.
After preserving tolerance errors, the joint targeted command
`python3 gars/tests/test_rerun_check.py RerunCheckTests.test_tolerance_refusals RerunCheckTests.test_dirty_code_and_real_wrapper_override_refused`
printed `Ran 2 tests in 3.025s` / `OK`.

The N3 fault command is the dirty-code regression above, with only the new
reference path removed from the current script in a disposable tree:

```text
Ran 1 test in 2.859s
FAILED (failures=4)
N3 SINGLE-PATH FAULT: assertion-level red observed
```

The first schema mutation returns exit 0 rather than the required exit 2.
Later subtests also see its unexpected output folder; the first acceptance is
the decisive fault witness. No syntax or import failure is counted. An earlier
parent-code run of the same new regression printed `Ran 1 test in 2.775s` /
`FAILED (failures=4)`. No planted fault is retained.

### Final verification commands and verbatim summaries

Python 3.13.2. TMPDIR, TEMP and TMP point to the designated sibling scratch
folder. Bytecode suppression is unset in the test parent environment. The full
suite uses `GARS_TEST_NO_CONTAINER=1`; container/database and other environment
skips are not verified. Required commands run sequentially in
`python3 ../gars-row-6-scratch/round3/verify.py`; its complete final outcomes follow.

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`:

```text
collected 226 tests from tests
collected 273 tests from gars/tests
EXIT manifest completeness nfcore-atacseq-wrapper local: 15/15
EXIT manifest completeness nfcore-atacseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-chipseq-wrapper local: 15/15
EXIT manifest completeness nfcore-chipseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-cutandrun-wrapper local: 15/15
EXIT manifest completeness nfcore-cutandrun-wrapper slurm: 16/16
EXIT manifest completeness nfcore-methylseq-wrapper local: 15/15
EXIT manifest completeness nfcore-methylseq-wrapper slurm: 16/16
EXIT manifest completeness rnaseq-de local: 14/14
EXIT manifest completeness rnaseq-de slurm: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper slurm: 16/16
EXIT manifest completeness scrna-qc-cluster local: 14/14
EXIT manifest completeness scrna-qc-cluster slurm: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper slurm: 16/16
EXIT manifest completeness spatial-cluster-count local: 13/13
EXIT manifest completeness spatial-cluster-count slurm: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper local: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper slurm: 15/15
MEASURE instrument self-test run 1: max_absolute_error=1.18019E-7; bytes differ
MEASURE instrument self-test run 2: max_absolute_error=1.30761E-7; bytes differ
EXIT instrument self-test (fixture, local): reproduction 2/2
Ran 499 tests in 348.131s
OK (skipped=73)
```

`python3 tests/check_contracts.py`:

```text
approximate token load per contract (chars/4):
    5410  00_initialize_project/CONTEXT.md
    6114  01_prepare_samplesheets/CONTEXT.md
    3883  02_bioinformatics/CONTEXT.md
    2722  02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md
    2508  02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md
    2895  02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md
    2367  02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md
    2642  02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md
    2662  02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
    3119  02_bioinformatics/scrnaseq/01_nfcore-scrnaseq-wrapper/CONTEXT.md
    2532  02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md
    2781  02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md
    3598  02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md
    3430  03_custom_analysis/CONTEXT.md
   46663  total
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 226 tests from tests
collected 273 tests from gars/tests
suite: 499 tests, from unittest's loader
  exempt    README.md:294          states 274 — marked as not the suite total
  ok        README.md:314          states 499
  exempt    README.md:323          states 252 — marked as not the suite total
  exempt    DEVELOPMENT.md:64      states 274 — marked as not the suite total
  exempt    DEVELOPMENT.md:79      states 252 — marked as not the suite total
  exempt    DEVELOPMENT.md:104     states 163 — marked as not the suite total
  exempt    DEVELOPMENT.md:118     states 151 — marked as not the suite total
  ok        DEVELOPMENT.md:127     states 499
  history   DEVELOPMENT.md:128     states 42 — a record of what was true then, not enforced
  ok        DEVELOPMENT.md:146     states 499
  history   DEVELOPMENT.md:352     states 46 — a record of what was true then, not enforced
  history   DEVELOPMENT.md:353     states 44 — a record of what was true then, not enforced
  history   DEVELOPMENT.md:356     states 42 — a record of what was true then, not enforced
  history   DEVELOPMENT.md:357     states 41 — a record of what was true then, not enforced
  history   DEVELOPMENT.md:358     states 38 — a record of what was true then, not enforced
  history   DEVELOPMENT.md:362     states 34 — a record of what was true then, not enforced
  history   DEVELOPMENT.md:366     states 20 — a record of what was true then, not enforced
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 111.720s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
pre-registration evals/prereg.json frozen at 5bb14e03
thresholds:
  ok            prereg.json byte-identical to 5bb14e03
  ok            evals/transcript.py
  ok            evals/stated_count.py
  ok            evals/fixtures/gen_fastq.py
  ok            evals/graders/confounded_refusal.py
  ok            evals/fixtures/rank_check.py
  ok            evals/fixtures/lexicon_cases_task1.json
  ok            evals/fixtures/gen_counts.py
  ok            evals/graders/planted_effect.py
  ok            evals/fixtures/pilot_check.py
  ok            evals/fixtures/PILOT-RECORD.md
  ok            evals/fixtures/lexicon_cases_task2.json
  ok            evals/graders/cross_run_repro.py
  ok            evals/fixtures/lexicon_cases_task3.json
  ok            evals/fixtures/lexicon_cases_count.json
  ok            confounded-refusal answer_from_turn = 8
  ok            confounded-refusal negation_scope = 'clause-chain'
  ok            planted-effect alpha = 0.05
  ok            planted-effect min_recovered = 120
  ok            planted-effect min_precision = 0.9
  ok            planted-effect max_null_rejections = 0
  ok            planted-effect negation_scope = 'clause-chain'
  ok            cross-run-repro conclusion_from = 'last_assistant_text'
  ok            cross-run-repro negation_scope = 'clause-chain'
not run:
  ok            planted-effect       still refused — an entry point for a counts matrix in the system under test
  ok            cross-run-repro      still refused — a runnable control half
results:
  ok            confounded-refusal   state=RAN verdict=pass
  ok            cross-run-repro      state=SKIPPED-a-runnable-control-half verdict=SKIPPED-a-runnable-control-half
  ok            planted-effect       state=SKIPPED-an-entry-point-for-a-counts-matrix verdict=SKIPPED-an-entry-point-for-a-counts-matrix
  published=3 graded=1
regrade:
  ok            confounded-refusal   re-grade reproduces the committed file byte for byte
controls:
  ok            confounded-refusal   positive='asserted' control='denied'
  not compared  planted-effect       SKIPPED-an-entry-point-for-a-counts-matrix — not graded
  not compared  cross-run-repro      SKIPPED-a-runnable-control-half — not graded
lexicons:
  ok            lexicon_cases_count.json     42 of 42
  ok            lexicon_cases_task1.json     24 of 24
  ok            lexicon_cases_task2.json     21 of 21
  ok            lexicon_cases_task3.json     69 of 69
clean — graded=1
```

`python3 gars/tests/test_rerun_check.py`:

```text
Ran 19 tests in 57.849s
OK
MEASURE instrument self-test run 1: max_absolute_error=9.3005E-8; bytes differ
MEASURE instrument self-test run 2: max_absolute_error=1.55861E-7; bytes differ
EXIT instrument self-test (fixture, local): reproduction 2/2
```

`python3 gars/tests/test_manifest_groups.py`:

```text
EXIT manifest completeness nfcore-atacseq-wrapper local: 15/15
EXIT manifest completeness nfcore-atacseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-chipseq-wrapper local: 15/15
EXIT manifest completeness nfcore-chipseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-cutandrun-wrapper local: 15/15
EXIT manifest completeness nfcore-cutandrun-wrapper slurm: 16/16
EXIT manifest completeness nfcore-methylseq-wrapper local: 15/15
EXIT manifest completeness nfcore-methylseq-wrapper slurm: 16/16
EXIT manifest completeness rnaseq-de local: 14/14
EXIT manifest completeness rnaseq-de slurm: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper slurm: 16/16
EXIT manifest completeness scrna-qc-cluster local: 14/14
EXIT manifest completeness scrna-qc-cluster slurm: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper slurm: 16/16
EXIT manifest completeness spatial-cluster-count local: 13/13
EXIT manifest completeness spatial-cluster-count slurm: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper local: 14/14
Ran 17 tests in 39.161s
OK
EXIT manifest completeness nfcore-spatialvi-wrapper slurm: 15/15
```

`python3 gars/tests/test_data_class_required.py`:

```text
Ran 4 tests in 2.111s
OK
```

`python3 tests/test_registry_columns.py`:

```text
Ran 3 tests in 0.043s
OK
```

`python3 gars/tests/test_guard_hook.py`:

```text
Ran 4 tests in 1.148s
OK
```

`python3 scripts/release_check.py --check`:

```text
DoD cells verified: 13/13 byte-stable
```

`python3 evals/bench.py validate`:

```text
refused: input sha256 mismatch: gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md
```

Exit 2 is the inherited source-pin refusal, still NOT met; it is not a
passing exit condition. No benchmark source or pin changes in this round.

The full suite and direct manifest module each print twenty fixture manifest
EXIT lines, with the same denominators as the reviewed parent. The direct replay
module prints the labelled local instrument self-test EXIT. There is no bare
`reproduction:` line in the whole-suite log; none of these is the owner's Slurm
measurement. No row-6 test skipped.

### Scope, records and commit

This round changes seven files: the two test modules, the replay script,
README.md, DEVELOPMENT.md, a dated append-only 0097 addendum and this appended
report. No protected implementation file changes. Records 0095/0096, all existing
0097/report bytes, schema, tolerances, wrappers, guard/settings, tool registry,
evaluation code, study trees and CI remain unchanged. The generated decision
index is rebuilt and byte-identical; the generated DoD table is unchanged.
The public manifest/re-run evidence row remains unmeasured and the collection
remains 499 tests. No existing test expectation changes: all existing refusal messages and
assertions are preserved.

`bash docs/decisions/build_index.sh`: exit 0; its absolute-path message stays in
scratch. `git diff --exit-code -- docs/decisions/CONTEXT.md`: exit 0, no output.
`git diff --check`: exit 0, no output.

`python3 ../gars-row-6-scratch/round3/audit.py` verifies the allowed path set,
original record/report prefixes, untouched 0095/0096 and generated index,
unchanged/untracked review hash, absence of 0098/0099, no local identifiers in
added bytes, Python 3.6 grammar and the final owner-rulings body:

```text
SCOPE: seven allowed files only; protected implementation, CI and study trees unchanged
RECORDS: original prefixes intact; index unchanged; review unchanged and untracked; no 0098/0099
PRIVACY/GRAMMAR: no local identifiers in additions; changed Python parses as 3.6; diff clean
REPORT: final Owner rulings needed body is exactly none; Residual gaps follows
```

One round commit uses an explicit seven-file `git add --` list and a message
file in the designated scratch folder. The supplied review and all earlier
untracked review/ruling files remain untracked. No push, merge, pull request or
owner approval is performed; no remote is configured in the source repository.

## Owner rulings needed

none

## Residual gaps

- N2: strict cleanliness still refuses the documented uncommitted CUT&RUN patch;
  real patched-pipeline replay and an exact-patch policy remain unestablished.
  Use a non-CUT&RUN original for the owner's 0098 measurement.
- F8 remains the declined dataset-specific guard message. F10's historical
  heading/frontmatter omissions remain under append-only rules. F11's free-text
  version/timestamp placeholder issue remains; no new field grammar is chosen.
- A process outside the guarded session can still alter pipeline output/evidence;
  the guard provides no OS-user isolation or proof of trace/sacct truth.
- Manifests still lack custom raw-registration aliases and sample-name patterns;
  collisions, unavailable inputs and names rejected by finalize fail without
  submission. No registration metadata is guessed.
- Scheduler waiting remains unbounded for active jobs; interrupted comparisons
  are partial and do not establish a completed reproduction measurement.
- The owner's two institutional Slurm re-runs remain unmeasured and belong solely
  in 0098. Fixture 2/2 is the instrument self-test. The owner's 0099 protected-path
  and tolerance approval and D-16 confirmation remain pending at merge. These
  existing separate obligations are not unanswered implementation choices.
- Biological execution, real-run manifest completeness, live scheduler behavior,
  §8.4's second backend, §17's ≥ 4/5, external pilot-1 reproduction and typed
  claim-set equality remain unverified. No whole-row reproduction exit is claimed.
- Earlier Step A gaps remain: GRCh38 hashes, stage-03/authoring manifests,
  row-7 methods/rendering/claim wiring, data handling, registry/liveness and row-2
  benchmark re-pinning. Source-pin validation still refuses; no pin is changed.
- The 73 full-suite environment skips remain unverified; no row-6 test skipped.
  Python 3.6 grammar passes, but its runtime and live biological environments are
  not verified here. No release or protected-path approval is claimed.
