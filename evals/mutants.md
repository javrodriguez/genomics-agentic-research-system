# Row 3 sealed-mutant record

State: **unsealed**. Score: **unmeasured**. Row 3 exit: **NOT met**.
The producer has not authored or inspected a sealed set. The ten slots below are intentionally
empty; public runner-control faults are not members of this set.

Sealer completes: seal type (`independent_context` or `external_human_seal`), sealer identity,
seal date, source SHA, hashes of the ten diffs and expected records, environment/skips,
first-run score and run SHA. Public credibility claims require `external_human_seal`.
See [MUTANTS-INTERFACE.md](MUTANTS-INTERFACE.md) for the complete handoff.

| Slot | Mutant id | Requirement attacked | Killing test or `survived` | Run SHA | State |
|---|---|---|---|---|---|
| 01 | | | | | unsealed |
| 02 | | | | | unsealed |
| 03 | | | | | unsealed |
| 04 | | | | | unsealed |
| 05 | | | | | unsealed |
| 06 | | | | | unsealed |
| 07 | | | | | unsealed |
| 08 | | | | | unsealed |
| 09 | | | | | unsealed |
| 10 | | | | | unsealed |

Record `ineffective` explicitly if returned; never convert it into a kill or silently remove
it from the denominator. A changed seal is a separate run with retained first-run evidence.
The sealer fills this document from its own run after the producer commit.
