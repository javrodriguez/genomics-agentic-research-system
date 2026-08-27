---
date: 2026-08-21
status: standing
kind: lesson
symptoms:
  - "typed fasta/gtf paths, typos expensive"
  - "wrong-release GTF silently misannotates every count"
touches:
  - gars/_references/genomes.md
  - gars/_system/configure.py
  - gars/02_bioinformatics/CONTEXT.md
---
# The config's scientific decisions come from menus, not free text

## The problem

[0019](0019-config-is-seeded-not-authored.md) stopped the user authoring a config from a blank
file, but left four decisions to be typed by hand:

```
fasta     which reference genome FASTA the reads are aligned to
gtf       which gene annotation defines the features reads are counted against
formula   the design formula the differential-expression model fits
contrast  which two levels of the design are compared, and in which direction
```

Two of those are paths, and one is a pair of level names. All three are typo-shaped, and their
typos are expensive:

- A FASTA paired with an annotation from a different release **silently misannotates** every
  count.
- A contrast naming a level that is not in the design fails hours in, or worse, names a level
  that exists but was not the comparison intended.

## Decision

**Every one of them is selected from a closed set, built by code.**

**Genome.** `_references/genomes.md` holds one row per reference: FASTA, matching GTF, and the
version-keyed index cache. Choosing a genome sets all three **together**, so the pairing is a
property of the reference rather than something the user has to get right twice. Only verified
references are listed — the iGenomes `GRCh38` is the NCBI build, carries no `gene_biotype`, and
fails *after* counts are written ([0005](0005-execution-failures-and-fixes.md), failure 5). Keeping
it out of the registry is what stops that being rediscovered.

Selecting the registered GRCh38 also wires up its cache, which skips ~43 GB and ~40 minutes of
index building. Correctness and speed happen to point the same way here.

**Contrast.** Built from `01_samplesheets/<Assay ID>_design.csv` — the levels the user actually
wrote. Every *ordered* pair is offered, because direction is itself a decision: `condition,MT,WT`
measures MT relative to WT, and reversing it reverses the sign of every fold change. Each option
states that in words. A pair whose levels do not both have ≥2 samples is marked `testable: false`
and refused, because a one-sample level produces something that looks like an answer.

**Formula** defaults to `~ condition`, the simplest model the design table supports.

## The line this draws on defaults

`config_schema.md` says no stage defaults a scientific key, and this looks like a reversal. It is
not, because the rule was never "never choose" — it was **never choose silently**. A default the
user is shown before anything runs is a starting point they can reject; a default applied quietly
is the system inventing the experiment.

So `apply --dry-run` prints exactly what would be written and the contract requires the agent to
show it and wait. `~ condition` is visible, and the prompt names the alternative that matters
(`~ batch + condition`, to control for a batch effect). What remains forbidden is unchanged: the
agent may write values the user selected, and may never select one for them.

## What is deliberately not automated

- **Adding a genome.** The contract forbids the agent editing the registry to satisfy a request.
  A reference is registered after someone verifies the FASTA/GTF pairing and readability; an
  unverified row is worse than an absent one.
- **Mouse.** `/gpfs/data/sequence/references/iGenomes/Mus_musculus/Ensembl/` exists on this
  cluster and is the obvious next row, but it has not been run against. It stays out until it has.
- **`strandedness`, `aligner`, `compute.*`.** Already filled by the seed and rarely wrong; adding
  menus for them would be motion, not safety.
