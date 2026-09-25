# Row 9 heredoc placement: round 1

Base: `da400610da606285f70e5549ad01a505c723f858`.
Branch: `build/gars-row-09-heredoc-placement`. No review was supplied for this round.
This is the lane's implementation under the delegation quoted in 0072 and
0129 (`docs/decisions/0129-row-9-heredoc-placement.md`). It is not a new row or
an owner-authored specification. No model was run, and this follow-up measures
nothing. No catch rate, and no figure of a measured run beyond what 0074
records, is claimed.

## Requirement to acceptance

In this table:

- `runner` means `evals/review-faults/run_reviews.py`;
- `heredoc tests` means `tests/test_review_faults_heredoc.py`;
- `heredoc faults` means `tests/test_review_faults_heredoc_faults.py`.

| Requirement | Changed files | Acceptance | Result and red-on-fault evidence |
|---|---|---|---|
| 1(a): data-only block = blocked, and not blocked with only retained data removed, across every program the preflight inspects and item 8's raw-text guard | runner (`moving`, `data_only`, preflight `moving` flag), heredoc tests | `test_block_causes` (heredoc, here-string, kept comment, nested heredoc → data-only; eval, pushd, heredoc+eval, heredoc+unset, heredoc+nested eval, heredoc+raw control → blocked) | PASS; red-on-fault seen: yes, `carry applied to every blocked call` makes every block data-only, and its named test turns red |
| 1(b): a data-only call starts at the carried placement, in both placements | runner, heredoc tests | `test_honest_heredoc_sessions`, `test_honest_data_only_carry` | PASS. C01 0 hits and 0 ambiguous; C02 0 hits and 2 ambiguous; synthetic 0 and 0. Red-on-fault seen: yes, `data-only carry dropped` turns both red, with C01 and C02 each as a witnessed subtest |
| 1(b): each `cd` word (including heredoc text) is refused. Its operand is judged from the folder before it, and the rest of the call and its end go to the kit root | runner (unchanged refused-cd path), heredoc tests | `test_refused_cd_in_call`, `test_refused_cd_next_call`, `test_cd_word_in_data_only_call` | PASS, each at least 1 hit, or the folders asserted. Red-on-fault seen: yes, `refused cd in a data-only block keeps the carried placement` turns all three red |
| 1(c): the next call starts at the data-only call's end | runner (existing end carry), heredoc tests | `test_honest_data_only_carry` | PASS; red-on-fault seen: yes, `data-only block end not carried to the next call` turns it red |
| 1(c): the other edges still apply (error) | none | `test_error_edge_after_data_only` | PASS, the next call's own hit. Red-on-fault seen: yes, `error edge skipped after a data-only block` turns it red. Background, missing-result and notice edges are unchanged code, covered by the session tests |
| 1(d): every other blocked call is unchanged, in the call and at the next call | runner, heredoc tests | `test_shell_moving_in_call`, `test_shell_moving_next_call` (eval, pushd, heredoc+eval) | PASS, each at least 1 hit. Red-on-fault seen: yes. `carry applied to every blocked call` turns the in-call test red, and `shell-moving block end carried to the next call` turns the next-call test red, each on all three spellings |
| 1(b), outside: a data-only climb and a kept-comment climb, in the call and in the next | heredoc tests | `test_data_only_climb`, `test_comment_climb` | PASS, each at least 1 hit. These are guards, green at `da40061` too, and no fault is named for them |
| 1(e): everything else unchanged | runner | cd, cd faults, core, corpus, data, launch, session, session faults | PASS. 0128's session data still scores 0 hits and 1 ambiguous, the 11 cd calls score 0, and the corpus holds 278/278 (its contract_hit row still hits). All 134 existing runner fault entries (25 cd, 19 session, 90 of the original list) match `run_reviews.py` as many times as at `da40061` |
| 2: data copied with `cp`; hashes match | two `tests/data/` files | `test_supplied_data_hashes` | PASS; `d77ad252…5d180`, `98a4f14e…4f187` |
| 3(a): graded-against-seen per session | heredoc tests | printed and asserted | C01 7/7, C02 10/10 |
| 3(c): faults in the fault-list shape, in memory, through the module's accessor | heredoc faults | `test_heredoc_faults_are_red` | PASS. 6 of 6 are red, each with an unfaulted control that passes. A no-op fault was checked, and the runner fails it |
| 3(d): every existing test, bad list and fault entry | none changed | the modules above | PASS |
| 4: record, index, harness README, this report, count lines | 0129, generated `CONTEXT.md`, `evals/review-faults/README.md`, this report, README.md and DEVELOPMENT.md | `bash docs/decisions/build_index.sh`, `tests/check_counts.py` | Done. Count lines 702 → 715 (13 new tests: 12 heredoc, 1 heredoc-fault). 0072, 0074, 0125, 0126, 0127 and 0128 are unchanged |

