# Reproduction campaign — results

Five public-data projects, each run end to end through GARS and scored against what the
original authors deposited. The design, accessions and standing cautions are in
[reproduction-campaign.md](reproduction-campaign.md); this file carries the outcomes,
including where we and the authors disagree and why.

**Status: 3 of 5 scored** (this document fills in as projects close).

| # | Project | Assay | Compared against | Headline |
|---|---|---|---|---|
| 1 | `dko-atac` | ATAC-seq | deposited bigWigs + the paper's differential-accessibility asymmetry | **Reproduces** — signal ρ 0.979–0.987, direction confirmed |
| 2 | `cuttag-k562` | CUT&Tag | deposited fragments, re-called with our own caller | **Mark identity reproduces** (600× separation); K4me3 fully, K27me3 with stated divergence |
| 3a | `dko-chip-k27` | ChIP-seq (broad) | deposited z-scored tracks | **Reproduces** — ρ ≈ 0.80 on healthy replicates; spreading direction confirmed |
| 3b | `dko-chip-k4` | ChIP-seq (narrow) | deposited bigWigs | scoring |
| 4 | `dko-rnaseq` | RNA-seq | the paper's deposited DE table | pipeline running |
| 5 | `dko-wgbs` | WGBS | deposited per-CpG calls | data staging |

---

## 1 · ATAC-seq — `dko-atac` (GSE126215)

Signal correlation at our consensus peaks against the authors' deposited bigWigs, and the
paper's headline direction test.

| Measure | Result |
|---|---|
| Matched-condition Spearman | **0.9859 / 0.9866** (HCT116), **0.9805 / 0.9789** (DKO1) |
| Cross-condition control | 0.526 — the biology separates where it should |
| liftOver retention | 99.3% (96,807 bins joined) |
| Direction asymmetry | **4,552 hyper / 523 hypo in DKO1, ratio 8.7, sign-test p ≈ 0** vs published 23,310 / 3,166 (ratio 7.36) |

**Verdict: reproduces.** Direction and bias match; absolute counts differ because the
differential method and peak set are ours, not theirs — stated rather than tuned away.

## 2 · CUT&Tag — `cuttag-k562` (GSE145187)

The deposit turned out to hold **aligned fragments, not peak calls** (a correction to the
campaign's original design). Rather than compare across methods, the deposited fragments were
re-called with the identical caller and mode, making the comparison like-for-like by
construction.

| Measure | H3K4me3 | H3K27me3 |
|---|---|---|
| Jaccard vs deposit-derived peaks | 0.341 / 0.630 | 0.169 / 0.047 |
| FRiP, ours vs deposited | 0.95 / 0.77 vs 0.61 / 0.61 | 0.85 / 0.68 vs 0.32 / **0.07** |
| TSS ±2 kb enrichment | high both sides | low both sides — the sharp/broad contrast holds |
| Separation control | **matched 0.297 vs cross-mark 0.0005 — 600×** | |

**Verdict: mark identity reproduces unambiguously.** K4me3 agrees on all three measures.
K27me3 agrees in direction but diverges in magnitude, and the largest single reason is on the
deposit's side: their K27me3 replicate 2 scores **FRiP 0.07 against its own peaks** — mostly
background by its own numbers. Broad-domain calling is also inherently less stable than
point-source, and our tracks are spike-in calibrated while the deposited fragments are not.

## 3a · ChIP-seq, H3K27me3 — `dko-chip-k27` (GSE58638)

Scored per replicate, paired by GSM accession rather than by label (see below).

| Measure | Result |
|---|---|
| Binned Spearman (10-kb, 274,679 bins) | **0.805 / 0.794 / 0.845** on the three healthy replicates |
| — the failed replicate | 0.464 |
| Spreading (the paper's claim) | DKO1 > HCT116 in **both** ours (123 M vs 45.6 M mean peak bp) and theirs (z>1 fraction 0.067 vs 0.045) — **direction reproduces** |
| Region-class concordance | 3 of 6 cells same-direction — **honestly weak**, reported as such |

### The finding: a failed immunoprecipitation in the published data

One library — `GSM1420155`, HCT116 H3K27me3 — fails our QC and the evidence converges from
three independent directions:

- **Our pipeline QC:** it is the *second-deepest* library in the panel (28.8 M filtered reads)
  yet yields 7× fewer peaks per read than its siblings (1,007 vs a remarkably uniform
  7,487–7,742 per million) at **FRiP 0.032**, with only 2.6% duplication — ruling out a
  PCR-collapsed library. Signature: plenty of reads, no enrichment.
- **The authors' own deposited track:** its z-score distribution is an extreme outlier among
  the four deposits — 0.0073 of bins above z>1 against 0.053–0.083 for the others, and
  **40–100× below them at z>2**.
- **Their published QC could not have seen it:** Supplemental Table 1 reports depth only — no
  FRiP, no peak counts, no enrichment metric. By depth alone, this library looks like the
  *best* of the four.

The replicate was kept, not silently dropped: every score is reported per replicate with the
failure flagged. A weak replicate that is labelled is data; one that is quietly excluded is a
result.

### A labelling trap, for anyone reproducing this dataset

The paper's supplementary table and GEO's own sample titles **disagree about which HCT116
H3K27me3 library is replicate 1 and which is replicate 2**. Replicates were therefore paired
by GSM accession, confirmed two independent ways (ENA run→sample resolution, and sequencing
depth matching). Anyone comparing against this series by replicate label risks silently
pairing the wrong samples.

---

## How the scoring was designed

Every comparison here was drafted as a reviewable plan, approved by a human, and executed only
after approval — the same stage-03 gate the system applies to any custom analysis. Three
recurring disciplines came out of running them:

1. **Read what was actually deposited before designing the comparison.** Two of the five
   projects' deposits were not what the campaign plan assumed (fragments rather than peaks;
   z-scored tracks that cannot express a global change). Both were found by checking, and both
   changed the design rather than being worked around.
2. **Pair by accession, never by label.** See the labelling trap above.
3. **Never normalise away the effect under test.** Where a scoring choice would have flattened
   a genuine per-condition difference, the plan says so explicitly and justifies what it does
   instead.
