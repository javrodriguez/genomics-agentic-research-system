# Row 12 change report — partial repo-side implementation

Row exit **NOT met**. The owner supplied rulings 12A and 13A; both are quoted in
[0057](../decisions/0057-row-12-lifecycle-status-writer.md). Additional material choices
are stopped under the owner's rule 5 and recorded there with numbered options.
The producer has not approved or merged this work. Merge remains conditional on the
separate study's done commit and the owner's review.

Starting branch: `build/gars-row-12-lifecycle`.
Starting commit (`HEAD@{start}`): `d17573af63ab5d21d0eadabf806c3da31541f5b6`.
`git status --short` was empty. The starting log includes row 4's implementation,
provisional rulings and the owner's protected-change approval commit 0056.

## Requirement, implementation and acceptance

| Requirement | Changed files | Acceptance test | Result; red-on-fault seen |
|---|---|---|---|
| R-150/R-151, 12A | `wrapperlib.py`, all ten wrapper Python files | `test_status_writer.py`: enum refusal, atomic failure, mapping, every nonterminal state's cancel/failure edges, source sweep | PASS for the writer and ten shipped wrappers; **yes**, inline write and out-of-enum mutants fail |
| R-077 | `executorlib.py` | `test_lifecycle_executor.py::test_scheduler_reasons_survive` | Reasons TIMEOUT, OUT_OF_MEMORY, NODE_FAIL, CANCELLED and numeric EXIT preserved; **yes**, TIMEOUT→FAILED fails |
| R-076 | `wrapperlib.py`, `executorlib.py` | exact concatenated-byte key and stub-scheduler duplicate test in `test_lifecycle_executor.py` | PASS, repo-side only; **yes**, duplicate scheduler submission mutant fails. Full acceptance **NOT met** |
| R-076 / decisions 0038, 0039 | `test_executorlib_resume.py`, `tests/run_tests.py` | generated resume guard preserves work and completed reentry; existing resume-refresh tests and golden bytes | PASS, guard unit proof only; no Slurm/Nextflow execution claim |
| R-135 | `wrapperlib.py`, `executorlib.py`, `test_no_false_completion.py` | actual local worker SIGKILL, injected unreachable executor, stale marker cannot overrule executor, scheduler success without marker | PASS for recorded wrapper jobs; **yes**, killed-worker COMPLETE mutant fails |
| R-151, 13A | `guard_hook.py`, `.claude/settings.json`, stage-02 STATUS instruction lines | `test_status_writer.py::test_agent_status_write_refused`, existing settings equality, contract lint | PASS; **yes**, removing STATUS protection fails |
| R-151 / status side effect | `tools/registry.json`, `test_role_profiles.py` | reviewer retains explicitly permitted status; all other side-effect tools remain refused | PASS; no role/identity override introduced |
| R-074 cancel | no implementation beyond inherited declared refusal | required long-running cancel and genuine approval-record acceptance | **NOT met**; approval-to-job binding/issuance awaits the owner; red-on-fault **no** |
| R-152 | conservative refusal of recorded failed-key re-submission in `executorlib.py`; `test_execution_policy.py` | required `test_failure_classification.py` on six injected failures, bounded transient retries | **NOT met**; no failure taxonomy/artifact, destructive retry approval, or bounded retry implementation claimed; red-on-fault **no** |
| R-151/R-135 beyond the boundary | unchanged `stage03_analysis.py` and authoring generator | repository-wide writer/success gate | **NOT met**; scope conflict recorded in 0057 |

The stub runner and no-false-completion runner print these lines verbatim. They are
repo-side results, not a claim that the row's full exit is met:

```text
duplicate side effects 0
every wrapper uses the writer
0 false completions
```

The seven nf-core prepare paths have params.yaml, samplesheet and assay config and get
the exact `sha256(params.yaml bytes + samplesheet bytes + assay config bytes)` key.
The only new manifest field is `idempotency_key`; submit.sh carries it as a comment
following the unchanged generated script. Submissions reserve the key before calling
the backend, under a file lock; ambiguous submission outcomes retain the reservation.
The marker guard still protects in-job reentry. The tests do not equate that guard
with preventing duplicate scheduler submissions.

