# Project configuration schema

`projects/<project_title>/_config/` holds the scientific decisions for one project. Stage 00
creates the directory empty; **the user writes every file in it** before stage 02 runs. Stages 01
and 02 read it and nothing writes it automatically, because every key here is a decision the
system must not make on the user's behalf.

| File | Written by | Read by |
|---|---|---|
| `<Assay ID>.yaml`, one per assay | user | 01_prepare_samplesheets, 02_bioinformatics |
| `nextflow.slurm.config` | user | 02_bioinformatics sub-stages that submit Nextflow |

**A stage that finds a required key missing stops and asks.** It never substitutes a default for
`reference`, `de.formula`, or `de.contrast` — a wrong value there produces confident, wrong
biology rather than an error, which is the one failure mode no downstream check can catch.

## `<Assay ID>.yaml`

```yaml
# _config/rnaseq_bulk.yaml
strandedness: auto              # auto | forward | reverse | unstranded   (read by stage 01)
reference:                      # declare genome OR fasta+gtf, never both
  genome: GRCh38                # iGenomes key
  # fasta: /path/to/genome.fa
  # gtf:   /path/to/genes.gtf
aligner: star_salmon            # star_salmon | star_rsem | hisat2 | bowtie2_salmon
compute:                        # Slurm directives for the pipeline job
  partition: cpu_long
  time: "5-00:00:00"
  cpus: 8
  mem: 64G
  # Nextflow's work directory. Point it at scratch, never inside the project.
  # A single 10-sample run accumulates 250-350 GB of intermediates there: work/ retains
  # every process output so -resume can reuse it, so trimmed FASTQs, unsorted BAMs, sorted
  # BAMs and deduplicated BAMs all coexist. results/ is published with mode 'copy', so
  # work/ is disposable once a run succeeds.
  work_dir: /gpfs/scratch/<user>/gars-work
  # Optional: cached indices built by a previous run with --save-reference.
  # Must be keyed by pipeline version -- see below.
  # derived_dir: <refs>/ensembl-GRCh38-116/derived/nf-core-rnaseq-3.26.0

de:                             # read by sub-stage 02.02
  formula: "~ condition"        # every term must be a column of the design table
  contrast: "condition,treated,control"   # factor,numerator,denominator
```

### `strandedness`

Set it explicitly when the library is known. `auto` delegates to nf-core's RSeQC-based check,
which cannot return a confident *stranded* call on an unstranded library and reports it as
"N/N samples failed strandedness check" — a warning that reads like a failure and is not one.

### `reference.derived_dir` — the index cache

Optional but strongly recommended. nf-core builds the STAR index, Salmon index and transcripts
FASTA into `work/` and, with `save_reference = false` (its default), never publishes them — so
they are rebuilt from scratch on every run, roughly 43 GB and an hour each time. Build them once
with `--save-reference`, harvest `results/genome/` into a cache, and point later runs at it.

**The cache must be keyed by pipeline version, not just genome build.** A STAR index is rejected
by a different STAR version (`Genome version 2.7.1a is INCOMPATIBLE with running STAR version
2.7.11b`), so the version must be part of the path or the incompatibility becomes a trap:

```
<refs>/ensembl-GRCh38-116/
    Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
    Homo_sapiens.GRCh38.116.gtf.gz
    derived/nf-core-rnaseq-3.26.0/      <- version-keyed, safe to reuse
        star/  salmon/  transcripts.fa  genome.bed
```

A sub-stage reusing a cached index must read `versionGenome` from `genomeParameters.txt` and
verify it before use. The incompatibility surfaces only when STAR loads the index mid-run, so no
preflight can detect it.

## `nextflow.slurm.config`

The executor settings passed to the wrapper via `--nextflow-config`. **Required, not optional.**
Nextflow submits each pipeline process as its own Slurm child job, and without an explicit
`process.queue` it dispatches them to whatever partition it defaults to, ignoring the partition
chosen for the parent job.

The file must define **no `params`** — the wrapper rejects configs that do, so its audited
parameter surface cannot be bypassed.

## Adding an assay

A new assay needs its own `<Assay ID>.yaml` shape. Keep the three top-level groups that are not
assay-specific — `reference`, `compute`, and any per-sub-stage group such as `de` — and add only
the keys that assay's pipeline genuinely requires. Document them here, in this file, so the
schema has one home.
