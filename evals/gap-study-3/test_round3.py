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
        env: dict = {"re": re, "json": json, "Path": Path, "OSError": OSError}
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
        # Comments are rewritten wherever a change is explained, so they are not the question. The
        # question is which EXECUTABLE lines of round 2's driver are gone, and each must be one the
        # manifest names.
        code = [l for l in removed if l.strip() and not l.strip().startswith("#")]
        named = ("check_take.py",                 # the display string naming round 2's folder
                 'PERMISSION_MODE = "auto"',      # ruling 7: default across the axis
                 "len(existing) >= 2",            # ruling 8: four walks per task
                 "the cap is two")                # ruling 8, its message
        unaccounted = [l for l in code if not any(n in l for n in named)]
        self.assertEqual(unaccounted, [], f"round 2's driver lost a line nothing accounts for: {unaccounted}")
        joined = " ".join(code)
        for n in ("check_take.py", 'PERMISSION_MODE = "auto"', "len(existing) >= 2"):
            with self.subTest(n):
                self.assertIn(n, joined)

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
        drive = self._lift("mode_recorded", "modes_recorded")
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
                 "Across halves, 2 of 6.",
                 "Across the two halves, 4 of 6 held.",
                 "Both rounds together, 5 of 9.",
                 "Round 3 improved on round 2 for this cell.",
                 "Two of three is better than none of three.",
                 "Up from 0 of 3 in the earlier round.",
                 "Up from none of three.",
                 "Down from round 2's count.",
                 "up from the previous round's figure.",
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
                "One cell is published unmeasured with its reason.",
                # the three false positives this guard raised against honest prose, kept as cases so the
                # narrowing cannot be undone without a red
                "The driver proves it by walking up from the checkout to the filesystem root.",
                "Claude Code walks up from the working directory collecting instruction files.",
                "The fixture is byte-identical across the halves and names no path of this repository.",
                "byte-identical across the two halves; pinned at the freeze",
                "The same question is asked across rounds, with the instrument fixed.",
                # a comparative claim is the owner's gate, not this guard's: it joins no figure
                "Both rounds agree on this task."]
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

    def test_a_spelled_out_count_is_a_figure(self):
        """"The sum of the two halves is four" carries no digit and is exactly the sentence to stop."""
        import lint_pooling as lp
        self.assertTrue(lp.scan_text("The sum of the two halves is four.", "x.md"))
        self.assertTrue(lp.scan_text("A total of eleven takes reached the probe.", "x.md"))

    def test_the_number_inside_the_scope_phrase_is_not_the_figure(self):
        """`across the TWO halves` counts the scopes, not the takes; counting it fires on honest prose."""
        import lint_pooling as lp
        self.assertEqual(lp.scan_text("byte-identical across the two halves; pinned at the freeze",
                                      "x.md"), [])
        self.assertTrue(lp.scan_text("Across the two halves, 4 of 6 held.", "x.md"))

    def test_a_scope_phrase_needs_a_figure_to_fire(self):
        """The split that stopped the guard describing the wrong thing, driven both ways on one phrase."""
        import lint_pooling as lp
        self.assertIn("across-halves", lp.NEEDS_A_FIGURE)
        self.assertNotIn("pooled", lp.NEEDS_A_FIGURE)
        clean = "The fixture is byte-identical across the halves."
        dirty = "The task held in 4 of 6 across the halves."
        self.assertEqual(lp.scan_text(clean, "x.md"), [])
        self.assertTrue(lp.scan_text(dirty, "x.md"), "a figure joined across halves must fire")

    def test_the_widened_spellings_are_covered(self):
        """`across the two halves` escaped the old pattern entirely: too broad on prose and too narrow
        on the shape it was written for, at the same time."""
        import lint_pooling as lp
        for text in ("Across the two halves, 4 of 6.", "across both rounds, 5 of 9.",
                     "across the rounds, 7 of 12."):
            with self.subTest(text):
                self.assertTrue(lp.scan_text(text, "x.md"))

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
        """Green when every registered round has its report; and while a round is OPEN -- its row committed
        alone, before its reviewer opens, which is the register's whole design -- the check refuses and
        names the round. That refusal is the register working, so it is asserted here rather than read as
        a red battery: this test used to fail CI at every row commit, from the row's landing until its
        report's."""
        r = run(str(self.rounds), "--check")
        rows = json.loads((HERE / "review_kit" / "rounds.json").read_text())["rows"] \
            if (HERE / "review_kit" / "rounds.json").is_file() else []
        mod = load_module("round3_rounds_for_open_rows", self.rounds)
        open_rows = [x for x in rows if not x.get("voided_by") and not x.get("spent_without_work")
                     and not mod.committed(mod.report_path(x))]
        if open_rows:
            self.assertEqual(r.returncode, 1, "an open round must block, and this one did not")
            for x in open_rows:
                self.assertIn(f"{x['kind']} round {x['n']} is OPEN", r.stdout)
            return
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
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

    def test_a_committed_report_is_bound_to_its_rows_session(self):
        """The binding lives here, not at launch: the launcher can be handed any id, or none. What the
        row means is that the COMMITTED blindness record names the id the row derives."""
        mod = load_module("round3_rounds_for_binding", self.rounds)
        src = (self.rounds).read_text()
        self.assertIn("does not name the session id this row derives", src)
        row = {"n": 1, "kind": "prefreeze"}
        self.assertTrue(str(mod.blindness_path(row)).endswith("prefreeze-1-blindness.txt"))
        self.assertTrue(str(mod.report_path(row)).endswith("prefreeze-1.md"))

    def test_the_blindness_record_names_the_session_it_read(self):
        mod = load_module("round3_blindness_for_sid", HERE / "review_kit" / "blindness.py")
        src = (HERE / "review_kit" / "blindness.py").read_text()
        self.assertIn("session id: {sid}", src)

    def test_the_launcher_accepts_a_given_session_id(self):
        src = (HERE / "review_kit" / "launch.py").read_text()
        self.assertIn("sys.argv[2] if len(sys.argv) == 3", src)
        self.assertIn("[<session id>]", src)

    def test_both_kinds_of_report_have_a_home_and_they_differ(self):
        mod = load_module("round3_rounds_for_report", self.rounds)
        self.assertEqual(set(mod.REPORT), set(mod.KINDS))
        homes = {k: mod.REPORT[k][0] for k in mod.KINDS}
        self.assertEqual(len(set(homes.values())), 2, homes)


# ---------------------------------------------------------------------------------------------
# Round 2, read as data, and the permission condition derived from it


