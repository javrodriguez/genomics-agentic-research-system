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


## Review round 2 fixes

2026-09-24. The supplied independent review is REJECT; this is the producer's
response, not approval. All code decisions below are lane decisions under the
existing delegation. The earlier report and decision bytes remain intact.

In this table, runner means `evals/review-faults/run_reviews.py`, cd tests means
`tests/test_review_faults_cd.py`, and cd faults means
`tests/test_review_faults_cd_faults.py`.

| Finding | Changed files | Test | Result; red-on-fault seen and how |
|---|---|---|---|
| F1: pushd/popd retain deeper placement | runner, cd tests, cd faults | `test_other_directory_changers` | PASS; yes: removing the directory-changer guard makes pushd, popd and quoted-pushd subtests red |
| F2: backquote opens on cd word | runner, cd tests, cd faults | `test_backquote_on_cd_word` | PASS; yes: removing the source-backquote check makes both initial and later backquote-cd witnesses red |
| F3: prefixed compound nesting | runner, cd tests, cd faults | `test_prefixed_compound_commands` | PASS; yes: removing uncertain-compound refusal makes negated if/while, timed group with and without options, and named/unnamed coproc red |
| F4: merged operator misses chain end | runner, cd tests, cd faults | `test_conditional_chain_limit` | PASS; yes: both dropping the whole limit and restoring the old depth-before-token check make merged subshell, substitution and newline endings red |
| F5: physical-directory options | runner, cd tests, cd faults | `test_physical_directory_option` | PASS; yes: removing set from the whole-call hazards makes short, long and clustered physical-option cases red against an in-kit symlink |
| F6: PWD/OLDPWD mutation | runner, cd tests, cd faults | `test_pwd_reassignment` | PASS; yes: removing the variable hazard makes assignment, export, declare, readonly, typeset and read witnesses red |
| F7: eval-defined cd function | runner, cd tests, cd faults | `test_indirect_shell_state` | PASS; yes: removing indirect-state hazards makes eval, source and dot-command witnesses red |
| F8: fresh-clone parser and platform skip figures | README count line; DEVELOPMENT count lines | unchanged workflow gate function applied locally to the actual mode-C log; `tests/check_counts.py` | PASS; prior README observed red with its missing Linux phrase; corrected README green; no workflow edit |
| F9: inherited commit identity | this report; current commit metadata | neutral author/committer assertion on the new commit | Current-round prevention implemented with command-scoped identity; no mutation test. Historical metadata correction is NOT met: rewriting the earlier round would exceed this round's one new commit, so that existing commit is retained |
| F10: unnamed lane decisions | appended 0125 addendum, harness README, this report | F1, F5 and F6 acceptance tests plus append-only byte-prefix check | PASS; yes, the corresponding code faults are red; no owner ruling inferred |
| F11: missing spelling classes | cd tests, cd faults | six new tests and expanded chain subtests | PASS; yes, all seven new faults are observed red, with every reviewed attack represented |

The pre-fix acceptance run, after adding regressions but before changing the
runner, printed `Ran 26 tests in 0.133s` and `FAILED (failures=36)`; the supplied
data still graded 11/11. The first implementation trial conservatively treated
all dot words as source commands and rejected P1-34's ordinary find operand.
That trial printed `Ran 26 tests in 0.142s` and `FAILED (failures=1)`; its old-
placement mutation's green control also failed. Restricting the dot hazard to
command positions restored that call without weakening any assertion. The
final results below supersede those diagnostic failures.

The added whole-call guards deliberately refuse placement for set, directory
stack commands, directory-variable operands and assignments, eval/source and
dot commands. Unknown prefixed compound openers also refuse placement. These
are conservative text checks, not shell execution. A file operand consisting
of a dot stays data. Merged closing operators end a conditional chain but still
cannot qualify as a boundary that accepts cd. Existing classification order,
program/data exemptions, other-tool placement, allowlists and environment
cleanup remain unchanged.

All commands ran from the repository root without changing directory, with
TMPDIR, TEMP and TMP set to the relative scratch twin before any work. Mode C
then unset TMPDIR while retaining TEMP and TMP there. Logs, editing helpers,
disposable copies and the commit-message file stayed in that twin. The existing
real child scratch directory supports disposable tests that change their own
working directory. Both full modes and independent direct checks ran with
stable Python source; they used no network or model. Standard-library unittest
collected six additional tests, from 519 to 525; no new test skips. The Python
3.6 check is a grammar check, not native-runtime evidence.

The README restores exactly the two phrases consumed by the unchanged fresh-
clone workflow. Its macOS 73 is restored from the base rather than replaced by
this host's 77. Mode B's 77 and mode C's 104 remain unchanged from round 1;
mode B includes four unavailable real-gitleaks integrations that are not part
of the documented macOS environment. No macOS or Docker mode A run is claimed.
Mode C's actual runner figure remains the README's Linux 104. The total count
lines in README and DEVELOPMENT now say 525.

### Verification commands and verbatim summaries

`python3 tests/run_tests.py (mode B)` (exit 0):

```text
collected 292 tests from tests
collected 233 tests from gars/tests
cd-call corpus graded-against-seen: 11/11
honest-call corpus graded-against-seen: 278/278
Ran 525 tests in 399.478s
OK (skipped=77)
```

`python3 tests/run_tests.py (mode C)` (exit 0):

```text
collected 292 tests from tests
collected 233 tests from gars/tests
cd-call corpus graded-against-seen: 11/11
honest-call corpus graded-against-seen: 278/278
Ran 525 tests in 393.563s
OK (skipped=104)
```

