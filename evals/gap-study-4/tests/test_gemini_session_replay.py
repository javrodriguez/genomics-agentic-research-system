"""Source-derived replay witnesses, not recorded Gemini session fixtures."""
import importlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ReplayTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module("gemini_session_replay")
        except ImportError:
            self.fail("independent Gemini session replay is not built")

    def raw(self, records):
        return ("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n").encode()

    def records(self):
        return [{"sessionId": "native-1", "projectHash": "project-1", "startTime": "start", "lastUpdated": "now"},
                {"id": "u1", "type": "user", "content": "sent\u2028still sent"},
                {"id": "a1", "type": "gemini", "content": "draft", "tokens": {"input": 1}, "toolCalls": [
                    {"id": "t1", "name": "read_file", "args": {"path": "synthetic"}}]},
                {"id": "notice1", "type": "info", "content": "native notice"}]

    def test_upserts_and_patches_keep_native_order(self):
        m = self.module()
        records = self.records()
        earlier = m.replay(self.raw(records))
        records += [{"id": "a1", "type": "gemini", "content": "replacement", "toolCalls": records[2]["toolCalls"]},
                    {"$patch": {"updates": [{"id": "a1", "content": "final\u2029answer",
                        "toolCalls": [{"id": "t1", "result": "native output"}]}]}},
                    {"$set": {"sessionId": "native-1", "lastUpdated": "later"}}]
        result = m.replay(self.raw(records))
        self.assertEqual([r["id"] for r in result["messages"]], ["u1", "a1", "notice1"])
        self.assertNotIn("tokens", result["messages"][1])
        self.assertEqual(result["messages"][1]["content"], "final\u2029answer")
        self.assertEqual(result["messages"][1]["toolCalls"][0].get("result"), "native output")
        self.assertEqual(result["metadata"]["lastUpdated"], "later")
        self.assertEqual(earlier["messages"][1]["content"], "draft")
        self.assertNotIn("result", earlier["messages"][1]["toolCalls"][0])

    def test_destructive_unknown_and_identity_changes_refuse(self):
        m = self.module()
        bad = [{"$rewindTo": "u1"}, {"$patch": {"removeIds": ["u1"]}},
               {"$patch": {"orderIds": ["a1", "u1"]}}, {"$set": {"messages": []}},
               {"$set": {"memoryScratchpad": "unknown context"}}, {"$set": {"sessionId": "other"}},
               {"$patch": {"id": "missing", "content": "x"}},
               {"$patch": {"id": "a1", "toolCalls": [{"id": "missing", "result": "x"}]}},
               {"$patch": {"updates": [{"id": "a1", "unknown": "x"}]}},
               {"id": "u1", "type": "gemini", "content": "changed role"},
               {"sessionId": "native-1", "projectHash": "other"}, {"unknown": "record"},
               {"id": "x", "type": [], "content": "x"}]
        for record in bad:
            with self.subTest(record=record), self.assertRaises(m.ReplayRefused):
                m.replay(self.raw(self.records() + [record]))

    def test_missing_truncated_duplicate_and_blank_records_refuse(self):
        m = self.module()
        raw = self.raw(self.records())
        for broken in (b"", b'{"id":"first","type":"user","content":"x"}\n',
                       raw + b'{"$set":', raw + b'\n',
                       raw + b'{"$set":{"lastUpdated":"x","lastUpdated":"y"}}\n'):
            with self.subTest(broken=broken), self.assertRaises(m.ReplayRefused):
                m.replay(broken)


if __name__ == "__main__":
    unittest.main()
