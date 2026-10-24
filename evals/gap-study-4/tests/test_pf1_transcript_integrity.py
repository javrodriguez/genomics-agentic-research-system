#!/usr/bin/env python3
"""Lane pf1-l3-transcript-integrity (Gap Study round 4; fold plan prefreeze-1, the lane orchestrator's approval of
Sat 24 Oct 2026 under Javier's standing delegation): pre-freeze review 1's MAJOR 7.

The graded record sits on the take's read-write config mount, owned by the agent's uid, and the cross-checks bound ids
only, so one in-take command that rewrote a reply's words passed. What is tested:

  T1-units      claude_code_adapter.content_problems: a session file equal to its streams, turn by turn, is []; each
                content kind rewritten in the session file (a text, a thinking block, a tool_use input, a tool_result's
                content and its is_error), a record moved to another turn, an injected assistant record, a record cut
                to a non-JSON line, a unit before the first operator line, and an operator line too many are each a
                problem; a sub-agent's stream records and a sidechain session record are not the main thread.
  T2-c6         claude_code_adapter.cross_check carries the content comparison, and a turn record without content
                units is a problem (fail closed); the adapter's own turn records carry the stream's units.
  T3-walks      every committed claude-code walk's transcript equals its streams (check_take.transcript_content_problems
                is []), every committed codex walk's commands and every readable gemini walk's tool-result outputs
                equal their native records (check_take.vendor_content_problems is []), w-g24 reads unreadable.
  T4-rewrites   on copies of committed walks: a reply's words rewritten in w125's transcript.jsonl, a command's argv
                rewritten in w-o46's rollout and a stream command rewritten (its envelope digest kept true), and a tool
                result display rewritten in w-g21's native session are each refused [transcript-mismatch].
  T5-wired      the readings sit on check4's and check4_walk's claude-code roads and in vendor_round4_problems.

Witnesses: each check is replaced by one that passes everything, and the rewrites above then pass (red), so every
check here is shown to bite. Reads committed files only; no process, network, model or credential.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(HERE / "tests") not in sys.path:
    sys.path.insert(0, str(HERE / "tests"))

import check_take as ct  # noqa: E402
import claude_code_adapter as cca  # noqa: E402
import test_claude_code_adapter as tca  # noqa: E402

WALKS = HERE / "rehearsals"
CLAUDE_WALK, CODEX_WALK, GEMINI_WALK = "w125", "w-o46", "w-g21"
UNREADABLE_GEMINI = {"w-g24"}       # its native snapshot ends on tool calls; its other readers say so too


def setUpModule():
    tca.setUpModule()


def tearDownModule():
    tca.tearDownModule()


def jsonl(recs) -> str:
    return "".join(json.dumps(r) + "\n" for r in recs)


def assistant(mid, blocks, *, stream=True, **extra):
    rec = {"type": "assistant", "message": {"id": mid, "model": "claude-opus-5-5", "content": blocks}}
    rec.update({"session_id": "s"} if stream else {"sessionId": "s", "requestId": "r-" + mid})
    rec.update(extra)
    return rec


def result(tid, content, *, stream=True, error=False, **extra):
    rec = {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tid, "content": content, "is_error": error}]}}
    rec.update({"session_id": "s"} if stream else {"sessionId": "s"})
    rec.update(extra)
    return rec


def operator(line):
    return {"type": "user", "sessionId": "s", "message": {"role": "user", "content": line}}


TEXT = {"type": "text", "text": "Starting stage 01."}
THINK = {"type": "thinking", "thinking": "I should read the context first.", "signature": "x"}
CALL = {"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": {"command": "cat CONTEXT.md"}}
CALL2 = {"type": "tool_use", "id": "toolu_2", "name": "Read", "input": {"file_path": "a.md"}}


def two_turns():
    """(turn streams, session records): turn 1 thinks, says, calls and gets a result; turn 2 calls and answers."""
    s1 = [{"type": "system", "subtype": "init", "session_id": "s"}, assistant("m1", [THINK]),
          assistant("m1", [TEXT]), assistant("m1", [CALL]), result("toolu_1", "# Context"),
          assistant("m2", [{"type": "text", "text": "Done."}]),
          # a sub-agent's records are not the main thread
          {"type": "assistant", "parent_tool_use_id": "toolu_x", "session_id": "s",
           "message": {"id": "sub", "model": "claude-opus-5-5", "content": [{"type": "text", "text": "sub"}]}},
          {"type": "result", "subtype": "success", "session_id": "s"}]
    s2 = [assistant("m3", [CALL2]), result("toolu_2", [{"type": "text", "text": "body"}]),
          assistant("m4", [{"type": "text", "text": "The answer."}])]
    sess = [{"type": "queue-operation", "content": "x"}, operator("Please start."),
            assistant("m1", [THINK], stream=False), assistant("m1", [TEXT], stream=False),
            assistant("m1", [CALL], stream=False), result("toolu_1", "# Context", stream=False, toolUseResult={"a": 1}),
            assistant("m2", [{"type": "text", "text": "Done."}], stream=False),
            {"type": "attachment", "attachment": {"type": "edited_text_file", "filename": "a"}},
            assistant("sc", [{"type": "text", "text": "side"}], stream=False, isSidechain=True),
            operator("go on"),
            assistant("m3", [CALL2], stream=False), result("toolu_2", [{"type": "text", "text": "body"}], stream=False),
            assistant("m4", [{"type": "text", "text": "The answer."}], stream=False)]
    return [jsonl(s1), jsonl(s2)], sess


def problems(streams, sess_recs=None, sess_text=None):
    text = jsonl(sess_recs) if sess_text is None else sess_text
    return cca.content_problems([cca.stream_content_units(t) for t in streams], text)


def edited(sess, k, fn):
    out = copy.deepcopy(sess)
    fn(out[k])
    return out


def rewrites():
    """(name, session records) for every rewrite T1 must refuse; the streams are two_turns()'s."""
    _, sess = two_turns()
    moved = copy.deepcopy(sess)
    moved.insert(9, moved.pop(4))                         # turn 1's tool call moved after the operator line of turn 2
    injected = copy.deepcopy(sess)
    injected.insert(6, assistant("m9", [{"type": "text", "text": "I declined."}], stream=False))
    cut = jsonl(sess).split("\n")
    cut[5] = cut[5][:40]                                  # the tool_result record cut to a non-JSON line
    early = copy.deepcopy(sess)
    early.insert(1, assistant("m0", [{"type": "text", "text": "before"}], stream=False))
    extra_op = copy.deepcopy(sess) + [operator("one more")]
    return [
        ("text", edited(sess, 3, lambda r: r["message"]["content"][0].update(text="Stopping before stage 01."))),
        ("thinking", edited(sess, 2, lambda r: r["message"]["content"][0].update(thinking="Skip it."))),
        ("tool-input", edited(sess, 4, lambda r: r["message"]["content"][0]["input"].update(command="ls"))),
        ("tool-name", edited(sess, 4, lambda r: r["message"]["content"][0].update(name="Read"))),
        ("tool-result", edited(sess, 5, lambda r: r["message"]["content"][0].update(content="Zero rows."))),
        ("tool-result-error", edited(sess, 5, lambda r: r["message"]["content"][0].update(is_error=True))),
        ("list-result", edited(sess, 11, lambda r: r["message"]["content"][0]["content"][0].update(text="x"))),
        ("dropped", [r for k, r in enumerate(sess) if k != 12]),
        ("moved", moved), ("injected", injected), ("cut", "\n".join(cut)), ("before-first-operator", early),
        ("operator-line-too-many", extra_op),
    ]


