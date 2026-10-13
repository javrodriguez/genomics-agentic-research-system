Status: review round 2 PASS (adc26ec7); ruling w11c-close-1 folded (2a6646c7); ready for athena

RESUME HERE: athena

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

## Fold w11c-R1, Mon 12 Oct 2026 16:28 EDT (`date`)

Review round 1 (`lane-reports/w11c-walk-plan-review-r1.md`, d8ed8b9b) was CHANGES: two MAJOR findings and three MINOR ones that loosen a check.
Ruling w11c-R1-fold (glitch-2f) folds all five, the notes, and a generated mutation sweep.
Red-first commit `0dae2059` (tests); fold commit `96376ecd` (code, tests folded while going green, fragment appends, checks line).

What changed in walk_plan.py:
- W11C-R1-1: `read_register(base, design)` reads the register through walk_register's own check and reader, one code path.
  The register's bytes are copied into a temporary folder beside a stand-in folder for each one-segment walk id; `walk_register.check` runs there against the design in force; any problem refuses the report, exit 2, with the check's own words (the first five, then "and N more"); `walk_register.registered` then reads the entries.
  A walk id used twice, ids that differ only by case, a wrong schema, an extra top-level key, walks that are not a list, a top-level list, a non-object entry, a counted entry, an off-design entry, a non-string or two-segment walk id and a duplicate JSON key all exit 2.
  The review's repro (every spec under one walk id, with `--require-complete`) now exits 2 with "registered twice".
  No walk folder under rehearsals/ is listed, read or looked up; the stand-ins mean only the folder rules are left to `walk_register.py --check`, which the gates run.
- Note: coverage checks each register entry's cell against the design's rows; an entry on a wording with no row covers nothing and is reported outside the plan.
- Note: `SPEC_FIELDS` is removed.

