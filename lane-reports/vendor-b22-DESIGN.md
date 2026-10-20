# vendor-b22 design note: file_change in item.started (round 1, no code)

Local executor, Tue 20 Oct 2026, 16:53 EDT / 20:53 UTC, on `19c7a88f` (branch lane/vendor-b22-20261020).
Ruling B22-1 (glitch-26): design first; stop for review.

## 0. The problem, reproduced

GPT walk w-o38 (gpt-6-luna, plan-gate normal) was held at turn 1 with "StreamError: the stream holds a record off the pre-registered tables: item.started carrying 'file_change': only ('command_execution', 'mcp_tool_call') are pre-registered there".

On `19c7a88f`, a synthetic record of w-o38's shape (types and keys only; the path is invented) gives the same text, word for word:

- `check_record({"type": "item.started", "item": {"id": "item_9", "type": "file_change", "changes": [{"path": "/tmp/run-x/a.txt", "kind": "update"}], "status": "in_progress"}})` raises `ShapeError: item.started carrying 'file_change': only ('command_execution', 'mcp_tool_call') are pre-registered there`.
- `codex_adapter.read_stream` on that one line raises `StreamError: the stream holds a record off the pre-registered tables: item.started carrying 'file_change': ...`.
- The matching `item.completed` (status `completed`) already passes `check_record` and maps to `[tool-call edit {path}, tool-result]` with ref `item_9#0`.

The refusal is at `transcript_codex.STARTED_ITEM_TYPES` (transcript_codex.py:96), checked at transcript_codex.py:167-168.
That tuple was this module's own guess: its docstring lists "which item types an item.started may carry" under "NOT in D8 (... unverified in this lane ...)" (transcript_codex.py:21-26).

## 1. Sources read

- Codex `github.com/openai/codex` commit `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`, the same pin as B11, B17 and B20.
  - `git ls-remote https://github.com/openai/codex.git 'refs/tags/rust-v0.162.1^{}'` printed `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`.
  - Fetched read-only with `git fetch --depth 1 --filter=blob:none origin 092d3acd...` into the session scratchpad; `git rev-parse FETCH_HEAD` printed the same commit.
  - The box pins `@openai/codex` 0.162.1 (B20-DESIGN.md section 1).
- The committed GPT walks: the records clone `/Users/javrodher/aegis-builds/gap4-walk-records-20261019`, its 31 `walk/w-*` branches holding an `rehearsals/w-o*` folder, read by `git show` only (no checkout, no write).
  31 walks: w-o7 to w-o16, w-o18 to w-o37, w-o46 (gpt-6-luna: w-o7 to w-o10, w-o29 to w-o37; gpt-6.1-sol: the rest), model read from each `turn-1.jsonl.launch.json` argv `-m`.
- w-o38 on athena (`/home/javier/w-wjRPXXvG`), read-only over `ssh athena` with `python3 -I -B -` on stdin: `repo/evals/gap-study-4/rehearsals/w-o38/turn-1.jsonl`, types, keys and counts only.
  The folder holds no `session/native-turn-*.jsonl` (the walk was held before the copy-out), so its rollout was not read.
- No transcript text was printed, copied or committed; the counting script printed types, key names, enum values and counts only.

## 2. What the pinned exec stream can carry, per event

The printer is `EventProcessorWithJsonOutput` (codex-rs/exec/src/event_processor_with_jsonl_output.rs, "EP" below); the wire types are codex-rs/exec/src/exec_events.rs ("EE").
Every item is `{"id": <exec id>, "type": <snake_case tag>, ...fields}` (EE:97-102, `#[serde(flatten)]` details with `#[serde(tag = "type", rename_all = "snake_case")]`, EE:105-107).
The exec id is synthetic, `item_<n>` (EP:100-102); an item.started and its item.completed carry the same exec id (EP:327-341, `started_item_id` / `completed_item_id`).

### 2a. The nine item types and their exact fields (EE:107-133 and each struct)

