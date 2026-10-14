"""box/settings_guard.py: the run tree's Claude Code settings files (review finding 1's second guard).

Bound to real data: GARS's shipped gars/.claude/settings.json at the pinned 844a4ce0 passes the baseline, and its
hash equals the one the sidecar recorded for it in stub take 5's pre-1 snapshot on athena.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
REPO = STUDY.parents[1]
sys.path.insert(0, str(STUDY))
from box import settings_guard as sg  # noqa: E402

PINNED = "844a4ce0d89437ca043363981a86096f6383a141"
SHIPPED = subprocess.run(["git", "-C", str(REPO), "show", f"{PINNED}:gars/.claude/settings.json"],
                         capture_output=True, check=True).stdout
RUN5 = REPO / "lane-reports" / "stub-take-20261014" / "stub-take-run5.derived.json"


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sg-")
        self.tree = os.path.join(self.d, "t")
        os.makedirs(os.path.join(self.tree, "gars", ".claude"))
        Path(self.tree, "gars", ".claude", "settings.json").write_bytes(SHIPPED)
        Path(self.tree, "README.md").write_text("x\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)


class Baseline(Base):
    def test_the_shipped_file_passes_and_is_hashed(self):
        self.assertEqual(sorted(json.loads(SHIPPED)), ["hooks", "permissions"])
        self.assertEqual(sg.baseline(self.tree), {"gars/.claude/settings.json": hashlib.sha256(SHIPPED).hexdigest()})

    def test_each_forbidden_key_refuses(self):
        for key in sg.FORBIDDEN_KEYS:
            for name in ("settings.json", "settings.local.json"):
                with self.subTest(key=key, name=name):
                    p = Path(self.tree, ".claude", name)
                    p.parent.mkdir(exist_ok=True)
                    p.write_text(json.dumps({key: "x"}))
                    with self.assertRaises(sg.SettingsRefused):
                        sg.baseline(self.tree)
                    p.unlink()
        self.assertEqual(set(sg.FORBIDDEN_KEYS), {"env", "model", "fallbackModel", "switchModelsOnFlag",
                                                  "availableModels"})

    def test_links_and_shapes_refuse(self):
        outside = os.path.join(self.d, "outside.json")
        Path(outside).write_text("{}")
        cases = []
        os.makedirs(os.path.join(self.tree, "a", ".claude"))
        os.symlink(outside, os.path.join(self.tree, "a", ".claude", "settings.local.json"))
        cases.append(os.path.join(self.tree, "a", ".claude", "settings.local.json"))
        for p in cases:
            with self.assertRaises(sg.SettingsRefused):
                sg.baseline(self.tree)
            os.unlink(p)
        os.symlink(os.path.join(self.d), os.path.join(self.tree, "b-claude-target"))
        os.makedirs(os.path.join(self.tree, "b"))
        os.symlink(self.d, os.path.join(self.tree, "b", ".claude"))
        with self.assertRaises(sg.SettingsRefused):
            sg.baseline(self.tree)
        os.unlink(os.path.join(self.tree, "b", ".claude"))
        Path(self.tree, "b", ".claude").write_text("x")
        with self.assertRaises(sg.SettingsRefused):
            sg.baseline(self.tree)
        os.unlink(os.path.join(self.tree, "b", ".claude"))
        for text in ("not json", "[1]"):
            Path(self.tree, "gars", ".claude", "settings.json").write_text(text)
            with self.subTest(text=text), self.assertRaises(sg.SettingsRefused):
                sg.baseline(self.tree)


class Snapshot(unittest.TestCase):
    def setUp(self):
        doc = json.loads(RUN5.read_text())
        self.snap = json.loads(doc["evidence"]["snapshots/pre-1.json"]["text"])
        self.base = {"gars/.claude/settings.json": hashlib.sha256(SHIPPED).hexdigest()}

    def test_athena_pre1_snapshot_matches_the_shipped_file(self):
        self.assertEqual(sg.snapshot_problems(self.snap, self.base), [])

    def edited(self, path, entry):
        s = json.loads(json.dumps(self.snap))
        if entry is None:
            s["entries"].pop(path)
        else:
            s["entries"][path] = entry
        return s

    def test_every_change_refuses(self):
        cases = {
            "edited": ("gars/.claude/settings.json", {"type": "file", "sha256": "0" * 64}),
            "made a link": ("gars/.claude/settings.json", {"type": "link", "target": "/x"}),
            "removed": ("gars/.claude/settings.json", None),
            "new local file": ("gars/.claude/settings.local.json", {"type": "file", "sha256": "1" * 64}),
            "new root file": (".claude/settings.json", {"type": "file", "sha256": "1" * 64}),
            "dir made a link": ("gars/.claude", {"type": "link", "target": "/tmp"}),
            "unreadable": ("gars/.claude/settings.json", {"type": "unreadable"}),
        }
        for name, (path, entry) in cases.items():
            with self.subTest(name=name):
                self.assertTrue(sg.snapshot_problems(self.edited(path, entry), self.base))
        self.assertTrue(sg.snapshot_problems({}, self.base))
        self.assertEqual(sg.snapshot_problems(self.edited("gars/notes/claude-settings.json",
                                                          {"type": "file", "sha256": "2" * 64}), self.base), [])


if __name__ == "__main__":
    unittest.main()
