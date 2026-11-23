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

Superseded by the addendum below.

## Addendum: merge 5 (Mon 12 Oct 2026, 02:08 to 02:10 EDT, clock read with `date`)

Asked by glitch-1b on head 818ccb70. The lane branched from 818ccb70; the tip equalled the assigned sha and the code head is its ancestor.

| # | Lane | Tip merged | Code head | Close ruling | Merge commit | Conflicts |
|---|---|---|---|---|---|---|
| 5 | gap4/w8a-walk-layout | 82a2bbc7 | 98c3a3a2 | W8A-close-1 and W8A-close-2 (`plans/gap-study-round-4/w8a-review-r1-2026-10-12.md`) | 765cb16a | none |

Clean merge (20 files); no resolution needed.

Checks on the merge head 765cb16a (Mac, Python 3.13.2, each behind `mac_slot.py light-ok` and `timeout -s INT 120`):

| Check | Exit | Result |
|---|---|---|
| copy_manifest.py --check | 0 | 273 files from 42 fragments |
| freeze.py --check | 0 | 273 owned paths checked; no takes or freeze performed |
| walk_register.py --check | 0 | 0 walks registered; nothing here is evidence about any walk |
| routing.py --check | 0 | routing.json: 22 rows, 3 annotations, sound |
| batch.py --check | 1 (expected) | the same three not-ready lines: pin_profiles empty, pin_profiles_status and spend_cap_markers_status not ruled (PENDING) |
| probes4.py --check | 0 | 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems |
| tests/test_walk_layout.py | 0 | Ran 14, OK, 0 skipped |
| tests/test_rehearsals.py | 0 | Ran 9, OK, 0 skipped |
| tests/test_spend_wiring.py | 0 | Ran 25, OK |
| tests/test_walk_wiring.py | 0 | Ran 20, OK |
| tests/test_drive_commit.py | 0 | Ran 31, OK |

Not run here: the whole test_scaffold, test_pipeline (w8a edited it) and run_checks; athena's.

Superseded by the addendum below (athena's run on 22b320be: 144 of 145).

## Addendum: the R5.case fix after athena's run on 22b320be (Mon 12 Oct 2026, 03:39 to 05:16 EDT, clock read with `date`)

Asked by glitch-1b. athena passed 144 of 145 on 22b320be; the one failure was `checks.d/w7d-rehearsals.txt:5`, `tests/test_rehearsals.py --witnesses`, witness `folder-by-path` FAIL (not RED).
Cause: the mutant looks a walk's folder up by path, `(base / walk).exists()`; R5.case registered "W-1" beside a folder "w-1/", which a path lookup finds only on a case-blind filesystem (APFS), so on athena's case-sensitive ext4 the mutant behaved like the guard and survived.

Fix, test-only, commit 5cd1056d: `tests/test_rehearsals.py` gains `case_blind(base)`, which patches Path.exists, is_dir, is_file, is_symlink and rglob so a path under the rig resolves its name by case (read through os.listdir, never the patched methods), as APFS does, while iterdir stays exact.
R5.case keeps its real-filesystem leg and adds a second leg under `case_blind`, with a non-vacuity assertion that `W-1` is a directory under the simulation and the listing is unchanged; its assertions carry `R5.case (case-blind)`.
The guard is not weakened: walk_register.py is unchanged, and the exact-name match must refuse "W-1" under both legs.
Recorded in `COPIED.d/w7d-rehearsals.json` (the owning fragment's reason for tests/test_rehearsals.py).

Checks on the Mac (Python 3.13.2, `mac_slot.py light-ok`, `timeout -s INT 120`):

| Check | Exit | Result |
|---|---|---|
| tests/test_rehearsals.py | 0 | Ran 9, OK, 0 skipped |
| tests/test_rehearsals.py --witnesses | 0 | 20/20 red; folder-by-path RED by R5.case, collateral none |
| walk_register.py --check | 0 | 0 walks registered |
| copy_manifest.py --check | 0 | 273 files from 42 fragments |
| freeze.py --check | 0 | 273 owned paths checked |

How it was shown to bite on a case-sensitive filesystem: a case-sensitive disk image could not be made (hdiutil create timed out), so a scratch driver (not committed) emulated one on the Mac by making Path.exists, is_dir, is_file and is_symlink answer False under a w7d- rig unless every component is listed by its exact name (armed check: `w-1` found, `W-1` not).
Under that emulation, with mutant folder-by-path:

| Test text | Run | Exit | Result |
|---|---|---|---|
| 22b320be (before the fix) | whole module | 0 | no failures: the mutant survives, athena's FAIL reproduced |
| 22b320be | R5.case's method only | 0 | Ran 1, OK: the mutant survives |
| 5cd1056d (the fix) | R5.case's method only | 1 | FAIL with AssertionError `R5.case (case-blind)`: RED |
| 5cd1056d, no mutant | whole module | 0 | Ran 9, OK |

A sweep of all 20 mutants under the emulation found 16 RED by the strict rule. In the other four (folder-by-path, round3-usage, schema-by-value, silent-empty), the bound method FAILed in three and the run then hit the 120 s cap in a later test; in schema-by-value the cap came before its bound method ran. That timeout comes from the emulator, not the suite: it lists the Mac's temp folder (about 266,000 entries) on every path query.
The emulated sweep is not counted as evidence beyond the folder-by-path rows above; athena's run_checks on this head is the authority for ext4.

RESIDUAL: diskimages-helper pid 97343 (started 03:39:52, parent 1) is most likely left from the failed hdiutil create; not killed, since it is a system helper and its owner is not proven.

RESUME HERE: merge head 5cd1056d474f95c448d9d05f6c95a4f946b605b6; athena run_checks owed (orchestrator)
