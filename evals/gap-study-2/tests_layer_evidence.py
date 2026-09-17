#!/usr/bin/env python3
"""CP8, review 1 blocker 1: each task's layer evidence is derived from the committed controls record, which names the tree it ran on.

    python3 evals/gap-study-2/test_harness.py TheLayerEvidenceIsTheControlsRecord

No model, no network, no live folder read: the record under controls/ and the pre-registration in force. stdlib only.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import prereg  # noqa: E402

sys.path.insert(0, str(HERE / "controls"))
import bind_evidence  # noqa: E402


class TheLayerEvidenceIsTheControlsRecord(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pre = prereg.load()
        cls.record = json.loads(bind_evidence.RECORD.read_text())

    def test_the_draft_blocks_are_what_the_record_gives(self):
        self.assertEqual(bind_evidence.problems(self.pre, self.record), [],
                         "the draft's evidence is not derived from the controls record")
        self.assertEqual(len(bind_evidence.bound_tasks(self.pre)), 5)

    def test_the_record_ran_on_the_pinned_tree_and_names_its_commit(self):
        self.assertEqual(self.record["gars_tree_sha"], self.pre["system_under_test"]["gars_tree_sha"])
        self.assertRegex(self.record["commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(self.record["run_at"], r"^\d{4}-\d{2}-\d{2}$")
        for t in bind_evidence.bound_tasks(self.pre):
            self.assertEqual(t["layer"]["evidence"]["record"], bind_evidence.provenance(self.record), t["id"])

    def test_an_attempt_edited_in_the_draft_is_refused(self):
        draft = copy.deepcopy(self.pre)
        task = next(t for t in bind_evidence.bound_tasks(draft) if t["id"] == "precondition-refusal")
        task["layer"]["evidence"]["per_behaviour"][0]["attempts"][0]["argv"] += " --force"
        got = bind_evidence.problems(draft, self.record)
        self.assertTrue(any("precondition-refusal" in p and "not what the controls record gives" in p for p in got), got)

    def test_a_record_from_another_tree_is_refused(self):
        record = copy.deepcopy(self.record)
        record["gars_tree_sha"] = "0" * 40
        got = bind_evidence.problems(self.pre, record)
        self.assertTrue(any("not the pinned tree" in p for p in got), got)

    def test_the_command_line_check(self):
        cli = [sys.executable, str(HERE / "controls" / "bind_evidence.py"), "--check"]
        ok = subprocess.run(cli, capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout)
        with tempfile.TemporaryDirectory() as td:
            draft = copy.deepcopy(self.pre)
            for k in ("_source", "_frozen"):
                draft.pop(k, None)
            next(t for t in bind_evidence.bound_tasks(draft) if t["id"] == "scope-read")["layer"]["evidence"]["per_behaviour"] = []
            p = Path(td) / "draft.json"
            p.write_text(json.dumps(draft))
            bad = subprocess.run(cli + ["--draft", str(p)], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1, bad.stdout)
            self.assertIn("scope-read", bad.stdout)


if __name__ == "__main__":
    unittest.main()
