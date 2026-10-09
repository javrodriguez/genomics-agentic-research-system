#!/usr/bin/env python3
"""Pipeline contracts on synthetic data and disposable repositories; no model or container.

Mutants are armed in setUpModule, never during module discovery. --mutant NAME
runs this entire file with that production clause removed in memory.
"""
from __future__ import annotations

import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import copy_manifest as cm
import freeze
import study

MUTANT = None
_patches = []


def mutations():
    return {
        "freeze-claims": (freeze, "output_fragment", lambda: {"lane": "freeze", "files": []}),
        "freeze-once": (freeze, "outputs_exist", lambda root: False),
        "freeze-snapshot": (freeze, "snapshot", lambda manifest, folder: {"files": []}),
    }


def setUpModule():
    if MUTANT:
        target, name, replacement = mutations()[MUTANT]
        patch = mock.patch.object(target, name, replacement)
        patch.start()
        _patches.append(patch)


def tearDownModule():
    while _patches:
        _patches.pop().stop()


def git(root, *args):
    got = subprocess.run(["git", "-C", str(root), "-c", "maintenance.auto=false",
                          "-c", "user.name=synthetic", "-c", "user.email=synthetic@example.invalid",
                          *args], capture_output=True, text=True)
    if got.returncode:
        raise AssertionError(got.stderr)
    return got.stdout.strip()


def commit(root, paths, message):
    git(root, "add", "--", *paths)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as msg:
        msg.write(message + "\n\nCo-Authored-By: Codex (gpt-6-astra) <noreply@openai.com>\n")
        msg.flush()
        git(root, "commit", "-q", "-F", msg.name)
    return git(root, "rev-parse", "HEAD")


@contextmanager
def manifest_repository():
    """Scratch index and files, with the checker's real historical source/blob readers.

    Only the five required copied builders are copied. Other files are synthetic.
    The source revisions stay the real pinned revisions: no byte guard is mocked.
    """
    builders = {p: (HERE / p).read_bytes() for p in cm.UNEDITABLE}
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp).resolve()
        git(repo, "init", "-q")
        root = repo / study.STUDY_REL
        folder = root / "COPIED.d"
        folder.mkdir(parents=True)
        entries = []
        for path, data in builders.items():
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            entries.append({"path": path, "status": "identical", "source": cm.SOURCE_DIR + "/" + path})
        for path, data in {"instrument.txt": "synthetic instrument\n",
                           "prereg-draft.json": '{"synthetic": true}\n'}.items():
            (root / path).write_text(data)
            entries.append({"path": path, "status": "new", "reason": "synthetic input"})
        entries.append({"path": "COPIED.d/synthetic.json", "status": "new", "reason": "synthetic claims"})
        (folder / "synthetic.json").write_text(json.dumps({"lane": "synthetic", "files": entries}))
        commit(repo, [study.STUDY_REL], "Record synthetic inputs")

        def tracked():
            return {p[len(study.STUDY_REL) + 1:] for p in
                    git(repo, "ls-files", "--", study.STUDY_REL).splitlines()}

        with mock.patch.object(cm, "HERE", root), mock.patch.object(cm, "tracked_here", tracked):
            yield repo, root, folder


class FreezeOutputs(unittest.TestCase):
    def writer(self):
        self.assertTrue(callable(getattr(freeze, "write_outputs", None)),
                        "freeze must write and claim its outputs together")
        return freeze.write_outputs

    def test_build_and_frozen_manifest_and_snapshot(self):
        writer = self.writer()
        with manifest_repository() as (repo, root, folder):
            self.assertEqual(cm.problems(folder, pinned=False), [])
            before = cm.derive(folder)
            writer({"synthetic": True, "status": "frozen"}, root=root, manifest=cm)
            commit(repo, [study.STUDY_REL], "Freeze synthetic inputs")
            self.assertEqual(cm.problems(folder, pinned=False), [])
            self.assertEqual(json.loads((root / "COPIED.json").read_text()), before)
            fragment = json.loads((folder / "freeze.json").read_text())
            self.assertEqual(fragment["lane"], "freeze")
            self.assertEqual({e["path"] for e in fragment["files"]},
                             {"COPIED.json", "prereg.json", "COPIED.d/freeze.json"})
            self.assertTrue(all(e["status"] == "new" and e["reason"] ==
                                "written once by freeze.py at the freeze" for e in fragment["files"]))
            paths = git(repo, "show", "--format=", "--name-only", "HEAD").splitlines()
            self.assertEqual(set(paths), {study.rel(p) for p in
                                         ("COPIED.json", "prereg.json", "COPIED.d/freeze.json")})

    def test_second_freeze_refused_before_any_write(self):
        writer = self.writer()
        with manifest_repository() as (_repo, root, _folder):
            writer({"synthetic": True}, root=root, manifest=cm)
            original = (root / "prereg.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "already exists"):
                writer({"synthetic": False}, root=root, manifest=cm)
            self.assertEqual((root / "prereg.json").read_bytes(), original)

    def test_missing_claim_mutant_is_refused(self):
        writer = self.writer()
        with manifest_repository() as (_repo, root, folder):
            with mock.patch.object(freeze, "output_fragment", lambda: {"lane": "freeze", "files": []}):
                writer({"synthetic": True}, root=root, manifest=cm)
            bad = cm.problems(folder, pinned=False)
            for path in ("COPIED.json", "prereg.json", "COPIED.d/freeze.json"):
                self.assertTrue(any(b.startswith(path + " is under") and "no fragment" in b for b in bad), bad)


if __name__ == "__main__":
    if "--mutant" in sys.argv:
        at = sys.argv.index("--mutant")
        MUTANT = sys.argv[at + 1]
        del sys.argv[at:at + 2]
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"test_pipeline: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped", flush=True)
    sys.exit(0 if result.wasSuccessful() else 1)
