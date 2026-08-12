# GARS — Development Log

Living record of what has been built, why, what state it is in, and what comes next.

**How to maintain this.** Update the *Current Status* and *Next Steps* sections whenever work
stops or a run changes state. Append to *Decision Log* only when something is decided or
learned — not for routine progress. Every entry states the reasoning, because the reasoning is
the part that gets lost and then reversed by someone who sees a simpler-looking option.

---

## Current Status

**As of 2026-08-12, 16:00 UTC**

| Component | State |
|---|---|
| Stage contracts 00, 01, 02 (+ 2 sub-stages) | Written, revised through live execution |
| Stage 03 (`03_custom_analysis`) | **Not written** |
| Environment (`gars-bio`, `gars-nxf`) | Installed, verified, locked |
| Ensembl GRCh38 r116 reference | Downloaded, integrity-verified |
| Test project `test-TALL` (10 samples) | Stages 00 and 01 complete |
| nf-core/rnaseq run | **Job 26336180 queued since 12:14 UTC — not started** |
| Portfolio repo | Published, private |

### What is proven

- Stages 00 → 01 produce correct artifacts from real data (38 samples, subset to 10)
- Sample exclusion via `samples.csv` works, leaving raw data intact
- Wrapper preflight passes on a compute node
- Nextflow dispatches per-task Slurm child jobs to the configured partition
- All 10 samples align and quantify; complete count matrices were written in an earlier run
- The samplesheet grain is correct — nf-core merged 2 lanes/sample into 10 `CAT_FASTQ` processes

### What is not yet proven

- `SUBREAD_FEATURECOUNTS` has never passed. Every configuration failed at or before it.
- Sub-stage 02.02 (differential expression) has never run.
- No run has produced `result.json` + `manifest.json`, so 02.01 has never reached `COMPLETE`.

### Current blocker — external

A cluster-wide node-failure event: **1,035 `NODE_FAIL` jobs in 24h**, peaking at 146 in a
two-hour window. Queues filled with requeued casualties (861 `REQUEUE_HOLD` on `cpu_long`).

**Recovering as of 15:57 UTC** — node failures down to 25 per 2h and `REQUEUE_HOLD` down to 172,
but the released backlog pushed `cpu_long` PENDING from 332 to 744. Job 26336180 has been queued
since 12:14 UTC (~3h45m) behind that backlog.

Nothing in our configuration is at fault. No action available beyond waiting; worth raising the
node-failure rate with cluster admins.

---

## Next Steps

Priority order.

1. **Wait for cluster recovery, then let job 26336180 run.** Configuration is fully validated;
   it needs a slot. Watch `SUBREAD_FEATURECOUNTS` — the only untested step.
2. **Report the node failures to HPC admins.** Also blocking ~21 unrelated GPU jobs.
3. **Complete sub-stage 02.02 (DE).** Requires 02.01 to reach `COMPLETE`. Note the test design
   is degenerate: all 10 samples are `condition=WT`, so the only two-level factor is `group`,
   and `group,G2,G1` will produce statistical noise. Fine for proving the chain, meaningless
   biologically.
4. **Write the `03_custom_analysis` contract.** Deliberately deferred until 02 produces real
   output — designing against an unproven handoff is what caused the samplesheet-grain mistake.
5. **Resolve repo/working-copy drift.** Canonical development happens in
   `bioinfo-research-system/gars/`; the published repo at `PROJECTS/gars/` is a snapshot copied
   by hand. **Drift is already real** — within two hours of publishing, the 02.01 contract was
   1,145 bytes ahead in the working copy (the STAR-index and biotype rules were missing from the
   repo).

   Suggested resolution: **make the repo canonical.** The architecture already assumes the
   template is copied *from* a stable location, git history becomes the per-change development
   record, and `bioinfo-research-system/` cannot itself be the repo because it holds `archive/`
   and real sample data. Retire `bioinfo-research-system/gars/`; recreate `gars-test/` from the
   repo when needed.

