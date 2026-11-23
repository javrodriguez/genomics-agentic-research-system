# Wave 8 merge — gap4/wave8-merge

Builder: the merge sub-agent assigned by glitch-1b, Mon 12 Oct 2026 (worktree `/Users/javrodher/aegis-builds/gap4-wave8`, base 98424794).
Written 10:18 EDT Mon 12 Oct 2026.

## Merges (first parent, oldest first)

| Commit | What |
|---|---|
| 4432d418 | merge gap4/w8b-holdout-digests (42ba7f1b), --no-ff, clean (git's default message) |
| e50b69ef | merge gap4/w8c-spend-ruled (e21bfe8b), --no-ff, one ruled conflict |
| 77febf0d | merge w8e at its code commit b043a750, --no-ff, clean (not 6a3d8473, not 374b40d7) |
| 77eb1f34 | w8e's lane report from 374b40d7, byte for byte (report only) |
| 39e4d518 | fold W8E-R1-1 under ruling W8E-close-1 |
| 33c35671 | prereg-draft.json re-derived through build_draft.py's writer, nothing else |
| 9997aa12 | merge gap4/w8d-cp8-prep (ffd1936b), --no-ff, one conflict (union) |

## Conflicts

1. `COPIED.d/w7a-draft-text.json` (w8b × w8c), resolved as ruled at the wave 8 trial merge.
   Kept w8b's side, which transfers build_draft.py and prereg-draft.json to w8b.
   w8c's note "Regenerated, without transfer, by lane w8c-spend-ruled …" is carried verbatim to the end of the prereg-draft.json entry in `COPIED.d/w8b-holdout-digests.json`.
   prereg-draft.json was re-derived through build_draft.py's writer on the merged tree; the output was byte-identical to git's auto-merge.
   It carries the RULED spend_cap_markers_status and w8b's holdout behaviour: no holdout_salted_digests, no count, and digests_and_count_enter set to "the freeze commit only".
   Pending inputs went from 79 to 77: w8b removed the holdout entry and w8c removed the spend-status entry.
2. `COPIED.d/w8a-walk-layout.json` (w8b × w8d), on the fragment's own self-entry only.
   Each side appended a transfer note: w8b's for freeze_rehearsal.py (Q7/Q8, W8B-gap4-1) and w8d's for drive.py and walk_register.py (W8D-gap4-1).
   Resolved as the union, each note verbatim, w8b's first.
   No ruling was needed: the two notes concern different files.

## Fold W8E-R1-1 (ruling W8E-close-1)

In `tasks/approval-scope.json`, decisions[2].text, "as the contract and glitch-f3's (B) say" became "in line with the contract's ban and glitch-f3's (B)".
The fold is recorded in `COPIED.d/w8e-lint-reds.json`.
No file pins this task's bytes except prereg-draft.json's task_sha256, which moved in 33c35671 (the full-sha git grep found no other hits).
The re-derivation matches w8e's own 6a3d8473 on all six pins except approval-scope, which differs because of the fold.
The w8d merge moved no build_draft input: a re-run of the writer left the tree clean, so there is no further prereg commit.

## Gates on 9997aa12 (Mac, single modules, light-ok + timeout -s INT 120, python3.13)

All exit 0: copy_manifest --check (283 files, 46 fragments), build_draft --check, freeze --check, walk_register --check (0 walks), lint_language over the folder (clean, 81 inputs), lint_pooling over the folder (clean), the w8e checks.d line, test_task_approval_scope, test_number_fidelity, test_task_number_fidelity, test_task_scope_read, test_build_draft (45/45), test_holdout_digests and --witnesses (18/18 red), test_batch, routing --check, w8c's exact batch --check line, test_routing, test_spend_wiring, test_walk_layout and --witnesses (21/21), test_rehearsals and --witnesses (20/20), test_cp8_prep (4/4) and --witnesses (15/15), test_walk_wiring, test_ci_job.

On the w8b+w8c tree (e50b69ef), lint_language was 27 and lint_pooling was 9, as at the base.
After w8e (33c35671), lint_language was 1 (w8a-walk-layout.json:8, [always]) and lint_pooling was 0.
After w8d, both were 0.

The following did not run to completion within the 120 s cap and are owed to athena: test_build_draft --witnesses 1 to 6 (rc 124 each, on e50b69ef; each group exceeds 120 s on this Mac), test_round4 (rc 124 on e50b69ef), and test_pipeline (never run here, by rule).
test_pipeline's PipelineOwnership deserves particular attention on athena: w8b and w8d both move files that its lane map reads.
