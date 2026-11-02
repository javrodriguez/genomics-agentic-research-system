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
            code, said = r.rounds_check()
            self.assertEqual(code, 1, f"M1-register: rounds.py --check passes a cut register: {said}")
            self.assertIn("append-only", said, "M1-register")

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
                    other = Path(tempfile.mkdtemp())
                    self.addCleanup(__import__("shutil").rmtree, other, True)
                    git(other, "init", "-q")
                    (other / "f").write_text("f\n")
                    git(other, "add", "-A")
                    git(other, "commit", "-q", "-m", "orphan")
                    git(r.repo, "fetch", "-q", str(other), "HEAD")
                    launch = git(r.repo, "rev-parse", "FETCH_HEAD")
                # written by the row's one introducing commit (the confirm review of b968597e: a row is never edited)
                r.register(7, launch_commit=launch)
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


# ---- the fresh review of bc438542 (CHANGES), glitch-45's ruling of Mon 2 Nov 2026 ----

def close_spent(r: "Rig", row: int, reason: str = "rate limit") -> int:
    mod = load_rounds(r.repo)
    with mock.patch.object(sys, "argv", ["rounds.py", "--close-spent", str(row), "--reason", reason]), \
            contextlib.redirect_stdout(io.StringIO()):
        return mod.main()


class B1Relabel(unittest.TestCase):
    """BLOCKER 1: a row's launch_commit relabelled in place after a pinned change."""

    def test_the_reviewers_relabel_commit_is_refused_by_freeze_and_check(self):
        for when in ("after the review", "before the review"):
            with self.subTest(when=when), rig() as r:
                r.register(7)
                r.path("code.py").write_text("x = 2\n")
                r.commit("code changed after the launch")
                if when == "after the review":
                    seed = r.review(7)
                rows = r.rows()
                rows[0]["launch_commit"] = git(r.repo, "rev-parse", "HEAD")
                r.set_rows(rows)
                r.commit("relabel")
                if when == "before the review":
                    seed = r.review(7)
                bad, name = r.problems(seed)
                self.assertTrue(bad and name is None and ("introduced" in bad[0] or "written once" in bad[0]),
                                f"B1: the relabel seeds: {bad}")
                code, said = r.rounds_check()
                self.assertEqual(code, 1, f"B1: rounds.py --check passes the relabel: {said}")
                self.assertIn("launch_commit", said, "B1")

    def test_a_launch_commit_that_is_not_the_row_commits_parent_is_refused(self):
        with rig() as r:
            first = git(r.repo, "rev-parse", "HEAD")
            r.path("notes.txt").write_text("unpinned\n")
            r.commit("an unpinned commit")
            rows = r.rows() + [{"n": 7, "kind": "prefreeze", "launch_commit": first, "voids": None}]
            r.set_rows(rows)
            r.row_sha[7] = r.commit("register round 7 naming the grandparent")
            seed = r.review(7)
            bad, name = r.problems(seed)
            self.assertTrue(bad and name is None and "parent" in bad[0], f"B1: {bad}")

    def test_any_other_in_place_field_edit_is_refused_by_check(self):
        for field, value in (("n", 9), ("kind", "verify"), ("prompt_sha256", "0" * 64), ("voids", 3),
                             ("added", "2026-01-01T00:00:00+00:00"), ("extra", "x")):
            with self.subTest(field=field), rig() as r:
                r.register(7)
                r.review(7)
                rows = r.rows()
                rows[0][field] = value
                r.set_rows(rows)
                r.commit(f"edit {field}")
                code, said = r.rounds_check()
                self.assertEqual(code, 1, f"B1: an in-place {field} edit passes --check: {said}")

    def test_the_kits_own_close_spent_still_checks_ok(self):
        with rig() as r:
            r.register(6)
            self.assertEqual(close_spent(r, 0), 0)
            r.commit("close 6 as spent")
            r.register(7)
            r.review(7)
            code, said = r.rounds_check()
            self.assertEqual(code, 0, f"B1: the close-spent writer's shape is refused: {said}")

    def test_a_hand_closed_row_off_the_writers_shape_is_refused(self):
        for extra in ({"spent_without_work": "x"}, {"spent_without_work": "", "spent_at": "2026-11-02T00:00:00+00:00"},
                      {"spent_without_work": "x", "spent_at": "yesterday"}, {"voided_by": 1},
                      {"spent_without_work": "x", "spent_at": "2026-11-02T00:00:00+00:00", "note": "y"}):
            with self.subTest(**extra), rig() as r:
                r.register(6)
                rows = r.rows()
                rows[0].update(extra)
                r.set_rows(rows)
                r.commit("hand close")
                code, said = r.rounds_check()
                self.assertEqual(code, 1, f"B1: a hand-closed row {extra} passes --check: {said}")

    def test_a_void_named_by_its_re_run_row_checks_ok(self):
        with rig() as r:
            r.register(6)
            r.register(7, voids=0)
            rows = r.rows()
            rows[0]["voided_by"] = 1
            r.set_rows(rows)
            r.commit("record the void")
            code, said = r.rounds_check()
            self.assertNotIn("in place", said, f"B1: the void shape is refused: {said}")


