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


## Review round 2 fixes

Date: **2026-09-22**. Supplied review: `docs/reviews/row_12_review.md`, SHA-256
`de4bc7e8a8416e8c9d57cd7553a072a690f42f6ce60ad8ab97cfeb1e2ef564f4`.
The review remains untracked and unchanged. This round starts at `e33f34e`; row 12 is
judged against `d17573a`, including the owner's row-4 approval decision 0056. No external
reviewer conversation or other build tree was read. Earlier report sections and decision
0057 retain their original bytes; [0058](../decisions/0058-row-12-review-addendum.md) is
an addendum. No owner approval, merge or full row exit is claimed.

The current instruction to stop for owner-owned schemas, thresholds and scope choices takes
precedence over the review's recommendation to select provisional defaults. Only 12A and
13A were supplied as owner rulings for this row. The unfinished implementation is still
unfit for promotion: in particular the downstream submission and retry limitations remain.
No finding is dismissed as wrong. Inherited row-4 material is not reassessed or repaired.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| BLOCKER-1: editable key and execution evidence | `executorlib.py`, `wrapperlib.py`, `guard_hook.py`, `.claude/settings.json`, `test_lifecycle_executor.py`, `test_no_false_completion.py`, `test_status_writer.py` | edited-key attack; rehash changed inputs; forged sibling-record collection; changed-backend success; four write tools against machine evidence | Fixed for guarded, recorded jobs. **Yes:** baseline edited-key test resubmitted; forged-record and terminal/reviewer tests failed; guard accepted all newly protected targets. Current tests pass. No same-UID unguarded-process guarantee. |
| MAJOR-1: definite refusal burns key | `executorlib.py`, `test_lifecycle_executor.py`, 0058 | failed stub sbatch followed by successful sbatch; missing local/Slurm backend; ambiguous output/signal/error with job id | Definite refusal fixed; recovery procedure's contract/authorization scope remains with owner. **Yes:** baseline second submit returned `duplicate_submission; key already recorded (STALE)`; current stub submits exactly once. Ambiguous reservations remain protected. |
| MAJOR-2: terminal regression | `wrapperlib.py`, `executorlib.py`, `test_status_writer.py`, `test_no_false_completion.py` | every terminal refuses exit; same-state no-op; reviewer-authorized status after empty accounting, RUNNING or failure response | Fixed. **Yes:** baseline accepted terminal exits and rewrote COMPLETE after the reviewer status call. Stage lock now serializes validation and replacement; final tests preserve terminal bytes. No general corrective bypass added. |
| MAJOR-3: downstream missing keys | report, 0058 | downstream submit acceptance not claimed | Owner ruling required on key inputs or the review's proposed exemption; no key schema chosen and no guard relaxed. **No:** no green downstream submission test is claimed. |
| MAJOR-4: retry and collect-failure dead ends | report, 0058 | executor-level permitted retry and collect-failure transition not claimed | Owner state/mapping/corrective-path ruling remains needed; recorded failed keys still refuse. **No:** generated guard unit tests are not represented as executor retry acceptance. |
| MAJOR-5: missing cancel | report, 0058 | inherited declared-refusal/role tests only | Owner timing/record binding required; missing verb remains open, including sub-hour acceptance. **No:** no live cancellation or approval-record acceptance is claimed. |
| MAJOR-6: absent classifier | report, 0058 | `python3 gars/tests/test_failure_classification.py` | Named test absent, exit 2; not a test pass. Owner mapping/artifact ruling required. **No.** |
| MINOR-1: case variants bypass protection | `guard_hook.py`, `test_status_writer.py` | Write/Edit/MultiEdit/NotebookEdit on `status`, `FILES.CSV`, `plan.MD.approved` | Fixed through case-insensitive path comparison. **Yes:** baseline allowed all twelve case-variant tool/path combinations; current tests refuse. |
| MINOR-2: sweep evasions | `test_status_writer.py`, `test_lifecycle_faults.py`; four wrapper module docstrings | real sweep with computed, copied and formatted STATUS paths planted in disposable source copies | Fixed. **Yes:** all three plants make the real sweep fail. STATUS substrings are allowed only in comments or the actual writer-call token span; a second write on the same line also fails. |
| MINOR-3: stale executor template | report, 0058 | existing resolved-template seam test | Owner action recorded below. **No:** normalization remains until an approved template refresh and its removal can land together. |
| MINOR-4: repeated status calls | ten stage-02 `CONTEXT.md` Process sections | `tests/check_contracts.py`; inspected diff of status lines | Partially fixed: typed-submit paths no longer immediately poll; every later active branch uses its single existing query. Collect-failure wording and the four inherited raw-sbatch paths await rulings. **No:** documentation correction, not a behavioral fault plant. |
| MINOR-5: fixed wrapper count and generator | `test_status_writer.py`, report | sweep asserts at least ten shipped wrappers | Count corrected; generator output remains owner-gated and unverified. **No:** the minimum stays ten; no behavior assertion is removed. |
| NOTE-1: generic Bash refusal | report | existing generic typed-surface/guard tests | Retained: inherited row-4 R-092 refusal already blocks the shell spellings; a STATUS-specific diagnostic is optional and unnecessary for enforcement. **No new plant.** |
| NOTE-2: protected-path owner approval | report | boundary audit | Owner approval record for guard/settings/registry remains required at merge; 13A is not represented as that record. **No.** |
| NOTE-3: incomplete timing | report | none | The earlier 0.404 h remains a lower bound, not usable ledger sizing. This round does not invent total or human-touch hours. **No.** |
| NOTE-4: published source pins | report | benchmark tests with existing scratch-only pin refresh | Owner integration action after the study's done commit remains; benchmark files unchanged. **No new plant.** |

