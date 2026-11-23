#!/usr/bin/env python3
"""Gemini CLI's `gemini -p ... -o stream-json` stream: its pre-registered shapes, and a parser into the transcript view
(arm G).

Lane w11b-gemini-adapter (Gap Study round 4; next-slices-plan-2026-10-12 section 2; D8 section 1). This module holds
the closed tables of what a Gemini CLI stream may carry, the one record check both readers use (`check_record`), and
`GeminiParser`, shaped like transcript_view's ClaudeCodeSessionParser: it turns one stream line into
`transcript_view.RawItem`s in the view's closed vocabulary. It is NOT registered in `transcript_view.PARSERS`: a later
seam slice registers it, once both non-Claude adapters land.

WHERE THE SHAPES COME FROM. No Gemini CLI stream has been recorded (none can be before J3's keys, D8:131-133), so every
table below is the documented shape, and `gemini_adapter.SHAPES_SOURCE` says "documented" until a stream recorded at
the pinned version re-tests it (ruling Q-3, glitch-2f, 12 Oct 2026). Two grades of source, kept apart:

  D8 section 1 (read from the vendor's documentation and its source's `types.ts` by glitch-f3's research, 7 Oct 2026):
    the event types   init, message, tool_use, tool_result, error, result
    init              session_id, model
    result            status, error (its type), stats: total_tokens, input_tokens, output_tokens, cached, input,
                      duration_ms, tool_calls, and the per-model breakdown (`stats.models`, keyed by model id)
  NOT in D8 (this lane's reading of Gemini CLI's stream-json types, unverified in this lane, which has no network; the
  first recorded stream confirms or replaces each, Q-w11b-1):
    `timestamp` on every event; message role (user | assistant), content and the optional `delta`; tool_use
    tool_name, tool_id and parameters; tool_result tool_id, status (success | error), output and error; error
    severity and message; the error object's keys (type, message); result status's two words (success | error);
    the per-model entry's keys (total_tokens, input_tokens, output_tokens, cached, input).
  READ FROM THE PINNED PACKAGE (lane vendor-admission round 18 B12, glitch-26's ruling of 18 Oct 2026, after practice
  walk w-g3 held on update_topic): the tool table GEMINI_TOOLS, from Gemini CLI 0.64.0's own tool registry, each entry
  with its source lines and file sha256 in gemini_tool_sources.py (read statically, never run or imported).

THE CLOSED RULE. An event type, key, role, status, tool name or argument key that is not in these tables is refused
(`ShapeError`), never read on a guess: the first recorded stream that carries one stops at the reader, and the tables
grow only by a lane that cites the recording or the pinned package. In particular the web tools (`google_web_search`,
`web_fetch`, which the per-take settings exclude, D8 section 3), the tools the pinned package defines but never offers a
headless arm G model (gemini_tool_sources.py names each) and names it does not define (`save_memory`) are refused because
no entry is pre-registered for them. OPEN_INPUT (at the end of this file) is the one exception, by ruling R-B16-2.

THE VIEW MAPPING (the brief's, item 2):
    message role user        -> operator (each one starts the next turn of the view)
    message role assistant   -> agent-text
    tool_use                 -> tool-call, its tool kind from GEMINI_TOOLS
    tool_result              -> tool-result of the same call (paired by tool_id)
    init, error, result      -> harness
A message's `delta` chunks are each one agent-text event, as the stream holds them.

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import transcript_view as tv  # noqa: E402

# ---- the event types (D8 section 1) and each one's keys: (required, allowed) ---------------------------------------
INIT = "init"
MESSAGE = "message"
TOOL_USE = "tool_use"
TOOL_RESULT = "tool_result"
ERROR = "error"
RESULT = "result"
# `type` is allowed on every event and required by the lookup itself (a record without it is an unknown event).
EVENT_KEYS = {
    INIT: (("session_id", "model"), ("type", "timestamp", "session_id", "model")),
    MESSAGE: (("role", "content"), ("type", "timestamp", "role", "content", "delta")),
    TOOL_USE: (("tool_name", "tool_id", "parameters"), ("type", "timestamp", "tool_name", "tool_id", "parameters")),
    TOOL_RESULT: (("tool_id", "status"), ("type", "timestamp", "tool_id", "status", "output", "error")),
    ERROR: (("message",), ("type", "timestamp", "severity", "message")),
    RESULT: (("status",), ("type", "timestamp", "status", "error", "stats")),
}
EVENT_TYPES = tuple(EVENT_KEYS)

# ---- the closed words (NOT in D8; Q-w11b-1) ------------------------------------------------------------------------
USER, ASSISTANT = "user", "assistant"
ROLES = (USER, ASSISTANT)
SUCCESS, FAILED = "success", "error"
STATUSES = (SUCCESS, FAILED)
SEVERITIES = ("warning", "error")
# Each key's value type, exact (`type(v) is`, so a bool is never an int and a subclass never passes): W11B-R1-4.
VALUE_TYPES = {"type": str, "timestamp": str, "session_id": str, "model": str, "role": str, "content": str,
               "delta": bool, "tool_name": str, "tool_id": str, "parameters": dict, "status": str, "output": str,
               "error": dict, "severity": str, "message": str, "stats": dict}
ERROR_OBJECT_TYPES = {"type": str, "message": str}
ERROR_OBJECT_KEYS = ("type", "message")

# ---- result.stats (D8 section 1 and the per-harness table, D8:175) -------------------------------------------------
STATS_COUNTS = ("total_tokens", "input_tokens", "output_tokens", "cached", "input", "duration_ms", "tool_calls")
STATS_MODELS = "models"
STATS_KEYS = STATS_COUNTS + (STATS_MODELS,)
# One model's entry in stats.models (NOT in D8; Q-w11b-1).
MODEL_STATS_KEYS = ("total_tokens", "input_tokens", "output_tokens", "cached", "input")

# ---- the tool table: read from the pinned Gemini CLI 0.64.0's tool registry (round 18 B12) -------------------------
# name -> (view kind, {raw key: view arg}, allowed raw keys). The names are every tool the pinned package's main registry
# (Config.createToolRegistry, bundle/chunk-NR7L3FXV.js lines 382782-382852) can offer a headless `-o stream-json` arm G
# run under take_config's settings, and the legacy alias the registry resolves (search_file_content); the stream's
# tool_name is the model's own call name (bundle/gemini-Q2GRYIAK.js line 12226). The keys are each tool's declared
# parameters for the gemini-3 tool family (both arm G models resolve to it; the default-legacy family declares the same
# keys), plus `wait_for_previous` on the tools that keep the base getSchema (bundle/chunk-NR7L3FXV.js lines 274269-274305).
# Each view kind is one of the view's existing kinds, from what the tool does in the pinned code (gemini_tool_sources).
_GREP_KEYS = ("pattern", "dir_path", "include_pattern", "exclude_pattern", "names_only", "case_sensitive",
              "fixed_strings", "context", "after", "before", "no_ignore", "max_matches_per_file", "total_max_matches")
GEMINI_TOOLS = {
    "run_shell_command": (tv.SHELL, {"command": "command", "is_background": "background"},
                          ("command", "description", "dir_path", "is_background", "delay_ms")),
    "read_file": (tv.READ, {"file_path": "path"}, ("file_path", "start_line", "end_line")),
    "write_file": (tv.WRITE, {"file_path": "path"}, ("file_path", "content")),
    "replace": (tv.EDIT, {"file_path": "path"}, ("file_path", "instruction", "old_string", "new_string",
                                                 "allow_multiple")),
    "glob": (tv.SEARCH, {"pattern": "pattern", "dir_path": "path"},
             ("pattern", "dir_path", "case_sensitive", "respect_git_ignore", "respect_gemini_ignore")),
    "grep_search": (tv.SEARCH, {"pattern": "pattern", "dir_path": "path"}, _GREP_KEYS),
    "search_file_content": (tv.SEARCH, {"pattern": "pattern", "dir_path": "path"}, _GREP_KEYS),
    "list_directory": (tv.OTHER, {}, ("dir_path", "ignore", "file_filtering_options")),
    "write_todos": (tv.OTHER, {}, ("todos",)),
    "update_topic": (tv.OTHER, {}, ("title", "summary", "strategic_intent", "wait_for_previous")),
    "activate_skill": (tv.OTHER, {}, ("name",)),
    "enter_plan_mode": (tv.OTHER, {}, ("reason",)),
    "exit_plan_mode": (tv.OTHER, {}, ("plan_filename",)),
    "list_background_processes": (tv.OTHER, {}, ("wait_for_previous",)),
    "read_background_output": (tv.OTHER, {}, ("pid", "lines", "delay_ms", "wait_for_previous")),
    "invoke_agent": (tv.DELEGATE, {}, ("agent_name", "prompt", "wait_for_previous")),
}
# Each entry's source lines, the pinned files' sha256 and the reading of each class: gemini_tool_sources.SOURCES.


class ShapeError(tv.ViewError):
    """A Gemini CLI stream record outside the pre-registered tables: refused, never read on a guess."""


def _types(what: str, rec: dict, table: dict) -> None:
    bad = sorted(k for k in rec if type(rec[k]) is not table[k])
    if bad:
        raise ShapeError(f"{what}: value(s) off their type: {bad}")


def _keys(what: str, rec: dict, required, allowed) -> None:
    missing = [k for k in required if k not in rec]
    if missing:
        raise ShapeError(f"{what}: required key(s) missing: {missing}")
    unknown = sorted(set(rec) - set(allowed))
    if unknown:
        raise ShapeError(f"{what}: key(s) with no entry in the tables: {unknown}")


def count(v) -> bool:
    """A token, time or call count as recorded: an int that is not a bool, never negative."""
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _error_object(what: str, err) -> None:
    _keys(f"{what}.error", err, ERROR_OBJECT_KEYS, ERROR_OBJECT_KEYS)
    _types(f"{what}.error", err, ERROR_OBJECT_TYPES)


def check_stats(stats) -> None:
    """result.stats against D8's keys: every count present and a count (missing is refused, never read as 0), no key
    off the table, and stats.models an object of model id -> its entry, each entry's keys and counts as above."""
    _keys("result.stats", stats, STATS_KEYS, STATS_KEYS)
    bad = [k for k in STATS_COUNTS if not count(stats[k])]
    if bad:
        raise ShapeError(f"result.stats: not a count: {bad}")
    models = stats[STATS_MODELS]
    if not isinstance(models, dict):
        raise ShapeError("result.stats.models is not an object")
    for model, entry in models.items():
        if not isinstance(entry, dict):
            raise ShapeError(f"result.stats.models[{model!r}] is not an object")
        _keys(f"result.stats.models[{model!r}]", entry, MODEL_STATS_KEYS, MODEL_STATS_KEYS)
        bad = [k for k in MODEL_STATS_KEYS if not count(entry[k])]
        if bad:
            raise ShapeError(f"result.stats.models[{model!r}]: not a count: {bad}")


