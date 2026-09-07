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
import re
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
            # not-run.json is a fact about the REAL tree, not about a synthetic one: copying it
            # would make every populated test's tasks come back declared-unrunnable. The not-run
            # path gets its own class below, which writes the declaration deliberately.
            if item.name in ("__pycache__", "results", "transcripts", "not-run.json"):
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


class NotRunDeclaration(unittest.TestCase):
    """A task the system cannot accept: published with its requirement named, never graded.

    The declaration is the easiest place in the whole design to hide a failure, because nothing
    about a blank row looks like a verdict. So these tests drive both directions: the declared
    task must never reach a grader, and a declaration whose evidence stops holding must go RED
    rather than stay quietly blank.
    """

    EVIDENCE = ["python3", "evals/freeze.py"]

    def setUp(self) -> None:
        self.t = Tree()
        self.addCleanup(self.t.destroy)
        self.t.populate()

    def declare(self, command: list, expect_exit: int = 0, expect_json: dict | None = None) -> None:
        (self.t.path("evals/not-run.json")).write_text(json.dumps({
            "tasks": {"planted-effect": {
                "missing_requirement": "a made-up requirement for this test",
                "reason": "written by the test suite",
                "evidence": {"command": command, "expect_exit": expect_exit,
                             "expect_json": expect_json or {}}}}}, indent=2))

    def test_a_declared_task_is_never_graded_and_names_its_requirement(self) -> None:
        self.declare(self.EVIDENCE)
        r = self.t.run("--all")
        self.assertIn("SKIPPED-a-made-up-requirement-for-this-test", r.stdout)
        self.assertNotIn("planted-effect       RAN", r.stdout)
        result = json.loads(self.t.path("evals/results/planted-effect.json").read_text())
        self.assertEqual(result["behaviour_label"], {})
        self.assertIn("not_run", result)
        self.assertNotIn(result["verdict"], ("pass", "fail"))

    def test_a_declaration_whose_evidence_stops_holding_goes_red(self) -> None:
        self.declare(self.EVIDENCE, expect_exit=99)
        c = self.t.check()
        self.assertNotEqual(c.returncode, 0)
        self.assertIn("NOW RUNS?", c.stdout)

    def test_an_out_of_bounds_evidence_command_is_refused(self) -> None:
        """The declaration may not become a way to run anything it names."""
        for command in (["/bin/sh", "-c", "echo pwned"],
                        ["python3", "/etc/passwd"],
                        ["python3", "../../../etc/hosts"],
                        ["curl", "http://example.invalid"]):
            with self.subTest(command=command):
                self.declare(command)
                c = self.t.check()
                self.assertNotEqual(c.returncode, 0, f"{command} was not refused")
                self.assertIn("REFUSED", c.stdout)


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
                if isinstance(argv, ast.Name):
                    # check_results.py runs the evidence command a not-run declaration names, so
                    # its argv cannot be a literal this test could read. That is precisely why
                    # check_not_run() constrains it at RUNTIME -- this interpreter, a script
                    # inside the repository, nothing else -- and refuses anything else before
                    # spawning. The guard is asserted by
                    # NotRunDeclaration.test_an_out_of_bounds_evidence_command_is_refused.
                    self.assertEqual(rel, "evals/check_results.py",
                                     f"{rel}: only the checker may spawn a non-literal argv")
                    self.assertEqual(argv.id, "argv",
                                     "the spawned list must be the guarded one")
                    continue
                self.assertIsInstance(argv, ast.List,
                                      f"{rel}: argv must be a literal list, never a shell string")
                head = argv.elts[0]
                spelled = (head.value if isinstance(head, ast.Constant) else
                           ast.unparse(head))
                if spelled == "argv[0]":
                    # check_results.py runs the evidence command a not-run declaration names.
                    # The argv is not a literal, so this test cannot read it -- which is exactly
                    # why check_not_run() constrains it at RUNTIME to this interpreter running a
                    # script inside the repository, and refuses anything else. That guard is
                    # asserted by NotRunDeclaration.test_an_out_of_bounds_evidence_command_is_refused.
                    self.assertEqual(rel, "evals/check_results.py")
                    continue
                self.assertIn(spelled, ("git", "sys.executable"),
                              f"{rel}: spawns {spelled!r}")


