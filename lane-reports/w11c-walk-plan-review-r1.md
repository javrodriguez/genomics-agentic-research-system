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

# Round 2

Written Mon 12 Oct 2026, 18:55 EDT (`date`), by the same reviewer, on glitch-2f's request.
Reviewed: head `7f37f234` (red `0dae2059`, fold `96376ecd`), ruling w11c-R1-fold.
No code was edited; this section is the only change.

## Verdict

PASS on the threat model: no MAJOR, and no MINOR that loosens a check.
Both round 1 MAJOR findings are closed, and so are the three loosening MINORs.
The generated sweep fails as committed: run whole on the Mac, 11 of its 251 mutants survive.
W11C-R2-1 names them; athena's `--generated-mutants` shard lines will be red until they are folded.

## Reproduced on the fold

- Suite: `test_walk_plan: 15 run, 0 failures, 0 errors, 0 skipped`.
- Round 1's W11C-R1-1 repro (every spec under one walk id, `--coverage --require-complete`) now exits 2 with "walk_register's check refuses".
  Case-twin ids exit 2.
  A complete register with distinct ids exits 0.

## The staged-copy road (request 2)

These probes ran against the worktree's `walk_plan.py` with synthetic registers in the reviewer's scratchpad.
- A symlinked `register.json` exits 2.
- A walk id with a path separator (`x/y`), a backslash, `..` or `.DS_Store` gets no stand-in folder, and the check refuses it, exit 2.
- It never reads a real walk folder.
  The base was set to mode 0311 (it can be entered but not listed) and two walk folders to mode 000, each holding a `grade.json`.
  `--coverage --require-complete` still exited 0 on a complete register.
  An audit hook saw only `open` on `register.json` under the base: nothing was listed, opened or created there.
  Every write went to the `walk-plan-register-*` temporary folder.
- Not loosening, noted:
  - A walk id of `register.json` makes the stand-in `mkdir` raise FileExistsError, and a 300-character id makes it raise "File name too long".
    Neither is caught, so the script dies with a traceback and exit 1, not the exit 2 the docstring promises.
    It fails closed, and under plain `--coverage` it fails closed too.
  - A walk id of `README.md` or `stand-in.txt` passes the staged check and is counted.
    The real `walk_register.check` would refuse `README.md`, because a file of that name sits in rehearsals/.
    The staged check refuses no missing folder, by design: the docstring leaves folder rules to `walk_register.py --check`, which the gates run.
    Until a later slice wires `--require-complete` into the freeze, that gate has to run beside it.
  - A symlinked base folder is followed, as `walk_register.check` follows it.

## My harness, re-anchored (request 1)

The round 1 AST mutator ran on a fresh scratch copy of the folded study, with `--failfast`, behind `light-ok` before every run.
It made 247 AST mutants and 15 hand mutants.
Results: 243 killed by an assertion, none killed only by an error, 19 survived.
None of the 19 loosens a check:
- L61-62 (the `sys.path` insert), L98 (`Path(study_dir)`), S6 (`ANY_WORDING` set to `"w1"`): equivalent.
- S10 (check against the default design): equivalent, because `main` passes the study's own design on every call.
- S11 (return the raw walks once the check has passed): equivalent, because the check guarantees every entry is an object with a string walk id.
- L214 (`is_file` dropped): equivalent in exit code; a missing register still exits 2 through the read error, with a different message.
- L219 (the read-error raise removed): an unreadable register crashes with a traceback (exit 1, not 2).
- L296 (`return 0` after `--list` removed): `--list` also prints a coverage report and still exits 0.
- L307 and S8 (the `FAIL --require-complete` message): exit 1 is unchanged.
- L145-146 and L228-229 (the "first five, and N more" bounds): message text only.
Hand mutants on module-level logic strings were killed: the every-wording arm (`A` to `O`) and family (`haiku` to `sonnet`), a two-segment `PROBE_WALK`, `STAND_IN` set to `.DS_Store`, and a scratch register under the wrong name.

## The generated sweep, run whole (request 3)

The generated sweep ran as 64 shards on a scratch copy, each behind `light-ok` (waiting through holds) and `timeout -s INT 120`.
All 251 mutants ran: 240 were killed by an assertion, 0 by an error, 0 timed out, and 11 survived.

### W11C-R2-1 (MINOR, does not loosen; gate red): the sweep's own checks.d lines fail

`EQUIVALENT` is empty, so each survivor fails its shard.
On the Mac these shards of 64 exited 1: 12, 16, 25, 26, 29, 32, 48, 57, 58 and 64.
The survivors, by the sweep's own ids:
- L98.pass.0 (`study_dir = Path(study_dir)`): equivalent.
- L214.drop1.0 (`is_file` dropped): equivalent in exit code, as above.
- L219.pass.0 (the read-error raise removed): an exit 2 becomes an uncaught traceback.
- L296.pass.0 (`return 0` after `--list`): `--list` falls through into a coverage report.
- L307.pass.0 (the `FAIL --require-complete` print): message only.
- L145.slice.0, L145.int.0, L146.int.0, L228.slice.0, L228.int.0, L229.int.0: the "first five, and N more" bounds.
The lane report says L146 and L229 were killed by an assertion on `--only` re-runs.
That holds for some mutants on those lines, but `.int.0` on each still survives.
Repro: `python3 -B -W ignore evals/gap-study-4/tests/test_walk_plan.py --generated-mutants --only L98.pass.0,L214.drop1.0,L219.pass.0,L296.pass.0,L307.pass.0`.
Fix direction: bind each of these by an assertion where it is real: exit 2 on an unreadable register; `--list` prints no coverage lines; the FAIL line under a gap; the "and N more" count on a register with six or more problems.
List the rest in `EQUIVALENT` with their reasons (L98, L214.drop1).

## String constants (request 4)

The generator mutates only inside functions, classes and the `__main__` block.
So module-level assignments (`EVERY_WORDING`, `ANY_WORDING`, `PROBE_WALK`, `STAND_IN`, the two reasons) are outside it, strings and all, not just the f-strings.
My hand mutants covered the logic among them, and each was killed (above); `ANY_WORDING` is equivalent.
The gate is the exit code, and each code (0, 1, 2) is bound by an assertion through `main` and through the script entry (P14).
These printed lines are bound by assertions:
- the per-spec `missing` and `covered ... by <walk id>` lines (P6, P7, P14);
- each model's figure line (P13);
- the `ok:` line, only under `--require-complete` with nothing missing (P14);
- the refusal line "walk_register's check refuses" (P12);
- the `outside the plan, not counted` lines (P4);
- the empty-register sentence, both ways (P6).
Two printed outputs are not bound: the `FAIL --require-complete` line (L307), and the `--list` output's freedom from coverage lines (L296).
Neither is a gate input; both are in W11C-R2-1.
No logic hides in the f-strings: every one builds a message, a label or a printed line, and none feeds a comparison or a key.

## Residuals

- The reviewer's harness and the 64 shards ran from a scratch copy of the study folder (session scratchpad), never the worktree; the driver has exited and the copy's `walk_plan.py` matches the worktree's.
- The Mac held several times (load up to 57); every run waited for `light-ok` before starting.
