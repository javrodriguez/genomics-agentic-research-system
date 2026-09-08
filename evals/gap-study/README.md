# The Gap Study

Where the deterministic layer does not cover a failure mode, which model catches it, and in how
many of n takes?

**Status: pre-freeze. Nothing here has been graded yet.**

Read `PROTOCOL.md` first. It carries the design, the definitions, what counts as a take, and the
rulings recorded so far.

## The documented commands

Once the pre-registration is frozen, these are the whole road from a fresh clone:

```
python3 evals/gap-study/run.py --all                                  # grade every committed take
python3 evals/gap-study/analyse.py                                    # the pre-registered comparison
python3 evals/gap-study/check_results.py [--ledger|--controls|--regrade]   # bind results to bytes
python3 evals/gap-study/check_take.py <transcript> --task <id> --half <h>  # validate one take
python3 evals/gap-study/drive.py --task <id> --half <h> --model <id> --take <k>   # drive one take
python3 evals/gap-study/test_harness.py [--mutations]                 # every guard, red first
```

Grading calls no model and opens no connection. It reads committed transcripts with the Python
standard library and nothing else.

## The layout

| Path | Holds |
|---|---|
| `PROTOCOL.md` | the design, the definitions, the rulings |
| `prereg-draft.json` → `prereg.json` | the frozen file every other module reads |
| `walks/` | pre-freeze walks through the real front door, stopped before the probe |
| `takes.json` | one row per pre-registered take, append-only |
| `transcripts/<task>/<half>/<model>/<take>/` | the session file, copied verbatim, with its driver ledger |
| `rehearsals/` | attempts refused before a first agent turn, kept, never graded |
| `results/<task>.json` | what the graders re-derive from committed transcripts |
| `analysis.json` | the pre-registered comparison's output |
| `cases/<task>.json` | the hand-labelled case suite each grader is tested against |
| `controls/` | the negative-control runs that classify a layer as enforced |
| `local-model/` | the recipe, the fit proofs, the server logs, the three quoted lines |
| `verification/` | the pre-freeze review and the final verifier reports, committed whatever they say |
| `COSTS.md` | tokens by class, wall clock, and every recorded pause |

## Relationship to the first study

`evals/` is the first evaluation and stays exactly as it was.
Its pinned files are never edited — its own checker re-hashes them against the frozen bytes and
would go red.
This study imports its transcript parser and its count reader rather than inventing new ones, so a
comparison between the two means something.

`confounded-design` here is the first study's task, carried over verbatim and referenced by its
pinned shas, now run across the three Claude tiers with three takes a half instead of one.

## What this study will not say

No rates. No percentages. No ranking of models.
Nothing about a local model beyond the labels its takes earned, and nothing implying it costs
nothing to run.
No claim about where a lab's data goes.

The counts are the claim, and the commands above are how a sceptical reader checks them.
