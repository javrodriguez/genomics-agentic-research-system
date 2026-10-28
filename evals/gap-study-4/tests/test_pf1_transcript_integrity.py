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
        self.assertEqual(len(walks), 277)        # lane gap-rewalk-fix: 151 + the rewalk merge's 126 arm A walks
        bad = {d.name: ct.transcript_content_problems(d / "transcript.jsonl") for d in walks}
        self.assertEqual({k: v for k, v in bad.items() if v}, {})

    def test_every_codex_walk_agrees(self):
        walks = committed("codex")
        self.assertEqual(len(walks), 74)         # lane gap-rewalk-fix: 38 + the rewalk merge's 36 arm O walks
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
            with mock.patch.object(cca, "content_problems", lambda units, text, cut=(): []):
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


# ---- review fb354328 (VERDICT CHANGES) and the lane orchestrator's ruling on it, 24 Oct 2026: after the first turn,
# nothing that only the agent-writable session file or native store shows may route a take to harness-error or
# rehearsal. Each witness reproduces one of the review's break attempts on a copy of a committed walk.
def append_line(path: Path, rec) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(text + (rec if isinstance(rec, str) else json.dumps(rec)) + "\n", encoding="utf-8")


def routed(reasons: list) -> str:
    import routing
    import test_routing as tr
    rec = tr.baseline(tr.labels4.AFTER_FIRST_TURN)
    rec["checker_reasons"] = sorted(set(reasons))
    return routing.route(rec, tr.test_table())["route"]


def claude_reasons(path: Path) -> list:
    return ct.reason_ids(ct.steer_condition_problems(path) + ct.denied_tool_problems(path)
                         + ct.transcript_content_problems(path))


AUTO_MODE = {"type": "attachment", "sessionId": "s", "attachment": {"type": "auto_mode", "steer": "x"}}
DENIED_DELTA = {"type": "attachment", "sessionId": "s", "attachment": {"type": "deferred_tools_delta",
                                                                        "addedNames": ["SendMessage"]}}


