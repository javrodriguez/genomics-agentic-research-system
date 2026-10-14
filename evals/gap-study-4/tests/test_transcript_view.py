#!/usr/bin/env python3
"""transcript_view.py: every kind and tool kind with a near-miss, every refusal, turns, and the seam.

The seam (interface 8): a test-only harness, `fake-second`, has its own made-up raw format, record
types, tool names and argument keys, none equal to Claude Code's. The same task content, rendered
for both harnesses, must give the EXPECTED events under each, asserted against values typed here.
A reader keyed on a Claude Code record type, tool name or argument key must make that check go red.

This file also holds the fake-second parser and the renderer the grader tests import (helpers live
in a test file of the lane's own, never as a non-test module under tests/).

Every check is a function returning problems; each test runs it on the real view (no problem) and on
an in-memory mutant (a problem), so each guard is shown able to fail (interface 3).
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import transcript_view as tv  # noqa: E402

CC = tv.ROUND3_HARNESS
FAKE = "fake-second"
REPO = HERE.parent.parent
ROUND3 = REPO / "evals" / "gap-study-3"

# ---- the test-only second harness ---------------------------------------------------------------
# Its own record types, tool names and argument keys; none equal to any of Claude Code's.
FAKE_RECORDS = ("op-line", "agent-say", "agent-muse", "agent-run", "run-output", "furniture")
FAKE_TOOLS = {
    "sh": (tv.SHELL, {"cmdline": "command", "detached": "background"}, ("cmdline", "detached")),
    "view": (tv.READ, {"target": "path"}, ("target",)),
    "create": (tv.WRITE, {"target": "path"}, ("target", "body")),
    "modify": (tv.EDIT, {"target": "path"}, ("target", "before", "after")),
    "hunt": (tv.SEARCH, {"needle": "pattern", "under": "path"}, ("needle", "under")),
    "nap": (tv.OTHER, {}, ("seconds",)),
}
FAKE_KIND = {"op-line": tv.OPERATOR, "agent-say": tv.AGENT_TEXT, "agent-muse": tv.AGENT_REASONING,
             "furniture": tv.HARNESS}


class FakeSecondParser:
    record_types = FAKE_RECORDS
    tools = FAKE_TOOLS

    def items(self, line):
        r = json.loads(line)
        rec = r.get("rec")
        if rec not in FAKE_RECORDS:
            raise tv.ViewError(f"unknown record type: {rec!r}")
        if rec == "agent-run":
            kind, args = tv.map_tool(FAKE_TOOLS, r.get("verb"), r.get("params"))
            return [tv.RawItem(rec, tv.TOOL_CALL, tool=kind, args=args, ref=r["ticket"])]
        if rec == "run-output":
            return [tv.RawItem(rec, tv.TOOL_RESULT, text=r["words"], ref=r["ticket"])]
        return [tv.RawItem(rec, FAKE_KIND[rec], text=r["words"])]


def source_mutant(mod, old: str, new: str, *more: str):
    """An in-memory copy of module `mod` with `old` replaced by `new` (and each further (old, new) pair in `more`);
    every site must occur exactly once."""
    import types
    src = Path(mod.__file__).read_text(encoding="utf-8")
    pairs = [(old, new)] + list(zip(more[::2], more[1::2]))
    for o, n in pairs:
        if src.count(o) != 1:
            raise AssertionError(f"the mutation site occurs {src.count(o)} times in {mod.__file__}: {o!r}")
        src = src.replace(o, n)
    m = types.ModuleType(mod.__name__ + "_mutant")
    m.__file__ = mod.__file__
    exec(compile(src, mod.__file__, "exec"), m.__dict__)
    return m


@contextlib.contextmanager
def fake_harness():
    """The parser table with the test-only fake beside the real entry, for the duration of a test."""
    with mock.patch.dict(tv.PARSERS, {FAKE: FakeSecondParser()}):
        yield


# ---- one script, two raw formats ----------------------------------------------------------------
# A script is a list of steps: ("operator", text) ("text", text) ("reasoning", text)
# ("call", tool kind, view args) ("result", text) (answers the latest call) ("harness", cc text, fake text)

_CC_NAME = {tv.SHELL: "Bash", tv.READ: "Read", tv.WRITE: "Write", tv.EDIT: "Edit", tv.SEARCH: "Grep",
            tv.OTHER: "ToolSearch"}
_FAKE_NAME = {v[0]: k for k, v in FAKE_TOOLS.items()}


def _cc_input(kind, a):
    if kind == tv.SHELL:
        return {"command": a["command"], "run_in_background": a["background"], "description": "d"}
    if kind in (tv.READ,):
        return {"file_path": a["path"]}
    if kind == tv.WRITE:
        return {"file_path": a["path"], "content": "x"}
    if kind == tv.EDIT:
        return {"file_path": a["path"], "old_string": "a", "new_string": "b"}
    if kind == tv.SEARCH:
        return {"pattern": a["pattern"], **({"path": a["path"]} if a["path"] is not None else {})}
    return {"query": "select:x"}


def _fake_params(kind, a):
    if kind == tv.SHELL:
        return {"cmdline": a["command"], "detached": a["background"]}
    if kind in (tv.READ, tv.WRITE, tv.EDIT):
        return {"target": a["path"]}
    if kind == tv.SEARCH:
        return {"needle": a["pattern"], **({"under": a["path"]} if a["path"] is not None else {})}
    return {"seconds": 3}


def render(script, harness):
    """The script as raw lines of `harness` (CC = Claude Code's session file; FAKE = the made-up one)."""
    out, n = [], 0
    for step in script:
        tag = step[0]
        if harness == CC:
            if tag == "operator":
                r = {"type": "user", "isSidechain": False, "message": {"role": "user", "content": step[1]}}
            elif tag == "text":
                r = {"type": "assistant", "message": {"content": [{"type": "text", "text": step[1]}]}}
            elif tag == "reasoning":
                r = {"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": step[1],
                                                                   "signature": "s"}]}}
            elif tag == "call":
                n += 1
                r = {"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "id": f"toolu_{n}", "name": _CC_NAME[step[1]],
                     "input": _cc_input(step[1], step[2]), "caller": {"type": "direct"}}]}}
            elif tag == "result":
                r = {"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": f"toolu_{n}", "content": step[1]}]}}
            else:
                r = {"type": "attachment", "attachment": {"type": "total_tokens_reminder", "text": step[1]}}
        else:
            if tag == "call":
                n += 1
                r = {"rec": "agent-run", "verb": _FAKE_NAME[step[1]], "params": _fake_params(step[1], step[2]),
                     "ticket": f"t-{n}"}
            elif tag == "result":
                r = {"rec": "run-output", "words": step[1], "ticket": f"t-{n}"}
            elif tag == "harness":
                r = {"rec": "furniture", "words": step[2]}
            else:
                r = {"rec": {"operator": "op-line", "text": "agent-say", "reasoning": "agent-muse"}[tag],
                     "words": step[1]}
        out.append(json.dumps(r))
    return out


