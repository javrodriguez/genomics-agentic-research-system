# Integration lane checkpoint, 14 Oct 2026 03:34 EDT

Writer: the integration lane (sole writer), under orchestrator glitch-06.
This supersedes `integration-checkpoint-2026-10-14-0208.md`, which is left as written.
Nothing is active, and nothing was pushed.

## Repository state

- Branch `gap4/live-merge-20261014`; the head is the commit that carries this file.
- Re-merges:
  - `0d2085ee`: box `0f7cdbfd`.
  - `7b5a9dd4`: harness `86ca78e6`.
  - Neither had a conflict hunk.
- Fix commit `492af633`: the dead-walk control in test_walk_runner now strips the box's launch journals.
- Reports: `a1f74059` and this commit.
- On `492af633`, `copy_manifest.py --check` and `freeze.py --check` both report ok, with 398 files from 57 fragments.
- The watcher-stop search on the merged tree found one record without `ignored_newline_paths`: `tests/test_box_integration.py:1643`.
  That record feeds the lenient `drive.sidecar_health`, not endstate.

## Mac, before the battery (light gate before each)

All of these were green:
- test_codex_adapter: 43 OK, witnesses 13/13 red.
- test_codex_executed_refusal: 5 OK.
- test_identity_evidence: 9 OK.
- test_identity_mode_evidence: 8 OK.
- test_transcript_view: 20 OK.
- test_cp8_prep witnesses: 15/15 red.
- test_run_take: 45 OK, process audit with 0 problems.
- test_sidecar: 157 OK, process check ok.
- test_gemini_adapter: 139 OK.
- test_env_allowlist: 28 OK.
- test_walk_builders: 43 OK.
- lint_language and lint_pooling: clean.

## Athena

`gap4-merge-a1f7405-20261014T065439Z` (head `a1f74059`, solo, full) has a verdict derived on the Mac of FAIL, rc 1.
- Log SHA-256: `b312c38de92b6c4e1f2f1868a5eadf9f3569da000d11543d017f0aa93f837639`.
- Step 1: `Ran 1303`, OK (skipped=82).
- Step 2: `run_checks: 249 of 269 commands passed`.

The 20 red lines:
- **Cross-lane, fixed in `492af633`** (2 lines: test_walk_runner, test_round4).
  test_round4's only error was the same walk_runner test (`Ran 3584`, errors=1).
  Athena subset `gap4-merge-492af63-20261014T073256Z` read PASS-SUBSET, with 1 of 1 passing (test_walk_runner).
- **Harness-owned** (18 lines).
  The same reds and the same survivor lists appear on the harness's own subset `gap4-harness-ab-86ca78e-20261014T063637Z`, so the merge did not cause them.
  - test_walk_runner --witnesses: the witness `walk-launch-journal-not-a-turn` (`97fb09fe`) has no METHOD entry.
    It therefore runs against the R3 default `test_a_walk_that_dies_before_turn_one_is_committed_with_its_reason`, which it cannot turn red.
    Its own test is `R3DeadWalk.test_a_ledgerless_walk_with_only_a_launch_journal_is_refused`.
  - test_codex_adapter --generated-mutants: 9 survivors in `CodexAdapter._turn`'s executed-refusal path.
    These are `executed_turns.append`, `executed["refused"]` and the `ExecutedTurnRefused` raise.
  - test_gemini_adapter --generated-mutants, shards 1-16 (16 lines): 50 survivor lines in total.
    They include the launch-record dict at L388-390 and `executed['refused']` at L370.

No box-owned red remains in this run.
