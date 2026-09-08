# What was done with each finding of `prefreeze-2.md`

A second fresh-context reviewer read the folded draft, the first review verbatim, and the record of
what was done with it. Same conditions as the first: a directory holding only the study's own files
and the system under test, no access to this repository or to anything about who commissioned it.

**Blindness verified, not asserted.** Its report and its full session log were searched for every
term that would show it had reached outside its inputs. Zero hits in both. Its first line is the
sha256 of the bytes it read, and that matches the draft.

**Its verdict was: do not freeze.** Two blockers, three one-line contradictions. Both blockers are
now closed and all three contradictions fixed. It also ruled independently on all six layer verdicts
and agreed with every one.

## Blocker 1 — a wait point with no answer, closed

Stage 00's contract requires template T3b unconditionally, and T3b ends by asking for the raw data
path. That makes it a wait point by the definition this study pins, and the driver sends no line
past an unheld marker.

Checked against the contract and against the committed walk. The agent sent T3b and T4a in a single
turn and never waited — but only because the operator's first line already carries the path. An
agent that follows the contract and stops at T3b would leave the next marker unheld, the driver
would send nothing further, and the take would publish as `did-not-reach`: a model failure the model
did not earn, across three tasks and half the planned takes.

This is the same class as the marker-case defect the first review stopped the freeze for, in the one
place Ruling 4 did not reach. Carrying it as open because it changes no number that exists today was
the wrong test — it changes numbers that do not exist yet, which is the only kind this file governs.

The script now carries a pre-registered recovery on that turn: if the reply is waiting at T3b and
the next marker is not held, the driver answers it ONCE with the same path the first line already
gave, and re-checks. It is data in the pre-registration, never the driver's judgment, and it sends
nothing when the agent does not wait. Six recovery steps, across the three stage-00 tasks and both
halves. `test_harness.py WaitPointsAllHaveAnAnswer` holds it.

## Blocker 2 — the field the study's headline count reads, closed

The fold for the first review's F2 closed the definition and moved the problem: the verdict the
analysis reads became unconstrained text with three different spellings, `covers the gap` named the
behaviour field rather than the verdict field, and one task read `not established`.

Whether the central count is three, five or six turned on a string comparison nobody had
pre-registered.

The verdict is now one of three fixed values, `covers the gap` names the verdict field explicitly,
and the reviewer's own Part 4 ruling is recorded as `confounded-design`'s layer evidence in place of
the grep the protocol forbids as a verdict. `test_harness.py` asserts every task's verdict is one of
the pre-registered values.

## The three contradictions, each a line

`precondition-refusal.differs_in` described the exit-1 branch its own note rules out. Rewritten to
name the absence that exits 3.

`number-fidelity.differs_in` still named the generator as the source of the true counts, which the
rewritten `counts_note` had just denied. Rewritten to name `cmd_inspect` and call the manifest a
cross-check.

`plan-gate` promised "nothing is executed" in two places while the contract's step 7 executes
immediately after `approve`. Closed by Ruling 6, below.

## Two findings the first review missed, both folded

**A personal name published into every `not run` table cell.** The study's own artifacts now name
the role. Recorded as Ruling 5. The repository is public and carries its owner's byline already;
this is a default the owner can set aside by naming themselves anywhere they want to.

**The control half could have executed, on this machine and on a paid cloud queue.** Recorded as
Ruling 6. The bound is an omission, not an invention, and it was verified before it was relied on.

## Carried open, and named

The `did-not-reach` clause naming which marker; a reach-marker vocabulary admitting T6; a
`scope-read.declined` decision; `holds` phrased over halves; `probed_behaviour` as a list; marker
provenance; the guard's file scope; the scoreable prediction count; walk coverage stated as it is;
and a freeze checklist distinguishing nulls-to-fill from nulls-by-design.

They change no number and none is a blocker. They are listed so a reader can see they were raised.

## The study is still not frozen

The folded bytes differ from the bytes this reviewer read, and the protocol requires a later review
covering that diff. A third pass is the next step, not the freeze.
