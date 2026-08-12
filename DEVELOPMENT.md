# GARS — Development Log

Living record of what has been built, why, what state it is in, and what comes next.

**How to maintain this.** Update the *Current Status* and *Next Steps* sections whenever work
stops or a run changes state. Append to *Decision Log* only when something is decided or
learned — not for routine progress. Every entry states the reasoning, because the reasoning is
the part that gets lost and then reversed by someone who sees a simpler-looking option.

---

## Current Status

**As of 2026-08-12, 17:00 UTC**

| Component | State |
|---|---|
| Template | **v0.1.0**, tagged and pushed |
| Stage contracts 00, 01, 02 (+ 2 sub-stages) | Written, revised through live execution |
| Stage 03 (`03_custom_analysis`) | **Not written** |
| Environments (`gars-bio`, `gars-nxf`) | Installed, verified, locked |
| Ensembl GRCh38 r116 reference | Downloaded, integrity-verified |
| Derived-index cache | Empty; this run populates it via `--save-reference` |
| Test project `test-TALL` | Rebuilt from v0.1.0; stages 00 and 01 complete |
| nf-core/rnaseq run | **Job 26341149 RUNNING** since 16:45 UTC on `cpu_long` |

### What is proven

- Stages 00 → 01 produce correct artifacts from real data (38 samples registered, 10 analysed)
- Sample exclusion via `samples.csv` works; raw data and `files.csv` left intact
- Wrapper preflight passes on a compute node
- Nextflow dispatches per-task Slurm child jobs to the configured partition
- All 10 samples align and quantify; complete count matrices were written in an earlier run
- Samplesheet grain is correct — nf-core merges 2 lanes/sample into 10 `CAT_FASTQ` processes
- **Skills resolve from the installed `clawbio`** — a workspace copied from the repo carries no
  skill code, and preflight ran from site-packages
- **`work/` lives on scratch** — 95 GB accumulated there within 10 minutes, outside the project

### What is not yet proven

- `SUBREAD_FEATURECOUNTS` has never passed. Every configuration so far failed at or before it.
- Sub-stage 02.02 (differential expression) has never run.
- No run has produced `result.json` + `manifest.json`, so 02.01 has never reached `COMPLETE`.
- The derived-index cache has never been populated or reused.

### Cluster note

A node-failure event on 2026-08-12 (1,035 `NODE_FAIL` in 24h, peaking at 146 per 2h) filled the
queues with requeued casualties and delayed two submissions by hours. Recovered by ~16:45 UTC;
job 26341149 started within a minute of submission. Preemption is **not** enabled on this
cluster (`PreemptMode = OFF`) — every infrastructure failure encountered was hardware.

---

## Next Steps

Priority order.

1. **Let job 26341149 finish.** Watch `SUBREAD_FEATURECOUNTS` — the only step never passed.
2. **Harvest the derived indices.** On success, copy `run/results/genome/` (STAR index, Salmon
   index, transcripts FASTA, gene BED) into
   `refs/ensembl-GRCh38-116/derived/nf-core-rnaseq-3.26.0/`, then drop `--save-reference` and
   pass `--star-index` / `--salmon-index` / `--transcript-fasta` on later runs. Saves ~43 GB and
   about an hour per run. Verify `versionGenome` in `genomeParameters.txt` before first reuse.
3. **Delete the scratch work dir** once the run succeeds and `results/` is verified —
   `/gpfs/scratch/rodrij92/gars-work/test-TALL-rnaseq_bulk`, expected 250-350 GB.
4. **Complete sub-stage 02.02 (DE).** Requires 02.01 to reach `COMPLETE`. Note the test design
   is degenerate: all 10 samples are `condition=WT`, so the only two-level factor is `group`,
   and `group,G2,G1` will produce statistical noise. Fine for proving the chain, meaningless
   biologically.
5. **Implement artifact reuse across sub-stages.** Design settled 2026-08-12 (see Decision Log);
   deferred until 02.02 has run, so it is validated against a real second consumer rather than a
   hypothetical one — the same reasoning that defers stage 03.

6. **Write the `03_custom_analysis` contract.** Deliberately deferred until 02 produces real
   output — designing against an unproven handoff is what caused the samplesheet-grain mistake.

**Completed 2026-08-12:** repo/working-copy drift resolved (repo is canonical, `bioinfo-research-system/gars/` retired); skills de-vendored and resolved from the installed
`clawbio`; template version stamping added with `_references/VERSION`; `work/` moved to scratch;
derived-reference caching designed and keyed by pipeline version.

---

## Decision Log

### Storage and reference reuse — added 2026-08-12

Four failed runs consumed **612 GB**. Accounting for one 10-sample run:

| Item | Size |
|---|---|
| STAR index, Salmon index, transcripts FASTA, decompressed genome | ~46 GB, **rebuilt every run** |
| Merged (`CAT_FASTQ`) + trimmed FASTQs | ~56 GB |
| Genome / transcriptome / sorted / markdup BAMs | ~17 GB per sample |

Two structural causes:

1. **`work/` never cleans up.** Nextflow keeps every process output so `-resume` can reuse it,
   so the trimmed FASTQ, unsorted BAM, sorted BAM and deduplicated BAM all coexist. It also
   defaulted to `<output>/upstream/work` — *inside the project*.
