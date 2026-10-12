status: closed (awaiting review)

# Lane w8b-holdout-digests: Gap Study round 4, holdout digests at the freeze (ruling W8B-gap4-1)

Written Mon 12 Oct 2026, 09:07 EDT (`date`), by the lane's sole writer (Claude Opus 5.5), assigned by glitch-1b.
The ruling is Javier's own decision, typed in glitch-1b's window on Mon 12 Oct 2026 at 08:51 EDT: "holdout digests A".
Under option A, the holdout's salted fingerprints and its per-version count enter GARS only at the freeze commit, and until then nothing about the holdout leaves aegis.
Branch `gap4/w8b-holdout-digests`, base `98424794` (the verified wave 7 head).
Code commit `4ad2b531`; this report is report-only.
Nothing was pushed or merged.
No real holdout content was read or created (synthetic strings only), and no model, network, credential, brief, saved output or sealed path was used.

## What was built

1. **Pre-freeze draft carries nothing (build_draft.py).**
   `describe` no longer writes `holdout_salted_digests: PENDING`, and `holdout_rule` is `HOLDOUT_RULE`.
   `HOLDOUT_RULE` carries no count field and adds `digests_and_count_enter: "the freeze commit only"` and `ruling: "W8B-gap4-1"`.
   `prefreeze_holdout_problems` names either freeze-only field (`HOLDOUT_FREEZE_KEYS`) or any other `holdout_rule`.
   `finalize` refuses such a draft, so `write_draft` and `build` refuse it too.
   The holdout pending reason is removed.
   `validate_digests` is now called only by the freeze.
   It takes the source's count (the same positive number for every task version) and returns it, so there is no fixed 3 in GARS code.
   `prereg-draft.json` was regenerated through the writer only, and `build_draft --check` exits 0.
   Tests: H1, H2, and test_build_draft's R7.absent.
2. **The freeze writes the fields (freeze.py).**
   `--holdout-digests <file>` reads a digest-only source of the form `{"salted_sha256": {task: [hex, ...]}}`.
   A salt, a wording, any other key or a repeated key is refused.
   The freeze writes `holdout_salted_digests` and `holdout_wordings_per_task_version` into the frozen file; both are in `FREEZE_WRITTEN_KEYS`.
   `holdout_source_problem` refuses by name (`HOLDOUT_ABSENT`, naming W8B-gap4-1) when the source is not given or is not a file.
   It does so before any review, git or write step, in preview and in `--write`.
   Only a disposable `--rehearsal` may go without the source; it then writes neither field and prints `NOT REHEARSED: the holdout digests ...`.
   `draft_holdout_problem` refuses a draft that carries either field, both at the freeze and at `--check`.
   Tests: H3 to H8.
3. **Tests.** `tests/test_holdout_digests.py` holds H1 to H8, with 11 witnesses under rule B (each mutant compiled in memory; only its bound test is run).
   The freeze is driven through `freeze.main` against a temporary folder, with git, the review, the pins, `prepare` and the writer as fakes.

## Evidence (Mac; every command prefixed in the same command by `mac_slot.py light-ok &&` and `timeout -s INT 120`; Python 3.13)

- Red first on `98424794` (only the new test file added): 8 run, 7 failures, 5 errors, exit 1.
  H1 failed by assertion: `['holdout_salted_digests'] != [] : H1.draft committed: a freeze-only field`.
- Green at `4ad2b531`: test_holdout_digests 8/8, exit 0.
- Witnesses: 11/11 RED, exit 0.
  The witnesses are pending-stand-in (H1), writer-admits and rule-count-admitted (H2), freeze-skips-write (H3), absent-admitted and missing-file-admitted (H4), salt-admitted and uneven-admitted (H5), keys-not-allowed (H6), check-skips-draft (H7) and rehearsal-silent (H8).
  Two runner fixes came before green.
  First, a test's subtests repeat its id, so the outcome check compares the distinct failing methods.
  Second, H5 fails by assertion when a malformed source crashes instead of being refused; under salt-admitted it had raised KeyError.
- test_build_draft: 45/45, exit 0.
  Its changed witnesses were run one at a time with `--mutant`, each exit 1, with the bound method red by its clause.
  digests-pending and digests-count are red in Description.test_commitments (R7.absent).
  Collateral for those two: the builder's own refusal fires in every build, giving 13 Readiness failures and 13 errors; these are listed, never credited.
  digest-shape is red in Readiness.test_digest_shapes (R7.digest-shape) with no collateral.
  The athena witness groups 1-6 were not run on the Mac.
