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
   `HOLDOUT_RULE` drops `wordings_per_task_version: 3` and adds `digests_and_count_enter: "the freeze commit only"` and `ruling: "W8B-gap4-1"`.
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
