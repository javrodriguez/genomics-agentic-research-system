#!/usr/bin/env python3
"""CP8: the freeze cannot be written until it has been rehearsed on these draft bytes, and it writes only its own keys.

    python3 evals/gap-study-2/test_harness.py TheFreezeNeedsARehearsal

Binds freeze.py's rehearsal gate (rehearsal_problems), its version refusal (claude_version), and the commit-body diff
(changed_keys, keys_outside_the_freeze): a freeze that changed a task's script on the way out would be refused. The
rehearsal script itself is exercised by running it, not here: its record is committed as verification/freeze-rehearsal-<n>.txt
and its first line is checked against the draft.

No model, no network, no live folder read. stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import freeze  # noqa: E402

DRAFT = HERE / "prereg-draft.json"


class TheFreezeNeedsARehearsal(unittest.TestCase):

    def test_no_rehearsal_record_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            got = freeze.rehearsal_problems("a" * 64, Path(td))
        self.assertEqual(len(got), 1)
        self.assertIn("has not been rehearsed", got[0])

    def test_a_record_for_other_bytes_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "freeze-rehearsal-1.txt").write_text("b" * 64 + "\nsteps\nall green\n")
            got = freeze.rehearsal_problems("a" * 64, Path(td))
        self.assertEqual(len(got), 1, "a rehearsal of other draft bytes was admitted")
        self.assertIn("the draft changed since the last rehearsal", got[0])

    def test_a_record_that_did_not_end_green_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "freeze-rehearsal-1.txt").write_text("a" * 64 + "\nsteps\nNOT all green: test_harness.py\n")
            got = freeze.rehearsal_problems("a" * 64, Path(td))
        self.assertEqual(len(got), 1)
        self.assertIn("did not end", got[0])

    def test_a_green_record_for_these_bytes_admits(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "freeze-rehearsal-2.txt").write_text("a" * 64 + "\nsteps\nall green\n")
            self.assertEqual(freeze.rehearsal_problems("a" * 64, Path(td)), [])

    def test_freeze_write_refuses_without_a_rehearsal_in_a_copy(self):
        """freeze.py --write, run in a copy of this study whose verification/ holds no rehearsal, must refuse by name.
        The copy carries a synthetic review commit so the refusal reached is the rehearsal's, not the review's."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            (root / "evals" / "gap-study-2").mkdir(parents=True)
            for name in ("freeze.py", "prereg.py", "study.py", "prereg-draft.json"):
                (root / "evals" / "gap-study-2" / name).write_bytes((HERE / name).read_bytes())
            ver = root / "evals" / "gap-study-2" / "verification"
            ver.mkdir()
            sha = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
            (ver / "prefreeze-1.md").write_text(f"prereg.json sha256: {sha}\n\n**Ruling: DO FREEZE.**\n")
            import scratch_git
            scratch_git.init(root)
            g = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
            subprocess.run(g + ["add", "-A"], check=True, capture_output=True)
            subprocess.run(g + ["commit", "-qm", "review"], check=True, capture_output=True)
            head = subprocess.run(g + ["rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            env = {k: v for k, v in os.environ.items() if not k.startswith("GAP_STUDY_2_POISON")}
            r = subprocess.run([sys.executable, str(root / "evals" / "gap-study-2" / "freeze.py"), "--review-commit",
                                head, "--write"], capture_output=True, text=True, cwd=str(root), env=env)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse((root / "evals" / "gap-study-2" / "prereg.json").exists(), "the freeze wrote without a rehearsal")
            out = r.stdout + r.stderr
            self.assertIn("has not been rehearsed", out,
                          "the freeze reached past the rehearsal gate: " + " | ".join(out.strip().splitlines()[-2:])[:300])

    def test_the_rehearsal_flag_is_refused_where_a_remote_exists(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            (root / "evals" / "gap-study-2").mkdir(parents=True)
            for name in ("freeze.py", "prereg.py", "study.py", "prereg-draft.json"):
                (root / "evals" / "gap-study-2" / name).write_bytes((HERE / name).read_bytes())
            import scratch_git
            scratch_git.init(root)
            subprocess.run(["git", "-C", str(root), "remote", "add", "origin", "https://example.invalid/x.git"],
                           check=True, capture_output=True)
            r = subprocess.run([sys.executable, str(root / "evals" / "gap-study-2" / "freeze.py"), "--review-commit",
                                "HEAD", "--rehearsal", "--write"], capture_output=True, text=True, cwd=str(root))
            self.assertEqual(r.returncode, 2)
            self.assertIn("has one", r.stdout + r.stderr)

    def test_the_commit_body_diff_names_only_freeze_written_keys(self):
        draft = json.loads(DRAFT.read_text())
        frozen = json.loads(DRAFT.read_text())
        frozen["status"] = "FROZEN"
        frozen["pinned_files"] = [{"path": "x"}]
        frozen["tasks"][0]["grader"] = {**frozen["tasks"][0]["grader"], "sha256": "y"}
        self.assertEqual(freeze.keys_outside_the_freeze(draft, frozen), [])
        self.assertIn("status", freeze.commit_body_diff(draft, frozen))
        frozen["tasks"][0]["positive"]["operator_script"][0]["line"] = "edited on the way out"
        self.assertEqual(freeze.keys_outside_the_freeze(draft, frozen), ["tasks[].positive.operator_script"],
                         "a freeze that edits a script line must be named as outside its keys")
        self.assertEqual(freeze.commit_body_diff(draft, draft), "none")

    def test_the_rehearsal_record_if_present_names_the_current_draft(self):
        """A committed rehearsal record is bound to the draft it rehearsed; a stale one is a finding, not a pass."""
        records = sorted((HERE / "verification").glob("freeze-rehearsal-*.txt"))
        if not records:
            self.skipTest("no rehearsal record yet; freeze.py refuses --write until one exists")
        sha = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
        latest = records[-1].read_text().splitlines()
        self.assertEqual(latest[0], sha, f"{records[-1].name} rehearsed other draft bytes; rehearse again")
        self.assertEqual(latest[-1].strip(), freeze.REHEARSAL_LAST_LINE, f"{records[-1].name} did not end all green")
        self.assertTrue(any("not done" in line for line in latest), "the record must say what it did not run")


if __name__ == "__main__":
    unittest.main()
