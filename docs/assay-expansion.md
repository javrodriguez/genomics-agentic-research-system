# Assay Expansion — Research Report

**Date:** 2026-08-12 · **Revised:** 2026-08-14

> Moved into the repo 2026-08-14 (previously `bioinfo-research-system/ASSAY_EXPANSION_RESEARCH.md`,
> untracked). Summarised in [DEVELOPMENT.md](../DEVELOPMENT.md); this is the full backing research.

**Question:** How should GARS gain support for assays beyond `rnaseq_bulk`? Specifically: should the
SNS (Seq-N-Slide) pipelines be integrated as skills, and can SNS be made portable enough to meet
GARS's quality standards?

**Answer, in one line:** Do not integrate SNS. Build **four** new nf-core wrapper skills
(`atacseq`, `chipseq`, `cutandrun`, `methylseq`) by cloning the wrapper pattern GARS already runs
three times over, and take WES/WGS from the existing `nfcore-sarek-wrapper`.

*(Corrected 2026-08-14: this line said "three" and omitted `cutandrun`, contradicting §6.1, which
records that the lab runs both classical ChIP-seq and CUT&RUN and that they must be separate
skills — they wrap different upstream pipelines and normalise differently.)*

**Paths as of this writing** — the GARS workspace was relocated on 2026-08-12 and is now a sibling
of this repo. Update these if the layout changes again:

| Thing | Absolute path |
|---|---|
| GARS workspace | `/gpfs/data/abl/home/rodrij92/PROJECTS/gars` |
| Test workspace | `/gpfs/data/abl/home/rodrij92/PROJECTS/bioinfo-research-system/gars-test` |
| Local iGenomes mirror | `/gpfs/data/sequence/references/iGenomes` **[verified 2026-08-14]** |
| Pinned pipeline checkouts | `~/install/nf-core-pipelines/` (currently `rnaseq-3.26.0` only) |
| Reference + derived indices | `~/install/refs/ensembl-GRCh38-116/` |
| SNS source | `/gpfs/data/abl/home/rodrij92/PROJECTS/bioinfo-research-system/archive/resources/sns/sns-main` |
| SNS docs (PDF) | `.../archive/resources/sns/SNS_documents/` |
| ClawBio skills | `~/install/miniconda_clean/envs/gars-bio/lib/python3.12/site-packages/clawbio/skills/` |

Every fact marked **[verified]** was checked on this cluster on 2026-08-12. Facts marked
**[unverified]** must be confirmed before implementation.

---

## 1. Executive summary

> **Revision note, 2026-08-14.** The document's central recommendation is unchanged and now
> better supported. Three things moved:
>
> - **The blocker is gone.** §6.2 item 0 — "prove one end-to-end nf-core run on this cluster" —
>   is done. `nf-core/rnaseq 3.26.0` completed on real data, and derived-index reuse was verified
>   separately. Six earlier attempts failed; every cause is now fixed in a contract (§2.3).
> - **Most reference prerequisites are resolved** (§6.5): a local iGenomes mirror exists, the
>   ATAC/ChIP blacklist is present, and the CUT&RUN spike-in genome is already on the cluster.
>   The one negative result: no human Bismark index exists, so methylseq must build its own.
> - **A new blocker appeared.** Skills were de-vendored on 2026-08-13, so `tools/skills/` — where
>   §6.3 places new wrappers — no longer exists, and `clawbio` is a third-party package we cannot
>   add to. GARS-authored wrappers currently have nowhere to live (§6.2a).
>
> Top of queue is now **Q2** (make stage 01 assay-aware) and **Q2b** (decide where wrappers live).
> Both touch existing contracts, so settle them before writing wrapper #1.


1. **ClawBio's coverage is inverted relative to SNS's value.** ClawBio already covers RNA-seq and the
   entire WES/WGS family — portably, in GARS's native skill pattern, often through the *identical*
   underlying tools. It has **nothing** for ATAC-seq, ChIP-seq, or bisulfite methylation. Those are
   exactly the assays that would motivate bringing SNS in.
2. **Therefore SNS's value collapses to 4–5 routes** (`atac`, `chip`, `chip-pairs-peaks`, `wgbs`,
   `rrbs`, plus `rna-snv`), not 14.
3. **Making SNS portable is feasible** — only ~145 lines of 13,113 are site-locked — but the
   mechanical edits are not the cost. The real costs are: no single environment can satisfy SNS's
   tool matrix (requires per-segment containers), runtime R package installation must be replaced,
   a reference bundle must be built, and you inherit a fork of someone else's scientific pipeline.
4. **For those same 4–5 assays, published nf-core pipelines already exist** — `atacseq`, `chipseq`,
   `cutandrun`, `methylseq` — maintained and portable by construction. GARS already has three
   working wrapper skills to clone, plus verified Nextflow + Apptainer.
5. **Recommendation:** build *wrapper skills* around those existing pipelines (no pipeline
   development — see §6.1). Keep SNS available as-is at NYU for comparability with historical
   results, but do not port it and do not wire it into GARS.

---

## 2. Constraints any integration must satisfy

Derived from `gars/CLAUDE.md`, `gars/CONTEXT.md`, `gars/02_bioinformatics/CONTEXT.md`, the two
sub-stage contracts, and `gars/_references/environment.md`.

### 2.1 The skill / contract split

| Object | Layer | Nature | Rule |
|---|---|---|---|
| Stage `CONTEXT.md` | L2 | prose contract | agent executes it literally; stops and asks rather than deviating |
| Sub-stage `CONTEXT.md` | L2 | prose contract | owns Process, Response Format, OUTPUT |
| Skill (installed with `clawbio`, resolved as `$GARS_SKILLS`) | code | deterministic CLI | **canonical, read-only**; agent may never edit, patch, or substitute it |

