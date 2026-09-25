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

## Owner rulings needed

None.
