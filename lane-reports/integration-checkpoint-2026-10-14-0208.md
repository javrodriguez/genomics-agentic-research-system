# Integration lane checkpoint, 14 Oct 2026 02:08 EDT

Writer: the integration lane (sole writer), under orchestrator glitch-06.
Stopped on blockers: every remaining red needs a ruling or a change in another lane.
Nothing is active: no job, test or athena run. Nothing was pushed.

## Repository state

- Clone: `/Users/javrodher/aegis-builds/gap4-live-merge-20261014`, branch `gap4/live-merge-20261014`.
- Merges: `96b31d32` (harness `d56cebf0` into box `db252b9e`), `5ae385a8` (harness `beecc274`), `01e12172` (box `c6a6637e`). There were no conflict hunks (detail in `integration-merge-2026-10-14.md`).
- Fix commits: `daf4311b` (the sidecar launch and Codex transition fakes) and `fa98717e` (the box launch journal in the identity fakes).
- On the merged head, `copy_manifest.py --check` and `freeze.py --check` both report ok, with 390 files from 57 fragments.

## Athena

- `gap4-merge-01e1217-20261014T052729Z` (head `01e12172`, solo, full) has a verdict derived on the Mac of FAIL, rc 1.
  - Log SHA-256: `dc9136fe0f3f9f68ab0fa88f55faeffe8495f81d136bf92de67052df29b842b9`.
  - Step 1 (GARS): `Ran 1303`, OK (skipped=82).
  - Step 2: `run_checks: 230 of 263 commands passed`.
- `gap4-merge-fa98717-20261014T060727Z` (head `fa98717e`, `--only test_identity`): PASS-SUBSET, with 2 of 2 passing.
  It is a subset only, never a whole run.

## The 33 red lines of the full run, by owner

Cross-lane, fixed in `fa98717e` (2 lines): test_identity_evidence and test_identity_mode_evidence.

Cross-lane, held for a ruling (4 lines):
- The Codex transition against the harness's Codex tests.
- These lines: test_codex_adapter (plain, --witnesses and --generated-mutants) and test_codex_executed_refusal.
- On the harness head alone, both modules are green. On the merged head every Codex turn refuses `NotReady` in `run_take.exec_argv`.
- Whichever fix is chosen, it either bypasses that refusal in a fake or retires checks and witnesses.

Box-owned (red on box head `c6a6637e` alone):
- test_run_take and its --process-audit (2 lines): `MODULE_ATTRS` lacks `run_take.GEMINI_MODE_ROUTE_VARIABLES`. The box lane holds this for a ruling.
- test_sidecar, in both its w4c and w6g lines, and its --process-check (3 lines): `box/sidecar.py` imports `importlib.util` outside its allowlist (from `3a3716a0`).
  The Mac run on box head gives 154 tests, 9 failures.
- test_endstate --witnesses (1 line): the witness control reads "tests/test_sidecar.py: NOT CLEAN", which comes from the item above. All 13 of 13 witnesses are red.
- The w8e lint (1 line): lint_language finds 'always' twice in `COPIED.d/live-box-2026-10-14.json` line 7. The Mac run on box head gives the same 2 findings.

Harness-owned (red on harness head `beecc274` alone):
- test_transcript_view (1 line): `c35fc915` made "codex" a known harness, so the "unknown harness" refusal case is stale. The Mac run on harness head gives 20 tests, 1 failure.
- test_cp8_prep --witnesses (1 line): the anchor of the witness `adapter-class-at-call-time` in drive.py is gone since `c35fc915`. The Mac run on harness head gives 0 tests and 1 error.
- test_walk_runner --generated-mutants shard 8/12 (1 line): `drive.walk_files:drop-2:L19` survives, because no walk_runner test binds the launch-journal clause that `0d417a1d` added.
- test_gemini_adapter --generated-mutants shards 1-16 (16 lines): `submitted_mode` (`91eb1754`) is not bound by test_gemini_adapter's own tests.
  - Shard 1 on the harness head alone: 9 survivors.
  - On the merged head: 10 survivors. The no-journal return at L268 now also survives, because the box journal is present on every turn.
- test_round4 (1 line): the aggregate of all the above.
