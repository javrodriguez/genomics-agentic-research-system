#!/usr/bin/env python3
"""The run tree the driver exports carries study-naming text only in the files the draft permits.

    python3 evals/gap-study-2/test_harness.py TheRunTreeCarriesOnlyPermittedSweepHits

FOUND 13 SEPTEMBER 2026 (CP3), by the environment smoke. smoke_run_tree.py sweeps the exported checkout with
TREE_SWEEP and reports the hits without judging them. Round 1's four run-tree smokes reported 4 hits, in README.md
and docs/RESULTS.md. The first round-2 smokes reported 64: the v1.0.1 build had since added assessment, review and
specification documents under docs/ that name this study, its pre-registration and evals/ by path. An agent in a
round-2 take could have opened any of them. The draft now excludes them, and this class makes the residual a
whitelist rather than a report: run_location.permitted_sweep_files names each file that may still match, with
why, and any other file that matches is refused. A new file naming the study fails the suite the day it lands.

The checkout is built the driver's way, drive.clean_run_tree at the driver's --at default with the draft's
exclusions, and removed afterwards. The class skips, printing why, only when git archive cannot run.

No model, no network. stdlib only.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

import prereg
import test_harness as th

HERE = th.HERE
PLANTED = Path("docs") / "notes-planted.md"


def smoke_module():
    spec = importlib.util.spec_from_file_location("gap_smoke_run_tree_sweep", HERE / "smoke_run_tree.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sweep_hits(tree: Path, pattern) -> list[tuple[str, int]]:
    """(file, line) for every line TREE_SWEEP matches, read the way smoke_run_tree reads the checkout."""
    hits = []
    for f in sorted(tree.rglob("*")):
        if ".git" in f.relative_to(tree).parts or not f.is_file():
            continue
        try:
            text = f.read_text(errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        for i, ln in enumerate(text.splitlines(), start=1):
            if pattern.search(ln):
                hits.append((f.relative_to(tree).as_posix(), i))
    return hits


def permitted_files(pre: dict) -> list[str]:
    entries = (pre.get("run_location") or {}).get("permitted_sweep_files")
    if not isinstance(entries, list) or not entries or not all(
            isinstance(e, dict) and set(e) == {"path", "why"} and isinstance(e["path"], str)
            and isinstance(e["why"], str) and e["why"].strip() for e in entries):
        raise AssertionError("run_location.permitted_sweep_files is not a non-empty list of {path, why}")
    return [e["path"] for e in entries]


def sweep_problems(hits: list[tuple[str, int]], permitted: list[str]) -> list[str]:
    problems = []
    for name in sorted({f for f, _ in hits} - set(permitted)):
        lines = [i for f, i in hits if f == name]
        problems.append(f"{name} names the study on line(s) {lines} and is not in run_location.permitted_sweep_files")
    return problems


class TheRunTreeCarriesOnlyPermittedSweepHits(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.drive = th.gap_drive()
        cls.pattern = smoke_module().TREE_SWEEP
        cls.pre = prereg.load()
        cls.tree = None
        cls.skip_reason = None
        if shutil.which("git") is None:
            cls.skip_reason = "git is not on this machine, so the run tree cannot be exported with git archive"
            return
        try:
            cls.tree = cls.drive.clean_run_tree(cls.drive.DEFAULT_AT, str(uuid.uuid4()),
                                                cls.drive.excluded_from_run_tree(cls.pre))
        except subprocess.CalledProcessError as exc:
            cls.skip_reason = (f"git archive could not export the run tree here ({exc.returncode}: "
                               f"{(exc.stderr or b'')[:200]!r})")

    @classmethod
    def tearDownClass(cls):
        if cls.tree is not None:
            shutil.rmtree(cls.tree, ignore_errors=True)
        cls.tmp.cleanup()

    def setUp(self):
        if self.skip_reason:
            print(self.skip_reason)
            self.skipTest(self.skip_reason)

    def test_every_sweep_hit_is_in_a_permitted_file(self):
        hits = sweep_hits(self.tree, self.pattern)
        self.assertTrue(hits, "the sweep matched nothing in the run tree, where README.md is expected to match; "
                              "this measured nothing")
        self.assertEqual(sweep_problems(hits, permitted_files(self.pre)), [],
                         "a file outside the permitted set names the study in the run tree")

    def test_a_planted_file_naming_the_study_is_refused(self):
        copy = Path(self.tmp.name) / "copy"
        shutil.copytree(self.tree, copy, ignore=shutil.ignore_patterns(".git"))
        (copy / PLANTED).parent.mkdir(parents=True, exist_ok=True)
        (copy / PLANTED).write_text("Background reading: the gap study and its pre-registration.\n")
        problems = sweep_problems(sweep_hits(copy, self.pattern), permitted_files(self.pre))
        self.assertTrue(any(p.startswith(PLANTED.as_posix()) for p in problems),
                        f"a planted file naming the study went unrefused: {problems}")


if __name__ == "__main__":
    unittest.main()
