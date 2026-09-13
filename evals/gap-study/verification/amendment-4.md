# Amendment 4 — the guards checklist line 12 names are applied, a moved criterion is refused, and the bill stops claiming evidence it does not have

12 September 2026, after the final verifier's first report.
Published as an amendment, with before and after side by side, never corrected in place.
The machine-readable record is `amendments[3]` in `prereg.json`.

## What happened

The final verifier's first report (`verification/2026-09-12-95c4923.md`) ruled checklist line 12 FAIL.
Six of the mutations the line names were listed as not applicable, with reasons written before any take existed.
Five could apply once the takes ran, and one of them had nothing behind it: no check compared the frozen file with its freeze, so a criterion edited after the freeze was refused only by a reader running `git diff`.

The same report ruled line 13 FAIL, because no take carries a record of the environment it ran under.
Reading why showed something worse than a missing record: `COSTS.md` and `costs.py` claimed that record as the evidence for the $0 (Ruling 34).

## What changed

- **`check_results.py`** — its default run compares the frozen file with the commit that introduced it. Only the amendments list and the pinned sha256 values an amendment records may differ, and each moved sha256 must chain from the freeze's pin through every amendment to the pin in force. A shallow clone, or a repository without that commit, is refused.
- **`costs.py`** and **`COSTS.md`** — the $0 is stated as the operator's statement, and each says that no committed file records the environment or the credential a take ran under, and what it said before.
- **`test_harness.py`** — `TheFrozenFileMovesOnlyByAmendment`, including this repository's own frozen file against its freeze; `TheLedgerBindsEachTranscriptToItsRow`, which plants a transcript from another row's session and a row committed after its transcript.
- **`mutations.py`** — four guards applied: a moved threshold after the freeze, a transcript whose session id is not its row's, a row committed after its transcript, and a doctored results file re-graded. The head-tree guard carries the name the checklist gives it. A local transcript with no server log stays not applicable, because the local tier was dropped at gate 2.

## What did not change

No criterion. No grader, threshold, label, fixture, operator script, marker, or pre-registered sentence.
No file that `run.py`, a grader or `analyse.py` reads.

## Before and after

| | before | after |
|---|---|---|
| tests | 257 | 266, OK |
| mutations | 110, 10 not applicable | 114, each red when broken, 107 watched green first |
| mutations, a fresh clone with the results and no harness | 105, 5 not applicable | 114, each red when broken, 107 watched green first |
| a criterion moved after the freeze | refused by nothing | refused by `check_results.py` |

## Both regrades, side by side

Identical.
`run.py --all` on the amended bytes rewrites each results file byte-identical, and `amendments[3].regrades.results_sha256` records each hash.
