#!/usr/bin/env python3
"""The Claude Code adapter for round 4's box (lane w6j, slice S6c, C15; s6b-checker-body-plan-2026-10-11, ruling D7).

`ClaudeCodeAdapter` is agent_adapter's interface for `claude-code`: one `docker exec` per turn into the kept-alive take
container (box/run_take.run_turn), the turn's stream-json stdout written host-side at the driver's stream path, and a
`TurnResult` read from that stream's harness-side records. It never calls a model itself: the turn's argv runs the CLI
inside the box, and every test drives it on a fake runtime with recorded or synthetic streams.

THE ARGV (round 3's drive.py:718-732 one_turn, with the plan's named changes for arms A and C, CP2 "UPDATE drive.py"):

    claude -p <line> --output-format stream-json --verbose --permission-mode <the routing pin's mode>
           --permission-prompts none --model <the row's model> --setting-sources project,local --strict-mcp-config
           --disallowedTools WebFetch WebSearch (--session-id <id> on the first turn | --resume <id> after)

  C15-1  The permission mode is the take's routing pin (ruling D1), never a module constant; a PENDING or absent mode
         refuses the adapter's making (a take never runs under a mode nobody pinned).
  C15-2  No `--allowedTools` (round 3's change 1 is retired for the box: "Arms A and C: bypass mode inside the box, no
         --allowedTools, --disallowedTools WebFetch WebSearch").
  C15-3  The session id is imposed (round 3: uuid5 of the row commit, takes.session_id_for); the adapter is given it.

THE RECORDS READ, AND WHERE THEIR SHAPES WERE VERIFIED (no field below is read on a guess):

  stream-json, harness 2.1.267, recorded: evals/haiku-prestudy/verification/probes/*.jsonl (real `claude -p
  --output-format stream-json --verbose` stdout, committed by the prestudy); round 3's readers stream_split and
  stream_init_source (drive.py:453-530); the API-error probe evals/gap-study/verification/api-error-stream-probe.txt.

    system/init   model, permissionMode, claude_code_version, apiKeySource, session_id, tools
    assistant     message.id, request_id, message.model, message.content[] (text / tool_use / thinking blocks),
                  session_id; the harness's own API-error record: is_api_error_message true, model `<synthetic>`,
                  `error` (its type, e.g. model_not_found), its words in text blocks
    result        subtype, is_error, result, total_cost_usd, usage, modelUsage, num_turns, permission_denials
                  ([{tool_name, tool_use_id, tool_input}]), api_error_status, session_id
                  UNEVIDENCED (W6J-R1-4): every recorded result is subtype success with is_error false and
                  api_error_status null. read_stream's error-result branch (is_error true or an `error...` subtype,
                  typed by the subtype) and its `error` key are round 3's stream_split reading, not seen in a
                  recording at 2.1.267; they stay unevidenced until CP6 records an error result.

  session file (the transcript the harness writes under CLAUDE_CONFIG_DIR/projects), harness 2.1.267, recorded:
  evals/gap-study-2/verification/env-smoke/tmpdir/transcript.jsonl: assistant records carry sessionId, requestId,
  message.id, message.model, message.usage, and one record per content block, each with the whole call's usage.

MEASURED, AND WHY TOKENS ARE READ FROM THE SESSION FILE (C14). In the recorded streams each assistant record's
`message.usage.output_tokens` is the count at the reply's start (3 and 4 on the haiku driver-argv probe), while the
turn's result record totals 286 output tokens: the stream does not carry a call's final output count. The session
file's records do (195 on the env-smoke turn, equal across its call's records). So a call's tokens are read once per
(message.id, requestId) from the session file (the 2 Oct correction's key: rounds 1-3 summed records, 1.98 times too
high), the stream's call set is cross-checked against it (C6), and `total_cost_usd` is the turn's own result record's
printed figure: Claude Code prints no dollar figure per API call, so none is derived, and nothing is summed from a
total. The result's `usage` and `modelUsage` (which holds the harness's side calls on other models) are kept as
printed, beside the calls, never added to them.

Standard library only. No model, vendor, network or credential is touched by anything in this module.
"""

from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import agent_adapter as aa  # noqa: E402
import harness_bookkeeping as hb  # noqa: E402
from box import run_take as rt  # noqa: E402

NAME = hb.CLAUDE_CODE
CLIENT = "claude"
OUTPUT_FLAGS = ("--output-format", "stream-json", "--verbose")
PERMISSION_PROMPTS = ("--permission-prompts", "none")
# Round 3's isolation flags (drive.py:165, ISOLATION_FLAGS), carried unchanged; a test binds the two.
ISOLATION_FLAGS = ("--setting-sources", "project,local", "--strict-mcp-config")
# The isolation ruling (glitch-6b, 15 Oct 2026; box lane run_take.ISOLATION_DISALLOWED_TOOLS, read from the pinned
# binary): RemoteTrigger, SendMessage and ListAgents are denied for every claude-code take; run_take refuses a turn
# whose argv denies fewer. Spelled here because a tree's run_take may predate box db7c0d14; where run_take carries
# the tuple, tests/test_claude_code_adapter.py binds the two (the box lane's patch read rt's directly).
ISOLATION_DENIED_TOOLS = ("RemoteTrigger", "SendMessage", "ListAgents")
DISALLOWED_TOOLS = ("WebFetch", "WebSearch", *ISOLATION_DENIED_TOOLS)
VERSION_ARGV = (CLIENT, "--version")
# `claude --version`'s printed form at 2.1.267 ("2.1.267 (Claude Code)", the env-smoke report's claude_version).
VERSION_FORM = re.compile(r"([0-9]+\.[0-9]+\.[0-9]+) \(Claude Code\)")

# The stream's record vocabulary (recorded; see the module docstring).
INIT_TYPE, INIT_SUBTYPE = "system", "init"
INIT_FIELD_KEYS = {"model": "model", "permission_mode": "permissionMode", "version": "claude_code_version"}
API_KEY_SOURCE = "apiKeySource"
API_ERROR_FLAG = "is_api_error_message"
SYNTHETIC_MODEL = "<synthetic>"
RESULT_KEYS = ("subtype", "is_error", "total_cost_usd", "usage", "modelUsage", "num_turns", "permission_denials",
               "api_error_status")
USAGE_CLASSES = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
DENIAL_KEYS = ("tool_name", "tool_use_id")     # what the ledger keeps of a denial: never the tool's input


class StreamError(ValueError):
    """A stream or session file the reader cannot use as it stands (a typed refusal, never a guess)."""


