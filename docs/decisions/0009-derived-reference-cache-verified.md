---
date: 2026-08-13
status: standing
kind: decision
symptoms:
  - "index version incompatibility surfaces only at STAR_ALIGN"
touches:
  - gars/_references/config_schema.md
---
# Derived-reference cache verified reusable

Populating a cache proves nothing; the STAR version incompatibility that killed run 26310826
surfaces only when STAR loads the index at `STAR_ALIGN`, so a preflight cannot detect it. A
throwaway 2-sample project (`cache-check`) was created purely to force a real alignment.

Result: **`Pipeline completed successfully`, 0 index-building processes launched.**

| Check | Result |
|---|---|
| `STAR_GENOMEGENERATE`, `SALMON_INDEX`, `MAKE_TRANSCRIPTS_FASTA` | 0 launched — all skipped |
| `versionGenome` verified before reuse (contract requirement) | 2.7.4a, logged by `submit.sh` |
| STAR loaded the cached genome index | aligned 2/2 |
| Salmon quantified against the cached transcriptome index | completed |
| Cache after reuse | 59 GB, unchanged |

Both indices had to be validated independently: an aligner index and a quantifier index are
compatible with the tool versions that built them, separately. Every later run against Ensembl
GRCh38 r116 with nf-core/rnaseq 3.26.0 now skips ~43 GB and roughly 40 minutes.

Also confirmed in the same run: setting `strandedness: unstranded` explicitly, on the RSeQC
evidence, removed the "10/10 samples failed strandedness check" warning entirely.

**Method note worth keeping.** A deliberately minimal project — 2 samples, no biological intent
— is the right way to verify infrastructure. It cost ~2 hours and 89 GB of scratch instead of
re-running a real analysis, and it isolated the thing under test.
