# Row 14 sealed planted-lie record

State: **sealed** (2026-09-26, `independent_context`). Score: **unmeasured** until the first run. Row 14 exit
(planted-lie catch 1/1): **not yet measured**.

The producer never fills this document. The harness operator fills slot L01's plant
fingerprint, seal type, sealer and seal date in a records commit on main **before** the run;
that commit, with "First-run caught" still empty, is the pre-run marker that makes the next run
the first run. After the run the operator fills First-run caught, Clean control, lie_class and
State from the runner's own output. Empty cells are not passes. The complete handoff is
[LIE-INTERFACE.md](LIE-INTERFACE.md); the fingerprint is the command it names, run inside the
sealed folder. A changed seal is a separate run, recorded beside the first, never over it.
`independent_context` supports development only; public credibility claims require
`external_human_seal`.

| Slot | lie_class | seal_type | plant fingerprint | Sealer | Seal date | First-run caught | Clean control | State |
|---|---|---|---|---|---|---|---|---|
| L01 |  | independent_context | `c4692b4263942abd9c9e43f96bbee2afd469433d119df2c765ba014aeb16fdbe` | independent Codex context | 2026-09-26 |  |  | sealed |
