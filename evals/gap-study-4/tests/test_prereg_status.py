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
        # W7A-R1-2: every listed model counted as running, as the absent model_status made it
        "runs-default": ("S4.running", "running_models", lambda: list(prereg.models())),
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
        held = prereg.deferred_arms(d)          # lane gemini-defer (R2): empty until the draft carries the key
        self.assertIn(f"arms     : {len(planned)} planned ({', '.join(planned)}); optional: C"
                      + (f"; deferred: {', '.join(a for a in planned if a in held)}" if held else ""), lines, "S1.arms")
        self.assertFalse(any(line.startswith("models") for line in lines), "S1.arms")
        for arm in planned:
            harness = {r["agent"]["harness"] for r in d["rows"] if r["arm"] == arm}
            self.assertEqual(len(harness), 1, "S1.arms")
            want = (f"  arm {arm}  {harness.pop()}: {len(d['models'][arm])} models, "
                    f"{sum(r['arm'] == arm for r in d['rows'])} rows: {', '.join(d['models'][arm])}"
                    + (f"; {prereg.deferral_label(held[arm])}" if arm in held else ""))
            self.assertIn(want, lines, "S1.arms")
        self.assertIn("  arm C  optional: claude-fable-5-1, 0 rows; optional (D2 B)", lines, "S1.arms")
        self.assertFalse(any("((" in line or "))" in line for line in lines), "S1.arms")
        self.assertFalse(any(line.startswith("  NOT RUN") for line in lines), "S1.arms")

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
        # every model in the fixed list: the planned arms' models, then the optional arms' (W7A-R1-2)
        d = committed()
        with mock.patch.object(prereg, "load", lambda: d):
            got = prereg.models()
        flat = [m for arm in d["arms"] if arm in d["models"] for m in d["models"][arm]]
        self.assertEqual(got, flat + ["claude-fable-5-1"], "S3.models")
        self.assertEqual(len(got), 8, "S3.models")
        self.assertFalse(set(got) & set(d["arms"]), "S3.models")

    def test_running_comes_from_the_rows(self):
        # W7A-R1-2: a model runs when the design plans rows for it; one with none is not running, with a reason.
        for name, d in (("committed", committed()), ("thinned", thinned())):
            with self.subTest(design=name):
                with mock.patch.object(prereg, "load", lambda: d):
                    running = prereg.running_models()
                    reasons = {m: prereg.not_run_reason(m) for m in prereg.models()}
                planned = {r["model"] for r in d["rows"]}
                held = prereg.deferred_models(d)    # lane gemini-defer (R2): a deferred arm's models never run
                self.assertEqual(running, [m for m in reasons if m in planned and m not in held], "S4.running")
                self.assertEqual(len(running), 7 - len(held), "S4.running")
                self.assertNotIn("claude-fable-5-1", running, "S4.running")
                self.assertEqual([m for m, why in reasons.items() if why],
                                 [m for m in reasons if m in held or m == "claude-fable-5-1"], "S4.running")
                self.assertIn("no planned rows", reasons["claude-fable-5-1"], "S4.running")
        # a design with one model's rows removed: that model stops running, with the reason
        d = committed()
        d["rows"] = [r for r in d["rows"] if r["model"] != "gpt-6-luna"]
        with mock.patch.object(prereg, "load", lambda: d):
            self.assertNotIn("gpt-6-luna", prereg.running_models(), "S4.running")
            self.assertIn("no planned rows", prereg.not_run_reason("gpt-6-luna") or "", "S4.running")


DEFERRED_G = "deferred (Javier, 22 Oct 2026)"


def deferred_design():
    """The committed draft carrying build_draft's own deferred_arms (lane gemini-defer, R1): what the regenerated draft
    holds, read from the builder rather than retyped."""
    import build_draft
    d = committed()
    d["deferred_arms"] = build_draft.assemble()["deferred_arms"]
    return d


def go(**changes):
    return dict({"kind": "deferred arm go", "arm": "G", "by": "Javier", "decision": "OD-synthetic",
                 "ask": "synthetic-go", "at": "2026-12-01T14:00:00Z"}, **changes)