**Operational limitation:** the three downstream wrappers have no complete key tuple;
submission now refuses their missing key. Recorded failed keys refuse retry pending
R-152's ruling. Scheduler success with its marker does not publish COMPLETE; collect
remains the success writer. The intermediate STATUS choice is stopped pending the
owner. This partial branch must not be promoted as a finished lifecycle implementation.

## JSON and compatibility changes

R-077 extends status JSON `state`: `CANCELLED`, `FAILED:TIMEOUT`,
`FAILED:OUT_OF_MEMORY`, `FAILED:NODE_FAIL`, `FAILED:EXIT_<n>`. `terminal` recognizes
cancellation and qualified failure. R-135 reports `ARTIFACT_MISSING` for a recorded job
whose scheduler succeeded without the marker. Unreachable status returns an error and
persists STALE, never COMPLETE. R-076 refusal responses retain `error` and add
`refusal: {type: execution_refusal, rule, reason}`, with exit 2. Successful submit's
`job_id` field and the typed dispatcher's stdout/stderr/exit-code envelope do not change.

The exact seeded legacy Slurm map/status argv normalize in memory to the new built-in
values. No descriptor file or golden fixture migrates. Header generation still uses
the descriptor seam and passes the original strict/legacy-parser golden-byte tests.
No existing STATUS file, resolver, project-state reader, pinned skill or pin digest is
migrated. Failure/collect classification and unrecorded legacy-job reconciliation remain
outside the partial implementation, not inferred from model text.

## STATUS-write enumeration

The initial read used:

```bash
rg -n 'STATUS|write_reproducibility|write_submit_sh|write_params' gars/_system/wrappers --glob '*.py'
```

The immutable starting tree was also enumerated with this grep command, retaining
both the open and the following write line:

```bash
git grep -n -A1 'with ws.atomic_open(substage / "STATUS")' d17573af63ab5d21d0eadabf806c3da31541f5b6 -- gars/_system/wrappers
```

Every row below wrote `fh.write("COMPLETE %s\n" % now)` on the following line:

| Wrapper file under `gars/_system/wrappers/` | Inline open line at start |
|---|---:|
| `nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py` | 309 |
| `nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py` | 310 |
| `nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py` | 286 |
| `nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py` | 206 |
| `nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py` | 263 |
| `nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py` | 377 |
| `nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py` | 322 |
| `rnaseq-de/rnaseq_de.py` | 385 |
| `scrna-qc-cluster/scrna_qc_cluster.py` | 496 |
| `spatial-cluster-count/spatial_cluster_count.py` | 566 |

A wider `rg -n 'COMPLETE|STATUS' gars/_system --glob '*.py'` also found
`stage03_analysis.py:427–428` and the authoring generator's lines 474–475. They are
outside the permitted edit list. The new sweep covers all ten shipped wrappers plus
executorlib and detects direct writes and path aliases; it is a static regression
sweep, not proof about arbitrary computed Python paths or a process bypassing the guard.

## Visible planted faults

Each implemented mutant is applied to a disposable source copy under the named scratch
folder. Its named real test runs as a subprocess; the test asserts a nonzero result and
its expected assertion witness. Source files in the working repository are never mutated.
These producer-visible plants are not the sealed row-3 mutation score.

| Plant | Watched red? | Witness |
|---|---|---|
| Wrapper writes STATUS inline | yes | sweep finds the write |
| Writer accepts out-of-enum state | yes | `StatusRefusal not raised` |
| TIMEOUT becomes FAILED | yes | expected `FAILED:TIMEOUT`, got `FAILED` |
| Duplicate reaches scheduler | yes | second submission returned job 123 |
| Cancel after one hour without approval | no | stopped pending approval binding; **NOT met** |
| Transient retry exceeds maxRetries | no | stopped pending failure/retry policy; **NOT met** |
| Killed worker reported COMPLETE | yes | injected COMPLETE publication/return fails killed-worker assertion |
| Agent writes STATUS | yes | Write accepted with exit 0 instead of refusal 2 |

`test_lifecycle_faults.py` prints each of the six observed `fault red:` lines.
The initial writer tests were red before implementation (11 failures and 3 missing-API
errors); the initial key/map tests were red (5 failures and 2 missing-feature errors).
Missing-API errors alone are not counted as the planted-fault evidence above.

## Existing expectations changed under the owner's rule 4

