#!/usr/bin/env python3
"""CP7: the pre-registration draft says what round 2 is, and each statement is bound to the data it describes.

    python3 evals/gap-study-2/test_harness.py ThePreRegistrationIsComplete CaseSuitesOnRoundTwoWalksLive

ThePreRegistrationIsComplete binds the draft's round-2 content: the 18 predictions, each re-derived here from round 1's
results files and the round-1 regrade records under the pinned rule, none blind; the system under test's difference
from round 1, its file list held to git; one entry per fix naming paths that exist; the instruments-differ comparison
and the replicate note; the study's own names among the leak words; and the limitations this round adds.

CaseSuitesOnRoundTwoWalksLive runs the walk case-suite checks over this study's own walks and cases/round-2/. It reads
the walks, which are live records, so it is a `...Live` class and TheSuiteNeverReadsLiveState leaves it out by name.

Round 1's results are read as data through study.ROUND1. No model, no network. stdlib only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
for p in (str(HERE / "graders"), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import prereg  # noqa: E402
import study  # noqa: E402
import test_harness as th  # noqa: E402

MODELS = ("claude-haiku-4-5-20251001", "claude-sonnet-5", "claude-opus-5")


def derived_predictions(pre: dict) -> dict[tuple[str, str], tuple[str, list[str]]]:
    """Each cell's prediction under the pinned rule, from round 1's files, with the paths it was read from."""
    regrades = {f["fix"]: f for f in pre["fixes"]}
    by_task = {}
    for f in regrades.values():
        rec = f.get("regrade_record")
        pinned = f.get("pinned_data") or ""
        for task in ("scope-read", "plan-gate"):
            if rec and f".tasks[{task}]." in pinned:
                by_task[task] = rec
    out = {}
    for t in pre["tasks"]:
        tid = t["id"]
        results = json.loads((study.ROUND1 / "results" / f"{tid}.json").read_text())
        regrade = json.loads((REPO / by_task[tid]).read_text()) if tid in by_task else None
        for model in MODELS:
            holds = True
            for half in ("positive", "control"):
                correct = t[half]["correct_behaviour_label"]
                if regrade:
                    got = [x["round_2_label"] for x in regrade["takes"] if x["model"] == model and x["half"] == half]
                else:
                    got = [x["label"] for x in results["cells"][model][half]["labels"]]
                if len(got) != 3 or any(label != correct for label in got):
                    holds = False
            paths = [f"{study.ROUND1_REL}/results/{tid}.json"] + ([by_task[tid]] if tid in by_task else [])
            out[(tid, model)] = ("holds" if holds else "does not hold", paths)
    return out


class ThePreRegistrationIsComplete(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pre = prereg.load()

    def test_eighteen_predictions_none_blind_each_in_the_fixed_form(self):
        preds = self.pre["predictions"]
        self.assertEqual(len(preds), 18, "round 2 predicts every task for every model, once")
        cells = {(p["task"], p["model"]) for p in preds}
        self.assertEqual(cells, {(t["id"], m) for t in self.pre["tasks"] for m in MODELS})
        for p in preds:
            self.assertNotEqual(p["basis"], "blind", f"{p['task']} {p['model']}: a round-2 prediction is never blind")
            self.assertEqual(p["statement"],
                             f"predicted {p['predicted']} · basis: informed by {' and '.join(p['informed_by'])}")

    def test_every_prediction_re_derives_from_round_ones_files(self):
        derived = derived_predictions(self.pre)
        wrong = [f"{p['task']} {p['model']}: the draft predicts {p['predicted']}, the rule gives "
                 f"{derived[(p['task'], p['model'])][0]}"
                 for p in self.pre["predictions"]
                 if (p["predicted"], p["informed_by"]) != derived[(p["task"], p["model"])]]
        self.assertFalse(wrong, "a prediction is not what round 1's files give under the pinned rule:\n" + "\n".join(wrong))

    def test_the_system_under_test_difference_is_the_git_difference(self):
        dfr = self.pre["system_under_test"]["differs_from_round_1"]
        r = subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", dfr["round_1_checked_commit"],
                            dfr["round_2_kickoff_base"], "--", "gars/"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"the two commits are not in this history: {r.stderr.strip()}")
        self.assertEqual(dfr["files"], r.stdout.split(), "the draft's file list is not what git reports")
        for commit, key in ((dfr["round_1_checked_commit"], "round_1_gars_tree_sha"),
                            (dfr["round_2_kickoff_base"], "gars_tree_sha")):
            tree = subprocess.run(["git", "-C", str(REPO), "rev-parse", f"{commit}:gars"], capture_output=True,
                                  text=True).stdout.strip()
            self.assertEqual(tree, self.pre["system_under_test"][key], f"{commit}'s gars tree is not the draft's {key}")

    def test_every_fix_names_paths_that_exist(self):
        self.assertEqual(len(self.pre["fixes"]), 5)
        missing = []
        for f in self.pre["fixes"]:
            for key in ("regrade_record", "case_suite", "walk"):
                if f.get(key) and not (REPO / f[key]).exists():
                    missing.append(f"{f['fix']}: {key} {f[key]}")
        self.assertFalse(missing, "a fix names a record that does not exist:\n" + "\n".join(missing))

    def test_the_comparison_and_the_replicate_note_are_stated(self):
        cmp = self.pre["analysis_plan"]["round_1_beside_round_2"]
        self.assertEqual(cmp["tasks"], ["scope-read", "plan-gate"])
        self.assertEqual(cmp["heading"], "The instruments differ: round 1's counts are printed beside round 2's, not pooled")
        note = self.pre["replicate_note"]
        for task in ("template-adherence", "precondition-refusal", "number-fidelity", "confounded-design"):
            self.assertIn(task, note)
        self.assertIn("never pooled", note)

    def test_the_leak_words_name_this_round(self):
        for word in ("gap-study-2", "gars-eval-v3", "round 2"):
            self.assertIn(word, self.pre["leak_words"])

    def test_the_limitations_this_round_adds_are_there(self):
        text = "\n".join(self.pre["limitations_lines"])
        for phrase in ("cannot see a credential held outside that environment", "fitted on round 1's texts",
                       "fitted on round 1's six correct control replies", "inherited the operator pane's effort level",
                       "n = 3 graded takes", "a Status: APPROVED line an agent writes by hand"):
            self.assertIn(phrase, text)


class CaseSuitesOnRoundTwoWalksLive(th.CaseSuites):
    """The walk case-suite checks over this study's own walks and the suites built from them alone."""

    CASES = HERE / "cases" / "round-2"
    WALKS = HERE / "walks"

    def setUp(self):
        super().setUp()
        import build_cases
        saved = build_cases.CARRIED_SOURCES
        build_cases.CARRIED_SOURCES = {}
        self.addCleanup(setattr, build_cases, "CARRIED_SOURCES", saved)


if __name__ == "__main__":
    unittest.main()
