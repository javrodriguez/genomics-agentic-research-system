# What was done with each finding of `prefreeze-6.md`

The sixth and final fresh-context reviewer read the five-times-folded draft, review 5 and its
disposition, the driver, the graders, the runner, the analysis and the harness. Zero hits for every
term that would show it had reached outside its inputs. Its first line is the sha256 of the bytes it
read.

**Its verdict was: freeze it.**

It reproduced each of review 5's fixes rather than reading the disposition — it put the old reading
back and watched the guard go red, and it recomputed every number in the walk-coverage statement
from the script. It found no blocker, and it did not re-open any design decision the earlier passes
agreed not to touch.

It ruled independently on all six layer verdicts: six of six silent for the behaviour each probe
elicits. Every one of the six passes has agreed.

## Closed before the freeze, because both touch the freeze itself

**Its follow-up 3.** The regression guard for the recurring phrase read `prereg-draft.json` by name.
It was the only check in the harness that named a pre-registration file instead of going through the
loader — and at the freeze the file in force becomes `prereg.json` while the draft stays on disk
beside it. The guard would have gone on reading the draft and reporting on a file nothing grades
against. Fixed before the freeze because the freeze is the moment it would have started lying.

**Its follow-up 6.** Every line count in the file covers the five tasks this protocol scripts.
`confounded-design` carries its script from the first study, so the driver may send more lines than
this file names, and "both halves are walked" has an exception. Both the frozen file and the
protocol now say so. The numerator is unaffected: those lines were sent to the same system under
test in the first study, and its transcripts are what that task's case suite is built from.

## Carried as follow-ups, in files the freeze does not close

The reviewer's own reasoning for why these are follow-ups rather than blockers: they are all in
files the freeze does not close, all correctable without an amendment, and all re-derivable —
`run.py` regrades from committed transcripts, so a fix costs a re-run rather than a regrade
published side by side.

1. Index the verdict field rather than `.get()`, and add a test that grades the runner's own output
   instead of a hand-built results object.
2. Enumerate takes by their driver ledger, so the `aborted` a missing session file produces can
   actually be assigned.
3. Record `held` in the row written for an aborted turn.
4. Print that no task's probed behaviour is enforced, rather than an empty mapping.
5. Bind the plant to the counts per FIELD rather than per dict — swapping the two values inside one
   dict would pass both assertions today.
6. **Test the driver's outcome strings against the reader.** The harness never imports the driver;
   the reserved-label guard feeds it strings written by hand. The reviewer checked all eight the
   driver can write and they map correctly, but a reworded outcome would silently stop producing its
   label — which is exactly how the `aborted` defect arose.

That last one is the most valuable of the six and is written down here so it is not lost.

## The six passes, as a record

Thirteen findings, then two blockers, then one, then four, then two, then none. Every pass found
something real in the code the previous fold had touched, until this one. Ten blockers were found
and closed. Not one of them was found by the run that wrote the code.
