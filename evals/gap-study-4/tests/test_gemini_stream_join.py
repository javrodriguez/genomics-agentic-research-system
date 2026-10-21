#!/usr/bin/env python3
"""Live harness slice 5: the stream-side Gemini join (unregistered; synthetic streams and sessions only).

One `gemini -p … -o stream-json` call is one interaction. The legacy non-interactive loop (gemini-legacy-content-source:
`while (true) { turnCount++; … for await (const event of responseStream) { content -> message delta; tool_call_request
-> tool_use; … } … }`) runs one model response per iteration and sends tool results back before the next, so a
response's text is every assistant delta after the previous tool_result. The native recorder stores that response's
text in recorder_normalize's normal form, so the stream side applies the same normalization per response before
comparing. An interaction counts as complete only with the stream's terminal result (r2 finding 1); tool facts
compare by id, name, order and status; errors and unknowns are kept; any disagreement refuses.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

MODEL = "gemini-3.8-flash"
TS = "2026-10-14T00:00:00.000Z"
SID = "1a2b3c4d-0000-4000-8000-00000000abcd"


def module():
    import gemini_stream_join
    return gemini_stream_join


def ev(t, **kw):
    return dict({"type": t, "timestamp": TS}, **kw)


def stream(*records, cut=False):
    text = "".join(json.dumps(r) + "\n" for r in records)
    return text + ('{"type": "mess' if cut else "")


def say(text):
    return ev("message", role="assistant", content=text, delta=True)


STATS = {"total_tokens": 3, "input_tokens": 2, "output_tokens": 1, "cached": 0, "input": 2, "duration_ms": 5,
         "tool_calls": 1, "models": {MODEL: {"total_tokens": 3, "input_tokens": 2, "output_tokens": 1, "cached": 0,
                                             "input": 2}}}


def good_stream(**over):
    recs = [ev("init", session_id=SID, model=MODEL),
            ev("message", role="user", content="exact sent"),
            say("  I'll read it."), say("<!-- hidden -->\n"),
            ev("tool_use", tool_name="read_file", tool_id="call-1", parameters={"file_path": "synthetic.txt"}),
            ev("tool_result", tool_id="call-1", status="success", output="display text"),
            say("\nDone.​"), say("\n"),
            ev("result", status="success", stats=STATS)]
    return recs


def native_fact():
    return {"session_id": SID, "requested_model": MODEL, "version": None, "cwd": None, "permission_mode": None,
            "sent": "exact sent",
            "output": [{"kind": "recorded-text", "message": "a1", "text": "I'll read it."},
                       {"kind": "recorded-text", "message": "a2", "text": "Done."},
                       {"kind": "tool", "id": "call-1", "name": "read_file", "args": {"file_path": "synthetic.txt"},
                        "emitted_status": "success", "output_present": True, "output": "display text"}]}


class Join(unittest.TestCase):
    def refused(self, recs, fact=None, why=""):
        m = module()
        with self.assertRaises(m.JoinRefused) as cm:
            m.join(fact or native_fact(), stream(*recs) if isinstance(recs, list) else recs)
        self.assertIn(why, str(cm.exception))
        return str(cm.exception)

    def test_a_matching_interaction_joins_and_is_complete(self):
        got = module().join(native_fact(), stream(*good_stream()))
        self.assertEqual(got, {"complete": True, "terminal_status": "success", "terminal_error": None,
                               "errors": [], "segments": ["I'll read it.", "Done."],
                               "tools": [("call-1", "read_file", "success")], "sent": "exact sent",
                               "init_model": MODEL})

    def test_without_the_terminal_result_completeness_is_never_claimed(self):
        recs = good_stream()[:-1]
        self.refused(recs, why="no terminal result")
        self.refused(stream(*good_stream()[:-1], cut=True), why="")

    def test_the_call_reader_itself_refuses_an_unfinished_call(self):
        m = module()
        for why, recs in (("no terminal result", good_stream()[:-1]),
                          ("no tool_result", good_stream()[:5] + good_stream()[6:])):
            with self.subTest(why=why), self.assertRaises(m.JoinRefused) as cm:
                m.read_call(stream(*recs))
            self.assertIn(why, str(cm.exception))

    def test_tool_order_is_compared(self):
        recs = good_stream()
        second = [ev("tool_use", tool_name="glob", tool_id="call-2", parameters={"pattern": "*"}),
                  ev("tool_result", tool_id="call-2", status="success")]
        fact = native_fact()
        fact["output"].append({"kind": "tool", "id": "call-2", "name": "glob", "args": {"pattern": "*"},
                               "emitted_status": "success", "output_present": False, "output": None})
        ordered = recs[:4] + second + recs[4:]           # call-2 before call-1 in the stream
        self.refused(ordered, fact, "tool facts disagree")
        self.assertTrue(module().join(fact, stream(*(recs[:6] + second + recs[6:])))["complete"])

    def test_a_failed_result_and_error_events_are_kept_not_hidden(self):
        recs = good_stream()
        recs[-1] = ev("result", status="error", error={"type": "synthetic", "message": "failed"}, stats=STATS)
        recs.insert(-1, ev("error", severity="warning", message="Loop detected, stopping execution"))
        got = module().join(native_fact(), stream(*recs))
        self.assertEqual((got["complete"], got["terminal_status"]), (False, "error"))
        self.assertEqual(got["terminal_error"], {"type": "synthetic", "message": "failed"})
        self.assertEqual(got["errors"], [{"severity": "warning", "message": "Loop detected, stopping execution"}])

    def test_every_disagreement_refuses_for_its_reason(self):
        cases = []

        def case(why, edit_stream=None, edit_fact=None):
            recs, fact = good_stream(), native_fact()
            if edit_stream:
                edit_stream(recs)
            if edit_fact:
                edit_fact(fact)
            cases.append((why, recs, fact))

        case("recorded text disagrees", lambda r: r.__setitem__(6, say("\nDone, differently.")))
        case("recorded text disagrees", lambda r: r.insert(5, r.pop(6)))     # "Done." moved into the first response
        case("recorded text disagrees", edit_fact=lambda f: f["output"].pop(1))
        case("tool facts disagree", lambda r: r[4].__setitem__("tool_name", "glob") or
             r[4].__setitem__("parameters", {"pattern": "*"}))
        case("tool facts disagree", lambda r: [r[4].__setitem__("tool_id", "call-9"),
                                                r[5].__setitem__("tool_id", "call-9")])
        case("tool facts disagree", lambda r: r[5].__setitem__("status", "error"))
        case("tool facts disagree", edit_fact=lambda f: f["output"].append(
            dict(f["output"][2], id="call-2")))
        case("no tool_result", lambda r: r.pop(5))
        case("tool_result names no tool_use", lambda r: r.insert(6, ev("tool_result", tool_id="call-7",
                                                                       status="success")))
        case("tool arguments disagree", lambda r: r[4].__setitem__("parameters", {"file_path": "other.txt"}))
        # round 18 B12: read_file's keys are the pinned 0.64.0 schema's (start_line, end_line), not offset and limit
        case("tool arguments disagree", lambda r: r[4].__setitem__("parameters", {"file_path": "synthetic.txt",
                                                                                   "start_line": 1}))
        case("tool arguments disagree", edit_fact=lambda f: f["output"][2].__setitem__("args", {"file_path": True}))
        case("tool arguments disagree", lambda r: r[4]["parameters"].__setitem__("end_line", 1),
             lambda f: f["output"][2]["args"].__setitem__("end_line", True))      # equal in Python, not in JSON
        case("tool_use id reused", lambda r: r.insert(5, copy.deepcopy(r[4])))
        case("sent text disagrees", lambda r: r[1].__setitem__("content", "other sent"))
        case("model disagrees", edit_fact=lambda f: f.__setitem__("requested_model", "other-model"))
        case("non-delta assistant message", lambda r: r.__setitem__(2, ev("message", role="assistant",
                                                                          content="  I'll read it.")))
        case("after the terminal result", lambda r: r.append(ev("result", status="success", stats=STATS)))
        case("after the terminal result", lambda r: r.append(say("late")))
        case("native fact", edit_fact=lambda f: f["output"].append({"kind": "unknown"}))
        for why, recs, fact in cases:
            with self.subTest(why=why):
                self.refused(recs, fact, why)

    def test_an_absent_user_message_stays_unknown(self):
        recs = [r for r in good_stream() if r.get("role") != "user"]
        got = module().join(native_fact(), stream(*recs))
        self.assertIsNone(got["sent"])
        self.assertTrue(got["complete"])

    def test_an_absent_or_other_init_refuses_on_session_identity(self):
        # Lane vendor-b25, glitch-26's ruling 5 (Gemini review MAJOR 3): the stream's init session_id is the only
        # stream-side witness of session identity, so a stream without init (it used to stay unknown here) or with
        # another id refuses, as the Codex join refuses another exec thread.
        no_init = [r for r in good_stream() if r["type"] != "init"]
        other = [dict(r, session_id="another-session") if r["type"] == "init" else r for r in good_stream()]
        for why, recs in (("no init", no_init), ("another id", other)):
            with self.subTest(why=why):
                self.refused(recs, native_fact(), "session identity disagrees")

    def test_the_join_is_unregistered(self):
        import vendor_provenance
        self.assertEqual(dict(vendor_provenance.NATIVE_SESSION_READERS), {})


if __name__ == "__main__":
    unittest.main()
