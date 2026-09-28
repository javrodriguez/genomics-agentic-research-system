---
date: 2026-09-28
status: standing
kind: decision
touches:
  - evals/gap-study-intervals/
  - docs/EVALS.md
  - .github/workflows/ci.yml
symptoms:
  - the Gap Study publishes "k of 3" counts and a "holds" verdict with no interval and no statement of what three takes can tell apart
  - a half's graded count read from its `n` field prints three takes where one was graded
---
# Gap Study intervals: exact per-half intervals for rounds 1-3, re-derived in CI

Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 and within the owner's 28 September 2026 direction that makes the AI-evaluation track a build priority (approved 15:21 EDT); no sentence in this record is the owner's.
That approval chose two things this record follows: the page is linked from `docs/EVALS.md` outside its generated markers, as [0068](0068-evals-round-2-incomplete-cell-correction.md) placed its correction, and the sensitivity result is published with no sentence comparing models.
[0211](0211-gap-study-intervals-0210-delegated-approval-of-protected-change.md) approves the protected CI change; this record does not write it.

## Context

The three Gap Study rounds publish, per half (one task, one model, one half), the correct takes out of three, and call a task held when all three takes are correct on both halves.
No published figure says how uncertain a count of three is, and nothing says that two halves of three takes can never be told apart at the 0.05 level by a two-sided Fisher exact test, whatever their counts.
Round 2 has one half whose results file carries `n: 3` over a single graded label (0068), so any figure read from `n` would overstate what was graded.
The rounds are pinned instruments: their folders are copied byte for byte into later rounds' manifests, their results publish exactly as graded, and a flaw is fixed only in a pre-registered follow-up.

## Decision

1. **A new folder, `evals/gap-study-intervals/`, outside every pinned study folder.**
   `intervals.py` (standard library only) reads the committed results files `evals/gap-study*/results/*.json` of rounds 1 to 3 and writes only `INTERVALS.md` and `intervals.json` in its own folder.
   Nothing is written, imported or regraded inside `evals/gap-study/`, `evals/gap-study-2/` or `evals/gap-study-3/`.
2. **What is counted.** A half's graded takes are the labels in its results file (`len(labels)`) and its correct takes are the labels whose verdict is `correct`; the `n` and `k` fields are never read.
   A verdict other than `correct` or `incorrect`, or a half other than `positive` or `control`, stops the script rather than being guessed at.
   A half with no label (round 1's dropped local tier) is printed as not run, with the state its results file records, and gets no interval.
3. **The method: Clopper-Pearson, two-sided, 0.95.**
   Why: its coverage is at least 0.95 at every per-take probability for every number of takes, and these halves have one or three takes, where the approximate intervals fall short.
   The page derives the evidence itself: the lowest coverage of Clopper-Pearson and of the Wilson score interval on a 0.001 grid of p, at one and at three takes (its "Method" table).
   Wilson's is well under 0.95 at both sizes; Clopper-Pearson's never is.
   The bounds are computed in exact rational arithmetic (a search over the 0.001 grid on exact binomial tails, no floating point), and each is rounded outward (lower down, upper up), so the printed interval contains the exact one and the output is identical on every platform.
   No point estimate is printed: the studies publish no rate, and a count of three carries none.
4. **Beside the intervals, three post-hoc readings, each labelled so.**
   Per round, the smallest two-sided Fisher exact p that any two halves of the sizes graded could reach (every take correct in one, none in the other); it is a property of the design, and no test between actual halves is computed or published.
   A hold read as six correct takes of six, with the chance of a hold under a per-take probability p.
   A sizing table for any later round: the widest printed interval, the lower bound when every take is correct, the smallest attainable Fisher p, and the smallest difference between two per-take probabilities centred on 0.5 that the test finds with power 0.80.
5. **`--check`, run by CI at every push in a new job.**
   It re-derives the page and the data and requires both byte-identical to the committed files; it names any results file added, removed or changed since the page was generated.
   It binds every results file to its blob at its round's done commit (`b735229`, `bf065fe`, `e2979b3`, the refs the three study jobs pin, asserted equal by a test), so a results file and a page rewritten together still fail.
   It refuses, exit 2, in a shallow clone or outside git, rather than passing on a binding it could not read; the job checks out full history.
   It prints graded against seen, and a check that saw no graded half fails.
6. **The mutation witness**, the job's second step: a flipped label, a changed interval digit in the page, a changed count in the data, a changed `n` field (which moves no figure but changes the bound bytes), a removed results file, an empty input set, and a consistent forgery of results and page (against a real git commit, and against injected readers) each make the check fail; a changed `k` field moves no figure, an unknown verdict stops the script, and an input set with no graded half fails even with a regenerated page; an unplanted copy passes, so the witness is not vacuous.
7. **The link.** One dated paragraph after the two opening lines of `docs/EVALS.md`, before every generated block, names the page, says it is a secondary analysis per half and never pooled, and cites this record; every table on that page stays byte-identical.
   The page and that paragraph carry no percentage and no comparative word, which a test enforces.

## Rejected alternatives

- **Wilson or Jeffreys intervals.** Narrower, but they undercover at one and three takes (the page's Method table), and a record that claims little should not rest on an approximation at its smallest sizes.
- **A Wald interval or a point estimate.** At zero or three of three a Wald interval has zero width, and a point estimate is a rate the studies deliberately do not publish.
- **Pooling takes across rounds, tasks or halves** for narrower intervals. The rounds' instruments differ and the halves are different conditions; nothing is pooled.
- **Editing the rounds' tables or folders** to add the intervals. They are frozen; this page sits beside them.
- **Publishing Fisher tests between actual halves or models.** Every comparative sentence about a model is the owner's (the rounds' Gate 3); only the design property is published.
- **Hard-coding the results files' hashes or figures in the page.** Every figure and hash is derived by the script, and `--check` re-derives it.

## What this does not close

- **Independence.** Each interval assumes a half's takes are independent draws with one per-take probability; that is a model of the takes, not a measurement.
- **The grading itself.** The check binds the page to the committed results and those to the rounds' done commits; whether each take was graded right is the rounds' own checks, run by their pinned jobs.
- **Round 3's section of `docs/EVALS.md`** does not exist yet and stays the owner's; the page already covers round 3, and a link from that section can follow when it is written.
- **The Layer B study and the Haiku pre-study** are not covered: the first has no halves of this shape, and the pre-study changed its driver and is never pooled with a round.

## Test

`python3 evals/gap-study-intervals/test_intervals.py`: 25 tests written first, red at `ef6250d` (`FAILED (failures=1, errors=24)`, the script absent); five more added from the lane's mutation run and review; all 30 green at the branch head.
They bind the known bounds at one and three takes, outward rounding against the closed forms for zero and all correct up to fifty takes, the Fisher p and power against an independent floating-point version, Clopper-Pearson's coverage at or above 0.95 and Wilson's under it at three takes, the round 2 half graded from its one label, the done commits equal to the pinned refs, and the witness plants above; the fault that must make CI fail is any planted change to a label, count, interval or input.
`python3 evals/gap-study-intervals/intervals.py --check` prints `graded against seen: 3 rounds, 15 results files, 114 halves seen, 90 graded, 24 not run`, both files `exactly what the script derives`, `done-commit binding: 15 of 15 results files equal their blobs`, and exits 0.
The lane's mutation run on `intervals.py` and the review are recorded in 0211.

## Status

Standing.
The implementation and this record are the lane's; the public push waits on the owner's word.

## Date

2026-09-28