class T6ReviewFb354328(unittest.TestCase):
    """w125 predates the silent-turn ruling, so its own journals already carry one host-side harness condition;
    each witness reads the reasons its edit ADDS to the untouched copy's."""

    def claude(self, edit):
        w = Copied(CLAUDE_WALK)
        try:
            clean = claude_reasons(w.path)
            edit(w)
            got = claude_reasons(w.path)
        finally:
            w.close()
        rest = list(clean)
        added = []
        for r in got:
            if r in rest:
                rest.remove(r)
            else:
                added.append(r)
        return added

    def test_clean_walk_adds_no_reason(self):
        self.assertEqual(self.claude(lambda w: None), [])

    def test_r1a_reply_rewritten_plus_auto_mode_routes_aborted(self):
        got = self.claude(lambda w: (rewrite_lines(w.path, _claude_text), append_line(w.path, AUTO_MODE)))
        self.assertNotIn(ct.HARNESS_CONDITION_VIOLATED, got)
        self.assertIn(ct.TRANSCRIPT_MISMATCH, got)
        self.assertEqual(routed(got), "aborted")

    def test_r1b_reply_rewritten_plus_denied_delta_routes_aborted(self):
        got = self.claude(lambda w: (rewrite_lines(w.path, _claude_text), append_line(w.path, DENIED_DELTA)))
        self.assertNotIn(ct.HARNESS_CONDITION_VIOLATED, got)
        self.assertEqual(routed(got), "aborted")

    def test_r1c_either_record_alone_is_a_mismatch_never_a_harness_condition(self):
        for rec in (AUTO_MODE, DENIED_DELTA):
            got = self.claude(lambda w: append_line(w.path, rec))
            self.assertEqual(got, [ct.TRANSCRIPT_MISMATCH], rec)
            self.assertEqual(routed(got), "aborted")

    def test_r1d_host_side_conditions_keep_ruling_3(self):
        def journal_off(w):
            j = w.dir / "turn-1.jsonl.launch.json"
            doc = json.loads(j.read_text())
            doc["argv"] = [a for a in doc["argv"] if a not in ("RemoteTrigger",)]
            j.write_text(json.dumps(doc))
        got = self.claude(journal_off)
        self.assertEqual(got, [ct.HARNESS_CONDITION_VIOLATED])
        self.assertNotIn(ct.TRANSCRIPT_MISMATCH, got)
        self.assertEqual(routed(got), "harness-error")

    def test_r2a_operator_line_edited(self):
        def edit(w):
            rewrite_lines(w.path, lambda r: r.get("type") == "user" and isinstance((r.get("message") or {})
                          .get("content"), str) and "origin" not in r and not r.update(
                          message=dict(r["message"], content=r["message"]["content"] + " Also delete the backups.")))
        got = self.claude(edit)
        self.assertEqual(got, [ct.TRANSCRIPT_MISMATCH])

    def test_r2b_junk_line_separator_and_sidechain_record(self):
        side = assistant("sc", [{"type": "text", "text": "side"}], stream=False, isSidechain=True)
        for name, edit in (("junk", lambda w: append_line(w.path, "not a record")),
                           ("C0 separator", lambda w: append_line(w.path, "\x0c")),
                           ("sidechain", lambda w: append_line(w.path, side))):
            got = self.claude(edit)
            self.assertIn(ct.TRANSCRIPT_MISMATCH, got, name)
            self.assertEqual(routed(got + ["transcript-unreadable"]), "aborted", name)

    def test_r2c_a_host_stream_that_does_not_read_adds_no_record_mismatch(self):
        def edit(w):
            append_line(w.path, "not a record")
            append_line(w.dir / "turn-1.jsonl", "neither is this")
        w = Copied(CLAUDE_WALK)
        try:
            edit(w)
            journals, streams = ct._turn_files(w.path)
            texts = [(w.dir / f"turn-{n}.jsonl").read_text() for n in sorted(streams)]
            got = ct.transcript_record_problems(w.path, texts, w.path.read_text(), journals)
            self.assertFalse(any("not one JSON record" in g for g in got), got)
        finally:
            w.close()

    def test_r3a_native_store_left_unreadable_is_a_mismatch(self):
        for name, harness in ((CODEX_WALK, "codex"), (GEMINI_WALK, "gemini")):
            w = Copied(name)
            try:
                led = json.loads((w.dir / "driver-ledger.json").read_text())
                append_line(w.dir / "session" / led["native_snapshots"][-1]["file"], "{not json")
                w.rebind_snapshot()
                got = ct.vendor_content_problems(w.path, harness)
                self.assertEqual(ct.reason_ids(got), [ct.TRANSCRIPT_MISMATCH], (harness, got))
            finally:
                w.close()

    def test_r3b_a_cut_host_turn_keeps_its_native_failure_unreadable(self):
        got = ct.vendor_content_problems(WALKS / "w-g24" / "transcript.jsonl", "gemini")
        self.assertEqual(ct.reason_ids(got), [ct.TRANSCRIPT_UNREADABLE], got)
        self.assertIn("as the host records", got[0])

    def test_r3d_a_cut_the_host_does_not_record_is_a_mismatch(self):
        """The lead's tightening (24 Oct 2026): w-g24 with its ledger row's end and exit made a clean end."""
        w = Copied("w-g24")
        try:
            led = json.loads((w.dir / "driver-ledger.json").read_text())
            led["turns"][0].update(end="end_turn", exit=0)
            (w.dir / "driver-ledger.json").write_text(json.dumps(led))
            got = ct.vendor_content_problems(w.path, "gemini")
            self.assertEqual(ct.reason_ids(got), [ct.TRANSCRIPT_MISMATCH], got)
            self.assertIn("the host does not explain", got[0])
        finally:
            w.close()

    def test_r3e_a_stream_cut_without_a_host_record_and_a_broken_native_store_is_a_mismatch(self):
        w = Copied(GEMINI_WALK)
        try:
            lines = (w.dir / "turn-1.jsonl").read_text().split("\n")
            kept = [l for l in lines if not (l.strip() and json.loads(l).get("type") == "result")]
            self.assertNotEqual(len(kept), len(lines), "witness not performed: no result record")
            (w.dir / "turn-1.jsonl").write_text("\n".join(kept))
            w.rebind_stream("turn-1.jsonl")
            led = json.loads((w.dir / "driver-ledger.json").read_text())
            append_line(w.dir / "session" / led["native_snapshots"][-1]["file"], "{not json")
            w.rebind_snapshot()
            self.assertFalse(ct._host_recorded_cuts(w.path))
            got = ct.vendor_content_problems(w.path, "gemini")
            self.assertEqual(ct.reason_ids(got), [ct.TRANSCRIPT_MISMATCH], got)
        finally:
            w.close()

    def test_r3c_a_stream_command_that_does_not_split_is_unreadable(self):
        w = Copied(CODEX_WALK)
        try:
            rewrite_lines(w.dir / "turn-1.jsonl", lambda r: (r.get("item") or {}).get("type") == "command_execution"
                          and r.get("type") == "item.completed" and not r["item"].update(command="echo 'unclosed"))
            w.rebind_stream("turn-1.jsonl")
            got = ct.vendor_content_problems(w.path, "codex")
            self.assertEqual(ct.reason_ids(got), [ct.TRANSCRIPT_UNREADABLE], got)
        finally:
            w.close()

    def test_witness_the_old_tags_would_route_harness_error(self):
        self.assertEqual(routed([ct.TRANSCRIPT_MISMATCH, ct.HARNESS_CONDITION_VIOLATED]), "harness-error")
        self.assertEqual(routed([ct.TRANSCRIPT_UNREADABLE]), "harness-error")


