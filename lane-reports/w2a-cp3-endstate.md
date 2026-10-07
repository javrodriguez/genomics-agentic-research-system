status: done

# Lane w2a-cp3-endstate: CP3 end-state reader

Base `164b272c7d662fa570c2f96f66de43e1410cb32f` (`gap4/wave1-merge`). Code commit `a4c565f6` on
`gap4/w2a-cp3-endstate`. I edited no wave 1 file and nothing outside the paths this lane owns.

## What changed (files)

| Path | Status | What |
|---|---|---|
| `evals/gap-study-4/graders/endstate.py` | new | The end-state reader. The evidence folder is defined in its docstring as a closed list of files and fields. `Evidence.load(folder)` and the pure `Evidence.from_parts(...)` give the same reader. |
| `evals/gap-study-4/harness_bookkeeping.py` | new | Interface 8's bookkeeping table, keyed by `AgentAdapter.name`. Its only real entry is `claude-code`. `entry()` refuses an unknown name and has no default. It also has a `--check` CLI. |
| `evals/gap-study-4/tests/test_endstate.py` | new | 34 tests: the plan's fixtures, the seam tests and the layout. |
| `evals/gap-study-4/tests/test_harness_bookkeeping.py` | new | 13 tests: grounding, refusal, segment matching and the seam. |
| `evals/gap-study-4/COPIED.d/w2a-cp3-endstate.json` | new | This lane's fragment. All six files are listed as `new`. |
| `evals/gap-study-4/checks.d/w2a-cp3-endstate.txt` | new | 5 commands. |
| `lane-reports/w2a-cp3-endstate.md` | new | This report. |

### What the reader exposes
- **Agent changes:**
  - `agent_changes(k)`: the diff pre-k → post-k. The turn ends at quiescence.
  - `agent_changes_by_stretch(p)`: each turn's own diff, grouped into `pre` (turns < p) and `post` (turns ≥ p). It is never one diff across a stretch.
  - `excluded_changes(k)`: the bookkeeping changes that `agent_changes(k)` leaves out. They are shown, not hidden.
- **Operator changes:**
  - `operator_changes(k)`: the diff post-k → pre-(k+1).
  - `operator_matches(k)`: matches that diff against the step's logged events.
  - `operator_check()`: returns `{"unexplained_diffs", "problems"}`. `box_records()` hands this count, under `agent_adapter.BOX_KEYS`' names, to `harness_records`, and from there to `routing.py`.
- **Accesses:**
  - `accesses(path=, turn=)` gives each access with `where` (setup / turn k / operator step k / after) and `late` (inside turn k but after its `ended_at`, i.e. the background stretch).
  - `accesses_by_stretch(p)` groups them by stretch.
- **End state:**
  - `end_state()`, `state(label, path)` and `unreadable(label)`.
  - `content(label, path)` returns the bytes of copied consequential files (blobs named by their own sha256).
- **Health and checks:**
  - `sidecar_record()` returns routing's `sidecar` shape.
  - `exclusion_conflicts(task_paths, harness)` lists task paths that an exclusion would hide.

## Tests and checks run (all on this head, from the repository root, `PYTHONDONTWRITEBYTECODE=1`)

Start block on the untouched base: it printed `hooks: only *.sample files; core.hooksPath unset`, `commit`,
`commit`, and the checkout succeeded.

```
test_round4: 436 run, 0 skipped, 0 expected failures
ok: 64 files from 2 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch): 44 identical and 4 edited (round 3 at e2979b31, shared files at 68ec902f), 16 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
```

On this lane's head:
```
$ python3 -W ignore evals/gap-study-4/tests/test_endstate.py            -> Ran 34 tests ... OK
$ python3 -W ignore evals/gap-study-4/tests/test_harness_bookkeeping.py -> Ran 13 tests ... OK
$ python3 evals/gap-study-4/harness_bookkeeping.py --check              -> harness_bookkeeping: ok: 1 harness(es): claude-code
$ python3 -W ignore evals/gap-study-4/test_round4.py                    -> test_round4: 483 run, 0 skipped, 0 expected failures
$ python3 evals/gap-study-4/copy_manifest.py --check                    -> ok: 70 files from 3 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch, w2a-cp3-endstate): 44 identical and 4 edited (round 3 at e2979b31, shared files at 68ec902f), 22 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf
$ python3 evals/gap-study-4/run_checks.py                               -> run_checks: 15 of 15 commands passed
```