6. **Stop vendoring `tools/skills/`; point the contracts at the installed `clawbio`.**
   Verified 2026-08-12: the vendored skills and those shipped in `clawbio==0.6.1` are
   **byte-identical in every source file** (only `__pycache__` differs), and the installed copy
   runs standalone. So this is a pure path change with no behavioural risk.

   Why it matters: the README already claims GARS orchestrates skills rather than vendoring
   them — true of the repo, false of the workspace. A workspace copied from the repo has no
   `tools/skills/` at all, so the contracts currently reference a path that will not exist.
   Two hand-synced copies of the same code will also drift, and the vendored one carries no
   version marker.

   Resolve the path at runtime rather than hardcoding it, so it survives a Python upgrade or
   env relocation:
   ```bash
   SKILLS=$($BIO/bin/python -c "import clawbio, pathlib; print(pathlib.Path(clawbio.__file__).parent / 'skills')")
   ```
   Consequence to accept: skills then move with `clawbio` upgrades, which makes
   `clawbio==0.6.1` in `gars-bio.lock.txt` load-bearing rather than informational. That is the
   correct trade — an upgrade becomes a deliberate, recorded act.

   **Sequencing:** do this only after the current run finishes. Job 26336180's `submit.sh`
   references `gars-test/tools/skills/`, and changing paths under a queued job invites a
   confusing overnight failure. Afterwards, recreating `gars-test/` from the repo doubles as a
   clean end-to-end verification.

---

## Decision Log

Chronological. Each entry: what was decided, and why.

### Architecture

**Layered context (L0–L4).** `CLAUDE.md` orientation, `CONTEXT.md` routing, stage contracts
loaded per task, config and references loaded selectively. An agent should never hold the whole
system in context.

**Exclusive stage ownership, encoded in directory names.** A project directory named `NN_*` is
written by stage `NN_*` and no other. `01_data/` was renamed `00_data/` because stage 00 creates
it — the number must identify the producer, otherwise the ownership rule is decorative.
`CONTEXT.md`, `HISTORY.md`, `_config/` carry no prefix: project metadata, not stage artifacts.
`HISTORY.md` is the one documented exception every stage appends to.

**Assay IDs lost their numeric prefix** (`01_rnaseq_bulk` → `rnaseq_bulk`) so `NN_` has exactly
one meaning per level: stage number at project level, sub-stage order within a stage.

### Agent control — the central finding

**Positive instructions do not constrain an LLM agent.** The first live test had both
"do not improvise steps it does not specify" at workspace level and an explicit failure branch
in the stage contract. Given a path with no FASTQs, the agent searched subdirectories, read a
colleague's `settings.txt` and sample sheets, and volunteered an analysis of an unrelated
experiment. Both instructions were present. Both were ignored.

Three fixes, all now standard in every contract:

1. **Scope Boundaries** — stated negatively, naming the forbidden action literally
   ("do not read sample sheets, settings files, QC reports, or pipeline outputs found there").
2. **Response Format** — fixed templates `T1…Tn`; nothing else may be sent. Free-form replies
   varied every run and buried decisions in prose.
3. **Process decomposition** — one action per numbered step, every failure branch its own step.
   The original step 7 was a 90-word sentence containing five conditionals; buried branches get
   skipped.

Codified as the seven-section **Stage Contract Standard** in `gars/CONTEXT.md`.

### Data model

**`metadata.csv` split into `files.csv` + `samples.csv`.** One file was carrying two grains.
Now: `files.csv` is machine-owned, one row per sample-lane; `samples.csv` is user-owned, one row
per sample. The user enters each experimental value once instead of once per file, and
"same sample, conflicting condition" becomes structurally impossible rather than a validation
rule. Rejected the alternative of a list-of-paths column — multi-value CSV cells cannot be
validated per-cell and nf-core cannot consume them.

**Subsetting by deletion, never by destruction.** Referential integrity is asymmetric: a sample
in `samples.csv` but not `files.csv` is an error; a sample in `files.csv` but not `samples.csv`
is a deliberate **exclusion**, confirmed via template T7. Raw symlinks and `files.csv` are left
untouched, so the choice is reversible. The earlier symmetric rule left the agent no legal way
to honour "analyse only these ten," so it deleted 112 symlinks and corrupted a machine-owned
file to satisfy the rule.

**Stage boundaries fall on human gates.** Stage 00 registers data; the user then fills in the
design; stage 01 validates it. Modelling that pause as a stage boundary rather than a wait
inside one stage makes resumability legible from the directory tree. Validation splits on the
same line: file-level checks in 00 (where files are touched), design-level checks in 01 (the
design does not exist until the user writes it).

**`01_ingest_data` renamed `01_prepare_samplesheets`** with its own output directory
`01_samplesheets/`. Stage 00 does the ingestion when it symlinks, so the old name described the
wrong stage.

**Scientific parameters are never defaulted.** No stage substitutes a value for `reference`,
`de.formula`, or `de.contrast`. A wrong contrast yields a confident wrong answer rather than an
error, so a missing key stops the stage and asks.

### Environment

