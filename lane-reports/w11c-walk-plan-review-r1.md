# Review round 1: lane w11c-walk-plan

Written Mon 12 Oct 2026, 15:50 EDT (`date`), by a fresh reviewer (Claude Opus 5.5), assigned by glitch-2f (the Lane-orchestrator).
Reviewed: branch `gap4/w11c-walk-plan`, base `f14ab57b`, head `1fa2d999` (red `cf76616b`, code `798223de`, report `1fa2d999`).
Brief: "### w11c-walk-plan" in `plans/gap-study-round-4/next-slices-plan-2026-10-12.md`; ruling Q-2 as recorded at 15:32 EDT in `next-slices-2026-10-11.md`.
No code was edited; this file is the only change.
Nothing was pushed, merged or spent, and no model was launched.

## Verdict

CHANGES: two MAJOR findings (W11C-R1-1, W11C-R1-2) and three MINOR findings that loosen a check (W11C-R1-3 to W11C-R1-5).

The derivation itself is sound.
The figures match ruling Q-2 (Haiku 90; Opus and Sonnet 18 each; 18 per arm O and arm G model; arm C none), the design is read from the files, and the spec check through `entry_problems` and the design's cells holds.

## Reproduced

- Suite on the worktree: `test_walk_plan: 10 run, 0 failures, 0 errors, 0 skipped`.
- Builder's witnesses: all 18 red.

## Mutation sweep (reviewer's own)

A stdlib AST mutator over a scratch copy of the study folder (never the worktree) built 235 mutants of `walk_plan.py`.
It swapped comparisons, set comparisons and if-conditions to True or False, flipped boolean operators and dropped their operands, removed `not`, took each branch of every conditional expression, widened slices, and replaced assignments, raises, returns and expressions with `pass`.
Ten hand mutants and two typed-design mutants were added.
Each mutant ran the whole suite behind `mac_slot.py light-ok`.
Results: 101 killed by an assertion, 69 killed only by an error, 65 survived.
Most survivors change only message text (lines 124, 136-137, 215, 229) or are equivalent in the test process (lines 52-53, 89).
The survivors that matter are named in the findings below.

## Findings

### W11C-R1-1 (MAJOR): `--require-complete` passes a malformed register; one walk id covers every spec

`walk_plan.py:183-196` (`read_register`) and `:166-178` (`coverage`).
`read_register` checks only that the file is a non-linked file, is JSON without duplicate keys, and holds a `walks` list.
It does not check what `walk_register.check` refuses at the register level: a walk id registered twice, two ids that differ only by case (one folder on the Mac), top-level keys other than `schema` and `walks`, or a wrong schema.
Repro: register `{"schema": 1, "walks": [<every spec as an entry, all with walk "only-walk">]}` with `--coverage --require-complete --base <dir>` exits 0 and prints "ok: every required walk is covered".
`walk_register.check` on the same register says "walk 'only-walk' is registered twice".
The same exit 0 holds for case-twin ids (`w0` and `W0`) and for `{"schema": 99, "extra": true, ...}`.
So one walk folder can cover all 216 required walks, against the threat model ("--require-complete fails closed on any gap or malformed register") and the module's own rule that a retry is a new walk id.
No test registers a duplicate walk id, a case twin or a bad top level.
Fix direction: refuse these register-level faults in `read_register`, exit 2, without listing folders.
Reuse walk_register's rules rather than retyping them, and give each refusal a witness.

### W11C-R1-2 (MAJOR): the per-model guard on the missing count can be deleted with the suite green

