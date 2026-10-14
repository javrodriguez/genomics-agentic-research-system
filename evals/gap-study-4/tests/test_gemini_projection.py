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
                {"id": "assistant-2", "type": "gemini", "model": "synthetic-model", "content": "Done."}]

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
        case("native tool response part names another call", tool("name", "other"))
        case("unknown native tool response part", tool("result", [{"unknownPart": "unknown"}]))
        case("native tool call lacks model-facing response parts", tool("result", None))
        case("ANSI escape", lambda r: r[2]["content"][0].__setitem__("text", "\x1b[31mtext"))
        case("differ in number", lambda r: r[2].__setitem__("toolCalls", []))
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
        case("incomplete: its last model message ends on tool calls", lambda r: r.pop(3))
        case("native user displayContent is unsupported", lambda r: r[1].__setitem__("displayContent", "exact sent"))
        case("contradictory native models", lambda r: r[3].__setitem__("model", "different"))
        for why, records in cases:
            with self.subTest(why=why):
                self.assertIn(why, self.reason(m, records))

    def test_history_patched_parallel_results_stay_refused(self):
        """Known false-refusal risk: the updateMessagesFromHistory caller is not retained (source report)."""
        m = self.module()
        def tool(cid):
            return {"id": cid, "name": "read_file", "args": {"file_path": cid}, "status": "success",
                    "result": [{"functionResponse": {"id": cid, "name": "read_file", "response": {"output": "x"}}}]}
        both = [tool("c1")["result"][0], tool("c2")["result"][0]]
        records = self.native()[:2] + [
            {"id": "a1", "type": "gemini", "model": "m", "content": "t", "toolCalls": [tool("c1"), tool("c2")]},
            {"$patch": {"updates": [{"id": "a1", "toolCalls": [{"id": "c1", "result": both},
                                                               {"id": "c2", "result": both}]}]}},
            {"id": "a2", "type": "gemini", "model": "m", "content": "done"}]
        self.assertIn("names another call", self.reason(m, records))

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
        self.assertIn("native tool call id reused", self.reason(m, records[:3] + [extra] + records[3:]))
        self.assertIn("no recorded answer text", self.reason(
            m, records[:2] + [{"id": "a0", "type": "gemini", "content": ""}]))
        self.assertIn("lacks an assistant message", self.reason(m, records[:2]))
        later = copy.deepcopy(records[2]); later["id"] = "assistant-later"
        self.assertIn("native tool call id reused", self.reason(
            m, records + [{"id": "user-later", "type": "user", "content": "later sent"}, later,
                          {"id": "assistant-later-2", "type": "gemini", "content": "ok"}]))


if __name__ == "__main__":
    unittest.main()