class PublishedTables(unittest.TestCase):
    """Invariant sweeps over the two published tables. These are absolutes, so they are swept.

    Every rule here is one the goal states without exception, and a rule checked once by eye on
    the day it was written is a rule that holds until the next edit. CI runs these, so the two
    tables cannot quietly merge and the banned vocabulary cannot quietly return.
    """

    EVALS_MD = REPO / "docs/EVALS.md"
    RESULTS_MD = REPO / "docs/RESULTS.md"

    FIRST_LINE = ("This table grades agent behaviour on 3 pre-registered tasks. It is not the "
                  "reproduction campaign, which scores pipeline output and lives in "
                  "docs/RESULTS.md.")

    # Words the goal bans from any public artifact, and the reason each is banned: they assert a
    # standing this work does not have, or a capability wider than three tasks.
    BANNED = ["compliant", "gxp", "production-ready", "named users",
              "benchmarking framework", "evaluation harness"]

    TASK_IDS = ["confounded-refusal", "planted-effect", "cross-run-repro"]

    def test_the_disclaimer_is_the_first_line_verbatim(self) -> None:
        first = self.EVALS_MD.read_text().splitlines()[0]
        self.assertEqual(first, self.FIRST_LINE)

    def test_no_banned_vocabulary(self) -> None:
        low = self.EVALS_MD.read_text().lower()
        for word in self.BANNED:
            self.assertNotIn(word, low, f"banned in a public artifact: {word!r}")

    def test_no_rate_over_three_tasks(self) -> None:
        """With n=3 the table reports outcomes. A percentage suggests a precision it cannot carry."""
        text = self.EVALS_MD.read_text()
        self.assertEqual(re.findall(r"\d+(?:\.\d+)?\s*%", text), [])

    def test_the_two_tables_share_no_project(self) -> None:
        """Swept against the slugs RESULTS.md actually contains, never a list typed out here.

        A hard-coded slug list would go stale the moment a campaign project is added, and would
        then pass while the thing it guards against was happening.
        """
        campaign = set(re.findall(r"`((?:dko|cuttag)[a-z0-9-]+)`", self.RESULTS_MD.read_text()))
        self.assertTrue(campaign, "no campaign slug found — this sweep would pass vacuously")
        evals_text = self.EVALS_MD.read_text()
        for slug in campaign:
            self.assertNotIn(slug, evals_text, f"campaign project {slug!r} in the Layer B table")
        results_text = self.RESULTS_MD.read_text()
        for task_id in self.TASK_IDS:
            self.assertNotIn(task_id, results_text,
                             f"eval task {task_id!r} in the campaign table")

    def test_the_campaign_keeps_its_own_denominator(self) -> None:
        """Every unclosed campaign project stays in the table saying so, rather than dropped."""
        rows = [ln for ln in self.RESULTS_MD.read_text().splitlines()
                if re.match(r"^\|\s*\d[a-z]?\s*\|", ln)]
        self.assertTrue(rows, "no campaign rows found — this sweep would pass vacuously")
        unclosed = [r for r in rows if "not scored" in r]
        marker_lines = [ln for ln in self.RESULTS_MD.read_text().splitlines()
                        if "not scored" in ln]
        self.assertEqual(len(unclosed), len(marker_lines),
                         "the not-scored marker appears outside the table, so counting it no "
                         "longer counts unclosed projects")

    def test_every_declared_task_has_a_row(self) -> None:
        text = self.EVALS_MD.read_text()
        for task_id in self.TASK_IDS:
            self.assertIn(f"`{task_id}`", text, f"{task_id} is declared but has no row")

    def test_a_not_run_task_says_so_in_the_table_and_is_never_graded(self) -> None:
        """The published row, the declaration and the runner must agree about a task not run.

        Three places can disagree, and the dangerous direction is a task quietly dropped from the
        table while the declaration still explains it. So the table is required to carry the row
        AND to mark it not run, and the results file is required to carry no verdict.
        """
        not_run = REPO / "evals/not-run.json"
        if not not_run.is_file():
            self.skipTest("no not-run declaration in this tree")
        declared = json.loads(not_run.read_text()).get("tasks", {})
        self.assertTrue(declared, "a not-run file with no tasks would pass this vacuously")
        table = self.EVALS_MD.read_text()
        for task_id, decl in declared.items():
            row = [ln for ln in table.splitlines()
                   if ln.startswith(f"| `{task_id}`")]
            self.assertEqual(len(row), 1, f"{task_id} has no single row in the table")
            self.assertIn("not run", row[0].lower(),
                          f"{task_id} is declared not run and the table does not say so")
            self.assertIn(decl["missing_requirement"].split()[0], table,
                          f"the table does not name what {task_id} lacked")

    def test_the_table_names_the_pre_registration_it_was_frozen_at(self) -> None:
        """The row's sha must be the commit that actually introduced the pre-registration.

        Asked of freeze.py, which knows when the answer cannot be trusted. Asking git directly
        was how this test passed a WRONG sha in a shallow clone.
        """
        sys.path.insert(0, str(REPO / "evals"))
        import freeze

        ref = freeze.freeze_ref()
        if not ref["verifiable"]:
            self.skipTest(f"the freeze cannot be proved from this checkout: {ref['why']}")
        self.assertIn(ref["sha"][:7], self.EVALS_MD.read_text(),
                      "the table cites a pre-registration sha that is not the freeze commit")