| type | fields after id, type | source |
|---|---|---|
| agent_message | text: string | EE:138-140 |
| reasoning | text: string | EE:144-146 |
| command_execution | command: string, aggregated_output: string, exit_code: int or null, status: in_progress / completed / failed / declined | EE:149-166 |
| file_change | changes: [{path: string, kind: add / delete / update}], status: in_progress / completed / failed | EE:168-198 |
| mcp_tool_call | server, tool, arguments (JSON), result ({content, _meta?, structured_content} or null), error ({message} or null), status | EE:200-294 |
| collab_tool_call | tool (spawn_agent / send_input / wait / close_agent), sender_thread_id, receiver_thread_ids, prompt, agents_states, status | EE:210-259 |
| web_search | id (a second, inner id), query, action, results? | EE:296-306 |
| todo_list | items: [{text, completed}] | EE:314-324 |
| error | message: string | EE:308-312 |

### 2b. Which event can carry which type

- **item.started** (EP:477-482 via `map_started_item`, EP:343-351): every type `map_item_with_id` maps (EP:143-325) except agent_message and reasoning, which return None.
  So: command_execution, **file_change**, mcp_tool_call, collab_tool_call, web_search; and todo_list from a plan update (EP:568-591).
  The upstream doc comment on FileChange, "emitted only as a completed event once the patch succeeds or fails" (EE:116-117), is stale at this pin: the code emits it started too.
- **item.updated**: only todo_list, from a second plan update (EP:568-578). Nothing else is ever printed as item.updated.
- **item.completed** (EP:483-493, plus EP:409-472, 494-507, 513-524): all nine types; error items from warnings, config warnings, deprecation notices and model reroutes; a todo_list closed at turn end; and any started item the turn never completed, closed from the turn's items (`reconcile_unfinished_started_items`, EP:370-385).

### 2c. file_change in item.started: its exact shape

- Core emits it at the apply_patch tool's Begin stage: `emit_turn_item_started(TurnItem::FileChange { id: call_id, changes, status: None, auto_approved: Some(..), stdout: None, stderr: None })` (core/src/tools/events.rs:241-263).
- The app-server conversion turns `status: None` into `PatchApplyStatus::InProgress` and the changes map into a path-sorted list (app-server-protocol/src/protocol/v2/item.rs:1028-1035; item_builders.rs:342-353).
- Exec keeps only `changes` (path, kind) and `status` (EP:182-206); `Update { move_path }` prints as plain `update` (EP:194), and a declined patch prints as `failed` (EP:201-203).
- So the one item.started shape is `{"type": "item.started", "item": {"id": "item_<n>", "type": "file_change", "changes": [{"path": ..., "kind": "add" | "delete" | "update"}, ...], "status": "in_progress"}}`.
  Its keys are exactly the table's file_change entry (id, type, changes, status); only the status value differs from the completed record.
- The completed record is the same item with status `completed` or `failed` (core events.rs:605-619, `emit_patch_end`).

## 3. What the adapter's tables admit today, per event (transcript_codex.py at `19c7a88f`)

| type | item.started | item.updated | item.completed |
|---|---|---|---|
| agent_message | refused (correct: never printed) | refused (event) | admitted |
| reasoning | refused (correct: never printed) | refused (event) | admitted |
| command_execution | admitted | refused (event) | admitted |
| file_change | **refused (Codex prints it)** | refused (event) | admitted; kind `delete` refused (Q-w11a-3) |
| mcp_tool_call | admitted | refused (event) | admitted |
| collab_tool_call | refused | refused (event) | refused |
| web_search | refused | refused (event) | refused |
| todo_list | refused | refused (event) | refused |
| error | refused | refused (event) | refused, except the one reroute shape read before the tables (codex_adapter.py:212-215) |

item.updated is not in EVENT_KEYS at all (transcript_codex.py:66-74).
file_change in item.started is the only cell where the pinned CLI prints a type in a shape the tables already hold, and the tables still refuse it.

## 4. What the real walks show (types, keys, counts)

### 4a. The 31 committed GPT walks (76 turn streams)

| record | count | item keys |
|---|---|---|
| thread.started | 76 | |
| turn.started | 76 | |
| turn.completed | 76 | |
| item.started:command_execution | 188 | aggregated_output, command, exit_code, id, status, type |
| item.completed:command_execution | 188 | aggregated_output, command, exit_code, id, status, type |
| item.completed:agent_message | 141 | id, text, type |