What changed in the tests (15 tests, 31 witnesses):
- W11C-R1-2: P13 binds each model's missing figure on a register with a different number of gaps on every model (0 to 6 in plan order), and on a synthetic design that plans one model id on arms A and O; witnesses per-model-arm-dropped and per-model-model-dropped.
- W11C-R1-3: P14 runs walk_plan's source as a script (`__name__ == "__main__"`) and binds its exit codes; `--list --require-complete` is refused; the ok line prints only under `--require-complete` with nothing missing; a design that cannot be derived exits 2; without `--base` the register is `walk_register.REHEARSALS`'.
- W11C-R1-4: P12 (the register shapes above, each first shown refused by `walk_register.check` itself); P4 gains a non-object entry and a non-string walk id (reported as "entry <i>"); P10 and the refusal helper accept only PlanRefused; calls into walk_plan go through helpers that fail the clause by an assertion on any other exception or a wrongly typed return; a module that fails or exits on import fails every test by P0.module.
- W11C-R1-5: P11 synthetic designs drop a half, add a half and add a model on arm G; P10 adds a haiku model moved to arm O (refused: arm A has none) and a haiku-named model on arm O beside arm A's (not taken, one wording); the test's own every-wording derivation searches arm A only.
- Notes: P6 binds every missing line, every covered line with its walk id, and the empty-register line only on an empty register; P7 also records stat and lstat, and only the register is touched under rehearsals/.
- The generated sweep: `--generated-mutants [--shard i/n] [--only ID,...]`, self-contained in the test file.
  A stdlib AST mutator over every function and the `__main__` block (comparison negated, if and conditional tests set to True and False, and/or swapped and each operand dropped, `not` removed, each conditional branch taken, a slice's bound removed, an integer moved by one, each comprehension filter dropped, an assignment, expression, raise, return or continue replaced by pass) makes 251 mutants of walk_plan.py.
  String constants and f-strings are never mutated (the one message rule); the printed lines the gate depends on are bound by assertions instead.
  The unmutated module, re-emitted by the same unparser, must pass first. Each mutant runs the whole suite with `--failfast` in its own process and must fail by an assertion, with no error; otherwise it must be listed in EQUIVALENT with its line text and a reason, and a listed mutant that is killed, or an entry whose mutant is no longer generated on that line, fails the sweep.
  EQUIVALENT is empty. P15 binds the registry check (a changed line, a missing mutant and an empty reason are each reported).
  checks.d runs it in four shard lines, for athena.

Witnesses added (13): rows-unchecked-coverage, entry-label-fallback (P4); stand-ins-missing (P6); folder-statted (P7); every-rule-dropped, every-rule-any-arm (P10); halves-typed (P11); register-check-skipped (P12); per-model-arm-dropped, per-model-model-dropped (P13); script-entry-dropped, list-require-admitted, ok-unconditional, default-base-ignored (P14).
Removed (1): register-duplicate-admitted, whose anchor (the old JSON read) is gone; the duplicate key is now refused by walk_register.check and bound in P12 under register-check-skipped.

Evidence (Mac, each batch behind `mac_slot.py light-ok` and `timeout -s INT 120` or 115, /usr/local/bin/python3.13):
- Red at `0dae2059` against 798223de's code: `14 run, 2 failures, 0 errors` (P12.register: the one-walk-id register exited 0; P4.off-design: a wording with no row covered a spec).
- Green at `96376ecd`: `test_walk_plan: 15 run, 0 failures, 0 errors, 0 skipped`; `test_walk_plan witnesses: 31 of 31 red; registry 31`.
- Gates: copy_manifest --check ok (299 files, 48 fragments); build_draft --check ok; freeze.py --check ok; walk_register --check ok, 0 walks.
- lint_language and lint_pooling over the folder: clean, 92 inputs each; both clean with `--include-code` over walk_plan.py, the test and the fragment, and over the commit bodies since f14ab57b. flake8 at 120 columns clean.
- Derived figures unchanged (`--list`): Haiku 90; Opus, Sonnet and each arm O and arm G model 18.
- The sweep on the Mac, a sample only (the Mac was near its light limit): shard 1 of 12, shards 2 to 8 of 16, three mutants of shard 9 of 16 and shard 17 of 32, about 140 of the 251 mutants.
  Survivors and errors found there, each now killed by an assertion (re-run with `--only`): L128 ifexp-else (an error before failfast), L146 and L229 (the "and N more" text), L206 drop1 and drop2 (stand-in ids), L234 (spec_line returning None), L245 (the --list walk lines), L249 (the rule text), L293 (exit 2 on a design failure), L314 (a module that runs main on import), L133 (each spec's reason).
  The rest of the sample was killed by an assertion on the first run. The whole sweep is athena's; a survivor there is folded by a test or an EQUIVALENT entry with its reason.

Residuals:
- One read-only timing probe of the mutant generator ran after a light-ok hold at 16:23 (load1 16.31): a `&&` chain stopped the suite but not the `;`-joined probe (about 15 s of one process). No other batch ran on a hold.
- Shard 9 of 16 was stopped by its 115 s timeout after three mutants (before the generator was made lazy); no child process was left running (`ps`).
- The sweep's run time on athena is about 251 suite runs, in four shard lines under run_checks' 3600 s limit each.

Open questions: none new. Q-w11c-3 is answered by the ruling Q-2 line the reviewer cites (next-slices-2026-10-11.md, 15:32 EDT).

## Modules athena must run (after fold w11c-R1)

- tests/test_walk_plan.py, `--witnesses`, and `--generated-mutants` in its four shards (checks.d/w11c-walk-plan.txt)
- tests/test_scaffold.py (whole)
- test_round4.py (the battery)
- The gates: copy_manifest --check, build_draft --check, freeze.py --check, walk_register --check, lint_language and lint_pooling over the folder

RESUME HERE: review round 2.

## Fold w11c-close-1, Mon 12 Oct 2026 19:11 EDT (`date`)

Review round 2 passed (adc26ec7). The full generated sweep (251 mutants) left 11 survivors with EQUIVALENT empty; ruling w11c-close-1 (glitch-2f) folds them before athena.
Red-first commit `52773435` (tests; against 96376ecd's code: 15 run, 1 failure, P12.register, the register.json walk id raised FileExistsError, 0 errors); fold commit `2a6646c7`.

- Code: read_register gives no stand-in folder to a walk id that cannot be one (register.json itself, a 300-character id); walk_register's check then reports the folder missing and the register is refused by name, exit 2, never a crash. The except body is a bare `pass`, which the sweep does not mutate.
- Tests: the "first five, and N more" bounds with six and with many problems, in plan_walks and in the register report; an unreadable register (read_bytes patched to raise) is a named exit 2; a missing register's own words; `--list` prints no coverage report; the FAIL line is the last line under a gap; a study folder named by a string plans the same walks; the two odd walk ids exit 2 with the check's words.
- L98.pass.0 and L214.drop1.0 were not equivalent: each is now killed by an assertion (the string study folder; the missing register's own words), so EQUIVALENT stays empty.
- Witness stand-in-crash added (P12): 32 in all.

Evidence (Mac, light-ok before each batch, waiting on holds; the full sweep was not run here):
- `test_walk_plan: 15 run, 0 failures, 0 errors, 0 skipped`; `test_walk_plan witnesses: 32 of 32 red; registry 32`.
- `--only` on the Mac, every one KILLED by an assertion: L98.pass.0, L214.drop1.0, L219.pass.0, L301.pass.0 and L312.pass.0 (athena's L296 and L307, five lines later after the fold), L145.slice.0, L145.int.0, L146.int.0, L233.slice.0, L233.int.0 and L234.int.0 (athena's L228 and L229), and the new lines' L227.pass.0 and L228.pass.0, with L146.cmp.0 and L234.cmp.0.
- The mutator still generates 251 mutants; ids after line 223 moved by five lines.
- Gates: copy_manifest, build_draft, freeze.py and walk_register --check all exit 0; lint_language and lint_pooling clean over the folder, with `--include-code` over the lane's files, and over the commit bodies since f14ab57b; flake8 clean.

## Modules athena must run (after fold w11c-close-1)

- tests/test_walk_plan.py, `--witnesses`, and `--generated-mutants` in its four shards (checks.d/w11c-walk-plan.txt)
- tests/test_scaffold.py (whole)
- test_round4.py (the battery)
- The gates: copy_manifest --check, build_draft --check, freeze.py --check, walk_register --check, lint_language and lint_pooling over the folder

RESUME HERE: athena.
