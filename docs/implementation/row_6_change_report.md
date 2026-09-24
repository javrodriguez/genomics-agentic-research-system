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
