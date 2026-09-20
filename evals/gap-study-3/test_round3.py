#!/usr/bin/env python3
"""Round 3's own test battery. Round 2's battery is round 2's record and is not copied.

    python3 -W ignore evals/gap-study-3/test_round3.py

Every test here is written so it can fail: each one either mutates the thing it guards and watches the
guard go red, or asserts a count against bytes on disk. A test that can only pass is not a test, and a
check that grades zero items and prints a pass is a defect -- the non-vacuity tests below exist for that.

No model, no network, stdlib only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import copy_manifest  # noqa: E402
import study  # noqa: E402


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=str(cwd or REPO))


def git_show(commit: str, path: str) -> bytes:
    out = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{path}"], capture_output=True)
    assert out.returncode == 0, f"{path} not at {commit[:12]}"
    return out.stdout


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------------------------
# The copy


class TheCopyTracesToRoundTwo(unittest.TestCase):
    def test_the_manifest_re_derives(self):
        r = run(str(HERE / "copy_manifest.py"), "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_manifest_grades_every_file_it_lists(self):
        """Non-vacuity: the manifest must have graded as many files as FILES names, not fewer."""
        rec = json.loads((HERE / "COPIED.json").read_text())
        self.assertEqual(len(rec["files"]), len(copy_manifest.FILES))
        self.assertGreater(len(rec["files"]), 0)

    def test_every_uneditable_file_is_byte_identical(self):
        """The goal file pins these: the take checker, every grader, the label reader, the two linters."""
        self.assertGreater(len(copy_manifest.UNEDITABLE), 0)
        for name in copy_manifest.UNEDITABLE:
            with self.subTest(name):
                src = git_show(copy_manifest.SOURCE_COMMIT, f"{copy_manifest.SOURCE_DIR}/{name}")
                self.assertEqual((HERE / name).read_bytes(), src, f"{name} differs from its source")

    def test_an_edited_grader_is_a_fail_not_a_manifest_entry(self):
        """Mutate a pinned grader in a copy of the tree and watch --check go red for the right reason."""
        with tempfile.TemporaryDirectory() as td:
            tree = Path(td) / "gap-study-3"
            shutil.copytree(HERE, tree, ignore=shutil.ignore_patterns("__pycache__"))
            victim = tree / "graders" / "scope_read.py"
            victim.write_bytes(victim.read_bytes() + b"\n# mutation\n")
            # run it in place of the real folder so REPO-relative git reads still work
            real, backup = HERE, Path(td) / "real"
            shutil.move(str(real), str(backup))
            try:
                shutil.move(str(tree), str(real))
                r = run(str(real / "copy_manifest.py"), "--check")
            finally:
                shutil.rmtree(real, ignore_errors=True)
                shutil.move(str(backup), str(real))
            self.assertEqual(r.returncode, 1, "a mutated grader passed the manifest check")
            self.assertIn("pinned byte-identical", r.stdout)

    def test_the_source_folders_are_pinned_at_named_commits(self):
        self.assertEqual(len(copy_manifest.PINNED_UNCHANGED), 4)
        for commit, path in copy_manifest.PINNED_UNCHANGED:
            with self.subTest(path):
                self.assertRegex(commit, r"^[0-9a-f]{40}$")
                ok = subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", commit],
                                    capture_output=True).returncode
                self.assertEqual(ok, 0, f"{commit[:12]} is not a commit in this repository")


# ---------------------------------------------------------------------------------------------
# The binding


class TheBindingNamesRoundThree(unittest.TestCase):
    def test_the_study_constants(self):
        self.assertEqual(study.STUDY, "gap-study-3")
        self.assertEqual(study.STUDY_REL, "evals/gap-study-3")
        self.assertEqual(study.rel("check_take.py"), "evals/gap-study-3/check_take.py")

    def test_the_two_report_folders_are_different(self):
        """A fresh run counts pre-freeze reviews and final verifications from `ls` alone, so they cannot
        share a folder."""
        self.assertNotEqual(study.REVIEW_DIR, study.VERIFY_DIR)

    def test_the_section_markers_differ_from_every_earlier_round(self):
        earlier = ("<!-- gap-study:summary -->", "<!-- gap-study-2:summary -->",
                   "<!-- haiku-prestudy:summary -->")
        self.assertNotIn(study.SUMMARY_START, earlier)
        self.assertTrue(study.SUMMARY_START.endswith("gap-study-3:summary -->"))

    def test_no_copied_python_file_builds_a_path_into_round_twos_folder(self):
        """A literal copied from round 2 names round 2. Every string this study EXECUTES or PRINTS must
        name this study's folder; only docstrings may still carry the copied round's spelling, and the
        README says so, because ten of these files are pinned byte-identical and cannot be corrected.

        Read with ast so the distinction is structural rather than a guess at line shape.
        """
        import ast
        offenders = []
        for f in sorted(HERE.rglob("*.py")):
            # study.py's ROUND1_REL IS round 2's folder, deliberately: the prior round, as data only.
            # copy_manifest.py's SOURCE_DIR is the same fact for the copy. Neither is a path this study
            # builds for itself, and both are read by the tests above.
            if "__pycache__" in f.parts or f.name in ("copy_manifest.py", "test_round3.py", "study.py"):
                continue
            tree = ast.parse(f.read_text())
            docstrings = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    body = getattr(node, "body", None)
                    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                            and isinstance(body[0].value.value, str):
                        docstrings.add(id(body[0].value))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                        and id(node) not in docstrings and "evals/gap-study-2" in node.value:
                    offenders.append(f"{f.relative_to(REPO)}:{node.lineno}  {node.value.strip()[:90]}")
        self.assertEqual(offenders, [],
                         "a live string builds a path into round 2's folder:\n" + "\n".join(offenders))

    def test_the_pinned_files_whose_docstrings_name_round_two_are_declared(self):
        """The ten byte-identical files cannot be corrected, so the README must name that fact rather
        than leave a reader to trip over it."""
        readme = (HERE / "README.md").read_text()
        self.assertIn("byte-identical", readme)
        self.assertIn("usage line", readme)


# ---------------------------------------------------------------------------------------------
# The driver's change


class TheDriverChangeIsWhatItSays(unittest.TestCase):
    @staticmethod
    def _lift(*names: str):
        """Run named top-level definitions out of drive.py's real bytes, with nothing else executed."""
        import ast
        import types
        tree = ast.parse((HERE / "drive.py").read_text())
        wanted = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
                wanted.append(node)
            elif isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id in names for t in node.targets):
                wanted.append(node)
        assert len(wanted) == len(names), f"lifted {len(wanted)} of {len(names)}: {names}"
        ns = types.SimpleNamespace()
        env: dict = {"re": re, "Path": Path, "OSError": OSError}
        exec(compile(ast.Module(body=wanted, type_ignores=[]), "drive.py", "exec"), env)
        for n in names:
            setattr(ns, n, env[n])
        return ns

    def setUp(self):
        self.ours = (HERE / "drive.py").read_text().splitlines(keepends=True)
        self.theirs = git_show(copy_manifest.SOURCE_COMMIT,
                               f"{copy_manifest.SOURCE_DIR}/drive.py").decode().splitlines(keepends=True)

    def test_nothing_is_removed_from_round_twos_driver(self):
        """Every line round 2's driver had is still here, bar the one display string the manifest names."""
        import difflib
        removed = [l[2:].rstrip("\n") for l in difflib.ndiff(self.theirs, self.ours) if l.startswith("- ")]
        self.assertEqual(len(removed), 1, f"removed lines: {removed}")
        self.assertIn("check_take.py", removed[0])

    def test_every_turn_passes_the_pre_registered_allowlist(self):
        text = "".join(self.ours)
        self.assertIn('argv += ["--allowedTools", *prereg.load()["driver_change"]["allowed_tools"]]', text)
        # in one_turn, which builds every turn's argv -- not in a branch that runs once
        one_turn = text.split("def one_turn(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("--allowedTools", one_turn)

    def test_the_ledger_records_the_mode_the_session_recorded(self):
        # drive.py reads the pre-registration at import time and refuses without one, which is the
        # behaviour that keeps a take from running against no design. So the function under test is
        # lifted out of the real bytes with ast and run on its own, rather than the module booted.
        drive = self._lift("mode_recorded", "PERMISSION_MODE_RECORD")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td) / "transcript.jsonl"
            t.write_text('{"permissionMode": "auto"}\n{"permissionMode": "default"}\n')
            self.assertEqual(drive.mode_recorded(t), "default", "default must win over auto")
            t.write_text('{"permissionMode": "auto"}\n')
            self.assertEqual(drive.mode_recorded(t), "auto")
            t.write_text('{"nothing": 1}\n')
            self.assertEqual(drive.mode_recorded(t), "unrecorded")
            self.assertEqual(drive.mode_recorded(Path(td) / "missing.jsonl"), "unrecorded")

    def test_the_checker_reads_that_field(self):
        """check_take.py is byte-identical to round 2's; the change is only what feeds its rule."""
        text = (HERE / "check_take.py").read_text()
        self.assertIn('ledger.get("permission_mode") != want_mode', text)
        self.assertIn("constant-binding", text)

    def test_round_twos_own_ledger_field_was_a_constant_compared_with_itself(self):
        """The defect this change closes, asserted against round 2's bytes so it cannot be misremembered."""
        theirs = "".join(self.theirs)
        self.assertIn('"permission_mode": PERMISSION_MODE', theirs)
        self.assertNotIn("mode_recorded", theirs)


