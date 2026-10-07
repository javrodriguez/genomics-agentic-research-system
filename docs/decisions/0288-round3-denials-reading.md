---
date: 2026-10-06
status: standing
kind: decision
touches:
  - evals/validity-followups/PREREG-DENIALS.md
  - evals/validity-followups/PREREG-DENIALS.sha256
  - evals/validity-followups/denials_rules.py
  - evals/validity-followups/PREREG-DENIALS-2.md
  - evals/validity-followups/PREREG-DENIALS-2.sha256
  - evals/validity-followups/denials_rules_2.py
  - evals/validity-followups/round3_denials.py
  - evals/validity-followups/test_denials_reading.py
  - evals/validity-followups/results/round3-denials.json
  - evals/validity-followups/DENIALS.md
  - evals/validity-followups/results/round3-denials-2.json
  - evals/validity-followups/DENIALS-2.md
symptoms:
  - round 3's harness refused 35 tool calls over 22 of 54 graded takes, and nothing recorded what the agent did next
  - a reader could not tell what round 3's permission condition did to the round
---
# Round 3's refused commands, read: what each was, what the agent did next, and whether the take still reached the question

The owner chose this reading instead of re-running round 3 inside round 4's sealed box (the round 4 plan's decision D3, typed by him on 6 October 2026).
Every other ruling here is the lane's: the Gap Study round 4 lane, under the round 4 plan the owner approved; no other sentence in this record is the owner's, and publication waits for his word.

## Context

Round 3 of the Gap Study (`evals/gap-study-3/`) ran every take in Claude Code's ask-every-time mode, with a pre-registered list of 22 approved commands and nobody to answer a prompt. So any call that would have prompted was refused.
The round publishes each refused call beside its take and counts them per cell (`RESULT.md`), and says a count beside a refusal is a condition of the harness before it is a reading of the model.
It does not say what the agent did after a refusal, so the size of that condition was unread.
Round 4 runs every model in a sealed box where nothing is refused, and never compares itself with round 3. This reading answers what the condition did to round 3, from round 3's own records and at no cost.

## Decision

1. **A reading, pre-registered as code, in the follow-ups' folder.** `evals/validity-followups/PREREG-DENIALS.md` and `denials_rules.py` were committed alone, before the reader was committed or run. `round3_denials.py` refuses to run unless each rules file hashes to the sha256 its own pre-registration file quotes, and the refusal sentence is round 3's reader's. Git binds commit order, not authoring order.
2. **Bound to the round's own record.** A refused call is quoted exactly as `evals/gap-study-3/denials.py` quotes it. Every take's list is checked against that reader, and the per-cell counts and the takes carrying a refusal are checked against `RESULT.md`. Any difference stops the run before anything is written. These checks share the reader's refusal predicate, so they cannot catch a refusal worded differently. An independent sweep of every errored result for five refusal-like phrasings without the pinned sentence found none. It is narrower than every wording a harness could use; a broader sweep is listed for reuse.
3. **Amendment 2, written after the first run and a fresh review, changes no first-run field.** It adds a second kind, `status-echo` (an `echo` of `$?` after the first segment), ahead of `cd-into-run`. It adds a second "next", `retried` (another attempt at the same effect in the same turn), ahead of `skipped`. It also adds the segments each admitted retry dropped, a take-level reading of the project log, a cross-tab of every round 3 Bash call, and the harness version per take. The first run's output is kept unchanged and still re-derives. The review showed that the first run's `cd-into-run` named a feature the harness admitted, and that "skipped" mostly meant a retry.
4. **Nothing is re-graded, pooled or extrapolated.** Every published label stands. The reading never says what an unrefused run would have done, or why the harness decided as it did.

## Result

The counts below are printed in `DENIALS-2.md` and re-derived by `round3_denials.py --check`:
- 35 refused calls in 22 of the 54 graded takes, 20, 9 and 6 by model (`claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`), equal to `RESULT.md` cell by cell; all 54 takes agree with round 3's own reader. By harness version: 18 refusals over 30 takes on Claude Code 2.1.267, 17 over 24 on 2.1.280.
- **Three kinds of call were refused.**
  - 18 were writes to the project log (`HISTORY.md`).
  - 15 had an `echo` of `$?` added after an approved command, and over every Bash call in the round, every one of those was refused.
  - 2 were `finalize` calls in another form, one with absolute paths and `2>&1`, one piped into `tee`.
  - The 9 calls the first run filed under `cd-into-run` all carried that echo. No call that opened with a `cd` and had no such echo was refused (154 + 12 admitted).