class ExecutedStreamRefused(StreamError, aa.ExecutedTurnRefused):
    """Drive-wiring review MINOR 3: a turn's stream refused after its exec ran (a modelless or ill-shaped record): an
    executed turn's refusal (the driver accounts for the turn and stops for a ruling), still a StreamError for this
    module's own callers."""

    def __init__(self, message, *, executed):
        aa.ExecutedTurnRefused.__init__(self, message, executed=executed)


# glitch-b5's ruling on review r8's finding 1 (16 Oct 2026): str.splitlines() also splits on these, and Claude Code's
# writer (JSON.stringify) leaves exactly U+2028, U+2029 and U+0085 raw inside strings (it escapes the C0 ones), so a
# record carrying one was dropped (a reached wait point read did-not-reach). The driver fails closed: a stream or
# session text carrying any of them refuses (StreamError, after the exec an executed turn's refusal), and every JSONL
# text here splits on "\n" alone. On the real road this end refuses U+2028, U+2029 and U+0085, and the C0 ones only
# when they reach it untranslated: box/run_take captures the turn's stdout with universal newlines (review r9), so a
# \r becomes \n before the stream file is written, and the session file is read the same way. The \r entry is kept as
# harmless defence in depth; \r is the checker's to refuse (check_take.transcript_line_problems reads the bytes).
# SUPERSEDED IN PART (lane pf1-l3, the lane orchestrator's ruling on the closure check of 8cf492b2, 24 Oct 2026):
# U+2028, U+2029 and U+0085 are legal inside a JSON string, and every reader here splits JSONL on "\n" alone, so a
# record carrying one is read whole, never dropped and never refused: the refusal let an agent void and re-run its own
# take by printing one character. Only the C0 separators stay refused (raw, they are never legal inside a JSON string).
JSON_STRING_SEPARATORS = ("\x85", "\u2028", "\u2029")       # read as text, split on "\n" alone
LINE_SEPARATORS = ("\r", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e")


def _records(text: str) -> tuple[list, int]:
    """(the JSON object records of a JSONL text in order, the count of lines that were not one); a text carrying a
    line separator other than newline refuses (StreamError)."""
    if any(s in (text or "") for s in LINE_SEPARATORS):
        found = sorted({f"U+{ord(s):04X}" for s in LINE_SEPARATORS if s in text})
        raise StreamError(f"the text carries line separator(s) {', '.join(found)} other than newline: refused, never "
                          f"split")
    out, bad = [], 0
    for raw in (text or "").split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(rec, dict):
            out.append(rec)
        else:
            bad += 1
    return out, bad


def _blocks(rec: dict) -> list:
    content = (rec.get("message") or {}).get("content") if isinstance(rec.get("message"), dict) else None
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _is_api_error(rec: dict) -> bool:
    msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
    return rec.get(API_ERROR_FLAG) is True or msg.get("model") == SYNTHETIC_MODEL


def _texts(rec: dict) -> list:
    return [b.get("text") for b in _blocks(rec) if b.get("type") == "text" and isinstance(b.get("text"), str)]


def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def read_stream(text: str) -> dict:
    """One turn's stream-json, read for its harness-side records and the agent's words, kept apart (round 3's
    stream_split, review 15 blocker 3 and review 16 blocker 2).

    init            the first system/init record's {model, permission_mode, version} (agent_adapter.INIT_FIELDS), or
                    None when the turn has none or it lacks one of them as a string
    init_extra      that record's apiKeySource (None when not a string: never the word "none" of our own),
                    session_id and tools
    inits           how many init records the turn holds
    agent_text      the text blocks of the agent's own assistant records (never an API-error record's)
    agent_output    True when an agent assistant record holds a non-blank text block or a tool_use block (the CP2
                    first-turn rule, the same as check_take.agent_output_count)
    api_errors      every API-error record, in order: {status, type, text}; an assistant API-error record's type is
                    its `error`, its text its words; a result record with is_error true adds one more, typed by its
                    subtype, with the result's own words; status is the result's api_error_status when an int
    calls           [{message_id, request_id, model}] per distinct (message.id, request_id) of the agent's records
    served_models   the distinct message.model of every agent assistant record, in order (the harness's own API-error
                    record, model <synthetic>, is never one); an agent record whose message.model is not a non-empty
                    string refuses (StreamError): an unknown shape is never read as the pin's model
    model_usage     the result record's modelUsage keys, in order, or None when the turn has no result or the result
                    carries no modelUsage; a modelUsage that is not an object of objects refuses (StreamError)
    tool_use_ids    every tool_use block id the agent's records hold, in order
    result          the result record's RESULT_KEYS (absent keys None; permission_denials kept as {tool_name,
                    tool_use_id}), or None when the turn has no result record (a cut or dead turn)
    session_ids     the distinct session_id values the stream's records carry
    undecoded       lines that were not a JSON object
    """
    recs, bad = _records(text)
    init, extra, inits = None, {"api_key_source": None, "session_id": None, "tools": None}, 0
    said, harness, output, api, calls, tools, result, sids = [], [], False, [], [], [], None, []
    seen_calls = set()
    status = None
    models, usage = [], None
    for rec in recs:
        if rec.get("type") == "result" and _int(rec.get("api_error_status")):
            status = rec["api_error_status"]
    subs, sub_models = [], []
    for rec in recs:
        sid = rec.get("session_id")
        if isinstance(sid, str) and sid not in sids:
            sids.append(sid)
        kind = rec.get("type")
        parent = rec.get("parent_tool_use_id")
        if parent is None and kind in SUBAGENT_RECORD_TYPES and rec.get("agent_id") is not None:
            raise StreamError("a record carries an agent_id and no parent_tool_use_id: neither the agent's nor a "
                              "sub-agent's (review r10 NIT)")
        if parent is not None and kind in SUBAGENT_RECORD_TYPES:
            subs.append(_subagent_record(rec, parent))
            if subs[-1]["api_error"]:                 # review r10 F3: routed as the agent's own API errors are
                words = "\n".join(t for t in _texts(rec) if t)
                harness.append(words)
                api.append({"status": status, "type": rec.get("error") if isinstance(rec.get("error"), str)
                            else None, "text": words or None})
            elif subs[-1]["model"] is not None and subs[-1]["model"] not in sub_models:
                sub_models.append(subs[-1]["model"])
            continue
        if kind == INIT_TYPE and rec.get("subtype") == INIT_SUBTYPE:
            inits += 1
            if inits == 1:
                vals = {f: rec.get(k) for f, k in INIT_FIELD_KEYS.items()}
                init = vals if all(isinstance(v, str) and v for v in vals.values()) else None
                src = rec.get(API_KEY_SOURCE)
                extra = {"api_key_source": src if isinstance(src, str) else None,
                         "session_id": sid if isinstance(sid, str) else None,
                         "tools": list(rec["tools"]) if isinstance(rec.get("tools"), list) else None}
            continue
        if kind == "assistant":
            if _is_api_error(rec):
                words = "\n".join(t for t in _texts(rec) if t)
                harness.append(words)
                api.append({"status": status, "type": rec.get("error") if isinstance(rec.get("error"), str)
                            else None, "text": words or None})
                continue
            texts = _texts(rec)
            said.extend(t for t in texts if t)
            blocks = _blocks(rec)
            if any((b.get("type") == "text" and (b.get("text") or "").strip()) or b.get("type") == "tool_use"
                   for b in blocks):
                output = True
            tools.extend(b.get("id") for b in blocks if b.get("type") == "tool_use")
            msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
            served = msg.get("model")
            if not isinstance(served, str) or not served:     # the served-model backstop reads every agent message
                raise StreamError(f"an agent assistant record names no model ({served!r}): an unknown shape")
            if served not in models:
                models.append(served)
            key = (msg.get("id"), rec.get("request_id"))
            if key not in seen_calls:
                seen_calls.add(key)
                calls.append({"message_id": key[0], "request_id": key[1], "model": msg.get("model")})
            continue
        if kind == "result":
            result = {k: rec.get(k) for k in RESULT_KEYS}
            mu = rec.get("modelUsage")
            if mu is not None and (not isinstance(mu, dict) or not all(isinstance(k, str) and k and isinstance(v, dict)
                                                                      for k, v in mu.items())):
                raise StreamError("the result's modelUsage is not an object of per-model objects: an unknown shape")
            usage = None if mu is None else list(mu)
            denials = rec.get("permission_denials")
            result["permission_denials"] = ([{k: d.get(k) for k in DENIAL_KEYS} for d in denials
                                             if isinstance(d, dict)] if isinstance(denials, list) else None)
            if (rec.get("is_error") is True or str(rec.get("subtype") or "").startswith("error")):
                words = "\n".join(str(rec.get(k)) for k in ("result", "error") if rec.get(k))
                harness.append(words)
                api.append({"status": status, "type": rec.get("subtype") if isinstance(rec.get("subtype"), str)
                            else None, "text": words or None})
    # glitch-b5's ruling R-B: a sub-agent record whose parent call is not one of this turn's own calls was written by a
    # sub-agent still running after its turn ended (or a stray): the turn is never read as complete
    late = [s for s in subs if s["parent_tool_use_id"] not in tools]
    nested_parents = {t["id"] for s in subs for t in s["tool_uses"]}
    if any(s["parent_tool_use_id"] in nested_parents for s in late):
        raise StreamError("a sub-agent record answers a call a sub-agent made: a nested sub-agent, which this reader "
                          "does not read (refused for a ruling)")
    if late:
        raise StreamError(f"{len(late)} sub-agent record(s) answer a call this turn's agent did not make (first parent "
                          f"{late[0]['parent_tool_use_id']!r}): a sub-agent of an earlier turn wrote after its turn "
                          f"ended")
    return {"init": init, "init_extra": extra, "inits": inits, "agent_text": "\n".join(said),
            "harness_text": "\n".join(h for h in harness if h), "agent_output": output, "api_errors": api,
            "calls": calls, "tool_use_ids": tools, "result": result, "session_ids": sids, "undecoded": bad,
            "served_models": models, "model_usage": usage, "subagent_records": subs, "subagent_models": sub_models}


# glitch-b5's Agent parity ruling (16 Oct 2026, part 4): an assistant or user stream record with parent_tool_use_id set
# is a sub-agent's (a harness event such as tool_progress also names the call it reports on, and is not; the recorded
# haiku probe carries one) (w083's turn 1: 38 of them, types assistant and user, keyed agent_id, message, parent_tool_use_id, request_id,
# session_id, subagent_type, task_description, timestamp, tool_result_meta, tool_use_result, type, uuid). Its words
# never count toward a wait point or the agent's visible output, and its calls never join the main calls the
# cross-check compares; the checker reads its tool calls for every reach check.
SUBAGENT_RECORD_TYPES = ("assistant", "user")


def _subagent_record(rec: dict, parent) -> dict:
    """One sub-agent stream record: {type, agent_id, parent_tool_use_id, model, tool_uses: [{id, name, input}]}; a
    parent id that is not a string, or an assistant record with no model, refuses (StreamError)."""
    kind = rec.get("type")
    if not isinstance(parent, str) or not parent:
        raise StreamError("a sub-agent record whose parent_tool_use_id is not a non-empty string")
    msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
    model = msg.get("model")
    api_error = kind == "assistant" and _is_api_error(rec)      # review r10 F3: the harness's words, never a model
    if kind == "assistant" and not api_error and (not isinstance(model, str) or not model):
        raise StreamError(f"a sub-agent assistant record names no model ({model!r}): an unknown shape")
    agent = rec.get("agent_id")
    return {"type": kind, "agent_id": agent if isinstance(agent, str) else None, "parent_tool_use_id": parent,
            "model": model if kind == "assistant" and not api_error else None, "api_error": api_error,
            "tool_uses": [{"id": b.get("id"), "name": b.get("name"), "input": b.get("input")}
                          for b in _blocks(rec) if b.get("type") == "tool_use"]}


# Review MINOR 5 (glitch-06's ruling, 14 Oct 2026): a modelUsage key beside the pin's is a side call only for a model on
# this closed list (the one observed: the recorded sonnet probe's claude-haiku-4-5-20251001, Claude Code's small and
# fast model); any other extra key is a mismatch. The side calls' token counts are recorded (side_calls).
SIDE_MODELS = ("claude-haiku-4-5-20251001",)
# A first-walk acceptance item (the same ruling): a turn that uses the Agent tool shows its subagent's assistant records
# in the 2.1.296 stream (parent_tool_use_id set), each carrying message.model; until a walk shows it, a subagent on
# another model may leave only a modelUsage key, which the closed list above then reads as a mismatch.
FIRST_WALK_ACCEPTANCE = ("a turn that uses the Agent tool shows its subagent's assistant records in the 2.1.296 "
                         "stream (parent_tool_use_id set), each carrying message.model",)
# glitch-b5's ruling R-C (16 Oct 2026): a sub-agent runs on the pin's model (every built-in agent type inherits at
# these arms: Explore and Plan by "inherit", general-purpose and claude by no model field; statusline-setup names
# sonnet) or, by the Agent tool's model input, on an explicit choice. The explicit ids admitted are 2.1.296's
# first-party alias ids (its baked model catalog's aliases: opus, sonnet, haiku; fable is not admitted); anything
# else stops the take (subagent_model_off). The models a turn's sub-agents served are recorded per take.
SUBAGENT_EXPLICIT_MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")


def subagent_model_off(read: dict, model: str):
    """The first sub-agent model this turn served that is neither the pin's nor in SUBAGENT_EXPLICIT_MODELS, else
    None."""
    for m in read.get("subagent_models") or ():
        if m != model and m not in SUBAGENT_EXPLICIT_MODELS:
            return m
    return None


def admitted_subagent_models(read: dict, model: str) -> set:
    """The sub-agent models this turn served that are admitted: a modelUsage key for one is a sub-agent's, not a
    switch or an unlisted side model."""
    return {m for m in read.get("subagent_models") or () if m == model or m in SUBAGENT_EXPLICIT_MODELS}


def side_calls(read: dict, model: str) -> dict:
    """{side model: {inputTokens, outputTokens}} for the result's modelUsage keys beside the pin's (as printed)."""
    usage = (read.get("result") or {}).get("modelUsage") or {}
    return {k: {t: _count(v.get(t)) for t in ("inputTokens", "outputTokens")} for k, v in usage.items()
            if k != model and isinstance(v, dict)}


def _count(v):
    """A token count as printed, kept only when it is an int (never a bool); anything else, stream text included, is
    None (review MINOR 2: no stream text rides a refusal or a record through a count)."""
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def served_model_off(read: dict, model: str):
    """THE SERVED-MODEL BACKSTOP (ownership review MAJOR 1, glitch-06, 14 Oct 2026): routing compares each turn's init
    model with the pin, so a switch after an init that carried the pin would pass. The first model the turn served
    that is not the pin's `model`, else None:
      - every agent assistant record's message.model (read_stream's served_models) must be the pin's model;
      - the result's modelUsage, when present and the turn made an agent call, must name the pin's model.
    A key BESIDE the pin's in modelUsage is a side call only for a model on SIDE_MODELS (glitch-06's ruling on review
    MINOR 5): the recorded sonnet probe (haiku-prestudy/verification/probes/claude-sonnet-5.auto.jsonl) carries
    claude-haiku-4-5-20251001 there (915 in, 11 out) while each of its assistant records is claude-sonnet-5; any other
    extra key is a mismatch, and the side calls' tokens are recorded (side_calls)."""
    for m in read["served_models"]:
        if m != model:
            return m
    usage = read["model_usage"]
    # review MINOR 1: a modelUsage that omits the pin's model is a switch whether or not the turn has assistant records
    if usage is not None and ((read["served_models"] and model not in usage) or (usage and model not in usage)):
        others = [k for k in read["model_usage"] if k != model]
        return others[0] if others else "<modelUsage names no model>"
    subagents = admitted_subagent_models(read, model)          # glitch-b5's ruling R-C: a sub-agent's own usage
    for k in read["model_usage"] or ():
        if k in subagents:
            continue
        if k != model and k not in SIDE_MODELS:     # a side key off the closed list is a mismatch
            return k
    return None


def unlisted_side_model(read: dict, model: str):
    """glitch-06's ruling (14 Oct 2026, window 2) on departure D-INT-2c: a side call off SIDE_MODELS stops the take and
    is reported. The first modelUsage key beside the pin's that is off SIDE_MODELS, on a turn whose served models are
    all the pin's and whose modelUsage names the pin's (when it served any): a side model, not a switch. A switch (an
    assistant record on another model, or a modelUsage without the pin's) is None here: the init-mismatch route."""
    usage = read["model_usage"] or ()
    if any(m != model for m in read["served_models"]) or (read["served_models"] and model not in usage) or \
            (usage and model not in usage):            # review MINOR 1: a modelUsage without the pin's is a switch
        return None
    subagents = admitted_subagent_models(read, model)          # glitch-b5's ruling R-C: a sub-agent's own usage
    for k in usage:
        if k in subagents:
            continue
        if k != model and k not in SIDE_MODELS:
            return k
    return None


SIDE_KEY_REPR_MAX = 120     # review MINOR 2: a side key is stream text; its repr in a refusal is capped


class SideModelOffList(RuntimeError):
    """A turn called a side model off SIDE_MODELS: the take stops for a ruling (an executed turn's refusal)."""


class SubagentModelOffList(RuntimeError):
    """A turn's sub-agent ran on a model off the admitted list: the take stops for a ruling (an executed turn's
    refusal)."""


def argv(line: str, *, model: str, permission_mode: str, session_id: str, first: bool) -> list:
    """The turn's argv inside the box (C15-1..3)."""
    for what, v in (("line", line), ("model", model), ("permission_mode", permission_mode),
                    ("session_id", session_id)):
        if not isinstance(v, str) or not v:
            raise StreamError(f"the turn's {what} must be a non-empty string")
    out = [CLIENT, "-p", line, *OUTPUT_FLAGS, "--permission-mode", permission_mode, *PERMISSION_PROMPTS,
           "--model", model, *ISOLATION_FLAGS, rt.CLAUDE_SETTINGS_FLAG, rt.claude_study_settings(model),
           "--disallowedTools", *DISALLOWED_TOOLS]
    out += ["--session-id", session_id] if first else ["--resume", session_id]
    return out


def end_reason(exit_code, timed_out: bool) -> str:
    """How the host saw the turn end: timed-out, end_turn on exit 0, else error (agent_adapter.END_REASONS)."""
    if timed_out:
        return aa.END_TIMED_OUT
    return aa.END_TURN if exit_code == 0 else aa.END_ERROR


class ClaudeCodeAdapter(aa.AgentAdapter):
    """C15: one take's Claude Code turns in the box.

    runtime          run_take's runtime protocol
    take_id          the take container's recorded id
    run_tree         the take's run tree (the exec's working folder)
    login_file       the login file run_take.read_login reads at exec time (its value never reaches argv)
    session_id       the imposed session id (takes.session_id_for of the row's commit)
    model            the row's model
    pin              the take's routing pin (batch.expected_pin): its permission_mode is passed (C15-1)
    stream_path_for  (n) -> the host-side path turn n's stream is written at (drive.stream_path)
    counters_for     () -> run_take.counters(cgroup_dir): the take container's cgroup counters, read host-side
    clock            the injected host clock

    `turn_records` holds, per turn, what the TurnResult has no field for: the exit and timeout as run_turn returned
    them, the init's apiKeySource, session id and tools, the calls and tool ids the stream holds, its result record,
    the session ids its records carry and the lines that did not decode. The driver writes them into its ledger
    (C7), its environment record (C8) and its cost record (C14).
    """

    name = NAME

    def __init__(self, *, runtime, take_id: str, run_tree: str, login_file: str, session_id: str, model: str,
                 pin: dict, stream_path_for, counters_for, clock, caller_env=None):
        super().__init__()
        mode = (pin or {}).get("permission_mode") if isinstance(pin, dict) else None
        if not isinstance(mode, str) or not mode or rt._is_pending(mode):
            raise rt.NotReady(f"the take's routing pin holds no permission mode ({mode!r}): no take runs under a "
                              f"mode nobody pinned")
        for name, fn in (("stream_path_for", stream_path_for), ("counters_for", counters_for), ("clock", clock)):
            if not callable(fn):
                raise TypeError(f"{name} must be callable")
        self.runtime, self.take_id, self.run_tree, self.login_file = runtime, take_id, run_tree, login_file
        self.session_id, self.model, self.permission_mode = session_id, model, mode
        self.stream_path_for, self.counters_for, self.clock = stream_path_for, counters_for, clock
        self.caller_env = caller_env
        self._version = None
        self.turn_records: list = []
        self.executed_turns: list = []      # review MINOR 3: each exec's outcome, kept before its stream is read

    def version(self) -> str:
        """`claude --version` in the take container, as the agent (a plain exec: no login, no variable), parsed by
        its recorded form; cached. A version that does not parse refuses, never a default."""
        if self._version is None:
            c = self.runtime.run(rt.agent_exec_argv(self.take_id, list(VERSION_ARGV)),
                                 env=rt.runtime_env(self.caller_env), timeout=rt.STEP_TIMEOUT_S)
            m = VERSION_FORM.fullmatch((c.stdout or "").strip()) if c.returncode == 0 else None
            if m is None:
                raise rt.NotReady(f"`claude --version` exited {c.returncode} with no version in its recorded form")
            self._version = m.group(1)
        return self._version

    def _start(self, take: dict) -> dict:
        return {"container_id": self.take_id}

    def _turn(self, line: str, *, first: bool, budget_s: float) -> aa.TurnResult:
        n = self._turns + 1
        inner = argv(line, model=self.model, permission_mode=self.permission_mode, session_id=self.session_id,
                     first=first)
        before = self.counters_for()
        got = rt.run_turn(self.runtime, self.take_id, inner, harness=NAME, run_tree=self.run_tree,
                          login_file=self.login_file, stream_path=self.stream_path_for(n), budget_s=budget_s,
                          clock=self.clock, caller_env=self.caller_env)
        self.__dict__.setdefault("stderr_seen", []).append(got["stderr"])   # R15-2: EROFS evidence (run_turn: a str)
        after = self.counters_for()
        counters = rt.counter_delta(before, after)
        # Review MINOR 3 (live harness 3a's pattern, as Gemini and Codex): the exec ran, so its outcome is kept before
        # the stream is read; a refusal from here on is an executed turn's, never a turn that did not happen.
        executed = {"n": n, "exit_code": got["exit_code"], "timed_out": got["timed_out"],
                    "started_at": got["started_at"], "ended_at": got["ended_at"], "stream_path": got["stream_path"],
                    "counters": counters, "refused": None}
        self.executed_turns.append(executed)
        try:
            with open(got["stream_path"], encoding="utf-8", errors="surrogateescape", newline="") as fh:
                stream_text = fh.read()
            read = read_stream(stream_text)
            off = served_model_off(read, self.model)
            side = unlisted_side_model(read, self.model)
            sub_off = subagent_model_off(read, self.model)
            if sub_off is not None:                    # glitch-b5's ruling R-C: stops the take for a ruling
                raise SubagentModelOffList(f"turn {n}'s sub-agent ran on {repr(sub_off)[:SIDE_KEY_REPR_MAX]}, neither "
                                           f"the pin's model nor one of {list(SUBAGENT_EXPLICIT_MODELS)}: the take "
                                           f"stops for a ruling (glitch-b5, 16 Oct 2026)")
            if side is not None:                       # D-INT-2c: stops the take, its tokens in the refusal
                raise SideModelOffList(f"turn {n} called side model {repr(side)[:SIDE_KEY_REPR_MAX]}, not on "
                                       f"SIDE_MODELS {list(SIDE_MODELS)}; "
                                       f"its tokens {side_calls(read, self.model).get(side)}: "
                                       f"the take stops for a ruling (glitch-06, 14 Oct 2026)")
        except (StreamError, OSError) as e:
            executed["refused"] = f"{type(e).__name__}: {e}"
            raise ExecutedStreamRefused(str(e), executed=executed) from e
        except Exception as e:  # noqa: BLE001 - any other failure after the exec is still the exec's
            executed["refused"] = f"{type(e).__name__}: {e}"
            raise aa.ExecutedTurnRefused(executed["refused"], executed=executed) from e
        # The init as routed: the init event's fields, its model the first served model off the pin when there is
        # one, so routing's init-mismatch row (after turn 1) or pin refusal (before it) reads the switch.
        init = read["init"] if off is None or read["init"] is None else dict(read["init"], model=off)
        self.turn_records.append({
            "n": n, "first": first, "exit_code": got["exit_code"], "timed_out": got["timed_out"],
            "api_key_source": read["init_extra"]["api_key_source"], "init_session_id": read["init_extra"]["session_id"],
            "tools": read["init_extra"]["tools"], "inits": read["inits"], "calls": read["calls"],
            "tool_use_ids": read["tool_use_ids"], "result": read["result"], "session_ids": read["session_ids"],
            "undecoded": read["undecoded"], "served_models": read["served_models"],
            "model_usage": read["model_usage"], "served_off": off, "side_calls": side_calls(read, self.model),
            "content_units": stream_content_units(stream_text)})   # PF1-L3: what C6 compares with the session file
        return aa.TurnResult(exit_code=got["exit_code"], text=read["agent_text"], stream_path=got["stream_path"],
                             end_reason=end_reason(got["exit_code"], got["timed_out"]), init=init,
                             api_errors=read["api_errors"], counters=counters,
                             started_at=got["started_at"], ended_at=got["ended_at"],
                             agent_output=read["agent_output"])

    def _end(self) -> None:
        """Nothing of the adapter's own to tear down: the driver removes the container by its recorded id."""
        return None


# ---- C14: the calls, counted once each, from the session file ---------------------------------------------------
# Lane pf1-l4-close (25 Oct 2026; the lane orchestrator's ruling on review REVIEW-pf1-l4-close-291b357 M1): Claude Code
# records each call's cache writes by duration in usage.cache_creation (ephemeral_5m_input_tokens and
# ephemeral_1h_input_tokens; every usage record of the 151 committed Claude walks carries both, summing to
# cache_creation_input_tokens), which costs.py prices each at its own row.
CACHE_SPLIT_KEYS = {"5m": "ephemeral_5m_input_tokens", "1h": "ephemeral_1h_input_tokens"}


def cache_write_split(usage: dict, counts) -> dict | None:
    """{"5m": n, "1h": n} as the usage record states it, or None (unrecorded) when the counts are unmeasured, the
    record carries no cache_creation object, a duration is not a count, or the two do not sum to the call's cache
    writes: costs.py then prices the whole at the stated bound, never a guessed split."""
    detail = usage.get("cache_creation")
    if counts is None or not isinstance(detail, dict):
        return None
    split = {d: detail.get(k) for d, k in CACHE_SPLIT_KEYS.items()}
    if not all(_int(v) and v >= 0 for v in split.values()) or sum(split.values()) != counts[
            "cache_creation_input_tokens"]:
        return None
    return split


def session_calls(text: str) -> list:
    """The session file's model calls, one per (message.id, requestId), in order: {message_id, request_id, model,
    usage, cache_write_durations (cache_write_split)}. usage holds the four USAGE_CLASSES as recorded, or is None when any of them is not a count (unmeasured,
    never 0: costs.py reads None as unmeasured). The harness's API-error records are not calls of the model. Two
    records of one call with different usage, or a usage record with no call key, refuse (StreamError): the reader
    never picks one."""
    recs, _ = _records(text)
    out, by_key = [], {}
    for rec in recs:
        if rec.get("type") != "assistant" or rec.get("isApiErrorMessage") is True or _is_api_error(rec):
            continue
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
        usage = msg.get("usage")
        if not isinstance(usage, dict):
            continue
        key = (msg.get("id"), rec.get("requestId"))
        if not all(isinstance(k, str) and k for k in key):
            raise StreamError("a session record carries usage with no (message.id, requestId) key")
        counts = {c: usage.get(c) for c in USAGE_CLASSES}
        if not all(_int(v) and v >= 0 for v in counts.values()):
            counts = None
        split = cache_write_split(usage, counts)
        if key in by_key:
            if (by_key[key]["usage"] != counts or by_key[key]["model"] != msg.get("model")
                    or by_key[key]["cache_write_durations"] != split):
                raise StreamError(f"call {key[0]} carries two different usages or models in the session file")
            continue
        call = {"message_id": key[0], "request_id": key[1], "model": msg.get("model"), "usage": counts,
                "cache_write_durations": split}
        by_key[key] = call
        out.append(call)
    return out


# ---- C6: the stream cross-checked against the session file ------------------------------------------------------
def cross_check(turn_records: list, session_text: str, *, session_id: str) -> list:
    """C6: the host-captured streams against the session file copied out of the config folder. Problems, each one
    sentence (empty when they agree):

      - every stream record's session id, and every session record's sessionId, is the imposed id;
      - the set of model calls (message.id, request id) the streams hold equals the session file's, and each call's
        model is the same in both (a dropped turn, an extra call, a different model id);
      - the tool_use ids the streams hold equal the session file's (an extra or missing tool call).
    """
    out = []
    try:
        recs, _ = _records(session_text)
    except StreamError as e:
        return [str(e)]
    raw_sids = [r.get("sessionId") for r in recs if "sessionId" in r]
    bad = sum(1 for x in raw_sids if not isinstance(x, str))      # W6J-R1-2: a null id is a problem, never a crash
    if bad:
        out.append(f"{bad} session record(s) carry a session id that is not a string")
    sids = sorted({x for x in raw_sids if isinstance(x, str)})
    if sids != [session_id]:
        out.append(f"the session file carries session ids {sids}, not the imposed {session_id}")
    stream_sids = sorted({s for t in turn_records for s in t["session_ids"]})
    if stream_sids and stream_sids != [session_id]:
        out.append(f"the streams carry session ids {stream_sids}, not the imposed {session_id}")
    try:
        sess = session_calls(session_text)
    except StreamError as e:
        return out + [str(e)]
    stream_calls = {(c["message_id"], c["request_id"]): c["model"] for t in turn_records for c in t["calls"]}
    sess_calls = {(c["message_id"], c["request_id"]): c["model"] for c in sess}
    if set(stream_calls) != set(sess_calls):
        only_s = len(set(stream_calls) - set(sess_calls))
        only_f = len(set(sess_calls) - set(stream_calls))
        out.append(f"the streams and the session file hold different model calls ({only_s} only in the streams, "
                   f"{only_f} only in the session file)")
    else:
        diff = sorted(k[0] for k in stream_calls if stream_calls[k] != sess_calls[k])
        if diff:
            out.append(f"{len(diff)} call(s) carry another model in the session file than in the stream")
    sess_tools = [b.get("id") for r in recs if r.get("type") == "assistant" and not _is_api_error(r)
                  and r.get("isApiErrorMessage") is not True for b in _blocks(r) if b.get("type") == "tool_use"]
    stream_tools = [i for t in turn_records for i in t["tool_use_ids"]]
    if sorted(map(str, sess_tools)) != sorted(map(str, stream_tools)):
        out.append(f"the streams hold {len(stream_tools)} tool call(s) and the session file {len(sess_tools)}, "
                   f"not the same ones")
    # PF1-L3 (MAJOR 7): the content itself, turn by turn and in order, never the ids alone
    units = [t.get("content_units") for t in turn_records]
    missing = sum(1 for u in units if not isinstance(u, list))
    if missing:
        out.append(f"{missing} turn record(s) carry no content units, so the session file's content cannot be "
                   f"compared with the streams")
    else:
        cut = {k for k, t in enumerate(turn_records, 1) if t.get("timed_out") is True or t.get("exit_code") == 124}
        out += content_problems(units, session_text, cut=cut)
    return out


# ---- PF1-L3: the content the graders read, compared with the host-captured streams (pre-freeze review 1, MAJOR 7) ---
# The lane orchestrator's approval of fold plan prefreeze-1 (Sat 24 Oct 2026, under Javier's standing delegation).
# transcript.jsonl is the session file copied out of the config folder, the take's read-write mount owned by the
# agent's uid, and every words-graded reading reads it (transcript_view's claude-code parser). C6 above bound ids
# only, so one in-take command that rewrote a reply's words passed. The units below are what transcript_view reads
# of an agent's text, reasoning, tool calls and tool results, so a change to any of them, in either file, shows:
#     text         (kind, message.id, the block's text)
#     thinking     (kind, message.id, the block's thinking)
#     tool_use     (kind, its id, its name, its input as canonical JSON)
#     tool_result  (kind, tool_use_id, its content as canonical JSON, is_error)
#     other-block  (kind, message.id, its type, the whole block as canonical JSON): any other assistant block
# from the main thread only: a stream record with parent_tool_use_id set (a sub-agent's) and a session record with
# isSidechain true are not the main thread, and the harness's API-error records are no agent content. The session
# file is split into turns at its operator lines (transcript_view's rule: a user record whose content is a string,
# with no origin and no isMeta or isApiErrorMessage key); turn k's units, in order, must equal turn k's stream's, and
# nothing may come before the first operator line. Measured on every committed claude-code walk at 96c1d959 (151 of
# 151 equal, turn by turn, with 1533 thinking, 890 text, 1663 tool_use and 1663 tool_result units); a line that is not
# JSON is skipped here, so a record cut or blanked in the session file is a missing unit (transcript_line_problems
# names the line). Not compared, because the stream does not carry them: attachments, system and bookkeeping records,
# and the sub-agent files (box_residuals names them).
CONTENT_UNIT_KINDS = ("text", "thinking", "tool_use", "tool_result", "other-block")


def _content_records(text: str) -> list:
    """The JSON object records of a JSONL text, split on newline alone; a line that is not one is skipped."""
    out = []
    for raw in (text or "").split("\n"):
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _units(rec: dict) -> list:
    """One main-thread record's content units, in block order."""
    msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
    content = msg.get("content")
    if not isinstance(content, list):
        return []
    if rec.get("type") == "assistant":
        if _is_api_error(rec) or rec.get("isApiErrorMessage") is True:
            return []
        out = []
        for b in content:
            if not isinstance(b, dict):
                continue
            kind = b.get("type")
            if kind == "text":
                out.append(("text", msg.get("id"), b.get("text")))
            elif kind == "thinking":
                out.append(("thinking", msg.get("id"), b.get("thinking")))
            elif kind == "tool_use":       # its message id last: a message's units group by it (third closure check)
                out.append(("tool_use", b.get("id"), b.get("name"), _canonical(b.get("input")), msg.get("id")))
            else:
                out.append(("other-block", msg.get("id"), kind, _canonical(b)))
        return out
    if rec.get("type") == "user":
        return [("tool_result", b.get("tool_use_id"), _canonical(b.get("content")), b.get("is_error") is True)
                for b in content if isinstance(b, dict) and b.get("type") == "tool_result"]
    return []


def stream_content_units(text: str) -> list:
    """One turn stream's main-thread content units, in order (a sub-agent's records, parent_tool_use_id set, left
    out)."""
    return [u for rec in _content_records(text) if rec.get("parent_tool_use_id") is None for u in _units(rec)]


def _is_operator_line(rec: dict) -> bool:
    msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
    return (rec.get("type") == "user" and isinstance(msg.get("content"), str) and "origin" not in rec
            and not any(k in rec for k in ("isMeta", "isApiErrorMessage")))


def session_content_turns(text: str) -> list:
    """The session file's main-thread content units split at its operator lines: [units before the first operator
    line, turn 1's, turn 2's, ...]."""
    turns = [[]]
    for rec in _content_records(text):
        if rec.get("isSidechain") is True:
            continue
        if _is_operator_line(rec):
            turns.append([])
            continue
        turns[-1].extend(_units(rec))
    return turns


def _unit_name(unit) -> str:
    return "nothing" if unit is None else f"{unit[0]} {str(unit[1])[:60]!r}"


def _message_id(unit):
    """The assistant message a unit belongs to (a tool_use unit carries it last), None for a tool_result."""
    if unit[0] == "tool_result":
        return None
    return unit[4] if unit[0] == "tool_use" else unit[1]


def _last_record_length(units: list) -> int:
    """How many of the units' trailing ones are the record in flight: the last tool_result alone (Claude Code writes
    one user record per result), or the assistant message the last unit belongs to, all its blocks (text, thinking,
    tool_use) grouped by its message id (the third closure check of 461dc169, findings 3 and 4)."""
    if not units:
        return 0
    if units[-1][0] == "tool_result":
        return 1
    mid = _message_id(units[-1])
    k = 0
    for u in reversed(units):
        if u[0] == "tool_result" or _message_id(u) != mid:
            break
        k += 1
    return k


def cut_tail_problem(stream: list, sess: list):
    """The second closure check of f0c0eb1d and the lead's ruling on it (24 Oct 2026): in a turn the host records as
    cut the two records may differ only by the record in flight when the kill fell. Everything before the stream's
    last record must be equal; after it the session may hold a prefix of that record's units (it lacks the rest) and
    at most one unit more that the stream lacks. None when that holds, else the sentence naming the difference."""
    g = _last_record_length(stream)
    head = len(stream) - g
    if sess[:head] != stream[:head]:
        i = next((k for k, (a, b) in enumerate(zip(stream[:head], sess[:head])) if a != b), min(head, len(sess)))
        return (f"the session file differs from the host-captured stream at item {i + 1}, before the record in flight "
                f"when the turn was cut")
    rest, last = sess[head:], stream[head:]
    # the third closure check of 461dc169 (finding 1): a unit present in both records has the same content, so the
    # tail is exactly one of two shapes: the session lags (a prefix of the record in flight, unit for unit), or the
    # stream lags (all of it and at most one unit more); any unit that differs in place refuses
    if rest == last[:len(rest)] or (rest[:len(last)] == last and len(rest) == len(last) + 1):
        return None
    if len(rest) > len(last) + 1 and rest[:len(last)] == last:
        return (f"the session file holds {len(rest) - len(last)} item(s) after the record in flight that the stream "
                f"does not, more than the one a cut can leave")
    i = next((k for k, (a, b) in enumerate(zip(rest, last)) if a != b), min(len(rest), len(last)))
    return (f"the session file's record in flight differs from the stream's at its item {i + 1}: a cut drops units, "
            f"it never changes one")


def _turn_line_units(session_text: str) -> list:
    """(turn, units) for each content-bearing main-thread line of the session file, in order (turn 0 before the first
    operator line)."""
    turn, out = 0, []
    for raw in (session_text or "").split("\n"):
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(rec, dict) or rec.get("isSidechain") is True:
            continue
        if _is_operator_line(rec):
            turn += 1
            continue
        got = _units(rec)
        if got:
            out.append((turn, got))
    return out


def unconfirmed_session_lines(stream_texts: list, session_text: str, cut=()) -> set:
    """The session file's line indices (0-based, newline-split) that hold only the one extra unit a cut turn's tail
    may carry when the stream lags: it has no host copy, so nothing the take is graded or classified on reads it (the
    third closure check of 461dc169, finding 2). Empty unless a host-recorded cut turn ends with that shape."""
    units = [stream_content_units(t) for t in stream_texts]
    turn, per_line = 0, []                    # (line index, turn, its units) for each content-bearing line
    for i, raw in enumerate((session_text or "").split("\n")):
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(rec, dict) or rec.get("isSidechain") is True:
            continue
        if _is_operator_line(rec):
            turn += 1
            continue
        got = _units(rec)
        if got:
            per_line.append((i, turn, got))
    out = set()
    for n in sorted(set(cut)):
        if not 1 <= n <= len(units):
            continue
        sess = [u for _, t, us in per_line if t == n for u in us]
        stream = [tuple(u) for u in units[n - 1]]
        if len(sess) != len(stream) + 1 or [tuple(u) for u in sess[:-1]] != stream:
            continue
        lines = [(i, us) for i, t, us in per_line if t == n]
        if lines and len(lines[-1][1]) == 1:
            out.add(lines[-1][0])
    return out


def host_recorded_cuts(folder) -> set:
    """The turns a take folder's driver ledger (host-written) records as cut: end timed-out or exit 124, by each
    row's own n."""
    try:
        with open(os.path.join(str(folder), "driver-ledger.json"), encoding="utf-8") as fh:
            rows = json.load(fh).get("turns") or []
    except (OSError, ValueError, AttributeError):
        return set()
    return {r["n"] for r in rows if isinstance(r, dict) and isinstance(r.get("n"), int) and not isinstance(r["n"], bool)
            and (r.get("end") == "timed-out" or r.get("exit") == 124)}


def confirmed_transcript_text(folder) -> str | None:
    """A claude-code take folder's transcript.jsonl without its unconfirmed lines, or None when it has none."""
    cut = host_recorded_cuts(folder)
    if not cut:
        return None
    base = str(folder)
    with open(os.path.join(base, "transcript.jsonl"), encoding="utf-8") as fh:
        text = fh.read()
    streams = []
    n = 1
    while os.path.isfile(os.path.join(base, f"turn-{n}.jsonl")):
        with open(os.path.join(base, f"turn-{n}.jsonl"), encoding="utf-8", errors="replace") as fh:
            streams.append(fh.read())
        n += 1
    drop = unconfirmed_session_lines(streams, text, cut)
    if not drop:
        return None
    return "\n".join(line for i, line in enumerate(text.split("\n")) if i not in drop)


def content_problems(stream_units: list, session_text: str, cut=()) -> list:
    """PF1-L3: the session file's content against the turn streams' (one list of units per turn, in turn order).
    Problems, each one sentence naming kinds and ids, never the words; [] when every turn's units are equal. A turn in
    `cut` (the host recorded its cut: timed out, exit 124) may differ only by the record in flight when the kill fell
    (cut_tail_problem), since it can fall between the CLI's writes to its stream and to its session file (the lead's
    rulings on the closure checks of 8cf492b2 and f0c0eb1d, 24 Oct 2026)."""
    turns = session_content_turns(session_text)
    out = []
    if turns[0]:
        out.append(f"the session file holds {len(turns[0])} content item(s) before its first operator line, which "
                   f"no turn stream holds")
    if len(turns) - 1 != len(stream_units):
        out.append(f"the session file holds {len(turns) - 1} operator line(s) and the take {len(stream_units)} turn "
                   f"stream(s)")
    for n, (stream, sess) in enumerate(zip(stream_units, turns[1:]), 1):
        if n in set(cut):
            why = cut_tail_problem([tuple(u) for u in stream], [tuple(u) for u in sess])
            if why is None and len(sess) == len(stream) + 1:
                # the fourth closure check of 2ab2c8f5: the one extra unit must sit alone on its line, or it could not
                # be left out of grading without cutting a line in two; the CLI writes one block per record
                lines = [us for t, us in _turn_line_units(session_text) if t == n]
                if not lines or len(lines[-1]) != 1:
                    why = ("the session file's one unit past the stream shares its line with another unit, a shape the "
                           "CLI never writes, so it cannot be left out of grading")
            if why:
                out.append(f"turn {n} (cut, as the host records): {why}")
            continue
        if [tuple(u) for u in stream] == [tuple(u) for u in sess]:
            continue
        i = next((k for k, (a, b) in enumerate(zip(stream, sess)) if tuple(a) != tuple(b)), min(len(stream), len(sess)))
        a = tuple(stream[i]) if i < len(stream) else None
        b = tuple(sess[i]) if i < len(sess) else None
        out.append(f"turn {n}: the session file's content differs from the host-captured stream at item {i + 1} "
                   f"(the stream holds {len(stream)} item(s), the session file {len(sess)}; there the stream has "
                   f"{_unit_name(a)} and the session file {_unit_name(b)})")
    return out


def cost_record(turn_records: list, session_text: str, *, model: str, version: str) -> dict:
    """C14: the take's cost, per call and per turn, never summed.

    calls   costs.py's call shape, one per session-file call: {vendor, call_id, model, agent{harness, version},
            usage, total_cost_usd, started_at, ended_at, cache_write_durations}. total_cost_usd and the clock are None:
            Claude Code prints no dollar figure and no time per call (unmeasured, never zero). usage is the session
            file's, and cache_write_durations its recorded 5m and 1h split (lane pf1-l4-close), or None.
    turns   per turn: {n, total_cost_usd, usage, model_usage, num_turns, permission_denials} as the turn's result
            record printed them (None when the turn has no result record), plus its stream's call ids.
    """
    calls = [{"vendor": "anthropic", "call_id": f"{c['message_id']}/{c['request_id']}", "model": c["model"],
              "agent": {"harness": NAME, "version": version}, "usage": c["usage"], "total_cost_usd": None,
              "started_at": None, "ended_at": None, "cache_write_durations": c["cache_write_durations"]}
             for c in session_calls(session_text)]
    turns = []
    for t in turn_records:
        res = t["result"] or {}
        turns.append({"n": t["n"], "total_cost_usd": res.get("total_cost_usd"), "usage": res.get("usage"),
                      "model_usage": res.get("modelUsage"), "num_turns": res.get("num_turns"),
                      "permission_denials": res.get("permission_denials"),
                      "calls": [f"{c['message_id']}/{c['request_id']}" for c in t["calls"]]})
    return {"model_requested": model, "calls": calls, "turns": turns}
