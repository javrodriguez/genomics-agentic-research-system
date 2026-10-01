---
date: 2026-09-30
status: standing
kind: decision
touches:
  - gars/_references/genomes.md
symptoms:
  - the genome registry every clone reads names a former HPC account and its lab group folder in the GRCh38 row's three paths
  - the GRCh38 row's placeholder paths change gars/_references/genomes.md, a protected path, and need the owner's approval record
---
# The GRCh38 registry row's paths become a placeholder, with the owner's approval slot

Every ruling in this record is **glitch-14's**, the Row-orchestrator's (the orchestrating Claude session), made under the owner's standing delegation of 23 September 2026; no sentence here is the owner's.
`gars/_references/genomes.md` is a protected path (R-094, spec §9.3), as [0099](0099-row-6-delegated-approval-of-protected-changes.md) records, so the change also needs an owner-approval record.
This record carries that approval's slot, **the owner's own**, not delegated, and leaves it empty; only the quoted words in that slot, once filled, are the owner's.
Its shape follows [0247](0247-r64-genome-row-0246-owner-approval-of-protected-change.md).

## Context

The launch-readiness audit of 30 September 2026 (item 10) found that the GRCh38 row of the genome registry, the file every clone's stage 02 reads through `configure.py genomes`, spelled its three paths (FASTA, GTF, derived cache root) under one person's directory in a lab group's work area on the HPC cluster GARS was built on.
That names a personal account and an institution's group folder, in a file a user is told to edit for their own site.
The paths were never usable anywhere else: off that cluster `configure.py` already reports them unreadable and refuses the genome, and "Paths are site-specific" already told a different site to edit the file.

## Decision

On the owner's yes below, the owner approves this protected change as it stands at the candidate named in the slot.

1. **`gars/_references/genomes.md`**: in the GRCh38 identity row, the prefix of the three paths before `install/refs/` becomes `/path/to/group-work-area`; the rest of each path (`install/refs/ensembl-GRCh38-116/…`) is unchanged. "Paths are site-specific" now says the GRCh38 row's paths begin with that placeholder and that a site using the row replaces it. The R64-1-1 row, both hash rows and every other line are unchanged.

The placeholder is a plain absolute-looking path rather than `<…>`, because the registry's cells are read raw by `configure.py` and GitHub drops an unknown `<tag>` from a rendered table.

Outside the protected prefixes, recorded for completeness: this record and the decision index.

### The owner's word (slot: filled only with Javier's own typed message)

- Owner's message, verbatim:
- Typed at (date and time, America/New_York, from the window it was typed in):
- Candidate sha the message names:

Until all three lines are filled from the owner's own message, this record approves nothing, and the change does not land.

## What this does not close

The same lab group folder, with a `<user>` placeholder, is still named in `CLAUDE.md`, `docs/execution-model.md` and `gars/_system/gars-env.sh` (the last a protected path); the frozen study records under `evals/` keep both account names as recorded, and the public history keeps the old row.
Neither is changed here.

## Test

`python3 tests/test_genome_registry_r64.py` runs 3 tests OK (GRCh38 still menu entry 01, its hash row still read), and the `run_tests.py` classes that read or rewrite the registry (`WorkspaceFixture`, `AtacseqWrapperTests`, `ChipFamilyAndMethylTests`, `ScrnaseqWrapperTests`, `ScrnaQcClusterTests`) run 49 tests OK (6 environment skips).
A fixed-string search of the tree for the former account name finds no hit in `gars/_references/genomes.md` after the change, where it found one before; a path that still carries the account turns that search red.

## Status

Standing as a record; the approval it carries takes effect only when the owner's slot is filled.

## Date

2026-09-30
