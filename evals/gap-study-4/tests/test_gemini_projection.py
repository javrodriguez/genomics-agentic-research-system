"""Synthetic legacy-path comparison; no recorded vendor fixtures or admission."""
import copy
import importlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ProjectionTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module("gemini_projection")
        except ImportError:
            self.fail("Gemini legacy projection is not built")

    def raw(self, records):
        return ("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n").encode()

    def call(self):
        return {"id": "call-1", "name": "read_file", "args": {"file_path": "synthetic.txt"}}

    def native(self):
        """One interaction whose first model message is a part array (the history road, as updateMessagesFromHistory
        writes it, not recordSyntheticMessage's road, which runs only without text, thoughts or tool calls), then its
        follow-up reply."""
        call = self.call()
        return [{"sessionId": "native-1", "projectHash": "project-1"},
                {"id": "user-1", "type": "user", "content": [{"text": "exact sent"}]},
                {"id": "assistant-1", "type": "gemini", "model": "synthetic-model",
                 "content": [{"text": " exact\ntext "}, {"text": "private thought", "thought": True},
                             {"functionCall": call, "thoughtSignature": "synthetic-signature"}],
                 "toolCalls": [dict(call, status="success", resultDisplay="display text",
                     result=[{"functionResponse": {"id": "call-1", "name": "read_file",
                                                   "response": {"output": "model-facing different text"}}}])]},
                self.round_trip("user-tool-1", ("call-1", "read_file")),
                {"id": "assistant-2", "type": "gemini", "model": "synthetic-model", "content": "Done."}]

    def round_trip(self, mid, *calls):
        """GeminiChat's record of one tool round trip: a "user" message of the calls' functionResponse parts."""
        return {"id": mid, "type": "user", "content": [
            {"functionResponse": {"id": cid, "name": name, "response": {"output": "x"}}} for cid, name in calls]}

    def reason(self, m, records):
        with self.assertRaises(m.ProjectionRefused) as cm:
            m.project(self.raw(records))
        return str(cm.exception)

    def test_native_projection_preserves_comparable_fields_and_absence(self):
        m = self.module()
        facts = m.project(self.raw(self.native()))
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["sent"], "exact sent")
        self.assertEqual(facts[0]["output"], [
            {"kind": "recorded-text", "message": "assistant-1", "text": "exact\ntext"},
            {"kind": "recorded-text", "message": "assistant-2", "text": "Done."},
            {"kind": "tool", "id": "call-1", "name": "read_file", "args": {"file_path": "synthetic.txt"},
             "emitted_status": "success", "output_present": True, "output": "display text"}])
        self.assertIsNone(facts[0]["permission_mode"])
        self.assertIsNone(facts[0]["version"])
        changed = self.native()
        changed[2]["toolCalls"][0]["resultDisplay"] = {"fileDiff": "native-only display"}
        tool = m.project(self.raw(changed))[0]["output"][-1]
        self.assertEqual((tool["output_present"], tool["output"]), (False, None))
        self.assertEqual(changed[2]["toolCalls"][0]["result"][0]["functionResponse"]["response"]["output"],
                         "model-facing different text")

    def test_recorded_text_is_the_recorders_normal_form_never_the_displayed_text(self):
        m = self.module()
        # What the stream showed for one model message: an HTML comment, a zero-width space, surrounding whitespace.
        displayed = "  Reading it now.\n<!-- note for the grader -->Done.​\n"
        self.assertEqual(m.recorder_normalize(displayed), "Reading it now.\nDone.")
        self.assertEqual(m.recorder_normalize("a<!-<!-- x -->- y -->b"), "ab")       # removed until none is left
        self.assertEqual(m.recorder_normalize("  text \xa0"), "text")           # JavaScript's trim set
        self.assertEqual(m.recorder_normalize("text\x1f"), "text\x1f")               # Python strip() would drop it
        records = self.native()[:2] + [{"id": "assistant-1", "type": "gemini", "model": "m",
                                        "content": m.recorder_normalize(displayed)}]
        self.assertEqual(m.project(self.raw(records))[0]["output"],
                         [{"kind": "recorded-text", "message": "assistant-1", "text": "Reading it now.\nDone."}])
        records[2]["content"] = displayed
        self.assertIn("recorder's normal form", self.reason(m, records))
        # Two model turns stay two segments: never joined with "" (the separator the stream showed is not lost).
        call = self.call()
        two = self.native()[:2] + [
            {"id": "a1", "type": "gemini", "model": "m", "content": m.recorder_normalize("I'll read it.\n"),
             "toolCalls": [dict(call, status="success", result=[{"functionResponse": {
                 "id": "call-1", "name": "read_file", "response": {"output": "x"}}}])]},
            self.round_trip("rt", ("call-1", "read_file")),
            {"id": "a2", "type": "gemini", "model": "m", "content": m.recorder_normalize("\nDone.\n")}]
        self.assertEqual([o["text"] for o in m.project(self.raw(two))[0]["output"] if o["kind"] == "recorded-text"],
                         ["I'll read it.", "Done."])

    def test_contradictions_and_unproven_shapes_refuse_each_for_its_reason(self):
        m = self.module()
        cases = []

        def case(why, edit):
            records = self.native()
            edit(records)
            cases.append((why, records))

        def tool(key, value):
            return lambda r: r[2]["toolCalls"][0].__setitem__(key, value)

        def content_call(key, value):
            return lambda r: r[2]["content"][2]["functionCall"].__setitem__(key, value)

        case("unsupported native tool status", tool("status", "cancelled"))
        case("unsupported native tool status", tool("status", "unknown"))
        case("content function call args disagrees", tool("args", {"file_path": "other"}))
        case("content function call name disagrees", content_call("name", "other"))
        case("content function call id disagrees", content_call("id", "call-other"))
        case("content function call args disagrees", content_call("args", {"file_path": "other"}))
        case("native tool response part names another call", lambda r: [tool("name", "other")(r),
             r.__setitem__(3, self.round_trip("user-tool-1", ("call-1", "other")))])
        case("unknown native tool response part", tool("result", [{"unknownPart": "unknown"}]))
        case("native tool call lacks model-facing response parts", tool("result", None))
        case("ANSI escape", lambda r: r[2]["content"][0].__setitem__("text", "\x1b[31mtext"))
        case("differ in number", lambda r: [r[2].__setitem__("toolCalls", []), r.pop(3)])
        case("native replay refused: native tools need unique", lambda r: r[2].__setitem__("toolCalls", r[2]["toolCalls"] * 2))
        case("native user content must be one text part", lambda r: r[1].__setitem__("content", [{"functionCall": {}}]))
        case("unknown or mixed native content part", lambda r: r[2].__setitem__("content", [{"inlineData": {}}]))
        case("nonfinite number", tool("args", {"number": float("nan")}))
        case("native gemini model is not a nonempty string", lambda r: r[2].__setitem__("model", 7))
        case("unknown or mixed native content part", lambda r: r[2]["content"].append({"text": "mixed", "functionCall": {}}))
        case("thoughtSignature is not a nonempty string", lambda r: r[2]["content"][2].__setitem__("thoughtSignature", ""))
        case("native gemini message precedes any user message", lambda r: r.pop(1))
        case("native error messages are unsupported", lambda r: r.append({"id": "error-1", "type": "error",
                                                                            "content": "failed"}))
        case("incomplete: its last model message ends on tool calls", lambda r: r.pop(4))
        case("no tool-response turn before the next", lambda r: r.pop(3))     # a missing round-trip record
        case("native user displayContent differs", lambda r: r[1].__setitem__("displayContent", "other text"))
        case("contradictory native models", lambda r: r[4].__setitem__("model", "different"))
        for why, records in cases:
            with self.subTest(why=why):
                self.assertIn(why, self.reason(m, records))

    def _parallel(self, both_c1=None, both_c2=None):
        def tool(cid):
            return {"id": cid, "name": "read_file", "args": {"file_path": cid}, "status": "success",
                    "result": [{"functionResponse": {"id": cid, "name": "read_file", "response": {"output": "x"}}}]}
        both = [tool("c1")["result"][0], tool("c2")["result"][0]]
        return self.native()[:2] + [
            {"id": "a1", "type": "gemini", "model": "m", "content": "t", "toolCalls": [tool("c1"), tool("c2")]},
            self.round_trip("rt", ("c1", "read_file"), ("c2", "read_file")),
            {"$patch": {"updates": [{"id": "a1", "toolCalls": [{"id": "c1", "result": both_c1 or both},
                                                               {"id": "c2", "result": both_c2 or both}]}]}},
            {"id": "a2", "type": "gemini", "model": "m", "content": "done"}]

    def test_history_patched_parallel_results_are_admitted(self):
        """Ruling 6, source retained (gemini-0.64.0-source-retained-addendum): GeminiChat.initialize calls
        updateMessagesFromHistory on every chat start, which sets a call's result to the whole user turn's parts."""
        m = self.module()
        tools = [o for o in m.project(self.raw(self._parallel()))[0]["output"] if o["kind"] == "tool"]
        self.assertEqual([t["id"] for t in tools], ["c1", "c2"])
        fr = lambda cid, name="read_file": {"functionResponse": {"id": cid, "name": name, "response": {}}}
        for why, c1 in (("names another call", [fr("c2"), fr("c9")]),
                        ("names another call", [fr("c1"), fr("c2", "glob")]),
                        ("name this call exactly once", [fr("c2")]),
                        ("name this call exactly once", [fr("c1"), fr("c1")]),
                        ("unknown native tool response part", [fr("c1"), {"text": "x"}])):
            with self.subTest(why=why, c1=c1):
                self.assertIn(why, self.reason(m, self._parallel(both_c1=c1)))

    def test_a_tool_response_turn_answers_exactly_the_message_before_it(self):
        """Source retained: every tool round trip records one "user" message holding the responses to the calls of the
        gemini message just before it; batch-5 review finding 1 binds each turn to exactly that message."""
        m = self.module()
        try:
            facts = m.project(self.raw(self.native()))
        except m.ProjectionRefused as exc:
            self.fail(f"a tool round trip was refused: {exc}")
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["sent"], "exact sent")
        self.assertEqual([o["kind"] for o in facts[0]["output"]], ["recorded-text", "recorded-text", "tool"])
        why = "answer exactly the calls of the gemini message just before it"
        for name, edit in (("an unknown call", lambda r: r.__setitem__(3, self.round_trip("x", ("call-9", "read_file")))),
                           ("a wrong name", lambda r: r.__setitem__(3, self.round_trip("x", ("call-1", "glob")))),
                           ("the call answered twice in one turn",
                            lambda r: r.__setitem__(3, self.round_trip("x", ("call-1", "read_file"),
                                                                       ("call-1", "read_file")))),
                           ("the call answered twice across turns",
                            lambda r: r.insert(4, self.round_trip("y", ("call-1", "read_file")))),
                           ("a round trip before any call", lambda r: r.insert(2, self.round_trip(
                               "z", ("call-1", "read_file"))))):
            bad = self.native()
            edit(bad)
            with self.subTest(name):
                self.assertIn("tool-response turn", self.reason(m, bad))
        older = self.native()[:4] + [
            {"id": "a2", "type": "gemini", "model": "synthetic-model", "content": "next",
             "toolCalls": [{"id": "call-2", "name": "glob", "args": {"pattern": "*"}, "status": "success",
                            "result": [{"functionResponse": {"id": "call-2", "name": "glob", "response": {}}}]}]},
            self.round_trip("rt-old", ("call-1", "read_file")),                 # answers an older round
            {"id": "a3", "type": "gemini", "model": "synthetic-model", "content": "done"}]
        self.assertIn(why, self.reason(m, older))
        mixed = self.native()
        mixed[1]["content"] = [{"functionResponse": {"id": "call-1", "name": "read_file", "response": {}}},
                               {"text": "mixed"}]
        self.assertIn("native user content must be one text part", self.reason(m, mixed))

    def test_display_content_is_admitted_only_when_equal_to_the_sent_text(self):
        """Ruling 5: the recorder writes displayContent only when it differs, so on real sessions it always refuses."""
        m = self.module()
        same = self.native()
        same[1]["displayContent"] = [{"text": "exact sent"}]
        self.assertEqual(m.project(self.raw(same))[0]["sent"], "exact sent")
        other = self.native()
        other[1]["displayContent"] = [{"text": "what the operator saw"}]
        self.assertIn("displayContent differs", self.reason(m, other))

    def test_all_interactions_are_returned_without_invented_model_fields(self):
        m = self.module()
        records = self.native()
        second = {"id": "assistant-3", "type": "gemini", "content": "second answer"}
        records += [{"id": "user-2", "type": "user", "content": "second sent"}, second]
        facts = m.project(self.raw(records))
        self.assertEqual([f["sent"] for f in facts], ["exact sent", "second sent"])
        self.assertEqual(facts[1]["output"], [{"kind": "recorded-text", "message": "assistant-3",
                                               "text": "second answer"}])
        self.assertIsNone(facts[1]["requested_model"])

    def test_partial_or_reused_tool_identity_never_becomes_success(self):
        m = self.module()
        records = self.native()
        extra = copy.deepcopy(records[2]); extra["id"] = "assistant-extra"
        self.assertIn("native tool call id reused", self.reason(m, records[:4] + [extra, self.round_trip("user-tool-2", ("call-1", "read_file"))] + records[4:]))
        # Lane vendor-b25, glitch-26's ruling 6 (Gemini review MAJOR 4, w-g13 turn 3): an interaction whose model
        # messages record no text is no longer refused here; the join decides (both sides empty agrees, one side
        # empty disagrees: test_b25_real_shapes.EmptyAnswer).
        empty = m.project(self.raw(records[:2] + [{"id": "a0", "type": "gemini", "content": ""}]))
        self.assertEqual([o for o in empty[0]["output"] if o["kind"] == "recorded-text"], [])
        self.assertIn("lacks an assistant message", self.reason(m, records[:2]))
        later = copy.deepcopy(records[2]); later["id"] = "assistant-later"
        self.assertIn("native tool call id reused", self.reason(
            m, records + [{"id": "user-later", "type": "user", "content": "later sent"}, later,
                          self.round_trip("rt-later", ("call-1", "read_file")),
                          {"id": "assistant-later-2", "type": "gemini", "content": "ok"}]))


if __name__ == "__main__":
    unittest.main()
