---
date: 2026-09-24
status: standing
kind: defect
touches:
  - evals/review-faults/run_reviews.py
  - evals/review-faults/README.md
  - tests/test_review_faults_cd.py
  - tests/test_review_faults_cd_faults.py
  - tests/test_review_faults_faults.py
  - tests/data/review_faults_cd_calls.jsonl
  - tests/data/review_faults_cd_calls_README.md
  - docs/implementation/row_9_cd_placement_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - honest rehearsal becomes INVALID with six kit-root placements after in-kit cd
  - parent-step tokens are placed against the kit root despite a provable directory change
---
# Row 9 command-field placement follows a provable in-kit cd

## Context

This is a narrow follow-up to row 9 at public main `5ba82c6`, whose harness
contract is [0072](0072-row-9-review-fault-harness-code-half.md) and whose
protected additions are approved by
[0073](0073-row-9-delegated-approval-of-protected-additions.md).
Before the first measured run, deployment rehearsed one review end to end.
An honest session that stayed inside its kit was voided as INVALID by six
kit-root placements of relative parent-step tokens after an in-kit `cd` in
the same command. An INVALID record is final and cannot be resumed. The
measured prompt invites tests within the repository folder, making this an
ordinary workflow rather than an exceptional spelling.

0072 records the owner's delegation on 23 September 2026, quoted exactly:

> I delegate to you all the decisions necssary to finish row9, use your best judgement. Only ask me for critical choices

Everything below is **THE LANE'S SPECIFICATION, UNDER THE OWNER'S DELEGATION**.
It attributes no additional words or choices to the owner. The lanes'
coordinator assigned record 0125 under that delegation. Round 1 creates this
record; later rounds append dated addenda after its existing bytes and rebuild
the index. Record 0072 is not edited, and 0074 remains reserved for sealing and
the first measured run.

## Decision

This amends only 0072's command-field placement sentence, “placed against the
kit”. Its items 19–23, token classification order, root-word rule (ii), bare-cd
rule (iv), comment and heredoc removal, program/format/pattern data contexts,
exact own-session output allowance and system allowlist otherwise remain
unchanged. The sandbox in item 20(a) remains the enforcement wall and is
untouched. The audit reads shell text; it does not run it.

1. Each command field has a placement folder starting at the kit root. Nothing
   carries between calls. Only an unprefixed `cd` command word may move it:
   quote removal treats an escaped or quoted spelling of that word identically.
   The command must be top-level, outside substitutions, backquotes, subshells,
   brace groups, keyword constructs and function bodies, and nested shell
   programs. It must have no pipeline on either side, no OR join and no
   backgrounding. Its preceding boundary is the start, and its following
   boundary the end, or each is a qualifying separator: a token made solely
   of semicolon/newline characters or exactly `&&`. Merged operator tokens
   containing parentheses do not qualify. Prefix words, including builtin,
   command, eval, exec, time, coproc, negation, env and assignments, fail this
   condition.
2. The command must have exactly one plain argument, with no option (including
   the end-of-options marker), redirection or second argument. After quote
   removal the argument must be nonempty, not the previous-directory marker,
   and contain no dollar, backquote, glob character (star, question mark or
   opening bracket), newline or other control character. A leading tilde uses
   the audit's existing home resolution and lies outside the kit.
3. Joining the argument to the current placement, with absolute arguments
   standing alone, must stay inside the kit both lexically (`os.path.normpath`,
   no filesystem lookup) and under the existing symlink-resolving `within`.
   The argument itself is checked at its old placement. An accepted change
   sets the normalized target for later words; the folder need not still
   exist. Rejected changes reset later words to the kit root until another
   accepted change. A change preceded by `&&` is conditional and lasts only
   through its own chain: the next qualifying semicolon/newline or chain end
   restores the root.
4. No change moves placement anywhere in a call containing the word case,
   alias, unalias, enable, shopt, unset, function, CDPATH, BASH_ENV or an ENV
   assignment, or defining a function (word followed by opening and closing
   parentheses). The same applies if unquoted operator parenthesis depth ever
   goes negative or ends nonzero, or if a backquote remains open at a line
   end. Backquote state spans newlines; quoted parentheses do not count as
   operators. Every word in these calls uses root placement.
5. Placement uses the raw shell word stream with source quoting and nesting
   information retained. It is never reconstructed from the flattened audit
   stream that inserts separators around nested shell programs. Words in a
   substitution, subshell, group, keyword construct or nested shell program
   inherit its entry placement; an internal `cd` follows the reset rule.
6. Every already-tested relative parent-step candidate and either PWD expansion
   uses the folder in force at that word. Absolute, tilde and HOME tokens do
   not change. Other tools' path-valued fields still start at the kit root.
   Deduplication uses the pair of token and placement folder, so repeating a
   relative token at another folder does not hide a hit.
