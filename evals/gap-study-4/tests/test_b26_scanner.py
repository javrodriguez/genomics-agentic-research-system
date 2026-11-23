#!/usr/bin/env python3
"""Lane vendor-b26 fold (Gap Study round 4): glitch-f1's ruling 1 on REVIEW-vendor-b26-04c4e77 MAJOR 1, the reviewer's
scanner witness folded in (its scratch file, tests/review_b26_scanner_witness.py in the review clone).

glitch-26's ruling 4 on the B26 design: after a tool-output masking re-record the loader's state holds only masked
copies, so check_take._gemini_snapshot_records (check_take.py:4104 and :4110) must read every original from the replay's
timeline at its frozen state, every resume or re-recorded copy, and every dead re-record update's results. The stage-1
witness (test_b26_rewrites.Scanner) held without the timeline on w-g47; each assertion here pins one of the three
sources, by the record's own `where`, so each one-line breakage (the loader's live state read instead of the originals;
the dead-update results skipped; the copies skipped) turns this red.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
FIX = Path(__file__).resolve().parent / "fixtures" / "b26-rewrites"


class ScannerReadsEveryCopy(unittest.TestCase):
    """w-g47's second snapshot: one re-record retired 201 originals (104 toolCalls) and wrote 104 dead results."""

    @classmethod
    def setUpClass(cls):
        import check_take
        import gemini_session_replay as rm
        cls.raw = (FIX / "w-g47-native-turn-2.jsonl").read_bytes()
        cls.rep = rm.replay(cls.raw)
        cls.where = [w for w, _, _ in check_take._gemini_snapshot_records(cls.raw, "s")]
        cls.wheres = set(cls.where)

    def test_every_frozen_original_tool_is_read(self):
        live = {m["id"] for m in self.rep["messages"]}
        frozen = [m for m in self.rep["timeline"] if m["id"] not in live and m.get("toolCalls")]
        self.assertTrue(frozen, "the fixture retires originals that carry toolCalls")
        for m in frozen:
            for i in range(len(m["toolCalls"])):
                self.assertIn(f"s message {m['id']!r} tool {i + 1}", self.wheres, m["id"])

    def test_every_dead_result_is_read(self):
        dead = self.rep["dead_results"]
        self.assertTrue(dead, "the fixture's re-record carries dead toolCalls updates")
        for k, d in enumerate(dead, 1):
            for i in range(len(d["result"])):
                self.assertIn(f"s re-record update {k} call {d['id']!r} response {i + 1}", self.wheres)

    def test_every_copy_tool_response_turn_is_read(self):
        turns = [m for m in self.rep["copies"] if m["type"] == "user" and m["content"]
                 and all(set(p) == {"functionResponse"} for p in m["content"])]
        self.assertTrue(turns, "the fixture holds re-recorded and resume copies of tool-response turns")
        for m in turns:
            for i in range(len(m["content"])):
                self.assertIn(f"s message {m['id']!r} response {i + 1}", self.wheres, m["id"])


if __name__ == "__main__":
    unittest.main()