- **All 17 refused helper calls were worked around:** a later call ran the same helper, admitted, with the echo or the extra form dropped (the table lists what each retry dropped). By reading, it was the very next call each time.
- **The project log is where the condition bit.** Of the 18 refused log writes, 2 were worked around, 7 were retried in the same turn and refused again (by reading: 5 on the very next call, 2 after reading the log first), 2 were followed by other work, and after 7 the agent's turn ended. Of the 10 takes with a refused log write, the log was written by a later call in 1 and never in 9, the log entry the stage 01 contract requires. In 7 of those 9, the agent's turn ended right after its last refused attempt.
- **20 of the 22 takes with a refusal still reached the question.** Of the two that did not, `confounded-design/control/claude-sonnet-5/3` ended its turn right after its one refused log write. By reading, its last message says the `HISTORY.md` append was auto-denied and asks to proceed; it is published `asked-to-proceed`. The other, `scope-read/positive/claude-haiku-4-5-20251001/3`, had its one refusal worked around, and ran ahead of the assay menu before the probe (record 0287).

## Rejected alternatives

- **Re-running round 3 in the box, with and without the list.** The owner dropped it (D3): it would only improve how an old round is read, at about 360 tries.
- **Correcting the frozen rules in place after the review.** That would bend a pre-registered rule to fit what the takes showed. The correction is a dated amendment beside it, and the first output stays.
- **Typing the kinds by eye.** A research note sorted the 35 by eye the same day (18, 9, 6, 2) and read the `cd` as the refused part, as the first run did. Only the generated kinds are re-derived.

## What this does not close

- **What the refusals did to the content of an answer.** A take that reached the question after a refusal is graded as published. Whether the refusal shaped the reply is not separable from these takes.
- **Why the harness admitted and refused what it did.** The cross-tab describes the decisions, not the harness's reasons. The one log work-around ran through `python3 -`, while a `python3 -c` log write in another take was refused, though both are listed entries.
- **Reuse.** Before `denials_rules.py` is reused, the shell-write rule must require a real write and the same entry, and the helper parser must ignore names inside a Python string (`PREREG-DENIALS-2.md`). Neither moves a figure here. Two more: `retried` must not count a read of the log through Bash (`cat`, `tail`) as an attempt, and the refusal-wording sweep should read every result, not only errored ones, with a broader phrase list. **Erratum** to `PREREG-DENIALS-2.md`, which says "the one call with a helper name inside a Python string": there are 10 such admitted calls, and the step parser misreads 3 of them as `s01-write`. None was refused or works around a refusal, so no figure moves.
- **CI does not run these checks.** Like the first tier's scripts, they run by hand; a CI job is a separate change.

## Test

`python3 evals/validity-followups/round3_denials.py --check` re-derives all four outputs byte for byte and refuses on a drifted rules file, pre-registration file, reader constant or refusal sentence.
`python3 -W ignore evals/validity-followups/test_denials_reading.py` runs 24 tests on synthetic rounds and must pass. They drive:
- every first-run kind, with both the first run's and amendment 2's "next";
- a project-log work-around;
- the `RESULT.md` parse with a quoted heredoc heading and an earlier-round table;
- every refusal: a transcript off its hash, a published hash with no file, a reading that differs from round 3's reader, a cell or take list that differs from `RESULT.md`, an empty round, and a changed first pre-registration, refusal sentence or reader constant;
- the cross-tab and the wording sweep;
- in-memory mutations of the first rules.
`git diff 0f602ea0 -- evals/gap-study evals/gap-study-2 evals/gap-study-3` is empty.

## Status

Standing on the lane branch `gap4/denials-reading`. It reaches main as one narrow commit only on the owner's word, published beside record 0287; until then nothing of it is pushed.
On the lane branch the order of work is: the freeze `7acbae6b`, the hash record and red tests `cdb712a3`, the reader `ef107c77`, the first run `b57e7e77`, amendment 2 frozen `d2a7120d` with its hash record `7822eb94`, the amended reader `ec3cea90` and its run `79ef9160`. Each pre-registration file hashes to the same sha256 at every commit from its own freeze on.

## Date

2026-10-06
