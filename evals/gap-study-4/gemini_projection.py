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
From the pinned bundle read on athena (lane-reports/gemini-0.64.0-source-
retained-addendum-2026-10-14.md): a "user" message holding only functionResponse
parts is GeminiChat's record of a tool round trip, so it continues its
interaction; it must follow the gemini message whose calls it answers and answer
exactly those calls, each once, and a tool-calling message must be followed by
one before the next gemini message; a call's result may hold the whole round trip's responses
(updateMessagesFromHistory, run by GeminiChat.initialize on every chat start), so
its parts may answer sibling calls of the same message by id and name and must
answer this call exactly once; displayContent is recorded only when it differs
from the sent text, so a present one is admitted only when equal and in practice
refuses. Still a named false-refusal risk: multi-part user content (an @-include
prompt), and the binary-injection road's synthetic thought and info messages.
A refusal is a reader result only: it never erases an executed record or
authorizes a replacement take.

Lane vendor-b25 (glitch-26's rulings 3, 4 and 6), read from the pinned package
(@google/gemini-cli 0.64.0, tarball sha256 891a794e..., bundle/chunk-NR7L3FXV.js
sha256 d566e81b..., the chunk bundle/gemini.js:10 imports):
  * The session context message is not an interaction. GeminiClient.startChat
    (:348055-348079) builds the history with getInitialChatHistory
    (:336356-336377), whose first turn is a user turn with id
    deriveStableId(["environment-context"]) (:336357, :336369; deriveStableId is
    sha256 of the sorted ids joined by "|", first 32 hex digits, :286041-286044)
    and one text part, getEnvironmentContext's block (:336332-336355), which
    begins "<session_context>\nThis is the Gemini CLI. We are setting up the
    context for our chat.\n" and ends "</session_context>" (:336343-336352,
    trimmed). The recorder writes it as newMessage("user", parts, undefined, id)
    (:286901-286909): keys id, timestamp, type, content. It is recognised only as
    the first replayed message, with exactly that id, those keys and that one
    wrapped text part (ENV_CONTEXT_ID, _session_context); anything else stays an
    interaction.
  * The resumed duplicate of a tool round trip. On resume,
    convertSessionToClientHistory (:286099-286194) emits after each tool-calling
    model turn a synthetic user turn `${msg.id}_response` holding its calls'
    results (:286156-286188), then the stored round-trip message read back as a
    user turn (:286105-286117); updateMessagesFromHistory appends the synthetic
    one as a new message (:286190-286196) and orders both behind the model turn
    (orderIds, :287262-287264). So after a tool-calling gemini message G there
    may be the copy (id G.id + "_response") and then the original; the copy is
    admitted only directly after G, only when the original follows it at once,
    and only when the two are byte-identical (same keys; content equal as
    serialized JSON); the original then counts as G's round trip and the copy as
    nothing. Any other repeated round trip still refuses.
  * An empty final answer (ruling 6): an interaction with no recorded text
    segment is no longer refused here; the join compares the segments with the
    stream's normalized responses, so both empty agrees and one side empty
    disagrees.

