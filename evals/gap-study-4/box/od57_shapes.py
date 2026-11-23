#!/usr/bin/env python3
"""OD57's read shapes, data only (lane vendor-b24, glitch-26's ruling B24-2 item 1): how each arm's records carry a
read of gars/_references/environment.md, read by box/od57_rule.py's closed schema. The adapters' READ_SHAPES are these
tuples (gemini_adapter.READ_SHAPES is GEMINI, codex_adapter.READ_SHAPES is CODEX), and the aegis door runs a byte copy of
this file, pinned by its sha256. No imports and no functions: literals, and dict() over them.
"""

# ---- OD57's read shapes for arm G (lane vendor-b17 round 2, glitch-26's rulings B17-5 to B17-7, 19 Oct 2026) ---------
# Moved here from gemini_adapter.py by lane vendor-b24 (B24-2 item 1), byte for byte but these notes. The records
# box/od57_rule.py's read-shape schema reads (drive.scan_read_shapes passes them for an arm G row's scan), each from
# Gemini CLI 0.64.0's pinned bundle (tarball sha256 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6),
# cited as <file>:<line> under bundle/ (lane-reports/B17-DESIGN-NOTE.md section 1). The reads: run_shell_command (its
# model-facing output `Output: <stdout>` inside <untrusted_context>, chunk-NR7L3FXV.js:326193-326214, 326351-326352,
# 274616-274620; its display the raw stdout, :326232-326233) and read_file (its output the file's lines, :254074-254084;
# its display never the text, :254085-254093). grep_search is not a read here (glitch-26's B17-7, as Claude's Grep).
# tests/test_gemini_adapter.py's a15_read_shapes pins these records' bytes; their behaviour is test_scan_record's.
_G_TOOL = {"prefix": None, "opener": None, "shells": None, "flags": None}
_G_SHELL = dict(_G_TOOL, kind="script", arg="command")
_G_SHELL_OUT = dict(_G_SHELL, prefix="Output: ", opener="<untrusted_context>")
_G_READ = dict(_G_TOOL, kind="path", arg="file_path")
# B24-2 item 2 as revised (lane vendor-b24, glitch-26, 21 Oct 2026; w-g22): grep_search (displayName SearchText) is a read.
# Its output is read by box/od57_rule's kind "grep" (each `L175: ` or `L175- ` line inside a File: block that names the
# doc, attested by the call's own display), and its display's match entries by kind "grep-display"
# (bundle/chunk-NR7L3FXV.js:321636-321700, 321596-321635; od57_rule cites them). The legacy alias search_file_content is
# not admitted.
_G_GREP = dict(_G_TOOL, kind="grep", arg="dir_path")
_G_GREP_DISPLAY = dict(_G_TOOL, kind="grep-display", arg="dir_path")
# Round 3 (glitch-26's B17-10, on review a051f6e3's finding 1): every node at its fixed record position, never at any
# depth. A session line is one message ({id, type, content, toolCalls, ...}) or one control record ({"$patch": ...}),
# each at the line's top level (chunk-NR7L3FXV.js:286808-286816; harness gemini_session_replay.py:80-120).
# A toolCalls entry, the session's call: {id, name, args, result, ..., resultDisplay} at a message's toolCalls
# (recordCompletedToolCalls chunk-NR7L3FXV.js:334058-334073); the recorder re-appends a whole message on each update
# (:286885-286897), so every copy of an id must be the same call (copies "same", B17-6); a $patch entry {id, result}
# names no tool and is no copy.
# Round 4 (review dd2d0398's NIT 2): each position also names its record's type: a message's toolCalls only in a
# "gemini" message (recordToolCalls, chunk-NR7L3FXV.js:286975-287025), a function-response turn's content only in a
# "user" message (recordSyntheticMessage, :333285), a $patch at a control line's top level.
_GEMINI, _USER = {"type": ("gemini",)}, {"type": ("user",)}
# Round 5 (review baef7c51's NIT 2): each position is (path, record, anchor), and each shape names its file kind; a
# functionResponse inside a toolCalls entry's result answers that entry (anchor: the entry's id is the part's id).
_G_SESSION_CALL = {"match": {}, "at": ((("toolCalls", "*"), _GEMINI, None),), "id": "id", "name": {"key": "name"},
                   "args": "args", "args_json": False, "text": ()}
