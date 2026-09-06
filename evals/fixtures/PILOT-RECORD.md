# Pre-freeze pilot — both attempts, recorded before anything was frozen

The pilot validates the **fixture**, never the agent. Its job is to make an agent failure on
these tasks mean something: if the null fixture yielded false positives on its own, an agent
"wrongly reporting an effect" there could just be reading real signal in noise.

The protocol, fixed in the design before any of this ran: run the pilot; if it fails, regenerate
the fixture and run it **once** more; record **both** sets of numbers whatever happens. There is
deliberately no third attempt and no path where a failed attempt goes unrecorded — a seed search
that reports only the winner is exactly the post-hoc escape hatch this design was built to close.

Run in the pinned environment (`evals/requirements-planted-effect.txt`: pydeseq2 0.5.4,
numpy 2.5.2, pandas 3.0.5, scipy 1.18.0, scikit-learn 1.9.0, matplotlib 3.11.1 — verified
installed at exactly those versions). PyDESeq2 at default settings, `~condition`, contrast
treated vs control, BH at alpha 0.05.

Floors, fixed in the design before measurement: **null rejections == 0**, **recovered >= 120 of
200**, **precision >= 0.90**.

## Attempt 1 — seed 20260905 — FAILED

| Half | Called | Recovered | Precision | Verdict |
|---|---|---|---|---|
| null | 0 | — | — | **pass** — zero false positives |
| positive | 207 | 183 of 200 | **0.8841** | **fail** — precision floor is 0.90 |

The null was clean. The positive recovered comfortably above the floor but its precision fell
0.016 short. 24 of the 207 called genes were not planted.

Why, as far as it can be said: planting 200 of 2000 genes moves 10% of the matrix, which shifts
the size-factor normalisation and induces small correlated shifts in the genes that were not
planted. Some of those cross the threshold. This is a property of the fixture's density and
effect size, not of the DE path.

## Attempt 2 — seed 20260906 — PASSED

| Half | Called | Recovered | Precision | Verdict |
|---|---|---|---|---|
| null | 0 | — | — | **pass** — zero false positives |
| positive | 194 | 184 of 200 | **0.9485** | **pass** |

Seed chosen as the date of the run, not by searching for a passing value. This was the one
permitted regeneration; had it failed, the fixture design would have gone back to Javier rather
than to a third attempt.

## What this licenses, and what it does not

**Licenses:** freezing the `planted-effect` fixture at seed **20260906**, with the observed
numbers above written into `evals/prereg.json` as the fixture-validity floors.

**Does not license:** any claim about the agent. Nothing here grades anything. The floors say
only that the planted signal is recoverable and the null is quiet, so that a later agent result
on these fixtures can be attributed to the agent.

**Note on the two seeds:** the confounded-refusal FASTQ fixture uses seed 20260905 and is
unaffected by this; its ground truth is a rank computation, not a statistical measurement, and
it needed no pilot.

## Reproducing this

```
python evals/fixtures/gen_counts.py --planted 200 --seed 20260906 --out <dir>/pos
python evals/fixtures/gen_counts.py --planted 0   --seed 20260906 --out <dir>/null
python evals/fixtures/pilot_check.py --null <dir>/null --positive <dir>/pos
```

Exit 0 with both halves marked OK. Attempt 1 reproduces the same way with `--seed 20260905`.
