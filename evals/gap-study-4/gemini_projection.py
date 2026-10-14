"""Provisional Gemini 0.64.0 native-session projection, never production admission.

Source-derived from the installed bundle's chatRecordingService (newMessage,
recordMessage, recordToolCalls) and GeminiChat.recordCompletedToolCalls, as
retained in the box lane's gemini-native-session-source.json and
gemini-tool-result-source.json; not validated against a recorded live session.
No production registry imports this module (vendor_provenance's
NATIVE_SESSION_READERS stays empty).

project(raw) replays one retained snapshot through gemini_session_replay and
returns one fact dict per user-delimited interaction, in the native-session
fact schema (vendor_provenance.SESSION_KEYS). Native version, cwd and mode are
None. requested_model is the `model` the native gemini messages of that
interaction report, None when none reports one; a contradiction refuses.

`output` is a comparison summary, NOT an event sequence: one exact visible-text
aggregate (non-thought text, concatenated in replay order) followed by ordered
tool facts. A tool fact carries id, name, structured args, the emitted raw
status and whether a string display result exists. Model-facing response parts
(toolCalls[].result) are validated as native evidence and never become displayed
output; an object display result is absent output, never an empty string.
Emitted "success" is the recorded status only, never proof of execution.

The initial supported subset refuses (ProjectionRefused), rather than guesses:
unknown keys/parts, statuses other than success/error, a sub-agent call,
nonfinite numbers, missing or mismatched response parts, reused call ids,
content function calls that disagree with the recorded tool calls, ANSI escape
bytes (the stream strips them; the transformation is unproven), displayContent,
multi-part user content, info/error/warning messages, and interactions without
a user message, an assistant message or visible answer text. A refusal is a
reader result only: it never erases an executed record or authorizes a
replacement take.
"""
from __future__ import annotations

import math

import gemini_session_replay as replay_mod


class ProjectionRefused(ValueError):
    """The retained native session is outside the reviewed projection subset."""


USER_KEYS = {"id", "timestamp", "type", "content"}
GEMINI_KEYS = {"id", "timestamp", "type", "content", "thoughts", "tokens", "model", "toolCalls"}
TOOL_KEYS = {"id", "name", "args", "result", "status", "timestamp", "resultDisplay", "description",
             "displayName", "renderOutputAsMarkdown"}
CALL_KEYS = {"id", "name", "args"}
RESPONSE_KEYS = {"id", "name", "response"}
STATUSES = ("success", "error")
ESCAPE = "\x1b"


def _string(value):
    return isinstance(value, str) and bool(value)


def _finite(value):
    """Every number anywhere in the record must be finite (json accepts NaN/Infinity)."""
    if isinstance(value, float) and not math.isfinite(value):
        raise ProjectionRefused("nonfinite number in native session")
    if isinstance(value, dict):
        for item in value.values():
            _finite(item)
    elif isinstance(value, list):
        for item in value:
            _finite(item)


def _no_escape(text):
    if ESCAPE in text:
        raise ProjectionRefused("ANSI escape in native text; the displayed transformation is unproven")


def _sent(message):
    if not set(message) <= USER_KEYS:
        raise ProjectionRefused("unsupported native user message keys")
    content = message["content"]
    if isinstance(content, list):
        if (len(content) != 1 or not isinstance(content[0], dict) or set(content[0]) != {"text"}):
            raise ProjectionRefused("native user content must be one text part")
        content = content[0]["text"]
    if not _string(content):
        raise ProjectionRefused("native user content is absent or not text")
    return content


def _content(content):
    """(visible text, ordered content function calls) of one gemini message."""
    if isinstance(content, str):
        _no_escape(content)
        return content, []
    if not isinstance(content, list):
        raise ProjectionRefused("native gemini content must be text or a part array")
    text, calls = [], []
    for part in content:
        if not isinstance(part, dict):
            raise ProjectionRefused("native content part is not an object")
        if set(part) == {"text"} and isinstance(part["text"], str):
            _no_escape(part["text"])
            text.append(part["text"])
        elif set(part) == {"text", "thought"} and isinstance(part["text"], str) and part["thought"] is True:
            continue                                   # thoughts stay separate from visible text
        elif set(part) == {"functionCall"}:
            call = part["functionCall"]
            if (not isinstance(call, dict) or set(call) != CALL_KEYS or not _string(call["id"])
                    or not _string(call["name"]) or not isinstance(call["args"], dict)):
                raise ProjectionRefused("native content function call is incomplete")
            calls.append(call)
        else:
            raise ProjectionRefused("unknown or mixed native content part")
    return "".join(text), calls


