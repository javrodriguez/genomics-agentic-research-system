---
name: nfcore-rnaseq-wrapper
description: >
  GARS-authored wrapper around nf-core/rnaseq 3.26.0 — the ClawBio path's replacement (decision 0029). Consumes the existing derived-index cache layout as-is.
metadata:
  openclaw:
    source: gars                    # versioned in this repo, ours to maintain (decision 0012)
    pipeline: nf-core/rnaseq
    pipeline_version: "3.26.0"
    requires:
      bins: [python3, nextflow, java, git]
      python: ">=3.6 (stdlib only)"
    install: >
      Nothing to install for the wrapper itself. Runtime needs gars-nxf on PATH at submit time (via _system/gars-env.sh) and the pinned checkout at $GARS_PIPELINES/rnaseq-3.26.0.
---

# nfcore-rnaseq-wrapper

One stdlib file on `_system/wrapperlib.py` (decision 0028): `check` (preflight), `prepare`
(params.yaml + submit.sh + reproducibility bundle, deterministic bytes), `collect` (content
exit gate, OUTPUTS.tsv, STATUS, history entry). The sub-stage contract at
`02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md` orchestrates it; nothing here is invoked
directly by a user. Exit codes: 0 ok / 1 failure / 2 refused / 3 usage.