Lane vendor-b26 (glitch-26's rulings 1 and 2 on the B26 design):
  * Facts are read from gemini_session_replay's `timeline`, the original
    messages at their state before any removal took them out of the loader's
    state, never from a resume copy or a re-recorded copy (verified in the
    replay). A tool-output masking re-record therefore changes no fact.
  * The loop-recovery feedback. GeminiClient._recoverFromLoop
    (chunk-NR7L3FXV.js:348601-348609) sends `System: Potential loop detected.
    Details: <detail>. Please take a step back ... without new results.`
    (:348603) as a new user message when the loop detector first fires
    (:348275-348285, :348355-348357); the stream has no line for it (only a
    repeated loop writes one, gemini-Q2GRYIAK.js:12232-12242). On its exact shape
    (keys id, timestamp, type, content; one text part, the pinned opening and
    closing around a non-empty detail; directly after a tool-response turn of
    the same interaction) it continues the interaction, is never a sent line and
    is never compared to the stream; any other message opening with the
    template refuses.
  * project_with_properties also returns the take properties: the replay's
    history rewrites, masked tool outputs and ignored-prompt resumes, and the
    loop feedback messages injected. They are properties, never facts.
"""
from __future__ import annotations

import math
import re

import gemini_session_replay as replay_mod


import hashlib
import json


class ProjectionRefused(ValueError):
    """The retained native session is outside the reviewed projection subset."""


USER_KEYS = {"id", "timestamp", "type", "content", "displayContent"}
# deriveStableId(["environment-context"]) (chunk-NR7L3FXV.js:286041-286044, :336369).
ENV_CONTEXT_ID = hashlib.sha256(b"environment-context").hexdigest()[:32]
ENV_CONTEXT_OPEN = ("<session_context>\nThis is the Gemini CLI. We are setting up the context for our chat.\n")
ENV_CONTEXT_CLOSE = "</session_context>"
RESPONSE_SUFFIX = "_response"       # chunk-NR7L3FXV.js:286182
LOOP_OPEN = "System: Potential loop detected. Details: "                 # chunk-NR7L3FXV.js:348603
LOOP_CLOSE = (". Please take a step back and confirm you're making forward progress. If not, take a step back, analyze "
              "your previous actions and rethink how you're approaching the problem. Avoid repeating the same tool calls "
              "or responses without new results.")
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


def _text_of(value, what):
    """A user content or displayContent as one string: a string, or a list of exactly one text part."""
    if isinstance(value, list):
        if len(value) != 1 or not isinstance(value[0], dict) or set(value[0]) != {"text"}:
            raise ProjectionRefused(f"native user {what} must be one text part")
        value = value[0]["text"]
    if not _string(value):
        raise ProjectionRefused(f"native user {what} is absent or not text")
    return value


def _sent(message):
    if not set(message) <= USER_KEYS:
        raise ProjectionRefused("unsupported native user message keys")
    content = _text_of(message["content"], "content")
    if "displayContent" in message:
        # Ruling 5 (source retained: GeminiChat records displayContent only when its string differs from the sent
        # parts'), so on sessions this version writes a present displayContent always refuses.
        if _text_of(message["displayContent"], "displayContent") != content:
            raise ProjectionRefused("native user displayContent differs from the sent text")
    return content


def _tool_response_turn(message):
    """A "user" message whose content is only functionResponse parts: GeminiChat's record of a tool round trip
    (recordSyntheticMessage("user", userContent.parts) when isOriginalFunctionResponse; source retained). Its
    [(id, name)], or None when the message is not one."""
    content = message.get("content")
    if not (isinstance(content, list) and content and set(message) <= USER_KEYS - {"displayContent"}
            and all(isinstance(p, dict) and set(p) == {"functionResponse"} for p in content)):
        return None
    out = []
    for part in content:
        r = part["functionResponse"]
        if (not isinstance(r, dict) or set(r) != RESPONSE_KEYS or not _string(r["id"]) or not _string(r["name"])
                or not isinstance(r["response"], dict)):
            raise ProjectionRefused("unknown native tool response part in a tool-response turn")
        out.append((r["id"], r["name"]))
    return out


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


def _tool(tool, siblings):
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
    own = 0
    for part in result:
        response = part.get("functionResponse") if isinstance(part, dict) and set(part) == {"functionResponse"} else None
        if not isinstance(response, dict) or set(response) != RESPONSE_KEYS or not isinstance(response["response"], dict):
            raise ProjectionRefused("unknown native tool response part")
        # Ruling 6 (source retained: updateMessagesFromHistory, called by GeminiChat.initialize on every chat start,
        # sets a call's result to the whole user turn's parts): a part may answer a sibling call of the same message,
        # by its id and name; it never names any other call.
        if siblings.get(response["id"]) != response["name"]:
            raise ProjectionRefused("native tool response part names another call")
        own += response["id"] == tool["id"]
    if own != 1:
        raise ProjectionRefused("native tool response parts must name this call exactly once")
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
        siblings = {t.get("id"): t.get("name") for t in recorded_tools if isinstance(t, dict)}
        facts = [_tool(tool, siblings) for tool in recorded_tools]
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
    return {"session_id": session_id, "requested_model": models.pop() if models else None,
            "version": None, "cwd": None, "permission_mode": None, "sent": sent,
            "output": segments + tools}


def _session_context(message) -> bool:
    """The first message is the session context turn on its exact pinned shape (module docstring)."""
    content = message.get("content")
    return (message.get("type") == "user" and message.get("id") == ENV_CONTEXT_ID
            and set(message) == {"id", "timestamp", "type", "content"} and isinstance(content, list)
            and len(content) == 1 and isinstance(content[0], dict) and set(content[0]) == {"text"}
            and isinstance(content[0]["text"], str) and content[0]["text"].startswith(ENV_CONTEXT_OPEN)
            and content[0]["text"].endswith(ENV_CONTEXT_CLOSE))


def _serialized(value) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _resumed_copy(message, gemini, following) -> bool:
    """`message` is the resume-time copy of `gemini`'s round trip (module docstring): its id is gemini's plus
    "_response", and the original that follows it at once is byte-identical to it (same keys, same content)."""
    return (gemini is not None and gemini["type"] == "gemini" and message["id"] == gemini["id"] + RESPONSE_SUFFIX
            and following is not None and following["type"] == "user" and following["id"] != message["id"]
            and _tool_response_turn(following) is not None and set(following) == set(message)
            and _serialized(following["content"]) == _serialized(message["content"]))


def _loop_opening(message) -> bool:
    content = message.get("content")
    text = content if isinstance(content, str) else "".join(
        p.get("text", "") for p in content if isinstance(p, dict) and isinstance(p.get("text"), str)) \
        if isinstance(content, list) else ""
    return message.get("type") == "user" and text.startswith(LOOP_OPEN)


def _loop_feedback(message) -> bool:
    """The loop-recovery message on its exact pinned shape (module docstring), its position aside."""
    content = message.get("content")
    return (set(message) == {"id", "timestamp", "type", "content"} and isinstance(content, list) and len(content) == 1
            and isinstance(content[0], dict) and set(content[0]) == {"text"} and isinstance(content[0]["text"], str)
            and content[0]["text"].startswith(LOOP_OPEN) and content[0]["text"].endswith(LOOP_CLOSE)
            and len(content[0]["text"]) > len(LOOP_OPEN) + len(LOOP_CLOSE))


def project(raw):
    """Every user-delimited interaction of one retained native snapshot, or ProjectionRefused."""
    return project_with_properties(raw)[0]


def project_with_properties(raw):
    """(project's facts, the take properties): history_rewrites, tool_outputs_masked, ignored_prompt_resumes and
    loop_feedback_injected, counted on this snapshot. Properties are never facts."""
    try:
        replayed = replay_mod.replay(raw)
    except replay_mod.ReplayRefused as exc:
        raise ProjectionRefused(f"native replay refused: {exc}") from None
    _finite(replayed)
    session_id = replayed["metadata"]["sessionId"]
    messages = list(replayed["timeline"])
    loops = 0
    if messages and _session_context(messages[0]):
        messages = messages[1:]                    # the session context turn: never an interaction
    groups, previous = [], None
    for k, message in enumerate(messages):
        answered = _tool_response_turn(message) if message["type"] == "user" else None
        if answered is None and _loop_opening(message):
            if not (_loop_feedback(message) and groups and previous is not None and previous["type"] == "user"
                    and _tool_response_turn(previous) is not None):
                raise ProjectionRefused("a loop-recovery feedback message is off its pinned shape or place "
                                        "(chunk-NR7L3FXV.js:348601-348609)")
            loops += 1
            previous = message
            continue                                   # the interaction continues; never a sent line
        if answered is not None and message["id"].endswith(RESPONSE_SUFFIX):
            following = messages[k + 1] if k + 1 < len(messages) else None
            if not _resumed_copy(message, previous, following):
                raise ProjectionRefused("a <gemini id>_response turn is not the resumed copy of the round trip that "
                                        "follows it (byte-identical, directly after its gemini message)")
            continue                                   # the copy counts as nothing; the original is the round trip
        if answered is not None:
            # Batch-5 review finding 1: GeminiChat records one round trip per tool-calling model message, holding the
            # responses to exactly that message's calls; so the turn must follow that message and answer each of its
            # calls once, and nothing else.
            calls = ([(t.get("id"), t.get("name")) for t in previous.get("toolCalls") or [] if isinstance(t, dict)]
                     if previous is not None and previous["type"] == "gemini" and groups else [])
            if not calls or sorted(answered) != sorted(calls) or len(set(answered)) != len(answered):
                raise ProjectionRefused("a tool-response turn must answer exactly the calls of the gemini message "
                                        "just before it, each once")
            previous = message
            continue                                   # a tool round trip, never a new interaction
        if (message["type"] == "gemini" and previous is not None and previous["type"] == "gemini"
                and previous.get("toolCalls")):
            raise ProjectionRefused("a tool-calling gemini message has no tool-response turn before the next one")
        previous = message
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
    return out, dict(replayed["properties"], loop_feedback_injected=loops)
