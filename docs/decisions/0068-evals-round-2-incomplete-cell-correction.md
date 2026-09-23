---
date: 2026-09-23
status: standing
kind: decision
touches:
  - docs/EVALS.md
symptoms:
  - a published Gap Study cell reads `0 of 3` while its results file grades one take
  - a summary names "one incomplete cell" without saying which
---
# EVALS: the round 2 incomplete cell is named beside the table, not edited into it

## Context

`docs/EVALS.md` publishes Gap Study round 2's table between its generated summary markers, as frozen and as verified.
The `template-adherence` row's `claude-sonnet-5` control cell prints `0 of 3`.
Round 2's results file for that task records the cell as `k: 0`, `n: 3`, one label (take 1, `incorrect`) and the state `incomplete — mechanical, 1 of 3`: two takes produced no gradable transcript.
The summary's own line says "incomplete: one cell, capped after three rehearsals, one graded", but it never names the cell, and a reader of the table sees three graded takes where one was graded.
It is the only cell of rounds 2 and 3 whose state is not `RAN`.
A blind evaluator in the GARS demo site rebuild found the mismatch on 23 September 2026; the site quotes neither figure.

## Decision

The owner ruled A on 23 September 2026: a dated correction line is added directly below the round 2 summary block, outside its generated markers, naming the cell and quoting its recorded state.
The table, round 2's code and every frozen file stay byte-identical.
Editing the cell inside the block would mean changing round 2's frozen table writer, which the study's rule forbids: results publish exactly as graded, and a flawed instrument is fixed in a pre-registered follow-up, never by amending what was frozen.

## What this does not close

- Round 2's table writer still prints an incomplete cell without its state; it is frozen, so the defect stays in its code and is recorded here.
- Round 3 has no incomplete cell; whether its own writer carries a cell's state was not tested by this change.

## Test

The correction's figures are the results file's own fields: `python3 -c "import json; c=json.load(open('evals/gap-study-2/results/template-adherence.json'))['cells']['claude-sonnet-5']['control']; print(c['k'], c['n'], len(c['labels']), c['labels'][0]['verdict'], c['state'])"` prints `0 3 1 incorrect incomplete — mechanical, 1 of 3`.
The same scan over every results file of rounds 2 and 3 finds no other cell whose state is not `RAN`.
`git diff` of this change touches no line between `<!-- gap-study-2:summary -->` and `<!-- /gap-study-2:summary -->`, and no file under `evals/`.

## Status

standing

## Date

2026-09-23
