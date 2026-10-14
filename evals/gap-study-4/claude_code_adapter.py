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
DISALLOWED_TOOLS = ("WebFetch", "WebSearch")
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


def _records(text: str) -> tuple[list, int]:
    """(the JSON object records of a JSONL text in order, the count of lines that were not one)."""
    out, bad = [], 0
    for raw in (text or "").splitlines():
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
    for rec in recs:
        sid = rec.get("session_id")
        if isinstance(sid, str) and sid not in sids:
            sids.append(sid)
        kind = rec.get("type")
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
    return {"init": init, "init_extra": extra, "inits": inits, "agent_text": "\n".join(said),
            "harness_text": "\n".join(h for h in harness if h), "agent_output": output, "api_errors": api,
            "calls": calls, "tool_use_ids": tools, "result": result, "session_ids": sids, "undecoded": bad,
            "served_models": models, "model_usage": usage}


# Review MINOR 5 (glitch-06's ruling, 14 Oct 2026): a modelUsage key beside the pin's is a side call only for a model on
# this closed list (the one observed: the recorded sonnet probe's claude-haiku-4-5-20251001, Claude Code's small and
# fast model); any other extra key is a mismatch. The side calls' token counts are recorded (side_calls).
SIDE_MODELS = ("claude-haiku-4-5-20251001",)
# A first-walk acceptance item (the same ruling): a turn that uses the Agent tool shows its subagent's assistant records
# in the 2.1.296 stream (parent_tool_use_id set), each carrying message.model; until a walk shows it, a subagent on
# another model may leave only a modelUsage key, which the closed list above then reads as a mismatch.
FIRST_WALK_ACCEPTANCE = ("a turn that uses the Agent tool shows its subagent's assistant records in the 2.1.296 "
                         "stream (parent_tool_use_id set), each carrying message.model",)


def side_calls(read: dict, model: str) -> dict:
    """{side model: {inputTokens, outputTokens}} for the result's modelUsage keys beside the pin's (as printed)."""
    usage = (read.get("result") or {}).get("modelUsage") or {}
    return {k: {t: v.get(t) for t in ("inputTokens", "outputTokens")} for k, v in usage.items()
            if k != model and isinstance(v, dict)}


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
    if read["model_usage"] is not None and read["served_models"] and model not in read["model_usage"]:
        others = [k for k in read["model_usage"] if k != model]
        return others[0] if others else "<modelUsage names no model>"
    for k in read["model_usage"] or ():
        if k != model and k not in SIDE_MODELS:     # a side key off the closed list is a mismatch
            return k
    return None


def argv(line: str, *, model: str, permission_mode: str, session_id: str, first: bool) -> list:
    """The turn's argv inside the box (C15-1..3)."""
    for what, v in (("line", line), ("model", model), ("permission_mode", permission_mode),
                    ("session_id", session_id)):
        if not isinstance(v, str) or not v:
            raise StreamError(f"the turn's {what} must be a non-empty string")
    out = [CLIENT, "-p", line, *OUTPUT_FLAGS, "--permission-mode", permission_mode, *PERMISSION_PROMPTS,
           "--model", model, *ISOLATION_FLAGS, "--disallowedTools", *DISALLOWED_TOOLS]
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
        after = self.counters_for()
        counters = rt.counter_delta(before, after)
        # Review MINOR 3 (live harness 3a's pattern, as Gemini and Codex): the exec ran, so its outcome is kept before
        # the stream is read; a refusal from here on is an executed turn's, never a turn that did not happen.
        executed = {"n": n, "exit_code": got["exit_code"], "timed_out": got["timed_out"],
                    "started_at": got["started_at"], "ended_at": got["ended_at"], "stream_path": got["stream_path"],
                    "counters": counters, "refused": None}
        self.executed_turns.append(executed)
        try:
            with open(got["stream_path"], encoding="utf-8", errors="surrogateescape") as fh:
                read = read_stream(fh.read())
            off = served_model_off(read, self.model)
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
            "model_usage": read["model_usage"], "served_off": off, "side_calls": side_calls(read, self.model)})
        return aa.TurnResult(exit_code=got["exit_code"], text=read["agent_text"], stream_path=got["stream_path"],
                             end_reason=end_reason(got["exit_code"], got["timed_out"]), init=init,
                             api_errors=read["api_errors"], counters=counters,
                             started_at=got["started_at"], ended_at=got["ended_at"],
                             agent_output=read["agent_output"])

    def _end(self) -> None:
        """Nothing of the adapter's own to tear down: the driver removes the container by its recorded id."""
        return None


# ---- C14: the calls, counted once each, from the session file ---------------------------------------------------
def session_calls(text: str) -> list:
    """The session file's model calls, one per (message.id, requestId), in order: {message_id, request_id, model,
    usage}. usage holds the four USAGE_CLASSES as recorded, or is None when any of them is not a count (unmeasured,
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
        if key in by_key:
            if by_key[key]["usage"] != counts or by_key[key]["model"] != msg.get("model"):
                raise StreamError(f"call {key[0]} carries two different usages or models in the session file")
            continue
        call = {"message_id": key[0], "request_id": key[1], "model": msg.get("model"), "usage": counts}
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
    recs, _ = _records(session_text)
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
    return out


def cost_record(turn_records: list, session_text: str, *, model: str, version: str) -> dict:
    """C14: the take's cost, per call and per turn, never summed.

    calls   costs.py's call shape, one per session-file call: {vendor, call_id, model, agent{harness, version},
            usage, total_cost_usd, started_at, ended_at}. total_cost_usd and the clock are None: Claude Code prints
            no dollar figure and no time per call (unmeasured, never zero). usage is the session file's.
    turns   per turn: {n, total_cost_usd, usage, model_usage, num_turns, permission_denials} as the turn's result
            record printed them (None when the turn has no result record), plus its stream's call ids.
    """
    calls = [{"vendor": "anthropic", "call_id": f"{c['message_id']}/{c['request_id']}", "model": c["model"],
              "agent": {"harness": NAME, "version": version}, "usage": c["usage"], "total_cost_usd": None,
              "started_at": None, "ended_at": None} for c in session_calls(session_text)]
    turns = []
    for t in turn_records:
        res = t["result"] or {}
        turns.append({"n": t["n"], "total_cost_usd": res.get("total_cost_usd"), "usage": res.get("usage"),
                      "model_usage": res.get("modelUsage"), "num_turns": res.get("num_turns"),
                      "permission_denials": res.get("permission_denials"),
                      "calls": [f"{c['message_id']}/{c['request_id']}" for c in t["calls"]]})
    return {"model_requested": model, "calls": calls, "turns": turns}
