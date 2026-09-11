# Where the Gap Study stands

**11 September 2026. Nothing is frozen. No take has run. Spend $0.**

Every byte of this study is inside this repository.
The eleven review reports are under `reviews/`; the dispositions are under `verification/`.

## What the last pass did

Review 11 ruled **DO NOT FREEZE — four blockers**, and all four are folded, with its seven follow-ups.
`verification/prefreeze-11-disposition.md` has each finding and its evidence; Ruling 9 in `PROTOCOL.md` has what changed.

In short: the agent's checkout is built with `git archive` into a one-commit repository with no remote and a neutral name, one per take, and the driver checks it before the first turn.
The session under test is also cut off from the operator's user scope, which folding the review showed it had been receiving: extra working directories and the account's connector tools.
Both were proven on real sessions — four smokes under `verification/run-tree-smoke/`, and `number-fidelity` walk 2, which the checker reads valid — and every new guard was watched failing.

## The next moves, in order

1. **Ruled — Ruling 10.** The repository owner ruled on 11 September 2026 that published transcripts have the injected account email removed and the removal disclosed.
   `drive.py` removes it at copy time for walks and takes alike, and `transcript_publication` in the pre-registration states the rule.
2. **The carried follow-ups that touch pinned bytes**, folded before the next review reads them (below).
3. **Review 12** as `verification/prefreeze-12.md`, then the freeze: `freeze.py --review-commit <sha> --write`.
4. Then, and only then, the 108 takes.

## State

- 6 task pairs · 9 walks (8 driven under the leak and refused by the checker as it now stands, 1 clean) · 122 hand-labelled cases · 66 tests · 18 mutations · 11 reviews · 4 smokes
- 0 takes graded · not frozen · `gars/` and the first study unchanged by this work
- The local tier was dropped by the repository owner at gate 2; `local-model/DROPPED.md` is the record
- Rulings 1–10 in `PROTOCOL.md`
- `RESIDUAL.md` was written at the slice cap and is kept deliberately, though the cap was lifted (Ruling 7)

## Carried follow-ups, most valuable first

- Render `confounded-design`'s carried operator lines under this driver's two substitutions before its first take, or publish that row `not run` with the reason (`RESIDUAL.md`, the one open defect).
- Test the driver's outcome strings against the reader that consumes them.
- Enumerate takes by their driver ledger.
- Bind the plant to the counts per field rather than per dict.
- Index the verdict field rather than reaching for it with a default.
- Record `held` on an aborted turn.
- Print that no task's probed behaviour is enforced, rather than an empty mapping.
- Whether the deterministic layer loads at a session opened at the checkout's root.
- The write detector is weaker than the tree's own guard, in the direction that credits a violating agent.
- Re-driving the earlier walks clean is bounded by the two-walk cap: `scope-read` has one slot left, and three tasks have none.