Stage 02 is a **pure router**: it resolves assay → ordered sub-stages from
`_references/assay_stage_skill_map.md`, checks each predecessor's `STATUS`, hands control to the
sub-stage contract, and runs nothing itself.

### 2.2 Non-negotiable standards

| Standard | Source |
|---|---|
| `STATUS` file is the sole authority on sub-stage state; never infer state from output files | 02/CONTEXT.md |
| Submit and return. Never run long jobs in foreground, never poll in a loop, never resubmit a `SUBMITTED`/`RUNNING` job | 02.01 |
| Never delete or overwrite a non-empty output directory | 02.01 |
| Preflight (`--check`) must pass before any submission | 02.01 |
| Structured errors: `stage`, `error_code`, `message`, `fix`, `details`; report verbatim and stop | skill contract |
| Never install packages on the fly (pip or conda); pin every version; keep lockfiles | environment.md |
| No Lmod modules — the whole stack is user-owned so an admin change cannot break a run | environment.md |
| Config is a user decision: never default `reference`, `de.formula`, `de.contrast` — "a wrong value there produces confident, wrong biology rather than an error" | CONTEXT.md |
| Stage owns its numbered directory exclusively | CONTEXT.md |
| Reproducibility bundle: `commands.sh`, `params.yaml`, `manifest.json`, checksums, `environment.yml`, provenance JSON | nfcore-rnaseq-wrapper |

### 2.3 Verified runtime **[verified]**

| Component | State |
|---|---|
| `gars-bio` conda env | clawbio 0.6.1, scikit-learn 1.9.0, pydeseq2 0.5.4, apptainer 1.5.3, squashfuse 0.6.2 |
| `gars-nxf` conda env | nextflow 26.04.6, openjdk 17.0.7 |
| Why two envs | nextflow and clawbio cannot co-solve (`c-ares` conflict) |
| Scheduler | Slurm |
| Containers | Apptainer, unprivileged, working (`starter-suid` not setuid, `max_user_namespaces` 1542271) |

~~**Known gap:** no end-to-end nf-core run has ever been executed on this cluster.~~
**CLOSED 2026-08-13 [verified].** `nf-core/rnaseq 3.26.0` completed on this cluster:
`Pipeline completed successfully`, 10 samples, 5h09m, 78,941 genes quantified, full QC suite. A
second 2-sample run then verified derived-index reuse with 0 index-building processes. Slurm
child-job dispatch, Apptainer, and the requeue guard are all exercised.

Six attempts failed before that one. The causes are worth knowing before building a new wrapper,
because each will recur:

| Failure | Cause | Fix now in the contract |
|---|---|---|
| Pipeline fetch | GitHub REST API rate limit (60/h, shared site IP) | `--pipeline-local`, cloned over git protocol |
| Version rejected | Wrapper's `_MANIFEST_VERSION_RE` matches `custom_config_version` | `--allow-pipeline-version-override` after verifying `git describe --tags`; [ClawBio#333](https://github.com/ClawBio/ClawBio/issues/333) |
| Task killed | Nextflow dispatched child jobs to an unintended partition | `_config/nextflow.slurm.config` setting `process.queue` |
| Resume rejected | Guard keyed on a Nextflow session; wrapper needs `reproducibility/manifest.json`, written only on success | Guard branches on the manifest; a crashed run cannot be resumed |
| `SUBREAD_FEATURECOUNTS` | iGenomes GRCh38 is **NCBI** and carries no biotype attribute | Ensembl reference, which provides `gene_biotype` |
| STAR rejected index | Site index built with STAR 2.7.1a; nf-core runs 2.7.11b | Never reuse a prebuilt index without checking `versionGenome` |

---

## 3. SNS anatomy **[verified]**

~13,113 lines of shell across routes/segments/scripts, plus Perl entry points and R analysis scripts.

### 3.1 Structure

| Layer | Count | Role |
|---|---|---|
| `gather-fastqs` (Perl) | 1 | FASTQ dir → `samples.fastq-raw.csv` |
| `generate-settings` (Perl) | 1 | genome name → `settings.txt` (`KEY\|value` format) |
| `run` (Perl) | 1 | dispatches one `sbatch` job **per sample** (or one total for `-groups-` routes) |
| `routes/*.sh` | 14 | serial orchestration of segments + nested `sbatch` fan-out |
| `segments/*.sh` | 38 | the actual work |
| `scripts/*` | 16 | helpers, R analysis |

### 3.2 Route classes

| Class | Routes | Sample sheet | Job model |
|---|---|---|---|
| Sample-centric | `rna-star`, `rna-salmon`, `rna-rsem`, `rna-snv`, `chip`, `atac`, `wes`, `wgbs`, `rrbs`, `species` | `samples.fastq-raw.csv` | one job per sample |
| Paired | `wes-pairs-snv`, `wes-pairs-cnv`, `chip-pairs-peaks` | `samples.pairs.csv` | one job per pair; consumes base-route BAMs |
| Grouped | `rna-star-groups-dge` | `samples.groups.csv` | one job total; consumes base-route counts |

Paired and grouped routes **must run from the same project directory** as their base route.

### 3.3 What SNS does well

SNS is already ICM-shaped, which is why wrapping it looked attractive:

- Segments do one thing, are idempotent (skip if output exists), and self-validate inputs and outputs.
- Communication between segments is plain-text CSV on disk (`samples.<segment>.csv`,
  `summary/<sample>.<segment>.csv`) — every intermediate is human-readable and editable.
- Re-running a route resumes: existing outputs are skipped, new samples are processed.
- Tool versions are pinned inline in module names (`star/2.7.3a`, `bowtie2/2.5.3`, `macs2/2.2.9`) —
  real provenance.
