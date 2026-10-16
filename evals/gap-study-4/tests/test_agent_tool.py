#!/usr/bin/env python3
"""The Agent (sub-agent) tool, read for parity with round 3 (glitch-b5's ruling, 16 Oct 2026: option 1, parity done
properly; CP6 walk w083, Haiku, held on "tool name with no entry in the parser's table: 'Agent'").

Round 3 offered Agent in 64 of its 64 transcripts (each prompt_snapshot's tool list) and never called it. 2.1.296 offers
it under the same model-facing name (its stream init lists it as Task). The fixtures here are modelled on w083's real
key sets (a structure-only read by glitch-b5, 16 Oct 2026; no content): the transcript's tool_use input keys exactly
{description, prompt}; its tool_result record with toolUseResult {agentId, canContinueAgent, canReadOutputFile,
description, isAsync, outputFile, prompt, resolvedModel, status}; the turn stream's sub-agent records keyed {agent_id,
message, parent_tool_use_id, request_id, session_id, subagent_type, task_description, timestamp, tool_result_meta,
tool_use_result, type, uuid}. Everything is synthetic.

  A-view     the view reads an Agent call (kind other) whose input keys are within the 2.1.296 schema's closed set
             (description, prompt, subagent_type, model, effort, run_in_background, name, team_name, mode,
             isolation) and its tool_result as the others'; any other key (cwd among them: the schema the model sees
             omits it) refuses.
  A-stream   read_stream keeps the sub-agent's stream records (parent_tool_use_id set) apart: their words never count
             toward the agent's text or visible output, their calls never join the main calls or tool ids the
             cross-check compares; they are listed with their agent_id, parent call, model and tool calls. A
             sub-agent record whose parent call is not one of this turn's main calls (a sub-agent still writing after
             its turn ended), a parent id that is not a string, and a sub-agent assistant record with no model,
             refuse (StreamError). A harness event naming a call (tool_progress) is not a sub-agent's record.
  A-models   a sub-agent model is admitted only when it is the pin's (inherit) or one of the 2.1.296 first-party alias
             ids for haiku, sonnet and opus (SUBAGENT_EXPLICIT_MODELS); anything else is named (subagent_model_off),
             and a modelUsage key is a side key only for SIDE_MODELS or an admitted sub-agent model this turn served.
"""

from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import transcript_view as tv  # noqa: E402

CC = tv.ROUND3_HARNESS
OP = {"type": "user", "message": {"role": "user", "content": "Plan the design before you run anything."}}
CALL_ID = "toolu_agent_1"
AGENT_ID = "a1b2c3d4"


def agent_call(input_=None, call_id=CALL_ID):
    return {"type": "assistant", "isSidechain": False, "uuid": "u-a", "parentUuid": "u-o", "sessionId": "s",
            "requestId": "req_1", "requestedModel": "claude-haiku-4-5-20251001", "apiBlockIndex": 0, "cwd": "/run",
            "entrypoint": "sdk-cli", "gitBranch": "", "perTurnEffort": None, "timestamp": "t", "userType": "external",
            "version": "2.1.296",
            "message": {"model": "claude-haiku-4-5-20251001", "role": "assistant", "content": [
                {"type": "tool_use", "id": call_id, "name": "Agent",
                 "input": {"description": "Survey the stages", "prompt": "List the stages."} if input_ is None
                 else input_}]}}


def agent_result(call_id=CALL_ID, agent_id=AGENT_ID, **over):
    tur = {"agentId": agent_id, "canContinueAgent": False, "canReadOutputFile": False, "description": "Survey the stages",
           "isAsync": False, "outputFile": None, "prompt": "List the stages.",
           "resolvedModel": "claude-haiku-4-5-20251001", "status": "completed"}
    tur.update(over)
    return {"type": "user", "isSidechain": False, "uuid": "u-r", "parentUuid": "u-a", "sessionId": "s", "cwd": "/run",
            "entrypoint": "sdk-cli", "gitBranch": "", "permissionDecision": None, "promptId": "p", "timestamp": "t",
            "userType": "external", "version": "2.1.296", "sourceToolAssistantUUID": "u-a", "toolUseResult": tur,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call_id,
                                                     "content": [{"type": "text", "text": "Stages 00 to 03."}]}]}}


def lines(*recs):
    return [json.dumps(r) for r in recs]


SCHEMA_KEYS = ("description", "prompt", "subagent_type", "model", "effort", "run_in_background", "name", "team_name",
               "mode", "isolation")


