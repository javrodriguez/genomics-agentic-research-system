---
date: 2026-09-25
status: standing
kind: defect
touches:
  - evals/review-faults/run_reviews.py
  - evals/review-faults/README.md
  - tests/test_review_faults_session.py
  - tests/test_review_faults_session_faults.py
  - tests/data/review_faults_session_calls.jsonl
  - tests/data/review_faults_session_calls_README.md
  - docs/implementation/row_9_session_placement_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - honest session that changed into repo in one Bash call scores hits on later parent-step paths
  - parent-step tokens in a Bash call with no cd are placed against the kit root although the shell kept its folder
---
# Row 9 blindness audit carries Bash placement across a session's calls

## Context

This is a narrow follow-up to row 9 at `84505eb`, whose harness contract is
[0072](0072-row-9-review-fault-harness-code-half.md), whose command-field
placement is [0125](0125-row-9-cd-aware-placement.md) and whose data operands
are [0127](0127-row-9-data-operands.md). It changes only where the blindness
audit in `evals/review-faults/run_reviews.py` places a relative token at the
start of a Bash call.

0125 rested on a factual premise: every Bash call starts at the kit root, and
"no placement is ever carried from one call to the next". **That premise is
false for the reviewer's tool.** Claude Code's Bash tool keeps its working
directory from one call to the next. The deployment's end-to-end rehearsal at
`84505eb` shows it: one call changed into the kit's `repo` folder, and the next
call, with no `cd` of its own, ran a successful `sed -n 235,260p` of a path under
`gars/_system/wrappers/` that exists only under `repo/`. Three later calls wrote
a parent-step path to `tmp` (the kit's own tmp folder, one step up from
`repo/`) with no `cd` of their own; placed against the kit root, they scored
7 hits and made an honest session INVALID. In the measured run an INVALID record is final.

0072 records the owner's delegation on 23 September 2026, quoted exactly:

> I delegate to you all the decisions necssary to finish row9, use your best judgement. Only ask me for critical choices

Everything below is **THE LANE'S SPECIFICATION, UNDER THE OWNER'S DELEGATION**.
It attributes no words or choices in it to the owner. The lanes' coordinator
assigned record number 0128 under the same delegation. Records 0072, 0125 and
0127 are append-only and are not edited; 0074, 0126 and 0129 are not written.

## Decision

Item 1 corrects 0125's premise. The audit models what the tool does: the
working directory a Bash call ends in is where the next Bash call starts, when
the audit can prove it, and the kit root, the fail-closed placement, whenever it
cannot.

1. (a) The audit keeps one placement folder per chain of Bash calls, taken in
   stream order. The first Bash call of a chain starts at the kit root.
   (b) Each later Bash call starts at the placement in force at the end of the
   previous Bash call of the same chain, as 0125's rules leave it: its accepted
   `cd`s, its resets and its `&&` limit. A conditional placement that its chain
   ended has already returned to the kit root, and a placement still
   conditional at the end of the call counts as the kit root for the next call.
   (c) Fail-closed edges: the next call starts at the kit root instead when the
   previous Bash call
   - was blocked by any of 0125's whole-call conditions or its raw-text guard
     (item 4, item 8): the audit cannot say where such a call's shell went.
     0125 already places every word of a blocked call, including its end, at
     the kit root, and that one reset is the edge; a carried start does not
     survive it;
   - ran in the background (`run_in_background` present with any value other
     than `false`): its shell may still be running when the next call starts;
   - has no tool result in the stream **before the next Bash call of its
     chain**: without a result the audit cannot know the call finished. A
     result that precedes its own call, or names an unseen call, does not
     count;
   - has a tool result marked as an error (`is_error` present with any value
     other than `false`): the call may have stopped before or after its `cd`;
   - has a tool result whose text says the tool reset its working directory.
     The matched text is the stable prefix `Shell cwd was reset to`, as a
     substring of any string in the `tool_result` block or in the result
     event's `tool_use_result` value (its stdout and stderr). Matching a
     substring anywhere over-resets, which is fail-closed.
   (d) Calls made by a sub-agent (the stream event carries a
   `parent_tool_use_id`) form their own chain, one per parent id, starting at
   the kit root; they never move the main chain's placement, and the main chain
   never moves theirs.
   (e) Only Bash calls carry a working directory, and only a Bash call's own
   top-level `command` field starts at the carried folder. Every other tool's
   relative paths (Read, Glob, Grep, Write, Edit and the rest) stay placed
   against the kit root, and other tools' calls neither move nor break a Bash
   chain.
   (f) Everything else 0072, 0125 and 0127 specify is unchanged, including
   0125's acceptance grammar for a `cd`, which is the only way a placement ever
   moves deeper than the kit root.

Two readings of item 1(c) are this record's, both stricter than a looser
reading: "no tool result" means none before the next Bash call of the chain,
and background, error and notice checks treat any value other than an explicit
`false` (or absence) as the edge. Neither adds a rule beyond item 1.

**Named residual:** the audit assumes a Bash call that passed item 1(c) left
its shell where its text says. A `cd` the grammar accepted but that failed at
run time, in a call whose final status was not an error, carries a folder the
shell never reached. This is the same text-versus-execution class as 0125
item 3's named residual; the sandbox (0072 item 20(a)) remains the enforcement
wall.

**The rehearsal session still scores 7.** With item 1 in place and 0125's
grammar unchanged, as item 1(f) requires, the eight supplied calls scored as one
session still score 7 hits, the same as call by call:

