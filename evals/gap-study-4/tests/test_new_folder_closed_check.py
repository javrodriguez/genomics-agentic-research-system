#!/usr/bin/env python3
"""The new-folder gap's task-level closed check (glitch-06's ruling on review r2-3, 14 Oct 2026).

inotifywait -r watches a folder the agent creates only after reading its CREATE, so an access inside a new folder
can go unseen (prereg-draft box_residuals[3]). An access is never missed on a path whose folder already exists
when the take starts: that folder is watched from the start. So the check, derived from the task definitions and
the built fixtures (every task half, each built by drive.build_take_fixture into a scratch copy of the run tree
it needs), is: every path an access-reading grader consults has its whole folder chain present, as real folders,
before the take starts. A task whose grader consults a path in a folder the fixture does not create fails by name.

The access-reading graders, by repository search (graders/*.py reading `accesses` or `accesses_by_stretch`):
scope_read (`planted`, opens) and new_tasks' approval-scope (`link_paths`, deletes). Each consulted path is also
reported as present or absent before the take, so the record shows which paths exist outright.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import drive  # noqa: E402

PROJECT = "run-0000abcd"
TASKS = HERE / "tasks"
# The graders that read the access log, and the grader_spec key whose paths each consults (repository search,
# 14 Oct 2026: graders/scope_read.py planted_accesses/outside_accesses; graders/new_tasks.py:611 approval-scope).
ACCESS_READERS = {"scope-read": "planted", "approval-scope": "link_paths"}


def consulted(task: dict, key: str) -> list:
    """Every path the grader consults for `task`, from any half's grader_spec ({project} rendered)."""
    out = []
    specs = [task.get("grader_spec", {})] + [h.get("grader_spec", {}) for h in task.get("halves", {}).values()]
    for spec in specs:
        v = spec.get(key)
        vals = v if isinstance(v, list) else [p for ps in (v or {}).values() for p in ps] if isinstance(v, dict) else []
        out += [p.replace("{project}", PROJECT) for p in vals]
    return sorted(set(out))


def chain_is_real(tree: Path, rel: str) -> bool:
    p = tree
    for seg in rel.split("/")[:-1]:
        p = p / seg
        try:
            if not stat.S_ISDIR(os.lstat(p).st_mode):
                return False
        except OSError:
            return False
    return True


def readings() -> list:
    """One row per (task, half, consulted path): the chain present before the take, and the path itself present."""
    rows = []
    for name, key in sorted(ACCESS_READERS.items()):
        task = json.loads((TASKS / f"{name}.json").read_text())
        paths = consulted(task, key)
        for half, h in sorted(task["halves"].items()):
            work = Path(tempfile.mkdtemp())
            try:
                tree = work / "tree"
                tree.mkdir()
                # the run tree's GARS system, as the pinned export carries it (the project generators need it)
                shutil.copytree(HERE.parents[1] / "gars", tree / "gars", symlinks=True,
                                ignore=shutil.ignore_patterns("__pycache__"))
                with contextlib.redirect_stdout(io.StringIO()):
                    rec, _ = drive.build_take_fixture(h["fixture"], tree, PROJECT)
                for rel in paths:
                    rows.append({"task": name, "half": half, "path": rel, "built": rec is not None,
                                 "chain_present": chain_is_real(tree, rel), "present": os.path.lexists(tree / rel)})
            finally:
                shutil.rmtree(work)
    return rows


class NewFolderClosedCheck(unittest.TestCase):
    def test_every_consulted_path_sits_in_a_folder_present_before_the_take(self):
        rows = readings()
        self.assertTrue(rows)
        self.assertEqual({r["task"] for r in rows}, set(ACCESS_READERS))
        self.assertEqual([r for r in rows if not r["built"]], [])
        bad = [f"{r['task']}/{r['half']}: {r['path']}" for r in rows if not r["chain_present"]]
        self.assertEqual(bad, [], "a grader consults a path inside a folder the agent would have to create")

    def test_the_access_readers_are_exactly_the_searched_ones(self):
        readers = sorted(p.stem for p in (HERE / "graders").glob("*.py") if p.stem != "endstate"
                         and any(s in p.read_text() for s in (".accesses(", ".accesses_by_stretch(")))
        self.assertEqual(readers, ["new_tasks", "scope_read"])


if __name__ == "__main__":
    if sys.argv[1:] == ["--print"]:
        print(json.dumps(readings(), indent=1))
        raise SystemExit(0)
    unittest.main()
