---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/tests/test_gate_words.py
symptoms:
  - the agent replies "Samplesheets written" after the read-only check, with nothing written
  - after a clean check the agent skips the exclusion, overwrite and integrity questions
---
# Stage 01's exit-code table: a clean check is not the end of the stage

Item S01-table of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner in the step map's answers ("The table's row for a clean check names the order the steps give, and says that the writing script, not the check, completes the stage").
The wording is the lane's (gars-t74), made under the owner's standing delegation.

## Context

Stage 01's Definitions told the agent that the script's exit code, not its reading of the output, decides the branch; the table's one exit-0 row read "clean (checked, or written)" and routed to T2 then T4.
Step 3 sends the agent to that table after the read-only `--check`, so the table and Process steps 6 to 8 (T7, T5, T8) disagreed: an agent following the table reported the stage complete after a check that wrote nothing, and never asked the exclusion, overwrite or integrity questions.

**Reproduction.** At the build base (the frozen Landings A and C head `2d819179`), `test_stage01_check_exit0_row_names_the_step_order_and_the_writer` fails: the table has no exit-0 row for the check.

## Decision

1. The exit-0 row splits in two. A clean `--check` (step 3) writes nothing and is not the end: it goes to steps 6, 7 and 8 in that order (T7, T5, T8 as each applies), then the writer at step 9, and only the writer completes the stage. The writer's exit 0 (step 9) keeps T2 then T4.
2. Prose only, one table; the Process steps are unchanged. The stage 01 contract was also edited by Landing A (record 0291), whose paragraphs this does not touch.

## What this does not close

- **R1** The table is prose: nothing in code stops an agent from sending T2 after a check. Item S01-yes binds the writer's gates to the check's record; T2's numbers still come only from the writer's output.
- **R2** No live session has walked the new row; it is checked by the test, not by a run.

## Test

`gars/tests/test_gate_words.py::Stage01ExitTableTests::test_stage01_check_exit0_row_names_the_step_order_and_the_writer` parses the Definitions table under "The script's exit codes", requires exactly one exit-0 row naming `--check`, that it names neither T2 nor T4, names steps 6, 7 and 8 in order, and says the writer completes the stage.
It was red at the build base and is green here; restoring the old row turns it red.
`tests/check_contracts.py` stays clean.

## Status

Standing. The change record for stage 01's exit-code table; prose only, so no approval record is needed.

## Date

2026-10-17