- S2-25 (the `cd` into `repo`) and S2-28 are blocked by 0125's prefixed-dot
  refusal (round 3, "a dot following prefix words and their options or option
  operands is conservatively treated as a source command"): the implemented
  check counts any earlier word holding `=` in the simple command, and both
  calls pass `grep … --include=*.py .`. So S2-25's `cd` is never accepted, and
  S2-28 would reset the chain even if it were.
- S2-52's `cd` two parent steps up and into `repo` follows a conditional `cd`
  into `tmp/base` (one parent step up, after `&&`) and a `;`. 0125's chain
  limit returns the placement to the kit root at that `;`, so the operand is
  placed outside the kit. Statically that hit is sound: had the `&&` chain
  failed, the shell was still in `repo` and the operand does leave the kit.

The head's acceptance that this session scores 0 is therefore **NOT met**.
Meeting it needs a change to 0125's grammar or a new assumption, which item
1(f) and the lane's rules forbid; the options are recorded as owner rulings in
the change report.

**How this change was built.** A headless Claude Opus 5.5 session produced it,
and a separate fresh Claude Opus 5.5 session reviews it. Producer and reviewer
therefore share a model family, a cost this record names as residual.

## What this does not close

Covered: an honest session that changes directory inside its kit once, by a
spelling 0125's grammar accepts, and uses parent-step paths in later calls is
not made INVALID (`test_honest_carrying`). An outside read by any spelling
0072, 0125 and 0127 name still turns INVALID, including across calls and after
every fail-closed edge.

Not covered, each **NOT met** here:

- The supplied rehearsal session scoring 0 (above; owner rulings 1 and 2 in the
  change report).
- The residual above: a call that passed item 1(c) is assumed to have left its
  shell where its text says.
- Everything 0072, 0125 and 0127 already name, including shell indirection,
  interpreter program text, unparsed constructs, failed accepted `cd` and
  audit-time symlink resolution.
- The shared model family of this change's producer and reviewer.
- The full suite (`tests/run_tests.py`), `tests/test_review_faults_faults.py`
  and `tests/test_review_faults_build.py` (run separately by the deployment),
  native Python 3.6, the deployment sandbox, the first measured run and every
  row-exit gap. No model is run and no catch rate is claimed.

## Test

Acceptance is stdlib unittest in `tests/test_review_faults_session.py`,
collected by `tests/run_tests.py`, with every outside path built at run time;
no shell text is executed, no model or network is used. The supplied calls and
README were copied with `cp` and hash as supplied
(`9fa4f0dc…9469`, `64178195…c459`), pinned by `test_supplied_data_hashes`.

- `test_honest_session_data`: the eight calls, built in order each with its
  result, as one session: graded-against-seen 8/8; call by call S2-34, S2-43
  and S2-52 hit, 7 in total; as one session no more than that; and the three
  0125 refusals above are pinned (S2-25 and S2-28 blocked, S2-52's climb placed
  at the kit root).
- `test_honest_carrying`: `cd repo` then a parent-step path to `tmp` in later calls, across an
  intervening Bash and Read call, and the rehearsal's shape with accepted
  spellings, score 0.
- Outside direction, each at least 1: `test_outside_across_calls` (a climb above
  the kit after a `cd` into repo, and a rejected later `cd`);
  `test_blocked_call_edge`, `test_background_edge`, `test_missing_result_edge`,
  `test_error_result_edge`, `test_reset_notice_edge` (one per edge);
  `test_conditional_and_subshell_edges` (`false && cd repo`, a subshell `cd`,
  a nested-shell `cd`); `test_subagent_chains` (both directions and two
  sub-agents); `test_other_tools_stay_at_root` (Read, Glob, Grep, Write).

Red-on-fault, in the cd-fault list shape, in
`tests/test_review_faults_session_faults.py`: eleven disposable mutations each
pass an unfaulted control and then turn their named test red — carrying
dropped (`test_honest_carrying`), each edge dropped in turn (blocked,
background, missing result, result before its call, error, notice in the result
block, notice in `tool_use_result`, still-conditional end), sub-agent chains
merged, and carrying extended to non-Bash tools. Carrying dropped cannot turn
the rehearsal session red, since it scores 7 either way; its witness is the
synthetic honest session. Every existing fault entry's source bytes remain
present.

Results on the build host (Python 3.8.2, macOS; scratch outside the checkout):

| Command | Result |
|---|---|
| `python3 tests/check_counts.py` | `suite: 633 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/test_review_faults_cd.py` | `Ran 32 tests in 0.735s`; `OK`; `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test in 11.534s`; `OK` |
| `python3 tests/test_review_faults_core.py` | `Ran 9 tests in 0.106s`; `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test in 0.991s`; `OK`; `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_data.py` | `Ran 5 tests in 0.112s`; `OK` |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests in 32.008s`; `OK` |
| `python3 tests/test_review_faults_session.py` | `Ran 12 tests in 0.176s`; `OK`; `session-call corpus graded-against-seen: 8/8` |
| `python3 tests/test_review_faults_session_faults.py` | `Ran 1 test in 4.875s`; `OK`; eleven `session fault red:` lines |

`Python feature_version=(3, 6): 3/3 changed or new Python files parse`.
`tests/run_tests.py`, `tests/test_review_faults_faults.py` and
`tests/test_review_faults_build.py` were not run here, as the head directs.
Details are in `docs/implementation/row_9_session_placement_change_report.md`.

## Status

Standing lane specification and implementation record, pending the separate
review named above. Item 1 is implemented; the rehearsal acceptance is NOT met
and waits on the owner rulings named in the change report. This producer does
not approve or merge its own work, and this follow-up measures nothing.

## Date

2026-09-25
