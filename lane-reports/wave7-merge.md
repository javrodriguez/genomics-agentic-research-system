# Lane report: wave7-merge (Gap Study round 4, wave 7 integration merge)

Sole writer of `gap4/wave7-merge`, assigned by the Lane-orchestrator glitch-1b.
Base: `d051bece`, the wave 6 merge head.
Written Mon 12 Oct 2026, merges and checks 00:12 to 00:15 EDT (clock read with `date`).
Nothing pushed, nothing amended or rebased.

## Merges (in order, each `git merge --no-ff`, each tip verified before merging)

| # | Lane | Tip merged | Code head | Close ruling | Merge commit | Conflicts |
|---|---|---|---|---|---|---|
| 1 | gap4/w7a-draft-text | ed123654 | 632ae20e | W7A-close-1 (`plans/gap-study-round-4/w7a-review-r1-2026-10-12.md`) | e941ce1f | none |
| 2 | gap4/w7b-walk-wiring | c33079a8 | 8178b30d | W7B-close-1 (`plans/gap-study-round-4/w7b-review-r1-2026-10-12.md`) | c1f36bc7 | 4 files, below |

Tip verification: both branch tips equalled the assigned shas, and each code head is an ancestor of its tip.

## Conflicts in merge 2 and their resolutions

No production-code file conflicted; drive.py, check_take.py and mode_binding.py merged clean from w7b.

- `tests/test_scaffold.py` `copied_modules()`: w7a's version taken (reads every fragment through `copy_manifest.load_fragments`, W6-claims-1); w7b's hand list with its added fragment dropped, as ruled for departure w7b-1.
- `tests/test_build_draft.py` `Claims.test_relocated_claims`: w7a's derived fragment list taken, with its R13.claims floor and named-path assertions; w7b's hand list dropped (departure w7b-1, ruled).
  w7b's changes to both test files were only these hand-list lines (9 changed lines against the base), so nothing else of w7b's was lost.
- `COPIED.d/w1a-cp1-scaffold.json` (reason for tests/test_scaffold.py): w7a's text kept, plus one sentence recording departure w7b-1 and its ruling at this merge (w7a's derived version taken, which reads w7b's fragment).
- `COPIED.d/w5c-draft-ci.json`: w7a's side kept, so build_draft.py and prereg-draft.json stay off w5c's fragment (transferred to w7a); the reason for tests/test_build_draft.py gains the same w7b-1 sentence.

Ownership after the merge: prereg-draft.json, build_draft.py and prereg.py are claimed only by `COPIED.d/w7a-draft-text.json`; drive.py, check_take.py, mode_binding.py and their transferred tests only by `COPIED.d/w7b-walk-wiring.json`.
Lane reports, checks.d and the other COPIED.d fragments merged without conflict.

## Checks on the merge head c1f36bc7 (Mac, Python 3.13.2, each behind `mac_slot.py light-ok` and `timeout -s INT 120`)

| Check | Exit | Result |
|---|---|---|
| copy_manifest.py --check | 0 | 261 files from 39 fragments |
| build_draft.py --check | 0 | the committed draft is what build_draft.py builds |
| freeze.py --check | 0 | 261 owned paths checked; no takes or freeze performed |
| probes4.py --check | 0 | 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems |
| mode_binding.py --check | 0 | graded 0 attempts; none committed yet |
| tests/test_build_draft.py | 0 | Ran 45, OK, 0 skipped |
| tests/test_prereg_status.py | 0 | Ran 4, OK, 0 skipped |
| tests/test_prereg_order.py | 0 | Ran 10, OK, 0 skipped |
| tests/test_walk_wiring.py | 0 | Ran 20, OK |
| tests/test_checker_body.py | 0 | Ran 29, OK |
| tests/test_mode_binding.py | 0 | Ran 8, OK |
| tests/test_wave6_bindings.py | 0 | Ran 2, OK |
| tests/test_scaffold.py TheImports | 0 | Ran 3, OK |
| tests/test_scaffold.py TheManifest.test_check_passes_on_the_folder | 0 | Ran 1, OK |

Not run here, by instruction: the whole test_scaffold, test_pipeline and run_checks; those are athena's.

Superseded by the addendum below (the athena run on 82cf6ae9 covers merges 1 and 2 only).

## Addendum: merges 3 and 4 (Mon 12 Oct 2026, 00:49 to 00:51 EDT, clock read with `date`)

Asked by glitch-1b after the report commit 82cf6ae9; athena was running on 82cf6ae9 from a bundle.
Both lanes branch from 82cf6ae9; both tips equalled the assigned shas, and each code head is an ancestor of its tip.

| # | Lane | Tip merged | Code head | Close ruling | Merge commit | Conflicts |
|---|---|---|---|---|---|---|
| 3 | gap4/w7c-spend-wiring | 5d20c3b3 | 54772733 | W7C-close-1 and W7C-close-2 (`plans/gap-study-round-4/w7c-review-r1-2026-10-12.md`) | cfaa3bc9 | none |
| 4 | gap4/w7d-rehearsals | 8994584c | 8fa9f8ef | W7D-close-1 (`plans/gap-study-round-4/w7d-review-r1-2026-10-12.md`) | 611ea72c | none |

No file conflicted, so no resolution was needed.
Ownership as ruled: batch.py and routing.py are claimed by `COPIED.d/w7c-spend-wiring.json`, review_kit/rounds.py by `COPIED.d/w7d-rehearsals.json`.
test_scaffold's identical-copy stand-in is w7d's `review_kit/launch.py` (departure w7d-1), kept.

Checks on the merge head 611ea72c (Mac, Python 3.13.2, each behind `mac_slot.py light-ok` and `timeout -s INT 120`):

| Check | Exit | Result |
|---|---|---|
| copy_manifest.py --check | 0 | 270 files from 41 fragments |
| freeze.py --check | 0 | 270 owned paths checked; no takes or freeze performed |
| routing.py --check | 0 | routing.json: 22 rows, 3 annotations, sound |
| batch.py --check | 1 (expected) | the base's three not-ready lines: pin_profiles empty, pin_profiles_status and spend_cap_markers_status not ruled (PENDING) |
| walk_register.py --check | 0 | 0 walks registered; nothing here is evidence about any walk |
| probes4.py --check | 0 | 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems |
| tests/test_spend_wiring.py | 0 | Ran 25, OK |
| tests/test_batch.py | 0 | Ran 118, OK |
| tests/test_routing.py | 0 | Ran 276, OK |
| tests/test_rehearsals.py | 0 | Ran 9, OK, 0 skipped |
| tests/test_scaffold.py TheImports | 0 | Ran 3, OK |
| tests/test_scaffold.py TheManifest.test_a_copy_that_differs_without_an_edited_entry_is_refused | 0 | Ran 1, OK |

Not run here: the whole test_scaffold, test_pipeline and run_checks; athena's.

RESUME HERE: merge head 611ea72c8c8b25acc5f097456e144a54605647e3; athena run_checks owed (orchestrator)
