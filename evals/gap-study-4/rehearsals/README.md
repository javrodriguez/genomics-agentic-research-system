# Round 4 rehearsals: the pre-freeze walks

This folder holds the walks of Gap Study round 4: the tries run in the box before the freeze, so the graders, the evidence readers and the operator script meet real end states before anything is pre-registered.
It says what the round 4 plan says about them, and names as open questions what the plan leaves undecided.
Line numbers cite the private round 4 plan (`plans/gap-study-round-4.md`) as it stood on Mon 12 Oct 2026.

## What a walk is

- The plan's CP6 ("Walks, reviews, freeze", lines 868-893) creates this file and lists the walks: every wording of every task on Haiku, and every task and half on each model with at least one wording (lines 874-876).
- "They are rehearsals: graded but never counted, each committed with its reason." (line 877)
- "Every walk is graded but never counted. The v4 graders and the evidence readers meet real box end states before the freeze, and their outputs are read." (line 878)
- "Fix what the walks show. Pre-register only what was walked." (line 884)
- The plan's checklist repeats it: "box probes with scripted stub agents, and every walk graded but not counted" (line 1186).

## A walk is never a data take

A walk is not a row of the design, is never part of a result, a count, a rate or a pooled number, and never fills a slot of the frozen take order.
Each register entry carries `"counted": false`, and the check refuses any other value.
Walks run before the freeze (CP6); the graded takes run after it (CP7, line 895 on).

The word "rehearsal" has a second, older meaning in this study, and the two are kept apart:

- In the routing table (line 193), a **rehearsal** is a graded take's attempt refused before the agent's first turn (a preflight failure, a container start failure, an API error), re-run in the same slot under its cap.
  Those attempts belong to the take's slot; round 4's production driver records them in the take's own folder (`takes/<slot>/<k>`), not here (open question 1 names the copied road that still writes here).
- Outside reads and critical-path prompts are recorded as events, never as rehearsals (line 185).
- This folder holds only the CP6 walks.

## Where a walk's records live

- The plan names `rehearsals/` as CP6's walk folder (line 299: "`rehearsals/` walks").
- One walk is one folder directly under this one: `rehearsals/<walk>/`, where `<walk>` is a single path segment named in the register.
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
- `python3 evals/gap-study-4/walk_register.py --check` binds the register to this folder both ways: every folder here is registered, every registered walk has its folder holding at least one file, and every entry is well formed.
  A file here other than `README.md` and `register.json` fails as well.
- With no walk run, the register is empty and the check says so: `ok, having registered 0 walks: ...`, never a bare ok.

## Open questions

These are not decided by the plan, and nothing here decides them.

1. **Which road writes here.** The copied round 3 code still writes walks to `walks/<task>/<n>/` (`drive.py --walk`, read by `mode_binding.py --walks`, `fixture_walk.py` and `build_cases.py`), and its rehearsal copy writes `rehearsals/<task>/<half>/<model>/row-<n>` (`drive.py`, round 3's section); round 4's production driver (`walk_driver`) writes `takes/<slot>/<k>`.
   None of them writes `rehearsals/<walk>/` yet.
   Until one does, a folder any of them creates here fails the register check as unregistered.
2. **What a walk folder holds, and where its grader output lives.** Line 878 says the outputs are read; the register checks only that the folder holds a file.
3. **Coverage.** The register does not check that the walks cover line 874-876's list; the count there (about 170) predates dropping one task and adding arms O and G.
4. **The copy record.** `copy_manifest.py --check` refuses any file in this study folder that no `COPIED.d` fragment claims, so a rule for claiming walk records is needed before the first walk is committed.
5. **The gates.** CP6's VALIDATE line (893) runs `review_kit/rounds.py --check` and `freeze_rehearsal.py`; neither runs `walk_register.py --check` yet.
6. **Publication.** Whether the walks themselves are published with the study at CP8 is not stated.
