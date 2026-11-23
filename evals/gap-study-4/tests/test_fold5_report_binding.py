#!/usr/bin/env python3
"""Lane fold5/report-binding (Gap Study round 4; pre-freeze review 5, MAJOR 1; glitch-45's rulings 1 and 2, Sat 31 Oct
2026, under Javier's standing delegation): a committed review report is bound to the bytes its reviewer's session wrote.

  B1-rebuild  blindness.written_report rebuilds the report from the reviewer's session file alone: its Write, then its
              Edits and MultiEdits in order, a failed one skipped. It records nothing, and says why, for a write the
              session file does not show whole (no result, an Edit whose old text is not in the report exactly once, a
              NotebookEdit, a content that is not a string), a shell step that writes the report, or a sub-agent's
              write. The committed rounds' real sessions are read by review_kit/check_real_sessions.py on the Mac, not
              here.
  B1-commit   commit_review.py refuses a report whose sha256 is not the digest its blindness record states, or whose
              record states none (a one-line edit of the ruling line after the reviewer wrote it is refused), and
              commits one that matches, its message stating the digest.
  B1-freeze   freeze.registered_review_problem refuses a seed review (round 5 on) whose committed bytes are not its
              committed record's digest, or whose record states none; rounds 1-4 are grandfathered by number.
  B2-paths    commit_review.ABS_PATH no longer reads a placeholder segment (/home/<user, /gpfs/home/<user>) or a bare
              root (`/Users/`) as a host path, and still refuses a real one (/Users/somebody/..., /home/javier/...,
              /private/tmp/..., /var/folders/...).

Synthetic folders and scratch git repositories in temporary directories only. No model, network or container.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
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
import takes  # noqa: E402


def load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, HERE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bl = load("fold5_blindness", "review_kit/blindness.py")
cr = load("fold5_commit_review", "review_kit/commit_review.py")


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                          "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"git {args}: {out.stderr}")
    return out.stdout.strip()


def use(tid: str, name: str, inp: dict, cwd: str = "/r", sidechain: bool = False) -> str:
    rec = {"type": "assistant", "cwd": cwd, "message": {"content": [{"type": "tool_use", "id": tid, "name": name,
                                                                     "input": inp}]}}
    if sidechain:
        rec["isSidechain"] = True
    return json.dumps(rec)


def result(tid: str, error: bool = False) -> str:
    return json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid,
                                                                "is_error": error, "content": "ok"}]}})


REPORT = Path("/r/prefreeze-6.md")
W = {"file_path": str(REPORT), "content": "line 1\n**Ruling: DO NOT FREEZE.**\nend\n"}


class B1Rebuild(unittest.TestCase):
    def rebuild(self, *lines, side=None):
        return bl.written_report(list(lines), REPORT, side)

    def test_a_write_then_edits_in_order(self):
        e1 = {"file_path": str(REPORT), "old_string": "end", "new_string": "the end"}
        e2 = {"file_path": "prefreeze-6.md", "edits": [{"old_string": "line 1", "new_string": "first"}]}
        text, why = self.rebuild(use("a", "Write", W), result("a"), use("b", "Edit", e1), result("b"),
                                 use("c", "MultiEdit", e2), result("c"))
        self.assertEqual((text, why), ("first\n**Ruling: DO NOT FREEZE.**\nthe end\n", ""), "B1-rebuild")

    def test_a_failed_edit_changes_nothing(self):
        e1 = {"file_path": str(REPORT), "old_string": "end", "new_string": "the end"}
        text, _ = self.rebuild(use("a", "Write", W), result("a"), use("b", "Edit", e1), result("b", error=True))
        self.assertEqual(text, W["content"], "B1-rebuild")

    def test_what_cannot_be_rebuilt_exactly_records_nothing(self):
        cases = {
            "no result": (use("a", "Write", W),),
            "edit text absent": (use("a", "Write", W), result("a"),
                                 use("b", "Edit", {"file_path": str(REPORT), "old_string": "zzz", "new_string": "y"}),
                                 result("b")),
            "edit text twice": (use("a", "Write", dict(W, content="x x\n")), result("a"),
                                use("b", "Edit", {"file_path": str(REPORT), "old_string": "x", "new_string": "y"}),
                                result("b")),
            "content not whole": (use("a", "Write", {"file_path": str(REPORT), "content": None}), result("a")),
            "notebook edit": (use("a", "Write", W), result("a"),
                              use("b", "NotebookEdit", {"notebook_path": str(REPORT), "new_source": "x"}), result("b")),
            "a shell redirect": (use("a", "Write", W), result("a"),
                                 use("b", "Bash", {"command": "cd /r && sed -n 1p x > prefreeze-6.md"}), result("b")),
            "a shell sed -i": (use("a", "Write", W), result("a"),
                               use("b", "Bash", {"command": "sed -i '' s/NOT// /r/prefreeze-6.md"}), result("b")),
            "a sidechain record": (use("a", "Write", W, sidechain=True), result("a")),
            # the review of f3ae7772, m1: fail closed on any step that names the report and is not a pure read
            "python3 -c open": (use("a", "Write", W), result("a"),
                                use("b", "Bash", {"command": "python3 -c \"open('prefreeze-6.md','a').write('x')\""}),
                                result("b")),
            "perl -pi": (use("a", "Write", W), result("a"),
                         use("b", "Bash", {"command": "perl -pi -e 's/NOT //' prefreeze-6.md"}), result("b")),
            "dd of=": (use("a", "Write", W), result("a"),
                       use("b", "Bash", {"command": "dd if=/tmp/x of=/r/prefreeze-6.md"}), result("b")),
            "truncate": (use("a", "Write", W), result("a"),
                         use("b", "Bash", {"command": "truncate -s 0 prefreeze-6.md"}), result("b")),
            "git checkout --": (use("a", "Write", W), result("a"),
                                use("b", "Bash", {"command": "git checkout -- prefreeze-6.md"}), result("b")),
            "bash -c >>": (use("a", "Write", W), result("a"),
                           use("b", "Bash", {"command": "bash -c 'echo x >> prefreeze-6.md'"}), result("b")),
            "awk writing with >": (use("a", "Write", W), result("a"),
                                   use("b", "Bash", {"command": "awk '{print > \"prefreeze-6.md\"}' x"}), result("b")),
            "awk -i inplace": (use("a", "Write", W), result("a"),
                               use("b", "Bash", {"command": "awk -i inplace '{sub(/NOT /,\"\")}1' prefreeze-6.md"}),
                               result("b")),
            "mv of a glob into the folder": (use("a", "Write", W), result("a"),
                                             use("b", "Bash", {"command": "mv /tmp/staged* /r/"}), result("b")),
            "no write at all": (use("b", "Bash", {"command": "grep -n Ruling /r/prefreeze-6.md"}), result("b")),
        }
        for what, lines in cases.items():
            with self.subTest(case=what):
                text, why = self.rebuild(*lines)
                self.assertIsNone(text, f"B1-rebuild: {what} rebuilt {text!r}")
                self.assertTrue(why, f"B1-rebuild: {what} names no reason")
        text, why = self.rebuild(use("a", "Write", W), result("a"), side={str(REPORT)})
        self.assertEqual((text, "sub-agent" in why), (None, True), "B1-rebuild: a sub-agent's session wrote it")

    def test_a_shell_read_is_no_write(self):
        for cmd in ("cd /r && grep -nE '/(Users|home)/' prefreeze-6.md", "sed -n 1,5p /r/prefreeze-6.md",
                    "shasum -a 256 prefreeze-6.md && wc -l prefreeze-6.md", "ls -l /r/prefreeze-6.md | head -1",
                    "cat prefreeze-6.md > /tmp/copy.md",
                    # the re-check of 0beda082, MINOR 2: harmless reads never void a round
                    "awk '{print $1}' prefreeze-6.md", "sort prefreeze-6.md | uniq -c", "less prefreeze-6.md",
                    "more prefreeze-6.md", "cut -c1-40 prefreeze-6.md", "nl prefreeze-6.md", "stat prefreeze-6.md",
                    "file prefreeze-6.md"):
            with self.subTest(cmd=cmd):
                text, why = self.rebuild(use("a", "Write", W), result("a"), use("b", "Bash", {"command": cmd}),
                                         result("b"))
                self.assertEqual((text, why), (W["content"], ""), "B1-rebuild: a pure read")

    def test_the_record_line_reads_back(self):
        d = "a" * 64
        self.assertEqual(bl.recorded_report_digest(f"x\n{bl.REPORT_DIGEST}{d}\n"), d, "B1-rebuild")
        self.assertIsNone(bl.recorded_report_digest(f"{bl.REPORT_UNBOUND}why\n"), "B1-rebuild")
        self.assertIsNone(bl.recorded_report_digest(f"{bl.REPORT_DIGEST}{d}\n{bl.REPORT_DIGEST}{d}\n"), "B1-rebuild")


# The two real-session checks (review 4's and review 5's rebuilds) left this battery for
# review_kit/check_real_sessions.py, which the orchestrator runs on the Mac before each freeze step: the sessions live
# only under the operator's ~/.claude, and the battery bans skips (test_round4.SKIP_ALLOWED; glitch-45, 1 Nov 2026).


DO = "**Ruling: DO FREEZE.**"


def report_text(kit_sha: str, ruling: str = DO) -> str:
    return f"prereg.json sha256: {kit_sha}\n\n# synthetic review\n\n{ruling}\n"


def session_rig(tmp: Path, written: str, n: int = 6, sid: str = "00000000-0000-5000-8000-0000000000ab"):
    """A review folder holding the kit and the report, its launch side folder with SESSION, and a projects folder
    holding the reviewer's session file, whose one Write is the report. Returns (folder, launch, projects, sid)."""
    folder, launch, projects = tmp / "round", tmp / "round-launch", tmp / "projects" / "-round"
    for d in (folder, launch, projects):
        d.mkdir(parents=True)
    folder = folder.resolve()
    (launch / "SESSION").write_text(sid + "\n")
    path = str(folder / f"prefreeze-{n}.md")
    lines = [use("w1", "Write", {"file_path": path, "content": written}, cwd=str(folder)), result("w1")]
    (projects / f"{sid}.jsonl").write_text("\n".join(lines) + "\n")
    (folder / f"prefreeze-{n}.md").write_text(written)
    return folder, launch, projects.parent, sid