- `scripts/get-ref.sh` is **convention-based reference discovery** and contains nothing site-specific.

### 3.4 What SNS lacks relative to GARS standards

| Gap | Detail |
|---|---|
| **No preflight** | Failures surface per-sample, hours in, inside `logs-sbatch/`. Error detection is `grep "ERROR:" logs-sbatch/*`. |
| **No structured errors** | `echo -e "\n $script_name ERROR: ..." >&2` |
| **Runtime R installation** | `scripts/load-install-packages.R` installs from CRAN/Bioconductor into the user library at run time, unpinned |
| **Config mutation** | `settings.txt` is written *during* execution (`EXP-STRAND` inferred by `align-star`, `EXP-PEAKS-*`, `EXP-TARGETS-BED`) |
| **No single job identity** | N jobs per route + nested `sbatch` children — incompatible with GARS's single-`job_id` `STATUS` line |

Note the R package list in `load-install-packages.R` contains typos that silently fall through to
the "not available" branch: `GenomiFeatures`, `rtraklayer`, `owplot`, `vfR`, `pakage_name`.

---

## 4. SNS portability audit **[verified]**

### 4.1 Blocker surface — 145 lines of 13,113 (~1%)

| Class | Lines | Detail |
|---|---|---|
| `module add` / `module load` | 93 | 30 segments + routes |
| `module purge` | 47 | env-reset assumption; becomes harmful under a conda substrate |
| Hardcoded software paths | 22 | `/gpfs/data/igorlab/software/`, `/gpfs/share/apps/` |
| Hardcoded reference paths | 20 | `/gpfs/data/igorlab/ref/` |
| `@nyulangone.org` | 6 | `run:128` + 5 routes |
| Hardcoded Slurm partitions | 4 | `run` + routes |

Hardcoded software paths are **not** module-managed — they are hand-installed binaries: GATK 3.8-1
and 4.4.0.0 jars, FREEC 11.6, LoFreq 2.1.3.1, Strelka 2.9.10, Manta 1.5.0, HMMRATAC 1.2.10, ANNOVAR,
Salmon 1.6.0, `jq`, sambamba 1.0.1.

### 4.2 The reference layer is already portable

`scripts/get-ref.sh` discovers references by convention inside a genome directory. Only the *root* is
hardcoded, in `generate-settings:44` — and it already accepts an exact directory when the argument
contains `/`. **This is a one-line fix plus a documented bundle spec.**

Required bundle contents per genome:

```
<genome>/
  genome.fa  genome.dict  genes.gtf  chrom.sizes  genome.2bit
  refFlat.txt.gz  rRNA.interval_list  blacklist.bed  fastq_screen.conf
  star/   bismark/   rsem/ref   salmon/
  <bowtie2 basename>.1.bt2   <bwa basename>.fa.bwt
```

Genuinely unportable reference bits, all narrow: FREEC's genome-keyed auxiliary files, ANNOVAR
databases (**licensing** — cannot be redistributed), Centrifuge `nt` index (>100 GB), and one
Trimmomatic adapter FASTA (which ships with Trimmomatic anyway).

### 4.3 The blocker that shapes everything: conflicting runtimes

SNS requires **`java/1.8` AND `jdk/17u028`**, **`python/cpu/2.7.15` AND `python/cpu/3.6.5`**,
**`r/3.6.1` AND `r/4.1.2`**. A single conda environment cannot satisfy that — the same class of
conflict `environment.md` already documents for nextflow-vs-clawbio, but intra-pipeline.

**Consequence: per-segment containers, not a conda env.** Every tool SNS uses has a biocontainer, and
SNS's module names supply the version pins directly.

### 4.4 Segment classification

`M` = module count, `S` = hardcoded software path, `R` = hardcoded reference path.

| Segment | M | S | R | | Segment | M | S | R |
|---|---|---|---|---|---|---|---|---|
| align-bismark | 2 | – | – | | peaks-hmmratac | 3 | 1 | – |
| align-bowtie2-atac | 2 | 1 | – | | peaks-macs2 | 5 | – | – |
| align-bowtie2-chip | 2 | 1 | – | | peaks-macs3 | 5 | – | – |
| align-bwa-mem | 2 | 1 | – | | peaks-macs3-hmmratac | 2 | – | – |
| align-star | 1 | – | – | | qc-coverage-gatk | 1 | 1 | – |
| annot-annovar | 2 | 1 | 1 | | qc-fastqc | 1 | – | – |
| annot-regions-annovar | 1 | 1 | 1 | | qc-fastqscreen | 2 | – | – |
| bam-dedup-bismark | 2 | – | – | | qc-fragment-sizes | 2 | – | – |
| bam-dedup-sambamba | – | 1 | – | | qc-picard-rnaseqmetrics | 5 | – | – |
| bam-ra-rc-gatk | 2 | 1 | – | | qc-target-reads-gatk | 1 | 1 | – |
| bam-splitncigar-gatk | 3 | 1 | – | | quant-featurecounts | 1 | – | – |
| bigwig-bedtools | 3 | – | – | | quant-rsem | 1 | – | – |
| bigwig-deeptools | 1 | – | – | | quant-salmon | 2 | 2 | – |
| **cnvs-wes-freec** | 6 | 1 | **14** | | snvs-gatk-hc | 2 | 1 | – |
| fastq-clean | – | – | – | | snvs-lofreq | 5 | 2 | – |
| fastq-trim-trimgalore | 3 | – | – | | snvs-mutect2 | 4 | 1 | – |
| fastq-trim-trimmomatic | 2 | – | 1 | | snvs-strelka | 3 | 2 | – |
| meth-bismark | 3 | – | – | | species-centrifuge | – | 1 | 1 |
| nucleosomes-nucleoatac | 4 | – | – | | species-fastqscreen | 2 | 1 | – |

