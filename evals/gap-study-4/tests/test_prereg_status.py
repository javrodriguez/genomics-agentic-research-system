#!/usr/bin/env python3
"""`prereg.py --status` reports round 4's design (Gap Study round 4, lane w7a, W6D-R1-1).

Round 3's status printed the design's model list and a (task, half, model, take)
count. Round 4's design is keyed by arm: `models` maps each arm to its models and
the planned rows carry arm, model, task, half, wording, repeat and agent. So the
status names the arms as arms, lists each arm's models, and counts the planned
rows themselves, never round 3's shape or the draft's own `counts` field.

The committed draft and synthetic designs only; no model, network or take.
--mutant NAME arms one altered prereg in setUpModule. --witnesses runs every
registered mutant in its own process and requires the bound method to fail by
an AssertionError carrying its clause token (rule B; collateral is listed, not
credited).
"""
from __future__ import annotations

import collections
import contextlib
import copy
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import prereg  # noqa: E402

SELECTED = None
PATCHES = []
REAL_LOAD = prereg.load


def committed():
    return copy.deepcopy(REAL_LOAD())


def thinned():
    """A synthetic design: the committed draft with arm O's last seven rows removed and its counts field left stale,
    so a status that reads `counts` or a per-model formula prints a number the rows do not have."""
    d = committed()
    o_rows = [i for i, r in enumerate(d["rows"]) if r["arm"] == "O"][-7:]
    d["rows"] = [r for i, r in enumerate(d["rows"]) if i not in set(o_rows)]
    return d


def status(design):
    out = io.StringIO()
    with mock.patch.object(prereg, "load", lambda: design), \
         mock.patch.object(sys, "argv", ["prereg.py", "--status"]), contextlib.redirect_stdout(out):
        code = prereg.main()
    return code, out.getvalue()


def mutants():
    """(clause, prereg attribute, replacement): each restores one piece of round 3's status. The row mutants
    return real rows, as many as the stale source says, so the status prints instead of raising."""
    return {
        # the arms printed under the label "models", as round 3's status did
        "models-label": ("S1.arms", "ARMS_LABEL", "models"),
        # the planned count read from the draft's own counts field instead of the rows
        "counts-field": ("S2.rows", "planned_rows", lambda pre: (pre["rows"] * 2)[:pre["counts"]["tries"]]),
        # round 3's (task, half, model, take) count
        "round3-count": ("S2.rows", "planned_rows", lambda pre: (pre["rows"] * 2)[:(
            len(pre["tasks"]) * 2 * len(pre["models"]) * int(pre["n"]))]),
        # the model list read as the design's top-level keys, which in round 4 are the arms
        "arm-keys": ("S3.models", "models", lambda: list(prereg.load()["models"])),
    }


def setUpModule():
    if SELECTED is not None:
        _, attr, value = mutants()[SELECTED]
        PATCHES.append(mock.patch.object(prereg, attr, value))
    for p in PATCHES:
        p.start()


def tearDownModule():
    while PATCHES:
        PATCHES.pop().stop()


class StatusIsRound4(unittest.TestCase):
    def test_arms_are_named_as_arms(self):
        d = committed()
        code, text = status(d)
        lines = text.splitlines()
        self.assertEqual(code, 0, "S1.arms")
        planned = [a for a in d["arms"] if a in d["models"]]
        self.assertEqual(planned, ["A", "O", "G"], "S1.arms")
        self.assertIn(f"arms     : {len(planned)} planned ({', '.join(planned)}); optional: C", lines, "S1.arms")
        self.assertFalse(any(line.startswith("models") for line in lines), "S1.arms")
        for arm in planned:
            harness = {r["agent"]["harness"] for r in d["rows"] if r["arm"] == arm}
            self.assertEqual(len(harness), 1, "S1.arms")
            want = (f"  arm {arm}  {harness.pop()}: {len(d['models'][arm])} models, "
                    f"{sum(r['arm'] == arm for r in d['rows'])} rows: {', '.join(d['models'][arm])}")
            self.assertIn(want, lines, "S1.arms")
        self.assertIn("  arm C  optional: claude-fable-5-1, 0 rows (optional (D2 B))", lines, "S1.arms")

    def test_rows_are_counted_from_the_rows(self):
        for name, d in (("committed", committed()), ("thinned", thinned())):
            with self.subTest(design=name):
                code, text = status(d)
                rows = d["rows"]
                self.assertEqual(code, 0, "S2.rows")
                self.assertIn(f"rows     : {len(rows)} planned rows (n = {d['n']} tries per half), "
                              f"{len({r['half_cell'] for r in rows})} half-cells", text.splitlines(), "S2.rows")
                by_arm = collections.Counter(r["arm"] for r in rows)
                for arm in ("A", "O", "G"):
                    self.assertIn(f", {by_arm[arm]} rows: ", text, "S2.rows")
                self.assertNotIn("planned takes", text, "S2.rows")
        self.assertIn("rows     : 1260 planned rows (n = 10 tries per half), 126 half-cells", status(committed())[1],
                      "S2.rows")
        self.assertIn("rows     : 1253 planned rows", status(thinned())[1], "S2.rows")

    def test_models_are_the_models(self):
        d = committed()
        with mock.patch.object(prereg, "load", lambda: d):
            got = prereg.models()
            running = prereg.running_models()
        flat = [m for arm in d["arms"] if arm in d["models"] for m in d["models"][arm]]
        self.assertEqual(got, flat, "S3.models")
        self.assertEqual(len(got), 7, "S3.models")
        self.assertFalse(set(got) & set(d["arms"]), "S3.models")
        self.assertEqual(running, flat, "S3.models")


BOUND = {"S1.arms": "test_arms_are_named_as_arms", "S2.rows": "test_rows_are_counted_from_the_rows",
         "S3.models": "test_models_are_the_models"}
WITNESSES = {name: ("StatusIsRound4." + BOUND[clause], clause) for name, (clause, _, _) in mutants().items()}


def run_witnesses():
    import re
    import subprocess
    red = 0
    for name, (method, clause) in sorted(WITNESSES.items()):
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name],
                             capture_output=True, text=True, timeout=300)
        record = re.findall(r"^test_prereg_status outcomes: (\{.*\})$", got.stdout, re.M)
        outcome = json.loads(record[-1]) if record else None
        blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", got.stderr, re.M | re.S)
        attributed = any(f"{cls}.{test}" == method and "AssertionError" in body and
                         re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w:.-])", body)
                         for test, cls, body in blocks)
        clean = bool(outcome) and method in outcome["failures"] and method not in outcome["errors"] \
            and method not in outcome["skipped"]
        passed = attributed and clean and got.returncode != 0
        other = {k: sorted(t for t in outcome[k] if t != method) for k in outcome} if outcome else {}
        note = "collateral: " + (", ".join(f"{k} {v}" for k, v in other.items() if v) or "none")
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}; {note}", flush=True)
        if not passed:
            print(got.stdout + got.stderr, flush=True)
            return 1
        red += 1
    print(f"test_prereg_status witnesses: {red}/{len(WITNESSES)} red; registry {len(WITNESSES)}", flush=True)
    return 0


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses())
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        if SELECTED not in WITNESSES:
            raise SystemExit(f"unknown mutant {SELECTED!r}")
        del sys.argv[index:index + 2]
    result = unittest.main(verbosity=2, exit=False).result
    ids = lambda pairs: [t.id().removeprefix("__main__.").split(" ")[0] for t, _ in pairs]
    print(f"test_prereg_status: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_prereg_status outcomes: " + json.dumps({"failures": ids(result.failures),
                                                        "errors": ids(result.errors),
                                                        "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