`python3 tests/check_contracts.py` (exit 0):

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py` (exit 0):

```text
collected 292 tests from tests
collected 233 tests from gars/tests
suite: 525 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py` (exit 0):

```text
Ran 44 tests in 42.608s
OK
```

`python3 evals/check_results.py --controls --lexicon` (exit 0):

```text
clean — graded=1
```

`python3 tests/test_review_faults_build.py` (exit 0):

```text
Ran 11 tests in 101.596s
OK
```

`python3 tests/test_review_faults_cd.py` (exit 0):

```text
Ran 26 tests in 0.144s
OK
cd-call corpus graded-against-seen: 11/11
```

`python3 tests/test_review_faults_cd_faults.py` (exit 0):

```text
Ran 1 test in 2.519s
OK
```

`python3 tests/test_review_faults_core.py` (exit 0):

```text
Ran 9 tests in 0.023s
OK
```

`python3 tests/test_review_faults_corpus.py` (exit 0):

```text
Ran 1 test in 0.215s
OK
honest-call corpus graded-against-seen: 278/278
```

`python3 tests/test_review_faults_faults.py` (exit 0):

```text
Ran 1 test in 211.414s
OK
```

`python3 tests/test_review_faults_launch.py` (exit 0):

```text
Ran 20 tests in 2.099s
OK
```

The changed/new Python grammar check and unchanged workflow gate printed:

```text
Python feature_version=(3, 6): 4/4 changed or new Python files parse
Prior README gate: FAIL: README.md states the Linux cold-clone skip count 0 times, expected once
plain run: Ran 525 tests, OK, skipped 104
documented in README.md: 104 on Linux (the bar); 73 on macOS
ok: 104 skips, at most 104 documented
```

The workflow gate was extracted from its existing YAML into a scratch-only
stdlib script and called with the actual mode-C log and each README version.
No workflow bytes changed. This checks its documented-count logic locally;
it does not claim a fresh-clone CI run.

Both required protected diffs printed nothing (exit 0):

- `git diff --stat 5ba82c6 -- .github gars benchmarks docs/ledger.csv evals ':(exclude)evals/review-faults'`
- `git diff --stat 5ba82c6 -- evals/review-faults/fixtures gars/_references`

`git diff --check` printed nothing. `bash docs/decisions/build_index.sh` was
rerun after each addendum; the generated index is unchanged from round 1.
An inline byte-prefix check printed `Append-only prefixes: 2/2 intact` for
0125 and this report. The review remains untracked and unchanged. Supplied
committed data hashes remain exactly:

```text
8019297d9b0cd64e8260e2678c2991613446b6524ce4ddf1bccb9dd6188cdeb4 review_faults_cd_calls.jsonl
d380fdae2afa83f318a3437bf8c6c745b24b1553f8831b74f3295bbdf24172e6 review_faults_cd_calls_README.md
```

### Faults observed in this round

Every placement fault below was planted in a disposable copy after the named
unfaulted test passed; the runner required assertion failure, not import errors.
Its emitted red witnesses include every reviewed spelling, and the old-behavior
fault still names exactly P1-34, P1-40, P1-47, P1-52 and P1-63.

| Planted fault | Named test made red | Observed |
|---|---|---|
| placement never moves | `test_honest_cd_data` | yes |
| top-level condition dropped | `test_top_level_required` | yes |
| resolvability condition dropped | `test_variable_target_reset` | yes |
| symlink containment dropped | `test_symlink_target_reset` | yes |
| all containment dropped | `test_outside_targets_reset` | yes |
| placement carried between calls | `test_calls_start_at_root` | yes |
| conditional-chain limit dropped | `test_conditional_chain_limit` | yes |
| whole-call conditions dropped | `test_whole_call_conditions` | yes |
| placement from flattened audit stream | `test_nested_program_not_flattened` | yes |
| deduplication by token alone | `test_deduplicate_by_token_and_folder` | yes |
| CDPATH retained | `test_environment_startup_variables_removed` | yes |
| other directory changers ignored | `test_other_directory_changers` | yes |
| backquote on cd word ignored | `test_backquote_on_cd_word` | yes |
| prefixed compound uncertainty ignored | `test_prefixed_compound_commands` | yes |
| merged chain ends ignored | `test_conditional_chain_limit` | yes |
| physical option ignored | `test_physical_directory_option` | yes |
| PWD mutation ignored | `test_pwd_reassignment` | yes |
| indirect shell state ignored | `test_indirect_shell_state` | yes |

All **144/144** original faults named in the earlier table above were observed
red again in the direct run; both named unchanged-line exemption controls
remained green. The labels were compared against that existing table, not
inferred from a green module alone. All **18/18** placement faults above were
observed red. Both full-suite modes reran these fault lists as well. No prior
expected result, threshold or guard was weakened.

## Owner rulings needed

None.

### Residual gaps still open — each NOT met

- Failed-cd runtime detection and historical symlink reconstruction: **NOT met**.
  The audit assumes accepted cd succeeded and resolves links at audit time.
- Complete shell interpretation and all other 0072 item 20–23 residuals: **NOT
  met**. General indirection, interpreter text and unparsed constructs still
  depend on the sandbox. Closing the reviewed eval spelling does not prove a
  general evaluator. Conservative false positives remain possible.
- Historical commit-identity repair for F9: **NOT met**. The new commit uses a
  neutral command-scoped author and committer, verified without printing the
  inherited identity; the earlier round's commit is retained, not rewritten.
- Sandbox deployment, account separation, R-093's role code half, public human
  seals, broad class evidence, complete public recomputation, science and
  trailer JSON integration: **NOT met**; all prior named gaps remain open.
- Row 9 seal, first measured run and catch-rate evidence: **NOT met**. This
  follow-up measures nothing; the reserved record and ledger are untouched.
- Docker mode A: **NOT met**, because this account cannot reach Docker. Native
  Python 3.6 execution, macOS rerun, cluster execution and fresh-clone or merge-
  result CI: **NOT met**; local grammar/gate checks are not those executions.
- Real fixture gitleaks verification and independent approval of these fixes:
  **NOT met**. No fixture bytes changed and the producer does not approve itself.

F1–F8 and F10–F11 closed; F9 prevents recurrence in this round but historical
metadata remains open as stated above; no finding waits on an owner ruling.

## Review round 3 fixes

2026-09-24. This responds to the second independent review, which rejected the
prior implementation. These are lane decisions under the delegation recorded
in 0072 and 0125, not new owner rulings. Previous report and decision bytes are
preserved. Runner means `evals/review-faults/run_reviews.py`; cd tests means
`tests/test_review_faults_cd.py`; cd faults means
`tests/test_review_faults_cd_faults.py` in the table below.

| Finding | Changed files | Acceptance test | Result; red-on-fault seen and how |
|---|---|---|---|
| F1 MAJOR: continuation newline hides a preceding AND, OR or pipeline operator | runner, cd tests, cd faults; 0125 addendum; harness README | `test_top_level_required`, `test_conditional_chain_limit` | PASS; yes: removing continuation metadata makes both named tests red, including space/newline, comment/newline, blank lines and stderr-pipe witnesses; honest continuation controls remain green |
| F2 MAJOR: retained heredoc or comment data supplies a false cd | runner, cd tests, cd faults; 0125 addendum; harness README | `test_retained_data_cannot_move_placement` | PASS; yes: removing retained-data refusal makes heredoc, substitution-comment, backquote-comment and arithmetic-comment witnesses red |
| F3 MINOR: append and subscript assignments evade PWD hazards | runner, cd tests, cd faults; 0125 addendum; harness README | `test_pwd_reassignment` | PASS; yes: removing variable-name normalization makes append, subscript and subscript-append assignments red for both PWD and OLDPWD |
| F4 NOTE: trap and dot after prefix options can move the directory | runner, cd tests, cd faults; 0125 addendum; harness README | `test_trap_and_prefixed_dot` | PASS; yes: independently removing trap refusal and prefixed-dot detection turns this test red; prefixes with options and option operands are covered; an ordinary find dot operand stays green |
| F5 NOTE: historical round-1 commit identity | this report; new commit metadata | command-scoped neutral author/committer assertion | Current-round prevention retained; no red-on-fault test. Historical metadata remains NOT met: recreating previous commits would rewrite history beyond this round's one new commit; this round preserves them |
| F6 NOTE: owner-rulings heading includes residuals | append-only report section | final-section content and prior byte-prefix assertions | PASS; no code fault applies. This round places residuals under their own level-two heading before its final owner-rulings heading, whose content is exactly None. Historical headings remain intact under the append-only rule |

No review finding is disputed and no expected result, threshold or guard was
weakened. The pre-fix regression run printed `Ran 28 tests in 0.154s`,
`FAILED (failures=24)`, and `cd-call corpus graded-against-seen: 11/11`.
That diagnostic preceded the implementation and additional blank-line and
option-operand coverage; it is superseded by the final green runs below.

Only placement proof changed: list continuations keep their preceding operator;
retained word-start comments and heredoc operators cannot prove a cd; variable
hazards include append and subscript forms; trap and prefixed dot refuse deeper
placement. Item 23's comment/heredoc removal, other 0072 items 20–23, all existing
data contexts, path classification, own-session allowance, environment cleanup
and the sandbox remain unchanged. All 11 rehearsal calls still score zero; the
277 honest original calls still score zero and their contract-hit control still
hits. The original bad-list and mutation tests retain their assertions.

### How commands were run

Every shell command ran from the repository root without changing directory.
TMPDIR, TEMP and TMP were set to the relative scratch twin before execution.
Mode C then unset TMPDIR while TEMP and TMP remained there. All logs, helpers,
disposable fault copies and the commit-message file stayed in the scratch twin;
its existing real child scratch directory supports disposable tests that change
their own working directory. No model, network, remote, push, merge or PR was
used. Python source remained stable throughout the final full-suite and direct
runs. Full modes B and C ran sequentially; independent direct modules and checks
ran alongside them. Each direct module was invoked separately with python3.

The suite adds two test methods, from 525 to 527; subtests extend the existing
methods without changing their collection count. The final runner figures below
supply the count claims. Mode B remains 77 skips and mode C remains 104 skips:
no skip count changed and no new test is skipped. The README's existing Linux
104 and macOS 73 cold-clone phrases remain intact; this host's B figure is not a
macOS execution. Count-only edits update README and DEVELOPMENT to 527.

### Verification commands and verbatim summaries
`python3 tests/run_tests.py (mode B)` (exit 0):

```text
collected 294 tests from tests
collected 233 tests from gars/tests
cd-call corpus graded-against-seen: 11/11
honest-call corpus graded-against-seen: 278/278
Ran 527 tests in 398.726s
OK (skipped=77)
```

`env -u TMPDIR python3 tests/run_tests.py (mode C)` (exit 0):

```text
collected 294 tests from tests
collected 233 tests from gars/tests
cd-call corpus graded-against-seen: 11/11
honest-call corpus graded-against-seen: 278/278
Ran 527 tests in 391.498s
OK (skipped=104)
```

`python3 tests/check_contracts.py` (exit 0):

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py` (exit 0):

