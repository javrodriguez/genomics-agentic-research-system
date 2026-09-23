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
