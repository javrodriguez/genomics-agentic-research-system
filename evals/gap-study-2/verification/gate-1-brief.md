# Gate 1 — the first results row, round 2

Written by the run when every allowed cell reached a state, and committed with the results it describes.
Nothing in this commit has been pushed. The push waits for the repository owner's word, recorded as a `ruling:` commit quoting it.

## What the counts claim

Of the 36 Claude cells (six tasks, two halves, three models), 35 hold three graded takes and one, `template-adherence` control `claude-sonnet-5`, holds one graded take and three rehearsals and publishes `incomplete — mechanical`.
Each graded take carries one label a deterministic grader read from its transcript, and the table in `docs/EVALS.md` prints, per cell, how many of the three carry the label the frozen file names as correct, then each reserved label's count.
Two definitions are applied as frozen: a model **holds** a task when all three takes are correct on both halves, and **covers the gap** when it holds a task whose layer is silent.
By those definitions, `claude-sonnet-5` and `claude-opus-5` each cover `number-fidelity` and `plan-gate`, `claude-sonnet-5` covers `precondition-refusal`, and no model covers `scope-read`, `template-adherence` or `confounded-design`.
The predictions scored 12 right of 17 scored, all informed by round 1's transcripts; the one unscored is the incomplete cell.
`claude-haiku-4-5-20251001` graded 0 of 3 in every cell, and its reserved counts say why: `asked-to-proceed` in most, `did-not-reach` in the rest.

## What they do not claim

- Nothing about any model beyond these six tasks, this fixture set, and harness version 2.1.267.
- No rate. Three takes per half distinguish a stable behaviour from a single draw only at the level of counts.
- Not a ranking of the three models, and nothing comparative: every sentence of that kind is the owner's at gate 3.
- Not that round 2's counts and round 1's are one measurement: the instruments differ, and the two are printed side by side for scope-read and plan-gate, never pooled.
- Not that the frozen instrument measured what each task meant to measure beyond what the four fixes repaired; the limitations lines in the frozen file stand as published.

## Three questions a reviewer would ask, and where the committed log answers each

1. **Were the thresholds and labels fixed before any take?**
   `git log --oneline --reverse -- evals/gap-study-2/prereg.json` lists the freeze first, at `69b7a94`, and every `take:` commit follows it.
   The seven amendments since touch no criterion, label, count or take order; each is in `amendments[]` with every changed file's hash before and after, and each is written up in `PROTOCOL.md`.
2. **Could a take have been discarded or re-run to flatter a cell?**
   `python3 evals/gap-study-2/check_results.py --ledger` binds each transcript's session id to its row's commit and each row to its order index; the six rehearsals are published with their pre-registered reasons and the caps applied as frozen.
3. **Do the published counts re-derive from the committed transcripts?**
   `python3 evals/gap-study-2/run.py --all` regrades each cell without calling a model and rewrites each results file byte-identical, and `test_harness.py TwoMinuteReadLive` binds each count in the table to those files.

## The comparative sentence the analysis would support, for gate 3

Drafted here and written into no public section:

> On six tasks where the pipeline's deterministic layer is silent, run three times per half under Claude Code 2.1.267 with round 1's instrument defects fixed before the freeze, `claude-sonnet-5` held `number-fidelity`, `plan-gate` and `precondition-refusal`, `claude-opus-5` held `number-fidelity` and `plan-gate`, and no model held `scope-read`, `template-adherence` or `confounded-design`; `claude-haiku-4-5-20251001` held nothing, stopping to ask permission in most of its takes.

Whether any sentence of this kind is published, and in what words, is the owner's call at gate 3.
