Status: design stop (round 1)

## ROUND 1 (local executor, Tue 20 Oct 2026, 16:53 EDT / 20:53 UTC)

glitch-26's ruling B22-1: design first, no code. Base `19c7a88f` (B21 at `45239b01` plus B21-9's two check lines).

- Design note: lane-reports/vendor-b22-DESIGN.md.
- Reproduced on `19c7a88f` with a synthetic record of w-o38's shape: check_record raises `ShapeError: item.started carrying 'file_change': only ('command_execution', 'mcp_tool_call') are pre-registered there`, and read_stream raises the live text, word for word.
- Source: openai/codex `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d` (`git ls-remote ... 'refs/tags/rust-v0.162.1^{}'` printed it), fetched read-only into the session scratchpad.
  The pinned exec prints file_change in item.started (EP:343-351, 477-482; core events.rs:241-263), always with status `in_progress` (v2/item.rs:1028-1035), and its keys are exactly the table's entry.
- Counts (types, keys and enum values only):
  - 31 committed GPT walks, 76 turn streams: command_execution 188 started and 188 completed, agent_message 141 completed, thread.started, turn.started and turn.completed 76 each; no file_change, no other item type, no item.updated.
  - w-o38 turn 1, 26 lines: command_execution 8 started and 8 completed, agent_message 3, file_change 2 started (status `in_progress`) and 2 completed (status `completed`), one `update` change each, change keys `kind, path`.
- Recommendation: STARTED_ITEM_TYPES gains FILE_CHANGE, with a started file_change's status pinned to `in_progress`; CodexParser maps item.started:file_change to no view item, so the view keeps one call per change (otherwise pause_adherence and the other call readers would see a phantom `other` call).
  READ_SHAPES, codex_adapter.py, the Gemini and Claude tables: unchanged.
- Named for the ruling, not admitted: file_change kind `delete`, collab_tool_call (multi_agent on by default, spawn_agent offered, 0 seen), non-reroute error items. Ruled out by the box's config: todo_list and item.updated (update_plan off), web_search (disabled).
- Downstream, recorded only (B22-4): check_take's T-8:file-change PENDING row and codex_native's two "unsupported in this subset" refusals meet any take holding a file_change; today's walks stop at `pending-native-reader` before either runs.
- Not touched: code, tests, fixtures, the records clone, athena (read only). Nothing pushed.

RESUME HERE: design stop; waiting for glitch-26's ruling on section 6 (and the names in section 7).

## ROUND 2 (local executor, Tue 20 Oct 2026, 17:03 EDT / 21:03 UTC)

Status: needs-review (round 2). This supersedes round 1's status and RESUME lines above; no line above is edited.

glitch-26's rulings: B22-6 (admit as recommended, transcript_codex.py only), B22-7 (`delete` stays refused; a walk showing one holds and goes to glitch-26), B22-8 (collab_tool_call, other error items, todo_list, item.updated and web_search stay refused; report the offered delegation tools).

### Red `1d60b7b5` (tests and their COPIED.d claim only)

