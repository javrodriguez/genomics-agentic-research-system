# Wave 11 merge — gap4/wave11-merge

Builder: the merge sub-agent assigned by glitch-2f (Lane-orchestrator), Tue 13 Oct 2026 (worktree `/Users/javrodher/aegis-builds/gap4-wave11-merge`, base `2235dd46`, gap4/wave10-merge; see `lane-reports/wave10-merge.md` for w10, w11a, w11b and w11c).
Written 03:18 EDT Tue 13 Oct 2026 (`date`).

## Commits (first parent, oldest first)

| Commit | What |
|---|---|
| a53ec96f | merge gap4/w11d-labelling-tools at 1b847b3e, --no-ff, clean (athena PASS on 1b847b3e, 177/177, all 16 labelling sweep shards, per glitch-2f) |
| ab6c8b2b | bind Q-w11d-6: HARNESS_WORDS reads the Codex and Gemini names from their readers' tables, with tests |
| (this commit) | report only |

## Conflicts

None.
w11d adds 8 new paths of its own; the merged tree carries each with w11d's exact blob (checked path by path, 0 differ) and nothing else moved.

## Q-w11d-6 binding (ab6c8b2b)

`labelling/sheet.py`: HARNESS_WORDS["codex"] is now `("apply_patch", "update_plan", "exec_command") + tuple(transcript_codex.TOOL_ITEM_TYPES) + ("AGENTS.md",)` and HARNESS_WORDS["gemini"] is `tuple(transcript_gemini.GEMINI_TOOLS) + ("GEMINI.md",)`.
The words and their order are unchanged, so K4's pinned lists and TEXT_HARNESS_WORDS still hold as w11d left them.
Codex's internal tool names (apply_patch, update_plan, exec_command) are in no reader table, so they stay listed by hand, as do the instruction files.
Choice made in-plan: Codex's names come from TOOL_ITEM_TYPES (the three tool item types w11d already listed), not all of ITEM_TYPES; adding agent_message and reasoning would widen the refused words beyond what w11d's review settled.

Tests (`tests/test_labelling.py`):
- K4 now checks that every name of transcript_codex.TOOL_ITEM_TYPES and transcript_gemini.GEMINI_TOOLS is a harness word (runs under the generated sweep against each mutant).
- New TestHarnessWordsBinding builds sheet.py over stand-in tables and checks that a name added to either table becomes a harness word (also in TEXT_HARNESS_WORDS and harness_word) and a dropped one leaves; a second test pins the derived tuples against the real tables.
- Red first: on w11d's sheet.py (1b847b3e, the copied lists) the binding test fails ("'new_codex_item' not found"); on the fold it passes. The file was restored from a byte backup and compared with cmp.

Recorded in `COPIED.d/w11d-labelling-tools.json`, as a fold note on the sheet.py and test_labelling.py entries (the W8E-close-1 precedent: a merge fold is recorded in the owning lane's fragment).
The sweep's EQUIVALENT keys are not touched: sheet's entries sit at L49 to L64, above the edit.

## Gates on the merge tree (Mac, light-ok before each, timeout -s INT, python3.13)

All exit 0:
- `copy_manifest.py --check`: ok, 354 files from 53 fragments.
- `lint_language.py evals/gap-study-4/`: clean, 99 inputs, 23 excused lines; `lint_pooling.py evals/gap-study-4/`: clean, 99 files.
- `test_round4.module_problems()`: 0 problems.
- `build_draft --check` ok; `freeze --check` 354 owned paths; `walk_register --check` 0 walks.
- `labelling/sample.py --check` and `labelling/agreement.py --check` (no takes, no labels: the "not a pass on data" lines, exit 0 as on w11d).
- test_labelling: 109 tests OK; --witnesses 64/64 red, registry 64.
- Generated sweep, sampled: shard 1/16 (127 ran, 125 killed, 2 equivalent) and shard 9/16 (126 ran, 125 killed, 1 equivalent), 0 survived, 0 stale, 0 leaked; 2024 mutants generated.
- Targeted: every generated mutant of sheet.py on lines 66 to 92 (the changed region), 69 mutants, 0 survived, run through the module's own run_mutant.

## Owed to athena (whole battery, --solo, a record cites it)

The whole battery on this head: every checks.d line, including all 16 test_labelling sweep shards on the folded sheet.py, the 16 w11b shards added at the wave 10 merge, test_round4, test_scaffold and test_pipeline.
Expected battery size: 198 (wave 10 merge) + 20 (w11d's lines; 177 - 157) = 218.

No push, mirror, athena run or spend.

RESUME HERE: ready for athena.
