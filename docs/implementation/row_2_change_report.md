# Row 2 repo-side change report

Date: 2026-09-14. Parent: `c423366`. Branch: `build/gars-row-02-bench`.

**Row 2 exit: NOT met.** This change provides the benchmark records and scorer
infrastructure. It supplies no Claude Code agent run, observed noise floor,
degraded-arm discrimination, or actual held-out seal. Scorer test fixtures are
not agent evidence and never enter `evals/runs/`.

## Requirements, files, acceptance and result

| Requirement | Changed files | Acceptance test | Result; red-on-fault seen |
|---|---|---|---|
| R-110, §11.1: five tasks with inputs and reference provenance | `benchmarks/tasks/{batch-confounded,single-replicate,pseudoreplicates,bulk-rnaseq,bulk-atacseq}.yaml`; `benchmarks/fixtures/{generate.py,batch-confounded.csv,single-replicate.csv,pseudoreplicates.csv,bulk-rnaseq-source.json,bulk-atacseq-source.json}` | `BenchmarkTests.test_task_schema_and_input_hashes`, `test_generator_reproduces_fixtures`; `python3 evals/bench.py validate` | Five task records validate: `5/5 = 1.000000`. Synthetic generator seed 110112 reproduces input bytes. Wrong-hash red seen: **yes**, CLI exits 2. nf-core numerical-reference gaps remain NOT met. |
| R-111: split tuned-on and held-out scores, external sealing | `benchmarks/HOLDOUT.md`; `evals/bench.py`; `evals/runs/README.md` and `.gitkeep` | `test_holdout_in_tuned_directory_is_red`, `test_external_holdout_is_separate_and_seal_is_checked`, `test_cli_records_missing_outputs_and_resources` | **Yes**: held-out task in tuned task directory exits 2; invalid seal digest/record seal refused. Unset variable records and prints `held_out: unmeasured` with no score fraction. Actual seal/access-denial evidence **NOT met**. |
| R-112: run identity, resource block, comparable deltas and noise floor | `evals/bench.py`; `evals/noise_floor.py`; `evals/runs/README.md` | `test_cli_records_missing_outputs_and_resources`, `test_delta_cross_model_and_prompt_are_red`, `test_two_run_noise_floor_is_red`, `test_range_mean_and_strict_discrimination`, `test_duplicate_repeats_and_suite_drift_refused`, `test_record_score_tampering_refused` | **Yes**: cross-model delta and two-run floor exit 2; cross-prompt comparison also refused. Owner-approved range/mean calculations use exact fractions and inclusive no-change band. Same-commit repeats cannot overwrite one another. Noise report persistence is exercised only with synthetic unit-test records in scratch. Actual recorded noise floor **NOT met**. |
| R-113: non-model scorers; no restored weighted system score | `evals/bench.py`; five task records | `test_model_scorer_is_red`, `test_refusal_scorers_discriminate`, `test_nfcore_artifact_contracts_accept_and_reject_content`, `test_missing_outputs_fail_not_skip` | **Yes**: a model-named scorer exits 2. Valid structured refusals and synthetic artifact exports pass; execution-started flags, wrong flags, missing registry types, negative counts and lost samples fail. No model is called. No aggregate weighted system score is published. |
| §11.3: ratios retain numerator/denominator | `evals/bench.py`; `evals/noise_floor.py` | `test_zero_denominator`, CLI resource/noise tests | `0/0 = uncomputable`; task scores retain their full denominator even when every artifact is missing. Fractional deltas, noise floor and mean print numerator and denominator. |
| §18 row 2: measured degraded-arm discrimination | `tests/test_benchmark_discriminates.py`; imported classes in `tests/run_tests.py` | `BenchmarkRecordTests.test_benchmark_discriminates` | **SKIP**, precisely: `missing owner run record(s): intact-1, intact-2, intact-3, degraded-1`. Red-on-agent-degradation seen: **no**; no agent runs exist. Arithmetic tests demonstrate strict inequality but do not close the exit. |
| §21 Q2 and material omissions | `docs/decisions/0045-row-2-benchmark-tasks-and-holdout.md`; generated `docs/decisions/CONTEXT.md` | Decision read-back and `bash docs/decisions/build_index.sh` | Defaults are the five §11.1 tasks and a separate sealing session. Owner explicitly approved the range/mean/equal-weight rule and run-content-SHA naming before their implementation. Decision includes the 0043/0044 other-branch number note. |
| Existing count contract | `README.md`; `DEVELOPMENT.md` | `python3 tests/check_counts.py` | Initially red on three current count statements. Corrected only those counts from 125 to the runner's 142; historical counts and other prose unchanged. Final `enforced=3`, clean. |