def _tool(tool):
    if not isinstance(tool, dict) or not set(tool) <= TOOL_KEYS:
        raise ProjectionRefused("unsupported native tool-call keys")
    if (not _string(tool.get("id")) or not _string(tool.get("name"))
            or not isinstance(tool.get("args"), dict)):
        raise ProjectionRefused("native tool call lacks id, name or structured args")
    if tool.get("status") not in STATUSES:
        raise ProjectionRefused("unsupported native tool status")
    result = tool.get("result")
    if not isinstance(result, list) or not result:
        raise ProjectionRefused("native tool call lacks model-facing response parts")
    for part in result:
        response = part.get("functionResponse") if isinstance(part, dict) and set(part) == {"functionResponse"} else None
        if (not isinstance(response, dict) or set(response) != RESPONSE_KEYS
                or response["id"] != tool["id"] or response["name"] != tool["name"]
                or not isinstance(response["response"], dict)):
            raise ProjectionRefused("unknown or mismatched native tool response part")
    display = tool.get("resultDisplay")
    present = isinstance(display, str)
    if present:
        _no_escape(display)
    elif display is not None and not isinstance(display, dict):
        raise ProjectionRefused("unknown native tool display result")
    return {"kind": "tool", "id": tool["id"], "name": tool["name"], "args": tool["args"],
            "emitted_status": tool["status"], "output_present": present, "output": display if present else None}


def _interaction(session_id, user, replies, seen_ids):
    sent = _sent(user)
    text, tools, models = [], [], set()
    for message in replies:
        if not set(message) <= GEMINI_KEYS:
            raise ProjectionRefused("unsupported native gemini message keys")
        if "model" in message:
            if not _string(message["model"]):
                raise ProjectionRefused("native gemini model is not a nonempty string")
            models.add(message["model"])
        if "thoughts" in message and not isinstance(message["thoughts"], list):
            raise ProjectionRefused("native thoughts must be an array")
        visible, calls = _content(message["content"])
        text.append(visible)
        recorded = message.get("toolCalls", [])
        if not isinstance(recorded, list):
            raise ProjectionRefused("native toolCalls must be an array")
        facts = [_tool(tool) for tool in recorded]
        if calls and [(c["id"], c["name"], c["args"]) for c in calls] != [(f["id"], f["name"], f["args"]) for f in facts]:
            raise ProjectionRefused("content function calls disagree with recorded tool calls")
        for fact in facts:
            if fact["id"] in seen_ids:
                raise ProjectionRefused("native tool call id reused")
            seen_ids.add(fact["id"])
        tools.extend(facts)
    if len(models) > 1:
        raise ProjectionRefused("contradictory native models within one interaction")
    answer = "".join(text)
    if not answer:
        raise ProjectionRefused("native interaction has no visible answer text")
    return {"session_id": session_id, "requested_model": models.pop() if models else None,
            "version": None, "cwd": None, "permission_mode": None, "sent": sent,
            "output": [{"kind": "visible-text", "text": answer}] + tools}


def project(raw):
    """Every user-delimited interaction of one retained native snapshot, or ProjectionRefused."""
    try:
        replayed = replay_mod.replay(raw)
    except replay_mod.ReplayRefused as exc:
        raise ProjectionRefused(f"native replay refused: {exc}") from None
    _finite(replayed)
    session_id = replayed["metadata"]["sessionId"]
    groups = []
    for message in replayed["messages"]:
        if message["type"] == "user":
            groups.append((message, []))
        elif message["type"] == "gemini":
            if not groups:
                raise ProjectionRefused("native gemini message precedes any user message")
            groups[-1][1].append(message)
        else:
            raise ProjectionRefused(f"native {message['type']} messages are unsupported in this subset")
    if not groups:
        raise ProjectionRefused("native session has no interactions")
    seen_ids, out = set(), []
    for user, replies in groups:
        if not replies:
            raise ProjectionRefused("native interaction lacks an assistant message")
        out.append(_interaction(session_id, user, replies, seen_ids))
    return out