class DeferredArm(unittest.TestCase):
    """Lane gemini-defer, ruling R2 (glitch-f1, 22 Oct 2026): arm G prints deferred, never running, never absent."""

    def test_status_prints_the_deferral(self):
        d = deferred_design()
        code, text = status(d)
        lines = text.splitlines()
        self.assertEqual(code, 0, "D1.status")
        self.assertIn("arms     : 3 planned (A, O, G); optional: C; deferred: G", lines, "D1.status")
        self.assertIn("  arm G  gemini: 2 models, 360 rows: gemini-3.8-flash, gemini-3.5-flash-lite; " + DEFERRED_G,
                      lines, "D1.status")
        self.assertIn("rows     : 1260 planned rows (n = 10 tries per half), 126 half-cells", lines, "D1.status")
        for arm in ("A", "O"):
            self.assertFalse(any(line.startswith(f"  arm {arm} ") and DEFERRED_G in line for line in lines),
                             "D1.status")

    def test_no_empty_deferred_list(self):
        # review NIT-3: a deferred arm with no planned arm in the design never leaves an empty "; deferred: " behind
        d = deferred_design()
        d["deferred_arms"] = {"Z": copy.deepcopy(d["deferred_arms"]["G"])}
        code, text = status(d)
        arms = [line for line in text.splitlines() if line.startswith("arms     :")]
        self.assertEqual(code, 0, "D1.status")
        self.assertEqual(arms, ["arms     : 3 planned (A, O, G); optional: C"], "D1.status")

    def test_not_run_reason_names_the_deferral(self):
        d = deferred_design()
        with mock.patch.object(prereg, "load", lambda: d):
            running = prereg.running_models()
            reasons = {m: prereg.not_run_reason(m) for m in prereg.models()}
            listed = prereg.models()
        self.assertEqual(len(listed), 8, "D2.reason")                  # never absent
        for model in ("gemini-3.8-flash", "gemini-3.5-flash-lite"):
            self.assertIn(model, listed, "D2.reason")
            self.assertNotIn(model, running, "D2.reason")
            self.assertEqual(reasons[model], DEFERRED_G, "D2.reason")
        self.assertEqual(len(running), 5, "D2.reason")
        self.assertEqual({m for m, why in reasons.items() if why},
                         {"gemini-3.8-flash", "gemini-3.5-flash-lite", "claude-fable-5-1"}, "D2.reason")

    def test_a_deferral_without_who_or_when_is_refused(self):
        d = deferred_design()
        for field, value in (("status", "optional"), ("by", ""), ("words", "his reply, undated")):
            bad = copy.deepcopy(d)
            bad["deferred_arms"]["G"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                prereg.deferred_arms(bad)

    def test_go_record_is_closed(self):
        self.assertEqual(prereg.go_record_problems(go(), "G"), [], "D3.go")
        self.assertTrue(prereg.deferred_arm_go("G", [go()]), "D3.go")
        self.assertFalse(prereg.deferred_arm_go("G", []), "D3.go")
        for bad in (go(kind="caps trimmed"), go(arm="O"), go(by="glitch-f1"), go(decision=""), go(ask=" "),
                    go(at="tomorrow"), go(at="2026-12-01T14:00:00"), dict(go(), extra=1),
                    {k: v for k, v in go().items() if k != "ask"}, "go", None):
            with self.subTest(record=bad):
                self.assertTrue(prereg.go_record_problems(bad, "G"), "D3.go")
                self.assertFalse(prereg.deferred_arm_go("G", [bad]), "D3.go")

    def test_go_record_is_read_committed(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(prereg.committed_go_records(root), [], "D3.go")      # no git at all: none
            git = lambda *a: subprocess.run(["git", "-C", tmp, *a], check=True, capture_output=True)
            git("init", "-q")
            git("config", "user.email", "synthetic@example.invalid")
            git("config", "user.name", "synthetic")
            (root / "other.txt").write_text("x\n")
            git("add", "other.txt")
            git("commit", "-q", "-m", "synthetic base")
            (root / prereg.GO_RECORD.name).write_text(json.dumps([go()]))
            self.assertEqual(prereg.committed_go_records(root), [], "D3.go")      # written, not committed
            git("add", prereg.GO_RECORD.name)
            # review NIT-1 (its M07 survivor): staged in the index, not committed, is still no go
            self.assertEqual(prereg.committed_go_records(root), [], "D3.go")
            git("commit", "-q", "-m", "synthetic go")
            self.assertEqual(prereg.committed_go_records(root), [go()], "D3.go")
            self.assertTrue(prereg.deferred_arm_go("G", prereg.committed_go_records(root)), "D3.go")
        self.assertEqual(prereg.committed_go_records(), [], "D3.go")      # this tree commits no go record


BOUND = {"S1.arms": "test_arms_are_named_as_arms", "S2.rows": "test_rows_are_counted_from_the_rows",
         "S3.models": "test_models_are_the_models", "S4.running": "test_running_comes_from_the_rows"}
WITNESSES = {name: ("StatusIsRound4." + BOUND[clause], clause) for name, (clause, _, _) in mutants().items()}


def run_witnesses():
    import re
    import subprocess
    red = 0
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_prereg_status witnesses", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve())],
                                    timeout=300, tag="test_prereg_status")
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
