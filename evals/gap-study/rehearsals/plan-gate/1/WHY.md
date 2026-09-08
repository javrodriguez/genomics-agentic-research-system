# Rehearsal, not a walk: an operator-side mechanical failure

This attempt was driven with a per-turn budget of 280 seconds against a pre-registered budget of
900. The agent was still drafting the plan when the driver cut the turn, and the ledger recorded
`timed-out`.

That label says nothing about the agent. It says the operator set the budget too low.

Under this study's rules a `timed-out` transcript counts against holding, so a flag that can
manufacture one is a way to make a model look worse by accident. Kept here rather than deleted, and
kept away from `walks/` because it measured nothing about the task.

`drive.py` now refuses any budget below the pre-registered value outright, so this cannot recur.
The walk slot it would have consumed is therefore still open, and the real walk follows.