All test method names above are in `tests/test_benchmark_discriminates.py` unless
otherwise stated. The runner imports its two TestCase classes explicitly because
`tests/run_tests.py` uses `unittest.main()` on its own module, not file discovery.
Seventeen new tests are loaded; one is the missing-owner-record acceptance skip.

## Five planted faults: actual red signals

These are malformed **inputs to the production CLI**, supplied by unittest in
throwaway scratch directories. A passing unittest means it observed the CLI
refusal, not that the planted input passed.

| Plant | Invocation exercised | Red observed | Restored/control behavior |
|---|---|---|---|
| Wrong input sha256 (`0` repeated 64 times) | `python3 evals/bench.py validate --tasks TEMP_TASKS` | **yes**, exit 2; `input sha256 mismatch` | Original five task files validate. |
| Scorer names a model (`claude-opus`) | Same validation CLI with mutated task JSON | **yes**, exit 2; `invalid scorer; models are never scorers` | `exact` and `pytest` task scorers validate and have positive output controls. |
| `holdout: true` in the tuned task directory | Same validation CLI; temporary directory mirrors `benchmarks/tasks/` and uses the same `holdout=False` loader | **yes**, exit 2; `holdout mismatch: held-out tasks are refused in benchmarks/tasks/` | An external synthetic interface-test task with `holdout: true` validates separately. It is not a real seal. |
| Delta across different models | `python3 evals/bench.py delta BEFORE AFTER --intact I1 I2 I3` | **yes**, exit 2; `refusing delta across different model` | Matching model/prompt/suite compares; within-floor delta says `no change`. Prompt-hash mismatch is tested too. |
| Noise floor from two intact records | `python3 evals/noise_floor.py I1 I2` | **yes**, exit 2; `uncomputable`, `requires exactly three intact records; found 2` | Three distinct synthetic intact records compute a range and mean, and can write a `.txt` noise report. |

Before implementation, the new test file was run with `evals/bench.py` absent and
failed with `ModuleNotFoundError: No module named 'bench'`. Behavioral tests were
added with the implementation; none of the pre-existing acceptance thresholds
or tests were weakened. No observed biological/model performance is inferred
from these scorer tests.

## Required runner results (verbatim summaries)

All five requested commands were run. The full suite was repeated after the
final seal-record validation and persisted-noise-report checks; count checking
was repeated after its three documentation corrections. No runner was changed
to make its result pass.