class RoundTwoIsReadAsDataAndOnlyThroughOneDoor(unittest.TestCase):
    def test_only_one_of_this_studys_own_files_opens_round_twos_folder(self):
        """Three readers of one folder drift, and the one that drifts quietly decides what gets
        published. round2.py is the door; no OTHER file this study wrote may walk past it.

        Scoped to the files round 3 wrote. A copied file's docstring naming the round it came from is
        the copy being honest about itself, and ten of those files cannot be edited at all.
        """
        import ast
        copied = {f["path"].split(study.STUDY_REL + "/", 1)[1]
                  for f in json.loads((HERE / "COPIED.json").read_text())["files"]}
        exempt = {"round2.py", "test_round3.py"}
        offenders = []
        for f in sorted(HERE.rglob("*.py")):
            rel = f.relative_to(HERE).as_posix()
            if "__pycache__" in f.parts or rel in copied or rel in exempt:
                continue
            for node in ast.walk(ast.parse(f.read_text())):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                        and "gap-study-2" in node.value:
                    offenders.append(f"{f.relative_to(REPO)}:{node.lineno}")
        self.assertEqual(offenders, [], f"round 2's folder is named outside the door: {offenders}")

    def test_the_door_is_one_of_this_studys_own_files(self):
        """If round2.py were itself a copied file the test above would exempt it and prove nothing."""
        copied = {f["path"].split(study.STUDY_REL + "/", 1)[1]
                  for f in json.loads((HERE / "COPIED.json").read_text())["files"]}
        self.assertNotIn("round2.py", copied)
        own = [f.relative_to(HERE).as_posix() for f in sorted(HERE.rglob("*.py"))
               if "__pycache__" not in f.parts and f.relative_to(HERE).as_posix() not in copied]
        self.assertGreater(len(own), 2, f"the scoped test has almost nothing to grade: {own}")

    def test_the_door_writes_nothing(self):
        text = (HERE / "round2.py").read_text()
        for writer in ("write_text(", "write_bytes(", "open(", "mkdir(", "unlink(", "rmtree("):
            with self.subTest(writer):
                self.assertNotIn(writer, text, f"round2.py calls {writer}; it is read-only by construction")

    def test_it_reads_the_frozen_file_never_a_draft(self):
        import round2
        self.assertTrue(str(round2.FROZEN).endswith("prereg.json"))
        self.assertNotIn("draft", str(round2.FROZEN))

    def test_the_probe_turns_come_from_round_twos_frozen_file(self):
        import round2
        turns = round2.probe_turns()
        self.assertEqual(len(turns), 6, f"three tasks, two halves: {sorted(turns)}")
        for (task, half), n in turns.items():
            with self.subTest(f"{task}/{half}"):
                self.assertIn(task, round2.TASKS)
                self.assertGreater(n, 1, "a probe on turn 1 would leave no route to derive from")

    def test_commands_stop_before_the_probe(self):
        """The route is what happens BEFORE the question. What happens after is the measurement, and
        conditions taken from it would be chosen by the thing they condition."""
        import round2
        rows = round2.pre_probe_commands()
        self.assertGreater(len(rows), 50)
        probes = round2.probe_turns()
        for r in rows:
            self.assertLess(r["operator_turn_before"], probes[(r["task"], r["half"])] + 1)

    def test_every_row_can_be_gone_and_looked_at(self):
        import round2
        rows = round2.pre_probe_commands()
        unlocatable = [r for r in rows if r["line"] == 0]
        self.assertEqual(unlocatable, [], "a command the derivation cannot point at in its transcript")


