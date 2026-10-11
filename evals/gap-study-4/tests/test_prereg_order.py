#!/usr/bin/env python3
"""`prereg.py --order` names freeze.planned_order's whole-row order (Gap Study round 4, slice S3).

The w5c lane carried this: round 3's per-axis positive/control order is not the
order the freeze writes. Round 4's freeze seeds ONE permutation of the design's
whole planned rows from the review commit (freeze.planned_order), so the door
anyone uses to recompute the order must return exactly that.

Fake seeds only; the committed draft's rows; no model, network or take.
--mutant NAME arms one altered prereg in setUpModule. --witnesses runs every
registered mutant in its own process and requires the bound method to fail by
an AssertionError carrying its clause token (rule B; collateral is listed, not
credited).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import prereg  # noqa: E402

SEED = "f" * 40  # a fake review sha
OTHER = "0123456789abcdef0123456789abcdef01234567"
SELECTED = None
PATCHES = []
REAL_LOAD = prereg.load


def fake_pinned():
    """The committed draft with every pending agent version filled by a fake string."""
    import copy
    d = copy.deepcopy(REAL_LOAD())
    for r in d["rows"]:
        r["agent"]["version"] = "0.0.0-fake"
    return d


FAKE = None


def rows():
    return FAKE["rows"]


def row_bytes(row):
    return json.dumps(row, sort_keys=True).encode()


def independent_order(seed):
    """The freeze's rule, recomputed here from its documented key (not by calling freeze)."""
    def key(row):
        return hashlib.sha256(seed.encode() + (json.dumps(row, indent=2, ensure_ascii=False) + "\n").encode()).hexdigest()
    return sorted(rows(), key=key)


def per_axis(seed_sha):
    """The inherited round 3 shape: one permutation per axis over (task, half, model, take)."""
    out = []
    for t in sorted(x["id"] for x in prereg.load()["tasks"]):
        for half in ("positive", "control"):
            for m in sorted(prereg.running_models()):
                for k in range(1, prereg.n() + 1):
                    out.append((t, half, m, k))
    import random
    rng = random.Random(int(hashlib.sha256(("claude" + seed_sha).encode()).hexdigest(), 16))
    rng.shuffle(out)
    return {"claude": out}


def mutants():
    real = prereg.order
    return {
        # the carry itself: the per-axis order returns
        "per-axis": ("O1.planned_order", lambda seed: per_axis(seed)),
        # a whole-row order, but not the one the freeze seeds
        "other-seed": ("O1.planned_order", lambda seed: real(seed + "0")),
        # a row lost from the permutation
        "dropped-row": ("O2.whole_rows", lambda seed: real(seed)[:-1]),
        # a row duplicated in place of another
        "duplicated-row": ("O2.whole_rows", lambda seed: (lambda o: o[:-1] + o[:1])(real(seed))),
        # whole rows from the right permutation, regrouped arm by arm
        "arm-blocks": ("O2.interleaved", lambda seed: sorted(real(seed), key=lambda r: r["arm"])),
        # pending versions filled in instead of refused
        "versions-defaulted": ("O5.pending", lambda seed: __import__("freeze").planned_order(
            {"rows": [dict(r, agent=dict(r["agent"], version=r["agent"]["version"] or "default"))
                      for r in prereg.load()["rows"]]}, seed)),
        # the seed check removed
        "short-seed": ("O4.seed", lambda seed: __import__("freeze").planned_order(prereg.load(), seed)),
    }


def setUpModule():
    global FAKE
    FAKE = fake_pinned()
    PATCHES.append(mock.patch.object(prereg, "load", lambda: FAKE))
    if SELECTED is None:
        pass
    elif SELECTED == "cli-label":
        PATCHES.append(mock.patch.object(prereg, "ORDER_FUNCTION", "prereg.order (per axis)"))
    else:
        PATCHES.append(mock.patch.object(prereg, "order", mutants()[SELECTED][1]))
    for p in PATCHES:
        p.start()


def tearDownModule():
    while PATCHES:
        PATCHES.pop().stop()


