# Restore evidence

Format: `date, RPO_h, RTO_min, PASS|FAIL` (UTC).
Thresholds: dated drill ≤ 30 days old; RPO ≤ 24 h; RTO ≤ 60 min.
The first destructive drill ran on Node 1 on 2026-09-22 and passed (decision 0054). A backup that
has never been restored is not verified; this one has, once, on synthetic data.
Public credibility stays unmeasured until external_human_seal evidence exists.

| Date | RPO_h | RTO_min | Result |
|---|---|---|---|
| 2026-09-22T16:55:13Z | 13.167400 | 0.284136 | PASS |

Seal: independent_context (0044 Q9); public restore credibility stays unmeasured until an
external_human_seal drill. Target: a distinct marked recovery database; §13.2's primary deletion
is not performed (0044).
The drill restored the scheduled (timer-made) backup, not one made for the drill, into a distinct
marked database, and verified every table against a canary chosen and written on the node and never
displayed. The data was synthetic: about 470,000 rows in three tables, a 66 MB database, so the RTO
is not a measurement at real scale. Next drill due by 2026-10-22.

Provenance of each drill, transcribed from its decision record; the release check joins it on the drill's timestamp.

| Date | Venue | Source | Target | Data | Seal | Record |
|---|---|---|---|---|---|---|
| 2026-09-22T16:55:13Z | node1 | scheduled-offmachine | recovery-db | synthetic | independent_context | 0054 |