def view_problems(view=tv) -> list:
    out = []
    full = {k: "x" for k in SCHEMA_KEYS}
    full["run_in_background"] = False
    for name, inp in (("w083's keys", None), ("every schema key", full)):
        try:
            evs = view.events(CC, lines(OP, agent_call(inp), agent_result()))
        except view.ViewError as e:
            out.append(f"A-view {name}: refused: {e}")
            continue
        calls = [e for e in evs if e.kind == view.TOOL_CALL]
        results = [e for e in evs if e.kind == view.TOOL_RESULT]
        if [(e.tool, e.args) for e in calls] != [(view.OTHER, {})]:
            out.append(f"A-view {name}: calls {[(e.tool, e.args) for e in calls]}")
        if [e.text for e in results] != ["Stages 00 to 03."] or results[0].call != calls[0].call:
            out.append(f"A-view {name}: results {[e.text for e in results]}")
    for name, inp in (("cwd", {"description": "d", "prompt": "p", "cwd": "/elsewhere"}),
                      ("an unknown key", {"description": "d", "prompt": "p", "fork": True})):
        try:
            view.events(CC, lines(OP, agent_call(inp), agent_result()))
            out.append(f"A-view: admitted an input with {name}")
        except view.ViewError:
            pass
    if set(view.CC_TOOLS["Agent"][2]) != set(SCHEMA_KEYS) if "Agent" in view.CC_TOOLS else True:
        out.append("A-view: the Agent entry's allowed keys are not the schema's closed set")
    return out


PIN = "claude-haiku-4-5-20251001"
INIT = {"type": "system", "subtype": "init", "session_id": "s", "model": PIN, "permissionMode": "bypassPermissions",
        "claude_code_version": "2.1.296", "apiKeySource": "none", "tools": ["Task", "Bash"]}


def main_said(text=None, call=True):
    content = [{"type": "text", "text": text}] if text else []
    if call:
        content.append({"type": "tool_use", "id": CALL_ID, "name": "Agent",
                        "input": {"description": "Survey", "prompt": "List the stages."}})
    return {"type": "assistant", "session_id": "s", "parent_tool_use_id": None,
            "message": {"id": "msg_main", "model": PIN, "role": "assistant", "content": content}, "request_id": "r1"}


def sub(kind="assistant", parent=CALL_ID, model=PIN, text="SUB-MARK", tool=None, **over):
    content = [{"type": "text", "text": text}]
    if tool:
        content.append(tool)
    msg = {"id": "msg_sub", "role": kind, "content": content}
    if kind == "assistant" and model is not None:
        msg["model"] = model
    r = {"type": kind, "agent_id": AGENT_ID, "message": msg, "parent_tool_use_id": parent, "request_id": "r2",
         "session_id": "s", "subagent_type": "general-purpose", "task_description": "Survey", "timestamp": "t",
         "tool_result_meta": None, "tool_use_result": None, "uuid": "u-s"}
    r.update(over)
    return r


RESULT = {"type": "result", "subtype": "success", "is_error": False, "session_id": "s", "result": "done",
          "modelUsage": {PIN: {"inputTokens": 1, "outputTokens": 1}}}


def stream(*recs):
    return "".join(json.dumps(r) + "\n" for r in recs)


