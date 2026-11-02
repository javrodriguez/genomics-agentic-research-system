#!/usr/bin/env python3
"""Lane fold9/round7-residual (Gap Study round 4; pre-freeze review 7; glitch-45's rulings of Mon 2 Nov 2026, under
Javier's standing delegation).

  ADD        (review 7, m-new-2) rounds.py --add refuses unless <folder>/COMMIT is HEAD, so a row's launch_commit is the
             commit its reviewer was handed: another commit, no COMMIT file and an empty one each write no row.
  GRAND      round 7 is grandfathered, so it never seeds, though it stays a registered round.
  UNBOUND    commit_review lands round 7's report, whose record reads NOT RECORDED because its reviewer ran one sed on
             it, only with exactly the named bytes, that exact record line, a grandfathered round and the as-written
             record committed. Any other round, other bytes, another NOT RECORDED reason, or a missing or altered
             as-written record is refused, and its message states the edit and never claims the digest.
  RECORD     the committed as-written bytes, with the one edit made, are the named report bytes.

tests/test_pipeline.py binds review 7's M1: the frozen file's published_tip_residual and the RESULT.md section.
Synthetic folders and scratch git repositories in temporary directories only. No model, network or container.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import freeze  # noqa: E402
import study  # noqa: E402
import takes  # noqa: E402
import test_fold5_report_binding as f5  # noqa: E402
import test_fold8_review_binding as f8  # noqa: E402

cr = f5.cr
git = f5.git
RK = study.REVIEW_DIR
AS_WRITTEN = "prefreeze-7.as-written.md"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Add(unittest.TestCase):
    def run_add(self, r, commit):
        mod = f8.load_rounds(r.repo)
        mod.BRIEF.write_text("synthetic brief\n")
        r.commit("brief")
        head = git(r.repo, "rev-parse", "HEAD")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "round"
            folder.mkdir()
            (folder / "prereg.json").write_text("{}\n")
            if commit is not None:
                (folder / "COMMIT").write_text(commit(head))
            with contextlib.redirect_stdout(io.StringIO()) as said:
                code = mod.add("prefreeze", folder, None)
        return code, said.getvalue(), head

    def test_the_kits_commit_writes_the_row(self):
        with f8.rig() as r:
            code, said, head = self.run_add(r, lambda h: h + "\n")
            self.assertEqual(code, 0, said)
            self.assertEqual(r.rows()[-1]["launch_commit"], head, "ADD: launch_commit is the kit's COMMIT")

    def test_any_other_commit_writes_no_row(self):
        for name, commit in (("another", lambda h: "0" * 40 + "\n"), ("absent", None), ("empty", lambda h: "\n"),
                             ("two lines", lambda h: h + "\n" + h + "\n"), ("short", lambda h: h[:12] + "\n")):
            with self.subTest(name), f8.rig() as r:
                code, said, _ = self.run_add(r, commit)
                self.assertEqual(code, 1, f"ADD: {name}: {said}")
                self.assertIn("COMMIT", said, "ADD")
                self.assertEqual(r.rows(), [], f"ADD: {name} wrote a row")


class Grandfathered(unittest.TestCase):
    def test_round_7_never_seeds_and_stays_registered(self):
        self.assertEqual(freeze.REPORT_DIGEST_GRANDFATHERED, (1, 2, 3, 4, 7))
        with f8.rig() as r:
            r.register(7)
            seed = r.review(7)
            bad, name = r.problems(seed)
            self.assertTrue(bad and name is None and "grandfathered" in bad[0], f"GRAND: {bad}")
            with r.patched():
                self.assertIsNone(freeze.registered_review_problem(f8.report_rel(7), 7), "GRAND")


def rig_commit(tmp: Path, n: int = 7, *, reason_command="sed -i '' 's/synthetic review/a review/' prefreeze-7.md",
               edit=None, as_written="right", unbound=None):
    """commit_review on a registered round n whose reviewer wrote the report, then ran one shell step on it. Returns
    (exit code, stdout, the commit message or "", the repository's file names at HEAD)."""
    repo = tmp / "repo"
    study_dir = repo / study.STUDY_REL
    (study_dir / RK).mkdir(parents=True)
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "user.email", "t@example.invalid")
    (study_dir / "commit_msg.py").symlink_to(HERE / "commit_msg.py")
    (study_dir / "prereg-draft.json").write_bytes(b'{"synthetic": "draft"}\n')
    kit = b'{"synthetic": "kit"}\n'
    written = f5.report_text(sha(kit))
    edited = written.replace("synthetic review", "a review") if edit is None else edit(written)
    if as_written == "right":
        (study_dir / RK / AS_WRITTEN).write_text(written)
    elif as_written == "other":
        (study_dir / RK / AS_WRITTEN).write_text(written + "other\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    (study_dir / RK / "rounds.json").write_text(json.dumps(
        {"rows": [{"n": k, "kind": "prefreeze", "voids": None} for k in range(1, n + 1)]}) + "\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "register")
    sid = takes.session_id_for(git(repo, "rev-parse", "HEAD"))
    folder, launch, projects, sid = f5.session_rig(tmp, written, n=n, sid=sid)
    session = projects / "-round" / f"{sid}.jsonl"
    session.write_text(session.read_text() + f5.use("b1", "Bash", {"command": reason_command}, cwd=str(folder)) + "\n"
                       + f5.result("b1") + "\n")
    (folder / f"prefreeze-{n}.md").write_text(edited)
    (folder / "prereg.json").write_bytes(kit)
    (launch / "blindness.txt").write_text(cr.blindness.report(folder, sid, projects))
    table = {str(n): {"report_sha256": sha(edited.encode()), "as_written": AS_WRITTEN,
                      "as_written_sha256": sha(written.encode()), "reason": "a shell step writes the report",
                      "edit": "one sed changed 'synthetic review' to 'a review'"}} if unbound is None else unbound
    out = io.StringIO()
    with mock.patch.object(cr, "STUDY_DIR", study_dir), mock.patch.object(cr, "REPO", repo), \
            mock.patch.object(cr.blindness, "PROJECTS", projects), mock.patch.object(cr, "UNBOUND_REPORTS", table), \
            mock.patch.object(sys, "argv", ["commit_review.py", str(folder), str(n)]), \
            contextlib.redirect_stdout(out):
        code = cr.main()
    msg = git(repo, "log", "-1", "--format=%B") if code == 0 else ""
    names = git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    return code, out.getvalue(), msg, names


