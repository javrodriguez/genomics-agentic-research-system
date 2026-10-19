# B16-2: a model-invented argument on a known Gemini tool (design note, no code)

Lane vendor-b16, round 1, under glitch-26's ruling B16-2 (Mon 19 Oct 2026). The Gemini practice walk on this head was held with StreamError: "the stream holds a record off the pre-registered tables: tool_use: tool 'grep_search': argument keys with no entry: ['file_path']". Nothing here changes a reader. The walk is not re-run.

Source: the verified Gemini CLI 0.64.0 tarball (sha256 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6). It was unpacked outside the clone and only read, never run. Files cited: bundle/chunk-NR7L3FXV.js (sha256 d566e81b...) and bundle/gemini-Q2GRYIAK.js (sha256 7702da31...).

## 1. Is file_path a parameter of grep_search?

No. It is not in either schema, in either tool family.

- Parameter names (chunk-NR7L3FXV.js 280599-280618): PARAM_FILE_PATH is "file_path" and PARAM_DIR_PATH is "dir_path". GREP_TOOL_NAME is "grep_search".
- Gemini-3 family (GEMINI_3_SET from 282708), which both arm G models resolve to:
  - grep (282751-282789): pattern, dir_path, include_pattern, exclude_pattern, names_only, max_matches_per_file, total_max_matches; required [pattern] (282788).
  - ripgrep (282791-282856): the same plus case_sensitive, fixed_strings, context, after, before, no_ignore; required [pattern] (282855).
- Default-legacy family (DEFAULT_LEGACY_SET from 282113): grep at 282158 (required 282195) and ripgrep at 282198 (required 282262) carry the same keys.
- Both tools also get wait_for_previous, added by the base getSchema (274269-274305).
- No grep schema sets additionalProperties. In this chunk's tool sets, only write_todos does (282573/282578 and 283142/283147).

transcript_gemini's _GREP_KEYS (transcript_gemini.py line 106) is already this set. The table is right. The model invented the key.

## 2. What the CLI does with a call that carries an undeclared argument

The call runs, and file_path is ignored.

1. The model's functionCall becomes a request with its args untouched: Turn.handlePendingFunctionCall, `args2 = fnCall.args || {}` (334519), carried as `args: args2` (334543). The display-only build at 334528 swallows errors.
2. The stream records the call before it runs, with the model's args verbatim. The ToolCallRequest branch emits tool_use {tool_name, tool_id, parameters: event.value.args} (gemini-Q2GRYIAK.js 12221-12229). So the stream's parameters hold file_path exactly as the model sent it.
3. The scheduler validates through build. The non-interactive road creates a Scheduler (gemini-Q2GRYIAK.js 12121) and calls scheduler.schedule (12342). Scheduler._validateAndCreateToolCall calls tool.build(request.args) (chunk-NR7L3FXV.js 349325), and a throw there becomes an Error call with INVALID_TOOL_PARAMS (349345-349354).
   - BaseDeclarativeTool.build calls validateToolParams (274389-274395). That runs SchemaValidator.validate on this.schema.parametersJsonSchema, then validateToolParamValues (274396-274401).
   - this.schema is getSchema() with no model id (274309-274311), so it is the definition's base, the default-legacy schema (resolveToolDeclaration, 309221-309224), plus wait_for_previous. It has no file_path either.
4. Validation passes. SchemaValidator (273788-273822) compiles the schema with Ajv, whose options set only strictSchema: false (273774). JSON Schema allows any additional property unless additionalProperties is false, and no grep schema sets it. No Ajv option strips or refuses extra keys.
   - GrepTool.validateToolParamValues (322156-322199) and RipGrepTool.validateToolParamValues (322578-322623) check pattern, exclude_pattern, the two caps and dir_path only. They never look at file_path.
