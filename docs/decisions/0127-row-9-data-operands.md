---
date: 2026-09-25
status: standing
kind: defect
touches:
  - evals/review-faults/run_reviews.py
  - evals/review-faults/README.md
  - tests/test_review_faults_data.py
  - tests/test_review_faults_faults.py
  - docs/implementation/row_9_data_operands_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - an honest tr call with a separator in its character set scores a blindness hit
  - a tr set is read as an absolute path or a separator-only word and turns the record INVALID
---
# Row 9 blindness audit treats tr operands as data

## Context

This is a narrow follow-up to row 9 at public main `ba31539`, whose harness
contract is [0072](0072-row-9-review-fault-harness-code-half.md), whose
protected additions are approved by
[0073](0073-row-9-delegated-approval-of-protected-additions.md), and whose
command-field placement is amended by [0125](0125-row-9-cd-aware-placement.md).

Before sealing the first measured run, the deployment re-scored nine real
in-kit review sessions with the merged audit. One honest tool call scored a
hit: `n=$(echo $c | tr '/ ' '__')`, run inside a `for` loop. Rule (i) (0072
item 20(b)(i)) reads the `tr` set `/ ` as an absolute path; a plain `tr / _`
hits rule (ii) as a separator-only word. `tr` never opens a file named by an
operand: its operands are character sets. In the one-shot measured run an
INVALID record is final, so this false alarm must go before sealing.

0072 records the owner's delegation on 23 September 2026, quoted exactly:

> I delegate to you all the decisions necssary to finish row9, use your best judgement. Only ask me for critical choices

Everything below is **THE LANE'S SPECIFICATION, UNDER THE OWNER'S DELEGATION**.
It attributes no words or choices in it to the owner. The lanes' coordinator
assigned record number 0127 under the same delegation. Records 0072 and 0125
are append-only and are not edited; 0074 and 0126 are not written here.

## Decision

1. An operand that the audit's own grammar classifies as data gets neither
   rule (i) nor rule (ii), exactly as 0072 items 21 and 22(a) already treat
   program, pattern and format text. This record adds one such context, by
   principle rather than by spelling: every non-option operand of `tr`,
   recognised on the shell word stream after any prefix command and its
   options, as items 20(b)(iv) and 21 find their commands. `tr` reads standard
   input only and never opens an operand.
2. `tr`'s options are -c, -C, -d, -s, -t and their long forms; `--` ends them.
   Before `--`, every word beginning with a dash (other than a lone dash) is an
   option word and stays scanned, wherever it appears, since none of `tr`'s
   options takes a value. A lone dash and every word after `--` are operands.
3. **What stays scanned.** A redirection target in the same simple command
   (`tr a b < FILE`, `tr a b > FILE`, appends and numbered descriptors) is a file
   the shell opens and keeps rule (i), as the audit already treats redirection
   targets. So does every operand of every other command, including a command
   after a separator or pipe and an unquoted command substitution, whose
   parenthesis operator ends the `tr` context.
4. sed's `y/…/…/` text is already data: it is sed program text under items 21
   and 22(a) (the first non-option argument or an -e value). No code changes
   for it; tests only. sed's input-file operands stay scanned.
5. Rule (iv) reads the same audited stream, so a `cd` word inside a `tr` set is
   data there too, as it already is inside echo, printf and program text.
   Command-field placement (0125) reads raw words and is unchanged.

0072's contract is otherwise unchanged: items 19-23, the root-word rule, the
bare-cd rule, comment and heredoc removal, the other data contexts, the exact
own-session output allowance, the system allowlist and the sandbox wall of
item 20(a). 0125's placement grammar is unchanged.

**How this change was built.** A headless Claude Opus 5.5 session produced it,
and a separate fresh Claude Opus 5.5 session reviews it; the deployment's
Codex producer was unavailable. Producer and reviewer therefore share a model
family, a cost this record names as residual.

## What this does not close

Covered: an honest `tr` call is not made INVALID by its sets; an outside read
by any spelling 0072 items 20-23 and 0125 name still turns INVALID, including a
file `tr` reads or writes through a redirection.

Not covered, each **NOT met** here:

- Everything 0072 and 0125 already name, including item 20(c)'s shell
  indirection, command substitution and interpreter text.
