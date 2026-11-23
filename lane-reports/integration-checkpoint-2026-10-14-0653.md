# Integration lane checkpoint, 14 Oct 2026 06:53 EDT

Writer: the integration lane (sole writer), under orchestrator glitch-06.
This supersedes `integration-checkpoint-2026-10-14-0541.md`, which is left as written.
Nothing is active, and nothing was pushed.

## Repository state

- Branch `gap4/live-merge-20261014`; the head is the commit that carries this file.
- Re-merges:
  - `0afb6825`: box `6221c297`, the five real image locks.
  - `9588a563`: harness `840048ab`.
  - Neither had a conflict marker. The test_identity_mode_evidence hunks do not overlap; both are kept, with the merged-head Journal.
  - The `ce852b01` change to test_gemini_adapter carries through unchanged.
- On `9588a563`:
  - `copy_manifest.py --check`: ok, 403 files from 57 fragments.
  - `freeze.py --check`: ok, 404 owned paths.
  - The watcher-stop search finds only `tests/test_box_integration.py:1643`, which feeds the lenient `drive.sidecar_health`.

## Mac (light gate before each)

All of these were green:
- test_identity_mode_evidence 8 OK; test_identity_evidence 9 OK.
- test_gemini_adapter 143 OK; witnesses 114/114 red; generated-mutant shards 1-16 each 0 survived, 0 stale.
- test_codex_adapter 48 OK; witnesses 15/15 red.
- test_codex_identity 5 OK.
- test_pipeline 85 OK.
- test_walk_runner 79 OK.
- test_image 43 OK.
- test_live_box 35 OK.
- test_run_take 45 OK.
- test_sidecar 157 OK.
- test_preflight 48 OK.
- test_wave4_bindings 13 OK.
- test_env_allowlist 28 OK.
- test_walk_builders 43 OK.
- lint_language and lint_pooling: clean.

## Athena

`gap4-merge-7a5dfd7-20261014T101742Z` (head `7a5dfd7f`, solo, full) has a verdict derived on the Mac of FAIL, rc 1.
- Log SHA-256: `5676742158bd53effb3c4cb4ad469c843930dae047030dab6975b9c111b3e235`.
- Step 1: `Ran 1303`, OK (skipped=82).
- Step 2: `run_checks: 266 of 273 commands passed`.
- The launch waited for the harness subset `gap4-harness-c3-840048a-20261014T095541Z` (PASS-SUBSET, done) to finish.

All 7 red lines are box-owned and come from the real locks in `6221c297`.
I ran each check below on box `6221c297` alone, on harness `840048ab` alone and on the merged head, each on the Mac: each fails on the box head and the merged head and passes on the harness head.
- **test_egress** (2 failures): `EgressImageTest.test_the_egress_image_is_by_digest_and_copies_nothing` still expects `pending(lock) == ("base", "image_id", "squid")`. The egress lock now has no PENDING value.
- **build_draft.py --check** (2 lines, w5c and w8b): "the committed draft is missing or differs from what build_draft.py builds". The committed `prereg-draft.json` was built before the locks changed.
- **test_build_draft** (`Readiness.test_committed_writer`) and its witness group 6: the same stale draft.
- **test_holdout_digests** (`H1Draft.test_no_pre_freeze_draft_carries_the_holdout`, "committed bytes are the writer's"): the same stale draft.
- **test_round4**: the aggregate of the four failures above (`Ran 3681`, failures=4).

No harness-owned red and no cross-lane red remain in this run.
The draft is a record that `build_draft.py` writes, so rebuilding it is the box lane's call, or the owner's; this lane did not touch it.
