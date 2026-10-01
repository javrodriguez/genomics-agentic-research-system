---
date: 2026-10-01
status: standing
kind: decision
touches:
  - gars/_references/genomes.md
  - tests/test_genome_registry_gsize_source.py
symptoms:
  - gars/_references/genomes.md says the GRCh38 MACS gsize 2,701,495,761 is the same value nf-core/atacseq's own iGenomes config uses for GRCh38 at the default read length; nf-core/atacseq 2.1.2 gives 2,701,262,066 there and has no default read length
---
# GRCh38 MACS gsize: the registry's source sentence corrected, the value kept

`gars/_references/genomes.md` is a protected path (R-094, spec §9.3, as [0099](0099-row-6-delegated-approval-of-protected-changes.md) and [0247](0247-r64-genome-row-0246-owner-approval-of-protected-change.md) record), so this sentence correction carries an owner-approval slot.
The slot is **the owner's own** and is left empty by the lane; only the quoted words in it, once filled, are the owner's.
Its shape follows [0247](0247-r64-genome-row-0246-owner-approval-of-protected-change.md).

## Context

The registry's **MACS gsize** paragraph said the GRCh38 value is "the deeptools 50-bp unique-mappability figure (2,701,495,761), the same value nf-core/atacseq's own iGenomes config uses for GRCh38 at the default read length".
The first half is true and the second is not.
A research check for the coordinator of the R64-1-1 row (30 Sep 2026, the R64 lane's gsize check, kept outside the repository) found it, and this lane re-read each source on 30 Sep 2026:

- deepTools' own documentation, `docs/content/feature/effectiveGenomeSize.rst`, prints `2701495761` for GRCh38 at read length 50 at every release tag from 3.4.0 to 3.5.4 (3.4.0, 3.4.1, 3.4.2, 3.4.3, 3.5.0, 3.5.1, 3.5.2, 3.5.3, 3.5.4; for example https://raw.githubusercontent.com/deeptools/deepTools/3.4.3/docs/content/feature/effectiveGenomeSize.rst, line 30 at each of these tags), and `2701495711` at 3.5.5 (line 50) and 3.5.6 (line 52), the two later tags; releases before 3.4.0 were not read.
- nf-core/atacseq 2.1.2, `conf/igenomes.config` (https://raw.githubusercontent.com/nf-core/atacseq/2.1.2/conf/igenomes.config, lines 43-44), lists GRCh38 `macs_gsize` `"50"  : 2701262066` under its NCBI GRCh38 entry; nf-core/atacseq 2.1.2 sets `read_length = null`, so it has no default read length.

So 2,701,495,761 is the deepTools documentation figure of releases 3.4.0 to 3.5.4, not nf-core's figure; nf-core's differs by 233,695 (about 0.009 %).
The value GARS passes stays: the GARS wrappers pass the registry's gsize to MACS2 explicitly, the registry states deepTools' 50-bp convention, and the evidence shows the number is that convention's published figure, not a wrong one.

## Decision

1. **`gars/_references/genomes.md`**: the one sentence of the **MACS gsize** paragraph that names the GRCh38 value's source now says it is deepTools' 50-bp effective genome size as printed in the deepTools documentation of every release from 3.4.0 to 3.5.4, that 3.5.5 and 3.5.6 print 2,701,495,711, and that nf-core/atacseq 2.1.2 lists 2,701,262,066 for its NCBI GRCh38 at read length 50, so the registry's value is not nf-core's.
   The GRCh38 table cell (`2701495761`), the R64-1-1 row and every other line are unchanged.
2. **`tests/test_genome_registry_gsize_source.py`** (new, two tests) pins the corrected claim: the registry's GRCh38 gsize equals the figure the sentence states and the deepTools 3.4.0 to 3.5.4 figure, and the sentence names deepTools as its source and never pairs the value with nf-core.

Outside the protected prefixes, recorded for completeness: the new test module, the suite totals in `README.md` and `DEVELOPMENT.md`, this record and the index.

### The owner's word (slot: filled only with Javier's own typed message)

- Owner's message, verbatim: "approve 0252 0256 0261 and the record masks at 947cc70 · push GARS to public main now"
- Typed at (date and time, America/New_York, from the window it was typed in): 2026-10-01, 07:03 EDT (clock read when it arrived), typed in the Row-orchestrator window (glitch-14)
- Candidate sha the message names: `947cc700f68e0a129819fb009700f7d85cc65cfd`

Until all three lines are filled from the owner's own message, this record approves nothing, and the change does not land.

## What this does not close

- Whether 50 bp is the right read length for any given GRCh38 run: the registry keeps one value per assembly, and a run at another read length still gets the 50-bp figure.
- The 50-bp deepTools figure moved between documentation releases (2,701,495,761 through 3.5.4, 2,701,495,711 from 3.5.5); the registry keeps the older printed figure, a difference of 50 bases.
- No GRCh38 effective size was recomputed here (no `unique-kmers.py` run); the sentence rests on the published sources above.

## Test

`python3 tests/test_genome_registry_gsize_source.py` runs 2 tests.
At the uncorrected registry it fails both (the sentence pairs the value with nf-core and names no deepTools release); with the correction both pass. A fresh-context review (Opus 5.5) also saw it fail with the table cell set to the nf-core figure or the 3.5.5 and 3.5.6 figure, with the sentence's figure changed, and with both switched to the nf-core figure; its MINOR, a release range wider than the tags read, was answered by reading every tag in the range named.
A registry GRCh38 gsize that is not 2701495761, a sentence that states another figure, or a sentence that again calls the value nf-core's turns it red.

## Status

Standing as a record; the approval it carries takes effect only when the owner's slot is filled.

## Date

2026-10-01
