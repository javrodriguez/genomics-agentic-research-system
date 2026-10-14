# Integration lane checkpoint, 14 Oct 2026 11:36 EDT

Writer: the integration lane (sole writer), under orchestrator glitch-06.
This supersedes `integration-checkpoint-2026-10-14-1010.md`, which is left as written.
Nothing is active, and nothing was pushed.

## Repository state

- Branch `gap4/live-merge-20261014`; the head is the commit that carries this file.
- `e0a4f957`: the ADAPTER_CHECK_SHA256 repin to `47cdad38…2717`, as ruled.
  `adapter_class_problems` is byte-identical to `c35fc915`'s.
- `e3309476`: the box merge of `d65d81b8`. No conflict marker; the repin is kept.
- `bfed7c44`: the harness merge of `e3f5010b`. One conflict hunk, `R6.unpinned`, resolved with the harness lane's text.
- `5ac04498`: this lane's own error, corrected.
  The `bfed7c44` resolution took the harness lane's whole test_build_draft file, which dropped the box lane's `NEW_FOLDER_RESIDUAL` lines.
  I redid the three-way merge, taking the harness lane's text only in that one hunk.
  The Mac showed test_build_draft 2 failures before the fix and 47 OK after.
- On `bfed7c44`:
  - `build_draft.py --check`: ok, so the draft was not regenerated.
  - `batch.py --check`: exit 0, `batch: routing.json ready`.
  - `copy_manifest.py --check`: ok, 412 files.
  - `freeze.py --check`: ok, 413 paths.
  - The watcher-stop search is unchanged: one lenient hit, at `tests/test_box_integration.py:1752`.

## Mac (light gate before each)

All OK:
- test_claude_code_adapter 19.
- test_stub_take 19.
- test_walk_layout 14.
- test_build_draft 47, after `5ac04498`.
- test_routing 282.
- test_batch 118.
- test_spend_wiring 25.
- test_drive_ownership 17.
- test_ownership 25.
- test_settings_guard 5.
- test_rules_scanner 8.
- test_take_config 9.
- test_run_take 47, process audit with 0 problems.
- test_live_box 38.
- test_egress 22.
- test_wave4_bindings 13.
- test_walk_builders 43.
- test_walk_wiring 20.
- test_drive_loop 27.
- test_cp6_wiring 5.
- test_cp8_prep witnesses 15/15 red.
- test_pending_walk 21.
- test_box_integration 61.
- test_walk_runner 79.
- lint_language and lint_pooling: clean.

test_env_allowlist was not in this round's Mac set.

## Athena

`gap4-merge-5ac0449-20261014T150002Z` (head `5ac04498`, solo, full) has a verdict derived on the Mac of FAIL, rc 1.
- Log SHA-256: `cb663a69514bd848d1e64712f94852844875e195e1033fbc287f00c6e748bd09`.
- Step 1: `Ran 1303`, OK (skipped=82).
- Step 2: `run_checks: 269 of 272 commands passed`.

The 3 red lines are all box-owned. The failing checks fail on box `d65d81b8` alone too (Mac: 27 tests, 2 failures and 2 errors).
- **test_env_allowlist and its `--witnesses`** (2 lines): `Refused: a claude-code turn names its model exactly once by --model`.
  Box `d3fd5305` made `exec_argv` refuse a claude-code turn without `--model` and the inline `--settings`.
  The E2 test's Claude turn argv is `["claude", "-p", "x"]`.
  The fake needs the box's new launch form; that is a test update for the lane that changed `exec_argv`.
- **test_round4** (1 line): the same E2 failures (`Ran 3780`, failures=1, errors=2).

No harness-owned red and no cross-lane red remain.
