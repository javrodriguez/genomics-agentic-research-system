# What capped round 2's one incomplete cell

Re-derive every number on this page with:

```
python3 evals/gap-study-3/fixture_walk.py --finding
```

It exits non-zero if round 2's bytes stop saying what is written here.

## What was believed

Round 2 published one cell as incomplete: `template-adherence`, control half, on one model, after three
attempts were refused and the cap bound. The kickoff brief that proposed a round 3 read those refusals as
the fixture leaking its own shape — "the task's fixture leaks its own shape through the paths a model reads
on the way to the template" — and proposed re-cutting the fixture so that nothing the agent reads names the
study's checkout. The plan written after the pre-study carried that reading forward unchanged.

## What the bytes say

All three refused attempts carry the same refusal reason, `read-outside-the-checkout`, and **none of the
three names this repository's checkout at all**. Every absolute path in all three, classified at path
boundaries on both the normalised and the resolved form, falls into one of three classes: the session's own
run tree, a system location, or one of two places that carry no information about the study:

| Where the refused path came from | Distinct paths across the three attempts |
|---|---|
| the session's own scratch redirect — `/tmp/gars_finalize_<project>.json`, created by the agent redirecting a stage-00 command's output there and read back with `cat` | 3 |
| the harness's background-task output file — named back to the agent by Claude Code whenever a command is run in the background | 6 |
| this repository's checkout | **0** |

The fixture is not implicated. `template-adherence` is `kind: generated` on both halves: built inside the
run tree by the generator at take time, byte-identical across the halves, and recording no path of this
repository. The static check agrees — across all three tasks and both halves, no operator line names this
checkout and no generator writes a path of it:

```
python3 evals/gap-study-3/fixture_walk.py --static    →    static verdict: clean
```

## What that means for this round

Three things follow, and the third is the one that needs a decision.

1. **The re-cut would not have prevented any of the three refusals.** They were not about the fixture.
2. **The measurement was right and the causal story was wrong.** Three attempts were refused, the cap bound,
   and the cell is genuinely incomplete. What the refusals were *about* is what this page corrects.
3. **The same refusal is available to every cell in this round, not just that one.** Both sources are
   ordinary agent behaviour under this harness: writing a scratch file to a hard-coded `/tmp`, and running a
   command in the background. The take checker is pinned byte-identical for this round, so round 3 cannot
   change how it reads either of them.

What round 3 does about the third point is the owner's call. This page states the finding and takes no view.

## Why the checker reads them as it does

The rule exists for a good reason and is doing its job as written. A session that reads a path inside this
repository's checkout has been shown the study it is being measured on, and that is invisible in a verdict —
it would simply look like a pass. The rule catches that. It also catches two things that carry nothing about
the study, and it cannot tell them apart, because the only thing it can see is that the path is outside the
run tree.