No file_change, mcp_tool_call, reasoning, todo_list, web_search, collab_tool_call or error item, and no item.updated, in any of the 76 streams (13 gpt-6-luna walks, 18 gpt-6.1-sol).
Their rollouts (`session/native-turn-*.jsonl`) by record and payload type: event_msg item_completed CommandExecution 442, AgentMessage 323, Reasoning 248, UserMessage 167; response_item custom_tool_call `exec` 423 and its 423 outputs, message 794, reasoning 248; no FileChange item and no function_call.
So no committed walk ever edited a file through the patch tool; every change went through a shell command.

### 4b. w-o38 (gpt-6-luna, turn 1, 26 lines)

| record | count | item keys |
|---|---|---|
| thread.started, turn.started, turn.completed | 1 each | (top-level keys as the tables hold) |
| item.started:command_execution | 8 | aggregated_output, command, exit_code, id, status, type |
| item.completed:command_execution | 8 | the same |
| item.completed:agent_message | 3 | id, text, type |
| **item.started:file_change** | **2** | **changes, id, status, type** |
| item.completed:file_change | 2 | changes, id, status, type |

- Each file_change holds one change, change keys exactly `kind, path`, kind `update` (2 of 2 started, 2 of 2 completed), path absolute and under `/tmp/run-` (4 of 4).
- status: `in_progress` in both item.started records, `completed` in both item.completed records.
- Every id is `item_<n>`; ids pair as started/completed for all 8 command_executions and both file_changes, and agent_message ids stand alone (3).
- Order: each item.started:file_change is followed directly by its item.completed:file_change.
- No other type off the tables appears, so admitting file_change in item.started is the only change this stream needs (the first refused line was the only one).

## 5. What the reader and the graders need from a file_change item

**The view (transcript_view.events through vendor_record_binding.bound_items, which calls CodexParser.items on every line, vendor_record_binding.py:91-135).**
- CodexParser maps item.completed:file_change to one `tool-call` per change (`add` -> write, `update` -> edit, args `{path}`, ref `<id>#<i>`) and its `tool-result` (status text) (transcript_codex.py:216-225).
- CodexParser maps every item.started that is not command_execution to `tool-call other {}` with ref `<id>` (transcript_codex.py:202-207).
  If only STARTED_ITEM_TYPES were widened, each w-o38 file change would enter the view twice: a phantom `other` call with ref `1:item_N` that never gets a result (events() does not refuse an unanswered call, transcript_view.py:767-800), then the real `edit` call.
- Graders read tool calls from the view:
  - pause_adherence counts every `tool-call` (graders/pause_adherence.py:253);
  - precondition_refusal reads write and edit calls (graders/precondition_refusal.py:360, 451, 465);
  - new_tasks reads write and edit calls after the probe (graders/new_tasks.py:542-546);
  - scope_read reads read, write and edit calls (graders/scope_read.py:231-235).
  A phantom `other` call would add a call the agent did not make and shift every later call number, so the parser must not map the started record to a call.
- What the graders need is already in the completed record: the path and kind of each change (write vs edit) and that the change happened.
  The started record carries the same id and the same changes, with status `in_progress`; it adds nothing a grader reads.
  The completed record is also the one Codex always prints, even for a patch whose started item was never closed (EP:370-385), so the view stays one call per change whether or not a started record precedes it.
- The end-state reader reads the snapshots, not the stream: graders/endstate.py names `snapshot` on 44 lines and imports neither transcript_view nor any tool-call kind (grep at `19c7a88f`). No grader can read file contents from the stream: its file_change carries no content (no diff, no text: exec drops `diff`, EP:187-196).

**The adapter (codex_adapter.read_stream).** item.started is only checked; agent_output and tool_ids come from item.completed (codex_adapter.py:243-250). Nothing changes there.

**check_take.** `_codex_exec_records` already reads file_change items of either event for reach (check_take.py:4030-4041); a started record adds the same path strings again, which reach reads as strings, so no new reach finding can arise from it.