- A path assembled at run time through `tr` and read by a later command (for
  example piped to `xargs cat`) never appears as a token. It is item 20(c)'s
  residual; the test pins this as a zero-hit, named residual. When the path is
  visible (a redirection into `tr`, or an operand of `xargs cat`) it hits.
- A command substitution inside a quoted or backquoted `tr` operand is not
  separately audited, as for echo and printf text (Z1 F3). The double-quoted
  form was already unseen before this change; a backquoted form such as
  ``tr a `cat FILE` `` scored a hit before only because backquotes split the
  word, and is now within the same named residual. An unquoted `$(...)` still
  hits. The sandbox must refuse such reads.
- The shared model family of this change's producer and reviewer.
- The full suite (`tests/run_tests.py`), native Python 3.6, the deployment
  sandbox, the first measured run and every row-exit gap remain outside this
  change. No model is run and no catch rate is claimed.

## Test

Acceptance is stdlib unittest in `tests/test_review_faults_data.py`, collected
by `tests/run_tests.py`, with every outside path built at run time from
`os.sep`, `chr(126)`, `chr(46) * 2` and a split HOME expansion. No shell text is
executed; no model or network is used.

- `test_honest_tr_operands`: the real call inside its loop and alone, `tr / _`,
  `tr -d /`, `tr -s '/' ' '`, `tr -- '/' '_'`, long and permuted options, a
  lone dash, in-kit redirections, pipelines, prefixes, a full-path `tr`, a
  nested shell, and `sed 'y/\//_/'` over an in-kit file each score 0.
- `test_redirections_stay_scanned`: input, output, append and descriptor
  redirections to an absolute, tilde, HOME or kit-leaving parent-step path,
  after `--`, after a prefix, inside the loop, and feeding `xargs cat`, each
  score at least 1.
- `test_outside_direction`: `tr / _` followed by `;`, `&&` or `|` and `cat` of
  each outside spelling, an unquoted substitution, `sed 'y/a/b/'` over an
  outside file, a root listing, and an `xargs cat` operand each score at least 1.
- `test_xargs_residual_named`: the item 20(c) residual above scores 0.
- `test_word_pieces_stay_whole`: a spaced separator inside a longer word of
  another command (a git message, a quoted in-kit name, a `--grep=` value)
  scores 0 under item 22(d).

Red-on-fault, in the existing list of `tests/test_review_faults_faults.py`:
dropping the `tr` context turns `test_honest_tr_operands` red; widening it to
`cat`'s operands turns `test_outside_direction` red; exempting the redirection
target turns `test_redirections_stay_scanned` red. Each first passes on an
unfaulted disposable copy.

One existing entry is retargeted, not removed. `item 22d word pieces become
root tokens` had one witness in the 278-call corpus, call Y1-18, whose word was
the `tr` set ` /`. Under item 1 that set is data, so the planted fault left the
corpus green (observed in the first full run of the fault module here). The
entry keeps its mutation and now names `test_word_pieces_stay_whole`, whose
non-`tr` words witness it red. The corpus itself and its labels are unchanged.

Results on the build host (Python 3.8.2, macOS; scratch outside the checkout),
verbatim:

| Command | Result |
|---|---|
| `python3 tests/check_counts.py` | `suite: 617 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/test_review_faults_build.py` | `Ran 11 tests in 476.634s`; `OK` |
| `python3 tests/test_review_faults_cd.py` | `Ran 32 tests in 1.027s`; `OK`; `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test in 13.818s`; `OK` |
| `python3 tests/test_review_faults_core.py` | `Ran 9 tests in 0.133s`; `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test in 1.108s`; `OK`; `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_data.py` | `Ran 5 tests in 0.096s`; `OK` |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests in 35.649s`; `OK` |
| `python3 tests/test_review_faults_faults.py` | `Ran 1 test in 994.174s` / `OK`; 146 `fault red:` lines (the three 0127 entries and the retargeted item 22d entry among them) and 2 `exemption green:` lines |

`Python feature_version=(3, 6): 3/3 changed or new Python files parse`.
The full suite is run separately by the deployment; it was not run here.
Details and the scratch setup are in
`docs/implementation/row_9_data_operands_change_report.md`.

## Status

Standing lane specification and implementation record, pending the separate
review named above. This producer does not approve or merge its own work.
This follow-up measures nothing and does not close row 9's measured exit.

## Date

2026-09-25
