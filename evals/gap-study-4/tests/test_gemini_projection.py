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

    def native(self):
        call = {"id": "call-1", "name": "read_file", "args": {"file_path": "synthetic.txt"}}
        return [{"sessionId": "native-1", "projectHash": "project-1"},
                {"id": "user-1", "type": "user", "content": [{"text": "exact sent"}]},
                {"id": "assistant-1", "type": "gemini", "model": "synthetic-model",
                 "content": [{"text": " exact\ntext "}, {"text": "private thought", "thought": True},
                             {"functionCall": call}],
                 "toolCalls": [dict(call, status="success", resultDisplay="display text",
                     result=[{"functionResponse": {"id": "call-1", "name": "read_file",
                                                   "response": {"output": "model-facing different text"}}}])]}]

    def test_native_projection_preserves_comparable_fields_and_absence(self):
        m = self.module()
        facts = m.project(self.raw(self.native()))
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["sent"], "exact sent")
        self.assertEqual(facts[0]["output"], [
            {"kind": "visible-text", "text": " exact\ntext "},
            {"kind": "tool", "id": "call-1", "name": "read_file", "args": {"file_path": "synthetic.txt"},
             "emitted_status": "success", "output_present": True, "output": "display text"}])
        self.assertIsNone(facts[0]["permission_mode"])
        self.assertIsNone(facts[0]["version"])
        changed = self.native()
        changed[2]["toolCalls"][0]["resultDisplay"] = {"fileDiff": "native-only display"}
        tool = m.project(self.raw(changed))[0]["output"][1]
        self.assertEqual((tool["output_present"], tool["output"]), (False, None))
        self.assertEqual(changed[2]["toolCalls"][0]["result"][0]["functionResponse"]["response"]["output"],
                         "model-facing different text")

    def test_contradictions_and_unproven_shapes_refuse(self):
        m = self.module()
        mutants = []
        for key, value in (("status", "cancelled"), ("status", "unknown"), ("args", {"file_path": "other"}),
                           ("name", "other"), ("result", [{"unknownPart": "unknown"}])):
            records = self.native()
            records[2]["toolCalls"][0][key] = value
            mutants.append(records)
        records = self.native(); records[2]["content"][0]["text"] = "\x1b[31mtext"; mutants.append(records)
        records = self.native(); records[2]["toolCalls"] = []; mutants.append(records)
        records = self.native(); records[2]["toolCalls"] *= 2; mutants.append(records)
        records = self.native(); records[1]["content"] = [{"functionCall": {}}]; mutants.append(records)
        records = self.native(); records[2]["content"] = [{"inlineData": {}}]; mutants.append(records)
        records = self.native(); records[2]["toolCalls"][0]["args"] = {"number": float("nan")}; mutants.append(records)
        records = self.native(); records[2]["model"] = 7; mutants.append(records)
        records = self.native(); records[2]["toolCalls"][0]["result"] = None; mutants.append(records)
        records = self.native(); records[2]["content"] += [{"text": "mixed", "functionCall": {}}]; mutants.append(records)
        records = self.native(); records.pop(1); mutants.append(records)
        records = self.native(); records.append({"id": "error-1", "type": "error", "content": "failed"}); mutants.append(records)
        for records in mutants:
            with self.subTest(records=records), self.assertRaises(m.ProjectionRefused):
                m.project(self.raw(records))

    def test_all_interactions_are_returned_without_invented_model_fields(self):
        m = self.module()
        records = self.native()
        second = copy.deepcopy(records[2]); second["id"] = "assistant-2"
        second["content"] = "second answer"; second.pop("model"); second.pop("toolCalls")
        records += [{"id": "user-2", "type": "user", "content": "second sent"}, second]
        facts = m.project(self.raw(records))
        self.assertEqual([f["sent"] for f in facts], ["exact sent", "second sent"])
        self.assertEqual(facts[1]["output"], [{"kind": "visible-text", "text": "second answer"}])
        self.assertIsNone(facts[1]["requested_model"])

    def test_partial_or_reused_tool_identity_never_becomes_success(self):
        m = self.module()
        records = self.native()
        extra = copy.deepcopy(records[2]); extra["id"] = "assistant-extra"
        with self.assertRaises(m.ProjectionRefused):
            m.project(self.raw(records + [extra]))
        second = copy.deepcopy(records[2]); second["id"] = "assistant-2"; second["model"] = "different"
        second["content"] = "more text"; second.pop("toolCalls")
        with self.assertRaises(m.ProjectionRefused):
            m.project(self.raw(records + [second]))
        with self.assertRaises(m.ProjectionRefused):
            m.project(self.raw(records[:2]))
        later = copy.deepcopy(records[2]); later["id"] = "assistant-later"
        with self.assertRaises(m.ProjectionRefused):
            m.project(self.raw(records + [{"id": "user-later", "type": "user", "content": "later sent"}, later]))


if __name__ == "__main__":
    unittest.main()
