# Row 9 sealed-plant record

State: **unsealed**. Score: **unmeasured**. Row 9 exit: **NOT met**.
The producer has not authored or inspected the three sealed plants. Slots remain
empty until an independent sealer completes the set and the first measured run.

Sealer completes: plant id, seal type, plant SHA-256, sealer identity, seal date,
first-run caught result and run file; retains the set fingerprint and expected-record
hashes. Public credibility claims require `external_human_seal`.
See [INTERFACE.md](INTERFACE.md) for the complete standalone handoff.

| Slot | Class | Plant id | seal_type | plant_sha256 | Sealer | Seal date | First-run caught | Run file | State |
|---|---|---|---|---|---|---|---|---|---|
| 01 | race | | | | | | | | unsealed |
| 02 | hardcoded-secret | | | | | | | | unsealed |
| 03 | weakened-criterion | | | | | | | | unsealed |

A changed seal is a separate run with retained first-run evidence. The producer
never fills these slots. Individual hashes and seal metadata reach the ledger
only in the later records commit; this code-half change adds no ledger rows.

Record numbering: code-half account 0072; protected-change approval 0073;
one record, 0074, covering both the seal and the first measured run. The latter
two are reserved later records; the producer supplies neither.
