---
date: 2026-09-25
status: standing
kind: defect
touches:
  - evals/review-faults/run_reviews.py
  - evals/review-faults/README.md
  - tests/test_review_faults_heredoc.py
  - tests/test_review_faults_heredoc_faults.py
  - tests/data/review_faults_heredoc_calls.jsonl
  - tests/data/review_faults_heredoc_calls_README.md
  - docs/implementation/row_9_heredoc_placement_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - honest session whose last Bash call writes review.json through a heredoc scores a blindness hit and turns INVALID
  - a heredoc or kept comment resets the placement carried from the previous Bash call to the kit root
---
# Row 9 blindness audit keeps the carried placement through a call blocked only by retained data

## Context

This is a narrow follow-up to row 9 at `da40061`. Its harness contract is
[0072](0072-row-9-review-fault-harness-code-half.md), command-field placement is
[0125](0125-row-9-cd-aware-placement.md), data operands are
[0127](0127-row-9-data-operands.md), session placement is
[0128](0128-row-9-session-placement.md), and the first measured run is
[0074](0074-row-9-seal-and-first-measured-run.md). It changes only two things
in the blindness audit in `evals/review-faults/run_reviews.py`: how it places
the words of a Bash call blocked **only** by retained data, and where the next
Bash call of the same chain starts after such a call.

**The finding.** Row 9's first measured run (0074) recorded 2 of 15 records
INVALID: the reviews of the public clean cases C01 and C02, each with one
blindness hit. A replay of the two recorded streams through the pinned harness
reproduced both envelopes and found one shared cause. Each session's last Bash
call wrote the review file through a quoted heredoc (`<<'EOF'`). 0125's
retained-data condition blocks such a call. A blocked call places every word,
and its end, at the kit root (0125 item 4), and 0128 item 1 (c) then also
starts the next call at the kit root. So the block threw away the placement
0128 had carried:

- C01, call 7: the carried placement was the kit's `repo` folder. The call
  names the review file one parent step up from `repo/`, which is the kit's own
  review file. Placed from the kit root, that path is one level above the kit,
  a hit under both placements.
- C02, call 10: the call begins `cd <parent>` from a carried `repo/`
  (the optimistic placement). From the kit root that operand names the folder
  above the kit, a hit.

In the measured run an INVALID record is final, so both clean cases went
unmeasured.

Why the block existed: 0125 blocks retained data because a heredoc body or a
kept comment may contain the word `cd` as data, and the placement engine must
not follow a `cd` that never ran. That concern is about following a `cd`. It
is not about the carried placement. A heredoc or a comment cannot move the
calling shell's working directory.

0072 records the owner's delegation on 23 September 2026, quoted exactly:

> I delegate to you all the decisions necssary to finish row9, use your best judgement. Only ask me for critical choices

Everything under Decision is **THE LANE'S SPECIFICATION, UNDER THE OWNER'S
DELEGATION**. None of it is attributed to the owner. The lanes' coordinator
assigned record number 0129 under the same delegation. Records 0072, 0074,
0125, 0126, 0127 and 0128 are append-only and are not edited.

## Decision

**This record amends 0128 item 1 (c)'s blocked-call edge, for data-only
blocks only.** Every other edge of 0128 item 1 (c), and every other rule of
0072, 0125, 0127 and 0128, is unchanged.