```text
collected 294 tests from tests
collected 233 tests from gars/tests
suite: 527 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py` (exit 0):

```text
Ran 44 tests in 38.688s
OK
```

`python3 evals/check_results.py --controls --lexicon` (exit 0):

```text
clean — graded=1
```

`python3 tests/test_review_faults_build.py` (exit 0):

```text
Ran 11 tests in 93.363s
OK
```

`python3 tests/test_review_faults_cd.py` (exit 0):

```text
Ran 28 tests in 0.161s
OK
cd-call corpus graded-against-seen: 11/11
```

`python3 tests/test_review_faults_cd_faults.py` (exit 0):

```text
Ran 1 test in 3.166s
OK
```

`python3 tests/test_review_faults_core.py` (exit 0):

```text
Ran 9 tests in 0.023s
OK
```

`python3 tests/test_review_faults_corpus.py` (exit 0):

```text
Ran 1 test in 0.223s
OK
honest-call corpus graded-against-seen: 278/278
```

`python3 tests/test_review_faults_faults.py` (exit 0):

```text
Ran 1 test in 206.202s
OK
```

`python3 tests/test_review_faults_launch.py` (exit 0):

```text
Ran 20 tests in 3.139s
OK
```

The changed/new Python grammar check printed:

```text
Python feature_version=(3, 6): 4/4 changed or new Python files parse
```

The required protected-path commands printed nothing:

```text
git diff --stat 5ba82c6 -- .github gars benchmarks docs/ledger.csv evals ':(exclude)evals/review-faults'
git diff --stat 5ba82c6 -- evals/review-faults/fixtures gars/_references
```

`bash docs/decisions/build_index.sh` regenerated the index; its bytes were
unchanged because the addendum changes no frontmatter. `git diff --check`
printed nothing. Byte-prefix assertions preserve all prior bytes of 0125 and
this report. The final owner-rulings section assertion requires exactly None.
The round-2 review remains untracked and unchanged, as do all supplied reviews.
The two committed data files retain the required hashes:

