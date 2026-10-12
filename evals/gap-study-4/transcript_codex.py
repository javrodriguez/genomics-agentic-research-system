#!/usr/bin/env python3
"""Codex CLI's `codex exec --json` stream: its pre-registered shapes, and a parser into the transcript view (arm O).

Lane w11a-codex-adapter (Gap Study round 4; next-slices-plan-2026-10-12 section 2; D8 section 1). This module holds
the closed tables of what a Codex exec stream may carry, the one record check both readers use (`check_record`), and
`CodexParser`, shaped like transcript_view's ClaudeCodeSessionParser: it turns one stream line into
`transcript_view.RawItem`s in the view's closed vocabulary. It is NOT registered in `transcript_view.PARSERS`: a later
seam slice registers it, once both non-Claude adapters land.

WHERE THE SHAPES COME FROM. No Codex stream has been recorded (none can be before J3's keys, D8:113-115), so every
table below is the documented shape, and `codex_adapter.SHAPES_SOURCE` says "documented" until a stream recorded at
the pinned version re-tests it (ruling Q-3, glitch-2f, 12 Oct 2026). Two grades of source, kept apart:

  D8 section 1 (read from the vendor's documentation by glitch-f3's research, 7 Oct 2026):
    the event types   thread.started, turn.started, item.started, item.completed, turn.completed, turn.failed, error
    the item types    agent_message, reasoning, command_execution, file_change, mcp_tool_call
    the usage keys    turn.completed.usage: input_tokens, cached_input_tokens, output_tokens, reasoning_output_tokens
  NOT in D8 (this lane's reading of Codex's exec event schema, unverified in this lane, which has no network; the
  docs read of plan item 2 or the first recorded stream confirms or replaces each, Q-w11a-1):
    thread.started.thread_id; turn.failed.error.message; error.message; every item's `id` and `type`;
    agent_message.text and reasoning.text; command_execution command, aggregated_output, exit_code, status;
    file_change changes[] of {path, kind} and status, with kind add or update (delete is refused, Q-w11a-3);
    mcp_tool_call server, tool, arguments, result, error, status; which item types an item.started may carry.

THE CLOSED RULE. A record type, item type or key that is not in these tables is refused (`ShapeError`), never read
on a guess: the first recorded stream that carries one stops at the reader, and the tables grow only by a lane that
cites the recording. In particular `item.updated` and the item types `web_search`, `todo_list` and `error`, which a
real stream may carry, are refused here because D8 does not name them.

THE VIEW MAPPING (the brief's, item 2):
    agent_message      item.completed -> agent-text
    reasoning          item.completed -> agent-reasoning
    command_execution  item.started -> tool-call shell {command}; item.completed -> its tool-result (aggregated_output)
    mcp_tool_call      item.started -> tool-call other {}; item.completed -> its tool-result
    file_change        item.completed -> one tool-call per change (add -> write, update -> edit, {path}) and its result
    thread.started, turn.started, turn.completed, turn.failed, error -> harness
The stream carries no operator line (the operator's line is exec's argument, not an event), so a view of a Codex
stream alone numbers every event turn 0: how the seam slice puts the ledger's sent lines in is Q-w11a-2.

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
THREAD_STARTED = "thread.started"
TURN_STARTED = "turn.started"
ITEM_STARTED = "item.started"
ITEM_COMPLETED = "item.completed"
TURN_COMPLETED = "turn.completed"
TURN_FAILED = "turn.failed"
ERROR = "error"
EVENT_KEYS = {
    THREAD_STARTED: (("type", "thread_id"), ("type", "thread_id")),
    TURN_STARTED: (("type",), ("type",)),
    ITEM_STARTED: (("type", "item"), ("type", "item")),
    ITEM_COMPLETED: (("type", "item"), ("type", "item")),
    TURN_COMPLETED: (("type", "usage"), ("type", "usage")),
    TURN_FAILED: (("type", "error"), ("type", "error")),
    ERROR: (("type", "message"), ("type", "message")),
}
EVENT_TYPES = tuple(EVENT_KEYS)
ITEM_EVENTS = (ITEM_STARTED, ITEM_COMPLETED)
# The two events whose text is the harness's own error words (never the agent's).
ERROR_EVENTS = (TURN_FAILED, ERROR)
TURN_FAILED_ERROR_KEYS = ("message",)

# ---- the item types (D8 section 1) and each one's keys: (required, allowed) ----------------------------------------
AGENT_MESSAGE = "agent_message"
REASONING = "reasoning"
COMMAND_EXECUTION = "command_execution"
FILE_CHANGE = "file_change"
MCP_TOOL_CALL = "mcp_tool_call"
ITEM_KEYS = {
    AGENT_MESSAGE: (("id", "type", "text"), ("id", "type", "text")),
    REASONING: (("id", "type", "text"), ("id", "type", "text")),
    COMMAND_EXECUTION: (("id", "type", "command"), ("id", "type", "command", "aggregated_output", "exit_code",
                                                    "status")),
    FILE_CHANGE: (("id", "type", "changes"), ("id", "type", "changes", "status")),
    MCP_TOOL_CALL: (("id", "type", "server", "tool"), ("id", "type", "server", "tool", "arguments", "result",
                                                       "error", "status")),
}
ITEM_TYPES = tuple(ITEM_KEYS)
# The item types an item.started may carry: the two whose call is open while it runs.
STARTED_ITEM_TYPES = (COMMAND_EXECUTION, MCP_TOOL_CALL)
# The item types that are the agent's completed output (text or a tool call): the seam's agent_output rule.
OUTPUT_ITEM_TYPES = (AGENT_MESSAGE, COMMAND_EXECUTION, FILE_CHANGE, MCP_TOOL_CALL)
TOOL_ITEM_TYPES = (COMMAND_EXECUTION, FILE_CHANGE, MCP_TOOL_CALL)

# ---- turn.completed.usage (D8 section 1 and the per-harness table, D8:175) -----------------------------------------
USAGE_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")

# ---- file_change's changes -----------------------------------------------------------------------------------------
CHANGE_KEYS = ("path", "kind")
CHANGE_KINDS = {"add": tv.WRITE, "update": tv.EDIT}

# ---- each key's value type (W11A-R1-8); a key not listed here (mcp_tool_call's arguments, result, error) is untyped,
# its shape not documented. A bool is never an int.
_NONE = type(None)
EVENT_VALUE_TYPES = {"type": (str,), "thread_id": (str,), "item": (dict,), "usage": (dict,), "error": (dict,),
                     "message": (str,)}
ITEM_VALUE_TYPES = {"id": (str,), "type": (str,), "text": (str,), "command": (str,), "aggregated_output": (str,),
                    "exit_code": (int, _NONE), "status": (str,), "changes": (list,), "server": (str,), "tool": (str,)}
CHANGE_VALUE_TYPES = {"path": (str,), "kind": (str,)}


class ShapeError(tv.ViewError):
    """A Codex stream record outside the pre-registered tables: refused, never read on a guess."""


def _keys(what: str, rec: dict, required, allowed) -> None:
    missing = [k for k in required if k not in rec]
    if missing:
        raise ShapeError(f"{what}: required key(s) missing: {missing}")
    unknown = sorted(set(rec) - set(allowed))
    if unknown:
        raise ShapeError(f"{what}: key(s) with no entry in the tables: {unknown}")


def _types(what: str, rec: dict, table: dict) -> None:
    for k, v in rec.items():
        if k in table and (not isinstance(v, table[k]) or (isinstance(v, bool) and bool not in table[k])):
            raise ShapeError(f"{what}: {k} is not {' or '.join(t.__name__ for t in table[k])}")


def check_record(rec) -> tuple:
    """(event type, item type or None) of one decoded stream record, after checking it against the tables.

    Refuses (ShapeError) a record that is not an object, an event type with no entry, an item type with no entry, an
    item type an item.started may not carry, any key, required or extra, off its entry, and any value off its type
    (a file_change's changes too: a non-empty list of {path, kind} with kind in CHANGE_KINDS)."""
    if not isinstance(rec, dict):
        raise ShapeError("a record that is not an object")
    t = rec.get("type")
    if t not in EVENT_KEYS:
        raise ShapeError(f"unknown event type: {t!r}")
    _keys(f"event {t}", rec, *EVENT_KEYS[t])
    _types(f"event {t}", rec, EVENT_VALUE_TYPES)
    if t == TURN_FAILED:
        _keys("turn.failed.error", rec["error"], TURN_FAILED_ERROR_KEYS, TURN_FAILED_ERROR_KEYS)
        _types("turn.failed.error", rec["error"], EVENT_VALUE_TYPES)
    if t not in ITEM_EVENTS:
        return t, None
    item = rec["item"]
    it = item.get("type")
    if it not in ITEM_KEYS:
        raise ShapeError(f"unknown item type: {it!r}")
    _keys(f"item {it}", item, *ITEM_KEYS[it])
    _types(f"item {it}", item, ITEM_VALUE_TYPES)
    if not item["id"]:
        raise ShapeError(f"item {it}: its id is empty")
    if t == ITEM_STARTED and it not in STARTED_ITEM_TYPES:
        raise ShapeError(f"item.started carrying {it!r}: only {STARTED_ITEM_TYPES} are pre-registered there")
    if it == FILE_CHANGE:
        if not item["changes"]:
            raise ShapeError(f"item {it}: its changes are empty")
        for ch in item["changes"]:
            if not isinstance(ch, dict):
                raise ShapeError(f"item {it}: a change that is not an object")
            _keys(f"item {it} change", ch, CHANGE_KEYS, CHANGE_KEYS)
            _types(f"item {it} change", ch, CHANGE_VALUE_TYPES)
            if ch["kind"] not in CHANGE_KINDS:
                raise ShapeError(f"item {it}: change kind with no entry: {ch['kind']!r}")
    return t, it


def decode(line: str) -> dict:
    """One stream line decoded and checked (ShapeError on a line that is not a JSON object in the tables)."""
    try:
        rec = json.loads(line)
    except ValueError:
        raise ShapeError("a line that is not JSON") from None
    check_record(rec)
    return rec


class CodexParser:
    """Codex's host-captured `codex exec --json` stream, one JSON record per line (never the rollout file)."""

    event_types = EVENT_TYPES
    item_types = ITEM_TYPES

    def items(self, line: str) -> list:
        rec = decode(line)
        t, it = check_record(rec)      # every key and value below has passed the tables
        if t not in ITEM_EVENTS:
            return [tv.RawItem(t, tv.HARNESS, text=tv._joined({k: v for k, v in rec.items() if k != "type"}))]
        item = rec["item"]
        raw = f"{t}:{it}"
        if t == ITEM_STARTED:
            if it == COMMAND_EXECUTION:
                kind, args = tv.SHELL, {"command": item["command"], "background": False}
            else:
                kind, args = tv.OTHER, {}
            return [tv.RawItem(raw, tv.TOOL_CALL, tool=kind, args=args, ref=item["id"])]
        if it == AGENT_MESSAGE:
            return [tv.RawItem(raw, tv.AGENT_TEXT, text=item["text"])]
        if it == REASONING:
            return [tv.RawItem(raw, tv.AGENT_REASONING, text=item["text"])]
        if it == COMMAND_EXECUTION:
            return [tv.RawItem(raw, tv.TOOL_RESULT, text=item.get("aggregated_output"), ref=item["id"])]
        if it == MCP_TOOL_CALL:
            return [tv.RawItem(raw, tv.TOOL_RESULT, text=tv._joined(item.get("result")), ref=item["id"])]
        return self._file_change(item, raw)

    @staticmethod
    def _file_change(item: dict, raw: str) -> list:
        out = []
        for i, ch in enumerate(item["changes"]):
            ref = f"{item['id']}#{i}"
            out.append(tv.RawItem(raw, tv.TOOL_CALL, tool=CHANGE_KINDS[ch["kind"]], args={"path": ch["path"]}, ref=ref))
            out.append(tv.RawItem(raw, tv.TOOL_RESULT, text=item.get("status"), ref=ref))
        return out
