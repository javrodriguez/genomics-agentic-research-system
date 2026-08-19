---
date: 2026-08-19
status: standing
touches:
  - gars/_system/gars-env.sh
  - gars/_references/assay_stage_skill_map.md
  - docs/assay-expansion.md
---
# GARS-authored wrappers live in `gars/_system/wrappers/`

**Question.** Skills were de-vendored on 2026-08-13, so there is no in-workspace skills directory,
and `clawbio` is a third-party pip package we cannot add to. A wrapper GARS writes —
`nfcore-atacseq-wrapper` and its three siblings — had nowhere to live. This blocked the assay
expansion programme. Research: [assay-expansion.md](../assay-expansion.md) §6.2a.

**Decision: option A. A versioned `gars/_system/wrappers/`, exported as `$GARS_WRAPPERS`.**

## The rule this establishes

> **Third-party skills are installed and read-only. GARS-authored wrappers are versioned in this
> repo and are ours to maintain.**

`$GARS_SKILLS` resolves the former from the installed `clawbio` package. `$GARS_WRAPPERS` resolves
the latter from the workspace. A sub-stage contract names which of the two its skill comes from,
and the distinction is visible at a glance rather than inferred.

## Why A over contributing upstream

Option B — contribute the wrappers to ClawBio so they arrive via `pip` like the existing three —
is genuinely attractive: no new location, no maintenance burden, and it matches how the current
skills got here. It was rejected on **pacing, not principle**.

The four wrappers are the critical path for every remaining assay. Routing them through an
external project's review queue makes the lab's roadmap depend on someone else's schedule, for
work that only this lab currently needs. The upstream defects found in `rnaseq-de` — three breaks
in a declared chaining pair, one silent — are also a caution: the pair we depend on most was
shipped without an end-to-end test, so upstream review is not the quality gate it might appear.

**This is not a decision to fork or to hoard.** If a wrapper proves general, contributing it
upstream afterwards is strictly easier than blocking on it beforehand, and B remains open per
wrapper. Revisit if the maintenance cost of four wrappers becomes the dominant cost, which the
research note estimates at ~12 modules each mirroring a 2.1 MB skill.

## Why this does not violate the no-vendoring rule

The no-vendoring rule is about **not copying someone else's code** — it was written when both skill
copies had been extracted from upstream without their shared library and could not even print
`--help` (see [0004](0004-environment-installed-not-vendored.md)). Code GARS writes and owns is a
different thing. The precedent is already set twice over: `stage00_register.py` and
`stage01_samplesheet.py` are GARS-authored, versioned here, and nobody's fork.

The guard in `.gitignore` against a re-introduced `skills/` directory stays exactly as it is.
`wrappers/` is not `skills/`, and the distinction is the point.

## What this obliges

- `gars-env.sh` exports `$GARS_WRAPPERS`, and does **not** fail when the directory is absent —
  today it is, and stage 02 must keep working until the first wrapper lands.
- A wrapper is a directory under `_system/wrappers/<name>/` carrying a `SKILL.md` with the same
  frontmatter shape ClawBio uses, so `assay_stage_skill_map.md`'s Skill column reads identically
  whichever source a skill comes from.
- The assay map gains a column naming the source (`clawbio` or `gars`) when the first wrapper
  lands. Not before: a column with one value in every row is noise.
- Wrappers are covered by the contract requirements added since the research was written —
  `OUTPUTS.tsv`, content-checking exit gates, Slurm submission, sourcing `gars-env.sh` — listed in
  [assay-expansion.md](../assay-expansion.md) §6.2b.
