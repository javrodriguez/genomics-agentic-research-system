# Reproduction campaign: the methylation-loss epigenome

Five public-data projects, one per assay, that validate every wrapper live **and** reproduce
published results quantitatively — the same numerical-validation discipline that caught the
upstream fold-change defect (0029), pointed at the literature.

Four of five share one biological story: **HCT116 vs DKO1** (DNMT1/DNMT3B double knockout —
the cell line that lost ~95% of its DNA methylation), across three mutually-citing papers:
methylation loss → gene de-repression (RNA-seq) → chromatin opening (ATAC) → H3K27me3
redistribution (ChIP) → the methylome itself (WGBS). The fifth (CUT&RUN slot) uses the
Kaya-Okur 2020 CUT&Tag protocol dataset — nf-core/cutandrun's own full-size test, so the
least-proven pipeline runs the most-proven data.

Each project ends with a **stage 03 comparison plan** (drafted, human-approved, gated) whose
output is one score against the authors' deposited results.

## The five projects

Run order = ascending risk and size: fast feedback first, the 41 GB WGBS last.

| # | Project | Assay | Data | Design | Size | Reproduce against | Score |
|---|---|---|---|---|---|---|---|
| 1 | `dko-atac` | atacseq_bulk | GSE126215 (SRR8544480–83), SE | HCT116 ×2 vs DKO1 ×2 | ~3.4 GB | deposited bigWigs; the paper's 23,310 hyper- / 3,166 hypo-accessible sites in DKO | signal correlation at consensus peaks; direction asymmetry |
| 2 | `cuttag-k562` | cutandrun | GSE145187 subset (the nf-core full-test samplesheet), PE | H3K4me3 ×2 vs H3K27me3 ×2 + IgG ×2 | ~5–8 GB | deposited per-sample ALIGNED-FRAGMENT BEDs (GSE145187_RAW carries no author peak calls — corrected during project 2's stage-03 drafting; peaks are re-derived from the deposited fragments with the identical caller+mode, making the Jaccard like-for-like by construction) | peak Jaccard (methodologically matched, cross-mark separation control); symmetric FRiP; K4me3-at-TSS |
| 3 | `dko-chip-k27` + `dko-chip-k4` (split ruled by the maintainer at the peaks gate 2026-08-28: one project per mark so each is called in its proper mode — K27me3 BROAD, K4me3 NARROW; mirror-image samples.csv subsets of one registered set, inputs shared) | chipseq_bulk | GSE58638 subset (SRP043384), SE | H3K4me3 + H3K27me3 × {HCT116, DKO1} ×2 reps + inputs (~11 runs; HCT116 input reused across its IP reps via the control column) | ~16 GB | per-sample bigWigs; Blattler 2014 Additional file 10 region classes | binned signal correlation; peak Jaccard vs region classes; K27me3 spreading in DKO1 |
| 4 | `dko-rnaseq` | rnaseq_bulk | GSE52429 + GSE60106 RNA (SRR1030462–63, SRR1536577–78), PE | HCT116 ×2 vs DKO1 ×2 | ~21 GB | Blattler 2014 Additional file 8 DE table (1,089 de-repressed) | log2FC rank correlation; DE-set overlap; de-repression direction concordance |
| 5 | `dko-wgbs` | methylseq | GSE60106 WGBS (SRR1536575–76), PE | HCT116 vs DKO1, n=1 each | ~41 GB | deposited per-CpG calls; DKO1 retains ~5% global methylation | coverage-filtered per-CpG correlation; global means |

Publications: Blattler et al. 2014 *Genome Biology* 15:469 (RNA, WGBS, enhancer tables);
Lay et al. 2015 *Genome Research* 25:467 (histone panel); Spektor et al. 2019 *Genome
Research* 29:969 (Omni-ATAC/mATAC); Kaya-Okur et al. 2020 *Nature Protocols* 15:3264
(CUT&Tag); WT RNA reps from Yao et al. 2014.

## Getting the data

Resolve exact FASTQ URLs at download time from ENA's filereport (no hardcoded mirrors):

```bash
ACC=SRP184492   # or a GSE's SRP/PRJNA; per-run SRR also works
curl -s "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=${ACC}&result=read_run&fields=run_accession,fastq_ftp,fastq_bytes,library_layout,sample_title" \
  | column -t -s$'\t'
# then wget/aria2c the fastq_ftp URLs onto scratch, and verify sizes against fastq_bytes
```

Downloads land on scratch (a download is pre-stage-00 operations, outside the contracts);
stage 00 registers from there as usual. For GSE58638, select runs by `sample_title`
(H3K4me3/H3K27me3/input × cell line) from the filereport listing before downloading.

## Standing cautions (decided up front, so the runs don't relitigate them)

- **Genome builds:** we run GRCh38; the HCT116-era deposits are hg19. Comparisons lift the
  *deposited* coordinates to GRCh38 (peaks/CpGs), or — where signal-level comparison demands
  it — the comparison run may use hg19 explicitly, recorded in the project config. Decide per
  stage-03 plan; never mix builds silently.
- **Scoring is rank/overlap-based, never exact-value**: the deposits are 2014-era tooling
  (TopHat/Cufflinks/Partek). Rank correlation and set overlap are the scientifically honest
  comparisons.
- **GSE126215 and GSE58638 are single-end** — supported; note it in each HISTORY entry.
- **WGBS is n=1 per condition** — acceptable because methylseq performs no differential
  statistics; the reproduction target is per-CpG agreement and the global-loss number.
- **Project 2 is CUT&Tag under the cutandrun pipeline** — supported and precedented (it is
  the pipeline's own full test); label it CUT&Tag everywhere.
- **Quota:** superseded 2026-08-28 — the campaign runs in a workspace checkout on scratch
  (no quotas; results staged off promptly, eviction is threshold-triggered cold-data).
- **Parser pairing (0034):** atacseq/chipseq/cutandrun/methylseq run under
  `NXF_SYNTAX_PARSER=v1`, exported by their generated `submit.sh` — their pinned releases
  predate Nextflow's strict parser and no newer releases exist. rnaseq stays strict.

## What done looks like

Five projects complete through their sub-stages, five approved stage-03 comparison plans
executed, five scores in five HISTORY.md files — and [RESULTS.md](RESULTS.md) summarising the
per-assay agreement, honestly including wherever we and the authors disagree and why. That
file is live and fills in as each project closes.
