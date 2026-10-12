#!/usr/bin/env python3
"""Lane w11c-walk-plan: the CP6 walk list and its coverage report (rehearsals/README.md question 3).

walk_plan.plan_walks(design) lists the walks CP6 requires (plan 874-876; arms O and G per ruling Q-2, D8:448), each
spec carrying exactly the register entry's fields plus the agent, derived from the design files and checked by
walk_register.entry_problems. These tests re-derive every figure from the design with code of their own, never
from a typed number, and bind:

  P1.counts         the figures per arm and model equal an independent derivation from prereg-draft.json and
                    tasks/<task>.json (every wording of every task and half on the every-wording model, each task
                    and half once on every other planned model, nothing for the optional arm C)
  P2.dropped        a dropped task or a dropped wording in a synthetic copy of the design changes the figures, to
                    what the independent derivation says; witnesses count-hard-coded, wordings-typed
  P3.halves         every planned model gets every task and every half; every spec has exactly the register's
                    fields plus the agent, passes entry_problems, names the harness the design's rows give, is
                    never counted and carries no walk id; the optional arm is not required; witnesses half-missing,
                    optional-required, agent-unread
  P4.off-design     a register entry the design refuses, or one the plan does not require, is reported by its walk
                    id and never counted toward coverage; a retry covers its spec once; witnesses off-design-counted,
                    outside-counted
  P5.exact-wording  on the every-wording model a walk covers only its own wording; on every other model any wording
                    of the task covers the task and half; two specs on one key refuse; witnesses
                    exact-wording-unchecked, spec-key-shared
  P6.require        --coverage exits 0 while walks are missing and names each; --require-complete exits 1 on any
                    gap and 0 only on a register that covers every spec; a missing, duplicate-keyed or symlinked
                    register exits 2; witnesses require-complete-gap, register-duplicate-admitted,
                    register-link-admitted
  P7.register-only  --coverage opens the register and the design files and nothing else under rehearsals/: no walk
                    folder is listed or read; witness folder-listed
  P8.spec-checked   a spec the register's design refuses, or one whose cell is not a row of the design, refuses the
                    whole plan, and so does a planned model whose rows name two harnesses; witnesses spec-unchecked,
                    cell-unchecked, harness-mixed-admitted
  P9.prose          the printed plan and coverage report are clean under lint_language's and lint_pooling's
                    patterns, and no printed line states a figure across arms or models; witness figure-across-arms
  P10.every-rule    the every-wording model is resolved from the plan's rule against the design's arm, and zero or
                    two matching models refuse; witness every-rule-first-match

Red first: before walk_plan.py exists every test fails by its own assertion (P0.module), with no error.

--mutant NAME compiles one altered walk_plan in memory before the bound test runs; --witnesses runs every
registered mutant in its own process, only its bound test, and requires that test to fail by an AssertionError
carrying its clause token, with no error (rule B).

Fakes and synthetic copies of the design only: no walk, model, network, container, credential, salt or holdout.
setUpModule arms a process guard (every subprocess start is refused while the tests run) and tearDownModule
restores sys.path and the guard. No folder outside this study and the test's own temporary folders is read.
"""
from __future__ import annotations

import builtins
import contextlib
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent

SELECTED = None
MODS: dict = {}
SAVED: dict = {}
LANE = "w11c-walk-plan"
FIELDS = ("walk", "task", "half", "wording", "arm", "model", "reason", "counted")


