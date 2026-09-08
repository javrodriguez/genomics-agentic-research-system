# What was done with each finding of `prefreeze-5.md`

A fifth fresh-context reviewer read the four-times-folded draft, all four earlier reports and
dispositions, the driver, the graders, the runner, the analysis and the test harness. Zero hits for
every term that would show it had reached outside its inputs. Its first line is the sha256 of the
bytes it read.

Its verdict was **do not freeze — two things, and both are one line.** It said plainly that it found
nothing wrong with the design decisions the earlier passes agreed not to touch and was not
re-opening any, that the pinning is byte-exact at thirteen quotes and twenty-eight markers, and that
the answer the study is heading toward is one the protocol pre-commits to publishing.

## B1 — the analysis read the run's expectation, not the verdict

`covers the gap` is defined over `layer.observed_for_probed_behaviour`. The runner never carried
that field into the results file and the analysis read `layer.expected` instead.

Those diverge on exactly one task. `precondition-refusal` EXPECTED enforced, and is silent for the
behaviour its probe elicits — which is why the per-behaviour distinction was introduced two folds
ago. So the published table would have carried the word `enforced` beside every reviewer's ruling of
`silent`, and **a model holding all six tasks would have published as covering five.** A wrong
number in the central column.

Reproduced before fixing. The runner now carries the verdict and the probed behaviour; the analysis
reads the verdict. A test pins the divergence by name and goes red if the expectation is read again.
The old test helper wrote only `expected`, which is how it pinned the very behaviour that was wrong.

## B2 — a false count in the frozen file

The statement about what the walks did not fix said twelve of thirty-eight lines. It is twenty-two:
ten probe lines and twelve recovery lines. The earlier number counted the recoveries and left the
probes out.

The numbers are now counted from the script rather than written by hand, which is why they moved
twice: once when the claim was false in the other direction, and once when it was merely wrong.

## The four non-blocking items, in the same commit as asked

**The fifth appearance of the same phrase.** A label gloss still said `held` meant "no approve,
nothing executed", eight lines above a heading rewritten to say that claim is not asserted there.
The gloss now says what the grader actually reads.

**`aborted` had a reader and a producer narrower than its definition.** The label is defined as the
process dying after the first agent turn; the driver wrote it only for the recovery turn and for a
missing session file. A scripted turn exiting non-zero mid-take fell through to the marker check and
published as `did-not-reach`. Both count against holding so no number moved, but the published
counts would have been wrong about which failure happened.

**The regression guard for that recurring phrase was scoped to one object and to the wrong string.**
The disposition said it had been checked across the whole file; the test in the repository was not.
It now reads the whole file and the short phrase.

**Nothing bound the planted numbers to the count fields.** The previous fold moved them into
literals while the grader reads them from two count fields. They agree today; if they drifted, the
positive half would plant the true counts and every take would grade `corrected` — a task passing
itself. Two assertions now hold them together.

## Carried open, correctly

Whether the deterministic layer loads at a session opened at the repository root; the
`did-not-reach` clause naming which marker; a reach-marker vocabulary admitting T6; `holds` phrased
over halves; `probed_behaviour` as a list; marker provenance; the scoreable prediction count; that
the write detector is weaker than the system's own guard in the direction that credits a violating
agent. None moves a number that exists.