class M1Reflog(unittest.TestCase):
    """MAJOR 1: a later round reachable only through the reflog still counts."""

    def test_a_rewound_later_round_still_stops_the_seed(self):
        with rig() as r:
            r.register(7)
            seed = r.review(7)
            r.register(8)
            r.review(8, DO_NOT)
            git(r.repo, "reset", "-q", "--hard", seed)
            bad, name = r.problems(seed)
            self.assertTrue(bad and name is None and "round 8" in bad[0], f"MAJOR 1: a rewound round 8: {bad}")

    def test_close_spent_refuses_a_report_only_the_reflog_holds(self):
        with rig() as r:
            row = r.register(6)
            r.review(6, DO_NOT)
            git(r.repo, "reset", "-q", "--hard", row)
            self.assertEqual(close_spent(r, 0), 1, "MAJOR 1: a rewound report's row closed as spent")


MIRROR_URL = "https://github.com/javrodriguez/gars-cloud-mirror.git"


class M1PublishedTip(unittest.TestCase):
    def tip(self, r: Rig):
        with r.patched():
            return freeze.published_tip_problem()

    def test_no_mirror_remote_prints_a_residual(self):
        with rig() as r:
            problem, note = self.tip(r)
            self.assertIsNone(problem)
            self.assertTrue(note and note.startswith("RESIDUAL"), note)

    def test_a_mirror_remote_binds_head_to_its_freeze_line_tip(self):
        with rig() as r:
            git(r.repo, "remote", "add", "mirror", MIRROR_URL)
            problem, _ = self.tip(r)
            self.assertTrue(problem and "never fetched" in problem, f"published tip: no tracking ref: {problem}")
            base = git(r.repo, "rev-parse", "HEAD")
            r.path("notes.txt").write_text("a\n")
            r.commit("on")
            git(r.repo, "update-ref", f"refs/remotes/mirror/{freeze.FREEZE_LINE}", base)
            self.assertEqual(self.tip(r), (None, None), "published tip: HEAD descends from the tip")
            git(r.repo, "checkout", "-q", "--detach", base)
            git(r.repo, "commit", "-q", "--allow-empty", "-m", "side")
            side = git(r.repo, "rev-parse", "HEAD")
            git(r.repo, "checkout", "-q", "-")
            git(r.repo, "update-ref", f"refs/remotes/mirror/{freeze.FREEZE_LINE}", side)
            problem, _ = self.tip(r)
            self.assertTrue(problem and "does not descend" in problem, f"published tip: {problem}")

    def test_a_mirror_named_by_remote_name_counts_too(self):
        with rig() as r:
            git(r.repo, "remote", "add", "gars-cloud-mirror", "/nowhere")
            problem, _ = self.tip(r)
            self.assertTrue(problem and "never fetched" in problem, problem)

    def test_main_reads_the_published_tip(self):
        src = (HERE / "freeze.py").read_text()
        body = src[src.index("\ndef main("):]
        self.assertIn("published_tip_problem()", body, "wiring: freeze.main reads the published tip")