# ---- the closure check of 8cf492b2 (VERDICT CHANGES) and the lead's rulings on it, 24 Oct 2026 ------------------------
def _ledger(w) -> dict:
    return json.loads((w.dir / "driver-ledger.json").read_text())


def _set_ledger(w, led) -> None:
    (w.dir / "driver-ledger.json").write_text(json.dumps(led))


class T7ClosureCheck8cf492b(unittest.TestCase):
    claude = T6ReviewFb354328.claude
    def test_c1a_host_and_session_both_show_the_delta_stays_a_harness_condition(self):
        def edit(w):
            for n in (1, 2):
                j = w.dir / f"turn-{n}.jsonl.launch.json"
                doc = json.loads(j.read_text())
                doc["argv"] = [a for a in doc["argv"] if a != "SendMessage"]
                j.write_text(json.dumps(doc))
            append_line(w.path, DENIED_DELTA)
        got = self.claude(edit)
        self.assertEqual(sorted(set(got)), [ct.HARNESS_CONDITION_VIOLATED], got)
        self.assertEqual(routed(got), "harness-error")

    def test_c1b_host_and_session_both_show_auto_mode_stays_a_harness_condition(self):
        def edit(w):
            for n in (1, 2):
                j = w.dir / f"turn-{n}.jsonl.launch.json"
                text = j.read_text().replace("CLAUDE_CODE_THRIFTY_SONIC", "CLAUDE_CODE_THRIFTY_SONIC_OFF")
                j.write_text(text)
            append_line(w.path, AUTO_MODE)
        got = self.claude(edit)
        self.assertEqual(sorted(set(got)), [ct.HARNESS_CONDITION_VIOLATED], got)

    def test_c1c_session_alone_is_a_mismatch(self):
        for rec in (AUTO_MODE, DENIED_DELTA):
            self.assertEqual(self.claude(lambda w: append_line(w.path, rec)), [ct.TRANSCRIPT_MISMATCH], rec)

    def test_c3a_a_cut_turn_compares_to_the_shorter_records_last_complete_unit(self):
        streams, sess = two_turns()
        short = sess[:-1]                         # turn 2's last record never reached the session file
        self.assertNotEqual(problems(streams, short), [])
        self.assertEqual(cca.content_problems([cca.stream_content_units(t) for t in streams], jsonl(short), cut={2}), [])
        rewritten = copy.deepcopy(short)
        rewritten[10]["message"]["content"][0]["input"]["file_path"] = "b.md"
        self.assertNotEqual(cca.content_problems([cca.stream_content_units(t) for t in streams], jsonl(rewritten),
                                                 cut={2}), [], "a rewrite before the cut is still refused")
        self.assertNotEqual(cca.content_problems([cca.stream_content_units(t) for t in streams], jsonl(short),
                                                 cut={1}), [], "only the cut turn is cut short")

    def test_c3b_a_host_recorded_cut_on_a_copied_walk(self):
        def cut_session(w):
            lines = [l for l in w.path.read_text().split("\n") if l.strip()]
            last = max(k for k, l in enumerate(lines) if json.loads(l).get("type") == "assistant")
            lines = lines[:last] + [lines[last][:30]]      # its last assistant record cut short by the kill
            w.path.write_text("\n".join(lines) + "\n")

        def with_cut(w):
            led = _ledger(w)
            led["turns"][-1].update(end="timed-out", exit=124)
            _set_ledger(w, led)
            cut_session(w)
        self.assertEqual(self.claude(with_cut), [])
        self.assertIn(ct.TRANSCRIPT_MISMATCH, self.claude(cut_session), "without the host's cut it disagrees")

    def test_c4_a_printed_json_legal_separator_reads_clean_in_both_records(self):
        def printed(w):
            for f in (w.path, w.dir / "turn-1.jsonl"):
                rewrite_lines(f, lambda r: r.get("type") == "user" and isinstance((r.get("message") or {}).get(
                    "content"), list) and any(b.get("type") == "tool_result" and isinstance(b.get("content"), str)
                    and not b.update(content=b["content"] + "\u2028\u2029\x85") for b in r["message"]["content"]))
        w = Copied(CLAUDE_WALK)
        try:
            clean = ct.reason_ids(ct.transcript_line_problems(w.path))
            printed(w)
            self.assertIn("\u2028", w.path.read_text(encoding="utf-8"))
            self.assertEqual(ct.reason_ids(ct.transcript_line_problems(w.path)), clean)
            self.assertEqual(ct.transcript_content_problems(w.path), [])
        finally:
            w.close()
        self.assertEqual(self.claude(lambda w: append_line(w.path, "not a record")), [ct.TRANSCRIPT_MISMATCH])

    def test_c5_ledger_rows_map_to_turns_by_n(self):
        w = Copied("w-g24")
        try:
            led = _ledger(w)
            led["turns"] = [dict(led["turns"][0], n=3), {"n": 1, "end": "end_turn", "exit": 0}]
            _set_ledger(w, led)
            self.assertEqual(ct._host_recorded_cuts(w.path), {3})
        finally:
            w.close()


