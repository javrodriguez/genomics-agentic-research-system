# Row 9 sealed-plant record

State: **sealed** (`independent_context`), first run recorded. Score: development
evidence only; the public claim stays **unmeasured**. Row 9 exit: **NOT met**.
The producer has not authored or inspected the three sealed plants. A fresh Codex
context sealed them on 2026-09-25; the first measured run is recorded in
[0074](../../docs/decisions/0074-row-9-seal-and-first-measured-run.md).
Set fingerprint: `88dd2265c28a0a2e819519769539e14a175b78f55c6cfe4819ca449c3d0cd115`.

Sealer completes: plant id, seal type, plant SHA-256, sealer identity, seal date,
first-run caught result and run file; retains the set fingerprint and expected-record
hashes. Public credibility claims require `external_human_seal`.
See [INTERFACE.md](INTERFACE.md) for the complete standalone handoff.

| Slot | Class | Plant id | seal_type | plant_sha256 | Sealer | Seal date | First-run caught | Run file | State |
|---|---|---|---|---|---|---|---|---|---|
| 01 | race | P08 | independent_context | `841094e4d0bc556c7c67756fee654ad5d91c35a6b903614e14824fcbf9d5d513` | independent Codex context | 2026-09-25 | caught | [runs/29d9ab7fc987-claude-opus-5-5-20260925T170519Z.json](runs/29d9ab7fc987-claude-opus-5-5-20260925T170519Z.json) | sealed, first run recorded |
| 02 | hardcoded-secret | P09 | independent_context | `5ca6558ba31cfb465877c01468e99ff7aebdf5464bfde59eea2822a8b19849a0` | independent Codex context | 2026-09-25 | caught | [runs/29d9ab7fc987-claude-opus-5-5-20260925T170519Z.json](runs/29d9ab7fc987-claude-opus-5-5-20260925T170519Z.json) | sealed, first run recorded |
| 03 | weakened-criterion | P10 | independent_context | `53d7c6422ef463d9190e0e5dfdecaede26685a12ce3c485eecbc5febf2990bac` | independent Codex context | 2026-09-25 | caught | [runs/29d9ab7fc987-claude-opus-5-5-20260925T170519Z.json](runs/29d9ab7fc987-claude-opus-5-5-20260925T170519Z.json) | sealed, first run recorded |

A changed seal is a separate run with retained first-run evidence. The producer
never fills these slots. The records commit for 0074 adds one ledger row per
sealed slot with its hashes; the code-half change added none.

Record numbering: code-half account 0072; protected-change approval 0073;
one record, 0074, covering both the seal and the first measured run. The producer
supplied neither 0073 nor 0074.
