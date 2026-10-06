#!/usr/bin/env python3
"""Round 4's test battery: every tests/test_*.py, discovered with unittest.

    python3 -W ignore evals/gap-study-4/test_round4.py

Round 3's battery is round 3's record and is not copied. Each module's tests live in their own
tests/test_<module>.py, so parallel lanes never edit one file, and each test that guards something mutates
what it guards and watches its check go red. A battery that discovers no test is a defect, not a pass.

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


def main(folder: Path | None = None) -> int:
    folder = TESTS if folder is None else folder
    s = suite(folder)
    if s.countTestCases() == 0:
        print(f"test_round4: no test found under {folder}/{PATTERN}; a battery that runs nothing is not a pass")
        return 1
    result = unittest.TextTestRunner(verbosity=2).run(s)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