1. (a) **Data-only block.** A Bash call is data-only-blocked when two things
   hold. It is blocked. And it would not be blocked if 0125's retained-data
   condition were the only condition removed. That condition is an operator
   word containing `<<`, or a word kept as a comment (`retained_data` in
   `run_reviews.py`). So none of these may block the call:
   - any other whole-call condition of 0125: the forbidden words, the
     shell-state hazards, `trap`;
   - any of 0125's parse checks: a broken word, unbalanced parentheses, an open
     backquote;
   - item 8's raw-text guard.

   This holds for the call and for every nested program the preflight
   inspects. A call blocked by any other cause is NOT data-only-blocked,
   whether that cause acts alone or together with retained data.

   (b) **Inside a data-only-blocked call.** The call starts at its carried
   placement as 0128 items 1 (a)-(c) give it, for the pessimistic and the
   optimistic placement alike, instead of the kit root. It still accepts no
   `cd`: 0125 item 4 is unchanged, and a blocked call proves no directory
   change. Its words are placed from the carried placement up to its first
   `cd` word. At every `cd` word, 0125's handling of a `cd` it cannot accept
   applies unchanged. That includes a `cd` word that is not top-level, and one
   that is heredoc or comment text. The `cd`'s operand is judged from the
   folder in force before it. The words after it are placed at the kit root,
   and the call ends there.

   (c) **After a data-only-blocked call.** The next Bash call of the same chain
   starts at the placement in force at the end of the data-only-blocked call,
   exactly as 0128 item 1 (b) carries an unblocked call's end. That placement
   is the carried one if the call had no `cd` word, and the kit root if it had
   one. 0128 item 1 (c)'s blocked-call edge no longer applies to a
   data-only-blocked call. Every other edge of 1 (c) still applies to it
   unchanged: background, no tool result before the next call, an error
   result, a reset notice.

   (d) **Every other blocked call is unchanged.** Every word and the end are
   placed at the kit root (0125 item 4, item 8), and the next call starts at
   the kit root (0128 item 1 (c)). The reason: those causes can move the shell
   where the audit cannot see it. `eval` and `source` run text the audit does
   not parse as a `cd`. `pushd` and `popd` change the folder. `set`, `trap`,
   functions, aliases and `CDPATH` change what a later `cd` does. A broken
   parse or a raw control character leaves the audit unable to say where the
   shell went.

   (e) Everything else 0072, 0125, 0127 and 0128 specify is unchanged. That
   includes 0128's two placements (pessimistic and optimistic), its `ambiguous`
   count, and 0125's acceptance grammar for a `cd`. That grammar remains the
   only way a placement ever moves deeper than the kit root.

**Why the change is scoped to retained data only.** The lane first worded the
principle for every blocked call: "a blocked call keeps the carried placement
and places its words from it". Read that way, it opens two escapes that the
audit catches today. 0129 closes both:

- **(1) A refused `cd`.** Take the blocked call
  `cd <parent>; cat <parent>/x <<'EOF'` from a carried `repo/`. If `repo/` were
  kept after the refused `cd`, the read would be placed inside the kit. But the
  shell went up one level first, so the read is one level above the kit. Item
  (b) closes this: every `cd` word resets the rest of the call, and its end, to
  the kit root.
- **(2) Shell-moving blocks.** Some causes can move the shell where the audit
  cannot see it. One is `eval "cd <parent>"; cat <parent>/x`, where the eval
  string is one quoted word and not a `cd`. Another is `pushd <parent>`. If the
  carried placement were kept inside such a call, or carried into the next
  call, the read would be placed inside the kit. Items (a) and (d) close this,
  because such a call is never data-only.

