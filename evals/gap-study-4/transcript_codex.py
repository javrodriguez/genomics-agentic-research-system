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
  READ FROM THE PINNED SOURCE (lane vendor-b14 B15, practice walk w-o3; codex_usage_sources records each line):
    the usage keys    D8's four and cache_write_input_tokens, exactly the fields of struct Usage at openai/codex
                      rust-v0.162.1 (092d3acd), codex-rs/exec/src/exec_events.rs:59-73, all five always serialized
  NOT in D8 (this lane's reading of Codex's exec event schema, unverified in this lane, which has no network; the
  docs read of plan item 2 or the first recorded stream confirms or replaces each, Q-w11a-1):
    thread.started.thread_id; turn.failed.error.message; error.message; every item's `id` and `type`;
    agent_message.text and reasoning.text; command_execution command, aggregated_output, exit_code, status;
    file_change changes[] of {path, kind} and status (its kinds: the pinned-source block below);
    mcp_tool_call server, tool, arguments, result, error, status.
  READ FROM THE PINNED SOURCE (lane vendor-b22, glitch-26's ruling B22-6, Tue 20 Oct 2026; GPT walk w-o38, held on a
  file_change item.started; lane-reports/vendor-b22-DESIGN.md):
    item.started      exec prints every item map_item_with_id maps but agent_message and reasoning
                      (exec/src/event_processor_with_jsonl_output.rs:343-351, 477-482); of those the tables admit
                      command_execution, mcp_tool_call and file_change. A file_change is started at apply_patch's
                      Begin stage with no status (core/src/tools/events.rs:241-263), printed as "in_progress"
                      (app-server-protocol/src/protocol/v2/item.rs:1028-1035), so a started file_change is admitted
                      only with that status. w-o38's turn 1 holds two, each followed by its item.completed.
  READ FROM THE PINNED SOURCE (lane pf1-codex-fcdelete, glitch-45's brief of Tue 27 Oct 2026; GPT walk w-o76, held
  on a file_change change of kind delete):
    change kinds      add, delete and update, exactly exec's PatchChangeKind (exec/src/exec_events.rs:192-198),
                      onto which exec maps every patch change (exec/src/event_processor_with_jsonl_output.rs:187-196).
                      Q-w11a-3 refused delete until a recorded stream showed one (glitch-26's ruling Q4, 20 Oct:
                      "a follow-up lane rules what a deleted file is in the view, after a recorded rollout"); w-o76's
                      turn 1 deletes a PLAN.md through the patch tool and adds it again (lines 17-20).

THE CLOSED RULE. A record type, item type or key that is not in these tables is refused (`ShapeError`), never read
on a guess: the first recorded stream that carries one stops at the reader, and the tables grow only by a lane that
cites the recording. In particular `item.updated` and the item types `web_search`, `todo_list` and `error`, which a
real stream may carry, are refused here because D8 does not name them.

