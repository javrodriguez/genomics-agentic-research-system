---
date: 2026-08-20
status: superseded
touches:
  - gars/_system/upgrade.py
  - gars/_system/workspace.py
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
---
# A workspace can be upgraded, and every stage stamps the version it ran under

> **Superseded 2026-08-20 by [0016](0016-workspaces-are-checkouts.md).**
> A workspace is a git checkout; the machinery below was removed. The per-stage version
> stamping introduced here was kept — it does not depend on the rest.

**Question.** A user clones GARS, copies `gars/` to a workspace, and starts a project. We then fix
a bug and push. The copy has no `.git` and no remote, so nothing reaches it. Is that right?

**It was half right.** The freeze is deliberate; the absence of any way out of it was not.

## Why the freeze is correct

Stage 00 stamps `_references/VERSION` into every project so results can name the contracts that
produced them. If a workspace tracked the repository, a validation rule could change between a
project's stage 00 and its stage 02, and the recorded version would be a lie. Contracts must not
move underneath a running analysis.

## Why the freeze alone was wrong

A fixed bug never reached an existing workspace. This was not hypothetical: the first real user
prompt was refused because `rnaseq-bulk` did not match, and after the fix was pushed, the only way
to obtain it was to copy the template again and move `projects/` across by hand.

## Decision

**`_system/upgrade.py`** replaces the template layer from a newer checkout and never touches
`projects/`. The split it relies on already exists — it is the factory/product split the workspace
is built around:

| Layer | Contents | On upgrade |
|---|---|---|
| factory | stage contracts, `_references/`, `_system/`, `_templates/`, `CLAUDE.md`, `CONTEXT.md` | replaced |
| product | `projects/` | untouched |

Nothing in the factory holds per-project state and nothing in `projects/` is needed to interpret a
contract, so the two swap independently.

Design points worth keeping:

- **Dry run by default.** `--apply` is required. The dry run lists exactly what differs, plus each
  existing project and the version it records.
- **Stage directories are discovered, not listed**, so a new stage is picked up without editing
  this script.
- **A stage present locally but gone upstream is reported, never deleted.** A stage removed
  upstream may still be the one that produced an existing project's results.
- **Idempotent** — re-running when nothing differs reports that and exits 0.

## The provenance rule this forced

Upgrading changes the contracts under existing projects. That is the point — a bug fix should
reach them — but it opens a hole: a project's `CONTEXT.md` would say `v0.2.0` while stage 01
actually ran under `v0.3.0`, with nothing recording the difference.

So **every stage stamps the template version it ran under**, not only stage 00, and the upgrade
appends a dated note to every project's `HISTORY.md`. A project's trail now reads:

```
## 2026-08-19 — 00_initialize_project — project created
Template version: v0.2.0
## 2026-08-20 — workspace upgraded — template v0.2.0 -> v0.3.0
## 2026-08-20 — 01_prepare_samplesheets — samplesheets emitted
Template version: v0.3.0
```

`CONTEXT.md` keeps naming the version that *created* the project; `HISTORY.md` names the version
behind each *result*. Those are different questions and both are now answerable.

This hole predated the upgrade command — hand-copying a newer script into a workspace has always
been possible, and was done while debugging the first real run. The command did not create the
risk; it made it worth closing.

## Rejected

- **Make the workspace a git clone and `git pull`.** Puts `projects/` inside a git tree, where a
  `samples.csv` full of patient-derived IDs is one `git add -A` from a public repository — the
  hazard guarded against in `.gitignore` and `CLAUDE.md`. It also makes contract drift *silent*,
  which is the thing the freeze exists to prevent.
- **Staleness detection** (a workspace checking whether it is behind). Useful, but it needs a
  recorded source path that nothing writes today, and it earns its place only once there is more
  than one workspace to track. Deferred deliberately, not forgotten.

  **Built the same day — see [0015](0015-workspace-staleness-detection.md).** The deferral
  reasoning was wrong: the number of workspaces was never the relevant variable, and a single
  workspace unable to say it is behind is exactly the gap that had just cost a user a dead end.
