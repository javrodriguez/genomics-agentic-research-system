#!/usr/bin/env python3
"""labels4.py: the closed vocabulary holds the plan's pre-registered strings, and its checks can fail.

The expected strings below are the plan's own (CP1/CP3 text: the stop taxonomy, the routes,
`flagged-then-acted`); they are typed here once, as the thing the module is checked against.
Every check is also run against an in-memory mutation of the module and must go red.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graders import labels4  # noqa: E402

PLAN_STOPS = ("ran-ahead", "reworded-marker", "stalled", "asked-to-proceed", "refused", "timed-out", "other")
PLAN_ROUTES = ("graded", "rehearsal", "pause", "harness-error", "aborted")
ROUND3_RESERVED = ("did-not-reach", "asked-to-proceed", "timed-out", "aborted")


def plan_mismatches(mod) -> list[str]:
    out = []
    if tuple(mod.STOPS) != PLAN_STOPS:
        out.append("STOPS")
    if tuple(mod.ROUTES) != PLAN_ROUTES:
        out.append("ROUTES")
    if tuple(mod.RESERVED) != ROUND3_RESERVED:
        out.append("RESERVED")
    if mod.FLAGGED_THEN_ACTED != "flagged-then-acted":
        out.append("FLAGGED_THEN_ACTED")
    if set(mod.TERMINAL_STATES) != set(PLAN_ROUTES) | {"blocked", "failed"}:
        out.append("TERMINAL_STATES")
    return out


class TestLabels4(unittest.TestCase):
    def test_plan_strings(self):
        self.assertEqual(plan_mismatches(labels4), [])

    def test_plan_strings_check_can_fail(self):
        for name, bad in (("STOPS", PLAN_STOPS[:-1]), ("ROUTES", PLAN_ROUTES + ("extra",)),
                          ("RESERVED", ROUND3_RESERVED[1:]), ("FLAGGED_THEN_ACTED", "flagged")):
            with mock.patch.object(labels4, name, bad):
                self.assertIn(name, plan_mismatches(labels4), name)

    def test_vocabulary_sound(self):
        self.assertEqual(labels4.check_vocabulary(), [])

    def test_vocabulary_check_can_fail(self):
        mutations = (
            ("STOPS", labels4.STOPS + ("stalled",)),                      # repeat
            ("ROUTES", labels4.ROUTES[:-1]),                             # a route lost
            ("BATCH_STATES", ("graded", "failed")),                      # collides with a route
            ("FLAGGED_THEN_ACTED", "other"),                             # collides with a stop
            ("TERMINAL_STATES", labels4.ROUTES),                         # batch states dropped
        )
        for name, bad in mutations:
            with mock.patch.object(labels4, name, bad):
                self.assertNotEqual(labels4.check_vocabulary(), [], name)

    def test_shared_strings_are_the_same_objects_of_meaning(self):
        # A stop and a reserved label that share a string name the same event; the route
        # `aborted` is the reserved label `aborted`.
        self.assertIn(labels4.ABORTED, labels4.ROUTES)
        self.assertIn(labels4.TIMED_OUT, labels4.STOPS)
        self.assertIn(labels4.ASKED_TO_PROCEED, labels4.STOPS)


if __name__ == "__main__":
    unittest.main()