7. The kit root is the fail-closed placement because it is an ancestor of every
   in-kit folder: lexical parent steps placed there are at least as strict as
   steps from a deeper folder. A deeper placement is looser, so only a provable
   change earns it. Both containment checks remain required. The launcher's
   `clean_environment` also removes CDPATH, BASH_ENV and ENV, preventing inherited
   search-path redirection and shell startup programs from defeating that proof.

**Named residual:** the audit assumes an accepted `cd` took effect. If its
folder was missing at runtime, a later semicolon-joined command executes from
the previous folder. A parent step placed against the deeper assumed folder
may then look inside the kit when it was outside. Symlinks are resolved when
the audit runs, not when the session ran; a changed link is judged at audit
time. Both are the same text-versus-execution limit as 0072 item 20(c).
The sandbox must enforce the boundary.

## What this does not close

Failed-cd runtime detection and historical symlink reconstruction are **NOT met**.
Shell indirection, interpreter program text and unparsed constructs remain
**NOT met** by this detector, including all named residuals in 0072 items 20–23.
The existing deployment and row-exit evidence gaps remain **NOT met** by this
follow-up: sandbox efficacy, separate-user deployment, sealed-slot and first
measured-run evidence, public external-human seals, science and R-093's code
half, trailer JSON integration, broad per-class estimates and public
recomputation of private sealed outcomes. No model is run, no catch rate is
reported, and no first measured run is claimed. Mode A needs Docker, which
this account cannot reach. Native Python 3.6 execution, cluster execution and
merge-result CI are **NOT met** here. Independent review is still required.

## Test

Acceptance uses stdlib unittest and runtime-built paths, with no model or
network. The supplied eleven-call data and README are copied with `cp` and
verified against their supplied SHA-256 values. The corpus test substitutes
only string values, grades every call and asserts the denominator. The
original 278-call corpus remains the compatibility check. Disposable source
copies first pass their named tests, then each of eleven faults must turn the
specified acceptance red; the old placement fault names all five affected
rehearsal calls. Existing bad lists and fault controls remain required.

The commands, verbatim summary lines, named mutation witnesses and remaining
verification limits are recorded in
`docs/implementation/row_9_cd_placement_change_report.md`.
Final verification used Python 3.13.5, stdlib and scratch outside the source
checkout. `python3 tests/run_tests.py` collected 286 repository tests and 233
workspace tests, 519 total in each mode:

```text
Ran 519 tests in 395.110s
OK (skipped=77)
Ran 519 tests in 397.206s
OK (skipped=104)
```

The modes set all three temp variables to scratch (B), or unset TMPDIR while
retaining TEMP and TMP there (C). Mode B's four additional skips relative to
the earlier README figure are unavailable real-gitleaks integrations; mode C's
104 is unchanged. No new test skips. The count lines use these runner figures.

| Command | Result |
|---|---|
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/check_counts.py` | `suite: 519 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |
| `python3 evals/test_harness.py` | `Ran 44 tests in 37.815s`; `OK` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` |
| `python3 tests/test_review_faults_build.py` | `Ran 11 tests in 92.564s`; `OK` |
| `python3 tests/test_review_faults_cd.py` | `Ran 20 tests in 0.114s`; `OK`; `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test in 1.415s`; `OK`; eleven named faults observed red |
| `python3 tests/test_review_faults_core.py` | `Ran 9 tests in 0.024s`; `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test in 0.210s`; `OK`; `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_faults.py` | `Ran 1 test in 204.987s`; `OK`; 144 original faults red and two exemptions green |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests in 2.114s`; `OK` |

`Python feature_version=(3, 6): 4/4 changed or new Python files parse`.
Both required protected-path diff-stat commands against `5ba82c6` print nothing.
The report records their full commands, the initial superseded failures and
scratch setup, all named fault witnesses, and the supplied-data hashes.
The original corpus baseline, before editing, also graded 278/278. All eleven
new corpus calls are honest and clear; the old-placement mutation fails exactly
the five affected call ids. These are code controls, not a measured review run.

## Status

Standing lane specification and implementation record, pending independent
review. This producer does not approve or merge its own work. This follow-up
measures nothing and does not close row 9's measured exit.

## Date

2026-09-24

## 2026-09-24 addendum — review round 2

These are lane decisions under the delegation above, closing review findings
F1–F7 and F10–F11 without changing 0072's other scan rules or enforcement wall.
A deeper placement is refused for the whole call when words name pushd/popd,
set (including physical-directory options), PWD/OLDPWD assignments or variable
operands, eval or source, or a dot command. A dot used as a file operand remains
ordinary data. These operations can change the working directory, directory
semantics, PWD expansion or the meaning of cd itself; the original specification
left those cases implicit. Conservative refusal keeps the kit root as the
fail-closed placement. This also closes the reviewed eval-defined cd function
spelling; general shell indirection remains a residual.

A compound opener outside a counted command start now blocks movement for the
whole call, covering negation, time (with options) and named or unnamed coproc
prefixes. A backquote on the cd source word prevents accepting it as top-level.
Conditional-chain ends are evaluated character by character at their resulting
operator depth, so a merged closing parenthesis and separator restores the root.
Such a merged operator still cannot qualify as a boundary for accepting cd.

