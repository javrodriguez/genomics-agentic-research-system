#!/usr/bin/env python3
"""The isolation denials are a study condition the checker verifies on every turn, fail closed (glitch-6b's rulings,
15 Oct 2026; proposed by the box lane, made fail closed by glitch-6b's ruling of the same day).

Every claude-code take denies RemoteTrigger, SendMessage and ListAgents (box/run_take.ISOLATION_DISALLOWED_TOOLS) by
--disallowedTools and by the one inline --settings' permissions.deny, and sets crossSessionInbound "refuse"
(box/run_take.CROSS_SESSION_INBOUND); each turn's launch journal (turn-N.jsonl.launch.json) records that argv. The
pinned 2.1.296 binary drops a denied tool from the model's list by name, so:

  D-violated   a turn stream whose init lists any of the three yields `[harness-condition-violated]` naming the turn
               and the tools; one line per such init.
  D-clean      full journals and inits that list none of them: nothing; the flag's =, comma and space spellings
               read alike; a deferred_tools_delta adding other names: nothing.
  D-delta      a transcript deferred_tools_delta whose addedNames includes one of the three refuses, as
               [transcript-mismatch] since lane pf1-l3 (the transcript alone shows it; review fb354328 finding 1).
  D-journal    fail closed: a journal whose --disallowedTools or permissions.deny lacks one of the three, whose
               crossSessionInbound is not "refuse" or is absent, or that carries two inline --settings; a turn stream
               with no journal; no journal at all; a turn stream with no init record: each refuses.
  D-prompt     a --disallowedTools that is the prompt after -p is never read as the flag.
  D-shape      an init whose tools are not a list raises CheckRefused rather than guess; a delta whose addedNames
               are not a list is [transcript-mismatch] (lane pf1-l3).
  D-wired      check4 and check4_walk both add these problems.
  D-names      the checker's three are the adapter's and run_take's (the harness lane's addition).
  D-witness    each clause dropped in memory turns a check red.

Synthetic fixtures only.
"""

from __future__ import annotations

import ast
import contextlib
import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import check_take as ct  # noqa: E402

BASE = ["Task", "Bash", "CronCreate", "Edit", "Read", "ScheduleWakeup", "Skill", "Workflow", "Write"]
DENY = ["RemoteTrigger", "SendMessage", "ListAgents"]


def settings(**over):
    st = {"availableModels": ["m"], "crossSessionInbound": "refuse",
          "env": {"CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "1", "CLAUDE_CODE_THRIFTY_SONIC": "false"},
          "fallbackModel": [], "permissions": {"deny": DENY}, "switchModelsOnFlag": False}
    for k, v in over.items():
        if v is None:
            st.pop(k, None)
        else:
            st[k] = v
    return json.dumps(st, sort_keys=True, separators=(",", ":"))


def journal(deny_argv=("--disallowedTools", *DENY), extra=(), **over):
    return {"schema": 1, "harness": "claude-code",
            "argv": ["claude", "-p", "x", "--model", "m", *deny_argv, "--settings", settings(**over), *extra]}


def init(tools):
    return {"type": "system", "subtype": "init", "session_id": "s", "tools": tools, "model": "m"}


def delta(names):
    return {"type": "attachment", "attachment": {"type": "deferred_tools_delta", "addedNames": names}}


def take(tmp: Path, turns, journals=None, records=()) -> Path:
    """turns: each turn's init tools (None: no init); journals: each turn's journal (default: the study's);
    records: further transcript records."""
    path = tmp / "transcript.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in
                            [{"type": "user", "message": {"content": "x"}}, *records]))
    for n, tools in enumerate(turns, 1):
        recs = [init(tools)] if tools is not None else []
        recs.append({"type": "result", "subtype": "success"})
        (tmp / f"turn-{n}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    for n, doc in enumerate([journal()] * len(turns) if journals is None else journals, 1):
        doc = dict(doc, stream=doc.get("stream", f"/synthetic/host/take/turn-{n}.jsonl"))   # r5 NIT (b)
        (tmp / f"turn-{n}.jsonl.launch.json").write_text(json.dumps(doc))
    return path


@contextlib.contextmanager
def source_mutant(old: str, new: str):
    """check_take's denied_tool_problems taken from a copy of its source with one anchored edit, patched in."""
    src = Path(ct.__file__).read_text()
    assert src.count(old) == 1, f"anchor occurs {src.count(old)} times: {old!r}"
    m = types.ModuleType("check_take_witness")
    m.__file__ = ct.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), ct.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    with mock.patch.object(ct, "denied_tool_problems", m.denied_tool_problems):
        yield


