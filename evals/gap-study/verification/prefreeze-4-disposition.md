# What was done with each finding of `prefreeze-4.md`

A fourth fresh-context reviewer read the thrice-folded draft, all three earlier reports and
dispositions, the driver AND the graders. Zero hits for every term that would show it had reached
outside its inputs, in report and session log. Its first line is the sha256 of the bytes it read.

Its verdict was **do not freeze**: four blockers, all small, all in code changed by the previous
fold. It said plainly that the downward trend is real, that review 3's blocker is genuinely closed
at both instances, and that it looked for a third instance and found none.

It ruled independently on all six layer verdicts and agreed with every one, as all three earlier
passes did.

## F1 — one task could not be driven at all

The driver substitutes `{project}` and `{source}` and nothing else. One task's probe line carried
`{wrong_files}` and `{wrong_samples}`, so the driver would have raised on that turn and the task
could not have produced a single take. Eighteen takes.

Underneath it, a design fault the reviewer named precisely: the frozen file carried TWO candidate
lines for that turn — a template in `line` and the resolved text in a second field — and identified
neither as the one sent. The graders read the second field; the driver read the first.

Reproduced before fixing. Each turn now carries exactly one line, with literal numbers, and the
second field is gone. `test_harness.py EveryOperatorLineRenders` asserts every one of the 38 lines
the driver may send renders with only the two substitutions it makes, and that no turn carries a
second candidate.

## F2 — a published quantity that nothing could produce

`aborted` is pre-registered on all six tasks and the protocol promises its counts per cell. Nothing
could assign it: the driver writes it, and the label reader had no branch for it, so a process that
died after the first agent turn published as `did-not-reach`.

That is Ruling 4's own defect one step downstream — a take wearing a label it did not earn, because
the mechanism that should have assigned the right one did not exist. `aborted` now has a producer,
including the missing-session-file case, and a test asserts every reserved label can be produced.

## C2 — the fourth pass, and the third time it was reported closed

"Nothing is executed" survived at the top level and in a grader's own docstring. The previous
disposition's mechanical check was scoped to the task object; the stale copies were outside it.

Checked across the whole file this time, not one object: the phrase now appears once, inside the
record of its own withdrawal. The grader's heading is rewritten to describe what the control half
can actually do and to point at the bound rather than assert the claim.

## F3 — the frozen file said the walks fixed every operator line

They did not. A walk stops before the probe, and the walks' agent never waited at either recovery
point because the operator's first line already carried both the title and the path. Twelve of the
38 lines the driver may send are frozen without ever having been sent to the system under test.

The claim is replaced by what the walks actually fixed, and by a companion field naming what they
did not and why.

## Items 5 to 10, each a line

The two exceptions to "the graders locate the probe by matching" are named. Two verdict strings
outside the vocabulary their own object declares are brought inside it. `layer.observed` had three
shapes across six tasks and now has one. The carried task's evidence cites all three rulings rather
than one made two folds ago. The driver's own docstring stated the rule its recovery breaks. A
lowercased marker constant and a dead variable are gone. The note describing one recovery now
describes both.

## Carried open, correctly

Whether the deterministic layer loads at a session opened at the repository root — the frozen file
pre-registers the condition and not the question. The `did-not-reach` clause naming which marker; a
reach-marker vocabulary admitting T6; `holds` phrased over halves; `probed_behaviour` as a list;
marker provenance; the scoreable prediction count; that the write detector is weaker than the
system's own guard in the direction that credits a violating agent. None moves a number that exists.