def cli(*args):
    out = io.StringIO()
    with mock.patch.object(sys, "argv", ["prereg.py", *args]), contextlib.redirect_stdout(out):
        code = prereg.main()
    return code, out.getvalue()


class OrderIsPlannedOrder(unittest.TestCase):
    def test_order_is_freeze_planned_order(self):
        import freeze
        got = prereg.order(SEED)
        self.assertTrue(isinstance(got, list) and got == freeze.planned_order(prereg.load(), SEED)
                        and got == independent_order(SEED), "O1.planned_order")
        self.assertTrue(prereg.order(OTHER) == freeze.planned_order(prereg.load(), OTHER) != got,
                        "O1.planned_order")

    def test_order_is_whole_rows(self):
        got = prereg.order(SEED)
        self.assertTrue(isinstance(got, list) and all(isinstance(r, dict) for r in got), "O2.whole_rows")
        self.assertEqual(sorted(map(row_bytes, got)), sorted(map(row_bytes, rows())), "O2.whole_rows")
        self.assertTrue(len({r["slot"] for r in got}) == len(got) == len(rows()) > 0, "O2.whole_rows")

    def test_order_interleaves_arms(self):
        got = prereg.order(SEED)
        self.assertIsInstance(got, list, "O2.interleaved")
        first = got[:len(got) // 4]
        self.assertTrue(len({r["arm"] for r in first}) == len({r["arm"] for r in rows()}) > 1, "O2.interleaved")

    def test_cli_names_planned_order(self):
        code, text = cli("--order", SEED)
        got = prereg.order(SEED)
        self.assertEqual(code, 0, "O3.cli")
        self.assertIn(f"take order: freeze.planned_order, one permutation of {len(rows())} whole planned rows",
                      text, "O3.cli")
        self.assertNotIn("axis", text, "O3.cli")
        listed = [line.split()[-1] for line in text.splitlines() if line.startswith("  ") and " s-" in line]
        self.assertEqual(listed, [r["slot"] for r in got[:8]], "O3.cli")

    def test_committed_draft_refuses_until_versions_are_pinned(self):
        self.assertTrue(any(r["agent"]["version"] is None for r in REAL_LOAD()["rows"]), "O5.pending")
        with mock.patch.object(prereg, "load", REAL_LOAD):
            with self.assertRaisesRegex(ValueError, "agent must be exactly", msg="O5.pending"):
                prereg.order(SEED)
            code, text = cli("--order", SEED)
        self.assertEqual(code, 1, "O5.pending")
        self.assertIn("take order: freeze.planned_order refuses the design in force (prereg-draft.json)", text,
                      "O5.pending")

    def test_short_seed_refused(self):
        for seed in ("", "abc123"):
            with self.subTest(seed=seed), self.assertRaises(SystemExit, msg="O4.seed"):
                prereg.order(seed)


BOUND = {"O1.planned_order": "test_order_is_freeze_planned_order", "O2.whole_rows": "test_order_is_whole_rows",
         "O2.interleaved": "test_order_interleaves_arms", "O3.cli": "test_cli_names_planned_order",
         "O4.seed": "test_short_seed_refused", "O5.pending": "test_committed_draft_refuses_until_versions_are_pinned"}
WITNESSES = {**{name: ("OrderIsPlannedOrder." + BOUND[clause], clause) for name, (clause, _) in mutants().items()},
             "cli-label": ("OrderIsPlannedOrder.test_cli_names_planned_order", "O3.cli")}


def run_witnesses():
    import re
    import subprocess
    red = 0
    for name, (method, clause) in sorted(WITNESSES.items()):
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name],
                             capture_output=True, text=True, timeout=300)
        record = re.findall(r"^test_prereg_order outcomes: (\{.*\})$", got.stdout, re.M)
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
    print(f"test_prereg_order witnesses: {red}/{len(WITNESSES)} red; registry {len(WITNESSES)}", flush=True)
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
    print(f"test_prereg_order: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_prereg_order outcomes: " + json.dumps({"failures": ids(result.failures),
                                                       "errors": ids(result.errors),
                                                       "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