class ShallowCheckout(unittest.TestCase):
    """A checkout without history must REFUSE, never print a green it did not earn.

    This is the defect freeze.py was written to close, and it was live: at depth 1 -- which is
    what actions/checkout makes by default -- `git log --reverse -- evals/prereg.json` returns
    the grafted head rather than nothing, because a grafted root looks like it added every file.
    The checker named that head as the freeze commit, read the file out of it, compared it to the
    working copy it came from, found them identical and printed "ok byte-identical". It verified
    the file against itself and would have gone on doing so in CI forever.
    """

    def setUp(self) -> None:
        self.t = Tree()
        self.addCleanup(self.t.destroy)
        self.shallow = self.t.dir / "shallow"
        r = sh("git", "clone", "-q", "--depth", "1", f"file://{self.t.root}", str(self.shallow))
        if r.returncode != 0:
            self.skipTest(f"git could not make a shallow clone here: {r.stderr.strip()[:120]}")

    def test_the_freeze_reference_refuses_rather_than_guessing(self) -> None:
        r = sh(sys.executable, self.shallow / "evals/freeze.py")
        ref = json.loads(r.stdout)
        self.assertIsNone(ref["sha"], "a shallow clone must offer no sha, not the wrong one")
        self.assertFalse(ref["verifiable"])
        self.assertIn("fetch-depth", ref["why"], "the refusal must name the fix")

    def test_the_checker_fails_instead_of_printing_a_hollow_green(self) -> None:
        r = sh(sys.executable, self.shallow / "evals/check_results.py")
        self.assertNotEqual(r.returncode, 0,
                            "a checkout that cannot prove the freeze must not exit 0")
        self.assertIn("UNVERIFIABLE", r.stdout)
        # Keyed to the CLAIM line, not to the words. The first version of this assertion looked
        # for "byte-identical" anywhere in the output and went red on the refusal's own
        # explanation of the defect -- a guard keyed to literal prose, catching the sentence that
        # describes the thing rather than the thing.
        self.assertNotIn("ok            prereg.json byte-identical", r.stdout,
                         "it must not claim byte-identity against a sha it could not trust")

    def test_the_runner_records_that_the_anchor_was_not_proved(self) -> None:
        sh(sys.executable, self.shallow / "evals/run.py", "--all")
        result = json.loads((self.shallow / "evals/results/planted-effect.json").read_text())
        self.assertIsNone(result["prereg_sha"])
        self.assertFalse(result["prereg_sha_verifiable"])
        self.assertIn("SHALLOW", result["prereg_sha_note"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
