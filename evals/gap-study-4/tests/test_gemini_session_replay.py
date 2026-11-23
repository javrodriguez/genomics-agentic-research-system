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
        # Lane vendor-b26 (glitch-26's ruling 8): an update carries the writer's arrays only, the turn's parts as
        # content and the user turn's parts as a result (chunk-NR7L3FXV.js:287168, :287182, :287227); a string refuses.
        out = [{"functionResponse": {"id": "t1", "name": "read_file", "response": {"output": "native output"}}}]
        records += [{"id": "a1", "type": "gemini", "content": "replacement", "toolCalls": records[2]["toolCalls"]},
                    {"$patch": {"updates": [{"id": "a1", "content": [{"text": "final\u2029answer"}],
                        "toolCalls": [{"id": "t1", "result": out}]}]}},
                    {"$set": {"sessionId": "native-1", "lastUpdated": "later"}}]
        result = m.replay(self.raw(records))
        self.assertEqual([r["id"] for r in result["messages"]], ["u1", "a1", "notice1"])
        self.assertNotIn("tokens", result["messages"][1])
        self.assertEqual(result["messages"][1]["content"], [{"text": "final\u2029answer"}])
        self.assertEqual(result["messages"][1]["toolCalls"][0].get("result"), out)
        self.assertEqual(result["metadata"]["lastUpdated"], "later")
        self.assertEqual(earlier["messages"][1]["content"], "draft")
        self.assertNotIn("result", earlier["messages"][1]["toolCalls"][0])

    def test_destructive_unknown_and_identity_changes_refuse(self):
        m = self.module()
        # Lane vendor-b25 (glitch-26's ruling 3): orderIds is admitted only as the pinned resume patch, exactly
        # {orderIds, updates} with orderIds a permutation of the known ids (chunk-NR7L3FXV.js:287262-287265 writes it;
        # :286415-286453 applies it). This one still refuses on both counts: no updates, and notice1 left out.
        # The admitted shape and each off-shape variant: tests/test_b25_real_shapes.py GeminiResumePatch.
        bad = [{"$rewindTo": "u1"}, {"$patch": {"removeIds": ["u1"]}},
               {"$patch": {"orderIds": ["a1", "u1"]}}, {"$set": {"messages": []}},
               {"$set": {"memoryScratchpad": "unknown context"}}, {"$set": {"sessionId": "other"}},
               {"$patch": {"id": "missing", "content": "x"}},
               {"$patch": {"id": "a1", "toolCalls": [{"id": "missing", "result": "x"}]}},
               {"$patch": {"updates": [{"id": "a1", "unknown": "x"}]}},
               # lane vendor-b26 (glitch-26's ruling 8): a well-formed direct patch on a present message; the pinned
               # writer's one $patch (chunk-NR7L3FXV.js:287254-287265) never carries a top-level id
               {"$patch": {"id": "a1", "content": [{"text": "x"}]}},
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