Line numbers refer to the final files. No threshold changes. Other observed reds were
fixed in production code: seeded descriptor normalization, and truthful STATUS wording
at the writer call for the unchanged authoring lint.

| Test / file:line | Old expectation | New expectation | Requirement |
|---|---|---|---|
| `test_01_shipped_template_resolves_to_the_builtin`, `tests/run_tests.py:1472` | raw parsed seeded map/argv equal built-in | loaded legacy descriptor normalizes to reason-preserving built-in; full validation still passes | R-077 |
| `test_prepared_local_failure_refuses_unclassified_retry`, `gars/tests/test_execution_policy.py:62` | exit 17 retries unconditionally, completed script can be submitted again | preserves EXIT_17 and refuses failed-key retry; generated guard behavior retained in separate resume test | R-076/R-077/R-152 |
| `test_reviewer_only_read_and_status`, `gars/tests/test_role_profiles.py:39` | every side-effect entry refuses reviewer | explicit status permission remains, despite its newly declared code-owned STATUS refresh; other writes still refuse | R-151, 13A; §9.2 |
| `test_task_schema_and_input_hashes`, `tests/test_benchmark_discriminates.py:65` | published pins match live wrapper/contract bytes | validator checks scratch current-source copies, rehashing only the four R-151/13A changed inputs | R-151, 13A |
| `test_refusal_scorers_discriminate`, same file:108 | load published source pins | load the same tasks with only those four scratch input hashes refreshed; all positive/negative assertions retained | R-151, 13A |
| `test_missing_outputs_fail_not_skip`, same file:125 | load published source pins | scratch current-source tasks; missing outputs still fail | R-151, 13A |
| `test_json_boolean_numeric_substitutions_are_red`, same file:129 | load published source pins | scratch current-source tasks; all type-confusion assertions retained | R-151, 13A |
| `test_nfcore_artifact_contracts_accept_and_reject_content`, same file:136 | load published source pins | scratch current-source tasks; every artifact/content corruption assertion retained | R-151, 13A |
| `test_coherent_forgery_and_missing_artifacts_are_red`, same file:308 | make record against live published pins | make record against scratch current-source pins; coherent forgery and absent artifacts still fail | R-151, 13A |
| `test_strict_reference_readiness_rejects_placeholders`, same file:370 | load published source pins | scratch current-source tasks; missing independent references still refuse | R-151, 13A |

Shared test setup copies the five public task definitions and their named inputs into
scratch and refreshes only the two wrapper and two contract hashes changed by this row,
using the existing `bench.file_sha`. All other published input hashes remain asserted.
The original wrong-hash and malformed-task controls still run through the unchanged CLI.
Nothing under benchmarks/ or evals/ is edited. **NOT met:** published benchmark source
pins for this changed branch; refreshing them belongs to the owner's later integration.

## Commands and execution conditions

Every shell command ran in bash from the repository root. Before each invocation,
TMPDIR, TEMP and TMP were exported to the owner-designated scratch folder outside the
repository. The literal local path is intentionally omitted from committed text.
`SCRATCH` below denotes that same folder, not a system temporary location:

```bash
export TMPDIR="$SCRATCH" TEMP="$SCRATCH" TMP="$SCRATCH"
python3 --version
python3 tests/run_tests.py
python3 tests/check_contracts.py
python3 tests/check_counts.py
python3 evals/test_harness.py
python3 evals/check_results.py --controls --lexicon
python3 gars/tests/test_status_writer.py
python3 gars/tests/test_lifecycle_executor.py
python3 gars/tests/test_no_false_completion.py
python3 gars/tests/test_lifecycle_faults.py
python3 gars/tests/test_executorlib_resume.py
python3 gars/tests/test_execution_policy.py
python3 gars/tests/test_role_profiles.py
python3 tests/test_benchmark_discriminates.py
python3 tests/run_tests.py ExecutorSeamTests.test_01_shipped_template_resolves_to_the_builtin
bash docs/decisions/build_index.sh
git diff --check
git diff --stat d17573af63ab5d21d0eadabf806c3da31541f5b6 -- evals/ .github/ gars/_system/hooks benchmarks gars/_references/tool_pins.json
```

