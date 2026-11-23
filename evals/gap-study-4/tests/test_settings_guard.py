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
MODEL = "claude-opus-5-5"


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
        self.assertEqual(sg.baseline(self.tree, model=MODEL), {"gars/.claude/settings.json": hashlib.sha256(SHIPPED).hexdigest()})

    def test_each_forbidden_key_refuses(self):
        for key in sg.FORBIDDEN_KEYS:
            for name in ("settings.json", "settings.local.json"):
                with self.subTest(key=key, name=name):
                    p = Path(self.tree, ".claude", name)
                    p.parent.mkdir(exist_ok=True)
                    p.write_text(json.dumps({key: "x"}))
                    with self.assertRaises(sg.SettingsRefused):
                        sg.baseline(self.tree, model=MODEL)
                    p.unlink()
        self.assertEqual(set(sg.FORBIDDEN_KEYS), {"env", "model", "fallbackModel", "switchModelsOnFlag",
                                                  "availableModels", "apiKeyHelper"})

    def test_links_and_shapes_refuse(self):
        outside = os.path.join(self.d, "outside.json")
        Path(outside).write_text("{}")
        cases = []
        os.makedirs(os.path.join(self.tree, "a", ".claude"))
        os.symlink(outside, os.path.join(self.tree, "a", ".claude", "settings.local.json"))
        cases.append(os.path.join(self.tree, "a", ".claude", "settings.local.json"))
        for p in cases:
            with self.assertRaises(sg.SettingsRefused):
                sg.baseline(self.tree, model=MODEL)
            os.unlink(p)
        os.symlink(os.path.join(self.d), os.path.join(self.tree, "b-claude-target"))
        os.makedirs(os.path.join(self.tree, "b"))
        os.symlink(self.d, os.path.join(self.tree, "b", ".claude"))
        with self.assertRaises(sg.SettingsRefused):
            sg.baseline(self.tree, model=MODEL)
        os.unlink(os.path.join(self.tree, "b", ".claude"))
        Path(self.tree, "b", ".claude").write_text("x")
        with self.assertRaises(sg.SettingsRefused):
            sg.baseline(self.tree, model=MODEL)
        os.unlink(os.path.join(self.tree, "b", ".claude"))
        for text in ("not json", "[1]"):
            Path(self.tree, "gars", ".claude", "settings.json").write_text(text)
            with self.subTest(text=text), self.assertRaises(sg.SettingsRefused):
                sg.baseline(self.tree, model=MODEL)


