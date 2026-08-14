# Sub-stage 02.01: nf-core/rnaseq Wrapper

## Purpose
Run upstream bulk RNA-seq preprocessing — FASTQ to gene count matrix — by submitting the
`nfcore-rnaseq-wrapper` skill to Slurm. This sub-stage submits the job and returns; it does not
wait for completion. A later invocation reads the STATUS file and collects results.

## Inputs
1. **`01_samplesheets/rnaseq_bulk_samplesheet.csv`** — written by stage 01
2. **`_config/rnaseq_bulk.yaml`** — reference genome, aligner, and compute settings
3. **The `nfcore-rnaseq-wrapper` skill** — shipped by the installed `clawbio` package, read-only

## Scope Boundaries
This sub-stage performs the steps in Process and nothing else.

- Never edit, patch, monkey-patch, or work around the skill's code. If it errors, report the
  error verbatim and stop.
- **Never substitute a hand-written pipeline.** If the skill cannot run, do not call `nextflow`
  directly, do not run STAR/Salmon by hand, and do not "approximate" the result. Report and stop.
- Never modify the samplesheet, `_design.csv`, `00_data/`, or anything under `01_samplesheets/`.
- Never run the pipeline in the foreground, and never poll for it in a loop. Submit, write
  STATUS, and return.
- Never resubmit a job whose STATUS is `SUBMITTED` or `RUNNING`.
- Never delete or overwrite an existing non-empty output directory. The skill rejects one
  (`OUTPUT_DIR_NOT_EMPTY`); surface that rather than clearing the directory.
- Do not interpret the biology. Report counts, paths, and QC file locations only.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Definitions

**Skill invocation.** `python nfcore_rnaseq_wrapper.py`, run from inside
`$SKILLS/nfcore-rnaseq-wrapper/` (see Definitions in `02_bioinformatics/CONTEXT.md` for how to
resolve `$SKILLS`). There is no `clawbio.py` launcher in this environment —
the CLI shown in the skill's own SKILL.md (`python clawbio.py run rnaseq-pipeline …`) is the
upstream ClawBio form and does not apply here. Flag names are otherwise identical.

**Required environment.** Entirely user-owned conda; **no `module load`**. Two environments,
because nextflow and clawbio cannot coexist in one — see `_references/environment.md`.

```bash
BIO=~/install/miniconda_clean/envs/gars-bio    # skill deps + apptainer + squashfuse
NXF=~/install/miniconda_clean/envs/gars-nxf    # nextflow 26.04.6 + openjdk 17
export PATH="$NXF/bin:$BIO/bin:$PATH"
export APPTAINER_CACHEDIR=~/.apptainer_cache
export NXF_APPTAINER_CACHEDIR=~/.apptainer_cache
```

Every invocation, including preflight and the Slurm script, must export all of the above.
`squashfuse` must be on `PATH` or Apptainer unpacks each multi-GB image on every container
launch. `NXF_APPTAINER_CACHEDIR` must be set or every run re-pulls the same images.

Invoke the skill as `$BIO/bin/python nfcore_rnaseq_wrapper.py`, never via `conda run` — the
latter buffers and can swallow the skill's output entirely, which reads as a silent crash.

**Container backend.** Always pass `--profile apptainer`. The wrapper supports it as a
first-class backend and its preflight then prefers the `apptainer` binary over `singularity`.

**Pipeline source: always local, never remote.** Pass
`--pipeline-local ~/install/nf-core-pipelines/rnaseq-3.26.0`. Nextflow resolves a remote
`nf-core/rnaseq` through the GitHub REST API, which is capped at 60 requests/hour for
unauthenticated clients and shared across this cluster's outbound IP — it fails with
`API rate limit exceeded` and no pipeline is fetched. The local checkout was cloned over the
git protocol, which is not subject to that cap. Refresh it with `git -C <dir> fetch --tags`.

**Version-override is mandatory with a local checkout, and is not a real override.** Add
`--allow-pipeline-version-override`. The wrapper's `_MANIFEST_VERSION_RE` uses a `(?<![A-Za-z])`
lookbehind that fails to exclude `custom_config_version` (the preceding character is `_`, not a
letter), so it reads `master` from `nextflow.config` instead of the manifest's real
`version = '3.26.0'`. Validations stay pinned to 3.26.0 either way. **Before adding the flag,
verify the checkout independently** — `git describe --tags` must report the pinned version. Only
then is the check known to be misfiring rather than correct.

