status: closed

# Lane w8d-cp8-prep: Gap Study round 4, CP8 prep (ruling W8D-gap4-1)

Written Mon 12 Oct 2026, 09:22 EDT (`date`), by the lane's sole writer (Claude Opus 5.5), assigned by glitch-1b under Javier's standing delegation.
Branch `gap4/w8d-cp8-prep`, base `98424794` (the verified wave 7 head).
Code commits `9a47cad6` (code, tests, the ci.yml step) and `6b5c9b78` (ownership records, checks.d); this report is report-only.
Nothing was pushed, merged or dispatched, and no walk, model, network, Docker, credential, brief, saved output, holdout or sealed path was used.

## What was built (each item with its test)

1. W8A-R2-2: `walk_register.history_problems`, run by the CLI's `--check`.
   For each registered walk: exactly one non-merge commit in HEAD's history touches `rehearsals/<walk>/`; it is a walk commit (`drive.WALK_SUBJECT`, one parent, changing only that folder and `register.json`, which lists the walk); HEAD's tree at the folder is the tree that commit wrote (so a merge cannot rewrite it either); the folder on disk is HEAD's; a shallow history refuses.
   No git is read when no walk is registered.
   Under the test-only `--base`, history is read only with `--repo`; the gates run the bare `--check`.
   Test: `tests/test_cp8_prep.py` H1 (the probe: a later ordinary commit edits the walk's driver ledger and is refused; also a forged second walk-subject commit, a hand-committed walk, a ledger-editing merge, an uncommitted edit, a depth-1 clone; WalkRepo's own walk passes).
2. W8A-R1-5: `.github/workflows/ci.yml` gains the step "Walk register" (`python3 evals/gap-study-4/walk_register.py --check`), three added lines.
   `tests/test_ci_job.py`'s contract binds it as a single-command step beside plan 1013-1036's commands (`WALK`, `WALK_STEP`; R38.command, R38.before, R38.total), never in their place.
   No rule was weakened.
   Three mutations were added: walk-step-removed, command-walk, before-walk.
3. W7B-R1-4: `drive.adapter_class_problems`. Every adapter WalkDriver makes must be exactly `claude_code_adapter.ClaudeCodeAdapter`.
   The check sits inside an `adapter_for` property, so a later assignment cannot lift it.
   Test: A1 (an object of another class named claude-code, and a subclass, are refused; the real class passes; a reassigned maker is refused).
   W7B-R1-5: `drive.take_k_problems`. WalkDriver now requires `records_root` (walk_driver passes its root).
   It hands TakeRepo a take's records only from `<root>/takes/<slot>/<attempt>`, with the attempt that `commit_records` receives.
   Test: K1 (folder 1 handed over as attempt 2 is refused; a walk folder, another slot and another root are refused).
4. Q-w8a-1: `denials.py` is not edited.
   D1 proves it is round 3's reader: w1a's record says identical, and its own usage names gap-study-3.
   D1 also proves it is unreachable from round 4: no study module imports or names it; no CI step, checks.d line or freeze-rehearsal command runs it; `transcripts/` is not a record root; and drive's round 3 road is shadowed.
5. `costs.py`: the docstring's last two lines now name `batch.Batch` (w7c's wiring: before a block is registered, and `month_turn_allowed` again before each paid launch).
   Docs only, and the line count is unchanged.

## Evidence (Mac, each command prefixed by `mac_slot.py light-ok &&` and `timeout -s INT 120`, /usr/local/bin/python3.13)

- Red first, `test_cp8_prep` on the base code: 4 run, 4 failures, 0 errors, exit 1.
  H1 failed on `--repo` (SystemExit 2, through `must`), A1 failed because "an object of another class named claude-code was accepted", and K1 failed because "takes/s-k/1 handed over as attempt 2".
  D1's failure there was my own checks.d comment naming the file; after rewording, D1 is green on the base code.
  D1 is a proof-only item, so it has no behavioural red; its two witnesses carry it.
- Red first, `test_ci_job` with the contract extended and before the ci.yml step: 23 run, 7 failures, 0 errors, exit 1.
  Green: 23 run, 0 failures, exit 0.
  Mutants walk-step-removed, command-walk and before-walk: each exit 1, the one failure being test_commands, carrying `R38.command:`/`R38.before:python3 evals/gap-study-4/walk_register.py --check`.
  The three whole-file witness groups are athena-only by that file's rule; the registry is 116.
