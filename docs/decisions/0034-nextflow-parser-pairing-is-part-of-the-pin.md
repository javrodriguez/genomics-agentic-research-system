---
date: 2026-08-28
status: standing
kind: decision
touches:
  - gars/_system/workspace.py
  - gars/_system/wrapperlib.py
  - gars/_references/gars-nxf.conda.txt
symptoms:
  - "Config parsing failed"
  - "Unexpected input: '(' ... def check_max"
  - "Invalid include source ... aws/batch/nextflow.config"
  - "job dies in seconds before any pipeline process"
---
# The Nextflow parser pairing is part of the pin

## What happened

The campaign's first ATAC dispatch (job 26863407) died in 8 seconds at config parsing:
nf-core/atacseq 2.1.2's `nextflow.config` defines the legacy `check_max` Groovy helper, and
the pinned Nextflow 26.04.6 ships only the strict config parser. Read-only diagnosis on the
same binary showed the blast radius was four of five pins: atacseq 2.1.2, chipseq 2.1.0 and
cutandrun 3.2.2 all carry `check_max` (each is its pipeline's LATEST release — there is no
newer pin to move to), and methylseq 4.2.0 fails differently (the strict parser resolves
profile `includeConfig` paths eagerly against a file absent from the checkout). rnaseq 3.26.0
is the only strict-clean pin — which is why every prior validation passed.
`NXF_SYNTAX_PARSER=v1` parsed all four clean, silently, on the exact failing binary.

## Decision

The parser is part of the version pairing, recorded in code beside the pins:
`workspace.NEXTFLOW_LEGACY_PARSER` names the four assays, and `wrapperlib.write_submit_sh`
exports `NXF_SYNTAX_PARSER=v1` in exactly their generated `submit.sh` — deterministic,
per-assay, carrying its own comment. rnaseq is deliberately not listed: its validated
configuration stays byte-identical. Tests pin presence for the four and absence for rnaseq.

## The horizon, stated honestly

Nothing in Nextflow's output promises the v1 parser survives future releases; it is honored
silently today. This pairing is valid exactly as long as Nextflow stays lockfile-pinned at
26.04.6. A Nextflow upgrade re-opens this decision — at which point the options are a newer
pipeline release (if one exists by then), a legacy Nextflow environment alongside, or
upstream fixes. The alternative rejected today — a second, older Nextflow environment with
per-assay selection — buys robustness against an unpin that the lockfile already prevents,
at the cost of real machinery.
