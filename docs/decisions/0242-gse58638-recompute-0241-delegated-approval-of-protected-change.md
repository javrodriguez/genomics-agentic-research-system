---
date: 2026-09-30
status: standing
kind: decision
touches:
  - .github/workflows/ci.yml
  - .github/workflows/geo-recompute.yml
symptoms:
  - the GSE58638 recompute (0241) adds a CI job to .github/workflows/ci.yml and a new workflow under .github/workflows/, protected paths, with no owner approval record
---
# GSE58638 recompute 0241: approval of its protected CI change, under the owner's delegation

Addendum to [0241](0241-gse58638-deposit-recompute.md).
The files this record approves are protected (`.github/workflows/`; §9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written under that delegation and labelled as such: **approved by Glitch under Javier's 23 Sep delegation**; no sentence in it is the owner's.
Its shape follows [0211](0211-gap-study-intervals-0210-delegated-approval-of-protected-change.md) and [0201](0201-small-fixes-0200-delegated-approval-of-protected-change.md).

## Context

0241 was built on branch `lane/geo-recompute` of the private mirror, from main `37a8d94`, by a Claude Code producer (Opus 5.5) in a cloud session, working from the lane brief, the plan's sections 2-8 and PREREG-2, and reviewed by fresh Claude Code contexts (Opus 5.5), each over a separate clean checkout of the candidate that never saw the producer's transcript.
**Same-model cost.** The producer and the reviewers are the same model; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent). The reviews were kept independent by fresh contexts, separate checkouts, a stated threat model and no access to the producer's transcript.
Producer commits, red first: `4c4d7e9` (the tests and fixtures, red: `ModuleNotFoundError: No module named 'recompute'`), then the script, the records and the jobs, the mutation findings and the review findings, as listed in the lane report `lane-reports/geo-recompute.md`.
Reviews, each a fresh `claude -p --model claude-opus-5-5` over its own `--no-local` clone of the candidate with no remote, briefed with the plan's sections 2-5, PREREG-2, the brief's rulings 4, 5, 7 and 8, and the threat model, with a fail-closed verdict reader (only a final `VERDICT: CLEAN` ends the loop):
`r1` on `1b3ded4`, CHANGES (two MAJOR, six MINOR, two NOTE): F-1 MAJOR the metadata section of `expected.txt` was unbound on push, now pinned; F-2 MAJOR the fixtures README implied agreement with UCSC's reader that was never run, reworded, and 0241 records property (e) as open; F-3 the one step-1 cell held to the recompute, kept on the orchestrator's answer and labelled as awaiting PREREG-3; F-4 "both figures come from B6" overclaimed, reworded (T2 also reproduces under B4); F-5 the addendum was found only by one literal heading, now also by content, and a changed RESULTS.md without a detected addendum fails; F-6 an unbound figure in the addendum passed, now every decimal must be accounted for; F-7 the records cited evidence not in the repository, now in 0241; F-8 two refusals had no functional test, added; F-9 the regrade now fails without `expected.txt`; F-10 no change.
`r2` on `9301a33`, CHANGES (one MAJOR, four MINOR, four NOTE): F-1 MAJOR property (e) does not hold, no run of UCSC's reader exists: **not fixable on the cloud machine** (egress policy), left open for the orchestrator; F-2 the named step-1 exception has no dated PREREG-3: **left open**, the orchestrator's to write; F-3 an addendum denying the reversal bound green, now it must state it; F-4 a line-73 figure called a recompute output passed, now line 73's figures count only inside their quotations; F-5 the lane report lacked this run, appended; F-6 a tautological per-chromosome check removed; F-7 the derived T2 sentence now reads "Recomputed:" and comes first; F-8 0241 says the counts are bound to the bytes only by the regrade; F-9 no change.
`r3` on `74b5985`, CHANGES (two MAJOR, two MINOR, two NOTE): F-1 MAJOR a consistent forgery of `expected.txt` (counts changed, re-rendered by the script's own renderer) passed on push, now the counts and sha256 are pinned (`COUNTS_SHA256`) and a test plants that forgery; F-2 MAJOR property (e), as r2's F-1, left open; F-3 the step-1 cell awaits PREREG-3, and r3 explained both differing cells as step 1 rounding twice (0241 corrected); F-4 the lane report, appended with this run; F-5 and F-6 no change.
`r4` on `32e5a35`, CHANGES (one MAJOR, three MINOR, one NOTE): F-1 MAJOR property (e), and F-2 the step-1 cell without PREREG-3, both as before and left open; F-3 three wordings that restated line 73's figures as recompute outputs bound green, now each line-73 span must occur exactly once in its quoted form and a metadata figure only in its own form; F-4 0241 no longer says a script edit without a re-run fails on push; F-5 no change.
`r5` on `e85030a`, CHANGES (one MAJOR, three MINOR, three NOTE): F-1 MAJOR property (e), left open; F-2 the binding's line said "PREREG-2 R3 holds" with one cell excepted, now it names the exception; F-3 no record named the blob that produced `expected.txt`, now 0241 records the final run's blob and output; F-4 the lane report section, committed; F-5 the GSM1415877 B4 difference reworded as consistent with double rounding or step 1's near-threshold tile; F-6, F-7 no change.
`r6` on `ce94e85`, CHANGES (one MAJOR, two MINOR, three NOTE): F-1 MAJOR property (e), and F-3 the PREREG-3 cell, left open; F-2 a same-size change to a deposit exited 2 (a parse refusal) instead of 1 (the deposit changed), and a malformed chromosome name escaped as a traceback: now every byte is hashed before a parse error is reported, the sha256 comparison decides first, and malformed structure is always a named refusal; the plan's step-3 bad-magic test now pins the malformed bytes, since a same-size bad-magic copy of a pinned deposit is a changed deposit; F-5 a wording fix in 0241; F-4, F-6 no change.
Because r2's F-1 and F-2 (and each later round's same two) cannot be closed by the lane, the review loop cannot reach CLEAN on this machine; the lane report lists every round and what stays open.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected change as merged.

