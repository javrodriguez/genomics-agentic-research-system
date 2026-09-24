# Row 9 change report — round 1

Starting hash, recorded before edits:
`e59dfc088fc638a801f255fc0373c139f7afbac4`.
Branch: `build/gars-row-09-review-faults`. No round-1 review file was supplied.
This is the repository code half; **row 9 exit NOT met**. No model was run against
any case. There is no seal, measured run, ledger row or producer approval.

## Changed files and acceptance

- `evals/review-faults/`: closed vocabulary, standalone sealing interface, empty
  seal slots, seven producer plants and five correct small changes; anonymous
  two-commit builder, schema/validator, reference launcher, oracle and scorer.
- `gars/_references/prompts/review_faults_code.md`: fixed reviewer brief; no tuning
  or model execution. Its protected approval remains the later separate record.
- Four `tests/test_review_faults_*.py` modules: collected automatically by the
  unchanged runner, no network and only a synthetic local executable in place
  of Claude. `testing.py` supplies disposable fixtures, mirroring the suite support.
- `scripts/release_check.py`: one row-9 reader; no records means unmeasured.
  `docs/implementation/dod_current.md` was regenerated, never edited by hand.
  Its bytes stay unchanged because no measurement exists.
- README and DEVELOPMENT: the three enforced current counts now say 424;
  DEVELOPMENT has the short invocation/scope paragraph. The README evidence row
  remains untouched.
- Decision 0070 and regenerated decision index; no existing decision bytes edited.
  Reserved records 0071–0074 remain unwritten.

The seven plant assignments are P01 unrelated-refactor, P02 provider-coupling,
P03 off-by-one, P04 dropped-provenance-field, P05 deleted-test, P06
fabricated-test-result and P07 swallowed-exception. Clean cases cover a documented
behaviour-preserving refactor, an existing-behaviour test, a comment correction,
a duplicate-header input refusal with its test, and a documentation correction.
No producer fixture contains a credential-shaped literal. The three sealed classes
are absent from producer plants. Every fixture applies independently to the full
base archive; the applicability summary below is the actual test output.

## Requirement → changed files → acceptance test → result

Each row below names an actual disposable-copy fault watched red, then the named
acceptance test that passes on the implementation. The fault runner requires
nonzero status and a named unittest FAILED result; an import failure is refused.
These public control faults are not the sealed plants or measured reviewer outcomes.