### 4.5 Route → segment map

| Route | Segments |
|---|---|
| `rna-star` | fastq-clean, qc-fastqc, qc-fastqscreen, fastq-trim-trimmomatic, align-star, bigwig-deeptools, qc-picard-rnaseqmetrics, quant-featurecounts |
| `rna-salmon` | fastq-clean, fastq-trim-trimmomatic, qc-fastqc, qc-fastqscreen, quant-salmon |
| `rna-rsem` | fastq-clean, qc-fastqscreen, quant-rsem |
| `rna-snv` | fastq-clean, fastq-trim-trimmomatic, qc-fastqc, qc-fastqscreen, align-star, bam-dedup-sambamba, bam-splitncigar-gatk, bam-ra-rc-gatk, snvs-gatk-hc, snvs-lofreq, qc-coverage-gatk, qc-target-reads-gatk |
| `atac` | fastq-clean, qc-fastqc, align-bowtie2-atac, bam-dedup-sambamba, bigwig-deeptools, qc-fragment-sizes, peaks-macs2, peaks-hmmratac, peaks-macs3-hmmratac |
| `chip` | fastq-clean, qc-fastqc, align-bowtie2-chip, bam-dedup-sambamba, bigwig-deeptools |
| `chip-pairs-peaks` | bam-dedup-sambamba, peaks-macs2, peaks-macs3 |
| `wes` | fastq-clean, fastq-trim-trimmomatic, qc-fastqc, align-bwa-mem, bam-dedup-sambamba, bam-ra-rc-gatk, snvs-gatk-hc, snvs-lofreq, qc-coverage-gatk, qc-target-reads-gatk, qc-fragment-sizes |
| `wes-pairs-snv` | snvs-mutect2, snvs-strelka |
| `wes-pairs-cnv` | cnvs-wes-freec |
| `wgbs` | fastq-clean, fastq-trim-trimmomatic, qc-fastqc, align-bismark, bam-dedup-bismark, meth-bismark |
| `rrbs` | fastq-clean, fastq-trim-trimgalore, qc-fastqc, align-bismark, meth-bismark |
| `species` | fastq-clean, species-centrifuge, species-fastqscreen |
| `rna-star-groups-dge` | (R only: `dge-deseq2.R`, `deseq2-pca.R`, `gse-fgsea.R`) |

### 4.6 Evidence of under-maintenance

`segments/cnvs-wes-freec.sh:178-185` — the `mm10` branch sets its variables and then unconditionally
`exit 1`s with `UNSUPPORTED GENOME`. Dead code.

`routes/atac.sh` calls both the legacy Java `peaks-hmmratac` and `peaks-macs3-hmmratac`; the MACS3
implementation supersedes it.

### 4.7 If SNS must be ported anyway — the design

Copy the pattern SNS already uses for references. Add `scripts/get-tool.sh` mirroring `get-ref.sh`,
backed by a per-site registry:

```
star       container  quay.io/biocontainers/star:2.7.3a--<build>
gatk3      container  broadinstitute/gatk3:3.8-1
sambamba   container  quay.io/biocontainers/sambamba:1.0.1--<build>
# site file for NYU keeps existing behaviour:
star       module     star/2.7.3a
```

Then the mechanical pass is `module add X` → `sns_tool X`; `foo_bin="/gpfs/..."` →
`foo_bin=$(sns_tool foo)`; `module purge` → `sns_env_reset`. After that, porting to a new cluster is
one file, not another 145 edits.

**Delivery mechanism: patch-at-prepare, not a hard fork.** Keep a pristine pinned upstream checkout
and apply a versioned patch set during the skill's `prepare` step. The diff *is* the port
documentation, it fails loudly when upstream drifts, and it stays compatible with the GARS rule that
agents never edit skill code.

**Route tiers if porting:**

| Tier | Routes | Note |
|---|---|---|
| 1 — cheap | `rrbs`, `wgbs`, `rna-star`, `rna-star-groups-dge`, `rna-rsem`, `chip`, `chip-pairs-peaks`, `atac`, `rna-salmon` | modules + a few biocontainer-available binaries |
| 2 — real work | `wes`, `rna-snv`, `wes-pairs-snv` | 7+ hardcoded tool paths each; GATK3 licensing; known-sites references **[unverified]** |
| 3 — cut | `wes-pairs-cnv`, `species`, ANNOVAR annotation | GEM mappability generation, >100 GB index, redistribution licensing |

**Do not use `sns/run`.** It hardcodes `--mail-user=${USER}@nyulangone.org`, fixed partitions, and
9 CPU / 80 GB for every sample of every route. Have the wrapper submit
`routes/<route>.sh <proj_dir> <sample>` itself (~40 lines) — this captures job IDs for `STATUS`,
honours `compute:` config, and touches zero lines of `routes/` or `segments/`. You must replicate
`run`'s sheet validation, `fix-csv.sh` pass, `SBATCHTIME=` extraction, and pairs/groups dispatch.

---

## 5. ClawBio skill library **[verified]**

`catalog.json` reports **95 skills**.

### 5.1 Maturity distribution

| Field | Distribution |
|---|---|
| `status` | 29 `mvp`, 66 `planned` |
| `maturity_tier` | 10 `ci-validated`, 39 `tested`, 38 `cli-registered`, 4 `spec-only`, 4 `scripted` |
| `has_script` | **89 of 95** |
| `has_script` + `has_tests` | 84 |
| `benchmark_validated` | `false` on every skill checked, including both GARS already uses |

