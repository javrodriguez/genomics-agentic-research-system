#!/usr/bin/env python3
"""A red in the mutation battery names its failing tests, not only the last lines of their output.

    python3 evals/gap-study-2/test_harness.py TheBatteryNamesTheFailingTests

Found in CI on 14 September 2026: twelve guards printed CONTROL RED with the tail "Ran 34 tests | FAILED
(failures=1)", and the log never said which test had failed, because the battery keeps only the last three lines of
a guard's output. So Sandbox.control and Sandbox.expect now append every unittest `FAIL:` and `ERROR:` line.

No sandbox is built: control() and expect() are called on a stub whose run_out returns a planted output.
No model, no network. stdlib only.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

UNITTEST_OUT = """..F.E
======================================================================
ERROR: test_b (tests_x.SomeGuard.test_b)
----------------------------------------------------------------------
Traceback (most recent call last):
RuntimeError: boom
======================================================================
FAIL: test_a (tests_x.SomeGuard.test_a)
----------------------------------------------------------------------
AssertionError: the planted read went unrefused
----------------------------------------------------------------------
Ran 5 tests in 0.420s

FAILED (failures=1, errors=1)
"""


def load_mutations():
    """This study's mutations.py, imported by name as tests_hygiene.py does: it registers its topic modules under
    `mutations`, so a copy loaded under another name cannot find itself. The file is checked to be this study's."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import mutations
    if Path(mutations.__file__).resolve() != HERE / "mutations.py":
        raise ImportError(f"imported another study's mutations.py: {Path(mutations.__file__).name} from outside this study")
    return mutations


class _Stub:
    controlled = False

    def __init__(self, code: int, out: str):
        self.code, self.out = code, out

    def run_out(self, argv):
        return self.code, self.out


class TheBatteryNamesTheFailingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = load_mutations()

    def test_a_control_red_names_every_failing_test(self):
        with self.assertRaises(self.m.ControlRed) as ctx:
            self.m.Sandbox.control(_Stub(1, UNITTEST_OUT), ["guard"])
        text = str(ctx.exception)
        self.assertIn("FAILED (failures=1, errors=1)", text, "the tail the battery printed before is gone")
        for name in ("FAIL: test_a (tests_x.SomeGuard.test_a)", "ERROR: test_b (tests_x.SomeGuard.test_b)"):
            self.assertIn(name, text, "a CONTROL RED does not name its failing test")

    def test_a_red_for_the_wrong_reason_names_its_failing_test(self):
        with self.assertRaises(RuntimeError) as ctx:
            self.m.Sandbox.expect(1, UNITTEST_OUT, "a phrase the output does not carry")
        self.assertIn("FAIL: test_a (tests_x.SomeGuard.test_a)", str(ctx.exception),
                      "a red for the wrong reason does not name its failing test")

    def test_a_green_control_and_a_right_red_are_unchanged(self):
        stub = _Stub(0, "OK")
        self.m.Sandbox.control(stub, ["guard"])
        self.assertTrue(stub.controlled)
        self.assertEqual(self.m.Sandbox.expect(1, UNITTEST_OUT, "went unrefused"), 1)
        self.assertEqual(self.m.failing_tests("Ran 3 tests\n\nOK\n"), "", "a clean run names a failing test")


if __name__ == "__main__":
    unittest.main()