# A functionResponse part's positions: a message's toolCalls entry's result, a function-response user turn's content,
# and the same two under a $patch, directly or in its updates (gemini_session_replay.py:97-108).
_G_PARTS = ("toolCalls", "*", "result", "*", "functionResponse"), ("content", "*", "functionResponse")
_G_RESPONSE_AT = ((_G_PARTS[0], _GEMINI, 2), (_G_PARTS[1], _USER, None),
                  (("$patch",) + _G_PARTS[0], {}, 3), (("$patch",) + _G_PARTS[1], {}, None),
                  (("$patch", "updates", "*") + _G_PARTS[0], {}, 5), (("$patch", "updates", "*") + _G_PARTS[1], {}, None))
# B20-5, B20-6 (glitch-26, lane vendor-b20, 20 Oct 2026): a git read binds its folder by its arguments alone. A
# run_shell_command runs in the target directory unless its dir_path names another ([C] 282009, PARAM_DIR_PATH), so the
# call may carry only command and description ([C] 282001, 282005); any other key (dir_path, is_background, ...) refuses.
_G_GIT = {"args": ("command", "description")}
GEMINI = (
    # the turn stream: tool_use {tool_name, tool_id, parameters} and tool_result {tool_id, status, output}, each a whole
    # line, its output the display string only (gemini-Q2GRYIAK.js:12223-12229, 12351-12361; 11830-11836,
    # 11846-11856), so only a shell read carries the doc's text there
    {"shape": "stream tool_result", "copies": "one", "tools": {"run_shell_command": _G_SHELL}, "copy_of": None,
     "kinds": ("stream",), "git": _G_GIT,
     "call": {"match": {"type": "tool_use"}, "at": (((), {"type": ("tool_use",)}, None),), "id": "tool_id",
              "name": {"key": "tool_name"}, "args": "parameters", "args_json": False, "text": ()},
     "result": {"match": {"type": "tool_result"}, "at": (((), {"type": ("tool_result",)}, None),), "id": "tool_id",
                "name": None, "text": (("output",),)}},
    # the session file: every functionResponse part {id, name, response: {output}} (createFunctionResponsePart
    # :289967-289975), in a toolCalls entry's result, a function-response user turn (:333244-333252, 333285) or a
    # $patch (:287199-287265, 287167-287182), found by its own id, its name the call's
    {"shape": "session functionResponse", "copies": "same", "copy_of": None, "kinds": ("session",), "git": _G_GIT,
     "tools": {"run_shell_command": _G_SHELL_OUT, "read_file": _G_READ, "grep_search": _G_GREP},
     "call": _G_SESSION_CALL,
     "result": {"match": {}, "at": _G_RESPONSE_AT, "id": "id", "name": "name", "text": (("response", "output"),)}},
    # the session file: a run_shell_command entry's own resultDisplay, the raw stdout (:334060-334061, 334070;
    # :326232-326233); read_file's display never carries the file's text (:254085-254093), so it is not read here
    # (B17-14)
    {"shape": "session resultDisplay", "copies": "same", "tools": {"run_shell_command": _G_SHELL}, "copy_of": None,
     "kinds": ("session",), "call": dict(_G_SESSION_CALL, text=(("resultDisplay",),)), "result": None, "git": _G_GIT},
    # B24-2: a grep_search entry's own display, its match entries {filePath, absolutePath, lineNumber, line}
    # (321691-321698): an entry is read only when it is the doc's match 175 (box/od57_rule._grep_display)
    {"shape": "session grep display", "copies": "same", "tools": {"grep_search": _G_GREP_DISPLAY}, "copy_of": None,
     "kinds": ("session",), "call": dict(_G_SESSION_CALL, text=(("resultDisplay", "matches"),)), "result": None},
)


