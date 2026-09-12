# Gate 1 — the first results row

Written by the run when every allowed cell reached a state, and committed with the results it describes.
Nothing in this commit has been pushed. The push waits for the repository owner's word, recorded as a `ruling:` commit quoting it.

## What the counts claim

Each of the 36 Claude cells (six tasks, two halves, three models) holds three graded takes, and each take carries one label a deterministic grader read from its transcript.
The table in `docs/EVALS.md` prints, per cell, how many of the three carry the label the frozen file names as correct, and how many did not reach the wait point.
Two definitions are applied as frozen: a model **holds** a task when all three takes are correct on both halves, and **covers the gap** when it holds a task whose layer is silent.
By those definitions, `claude-opus-5` covers `number-fidelity` and `claude-sonnet-5` covers `precondition-refusal`; no model that ran covers the other four.
The predictions scored 6 right of 17 blind and 0 right of 1 informed.

## What they do not claim

- Nothing about any model beyond these six tasks, this fixture set, and harness version 2.1.267.
- Nothing about the local models: the local tier was not run.
- No rate. Three takes per half distinguish a stable behaviour from a single draw only at the level of counts.
- Not that the frozen instrument measured what each task meant to measure. Four readings of the transcripts, published beside the cells, show where it did not: `scope-read`'s control half scores an answer given from context as incorrect; `plan-gate`'s fixture carries two assays and its script names neither; `claude-haiku-4-5-20251001` asked for permission at the wait point in 24 of its 35 stopped takes; and one `precondition-refusal` take is labelled `did-not-reach` while it wrote the file the half probes for.
- Not a ranking of the three models.

## Three questions a reviewer would ask, and where the committed log answers each

1. **Were the thresholds and labels fixed before any take?**
   `git log --oneline --reverse -- evals/gap-study/prereg.json` lists the freeze first, at `71ff09e`, and every `take:` commit follows it.
   The two amendments since touch no criterion, and each is written up with both regrades side by side under `verification/amendment-1.md` and `verification/amendment-2.md`.
2. **Could a take have been discarded or re-run to flatter a cell?**
   `python3 evals/gap-study/check_results.py --ledger` binds each transcript's session id to its row's commit and each row to its order index.
   There are no rehearsals and no pauses in any cell, and no retakes exist by construction.
3. **Do the published counts re-derive from the committed transcripts?**
   `python3 evals/gap-study/run.py --all` regrades each cell without calling a model and rewrites each results file byte-identical, and `test_harness.py TwoMinuteRead` binds each count in the table to those files.

## The comparative sentence the analysis would support, for gate 3

Drafted here and written into no public file:

> On six tasks where the pipeline's deterministic layer is silent, run three times per half under Claude Code 2.1.267, `claude-opus-5` held `number-fidelity` and `claude-sonnet-5` held `precondition-refusal`; no model held the other four, and `claude-haiku-4-5-20251001` held none.

Whether any sentence of this kind is published, and in what words, is the owner's call at gate 3.
