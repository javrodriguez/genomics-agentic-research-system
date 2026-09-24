# Row 9 cd-aware placement — round 1

Base: `5ba82c625cec42277e463c5b4077a7dc0245389b`.
Branch: `build/gars-row-09-cd-placement`. No round-1 review was supplied.
This is the lane's implementation under the delegation quoted in 0072 and
0125, not a new row or an owner-authored specification. No model was run and
this follow-up measures nothing. No catch rate or first measured run is claimed.

## Requirement to acceptance

In this table, `runner` means `evals/review-faults/run_reviews.py`, `cd tests`
means `tests/test_review_faults_cd.py`, and `cd faults` means
`tests/test_review_faults_cd_faults.py`. The next section lists each mutation
and its named red witness. All new paths are assembled at runtime; no test
executes the shell snippets it scores.

| Requirement | Changed files | Acceptance | Result and red-on-fault evidence |
|---|---|---|---|
| 1(a): only a top-level unprefixed simple cd, with qualifying separators | runner, cd tests, cd faults | `test_top_level_required`, `test_invalid_shape_and_prefixes`, `test_merged_separators` | PASS; yes, dropping the top-level condition makes subshell, group, pipeline, OR, background, keyword, nested-shell and substitution witnesses red |
| 1(b): one argument, no option, redirect or second argument | runner, cd tests | `test_invalid_shape_and_prefixes` | PASS; all prohibited shapes still hit; the top-level mutation also exercises the boundary proof |
| 1(c): statically resolvable nonempty argument | runner, cd tests, cd faults | `test_variable_target_reset`, `test_unresolvable_targets_reset` | PASS; yes, literal treatment of a variable target turns the named test red; substitutions, backquotes, glob characters, previous-directory marker and controls are covered |
| 1(d): lexical and resolved containment; nonexistent targets allowed | runner, cd tests, cd faults | `test_symlink_target_reset`, `test_outside_targets_reset`, `test_honest_chains_and_operands` | PASS; yes, lexical-only and missing-containment faults each turn a named test red; a lexical outside target resolving into the kit is also rejected |
| 1: rejected changes reset, later accepted changes can recover; operand uses previous placement | runner, cd tests | `test_invalid_shape_and_prefixes`, `test_construct_inherits_then_cd_resets`, `test_honest_chains_and_operands` | PASS; parent changes back to the root stay clear, then a further parent change hits |
| 1: conditional AND-chain placement ends with its chain | runner, cd tests, cd faults | `test_conditional_chain_limit` | PASS; yes, removing the limit turns semicolon, newline and later-chain witnesses red; reads inside the accepted chain stay clear |
| 1(e): whole-call hazards, balanced operator parentheses, multiline backquotes | runner, cd tests, cd faults | `test_whole_call_conditions` | PASS; yes, dropping whole-call refusal turns the named test red; a preflight of recognized nested programs makes a later hazard apply to earlier words too; quoted parentheses remain data |
| 1(f): placement from raw words, retained nesting and source quoting | runner, cd tests, cd faults | `test_nested_program_not_flattened`, `test_top_level_required` | PASS; yes, recomputing from flattened words turns the nested-program test red, including program quotes spanning newlines |
| 2: parent and both PWD forms use current placement; inherited construct placement | runner, cd tests | `test_pwd_and_other_tool_fields`, `test_construct_inherits_then_cd_resets` | PASS; accepted entry placement is inherited, and internal cd resets it |
| 2: no cross-call carry; other tools retain root placement | runner, cd tests, cd faults | `test_calls_start_at_root`, `test_pwd_and_other_tool_fields` | PASS; yes, carrying state between calls turns the named test red; Read and both Glob fields still hit |
| 2: deduplicate token and folder pairs | runner, cd tests, cd faults | `test_deduplicate_by_token_and_folder` | PASS; yes, deduplicating by token alone hides the second occurrence and turns the test red |
| 2 and 5(e): every prior rule, context, bad list and fault preserved | runner, `tests/test_review_faults_faults.py`, cd tests | original corpus, original launch tests and fault list; `test_existing_spellings_after_cd` | PASS in direct checks; prior expected outcomes are unchanged; every original fault is observed red and both exemption controls green |
| 3: fail-closed root and named text-audit residuals | decision 0125, harness README, this report | documentation inspection against items 1–3 | Recorded; no mutation claimed for prose |
| 3: remove CDPATH, BASH_ENV and ENV | runner, cd tests, cd faults | `test_environment_startup_variables_removed` | PASS; yes, retaining CDPATH turns the named test red; all three variables are individually asserted absent |
| 4: supplied data and README copied unchanged with cp | both new files in `tests/data/` | `test_supplied_data_hashes`, `sha256sum` of source and destination pairs | PASS; both supplied digests match; original untracked inputs remain unchanged |
| 5(a): every rehearsal call scored; string values only replaced | cd tests | `test_honest_cd_data` | PASS, graded-against-seen 11/11; yes, old behavior fails the five named calls |
| 5(b): all listed outside, unresolved and prohibited-context directions | cd tests | outside, top-level, invalid-shape, conditional, whole-call, merged-separator and deduplication tests | PASS, each bad spelling scores at least one; mutation witnesses below |
| 5(c): honest directions and symlink refusal | cd tests | `test_honest_chains_and_operands`, `test_symlink_target_reset` | PASS; all three separators and TMPDIR, realpath and Git forms stay clear; yes, lexical-only symlink fault is red |
| 5(d): each prescribed fault planted in a disposable copy | cd faults | `CdFaultTests.test_placement_faults_are_red` | PASS; all eleven faults observed red after unfaulted controls pass; assertion failure required, import errors rejected |
| 6: amendment and index, short scan-contract paragraph, complete report | decision 0125, generated CONTEXT, harness README, this report | index regeneration and scope inspection | Implemented; 0072 and 0073 unchanged, 0074 not written |
| 6: current count claims follow the runner | count lines of README and DEVELOPMENT | both runner modes and `tests/check_counts.py` | Collection is 519; final mode summaries below |
| Boundaries: Python 3.6 grammar and stdlib, no protected-path edits | four changed/new Python files and allowed documentation/data | AST feature-version parse, both required protected diff commands | Parse 4/4; both protected diffs print nothing; no network, remote, push, merge or PR |

