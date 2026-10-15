"""The walk-token scripts, run against a temporary HOME with a planted fake value (never a real token).
Run: python3 -m unittest discover -s lane-reports/walk-login -p test_walk_login_scripts.py"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAKE = "FAKEVALUE-walktoken-0123456789abcdef-PLANTED-not-a-token"
sys.path.insert(0, str(HERE.parents[1] / "evals" / "gap-study-4"))


def run(script, home, *args):
    env = {"HOME": home, "PATH": "/usr/bin:/bin"}
    return subprocess.run([sys.executable, "-I", str(HERE / script), *args], capture_output=True, text=True, env=env,
                          timeout=60)


class WalkToken(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="wt-")
        self.path = os.path.join(self.home, "gap4-secrets", "claude1", "claude-walk-token")

    def paste(self, text):
        with open(self.path, "a") as fh:            # what the editor leaves: the name already there, the value, a newline
            fh.write(text)

    def test_prepare_then_paste_then_verify(self):
        p = run("prepare_walk_login.py", self.home, "claude1")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        rec = json.loads(p.stdout)
        modes = [e["mode"] for e in rec["entries"]]
        self.assertEqual(modes, ["0o700", "0o700", "0o600"])
        self.assertEqual(Path(self.path).read_bytes(), b"CLAUDE_CODE_OAUTH_TOKEN=")
        v = run("verify_walk_login.py", self.home, "claude1")
        self.assertEqual(v.returncode, 1)                 # nothing pasted yet
        self.assertIn("length: empty", v.stdout)
        self.paste(FAKE + "\n")
        v = run("verify_walk_login.py", self.home, "claude1")
        self.assertEqual(v.returncode, 0, v.stdout)
        self.assertIn("RESULT: OK", v.stdout)
        self.assertIn("length: 20 or more", v.stdout)
        for line in ("value contains '=': no", "value pasted twice: no", "value starts with the variable name: no"):
            self.assertIn(line, v.stdout)
        self.assertNotIn(FAKE, v.stdout + v.stderr)
        self.assertNotIn(FAKE[:8], v.stdout + v.stderr)
        # the box's own reader agrees with the verify script on the prepared, pasted file
        from box import run_take as rt
        self.assertEqual(rt.read_login(self.path, "CLAUDE_CODE_OAUTH_TOKEN"), FAKE)
        rt.check_login_place(self.path, "/srv/w/t1/tree")
        # a second prepare never overwrites a pasted token
        p = run("prepare_walk_login.py", self.home, "claude1")
        self.assertEqual(p.returncode, 1)
        self.assertEqual(Path(self.path).read_text(), "CLAUDE_CODE_OAUTH_TOKEN=" + FAKE + "\n")
        self.assertNotIn(FAKE, p.stdout + p.stderr)

    def test_verify_refuses_each_wrong_shape(self):
        run("prepare_walk_login.py", self.home, "claude1")
        self.paste(FAKE + "\n")
        for name, change, undo in (
                ("mode", lambda: os.chmod(self.path, 0o644), lambda: os.chmod(self.path, 0o600)),
                ("folder", lambda: os.chmod(os.path.dirname(self.path), 0o755),
                 lambda: os.chmod(os.path.dirname(self.path), 0o700)),
                ("two lines", lambda: self.paste("X=1\n"), None),
        ):
            change()
            v = run("verify_walk_login.py", self.home, "claude1")
            with self.subTest(name):
                self.assertEqual(v.returncode, 1, v.stdout)
                self.assertNotIn(FAKE, v.stdout + v.stderr)
            if undo:
                undo()
        # review-walk-token W-2: a doubled paste, a whole-line paste and a value holding '=' each fail, by name
        for text, line in (("CLAUDE_CODE_OAUTH_TOKEN=" + FAKE + FAKE + "\n", "value pasted twice: YES"),
                           ("CLAUDE_CODE_OAUTH_TOKEN=CLAUDE_CODE_OAUTH_TOKEN=" + FAKE + "\n", "value contains '=': YES"),
                           ("CLAUDE_CODE_OAUTH_TOKEN=CLAUDE_CODE_OAUTH_TOKEN" + FAKE + "\n",
                            "value starts with the variable name: YES"),
                           ("CLAUDE_CODE_OAUTH_TOKEN=" + FAKE + "=x\n", "value contains '=': YES")):
            Path(self.path).write_text(text)
            v = run("verify_walk_login.py", self.home, "claude1")
            with self.subTest(line):
                self.assertEqual(v.returncode, 1, v.stdout)
                self.assertIn(line, v.stdout)
                self.assertNotIn(FAKE, v.stdout + v.stderr)
        for text in ("CLAUDE_CODE_OAUTH_TOKEN=short\n", "CLAUDE_CODE_OAUTH_TOKEN=has space " + FAKE + "\n",
                     FAKE + "\n", ""):
            Path(self.path).write_text(text)
            v = run("verify_walk_login.py", self.home, "claude1")
            with self.subTest(text=len(text)):
                self.assertEqual(v.returncode, 1, v.stdout)
                self.assertNotIn(FAKE, v.stdout + v.stderr)
        os.unlink(self.path)
        os.symlink(os.path.join(self.home, "elsewhere"), self.path)
        self.assertEqual(run("verify_walk_login.py", self.home, "claude1").returncode, 1)

    def test_prepare_refuses(self):
        os.makedirs(os.path.join(self.home, "gap4-secrets"))
        os.symlink(self.home, os.path.join(self.home, "gap4-secrets", "claude1"))
        self.assertEqual(run("prepare_walk_login.py", self.home, "claude1").returncode, 1)
        self.assertEqual(run("prepare_walk_login.py", self.home, "../x").returncode, 1)
        repo_home = tempfile.mkdtemp(prefix="wt-")
        os.mkdir(os.path.join(repo_home, ".git"))
        self.assertEqual(run("prepare_walk_login.py", repo_home, "claude1").returncode, 1)


class GeminiKey(unittest.TestCase):
    """The Gemini key road (glitch-06, 14 Oct 2026), the walk-token road's mirror: account r4-g, file gemini-walk-login,
    one line GEMINI_API_KEY=<key>. The verify script also refuses quotes and names a stray non-ASCII character by its
    Unicode name only (a Mac's Option key types them: U+2248 from Option-X). Planted values are fakes."""
    FAKE_G = "AIzaFAKE-gemini-0123456789abcdef-PLANTED"

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="gk-")
        self.path = os.path.join(self.home, "gap4-secrets", "r4-g", "gemini-walk-login")

    def verify(self):
        return run("verify_walk_login.py", self.home, "r4-g")

    def test_prepare_then_paste_then_verify(self):
        p = run("prepare_walk_login.py", self.home, "r4-g")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([e["mode"] for e in json.loads(p.stdout)["entries"]], ["0o700", "0o700", "0o600"])
        self.assertEqual(Path(self.path).read_bytes(), b"GEMINI_API_KEY=")
        v = self.verify()
        self.assertEqual(v.returncode, 1)
        self.assertIn("length: empty", v.stdout)
        with open(self.path, "a") as fh:
            fh.write(self.FAKE_G + "\n")
        v = self.verify()
        self.assertEqual(v.returncode, 0, v.stdout)
        self.assertIn("RESULT: OK", v.stdout)
        self.assertIn("stray non-ASCII character: none", v.stdout)
        self.assertNotIn(self.FAKE_G, v.stdout + v.stderr)
        self.assertNotIn(self.FAKE_G[:8], v.stdout + v.stderr)
        from box import run_take as rt
        self.assertEqual(rt.read_login(self.path, "GEMINI_API_KEY"), self.FAKE_G)
        rt.check_login_place(self.path, "/srv/w/t1/tree")
        self.assertEqual(rt.WALK_LOGIN_FILES["r4-g"], "/home/javier/gap4-secrets/r4-g/gemini-walk-login")

    def test_verify_refuses_each_wrong_shape(self):
        run("prepare_walk_login.py", self.home, "r4-g")
        for text, line in (("GEMINI_API_KEY=" + self.FAKE_G + "\u2248\n", "stray non-ASCII character: ALMOST EQUAL TO"),
                           ("GEMINI_API_KEY=" + self.FAKE_G + "'\n", "quote in the value: YES"),
                           ("GEMINI_API_KEY='" + self.FAKE_G + "'\n", "quote in the value: YES"),
                           ("GEMINI_API_KEY=" + self.FAKE_G + " x\n", "format ok"),
                           ("GEMINI_API_KEY=" + self.FAKE_G + self.FAKE_G + "\n", "value pasted twice: YES"),
                           ("GEMINI_API_KEY=GEMINI_API_KEY" + self.FAKE_G + "\n",
                            "value starts with the variable name: YES"),
                           ("CLAUDE_CODE_OAUTH_TOKEN=" + self.FAKE_G + "\n", "format ok")):
            Path(self.path).write_text(text, encoding="utf-8")
            v = self.verify()
            with self.subTest(line):
                self.assertEqual(v.returncode, 1, v.stdout)
                self.assertIn(line, v.stdout)
                self.assertNotIn(self.FAKE_G, v.stdout + v.stderr)
        self.assertEqual(run("verify_walk_login.py", self.home, "r4-x").returncode, 1)   # no such account
        self.assertEqual(run("prepare_walk_login.py", self.home, "r4-x").returncode, 1)


if __name__ == "__main__":
    unittest.main()
