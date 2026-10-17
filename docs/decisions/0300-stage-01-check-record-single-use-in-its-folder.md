---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/stage01_samplesheet.py
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/tests/test_stage01_gates.py
  - gars/tests/test_r164_failure_recovery.py
  - docs/decisions/0299-stage-01-gates-fixed-words-bound-to-the-check.md
symptoms:
  - --force after an identical forced rewrite overwrites from a design the user never saw in T5
  - the stage 01 check record is writable through the agent's Write tool
  - "--check help says write nothing, yet a clean check writes .stage01_check.json"
  - a hand-made check record raises AttributeError (exit 1, read as T3) instead of exit 2
  - blocked "the last write consumed it; run --check"
---
# Stage 01's check record is single-use and lives in the stage's own folder

The fold of the review of lane gars-t74's run 1 (S01-yes, record 0299), under glitch-b5's rulings of Sat 17 Oct 2026, 11:58 EDT, made under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing.

## Context

The review found three faults in record 0299's mechanism and one rough edge:

- **Replay (finding 1).** The record was kept after a write and never consumed. A forced rewrite that reproduced the checked bytes left it matching, so after a condition swap in `samples.csv` a second `--force` with no new check still wrote; the same held for `--confirm-exclusions --force` with an unchanged excluded set. Record 0299 point 3 claimed the opposite.
- **Placement (finding 2, the lane's question 2).** At the project root the record was outside the stage's owned folder and writable by the agent's own Write tool; inside `01_samplesheets/` the guard already refuses it ("is emitted by `_system/stage01_samplesheet.py`"), with no change to the frozen guard.
- **Prose (finding 3).** The `--check` help said "write nothing" and the contract's exit-code row said "nothing is written", while a clean check writes the record; the contract's OUTPUT did not name it.
- **Shape (NIT 2).** A hand-made record of the right top level but a wrong inner type raised `AttributeError`: exit 1, which the contract reads as a validation failure (T3), instead of a refusal.

**Reproduction.** At 909b822b, `gars/tests/test_stage01_gates.py` fails four tests and errors in a fifth (`FAILED (failures=4, errors=2)`, the errors two subtests): the two replay cases exit 0 where 2 is expected, the guard does not refuse a Write to the record's path, the three-artifact listing lacks the record, and the wrong-shape record raises `AttributeError: 'str' object has no attribute 'get'`.

## Decision

1. The record is `01_samplesheets/.stage01_check.json`, a dotfile beside the artifacts (glitch-b5's ruling 2). The guard's existing `projects/*/01_samplesheets/*` rule refuses the agent's Write to it; the three-artifact names that `existing` lists, stage 02 resolves and the exit gate re-reads are unchanged. A clean `--check` with a gate to record creates the folder when it is absent; one with nothing to gate (no exclusions, no existing artifacts) keeps no record and removes a stale one, since an empty record refuses every switch exactly as no record does. So a check of a fresh project still creates no `01_samplesheets/`, and `tests/test_stage01_design.py` (which asserts that after a refusal) stays green unchanged.
2. The record carries `written_by`. A clean `--check` writes `check`; after every write, the writer replaces it with its own: the written files' sha256 and `written_by: writer` (glitch-b5's ruling 1). Only a `check` record clears a gate, so after any write a `--force` or `--confirm-exclusions` that clears a present gate needs a new `--check`; the refusal says "the last write consumed it". Record 0299 point 3 is corrected to say this.
3. A record that is not exactly the shape the script writes (the marker, a map of assay to a list of sample ids, a map of file name to a hex string) counts as no record: exit 2, "no --check is recorded".
4. Prose: the `--check` help says it writes only the check record; the exit-code table's check row says "it writes only its check record"; step 10 names the consumed check as a return to step 3; the OUTPUT table names the record and what reads it (nothing downstream).
5. Tests whose listing of `01_samplesheets/` now includes the record list it as the stage's own, under ruling 2: `test_check_then_write_leaves_only_the_three_artifacts` (named by the ruling) and `test_stage01_interrupted_keeps_each_previous_file` in `gars/tests/test_r164_failure_recovery.py` (the same listing, the same reason). The frozen `gars/tests/test_r164_writer_recovery.py` is unchanged and its 56 tests stay green.

## What this does not close

- **R1** and **R3** of record 0299 stand: the record proves the script showed something, not that the user saw it, and no live session has walked the gates.
- **R2** narrows: the plain Write path is closed by the guard, but an agent's shell command that writes the file is still the deliberate forgery 0299 R2 names.
- A reproduction package (`claims/package_run.py`) copies `01_samplesheets/` whole, so it now carries the record; it holds only sample ids and hashes already implied by the artifacts.

## Test

`gars/tests/test_stage01_gates.py` (twelve tests): the two replay cases, the guard refusing a Write to the record's path, the wrong-shape records each refused with exit 2, and the three-artifact listing with the record beside it and the artifacts' bytes equal to the unchanged writer's (review NIT 3); the eight earlier tests unchanged.
Mutation: a writer that skips replacing the record turns the two replay tests red.

## Status

Standing. Amends record 0299 (point 3 corrected in place; points 1 and 5 name the project root, which this record replaces).

## Date

2026-10-17