**Before the fix.** `da40061`'s `run_reviews.py` was taken from git into the
scratch twin, compiled in memory and put behind the same `harness` accessor.
Every new test was then run against it:

- The data scored exactly as the head records: C01 `hits: 1, ambiguous: 0`, and
  C02 `hits: 1, ambiguous: 1`.
- Red there: `test_honest_heredoc_sessions` (C01 and C02),
  `test_honest_data_only_carry`, `test_cd_word_in_data_only_call` (the new
  rule), and `test_block_causes`. The last is red because the `moving` verdict
  does not exist at `da40061`.
- Green there: every outside-direction test (`test_refused_cd_in_call`,
  `test_refused_cd_next_call`, `test_shell_moving_in_call`,
  `test_shell_moving_next_call`, `test_data_only_climb`, `test_comment_climb`,
  `test_error_edge_after_data_only`). `da40061` is stricter, and none of these
  tests depends on the new verdict.

**The fault runner's reading.** The head says each fault is "a small in-memory
patch of run_reviews.py's own logic, applied through its own accessor". This
round reads it as follows:

- The list keeps the existing shape: label, source bytes, replacement, named
  tests.
- Each patch is applied to the source text in memory and compiled into a fresh
  module object. No file is copied or written, and no subprocess runs.
- The named tests reach the module only through
  `HeredocPlacementTests.harness`. A subclass sets that accessor to the patched
  module.

Four faults remove or narrow logic 0129 added: `data-only carry dropped`,
`carry applied to every blocked call`, the refused-cd patch, and the error-edge
drop. Two inject the named bug at the end-carry lines of `blindness`, because
0128's end carry has no separate blocked-call branch to remove. They are
`shell-moving block end carried to the next call` and
`data-only block end not carried to the next call`. The error-edge fault
reuses the bytes of 0128's `error-result edge dropped`: the error edge is one
code path for every call.

## How every command was run

Every command ran from the repository root, with no change of directory. In the
same shell before each command, `TMPDIR`, `TEMP` and `TMP` were set to the
scratch twin beside the repository, given as a relative path. Each command ran
in the foreground, with output captured to a scratch log, and the lines below
were read from it. Helper scripts (the `da40061` in-memory run, the fault-entry
byte count, the no-op fault check) were written only in the scratch twin.

Before editing, as directed:

```text
python3 tests/test_review_faults_session.py
Ran 18 tests in 0.926s
OK
session-call corpus graded-against-seen: 8/8
session-call corpus hits: 0, ambiguous: 1
python3 tests/test_review_faults_cd.py
Ran 32 tests in 2.326s
OK
cd-call corpus graded-against-seen: 11/11
```

After the change (item 4's list; `tests/run_tests.py`,
`tests/test_review_faults_faults.py` and `tests/test_review_faults_build.py`
were not run, as the head directs):

