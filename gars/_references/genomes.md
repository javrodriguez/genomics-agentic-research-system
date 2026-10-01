# Genome registry

The references a project may be aligned against. Selecting one fills `reference.fasta`,
`reference.gtf`, the assay-appropriate `reference.derived_dir`, and the genome-derived facts an
assay needs (mitochondrial contig name, MACS effective genome size) together, so a FASTA can
never be paired with a mismatched annotation — the pairing is a property of the reference, not a
decision the user makes twice.

**One table, deliberately.** `assay_stage_skill_map.md` has two, and a parser that read every
pipe-prefixed line once accepted a skill name as an assay and created `00_data/(unpinned)/`. Add
columns here, never a second table.

**Paths are site-specific.** They name two sites. The GRCh38 row's paths begin with a placeholder,
`/path/to/group-work-area`, for the HPC cluster's group work area, under which the references sit in
`install/refs/`; a site using that row replaces it. The R64-1-1 row's are correct for the launch pad, whose GARS clone is
`/home/ubuntu/genomics-agentic-research-system` and keeps its references in the clone's
self-ignoring `install/refs/`. A different site edits this file; nothing else needs to change.

| ID | Species | Build | Source | FASTA | GTF | Derived cache root | Mito contig | MACS gsize |
|---|---|---|---|---|---|---|---|---|
| GRCh38 | Homo sapiens | GRCh38 | Ensembl release 116 | /path/to/group-work-area/install/refs/ensembl-GRCh38-116/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz | /path/to/group-work-area/install/refs/ensembl-GRCh38-116/Homo_sapiens.GRCh38.116.gtf.gz | /path/to/group-work-area/install/refs/ensembl-GRCh38-116/derived | MT | 2701495761 |
| R64-1-1 | Saccharomyces cerevisiae | R64-1-1 | nf-core/test-datasets atacseq branch, pinned by sha256 | /home/ubuntu/genomics-agentic-research-system/install/refs/R64-1-1/genome.fa | /home/ubuntu/genomics-agentic-research-system/install/refs/R64-1-1/genes.gtf | /home/ubuntu/genomics-agentic-research-system/install/refs/R64-1-1/derived | MT | 11624332 |

**Derived cache root, not path.** The cell names the *root*; `configure.py` appends the assay's
pinned pipeline key from `workspace.PIPELINES` (`nf-core-rnaseq-3.26.0`,
`nf-core-atacseq-2.1.2`, …), because an index cache is only valid for the pipeline version that
built it. A keyed directory that does not exist yet is still written to the config: the wrapper
passes `--save-reference` on the first run and harvests the built indices into it.

**Mito contig** is the assembly's mitochondrial sequence name — `MT` for Ensembl, `chrM` for
UCSC. ATAC-seq pipelines filter mitochondrial reads by this name; a wrong one silently filters
nothing.

**MACS gsize** is the effective genome size MACS2 uses for peak calling. The GRCh38 value is
deepTools' 50-bp unique-mappability figure (2,701,495,761) as printed in the deepTools
documentation of every release from 3.4.0 to 3.5.4 (3.5.5 and 3.5.6 print 2,701,495,711); it is
not nf-core's figure: nf-core/atacseq 2.1.2's iGenomes config lists 2,701,262,066 for its NCBI
GRCh38 at read length 50 (corrected in decision 0256). It is a property of the assembly,
recorded here so it is chosen once, with the genome — never typed per project.

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

**R64-1-1 against requirement 2.** Its GTF carries `gene_biotype` on every record (34,945 of
34,945 lines of the pinned file, read from its bytes), so featureCounts would not fail on it for
want of the attribute, and requirement 2 bars no assay from it. The row is registered for the
launch pad's ATAC-seq and ChIP-seq fixtures, which use the GTF for annotation, not for counting;
an RNA-seq run on it is not part of that registration.

Mouse is the obvious next one. `/gpfs/data/sequence/references/iGenomes/Mus_musculus/Ensembl/`
exists on this cluster but has not been verified against a run, and an unverified row is worse
than an absent one — the registry's value is that everything in it is known to work.

## Reference hashes (R-090)

This second table is keyed by ID and is parsed separately from the identity table
above. It supersedes the earlier one-table instruction for hash provenance only.
UNKNOWN is incomplete evidence; the owner must hash the registered files where
they live before a run can satisfy manifest group 6.

| ID | Annotation release | fasta_sha256 | gtf_sha256 |
|---|---|---|---|
| GRCh38 | Ensembl release 116 | UNKNOWN | UNKNOWN |
| R64-1-1 | test-datasets atacseq branch, fetched 2026-09-30 | c0b7305c230b550c3d8ccc692df52338afc7a297b43d965868c285b98aa64ae1 | 3a1e64b8f290127562612b47d6014bc6e4c130399da3e06ad062b268fd6d08fb |
