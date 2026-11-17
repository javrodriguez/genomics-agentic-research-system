---
date: 2026-11-17
status: standing
kind: decision
touches:
  - docs/ops/restore-log.md
  - docs/implementation/dod_current.md
  - tests/test_release_check.py
---
# The second restore drill, run on Node 1

## Context

The first destructive restore drill ran on Node 1 on 2026-09-22T16:55:13Z and passed (0054).
Its next drill was due by 2026-10-22 (30 days), so the restore evidence had gone stale.
This record is the second drill, run on 2026-11-17 with the same kit, venue and target as 0054.
The facts below are transcribed from Node 1's own restore log, read on 2026-11-17 by the operator context.

## Decision

- **Venue, source and target as 0054:** Node 1, container mode, the newest **timer-made** archive from the scheduled off-machine copy, restored into the distinct, marked recovery database (0044's supported target).
  The archive was `gars-20261117T033002Z.dump.gpg`, made by the nightly timer at 03:30Z with `result=PASS`, never one made for the drill (§13.2).
  The drill's RPO, worked back to that archive's time, confirms which archive it took.
- **R-095 kept strictly:** the owner ran the drill himself, `drill --destroy`, and it exited 0.
- **The canary is unseen.** It was written on the node (`canary=written sha256=c262644f9f791dfcdfc125ca5eeeb607df265c65ca53aa95b3be000630df1174 tables=3`) and never displayed, so the value is unknown to the operator context.
  The seal class is therefore `independent_context`, not `external_human_seal`.
- **The data is synthetic,** the same three tables as 0054.

## Evidence

- **Drill:** `2026-11-17T21:06:31Z, 17.608207, 0.330002, PASS`.
  RPO 17.61 h and RTO 20 s, against 24 h and 60 min.
  Exit 0, and no `result=FAIL` line anywhere (0047).
- **Negative controls, in order, before the drill:**
  - a dry run with no canary gave `FAIL reason=canary_missing`;
  - a dry run against the unmarked target gave `FAIL reason=target_not_marked`;
  - after the marker, a dry run gave `DRY_RUN rpo_h=17.600626`, resolving to the same scheduled archive the drill then used.
- **Source intact afterwards:** drill_claims 20000, drill_runs 50000 and drill_samples 400000 rows, a 66 MB database, unchanged by the drill.
- **Provenance row, as transcribed into [restore-log.md](../ops/restore-log.md):**
  `| 2026-11-17T21:06:31Z | node1 | scheduled-offmachine | recovery-db | synthetic | independent_context | 0325 |`

## Repository changes

- The result row and the provenance row are appended to [restore-log.md](../ops/restore-log.md), and `python3 scripts/release_check.py` regenerated the restore-drill cell in `docs/implementation/dod_current.md`, which now cites this record.
- `tests/test_release_check.py` pinned the repository's latest drill to 0054's row, so the repository-bound tests now pin this one: the restore cell, the RPO tamper, the provenance-upgrade edits and the 14-day tag ageing.
  Fixture tests keep 0054's values, which stay a valid evidence shape.

## What this does not close

- **§13.2's primary deletion** is not performed; the target is a distinct recovery database (0044).
- **`external_human_seal`:** the public claim that the system restores reliably stays unmeasured.
- **RTO at real scale:** measured on 470,000 synthetic rows (a 66 MB database), not on real data.
- Everything else 0054 left open stays open; this drill re-dates the evidence and changes nothing in the kit.

## Test

- `python3 scripts/release_check.py --check` prints `DoD cells verified: 13/13 byte-stable`, and the restore-drill cell reads this drill, qualifying, with seal `independent_context (0325)`.
- `python3 -m unittest discover -s tests -p test_release_check.py` passes; it fails if the drill's RPO is edited past 24 h, if the provenance row is upgraded to `external_human_seal`, `primary` or `real` data that this record does not quote, or once the drill is more than 14 days old at tag time.

## Status

Standing.
The drill was run by the owner on Node 1; this record transcribes its evidence and implements no new behaviour.

## Date

2026-11-17. The next drill is due by 2026-12-17 (30 days).