**Task dispatch: set the queue explicitly.** Nextflow detects Slurm on its own and submits each
process as a **child job**. The parent job's `--partition` governs only the wrapper process, not
the ~50 tasks it spawns — left unset, Nextflow dispatched them to `cpu_short`, the most
contended partition on this cluster. Always pass
`--nextflow-config <project>/_config/nextflow.slurm.config`, which sets `process.queue` and
raises `maxRetries`. That config must contain **no `params` block** in any form; the wrapper
rejects such configs so its audited parameter surface cannot be bypassed. Executor and process
settings are the permitted use.

**`--resume` cannot continue a crashed run.** The wrapper writes
`reproducibility/manifest.json` only on *successful* completion and rejects `--resume` without
it (`INVALID_RESUME_STATE`). Its `--resume` therefore replays a finished bundle; it is not a
crash-recovery mechanism. A crashed or preempted run cannot be continued — `run/` must be moved
aside and the pipeline restarted from zero. Container images and the pipeline checkout survive,
so a restart is faster than the first run, but every task re-executes.

**Requeue guard.** This cluster has `Requeue=1`; a preempted job restarts and re-runs
`submit.sh`, and the wrapper rejects a populated `--output` with `OUTPUT_DIR_NOT_EMPTY`. So
`submit.sh` must branch on `reproducibility/manifest.json` — **not** on the presence of a
Nextflow session, which is the wrong signal and fails as above:

- manifest present -> add `--resume` (replay a completed run)
- `run/` populated, no manifest -> a previous run crashed: **exit non-zero with a clear message**
  rather than retrying into a guaranteed `INVALID_RESUME_STATE`
- `run/` empty or absent -> clean start

Slurm snapshots the batch script at submission, so editing `submit.sh` never affects an
already-queued job — cancel and resubmit instead.

**Declared requirements.** `_references/assay_stage_skill_map.md` lists what this skill needs (binaries and Python packages). Report a missing requirement by name — "scikit-learn missing, required by rnaseq-de" — not as a raw traceback.

**Skill importability.** Before preflight, confirm the skill imports:
`$BIO/bin/python nfcore_rnaseq_wrapper.py --help`. Verified 2026-08-11 with `clawbio==0.6.1`,
`nextflow=26.04.6`, `apptainer=1.5.3`. If it fails, that is a preconditions failure (T5):
report it and stop. Never vendor, stub, or reimplement a missing module, and never
pip-install or `conda install` on the fly — an unpinned install here already silently produced
a 2017 Nextflow once.

**Output directory.** `projects/<project_title>/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/run/`.
It must be **empty** before submission — the skill rejects a populated one with
`OUTPUT_DIR_NOT_EMPTY`. The skill also rejects an output directory inside its own source tree
(`PROJECT_ROOT`, which is `tools/`); a path under `projects/` is outside it and therefore valid.

**Preflight.** The same invocation with `--check` added: validates samplesheet, references,
runtime, and backend without launching Nextflow. It must pass before any job is submitted.

**Preflight writes output too.** `--check` populates its `--output` with `check_result.json`
and `reproducibility/samplesheet.valid.csv`. It must therefore be given its **own** directory,
`../preflight/`, never `run/` — pointing both at `run/` leaves it non-empty and the real
submission then fails `OUTPUT_DIR_NOT_EMPTY`. Discard `preflight/` freely; it is diagnostic
only. `run/` is created by the Slurm job and never by preflight.

**Absolute paths in the samplesheet.** Stage 01 writes absolute FASTQ paths, so a project that
is moved or renamed invalidates them. If any path in the samplesheet fails to resolve, that is
a preconditions failure (T5): re-run stage 01 to regenerate it. Never rewrite the samplesheet
here — stage 01 owns it.

**Config keys.** Read from `_config/rnaseq_bulk.yaml`:

| Key | Required | Maps to |
|---|---|---|
| `reference.genome` | one of these two | `--genome <value>` |
| `reference.fasta` + `reference.gtf` | one of these two | `--fasta <v> --gtf <v>` |
| `aligner` | no (default `star_salmon`) | `--aligner <value>` |
| `compute.partition`, `compute.time`, `compute.cpus`, `compute.mem` | yes | Slurm directives |
| `compute.work_dir` | yes | `--work-dir <value>/<project>-<assay>` |
| `reference.derived_dir` | no | `--star-index`, `--salmon-index`, `--transcript-fasta` from that directory |

`reference.genome` and `reference.fasta` are mutually exclusive — the skill rejects both.

