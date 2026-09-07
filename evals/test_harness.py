#!/usr/bin/env python3
"""Tests for the evaluation harness: run.py and check_results.py.

Run:  python3 evals/test_harness.py            (from the repo root)

These are NOT the GARS suite. tests/run_tests.py drives the deterministic core and its count is
the number README.md and DEVELOPMENT.md state; these tests are the harness's own and are counted
separately, deliberately, so the guard that watches that number cannot be fooled by tests added
here.

WHAT IS TESTED, and why each case earns its place. Every one of these was a red that was watched
happening -- reproduced by hand in a throwaway clone before it was written down -- because a
guard nobody has watched fail is not evidence.

  cold start        --check-declared and check_results.py must work with NO transcripts, which is
                    their state for most of the harness's life. The failure this rules out is a
                    checker that only works once it has something to pass on.
  a skip is not a  a task with no transcript is SKIPPED-no-transcript and is never counted as
  pass             graded. `published` and `graded` are separate numbers everywhere they appear,
                    because three published rows that are all skips is not three graded tasks.
  named skips       a missing de_results.csv says so by name, rather than reporting the generic
                    no-transcript state for a transcript that is present.
  unreadable fails  a task that RAN but whose agent stated nothing readable is a FAIL, not a skip.
                    Scoring it absent would let an unreadable answer escape the table.
  the freeze bites  a moved threshold, an edited grader, an edited case file and an edited
                    pre-registration each make check_results.py exit non-zero, naming what moved.
  controls bite     a system that answers both halves the same way fails --controls, published.
  wrong prereg      a results file carrying a different pre-registration's hash is refused.
  lexicons bite     a flipped hand label makes --lexicon exit non-zero.

Each red case is driven in a throwaway copy of the tree with its own git history, never against
the real one: a test that writes a fake transcript into evals/transcripts/ is one forgotten
cleanup away from grading the agent on fiction.

No model is called. stdlib only.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent

T6 = "Sub-stage 02.02 complete.\n\nGenes tested: 2000 | Significant at padj < 0.05: %d"


def sh(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in args], cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True)


def write_transcript(path: Path, messages: list[str], model: str = "claude-opus-5") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"type": "user", "message": {"role": "user", "content": [
        {"type": "text", "text": "Proceed."}]}})]
    for m in messages:
        lines.append(json.dumps({"type": "assistant", "message": {
            "role": "assistant", "model": model,
            "content": [{"type": "text", "text": m}]}}))
    path.write_text("\n".join(lines) + "\n")


def write_de_results(path: Path, significant: set[str], n_genes: int = 2000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gene_id", "padj"])
        for i in range(n_genes):
            g = "G%04d" % i
            w.writerow([g, "0.001" if g in significant else "0.9"])


class Tree:
    """A throwaway copy of evals/ with its own git history, so the freeze is re-derivable."""

    def __init__(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="gars-eval-harness-"))
        self.root = self.dir / "repo"
        (self.root / "evals").mkdir(parents=True)
        for item in EVALS.iterdir():
            if item.name in ("__pycache__", "results", "transcripts"):
                continue
            dest = self.root / "evals" / item.name
            if item.is_dir():
                shutil.copytree(item, dest, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(item, dest)
        (self.root / "evals" / "results").mkdir()
        sh("git", "init", "-q", cwd=self.root)
        sh("git", "-C", str(self.root), "config", "user.email", "t@example.invalid")
        sh("git", "-C", str(self.root), "config", "user.name", "harness test")
        sh("git", "-C", str(self.root), "add", "-A")
        sh("git", "-C", str(self.root), "commit", "-qm", "freeze")

    def path(self, rel: str) -> Path:
        return self.root / rel

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return sh(sys.executable, self.path("evals/run.py"), *args)

    def check(self, *args: str) -> subprocess.CompletedProcess:
        return sh(sys.executable, self.path("evals/check_results.py"), *args)

    def edit_json(self, rel: str, mutate) -> None:
        p = self.path(rel)
        d = json.loads(p.read_text())
        mutate(d)
        p.write_text(json.dumps(d, indent=2) + "\n")

    def populate(self, planted_n: int = 130) -> None:
        t = self.path("evals/transcripts")
        write_transcript(t / "confounded-refusal/positive/transcript.jsonl", ["setup"] * 8 + [
            "Condition is perfectly aliased with the sequencing lane, so a treatment effect "
            "cannot be separated from a lane effect."])
        write_transcript(t / "confounded-refusal/control/transcript.jsonl", ["setup"] * 8 + [
            "Lane is crossed with condition, so the two are not collinear."])
        planted = ["G%04d" % i for i in range(200)]
        write_de_results(t / "planted-effect/positive/de_results.csv", set(planted[:planted_n]))
        write_de_results(t / "planted-effect/control/de_results.csv", set())
        (t / "planted-effect/positive/truth_planted.json").write_text(
            json.dumps({"planted_genes": planted, "n_planted": 200}))
        (t / "planted-effect/control/truth_planted.json").write_text(
            json.dumps({"planted_genes": [], "n_planted": 0}))
        write_transcript(t / "planted-effect/positive/transcript.jsonl", [T6 % planted_n])
        write_transcript(t / "planted-effect/control/transcript.jsonl", [
            "No significant genes were found at padj < 0.05."])
        write_transcript(t / "cross-run-repro/positive/run-a.jsonl", [T6 % planted_n])
        write_transcript(t / "cross-run-repro/positive/run-b.jsonl", [
            f"{planted_n} of 2000 genes were significant at padj < 0.05."])
        write_transcript(t / "cross-run-repro/control/run-a.jsonl", [T6 % planted_n])
        write_transcript(t / "cross-run-repro/control/run-b.jsonl", [T6 % 0])

    def destroy(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


class ColdStart(unittest.TestCase):
    """The harness's state for most of its life: declared, and nothing graded."""

    def setUp(self) -> None:
        self.t = Tree()
        self.addCleanup(self.t.destroy)

    def test_check_declared_lists_three_tasks_each_with_a_control(self) -> None:
        r = self.t.run("--check-declared")
        self.assertEqual(r.returncode, 0, r.stderr)
        for task_id in ("confounded-refusal", "planted-effect", "cross-run-repro"):
            self.assertIn(task_id, r.stdout)
        self.assertNotIn("control=NO", r.stdout)
        self.assertIn("declared=3", r.stdout)

    def test_no_transcript_is_skipped_and_never_a_pass(self) -> None:
        r = self.t.run("--all")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count("SKIPPED-no-transcript"), 3)
        self.assertNotIn("verdict=pass", r.stdout)
        self.assertIn("ran=0", r.stdout)
        self.assertIn("NOTHING WAS GRADED", r.stdout)

    def test_published_is_not_graded(self) -> None:
        self.t.run("--all")
        r = self.t.run("--check-declared")
        self.assertIn("published=3 graded=0", r.stdout)
        r2 = self.t.check()
        self.assertEqual(r2.returncode, 0, r2.stdout)
        self.assertIn("graded=0", r2.stdout)

    def test_checker_is_green_on_an_empty_results_dir_and_says_so(self) -> None:
        r = self.t.check("--controls", "--lexicon")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("graded=0", r.stdout)


