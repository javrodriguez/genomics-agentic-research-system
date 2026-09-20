# Round 3 — progress, one line per slice, append-only

Append-only: a line is added, never edited and never removed. The last act of every slice is the line
for that slice, committed with it.

**The slice counter is the number of lines below that begin with a date** — `grep -c "^2026" PROGRESS.md`
— never an estimate. The cap is 20 slices.

Each line reads: `date · slice n of 20 · milestone · reviews · freeze · rows · next`, where

- **reviews** is pre-freeze review rounds committed, of the cap of 3;
- **freeze** is `unfrozen` until `prereg.json` exists, then the freeze commit;
- **rows** is `committed / driven / graded / rehearsed`, with the rehearsal reasons named;
- **next** is the exact command the next slice opens with, so a fresh run needs nothing else.

---

2026-09-19 · slice 1 of 20 · the instrument copy: 44 files copied from round 2's done commit bf065fe, 11 edited with a reason and 10 pinned byte-identical; the pinned reviewer brief and purpose page committed before any draft exists; the round register, round 3's own guard against adding two instruments together, and its 33-test battery; the CI job added with no line removed · reviews 0 of 3 · unfrozen · rows 0 committed, 0 driven, 0 graded, 0 rehearsed · next: `python3 evals/gap-study-3/allowlist.py --derive`
2026-09-19 · slice 2 of 20 · the permission condition, derived by code: round2.py is the one read-only door to round 2's record, allowlist.py reads 364 pre-probe Bash calls in 52 committed transcripts and produces 22 candidate entries -- 15 route, 5 shape, 2 arbitrary -- each a verbatim prefix quoted from a named transcript and line, with 118 calls printed as refused by construction (109 of them a `cd` into a path naming one run). The entries themselves are gate 1 and are not pinned yet: the harness splits a compound command and rules on each part, so the route needs a probe before the list is chosen · reviews 0 of 3 · unfrozen · rows 0 committed, 0 driven, 0 graded, 0 rehearsed · next: `python3 evals/gap-study-3/probe.py --forms`
2026-09-20 · slice 3 of 20 · the draft pre-registration, built by code: 26 of round 2's frozen keys carried byte-identical, its three tasks verbatim on both halves, 18 planned cells and 54 planned takes, the 22 derived entries as the permission condition, and 18 predictions of which 7 carry no predicted count -- the 6 cells whose round-2 transcripts recorded `default` where `auto` was passed, derived from those transcripts, plus the one cell round 2 published incomplete. Two owner gates start null and the freeze refuses while either is: the allowlist entries, and three carried rulings re-put because their recorded scope names round 2's own artifact. The copied loader reads the draft and plans 54 takes; the driver boots against it · reviews 0 of 3 · unfrozen · rows 0 committed, 0 driven, 0 graded, 0 rehearsed · next: `python3 evals/gap-study-3/fixture_walk.py --recut`