5. The search runs over the working directory. Both invocations read only this.params.dir_path: grep at 321746 and 322126-322127, ripgrep at 322258 (`this.params.dir_path || "."`). With no dir_path, the search covers the take's whole working directory, and file_path has no effect.
6. The stream then records an ordinary result. tool_result {tool_id, status "success", output: resultDisplay, error: undefined} (gemini-Q2GRYIAK.js 12350-12361). Nothing in the stream marks the ignored key. The native session records the same call with the same args dict (the projection's args, gemini_projection.py 196 and 208-209).

So the stream is faithful: it shows what the model asked for (parameters with file_path) and what ran (a search of the working directory), with no error. The CLI's only possible refusal here is an Error call with INVALID_TOOL_PARAMS (349345-349354). That fires for a value off its type or a failing validateToolParamValues, never for an extra key.

## 3. How the study's readers treat a model-invented argument on a known tool

- **Arm G stream, transcript_gemini: refused.** tool_kind (transcript_gemini.py 181-185) calls transcript_view.map_tool(GEMINI_TOOLS, ...). map_tool refuses any raw key outside the entry's allowed keys (transcript_view.py 214-217, "argument keys with no entry"). gemini_adapter turns that into StreamError (gemini_adapter.py 152), which held the walk.
- **Arm G native readers: accepted.** gemini_projection keeps args as a structured dict with no key check (gemini_projection.py 196, 208-209, 234). gemini_stream_join compares the stream's parameters with the native args as exact JSON (gemini_stream_join.py 84, 123, 138-139). Both would accept file_path, because both sides carry it.
- **Arm O, the Codex readers: never sees the keys.** transcript_codex reads the exec stream, which never carries a model's raw function-call arguments:
  - command_execution is read as the CLI's rendered command string (transcript_codex.py 203-204).
  - file_change is read as its path and kind (219-225).
  - An mcp_tool_call's arguments are untyped and read as OTHER with no args (transcript_codex.py 111-112, 205-206).
  - codex_native admits a rollout response_item (function_call included) by its type alone and never reads its arguments (codex_native.py 230-233).

  An invented argument on a Codex tool is therefore neither refused nor visible to the study.
- **Arm A, the Claude Code reader: refused by the same closed rule.** ClaudeCodeParser maps each tool_use block through map_tool(CC_TOOLS, name, input) (transcript_view.py 557; table 253-273, e.g. Grep at 260-262). An input key outside the entry refuses with the same "argument keys with no entry" ViewError (214-217). This note does not read whether Claude Code 2.1.296 itself refuses or ignores such a key; that would need Claude Code's own tool-input validation read from its pinned package.

## 4. Options

- **A. Keep the closed rule as it is.** Every model-invented key on a known tool holds the stream as a harness-shape error.
  - For: nothing moves.
  - Against: it holds a take for something the agent did, not something the harness or the reader got wrong. The CLI ran the call and the stream reads it faithfully. Arm G would be held at a rate set by the model's own argument slips, which the other arms do not see in the same way (arm O cannot see them at all).
- **B. Read an undeclared key on a known Gemini tool as named, ignored input (recommended).**
  - Scope: transcript_gemini only. For a tool name already in GEMINI_TOOLS, a raw key outside the entry's allowed keys is not refused when both of these hold:
    1. The pinned schema sets no additionalProperties: false for that tool, so Ajv passes it (step 4 above).
    2. The tool's invocation reads only declared keys, cited per tool in gemini_tool_sources.py, as B12 cited the keys.
  - The view's args stay what the CLI ran: here path None, the working directory, from transcript_view.py 225-226. The undeclared keys are kept by name on the view item (for example an `undeclared_args` list), so graders and the labelling sheet see the model's mistake and it never silently vanishes.
  - Still refused: an unknown tool name, a declared key off its type, a tool whose schema closes its properties (write_todos), and a tool whose invocation would read the key.
  - Red first: the held walk's tool_use record (or a synthetic one of the same shape) read with path None and file_path named, plus witnesses (the per-tool citation removed; additionalProperties false assumed; the name dropped from the view) each red alone.
  - This edits transcript_gemini.py, a READER_SOURCES file. It needs a named exception like B12's, before any native reader acceptance record exists.
- **C. Route the call as an agent event, not a stream error.** Admit the record but mark the turn executed-and-refused (ExecutedTurnRefused), so the take ends for a human with the turn counted.
  - For: nothing of the agent's mistake is lost.
  - Against: it still ends the take for a call the CLI ran normally. It also adds a new routed reason that the other arms have no counterpart for.

## 5. Recommendation

Option B, for arm G only, and only per tool where the pinned package shows the key is passed through and never read.

The CLI ran the call. The stream records both what the model asked and what ran. A reader that holds the take is reporting the agent's slip as a reader failure. Naming the undeclared key on the view keeps the slip visible without guessing what the model meant: the view shows the search that actually ran.

Arm A's reader refuses under the same rule. Whether to change it should be ruled separately, after reading Claude Code's own validation of tool input: if Claude Code refuses the call itself, its record carries an error result and the reader's rule should match that. Arm O needs nothing, because no Codex reader reads tool-call argument keys.