| Requirement / guard and deliberate fault | Changed file | Acceptance test | Result / red-on-fault seen |
|---|---|---|---|
| 6 / 12 construction: repository bytes nondeterministic | `evals/review-faults/build_cases.py` | `test_review_faults_build.py`: `BuildTests.test_determinism_history_and_private_key` | PASS; yes — `fault red: repository bytes nondeterministic` |
| 6 / 12 construction: extra repository history | `evals/review-faults/build_cases.py` | `test_review_faults_build.py`: `BuildTests.test_determinism_history_and_private_key` | PASS; yes — `fault red: extra repository history` |
| 6 / 12 construction: key enters case folder | `evals/review-faults/build_cases.py` | `test_review_faults_build.py`: `BuildTests.test_determinism_history_and_private_key` | PASS; yes — `fault red: key enters case folder` |
| 6 / 12 construction: collision guard removed | `evals/review-faults/build_cases.py` | `test_review_faults_build.py`: `BuildTests.test_build_refusals` | PASS; yes — `fault red: collision guard removed` |
| 6 / 12 construction: nonapplying plant accepted | `evals/review-faults/build_cases.py` | `test_review_faults_build.py`: `BuildTests.test_build_refusals` | PASS; yes — `fault red: nonapplying plant accepted` |
| 9 / 12 scoring and publication: invalid case hidden | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_rates_invalid_and_first_run_cold_twin` | PASS; yes — `fault red: invalid case hidden` |
| 9 / 12 scoring and publication: catch numerator inflated | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_rates_invalid_and_first_run_cold_twin` | PASS; yes — `fault red: catch numerator inflated` |
| 9 / 12 scoring and publication: account name published | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_published_copy_masks_and_keeps_fields` | PASS; yes — `fault red: account name published` |
| 9 / 12 scoring and publication: raw host digest published | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_published_copy_masks_and_keeps_fields` | PASS; yes — `fault red: raw host digest published` |
| 9 / 12 scoring and publication: kit prefix published | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_published_copy_masks_and_keeps_fields` | PASS; yes — `fault red: kit prefix published` |
| 9 / 12 scoring and publication: home prefix published | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_published_copy_masks_and_keeps_fields` | PASS; yes — `fault red: home prefix published` |
| 9 / 12 oracle: oracle ignores class | `evals/review-faults/oracle.py` | `test_review_faults_core.py`: `OracleTests.test_full_grid` | PASS; yes — `fault red: oracle ignores class` |
| 9 / 12 oracle: oracle ignores file | `evals/review-faults/oracle.py` | `test_review_faults_core.py`: `OracleTests.test_full_grid` | PASS; yes — `fault red: oracle ignores file` |
| 9 / 12 oracle: line tolerance widened | `evals/review-faults/oracle.py` | `test_review_faults_core.py`: `OracleTests.test_full_grid` | PASS; yes — `fault red: line tolerance widened` |
| 9 / 12 oracle: min severity ignored | `evals/review-faults/oracle.py` | `test_review_faults_core.py`: `OracleTests.test_full_grid` | PASS; yes — `fault red: min severity ignored` |
| 9 / 12 oracle: file mode ignored | `evals/review-faults/oracle.py` | `test_review_faults_core.py`: `OracleTests.test_full_grid` | PASS; yes — `fault red: file mode ignored` |
| 9 / 12 oracle: repository prefix retained | `evals/review-faults/oracle.py` | `test_review_faults_core.py`: `OracleTests.test_full_grid` | PASS; yes — `fault red: repository prefix retained` |
| 9 / 12 oracle: NOTE becomes alarm | `evals/review-faults/oracle.py` | `test_review_faults_core.py`: `OracleTests.test_full_grid` | PASS; yes — `fault red: NOTE becomes alarm` |
| 7 / 12 record validation: closed enum ignored | `evals/review-faults/review_record.py` | `test_review_faults_core.py`: `ContractTests.test_classes_closed` | PASS; yes — `fault red: closed enum ignored` |
| 7 / 12 record validation: required fields ignored | `evals/review-faults/review_record.py` | `test_review_faults_core.py`: `ContractTests.test_schema_contract_drift` | PASS; yes — `fault red: required fields ignored` |
| 8 / 12 launch: envelope taken from stub text | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_envelope_and_command_are_code_owned` | PASS; yes — `fault red: envelope taken from stub text` |
| 8 / 12 launch: producer uid check removed | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_identity_refusals` | PASS; yes — `fault red: producer uid check removed` |
| 8 / 12 launch: unresolved producer account accepted | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_identity_refusals` | PASS; yes — `fault red: unresolved producer account accepted` |
| 8 / 12 launch: root uid allowed | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_identity_refusals` | PASS; yes — `fault red: root uid allowed` |
| 8 / 12 launch: missing model allowed | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_api_model_and_prompt_refusals` | PASS; yes — `fault red: missing model allowed` |
| 8 / 12 launch: API key allowed | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_api_model_and_prompt_refusals` | PASS; yes — `fault red: API key allowed` |
| 8 / 12 launch: prompt hash not checked | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_api_model_and_prompt_refusals` | PASS; yes — `fault red: prompt hash not checked` |
| 8 / 12 launch: output owner ignored | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_review_output_owner` | PASS; yes — `fault red: output owner ignored` |
| 8 / 12 launch: symlink output followed | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_symlink_review_is_invalid` | PASS; yes — `fault red: symlink output followed` |
| 8 / 12 launch: parent step rule removed | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_blindness_every_spelling` | PASS; yes — `fault red: parent step rule removed` |
| 8 / 12 launch: absolute path rule removed | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_blindness_every_spelling` | PASS; yes — `fault red: absolute path rule removed` |
| 8 / 12 launch: home path rule removed | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_blindness_every_spelling` | PASS; yes — `fault red: home path rule removed` |
| 7 / 12 record validation: blindness does not invalidate | `evals/review-faults/review_record.py` | `test_review_faults_launch.py`: `LaunchTests.test_blindness_stream_makes_record_invalid` | PASS; yes — `fault red: blindness does not invalidate` |
| 8 / 12 launch: limit no longer stops | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_usage_limit_stops_retains_and_resumes` | PASS; yes — `fault red: limit no longer stops` |
| 8 / 12 launch: only filter ignored | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_only_and_existing_never_overwritten` | PASS; yes — `fault red: only filter ignored` |
| 8 / 12 launch: existing review rerun allowed | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_only_and_existing_never_overwritten` | PASS; yes — `fault red: existing review rerun allowed` |
| 8 / 12 launch: assistant model mismatch ignored | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_model_mismatch_invalid_and_synthetic_ignored` | PASS; yes — `fault red: assistant model mismatch ignored` |
| 8 / 12 launch: model mismatch accepted | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_model_mismatch_invalid_and_synthetic_ignored` | PASS; yes — `fault red: model mismatch accepted` |
| 8 / 12 launch: settings copy altered | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_envelope_and_command_are_code_owned` | PASS; yes — `fault red: settings copy altered` |
| 8 / 12 launch: neutral parent rule removed | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_environment_and_neutral_parent_guard` | PASS; yes — `fault red: neutral parent rule removed` |
| 8 / 12 launch: Claude environment retained | `evals/review-faults/run_reviews.py` | `test_review_faults_launch.py`: `LaunchTests.test_envelope_and_command_are_code_owned` | PASS; yes — `fault red: Claude environment retained` |
| 6 / 12 construction: answer key in case allowed | `evals/review-faults/build_cases.py` | `test_review_faults_build.py`: `BuildTests.test_answer_key_base_refused` | PASS; yes — `fault red: answer key in case allowed` |
| 6 / 12 construction: neutral id omits salt | `evals/review-faults/build_cases.py` | `test_review_faults_build.py`: `BuildTests.test_salt_changes_neutral_identifier` | PASS; yes — `fault red: neutral id omits salt` |
| 6 / 12 construction: output inside worktree allowed | `evals/review-faults/build_cases.py` | `test_review_faults_build.py`: `BuildTests.test_worktree_output_refused` | PASS; yes — `fault red: output inside worktree allowed` |
| 9 / 12 scoring and publication: first run always true | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_rates_invalid_and_first_run_cold_twin` | PASS; yes — `fault red: first run always true` |
| 9 / 12 scoring and publication: answer hashes not checked | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_tamper_and_mixed_records` | PASS; yes — `fault red: answer hashes not checked` |
| 9 / 12 scoring and publication: mixed models accepted | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_tamper_and_mixed_records` | PASS; yes — `fault red: mixed models accepted` |
| 7 / 12 record validation: same uid record accepted | `evals/review-faults/review_record.py` | `test_review_faults_core.py`: `ScoreTests.test_tamper_and_mixed_records` | PASS; yes — `fault red: same uid record accepted` |
| 7 / 12 record validation: record prompt mismatch accepted | `evals/review-faults/review_record.py` | `test_review_faults_core.py`: `ScoreTests.test_tamper_and_mixed_records` | PASS; yes — `fault red: record prompt mismatch accepted` |
| 9 / 12 scoring and publication: latest invalid attempt selected | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_latest_valid_attempt_retains_all` | PASS; yes — `fault red: latest invalid attempt selected` |
| 9 / 12 scoring and publication: mask literal retained | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_published_copy_masks_and_keeps_fields` | PASS; yes — `fault red: mask literal retained` |
| 9 / 12 scoring and publication: raw uid published | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_published_copy_masks_and_keeps_fields` | PASS; yes — `fault red: raw uid published` |
| 9 / 12 scoring and publication: zero denominator hidden | `evals/review-faults/score.py` | `test_review_faults_core.py`: `ScoreTests.test_rates_invalid_and_first_run_cold_twin` | PASS; yes — `fault red: zero denominator hidden` |

Additional acceptance and limits:

| Requirement | Changed files | Acceptance test | Result / red-on-fault seen |
|---|---|---|---|
| 2, 3: exactly seven assigned plants and five clean, full-base patch application | classes.json; fixtures; build_cases.py | BuildTests.test_every_fixture_applies_to_base_archive | PASS, 12/12; malformed patch guard watched red above |
| 6: full root tree, exactly two commits, fixed identities and deterministic bytes | build_cases.py | BuildTests.test_determinism_history_and_private_key | PASS; extra history, nondeterminism and key inclusion each watched red |
| 12: every-byte absence of class ids in the full case tree | build_cases.py; test_review_faults_build.py | BuildTests.test_base_vocabulary_conflict_is_reproducible | NOT met; no — contradictory acceptance stopped for ruling 1 |
| 7: JSON Schema required/enum contract and closed class definitions | review_record.py; schema; classes.json | ContractTests.test_schema_contract_drift; test_classes_closed | PASS; required and enum removal watched red |
| 8: unknown producer account, root and same-account launch refuse | run_reviews.py | LaunchTests.test_identity_refusals | PASS; root, same-account and unknown-account guards each watched red |
| 8: exact command/settings, no local clone links, remote/reflog removal, launch identity | run_reviews.py | LaunchTests.test_envelope_and_command_are_code_owned | PASS; stub envelope, settings and environment faults watched red |
| 8: allowed system devices/executables and in-kit paths are not hits | run_reviews.py | LaunchTests.test_blindness_every_spelling | PASS positive controls; outside absolute/home/parent paths watched red |
| 9: NOTE clean versus MINOR clean; ±3 versus ±4, file-only mode and prefix normalization | oracle.py | OracleTests.test_full_grid | PASS; each matching guard watched red above |
| 9: earlier-run versus empty-runs cold-start twin, including a second model at the same prompt | score.py | ScoreTests.test_rates_invalid_and_first_run_cold_twin | PASS; always-first fault watched red |
| 11: independent-context code results never meet the public/science clause | scripts/release_check.py | ScoreTests.test_release_development_only | PASS on synthetic 10/10; no real result published; red-on-fault no separate adapter mutation |
| 13: suite collection and three living-document claims agree | README; DEVELOPMENT; four test modules | tests/check_counts.py | PASS, enforced=3; initial stale count check refused before count update |
| 3: both real gitleaks rulesets over staged fixtures | fixtures only staged at hook invocation | repository pre-commit hook | NOT met; gitleaks absent; hook REFUSED; no bypass or replacement scanner |
| Python 3.6 syntax | every new Python module | ast.parse feature_version=(3, 6) | PASS; native Python 3.6 execution NOT met |

## Existing expectations changed

None. No existing test module, test assertion, threshold, hook, policy, seam or pin
was edited. Count prose changes describe current collection and link to this run's
actual execution instead of applying a new count to old platform evidence.

## Commands and execution method

Every operator command was issued from the repository root. No initial directory
change was used. TMPDIR, TEMP and TMP were set to `../gars-row-9-scratch/` before
commands. The scratch-only `run_checks.py` driver resolves that approved directory
at runtime for child processes, sets PYTHONDONTWRITEBYTECODE, unsets CI and
GARS_ROW5_SCRATCH for cold-clone modes, and names an empty scratch pipeline folder.
Mode C then unsets TMPDIR while retaining TEMP and TMP there. All logs, temporary
repositories, executable stubs and mutation copies stay in that scratch twin.
No environment values or credentials were inspected or printed. Python is 3.13.5,
which also supplies the >=3.9 interpreter needed by evals/test_harness.py.
`rg` was absent, so repository-only grep/find/sed were used for required reads.
The requested tests/test_secret_containment.py path does not exist at the base;
its actual suite module, gars/tests/test_secret_containment.py, was read in full
and remains unchanged. The suite runner also exercises it subject to its skips.

The first mode-B run failed on an ineffective host-mask control mutation, not a
production assertion: the later text mask still removed the digest. The corrected
fault returns the raw digest directly. The additional general home-path masking
likewise required a direct bypass control. The final fault list contains 53 named
red witnesses. No assertion was weakened to accept either ineffective mutation.
Final full-suite results are below; earlier failed logs remain private in scratch.

Mode A: NOT verified; Docker is not reachable by this account, as stated in the
lane brief. Modes B/C skips are retained, not counted as executed acceptance.

`python3 tests/run_tests.py (mode B)`:

```text
collected 250 tests from tests
collected 174 tests from gars/tests
citations: 1/1 resolve
citations: 1/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/0 resolve
citations: 0/0 resolve
citations: 0/1 resolve
citations: 292/292 resolve
literal case-byte class sweep: NOT met; base tree already contains class vocabulary
fixtures: git apply --check passed for 12/12 against base archive
Ran 424 tests in 72.712s
OK (skipped=59)
```

`python3 tests/run_tests.py (mode C)`:

```text
collected 250 tests from tests
collected 174 tests from gars/tests
citations: 1/1 resolve
citations: 1/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/0 resolve
citations: 0/0 resolve
citations: 0/1 resolve
citations: 292/292 resolve
literal case-byte class sweep: NOT met; base tree already contains class vocabulary
fixtures: git apply --check passed for 12/12 against base archive
Ran 424 tests in 67.547s
OK (skipped=86)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 250 tests from tests
collected 174 tests from gars/tests
suite: 424 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 38.091s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 tests/test_review_faults_core.py`:

```text
Ran 8 tests in 0.018s
OK
```

`python3 tests/test_review_faults_launch.py`:

```text
Ran 11 tests in 0.759s
OK
```

`python3 tests/test_review_faults_build.py`:

```text
Ran 7 tests in 8.464s
OK
literal case-byte class sweep: NOT met; base tree already contains class vocabulary
fixtures: git apply --check passed for 12/12 against base archive
```

`python3 tests/test_review_faults_faults.py`:

```text
Ran 1 test in 4.189s
OK
```

`feature_version=(3, 6) parse`:

```text
Python feature_version=(3, 6): 11/11 new Python files parsed
```

`python3 gars/_system/hooks/pre-commit (new fixtures staged)`:

```text
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 292/292 resolve
pre-commit: REFUSED
```

`python3 gars/_system/hooks/pre-commit (all final paths staged)`:

```text
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 292/292 resolve
pre-commit: REFUSED
```

`python3 scripts/release_check.py` regenerated the table; its summary:

```text
DoD cells regenerated: 13/13
```

The reviewer row from that generated file is:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

`bash docs/decisions/build_index.sh` was rerun. Its output identifies the regenerated
decision index; the machine-specific prefix is deliberately not copied here.

## Boundary verification

Each required command produced empty output (including staged and unstaged changes):

```sh
git diff --stat e59dfc0 -- .github/ gars/_system/ benchmarks/ docs/ledger.csv
```

Output: empty.

```sh
git diff --stat e59dfc0 -- evals/ ':(exclude)evals/review-faults/'
```

Output: empty.

```sh
git diff --stat e59dfc0 -- gars/_references/ ':(exclude)gars/_references/prompts/review_faults_code.md'
```

Output: empty.

`git diff --check` has empty output. `git diff --cached --check` reports whitespace
in the new plant.diff files: unified-diff blank context lines contain their required
single-space prefix, including the final context line of P07. These are patch
syntax, not introduced whitespace in the patched source. GARS launch_role()
remains producer. The Gap Study,
benchmark, CI, ledger and existing decision bytes remain untouched. No remote,
push, pull request, merge, seal or measured reviewer session was performed.

## Owner rulings needed

1. **Full-base tree versus literal every-byte absence.** Item 6 requires the entire
   base tree. Item 12 requires absence of every class id in every case byte. Base
   specification §10 line 243 already contains off-by-one and race, as reproduced
   from the exact base object. Options: allow inherited unchanged base bytes and
   test newly introduced case-identifying/answer metadata; or retain the literal
   absence criterion and authorize a different exported source tree. The latter
   changes item 6. No choice is made here. The literal sweep is stopped and NOT met;
   construction, history, key placement, salt and manifest tests run independently.
   The async clarification remained unanswered when this report was prepared.
2. **Real fixture secret scan unavailable.** The repository hook refuses because
   gitleaks is absent from PATH. Options: provide an offline executable in the
   approved work area and rerun the unchanged hook; or retain this check as NOT met
   until the later equipped review environment runs it. No network install, hook
   change, scanner substitution or bypass was performed. Ordinary producer commit
   creation does not turn this refused manual check into a pass; this checkout has
   no installed pre-commit hook, and no hook installation/configuration was changed.

## Residual gaps — each NOT met

- Full row 9 exit: the seal and first measured run, CP7–CP9, remain later work.
- Literal case-byte absence acceptance and the real gitleaks fixture scan.
- R-093 code half: launch_role() is still producer; actual two-user/read-only
  credential deployment evidence remains outside this repository.
- Resistance to a reviewer guessing the measurement from the diff's style.
- Different model-family independence between the sealer and producer (R9-C).
- Public credibility: independent_context evidence is development only; public
  claims still need external_human_seal under §10 and §21 Q9.
- Science half (row 10) and trailer-gate JSON consumption (row 11's session line).
- Broad per-class sample size: one plant yields only 0/1 or 1/1.
- Public recomputation of the three private sealed outcomes: hashes only;
  a stranger recomputes twelve of fifteen outcomes from repository inputs.
- Protected-path approval in the separate later record 0071, independent review,
  merge-result CI, native Python 3.6 runtime and Docker mode A.

## Rulings round R1

2026-09-23. Starting hash, recorded before edits:
`767a986d6477ba1fae50e0d5a9dd214811549b39`.
No review was supplied, read or requested. Earlier report and decision bytes are
preserved. This is a rulings round, not a response to a review.

| Ruling or item | Changed files | Test | Result; red-on-fault seen |
|---|---|---|---|
| Q1 A / item 14(a) | `evals/review-faults/testing.py`; `tests/test_review_faults_build.py`; `tests/test_review_faults_faults.py`; append-only 0070 addendum | `BuildTests.test_added_case_bytes_sweep`; `test_base_exemption_is_byte_identity_at_same_path`; `test_added_byte_leak_control`; `FaultTests.test_every_guard_fault_is_red` | Sweep implemented literally; full-case acceptance NOT met and stopped for the scope rulings below. Yes: twelve injected leaks and two incorrect exemptions turn their named test red in disposable copies. All 53 earlier faults remain red as required. |
| Q2 A / item 14(b) | append-only 0070 addendum and this report | Unchanged repository pre-commit hook, with all 24 fixture files staged in a disposable base-tree repository | NOT met, as ruled: gitleaks absent; hook REFUSED. Red-on-fault: no scanner mutation or replacement; actual refusal observed. Nothing installed. |
| Item 14(c) | `evals/review-faults/README.md`; `tests/test_review_faults_core.py` | Direct core tests and prefix comparison of 0070 against starting commit | PASS: repository-relative Markdown text and `os.path.join` suffixes; every original 0070 byte preserved. Red-on-fault: no separate spelling mutation; existing masking mutations still turn the named test red. |
| Collection count required by the added tests | `README.md`; `DEVELOPMENT.md` | `tests/check_counts.py` | PASS: three claims now match 426 collected tests. No existing assertion or threshold weakened; red-on-fault: no count mutation. DEVELOPMENT's row-9 paragraph names the remaining scope stop. |

The sweep reads the submitted diff, applied Git diff, decoded raw commit objects
for both commits (including authors, dates and messages), case and repo folder
names, manifest bytes, and all file bytes under each repo. It scans every class
id, every fixture case id, and every repository-relative fixture directory path.
A file is exempt only if its bytes equal the base blob at that exact path.
There is no filename, directory or Git-storage exemption. Git metadata is read
both in storage and decoded form so compression cannot conceal a commit message.

The byte-identity control uses a small synthetic two-commit repo with inherited
class vocabulary. Its intact baseline passes; adding one newline at the same
path must expose the vocabulary; copying identical bytes to a new path must also
expose it. The full twelve-case acceptance separately uses the actual base archive.
Synthetic controls are not substituted for acceptance over the shipped fixtures.

Named new red witnesses (each line was printed by the disposable-copy fault run):

```text
fault red: added-byte leak in commit message: off-by-one
fault red: added-byte leak in root commit message: off-by-one
fault red: added-byte leak in changed file: off-by-one
fault red: added-byte leak in folder name: off-by-one
fault red: added-byte leak in manifest: off-by-one
fault red: added-byte leak in plant diff: off-by-one
fault red: added-byte leak in commit message: P01
fault red: added-byte leak in root commit message: P01
fault red: added-byte leak in changed file: P01
fault red: added-byte leak in folder name: P01
fault red: added-byte leak in manifest: P01
fault red: added-byte leak in plant diff: P01
fault red: changed base file wrongly exempt
fault red: renamed base blob wrongly exempt
```

The two exemption faults mutate the comparison into a path-only exemption or a
content-anywhere exemption. Each causes the byte-identity test to fail. The twelve
leak faults add either `off-by-one` or `P01` to each of: second commit message,
root commit message, changed file, case folder name, manifest, and plant diff.
The unmutated controls pass. The full real-case acceptance fails independently.

### Required command summaries

All operator commands ran from the repository root. TMPDIR, TEMP and TMP pointed
to the approved scratch twin; child-process paths were resolved at runtime.
Mode C unsets TMPDIR while retaining TEMP and TMP there. Logs, disposable repos,
mutation copies and the fixture-hook copy stay in scratch. No model or network
was used. Initial exploratory failures are retained in scratch; the final summaries
below are from the final implementation. Native Python 3.6 execution is not claimed.
The Python 3.6 parser check is separate.

The fixture-hook driver archives the base into a disposable repository, commits
that tree with the fixed synthetic producer identity, copies only the existing
fixtures, and stages their 24 files with path-limited `git add`. It asserts the
actual cached diff lists exactly those paths before invoking the unchanged hook.
The source checkout's index and hooks are not changed by that check. An earlier
alternate-index setup was discarded because comparing its index to the source
HEAD would not present the fixtures as additions; it is not the reported scan.

`python3 tests/run_tests.py (mode B)`:

```text
collected 252 tests from tests
collected 174 tests from gars/tests
first failing test: test_review_faults_build.BuildTests.test_added_case_bytes_sweep
citations: 1/1 resolve
citations: 1/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/0 resolve
citations: 0/0 resolve
citations: 0/1 resolve
citations: 292/292 resolve
DoD cells regenerated: 13/13
DoD cells regenerated: 13/13
DoD cells verified: 13/13 byte-stable
DoD cells regenerated: 13/13
DoD cells verified: 13/13 byte-stable
DoD cells regenerated: 13/13
DoD cells verified: 1/1 byte-stable
fixtures: git apply --check passed for 12/12 against base archive
Ran 426 tests in 98.333s
FAILED (failures=1, skipped=59)
```

`python3 tests/run_tests.py (mode C)`:

```text
collected 252 tests from tests
collected 174 tests from gars/tests
first failing test: test_review_faults_build.BuildTests.test_added_case_bytes_sweep
citations: 1/1 resolve
citations: 1/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/0 resolve
citations: 0/0 resolve
citations: 0/1 resolve
citations: 292/292 resolve
DoD cells regenerated: 13/13
DoD cells regenerated: 13/13
DoD cells verified: 13/13 byte-stable
DoD cells regenerated: 13/13
DoD cells verified: 13/13 byte-stable
DoD cells regenerated: 13/13
DoD cells verified: 1/1 byte-stable
fixtures: git apply --check passed for 12/12 against base archive
Ran 426 tests in 91.798s
FAILED (failures=1, skipped=86)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 252 tests from tests
collected 174 tests from gars/tests
suite: 426 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 37.890s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 tests/test_review_faults_core.py`:

```text
Ran 8 tests in 0.019s
OK
```

`python3 tests/test_review_faults_launch.py`:

```text
Ran 11 tests in 0.795s
OK
```

`python3 tests/test_review_faults_build.py`:

```text
Ran 9 tests in 31.379s
FAILED (failures=1)
fixtures: git apply --check passed for 12/12 against base archive
```

`python3 tests/test_review_faults_faults.py`:

```text
Ran 1 test in 5.382s
OK
```

`feature_version=(3, 6) parse`:

```text
Python feature_version=(3, 6): 11/11 new Python files parsed
```

`python3 gars/_system/hooks/pre-commit (24 fixture files staged in disposable base repository)`:

```text
fixture hook index: 24 fixture files staged against base
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 292/292 resolve
pre-commit: REFUSED
```

`python3 scripts/release_check.py`:

```text
DoD cells regenerated: 13/13
```

The regenerated reviewer row remains:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

`bash docs/decisions/build_index.sh` was rerun after the addenda; its generated
index is byte-identical because the indexed frontmatter is unchanged. Its output
names that index with a machine-specific prefix, which is not published here.
The release render is likewise unchanged. The README evidence row is untouched.

Mode A: NOT verified; Docker is not reachable by this account. Modes B and C
have one failure, `BuildTests.test_added_case_bytes_sweep`, and retained skips.
The failure is neither skipped nor marked expected. No existing guard was relaxed.

### Boundary verification

`git diff --check` is clean. Comparison against the public base yields no changes
to the protected boundary sets: `.github/`, `gars/_system/`, `benchmarks/`,
`docs/ledger.csv`, evals outside this row, references outside the one prompt,
or decision files other than 0070 and the index. This round changes neither
fixtures nor prompt. Starting-commit prefix checks preserve all earlier bytes of
0070 and this report. Reserved records 0071–0074 are untouched. No remote, push,
merge or pull request was used.

## Owner rulings needed

1. **Inherited vocabulary in a changed file.** Item 14(a) requires the whole file
   to be scanned once any byte differs. P02 changes `gars/_system/executorlib.py`,
   which already contains the word `race` at base line 108. P04 changes
   `gars/_system/wrapperlib.py`, with `race` at base lines 645 and 668. P06 changes
   `tests/run_tests.py`, whose base text contains those bytes inside `braces` and
   `traceback`. These remain in the post-change files. Options: A, retain the
   whole-file/literal sweep and authorize replacing the affected plants while
   preserving their assigned classes; B, exempt unchanged portions of changed
   files, which changes the stated whole-file scope. No choice is made here.
2. **Literal Git storage versus decoded base identity.** The original every-byte
   sweep, narrowed only by item 14(a)'s identical-base-blob exemption, also visits
   Git files, which have no blob at the same base path. All twelve cases contain
   incidental case-id byte strings in compressed objects inherited from the base.
   A concrete witness is `P04` inside the object file named
   `.git/objects/01/6f0f998d1eaf95b518541239bf89a36ab7df70`; it appears even in C03.
   Options: A, inspect decoded Git objects, exempting only base-identical content
   while always scanning commit metadata and newly introduced objects; B, retain
   literal storage-byte absence and authorize a different encoding or case-id
   vocabulary that can meet it. No Git-path exemption, encoding change or case-id
   vocabulary change is made here. This part stops pending the ruling.

## Residual gaps after R1

- Q1's exact literal acceptance remains NOT met pending the two scope rulings;
  its implementation and synthetic leak controls do not constitute a pass.
- Fixture pre-commit secret check remains NOT met on this host: both real gitleaks
  rulesets still wait on the lane's independent verification, per Q2 A.
- Full row 9 exit: three sealed slots, later seal/ledger records, deployment
  evidence and the first measured run remain the owner's later work. No model
  was run; no first-run claim is made.
- R-093's code half remains open: `launch_role()` still returns producer. Two-user
  read-only-credential deployment evidence lives outside this repository.
- Diff-style inference, model-family independence, the thin per-class sample,
  and hash-only public checking of three private sealed outcomes remain limits.
- Independent-context evidence is development only; public evidence still needs
  external-human seals. Science and trailer-gate JSON consumption remain later rows.
- Protected-path approval in reserved 0071, independent review, merge-result CI,
  Docker mode A and a native Python 3.6 run remain unverified.

Q2 A and item 14(c) are carried out; Q1 A is implemented but its literal acceptance
is stopped for the numbered scope rulings. The fixture secret scan, seals,
measured run and row exit wait on the owner and independent verification.

## Rulings round S1

2026-09-23. Starting hash, recorded before reads or edits:
`6af7e2a15308008e366e1f7f61aabb49e17a1b9a`.
No review was supplied, read or requested. This round applies the supplied
rulings; it is not a review response. All earlier bytes of this report and 0070
are preserved. No model was run against any case.

| Ruling or item | Changed files | Test | Result; red-on-fault seen |
|---|---|---|---|
| Q3 A / item 15(i): committed added lines and whole added files | `evals/review-faults/testing.py`; `tests/test_review_faults_build.py`; `tests/test_review_faults_faults.py` | `BuildTests.test_added_byte_leak_control`; `test_base_exemption_is_byte_identity_at_same_path`; `FaultTests.test_every_guard_fault_is_red` | PASS; yes — separate disposable changed-file and added-file injections of both `off-by-one` and `P01` make the named test red. A copied inherited blob is still scanned in full when added under a new name. |
| Q4 A / item 15(ii): decoded reachable Git objects | Same three files; append-only 0070 addendum | Same named control tests; `BuildTests.test_added_case_bytes_sweep` | PASS; yes — separate injections in decoded second-commit messages, root-commit messages and new tree entry names make the named test red for both tokens. Repacking leaves the clean result unchanged; an unreachable object carrying both tokens stays outside the sweep. |
| Item 15(iii): case and repo folder names | Same three test/support files | `BuildTests.test_added_byte_leak_control`; `FaultTests.test_every_guard_fault_is_red` | PASS; yes — each token injected into the case folder name turns the named test red. Both case and repo names remain scanned. |
| Item 15(iv): manifest bytes | Same three test/support files | Same named control tests | PASS; yes — each token injected only into manifest bytes turns the named test red. |
| Exemption's other direction: unchanged line of a changed file | Same three test/support files | `BuildTests.test_base_exemption_is_byte_identity_at_same_path`; `test_added_byte_leak_control`; `FaultTests.test_every_guard_fault_is_red` | PASS; green seen: yes — separate disposable injections of each token into an inherited line, followed by a different added line in that file, leave the named test green. Red-on-fault seen: yes — scanning a modified blob's whole content instead makes the named test red. |
| Twelve shipped cases pass the sweep | `evals/review-faults/testing.py`; `tests/test_review_faults_build.py` | `BuildTests.test_added_case_bytes_sweep`; `test_every_fixture_applies_to_base_archive` | PASS, 12/12 clear and 12/12 apply. Red-on-fault: yes for the separately named surface controls above; no shipped fixture was mutated. No fixture, expected answer, manifest format or prompt changes were needed. |
| Current development status and existing count claims | `DEVELOPMENT.md` | `tests/run_tests.py`, modes B/C; `tests/check_counts.py` | PASS; all three claims already equal 426, so no count or README edit is needed. Red-on-fault: no separate prose/count mutation. The stale R1 scope-stop paragraph is updated. |
| Append-only ruling record and index | 0070 addendum; regenerated decision index (byte-identical) | Starting-commit prefix comparison; `bash docs/decisions/build_index.sh` | PASS; red-on-fault: no record mutation. The exact Q3/Q4 questions and chosen options and the uncorrected delegation sentence are quoted, attributed only as supplied. Item 15's implementation is labelled the lane's specification. |

### Scope and observed controls

Item 15 supersedes item 14(a) where they differ. Q3's unchanged-line exemption
applies to decoded modified blobs too; decoding is not an excuse to sweep those
unchanged lines again. Whole new files are still swept, including a byte-identical
copy of an inherited blob. New decoded tree names and full commit metadata remain
covered. The case's first commit has the exact base tree with no imported history;
the sweep compares to that tree. Raw compressed storage, uncommitted files and
unreachable objects are not additional surfaces. No path-name exemption is used.

R1's controls are carried forward on the now-ruled surfaces: changed files and
new diff content are committed before the sweep, rather than relying on a scan
of uncommitted working files or the submitted patch's context. The same-path
exemption control now rejects a leak on an added line while allowing inherited
lines, as Q3 requires. The copied-blob control still rejects an inherited blob
introduced as a whole new file. All 53 round-1 guard faults remain in the list.
The direct harness fault module observed 70 red witnesses and two green exemption
witnesses. No existing production guard, threshold, schema or CI file changed.

The S1/R1 surface-control summary lines, verbatim from the direct fault module:

```text
fault red: added-byte leak in commit message: off-by-one
fault red: added-byte leak in root commit message: off-by-one
fault red: added-byte leak in changed file: off-by-one
fault red: added-byte leak in folder name: off-by-one
fault red: added-byte leak in manifest: off-by-one
fault red: added-byte leak in plant diff added file: off-by-one
fault red: added-byte leak in decoded tree name: off-by-one
fault red: added-byte leak in commit message: P01
fault red: added-byte leak in root commit message: P01
fault red: added-byte leak in changed file: P01
fault red: added-byte leak in folder name: P01
fault red: added-byte leak in manifest: P01
fault red: added-byte leak in plant diff added file: P01
fault red: added-byte leak in decoded tree name: P01
fault red: changed base file wrongly exempt
fault red: renamed base blob wrongly exempt
fault red: unchanged lines wrongly swept
exemption green: unchanged line of changed file: off-by-one
exemption green: unchanged line of changed file: P01
```

### Required command summaries

Commands ran from the repository root with temporary files and logs in the
approved scratch twin. The check driver resolves that folder at runtime, selects
an empty scratch pipeline directory and retains the same cold-clone setup used
in R1. Mode B sets TMPDIR, TEMP and TMP there. Mode C unsets TMPDIR and retains
TEMP and TMP there. The full suite's environment skips remain skips, not passed
acceptance. No network, model, credential inspection or hook/configuration change
was used. Python 3.6 syntax is checked separately from native runtime execution.

`python3 tests/run_tests.py (mode B)`:

```text
collected 252 tests from tests
collected 174 tests from gars/tests
citations: 1/1 resolve
citations: 1/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/0 resolve
citations: 0/0 resolve
citations: 0/1 resolve
citations: 292/292 resolve
DoD cells regenerated: 13/13
DoD cells regenerated: 13/13
DoD cells regenerated: 13/13
DoD cells regenerated: 13/13
added case-byte sweep: 12/12 clear; item 15 added lines and decoded objects
fixtures: git apply --check passed for 12/12 against base archive
Ran 426 tests in 104.674s
OK (skipped=59)
```

`python3 tests/run_tests.py (mode C)`:

```text
collected 252 tests from tests
collected 174 tests from gars/tests
citations: 1/1 resolve
citations: 1/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/1 resolve
citations: 0/0 resolve
citations: 0/0 resolve
citations: 0/1 resolve
citations: 292/292 resolve
DoD cells regenerated: 13/13
DoD cells regenerated: 13/13
DoD cells regenerated: 13/13
DoD cells regenerated: 13/13
added case-byte sweep: 12/12 clear; item 15 added lines and decoded objects
fixtures: git apply --check passed for 12/12 against base archive
Ran 426 tests in 111.404s
OK (skipped=86)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 252 tests from tests
collected 174 tests from gars/tests
suite: 426 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 38.660s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 tests/test_review_faults_core.py`:

```text
Ran 8 tests in 0.019s
OK
```

`python3 tests/test_review_faults_launch.py`:

```text
Ran 11 tests in 0.849s
OK
```

`python3 tests/test_review_faults_build.py`:

```text
Ran 9 tests in 37.404s
OK
added case-byte sweep: 12/12 clear; item 15 added lines and decoded objects
fixtures: git apply --check passed for 12/12 against base archive
```

`python3 tests/test_review_faults_faults.py`:

```text
Ran 1 test in 6.239s
OK
```

`feature_version=(3, 6) parse`:

```text
Python feature_version=(3, 6): 11/11 new Python files parsed
```

`python3 gars/_system/hooks/pre-commit (24 fixtures staged in a disposable base repository)`:

```text
fixture hook index: 24 fixture files staged against base
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 292/292 resolve
pre-commit: REFUSED
```

`python3 scripts/release_check.py`:

```text
DoD cells regenerated: 13/13
```

The regenerated reviewer row, verbatim:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

The release render and regenerated decision index are byte-identical to their
starting versions. The README evidence row and all fixture bytes are unchanged.
The fixture hook checked precisely the 24 staged fixture paths in a disposable
base-tree repository; its secret scan is NOT met, and its actual refusal is
reported above. No substitute scanner or bypass was used.

### Boundary verification

Starting-commit prefix comparisons preserve every preceding byte of 0070 and
this report. `git diff --check` is clean. Against the public base, there are no
changes to CI, system code, benchmarks, the ledger, evals outside this row,
references outside the previously added prompt, or other decision records.
This round changes neither fixtures nor prompt. Reserved 0071–0074 are untouched.
No remote, push, merge or pull request was used. One path-limited commit records
this round; its message file lives in scratch.

## Owner rulings needed

None. Q3 A and Q4 A resolve both R1 scope questions. No further schema, threshold,
scope or CI decision is taken under the delegation.

## Residual gaps after S1

- Fixture pre-commit secret check remains NOT met on this host: gitleaks is
  unavailable; both real rulesets await the lane's independent verification,
  as ruled by Q2 A.
- Row 9 exit remains NOT met: the three sealed slots, later seal/ledger records,
  separate-user/read-only-credential deployment evidence and the first measured
  run remain the owner's later work. No model was run and no first-run evidence
  is claimed.
- R-093's code half stays open: `launch_role()` still returns producer. The uid
  check proves only that reviewing and producing OS accounts differ on the review
  host, not which machine built cases or how GARS assigns its own roles.
- Diff-style inference, shared sealer/producer model family, one-plant-per-class
  sample size, and hash-only public checking of three private sealed outcomes
  remain limits; strangers can recompute only twelve of fifteen outcomes.
- Independent-context seals are development evidence only. Public claims need
  external-human seals. Science and trailer-gate JSON consumption remain later
  rows.
- Protected-path approval in reserved 0071, independent review, merge-result CI,
  native Python 3.6 execution and Docker mode A remain unverified. Mode A requires
  Docker, which this account cannot reach.

Q3 A, Q4 A and item 15(i)–(iv) are carried out; Q2 A remains carried out as an
explicit NOT-met fixture scan. Seals, measured run, deployment evidence,
independent secret verification, protected approval and the row exit wait on
the owner and later independent verification.

## Review round T1 fixes

2026-09-23. Starting head: `bfae75726929e0302189e02925144bb95bf8a2df`.
Independent input: `docs/reviews/row_9_review_S1.md`, kept untracked and unchanged.
Earlier report bytes are preserved. No model, network, seal, measured run, ledger
entry, approval, merge, remote, push or pull request is supplied by this round.

The lane, under the owner's delegation, renumbered this row's record to
`docs/decisions/0071-row-9-review-fault-harness-code-half.md` with a path-limited
Git move and a dated addendum. Public main's row-12 approval owns 0070. All 18,112
pre-T1 record bytes remain its exact prefix. Old self-references to 0070 mean
0071; old reservations of 0071–0074 mean 0072–0074. Live references use code-half
0071, protected approval 0072, seal 0073 and first run 0074. The latter three are
unwritten. The decision index was regenerated by its script.

| Finding / requirement | Changed files | Test | Result; red-on-fault seen |
|---|---|---|---|
| F1 BLOCKER: P07 match was 57 instead of 73 | `evals/review-faults/fixtures/plants/P07/expected.json`; build and fault tests | `BuildTests.test_plant_match_intervals_cover_changed_lines` | PASS for every file-lines plant; yes, shifting P07 back to 57 fails with `answer match misses changed lines: P07`. |
| F2 MAJOR: blindness spelling gaps | `evals/review-faults/run_reviews.py`; launch and fault tests | `LaunchTests.test_blindness_every_spelling`; `test_blindness_stream_makes_record_invalid` | PASS; yes, individual controls omit nested shell, nested interpreter, brace home, variable parent, attached option and bare-directory-change scanning. Original decoded shell tokens and malformed-string refusal remain covered. |
| F3 MAJOR: unrelated red controls | `tests/test_review_faults_faults.py` | `FaultTests.test_every_guard_fault_is_red` | PASS; every named test first passes in the same disposable source copy. Scratch is a sibling outside its symlinked work tree. Yes: all 78 faults then fail, with two unchanged-line exemption controls remaining green. The five reported controls have explicit expected diagnostics; unexpected test errors are refused. |
| F4 MINOR: existing ancestors rejected | `evals/review-faults/run_reviews.py`; harness README; launch and fault tests | `LaunchTests.test_environment_and_neutral_parent_guard`; `test_envelope_and_command_are_code_owned` | PASS under an ancestor containing review; yes, removing the created-directory guard fails its explicit negative control. Only the created kit directories are constrained. |
| F5 MINOR: skip claims removed | `README.md`; `DEVELOPMENT.md` | Full suite modes B/C; `tests/check_counts.py` | PASS; 428 tests and explicit observed platform/skip counts. No prose mutation; current-main fresh-clone CI remains a merge-result check. README evidence row unchanged. |
| F6 MINOR: free sealed ids unspecified | `evals/review-faults/INTERFACE.md` | Read the standalone interface | PASS: P08, P09 and P10 are mandatory, one each, before sealing. No red-on-fault for prose; producer class assignments are not listed. |
| F7 NOTE: deployment commit identity | T1 report and 0071 addendum only | S1 finding states no required row fix | No configuration or identity change; this is a deployment policy observation, not a producer-selected identity. No red-on-fault. |
| F8 NOTE: coincident uid numbers masked in prose | `evals/review-faults/score.py` docstring; harness README; 0071 addendum | `ScoreTests.test_published_copy_masks_and_keeps_fields` | PASS; effect explicitly pre-registered: word-bounded prose numbers equal to uids are masked too; private originals govern scoring. Existing raw-uid and literal masking controls remain red. |
| F9 NOTE: wide finding interval | Core test; harness README; 0071 addendum | `ScoreTests.test_published_copy_masks_and_keeps_fields` | PASS: a span from 1 to 100000 stays visible in the published finding. The specified overlap oracle is unchanged. No new span-cap guard or mutation. |
| F10 NOTE: sealed additions not swept at build | `evals/review-faults/case_sweep.py`; builder; test support; build/fault tests; harness README | `BuildTests.test_external_case_leak_refused`; all item-15 surface controls | PASS; the unchanged sweep implementation is shared with production and runs over all inputs before writing key/manifest. Yes, disabling the refusal admits a leaked external case id and fails the test. Only a disposable copy of a public producer fixture is used. |
| Item 16: renumber without rewriting history | 0071, index, interface, seals, harness README, README, DEVELOPMENT, this new section | Prefix and boundary checks; index rebuild | PASS; all original decision/report bytes preserved, reserved records absent. No record mutation. |
| Item 17: bounded determinism | `tests/test_review_faults_build.py` | `BuildTests.test_determinism_history_and_private_key`; disposable memory runs | PASS; sorted file paths and streamed SHA-256 values, plus Git object ids. Yes, nondeterministic salt reports the first differing path and hashes, never file bytes. |

The earlier round reports' red-on-fault claims for the five F3 controls are
superseded: those observations failed on work-tree placement, not their named
guards. T1's passing baselines and checked fault diagnostics supply the missing
evidence. Three deliberate mutations are expected to produce specific errors:
collision materializes a duplicate folder, altered settings trigger the exact
settings-copy refusal, and selecting an invalid review reaches the oracle with
missing findings. Other controls must fail by assertion, not by a test error.

### Memory evidence

`resource.getrusage` measured disposable test runs. Before edits, the original
passing test peaked at **342,068 KiB** on this host. The review reports about
**14 GiB** for the old mismatch/diagnostic path on its host; that unsafe allocation
was not repeated here. Immediately after replacing the whole-tree comparison,
the passing test peaked at **278,812 KiB**. With F10's additional production audit
included, final isolated runs peaked at **649,552 KiB** (passing) and **649,736 KiB**
(deliberate nondeterminism, correctly red). Both final disposable runs had a
900 MiB address-space ceiling and completed. The diagnostic contains only paths
and digests. The shared sweep adds memory to construction, but every observed
row-suite process stays below approximately 1 GiB.

### Verification summaries

Commands ran from the repository root; all logs, temporary trees and mutation
copies stayed in the scratch twin. Mode B set TMPDIR, TEMP and TMP there. Mode C
unset TMPDIR and retained TEMP/TMP. The empty pipeline directory and absent row-5
scratch preserve the prior cold-clone setup. Environment skips are not passes.
An initial artificial address-space cap caused three extra shallow-clone skips
in the legacy evaluation harness; rerunning without that cap restored all 44
passes. The final summaries below are authoritative.

`python3 tests/run_tests.py (mode B)`:

```text
collected 254 tests from tests
collected 174 tests from gars/tests
Ran 428 tests in 287.334s
OK (skipped=59)
```

`python3 tests/run_tests.py (mode C)`:

```text
collected 254 tests from tests
collected 174 tests from gars/tests
Ran 428 tests in 282.081s
OK (skipped=86)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 254 tests from tests
collected 174 tests from gars/tests
suite: 428 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 44.350s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 scripts/release_check.py`:

```text
DoD cells regenerated: 13/13
```

`python3 tests/test_review_faults_build.py`:

```text
Ran 11 tests in 89.920s
OK
added case-byte sweep: 12/12 clear; item 15 added lines and decoded objects
fixtures: git apply --check passed for 12/12 against base archive
plant match intervals: every file_lines answer overlaps changed lines
```

`python3 tests/test_review_faults_core.py`:

```text
Ran 8 tests in 0.070s
OK
```

`python3 tests/test_review_faults_launch.py`:

```text
Ran 11 tests in 0.908s
OK
```

`python3 tests/test_review_faults_faults.py`:

```text
Ran 1 test in 136.782s
OK
```

`feature_version=(3, 6) parse of all twelve new Python files`:

```text
Python feature_version=(3, 6): 12/12 new Python files parsed
```

`python3 gars/_system/hooks/pre-commit (24 fixtures staged in a disposable base tree)`:

```text
fixture hook index: 24 fixture files staged against base
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 292/292 resolve
pre-commit: REFUSED
```

Final full-suite process peaks from `resource.getrusage(RUSAGE_CHILDREN)`:
mode B **666,188 KiB**, mode C **665,848 KiB**; direct fault module **650,452 KiB**.

`bash docs/decisions/build_index.sh` regenerated the index. The release script
regenerated `docs/implementation/dod_current.md`, byte-identically. Its reviewer
row remains:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

The fixture hook ran in a disposable archive of the pinned base, with exactly
24 fixture files staged and no other staged paths. Its unchanged real scanner
refused because gitleaks is absent. Neither ruleset was substituted or bypassed;
Q2 A leaves this check NOT met pending the lane's independent verification.

Boundary and prefix checks passed: no changes to CI, system code, pinned evals,
benchmarks, the ledger, other references, or any base decision record. This round
changes only P07's two answer-line integers in the protected fixtures; the prompt
is unchanged. The seven plants, five clean cases and three empty sealed slots
remain intact. The reviewer input stays untracked and is excluded from staging.
No run JSON was created in the repository. Staging is path-limited, and the commit
message comes from scratch. No hook or Git configuration changed.

## Owner rulings needed

None for the T1 fixes. F7 requires no action in this row; any later deployment
identity policy remains separate. Reserved protected approval 0072, seal 0073 and
first measured run 0074 are later records, not approvals claimed by the producer.

## Residual gaps after T1

- **Row 9 exit NOT met:** the three sealed slots, seal/ledger records and first
  real measured run remain the owner's later work. No first-run measurement is
  claimed and no model has reviewed any case.
- Real fixture secret scanning remains NOT met; both gitleaks rulesets need the
  independent verification already selected by Q2 A.
- R-093 code half remains NOT met: `launch_role()` is still producer. Deployment
  evidence for two unprivileged OS users and read-only credentials is external.
  The uid check proves only that reviewing and producing accounts differ on the
  review host, not which machine constructed the cases.
- Diff-style inference, shared producer/sealer model family, a one-plant-per-class
  sample, and hash-only public checking of three private outcomes remain limits.
  A stranger can recompute twelve of fifteen outcomes from public inputs.
- Independent-context seals are development evidence only; public credibility
  requires external-human seals. Science and trailer-gate JSON consumption remain
  later rows. Publication conservatively masks uid-coincident prose numbers and
  exposes wide finding spans without changing the specified overlap threshold.
- Docker mode A is unverified because this account cannot reach Docker. Native
  Python 3.6 execution, protected approval, the next independent review and all
  merge-result CI (including current main's fresh-clone job) remain unverified.

F1–F6, F8–F10 and items 16–17 are closed by these fixes and checks; F7 is answered
with no producer action required. No finding waits on a new owner ruling; the
secret scan, protected approval, sealing, measured run and row exit remain later.

## Renumbering round U1

2026-09-23. Starting head, recorded before reads or edits:
`bfc2573d83cf8c99471fc06576da6012679010eb`.
This round implements only item 18 (RENUMBERING, SECOND); it answers no review
and does not reopen T1's fixes. The supplied review file remains untracked and
unchanged. No model, network, seal, measured run, ledger entry, approval, merge,
remote, push or pull request is supplied.

THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION.
Item 18 supersedes item 16's numbering because public main has since also landed
its own 0071, row 12's owner record. This row's account is now
`docs/decisions/0072-row-9-review-fault-harness-code-half.md`. Earlier report
sections and the record's earlier bytes retain their historical wording:
self-references to 0070 or 0071 mean 0072; any reserved number means 0073 for the
owner's approval of the protected changes or 0074 for ONE record covering both
the seal and the first measured run. Public main's 0070 and 0071 are untouched.
Reserved 0073 and 0074 remain unwritten. No further delegated choice is made.

| Item 18 | Changed files | Test | Result; red-on-fault seen |
|---|---|---|---|
| Path-limited rename preserving both earlier forms | `docs/decisions/0072-row-9-review-fault-harness-code-half.md` | `git show` of 0070 at bfae757 and 0071 at bfc2573 into scratch; `cmp -n` over each original length | PASS: 18,112 and 20,792 bytes respectively are exact prefixes. Git records a rename. Red-on-fault: no; direct byte comparisons, no historical record mutation. |
| Dated addendum after the last original byte | 0072 addendum | Prefix checks and assertion of the date, lane label, reason and complete mapping | PASS: item 18 supersedes item 16; the addendum is the lane's specification, not additional owner words. Red-on-fault: no; prose verification. |
| Standalone sealer reference | `evals/review-faults/INTERFACE.md` | Number grep and exact mapping assertions | PASS: 0072 account, 0073 approval and one 0074 seal/first-run record. Red-on-fault: no; prose verification. |
| Empty seal-slot reference | `evals/review-faults/SEALS.md` | Number grep and exact mapping assertions | PASS: same mapping; all slots remain empty. Red-on-fault: no; prose verification. |
| README references | `README.md`; `evals/review-faults/README.md` | Number grep; decision-link checks in full suite | PASS: both point to 0072; public evidence row unchanged. Red-on-fault: no new prose mutation. |
| Development reference | `DEVELOPMENT.md` | Number grep and exact mapping assertion | PASS: 0072 account, 0073 approval, one 0074 covering seal and first measured run. Red-on-fault: no; prose verification. |
| Historical report mapping | This appended section only | Starting-report `cmp -n` prefix check | PASS: every earlier byte retained; historical numbers mapped here. Red-on-fault: no; direct byte comparison. |
| Regenerated decision index | `docs/decisions/CONTEXT.md` | `bash docs/decisions/build_index.sh`; assert 0072 present and 0071 absent | PASS: generated by the script. Red-on-fault: no; output verification. |
| No other numbered record or stale live reference | No further files | Absence check for 0070, 0071, 0073, 0074; decision-scope diff against e59dfc0; number grep | PASS: only 0072 and CONTEXT.md differ under decisions. Historical record/report sections are mapped, never rewritten. Red-on-fault: no; direct scope checks. |

No check required a further repository change. Number searches found no record
number pinned in the code, schema, prompt or tests, so those files are unchanged.
Unrelated numeric matches in frozen data and study material are not live record
references; the numeric fraction in `docs/RESULTS.md` is unchanged. All prior
guards, thresholds and red-on-fault controls remain intact. Existing count claims
remain 428 and the observed mode-B/mode-C skip counts remain 59/86.

### Required command summaries

All commands ran from the repository root. Logs, scratch scripts and disposable
copies stayed in the scratch twin. Mode B sets TMPDIR, TEMP and TMP there; mode C
unsets TMPDIR while keeping TEMP and TMP there. The same empty pipeline directory
and absent row-5 scratch preserve T1's cold-clone setup. Checks ran one at a time.
No credentials or environment values were inspected. The unchanged fixture hook
runs against exactly 24 staged fixture files in a disposable base-tree repository.

`python3 tests/run_tests.py (mode B)`:

```text
collected 254 tests from tests
collected 174 tests from gars/tests
added case-byte sweep: 12/12 clear; item 15 added lines and decoded objects
fixtures: git apply --check passed for 12/12 against base archive
plant match intervals: every file_lines answer overlaps changed lines
Ran 428 tests in 265.718s
OK (skipped=59)
```

`python3 tests/run_tests.py (mode C)`:

```text
collected 254 tests from tests
collected 174 tests from gars/tests
added case-byte sweep: 12/12 clear; item 15 added lines and decoded objects
fixtures: git apply --check passed for 12/12 against base archive
plant match intervals: every file_lines answer overlaps changed lines
Ran 428 tests in 261.147s
OK (skipped=86)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 254 tests from tests
collected 174 tests from gars/tests
suite: 428 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 37.680s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 scripts/release_check.py`:

```text
DoD cells regenerated: 13/13
```

`python3 tests/test_review_faults_build.py`:

```text
Ran 11 tests in 82.934s
OK
added case-byte sweep: 12/12 clear; item 15 added lines and decoded objects
fixtures: git apply --check passed for 12/12 against base archive
plant match intervals: every file_lines answer overlaps changed lines
```

`python3 tests/test_review_faults_core.py`:

```text
Ran 8 tests in 0.018s
OK
```

`python3 tests/test_review_faults_launch.py`:

```text
Ran 11 tests in 0.826s
OK
```

`python3 tests/test_review_faults_faults.py`:

```text
Ran 1 test in 122.845s
OK
```

`feature_version=(3, 6) parse of every row Python file`:

```text
Python feature_version=(3, 6): 12/12 new Python files parsed
```

`python3 gars/_system/hooks/pre-commit (24 fixture files staged in a disposable base tree)`:

```text
fixture hook index: 24 fixture files staged against base
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 292/292 resolve
pre-commit: REFUSED
```

The unchanged direct fault module observed 78 red fault witnesses and two
green unchanged-line exemption witnesses. No guard or assertion was weakened.

The regenerated reviewer row remains, verbatim:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

The release render is byte-identical to its starting version. The decision
index was regenerated with `bash docs/decisions/build_index.sh`; its output
names the index with a machine-specific prefix, retained only in scratch.

### Renumbering and boundary checks

```text
byte prefix 0070: PASS (18112 bytes; cmp -n)
byte prefix 0071: PASS (20792 bytes; cmp -n)
earlier change report bytes: PASS (cmp -n)
other decision numbers: PASS (0070, 0071, 0073, 0074 absent)
decision index: PASS (0072 present; 0071 absent)
live references: PASS (0072 account; 0073 approval; 0074 seal and first run)
item 18 addendum: PASS (dated lane specification; full mapping)
review file: PASS (untracked and unchanged)
decision scope: PASS (only 0072 and CONTEXT.md against e59dfc0)
```

Both earlier decision forms were written from their named Git objects into
scratch and compared with `cmp -n` over their exact byte lengths. These checks
are repeated against the committed 0072 blob after the one U1 commit. The
committed decision diff against e59dfc0 must name only 0072 and CONTEXT.md.
Number grep leaves only mapped historical references; no code or test references
needed moving. The reviewer input is still untracked and its hash is unchanged.

U1 changes only the five live-reference files, the renamed record with its
append-only addendum, the regenerated index and this appended report section.
No protected fixture or prompt changes were needed. Existing decision records,
pinned evals, CI, system code, benchmarks and ledger bytes are unchanged.

## Owner rulings needed

None. Item 18 fully specifies this renumbering; no schema, threshold, scope,
CI or other decision was needed. Reserved 0073 and 0074 are not written here.

## Residual gaps after U1

- **Fixture pre-commit check NOT met on this host:** gitleaks remains unavailable;
  the actual hook refused. Both rulesets await the independent verification in
  Q2 A. No scanner substitution, installation or bypass was used.
- **Row 9 exit NOT met:** the three sealed slots, later ledger rows and first
  measured run remain the owner's later work. No model ran against any case.
- Protected-change approval remains the owner's 0073; one later 0074 covers
  both the seal and first measured run. Merge-result CI remains unverified.
- R-093's code half remains NOT met: `launch_role()` still returns producer.
  Two-user and read-only-credential deployment evidence remains external; the
  uid check proves account inequality on the review host only.
- Independent-context seals are development evidence only; public credibility
  needs external-human seals. Science and trailer-gate JSON consumption remain
  later rows. Diff-style inference, a shared model family, thin per-class samples
  and hash-only public checking of three sealed outcomes remain limitations.
- Docker mode A is unverified because this account cannot reach Docker. Native
  Python 3.6 execution and an expanded-suite cluster run are not verified; syntax
  parsing alone does not establish runtime compatibility. Test skips remain skips.

Item 18's second renumbering, preserved history, live mappings and regenerated
index are carried out; protected approval, secret verification, sealing, the
first measured run and the row exit wait on the owner and independent verification.

## Review round V1 fixes

Date: 2026-09-23. Starting head:
`c7aa6f2f152b42d2620e173d272b5291d819a338`.
Review input: `docs/reviews/row_9_review_U1.md`, left untracked and unchanged.
This round addresses U1 F1–F3 and, separately, head item 19. Earlier report
sections and every existing byte of record 0072 are preserved. No model ran
against any case. The reviewer prompt, fixtures and answer keys are unchanged.

| Finding | Changed files | Test | Result; red-on-fault seen |
|---|---|---|---|
| U1 F1, MAJOR: ordinary commands and review prose became blindness hits | `evals/review-faults/run_reviews.py`; `tests/test_review_faults_launch.py`; `tests/test_review_faults_faults.py` | `LaunchTests.test_blindness_every_spelling`; `FaultTests.test_every_guard_fault_is_red` | PASS; yes — restoring the eager option cut or treating lone separators as paths turns the named test red. Test-directory and Git-directory relative options, awk/cut delimiters, integer division and review JSON prose remain clear. Rooted options and attached parent/home paths remain hits; removing the latter parsing also turns the test red. |
| U1 F2, MINOR: shell boundaries and modified variables escaped scanning | Same launcher and two test modules | `LaunchTests.test_blindness_every_spelling`; `FaultTests.test_every_guard_fault_is_red` | PASS; yes — separately suppressing newline, subshell, brace group, then, do, else, builtin, command, HOME-modifier and PWD-modifier detection turns the named test red. Exact PWD resolves to the kit; unresolved modifiers fail closed. |
| U1 F3, MINOR: sealer unaware of substring rejection | `evals/review-faults/INTERFACE.md`; `evals/review-faults/build_cases.py`; `tests/test_review_faults_build.py`; `tests/test_review_faults_faults.py` | `BuildTests.test_external_case_leak_refused`; `FaultTests.test_every_guard_fault_is_red`; interface inspection | PASS; yes — disabling the build refusal or dropping absent reserved ids turns the named test red. A disposable public-fixture copy refuses a commit message containing its id, race inside traceback, or an absent reserved id. The interface lists all forbidden ids, case-sensitive substrings and sweep surfaces, with a coordinator-run pre-seal command using the same builder. No sealer reads producer implementation or inputs. |
| Item 19 (not a review finding): this session's saved-output store | `evals/review-faults/run_reviews.py`; `evals/review-faults/README.md`; `tests/test_review_faults_launch.py`; `tests/test_review_faults_faults.py`; 0072 addendum | `LaunchTests.test_session_output_store_boundary`; `test_envelope_and_command_are_code_owned`; `FaultTests.test_every_guard_fault_is_red` | PASS; yes — widening the allowance to the projects folder, denying own output, changing kit-name encoding, or omitting the launch session id makes the named test red. Own-session output is clear; the transcript, memory, another session, another kit and escaping symlinks or parent steps are hits. A character-by-character oracle verifies encoding of a runtime kit path with punctuation and spaces. |
| Records and counts | README; DEVELOPMENT; append-only 0072 and this report; regenerated index | Required runner/count check; starting-head prefix and scope checks | PASS; red-on-fault: no separate prose mutation. Current suite count is 429; skip claims remain 59 and 86. Index regenerated without changing its bytes; release output remains unmeasured. |

THE LANE, UNDER THE OWNER'S DELEGATION: the dated 0072 addendum labels item
19 as the lane's specification. Its allowance uses the reviewer's home and the
tool's projects folder, encoded kit path, launcher-supplied session id and
`tool-results`, never a model-supplied location. No new statement is attributed
to the owner. Reserved 0073 (protected approval) and 0074 (seal and first run)
remain unwritten.

### Required command summaries

Commands ran from the repository root with all scratch and temporary data in
the approved scratch twin. Mode C unsets TMPDIR and retains TEMP/TMP there.
No network or model was used. Checks below report their final summaries verbatim;
the direct fault run requires each unchanged control to pass before the changed
copy fails for its expected reason. Initial verification logs remain in scratch.

`python3 tests/run_tests.py (mode B)`:

```text
collected 255 tests from tests
collected 174 tests from gars/tests
Ran 429 tests in 334.317s
OK (skipped=59)
```

`python3 tests/run_tests.py (mode C)`:

```text
collected 255 tests from tests
collected 174 tests from gars/tests
Ran 429 tests in 311.648s
OK (skipped=86)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 255 tests from tests
collected 174 tests from gars/tests
suite: 429 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 37.621s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 scripts/release_check.py`:

```text
DoD cells regenerated: 13/13
```

`python3 tests/test_review_faults_build.py`:

```text
Ran 11 tests in 90.936s
OK
added case-byte sweep: 12/12 clear; item 15 added lines and decoded objects
fixtures: git apply --check passed for 12/12 against base archive
plant match intervals: every file_lines answer overlaps changed lines
```

`python3 tests/test_review_faults_core.py`:

```text
Ran 8 tests in 0.018s
OK
```

`python3 tests/test_review_faults_launch.py`:

```text
Ran 12 tests in 0.845s
OK
```

`python3 tests/test_review_faults_faults.py`:

```text
Ran 1 test in 174.488s
OK
```

`feature_version=(3, 6) parse of every row Python file`:

```text
Python feature_version=(3, 6): 12/12 new Python files parsed
```

`python3 gars/_system/hooks/pre-commit (24 fixture files staged in a disposable base tree)`:

```text
fixture hook index: 24 fixture files staged against base
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 292/292 resolve
pre-commit: REFUSED
```

The final direct fault module observed 96 red fault witnesses and two green
unchanged-line exemption witnesses. No threshold, assertion or guard was weakened.

The regenerated reviewer row remains, verbatim:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

The index was regenerated with `bash docs/decisions/build_index.sh`; its output
contains a machine-specific prefix retained only in scratch. Both the index and
the release render are byte-identical to their starting versions. The README
evidence row is unchanged.

### Temp setup and memory

Two initial mode-B invocations inherited a relative TMPDIR. Lifecycle controls
change their child working directories, making that value invalid. Their setup
errors were not product regressions, and no out-of-scope code was changed:

```text
Ran 429 tests in 319.145s
FAILED (failures=15, skipped=59)
```

```text
Ran 429 tests in 316.357s
FAILED (failures=15, skipped=59)
```

The initial mode-C invocation passed:

```text
Ran 429 tests in 324.644s
OK (skipped=86)
```

Final verification resolves the approved scratch location at runtime before
launching children; mode C then removes TMPDIR and keeps TEMP/TMP there.
Both final full-suite summaries above are green. Earlier exploratory and setup
logs stay in scratch; none is represented as a clean mode-B run.

The pre-T1 implementation's reported peak was about 14 GiB on the review host;
that unbounded implementation was not rerun. T1 had already replaced whole-tree
byte dictionaries with streamed digests. V1 preserves that implementation and
its red-on-fault. A fresh disposable determinism-only process measured with
`resource.getrusage(resource.RUSAGE_CHILDREN)` reports:

```text
Ran 1 test in 6.123s
OK
determinism peak memory: 648652 KiB
```

The final verification driver's cumulative child peak was 667140 KiB, below
1 GiB across its full-suite and direct-module checks. The stream compares
per-file digests and Git object ids; mismatch diagnostics never contain tree bytes.

### Boundary and append-only verification

Starting-head prefix checks preserve every earlier byte of 0072 and this report.
The U1 review stays untracked and byte-identical; no review is staged. The diff
against the public base touches no prohibited tree, ledger or other decision
record. This round changes neither fixture nor reviewer-prompt bytes. The record
index was regenerated, reserved 0073 and 0074 remain absent, and no measured-run
file exists. No remote, push, merge or pull request was used. `git diff --check`
is clean. Only explicitly named files are staged for the single V1 commit.

## Owner rulings needed

None. U1 F1–F3 and item 19 fit the supplied scope and delegation; no schema,
threshold, protected-tree or CI decision was needed. Q2 A's existing independent
secret-verification requirement remains open and does not need a new ruling.

## Residual gaps after V1

- **Fixture pre-commit check NOT met on this host:** the actual hook refused
  because gitleaks is unavailable. Both rulesets await the lane's independent
  verification. No installation, substitute scan or bypass was used.
- **Row 9 exit NOT met:** the three sealed slots, first measured run, later
  ledger rows and combined seal/run record 0074 remain later work. No model ran
  against any case, and no catch rate or first-run result is claimed.
- Protected-change approval remains the owner's reserved 0073. Live separate-user
  and read-only-credential deployment evidence is external. The uid check proves
  account inequality on the review host only; `launch_role()` still returns
  producer, so R-093's code half remains NOT met.
- Public credibility remains unmeasured until external-human seals. Independent
  context seals are development evidence only. Science and trailer-gate JSON
  consumption remain later rows. Diff-style inference, a shared model family,
  thin per-class samples and hash-only checking of three sealed outcomes remain.
- Docker mode A is not verified: this account cannot reach Docker. Native Python
  3.6 execution, expanded-suite cluster execution and merge-result CI are not
  verified. Existing test skips remain skips. The blindness scan is a static
  post-run audit, not a complete shell interpreter or operating-system sandbox.

Closed: U1 F1, F2 and F3; item 19 implemented and tested separately. No review
finding awaits an owner ruling. Protected approval, secret verification, sealing,
the first measured run and the row exit remain with the owner and independent
verification.


## Review round W2 fixes

Date: 2026-09-23. Starting head: `fcb41db099dbc9dfa739ea901aced5a5887056f7`.
Independent review: `docs/reviews/row_9_review_W1.md`, unchanged and untracked.
Every earlier byte of this report and decision 0072 is preserved. This round
fixes W1 F1 and F2 without changing the prompt, fixtures, schema, thresholds or
protected trees. No model ran against any case; row 9 exit remains NOT met.

| Finding | Changed files | Test | Result; red-on-fault seen |
|---|---|---|---|
| W1 F1 BLOCKER: separator-only root access was exempt | `evals/review-faults/run_reviews.py`; `tests/test_review_faults_launch.py`; `tests/test_review_faults_faults.py` | `LaunchTests.test_blindness_every_spelling`; `test_blindness_stream_makes_record_invalid`; `FaultTests.test_every_guard_fault_is_red` | PASS; yes — restoring the blanket exemption makes the named test red. Root directory changes followed by relative reads, listing, search, quoted/repeated roots, path fields and root-valued options are hits. Stub records become INVALID. |
| W1 F1 exemption boundary | Same three files; `evals/review-faults/README.md` | Same spelling and fault tests | PASS; yes — broadening delimiter allowance to other commands, omitting nested-shell roots, exempting path fields, or treating script-file paths as program text each fails the named test. Existing delimiter, division, relative-option and JSON-prose controls remain clear. Delimiter commands in tests now run as complete synthetic command inputs instead of arguments appended to cat; all expected hits and assertions remain. |
| W1 F2 MINOR: option-only and prefixed home changes escaped | Same launcher and two test modules; harness README | Same spelling, stub-record and fault tests | PASS; yes — dropping option-only argument detection or separately suppressing eval, exec or time detection turns the named test red. The flags --, -L and -P, including combinations, are covered. Explicit in-kit directory arguments remain clear. |
| Records and current status | Append-only 0072 and this report; `DEVELOPMENT.md`; regenerated decision index | Prefix/scope checks; required runner and count check | PASS; red-on-fault: no separate prose mutation. All three count claims already match 429 tests, so no count edit or README evidence-row edit is needed. Index and release render are byte-identical after regeneration. |

THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION:
separator-only text is classified by field and shell-word context. File-content
fields and interpreter program text are distinct from path arguments; the
existing scan still checks named absolute, home and parent spellings everywhere.
The root-only detector recognizes awk/cut delimiter options only for those
commands. In particular, a listing command's directory option does not make the
root a delimiter, and awk/sed script-file options do not hide root paths or later
input files. The directory-change regex retains its existing boundaries and adds
only the requested option words and prefixes. Item 19 and the uid check remain
unchanged. These are static post-run checks, not a complete shell interpreter or
OS sandbox. No new words are attributed to the owner.

### Required command summaries

All commands ran from the repository root, with scratch, logs and temporary
copies in the approved scratch twin. Mode B resolves TMPDIR/TEMP/TMP there;
mode C unsets TMPDIR and retains TEMP/TMP. Checks use the established empty
pipeline directory and absent row-5 scratch for cold-clone execution. There is
no network, model run, credential inspection, configuration change or hook bypass.

`python3 tests/run_tests.py (mode B, final)`:

```text
collected 255 tests from tests
collected 174 tests from gars/tests
citations: 292/292 resolve
DoD cells regenerated: 13/13
DoD cells regenerated: 13/13
DoD cells verified: 13/13 byte-stable
DoD cells regenerated: 13/13
DoD cells verified: 13/13 byte-stable
DoD cells regenerated: 13/13
DoD cells verified: 1/1 byte-stable
added case-byte sweep: 12/12 clear; item 15 added lines and decoded objects
fixtures: git apply --check passed for 12/12 against base archive
plant match intervals: every file_lines answer overlaps changed lines
Ran 429 tests in 322.954s
OK (skipped=59)
```

`python3 tests/run_tests.py (mode C)`:

```text
collected 255 tests from tests
collected 174 tests from gars/tests
citations: 292/292 resolve
DoD cells regenerated: 13/13
DoD cells regenerated: 13/13
DoD cells verified: 13/13 byte-stable
DoD cells regenerated: 13/13
DoD cells verified: 13/13 byte-stable
DoD cells regenerated: 13/13
DoD cells verified: 1/1 byte-stable
added case-byte sweep: 12/12 clear; item 15 added lines and decoded objects
fixtures: git apply --check passed for 12/12 against base archive
plant match intervals: every file_lines answer overlaps changed lines
Ran 429 tests in 313.846s
OK (skipped=86)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 255 tests from tests
collected 174 tests from gars/tests
suite: 429 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 37.710s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 scripts/release_check.py`:

```text
DoD cells regenerated: 13/13
```

`python3 tests/test_review_faults_build.py`:

```text
Ran 11 tests in 90.790s
OK
added case-byte sweep: 12/12 clear; item 15 added lines and decoded objects
fixtures: git apply --check passed for 12/12 against base archive
plant match intervals: every file_lines answer overlaps changed lines
```

`python3 tests/test_review_faults_core.py`:

```text
Ran 8 tests in 0.018s
OK
```

`python3 tests/test_review_faults_launch.py`:

```text
Ran 12 tests in 1.196s
OK
```

`python3 tests/test_review_faults_faults.py`:

```text
Ran 1 test in 167.489s
OK
```

`feature_version=(3, 6) parse of every row Python file`:

```text
Python feature_version=(3, 6): 12/12 new Python files parsed
```

`python3 gars/_system/hooks/pre-commit (24 fixture files staged in a disposable base tree)`:

```text
fixture hook index: 24 fixture files staged against base
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 292/292 resolve
pre-commit: REFUSED
```

The final direct mutation module observed **105 red fault witnesses** and **2 green unchanged-line exemption witnesses**. Each mutation first passes its unchanged control. No guard, assertion or threshold was weakened.

The regenerated reviewer row remains, verbatim:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

The actual fixture hook refuses because gitleaks is absent. This check stays
NOT met under Q2 A; both real rulesets await independent verification. The index
was regenerated with `bash docs/decisions/build_index.sh`; its machine-specific
output remains in scratch. No measured-run file exists.

### Verification timing and memory

The initial mode-B suite had already started when inspection identified the
awk/sed script-file edge case. The final mode-B run above was repeated after
that last code change; mode C and every final direct module started afterwards.
The initial run is retained for transparency and is not the final acceptance:

```text
Ran 429 tests in 318.748s
OK (skipped=59)
```

The pre-T1 implementation was reported at about 14 GiB on the review host;
that unsafe whole-tree comparison was not rerun. W2 preserves streamed per-file
digests and bounded mismatch diagnostics. A fresh disposable determinism-only
process measured with `resource.getrusage(resource.RUSAGE_CHILDREN)` reports:

```text
Ran 1 test in 6.002s
OK
determinism peak memory: 649276 KiB
```

The maximum recorded child peak across the verification drivers was 667924 KiB, below 1 GiB.

### Boundary and append-only checks

Starting-head prefix comparisons preserve all preceding decision and report
bytes. W1 stays untracked and byte-identical; no review is staged. The diff from
the public base touches no prohibited tree, ledger or other decision record.
This round changes neither protected prompt nor fixture bytes. Reserved 0073
(protected approval) and 0074 (seal and first run) remain absent. The README
evidence row is unchanged; the release render and decision index were regenerated.
`git diff --check` is clean. The single W2 commit uses an explicit path list and
a message file in scratch. No remote, push, merge or pull request was used.

## Owner rulings needed

None. W1 F1 and F2 fit the supplied scope. No schema, threshold, scope, CI or
protected-path decision is needed. Q2 A's independent secret verification remains
open under its existing ruling.

## Residual gaps after W2

- Fixture pre-commit secret verification remains NOT met: both gitleaks rulesets
  await independent verification; no replacement scan or bypass was used.
- Row 9 exit remains NOT met: three sealed slots, one real first measured run,
  later ledger rows and reserved combined record 0074 remain later work. No
  model was run, and no catch rate or first-run result is claimed.
- Protected approval remains the owner's reserved 0073. Separate-user and
  read-only-credential deployment evidence is external. The uid check proves
  account inequality on the review host only; R-093's code half stays NOT met
  because GARS launch_role() still returns producer.
- Public credibility stays unmeasured until external-human seals; independent
  context seals are development evidence only. Science and trailer-gate JSON
  consumption remain later rows. Diff-style inference, a shared model family,
  thin per-class samples and hash-only checking of three private outcomes remain.
- Docker mode A is not verified because this account cannot reach Docker.
  Native Python 3.6, expanded-suite cluster execution and merge-result CI are
  unverified. Existing skips remain skips. Long project-name truncation/hashing
  by the deployed reviewer tool remains unverified, as W1 disclosed; item 19's
  supplied encoding is unchanged. The blindness audit is static, not a sandbox.

Closed: W1 F1 and F2. No review finding waits on a new owner ruling. Secret
verification, protected approval, sealing, the measured run and row exit remain
with the owner and independent verification.
