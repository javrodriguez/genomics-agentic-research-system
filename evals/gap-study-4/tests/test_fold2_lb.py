#!/usr/bin/env python3
"""Lane fold2/lb (glitch-45's fold of pre-freeze review 2, FOLD-PLAN-prefreeze-2.md section 1 and section 3, L-B): the
freeze and witness gates, red first.

    python3 -B -W ignore evals/gap-study-4/tests/test_fold2_lb.py

MAJOR 3   the seed review's ruling is read from exactly one anchored ruling line (commit_review.read_ruling, shared
          with freeze.review_file_problems and so with run_builders.py rehearse); zero or several read "ambiguous",
          which commit_review commits unedited and records, and which the freeze refuses.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import freeze  # noqa: E402
import study  # noqa: E402


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                          "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"git {args}: {out.stderr}")
    return out.stdout.strip()


def load_commit_review():
    spec = importlib.util.spec_from_file_location("fold2_commit_review", HERE / "review_kit" / "commit_review.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DO = "**Ruling: DO FREEZE.**"
DO_NOT = "**Ruling: DO NOT FREEZE.**"


def report(digest: str, *body: str) -> str:
    return "\n".join((f"prereg.json sha256: {digest}", "", "# synthetic review", "", *body)) + "\n"


# The reviewer's shape (review 2, MAJOR 3): a correct line 1, the bold DO NOT FREEZE line, and the DO FREEZE literal
# quoted inside a sentence, as the review brief's "name both rulings" invites.
QUOTED = (DO_NOT, "", f"The brief names both rulings; the other would have read {DO} on its own line.")
TWO_LINES = (DO, "", "Second thoughts:", "", DO_NOT)


@contextlib.contextmanager
def review_repo(*bodies):
    """A scratch repository whose study folder holds a draft and one committed review per body (prefreeze-1.md, ...);
    yields (repo, draft path, [commit per review])."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, "init", "-q")
        study_dir = repo / study.STUDY_REL
        (study_dir / study.REVIEW_DIR).mkdir(parents=True)
        draft = study_dir / "prereg-draft.json"
        draft.write_bytes(b'{"synthetic": "draft"}\n')
        digest = hashlib.sha256(draft.read_bytes()).hexdigest()
        shas = []
        for n, body in enumerate(bodies, 1):
            (study_dir / study.REVIEW_DIR / f"prefreeze-{n}.md").write_text(report(digest, *body))
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", f"review {n}")
            shas.append(git(repo, "rev-parse", "HEAD"))
        yield repo, draft, shas


def seed_problems(body):
    with review_repo(body) as (repo, draft, shas), \
            mock.patch.object(freeze, "REPO", repo), mock.patch.object(freeze, "DRAFT", draft):
        bad, _ = freeze.review_file_problems(shas[0])
    return bad


