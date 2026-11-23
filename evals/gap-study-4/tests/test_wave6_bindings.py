#!/usr/bin/env python3
"""The wave 6 merge bindings: what the slices only show when they share test_round4's one process.

Binding 1, sys.path. check_take.py (a round 3 copy) puts the shared `evals/` folder at the front of sys.path when it is
imported, so its round 3 imports resolve. Three wave 6 test modules import it, directly or through drive.py:
test_box_integration (S6, and test_drive_loop through it), test_check_take (S6) and test_checker_body (S6b). Before
the merge fix, none of them put sys.path back, so every module the battery ran after them saw `evals/` on the path and
test_confounded_design's contract-drift test (it asserts `evals/` is absent) failed in athena's run on 7e057eb2.

Each module now restores sys.path, in place, when its tearDownModule closes its stack. The check runs each module's
setUpModule, then imports check_take.py the way drive.py does at test time, then its tearDownModule, in a fresh
interpreter per module so this process's path is never touched, and requires sys.path to come back exactly as it
was. Red first: on the merge head before the fix all three modules came back with `evals/` added.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TESTS = HERE / "tests"
EVALS = HERE.parent

MODULES = ("test_box_integration", "test_check_take", "test_checker_body")

PROBE = r"""
import importlib, json, sys
here, tests, name = sys.argv[1], sys.argv[2], sys.argv[3]
for p in (here, tests):
    if p not in sys.path:
        sys.path.insert(0, p)
mod = importlib.import_module(name)
before = list(sys.path)
mod.setUpModule()
try:
    import check_take  # noqa: F401  (drive.py imports it at test time; setUpModule may already have)
finally:
    mod.tearDownModule()
print(json.dumps({"before": before, "after": list(sys.path)}))
"""


def probe(name: str) -> dict:
    got = subprocess.run([sys.executable, "-B", "-W", "ignore", "-c", PROBE, str(HERE), str(TESTS), name],
                         capture_output=True, text=True, timeout=110, cwd=str(TESTS))
    if got.returncode != 0:
        raise AssertionError(f"W6M1.probe:{name} exited {got.returncode}: {got.stderr[-2000:]}")
    return json.loads(got.stdout.strip().splitlines()[-1])


class BindingOneSysPath(unittest.TestCase):
    def test_each_module_puts_sys_path_back(self):
        for name in MODULES:
            with self.subTest(module=name):
                seen = probe(name)
                self.assertNotIn(str(EVALS), [p for p in seen["after"] if p not in seen["before"]],
                                 f"W6M1.evals-left:{name}")
                self.assertEqual(seen["after"], seen["before"], f"W6M1.restored:{name}")

    def test_the_probe_sees_the_insertion(self):
        # Non-vacuity: without any teardown, importing check_take.py does put evals/ on the path, so a green above
        # is the restore at work and not a probe that never saw the insertion.
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", "-c",
                              "import sys, json; sys.path.insert(0, sys.argv[1]); before = list(sys.path); "
                              "import check_take; print(json.dumps([p for p in sys.path if p not in before]))",
                              str(HERE)], capture_output=True, text=True, timeout=110, cwd=str(TESTS))
        self.assertEqual(got.returncode, 0, got.stderr[-2000:])
        self.assertIn(str(EVALS), json.loads(got.stdout.strip().splitlines()[-1]), "W6M1.non-vacuous")


if __name__ == "__main__":
    unittest.main(verbosity=2)
