#!/usr/bin/env python3
"""Integration slice: the driver ledger states what the retained native snapshots prove, never more.

For an adapter that names a native session, _take_records now runs step 1's session_history_facts over the take's
retained snapshots (3c) through the PRODUCTION reader registry, which stays empty: the ledger's `native_history` is
`pending` with the registry's own reason, never an acceptance. With a reviewed reader it would read `joined` (every
later snapshot reproduces every earlier interaction), and a rewritten snapshot `refused`. Claude takes carry no such
key. Synthetic snapshots and fakes only.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_box_integration as tbi  # noqa: E402
import test_native_snapshot as tns  # noqa: E402
import vendor_provenance as vp  # noqa: E402


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


def reader(raw, ordinal):
    rows = [json.loads(x) for x in raw.decode().splitlines()]
    if ordinal > len(rows):
        raise vp.ProvenanceRefused("snapshot lacks requested interaction")
    r = rows[ordinal - 1]
    return {"session_id": "s", "requested_model": None, "version": None, "cwd": None, "permission_mode": None,
            "sent": r["line"], "output": [r["turn"]]}


class Record(unittest.TestCase):
    def retained(self, folder, texts):
        refs = []
        for n, text in enumerate(texts, 1):
            src = Path(folder) / f"src-{n}.jsonl"
            src.write_text(text)
            refs.append(tns.ns().retain(folder, n, str(src)))
        return refs

    def test_the_production_registry_leaves_it_pending(self):
        import drive
        with tempfile.TemporaryDirectory() as tmp:
            refs = self.retained(tmp, ['{"turn": 1, "line": "a"}\n'])
            got = drive.native_history_record("gemini", Path(tmp) / "session", refs)
        self.assertEqual(got["status"], "pending")
        self.assertIn("no reviewed native-session reader", got["why"])
        self.assertIsNone(got["interactions"])

    def test_a_reviewed_reader_joins_and_a_rewrite_refuses(self):
        import drive
        with tempfile.TemporaryDirectory() as tmp:
            one = '{"turn": 1, "line": "a"}\n'
            refs = self.retained(tmp, [one, one + '{"turn": 2, "line": "b"}\n'])
            got = drive.native_history_record("gemini", Path(tmp) / "session", refs, readers={"gemini": reader})
            self.assertEqual(got, {"status": "joined", "why": None, "interactions": 2,
                                   "basis": "unmasked retained originals, before the drive scan"})
            (Path(tmp) / "session" / "native-turn-2.jsonl").write_text('{"turn": 1, "line": "x"}\n')
            got = drive.native_history_record("gemini", Path(tmp) / "session", refs, readers={"gemini": reader})
            self.assertEqual(got["status"], "refused")
            self.assertEqual(drive.native_history_record("gemini", Path(tmp) / "session", [],
                                                         readers={"gemini": reader})["status"], "refused")

    def test_the_driver_ledger_carries_it_only_for_a_native_session(self):
        case = tns.DriverRetains("test_each_snapshot_is_retained_before_the_next_resume")
        rig, o, folder, ledger = case.drive()
        self.assertIn("native_history", ledger)
        # The test adapter claims claude-code, which has no native-session road: refused, never joined or pending.
        self.assertEqual(ledger["native_history"]["status"], "refused")
        self.assertIsNone(ledger["native_history"]["interactions"])
        rig, o, folder, ledger = case.drive(plain=True)
        self.assertNotIn("native_history", ledger)


if __name__ == "__main__":
    unittest.main()
