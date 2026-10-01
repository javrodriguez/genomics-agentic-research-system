---
date: 2026-09-30
status: standing
kind: decision
touches:
  - gars/_references/genomes.md
symptoms:
  - the R64-1-1 genome row (0246) changes gars/_references/genomes.md, a protected path, and needs the owner's approval record
---
# R64-1-1 genome row 0246: the owner's approval of its protected registry change

Addendum to [0246](0246-r64-genome-row-for-the-launch-pad.md).
`gars/_references/genomes.md` is a protected path (R-094, spec §9.3), as [0099](0099-row-6-delegated-approval-of-protected-changes.md) records, so the change needs an owner-approval record.
This approval is **the owner's own**, not delegated: the launch-pad plan puts the R64 diff in front of Javier for his typed yes.
The lane wrote everything below except the owner's slot, which it leaves empty; only the quoted words in that slot, once filled, are the owner's.
Its shape follows [0066](0066-row-12-owner-approval-of-protected-changes.md).

## Context

0246 was built on its own branch from public main `37a8d94` by a Claude Code producer (Opus 5.5) in an isolated clone with no remote, with its rulings made by glitch-14 under the owner's 23 September 2026 delegation.
A fresh-context Claude Code reviewer (Opus 5.5) reviews the candidate before it is shown to the owner; its verdict is recorded at landing.

## Decision

On the owner's yes below, the owner approves this protected change as it stands at the candidate named in the slot.

1. **`gars/_references/genomes.md`**: one identity row for R64-1-1 after the GRCh38 row (`MT`, `11624332`, the launch pad's paths under `install/refs/R64-1-1/`); one hash row for R64-1-1 in the ID-keyed table (`c0b7305c230b550c3d8ccc692df52338afc7a297b43d965868c285b98aa64ae1`, `3a1e64b8f290127562612b47d6014bc6e4c130399da3e06ad062b268fd6d08fb`); "Paths are site-specific" rewritten to name the HPC cluster and the launch pad; one paragraph stating requirement 2 (`gene_biotype`) for R64-1-1. The GRCh38 rows and every other line are unchanged.

Outside the protected prefixes, recorded for completeness: `tests/test_genome_registry_r64.py`, the suite totals in `README.md` and `DEVELOPMENT.md`, 0246, this record and the index.

### The owner's word (slot: filled only with Javier's own typed message)

- Owner's message, verbatim: "recompute wording ok · approve R64 genome row 522852c · push GARS to public main now"
- Typed at (date and time, America/New_York, from the window it was typed in): 2026-09-30, 20:13 EDT (clock read when it arrived), in the Row-orchestrator window (glitch-14)
- Candidate sha the message names: `522852c74d9177c8f3e39ebe22c1b3d88f4b17fd`

Until all three lines are filled from the owner's own message, this record approves nothing, and the change does not land.

## Test

`python3 tests/test_genome_registry_r64.py` runs 3 tests OK at the candidate; with the base registry it fails 5 ways, and a planted `Mito` fails it (0246, "Test").
A change to the R64-1-1 row's mito name, gsize, paths or hashes, or a hash-table row read as a genome, turns it red.

## Status

Standing as a record; the approval it carries takes effect only when the owner's slot is filled.

## Date

2026-09-30

## Landing note (30 Sep 2026)

Reviews at the candidate: r1 and r2, fresh Claude Code reviewers (Opus 5.5), 0 MAJOR each. Full suite on 522852c: 1211 tests, no failures or errors (76 environment skips, named in the lane record). It lands together with 0241/0242 (the GSE58638 recompute) on top of it, in one push on the same message.