## 6. Recommendation (the narrowest admission)

Two edits, both in transcript_codex.py, nothing else:

1. **check_record.** `STARTED_ITEM_TYPES` gains `FILE_CHANGE`: `(COMMAND_EXECUTION, FILE_CHANGE, MCP_TOOL_CALL)`.
   Narrower still, and my recommendation: an item.started:file_change must carry `status` and its value must be exactly `in_progress`, the only value the pinned code can print there (section 2c; 2 of 2 in w-o38).
   The completed record's status stays as it is (a string, unpinned), and `delete` stays refused in both events (Q-w11a-3; w-o38 has none).
2. **CodexParser.items.** item.started:file_change maps to no view item (an empty list); item.completed:file_change keeps its mapping unchanged.
   This keeps the view at one call and one result per change, as on `19c7a88f` for a completed-only stream.

Docstring: the "which item types an item.started may carry" clause moves from "NOT in D8" to the pinned-source block, citing EP:343-351, EP:477-482, core/src/tools/events.rs:241-263 and v2/item.rs:1028-1035, with w-o38 named as the walk that showed it; the VIEW MAPPING line for file_change gains "item.started -> nothing (the completed record carries the call)".

Unchanged: EVENT_KEYS (item.updated stays refused), ITEM_KEYS, CHANGE_KINDS, OUTPUT_ITEM_TYPES, TOOL_ITEM_TYPES, every value table, codex_adapter.py and its READ_SHAPES (they match command_execution, CommandExecution and custom_tool_call only, codex_adapter.py:144-173), and every Gemini and Claude table (B22-3).
READ_SHAPES need no re-pin: no shape names file_change.

For B22-2, the tests I would expect (stated here, built only after the ruling):
- red on `19c7a88f`: a synthetic two-line stream of w-o38's shape (item.started then item.completed file_change, one `update` change) refused by check_record, decode and read_stream with the live text;
- green: it reads, and through a COPY of PARSERS the view holds exactly one `edit` call and one result for it (not two calls);
- witnesses, each red alone: FILE_CHANGE dropped from STARTED_ITEM_TYPES; the `in_progress` pin dropped (a started file_change with `completed` passes); the parser mapping the started record to a call (the view holds two calls); agent_message admitted in item.started (the existing S2 case);
- test_codex_adapter's D8_ITEMS and EVENT_TYPES pins stay as they are; its generated mutation sweep (`--generated-mutants`) gains mutants on the new lines, and any survivor needs an EQUIVALENT entry with its reason (its run is longer than the Mac's bound, so athena's);
- COPIED.d/w11a-codex-adapter.json's reason for transcript_codex.py gains one B22 sentence, and the new test claim rides with the red commit (F21-2's lesson).

## 7. Types the next walks might hit, named for the ruling and not admitted

- **file_change with kind `delete`**, in either event: the pinned CLI prints it (EE:194-198, EP:193) whenever a patch deletes a file. Refused since Q-w11a-3, in item.completed too, so it is not new to this lane; no walk shows one. Possible, not certain.
- **collab_tool_call** in item.started and item.completed: `multi_agent` is a stable feature, on by default at the pin (codex-rs/features/src/lib.rs:1415-1418), and each of the three rollouts I counted (w-o7, w-o35, w-o46) names `spawn_agent` on one line. None of the 32 walks' streams holds one, nor any of the 31 committed rollouts. Possible, not certain.
- **error items** other than the reroute (warnings, config warnings, deprecation notices, EP:409-472): printed whenever the CLI warns; none in 32 walks. Possible, not certain.
- **todo_list** (item.started / item.updated / item.completed): needs `tools.update_plan.enabled = true` (core/src/config/mod.rs:2730-2736; spec_plan.rs:1228-1230); the box's Codex config sets no such key (box/take_config.py:61-71). It cannot occur in a take.
- **web_search**: the box sets `web_search = "disabled"` (box/take_config.py:61). Not expected.

None of these is certain for the next walks, so none is admitted here.

## 8. Downstream of the admission (outside B22-4, recorded only)

