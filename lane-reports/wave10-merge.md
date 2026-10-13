# Wave 10 merge — gap4/wave10-merge

Builder: the merge sub-agent assigned by glitch-2f (Lane-orchestrator), Tue 13 Oct 2026 (worktree `/Users/javrodher/aegis-builds/gap4-wave10-merge`, base `f14ab57b`, gap4/w9-cp6, athena PASS gap4-wave9-f14ab57-20261012T163235Z).
Written 02:56 EDT Tue 13 Oct 2026 (`date`).

## Merges (first parent, oldest first)

| Commit | What |
|---|---|
| 484337d4 | merge gap4/w10-walk-runner at 1f121c5c, --no-ff, clean (athena gap4-w10-1f121c5-20261013T055954Z PASS, battery 171/171) |
| 7f2b0b14 | merge gap4/w11a-codex-adapter at 7db238a0, --no-ff, clean (athena gap4-w11a-7db238a-20261012T202256Z PASS, 160/160) |
| 8f6fb305 | merge gap4/w11b-gemini-adapter at f1aa32fb, --no-ff, clean (athena gap4-w11b-f1aa32f-20261012T223941Z PASS, 159/159) |
| 37c6bc3f | merge gap4/w11c-walk-plan at e6a33ac0, --no-ff, clean (athena gap4-w11c-e6a33ac-20261013T052847Z PASS, 163/163) |
| 244f3fce | merge-owned: w11b's generated sweep into checks.d (16 shards) |

Each branch was confirmed at its verified sha before its merge; no existing branch was moved.

## Conflicts

None.
The four lanes touch disjoint files (24, 23, 23 and 6 paths against `f14ab57b`, 76 in all), each with its own `COPIED.d` fragment and `checks.d` file; w10's edits to other lanes' fragments (w1a, w7b, w8a, w8d, w9) are the only ones to those files.
The merged tree at 37c6bc3f equals the union: every path each lane changed has that lane's exact blob (checked path by path, 0 differ), and nothing else moved.

## Merge-owned addition (244f3fce)

glitch-2f's w11b ATHENA PASS entry (20:08 EDT Mon 12 Oct) named the w11b generated sweep as owed at the merge: w11b's own `checks.d` ran only the suite and its witnesses.
Added `checks.d/wave10-merge.txt` with the 16 shard lines the lane used (`--generated-mutants --shard i/16`, 1159 mutants), and `COPIED.d/wave10-merge.json` claiming both files, in the wave6-merge shape.
w11b's own files are untouched, so its athena-verified bytes stand.
Expected battery size on athena: 157 (wave 9) + 14 (w10) + 3 (w11a) + 2 (w11b) + 6 (w11c) + 16 (this file) = 198.

## Gates on the merge tree (Mac, light-ok before each, timeout -s INT, python3.13)

All exit 0 unless noted:
- `copy_manifest.py --check`: ok, 348 files from 52 fragments (wave10-merge included).
- `lint_language.py evals/gap-study-4/`: clean, 98 inputs, 23 excused lines on record.
- `lint_pooling.py evals/gap-study-4/`: clean, 98 files.
- `test_round4.module_problems()`: 0 problems.
- `build_draft --check` ok; `freeze --check` 348 owned paths; `walk_register --check` 0 walks.
- test_walk_plan 17 run; test_codex_adapter 42; test_gemini_adapter 138; test_walk_runner 75; test_agent_adapter 35; test_transcript_view 20; test_ci_job 23; all OK.
- New line proven: test_gemini_adapter `--generated-mutants --shard 1/16` (73 ran, 71 killed, 2 equivalent, 0 survived, 0 stale) and `--shard 16/16` (72 ran, 68 killed, 4 equivalent, 0 survived, 0 stale).
- test_scaffold: rc 124 at the 400 s cap (Mac load about 15-60 during the run); owed to athena, not a finding.

## Owed to athena (whole battery, --solo, a record cites it)

The whole battery on the merge head, including test_round4, test_scaffold, test_pipeline, all generated-sweep shards (w10 12, w11a whole, w11c 4, and the 16 new w11b shards for the first time), and every witness line.

## Not done here

w11d (1b847b3e) is not merged; it joins after its athena PASS, and its Q-w11d-6 binding (HARNESS_WORDS reading the Codex and Gemini names from their modules) applies at that merge.
No push, mirror, athena run or spend.

RESUME HERE: ready for athena.
