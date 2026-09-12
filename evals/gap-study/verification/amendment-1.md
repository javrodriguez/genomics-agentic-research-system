# Amendment 1 — the freeze turned two of the study's own guards red, and they are repaired

12 September 2026. Published as an amendment, with before and after side by side, never corrected in place.
The machine-readable record is `amendments[0]` in `prereg.json`, which keeps each amended file's pinned sha256 from before this change beside the one now in force.

## What happened

Freezing switches on code paths that were dormant. `prereg.is_frozen()` becomes true and the per-half fixture pins fill. Two tests in the pinned harness asserted the behaviour of the **draft** rather than the behaviour of the check, and failed the moment the freeze landed.

Through those two tests, 24 of 103 mutation guards stopped firing. The split is evidence, not inference, and the full per-line run is at `verification/post-freeze-battery.txt`:

| how the guard failed | count | cause |
|---|---|---|
| control red before the mutation | 16 | their control class holds one of the two failing tests |
| mutated and still green | 7 | the sandbox reads the frozen file while the mutation edited the draft |
| mutated and still green | 1 | its premise was that the runner refuses a draft |
| mutation could not apply | 0 | nothing in the battery's targeting was stale |

## What changed

Two files, both pinned, both named by the study's own pin check.

- **`test_harness.py`** — the unpinned-half test asserts the note before the freeze **and** the refusal after it, by stubbing the frozen predicate, instead of asserting the draft's answer alone. The normalised-fixture test compares the block with the record the driver writes from the spec, instead of naming the three keys that block carries while the pin is null. Both now say the same thing in either state.
- **`mutations.py`** — seven guards edit the pre-registration the code actually reads, frozen or draft, rather than the draft alone. The guard that proves the runner refuses a draft removes the frozen file from its sandbox first, which is what puts the sandbox back into the state the guard names.

## What did not change

No criterion. No grader, threshold, label, fixture, operator script, marker, or pre-registered sentence. The pre-registration's content is untouched: `prereg-draft.json` still hashes to `18d65c17488f4114ac17c7d760491ff7300834ba0c4f35f5302d183ca0434d08`, the bytes review 23 read and the freeze recorded. Every other pinned file hashes to what the freeze pinned.

## Before and after

| | before | after |
|---|---|---|
| tests | 243, 2 failures | 243, OK |
| mutations | 103, 24 did not go red | 103, every one red when broken, 96 watched green first |
| pinned files | 2 mismatched | 54 re-hashed, clean |
| language guard, costs, ledger | clean | clean |
| first study | 44 tests OK, controls clean | 44 tests OK, controls clean |

## Both regrades, side by side

There are none, and that is checkable. No take had run, no results file existed, and the ledger was empty when this amendment was made. There is nothing to regrade, and the amendment is provably before any number exists.

## Why no review caught it

A reviewer may not run the freeze, because running it consumes the thing under review, and no pass rehearsed it into a scratch tree either. So the effect of freezing on the harness was unexercised until it was irreversible. That is a defect in the sequencing, not in the reviews. A study that freezes should run its own freeze into a throwaway copy and put the whole gate through the after-state first.

## One thing this amendment repeated, and the battery caught

A sentence written into this amendment tripped the language guard, and that single red made three lint-controlled guards report their control red before any mutation. The same shape as the sixteen above: one broken control silently disarms every guard that shares it. The word was changed and all three returned.