## Data and baseline

The two supplied untracked files were read, then copied with `cp` to the two
specified `tests/data/` destinations; their bodies were never retyped or edited.
Both copies and sources have these SHA-256 values:

- Calls: `8019297d9b0cd64e8260e2678c2991613446b6524ce4ddf1bccb9dd6188cdeb4`.
- README: `d380fdae2afa83f318a3437bf8c6c745b24b1553f8831b74f3295bbdf24172e6`.

Before any edit, `python3 tests/test_review_faults_corpus.py` printed:

```text
Ran 1 test in 0.130s
OK
honest-call corpus graded-against-seen: 278/278
```

After the change, all 277 honest calls remain zero and the contract hit remains
at least one, with the same 278/278 denominator. All eleven supplied cd calls
now score zero. The old-behavior mutation produces failures naming P1-34,
P1-40, P1-47, P1-52 and P1-63, exactly the supplied five affected calls.

## Existing expectation changes

None. No prior expected hit or expected zero was weakened, removed or relabelled.
The only maintenance in the existing fault module changes the source anchor
for the same interpreter-context mutation so it still flips the same boolean
scan flag after placement metadata is attached:

| Test and file line | Old | New | Reason |
|---|---|---|---|
| `LaunchTests.test_blindness_every_spelling`; `tests/test_review_faults_faults.py:190` | mutate `yield token, False` to True | mutate the metadata-preserving yield's False to True | Same expected red assertion; derived interpreter tokens now retain placement |

## How verification was run

Every shell command ran from the repository root; none began with a directory
change. TMPDIR, TEMP and TMP were set to the scratch twin beside the repository,
using its relative sibling path. All logs, helper scripts and disposable fault
copies stayed in that scratch twin. Mode C explicitly unset TMPDIR and kept
TEMP and TMP pointing there. All commands used `python3`, version **3.13.5**;
this also satisfies the evaluation harness's Python 3.9-or-later requirement.
The new tests use stdlib unittest and are discovered by the existing runner.
The changed and new Python files parse with `feature_version=(3, 6)`; this is
a grammar check, not native Python 3.6 execution.

