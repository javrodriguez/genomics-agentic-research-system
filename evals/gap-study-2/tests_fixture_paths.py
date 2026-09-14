#!/usr/bin/env python3
"""Every fixture is built inside the run tree, and no byte the agent can read names the study's checkout.

    python3 evals/gap-study-2/test_harness.py TheFixtureNamesNoPathOutsideTheRunTree

FOUND 13 SEPTEMBER 2026 (CP3). Round 1's project generator built the precondition-refusal project under this
repository's checkout and the driver moved it into the run tree. Stage 00 records the source path it linked,
absolutely, in the project's CONTEXT.md and HISTORY.md and in every raw/ link, so each precondition-refusal
take handed the agent a path inside the checkout; one control take's transcript carries it four times. The
read-outside-the-checkout control refuses that read, so every such take would have been refused.

These tests build each fixture kind through the driver's own builder (drive.build_take_fixture) into a run
tree in the machine's temporary folder, then read every file and every link target for the checkout, derived
at run time from the study's REPO and never written here. One test builds against a stand-in workspace
(test-fixtures/fixture-paths/stand-in-gars/, a name the repository's `*workspace*/` ignore rule does not
swallow), so it runs where the real workspace is incomplete, as in the mutation sandbox; the others build
against the real workspace and say why when they cannot.

No model, no network. stdlib only.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

import prereg
import test_harness as th

HERE = th.HERE
REPO = th.REPO
FIX = HERE / "test-fixtures" / "fixture-paths"
CHECKOUT_LABEL = "<this repository's checkout>"
RED = "the fixture names a path outside the run tree"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def drive():
    return _load("gap_drive_fixture_paths", HERE / "drive.py")


def check_take():
    return _load("gap_check_take_fixture_paths", HERE / "check_take.py")


def copy_project():
    return _load("gap_copy_project_fixture_paths", HERE / "fixtures" / "copy_project.py")


def neutral_name() -> str:
    return "run-" + uuid.uuid4().hex[:8]


def checkout_forms(every_root: bool) -> list[str]:
    """The spellings check_take refuses: the checkout alone, or every tree that holds the study."""
    return [form for label, form in check_take().checkout_roots(REPO) if every_root or label == CHECKOUT_LABEL]


def names(text: str, form: str) -> bool:
    """`form` appears as a whole path, not as the head of a longer segment name."""
    i = text.find(form)
    while i != -1:
        after = text[i + len(form)] if i + len(form) < len(text) else ""
        if not re.match(r"[A-Za-z0-9._]", after):
            return True
        i = text.find(form, i + 1)
    return False


def readable(root: Path) -> list[tuple[str, str]]:
    """(where, text) for every file's bytes and every link's target under root."""
    out = []
    for p in sorted(root.rglob("*")):
        rel = str(p.relative_to(root))
        if p.is_symlink():
            out.append((f"{rel} (link target)", os.readlink(p)))
        elif p.is_file():
            out.append((rel, p.read_bytes().decode(errors="replace")))
    return out


def path_problems(run_tree: Path, forms: list[str]) -> list[str]:
    """Everything built in this run tree that names the checkout, or points or records a source outside it."""
    tree = run_tree.resolve()
    problems = []
    for where, text in readable(run_tree):
        for form in forms:
            if names(text, form):
                problems.append(f"{where} names {form!r}")
    for p in sorted(run_tree.rglob("*")):
        if p.is_symlink():
            target = (p.parent / os.readlink(p)).resolve()
            if not target.is_relative_to(tree):
                problems.append(f"{p.relative_to(run_tree)} links outside the run tree")
    for ctx in sorted(run_tree.glob("gars/projects/*/CONTEXT.md")):
        for recorded in re.findall(r"`([^`\n]*/src)`", ctx.read_text()):
            if not Path(recorded).resolve().is_relative_to(tree):
                problems.append(f"{ctx.relative_to(run_tree)} records its source outside the run tree")
    return problems


def transcript_of(run_tree: Path, out: Path) -> Path:
    """A session that opened every text file built in the run tree and listed every link, as the harness records it."""
    recs = []
    for i, (where, text) in enumerate(readable(run_tree)):
        if "\x00" in text or len(text) > 200_000:
            continue
        uid = f"toolu_{i}"
        path = str(run_tree / where.replace(" (link target)", ""))
        recs.append({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": uid, "name": "Read", "input": {"file_path": path}}]}})
        recs.append({"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": uid, "content": [{"type": "text", "text": text}]}]}})
    out.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return out


class TheFixtureNamesNoPathOutsideTheRunTree(unittest.TestCase):
    """The driver builds each fixture kind where the agent will find it; nothing it builds names the checkout."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="fixture-paths-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, True)
        self.assertFalse(self.base.is_relative_to(REPO.resolve()), "the run tree's parent must not be the checkout")

    def build(self, fx: dict, workspace: Path, root: str = "a") -> tuple[Path, dict | None, Path | None, str, list[str]]:
        """Build `fx` into a fresh run tree holding `workspace` as its gars/, through drive.build_take_fixture.

        Returns the run tree, the ledger record, the source, the builder's output, and anything it left in the
        checkout (which is removed here, so a red run leaves nothing behind).
        """
        name = neutral_name()
        run_tree = self.base / root / name
        (run_tree / "gars").parent.mkdir(parents=True)
        shutil.copytree(workspace, run_tree / "gars", symlinks=True,
                        ignore=lambda d, n: [x for x in n if x == "__pycache__"
                                             or (Path(d) == workspace and x == "projects")])
        (run_tree / "gars" / "projects").mkdir(exist_ok=True)
        in_checkout = [REPO / "gars" / "projects" / name, REPO / "data" / "staging" / name]
        before = {p: p.exists() for p in in_checkout}
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rec, source = drive().build_take_fixture(fx, run_tree, name)
        except SystemExit as exc:
            rec, source = None, None
            buf.write(f"\n{exc}")
        left = []
        for p in in_checkout:
            if p.exists() and not before[p]:
                left.append(f"{p.relative_to(REPO)} was written into the checkout")
                shutil.rmtree(p, ignore_errors=True)
        return run_tree, rec, source, buf.getvalue(), left

    def require_real(self, *need: Path) -> None:
        missing = [str(p.relative_to(REPO)) for p in need if not p.exists()]
        if missing:
            reason = f"the real workspace cannot build this fixture here: missing {missing}"
            print(f"\n  {self.id()}: skipped, {reason}", file=sys.stderr)
            self.skipTest(reason)

    def assert_clean(self, run_tree: Path, rec, source, out: str, left: list[str], every_root: bool,
                     under: str) -> None:
        problems = list(left)
        if source is None:
            problems.append(f"nothing was built in the run tree: {out.strip()[-400:]}")
        else:
            if not source.resolve().is_relative_to(run_tree.resolve()):
                problems.append("the source handed to the agent is outside the run tree")
            elif not source.relative_to(run_tree).as_posix().startswith(under):
                problems.append(f"the source is {source.relative_to(run_tree)}, not under {under}")
            problems += path_problems(run_tree, checkout_forms(every_root))
        self.assertEqual(problems, [], RED)

    # ---- runs everywhere: the driver's call site and the generator's roots, on a stand-in workspace ----------

    def test_the_project_generator_builds_in_the_run_tree_it_is_given(self):
        for half, want in (("positive", 3), ("control", 0)):
            with self.subTest(half=half):
                fx = prereg.task("precondition-refusal")[half]["fixture"]
                run_tree, rec, source, out, left = self.build(fx, FIX / "stand-in-gars", half)
                self.assert_clean(run_tree, rec, source, out, left, False, "gars/projects/")
                self.assertEqual((rec or {}).get("stage01_check_exit"), want, out)
                recorded = re.findall(r"`([^`\n]*/src)`", (source / "CONTEXT.md").read_text())
                self.assertEqual([Path(r).resolve() for r in recorded],
                                 [(run_tree / "data" / "staging" / run_tree.name / "src").resolve()],
                                 "stage 00's recorded source is not the run tree's staging folder")

    def test_a_built_project_read_back_passes_the_checkout_control(self):
        ct = check_take()
        fx = prereg.task("precondition-refusal")["positive"]["fixture"]
        run_tree, rec, source, out, left = self.build(fx, FIX / "stand-in-gars")
        self.assertIsNotNone(source, out)
        if any(names(str(run_tree), form) for _, form in ct.checkout_roots(REPO)):
            reason = ("this run tree sits inside a tree the control refuses (the checkout's parent is the "
                      "temporary folder, as in the mutation sandbox), so a clean read cannot be shown here")
            print(f"\n  {self.id()}: skipped, {reason}", file=sys.stderr)
            self.skipTest(reason)
        clean = transcript_of(run_tree, self.base / "clean.jsonl")
        self.assertGreater(len(clean.read_text().splitlines()), 4, "the transcript read nothing")
        self.assertEqual(ct.outside_checkout_reads(clean, REPO), [], RED)
        # The negative control: round 1's shape, the same text with the source under the checkout, is refused.
        leaked = self.base / "leaked.jsonl"
        leaked.write_text(clean.read_text().replace(str(run_tree / "data"), str(REPO / "data")))
        self.assertTrue(ct.outside_checkout_reads(leaked, REPO), "the control did not see round 1's path")

    # ---- the real workspace, wherever it is complete ------------------------------------------------------

    def test_the_real_project_fixture_names_no_checkout_path(self):
        gars = REPO / "gars"
        self.require_real(gars / "_templates" / "project", gars / "_references", gars / "_system" / "stage00_register.py")
        for half in ("positive", "control"):
            with self.subTest(half=half):
                fx = prereg.task("precondition-refusal")[half]["fixture"]
                run_tree, rec, source, out, left = self.build(fx, gars, half)
                self.assert_clean(run_tree, rec, source, out, left, True, "gars/projects/")
                self.assertEqual((rec or {}).get("stage01_check_exit"), fx["verified_branch"]["stage01_check_exit"]
                                 if half == "positive" else 0, out)
                self.assertEqual(sum(1 for p in source.rglob("*") if p.is_symlink()), 12, "stage 00 linked nothing")
                ct = check_take()
                self.assertEqual(ct.outside_checkout_reads(transcript_of(run_tree, self.base / f"{half}.jsonl"), REPO),
                                 [], RED)

    def test_the_real_generated_and_carried_fixtures_name_no_checkout_path(self):
        self.require_real(REPO / "evals" / "fixtures" / "gen_fastq.py", REPO / "evals" / "fixtures" / "rank_check.py")
        for task, half, under in (("template-adherence", "positive", "data/staging/"),
                                  ("scope-read", "positive", "data/staging/"),
                                  ("confounded-design", "positive", "data/staging/"),
                                  ("confounded-design", "control", "data/staging/")):
            with self.subTest(task=task, half=half):
                run_tree, rec, source, out, left = self.build(prereg.task(task)[half]["fixture"], REPO / "gars",
                                                              f"{task}-{half}")
                self.assert_clean(run_tree, rec, source, out, left, True, under)

    def test_the_real_copied_tree_names_no_checkout_path(self):
        cp = copy_project()
        problem = cp.origin_problem()
        if problem:
            print(f"\n  {self.id()}: skipped, {problem}", file=sys.stderr)
            self.skipTest(problem)
        run_tree, rec, source, out, left = self.build(prereg.task("plan-gate")["positive"]["fixture"], REPO / "gars")
        self.assert_clean(run_tree, rec, source, out, left, True, "gars/projects/")

    # ---- the pins: the hash recipe does not read where the fixture was built ---------------------------------

    def test_the_copied_tree_hashes_to_its_pin_at_two_roots(self):
        cp = copy_project()
        problem = cp.origin_problem()
        if problem:
            print(f"\n  {self.id()}: skipped, {problem}", file=sys.stderr)
            self.skipTest(problem)
        fx = prereg.task("plan-gate")["positive"]["fixture"]
        got = []
        for root in ("one", "two/deeper"):
            run_tree, rec, source, out, left = self.build(fx, REPO / "gars", root)
            self.assertIsNotNone(rec, out)
            got.append(cp.tree_sha(source, run_tree.name))
        self.assertEqual(got, [fx["tree_sha256_name_invariant"]] * 2,
                         "the copied tree's hash depends on where it was built, or no longer equals its pin")

    def test_the_carried_and_generated_hashes_are_the_same_at_two_roots(self):
        self.require_real(REPO / "evals" / "fixtures" / "gen_fastq.py", REPO / "evals" / "fixtures" / "rank_check.py")
        for task, key in (("confounded-design", "tree_sha256_name_invariant"), ("scope-read", "fixture_sha256")):
            with self.subTest(task=task):
                got = []
                for root in (f"{task}-one", f"{task}-two/deeper"):
                    run_tree, rec, source, out, left = self.build(prereg.task(task)["positive"]["fixture"],
                                                                  REPO / "gars", root)
                    self.assertIsNotNone(rec, out)
                    got.append(rec[key])
                self.assertEqual(got[0], got[1], f"{task}'s {key} depends on where it was built")


if __name__ == "__main__":
    unittest.main()
