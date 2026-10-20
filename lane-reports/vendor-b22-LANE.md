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
