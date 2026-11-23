# Lane w10-walk-runner: review round 1

Written Mon 12 Oct 2026, 13:45 EDT (`date`), by a fresh reviewer (Claude Opus 5.5), assigned by the Lane-orchestrator.
Reviewed: `f14ab57b..25d7b719` on `gap4/w10-walk-runner` (8aca2c9b, cb53102e, 17e7e129, 25d7b719).
No code was edited; this file is the only change.
Nothing was pushed, merged or spent; no model, network, container, credential, salt or holdout was used.

## Verdict

CHANGES (one MAJOR, one MINOR that loosens a check).

## What was verified (Mac, each run behind `mac_slot.py light-ok`, `timeout -s INT 120`, python3.13)

- Append-only claim on `check_take.py`: the base's bytes minus its `if __name__` block are a byte prefix of the new file, and both end in the same `__main__` block (scratch comparison of `git show f14ab57b:...` against the working file: prefix True, tail True).
  `drive.py` is not append-only, as the lane declares (three in-place edits named in its banner).
- `check_walk`'s "exactly one row-needed line" cannot mask a different failure.
  With `row_index=None, is_walk=False`, `check()` returns early only at check_take.py:1608 (script not a list, unreachable from `check4_walk`, which requires a non-empty list) and at :1748-1749 (the row-needed line, appended last, then returned).
  `TAKE_ROW_NEEDED` is emitted nowhere else, so every problem `check()` found before it is kept, and the assertion only strips that one line.
  Any other ending raises `CheckRefused`, so the drive raises and the walk is held (fail closed).
- No path commits a walk without `check.json`: `WalkRepo.commit_walk` takes its files from `walk_files` (drive.py:2988), which requires `WALK_CHECK`; `walk_register.content_problems` reads the same rule.
  Presence only; the content is not re-derivable (the lane's Q-w10-3), noted, not a finding.
- `tests/test_walk_runner.py`: 10 run, 0 failures, 0 errors, 0 skipped.
- Witnesses: 16/16 RED, in two batches of 8, each by assertion with its clause.
- The departure (config folder kept after a postflight refusal): its guard is right on the walk's own road (R4 binds both sides, and the `postflight-config-deleted` witness and my `teardown-guard-gone` mutant both go red), but see W10-R1-2.

## Findings

### W10-R1-1 MAJOR: the D1 walk road's tail and D2's row clause can be deleted with the suite green

Threat model: every guard red by assertion when removed.
The lane's witnesses bind only the two session bindings of `check_walk`; the rest of the walk road, which D1 promises reads "as for a take", is unbound.
Reviewer mutants, each applied through the test module's own mutant machinery (anchor asserted once by its `setUpModule`) and the whole of R1-R7 run: all 9 tests green for each of these:

- check_take.py:2257 `if (ledger.get("task"), ledger.get("half")) != (task_id, half_name):` → `if False:`
- check_take.py:2263 the ledger's `row`/`row_commit` check → `if False:`
- check_take.py:2265 `problems += environment_problems(path, ledger, pre, None)` deleted
- check_take.py:2271 the environment record's `row`/`row_commit` check → `if False:`
- check_take.py:2275 `problems += model_problems(...)` deleted
- check_take.py:2278-2280 `constant_problems`, `checkout_problems`, `pinned_instruction_problems` deleted
- check_take.py:2241 the `TAKE_ROW_NEEDED` assertion → `if False:` (defensive today; without a witness a later edit to `check()` would let the blind `[:-1]` strip a real problem)
- check_take.py:2321-2322 in `check4_walk`: `recorded_mode_problems` and `design_tree_problems` deleted
- drive.py:3295-3296 in `walk_identity_problems`: the `row`/`row_commit` clause removed (R2's take-identity test changes the session id too, so the session check alone turns it red)

Two structural causes: `drive` imports the real `check_take` before a witness module is compiled, so a `check_take` mutant reaches only R2's direct `check_walk` calls, never `check4_walk` through the drive; and no test feeds the walk road a transcript whose ledger, environment record, model, mode or arm is wrong.
Repro (one line): mutate `problems += model_problems(path, ledger["model_requested"])` to `pass` in check_take.py and run `tests/test_walk_runner.py`: 10 run, 0 failures.
Fix direction (lane's call): one walk-road test per binding, each on a copied folder with one record altered and read through `check4_walk` (or the drive with a `check_take` witness the drive itself imports), plus witnesses for each line above; and the take-identity test split so a right session id with row 0 alone is refused.

### W10-R1-2 MINOR (loosens the departure's guard): a slot-refused walk deletes another walk's kept config folder

walk_runner.py:124-129 (`run_one`'s finally) calls `_publish(driver, row, folder)` in `finally` for every walk with a string id, including one the runner itself refused before launch (walk_runner.py:137-139, "made nothing").
`_publish` reads the keep-guard from `rehearsals/<walk>/` but `driver.published(row, 0)` pops `_by_slot[row["slot"]]` (drive.py:2413).
So a row whose slot is not its walk id, on a driver that holds an earlier walk kept for a human, deletes that walk's config folder: the credential-like file the departure exists to keep, and the result reports `config: None`.
Repro (scratch, reusing the test rig): `run_walks([walk("w-0001")])` with a failing postflight (held, 1 config folder kept), then `run_walks([walk("w-0002", slot="w-0001")])` on the same driver: `[('launch-refused', None)]`, config folders left 0 (assertion `0 != 1`).
Also, the guard keys "the drive ran" off `teardown.json`, whose write failure is recorded, not raised (drive.py:2248-2252); a postflight refusal with an unwritten `teardown.json` would also delete the folder. Keying the keep on `postflight.json` being present and not ok, or on the take the driver holds for this walk's slot, closes both.
Fix direction: call `_publish` only after `driver.launch` was reached for this row (never for the runner's own pre-launch refusals), and add a witness.

## Notes (not findings)

- A walk that died before turn 1 gets `check.json` with `checker_reasons: []`, because the driver substitutes an empty reading when the checker did not run (drive.py:2335-2336); the file does not say the checker did not run.
  Its `route` and `grade.json` ("not graded, because ...") carry the truth, so nothing is counted wrong, but a `"checked": false` field would make the record honest on its own.
- Within the runner, the register entry's model and the driver ledger's `model_requested` come from the same row, so the walk road binding the transcript's model to the ledger (not to an independent row, as for a take) is consistent by construction.

## Modules athena must run

- None beyond the lane's list; this commit is a review file only.
