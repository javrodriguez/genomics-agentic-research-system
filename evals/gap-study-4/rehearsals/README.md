# Round 4 rehearsals: the pre-freeze walks

This folder holds the walks of Gap Study round 4: the tries run in the box before the freeze, so the graders, the evidence readers and the operator script meet real end states before anything is pre-registered.
It says what the round 4 plan says about them and how they are recorded, and names as open questions what the plan leaves undecided.
Line numbers cite the private round 4 plan (`plans/gap-study-round-4.md`) as it stood on Mon 12 Oct 2026.

## What a walk is

- The plan's CP6 ("Walks, reviews, freeze", lines 868-893) creates this file and lists the walks: every wording of every task on Haiku, and every task and half on each model with at least one wording (lines 874-876).
- "They are rehearsals: graded but never counted, each committed with its reason." (line 877)
- "Every walk is graded but never counted. The v4 graders and the evidence readers meet real box end states before the freeze, and their outputs are read." (line 878)
- "Fix what the walks show. Pre-register only what was walked." (line 884)
- The plan's review fold-in list repeats it: "box probes with scripted stub agents, and every walk graded but not counted" (line 1186).

## A walk is never a data take

A walk is not a row of the design, is never part of a result, a count, a rate or a figure joined across takes, and never fills a slot of the frozen take order.
Each register entry carries `"counted": false`, and the check refuses any other value.
Walks run before the freeze (CP6); the graded takes run after it (CP7, line 895 on).

The word "rehearsal" has a second, older meaning in this study, and the two are kept apart:

- In the routing table (line 193), a **rehearsal** is a graded take's attempt refused before the agent's first turn (a preflight failure, a container start failure, an API error), re-run in the same slot under its cap.
  Those attempts belong to the take's slot; round 4's production driver records them in the take's own folder (`takes/<slot>/<k>`), not here (round 3's copied road that wrote them here is retired; open question 1).
- Outside reads and critical-path prompts are recorded as events, never as rehearsals (line 185).
- This folder holds only the CP6 walks.

## Where a walk's records live

- The plan names `rehearsals/` as CP6's walk folder (line 299: "`rehearsals/` walks").
- One walk is one folder directly under this one: `rehearsals/<walk>/`, where `<walk>` is a single path segment named in the register.
  A walk that dies is still a walk, committed with its reason; a retry is a new walk id.
- The folder holds what a take folder holds (the driver ledger, launch, preflight, refusal, postflight, teardown, operator-check and environment records, the scrubbed transcript and its scrub record, the turn streams, `proxy.log`, `evidence/` and `session/`), plus `grade.json` and `check.json`.
- `grade.json` is the v4 grader's output for the walk (`run.py`'s `regrade()`, through `grade_walk()`), or `{"graded": false, "why": ...}` when the walk had no first agent turn, its reason read from the driver ledger.
- `check.json` is the checker's reading of the walk and the route routing gives its records (ruling D1, lane w10-walk-runner): a walk is read by check4's round-4 walk road, with no takes.json row and its own session id (ruling D2: uuid5 of `walk/<walk id>`), never as a take.
- A walk that died before its first turn, so before the driver wrote its ledger, holds `preflight.json` or `refusal.json` in the ledger's place, and its `grade.json` says "not graded, because ..." (ruling D3).
  A folder that holds a transcript or a turn record but no driver ledger is refused: a turn ran, so its ledger is missing, not unwritten (W10-R2-3).
- The folder names are defined once, in `mode_binding.py` (`WALKS_DIR` for walks, `TAKES_DIR` for the graded takes under `takes/<slot>/<k>/`), and every reader and writer imports them.
- A walk folder can never be graded into results: `run.py` grades only folders under `takes/`.
- Until publication nothing of round 4 is pushed beyond the two narrow early-piece commits: "no lane branch, no walk and no transcript reaches GitHub" (line 862).
- The holdout author never reads the build's walks or rehearsals (line 708).

## How a walk is registered

`register.json`, beside this file, lists every walk:

```json
{"schema": 1, "walks": [{"walk": "<one path segment>", "task": "<task id>", "half": "<half>",
                         "wording": "<wording id>", "arm": "<arm>", "model": "<model id>",
                         "reason": "<why this walk was run>", "counted": false}]}
```

- `task`, `wording`, `arm` and `model` are read against the design in force (`prereg-draft.json`), and `half` against `tasks/<task>.json`; arm C's optional model is admitted.
- `reason` is the reason the plan requires each walk to be committed with (line 877), never empty.
- A walk is driven by `drive.walk_driver(records="walks")` into its folder, and committed by `drive.WalkRepo`: one commit holding the walk's folder and its new register entry, scanned as a take's records are, and refused once `prereg.json` exists (walks run before the freeze; the graded takes are committed after it, by `TakeRepo`).
- `walk_runner.py` runs the walks one at a time: launch through the walk arm, drive, check, grade, commit, then delete the per-take config folder.
  A walk refused before launch made nothing and is reported; a walk whose drive raised (a drive scan or postflight refusal among them) is never committed, its folder is left for a human (which turns the check below red), and the runner stops.
- `python3 evals/gap-study-4/walk_register.py --check` binds the register to this folder both ways: every folder here is registered, every registered walk has its folder holding at least one file, and every entry is well formed.
  A file here other than `README.md` and `register.json` fails as well.
  Each registered walk's folder must also hold only the records listed above and must hold `grade.json`, `check.json` and `driver-ledger.json` (or, for a walk that died before its first turn, `preflight.json` or `refusal.json`).
- With no walk run, the register is empty and the check says so: `ok, having registered 0 walks: ...`, never a bare ok.

## Open questions

These are not decided by the plan.
Questions 1, 2, 4 and 5 were closed by slice w8a (ruling W8-layout-1, Mon 12 Oct 2026); 3 and 6 stay open.

1. **Which road writes here.** _Closed by w8a._
   `drive.walk_driver(records="walks")` writes `rehearsals/<walk>/` (the row's walk id; an existing folder refused), and `drive.WalkRepo` commits it with its register entry.
   Round 3's host road (`drive.py --walk`, which wrote `walks/<task>/<n>/`, and its router, which wrote `rehearsals/<task>/<half>/<model>/row-<n>`, `transcripts/` and `pauses/`) is shadowed by refusals naming the walk runner; `tests/test_walk_layout.py` L1 and L2 prove both.
2. **What a walk folder holds, and where its grader output lives.** _Closed by w8a._
   A take folder's records plus `grade.json` (and, since w10, `check.json`), as above; `walk_register.py --check` enforces it (L10), and `run.py --walks --check` regrades every walk and requires its `grade.json` byte-identical (L6).
3. **Coverage.** The register does not check that the walks cover line 874-876's list; the count there (about 170) predates dropping one task and adding arms O and G.
4. **The copy record.** _Closed by w8a._
   `copy_manifest.py --check` claims a file inside `rehearsals/<walk>/` exactly when the register lists the walk; an unregistered walk folder's files still fail, and a fragment claiming a path inside a record folder is refused (L7).
5. **The gates.** _Closed by w8a for the rehearsal._
   `freeze_rehearsal.py` runs `walk_register.py --check`, `mode_binding.py --walks --check`, `fixture_walk.py --check` and `run.py --walks --check` (L11).
   Appending `walk_register.py --check` to CP6's VALIDATE line (893) is a proposed plan amendment for Javier, not applied; the CI job gains a walk step only at CP8, with its owner.
6. **Publication.** Whether the walks themselves are published with the study at CP8 is not stated.