# ---- OD57's read shapes for arm O (lane vendor-b17 round 2, glitch-26's rulings B17-5 to B17-7, 19 Oct 2026) ---------
# Moved here from codex_adapter.py by lane vendor-b24 (B24-2 item 1). The records box/od57_rule.py's read-shape schema reads (drive.scan_read_shapes passes them for an arm O row's scan),
# each from the pinned source, openai/codex 092d3acd6bec3e3a14bdc7e7a2810ab628ab759d (rust-v0.162.1), cited as
# codex-rs/<path>:<line> (lane-reports/B17-DESIGN-NOTE.md section 2). The one read tool is the shell: the pinned CLI
# offers unified exec or none (protocol/src/openai_models.rs:316-320), exec_command {cmd, ...}
# (core/src/tools/handlers/shell_spec.rs:24-114), run as exactly [<shell>, -lc | -c, <script>] (core/src/shell.rs:24-33).
# write_stdin's output is not a read (glitch-26's B17-7), nor is a PTY's CRLF line (81 bytes, never the ruled 80).
# Round 3 (glitch-26's B17-10, B17-12 to B17-14, on review a051f6e3): every node at its fixed record position (a stream
# line's top-level `item`; a rollout line's `payload`, or its `payload.item`), never at any depth; the one shell is the
# arm O image's, /bin/bash (box/codex/Dockerfile:18, `useradd ... --shell /bin/bash dana`: the agent user's login shell,
# which Codex runs as [shell, -lc | -c, script], core/src/shell.rs:24-33), both as a wrapper's argv[0] and as
# exec_command's `shell` argument (shell_spec.rs:65-72); and a call with `tty: true` (shell_spec.rs:47-53) is no read,
# whatever its output's line ending.
# Round 4 (glitch-26's B17-16a to B17-16d and NIT 2, on review dd2d0398's MAJOR 1): both arm O models run code mode
# only. The pinned catalog marks gpt-6.1-sol and gpt-6-luna `"tool_mode": "code_mode_only"` (models-manager/models.json
# lines 177/193 and 524/540; core/src/tools/mod.rs:75-97), which hides every tool but `exec` and `wait`
# (core/src/tools/spec_plan.rs:838-850; code-mode-protocol/src/lib.rs:54-55, description.rs:262-263). So exec_command
# is never a direct function_call, and the committed arm O rollouts (w-o7 to w-o14, by counts) hold 97 custom_tool_call
# `exec` records and their 97 custom_tool_call_output records, no function_call and no function_call_output; the
# function_call shapes of rounds 2 and 3 are removed. The rollout's CommandExecution (source unified_exec_startup) admits
# on its own argv again, a joined shape (16a), pinned to [/bin/bash, -lc, script] as all 108 committed ones are; an exec
# output admits only the verbatim copies of such a read's aggregated_output (16b). Each position names its record's
# type (NIT 2). A tty exec's `tty` argument is inside the exec script's text, read by no shape: its output is held by
# its CRLF bytes only (a known limit, as the stream's).
_O_SHELLS = ("/bin/bash",)
_O_TOOL = {"prefix": None, "opener": None}
# B24 (design section 2, F-RS-6): the stream's flag is -lc only, as every committed record's (452 of 452) and the door's
_O_WRAP = dict(_O_TOOL, kind="wrapped", arg=None, shells=_O_SHELLS, flags=("-lc",))
# Round 5 (glitch-26's B17-17 to B17-19 and NITs 2, 5 on review baef7c51): the CommandExecution's event is
# item_completed (all 108 committed ones are) and its argv a list (kind "argv"); each shape names its file kind; the
# exec output admits its own exec pair's reads, verbatim (gpt-6-luna, 32 of 36 committed) or as one JSON string literal
# whose decode is the read's output exactly (gpt-6.1-sol, 60 of 72); the 16 lossy middle truncations stay refused
# (lane-reports/B17-DESIGN-NOTE.md section 7).
_O_WRAP_LC = dict(_O_WRAP, kind="argv", flags=("-lc",))
_RESPONSE_ITEM = {"type": ("response_item",)}
# B20-6 (glitch-26, lane vendor-b20, 20 Oct 2026, on review 21fc1c7e's MINOR-1): a git read is admitted only where its
# folder is bound: the rollout CommandExecution's cwd (protocol/src/items.rs:265, a PathUri, serialized as its URL,
# utils/path-uri/src/lib.rs:689-695) exactly file:// + session_meta's cwd (protocol/src/protocol.rs:3171, the run tree;
# w-o14's rollout: '/tmp/run-b6ddc761' and 'file:///tmp/run-b6ddc761'). The stream's command_execution carries no cwd,
# so it binds nothing and admits no git read; the exec output's copy reads only its CommandExecution's admitted reads.
_O_GIT = {"cwd": "cwd", "prefix": "file://", "meta": ({"type": ("session_meta",)}, "payload.cwd")}
CODEX = (
    # the turn stream: a command_execution item, the call and its output in one object; `command` is
    # redact_secrets(shlex_join(argv)) (app-server-protocol/src/protocol/item_builders.rs:54-61, 96-143); item.started
    # and item.completed carry the same synthetic id (exec/src/event_processor_with_jsonl_output.rs:100-102, 162-181,
    # 327-341, 474-491), so every copy of an id must be the same call
    {"shape": "stream command_execution", "copies": "same", "tools": {"shell": _O_WRAP}, "result": None,
     "copy_of": None, "kinds": ("stream",),
     "call": {"match": {"type": "command_execution"},
              "at": ((("item",), {"type": ("item.started", "item.completed")}, None),),
              "id": "id", "name": {"value": "shell"}, "args": "command", "args_json": False,
              "text": (("aggregated_output",),)}},
    # the rollout: event_msg item_completed's CommandExecution item {id, command: argv, aggregated_output, source, ...}
    # (protocol/src/items.rs:243-281; core/src/tools/events.rs:561-589), the call and its output in one object
    {"shape": "rollout CommandExecution", "copies": "same", "tools": {"shell": _O_WRAP_LC}, "result": None,
     "copy_of": None, "kinds": ("session",), "git": _O_GIT,
     "call": {"match": {"type": "CommandExecution"},
              "at": ((("payload", "item"), {"type": ("event_msg",), "payload.type": ("item_completed",)}, None),),
              "id": "id", "name": {"value": "shell"}, "args": "command", "args_json": False,
              "text": (("aggregated_output",),)}},
    # the rollout: a custom_tool_call {name: "exec", call_id, input: the script} and its custom_tool_call_output
    # {call_id, output: [{type: input_text, text}]} (protocol/src/models.rs:1136-1171, 2096-2104, 2187-2265), the output
    # admitted only where it copies, verbatim or as one exact JSON string literal, a CommandExecution (shape 1) that
    # lies between this exec's call and output lines
    {"shape": "rollout exec output", "copies": "one", "copy_of": 1, "kinds": ("session",),
     "tools": {"exec": dict(_O_TOOL, kind="copy", arg=None, shells=None, flags=None)},
     "call": {"match": {"type": "custom_tool_call"}, "at": ((("payload",), _RESPONSE_ITEM, None),), "id": "call_id",
              "name": {"key": "name"}, "args": "input", "args_json": False, "text": ()},
     "result": {"match": {"type": "custom_tool_call_output"}, "at": ((("payload",), _RESPONSE_ITEM, None),),
                "id": "call_id", "name": None, "text": (("output",), ("output", "*", "text"))}},
)
