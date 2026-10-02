#!/usr/bin/env python3
"""Tests for evals/gap-study-costs-by-call/costs_by_call.py, the dated token correction (decision 0271).

Run:  python3 tests/test_gap_study_costs_by_call.py      (from the repo root; stdlib only)
      python3 tests/run_tests.py                          (discovered there as well)

What these bind:
- the fixture `tests/data/costs_by_call_duplicate_records.jsonl` holds one call written as three
  records (thinking, text, tool_use, each carrying the whole call's usage) and one call written as one;
  the pinned round 1 reader sums it as four calls' worth, and the corrected reader counts two;
- a call is keyed by the pair (message.id, requestId); two records of one key with different usage
  are refused rather than one picked; a record missing either half of the key is never merged;
- the row the correction was found on reproduces exactly from its committed transcript, both ways;
- the committed correction page is what the reader writes, and every published figure it prints is
  found in that round's own COSTS.md, so a planted change on either side fails the check.
"""

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "evals" / "gap-study-costs-by-call" / "costs_by_call.py"
FIXTURE = REPO / "tests" / "data" / "costs_by_call_duplicate_records.jsonl"
ROW = (REPO / "evals" / "gap-study-2" / "transcripts" / "number-fidelity" / "control" / "claude-opus-5" / "1"
       / "transcript.jsonl")
ORDER = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corrected():
    return load(SCRIPT, "gap_study_costs_by_call")


def pinned_round_1():
    return load(REPO / "evals" / "gap-study" / "costs.py", "pinned_gap_study_costs")


def four(r):
    return tuple(r[c] for c in ORDER)


class DuplicateRecordsFixture(unittest.TestCase):
    def test_the_pinned_reader_counts_the_three_block_call_three_times(self):
        got = pinned_round_1().read_one(FIXTURE)
        self.assertEqual(got["usage_records"], 4)
        self.assertEqual(four(got), (3 * 3 + 2, 3 * 40000 + 41200, 3 * 1200 + 300, 3 * 250 + 90))

    def test_each_call_is_counted_once(self):
        got = corrected().read_calls(FIXTURE)
        self.assertEqual((got["records"], got["calls"], got["partial_key"]), (4, 2, 0))
        self.assertEqual(four(got), (3 + 2, 40000 + 41200, 1200 + 300, 250 + 90))


class TheKey(unittest.TestCase):
    def setUp(self):
        self.m = corrected()
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(str(self.tmp))

    def records(self):
        return [json.loads(line) for line in FIXTURE.read_text().splitlines()]

    def write(self, recs):
        p = self.tmp / "t.jsonl"
        p.write_text("".join(json.dumps(r) + "\n" for r in recs))
        return p

    def test_two_records_of_one_call_with_different_usage_are_refused(self):
        recs = self.records()
        recs[2]["message"]["usage"] = dict(recs[2]["message"]["usage"], output_tokens=251)
        with self.assertRaises(self.m.Disagreement):
            self.m.read_calls(self.write(recs))

    def test_the_same_message_id_under_another_request_is_another_call(self):
        recs = self.records()
        recs[3]["requestId"] = "req_fixture_retry"
        got = self.m.read_calls(self.write(recs))
        self.assertEqual(got["calls"], 3)
        self.assertEqual(got["output_tokens"], 2 * 250 + 90)

    def test_a_record_missing_half_its_key_is_never_merged(self):
        for drop in ("requestId", "id"):
            recs = self.records()
            if drop == "id":
                del recs[2]["message"]["id"]
            else:
                del recs[2]["requestId"]
            got = self.m.read_calls(self.write(recs))
            self.assertEqual((got["calls"], got["partial_key"]), (3, 1), drop)
            self.assertEqual(got["output_tokens"], 2 * 250 + 90, drop)

    def test_records_without_usage_and_broken_lines_are_not_calls(self):
        p = self.write(self.records())
        p.write_text(p.read_text() + "{not json\n[1, 2]\n")
        got = self.m.read_calls(p)
        self.assertEqual((got["records"], got["calls"]), (4, 2))


class TheRowItWasFoundOn(unittest.TestCase):
    def test_round_2_number_fidelity_control_opus_take_1(self):
        pub = load(REPO / "evals" / "gap-study-2" / "costs.py", "pinned_gap_study_2_costs").read_one(ROW)
        self.assertEqual((pub["usage_records"],) + four(pub), (16, 32, 437281, 48901, 4494))
        got = corrected().read_calls(ROW)
        self.assertEqual((got["records"], got["calls"]) + four(got), (16, 10, 20, 286108, 26023, 2820))


