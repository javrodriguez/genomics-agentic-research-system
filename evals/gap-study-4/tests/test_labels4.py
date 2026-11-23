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
# How the host saw a turn end: the API's end_turn, the reserved timed-out (a timeout stays the
# agent's), and error. Only the first two can end a graded take.
TURN_ENDS = ("end_turn", "timed-out", "error")
GRADED_ENDS = ("end_turn", "timed-out")
# Round 3's cell state at a rehearsal or pause cap, as takes.py:284 and 289 print it (e2979b31).
ROUND3_CELL_STATE = "incomplete — mechanical"
# Review round 3, W1B3-1 (the gap4 lane lead's brief; glitch-f3 accepted it as written, 6 Oct 2026): a restart goes on
# past a blocked take, or a take that failed after its drive started, only on a ruling committed in the repo for that
# (slot, attempt), "one of `re-run` or `route <route>`", in "an outcome kind such as `ruling`". Typed here once.
BRIEF_RULING_KIND = "ruling"
BRIEF_RULINGS = ("re-run", "route")


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
    if tuple(mod.TURN_ENDS) != TURN_ENDS:
        out.append("TURN_ENDS")
    if tuple(mod.GRADED_ENDS) != GRADED_ENDS:
        out.append("GRADED_ENDS")
    return out


def cell_state_mismatches(mod) -> list[str]:
    """glitch-f3's cap ruling: round 3's cell state is a labels4 word, in its own group and in the vocabulary."""
    out = []
    word = getattr(mod, "INCOMPLETE_MECHANICAL", None)
    if word != ROUND3_CELL_STATE:
        out.append("INCOMPLETE_MECHANICAL")
    if tuple(getattr(mod, "CELL_STATES", ())) != (ROUND3_CELL_STATE,):
        out.append("CELL_STATES")
    if ROUND3_CELL_STATE not in getattr(mod, "VOCABULARY", ()):
        out.append("VOCABULARY")
    return out


def ruling_mismatches(mod) -> list[str]:
    """W1B3-1: the ruling record's kind and its two words are labels4's, in their own group and in the vocabulary."""
    out = []
    if getattr(mod, "RULING", None) != BRIEF_RULING_KIND:
        out.append("RULING")
    if tuple(getattr(mod, "RULINGS", ())) != BRIEF_RULINGS:
        out.append("RULINGS")
    if (getattr(mod, "RULE_RERUN", None), getattr(mod, "RULE_ROUTE", None)) != BRIEF_RULINGS:
        out.append("RULE_RERUN, RULE_ROUTE")
    if not set(BRIEF_RULINGS + (BRIEF_RULING_KIND,)) <= set(getattr(mod, "VOCABULARY", ())):
        out.append("VOCABULARY")
    return out


class TestLabels4(unittest.TestCase):
    def test_plan_strings(self):
        self.assertEqual(plan_mismatches(labels4), [])

    def test_plan_strings_check_can_fail(self):
        for name, bad in (("STOPS", PLAN_STOPS[:-1]), ("ROUTES", PLAN_ROUTES + ("extra",)),
                          ("RESERVED", ROUND3_RESERVED[1:]), ("FLAGGED_THEN_ACTED", "flagged"),
                          ("TURN_ENDS", ("end_turn", "timeout", "error")), ("GRADED_ENDS", TURN_ENDS)):
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
            ("TURN_ENDS", labels4.TURN_ENDS + ("end_turn",)),            # repeat
            ("TURN_ENDS", ("end_turn", "error")),                        # the timeout lost
            ("GRADED_ENDS", labels4.TURN_ENDS),                          # error graded
            ("GRADED_ENDS", ("end_turn",)),                              # a timeout no longer the agent's
            ("TURN_ENDS", ("end_turn", "timed-out", "error", "graded")), # collides with a route
        )
        for name, bad in mutations:
            with mock.patch.object(labels4, name, bad):
                self.assertNotEqual(labels4.check_vocabulary(), [], name)

    def test_incomplete_mechanical_is_round_3s_cell_state(self):
        """glitch-f3's ruling (in-plan, 6 Oct 2026; glitch-f3's, not the owner's): a half-cell that reaches its
        rehearsal or pause cap publishes round 3's cell state (evals/gap-study-3/takes.py:280-291 at e2979b31),
        and that word lives once, here, in the closed vocabulary."""
        self.assertEqual(cell_state_mismatches(labels4), [])
        self.assertEqual(labels4.check_vocabulary(), [])

    def test_cell_state_check_can_fail(self):
        for name, bad in (("INCOMPLETE_MECHANICAL", "incomplete - mechanical"),   # retyped
                          ("INCOMPLETE_MECHANICAL", "incomplete"),                # cut short
                          ("CELL_STATES", ())):                                   # dropped from its group
            with mock.patch.object(labels4, name, bad):
                self.assertIn(name, cell_state_mismatches(labels4), (name, bad))
        with mock.patch.object(labels4, "VOCABULARY", labels4.VOCABULARY - {ROUND3_CELL_STATE}):
            self.assertIn("VOCABULARY", cell_state_mismatches(labels4))
        for bad in (("graded",), ("blocked",), ("timed-out",), (ROUND3_CELL_STATE, ROUND3_CELL_STATE)):
            with mock.patch.object(labels4, "CELL_STATES", bad):        # collides with a route, a batch state,
                self.assertNotEqual(labels4.check_vocabulary(), [], bad)  # a turn end, or repeats

    def test_ruling_words_are_the_briefs(self):
        """W1B3-1 (glitch-f3 accepted the brief's fix as written, 6 Oct 2026; glitch-f3's, not the owner's)."""
        self.assertEqual(ruling_mismatches(labels4), [])
        self.assertEqual(labels4.check_vocabulary(), [])

    def test_ruling_check_can_fail(self):
        for name, bad in (("RULING", "rule"), ("RULINGS", ("re-run",)), ("RULE_RERUN", "rerun"),
                          ("RULE_ROUTE", "reroute")):
            with mock.patch.object(labels4, name, bad):
                self.assertNotEqual(ruling_mismatches(labels4), [], (name, bad))
        with mock.patch.object(labels4, "VOCABULARY", labels4.VOCABULARY - {BRIEF_RULING_KIND}):
            self.assertIn("VOCABULARY", ruling_mismatches(labels4))
        for name, bad in (("RULINGS", ("re-run", "re-run")),      # repeats
                          ("RULINGS", ("re-run", "graded")),      # collides with a route
                          ("RULING", "blocked"),                  # the kind collides with a batch state
                          ("RULINGS", ("re-run", "timed-out"))):  # collides with a turn end
            with mock.patch.object(labels4, name, bad):
                self.assertNotEqual(labels4.check_vocabulary(), [], (name, bad))

    def test_shared_strings_are_the_same_objects_of_meaning(self):
        # A stop and a reserved label that share a string name the same event; the route
        # `aborted` is the reserved label `aborted`.
        self.assertIn(labels4.ABORTED, labels4.ROUTES)
        self.assertIn(labels4.TIMED_OUT, labels4.STOPS)
        self.assertIn(labels4.ASKED_TO_PROCEED, labels4.STOPS)


if __name__ == "__main__":
    unittest.main()