def mutants():
    """name -> (clause, old text, new text) in walk_plan.py. Each weakens one guard; old must occur exactly once."""
    return {
        "count-hard-coded": ("P2.dropped",
                             "    out: dict = {}\n    for spec in specs:\n",
                             "    return {\"A\": {\"claude-opus-5-5\": 18, \"claude-sonnet-5-5\": 18, "
                             "\"claude-haiku-4-5-20251001\": 90}, \"O\": {\"gpt-6.1-sol\": 18, \"gpt-6-luna\": 18}, "
                             "\"G\": {\"gemini-3.8-flash\": 18, \"gemini-3.5-flash-lite\": 18}}\n"
                             "    out: dict = {}\n    for spec in specs:\n"),
        "wordings-typed": ("P2.dropped",
                           "wordings = list(task[\"wordings\"]) if every else list(task[\"wordings\"])[:1]",
                           "wordings = [\"w1\", \"w2\", \"w3\", \"w4\", \"w5\"] if every else [\"w1\"]"),
        "half-missing": ("P3.halves", "            for half in task[\"halves\"]:",
                         "            for half in task[\"halves\"][:1]:"),
        "optional-required": ("P3.halves",
                              "    planned = {arm: list(models) for arm, models in draft[\"models\"].items()}",
                              "    planned = {arm: list(models) for arm, models in register[\"arms\"].items()}"),
        "agent-unread": ("P3.halves", "                        \"agent\": agents[(arm, model)],",
                         "                        \"agent\": \"claude-code\","),
        "off-design-counted": ("P4.off-design", "        if bad:\n", "        if False:\n"),
        "outside-counted": ("P4.off-design", "        if key not in by_key:\n", "        if False:\n"),
        "exact-wording-unchecked": ("P5.exact-wording",
                                    "    exact = (entry[\"arm\"], entry[\"model\"]) == design[\"every_wording\"]",
                                    "    exact = False"),
        "require-complete-gap": ("P6.require", "    if args.require_complete and missing:",
                                 "    if False:"),
        "folder-listed": ("P7.register-only", "        entries = read_register(base)\n",
                          "        entries = read_register(base)\n"
                          "        _ = sorted(p.name for p in base.iterdir())\n"),
        "spec-unchecked": ("P8.spec-checked", "    if problems:\n        raise PlanRefused(",
                           "    if False:\n        raise PlanRefused("),
        "cell-unchecked": ("P8.spec-checked", "        if cell not in design[\"cells\"]:",
                           "        if False:"),
        "figure-across-arms": ("P9.prose", "    return lines\n\n\ndef coverage_lines(",
                               "    lines.append(f\"{len(specs)} required walks on every arm and model\")\n"
                               "    return lines\n\n\ndef coverage_lines("),
        "every-rule-first-match": ("P10.every-rule", "    if len(found) != 1:\n", "    if not found:\n"),
        "register-duplicate-admitted": ("P6.require",
                                        "json.loads(path.read_text(), "
                                        "object_pairs_hook=walk_register.no_duplicate_keys)",
                                        "json.loads(path.read_text())"),
        "register-link-admitted": ("P6.require", "    if path.is_symlink() or not path.is_file():",
                                   "    if not path.is_file():"),
        "harness-mixed-admitted": ("P8.spec-checked", "            if len(got) != 1:\n", "            if not got:\n"),
        "spec-key-shared": ("P5.exact-wording", "        if key in by_key:\n            raise PlanRefused(",
                            "        if False:\n            raise PlanRefused("),
    }


class Refused(Exception):
    pass


def refuse_process(*args, **kwargs):
    raise Refused(f"test_walk_plan: a process start is refused while the tests run: {args[:1]!r}")


