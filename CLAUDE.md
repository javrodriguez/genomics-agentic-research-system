# GARS — repository orientation

**You are in the GARS source repository, not in a workspace.** This file orients work *on* the
system. If you are running an analysis instead, the entry point is `gars/CLAUDE.md`.

| Mode | You are | Entry point |
|---|---|---|
| **Developing GARS** | editing contracts, docs, the template | **this file** |
| **Using GARS** | running an analysis in `gars/` of a checkout | `gars/CLAUDE.md` |

---

## Read this first

**[DEVELOPMENT.md](DEVELOPMENT.md)** — current status, what is proven and what is not, next steps
in priority order. Volatile; update it whenever work stops or a run changes state.

**[docs/decisions/](docs/decisions/CONTEXT.md)** — one file per decision, with frontmatter naming
the paths it constrains. Durable; append-only. **Before changing anything under `gars/`, grep its
index for the path you are about to touch** — and when debugging, grep its Symptoms column for
what you are seeing. Most of what looks like an odd choice is recorded there with the failure
that motivated it, and reversing one without reading is how the lesson gets lost.

**A lesson lands in the artifact it constrains** (decision 0032): a template default or comment,
a menu entry, a preflight check, or a decision file with accurate `touches` — never parked in
status prose. DEVELOPMENT.md may point at where a lesson landed; it is not a lesson's home.

| Document | Covers |
|---|---|
| [docs/architecture.md](docs/architecture.md) | **how the system works** — the pipeline, the seven rules, where everything lives. Start here to re-orient. |
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
docs/               architecture, execution model, assay research, decisions/
examples/           synthetic worked example, no real data
gars/               THE WORKSPACE — users clone this repo and work in here.
                    Its own CLAUDE.md is the entry point; do not restate its
                    internals here, or the two descriptions drift.
                    gars/projects/ is gitignored: real data never enters git.
```

---

## Things a new session gets wrong

- **This repo is canonical.** `bioinfo-research-system/gars-test/` is a disposable workspace copy
  for testing; never develop there. Drift between the two was measured once and it was real.
- **`gars/` is the workspace.** Anything added there ships to every user on `git pull`, so
  repo-level material (this file, `docs/`, `DEVELOPMENT.md`) stays *outside* it — and anything
  `gars/` cites must live *inside* it, since a user working in `gars/` should never need to
  reach up into the repo.
- **The ClawBio skills are retired, not gone.** They remain installed with the `clawbio`
  package but no sub-stage invokes them (decision 0029; procedures deleted 2026-08-27). Every
  sub-stage runs on a GARS wrapper under `gars/_system/wrappers/`. `$GARS_SKILLS` still
  resolves, for inspection only.
- **`$HOME` is not the work area.** `/gpfs/home/<user>` and `/gpfs/data/abl/home/<user>` are
  different directories. Use `GARS_ROOT`; using `$HOME` once pointed the container cache at an
  empty directory and silently re-pulled 26 images.
- **Deterministic artifacts are code's job, not the agent's.** Samplesheets, design tables and
  indexes are produced by `gars/_system/` scripts; contracts orchestrate them. Adding a rule
  means editing the script *and* the contract's Definitions, which share its vocabulary — see
  [decision 0011](docs/decisions/0011-deterministic-artifacts-in-stages-00-01.md).
- **Real data and patient-derived sample IDs never enter this repo.** `.gitignore` guards it;
  keep it that way. `gars/projects/*/` is ignored, which covers the normal case. The hazard is a
  **stray workspace copy elsewhere in the repo directory** — its projects hold real `samples.csv`
  files, and one `git add -A` publishes them. Prefer path-limited staging
  (`git add -- gars/ docs/`) over `git add -A` here.

## Editing contracts

The eight-section standard and the reasoning behind each section live in
[gars/_references/contract_standard.md](gars/_references/contract_standard.md). Read it before
writing or editing a contract.

Two mechanical rules, both learned the hard way:

- **Replace whole sections by heading.** A previous edit cut on `t.index("---")`, matched a
  markdown table separator, and silently duplicated half the document.
- **Adding a section to the standard means adding it to every contract in the same change.**
- **When you change how something works, grep for its *description*, not its identifier.** The
  mechanism and the prose describing it live in different files, and the prose does not break —
  it just becomes a lie. Three bugs in one day came from updating only the mechanism: an assay
  menu was added while `T2` still asked the same question and shadowed it; workspaces became
  checkouts while six passages still said "copy the `gars/` folder"; config menus were added while
  stage 01 still offered to take the values as free text. Search for the old *concept*
  (`copy`, `write the config`, `type the path`), not the symbol you renamed.

## Before committing

Run both, from the repo root, whenever you touch `gars/_system/` or a contract — they are the
reason regressions stopped needing a live run to be found (decision 0023):

```bash
python3 tests/run_tests.py         # drives every helper through its real CLI
python3 tests/check_contracts.py   # sections, wait points, script<->contract vocabulary
```

## Generated files

Never hand-edit these; run the script instead.

| File | Rebuild with |
|---|---|
| `gars/projects/_index.md` | `bash gars/_system/build_projects_index.sh gars` |
| `docs/decisions/CONTEXT.md` (index table) | `bash docs/decisions/build_index.sh` |
| a project's `00_data/*/files.csv`, `samples.csv` | `python3 gars/_system/stage00_register.py finalize --project <dir>` |
| a project's `01_samplesheets/*.csv` | `python3 gars/_system/stage01_samplesheet.py --project <dir>` |

## Workspaces are checkouts

A user clones this repo and works in `gars/` directly; `gars/projects/` is gitignored, so real
data never enters git. Updating is `git pull`, pinning is `git checkout <tag>`.

There is deliberately **no bespoke upgrade machinery** — see
[decision 0016](docs/decisions/0016-workspaces-are-checkouts.md) for the detour that produced
some and why it was removed. Every stage still stamps the template version it ran under into the
project's `HISTORY.md`, so a `git pull` mid-analysis is recorded.

Three more `_system/` helpers compute rather than generate: `configure.py` (completes a project's
`_config/` from the genome registry and the design's own levels), `resolve_artifact.py` (stage 02's
input resolution) and `stage01_samplesheet.py --list-formats` (the registered per-assay
samplesheet formats).

## Releasing

Bump `gars/_references/VERSION` when the template changes shape — stage 00 stamps it into every
project it creates, so a project can always name the contract version that produced it.
