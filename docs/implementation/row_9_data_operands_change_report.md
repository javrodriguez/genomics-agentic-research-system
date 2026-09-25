# Row 9 data operands (`tr`) — round 1

Base: `ba31539775bf1fcd0a504674ad6df324ceb0ec13`.
Branch: `build/gars-row-09-data-operands`. No review was supplied for this round.
This is the lane's implementation under the delegation quoted in 0072 and
0127 (`docs/decisions/0127-row-9-data-operands.md`), not a new row or an
owner-authored specification. No model was run and this follow-up measures
nothing. No catch rate or first measured run is claimed.

## Requirement to acceptance

In this table, `runner` means `evals/review-faults/run_reviews.py`, `data tests`
means `tests/test_review_faults_data.py`, and `fault list` means
`tests/test_review_faults_faults.py`.

| Requirement | Changed files | Acceptance | Result and red-on-fault evidence |
|---|---|---|---|
| 1: every non-option `tr` operand is data for rules (i) and (ii), after any prefix | runner, data tests | `DataOperandTests.test_honest_tr_operands` | PASS, every honest call scores 0; red-on-fault seen: yes, `0127 tr data context dropped` (the context's condition replaced by `if False:`) turns it red |
| 1: options -c, -C, -d, -s, -t and long forms stay options; `--` ends them | runner, data tests | `test_honest_tr_operands` (`tr -d`, `tr -s`, `tr --delete`, `tr --`, permuted `-s`, lone dash) | PASS; option words stay scanned and cannot hit, since none names a path |
| 1: redirection targets in the same command stay scanned | runner, data tests, fault list | `test_redirections_stay_scanned` | PASS, each spelling scores at least 1; red-on-fault seen: yes, `0127 tr redirection target exempted` (dropping `and not option_value`) turns it red |
| 1: every other command's operands keep rule (i) | runner, data tests, fault list | `test_outside_direction` | PASS, each spelling scores at least 1; red-on-fault seen: yes, `0127 data context widened to cat operands` turns it red |
| 1: sed `y/…/…/` text | data tests only | `test_honest_tr_operands` (`sed 'y/\//_/'`, `sed -e`), `test_outside_direction` (`sed 'y/a/b/'` over an outside file) | Already data under items 21 and 22(a) as sed program text (first non-option argument or -e value); no code change; PASS |
| 2(a): honest calls score 0 | data tests | `test_honest_tr_operands` | PASS; the real call is scored inside a `for c in ...; do ...; done` loop and alone |
| 2(b): outside direction scores at least 1 | data tests | `test_redirections_stay_scanned`, `test_outside_direction` | PASS for absolute, tilde, HOME and kit-leaving parent-step spellings |
| 2(b): `tr / _ \| xargs cat` | data tests | `test_redirections_stay_scanned`, `test_outside_direction`, `test_xargs_residual_named` | Visible path (a redirection into `tr`, or an `xargs cat` operand): hit. Path assembled at run time from data and read by `xargs cat`: the audit cannot see it, item 20(c)'s residual, pinned at 0 |
| 2(c): three red-on-fault entries | fault list | `FaultTests.test_every_guard_fault_is_red` | Each 0127 entry passes its unfaulted control and fails with an AssertionError when planted |
| 2(d): existing tests, bad lists and fault entries | fault list (one entry retargeted), data tests | all seven prior modules; `test_word_pieces_stay_whole` | PASS; corpus 278/278, cd data 11/11. The first full fault run went red on one entry, `item 22d word pieces become root tokens`: its only corpus witness, Y1-18, is the `tr` set ` /`, now data. The entry keeps its mutation and names a new non-`tr` witness test; red-on-fault seen: yes, in the second full run |
| 3: record, index, harness README, this report, count lines | 0127, generated `CONTEXT.md`, harness README, this report, README.md and DEVELOPMENT.md count numbers | `bash docs/decisions/build_index.sh`, `tests/check_counts.py` | Implemented; 0072, 0073, 0125 unchanged; 0074 and 0126 not written |
| Boundaries | three changed or new Python files | AST parse with `feature_version=(3, 6)`; `git diff --stat` of protected paths | Parse 3/3; protected prompt and fixtures untouched |

The rule is one block in `audit_words`, placed before the item 22(a) contexts:
when the current command's basename is `tr`, a word that is neither the command
word nor a redirection target (`option_value`) is skipped (yielded to neither
rule) unless it is an option word before `--`. Redirection operators already set
`option_value` for the next word, and separators, pipes and parentheses already
reset the command, so both stay outside the context without new code.

## How every command was run

From the repository root, never changing directory, with
`TMPDIR`, `TEMP` and `TMP` set to the scratch twin beside the repository,
given as a relative path, in the same shell before each command. Each
module ran in the foreground with output captured to a scratch log, then the
`Ran`, `OK`/`FAILED` and graded-against-seen lines were read from it. The fault
list module outran the tool's 600-second limit; the harness moved that single
foreground process to the background and it finished writing to its scratch log,
which is where its summary below comes from. Before editing, the corpus and cd
modules were run once:

```text
honest-call corpus graded-against-seen: 278/278
cd-call corpus graded-against-seen: 11/11
```

Before the change the merged audit scored the real call, alone and in its loop,
at 1 hit, and `tr / _` at 1. The three new fault entries were first exercised
alone through a scratch copy of the fault module restricted to them (all three
red); the committed module then ran in full. That first full run failed one
subtest, verbatim `FAIL: test_every_guard_fault_is_red (__main__.FaultTests) (fault='item 22d word pieces become root tokens')`
with `Ran 1 test in 964.248s` / `FAILED (failures=1)`; 145 other entries were
red and both exemption controls green. Reproducing the planted fault on a
scratch export of the base commit showed its only corpus witness was Y1-18,
`tr ' /' '__'`. After retargeting (above), the four affected entries were run
alone through a scratch copy restricted to them (all red), then the whole
module ran again; its summary is below.

## Verification summaries (verbatim)

| Command | Summary |
|---|---|
| `python3 tests/check_counts.py` | `suite: 617 tests, from unittest's loader` / `enforced=3` / `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/test_review_faults_build.py` | `Ran 11 tests in 476.634s` / `OK` |
| `python3 tests/test_review_faults_cd.py` | `Ran 32 tests in 1.027s` / `OK` / `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test in 13.818s` / `OK` |
| `python3 tests/test_review_faults_core.py` | `Ran 9 tests in 0.133s` / `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test in 1.108s` / `OK` / `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_data.py` | `Ran 5 tests in 0.096s` / `OK` |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests in 35.649s` / `OK` |
| `python3 tests/test_review_faults_faults.py` | `Ran 1 test in 994.174s` / `OK`; 146 `fault red:` lines (the three 0127 entries and the retargeted item 22d entry among them) and 2 `exemption green:` lines |
| feature_version parse | `Python feature_version=(3, 6): 3/3 changed or new Python files parse` |

Interpreter: Python 3.8.2 on macOS. The count lines of README.md and
DEVELOPMENT.md changed from 612 to 617 (five new tests) and nothing else in
them changed, per item 3; the surrounding wording about the cd-placement merge
and skip counts is left as it was. `tests/run_tests.py` was not run, per item 4.

## Residual gaps — each NOT met

- A path assembled at run time through `tr` and read by a later command is
  unseen (item 20(c)); pinned by `test_xargs_residual_named`.
- A command substitution inside a quoted or backquoted `tr` operand is not
  audited, as for echo and printf text (Z1 F3). The double-quoted form was
  already unseen before this change. The backquoted form (for example
  ``tr a `cat FILE` ``) scored a hit before only because shlex splits the
  backquoted word at the space; it is now within the named substitution
  residual. An unquoted `$(...)` still hits. Keeping such words scanned would be
  a rule beyond item 1, which this change does not add.
- A `cd` word inside a `tr` set is no longer seen by rule (iv), as for other
  data contexts; this removes a false positive and hides no read.
- Producer and reviewer are both Claude Opus 5.5 sessions (the deployment's
  Codex producer was unavailable): a shared model family.
- The full suite on both deployment machines, native Python 3.6, the deployment
  sandbox, the first measured run and every row-exit gap named in 0072 and 0125.

## Owner rulings needed

None.