- New `evals/gap-study-4/tests/test_codex_started_file_change.py`: F1-admit (w-o38's synthetic shape through check_record, decode and read_stream), F2-status, F3-view (through a copy of PARSERS), F4-closed, three in-memory mutants (`--witnesses`), and `--walks <records clone>`.
- COPIED.d/vendor-admission.json claims it, in the red commit (F21-2's lesson).
- Runner on 19c7a88f's transcript_codex.py: `Ran 5 tests in 0.003s`, `FAILED (failures=2, errors=1)`.
  - F1: "line 5: refused: item.started carrying 'file_change': only ('command_execution', 'mcp_tool_call') are pre-registered there", the live text.
  - F3: "the view refuses: line 5: item.started carrying 'file_change': ...".
  - Mutants: `WitnessNotPerformed: the anchor occurs 0 times` (the anchors are the green lines).
  - F2 and F4 green on the base: every started file_change was refused there, so their refusals held trivially; F2's admitting half (completed `completed` and `failed` read) also held.
- copy_manifest --check on the red tree: `ok: 492 files from 60 fragment(s) ...` (12.2 s).

### Green `22a63652`

- transcript_codex.py:
  - `STARTED_ITEM_TYPES = (COMMAND_EXECUTION, FILE_CHANGE, MCP_TOOL_CALL)`;
  - `STARTED_FILE_CHANGE_STATUS = "in_progress"`, and check_record refuses a started file_change whose status is anything else or missing ("its status must be 'in_progress', the only one the pinned exec prints there"); keys stay the table's entry, `delete` and an empty change list stay refused;
  - CodexParser maps item.started:file_change to `[]`; the completed mapping is unchanged;
  - docstring: the started-item clause moved from "NOT in D8" to a pinned-source block (EP:343-351, 477-482; core events.rs:241-263; v2/item.rs:1028-1035; w-o38), and the VIEW MAPPING line for file_change names the started record.
- COPIED.d/w11a-codex-adapter.json: one B22 sentence appended to transcript_codex.py's reason.
- B22-3: the diff from 19c7a88f touches transcript_codex.py, the two COPIED.d fragments, the new test and the two lane files only; no Gemini, Claude, adapter, READ_SHAPES, scanner, drive, preflight, postflight, sidecar or bookkeeping file.

### Runner lines on the green tree (Mac, after light-ok, env -i, Python 3.13.2)

- test_codex_started_file_change: `Ran 5 tests in 0.009s`, `OK`.
- `--witnesses`: `witnesses: 3/3 red`.
  - `type-removed-again (admit); red checks: admit, view`
  - `status-check-removed (status); red checks: status`
  - `started-mapped-to-a-call (view); red checks: view` (the view's calls become shell 1, other 2, edit 3, shell 4).
- `--walks /Users/javrodher/aegis-builds/gap4-walk-records-20261019` (3.3 s): `walks: 76 streams of 31 walks, identical before and after`; totals `item.completed:agent_message 141, item.completed:command_execution 188, item.started:command_execution 188, streams 76, thread.started 76, turn.completed 76, turn.started 76, walks 31`, equal to the design note's; readings sha256 `450946a3a7454492cc824d2c92f8c3561e457f2597cfb96768f1108a052ae43c`.
  - Not hollow: an unrecorded probe that planted a parser change (shell `background` read as true) in this tree's module gave 68 differing streams (the 8 others hold no shell call).
  - It needs the records clone, which lives on the Mac; it is a command-line mode, not a unittest, so the battery does not depend on a Mac path.
- Neighbouring modules, each under a 45 s cap: test_codex_adapter `Ran 57` OK (2 s), its `--witnesses` `16/16 red; registry 16`; test_codex_native `Ran 15` OK; test_vendor_check `Ran 26` OK; test_nested_agent `Ran 35` OK; test_scan_record `Ran 203` OK (6 s); test_labelling `Ran 109` OK (8 s); test_codex_executed_refusal `Ran 5` OK; test_codex_identity `Ran 5` OK; test_codex_usage_source `Ran 3` OK, `--witnesses` `9/9 red`; test_jsonl_split `Ran 5` OK.
  - test_pending_codex_walk: stopped by the 45 s cap, athena's.
- copy_manifest --check: `ok: 492 files from 60 fragment(s) ...`; freeze --check: `freeze: 493 owned paths checked; no takes or freeze performed`; build_draft --check: `ok: the committed draft is what build_draft.py builds`; `check_vendor_sources.py P2 transcript_codex.py tests/test_codex_started_file_change.py`: exit 0.

### For athena's battery (glitch-26 runs these; each needs its own runner line)

From the repository root:
- `python3 -B -W ignore evals/gap-study-4/tests/test_codex_adapter.py --generated-mutants` (or sharded: `... --generated-mutants --shard 1/4` to `--shard 4/4`): the generated sweep over transcript_codex.py and codex_adapter.py; the new lines add mutants, and any survivor needs an EQUIVALENT entry with its reason, which would come back to this lane.
- `python3 -B -W ignore evals/gap-study-4/tests/test_codex_started_file_change.py` and the same with `--witnesses`.
- `python3 -B -W ignore evals/gap-study-4/tests/test_pending_codex_walk.py` (past the Mac's cap).
- the full checks.d/vendor-admission.txt and w11a lines, and the athena suite.
- Proposed, not done (needs your word, as B21-9 did): two checks.d/vendor-admission.txt lines for the new module and its `--witnesses`.

### B22-8: delegation tools offered to the GPT arm (counts and names only, no code change)

- The committed GPT walks' rollouts (31 walks, 76 rollout files; 18 gpt-6.1-sol, 13 gpt-6-luna) were searched for the pinned CLI's delegation tool names (spawn_agent, send_input, send_message, followup_task, wait_agent, close_agent, resume_agent, list_agents, interrupt_agent).
- In 31 of 31 walks (76 of 76 rollouts), one `response_item` `message` with role `developer` names six of them in its text: spawn_agent, send_message, followup_task, wait_agent, interrupt_agent, list_agents. No other record names any.
  - Those six are exactly the names of the pinned multi-agent v2 usage hint (prompts/src/multi_agent_instructions.rs:9-15), which says they are called "only as direct tool calls ... `to=functions.collaboration.spawn_agent`", outside `functions.exec`. So code-mode-only does not hide them.
- No walk called one: 0 function_call or custom_tool_call named for a delegation tool, and 0 collab_tool_call items in the streams.
- Why they are offered (the pinned source):
  - the model catalog gives both arm O models `"multi_agent_version": "v2"` (models-manager/models.json:194 gpt-6.1-sol, :541 gpt-6-luna);
  - `multi_agent_version_for_model` takes the config's override first, then the model's version (core/src/config/mod.rs:1624-1631); the override is V2 when features.multi_agent_v2 is on (default off, features/src/lib.rs:1421-1424), Disabled when `[agents] enabled` is false, else none (mod.rs:1604-1611);
  - `[agents] enabled` defaults to true (mod.rs:3893-3897), and the box's Codex config sets neither `[agents]` nor any multi_agent feature (box/take_config.py, grep);
  - so each take runs multi-agent V2 from the model catalog's default, and `collab_tools_enabled` is true for the root session (core/src/tools/spec_plan.rs:715-731).
- The switch that would turn it off, for a config lane to verify: `[agents] enabled = false`, which makes the override Disabled ahead of the model's version (mod.rs:1607-1608).
- Not verified: the tool list the CLI actually sent (the rollout records the developer instructions, not the request's tool specs). The offer is read from the instructions text plus the source, not from a recorded tool list.

RESUME HERE (round 2): review stop; athena runs the sweep and battery; glitch-26 rules on the checks.d lines and on a config lane for `[agents] enabled = false`.

## B22-9 and B22-10 design (local executor, Tue 20 Oct 2026, 17:08 EDT / 21:08 UTC)

- **B22-9** (`34f7340f`): checks.d/vendor-admission.txt gains `python3 -B -W ignore evals/gap-study-4/tests/test_codex_started_file_change.py` and the same with `--witnesses`, under a lane comment in the existing form (no blank line, as the blocks above). On the Mac after light-ok: the module `Ran 5 tests`, `OK`; `--witnesses` `witnesses: 3/3 red`; copy_manifest --check `ok: 492 files from 60 fragment(s) ...`; freeze --check `freeze: 493 owned paths checked; no takes or freeze performed`.
- **B22-10 design** (`fcc97ce2`, vendor-b22-DESIGN.md section 10, appended): `[agents] enabled = false` in arm O's config.toml makes the override Disabled ahead of the catalog's v2 for both models, on new, resumed and per-turn roads. The six collaboration tools and the `<multi_agent_role>` and `<multi_agent_mode>` developer sections go (76 of 76 committed rollouts carry each now). turn_context's `multi_agent_version` goes from `"v2"` (167 of 167) to `"disabled"`, read by no study reader. The stream and the other tools do not change. prereg-draft.json's two codex config sha256 pairs move, so the green rebuilds the draft. The committed practice walks were offered the six tools, called none, and are uncounted.

RESUME HERE (B22-10): design stop; waiting for glitch-26's ruling on section 10e before the red.

## B22-10 (local executor, Tue 20 Oct 2026, 17:19 EDT / 21:19 UTC)

Status: needs-review (the whole lane, B22-6 to B22-10). This supersedes the earlier status and RESUME lines above; no line above is edited.

glitch-26's ruling on section 10e: build it as proposed, in box/take_config.py; red first; green with the rebuilt draft (only the two codex config hash pairs may move); three witnesses; test_take_config's Codex pins and study-word check re-run.

### Red `b088add5` (tests and the new module's COPIED.d claim)

- New `evals/gap-study-4/tests/test_codex_agents_off.py`:
  - K1: each arm O model's config.toml holds `[agents]` with exactly `enabled = false`, between `[features]` and `[otel]`, and without that table is byte-identical to 34f7340f's (sha256 pinned per model);
  - K2: Gemini's files (both draft models) and Claude Code's are byte-identical to 34f7340f's (build_draft's combined sha256, pinned);
  - K3: `VALUE_SOURCES["CODEX_AGENTS"]` is the record of the pinned reads;
  - three mutants (`--witnesses`).
- `tests/test_take_config.py`, three edits to existing tests, each named here:
  - TestContents' expected codex config.toml gains `"agents": {"enabled": False}`;
  - TestR3Values' VALUE_SOURCES record gains `B22_SOURCES`, imported from the new module so the record is written once;
  - TestB18CodexSwitches sets the `[agents]` table aside, as it does `otel`.
- Runner on the unchanged writer:
  - test_codex_agents_off: `Ran 4 tests`, `FAILED (failures=2, errors=1)`. K1 reads "gpt-6.1-sol: agents is None, not {'enabled': False}" and the same for gpt-6-luna; K3 reads "VALUE_SOURCES['CODEX_AGENTS'] is not the B22 record"; the mutants cannot patch the absent constant; K2 is green (the pins are the base's).
  - test_take_config: `Ran 16 tests`, `FAILED (failures=2)` (TestContents, TestR3Values).
- copy_manifest --check on the red tree: `ok: 493 files from 60 fragment(s) ...`.

### Green `6c60fc0e`

- box/take_config.py:
  - `CODEX_AGENTS = (("enabled", False),)`, with a comment naming B22-10 as R-B14-2's sibling and the Claude arm's Agent tool as the named difference;
  - `_codex` writes `[agents]` after `[features]` and before `[otel]`;
  - `VALUE_SOURCES["CODEX_AGENTS"]` cites 092d3acd: core/src/config/mod.rs 1607, 1629, 3897; config_toml.rs 481, 756; models.json 194, 541; features/src/lib.rs 1424; session/mod.rs 772; spec_plan.rs 721, 1376; session/multi_agents.rs 16, 80. Each cited line was re-read at the pin before it was written.
- prereg-draft.json, rebuilt by `build_draft.py` (`wrote prereg-draft.json: 1260 planned tries, 126 half-cells`; `pending inputs: 22; freeze closed`). `git diff HEAD~1 HEAD -- evals/gap-study-4/prereg-draft.json` changes 4 lines, the two codex hash pairs only:
  - gpt-6.1-sol config.toml `6a2c7537...` -> `dcffae85...`, combined `e56a71d5...` -> `cd3eb17b...`;
  - gpt-6-luna config.toml `41870f8a...` -> `99a064e0...`, combined `52a0fba5...` -> `df62f797...`.
- COPIED.d: one B22 sentence each in the reasons for box/take_config.py and tests/test_take_config.py (w4b-cp2-runtake-preflight.json) and prereg-draft.json (w8b-holdout-digests.json).

### Runner lines on the green tree (Mac, after light-ok, env -i, Python 3.13.2)

- test_codex_agents_off: `Ran 4 tests`, `OK`.
- `--witnesses`: `witnesses: 3/3 red`. Each mutant turns only its own check red: `key-dropped (table)`, `key-set-true (table)`, `gemini-gains-the-table (others)`.
- test_take_config: `Ran 16 tests in 0.431s`, `OK`. Its Codex pins (TestContents, TestB18CodexSwitches, TestR3Values) and its study-word check (`test_b18`'s and line 909's mutants) all ran inside it.
- build_draft --check, after the commit: `ok: the committed draft is what build_draft.py builds`. Before the commit it read FAIL because it compares against HEAD.
- copy_manifest --check: `ok: 493 files from 60 fragment(s) ...`; freeze --check: `freeze: 494 owned paths checked; no takes or freeze performed`.
- `check_vendor_sources.py P2 box/take_config.py tests/test_take_config.py tests/test_codex_agents_off.py prereg-draft.json`: exit 0.
- Other readers of take_config, each under a 45 s cap: test_preflight `Ran 59` OK; test_live_box `Ran 38` OK; test_vendor_roads `Ran 13` OK (32 s); test_env_allowlist `Ran 37` OK; test_settings_guard `Ran 15` OK.
- Under `mac_slot.py run --kind heavy --owner vendor-b22`: test_build_draft `Ran 49 tests in 38.463s`, `OK`; test_walk_builders `Ran 102 tests in 79.773s`, `FAILED (failures=2)`.
- Three reds, each the same on an archive of 34f7340f (`git archive 34f7340f evals`), so none comes from this lane; all are Mac-only:
  - test_walk_builders `B13Lease.test_the_driver_and_walkrepo_get_the_lease_secrets` and `B19VendorConfig.test_the_vendor_config_is_written_on_the_walk_road`: "the run tree '/tmp/tmp.../tree' is not its canonical path, so Codex's trust key would not match it" (macOS /tmp is a link to /private/tmp);
  - test_config_folder `C7Shapes.test_shape_rules`: `OSError: [Errno 92] Illegal byte sequence` creating a non-UTF-8 file name (APFS refuses it).
  These need athena's runner lines to be green.

### For the review and athena

- The practice walks: the 31 committed GPT walks were offered the six collaboration tools (spawn_agent, send_message, followup_task, wait_agent, interrupt_agent, list_agents) and the two developer-message sections (`<multi_agent_role>` and `<multi_agent_mode>`, one each in 76 of 76 rollouts). They called none (0 direct calls, 0 collab_tool_call items). From `6c60fc0e` on, a walk is offered neither, so the committed walks are not byte-comparable with later walks on those two sections. Their turn_context `multi_agent_version` reads `"v2"`; later walks' should read `"disabled"`, which the first walk on this head will show.
- A correction to the design note (append-only, so recorded here): section 10b cites "session/multi_agents.rs:14-17, 82-84"; the mode gate is at line 80, as the VALUE_SOURCES record cites.
- athena's lines, from the repository root: `python3 -B -W ignore evals/gap-study-4/tests/test_codex_agents_off.py` and the same with `--witnesses`; test_take_config, test_walk_builders, test_config_folder and test_build_draft; then the earlier list (test_codex_adapter `--generated-mutants`, test_codex_started_file_change and its `--witnesses`, test_pending_codex_walk, checks.d, the athena suite).
- Proposed, not done: two checks.d/vendor-admission.txt lines for test_codex_agents_off and its `--witnesses`, as B22-9 did, on glitch-26's word.

### The whole lane from 19c7a88f

13 files: transcript_codex.py and box/take_config.py (product); prereg-draft.json (generated); the two new test modules and test_take_config.py; four COPIED.d fragments; checks.d/vendor-admission.txt; the two lane files. Gemini's and Claude Code's tables, configs and adapters are unchanged. Nothing was pushed, mirrored or run on athena.

RESUME HERE (B22-10): review stop for the whole lane (B22-6 to B22-10).

- **B22-11** (Tue 20 Oct 2026, 17:20 EDT): checks.d/vendor-admission.txt gains `python3 -B -W ignore evals/gap-study-4/tests/test_codex_agents_off.py` and the same with `--witnesses`, under a lane comment in the existing form. On the Mac after light-ok: the module `OK`, `--witnesses` `witnesses: 3/3 red`, copy_manifest --check `ok: 493 files from 60 fragment(s) ...`, freeze --check `freeze: 494 owned paths checked; no takes or freeze performed`.