class TheAllowlistIsDerivedNotChosen(unittest.TestCase):
    def setUp(self):
        import allowlist
        self.al = allowlist
        self.rec = json.loads((HERE / "allowlist-derivation.json").read_text())

    def test_the_record_re_derives(self):
        r = run(str(HERE / "allowlist.py"), "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_it_graded_something(self):
        self.assertGreater(self.rec["calls_seen"], 0)
        self.assertGreater(len(self.rec["entries"]), 0)

    def test_no_entry_is_a_bare_binary(self):
        for e in self.rec["entries"]:
            with self.subTest(e["entry"]):
                self.assertIn(" ", e["entry"], "a bare binary wildcard reached the candidate list")

    def test_every_entry_is_a_verbatim_prefix_of_a_real_command(self):
        import round2
        for e in self.rec["entries"]:
            with self.subTest(e["entry"]):
                self.assertTrue(e["quoted_from"]["command"].startswith(e["entry"]))
                self.assertTrue((REPO / round2.transcript_rel(e["quoted_from"])).is_file())
                self.assertGreater(e["quoted_from"]["line"], 0)

    def test_the_record_carries_no_path_the_copied_linter_would_misread(self):
        """The record stores the four fields and builds the path in code, because the pinned linter
        reads `claude-opus-5/1/` as a rate. Asserted, so nobody puts the path back."""
        text = (HERE / "allowlist-derivation.json").read_text()
        self.assertNotIn("transcripts/", text)
        r = run(str(HERE / "lint_language.py"), str(HERE / "allowlist-derivation.json"))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_bare_binary_command_yields_no_entry(self):
        entry, why = self.al.candidate("pwd")
        self.assertIsNone(entry)
        self.assertIn("bare binary", why)

    def test_a_run_specific_path_yields_no_entry(self):
        entry, why = self.al.candidate("cd /private/var/folders/x/T/run-9463df65/gars && ls")
        self.assertIsNone(entry, "an entry naming one run would match no other run")
        self.assertIn("one run", why)

    def test_an_arbitrary_entry_is_called_what_it_is(self):
        self.assertEqual(self.al.classify("python3 -c"), "arbitrary")
        self.assertEqual(self.al.classify("ls -la"), "shape")
        self.assertEqual(self.al.classify("python3 _system/stage00_register.py"), "route")

    def test_refused_calls_are_printed_never_dropped(self):
        seen = self.rec["calls_seen"]
        self.assertEqual(seen, self.rec["calls_admitted"] + self.rec["calls_refused_by_construction"])
        self.assertEqual(len(self.rec["refused_by_construction"]),
                         self.rec["calls_refused_by_construction"])

    def test_a_pinned_entry_the_derivation_does_not_produce_is_a_failure(self):
        """The rule that stops the list being widened by argument, driven rather than asserted."""
        rec = dict(self.rec)
        bad = self.al.problems(rec)
        self.assertEqual(bad, [], f"the real derivation is already failing: {bad}")
        # a guessed entry, checked through the same code path the pre-registration goes through
        legal = {e["tool"] for e in rec["entries"]}
        self.assertNotIn("Bash(curl:*)", legal)


# ---------------------------------------------------------------------------------------------
# The draft


class TheDraftIsBuiltNotWritten(unittest.TestCase):
    def setUp(self):
        self.draft = json.loads((HERE / "prereg-draft.json").read_text())

    def test_it_re_derives(self):
        r = run(str(HERE / "build_draft.py"), "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_it_carries_round_twos_keys_byte_for_byte(self):
        import build_draft
        r2 = build_draft.source_prereg()
        self.assertGreater(len(build_draft.CARRIED), 20)
        for k in build_draft.CARRIED:
            with self.subTest(k):
                self.assertIn(k, r2, f"round 2's frozen file has no {k}")
                self.assertEqual(self.draft[k], r2[k], f"{k} is not round 2's frozen value")
        self.assertNotIn("driver_constants", build_draft.CARRIED,
                         "it gains a key, so claiming it is carried whole would be false")
        for k, v in r2["driver_constants"].items():
            with self.subTest(f"driver_constants.{k}"):
                if k == "permission_mode":
                    self.assertEqual(self.draft["driver_constants"][k], "default")
                    self.assertEqual(self.draft["driver_constants"]["permission_mode_round_2"], v)
                    continue
                self.assertEqual(self.draft["driver_constants"][k], v,
                                 "every other key round 2 froze is still round 2's value")

    def test_the_three_tasks_are_round_twos_own(self):
        import build_draft
        import round2
        r2 = {t["id"]: t for t in build_draft.source_prereg()["tasks"]}
        ids = [t["id"] for t in self.draft["tasks"]]
        self.assertEqual(sorted(ids), sorted(round2.TASKS))
        for t in self.draft["tasks"]:
            with self.subTest(t["id"]):
                self.assertEqual(t, r2[t["id"]], "a task differs from round 2's frozen copy")
                for half in ("positive", "control"):
                    self.assertIn(half, t, "both halves are measured")

    def test_the_plan_is_eighteen_cells_and_fifty_four_takes(self):
        self.assertEqual(self.draft["planned_cells"], 18)
        self.assertEqual(self.draft["planned_takes"], 54)
        self.assertEqual(self.draft["n"], 3)
        self.assertEqual(len(self.draft["predictions"]), 18)

    def test_the_export_commit_carries_round_twos_system_under_test(self):
        """gars/ has moved on main since round 2, so the export commit is deliberately not HEAD."""
        import build_draft
        self.assertEqual(self.draft["export_at_gars_tree"],
                         self.draft["system_under_test"]["gars_tree_sha"])
        head_gars = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD:gars"],
                                   capture_output=True, text=True).stdout.strip()
        self.assertNotEqual(self.draft["export_at"], "HEAD")
        if head_gars != self.draft["export_at_gars_tree"]:
            self.assertNotEqual(build_draft.EXPORT_AT, head_gars,
                                "the export commit must carry round 2's tree, not the current one")

    def test_every_prediction_names_the_bytes_it_read(self):
        for p in self.draft["predictions"]:
            with self.subTest(f"{p['task']}/{p['half']}/{p['model']}"):
                self.assertIn("derived_from", p)
                self.assertIn("read_from", p["derived_from"])
                if p["basis"] == "informed":
                    self.assertIsInstance(p["predicted"], int)
                    self.assertEqual(p["predicted"], p["derived_from"]["round_2_k"])
                else:
                    self.assertIsNone(p["predicted"], "a basis-less cell must carry no predicted count")
                    self.assertTrue(p["basis"].startswith("no informed basis — "), p["basis"])

    def test_the_uninformed_cells_are_exactly_the_ones_the_bytes_name(self):
        """Six cells whose transcripts recorded a mode other than the one passed, plus the one cell round 2
        published incomplete. Re-derived here from the same two sources, not from the draft."""
        import round2
        # ROUND 2's constant, not this round's: the question is whether round 2's cell recorded what
        # ROUND 2 passed. Reading this round's value here made six cells compare equal once ruling 7 set
        # it to `default`, and the test silently stopped asking anything.
        import build_draft
        passed = build_draft.source_prereg()["driver_constants"]["permission_mode"]
        modes, counts = round2.cell_modes(), round2.cells()
        expected = set()
        for task in round2.TASKS:
            for model, halves in counts[task]["cells"].items():
                for half, cell in halves.items():
                    recorded = modes[task][model][half]
                    if recorded != passed or "incomplete" in str(cell.get("state", "")).lower():
                        expected.add((task, half, model))
        got = {(p["task"], p["half"], p["model"]) for p in self.draft["predictions"]
               if p["predicted"] is None}
        self.assertEqual(got, expected)
        self.assertEqual(len(got), 7, sorted(got))

    def test_both_owner_gates_are_named_and_quoted_verbatim(self):
        keys = [r["source_key"] for r in self.draft["carried_rulings"]]
        self.assertIn("permission_stop_rule", keys,
                      "asked-to-proceed's broad reading is named by the goal as one that must be re-put")
        for r in self.draft["carried_rulings"]:
            with self.subTest(r["source_key"]):
                self.assertEqual(r["quoted_verbatim"], self.draft[r["source_key"]],
                                 "a carried ruling must be quoted verbatim from the key it was recorded in")

    def test_the_allowlist_in_the_draft_is_exactly_what_the_derivation_produces(self):
        import allowlist
        derived = [e["tool"] for e in allowlist.derive()["entries"]]
        self.assertEqual(self.draft["driver_change"]["allowed_tools"], derived)
        self.assertGreater(len(derived), 0)

    def test_the_limitations_carry_the_three_the_goal_names(self):
        text = " ".join(self.draft["limitations_lines"]).lower()
        self.assertIn("no session file records", text)
        self.assertIn("less permissive", text)
        self.assertIn("later date", text)
        self.assertGreaterEqual(len(self.draft["limitations_lines"]), 6)

    def test_the_not_poolable_rule_names_what_enforces_it(self):
        np = self.draft["not_poolable"]
        self.assertGreaterEqual(len(np["enforced_by"]), 2)
        self.assertTrue(any("lint_pooling" in e for e in np["enforced_by"]))
        self.assertTrue(any("result.py" in e for e in np["enforced_by"]))

    def test_the_take_order_is_not_drawn_before_the_review(self):
        self.assertIsNone(self.draft["take_order"])
        self.assertIsNone(self.draft["take_order_seed"])

    def test_the_namespace_is_this_studys_own(self):
        import build_draft
        import uuid as _uuid
        ns = self.draft["session_namespace"]
        self.assertEqual(ns["uuid"], str(_uuid.uuid5(_uuid.NAMESPACE_URL, ns["derived_from"])))
        r2_ns = build_draft.source_prereg()["session_namespace"]["uuid"]
        self.assertNotEqual(ns["uuid"], r2_ns, "a shared namespace could repeat round 2's session ids")

    def test_the_copied_loader_reads_it_and_plans_the_right_size(self):
        r = run(str(HERE / "takes.py"), "--plan")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("planned 54 takes", r.stdout)


# ---------------------------------------------------------------------------------------------
# The leak verdict, and the finding that corrected the premise


class TheLeakVerdictIsDecidedAtPathBoundaries(unittest.TestCase):
    def setUp(self):
        import fixture_walk
        self.fw = fixture_walk

    def test_containment_is_by_parts_never_by_substring(self):
        """`/tmp/run-1/gars` is not inside `/tmp/run-11`, and a substring test says it is."""
        self.assertTrue(self.fw.under("/tmp/run-1/gars", "/tmp/run-1"))
        self.assertFalse(self.fw.under("/tmp/run-11/gars", "/tmp/run-1"))
        self.assertFalse(self.fw.under("/tmp/run-1", "/tmp/run-1/gars"))
        self.assertTrue(self.fw.under("/tmp/run-1", "/tmp/run-1"))

    def test_a_dotted_path_is_normalised_before_it_is_compared(self):
        self.assertTrue(self.fw.under("/tmp/run-1/x/../gars", "/tmp/run-1"))
        self.assertFalse(self.fw.under("/tmp/run-1/../run-2/gars", "/tmp/run-1"))

    def test_the_study_roots_are_taken_from_this_files_location(self):
        roots = self.fw.study_roots()
        self.assertIn(str(REPO), roots)
        self.assertEqual(len(roots), 3, "the checkout, the folder holding it, and the root above")
        for r in roots:
            with self.subTest(r):
                self.assertTrue(Path(r).is_absolute())

    def test_a_path_inside_the_checkout_is_the_only_leak(self):
        inside = str(REPO / "evals" / "gap-study-3" / "prereg-draft.json")
        self.assertEqual(self.fw.classify_path(inside, "/tmp/run-1"), "study")
        self.assertEqual(self.fw.classify_path("/tmp/run-1/gars/CLAUDE.md", "/tmp/run-1"), "run-tree")
        self.assertEqual(self.fw.classify_path("/usr/bin/python3", "/tmp/run-1"), "system")
        self.assertEqual(self.fw.classify_path("/tmp/scratch.json", "/tmp/run-1"), "elsewhere")

    def test_the_static_verdict_is_clean_and_graded_every_half(self):
        rec = self.fw.static_verdict()
        self.assertEqual(rec["verdict"], "clean")
        halves = sum(len(v) for v in rec["tasks"].values())
        self.assertEqual(halves, 6, f"three tasks, two halves each: {halves}")

    def test_the_finding_re_derives_from_round_twos_bytes(self):
        r = run(str(HERE / "fixture_walk.py"), "--finding")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("re-derives", r.stdout)

    def test_none_of_the_three_refused_attempts_named_this_checkout(self):
        """The correction itself, driven on the bytes rather than read off the page that states it."""
        import round2
        root = (REPO / study.ROUND1_REL / "rehearsals" / "template-adherence" / "control"
                / "claude-sonnet-5")
        attempts = sorted(root.glob("row-*/transcript.jsonl"))
        self.assertEqual(len(attempts), 3, f"round 2's capped cell has three refused attempts: {attempts}")
        for a in attempts:
            with self.subTest(a.parent.name):
                rec = self.fw.replay(a)
                # Not `clean`: each named its own scratch redirect, a path the verdict cannot place, which
                # is what the checker refused it for. The claim here is only that none named THIS checkout.
                self.assertNotEqual(rec["verdict"], "leaks", rec["leaking_paths"])
                self.assertEqual(rec["leaking_paths"], [])
                self.assertGreater(rec["distinct_absolute_paths"], 5,
                                   "a verdict over almost no paths has graded nothing")

    def test_the_finding_page_states_what_the_code_derives(self):
        """A page whose own checker passes while the page says something else is the defect this guards."""
        page = (HERE / "verification" / "finding.md").read_text()
        self.assertIn("fixture_walk.py --finding", page)
        derived = self.fw.round2_caps()
        self.assertIn(str(derived["refused_attempts"]), page)
        self.assertIn(str(derived["distinct_outside_paths_by_source"]
                          ["the harness's background-task output file"]), page)

    def test_half_equivalence_is_derived_per_task_not_assumed(self):
        """It is not uniform: two tasks build the same fixture bytes for both halves and one does not."""
        eq = self.fw.half_equivalence()
        self.assertEqual(len(eq), 3)
        for task, rec in eq.items():
            with self.subTest(task):
                self.assertTrue(rec["pre_probe_script_identical"],
                                "a walk stops before the probe, so the pre-probe script must be the same")
                self.assertEqual(rec["walks_needed"], 1 if rec["fixture_sha256_identical"] else 2)
        self.assertFalse(eq["confounded-design"]["one_walk_covers_both_halves"],
                         "its two halves build different fixture bytes")
        self.assertTrue(eq["template-adherence"]["one_walk_covers_both_halves"])

    def test_every_half_is_covered_by_a_committed_walk(self):
        cov = self.fw.walk_coverage()
        short = {t: c for t, c in cov.items() if not c["covered"]}
        self.assertEqual(short, {}, f"halves with no walk behind them: {short}")
        self.assertGreater(sum(c["walks_committed"] for c in cov.values()), 0)

    def test_every_committed_walk_is_clean(self):
        walks = self.fw.committed_walks()
        self.assertGreaterEqual(len(walks), 5, "a verdict over almost no walks has graded nothing")
        for w in walks:
            with self.subTest(w.parent.name):
                self.assertEqual(self.fw.replay(w)["verdict"], "clean")

    def test_the_walks_record_the_mode_each_session_actually_ran_in(self):
        """The driver's change, driven on real sessions rather than on a fixture."""
        seen = set()
        for w in self.fw.committed_walks():
            d = json.loads((w.parent / "driver-ledger.json").read_text())
            with self.subTest(f"{d['task']}/{d['half']}/{d['model_requested']}"):
                self.assertIn(d.get("permission_mode"), ("auto", "default", "unrecorded"))
                self.assertEqual(len(d.get("allowed_tools") or []), 22)
                seen.add((d["model_requested"], d["permission_mode"]))
        # The five walks committed so far were driven under ruling 2, with `auto` passed; review 1 raised
        # that as a SHOULD and ruling 7 makes it load-bearing. Walks under `default` come next, so this
        # asserts what each ledger records rather than a constant that has since moved.
        self.assertIn(("claude-haiku-4-5-20251001", "default"), seen)

    def test_no_walk_met_a_denial(self):
        """What the permission condition is for. A denial here would be the condition, not the model."""
        for w in self.fw.committed_walks():
            with self.subTest(w.parent.name):
                self.assertNotIn("Permission for this tool use was denied",
                                 w.read_text(errors="replace"))

    def test_check_says_out_loud_when_it_has_graded_no_walk(self):
        r = run(str(HERE / "fixture_walk.py"), "--check")
        self.assertEqual(r.returncode, 0, r.stdout)
        if not self.fw.committed_walks():
            self.assertIn("graded 0 walks", r.stdout)
            self.assertIn("Not a pass", r.stdout)
        else:
            self.assertIn("committed walk(s) graded", r.stdout)


# ---------------------------------------------------------------------------------------------
# The permission mode, asserted where the copied checker could not assert it


class TheModeBindingIsAnAssertionRoundTwoCouldNotMake(unittest.TestCase):
    def setUp(self):
        import mode_binding
        self.mb = mode_binding

    def test_round_twos_rule_compared_a_constant_with_itself(self):
        """The defect this file exists for, asserted against round 2's own bytes."""
        import build_draft
        r2 = build_draft.source_prereg()
        src = git_show(copy_manifest.SOURCE_COMMIT,
                       f"{copy_manifest.SOURCE_DIR}/drive.py").decode()
        self.assertIn('"permission_mode": PERMISSION_MODE', src)
        self.assertEqual(r2["driver_constants"]["permission_mode"], "auto")
        self.assertNotIn("permission_mode_expected", r2["driver_constants"])

    def test_the_expectation_is_per_model_and_covers_every_model(self):
        exp = self.mb.expected()
        import prereg
        for m in prereg.load()["models"]:
            with self.subTest(m):
                self.assertIn(m, exp, "a model with no expected mode could not be held to anything")
        import prereg as _pr
        self.assertEqual(set(exp.values()), {_pr.load()["driver_constants"]["permission_mode"]},
                         "ruling 7: one condition across the axis means one expected value")

    def test_the_mode_is_re_derived_here_not_read_from_the_ledger(self):
        """A checker that read the driver's own field would be checking the driver against itself."""
        src = (HERE / "mode_binding.py").read_text()
        self.assertIn("def modes_recorded", src)
        self.assertNotIn("import drive", src)

    def test_every_walk_records_the_mode_its_model_is_pinned_to(self):
        got = self.mb.rows(walks=True)
        self.assertGreaterEqual(len(got), 5, "a binding over almost no sessions has graded nothing")
        for r in got:
            with self.subTest(r["attempt"]):
                self.assertEqual(r["problems"], [])
        self.assertIn("default", {r["recorded"] for r in got})
        self.assertIn("auto", {r["recorded"] for r in got})
        # Ruling 7 replaced the condition these five were driven under, so each is reported as superseded
        # rather than graded, and the run says so out loud rather than counting a pass over them.
        sup = [r for r in got if r["superseded"]]
        live = [r for r in got if not r["superseded"]]
        self.assertEqual(len(sup), 5, "the walks driven before the design pinned an expectation")
        self.assertGreaterEqual(len(live), 3, "ruling 7 needs a graded walk on each of the two larger models, "
                                              "and review 2's third NIT one on the smallest")
        self.assertEqual({r["model"] for r in live},
                         {"claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"})
        for r in live:
            with self.subTest(r["attempt"]):
                self.assertEqual(r["passed"], "default")
                self.assertEqual(r["recorded"], "default")

    def test_the_smallest_model_records_default_where_auto_is_passed(self):
        """The finding, stated as a fact about this round's own sessions rather than the pre-study's: the
        four walks that passed `auto` recorded `default`. The one driven after ruling 7 passed `default`
        and recorded it, which is the other half of the same fact."""
        got = [r for r in self.mb.rows(walks=True) if r["model"] == "claude-haiku-4-5-20251001"]
        under_auto = [r for r in got if r["passed"] == "auto"]
        under_default = [r for r in got if r["passed"] == "default"]
        self.assertGreaterEqual(len(under_auto), 4)
        self.assertGreaterEqual(len(under_default), 1, "review 2's third NIT: one walk with default passed")
        for r in got:
            with self.subTest(r["attempt"]):
                self.assertEqual(r["recorded"], "default")

    def test_a_session_recording_the_wrong_mode_turns_it_red(self):
        """Driven on synthetic input, so it keeps biting when every committed session is superseded --
        which is the state that made this mutation pass over nothing once already."""
        exp = self.mb.expected()
        ledger = {"model_requested": "claude-sonnet-5", "permission_mode_expected": "default",
                  "permission_mode_passed": "default"}
        sup, ok = self.mb.judge(ledger, "default", exp, walks=False)
        self.assertFalse(sup)
        self.assertEqual(ok, [], "the honest case must pass, or the mutation proves nothing")
        sup, bad = self.mb.judge(ledger, "auto", exp, walks=False)
        self.assertTrue(any("is pinned to record" in p for p in bad), bad)

    def test_a_ledger_that_disagrees_with_its_transcript_turns_it_red(self):
        exp = self.mb.expected()
        ledger = {"model_requested": "claude-sonnet-5", "permission_mode_expected": "default",
                  "permission_mode_recorded": "auto"}
        _, bad = self.mb.judge(ledger, "default", exp, walks=False)
        self.assertTrue(any("publishes" in p for p in bad), bad)

    def test_a_take_is_never_excused_as_superseded(self):
        """The supersession is a walk's relief, never a take's: a take with no recorded expectation is a
        take the driver did not bind, and that must not read as 'not graded'."""
        exp = self.mb.expected()
        ledger = {"model_requested": "claude-sonnet-5"}
        sup, bad = self.mb.judge(ledger, "auto", exp, walks=False)
        self.assertFalse(sup, "a take may not be waved through as superseded")
        self.assertTrue(bad)
        sup, _ = self.mb.judge(ledger, "auto", exp, walks=True)
        self.assertTrue(sup)

    def test_the_draft_carries_the_expectation_and_says_why(self):
        import prereg
        dc = prereg.load()["driver_constants"]
        self.assertIn("permission_mode_expected", dc)
        self.assertIn("permission_mode_expected_why", dc)
        self.assertEqual(dc["permission_mode"], "default", "ruling 7: one condition across the axis")
        self.assertEqual(dc["permission_mode_round_2"], "auto", "round 2's value stays visible")

    def test_both_owner_gates_are_closed(self):
        import prereg
        pre = prereg.load()
        self.assertIsNotNone(pre["driver_change"]["approved_by_owner"])
        self.assertIsNotNone(pre["driver_change"]["approved_at"])
        for r in pre["carried_rulings"]:
            with self.subTest(r["source_key"]):
                self.assertIsNotNone(r["reaffirmed_by_owner"])
                self.assertIsNotNone(r["reaffirmed_at"])


# ---------------------------------------------------------------------------------------------
# The leak list, driven against real sessions before the freeze


class TheLeakListIsDrivenBeforeItIsFrozen(unittest.TestCase):
    def setUp(self):
        import leak_grep
        self.lg = leak_grep

    def test_it_reads_through_the_checkers_own_readers(self):
        """A check that re-implemented them would be testing a different rule from the one that judges."""
        src = (HERE / "leak_grep.py").read_text()
        self.assertIn("check_take.py", src)
        self.assertIn("context_text", src)
        self.assertIn("context_leaks", src)

    def test_it_is_green_and_graded_something(self):
        r = run(str(HERE / "leak_grep.py"), "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rec = self.lg.derive()
        self.assertGreaterEqual(rec["sessions_read"], 5, "a grep over no session says nothing")
        self.assertGreaterEqual(rec["leak_words"], 20)
        self.assertEqual(rec["words_that_would_void_a_session"], [])

    def test_the_two_harness_words_really_are_present(self):
        """The excusals are not decorative: both words DO appear in every real session's context."""
        rec = self.lg.derive()
        present = set(rec["words_present_in_some_session"])
        self.assertIn("allowlist", present)
        for w in rec["per_word"]:
            with self.subTest(w["word"]):
                self.assertEqual(w["sessions_hit"], rec["sessions_read"],
                                 "harness furniture appears in every session, not some")
                self.assertEqual(w["still_flagged_in"], 0)

    def test_the_un_enumerable_leak_word_is_gone_and_says_why(self):
        """A word that can only be excused wording by wording is not a leak signal. It was found in three
        different wordings across seven real walks, one of them for a single model, and a fourth was a
        harness release away -- which after the freeze would void takes with no fix but an amendment."""
        import prereg
        pre = prereg.load()
        self.assertNotIn("permission mode", pre["leak_words"])
        dropped = pre["leak_word_dropped"]
        self.assertEqual(dropped["word"], "permission mode")
        self.assertIn("three different wordings", dropped["why"])
        # the names that identify THIS study stay
        for name in ("gap-study-3", "gars-eval-v4", "round 3", "allowlist"):
            with self.subTest(name):
                self.assertIn(name, pre["leak_words"])

    def test_no_excusal_survives_for_the_dropped_word(self):
        """Excusals for a word no longer on the list would forgive nothing and hide that they do."""
        import prereg
        for e in prereg.load()["leak_context_excusals"]:
            with self.subTest(e["phrase"][:40]):
                self.assertNotIn("user-selected permission mode", e["phrase"])

    def test_removing_an_excusal_turns_it_red(self):
        """Driven through the checker's own reader on a real session's real context."""
        import importlib.util
        import prereg
        spec = importlib.util.spec_from_file_location("ct_for_leak_test", HERE / "check_take.py")
        ct = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ct)
        pre = dict(prereg.load())
        session = self.lg.sessions()[0]
        ctx = ct.context_text(session)
        self.assertEqual(ct.context_leaks(ctx, pre), set(), "the real list must be clean to start")
        stripped = dict(pre)
        stripped["leak_context_excusals"] = [e for e in pre["leak_context_excusals"]
                                             if "allowlist" not in e["phrase"]]
        self.assertIn("allowlist", ct.context_leaks(ctx, stripped),
                      "dropping the excusal must bring the finding back")

    def test_every_added_excusal_quotes_text_that_is_really_there(self):
        """An excusal pinned to a phrase the producer does not say forgives nothing and hides that."""
        import build_draft
        import importlib.util
        spec = importlib.util.spec_from_file_location("ct_for_phrase_test", HERE / "check_take.py")
        ct = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ct)
        contexts = [ct.context_text(s) for s in self.lg.sessions()]
        self.assertTrue(contexts)
        for e in build_draft.EXCUSALS_ADDED:
            with self.subTest(e["phrase"][:40]):
                self.assertTrue(any(e["phrase"].lower() in c for c in contexts),
                                "no recorded session carries this phrase")

    def test_the_draft_carries_round_twos_excusals_and_this_rounds(self):
        import build_draft
        import prereg
        r2 = build_draft.source_prereg()["leak_context_excusals"]
        got = prereg.load()["leak_context_excusals"]
        self.assertEqual(got[:len(r2)], r2, "round 2's excusals are carried verbatim and first")
        self.assertEqual(len(got), len(r2) + len(build_draft.EXCUSALS_ADDED))


