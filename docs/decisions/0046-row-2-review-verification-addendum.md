---
date: 2026-09-15
status: standing
kind: defect
touches:
  - benchmarks/
  - evals/bench.py
  - evals/noise_floor.py
  - tests/test_benchmark_discriminates.py
  - README.md
  - DEVELOPMENT.md
symptoms:
  - "coherent fabricated scores pass without outputs"
  - "held-out evidence absent but benchmark acceptance green"
  - "coupled samplesheet and count deletion passes"
---
# Row 2 review verification addendum

Addendum to [0045](0045-row-2-benchmark-tasks-and-holdout.md), whose original bytes
remain unchanged. The independent round-1 review identified trust in supplied
verdicts, an incomplete exit gate, sample-loss ambiguity, missing public vocabulary,
JSON boolean/number confusion, and unsupported expanded-suite platform claims.

The owner explicitly approved a hashed expected-samplesheet field in this round
and authorized the implementation work needed to finish the review fixes.
`expected_samplesheet` names a hashed task input; `null` fails scoring until an
independent roster exists. Count references use `reference_counts`, mapping count
types to hashed input tables, with exact byte equality and no invented tolerance.
The strict exit requires all count references and materialized samplesheet FASTQs.
The existing nf-core tasks retain explicit gaps; no sample roster or biological
reference was invented for them.

Records remain schema version 1 with the existing owner-approved filename recipe.
An authorized evaluator must retain the artifacts under an external run-id archive,
pin its scorer checkout, verify hashes, and recompute verdicts against that checkout's
task suite. Internal agreement between a total and its booleans is insufficient.
The scorer cannot authenticate agent authorship, pipeline execution, human reference
independence, or access denial; those require the owner's retained evidence.

`bench.py row-exit` is the strict evidence gate: all four runs, both measured
partitions, resolved references, and unchanged strict discrimination thresholds.
The repository-only test may skip missing owner runs; its green with that skip
does not establish the row exit. Arithmetic controls now score actual scratch
files under a pinned synthetic suite rather than hand-authoring verdicts.

All agents receive RESPONSE.md uniformly. HOLDOUT.md specifies the complete prompt
bundle hash, artifact archive, reference materialization, and evaluator procedure.
JSON exact equality preserves types recursively. Current collection counts are
separate from dated execution evidence; expanded-suite cluster status is unverified.

Correction to 0045's evidence-table statement: the prescribed fixed-row README
table is inherited **missing**, not an existing table with unmeasured cells. It
belongs to the earlier row and is not created in this fix. The broader repository
also retains inherited personal/machine-specific text; this row makes no claim
of repository-wide sanitization and does not alter protected trees for that purpose.

Verification commands and actual results are appended to the
[item report](../implementation/row_2_change_report.md). No agent run, seal,
external reference retrieval, cluster execution, or merge is supplied by this round.