def expected_events(script, harness):
    """The events the view must give for `script`, written from the script alone (never from the view)."""
    out, turn, n = [], 0, 0
    last_tool = None
    for step in script:
        tag = step[0]
        if tag == "operator":
            turn += 1
            out.append(tv.AgentEvent(turn, tv.OPERATOR, step[1], None, None, None))
        elif tag == "text":
            out.append(tv.AgentEvent(turn, tv.AGENT_TEXT, step[1], None, None, None))
        elif tag == "reasoning":
            out.append(tv.AgentEvent(turn, tv.AGENT_REASONING, step[1], None, None, None))
        elif tag == "call":
            n += 1
            last_tool = step[1]
            out.append(tv.AgentEvent(turn, tv.TOOL_CALL, None, step[1], dict(step[2]), n))
        elif tag == "result":
            out.append(tv.AgentEvent(turn, tv.TOOL_RESULT, step[1], last_tool, None, n))
        else:
            out.append(tv.AgentEvent(turn, tv.HARNESS, step[1] if harness == CC else step[2], None, None, None))
    return out


# One take with every kind and every tool kind; its furniture text differs per harness.
SEAM_SCRIPT = [
    ("harness", "cc furniture before the first line", "fake furniture before the first line"),
    ("operator", "Start a bulk RNA-seq project called run-x, source data in data/staging/run-x/src"),
    ("reasoning", "The contract says to show the assay menu."),
    ("call", tv.READ, {"path": "gars/00_initialize_project/CONTEXT.md"}),
    ("result", "# Stage 00"),
    ("call", tv.SHELL, {"command": "python3 _system/stage00_register.py assays", "background": False}),
    ("result", '{"assays": []}'),
    ("text", "Reply with a comma-separated list of IDs"),
    ("harness", "cc furniture in turn 1", "fake furniture in turn 1"),
    ("operator", "05"),
    ("call", tv.SEARCH, {"pattern": "rnaseq", "path": None}),
    ("result", "match"),
    ("call", tv.SEARCH, {"pattern": "rnaseq", "path": "gars"}),
    ("result", "match"),
    ("call", tv.WRITE, {"path": "notes.txt"}),
    ("result", "ok"),
    ("call", tv.EDIT, {"path": "notes.txt"}),
    ("result", "ok"),
    ("call", tv.OTHER, {}),
    ("result", "x"),
    ("call", tv.SHELL, {"command": "sleep 1", "background": True}),
    ("result", "started"),
    ("text", "Confirm to create symlinks under 00_data/rnaseq_bulk/raw/"),
]