class Agents(Base):
    """Round-2 review R2-6: agent definitions under .claude/agents/ may name only the take's model or inherit."""

    def agent(self, text, rel=("gars", ".claude", "agents", "helper.md")):
        p = Path(self.tree, *rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def test_allowed_models(self):
        for text in ("---\nname: helper\n---\nbody\n", "---\nname: h\nmodel: inherit\n---\n",
                     f"---\nmodel: {MODEL}\n---\n", f"---\nmodel: '{MODEL}'\n---\n", "no frontmatter\n"):
            with self.subTest(text=text):
                self.agent(text)
                base = sg.baseline(self.tree, model=MODEL)
                self.assertIn("gars/.claude/agents/helper.md", base)

    def test_other_models_refuse(self):
        for text in ("---\nmodel: haiku\n---\n", "---\nmodel: claude-sonnet-5-5\n---\n",
                     "---\nname: h\nmodel: opus\n---\n"):
            with self.subTest(text=text):
                self.agent(text)
                with self.assertRaises(sg.SettingsRefused):
                    sg.baseline(self.tree, model=MODEL)
        p = self.agent("---\nmodel: haiku\n---\n", rel=(".claude", "agents", "deep", "x.md"))
        self.agent("---\nmodel: inherit\n---\n")
        with self.assertRaises(sg.SettingsRefused):
            sg.baseline(self.tree, model=MODEL)
        p.unlink()

    def test_links_and_shapes_refuse(self):
        outside = os.path.join(self.d, "outside.md")
        Path(outside).write_text("---\nmodel: inherit\n---\n")          # allowed content: only the link refuses
        os.makedirs(os.path.join(self.tree, "gars", ".claude", "agents"))
        os.symlink(outside, os.path.join(self.tree, "gars", ".claude", "agents", "a.md"))
        with self.assertRaises(sg.SettingsRefused):
            sg.baseline(self.tree, model=MODEL)
        os.unlink(os.path.join(self.tree, "gars", ".claude", "agents", "a.md"))
        os.rmdir(os.path.join(self.tree, "gars", ".claude", "agents"))
        os.symlink(self.d, os.path.join(self.tree, "gars", ".claude", "agents"))
        with self.assertRaises(sg.SettingsRefused):
            sg.baseline(self.tree, model=MODEL)
        os.unlink(os.path.join(self.tree, "gars", ".claude", "agents"))
        Path(self.tree, "gars", ".claude", "agents").write_text("x")
        with self.assertRaises(sg.SettingsRefused):
            sg.baseline(self.tree, model=MODEL)


class SkillsAndCommands(Base):
    """Closure-r2 note C-1: skills (.claude/skills/**) and slash commands (.claude/commands/**) carry a `model:`
    frontmatter field too (code.claude.com/docs/en/skills.md); the agents rule covers all three trees."""

    TREES = {"agents": ("helper.md",), "skills": ("helper", "SKILL.md"), "commands": ("helper.md",)}

    def put(self, tree, text, root=("gars", ".claude")):
        p = Path(self.tree, *root, tree, *self.TREES[tree])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def test_the_pinned_run_tree_ships_only_its_settings_file(self):
        """Measured at the pin: the only .claude path GARS ships is its settings file, so no agent, skill or command
        file is in the baseline (and the shipped tree passes, test_the_shipped_file_passes_and_is_hashed)."""
        names = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", PINNED],
                               capture_output=True, check=True, text=True).stdout.splitlines()
        self.assertGreater(len(names), 100)
        self.assertEqual([n for n in names if "/.claude/" in "/" + n], ["gars/.claude/settings.json"])
        self.assertEqual(sg.MODEL_DIRS, ("agents", "skills", "commands"))

    def test_allowed_models(self):
        for tree in self.TREES:
            for text in ("---\nname: helper\n---\nbody\n", "---\nname: h\nmodel: inherit\n---\n",
                         f"---\nmodel: {MODEL}\n---\n", f"---\nmodel: \"{MODEL}\"\n---\n", "no frontmatter\n"):
                with self.subTest(tree=tree, text=text):
                    p = self.put(tree, text)
                    base = sg.baseline(self.tree, model=MODEL)
                    self.assertIn(os.path.relpath(p, self.tree), base)
            # a skill's supporting file is hashed too, so changing it refuses at the next snapshot
            if tree == "skills":
                Path(self.tree, "gars", ".claude", "skills", "helper", "run.sh").write_text("echo x\n")
                self.assertIn("gars/.claude/skills/helper/run.sh", sg.baseline(self.tree, model=MODEL))

    def test_other_models_refuse(self):
        for tree in self.TREES:
            for text in ("---\nmodel: haiku\n---\n", "---\nmodel: claude-sonnet-5-5\n---\n",
                         "---\nname: h\nmodel: opus\n---\n"):
                with self.subTest(tree=tree, text=text):
                    p = self.put(tree, text)
                    with self.assertRaises(sg.SettingsRefused):
                        sg.baseline(self.tree, model=MODEL)
                    p.unlink()
            with self.subTest(tree=tree, where="root .claude"):
                p = self.put(tree, "---\nmodel: haiku\n---\n", root=(".claude",))
                with self.assertRaises(sg.SettingsRefused):
                    sg.baseline(self.tree, model=MODEL)
                p.unlink()

    def test_links_and_shapes_refuse(self):
        outside = os.path.join(self.d, "outside.md")
        Path(outside).write_text("---\nmodel: inherit\n---\n")          # allowed content: only the link refuses
        for tree in ("skills", "commands"):
            with self.subTest(tree=tree, case="file link"):
                folder = os.path.join(self.tree, "gars", ".claude", tree)
                os.makedirs(folder)
                os.symlink(outside, os.path.join(folder, "a.md"))
                with self.assertRaises(sg.SettingsRefused):
                    sg.baseline(self.tree, model=MODEL)
                os.unlink(os.path.join(folder, "a.md"))
            with self.subTest(tree=tree, case="sub-folder link"):
                os.symlink(self.d, os.path.join(folder, "sub"))
                with self.assertRaises(sg.SettingsRefused):
                    sg.baseline(self.tree, model=MODEL)
                os.unlink(os.path.join(folder, "sub"))
                os.rmdir(folder)
            with self.subTest(tree=tree, case="folder link"):
                os.symlink(self.d, folder)
                with self.assertRaises(sg.SettingsRefused):
                    sg.baseline(self.tree, model=MODEL)
                os.unlink(folder)
            with self.subTest(tree=tree, case="not a folder"):
                Path(folder).write_text("x")
                with self.assertRaises(sg.SettingsRefused):
                    sg.baseline(self.tree, model=MODEL)
                os.unlink(folder)
        self.assertEqual(sg.baseline(self.tree, model=MODEL),
                         {"gars/.claude/settings.json": hashlib.sha256(SHIPPED).hexdigest()})