def tool_kind(rec: dict) -> tuple:
    """(view kind, view args) of a tool_use by GEMINI_TOOLS: a tool name or argument key with no entry is refused."""
    try:
        return tv.map_tool(GEMINI_TOOLS, rec["tool_name"], _declared(rec))
    except tv.ViewError as e:
        raise ShapeError(f"tool_use: {e}") from None


def check_record(rec) -> str:
    """The event type of one decoded stream record, after checking it against the tables.

    Refuses (ShapeError) a record that is not an object, an event type with no entry, any key, required or extra, off
    its entry, a value off its VALUE_TYPES type, a role, status or severity off its words, an empty tool id, a tool
    name or argument key off GEMINI_TOOLS, an error object off its keys or types, result.stats off check_stats, and a
    successful result with no stats."""
    if not isinstance(rec, dict):
        raise ShapeError("a record that is not an object")
    t = rec.get("type")
    if t not in EVENT_KEYS:
        raise ShapeError(f"unknown event type: {t!r}")
    _keys(f"event {t}", rec, *EVENT_KEYS[t])
    _types(f"event {t}", rec, VALUE_TYPES)
    if t == MESSAGE and rec["role"] not in ROLES:
        raise ShapeError(f"message: role with no entry: {rec['role']!r}")
    if t in (TOOL_USE, TOOL_RESULT) and not rec["tool_id"]:
        raise ShapeError(f"{t}: its tool_id is empty")
    if t == TOOL_USE:
        tool_kind(rec)
    if t in (TOOL_RESULT, RESULT) and rec["status"] not in STATUSES:
        raise ShapeError(f"{t}: status with no entry: {rec['status']!r}")
    # EVENT_KEYS allows `severity` on an error event only, `error` on a tool_result or result only, and `stats` on a
    # result only, so each check below needs no event-type clause of its own.
    if "severity" in rec and rec["severity"] not in SEVERITIES:
        raise ShapeError(f"error: severity with no entry: {rec['severity']!r}")
    if "error" in rec:
        _error_object(t, rec["error"])
    if "stats" in rec:
        check_stats(rec["stats"])
    elif t == RESULT and rec["status"] == SUCCESS:
        raise ShapeError("result: a successful result carries no stats (usage unmeasured is refused, W11B-R1-2)")
    return t