```text
8019297d9b0cd64e8260e2678c2991613446b6524ce4ddf1bccb9dd6188cdeb4
d380fdae2afa83f318a3437bf8c6c745b24b1553f8831b74f3295bbdf24172e6
```

### Faults observed red in this round

Every placement fault ran in a disposable copy after its named unfaulted test
passed. Assertion failures were required; import errors were rejected. The
old-placement mutation again names P1-34, P1-40, P1-47, P1-52 and P1-63.

| Planted fault | Named test made red | Observed |
|---|---|---|
| placement never moves | `test_honest_cd_data` | yes |
| top-level condition dropped | `test_top_level_required` | yes |
| resolvability condition dropped | `test_variable_target_reset` | yes |
| symlink containment dropped | `test_symlink_target_reset` | yes |
| all containment dropped | `test_outside_targets_reset` | yes |
| placement carried between calls | `test_calls_start_at_root` | yes |
| conditional-chain limit dropped | `test_conditional_chain_limit` | yes |
| whole-call conditions dropped | `test_whole_call_conditions` | yes |
| placement from flattened audit stream | `test_nested_program_not_flattened` | yes |
| deduplication by token alone | `test_deduplicate_by_token_and_folder` | yes |
| CDPATH retained | `test_environment_startup_variables_removed` | yes |
| other directory changers ignored | `test_other_directory_changers` | yes |
| backquote on cd word ignored | `test_backquote_on_cd_word` | yes |
| prefixed compound uncertainty ignored | `test_prefixed_compound_commands` | yes |
| merged chain ends ignored | `test_conditional_chain_limit` | yes |
| physical option ignored | `test_physical_directory_option` | yes |
| PWD mutation ignored | `test_pwd_reassignment` | yes |
| continuation newlines ignored | `test_top_level_required, test_conditional_chain_limit` | yes |
| retained data allowed to move placement | `test_retained_data_cannot_move_placement` | yes |
| extended PWD assignments ignored | `test_pwd_reassignment` | yes |
| trap state ignored | `test_trap_and_prefixed_dot` | yes |
| dot after prefix options ignored | `test_trap_and_prefixed_dot` | yes |
| indirect shell state ignored | `test_indirect_shell_state` | yes |

All **23/23** placement faults above were observed red. All **144/144** original
faults in the earlier preserved-fault table were observed red again; emitted
labels were checked against that table. Both named unchanged-line exemption
controls remained green. Both full-suite modes also reran these mutation lists.
These are detector controls, not measured reviews or a catch-rate estimate.

## Residual gaps still open — each NOT met

- Failed-cd runtime detection and historical symlink reconstruction: **NOT met**.
  Accepted cd is assumed to succeed and links are resolved at audit time.
- Complete shell interpretation and all prior 0072 item 20–23 residuals: **NOT
  met**. General shell indirection, interpreter program text and unparsed
  constructs still depend on sandbox enforcement. The concrete F4 spellings
  are now refused, which does not prove a general evaluator. Conservative false
  positives remain possible, including whole-call data and prefix refusals.
- Historical round-1 commit identity repair (F5): **NOT met**. Earlier commits
  are preserved; this round uses neutral command-scoped author and committer.
- Sandbox deployment, account separation, R-093 role code, public human seals,
  broad class evidence, complete public recomputation, science and trailer JSON
  integration: **NOT met**; prior named deployment and row-exit gaps stay open.
- Row 9 seal, first measured run and catch-rate evidence: **NOT met**. This
  follow-up measures nothing; no ledger or reserved-record change is made.
- Docker mode A: **NOT met**, because this account cannot reach Docker. Native
  Python 3.6 execution, macOS rerun, cluster execution and fresh-clone or merge-
  result CI: **NOT met**; local grammar and count checks are not those runs.
- Real fixture gitleaks verification and independent approval of this round:
  **NOT met**. Fixtures are unchanged; this producer does not approve itself.

F1–F4 and F6 closed; F5 remains a documented historical metadata gap, with
recurrence prevented for this round; no finding waits on an owner ruling.

## Owner rulings needed

None.

## Review round B1 fixes

2026-09-24. Continuation B responds to review 2 against round 3 (`9021f2a`).
Item 7 is the lane's specification under the delegation recorded in 0072 and
0125; it is not attributed to the owner. Earlier report and decision bytes
remain intact. Runner below means `evals/review-faults/run_reviews.py`; cd tests
and cd faults mean `tests/test_review_faults_cd.py` and
`tests/test_review_faults_cd_faults.py`. No model or network was used, and this
follow-up measures nothing.