Only the machine-evidence fixes above extend the new row-12 protection. New reservations
still use the existing fields and return shapes; no on-disk schema is introduced. The
COMPLETE writer now also verifies recorded scheduler success, and status refuses a backend
switch for a recorded job. The raw `.gars_local_jobs` record and `.local.exit` are protected
because otherwise an editable local scheduler answer would bypass the same completion gate.
Protected JSON/scripts cannot be replaced by an agent session to remove or forge the key.

### Existing test expectations changed this round

One row per changed expectation; every other red was corrected in code or in the new test's
fixture before counting it as a fault witness. No threshold is reduced.

| Test | Previous expectation | Requirement-correct expectation | Reason |
|---|---|---|---|
| `StatusWriterTests.test_all_nonterminal_states_have_cancel_and_failure_edges` | reuse one stage by leaving CANCELLED/FAILED for the next nonterminal fixture | each tested edge starts from a fresh STATUS fixture; every original cancel/failure edge remains asserted | R-150 and MAJOR-2 prohibit the fixture's terminal-to-nonterminal reset through the production writer |
| `NoFalseCompletionTests.test_killed_worker_and_unreachable_executor` | later unreachable scheduler overwrites FAILED:EXIT_137 with STALE | retains FAILED:EXIT_137 byte/state authority; injected unreachable query still refuses collect | R-135/R-150 terminal stickiness; the mock now injects scheduler unreachability directly instead of changing the recorded job's backend |
| `StatusWriterTests.test_every_wrapper_uses_writer` | exactly ten wrapper source files | at least ten; every discovered wrapper must still call the writer and pass both sweeps | R-151 and MINOR-5 require future wrappers to be checked, not rejected merely for existing |

The baseline red runs used Python 3.8.2 and these newly added tests, before production fixes:

```text
python3 gars/tests/test_lifecycle_executor.py
Ran 7 tests in 1.458s
FAILED (failures=4)
python3 gars/tests/test_no_false_completion.py
Ran 4 tests in 0.308s
FAILED (failures=2)
python3 -m unittest discover -s gars/tests -p test_status_writer.py
Ran 8 tests in 7.766s
FAILED (failures=48)
```

These are assertion failures on the defects, not missing-API errors. Initial fixture errors
were corrected and the baseline was rerun before those figures were retained. The sweep's
three additional visible mutants run in copied source trees; the working source is not
mutated. The earlier six plants remain and still fail their named tests when injected.

## Owner rulings needed

1. **MAJOR-3 — downstream idempotency formula.** The review offers (a) a key over every
   wrapper's declared manifest input bytes in a fixed order, recorded as a provisional
   formula, or (b) gating the key refusal to wrappers that declare one. Decision 0057 also
   records serializing downstream params and using the stage-01 samplesheet versus a separate
   downstream formula. The spec's exact three-file tuple does not define those downstream
   inputs. Select the formula/schema, or explicitly authorize the exemption; the producer
   does neither and does not relax the guard. All three downstream submits remain NOT met.
2. **MAJOR-4 — scheduler success and corrective transitions.** Options recorded in 0057:
   persist `VALIDATING` while returning scheduler `COMPLETED` until collect, or another
   owner-selected non-success state. The review recommends `VALIDATING` and collect failure
   `FAILED:EXIT_<n>` (or an owner-chosen state). Confirm their relationship to 13A and the
   explicit corrective/retry path out of a terminal failure. Until then, no misleading
   FAILED or success transition is guessed; the existing RUNNING/collect failure gap remains.
