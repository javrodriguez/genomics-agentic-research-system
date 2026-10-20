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
