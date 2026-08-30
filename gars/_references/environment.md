# Runtime Environment

This file records **what is installed and how to reproduce it**, and ships inside the workspace
template so a copied workspace can rebuild its own runtime. For how the pieces relate — package
managers, Nextflow vs nf-core, containers and SIF — see `docs/execution-model.md` in the GARS
source repository; that document is background and is not shipped in a workspace.

Verified on the login node, 2026-08-11. Re-verify after any cluster change.

## Cluster

| Facility | State |
|---|---|
| Scheduler | Slurm (`sbatch`, `squeue`, `sacct`) |
| Modules | Lmod (`module avail`, `module load`) |
| Conda | 26.1.1, at `~/install/miniconda_clean` |
| Containers | Singularity only — this cluster has no Docker |

## What stage 02 needs

**No Lmod modules.** The whole stack is user-owned in two conda environments, so an
admin-side module change cannot break a run.

| Env | Holds | Used by |
|---|---|---|
| `gars-bio` | ClawBio skills' Python deps, **apptainer 1.5.3**, squashfuse | both sub-stages; provides the container runtime |
| `gars-nxf` | **nextflow 26.04.6**, openjdk 17 | 02.01 only, as the pipeline engine |

```bash
BIO=~/install/miniconda_clean/envs/gars-bio
NXF=~/install/miniconda_clean/envs/gars-nxf
export PATH="$NXF/bin:$BIO/bin:$PATH"      # nextflow + apptainer + squashfuse
export APPTAINER_CACHEDIR=~/.apptainer_cache
export NXF_APPTAINER_CACHEDIR=~/.apptainer_cache
$BIO/bin/python nfcore_rnaseq_wrapper.py --profile apptainer ...
```

### Why two environments

`nextflow` and `clawbio` **cannot coexist**. Nextflow 26.04.6 needs a `curl`/`libnghttp2`
stack requiring `c-ares >=1.32`, while clawbio's tree (grpcio, google-cloud-*) pins older
`c-ares`. The solve fails with `LibMambaUnsatisfiableError`. They are different runtimes — the
wrapper calls `nextflow` as a subprocess — so separating them costs nothing.

### Trap: an unpinned conda install silently gave us Nextflow from 2017

`conda install -c bioconda nextflow` resolved to **nextflow 0.24.2** with **openjdk 8**, rather
than reporting the conflict above. Nothing failed loudly; `nextflow -version` just emitted a
wall of Maven `handshake_failure` errors, because Java 8's TLS can no longer negotiate with
Maven Central. Nine years of silent regression.

**Always pin the version explicitly** (`nextflow=26.04.6`) so a conflict surfaces as an error
instead of a downgrade. This is the strongest argument for the lockfiles below.

### Trap: Apptainer needs squashfuse, or it extracts every image

Without `squashfuse` on `PATH`, Apptainer cannot mount SIF images and instead logs
`Converting SIF file to temporary sandbox...`, unpacking the **entire image on every container
launch**. For an nf-core run — dozens of tasks, multi-GB images, shared GPFS — that is
crippling I/O. `squashfuse 0.6.2` is installed in `gars-bio` and removes the message.

`fakeroot` failed to install and was left out. It is only needed to *build* images; pulling and
running nf-core containers does not require it.

### Legacy note

Earlier drafts used `module load python/cpu/3.10.6`, `nextflow/25.10.3`, and
`singularity/3.11.5`. All three are superseded. If you ever fall back to modules: **never pipe
`module load`** — piping runs it in a subshell and silently discards the `PATH` change, which
already produced one false "the module stack is broken" diagnosis.

## Environment-variable precedence worth knowing

`gars-env.sh` only *defaults* `NXF_HOME` (and the container-cache variables) when they are
unset — an operator's own exports win. On the validated cluster setup, a `~/.bashrc` export
points `NXF_HOME` at lab-shared storage rather than `$GARS_ROOT/.nextflow_gars`, and every
validated run (including the wrapper-switchover chain) ran under that precedence. Deliberate:
gars-env does not override a working operator environment; if you need the GARS-local default,
unset the variable before sourcing.

## The `gars-bio` conda environment

Created 2026-08-11. Holds the ClawBio library and everything both retired skills needed —
kept as the provider of PyDESeq2, scikit-learn and the container runtime (the skills are
retired from every sub-stage, decision 0029; the sections below stand as environment
provenance).

| Field | Value |
|---|---|
| Name | `gars-bio` |
| Path | `~/install/miniconda_clean/envs/gars-bio` |
| Interpreter | `~/install/miniconda_clean/envs/gars-bio/bin/python` (3.12) |
| Lockfile | `_references/gars-bio.lock.txt` |

### How it was installed

```bash
# gars-bio: skills + container runtime
conda create -y -n gars-bio python=3.12 pip
conda run -n gars-bio pip install clawbio scikit-learn
conda install -y -n gars-bio -c conda-forge apptainer squashfuse

# gars-nxf: pipeline engine, kept separate (see "Why two environments")
conda create -y -n gars-nxf -c bioconda -c conda-forge "nextflow=26.04.6" "openjdk>=17,<26"
```

`clawbio` pulls its own dependency tree, which is why `gars-bio` ends up with ~125 packages
from a two-package request. Note the explicit `nextflow=26.04.6` pin — without it conda
installs a 2017 build, see the trap above.

### Why these two packages

**`clawbio`** — the (now retired, decision 0029) skills import a shared ClawBio library that
was not copied with them:

| Skill | Imports |
|---|---|
| `nfcore-rnaseq-wrapper` | `clawbio.common.{textio, checksums, report, reproducibility, portable_commands}` across 6 modules |
| `rnaseq-de` | `clawbio.common.report.write_result_json` |