**Implementation.** `CommandPlacement` now keeps a `moving` verdict beside
`blocked`. `moving` is every blocking cause except retained data, plus a
whole-call `moving` flag set by the preflight or by item 8's raw-text guard.
`data_only` is `blocked and not moving`. A data-only call restores the folder
it was entered with after 0125's reset. A `cd` word still takes 0125's
refused-cd path. The preflight records `moving` whenever any inspected program
is blocked by a cause other than retained data. `blindness` is unchanged apart from
one comment. It already carries the end folder of a call that passed 0128's edges, and a
shell-moving block still ends at the kit root. Every byte that the existing
fault lists mutate is kept. All 134 existing runner fault entries (cd faults,
session faults, the original list's runner entries) match
`run_reviews.py` as many times as at `da40061`.

**How this change was built.** A headless Claude Opus 5.5 session produced it,
and a separate fresh Claude Opus 5.5 session reviews it (residual (iv)).

## What this does not close

Covered: an honest session whose last call writes its review through a
heredoc, relative to the folder earlier calls left it in, is not made INVALID
(`test_honest_heredoc_sessions`, `test_honest_data_only_carry`). An outside
read by any spelling 0072, 0125, 0127 and 0128 name still scores a hit. That
holds inside or after a data-only-blocked call, after a refused `cd` in one,
and inside or after a call blocked by any shell-moving cause.

Named residuals, each **NOT met** here:

- **(i) The measured run is never re-scored.** 0129 applies to future runs
  only. 0074's figures, its two INVALID records and its run file stand as
  recorded. No reader should take 0129 as saying C01 or C02 would have been
  clean. 0074 notes that C02's submitted, ungraded review carries a finding at
  MAJOR.
- **(ii) A presentation residual in the grader.**
  `evals/review-faults/score.py` prints the overall false-alarm figure against
  a fixed denominator of 5 (`ratio(total_alarms, 5)`). So a run with INVALID
  clean records prints, for example, `0/5`, where the measured figure is 0 of
  3 valid clean reviews (0074 reports it that way). The grader is deliberately
  NOT changed here. It is the instrument the first run was graded with, and
  changing it is outside this follow-up. Readers take the valid clean count
  from the record and from `release_check`'s reviewer cell.
- **(iii) The audit assumes that a heredoc or a kept comment cannot move the
  calling shell's working directory.** A program that replaces or re-enters the
  shell from such data is the same residual class as 0125 item 3, for example
  a shell that reads its program from a heredoc through `exec`. The sandbox
  (0072 item 20(a)) remains the enforcement wall.
- **(iv) Shared model family.** This change was built by a headless Claude
  Opus 5.5 session and is reviewed by a separate fresh Claude Opus 5.5
  session, so producer and reviewer share a model family. This record names
  that cost as a residual.
- Everything 0072, 0125, 0127 and 0128 already name.
- Not run here: the full suite (`tests/run_tests.py`),
  `tests/test_review_faults_faults.py` and `tests/test_review_faults_build.py`
  (the deployment runs these separately), native Python 3.6, and the
  deployment sandbox. No model is run, and no catch rate or figure beyond
  0074's is claimed.

## Test

Acceptance is stdlib unittest in `tests/test_review_faults_heredoc.py`,
collected by `tests/run_tests.py`. Every outside path is built at run time from
pieces. No shell text is executed, and no model or network is used. The
supplied calls and README were copied with `cp`, and their hashes match the
supplied ones (`d77ad252…5d180`, `98a4f14e…4f187`). `test_supplied_data_hashes`
pins both.

- `test_honest_heredoc_sessions` scores each session of the data as one stream,
  never merged. The kit holds `repo/`, `tmp/` and `repo/tmp/prev/`.
  - Graded-against-seen: C01 7/7 and C02 10/10.
  - C01 scores 0 hits and 0 ambiguous. C02 scores 0 hits and 2 ambiguous: its
    ninth call's, plus its tenth call's `cd <parent>` judged from the
    pessimistic kit-root start that its ninth call left.
  - Each session's last call is asserted data-only-blocked, and every other
    call unblocked.
  - At `da40061`'s logic the same test prints C01 1 hit, 0 ambiguous and C02
    1 hit, 1 ambiguous, as the head records, and fails.
- `test_honest_data_only_carry`: `cd repo`, then a data-only-blocked call with
  no `cd` that writes a parent-step `tmp` path, then a call reading a
  parent-step `tmp` path. Result: 0 hits, 0 ambiguous.
- `test_block_causes` asserts the verdict for each cause. Data-only: heredoc,
  here-string, kept comment, a nested program's heredoc. Blocked: eval, pushd,
  heredoc with eval, heredoc with `unset`, heredoc with a nested eval, heredoc
  with a raw control character. Also the calls the outside tests below use.
- Outside direction, each after a first call `cd repo` whose result arrived,
  each at least 1 **hit**. Every next-call entry asserts that adding the next
  call raises the stream's hits by at least 1 over the same stream without it.
  - `test_refused_cd_in_call` and `test_refused_cd_next_call` cover escape (1).
  - `test_cd_word_in_data_only_call`: in kept heredoc text, a `cd`'s operand is
    placed at the carried folder, and the words after it and the call's end are
    placed at the kit root.
  - `test_shell_moving_in_call` and `test_shell_moving_next_call` cover escape
    (2): eval, pushd, and heredoc with eval.
  - `test_data_only_climb` and `test_comment_climb`: a two-step climb, inside
    and after a heredoc block and a kept-comment block.
  - `test_error_edge_after_data_only`: a data-only-blocked call with an error
    result, then a parent-step `tmp` read.
  - Each outside test is green at `da40061`'s logic too, run in memory through
    the same accessor. The honest tests, the verdict test and the cd-word
    placement test are red there.
- Red-on-fault is in `tests/test_review_faults_heredoc_faults.py`, in the fault
  list shape (label, source bytes, replacement, named tests). Each fault is
  applied in memory: `run_reviews.py` is compiled with one replacement, and the
  named tests run against it through the test class's `harness` accessor. Each
  run has an unfaulted control that must pass. A faulted run must fail with
  failures, not errors, on every named test. Named subtests serve as witnesses.
  All six are red:
  - `data-only carry dropped` fails the C01 and C02 sessions and the synthetic
    honest case.
  - `refused cd in a data-only block keeps the carried placement` fails
    escape (1)'s entries and the cd-word placement test.
  - `carry applied to every blocked call` fails escape (2)'s in-call entries
    (eval, pushd, heredoc with eval).
  - `shell-moving block end carried to the next call` fails escape (2)'s
    next-call entries.
  - `data-only block end not carried to the next call` fails the synthetic
    honest case.
  - `error edge skipped after a data-only block` fails its entry.

  A no-op fault was also checked: the runner fails it.

Results on the build host (Python 3.8.2, macOS; scratch outside the checkout):

| Command | Result |
|---|---|
| `python3 tests/check_counts.py` | `suite: 715 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/test_review_faults_cd.py` | `Ran 32 tests`; `OK`; `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test`; `OK`; 25 `cd fault red:` lines |
| `python3 tests/test_review_faults_core.py` | `Ran 12 tests`; `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test`; `OK`; `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_data.py` | `Ran 5 tests`; `OK` |
| `python3 tests/test_review_faults_heredoc.py` | `Ran 12 tests`; `OK`; `heredoc-call corpus C01 graded-against-seen: 7/7`, `C01 hits: 0, ambiguous: 0`; `C02 graded-against-seen: 10/10`, `C02 hits: 0, ambiguous: 2` |
| `python3 tests/test_review_faults_heredoc_faults.py` | `Ran 1 test`; `OK`; 6 `heredoc fault red:` lines |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests`; `OK` |
| `python3 tests/test_review_faults_session.py` | `Ran 18 tests`; `OK`; `session-call corpus graded-against-seen: 8/8`; `session-call corpus hits: 0, ambiguous: 1` |
| `python3 tests/test_review_faults_session_faults.py` | `Ran 1 test`; `OK`; 19 `session fault red:` lines |

`Python feature_version=(3, 6): 3/3 changed or new Python files parse`.
Timings and the exact lines are in the change report,
`docs/implementation/row_9_heredoc_placement_change_report.md`.

## Status

Standing lane specification and implementation record, pending the separate
review named above. Item 1 is implemented and its acceptance passes on the
build host. This producer does not approve or merge its own work, and this
follow-up measures nothing.

## Date

2026-09-25
