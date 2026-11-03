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
    """Every .py file copied into this folder (status identical or edited), whichever lane's fragment claims it now.

    Edit W7A-gap4-1 (lane w7a, W6-claims-1): this read a hand list of fragments, which went stale as claims moved
    between lanes (drive.py, check_take.py and mode_binding.py on 11 Oct) and never held w5b's pipeline copies. It now
    reads every fragment through copy_manifest's own loader, so an ownership move cannot drop a module."""
    entries, problems = cm.load_fragments()
    if problems:
        raise ValueError("COPIED.d does not load: " + "; ".join(problems))
    # W7A-R1-5: every non-new .py copy, the five from outside the prior round included.
    return [e["path"] for _, e in entries if e["status"] != "new" and e["path"].endswith(".py")]


def own_fragment_in(folder: Path, files: list[dict] | None = None, name: str = LANE) -> None:
    """This lane's fragment (or `files` in its place), and every OTHER lane's real fragment beside it, so a test's
    temporary COPIED.d claims the whole folder once lanes merge (the wave 1 merge showed the gap)."""
    rec = json.loads(OWN_FRAGMENT.read_text())
    for frag in cm.FRAGMENTS.glob("*.json"):
        if frag.stem != LANE:
            (folder / frag.name).write_text(frag.read_text())
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
        # Departure w6e-1 (lane w6e, ruling S5-gap4-1 moved drive.py to w6e as an edited copy): denials.py, an
        # identical copy this lane still claims, stands in for drive.py, so the four cases stay four. Departure w6h-1
        # (lane w6h, ruling S6-gap4-1 moved check_take.py to w6h as an edited copy): allowlist.py stood in for it, and
        # since lane freeze-gates-fix S9 retired round 4's allowlist.py (glitch-f1's ruling), ci_conclusion.py does.
        # Departure w7d-1 (lane w7d, ruling W7D-gap4-1 moved review_kit/rounds.py to w7d as an edited copy):
        # review_kit/launch.py, an identical copy this lane still claims, stands in for it. Departure review-kit-port-1
        # (lane review-kit-port moved review_kit/launch.py there as an edited copy): review_kit/build_kit.py stands in.
        # Departure review-kit-port-2 (build_kit.py moved there too): smoke_run_tree.py stands in.
        for name in ("denials.py", "ci_conclusion.py", "lexicons/permission-stop.json", "smoke_run_tree.py"):
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
        bad = cm.problems(pinned=False, present=present - {"prereg.py"})
        self.assertTrue(any("prereg.py" in b and "does not exist" in b for b in bad), bad)

    def test_a_copy_recorded_as_new_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            rec = json.loads(OWN_FRAGMENT.read_text())["files"]
            # round2.py: a byte-identical copy (prereg.py, the earlier example, is an edited copy since slice S3)
            for e in rec:
                if e["path"] == "round2.py":
                    e.pop("source")
                    e["status"], e["reason"] = "new", "claimed new"
            own_fragment_in(d, rec)
            bad = cm.problems(d, pinned=False)
            self.assertTrue(any("round2.py" in b and "it is a copy and must say so" in b for b in bad), bad)

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
        allowed = self.later_lane([{"path": "zz_intervals_probe.py", "status": "identical",
                                    "source": "evals/gap-study-intervals/intervals.py"}],
                                  {"zz_intervals_probe.py": cm.source_bytes("evals/gap-study-intervals/intervals.py")})
        self.assertEqual(allowed, [])

    def test_a_record_recorded_as_new_at_another_path_is_refused(self):
        data = cm.source_bytes("evals/gap-study-3/takes.json")
        bad = self.later_lane([{"path": "prior/takes.json", "status": "new", "reason": "a fresh file"}],
                              {"prior/takes.json": data})
        self.assertTrue(any("its bytes are one of round 3's records" in b for b in bad), bad)
        other = cm.git("show", f"{cm.BASE_COMMIT}:evals/gap-study-2/takes.py").stdout
        self.assertTrue(other)
        bad = self.later_lane([{"path": "prior/old.py", "status": "new", "reason": "a fresh file"}],
                              {"prior/old.py": other})
        self.assertTrue(any("its bytes are a file under evals/" in b for b in bad), bad)
        ok = self.later_lane([{"path": "fresh.txt", "status": "new", "reason": "a fresh file"}],
                             {"fresh.txt": b"round 4 only\n"})
        self.assertEqual(ok, [])

    def test_the_record_guard_itself_is_bound(self):
        data = cm.source_bytes("evals/gap-study-3/prereg.json")
        saved = (cm.ROUND3_RECORDS, cm._RECORD_BLOBS)
        try:
            cm.ROUND3_RECORDS, cm._RECORD_BLOBS = (), set()   # both record guards off: the source and the bytes
            bad = self.later_lane([{"path": "p.json", "status": "identical", "source": "evals/gap-study-3/prereg.json"}],
                                  {"p.json": data})
            self.assertFalse(any("one of round 3's records" in b for b in bad), bad)
        finally:
            cm.ROUND3_RECORDS, cm._RECORD_BLOBS = saved

    def test_a_record_recorded_as_edited_is_refused(self):
        # review round 2 W1A2-1: a record's exact bytes under an `edited` entry, whatever source it names
        cases = [("prior/takes.json", "evals/gap-study-3/takes.json", "evals/gap-study-3/takes.py"),
                 ("prior/labels.py", "evals/gap-study-3/graders/labels.py", "evals/fixtures/gen_fastq.py")]
        for path, record, named in cases:
            bad = self.later_lane([{"path": path, "status": "edited", "source": named, "reason": "an edit"}],
                                  {path: cm.source_bytes(record)})
            self.assertTrue(any(f"{path} (zz-later): its bytes are one of round 3's records" in b for b in bad),
                            (path, bad))

    def test_an_edited_copy_of_a_record_source_is_refused_by_its_source(self):
        # review round 3 W1A3-1 (1): bytes that are no record's (a record plus a line), naming a record as source
        data = cm.source_bytes("evals/gap-study-3/takes.json") + b"\n"
        bad = self.later_lane([{"path": "prior/takes.json", "status": "edited", "reason": "an edit",
                                "source": "evals/gap-study-3/takes.json"}], {"prior/takes.json": data})
        self.assertTrue(any("its source evals/gap-study-3/takes.json is one of round 3's records" in b for b in bad), bad)
        self.assertFalse(any("its bytes are one of round 3's records" in b for b in bad), bad)

    def test_an_edited_entry_holding_another_files_bytes_must_be_identical(self):
        # review round 3 W1A3-1 (2): the bytes of a non-record file under evals/, under an `edited` entry
        data = cm.git("show", f"{cm.BASE_COMMIT}:evals/fixtures/PILOT-RECORD.md").stdout
        self.assertTrue(data)
        bad = self.later_lane([{"path": "notes.md", "status": "edited", "reason": "an edit",
                                "source": "evals/gap-study-3/takes.py"}], {"notes.md": data})
        self.assertTrue(any("notes.md (zz-later) is recorded as edited but its bytes are a file under evals/; "
                            "record it identical from that file" in b for b in bad), bad)
        self.assertFalse(any("one of round 3's records" in b for b in bad), bad)

    def test_a_failing_git_listing_is_a_problem_never_an_empty_set(self):
        # review round 3 W1A3-6: a failed `git ls-tree` must not leave the record and prior guards reading nothing
        saved = (cm.git, cm._RECORD_BLOBS, cm._PRIOR_BLOBS)
        def broken(*args):
            if args[0] == "ls-tree":
                return subprocess.CompletedProcess(args, 128, b"", b"fatal: simulated")
            return saved[0](*args)
        try:
            cm.git, cm._RECORD_BLOBS, cm._PRIOR_BLOBS = broken, None, None
            bad = self.later_lane([{"path": "fresh.txt", "status": "new", "reason": "fresh"}], {"fresh.txt": b"x\n"})
        finally:
            cm.git, cm._RECORD_BLOBS, cm._PRIOR_BLOBS = saved
        self.assertTrue(any("cannot list" in b for b in bad), bad)

    def test_main_needs_every_commit_it_reads(self):
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import copy_manifest as cm; "
                "cm.SHARED_COMMIT = '0' * 40; sys.argv = ['x', '--check']; sys.exit(cm.main())")
        p = subprocess.run([sys.executable, "-c", code, str(STUDY_DIR)], capture_output=True, text=True, cwd=str(REPO),
                           env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("is not in this clone", p.stdout)

    def test_a_shared_builder_is_copied_identical_only(self):
        # review round 2 W1A2-4: the named builders only, never edited; the rest of evals/fixtures/ not at all
        data = cm.source_bytes("evals/fixtures/gen_fastq.py")
        ok = self.later_lane([{"path": "shared/gen_fastq.py", "status": "identical", "source": "evals/fixtures/gen_fastq.py"}],
                             {"shared/gen_fastq.py": data})
        self.assertEqual(ok, [])
        bad = self.later_lane([{"path": "shared/gen_fastq.py", "status": "edited", "source": "evals/fixtures/gen_fastq.py",
                                "reason": "tuned"}], {"shared/gen_fastq.py": data + b"\n# tuned\n"})
        self.assertTrue(any("uneditable" in b for b in bad), bad)
        bad = self.later_lane([{"path": "x.md", "status": "identical", "source": "evals/fixtures/PILOT-RECORD.md"}],
                              {"x.md": cm.source_bytes("evals/fixtures/PILOT-RECORD.md")})
        self.assertTrue(any("not an allowed copy source" in b for b in bad), bad)

    def test_shared_sources_at_the_shared_commit_equal_round_3s_where_both_exist(self):
        for src in cm.ALLOWED_SOURCES:
            if src.endswith("/"):
                continue
            here = cm.git("show", f"{cm.SHARED_COMMIT}:{src}")
            there = cm.git("show", f"{cm.SOURCE_COMMIT}:{src}")
            self.assertEqual(here.returncode, 0, src)
            if there.returncode == 0:
                self.assertEqual(here.stdout, there.stdout, src)

    def test_a_builder_recorded_as_new_with_edited_bytes_is_refused(self):
        rec = [e for e in json.loads(OWN_FRAGMENT.read_text())["files"] if e["path"] != "fixtures/gen_source.py"]
        rec.append({"path": "fixtures/gen_source.py", "status": "new", "reason": "rewritten"})
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            own_fragment_in(d, rec)
            bad = cm.problems(d, pinned=False, read=lambda p: b"# rewritten\n" if p == "fixtures/gen_source.py"
                              else cm.read_copy(p))
        self.assertTrue(any("is a copied fixture builder recorded as new" in b for b in bad), bad)

    def test_a_claimed_cache_and_a_link_are_refused(self):
        bad = self.later_lane([{"path": "graders/x.pyc", "status": "new", "reason": "cached"}], {"graders/x.pyc": b"\x00pyc"})
        self.assertTrue(any("graders/x.pyc" in b and "is an interpreter cache" in b for b in bad), bad)
        saved = cm.is_link
        try:
            cm.is_link = lambda name: name == "takes.py"
            bad = cm.problems(pinned=False)
        finally:
            cm.is_link = saved
        self.assertTrue(any("takes.py is a symbolic link" in b for b in bad), bad)

    def test_malformed_fragments_and_a_missing_folder_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            own_fragment_in(d)
            (d / "broken.json").write_text("{not json")
            bad = cm.problems(d, pinned=False)
            self.assertTrue(any("broken.json is not JSON" in b for b in bad), bad)
            (d / "broken.json").write_text(json.dumps(["a", "list"]))
            bad = cm.problems(d, pinned=False)
            self.assertTrue(any("broken.json is not" in b for b in bad), bad)
            (d / "broken.json").write_text(json.dumps({"lane": "broken", "files": [{"path": "x", "status": "new",
                                                                                  "owner": "y"}]}))
            bad = cm.problems(d, pinned=False)
            self.assertTrue(any("broken.json: entry" in b for b in bad), bad)
        bad = cm.problems(Path("/nonexistent-copied-d"), pinned=False)
        self.assertTrue(any("no lane has recorded its files" in b for b in bad), bad)

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
        takes = cm.source_bytes("evals/gap-study-3/prereg.py")
        cases = [
            ({"path": "prereg.py", "status": "identical", "source": "evals/gap-study-3/prereg.py", "reason": "x"},
             "is identical and carries a reason"),
            ({"path": "prereg.py", "status": "identical"}, "names no source"),
            ({"path": "fresh.txt", "status": "new", "source": study_src, "reason": "x"}, "is new and names a source"),
            ({"path": "fresh.txt", "status": "new"}, "is new and carries no reason"),
            ({"path": "study.py", "status": "edited", "source": study_src}, "no reason is recorded"),
            ({"path": "study.py", "status": "edited", "source": study_src, "reason": "  "},
             "its reason is not a non-empty string"),
            ({"path": "prereg.py", "status": "identical", "source": "evals/gap-study-3/no-such-file.py"},
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
        if tuple(s.ARMS) != ("A", "C", "O", "G"):
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
                "r.BATTERY = 'echo test_round4: 1 run, 0 skipped, 0 expected failures'; r.CHECKS = Path(sys.argv[2]); sys.exit(r.main())")
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
                "r.BATTERY = 'echo test_round4: 1 run, 0 skipped, 0 expected failures'; r.CHECKS = Path(sys.argv[2]); sys.exit(r.main())")
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

    def test_an_interrupt_still_prints_a_true_count_last(self):
        # review round 2 W1A2-7
        # lane fold10/rehearsal-road: SIGINT put back first, since a process started under nohup or as a background job
        # inherits it ignored (the rehearsal's held command), and then no interrupt reaches the runner to be counted
        code = ("import signal, sys; signal.signal(signal.SIGINT, signal.default_int_handler); "
                "sys.path.insert(0, sys.argv[1]); import run_checks as r; from pathlib import Path; "
                "r.BATTERY = 'echo test_round4: 1 run, 0 skipped, 0 expected failures'; r.CHECKS = Path(sys.argv[2]); sys.exit(r.main())")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.txt").write_text("true\nkill -INT $PPID; sleep 5\ntrue\n")
            p = subprocess.run([sys.executable, "-c", code, str(STUDY_DIR), d], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0, p.stdout)
        self.assertEqual(p.stdout.splitlines()[-1], "run_checks: 2 of 3 commands passed", p.stdout)

    def test_a_battery_without_its_closing_line_fails(self):
        # review round 3 W1A3-3: a battery that exits 0 without `test_round4: N run, M skipped` (os._exit in a
        # test) counts as a failed command
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import run_checks as r; from pathlib import Path; "
                "r.BATTERY = sys.argv[3]; r.CHECKS = Path(sys.argv[2]); sys.exit(r.main())")
        with tempfile.TemporaryDirectory() as d:
            for battery, want in (("true", "run_checks: 0 of 1 commands passed"),
                                  ("echo 'test_round4: 3 run, 0 skipped, 0 expected failures'; echo 'later'",
                                   "run_checks: 0 of 1 commands passed"),
                                  ("echo 'test_round4: 3 run, 0 skipped, 0 expected failures'",
                                   "run_checks: 1 of 1 commands passed")):
                p = subprocess.run([sys.executable, "-c", code, str(STUDY_DIR), d, battery], capture_output=True,
                                   text=True)
                self.assertEqual(p.stdout.splitlines()[-1], want, p.stdout)

    def test_a_pipeline_fails_when_any_stage_fails(self):
        # review round 3 W1A3-4: commands run under bash -o pipefail
        with redirect_stdout(io.StringIO()):
            k, n = run_checks.run_all([("pipe", "false | cat")])
        self.assertEqual((k, n), (0, 1))

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
            (d / "test_live_pm.py").write_text("import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        pass\n")
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

    def test_a_skip_fails_the_battery_unless_its_reason_is_named(self):
        # review round 2 W1A2-2: four skip forms, each beside a live module
        live = "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        pass\n"
        forms = {
            "class_skip": "import unittest\n@unittest.skip('later')\nclass S(unittest.TestCase):\n    def test_y(self):\n        pass\n",
            "skip_unless": "import unittest, shutil\nclass S(unittest.TestCase):\n    @unittest.skipUnless(shutil.which('no-such-tool-xyz'), 'no tool')\n    def test_y(self):\n        pass\n",
            "module_skip": "import unittest\nraise unittest.SkipTest('whole module')\n",
            "setupclass_skip": "import unittest\nclass S(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n        raise unittest.SkipTest('no box')\n    def test_y(self):\n        pass\n",
        }
        for name, body in forms.items():
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                (d / f"test_live_{name}.py").write_text(live)
                (d / f"test_{name}.py").write_text(body)
                with redirect_stdout(io.StringIO()) as out, __import__("contextlib").redirect_stderr(io.StringIO()):
                    code = test_round4.main(d)
                self.assertEqual(code, 1, (name, out.getvalue()[-400:]))
                self.assertIn("skipped", out.getvalue())
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "test_live_alone.py").write_text(live)
            with redirect_stdout(io.StringIO()) as out, __import__("contextlib").redirect_stderr(io.StringIO()):
                self.assertEqual(test_round4.main(d), 0)
            self.assertIn("test_round4: 1 run, 0 skipped", out.getvalue())

    def test_an_expected_failure_fails_the_battery_and_is_counted(self):
        # review round 3 W1A3-2: @expectedFailure turns a red guard green; it is banned and counted
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "test_live_ef3.py").write_text("import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        pass\n")
            (d / "test_guard_ef3.py").write_text("import unittest\nclass G(unittest.TestCase):\n"
                                                 "    @unittest.expectedFailure\n    def test_red(self):\n"
                                                 "        self.assertEqual(1, 2)\n")
            with redirect_stdout(io.StringIO()) as out, __import__("contextlib").redirect_stderr(io.StringIO()):
                self.assertEqual(test_round4.main(d), 1)
        self.assertIn("1 expected failures", out.getvalue())

    def test_a_python_file_the_battery_would_never_discover_fails_it(self):
        # review round 2 W1A2-5
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "test_live_nd.py").write_text("import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        pass\n")
            (d / "test-routing.py").write_text("raise SystemExit(1)\n")
            (d / "routing_test.py").write_text("raise SystemExit(1)\n")
            got = test_round4.module_problems(d)
        self.assertTrue(any(g.startswith("test-routing.py") for g in got), got)
        self.assertTrue(any(g.startswith("routing_test.py") for g in got), got)

    def test_an_empty_battery_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(test_round4.main(Path(d)), 1)
        self.assertIn("a battery that runs nothing is not a pass", out.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