class Denials(unittest.TestCase):
    def run_case(self, turns, journals=None, records=()):
        with tempfile.TemporaryDirectory() as d:
            return ct.denied_tool_problems(take(Path(d), turns, journals, records))

    def check_violated(self):
        out = []
        for tool in DENY:
            got = self.run_case([BASE, BASE + [tool]])
            if ct.reason_ids(got) != ["harness-condition-violated"] or "turn 2" not in got[0] or tool not in got[0]:
                out.append(f"D-violated {tool}: {got}")
        got = self.run_case([BASE + DENY] * 2)
        if len(got) != 2:
            out.append(f"D-violated: one line per init expected, got {got}")
        return out

    def check_clean(self):
        out = []
        for name, turns, journals in (
                ("clean", [BASE, BASE], None),
                ("a near name", [BASE + ["ListPeers", "SendMessages"]], None),
                ("the = spelling", [BASE], [journal(("--disallowedTools=RemoteTrigger,SendMessage,ListAgents",))]),
                ("the dashed flag, comma list", [BASE], [journal(("--disallowed-tools", "RemoteTrigger,SendMessage",
                                                                  "ListAgents"))]),
                ("two flags", [BASE], [journal(("--disallowedTools", "RemoteTrigger", "--disallowedTools",
                                                "SendMessage", "ListAgents"))])):
            got = self.run_case(turns, journals)
            if got:
                out.append(f"D-clean {name}: {got}")
        got = self.run_case([BASE], records=[delta(["mcp__x__y", "ListPeers"])])
        if got:
            out.append(f"D-clean a delta of other names: {got}")
        return out

    def check_delta(self):
        out = []
        for tool in DENY:
            got = self.run_case([BASE], records=[delta(["mcp__x__y", tool])])
            # lane pf1-l3 (ruling on review fb354328 finding 1): the delta is the transcript's alone, a mismatch
            if ct.reason_ids(got) != ["transcript-mismatch"] or tool not in got[0]:
                out.append(f"D-delta {tool}: {got}")
        return out

    def check_journal(self):
        out = []
        cases = {
            "the flag lacks one": ([BASE], [journal(("--disallowedTools", "RemoteTrigger", "SendMessage"))]),
            "no flag": ([BASE], [journal(())]),
            "settings deny lacks one": ([BASE], [journal(permissions={"deny": DENY[:2]})]),
            "settings without permissions": ([BASE], [journal(permissions=None)]),
            "inbound hold": ([BASE], [journal(crossSessionInbound="hold")]),
            "inbound absent": ([BASE], [journal(crossSessionInbound=None)]),
            "two inline settings": ([BASE], [journal(extra=("--settings", settings()))]),
            "one turn of two": ([BASE, BASE], [journal(), journal(crossSessionInbound="accept")]),
            "a stream with no journal": ([BASE, BASE], [journal()]),
            "no journal at all": ([BASE], []),
            "no journal and no stream": ([], []),
            "a turn stream with no init": ([BASE, None], None),
        }
        for name, (turns, journals) in cases.items():
            got = self.run_case(turns, journals)
            if ct.reason_ids(got)[:1] != ["harness-condition-violated"]:
                out.append(f"D-journal {name}: {got}")
        return out

    def check_prompt(self):
        # the prompt is the word "--disallowedTools": the three after it are the prompt's neighbours, not its values
        j = journal(())
        j["argv"] = ["claude", "-p", "--disallowedTools", *DENY, "--model", "m", "--settings", settings()]
        got = self.run_case([BASE], [j])
        return [] if ct.reason_ids(got) == ["harness-condition-violated"] else [f"D-prompt: {got}"]

    def check_shape(self):
        out = []
        with tempfile.TemporaryDirectory() as d:
            path = take(Path(d), [None])
            (Path(d) / "turn-1.jsonl").write_text(json.dumps(init("RemoteTrigger")) + "\n")
            try:
                ct.denied_tool_problems(path)
                out.append("D-shape: tools that are not a list were read")
            except ct.CheckRefused:
                pass
        with tempfile.TemporaryDirectory() as d:
            # lane pf1-l3 (ruling on review fb354328 finding 1): a delta off its shape is the agent-writable
            # transcript's, so it is transcript-mismatch, never a guess and never a stop
            path = take(Path(d), [BASE], records=[delta("RemoteTrigger")])
            got = ct.denied_tool_problems(path)
            if ct.reason_ids(got) != ["transcript-mismatch"] or "not a list" not in got[0]:
                out.append(f"D-shape: addedNames that are not a list read as {got}")
        return out

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

    def test_journal(self):
        self.assertEqual(self.check_journal(), [])

    def test_prompt(self):
        self.assertEqual(self.check_prompt(), [])

    def test_delta(self):
        self.assertEqual(self.check_delta(), [])

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
        inbound = getattr(rt, "CROSS_SESSION_INBOUND", None)
        if inbound is not None:
            self.assertEqual(inbound, ct.CROSS_SESSION_INBOUND)

    def test_witnesses(self):
        all_checks = lambda: (self.check_violated() + self.check_clean() + self.check_journal()  # noqa: E731
                              + self.check_prompt() + self.check_shape() + self.check_delta())
        for name, ctx in (
                ("a tool dropped", lambda: mock.patch.object(ct, "ISOLATION_DENIED_TOOLS", ("RemoteTrigger", "SendMessage"))),
                ("no tools", lambda: mock.patch.object(ct, "ISOLATION_DENIED_TOOLS", ())),
                ("another stream name", lambda: mock.patch.object(ct, "_TURN_STREAM",
                                                                  re.compile(r"stream-([1-9][0-9]*)\.jsonl"))),
                ("inbound accepted", lambda: mock.patch.object(ct, "CROSS_SESSION_INBOUND", "accept")),
                ("missing journal read as nothing", lambda: mock.patch.object(ct, "_journal_gaps", lambda *a: [])),
                ("no init read as nothing", lambda: source_mutant("        if not inits:", "        if False:")),
                ("the delta unread", lambda: source_mutant(
                    'att.get("type") == "deferred_tools_delta"', 'att.get("type") == "deferred_tools_delta_x"')),
                ("inbound unchecked", lambda: source_mutant(
                    "            if settings[0].get(\"crossSessionInbound\") != CROSS_SESSION_INBOUND:",
                    "            if False:")),
                ("settings deny unchecked", lambda: source_mutant("            if not want <= deny:",
                                                                  "            if False:")),
                ("the prompt read as flags", lambda: mock.patch.object(ct, "_JOURNAL_PRINT_FLAGS", ())),
                ("the variadic read as one", lambda: mock.patch.object(
                    ct, "_journal_denied", lambda toks: {toks[i + 1] for i, t in enumerate(toks[:-1])
                                                         if t in ct._JOURNAL_DENY_FLAGS}))):
            with ctx():
                try:
                    got = all_checks()
                except Exception as e:  # noqa: BLE001
                    got = [f"raised {type(e).__name__}"]
            print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
            self.assertTrue(got, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