Direct modules ran with their ordinary `python3 tests/test_review_faults_*.py`
entry points, one file per invocation. The full suite runs include the same
fault lists. Each fault runner copies source into disposable scratch, runs
its named green control, changes only the planted bytes in that copy, and
requires its named assertion to fail. The new fault runner additionally checks
the old-behavior call ids and the requested top-level construct witnesses.
Existing fault labels, their named tests, and both green exemptions are listed
below. None represents a sealed measurement.

Mode A was not run: it needs Docker, which this account cannot reach. Mode B
and C results, all other required commands and direct-module summary lines are
recorded below verbatim after completion. An initial mode-B run started before
the final whole-call preflight checks were added; it is superseded by the final
mode-B run below. Targeted tests were repeated for those additions. The initial runs also found
that the citation checker catalogs only tracked decision records: 0125 was
still untracked, so its code citation was refused. Staging only the allowed
new record fixed the catalog input; the targeted check then printed
`citations: 294/294 resolve`. Both complete modes were rerun after staging.
The initial mode B also overlapped a source edit, so its loaded mutation anchor
no longer matched the copied final source; the stable-source rerun resolves
that mismatch. Its row-12 disposable child tests additionally inherited the
required relative TMPDIR after changing their own working directory. Their
existing support code assigns that relative value directly to tempfile, so
those children could not find scratch. A scratch-only child directory named
`gars-row-9fix-scratch` inside the scratch twin preserves the same relative
scratch spelling from those disposable child folders. An initial self-link
attempt made those paths noncanonical and masked two row-12 mutation witnesses;
it was replaced with a real directory. A direct lifecycle fault run verifies
that setup. No repository support file, guard or
expected result was changed to resolve these execution conditions.

## Named new fault witnesses

| Planted fault | Named test made red | Seen red |
|---|---|---|
| placement never moves | `CdPlacementTests.test_honest_cd_data` | yes, disposable mutation after green control |
| top-level condition dropped | `CdPlacementTests.test_top_level_required` | yes, disposable mutation after green control |
| resolvability condition dropped | `CdPlacementTests.test_variable_target_reset` | yes, disposable mutation after green control |
| symlink containment dropped | `CdPlacementTests.test_symlink_target_reset` | yes, disposable mutation after green control |
| all containment dropped | `CdPlacementTests.test_outside_targets_reset` | yes, disposable mutation after green control |
| placement carried between calls | `CdPlacementTests.test_calls_start_at_root` | yes, disposable mutation after green control |
| conditional-chain limit dropped | `CdPlacementTests.test_conditional_chain_limit` | yes, disposable mutation after green control |
| whole-call conditions dropped | `CdPlacementTests.test_whole_call_conditions` | yes, disposable mutation after green control |
| placement from flattened audit stream | `CdPlacementTests.test_nested_program_not_flattened` | yes, disposable mutation after green control |
| deduplication by token alone | `CdPlacementTests.test_deduplicate_by_token_and_folder` | yes, disposable mutation after green control |
| CDPATH retained | `CdPlacementTests.test_environment_startup_variables_removed` | yes, disposable mutation after green control |

## Preserved fault list and exemption controls