class M1ShallowClones(unittest.TestCase):
    def cloned(self, r: Rig, *flags):
        dest = Path(tempfile.mkdtemp(dir=r.repo.parent))
        subprocess.run(["git", "clone", "-q", *flags, f"file://{r.repo}", str(dest)], check=True, capture_output=True)
        return dest

    def test_a_shallow_or_single_branch_clone_is_refused(self):
        for flags, word in ((("--depth", "1"), "shallow"), (("--single-branch",), "single-branch")):
            with self.subTest(flags=flags), rig() as r:
                r.register(7)
                seed = r.review(7)
                dest = self.cloned(r, *flags)
                with mock.patch.object(freeze, "REPO", dest), \
                        mock.patch.object(freeze, "DRAFT", dest / study.STUDY_REL / "prereg-draft.json"), \
                        mock.patch.object(freeze, "PINNED", r.pinned()):
                    bad, name = freeze.review_file_problems(seed)
                self.assertTrue(bad and name is None and word in bad[0], f"MINOR 1: {flags}: {bad}")

    def test_a_full_clone_still_seeds(self):
        with rig() as r:
            r.register(7)
            seed = r.review(7)
            dest = self.cloned(r)
            with mock.patch.object(freeze, "REPO", dest), \
                    mock.patch.object(freeze, "DRAFT", dest / study.STUDY_REL / "prereg-draft.json"), \
                    mock.patch.object(freeze, "PINNED", r.pinned()):
                self.assertEqual(freeze.review_file_problems(seed), ([], report_rel(7)))


class M2Mutants(unittest.TestCase):
    """MINOR 2: the review's surviving mutants G7 and G8."""

    def test_g7_a_git_error_reading_a_report_history_refuses(self):
        with rig() as r:
            r.register(6)
            r.review(6, DO_NOT)
            rows = r.rows()
            rows[0]["spent_without_work"] = "x"
            r.set_rows(rows)
            r.commit("close 6 by hand")
            r.register(7)
            seed = r.review(7)
            real = freeze.git

            def failing(*args):
                if args[:2] == ("log", "--all") and "-1" in args:
                    return 128, ""
                return real(*args)
            with r.patched(), mock.patch.object(freeze, "git", failing):
                bad, name = freeze.review_file_problems(seed)
            self.assertTrue(bad and name is None, f"G7: a git error read as never committed: {bad}")
            self.assertTrue(freeze.ever_committed.__doc__)
            with r.patched(), mock.patch.object(freeze, "git", lambda *a: (128, "")):
                self.assertTrue(freeze.ever_committed("anything"), "G7: an unreadable history reads committed")

    def test_g7_rounds_check_reads_a_git_error_as_committed(self):
        with rig() as r:
            mod = load_rounds(r.repo)
            real = mod.subprocess.run

            def run(cmd, *a, **k):
                if "log" in cmd and "-1" in cmd:
                    return subprocess.CompletedProcess(cmd, 128, "", "fatal")
                return real(cmd, *a, **k)
            with mock.patch.object(mod.subprocess, "run", run):
                self.assertTrue(mod.ever_committed(mod.REGISTER), "G7: rounds.ever_committed fails open")

    def test_g8_a_side_branch_launch_with_equal_pinned_bytes_is_not_an_ancestor(self):
        with rig() as r:
            base = git(r.repo, "rev-parse", "HEAD")
            git(r.repo, "checkout", "-q", "--detach", base)
            r.path("notes.txt").write_text("unpinned, on a side branch\n")
            side = r.commit("side")
            git(r.repo, "checkout", "-q", "-")
            r.path("notes.txt").write_text("unpinned, on the line\n")
            r.commit("line")
            rows = r.rows() + [{"n": 7, "kind": "prefreeze", "launch_commit": side, "voids": None}]
            r.set_rows(rows)
            r.row_sha[7] = r.commit("register round 7 on a side-branch launch")
            seed = r.review(7)
            bad, name = r.problems(seed)
            self.assertTrue(bad and name is None and "not an ancestor of HEAD" in bad[0], f"G8: {bad}")