| Command | Summary line(s), verbatim | Exit |
|---|---|---|
| `python3 tests/run_tests.py` | `Ran 142 tests in 51.014s` · `OK (skipped=10)` | 0 |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | 0 |
| `python3 tests/check_counts.py` | `suite: 142 tests, from unittest's loader` · `enforced=3` · `clean — every current claim matches the suite` | 0 after count-only corrections |
| `python3 evals/test_harness.py` | `Ran 44 tests in 265.974s` · `OK` | 0 |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` | 0 |

The frozen evaluation checker still reports `published=3 graded=1`; the two
pre-existing ungraded tasks remain explicitly ungraded. Their records were not
rewritten or reused as this row's runs. The full-suite skips comprise the new
owner-record skip plus nine pre-existing environment skips. Direct benchmark
verification also reported `Ran 17 tests in 3.941s` and `OK (skipped=1)` before
the final full-suite rerun.

## Command environment and execution record

Every shell command ran from the repository root. For **every** invocation,
`TMPDIR`, `TEMP`, and `TMP` were set to the exact owner-specified sibling scratch
directory; its absolute machine path is intentionally omitted from committed
files. No new command wrote to the system temporary directory. Test-created
workspaces, fault records, captured logs and the commit-message file use that
scratch directory. The existing runners create and clean up their own disposable
fixtures there; no frozen repository fixture was edited.

The sandbox initially rejected a scratch log write because the specified sibling
was outside its writable roots. The command was rerun using the tool's explicit
escalation/approval mechanism; the tests and logs then ran with that authorization.
No alternate temporary directory was substituted. Subsequent scratch-writing
runners used the same approved execution route.

| Commands/group | How run and purpose |
|---|---|
| `pwd`, `rg --files`, `rg -n`, `cat`, `head`, `tail`, `sed -n`, `ls`, `du` | Read-only repository/scratch inspection. Root `AGENTS.md` is absent, so root `CLAUDE.md` was read. Read DEVELOPMENT, decision index and applicable decisions, §11.1/11.3/11.5/18/21 Q2, Row 2 assessment/review n-1, runner discovery and reusable assets. New paths had no prior index hits; tests/count-doc/index decisions were read before editing. Some `rg` calls intentionally returned no matches. |
| `git status --short --branch`, `git diff`, `git diff --check`, `git log`, `git diff --stat c423366 -- …` | Read-only branch, parent, scope, whitespace and frozen-path verification. No remote/push/PR command used. |
| `mkdir`, `touch`, quoted shell heredocs, inline stdlib Python | Create only the new allowed files and perform the specific runner import/count edits. Task hashes use SHA-256 of repository file bytes; no model, network download or pipeline execution is involved. |
| `python3 benchmarks/fixtures/generate.py` | Rebuild the tuned-on synthetic design CSVs from seed 110112. Generator test independently rebuilds in scratch and compares bytes. |
| `python3 evals/bench.py validate`; `python3 evals/noise_floor.py` | Validate all task records; separately confirm missing observations yield `uncomputable` and exit 2. Neither command starts an agent. |
| `python3 tests/test_benchmark_discriminates.py` | Initial missing-module red, then direct benchmark tests with synthetic records/artifacts only. Its CLI child processes inherit the temp variables, use the repository root, and clear `GARS_BENCH_HOLDOUT_DIR` for unset-variable tests. The seal test replaces it with a temporary synthetic interface fixture. No actual held-out slice was read. |
| Five required runner commands above | Initially dispatched concurrently by a stdlib `ThreadPoolExecutor`/`subprocess.run` wrapper, `cwd` repository root, stdout/stderr captured into scratch `row2-*.log` files. `GARS_PIPELINES` points to an intentionally absent directory within scratch, preventing fallback to a home-directory pipeline checkout. Later full-suite execution uses the same environment. |
| `python3 tests/check_counts.py` after correction | Same repo root and temp environment; derives 142 using unittest's loader, without changing the checker. |
| `python3 --version`; stdlib `shutil.which` probes | Python is 3.13.2 here. `python3.6`, `nextflow`, and `apptainer` are absent from PATH. The Claude CLI is available but was never started. No live Claude Code session or pipeline runs were attempted. |
| stdlib `ast.parse(..., feature_version=(3,6))` | Accepted the new scorer, noise helper, generator and benchmark test source under Python 3.6 grammar. This is not execution on Python 3.6.8; that interpreter is absent. New code uses only stdlib APIs available at that floor. |
| `bash docs/decisions/build_index.sh` | Regenerate the decision index from frontmatter; never edited by hand. A repeated build is checked for an empty diff. |
| Path-limited `git add -- …`; `git commit -F COMMIT_MESSAGE_FILE` | One row commit, message read from scratch, on the requested branch. No `git add -A` was used for this repository. The pre-existing evaluation harness internally stages its own disposable test repository; that runner is unchanged. No self-approval or merge. |

## Hours

Self-reported effort: approximately **0.75 hours**, including repository/spec
reading, implementation, verification and report preparation. This is not a
session-registry measurement; no registry-derived hours are claimed. Agent-run
wall time, tokens and cost are unknown because no agent run exists. Required
runner wall times above are observed test durations, not agent resource values.

## Residual gaps and merge condition

- **NOT met — intact repeat 1:** no owner `intact-1` agent record.
- **NOT met — intact repeat 2:** no owner `intact-2` agent record.
- **NOT met — intact repeat 3:** no owner `intact-3` agent record.
- **NOT met — degraded run:** no owner `degraded-1` record with design check and
  reviewer disabled. No degraded-agent red/green discrimination has been observed.
- **NOT met — observed noise floor:** no three-run observation; current command
  exits nonzero and prints `uncomputable`. The implemented computation is not a
  recorded measurement.
- **NOT met — held-out seal and measurement:** separate session must create and
  protect the slice from the complete HOLDOUT interface, retain producer-denial
  evidence, and perform authorized scoring. Public claims require external-human
  sealing; unit-test seal metadata establishes no such evidence.
- **NOT met — `NFCORE_RNASEQ_EXPECTED_OUTPUT_NOT_OBTAINED`:** test data are by
  reference; actual input pins/hashes and independent numerical output remain
  for the owner. The current scorer checks the RNA artifact contract only.
- **NOT met — `NFCORE_ATACSEQ_EXPECTED_OUTPUT_NOT_OBTAINED`:** same limitation for
  ATAC. No scientific reproduction score is claimed.
- **NOT met — growth to ten tasks:** later, after the first five discriminate.
- **NOT met — native Python 3.6.8 execution:** grammar/API compatibility assessed,
  but that interpreter is absent here; existing repository runners themselves
  already include newer-Python code and were run with the available interpreter.

The owner's standing ruling is retained: **this row merges only after the
separate study's done commit**. The required study checks observed here were
clean, but that does not waive the ruling or authorize a merge. The requested
frozen-path diff is empty, including `evals/gap-study/`, `evals/gap-study-2/`,
`evals/run.py`, `evals/graders/`, `evals/fixtures/`, `gars/`, and `.github/`.
Only `bench.py`, `noise_floor.py`, and `runs/` were added under `evals/`.
No later-row catalogue, release check, demo target, remote, PR or merge was added.


## Review round 1 fixes

Date: **2026-09-15**. Reviewed base: `1163c35`. Independent review:
`docs/reviews/row_2_review.md` (left untracked and unchanged). This section is an
append-only correction to the earlier report. **Row 2 exit remains NOT met.**
No agent run, independent biological reference, actual seal, or cluster result
was created to close a repository finding.

| Finding | Changed files | Test / check | Result; red-on-fault seen: yes/no, how |
|---|---|---|---|
| F1 BLOCKER — coherent fabricated verdicts | `evals/bench.py`, `tests/test_benchmark_discriminates.py`, `benchmarks/HOLDOUT.md` | `BenchmarkRecordTests.test_coherent_forgery_and_missing_artifacts_are_red`, `test_changed_artifact_hash_is_red`, existing score-tamper/delta/noise controls | **Closed. Yes:** changing every verdict and the matching total on an empty-output record now raises a recomputation mismatch; missing retained outputs and altered file hashes also raise. The coherent-forgery regression failed against the reviewed scorer before the fix. Every record consumed by comparisons or the exit is re-scored from retained artifacts and hash-validated current inputs. |
| F2 MAJOR — incomplete exit succeeds | `evals/bench.py`, `tests/test_benchmark_discriminates.py`, `benchmarks/HOLDOUT.md`, two bulk task YAMLs | `test_strict_row_exit_rejects_missing_cohort`, `test_strict_row_exit_requires_holdout_and_discrimination`, `test_strict_reference_readiness_rejects_placeholders`; `bench.py row-exit` | **Closed gate defect. Yes:** strict CLI exits 2 with all four missing ids; actual synthetic output cohorts reject absent held-out measurement, and a measured held-out arm that does not discriminate. Placeholder references reject; a complete synthetic interface cohort passes. Repository development retains the explicit missing-owner SKIP. Actual row exit is still NOT met. |
| F3 MAJOR — coupled sample deletion | `evals/bench.py`, two bulk task YAMLs, `tests/test_benchmark_discriminates.py`, `benchmarks/HOLDOUT.md` | `BenchmarkTests.test_nfcore_artifact_contracts_accept_and_reject_content` | **Closed scorer defect. Yes:** for RNA and ATAC, deleting a condition from both the exported sheet and every count table fails against the hashed independent roster; restoration passes. Wrong columns, negative counts, missing registry types, and changed reference counts reject. Current nf-core tasks have `expected_samplesheet: null` and fail scoring until owner materialization; no roster was invented. |
| F4 MINOR — blind response vocabulary missing | new `benchmarks/RESPONSE.md`, `benchmarks/HOLDOUT.md` | Public vocabulary read-back against all three exact task contracts | **Closed. No fault injection:** `public response vocabulary: 3/3 task contracts covered`. Shared instructions define all fields, types, flag and stage strings uniformly; canonical prompt bundles bind that text, all questions, delivered input hashes and extra instructions. Blind runner behavior is not empirically verified. |
| F5 MINOR — JSON booleans equal numbers | `evals/bench.py`, `tests/test_benchmark_discriminates.py`, `benchmarks/HOLDOUT.md` | `BenchmarkTests.test_json_boolean_numeric_substitutions_are_red` and existing refusal positives | **Closed. Yes:** `0`, `0.0`, `1`, and `1.0` substitutions fail. The new regression failed on numeric zero against the reviewed code before the fix. Equality now preserves nested JSON types. |
| F6 MINOR — unsupported expanded-suite platform claim | `README.md`, `DEVELOPMENT.md`, this appended report | `tests/check_counts.py`; full suite on macOS / Python 3.13.2 | **Closed. No platform fault injection:** current collection is 148; the dated local run reports ten skips (nine environment, one owner cohort). Expanded-suite cluster execution is explicitly unverified. The count checker remains unchanged and enforces all three current claims. |
| F7 NOTE — inherited personal/machine text | this report; new decision addendum | Limited added-line disclosure-indicator scan; protected-path diff | **Answered. No fault injection:** no newly introduced indicator matched; this does not establish repository-wide cleanliness. Broader sanitization stays separately scoped because it includes inherited and protected material. |

The arithmetic controls no longer manufacture internally consistent verdicts.
They score real temporary response files against five pinned synthetic tasks;
all original fraction values, inequality thresholds, duplicate-repeat assertions,
and mismatch refusals remain. Suite drift now rejects during re-scoring, earlier
than the former compatibility check. The owner-record test invokes the same
strict gate as the CLI once its records exist. Unit-test task suites and synthetic
seal metadata stay entirely in scratch and never enter `evals/runs/`.

The independent expected sheet is a hashed task input. Exported sample sets and
count columns must match it independently; count columns represent each expected
sample once. `reference_counts` names hashed independent count tables, checked by
exact byte equality when supplied. Strict nf-core readiness requires every count
reference and materialized FASTQs named by the expected sheet, and rejects source
descriptors still declaring a gap. No tolerance, guard, or test threshold was
weakened. Numerical source independence and real pipeline execution still require
retained owner provenance; directory presence is not wrapper-equivalent validation.

Decision [0046](../decisions/0046-row-2-review-verification-addendum.md) supplements
0045 without editing it, and corrects the inherited README evidence-table claim:
that earlier-row table is missing, not present with unmeasured cells. The index was
regenerated with its existing script. Reviews and reviewed assessments were not
edited; the earlier bytes of this report are preserved.

### Runner results for this round (verbatim)

All shell invocations set `TMPDIR`, `TEMP`, and `TMP` to the required sibling
`*-scratch/` directory before running. Scratch writes used the explicit sandbox
approval mechanism. Tests disabled Python bytecode output, set `GARS_PIPELINES`
to an absent scratch directory, and unset actual holdout/archive variables.
Only synthetic interface tests temporarily supplied those variables. No other
build folder, reviewer conversation, real private holdout, or network was read.

| Command | Summary line(s), verbatim | Exit |
|---|---|---|
| `python3 tests/run_tests.py` | `Ran 148 tests in 159.748s` · `OK (skipped=10)` | 0 |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | 0 |
| `python3 tests/check_counts.py` | `suite: 148 tests, from unittest's loader` · `enforced=3` · `clean — every current claim matches the suite` | 0 |
| `python3 evals/test_harness.py` | `Ran 44 tests in 266.274s` · `OK` | 0 |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` | 0 |
| `python3 tests/test_benchmark_discriminates.py` | `Ran 23 tests in 12.215s` · `OK (skipped=1)` | 0 |
| `python3 evals/bench.py validate` | `valid tasks: 5/5 = 1.000000` | 0 |
| `python3 evals/bench.py row-exit` | `refused: missing owner run record(s): intact-1, intact-2, intact-3, degraded-1` | 2, expected refusal |

The frozen results checker still supplies no Row 2 agent evidence. The three
pre-fix controls (JSON numeric substitution, coherent forgery, missing strict gate)
reported `Ran 3 tests in 0.276s` and `FAILED (failures=2, errors=1)`; the missing
strict function was the error, not a behavioral result. Their individual behaviors
now pass in the benchmark module and full suite. Logs are retained in the sibling
scratch folder as `round1-before.log`, `round1-benchmark.log`, `round1-suite.log`,
`round1-contracts.log`, `round1-counts.log`, `round1-harness.log`,
`round1-results.log`, and `round1-strict-exit.log`; the required command/exit/summary
mapping is `round1-required-results.json`.

Additional checks: Python 3.6 grammar parsing reported
`Python 3.6 grammar: 3/3 files accepted; native execution unverified` for the scorer,
noise helper and benchmark tests; `python3 --version` reported `Python 3.13.2`,
and the platform probe reported `darwin`. Count checking was repeated after the
status wording changed and again reported `enforced=3` and
`clean — every current claim matches the suite`. Read-only `pwd`, `rg`, `cat`,
`sed`, `tail`, and git status/log/diff inspections have no test-runner summary.
`git diff --check` and the explicit protected-tree diff produced no output.
No remote, push, merge, pull request, or broad staging command was used.

## Owner rulings needed

**None for this review round.** The owner explicitly approved the hashed expected
samplesheet field and pre-approved the implementation needed to finish this work.
The review's alternatives were a hashed task input or an immutable expected
samplesheet; the approved implementation uses a samplesheet pinned as a task input.
This authorization does not turn missing data, runs, or sealing evidence into
measured results, and the standing separate-study merge condition still applies.

### Residual gaps still open

- All four real owner runs, genuine degraded configuration evidence, recorded
  observed noise, and both-partition agent discrimination remain absent. The
  strict exit refuses; the repository-suite SKIP is not a Row 2 PASS.
- nf-core RNA and ATAC need independent sample rosters, pinned materialized raw
  inputs, numerical count references and source provenance. Both placeholder
  tasks intentionally remain unable to pass scoring today.
- Actual held-out sealing, producer read denial, independent reference authorship,
  agent authorship of exports, complete prompt/trace retention, and disabled
  design-check/reviewer attestation were not verified by this producer.
- Expanded-suite cluster and native Python 3.6.8 execution were not verified.
  Earlier-row missing README evidence table, clean-design false-alarm measurement,
  growth to ten tasks, and repository-wide sanitization remain separately scoped.
- The separate study's done commit and merge condition were not verified or waived.
  Frozen paths are unchanged; no merge is performed.