2. **Derived references are discarded.** `save_reference = false` means the STAR/Salmon indices
   are built into `work/` and never published, so they are regenerated on every run and deleted
   with it. Three runs rebuilt them: ~130 GB of pure repetition.

Note the raw FASTQs are **not** duplicated — GARS symlinks them and Nextflow's default
`stageInMode` is also symlink. `results/` is safe to keep alone because
`publish_dir_mode = 'copy'` gives it real files, not pointers into `work/`.

Fixes applied to the config schema and the 02.01 contract:

- **`compute.work_dir`** — required, on scratch, never inside the project.
- **`reference.derived_dir`** — optional cache of built indices. Populate it once via
  `--save-reference`, reuse thereafter.
- **The cache is keyed by pipeline version** (`derived/nf-core-rnaseq-3.26.0/`), because a STAR
  index built by a different STAR version is rejected outright. Keying by genome build alone
  recreates the exact trap that killed run 26310826.
- 02.01 must read `versionGenome` from `genomeParameters.txt` before reusing a cached index.

### Artifact reuse across sub-stages — survey and design, 2026-08-12

**Question:** do different sub-stages and skills consume the same processed data (trimmed FASTQ,
BAM, counts), and can GARS recycle it instead of reprocessing?

**Method.** All 96 installed ClawBio skills, checked three ways. Frontmatter alone is not
trustworthy: only 53 of 96 declare `inputs`/`outputs`, and those undercount badly — exactly one
skill declares BAM input. So argparse flags were parsed from every script (83 skills) and the
`Input Formats` tables read from each SKILL.md.

**There is no machine-readable type system to build on.** 56 of 83 skills take a generic
`--input` and infer the type. Any typing must come from GARS.

**Finding 1 — the catalogue is mostly not NGS preprocessing.** Of 96 skills only ~17 touch NGS
data, and just three consume FASTQ: the nfcore-rnaseq, nfcore-sarek and nfcore-scrnaseq
wrappers. The other ~79 operate on already-derived data. The opportunity is therefore
**derived-artifact fan-out**, not raw-data reprocessing.

**Finding 2 — where consumers actually converge:**

| Artifact | Direct consumers | Size | Value |
|---|---|---|---|
| VCF | 10 | MB | highest |
| Count matrix | ~8 | MB | highest |
| FASTQ samplesheet | 4 | KB | high |
| h5ad | 4 | GB | medium |
| BAM | **~0 directly** | 17 GB/sample | see below |

Most-depended-on skills by in-degree: `scrna-orchestrator` (5), `diff-visualizer` (4),
`rnaseq-de` (3) — all consuming tabular output, not alignments.

**Finding 3 — almost nothing consumes BAMs directly.** The only real path is nf-core/rnaseq's
`--skip-alignment` with a `samplesheet_with_bams.csv`, which re-quantifies against a different
annotation without re-aligning. That samplesheet is produced **only** when the original run used
`--save-align-intermeds`.

**Decision: `--save-align-intermeds` was declined** (2026-08-12). Consequence, recorded
deliberately: BAMs from run 26341149 cannot be re-quantified, so changing annotation means a
full rerun. Revisit if re-quantification becomes routine.

**Design, to implement after 02.02.** One new file per sub-stage, one controlled vocabulary. No
database, no daemon, no copying.

1. `_references/artifact_types.md` — a closed vocabulary: `samplesheet`, `design`,
   `counts_gene`, `counts_transcript`, `bam_genome`, `bam_transcriptome`, `vcf`, `h5ad`,
   `qc_multiqc`. Nothing outside it may be declared.
2. Each sub-stage writes `OUTPUTS.tsv` beside its `STATUS`: `<type>\t<path>`, **paths only,
   never copies**. This mirrors the existing STATUS convention rather than adding a mechanism.
3. The assay map gains `Consumes` / `Produces` columns, so stage 02's router can verify required
   artifacts exist before dispatching — reusing the gate pattern it already applies to STATUS.
4. Resolution rule, stated once in `02_bioinformatics/CONTEXT.md`: a sub-stage needing type T
   searches completed sub-stages' `OUTPUTS.tsv` in reverse order, takes the first match, and
   records the supplying sub-stage in `HISTORY.md`. If none exists it **stops and reports** —
   never regenerates silently, because silent regeneration is how a project ends up with two
   count matrices that disagree.

**Explicitly rejected:**

- *Cross-project artifact sharing* — one project's provenance would depend on another's
  lifecycle. The reference cache is safe only because references are immutable and version-keyed;
  sample data is neither.
- *A content-addressed store* — Nextflow already does this inside `work/`; duplicating it adds
  hashing and garbage collection for no gain.
- *Automatic copying of artifacts* — paths and symlinks only, or the 612 GB problem returns.



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

### Housekeeping

Failed-run artifacts from 2026-08-12 (612 GB across four runs) were deleted. `work/` now lives
on scratch at `/gpfs/scratch/rodrij92/gars-work/<project>-<assay>` and is disposable once a run
succeeds, because `results/` is published with `publish_dir_mode = 'copy'`.