**Skills are installed, not vendored.** `clawbio` was missing entirely — both skill copies
import `clawbio.common.*` and could not even print `--help`. Installed from PyPI (0.6.1,
provenance verified against the repo URL in each SKILL.md) rather than vendored, because it
carries a real dependency tree (`opentelemetry`) and the wheel bundles duplicate copies of the
same skills.

**Two conda environments.** `nextflow` and `clawbio` cannot be solved together — conflicting
`c-ares` constraints via curl/libnghttp2. They are different runtimes and the wrapper calls
`nextflow` as a subprocess, so separation costs nothing.

**User-owned stack, not Lmod modules.** Apptainer 1.5.3 and Nextflow 26.04.6 are both *newer*
than the site modules and under our control. Verified the site's Singularity is not setuid and
user namespaces are enabled, so a user-owned rootless runtime has no privilege disadvantage.
`squashfuse` is required — without it Apptainer unpacks every multi-GB image on each container
launch.

**Always pin conda versions.** An unpinned `conda install nextflow` silently resolved to
**nextflow 0.24.2 (2017)** with openjdk 8, rather than reporting the conflict. It failed later
with opaque Maven TLS errors.

### Execution — failures and fixes

Each of these was found by running, not by reading.

| # | Failure | Cause | Fix |
|---|---|---|---|
| 1 | Pipeline fetch failed | GitHub REST API rate limit (60/hr, shared site IP) | Clone via git protocol; `--pipeline-local` |
| 2 | Valid checkout rejected as version `master` | **Upstream bug**: `_MANIFEST_VERSION_RE` lookbehind `(?<![A-Za-z])` fails to exclude `custom_config_version` | `--allow-pipeline-version-override` after verifying `git describe --tags`; reported as [ClawBio#333](https://github.com/ClawBio/ClawBio/issues/333) |
| 3 | Task killed mid-run | `NODE_FAIL`; Nextflow dispatched child jobs to an unintended partition | `_config/nextflow.slurm.config` setting `process.queue` + `maxRetries=3` |
| 4 | Resume rejected | Guard keyed on a Nextflow session; wrapper requires `reproducibility/manifest.json`, written only on success | Guard branches on manifest; a crashed run cannot be resumed and must exit clearly |
| 5 | `SUBREAD_FEATURECOUNTS` failed after counts were written | iGenomes GRCh38 is **NCBI** and has no biotype attribute | Ensembl GRCh38 r116, which provides `gene_biotype` |
| 5b | STAR rejected the index | Prebuilt site index built with STAR 2.7.1a; nf-core runs 2.7.11b | Let nf-core build the index; never reuse one without checking its version |

**Contract defects found the same way:** preflight and the real run pointed at the same output
directory (wrapper rejects a populated `--output`); no verification that samplesheet absolute
paths still resolve after a project move.

**Preemption was a red herring.** A "preemption ratio" was used to choose partitions before
checking `scontrol show config` — which reports `PreemptMode = OFF`. Preemption is not enabled
on this cluster; every infrastructure failure was hardware. The metric accidentally correlated
with node-failure rate, which is why the partition switch still helped.

---

## Quick Reference

### Environments
```bash
BIO=~/install/miniconda_clean/envs/gars-bio    # clawbio, scikit-learn, pydeseq2, apptainer, squashfuse
NXF=~/install/miniconda_clean/envs/gars-nxf    # nextflow 26.04.6, openjdk 17
export PATH="$NXF/bin:$BIO/bin:$PATH"
export APPTAINER_CACHEDIR=~/.apptainer_cache
export NXF_APPTAINER_CACHEDIR=~/.apptainer_cache
```
Never pipe `module load` — it runs in a subshell and silently discards the `PATH` change.
Invoke skills by interpreter path, not `conda run`, which can swallow output entirely.

### Key locations
| Path | Contents |
|---|---|
| `bioinfo-research-system/gars/` | canonical workspace template (development happens here) |
| `bioinfo-research-system/gars-test/` | live test workspace + `test-TALL` project |
| `PROJECTS/gars/` | published portfolio repo (snapshot) |
| `~/install/nf-core-pipelines/rnaseq-3.26.0` | pinned pipeline checkout |
| `~/install/refs/ensembl-GRCh38-116/` | reference FASTA + GTF |

### Checking a run
```bash
S=.../02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper
cat $S/STATUS                          # authority on sub-stage state
squeue -j <id>; sacct -j <id>
grep '\[guard\]' $S/*.out              # clean start vs resume vs crashed
tail $S/run/logs/stdout.txt
```

### Preserved failed runs
`run.failed-biotype-26296448` holds valid count matrices from the iGenomes attempt — usable for
comparing NCBI vs Ensembl quantification.