- Green: `test_cp8_prep` 4 run, 0 failures, exit 0. Witnesses: 9/9 RED (three batches, exit 0 each).
- Earlier witnesses stay red: test_walk_layout 14 OK and 21/21 RED; test_rehearsals 9 OK and 20/20 RED.
  For test_rehearsals, one line in history_problems was first reworded because it repeated R7's anchor `object_pairs_hook=no_duplicate_keys`.
  test_walk_wiring 20 OK (its witnesses included).
- Ownership readers: `test_pipeline.PipelineOwnership` OK; `test_scaffold.TheImports` 3 OK; `test_build_draft.Claims` 2 OK.
  `test_scaffold.TheManifest`, method by method (check_passes, copy_that_differs, fragment_must_carry_its_own_lane, every_entry_refusal_fires): OK each.
  The whole class ran past 120 s (exit 124, a timeout and not a failure), and its other methods were not run.
- Gates: `walk_register --check` exit 0 (0-walk line); `copy_manifest --check` exit 0 (276 files, 43 fragments); `freeze.py --check` exit 0 (276 owned paths).
- Lint: the whole study shows 27 language and 9 pooling findings, equal to the base `98424794` (archived copy); the one "always" moved with drive.py's reason from w8a's fragment to w8d's.
- Not run: whole test_scaffold, test_pipeline, run_checks, test_round4, test_ci_job witness groups.

## Ownership (ruling W8D-gap4-1)

`COPIED.d/w8d-cp8-prep.json` claims drive.py and walk_register.py (from w8a-walk-layout) and tests/test_ci_job.py (from w5c-draft-ci), each transfer named in the old owner's own entry.
It also claims tests/test_cp8_prep.py, checks.d/w8d-cp8-prep.txt and itself, and names the ci.yml step, which is outside the copy record.
Departure w8d-1, for ratification: costs.py's docstring edit is recorded in w5b's entry with no transfer, because `test_pipeline.PipelineOwnership` binds costs.py to w5b.

## Open questions

- Q-w8d-1: K1 refuses a drifted k at the commit, which comes after the take ran.
  The drift road is real: W7C-R1-3's hold refuses a paid launch before its folder exists, and a restart then gives k = attempt - 1.
  So a paid take could run and then be refused.
  Refusing before launch needs Batch to hand the attempt to the driver (`launch(row, attempt)`, which touches every fake driver) or the driver to read takes.json's registration. That is CP6's call.
- Q-w8d-2: the history rule is "exactly one commit ever touches a walk folder".
  Any future legitimate rewrite (for example a regrade writing grade.json) must be a new walk or a ruled exception.
- Q-w8d-3: round 4 has no denial reader for results.
  denials.py is round 3's, and claude_code_adapter keeps `permission_denials` per turn.
  CP7/CP8 should decide whether result.py prints denials beside each take.
- Pre-existing, not changed here: lint_language and lint_pooling over the whole study are red at the base (27 and 9 findings), so the CI job's "Language rules" and "Separation of rounds" steps would be red as the tree stands.

## Review round 1 fold (ruling W8D-close-1), Mon 12 Oct 2026 09:41 EDT (`date`)

Code commit `1667c988`, on top of `7136c955`.
Review record: plans/gap-study-round-4/w8d-review-r1-2026-10-12.md (CHANGES, five findings, all folded).

- W8D-R1-1 (MAJOR) and W8D-R1-2 (ruled append-only): `history_problems` now holds the register append-only over history.
  Every entry that a walk-subject commit's register lists must be listed at HEAD, identical.
  It reports, once per walk, either "not in HEAD's register" or "entry at HEAD is not the one walk commit <sha> wrote".
  The register on disk must be HEAD's.
  git is now read even with an empty register: no walk-subject commit passes, and a shallow clone refuses.
  New H1 cases cover a rewritten reason, a rewritten model, a deleted walk, a deleted then re-added walk (through WalkRepo), an uncommitted register edit, an empty register (passes) and its depth-1 clone (refused).
  H1's old final case was removed: bare `--check` on the real study now reads this repository's git, which test_box_integration's process guard refuses.
  The gate command and test_rehearsals' own bare `--check` cover that path instead (exit 0).
- W8D-R1-3: `drive.PRODUCTION_ADAPTER` is captured at import, and the adapter's module must be `claude_code_adapter`.
  A1 adds two cases: a fake that claims the production module's name, patched in after import, is refused by the captured class; a drive compiled under a patch captures the fake, which is refused by its module.