**Important nuance:** `cli_registered` is irrelevant to GARS. Sub-stage contracts invoke
`python <skill>.py` directly and explicitly note the `clawbio.py` launcher "does not apply here." So
the practically usable set is ~89, not the 29 MVPs. Only 6 skills ship no code at all:
`de-summary`, `ncbi-datasets`, `repro-enforcer`, `bgpt-mcp`, `claw-semantic-sim`, `drug-photo`.

### 5.2 SNS route → ClawBio equivalence

| SNS route | ClawBio equivalent | Coverage |
|---|---|---|
| `rna-star`, `rna-salmon`, `rna-rsem` | **nfcore-rnaseq-wrapper** (`star_salmon`, `star_rsem`, `hisat2`, `bowtie2_salmon` + salmon/kallisto pseudo) | **Full** — already in GARS |
| `rna-star-groups-dge` | **rnaseq-de** (ci-validated) + **diff-visualizer** + **pathway-enricher** | **Full** for DE; SNS's fgsea maps to Enrichr-based `pathway-enricher` (different method) |
| `wes` | **nfcore-sarek-wrapper** (ci-validated) | **Full** |
| `wes-pairs-snv` | sarek `--tools mutect2,strelka,manta` | **Full — same three callers SNS uses** |
| `wes-pairs-cnv` | sarek `--tools controlfreec` (also `ascat`, `cnvkit`) | **Full — same tool**, with iGenomes resources instead of 14 hardcoded paths |
| `rna-snv` | none direct; `rare-disease-rnaseq` is expression-outlier detection | **Gap** |
| `chip`, `chip-pairs-peaks` | none — `gi-chromatin` is a DeepSEA-style sequence *predictor* | **Gap** |
| `atac` | none — same | **Gap** |
| `wgbs`, `rrbs` | none — `claw-methylation-cycle` is SNP/metabolic; `methylation-clock` is array-based | **Gap** |
| `species` | **claw-metagenomics** (mvp, `has_tests: false`) | **Partial**, different method |
| QC layer | **multiqc-reporter**, **bioqc-mcp**, **sample-qc-triage** | **Partial** — aggregation only |
| generic FASTQ→BAM | **seq-wrangler** (FastQC + BWA/Bowtie2/Minimap2 + SAMtools) | Alignment half only; no peak calling |

### 5.3 The decisive finding

**Coverage is inverted relative to SNS's value.** The 7 routes ClawBio covers well are covered
portably, in GARS's native pattern, often through identical tools. The 4–5 routes that would justify
SNS — ATAC, ChIP, WGBS/RRBS — have no ClawBio equivalent at all.

---

## 6. Recommended plan

### 6.1 Decision

Build new **wrapper skills** around **already-published nf-core pipelines**.

> **Read this before implementing.** "nf-core wrapper skill" means the thin ClawBio-style layer that
> *wraps* an existing upstream pipeline — exactly the relationship `nfcore-rnaseq-wrapper` has to
> `nf-core/rnaseq`. **No pipeline development is proposed anywhere in this document.**
> `nf-core/atacseq`, `nf-core/chipseq`, `nf-core/cutandrun`, and `nf-core/methylseq` are all
> published and maintained upstream. The pipeline does the science; the wrapper is what makes it
> satisfy the GARS contract. The new work per assay is *wrapper + sub-stage contract only*.

What the wrapper layer contributes — and why a sub-stage contract cannot simply call
`nextflow run nf-core/atacseq` itself:

| Wrapper responsibility | Why it is required |
|---|---|
| `--check` preflight | Contract forbids submitting before preflight passes |
| `_config/<assay>.yaml` → audited `params.yaml` | Agent must never improvise a pipeline parameter |
| Job-ID capture, `STATUS` writing, requeue guard | `STATUS` is the sole state authority; this cluster has `Requeue=1` |
| Structured `SkillError` (`error_code` + `fix`) | Contract requires verbatim, structured error reporting |
| Reproducibility bundle | `commands.sh`, `params.yaml`, `manifest.json`, checksums, provenance |
| Refusal to run a hand-written pipeline | 02.01: "do not call `nextflow` directly … Report and stop" |

Rationale for this route over porting SNS:

- The wrapper pattern is **proven three times** in ClawBio (`nfcore-rnaseq-wrapper`,
  `nfcore-scrnaseq-wrapper`, `nfcore-sarek-wrapper`) — clone, don't invent.
- The upstream pipelines are maintained and portable by construction.
- Nextflow 26.04.6 + Apptainer 1.5.3 are already installed and verified.
- No fork of anyone else's pipeline to maintain.
- Reference handling, container provisioning, and resume semantics come for free.

**ChIP-family: both wrappers are required.** Confirmed with the lab on 2026-08-12 — **both**
classical ChIP-seq and CUT&RUN/CUT&Tag are run here, so `nfcore-chipseq-wrapper` and
`nfcore-cutandrun-wrapper` are both in scope.

They are **two Assay IDs and two skills, never one skill with a mode flag.** They wrap different
upstream pipelines and differ in ways that would corrupt each other's results if merged:

| | `chipseq_bulk` | `cutandrun` |
|---|---|---|
| Upstream | `nf-core/chipseq` | `nf-core/cutandrun` |
| Control type | input chromatin | IgG |
| Normalisation | read-depth / input-relative | **spike-in** (usually *E. coli*) |
| Extra reference | — | spike-in genome index |

A single skill choosing between them at runtime would put a scientific decision inside the code,
which the config-is-a-user-decision rule forbids. Build them back to back: they share preflight,
params-translation, and reporting structure, so the second is mostly a diff of the first.

Keep SNS runnable as-is at NYU for comparability with historical ATAC/ChIP results. That is an
argument for *not deleting SNS*, not for porting it.

### 6.2 Build order

