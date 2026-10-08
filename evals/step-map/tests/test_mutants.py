#!/usr/bin/env python3
"""Tests for the mutant runner itself: its kill count must be able to say "survived".

Run alone: python3 evals/step-map/tests/test_mutants.py (light: parses runner output only).
"""
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("stepmap_mutants", os.path.join(HERE, "mutants.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

OUTPUT = """test_a (__main__.A.test_a) ... ok
The facts under evals/step-map/facts/ are re-derived and diffed byte for byte. ... FAIL
Some docstring line ... FAIL

======================================================================
FAIL: test_committed_facts_equal_a_fresh_extraction (__main__.PublishedFactsTests.test_committed_facts_equal_a_fresh_extraction)
The facts under evals/step-map/facts/ are re-derived and diffed byte for byte.
----------------------------------------------------------------------
AssertionError: x

======================================================================
FAIL: test_b (__main__.B.test_b)
Some docstring line
----------------------------------------------------------------------
AssertionError: y
"""


class RunnerTests(unittest.TestCase):
    def test_failures_read_from_id_headers(self):
        self.assertEqual(M.failed_tests(OUTPUT),
                         ["PublishedFactsTests.test_committed_facts_equal_a_fresh_extraction",
                          "B.test_b"])

    def test_snapshot_failure_is_not_a_kill(self):
        only_snapshot = OUTPUT.split("======================================================================\nFAIL: test_b")[0]
        self.assertEqual(M.kills(only_snapshot), [])
        self.assertEqual(M.kills(OUTPUT), ["B.test_b"])

    def test_runner_has_a_negative_control(self):
        controls = [m for m in M.MUTANTS if m[0] == M.CONTROL]
        self.assertEqual(len(controls), 1)
        self.assertIn("SCHEMA", controls[0][2])

    def test_mutant_runs_disable_the_snapshot(self):
        self.assertEqual(M.RUN_ENV, {"STEPMAP_NO_SNAPSHOT": "1"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