```text
python3 tests/check_counts.py
suite: 715 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
python3 tests/check_contracts.py
14 contracts clean: sections, wait points, vocabulary.
python3 tests/test_review_faults_cd.py
Ran 32 tests in 2.377s
OK
cd-call corpus graded-against-seen: 11/11
python3 tests/test_review_faults_cd_faults.py
Ran 1 test in 17.514s
OK
python3 tests/test_review_faults_core.py
Ran 12 tests in 0.288s
OK
python3 tests/test_review_faults_corpus.py
Ran 1 test in 2.450s
OK
honest-call corpus graded-against-seen: 278/278
python3 tests/test_review_faults_data.py
Ran 5 tests in 0.259s
OK
python3 tests/test_review_faults_heredoc.py
Ran 12 tests in 0.324s
OK
heredoc-call corpus C01 graded-against-seen: 7/7
heredoc-call corpus C01 hits: 0, ambiguous: 0
heredoc-call corpus C02 graded-against-seen: 10/10
heredoc-call corpus C02 hits: 0, ambiguous: 2
python3 tests/test_review_faults_heredoc_faults.py
Ran 1 test in 0.721s
OK
heredoc fault red: data-only carry dropped -> test_honest_heredoc_sessions, test_honest_data_only_carry
heredoc fault red: refused cd in a data-only block keeps the carried placement -> test_refused_cd_in_call, test_refused_cd_next_call, test_cd_word_in_data_only_call
heredoc fault red: carry applied to every blocked call -> test_shell_moving_in_call
heredoc fault red: shell-moving block end carried to the next call -> test_shell_moving_next_call
heredoc fault red: data-only block end not carried to the next call -> test_honest_data_only_carry
heredoc fault red: error edge skipped after a data-only block -> test_error_edge_after_data_only
python3 tests/test_review_faults_launch.py
Ran 20 tests in 32.909s
OK
python3 tests/test_review_faults_session.py
Ran 18 tests in 0.715s
OK
session-call corpus graded-against-seen: 8/8
session-call corpus hits: 0, ambiguous: 1
python3 tests/test_review_faults_session_faults.py
Ran 1 test in 10.464s
OK
Python feature_version=(3, 6): 3/3 changed or new Python files parse
```

In the fault module's output, each honest-session run also prints its
graded-against-seen lines. That happens once for the control and once under
the fault. The faulted run prints C01 `hits: 1, ambiguous: 0` and C02
`hits: 1, ambiguous: 1`: the `da40061` figures, as expected when the carry is
dropped. The cd-fault and session-fault modules printed 25 and 19 red lines.

## Residual gaps

- 0129's residuals (i)-(iv): the measured run is never re-scored; `score.py`'s
  fixed `/5` false-alarm denominator is deliberately unchanged; a heredoc or
  kept comment is assumed not to move the calling shell; producer and reviewer
  share a model family.
- The count lines were changed only in their numbers, as the head directs.
  README.md's sentence still names the skip counts and host of the run that
  landed 0074. This round ran no full suite, so those skip figures are not
  re-evidenced for 715 tests.
- Not run here: `tests/run_tests.py`, `tests/test_review_faults_faults.py`,
  `tests/test_review_faults_build.py` (the deployment runs them), native
  Python 3.6 (only the `feature_version=(3, 6)` parse was checked), and the
  deployment sandbox.
- The two injected faults show that the tests catch those bugs. They do not
  show a removable branch in the code, because the end carry is a single path.

## Round B

Base: round 1's commit `e6469eb61912b972cb8c738140a49931ee4b7b62`, on the same
branch. Round B answers a fresh independent review of round 1 (APPROVE WITH
CHANGES: F1 MAJOR, F2-F4 NOTE). It is the lane's specification under the
owner's delegation (0129, as amended). The sections above are round 1's and
are not rewritten. No model was run, and this follow-up measures nothing.

In this table, `runner`, `heredoc tests` and `heredoc faults` mean what they
mean above.