class T1Units(unittest.TestCase):
    def test_equal_is_clean(self):
        streams, sess = two_turns()
        self.assertEqual(problems(streams, sess), [])

    def test_every_rewrite_is_refused(self):
        streams, _ = two_turns()
        for name, sess in rewrites():
            got = problems(streams, sess_text=sess) if isinstance(sess, str) else problems(streams, sess)
            self.assertNotEqual(got, [], name)

    def test_the_words_never_enter_a_problem(self):
        streams, _ = two_turns()
        for name, sess in rewrites():
            got = problems(streams, sess_text=sess) if isinstance(sess, str) else problems(streams, sess)
            for words in ("Stopping before", "Skip it", "I declined", "Zero rows"):
                self.assertFalse(any(words in g for g in got), (name, got))

    def test_a_turn_stream_missing_is_refused(self):
        streams, sess = two_turns()
        self.assertNotEqual(problems(streams[:1], sess), [])

    def test_a_stream_rewritten_is_refused(self):
        streams, sess = two_turns()
        self.assertNotEqual(problems([streams[0].replace("# Context", "# Other"), streams[1]], sess), [])

    def test_the_main_thread_only(self):
        streams, sess = two_turns()
        units = cca.stream_content_units(streams[0])
        self.assertNotIn("sub", json.dumps(units))
        self.assertNotIn("side", json.dumps(cca.session_content_turns(jsonl(sess))))
        self.assertEqual([u[0] for u in units], ["thinking", "text", "tool_use", "tool_result", "text"])

    def test_witness_a_comparison_that_ignores_content_passes_a_rewrite(self):
        streams, sess = two_turns()
        bad = rewrites()[0][1]
        with mock.patch.object(cca, "_units", lambda rec: [("x",)] if rec.get("type") == "assistant" else []):
            self.assertEqual(problems(streams, bad), [], "witness not performed")
        self.assertNotEqual(problems(streams, bad), [])