**Never let `work/` default into the project.** Nextflow retains every process output in its
work directory so `-resume` can reuse it, so a single 10-sample run accumulates 250-350 GB of
intermediates there. Always pass `--work-dir` from `compute.work_dir`, on scratch. Because
`publish_dir_mode = 'copy'`, `results/` holds real files and `work/` may be deleted once the run
succeeds.

**Reuse derived references; never rebuild them per run.** nf-core builds the STAR index, Salmon
index and transcripts FASTA into `work/` and does not publish them (`save_reference = false`), so
they are regenerated every run — roughly 43 GB and an hour each time, and discarded with `work/`.

- If `reference.derived_dir` is set and populated, pass `--star-index`, `--salmon-index` and
  `--transcript-fasta` from it. Do not pass `--save-reference`.
- If it is set but empty, pass `--save-reference` so this run publishes them to
  `run/results/genome/`, then report their location so they can be harvested into the cache.
- **Before reusing a cached STAR index, verify the version that built it.** Read `versionGenome`
  from its `genomeParameters.txt`; STAR refuses an index built by an incompatible version. The
  cache path must be keyed by pipeline version for this reason.

**Reference annotation must carry a biotype attribute.** nf-core's `SUBREAD_FEATURECOUNTS` step
groups by `gene_biotype`. Ensembl GTFs provide it and are the native case. GENCODE names the
same field `gene_type`, so a GENCODE GTF additionally requires `--gencode` and
`--featurecounts-group-type gene_type`. The iGenomes `--genome GRCh38` annotation is **NCBI and
has no biotype attribute at all**: nf-core warns that biotype QC will be skipped, then runs it
anyway and the pipeline dies — after the count matrices have already been written, so the
failure looks late and unrelated. Prefer Ensembl.

**Never reuse a prebuilt aligner index without checking the tool version that built it.** A
STAR index records `versionGenome` in its `genomeParameters.txt`, and STAR refuses an index
built by an incompatible version (`Genome version 2.7.1a is INCOMPATIBLE with running STAR
version 2.7.11b`). Site-provided indices are frequently years older than the pipeline's
containerised aligner. Check before passing `--star-index`; when in doubt omit it and let
nf-core build one, which costs about an hour and is then reused from the work directory.

## Process
1. Reply T1.
2. Read `_config/rnaseq_bulk.yaml`. If it is missing, or names neither `reference.genome` nor
   `reference.fasta` + `reference.gtf`, reply T5 and stop. Never guess a reference genome.
3. Read the STATUS file. If it is `SUBMITTED`, `RUNNING`, or `COMPLETE`, stop — stage 02's
   router already handles those states and should not have routed here.
4. Verify every FASTQ path in the samplesheet resolves. If any does not, reply T5 and stop —
   the project has moved and stage 01 must regenerate the samplesheet.
5. Check that `run/` does not exist or is empty. If it is non-empty, reply T5 and stop; a
   previous run's output is never deleted automatically. Then run preflight: the skill
   invocation with `--check` and `--output <sub-stage dir>/preflight`, under the required
   environment, with `--input <samplesheet>` and the reference flags from config. Capture
   stdout and stderr to `logs/preflight.log`.
6. If preflight fails, write `STATUS` as `FAILED <iso8601> <error_code>`, reply T4 with the
   skill's verbatim error, and stop. Do not attempt to fix the cause.
7. If preflight passes, write a Slurm batch script `submit.sh` in the sub-stage output directory
   containing the full environment exports from Definitions, the skill invocation without
   `--check` but with `--profile apptainer`, and `--timeout-hours 0` so the wrapper's 12-hour
   internal cap does not pre-empt the Slurm walltime. Use the `compute.*` config values for the
   Slurm directives. The script must be re-runnable standalone — it carries its own environment
   and never assumes an interactive shell's state.
8. Submit it with `sbatch`. Capture the job ID.
9. Write `STATUS` as `SUBMITTED <job_id> <iso8601>`.
10. Reply T2 and stop. Do not wait, poll, or sleep.
11. **On a later invocation** where STATUS is `SUBMITTED` or `RUNNING`: query `sacct`/`squeue`
    for the job. If still active, update STATUS to `RUNNING <job_id> <iso8601>`, reply T3, stop.
12. If the job finished, read the skill's `result.json` from the output directory. Confirm it
    reports a merged count matrix (`preferred_counts_tsv`). If it does not — for example an
    alignment-only run — write `FAILED`, reply T4, and stop; the next sub-stage cannot proceed
    without counts.
