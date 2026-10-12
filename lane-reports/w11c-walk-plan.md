Status: built, gates green on the Mac; review round 1 (fresh opus-medium, on construction) not yet run; then athena

RESUME HERE: review round 1, then athena

# Lane w11c-walk-plan: Gap Study round 4, the CP6 walk list and its coverage report

Written Mon 12 Oct 2026, 15:30 EDT (`date`), by the lane's only writer (Claude Opus 5.5), assigned by glitch-2f (the Lane-orchestrator, under Javier's standing delegation) from section 2 of `plans/gap-study-round-4/next-slices-plan-2026-10-12.md`.
Branch `gap4/w11c-walk-plan`, base `f14ab57b` (wave 9, athena PASS), worktree `/Users/javrodher/aegis-builds/gap4-w11c`.
Red-first commit `cf76616b`; code commit `798223de`; this report is in its own commit.
Nothing was pushed or merged, and nothing was spent.
No model, walk, network, Docker, credential, salt or holdout path was used or read.

## What was built

1. `evals/gap-study-4/walk_plan.py` (new).
   - `design_in_force(study_dir)` reads the design files only: tasks, wordings and halves through `walk_register.design_in_force` (the reading the register's own check uses), the planned arms and models from the draft's `models`, each planned model's harness from the draft's rows (exactly one, or refused), and the set of the design's cells (arm, model, task, half, wording) from the rows.
   - `EVERY_WORDING` carries the one rule taken from the plan's words (plan 875, "every wording of every task, on Haiku"): arm A and the family name `haiku`; the design must hold exactly one such model on arm A, or the plan is refused.
   - `plan_walks(design)` returns the ordered specs: arms and models in the draft's order, then tasks, halves and wordings in the design's order.
     The every-wording model gets every wording of every task and half; every other planned model gets each task and half once, naming the task's first wording to run.
     The optional arm C is not planned (the draft's `models` holds A, O and G; C sits in `optional_arms`).
   - Each spec holds exactly `walk_register.FIELDS` plus `agent`; `walk` is None (the runner's; no ruling names an id rule), `reason` is the plan's reason, `counted` is false.
     Every spec is checked by `walk_register.entry_problems` against the design in force (under a probe walk id) and against the design's cells; any refusal refuses the whole plan.
   - `coverage(entries, specs, design)`: on the every-wording model a walk covers its own wording only; on every other model any wording of the task covers its task and half.
     An entry the design refuses, or one the plan does not require (an arm C walk), is reported by walk id under "outside the plan, not counted"; a retry covers its spec once and is named beside the first walk.
   - CLI: `--list` prints one line per required walk and one figure line per arm and model; `--coverage` reads `rehearsals/register.json` only (no walk folder is listed or read), names each required walk covered or missing and prints a figure line per arm and model, exit 0 with gaps; `--require-complete` exits 1 on any gap; a missing, symlinked, unreadable or duplicate-keyed register exits 2.
     No printed figure joins arms or models.
2. `evals/gap-study-4/tests/test_walk_plan.py` (new): P1 to P10, with an independent derivation of the figures written in the test itself, synthetic copies of the design for the dropped-task and dropped-wording cases, and 18 rule B witnesses.
3. `COPIED.d/w11c-walk-plan.json`, `checks.d/w11c-walk-plan.txt` and this report.

Not in scope, carried: wiring `--coverage --require-complete` into `freeze_rehearsal.py` or `walk_register.py` (w8b and w8d own them; a later slice), and walk_runner's CLI (wave 10's).
No file outside the closed list was touched.

## Derived figures (f14ab57b's design, from `walk_plan.py --list`)

| Arm | Model | Harness | Required walks | Rule |
|---|---|---|---|---|
| A | claude-opus-5-5 | claude-code | 18 | each task and half, one wording |
| A | claude-sonnet-5-5 | claude-code | 18 | each task and half, one wording |
| A | claude-haiku-4-5-20251001 | claude-code | 90 | every wording of each task and half |
| O | gpt-6.1-sol | codex | 18 | each task and half, one wording |
| O | gpt-6-luna | codex | 18 | each task and half, one wording |
| G | gemini-3.8-flash | gemini | 18 | each task and half, one wording |
| G | gemini-3.5-flash-lite | gemini | 18 | each task and half, one wording |
| C | claude-fable-5-1 | none | none required | optional arm, no rows |

The design holds 9 tasks, each with 2 halves (trap, normal) and 5 wordings (w1 to w5).
These match the brief's expectations, which were tested against and not typed: Haiku 90 (9 x 2 x 5); Opus and Sonnet 18 each (36 on arm A beside Haiku); arms O and G 18 per model, 36 per arm (72 for the two added arms, ruling Q-2 as proposed, D8:448).
No derivation disagreed with the expectations.
D8:448's "about 30 per model" is these 18 plus bring-up walks, which are registered and not required.

## Evidence (Mac, each batch behind `mac_slot.py light-ok` and `timeout -s INT 120`, /usr/local/bin/python3.13)

- Red first, at `cf76616b` (tests committed, no walk_plan.py): `test_walk_plan: 10 run, 10 failures, 0 errors, 0 skipped`; every failure is `AssertionError: ... P0.module <clause>: walk_plan.py does not exist yet`.
- Green at `798223de`: `test_walk_plan: 10 run, 0 failures, 0 errors, 0 skipped`.
- Witnesses: `test_walk_plan witnesses: 18 of 18 red; registry 18`; each bound test fails by an AssertionError carrying its clause, with no error.
- Gates on `798223de`: `copy_manifest.py --check` ok (299 files from 48 fragments, 246 new); `build_draft.py --check` ok; `freeze.py --check` ok (299 owned paths); `walk_register.py --check` ok, having registered 0 walks.
- `lint_language.py evals/gap-study-4/`: clean, 92 inputs; `lint_pooling.py evals/gap-study-4/`: clean, 92 files.
  Both also clean with `--include-code` over walk_plan.py, the test, the fragment and the checks line, and over the commit bodies since `f14ab57b` (`--commits-since f14ab57b --at HEAD`).
- flake8 at a 120-column limit: clean over both new Python files.
- `walk_plan.py --coverage` on the real (empty) register: "the register lists no walk", every spec missing, exit 0; with `--require-complete`, exit 1.

## Witnesses and their bound tests

| Witness | Bound test (clause) | What it weakens |
|---|---|---|
| count-hard-coded | P2Dropped (P2.dropped) | `counts()` returns the f14ab57b figures as literals |
| wordings-typed | P2Dropped (P2.dropped) | the wordings typed as w1 to w5 |
| half-missing | P3Halves (P3.halves) | only the first half planned |
| optional-required | P3Halves (P3.halves) | the optional arm planned |
| agent-unread | P3Halves (P3.halves) | the agent typed as claude-code |
| off-design-counted | P4OffDesign (P4.off-design) | entry_problems ignored in coverage |
| outside-counted | P4OffDesign (P4.off-design) | an entry the plan does not require counted |
| exact-wording-unchecked | P5ExactWording (P5.exact-wording) | any wording covers on the every-wording model |
| spec-key-shared | P5ExactWording (P5.exact-wording) | two specs on one coverage key admitted |
| require-complete-gap | P6Require (P6.require) | `--require-complete` passes with a gap |
| register-duplicate-admitted | P6Require (P6.require) | duplicate keys in the register read |
| register-link-admitted | P6Require (P6.require) | a symlinked register read |
| folder-listed | P7RegisterOnly (P7.register-only) | coverage lists rehearsals/ |
| spec-unchecked | P8SpecChecked (P8.spec-checked) | a spec the register's design refuses admitted |
| cell-unchecked | P8SpecChecked (P8.spec-checked) | a spec with no row of the design admitted |
| harness-mixed-admitted | P8SpecChecked (P8.spec-checked) | a planned model with two harnesses admitted |
| figure-across-arms | P9Prose (P9.prose) | a figure across arms and models printed |
| every-rule-first-match | P10EveryRule (P10.every-rule) | two haiku models admitted, the first taken |

P1 (the figures against the independent derivation) has no mutant of its own: the only way to break it without breaking P2 or P3 first is to change the derivation, which P2's two witnesses cover.

## Folds made while going green (tests, before the code commit)

- P10's two-haiku case adds rows for the second model, so only the every-wording rule can refuse it (the harness guard refused it first, and the witness passed).
- P4 and P5 read a coverage refusal as a failure by clause (the spec-key guard raised an error under exact-wording-unchecked).
- P6 gains a symlinked register, P8 a mixed-harness model, P5 two specs on one key; four witnesses added for them.
- The folder-listed anchor was re-indented to sit inside the `try`.
- No test was weakened.

The code commit's message was amended once before this report (own branch, never pushed): its body wrote the witness figure as a slash ratio, which `lint_language --commits-since` flags as a ratio; it now reads "18 of 18". The amended commit is `798223de`.

## Ownership

All new files are claimed in `COPIED.d/w11c-walk-plan.json` (four entries, appended in order).
No other lane's file was edited.

## Open questions

- Q-w11c-1: on models other than the every-wording one, does any wording of the task cover its task and half?
  Proposed: yes, as built (plan 876, "with at least one wording"); the spec still names the task's first wording, so the runner has one deterministic choice.
- Q-w11c-2: the every-wording model is the one model of arm A whose id carries "haiku" (EVERY_WORDING, from plan 875's words), refused when zero or two match.
  Proposed: keep; this is the plan's rule, not a figure, and a design change that adds or drops a haiku model refuses the plan rather than guessing.
- Q-w11c-3: ruling Q-2 is recorded as "Proposed" in section 3 of the next-slices plan; this lane applied it as glitch-2f's launch message names it ("arms O and G per ruling Q-2").
  Proposed: glitch-2f records the ruling line (with its time) in the next-slices notes, so the docstring's citation binds to a ruling, not a proposal.
- Q-w11c-4: does a bring-up walk that lands on a required spec cover it?
  Proposed: yes; a walk is a walk (rehearsals/README.md), and a bring-up walk off the list is reported as outside the plan and never counted.
- Q-w11c-5: the walk id stays the runner's; no ruling names an id rule. Proposed: keep until a ruling names one.

## Modules athena must run

- tests/test_walk_plan.py and `--witnesses`
- tests/test_scaffold.py (whole)
- test_round4.py (the battery)
- The gates: copy_manifest --check, build_draft --check, freeze.py --check, walk_register --check, lint_language and lint_pooling over the folder
