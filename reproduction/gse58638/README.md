# Recompute the deposited half of the failed-replicate finding

**What it recomputes.** The deposit side of [docs/RESULTS.md](../../docs/RESULTS.md) row 3a: from the authors' four H3K27me3 z-score tracks in GEO GSE58638, each library's fraction of 10-bp bins above z>1 and z>2 and of 10-kb tiles whose exact mean is above them, set against the figures RESULTS.md quotes.
The per-library figures (FRiP, peaks per read) come from pipeline outputs that are not public, and stay quoted.

**The command**, from the root of a clone: `python3 reproduction/gse58638/recompute.py`.
It streams 8.8 GB from NCBI and stores nothing; it took about 17 minutes on GitHub's runner; it needs standard-library Python 3.9 or later.
`--from DIR` reads local copies of the four files instead (size and sha256 checked), and `--check-published` is the network-free binding CI runs on every push to main and every pull request.

**Exit codes** (from `recompute.py`): 0, the report is identical to `expected.txt`; 1, a science difference, named (a deposit's size or sha256 changed, a quotation moved, or the report differs); 2, refused (a short read, a bad format, zero records, or the network failing on the deposits); 3, only a public-metadata context line changed or could not be fetched.

**A green public run:** [GEO recompute run 36795272678](https://github.com/javrodriguez/genomics-agentic-research-system/actions/runs/36795272678), at commit `dbb434d`, printed "Identical to reproduction/gse58638/expected.txt: yes".

**The files**

- `recompute.py`: the command.
- `expected.txt`: the committed report the command must reproduce.
- `PREREG.md`: the pre-registration, frozen before any deposit byte was read.
- `VERDICT-step1.md`: step 1's dated verdict (IN KIND, adopted basis B1), kept beside the frozen pre-registration rather than appended to it.
- `PREREG-2.md`: the dated rule for what the binding asserts under that verdict.
- `PREREG-3.md`: the dated rule that binds two twice-rounded step-1 figures at one rounding.
- `test_recompute.py`: the reader, thresholds, stream, pins and exit codes, tested against the committed fixtures.
- `fixtures/`: three tiny bigWig files as hex text and the sources they were written from ([fixtures/README.md](fixtures/README.md)).
- `.gitattributes`: keeps the bytes the same on every platform, since the report embeds the script's git blob.

"glitch-14" in these records is the orchestrating Claude session, an AI agent that ran this build under Javier's delegation; "the geo-recompute lane" is a session it directed.
What the recompute binds, and what it cannot, is in [decision 0241](../../docs/decisions/0241-gse58638-deposit-recompute.md).
