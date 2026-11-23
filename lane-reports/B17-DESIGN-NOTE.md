# B17 design note: OD57's admission for the Gemini and Codex arms' reads of the ruled doc

Lane vendor-b17, round 1 (glitch-26's rulings B17-1 to B17-4; Javier's "b17-local yes", OrgOS ask b17-local, T101).
Local executor on the Mac, worktree branch work/b17-local-20261019 from 67075247.
Design and red tests only: glitch-26 rules this note before any green code.

## 0. The fact, and what does not change

Practice walk w-g9 (Gemini arm, on 7dc0cf9e) was held at the drive scan: gitleaks' generic-api-key on a line of the turn stream and of both native session files.
Each flagged line carries the OD57 ruled line once, raw, inside the agent's read of gars/_references/environment.md.
scan_record admits that line only inside a Claude Code tool_result block whose tool_use is a Read or an admitted Bash grep or cat (box/scan_record.py:570-579, 596-618), so these records refuse although the bytes are the ruled ones.
OD57's text, rule, 80 bytes, sha256 (box/scan_record.py:116-120) and every other ruling stay exactly as they are.
I did not read any walk record (B17-4 and the round's rules); every record shape below is read from the harness and the pinned vendor sources.

Sources, read only, each pin checked in this session:

- Codex CLI source at 092d3acd6bec3e3a14bdc7e7a2810ab628ab759d (rust-v0.162.1): `git rev-parse HEAD` printed exactly that hash. Cited as codex-rs/<path>:<line>.
- Gemini CLI 0.64.0 package: the tarball's sha256 printed 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6, the pin. Cited as bundle/<file>:<line>.
- The harness at 67075247, cited as <file>:<line> under evals/gap-study-4/.

Which files the scan sees: a take or walk folder's `turn-<N>.jsonl` is kind `stream` and anything under `session/` is kind `session` (drive.py:1844, 3901-3918); both are agent-text kinds (box/scan_record.py:80).

## 1. The Gemini arm (Gemini CLI 0.64.0)

### 1.1 The read tools

The headless arm's tool table holds two tools that return a file's text to the model (transcript_gemini.py:108-128, from the pinned registry):

- `read_file` {file_path, start_line, end_line} (transcript_gemini.py:111).
  Its model-facing result (llmContent) is the selected lines joined by newline, with no line numbers (bundle/chunk-NR7L3FXV.js:254074-254084), plus any JIT context appended after them (:314453-314460).
  Its display string (returnDisplay) is empty or a summary such as "Read lines a-b of n from <path>", never the file's text (:254085-254093, :314462-314470).
- `run_shell_command` {command, description, dir_path, is_background, delay_ms} (transcript_gemini.py:109-110).
  Its llmContent is `Output: <stdout>`, then optional Error/Exit Code/Signal lines (:326193-326214), wrapped as `<untrusted_context>\n...\n</untrusted_context>` (:326351-326352, wrapUntrusted :274616-274620).
  Its returnDisplay is the raw stdout (:326232-326233; in debug mode the llmContent, :326217-326218; an ANSI output array when the shell produced one, which is then not a string).
- `grep_search` (and its alias `search_file_content`) also returns matching lines to the model; Claude's Grep tool is not admitted by OD57 today, so this note does not propose it (open point O2).

### 1.2 The turn stream (`-o stream-json`, written by the drive as turn-<N>.jsonl)

- Call: `{"type": "tool_use", "timestamp", "tool_name", "tool_id", "parameters"}` (bundle/gemini-Q2GRYIAK.js:12223-12229, and :11830-11836 on the agent-session road; harness transcript_gemini.py:71).
- Result: `{"type": "tool_result", "timestamp", "tool_id", "status", "output"[, "error"]}`, named to its call by `tool_id` (gemini-Q2GRYIAK.js:12351-12361 and :11846-11856; harness transcript_gemini.py:72, 259-262).
- Where the text sits: `output` is the tool's display string only (`typeof resultDisplay === "string" ? resultDisplay : void 0`, :12356; `displayContentToString(event.display?.result)`, :11843-11851).
  So a `read_file` result in the stream never carries the doc's text, and a `run_shell_command` result carries the raw stdout, unprefixed.
  The flagged stream record of w-g9 (keys output, status, timestamp, tool_id, type) is this shape; that its call was a shell read is my inference from these lines (open point O8).

### 1.3 The native session file (chats/session-*.jsonl, kept by the box under session/)

The recorder appends one JSON object per line (bundle/chunk-NR7L3FXV.js:286808-286816) to `session-<time>-<short id>.jsonl`, or `<session id>.jsonl` under the parent's folder for a sub-agent (:286716-286733).
It appends a whole message again each time the message changes, and a reader keeps the last copy by id (pushMessage :286885-286897; harness gemini_session_replay.py:111-120, "dict assignment mirrors Map.set").
Four record shapes carry a tool's result:

- G-S1, the gemini message with its tool calls: `{"id", "timestamp", "type": "gemini", "content", "thoughts", "tokens", "model", "toolCalls": [...]}` (recordToolCalls :286975-287025; harness gemini_projection.py:81).
  Each toolCalls entry holds the call and its result together: `{"id", "name", "args", "result", "status", "timestamp", "resultDisplay", "description", "displayName", "renderOutputAsMarkdown"[, "agentId"]}` (recordCompletedToolCalls :334058-334073, enriched at :286979-286986; harness gemini_projection.py:82-83).
  `result` is the call's response parts, each `{"functionResponse": {"id", "name", "response": {"output"}}}` (createFunctionResponsePart :289967-289975; harness gemini_projection.py:85).
  The text sits in `functionResponse.response.output` (the llmContent above) and, for a shell read, a second time in `resultDisplay` (the raw stdout).
  A call's `result` may also hold its sibling calls' responses, each named by its own id (harness gemini_projection.py:58-61, from updateMessagesFromHistory).
  Amended in round 6 (glitch-26's ruling on review baef7c51's O25): a part inside an entry's `result` is admitted only when its `functionResponse.id` is that entry's own id (the position's anchor). A sibling's response held there is not admitted; see the known limit in section 7.
  This is the w-g9 session record shape (keys content, id, model, thoughts, timestamp, tokens, toolCalls, type).
  The same message is appended again on a later update (its tokens, :286950-286966, or more tool calls, :287007-287024), so one call id appears on several lines, each copy the same call.
- G-S2, the function-response turn: `{"id", "timestamp", "type": "user", "content": [functionResponse parts]}` (recordSyntheticMessage for a function response, :333244-333252 and :333285; also appended by updateMessagesFromHistory, :287190-287196; harness gemini_projection.py:156-165).
  Its call is a toolCalls entry of an earlier gemini message, found by `functionResponse.id`.
- G-S3, a `$patch` record: `{"$patch": {"updates": [{"id": <message id>, "toolCalls": [{"id", "result"}], "content"}], ...}}` (:287199-287265; harness gemini_session_replay.py:97-108).
  The call is again a toolCalls entry, found by the patched call id.
- G-S4, a `$patch` content change: `{"$patch": {"updates": [{"id", "content": <parts>}]}}` (:287167-287182), whose parts may be the turn's functionResponse parts; the same rule as G-S2 applies to each part.

Where the line sits inside the text: in a `read_file` output the ruled line is a whole line with no prefix; in a shell output it is a whole line of stdout, except that the first stdout line is preceded by `Output: ` (:326193); `grep -n` and grep's file-name prefixes are the ones the scan already allows (box/scan_record.py:123).

## 2. The Codex arm (Codex CLI 0.162.1)

### 2.1 The read tool

The pinned CLI offers one shell tool family, unified exec, or none (ConfigShellToolType::{UnifiedExec, Disabled}, codex-rs/protocol/src/openai_models.rs:316-320).
Its tools are `exec_command` {cmd, workdir, tty, yield_time_ms, max_output_tokens[, shell][, login]} and `write_stdin` {session_id, chars, ...} (codex-rs/core/src/tools/handlers/shell_spec.rs:24-114, 117-159).
There is no file-read tool: every read of the doc is a shell command, run as argv `[<shell path>, "-lc" | "-c", <script>]` (codex-rs/core/src/shell.rs:24-33).

### 2.2 The turn stream (`codex exec --json`, written by the drive as turn-<N>.jsonl)

- C-T1: `{"type": "item.started" | "item.completed", "item": {"id", "type": "command_execution", "command", "aggregated_output", "exit_code", "status"}}` (codex-rs/exec/src/event_processor_with_jsonl_output.rs:162-181, 474-491; harness transcript_codex.py:85-93, 202-213; codex_native.py:45-47).
  The call and its output are one item: `command` is the presentation string `redact_secrets(shlex_join(argv))` (codex-rs/app-server-protocol/src/protocol/item_builders.rs:54-61, 96-143), so it reads `/bin/bash -lc '<script>'`; `aggregated_output` is the raw output.
  The item id is synthetic, `item_<n>` (event_processor_with_jsonl_output.rs:100-102); item.started and item.completed of one call share it (:327-341), and the started copy carries an empty output.

### 2.3 The native session file (the rollout, rollout-*.jsonl, kept under session/)

Each line is `{"timestamp", "ordinal", "type", "payload"}` (codex-rs/history/src/lib.rs:357-368; harness codex_native.py:7-14, 104).

- C-R1, the call: `{"type": "response_item", "payload": {"type": "function_call", "name": "exec_command", "arguments": <a JSON string>, "call_id"[, "id", "namespace", ...]}}` (codex-rs/protocol/src/models.rs:1076-1095).
  `arguments` is a string holding JSON (:1084-1087), so the script is `json.loads(arguments)["cmd"]`.
- C-R2, the model-facing result: `{"type": "response_item", "payload": {"type": "function_call_output", "call_id", "output"[, "id", "name", "namespace"]}}` (models.rs:1111-1135).
  This closes the cloud's open point on its keys: `call_id`, `name`, `namespace` and `id` are optional and skipped when absent; `output` is either a plain string or an array of content items, each text item `{"type": "input_text", "text"}` (models.rs:2096-2104, 2187-2192, 2252-2265; a single text item is sent as the plain string, codex-rs/core/src/tools/context.rs:578-603).
  The text is `exec_command`'s response: a header (`Chunk ID: ...`, `Wall time: ...`, `Process exited with code ...`, `Process running with session ID ...`, `Original token count: ...`, each when present), then `Output:`, then the output on the following lines (context.rs:524-575), possibly truncated with a warning line first (:495-522).
  So the ruled line is a whole line of the output, with no new prefix.
- C-R3, the turn item: `{"type": "event_msg", "payload": {"type": "item_completed", "thread_id", "turn_id", "item": {"type": "CommandExecution", "id", "command", "cwd", "parsed_cmd", "source", "status", "aggregated_output", "exit_code", ...}}}` (codex-rs/protocol/src/items.rs:243-281; built with `id: call_id` and `command: argv`, codex-rs/core/src/tools/events.rs:561-589; harness codex_native.py:21-23, 179-188).
  The call and its output are one item again: `command` is the argv list, `aggregated_output` the raw output (truncated past 64 KiB, codex_native.py:37-42).

## 3. The proposal

### 3.1 OD57's five constraints, applied unchanged

1. The exact 80 bytes: `_ruled_text` as today (sha256 and length of a whole line, after an allowed prefix), plus one prefix: `Output: ` before the first stdout line of a Gemini shell result, declared by that shape alone.
2. Only inside a read of that doc, whose call is found by its id exactly once in the same file:
   - a read-by-path call (Gemini `read_file`) admits when its path argument equals the doc's path or ends in `/_references/environment.md`; this is stricter than the Claude Read today, which admits a Read of any path;
   - a shell call admits when its script passes `_ruled_bash` unchanged; the script is the argument itself (Gemini `run_shell_command`'s `command`; Codex `exec_command`'s `cmd`, after decoding `arguments`), or, for Codex's own wrapper (C-T1's string, C-R3's argv), the third element of exactly `[<shell>, "-lc" | "-c", <script>]` with `<shell>` one of bash, zsh or sh, bare or absolute; anything else (another flag, a fourth element, zsh's brokered `-lfc`) refuses;
   - the call is found by its id: the result's id (Gemini stream `tool_id`; a functionResponse part's `id`; Codex `call_id`; a self-contained item's own `id`) must name exactly one call in the file.
     For Codex's call records (C-R1) and the Gemini stream, exactly one call record carries the id, as today.
     For the self-contained items (C-T1, C-R3, a G-S1 entry), the call is the item itself; every other item in the file with the same id must be the same call (the Codex item.started copy, a Gemini re-append), and one with another command, name or args refuses.
     For Gemini's session, "exactly once" becomes: the id names exactly one distinct (name, args) across the file's toolCalls entries, because the recorder re-appends the same message by design (open point O1, for glitch-26).
   - a functionResponse part's own `name` must equal its call's name.
3. Only in an agent-text kind: unchanged (MASKABLE, box/scan_record.py:80).
4. The probe rescan: unchanged (`_ruled_findings`, box/scan_record.py:646-690), and the "nowhere else on the record" guard (`_ruled_text`, :640-642) counts the text in every result string the shape names, so a G-S1 shell entry counts both `response.output` and `resultDisplay`, and a copy anywhere else on the record (the model's own content, an argument) still refuses.
5. Each admitted finding listed in `ruled`: unchanged.

### 3.2 Where the shapes live and how they reach the scan (scan_record.py stays vendor-neutral)

Recommended (A): scan_record.py gains a closed, role-named vocabulary of read shapes and no vendor word.
A shape record says, as data: how a call is found (its record's type value, id key, name key, args key, or a key holding JSON text), how a result is found (its type value or containing key, id key, the paths of its text strings), whether call and result are one object, which tools are reads by path (name, path key) and which by script (name, script key, or the wrapper form), and any extra first-line prefix.
scan_record checks each shape record against that closed schema (an unknown field or kind refuses with ScanError) and keeps every OD57 constraint in its own code.
The per-arm records live beside each arm's existing seam code, which may type a harness name (checks.d/w4c-cp2-sidecar-scan.txt refuses `codex`, `gemini` and `claude-code` only in box/sidecar.py and box/scan_record.py): GEMINI_READ_SHAPES in gemini_adapter.py and CODEX_READ_SHAPES in codex_adapter.py, each line citing the source lines in sections 1 and 2.
They reach the scan as an argument: `scan(files, secrets, *, rules_scanner, holdout_matcher=None, read_shapes=())`, and the same for `scan_with_witness`; the drive passes the take's arm's shapes at its three scan calls (drive.py:1699, 2880, 4096) from the arm it already resolved for that take.
With the default `()` today's Claude admission is unchanged byte for byte, so a Claude take can never be admitted through another arm's shape, and test_sidecar's import allow-list for scan_record does not change (no new import).
This changes drive.py, which this round leaves untouched; the green round would.

Alternative (B): the same role-named shapes held as constants inside scan_record.py and always on for every file.
No drive.py change, but every arm's shapes then apply to every take, which admits more than needed; I do not recommend it.

The red tests call `sr.scan` with today's interface; under (A) their one helper (`TestOD57Ruling.scan`, used through `TestOD57OtherArms.scanned`) would pass the arm's shapes, a fixture change and never an assertion change.

## 4. The door on athena (for glitch-26 only)

What ops/athena_suite.py's OD57 twin (aegis workspace, lines 1305-1399, "keep the two byte-identical in logic") would need for the same admission:

1. Its agent-text pattern `RULED_AGENT_TEXT` (athena_suite.py:1324-1325) names only `rehearsals/w[0-9]+/`; the practice walks write `rehearsals/w-g<N>/` and `rehearsals/w-o<N>/`, so it must name those folders too (exactly, not any name).
2. Its session-file part already takes `session/**/<name>.jsonl`, which covers Gemini's chats files and Codex's rollout files; a sub-agent file under the drive's sub-agent folder (drive.py:3916-3917) is not in it, as today.
3. A way to know each walk folder's arm, so it applies only that arm's shapes (the folder's prefix, or the walk's own ledger field): an open point for the door's lane.
4. The same shape vocabulary, the per-arm shape records and the constraint code as the harness's green round, including the `Output: ` prefix, the wrapper unwrap and the JSON-string arguments decode; its `_ruled_tool_uses` (:1346-1364) finds only `tool_use` blocks today.
5. Its probe rescan at the commit and its `ruled_used` listing, unchanged.
6. Its test twin (ops/test_athena_od57.py, whose walk folder is `rehearsals/w001/`) gains the same synthesized cases.

## 5. Open points for glitch-26

- O1. Gemini's re-appended messages: "the call found by its id exactly once" cannot hold literally in its session file; the note proposes "exactly one distinct call (name, args) for the id across the file".
- O2. Gemini `grep_search` over the doc returns its matching lines to the model; Claude's Grep is not admitted by OD57, so the note does not admit it either.
- O3. A `read_file` result may end with JIT context the CLI appends (:314453-314460); admission is per line, so this changes nothing, but it is text the scan reads.
- O4. Codex `exec_command` with `tty: true` runs in a PTY, whose lines may end in a carriage return; such a line is 81 bytes and refuses (admitting less is fine). Output read back through `write_stdin` refuses too (its call is not a read).
- O5. Codex's zsh fork road may run `-lfc` or `-fc` (codex-rs/core/src/tools/runtimes/mod.rs:325-339); the note admits only `-lc` and `-c`.
- O6. Which two native session files w-g9 held (a main chat and a sub-agent chat, or two chats) I did not check, since no walk record is read; the tests cover every shape in section 1.3 instead.
- O7. Gemini's stream output for a shell read in debug mode would be the llmContent with its `Output: ` prefix (:326217-326218); the prefix rule covers it, and whether the arm runs in debug mode I did not check.
- O8. That w-g9's stream finding came from a `run_shell_command` read is inferred from section 1.2 (a `read_file` stream result never carries the text); glitch-26 can confirm it from the held scan record.
- O9. The Gemini session's G-S4 content patch is named from the source but has no red test of its own; it uses the same functionResponse rule as G-S2.

## 6. Round 4: C-R1 and C-R2 re-derived against the committed arm O rollouts (B17-16d)

Read by counts and key names only, from the committed arm O walks w-o7 to w-o14 (eight folders on the walk/* branches of gap4-walk-records-20261019, the reviewer's census scripts census_o2.py and census_o4.py, run unchanged).

- The native rollouts hold 97 `response_item` `custom_tool_call` records, every one `name=exec`, with the keys call_id, id, input, internal_chat_message_metadata_passthrough, name, status and type, and a string input.
- They hold 97 `custom_tool_call_output` records, with the keys call_id, id, internal_chat_message_metadata_passthrough, output and type, and `output` a list of `input_text` items.
- They hold no `function_call` and no `function_call_output` record.
- They hold 108 `CommandExecution` items, all `source='unified_exec_startup'`, with the keys aggregated_output, command, cwd, duration, exit_code, id, parsed_cmd, process_id, source, status and type. No item's id is a custom_tool_call call_id.
- Every exec input contains `tools.`, `await ` and `exec_command`: this is Codex's code mode, whose script calls exec_command inside.

Why there is no function_call: both arm O models (prereg-draft.json "O": gpt-6.1-sol, gpt-6-luna) carry `"tool_mode": "code_mode_only"` in the pinned catalog.
The citations are at codex-rs/models-manager/models.json: gpt-6.1-sol is at slug line 177 and tool_mode line 193, and gpt-6-luna at lines 524 and 540.
requested_tool_mode takes the model's tool_mode first (core/src/tools/mod.rs:75-85), and effective_tool_mode keeps CodeModeOnly (:87-97).
In CodeModeOnly every tool but `exec` and `wait` is hidden (core/src/tools/spec_plan.rs:838-850; code-mode-protocol/src/lib.rs:54-55, description.rs:262-263), so exec_command is never offered as a direct function.
So C-R1 (function_call) and C-R2 (function_call_output) cannot be emitted by the pinned arm O configuration, and their shapes are removed.
In their place:

- C-R3 (the CommandExecution item) admits on its own argv, as a joined shape pinned to `[/bin/bash, -lc, script]`, which all 108 committed items match (B17-16a).
- C-R4, new: the exec `custom_tool_call_output` admits the ruled line only inside a verbatim copy of an admitted C-R3 item's aggregated_output in the same file. Its call is a `custom_tool_call` named `exec` with the same call id, and nothing else in that output is admitted by this rule (B17-16b).

Known limit (round 4): a tty exec's `tty` argument now sits only inside the exec script's text, which no shape reads. Its output is held by its CRLF bytes, in the rollout as in the stream.

## 7. Round 5: the exec output's real forms (B17-17), by counts only

The census was census_r5.py (scratchpad/b17regress-tool/), over the committed arm O rollouts (gap4-walk-records-20261019, walk/* branches, 20 distinct native files read through git cat-file, run under a heavy booking).
It printed counts, booleans and model slugs only.
Each of the 108 CommandExecution items lies inside exactly one exec call/output pair by line order.
Its aggregated_output was looked for in that pair's custom_tool_call_output items:

| model | A verbatim | B one JSON string literal, escaped once | C double-escaped | D other |
|---|---|---|---|---|
| gpt-6-luna (36) | 32 | 0 | 0 | 4 |
| gpt-6.1-sol (72) | 0 | 60 | 0 | 12 |

- B: in all 60, the escaped form appears with its own quotes, as one whole JSON string literal. 54 sit in an item that is a JSON object, and 6 in an item that is not. The reviewer counted 38 escaped for gpt-6.1-sol because ascii escaping hid the non-ASCII outputs; the real literal keeps non-ASCII raw.
- D: all 16 are lossy. Each item holds a truncation marker, only 50 to 90 percent of the non-empty lines are present, and the first half of the output is not; this is a middle truncation. 4 of gpt-6.1-sol's 12 scripts pipe through `head`.
- Admitted (B17-17a): A, and B as one JSON string literal whose single `json.loads` decode equals the read's output exactly, its opening quote not escaped. C never occurs, so it is not admitted. D stays refused: a lossy copy cannot be shown to come from the read. That is a known limit, 16 of 108 committed outputs, all of them reads of other files.
- B17-18: each position of the ruled line in an exec output counts once, however many sources match it.
- B17-19: an exec output's sources are only the CommandExecutions that lie between its own exec call's line and its own line.

Round 6 (glitch-26's B17-20 to B17-22 on review 8776055a):

- B17-20: the literal is `json.dumps(read, ensure_ascii=False)` only, the JSON.stringify form. The doc holds 17 non-ASCII characters, and a gpt-6.1-sol fixture with non-ASCII text pins it.
- B17-22: the ASCII-escaped form is refused, since no real record uses it. A source admits through its literal only when the output holds exactly one copy of that literal, and the literal's opening quote is preceded, after optional whitespace, by `:`, `[` or `,`.
- B17-21: a CommandExecution is a source only when it lies in exactly one exec window, and an exec call with more than one output admits nothing.
- The reviewer's swap census (review-b17r5.9sfX/census_r5r.py, run unchanged on round 6's code) gives the same counts as round 5.
  - All 108 CommandExecutions sit in exactly one window, each exec has one call and one output, and every argv is [/bin/bash, -lc, script].
  - Admitted by `_ruled_text` with a doc read swapped in: gpt-6-luna 28 of 32 verbatim (26 with a unique anchor, 2 with a short one) and gpt-6.1-sol 57 of 60 literals (31 and 26).
  - The other 7 find their copy (copy hits 1) and are refused only because the census's short stand-in anchor recurs in the record, which is an artifact of the method.
  - So 92 of 92 non-lossy outputs carry an admissible copy under the tightened rule.
- Known limit (round 5, glitch-26): a toolCalls entry whose result holds a sibling's functionResponse with the line refuses, failing closed, until a real record shows it.
