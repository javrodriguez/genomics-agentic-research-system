---
date: 2026-10-01
status: standing
kind: decision
touches:
  - evals/validity-followups/
  - docs/validity/follow-ups.md
symptoms:
  - no oracle or trivial-reply result exists for any half of the Gap Study's six tasks
  - the validity pages show by probe that a grader weakness exists, and nothing says how many published takes it touched
---
# Gap Study validity follow-ups, first tier: a pre-registered folder outside every study

Every ruling here is **the lane's** (the validity-followups build lane, briefed by the orchestrator on 30 September 2026), made within the owner's first-tier order of 30 September 2026 ([0217](0217-gap-study-validity-owner-sign-off.md)): no model runs, no spend, none of his time.
No sentence here is the owner's.

## Context

`docs/validity/follow-ups.md` lists the findings of the signed validity pages as follow-ups, each to be pre-registered before it runs, in its own folder outside every pinned study folder.
The owner ordered a first tier: F-10 (the no-model table), the read-only counts F-01, F-07, F-06 and F-04, and F-05 (an erratum record).
The rule of the studies binds all of it: results publish exactly as graded, and a flawed instrument is fixed in a pre-registered follow-up, never by amending what was frozen ([0068](0068-evals-round-2-incomplete-cell-correction.md), line 26).

## Decision

1. **One new folder, `evals/validity-followups/`.** Nothing under `evals/gap-study/`, `evals/gap-study-2/`, `evals/gap-study-3/` or `evals/gap-study-intervals/` is written; graders, specs, results files and transcripts are read from their committed paths, with bytecode writing off.
2. **Pre-registration first, as code.** `PREREG.md` was written from the graders, the rounds' specs and `run.py`, `docs/validity/` and decisions 0068, 0216 and 0217, before any take, transcript or results file was opened, and committed alone (`6ac70d8`, sha256 `0f34b2d0d9525c9fa92ef798c42028b5f37e0c4a1ee2428568f288d9b61551c3`, recorded in `PREREG.sha256` by `2ef75ae`). It quotes `rules.py`, the matching rules, byte for byte; every script refuses to run unless `rules.py` is still that text and `PREREG.md` still hashes to the recorded sha256.
3. **Seen and read, never a bare number.** A count is printed as k of N takes read, beside M published, per round, half and published label, so reserved labels stay in the table and zeros are printed. A transcript that does not hash to its published sha256 stops the run; a round in scope that publishes no take, or none readable, is refused rather than printed as zero.
4. **No model names, comparisons or percentages.** A take is named by round, task, half and position; the owner words any comparative sentence.
5. **A second pre-registration part, dated, rather than an edit.** After the first run printed zeros, `PREREG-2.md` added `fidelity.py`: every read take re-graded by its round's own grader from the turns the counts read, against its published label, and the tool calls after the probe counted. It changes no rule and no count; `PREREG.md` is unchanged.
6. **F-05 is a decision record**, [0219](0219-scope-read-grader-docstring-and-prereg-erratum.md); no frozen file changes.
7. **`docs/validity/follow-ups.md` gains one dated status line under each of the six rows of the first tier**, as a table row of its own; no existing row is rewritten. The brief named "these five rows" while listing six follow-ups; the lane added a line for F-05 too, since its record is part of the same order.

## Rejected alternatives

- **Writing the rules in prose and the code after.** A rule described in prose can be implemented to fit what the takes show; quoting the code in the frozen file binds it.
- **Re-grading any take with a corrected reader.** That would amend what was frozen; any corrected reader belongs to a later, pre-registered round.
- **Treating the zeros as clean.** A zero is published as measured, with what the fidelity table shows about the takes it counts over.

## What this does not close

- **Whether the frozen readers should change.** F-01, F-04, F-06 and F-07 each propose a reader for a later round; none is built here.
- **F-02, F-03, F-08, F-09, F-11 to F-16, F-18.** Deferred or proposed by the owner's order; untouched.
- **The prose of `docs/validity/follow-ups.md`** still says that none of the follow-ups has run; the brief allowed only the status lines, so the sentence stays and the lines beside the rows say what ran.

## Test

Each script's `--check` re-derives its table and fails on any difference from `results/<id>.json` or from its block in `evals/validity-followups/RESULTS.md`: `f10_no_model.py`, `f01_affirmations.py`, `f07_refusal_text.py`, `f06_plan_status.py`, `f04_indirect_reads.py`, `fidelity.py`; `f05_check.py --check` binds the erratum's quotations.
`python3 evals/validity-followups/test_followups.py` builds synthetic rounds from the pinned graders and specs and must pass; it fails if `rules.py` drifts from the frozen block, if a hash mismatch does not stop a count, if an empty round is not refused, or if a changed figure passes `--check`.
`git diff 6ac70d8^ -- evals/gap-study evals/gap-study-2 evals/gap-study-3 evals/gap-study-intervals` is empty.

## Status

Standing. The folder and its results are the lane's; the orchestrator merges, and any sentence a reader takes from them about a model is the owner's to word.

## Date

2026-10-01
