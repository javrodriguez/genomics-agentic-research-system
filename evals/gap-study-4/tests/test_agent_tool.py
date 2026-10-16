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


class TheAgentTool(unittest.TestCase):
    def test_a_view(self):
        self.assertEqual(view_problems(), [])


if __name__ == "__main__":
    unittest.main()
