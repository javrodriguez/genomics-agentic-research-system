#!/usr/bin/env python3
"""Tests and the CI mutation witness for evals/gap-study-intervals/intervals.py.

Run:  python3 evals/gap-study-intervals/test_intervals.py      (from the repo root; stdlib only)

What these bind:
- the exact interval arithmetic, against closed forms and hand-checkable values;
- the graded count is the number of labels in a results file, never its `n` field;
- the committed page and data are exactly what the script derives from the committed results;
- the mutation witness: a planted change to a label, a count, an interval or an input file makes
  `--check` fail, and a consistent forgery of both results and page is caught by the binding to
  each round's done commit;
- the page carries no percentage and no sentence comparing models.
"""

import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SCRIPT = HERE / "intervals.py"


def load():
    spec = importlib.util.spec_from_file_location("gap_study_intervals", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Arithmetic(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def test_known_intervals_at_three_and_one_take(self):
        cp = self.m.clopper_pearson
        f = self.m.fmt
        cases = {(0, 3): ("0.000", "0.708"), (1, 3): ("0.008", "0.906"),
                 (2, 3): ("0.094", "0.992"), (3, 3): ("0.292", "1.000"),
                 (0, 1): ("0.000", "0.975"), (1, 1): ("0.025", "1.000")}
        for (x, n), want in cases.items():
            with self.subTest(x=x, n=n):
                lo, hi = cp(x, n)
                self.assertEqual((f(lo), f(hi)), want)

    def test_bounds_round_outward_against_the_closed_forms(self):
        """x = n and x = 0 have closed forms; the published bound must contain the exact one."""
        cp = self.m.clopper_pearson
        for n in range(1, 51):
            exact_lower = 0.025 ** (1.0 / n)          # x = n
            exact_upper = 1.0 - 0.025 ** (1.0 / n)    # x = 0
            lo, _ = cp(n, n)
            _, hi = cp(0, n)
            with self.subTest(n=n):
                self.assertLessEqual(float(lo), exact_lower + 1e-12)
                self.assertGreater(float(lo), exact_lower - 0.001)
                self.assertGreaterEqual(float(hi), exact_upper - 1e-12)
                self.assertLess(float(hi), exact_upper + 0.001)

    def test_interval_is_on_the_three_decimal_grid(self):
        for n in (1, 3, 7):
            for x in range(n + 1):
                for bound in self.m.clopper_pearson(x, n):
                    self.assertEqual((bound * 1000).denominator, 1)

    def test_fisher_smallest_attainable_p(self):
        mp = self.m.min_fisher_p
        self.assertEqual(mp(3, 3), Fraction(1, 10))
        self.assertEqual(mp(1, 3), Fraction(1, 4))
        self.assertEqual(mp(1, 1), Fraction(1))

    def test_fisher_two_sided_matches_an_independent_float_version(self):
        def float_fisher(x1, n1, x2, n2):
            k, total = x1 + x2, n1 + n2
            probs = {i: math.comb(n1, i) * math.comb(n2, k - i) / math.comb(total, k)
                     for i in range(max(0, k - n2), min(k, n1) + 1)}
            obs = probs[x1]
            return sum(p for p in probs.values() if p <= obs * (1 + 1e-9))
        for n1, n2 in ((3, 3), (1, 3), (5, 7), (10, 10)):
            for x1 in range(n1 + 1):
                for x2 in range(n2 + 1):
                    with self.subTest(x1=x1, n1=n1, x2=x2, n2=n2):
                        self.assertAlmostEqual(float(self.m.fisher_two_sided(x1, n1, x2, n2)),
                                               float_fisher(x1, n1, x2, n2), places=9)

    def test_power_matches_an_independent_float_version(self):
        def float_power(n, a):
            p1, p2 = (50 - a) / 100, (50 + a) / 100
            total = 0.0
            for x1 in range(n + 1):
                for x2 in range(n + 1):
                    k = x1 + x2
                    probs = {i: math.comb(n, i) * math.comb(n, k - i)
                             for i in range(max(0, k - n), min(k, n) + 1)}
                    obs = probs[x1]
                    p = sum(v for v in probs.values() if v <= obs) / math.comb(2 * n, k)
                    if p <= 0.05 + 1e-12:
                        total += (math.comb(n, x1) * p1 ** x1 * (1 - p1) ** (n - x1) *
                                  math.comb(n, x2) * p2 ** x2 * (1 - p2) ** (n - x2))
            return total
        for n, a in ((3, 50), (10, 30), (20, 20), (30, 15)):
            with self.subTest(n=n, a=a):
                self.assertAlmostEqual(float(self.m.power_centred(n, a)), float_power(n, a), places=9)

    def test_three_takes_can_detect_no_difference(self):
        self.assertIsNone(self.m.smallest_detectable(3))
        found = self.m.smallest_detectable(50)
        self.assertIsNotNone(found)
        self.assertGreaterEqual(self.m.power_centred(50, found), Fraction(4, 5))
        self.assertLess(self.m.power_centred(50, found - 1), Fraction(4, 5))

    def test_clopper_pearson_never_undercovers_and_wilson_does_at_three(self):
        cov = self.m.coverage_minimum
        cp_min, _ = cov(3, "clopper-pearson")
        wilson_min, _ = cov(3, "wilson")
        self.assertGreaterEqual(cp_min, Fraction(95, 100))
        self.assertLess(wilson_min, Fraction(95, 100))


class RealResults(unittest.TestCase):
    """The committed results files of the three rounds, read as they are."""

    def setUp(self):
        self.m = load()
        self.data = self.m.derive(REPO)

    def half(self, rnd, task, model, half):
        for r in self.data["rounds"]:
            if r["round"] == rnd:
                for h in r["halves"]:
                    if (h["task"], h["model"], h["half"]) == (task, model, half):
                        return h
        self.fail("no such half")

    def test_the_incomplete_round_2_cell_counts_its_labels_not_n(self):
        h = self.half("2", "template-adherence", "claude-sonnet-5", "control")
        self.assertEqual((h["graded"], h["correct"]), (1, 0))
        self.assertEqual((h["lower"], h["upper"]), ("0.000", "0.975"))

    def test_every_half_is_seen_and_the_zero_rule_holds(self):
        seen = sum(len(r["halves"]) for r in self.data["rounds"])
        graded = sum(1 for r in self.data["rounds"] for h in r["halves"] if h["graded"])
        self.assertEqual((seen, graded), (114, 90))

    def test_correct_count_agrees_with_k_wherever_the_cell_ran(self):
        """A consistency reading only: the count comes from the labels, and matches k where RAN."""
        for rnd, folder, _ in self.m.ROUNDS:
            for path in sorted((REPO / folder / "results").glob("*.json")):
                cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
                for model, halves in cells.items():
                    for half, cell in halves.items():
                        if cell.get("state") == "RAN":
                            got = self.half(rnd, path.stem, model, half)
                            self.assertEqual(got["correct"], cell["k"])
                            self.assertEqual(got["graded"], len(cell["labels"]))

    def test_done_commits_are_the_ones_ci_pins(self):
        ci = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        for _, folder, commit in self.m.ROUNDS:
            job = folder.split("/")[-1]
            block = re.search(r"^  %s:\n(.*?)(?=^  [a-z0-9-]+:\n|\Z)" % re.escape(job), ci, re.M | re.S)
            self.assertIsNotNone(block, job)
            self.assertIn("ref: " + commit, block.group(1))

    def test_the_committed_page_and_data_are_what_the_script_derives(self):
        code, lines = self.m.check(REPO)
        self.assertEqual(code, 0, "\n".join(lines))


class Witness(unittest.TestCase):
    """The CI mutation witness: each planted change must make --check fail."""

    def setUp(self):
        self.m = load()
        self.tmp = Path(tempfile.mkdtemp(prefix="gap-study-intervals-"))
        self.root = self.tmp / "repo"
        for _, folder, _ in self.m.ROUNDS:
            shutil.copytree(str(REPO / folder / "results"), str(self.root / folder / "results"))
        out = self.root / "evals/gap-study-intervals"
        out.mkdir(parents=True)
        for name in ("INTERVALS.md", "intervals.json"):
            shutil.copy2(str(HERE / name), str(out / name))
        self.original = {p: p.read_bytes() for p in self.root.rglob("*.json")}

    def tearDown(self):
        shutil.rmtree(str(self.tmp))

    def check(self):
        return self.m.check(self.root, verify_history=False)

    def edit(self, rel, old, new):
        path = self.root / rel
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1, "the plant must apply exactly once")
        path.write_text(text.replace(old, new), encoding="utf-8")

    def test_positive_control_the_unplanted_copy_passes(self):
        code, lines = self.check()
        self.assertEqual(code, 0, "\n".join(lines))

    def test_a_flipped_label_fails(self):
        path = self.root / "evals/gap-study-2/results/scope-read.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        label = data["cells"]["claude-opus-5"]["control"]["labels"][0]
        self.assertEqual(label["verdict"], "incorrect")
        label["verdict"] = "correct"
        path.write_text(json.dumps(data), encoding="utf-8")
        code, lines = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any("scope-read.json" in ln for ln in lines), lines)

    def test_a_planted_interval_digit_in_the_page_fails(self):
        self.edit("evals/gap-study-intervals/INTERVALS.md", "0 of 1 | 0.000 to 0.975", "0 of 1 | 0.000 to 0.976")
        self.assertEqual(self.check()[0], 1)

    def test_a_planted_count_in_the_data_fails(self):
        path = self.root / "evals/gap-study-intervals/intervals.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rounds"][0]["halves"][0]["correct"] += 1
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        self.assertEqual(self.check()[0], 1)

    def test_the_n_field_is_never_read_but_its_bytes_are_bound(self):
        rel = "evals/gap-study-2/results/template-adherence.json"
        before = self.m.derive(self.root)
        path = self.root / rel
        data = json.loads(path.read_text(encoding="utf-8"))
        data["cells"]["claude-sonnet-5"]["control"]["n"] = 1
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        after = self.m.derive(self.root)
        self.assertEqual(before["rounds"], after["rounds"])
        self.assertEqual(self.check()[0], 1)

    def test_the_k_field_is_never_read(self):
        rel = "evals/gap-study-2/results/template-adherence.json"
        before = self.m.derive(self.root)
        path = self.root / rel
        data = json.loads(path.read_text(encoding="utf-8"))
        data["cells"]["claude-sonnet-5"]["control"]["k"] = 3
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.assertEqual(before["rounds"], self.m.derive(self.root)["rounds"])

    def test_an_unknown_verdict_stops_the_script(self):
        path = self.root / "evals/gap-study-3/results/scope-read.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["cells"]["claude-opus-5"]["positive"]["labels"][0]["verdict"] = "partly"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.m.derive(self.root)
        self.assertEqual(self.check()[0], 1)

    def test_no_graded_half_fails_even_with_a_regenerated_page(self):
        for _, folder, _ in self.m.ROUNDS:
            shutil.rmtree(str(self.root / folder / "results"))
            (self.root / folder / "results").mkdir()
        self.m.write(self.root)
        code, lines = self.check()
        self.assertEqual(code, 1, lines)

    def test_a_removed_file_with_a_regenerated_page_is_caught_by_the_listing(self):
        original = self.original
        (self.root / "evals/gap-study-3/results/scope-read.json").unlink()
        self.m.write(self.root)
        self.assertEqual(self.check()[0], 0)

        def listing(root, commit, folder):
            return sorted(p.name for p in original if p.parent == root / folder / "results")
        code, lines = self.m.check(self.root, verify_history=True,
                                   blob=lambda root, commit, rel: original[root / rel],
                                   listing=listing)
        self.assertEqual(code, 1, lines)

    def test_a_removed_input_file_fails(self):
        (self.root / "evals/gap-study-3/results/scope-read.json").unlink()
        self.assertEqual(self.check()[0], 1)

    def test_an_empty_input_set_fails(self):
        for _, folder, _ in self.m.ROUNDS:
            shutil.rmtree(str(self.root / folder / "results"))
            (self.root / folder / "results").mkdir()
        self.assertEqual(self.check()[0], 1)

    def test_a_consistent_forgery_is_caught_by_the_done_commit_binding(self):
        """Results and page rewritten together pass the re-derivation; the blob binding refuses."""
        path = self.root / "evals/gap-study-3/results/scope-read.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["cells"]["claude-haiku-4-5-20251001"]["control"]["labels"][0]["verdict"] = "correct"
        path.write_text(json.dumps(data), encoding="utf-8")
        self.m.write(self.root)
        self.assertEqual(self.check()[0], 0)
        original = self.original

        def blob(root, commit, rel):
            return original[root / rel]
        code, lines = self.m.check(self.root, verify_history=True, blob=blob,
                                   listing=lambda root, commit, folder: sorted(
                                       p.name for p in original if p.parent == root / folder / "results"))
        self.assertEqual(code, 1)
        self.assertTrue(any("scope-read.json" in ln for ln in lines), lines)

    def test_a_consistent_forgery_fails_against_real_git(self):
        """No injected reader: the done commit is a real commit, the forgery lives only in the tree."""
        git = ["git", "-C", str(self.root), "-c", "user.name=witness",
               "-c", "user.email=witness@users.noreply.github.com",
               "-c", "maintenance.auto=false", "-c", "gc.auto=0"]
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "done"], check=True)
        head = subprocess.run(git + ["rev-parse", "HEAD"], check=True,
                              stdout=subprocess.PIPE).stdout.decode().strip()
        saved = self.m.ROUNDS
        self.m.ROUNDS = tuple((rnd, folder, head) for rnd, folder, _ in saved)
        try:
            self.m.write(self.root)      # the page names its done commits, here the witness commit
            code, lines = self.m.check(self.root)
            self.assertEqual(code, 0, lines)
            path = self.root / "evals/gap-study-3/results/scope-read.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["cells"]["claude-haiku-4-5-20251001"]["control"]["labels"][0]["verdict"] = "correct"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.m.write(self.root)
            self.assertEqual(self.check()[0], 0)
            code, lines = self.m.check(self.root)
            self.assertEqual(code, 1, lines)
            self.assertTrue(any("scope-read.json" in ln and "done commit" in ln for ln in lines), lines)
        finally:
            self.m.ROUNDS = saved

    def test_history_binding_refuses_outside_git(self):
        code, _ = self.m.check(self.root, verify_history=True)
        self.assertEqual(code, 2)