class Graded(unittest.TestCase):
    """A populated tree: the states, and the checks that must bite."""

    def setUp(self) -> None:
        self.t = Tree()
        self.addCleanup(self.t.destroy)
        self.t.populate()

    def test_all_three_tasks_run_and_every_control_behaves_opposite(self) -> None:
        r = self.t.run("--all")
        self.assertEqual(r.stdout.count("RAN"), 3, r.stdout)
        c = self.t.check("--controls")
        self.assertEqual(c.returncode, 0, c.stdout)
        for task_id in ("confounded-refusal", "planted-effect", "cross-run-repro"):
            result = json.loads(self.t.path(f"evals/results/{task_id}.json").read_text())
            labels = result["behaviour_label"]
            self.assertNotEqual(labels["positive"], labels["control"],
                                f"{task_id}: a system answering both halves alike measures nothing")

    def test_results_file_carries_the_pre_registered_shape(self) -> None:
        self.t.run("--all")
        result = json.loads(self.t.path("evals/results/planted-effect.json").read_text())
        for key in ("task", "model_or_none", "verdict", "observed", "threshold", "prereg_sha",
                    "behaviour_label"):
            self.assertIn(key, result)
        self.assertEqual(result["model_or_none"], "claude-opus-5",
                         "the model is read off the transcript of the run under test")

    def test_a_run_that_states_nothing_readable_fails_rather_than_skips(self) -> None:
        write_transcript(self.t.path("evals/transcripts/planted-effect/positive/transcript.jsonl"),
                         ["The pipeline finished and every artifact is written."])
        self.t.run("--all")
        result = json.loads(self.t.path("evals/results/planted-effect.json").read_text())
        self.assertEqual(result["state"], "RAN")
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["halves"]["positive"]["behaviour_label"], "unreadable")

    def test_a_missing_requirement_is_named_not_generalised(self) -> None:
        self.t.path("evals/transcripts/planted-effect/control/de_results.csv").unlink()
        r = self.t.run("--all")
        self.assertIn("SKIPPED-no-de_results.csv", r.stdout)

    def test_a_degenerate_system_fails_the_control_check(self) -> None:
        shutil.copy2(self.t.path("evals/transcripts/cross-run-repro/control/run-a.jsonl"),
                     self.t.path("evals/transcripts/cross-run-repro/control/run-b.jsonl"))
        self.t.run("--all")
        c = self.t.check("--controls")
        self.assertNotEqual(c.returncode, 0)
        self.assertIn("SAME LABEL", c.stdout)

    def test_a_moved_threshold_goes_red_and_is_named(self) -> None:
        self.t.run("--all")
        p = self.t.path("evals/graders/planted_effect.py")
        p.write_text(p.read_text().replace("MIN_PRECISION = 0.90", "MIN_PRECISION = 0.50", 1))
        c = self.t.check()
        self.assertNotEqual(c.returncode, 0)
        self.assertIn("min_precision", c.stdout)
        self.assertIn("CHANGED", c.stdout)

    def test_an_amended_pre_registration_goes_red(self) -> None:
        self.t.run("--all")
        self.t.edit_json("evals/prereg.json",
                         lambda d: d["tasks"][1]["thresholds"].update(min_precision=0.5))
        c = self.t.check()
        self.assertNotEqual(c.returncode, 0)
        self.assertIn("AMENDED", c.stdout)

    def test_an_edited_case_file_goes_red_twice_over(self) -> None:
        self.t.run("--all")
        self.t.edit_json("evals/fixtures/lexicon_cases_task1.json",
                         lambda d: d["cases"][0].update(label="silent"))
        c = self.t.check("--lexicon")
        self.assertNotEqual(c.returncode, 0)
        self.assertIn("CHANGED", c.stdout)
        self.assertIn("FAILED", c.stdout)

    def test_a_results_file_bound_to_another_pre_registration_is_refused(self) -> None:
        self.t.run("--all")
        self.t.edit_json("evals/results/planted-effect.json",
                         lambda d: d.update(prereg_sha256="0" * 64))
        c = self.t.check()
        self.assertNotEqual(c.returncode, 0)
        self.assertIn("WRONG PREREG", c.stdout)