THE VIEW MAPPING (the brief's, item 2):
    agent_message      item.completed -> agent-text
    reasoning          item.completed -> agent-reasoning
    command_execution  item.started -> tool-call shell {command}; item.completed -> its tool-result (aggregated_output)
    mcp_tool_call      item.started -> tool-call other {}; item.completed -> its tool-result
    file_change        item.started -> one tool-call per change (add -> write, update -> edit, delete -> write,
                       {path}, ref <id>#<i>; a delete changes that path, so every grader that reads a write or an
                       edit of a path reads a delete of it, Q-w11a-3's proposed mapping);
                       item.completed -> each change's result (its status). Lane vendor-b23 (glitch-26's ruling Q1,
                       option C, Tue 20 Oct 2026; replaces B22-6's "started -> nothing"): the pinned handler emits
                       Begin before it runs the patch and Finish after it, both with the same changes
                       (core/src/tools/handlers/apply_patch.rs:544, 572; core/src/tools/events.rs:241-263, 599-615), and
                       at turn end exec completes each unfinished started item held in the turn's items
                       (reconcile_unfinished_started_items, exec/src/event_processor_with_jsonl_output.rs:370-385,
                       524), a patch among them, so a started patch with no completion is left only by a killed exec
                       (a take's timeout): it stays an edit call with no result. That does not hold for every command:
                       a unified-exec process that outlives its turn leaves its start with no completion in a completed
                       stream (pf1-codex-turnitem, w-o69's turn-4.jsonl line 9; codex_native's docstring). A completed
                       file_change with no started record in its stream (exec gives it a fresh id, :337-341; the D8
                       fixtures hold them) keeps its call and its result at the completion. The parser keeps one map
                       per stream, reset at thread.started: a second start of one id, or a completion whose changes
                       are not its start's, is refused.
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
# The item types an item.started may carry: the calls open while they run (B22-6 adds file_change, read from the
# pinned source; see the docstring), and the one status a started file_change carries.
STARTED_ITEM_TYPES = (COMMAND_EXECUTION, FILE_CHANGE, MCP_TOOL_CALL)
STARTED_FILE_CHANGE_STATUS = "in_progress"
# The item types that are the agent's completed output (text or a tool call): the seam's agent_output rule.
OUTPUT_ITEM_TYPES = (AGENT_MESSAGE, COMMAND_EXECUTION, FILE_CHANGE, MCP_TOOL_CALL)
TOOL_ITEM_TYPES = (COMMAND_EXECUTION, FILE_CHANGE, MCP_TOOL_CALL)

# ---- turn.completed.usage (D8 section 1 and the per-harness table, D8:175; B15, the pinned struct) -----------------
# exec_events.rs:63, :65, :68, :70 and :72 in that order. No field is skip_serializing_if, and the serde(default) on
# cache_write_input_tokens (:67) is read only when deserializing, so exec prints all five on every turn.completed.
USAGE_KEYS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens",
              "reasoning_output_tokens")

# ---- file_change's changes -----------------------------------------------------------------------------------------
CHANGE_KEYS = ("path", "kind")
# Lane pf1-codex-fcdelete: delete maps to write {path} (the docstring's pinned-source block); any other kind refuses.
CHANGE_KINDS = {"add": tv.WRITE, "update": tv.EDIT, "delete": tv.WRITE}

# ---- each key's value type (W11A-R1-8); a key not listed here (mcp_tool_call's arguments, result, error) is untyped,
# its shape not documented. No entry lists bool, and a bool is never read as an int. A record's `type` is checked
# against its table before these are read.
_NONE = type(None)
EVENT_VALUE_TYPES = {"thread_id": (str,), "item": (dict,), "usage": (dict,), "error": (dict,),
                     "message": (str,)}
ITEM_VALUE_TYPES = {"id": (str,), "text": (str,), "command": (str,), "aggregated_output": (str,),
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
        if k in table and (not isinstance(v, table[k]) or isinstance(v, bool)):
            raise ShapeError(f"{what}: {k} is not {' or '.join(t.__name__ for t in table[k])}")


def check_record(rec) -> tuple:
    """(event type, item type or None) of one decoded stream record, after checking it against the tables.

    Refuses (ShapeError) a record that is not an object, an event type with no entry, an item type with no entry, an
    item type an item.started may not carry, any key, required or extra, off its entry, and any value off its type
    (a file_change's changes too: a non-empty list of {path, kind} with kind in CHANGE_KINDS)."""
    if not isinstance(rec, dict):
        raise ShapeError("a record that is not an object")
    t = rec.get("type")
    if not isinstance(t, str) or t not in EVENT_KEYS:
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
    if not isinstance(it, str) or it not in ITEM_KEYS:
        raise ShapeError(f"unknown item type: {it!r}")
    _keys(f"item {it}", item, *ITEM_KEYS[it])
    _types(f"item {it}", item, ITEM_VALUE_TYPES)
    if not item["id"]:
        raise ShapeError(f"item {it}: its id is empty")
    if t == ITEM_STARTED and it not in STARTED_ITEM_TYPES:
        raise ShapeError(f"item.started carrying {it!r}: only {STARTED_ITEM_TYPES} are pre-registered there")
    if t == ITEM_STARTED and it == FILE_CHANGE and item.get("status") != STARTED_FILE_CHANGE_STATUS:
        raise ShapeError(f"item.started carrying file_change: its status must be {STARTED_FILE_CHANGE_STATUS!r}, "
                         f"the only one the pinned exec prints there")
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
    """Codex's host-captured `codex exec --json` stream, one JSON record per line (never the rollout file). One parser
    may read a take's streams one after another; each stream's started file changes are kept until thread.started."""

    def __init__(self) -> None:
        self._started: dict = {}       # exec id -> the started file_change's [(path, kind)], this stream only

    def items(self, line: str) -> list:
        rec = decode(line)
        t, it = check_record(rec)      # every key and value below has passed the tables
        if t == THREAD_STARTED:
            self._started = {}
        if t not in ITEM_EVENTS:
            return [tv.RawItem(t, tv.HARNESS, text=tv._joined({k: v for k, v in rec.items() if k != "type"}))]
        item = rec["item"]
        raw = f"{t}:{it}"
        if t == ITEM_STARTED:
            if it == FILE_CHANGE:
                return self._file_change_started(item, raw)
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
    def _changes(item: dict) -> list:
        return [(ch["path"], ch["kind"]) for ch in item["changes"]]

    def _file_change_started(self, item: dict, raw: str) -> list:
        if item["id"] in self._started:
            raise ShapeError(f"a second item.started for file_change {item['id']!r} in one stream")
        self._started[item["id"]] = self._changes(item)
        return [tv.RawItem(raw, tv.TOOL_CALL, tool=CHANGE_KINDS[kind], args={"path": path}, ref=f"{item['id']}#{i}")
                for i, (path, kind) in enumerate(self._started[item["id"]])]

    def _file_change(self, item: dict, raw: str) -> list:
        started = self._started.pop(item["id"], None)
        changes = self._changes(item)
        if started is not None:
            if started != changes:
                raise ShapeError(f"file_change {item['id']!r} completes with changes that are not its start's")
            return [tv.RawItem(raw, tv.TOOL_RESULT, text=item.get("status"), ref=f"{item['id']}#{i}")
                    for i in range(len(changes))]
        out = []
        for i, (path, kind) in enumerate(changes):
            ref = f"{item['id']}#{i}"
            out.append(tv.RawItem(raw, tv.TOOL_CALL, tool=CHANGE_KINDS[kind], args={"path": path}, ref=ref))
            out.append(tv.RawItem(raw, tv.TOOL_RESULT, text=item.get("status"), ref=ref))
        return out