- Gates:
  - `build_draft.py --check` exit 0.
  - `freeze.py --check` exit 0 (276 owned paths).
  - `copy_manifest.py --check` exit 0 (276 files, 43 fragments).
- Regressions:
  - test_prereg_order 10/10.
  - test_prereg_status 4/4.
  - test_pipeline FreezeOutputs, FreezeDesign and FreezeCoverage: 15 tests through `-m unittest` by class (not the whole module), exit 0.
    FreezeCoverage includes the in-process `freeze.main --rehearsal --write` clone, so the rehearsal's no-source road is exercised.
- Lint: the new test, fragment, checks line and freeze.py are clean.
  build_draft.py shows the same 8 findings as at `98424794` (pre-existing prose in other passages).
- Not run: whole test_scaffold, whole test_pipeline, run_checks, freeze_rehearsal.py.

## Ownership (ruling W8B-gap4-1)

- New fragment `COPIED.d/w8b-holdout-digests.json`.
  It claims build_draft.py and prereg-draft.json (with its writer, Q-w7a-2) from w7a-draft-text, and freeze.py from w5b-cp5-pipeline.
  It also claims tests/test_holdout_digests.py, `checks.d/w8b-holdout-digests.txt` and the fragment itself.
  Each transfer is named in the old owner's own fragment entry.
- tests/test_build_draft.py was edited without transfer, and the edit is recorded in w5c-draft-ci's entry (the same road w7a took).
  The edits: R7.pending became R7.absent with two witnesses, fill_fake no longer plants digests, and the required-set exclusion changed.
  R34 now reads the draft's claim from the w8b fragment.
- The new checks.d line runs test_holdout_digests, its --witnesses, `build_draft --check` and `freeze --check`.

## Open questions for glitch-1b

