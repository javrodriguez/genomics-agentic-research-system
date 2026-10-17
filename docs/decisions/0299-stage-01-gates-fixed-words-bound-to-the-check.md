---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/stage01_samplesheet.py
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/tests/test_stage01_gates.py
  - gars/tests/test_gate_words.py
  - gars/tests/test_r164_failure_recovery.py
  - tests/run_tests.py
symptoms:
  - stage01_samplesheet.py --force overwrites samplesheets with no check shown to the user
  - --confirm-exclusions writes a reduced set after samples.csv changed since the user saw T7
  - the agent reads "ok, but keep sample 4" as a confirmation of the exclusions
  - blocked "does not match the --check the user was shown" or "no --check is recorded"
---
# Stage 01's two gates: a fixed word each, bound to the check the user saw

Item S01-yes of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner in the step map's answers ("A fixed word for each gate ("exclude", "overwrite"), and the script refuses a switch that has no matching recorded answer").
The mechanism and wording are the lane's (gars-t74), made under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing.

## Context

Stage 01 has two human gates: T7 (samples with raw data but no design row will be excluded) and T5 (the samplesheets already exist and will be overwritten).
The writer honoured `--confirm-exclusions` and `--force` whenever they were passed: with no check run at all, or after `samples.csv` or the files had changed since the user was shown T7 or T5.
The templates closed on "Confirm to ...", so any reply could be read as the confirmation.
GARS has no user-prompt hook, so no script can see what the user typed (plan fact 3); what code can hold is that a switch matches a record the script itself wrote when it produced what the user was shown.

**Reproduction.** At the build base (the frozen Landings A and C head `2d819179`), `gars/tests/test_stage01_gates.py` fails four tests: `--force` with no prior check, `--force` after a samplesheet changed since the check, and `--confirm-exclusions` with no prior check or after one more sample was dropped, all exit 0 where 2 is expected.

## Decision

1. A clean `--check` writes one record, `.stage01_check.json` at the project root: each assay's excluded sample ids and each existing samplesheet artifact's sha256. It is outside `01_samplesheets/`, so that folder still holds only the three artifacts per assay, and it is replaced by every clean check.
2. The writer judges a switch only when it clears a gate that is present (`--confirm-exclusions` with exclusions, `--force` with existing files). Such a switch needs the record, and the record's subject must equal today's: the same excluded samples, the same files byte for byte. Otherwise exit 2 with a `blocked` entry naming the switch, what changed (or that no check is recorded), and that the check must be run and its template shown again. A switch that clears no gate needs no record, so a project with nothing to exclude or overwrite writes as before.
3. The writer's artifacts are unchanged in bytes; the record is kept after a write, so a later `--force` needs a new check (the record's file set no longer matches).
4. Contract: T7 closes on the reply `exclude`, T5 on `overwrite`; steps 6 and 7 clear their gate only on that word alone and send the template again on any other reply; step 10 sends a refused switch back to step 3, and the exit-code table's exit-2 row names that branch. The Scope Boundaries line on the two switches names the words. Overlap with Landings A and C: the stage 01 contract (Landing A, record 0291); its non-public paragraphs are untouched, and step 6 says "the design" rather than naming `samples.csv`, so `test_closed_project_contracts.py` finds no new refused-read step.
5. Callers that passed a switch with no check, the exact path this item outlaws, now run `--check` first, with every earlier assertion kept and one added for the check's exit 0: five tests in `tests/run_tests.py` (`WorkspaceFixture` 06-08, `AtacseqWrapperTests` 00b, `ChipFamilyAndMethylTests` 00) and the `stage01` helper of `gars/tests/test_r164_failure_recovery.py`, which `gars/tests/test_r164_writer_recovery.py` (frozen by Landing C) calls; that frozen file is unchanged and its 56 tests stay green, since the injected faults strike writes to the artifacts only and the record is written at the project root.

## What this does not close

- **R1** The record proves the script showed something, not that the user saw it or answered with the word: an agent that runs `--check` and then passes the switch without asking still writes. The word is held by the contract (as in record 0297); the code holds only that the switch matches the latest check.
- **R2** The record is an ordinary file the agent could write itself with the right hashes; the guard does not protect it. Forging it needs the exact sample ids and sha256 values, which is deliberate deviation rather than a misread reply.
- **R3** No live session has walked the new gates; they are checked by the tests, not by a run.

## Test

`gars/tests/test_stage01_gates.py` (eight tests): the four refusals above, each with exit 2, `ok` false, nothing written and a `blocked` entry naming the cause, and a refused overwrite leaving every file as it was; and four controls green before and after: either switch after a matching check writes, a switch that clears no gate writes, and check-then-write leaves only the three artifacts in `01_samplesheets/`.
Mutation: `unmatched_switches` returning no reasons turns the four refusals red.
`gars/tests/test_gate_words.py::Stage01GateWordTests` requires T7 to close on `exclude` and `cancel`, T5 on `overwrite` and `cancel`, steps 6 and 7 to re-send their template on any other reply, and step 10 to return to step 3 on a refused switch; red before the contract change. `tests/check_contracts.py`, `gars/tests/test_closed_project_contracts.py` and the other contract readers stay green.

## Status

Standing. The change record for stage 01's two gates; the `_system/` change waits on glitch-b5's approval record at landing.

## Date

2026-10-17
