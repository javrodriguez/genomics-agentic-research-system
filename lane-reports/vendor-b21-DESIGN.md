Status: needs-review (round 1, design stop)

# vendor-b21 design: promoting codex and gemini into the bookkeeping TABLE

Local executor, Tue 20 Oct 2026, 12:18 EDT (16:18 UTC), on `28b46165` (B20), branch lane/vendor-b21-20261020.
Rulings B21-1 to B21-6 are glitch-26's, under Javier's standing delegation.
Round 1 is this note and no code.

## 0. The problem, as reproduced

GPT walk w-o45 (gpt-6.1-sol, explain-not-act trap, on `28b46165`) was held at its operator step with "drive raised UnknownHarness: harness 'codex' has no bookkeeping entry (known: ['claude-code'])".
The road: drive.py:2380 `_excluded(rel, harness)` -> drive.py:2418-2422 `_excluded` -> `_endstate.harness_run_tree_exclusions(harness)` -> graders/endstate.py:342-344 -> `hb.entry()` (harness_bookkeeping.py:178-185), which knows TABLE alone.
codex and gemini live only in `VENDOR_CANDIDATES` (harness_bookkeeping.py:105-172, the dict at 115), which `entry()` never reads.
The same refusal stops production grading: `Evidence.load` -> `_read_ledger` -> `agent_of` (endstate.py:321-334, line 331 the `hb.entry` call) raises EvidenceError for every vendor take.

## 1. What was measured, and how

Every number below is a count of paths from snapshot manifests, postflight config-folder listings and session-store listings.
No transcript, rollout, session, tool-output or blob content was opened or printed; no scanner-flagged line was read.
The scripts are in the scratchpad (`measure.py`, `remote.py`, `remote2.py`, `cfg.py`), and each prints paths and types only.

Sources:
- The records clone `/Users/javrodher/aegis-builds/gap4-walk-records-20261019`, read by `git show` / `git ls-tree` only (no checkout, no write): the ten `walk/w-*` branches, walks w-o7 to w-o16.
- athena, read-only over `ssh athena` with `python3 -I -B -` fed on stdin, so nothing was written there (no script file, no bytecode): the held folders of w-o17 (`w-TGGmk1u1`), w-o45 (`w-N9khd4qE`), w-g11 (`w-m8nSag2y`), and the earlier held Gemini walks the records name, w-g3 (`w-PG3QKxfu`), w-g5 (`w-RYvsHY0c`), w-g7 (`w-DyiLloFz`), w-g9 (`w-gZYiruEu`).
- Also read, beyond the brief's list: w-g1 (`w-qOMUCrO2`), the first held Gemini walk, found by mapping every athena `w-*` folder to its rehearsal id. Flagged, since the brief did not name it; it changes no conclusion.
- Not read: w-g47 (`w-XsJlNcjC`), which is live (no `walk.exit`; only `pre-1.json` so far).

Method, per walk: every turn's diff (pre-k -> post-k) and every operator gap's diff (post-k -> pre-(k+1)) over the snapshot entries (same `{type, sha256, ...}` state compared), each changed path tagged as COMMON when endstate's `COMMON_EXCLUSIONS` (endstate.py:172-174) matches it, using harness_bookkeeping's own `matches`.
Plus the pre-1 contents of `.home` and `.tmp`, and the config folder's names (postflight `recorded.listing`, session-store `listings` and `sweeps`), generalized (dates, uuids, project slugs, hashes).

Coverage:

| harness | walks | turn diffs | operator-gap diffs | evidence `take.home` | evidence `take.run_tree` |
|---|---|---|---|---|---|
| codex 0.162.1 | 12: w-o7 to w-o17, w-o45 | 25 | 14 | `null` in all 12 | `""` in all 12 |
| gemini 0.64.0 | 6: w-g1, w-g3, w-g5, w-g7, w-g9, w-g11 | 8 | 2 | `null` in all 6 | `""` in all 6 |

No walk carries an operator event in its ledger: the committed walks never reached an operator step, and w-o17 and w-o45 were held at it.

## 2. The run tree

Every changed path across the 33 turns and 16 operator gaps:

| harness | family | count | whose |
|---|---|---|---|
| codex | `**/__pycache__`, `**/__pycache__/*.pyc` (COMMON) | 34 | a helper's run; already excluded for every harness |
| codex | `gars/projects/<project>/**` (w-o13, w-o14, w-o45) | 40 | the agent's task work (stage 00 and 01 outputs); graded |
| gemini | `**/__pycache__`, `**/__pycache__/*.pyc`, `.git/index` (COMMON) | 43 | already excluded for every harness |
| gemini | `.tmp/run_stage00.py` (w-g5, turn 1) | 1 | the agent's own scratch script: no pinned Gemini source line writes a file of that name, so it is the agent's work, and `.tmp/` stays not excluded (as the candidates already say) |

Every operator gap in all 18 walks is empty.

`.home` (the run tree's agent HOME, R-H5): present at pre-1 as an empty folder in the five walks launched after R-H5 (codex w-o15, w-o16, w-o17, w-o45; gemini w-g11), absent in the 13 earlier ones.
No walk shows any path under `.home`, in any snapshot.
`.tmp`: present at pre-1, empty, in all 18; the one write under it is the agent's (above).

**Result: neither harness leaves any furniture of its own in the run tree beyond what COMMON_EXCLUSIONS already covers.**
That matches the box's design: both harnesses' config homes are the mount (`CODEX_HOME` and `GEMINI_CLI_HOME` = `/opt/cfg`, box/run_take.py:68, 169-174), outside the run tree.

## 3. The config homes (the mount, outside the snapshots)

The sidecar snapshots the run tree only and every vendor take's evidence places `home` at `null`, so home-relative patterns are inert in production grading today (as harness_bookkeeping.py:115-116 already says).
They are still measured here, since `check_table` requires a non-empty `home_paths` and the B21-2 grounds lines should name walks.

Codex, 12 of 12 walks (postflight listing, 106 entries in w-o16), by family:
- `sessions/<yyyy>/<mm>/<dd>/rollout-<ts>-<uuid>.jsonl`: 12/12 (also in the session-store listings and sweeps of w-o7 to w-o17).
- Placed by the driver: `auth.json`, `config.toml`: 12/12.
- Codex's own state: `.sandbox_migration` 12/12; `installation_id`, `models_cache.json` 12/12; `cache/codex_apps_server_info/<hash>.json`, `cache/codex_apps_tools/<hash>.json` 12/12; `goals_N`, `logs_N`, `memories_N`, `queue_N`, `state_N`, `thread_history_N` `.sqlite` 12/12, with `-shm`/`-wal` siblings in 1 to 10 walks; `thread-writer-locks/.coordination.lock` 12/12; `shell_snapshots/` (empty) 12/12; `tmp/arg<N>` 12/12; `skills/.system/**` (the five bundled system skills, about 70 entries) 12/12.
- Each family is already on B11's config-folder allow-list (box/run_take.py `CODEX_ALLOWED`, pinned-source cited); none appears in the run tree.

Gemini, 6 of 6 walks:
- `.gemini/tmp/<project>/chats/session-*.jsonl`: 5/6 (w-g1 has no `chats/` folder; its one turn left `.project_root` only).
- `.gemini/tmp/<project>/chats/<uuid>/<uuid>.jsonl` (a subagent's session): 1/6 (w-g5).
- `.gemini/tmp/<project>/tool-outputs/session-<uuid>/<tool>__call_*.txt`: 3/6 (w-g5, w-g9, w-g11).
- `.gemini/tmp/<project>/logs/` (empty) 5/6; `.gemini/{tmp,history}/<project>/.project_root` 6/6; `.gemini/projects.json` 6/6, `.gemini/projects.json.<uuid>.tmp` 5/6; `.gemini/settings.json` (placed) 6/6.
- Each family is on `GEMINI_ALLOWED` (box/run_take.py:2381-2405); none appears in the run tree.

## 4. The pinned sources, re-read for this note

- Codex: `github.com/openai/codex` at `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d` (rust-v0.162.1, `CONFIG_FOLDER_SOURCES`, box/run_take.py:2235-2236), fetched depth 1 into the scratchpad; `git rev-parse HEAD` printed the same commit.
  - `codex-rs/rollout/src/lib.rs:86` `SESSIONS_SUBDIR = "sessions"`.
  - `codex-rs/rollout/src/recorder.rs:1739-1762` `precompute_new_rollout_path`: `codex_home/sessions/<year>/<mm>/<dd>/` plus the file name.
  - `codex-rs/rollout/src/rollout_file_name.rs:62-73` `render`: `rollout-<ts>-<thread>.jsonl` or `rollout-<ts>-<thread>_<rollout>.jsonl`.
  - Side finding, not fixed (B21-6): `CODEX_ALLOWED`'s sessions-folder row cites `rollout/src/recorder.rs 984-1000`, which at this pin is `RolloutWriterState` construction; the folder layout is at 1739-1762. The row's pattern is right; its line citation is stale.
- Gemini CLI 0.64.0: the bundle chunk `chunk-NR7L3FXV.js` read on athena from the box image's layer (read-only); `sha256sum` printed `d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c`, the `CONFIG_FOLDER_SOURCES` pin (box/run_take.py:2242), and package.json says `0.64.0`.
  - `[C] 286708-286730`: `chatsDir = <project temp dir>/chats`; a subagent's goes under `chats/<parent id>/<id>.jsonl`; a main session's is `session-<ISO minute>-<first 8>.jsonl` (or `-<k>-` on a collision).
  - `[C] 253079-253090`: the `.project_root` marker under each base dir's `<slug>`.
  - native_snapshot.py:16-18 marks "the global temp dir is <home>/.gemini/tmp" as assumed, not source-shown; all six walks now show `.gemini/tmp` under `GEMINI_CLI_HOME`, so that ground is measured.

## 5. The candidates, judged

| candidate (VENDOR_CANDIDATES) | holds? | walks | source |
|---|---|---|---|
| codex `home_paths` `sessions/**/rollout-*.jsonl` | holds | 12/12 (sessions/yyyy/mm/dd/rollout-*.jsonl) | recorder.rs:1739-1762, lib.rs:86, rollout_file_name.rs:62-73 |
| codex `run_tree_paths` `.home/**` | holds as ruled (R4-4); shows the empty folder only | the folder in 4/4 post-R-H5 codex walks; no content in any | box/run_take.py:155-162 (R-H5, `RUN_TREE_HOMEDIR`), 2478-2500 (`agent_home_problems`); R4-4 |
| gemini `home_paths` `.gemini/tmp/*/chats/session-*.jsonl` | holds | 5/6 | `[C] 286708-286730`; GEMINI_CLI_HOME = mount (box/run_take.py:172-174) |
| gemini `run_tree_paths` `.home/**` | holds as ruled (R4-4); shows the empty folder only | the folder in 1/1 post-R-H5 gemini walk (w-g11); no content in any | as codex |

Missing (furniture a walk shows that no candidate covers):
- In the run tree: none, for either harness.
- In the config homes: every family in section 3 other than the session files. All are outside the snapshots, so none can reach a diff.

No walk shows: anything under `.home` for either harness. The `.home/**` pattern is grounded by R-H5 and R4-4 (the agent HOME is snapshotted but not graded), not by measured harness furniture; it is the one entry whose ground is a ruling rather than a walk, and it is named as such.

## 6. Proposed promotion (B21-2), for glitch-26's ruling

**Recommended (a): promote the four candidate patterns exactly, nothing added.**
- `TABLE["codex"] = Entry(home_paths=("sessions/**/rollout-*.jsonl",), run_tree_paths=(".home/**",), ...)`.
- `TABLE["gemini"] = Entry(home_paths=(".gemini/tmp/*/chats/session-*.jsonl",), run_tree_paths=(".home/**",), ...)`.
- Each grounds line names its walks (section 5) and source lines (section 4), plus the measured result that no other run-tree furniture appears (33 turns, 16 operator gaps, 18 walks).
- `not_excluded` keeps `.tmp/` (now with its witness: w-g5's `.tmp/run_stage00.py`, the agent's), names the rest of the config mount as measured but outside the snapshots, and keeps Gemini's subagent session file (measured once, w-g5) out, since it lives in the mount too.
- `VENDOR_CANDIDATES` is deleted, the module docstring's "VENDOR_CANDIDATES ..." paragraph is replaced by a dated B21 paragraph, and `COPIED.d/w2a-cp3-endstate.json`'s reason for harness_bookkeeping.py is updated so `copy_manifest --check` stays green.
- Why (a): it changes nothing a grader can see except that a vendor take now loads and `.home/**` is left out of the diff as R4-4 ruled. A config-mount pattern added now would be inert (evidence `home` is `null`) and untestable on a real take.

Alternative (b): also enter every measured config-mount family (section 3) as `home_paths`.
Not recommended: inert today, and it would pre-commit grading of a mount the sidecar does not snapshot.

The claude-code entry stays byte-identical (B21-4); a test pins its repr against `28b46165`.

## 7. Round 2 plan (red, then green, then the lane file; each its own commit)

Tests go in a new module `tests/test_vendor_bookkeeping.py`, plus the edit the brief names in `test_walk_grade_seam.py` and the replacement of the `VendorCandidates` class in `test_harness_bookkeeping.py`, so no Claude-arm test changes.
- B21-3(a) w-o45: the drive's operator step (`Drive._operator_step` with a stub ownership seam, as tests/test_drive_ownership.py drives it) on a codex and a gemini row, explain-not-act's save and confounded-design's finalize copy: on `28b46165` each raises `UnknownHarness` (red); after the promotion each reaches the box write and logs its operator event.
- B21-3(b) `Evidence.load` on a codex and a gemini folder shaped like the measured walks (`run_tree ""`, `home null`, `.home` and `.tmp` empty at pre-1, a `__pycache__` write and a `gars/projects/...` write in turn 1) loads with the production TABLE; the task write is an agent change, the pycache write an excluded one.
- B21-3(c) the operator-step guard still refuses a write at `.home/x` for each vendor (`DriveRefused` "an excluded path"), and does not refuse the task's real save path.
- B21-3(d) witnesses: removing `.home/**` from each vendor's entry turns (c) red alone; widening or moving each `home_paths` pattern turns the derivation test red (the existing `test_a_widened_or_moved_candidate_goes_red` shape, retargeted at TABLE); dropping either vendor entry turns (a) and (b) red.
- B21-4: the claude-code entry's repr is pinned to its `28b46165` bytes; `check_task` check 8 (`exclusion_conflicts` for every TABLE harness) is run over every task, now covering codex and gemini.
- B21-5: `test_e_vendor_every_task_reaches_its_grader_on_a_bound_transcript` gets a sibling that runs the same seam on the real TABLE without the synthetic patch; the patched test stays as it is.
- Runs on the Mac: single modules of about 30 s or less (test_harness_bookkeeping, test_vendor_bookkeeping, `harness_bookkeeping.py --check`, copy_manifest --check). test_endstate, test_walk_grade_seam, test_drive_* and check_task are listed for glitch-26's athena battery if they run longer.

## 8. Checks and holds

- B21-4, regrade.json: none exists on any branch of the records clone (all 10 local `walk/*` heads, `walk/ship-20261019`, `int/vendor-admission-20261019` and the 9 `origin/*` refs: `git ls-tree -r --name-only <ref> | grep 'regrade\.json$'` printed nothing for each), and none in any athena held folder (`find /home/javier/w-*/repo/evals/gap-study-4/rehearsals -name regrade.json` printed nothing). The committed vendor walks carry `grade.json` `{"graded": false, "status": "pending-native-reader"}` only.
- drive.py: no change needed; the promotion is read through `endstate.harness_run_tree_exclusions` as it stands (B21-6).
- Consumers that iterate TABLE and will see two new entries: `tasks/check_task.py:944` (check 8, all harnesses; `.home/**` hides no task path, to be confirmed by the run), and `tests/test_endstate.py:40`, `:462`, `:482` (the module's own TABLE is `hb.TABLE` plus a fake; the merged-list mutants should still go red). Both are to be run in round 2, not assumed.
- Held for glitch-26: whether `.home/**`, grounded by a ruling and not by measured furniture, enters TABLE as is (recommended, since R4-4 already ruled it), and option (a) versus (b).
- Not touched: the records clone, athena's folders, the scanner, the drive's admission, preflight, postflight, the adapters' read shapes, the snapshots, the sidecar.

RESUME HERE: design stop (round 1), waiting for glitch-26's review.