Python was **3.13.2**, including the evaluation harness (meets its ≥3.9 requirement).
Production additions remain stdlib-only and use Python-3.6-compatible syntax/APIs;
actual Python 3.6.8 execution is **NOT met**. Existing environment-dependent tests retain
their declared skips; no dependency was installed. Reads used cat/sed/rg, index searches
preceded edits, and all ten STATUS-writing contracts plus the required spec sections and
decisions were read. Edits used apply_patch or Python heredocs, with JSON serialized by
stdlib json. Runtime logs and disposable copies stayed in scratch. The raw logs contain
runtime paths and therefore are not committed; their summaries are retained below.

The Docker probe was `docker image ls --format '{{.Repository}}:{{.Tag}}'`, exit 1:
Docker daemon socket access was denied. No installation, network pull or Slurm run was
attempted. Consequently the Slurm half of R-076 is **NOT met**, even though the stub
scheduler test passes. The protected-tree diff command above returned no output.
Path-limited git staging and a scratch-file commit message are used for the single row
commit. No remote is added; no push, PR, approval or merge is performed.

## Verification summaries

`python3 tests/run_tests.py`:

```text
fault red: wrapper writes STATUS inline
fault red: writer accepts an out-of-enum value
fault red: TIMEOUT folds into FAILED
fault red: duplicate submission reaches scheduler
fault red: agent session writes STATUS
fault red: killed worker reported COMPLETE
Ran 319 tests in 126.222s
OK (skipped=50)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 187.223s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 gars/tests/test_status_writer.py`:

```text
Ran 6 tests in 0.550s
OK
```

`python3 gars/tests/test_lifecycle_executor.py`:

```text
Ran 3 tests in 0.452s
OK
```

`python3 gars/tests/test_no_false_completion.py`:

```text
Ran 2 tests in 0.156s
OK
```

`python3 gars/tests/test_lifecycle_faults.py`:

```text
Ran 1 test in 12.361s
OK
fault red: wrapper writes STATUS inline
fault red: writer accepts an out-of-enum value
fault red: TIMEOUT folds into FAILED
fault red: duplicate submission reaches scheduler
fault red: agent session writes STATUS
fault red: killed worker reported COMPLETE
```

`python3 gars/tests/test_execution_policy.py`:

```text
Ran 7 tests in 12.340s
OK
```

`python3 tests/test_benchmark_discriminates.py`:

```text
Ran 23 tests in 2.707s
OK (skipped=1)
```

Additional targeted checks, also run directly:

```text
python3 gars/tests/test_executorlib_resume.py
Ran 2 tests in 0.060s
OK
python3 gars/tests/test_role_profiles.py
Ran 6 tests in 0.012s
OK
python3 tests/run_tests.py ExecutorSeamTests.test_01_shipped_template_resolves_to_the_builtin
Ran 1 test in 0.005s
OK
Python 3.6 syntax audit: 3 changed production modules parsed
```

The final whole suite collected 319 and ended OK. The 50 skips are inherited
environment/evidence skips, not new lifecycle skips. Six visible lifecycle faults were
observed red. Early integration runs exposed benchmark pin drift and legacy descriptor
expectations; their targeted changes and final checks are listed above. No failing
acceptance threshold was lowered. README and DEVELOPMENT now match the runner count.

## Hours and residual gaps

Measured build/verification interval: **0.404 hours**, 11:40:05 to 12:04:18 UTC.
This starts at the first retained source enumeration; preceding required reading was
not separately timed, so total task hours are greater and are not fabricated. Human
touch time was not measured here (R-153 is row 13). No cluster compute hours were used.

- **NOT met:** R-076 Slurm-path acceptance; Docker access failed; no containerised Slurm ran.
- **NOT met:** R-074 cancel and its approval-record condition; the declared refusal remains.
- **NOT met:** R-152 classes, error/class artifacts, six-failure classification test, bounded
  transient retry and destructive retry approval. These are stopped for an owner ruling.
- **NOT met:** downstream-wrapper keys and their submit usability until the input ruling.
- **NOT met:** scheduler-success intermediate STATUS and collect-failure classification.
- **NOT met:** stage-03 writer/completion coverage and generated future wrappers, outside
  the edit boundary; four raw-sbatch contract submit lines also need a separate scope ruling.
- **NOT met:** §13.7 Stage 3 durable state table, ownership/heartbeats and restart reconciliation.
- **NOT met:** full row-12 exit. The three repo-side printed metrics do not close the gaps.
- No other row, protected study tree, pinned skill or pin inventory is changed.