class T2CrossCheck(unittest.TestCase):
    def records(self, streams):
        return [{"session_ids": ["s"], "calls": [], "tool_use_ids": [], "content_units": cca.stream_content_units(t)}
                for t in streams]

    def test_c6_carries_the_comparison(self):
        streams, sess = two_turns()
        clean = cca.cross_check(self.records(streams), jsonl(sess), session_id="s")
        self.assertFalse(any("content" in g for g in clean), clean)
        bad = rewrites()[0][1]
        got = cca.cross_check(self.records(streams), jsonl(bad), session_id="s")
        self.assertTrue(any("differs from the host-captured stream" in g for g in got), got)

    def test_a_record_without_units_fails_closed(self):
        streams, sess = two_turns()
        recs = self.records(streams)
        del recs[1]["content_units"]
        got = cca.cross_check(recs, jsonl(sess), session_id="s")
        self.assertTrue(any("carry no content units" in g for g in got), got)

    def test_the_adapter_records_the_streams_units(self):
        box = tca.FakeRuntime([tca.synthetic_turn(msg="m1", req="r1", tool=True)], exit_codes=[0])
        a = tca.adapter(cca, box)
        a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
        t1 = a.turn("one", first=True, budget_s=60)
        want = cca.stream_content_units(Path(t1.stream_path).read_text(encoding="utf-8"))
        self.assertEqual(a.turn_records[0]["content_units"], want)
        self.assertEqual([u[0] for u in want], ["text", "tool_use"])


def committed(harness):
    out = []
    for d in sorted(WALKS.iterdir()):
        led = d / "driver-ledger.json"
        if led.is_file() and (json.loads(led.read_text()).get("agent") or {}).get("harness") == harness:
            out.append(d)
    return out


class T3Walks(unittest.TestCase):
    def test_every_claude_walk_agrees(self):
        walks = committed("claude-code")
        self.assertEqual(len(walks), 151)
        bad = {d.name: ct.transcript_content_problems(d / "transcript.jsonl") for d in walks}
        self.assertEqual({k: v for k, v in bad.items() if v}, {})

    def test_every_codex_walk_agrees(self):
        walks = committed("codex")
        self.assertEqual(len(walks), 38)
        bad = {d.name: ct.vendor_content_problems(d / "transcript.jsonl", "codex") for d in walks}
        self.assertEqual({k: v for k, v in bad.items() if v}, {})

    def test_every_readable_gemini_walk_agrees(self):
        walks = committed("gemini")
        self.assertEqual(len(walks), 36)
        got = {d.name: ct.vendor_content_problems(d / "transcript.jsonl", "gemini") for d in walks}
        self.assertEqual({k: v for k, v in got.items() if v and k not in UNREADABLE_GEMINI}, {})
        for k in UNREADABLE_GEMINI:
            self.assertEqual([g[:len("[transcript-unreadable]")] for g in got[k]], ["[transcript-unreadable]"], got[k])


