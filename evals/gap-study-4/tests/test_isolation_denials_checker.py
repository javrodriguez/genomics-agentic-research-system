#!/usr/bin/env python3
"""The isolation denials are a study condition the checker verifies (glitch-6b's ruling, 15 Oct 2026; proposed by the
box lane for the harness lane to route).

Every claude-code take denies RemoteTrigger, SendMessage and ListAgents (box/run_take.ISOLATION_DISALLOWED_TOOLS, by
--disallowedTools and the inline settings' permissions.deny). The pinned 2.1.296 binary drops a denied tool from the
model's list by name, so:

  D-violated   a turn stream whose init lists any of the three yields `[harness-condition-violated]` naming the turn
               and the tools; one line per such init.
  D-clean      inits that list none of them: nothing; a take with no turn stream: nothing (other readers own that).
  D-shape      an init whose tools are not a list raises CheckRefused rather than guess.
  D-wired      check4 and check4_walk both add these problems.
  D-witness    each clause dropped in memory turns a check red.

Synthetic fixtures only.
"""

from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import check_take as ct  # noqa: E402

BASE = ["Task", "Bash", "CronCreate", "Edit", "Read", "ScheduleWakeup", "Skill", "Workflow", "Write"]


def init(tools):
    return {"type": "system", "subtype": "init", "session_id": "s", "tools": tools, "model": "m"}


def take(tmp: Path, turns) -> Path:
    path = tmp / "transcript.jsonl"
    path.write_text(json.dumps({"type": "user", "message": {"content": "x"}}) + "\n")
    for n, tools in enumerate(turns, 1):
        recs = [init(tools)] if tools is not None else []
        recs.append({"type": "result", "subtype": "success"})
        (tmp / f"turn-{n}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    return path


class Denials(unittest.TestCase):
    def run_case(self, turns):
        with tempfile.TemporaryDirectory() as d:
            return ct.denied_tool_problems(take(Path(d), turns))

    def check_violated(self):
        out = []
        for tool in ("RemoteTrigger", "SendMessage", "ListAgents"):
            got = self.run_case([BASE, BASE + [tool]])
            if ct.reason_ids(got) != ["harness-condition-violated"] or "turn 2" not in got[0] or tool not in got[0]:
                out.append(f"D-violated {tool}: {got}")
        got = self.run_case([BASE + ["RemoteTrigger", "SendMessage", "ListAgents"]] * 2)
        if len(got) != 2:
            out.append(f"D-violated: one line per init expected, got {got}")
        return out

    def check_clean(self):
        out = []
        for name, turns in (("clean", [BASE, BASE]), ("no init", [None]), ("no stream", []),
                            ("a near name", [BASE + ["ListPeers", "SendMessages"]])):
            got = self.run_case(turns)
            if got:
                out.append(f"D-clean {name}: {got}")
        return out

    def check_shape(self):
        with tempfile.TemporaryDirectory() as d:
            path = take(Path(d), [])
            (Path(d) / "turn-1.jsonl").write_text(json.dumps(init("RemoteTrigger")) + "\n")
            try:
                ct.denied_tool_problems(path)
                return ["D-shape: tools that are not a list were read"]
            except ct.CheckRefused:
                return []

    def check_wired(self):
        tree = ast.parse(Path(ct.__file__).read_text())
        out = []
        for fn in ("check4", "check4_walk"):
            body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn)
            calls = {c.func.id for c in ast.walk(body) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
            if "denied_tool_problems" not in calls:
                out.append(f"D-wired: {fn} does not add the isolation denials' problems")
        return out

    def test_violated(self):
        self.assertEqual(self.check_violated(), [])

    def test_clean(self):
        self.assertEqual(self.check_clean(), [])

    def test_shape(self):
        self.assertEqual(self.check_shape(), [])

    def test_wired(self):
        self.assertEqual(self.check_wired(), [])

    def test_the_checker_reads_the_launchers_names(self):
        """(the harness lane's addition) the names the checker looks for are the ones every turn denies: the
        adapter's three after round 3's two web tools, and run_take's where that module carries them."""
        import claude_code_adapter as cca
        from box import run_take as rt
        self.assertEqual(ct.ISOLATION_DENIED_TOOLS, cca.DISALLOWED_TOOLS[2:])
        theirs = getattr(rt, "ISOLATION_DISALLOWED_TOOLS", None)
        if theirs is not None:
            self.assertEqual(tuple(theirs), ct.ISOLATION_DENIED_TOOLS)

    def test_witnesses(self):
        all_checks = lambda: self.check_violated() + self.check_clean() + self.check_shape()  # noqa: E731
        for name, ctx in (
                ("a tool dropped", lambda: mock.patch.object(ct, "ISOLATION_DENIED_TOOLS", ("RemoteTrigger", "SendMessage"))),
                ("no tools", lambda: mock.patch.object(ct, "ISOLATION_DENIED_TOOLS", ())),
                ("another stream name", lambda: mock.patch.object(ct, "_TURN_STREAM",
                                                                  __import__("re").compile(r"stream-([1-9][0-9]*)\.jsonl")))):
            with ctx():
                try:
                    got = all_checks()
                except Exception as e:  # noqa: BLE001
                    got = [f"raised {type(e).__name__}"]
            print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
            self.assertTrue(got, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
