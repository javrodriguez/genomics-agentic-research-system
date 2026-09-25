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
  - an ordinary word such as case, set or PWD inside a heredoc review body still resets the carried placement
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

1. (a) **Data-only block (as amended by round B, 25 September 2026).** Round B
   is also THE LANE'S SPECIFICATION, UNDER THE OWNER'S DELEGATION; the lanes'
   coordinator's standing delegation covers it. It replaces round 1's wording
   of this item by the four parts below. Items 1 (b)-(e) stand.

   A Bash call is data-only-blocked when two things hold. It is blocked. And
   it would not be blocked if 0125's retained-data condition were the only
   condition removed. That condition is an operator word containing `<<`, or
   a word kept as a comment (`retained_data` in `run_reviews.py`). A cause
   that would still block the call is a **moving cause**. The four parts
   decide what counts as one:

   - **(a.1) Moving causes are read only from text the shell runs.** For the
     data-only decision only, every whole-call condition of 0125 (the
     forbidden words, the PWD text check, the shell-state values, `trap`)
     reads the call with two things left out: the bodies of the heredocs the
     harness itself removes (its own heredoc removal, under 0072 item 23's
     unambiguity rule), and the text of kept comments, each to the end of its
     physical line. A word that appears only inside such a body or comment
     never makes a call moving. The same word anywhere else still does,
     including in a comment item 23 removed. 0125's blocking is unchanged:
     retained data still blocks the call, and still accepts no `cd`. 0125's
     parse checks (a broken word, unbalanced parentheses, an open backquote)
     and item 8's raw-text guard are not whole-call conditions in this
     record's vocabulary, and they still read the whole call: they guard the
     parse that finds the bodies.
   - **(a.2) An unproven heredoc is a moving cause.** A `<<` operator counts
     as retained data only when the harness can prove it opens a heredoc. It
     is a moving cause instead when the physical line holding it also holds
     `$[`, `$((`, `((` or `${` (where bash may read `<<` as a shift or as
     parameter text), or when item 23's check cannot prove its body's removal
     unambiguous. Here-strings (`<<<`) stay retained data.
   - **(a.3) An expanded command word is a moving cause.** In a call that
     would otherwise be data-only, a word in command position (as the
     harness's own grammar already tracks command starts), outside retained
     data, that is or begins with an expansion (`$`, including `$'cd'`-style
     ANSI-C quoting and `${ }`) or holds a backquote makes the call moving.
     The audit cannot tell which command it runs.
   - **(a.4) Everything else stays as round 1 has it.** Every other cause, and
     every mixed case, is a moving cause: 0125's parse checks, item 8's
     raw-text guard, and every whole-call condition read as (a.1) gives it.
     This holds for the call and for every nested program the preflight
     inspects. A call blocked by any moving cause is NOT data-only-blocked,
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

Round B changes only how `moving` is computed. `without_heredocs` can now
report each removal it makes (its operator count and its lines), and a new
`shell_run_text` returns the call's text less those bodies and less each
kept comment, the indices of the words outside kept comments, and how many
removed heredocs sat on a line without a shift or parameter cue.
`CommandPlacement` reads the forbidden words, the PWD text and the
shell-state values from that text and those words for `moving` alone
(a.1). A call is also moving when its heredoc operators outside kept
comments outnumber the proven removals (a.2), or when a command word outside
kept comments begins with `$` or holds a backquote (a.3). `blocked`, the
refused-cd path and `blindness` are unchanged. The 134 existing runner fault
entries and round 1's six heredoc fault entries still match `run_reviews.py`
as many times as at `e6469eb`.

### Round B: what review 1 found and how each finding is answered

A fresh independent review of round 1 (`e6469eb`) returned APPROVE WITH
CHANGES, with one MAJOR and three NOTEs.

- **F1 (MAJOR): round 1 did not fix the defect it exists for.** 0125's
  forbidden-word and PWD-text checks read the call's raw text, heredoc bodies
  and comments included, and round 1 counted them as moving causes. So a
  heredoc whose review body held an ordinary word such as `case`,
  `function`, `enable`, `unset`, `set` or `PWD` was still blocked at the kit
  root, exactly as at `da40061`. The supplied data passed only because its
  placeholder body line avoids those words. The lane then checked the two
  real recorded sessions against `e6469eb`'s code: both still score 1 hit,
  because both real review bodies hold such words (`case` in both, `set` in
  one). **Answered by (a.1)**, and by `test_honest_review_bodies` and
  `test_honest_kept_comment_words`.

  Why round 1's tests missed it: the data README's substitution check (that
  replacing the body by one placeholder line leaves both scores unchanged)
  was made against `da40061`'s code. There every blocked call reset to the
  kit root, whatever blocked it, so the body could not change the score. At
  round 1's code the body decides whether the call is data-only, and the
  check no longer held. Round B's tests therefore replace the placeholder at
  run time with review-like bodies; the committed data files are unchanged.
- **F2 (NOTE): a `<<` that bash does not read as a heredoc.** Inside `$[ ]`,
  `$(( ))` or `${ }`, the harness still removed lines bash actually runs.
  A `cd` or `pushd` hidden there kept the carried placement, and a
  parent-step read after it scored 0 where `da40061` scored a hit. **Answered
  by (a.2)**, and by `test_unproven_heredoc_in_call` and
  `test_unproven_heredoc_next_call`.
- **F3 (NOTE): a `cd` spelled through an expansion in command position**
  (`$'cd'`, or `c=cd; $c <parent>`) next to a heredoc scored a hit at
  `da40061` only through the block's reset, and scored 0 at round 1.
  **Answered by (a.3)**, and by `test_expanded_command_word_in_call` and
  `test_expanded_command_word_next_call`.
- **F4 (NOTE): README.md's count sentence** dated 715 tests to the 0074
  landing, which collected 702. **Answered** by rewording that one sentence:
  it now states the count the suite collects at this change, and says the
  skip figures beside it were measured on the 702-test suite at 0074's
  landing. DEVELOPMENT.md's two count lines are corrected the same way.

**How this change was built.** A headless Claude Opus 5.5 session produced it,
and a separate fresh Claude Opus 5.5 session reviews it (residual (iv)).

## What this does not close

Covered, and only as far as the tests below show it:

- The supplied C01 and C02 sessions score 0 hits (C01 0 ambiguous, C02 2)
  with their placeholder body, and with review-like bodies substituted at run
  time that name, in prose and in JSON strings, each of `case`, `function`,
  `enable`, `unset`, `set`, `alias`, `shopt`, `trap`, `eval`, `source`,
  `pushd`, `popd`, `cd`, `PWD`, `OLDPWD`, `CDPATH`, `BASH_ENV` and a `.` as a
  word (one body per word, and one holding all). This is shown for these
  bodies only. The real review bodies are not in this repository, and no
  claim is made about them.
- A kept comment naming each of those words, in a data-only call after
  `cd repo`, then a parent-step `tmp` read in the next call, scores 0. A bare
  `cd` in kept comment text is the exception: it is a `cd` word, and item 1
  (b) refuses it and resets to the kit root, so the comment tests name it
  only as `cd:`.
- An outside read after `cd repo` scores at least one hit in the call and in
  the next call for every spelling the tests build: a refused `cd` (escape
  (1)); `eval`, `pushd` and a heredoc with `eval` (escape (2)); the words
  `eval`, `pushd`, `set`, `case`, `alias`, `source`, `.`, `unset` and `trap`
  used as commands next to a heredoc; review 1's F2 spellings (`$[ ]`,
  `$(( ))`, `${ }`); review 1's F3 spellings (`$'cd'`, `c=cd; $c`); a
  two-step climb in or after a heredoc or a kept comment; and a read after an
  error result. Every other spelling 0072, 0125, 0127 and 0128 name keeps its
  own tests, which still pass in the modules this change ran.

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
- **(v) An unquoted heredoc body is expanded by the shell.** Its parameter
  expansions and command substitutions run in a subshell or only assign
  variables, so none of them moves the calling shell. The audit relies on
  that when (a.1) leaves such a body out of the moving check.