def seam_problems(view=tv) -> list[str]:
    out = []
    with fake_harness():
        for h in (CC, FAKE):
            try:
                got = view.events(h, render(SEAM_SCRIPT, h))
            except tv.ViewError as e:
                out.append(f"{h}: refused: {e}")
                continue
            if got != expected_events(SEAM_SCRIPT, h):
                out.append(f"{h}: events differ from the expected ones")
    return out


# ---- refusals -----------------------------------------------------------------------------------

def _cc(r):
    return [json.dumps(r)]


REFUSE = {
    "unknown record type": (CC, _cc({"type": "summary", "summary": "x"})),
    "unknown block type": (CC, _cc({"type": "assistant", "message": {"content": [{"type": "redacted_thinking",
                                                                                  "data": "x"}]}})),
    "unknown block type in a user record": (CC, _cc({"type": "user", "message": {"content": [
        {"type": "text", "text": "x"}]}})),
    "unknown block type in a tool result": (CC, [
        render([("call", tv.OTHER, {})], CC)[0],
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": [{"type": "image", "source": {}}]}]}})]),
    "unknown tool name": (CC, _cc({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "toolu_9", "name": "WebFetch", "input": {"url": "x"}}]}})),
    "unknown argument key": (CC, _cc({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "toolu_9", "name": "Read", "input": {"file_path": "x", "encoding": "y"}}]}})),
    "unknown attachment type": (CC, _cc({"type": "attachment", "attachment": {"type": "hook_output", "x": 1}})),
    "a queued command that is not a notification": (CC, _cc({"type": "attachment", "attachment": {
        "type": "queued_command", "commandMode": "prompt", "prompt": "go on"}})),
    "a user record with another origin": (CC, _cc({"type": "user", "origin": {"kind": "hook"},
                                                   "message": {"content": "x"}})),
    "a sidechain record": (CC, _cc({"type": "assistant", "isSidechain": True, "message": {"content": []}})),
    # Review round 1, W2B1-6: records the harness wrote itself are refused, never read as anyone's words.
    "a meta user record": (CC, _cc({"type": "user", "isMeta": True, "message": {"content": "Caveat: the messages"}})),
    "a record carrying isMeta, even false": (CC, _cc({"type": "user", "isMeta": False, "message": {"content": "05"}})),
    "an API-error assistant record": (CC, _cc({"type": "assistant", "isApiErrorMessage": True, "message": {
        "model": "claude-haiku-4-5-20251001", "content": [{"type": "text", "text": "API Error: 500"}]}})),
    "a synthetic assistant record": (CC, _cc({"type": "assistant", "message": {
        "model": "<synthetic>", "content": [{"type": "text", "text": "No response requested."}]}})),
    "a result for no call": (CC, _cc({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "toolu_404", "content": "x"}]}})),
    "a second result for one call": (CC, render([("call", tv.OTHER, {}), ("result", "a"), ("result", "b")], CC)),
    "a repeated call id": (CC, render([("call", tv.OTHER, {})], CC) * 2),
    "a required argument missing": (CC, _cc({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "toolu_9", "name": "Bash", "input": {"description": "no command"}}]}})),
    "an argument of the wrong type": (CC, _cc({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "toolu_9", "name": "Bash", "input": {"command": "ls",
                                                                       "run_in_background": "yes"}}]}})),
    "a line that is not JSON": (CC, ["{not json"]),
    "a blank line": (CC, ["   "]),
    "unknown harness": ("no-such-harness", render([("operator", "x")], CC)),   # codex is known since c35fc915
    "an empty harness name": ("", render([("operator", "x")], CC)),
    "a harness name in another case": (CC.upper(), render([("operator", "x")], CC)),
}


