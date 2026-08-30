---
date: 2026-08-29
status: standing
kind: decision
touches:
  - gars/_system/authoring/
  - gars/_system/wrappers/
  - tests/run_tests.py
  - docs/upstream/clawbio-scrna-spatial-assessment.md
---
# The wrapper method is itself a skill, and a linter proves it

## What happened

Six wrappers exist. The knowledge of how to build a seventh correctly is real but scattered:
across 38 decision records, one upstream defect report, `_references/contract_standard.md`, and
1,944 lines of wrapper source. A new assay meant re-deriving that knowledge by reading, and a
reader who skipped a step would not find out until a run produced a plausible wrong number.

The immediate trigger was two new assays at once (single-cell and spatial) plus the finding in
[the ClawBio single-cell assessment](../upstream/clawbio-scrna-spatial-assessment.md) that a
maturity tier can be earned — the *highest* tier — without any scientific validation whatsoever.

## Decision

**`gars/_system/authoring/` carries the method as a skill: `SKILL.md` (the procedure) and
`create_bioinformatics_skill.py` (`scaffold` + `conform`).**

Not `gars/_system/skills/` — that path is guarded in `.gitignore` against re-introducing
vendored third-party skills ([0012](0012-gars-authored-wrappers-live-in-system.md)), and the
guard stays exactly as it is. `authoring/` is not `skills/`, the same way `wrappers/` is not.

Three properties make it more than documentation:

1. **`conform` is mechanical.** One module, stdlib-only, py3.6 syntax, `wrapperlib` used, the
   four exit codes, `ASSAY`/`SUBSTAGE` declared, the pin **derived from `workspace.PIPELINES`**
   rather than restated, all three verbs, `--model` accepted, `OUTPUTS.tsv` and `STATUS`
   written, writes atomic, `SKILL.md` frontmatter complete. Each rule cites the decision it
   enforces, so a tripped rule teaches instead of scolding.

2. **The standard is validated against known-good work.** All six existing wrappers pass, and
   that is a test in the suite (`SkillAuthoringTests`). A rule that fails a wrapper we already
   trust is a wrong rule, not a wrong wrapper — the linter is subordinate to reality.

3. **Every rule is mutation-tested.** Break it deliberately, the linter must go red. This
   caught a real weakness during construction: the `--model` rule tested `"--model" in src`,
   and a mutation renaming the flag to `--modelx` sailed through, because the rename still
   contains the substring. It now matches a complete quoted flag. Without mutation coverage a
   linter can pass everything and prove nothing.

## The scaffold refuses a spec with no content gate

`scaffold` will not generate a wrapper whose spec fails to mark one artifact
`content_gate: true`. This is [0010](0010-skill-chaining-defects-and-adaptation.md) enforced at
the earliest possible moment: an exit gate that checks existence once passed a complete DE table
whose identifier column had been silently dropped. Asking "which artifact's *content* proves
every sample survived?" at spec time is cheaper than discovering the answer was "none" after a
run.

It also **prints registry rows rather than writing them**. `workspace.PIPELINES` and
`assay_stage_skill_map.md` are shared, reviewed files; a generator that edits them turns a
review into a merge conflict.

## What the method cannot do, said plainly

`conform` proves a skill is well-formed. It cannot prove an answer is right, and the checklist
says so in its own words: the final item is validating at least one number against something
external — a published result, an independent reimplementation, or a naive calculation from the
same inputs.

That item exists because of the assessment finding: the dependency that published a
`log2FoldChange` correlating 0.33 with its own counts carried its library's highest maturity
tier and passed its own CI. Unit tests confirm code does what its author coded; they cannot
notice that the estimator is the wrong estimator. A gate that can be passed without ever
comparing to truth is a gate that misleads, so the comparison is a required, written-down step
rather than a field.

## Why not adopt an existing scaffolder

ClawBio ships `skill-builder`, which scaffolds a ClawBio skill from a spec. It was read and not
adopted, for the same reason as the rest of that assessment: it generates the 12-module
architecture [0028](0028-wrappers-are-thin-system-helpers.md) deliberately declined, and it
encodes no content-gate requirement, which is the single rule this project exists to enforce.