13. Run the exit gate: `report.md`, `result.json`, and the counts TSV all exist and are
    non-empty; the sample count in the counts matrix equals the distinct `sample` count in the
    samplesheet. If any check fails, write `FAILED`, reply T4, stop.
14. **Populate the derived-reference cache, automatically.** If `reference.derived_dir` is set
    and does not already contain a populated `star/`, publish this run's built references into
    it. No approval is required: the contents are a deterministic function of the FASTA, GTF and
    pipeline version, and nothing about them is project-specific.

    Publish **atomically** — the cache is shared across projects and two runs may finish at
    once. Write to a sibling temporary directory on the same filesystem, then `mv` it into
    place. Never write directly into the cache path, and never overwrite a populated cache; if
    one already exists, leave it and record that it was reused.

    Copy `run/upstream/results/genome/`: the STAR index, Salmon index, `genome.transcripts.fa`,
    the filtered GTF and the gene BED. Then write a `PROVENANCE` file recording the source FASTA
    and GTF paths, the pipeline version, the STAR `versionGenome`, and the job ID that built it.

15. Write `OUTPUTS.tsv` declaring the artifacts produced, using the closed vocabulary in
    `_references/artifact_types.md`. All rows are `native`; paths are relative to this sub-stage
    directory. At minimum: `counts_gene`, `counts_transcript`, `tpm_gene`, `bam_genome`,
    `qc_multiqc`. Resolve `counts_gene` from `result.json`'s `preferred_counts_tsv` rather than
    guessing a filename.
16. Write `STATUS` as `COMPLETE <iso8601>`, append a dated entry to the project's `HISTORY.md`
    noting whether the cache was populated or reused, and reply T6.

## Response Format
Every message you send in this sub-stage is one of the templates below, with placeholders
filled. Add nothing else: no observations, no suggestions, no biological interpretation.

**T1 — Start**
```
Sub-stage 02.01: nf-core/rnaseq wrapper.
Assay: rnaseq_bulk
Samplesheet: 01_samplesheets/rnaseq_bulk_samplesheet.csv (<n> rows, <n> samples)
Reference: <genome or fasta+gtf>
Aligner: <aligner>
```

**T2 — Submitted**
```
Preflight passed. Submitted to Slurm as job <job_id>.

Output: 02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/run/
Status:  02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/STATUS

Check progress: squeue -j <job_id>
Run stage 02 again when it finishes to collect results.
```

**T3 — Still running**
```
Job <job_id> is <state>, submitted <timestamp>. Nothing was resubmitted.

Check progress: squeue -j <job_id>
```

**T4 — Failed**
```
Sub-stage 02.01 failed at <stage: preflight|run|exit gate>.

<verbatim skill error, including error_code and fix if present>

STATUS set to FAILED. Nothing was retried, nothing was deleted.
Log: 02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/logs/<log file>
```

**T5 — Preconditions not met**
```
Cannot start sub-stage 02.01.

| Requirement | Status |
|---|---|
| _config/rnaseq_bulk.yaml exists | Yes / No |
| Reference declared (genome, or fasta+gtf) | Yes / No |
| Output directory empty | Yes / No |

<what the user must provide>
```

**T6 — Complete**
```
Sub-stage 02.01 complete.

| Artifact | Path |
|---|---|
| Count matrix | <preferred_counts_tsv> |
| MultiQC report | <multiqc html> |
| Wrapper report | <report.md> |

Samples in matrix: <n>
Next: sub-stage 02_rnaseq-de.
```

# OUTPUT
Written to `projects/<project_title>/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/`:

| Artifact | Contents |
|---|---|
| `STATUS` | Sub-stage state. The authority on completion. |
| `submit.sh` | The exact Slurm script submitted, including module loads. Re-runnable by hand. |
| `logs/preflight.log` | Preflight stdout/stderr. |
| `preflight/` | Preflight's own output (`check_result.json`, validated samplesheet). Diagnostic only, safe to discard. Kept separate so `run/` stays empty for submission. |
| `OUTPUTS.tsv` | Artifacts produced, by type. How 02.02 finds the count matrix. |
| `run/` | The skill's own output tree: `report.md`, `result.json`, `upstream/results/`, `provenance/`, `reproducibility/`. |

The count matrix consumed by the next sub-stage is the `preferred_counts_tsv` named in
`run/result.json`. `00_data/` and `01_samplesheets/` are never modified.
