# Validity follow-ups, first tier: pre-registration, second part

Written on 1 October 2026 (UTC), by the validity-followups build lane, after the first run of the four read-only
counts. `PREREG.md` is unchanged and still governs every count; no rule in `rules.py` changes, and no count
published in `RESULTS.md` is produced by anything this file adds.

## Why this exists

The first run printed zero for F-01, F-06 and F-04 in every round. The threat this lane was briefed against is a
count that reads zero silently, because a filter dropped the takes or a path matched nothing. `PREREG.md` already
refuses a round with no published take or no readable take, and binds every read transcript to its published
sha256; it does not show that the turns a rule reads are the turns the round's grader read.

## What is added

**`fidelity.py`, a verification, not a follow-up.** For every take in the scope of F-01, F-07, F-06 and F-04,
it loads the transcript exactly as the counts do (`rules.load_turns`), runs the round's own grader on those
turns with the take's own driver ledger (`driver-ledger.json` beside the transcript, a file `PREREG.md` did
not list), marking harness records first where the round's `labels.py` has that step (rounds 2 and 3, as their
`run.py` does), and prints how many re-grade to the label the round's results file publishes. It also prints
how many tool calls follow the probe across the read takes, so a zero count over takes that ran no tool after
the probe reads as that, not as a rule that saw nothing. It publishes no label and changes none; a take that
re-graded differently would be named, not counted.

Its table is published in `RESULTS.md` under "Fidelity", re-derived by `fidelity.py --check`.

## A widened scope on F-05

`PREREG.md` (section F-05) names the round 2 texts. While writing decision 0219 the same docstring line was
found in round 3's grader (byte-identical) and round 1's (other spacing), and the same pre-registration sentence
in `evals/gap-study-3/prereg.json:452`. The erratum names them too, and `f05_check.py` checks them. No frozen
file changes.

## Nothing else

No rule, window, word list, scope or output format of `PREREG.md` changed after a take was read.