class Bounds(Base):
    """Round-2 review R2-2: the 2 MiB cap and an unreadable folder are bound."""

    def test_the_size_cap(self):
        doc = json.dumps({"hooks": {}, "pad": "x" * (2 * 1024 * 1024)})
        Path(self.tree, "gars", ".claude", "settings.json").write_text(doc)
        with self.assertRaises(sg.SettingsRefused):
            sg.baseline(self.tree, model=MODEL)

    def test_an_unreadable_folder_refuses(self):
        locked = os.path.join(self.tree, "locked")
        os.mkdir(locked)
        os.chmod(locked, 0)
        try:
            with self.assertRaises(sg.SettingsRefused):
                sg.baseline(self.tree, model=MODEL)
        finally:
            os.chmod(locked, 0o700)


class Snapshot(unittest.TestCase):
    def setUp(self):
        doc = json.loads(RUN5.read_text())
        self.snap = json.loads(doc["evidence"]["snapshots/pre-1.json"]["text"])
        self.base = {"gars/.claude/settings.json": hashlib.sha256(SHIPPED).hexdigest()}

    def test_athena_pre1_snapshot_matches_the_shipped_file(self):
        self.assertEqual(sg.snapshot_problems(self.snap, self.base), [])

    def test_every_snapshot_after_a_turn_is_checked_too(self):
        """R2-1: the post-k snapshots, the final one included, are compared as the pre-k ones are."""
        doc = json.loads(RUN5.read_text())
        posts = sorted(k for k in doc["evidence"] if k.startswith("snapshots/post-"))
        self.assertEqual(posts, ["snapshots/post-1.json", "snapshots/post-2.json", "snapshots/post-3.json"])
        for k in posts:
            snap = json.loads(doc["evidence"][k]["text"])
            self.assertEqual(sg.snapshot_problems(snap, self.base), [], k)
            snap["entries"]["gars/.claude/settings.local.json"] = {"type": "file", "sha256": "1" * 64}
            self.assertTrue(sg.snapshot_problems(snap, self.base), k)

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
            "new agent": ("gars/.claude/agents/x.md", {"type": "file", "sha256": "3" * 64}),
            "agents made a link": ("gars/.claude/agents", {"type": "link", "target": "/tmp"}),
            # closure-r2 note C-1: skills and slash commands, the same rule
            "new skill": ("gars/.claude/skills/x/SKILL.md", {"type": "file", "sha256": "3" * 64}),
            "new root skill": (".claude/skills/x/SKILL.md", {"type": "file", "sha256": "3" * 64}),
            "new command": ("gars/.claude/commands/x.md", {"type": "file", "sha256": "3" * 64}),
            "skills made a link": ("gars/.claude/skills", {"type": "link", "target": "/tmp"}),
            "commands made a file": ("gars/.claude/commands", {"type": "file", "sha256": "4" * 64}),
            "skill sub-folder made a link": ("gars/.claude/skills/x", {"type": "link", "target": "/tmp"}),
            "unreadable": ("gars/.claude/settings.json", {"type": "unreadable"}),
        }
        for name, (path, entry) in cases.items():
            with self.subTest(name=name):
                self.assertTrue(sg.snapshot_problems(self.edited(path, entry), self.base))
        self.assertTrue(sg.snapshot_problems({}, self.base))
        # a shipped skill that is changed or removed refuses; its unchanged sub-folder entry does not
        base = dict(self.base, **{"gars/.claude/skills/x/SKILL.md": "5" * 64})
        snap = self.edited("gars/.claude/skills/x/SKILL.md", {"type": "file", "sha256": "5" * 64})
        snap["entries"]["gars/.claude/skills"] = {"type": "dir"}
        snap["entries"]["gars/.claude/skills/x"] = {"type": "dir"}
        self.assertEqual(sg.snapshot_problems(snap, base), [])
        snap["entries"]["gars/.claude/skills/x/SKILL.md"] = {"type": "file", "sha256": "6" * 64}
        self.assertTrue(sg.snapshot_problems(snap, base))
        snap["entries"].pop("gars/.claude/skills/x/SKILL.md")
        self.assertTrue(sg.snapshot_problems(snap, base))
        self.assertEqual(sg.snapshot_problems(self.edited("gars/notes/claude-settings.json",
                                                          {"type": "file", "sha256": "2" * 64}), self.base), [])


if __name__ == "__main__":
    unittest.main()