How each Done item maps to a test, and the mutant that goes red against it:

| Done item | Test | Mutant |
|---|---|---|
| An operator write between turns is never the agent's | `test_operator_write_between_turns_is_never_the_agents` | the turn diff starts at post-(k-1), across the operator step |
| A pre-probe stage output is never the probe's answer | `test_pre_probe_stage_output_is_never_the_probes_answer` | the post stretch is read as one diff, pre-1 → post-N |
| An unexplained diff routes as `harness-error` (through `harness_records` and `routing.route`, with a test-only pin profile injected in memory as `test_routing.py` does) | `test_unexplained_diff_routes_harness_error`. The same diff is `rehearsal` before the first turn, and the clean take is `graded`. | `operator_matches` drops its unexplained list, and the take routes `graded` |
| A symbolic link is recorded as a link and never followed | `test_symlink_is_recorded_as_a_link_and_never_followed`, `test_a_snapshot_that_followed_a_link_is_refused` | `follow_state` resolves the link |
| A background writer's late write belongs to the turn that launched it | `test_background_late_write_is_the_launching_turns` | a turn ends at the reply, not at quiescence. A process still alive past post-k is refused. |
| Seam: the same task under both harnesses | `test_the_same_task_reads_as_expected_under_both_harnesses` asserts the typed `EXPECTED` (agent changes, operator matches, access stretches, check count) under `claude-code` and `fake-second` | the harness exclusions are removed |
| Under `fake-second`, a write into Claude Code's folder is the agent's | `test_under_fake_second_a_write_into_claude_codes_folder_is_the_agents` | (the merged-list mutant below) |
| Mutant: one merged exclusion list | `test_mutant_one_merged_exclusion_list_goes_red` (endstate), `Seam.test_mutant_one_merged_list_goes_red` (bookkeeping) | red |
| Mutant: a missing `agent` defaults to `claude-code` | `test_a_missing_agent_is_refused_never_defaulted`, `test_mutant_missing_agent_defaulting_goes_red`, `Refusal.test_refusal_check_can_fail` | red |
| Mutant: `endstate.py` types `claude-code` | `test_endstate_types_no_harness` and `test_mutant_endstate_typing_claude_code_goes_red` scan the source for `claude` in any case, every table name and every home folder; a checks.d grep does the same | red |
| Turn k is the k-th turn record, never its `n` | `test_turn_k_is_the_kth_turn_record_never_its_n` | `ordinal_turns` sorts by `n` |

## Failed or skipped
- Nothing failed or was skipped.
- I did not run GARS's whole suite (`tests/run_tests.py`), because the cloud lane contract says it is red here for environment reasons. The home session runs it on athena.

