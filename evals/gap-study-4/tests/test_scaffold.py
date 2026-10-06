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

    def test_no_round3_record_is_copied(self):
        records = ("prereg.json", "prereg-draft.json", "takes.json", "COPIED.json", "RESULT.md", "COSTS.md",
                   "PROGRESS.md", "results/", "transcripts/", "rehearsals/", "walks/", "verification/", "cases/",
                   "graders/", "test_round3.py", "review_kit/rounds.json", "review_kit/prefreeze-")
        sources = [e.get("source") or "" for e in json.loads(OWN_FRAGMENT.read_text())["files"]]
        hits = [s for s in sources for r in records if s.startswith(f"{cm.SOURCE_DIR}/{r}")]
        self.assertEqual(hits, [])
        sources.append(f"{cm.SOURCE_DIR}/results/x.json")
        self.assertTrue([s for s in sources for r in records if s.startswith(f"{cm.SOURCE_DIR}/{r}")])


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

    def test_an_empty_battery_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(test_round4.main(Path(d)), 1)
        self.assertIn("a battery that runs nothing is not a pass", out.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
