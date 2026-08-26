# Execution Model

How the pieces of the GARS stack relate: package managers, environments, workflow engine, and
containers. Written because the layering is easy to get backwards, and getting it backwards
leads to real mistakes — pruning a "unused" dependency that is load-bearing, or expecting a
container to hold something it does not.

---

## The layers

```
GARS contract      decides THAT this assay is processed, with which reference and samples
                                                              (this repo, markdown)
   │ invokes
   ▼
GARS wrapper       validates inputs, writes params.yaml + submit.sh, gates results
                     (_system/wrappers/, stdlib; since 0029 -- the ClawBio skills are the
                      deprecated fallback and remain installed in gars-bio)
   │ launches
   ▼
Nextflow           reads the pipeline, builds the task graph, submits Slurm jobs
                                                              (gars-nxf env)
   │ reads                              │ calls, once per task
   ▼                                    ▼
nf-core/rnaseq                       Apptainer ──▶ [ one tool per container ]
107 plain-text .nf scripts on disk.  (gars-bio env)   ~26 images per RNA-seq run
Declares the steps, their order,
and which container each one uses.
```

Read the two branches carefully: Nextflow **reads** the pipeline and **calls** the container
engine. The pipeline does not contain Apptainer, and Apptainer never sees the pipeline.

Each layer governs the one below without taking over its job. Two consequences worth holding
onto, each expanded below:

- a container holds **one tool**, not the pipeline
- the wrapper **launches**, it does not assemble anything

---

## Two package managers, one environment

`conda` and `pip` differ in reach:

| | Can install | Cannot install |
|---|---|---|
| **pip** | Python packages only | anything not written in Python |
| **conda** | anything: Python, compiled programs, CLI tools | — |

`gars-bio` needs both kinds of thing, so it was built in two passes:

- **conda pass** — Python 3.12 itself, plus `apptainer` and `squashfuse`. Those two are compiled
  programs; **pip cannot install them at all.**
- **pip pass** — `clawbio` and its ~120 Python dependencies, published on PyPI.

Each installer keeps its own record, so the environment has **two receipts**:

| File | Written by | Holds |
|---|---|---|
| `gars-bio.conda.txt` | `conda list --explicit` | 44 entries: interpreter, apptainer, squashfuse. Exact build URLs — reproducible, but linux-64 only. |
| `gars-bio.lock.txt` | `pip freeze` | 122 entries: clawbio and its tree. Version numbers only — portable. |

Neither rebuilds the environment alone. Replay conda first: pip needs an interpreter to exist
before it can install into one.

---

## Installing from scratch

```bash
# 1. Python + container runtime. conda handles both; note apptainer/squashfuse are not Python.
conda create -y -n gars-bio -c conda-forge python=3.12 pip apptainer squashfuse

# 2. The skills. pip AFTER conda, never the reverse.
conda run -n gars-bio pip install clawbio scikit-learn

# 3. The workflow engine, in its own environment.
conda create -y -n gars-nxf -c bioconda -c conda-forge "nextflow=26.04.6" "openjdk>=17,<26"

# 4. The pipeline, over the git protocol.
git clone --depth 1 --branch 3.26.0 https://github.com/nf-core/rnaseq.git \
    ~/install/nf-core-pipelines/rnaseq-3.26.0

# 5. Reference genome: Ensembl GRCh38 FASTA + GTF -> ~/install/refs/ensembl-GRCh38-116/

# 6. The workspace: copy gars/ from this repo.
```

Three ordering rules, each learned the hard way:

- **conda before pip.** Installing conda packages after pip can overwrite pip's files.
- **`nextflow` needs its own environment.** It and `clawbio` have conflicting `c-ares`
  constraints; conda cannot solve them together.
- **Pin `nextflow` explicitly.** Unpinned, conda silently resolved to a 2017 build (0.24.2)
  with Java 8, which then failed with opaque TLS errors.

Steps 4-5 are one-time. The derived index cache builds itself on the first pipeline run and is
reused thereafter.

---

## Containers: image, engine, format

Three things that are easy to conflate:

| Term | What it is |
|---|---|
| **Image** | A frozen, self-contained copy of a program plus its libraries, so it runs identically anywhere. nf-core publishes these in **Docker/OCI** format. |
| **Engine** | The program that runs an image: Docker, Apptainer, Podman, Charliecloud… |
| **SIF** | Apptainer's *own* single-file format. Not what nf-core publishes — what Apptainer converts to. |

Every nf-core module declares two recipes and picks by engine:

```groovy
conda     "${moduleDir}/environment.yml"
container "${ workflow.containerEngine == 'singularity' ? 'https://…/data'
                                                        : 'community.wave.seqera.io/library/…' }"
```

The same pipeline therefore behaves three ways:

| Profile | What happens |
|---|---|
| `--profile apptainer` (ours) | Apptainer pulls each Docker image and **converts** it to `.sif` in `~/.apptainer_cache`. 26 images for an RNA-seq run. |
| `--profile docker` | Docker runs the same images directly. **No SIF exists.** |
| `--profile conda` | No containers at all; Nextflow builds a small conda env per tool. |

**`squashfuse` matters here.** Without it Apptainer cannot mount a SIF and instead unpacks the
whole multi-GB image on *every* container launch — crippling on shared storage.

This is also why `gars-bio` contains no aligner: **STAR, Salmon and samtools arrive inside
containers**, not through conda or pip. Their absence from the lockfile is correct, not an
omission.

---

## Common misconception: the container does not hold the pipeline

It is natural to assume "the container has the pipeline, and Nextflow uses Apptainer to get at
it". The relationship is the reverse.

**Each container holds one tool.** A run caches images named `htslib_samtools_star_gawk`,
`bedtools_coreutils`, `picard`, `multiqc`, `rseqc_r-base`, `dupradar`, `tximeta` — about 26,
because the pipeline uses about 26 programs. A single "pipeline container" would be one image.

**The pipeline is plain text on disk.** 107 `.nf` scripts, 34 MB, in the git clone. `main.nf`
declares no container of its own. Nextflow reads those scripts directly.

```
Nextflow          reads the .nf scripts, builds the task graph,
                  decides STAR runs before Salmon
   │
   ├─ task 1 ──▶ Apptainer ──▶ [ STAR container ]     align sample 1
   ├─ task 2 ──▶ Apptainer ──▶ [ STAR container ]     align sample 2
   ├─ task 3 ──▶ Apptainer ──▶ [ Salmon container ]   quantify
   └─ task 4 ──▶ Apptainer ──▶ [ MultiQC container ]  report
```

Nextflow is the orchestrator and already holds the pipeline. It calls Apptainer once per task to
borrow a single tool, then discards that container. **Apptainer never sees the pipeline** and has
no idea what runs next. The pipeline orchestrates containers, not the other way round.

The practical consequence: containers are interchangeable tool deliveries. Switch to
`--profile conda` and the identical pipeline runs with no containers at all.

Why it is built this way — small single-tool images can be shared, cached and version-bumped
independently, while the pipeline stays readable, diffable text.

---

## Second misconception: the wrapper does not build the pipeline

A natural follow-on assumption is that the wrapper "organises the containers and tools into a
pipeline, which Nextflow then orchestrates". The wrapper does considerably less than that. It
never touches containers and it does not assemble anything. (This was written about the
ClawBio wrapper and is equally true of the GARS-authored wrappers that replaced it, decision
0029 — they validate, translate config into `params.yaml`, generate `submit.sh`, and gate
results; the pipeline is untouched.)

| Piece | Job | Knows about containers? |
|---|---|---|
| **nfcore-rnaseq-wrapper** (gars, `_system/wrappers/`) | Validates the samplesheet, references and executor config, translates `_config/<assay>.yaml` into `params.yaml`, generates `submit.sh`, gates the results afterwards | **No** — passes `-profile apptainer` through as a string |
| **nf-core/rnaseq** (the pipeline) | Declares the steps, their order, and **which container each step uses** — 78 modules, 78 declarations | Yes, this is where they are declared |
| **Nextflow** (the engine) | Reads the pipeline, builds the task graph, submits Slurm jobs, calls the container engine per task | Yes, it invokes them |
| **Apptainer** | Runs one tool in one container, once | Runs them |

The wrapper's only container-adjacent code is profile passthrough and a macOS Docker memory
workaround. Nothing in it decides that STAR runs in one image and Salmon in another — **the
pipeline already says so**, and said so before the wrapper or this project existed. The step
order is authored by the nf-core community, not assembled at run time.

Stated correctly:

> The nf-core/rnaseq **pipeline** declares which tool runs at each step and in what order.
> **Nextflow** executes that declaration, calling **Apptainer** to run one tool-container per
> task. The **wrapper** is a launcher that validates inputs and starts Nextflow — it neither
> builds the pipeline nor manages containers.

### One line each

```
GARS contract    decides THAT bulk RNA-seq should be processed        (markdown)
  wrapper        checks inputs, builds params.yaml, starts Nextflow   (python)
    Nextflow     schedules tasks, calls the container engine          (engine)
      pipeline   declares the steps and their containers              (static .nf text)
        Apptainer  runs one tool                                      (per task)
```

### The sanity check

**The pipeline runs perfectly well without the wrapper.** `nextflow run nf-core/rnaseq` by hand
produces the same result. The wrapper exists to make that invocation validated, reproducible and
auditable — preflight checks, a pinned pipeline version, a provenance bundle. It is a seatbelt,
not an engine.

The same test applies one layer up: the pipeline runs without GARS. GARS decides *that* an assay
should be processed, with which reference and which samples, and records why. Each layer adds
governance over the one below without taking over its job.

## Nextflow and nf-core are not the same thing

