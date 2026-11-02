#!/usr/bin/env python3
"""Lane fold8/review-binding (Gap Study round 4; pre-freeze review 6, MAJORs 1 and 2; glitch-45's ruling of Mon 2 Nov
2026, under Javier's standing delegation): the freeze seeds only from the latest review ever registered or committed,
and only when the code it freezes is the code that review was handed.

  M1-road      review 6's clone road, replayed in a scratch repository: an approving round 7, a later round 8, then one
               commit deleting review 8's report and blindness record and marking row 8 spent_without_work. Round 7
               no longer seeds: review 8's report was committed once, and its row is marked spent with a committed
               report. rounds.py --check refuses that register too.
  M1-register  a later prefreeze row in review_kit/rounds.json, spent, voided or open, or in any committed version of
               the register, stops an earlier seed; a spent row whose report was ever committed stops any seed.
  M1-grand     no round in REPORT_DIGEST_GRANDFATHERED (1-4) seeds a freeze, though registered_review_problem still
               reads it as a registered round; review 4 at this repository's HEAD is refused by each new check.
  M2-pinned    a pinned file whose bytes at HEAD are not its bytes at the seed round's launch_commit stops the seed,
               and the refusal names the first differing path; a launch_commit that is absent, not a commit or not an
               ancestor of HEAD stops it too.
  M2-allowed   the round's own report, its blindness record and rounds.json may differ, by name, pinned or not; so
               may two record-only additions the freeze could not run without (entries appended to
               COPIED.d/review-records.json claiming exactly that report and record, and language-allowlist.json
               excusals naming exactly those files). Any other change to either file stops the seed.
  wiring       freeze.main, freeze_rehearsal.main and run_builders.latest_review read the seed through
               review_file_problems, so the rehearsal refuses exactly what the real freeze refuses.

Scratch git repositories in temporary directories only. No model, network or container.
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

RK = study.REVIEW_DIR
DO = freeze.RULING_LINE
DO_NOT = "**Ruling: DO NOT FREEZE.**"
FRAGMENT = "COPIED.d/review-records.json"
ALLOWLIST = "language-allowlist.json"


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                          "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"git {args}: {out.stderr}")
    return out.stdout.strip()


def load_rounds(repo: Path):
    """review_kit/rounds.py loaded on its own, pointed at the scratch repository."""
    spec = importlib.util.spec_from_file_location("fold8_rounds", HERE / RK / "rounds.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REPO = repo
    mod.STUDY_DIR = repo / study.STUDY_REL
    mod.REGISTER = mod.STUDY_DIR / RK / "rounds.json"
    mod.BRIEF = mod.STUDY_DIR / RK / "BRIEF.md"
    return mod


class Rig:
    """A scratch repository shaped like the study: a draft, one pinned code file, the review-records fragment, the
    language allowlist and the round register."""

    def __init__(self, root: Path):
        self.repo = root
        git(root, "init", "-q")
        self.study = root / study.STUDY_REL
        (self.study / RK).mkdir(parents=True)
        (self.study / "COPIED.d").mkdir()
        self.draft = self.study / "prereg-draft.json"
        self.draft.write_bytes(b'{"synthetic": "draft"}\n')
        (self.study / "code.py").write_text("x = 1\n")
        self.write_json(FRAGMENT, {"lane": "review-records", "files": [
            {"path": FRAGMENT, "status": "new", "reason": "synthetic"}]})
        self.write_json(ALLOWLIST, {"role": "synthetic", "excused": [
            {"file": study.rel("code.py"), "pattern": "p", "line_text": "x = 1", "ruled": "2026-11-02", "why": "w"}]})
        self.write_json(f"{RK}/rounds.json", {"rows": []})
        self.row_sha: dict[int, str] = {}
        self.commit("base")

    def path(self, rel: str) -> Path:
        return self.study / rel

    def write_json(self, rel: str, value) -> None:
        self.path(rel).write_text(json.dumps(value, indent=2) + "\n")

    def read_json(self, rel: str):
        return json.loads(self.path(rel).read_text())

    def commit(self, msg: str) -> str:
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", msg)
        return git(self.repo, "rev-parse", "HEAD")

    def rows(self) -> list:
        return self.read_json(f"{RK}/rounds.json")["rows"]

    def set_rows(self, rows) -> None:
        self.write_json(f"{RK}/rounds.json", {"rows": rows})

    def register(self, n: int, **extra) -> str:
        row = {"n": n, "kind": "prefreeze", "launch_commit": git(self.repo, "rev-parse", "HEAD"), "voids": None}
        row.update(extra)
        self.set_rows(self.rows() + [row])
        self.row_sha[n] = self.commit(f"register round {n}")
        return self.row_sha[n]

    def review(self, n: int, ruling: str = DO) -> str:
        digest = hashlib.sha256(self.draft.read_bytes()).hexdigest()
        text = f"{freeze.REVIEW_DIGEST_PREFIX}{digest}\n\n# synthetic review {n}\n\n{ruling}\n"
        sid = takes.session_id_for(self.row_sha[n])
        written = freeze._blindness().REPORT_DIGEST + hashlib.sha256(text.encode()).hexdigest()
        self.path(f"{RK}/prefreeze-{n}-blindness.txt").write_text(f"session id: {sid}\n{written}\n")
        self.path(f"{RK}/prefreeze-{n}.md").write_text(text)
        return self.commit(f"review {n}")

    def pinned(self, *more: str) -> list[str]:
        return [study.rel(p) for p in ("code.py", "prereg-draft.json", FRAGMENT, ALLOWLIST, f"{RK}/rounds.json",
                                       *more)]

    @contextlib.contextmanager
    def patched(self, *more: str):
        with mock.patch.object(freeze, "REPO", self.repo), mock.patch.object(freeze, "DRAFT", self.draft), \
                mock.patch.object(freeze, "PINNED", self.pinned(*more)):
            yield

    def problems(self, sha: str, *more: str):
        with self.patched(*more):
            return freeze.review_file_problems(sha)

    def rounds_check(self) -> tuple[int, str]:
        mod = load_rounds(self.repo)
        with contextlib.redirect_stdout(io.StringIO()) as said:
            code = mod.check()
        return code, said.getvalue()


@contextlib.contextmanager
def rig():
    with tempfile.TemporaryDirectory() as tmp:
        yield Rig(Path(tmp))


def report_rel(n: int) -> str:
    return study.rel(RK, f"prefreeze-{n}.md")


class M1Road(unittest.TestCase):
    def test_the_reviewers_clone_road_is_refused(self):
        with rig() as r:
            r.register(7)
            seed = r.review(7)
            self.assertEqual(r.problems(seed), ([], report_rel(7)), "M1-road: the approving round seeds at first")
            r.register(8)
            r.review(8, DO_NOT)
            self.assertTrue(r.problems(seed)[0], "M1-road: the later review stops the earlier seed")
            # the road: delete review 8's pair, mark its row spent by hand, one commit
            git(r.repo, "rm", "-q", f"{study.rel(RK)}/prefreeze-8.md", f"{study.rel(RK)}/prefreeze-8-blindness.txt")
            rows = r.rows()
            rows[1]["spent_without_work"] = "x"
            r.set_rows(rows)
            r.commit("drop")
            bad, name = r.problems(seed)
            self.assertIsNone(name, f"M1-road: round 7 seeds after the drop: {bad}")
            self.assertTrue(any("round 8" in b for b in bad), f"M1-road: {bad}")
            code, said = r.rounds_check()
            self.assertEqual(code, 1, f"M1-road: rounds.py --check passes the dropped review: {said}")
            self.assertIn("prefreeze-8.md", said, "M1-road")


    def test_a_deleted_report_alone_still_stops_the_seed(self):
        # the report history on its own (no register row names round 8): a committed then deleted prefreeze-8.md
        with rig() as r:
            r.register(7)
            seed = r.review(7)
            r.path(f"{RK}/prefreeze-8.md").write_text("a later review\n")
            r.commit("a later report")
            git(r.repo, "rm", "-q", f"{study.rel(RK)}/prefreeze-8.md")
            r.commit("drop it")
            bad, name = r.problems(seed)
            self.assertTrue(bad and name is None and "prefreeze-8.md was committed" in bad[0], f"M1-road: {bad}")


class M1Register(unittest.TestCase):
    def test_a_later_registered_row_stops_the_seed(self):
        for extra in ({}, {"spent_without_work": "rate limit"}, {"voided_by": 3}):
            with self.subTest(**extra), rig() as r:
                r.register(7)
                seed = r.review(7)
                r.register(8, **extra)
                bad, name = r.problems(seed)
                self.assertTrue(bad and name is None, f"M1-register: row 8 {extra} left round 7 seeding")
                self.assertIn("round 8", bad[0], f"M1-register: {bad}")

    def test_a_row_removed_from_the_register_still_counts(self):
        with rig() as r:
            r.register(7)
            seed = r.review(7)
            r.register(8)
            r.set_rows(r.rows()[:1])
            r.commit("unregister round 8")
            bad, name = r.problems(seed)
            self.assertTrue(bad and "round 8" in bad[0], f"M1-register: {bad}")

    def test_a_spent_row_with_a_committed_report_stops_any_seed(self):
        with rig() as r:
            r.register(6)
            r.review(6, DO_NOT)
            rows = r.rows()
            rows[0]["spent_without_work"] = "x"
            r.set_rows(rows)
            r.commit("close 6 as spent")
            r.register(7)
            seed = r.review(7)
            bad, name = r.problems(seed)
            self.assertTrue(bad and name is None, f"M1-register: a spent row with a report: {bad}")
            self.assertIn("prefreeze-6.md", bad[0], f"M1-register: {bad}")
            code, said = r.rounds_check()
            self.assertEqual(code, 1, f"M1-register: rounds.py --check passes it: {said}")

    def test_rounds_check_close_spent_refuses_a_report_ever_committed(self):
        with rig() as r:
            r.register(6)
            r.review(6, DO_NOT)
            git(r.repo, "rm", "-q", f"{study.rel(RK)}/prefreeze-6.md")
            r.commit("drop 6")
            mod = load_rounds(r.repo)
            with mock.patch.object(sys, "argv", ["rounds.py", "--close-spent", "0", "--reason", "x"]), \
                    contextlib.redirect_stdout(io.StringIO()) as said:
                code = mod.main()
            self.assertEqual(code, 1, f"M1-register: a dropped report's row closed as spent: {said.getvalue()}")

    def test_the_clean_register_still_checks_ok(self):
        with rig() as r:
            r.register(7)
            r.review(7)
            code, said = r.rounds_check()
            self.assertEqual(code, 0, said)


class M1Grandfathered(unittest.TestCase):
    def test_no_grandfathered_round_seeds(self):
        self.assertEqual(freeze.REPORT_DIGEST_GRANDFATHERED, (1, 2, 3, 4))
        for n in freeze.REPORT_DIGEST_GRANDFATHERED:
            with self.subTest(round=n), rig() as r:
                r.register(n)
                seed = r.review(n)
                bad, name = r.problems(seed)
                self.assertTrue(bad and name is None, f"M1-grand: round {n} seeds: {bad}")
                self.assertIn("grandfathered", bad[0], f"M1-grand: {bad}")
                with r.patched():
                    self.assertIsNone(freeze.registered_review_problem(report_rel(n), n),
                                      "M1-grand: it is still a registered round")

    def test_review_4_at_head_is_refused_by_each_new_check(self):
        rel = report_rel(4)
        self.assertIsNotNone(freeze.later_review_problem(rel, 4), "M1: review 4 is not the latest")
        self.assertIsNotNone(freeze.grandfathered_seed_problem(rel, 4), "M1: review 4 is grandfathered")
        got = freeze.launch_binding_problem(rel, 4)
        self.assertTrue(got and "4163754f" in got, f"M2: review 4's launch commit is not HEAD's code: {got}")


class M2Pinned(unittest.TestCase):
    def test_a_pinned_change_after_launch_is_refused_and_named(self):
        for when in ("before the review", "after the review"):
            with self.subTest(when=when), rig() as r:
                r.register(7)
                if when == "before the review":
                    r.path("code.py").write_text("x = 2\n")
                    r.commit("code")
                seed = r.review(7)
                if when == "after the review":
                    r.path("code.py").write_text("x = 2\n")
                    r.commit("code")
                bad, name = r.problems(seed)
                self.assertTrue(bad and name is None, f"M2-pinned: a code change {when} seeds: {bad}")
                self.assertIn(study.rel("code.py"), bad[0], f"M2-pinned: the path is named: {bad}")

    def test_a_new_pinned_file_after_launch_is_refused(self):
        with rig() as r:
            r.register(7)
            r.path("new.py").write_text("y = 1\n")
            seed = r.review(7)
            bad, _ = r.problems(seed, "new.py")
            self.assertTrue(bad and study.rel("new.py") in bad[0], f"M2-pinned: {bad}")

    def test_an_unpinned_change_is_not_read(self):
        with rig() as r:
            r.register(7)
            r.path("notes.txt").write_text("not pinned\n")
            seed = r.review(7)
            self.assertEqual(r.problems(seed), ([], report_rel(7)), "M2: only pinned paths are compared")

    def test_a_bad_launch_commit_is_refused(self):
        for launch in (None, "not-a-commit", "0" * 40, "orphan"):
            with self.subTest(launch=launch), rig() as r:
                if launch == "orphan":
                    other = Path(tempfile.mkdtemp(dir=r.repo.parent))
                    git(other, "init", "-q")
                    (other / "f").write_text("f\n")
                    git(other, "add", "-A")
                    git(other, "commit", "-q", "-m", "orphan")
                    git(r.repo, "fetch", "-q", str(other), "HEAD")
                    launch = git(r.repo, "rev-parse", "FETCH_HEAD")
                r.register(7)
                rows = r.rows()
                if launch is None:
                    del rows[0]["launch_commit"]
                else:
                    rows[0]["launch_commit"] = launch
                r.set_rows(rows)
                r.row_sha[7] = r.commit("register round 7")       # the row's introducing commit stays the first
                r.row_sha[7] = git(r.repo, "rev-parse", "HEAD~1")
                seed = r.review(7)
                bad, name = r.problems(seed)
                self.assertTrue(bad and name is None and "launch_commit" in bad[0], f"M2: {launch}: {bad}")


class M2Allowed(unittest.TestCase):
    def test_the_three_named_paths_may_differ_pinned_or_not(self):
        with rig() as r:
            r.register(7)
            seed = r.review(7)
            self.assertEqual(r.problems(seed), ([], report_rel(7)), "M2-allowed: unpinned report")
            more = (f"{RK}/prefreeze-7.md", f"{RK}/prefreeze-7-blindness.txt")
            self.assertEqual(r.problems(seed, *more), ([], report_rel(7)), "M2-allowed: report and record pinned")

    def test_another_rounds_report_is_not_allowed(self):
        with rig() as r:
            r.register(7)
            r.path(f"{RK}/prefreeze-3.md").write_text("an older report, edited\n")
            r.commit("edit an older report")
            seed = r.review(7)
            bad, _ = r.problems(seed, f"{RK}/prefreeze-3.md")
            self.assertTrue(bad and "prefreeze-3.md" in bad[0], f"M2-allowed: {bad}")

    def claim(self, r: Rig, paths):
        frag = r.read_json(FRAGMENT)
        frag["files"] += [{"path": p, "status": "new", "reason": "the seed round's own record"} for p in paths]
        r.write_json(FRAGMENT, frag)

    def excuse(self, r: Rig, files):
        allow = r.read_json(ALLOWLIST)
        allow["excused"] += [{"file": f, "pattern": "ratio-slash", "line_text": "18/18", "ruled": "2026-11-02",
                              "why": "a tally"} for f in files]
        r.write_json(ALLOWLIST, allow)

    def test_the_seed_rounds_own_claims_and_excusals_may_be_added(self):
        with rig() as r:
            r.register(7)
            seed = r.review(7)
            self.claim(r, [f"{RK}/prefreeze-7.md", f"{RK}/prefreeze-7-blindness.txt"])
            self.excuse(r, [report_rel(7)])
            r.commit("claim and excuse review 7")
            self.assertEqual(r.problems(seed), ([], report_rel(7)), "M2-allowed: record-only additions")

    def test_any_other_change_to_the_two_records_is_refused(self):
        cases = {
            "claim of another path": lambda r: self.claim(r, ["code2.py"]),
            "claim edited": lambda r: r.write_json(FRAGMENT, {"lane": "review-records", "files": [
                {"path": FRAGMENT, "status": "new", "reason": "edited"},
                {"path": f"{RK}/prefreeze-7.md", "status": "new", "reason": "r"}]}),
            "claim with a source": lambda r: (self.claim(r, []), r.write_json(FRAGMENT, {
                **r.read_json(FRAGMENT), "files": r.read_json(FRAGMENT)["files"] + [
                    {"path": f"{RK}/prefreeze-7.md", "status": "identical", "source": "evals/x.md"}]})),
            "excusal of another file": lambda r: self.excuse(r, [study.rel("code.py")]),
            "excusal removed": lambda r: r.write_json(ALLOWLIST, {"role": "synthetic", "excused": []}),
            "excusal reordered in front": lambda r: r.write_json(ALLOWLIST, {"role": "synthetic", "excused": [
                {"file": report_rel(7), "pattern": "p", "line_text": "t", "ruled": "d", "why": "w"},
                *r.read_json(ALLOWLIST)["excused"]]}),
        }
        for name, change in cases.items():
            with self.subTest(case=name), rig() as r:
                r.register(7)
                seed = r.review(7)
                change(r)
                r.commit(name)
                bad, got = r.problems(seed)
                self.assertTrue(bad and got is None, f"M2-allowed: {name} seeds: {bad}")

    def test_a_claim_in_another_fragment_is_refused(self):
        with rig() as r:
            r.write_json("COPIED.d/other.json", {"lane": "other", "files": [
                {"path": "COPIED.d/other.json", "status": "new", "reason": "r"}]})
            r.commit("other fragment")
            r.register(7)
            seed = r.review(7)
            r.write_json("COPIED.d/other.json", {"lane": "other", "files": [
                {"path": "COPIED.d/other.json", "status": "new", "reason": "r"},
                {"path": f"{RK}/prefreeze-7.md", "status": "new", "reason": "r"}]})
            r.commit("claim in other")
            bad, _ = r.problems(seed, "COPIED.d/other.json")
            self.assertTrue(bad and "COPIED.d/other.json" in bad[0], f"M2-allowed: {bad}")


class Wiring(unittest.TestCase):
    def test_every_seed_reader_goes_through_review_file_problems(self):
        for mod, name in ((HERE / "freeze.py", "main"), (HERE / "freeze_rehearsal.py", "main"),
                          (HERE / "run_builders.py", "latest_review")):
            src = mod.read_text()
            body = src[src.index(f"\ndef {name}("):]
            body = body[:body.find("\ndef ", 1) if body.find("\ndef ", 1) > 0 else None]
            self.assertIn("review_file_problems(", body, f"wiring: {mod.name} {name}")

    def test_review_file_problems_reads_both_fixes(self):
        with rig() as r:
            r.register(7)
            seed = r.review(7)
            for fn in ("later_review_problem", "grandfathered_seed_problem", "launch_binding_problem"):
                with self.subTest(fn=fn), r.patched(), mock.patch.object(freeze, fn, lambda rep, n: "synthetic"):
                    self.assertEqual(freeze.review_file_problems(seed), (["synthetic"], None), f"wiring: {fn}")


if __name__ == "__main__":
    unittest.main()