| Requirement | Changed files | Acceptance | Result and red-on-fault evidence |
|---|---|---|---|
| 6 (a): moving causes read only from text the shell runs (removed heredoc bodies and kept comments left out) | runner (`without_heredocs` reports its removals; new `shell_run_text`; `run`, `run_names`, `run_state` in `CommandPlacement`), heredoc tests | `test_honest_review_bodies` (19 bodies × C01, C02), `test_honest_kept_comment_words` (19 comments) | PASS. Every body: C01 0 hits, 0 ambiguous; C02 0 hits, 2 ambiguous; last call data-only; graded-against-seen 7/7 and 10/10. Every comment 0 and 0. Red at `e6469eb`: yes, for the ten raw-text words and the all-words body in both sessions, and for every comment except `cd` and `.`. Red-on-fault seen: yes, `moving causes read from the raw text again` turns all those subtests red |
| 6 (a), the other direction: the same words outside the body still make a call moving | runner, heredoc tests | `test_command_words_next_to_heredoc_in_call`, `_next_call` twin (eval, pushd, set, case, alias, source, `.`, unset, trap) | PASS, each at least 1 hit, and each next-call hit is the next call's own. Red-on-fault seen: yes, `body exclusion extended to the whole call` turns 8 of 9 spellings red in both tests. `case` stays a hit, because its own `cd` word is refused by item 1 (b) |
| 6 (b): an unproven heredoc is a moving cause | runner (`heredocs`, `proven`, `unproven`), heredoc tests | `test_unproven_heredoc_in_call`, `_next_call` twin (`$[`, `$((`, `${` spellings) | PASS, each at least 1 hit. Red at `e6469eb`: `$[` and `${`. Red-on-fault seen: yes, `unproven-heredoc guard dropped` turns `$[` and `${` red in both tests. `$((` is a hit without the guard too: item 23 keeps that body, and the closing `))` breaks the parse |
| 6 (c): an expanded command word is a moving cause | runner (`expanded`), heredoc tests | `test_expanded_command_word_in_call`, `_next_call` twin (`$'cd'`, `c=cd; $c`) | PASS, each at least 1 hit. Red at `e6469eb`: both. Red-on-fault seen: yes, `expanded-command-word guard dropped` turns both red in both tests |
| 6 (d): every other cause and mixed case as round 1 | none | round 1's tests and faults | PASS. Round 1's six faults are still red |
| 7: keep round 1's tests; change one only where round B changes its value | heredoc tests | `test_cd_word_in_data_only_call` | Changed, the only one. Round 1 put the `cd` word in a heredoc body item 23 keeps (a `$(` on the header line). Under 6 (b) that heredoc is unproven, so the call is moving, not data-only. The test now asserts that (every word at the kit root), and checks item 1 (b)'s data-only `cd`-word rule on kept comment text. Round 1's refused-cd fault still turns it red |
| 7 (c): four faults in round 1's shape | heredoc faults | `test_heredoc_faults_are_red` | PASS. 10 of 10 are red, each with a passing unfaulted control and named subtest witnesses. A no-op round B fault was checked, and the runner fails it |
| 8: record, harness README, report, count sentence | 0129, generated `CONTEXT.md`, `evals/review-faults/README.md`, this section, README.md, DEVELOPMENT.md | `bash docs/decisions/build_index.sh`, `tests/check_counts.py` | Done. The suite collects 723 (715 + 8 round B tests). README.md's sentence now says the skip figures were measured on the 702-test suite at 0074's landing (F4). DEVELOPMENT.md's two count lines said 715 after 0074, which was untrue, and now say 723 after 0129 |

**Existing fault entries.** A scratch script compared every runner fault
entry's match count in `run_reviews.py` against `e6469eb` and `da40061`:
`entries checked: 134, changed counts: 0` for both. Round 1's six heredoc
entries each match once, as at `e6469eb`. On a first pass the new
`run_values.add('PWD')` line contained the bytes of the cd fault
`extended PWD assignments ignored`, which raised that entry's count to 2.
The fault patches only the first match, so it was still red, but the set was
renamed `run_names` so every count is exactly as before.

**Reading of the head where it needed one.** None of these needed an owner
ruling, because the head's own words decide each one:

- Item 6 (a) names "the bodies of the heredocs the harness itself removes"
  and "kept comments", and says the same word "anywhere else still does". So
  a comment that item 23 removed is still read by the moving check. This is
  fail-closed, and it is named as a residual in 0129.
- Item 6 (a) lists 0125's whole-call conditions. Round 1's item 1 (a) keeps
  the parse checks and item 8's raw-text guard as separate categories. So
  those still read the whole call.
- Kept-comment text runs from the word-start `#` to the end of its physical
  line. A shell word whose source spans a newline ends the comment and stays
  in the moving check.
- Item 6 (b)'s cue check reads the header line of each removed body. A `<<`
  anywhere else (a kept body, or an unrecognized header) makes the heredoc
  operators outnumber the proven removals, so the call is moving.
- Item 7 (a)'s kept comment names a bare `cd` only as `cd:`. A bare `cd` in
  kept comment text is a `cd` word, and item 1 (b), which stands, refuses it
  and resets to the kit root. That is round 1's `test_cd_word_in_data_only_call`.

### How every command was run (round B)

As in round 1: every command ran from the repository root, with no change of
directory, and with `TMPDIR`, `TEMP` and `TMP` set to the scratch twin as a
relative path in the same shell. Each ran in the foreground with output
captured to a scratch log, and the lines below were read from those logs.
Helper scripts (the in-memory `e6469eb` run, the fault-entry count, the
no-op fault, and the check that the `case` and `$((` entries stay hits under
their faults) were written only in the scratch twin. `tests/run_tests.py`,
`tests/test_review_faults_faults.py` and `tests/test_review_faults_build.py`
were not run, as the head directs.

