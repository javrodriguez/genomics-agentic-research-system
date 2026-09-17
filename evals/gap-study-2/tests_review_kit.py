#!/usr/bin/env python3
"""CP8: the blind reviewer is launched the way a take is, cannot push, and its blindness check sees this round.

    python3 evals/gap-study-2/test_harness.py TheReviewKitMatchesTheDriver TheReviewerCannotPush

No model, no network, no live folder read. stdlib only.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
KIT = HERE / "review_kit"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"gap_study_2_kit_{name}", KIT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TheReviewKitMatchesTheDriver(unittest.TestCase):

    def test_launch_flags_and_environment_are_the_drivers(self):
        launch = load("launch")
        drive = launch.load_drive()
        argv = launch.argv_for("00000000-0000-0000-0000-000000000000", drive)
        for flag in drive.ISOLATION_FLAGS:
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--model") + 1], launch.MODEL)
        self.assertIn("--permission-mode", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "auto")
        # the twelve names planted in this process's environment first: in a cleared shell (the clean-clone battery)
        # nothing carries them, and a launcher that inherited os.environ would inherit nothing and read as stripped
        # (ROUND 2, CP8, rehearsal 5)
        planted = {name: "planted-by-the-test" for name in drive.STRIPPED_ENV}
        with mock.patch.dict(os.environ, planted):
            env = launch.env_for(drive)
        for k, v in drive.ISOLATION_ENV.items():
            self.assertEqual(env.get(k), v)
        for k, v in launch.REVIEWER_ENV.items():
            self.assertEqual(env.get(k), v)
        for name in drive.STRIPPED_ENV:
            self.assertNotIn(name, env, f"the reviewer inherits {name}, which a take does not")

    def test_the_reviewer_is_never_a_sub_agent(self):
        source = (KIT / "launch.py").read_text()
        self.assertIn('"claude", "-p"', source)
        self.assertNotIn("Agent(", source)

    def test_blindness_markers_name_this_round_and_the_operator(self):
        blind = load("blindness")
        words = {w for _, w in blind.MARKERS}
        for w in ("gars-eval-v3", "gap-study-2", "round 2", "Waiting on Javier", "glitch-mem", "SOUL.md", "north star"):
            self.assertIn(w, words)
        self.assertEqual(blind.REPO.resolve(), HERE.parent.parent.resolve(), "the repository path is not taken from the file's own location")

    def test_the_email_regex(self):
        blind = load("blindness")
        for s in ("someone@example.com", "first.last+tag@sub.example.org", "x@y.io"):
            self.assertTrue(blind.EMAIL.fullmatch(s), s)
        for s in ("not an email", "a@b", "@example.com", "user@.com"):
            self.assertFalse(blind.EMAIL.fullmatch(s), s)
        self.assertEqual(blind.mask("mail me at someone@example.com", "/nowhere"), "mail me at <account email>")

    def test_the_brief_template_carries_its_placeholders_and_the_forbidden_commands(self):
        text = (KIT / "BRIEF.md").read_text()
        for ph in ("{N}", "{PREVIOUS}"):
            self.assertIn(ph, text)
        for forbidden in ("drive.py", "freeze.py --write", "takes.py --add", "freeze_rehearsal.py"):
            self.assertIn(forbidden, text)
        self.assertIn("threat_model", text)
        self.assertIn("limitations_lines", text)

    def test_commit_review_refuses_a_report_with_a_path_or_a_person_or_no_ruling(self):
        cr = load("commit_review")
        sha = "a" * 64
        good = f"prereg.json sha256: {sha}\n\n**Ruling: DO FREEZE.**\n"
        self.assertEqual(cr.report_problems(good, sha), [])
        self.assertTrue(cr.report_problems(good.replace(sha, "b" * 64), sha))
        self.assertTrue(cr.report_problems(good + "/Users/someone/x\n", sha))
        self.assertTrue(cr.report_problems(good + "written by Javier\n", sha))
        self.assertTrue(cr.report_problems(f"prereg.json sha256: {sha}\n\nno ruling here\n", sha))


class TheReviewerCannotPush(unittest.TestCase):

    def test_a_folder_whose_clone_has_a_remote_is_refused(self):
        launch = load("launch")
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "review"
            (folder / "study").mkdir(parents=True)
            (folder / "BRIEF.md").write_text("x")
            import scratch_git
            scratch_git.init(folder / "study")
            self.assertEqual(launch.folder_problems(folder), [])
            subprocess.run(["git", "-C", str(folder / "study"), "remote", "add", "origin", "https://example.invalid/x.git"],
                           check=True, capture_output=True)
            problems = launch.folder_problems(folder)
            self.assertTrue(any("has a remote" in p for p in problems), problems)

    def test_a_folder_under_the_repository_is_refused(self):
        launch = load("launch")
        folder = HERE / "review_kit" / "would-be-inside"
        problems = launch.folder_problems(folder)
        self.assertTrue(any("under this repository" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
