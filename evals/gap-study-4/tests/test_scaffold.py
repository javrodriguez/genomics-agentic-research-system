#!/usr/bin/env python3
"""CP1's scaffold: the copy manifest, the copied modules' import paths, study.py's binding and the local runner.

    python3 -W ignore evals/gap-study-4/tests/test_scaffold.py

Every test that guards something also mutates what it guards, in memory or in a temporary folder, and watches
its check go red. Nothing under the study folder or any frozen round is written.

No model, no network, stdlib only.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent.parent
REPO = STUDY_DIR.parent.parent
if str(STUDY_DIR) not in sys.path:
    sys.path.insert(0, str(STUDY_DIR))

import copy_manifest as cm  # noqa: E402
import run_checks  # noqa: E402
import study  # noqa: E402
import test_round4  # noqa: E402

LANE = "w1a-cp1-scaffold"
OWN_FRAGMENT = cm.FRAGMENTS / f"{LANE}.json"

# Copied modules that cannot import yet, each with the exact error it stops on. Each waits on a later
# checkpoint's file; when that file lands this test goes red and the entry must go.
BLOCKED = {
    "drive.py": "SystemExit: no pre-registration: neither prereg.json nor prereg-draft.json exists.",
    "run.py": "ModuleNotFoundError: No module named 'labels'",
}

# Run in a fresh interpreter, from a folder outside the study, as `python3 <path>` would: the file's own folder is
# sys.path[0] and the cwd adds nothing.
PROBE = r"""
import json, os, sys
path, override = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.dirname(path))
src = open(override if override else path).read()
sys.argv = [path]
ns = {"__name__": "probe_target", "__file__": path}
err = None
try:
    exec(compile(src, path, "exec"), ns)
except BaseException as e:
    err = f"{type(e).__name__}: {e}"
files = sorted({getattr(m, "__file__", None) for m in list(sys.modules.values())} - {None})
print(json.dumps({"error": err, "files": files}))
"""


def probe(rel: str, override: Path | None = None) -> dict:
    with tempfile.TemporaryDirectory() as cwd:
        p = subprocess.run([sys.executable, "-W", "ignore", "-c", PROBE, str(STUDY_DIR / rel), str(override or "")],
                           capture_output=True, text=True, cwd=cwd, env={"PYTHONDONTWRITEBYTECODE": "1",
                                                                         "PATH": "/usr/bin:/bin"})
    return json.loads(p.stdout.strip().splitlines()[-1])


def foreign(files: list[str]) -> list[str]:
    """Loaded files under evals/ that are neither this study's nor the shared transcript parser."""
    evals = (REPO / "evals").resolve()
    out = []
    for f in files:
        fp = Path(f).resolve()
        if evals in fp.parents and STUDY_DIR not in fp.parents and fp != evals / "transcript.py":
            out.append(str(fp.relative_to(REPO)))
    return out


def copied_modules() -> list[str]:
    rec = json.loads(OWN_FRAGMENT.read_text())
    return [e["path"] for e in rec["files"] if e["status"] != "new" and e["path"].endswith(".py")]


def own_fragment_in(folder: Path, files: list[dict] | None = None, name: str = LANE) -> None:
    rec = json.loads(OWN_FRAGMENT.read_text())
    (folder / f"{name}.json").write_text(json.dumps({"lane": name, "files": files if files is not None
                                                     else rec["files"]}))