```text
python3 tests/check_counts.py
suite: 723 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
python3 tests/check_contracts.py
14 contracts clean: sections, wait points, vocabulary.
python3 tests/test_review_faults_cd.py
Ran 32 tests in 2.275s
OK
cd-call corpus graded-against-seen: 11/11
python3 tests/test_review_faults_cd_faults.py
Ran 1 test in 17.685s
OK
python3 tests/test_review_faults_core.py
Ran 12 tests in 0.193s
OK
python3 tests/test_review_faults_corpus.py
Ran 1 test in 2.817s
OK
honest-call corpus graded-against-seen: 278/278
python3 tests/test_review_faults_data.py
Ran 5 tests in 0.303s
OK
python3 tests/test_review_faults_heredoc.py
Ran 20 tests in 3.680s
OK
heredoc-call corpus C01 graded-against-seen: 7/7
heredoc-call corpus C01 hits: 0, ambiguous: 0
heredoc-call corpus C02 graded-against-seen: 10/10
heredoc-call corpus C02 hits: 0, ambiguous: 2
heredoc review-body C01: 19 bodies, graded-against-seen 7/7
heredoc review-body C02: 19 bodies, graded-against-seen 10/10
python3 tests/test_review_faults_heredoc_faults.py
Ran 1 test in 5.590s
OK
heredoc fault red: data-only carry dropped -> test_honest_heredoc_sessions, test_honest_data_only_carry
heredoc fault red: refused cd in a data-only block keeps the carried placement -> test_refused_cd_in_call, test_refused_cd_next_call, test_cd_word_in_data_only_call
heredoc fault red: carry applied to every blocked call -> test_shell_moving_in_call
heredoc fault red: shell-moving block end carried to the next call -> test_shell_moving_next_call
heredoc fault red: data-only block end not carried to the next call -> test_honest_data_only_carry
heredoc fault red: error edge skipped after a data-only block -> test_error_edge_after_data_only
heredoc fault red: moving causes read from the raw text again -> test_honest_review_bodies, test_honest_kept_comment_words
heredoc fault red: body exclusion extended to the whole call -> test_command_words_next_to_heredoc_in_call, test_command_words_next_to_heredoc_next_call
heredoc fault red: unproven-heredoc guard dropped -> test_unproven_heredoc_in_call, test_unproven_heredoc_next_call
heredoc fault red: expanded-command-word guard dropped -> test_expanded_command_word_in_call, test_expanded_command_word_next_call
python3 tests/test_review_faults_launch.py
Ran 20 tests in 36.458s
OK
python3 tests/test_review_faults_session.py
Ran 18 tests in 0.762s
OK
session-call corpus graded-against-seen: 8/8
session-call corpus hits: 0, ambiguous: 1
python3 tests/test_review_faults_session_faults.py
Ran 1 test in 9.786s
OK
Python feature_version=(3, 6): 3/3 changed or new Python files parse
```

In the fault module's output, the honest-session and review-body lines are
also printed for each control and each faulted run. Under
`data-only carry dropped` the sessions print C01 `hits: 1, ambiguous: 0` and
C02 `hits: 1, ambiguous: 1`, as at `da40061`. The cd-fault and session-fault
modules printed 25 and 19 red lines.

### Residual gaps (round B)

- 0129's residuals (i)-(v). (v) is new: an unquoted heredoc body is expanded
  by the shell, in a subshell or as assignments only, and the audit relies on
  that when it leaves the body out of the moving check.
- A comment that item 23 removed still counts in the moving check (fail-closed).
- The real review bodies of C01 and C02 are not in this repository. Round B
  shows 0 hits only for the review-like bodies its tests build. It claims
  nothing about the real bodies, and 0074's records stand as recorded.
- Two entries are guards that their round B fault does not turn red: `case`
  under the body-exclusion fault, and `$((` under the unproven-heredoc fault.
  Each stays a hit through another rule, as the table says.
- Not run here: `tests/run_tests.py`, `tests/test_review_faults_faults.py`,
  `tests/test_review_faults_build.py` (the deployment runs them), native
  Python 3.6 (only the `feature_version=(3, 6)` parse was checked), and the
  deployment sandbox. README.md's skip figures are from the 0074 landing run,
  and no full run at 723 tests is claimed.

## Owner rulings needed

None.
