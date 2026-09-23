---
date: 2026-09-23
status: standing
kind: decision
touches:
  - docs/decisions/0063-row-12-lifecycle-status-writer.md
  - docs/decisions/0069-row-12-fix-round-minors.md
  - docs/decisions/0070-row-12-fix-round-owner-approval-of-protected-changes.md
symptoms:
  - 0063 and 0069 record "Row 12 exit NOT met" after every row-12 deliverable is merged, green and approved
  - the remaining gap is live scheduler evidence and later rulings, not row-12 code
---
# The owner closes row 12 in tests and moves live scheduler acceptance to its own item

Addendum to [0063](0063-row-12-lifecycle-status-writer.md), [0069](0069-row-12-fix-round-minors.md) and [0070](0070-row-12-fix-round-owner-approval-of-protected-changes.md), which stay as written.

## Context

Row 12 of the v1.0.1 guideline delivers the closed-enum `STATUS` writer with preserved Slurm reasons and `CANCELLED`, `idempotency_key` in `submit.sh`, the `cancel` verb, the failure-class rules and `test_no_false_completion.py`.
Its exit is: duplicate side effects 0; every wrapper uses the writer; 0 false completions.
Row 12 merged with the owner's approval in [0066](0066-row-12-owner-approval-of-protected-changes.md), and its post-merge fix round merged with his approval in [0070](0070-row-12-fix-round-owner-approval-of-protected-changes.md).
At main `16510c5` the suite collects 421 tests and passes in all three CI modes, `test_no_false_completion.py` included; at `c41ca7c`, one README sentence later, both GitHub workflows (CI and Fresh clone) pass.
0063 and 0069 still say "Row 12 exit NOT met", because that evidence comes from stub schedulers: no run on real Slurm, `sacct` and `scancel`, or on the cluster's Python 3.6.8, is recorded.

## Decision

The owner closes row 12 on 23 September 2026: its deliverables are built, merged and approved, and its exit holds in the test suite against stub schedulers.
Live scheduler acceptance moves out of row 12 into its own named item, to be run in the first cluster session, because it needs the cluster rather than more row-12 code, and other rows need the same session.
That item runs a real submit, status, cancel and collect on Slurm under Python 3.6.8 and records the real `sacct` and `scancel` output shapes against the writer's state mapping.
Where that run disagrees with the stubs, the fix is a new record against this one; the closure does not claim the live result in advance.
0063 and 0069 keep their "NOT met" wording, because decision records are append-only; this record is what changes the row's standing.

## What this does not close

- Live scheduler acceptance itself: real Slurm, `sacct` and `scancel` output shapes, and Python 3.6.8 execution.
- Separate-user execution: executed scripts share the agent's OS user and can alter executor-owned evidence (0069, 0070).
- Ambiguous submission recovery (ruling 9) and published benchmark pins (ruling 10).
- Round-4 NOTE-1: accounting loss can leave VALIDATING → STALE until the owner rules on the durable state table.
- The round 7 review NOTEs that 0070 lists.
- The reviews were fresh-context model reviews on the same machine and OS user (`independent_context`), not an external human seal.

## Test

`python3 tests/run_tests.py` at `16510c5` collects 421 tests and passes in the three CI modes (skipped 11, 55 and 86), `test_no_false_completion.py` included; `c41ca7c` differs from it only in one README sentence, and the CI and Fresh clone workflows pass on `c41ca7c`.
This record changes no code; with it placed and `bash docs/decisions/build_index.sh` re-run, row 11's record checker (`decision_links` in `gars/_system/hooks/pre-commit`) accepts every record.
The closure is reversed by a later record if the live acceptance item finds a false completion.

## Status

standing

## Date

2026-09-23