def decode(line: str) -> dict:
    """One stream line decoded and checked (ShapeError on a line that is not a JSON object in the tables)."""
    try:
        rec = json.loads(line)
    except ValueError:
        raise ShapeError("a line that is not JSON") from None
    check_record(rec)
    return rec


def error_text(rec: dict):
    """The harness's own error words on a checked error event or failed result (None when a result carries no error
    object, or for any other record), never the agent's."""
    t = rec.get("type")
    if t == ERROR:
        return rec["message"]
    if t == RESULT and "error" in rec:
        return rec["error"]["message"]
    return None


class GeminiParser:
    """Gemini CLI's host-captured `-o stream-json` stream, one JSON record per line."""

    event_types = EVENT_TYPES
    tools = GEMINI_TOOLS

    def items(self, line: str) -> list:
        rec = decode(line)
        t = rec["type"]
        if t == MESSAGE:
            kind = tv.OPERATOR if rec["role"] == USER else tv.AGENT_TEXT
            return [tv.RawItem(t, kind, text=rec["content"])]
        if t == TOOL_USE:
            kind, args = tool_kind(rec)
            return [_call_item(t, kind, args, rec)]
        if t == TOOL_RESULT:
            out = rec.get("output")
            text = out if isinstance(out, str) else tv._joined(rec.get("error"))
            return [tv.RawItem(t, tv.TOOL_RESULT, text=text, ref=rec["tool_id"])]
        return [tv.RawItem(t, tv.HARNESS, text=tv._joined({k: v for k, v in rec.items() if k != "type"}))]


