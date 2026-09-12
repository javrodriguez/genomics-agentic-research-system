# Amendment 3 — the tests the checklist names are written, and the driver loop's tests stop needing the operator's harness

12 September 2026, after the 108 takes and before any result is committed.
Published as an amendment, with before and after side by side, never corrected in place.
The machine-readable record is `amendments[2]` in `prereg.json`.

## What happened

**Two tests the checklist names did not exist.**
Checklist line 10 runs `test_harness.py TwoMinuteRead`, and line 9 runs `test_harness.py NoRateNoBannedWord`.
Neither class was ever written, so both lines could only have been checked by hand.
The owner ruled the first is written as an amendment (Ruling 30).
The second is the same gap, and the operator wrote it under the same ruling, flagged there as the operator's reading rather than the owner's word.

**Six tests only ever ran on the operator's machine.**
The driver loop records the harness version by running `claude --version` before its first turn.
The tests replace the model turn and not that call, so on a machine with no harness installed they errored.
The CI runner is such a machine, and CI has been red on those six since they were written.

## What changed

Two files, both pinned.

- **`test_harness.py`**
  - `TwoMinuteRead`: the summary block of this study's section in `docs/EVALS.md` is at most 350 words, counted as a reader reads them; the section stands above the first study's; each `k of n` and each did-not-reach count in its table equals the results file; the limitations name each count requirement 7 names and the harness version the takes recorded; the three committed lines appear byte-identical; and the file has only gained lines since `50a2bdc` (Ruling 30).
  - `NoRateNoBannedWord`: the language guard over the section, `analysis.json`, the gate brief, and the bodies of every commit touching the study since the freeze, with a negative control proving the scan reads what it is given.
  - `ThePublishedAnalysisIsRegenerated`: `analysis.json` is exactly what `analyse.py --json` writes, so the scan reads a file something regenerates.
  - Each is required once a results file exists, and skipped with its reason before.
  - The driver loop's tests answer `claude --version` with the version the freeze recorded, inside the driver module only.
- **`mutations.py`** — five guards: a summary over the cap, a table count that is not the results file's, a committed line reworded, a banned word in the section, and a stale published analysis. The sandbox now carries `docs/EVALS.md`.
  In a tree with no results file those five raise `NotYetApplicable` and print as `n/a` with the reason, because the guards they break skip there and a mutation would come back green and read as a dead guard. With results present they are required, and a missing or broken section is a failure.

## What did not change

No criterion. No grader, threshold, label, fixture, operator script, marker, or pre-registered sentence.
No file that `run.py`, a grader or `analyse.py` reads.

## Before and after

| | before | after |
|---|---|---|
| tests | 245; on a machine without the harness, 6 errors | 257, OK here and on a fresh clone with no harness on PATH |
| mutations | 105 | 110, each red when broken, 103 watched green first |
| mutations, a fresh clone with no results and no harness | not run | 105 red when broken, the 5 over the section not applicable |
| checklist lines 9 and 10 | named two classes that did not exist | both classes exist and pass |

## Both regrades, side by side

Identical.
`run.py --all` on the amended bytes rewrites each results file byte-identical, and `amendments[2].regrades.results_sha256` records each hash.