class ThePage(unittest.TestCase):
    def setUp(self):
        self.m = corrected()

    def test_the_committed_page_is_what_the_reader_writes_and_binds_to_each_costs_md(self):
        self.assertEqual(self.m.problems(), [])

    def test_a_planted_change_on_the_page_fails(self):
        text = self.m.OUT.read_text()
        self.assertIn("| 286,108 |", text)
        self.assertNotEqual(self.m.problems(page=text.replace("| 286,108 |", "| 286,109 |", 1)), [])

    def test_a_published_figure_missing_from_costs_md_fails(self):
        got = self.m.collect()
        costs = {s: (REPO / "evals" / s / "COSTS.md").read_text() for s in self.m.STUDIES}
        self.assertEqual(self.m.binding_problems(got, costs), [])
        costs["gap-study-2"] = costs["gap-study-2"].replace("| 437,281 |", "| 437,282 |", 1)
        self.assertNotEqual(self.m.binding_problems(got, costs), [])

    def test_the_figures_docs_evals_quotes_are_the_readers(self):
        got = self.m.collect()
        costs = {s: (REPO / "evals" / s / "COSTS.md").read_text() for s in self.m.STUDIES}
        evals = (REPO / "docs" / "EVALS.md").read_text()
        self.assertIn(self.m.evals_sentence(got), evals)
        self.assertNotEqual(self.m.binding_problems(got, costs, evals.replace("195,353,721", "195,353,722")), [])

    def test_decision_0271_carries_the_figures_the_reader_derives(self):
        got = self.m.collect()
        text = self.m.DECISION.read_text()
        self.assertEqual(self.m.decision_problems(got, text), [])
        for figure in self.m.decision_figures(got):
            self.assertIn(figure, text)
            self.assertNotEqual(self.m.decision_problems(got, text.replace(figure, "x")), [], figure)

    def test_a_costs_md_row_the_page_does_not_carry_fails(self):
        got = self.m.collect()
        costs = {s: (REPO / "evals" / s / "COSTS.md").read_text() for s in self.m.STUDIES}
        self.assertEqual(self.m.row_count_problems(got, costs), [])
        for heading in ("## Per take", "## Pre-freeze walks", "## Per model"):
            text = costs["gap-study-3"]
            h = text.index(heading)
            i = text.index("\n|---", h)
            j = text.index("\n", i + 1)
            planted = dict(costs, **{"gap-study-3": text[:j + 1] + "| `planted` | row |\n" + text[j + 1:]})
            self.assertNotEqual(self.m.row_count_problems(got, planted), [], heading)

    def test_every_tracked_line_quoting_a_published_figure_is_cited(self):
        got = self.m.collect()
        hits = self.m.figure_hits(got)
        self.assertTrue(hits, "the sweep found nothing, so it measured nothing")
        self.assertEqual(self.m.uncited(hits), [])
        planted = hits + [("docs/EVALS.md", 9999, "100,147")]
        self.assertEqual(self.m.uncited(planted), [("docs/EVALS.md", 9999, "100,147")])

    def test_a_cited_line_that_moved_fails(self):
        got = self.m.collect()
        costs = {s: (REPO / "evals" / s / "COSTS.md").read_text() for s in self.m.STUDIES}
        path, line, needle, what = self.m.CITED[0]
        saved = self.m.CITED
        try:
            self.m.CITED = ((path, line + 1, needle, what),) + saved[1:]
            self.assertNotEqual(self.m.binding_problems(got, costs), [])
        finally:
            self.m.CITED = saved

    def test_every_round_and_every_table_is_covered(self):
        got = self.m.collect()
        self.assertEqual(sorted(got), sorted(self.m.STUDIES))
        for study, s in got.items():
            self.assertTrue(s["takes"], study)
            self.assertTrue(s["walks"], study)
            for r in s["takes"] + s["walks"]:
                self.assertEqual(r["call"]["partial_key"], 0, r["slot"])
                self.assertLessEqual(r["call"]["calls"], r["call"]["records"])
                self.assertEqual(r["pub"]["usage_records"], r["call"]["records"])


if __name__ == "__main__":
    unittest.main()
