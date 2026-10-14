#!/usr/bin/env python3
"""ops/write_image_lock.py: the one supported lock writer, on a temporary repository only (never the real locks).

Every value is obviously fake. Each refusal is tested alone, and one positive write fills a schema-1 take-a lock
into a schema-2 lock that image_lock validates and preflight.load_take_lock projects.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from box import image_lock as il  # noqa: E402
from box import preflight as pf  # noqa: E402

SPEC = importlib.util.spec_from_file_location("write_image_lock_test", HERE.parents[1] / "ops/write_image_lock.py")
w = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w)

BASE = "registry.example/fake-base@sha256:" + "a" * 64
INDEX, MANIFEST, CONFIG = "sha256:" + "f" * 64, "sha256:" + "c" * 64, "sha256:" + "d" * 64
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false",
       "-c", "maintenance.auto=false", "-c", "gc.auto=0"]


def committed_take_a() -> dict:
    return il.load(os.path.join(il.BOX_DIR, "image.lock"))


def inputs(lock: dict) -> dict:
    return {"base": BASE, "harness": dict(lock["harness"], version="9.8.7"), "python": "3.12.99",
            "users": copy.deepcopy(lock["users"])}


class Repo:
    """A throwaway git repository holding box/image.lock (take-a, schema 1) and one build record."""

    def __init__(self, tc):
        d = Path(tempfile.mkdtemp())
        tc.addCleanup(lambda: __import__("shutil").rmtree(d))
        self.root, self.box = d, d / "box"
        self.box.mkdir()
        (self.box / "Dockerfile").write_text("FROM scratch\n")
        self.lock_path = self.box / "image.lock"
        self.lock = committed_take_a()
        self.lock_path.write_text(json.dumps(self.lock, indent=1) + "\n")
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.record_path = d / "build-record.json"
        self.row = {"image": "take-a", "exit": 0, "image_id": INDEX, "manifest_digest": MANIFEST,
                    "config_digest": CONFIG, "label_problems": [], "lock_inputs": inputs(self.lock)}
        self.record = {"schema": 2, "source_commit": self.base, "images": [self.row]}
        self.commit_record()
        p = mock.patch.object(il, "BOX_DIR", str(self.box))
        p.start()
        tc.addCleanup(p.stop)

    def git(self, *args) -> str:
        return subprocess.run(GIT + ["-C", str(self.root), *args], check=True, capture_output=True,
                              text=True, env={"PATH": "/usr/bin:/bin", "HOME": str(self.root)}).stdout

    def commit_record(self):
        self.record_path.write_text(json.dumps(self.record, indent=1) + "\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "record")

    def plan(self):
        return w.plan(il, self.root, self.record_path, self.lock_path, "take-a")


class Positive(unittest.TestCase):
    def test_a_temp_repo_write_fills_a_valid_schema_2_lock(self):
        r = Repo(self)
        new, read = r.plan()
        self.assertEqual(read, r.lock_path.read_bytes())
        w.write(r.lock_path, new, read)
        got = il.load(str(r.lock_path))
        self.assertEqual((got["schema"], got["image_id"], got["manifest_digest"], got["config_digest"],
                          got["source_commit"], got["pending"]), (2, INDEX, MANIFEST, CONFIG, r.base, {}))
        self.assertEqual(il.problems(got), [])
        projected = pf.load_take_lock(str(r.lock_path), harness="claude-code")
        self.assertEqual(projected["manifest_digest"], MANIFEST)
        self.assertFalse(Path(str(r.lock_path) + ".writing").exists())

    def test_without_write_nothing_changes(self):
        r = Repo(self)
        before = r.lock_path.read_bytes()
        r.plan()
        self.assertEqual(r.lock_path.read_bytes(), before)


class Refusals(unittest.TestCase):
    def refuse(self, r, pattern):
        with self.assertRaisesRegex((w.Refused, il.LockError), pattern):
            r.plan()

    def test_an_uncommitted_record(self):
        r = Repo(self)
        r.record_path.write_text(r.record_path.read_text() + " ")
        self.refuse(r, "differs from its committed bytes")
        untracked = r.root / "other.json"
        untracked.write_text(r.record_path.read_text())
        with self.assertRaisesRegex(w.Refused, "not a file committed"):
            w.plan(il, r.root, untracked, r.lock_path, "take-a")

    def test_a_commit_not_an_ancestor(self):
        r = Repo(self)
        r.git("checkout", "-q", "-b", "side", r.base)
        r.git("commit", "-q", "--allow-empty", "-m", "side")
        side = r.git("rev-parse", "HEAD").strip()
        r.git("checkout", "-q", "-")
        r.record["source_commit"] = side
        r.commit_record()
        self.refuse(r, "not an ancestor")
        r.record["source_commit"] = "main"
        r.commit_record()
        self.refuse(r, "40 hex")

    def test_each_row_condition(self):
        for key, value, pattern in (("exit", 1, "did not exit 0"), ("exit", True, "did not exit 0"),
                                    ("label_problems", ["x"], "labels"), ("manifest_digest", "c" * 64, "manifest"),
                                    ("config_digest", None, "config"), ("image_id", "sha256:x", "image_id"),
                                    ("lock_inputs", None, "lock_inputs")):
            with self.subTest(key=key, value=value):
                r = Repo(self)
                r.row[key] = value
                r.commit_record()
                with self.assertRaisesRegex(w.Refused, pattern):   # the writer's own check, before any validation
                    r.plan()

    def test_zero_or_two_rows(self):
        r = Repo(self)
        r.record["images"] = [r.row, dict(r.row)]
        r.commit_record()
        self.refuse(r, "2 rows")
        r.record["images"] = []
        r.commit_record()
        self.refuse(r, "0 rows")

    def test_an_unresolved_or_changed_input(self):
        for edit, pattern in ((lambda i: i.pop("python"), "does not resolve python"),
                              (lambda i: i.update(python=il.PENDING), "PENDING not resolved|pinned shape"),
                              (lambda i: i["harness"].update(package="@openai/codex"), "harness package"),
                              (lambda i: i["users"]["agent"].update(uid=10009), "users differs"),
                              (lambda i: i.update(squid="6.99-1"), "does not carry")):
            with self.subTest(pattern=pattern):
                r = Repo(self)
                edit(r.row["lock_inputs"])
                r.commit_record()
                self.refuse(r, pattern)

    def test_a_filled_or_other_lock(self):
        r = Repo(self)
        new, read = r.plan()
        w.write(r.lock_path, new, read)
        r.git("add", "-A"); r.git("commit", "-q", "-m", "filled")
        self.refuse(r, "not the unfilled schema-1 lock")
        r2 = Repo(self)
        with self.assertRaisesRegex(w.Refused, "0 rows"):
            w.plan(il, r2.root, r2.record_path, r2.lock_path, "take-o")

    def test_a_record_of_another_schema(self):
        r = Repo(self)
        r.record["schema"] = 1
        r.commit_record()
        self.refuse(r, "not schema 2")

    def test_a_lock_changed_after_reading_is_not_overwritten(self):
        r = Repo(self)
        new, read = r.plan()
        r.lock_path.write_text(r.lock_path.read_text() + "\n")
        with self.assertRaisesRegex(w.Refused, "changed since it was read"):
            w.write(r.lock_path, new, read)


if __name__ == "__main__":
    unittest.main()