3. **MAJOR-4/MAJOR-6 — failure taxonomy/artifact and retry approval.** The recorded options
   are the existing transient set 104 and 130–145 unless a specific scheduler reason overrides;
   scheduler TIMEOUT/OUT_OF_MEMORY/NODE_FAIL as infrastructure; 126/127 as tool; 65 as data_quality;
   other nonzero exits as workflow, leaving agent_reasoning/scientific_validation unassigned;
   or owner-supplied alternatives. The review recommends that mapping and a one-line class/error
   artifact beside the log. Confirm the producer codes and artifact schema. Only transient may
   retry, at the existing `maxRetries`; destructive retry needs approval. No classification,
   artifact schema, retry exception or missing producer codes are invented in this round.
4. **MAJOR-5 — cancellation timing and approval binding.** Options in 0057: a job-specific
   cancellation plan using the existing protected store and an issuance path, or an action
   record extension. The review requires R-073-shaped approval naming job id/backend for a job
   past one hour. The current submission schema records key/script/state/job_id/executor,
   but no start or consumed-compute time. Confirm the recorded-start/timing field and its
   source, as well as the job/backend binding and human issuance route. This is why sub-hour
   cancellation is not claimed either: it cannot be safely selected from the current record.
   No environment, payload or force flag is an approval substitute. The one-hour threshold
   itself is fixed by the spec and is not a question.
5. **MINOR-5 and R-151/R-135 scope.** Authorize narrow changes to stage03_analysis.py and
   the authoring generator, with generated-output sweep coverage, or leave both explicitly
   NOT met, as the review and 0057 state. Neither file is changed in this round. Stage-03
   completion and the next scaffolded wrapper remain uncovered.
6. **MINOR-4 and inherited contract boundary.** The four raw-sbatch submit lines were
   inherited from the approved row-4 head. Options: authorize typed executor.submit lines,
   or retain their declared refusal until a separate contract change. The remaining
   collect-failure status instructions depend on ruling 2 above; these are not closed by
   the mechanical duplicate-call cleanup.
7. **MINOR-3 — protected template refresh.** Owner action: refresh
   `gars/_templates/config/executor.yaml` to the reason-preserving map/status argv and issue
   its §9.3 approval record; remove legacy recognition in the same change and restore the
   raw-template equality assertion. The template and normalizer are left together as-is now.
8. **NOTE-2 — protected-path approval at merge.** The owner must record approval for
   row 12's `guard_hook.py`, `.claude/settings.json` and `tools/registry.json` changes.
   This producer's proposed 0057/0058 and the substantive 13A ruling do not fabricate that
   approval record. Registry bytes are unchanged in this round but changed in row 12.
9. **MAJOR-1 — ambiguous submission recovery.** Definite refusals are fixed. For ambiguous
   outcomes, select the supported scheduler reconciliation/record-binding or reservation-
   release operation and its evidence/authorization; authorize the contract recovery paragraph
   beyond the STATUS-only lines. Until then the safe recovery instruction is stop, preserve
   record/logs/work, and request owner reconciliation; never delete the reservation to retry.
10. **NOTE-4 — published benchmark pins.** Owner integration action, after the separate
    study's done commit: refresh the affected published source pins and their acceptance
    evidence. Scratch rehashing is not published-pin acceptance. No benchmark/study file changed.
11. **Row 15 / unguarded processes.** Any extension of these protections to non-agent
    builders or a same-UID process bypassing the workspace guard needs the separate row-15
    hooks/deployment scope. Row 15 is not inspected or modified here. The workspace guard
    and settings are not a filesystem sandbox or proof of separate-OS-user isolation.

### Residual gaps

- Full row-12 exit is **NOT met**. MAJOR-3 through MAJOR-6 remain open pending the above
  rulings; MAJOR-1's ambiguous recovery procedure and MINOR-3/4/5 have named remaining parts.
- The three downstream wrappers still lack accepted keys and refuse typed submission.
  Failed-key retry remains unavailable. Collect validation failure can still leave RUNNING;
  scheduler success before collect has no new intermediate state. These are operational
  defects, not successes hidden by documentation.
- No cancel verb, approved long-job cancellation, failure classification artifact, six-failure
  classification acceptance, or bounded executor-level retry is claimed.
- Live Slurm/Nextflow R-076 acceptance, Docker/cluster behavior, actual Python 3.6.8 execution,
  native harness permission-glob depth/case behavior, separate-OS-user isolation and Stage-3
  durable state/heartbeats/restart reconciliation remain unverified.
