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

(The lane's own runs, on `a4c565f6`. Fold 1's runs are in its section at the end.)

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
2. **Harness exclusions are relative to the take user's home, never the run tree.** Git's and the helpers' exclusions are relative to the run tree. With that anchoring, a merged list is observable: under `fake-second`, `.claude/...` in the home is the agent's change. (Fold 1 adds a second, run-tree-relative list per harness, `run_tree_paths`, empty for `claude-code`: W2A1-6.)
3. **The `claude-code` entry excludes only `.claude/projects/*/*.jsonl`** (drive.py:241-242; drive.py:170's environment sets no `CLAUDE_CONFIG_DIR`). These are not excluded, and each is recorded in the entry's `not_excluded`:
   - the auto-memory folder (it is disabled);
   - `.tmp/`, the tools' scratch, which includes the agent's own (a placeholder data file written there is a created file);
   - `data/staging/` (it is only git-excluded; it is the driver's staging);
   - round 3's `excluded_from_the_run_tree` paths (they are absent from the run tree, so anything that appears there was written in the take).
4. **Common exclusions:**
   - `GIT_BOOKKEEPING = (".git/index", ".git/index.lock")`: the stat cache that `git status` refreshes, and its lock. A commit (objects, refs, logs, `COMMIT_EDITMSG`) is not excluded.
   - `HELPER_BOOKKEEPING = ("**/__pycache__/**",)`: Python's bytecode caches. The repository's `.gitignore` names `__pycache__/`. (Fold 1 narrowed it to `**/__pycache__` and `**/__pycache__/*.pyc`: W2A1-2.)
   - These are not grounded in round 3's files (the brief asked for that only for the `claude-code` entry). See the open questions.
5. **Exclusions apply to every snapshot diff**, the operator steps included, but never to the access log, which only watches consequential paths.
6. **The operator re-check counts three things:**
   - a changed path that no event explains;
   - a modify or delete the watcher logged in an operator step on a path no event of that step names;
   - an event whose write is not in the diff.

   Each counts one in `unexplained_diffs`. The last two are stricter than "every diff is explained". (Fold 1 adds a fourth: a modify or delete logged after post-N, W2A1-4.)
7. **Time windows:**
   - turn k is (pre-k, post-k];
   - the operator step after k is (post-k, pre-(k+1)];
   - anything at or before pre-1 is `setup`, and anything after post-N is `after`.
   - A background process must be stopped by post-k, or the evidence is refused.
   - An operator record before the first turn or after the last turn is refused.
8. **`sidecar_record()` never invents an exit code.** With no stop record, `exit_code` is None and `stop_record` is False. See the open questions for how `routing.py` treats that. (Fold 1 reads the flags in time order, W2A1-1, and pins the refusal in a test, W2A1-5.)
9. **The reader takes the probe's turn as a parameter.** Graders know their task, and a probe past the last turn leaves `post` empty.
10. **`labels4` is imported but no label is named.** The reader only describes evidence. Its own words (`pre`, `post`, `setup`, `after`, `turn`, `operator`, the change kinds) are not graded labels or routes.

## Open questions for the home session (for CP2 unless marked)
1. **More of Claude Code's own writes in its home.** Round 3's files do not ground `~/.claude.json`, `~/.claude/todos/`, `shell-snapshots/`, `statsig/` or similar, so none is excluded. If the box's snapshots cover the home, those show up as agent changes. CP2 should measure them on a stub take and amend the entry with grounds, or keep `home` null.
2. **Claude Code's temp files inside `.tmp/`.** With TMPDIR set inside the run tree, Claude Code's Bash tool may leave its own temp files under `.tmp/`. They are not excluded, so they read as agent changes. CP2 should measure this; a harness entry for the run tree would need a new field and a decision. (Fold 1 added the field, `run_tree_paths`, empty for `claude-code` until CP2 grounds one: W2A1-6.)
3. **`CLAUDE_CONFIG_DIR` in the inherited environment.** drive.py:170 does not set it, but I did not check whether round 3's `stripped_env` (prereg `driver_constants`) drops an inherited one. Under the reading rule I read only the named lines and the one key. CP2's box should pin it. (Fold 1 reworded the docstring and the grounds to say exactly this: W2A1-7.)
4. **A missing stop record and routing.** `routing.py` types `sidecar.exit_code` as an int, so when there is no stop record, this reader's None makes routing refuse the records (blocked for a human) instead of routing `harness-error`. Wave 1's files are untouched. I checked this by routing a no-stop evidence through `tests/test_endstate.route_with`, which printed `refused: sidecar.exit_code must be an int, got None`. Decide in CP2 whether the drive step maps "no stop record" to a sentinel or keeps the refusal. (Fold 1 pins the refusal in `test_sidecar_health_feeds_routing`, so CP2's change flips a visible test: W2A1-5.)
5. **The common exclusions** (`.git/index`, `.git/index.lock`, `**/__pycache__/**`; since fold 1 `**/__pycache__` and `**/__pycache__/*.pyc`) are lane decisions, not grounded in round 3's records. Do they need the owner's pre-registration word?
6. **Mode bits are not recorded.** A chmod alone, such as making a file unreadable, is invisible in a STATE: the sidecar reads anyway, and the sha does not change. Should STATE carry `mode`?

## Lessons worth keeping
- An exclusion list relative to a header-supplied root makes the "one merged list" mutant invisible: every harness's patterns re-anchor to the current harness's home. Anchoring each entry's paths at a folder named in the entry itself (here `.claude/` and `.fake2/` under the shared home) is what lets the seam test see a merge.
- A defaulting mutant is only observable if exactly one function decides the field. The take record's `agent` is therefore checked only in `agent_of`, and the generic closed-field check skips it.

## Session files

Not recorded. The pinned session-files block (run once, as one command, exactly as written, after the report commit
`f52ab83d`) was refused before it ran by the Claude Code auto-mode classifier, which gave the reason
"[Sensitive-Source Provenance]". Per the brief and the hard rules, it was not reworded or retried in any form.
No `gap4/w2a-cp3-endstate-session` branch was created. The home session should record "blindness unverified".

## Fold 1: review round 1

Review round 1 (a fresh `claude-opus-5-5`, on `0a46291a`) returned CHANGES: one MAJOR, three MINORs and five NITs.
The gap4 lane lead's local build agent folded all of them on the Mac, in the worktree `gap4-w2a-fold` on branch
`gap4/w2a-cp3-endstate-fold`, red first:
- `dc9e7c0e`: red tests only. The guards below are red on the unchanged reader and table.
- `f2ca208e`: the fixes.
- The commit that adds this section: the copy-record reasons and this report.

Nothing outside the lane's seven paths changed (`git diff 0a46291a --stat`). Nothing was pushed or merged.

### Per finding: reproduced, fixed, tested, mutated

The reviewer's probes were copied to new names in the session scratchpad and repointed at the fold worktree.
The originals were not edited. After the fix, the copies wrap the access reads that now refuse, so a refusal prints
instead of stopping the probe.

**W2A1-1 (MAJOR): watcher health was read by counts only.**
- Reproduced: probe 1 (P2 to P5) gave `{start_record: True, stop_record: True, exit_code: 0, queue_overflow: False}`
  and `graded` for a late start, a hole over turn 2, a stop before its start, and an early stop. P6 accepted a
  turn-1 access stamped before the watcher's start. Probe 4 (the scope-read-shaped take, the watcher down from 150
  to 206.5 over probe turn 2, which runs from 200 to 206) routed `graded`, with no planted access in `post`.
- Fixed in `graders/endstate.py`:
  - Health records out of time order are refused.
  - `_walk_health` walks the start and stop records in order. A start and the stop right after it bound one closed
    interval. A stop with no start open before it means a start record is missing. A start while one runs, or a
    last start with no stop, means a stop record is missing.
  - `uncovered_turns()`: each turn's window, pre-k to post-k, must lie inside one closed interval.
  - `unwatched_accesses()`: every access must lie inside an interval the records show running.
  - `sidecar_record()`: `start_record` is False for a missing start and `stop_record` False for a missing stop.
    Both are False for an uncovered turn or an unwatched access, so such a take routes `harness-error` after the
    first turn and `rehearsal` before it. `exit_code` is unchanged and never invented.
  - `accesses()` and `accesses_by_stretch()` refuse unless `sidecar_record()` is clean. `operator_matches` and the
    new after-check read the log through `_located()`, so `box_records()` still reaches routing on an unhealthy take.
  - The docstring's new section, THE WATCHER'S HEALTH, says how a snapshot pause is recorded: a `watcher-stop`
    (exit 0) and then a `watcher-start`, both stamped with that snapshot's own `taken_at`. (Fold 2, W2A2-1, replaced
    this rule: each record is stamped when it happens, and a turn's window runs from its `started_at`.)
- Re-run of the fold copies: P2 to P5 now read `{False, False, 0, False}` and route `harness-error`. The access reads
  in P2, P5 and P6 are refused, and each refusal names the uncovered turns and the unwatched accesses. Probe 4 now
  reads `{False, False, 0, False}` and routes `harness-error`, and its probe-stretch read is refused.
- Tests (`WatcherHealth`):
  - `test_a_turn_the_watcher_did_not_cover_is_a_watcher_gap`: late start, a hole over the probe turn, early stop,
    stop before start, and a stop and restart inside a turn. Each reads as a gap in both flags, names its uncovered
    turns, and routes `harness-error` after the first turn and `rehearsal` before it.
  - `test_records_out_of_alternation_flag_the_missing_record`: with every turn covered, a second stop clears
    `start_record`, and a second start clears `stop_record`.
  - `test_an_access_outside_every_watcher_interval_is_a_gap`: an access at 20, before the start, or at 309, after the
    stop, routes `harness-error`, and the access read is refused.
  - `test_an_unwatched_probe_turn_never_reads_as_no_access` (probe 4's take): `harness-error`, and
    `accesses(turn=2)`, `accesses_by_stretch(2)`, `accesses(path=planted)` and `accesses(turn=1)` are all refused.
  - `test_health_records_out_of_time_order_are_refused`.
  - `test_a_snapshot_pause_stamped_at_the_snapshots_instant_is_healthy`: the documented pause reads clean and
    `graded`, and a restart stamped half a second late leaves turn 2 uncovered. (Fold 2, W2A2-1, replaced it with
    `test_a_snapshot_pause_stamped_when_it_happens_is_healthy`: that half-second re-arm, before turn 2 starts, is
    now clean.)
- Mutants, each red against the guard tests above:
  - count-only health (the round 1 code): each of the reviewer's four cases goes red alone, and probe 4's take
    routes `graded`;
  - turn windows unread;
  - alternation unread;
  - unwatched accesses unread;
  - access reads without the health check;
  - time order unread.

**W2A1-2 (MINOR): `**/__pycache__/**` hid any file under such a folder.**
- Reproduced: probe 2 (P8). `__pycache__/samples_placeholder.csv` gave `agent_changes(1) == {}`.
- Fixed: `HELPER_BOOKKEEPING = ("**/__pycache__", "**/__pycache__/*.pyc")`.
- Re-run: P8's file is now the agent's change.
- Test: `Exclusions.test_only_bytecode_under_a_pycache_folder_is_excluded`. A `.csv`, and a `.pyc` one folder deeper,
  are the agent's changes, while the folder entry and its `.pyc` are excluded. `exclusion_conflicts` reports no conflict.
- Mutant: the broad pattern, red.

**W2A1-3 (MINOR): two unreadable states compared equal.**
- Reproduced: probe 2 (P7). `agent_changes(2) == {}` and the route was `graded`.
- Fixed: `same_state()` treats an unreadable state as never the same as any state, itself included. Such a path is
  an `unknown` change (fold 1's choice; see the decisions below), and no event explains an unreadable end.
- Re-run: P7 now shows `plan.md` as a change in turn 2, and `box_records` carries `unexplained_operator_diffs: 1`.
- Test: `UnreadablePaths.test_an_unreadable_path_is_never_read_as_unchanged`.
  - Unknown in each turn and in `post`.
  - Unexplained across the operator step, so the take routes `harness-error`.
  - A file that became unreadable is `unknown`.
  - An operator write of known content still explains an unreadable path.
- Mutants: equality comparison, red; `kind_of` without `unknown`, red.

**W2A1-4 (MINOR): a write logged after post-N was accepted silently.**
- Reproduced: probe 2 (P9). A `modify` at 350, after post-3 at 306, left `operator_check` at 0, and the route was `graded`.
- Fixed: `writes_after_the_end()` lists every modify or delete logged after post-N, and `operator_check()` counts
  each one, so the take routes `harness-error`.
- Re-run: P9 now gives `unexplained_diffs: 1` and `harness-error`. P9 also logs a setup write at 10, before the
  watcher's start at 50, so W2A1-1 now flags it as an unwatched access.
- Test: `PlanFixtures.test_a_write_logged_after_the_end_state_is_counted`. A modify or a delete at 307 counts one and
  routes `harness-error`; an open at 307 counts none.
- Mutant: the after stretch unread, red.

**W2A1-5 (NIT): pin the no-stop refusal.**
- Reproduced: probe 1 (P1). It printed `REFUSED: sidecar.exit_code must be an int, got None` before and after the
  first turn, and for empty health.
- Fixed: the code is unchanged; this pins the refusal. In `test_sidecar_health_feeds_routing`,
  `assertRaisesRegex(routing.RoutingRefused, "exit_code must be an int")` covers no stop and empty health. The
  mapping is left to CP2.
- Mutant: `test_mutant_an_invented_exit_code_goes_red`. A missing stop read as exit 0 routes instead of refusing, red.

**W2A1-6 (NIT): run-tree bookkeeping per harness.**
- Fixed: `Entry.run_tree_paths` is required, with no default. It is `()` for `claude-code` until CP2 grounds one.
  - `harness_bookkeeping.run_tree_excluded()` reads it.
  - `endstate.is_excluded` reads the take's harness's list under the run tree, through `harness_run_tree_exclusions`.
  - `exclusion_conflicts` checks the common list plus that harness's own list.
  - `check_table` validates the field.
- Tests:
  - `Seam.test_under_claude_code_a_write_into_fake_seconds_run_tree_folder_is_the_agents`: under `claude-code`, a
    write into fake-second's `.fake2-run/` is the agent's change; under fake-second it is excluded. Conflicts are
    checked per harness.
  - The both-harness seam test now carries fake-second's run-tree cache.
  - `TB.Seam.test_each_harness_excludes_its_own_paths_only` gains the run-tree checks.
  - `test_grounded_in_round3_files` requires `claude-code`'s list to be empty.
  - `test_check_table_can_fail` gains three run-tree cases.
- Mutants, red:
  - the merged run-tree list, both in `endstate` and in the table (`TB.Seam.test_mutant_one_merged_list_goes_red`
    extended);
  - the run-tree list unread;
  - `exclusion_conflicts` ignoring the harness;
  - `claude-code` given `.tmp/**`;
  - `check_table` skipping the field.

**W2A1-7 (NIT): "holds" reworded.**
- Fixed: the docstring and the grounds now say that drive.py:170 sets no `CLAUDE_CONFIG_DIR`, and "whether an
  inherited one passes through is open (CP2)".
- Test: `TheTable.test_an_inherited_config_dir_is_left_open`.
- Mutant: the round 1 wording, red.

**W2A1-8 (NIT): staging-only changes are hidden.**
- Fixed: `GIT_BOOKKEEPING`'s docstring entry says that excluding the index also hides staging-only changes
  (`git rm --cached`, `git reset <path>`, `git add` of a blob the repository already holds).
- Test: `Exclusions.test_a_staging_only_change_is_hidden_as_documented` pins the behaviour (P10) and the sentence.
- Mutant: the docstring without it, red.

**W2A1-9: no code change.** The session-files step was refused by the classifier, and the lane did not retry it.
Blindness stays unverified for this lane, and the home session records it so.

### Decisions (fold 1's own, the local build agent's; none is Javier's or glitch-f3's)
1. **An uncovered turn or an unwatched access clears both flags.** Before the first turn, routing reads only
   `start_record` (wave 1's row), so a gap has to reach that flag to rehearse there. An uncovered turn also has no
   covering start and stop pair.
2. **An alternation fault with every turn covered clears only the missing record's flag.** A stop-side fault alone
   (a second start, for example) is ignored before the first turn, as wave 1's row intends; the take routes by its
   own reason. (Reworded in fold 2, W2A2-5. Wave 1's before-first-turn watcher row reads no stop record: "before
   the first turn it may legitimately not exist yet". A real take that ends there has its own reason row, such as a
   container that never started, and rehearses by it. Only a constructed take with no reason is refused, exactly as
   a clean one is: "no row matches these records (phase before-first-turn)". `MISPAIRED` pins that refusal and fold
   2's `test_before_the_first_turn_the_take_routes_by_its_own_reason` pins the rehearsal, so a CP2 change shows up.)
3. **Health out of time order is refused, not routed.** Like snapshots out of order, it is malformed evidence, not a gap.
4. **An unwatched access is a gap, not a refusal at construction.** It routes `harness-error`, and the access
   reads refuse it, but construction does not, so the drive step can still route the take.
   - For this check only, a start no stop closed counts as running (until the next start, or for ever after the
     last). It never covers a turn.
5. **Access reads refuse on any record that is not clean.** That means a gap anywhere, a non-zero or missing exit, or
   a queue overflow, not only the uncovered turn asked about. This is stricter than the finding. Such a take routes
   away from `graded`, so nothing grades from it.
6. **W2A1-3: the `unknown` change kind, not a refusal of the stretch.**
   - Any pair present at both ends with an unreadable side is `unknown`. A file that became unreadable used to read
     `retyped`, but an unreadable file is not a new type.
   - An `unknown` change is explained only by an operator write whose `after` is a known state the step's end
     shows. So an unreadable path that persists across an operator step routes `harness-error`.
7. **W2A1-4: count, do not refuse.** It is one count per logged modify or delete after post-N. Reads after post-N
   do not count. Neither do writes in setup, because pre-1 holds them.
8. **W2A1-2: the reviewer's patterns, exactly.** One residual remains: `**/__pycache__` would also hide a file that is
   itself named `__pycache__`, because patterns carry no type.
9. **W2A1-6: `home_paths` stays required and non-empty.** `run_tree_paths` is required and may be empty.

### Open questions from fold 1 (for CP2 unless marked)
1. **A stop-side health fault alone before the first turn** is ignored before the first turn, as wave 1's row
   intends; the take routes by its own reason (decision 2). (Reworded in fold 2, W2A2-5. Left for CP2 only if it
   adds the stop record to that row, which flips `MISPAIRED`'s pin.)
2. **The pause stamp is binding.** CP2's sidecar must stamp each snapshot pause exactly as the docstring says. If it
   restarts the watcher after the snapshot's instant, every take reads uncovered and routes `harness-error`.
   (Superseded in fold 2, W2A2-1: every health record is now stamped when it happens, and the re-arm must come
   before the turn starts. See Fold 2.)
3. **Persistently unreadable paths** (for example special files the sidecar records as unreadable) now route every
   multi-turn take `harness-error` through the operator re-check (decision 6). CP2 should measure this on a stub take.
4. **An operator event on an excluded path** (probe 2's P11, unchanged): an event that writes `.git/index` reads as a
   write the step does not show, so it counts one and routes `harness-error`. CP2's driver should not log index
   writes as operator events, or the reader needs a rule for them.
5. **W2A1-4's count sees only what the watcher logs after post-N.** If the sidecar stops the watcher at post-N (the
   natural end under the pause stamp), an unstopped writer after post-N is never logged, and the count stays 0.
   CP2 decides how long the watcher keeps running after post-N, and whether the reader should require a stop
   strictly after it.

### Tests and checks run (fold 1, on the Mac, `PYTHONDONTWRITEBYTECODE=1`, `mac_slot.py light-ok` before each batch)
```
$ python3 -W ignore evals/gap-study-4/tests/test_endstate.py            -> Ran 56 tests ... OK
$ python3 -W ignore evals/gap-study-4/tests/test_harness_bookkeeping.py -> Ran 14 tests ... OK
$ python3 evals/gap-study-4/harness_bookkeeping.py --check              -> harness_bookkeeping: ok: 1 harness(es): claude-code
```
The battery and the checks ran under `mac_slot.py acquire --kind heavy --owner gap4-w2a-fold --minutes 20 --wait
1800`, granted at 01:09 EDT once the launch-pad booking ended, and released at 01:16. They ran on the code commit
`f2ca208e` with this commit's copy-record fragment staged:
```
$ python3 -W ignore evals/gap-study-4/test_round4.py   -> test_round4: 506 run, 0 skipped, 0 expected failures   (436 + 56 + 14)
$ python3 evals/gap-study-4/run_checks.py               -> run_checks: 15 of 15 commands passed
```
`copy_manifest.py --check` passed inside run_checks (w1a's checks file).
- **Red first, on the pre-fold code.** A scratch runner only gave `Entry` the new field, so the modules import, then
  ran both files.
  - Red results (failures plus errors, each subtest counted once): 27 in test_endstate and 12 in
    test_harness_bookkeeping.
  - They cover every new guard test, except the W2A1-5 pin, which pins unchanged behaviour and passes on both sides.
  - The rest are existing tests that read the new field. One more,
    `test_one_real_entry_named_as_the_adapter`, is an artifact of the runner: the real entry is not an instance of
    the shim class.
- **The mutation run.** 17 guard tests pass on the fold's code, and each goes red under its mutant (23 mutant rows).
- **The reviewer's probe 3, re-run.** The real code passes. The same 13 mutant rows are red as in the review, and
  the merged-list row against the same-task guard stays green, as the reviewer expected.

## Fold 2: review round 2

Review round 2 (a fresh `claude-opus-5-5`, on `86c25837`) returned PASS with no MAJOR: two MINORs that loosen a check (W2A2-1, W2A2-2) and four NITs.
The loop is closed, so there is no review round 3.
Under the stop rule the two MINORs are folded as the reviewer wrote them, red first.
On glitch-f3's ruling, NITs are folded only where they are cheap and touch no checked behaviour: W2A2-5 and W2A2-6 as wording, W2A2-3 and W2A2-4 recorded, not folded.
The gap4 lane lead's local build agent folded them on the Mac, in the worktree `gap4-w2a-fold` on branch `gap4/w2a-cp3-endstate-fold`:
- `84537558`: red tests only.
  On the unchanged reader, 4 tests are red (12 failures, counting subtests).
- `cdf58157`: the fixes, in `graders/endstate.py` alone.
- The commit that adds this section: this report.

`git diff 86c25837 --stat` touches `graders/endstate.py`, `tests/test_endstate.py` and this report, nothing else.
Nothing was pushed or merged.

### Per finding: reproduced, fixed, tested, mutated

The reviewer's probes were copied to new names in the session scratchpad (`w2a_f2_probe6a.py`, case A of probe 6, and `w2a_f2_probe7.py`); they already pointed at this worktree.
The originals were not edited.

**W2A2-1 (MINOR): the pause stamp forced a start stamped when the watcher was not running, and hid a late re-arm.**
- Reproduced on `86c25837` with `w2a_f2_probe7.py`.
  Turn 2 runs from 201 to 203; pre-2 is at 200 and post-2 at 206.
  - A truthful re-arm at 200.5, before turn 2 starts, read `uncovered (2,) -> harness-error`: a false gap.
  - A truthful re-arm at 202.5, after turn 2 started, read `uncovered (2,) -> harness-error`.
    Stamped at 200.0, as the old rule told the sidecar, the same take read `uncovered () -> graded`.
- Fixed in `graders/endstate.py`:
  - Every health record is stamped when it happens.
    A snapshot's `taken_at` is the instant it begins (its pause's stop), and the re-arm is stamped when the watcher is re-armed.
  - `uncovered_turns()` requires each turn's window, from its `started_at` to post-k's `taken_at`, to lie inside one recorded interval, so the re-arm must come before the turn starts.
  - The docstring's pause rule (THE WATCHER'S HEALTH), the snapshot's `taken_at` field and the uncovered-turn problem text say the same.
- Re-run: the re-arm at 200.5 now reads `uncovered () -> graded`, and the one at 202.5 still reads `uncovered (2,) -> harness-error`.
  The fold's reader and the reviewer's started_at-window variant agree on all three rows.
- Test: `WatcherHealth.test_a_snapshot_pause_stamped_when_it_happens_is_healthy` replaces fold 1's 200.5 case.
  - A re-arm at 200, 200.5 or 201 (at or before turn 2's `started_at`) is clean and `graded`.
  - A re-arm at 202.5 (after it) is a gap in both flags and routes `harness-error`.
  - Every snapshot re-armed half a second after it begins is clean.
  - The docstring holds both phrases of the new rule.
- Mutants, each red against that test:
  - the window measured from pre-k (the reviewer's; `test_mutant_window_from_pre_k_goes_red`);
  - the window measured from the turn's end, so a late re-arm passes (mine; `test_mutant_window_from_turn_end_goes_red`);
  - the docstring without one phrase or the other (two rows, mutation script only).

**W2A2-2 (MINOR): `accesses(turn=k)` never validated k.**
- Reproduced on `86c25837` with `w2a_f2_probe6a.py`: `accesses(turn=0 | 4 | 99 | "2")` each returned `[]`, while `agent_changes` refused each (`turn 4 is not 1..3`).
- Fixed: `accesses()` calls `self._turn(turn)` when a turn is given, before the health check, and its docstring says so.
- Re-run: each of the four now prints `REFUSED(EvidenceError): turn ... is not 1..3`, as `agent_changes` does.
- Test: `TurnsAndLayout.test_an_access_read_for_a_turn_the_take_does_not_have_is_refused`.
  0, N+1, 99, "2", 2.0, True and -1 are each refused by both reads, and turn 2 still reads its one logged open.
- Mutant: `accesses_without_the_turn_check()` rebuilds `accesses` in memory from its own source with the call replaced by `pass`.
  It refuses to build unless the call is there exactly once, so it can never be the real code by accident.
  Red: `test_mutant_accesses_without_the_turn_check_goes_red` shows the four reads return `[]` again.

**W2A2-5 (NIT): folded as wording, plus the optional test-only pin.**
- Fold 1's decision 2 and its open question 1 are reworded above to "ignored before the first turn, as wave 1's row intends; the take routes by its own reason", each marked as reworded in fold 2.
- Pin: `WatcherHealth.test_before_the_first_turn_the_take_routes_by_its_own_reason`.
  - With `container_started` False, a clean take, a start while the watcher runs, and a stop with no start before it each route `rehearsal`.
  - With no reason at all, the clean take and the stop-side fault are both refused with `no row matches these records (phase before-first-turn)`.
  - It pins unchanged behaviour, so it passes on both sides of the fix.
- Mutant: a missing stop record read as "no exit known" (`exit_code` None), which routing refuses before any reason; red (`test_mutant_a_stop_side_fault_read_as_no_exit_goes_red`).

**W2A2-6 (NIT): folded as wording.**
- `endstate.py`'s docstring (WHO CHANGED WHAT) now says the after-post-N write count rides `operator-diff-unexplained-after-first-turn`, and so carries a second cause, a quiescence-cap failure.
  `operator_check()["problems"]` names the true cause of each count.
- So a take whose only fault is a write after post-N is recorded under that row, and the published `harness-error` column names an operator diff for it.
  This lane feeds only the two box keys it owns; a key of its own is for CP2 (open question 3 below).
- Test (mine, binding the sentence to the data): `PlanFixtures.test_a_write_after_the_end_rides_the_operator_diff_row_and_names_its_own_cause`.
  For a take whose only fault is a modify at 307 (post-3 is at 306), routing's winning rows are exactly `["operator-diff-unexplained-after-first-turn"]`.
  Its one problem starts `after the last turn:` and names the quiescence cap, and the docstring holds the sentence.
- Mutants, each red: the problem renamed as an operator-step diff (`test_mutant_an_after_write_named_as_an_operator_diff_goes_red`, and the script), and the docstring without the sentence (script).

**W2A2-3 and W2A2-4 (NITs): recorded, not folded (stop rule; glitch-f3).**
Both would change checked behaviour, so they are recorded here for CP2 and CP4.
- W2A2-3: the closed STATE has no type for a socket, FIFO or device, so the sidecar can only record one as `unreadable`.
  - A special file present in a 1-turn take reads as a phantom `unknown` agent change, and the take routes `graded`.
  - One the agent makes in turn 1 of 3 reads created, unknown, unknown, and the operator re-check counts 2, so the take routes `harness-error` and is re-run.
    The plan says no try is ever re-run for something the agent did; this fails closed for multi-turn takes.
  - The reviewer's fix: a `{"type": "special", "kind": "socket" | "fifo" | "char" | "block"}` STATE compared by equality, so a lasting special file reads as no change.
    For CP2, with fold 1's open question 3.
- W2A2-4: `harness_bookkeeping.pattern_problems` refuses only the literal `**`.
  `**/*`, `*/**` and `*` pass, and in `run_tree_paths` such a pattern would hide every agent change in the run tree.
  The reviewer's fix: refuse any pattern whose first segment holds a wildcard, in both lists (every current entry passes: `.claude`, `.fake2`, `.fake2-run`), with those three cases added to `test_check_table_can_fail`.
  Until then, the only backstop is CP4 running `exclusion_conflicts` per task under every harness.

### Decisions (fold 2's own, the local build agent's; none is Javier's or glitch-f3's)
1. **The turn check in `accesses()` runs before the health check.**
   A bad turn is named as a bad turn even on an unhealthy take; both refusals are `EvidenceError`.
2. **W2A2-2's refused set adds 2.0, True and -1** to the reviewer's 0, N+1, 99 and "2".
   2.0 and True matter because `("turn", 2) == ("turn", 2.0)` and `1 == True` in Python, so the unchanged filter matched them to turns 2 and 1.
3. **The W2A2-2 mutant is built from `accesses`' own source**, with the one call replaced by `pass`, and refuses to build unless the call is there exactly once.
4. **W2A2-1 gets a second mutant**, the window measured from the turn's end, so the late-re-arm half of the test is shown to bind too.
5. **W2A2-5's pin and W2A2-6's test pin unchanged behaviour**, each with a mutant.
   The new docstring phrases are pinned as fold 1 pinned W2A1-7's and W2A1-8's, with docstring mutants in the mutation script.
6. **Fold 1's superseded text is kept and marked, never deleted**: its decision 2, its open questions 1 and 2, and the W2A1-1 pause bullets.
7. **The reader does not require a watcher-stop at each snapshot's `taken_at`.**
   That would be stricter, but it is beyond the finding, and it would refuse every constructed take without pauses (the tests' default health has none).
   Open question 2 below.

### Open questions from fold 2 (for CP2 unless marked)
1. **The reader cannot tell a truthful stamp from a false one.**
   Fold 2 removes the reason a working sidecar had to stamp a start it never made, and a late re-arm stamped truthfully now reads as a gap.
   A sidecar that stamped a re-arm earlier than it happened would still pass.
   CP2's sidecar tests should prove each record is stamped when it happens (a fake clock across a slow snapshot), and that the driver sends the next line only after the re-arm.
2. **Should the reader require a watcher-stop at each snapshot's `taken_at`?** (decision 7)
   If the watcher ran through a snapshot, the snapshot's own opens of the consequential paths would be logged just after `taken_at`, inside the next turn's (pre-k, post-k] window or the operator step after post-k.
   The reader would then read a pre-k snapshot's open of a planted file as the agent's access in turn k.
   CP2 decides whether the sidecar's tests alone guard this, or the reader also checks it.
3. **A box key of its own for the after-post-N write count** (W2A2-6), with its own routing row, so the published `harness-error` column names a quiescence-cap failure as such.
   That changes `agent_adapter.BOX_KEYS` and `routing.json`, wave 1's files, so it is CP2's.
4. **W2A2-3 (a `special` STATE type) for CP2, and W2A2-4 (a first-segment wildcard guard) for CP2 or CP4**, as recorded above.

### Tests and checks run (fold 2, on the Mac, `PYTHONDONTWRITEBYTECODE=1`, `mac_slot.py light-ok` before each batch)
- **Red first, on the unchanged reader.** With the red tests committed (`84537558`) and `graders/endstate.py` still at `86c25837`:
  ```
  $ python3 -W ignore evals/gap-study-4/tests/test_endstate.py            -> Ran 64 tests ... FAILED (failures=12)
  ```
  The red tests are W2A2-1's pause test (3 failures), W2A2-2's refusal test (7, one per refused turn), W2A2-2's mutant (it refuses to build: the call is not there yet) and W2A2-6's test (the docstring sentence).
  The W2A2-5 pin, its mutant and the W2A2-1 mutant demos pass on both sides, as pins of unchanged behaviour and in-memory mutants do.
- **On the fix (`cdf58157`):**
  ```
  $ python3 -W ignore evals/gap-study-4/tests/test_endstate.py            -> Ran 64 tests ... OK
  $ python3 -W ignore evals/gap-study-4/tests/test_harness_bookkeeping.py -> Ran 14 tests ... OK
  $ python3 evals/gap-study-4/harness_bookkeeping.py --check              -> harness_bookkeeping: ok: 1 harness(es): claude-code
  ```
- **The mutation run** (`w2a_fold2_mutants.py` in the session scratchpad, in memory only): the 4 guard tests fold 2 adds or changes pass on the real code, and all 8 mutant rows are red.
  ```
  real code: 4 guard(s) all PASS; mutants: 8 row(s) all RED
  ```
- **The pre-fold reader, loaded from git in memory** (`w2a_fold2_oldreader.py`): `accesses(turn=2.0)` returned turn 2's open and `accesses(turn=True)` turn 1's, so decision 2's two extra cases were live.
- **The battery and the checks** ran on `cdf58157` under `mac_slot.py acquire --kind heavy --owner gap4-w2a-fold --minutes 20 --wait 1800`, granted at 02:05 EDT once the load fell below the second-slot bar, and released at 02:12.
  This report was modified, uncommitted, in the working tree; the battery and the checks do not read it.
  ```
  $ python3 -W ignore evals/gap-study-4/test_round4.py   -> test_round4: 514 run, 0 skipped, 0 expected failures   (506 + 8)
  $ python3 evals/gap-study-4/run_checks.py               -> run_checks: 15 of 15 commands passed
  ```
- `git status --porcelain --ignored` showed only this report after every run, and nothing once it was committed.
