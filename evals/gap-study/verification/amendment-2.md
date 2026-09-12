# Amendment 2 — the filled ledger turned the language guard and five tests red, and they are repaired

12 September 2026, after the 108 takes and before any result is committed.
Published as an amendment, with before and after side by side, never corrected in place.
The machine-readable record is `amendments[1]` in `prereg.json`, which keeps each amended file's pinned sha256 from before this change beside the one now in force.

## What happened

The run produced the first real take records, and two instruments had never read one.

**The language guard read take records as claims.**
It scanned every `driver-ledger.json` and `scrub.json` the driver wrote, and its `k / n` rule matched the model and take segments of the paths recorded inside them.
Those files are records the pinned driver writes, not sentences the study publishes.

**Tests written against an empty study met a full one.**
Three tests built take folders inside the study, and the run's real folders collided with them.
Five tests pass ledger row 0 to the take checker and expect it to stop at "no ledger row 0", which was the answer while the ledger was empty.
With 108 rows, row 0 exists, so the same call walked on into the ledger's git history: a different path in this repository, and an error in a mutation sandbox, which carries no git.
Through those five, 21 mutation guards reported their control red before any mutation.

**The take loop's commit subjects carried progress counters.**
Checklist line 9 scans the bodies of every commit touching the study since the freeze, and 109 take commits, already pushed, carry the take's position in the run as a `k / n` counter in their subject.
The loop that wrote them is the operator's, not the pinned driver, and the guard's commit scan was never part of its gate, so the counters went out unread.

## What changed

Four files, all pinned, all named by the study's own pin check.

- **`lint_language.py`** — `driver-ledger.json` and `scrub.json` under `transcripts/`, `rehearsals/` or `pauses/` are not scanned. Every other file in those folders, and everywhere else, still is.
- **`language-allowlist.json`** — two excusals in `COSTS.md`, each pinned to its exact line: an input-token count on the `confounded-design` row for `claude-opus-5`, and a wall clock on the `precondition-refusal` control row for `claude-sonnet-5`. And 111 excusals, one per exact subject line of those take commits. Pushed history is not rewritten, so each line is excused rather than the rule narrowed, and an edited line brings its finding back.
- **`test_harness.py`** — `TheTakeRecordsAreRecordsNotClaims` binds the exclusion both ways. The three colliding tests build their folders in scratch trees. The five row-0 tests read an empty ledger they own, not the study's live one.
- **`mutations.py`** — two guards for the exclusion: one that ignores where the file is, one that swallows every JSON file.

## What did not change

No criterion. No grader, threshold, label, fixture, operator script, marker, or pre-registered sentence.
No file that `run.py`, a grader or `analyse.py` reads.

## Before and after

| | before | after |
|---|---|---|
| language guard, files | 111 findings across 289 inputs: 109 in take records, 2 in `COSTS.md` | clean |
| language guard, commit bodies since the freeze | 111 findings in 109 take-commit subjects | clean, 115 excused lines on record in all |
| tests | 243, 2 failures | 245, OK |
| mutations | 105, 21 did not go red, each with its control red first | 105, each red when broken, 98 watched green first |

The two batteries are `verification/amendment-2-battery-before.txt` and `verification/amendment-2-battery.txt`.

## Both regrades, side by side

Identical.
`run.py --all` on the amended bytes rewrote each of the six results files byte-identical to what the frozen instrument wrote, and `amendments[1].regrades.results_sha256` records each hash.
No cell moved, because nothing a grade is computed from was touched.

## What this amendment did not repair

Ten mutations are still listed as not applicable, with reasons written before any take existed, such as "no take has run" and "no results file exists".
With the takes run, several of them could now apply.
That is recorded here rather than folded into this amendment.

## The shape, a second time

Amendment 1 was a one-way change switching on code nobody had run in its after-state: the freeze.
This is the same shape with a different switch: the first real take records.
A guard or test written while a folder is empty encodes "empty" without saying so, and the first real rows are when that comes due.
