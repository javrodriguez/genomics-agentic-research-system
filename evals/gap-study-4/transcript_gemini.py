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
    the per-model entry's keys (total_tokens, input_tokens, output_tokens, cached, input); and the tool table
    GEMINI_TOOLS (Gemini CLI's built-in tool names and their argument keys).

THE CLOSED RULE. An event type, key, role, status, tool name or argument key that is not in these tables is refused
(`ShapeError`), never read on a guess: the first recorded stream that carries one stops at the reader, and the tables
grow only by a lane that cites the recording. In particular the web tools (`google_web_search`, `web_fetch`, which the
per-take settings exclude), `read_many_files` (it reads many paths, and the view's read carries one) and `save_memory`
are refused because no entry is pre-registered for them.

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
EVENT_KEYS = {
    INIT: (("type", "session_id", "model"), ("type", "timestamp", "session_id", "model")),
    MESSAGE: (("type", "role", "content"), ("type", "timestamp", "role", "content", "delta")),
    TOOL_USE: (("type", "tool_name", "tool_id", "parameters"), ("type", "timestamp", "tool_name", "tool_id",
                                                                "parameters")),
    TOOL_RESULT: (("type", "tool_id", "status"), ("type", "timestamp", "tool_id", "status", "output", "error")),
    ERROR: (("type", "message"), ("type", "timestamp", "severity", "message")),
    RESULT: (("type", "status"), ("type", "timestamp", "status", "error", "stats")),
}
EVENT_TYPES = tuple(EVENT_KEYS)

# ---- the closed words (NOT in D8; Q-w11b-1) ------------------------------------------------------------------------
USER, ASSISTANT = "user", "assistant"
ROLES = (USER, ASSISTANT)
SUCCESS, FAILED = "success", "error"
STATUSES = (SUCCESS, FAILED)
SEVERITIES = ("warning", "error")
ERROR_OBJECT_KEYS = ("type", "message")

# ---- result.stats (D8 section 1 and the per-harness table, D8:175) -------------------------------------------------
STATS_COUNTS = ("total_tokens", "input_tokens", "output_tokens", "cached", "input", "duration_ms", "tool_calls")
STATS_MODELS = "models"
STATS_KEYS = STATS_COUNTS + (STATS_MODELS,)
# One model's entry in stats.models (NOT in D8; Q-w11b-1).
MODEL_STATS_KEYS = ("total_tokens", "input_tokens", "output_tokens", "cached", "input")

# ---- the tool table (NOT in D8; Q-w11b-1): name -> (view kind, {raw key: view arg}, allowed raw keys) ---------------
GEMINI_TOOLS = {
    "run_shell_command": (tv.SHELL, {"command": "command", "is_background": "background"},
                          ("command", "description", "dir_path", "is_background")),
    "read_file": (tv.READ, {"file_path": "path"}, ("file_path", "offset", "limit")),
    "write_file": (tv.WRITE, {"file_path": "path"}, ("file_path", "content")),
    "replace": (tv.EDIT, {"file_path": "path"}, ("file_path", "old_string", "new_string", "expected_replacements",
                                                 "instruction")),
    "glob": (tv.SEARCH, {"pattern": "pattern", "dir_path": "path"},
             ("pattern", "dir_path", "case_sensitive", "respect_git_ignore", "respect_gemini_ignore")),
    "search_file_content": (tv.SEARCH, {"pattern": "pattern", "dir_path": "path"}, ("pattern", "dir_path", "include")),
    "list_directory": (tv.OTHER, {}, ("dir_path", "ignore", "file_filtering_options")),
    "write_todos": (tv.OTHER, {}, ("todos",)),
}


class ShapeError(tv.ViewError):
    """A Gemini CLI stream record outside the pre-registered tables: refused, never read on a guess."""


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
    if not isinstance(err, dict):
        raise ShapeError(f"{what}: its error is not an object")
    _keys(f"{what}.error", err, ERROR_OBJECT_KEYS, ERROR_OBJECT_KEYS)


def check_stats(stats) -> None:
    """result.stats against D8's keys: every count present and a count (missing is refused, never read as 0), no key
    off the table, and stats.models an object of model id -> its entry, each entry's keys and counts as above."""
    if not isinstance(stats, dict):
        raise ShapeError("result.stats is not an object")
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
        return tv.map_tool(GEMINI_TOOLS, rec.get("tool_name"), rec.get("parameters"))
    except tv.ViewError as e:
        raise ShapeError(f"tool_use: {e}") from None


def check_record(rec) -> str:
    """The event type of one decoded stream record, after checking it against the tables.

    Refuses (ShapeError) a record that is not an object, an event type with no entry, any key, required or extra, off
    its entry, a role, status or severity off its words, a message whose content is not a string, a tool id that is
    not a non-empty string, a tool name or argument key off GEMINI_TOOLS, an error object off its keys, and
    result.stats off check_stats."""
    if not isinstance(rec, dict):
        raise ShapeError("a record that is not an object")
    t = rec.get("type")
    if t not in EVENT_KEYS:
        raise ShapeError(f"unknown event type: {t!r}")
    _keys(f"event {t}", rec, *EVENT_KEYS[t])
    if t == MESSAGE and rec["role"] not in ROLES:
        raise ShapeError(f"message: role with no entry: {rec['role']!r}")
    if t == MESSAGE and not isinstance(rec["content"], str):
        raise ShapeError("message: its content is not a string")
    if t in (TOOL_USE, TOOL_RESULT) and (not isinstance(rec["tool_id"], str) or not rec["tool_id"]):
        raise ShapeError(f"{t}: its tool_id is not a non-empty string")
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
    """The harness's own error words on an error event or a failed result (None when not a string), never the
    agent's."""
    t = rec.get("type")
    if t == ERROR:
        words = rec.get("message")
    elif t == RESULT:
        words = (rec.get("error") or {}).get("message")
    else:
        return None
    return words if isinstance(words, str) else None


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
            return [tv.RawItem(t, tv.TOOL_CALL, tool=kind, args=args, ref=rec["tool_id"])]
        if t == TOOL_RESULT:
            out = rec.get("output")
            text = out if isinstance(out, str) else tv._joined(rec.get("error"))
            return [tv.RawItem(t, tv.TOOL_RESULT, text=text, ref=rec["tool_id"])]
        return [tv.RawItem(t, tv.HARNESS, text=tv._joined({k: v for k, v in rec.items() if k != "type"}))]
