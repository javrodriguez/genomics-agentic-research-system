---
date: 2026-09-30
status: standing
kind: decision
touches:
  - gars/_references/genomes.md
  - tests/test_genome_registry_r64.py
symptoms:
  - the launch pad's yeast fixtures (R64-1-1) are not in the genome registry, so no peak-assay menu offers them
  - mito_name Mito passed for a FASTA whose mitochondrial contig is MT; the mito filter is skipped with no error
  - a MACS gsize that is the whole-assembly length where the registry states the 50-bp effective size
---
# R64-1-1 in the genome registry: the launch pad's yeast reference, with its hash row

Every ruling in this record is **glitch-14's**, the Row-orchestrator's, made under the owner's standing delegation of 23 September 2026; no sentence here is the owner's.
The protected-path approval of the registry change is [0247](0247-r64-genome-row-0246-owner-approval-of-protected-change.md), which waits for the owner's own typed word; this record does not write it.

## Context

The launch pad runs GARS on a cloud box whose clone is `/home/ubuntu/genomics-agentic-research-system`, with a self-ignoring `install/` folder beside the code.
Its first recorded take navigates a yeast project through ATAC-seq and ChIP-seq on the nf-core/test-datasets fixtures, and stage 02 offers a reference only through the genome menu (`configure.py genomes`), which reads `_references/genomes.md`.
The registry had one row, GRCh38, for the HPC cluster.
Manifest group 6 passes only when the registry's `fasta_sha256` and `gtf_sha256` match the files the run used (`wrapperlib.reference_evidence`), so the row needs its hash row as well.

The two fixture files were downloaded on 30 September 2026 from the test-datasets `atacseq` branch (head `cd022b097372b078a68d8afadb172ad7342fd91f` at fetch) and hashed:

```
$ shasum -a 256 genome.fa genes.gtf
c0b7305c230b550c3d8ccc692df52338afc7a297b43d965868c285b98aa64ae1  genome.fa
3a1e64b8f290127562612b47d6014bc6e4c130399da3e06ad062b268fd6d08fb  genes.gtf
```

Both equal the pins the demo's fixture spec carries for them.
The launch-pad plan proposed the row with mito contig `Mito` and MACS gsize `12157105`, the values the demo's 3 September runs used.
The lane read both from the bytes and found one wrong and one against the registry's own convention; it stopped before writing the row, and glitch-14 ruled.

**The mitochondrial contig is `MT`.**
`grep -n '^>' genome.fa` lists seventeen headers, `I` to `XVI` and `MT` (line 55539); none is `Mito`.
The GTF uses the same names: 251 of its records are on `MT` and none on `Mito`.
nf-core/atacseq 2.1.2 (tag commit `1a1dbe52ffbd82256c941a032b0e22abbd925b8a`) says the same for these very files: `conf/test.config:27` sets `mito_name = 'MT'` beside the two test-datasets URLs (lines 28-29), and `conf/igenomes.config:364` sets `mito_name = "MT"` for R64-1-1.

**The MACS gsize is 11624332.**
The FASTA's summed sequence length is 12157105 (`awk '!/^>/{gsub(/[ \t\r]/,""); total+=length($0)}END{print total}' genome.fa`), the whole assembly with `MT`'s 85779 bases included; that is the figure the demo used.
It is not the registry's figure: genomes.md states that the GRCh38 value is the deeptools 50-bp unique-mappability effective size, the value nf-core/atacseq's own iGenomes config uses at the default read length.
For R64-1-1 that config gives 11624332 at read length 50 (`conf/igenomes.config:365-371`), and the fixtures' own test profile runs at read length 50 (`conf/test.config:24`).
11624332 is nf-core's precomputed effective size for the iGenomes Ensembl R64-1-1 FASTA; it applies to this fixture **by inference**, because the fixture is the same R64-1-1 assembly under Ensembl contig names, and not by a measurement on the fixture.
No effective-size tool (khmer or another) was run on the fixture, and whether the iGenomes FASTA's bytes equal the fixture's was not checked.

**`gene_biotype`.** `grep -c gene_biotype genes.gtf` and `wc -l` both give 34945, with no header line, so every record carries the attribute and requirement 2 of "Adding a reference" is met.
The GTF carries no release line, so the hash row's annotation release names its source and fetch date.

The lane's commands and their full outputs, and a second builder's independent reproduction that agrees on every value, are kept outside the repository in the lane's evidence folder.

## Decision

