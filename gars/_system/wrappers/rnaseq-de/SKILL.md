---
name: rnaseq-de
description: >
  GARS-authored differential expression (PyDESeq2) — the ClawBio rnaseq-de replacement (decision 0029), numerically validated against the leukemia-tall baseline; owns adaptation, DE, figures and report.
metadata:
  openclaw:
    source: gars                    # versioned in this repo, ours to maintain (decision 0012)
    pipeline: pydeseq2 (gars-bio)
    pipeline_version: "0.5.4"
    requires:
      bins: [python3, git]
      python: ">=3.6 (stdlib only)"
    install: >
      Nothing to install for the wrapper itself. The analysis script runs under $GARS_PY (gars-bio: pandas, pydeseq2, scikit-learn, matplotlib), always via sbatch.
---

# rnaseq-de

One stdlib file on `_system/wrapperlib.py` (decision 0028): `check` (preflight), `prepare`
(params.yaml + submit.sh + reproducibility bundle, deterministic bytes), `collect` (content
exit gate, OUTPUTS.tsv, STATUS, history entry). The sub-stage contract at
`02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md` orchestrates it; nothing here is invoked
directly by a user. Exit codes: 0 ok / 1 failure / 2 refused / 3 usage.