def refusal_problems(view=tv) -> list[str]:
    out = []
    for why, (h, lines) in REFUSE.items():
        try:
            view.events(h, lines)
        except tv.ViewError:
            continue
        out.append(f"not refused: {why}")
    try:
        view.harness_types("no-such-harness", render([("operator", "x")], CC))
        out.append("harness_types did not refuse an unknown harness")
    except tv.ViewError:
        pass
    return out


# ---- near-misses: one per kind and per tool kind ------------------------------------------------

def _one(h, r):
    evs = tv.events(h, [json.dumps(r)] if isinstance(r, dict) else r)
    return evs


def near_miss_problems(view=tv) -> list[str]:
    """Each case: raw lines, the kind (or tool kind) it must give, and the near-miss it must not be."""
    out = []
    cases = [
        ("operator", {"type": "user", "message": {"content": "05"}}, tv.OPERATOR),
        ("operator near-miss: a task notification",
         {"type": "user", "origin": {"kind": "task-notification"}, "message": {"content": "05"}}, tv.HARNESS),
        ("agent-text", {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}},
         tv.AGENT_TEXT),
        ("agent-text near-miss: the same words as reasoning", {"type": "assistant", "message": {"content": [
            {"type": "thinking", "thinking": "hi", "signature": ""}]}}, tv.AGENT_REASONING),
        # W2B1-6's near-miss: an assistant record with a real model is the agent's (only <synthetic> is refused).
        ("agent-text: a model's own record", {"type": "assistant", "message": {
            "model": "claude-haiku-4-5-20251001", "content": [{"type": "text", "text": "hi"}]}}, tv.AGENT_TEXT),
        ("harness", {"type": "attachment", "attachment": {"type": "date", "date": "hi"}}, tv.HARNESS),
        ("harness near-miss: an operator line with the same words", {"type": "user", "message": {"content": "hi"}},
         tv.OPERATOR),
        ("harness: a queued task notification", {"type": "attachment", "attachment": {
            "type": "queued_command", "commandMode": "task-notification", "prompt": "hi"}}, tv.HARNESS),
        ("harness: a bookkeeping record", {"type": "last-prompt", "lastPrompt": "hi"}, tv.HARNESS),
        ("harness: a system record", {"type": "system", "content": "hi"}, tv.HARNESS),
    ]
    for name, rec, kind in cases:
        try:
            evs = view.events(CC, [json.dumps(rec)])
        except tv.ViewError as e:
            out.append(f"{name}: refused: {e}")
            continue
        if [e.kind for e in evs] != [kind]:
            out.append(f"{name}: got {[e.kind for e in evs]}, expected [{kind}]")
    # Tool kinds: each name maps to its kind, and its near-miss (a sibling tool) does not.
    tools = [
        ("Bash", {"command": "ls"}, tv.SHELL, {"command": "ls", "background": False}),
        ("Bash", {"command": "ls", "run_in_background": True}, tv.SHELL, {"command": "ls", "background": True}),
        ("Read", {"file_path": "a", "limit": 5}, tv.READ, {"path": "a"}),
        ("Write", {"file_path": "a", "content": "x"}, tv.WRITE, {"path": "a"}),
        ("Edit", {"file_path": "a", "old_string": "x", "new_string": "y"}, tv.EDIT, {"path": "a"}),
        ("Grep", {"pattern": "p"}, tv.SEARCH, {"pattern": "p", "path": None}),
        ("Glob", {"pattern": "*.md", "path": "gars"}, tv.SEARCH, {"pattern": "*.md", "path": "gars"}),
        ("ToolSearch", {"query": "q"}, tv.OTHER, {}),
        ("Monitor", {"process_id": "b1"}, tv.OTHER, {}),
        ("ScheduleWakeup", {"delaySeconds": 60}, tv.OTHER, {}),
    ]
    for i, (name, inp, kind, args) in enumerate(tools):
        lines = [json.dumps({"type": "assistant", "message": {"content": [
                     {"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}]}}),
                 json.dumps({"type": "user", "message": {"content": [
                     {"type": "tool_result", "tool_use_id": f"t{i}", "content": "r"}]}})]
        try:
            evs = view.events(CC, lines)
        except tv.ViewError as e:
            out.append(f"{name}: refused: {e}")
            continue
        want = [tv.AgentEvent(0, tv.TOOL_CALL, None, kind, args, 1), tv.AgentEvent(0, tv.TOOL_RESULT, "r", kind, None, 1)]
        if evs != want:
            out.append(f"{name} {inp}: got {evs}")
    # Near-misses between tool kinds: Write is never edit, Edit never write, Glob never read.
    for name, inp, wrong in (("Write", {"file_path": "a"}, tv.EDIT), ("Edit", {"file_path": "a"}, tv.WRITE),
                             ("Glob", {"pattern": "a"}, tv.READ), ("Read", {"file_path": "a"}, tv.SEARCH)):
        evs = view.events(CC, [json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t", "name": name, "input": inp}]}})])
        if evs[0].tool == wrong:
            out.append(f"{name} read as {wrong}")
    return out


def turn_problems(view=tv) -> list[str]:
    out = []
    script = [("text", "before"), ("operator", "a"), ("text", "one"),
              ("harness", "x", "x"), ("operator", "a"), ("text", "two")]
    lines = render(script, CC)
    # A task notification between turns never starts a turn.
    lines.insert(3, json.dumps({"type": "user", "origin": {"kind": "task-notification"},
                                "message": {"content": "<task-notification>"}}))
    evs = view.events(CC, lines)
    got = [(e.turn, e.kind) for e in evs]
    want = [(0, tv.AGENT_TEXT), (1, tv.OPERATOR), (1, tv.AGENT_TEXT), (1, tv.HARNESS), (1, tv.HARNESS),
            (2, tv.OPERATOR), (2, tv.AGENT_TEXT)]
    if got != want:
        out.append(f"turns: {got}")
    # The operator lines bind to a ledger's sent lines, in order; a recovery line repeating n is still a turn.
    try:
        view.require_operator_lines(evs, ["a", "a"])
    except tv.ViewError:
        out.append("refused a take whose lines equal the sent lines")
    for bad in (["a"], ["a", "b"], ["a", "a", "a"]):
        try:
            view.require_operator_lines(evs, bad)
            out.append(f"bound to the wrong sent lines {bad}")
        except tv.ViewError:
            pass
    return out


class TheView(unittest.TestCase):
    def test_kinds_and_tool_kinds_and_their_near_misses(self):
        self.assertEqual(near_miss_problems(), [])

    def test_a_near_miss_check_fires_on_a_view_that_reads_reasoning_as_text(self):
        real = tv.ClaudeCodeSessionParser._assistant

        def mutant(self, r):
            return [tv.RawItem(i.raw_type, tv.AGENT_TEXT if i.kind == tv.AGENT_REASONING else i.kind, i.text,
                               i.tool, i.args, i.ref) for i in real(self, r)]
        with mock.patch.object(tv.ClaudeCodeSessionParser, "_assistant", mutant):
            self.assertTrue(near_miss_problems())

    def test_a_near_miss_check_fires_on_a_view_that_maps_write_as_edit(self):
        tools = dict(tv.CC_TOOLS)
        tools["Write"] = (tv.EDIT,) + tools["Write"][1:]
        with mock.patch.dict(tv.CC_TOOLS, tools):
            self.assertTrue(near_miss_problems())

    def test_every_refusal(self):
        self.assertEqual(refusal_problems(), [])

    def test_the_refusal_check_fires_on_a_view_that_reads_harness_written_records(self):  # review round 1, W2B1-6
        with mock.patch.object(tv, "CC_REFUSED_FLAGS", ()):
            self.assertEqual(refusal_problems(), ["not refused: a meta user record",
                                                  "not refused: a record carrying isMeta, even false",
                                                  "not refused: an API-error assistant record"])
        with mock.patch.object(tv, "CC_SYNTHETIC_MODEL", object()):
            self.assertEqual(refusal_problems(), ["not refused: a synthetic assistant record"])

    def test_the_refusal_check_fires_on_a_view_that_defaults_the_harness(self):
        with mock.patch.object(tv, "_parser", lambda h: tv.PARSERS.get(h, tv.PARSERS[CC])):
            self.assertIn("not refused: unknown harness", refusal_problems())

    def test_the_refusal_check_fires_on_a_view_that_guesses_an_unknown_tool(self):
        real = tv.map_tool

        def guessing(table, name, raw):
            if name not in table:
                return tv.OTHER, {}
            return real(table, name, raw)
        with mock.patch.object(tv, "map_tool", guessing):
            self.assertIn("not refused: unknown tool name", refusal_problems())

    def test_the_refusal_check_fires_on_a_view_that_guesses_an_unknown_record_type(self):
        real = tv.ClaudeCodeSessionParser.items

        def guessing(self, line):
            try:
                r = json.loads(line)
            except ValueError:
                return real(self, line)
            if isinstance(r, dict) and r.get("type") not in tv.CC_RECORD_TYPES:
                return [tv.RawItem(str(r.get("type")), tv.HARNESS, text=None)]
            return real(self, line)
        with mock.patch.object(tv.ClaudeCodeSessionParser, "items", guessing):
            self.assertIn("not refused: unknown record type", refusal_problems())

    def test_turns_count_operator_lines(self):
        self.assertEqual(turn_problems(), [])

    def test_the_turn_check_fires_on_a_view_that_counts_notifications_as_turns(self):
        real = tv.ClaudeCodeSessionParser._user

        def mutant(self, r):
            return [tv.RawItem(i.raw_type, tv.OPERATOR if i.raw_type.startswith("user:") else i.kind, i.text,
                               i.tool, i.args, i.ref) for i in real(self, r)]
        with mock.patch.object(tv.ClaudeCodeSessionParser, "_user", mutant):
            self.assertTrue(turn_problems())


class TheSeam(unittest.TestCase):
    def test_both_harnesses_give_the_expected_events(self):
        self.assertEqual(seam_problems(), [])

    def test_the_expected_events_are_typed_values_not_the_views(self):
        evs = expected_events(SEAM_SCRIPT, FAKE)
        self.assertEqual(evs[0], tv.AgentEvent(0, tv.HARNESS, "fake furniture before the first line", None, None,
                                               None))
        self.assertEqual(evs[5], tv.AgentEvent(1, tv.TOOL_CALL, None, tv.SHELL,
                                               {"command": "python3 _system/stage00_register.py assays",
                                                "background": False}, 2))
        self.assertEqual(sum(e.kind == tv.OPERATOR for e in evs), 2)

    def test_the_fake_shares_no_raw_name_with_claude_code(self):
        p = tv.PARSERS[CC]
        cc_names = set(p.record_types) | set(p.block_types) | set(p.attachment_types) | set(p.tools)
        cc_keys = {k for _, _, allowed in p.tools.values() for k in allowed}
        fake_keys = {k for _, _, allowed in FAKE_TOOLS.values() for k in allowed}
        self.assertFalse((set(FAKE_RECORDS) | set(FAKE_TOOLS)) & (cc_names | cc_keys))
        self.assertFalse(fake_keys & (cc_names | cc_keys))
        self.assertNotIn(FAKE, tv.PARSERS)

    def test_the_seam_fires_on_a_reader_keyed_on_a_claude_code_record_type(self):
        real = tv._items

        def keyed(h, lines):
            # The mutant decides "the agent's words" by Claude Code's record type, not by the parser's kind.
            return [tv.RawItem(i.raw_type, tv.HARNESS if i.kind == tv.AGENT_TEXT and i.raw_type != "assistant"
                               else i.kind, i.text, i.tool, i.args, i.ref) for i in real(h, lines)]
        with mock.patch.object(tv, "_items", keyed):
            self.assertTrue(seam_problems())

    def test_the_seam_fires_on_a_reader_keyed_on_a_claude_code_tool_name_or_key(self):
        real = tv.map_tool

        def keyed(table, name, raw):
            kind, args = real(table, name, raw)
            if kind == tv.SHELL and "command" not in raw:
                args = dict(args, command="")
            return kind, args
        with mock.patch.object(tv, "map_tool", keyed):
            self.assertTrue(seam_problems())

    def test_the_seam_fires_on_a_view_that_drops_the_harness_events(self):
        real = tv._items
        with mock.patch.object(tv, "_items", lambda h, l: [i for i in real(h, l) if i.kind != tv.HARNESS]):
            self.assertTrue(seam_problems())

    def test_a_grader_keyed_on_a_claude_code_tool_name_goes_red_on_the_fake_only(self):
        """Review round 1, W2B1-5: the reviewer's hybrid mutant, run through pause_adherence's own seam check. It
        takes every event from the view, but keeps a tool call only when its raw name is Claude Code's shell tool.
        Records, words and turns are the view's, so nothing is refused at the binding and the mutant isolates keying
        on a tool name: claude-code still grades as expected; fake-second, whose shell tool has its own name, does
        not. (Here, beside the view's seam, because the fold's brief confines edits to test_pause_adherence.py to
        W2B1-7.)"""
        import test_pause_adherence as tpa  # imported here, not at the top: it imports this file

        def hybrid(h, lines, case):
            kept, n = set(), 0
            for ln in lines:
                r = json.loads(ln)
                blocks = r.get("message", {}).get("content") if r.get("type") == "assistant" else None
                for b in blocks if isinstance(blocks, list) else []:
                    if b.get("type") == "tool_use":
                        n += 1
                        if b["name"] == _CC_NAME[tv.SHELL]:
                            kept.add(n)
                if r.get("rec") == "agent-run":
                    n += 1
            evs = [e for e in tv.events(h, lines) if e.kind != tv.TOOL_CALL or e.call in kept]
            return tpa.pa.grade(evs, {"wait_points": tpa.WPS}, case[0][1])
        self.assertEqual(tpa.seam_problems(tpa.view_pipeline()), [])
        problems = tpa.seam_problems(hybrid)
        self.assertTrue(problems)
        self.assertTrue(all(p.startswith(FAKE + ": ") for p in problems), problems)
        self.assertFalse([p for p in problems if "refused" in p])


def round3_takes():
    """Round 3's committed transcripts with their ledgers, opened in the working tree (the named exception)."""
    out = []
    for task in ("confounded-design", "scope-read", "template-adherence"):
        for half in ("control", "positive"):
            base = ROUND3 / "transcripts" / task / half
            for model in sorted(os.listdir(base)):
                for take in sorted(os.listdir(base / model)):
                    out.append(base / model / take)
    return out


class RoundThree(unittest.TestCase):
    def test_every_round3_transcript_reads_and_binds_to_its_ledger(self):
        takes = round3_takes()
        self.assertEqual(len(takes), 54)
        kinds = {}
        for t in takes:
            evs = tv.events(CC, t / "transcript.jsonl")
            led = json.loads((t / "driver-ledger.json").read_text())
            tv.require_operator_lines(evs, [x["sent"] for x in led["turns"]])
            for e in evs:
                kinds[e.kind] = kinds.get(e.kind, 0) + 1
        # Counted once by this lane's survey of the 54 files (e2979b31), and pinned here.
        self.assertEqual(kinds, {tv.HARNESS: 3350, tv.TOOL_CALL: 812, tv.TOOL_RESULT: 812, tv.AGENT_REASONING: 625,
                                 tv.AGENT_TEXT: 431, tv.OPERATOR: 178})

    def test_the_binding_fires_on_a_ledger_whose_n_is_used_as_the_turn(self):
        t = ROUND3 / "transcripts/confounded-design/control/claude-haiku-4-5-20251001/1"
        evs = tv.events(CC, t / "transcript.jsonl")
        led = json.loads((t / "driver-ledger.json").read_text())
        ns = [x["n"] for x in led["turns"]]
        self.assertNotEqual(len(set(ns)), len(ns), "this take's ledger repeats n on its recovery turn")
        self.assertEqual(max(e.turn for e in evs), len(led["turns"]))
        with self.assertRaises(tv.ViewError):
            tv.require_operator_lines(evs, [x["sent"] for x in led["turns"]][:max(ns)])

    def test_harness_types_counts_only_harness_records(self):
        t = ROUND3 / "transcripts/scope-read/control/claude-haiku-4-5-20251001/1/transcript.jsonl"
        types = tv.harness_types(CC, t)
        n_harness = sum(e.kind == tv.HARNESS for e in tv.events(CC, t))
        self.assertEqual(sum(types.values()), n_harness)
        self.assertNotIn("assistant", types)
        self.assertNotIn("user", types)


if __name__ == "__main__":
    unittest.main()
