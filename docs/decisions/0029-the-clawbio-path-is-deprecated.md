---
date: 2026-08-25
status: standing
kind: defect
symptoms:
  - "published log2FoldChange correlates 0.33 with actual ratios"
  - "gene at padj 1e-12 shown as 1.04x change"
  - "shrinkage coefficient resolves wrong or sign-flipped"
touches:
  - gars/_system/wrappers/nfcore-rnaseq-wrapper/
  - gars/_system/wrappers/rnaseq-de/
  - gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
  - gars/_references/assay_stage_skill_map.md
---
# The ClawBio path for rnaseq is deprecated, not deleted

> **Executed, 2026-08-27.** All three switchover criteria were met on a live run
> (`rnaseq-wrapper-validation`: 02.01 job 26842968, 02.02 job 26851720, numerical check
> r = 0.999952) and both `DEPRECATED-clawbio-path.md` files were deleted the same day. The
> fallback below is now history-only: reviving the path means `git checkout` from history,
> not a `git mv`. The criteria and reasoning stand as written.


## What happened

The assessment (2026-08-21, rec 8) said it plainly: a single declared skill-chaining pair
yielded three defects, one silent — a complete, plausible DE table in which every gene was
anonymous ([0010](0010-skill-chaining-defects-and-adaptation.md),
[0021](0021-the-adaptation-rename-belongs-in-code.md)) — and the adaptation layer existed to
compensate for a dependency of unproven quality. [0012](0012-gars-authored-wrappers-live-in-system.md)
had already routed every *new* assay through GARS-authored wrappers; rnaseq stayed the
exception on the older, riskier path. With wrapper #1 shipped and the pattern proven
([0028](0028-wrappers-are-thin-system-helpers.md)), the exception lost its justification.

## Decision

Both rnaseq sub-stages migrate to GARS-authored wrappers, so all assays share one idiom:

- **`_system/wrappers/nfcore-rnaseq-wrapper/`** — same shape as the atacseq wrapper; consumes
  the already-populated 59 GB derived cache as-is (`index/{star,salmon}` +
  `genome.transcripts.fa`), refuses a STAR cache with no `genomeParameters.txt`.
- **`_system/wrappers/rnaseq-de/`** — owns the whole DE path: `adapt_counts.py` first
  (0021), then a *generated* PyDESeq2 script under `gars-bio`, always via `sbatch` (0005,
  0027). Output schema byte-compatible with the retired skill
  (`gene,baseMean,log2FoldChange,pvalue,padj`), so projects from either path read the same
  downstream. The exit gate checks the 0010 defect class as content: identifier column named
  `gene`, first, with no empty values.

**The old path is deprecated, not deleted.** Each retired contract sits beside its
replacement as `DEPRECATED-clawbio-path.md`, stamped with the fallback instruction (`git mv`
it back over `CONTEXT.md`, revert the assay map's Source column). The installed clawbio
skills remain untouched — they were never vendored, so there is nothing to delete in the
workspace.

## Numerical validation

The migration's risk is 02.02: it reimplements a statistical analysis. That was validated
against reality, not assumed. The generated script ran on `leukemia-tall`'s actual inputs
(the 78,941-gene native matrix, the 10-sample design, `condition,MT,WT`) as Slurm jobs, and
its `de_results.csv` was compared to the proven 2026-08-24 baseline:

- **Tested gene set: identical** (22,783 genes) once the skill's low-count filter
  (>=10 in >=2 samples) was read out of its code and matched.
- **p-values and padj: identical** (padj r = 0.999985), **significant set: identical**
  (265/265 overlap at padj < 0.05), directions consistent.
- **log2FoldChange: deliberately not identical.** The retired skill published
  shrunken-looking fold changes from an estimator its own code cannot reproduce — its
  coefficient resolution returns empty for an A-vs-B contrast whose numerator is the design
  reference, and probing jobs showed neither pydeseq2's MLE, apeglm shrinkage on either
  coefficient sign, nor naive normalized ratios match its values (well-estimated genes agree
  to ~5%; one-group-zero genes collapse from |LFC|~7 to ~0.03). The decisive check: the new
  wrapper's LFC column correlates **0.992** with group ratios computed directly from the
  normalized counts; the retired skill's correlates **0.330** — a gene at padj ~1e-12 carried
  a reported fold change of 1.04x against an actual ~70x. This is the ClawBio chain's fourth
  recorded defect, silent like the third, now in the upstream report. The new wrapper publishes
  the documented DESeq2 Wald MLE instead of imitating an unidentifiable estimator, and says
  so in its generated script.

The validation also caught two real wrapper defects before they shipped — relative paths
frozen into the generated script broke under `submit.sh`'s working directory, and the first
staging attempt sat on the login node's local `/tmp`, invisible to compute nodes — which is
exactly why the validation ran before the switch, not after.

## Switchover criteria — when the deprecated files may be deleted

All three, recorded here so the deletion is a checklist and not a judgment call:

1. One full **live pipeline run** (02.01) under the gars wrapper completes on real data and
   passes `collect`.
2. Its downstream **02.02 completes live** under the gars DE wrapper on that run's counts.
3. The numerical-equivalence check holds for that run too: same inputs into old-baseline
   comparison where a baseline exists, or the sanity triple (genes tested matches the matrix,
   padj distribution non-degenerate, top genes stable under re-run) where none does.

Until then, both `DEPRECATED-clawbio-path.md` files stay, and falling back is one `git mv`.