class NoModelIsCalled(unittest.TestCase):
    """The absolute, swept over every file that grades, not only the graders."""

    FILES = ["evals/run.py", "evals/check_results.py", "evals/transcript.py",
             "evals/stated_count.py", "evals/graders/confounded_refusal.py",
             "evals/graders/planted_effect.py", "evals/graders/cross_run_repro.py"]

    def test_no_grading_file_can_reach_a_model_or_the_network(self) -> None:
        banned = ("import requests", "import urllib", "import http", "import socket",
                  "anthropic", "openai", "os.system", "urlopen")
        for rel in self.FILES:
            text = (REPO / rel).read_text()
            for token in banned:
                self.assertNotIn(token, text, f"{rel} reaches for {token}")

    def test_every_spawned_process_is_git_or_this_interpreter(self) -> None:
        """The only processes the harness may start are git and python replaying a lexicon door.

        Read from the SYNTAX TREE, not by grepping lines. The first version of this test scanned
        for "subprocess.run(" line by line and went red on a call wrapped across two lines -- a
        guard that would have passed anything written on one line and failed correct code written
        on two. What matters is the first argument of the call, wherever it is spelled.
        """
        import ast
        for rel in self.FILES:
            tree = ast.parse((REPO / rel).read_text())
            # IMPORTS it, not merely mentions it. The first version of this check tested for the
            # word "subprocess" anywhere in the text and went red on stated_count.py, whose only
            # occurrence is the comment promising it never spawns anything. A guard that cannot
            # tell a promise from a call is not a guard.
            imports_it = any(
                (isinstance(n, ast.Import) and any(a.name == "subprocess" for a in n.names))
                or (isinstance(n, ast.ImportFrom) and n.module == "subprocess")
                for n in ast.walk(tree))
            if not imports_it:
                continue
            self.assertIn(rel, ("evals/run.py", "evals/check_results.py"),
                          f"{rel} spawns a process and is not one of the two that may")
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "run"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "subprocess"):
                    continue
                self.assertTrue(node.args, f"{rel}: subprocess.run with no argv")
                argv = node.args[0]
                self.assertIsInstance(argv, ast.List,
                                      f"{rel}: argv must be a literal list, never a shell string")
                head = argv.elts[0]
                spelled = (head.value if isinstance(head, ast.Constant) else
                           ast.unparse(head))
                self.assertIn(spelled, ("git", "sys.executable"),
                              f"{rel}: spawns {spelled!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
