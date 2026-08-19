# GARS — repository orientation

**You are in the GARS source repository, not in a workspace.** This file orients work *on* the
system. If you are running an analysis instead, the entry point is `gars/CLAUDE.md`.

| Mode | You are | Entry point |
|---|---|---|
| **Developing GARS** | editing contracts, docs, the template | **this file** |
| **Using GARS** | running an analysis in a copied workspace | `gars/CLAUDE.md` |

---

## Read this first

**[DEVELOPMENT.md](DEVELOPMENT.md)** — current status, what is proven and what is not, next steps
in priority order. Volatile; update it whenever work stops or a run changes state.

**[docs/decisions/](docs/decisions/CONTEXT.md)** — one file per decision, with frontmatter naming
the paths it constrains. Durable; append-only. **Before changing anything under `gars/`, grep its
index for the path you are about to touch.** Most of what looks like an odd choice is recorded
there with the failure that motivated it, and reversing one without reading is how the lesson
gets lost.

| Document | Covers |
|---|---|
| [DEVELOPMENT.md](DEVELOPMENT.md) | status, next steps, quick reference |
| [docs/decisions/](docs/decisions/CONTEXT.md) | every design decision and its reasoning |
| [docs/execution-model.md](docs/execution-model.md) | how the layers relate: conda/pip, Nextflow vs nf-core, containers |
| [docs/assay-expansion.md](docs/assay-expansion.md) | research behind adding ATAC/ChIP/CUT&RUN/methyl assays |
| [README.md](README.md) | what GARS is, for an outside reader |

---

## Layout

```
CLAUDE.md           you are here — orientation for developing GARS
DEVELOPMENT.md      status and next steps
README.md           public-facing description
docs/               execution model, assay research, decisions/
examples/           synthetic worked example, no real data
gars/               THE WORKSPACE TEMPLATE — copied to start a project.
                    Its own CLAUDE.md is the entry point; do not restate its
                    internals here, or the two descriptions drift.
```

---

## Things a new session gets wrong

- **This repo is canonical.** `bioinfo-research-system/gars-test/` is a disposable workspace copy
  for testing; never develop there. Drift between the two was measured once and it was real.
- **`gars/` is a template that gets copied.** Anything added there travels into every future
  workspace, so repo-level material (this file, `docs/`, `DEVELOPMENT.md`) stays *outside* it —
  and anything the template's own files cite must live *inside* it, or the citation dangles the
  moment someone copies the folder.
- **Skills are not vendored.** They ship with the installed `clawbio` package and are read-only.
  There is no skills directory in the workspace. Resolve them via `$GARS_SKILLS` from
  `gars/_system/gars-env.sh`.
- **`$HOME` is not the work area.** `/gpfs/home/<user>` and `/gpfs/data/abl/home/<user>` are
  different directories. Use `GARS_ROOT`; using `$HOME` once pointed the container cache at an
  empty directory and silently re-pulled 26 images.
- **Deterministic artifacts are code's job, not the agent's.** Samplesheets, design tables and
  indexes are produced by `gars/_system/` scripts; contracts orchestrate them. Adding a rule
  means editing the script *and* the contract's Definitions, which share its vocabulary — see
  [decision 0011](docs/decisions/0011-deterministic-artifacts-in-stages-00-01.md).
- **Real data and patient-derived sample IDs never enter this repo.** `.gitignore` guards it;
  keep it that way.

## Editing contracts

The eight-section standard and the reasoning behind each section live in
[gars/_references/contract_standard.md](gars/_references/contract_standard.md). Read it before
writing or editing a contract.

Two mechanical rules, both learned the hard way:

- **Replace whole sections by heading.** A previous edit cut on `t.index("---")`, matched a
  markdown table separator, and silently duplicated half the document.
- **Adding a section to the standard means adding it to every contract in the same change.**

## Generated files

Never hand-edit these; run the script instead.

| File | Rebuild with |
|---|---|
| `gars/projects/_index.md` | `bash gars/_system/build_projects_index.sh gars` |
| `docs/decisions/CONTEXT.md` (index table) | `bash docs/decisions/build_index.sh` |
| a project's `01_samplesheets/*.csv` | `python3 gars/_system/stage01_samplesheet.py --project <dir>` |

## Releasing

Bump `gars/_references/VERSION` when the template changes shape — stage 00 stamps it into every
project it creates, so a project can always name the contract version that produced it.
