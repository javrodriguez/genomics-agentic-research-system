---
date: 2026-08-21
status: standing
touches:
  - gars/_templates/config/
  - gars/_system/stage00_register.py
  - gars/_system/stage01_samplesheet.py
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/00_initialize_project/CONTEXT.md
---
# The project config is seeded, not authored

## What happened

Stage 01 finished and told the user: *"stage 02 reads `_config/<Assay ID>.yaml` and
`_config/nextflow.slurm.config` — reference, aligner, compute, and the DE formula and contrast.
Schema and rationale: `_references/config_schema.md`."*

They replied: **"I have to write the config file? what?"**

They were right. `_config/` was created **empty**, and the user was pointed at a 91-line schema
document and expected to produce two YAML files from nothing.

## The conflation

Two different things were being asked for under one instruction:

| | |
|---|---|
| **Make the scientific decisions** — which reference, which contrast | correct, and the system must never guess |
| **Author YAML from a schema doc** | pure friction with no scientific content |

And `nextflow.slurm.config` is not a decision at all. It is executor boilerplate whose contract
requires it to contain no `params`. Asking a user to hand-write it was indefensible.

This is the same error as *"Then run 01_prepare_samplesheets"* — describing the system as though
the user operates it, when the user decides and the agent operates.

## Decision

**Stage 00 seeds `_config/` at project creation** from `_templates/config/`:

- `<Assay ID>.yaml` with every derivable value already filled — `strandedness`, `aligner`,
  partition, time, cpus, mem, and `work_dir` resolved to the actual user and project.
- The genuinely scientific keys left marked `<REQUIRED: …>` with an inline example, because no
  stage substitutes a value for them.
- `nextflow.slurm.config` copied verbatim.

The file also carries the reasoning inline, so the traps are read at the moment of the decision
rather than in a separate document — notably that `genome: GRCh38` resolves to the NCBI build,
which has no `gene_biotype` and fails *after* counts are written.

**`<REQUIRED>` is machine-detectable, deliberately.** It is the same device as `{{placeholder}}`
in the project stamp: an unmade decision is visible to code, not just to a reader. Stage 01
reports the outstanding keys as `config_unfilled`, and the handoff names them in a table.

**The agent may write values the user supplies, and may never choose one.** Offering to type in
a contrast someone dictated is help; picking a reference genome for them is inventing the
experiment.

## What this does not change

Nothing is defaulted that carries scientific meaning. The system still refuses to run without a
reference, a formula and a contrast. The change is that the user completes a documented file
instead of conjuring one — four marked decisions instead of two blank files and a schema to read.
