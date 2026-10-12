# Lane w10-walk-runner: review round 2

Written Mon 12 Oct 2026, 14:23 EDT (`date`), by a fresh reviewer (Claude Opus 5.5), assigned by the Lane-orchestrator.
Reviewed: `866586d4..adea27d3` on `gap4/w10-walk-runner` (fold f0af28ee, report adea27d3), against base f14ab57b.
No code was edited; this file is the only change.
Nothing was pushed, merged or spent; no model, network, container, credential, salt or holdout was used.

## Verdict

CHANGES (one MAJOR, two MINORs that loosen a check).

## What was verified (Mac, each run behind `mac_slot.py light-ok`, `timeout -s INT 120`, python3.13)

- Green: `tests/test_walk_runner.py`: 31 run, 0 failures, 0 errors, 0 skipped (58 s).
- Round 1's nine mutants, re-derived for f0af28ee's anchors (`pre` is now `walk_pre`), each compiled through the test module's own machinery (`T.mutants`/`T.SELECTED`, anchor asserted once by its `setUpModule`), with R1-R9 run whole (30 tests).
  All nine are red, by AssertionError only, 0 errors:
  - row-needed assertion: R8 test_the_row_needed_line_is_asserted ("CheckRefused not raised").
  - ledger task/half: R8 test_the_ledger_cell.
  - ledger row/row_commit: R8 test_the_ledger_row, test_the_ledger_row_commit.
  - environment_problems: R8 test_the_environment_record.
  - environment record row/row_commit: R8 test_the_environment_row, test_the_environment_row_commit.
  - model_problems: R8 test_the_model.
  - constants + checkout + pinned instructions: R8 test_the_constants, test_the_checkout, test_the_instructions.
  - recorded mode + design tree: R8 test_the_permission_mode, test_the_design_tree, and test_the_design_tree_through_the_drive (check.json `checker_reasons: []`, so the mutant reached the drive's checker).
  - drive identity row clause: R2 test_a_walk_identity_with_a_row_is_refused (the walk was committed instead of refused).
  - Also red: removing the ledger session check (R2 test_a_walk_is_read_as_a_walk).
- Root cause 1 (the drive importing the real check_take): the builder is right that it does not reproduce.
  drive.py:2673 and :3288 import `check_take` at call time, so they resolve `sys.modules["check_take"]`, which `compile_module` sets to the witness.
  The builder's probe (`.../scratchpad/w10/probe_machinery.py`, a raise at the top of `check4_walk`, run through R1) is sound, and my `mode-gone` mutant independently turned the through-the-drive test red.
  Round 1's nine survived for lack of bad-walk inputs (root cause 2), not because the drive missed the witness.
- Single-change tests: each R8 test changes one fact; where a record is forged to agree (environment.json's half and model, the ledger's environment sha via `rebind_environment`, the instruction paths with the working directory), the forged record is one that cross-binds the changed fact to another record, never to the guard under test, and each guard's own mutant goes red.
  `one_change` requires every added line to carry the bound guard's prefix.
  Not a finding: nothing on the walk road binds the ledger's `model_requested` to the row or register entry (the runner builds both from the same row, round 1's note).
- W10-R1-2: `_publish` runs only once `reached` is set, just before `driver.launch`; every runner refusal before that point (no walk id, slot not the walk id, no reason) returns first.
  Since the slot must equal the walk id before launch, the folder the keep guard reads is the folder of the take `published` pops.
  The keep is now keyed on `postflight.json` (present and not ok), else on `teardown.json` present with no postflight record.
  Both new R4 tests and their witnesses are as described; see W10-R2-2 for the remaining case.
- "checked": `checked = (folder / driver-ledger.json).is_file()`.
  drive.py writes the ledger in `_take_records` exactly when `ok and turns`, the same condition under which the checker runs (drive.py:2332-2336), and `_write` raises, so a checker that ran always leaves a ledger.
  R1 asserts true, R3 asserts false, witness `checked-always`.
- check_take.py append-only against f14ab57b: the base's bytes up to its `if __name__` block are a byte prefix of adea27d3's, the two `__main__` tails are equal, 8,846 bytes are appended, and the working file is adea27d3's (sha256 prefix 31e6b5ba0363e896).
  The appended top level is `WALK_SESSION_PREFIX`, `TAKE_ROW_NEEDED`, `walk_session_id`, `check_walk`, `check4_walk`: no base name is shadowed, and the appended code has no `global` statement or attribute store.
  The `pre` to `walk_pre` rename is inside the lane's own appended `check_walk`, so the base is untouched and round 3's code paths are byte-identical; R5 (same problems and printed lines for a round-3 walk under the base module and this one) is green.