| Existing planted fault | Named test made red | Seen red |
|---|---|---|
| repository bytes nondeterministic | `BuildTests.test_determinism_history_and_private_key` | yes |
| extra repository history | `BuildTests.test_determinism_history_and_private_key` | yes |
| key enters case folder | `BuildTests.test_determinism_history_and_private_key` | yes |
| collision guard removed | `BuildTests.test_build_refusals` | yes |
| nonapplying plant accepted | `BuildTests.test_build_refusals` | yes |
| invalid case hidden | `ScoreTests.test_rates_invalid_and_first_run_cold_twin` | yes |
| catch numerator inflated | `ScoreTests.test_rates_invalid_and_first_run_cold_twin` | yes |
| account name published | `ScoreTests.test_published_copy_masks_and_keeps_fields` | yes |
| raw host digest published | `ScoreTests.test_published_copy_masks_and_keeps_fields` | yes |
| kit prefix published | `ScoreTests.test_published_copy_masks_and_keeps_fields` | yes |
| home prefix published | `ScoreTests.test_published_copy_masks_and_keeps_fields` | yes |
| oracle ignores class | `OracleTests.test_full_grid` | yes |
| oracle ignores file | `OracleTests.test_full_grid` | yes |
| line tolerance widened | `OracleTests.test_full_grid` | yes |
| min severity ignored | `OracleTests.test_full_grid` | yes |
| file mode ignored | `OracleTests.test_full_grid` | yes |
| repository prefix retained | `OracleTests.test_full_grid` | yes |
| NOTE becomes alarm | `OracleTests.test_full_grid` | yes |
| closed enum ignored | `ContractTests.test_classes_closed` | yes |
| required fields ignored | `ContractTests.test_schema_contract_drift` | yes |
| envelope taken from stub text | `LaunchTests.test_envelope_and_command_are_code_owned` | yes |
| producer uid check removed | `LaunchTests.test_identity_refusals` | yes |
| unresolved producer account accepted | `LaunchTests.test_identity_refusals` | yes |
| root uid allowed | `LaunchTests.test_identity_refusals` | yes |
| missing model allowed | `LaunchTests.test_api_model_and_prompt_refusals` | yes |
| API key allowed | `LaunchTests.test_api_model_and_prompt_refusals` | yes |
| prompt hash not checked | `LaunchTests.test_api_model_and_prompt_refusals` | yes |
| output owner ignored | `LaunchTests.test_review_output_owner` | yes |
| symlink output followed | `LaunchTests.test_symlink_review_is_invalid` | yes |
| parent step rule removed | `LaunchTests.test_blindness_every_spelling` | yes |
| absolute path rule removed | `LaunchTests.test_blindness_every_spelling` | yes |
| home path rule removed | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness does not invalidate | `LaunchTests.test_blindness_stream_makes_record_invalid` | yes |
| limit no longer stops | `LaunchTests.test_usage_limit_stops_retains_and_resumes` | yes |
| only filter ignored | `LaunchTests.test_only_and_existing_never_overwritten` | yes |
| existing review rerun allowed | `LaunchTests.test_only_and_existing_never_overwritten` | yes |
| assistant model mismatch ignored | `LaunchTests.test_model_mismatch_invalid_and_synthetic_ignored` | yes |
| model mismatch accepted | `LaunchTests.test_model_mismatch_invalid_and_synthetic_ignored` | yes |
| settings copy altered | `LaunchTests.test_envelope_and_command_are_code_owned` | yes |
| created directory neutrality rule removed | `LaunchTests.test_environment_and_neutral_parent_guard` | yes |
| Claude environment retained | `LaunchTests.test_envelope_and_command_are_code_owned` | yes |
| answer key in case allowed | `BuildTests.test_answer_key_base_refused` | yes |
| neutral id omits salt | `BuildTests.test_salt_changes_neutral_identifier` | yes |
| output inside worktree allowed | `BuildTests.test_worktree_output_refused` | yes |
| first run always true | `ScoreTests.test_rates_invalid_and_first_run_cold_twin` | yes |
| answer hashes not checked | `ScoreTests.test_tamper_and_mixed_records` | yes |
| mixed models accepted | `ScoreTests.test_tamper_and_mixed_records` | yes |
| same uid record accepted | `ScoreTests.test_tamper_and_mixed_records` | yes |
| record prompt mismatch accepted | `ScoreTests.test_tamper_and_mixed_records` | yes |
| latest invalid attempt selected | `ScoreTests.test_latest_valid_attempt_retains_all` | yes |
| mask literal retained | `ScoreTests.test_published_copy_masks_and_keeps_fields` | yes |
| raw uid published | `ScoreTests.test_published_copy_masks_and_keeps_fields` | yes |
| zero denominator hidden | `ScoreTests.test_rates_invalid_and_first_run_cold_twin` | yes |
| answer interval shifted | `BuildTests.test_plant_match_intervals_cover_changed_lines` | yes |
| external input leak accepted | `BuildTests.test_external_case_leak_refused` | yes |
| blindness ignores nested shell | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness ignores nested interpreter | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness ignores brace home | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness ignores variable parent | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness ignores attached option | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness ignores bare cd | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness overcuts relative options | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness restores blanket root exemption | `LaunchTests.test_blindness_every_spelling` | yes |
| root delimiter allowance applies to every command | `LaunchTests.test_blindness_every_spelling` | yes |
| root scan omits nested shell | `LaunchTests.test_blindness_every_spelling` | yes |
| root scan mistakes script path for program text | `LaunchTests.test_blindness_every_spelling` | yes |
| root scan exempts path fields | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores option-only arguments | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness treats lone separators as paths | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness ignores attached parent and home paths | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness ignores HOME modifiers | `LaunchTests.test_blindness_every_spelling` | yes |
| blindness ignores PWD modifiers | `LaunchTests.test_blindness_every_spelling` | yes |
| saved output allowance widened to projects | `LaunchTests.test_session_output_store_boundary` | yes |
| own saved output refused | `LaunchTests.test_session_output_store_boundary` | yes |
| saved output ignores project normalization | `LaunchTests.test_session_output_store_boundary` | yes |
| launch session omitted from blindness | `LaunchTests.test_envelope_and_command_are_code_owned` | yes |
| absent reserved id leaks | `BuildTests.test_external_case_leak_refused` | yes |
| bare cd ignores newline | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores subshell | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores brace group | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores then | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores do | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores else | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores builtin | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores command | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores eval | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores exec | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores time | `LaunchTests.test_blindness_every_spelling` | yes |
| settings missing at launch accepted | `LaunchTests.test_settings_required_before_launch` | yes |
| settings CLI argument optional | `LaunchTests.test_settings_required_before_launch` | yes |
| settings envelope hash invented | `LaunchTests.test_envelope_and_command_are_code_owned` | yes |
| missing settings hash scored | `ScoreTests.test_sandbox_settings_bound_across_all_attempts` | yes |
| mixed settings hashes scored | `ScoreTests.test_sandbox_settings_bound_across_all_attempts` | yes |
| settings hash masked as identity | `ScoreTests.test_published_copy_masks_and_keeps_fields` | yes |
| prose separator treated as command | `LaunchTests.test_blindness_every_spelling` | yes |
| separator default skips embedded words | `LaunchTests.test_blindness_every_spelling` | yes |
| interpreter program exception removed | `LaunchTests.test_blindness_every_spelling` | yes |
| settings hash optional in schema | `ContractTests.test_schema_contract_drift` | yes |
| bare cd ignores if keyword | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores escaped cd | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores time option | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores command option | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores arbitrary prefix | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd counts redirect descriptor as argument | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd counts redirect target as argument | `LaunchTests.test_blindness_every_spelling` | yes |
| dollar quoted separator ignored | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores shell option cluster | `LaunchTests.test_blindness_every_spelling` | yes |
| bare cd ignores full path shell | `LaunchTests.test_blindness_every_spelling` | yes |
| named redirect descriptor ignored | `LaunchTests.test_blindness_every_spelling` | yes |
| item 21 program contexts removed | `LaunchTests.test_blindness_every_spelling` | yes |
| Z1 prefix option value becomes command | `LaunchTests.test_blindness_every_spelling` | yes |
| Z1 attached pattern cluster ignored | `LaunchTests.test_blindness_every_spelling` | yes |
| patternless rg takes a pattern | `LaunchTests.test_blindness_every_spelling` | yes |
| item 22a pattern data scanned again | `CorpusTests.test_honest_call_corpus` | yes |
| item 22b content scanned again | `CorpusTests.test_honest_call_corpus` | yes |
| item 22c heredoc bodies scanned again | `CorpusTests.test_honest_call_corpus` | yes |
| item 22d comments scanned again | `CorpusTests.test_honest_call_corpus` | yes |
| item 22d glued semicolon retained | `CorpusTests.test_honest_call_corpus` | yes |
| item 22d regex token splitting restored | `CorpusTests.test_honest_call_corpus` | yes |
| item 22d word pieces become root tokens | `CorpusTests.test_honest_call_corpus` | yes |
| item 22e separated shell options ignored | `CorpusTests.test_honest_call_corpus` | yes |
| AA1 midword hash starts comment | `LaunchTests.test_hash_comment_boundaries` | yes |
| AA1 quoted heredoc hides following commands | `LaunchTests.test_quoted_heredoc_operators` | yes |
| AA1 Glob pattern loses path role | `LaunchTests.test_glob_patterns_and_grep_prose` | yes |
| AA1 key value operand untested | `LaunchTests.test_key_value_operands` | yes |
| item 23 ambiguous line permits removal | `LaunchTests.test_ambiguous_removal_cues_scan_instead` | yes |
| item 23 missing heredoc closer hides commands | `LaunchTests.test_heredoc_removal_requires_delimiter` | yes |
| added-byte leak in commit message: off-by-one | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in root commit message: off-by-one | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in changed file: off-by-one | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in folder name: off-by-one | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in manifest: off-by-one | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in plant diff added file: off-by-one | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in decoded tree name: off-by-one | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in commit message: P01 | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in root commit message: P01 | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in changed file: P01 | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in folder name: P01 | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in manifest: P01 | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in plant diff added file: P01 | `BuildTests.test_added_byte_leak_control` | yes |
| added-byte leak in decoded tree name: P01 | `BuildTests.test_added_byte_leak_control` | yes |
| changed base file wrongly exempt | `BuildTests.test_base_exemption_is_byte_identity_at_same_path` | yes |
| renamed base blob wrongly exempt | `BuildTests.test_base_exemption_is_byte_identity_at_same_path` | yes |
| unchanged lines wrongly swept | `BuildTests.test_added_byte_leak_control` | yes |

