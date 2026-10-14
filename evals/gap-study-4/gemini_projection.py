"""Provisional Gemini 0.64.0 native-session projection, never production admission.

Source-derived from the installed bundle's chatRecordingService (newMessage,
recordMessage, recordToolCalls) and GeminiChat.recordCompletedToolCalls, as
retained in the box lane's gemini-native-session-source.json and
gemini-tool-result-source.json (see lane-reports/gemini-0.64.0-source-retained-
2026-10-14.md); not validated against a recorded live session. No production
registry imports this module (vendor_provenance's NATIVE_SESSION_READERS stays
empty).

project(raw) replays one retained snapshot through gemini_session_replay and
returns one fact dict per user-delimited interaction, in the native-session
fact schema (vendor_provenance.SESSION_KEYS). Native version, cwd and mode are
None. requested_model is the `model` the native gemini messages of that
interaction report, None when none reports one; a contradiction refuses.

`output` is a comparison summary, NOT an event sequence and NOT displayed text:

  {"kind": "recorded-text", "message": <native id>, "text": ...}
      one segment per gemini message with non-empty recorded text, in replay
      order, never joined. The recorder does not store what the stream showed:
      chunk-J7SXW2FI.js (sha256 e2aca152...f206e), the GeminiChat code before its
      recordMessage({model, type: "gemini", content: responseText}) call,
      removes [U+200B-U+200D U+FEFF U+200E U+200F], removes <!-- ... -->
      repeatedly until none is left, then trims (RECORDER_NORMALIZATION,
      recorder_normalize below). The stream side must group its assistant
      deltas per model message and apply recorder_normalize to each before any
      comparison; a recorded segment is never "the displayed text".
  {"kind": "tool", id, name, args, emitted_status, output_present, output}
      ordered tool facts; output is the string resultDisplay only. Model-facing
      response parts (toolCalls[].result) are validated as native evidence and
      never become output; an object display result is absent output, never an
      empty string. Emitted "success" is the recorded status only, never proof
      of execution.

A string gemini content must already be in recorder normal form (else it
contradicts the recorder and refuses). A part-array content (the recorder's
synthetic road) yields recorder_normalize of its non-thought text parts.

Refused (ProjectionRefused, each with its own reason), rather than guessed:
unknown keys/parts, statuses other than success/error, a sub-agent call,
nonfinite numbers, missing or mismatched response parts, reused call ids,
content function calls that disagree with the recorded tool calls by id, name
or args, ANSI escape bytes, info/error/warning messages, interactions without a
user message, an assistant message or recorded text, and an interaction whose
last gemini message carries tool calls (the follow-up model reply was never
recorded: killed or timed out after the tool).
The native record alone never establishes that an interaction completed: a kill
while a tool is still running leaves an ordinary-looking text message with no
toolCalls (recordToolCalls runs only once tools complete). An interaction counts
as complete only when joined to the stream's terminal result for that turn
(the stream-side slice owes that join); this projection makes no such claim.
Known false-refusal risks for the first recorded walk, kept refusing because the
pinned source lines are not retained (lane-reports/gemini-0.64.0-source-
retained-2026-10-14.md): user displayContent (GeminiChat's user-message
recording), multi-part user content, and history-patched parallel tool results
(the updateMessagesFromHistory caller). A refusal is a reader result only: it
never erases an executed record or authorizes a replacement take.
"""
from __future__ import annotations

import math
import re

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
# chunk-J7SXW2FI.js, before GeminiChat's recordMessage({model, type: "gemini", content: responseText}):
#   rawResponseText.replace(/[​-‍﻿‎‏]/g, "")
#   do { previous = responseText; responseText = responseText.replace(/<!--[\s\S]*?-->/g, ""); }
#   while (responseText !== previous);
#   responseText = responseText.trim();
RECORDER_NORMALIZATION = "zero-width removal, repeated <!-- --> removal, trim (chunk-J7SXW2FI.js recordMessage site)"
_ZERO_WIDTH = re.compile("[​-‍﻿‎‏]")
_COMMENT = re.compile(r"<!--[\s\S]*?-->")
# JavaScript's String.prototype.trim strips WhiteSpace and LineTerminator code points; Python's str.strip()
# differs (it strips U+001C-U+001F and U+0085, and JS strips U+FEFF, already removed above). Spelled out exactly.
_JS_TRIM = ("\t\n\x0b\x0c\r \xa0            "
            "    　﻿")