## Findings

### W10-R2-1 MAJOR: the walk road's inherited-context tail can still be deleted with the suite green

check_take.py:2281-2286, in `check_walk`: the "no system-prompt snapshot" line and the "offered the harness's persistent memory folder" line.
On the walk road `check()` returns at the row-needed line (check_take.py:1747-1749) before its own copies of these two checks (:1776-1782), so `check_walk`'s copies are the only ones a walk gets.
`check_walk`'s docstring and the test module's R8 header both name them as part of D1's "take's tail", but R8 has no test that feeds a walk without a snapshot or a walk offered the memory folder.
Each mutant, through the real test module with R1-R9 run whole: 30 run, 0 failures, 0 errors.
Repro: replace `    if memory_section_offered(path):` + its append in `check_walk` (the one just before `return problems` above `def check4_walk`) with nothing, and run test_walk_runner: 31 run, 0 failures.
Same class as W10-R1-1 (a walk read "as for a take" that a take would refuse, reading clean); the fold closed the nine named lines but not the whole tail it names.
Fix direction: two R8 single-change tests (drop the snapshot attachment; add the memory section to it) with witnesses.

### W10-R2-2 MINOR (loosens the departure's keep guard): a failed postflight whose two records cannot be written deletes the config folder

walk_runner.py:98-113 (`_publish`).
The keep is read from the two records only; when neither `postflight.json` nor `teardown.json` was written, `_publish` deletes the config folder, while the driver raised "postflight: the postflight check did not run; the config folder is kept for a human" (drive.py:2318-2320, `_postflight` returns None on a write failure, :2115-2124).
One disk refusing both writes (for example a full disk) is the plausible shape.
Repro (scratch `.../scratchpad/w10r2/keep_probe.py`, the R4 rig): failing postflight, the driver's `_write` raising for `teardown.json` and `postflight.json`: `[('held', None, 'drive raised DriveRefused: postflight: the postflight check did not run; the config folder is kept for a human; ...')]`, config folders left 0.
Fix direction: keep by default once the drive was entered, and delete only on a positive record (postflight.json present and ok), or when the drive's error is not a postflight stop.

### W10-R2-3 MINOR (loosens a check): the walk road's defensive guards are only partly bound, and D3's content rule admits a ledgerless walk whose agent ran

Three survivors, none reachable through the runner today, each fail-open if reached:
- check_take.py:2241, the `problems[-1] != TAKE_ROW_NEEDED` clause alone can be removed with the suite green (R8's test feeds only `[real]`, which the `count` clause also catches); a `check()` result of `[TAKE_ROW_NEEDED, real]` would then have `real` stripped.
  (Removing the `count` clause alone is also green, but fail-safe: a second row-needed line stays as a reason.)
- check_take.py:2253-2255, the "no driver ledger beside the walk's transcript" line can be removed with the suite green; a ledgerless transcript would then read clean (the drive always writes the ledger before its checker runs).
- drive.py:2929 (`walk_files`, also walk_register's content rule): a walk folder holding `transcript.jsonl`, three `turn-N.jsonl` and `preflight.json` but no `driver-ledger.json` is accepted as "died before turn 1", and run.py's `died_before_turn_one` writes "its preflight passed and no turn ran" for it.
  Repro (scratch `.../scratchpad/w10r2/ledgerless_probe.py`): a committed w-0001 copied, its ledger removed, grade.json regenerated: `walk_files ACCEPTS: 24 files`, grade `{'graded': False, 'why': 'not graded, because its preflight passed and no turn ran, ...'}`.
  The runner cannot produce such a folder (the ledger write raises), so only a hand-built folder given to `WalkRepo.commit_walk` reaches it; walks are never counted.
Fix direction: the pre-turn alternative refuses a folder with a transcript or a turn record; a single-change test per clause.

## Notes (not findings)

- Builder's 38-witness registry was not re-run in full; every check above went through the test module's own machinery with the whole suite, which is the stronger form.
- Reviewer probes: `.../scratchpad/w10r2/mut.py` (15 mutants), `keep_probe.py`, `ledgerless_probe.py`, batch log `batch.out`.

## Modules athena must run

- None beyond the lane's list; this commit is a review file only.
