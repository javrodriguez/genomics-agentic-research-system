---
date: 2026-08-12
status: standing
kind: decision
touches:
  - gars/_references/assay_stage_skill_map.md
  - docs/assay-expansion.md
---
# Assay expansion: wrap nf-core pipelines rather than import SNS

Full research in [assay-expansion.md](../assay-expansion.md). Summary and current state:

**Question.** Should the lab's existing SNS (Seq-N-Slide) pipelines be integrated as skills, to
gain ATAC-seq, ChIP-seq, CUT&RUN and methylation support?

**Decision: no. Wrap the published nf-core pipelines instead.**

The deciding finding is that **ClawBio's coverage is inverted relative to SNS's value**. The
seven SNS routes ClawBio already covers — the whole RNA-seq and WES/WGS family — it covers
portably, in GARS's native pattern, often through the identical underlying tools. The four to
five routes that would actually justify importing SNS (ATAC, ChIP, WGBS/RRBS) have no ClawBio
equivalent at all. So SNS's marginal value is small, while its cost is not: no preflight, no
structured errors, runtime R package installation, config mutated during execution, and N jobs
per route with nested `sbatch` — incompatible with a single-`job_id` STATUS line.

Making SNS portable is *feasible* — only ~145 of 13,113 lines are site-locked — but the
mechanical edits were never the cost. The real costs are per-segment containers (SNS needs
`java/1.8` **and** `jdk/17u028`, `python/2.7` **and** `3.6`, `r/3.6` **and** `r/4.1` — no single
environment satisfies that), a reference bundle to build, and owning a fork of someone else's
scientific pipeline. All to reach tools nf-core already provides portably.

**Plan: four new wrapper skills**, cloning the pattern ClawBio already runs three times over —
`atacseq` (2.1.2), `chipseq` (2.1.0), `cutandrun` (3.2.2), `methylseq` (4.2.0). WES/WGS needs a
contract only; `nfcore-sarek-wrapper` already exists and is ci-validated. **No pipeline
development is proposed** — the upstream pipelines do the science, the wrapper is what makes
them satisfy the GARS contract.

ChIP-seq and CUT&RUN are **two Assay IDs and two skills, never one skill with a mode flag**.
They wrap different upstream pipelines and normalise differently — read-depth versus spike-in —
so merging them would put a scientific decision inside code, which the config-is-a-user-decision
rule forbids.

**Keep SNS runnable as-is at NYU** for comparability with historical results. That is an argument
for not deleting it, not for porting it.

**Resolved since the report was written:**

- The blocker — "does any nf-core pipeline complete end-to-end on this cluster?" — is **closed**
  (2026-08-13). Six attempts failed first; every cause is now fixed in a contract.
- Local iGenomes mirror exists; ATAC/ChIP blacklist present; the CUT&RUN *E. coli* spike-in
  genome is already on the cluster.
- **No human Bismark index exists** anywhere on this cluster, so methylseq must build its own.
  That question is closed unfavourably — budget for it.

**Two blockers remain, both touching working contracts** — see Next Steps in
[DEVELOPMENT.md](../../DEVELOPMENT.md).
