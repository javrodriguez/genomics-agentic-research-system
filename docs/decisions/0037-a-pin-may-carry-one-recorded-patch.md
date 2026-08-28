---
date: 2026-08-28
status: standing
kind: decision
touches:
  - gars/_references/patches/cutandrun-3.2.2-trimgalore-dsl.patch
  - gars/_system/wrapperlib.py
  - gars/_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py
  - gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md
symptoms:
  - "Cannot invoke method optional() on null object"
  - "NullPointerException at workflow-graph build"
  - "module dies before any process runs, past config parse"
---
# A pin may carry one recorded patch, verified at preflight

## What happened

cutandrun's resubmission (job 26873422) cleared 0034's parser pairing and 0036's spike-in
pin, then died at 16 seconds: the checkout's own local module
(`modules/local/for_patch/trimgalore/main.nf`) writes its output options in legacy DSL2 —
`emit: html optional true` — which Nextflow 26 parses as a chained call on null: an NPE at
workflow-graph build. This is module-script DSL, beyond the v1 CONFIG parser's reach — the
recorded boundary of decision 0034. Blast radius, grepped across all five pins: exactly two
lines in one file, cutandrun only. No newer cutandrun release exists; upstream fixed the
file in their dev branch.

## Decision

The pin's provenance becomes **tag + one recorded patch**, which is more honest than
pretending the tag runs unmodified when it cannot:

- The patch ships in the workspace (`_references/patches/`), its replacement lines
  upstream's own dev-branch fix, verbatim — the authoritative source, not our invention.
- The wrapper's preflight verifies the PATCHED CONTENT (`module_patch_state` in wrapperlib)
  and refuses with `pipeline_patch`, naming the exact `git apply` command, until it is
  applied. Content is the authority: a re-cloned checkout regresses to legacy and the
  refusal comes back — the same verify-don't-hope shape as 0036's index content check.
- Rejected today: the legacy-Nextflow environment (a second pinned Nextflow for legacy-era
  pipelines). It would retire both 0034's parser flag and this patch, but it is real
  machinery — a new env, per-assay selection, re-validation — bought against a fragility
  the Nextflow lockfile pin already contains.

## The escalation trigger, stated now

This is cutandrun's SECOND legacy incompatibility (0034 was the first). If a THIRD surfaces
in this pipeline, stop patching: build the legacy-Nextflow environment and retire the whole
workaround family. Recorded here so the next incident starts at the decision, not the debate.