A take holding a file_change gets past the adapter after this change, and then meets three readers that refuse or hold it, each by design and none on a walk's road today:
- check_take's `vendor_file_change_problems` raises the PENDING row T-8:file-change, `[transcript-unreadable] no vendor reader yet (T-8:file-change)`, for any codex take whose stream holds a file_change (check_take.py:3775, 4816-4828).
- codex_native.read_exec refuses a file_change exec item as "unsupported in this subset" (codex_native.py:315-318), and codex_native's rollout reader refuses a FileChange TurnItem the same way (codex_native.py:153-158).
- Today every committed GPT walk's check.json reads `pending-native-reader` ("no reviewed native-session reader for codex") and is not graded (w-o11 and w-o35 checked), so neither reader runs on a walk yet.
Whether w-o38's rollout persists a FileChange item was not checked: its rollout is not in the folder.

## 9. Not touched

No code, no test, no fixture. The records clone and athena were read only. No push, no mirror, no athena run.

## 10. B22-10: switching off the GPT arm's delegation tools (design, appended Tue 20 Oct 2026, 17:08 EDT / 21:08 UTC)

glitch-26's ruling B22-10: the study refuses delegation on the vendor side (Gemini's `invoke_agent` was excluded under R-B14-2, box/take_config.py:124-125; the Claude arm keeps its Agent tool as a named difference).
Design only; no code until the ruling.
Source: the same pin, 092d3acd (section 1). Rollout facts: the 31 committed GPT walks' 76 rollouts, counts and names only.

### 10a. `[agents] enabled = false` gives Disabled ahead of the catalog's v2, for both arm O models

- The key: `ConfigToml.agents: Option<AgentsToml>` (config/src/config_toml.rs:481), with `AgentsToml.enabled: Option<bool>` (config_toml.rs:753-756); `Config.agents_enabled` is that value, defaulting to true (core/src/config/mod.rs:3893-3897).
- The override (mod.rs:1604-1611): `features.multi_agent_v2` on gives V2; else `!agents_enabled` gives `Some(Disabled)`; else None. The box's `[features]` holds only `hooks = false` and `plugins = false` (box/take_config.py:69), and `multi_agent_v2` defaults off (features/src/lib.rs:1421-1424), so the first branch is never taken and `enabled = false` gives `Some(Disabled)`.
- `multi_agent_version_for_model(model_version)` is `override().or(model_version).unwrap_or_else(...)` (mod.rs:1624-1631): the override comes first, so Disabled stands ahead of the model catalog's `"multi_agent_version": "v2"` for gpt-6.1-sol (models-manager/models.json:194) and gpt-6-luna (:541) alike.
- Every road a take's turn takes reads that override first:
  - the session's version at start: `config.multi_agent_version_override().or_else(|| resolve_multi_agent_version(history, inherited))` (core/src/session/mod.rs:772-774), so a resumed thread (turn 2 onward, `codex exec resume`) is Disabled too, whatever its history says;
  - the thread manager's spawn: `effective_multi_agent_version_for_spawn` returns the override before any history (core/src/thread_manager.rs:1760-1770);
  - each turn's context: `resolve_multi_agent_version_for_model` (session/mod.rs:4155-4166) and the prewarm road (session/turn_context.rs:1286-1299) both go through `multi_agent_version_for_model`.

### 10b. What disappears

- **The six tools.** `collab_tools_enabled` is false for Disabled (core/src/tools/spec_plan.rs:719-731), so none of the collaboration handlers is registered (spec_plan.rs:1376-1470: SpawnAgentHandlerV2, SendMessageHandlerV2, FollowupTaskHandlerV2, WaitAgentHandlerV2, InterruptAgentHandler, ListAgentsHandlerV2), and the required child-management list is empty (spec_plan.rs:733-764).
  These are exactly the six names the rollouts show: spawn_agent, send_message, followup_task, wait_agent, interrupt_agent, list_agents.
