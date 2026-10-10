#!/usr/bin/env python3
"""The draft's derived identities and commitments; all supplied values here are fake.

--mutant NAME substitutes one builder accessor in setUpModule and runs this
whole file. No patch is armed on import; no model or container is called.
"""
from __future__ import annotations
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import build_draft as b
import study
import variants
import check_results
from box import image_lock, run_take
import harness_bookkeeping

SELECTED = None
PATCHES = []
CLAUDE = harness_bookkeeping.CLAUDE_CODE
CODEX, GEMINI = run_take.CODEX, run_take.GEMINI
MODELS = {"A": ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5-20251001"],
          "O": ["gpt-6.1-sol", "gpt-6-luna"],
          "G": ["gemini-3.8-flash", "gemini-3.5-flash-lite"]}
HARNESSES = {"A": CLAUDE, "O": CODEX, "G": GEMINI}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def core_problems(d):
    bad = []
    def need(ok, clause):
        if not ok:
            bad.append(clause)
    paths = sorted((HERE / "tasks").glob("*.json"))
    ids = [p.stem for p in paths]
    need([t["id"] for t in d["tasks"]] == ids, "R1.tasks")
    need(all(t["task_sha256"] == digest(HERE / "tasks" / (t["id"] + ".json")) and
             t["variants_sha256"] == digest(HERE / "variants" / (t["id"] + ".json")) for t in d["tasks"]), "R1.hashes")
    need(d["models"] == MODELS, "R2.models")
    need(d["n"] == variants.TRIES_PER_HALF and d["wordings"] == variants.N_WORDINGS and
         d["repeats"] == variants.REPEATS, "R2.n")
    need(d["optional_arms"] == {"C": {"model": "claude-fable-5-1", "status": "optional (D2 B)",
         "cut": "first cut if the freeze slips (plan 345)", "rows": 0, "tries": 0}}, "R2.optional")
    need(d["take_order"] is None and d["take_order_seed"] is None and
         d["take_order_function"] == "freeze.planned_order" and "review commit" in d["take_order_rule"] and
         "prereg.py --order" in d["order_carry"], "R3.order")
    rows = d["rows"]
    need(all(set(r["agent"]) == {"harness", "version"} and r["agent"]["harness"] == HARNESSES[r["arm"]]
             for r in rows), "R11.agent")
    need(len({r["slot"] for r in rows}) == len(rows), "R12.slots")
    cells = {}
    for r in rows:
        key = (r["arm"], r["task"], r["half"], r["model"], r["agent"]["harness"])
        cells.setdefault(r["half_cell"], set()).add(key)
    need(all(len(keys) == 1 for keys in cells.values()) and
         len({next(iter(k)) for k in cells.values()}) == len(cells), "R12.cells")
    expected = {(arm, task, model, c["half"], c["wording"], c["repeat"], c["pressure"])
                for arm, models in MODELS.items() for model in models for task in ids
                for c in variants.cells(task)}
    actual = {(r["arm"], r["task"], r["model"], r["half"], r["wording"], r["repeat"], r["pressure"]) for r in rows}
    need(actual == expected and len(rows) == len(expected), "R2.factors")
    need(d["amendments"] == {a: "Javier's letter \"D8: B2\", Tue 6 Oct 2026 23:43:50 EDT" for a in ("O", "G")}, "R13.amendment")
    need("confounded-design-unprompted" not in ids and all(r["task"] in ids for r in rows), "R19.tasks")
    need(d["counts"] == {"pairs": len(ids), "by_arm": {a: sum(r["arm"] == a for r in rows) for a in MODELS},
         "tries": len(rows), "half_cells": len(cells)} and d["counts"] ==
         {"pairs": 9, "by_arm": {"A": 540, "O": 360, "G": 360}, "tries": 1260, "half_cells": 126}, "R20.counts")
    locks = d["image_locks"]
    need({item["path"] for item in locks} == {str(p.relative_to(HERE)) for p in (HERE / "box").rglob("image.lock")}
         and all(item["sha256"] == digest(HERE / item["path"]) and
                 item["lock"] == image_lock.load(str(HERE / item["path"])) for item in locks), "R6.locks")
    need(all(r["agent"]["version"] is None for r in rows), "R6.unpinned")
    need(set(d["version_pins"]) == set(HARNESSES.values()) and all(set(d["version_pins"][h]) == set(MODELS[a])
         for a, h in HARNESSES.items()), "R14.pins")
    return bad


