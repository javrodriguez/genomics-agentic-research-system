Status: review round 1 PASS; fold w12b-R1 and athena's four survivors folded (see the end); athena rerun owed on the fold head

RESUME HERE: athena rerun of the module list below on the fold head

# Lane w12b-walk-builders: Gap Study round 4, the walk runner's production builders (fake half)

Written Tue 13 Oct 2026, 05:38 EDT (`date`), by the lane's only writer (Claude Opus 5.5), assigned by glitch-2f (Lane-orchestrator) under Javier's standing delegation.
Branch `gap4/w12b-walk-builders`, base `f4420445` (gap4/wave11-merge, athena battery 218/218 per the assignment).
Worktree `/Users/javrodher/aegis-builds/gap4-w12b`.
Nothing was pushed, merged or spent; no athena run; no model, network, Docker, credential, salt or holdout was used.
No login token value was read: every login file in the tests holds test_box_integration's synthetic value.

## Spec read

- `plans/gap-study-round-4/next-slices-plan-2026-10-12.md` section 1 item 5: DockerRuntime, the login-file reader by name, the counters reader, the D2 identity builder, the run-tree and fixture builders; `walk_runner.main` stops refusing only when every builder exists; the identity builder and CLI plumbing on fakes now, the runtime half after item 4.
- `lane-reports/w7b-walk-wiring.md` Q-w7b-3 and "Not built" (fixture and run-tree builders need stage 01's exits).
- `lane-reports/w10-walk-runner.md` Rulings: D2, `session_id = uuid5(takes.namespace(), "walk/" + id)`, row and row_commit None.
- `evals/gap-study-4/walk_runner.py` at the base: the CLI refused unconditionally (docstring lines 31-33, `CLI_REFUSAL` line 53).

## Commits

| Commit | What |
|---|---|
| `5cf4d11c` | tests first: `tests/test_walk_builders.py` alone |
| `8a86a246` | `walk_builders.py`, `walk_runner.main`'s new body, the cli-runs witness anchor, both fragments, checks.d |
| (this commit) | this report |

## What was built (`evals/gap-study-4/walk_builders.py`, new)

- `walk_identity(walk, *, source, fixture, gars_tree_sha)`: ruling D2.
  The session id is `check_take.walk_session_id` (the one `drive.walk_identity_problems` compares at launch); row and row_commit None; exactly `drive.IDENTITY_KEYS`.
  A relative or unnormalised source, a missing fixture record and a gars tree that is not 40 hex are refused.
  `identity_for(prepared)` hands a copy of the identity prepared for the row's own walk and refuses any other walk.
- `login_file_by_name(path, harness)`: absolute path, regular file (never a link), mode 600, owned by the reader, outside every repository, then exactly `len(LOGIN_VARIABLE[harness]) + 1` bytes read in one `os.read` and compared with `NAME=`.
  The value is never read; it returns the path.
  `login_secrets` reads the value through `scan_record.read_login` only when the scan calls it.
- `counters_reader(cgroup_dir_for)`: the adapter's `counters_for(take)`, `run_take.counters` over the absolute existing folder `cgroup_dir_for(take)` names.
- `build_run_tree(walk, *, repo, commit, exclude)`: `drive.clean_run_tree` of the origin commit at the walk's own neutral name; every refusal or failure is `BuilderRefused` and leaves nothing. `remove_run_tree` says why it could not remove.
- `build_walk_fixture(row, run_tree, project)`: `drive.build_take_fixture` inside the run tree (every kind round 3 builds), then refused by name when nothing was built, when a project fixture records another variant, no stage 01 exit, a non-integer exit, or not the exit its variant is built to reach, or when the template's source does not exist after the build.
  The source handed to the identity is the task's `source_template` rendered for the walk, as test_walk_runner's rig does.
- `walk_row`: the design's first row for the cell (draft order, so its pressure and repeat), `walk` and `slot` the walk id, the pinned agent version; the design's rows untouched.
- `production_builders()` and `missing()`: the closed name set `NAMES` (20 names); see "Refusals still standing".
- `cli(argv, builders=None, *, refusal)`: refuse by name (exit 2) before anything is parsed or built; else parse `--walk --task --half --wording --arm --model --reason`, build the row (a row of another harness refused: drive A1), check the login by name, build the run tree, the fixture and the identity, `drive.walk_driver(records="walks")` over `mode_binding.HERE` with its `WalkRepo`, and run the one walk through `walk_runner.run_walks`; print one JSON line.
  Exit 0 committed, 1 launch-refused or held, 2 a builder's refusal (its run tree removed first).
  A held walk keeps its run tree for a human, as it keeps its folder; anything else the driver's construction raises goes on as itself, its run tree removed first.

`walk_runner.main(argv=None, *, builders=None)` is now `return walk_builders.cli(argv, builders, refusal=CLI_REFUSAL)`.

## Refusals still standing (production, `walk_runner.py` with any argv exits 2 naming each, in this order)

| Name | Why (as printed, abridged) |
|---|---|
| runtime | the DockerRuntime, built at item 4, the real-box bring-up (Q-w7b-3) |
| config_parent | the per-walk config folders' parent, outside every repository (item 4) |
| take_spec | box/image.lock's image and run_take's `TakeSpec.resources` (PENDING) |
| sidecar_for | the sidecar launch, image pinned, `sidecar.expect` bound to `launched.sidecar_id` (cp6-readiness:62) |
| proxy | the egress proxy launch (box/egress, `squid -k parse`) |
| lock_path | box/image.lock, pinned at the bring-up |
| hosts | preflight's hosts mapping |
| uid_map | `run_take.CALLER_PENDING["uid_map"]` |
| cgroup_dir_for | `run_take.CALLER_PENDING["cgroup_dir"]` |
| rules_scanner | `scan_record.RULES_SCANNER` PENDING (gitleaks on athena) |
| login_path | the walk token's login file (hands card Part 3, item 7) |
| agent_version | `version_pins` PENDING in prereg-draft.json |
| pin_for | routing.json `pin_profiles` empty |
| design_for | `check_take.CHECKER_CONSTANTS` paths still PENDING (listed in the message) |
| budgets | the turn budget (`budgets.turn_timeout_s`), the quiescence cap and the poll interval: not yet pre-registered |
| run_tree_exclude | `CHECKER_CONSTANTS.run_location` PENDING |

Present in production: `table` (routing.json), `run_tree_origin` (`drive.REPO`, `variants.PINNED_TREE`), `clock`/`sleep` (`time.time`, `time.sleep`).
`pin_for`, `design_for` and `rules_scanner` become present by themselves once their values are filled where they live (B8); nothing here fills a PENDING value.

## Tests (`tests/test_walk_builders.py`, 40 tests)

B1 identity, B2 login by name, B3 counters, B4 run tree (a real `clean_run_tree` over a scratch origin repository, inside the scratch folder), B5 fixture (a stand-in generator replaces `subprocess.run` for the generator processes only; the guard keeps every other process), B6 row, B7 production refuses by name, B8 a measured value is present, B9 the command line on the fake box, G1 the EQUIVALENT registry, and W6M1 (sys.path restored).

B9's end-to-end walk: `walk_runner.main(argv, builders=<fake box>)` on test_walk_wiring's session box, the REAL Claude Code adapter and check4 on the real design, the REAL v4 grader (the fake sidecar watches the half's planted paths, as w10's R9), committed through WalkRepo: exit 0, one register entry with its reason, the ledger's session id the D2 one and row/row_commit None, the fixture record the generated one at its pin, `check.json` checked/graded/no reasons, `grade.json` graded by `graders/scope_read.py`, the run tree and the config folder removed, nothing under `takes/`, a clean status.
B9 also: one builder absent, Missing or unknown (exit 2, named alone, nothing built); a cell the design lacks and an arm O row (exit 2, nothing built); a login of another name (exit 2, the value printed nowhere); a refused fixture (exit 2, run tree removed); a driver construction that raises (raises as itself, run tree removed); a walk id already registered (launch-refused, exit 1, run tree removed); a held walk via a scan finding (exit 1, run tree kept).

Evidence (Mac, each run behind `mac_slot.py light-ok`, `timeout -s INT 120`, `/usr/local/bin/python3.13 -B -W ignore`):
- Red first, on `5cf4d11c` with `walk_builders.py` removed and `walk_runner.py` at `f4420445`'s bytes (byte backups, restored, `shasum -a 256 -c` OK on both): `test_walk_builders: 40 run, 62 failures, 0 errors, 0 skipped` (failures counted per subTest), 39 distinct tests failing by assertion; the 40th is W6M1, which passes on any module that restores sys.path.
- Green at `8a86a246`: `test_walk_builders: 40 run, 0 failures, 0 errors, 0 skipped` (75 s on a loaded Mac).
- Hand witnesses: 28/28 RED (batches of 10, 10, 8), each failing only its bound test by an AssertionError carrying its clause token.
- Generated sweep: 321 mutants (319 over walk_builders.py's 17 top-level functions, 2 over walk_runner.main), 0 dropped; 89 run on the Mac, all killed (next section).
- Neighbours: test_walk_runner R6Cli + R11Units + R10Guards, Ran 18, OK; its `--witnesses cli-runs` 1/1 red (registry 67); its G1Generated OK; its generated sweep on walk_runner.main's two new mutants: 2 run, 2 killed by R6 (533 generated, as before).
- Gates, exit 0: `copy_manifest.py --check` (358 files, 54 fragments); `freeze.py --check` (358 owned paths); `build_draft.py --check`; `walk_register.py --check` (0 walks).
- `lint_language.py evals/gap-study-4/`: clean, 100 inputs, 23 excused lines (unchanged). `lint_pooling.py evals/gap-study-4/`: clean, 100 files.
- `test_round4.module_problems()`: `[]`.

## Generated sweep on the Mac (a sample; the whole sweep is athena's)

- Each chunk of three ids ran as `--generated-mutants --only <ids> --timeout 110` behind `light-ok` and `timeout -s INT 120`.
- In order, the first 60 generated ids (walk_identity, identity_for, login_name, login_file_by_name and the start of login_secrets): 60 run, 60 killed, 0 survived, 0 inconclusive.
- The Mac then held on memory pressure for most of 25 minutes, so the in-order run was stopped there (by its script's own name) and a stratified sample of the remaining 261 ran instead: every ninth id, 29 ids across build_run_tree, build_walk_fixture, cli, counters_reader, login_file_by_name, missing, parse, prepare, production_builders, walk_driver_for and walk_row: 29 run, 29 killed, 0 survived, 0 inconclusive.
- In all, 89 of 321 run and 89 killed; EQUIVALENT is empty. The 232 not run on the Mac are in the 16 shard lines for athena.

## Ownership and departures

- New, claimed in `COPIED.d/w12b-walk-builders.json`: `walk_builders.py`, `tests/test_walk_builders.py`, `checks.d/w12b-walk-builders.txt`, the fragment itself.
- Departure w12b-1: `walk_runner.py` (lane w10's): `main` takes an optional builder set and hands its argv to `walk_builders.cli`; `CLI_REFUSAL`'s words (still naming Q-w7b-3) and the module docstring follow. Recorded at the end of w10's `walk_runner.py` entry.
- Departure w12b-2: `tests/test_walk_runner.py` (lane w10's): the cli-runs witness's anchor follows main's new body; no assertion changed. Recorded at the end of w10's entry for it.
- w10's generated sweep still mutates `walk_runner.main` (now two statements, both killed by R6); this lane's sweep mutates it too, with the builder-set tests.
- `tests/walk_mutation.py` is reused unchanged: this module patches its `ROAD` for the call (`mock.patch.dict`), with a road read by AST from walk_builders.py, so a new function is in the sweep without an edit.

## Open questions (proposed answers)

- Q-w12b-1: the run tree's exclusions, identity and subject. `build_run_tree` uses round 3's `clean_run_tree`, whose checkout identity and subject are `drive.TREE_IDENTITY`/`TREE_SUBJECT`, while check4 reads them from the PENDING `run_location` constants. Proposed: when `run_location` is measured, one test binds the two (the walk's checkout must read clean under check4's checkout check); until then `run_tree_exclude` keeps the CLI refused.
- Q-w12b-2: the walk row takes the design's first row for the cell (repeat 1, its pressure). Proposed: accept; walk_plan's specs carry no pressure or repeat, and w10's rig reads a row the same way.
- Q-w12b-3: run-tree removal after a committed or launch-refused walk uses `shutil.rmtree`; under rootless Docker the agent's uid-mapped files may refuse it (`CALLER_PENDING["tree ownership"]`). The failure is reported in the JSON line (`run_tree_kept`), never over the walk's state. Proposed: the bring-up (item 4) measures the removal road and this function adopts it.
- Q-w12b-4: the fixture builder runs the round-3 generators on the operator host, as round 3 did; stage 01's exits come from that run (the project-fixture input of item 5). Proposed: accept; the first real walk of a project-fixture task is the first live reading of them.
- Not built (the runtime half, after item 4): the DockerRuntime, and every row of the table above.

## Modules athena must run

- `tests/test_walk_builders.py`, its `--witnesses` (28), and its generated sweep in the 16 shard lines of `checks.d/w12b-walk-builders.txt`.
- `tests/test_walk_runner.py` whole, `--witnesses` (67), and its 12 generated shards (main's body changed).
- `tests/test_walk_wiring.py`, `test_box_integration.py` (whole), `test_scaffold.py` (whole: a new fragment), `test_pipeline.py`, `test_wave6_bindings.py`, `test_round4.py` (the battery).
- The gates: `copy_manifest --check`, `build_draft --check`, `freeze.py --check`, `walk_register --check`, `lint_language` and `lint_pooling` over the folder.

## Fold w12b-R1, Tue 13 Oct 2026 (review round 1 PASS; glitch-2f's fold list)

Review: `lane-reports/w12b-walk-builders-review-r1.md` (in `/Users/javrodher/aegis-builds/gap4-w12b-review`), PASS, three MINORs and one note.
athena run `gap4-w12b-bc66fdf-20261013T101052Z` on `bc66fdfd`: everything passed apart from four generated survivors (shards 10, 11, 15 and 16), folded here too.

What changed:
- W12B-R1-1: `login_file_by_name` fstats the opened descriptor and refuses ("changed between its check and its read") unless its device, inode and mode are the checked path's.
  B2 swaps three things in after the check (lstat patched to answer the checked file's stat): a regular file of another inode and mode (the fstat refuses), a link (O_NOFOLLOW refuses at open) and a FIFO (opens without blocking under O_NONBLOCK, then the fstat refuses); every open is asserted to carry both flags, and an open without O_NONBLOCK is answered as an error by the test's opener so the run never blocks.
  Witnesses login-fstat-unchecked, login-follows-links (O_NOFOLLOW at 0), login-blocks-on-fifo (O_NONBLOCK at 0).
- W12B-R1-2: `missing()` names a value held as None ("present but None"). Witness missing-none-present.
- W12B-R1-3: `cli` reads `production_builders()` inside the refusal, so an unreadable routing table exits 2 by name (witness table-error-raises); `prepare` refuses a walk id that is not one path segment (`walk_register.WALK_ID`) before anything is built (witness walk-id-unchecked); when `run_walks` raises, the run tree is kept and its path printed on its own `kept run tree:` line before the exception goes on (witness kept-tree-unnamed).
- W12B-R1-4 (note): `drive.neutral_name` keeps 32 bits of the session id, so two walk ids can share a run-tree name (the reviewer found `w-105050` and `w-105131`); the second walk's build fails closed with "already exists" and the first walk's tree is left intact. Left as round 3 made it.
- athena's survivors: the exact refusal line (`refused: <CLI_REFUSAL>` as the last stderr line) is now asserted in both refusal roads; the command line's JSON output line is parsed by assertion with its four keys; a relative cgroup folder that exists is refused (the `isabs` clause); `remove_run_tree`'s final `return None` is listed EQUIVALENT (deleted, the function falls off its end and returns None).

Evidence (Mac, light-ok before each batch, `timeout -s INT 120`, python3.13):
- Red first: the five new or tightened fold tests against `8a86a246`'s `walk_builders.py` (byte backup restored, `shasum -c` OK): 5 run, 6 failures (per subTest), 0 errors, each by assertion.
- Green on the fold: `test_walk_builders: 43 run, 0 failures, 0 errors, 0 skipped`.
- athena's four survivors through `--generated-mutants --only`: three killed (B7's two refusal-line tests, B9's held walk, B3's bad folder) and the listed one EQUIVALENT; the `kept run tree` print killed by its new test.
- The generator now makes 346 mutants (the fold's new lines); the checks.d count comment says so, still 16 shards.
- Of the fold's 20 generated mutants on its new lines, 15 ran on the Mac and were killed; the other 5, the seven new hand witnesses, and the gates and lints on this head were not run on the Mac.
  From 07:30 EDT the Mac sat at `light hold: memory pressure critical`, and it was still holding at 08:02, so they were handed to athena's rerun (its checks.d lines run `--witnesses` and every shard).
  The witnesses' anchors were checked against the file when they were written, and each witness compiles only when its anchor occurs exactly once.
