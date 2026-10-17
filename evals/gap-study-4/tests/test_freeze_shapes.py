#!/usr/bin/env python3
"""Lane vendor-admission T3: the freeze refuses an arm whose adapter reads documented shapes only.

Ruling Q-3 (glitch-2f, 12 Oct 2026; codex_adapter.py:9-14, gemini_adapter.py:9-14): build arms O and G on the
documented stream shapes now, and the freeze refuses any arm whose adapter has not been re-tested on a stream recorded
at its first real walk. glitch-b5's lane vendor-admission (16 Oct 2026), task T3, builds that refusal: freeze.main
refuses while a design row's harness is codex or gemini and that adapter's SHAPES_SOURCE is not "recorded", naming the
arm; nothing is written.

  FS-draft     on the committed draft (arms O and G, both adapters "documented") the check names both arms.
  FS-main      freeze.main on a fixture draft with an O row, a G row, or both refuses at "documented" naming each arm,
               and passes once that adapter's SHAPES_SOURCE is patched to "recorded"; a claude-code-only draft passes.
  FS-docs      each adapter's SHAPES_SOURCE paragraph says freeze.py now refuses its arm, never that the refusal is
               owed to a later slice (round-2 ruling 2).
  FS-witness   freeze.py compiled in memory without the check's call, or with its comparison disabled, goes red.

freeze.main runs against a temporary folder: git, the review, the pins, prepare and the writer are fakes (the shape of
test_holdout_digests' FreezeHarness). No take, model, container or network; no freeze output is written.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import codex_adapter  # noqa: E402
import freeze  # noqa: E402
import gemini_adapter  # noqa: E402

ADAPTERS = {"O": codex_adapter, "G": gemini_adapter}


def row(arm: str) -> dict:
    harness = {"A": "claude-code", "O": "codex", "G": "gemini"}[arm]
    return {"arm": arm, "task": "synthetic-task", "half": "trap", "wording": "w1", "repeat": 1, "pressure": None,
            "model": f"synthetic-{arm}-model", "agent": {"harness": harness, "version": "0.0.1"},
            "half_cell": f"c-{arm}", "slot": f"s-{arm}"}


def draft(arms) -> dict:
    return {"status": "DRAFT", "tasks": [], "rows": [row(a) for a in arms]}


def fake_git(*args):
    return {("remote",): (0, ""), ("status", "--porcelain"): (0, ""),
            ("rev-parse", "HEAD"): (0, "b" * 40)}.get(args, (1, "no such fake git call"))


def fake_prepare(d, *, review, parent, pins, frozen_at):
    return dict(copy.deepcopy(d), status="FROZEN", frozen_at=frozen_at, frozen_at_commit_parent=parent,
                pre_freeze_review_commit=review, take_order_seed=review, take_order=[], pinned_files=pins)


def run_main(mod, d: dict) -> tuple[int, str, list]:
    """(exit code, stdout, frozen files written) of mod.main, previewing and then writing a rehearsal freeze."""
    written, outs, codes = [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "prereg-draft.json").write_text(json.dumps(d))
        patches = ((mod, "HERE", tmp), (mod, "REPO", tmp), (mod, "DRAFT", tmp / "prereg-draft.json"),
                   (mod, "PINNED", []), (mod, "git", fake_git), (mod, "prepare", fake_prepare),
                   (mod, "review_file_problems", lambda commit: ([], "review/prefreeze-1.md")),
                   (mod, "study_tree_sha", lambda *a, **k: "c" * 64),
                   (mod, "write_outputs", lambda frozen: written.append(frozen) or ()),
                   (mod, "owned_paths", lambda *a, **k: []),
                   (mod.copy_manifest, "problems", lambda *a, **k: []))
        (tmp / "review").mkdir()
        (tmp / "review" / "prefreeze-1.md").write_text("synthetic review\n")
        for argv in (["--review-commit", "a" * 40, "--rehearsal"], ["--review-commit", "a" * 40, "--rehearsal",
                                                                   "--write"]):
            out = io.StringIO()
            with contextlib.ExitStack() as stack:
                for module, name, value in patches:
                    stack.enter_context(mock.patch.object(module, name, value))
                stack.enter_context(contextlib.redirect_stdout(out))
                codes.append(mod.main(argv))
            outs.append(out.getvalue())
    return max(codes), "".join(outs), written


def shapes(**recorded):
    """Patch each named arm's adapter (O, G) to SHAPES_SOURCE "recorded"."""
    stack = contextlib.ExitStack()
    for arm in recorded:
        stack.enter_context(mock.patch.object(ADAPTERS[arm], "SHAPES_SOURCE", "recorded"))
    return stack


