#!/usr/bin/env python3
"""Round 4's test battery: every tests/test_*.py, discovered with unittest.

    python3 -W ignore evals/gap-study-4/test_round4.py

Round 3's battery is round 3's record and is not copied. Each module's tests live in their own
tests/test_<module>.py, so parallel lanes never edit one file, and each test that guards something mutates
what it guards and watches its check go red. A battery that discovers no test is a defect, not a pass.

Home fold of review round 1 (W1A-2): the count is per module, not per battery. Every tests/test_*.py is loaded
on its own and must hold at least one test, and a test_*.py anywhere deeper under tests/ (which discovery would
not load) fails the battery, so no module rides on another's tests.

No model, no network, stdlib only.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = HERE / "tests"
PATTERN = "test_*.py"
sys.path.insert(0, str(HERE))


def suite(folder: Path | None = None) -> unittest.TestSuite:
    folder = TESTS if folder is None else folder
    return unittest.defaultTestLoader.discover(str(folder), pattern=PATTERN, top_level_dir=str(folder))


def module_problems(folder: Path | None = None) -> list[str]:
    """Every test module that would add nothing: one holding no test, one that fails to load, and one deeper than
    tests/ itself."""
    folder = TESTS if folder is None else folder
    out = []
    for f in sorted(folder.rglob(PATTERN)):
        if "__pycache__" in f.parts:
            continue
        if f.parent != folder:
            out.append(f"{f.relative_to(folder)} is below {folder.name}/; discovery would not load it (keep tests flat)")
            continue
        loaded = unittest.defaultTestLoader.discover(str(folder), pattern=f.name, top_level_dir=str(folder))
        failed = [t for t in _leaves(loaded) if type(t).__name__ == "_FailedTest"]
        if failed:
            out.append(f"{f.name} does not load")
        elif loaded.countTestCases() == 0:
            out.append(f"{f.name} holds no test; a module that runs nothing is not a pass")
    return out


def _leaves(s):
    for t in s:
        if isinstance(t, unittest.TestSuite):
            yield from _leaves(t)
        else:
            yield t


def main(folder: Path | None = None) -> int:
    folder = TESTS if folder is None else folder
    s = suite(folder)
    if s.countTestCases() == 0:
        print(f"test_round4: no test found under {folder}/{PATTERN}; a battery that runs nothing is not a pass")
        return 1
    bad = module_problems(folder)
    for b in bad:
        print(f"test_round4: {b}")
    result = unittest.TextTestRunner(verbosity=2).run(s)
    return 0 if result.wasSuccessful() and not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