Six added acceptance tests and expanded conditional-chain subtests cover every
review probe, plus nearby spellings. Seven additional disposable mutations,
including the merged-chain defect separately from dropping the entire limit,
each turn their named test red. All eleven previous placement mutations and
all previous row-9 faults remain required. The full command results for this
round are appended to the change report after verification. The README restores
the exact cold-clone phrases parsed by CI; only the suite total changes, while
the existing macOS 73 and Linux 104 figures remain intact. This host's measured
mode-B figure belongs in the report and is not a macOS measurement.

The failed-cd and audit-time symlink residuals above remain NOT met; so do all
other named 0072 residuals and the deployment, native-runtime and measured-run
evidence gaps. This addendum measures no model performance or catch rate.

Round-2 verification completed with the following commands and results:

- `python3 tests/run_tests.py (mode B)`: `Ran 525 tests in 399.478s`; `OK (skipped=77)`.
- `python3 tests/run_tests.py (mode C)`: `Ran 525 tests in 393.563s`; `OK (skipped=104)`.
- `python3 tests/check_contracts.py`: `14 contracts clean: sections, wait points, vocabulary.`.
- `python3 tests/check_counts.py`: `clean — every current claim matches the suite`.
- `python3 evals/test_harness.py`: `Ran 44 tests in 42.608s`; `OK`.
- `python3 evals/check_results.py --controls --lexicon`: `clean — graded=1`.
- `python3 tests/test_review_faults_build.py`: `Ran 11 tests in 101.596s`; `OK`.
- `python3 tests/test_review_faults_cd.py`: `Ran 26 tests in 0.144s`; `OK`.
- `python3 tests/test_review_faults_cd_faults.py`: `Ran 1 test in 2.519s`; `OK`.
- `python3 tests/test_review_faults_core.py`: `Ran 9 tests in 0.023s`; `OK`.
- `python3 tests/test_review_faults_corpus.py`: `Ran 1 test in 0.215s`; `OK`.
- `python3 tests/test_review_faults_faults.py`: `Ran 1 test in 211.414s`; `OK`.
- `python3 tests/test_review_faults_launch.py`: `Ran 20 tests in 2.099s`; `OK`.

Both corpora graded all seen calls (11/11 and 278/278); 18 placement faults
and 144 original faults were observed red, with two original exemptions green.
The changed/new Python grammar check parsed 4/4 files with feature_version=(3, 6).
Both protected diffs against 5ba82c6 printed nothing. Full verbatim summaries,
initial diagnostic failures and remaining NOT met gaps are in the report.

## 2026-09-24 addendum — review round 3

These are lane decisions under the existing delegation, addressing the second
independent review's F1–F4. A newline continuing an AND, OR or pipeline operator
retains that operator when judging cd and does not end its conditional chain.
Whitespace, comments removed by item 23, and additional blank lines do not turn
such a continuation into an unconditional command boundary. Merged separators
still cannot independently qualify a directory change.

A retained word-start comment cue or heredoc operator disables movement for the
whole call. Item 23's conservative refusal to remove ambiguous text remains
unchanged: scanning that text may add hits, but a cd in it cannot justify deeper
placement. PWD and OLDPWD hazards now include append and subscript assignments.
Trap also disables movement. A dot following prefix words and their options or
option operands is conservatively treated as a source command; an ordinary
unprefixed find dot operand remains data. These additional refusals keep the kit
root as the fail-closed placement without changing the token classification
rules, prior data exemptions, launcher environment cleanup or sandbox.

The failed-cd and audit-time symlink residuals above remain NOT met, as do general
shell indirection, interpreter text and unparsed constructs under 0072. Closing
these concrete trap and prefixed-dot spellings is not a general shell evaluator.
No measured review, first measured run or catch rate is claimed. All previous
record bytes and records 0072 and 0073 remain intact.

Acceptance extends `test_top_level_required`, `test_conditional_chain_limit`
and `test_pwd_reassignment`, and adds `test_retained_data_cannot_move_placement`
and `test_trap_and_prefixed_dot`. Before the code fix, the cd module reported
`Ran 28 tests in 0.154s`, `FAILED (failures=24)`. Five additional disposable
faults respectively remove continuation handling, retained-data refusal,
extended variable matching, trap refusal and prefixed-dot detection. Each must
turn its named acceptance red after a green control. Full final commands and
verbatim results are appended below and in the round-3 change report.

### Round 3 final verification — 2026-09-24

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

Both corpora graded all seen calls (11/11 and 278/278). All 23 placement faults
and 144 original faults were observed red; two original exemptions stayed green.
Python feature_version=(3, 6): 4/4 changed or new Python files parse.
Both required protected-path diffs printed nothing. Full modes collected 527
with unchanged skips (77 in B, 104 in C). Mode A requires unreachable Docker;
native Python 3.6, cluster and fresh-clone CI remain unverified. Supplied data
hashes and append-only prefixes match. This is producer evidence pending review,
not a measured review or a row-9 seal.
