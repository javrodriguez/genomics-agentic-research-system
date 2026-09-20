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
                # the false positive this guard raised against the carried keys, kept as a case so the
                # narrowing cannot be undone without a red
                "The driver proves it by walking up from the checkout to the filesystem root.",
                "Claude Code walks up from the working directory collecting instruction files."]
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
        passed = self.draft["driver_constants"]["permission_mode"]
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

    def test_both_owner_gates_start_null_and_are_named(self):
        self.assertIsNone(self.draft["driver_change"]["approved_by_owner"])
        keys = [r["source_key"] for r in self.draft["carried_rulings"]]
        self.assertIn("permission_stop_rule", keys,
                      "asked-to-proceed's broad reading is named by the goal as one that must be re-put")
        for r in self.draft["carried_rulings"]:
            with self.subTest(r["source_key"]):
                self.assertIsNone(r["reaffirmed_by_owner"])
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
        self.assertIn("more permissive", text)
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
# The reviewer's brief and the purpose page


class TheReviewKitIsPinnedAndBlind(unittest.TestCase):
    # The brief is pinned byte-identical from its first commit, so it names checks that later slices
    # build. Each one lives here until it exists; the set must be EMPTY before the freeze, and the test
    # below fails if the study is frozen while anything is still planned.
    PLANNED = {
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
