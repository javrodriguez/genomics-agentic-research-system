---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/stage00_register.py
  - gars/00_initialize_project/CONTEXT.md
  - gars/tests/test_stage00_patterns.py
symptoms:
  - "--sample-id-pattern ... disagrees with ..., which its link recorded" from stage 00 finalize
  - "cannot derive sample IDs: ... do not match ...; link with the pattern this assay's inspect used" from stage 00 link
  - "undeclared option" from the guard for link --sample-id-pattern (registry hunk not applied)
  - "classifying data is the owner's" for a declared-public finalize after link (guard hunk not applied)
  - one assay's sample names derived with another assay's pattern
---
# Each assay keeps the sample-name pattern its own inspection used

Item S00-onepattern of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner. Wording is the lane's (gars-t74), under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing, and so are the two frozen-file hunks the lane may not apply: `lanes/gars-t74/S00-onepattern-registry.patch` and `lanes/gars-t74/S00-onepattern-guard.patch`.

## Context

`inspect` takes `--sample-id-pattern` per assay, but `finalize` took one pattern for the whole project and applied it to every assay. In a two-assay project where only one assay's files need a pattern, the contract's "add the same `--sample-id-pattern` if one was used" put that pattern on the other assay too: its names failed to derive, or, with a pattern loose enough, derived wrong.

**Reproduction.** At 2366b182, `gars/tests/test_stage00_patterns.py` fails six of eight (`FAILED (failures=5, errors=1)`): `link` has no `--sample-id-pattern` (argparse exit 2 in the two-assay rows and the record and refusal rows), the guard refuses the flag as undeclared, and the contract still passes the pattern to finalize. The two controls (an assay linked before the record keeps the finalize flag; a one-assay convention project's `files.csv` and `samples.csv`) are green.

## Decision

1. `link` takes the `--sample-id-pattern` its assay's `inspect` used and re-reads the folder with it before any link exists: unmatched names or mixed pairing exit 2 (T5, `unmatched_examples`), an invalid regex exit 3.
2. On success `link` writes `00_data/<Assay ID>/sample_id_pattern.txt`, machine-owned (0444): the pattern and a newline, or empty for the bcl2fastq convention.
3. `finalize` derives each assay's names with that assay's record alone. A `--sample-id-pattern` that disagrees with any assay's record is refused (exit 2) before anything is written, naming the assay and both patterns. An assay with no record, linked before this change, takes the flag as it always did.
4. The stage 00 contract: step 12 passes the pattern to `link` for that assay only; step 15 never passes it to finalize; Definitions say each assay keeps its own.
5. Registry hunk: `stage00_register.link` gains `sample-id-pattern` (a string, as on `inspect`). Finalize's entry is unchanged: the per-assay record makes a per-assay finalize flag unnecessary, so the plan's `ASSAY=REGEX` form is not built.
6. Guard hunk: the record is a protected path beside `files.csv`, and `registrable` counts it beside `raw/`. Without it, a project linked with the record is no longer "create's stamp plus raw entries", so a declared-public registration's finalize is refused (fail-closed) and `test_nonpublic_read_block` fails six rows until the hunk is applied.

## What this does not close

- **A project linked partly before this change** mixes records and a flag: assays with a record ignore the flag, a flag disagreeing with any record is refused, and an older assay that needed a pattern then needs a re-link (`--force` is the human's).
- **The record is trusted.** It is machine-owned and, with the guard hunk, a protected path; without the hunk the agent could rewrite it.

## Test

`gars/tests/test_stage00_patterns.py` (8 tests): two assays with their own patterns; the record and its mode; a disagreeing finalize flag refused with nothing written; a pattern that does not read the folder refused before any link; the legacy control; the one-assay control; the guard admits the flag (green only with the registry hunk); the contract.
Mutation: finalize ignores the record `FAILED (failures=1, errors=1)` (the errors row is the guard's, waiting on the hunk).

## Status

Standing.

## Date

2026-10-17