# ---- undeclared argument keys, read as named, ignored input (lane vendor-b16 round 2, glitch-26's ruling R-B16-2) ---
# NAMED EXCEPTION (ruling R-B16-2): transcript_gemini.py is a READER_SOURCES file (native_reader_registration). No
# Gemini reader acceptance record exists, so no accepted bytes move; recorded as B12's was, here, in the lane file and
# the commit message. The Gemini practice walk was held on "tool 'grep_search': argument keys with no entry:
# ['file_path']"; the pinned Gemini CLI 0.64.0 ran that call over the working directory and its stream recorded the
# model's parameters with a success result (lane-reports/B16-DESIGN-NOTE.md sections 2 and 4).
# name -> (its schema closes its properties, the raw keys the pinned run reads off the call's arguments). For a tool
# here, a raw key outside its GEMINI_TOOLS entry's allowed keys is not refused when the schema leaves its properties
# open (Ajv passes the key) and the key is not one the run reads: it is dropped from what is mapped, so the view's args
# are what ran, and it is named on the view item (undeclared_args). Each entry is cited in
# gemini_tool_sources.OPEN_INPUT. Still refused: an unknown tool name, a declared key off its type, a tool with no
# entry here or whose schema closes its properties, and a key the run reads. The read keys are both grep invocations'
# (GrepTool's and RipGrepTool's, either of which serves grep_search) and wait_for_previous, which the scheduler reads
# off every call.
import dataclasses  # noqa: E402  (kept here so the lines above, which the generated sweep keys, do not move)

_GREP_READS = _GREP_KEYS + ("wait_for_previous",)
OPEN_INPUT = {
    "grep_search": (False, _GREP_READS),
    "search_file_content": (False, _GREP_READS),
}


def ignored_args(rec: dict) -> tuple:
    """The raw argument keys of a checked tool_use that OPEN_INPUT reads as named, ignored input, in the record's
    order; () when there are none or when any undeclared key may not be ignored (the call is then mapped whole, and
    map_tool refuses it)."""
    entry = OPEN_INPUT.get(rec["tool_name"])
    if entry is None or entry[0] is not False:
        return ()
    extra = [k for k in rec["parameters"] if k not in GEMINI_TOOLS[rec["tool_name"]][2]]
    if set(extra) & set(entry[1]):
        return ()
    return tuple(extra)


def _declared(rec: dict) -> dict:
    """The tool_use's parameters without the keys ignored_args names."""
    ignored = ignored_args(rec)
    return {k: v for k, v in rec["parameters"].items() if k not in ignored}


@dataclasses.dataclass(frozen=True, kw_only=True)
class CallItem(tv.RawItem):
    """A tool call's view item that names the undeclared argument keys read as ignored input (OPEN_INPUT)."""
    undeclared_args: tuple


def _call_item(t: str, kind: str, args: dict, rec: dict):
    """The tool call's view item: a CallItem naming the ignored keys when there are any, else the plain RawItem."""
    ignored = ignored_args(rec)
    if not ignored:
        return tv.RawItem(t, tv.TOOL_CALL, tool=kind, args=args, ref=rec["tool_id"])
    return CallItem(t, tv.TOOL_CALL, tool=kind, args=args, ref=rec["tool_id"], undeclared_args=ignored)