class TestMajor3Ruling(unittest.TestCase):
    def test_quoted_literal_beside_a_do_not_freeze_line_is_refused(self):
        self.assertTrue(seed_problems(QUOTED), "MAJOR 3: a DO NOT FREEZE report quoting the literal seeds a freeze")

    def test_two_anchored_ruling_lines_are_refused(self):
        self.assertTrue(seed_problems(TWO_LINES), "MAJOR 3: a report with two ruling lines seeds a freeze")

    def test_plain_do_freeze_still_passes(self):
        self.assertEqual(seed_problems((DO,)), [])

    def test_do_not_freeze_and_no_line_are_refused(self):
        self.assertTrue(seed_problems((DO_NOT,)))
        self.assertTrue(seed_problems(("No ruling here.",)))

    def test_read_ruling_reads_exactly_one_anchored_line(self):
        cr = load_commit_review()
        cases = {(DO,): "DO FREEZE", (DO_NOT,): "DO NOT FREEZE", QUOTED: "DO NOT FREEZE",
                 TWO_LINES: cr.AMBIGUOUS, (DO, DO): cr.AMBIGUOUS, ("none",): cr.AMBIGUOUS,
                 (f"> {DO}",): cr.AMBIGUOUS, (DO + " ",): cr.AMBIGUOUS}
        for body, want in cases.items():
            with self.subTest(body=body):
                self.assertEqual(cr.read_ruling(report("0" * 64, *body)), want)

    def test_freeze_reads_the_ruling_through_commit_review(self):
        # one reader: freeze's gate is commit_review.read_ruling, so the two can never disagree again
        cr = load_commit_review()
        with review_repo((DO,)) as (repo, draft, shas), \
                mock.patch.object(freeze, "REPO", repo), mock.patch.object(freeze, "DRAFT", draft), \
                mock.patch.object(freeze, "read_ruling", lambda text: cr.AMBIGUOUS):
            bad, _ = freeze.review_file_problems(shas[0])
        self.assertTrue(bad and "ambiguous" in bad[0], bad)

    def test_rehearse_latest_review_uses_the_same_gate(self):
        # run_builders.py rehearse's no-pre-freeze-review path calls freeze.review_file_problems
        import run_builders
        with review_repo(QUOTED) as (repo, draft, shas), \
                mock.patch.object(freeze, "REPO", repo), mock.patch.object(freeze, "DRAFT", draft):
            self.assertIsNone(run_builders.latest_review(repo))
        with review_repo((DO,)) as (repo, draft, shas), \
                mock.patch.object(freeze, "REPO", repo), mock.patch.object(freeze, "DRAFT", draft):
            self.assertEqual(run_builders.latest_review(repo), shas[0])

    def test_commit_review_commits_an_ambiguous_report_unedited(self):
        """commit_review never refuses a report for its ruling (a refused report is a voided round and a second draw
        of the review): two ruling lines, or none, are committed unedited and recorded as ambiguous."""
        for body in (TWO_LINES, ("No ruling line at all.",), QUOTED):
            with self.subTest(body=body[0]):
                msg, committed, text = self.run_commit_review(body)
                self.assertIsNotNone(committed, msg)
                self.assertEqual(committed, text, "the report is committed unedited")
                want = "DO NOT FREEZE" if body is QUOTED else "ambiguous"
                self.assertIn(f"ruled: {want}", msg)

    def run_commit_review(self, body):
        cr = load_commit_review()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            study_dir = repo / study.STUDY_REL
            (study_dir / study.REVIEW_DIR).mkdir(parents=True)
            git(repo, "init", "-q")
            git(repo, "config", "user.name", "t")
            git(repo, "config", "user.email", "t@example.invalid")
            # a link: commit_msg.py resolves its own folder, so it lints with the real lint_language and study
            (study_dir / "commit_msg.py").symlink_to(HERE / "commit_msg.py")
            (study_dir / "prereg-draft.json").write_bytes(b'{"synthetic": "draft"}\n')
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "base")
            folder = Path(tmp) / "round"
            launch = Path(tmp) / "round-launch"
            folder.mkdir()
            launch.mkdir()
            kit = b'{"synthetic": "kit"}\n'
            (folder / "prereg.json").write_bytes(kit)
            text = report(hashlib.sha256(kit).hexdigest(), *body)
            (folder / "prefreeze-3.md").write_text(text)
            (launch / "blindness.txt").write_text("synthetic blindness\n")
            out = io.StringIO()
            with mock.patch.object(cr, "STUDY_DIR", study_dir), mock.patch.object(cr, "REPO", repo), \
                    mock.patch.object(sys, "argv", ["commit_review.py", str(folder), "3"]), \
                    contextlib.redirect_stdout(out):
                code = cr.main()
            dest = study_dir / study.REVIEW_DIR / "prefreeze-3.md"
            if code != 0 or not dest.is_file():
                return out.getvalue(), None, text
            msg = git(repo, "log", "-1", "--format=%B")
            return msg, dest.read_text(), text


if __name__ == "__main__":
    unittest.main(verbosity=2)