def setUpModule():
    SAVED["path"] = list(sys.path)
    for p in (HERE, HERE / "tests"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    SAVED["popen"] = subprocess.Popen
    subprocess.Popen = refuse_process          # the process guard: armed here, never at import
    for name in ("walk_register", "lint_language", "lint_pooling"):
        MODS[name] = __import__(name)
    try:
        import walk_plan
    except ImportError:
        MODS["walk_plan"] = None               # red first: every test fails by P0.module, never by an error
        return
    MODS["walk_plan"] = walk_plan
    if SELECTED is None:
        return
    _, old, new = mutants()[SELECTED]
    path = HERE / "walk_plan.py"
    text = path.read_text()
    assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
    mod = types.ModuleType("walk_plan")
    mod.__file__ = str(path)
    sys.modules["walk_plan"] = mod
    exec(compile(text.replace(old, new), str(path) + " (witness)", "exec"), mod.__dict__)
    MODS["walk_plan"] = mod


def tearDownModule():
    subprocess.Popen = SAVED["popen"]
    if SELECTED is not None:
        sys.modules.pop("walk_plan", None)     # a compiled witness never outlives this module
    sys.path[:] = SAVED["path"]


# ---- the independent derivation: the tests' own reading of the design files, never walk_plan's ----

def read_design(study: Path):
    draft = json.loads((study / "prereg-draft.json").read_text())
    tasks = []
    for t in draft["tasks"]:
        halves = list(json.loads((study / "tasks" / f"{t['id']}.json").read_text())["halves"])
        tasks.append((t["id"], halves, list(t["wordings"])))
    return draft, tasks


def every_wording_model(draft) -> tuple:
    """The plan's rule (plan 875, "every wording of every task, on Haiku"), read against the design's arm A."""
    found = [(arm, m) for arm, models in draft["models"].items() for m in models if "haiku" in m.casefold()]
    assert len(found) == 1, f"the design names {len(found)} haiku models"
    return found[0]


def expected_counts(study: Path) -> dict:
    draft, tasks = read_design(study)
    every = every_wording_model(draft)
    out: dict = {}
    for arm, models in draft["models"].items():
        for m in models:
            n = 0
            for _, halves, wordings in tasks:
                n += len(halves) * (len(wordings) if (arm, m) == every else 1)
            out.setdefault(arm, {})[m] = n
    return out


def harness_of(draft) -> dict:
    out: dict = {}
    for row in draft["rows"]:
        out.setdefault((row["arm"], row["model"]), set()).add(row["agent"]["harness"])
    return out


def entry(spec: dict, walk: str, **changes) -> dict:
    e = {k: spec[k] for k in FIELDS}
    e.update(walk=walk, reason="synthetic register entry for a test", counted=False)
    e.update(changes)
    return e


class Base(unittest.TestCase):
    def wp(self, clause: str):
        mod = MODS.get("walk_plan")
        self.assertIsNotNone(mod, f"P0.module {clause}: walk_plan.py does not exist yet")
        return mod

    def plan(self, clause: str, study: Path = HERE):
        wp = self.wp(clause)
        try:
            design = wp.design_in_force(study)
            return design, wp.plan_walks(design)
        except wp.PlanRefused as exc:
            self.fail(f"{clause}: the plan was refused: {exc}")

    def cover(self, clause: str, entries: list, specs: list, design: dict) -> dict:
        wp = self.wp(clause)
        try:
            return wp.coverage(entries, specs, design)
        except wp.PlanRefused as exc:
            self.fail(f"{clause}: coverage was refused: {exc}")

    def tmpdir(self) -> Path:
        d = Path(tempfile.mkdtemp(prefix="w11c-"))
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def study_copy(self) -> Path:
        """A synthetic copy of the design files: prereg-draft.json and tasks/*.json, nothing else."""
        d = self.tmpdir()
        shutil.copy2(HERE / "prereg-draft.json", d / "prereg-draft.json")
        (d / "tasks").mkdir()
        for f in (HERE / "tasks").glob("*.json"):
            shutil.copy2(f, d / "tasks" / f.name)
        return d

    def edit_draft(self, study: Path, edit) -> None:
        path = study / "prereg-draft.json"
        draft = json.loads(path.read_text())
        edit(draft)
        path.write_text(json.dumps(draft))

    def rehearsals(self, entries: list) -> Path:
        base = self.tmpdir() / "rehearsals"
        base.mkdir()
        (base / "register.json").write_text(json.dumps({"schema": 1, "walks": entries}))
        return base

    def cli(self, clause: str, argv: list) -> tuple[int, str]:
        wp = self.wp(clause)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = wp.main(argv)
        return code, out.getvalue() + err.getvalue()


class P1Counts(Base):
    def test_the_figures_are_rederived_from_the_design(self):
        _, specs = self.plan("P1.counts")
        wp = self.wp("P1.counts")
        self.assertEqual(wp.counts(specs), expected_counts(HERE), "P1.counts")
        self.assertEqual(len(specs), sum(sum(v.values()) for v in expected_counts(HERE).values()), "P1.counts")


class P2Dropped(Base):
    def test_a_dropped_task_or_wording_changes_the_figures(self):
        wp = self.wp("P2.dropped")
        base = expected_counts(HERE)
        # a dropped task: gone from the draft's tasks and rows
        study = self.study_copy()
        draft = json.loads((study / "prereg-draft.json").read_text())
        gone = draft["tasks"][-1]["id"]
        self.edit_draft(study, lambda d: (d.__setitem__("tasks", [t for t in d["tasks"] if t["id"] != gone]),
                                          d.__setitem__("rows", [r for r in d["rows"] if r["task"] != gone])))
        _, specs = self.plan("P2.dropped", study)
        want = expected_counts(study)
        self.assertNotEqual(want, base, "P2.dropped: the synthetic edit did not change the design")
        self.assertEqual(wp.counts(specs), want, f"P2.dropped: a dropped task ({gone})")
        self.assertNotIn(gone, {s["task"] for s in specs}, "P2.dropped")
        # a dropped wording: the last wording of the first task, gone from the task and its rows
        study = self.study_copy()
        draft = json.loads((study / "prereg-draft.json").read_text())
        task, last = draft["tasks"][0]["id"], draft["tasks"][0]["wordings"][-1]

        def drop(d):
            d["tasks"][0]["wordings"] = d["tasks"][0]["wordings"][:-1]
            d["rows"] = [r for r in d["rows"] if not (r["task"] == task and r["wording"] == last)]
        self.edit_draft(study, drop)
        _, specs = self.plan("P2.dropped", study)
        want = expected_counts(study)
        self.assertNotEqual(want, base, "P2.dropped: the synthetic edit did not change the design")
        self.assertEqual(wp.counts(specs), want, f"P2.dropped: a dropped wording ({task} {last})")
        self.assertNotIn((task, last), {(s["task"], s["wording"]) for s in specs}, "P2.dropped")


class P3Halves(Base):
    def test_every_task_and_half_on_every_planned_model(self):
        design, specs = self.plan("P3.halves")
        wr = MODS["walk_register"]
        draft, tasks = read_design(HERE)
        every = every_wording_model(draft)
        harness = harness_of(draft)
        reg = wr.design_in_force(HERE)
        for arm, models in draft["models"].items():
            for m in models:
                mine = [s for s in specs if (s["arm"], s["model"]) == (arm, m)]
                self.assertEqual({(s["task"], s["half"]) for s in mine},
                                 {(t, h) for t, halves, _ in tasks for h in halves}, f"P3.halves {arm} {m}")
                if (arm, m) == every:
                    self.assertEqual({(s["task"], s["half"], s["wording"]) for s in mine},
                                     {(t, h, w) for t, halves, ws in tasks for h in halves for w in ws},
                                     f"P3.halves every wording on {m}")
        for i, s in enumerate(specs):
            self.assertEqual(tuple(s), FIELDS + ("agent",), f"P3.halves spec {i}: its fields")
            self.assertIsNone(s["walk"], f"P3.halves spec {i}: the walk id is the runner's")
            self.assertIs(s["counted"], False, f"P3.halves spec {i}: counted")
            self.assertTrue(isinstance(s["reason"], str) and s["reason"].strip(), f"P3.halves spec {i}: reason")
            self.assertEqual({s["agent"]}, harness[(s["arm"], s["model"])], f"P3.halves spec {i}: agent")
            self.assertEqual(wr.entry_problems(i, entry(s, f"probe-{i}"), reg), [], f"P3.halves spec {i}")
        optional = {spec["model"] for spec in (draft.get("optional_arms") or {}).values()}
        self.assertTrue(optional, "P3.halves: the design names an optional arm (arm C)")
        self.assertFalse(optional & {s["model"] for s in specs}, "P3.halves: an optional arm is never required")
        self.assertFalse(set(draft.get("optional_arms") or {}) & {s["arm"] for s in specs}, "P3.halves")
        self.assertEqual(design["every_wording"], every, "P3.halves")


class P4OffDesign(Base):
    def test_an_entry_outside_the_plan_is_reported_never_counted(self):
        wp = self.wp("P4.off-design")
        design, specs = self.plan("P4.off-design")
        draft, _ = read_design(HERE)
        every = design["every_wording"]
        other = next(s for s in specs if (s["arm"], s["model"]) != every)
        later = json.loads((HERE / "prereg-draft.json").read_text())["tasks"]
        later_wording = next(t["wordings"][-1] for t in later if t["id"] == other["task"])
        c_arm, c_spec = next(iter(draft["optional_arms"].items()))
        entries = [
            entry(other, "w-ok", wording=later_wording),                 # covers: any wording of the task
            entry(other, "w-retry"),                                     # a retry: the same spec, counted once
            entry(other, "w-bad-wording", wording="w-not-in-design"),    # refused by the design
            entry(other, "w-counted", counted=True),                     # refused: a walk is never counted
            entry(other, "w-wrong-arm", arm="O" if other["arm"] != "O" else "G"),
            entry(other, "w-arm-c", arm=c_arm, model=c_spec["model"]),   # in the design, not in the plan
        ]
        got = self.cover("P4.off-design", entries, specs, design)
        key = wp.cover_key(other, design)
        self.assertEqual(list(got["covered"]), [key], "P4.off-design: only the plan's spec is covered")
        self.assertEqual(got["covered"][key], ["w-ok", "w-retry"], "P4.off-design: a retry covers the spec once")
        self.assertEqual(len(got["missing"]), len(specs) - 1, "P4.off-design: one spec covered, once")
        outside = [w for w, _ in got["outside"]]
        self.assertEqual(outside, ["w-bad-wording", "w-counted", "w-wrong-arm", "w-arm-c"], "P4.off-design")
        why = dict(got["outside"])
        self.assertIn("not a walk the plan requires", why["w-arm-c"], "P4.off-design")
        base = self.rehearsals(entries)
        code, out = self.cli("P4.off-design", ["--coverage", "--base", str(base)])
        self.assertEqual(code, 0, f"P4.off-design: {out}")
        for w in outside:
            self.assertRegex(out, rf"(?m)^outside the plan, not counted: walk '{re.escape(w)}'", "P4.off-design")


class P5ExactWording(Base):
    def test_the_every_wording_model_needs_each_wording(self):
        wp = self.wp("P5.exact-wording")
        design, specs = self.plan("P5.exact-wording")
        every = [s for s in specs if (s["arm"], s["model"]) == design["every_wording"]]
        first, second = every[0], next(s for s in every[1:] if (s["task"], s["half"]) == (every[0]["task"],
                                                                                          every[0]["half"]))
        got = self.cover("P5.exact-wording", [entry(second, "h-second")], specs, design)
        self.assertEqual(list(got["covered"]), [wp.cover_key(second, design)], "P5.exact-wording")
        self.assertIn(first, got["missing"], "P5.exact-wording: another wording does not cover this one")
        self.assertNotEqual(wp.cover_key(first, design), wp.cover_key(second, design), "P5.exact-wording")
        other = next(s for s in specs if (s["arm"], s["model"]) != design["every_wording"])
        twin = dict(other, wording=first["wording"] if other["wording"] != first["wording"] else "w2")
        with self.assertRaises(wp.PlanRefused, msg="P5.exact-wording: two specs for one task and half"):
            wp.coverage([], [other, twin], design)
        self.assertEqual(sum(1 for s in specs if wp.cover_key(s, design) == wp.cover_key(other, design)), 1,
                         "P5.exact-wording: one spec per task and half on every other model")


class P6Require(Base):
    def test_require_complete_refuses_a_gap(self):
        _, specs = self.plan("P6.require")
        empty = self.rehearsals([])
        code, out = self.cli("P6.require", ["--coverage", "--base", str(empty)])
        self.assertEqual(code, 0, f"P6.require: missing walks before the freeze exit 0: {out}")
        self.assertIn("the register lists no walk", out, "P6.require: an empty register is said out loud")
        for s in specs:
            self.assertIn(f"missing  {s['arm']} {s['model']} {s['task']} {s['half']}", out, "P6.require")
        code, out = self.cli("P6.require", ["--coverage", "--require-complete", "--base", str(empty)])
        self.assertEqual(code, 1, "P6.require: --require-complete with every walk missing")
        one_gap = self.rehearsals([entry(s, f"walk-{i}") for i, s in enumerate(specs[:-1])])
        code, out = self.cli("P6.require", ["--coverage", "--require-complete", "--base", str(one_gap)])
        self.assertEqual(code, 1, f"P6.require: --require-complete with one gap: {out[-400:]}")
        last = specs[-1]
        n = sum(1 for s in specs if (s["arm"], s["model"]) == (last["arm"], last["model"]))
        self.assertIn(f"arm {last['arm']}, {last['model']} ({last['agent']}): {n - 1} of {n} required walks "
                      f"covered, 1 missing", out, "P6.require")
        full = self.rehearsals([entry(s, f"walk-{i}") for i, s in enumerate(specs)])
        code, out = self.cli("P6.require", ["--coverage", "--require-complete", "--base", str(full)])
        self.assertEqual(code, 0, f"P6.require: a complete register: {out[-400:]}")
        bad = self.tmpdir() / "rehearsals"
        bad.mkdir()
        (bad / "register.json").write_text('{"schema": 1, "walks": [], "walks": []}')
        code, out = self.cli("P6.require", ["--coverage", "--base", str(bad)])
        self.assertEqual(code, 2, f"P6.require: a register with a duplicate key: {out}")
        code, out = self.cli("P6.require", ["--coverage", "--base", str(self.tmpdir())])
        self.assertEqual(code, 2, f"P6.require: a missing register is not an empty one: {out}")
        linked = self.tmpdir() / "rehearsals"
        linked.mkdir()
        (linked / "register.json").symlink_to(full / "register.json")
        code, out = self.cli("P6.require", ["--coverage", "--base", str(linked)])
        self.assertEqual(code, 2, f"P6.require: a symlinked register is refused: {out[-300:]}")


class P7RegisterOnly(Base):
    def test_coverage_reads_the_register_and_never_a_walk_folder(self):
        _, specs = self.plan("P7.register-only")
        base = self.rehearsals([entry(specs[0], "walk-a")])
        (base / "walk-a").mkdir()
        (base / "walk-a" / "grade.json").write_text("{}")
        touched: list = []
        real_open, real_listdir, real_scandir = builtins.open, os.listdir, os.scandir

        def rec_open(file, *a, **k):
            touched.append(("open", str(file)))
            return real_open(file, *a, **k)

        def rec_listdir(path=".", *a, **k):
            touched.append(("list", str(path)))
            return real_listdir(path, *a, **k)

        def rec_scandir(path=".", *a, **k):
            touched.append(("list", str(path)))
            return real_scandir(path, *a, **k)
        with mock.patch("builtins.open", rec_open), mock.patch("io.open", rec_open), \
                mock.patch("os.listdir", rec_listdir), mock.patch("os.scandir", rec_scandir):
            code, out = self.cli("P7.register-only", ["--coverage", "--base", str(base)])
        self.assertEqual(code, 0, f"P7.register-only: {out}")
        under = [(kind, p) for kind, p in touched if Path(p).resolve().is_relative_to(base.resolve())]
        self.assertEqual(under, [("open", str(base / "register.json"))],
                         "P7.register-only: only the register is opened under rehearsals/, and nothing is listed")
        self.assertIn("covered", out, "P7.register-only")


class P8SpecChecked(Base):
    def test_a_spec_the_design_refuses_refuses_the_plan(self):
        wp = self.wp("P8.spec-checked")
        design, _ = self.plan("P8.spec-checked")
        # the register's design no longer admits one planned model
        arm, models = next((a, m) for a, m in design["planned"].items() if a != design["every_wording"][0])
        bent = copy.deepcopy(design)
        bent["register"]["arms"][arm] = [m for m in bent["register"]["arms"][arm] if m != models[0]]
        with self.assertRaises(wp.PlanRefused, msg="P8.spec-checked: a model the register refuses"):
            wp.plan_walks(bent)
        # a planned cell that is not a row of the design
        bent = copy.deepcopy(design)
        bent["cells"] = {c for c in bent["cells"] if c[1] != models[0]}
        with self.assertRaises(wp.PlanRefused, msg="P8.spec-checked: a cell with no row"):
            wp.plan_walks(bent)
        # a planned model whose rows name two harnesses
        study = self.study_copy()

        def mixed(d):
            row = next(r for r in d["rows"] if r["model"] == models[0])
            row["agent"] = dict(row["agent"], harness=row["agent"]["harness"] + "-other")
        self.edit_draft(study, mixed)
        with self.assertRaises(wp.PlanRefused, msg="P8.spec-checked: two harnesses for one model"):
            wp.design_in_force(study)


class P9Prose(Base):
    def test_the_printed_plan_and_report_are_clean(self):
        _, specs = self.plan("P9.prose")
        ll, lp = MODS["lint_language"], MODS["lint_pooling"]
        code, listed = self.cli("P9.prose", ["--list"])
        self.assertEqual(code, 0, f"P9.prose: {listed[-400:]}")
        base = self.rehearsals([entry(specs[0], "walk-a")])
        code, covered = self.cli("P9.prose", ["--coverage", "--base", str(base)])
        self.assertEqual(code, 0, "P9.prose")
        draft, _ = read_design(HERE)
        for name, text in (("--list", listed), ("--coverage", covered)):
            found = lp.scan_text(text, f"walk_plan {name}")
            found += ll.scan_text(text, f"walk_plan {name}", ll.load_allowlist())
            self.assertEqual(found, [], f"P9.prose {name}")
            for line in text.splitlines():
                # a figure sits on a line that names one model, on a citation header, or on one register entry
                named = any(m in line for models in draft["models"].values() for m in models)
                if re.search(r"\d", line):
                    self.assertTrue(named or line.startswith(("# ", "outside the plan, not counted: walk ")),
                                    f"P9.prose {name}: a figure not bound to one model: {line!r}")
        for arm, models in draft["models"].items():
            for m in models:
                self.assertRegex(listed, rf"(?m)^arm {arm}, {re.escape(m)} \(", f"P9.prose: a line for {m}")


class P10EveryRule(Base):
    def test_the_every_wording_model_is_one_model_of_the_design(self):
        wp = self.wp("P10.every-rule")
        design, _ = self.plan("P10.every-rule")
        draft, _ = read_design(HERE)
        self.assertEqual(design["every_wording"], every_wording_model(draft), "P10.every-rule")

        def two(d):
            # a second haiku model with rows of its own, so only the every-wording rule can refuse it
            d["models"]["A"] = d["models"]["A"] + ["claude-haiku-x"]
            d["rows"] = d["rows"] + [dict(r, model="claude-haiku-x") for r in d["rows"] if "haiku" in r["model"]]
        for label, edit in (("none", lambda d: d["models"].__setitem__(
                                "A", [m for m in d["models"]["A"] if "haiku" not in m])),
                            ("two", two)):
            study = self.study_copy()
            self.edit_draft(study, edit)
            with self.assertRaises(wp.PlanRefused, msg=f"P10.every-rule: {label}") as caught:
                wp.design_in_force(study)
            self.assertIn("for every wording", str(caught.exception), f"P10.every-rule: {label}")


BOUND = {"P2.dropped": "P2Dropped.test_a_dropped_task_or_wording_changes_the_figures",
         "P3.halves": "P3Halves.test_every_task_and_half_on_every_planned_model",
         "P4.off-design": "P4OffDesign.test_an_entry_outside_the_plan_is_reported_never_counted",
         "P5.exact-wording": "P5ExactWording.test_the_every_wording_model_needs_each_wording",
         "P6.require": "P6Require.test_require_complete_refuses_a_gap",
         "P7.register-only": "P7RegisterOnly.test_coverage_reads_the_register_and_never_a_walk_folder",
         "P8.spec-checked": "P8SpecChecked.test_a_spec_the_design_refuses_refuses_the_plan",
         "P9.prose": "P9Prose.test_the_printed_plan_and_report_are_clean",
         "P10.every-rule": "P10EveryRule.test_the_every_wording_model_is_one_model_of_the_design"}
WITNESSES = {name: (BOUND[clause], clause) for name, (clause, _, _) in mutants().items()}


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=110)
        record = re.findall(r"^test_walk_plan outcomes: (\{.*\})$", got.stdout, re.M)
        outcome = json.loads(record[-1]) if record else None
        blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", got.stderr,
                            re.M | re.S)
        attributed = any(f"{cls}.{test}" == method and "AssertionError" in body and
                         re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w.-])", body)
                         for test, cls, body in blocks)
        clean = bool(outcome) and outcome["failures"] == [method] and outcome["errors"] == [] \
            and outcome["skipped"] == []
        passed = attributed and clean and got.returncode != 0
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}", flush=True)
        if not passed:
            print(got.stdout[-3000:] + got.stderr[-3000:], flush=True)
            return 1
        red += 1
    print(f"test_walk_plan witnesses: {red}/{len(chosen)} red; registry {len(WITNESSES)}", flush=True)
    return 0


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses(sys.argv[sys.argv.index("--witnesses") + 1:]))
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        if SELECTED not in WITNESSES:
            raise SystemExit(f"unknown mutant {SELECTED!r}")
        del sys.argv[index:index + 2]
    result = unittest.main(verbosity=2, exit=False).result
    ids = lambda pairs: [t.id().removeprefix("__main__.").split(" ")[0] for t, _ in pairs]  # noqa: E731
    print(f"test_walk_plan: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_walk_plan outcomes: " + json.dumps({"failures": ids(result.failures), "errors": ids(result.errors),
                                                    "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