| # | Deliverable | Why this order |
|---|---|---|
| ~~0~~ | ~~**Prove one end-to-end nf-core run on this cluster**~~ | **DONE 2026-08-13** — see §2.3. The build order now starts at #1. |
| 0b | **Decide where GARS-authored wrappers live** (§6.2a) and **make stage 01 assay-aware** (Q2) | Both touch existing contracts and block wrapper #1 |
| 1 | `nfcore-atacseq-wrapper` skill + `02_bioinformatics/atacseq_bulk/01_.../CONTEXT.md` | Highest demand; validates the clone-the-pattern approach |
| 2 | `nfcore-chipseq-wrapper` + contract | Shares most structure with atacseq |
| 3 | `nfcore-cutandrun-wrapper` + contract | **Build immediately after #2** — mostly a diff of the chipseq wrapper while that structure is fresh |
| 4 | Wire `nfcore-sarek-wrapper` in as `wes` / `wgs` assays + contracts | Skill already exists and is ci-validated — cheapest real win |
| 5 | `nfcore-methylseq-wrapper` + contract | Covers `wgbs` + `rrbs` |
| 6 | Optional: peak-level downstream skills (differential binding) | Only after upstream works |

Total new wrapper skills: **four** (atacseq, chipseq, cutandrun, methylseq). Sarek needs a contract
only — the skill already exists.

### 6.2a Where GARS-authored wrappers live — **RESOLVED 2026-08-19: option A**

> Settled in [decision 0012](decisions/0012-gars-authored-wrappers-live-in-system.md):
> `gars/_system/wrappers/`, exported as `$GARS_WRAPPERS`. The rule is *third-party skills are
> installed and read-only; GARS-authored wrappers are versioned in the repo and ours to maintain*.
> B was rejected on pacing, not principle, and stays open per wrapper. The original analysis
> follows.

**[New 2026-08-14.]** §6.3 (below) assumes new wrappers go in `tools/skills/`. **That directory no
longer exists.** Skills were de-vendored on 2026-08-13; they now resolve at runtime from
`site-packages/clawbio/skills/` via `$GARS_SKILLS`, exported by `_system/gars-env.sh`.

`clawbio` is a third-party pip package, so a wrapper we write cannot be added to it. An
`nfcore-atacseq-wrapper` currently has **nowhere to live**.

Two viable answers:

| Option | Shape | Trade-off |
|---|---|---|
| **A — `gars/_system/wrappers/`** | Versioned in the GARS repo, exported as `$GARS_WRAPPERS` alongside `$GARS_SKILLS` | Fast; we own and maintain four wrappers. Keeps the no-vendoring rule intact, which was about not copying *someone else's* code |
| **B — contribute upstream to ClawBio** | Wrappers arrive via `pip` like the existing three | Slower and externally paced, but no new location, no maintenance burden, and matches how the current three got here |

If A: state the rule explicitly — *third-party skills are installed and read-only; GARS-authored
wrappers are versioned in the repo and are ours to maintain* — and add `$GARS_WRAPPERS` to
`gars-env.sh`.

**Cost note.** "Clone the wrapper pattern" is 12 modules mirroring a 2.1 MB skill — preflight,
params builder, command builder, executor, outputs parser, provenance, reproducibility bundle,
structured errors, tests. Per assay, times four. That cost is the strongest argument for B.

### 6.2b Contract changes since this document was written

New wrappers and their sub-stage contracts must also satisfy requirements added 2026-08-13/14:

| Requirement | Where |
|---|---|
| Source `_system/gars-env.sh`; do not re-declare env exports in `submit.sh` | supersedes the export block in §6.3 |
| `compute.work_dir` on scratch — a run accumulates 250-350 GB in `work/` | `_config/<assay>.yaml` |
| `reference.derived_dir`, keyed by **pipeline version**, populated automatically via `--save-reference` | 02.01 contract |
| Write `OUTPUTS.tsv` declaring artifacts by type and `native`/`adapted` role | `_references/artifact_types.md` |
| Assay map now has one row per sub-stage with `Consumes` / `Produces` columns | supersedes the table in §6.4 |
| Exit gates check **content**, not just file existence | a skill silently dropped a gene-identifier column and a file-exists gate passed it |
| Analysis sub-stages submit to Slurm too — a pure-Python DE step was SIGKILLed on a login node | 02.02 contract |

### 6.3 Skill design — clone the existing surface

Mirror `nfcore-rnaseq-wrapper` module-for-module so the sub-stage contracts read almost identically
to 02.01 and the agent's existing habits transfer:

```
<wrapper location — see §6.2a>/nfcore-atacseq-wrapper/
    SKILL.md                 # ClawBio-style YAML frontmatter
    nfcore_atacseq_wrapper.py
    preflight.py  schemas.py  params_builder.py  command_builder.py
    executor.py   outputs_parser.py  reporting.py  provenance.py
    pipeline_source.py  errors.py  remap_paths.py
    reproducibility/pinned_versions.json
    tests/
```

Required behaviours, carried over verbatim from 02.01's hard-won lessons:

| Behaviour | Reason |
|---|---|
| `--check` preflight writing `check_result.json` to its **own** directory | Preflight writes output; pointing it at `run/` leaves it non-empty and the real submission then fails |
| `--pipeline-local <path>` | Remote `nf-core/*` resolution goes through the GitHub REST API, capped at 60 req/h shared across this cluster's outbound IP |
| `--profile apptainer` | No Docker on this cluster |
| `--timeout-hours 0` | So the wrapper's internal cap does not pre-empt Slurm walltime |
| Reject non-empty `--output` (`OUTPUT_DIR_NOT_EMPTY`) | Consistency with existing wrappers |
| `submit.sh` requeue guard | This cluster has `Requeue=1`; add `-resume` when `run/.nextflow/` exists |
| Structured `SkillError` with `stage`, `error_code`, `message`, `fix`, `details` | Contract requirement |
| Reproducibility bundle | `commands.sh`, `params.yaml`, `manifest.json`, checksums, `environment.yml`, provenance JSON |

