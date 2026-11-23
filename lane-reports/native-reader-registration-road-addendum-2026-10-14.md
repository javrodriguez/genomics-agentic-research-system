# Gemini native-reader registration: the acceptance-walk road and a walk the runner made (addendum)

Parent: `628489415`. Writer: Claude Code harness lane, 14 Oct 2026 03:16 EDT, under glitch-06's order after the review `review-harness-registration-fix-codex1.md` (fd4177e0: CHANGES, findings 1 and 2).
The earlier registration reports stay as written; this addendum supersedes their claims about which walk can register.
All fixtures are test fixtures in throwaway scratch repositories; no acceptance record was committed or written into the study folder.

One departure, flagged: findings 2 and 1 land in one commit, not one each, because the finding-1 gates can only be exercised on a walk the finding-2 road made.

## Finding 2: a real Gemini walk can now reach the gate

- `drive.walk_driver` builds its adapters with `harness_adapter_for`, so a Gemini walk runs on the same road as a Claude walk.
  A Codex walk does too once its `rollout_for` road exists; until then a Codex walk refuses before a turn.
  `WalkDriver` still admits only each harness's exact production class.
- `walk_runner._run_one`: when the drive stops with `drive.NativeCrossCheckPending` (after its cleanup, ledger and scan) and its containers were removed, `_commit_pending` commits the walk through `WalkRepo` with every record it made.
  `check.json` is `pending_walk.check_doc` and `grade.json` is `run.grade_walk`'s pending document, both derived from the driver ledger alone.
  The state is `pending-native-reader`: never graded, never counted as rehearsal coverage, never re-run (its id is registered), and the runner moves on.
- The same stop with a container left behind is held, and every other hold is unchanged (R12Pending in `tests/test_walk_runner.py`, run on athena).
- `run.grade_walk` returns the pending document for a ledger whose cross-check is pending, so `run.walk_problems` regrades a pending walk to the same bytes.
- `walk_regrade.py` (new): after a reader is registered, `regrade_doc` re-derives the cross-check (the one shared join) and the grade from the walk's committed bytes.
  `write_regrade` writes `rehearsals/<walk>/regrade.json` once.
  `commit_regrade` scans it and commits it alone under `Regrade one pending walk; never counted`.
  `regrade_problems` (`--check`) re-derives every committed regrade to its bytes.
  The walk's own commit and records are never touched.
  A grader that raises refuses the whole regrade.
  The checker's reading and route are not re-derived (they need the design view); `check.json` keeps saying the checker never ran.
- `regrade.json` joins the walk folder's closed map (`drive.WALK_REGRADE`, kind ledger).

## Finding 1: the gate now proves the runner made the walk

`native_reader_registration.acceptance_problems` now requires all of the following:

- **The walk commit.** The oldest commit touching the walk folder has `WALK_SUBJECT`.
  It adds exactly `rehearsals/<walk>/**` plus `register.json`.
  Its register is its parent's with exactly this entry appended.
  Any later commit touching the folder must be a regrade commit of `regrade.json` alone.
- **The two records.** `check.json` is byte for byte the runner's pending check record.
  `grade.json` is byte for byte `run.grade_walk`'s pending document.
- **The driver ledger.** It has the full take schema of a native-session vendor walk (`LEDGER_KEYS`).
  It names the register entry's task, half, wording, arm and model, and agent `gemini` at `0.64.0`.
  It has no row and no transcript, and records the pending cross-check.
  `environment.json` must re-hash to its ledger record.
- **The launch journals.** Each turn's launch journal passes `vendor_provenance.launch_facts` against the registered invocation.
  The take container comes from `launch.json`; the model, mode and sent line from the ledger; the resumed session from turn 1's init.
  The working folder and the stream folder are the journals' own, but must be one value across every turn.
  Each stream name must be its turn's.
- **The verify output.** `verify` prints the walk commit's author and committer next to the acceptance and review commits.

Limits, stated plainly:

- These are local git records. A person who can run the real road can make a real walk; what the gate now refuses is a walk fabricated by hand.
- The journals' working folder and stream folder are only checked for consistency, never against an outside record of the run.
- The final guarantee stays procedural: Javier's acceptance commit, made in his own window.
- The acceptance record and the review live in `native-readers/`, which no record ledger claims.
  So the acceptance commit must also add both to `COPIED.d/live-harness-foundation.json` (status new), or `copy_manifest.py --check` fails.
  This is named for the acceptance step, not built.

## Verification (every batch behind a light gate)

**Tests.**
- `tests/test_pending_walk.py` (new) runs 18/18.
- The road is the real one: `WalkDriver` with `harness_adapter_for`, the production `GeminiAdapter` on a fake box that answers the Gemini execs and grows the native session file, `walk_runner.run_walks`, and `WalkRepo`.
  A wrapper around `run_take.run_turn` writes each turn's launch journal in the box's schema, which the box lane's `run_turn` writes on the merged head.
- What the module covers:
  - the pending commit, and the held case;
  - every registration gate refusing for its own reason (moved here from the hand fixtures of fd4177e0 and cfe5269a);
  - a positive registration and its single mutations;
  - the coverage floor, and the synthetic marker in each of three places;
  - the reviewer's hand-fabricated walks:
    - placeholder `check.json` or `grade.json`;
    - a ledger key dropped;
    - `environment.json` altered;
    - a journal off its invocation, or in another folder, or naming another stream;
    - a ledger with another version or without a pending cross-check;
    - a commit with another file;
    - a rewritten register entry;
    - a hand commit under another subject;
    - a folder missing its grade;
  - the regrade road.

**Neighbour suites (all OK).**

| Suite | Result |
|---|---|
| `test_native_reader_registration` | 5/5 (the shared join and the tool) |
| `test_vendor_checker_road` | 5 |
| `test_vendor_take_records` | 4 |
| `test_native_history_record` | 3 |
| `test_cp8_prep` | 4, witnesses 15/15 red |
| `test_walk_layout` | 14, witnesses 21/21 red |
| `test_walk_builders` | 43 |
| `test_walk_wiring` | 20 |
| `test_executed_turn_refusal` | 10 |

**Mutants.** 21 in-memory mutants against `test_pending_walk`; 20 killed.
The survivor, "pending not required" in `_ledger_problems`, is equivalent: `_records_problems` derives `check.json` through `pending_walk.check_doc`, which refuses the same ledger with the same words, so deleting either guard leaves the other.

**The reviewer's witnesses.**
`witness_registration_fix.py` builds on the hand-fixture class this fold removed, so it errors at setup and proves nothing by itself.
Each of its attacks is re-staged on a road-made walk in `FabricatedWalks` and `Gates`.

**Not run here (athena).** `test_walk_runner` (R12Pending, its four own mutants, and the A3 witness binding) and every generated-mutant shard.
