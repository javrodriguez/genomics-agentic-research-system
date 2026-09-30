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
Later rounds are listed in the lane report.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected change as merged.

1. **`.github/workflows/ci.yml`**: one new job, `geo-recompute-binding`, appended after the last job: a matrix over `ubuntu-latest`, `macos-latest` and `windows-latest` (fail-fast off), checkout at the default depth, Python 3.12, then `python reproduction/gse58638/test_recompute.py` and `python reproduction/gse58638/recompute.py --check-published`. It needs no network and no history. Zero lines removed; every other job and step is as at `37a8d94`.
2. **`.github/workflows/geo-recompute.yml`**, new: `workflow_dispatch` and a monthly schedule (`17 6 3 * *`), ubuntu-latest, 90-minute limit, running `python3 reproduction/gse58638/recompute.py` exactly as the README prints it and writing its report, exit code and wall time to the job summary. It streams 8.8 GB from NCBI per run and stores nothing. No run has been dispatched by the lane; the first dispatch is the owner's word.

Outside the protected prefixes, recorded for completeness: the new folder `reproduction/gse58638/`, the README sub-bullet, the DEVELOPMENT.md changelog row, 0241, this record and the index.
The public push waits for the owner's own typed word.

## Test

`python3 reproduction/gse58638/test_recompute.py` (58 tests) passes at the branch head with one test skipped by name (`test_addendum_binding`, until the row 3a addendum is in RESULTS.md) and, on Windows, `test_results_md_read_as_utf8` skipped by name (the C locale is a POSIX device); `python3 reproduction/gse58638/recompute.py --check-published` exits 0.
A change that removes the job leaves `expected.txt`, the script and RESULTS.md's quotations unbound on push; the job's tests plant a changed deposit byte, a short read, a zero-record file, a duplicated or moved quotation, a changed report line and a metadata-only change, and require the named exit code; 0241's mutation witness (20 of 20 killed) shows each named test can fail.

## Status

Standing.

## Date

2026-09-30