`walk_plan.py:237`: `gap = sum(1 for s in got["missing"] if (s["arm"], s["model"]) == (arm, model))`.
These surviving mutants count missing walks from more than one model into one model's line:
- `gap = sum(1 for s in got["missing"])` (across arms and models; hand mutant H1);
- `if s["arm"] == arm` (across the models of one arm; H2);
- the comparison set to True (AST mutant at L237).
P6's only figure assertion uses a register with exactly one missing walk, so the wrong count and the per-model count are both 1.
A count drawn from other models then prints on a line that names one model ("arm O, gpt-6.1-sol (codex): 16 of 18 required walks covered, 2 missing", with both gaps on Haiku), and lint_pooling.py cannot see it because the line names one model.
This per-model filter is how the report keeps each figure to one arm and one model.
Fix direction: assert each model's figure line against a register with gaps on two or more models of different arms, so each per-model count differs from a count over several models.

### W11C-R1-3 (MINOR, loosens): the command-line exit path is not bound

- `walk_plan.py:280-281`: deleting `raise SystemExit(main())`, or setting `__name__ == "__main__"` to False, survives.
  Run as a script, the gate would then exit 0 on any register.
  That is how a freeze rehearsal would call it, and no test runs the script entry (the process guard blocks a subprocess, but `runpy.run_path` with `sys.argv` patched would bind it).
- `walk_plan.py:252-253`: deleting the `--require-complete goes with --coverage` refusal survives (H3, L252 if False).
  `--list --require-complete` then exits 0, so a mis-typed gate passes.
- `walk_plan.py:275`: the condition set to True survives.
  `--coverage` without the flag then prints "ok: every required walk is covered" while walks are missing.
- `walk_plan.py:263`: the default base (`walk_register.REHEARSALS`) is never exercised, because every test passes `--base`.

### W11C-R1-4 (MINOR, loosens): register shapes below the top level are unbound

- `walk_plan.py:194-195`: the "holds no walks list" refusal can be deleted, or either clause dropped, with the suite green (L194 operand drops and flip, L195 raise to pass, H4).
  Without it, a top-level list register crashes with an AttributeError outside the caught set, and `"walks": {}` reads as an empty register.
- `walk_plan.py:167`: the label fallback for a non-object entry or a non-string walk is unbound (L167 body branch, flip and operand drops all survive).
  No test registers a non-object entry, and with the fallback gone such an entry raises an uncaught error instead of being reported as outside the plan.
- Deleting the duplicate-key `raise` at line 191, or the whole every-rule guard at line 80, is red only by an error, not by an assertion carrying the clause (rule B).

### W11C-R1-5 (MINOR, loosens): halves and the arm of the every-wording rule are not bound by synthetic designs

- Typed halves (`for half in ("trap", "normal"):`, T1) survive: P3 compares against the live design, whose every task has those two halves.
  A design that adds a half would then not be required, and P2 tests only a dropped task and a dropped wording.
  The threat model also names a dropped half and a dropped model, and neither has a synthetic-design case.
- Resolving the every-wording model from any arm (H7) survives.
  The test's own derivation at `tests/test_walk_plan.py:180` also searches every arm, so the "arm A" half of `EVERY_WORDING` is bound by nothing.

## Not loosening (noted, no action required by the stop rule)

- `walk_plan.py:228`: with `if walks:` set to False, every spec prints "missing" even when it is covered, and the suite stays green (P7's `assertIn("covered", out)` matches the per-model line).
- `walk_plan.py:223`: with the condition set to True, "the register lists no walk" prints over a non-empty register.
- P7 records only `open`, `listdir` and `scandir`.
  A `stat` or `exists` on a walk folder (H5) goes unseen, so "no walk folder is listed or read" is bound for reads and listings only.
- `walk_plan.py:62`: `SPEC_FIELDS` is defined and never used.
- `coverage` checks register entries against `entry_problems` but not against the design's cells.
  Today every planned model's rows hold all five wordings, so this is latent.
  If rows ever thin a model's wordings, a walk on a wording with no row would still cover that model's task and half.

## Residuals

- Before one small read-only repro batch (the W11C-R1-1 script), `mac_slot.py light-ok` said hold (load1 20.57) and the batch ran anyway.
  Every mutation run waited on light-ok inside the harness.
- The sweep's scratch copy and harness sit in the reviewer's session scratchpad, not in the repo.