class Nits(unittest.TestCase):
    def test_nit1_an_appended_excusal_carries_exactly_the_five_keys(self):
        for entry in ({"file": None, "pattern": "p", "line_text": "t", "ruled": "d", "why": "w", "note": "x"},
                      {"file": None, "pattern": "p", "line_text": "t", "ruled": "d"}):
            with self.subTest(keys=sorted(entry)), rig() as r:
                r.register(7)
                seed = r.review(7)
                allow = r.read_json(ALLOWLIST)
                allow["excused"].append({**entry, "file": report_rel(7)})
                r.write_json(ALLOWLIST, allow)
                r.commit("excuse")
                bad, name = r.problems(seed)
                self.assertTrue(bad and name is None, f"NIT 1: {sorted(entry)} admitted: {bad}")

    def test_nit2_an_unreadable_old_register_fails_check(self):
        with rig() as r:
            r.register(7)
            r.review(7)
            good = r.path(f"{RK}/rounds.json").read_text()
            r.path(f"{RK}/rounds.json").write_text("not json\n")
            r.commit("break the register")
            r.path(f"{RK}/rounds.json").write_text(good)
            r.commit("mend it")
            code, said = r.rounds_check()
            self.assertEqual(code, 1, f"NIT 2: an unreadable old register version passes: {said}")


# ---- the confirm review of b968597e (CHANGES), glitch-45's ruling of Mon 2 Nov 2026 ----

