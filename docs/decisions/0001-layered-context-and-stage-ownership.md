---
date: 2026-08-08
status: standing
kind: decision
touches:
  - gars/CLAUDE.md
  - gars/CONTEXT.md
  - all stage contracts
---
# Layered context and exclusive stage ownership

**Layered context (L0–L4).** `CLAUDE.md` orientation, `CONTEXT.md` routing, stage contracts
loaded per task, config and references loaded selectively. An agent should never hold the whole
system in context.

**Exclusive stage ownership, encoded in directory names.** A project directory named `NN_*` is
written by stage `NN_*` and no other. `01_data/` was renamed `00_data/` because stage 00 creates
it — the number must identify the producer, otherwise the ownership rule is decorative.
`CONTEXT.md`, `HISTORY.md`, `_config/` carry no prefix: project metadata, not stage artifacts.
`HISTORY.md` is the one documented exception every stage appends to.

**Assay IDs lost their numeric prefix** (`01_rnaseq_bulk` → `rnaseq_bulk`) so `NN_` has exactly
one meaning per level: stage number at project level, sub-stage order within a stage.