- W8D-R1-4: the docstring says "ONE WALK, ONE COMMIT" and names what the check cannot see.
  Amending the walk commit, a hand-made walk-subject commit and a `__class__` patch all pass; the backstop is CP8's full-sha pins and a protected branch.
- W8D-R1-5: the drive.py entry in the w8d fragment now says "strict by construction".
  lint_language goes from 27 to 26 findings with no w8d hits; lint_pooling stays at 9. The rest are left to the W8D-lint triage.

Evidence (each command run with `mac_slot.py light-ok &&` and `timeout -s INT 120`, /usr/local/bin/python3.13):
- Red first, with the new cases on the unfolded code: `test_cp8_prep` 4 run, 2 failures, 0 errors, exit 1.
  H1 failed with "a later commit that rewrote the walk's reason passed"; A1 failed with "AdapterIdentityRefused not raised: a patched class".
- Green: `test_cp8_prep` 4 run, 0 failures, 0 errors, exit 0.
- Witnesses: 14/14 RED, in batches, exit 0 each.
  The new ones are entry-uncompared, walk-dropped-admitted, register-disk-unchecked, adapter-class-at-call-time and adapter-module-unchecked.
  Two anchors needed fixing first. walk-subject-unchecked's anchor occurred twice, so the new loop reads `if not subject == ...`.
  adapter-class-at-call-time was first killed by the module check alone, so its case now uses a fake whose module is claude_code_adapter.
- Neighbours:
  - test_walk_layout: 14 OK, exit 0; the witnesses bound to walk_register and drive (content-rule-skipped, walk-folder-under-takes, freeze-unchecked, register-in-another-commit, freeze-at-head-unchecked, history-unchecked) are 6/6 RED.
  - test_rehearsals: 9 OK and 20/20 RED, exit 0.
  - test_walk_wiring: 20 OK, exit 0.
  - test_ci_job: 23 OK, exit 0.
- Gates: `walk_register --check` exit 0 (0-walk line), `copy_manifest --check` exit 0 (276 files, 43 fragments), `freeze.py --check` exit 0.

## Review round 2 fold (ruling W8D-close-2), Mon 12 Oct 2026 09:55 EDT (`date`)

Code commit `d41f4495`, on top of `5a28beeb`; the round 2 record is in w8d-review-r1-2026-10-12.md.

- W8D-R2-1 (MAJOR): both of `history_problems`' git logs use `--full-history`: the register's walk-subject commits, and each walk folder's commits.
  Without it, git's default simplification pruned a merge side, so a walk dropped by `git merge -s ours` in either direction passed with a false 0-walk line.
  H1 gains two cases, both refused: P4a, a walk committed through WalkRepo on a side branch and merged into main with `-s ours --no-ff`; P4b, a branch from before the walk merges main with `-s ours`, then main fast-forwards to it.
  New witness: register-log-simplified, which drops `--full-history` from the register log.
- W8D-R2-2: no new check.
  walk_register's docstring and drive.py's comment beside PRODUCTION_ADAPTER now name the import-or-reload-under-patch road (a fake whose `__module__` is claude_code_adapter, captured as the production class) beside the `__class__` limit.
  The backstop stays CP8's full-sha pins and a protected branch.
- Departure w8d-2 was ratified. ci.yml's step order is unchanged; w8e owns the lint reds.

Evidence (each command run with `mac_slot.py light-ok &&` and `timeout -s INT 120`, /usr/local/bin/python3.13):
- Red first, with the P4a and P4b cases on the unfolded code: `test_cp8_prep` 4 run, 1 failure, 0 errors, exit 1.
  The failure was "a walk dropped by a branch that merged main with -s ours (P4b) passed: ok, having registered 0 walks".
- Green: `test_cp8_prep` 4 run, 0 failures, 0 errors, exit 0.
- Witnesses: 15/15 RED in five batches (3, 3, 3, 4, 2), exit 0 each.
- Neighbours:
  - test_walk_layout: 14 OK, exit 0; the witnesses content-rule-skipped, register-in-another-commit and history-unchecked are 3/3 RED.
  - test_rehearsals: 9 OK and 20/20 RED, exit 0.
  - test_walk_wiring: 20 OK, exit 0.
- Gates: `walk_register --check` exit 0 (0-walk line), `copy_manifest --check` exit 0 (276 files), `freeze.py --check` exit 0.
- Lint: lint_language 26 findings and lint_pooling 9, none in w8d's files.