# ---------------------------------------------------------------------------------------------
# The result, and the rule that no cell goes missing


class TheResultPublishesCountsAndNamesWhatItDidNotMeasure(unittest.TestCase):
    def setUp(self):
        import result
        self.r = result
        self.rec = result.derive()

    def test_it_refuses_against_a_draft(self):
        import prereg
        if prereg.is_frozen():
            self.skipTest("the study is frozen; this rule is about the draft")
        out = run(str(HERE / "result.py"), "--check")
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn("not applicable — not frozen", out.stdout)
        self.assertIn("graded 0 of 54", out.stdout)

    def test_the_denominator_is_the_plan_not_the_disk(self):
        """A cell cannot go missing by not being written: the plan is what is counted against."""
        self.assertEqual(self.rec["planned_cells"], 18)
        self.assertEqual(self.rec["planned_takes"], 54)
        self.assertEqual(len(self.rec["cells"]), 18)
        keys = {(c["task"], c["half"], c["model"]) for c in self.rec["cells"]}
        self.assertEqual(len(keys), 18, "a duplicated cell would hide a missing one")

    def test_every_cell_is_complete_or_unmeasured_with_a_reason(self):
        for c in self.rec["cells"]:
            with self.subTest(f"{c['task']}/{c['half']}/{c['model']}"):
                self.assertIn(c["state"], ("complete", "unmeasured"))
                if c["state"] != "complete":
                    self.assertTrue(c["reason"], "unmeasured is only legal with a reason")

    def test_every_k_of_n_has_n_equal_to_three(self):
        for c in self.rec["cells"]:
            self.assertEqual(c["n"], 3)
        for r in self.rec["round_two"]["rows"]:
            self.assertEqual(r["n"], 3)

    def test_a_cell_with_the_wrong_n_turns_the_structural_check_red(self):
        bad = json.loads(json.dumps(self.rec))
        bad["cells"][0]["n"] = 6
        self.assertTrue(any("n = 6" in p for p in self.r.structural_problems(bad)))

    def test_an_unmeasured_cell_with_no_reason_turns_it_red(self):
        bad = json.loads(json.dumps(self.rec))
        bad["cells"][0]["state"] = "unmeasured"
        bad["cells"][0]["reason"] = None
        self.assertTrue(any("names no reason" in p for p in self.r.structural_problems(bad)))

    def test_the_earlier_rounds_incomplete_cell_publishes_as_incomplete(self):
        rows = {(r["task"], r["half"], r["model"]): r for r in self.rec["round_two"]["rows"]}
        hit = rows[("template-adherence", "control", "claude-sonnet-5")]
        self.assertTrue(hit["incomplete"])
        self.assertIsNone(hit["graded"], "an incomplete cell must not publish a count")
        self.assertEqual(sum(1 for r in self.rec["round_two"]["rows"] if r["incomplete"]), 1)

    def test_an_incomplete_cell_that_published_a_count_turns_it_red(self):
        bad = json.loads(json.dumps(self.rec))
        for r in bad["round_two"]["rows"]:
            if r["incomplete"]:
                r["graded"] = 0
        self.assertTrue(any("incomplete and publishes a count" in p
                            for p in self.r.structural_problems(bad)))

    def test_the_caption_is_written_by_code_and_names_all_three(self):
        cap = self.r.caption()
        for want in ("permission condition", "run date", "instrument", "recorded"):
            with self.subTest(want):
                self.assertIn(want, cap.lower())
        self.assertIn("22 admitted commands", cap)
        self.assertIn("read separately", cap)
        self.assertIn("would describe neither", cap)

    def test_the_two_tables_are_separate_in_the_rendered_page(self):
        page = self.r.render(self.rec)
        self.assertIn("## This round", page)
        self.assertIn("## The earlier round, beside — never joined", page)
        self.assertLess(page.index("## This round"), page.index("## The earlier round"))

    def test_the_rendered_page_survives_both_language_guards(self):
        import tempfile as _tf
        with _tf.TemporaryDirectory() as td:
            f = Path(td) / "RESULT.md"
            f.write_text(self.r.render(self.rec))
            for guard in ("lint_language.py", "lint_pooling.py"):
                with self.subTest(guard):
                    out = run(str(HERE / guard), str(f))
                    self.assertEqual(out.returncode, 0, out.stdout)