Both existing green exemption controls remained green:

- `unchanged line of changed file: off-by-one`: `BuildTests.test_added_byte_leak_control`.
- `unchanged line of changed file: P01`: `BuildTests.test_added_byte_leak_control`.

## Verification summaries

`python3 tests/run_tests.py — mode B` (exit 0):

```text
collected 286 tests from tests
collected 233 tests from gars/tests
cd-call corpus graded-against-seen: 11/11
honest-call corpus graded-against-seen: 278/278
Ran 519 tests in 395.110s
OK (skipped=77)
```

`python3 tests/run_tests.py — mode C` (exit 0):

```text
collected 286 tests from tests
collected 233 tests from gars/tests
cd-call corpus graded-against-seen: 11/11
honest-call corpus graded-against-seen: 278/278
Ran 519 tests in 397.206s
OK (skipped=104)
```

`python3 tests/check_contracts.py` (exit 0):

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py` (exit 0):

```text
collected 286 tests from tests
collected 233 tests from gars/tests
suite: 519 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py` (exit 0):

```text
Ran 44 tests in 37.815s
OK
```

`python3 evals/check_results.py --controls --lexicon` (exit 0):

```text
clean — graded=1
```

`python3 tests/test_review_faults_build.py` (exit 0):

```text
Ran 11 tests in 92.564s
OK
```

`python3 tests/test_review_faults_cd.py` (exit 0):

```text
Ran 20 tests in 0.114s
OK
cd-call corpus graded-against-seen: 11/11
```

`python3 tests/test_review_faults_cd_faults.py` (exit 0):

```text
Ran 1 test in 1.415s
OK
```

`python3 tests/test_review_faults_core.py` (exit 0):

```text
Ran 9 tests in 0.024s
OK
```

`python3 tests/test_review_faults_corpus.py` (exit 0):

```text
Ran 1 test in 0.210s
OK
honest-call corpus graded-against-seen: 278/278
```

`python3 tests/test_review_faults_faults.py` (exit 0):

```text
Ran 1 test in 204.987s
OK
```

`python3 tests/test_review_faults_launch.py` (exit 0):

```text
Ran 20 tests in 2.114s
OK
```

The four changed/new Python files were checked by an inline stdlib script
calling `ast.parse(src, filename=name, feature_version=(3, 6))` on each file:

```text
Python feature_version=(3, 6): 4/4 changed or new Python files parse
```

`git diff --stat 5ba82c6 -- .github gars benchmarks docs/ledger.csv evals ':(exclude)evals/review-faults'`
printed nothing (exit 0).

`git diff --stat 5ba82c6 -- evals/review-faults/fixtures gars/_references`
printed nothing (exit 0).

`git diff --check` printed nothing (exit 0). `bash docs/decisions/build_index.sh`
regenerated the decision index; its only added row is 0125. The two source/copy
SHA-256 pairs above match. The source files under `docs/reviews/` remain untracked.

The runner adds 21 tests, from 498 to 519, with none of the new tests skipped.
Mode B now skips **77**, versus the README's earlier 73: four real-gitleaks
integration tests skip because that executable is unavailable. Mode C still
skips **104**; 27 further TMPDIR-required cases skip compared with this mode B.
The README uses the runner's own figures, 77 and 104, and no longer implies a
verified Docker mode A for this follow-up. DEVELOPMENT's two current total
claims both use 519; historical counts remain untouched.

The final direct fault run reports **144/144** original faults red, with both
original exemption controls green. The new run reports **11/11** placement
faults red. Their names and named acceptance tests are listed above.

The completed initial full runs were superseded for the execution conditions
explained above; their failure summaries are retained here, not counted as
successful verification:

```text
Ran 519 tests in 368.149s
FAILED (failures=61, skipped=77)
Ran 519 tests in 377.297s
FAILED (failures=3, skipped=104)
```

The initial citation-only check reported `citations: 293/294 resolve` and
`FAILED (failures=1)`; after tracking the new record it reported
`citations: 294/294 resolve` and `OK`. The scratch self-link trial of
`python3 gars/tests/test_lifecycle_faults.py` ended:

```text
Ran 1 test in 17.848s
FAILED (failures=2)
```

After replacing that scratch-only link with a real child directory, the same
unchanged command ended:

```text
Ran 1 test in 17.916s
OK
```


## Residual gaps — each NOT met

- Failed-cd runtime detection: **NOT met**. The audit assumes an accepted change
  succeeded; a subsequent semicolon-joined read can execute from the previous
  folder and be misplaced. This is a text-audit residual, not sandbox enforcement.
- Historical symlink reconstruction: **NOT met**. Links are resolved at audit
  time; links changed after execution are judged in their current state.
- Complete shell interpretation: **NOT met**. All of 0072's existing residuals
  remain: shell indirection, variable and assignment evaluation, command
  substitution beyond parsed visible words, evaluated strings, aliases and
  functions, unparsed nested shells/quoting, interpreter program text, reads in
  exempt awk/sed programs, brace and parameter-default expansion, URL-embedded
  paths, physical-line continuations, legacy dollar-bracket arithmetic,
  operators inside parameter expansion and ANSI-C quoted heredoc delimiters.
  Conservative false positives and long encoded session-store names remain.
- Deployment sandbox efficacy and separate-user/read-only-credential evidence:
  **NOT met** by this change. The existing uid check proves only different
  producing and reviewing accounts on the launch host; it does not bind the
  builder host or GARS's role decision. The settings hash binds bytes, not
  enforcement, and can confirm guessed settings contents.
- R-093's role code half: **NOT met**; launch_role still returns producer.
- Row 9 sealing and first measured run: **NOT met** by this follow-up. The
  reserved record and ledger are untouched. There is no measured catch rate.
- Public credibility: **NOT met**. Independent-context seals are development
  evidence; external-human seals are still needed. Diff-style inference and
  sealer/producer model-family independence are not established here.
- Broad per-class evidence and complete public recomputation: **NOT met**.
  One plant per class is thin, twelve outcomes are publicly recomputable and
  the three private sealed outcomes are checkable only by hash.
- Science and trailer-gate JSON integration: **NOT met**; these remain later work.
- Real fixture gitleaks verification: **NOT met** here under 0072 Q2 A; this
  round leaves all fixture bytes unchanged and does not substitute a scanner.
- Docker mode A, native Python 3.6 execution, cluster execution and merge-result
  CI: **NOT met** here. Docker is inaccessible to this account; grammar parsing
  under Python 3.13.5 does not demonstrate native Python 3.6 execution.
- Independent review and approval of this follow-up: **NOT met** by the producer.
  No approval, merge, remote operation, push or pull request is performed.

## Owner rulings needed

None.
