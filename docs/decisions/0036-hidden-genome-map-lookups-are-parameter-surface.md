---
date: 2026-08-28
status: standing
kind: lesson
touches:
  - gars/_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py
  - gars/_templates/config/cutandrun.yaml
  - gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md
symptoms:
  - "No such file or directory: s3://ngi-igenomes"
  - "pipeline chases an s3 path despite local references supplied"
  - "nf-amazon plugin downloads on an offline-intended run"
---
# A pipeline's hidden genome-map lookups are part of its parameter surface

## What happened

cutandrun's first live run (campaign project `cuttag-k562`, job 26873220) died in 19 seconds:
`No such file or directory: s3://ngi-igenomes/igenomes/Escherichia_coli_K_12_MG1655/.../Bowtie2Index`.
The wrapper passed a local `spikein_fasta`, but nf-core/cutandrun 3.2.2 resolves the spike-in
**bowtie2 index** independently, from its own genome map keyed on `spikein_genome`
(default `K12-MG1655`) — an s3 iGenomes path — regardless of the supplied fasta. The 0034
parser pairing worked; the pipeline booted far enough to fetch the nf-amazon plugin and chase
the cloud path.

## Decision

Every genome-map lookup a pipeline performs is parameter surface the wrapper must pin locally,
whether or not a local file was already supplied for the "same" reference. For cutandrun:
`spikein.bowtie2` ships in the seeded config beside `spikein.fasta`, pointing at the local
mirror's `Bowtie2Index` — the exact twin of the s3 path the pipeline would have fetched
(verified present on the mirror). The wrapper requires the key, content-checks it in preflight
(`genome.1.bt2` readable — a directory existing is not an index existing), and passes
`--spikein_bowtie2` explicitly, which wins over the map default.

## The lesson

Passing a local fasta proves nothing about the pipeline's OTHER references. Promotion of an
assay must read the pipeline's parameter resolution (its config's genome-map attributes), not
only the parameters the wrapper chooses to set — the atacseq run escaped this only because we
passed fasta+gtf explicitly for the main genome. Same family as 0035: the pinned checkout is
one file away from the assumption it would have corrected.