class Unbound(unittest.TestCase):
    def run_rig(self, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            return rig_commit(Path(tmp).resolve(), **kw)

    def test_the_named_report_lands_and_says_what_it_is(self):
        code, out, msg, names = self.run_rig()
        self.assertEqual(code, 0, out)
        self.assertIn(study.rel(RK, "prefreeze-7.md"), names)
        self.assertIn("one sed changed", msg, "UNBOUND: the message states the edit")
        self.assertIn(AS_WRITTEN, msg, "UNBOUND: the message names the record")
        self.assertNotIn("the bytes its blindness record rebuilds", msg, "UNBOUND: no digest is claimed")

    def test_other_bytes_are_refused(self):
        code, out, _, names = self.run_rig(edit=lambda w: w.replace("synthetic review", "a review") + "more\n",
                                           unbound={"7": {"report_sha256": "0" * 64, "as_written": AS_WRITTEN,
                                                          "as_written_sha256": "0" * 64, "edit": "e",
                                                          "reason": "a shell step writes the report"}})
        self.assertEqual(code, 1, out)
        self.assertNotIn(study.rel(RK, "prefreeze-7.md"), names)

    def test_a_missing_or_altered_as_written_record_is_refused(self):
        for state in ("absent", "other"):
            with self.subTest(state):
                code, out, _, names = self.run_rig(as_written=state)
                self.assertEqual(code, 1, out)
                self.assertIn(AS_WRITTEN, out, "UNBOUND")
                self.assertNotIn(study.rel(RK, "prefreeze-7.md"), names)

    def test_another_not_recorded_reason_is_refused(self):
        code, out, _, _ = self.run_rig(reason_command="python3 -c \"open('prefreeze-7.md','w')\"")
        self.assertEqual(code, 1, out)
        self.assertIn("as the reviewer's session wrote it", out, "UNBOUND")

    def test_a_round_not_named_or_not_grandfathered_is_refused(self):
        # round 9 has no entry; round 9 named in the table is still no grandfathered round
        code, out, _, _ = self.run_rig(n=9, reason_command="sed -i '' 's/a/b/' prefreeze-9.md", unbound={})
        self.assertEqual(code, 1, out)
        code, out, _, _ = self.run_rig(n=9, reason_command="sed -i '' 's/a/b/' prefreeze-9.md")
        self.assertEqual(code, 1, out)
        self.assertIn("grandfathered", out, "UNBOUND")


class Record(unittest.TestCase):
    def test_the_committed_record_with_the_one_edit_is_the_named_report(self):
        entry = cr.UNBOUND_REPORTS["7"]
        data = (HERE / RK / AS_WRITTEN).read_bytes()
        self.assertEqual(sha(data), entry["as_written_sha256"], "RECORD: the committed bytes")
        old, new = b"  - This sound apart from", b"  - This is sound apart from"
        self.assertEqual(data.count(old), 1, "RECORD: one line")
        self.assertEqual(sha(data.replace(old, new)), entry["report_sha256"], "RECORD: the one sed")
        self.assertEqual(entry["report_sha256"], "4538ce819faa156431b6d3a2d784991a880d74d7b287c264d1b606f4ed8833cf")


if __name__ == "__main__":
    unittest.main()