- **Two developer-message sections**, both returning None unless the turn is V2 (core/src/session/multi_agents.rs:14-17, 82-84) and assembled at session/world_state.rs:351-358:
  - the multi-agent role instructions (the `<multi_agent_role>` part, here the model catalog's text, `marked` because it is a catalog override; prompts/src/multi_agent_instructions.rs), which carries the shared usage hint naming the six tools and `functions.collaboration`;
  - the multi-agent mode section (`<multi_agent_mode>`, protocol/src/protocol.rs:137-138): with no mode and no earlier state it renders nothing (context/world_state/multi_agent_mode.rs:61-80).
  In the committed rollouts, of 228 developer messages and 384 content parts, 76 parts carry `<multi_agent_role>`, 76 `<multi_agent_mode>`, 76 `spawn_agent` and 76 `functions.collaboration`: one per rollout, in all 31 walks. After the switch, none should.
- **The model catalog section** stays empty either way: it needs `model_catalog_in_context`, off by default (session/world_state.rs:377-392).

### 10c. What else changes, and what does not

- **The rollout's turn_context** records `multi_agent_version` (session/turn_context.rs:912, serialized snake_case, protocol.rs:3109-3116): all 167 committed turn_context records read `"v2"`; they will read `"disabled"`. session_meta carries none (76 of 76 None). No study reader reads that field: no non-test module under evals/gap-study-4 names `multi_agent` (grep).
- **An interrupted turn's history marker** would be a contextual-user message rather than a developer one (tasks/mod.rs:85-97). It applies only when Codex itself records an interrupted turn; a take's timed-out exec is killed and leaves no turn record, so I expect no take to show it (not measured).
- **The exec stream** is unchanged: collab_tool_call items can no longer occur, and no committed walk had one (0 in 76 streams). The other item types, the event types and the usage keys do not depend on the version.
- **The other tools**: `exec` and `wait` (code mode) are not gated on the version. The collaboration tools are already absent from `functions.exec`'s `tools.*` namespace (the hint text, multi_agent_instructions.rs:9-15), so the exec tool's nested list should not change. I did not render the tool list to confirm this; the rollout records no tool specs.
- **The prompt otherwise**: the base instructions do not name any delegation tool (the names appear in no other record of the 76 rollouts), and nothing else in the world-state assembly reads the version.
- **The config's bytes and the pre-registration draft**: config.toml gains an `[agents]` table for arm O.
  Its sha256 is pinned per model in prereg-draft.json's config templates (`config_templates`, build_draft.py:1020-1033; prereg-draft.json:23586 and :23595), so the green commit must rebuild the draft (`build_draft --check` goes red until then). Gemini's and Claude's entries stay byte-identical.

### 10d. What it means for the practice walks already committed

- Their offered list differs from every walk after the switch: they had the six collaboration tools and the two developer sections; later walks have neither. No committed walk called a delegation tool (0 direct calls, 0 collab_tool_call items).
- Those practice walks are marked "Commit one walk; never counted", and every one read `pending-native-reader` and went ungraded (section 8), so no counted result changes. Their prompts are not byte-comparable with later walks' on these two sections; the lane file should say so beside the change, and the walk register needs no edit (it was not checked here).

### 10e. Proposed change, for the ruling

In box/take_config.py only:
- `CODEX_AGENTS = (("enabled", False),)`, rendered by `_codex` as an `[agents]` table after `[features]` and before `[otel]`, for arm O only; a `VALUE_SOURCES["CODEX_AGENTS"]` entry citing config_toml.rs:753-756, mod.rs:1604-1611, 1624-1631 and 3893-3897, models.json:194 and :541, and spec_plan.rs:719-731; a comment naming B22-10 and R-B14-2 as its sibling.
- Red first: a test that `files_for(CODEX, ...)` for each arm O model holds `[agents]` with `enabled = false` (red on the current tree, which writes no such table), and that Gemini's and Claude's files are byte-identical to `34f7340f`'s (sha256 pinned).
- Green: the key, and the rebuilt prereg-draft.json (two codex sha256 pairs move; nothing else).
- Witnesses: the key dropped and the key set true each go red alone; the table written for Gemini too goes red.
- Existing pins to re-check: test_take_config's Codex cases, including its study-word check (line 909), which rejects certain config words.