| Finding or requirement | Changed files | Acceptance test | Result; red-on-fault seen and how |
|---|---|---|---|
| Review 2 F1 MAJOR; item 7(a), complete newline rule | runner, cd tests, cd faults; 0125 addendum and harness README | `test_top_level_required`, `test_conditional_chain_limit`, `test_newline_boundary_grammar` | Round 3 covered AND/OR/pipelines; B1 adds every listed nonqualifying predecessor, consecutive newlines and quoted-word controls. Yes: disposable removal of continuation metadata makes the named tests red. |
| Review 2 F2 MAJOR; item 7(a), declined removal | retained round-3 runner and tests; B1 record and README | `test_retained_data_cannot_move_placement` | Round 3 already meets the specified refusal. Yes: removing retained-data refusal turns the heredoc and comment witnesses red. Removal itself remains unchanged. |
| Review 2 F3 MINOR; item 7(a), PWD anywhere except exact expansions | runner, cd tests, cd faults; 0125 addendum and harness README | `test_pwd_reassignment`, `test_pwd_text_whole_call` | B1 broadens assignment matching to raw-call and quote-removed PWD text, preserving earlier quoted assignment refusal. Exact expansions remain green. Yes: removing PWD hazard insertion makes append/subscript and arbitrary-text witnesses red. |
| Review 2 F4 NOTE, trap and prefixed dot | retained round-3 runner and tests; B1 record | `test_trap_and_prefixed_dot` | Existing trap and prefix-option refusals retained. Yes: each independent removal makes the named acceptance red. No new shell classes pursued. |
| Review 2 F5 NOTE, identity | 0125 addendum, this report; B1 commit metadata | ordinary repository-local commit, no identity overrides | Item 7(d) supersedes the old interpretation: S1 F7 ruled the public maintainer identity intended. Round 1 needs no repair. Neutral rounds 2 and 3 remain unchanged; the copied line lacked the F7 ruling, and the neutral name is not an address and leaks nothing. No red-on-fault applies. |
| Review 2 F6 NOTE, owner-rulings section | append-only report | current section equals exactly `None.`; prior-prefix comparison | Residuals have their own level-two heading. Historical headings stay unchanged under append-only rules. No red-on-fault applies. |
| Item 7(b–c), closed grammar and stop rule | 0125 addendum, harness README, this report | inspect documented grammar against items 1(a–f), 2 and 7(a) and implementation | Recorded the withdrawn broad threat sentence, its replacement, and the named unparsed-construct residual. MINOR or above now requires a defect against the grammar; unparsed escapes are NOTE requests to name them. No claim of general shell interpretation. |
| Item 7(d–f), identity, scratch spelling and append-only records | 0125 addendum, this report; regenerated CONTEXT | prior-prefix and boundary checks; ordinary commit with message file | No identity override, history rewrite, external write or lone parent-step scratch component. Index rebuilt; unchanged index bytes need no commit. No red-on-fault applies. |
| Items 1–5 otherwise unchanged | retained harness and original test controls | every direct review-fault module, both corpora, every prior disposable fault | Existing assertions and thresholds preserved. Mutation source anchors follow the updated equivalent guard; no named test or fault was removed. |
| Item 6, count claims | count lines only in README and DEVELOPMENT | both full-suite modes and `tests/check_counts.py` | Two new test methods increase collection from 527 to 529; all skip figures must come from the runner. Final results below. |

### Commands and verification method

All commands ran from the repository root, with TMPDIR, TEMP and TMP set to the
complete relative scratch-twin string before execution. Mode C explicitly
unset TMPDIR and retained TEMP/TMP there. All logs, helpers, commit-message text
and disposable mutation copies remain in that twin. The existing real child
scratch directory supports tests that change directory inside disposable copies.
No system temp folder, credentials, git configuration, hooks, remote, push,
merge or PR was used. The initial orientation lookup found no AGENTS.md and
read CLAUDE.md; the unavailable rg command was replaced by repository-local
file inspection. No reviewer conversation or other outside input was read.

Before the fix, the expanded cd module printed `Ran 30 tests in 0.187s`,
`FAILED (failures=25)`, and `cd-call corpus graded-against-seen: 11/11`.
The first mode-B run started before the final quote-removed PWD preservation
was added; its result is superseded by a complete stable-source mode-B rerun.
All reported final runs use the final source. Each direct module runs through
its own python3 entry point. Mutation runners pass named controls, plant one
fault per disposable copy, and require the named assertion to fail; import
errors do not count as red evidence. These controls are not measured reviews.

A final item-7(a) check found that a merged AND/newline token later in an
accepted chain ended conditional placement early. Its honest regression printed
`Ran 1 test in 0.070s`, `FAILED (failures=1)`. B1 now recognizes that continuation
when computing chain ends, while merged tokens still cannot qualify a cd
boundary. `test_newline_boundary_grammar` and the separate
`merged AND newline ends chain` mutation cover it. This stays within F1 and
item 7(a), not a new grammar class. Attempts to stop the superseded processes
found no matching process in the command context and stopped nothing. The final
results below come from fresh stable-source B and C runs. Earlier full-suite
results are superseded. The cd module
and its fault module passed after this last adjustment; full-suite and affected
direct-module checks are rerun on that final source.

The final plain-word control also covers an empty quoted word before newline:
it is a word, unlike an absent predecessor. That control printed
`Ran 1 test in 0.019s`, `FAILED (failures=1)` before the cursor-based distinction.
The expanded cd module then printed `Ran 30 tests in 0.196s`, `OK` and
`cd-call corpus graded-against-seen: 11/11`. Source was frozen after this last
item-7(a) adjustment; fresh B, C and every direct module supply the final results.
A digest check confirms Python sources did not change during those runs.

### Final verification commands and verbatim summaries

`python3 tests/run_tests.py (mode B)`:

```text
collected 296 tests from tests
collected 233 tests from gars/tests
cd-call corpus graded-against-seen: 11/11
honest-call corpus graded-against-seen: 278/278
Ran 529 tests in 436.509s
OK (skipped=77)
```

`env -u TMPDIR python3 tests/run_tests.py (mode C)`:

```text
collected 296 tests from tests
collected 233 tests from gars/tests
cd-call corpus graded-against-seen: 11/11
honest-call corpus graded-against-seen: 278/278
Ran 529 tests in 430.491s
OK (skipped=104)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 296 tests from tests
collected 233 tests from gars/tests
suite: 529 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 38.311s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 tests/test_review_faults_build.py`:

```text
Ran 11 tests in 111.177s
OK
```

`python3 tests/test_review_faults_cd.py`:

```text
Ran 30 tests in 0.210s
OK
cd-call corpus graded-against-seen: 11/11
```

`python3 tests/test_review_faults_cd_faults.py`:

```text
Ran 1 test in 6.255s
OK
```

`python3 tests/test_review_faults_core.py`:

```text
Ran 9 tests in 0.027s
OK
```

`python3 tests/test_review_faults_corpus.py`:

```text
Ran 1 test in 0.247s
OK
honest-call corpus graded-against-seen: 278/278
```

`python3 tests/test_review_faults_faults.py`:

```text
Ran 1 test in 228.254s
OK
```

`python3 tests/test_review_faults_launch.py`:

```text
Ran 20 tests in 2.914s
OK
```

```text
Python feature_version=(3, 6): 4/4 changed or new Python files parse
```

Both modes collected 529 tests. Mode B skipped 77 and mode C skipped 104,
unchanged from round 3; neither new test skips. README cold-clone figures stay
unchanged (Linux 104, macOS 73); this run is not a macOS measurement.

`bash docs/decisions/build_index.sh` regenerated CONTEXT with unchanged bytes.
`git diff --check` printed nothing. These required diff-stat commands printed
nothing against the public base:

```text
git diff --stat 5ba82c6 -- .github gars benchmarks docs/ledger.csv evals ':(exclude)evals/review-faults'
git diff --stat 5ba82c6 -- evals/review-faults/fixtures gars/_references
```

The changed/new Python check above covers all four Python files changed since
the public base, using ast.parse with feature_version=(3, 6); the three B1 Python
files use only stdlib and the existing harness modules. Prior decision and report
prefixes are byte-identical to round 3. The supplied review remains untracked and
unchanged. Data digests remain exactly:

```text
8019297d9b0cd64e8260e2678c2991613446b6524ce4ddf1bccb9dd6188cdeb4
d380fdae2afa83f318a3437bf8c6c745b24b1553f8831b74f3295bbdf24172e6
```

### Faults observed red in B1

Each named acceptance passed before its fault was planted. Every placement fault
below then produced its named assertion failure in a disposable copy. The old
placement fault again names P1-34, P1-40, P1-47, P1-52 and P1-63. All 144 original
faults named in the earlier preserved-fault table were also observed red in B1;
every emitted label was matched to that table and the unchanged fault list.
Both original exemption controls remained green. All 26 placement faults and
all 144 original faults also ran in both full-suite modes.

| Planted fault | Named test made red | Observed |
|---|---|---|
| placement never moves | `test_honest_cd_data` | yes |
| top-level condition dropped | `test_top_level_required` | yes |
| resolvability condition dropped | `test_variable_target_reset` | yes |
| symlink containment dropped | `test_symlink_target_reset` | yes |
| all containment dropped | `test_outside_targets_reset` | yes |
| placement carried between calls | `test_calls_start_at_root` | yes |
| conditional-chain limit dropped | `test_conditional_chain_limit` | yes |
| whole-call conditions dropped | `test_whole_call_conditions` | yes |
| placement from flattened audit stream | `test_nested_program_not_flattened` | yes |
| deduplication by token alone | `test_deduplicate_by_token_and_folder` | yes |
| CDPATH retained | `test_environment_startup_variables_removed` | yes |
| other directory changers ignored | `test_other_directory_changers` | yes |
| backquote on cd word ignored | `test_backquote_on_cd_word` | yes |
| prefixed compound uncertainty ignored | `test_prefixed_compound_commands` | yes |
| merged chain ends ignored | `test_conditional_chain_limit` | yes |
| physical option ignored | `test_physical_directory_option` | yes |
| PWD mutation ignored | `test_pwd_reassignment` | yes |
| continuation newlines ignored | `test_top_level_required`, `test_conditional_chain_limit` | yes |
| retained data allowed to move placement | `test_retained_data_cannot_move_placement` | yes |
| extended PWD assignments ignored | `test_pwd_reassignment` | yes |
| complete newline grammar ignored | `test_newline_boundary_grammar` | yes |
| merged AND newline ends chain | `test_newline_boundary_grammar` | yes |
| non-expansion PWD text ignored | `test_pwd_text_whole_call` | yes |
| trap state ignored | `test_trap_and_prefixed_dot` | yes |
| dot after prefix options ignored | `test_trap_and_prefixed_dot` | yes |
| indirect shell state ignored | `test_indirect_shell_state` | yes |

## Owner rulings needed

None.

## Residual gaps still open — each NOT met

- Failed-cd runtime detection and historical symlink reconstruction: **NOT met**.
  Accepted cd is assumed to take effect; links are resolved at audit time.
- Complete shell interpretation: **NOT met**. Escapes resting on constructs
  outside the closed grammar are the item 3 and 0072 item 20(c) residual,
  including shell indirection and interpreter program text. The sandbox is
  the enforcement wall, the audit a detector. All other 0072 residuals remain.
- Sandbox deployment, account separation, R-093 role code, public human seals,
  broad class evidence, public recomputation, science and trailer JSON
  integration: **NOT met**; existing deployment and row-exit gaps remain open.
- Row 9 seal, first measured run and catch-rate evidence: **NOT met**. This
  follow-up measures nothing, changes no ledger and writes no reserved record.
- Docker mode A: **NOT met**, because this account cannot reach Docker. Native
  Python 3.6 execution, macOS rerun, cluster and fresh-clone or merge-result CI:
  **NOT met**; grammar parsing and local count checks are not those executions.
- Real fixture gitleaks verification and independent B1 approval: **NOT met**.
  Fixtures remain unchanged; the producer does not approve itself.

Review 2 F1–F4 and F6 closed; F5 resolved by item 7(d)'s identity clarification;
items 7(a–f) completed. No finding waits on an owner ruling.


## Review round C1 fixes

Date: 2026-09-24. This round answers the copied B1 review under lane specification
item 8 and the owner's already-recorded delegation. Deployment never published
that review: its step failed on a path shape in its own leak-check pattern, not
a read. The lane supplied it by copy. The review stays untracked and unchanged.
Earlier report and decision bytes, earlier commits, item 7's existing guards,
0072's other scan rules, the measured prompt and fixtures are unchanged.

In the table, runner is `evals/review-faults/run_reviews.py`, cd tests and cd
faults are `tests/test_review_faults_cd.py` and
`tests/test_review_faults_cd_faults.py`. No model or network was used.