- The named missing classification test exits 2 because its file does not exist. Docker image
  inspection exits 1 because daemon socket access is denied; no image is pulled or installed.
- No formal historical record, assessment or supplied review is rewritten. No row-15,
  protected study, CI, pinned skill, pin inventory or benchmark file changes. No remote,
  push, merge, pull request or owner-identifying committed text is introduced.

### Final command summaries
All final verification below used Python **3.13.2**, with that interpreter first on PATH
for child runners. TMPDIR, TEMP and TMP were exported to the designated sibling scratch
folder before every shell invocation. Scratch logs and copied mutation trees stay there;
none is staged. The initial full run, before the final two tests were added, was
`Ran 328 tests in 248.913s` / `OK (skipped=50)`; the final run below tests the final code.
README and DEVELOPMENT now reflect the loader's final 330. Summary lines below are copied
verbatim from each runner, including durations and inherited environment/evidence skips.

`python3 tests/run_tests.py`:

```text
fault red: wrapper writes STATUS inline
fault red: writer accepts an out-of-enum value
fault red: TIMEOUT folds into FAILED
fault red: duplicate submission reaches scheduler
fault red: agent session writes STATUS
fault red: killed worker reported COMPLETE
fault red: computed STATUS path
fault red: copied STATUS path
fault red: formatted STATUS path
Ran 330 tests in 186.612s
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
Ran 44 tests in 217.272s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 gars/tests/test_status_writer.py`:

```text
Ran 9 tests in 5.737s
OK
every wrapper uses the writer
```

`python3 gars/tests/test_lifecycle_executor.py`:

```text
Ran 8 tests in 1.493s
OK
duplicate side effects 0
```

`python3 gars/tests/test_no_false_completion.py`:

```text
Ran 5 tests in 0.339s
OK
0 false completions
```

`python3 gars/tests/test_lifecycle_faults.py`:

```text
Ran 1 test in 15.193s
OK
fault red: wrapper writes STATUS inline
fault red: writer accepts an out-of-enum value
fault red: TIMEOUT folds into FAILED
fault red: duplicate submission reaches scheduler
fault red: agent session writes STATUS
fault red: killed worker reported COMPLETE
fault red: computed STATUS path
fault red: copied STATUS path
fault red: formatted STATUS path
```

`python3 gars/tests/test_executorlib_resume.py`:

```text
Ran 2 tests in 0.124s
OK
```

`python3 gars/tests/test_execution_policy.py`:

```text
Ran 7 tests in 22.625s
OK
```

`python3 gars/tests/test_role_profiles.py`:

```text
Ran 6 tests in 0.018s
OK
```

`python3 tests/test_benchmark_discriminates.py`:

```text
Ran 23 tests in 5.647s
OK (skipped=1)
```

`python3 tests/run_tests.py ExecutorSeamTests.test_01_shipped_template_resolves_to_the_builtin`:

```text
Ran 1 test in 0.009s
OK
```

`python3 -m unittest discover -s gars/tests -p test_pre_push.py -v`:

```text
Ran 7 tests in 10.296s
OK
```

Other checks in this run:

- `python3 --version`: `Python 3.13.2` for final checks; early red/focused runs used 3.8.2.
- Python grammar audit: `Python 3.6 syntax audit: 7 changed production modules parsed`.
  This is syntax evidence only, not execution under Python 3.6.8.
- `bash docs/decisions/build_index.sh`: exit 0; regenerated `docs/decisions/CONTEXT.md`.
  Its path-bearing output remains in scratch, not this report.
- `git diff --check`: exit 0, no output.
- Boundary diff against `d17573a` for `.github/`, `evals/`, `benchmarks/`,
  `gars/_references/`, `gars/_templates/`, `gars/_system/hooks/`,
  `gars/_system/authoring/` and `gars/_system/stage03_analysis.py`: empty.
- Historical record audit: 0057 unchanged; this report retains its complete previous
  contents as an exact prefix; the supplied review hash remains the one recorded above.
- `python3 gars/tests/test_failure_classification.py`: exit 2, file absent; **NOT met**.
- `docker image ls --format '{{.Repository}}:{{.Tag}}'`: exit 1, daemon socket permission
  denied; **NOT met**. No Slurm-in-container fixture, live scheduler, network pull or
  dependency installation ran.

One round commit uses an explicit path list and a message file in scratch. The review is
excluded from staging. Commit identity is a generic producer identity; no personal name,
login or machine name is added. No remote, push, merge or pull request is used.
