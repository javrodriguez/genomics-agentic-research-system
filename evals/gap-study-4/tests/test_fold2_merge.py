#!/usr/bin/env python3
"""Lane fold2/merge (Gap Study round 4): the no-match take whose end state cannot be read, built at the merge.

Named by lane fold2/la2 (m6's residual) and lane fold2/la1 ("Coordinator item", fold2-la1-REPORT.md), and assigned
to the merge lane by glitch-45 (Thu 29 Oct 2026, under Javier's standing delegation).

The gap: a take after the agent's first turn whose records match no routing row is ruled by its class's
pre-registered default (routing.json no_match_defaults), which is graded. Pre-freeze review 2's m6 now refuses a
graded ruling on a take whose own grader cannot read its committed end state, and the no-match rule refused every
other ruling, so no ruling could stand for such a take.

The fold: the after-first-turn no_match_defaults entry carries an optional `unreadable` alternative, a route ruling to
aborted. routing.py --check allows it on an after-first-turn entry only. batch accepts it only when the ruling's cite
has the form m6 requires ("end state unreadable: <ExceptionType>"); the door and the publication
(check_results.ruled_route_problems) then hold the cite to the reading the grader actually failed with
(check_results.unread_cite_holds) and refuse it on an end state that reads whole.

Synthetic records only; no model, network, container or git.
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
_PATH = list(sys.path)
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import batch  # noqa: E402
import routing  # noqa: E402
import takes  # noqa: E402
from graders import labels4  # noqa: E402
import test_pf1_routing_rulings as rr  # noqa: E402

sys.path[:] = _PATH

A, B = labels4.AFTER_FIRST_TURN, labels4.BEFORE_FIRST_TURN
CITE = batch.END_STATE_UNREAD_CITE
CITED = f"{CITE}: ValueError, the take's evidence folder cannot be loaded"


def after_no_match():
    return rr.stopped(rr.records(end=labels4.END_ERROR))           # after the first turn, no row matches


def before_no_match():
    return rr.stopped(rr.records(B, turns=1, end=labels4.END_TURN))   # before it, no row matches


def aborted(cite):
    return rr.ruling(*rr.rt(labels4.ABORTED), cite=cite)


def entry(table, when, end):
    return next(e for e in table[routing.NO_MATCH_KEY]["entries"] if (e["when"], e["end"]) == (when, end))


def without_alternative(table):
    t = copy.deepcopy(table)
    for e in t[routing.NO_MATCH_KEY]["entries"]:
        e.pop("unreadable", None)
    return t


def standing(word):
    def read(row, o):
        if word == "raise":
            raise ValueError("the take's evidence folder cannot be loaded")
        return word
    return read


class TheTable(unittest.TestCase):
    """routing.json carries the alternative, and routing.py --check allows it after the first turn only."""

    def test_the_after_first_turn_default_carries_the_unreadable_alternative(self):
        alt = entry(rr.REAL, A, labels4.END_ERROR).get("unreadable")
        self.assertIsInstance(alt, dict, "the after-first-turn no-match default has no unreadable alternative")
        self.assertEqual((alt["ruling"], alt["route"], alt["cite"]), (labels4.RULE_ROUTE, labels4.ABORTED, CITE))
        self.assertTrue(alt["why"].strip())

    def test_routing_names_the_alternative_for_after_first_turn_records_only(self):
        self.assertEqual(routing.no_match_unreadable(after_no_match()["records"], rr.REAL),
                         (labels4.RULE_ROUTE, labels4.ABORTED))
        self.assertIsNone(routing.no_match_unreadable(before_no_match()["records"], rr.REAL))
        self.assertEqual(routing.no_match_default(after_no_match()["records"], rr.REAL),
                         (labels4.RULE_ROUTE, labels4.GRADED), "the default itself is unchanged")

    def test_the_real_table_is_sound(self):
        self.assertEqual(routing.no_match_problems(rr.REAL), [])

    def test_check_refuses_the_alternative_before_the_first_turn(self):
        t = copy.deepcopy(rr.REAL)
        entry(t, B, labels4.END_TURN)["unreadable"] = copy.deepcopy(entry(t, A, labels4.END_ERROR)["unreadable"])
        self.assertTrue(any("unreadable" in p for p in routing.no_match_problems(t)),
                        "an unreadable alternative before the first turn passes --check")

    def test_check_refuses_a_malformed_alternative(self):
        for name, change in (("route graded", {"route": labels4.GRADED}), ("route pause", {"route": labels4.PAUSE}),
                             ("another cite", {"cite": "synthetic cite"}), ("no why", {"why": " "}),
                             ("a re-run ruling", {"ruling": labels4.RULE_RERUN}), ("an extra key", {"extra": 1})):
            with self.subTest(name=name):
                t = copy.deepcopy(rr.REAL)
                e = entry(t, A, labels4.END_ERROR)
                e["unreadable"] = dict(e["unreadable"], **change)
                self.assertTrue(routing.no_match_problems(t), f"--check passes an alternative with {name}")

    def test_check_refuses_an_alternative_on_an_aborted_default(self):
        t = copy.deepcopy(rr.REAL)
        e = entry(t, A, labels4.END_ERROR)
        e["route"] = labels4.ABORTED
        self.assertTrue(routing.no_match_problems(t), "an alternative beside an aborted default passes --check")


class TheBatch(unittest.TestCase):
    """batch (the restart and the door's shared rule) accepts the alternative only with the cited reading's form."""

    def bad(self, take, ruling, table=rr.REAL):
        return rr.history_ok(batch, [take, ruling], table)

    def test_an_aborted_ruling_citing_the_unreadable_end_state_after_the_first_turn_passes(self):
        self.assertEqual(self.bad(after_no_match(), aborted(CITED)), [])

    def test_the_default_still_passes(self):
        self.assertEqual(self.bad(after_no_match(), rr.ruling(*rr.rt(labels4.GRADED))), [])

    def test_without_the_cited_reading_it_is_refused(self):
        for cite in ("synthetic cite", CITE, f"{CITE}.", f"NOT {CITED}", f"the {CITED}", f"{CITE}: ", f"{CITE}: 9x"):
            with self.subTest(cite=cite):
                self.assertTrue(self.bad(after_no_match(), aborted(cite)), f"aborted citing {cite!r} passes")

    def test_before_the_first_turn_it_is_refused(self):
        self.assertTrue(self.bad(before_no_match(), aborted(CITED)))

    def test_a_table_without_the_alternative_refuses_it(self):
        self.assertTrue(self.bad(after_no_match(), aborted(CITED), without_alternative(rr.REAL)))

    def test_other_routes_stay_refused(self):
        for choice in (rr.RERUN, rr.rt(labels4.PAUSE), rr.rt(labels4.HARNESS_ERROR)):
            with self.subTest(choice=choice):
                self.assertTrue(self.bad(after_no_match(), rr.ruling(*choice, cite=CITED)))


class TheDoor(unittest.TestCase):
    """The door as takes.commit_ruling runs it: validate_ruling (batch's history_problems on the real table), then
    ruling_door_problems (m6's end-state reading)."""

    def door(self, ruling, word):
        history = [after_no_match()]
        try:
            takes.validate_ruling(ruling, history)
        except ValueError as e:
            return [f"validate_ruling: {e}"]
        return takes.ruling_door_problems(ruling, history, [dict(rr.ROW, attempt=1)], table=rr.REAL,
                                          standing=standing(word), driver_refusal=lambda row, o: None)

    def test_an_unreadable_end_state_ruled_aborted_with_its_reading_stands(self):
        self.assertEqual(self.door(aborted(CITED), "raise"), [])

    def test_a_readable_end_state_ruled_aborted_is_refused(self):
        self.assertTrue(self.door(aborted(CITED), "right"))

    def test_a_cite_naming_another_exception_type_is_refused(self):
        self.assertTrue(self.door(aborted(f"{CITE}: KeyError, missing"), "raise"))

    def test_an_unreadable_end_state_ruled_graded_is_refused(self):
        self.assertTrue(self.door(rr.ruling(*rr.rt(labels4.GRADED)), "raise"))

    def test_a_readable_end_state_takes_its_default(self):
        self.assertEqual(self.door(rr.ruling(*rr.rt(labels4.GRADED)), "wrong"), [])


class TheRuleText(unittest.TestCase):
    def test_the_ruling_rule_names_the_alternative(self):
        text = batch.RULING_RULE["text"]
        self.assertIn("pre-registered alternative", text)
        self.assertIn("no_match_defaults", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
