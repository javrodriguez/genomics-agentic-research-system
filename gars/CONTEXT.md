# Workflow: genomics research

Four stages: initialize project → prepare samplesheets → bioinformatics → custom analysis. Each
has a contract with explicit inputs, one job, and one output location. A human reviews between
stages.

## Stage map

| Stage | Purpose | Inputs | Writes |
|---|---|---|---|
| `00_initialize_project` | Create the project, register and validate raw data | project title, assays, one raw data path per assay | `projects/<project_title>/` |
| `01_prepare_samplesheets` | Validate the completed design, emit workflow-ready samplesheets | project title, completed `samples.csv` per assay | `01_samplesheets/` |
| `02_bioinformatics` | Route an assay to its ordered sub-stages and run each one's skill | project title, Assay ID, samplesheet + design, `_config/<Assay ID>.yaml` | `02_bioinformatics/<Assay ID>/` |
| `03_custom_analysis` | **Not implemented.** Its contract replies and stops. | — | nothing |

Read the stage's own `CONTEXT.md` and execute it literally. Nothing on this page overrides a
contract; where they disagree, the contract is wrong and should be fixed, not worked around.

## How stages connect

- **00 → 01 is the human gate.** Stage 00 registers raw data and validates it at the file level
  (links resolve, files intact, reads paired), writing `files.csv` (one row per sample-lane,
  machine-owned) and `samples.csv` (one row per sample, experimental columns blank). The user
  fills in `condition`, `group` and `replicate` before stage 01 runs.
- **01 → 02.** Stage 01 validates the completed design and emits per-assay samplesheets. Stage 02
  routes the assay to its ordered sub-stages, each of which resolves its inputs by artifact type.
- **02 → 03.** Stage 03 would consume stage 02's artifacts. It does not exist yet.

Validation splits along the human gate: **file-level checks belong to stage 00**, because that is
where the files are touched; **design-level checks belong to stage 01**, because the design does
not exist until the user has written it.

## Directory ownership

Stage ownership of project directories is exclusive, and the numeric prefix encodes the owner: a
project directory named `NN_*` is written by the stage named `NN_*`, and by no other stage.

| Project directory | Owned by |
|---|---|
| `00_data/` | `00_initialize_project` |
| `01_samplesheets/` | `01_prepare_samplesheets` |
| `02_bioinformatics/` | `02_bioinformatics` |
| `03_custom_analysis/` | `03_custom_analysis` |

`CONTEXT.md`, `HISTORY.md` and `_config/` carry no prefix: they are project-level metadata rather
than stage artifacts. `HISTORY.md` is the one file every stage appends to.

When adding a stage, give its output directory the stage's own number. Never reuse a number
across two directories.

## Reference material

Workspace-level, in `_references/`, shared across all projects. Load only what the current
contract's Inputs section names.

| File | Use |
|---|---|
| `assay_stage_skill_map.md` | Assay → Stage → Sub-stage → Skill. Its **Assay column is the definitive list of supported assays**; stage 00 validates against it, stage 02 routes with the remaining columns. |
| `artifact_types.md` | The closed vocabulary a sub-stage may declare in `OUTPUTS.tsv`, the `native`/`adapted` roles, and the resolution rule by which a sub-stage finds its inputs by type rather than by path. |
| `config_schema.md` | What belongs in a project's `_config/`: the per-assay YAML, `nextflow.slurm.config`, and the index cache. Every key is a user decision; no stage defaults one. |
| `environment.md` | The verified runtime for stage 02 — the `gars-bio` and `gars-nxf` conda environments, how they were installed, why they are separate, and the traps. No Lmod modules. |
| `gars-bio.lock.txt`, `gars-bio.conda.txt`, `gars-nxf.conda.txt` | Lockfiles rebuilding both environments at exact versions. They pin the skills too, since the skills ship with `clawbio`. |
| `contract_standard.md` | The eight-section shape every stage contract follows. Needed when **writing** a contract, never when running one. |
| `VERSION` | The template revision. Stage 00 stamps it into every project, so a project can always name the contract version that produced it. |

Project-level configuration lives in `projects/<project_title>/_config/` and is described in
`config_schema.md`. Stages read it; nothing writes it automatically.

`_templates/` holds the stamps stages copy — see `_templates/CONTEXT.md`.
`_system/` holds `gars-env.sh` (the execution environment), `stage00_register.py` and
`stage01_samplesheet.py` (the registrar and the samplesheet emitter) and
`build_projects_index.sh`. Stage contracts orchestrate these; they do not duplicate what the
scripts compute.
