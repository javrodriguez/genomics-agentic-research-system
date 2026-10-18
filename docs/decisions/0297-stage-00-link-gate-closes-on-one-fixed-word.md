---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/00_initialize_project/CONTEXT.md
  - gars/tests/test_gate_words.py
symptoms:
  - the agent runs stage00_register.py link on a reply such as "looks fine, but" after T4a
  - T4a asks the user to confirm without naming what reply confirms
---
# Stage 00's link gate closes on one fixed word

Item S00-yes of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner in the step map's answers ("A fixed word (for example "link"), asked again on any other reply").
The wording choices below are the lane's (gars-t74), made under the owner's standing delegation.

## Context

After `inspect`, T4a ended "Confirm to create symlinks under 00_data/<Assay ID>/raw/, or provide a different path", and Process step 12 ran `link` "on confirmation".
Nothing said which reply is a confirmation, so a hedged reply ("looks fine, but sample 4 is odd") could be read as one and the raw files linked.
GARS has no user-prompt hook, so no script can see the reply; the gate is held by the contract alone.

**Reproduction.** At the build base (the frozen Landings A and C head `2d819179`), `test_stage00_link_gate_names_one_word` fails: T4a's last line names no fixed word.

## Decision

1. T4a ends "Reply `link` to create symlinks under 00_data/<Assay ID>/raw/, or provide a different path."
2. Step 11 waits for the reply `link`; step 12 links only on that word alone. A different path goes back to step 9; any other reply, a "yes", an "ok" or a hedged one included, gets T4a again and is never read as `link`.
3. Prose only: no code, guard rule or registry entry changes.

## What this does not close

- **R1** The word is held by the contract, not by code: an agent that ignores its contract can still run `link`. `link` itself writes only symlinks into an empty `raw/` and refuses a populated one without `--force`, which the contract forbids.
- **R2** No live session has walked the new gate; it is checked by the test, not by a run.

## Test

`gars/tests/test_gate_words.py::Stage00LinkGateTests::test_stage00_link_gate_names_one_word` reads the stage 00 contract and requires T4a's last line to name exactly the backticked word `link`, and the one Process step that runs `stage00_register.py link` to name `link` as its reply and to send T4a again on any other reply.
It was red at the build base and is green here; restoring the old T4a line turns it red.
`tests/check_contracts.py` stays clean.

## Status

Standing. The change record for the stage 00 link gate; prose only, so no approval record is needed.

## Date

2026-10-17
