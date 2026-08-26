# Project configuration schema

`projects/<project_title>/_config/` holds the scientific decisions for one project. **Stage 00
seeds it** from `_templates/config/` at project creation ([decision 0019]): every derivable
value filled, every scientific decision marked `<REQUIRED>`. **Stage 02 completes the
`<REQUIRED>` keys from menus** the user answers ([decision 0020]) — the genome registry, the
per-assay decision menu — and shows the result for confirmation before writing. No stage ever
chooses a scientific value silently, because a wrong value here produces confident, wrong
biology rather than an error, which is the one failure mode no downstream check can catch.

| File | Seeded by | Completed by | Read by |
|---|---|---|---|
| `<Assay ID>.yaml`, one per assay | stage 00, from `_templates/config/` | stage 02 menus (`_system/configure.py apply`), user confirms | stage 01 (assay-specific keys), the stage 02 wrapper |
| `nextflow.slurm.config` | stage 00, verbatim copy | nothing — edit by hand only if your allocation differs | every wrapper's generated `submit.sh` |

## The common shape

Every `<Assay ID>.yaml` has a `reference` block, a `compute` block, and at most one
assay-specific decision block. Values the genome menu sets travel together so they cannot be
mismatched (`_references/genomes.md`): fasta, gtf, and — where the assay uses them —
`mito_name`, `macs_gsize`, and the version-keyed `derived_dir`.

**`reference.genome` (the iGenomes key) is deliberately not supported.** The iGenomes GRCh38 is
the NCBI build with no `gene_biotype`; it killed a full run *after* counts were written
(decision 0005, failure 5). Every wrapper refuses the key; the registry's fasta+gtf pairs are
the verified route.

**`compute.*`** is infrastructure, not science: Slurm directives for the generated `submit.sh`
(`partition`, `time`, `cpus`, `mem`) plus `compute.work_dir` — Nextflow's scratch, **never
inside the project**: `work/` retains every process output so `-resume` can reuse it, and a
single run accumulates hundreds of GB there. `results/` is published with mode `copy`, so
`work/` is disposable once a run succeeds.

## Per-assay decision blocks

| Assay | Beyond `reference` + `compute` | Decision menu at stage 02 |
|---|---|---|
| `rnaseq_bulk` | `strandedness` (stage 01 reads it into the samplesheet); `de.formula`, `de.contrast` | genome + contrast (+ formula, default `~ condition`) |
| `atacseq_bulk` | `peaks.type` (narrow\|broad), `peaks.macs_gsize`, `reference.mito_name`, optional `reference.blacklist` | genome + peak type |
| `chipseq_bulk` | `peaks.type`, `peaks.macs_gsize`, optional `reference.blacklist` (no `mito_name` — the pipeline has no such parameter) | genome + peak type |
| `cutandrun` | `reference.mito_name`; `spikein.fasta` (seeded with the local E. coli K12 mirror path); `peaks.peakcaller` (seacr\|macs2), `peaks.normalisation`, `peaks.use_control` — presented defaults, confirmed not chosen | genome only |
| `methylseq` | none — fasta and `aligner` (bismark\|bismark_hisat\|bwameth\|bwamem) are the whole surface; no annotation is used | genome only |

The authoritative key list for each assay is its template in `_templates/config/` — the seeded
file carries a comment on every key saying what it is and where its value comes from. This page
is the map, not a second copy of the keys.

## The derived-reference cache (`reference.derived_dir`)

Optional but strongly recommended where a wrapper supports it (rnaseq, atacseq, chipseq).
Pipelines build aligner indices into `work/` and, by default, never publish them — rebuilt from
scratch every run (~43 GB and ~40 minutes for rnaseq). The wrappers close the loop in code:
`prepare` passes the cached indices when the keyed directory is populated, passes
`--save-reference` when it is not, and `collect` harvests the built indices into the cache
atomically, with a `PROVENANCE` file.

**The cache is keyed by pipeline version, not just genome build.** An aligner rejects an index
built by an incompatible version (`Genome version 2.7.1a is INCOMPATIBLE with running STAR
version 2.7.11b`), so the version is part of the path — `configure.py` appends the assay's pin
from `workspace.PIPELINES` to the registry's cache root:

```
<refs>/ensembl-GRCh38-116/
    Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
    Homo_sapiens.GRCh38.116.gtf.gz
    derived/nf-core-rnaseq-3.26.0/      <- version-keyed, safe to reuse
        index/star/  index/salmon/  genome.transcripts.fa  PROVENANCE
    derived/nf-core-atacseq-2.1.2/
        bwa/  PROVENANCE
```

The rnaseq wrapper additionally refuses a STAR cache directory that lacks
`genomeParameters.txt` — a half-built cache is never reused (decision 0009). cutandrun and
methylseq have no cache yet; their first live runs establish what is worth harvesting.

## `nextflow.slurm.config`

The executor settings every generated `submit.sh` passes to Nextflow with `-c`. **Required,
not optional.** Nextflow submits each pipeline process as its own Slurm child job, and without
an explicit `process.queue` it dispatches them to whatever partition it defaults to, ignoring
the partition chosen for the parent job.

The file must define **no `params`** — every wrapper's preflight rejects a config that does
(`executor_config` failure), so the audited parameter surface in `params.yaml` cannot be
bypassed.

## Adding an assay

A new assay adds a template in `_templates/config/<Assay ID>.yaml` (stage 00 seeds whatever
exists there), an `ASSAY_DECISIONS` entry in `_system/configure.py` naming its decision shape,
and a row in the table above. Keep the common `reference`/`compute` shape and add only the keys
the assay's pipeline genuinely requires — read from its `nextflow_schema.json`, never from
memory (decision 0031).

[decision 0019]: ../../docs/decisions/0019-config-is-seeded-not-authored.md
[decision 0020]: ../../docs/decisions/0020-config-decisions-come-from-menus.md
