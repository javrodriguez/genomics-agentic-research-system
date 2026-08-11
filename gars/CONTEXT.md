# Workflow: Genomics Research

## Overview
Four-stage pipeline: Initialize project → Ingest data → Bioinformatics → Custom analysis. Each stage has a defined contract, explicit inputs, and a clear output location. Human reviews between stages.

## Stage Map

| Stage | Purpose | Inputs | Output Location |
|---|---|---|---|
| 00_initialize_project | Initialize project, gather and organize project metadata | Project title, assay/s, one raw data path per assay | projects/<project_title>/ |
| 01_prepare_samplesheets | Validate the completed experimental design and emit workflow-ready samplesheets | Project title, completed samples.csv per assay | projects/<project_title>/01_samplesheets/ |
| 02_bioinformatics | Route an assay to its ordered sub-stages and run each one's skill | Project title, Assay ID, samplesheet + design, _config/<Assay ID>.yaml | projects/<project_title>/02_bioinformatics/<Assay ID>/ |
| 03_custom_analysis | Run customized bioinformatics workflows | Project title, goal | projects/<project_title>/03_custom_analysis |

## How Stages Connect
- 00 → 01: Stage 00 registers the raw data and validates it at the file level (links resolve, files intact, reads paired). It writes `files.csv` (one row per sample-lane, machine-owned) and `samples.csv` (one row per sample, experimental columns blank). **The boundary is a human gate:** the user fills in condition, group, and replicate in `samples.csv` before stage 01 runs.
- 01 → 02: Stage 01 validates the completed design and emits per-assay samplesheets. A bioinformatics workflow then processes assay-specific data. It can be composed by multiple sequence-ordered substages.
- 02 → 03: Uses processed data to perform a user's customized bioinformatics workflow. The workflow can be ingeneered with AI-support.

Validation is split along that human gate. File-level checks belong to stage 00, because that
is where the files are touched. Design-level checks belong to stage 01, because the design does
not exist until the user has written it.

Stage ownership of project directories is exclusive, and the numeric prefix encodes the owner:
a project directory named `NN_*` is written by the stage named `NN_*`, and by no other stage.

| Project directory | Owned by |
|---|---|
| `00_data/` | 00_initialize_project |
| `01_samplesheets/` | 01_prepare_samplesheets |
| `02_bioinformatics/` | 02_bioinformatics |
| `03_custom_analysis/` | 03_custom_analysis |

`CONTEXT.md`, `HISTORY.md`, and `_config/` carry no prefix: they are project-level metadata
rather than stage artifacts. `HISTORY.md` is the one file every stage appends to.

When adding a stage, give its output directory the stage's own number. Never reuse a number
across two directories.

## Stage Contract Standard
Every stage CONTEXT.md must contain these sections, in this order. `00_initialize_project` is
the worked example.

| Section | Role |
|---|---|
| Purpose | What the stage produces, in two or three sentences. |
| Inputs | What must be collected from the user or read from a prior stage. |
| Scope Boundaries | What the stage may **not** do. Stated negatively and specifically — positive instructions alone do not prevent improvisation. |
| Definitions | Every term the Process relies on, defined precisely enough that no judgment call is needed. |
| Process | Numbered steps. One action per step. Every failure branch is its own step with its own response template. |
| Response Format | The complete set of message templates. The agent sends nothing outside them. |
| OUTPUT | Table of artifacts written, with their exact contents. |

An agent running a stage follows that stage's contract literally. If a step seems to need
deviation, it stops and asks rather than acting.

## Reference Material

**Workspace-level** — `_references/`, shared across all projects:

| File | Use |
|---|---|
| `assay_stage_skill_map.md` | Authoritative map of Assay -> Stage -> Sub-stage -> Skills. Its Assay column is the definitive list of supported assays; stage 00 validates user-requested assays against it, and 02_bioinformatics uses the remaining columns to route each assay to its sub-stage and skills. |
| `environment.md` | Verified runtime for stage 02: the `gars-bio` and `gars-nxf` conda envs, how they were installed and why they are separate, and the traps that cost real debugging time. No Lmod modules are used. |
| `gars-bio.lock.txt`, `gars-bio.conda.txt`, `gars-nxf.conda.txt` | Lockfiles rebuilding both environments at exact versions. |
| `ICM_agents.pdf` | Integrated Context Methodology manuscript — architectural background. |

**Project-level** — `projects/<project_title>/_config/`, scoped to a single project:
Created empty by stage 00. One file per assay, named `<Assay ID>.yaml`, written by the user
before stage 02 runs. Stages 01 and 02 read it; nothing writes it automatically, because every
key in it is a scientific decision the system must not make on the user's behalf.

```yaml
# _config/rnaseq_bulk.yaml
strandedness: auto              # auto | forward | reverse | unstranded   (read by stage 01)
reference:                      # declare genome OR fasta+gtf, never both
  genome: GRCh38                # iGenomes key
  # fasta: /path/to/genome.fa
  # gtf:   /path/to/genes.gtf
aligner: star_salmon            # star_salmon | star_rsem | hisat2 | bowtie2_salmon
compute:                        # Slurm directives for the pipeline job
  partition: cpu_medium
  time: "48:00:00"
  cpus: 8
  mem: 64G
de:                             # read by sub-stage 02.02
  formula: "~ condition"        # every term must be a column of the design table
  contrast: "condition,treated,control"   # factor,numerator,denominator
```

A stage that finds a key missing stops and asks. It never substitutes a default for
`reference`, `de.formula`, or `de.contrast` — a wrong value there produces confident, wrong
biology rather than an error.

`_config/` also holds **`nextflow.slurm.config`**, the executor settings passed to the wrapper
via `--nextflow-config`. It is required, not optional: Nextflow submits each pipeline process as
its own Slurm child job, and without an explicit `process.queue` it dispatches them to whatever
partition it defaults to, ignoring the partition chosen for the parent job. The file must define
no `params` — the wrapper rejects configs that do, so its audited parameter surface cannot be
bypassed.