1. **Rehearsal without a source (my call, inside the ruling).**
   A disposable `--rehearsal` with no `--holdout-digests` freezes without the two fields and prints NOT REHEARSED, rather than refusing.
   I did this because freeze_rehearsal.py (w8a's) cannot pass a source today.
   Keep this, or have freeze_rehearsal take a source and refuse without one?
2. **`holdout.py --check` is still in freeze_rehearsal.COMMANDS**, but no holdout.py exists in GARS.
   Under C4 it belongs in aegis (cp6-readiness 5.3), so the rehearsal will fail that step until someone rules on it.
3. **"Per version" is read as per task.**
   The count is `holdout_wordings_per_task_version`, keyed like the old validator ("one digest list per task").
   If a version means a task half, the source shape needs a ruling.
4. **The aegis side is still owed.**
   No aegis source exists today: no salt, no digest file and no loader for the holdout matcher.
   The plan text at lines 709 and 829, which says the public draft carries the digests, is now superseded by this ruling but has not been edited.

## Fold: glitch-1b's rulings Q7 and Q8 (written Mon 12 Oct 2026, 09:14 EDT, `date`)

Code commit `6c616d5a` sits on top of `8a833144`.
The rulings were Q7 (rehearsal exercises the digest path), Q8/Q10 (the holdout check stays in aegis and is owed until S9), and Q9 ("per version" means per task, as built).

1. **Q7.** `freeze_rehearsal` writes `synthetic-holdout-digests.json` in its temporary folder, beside the clone so the clone stays committed.
   The file holds the sha256 of fake strings, one list per task of the cloned draft, and never any holdout content.
   The rehearsal hands it to `freeze.py --holdout-digests`, and a "holdout digests" step checks both frozen fields (`holdout_written_problems`).
   `--no-holdout-digests` leaves the file out and records `NOT REHEARSED: the holdout digests ...` as a failing step, so that rehearsal is never all green.
   Tests: H9 and H10 (H10 reads the real freeze's output).
2. **Q8.** The `holdout.py --check` step is never run in the clone.
   `owed_step` fails it with `OWED: holdout.py --check lives in private aegis (ruling C4) and is wired with S9's landing ...`, so the rehearsal is not all green until S9 rewires it.
   `COMMANDS` is unchanged, so L11 and FreezeCoverage hold.
   Test: H11.
3. **Ownership.** freeze_rehearsal.py moved from w8a to w8b, and the transfer is named in w8a's fragment.
   tests/test_pipeline.py was edited without transfer, recorded in w8a's entry: PipelineOwnership's lane map now reads freeze.py and freeze_rehearsal.py from w8b.
4. **Regression I caused in `4ad2b531`.** Moving freeze.py out of w5b turned PipelineOwnership red.
   I had not run that class at the first hand-back; it is fixed in `6c616d5a`.

Evidence (Mac; `light-ok &&`, `timeout -s INT 120`, Python 3.13):
- Red first, with `8a833144`'s freeze_rehearsal.py restored byte for byte around the run: 11 run, 3 failures, 0 errors, exit 1, all by assertion (H9, H10 "the fold"; H11 holdout.py was run).
- Green: 11/11, exit 0.
- Witnesses: 16/16 RED, exit 0.
  The five new ones are rehearsal-skips-file and no-file-silent (H9), written-unchecked (H10), and owed-passes and owed-runs (H11).
- test_pipeline PipelineOwnership, FreezeCoverage, FreezeOutputs and FreezeDesign: 16 tests run by class, exit 0.
- test_walk_layout L11Gates: exit 0.
- test_build_draft: 45/45, exit 0.
- `copy_manifest --check` exit 0; `freeze.py --check` exit 0.
- Lint: freeze_rehearsal.py and the test are clean.

## Fold W8B-close-1: review round 1 (written Mon 12 Oct 2026, 09:26 EDT, `date`)

Code commit `19af7698` sits on top of `b533f53b`.
Review round 1 came back CHANGES with one MAJOR and two MINOR findings (`plans/gap-study-round-4/w8b-review-r1-2026-10-12.md`).

1. **W8B-R1-1 (MAJOR).** The synthetic digest generator now lives in freeze.py (`synthetic_digest`, `synthetic_holdout_source`, `SYNTHETIC_BOUND` = 8, two per task by default).
   `holdout_fields` now refuses, outside a disposable rehearsal, a source holding any synthetic digest of any of its tasks at an index below the bound.
   The refusal names the tasks and ruling W8B-gap4-1.
   `freeze_rehearsal` calls the generator from freeze.py, and its `finally` deletes the synthetic file unless `--keep`.
   I reran the reviewer's `probe.py` against the fold: `holdout_source_problem` still prints None, because that check only covers an absent file.
   The probe then stops at `holdout_fields` with `ValueError: the holdout digest source holds the rehearsal's synthetic digests (...all 9 tasks...); a real freeze takes only the salted digests from private aegis (ruling W8B-gap4-1)`.
   New test H12: a real freeze refuses the probe's file, and also refuses a single synthetic digest hidden at index 7 of another task; a rehearsal accepts the file; the file is gone after a rehearsal and kept with `--keep`.
   Witnesses: synthetic-admitted and synthetic-file-kept.
2. **W8B-R1-2.** No mutant or negative case plants the real count any more; 7 is used instead.
   This covers H5, H7 and H10 here, and test_build_draft's digests-count mutant and digest-shape cases.
   The ownership line above was reworded so it no longer quotes the count.
   The base-history note (98424794 holds the count and the stand-in) is left for Javier's publish decision; no history was rewritten.
3. **W8B-R1-3.** H3 to H6 now open with `hasattr` assertions.
   In a temporary detached worktree of `98424794` (removed after) with only the new test file: 12 run, 14 failures, 0 errors, exit 1, every one by assertion.

Evidence (Mac; `light-ok &&`, `timeout -s INT 120`, Python 3.13):
- Red first on `b533f53b`'s code: 12 run, 1 failure (H12 by assertion: "the generator lives in freeze.py"), exit 1.
- Green: 12/12, exit 0.
- Witnesses: 18/18 RED, exit 0.
- test_build_draft: 45/45, exit 0.
  Mutants digests-count (R7.absent) and digest-shape (R7.digest-shape): each exit 1, red by its clause.
- test_pipeline PipelineOwnership, FreezeCoverage, FreezeOutputs and FreezeDesign: 16 tests run by class, exit 0.
- `copy_manifest --check`, `freeze.py --check` and `build_draft --check`: each exit 0.
- Lint: freeze.py, freeze_rehearsal.py and the test are clean.
- `~/holdout-author` was never opened.