def changed(d, path, value):
    out = copy.deepcopy(d)
    current = out
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value
    return out


# Each mutation changes an emitted clause through the builder's own accessor.
CORE_MUTANTS = {
    "task-hash": ("R1.hashes", ("tasks", 0, "task_sha256"), "0" * 64),
    "models": ("R2.models", ("models", "O", 0), "fake-model"),
    "n": ("R2.n", ("n",), 11),
    "optional": ("R2.optional", ("optional_arms", "C", "tries"), 180),
    "order": ("R3.order", ("take_order_seed",), "fake-seed"),
    "agent": ("R11.agent", ("rows", 0, "agent", "harness"), "fake-harness"),
    "slots": ("R12.slots", ("rows", 0, "slot"), None),
    "cells": ("R12.cells", ("rows", 0, "half_cell"), "fake-cell"),
    "factor": ("R2.factors", ("rows", 0, "repeat"), 99),
    "amendment": ("R13.amendment", ("amendments", "O"), "fake-source"),
    "task-list": ("R19.tasks", ("rows", 0, "task"), "confounded-design-unprompted"),
    "pair-count": ("R20.counts", ("counts", "pairs"), 10),
    "lock": ("R6.locks", ("image_locks", 0, "sha256"), "0" * 64),
    "version": ("R6.unpinned", ("rows", 0, "agent", "version"), "0.0.0-fake"),
    "pin-harness": ("R14.pins", ("version_pins", CODEX), {}),
}


def alter(d, name):
    clause, path, value = CORE_MUTANTS[name]
    if name == "slots":
        value = d["rows"][1]["slot"]
    return changed(d, path, value)


def setUpModule():
    if SELECTED:
        original = b.assemble
        patch = mock.patch.object(b, "assemble", lambda *a, **k: alter(original(*a, **k), SELECTED))
        patch.start()
        PATCHES.append(patch)


def tearDownModule():
    while PATCHES:
        PATCHES.pop().stop()


class Assembly(unittest.TestCase):
    def get(self):
        self.assertTrue(hasattr(b, "assemble"), "the round's assembler is required")
        return b.assemble()

    def test_rows(self):
        self.assertEqual(core_problems(self.get()), [])
        self.assertEqual(study.ARMS, ("A", "C", "O", "G"))

    def test_accessors_red(self):
        d = self.get()
        for name, (clause, _, _) in CORE_MUTANTS.items():
            with self.subTest(name=name):
                self.assertIn(clause, core_problems(alter(d, name)))

    def test_ledger(self):
        d = self.get()
        rows = copy.deepcopy(d["rows"])
        for row in rows:
            row["agent"]["version"] = "0.0.0-fake"
            row["attempt"] = 1
        self.assertEqual(len(check_results.validate_ledger(rows)), 1260)
        for bad in (None, {}, {"harness": CLAUDE}):
            with self.subTest(agent=bad), self.assertRaises((ValueError, KeyError)):
                check_results.validate_ledger([dict(rows[0], agent=bad)])

    def test_local_modules(self):
        for mod in (b, study, variants, check_results, image_lock, run_take, harness_bookkeeping):
            self.assertTrue(Path(mod.__file__).resolve().is_relative_to(HERE.resolve()))


if __name__ == "__main__":
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        del sys.argv[index:index + 2]
    result = unittest.main(verbosity=2, exit=False).result
    print(f"test_build_draft: {result.testsRun} run, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped")
    raise SystemExit(not result.wasSuccessful())
