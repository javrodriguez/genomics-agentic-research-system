# Genome registry

The references a project may be aligned against. Selecting one fills `reference.fasta`,
`reference.gtf` and `reference.derived_dir` together, so a FASTA can never be paired with a
mismatched annotation — the pairing is a property of the reference, not a decision the user makes
twice.

**One table, deliberately.** `assay_stage_skill_map.md` has two, and a parser that read every
pipe-prefixed line once accepted a skill name as an assay and created `00_data/(unpinned)/`. Add
columns here, never a second table.

**Paths are site-specific.** They are correct for this cluster. A different site edits this file;
nothing else needs to change.

| ID | Species | Build | Source | FASTA | GTF | Derived index cache |
|---|---|---|---|---|---|---|
| GRCh38 | Homo sapiens | GRCh38 | Ensembl release 116 | /gpfs/data/abl/home/rodrij92/install/refs/ensembl-GRCh38-116/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz | /gpfs/data/abl/home/rodrij92/install/refs/ensembl-GRCh38-116/Homo_sapiens.GRCh38.116.gtf.gz | /gpfs/data/abl/home/rodrij92/install/refs/ensembl-GRCh38-116/derived/nf-core-rnaseq-3.26.0 |

## Why Ensembl and not iGenomes

The iGenomes `GRCh38` is the **NCBI** build and carries no `gene_biotype` attribute.
`SUBREAD_FEATURECOUNTS` fails on it *after* counts are written — a full run wasted, diagnosed as
failure 5 in [decision 0005](../../docs/decisions/0005-execution-failures-and-fixes.md). Registering
only verified pairs is what stops that being re-discovered.

## The derived cache

Optional per row, and worth having: it holds the STAR and Salmon indices already built for this
FASTA+GTF, so a run skips roughly 43 GB and 40 minutes of index building. It is keyed by
**pipeline version**, because a STAR index is rejected by a different STAR version
(`Genome version 2.7.1a is INCOMPATIBLE with running STAR version 2.7.11b`). A sub-stage reusing
one must verify `versionGenome` before trusting it.

Leave the column empty for a reference whose indices have not been built.

## Adding a reference

One row. Requirements before adding it:

1. The FASTA and GTF are the **same source and release** — mixing them silently misannotates.
2. The GTF carries `gene_biotype`, or featureCounts will fail late.
3. Both paths are readable by everyone who will run the pipeline.
4. The derived cache, if given, was built by the pipeline version named in its path.

Mouse is the obvious next one. `/gpfs/data/sequence/references/iGenomes/Mus_musculus/Ensembl/`
exists on this cluster but has not been verified against a run, and an unverified row is worse
than an absent one — the registry's value is that everything in it is known to work.