**nf-core is always Nextflow.** nf-core is a community collection of pipelines *written in*
Nextflow, plus shared standards and tooling. An nf-core pipeline cannot run without it.

**Nextflow is not always nf-core.** It is a general workflow engine; plenty of pipelines written
in it have nothing to do with nf-core.

```
Nextflow  ──── the engine (general purpose, containers optional)
   ├── nf-core/rnaseq   ── one pipeline written for it
   └── any other pipeline
```

The "every module declares a container" convention is **nf-core's**, not Nextflow's. Nextflow
itself will happily run bare commands with nothing containerised.

---

## Running a skill: source one file

Every `submit.sh` begins with a single line:

```bash
source "$WS/_system/gars-env.sh"
```

That script is the **only** definition of how to run a GARS skill. It sets `PATH` (with
`gars-nxf` first, so `java` resolves to OpenJDK 17 rather than the system Java 1.8 that Nextflow
refuses), `JAVA_HOME`, the Apptainer and Nextflow caches, and exports `$GARS_PY`,
`$GARS_SKILLS`, `$GARS_PIPELINES` and `$GARS_REFS`. It exits non-zero if an environment or the
skills directory is missing, so a broken setup fails at submission rather than minutes into a
scheduled job.

It exists because the same ~20 lines of setup were previously copy-pasted into every
`submit.sh`, in every project, for every sub-stage — and they drifted. A recovered script was
still pointing at a vendored skills path that had been removed. Centralising cut a job script
from 97 lines to 29.

It lives **in the workspace**, not in `$HOME`: a workspace is a copy of the template and the
contracts treat it as self-contained, so copying a workspace carries its environment definition,
and it is versioned in git where a change is a reviewable commit.

### Persistent vs disposable: two very different locations

A recurring confusion, worth stating plainly. Only one of these belongs on scratch:

| | Location | Size | Lifecycle |
|---|---|---|---|
| Nextflow work dir | `/gpfs/scratch/<user>/gars-work/` | 250-350 GB per run | **Disposable** — deleted once `results/` is verified |
| Apptainer image cache | `$GARS_ROOT/.apptainer_cache` | ~17 GB | **Persistent** — reused by every run |
| Reference genome + derived indices | `$GARS_ROOT/install/refs/` | ~60 GB | Persistent |
| Pinned pipeline checkout | `$GARS_ROOT/install/nf-core-pipelines/` | 34 MB | Persistent |

The test is: *does losing this cost only time, or does it cost repetition forever?* A work
directory costs nothing to lose. The image cache costs a re-pull on every subsequent run, and
scratch filesystems are commonly purged after 30-90 days — so putting the cache there would
silently make every run slower, months later, for no visible reason.

### `GARS_ROOT`, and why not `$HOME`

`$HOME` (`/gpfs/home/<user>`) and the group work area (`/gpfs/data/abl/home/<user>`) are
**different directories** on this cluster — different inodes. Some subtrees, such as `install/`,
are shared via symlink, which makes them look identical if you spot-check the wrong path.

An early version of `gars-env.sh` used `$HOME` and therefore pointed `APPTAINER_CACHEDIR` at an
empty directory. Nothing failed: runs simply re-pulled all 26 images and were slower. That is the
most dangerous shape of bug in this system — no error, no wrong answer, just silent waste.

`gars-env.sh` now derives everything from one explicit `GARS_ROOT`, reports the resolved cache
and its image count on every invocation, and warns when the cache is empty:

```
[gars-env] cache=/gpfs/data/abl/home/rodrij92/.apptainer_cache (26 images)
```

An empty cache is a warning rather than an error, because a genuinely first run has one.

### For interactive debugging

Batch jobs never use `conda activate` — absolute paths behave identically on every node, which
is what a Slurm script needs. But for poking at things by hand, both environments now carry
their own variables, so activation just works:

```bash
conda activate gars-nxf && nextflow -v      # JAVA_HOME set by the env
```

Without that, `nextflow -v` fails with *"Cannot find Java or it's a wrong version"* even though
OpenJDK 17 sits in the same environment — Nextflow looks at `PATH` and `JAVA_HOME`, not at where
its own binary lives. That error looks like a broken install and is not.

## Where each piece lives

| Piece | Location |
|---|---|
| GARS contracts | this repo, `gars/` |
| ClawBio skills | `gars-bio` env, `site-packages/clawbio/skills/` — never vendored |
| Nextflow + Java | `gars-nxf` env |
| Apptainer + squashfuse | `gars-bio` env |
| nf-core/rnaseq pipeline | `~/install/nf-core-pipelines/rnaseq-3.26.0` |
| Container images | `~/.apptainer_cache` |
| Reference genome | `~/install/refs/ensembl-GRCh38-116/` |
| Derived indices | `…/derived/nf-core-rnaseq-3.26.0/` — keyed by pipeline version |
| Nextflow work dir | `/gpfs/scratch/<user>/gars-work/` — disposable |