1. **One identity row, after GRCh38**, so GRCh38 stays menu 01 and R64-1-1 is 02 (the suite's fixtures cut the registry at `| GRCh38 |`):
   `| R64-1-1 | Saccharomyces cerevisiae | R64-1-1 | nf-core/test-datasets atacseq branch, pinned by sha256 | /home/ubuntu/genomics-agentic-research-system/install/refs/R64-1-1/genome.fa | …/genes.gtf | …/derived | MT | 11624332 |`.
   The paths sit in the pad clone's self-ignoring `install/refs/`, so the clone stays clean.
   The derived cache root is given before any index is built; the wrappers pass `--save-reference` on the first run and harvest into the keyed directory, as the registry's cache paragraph says.
   Each peak assay's cache is that root plus its own pinned pipeline, `nf-core-atacseq-2.1.2` and `nf-core-chipseq-2.1.0`, so ATAC and ChIP never share an index.
2. **One hash row**, keyed by ID in the separate table: `| R64-1-1 | test-datasets atacseq branch, fetched 2026-09-30 | c0b7305c… | 3a1e64b8… |`, both hashes re-derived from the downloaded bytes.
3. **Two sites named.** "Paths are site-specific" now says the GRCh38 row's paths are the HPC cluster's and the R64-1-1 row's are the launch pad's.
4. **Requirement 2 stated for this row.** One paragraph after the requirements: the GTF carries `gene_biotype` on every record, so requirement 2 bars no assay; the row is registered for the pad's ATAC-seq and ChIP-seq fixtures, which use the GTF for annotation, and an RNA-seq run on it is not part of that registration.
5. **A test**, `tests/test_genome_registry_r64.py`, collected by `tests/run_tests.py`; the README and DEVELOPMENT.md totals move from 1208 to 1211, the loader's count.

Every other line of `genomes.md` is unchanged, and no code changes.

## Rejected alternatives

- **`Mito`, as the plan proposed.** It names no contig in the pinned FASTA; nf-core/atacseq 2.1.2 drops contigs matching `/<mito_name>/` from its include regions (`modules/local/genome_blacklist_regions.nf:24`), so `Mito` would keep every `MT` read, with no error (the pipeline's schema, `nextflow_schema.json:174`: "otherwise this step is skipped").
- **12157105, the whole-assembly length.** It would make this the registry's one row whose gsize is not an effective size, against the registry's own stated convention.
- **Measuring the effective size on the fixture now.** The upstream figure, with its inference stated, is enough for a prototype's row; a measurement would be a new instrument for a single number.

## Known issue for the demo repository (not changed here)

The demo repository `gars-demo-v2` spells the yeast mito contig `Mito`: `tools/modality/workspace.py:220` and `api/app/live/sandbox.py:501` write it into their registry rows, `docs/v2-modalities.md:48` states the gsize as 12157105, and the 3 September ATAC run's log records `mito_name : Mito` (`docs/evidence/runs/epigenome-a/20260903-2106/atacseq/job.log:33`).
By the pipeline code above, that run most likely skipped the mitochondrial-read filter; this is read from its log and was not reproduced.
glitch-14 opens that as its own lane; this record changes nothing in the demo.

## What this does not close

- **The effective size is inferred**, not measured on the fixture (above).
- **No run has used this row.** The pad's first run on it is rung 3; its prepare will hash the files where they live, and a mismatch refuses as `reference_hash_mismatch`.
- **The pad must place the files.** The row names paths that exist only on the pad once its boot fetches the fixtures against their pins; on any other machine the menu shows the row unreadable, and `apply` refuses it.
- **RNA-seq on R64-1-1** is outside this registration.
- **One sentence of the registry's prose disagrees with its own cache paragraph.** "The derived cache" says to leave the column empty for a reference whose indices have not been built, while the cache paragraph after the table says a keyed directory that does not exist yet is still written and filled on the first run; this row, like the plan, follows the second. The sentence is left unchanged here.
- A review in a fresh context on the same machine and OS user is `independent_context`, not `external_human_seal`.

## Test

`tests/test_genome_registry_r64.py`, three tests, written first and red on the base registry at `37a8d94` (`Ran 3 tests … FAILED (failures=5)`: R64-1-1 absent from both menus, from the identity parse and from the numbering), then green with the row (`Ran 3 tests … OK`):
the `atacseq_bulk` and `chipseq_bulk` menus, through `configure.py`'s real command line, list R64-1-1 once with every identity and hash field, `MT` and `11624332`, and a cache key equal to the root plus the assay's pinned pipeline, the two keys different; `--select R64-1-1` resolves it; the menu numbers stay GRCh38 01, R64-1-1 02; the identity parse returns exactly the two identity rows, each table's body is counted from the file, and a planted hash-only row never becomes a genome.
Planted faults, each restored from a byte backup: `Mito` with 12157105, and `Mito` alone, each turn the test red (`AssertionError: 'Mito' != 'MT'`).
`python3 tests/check_contracts.py`: `14 contracts clean`; `python3 tests/check_counts.py`: `suite: 1211 tests`, `enforced=3`, clean (1208 at `37a8d94`).

## Status

Standing.
The row, the test and this record are the lane's, and its rulings glitch-14's; the protected change waits on the owner's yes in 0247, and the public push waits on the owner's own word.

## Date

2026-09-30
