#!/usr/bin/env python3
"""Tests for the step map (evals/step-map/build_map.py): the published map is a fresh build of the
facts and the judgment, the validator refuses bad judgment, the ranking follows the method, and
every extracted field is bound to a line that exists at the pin.

Run alone, from the repository root:  python3 evals/step-map/tests/test_build_map.py
Standard library only; writes only to temp dirs.
"""

import copy
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(LANE))
PIN = "a626cdc2"

spec = importlib.util.spec_from_file_location("stepmap_build", os.path.join(LANE, "build_map.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


def show(path):
    return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (PIN, path)], stdout=subprocess.PIPE,
                          check=True, universal_newlines=True).stdout


class Published(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maps, cls.ranked, cls.summary, cls.contracts = B.build()

    def test_map_and_md_equal_a_fresh_build(self):
        proc = subprocess.run([sys.executable, os.path.join(LANE, "build_map.py"), "--check"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_every_step_has_facts_and_judgment(self):
        steps = sum(len(m["steps"]) for m in self.maps.values())
        self.assertEqual(steps, 142)
        for m in self.maps.values():
            for st in m["steps"]:
                self.assertEqual(st["judgment"]["kind"], "judgment")
                self.assertIn("source", st["extracted"])

    def test_no_occurrence_is_claimed(self):
        """Occurrence is a measured failure rate; nothing here was measured, so none is given."""
        self.assertTrue(self.ranked)
        self.assertEqual([r["id"] for r in self.ranked if r["occurrence"] is not None], [])

    def test_ranking_is_severity_then_detection_then_earliest(self):
        for k in range(len(B.GROUPS)):
            group = [r for r in self.ranked if r["group"] == k]
            self.assertTrue(group, "stage group %d has no unsaid decision" % k)
            keys = [(-r["severity"], -r["detection"]) for r in group]
            self.assertEqual(keys, sorted(keys), B.GROUPS[k][0])
            self.assertEqual([r["rank_in_stage"] for r in group], list(range(1, len(group) + 1)))

    def test_extracted_sources_point_at_real_lines(self):
        """Every `path:line` an extracted field cites exists at the pin and is not blank."""
        seen = 0
        cache = {}
        for m in self.maps.values():
            for st in m["steps"]:
                x = st["extracted"]
                refs = [c["source"] for c in x["calls"]] + \
                       [e["source"] for e in x["exit_branches"]] + \
                       [a["source"] for a in x["file_actions"]] + \
                       [f["source"] for f in x["prose_flags"]]
                for ref in refs:
                    path, line = ref.rsplit(":", 1)
                    if path not in cache:
                        cache[path] = show(path).split("\n")
                    self.assertTrue(cache[path][int(line) - 1].strip(), ref)
                    seen += 1
        self.assertGreater(seen, 150)

    def test_defects_cited_by_judgment_exist(self):
        ids = B.defect_ids()
        self.assertGreaterEqual(len(ids), 20)
        cited = {d for r in self.ranked for d in r.get("defects", [])}
        self.assertTrue(cited)
        self.assertEqual(cited - ids, set())

    def test_review_page_names_each_stage_top_three(self):
        """REVIEW.md presents, for each stage group, the map's top three, in rank order."""
        path = os.path.join(LANE, "REVIEW.md")
        self.assertTrue(os.path.exists(path), "REVIEW.md missing")
        text = open(path, encoding="utf-8").read()
        found = re.findall(r"<!-- ([A-Za-z0-9-]+) -->", text)
        expected = []
        for k in range(len(B.GROUPS)):
            expected += [r["id"] for r in self.ranked if r["group"] == k][:3]
        self.assertEqual(found, expected)

    def test_review_page_scores_equal_the_map(self):
        """Each item's "Harm X, slip-through Y" is the ranked decision's own severity and detection."""
        text = open(os.path.join(LANE, "REVIEW.md"), encoding="utf-8").read()
        parts = re.split(r"<!-- ([A-Za-z0-9-]+) -->", text)[1:]
        by_id = {}
        for r in self.ranked:
            by_id.setdefault(r["id"], r)
        self.assertEqual(len(parts), 30)
        for uid, body in zip(parts[::2], parts[1::2]):
            scores = re.findall(r"Harm (\d+), slip-through (\d+)", body.split("\n## ")[0])
            self.assertEqual(len(scores), 1, uid)
            self.assertEqual((int(scores[0][0]), int(scores[0][1])),
                             (by_id[uid]["severity"], by_id[uid]["detection"]), uid)


class Validator(unittest.TestCase):
    """Each rule the validator enforces refuses a judgment that breaks it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="stepmap-judgment-")
        shutil.copytree(B.JUDGMENT, os.path.join(self.tmp, "judgment"))
        self.saved = B.JUDGMENT
        B.JUDGMENT = os.path.join(self.tmp, "judgment")

    def tearDown(self):
        B.JUDGMENT = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def edit(self, name, fn):
        path = os.path.join(B.JUDGMENT, name)
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        fn(data)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)

    def refuses(self, needle):
        with self.assertRaises(B.Invalid) as ctx:
            B.build()
        self.assertIn(needle, str(ctx.exception))

    def test_baseline_builds(self):
        B.build()

    def test_missing_step(self):
        self.edit("00_initialize_project.json", lambda d: d["steps"].pop("17"))
        self.refuses("missing for steps ['17']")

    def test_unknown_control(self):
        self.edit("00_initialize_project.json",
                  lambda d: d["steps"]["1"]["controls"].append("vibes"))
        self.refuses("19 kinds")

    def test_r5_without_unsaid(self):
        def fn(d):
            d["steps"]["1"].update(rung_now="R5", question=1, rung_target="R4")
        self.edit("00_initialize_project.json", fn)
        self.refuses("unsaid decision is R5 today")

    def test_unsaid_below_r5(self):
        def fn(d):
            d["steps"]["15"].update(rung_now="R4", question=4, rung_target="R3")
        self.edit("00_initialize_project.json", fn)
        self.refuses("unsaid decision is R5 today")

    def test_question_must_place_the_target(self):
        self.edit("00_initialize_project.json", lambda d: d["steps"]["1"].update(question=2))
        self.refuses("placed by question 5")

    def test_occurrence_needs_a_measurement(self):
        self.edit("00_initialize_project.json",
                  lambda d: d["steps"]["15"]["silent"][0].update(occurrence=3))
        self.refuses("no measurement cited")

    def test_score_range(self):
        self.edit("00_initialize_project.json",
                  lambda d: d["steps"]["15"]["silent"][0].update(severity=11))
        self.refuses("integer 1-10")

    def test_unknown_defect(self):
        self.edit("00_initialize_project.json",
                  lambda d: d["steps"]["2"]["silent"][0].update(defects=["D99"]))
        self.refuses("D99")

    def test_kind_is_closed(self):
        self.edit("00_initialize_project.json",
                  lambda d: d["steps"]["15"]["silent"][0].update(kind="maybe"))
        self.refuses("unsaid or unchecked")

    def test_unchecked_only_step_is_r4(self):
        def fn(d):
            row = d["steps"]["14"]                    # its only decision, S00-skip, is unique
            row["silent"][0]["kind"] = "unchecked"
            row.update(rung_now="R3", rung_target="R0", question=2)
        self.edit("00_initialize_project.json", fn)
        self.refuses("is R4 (a written rule with no audit)")

    def test_same_id_different_content(self):
        def fn(d):
            d["steps"]["6"]["silent"][0]["severity"] = 6
        self.edit("01_prepare_samplesheets.json", fn)
        self.refuses("defined twice")

    def test_prose_cites_only_defined_ids(self):
        self.edit("00_initialize_project.json",
                  lambda d: d["steps"]["1"].update(rung_why="Fixed text (D-handoff)."))
        self.refuses("prose cites D-handoff")

    def test_record_ids_in_prose_are_not_decision_ids(self):
        self.edit("00_initialize_project.json",
                  lambda d: d["steps"]["1"].update(rung_why="Fixed text (R-092, D-24)."))
        B.build()

    def test_wrong_pin(self):
        self.edit("00_initialize_project.json", lambda d: d.update(sha="0" * 40))
        self.refuses("pinned to")


if __name__ == "__main__":
    unittest.main(verbosity=2)