class Copied:
    """A committed walk copied into a scratch folder, so a rewrite never touches the study."""

    def __init__(self, name):
        self.tmp = tempfile.mkdtemp(prefix="pf1-l3-")
        self.dir = Path(shutil.copytree(WALKS / name, Path(self.tmp) / name))
        self.path = self.dir / "transcript.jsonl"

    def close(self):
        shutil.rmtree(self.tmp)

    def rebind_snapshot(self):
        """Keep the ledger's digest of the last native snapshot true after a rewrite (the attack under test is a
        rewrite of the native store before the driver snapshots it, so the snapshot binds the rewritten bytes)."""
        led = json.loads((self.dir / "driver-ledger.json").read_text())
        snap = led["native_snapshots"][-1]
        snap["sha256"] = hashlib.sha256((self.dir / "session" / snap["file"]).read_bytes()).hexdigest()
        (self.dir / "driver-ledger.json").write_text(json.dumps(led))
        return snap["file"]

    def rebind_stream(self, name):
        envs = [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()]
        for e in envs:
            if e["stream"] == name:
                e["sha256"] = hashlib.sha256((self.dir / name).read_bytes()).hexdigest()
        self.path.write_text("".join(json.dumps(e) + "\n" for e in envs))


def rewrite_lines(path: Path, fn) -> bool:
    """Apply fn to each JSON line until it returns True for one; write the file back; True when one changed."""
    lines = path.read_text(encoding="utf-8").split("\n")
    for k, line in enumerate(lines):
        if not line.strip():
            continue
        rec = json.loads(line)
        if fn(rec):
            lines[k] = json.dumps(rec, ensure_ascii=False)
            path.write_text("\n".join(lines), encoding="utf-8")
            return True
    return False


def _claude_text(rec):
    if rec.get("type") != "assistant":
        return False
    for b in (rec.get("message") or {}).get("content") or []:
        if b.get("type") == "text" and b.get("text"):
            b["text"] = "I will not run that."
            return True
    return False


def _codex_native_cmd(rec):
    item = (rec.get("payload") or {}).get("item") or {}
    if item.get("type") == "CommandExecution":
        item["command"] = item["command"][:-1] + ["true"]
        return True
    return False


def _codex_stream_cmd(rec):
    item = rec.get("item") or {}
    if rec.get("type") == "item.completed" and item.get("type") == "command_execution":
        item["command"] = "/bin/bash -lc true"
        return True
    return False


def _gemini_display(rec):
    for m in [rec] + list(rec.get("messages") or []) if isinstance(rec, dict) else []:
        for t in m.get("toolCalls") or []:
            if isinstance(t.get("resultDisplay"), str) and t["resultDisplay"]:
                t["resultDisplay"] = "No such file."
                return True
    return False


