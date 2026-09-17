#!/usr/bin/env python3
"""CP8: the freeze cannot be written until it has been rehearsed on these draft bytes, and it writes only its own keys.

    python3 evals/gap-study-2/test_harness.py TheFreezeNeedsARehearsal

Binds freeze.py's rehearsal gate (rehearsal_problems), its version refusal (claude_version), and the commit-body diff
(changed_keys, keys_outside_the_freeze): a freeze that changed a task's script on the way out would be refused. The
rehearsal script itself is exercised by running it, not here: its record is committed as verification/freeze-rehearsal-<n>.txt
and its first line is checked against the draft.

No model, no network, no live folder read. stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import freeze  # noqa: E402

DRAFT = HERE / "prereg-draft.json"


class TheFreezeNeedsARehearsal(unittest.TestCase):

    def test_no_rehearsal_record_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            got = freeze.rehearsal_problems("a" * 64, Path(td))
        self.assertEqual(len(got), 1)
        self.assertIn("has not been rehearsed", got[0])

    def test_a_record_for_other_bytes_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "freeze-rehearsal-1.txt").write_text("b" * 64 + "\nsteps\nall green\n")
            got = freeze.rehearsal_problems("a" * 64, Path(td))
        self.assertEqual(len(got), 1, "a rehearsal of other draft bytes was admitted")
        self.assertIn("the draft changed since the last rehearsal", got[0])

    def test_a_record_that_did_not_end_green_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "freeze-rehearsal-1.txt").write_text("a" * 64 + "\nsteps\nNOT all green: test_harness.py\n")
            got = freeze.rehearsal_problems("a" * 64, Path(td))
        self.assertEqual(len(got), 1)
        self.assertIn("did not end", got[0])

    def test_a_green_record_for_these_bytes_admits(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "freeze-rehearsal-2.txt").write_text("a" * 64 + "\nsteps\nall green\n")
            self.assertEqual(freeze.rehearsal_problems("a" * 64, Path(td)), [])
            (Path(td) / "freeze-rehearsal-3.txt").write_text(
                "a" * 64 + "\nprose\n" + freeze.REHEARSAL_TREE_PREFIX + "t" * 64 + "\nsteps\nall green\n")
            self.assertEqual(freeze.rehearsal_problems("a" * 64, Path(td), "t" * 64), [])
            # the admitted record is the latest by number, not by name (review 3, round 2)
            (Path(td) / "freeze-rehearsal-10.txt").write_text(
                "a" * 64 + "\nprose\n" + freeze.REHEARSAL_TREE_PREFIX + "t" * 64 + "\nsteps\nall green\n")
            self.assertEqual(freeze.admitted_rehearsal("a" * 64, Path(td), "t" * 64).name, "freeze-rehearsal-10.txt")

    def test_a_record_for_another_study_tree_refuses(self):
        """Review 1, blocker 2: a code edit after the rehearsal is a state never exercised."""
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "freeze-rehearsal-1.txt").write_text(
                "a" * 64 + "\nprose\n" + freeze.REHEARSAL_TREE_PREFIX + "t" * 64 + "\nsteps\nall green\n")
            got = freeze.rehearsal_problems("a" * 64, Path(td), "u" * 64)
            self.assertEqual(len(got), 1, "a rehearsal of another study tree was admitted")
            self.assertIn("another study tree", got[0])
            (Path(td) / "freeze-rehearsal-2.txt").write_text("a" * 64 + "\nno tree line\nall green\n")
            got = freeze.rehearsal_problems("a" * 64, Path(td), "u" * 64)
            self.assertEqual(len(got), 1)
            self.assertIn("no study tree line", got[0])

    def test_the_study_tree_sha_ignores_the_records_it_excludes(self):
        """The rehearsal record and the review's files land between the rehearsal and the freeze, so they are not
        part of the tree the freeze is bound to; a code file is."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            sd = root / "evals" / "gap-study-2"
            (sd / "verification").mkdir(parents=True)
            (sd / "code.py").write_text("x = 1\n")
            import scratch_git
            scratch_git.init(root)
            g = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
            subprocess.run(g + ["add", "-A"], check=True, capture_output=True)
            subprocess.run(g + ["commit", "-qm", "base"], check=True, capture_output=True)
            saved = freeze.REPO
            freeze.REPO = root
            try:
                before = freeze.study_tree_sha("HEAD")
                (sd / "verification" / "freeze-rehearsal-1.txt").write_text("r\n")
                (sd / "verification" / "prefreeze-1.md").write_text("r\n")
                (sd / "verification" / "prefreeze-1-blindness.txt").write_text("r\n")
                subprocess.run(g + ["add", "-A"], check=True, capture_output=True)
                subprocess.run(g + ["commit", "-qm", "records"], check=True, capture_output=True)
                self.assertEqual(freeze.study_tree_sha("HEAD"), before, "a record changed the bound tree")
                (sd / "code.py").write_text("x = 2\n")
                subprocess.run(g + ["add", "-A"], check=True, capture_output=True)
                subprocess.run(g + ["commit", "-qm", "code"], check=True, capture_output=True)
                after_code = freeze.study_tree_sha("HEAD")
                self.assertNotEqual(after_code, before, "a code edit left the bound tree unchanged")
                # a pinned file outside the study is bound too (review 3, round 2)
                (root / "CLAUDE.md").write_text("# the instruction file\n")
                subprocess.run(g + ["add", "-A"], check=True, capture_output=True)
                subprocess.run(g + ["commit", "-qm", "outside"], check=True, capture_output=True)
                self.assertNotEqual(freeze.study_tree_sha("HEAD"), after_code, "a pinned file outside the study is not bound")
            finally:
                freeze.REPO = saved

    def test_freeze_write_refuses_without_a_rehearsal_in_a_copy(self):
        """freeze.py --write, run in a copy of this study whose verification/ holds no rehearsal, must refuse by name.
        The copy carries a synthetic review commit so the refusal reached is the rehearsal's, not the review's."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            (root / "evals" / "gap-study-2").mkdir(parents=True)
            for name in ("freeze.py", "prereg.py", "study.py", "prereg-draft.json"):
                (root / "evals" / "gap-study-2" / name).write_bytes((HERE / name).read_bytes())
            ver = root / "evals" / "gap-study-2" / "verification"
            ver.mkdir()
            sha = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
            (ver / "prefreeze-1.md").write_text(f"prereg.json sha256: {sha}\n\n**Ruling: DO FREEZE.**\n")
            import scratch_git
            scratch_git.init(root)
            g = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
            subprocess.run(g + ["add", "-A"], check=True, capture_output=True)
            subprocess.run(g + ["commit", "-qm", "review"], check=True, capture_output=True)
            head = subprocess.run(g + ["rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            env = {k: v for k, v in os.environ.items() if not k.startswith("GAP_STUDY_2_POISON")}
            r = subprocess.run([sys.executable, str(root / "evals" / "gap-study-2" / "freeze.py"), "--review-commit",
                                head, "--write"], capture_output=True, text=True, cwd=str(root), env=env)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse((root / "evals" / "gap-study-2" / "prereg.json").exists(), "the freeze wrote without a rehearsal")
            out = r.stdout + r.stderr
            self.assertIn("has not been rehearsed", out,
                          "the freeze reached past the rehearsal gate: " + " | ".join(out.strip().splitlines()[-2:])[:300])

    def test_freeze_write_refuses_uncommitted_changes_under_the_study(self):
        """Review 2 (round 2), blocker 1: the pins read the disk and the gate reads HEAD, so an uncommitted edit to a
        pinned file was frozen unrehearsed. The refusal comes before the rehearsal gate, so this copy needs no record."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            (root / "evals" / "gap-study-2").mkdir(parents=True)
            for name in ("freeze.py", "prereg.py", "study.py", "prereg-draft.json"):
                (root / "evals" / "gap-study-2" / name).write_bytes((HERE / name).read_bytes())
            ver = root / "evals" / "gap-study-2" / "verification"
            ver.mkdir()
            sha = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
            (ver / "prefreeze-1.md").write_text(f"prereg.json sha256: {sha}\n\n**Ruling: DO FREEZE.**\n")
            import scratch_git
            scratch_git.init(root)
            g = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
            subprocess.run(g + ["add", "-A"], check=True, capture_output=True)
            subprocess.run(g + ["commit", "-qm", "review"], check=True, capture_output=True)
            head = subprocess.run(g + ["rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            with (root / "evals" / "gap-study-2" / "prereg.py").open("a") as f:
                f.write("# an edit nobody rehearsed\n")
            env = {k: v for k, v in os.environ.items() if not k.startswith("GAP_STUDY_2_POISON")}
            r = subprocess.run([sys.executable, str(root / "evals" / "gap-study-2" / "freeze.py"), "--review-commit",
                                head, "--write"], capture_output=True, text=True, cwd=str(root), env=env)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse((root / "evals" / "gap-study-2" / "prereg.json").exists(), "the freeze wrote with uncommitted changes under the study")
            self.assertIn("uncommitted changes", r.stdout + r.stderr, "the freeze did not name the uncommitted change")
            # an uncommitted edit outside the study, to a file the freeze pins (review 3, round 2)
            subprocess.run(g + ["checkout", "--", "evals/gap-study-2/prereg.py"], check=True, capture_output=True)
            (root / "CLAUDE.md").write_text("# an edit nobody rehearsed\n")
            r = subprocess.run([sys.executable, str(root / "evals" / "gap-study-2" / "freeze.py"), "--review-commit",
                                head, "--write"], capture_output=True, text=True, cwd=str(root), env=env)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("uncommitted changes", r.stdout + r.stderr, "the freeze did not name the uncommitted change outside the study")

    def test_the_freeze_commit_is_held_to_the_rehearsal_and_each_pin_to_its_blob(self):
        """check_results.frozen_commit_problems on a repository the test builds: clean when the freeze commit's study
        tree is the rehearsed one and every pin is the committed blob; red for a moved tree, a foreign blob, or a pin
        whose sha256 is not the committed bytes (the uncommitted-edit route)."""
        import check_results as cr
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            sd = root / "evals" / "gap-study-2"
            (sd / "verification" / "round1-regrade").mkdir(parents=True)
            (sd / "a.py").write_text("x = 1\n")
            import scratch_git
            scratch_git.init(root)
            g = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
            subprocess.run(g + ["add", "-A"], check=True, capture_output=True)
            subprocess.run(g + ["commit", "-qm", "rehearsed"], check=True, capture_output=True)
            saved = (freeze.REPO, cr.REPO)
            freeze.REPO = cr.REPO = root
            try:
                tree = freeze.study_tree_sha("HEAD")
                pin_rel = "evals/gap-study-2/a.py"  # a file only this scratch repository has
                blob = subprocess.run(g + ["rev-parse", f"HEAD:{pin_rel}"], capture_output=True, text=True).stdout.strip()
                rehearsed = subprocess.run(g + ["log", "-1", "--format=%H"], capture_output=True, text=True).stdout.strip()
                # amendment 1: the hold runs only where the freeze commit sits on the recorded parent
                frozen = {"rehearsed_study_tree_sha256": tree, "frozen_at_commit_parent": rehearsed,
                          "pinned_files": [{"path": pin_rel, "git_blob_sha": blob,
                                            "sha256": hashlib.sha256(b"x = 1\n").hexdigest()}]}
                (sd / "prereg.json").write_text(json.dumps(frozen))
                (sd / "verification" / "round1-regrade" / "environment.json").write_text("{}\n")
                subprocess.run(g + ["add", "-A"], check=True, capture_output=True)
                subprocess.run(g + ["commit", "-qm", "freeze"], check=True, capture_output=True)
                commit = cr.freeze_commit()
                self.assertTrue(commit)
                self.assertEqual(cr.frozen_commit_problems(frozen, commit), [])
                moved = {**frozen, "rehearsed_study_tree_sha256": "0" * 64}
                self.assertTrue(any("not the rehearsed one" in p for p in cr.frozen_commit_problems(moved, commit)),
                                "a freeze commit whose tree is not the rehearsed one passed")
                foreign = {**frozen, "pinned_files": [{**frozen["pinned_files"][0], "git_blob_sha": "1" * 40}]}
                self.assertTrue(any("not what was committed" in p for p in cr.frozen_commit_problems(foreign, commit)))
                edited = {**frozen, "pinned_files": [{**frozen["pinned_files"][0], "sha256": hashlib.sha256(b"x = 2\n").hexdigest()}]}
                self.assertTrue(any("uncommitted at the freeze" in p for p in cr.frozen_commit_problems(edited, commit)),
                                "a pin whose bytes were not the committed blob's passed")
                # a copy whose freeze commit does not sit on the recorded parent is not checked, and says so
                import contextlib, io
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    unheld = cr.frozen_commit_problems({**moved, "frozen_at_commit_parent": "0" * 40}, commit)
                self.assertEqual(unheld, [])
                self.assertIn("NOT CHECKED", buf.getvalue())
            finally:
                freeze.REPO, cr.REPO = saved

    def test_the_rehearsal_flag_is_refused_where_a_remote_exists(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            (root / "evals" / "gap-study-2").mkdir(parents=True)
            for name in ("freeze.py", "prereg.py", "study.py", "prereg-draft.json"):
                (root / "evals" / "gap-study-2" / name).write_bytes((HERE / name).read_bytes())
            import scratch_git
            scratch_git.init(root)
            subprocess.run(["git", "-C", str(root), "remote", "add", "origin", "https://example.invalid/x.git"],
                           check=True, capture_output=True)
            r = subprocess.run([sys.executable, str(root / "evals" / "gap-study-2" / "freeze.py"), "--review-commit",
                                "HEAD", "--rehearsal", "--write"], capture_output=True, text=True, cwd=str(root))
            self.assertEqual(r.returncode, 2)
            self.assertIn("has one", r.stdout + r.stderr)

    def test_the_commit_body_diff_names_only_freeze_written_keys(self):
        draft = json.loads(DRAFT.read_text())
        frozen = json.loads(DRAFT.read_text())
        frozen["status"] = "FROZEN"
        frozen["pinned_files"] = [{"path": "x"}]
        frozen["tasks"][0]["grader"] = {**frozen["tasks"][0]["grader"], "sha256": "y"}
        self.assertEqual(freeze.keys_outside_the_freeze(draft, frozen), [])
        self.assertIn("status", freeze.commit_body_diff(draft, frozen))
        frozen["tasks"][0]["positive"]["operator_script"][0]["line"] = "edited on the way out"
        self.assertEqual(freeze.keys_outside_the_freeze(draft, frozen), ["tasks[].positive.operator_script"],
                         "a freeze that edits a script line must be named as outside its keys")
        self.assertEqual(freeze.commit_body_diff(draft, draft), "none")

    def test_the_rehearsal_record_if_present_names_the_current_draft(self):
        """The record for the current draft's bytes, when one exists, is whole: green, a study tree, a not-done line.

        Every record is kept, so an earlier draft's record stays on disk beside the current one; whether the current
        draft HAS a green record is the freeze gate's question (rehearsal_problems), not this test's. Before CP8's
        review this test read the latest record and failed on a stale one, which made the suite red in every rehearsal
        clone after a draft change: the record that would clear it is written only after that suite passes.
        """
        sha = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
        records = [p for p in sorted((HERE / "verification").glob("freeze-rehearsal-*.txt"))
                   if p.read_text().splitlines()[:1] == [sha]]
        if not records:
            self.skipTest("no rehearsal record for the current draft yet; freeze.py refuses --write until one exists")
        latest = records[-1].read_text().splitlines()
        self.assertEqual(latest[-1].strip(), freeze.REHEARSAL_LAST_LINE, f"{records[-1].name} did not end all green")
        self.assertTrue(freeze.recorded_tree(records[-1]), f"{records[-1].name} names no study tree")
        self.assertTrue(any("not done" in line for line in latest), "the record must say what it did not run")


if __name__ == "__main__":
    unittest.main()