class B1Commit(unittest.TestCase):
    def run_commit(self, *, tamper=None, session=True, sid=None):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            repo = tmp / "repo"
            study_dir = repo / study.STUDY_REL
            (study_dir / study.REVIEW_DIR).mkdir(parents=True)
            git(repo, "init", "-q")
            # commit_review commits with the repository's own identity; a suite user with none (athena's battery,
            # gap4-fold5-battery-a63a838) needs it set here, as test_fold2_lb's commit_review rig does
            git(repo, "config", "user.name", "t")
            git(repo, "config", "user.email", "t@example.invalid")
            (study_dir / "commit_msg.py").symlink_to(HERE / "commit_msg.py")
            (study_dir / "prereg-draft.json").write_bytes(b'{"synthetic": "draft"}\n')
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "base")
            # the re-check of 0beda082, MINOR 1: the round is registered, and its session is the one its row derives
            (study_dir / study.REVIEW_DIR / "rounds.json").write_text(json.dumps(
                {"rows": [{"n": k, "kind": "prefreeze", "voids": None} for k in range(1, 7)]}) + "\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "register")
            registered = takes.session_id_for(git(repo, "rev-parse", "HEAD"))
            kit = b'{"synthetic": "kit"}\n'
            written = report_text(hashlib.sha256(kit).hexdigest())
            folder, launch, projects, sid = session_rig(tmp, written, sid=sid or registered)
            (folder / "prereg.json").write_bytes(kit)
            (launch / "blindness.txt").write_text(cr.blindness.report(folder, sid, projects))
            if tamper:
                tamper(folder, launch)
            if not session:
                (launch / "SESSION").unlink()
            out = io.StringIO()
            with mock.patch.object(cr, "STUDY_DIR", study_dir), mock.patch.object(cr, "REPO", repo), \
                    mock.patch.object(cr.blindness, "PROJECTS", projects), \
                    mock.patch.object(sys, "argv", ["commit_review.py", str(folder), "6"]), \
                    contextlib.redirect_stdout(out):
                code = cr.main()
            msg = git(repo, "log", "-1", "--format=%B") if code == 0 else ""
            return code, out.getvalue(), msg, written

    def test_the_session_bytes_are_committed_and_named(self):
        code, out, msg, written = self.run_commit()
        self.assertEqual(code, 0, out)
        self.assertIn(hashlib.sha256(written.encode()).hexdigest(), msg, "B1-commit: the message states the digest")
        self.assertNotIn("committed unedited", msg, "B1-commit")

    def test_an_edited_ruling_line_is_refused(self):
        def edit(folder, launch):
            p = folder / "prefreeze-6.md"
            p.write_text(p.read_text().replace(DO, "**Ruling: DO NOT FREEZE.**"))
        code, out, _, _ = self.run_commit(tamper=edit)
        self.assertEqual(code, 1, out)
        self.assertIn("changed after the reviewer wrote it", out, "B1-commit")

    def test_a_forged_report_and_digest_line_are_refused(self):
        # the review of f3ae7772, MAJOR: both forged, the record's digest line made to match the forged report
        def forge(folder, launch):
            p = folder / "prefreeze-6.md"
            p.write_text(p.read_text().replace(DO, "**Ruling: DO NOT FREEZE.**"))
            forged = hashlib.sha256(p.read_bytes()).hexdigest()
            rec = launch / "blindness.txt"
            rec.write_text("\n".join(bl.REPORT_DIGEST + forged if ln.startswith(bl.REPORT_DIGEST) else ln
                                     for ln in rec.read_text().split("\n")))
        code, out, _, _ = self.run_commit(tamper=forge)
        self.assertEqual(code, 1, out)
        self.assertIn("not the one blindness.py writes from the reviewer's session now", out, "B1-commit")

    def test_a_record_edited_anywhere_is_refused(self):
        def edit(folder, launch):
            rec = launch / "blindness.txt"
            rec.write_text(rec.read_text().replace("UNEXPLAINED", "UNEXPLAlNED", 1))
        code, out, _, _ = self.run_commit(tamper=edit)
        self.assertEqual(code, 1, out)
        self.assertIn("not the one blindness.py writes", out, "B1-commit")

    def test_a_session_the_round_did_not_register_is_refused(self):
        code, out, _, _ = self.run_commit(sid="00000000-0000-5000-8000-00000000dead")
        self.assertEqual(code, 1, out)
        self.assertIn("round 6's registered row derives", out, "MINOR 1: the session is the registered row's")

    def test_no_session_id_is_refused(self):
        code, out, _, _ = self.run_commit(session=False)
        self.assertEqual(code, 1, out)
        self.assertIn("no session id", out, "B1-commit")

    def test_the_record_states_the_session_file_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder, launch, projects, sid = session_rig(Path(tmp), report_text("0" * 64))
            text = bl.report(folder, sid, projects)
            want = hashlib.sha256((projects / "-round" / f"{sid}.jsonl").read_bytes()).hexdigest()
        self.assertIn(bl.SESSION_DIGEST + want, text, "B1-commit: section 8 names the session file's bytes")


@contextlib.contextmanager
def seed(n: int, *, record: str, edit: bool = False):
    """A scratch repository whose round n is registered and committed with a DO FREEZE report; `record` is "session"
    (the record states the report's digest), "none" (it states none) or "other" (another digest)."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, "init", "-q")
        review_dir = repo / study.STUDY_REL / study.REVIEW_DIR
        review_dir.mkdir(parents=True)
        draft = review_dir.parent / "prereg-draft.json"
        draft.write_bytes(b'{"synthetic": "draft"}\n')
        (review_dir / "rounds.json").write_text(json.dumps({"rows": [{"n": k, "kind": "prefreeze", "voids": None}
                                                                     for k in range(1, n + 1)]}) + "\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "register")
        sid = takes.session_id_for(git(repo, "rev-parse", "HEAD"))
        written = report_text(hashlib.sha256(draft.read_bytes()).hexdigest())
        digest = {"session": bl.REPORT_DIGEST + hashlib.sha256(written.encode()).hexdigest(),
                  "none": bl.REPORT_UNBOUND + "synthetic", "other": bl.REPORT_DIGEST + "0" * 64}[record]
        (review_dir / f"prefreeze-{n}-blindness.txt").write_text(f"session id: {sid}\n{digest}\n")
        (review_dir / f"prefreeze-{n}.md").write_text(written.replace("synthetic review", "edited") if edit else written)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", f"review {n}")
        with mock.patch.object(freeze, "REPO", repo), mock.patch.object(freeze, "DRAFT", draft):
            yield f"{study.STUDY_REL}/{study.REVIEW_DIR}/prefreeze-{n}.md"


class B1Freeze(unittest.TestCase):
    def test_the_session_bytes_seed(self):
        with seed(6, record="session") as rel:
            self.assertIsNone(freeze.registered_review_problem(rel, 6), "B1-freeze")

    def test_other_bytes_never_seed(self):
        for kw in ({"record": "session", "edit": True}, {"record": "other"}, {"record": "none"}):
            with self.subTest(**kw), seed(6, **kw) as rel:
                got = freeze.registered_review_problem(rel, 6)
                self.assertTrue(got and ("reviewer's session wrote" in got), f"B1-freeze: {kw}: {got}")

    def test_rounds_1_to_4_are_grandfathered_by_number(self):
        self.assertEqual(freeze.REPORT_DIGEST_GRANDFATHERED, (1, 2, 3, 4, 7), "B1-freeze")   # 7: lane fold9
        with seed(4, record="none") as rel:
            self.assertIsNone(freeze.registered_review_problem(rel, 4), "B1-freeze")
        with seed(5, record="none") as rel:
            self.assertIsNotNone(freeze.registered_review_problem(rel, 5), "B1-freeze: round 5 is after the rule")

    def test_the_session_id_is_read_from_the_records_own_line(self):
        # the re-check of 0beda082, MINOR 1: a record that holds the id only inside another line never binds
        with seed(6, record="session") as rel:
            blind = freeze.REPO / rel.replace(".md", "-blindness.txt")
            text = blind.read_text()
            sid = text.split("\n", 1)[0].removeprefix("session id: ")
            blind.write_text(text.replace(f"session id: {sid}", f"not the session id: {sid} (quoted)"))
            git(freeze.REPO, "commit", "-q", "-am", "requote")
            got = freeze.registered_review_problem(rel, 6)
            self.assertTrue(got and "does not name the session id" in got, f"MINOR 1: {got}")

    def test_freeze_reads_the_record_with_blindness_own_reader(self):
        self.assertEqual(freeze._blindness().REPORT_DIGEST, bl.REPORT_DIGEST, "B1-freeze")


class B2Paths(unittest.TestCase):
    def test_placeholders_and_bare_roots_are_no_host_path(self):
        for t in ("the fixture's `/gpfs/home/<user>` placeholder", ".../agent.jsonl:/home/<user",
                  "grepped for checkout-shaped strings (`/Users/`, `gap-study`)", "a path under /home/ alone",
                  "(/private/)"):
            with self.subTest(text=t):
                self.assertIsNone(cr.ABS_PATH.search(t), f"B2-paths: {t!r} read as a host path")

    def test_a_real_host_path_still_refuses(self):
        for t in ("/Users/somebody/aegis/x.md", "/home/\u00e9l\u00e8ve/x", "see /home/javier/repo", "/private/tmp/run-1/x",
                  "/var/folders/ab/T/tmp1", "`/Users/someone/`"):
            with self.subTest(text=t):
                self.assertIsNotNone(cr.ABS_PATH.search(t), f"B2-paths: {t!r} passed")
                self.assertIn("absolute path", " ".join(cr.report_problems("x\n" + t, "0")), "B2-paths")

    def test_review_4_as_written_needs_no_mask_now(self):
        text = (HERE / study.REVIEW_DIR / "prefreeze-4.as-written.md").read_text()
        self.assertIsNone(cr.ABS_PATH.search(text), "B2-paths: the as-written report would still be refused")


if __name__ == "__main__":
    unittest.main()