class TheManifest(unittest.TestCase):
    def test_check_passes_on_the_folder(self):
        p = subprocess.run([sys.executable, str(STUDY_DIR / "copy_manifest.py"), "--check"], capture_output=True,
                           text=True, cwd=str(REPO), env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(p.stdout.startswith("ok: "), p.stdout)

    def test_a_path_claimed_by_two_fragments_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            own_fragment_in(d)
            self.assertEqual(cm.problems(d, pinned=False), [])
            (d / "other-lane.json").write_text(json.dumps({"lane": "other-lane", "files": [
                {"path": "takes.py", "status": "identical", "source": "evals/gap-study-3/takes.py"}]}))
            bad = cm.problems(d, pinned=False)
            self.assertTrue(any("takes.py is claimed by" in b and "a file has one owner" in b for b in bad), bad)

    def test_an_edited_fixture_builder_is_refused(self):
        real = cm.read_copy
        for name in cm.UNEDITABLE:
            mutated = lambda path, name=name: real(path) + (b"\n# edited\n" if path == name else b"")
            bad = cm.problems(pinned=False, read=mutated)
            self.assertTrue(any(name in b and "fixture builder" in b for b in bad), (name, bad))
            # recording it as edited, with a reason, does not help
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                rec = json.loads(OWN_FRAGMENT.read_text())["files"]
                for e in rec:
                    if e["path"] == name:
                        e["status"], e["reason"] = "edited", "an honest-sounding reason"
                own_fragment_in(d, rec)
                bad = cm.problems(d, pinned=False, read=mutated)
                self.assertTrue(any(name in b and "that is a FAIL" in b for b in bad), (name, bad))

    def test_a_copy_that_differs_without_an_edited_entry_is_refused(self):
        real = cm.read_copy
        for name in ("drive.py", "check_take.py", "lexicons/permission-stop.json", "review_kit/rounds.py"):
            mutated = lambda path, name=name: real(path) + (b" " if path == name else b"")
            bad = cm.problems(pinned=False, read=mutated)
            self.assertIn(f"{name} ({LANE}) differs from evals/gap-study-3/{name} at {cm.SOURCE_COMMIT} and has no "
                          f"`edited` entry", bad)

    def test_an_edited_entry_that_does_not_differ_is_refused(self):
        real = cm.read_copy
        unedit = lambda path: (cm.source_bytes(f"{cm.SOURCE_DIR}/{path}") if path == "study.py" else real(path))
        bad = cm.problems(pinned=False, read=unedit)
        self.assertTrue(any("study.py" in b and "byte-identical" in b for b in bad), bad)

    def test_an_unclaimed_or_missing_file_is_refused(self):
        present = cm.files_here()
        bad = cm.problems(pinned=False, present=present | {"stray.py"})
        self.assertTrue(any(b.startswith("stray.py is under") for b in bad), bad)
        bad = cm.problems(pinned=False, present=present - {"takes.py"})
        self.assertTrue(any("takes.py" in b and "does not exist" in b for b in bad), bad)

    def test_a_copy_recorded_as_new_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            rec = json.loads(OWN_FRAGMENT.read_text())["files"]
            for e in rec:
                if e["path"] == "takes.py":
                    e.pop("source")
                    e["status"], e["reason"] = "new", "claimed new"
            own_fragment_in(d, rec)
            bad = cm.problems(d, pinned=False)
            self.assertTrue(any("takes.py" in b and "it is a copy and must say so" in b for b in bad), bad)

    def test_a_fragment_must_carry_its_own_lane_and_shape(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            rec = json.loads(OWN_FRAGMENT.read_text())
            (d / f"{LANE}.json").write_text(json.dumps({"lane": "someone-else", "files": rec["files"]}))
            bad = cm.problems(d, pinned=False)
            self.assertTrue(any("a fragment's lane is its file name" in b for b in bad), bad)
            (d / f"{LANE}.json").write_text(json.dumps({"lane": LANE, "files": rec["files"] + [
                {"path": "x", "status": "copied"}]}))
            bad = cm.problems(d, pinned=False)
            self.assertTrue(any("status 'copied'" in b for b in bad), bad)

    def test_the_frozen_paths_are_bound(self):
        self.assertEqual([b for b in cm.problems() if "since" in b or "working tree" in b], [])
        saved = cm.BASE_COMMIT
        try:
            cm.BASE_COMMIT = cm.SOURCE_COMMIT  # round 3 gained its verification records after its done commit
            bad = cm.problems()
            self.assertTrue(any(b.startswith("evals/gap-study-3 has changed since") for b in bad), bad)
        finally:
            cm.BASE_COMMIT = saved

    def later_lane(self, files: list[dict], blobs: dict[str, bytes]):
        """problems() with this lane's fragment plus a later lane's, whose files exist with the given bytes."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            own_fragment_in(d)
            (d / "zz-later.json").write_text(json.dumps({"lane": "zz-later", "files": files}))
            read = lambda path: blobs[path] if path in blobs else cm.read_copy(path)
            return cm.problems(d, present=cm.files_here() | set(blobs), read=read, pinned=False)

    def test_a_round3_record_copied_by_any_lane_is_refused(self):
        # review W1A-1: a later lane's fragment copying a record or a grader of round 3 must go red
        for src in ("evals/gap-study-3/prereg.json", "evals/gap-study-3/takes.json", "evals/gap-study-3/RESULT.md",
                    "evals/gap-study-3/graders/labels.py", "evals/gap-study-3/test_round3.py",
                    "evals/gap-study-3/review_kit/rounds.json"):
            data = cm.source_bytes(src)
            self.assertIsNotNone(data, src)
            bad = self.later_lane([{"path": "prior/x", "status": "identical", "source": src}], {"prior/x": data})
            self.assertTrue(any("one of round 3's records" in b for b in bad), (src, bad))

    def test_a_transcript_copied_by_any_lane_is_refused(self):
        listed = cm.git("ls-tree", "-r", "--name-only", cm.SOURCE_COMMIT, "--", "evals/gap-study-3/transcripts/")
        src = next(n for n in listed.stdout.decode().splitlines() if n.endswith("transcript.jsonl"))
        bad = self.later_lane([{"path": "data/t.jsonl", "status": "identical", "source": src}],
                              {"data/t.jsonl": cm.source_bytes(src)})
        self.assertTrue(any("one of round 3's records" in b for b in bad), bad)

    def test_a_source_outside_the_allowed_ones_is_refused(self):
        src = "evals/gap-study-2/takes.py"
        bad = self.later_lane([{"path": "x.py", "status": "identical", "source": src}], {"x.py": cm.source_bytes(src)})
        self.assertTrue(any("not an allowed copy source" in b for b in bad), bad)
        allowed = self.later_lane([{"path": "intervals.py", "status": "identical",
                                    "source": "evals/gap-study-intervals/intervals.py"}],
                                  {"intervals.py": cm.source_bytes("evals/gap-study-intervals/intervals.py")})
        self.assertEqual(allowed, [])

    def test_a_record_recorded_as_new_at_another_path_is_refused(self):
        data = cm.source_bytes("evals/gap-study-3/takes.json")
        bad = self.later_lane([{"path": "prior/takes.json", "status": "new", "reason": "a fresh file"}],
                              {"prior/takes.json": data})
        self.assertTrue(any("its bytes are a file under evals/" in b for b in bad), bad)
        ok = self.later_lane([{"path": "fresh.txt", "status": "new", "reason": "a fresh file"}],
                             {"fresh.txt": b"round 4 only\n"})
        self.assertEqual(ok, [])

    def test_the_record_guard_itself_is_bound(self):
        data = cm.source_bytes("evals/gap-study-3/prereg.json")
        saved = cm.ROUND3_RECORDS
        try:
            cm.ROUND3_RECORDS = ()
            bad = self.later_lane([{"path": "p.json", "status": "identical", "source": "evals/gap-study-3/prereg.json"}],
                                  {"p.json": data})
            self.assertFalse(any("one of round 3's records" in b for b in bad), bad)
        finally:
            cm.ROUND3_RECORDS = saved

    def test_a_tracked_cache_is_refused(self):
        # review W1A-3: a force-added .pyc or __pycache__ entry must be claimed-or-refused, never ignored
        saved = cm.tracked_here
        try:
            cm.tracked_here = lambda: saved() | {"graders/labels.pyc", "__pycache__/x.py"}
            bad = cm.problems(pinned=False, present=cm.files_here())
            self.assertTrue(any("graders/labels.pyc is a tracked interpreter cache" in b for b in bad), bad)
            self.assertTrue(any("__pycache__/x.py is a tracked interpreter cache" in b for b in bad), bad)
        finally:
            cm.tracked_here = saved
        self.assertFalse(any(cm.is_cache(n) for n in cm.files_here()))

    def test_every_entry_refusal_fires(self):
        # review W1A-5: each refusal branch of problems(), driven once
        study_src = "evals/gap-study-3/study.py"
        takes = cm.source_bytes("evals/gap-study-3/takes.py")
        cases = [
            ({"path": "takes.py", "status": "identical", "source": "evals/gap-study-3/takes.py", "reason": "x"},
             "is identical and carries a reason"),
            ({"path": "takes.py", "status": "identical"}, "names no source"),
            ({"path": "fresh.txt", "status": "new", "source": study_src, "reason": "x"}, "is new and names a source"),
            ({"path": "fresh.txt", "status": "new"}, "is new and carries no reason"),
            ({"path": "study.py", "status": "edited", "source": study_src}, "no reason is recorded"),
            ({"path": "study.py", "status": "edited", "source": study_src, "reason": "  "},
             "its reason is not a non-empty string"),
            ({"path": "takes.py", "status": "identical", "source": "evals/gap-study-3/no-such-file.py"},
             "does not exist at"),
        ]
        for entry, want in cases:
            rec = [e for e in json.loads(OWN_FRAGMENT.read_text())["files"] if e["path"] != entry["path"]] + [entry]
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                own_fragment_in(d, rec)
                read = lambda path: b"round 4 only\n" if path == "fresh.txt" else cm.read_copy(path)
                bad = cm.problems(d, present=cm.files_here() | {"fresh.txt"}, read=read, pinned=False)
            self.assertTrue(any(want in b for b in bad), (entry, want, bad))
        self.assertIsNotNone(takes)

    def test_a_fixture_builder_from_another_source_or_unclaimed_is_refused(self):
        rec = json.loads(OWN_FRAGMENT.read_text())["files"]
        moved = [dict(e, source="evals/gap-study-3/fixtures/gen_source.py") if e["path"] == "fixtures/gen_project.py"
                 else e for e in rec]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            own_fragment_in(d, moved)
            bad = cm.problems(d, pinned=False, read=lambda p: cm.source_bytes("evals/gap-study-3/fixtures/gen_source.py")
                              if p == "fixtures/gen_project.py" else cm.read_copy(p))
        self.assertTrue(any("fixtures/gen_project.py" in b and "whose source is" in b for b in bad), bad)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            own_fragment_in(d, [e for e in rec if e["path"] != "fixtures/gen_source.py"])
            bad = cm.problems(d, pinned=False)
        self.assertTrue(any("fixtures/gen_source.py, a copied fixture builder, is not claimed" in b for b in bad), bad)

    def test_the_working_tree_branch_of_the_pin_fires(self):
        saved = cm.git
        def fake(*args):
            if args[:2] == ("diff", "--quiet") and "HEAD" not in args:
                return subprocess.CompletedProcess(args, 1, b"", b"")
            return saved(*args)
        try:
            cm.git = fake
            bad = cm.problems()
        finally:
            cm.git = saved
        self.assertTrue(any("differs from" in b and "in the working tree" in b for b in bad), bad)

    def test_derive_refuses_a_bad_manifest(self):
        # review N9: the record the freeze writes comes only from a clean manifest
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import copy_manifest as cm; "
                "cm.problems = lambda *a, **k: ['planted']; sys.argv = ['x', '--derive']; sys.exit(cm.main())")
        p = subprocess.run([sys.executable, "-c", code, str(STUDY_DIR)], capture_output=True, text=True, cwd=str(REPO),
                           env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL planted", p.stdout)


class TheImports(unittest.TestCase):
    def test_every_copied_module_imports_from_inside_this_folder(self):
        mods = copied_modules()
        self.assertGreater(len(mods), 30)
        for rel in mods:
            with self.subTest(rel):
                got = probe(rel)
                self.assertEqual(foreign(got["files"]), [], rel)
                if rel in BLOCKED:
                    self.assertIsNotNone(got["error"], f"{rel} now imports: take it off BLOCKED")
                    self.assertTrue(got["error"].startswith(BLOCKED[rel]), got["error"])
                else:
                    self.assertIsNone(got["error"], rel)

    def test_the_named_imports_resolve_here(self):
        # drive.py:125-128 and freeze_rehearsal.py:59-61, named by the plan
        for rel, names in (("drive.py", ("prereg", "study", "takes", "scrub")),
                           ("freeze_rehearsal.py", ("freeze", "scratch_git", "study"))):
            got = probe(rel)
            for n in names:
                self.assertIn(str(STUDY_DIR / f"{n}.py"), got["files"], (rel, n))

    def test_an_import_reaching_round3_goes_red(self):
        src = (STUDY_DIR / "takes.py").read_text()
        needle = "sys.path.insert(0, str(HERE))"
        self.assertIn(needle, src)
        with tempfile.TemporaryDirectory() as d:
            alt = Path(d) / "takes.py"
            alt.write_text(src.replace(needle, 'sys.path.insert(0, str(HERE.parent / "gap-study-3"))', 1))
            got = probe("takes.py", alt)
        self.assertTrue(any(f.startswith("evals/gap-study-3/") for f in foreign(got["files"])), got)


class TheBinding(unittest.TestCase):
    @staticmethod
    def problems(s) -> list[str]:
        out = []
        if s.STUDY != "gap-study-4" or s.STUDY_REL != "evals/gap-study-4":
            out.append("round name")
        if s.ROUND1_REL != "evals/gap-study-3" or s.ROUND1 != REPO / "evals" / "gap-study-3":
            out.append("prior round")
        if tuple(s.ARMS) != ("A", "C"):
            out.append("arms")
        for m in (s.SECTION_TITLE, s.SUMMARY_START, s.SUMMARY_END, s.SECTION_END):
            if "gap-study-4" not in m and "round 4" not in m:
                out.append(f"marker {m}")
        if s.rel("x.py") != "evals/gap-study-4/x.py":
            out.append("rel")
        return out

    def test_study_names_round_4(self):
        self.assertEqual(self.problems(study), [])

    def test_a_wrong_binding_goes_red(self):
        base = {k: getattr(study, k) for k in dir(study) if not k.startswith("__")}
        for k, v in (("STUDY", "gap-study-3"), ("ROUND1_REL", "evals/gap-study-2"), ("ARMS", ("A", "B", "C")),
                     ("SUMMARY_START", "<!-- gap-study-3:summary -->")):
            s = types.SimpleNamespace(**{**base, k: v})
            self.assertTrue(self.problems(s), k)


class TheRunner(unittest.TestCase):
    def test_commands_reads_every_lane_file_and_skips_comments(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "a.txt").write_text("# a comment\n\ntrue\n")
            (d / "b.txt").write_text("false\n  # indented comment\n")
            got = run_checks.commands(d)
        self.assertEqual([c for _, c in got], [run_checks.BATTERY, "true", "false"])
        self.assertEqual(run_checks.commands(Path("/nonexistent-folder")), [("test_round4", run_checks.BATTERY)])

    def test_a_failing_command_fails_the_run_and_the_line_is_fixed(self):
        with redirect_stdout(io.StringIO()) as out:
            k, n = run_checks.run_all([("x", "true"), ("y", "false")])
        self.assertEqual((k, n), (1, 2))
        self.assertIn("FAIL [y] exit 1", out.getvalue())
        self.assertEqual(run_checks.summary(k, n), "run_checks: 1 of 2 commands passed")
        self.assertEqual(run_checks.verdict(k, n), 1)
        self.assertEqual(run_checks.verdict(2, 2), 0)
        self.assertEqual(run_checks.verdict(0, 0), 1)

    def test_main_prints_the_summary_last(self):
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import run_checks as r; from pathlib import Path; "
                "r.BATTERY = 'true'; r.CHECKS = Path(sys.argv[2]); sys.exit(r.main())")
        with tempfile.TemporaryDirectory() as d:
            for lines, want_code, want_last in (("true\n", 0, "run_checks: 2 of 2 commands passed"),
                                                ("true\nfalse\n", 1, "run_checks: 2 of 3 commands passed")):
                (Path(d) / "l.txt").write_text(lines)
                p = subprocess.run([sys.executable, "-c", code, str(STUDY_DIR), d], capture_output=True, text=True)
                self.assertEqual(p.returncode, want_code, p.stdout + p.stderr)
                self.assertEqual(p.stdout.splitlines()[-1], want_last)

    def test_a_misnamed_or_empty_checks_file_counts_as_a_failure(self):
        # review W1A-4
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "w1a.txt").write_text("true\n")
            (d / "w1b-lane.text").write_text("true\n")
            (d / "W1C.TXT").write_text("true\n")
            (d / "w1d.txt").write_text("# only a comment\n\n")
            got = run_checks.file_problems(d)
        self.assertEqual(sorted(n for n, _ in got), ["W1C.TXT", "w1b-lane.text", "w1d.txt"])
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import run_checks as r; from pathlib import Path; "
                "r.BATTERY = 'true'; r.CHECKS = Path(sys.argv[2]); sys.exit(r.main())")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.txt").write_text("true\n")
            (Path(d) / "b.TXT").write_text("true\n")
            p = subprocess.run([sys.executable, "-c", code, str(STUDY_DIR), d], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertEqual(p.stdout.splitlines()[-1], "run_checks: 2 of 3 commands passed")

    def test_a_timeout_or_a_crash_is_a_failure_and_the_line_stays_last(self):
        # review N1
        saved = run_checks.TIMEOUT_S
        try:
            run_checks.TIMEOUT_S = 1
            with redirect_stdout(io.StringIO()) as out:
                k, n = run_checks.run_all([("slow", "sleep 5"), ("bytes", "printf '\\377\\376'; exit 1")])
        finally:
            run_checks.TIMEOUT_S = saved
        self.assertEqual((k, n), (0, 2))
        self.assertIn("FAIL [slow] exit timeout", out.getvalue())
        self.assertIn("FAIL [bytes] exit 1", out.getvalue())
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import run_checks as r; "
                "r.commands = lambda: (_ for _ in ()).throw(RuntimeError('boom')); sys.exit(r.main())")
        p = subprocess.run([sys.executable, "-c", code, str(STUDY_DIR)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(p.stdout.splitlines()[-1], "run_checks: 0 of 1 commands passed")

    def test_this_lane_lists_its_check(self):
        self.assertIn(("w1a-cp1-scaffold.txt:2", "python3 evals/gap-study-4/copy_manifest.py --check"),
                      run_checks.commands())


class TheBattery(unittest.TestCase):
    def test_discovery_finds_this_file(self):
        names = set()

        def walk(s):
            for t in s:
                walk(t) if isinstance(t, unittest.TestSuite) else names.add(type(t).__module__)
        walk(test_round4.suite())
        self.assertIn("test_scaffold", names)

    def test_a_module_with_no_test_fails_even_beside_a_live_one(self):
        # review W1A-2: the count is per module
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "test_a.py").write_text("import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        pass\n")
            (d / "test_b.py").write_text("class NotATestCase:\n    def test_y(self):\n        pass\n")
            (d / "sub").mkdir()
            (d / "sub" / "test_c.py").write_text("import unittest\nclass T(unittest.TestCase):\n    def test_z(self):\n        pass\n")
            got = test_round4.module_problems(d)
            self.assertTrue(any(g.startswith("test_b.py holds no test") for g in got), got)
            self.assertTrue(any(g.startswith("sub/test_c.py is below") for g in got), got)
            with redirect_stdout(io.StringIO()), __import__("contextlib").redirect_stderr(io.StringIO()):
                self.assertEqual(test_round4.main(d), 1)
            (d / "test_b.py").unlink()
            (d / "sub" / "test_c.py").unlink()
            with redirect_stdout(io.StringIO()), __import__("contextlib").redirect_stderr(io.StringIO()):
                self.assertEqual(test_round4.main(d), 0)
        self.assertEqual(test_round4.module_problems(), [])

    def test_an_empty_battery_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(test_round4.main(Path(d)), 1)
        self.assertIn("a battery that runs nothing is not a pass", out.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