- A comment that item 23 removed is still read by the moving check (a.1
  leaves out only kept comments). So a forbidden word in such a comment, in a
  call with a heredoc, still resets that call to the kit root, as at
  `da40061`. This is fail-closed.
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

Round B adds eight tests to the same module and class, and four fault
entries to the same list. Each new honest test was run against `e6469eb`'s
`run_reviews.py`, compiled in memory behind the same accessor. Each new
outside test was run under its round B fault.

- `test_honest_review_bodies` (item 7 (a)): each supplied session, with the
  placeholder body line replaced at run time by a review-like body naming the
  word in prose and inside JSON strings. There are 19 bodies: one per word
  (`case`, `function`, `enable`, `unset`, `set`, `alias`, `shopt`, `trap`,
  `eval`, `source`, `pushd`, `popd`, `cd`, `PWD`, `OLDPWD`, `CDPATH`,
  `BASH_ENV`, `.`) and one holding all of them. Every body gives C01 0 hits
  and 0 ambiguous, and C02 0 hits and 2 ambiguous. Each last call is asserted
  data-only. Graded-against-seen is 7/7 and 10/10 for every body. At
  `e6469eb` it is red for the bodies naming a word the raw-text checks read
  (`case`, `function`, `enable`, `unset`, `alias`, `shopt`, `PWD`, `OLDPWD`,
  `CDPATH`, `BASH_ENV`, and the all-words body), in both sessions. It is
  green there for `set`, `trap`, `eval`, `source`, `pushd`, `popd`, `cd` and
  `.`: `e6469eb` read those as word values, and a removed body yields no
  words.