Environment exports every invocation must carry:

```bash
BIO=~/install/miniconda_clean/envs/gars-bio
NXF=~/install/miniconda_clean/envs/gars-nxf
export PATH="$NXF/bin:$BIO/bin:$PATH"
export APPTAINER_CACHEDIR=~/.apptainer_cache
export NXF_APPTAINER_CACHEDIR=~/.apptainer_cache
$BIO/bin/python nfcore_atacseq_wrapper.py ...   # never via `conda run` — it buffers and swallows output
```

### 6.4 Workspace changes

**`_references/assay_stage_skill_map.md`** — add rows:

| Assay | Assay ID | Stage | Sub-stages (ordered) | Skills |
|---|---|---|---|---|
| ATAC-seq (bulk) | `atacseq_bulk` | 02_bioinformatics | `01_nfcore-atacseq-wrapper` | nfcore-atacseq-wrapper |
| ChIP-seq (bulk) | `chipseq_bulk` | 02_bioinformatics | `01_nfcore-chipseq-wrapper` | nfcore-chipseq-wrapper |
| CUT&RUN / CUT&Tag | `cutandrun` | 02_bioinformatics | `01_nfcore-cutandrun-wrapper` | nfcore-cutandrun-wrapper |
| WES | `wes` | 02_bioinformatics | `01_nfcore-sarek-wrapper` | nfcore-sarek-wrapper |
| WGBS/RRBS | `methylseq` | 02_bioinformatics | `01_nfcore-methylseq-wrapper` | nfcore-methylseq-wrapper |

**`_config/<Assay ID>.yaml`** — per-assay schema. Sketch for ATAC:

```yaml
reference:                 # declare genome OR fasta+gtf, never both
  genome: GRCh38
aligner: bwa               # bwa | bowtie2 | chromap | star
peaks:
  type: narrow             # narrow | broad   — a scientific decision; never defaulted
  macs_gsize: 2701495761   # required by nf-core/atacseq unless --genome supplies it
compute:
  partition: cpu_medium
  time: "48:00:00"
  cpus: 8
  mem: 64G
```

**Control assignment is a stage-01 concern, and it differs per assay.** `01_prepare_samplesheets`
currently emits `sample_id,condition,group,replicate` only. Both ChIP-family assays need a control
column added, but they do not mean the same thing:

| Assay | Column | Points at | Notes |
|---|---|---|---|
| `chipseq_bulk` | `control` | the input-chromatin sample | nf-core/chipseq samplesheet requirement |
| `cutandrun` | `control` | the IgG sample | plus spike-in normalisation, so the config carries a spike-in genome |

Design one control mechanism that serves both rather than two — the column shape is identical and
only the biological referent differs — but keep the *validation* per-assay, since "every ChIP sample
has an input" and "every CUT&RUN sample has an IgG" are separate checks against separate configs.

**Stage 01 impact — done 2026-08-19.** The emitter is now table-driven: `FORMATS` in
`_system/stage01_samplesheet.py` holds one entry per Assay ID, each column declaring its source
(`sample_id`/`fastq_1`/`fastq_2` from `files.csv`, `config:<key>` from `_config/<assay>.yaml`,
`design:<col>` from `samples.csv`). Adding an assay is a row plus, if needed, a validator — not a
change to any function. `--list-formats` prints what is registered.

Only `rnaseq_bulk` is registered, because it is the only assay in the map. **The four planned
assays each add their entry when that pipeline's samplesheet schema has been read from the
pipeline itself** — the columns were deliberately not guessed from memory here.

The `control` column for ChIP/CUT&RUN is expressible today as `design:control`, but it needs a
`control` column in `samples.csv`, which stage 00 does not yet write. The emitter reports that as
a `config` failure rather than emitting a blank column, so the gap is loud. Making stage 00's
`samples.csv` header assay-aware is the remaining piece, and belongs with wrapper #2 (chipseq).

### 6.5 Reference prerequisites — **mostly resolved [verified 2026-08-14]**

| Requirement | Status |
|---|---|
| Local iGenomes mirror | **Yes** — `/gpfs/data/sequence/references/iGenomes/`, with `Homo_sapiens/{Ensembl,NCBI,UCSC}` and `Mus_musculus`. Usable as `--igenomes-base`. |
| ATAC/ChIP blacklist BED | **Yes** — `/gpfs/data/igorlab/ref/hg38/blacklist.bed`, plus `v1` and `v2` variants. Pick deliberately; they differ. |
| CUT&RUN spike-in genome | **Yes** — the same mirror carries `Escherichia_coli_K_12_MG1655`, the standard spike-in. No build required. |
| methylseq bisulfite index | **No shortcut.** Only `PhiX`, `hg38_SARS-CoV-2` and `hg38_MPXV` combined genomes have Bismark indices; there is no plain human one. methylseq must build its own — expensive, but it removes the cross-lab dependency this document worried about. Budget for it and cache the result under `derived/nf-core-methylseq-<version>/`. |
| `macs_gsize` | Still a user decision; never default it. |
| sarek BQSR `--dbsnp` / `--known-indels` | **[unverified]** — still to confirm. Do not let it be silently skipped. |

**Prefer Ensembl over the iGenomes NCBI build.** The GRCh38 iGenomes annotation is NCBI and
carries no biotype attribute; it is what killed `SUBREAD_FEATURECOUNTS` after 1h38m of otherwise
successful work. GARS already holds a verified Ensembl GRCh38 r116 FASTA + GTF at
`~/install/refs/ensembl-GRCh38-116/`, with derived STAR/Salmon indices cached and proven reusable.
Whether ATAC/ChIP/methyl pipelines have the same biotype sensitivity is **[unverified]**, but
starting from the reference that is already validated here is the cheaper default.