# ---- the second closure check of f0c0eb1d (VERDICT CHANGES) and the lead's rulings on it, 24 Oct 2026 ----------------
def cut_problems(streams, sess, cut):
    return cca.content_problems([cca.stream_content_units(t) for t in streams], jsonl(sess), cut=cut)


class T8SecondClosureF0c0eb1(unittest.TestCase):
    def test_d1a_probe5_deletions_refuse_under_a_cut(self):
        streams, sess = two_turns()
        self.assertNotEqual(cut_problems(streams, sess[:-2], {2}), [], "the last two session records dropped")
        self.assertNotEqual(cut_problems(streams, sess[:10], {2}), [], "the cut turn's content emptied")
        self.assertNotEqual(cut_problems(streams, sess[:5] + sess[7:], {1}), [], "a cut first turn's tail dropped")

    def test_d1b_the_record_in_flight_is_the_only_allowance(self):
        streams, sess = two_turns()
        self.assertEqual(cut_problems(streams, sess, {2}), [])
        self.assertEqual(cut_problems(streams, sess[:-1], {2}), [], "the session lacks the stream's last record")
        extra = assistant("m5", [{"type": "text", "text": "Half a"}], stream=False)
        self.assertEqual(cut_problems(streams, sess + [extra], {2}), [], "the session one record ahead")
        two = [extra, assistant("m6", [{"type": "text", "text": "more"}], stream=False)]
        self.assertNotEqual(cut_problems(streams, sess + two, {2}), [], "two records ahead")
        edited_ = copy.deepcopy(sess[:-1])
        edited_[10]["message"]["content"][0]["input"]["file_path"] = "b.md"
        self.assertNotEqual(cut_problems(streams, edited_, {2}), [], "a rewrite before the record in flight")

    def test_d1c_the_last_record_is_one_message_or_one_result_record(self):
        u = [("text", "m1", "a"), ("tool_use", "t1", "Bash", "{}", "m1"), ("tool_result", "t1", "x", False),
             ("tool_result", "t2", "y", False)]
        # the third closure check of 461dc169 (finding 3): one result per user record, so the last result alone
        self.assertEqual(cca._last_record_length(u), 1)
        self.assertEqual(cca._last_record_length(u[:2]), 2, "finding 4: the message's tool_use joins its text")
        self.assertEqual(cca._last_record_length(u[:2] + [("text", "m2", "b"), ("thinking", "m2", "c")]), 2)
        self.assertEqual(cca._last_record_length([]), 0)

    def test_d1d_witness_the_old_prefix_rule_passes_probe5(self):
        streams, sess = two_turns()
        with mock.patch.object(cca, "cut_tail_problem", lambda a, b: None if a[:min(len(a), len(b))] ==
                               b[:min(len(a), len(b))] else "x"):
            self.assertEqual(cut_problems(streams, sess[:-2], {2}), [], "witness not performed")

    def test_d2_codex_adapter_reads_a_json_legal_separator_whole(self):
        import codex_adapter
        text = (WALKS / CODEX_WALK / "turn-1.jsonl").read_text(encoding="utf-8")
        marked = text.replace('"aggregated_output": "', '"aggregated_output": "\u2028\u2029\x85', 1)
        if marked == text:
            marked = text.replace('"aggregated_output":"', '"aggregated_output":"\u2028\u2029\x85', 1)
        self.assertNotEqual(marked, text, "witness not performed: no aggregated_output")
        self.assertIn("\u2028", marked)
        clean = codex_adapter.read_stream(text)
        got = codex_adapter.read_stream(marked)
        self.assertEqual((got["completed"], got["tool_ids"], got["undecoded"]),
                         (clean["completed"], clean["tool_ids"], clean["undecoded"]))
        led = json.loads((WALKS / CODEX_WALK / "driver-ledger.json").read_text())
        native = (WALKS / CODEX_WALK / "session" / led["native_snapshots"][-1]["file"]).read_text(encoding="utf-8")
        marked = native.replace('"aggregated_output":"', '"aggregated_output":"\u2028', 1)
        self.assertNotEqual(marked, native, "witness not performed: no rollout aggregated_output")
        self.assertEqual(len(codex_adapter._rollout_records(marked)), len(codex_adapter._rollout_records(native)))


