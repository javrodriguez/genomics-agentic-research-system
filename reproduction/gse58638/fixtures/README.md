# Fixtures for test_recompute.py

Three tiny bigWig files, each committed as hex text (`<name>.bw.hex`, 32 bytes a line), and the
two text sources they were written from (`<name>_source.tsv`). The text source is the truth: the
reader must return exactly its records, with each value taken through float32.

| File | Section type | What it holds |
|---|---|---|
| `bedgraph` | 1 (bedGraph) | two chromosomes (60,000 and 12,345 bp), three data blocks; values exactly 1.0 and 2.0, and float32 neighbours of 1.0; a record across the 10-kb tile edge; a NaN; a +inf; a span that is not a multiple of 10; a tile whose mean is exactly 1.0; the last partial tile |
| `fixedstep` | 3 (fixedStep) | 1,200 contiguous 10-bp steps on chrA across the tile edge, with NaN, 1.0 and 2.0; 50 5-bp steps on chrB |
| `empty` | none | a header and chromosome list with zero records: the zero-record refusal |

The truncated, bad-magic, changed-size and one-byte-changed copies are derived from these by the
tests at run time.

## How they were made

On 30 Sep 2026 by the geo-recompute lane, with **pyBigWig 0.3.26** (libBigWig) on Linux, from the
text sources, never by `recompute.py`:
`addHeader([("chrA", 60000), ("chrB", 12345)], maxZooms=2)`, then `addEntries` in chunks of 100
records (bedGraph) or one fixedStep run per chromosome.

The plan asked for fixtures made by UCSC's own tools (`bedGraphToBigWig`, `wigToBigWig`). The
cloud machine that built them could not reach hgdownload.soe.ucsc.edu (egress policy), so an
independent writer was used instead; the reader's agreement with UCSC's reference reader on the
four real deposits is recorded separately (decision 0241). Regenerating them with UCSC's tools
from the same text sources should leave every test green; only `FIXPINS` in the test changes.

Why hex: the repository's pre-commit gate refuses binary content it cannot scan completely.