def main_problems(mod) -> list:
    out = []
    for arms in (("A", "O"), ("A", "G"), ("A", "O", "G"), ("O",), ("G",)):
        vendors = [a for a in arms if a in ADAPTERS]
        code, text, written = run_main(mod, draft(arms))
        if code != 1 or written or "REFUSE" not in text:
            out.append(f"{arms} at documented: not refused (exit {code}, {len(written)} written)")
        for a in vendors:
            if f"arm {a} " not in text:
                out.append(f"{arms} at documented: the refusal does not name arm {a}: {text[:200]!r}")
        with shapes(**{a: True for a in vendors}):
            code, text, written = run_main(mod, draft(arms))
        if code != 0 or len(written) != 1:
            out.append(f"{arms} at recorded: refused (exit {code}): {text[:200]!r}")
        if len(vendors) == 2:
            with shapes(O=True):
                code, text, written = run_main(mod, draft(arms))
            if code != 1 or written or "arm G " not in text or "arm O " in text:
                out.append(f"{arms} with O recorded: G not refused alone: {text[:200]!r}")
    code, text, written = run_main(mod, draft(("A",)))
    if code != 0 or len(written) != 1:
        out.append(f"a claude-code-only draft is refused: {text[:200]!r}")
    return out


class TheFreezeRefusesDocumentedShapes(unittest.TestCase):
    def test_fs_the_adapters_are_documented_on_this_head(self):
        self.assertEqual((codex_adapter.SHAPES_SOURCE, gemini_adapter.SHAPES_SOURCE), ("documented", "documented"))

    def test_fs_draft_the_committed_draft_names_both_arms(self):
        committed = json.loads((HERE / "prereg-draft.json").read_text())
        got = freeze.unrecorded_shapes_problem(committed)
        self.assertIsNotNone(got)
        for words in ("arm O (codex)", "arm G (gemini)", "'documented'", "recorded"):
            self.assertIn(words, got)
        with shapes(O=True, G=True):
            self.assertIsNone(freeze.unrecorded_shapes_problem(committed))
        self.assertIsNone(freeze.unrecorded_shapes_problem(draft(("A",))))
        self.assertIsNone(freeze.unrecorded_shapes_problem({"tasks": []}))

    def test_fs_main_refuses_at_documented_and_passes_at_recorded(self):
        self.assertEqual(main_problems(freeze), [])

    def test_fs_docs_the_adapters_name_the_refusal_this_lane_built(self):
        # round-2 ruling 2 (glitch-b5): the SHAPES_SOURCE paragraph of each adapter's docstring names freeze.py's
        # refusal (T3) and no longer says it is owed to a later slice
        for mod, arm in ((codex_adapter, "arm O"), (gemini_adapter, "arm G")):
            doc = " ".join(mod.__doc__.split())
            with self.subTest(adapter=mod.__name__):
                self.assertNotIn("owed to a later slice", doc)
                for words in ("freeze.py now refuses a design row of this harness", f"({arm})",
                              'while SHAPES_SOURCE is not "recorded"', "freeze.unrecorded_shapes_problem"):
                    self.assertIn(words, doc)

    def test_fs_check_mode_is_unchanged(self):
        # freeze.py --check (a checks.d gate) checks the copy record and the draft's holdout fields only
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(freeze.main(["--check"]), 0, out.getvalue())


def mutant(old: str, new: str):
    src = Path(freeze.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutation site occurs {src.count(old)} times in freeze.py: {old!r}")
    m = types.ModuleType("freeze_mutant")
    m.__file__ = freeze.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), freeze.__file__ + " (witness)", "exec"), m.__dict__)  # noqa: S102
    finally:
        del sys.modules[m.__name__]
    return m


WITNESSES = {
    "the check's call deleted": ("        problem = unrecorded_shapes_problem(draft)\n        if problem:\n"
                                 "            raise ValueError(problem)\n", ""),
    "the comparison disabled": ("        if source != RECORDED_SHAPES:", "        if False:"),
}


class Witnesses(unittest.TestCase):
    def test_fs_witness_each_mutant_goes_red(self):
        for name, (old, new) in WITNESSES.items():
            with self.subTest(witness=name):
                self.assertNotEqual(main_problems(mutant(old, new)), [], f"witness {name} stayed green")


if __name__ == "__main__":
    unittest.main()