### 6.5a Pipeline versions to pin **[verified 2026-08-14]**

Latest released tags at time of writing. Confirm again at implementation and pin explicitly:

| Pipeline | Latest tag |
|---|---|
| `nf-core/atacseq` | 2.1.2 |
| `nf-core/chipseq` | 2.1.0 |
| `nf-core/cutandrun` | 3.2.2 |
| `nf-core/methylseq` | 4.2.0 |

All four exist and are reachable. Clone over the git protocol into `~/install/nf-core-pipelines/`
alongside `rnaseq-3.26.0`.

### 6.6 Local pipeline checkouts

Clone over the **git protocol** (not the GitHub REST API) into `~/install/nf-core-pipelines/`,
matching the existing `rnaseq-3.26.0` checkout. Pin a tag, verify with `git describe --tags` before
trusting any version-override flag. Refresh with `git -C <dir> fetch --tags`.

**[unverified]** — pin the exact version of each pipeline at implementation time; do not assume the
versions in this document.

---

## 7. Open questions

| # | Question | Status | Blocks |
|---|---|---|---|
| ~~1~~ | ~~Does any nf-core pipeline complete end-to-end here?~~ | **RESOLVED 2026-08-13** — yes, see §2.3 | — |
| **2** | Should stage 01's samplesheet emitter become assay-aware, or emit per-assay column sets? | **RESOLVED 2026-08-19.** Assay-aware, table-driven: `FORMATS` in `_system/stage01_samplesheet.py`, one entry per Assay ID, printable with `--list-formats`. An assay with no entry is refused rather than given the RNA layout | — |
| **2b** | Where do GARS-authored wrappers live, now that the vendored skills directory is gone? | **RESOLVED 2026-08-19** — `gars/_system/wrappers/`, decision 0012 | — |
| ~~3~~ | ~~How do control assignments (ChIP input, CUT&RUN IgG) enter the design table?~~ | **RESOLVED 2026-08-25** — per-assay design columns via `workspace.design_columns` (decision 0030): chipseq's `control` names the input sample (with `control_replicate` derived), cutandrun's names the IgG group; validation is per-assay | — |
| ~~3b~~ | ~~Classical ChIP-seq or CUT&RUN/CUT&Tag?~~ | RESOLVED 2026-08-12: the lab runs both, as separate Assay IDs | — |
| ~~3c~~ | ~~Where does the CUT&RUN spike-in genome come from?~~ | **RESOLVED 2026-08-14** — `Escherichia_coli_K_12_MG1655` in the local iGenomes mirror | — |
| ~~4~~ | ~~Is there a local iGenomes mirror?~~ | **RESOLVED 2026-08-14** — yes, `/gpfs/data/sequence/references/iGenomes/` | — |
| ~~5~~ | ~~Reuse `igorlab`'s Bismark indices, or build our own?~~ | **RESOLVED 2026-08-14** — none exist for human; **build our own** | — |
| 6 | Does anyone still need `rna-snv`? | OPEN | Scope |
| 7 | Should SNS stay in `archive/` as a reference implementation? | OPEN | Housekeeping |
| ~~8~~ | ~~Build wrappers ourselves (§6.2a option A) or contribute upstream to ClawBio (option B)?~~ | **RESOLVED 2026-08-25** — built ourselves, but as thin `_system/` helpers on a shared `wrapperlib.py` rather than 12-module clones (decision 0028), which dissolved the cost driver; all five assays wired (decisions 0029, 0031) | — |

---

## 8. What was rejected, and why

| Option | Verdict |
|---|---|
| One skill per SNS route (14 skills) | **No.** Route variance is data, not code — a table, not 14 codebases. Would also reintroduce description-matching as the routing mechanism, which ICM's folder-based routing exists to avoid. |
| One `sns-wrapper` skill + N sub-stage contracts | **Sound design, wrong target.** This was the right shape *if* SNS were the answer. Superseded by §5.3. |
| Port SNS to be portable | **No.** Feasible (~145 lines) but the real costs are per-segment containerization, an R container, a reference bundle, a fork to maintain, and full revalidation of every route against known-good results. All to reach tools that nf-core already provides portably. |
| Wrap SNS's `rna-*` / `wes*` routes | **No.** Duplicates `nfcore-rnaseq-wrapper` and `nfcore-sarek-wrapper` with a site-locked implementation of the same underlying tools. Two RNA-seq paths under one assay ID would also make stage 02's routing non-deterministic. |
| Keep SNS runnable as-is at NYU | **Yes**, outside GARS. Comparability with historical ATAC/ChIP results is a real scientific argument. |

---

## 9. Reference: SNS settings keys

For anyone reading SNS output or comparing results.

| Key | Set by | Meaning |
|---|---|---|
| `GENOME-DIR` | `generate-settings` | reference bundle root |
| `REF-FASTA`, `REF-GTF`, `REF-DICT`, `REF-STAR`, `REF-SALMON`, `REF-BWA`, `REF-CHROMSIZES`, `REF-REFFLAT`, `REF-RRNAINTERVALLIST` | `get-ref.sh`, lazily on first use | discovered by convention under `GENOME-DIR` |
| `EXP-STRAND` | **inferred by `align-star`** and persisted | `unstr` / `fwd` / `rev`, from ReadsPerGene column ratios (>5× threshold, requires >10,000 unstranded counts) |
| `EXP-TARGETS-BED` | user or auto-found | capture targets for WES |
| `EXP-PEAKS-TYPE`, `EXP-PEAKS-MACS2-Q`, `EXP-PEAKS-MACS3-Q` | route arguments | peak calling parameters |