class PublishedWords(unittest.TestCase):
    """No rate, and no sentence that sets one model against another (Gate 3 is the owner's)."""

    COMPARATIVE = re.compile(r"\b(than|better|worse|beats?|outperform\w*|superior|inferior|"
                             r"stronger|weaker|best|worst|significant\w*)\b", re.I)

    def texts(self):
        page = (HERE / "INTERVALS.md").read_text(encoding="utf-8")
        evals = (REPO / "docs/EVALS.md").read_text(encoding="utf-8")
        para = [block for block in evals.split("\n\n") if "gap-study-intervals" in block]
        return page, para

    def test_no_percent_sign(self):
        page, para = self.texts()
        for text in [page] + para:
            self.assertEqual(re.findall(r"\d+(?:\.\d+)?\s*%", text), [])

    def test_no_comparative_sentence(self):
        page, para = self.texts()
        for text in [page] + para:
            self.assertEqual(self.COMPARATIVE.findall(text), [])

    def test_evals_links_the_page_outside_every_generated_block(self):
        evals = (REPO / "docs/EVALS.md").read_text(encoding="utf-8")
        link = "(../evals/gap-study-intervals/INTERVALS.md)"
        self.assertEqual(evals.count(link), 1)
        at = evals.index(link)
        opened = [m.start() for m in re.finditer(r"<!-- [a-z0-9-]+:summary -->", evals)]
        closed = [m.start() for m in re.finditer(r"<!-- /[a-z0-9-]+(?::summary)? -->", evals)]
        self.assertTrue(opened and closed, "no generated markers found; this check would be vacuous")
        self.assertLess(at, min(opened + closed), "the link must sit before every generated block")
        self.assertTrue((REPO / "evals/gap-study-intervals/INTERVALS.md").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