class T4Rewrites(unittest.TestCase):
    def test_claude_reply_rewritten(self):
        w = Copied(CLAUDE_WALK)
        try:
            self.assertEqual(ct.transcript_content_problems(w.path), [])
            self.assertTrue(rewrite_lines(w.path, _claude_text))
            got = ct.transcript_content_problems(w.path)
            self.assertTrue(got and all(g.startswith("[transcript-mismatch] turn ") for g in got), got)
            self.assertEqual(ct.reason_ids(got), [ct.TRANSCRIPT_MISMATCH] * len(got))
        finally:
            w.close()

    def test_codex_rollout_argv_rewritten(self):
        w = Copied(CODEX_WALK)
        try:
            led = json.loads((w.dir / "driver-ledger.json").read_text())
            self.assertTrue(rewrite_lines(w.dir / "session" / led["native_snapshots"][-1]["file"], _codex_native_cmd))
            w.rebind_snapshot()
            got = ct.vendor_content_problems(w.path, "codex")
            self.assertEqual(ct.reason_ids(got), [ct.TRANSCRIPT_MISMATCH], got)
        finally:
            w.close()

    def test_codex_stream_command_rewritten(self):
        w = Copied(CODEX_WALK)
        try:
            self.assertTrue(rewrite_lines(w.dir / "turn-1.jsonl", _codex_stream_cmd))
            w.rebind_stream("turn-1.jsonl")
            got = ct.vendor_content_problems(w.path, "codex")
            self.assertEqual(ct.reason_ids(got), [ct.TRANSCRIPT_MISMATCH], got)
        finally:
            w.close()

    def test_gemini_display_rewritten(self):
        w = Copied(GEMINI_WALK)
        try:
            led = json.loads((w.dir / "driver-ledger.json").read_text())
            native = w.dir / "session" / led["native_snapshots"][-1]["file"]
            self.assertTrue(rewrite_lines(native, _gemini_display))
            w.rebind_snapshot()
            got = ct.vendor_content_problems(w.path, "gemini")
            self.assertEqual(ct.reason_ids(got), [ct.TRANSCRIPT_MISMATCH], got)
        finally:
            w.close()

    def test_an_unbound_snapshot_reads_unreadable(self):
        w = Copied(GEMINI_WALK)
        try:
            led = json.loads((w.dir / "driver-ledger.json").read_text())
            rewrite_lines(w.dir / "session" / led["native_snapshots"][-1]["file"], _gemini_display)
            got = ct.vendor_content_problems(w.path, "gemini")         # digest not rebound: never read as clean
            self.assertEqual(ct.reason_ids(got), [ct.TRANSCRIPT_UNREADABLE], got)
        finally:
            w.close()

    def test_witness_checks_that_pass_everything_pass_the_rewrites(self):
        w = Copied(CODEX_WALK)
        try:
            self.assertTrue(rewrite_lines(w.dir / "turn-1.jsonl", _codex_stream_cmd))
            w.rebind_stream("turn-1.jsonl")
            with mock.patch.object(ct._shlex, "split", lambda s: None), \
                    mock.patch.object(ct, "_codex_command_problems", lambda texts, raw: []):
                self.assertEqual(ct.vendor_content_problems(w.path, "codex"), [], "witness not performed")
        finally:
            w.close()
        w = Copied(CLAUDE_WALK)
        try:
            rewrite_lines(w.path, _claude_text)
            with mock.patch.object(cca, "content_problems", lambda units, text: []):
                self.assertEqual(ct.transcript_content_problems(w.path), [], "witness not performed")
        finally:
            w.close()


class T5Wired(unittest.TestCase):
    def test_on_both_claude_roads_and_the_vendor_readings(self):
        for fn in (ct.check4, ct.check4_walk):
            src = inspect.getsource(fn)
            self.assertIn("problems += transcript_content_problems(path)", src, fn.__name__)
            self.assertLess(src.index("if design.harness == CLAUDE_CODE:"),
                            src.index("problems += transcript_content_problems(path)"), fn.__name__)
        self.assertIn("vendor_content_problems(path, harness)", inspect.getsource(ct.vendor_round4_problems))

    def test_the_reason_is_an_operator_reason_with_its_row(self):
        import routing
        table = routing.load_table()
        self.assertIn(ct.TRANSCRIPT_MISMATCH, table["operator_reasons"])
        self.assertIn(ct.TRANSCRIPT_MISMATCH, table["operator_reasons_round4"]["ids"])
        self.assertEqual([r["route"] for r in table["rows"] if r["id"] == ct.TRANSCRIPT_MISMATCH], ["aborted"])
        self.assertNotIn(ct.TRANSCRIPT_MISMATCH, ct.CONSTANT_BOUND_REASONS)


if __name__ == "__main__":
    unittest.main(verbosity=1)