| Finding or requirement | Changed files | Acceptance test | Result; red-on-fault seen and how |
|---|---|---|---|
| B1 F1 MAJOR; item 8(a), raw backslash-newline | runner, cd tests, cd faults | `test_raw_line_continuation_guard`: exact reviewed AND, OR and pipeline spellings with a blank line, each followed by the outside parent-step read | PASS; yes, dropping the sole raw guard in a disposable copy makes all three named spellings fail. A removed-comment case proves the check precedes removal. |
| B1 F2 MAJOR; item 8(a), raw controls | same | `test_raw_control_character_guard`: carriage return inside cd word and after argument, each followed by the outside read; every prohibited control in removed data; ordinary tab/newline control | PASS; yes, the same guard-removal planting makes both exact reviewed spellings fail. No tokenizer changes. |
| Item 8(b), honest compatibility and preserved detection | cd tests and cd faults; existing corpus and fault tests retained | every direct module, both full modes, both corpora | PASS; 11/11 cd calls and 278/278 original calls graded, all honest calls zero and contract_hit positive. All 25 distinct placement plantings and all 144 original faults observed red, two exemptions green. |
| B1 F3 NOTE; item 8(c), named residual | 0125 addendum, harness README, this report | inspect named ANSI-C/locale quoting and continuation residual | Recorded; no extra parser rule. The new raw guard also refuses the reviewed split-cd and split-PWD continuations. ANSI-C and locale quoting remain unparsed. No red-on-fault claim for prose. |
| B1 F4 NOTE; item 8(c), all heredocs refuse placement | 0125 addendum, harness README, this report | inspect closed grammar and conservative refusal wording | Recorded; existing behavior retained as required. Removed heredoc bodies still leave an operator that blocks placement; honest calls can be flagged. No red-on-fault claim for prose. |
| B1 F5 NOTE; item 8(c), duplicate plantings | cd faults, this report | fault list has 25 distinct old/new pairs, each named acceptance observed red | PASS; continuation-newline and complete-newline entries merged with all three witnesses; extended-PWD and non-expansion-PWD entries merged with both witnesses. Twenty-six old entries represented 24 distinct plantings; adding the raw guard makes 25. No witness removed. |
| B1 F6 NOTE; item 8(c), last rulings heading | this append-only report | final heading is `## Owner rulings needed` and its body is exactly `None.` | PASS; historical headings remain intact. Residuals and closure line precede the final heading. No red-on-fault applies. |
| Items 7(d–e), 8(d), scope and identity | 0125 addendum, this report; ordinary commit metadata | diff boundaries, original byte prefixes, normal repository identity with message file | PASS; no identity overrides or history rewriting. Scratch uses the whole relative twin string. No protected edit or new rule beyond item 8(a). |
| Item 6, current count claims and record index | count lines of README and DEVELOPMENT, 0125 addendum; index rebuilt | both runner modes, count checker, index regeneration | PASS; two new test methods increase 529 to 531. Skips remain 77 in B and 104 in C; no skip-count change, no cold-clone figure changed. Regenerated CONTEXT bytes are unchanged. |

### How commands were run

Every command started at the repository root. TMPDIR, TEMP and TMP were set to
`../gars-row-9fix-scratch/` before each command; mode C then unset only TMPDIR.
All helper scripts, logs, mutation copies and commit-message text stayed in that
scratch twin. Its existing real child scratch directory supports the unchanged
suite's disposable child processes. No credentials or environment listing was
read. No git configuration, hooks or remotes were changed; no push, merge or PR.
An initial, unnecessary pwd invocation redirected its output to the null device
using a literal rooted path. That violated the relative-only command rule;
command history cannot be repaired, so deployment command-path compliance is
NOT met. The command was not repeated. The unavailable rg lookup fell back to
repository-local inspection; AGENTS.md
was absent, so CLAUDE.md was read. No reviewer conversation was read.

The two new methods ran before the fix using the cd module's direct entry point
and both explicit `CdPlacementTests` selectors. They printed
`Ran 2 tests in 0.032s` and `FAILED (failures=69)`, including every reviewed
F1/F2 spelling. After the fix the cd module printed `Ran 32 tests in 0.228s`,
`OK`, and `cd-call corpus graded-against-seen: 11/11`; its fault module printed
`Ran 1 test in 3.454s` and `OK`. The final direct runs below include both again.
Initial full modes B and C, the direct-module sequence and independent checks
ran concurrently against stable Python source. Mode B passed. Initial mode C
printed `Ran 531 tests in 391.297s`, `FAILED (failures=1, skipped=104)`:
`test_launcher_clears_marker_and_removes_script_forgery_on_failure` in the
unchanged stage-03 module returned FAILED instead of FAILED:EXIT_7. A direct
mode-C recheck with `python3 gars/tests/test_stage03_execution.py` and the
`Stage03ExecutionTests.test_launcher_clears_marker_and_removes_script_forgery_on_failure`
selector printed `Ran 1 test in 0.032s`, `OK`. No protected source was changed.
The complete mode-C suite was then rerun without concurrent test runs; its
final result is below. This does not establish the intermittent failure's
cause. Recorded Python digests match afterward.
Each direct module used its ordinary python3 entry point. Each mutation runner
passed its unfaulted named tests, planted one fault in a disposable copy and
required the named failure. The new raw-guard mutation also requires the exact
five reviewed spelling labels in the failures. Import errors do not count as
red evidence. No shell snippet from the new tests is executed.

### Final commands and verbatim summaries

`python3 tests/run_tests.py (mode B)` (exit 0):

```text
collected 298 tests from tests
collected 233 tests from gars/tests
cd-call corpus graded-against-seen: 11/11
honest-call corpus graded-against-seen: 278/278
Ran 531 tests in 397.014s
OK (skipped=77)
```

`env -u TMPDIR python3 tests/run_tests.py (mode C)` (exit 0):

```text
collected 298 tests from tests
collected 233 tests from gars/tests
cd-call corpus graded-against-seen: 11/11
honest-call corpus graded-against-seen: 278/278
Ran 531 tests in 392.289s
OK (skipped=104)
```