def stream_problems(cca=None) -> list:
    import claude_code_adapter as real
    cca = cca or real
    out = []
    read = cca.read_stream(stream(INIT, main_said("I will delegate."), sub(tool={"type": "tool_use", "id": "toolu_sub",
                                                                                  "name": "Bash", "input": {"command": "ls"}}),
                                  sub("user", text="ok"), RESULT))
    if "SUB-MARK" in read["agent_text"] or read["agent_text"] != "I will delegate.":
        out.append(f"A-stream: the agent's text {read['agent_text']!r}")
    if read["tool_use_ids"] != [CALL_ID] or [c["message_id"] for c in read["calls"]] != ["msg_main"]:
        out.append(f"A-stream: main calls {read['calls']} / ids {read['tool_use_ids']}")
    subs = read.get("subagent_records") or []
    if [(s["type"], s["agent_id"], s["parent_tool_use_id"]) for s in subs] != [("assistant", AGENT_ID, CALL_ID),
                                                                               ("user", AGENT_ID, CALL_ID)]:
        out.append(f"A-stream: sub-agent records {subs}")
    elif [t["name"] for t in subs[0]["tool_uses"]] != ["Bash"]:
        out.append(f"A-stream: sub-agent tool calls {subs[0]['tool_uses']}")
    progress = cca.read_stream(stream(INIT, main_said("x"), {"type": "tool_progress", "parent_tool_use_id": "toolu_x",
                                                              "session_id": "s"}, RESULT))
    if progress["subagent_records"]:
        out.append("A-stream: a tool_progress event read as a sub-agent record")
    if read.get("subagent_models") != [PIN]:
        out.append(f"A-stream: sub-agent models {read.get('subagent_models')}")
    only_sub = cca.read_stream(stream(INIT, main_said(None), sub(), RESULT))
    if only_sub["agent_text"] or only_sub["agent_output"] is not True:     # the main call itself is output
        out.append(f"A-stream: a turn whose only words are the sub-agent's reads {only_sub['agent_text']!r}")
    for name, text in (("a parent call not made in this turn", stream(INIT, main_said("x"), sub(parent="toolu_other"))),
                       ("a sub-agent assistant record with no model", stream(INIT, main_said("x"), sub(model=None))),
                       ("a parent id that is not a string", stream(INIT, main_said("x"), sub(parent=7)))):
        try:
            cca.read_stream(text)
            out.append(f"A-stream: read {name}")
        except cca.StreamError:
            pass
    return out


def model_problems(cca=None) -> list:
    import claude_code_adapter as real
    cca = cca or real
    out = []
    if tuple(cca.SUBAGENT_EXPLICIT_MODELS) != ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"):
        out.append(f"A-models: {cca.SUBAGENT_EXPLICIT_MODELS}")
    for m, ok in ((PIN, True), ("claude-opus-5-5", True), ("claude-sonnet-5-5", True), ("claude-haiku-5-5", True),
                  ("claude-fable-5-1", False), ("claude-sonnet-4-5", False)):
        read = cca.read_stream(stream(INIT, main_said("x"), sub(model=m),
                                      dict(RESULT, modelUsage={PIN: {}, m: {}} if m != PIN else {PIN: {}})))
        off = cca.subagent_model_off(read, PIN)
        if (off is None) is not ok:
            out.append(f"A-models {m}: subagent_model_off {off!r}")
        if ok and (cca.served_model_off(read, PIN) is not None or cca.unlisted_side_model(read, PIN) is not None):
            out.append(f"A-models {m}: an admitted sub-agent model read as a switch or an unlisted side model")
    read = cca.read_stream(stream(INIT, main_said("x"), dict(RESULT, modelUsage={PIN: {}, "claude-opus-5-5": {}})))
    if cca.unlisted_side_model(read, PIN) != "claude-opus-5-5":
        out.append("A-models: a modelUsage key no sub-agent of this turn served reads as admitted")
    return out


def mutant(mod, old, new):
    src = Path(mod.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutation site occurs {src.count(old)} times in {mod.__file__}: {old!r}")
    m = types.ModuleType(mod.__name__ + "_mutant")
    m.__file__ = mod.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), mod.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    return m


class TheAgentTool(unittest.TestCase):
    def test_a_view(self):
        self.assertEqual(view_problems(), [])

    def test_a_stream(self):
        self.assertEqual(stream_problems(), [])

    def test_a_models(self):
        self.assertEqual(model_problems(), [])

    def test_a_stream_witnesses(self):
        import claude_code_adapter as cca
        cases = (
            ("sub-agent records read as the agent's",
             "        if parent is not None and kind in SUBAGENT_RECORD_TYPES:\n", "        if False:\n"),
            ("a late sub-agent record read", "    late = [s for s in subs if s[\"parent_tool_use_id\"] not in tools]\n",
             "    late = []\n"),
            ("any sub-agent model admitted", "    if m != model and m not in SUBAGENT_EXPLICIT_MODELS:", "    if False:"),
            ("sub-agent usage unread", "    return {m for m in read.get(\"subagent_models\") or () if m == model or "
             "m in SUBAGENT_EXPLICIT_MODELS}", "    return set()"),
        )
        for name, old, new in cases:
            with self.subTest(witness=name):
                m = mutant(cca, old, new)
                try:
                    got = stream_problems(m) + model_problems(m)
                except Exception as e:  # noqa: BLE001 - a mutant that crashes the reader is red too
                    got = [f"raised {type(e).__name__}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
                self.assertTrue(got, name)


if __name__ == "__main__":
    unittest.main()
