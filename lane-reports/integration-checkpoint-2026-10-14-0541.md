# Integration lane checkpoint, 14 Oct 2026 05:41 EDT

Writer: the integration lane (sole writer), under orchestrator glitch-06.
This supersedes `integration-checkpoint-2026-10-14-0334.md`, which is left as written.
Nothing is active, and nothing was pushed.

## Repository state

- Branch `gap4/live-merge-20261014`; the head is the commit that carries this file.
- Re-merges:
  - `2189a8e5`: box `0dbe18ed`.
  - `71b1cc7f`: harness `9649aa0a`.
  - Neither had a conflict marker. The harness lane mirrored the R3DeadWalk hunk byte for byte, so the merged file is the harness lane's text.
- Fix commit `ce852b01`: test_gemini_adapter A11 and A14 now read the box's own launch journal.
- On `ce852b01`, `copy_manifest.py --check` reports ok (402 files from 57 fragments), and so does `freeze.py --check` (on `71b1cc7f`).
- The watcher-stop search finds only `tests/test_box_integration.py:1643`. That record feeds the lenient `drive.sidecar_health`.
- Not merged:
  - The five real image locks had not landed on the box branch by 05:03.
  - Harness `a36a5743` is newer than the green subset and touches `tests/test_identity_mode_evidence.py`. Both wait for the next re-merge.

## Mac (light gate before each)

All of these were green:
- test_walk_runner: 79 OK, witnesses 72/72 red.
- test_codex_adapter: 44 OK, witnesses 13/13 red.
- test_gemini_adapter: 143 OK, witnesses 114/114 red; generated-mutant shards 1-16 each 0 survived and 0 stale.
- test_identity_evidence: 9 OK.
- test_identity_mode_evidence: 8 OK.
- test_walk_wiring: 20 OK.
- test_walk_builders: 43 OK.
- test_env_allowlist: 28 OK.
- test_run_take: 45 OK.
- test_sidecar: 157 OK.
- test_live_box: 35 OK.
- test_box_integration: 61 OK.
- test_pending_walk: 18 OK.

## Athena

`gap4-merge-a7799ac-20261014T090400Z` (head `a7799aca`, solo, full) has a verdict derived on the Mac of FAIL, rc 1.
- Log SHA-256: `0f0c4f7593f60d5eb74879e9c73fc7dfecc096c8a000f7f2fecceb66e225c130`.
- Step 1: `Ran 1303`, OK (skipped=82).
- Step 2: `run_checks: 268 of 271 commands passed`.

The 3 red lines are all harness-owned, and each is red on harness `9649aa0a` alone on the Mac:
- **test_pipeline** `FreezeCoverage.test_rehearsal_plan_runtime_commands_accept_only_disposable_placeholder`.
  `run.py --all` in the disposable copy fails with `ModuleNotFoundError: No module named 'pending_walk'`.
  `run.py` imports `pending_walk` since `15429361`, and the rehearsal copy does not carry that file.
  Harness head on the Mac: 85 tests, 1 failure. The merged head gives the same result.
- **test_round4**: this is the same test_pipeline failure (`Ran 3648`, failures=1).
- **w8e lint**: lint_language finds 'consisten' twice at `COPIED.d/live-harness-foundation.json:127` ("consistency is a claim about a rate").
  The harness head on the Mac gives the same 2 findings.

No box-owned red and no cross-lane red remain in this run.
