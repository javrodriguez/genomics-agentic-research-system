---
date: 2026-09-14
status: standing
kind: decision
touches:
  - benchmarks/
  - evals/bench.py
  - evals/noise_floor.py
  - evals/runs/
  - tests/test_benchmark_discriminates.py
  - tests/run_tests.py
  - docs/implementation/row_2_change_report.md
---
# Row 2 benchmark tasks, owner run records, and independent holdout

## Context

§18 row 2 and §11.1 require the benchmark before the components it scores.
The gap assessment's Row 2 and review n-1 correctly classify it as missing.
The frozen Gap Study has six model tasks and three takes per half, the closest
existing repeat precedent, but neither GARS system scores nor a held-out slice.
D-20 is resolved by the owner's instruction: this benchmark scores a Claude Code
session driven by `gars/CLAUDE.md`; helpers and synthetic scorer tests are not
substitutes for agent runs.

Number note: **0043 and 0044 live on other branches and are not in this history**.
This decision uses 0045 to avoid collisions when those branches land.

## Decision

Use the five §11.1 defaults (Q2), with these concrete tuned-on tasks:

| Task | Why | `reference_source` | Scorer |
|---|---|---|---|
| `batch-confounded` | Tests whether condition/batch non-identifiability stops execution | `synthetic_with_generator_seed` | `exact` |
| `single-replicate` | Tests refusal of one independent biological replicate per condition | `synthetic_with_generator_seed` | `exact` |
| `pseudoreplicates` | Tests the distinction between libraries and biological replication | `synthetic_with_generator_seed` | `exact` |
| `bulk-rnaseq` | Exercises the existing RNA project artifact contract on the nf-core test-data route | `nfcore_test_data_expected_output` | `pytest` |
| `bulk-atacseq` | Exercises the existing ATAC project artifact contract on the nf-core test-data route | `nfcore_test_data_expected_output` | `pytest` |

The synthetic generator and seed 110112 supply external-to-agent truth for the
three `refuse and flag` answers. They are newly generated tuned-on design data;
no row 1 sealed fixture is read. Existing planted-effect counts, frozen graders,
case transcripts, and demo project are inspected and reused as precedents or by
reference, never copied into a competing fixture tree. The two nf-core source
descriptors record gaps, not fabricated numerical references. Their source enum
is the intended provenance; current scorers assert artifact contracts only.

The task loader uses the strict JSON subset of YAML: the existing narrow YAML
config parsers cannot read nested task records, and decision 0011 requires stock
Python 3.6.8 and stdlib only. `pytest` selects Python assertion contracts compatible
with pytest but executed using stdlib unittest assertions, not a new dependency.
No model or task-provided executable is loaded as a scorer. `human` is a recognized
schema enum but execution is refused pending a separately approved manual protocol.

The held-out slice is supplied at run time by `GARS_BENCH_HOLDOUT_DIR`, with
`tasks/*.yaml`, private inputs, `seal.json`, and private sealing notes. The complete
schema, canonical digest, access-denial procedure, output assertions, and owner
commands live in [HOLDOUT.md](../../benchmarks/HOLDOUT.md), sufficient for a separate
session to seal without the producer transcript. Development permits an
`independent_context` seal; public credibility requires `external_human_seal`.
The scorer verifies seal metadata and hashes, not the external ACL itself.
Tuned-on and held-out scores stay separate; without the variable, held-out is
explicitly `unmeasured` with no numerical denominator.

Two material omissions in the spec were paused and put to the owner in this
session before implementation. The owner explicitly approved both:

1. Equal binary task weights; noise floor = max minus min across exactly three
   distinct intact repeats; intact baseline = arithmetic mean. Strict
   `degraded < mean(intact) - noise_floor`. Compute separately by partition.
   Use exact fractions; inside or on the floor, a delta says `no change`.
2. `<sha>` in `<sha>-<model>-<prompt_sha>.json` is the SHA-256 of the output-file
   hash manifest plus the owner-supplied unique `run_id`; the scored GARS commit
   is stored separately as `git_sha`. This avoids overwriting byte-identical
   repeats at one commit/model/prompt while retaining the required filename shape.

Records include the agent's wall time, tokens and USD cost when known, `unknown`
otherwise. Deltas require identical model, prompt hash, and suite; three intact
repeats also require one commit. Unique ids and a suite digest prevent reusing a
repeat or comparing a changed task set. Explicit record inputs avoid automatic
selection of a convenient cohort. The acceptance cohort ids are `intact-1`,
`intact-2`, `intact-3`, `degraded-1`; missing ids are named in its SKIP reason.

The existing test runner only loads its own module-level TestCase classes;
import the two benchmark classes there, following its unittest shape. Do not
replace the runner or weaken any threshold. Current count prose is updated only
to match what that runner prints.

## What this does not close

- **NOT met:** the three intact agent repeats and the degraded agent run; their
  absence means no observed noise floor or benchmark discrimination.
- **NOT met:** the held-out seal, producer access-denial evidence and held-out
  measurements. No sealed data were read or created by this producer.
- **NOT met:** `NFCORE_RNASEQ_EXPECTED_OUTPUT_NOT_OBTAINED` and
  `NFCORE_ATACSEQ_EXPECTED_OUTPUT_NOT_OBTAINED`; owner retrieval must pin/hash
  actual test inputs and obtain expected numerical outputs. Artifact contract
  success alone does not establish numerical correctness or pipeline provenance.
- **NOT met:** growth to ten tasks; it follows discrimination, not this row.
- §11.5's README evidence table remains unmeasured; this change supplies no
  biological or public credibility claim and does not implement `make demo`.
- The §11.1 weighted score remains withdrawn. Binary counts within each partition
  are not a replacement aggregate across system components.
- The owner must retain agent traces and attest disabled design check/reviewer
  for the degraded arm. Output records cannot independently prove those facts.

## Test

`tests/test_benchmark_discriminates.py` covers schema/input hashes, non-model
scorers, tuned-directory holdout refusal, positive and corrupted artifact
contracts, run resources/naming, seal digests, ratio rendering, duplicate records,
model/prompt/suite mismatch, noise range/mean, and strict discrimination arithmetic.
The owner-run acceptance reads committed records and SKIPs when named records are
missing. Five deliberately invalid CLI inputs must exit nonzero: wrong input
hash, model scorer, held-out task in the tuned directory, cross-model delta,
and two-repeat noise floor. Full commands and observed runner summaries are in
[the change report](../implementation/row_2_change_report.md).

## Status

Repo-side implementation only. **Row 2 exit NOT met.** No approval or merge is
performed by this producer. Under the owner's standing ruling, this row merges
only after the separate study's done commit. Frozen study/runtime paths remain
unchanged; study CI controls may reject new `evals/` files until that point.

## Date

2026-09-14