# ---- the third closure check of 461dc169 (VERDICT CHANGES) and the lead's rulings on it, 24 Oct 2026 (probe6) --------
def _p6(stream_recs, sess_recs, cut=frozenset({1})):
    return cca.content_problems([cca.stream_content_units(jsonl(stream_recs))], jsonl([operator("go")] + sess_recs),
                                cut=set(cut))


def _T(mid, x, stream=True):
    return assistant(mid, [{"type": "text", "text": x}], stream=stream)


def _CALL(i, p):
    return {"type": "tool_use", "id": i, "name": "Read", "input": {"file_path": p}}


P6_STREAM = [_T("m1", "Reading."), assistant("m1", [_CALL("t1", "a.md")]), result("t1", "A"),
             _T("m2", "I will read the planted file next.")]
P6_SESS = [_T("m1", "Reading.", False), assistant("m1", [_CALL("t1", "a.md")], stream=False),
           result("t1", "A", stream=False)]
P6_S2 = [assistant("m1", [_CALL(f"t{k}", c)]) for k, c in ((1, "a"), (2, "b"), (3, "c"))] + [
    result("t1", "A"), result("t2", "B"), result("t3", "C")]
P6_Q2 = [assistant("m1", [_CALL(f"t{k}", c)], stream=False) for k, c in ((1, "a"), (2, "b"), (3, "c"))]
P6_S3 = [_T("m1", "x"), assistant("m9", [{"type": "thinking", "thinking": "plan", "signature": "s"}]),
         _T("m9", "reply part 1"), _T("m9", "reply part 2")]
P6_Q3 = [_T("m1", "x", False)]
STOP_RECORD = _T("m3", "STOP: I am waiting for the operator.", False)