- `test_honest_kept_comment_words`: `true # <word>: see <word> x $(date)` for
  each word (the `$(` keeps the comment), and one comment holding all, each
  a data-only call after `cd repo`, then `export TMPDIR=<parent>/tmp`. Every
  one scores 0 hits and 0 ambiguous. A bare `cd` is named only as `cd:`,
  because item 1 (b) refuses a `cd` word in kept comment text. At `e6469eb`
  it is red for every comment except `cd` and `.`.
- Item 7 (b), outside, each after `cd repo`, each at least one hit in the call
  and, by round 1's next-call rule, a hit that is the next call's own:
  - `test_command_words_next_to_heredoc_in_call` and `_next_call` twin:
    `eval "cd <parent>"`, `pushd <parent>`, `set -P`,
    `case x in x) cd <parent>;; esac`, `alias up='cd <parent>'` then `up`,
    `source f`, `. f`, `unset PWD`, `trap 'cd <parent>' DEBUG`, each on a
    heredoc's header line, and each asserted blocked, not data-only.
  - `test_unproven_heredoc_in_call` and `_next_call` twin (F2): `echo $[1<<2]`,
    `cd <parent>`, `2]` on three lines; the same with `$((1<<2))` and `2))`;
    and `echo ${v:-<<EOF}` closed by `EOF}`. The `$[` and `${` spellings are
    red at `e6469eb`. The `$((` spelling is a hit there too: item 23 keeps
    that line's body, and its closing `))` breaks the parse.
  - `test_expanded_command_word_in_call` and `_next_call` twin (F3):
    `$'cd' <parent>` and `c=cd; $c <parent>`, each next to a heredoc. Both
    are red at `e6469eb`.
- `test_cd_word_in_data_only_call` is the one round 1 test whose expected
  value round B changes. Round 1 placed the `cd` word in a heredoc body that
  item 23 keeps (the header line holds `$(`). Under (a.2) such a heredoc is
  unproven, so the call is moving and every word is at the kit root. The
  test now asserts that, and checks the data-only `cd`-word rule of item 1
  (b) on kept comment text instead. It is still named by round 1's
  refused-cd fault, which still turns it red.
- Round B's red-on-fault entries, all red, each with an unfaulted control
  that passes and named subtests as witnesses:
  - `moving causes read from the raw text again` fails
    `test_honest_review_bodies` (every raw-text word's body, and the
    all-words body, in C01 and C02) and `test_honest_kept_comment_words`
    (every comment except `cd` and `.`).
  - `body exclusion extended to the whole call` (the moving check reads no
    text at all) fails both command-word tests on every spelling except
    `case`. The `case` entry's own `cd` word is refused by item 1 (b), so it
    is still a hit under this fault.
  - `unproven-heredoc guard dropped` fails both F2 tests on the `$[` and `${`
    spellings. The `$((` spelling stays a hit through its broken parse.
  - `expanded-command-word guard dropped` fails both F3 tests on both
    spellings.

  A no-op round B fault was also checked: the runner fails it.

Results on the build host at round B (Python 3.8.2, macOS; scratch outside
the checkout). Round 1's results are kept in the change report.

| Command | Result |
|---|---|
| `python3 tests/check_counts.py` | `suite: 723 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/test_review_faults_cd.py` | `Ran 32 tests`; `OK`; `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test`; `OK`; 25 `cd fault red:` lines |
| `python3 tests/test_review_faults_core.py` | `Ran 12 tests`; `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test`; `OK`; `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_data.py` | `Ran 5 tests`; `OK` |
| `python3 tests/test_review_faults_heredoc.py` | `Ran 20 tests`; `OK`; `heredoc-call corpus C01 graded-against-seen: 7/7`, `C01 hits: 0, ambiguous: 0`; `C02 graded-against-seen: 10/10`, `C02 hits: 0, ambiguous: 2`; `heredoc review-body C01: 19 bodies, graded-against-seen 7/7`; `heredoc review-body C02: 19 bodies, graded-against-seen 10/10` |
| `python3 tests/test_review_faults_heredoc_faults.py` | `Ran 1 test`; `OK`; 10 `heredoc fault red:` lines |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests`; `OK` |
| `python3 tests/test_review_faults_session.py` | `Ran 18 tests`; `OK`; `session-call corpus graded-against-seen: 8/8`; `session-call corpus hits: 0, ambiguous: 1` |
| `python3 tests/test_review_faults_session_faults.py` | `Ran 1 test`; `OK`; 19 `session fault red:` lines |

`Python feature_version=(3, 6): 3/3 changed or new Python files parse`.
Timings and the exact lines are in the change report,
`docs/implementation/row_9_heredoc_placement_change_report.md`.

## Status

Standing lane specification and implementation record, pending the separate
review named above. Item 1, with round B's amendment of 1 (a), is implemented
and its acceptance passes on the build host. This producer does not approve
or merge its own work, and this follow-up measures nothing.

## Date

2026-09-25