1. **`.github/workflows/ci.yml`**: one new job, `geo-recompute-binding`, appended after the last job: a matrix over `ubuntu-latest`, `macos-latest` and `windows-latest` (fail-fast off), checkout at the default depth, Python 3.12, then `python reproduction/gse58638/test_recompute.py` and `python reproduction/gse58638/recompute.py --check-published`. It needs no network and no history. Zero lines removed; every other job and step is as at `37a8d94`.
2. **`.github/workflows/geo-recompute.yml`**, new: `workflow_dispatch` and a monthly schedule (`17 6 3 * *`), ubuntu-latest, 90-minute limit, running `python3 reproduction/gse58638/recompute.py` exactly as the README prints it and writing its report, exit code and wall time to the job summary. It streams 8.8 GB from NCBI per run and stores nothing. No run has been dispatched by the lane; the first dispatch is the owner's word.

Outside the protected prefixes, recorded for completeness: the new folder `reproduction/gse58638/`, the README sub-bullet, the DEVELOPMENT.md changelog row, 0241, this record and the index.
The public push waits for the owner's own typed word.

## Test

`python3 reproduction/gse58638/test_recompute.py` (64 tests) passes at the branch head with one test skipped by name (`test_addendum_binding`, until the row 3a addendum is in RESULTS.md) and, on Windows, `test_results_md_read_as_utf8` skipped by name (the C locale is a POSIX device); `python3 reproduction/gse58638/recompute.py --check-published` exits 0.
A change that removes the job leaves `expected.txt`, the script and RESULTS.md's quotations unbound on push; the job's tests plant a changed deposit byte, a short read, a zero-record file, a duplicated or moved quotation, a changed report line and a metadata-only change, and require the named exit code; 0241's mutation witness (21 of 21 killed) shows each named test can fail.

## Status

Standing.

## Date

2026-09-30

## Addition, 30 Sep 2026 (the merge at home)

Written by glitch-14's merge lane on the Mac, under the same delegation; no sentence here is the owner's.
The lane's commits were replayed onto public main `68ec902`, where the row 3a addendum is in RESULTS.md, together with the mirror's review-r6 commit, which the cloud lane pushed after its report.
The lane report named above (`lane-reports/geo-recompute.md`) stays in the private mirror; lane reports do not land in this repository.
Nothing in the approved protected change moved: on `68ec902` the `ci.yml` diff is the one appended job (24 lines added, none removed), and `geo-recompute.yml` is as the lane wrote it.
The Test section above describes the lane's candidate and is superseded here: with the addendum in the base, `test_addendum_binding` runs and never skips, and the test count, the binding's output line and the mutation witness on the merged candidate are recorded in 0241's addition of the same date.
The home review (a fresh `claude -p --model claude-opus-5-5` in a no-remote `--no-local` clone of the merged candidate, briefed with the plan's sections 2-5, PREREG-2, PREREG-3 and the threat model, and asked to cover the r6 commit explicitly) is recorded in 0241's addition.
