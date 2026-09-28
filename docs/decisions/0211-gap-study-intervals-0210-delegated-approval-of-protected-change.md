---
date: 2026-09-28
status: standing
kind: decision
touches:
  - .github/workflows/ci.yml
symptoms:
  - the Gap Study intervals change (0210) adds a CI job to .github/workflows/ci.yml, a protected path, with no owner approval record
---
# Gap Study intervals 0210: approval of its protected CI change, under the owner's delegation

Addendum to [0210](0210-gap-study-intervals.md).
The file this record approves is protected (`.github/workflows/ci.yml`; §9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such: **approved by Glitch under Javier's 23 Sep delegation**; no sentence in it is the owner's.
Its shape follows [0201](0201-small-fixes-0200-delegated-approval-of-protected-change.md) and row 14's [0122](0122-row-14-delegated-approval-of-protected-changes.md), which approved the last added CI step.

## Context

0210 was built on its own branch from public main `ef6250d` by a Claude Code producer (Opus 5.5) in an isolated clone with no remote, and reviewed three times by fresh Claude Code contexts (Opus 5.5), each from a separate checkout with no remote that never saw the producer's transcript.
**Same-model cost.** The producer and the reviewers are the same model; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent). The reviews were kept independent by fresh contexts, separate no-remote checkouts, a stated threat model and no access to the producer's transcript.
Producer commits, red first: `e2a325f` (the tests, red at `ef6250d`: `FAILED (failures=1, errors=24)`), `3a5a80c` (the script and its generated page), `5de4b2a` (0210, the CI job, the `docs/EVALS.md` paragraph, the index), `bd156a0` (four guard tests from the lane's mutation run), `50028dd` (review r1's findings), `0e38639` (a real-git listing witness from the mutation run), `53c466c` (review r2's findings).
Reviews, kept outside the repository and cited by their kit folders:
`gars-e1-intervals/reviews/r1` APPROVE WITH CHANGES on `ef6250d..bd156a0` (one MAJOR, three MINOR, two NOTE): F-1 MAJOR, the forgery witnesses injected their own readers, so a blob reader on the working tree survived; a real-git witness was added. F-2 the Fisher qualification; F-3 the printed-width label; F-4 the test count; F-5 a wording note; all fixed. F-6 NOTE out of scope.
`gars-e1-intervals/reviews/r2` APPROVE WITH CHANGES on `bd156a0..0e38639` (one MAJOR, one MINOR, four NOTE): F-1 MAJOR, the real-git forgery was never committed, so a reader of HEAD or the index survived; the forgery is now committed on top of the done commit. F-4 wording; F-6 the witnesses' git runs with signing off and no hooks folder; both fixed.
`gars-e1-intervals/reviews/r3` APPROVE on `0e38639..53c466c`, no findings. The fail-closed reader read CLEAN, so the loop ended.
The lane's mutation run on `intervals.py`, from a clean clone of `53c466c`: 19 mutants (counts from `k` or `n`, the tail level, inward rounding of either bound, the page, data, changed-input, listing and zero checks disabled, the binding skipped, a one-sided Fisher test, the power threshold, the verdict guard, Wilson coverage made exact, and blob or listing readers on the working tree, HEAD or the index), 19 of 19 killed by the named test.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected change as merged.

1. **`.github/workflows/ci.yml`**: one new job, `gap-study-intervals`, appended after the last job: checkout at full depth, Python 3.12, `python3 evals/gap-study-intervals/intervals.py --check`, then `python3 evals/gap-study-intervals/test_intervals.py` with `TMPDIR` set to the runner's temp folder. Zero lines removed; every other job and step is as at `ef6250d`.

Outside the protected prefixes, recorded for completeness: the new folder `evals/gap-study-intervals/`, the one paragraph in `docs/EVALS.md`, 0210, this record and the index.
The public push waits for the owner's own typed word.

## Test

`python3 evals/gap-study-intervals/intervals.py --check` exits 0 and `python3 evals/gap-study-intervals/test_intervals.py` runs 31 tests OK at the branch head; the job's own witness tests plant a label, count, interval or input change and require the check to fail.
A change that removes the job, or runs it shallow, loses the done-commit binding: the check refuses with exit 2 in a shallow clone.

## Status

Standing.

## Date

2026-09-28
