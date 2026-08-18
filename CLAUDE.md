# GARS — repository orientation

**You are in the GARS source repository, not in a workspace.** This file orients work *on* the
system. If you are running an analysis instead, the entry point is `gars/CLAUDE.md`.

Two modes, two entry points — check which one applies before doing anything:

| Mode | You are | Entry point |
|---|---|---|
| **Developing GARS** | editing contracts, docs, the template | **this file** |
| **Using GARS** | running an analysis in a copied workspace | `gars/CLAUDE.md` |

---

## Read this first

**[DEVELOPMENT.md](DEVELOPMENT.md) is the living record.** Current status, what is proven and what
is not, next steps in priority order, and a Decision Log giving the *reasoning* behind every
design choice. Read it before changing anything — most of what looks like an odd decision is
recorded there with the failure that motivated it, and reversing one without reading is how the
lessons get lost.

Update it whenever work stops or a run changes state.

| Document | Covers |
|---|---|
| [DEVELOPMENT.md](DEVELOPMENT.md) | status, next steps, decisions and why |
| [docs/execution-model.md](docs/execution-model.md) | how the layers relate: conda/pip, Nextflow vs nf-core, containers, what holds what |
| [docs/environment.md](docs/environment.md) | the two conda envs, how they were installed, how to reproduce them |
| [docs/assay-expansion.md](docs/assay-expansion.md) | research behind adding ATAC/ChIP/CUT&RUN/methyl assays |
| [README.md](README.md) | what GARS is, for an outside reader |

---

## Layout

```
DEVELOPMENT.md      the living record — read first
README.md           public-facing description
docs/               execution model, environment, assay-expansion research
examples/           synthetic worked example, no real data
gars/               THE WORKSPACE TEMPLATE — copied to start a project
    CLAUDE.md           L0 orientation for a workspace user
    CONTEXT.md          L1 routing, stage map, config schema
    00_initialize_project/   01_prepare_samplesheets/
    02_bioinformatics/       03_custom_analysis/
    _references/        assay map, artifact types, VERSION
    tools/gars-env.sh   the single definition of the execution environment
```

---

## Things a new session gets wrong

- **This repo is canonical.** `bioinfo-research-system/gars-test/` is a disposable workspace copy
  for testing; never develop there. Drift between the two was measured once and it was real.
- **Skills are not vendored.** They ship with the installed `clawbio` package and are read-only.
  `tools/skills/` does not exist. Resolve them via `$GARS_SKILLS` from `tools/gars-env.sh`.
- **`gars/` is a template that gets copied.** Anything added there travels into every future
  workspace, so repo-level material (this file, `docs/`, `DEVELOPMENT.md`) stays *outside* it.
- **`$HOME` is not the work area.** `/gpfs/home/<user>` and `/gpfs/data/abl/home/<user>` are
  different directories. Use `GARS_ROOT`; using `$HOME` once pointed the container cache at an
  empty directory and silently re-pulled 26 images.
- **Real data and patient-derived sample IDs never enter this repo.** `.gitignore` guards it;
  keep it that way.

## Editing contracts

Stage contracts follow a seven-section standard defined in `gars/CONTEXT.md`. Two sections do the
real work and exist because positive instructions alone failed to constrain an agent:

- **Scope Boundaries** — stated negatively, naming the forbidden action literally
- **Response Format** — fixed templates; nothing else may be sent

When editing these files programmatically, replace whole sections by heading. A previous edit cut
on `t.index("---")`, matched a markdown table separator, and silently duplicated half the
document.
