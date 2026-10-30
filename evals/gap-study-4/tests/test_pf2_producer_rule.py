#!/usr/bin/env python3
"""Pre-freeze review 2, MAJOR 1: glitch-45's ruling 2 (29 Oct 2026), the producer rule on the round-3 reasons.

"gap4 routing: A" copied round 3's values into routing.json; it did not fix their routes. Read by raise site:
  P.pure     a reason every raise site of which reads a record the agent can write (the session file, a sub-agent file
             or a vendor native store) routes aborted after the agent's first turn, by the agent-reachable-reason row;
             a rehearsal before it, as before
  P.mixed    a reason with a site that reads only driver or host records keeps harness-error, and the class table says
             "mixed, kept harness-error, counted in STOPPED_ROUTES"
  P.finalize finalize-abort-after-first-turn routes aborted (an operator step that fails on a run tree the agent
             shaped; round 3's own reading)
  P.hcv      harness-condition-violated keeps its precedence (glitch-b5's ruling 3); the table says "reachable, kept,
             counted"
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import routing  # noqa: E402
import test_routing as tr  # noqa: E402
from graders import labels4  # noqa: E402

PURE = ("readers-disagree", "unknown-harness-origin", "operator-lines", "stop-at-held-marker",
        "continued-past-unheld-marker", "leak-in-loaded-context", "checkout-binding")
MIXED = ("no-session-id", "leak-in-operator-turn", "project-name", "inherited-context", "session-binding",
         "constant-binding", "outcome-binding", "environment-record", "transcript-unreadable", "model-binding")
DRIVER = ("script-not-a-list", "fixture-binding", "invocation", "stop-without-a-wait-point")


def route(ids, phase=labels4.AFTER_FIRST_TURN, edit=None):
    rec = tr.baseline(phase)
    if phase == labels4.BEFORE_FIRST_TURN:
        tr.silent_turn(rec)
    rec["checker_reasons"] = list(ids)
    if edit:
        edit(rec)
    return routing.route(rec, tr.test_table())


class ProducerRule(unittest.TestCase):
    def test_p_pure(self):
        for rid in PURE:
            with self.subTest(reason=rid):
                self.assertEqual(route([rid])["route"], labels4.ABORTED)
                self.assertEqual(route([rid])["rows"], ["agent-reachable-reason"])
                self.assertEqual(route([rid], labels4.BEFORE_FIRST_TURN)["route"], labels4.REHEARSAL)
                self.assertEqual(route([rid, "harness-condition-violated"])["route"], labels4.HARNESS_ERROR)

    def test_p_mixed_and_driver(self):
        entries = routing.load_table()["agent_reach"]["entries"]
        for rid in MIXED + DRIVER:
            with self.subTest(reason=rid):
                self.assertEqual(route([rid])["route"], labels4.HARNESS_ERROR)
        for rid in MIXED:
            with self.subTest(reason=rid):
                self.assertIn("mixed, kept harness-error, counted in STOPPED_ROUTES", entries[f"reason:{rid}"]["call"])
                self.assertNotIn("OWED", entries[f"reason:{rid}"]["call"])
        for rid in PURE:
            self.assertIsNone(entries[f"reason:{rid}"]["call"], rid)

    def test_p_finalize(self):
        got = route([], edit=lambda r: r["ledger"].__setitem__("finalize_abort", True))
        self.assertEqual(got["route"], labels4.ABORTED)
        self.assertEqual(got["rows"], ["finalize-abort-after-first-turn"])

    def test_p_hcv(self):
        e = routing.load_table()["agent_reach"]["entries"]["reason:harness-condition-violated"]
        self.assertTrue(e["reachable"])
        self.assertIn("reachable, kept, counted", e["call"])
        self.assertEqual(route(["harness-condition-violated", "subagent-unbound"])["route"], labels4.HARNESS_ERROR)


if __name__ == "__main__":
    unittest.main()
