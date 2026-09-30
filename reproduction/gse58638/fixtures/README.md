# Fixtures for test_recompute.py

Three tiny bigWig files, each committed as hex text (`<name>.bw.hex`, 32 bytes a line), and the
two text sources they were written from (`<name>_source.tsv`). The text source is the truth: the
reader must return exactly its records, with each value taken through float32.

| File | Section type | What it holds |
|---|---|---|
| `bedgraph` | 1 (bedGraph) | two chromosomes (60,000 and 12,345 bp), four data blocks; values exactly 1.0 and 2.0, and float32 neighbours of 1.0; a record across the 10-kb tile edge; a NaN; a +inf; a span that is not a multiple of 10; a tile whose mean is exactly 1.0; the last partial tile |
| `fixedstep` | 3 (fixedStep) | 1,200 contiguous 10-bp steps on chrA across the tile edge, with NaN, 1.0 and 2.0; 50 5-bp steps on chrB |
| `empty` | none | a header and chromosome list with zero records: the zero-record refusal |

The truncated, bad-magic, changed-size and one-byte-changed copies are derived from these by the
tests at run time.

## How they were made

`bedgraph` was written on 30 Sep 2026 by UCSC's own writer, `bedGraphToBigWig` v2.10 (macOSX.x86_64
build, sha256 `ba47840edbecb6c4cd7c9a2e09e7b18efc89f4533ddc04e17268078a3a42ca5a`), from its text source
with the source's `#` lines removed and the chromosome sizes chrA 60000 and chrB 12345. It holds four
zlib-compressed data blocks, all of section type 1.

`fixedstep` and `empty` were written the same day with **pyBigWig 0.3.26** (libBigWig) on Linux:
`addHeader([("chrA", 60000), ("chrB", 12345)], maxZooms=2)`, then one fixedStep run per chromosome.
UCSC's writers cannot make either faithfully:
- `wigToBigWig` (v2.10, sha256 `ae626a62d9f262569c7e17700b9edfcb38a2d41ea7ae0e79dedee3d5739bec75`)
  writes the fixedStep source's records correctly, but its header's total summary says 12,390 bases
  covered where the file holds 12,250; the 140 extra are all on chrA's 10-bp run, with or without
  its NaN steps. This reader refuses that file ("graded 10750 bases (+1500 NaN) but the header
  covers 12390"), which is correct: the header is the only independent count a file carries, and
  it disagrees with the records.
- neither `bedGraphToBigWig` nor `wigToBigWig` writes a file with zero records (both exit 255 on
  empty input), so the zero-record refusal needs another writer.

UCSC's own reader, `bigWigToBedGraph`, returns exactly the text source for `bedgraph` and
`fixedstep`, record for record, and refuses `empty`, as this reader does (decision 0241).

Why hex: the repository's pre-commit gate refuses binary content it cannot scan completely.