def recorder_normalize(text: str) -> str:
    """The recorder's normalization of one model message's text, as the pinned 0.64.0 bundle applies it."""
    text = _ZERO_WIDTH.sub("", text)
    previous = None
    while text != previous:
        previous, text = text, _COMMENT.sub("", text)
    return text.strip(_JS_TRIM)


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
    if "displayContent" in message:
        raise ProjectionRefused("native user displayContent is unsupported until its recording source is retained")
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
    """(recorded text, ordered content function calls) of one gemini message."""
    if isinstance(content, str):
        _no_escape(content)
        if recorder_normalize(content) != content:
            raise ProjectionRefused("native gemini text is not in the recorder's normal form")
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
            continue                                   # thoughts stay separate from recorded text
        elif set(part) in ({"functionCall"}, {"functionCall", "thoughtSignature"}):
            if "thoughtSignature" in part and not _string(part["thoughtSignature"]):
                raise ProjectionRefused("native thoughtSignature is not a nonempty string")
            call = part["functionCall"]                # thoughtSignature: a known key, never output
            if (not isinstance(call, dict) or set(call) != CALL_KEYS or not _string(call["id"])
                    or not _string(call["name"]) or not isinstance(call["args"], dict)):
                raise ProjectionRefused("native content function call is incomplete")
            calls.append(call)
        else:
            raise ProjectionRefused("unknown or mixed native content part")
    return recorder_normalize("".join(text)), calls


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
        if not isinstance(response, dict) or set(response) != RESPONSE_KEYS or not isinstance(response["response"], dict):
            raise ProjectionRefused("unknown native tool response part")
        if response["id"] != tool["id"] or response["name"] != tool["name"]:
            raise ProjectionRefused("native tool response part names another call")
    display = tool.get("resultDisplay")
    present = isinstance(display, str)
    if present:
        _no_escape(display)
    elif display is not None and not isinstance(display, dict):
        raise ProjectionRefused("unknown native tool display result")
    return {"kind": "tool", "id": tool["id"], "name": tool["name"], "args": tool["args"],
            "emitted_status": tool["status"], "output_present": present, "output": display if present else None}


def _agree(calls, facts):
    """Content function calls, when present, must be the recorded tool calls, compared by id, name and args."""
    if not calls:
        return
    if len(calls) != len(facts):
        raise ProjectionRefused("content function calls and recorded tool calls differ in number")
    for call, fact in zip(calls, facts):
        for key in ("id", "name", "args"):
            if call[key] != fact[key]:
                raise ProjectionRefused(f"content function call {key} disagrees with the recorded tool call")


def _interaction(session_id, user, replies, seen_ids):
    sent = _sent(user)
    segments, tools, models = [], [], set()
    for message in replies:
        if not set(message) <= GEMINI_KEYS:
            raise ProjectionRefused("unsupported native gemini message keys")
        if "model" in message:
            if not _string(message["model"]):
                raise ProjectionRefused("native gemini model is not a nonempty string")
            models.add(message["model"])
        if "thoughts" in message and not isinstance(message["thoughts"], list):
            raise ProjectionRefused("native thoughts must be an array")
        recorded, calls = _content(message["content"])
        if recorded:
            segments.append({"kind": "recorded-text", "message": message["id"], "text": recorded})
        recorded_tools = message.get("toolCalls", [])
        if not isinstance(recorded_tools, list):
            raise ProjectionRefused("native toolCalls must be an array")
        facts = [_tool(tool) for tool in recorded_tools]
        _agree(calls, facts)
        for fact in facts:
            if fact["id"] in seen_ids:
                raise ProjectionRefused("native tool call id reused")
            seen_ids.add(fact["id"])
        tools.extend(facts)
    if replies[-1].get("toolCalls"):
        raise ProjectionRefused("native interaction is incomplete: its last model message ends on tool calls")
    if len(models) > 1:
        raise ProjectionRefused("contradictory native models within one interaction")
    if not segments:
        raise ProjectionRefused("native interaction has no recorded answer text")
    return {"session_id": session_id, "requested_model": models.pop() if models else None,
            "version": None, "cwd": None, "permission_mode": None, "sent": sent,
            "output": segments + tools}


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