class TheCompletenessCheckCountsAgainstThePlan(unittest.TestCase):
    def test_it_enumerates_every_planned_cell(self):
        r = run(str(HERE / "completeness.py"), "--check")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("complete cells", r.stdout)
        self.assertEqual(r.stdout.count("of 3   "), 18, "every planned cell must be printed")

    def test_it_says_out_loud_that_it_claims_nothing_before_the_freeze(self):
        import prereg
        if prereg.is_frozen():
            self.skipTest("the study is frozen")
        r = run(str(HERE / "completeness.py"), "--check")
        self.assertIn("not applicable — not frozen", r.stdout)


# ---------------------------------------------------------------------------------------------
# What review 1's four blockers were, driven so none can come back


class ReviewOneBlockersStayFixed(unittest.TestCase):
    def test_blocker_1_the_held_count_is_the_graders_not_the_take_count(self):
        """A cell with three graded takes and one correct verdict must publish 1, not 3."""
        import result
        held = {("t", "positive", "m"): {"k": 1, "n": 3, "state": "RAN",
                                         "labels": ["correct", "wrong", "wrong"]}}
        g = {("t", "positive", "m"): {"takes": ["1", "2", "3"], "modes": {"default"}}}
        import prereg
        c = result.cell_state(("t", "positive", "m"), g, {}, {}, prereg.load(), held)
        self.assertEqual(c["state"], "complete")
        self.assertEqual(c["held"], 1, "the held count must come from the graders")
        self.assertEqual(c["graded"], 3, "the take count is the denominator, not the answer")
        page = result.render({"planned_cells": 1, "planned_takes": 3, "graded_takes": 3,
                              "complete_cells": 1, "cells": [c],
                              "round_two": result.round_two_table(), "amendments": []})
        self.assertIn("| 1 of 3 |", page)
        self.assertNotIn("| 3 of 3 | 3 of 3 |", page)

    def test_blocker_1_a_complete_cell_with_no_grader_count_turns_it_red(self):
        import result
        import prereg
        g = {("t", "positive", "m"): {"takes": ["1", "2", "3"], "modes": set()}}
        c = result.cell_state(("t", "positive", "m"), g, {}, {}, prereg.load(), {})
        bad = result.structural_problems({"cells": [c], "round_two": {"rows": []}})
        self.assertTrue(any("publishes no held count" in p for p in bad), bad)

    def test_blocker_2_every_pin_exists_and_this_rounds_own_guards_are_pinned(self):
        fz = load_module("round3_freeze_for_pins", HERE / "freeze.py")
        missing = [p for p in fz.PINNED if not (REPO / p).is_file()]
        self.assertEqual(missing, [], f"a missing pin makes the freeze exit 1: {missing}")
        own = {p.rsplit("/", 1)[-1] for p in fz.PINNED if study.STUDY_REL in p}
        for guard in ("result.py", "mode_binding.py", "completeness.py", "lint_pooling.py",
                      "test_round3.py", "allowlist.py", "round2.py", "fixture_walk.py", "leak_grep.py",
                      "build_draft.py", "copy_manifest.py", "study.py", "COPIED.json",
                      "allowlist-derivation.json"):
            with self.subTest(guard):
                self.assertIn(guard, own, "unpinned, it could be edited after the freeze unnoticed")

    def test_blocker_2_a_new_file_is_pinned_by_existing(self):
        """The list is derived, so the way it went stale between two rounds cannot recur."""
        fz = load_module("round3_freeze_for_derive", HERE / "freeze.py")
        probe = HERE / "zzz_probe_for_pin_derivation.py"
        try:
            probe.write_text("# a file that did not exist when the list was written\n")
            fresh = load_module("round3_freeze_rederive", HERE / "freeze.py")
            self.assertIn(study.rel(probe.name), fresh.PINNED)
        finally:
            probe.unlink(missing_ok=True)
        self.assertNotIn(study.rel("zzz_probe_for_pin_derivation.py"), fz.PINNED)

    def test_blocker_2_the_rehearsal_runs_only_commands_that_exist(self):
        src = (HERE / "freeze_rehearsal.py").read_text()
        import re as _re
        named = set(_re.findall(r'f"\{S\}/([\w/]+\.(?:py|sh))"', src))
        self.assertGreater(len(named), 10)
        missing = sorted(n for n in named if not (HERE / n).is_file())
        self.assertEqual(missing, [], f"the rehearsal cannot end all-green while it names these: {missing}")

    def test_blocker_3_one_disposition_and_the_copied_checker_applies_it(self):
        import prereg
        pre = prereg.load()
        want = pre["driver_constants"]["permission_mode"]
        self.assertEqual(want, "default")
        self.assertEqual(set(pre["driver_constants"]["permission_mode_expected"].values()), {want},
                         "one condition across the axis means one expected value")
        binding = pre["driver_change"]["permission_mode_binding"]
        self.assertIn("constant-binding", binding)
        self.assertNotIn("mode-drift", binding, "a reason id the carried list does not have")
        self.assertIn("constant-binding", pre["rehearsal_reasons"])
        for r in pre["driver_constants"]["permission_mode_expected_why"], binding:
            self.assertNotIn("mode-drift", r)

    def test_blocker_3_the_driver_writes_the_recorded_mode_where_the_checker_reads(self):
        drive_src = (HERE / "drive.py").read_text()
        self.assertIn('ledger["permission_mode"] = recorded', drive_src)
        self.assertIn('ledger.get("permission_mode") != want_mode', (HERE / "check_take.py").read_text())

    def test_blocker_4_the_question_claims_what_the_design_delivers(self):
        import prereg
        pre = prereg.load()
        q = pre["question"]
        self.assertIn("default", q)
        self.assertNotIn("one permission condition pre-registered for the whole model axis", q)
        self.assertEqual(pre["driver_constants"]["permission_mode"], "default")
        drive_src = (HERE / "drive.py").read_text()
        self.assertIn('PERMISSION_MODE = "default"', drive_src)

    def test_blocker_4_the_limitation_now_says_less_permissive(self):
        import prereg
        text = " ".join(prereg.load()["limitations_lines"]).lower()
        self.assertIn("less permissive", text)
        self.assertNotIn("more permissive", text)