class T9ThirdClosure461dc16(unittest.TestCase):
    def test_e1_probe6_rewrites_refuse(self):
        self.assertNotEqual(_p6(P6_STREAM, P6_SESS + [_T("m2", "I decline and stop here.", False)]), [],
                            "the record in flight rewritten")
        self.assertNotEqual(_p6(P6_S2, P6_Q2 + [result("t1", "A", stream=False), result("t2", "B", stream=False),
                                                result("t3", "FORGED", stream=False)]), [], "the last result rewritten")
        self.assertNotEqual(_p6(P6_S3, P6_Q3 + [assistant("m9", [{"type": "thinking", "thinking": "plan",
                                                                   "signature": "s"}], stream=False),
                                                _T("m9", "FORGED", False)]), [], "a same-id block rewritten")

    def test_e1b_the_two_genuine_shapes_read_clean(self):
        full = P6_SESS + [_T("m2", "I will read the planted file next.", False)]
        self.assertEqual(_p6(P6_STREAM, full), [])
        self.assertEqual(_p6(P6_STREAM, P6_SESS), [], "the session lags by the record in flight")
        self.assertEqual(_p6(P6_STREAM, full + [STOP_RECORD]), [], "the stream lags by one unit")
        self.assertNotEqual(_p6(P6_STREAM, full + [STOP_RECORD, STOP_RECORD]), [], "two units past the stream")
        self.assertNotEqual(_p6(P6_STREAM, P6_SESS + [_T("m2", "I decline and stop here.", False)], cut=()), [],
                            "the control: not cut")

    def test_e3_a_trailing_result_run_is_one_record_per_result(self):
        self.assertNotEqual(_p6(P6_S2, P6_Q2), [], "three trailing results all deleted")
        self.assertEqual(_p6(P6_S2, P6_Q2 + [result("t1", "A", stream=False), result("t2", "B", stream=False)]), [],
                         "only the last result in flight")

    def test_e4_a_message_groups_its_tool_use_blocks(self):
        units = cca.stream_content_units(jsonl(P6_STREAM[:2]))
        self.assertEqual(cca._last_record_length(units), 2, "m1's text and its tool_use are one message")
        self.assertEqual(_p6(P6_STREAM[:2], [], cut={1}), [], "the whole in-flight message, its tool_use included")
        self.assertEqual(_p6(P6_S3, P6_Q3), [], "the same-id message dropped whole")

    def test_e2_the_unconfirmed_extra_unit_is_never_graded(self):
        import run as run_mod
        w = Copied(CLAUDE_WALK)
        try:
            led = json.loads((w.dir / "driver-ledger.json").read_text())
            last = led["turns"][-1]["n"]
            led["turns"][-1].update(end="timed-out", exit=124)
            (w.dir / "driver-ledger.json").write_text(json.dumps(led))
            before = [str(x) for x in run_mod.transcript_lines(w.path)]
            self.assertEqual(ct.transcript_content_problems(w.path), [])
            append_line(w.path, dict(STOP_RECORD, sessionId=json.loads(w.path.read_text().split("\n")[0]).get(
                "sessionId")))
            self.assertEqual(ct.transcript_content_problems(w.path), [], "a cut's one extra unit is allowed")
            after = [str(x) for x in run_mod.transcript_lines(w.path)]
            self.assertEqual(after, before, "the graders are handed the transcript without the forged record")
            self.assertFalse(any("STOP: I am waiting" in x for x in after))
            self.assertTrue(any("STOP: I am waiting" in x for x in w.path.read_text().split("\n")))
            self.assertEqual(last, len(ct._turn_files(w.path)[1]))
        finally:
            w.close()

    def test_e2b_without_a_host_cut_nothing_is_dropped(self):
        import run as run_mod
        w = Copied(CLAUDE_WALK)
        try:
            append_line(w.path, STOP_RECORD)
            got = [str(x) for x in run_mod.transcript_lines(w.path)]
            self.assertTrue(any("STOP: I am waiting" in x for x in got))
            self.assertNotEqual(ct.transcript_content_problems(w.path), [], "and the record refuses the take")
        finally:
            w.close()


# ---- the fourth closure check of 2ab2c8f5 (one MINOR) and the lead's ruling on it, 25 Oct 2026 (probe7) ------------
class T10FourthClosure2ab2c8f(unittest.TestCase):
    STREAM = [_T("m1", "Reading."), assistant("m1", [_CALL("t1", "a.md")]), result("t1", "A"), _T("m2", "Next.")]
    BASE = [_T("m1", "Reading.", False), assistant("m1", [_CALL("t1", "a.md")], stream=False),
            result("t1", "A", stream=False)]

    def test_f1_an_extra_unit_sharing_its_line_refuses(self):
        shared = self.BASE + [assistant("m2", [{"type": "text", "text": "Next."}, {"type": "text", "text":
                                                                                   "FORGED STOP"}], stream=False)]
        self.assertNotEqual(_p6(self.STREAM, shared), [], "probe7: the extra unit on the confirmed unit's line")

    def test_f1b_an_extra_unit_alone_on_its_line_is_still_allowed_and_dropped(self):
        alone = self.BASE + [_T("m2", "Next.", False), _T("m3", "FORGED STOP", False)]
        self.assertEqual(_p6(self.STREAM, alone), [])
        text = jsonl([operator("go")] + alone)
        self.assertEqual(len(cca.unconfirmed_session_lines([jsonl(self.STREAM)], text, {1})), 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