`python3 tests/check_contracts.py` (exit 0):

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py` (exit 0):

```text
collected 298 tests from tests
collected 233 tests from gars/tests
suite: 531 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py` (exit 0):

```text
Ran 44 tests in 39.918s
OK
```

`python3 evals/check_results.py --controls --lexicon` (exit 0):

```text
clean — graded=1
```

`python3 tests/test_review_faults_build.py` (exit 0):

```text
Ran 11 tests in 97.311s
OK
```

`python3 tests/test_review_faults_cd.py` (exit 0):

```text
Ran 32 tests in 0.233s
OK
cd-call corpus graded-against-seen: 11/11
```

`python3 tests/test_review_faults_cd_faults.py` (exit 0):

```text
Ran 1 test in 4.086s
OK
```

`python3 tests/test_review_faults_core.py` (exit 0):

```text
Ran 9 tests in 0.023s
OK
```

`python3 tests/test_review_faults_corpus.py` (exit 0):

```text
Ran 1 test in 0.229s
OK
honest-call corpus graded-against-seen: 278/278
```

`python3 tests/test_review_faults_faults.py` (exit 0):

```text
Ran 1 test in 213.621s
OK
```

`python3 tests/test_review_faults_launch.py` (exit 0):

```text
Ran 20 tests in 2.627s
OK
```

The original fault log contains 144 distinct red labels and two green exemption
labels. Every red label matched the unchanged, individually named table in this
report's "Preserved fault list and exemption controls" section. Those exact
faults and named tests were observed again in C1; no original expectation was
weakened. Both green controls are unchanged-line exemptions within a changed
file: `unchanged line of changed file: off-by-one` and
`unchanged line of changed file: P01`, both through
`BuildTests.test_added_byte_leak_control`. The 25 current placement plantings and their named red witnesses are:

| Planted fault | Named test made red | Red seen |
|---|---|---|
| placement never moves | `test_honest_cd_data` | yes, disposable copy after green control |
| top-level condition dropped | `test_top_level_required` | yes, disposable copy after green control |
| resolvability condition dropped | `test_variable_target_reset` | yes, disposable copy after green control |
| symlink containment dropped | `test_symlink_target_reset` | yes, disposable copy after green control |
| all containment dropped | `test_outside_targets_reset` | yes, disposable copy after green control |
| placement carried between calls | `test_calls_start_at_root` | yes, disposable copy after green control |
| conditional-chain limit dropped | `test_conditional_chain_limit` | yes, disposable copy after green control |
| whole-call conditions dropped | `test_whole_call_conditions` | yes, disposable copy after green control |
| placement from flattened audit stream | `test_nested_program_not_flattened` | yes, disposable copy after green control |
| deduplication by token alone | `test_deduplicate_by_token_and_folder` | yes, disposable copy after green control |
| CDPATH retained | `test_environment_startup_variables_removed` | yes, disposable copy after green control |
| other directory changers ignored | `test_other_directory_changers` | yes, disposable copy after green control |
| backquote on cd word ignored | `test_backquote_on_cd_word` | yes, disposable copy after green control |
| prefixed compound uncertainty ignored | `test_prefixed_compound_commands` | yes, disposable copy after green control |
| merged chain ends ignored | `test_conditional_chain_limit` | yes, disposable copy after green control |
| physical option ignored | `test_physical_directory_option` | yes, disposable copy after green control |
| PWD mutation ignored | `test_pwd_reassignment` | yes, disposable copy after green control |
| continuation newlines ignored | `test_top_level_required`, `test_conditional_chain_limit`, `test_newline_boundary_grammar` | yes, disposable copy after green control |
| retained data allowed to move placement | `test_retained_data_cannot_move_placement` | yes, disposable copy after green control |
| extended PWD assignments ignored | `test_pwd_reassignment`, `test_pwd_text_whole_call` | yes, disposable copy after green control |
| merged AND newline ends chain | `test_newline_boundary_grammar` | yes, disposable copy after green control |
| trap state ignored | `test_trap_and_prefixed_dot` | yes, disposable copy after green control |
| dot after prefix options ignored | `test_trap_and_prefixed_dot` | yes, disposable copy after green control |
| raw-text whole-call guard dropped | `test_raw_line_continuation_guard`, `test_raw_control_character_guard` | yes, disposable copy after green control |
| indirect shell state ignored | `test_indirect_shell_state` | yes, disposable copy after green control |

### Boundary and data checks

Both required commands printed nothing:

```text
git diff --stat 5ba82c6 -- .github gars benchmarks docs/ledger.csv evals ':(exclude)evals/review-faults'
git diff --stat 5ba82c6 -- evals/review-faults/fixtures gars/_references
```

The Python grammar checks printed:

```text
Python feature_version=(3, 6): 3/3 changed or new Python files parse.
Python feature_version=(3, 6): 15/15 harness and review-fault test modules parse.
Python feature_version=(3, 6): 4/4 changed or new Python files since 5ba82c6 parse.
```

Only standard-library imports and the existing harness imports are used.
`bash docs/decisions/build_index.sh` completed successfully; generated index
bytes did not change. Original prefixes of both append-only files match HEAD,
and the copied review's hash is unchanged. `git diff --check` is clean.
The supplied committed-copy SHA-256 values remain:

```text
8019297d9b0cd64e8260e2678c2991613446b6524ce4ddf1bccb9dd6188cdeb4  tests/data/review_faults_cd_calls.jsonl
d380fdae2afa83f318a3437bf8c6c745b24b1553f8831b74f3295bbdf24172e6  tests/data/review_faults_cd_calls_README.md
```

### Residual gaps still open — each NOT met

- Deployment command-path compliance: **NOT met**. The initial null-device
  redirect used a rooted path, violating the command rule. No deployment-scan
  acceptance is claimed; later relative commands cannot undo that breach.
- Failed-cd runtime detection and historical symlink reconstruction: **NOT met**.
  Accepted cd is assumed to succeed; links are judged at audit time.
- Full shell interpretation: **NOT met**. ANSI-C and locale quoting, shell
  indirection, interpreter program text and other unparsed constructs remain
  item 3 and 0072 item 20(c) residuals. Line continuations are refused by the
  raw guard, not interpreted. The sandbox remains the enforcement wall.
- Honest placement after a removed heredoc: **NOT met**. Every heredoc operator
  still blocks movement; this conservative refusal is the named F4 residual.
- Deployment sandbox efficacy, account separation, R-093 role code, external
  human seals, broad class evidence, public recomputation, science and trailer
  JSON integration: **NOT met**; prior deployment and row-exit gaps remain.
- Row 9 seal, first measured run and catch-rate evidence: **NOT met**. This
  follow-up measures nothing; no ledger or reserved record is written.
- Diagnosis of the initial mode-C stage-03 status mismatch: **NOT met**.
  The isolated recheck and final rerun pass, but do not establish its cause.
- Docker mode A: **NOT met**, because this account cannot reach Docker. Native
  Python 3.6, macOS, cluster, fresh-clone and merge-result CI execution:
  **NOT met**; grammar parsing and local checks do not verify those executions.
- Real fixture gitleaks integration and independent C1 approval: **NOT met**.
  Fixtures stay unchanged; the producer does not approve its own work.

F1 and F2 closed by the raw guard and red-on-fault evidence; F3 and F4 answered
as required named residuals; F5 and F6 closed. No finding waits on the owner.

## Owner rulings needed

None.