class ReviewTwoBlockersStayFixed(unittest.TestCase):
    """Review 2's three blockers and four follow-ups, each driven on synthetic input so it keeps biting."""

    @staticmethod
    def _cr():
        return load_module("round3_check_results_for_review_2", HERE / "check_results.py")

    @staticmethod
    def _write_transcript(folder: Path, records: list[dict]) -> Path:
        t = folder / "transcript.jsonl"
        t.write_text("".join(json.dumps(r) + "\n" for r in records))
        return t

    # -- blocker 1: a mode-drifting take has a route, and an edited field still has none ---------------

    def test_blocker_1_constant_binding_is_off_this_rounds_driver_decided_list(self):
        import build_draft
        import prereg
        pre = prereg.load()
        self.assertNotIn("constant-binding", pre["driver_decided_reasons"])
        self.assertIn("constant-binding", pre["driver_decided_reasons_round_2"], "round 2's list is kept beside")
        self.assertIn("constant-binding", build_draft.source_prereg()["driver_decided_reasons"])
        self.assertIn("constant-binding", pre["rehearsal_reasons"], "the reason id itself is carried")
        self.assertIn("driver_decided_reasons_round_2", pre["driver_decided_reasons_note"])
        self.assertNotIn("driver_decided_reasons", build_draft.CARRIED,
                         "it is edited, so claiming it is carried whole would be false")
        self.assertIn("ADMISSIBLE", pre["driver_change"]["permission_mode_binding"])

    def test_blocker_1_the_normalised_ledger_reads_the_mode_from_the_transcript(self):
        cr = self._cr()
        with tempfile.TemporaryDirectory() as td:
            t = self._write_transcript(Path(td), [{"type": "user", "permissionMode": "auto"}])
            self.assertEqual(cr.recorded_permission_mode(t, {"permission_mode": "auto"}), "auto",
                             "an honest drift is read as the session recorded it")
            t = self._write_transcript(Path(td), [{"type": "user", "permissionMode": "default"}])
            self.assertEqual(cr.recorded_permission_mode(t, {"permission_mode": "auto"}), "default",
                             "an edited field is put back to what the transcript says")
            gone = Path(td) / "missing.jsonl"
            self.assertEqual(cr.recorded_permission_mode(gone, {"permission_mode": "unrecorded",
                                                                "transcript": None}), "unrecorded")

    def test_blocker_1_an_honest_drift_survives_the_re_run_and_an_edited_field_does_not(self):
        """The ledger-made rule asks which refusals survive the normalised ledger. Both cases, end to end
        through the pinned checker's own constant rule."""
        import prereg
        cr = self._cr()
        ct = load_module("round3_check_take_for_review_2", HERE / "check_take.py")
        pre = prereg.load()
        base = {"budget_s": int(pre["budgets"]["turn_timeout_s"]),
                "gars_tree_sha": pre["system_under_test"]["gars_tree_sha"]}
        with tempfile.TemporaryDirectory() as td:
            # honest: the session recorded auto, the driver wrote auto, the checker refuses -- and the
            # refusal is still there once the ledger is read as the driver writes it
            t = self._write_transcript(Path(td), [{"type": "user", "permissionMode": "auto"}])
            led = {**base, "permission_mode": "auto"}
            before = ct.constant_problems(led, pre)
            self.assertTrue(any("constant-binding" in p for p in before), before)
            after = ct.constant_problems({**led, "permission_mode": cr.recorded_permission_mode(t, led)}, pre)
            self.assertTrue(any("constant-binding" in p for p in after),
                            "the honest drift's refusal must survive the re-run, or it has no route")
            # edited: the session recorded default, the field was edited to auto; the refusal disappears
            t = self._write_transcript(Path(td), [{"type": "user", "permissionMode": "default"}])
            after = ct.constant_problems({**led, "permission_mode": cr.recorded_permission_mode(t, led)}, pre)
            self.assertEqual([p for p in after if "permission mode" in p], [],
                             "an edit to the field alone must disappear under the re-run, and be refused as ledger-made")

    # -- blocker 2: denials are read by code and printed beside each take -------------------------------

    @staticmethod
    def _denial_records(command: str, denied: bool) -> list[dict]:
        text = ("Permission for this tool use was denied. What required approval: " + command) if denied \
            else "ok\n"
        return [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": command}}]}},
            {"type": "user", "permissionMode": "default", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "is_error": denied, "content": text}]}},
        ]

    def test_blocker_2_a_denial_is_read_out_of_the_tool_result_with_its_command(self):
        import denials
        with tempfile.TemporaryDirectory() as td:
            t = self._write_transcript(Path(td), self._denial_records("cd /somewhere && ls", True))
            got = denials.denials_in(t)
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0]["command"], "cd /somewhere && ls")
            self.assertEqual(got[0]["tool"], "Bash")
            t = self._write_transcript(Path(td), self._denial_records("ls", False))
            self.assertEqual(denials.denials_in(t), [], "a call that ran is not a denial")
            # the sentence in agent prose or a user line is not a denial: only a tool result is read
            t = self._write_transcript(Path(td), [
                {"type": "assistant", "message": {"content": [
                    {"type": "text", "text": "Permission for this tool use was denied, it said."}]}}])
            self.assertEqual(denials.denials_in(t), [])

    def test_blocker_2_the_result_prints_the_count_beside_the_cell_and_quotes_the_commands(self):
        import prereg
        import result
        held = {("t", "positive", "m"): {"k": 0, "n": 3, "state": "RAN", "labels": ["wrong"] * 3}}
        g = {("t", "positive", "m"): {"takes": ["1", "2", "3"], "modes": {"default"}}}
        den = {("t", "positive", "m"): {"denied": 2, "commands": ["cd /x", "cd /y"]}}
        c = result.cell_state(("t", "positive", "m"), g, {}, {}, prereg.load(), held, den)
        self.assertEqual(c["denied"], 2)
        rec = {"planned_cells": 1, "planned_takes": 3, "graded_takes": 3, "complete_cells": 1, "cells": [c],
               "denials": [{"task": "t", "half": "positive", "model": "m", "take": "1", "denied": 2,
                            "commands": ["cd /x", "cd /y"]},
                           {"task": "t", "half": "positive", "model": "m", "take": "2", "denied": 0,
                            "commands": []}],
               "round_two": result.round_two_table(), "amendments": []}
        page = result.render(rec)
        self.assertIn("| 0 of 3 | 3 of 3 | 2 | default |", page)
        self.assertIn("## Denials, per graded take", page)
        self.assertIn("2 denied call(s): `cd /x`; `cd /y`", page)
        self.assertIn("take 2: no denial", page)
        self.assertEqual(result.structural_problems(rec), [])
        bad = json.loads(json.dumps(rec))
        bad["cells"][0]["denied_commands"] = ["cd /x"]
        self.assertTrue(any("quotes 1 command" in p for p in result.structural_problems(bad)))
        bad["cells"][0].pop("denied")
        self.assertTrue(any("no denial count" in p for p in result.structural_problems(bad)))

    def test_blocker_2_the_reader_says_out_loud_when_it_has_read_no_take(self):
        r = run(str(HERE / "denials.py"), "--check")
        self.assertEqual(r.returncode, 0, r.stdout)
        if not (HERE / "transcripts").is_dir():
            self.assertIn("having read 0 graded takes", r.stdout)
            self.assertIn("Not a pass", r.stdout)

    # -- blocker 3: the record of the driver change says what the code does -----------------------------

    def test_blocker_3_the_docstring_the_manifest_and_the_readme_agree_on_five_changes(self):
        import copy_manifest
        doc = (HERE / "drive.py").read_text().split('"""', 3)[1]
        self.assertIn("with five changes", doc)
        self.assertNotIn("is still passed", doc, "the docstring said auto was still passed; it is not")
        self.assertIn("--permission-mode default", doc)
        self.assertTrue(copy_manifest.EDITS["drive.py"].startswith("Five changes"))
        self.assertIn("--permission-mode default", copy_manifest.EDITS["drive.py"])
        self.assertNotIn("per-model expectation", copy_manifest.EDITS["drive.py"],
                         "the superseded ruling 2 semantics may not describe the driver")
        self.assertNotIn("keeps round 2's meaning", copy_manifest.EDITS["drive.py"])
        why = next(f["why"] for f in json.loads((HERE / "COPIED.json").read_text())["files"]
                   if f["path"].endswith("/drive.py"))
        self.assertEqual(why, copy_manifest.EDITS["drive.py"])
        readme = (HERE / "README.md").read_text()
        self.assertIn("carries five changes", readme)
        self.assertIn("**The mode passed is `default`, not `auto`**", readme)

    def test_blocker_3_the_readme_edited_count_is_the_manifests(self):
        words = {8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
                 15: "fifteen", 16: "sixteen"}
        edited = sum(1 for f in json.loads((HERE / "COPIED.json").read_text())["files"] if f.get("edited"))
        self.assertIn(f"with {words[edited]} files edited", (HERE / "README.md").read_text())

    # -- the follow-ups ------------------------------------------------------------------------------

    def test_should_1_the_run_date_is_the_takes_own_not_the_writing_day(self):
        import result
        src = (HERE / "result.py").read_text()
        self.assertNotIn("date.today", src)
        self.assertNotIn("from datetime import", src)
        self.assertIn("no graded take yet", result.run_dates()) if not (HERE / "transcripts").is_dir() else None
        with tempfile.TemporaryDirectory() as td:
            here = result.HERE
            try:
                result.HERE = Path(td)
                for take, s, e in (("1", "2026-09-25T10:00:00+00:00", "2026-09-25T10:03:00+00:00"),
                                   ("2", "2026-09-27T10:00:00+00:00", "2026-09-27T10:03:00+00:00")):
                    d = Path(td) / "transcripts" / "t" / "positive" / "m" / take
                    d.mkdir(parents=True)
                    (d / "driver-ledger.json").write_text(json.dumps({"started": s, "finished": e}))
                self.assertEqual(result.run_dates(), "2026-09-25 to 2026-09-27")
            finally:
                result.HERE = here

    def test_should_2_a_path_the_verdict_cannot_place_fails_it_wherever_the_check_runs(self):
        import fixture_walk as fw
        harness = "/private/tmp/claude-501/-private-var-folders-x/0beb75d1-ea09-4ea6-a471-a221cd99a87f/tasks/b3rn.output"
        self.assertEqual(fw.classify_path(harness, None), "harness")
        self.assertEqual(fw.classify_path("/usr/bin/python3", None), "system")
        # A path under none of the roots the verdict knows. Which root that is depends on where this
        # checkout lives (the study roots reach two levels above it, which is /Users on a Mac and /home
        # in CI), so the path is chosen from candidates rather than typed.
        elsewhere = next(p for p in ("/Users/nobody-here/checkouts/a-study/evals/x.py",
                                     "/home/nobody-here/checkouts/a-study/evals/x.py",
                                     "/opt/nobody-here/checkouts/a-study/evals/x.py")
                         if fw.classify_path(p, None) == "elsewhere")
        with tempfile.TemporaryDirectory() as td:
            t = self._write_transcript(Path(td), [
                {"type": "assistant", "message": {"content": [
                    {"type": "text", "text": f"reading {elsewhere} now"}]}}])
            rec = fw.replay(t)
            self.assertEqual(rec["verdict"], "unplaced")
            self.assertEqual(rec["unplaced_paths"], [elsewhere])
            # the reviewer's scenario: the study root is somewhere else (a clone, CI, a review copy) and the
            # walk names THIS checkout. It used to read clean; it must not.
            real = str(REPO / "evals" / "gap-study-3" / "prereg-draft.json")
            t = self._write_transcript(Path(td), [
                {"type": "assistant", "message": {"content": [{"type": "text", "text": f"cat {real}"}]}}])
            roots = fw.study_roots
            try:
                fw.study_roots = lambda: ["/somewhere/else/entirely"]
                self.assertNotEqual(fw.replay(t)["verdict"], "clean")
            finally:
                fw.study_roots = roots
            self.assertEqual(fw.replay(t)["verdict"], "leaks")
            t = self._write_transcript(Path(td), [
                {"type": "assistant", "message": {"content": [{"type": "text", "text": f"tail {harness}"}]}}])
            self.assertEqual(fw.replay(t)["verdict"], "clean", "the harness's own file is placed, not a leak")

    def test_should_3_the_enforcement_claim_names_the_scan_ci_runs(self):
        import prereg
        text = " ".join(prereg.load()["not_poolable"]["enforced_by"])
        self.assertIn("since the FREEZE", text)
        self.assertIn("verification/commit-body-note.md", text)
        self.assertNotIn("since the kickoff)", text)
        ci = (REPO / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn('lint_pooling.py --commits-since "$freeze"', ci)

    def test_should_4_the_mode_binding_reads_the_field_the_copied_checker_reads(self):
        import mode_binding as mb
        exp = mb.expected()
        ledger = {"model_requested": "claude-sonnet-5", "permission_mode_expected": "default",
                  "permission_mode_recorded": "default", "permission_mode": "auto"}
        _, bad = mb.judge(ledger, "default", exp, walks=False)
        self.assertTrue(any("the field the copied checker reads" in p for p in bad), bad)
        ledger["permission_mode"] = "default"
        _, ok = mb.judge(ledger, "default", exp, walks=False)
        self.assertEqual(ok, [])

    def test_nit_1_the_limitation_names_the_semicolon_and_find_forms(self):
        import prereg
        text = " ".join(prereg.load()["limitations_lines"])
        self.assertIn("semicolon", text)
        self.assertIn("-exec", text)

    def test_nit_2_the_mode_is_read_from_the_record_not_from_echoed_text(self):
        import mode_binding as mb
        import round2
        drive = TheDriverChangeIsWhatItSays._lift("mode_recorded", "modes_recorded")
        echo = {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": '{"permissionMode": "auto"}'}]}}
        with tempfile.TemporaryDirectory() as td:
            t = self._write_transcript(Path(td), [echo])
            for name, fn in (("mode_binding", mb.mode_of), ("drive", drive.mode_recorded)):
                with self.subTest(name):
                    self.assertEqual(fn(t), "unrecorded", "an echo inside a tool result is not the field")
            self.assertEqual(round2.modes_recorded(t), set())
            t = self._write_transcript(Path(td), [echo, {"type": "user", "permissionMode": "default"}])
            self.assertEqual(mb.mode_of(t), "default")
            self.assertEqual(drive.mode_recorded(t), "default")
            self.assertEqual(round2.modes_recorded(t), {"default"})


class AnInterruptedReviewerIsResumedNotReplaced(unittest.TestCase):
    """Round 3's reviewer was cut off by a session limit after 39 turns. The launcher resumes the same
    session under the same id; it never opens a second reviewer on the same bytes."""

    def setUp(self):
        self.launch = load_module("round3_launch_for_resume", HERE / "review_kit" / "launch.py")
        self.drive = self.launch.load_drive()

    def test_the_resume_argv_continues_the_same_id_with_the_harnesss_own_flag(self):
        sid = "86fe36ac-156b-59c3-b59b-5b2d23952438"
        argv = self.launch.resume_argv_for(sid, self.drive)
        self.assertIn("--resume", argv)
        self.assertEqual(argv[argv.index("--resume") + 1], sid)
        self.assertNotIn("--session-id", argv, "a resume never opens a new session")
        fresh = self.launch.argv_for(sid, self.drive)
        self.assertEqual(argv[argv.index("--model") + 1], fresh[fresh.index("--model") + 1], "the same reviewer model")
        for flag in self.drive.ISOLATION_FLAGS:
            self.assertIn(flag, argv, "the same isolation as the first launch")
        self.assertIn("--permission-prompts", argv)

    def test_a_resume_refuses_any_id_but_the_one_the_folder_was_launched_under(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "round-x"
            side = Path(td) / "round-x-launch"
            folder.mkdir(); side.mkdir()
            (side / "SESSION").write_text("11111111-1111-5111-8111-111111111111\n")
            code = self.launch.resume(folder, "22222222-2222-5222-8222-222222222222", self.drive)
            self.assertEqual(code, 2)
            self.assertEqual(list(side.glob("stream-resume-*")), [], "nothing was opened")

    def test_the_register_names_the_case(self):
        src = (HERE / "review_kit" / "rounds.py").read_text()
        self.assertIn("IS A PAUSE, AND IS RESUMED", src)


# ---------------------------------------------------------------------------------------------
# The reviewer's brief and the purpose page


class TheReviewKitIsPinnedAndBlind(unittest.TestCase):
    # The brief is pinned byte-identical from its first commit, so it named checks that later slices
    # built. Each one lived here until it existed, and the set had to be EMPTY before the freeze.
    # It is empty: every command the brief asks a reviewer to run now exists. Typed rather than
    # inferred, because `{}` is a dict and would have made this test pass over nothing.
    PLANNED: set[str] = set()

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
