---
date: 2026-08-28
status: standing
kind: lesson
touches:
  - gars/_system/wrapperlib.py
  - gars/_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py
  - gars/_templates/config/cutandrun.yaml
  - gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md
symptoms:
  - "exit 137 cgroup OOM-kill on plotHeatmap"
  - "same task dies at every memory bump"
  - "params change needs -resume but prepare refuses the populated run/"
---
# QC that cannot fit is a decision, not a casualty — and params changes may ride -resume

## What happened

cutandrun's first live run reached the QC tail and OOM-killed twelve deeptools heatmap
tasks at 64G. The resume road at 128G (the requeue guard's own re-entry, 320 tasks from
cache in ~100 seconds — the first deliberate live exercise of `-resume`) fixed the
per-sample heatmaps but DEEPTOOLS_PLOTHEATMAP_GENE_ALL — an all-samples × all-genes matrix
with a text dump — died at 137 on every attempt, effectively alone on the node. Some QC
figures simply do not fit a sane single-node allocation on real cohorts; a third memory
bump was the pre-recorded non-road.

## Decision

Two surfaces, both recorded:

1. **`qc.gene_heatmaps` in the seeded config** — `false` passes the pipeline's own
   `--skip_heatmaps`. The stage-03 scoring consumes peaks/consensus/bigwigs/multiqc, never
   these figures, so the skip is scientifically free — but it is a per-project decision the
   user records in the config, never a silent default. The template default stays `true`.
2. **`prepare --resume-refresh`** — a params-change-then-resume road: prepare may regenerate
   `params.yaml` and `submit.sh` WITHOUT moving `run/` aside, gated on both conditions
   (STATUS terminally FAILED, `run/.nextflow` present) so it can never bypass the
   populated-run protection for a live or completed run. The refusal message now names this
   road when Nextflow state exists. Without it, every params fix after a late-stage failure
   costs a full re-run — 2.5 hours here to re-earn 320 cached tasks.

## The lesson

An unfittable QC figure is not a resource-tuning problem, and a failed run's cache is an
asset the tooling must let you keep. The stop-rule ("no third bump") was written into the
previous instruction before the second failure — pre-deciding the escalation is what kept
this a one-hour incident instead of a night of bumps.