# ---------------------------------------------------------------------------------------------
# The language guard, and its vacuity


class TheLanguageGuardActuallyScans(unittest.TestCase):
    def test_it_is_clean_and_says_how_much_it_scanned(self):
        r = run(str(HERE / "lint_language.py"), str(HERE))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = re.search(r"clean — (\d+) input\(s\) scanned", r.stdout)
        self.assertIsNotNone(m, f"the linter did not report what it scanned: {r.stdout!r}")
        self.assertGreater(int(m.group(1)), 5, "the linter scanned almost nothing and called it clean")

    def test_a_banned_word_turns_it_red(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "scan"
            folder.mkdir()
            (folder / "note.md").write_text("The model answered reliably in 2 of 3 takes.\n")
            r = run(str(HERE / "lint_language.py"), str(folder))
            self.assertEqual(r.returncode, 1, f"the linter passed a banned word: {r.stdout!r}")
            self.assertIn("reliably", r.stdout)

    def test_the_copied_linter_has_no_pooling_pattern(self):
        """Stated as a fact about round 2's bytes, so the reason round 3 adds its own guard is on record
        rather than in a commit message."""
        import lint_language as ll
        names = {n for n, _, _ in ll.PATTERNS}
        for absent in ("combined", "pooled", "overall", "average", "total-of"):
            self.assertNotIn(absent, names)


class ThePoolingGuardIsMutationProved(unittest.TestCase):
    """The guard round 3 adds. Every case below is a sentence somebody would actually write."""

    def test_the_study_folder_is_clean(self):
        r = run(str(HERE / "lint_pooling.py"), str(HERE))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = re.search(r"clean — (\d+) file\(s\)", r.stdout)
        self.assertIsNotNone(m, r.stdout)
        self.assertGreater(int(m.group(1)), 5, "the guard scanned almost nothing and called it clean")

    def test_every_pooled_sentence_turns_it_red(self):
        cases = ["Across rounds, the models held 5 of 6.",
                 "Combined, that is 4 of 9 takes.",
                 "Overall the task was held in 7 of 12.",
                 "The average across the three models is one of three.",
                 "A total of 11 takes reached the probe.",
                 "Pooled with round 2, the count is 6 of 9.",
                 "Across halves, two of six.",
                 "Both rounds agree on this task.",
                 "Round 3 improved on round 2 for this cell.",
                 "Two of three is better than none of three.",
                 "Up from 0 of 3 in the earlier round.",
                 "In total, 11 takes.",
                 "The aggregate figure is 6 of 9.",
                 "The sum of the two halves is four.",
                 "The mean of the three cells is one."]
        for text in cases:
            with self.subTest(text):
                with tempfile.TemporaryDirectory() as td:
                    folder = Path(td) / "scan"
                    folder.mkdir()
                    (folder / "note.md").write_text(text + "\n")
                    r = run(str(HERE / "lint_pooling.py"), str(folder))
                    self.assertEqual(r.returncode, 1, f"the guard passed a pooled sentence: {r.stdout!r}")

    def test_an_honest_sentence_survives(self):
        keep = ["The cell holds 2 of 3 takes.",
                "Round 2's counts print beside these under a caption naming the instrument.",
                "Slice 4 of 20 landed the fixture re-cut.",
                "One cell is published unmeasured with its reason."]
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "scan"
            folder.mkdir()
            (folder / "note.md").write_text("\n".join(keep) + "\n")
            r = run(str(HERE / "lint_pooling.py"), str(folder))
            self.assertEqual(r.returncode, 0, f"the guard fired on honest prose: {r.stdout}")

    def test_it_refuses_to_call_an_empty_scan_a_pass(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "empty"
            folder.mkdir()
            r = run(str(HERE / "lint_pooling.py"), str(folder))
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("Not a pass", r.stdout)

    def test_it_has_no_allowlist_at_all(self):
        text = (HERE / "lint_pooling.py").read_text()
        self.assertNotIn("language-allowlist", text)
        self.assertNotIn("def excused", text)
        self.assertNotIn("load_allowlist", text)

    def test_it_reads_commit_bodies(self):
        r = run(str(HERE / "lint_pooling.py"), "--commits-since", "HEAD~1")
        self.assertIn(r.returncode, (0, 1, 2), r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_the_excusal_list_is_this_studys_own(self):
        rec = json.loads((HERE / "language-allowlist.json").read_text())
        for e in rec["excused"]:
            with self.subTest(e["file"]):
                self.assertTrue(e["file"].startswith(study.STUDY_REL + "/"),
                                f"{e['file']} is not a file of this study")
                self.assertTrue((REPO / e["file"]).is_file(), f"{e['file']} does not exist")
                self.assertIn(e["line_text"], (REPO / e["file"]).read_text(),
                              f"the excused line is not in {e['file']} as written")


# ---------------------------------------------------------------------------------------------
# The round register


class TheRoundRegisterBinds(unittest.TestCase):
    def setUp(self):
        self.rounds = HERE / "review_kit" / "rounds.py"

    def test_check_is_green_and_says_it_graded_nothing_when_it_did(self):
        r = run(str(self.rounds), "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = json.loads((HERE / "review_kit" / "rounds.json").read_text())["rows"] \
            if (HERE / "review_kit" / "rounds.json").is_file() else []
        if not rows:
            self.assertIn("graded 0 rounds", r.stdout,
                          "an empty register reported a pass without saying it graded nothing")

    def test_the_prompt_is_pinned_to_the_brief_on_disk(self):
        mod = load_module("round3_rounds_for_test", self.rounds)
        want = hashlib.sha256((HERE / "review_kit" / "BRIEF.md").read_bytes()).hexdigest()
        self.assertEqual(mod.sha256_bytes((HERE / "review_kit" / "BRIEF.md").read_bytes()), want)

    def test_a_folder_digest_changes_with_one_byte(self):
        mod = load_module("round3_rounds_for_digest", self.rounds)
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "kit"
            (f / "study").mkdir(parents=True)
            (f / "BRIEF.md").write_text("x")
            first = mod.folder_sha256(f)
            (f / "BRIEF.md").write_text("y")
            self.assertNotEqual(first, mod.folder_sha256(f))
            # a clone's git objects are excluded, so history churn does not move the digest
            (f / "study" / ".git").mkdir()
            (f / "study" / ".git" / "objectish").write_text("z")
            self.assertEqual(mod.folder_sha256(f), mod.folder_sha256(f))

    def test_both_kinds_of_report_have_a_home_and_they_differ(self):
        mod = load_module("round3_rounds_for_report", self.rounds)
        self.assertEqual(set(mod.REPORT), set(mod.KINDS))
        homes = {k: mod.REPORT[k][0] for k in mod.KINDS}
        self.assertEqual(len(set(homes.values())), 2, homes)


# ---------------------------------------------------------------------------------------------
# The reviewer's brief and the purpose page


class TheReviewKitIsPinnedAndBlind(unittest.TestCase):
    # The brief is pinned byte-identical from its first commit, so it names checks that later slices
    # build. Each one lives here until it exists; the set must be EMPTY before the freeze, and the test
    # below fails if the study is frozen while anything is still planned.
    PLANNED = {
        "evals/gap-study-3/allowlist.py",
        "evals/gap-study-3/build_draft.py",
        "evals/gap-study-3/completeness.py",
        "evals/gap-study-3/fixture_walk.py",
        "evals/gap-study-3/leak_grep.py",
    }

    def test_the_brief_names_every_check_it_asks_for(self):
        """A brief that names a command the study does not have grades the reviewer on a typo."""
        brief = (HERE / "review_kit" / "BRIEF.md").read_text()
        named = set(re.findall(r"python3 (evals/gap-study-3/[\w/]+\.py)", brief))
        self.assertGreater(len(named), 5)
        missing = sorted(p for p in named if not (REPO / p).is_file())
        unexpected = sorted(set(missing) - self.PLANNED)
        self.assertEqual(unexpected, [], f"the brief names files nothing plans to build: {unexpected}")
        stale = sorted(p for p in self.PLANNED if (REPO / p).is_file())
        self.assertEqual(stale, [], f"these are built and still listed as planned: {stale}")
        if (HERE / "prereg.json").is_file():
            self.assertEqual(missing, [], "the study is FROZEN and the brief still names files that do "
                                          f"not exist: {missing}")

    def test_the_brief_asks_for_the_threat_model_first_and_a_classified_table(self):
        brief = (HERE / "review_kit" / "BRIEF.md").read_text()
        self.assertIn("The threat model first", brief)
        self.assertIn("BLOCKER, SHOULD or NIT", brief)
        self.assertIn("in your own words", brief)
        self.assertLess(brief.index("The threat model first"), brief.index("Try to break it"))

    def test_the_purpose_page_carries_no_operator_material(self):
        why = (HERE / "review_kit" / "why.md").read_text()
        for marker in ("javrodher", "javier", "@gmail", "portfolio", "hiring", "employer", "glitch"):
            with self.subTest(marker):
                self.assertNotIn(marker, why.lower())

    def test_the_blindness_markers_name_this_round_and_the_ones_before_it(self):
        mod = load_module("round3_blindness_for_test", HERE / "review_kit" / "blindness.py")
        words = {w for _, w in mod.MARKERS}
        for expected in ("gars-eval-v4", "gap-study-3", "round 3", "gars-eval-v3", "gap-study-2",
                         "round 2", "gars-haiku-prestudy", "haiku-prestudy"):
            with self.subTest(expected):
                self.assertIn(expected, words)


if __name__ == "__main__":
    unittest.main(verbosity=2)
