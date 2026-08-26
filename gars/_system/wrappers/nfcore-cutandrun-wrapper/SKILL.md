---
name: nfcore-cutandrun-wrapper
description: >
  GARS-authored wrapper around nf-core/cutandrun 3.2.2 — spike-in-calibrated CUT&RUN/CUT&Tag with group-shaped design and IgG controls (decision 0031).
metadata:
  openclaw:
    source: gars                    # versioned in this repo, ours to maintain (decision 0012)
    pipeline: nf-core/cutandrun
    pipeline_version: "3.2.2"
    requires:
      bins: [python3, nextflow, java, git]
      python: ">=3.6 (stdlib only)"
    install: >
      Nothing to install for the wrapper itself. Runtime needs gars-nxf on PATH at submit time and the pinned checkout at $GARS_PIPELINES/cutandrun-3.2.2.
---

# nfcore-cutandrun-wrapper

One stdlib file on `_system/wrapperlib.py` (decision 0028): `check` (preflight), `prepare`
(params.yaml + submit.sh + reproducibility bundle, deterministic bytes), `collect` (content
exit gate, OUTPUTS.tsv, STATUS, history entry). The sub-stage contract at
`02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md` orchestrates it; nothing here is invoked
directly by a user. Exit codes: 0 ok / 1 failure / 2 refused / 3 usage.
