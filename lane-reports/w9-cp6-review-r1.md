Status: review round 1 done, verdict PASS (no MAJOR)

# Lane w9-cp6 review, round 1

Written Mon 12 Oct 2026, 12:28 EDT (`date`), by a fresh reviewer (Claude Opus 5.5), for the Lane-orchestrator.
Reviewed `9961d0a2..a72f576f` on `gap4/w9-cp6` (code 09fd22d0, fold 4a035e84; reports 5b3c9535, a72f576f).
No code was edited. Nothing was pushed, merged, spent or launched. No holdout folder, salt or digest was touched.
The only aegis file read was the tool's own source, `workspaces/aegis/holdout/tools/holdout.py` (its arguments and what `--check` reads).

## Verdict: PASS

No MAJOR. One MINOR, against the threat-model clause "every guard is red by assertion when removed".
It does not loosen a check today, because Batch cannot reach the guarded state.

## Findings

- W9-R1-1 (MINOR): the "open registration is the slot's latest" guard has no witness.
  Where: `evals/gap-study-4/drive.py`, `open_registration`, line 3191 at a72f576f, `if reg.get("attempt") != max(...)`.
  Repro: a scratch mutant that replaces that condition with `if False:`, then run `K1Launch.test_a_take_is_checked_against_its_records_before_launch`. It stays green (SURVIVED).
  Reach: through Batch the state cannot happen. `takes.guard_registration` refuses a new registration while an earlier one is open ("human reconciliation required").
  So only a takes.json appended outside `commit_registration`, plus a caller other than Batch, reaches it.
  Ask: add one K1 case (a hand-committed ledger with an open attempt 1 under an outcome-closed attempt 2) and a witness. Or name the guard as defence in depth in the clause.

## Checked and found sound

- Every road to `run_take.launch`. It has one caller, `TakeDriver.launch` (drive.py:1981), and Batch reaches it only through `driver.launch(row)` (batch.py:995).
  `WalkDriver.launch` runs `launch_problems` first. A bare `TakeDriver` is closed by test_walk_wiring's W5-one-road AST check: no production module builds it or derives from it except WalkDriver.
  The `_folder` keyword is not reachable from outside: `WalkDriver.launch(row)` takes no keyword.
- The allow-list. `LAUNCH_FIELDS` is the planned row's full key set in prereg-draft.json (arm, task, half, wording, repeat, pressure, model, agent, half_cell, slot).
  `require_planned_row` binds every key of the planned row, so the check covers everything the frozen plan binds.
  Keys a launch row carries beyond the plan are not compared with takes.json, which stores `dict(row, attempt)`.
  Batch hands the same dict to `register` and to `launch`, so they cannot differ there. Noted, not a finding.
- Race between registration and launch. The launch reads takes.json only when `git status` is clean for it (`load_rows`).
  A second registrant is refused by `guard_registration` while a row is open. `os.makedirs` raises on a folder made after the `lexists` check, before any container exists.
- The folder-exists refusal and stranding. A crash after launch leaves files in an untracked `takes/<slot>/<N>`.
  That makes the repository dirty, so `commit_registration` refuses the restart's next registration ("requires a clean committed repository").
  The restart also refuses a re-registration of the open attempt N. Human reconciliation comes first either way, as before this lane.
  So the refusal fires only on an empty folder, which git cannot see (case 2b). There Batch commits `failed` with `drive_started` false, and `_replay` owes attempt N+1.
  `guard_registration` admits N+1 after a failed take that never started, so the slot is not stranded (case 5, through a real Batch). Fail-closed and correct.
- W8B-R2-2: `synthetic_digest_problems` re-applies `freeze.synthetic_tasks` to both the freeze commit's bytes and the file on disk. Under `--rehearsal-plan` it prints NOT CHECKED.
  A copy that is not a git repository skips it with the existing NOT CHECKED line. That is unchanged behaviour, and production runs in a clone.
- The holdout step. The aegis tool's `--check` reads only `--holdout`, `--gars` and `--sha`. Salt is read only under `--digests`, and only `--make-salt` writes.
  The rehearsal always passes the clone's synthetic fixture. The 9 fixture files are obviously fake ("Synthetic rehearsal opening xbh1o1 ...").
- Unwitnessed guards that are redundant (no loosening):
  - Field presence (`k not in row or k not in reg`): with the mutant, `require_planned_row`'s KeyError still refuses.
  - The relative-path refusal: with the mutant, a relative path is still refused as "missing" from the test's cwd, and the in-repo check resolves first.
  - The name check and `allow_abbrev=False` each went red under ad-hoc mutants.

## Evidence (Mac, `mac_slot.py light-ok` before each batch, `timeout -s INT 120`, /usr/local/bin/python3.13)

- test_cp6_wiring: 5 run, 0 failures, 0 errors, 0 skipped, rc 0.
- Witnesses: 18/18 RED in three batches of 6, rc 0 each; registry 18.
- test_walk_wiring: Ran 20, OK.
- Ad-hoc mutants, run in a scratch harness that wraps the test module's own `mutants()`. No file in the worktree was edited.
  - latest-unchecked: SURVIVED (W9-R1-1).
  - relative-admitted: SURVIVED (redundant).
  - walk-fields-missing (field presence): SURVIVED (redundant).
  - name-admitted: RED.
  - abbrev-allowed: RED.

## Note for the orchestrator (not a finding)

- With `--holdout-tool`, a rehearsal can now end all green, and its frozen record says `[0] holdout.py --check` with the tool's counts (9 task files, 27 wordings).
  The synthetic fixture has the real pack's shape, so a reader of the public record cannot tell the counts are synthetic.
  This is the design ruled under Q8, and the real check stays at the real freeze. Labelling the step "on the synthetic fixture" would keep the public record from over-reading.
