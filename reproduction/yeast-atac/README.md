# nfcore-atacseq-wrapper, re-run from its reproduction package

[![re-run counts](https://img.shields.io/badge/re--run-2%20exact%2C%201%20tolerance%2C%201%20presence%2C%202%20differ-informational)](https://github.com/javrodriguez/genomics-agentic-research-system/actions/workflows/reproduction-yeast-atac.yml)

What was analysed: nf-core/atacseq 2.1.2 (pipeline commit `1a1dbe52ffbd82256c941a032b0e22abbd925b8a`).

Re-run: `bash package/rerun.sh --out <empty folder>`

Verify: `python3 package/verify.py --against <that folder>`

Re-run on a fresh 4-CPU 16 GB launch-pad machine (AWS m5.xlarge), no image cached, 2026-10-06 and 2026-10-07, from this package and the public sources it pins by checksum (package sha256 `f5964ecee48730b533458db313667b597a7c0e09df27020e8ba6da07cae85811`): of 6 outputs (209 files), 2 matched exactly, 1 within the stated tolerance, 1 present but not byte-comparable, 2 differ (causes in PROVENANCE.md).

The re-run was a pre-landing pass in a private environment (not viewable); the public workflow's runs ([reproduction-yeast-atac.yml](https://github.com/javrodriguez/genomics-agentic-research-system/actions/workflows/reproduction-yeast-atac.yml)) must show the same table.

| Stage | Output | Path | Members | Exact | Presence | Other | Failed | Extra | Result |
|---|---|---|---|---|---|---|---|---|---|
| atacseq_bulk.01_nfcore-atacseq-wrapper | peaks | `run/results/bwa/merged_library/macs2/narrow_peak` | 50 | 39 | 6 | 5 | 8 | 0 | F |
| atacseq_bulk.01_nfcore-atacseq-wrapper | peaks_consensus | `run/results/bwa/merged_library/macs2/narrow_peak/consensus/consensus_peaks.mLb.clN.bed` | 1 | 1 | 0 | 0 | 0 | 0 | M |
| atacseq_bulk.01_nfcore-atacseq-wrapper | counts_peaks | `run/results/bwa/merged_library/macs2/narrow_peak/consensus/consensus_peaks.mLb.clN.featureCounts.txt` | 1 | 0 | 0 | 1 | 0 | 0 | K |
| atacseq_bulk.01_nfcore-atacseq-wrapper | bigwig | `run/results/bwa/merged_library/bigwig` | 8 | 8 | 0 | 0 | 0 | 0 | M |
| atacseq_bulk.01_nfcore-atacseq-wrapper | bam_genome | `run/results/bwa/merged_library` | 208 | 113 | 54 | 41 | 8 | 0 | F |
| atacseq_bulk.01_nfcore-atacseq-wrapper | qc_multiqc | `run/results/multiqc/narrow_peak/multiqc_report.html` | 1 | 0 | 1 | 0 | 0 | 0 | P |

Every caveat, label and "not recorded" is in [package/PROVENANCE.md](package/PROVENANCE.md).