## Decisions (this lane's own)
1. **The evidence layout, field by field** (docstring of `endstate.py`):
   - The files are `ledger.jsonl`, `snapshots/{pre,post}-<k>.json`, `access.jsonl`, `health.jsonl` and an optional `blobs/<sha256>`. Any other file, unknown field or unknown record kind is refused, and so is a symbolic link anywhere in the folder.
   - The take record carries `run_tree` (where the run tree sits in the snapshots) and `home` (where the take user's home sits, or null). The two must be disjoint.
   - Operator and background records belong to the turn record before them, by ledger position. Neither carries a turn number.
   - CP2 must write exactly this layout or amend it here.
2. **Harness exclusions are relative to the take user's home, never the run tree.** Git's and the helpers' exclusions are relative to the run tree. With that anchoring, a merged list is observable: under `fake-second`, `.claude/...` in the home is the agent's change.
3. **The `claude-code` entry excludes only `.claude/projects/*/*.jsonl`** (drive.py:241-242; drive.py:170's environment sets no `CLAUDE_CONFIG_DIR`). These are not excluded, and each is recorded in the entry's `not_excluded`:
   - the auto-memory folder (it is disabled);
   - `.tmp/`, the tools' scratch, which includes the agent's own (a placeholder data file written there is a created file);
   - `data/staging/` (it is only git-excluded; it is the driver's staging);
   - round 3's `excluded_from_the_run_tree` paths (they are absent from the run tree, so anything that appears there was written in the take).
4. **Common exclusions:**
   - `GIT_BOOKKEEPING = (".git/index", ".git/index.lock")`: the stat cache that `git status` refreshes, and its lock. A commit (objects, refs, logs, `COMMIT_EDITMSG`) is not excluded.
   - `HELPER_BOOKKEEPING = ("**/__pycache__/**",)`: Python's bytecode caches. The repository's `.gitignore` names `__pycache__/`.
   - These are not grounded in round 3's files (the brief asked for that only for the `claude-code` entry). See the open questions.
5. **Exclusions apply to every snapshot diff**, the operator steps included, but never to the access log, which only watches consequential paths.
6. **The operator re-check counts three things:**
   - a changed path that no event explains;
   - a modify or delete the watcher logged in an operator step on a path no event of that step names;
   - an event whose write is not in the diff.

   Each counts one in `unexplained_diffs`. The last two are stricter than "every diff is explained".
7. **Time windows:**
   - turn k is (pre-k, post-k];
   - the operator step after k is (post-k, pre-(k+1)];
   - anything at or before pre-1 is `setup`, and anything after post-N is `after`.
   - A background process must be stopped by post-k, or the evidence is refused.
   - An operator record before the first turn or after the last turn is refused.
8. **`sidecar_record()` never invents an exit code.** With no stop record, `exit_code` is None and `stop_record` is False. See the open questions for how `routing.py` treats that.
9. **The reader takes the probe's turn as a parameter.** Graders know their task, and a probe past the last turn leaves `post` empty.
10. **`labels4` is imported but no label is named.** The reader only describes evidence. Its own words (`pre`, `post`, `setup`, `after`, `turn`, `operator`, the change kinds) are not graded labels or routes.

## Open questions for the home session (for CP2 unless marked)
1. **More of Claude Code's own writes in its home.** Round 3's files do not ground `~/.claude.json`, `~/.claude/todos/`, `shell-snapshots/`, `statsig/` or similar, so none is excluded. If the box's snapshots cover the home, those show up as agent changes. CP2 should measure them on a stub take and amend the entry with grounds, or keep `home` null.
2. **Claude Code's temp files inside `.tmp/`.** With TMPDIR set inside the run tree, Claude Code's Bash tool may leave its own temp files under `.tmp/`. They are not excluded, so they read as agent changes. CP2 should measure this; a harness entry for the run tree would need a new field and a decision.
3. **`CLAUDE_CONFIG_DIR` in the inherited environment.** drive.py:170 does not set it, but I did not check whether round 3's `stripped_env` (prereg `driver_constants`) drops an inherited one. Under the reading rule I read only the named lines and the one key. CP2's box should pin it.
4. **A missing stop record and routing.** `routing.py` types `sidecar.exit_code` as an int, so when there is no stop record, this reader's None makes routing refuse the records (blocked for a human) instead of routing `harness-error`. Wave 1's files are untouched. I checked this by routing a no-stop evidence through `tests/test_endstate.route_with`, which printed `refused: sidecar.exit_code must be an int, got None`. Decide in CP2 whether the drive step maps "no stop record" to a sentinel or keeps the refusal.
5. **The common exclusions** (`.git/index`, `.git/index.lock`, `**/__pycache__/**`) are lane decisions, not grounded in round 3's records. Do they need the owner's pre-registration word?
6. **Mode bits are not recorded.** A chmod alone, such as making a file unreadable, is invisible in a STATE: the sidecar reads anyway, and the sha does not change. Should STATE carry `mode`?

## Lessons worth keeping
- An exclusion list relative to a header-supplied root makes the "one merged list" mutant invisible: every harness's patterns re-anchor to the current harness's home. Anchoring each entry's paths at a folder named in the entry itself (here `.claude/` and `.fake2/` under the shared home) is what lets the seam test see a merge.
- A defaulting mutant is only observable if exactly one function decides the field. The take record's `agent` is therefore checked only in `agent_of`, and the generic closed-field check skips it.
