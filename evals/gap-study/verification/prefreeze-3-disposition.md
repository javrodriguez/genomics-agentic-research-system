# What was done with each finding of `prefreeze-3.md`

A third fresh-context reviewer read the twice-folded draft, both earlier reports, both dispositions,
and the driver itself. Same conditions: only the study's own files and the system under test. Zero
hits for every term that would show it had reached outside its inputs, in report and session log.
Its first line is the sha256 of the bytes it read.

**Its verdict was: do not freeze.** One blocker of substance and four contradictions the previous
fix created or left. All are now closed.

It ruled independently on all six layer verdicts and agreed with every one, as both earlier passes
did.

## The blocker — the recovery was installed at one of two wait points

Stage 00 reaches TWO templates that end by asking before the probe: T1, which asks for the project
title, and T3b, which asks for the raw data path. Both are required unconditionally, so both are
wait points by the definition the study pins.

The previous fold installed a recovery at T3b only. An agent that stops at T1 — one turn earlier —
leaves the menu marker unheld, the driver sends nothing further, and the take publishes as
`did-not-reach`. Same three tasks, same both halves, half the planned takes, same label the model
did not earn.

The reviewer found it by reading the contract's Process rather than the walk, because the walk's
agent never waited at either point: the operator's first line already carried the path AND the
title. Twelve recovery steps are now pre-registered, covering both wait points across the three
tasks and both halves.

## C3 — the fix moved the index the graders count by

A recovery adds a real operator turn to the transcript. The graders counted operator turns to find
the probe, so a recovery would make them read one turn EARLY — and on `number-fidelity` that means
taking the stage's own printed counts for the agent's answer to a planted wrong count. A false
`corrected`, produced by the operator's own repair.

The graders now locate the probe by MATCHING its pre-registered text. That is immune to a recovery
and to anything else the operator ever has to send, and when the probe cannot be found the grader
gets nothing rather than a guess.

Twenty tests had to be rewritten to send the real script lines, because they had been sending
placeholders. Seventeen of them failed the moment the graders stopped counting — correctly.

## C4 — the recovery turn's exit code was swallowed

A budget overrun on the recovery turn would have left the marker unheld and published
`did-not-reach`. That is Ruling 4's defect — an operator-side failure wearing a label the agent did
not earn — reintroduced by the fix for Ruling 4's own class. The recovery turn's exit code is now
read like every other turn's: a timeout is `timed-out`, any other non-zero exit is `aborted`.

## C1 — the protocol still stated the rule the recovery breaks

The Wait points section said the driver sends no line past an unheld marker and did not mention the
recovery. That is the document a reimplementer reads for what the driver may send. It now describes
the recovery, both wait points, the at-most-once rule, and that a recovery turn is not a numbered
operator turn.

## C2 — the withdrawn claim, standing in a third place

"Nothing is executed" survived in a third field, beside its own retraction and beside a correctly
rewritten duplicate. Removed. This is the third pass at which this exact pattern has been found: a
corrected claim left standing next to the sentence correcting it. Checked mechanically this time —
the phrase now appears once in the whole task, inside the record of its withdrawal.

## C7, C6, C8 — one line each

The execution bound named one residual and there are two: a machine with a scheduler, and a plan
whose Execution line says login-node, which does not go through the scheduler at all. Ruling 6's
"and now cannot" was true for one venue and overstated for the other, and now says so.

The recovery's marker is brought under the same rule as every other marker. The permission mode,
permission-prompt setting and working directory every take runs under were driver constants and are
now pre-registered: a take under a different permission mode is a different experiment, and a reader
cannot check a constant that lives only in code.

## Carried open, correctly

The `did-not-reach` clause naming which marker; a reach-marker vocabulary admitting T6; a
`scope-read.declined` decision; `holds` phrased over halves; `probed_behaviour` as a list; marker
provenance; the guard's file scope; the scoreable prediction count; and that `confounded-design`'s
`reach_turn` means a raw transcript index where the other five mean an operator-turn index. None
moves a number.

## Still not frozen

The folded bytes differ from what this reviewer read, so the protocol requires a further pass
covering that diff.