Without it the skills raise `ModuleNotFoundError: No module named 'clawbio'` at import and
cannot even print `--help`. Neither `gars/_system/` nor `archive/bio_icm_system/` contains it —
the skills were extracted from upstream without their shared library, in both locations.

**`scikit-learn`** — required by `rnaseq-de` for PCA, and absent from every cluster Python
module.

`pydeseq2` was **not** requested explicitly; it arrived as a `clawbio` dependency. That is the
preferred DE backend for `rnaseq-de` (`--backend {auto,pydeseq2,simple}`), so no separate
install is needed.

### Provenance of the package

PyPI `clawbio` 0.6.1 was confirmed to be the right project before installing, rather than
trusted on the name — a same-named PyPI package is a standard dependency-confusion vector.
Its metadata gives `Repository: https://github.com/ClawBio/ClawBio`, matching the homepage
declared in each skill's own SKILL.md, and its summary matches the skills' provenance
("bioinformatics-native AI agent skill library, built on OpenClaw"). All nine symbols the
skills import were confirmed present in the wheel before install.

### Why installed rather than vendored alongside the skills

When the skills were still vendored in the workspace, each put `SKILL_DIR.parent.parent` on
`sys.path`, so a `clawbio/` package placed beside them would have been found. Vendoring was
rejected anyway, and the skills were de-vendored afterwards:

1. **It has a real dependency tree.** `clawbio.common.report` imports `clawbio.common.audit`,
   which imports `opentelemetry`. Copying the source in yields a different `ModuleNotFoundError`.
2. **The wheel bundles `clawbio/skills/`** — its own copies of `nfcore-rnaseq-wrapper` and
   `rnaseq-de`. Vendoring 14 MB of it would re-introduce the skill duplication that was already
   removed once from `02_bioinformatics/`.

A normal install puts the package on `sys.path`, which is all the skills need.

### Reproducing the environments exactly

Three lockfiles, all in `_references/`:

| File | Rebuilds | Command |
|---|---|---|
| `gars-bio.conda.txt` | gars-bio **conda** layer (44 pkgs): interpreter, apptainer, squashfuse. Pins exact build URLs, so linux-64 only | `conda create -n gars-bio --file gars-bio.conda.txt` |
| `gars-bio.lock.txt` | gars-bio **pip** layer (133 pkgs): `clawbio` and its tree, plus `scanpy`/`leidenalg` for sub-stage 02.02 | `conda run -n gars-bio pip install -r gars-bio.lock.txt` |
| `gars-nxf.conda.txt` | gars-nxf entirely (27 pkgs) | `conda create -n gars-nxf --file gars-nxf.conda.txt` |

`gars-bio` needs both of its files, conda layer first, because clawbio came from pip while
apptainer and squashfuse came from conda.

Regenerate after any change:
```bash
conda run -n gars-bio pip freeze         > _references/gars-bio.lock.txt
conda list -n gars-bio --explicit        > _references/gars-bio.conda.txt
conda list -n gars-nxf --explicit        > _references/gars-nxf.conda.txt
```

Key pinned versions: `clawbio==0.6.1`, `scikit-learn==1.9.0`, `pydeseq2==0.5.4`,
`pandas==3.0.5`, `numpy==2.5.2`, `matplotlib==3.11.1`, `scipy==1.18.0`,
`nextflow=26.04.6`, `apptainer=1.5.3`, `squashfuse=0.6.2`, `openjdk=17.0.7`.

## Verification

All checked 2026-08-11, exit 0:

| Check | Result |
|---|---|
| `$BIO/bin/python nfcore_rnaseq_wrapper.py --help` | usage printed |
| `$BIO/bin/python rnaseq_de.py --help` | usage printed |
| `$NXF/bin/nextflow -version` | 26.04.6 build 12646, on openjdk 17.0.7 |
| `$BIO/bin/apptainer --version` | 1.5.3 |
| `apptainer pull docker://busybox` | SIF built |
| `apptainer exec busybox.sif echo ...` | ran; mounts directly once squashfuse is on `PATH` |

```bash
PY=~/install/miniconda_clean/envs/gars-bio/bin/python
SKILLS=$($PY -c "import clawbio, pathlib; print(pathlib.Path(clawbio.__file__).parent / 'skills')")
cd $SKILLS/nfcore-rnaseq-wrapper && $PY nfcore_rnaseq_wrapper.py --help
cd $SKILLS/rnaseq-de             && $PY rnaseq_de.py --help
```

The container runtime is genuinely usable unprivileged here: `starter-suid` is **not** setuid
(`-rwxrwxr-x`), `max_user_namespaces` is 1542271, and the site bind config is two lines, so a
user-owned Apptainer has no privilege disadvantage. The wrapper supports `apptainer` as a
first-class backend (`schemas.py`), and its preflight prefers the `apptainer` binary over
`singularity` when `--profile apptainer` is set.

Note the skills declare their own version as 0.1.0 while `clawbio` is 0.6.1; the `common` API
they depend on is unchanged across that gap, confirmed by the two commands above. Re-run them
after any `clawbio` upgrade — an API drift would surface there first.

**Use the interpreter path, not `conda run`, when you need the output.** `conda run` buffers and
can swallow a skill's stdout entirely, which looks like a silent failure.

## Remaining unknowns

- No end-to-end pipeline execution has been attempted. `--help` proves imports resolve, not that
  a real nf-core run succeeds on this cluster.
- Nextflow and Singularity were confirmed available as modules but never exercised together on
  a compute node.
- A sub-stage that hits a missing dependency reports it as a preconditions failure and stops. It
  never pip-installs on the fly and never works around a missing module.