class ConfirmProbes(unittest.TestCase):
    """MINOR D: the confirm review's two probes, as tests (BLOCKER A and MAJOR B)."""

    def test_a_relabel_through_a_merge_is_refused(self):
        # probe_relabel_merge.py: a side branch re-adds row 7 with a later launch_commit, a merge takes its register,
        # the blindness record's session line is rewritten to the side commit's id, the side branch is deleted
        with rig() as r:
            P = git(r.repo, "rev-parse", "HEAD")
            r.register(7)
            seed = r.review(7)
            self.assertEqual(r.problems(seed), ([], report_rel(7)), "BLOCKER A: the baseline seeds")
            git(r.repo, "checkout", "-q", "-b", "side", P)
            r.path("code.py").write_text("x = 2   # code the reviewer never read\n")
            C2 = r.commit("code change")
            r.set_rows(r.rows() + [{"n": 7, "kind": "prefreeze", "launch_commit": C2, "voids": None}])
            Y = r.commit("register round 7 again, launch at the changed code")
            git(r.repo, "checkout", "-q", "-")
            subprocess.run(["git", "-C", str(r.repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                            "-c", "commit.gpgsign=false", "merge", "-q", "side", "-m", "merge"], capture_output=True)
            git(r.repo, "checkout", "--theirs", "--", study.rel(RK, "rounds.json"))
            blind = r.path(f"{RK}/prefreeze-7-blindness.txt")
            lines = blind.read_text().splitlines()
            lines[0] = f"session id: {takes.session_id_for(Y)}"
            blind.write_text("\n".join(lines) + "\n")
            r.commit("merge side")
            git(r.repo, "branch", "-q", "-D", "side")
            self.assertEqual(r.rows()[0]["launch_commit"], C2, "BLOCKER A: the row at HEAD names the changed code")
            bad, name = r.problems(seed)
            self.assertTrue(bad and name is None, f"BLOCKER A: the merged relabel seeds: {bad}")
            code, said = r.rounds_check()
            self.assertEqual(code, 1, f"BLOCKER A: rounds.py --check passes the merged relabel: {said}")

    def test_the_relabel_is_refused_even_with_the_blindness_record_untouched(self):
        # the register half alone: the row re-added on a side branch and merged, nothing else changed
        with rig() as r:
            P = git(r.repo, "rev-parse", "HEAD")
            r.register(7)
            seed = r.review(7)
            git(r.repo, "checkout", "-q", "-b", "side", P)
            r.path("notes.txt").write_text("unpinned\n")
            C2 = r.commit("an unpinned change")
            r.set_rows(r.rows() + [{"n": 7, "kind": "prefreeze", "launch_commit": C2, "voids": None}])
            r.commit("register round 7 again")
            git(r.repo, "checkout", "-q", "-")
            subprocess.run(["git", "-C", str(r.repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                            "-c", "commit.gpgsign=false", "merge", "-q", "side", "-m", "merge"], capture_output=True)
            git(r.repo, "checkout", "--theirs", "--", study.rel(RK, "rounds.json"))
            r.commit("merge side")
            with r.patched():
                self.assertIsNotNone(freeze.row_introducer(study.rel(RK, "rounds.json"), 0)[1],
                                     "BLOCKER A: two introducers of row 0 read as one")
            bad, name = r.problems(seed)
            self.assertTrue(bad and name is None, f"BLOCKER A: {bad}")

    def test_an_edited_blindness_record_is_refused(self):
        with rig() as r:
            r.register(7)
            seed = r.review(7)
            blind = r.path(f"{RK}/prefreeze-7-blindness.txt")
            blind.write_text(blind.read_text() + "an added line\n")
            r.commit("edit the record")
            bad, name = r.problems(seed)
            self.assertTrue(bad and name is None and "blindness" in bad[0], f"BLOCKER A: {bad}")

    def test_a_later_round_hidden_by_an_ours_merge_is_refused(self):
        # probe_merge.py: round 8 on a lane worktree, merged with -s ours, worktree removed and branch deleted
        with rig() as r:
            r.register(7)
            seed = r.review(7)
            wt = Path(tempfile.mkdtemp()) / "side-wt"
            try:
                git(r.repo, "worktree", "add", "-q", "-b", "side", str(wt))
                side = Rig.__new__(Rig)
                side.repo, side.study = wt, wt / study.STUDY_REL
                side.draft, side.row_sha = side.study / "prereg-draft.json", dict(r.row_sha)
                side.register(8)
                side.review(8, DO_NOT)
                git(r.repo, "merge", "-q", "-s", "ours", "side", "-m", "merge side, keeping the line's tree")
                git(r.repo, "worktree", "remove", str(wt))
                git(r.repo, "branch", "-q", "-D", "side")
            finally:
                import shutil
                shutil.rmtree(wt.parent, ignore_errors=True)
            bad, name = r.problems(seed)
            self.assertTrue(bad and name is None and "round 8" in bad[0], f"MAJOR B: the hidden round 8: {bad}")
            code, said = r.rounds_check()
            self.assertEqual(code, 1, f"MAJOR B: rounds.py --check passes the hidden round: {said}")


class ConfirmNits(unittest.TestCase):
    def test_minor_c_the_mirror_url_matches_in_any_case(self):
        with rig() as r:
            git(r.repo, "remote", "add", "m", "https://github.com/JavRodriguez/GARS-Cloud-Mirror.git")
            with r.patched():
                problem, _ = freeze.published_tip_problem()
            self.assertTrue(problem and "never fetched" in problem, f"MINOR C: {problem}")

    def test_minor_c_the_residual_names_the_real_exposure(self):
        for words in ("last fetched", "force-push", "not scanned"):
            self.assertIn(words, freeze.PUBLISHED_TIP_RESIDUAL, "MINOR C")

    def test_nit_e_an_unreadable_register_version_fails_check(self):
        with rig() as r:
            r.register(7)
            r.review(7)
            first = r.row_sha[7]
            mod = load_rounds(r.repo)
            real = mod.register_at
            with mock.patch.object(mod, "register_at", lambda rev: ("unreadable", None) if rev == first else real(rev)), \
                    contextlib.redirect_stdout(io.StringIO()) as said:
                code = mod.check()
            self.assertEqual(code, 1, f"NIT E: an unreadable version is skipped: {said.getvalue()}")


if __name__ == "__main__":
    unittest.main()
