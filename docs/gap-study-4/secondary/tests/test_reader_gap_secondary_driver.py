#!/usr/bin/env python3
"""OD201 secondary analysis (branch analysis/reader-gap-secondary only): reader_gap_secondary.py on fakes (review of
789374bf, MINOR 3). Item 2's selection of the takes ruled aborted with an "end state unreadable: ViewError" cite; the
takes the frozen reader cannot read that no such ruling covers (MINOR 1); item 3's compare; and item 4's side-by-side
decision tables with item 5's changed rows. No study data is read: every history, grade file and table here is a fake.

The driver under test is evals/gap-study-4/reader_gap_secondary.py, or the file RGS_DRIVER names (the red-before run
and the null mutants point it at another copy). Run from this folder:
    python3 -B -m unittest test_reader_gap_secondary_driver
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY))
import batch  # noqa: E402
from graders import labels4  # noqa: E402

DRIVER = Path(os.environ.get("RGS_DRIVER") or STUDY / "reader_gap_secondary.py")
_spec = importlib.util.spec_from_file_location("rgs_under_test", DRIVER)
rgs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rgs)


def ruling(slot, attempt=1, *, route=labels4.ABORTED, rule=labels4.RULE_ROUTE, cite="end state unreadable: ViewError: x"):
    return {"kind": labels4.RULING, "ruling": rule, "route": route, "slot": slot, "attempt": attempt, "cite": cite,
            "by": "fake", "why": "fake"}


def outcome(slot, attempt=1, state=labels4.ABORTED):
    return {"slot": slot, "attempt": attempt, "state": state}


HISTORY = [
    outcome("s-a"), ruling("s-a"),                                                     # selected
    outcome("s-b"), ruling("s-b", cite="end state unreadable: ViewError"),             # selected (bare cite)
    outcome("s-c"), ruling("s-c", cite="end state unreadable: OSError: y"),            # another exception: not
    outcome("s-d"), ruling("s-d", route=labels4.GRADED),                               # routed graded: not
    outcome("s-e"), ruling("s-e", rule=labels4.RULE_RERUN),                            # a re-run ruling: not
    outcome("s-f"), ruling("s-f", cite="the end state unreadable: ViewError"),         # not at the start: not
    outcome("s-g"), ruling("s-g", cite=None),                                          # no cite: not
    outcome("s-h", state=labels4.ABORTED),                                             # routed by the table, no ruling
    {"kind": batch.NIGHT_RULING, "cite": "end state unreadable: ViewError"},               # not a take's ruling
]


class Selection(unittest.TestCase):
    def test_only_route_rulings_to_aborted_citing_a_view_error_are_selected(self):
        got = [(e["slot"], e["attempt"]) for e in rgs.select_targets(HISTORY, batch, labels4)]
        self.assertEqual(got, [("s-a", 1), ("s-b", 1)])

    def test_an_outcome_is_never_selected(self):
        self.assertFalse(any(rgs.is_target(o, batch, labels4) for o in HISTORY if batch.is_outcome(o)))


class Uncovered(unittest.TestCase):
    FROZEN = {"s-a/1": {"raised": "ViewError"}, "s-h/1": {"raised": "ViewError"}, "s-c/1": {"raised": "OSError"},
              "s-d/1": {"raised": None, "sha256": "0" * 64}}
    PATCHED = {"s-a/1": {"raised": None}, "s-h/1": {"raised": None}, "s-c/1": {"raised": "OSError"},
               "s-d/1": {"raised": None, "sha256": "0" * 64}}

    def test_a_view_error_take_no_item_2_ruling_covers_is_named_with_its_route(self):
        targets = rgs.select_targets(HISTORY, batch, labels4)
        got = rgs.uncovered_unreadable(self.FROZEN, self.PATCHED, targets, HISTORY, batch)
        self.assertEqual([(u["slot"], u["attempt"], u["state"], u["rulings"], u["patched_reads"]) for u in got],
                         [("s-h", "1", labels4.ABORTED, [], True)])

    def test_its_sentence_names_the_take_and_why_item_2_leaves_it(self):
        targets = rgs.select_targets(HISTORY, batch, labels4)
        (s,) = rgs.uncovered_sentences(rgs.uncovered_unreadable(self.FROZEN, self.PATCHED, targets, HISTORY, batch))
        for words in ("`s-h` attempt 1", "never ruled", f"routed `{labels4.ABORTED}` by the routing table",
                      "graded in neither analysis", "does not cover it"):
            self.assertIn(words, s)

    def test_none_uncovered_writes_no_sentence(self):
        self.assertEqual(rgs.uncovered_sentences([]), [])


class Compare(unittest.TestCase):
    def run_compare(self, a, b):
        with tempfile.TemporaryDirectory() as d:
            fa, fb, out = Path(d, "a.json"), Path(d, "b.json"), Path(d, "c.json")
            fa.write_text(json.dumps(a))
            fb.write_text(json.dumps(b))
            ns = type("A", (), {"frozen": str(fa), "patched": str(fb), "out": str(out)})()
            try:
                rc = rgs.cmd_compare(ns)
            except SystemExit as e:
                return "refused", str(e)
            return rc, json.loads(out.read_text())

    @staticmethod
    def doc(parser, grades, reader="r" * 64):
        return {"parser": parser, "installed_parser": "Frozen" if parser == "frozen" else "Secondary",
                "reader_sha256": reader, "secondary_module_sha256": None if parser == "frozen" else "s" * 64,
                "grades": grades}

    G = {"t/1": {"raised": None, "sha256": "1" * 64}, "t/2": {"raised": "ViewError", "sha256": None}}

    def test_identical_grades_pass_and_an_unreadable_take_is_not_compared(self):
        rc, doc = self.run_compare(self.doc("frozen", self.G), self.doc("secondary", self.G))
        self.assertEqual((rc, doc["pass"], doc["compared"], doc["identical"]), (0, True, 1, 1))

    def test_a_changed_or_refused_grade_fails(self):
        for after in ({"raised": None, "sha256": "2" * 64}, {"raised": "VendorAdmissionRefused", "sha256": None}):
            rc, doc = self.run_compare(self.doc("frozen", self.G), self.doc("secondary", dict(self.G, **{"t/1": after})))
            self.assertEqual((rc, doc["pass"], doc["differ"]), (1, False, ["t/1"]))

    def test_a_take_missing_from_one_run_fails(self):
        rc, doc = self.run_compare(self.doc("frozen", self.G), self.doc("secondary", {"t/1": self.G["t/1"]}))
        self.assertEqual((rc, doc["pass"], doc["takes_not_in_both"]), (1, False, ["t/2"]))

    def test_two_runs_of_one_parser_or_an_edited_reader_file_are_refused(self):
        self.assertEqual(self.run_compare(self.doc("frozen", self.G), self.doc("frozen", self.G))[0], "refused")
        self.assertEqual(self.run_compare(self.doc("frozen", self.G),
                                          self.doc("secondary", self.G, reader="e" * 64))[0], "refused")


class SideBySide(unittest.TestCase):
    P = {"comparisons": [{"family": "f", "harness_a": "h", "model_a": "a", "harness_b": "h", "model_b": "b",
                          "task": "t", "at_alpha": True}],
         "holds": [{"arm": "A", "task": "t", "model": "a", "harness": "h", "holds": "no"},
                   {"arm": "B", "task": "t", "model": "b", "harness": "h", "holds": "yes"}],
         "across_tasks": [{"family": "f", "harness_a": "h", "model_a": "a", "harness_b": "h", "model_b": "b",
                           "lower": "+0.010", "upper": "+0.200"}]}
    HEAD = {"comparisons": "### Comparisons", "holds": "### Holds", "across_tasks": "### Across tasks"}

    def test_the_same_tables_give_rows_and_no_change(self):
        sections, changed = rgs.side_by_side(self.P, self.P, self.HEAD)
        self.assertEqual(changed, [])
        self.assertEqual(len(sections), 3)
        for s in sections:
            self.assertIn("| Row | Primary | Secondary | Changed |", s)
            self.assertNotIn("**yes**", s)
        self.assertIn("| yes | yes |", sections[0])
        self.assertTrue(sections[2].count("| yes | yes |") == 1)          # +0.010 to +0.200 excludes zero

    def test_a_flipped_decision_in_each_table_is_flagged(self):
        s = json.loads(json.dumps(self.P))
        s["comparisons"][0]["at_alpha"] = False
        s["holds"][0]["holds"] = "yes"
        s["across_tasks"][0]["lower"] = "-0.010"
        sections, changed = rgs.side_by_side(self.P, s, self.HEAD)
        self.assertEqual(sorted(c[0] for c in changed), ["across_tasks", "comparisons", "holds"])
        self.assertEqual([c for c in changed if c[0] == "holds"][0][2:], ("no", "yes"))
        self.assertEqual(sum(x.count("**yes**") for x in sections), 3)

    def test_a_row_in_one_analysis_only_is_flagged_absent(self):
        s = dict(self.P, holds=self.P["holds"][:1])
        _, changed = rgs.side_by_side(self.P, s, self.HEAD)
        self.assertEqual([(c[0], c[3]) for c in changed], [("holds", "absent")])

    def test_no_rows_prints_a_no_rows_line(self):
        empty = {"comparisons": "no takes", "holds": "no takes", "across_tasks": "no takes"}
        sections, changed = rgs.side_by_side(empty, empty, self.HEAD)
        self.assertEqual(changed, [])
        self.assertTrue(all("| (no rows) | | | |" in x for x in sections))


class TheDisclosure(unittest.TestCase):
    def test_the_plan_disclosure_items_are_written(self):
        text = "\n".join(rgs.DISCLOSURE)
        for words in ("s-3c4f8d", "s-0e780d", "OD200", "OD201", "native-reader acceptance records",
                      "checker digest"):
            self.assertIn(words, text)


if __name__ == "__main__":
    unittest.main()
