"""Live harness slice 5: join one Gemini stream-json call to its native interaction; never production admission.

One `gemini -p … -o stream-json` call is one interaction. The legacy non-interactive loop in the pinned 0.64.0
bundle (gemini-legacy-content-source, the box lane's evidence) runs one model response per loop iteration: each content
event is written as an assistant `message` with `delta: true` (ANSI stripped unless raw output is configured), each
tool call request as `tool_use`, and the tools run and their `tool_result`s are written before the next response
starts. So a response's text is every assistant delta after the previous tool_result.

The native recorder stores each response's text in gemini_projection.recorder_normalize's normal form (zero-width
removal, repeated <!-- --> removal, JavaScript trim; chunk-J7SXW2FI.js, before recordMessage), and stores nothing for a
response whose normalized text is empty. join() applies the same normalization to each stream response, drops the
empty ones, and requires the list to equal the native `recorded-text` segments, in order. It never calls either side
"displayed text".

Completeness is the stream's alone: an interaction is complete only when its call ended with exactly one terminal
`result` whose status is success, the last record of the stream (r2 finding 1: the native record cannot tell a kill
during a tool run from an answer). A failed result is kept and reported (complete False), with its error object;
`error` events are kept in order. No result at all, a cut stream, or a record after the result refuses.

Tool facts compare by id, name, order and status: every tool_use has exactly one tool_result of its id, ids are never
reused, and the stream's (id, name, status) list must equal the native tool facts' (id, name, emitted_status).
The sent text and the init model are compared when both sides have them, and stay None when the stream lacks them.
Session identity (lane vendor-b25, glitch-26's ruling 5; Gemini review MAJOR 3), as the Codex join binds the exec
thread: the stream's init session_id must equal the native session's sessionId; a stream with no init, or another id,
refuses.
Every disagreement, and every shape the stream tables refuse (transcript_gemini.check_record), refuses (JoinRefused).
Unregistered: vendor_provenance's NATIVE_SESSION_READERS stays empty until a real recorded session is reviewed.
"""
from __future__ import annotations

import json

import gemini_projection as gp
import transcript_gemini as tg


class JoinRefused(ValueError):
    """The stream and the native interaction disagree, or one of them is outside the supported subset."""


def _records(text: str) -> list:
    if not isinstance(text, str):
        raise JoinRefused("the stream must be text")
    out = []
    lines = [line for line in text.split("\n") if line.strip()]
    for n, line in enumerate(lines, 1):
        try:
            rec = json.loads(line)
        except ValueError:
            raise JoinRefused(f"stream line {n} is not JSON (a cut stream has no proven end)") from None
        try:
            tg.check_record(rec)
        except tg.ShapeError as exc:
            raise JoinRefused(f"stream record {n} is off the stream tables: {exc}") from None
        out.append(rec)
    return out


def read_call(text: str) -> dict:
    """One call's stream, read for the join: sent, init model, per-response raw texts, tools, errors, terminal."""
    sent, init_model, responses, tools, results, errors, terminal = None, None, [[]], [], {}, [], None
    init_session = None
    params = {}
    after_result = False
    for rec in _records(text):
        t = rec["type"]
        if terminal is not None:
            raise JoinRefused("a stream record comes after the terminal result")
        if t == tg.INIT:
            if init_model is not None:
                raise JoinRefused("two init records in one call")
            init_model, init_session = rec["model"], rec["session_id"]
        elif t == tg.MESSAGE and rec["role"] == tg.USER:
            if sent is not None:
                raise JoinRefused("two user messages in one call")
            sent = rec["content"]
        elif t == tg.MESSAGE:
            if rec.get("delta") is not True:
                raise JoinRefused("a non-delta assistant message is unsupported in this subset")
            if after_result:
                responses.append([])
                after_result = False
            responses[-1].append(rec["content"])
        elif t == tg.TOOL_USE:
            if any(rec["tool_id"] == x[0] for x in tools):
                raise JoinRefused("tool_use id reused")
            tools.append((rec["tool_id"], rec["tool_name"]))
            params[rec["tool_id"]] = rec["parameters"]
        elif t == tg.TOOL_RESULT:
            if rec["tool_id"] not in {x[0] for x in tools}:
                raise JoinRefused("a tool_result names no tool_use before it")
            if rec["tool_id"] in results:
                raise JoinRefused("two tool_results for one tool_use")
            results[rec["tool_id"]] = rec["status"]
            after_result = True
        elif t == tg.ERROR:
            errors.append({"severity": rec.get("severity"), "message": rec["message"]})
        elif t == tg.RESULT:
            terminal = {"status": rec["status"], "error": rec.get("error")}
        else:
            raise JoinRefused(f"stream event {t!r} is unsupported in this subset")
    if terminal is None:
        raise JoinRefused("no terminal result: the interaction's completeness is unproven")
    missing = [i for i, _ in tools if i not in results]
    if missing:
        raise JoinRefused(f"no tool_result for tool_use {missing}")
    return {"sent": sent, "init_model": init_model, "init_session": init_session, "responses": ["".join(r) for r in responses],
            "tools": [(i, n, results.get(i)) for i, n in tools], "args": [params[i] for i, _ in tools],
            "errors": errors, "terminal": terminal}


def _canonical(value) -> str:
    """Exact JSON equality after both sides are parsed: one canonical spelling (sorted keys), so 1, 1.0 and true
    stay three different values, as JSON says they are."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _native(fact: dict) -> tuple:
    if not isinstance(fact, dict) or not isinstance(fact.get("output"), list):
        raise JoinRefused("the native fact is not a projected interaction")
    texts, tools = [], []
    for item in fact["output"]:
        kind = item.get("kind") if isinstance(item, dict) else None
        if kind == "recorded-text":
            texts.append(item["text"])
        elif kind == "tool":
            tools.append((item["id"], item["name"], item["emitted_status"], _canonical(item["args"])))
        else:
            raise JoinRefused(f"the native fact holds an output item of unknown kind {kind!r}")
    return texts, tools


def join(fact: dict, stream_text: str) -> dict:
    """The joined interaction, or JoinRefused. `fact` is one element of gemini_projection.project's list."""
    native_texts, native_tools = _native(fact)
    call = read_call(stream_text)
    if call["init_session"] is None or call["init_session"] != fact.get("session_id"):
        raise JoinRefused("session identity disagrees: the stream's init session_id is not the native sessionId")
    segments = [s for s in (gp.recorder_normalize(r) for r in call["responses"]) if s]
    if segments != native_texts:
        raise JoinRefused("recorded text disagrees: the stream's normalized responses are not the native segments")
    if call["tools"] != [t[:3] for t in native_tools]:
        raise JoinRefused("tool facts disagree (id, name, order or status)")
    if [_canonical(a) for a in call["args"]] != [t[3] for t in native_tools]:
        raise JoinRefused("tool arguments disagree (the stream's parameters against the native args, as exact JSON)")
    if call["sent"] is not None and call["sent"] != fact.get("sent"):
        raise JoinRefused("sent text disagrees")
    if call["init_model"] is not None and fact.get("requested_model") is not None \
            and call["init_model"] != fact["requested_model"]:
        raise JoinRefused("model disagrees between the stream init and the native session")
    terminal = call["terminal"]
    return {"complete": terminal["status"] == tg.SUCCESS, "terminal_status": terminal["status"],
            "terminal_error": terminal["error"], "errors": call["errors"], "segments": segments,
            "tools": call["tools"], "sent": call["sent"], "init_model": call["init_model"]}
