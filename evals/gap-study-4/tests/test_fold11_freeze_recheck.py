#!/usr/bin/env python3
"""Lane fold11/freeze-recheck (Gap Study round 4; pre-freeze review 8, M1; fold 10's gate review, m1 and m5).

A scratch repository holds the study's real pinned files and the real draft, a registered approving round on the real
register, and a frozen file written by the real freeze.main (so by the real freeze.prepare). Three gates are switched off
in the writer's process only, by name, because they read the walks and the source commits this scratch does not carry:
copy_manifest.problems, coverage_problem and unrecorded_shapes_problem. Nothing the recheck reads is mocked, except where
a test says so. Each test then commits the freeze again by hand, with one edit, and reads the real check.

  D.draft     the draft at the freeze commit hashes to draft_sha256_at_freeze
  D.keys      keys_outside_the_freeze is empty and every key the freeze writes is present
  D.limit     published_tip_residual is freeze.PUBLISHED_TIP_LIMIT, at the check and at check_publication
  D.review    the review file at the parent hashes to its sha256, reads as approval, and review_file_problems is clean
              as of the parent, naming the same file
  D.parent    the recorded parent is the freeze commit's only parent (else the hold printed NOT CHECKED and passed)
  D.touch     the freeze commit changes exactly its three outputs, and its fragment is output_fragment's bytes
  D.bytes     the frozen file is byte for byte what the freeze's own code writes from the parent's tree: a pin dropped, a
              task edited or dropped, a key keys_outside_the_freeze allows but nothing writes
  D.gates     the freeze's two gates on the draft itself: no holdout field, and the order function's digest
  D.holdout   the frozen digests pass the freeze's own validator and the count is theirs
  D.real      outside a disposable rehearsal: the rehearsal record's sha256 is its text's, the beacon reading is no
              synthetic one, the witness is one and is what the freeze derives from its own stamps
  D.network   check_results.py --witness holds the frozen witness to the push records and the reading to the relays
  D.shapes    the freeze's shapes gate on the draft is read again, and it holds on this tree
  D.py39      freeze_as_of never reaches tar's extractall; no claim about Python 3.9, which fails closed at the shapes gate
  D.rounds    rounds.py --add refuses a prefreeze row once a frozen file exists, and leaves a verify row alone
  D.road      a DO FREEZE report that trips both lints lands through the post-review road with no edit to a pinned file
              but its own claims, both lints clean, and the launch binding reads clean
  D.post      after the freeze: rounds.json's pin holds on every row present at the freeze, and only valid verify rows may
              be appended; every other pinned file still refuses; check_results.py --ledger is green along the plan's whole
              road (a take, its records and page, labels, one verify round, two, a new copy-record fragment)
  D.main      main --ledger --rehearsal-plan, the real CLI, passes the clean state and refuses an edited one, and the
              runtime steps of the rehearsal run on it

--witnesses runs every mutant of mutants() against its bound test, each in its own scratch repository. Scratch git
repositories in temporary directories only. No model, network or container.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import freeze  # noqa: E402
import freeze_rehearsal  # noqa: E402
import study  # noqa: E402
import takes  # noqa: E402

SELECTED = None
# A report's words that trip both lints, each as review 8 wrote it: a reviewer restates the guard it reads, and its report
# is never edited.
REPORT_WORDS = ("`not_poolable` forbids comparison, pooling and bridging with rounds 1-3.\n\n"
                "I found no sentence better than a plain count, always read at 690/700.")
LIVE_BOX_PASS = ("live-box record " + "a" * 64 + ": walk lb1, budget 10 s of 20 s, turn 2 cut (end timed-out, exit 124), stream 3 "
                 "unit(s), session 3 unit(s), shape equal, content problems 0, session torn no; files 4 re-read equal; adapter, "
                 "check_take and checker digests this tree's; within the bound")
OUTPUTS = ("prereg.json", "COPIED.json", "COPIED.d/freeze.json")
FRAGMENT = "COPIED.d/review-records.json"
MESSAGE = "Freeze\n\nCo-Authored-By: synthetic <synthetic@example.invalid>\n"

# The check as the battery reads a broken freeze: frozen_commit_problems (880 pins, two processes each, unchanged by this
# lane, and driven unstubbed by D.main) is the only stand-in. `plan` is the --rehearsal-plan flag.
DRIVER = """
import json, sys
sys.path.insert(0, sys.argv[1])
import check_results as cr, freeze
freeze.unrecorded_shapes_problem = lambda draft: None   # reads committed walks this scratch lacks; DShapes reads it real
if sys.argv[3:] != ["unstubbed"]:
    cr.frozen_commit_problems = lambda frozen, commit: []
print("PROBLEMS " + json.dumps(cr.check_frozen_content(rehearsal_plan=sys.argv[2] == "plan")))
"""
# The writer: the real freeze.main. The three names switched off read walks and source commits this scratch lacks.
WRITER = """
import sys
sys.path.insert(0, sys.argv[1])
import freeze
freeze.copy_manifest.problems = lambda *a, **k: []
freeze.coverage_problem = lambda *a, **k: None
freeze.unrecorded_shapes_problem = lambda *a, **k: None
raise SystemExit(freeze.main(sys.argv[2:]))
"""


def run_git(repo: Path, *args: str) -> str:
    got = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                          "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    if got.returncode != 0:
        raise AssertionError(f"git {args}: {got.stderr}")
    return got.stdout.strip()


def source_files() -> list[str]:
    """What the scratch carries: every pinned path, minus the freeze's own outputs (the battery also runs in a frozen
    rehearsal clone, where they exist and would stop the freeze)."""
    gone = {study.rel(p) for p in OUTPUTS}
    return [p for p in freeze.pinned_paths(freeze.PINNED) if p not in gone]


class World:
    """The scratch repository, up to and including a clean freeze commit."""

    def __init__(self, root: Path, mutate=None):
        self.repo = root / "repo"
        self.study = self.repo / study.STUDY_REL
        for rel in source_files():
            f = self.repo / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(HERE.parent.parent / rel, f)
        if mutate:
            mutate(self.study)
        run_git(self.repo, "init", "-q")
        run_git(self.repo, "config", "user.name", "t")
        run_git(self.repo, "config", "user.email", "t@example.invalid")
        self.base = self.commit("the study")
        self.rounds = self.study / study.REVIEW_DIR / "rounds.json"
        register = json.loads(self.rounds.read_text())
        register["rows"] = [r for r in register["rows"] if r.get("kind") == "prefreeze"]   # a verify report is not pinned
        self.rounds.write_text(json.dumps(register, indent=2) + "\n")
        self.base = self.commit("the study, its prefreeze rows")
        self.earlier = max(r["n"] for r in register["rows"] if r.get("kind") == "prefreeze")
        self.n = self.earlier + 1
        kit = root / "kit"
        kit.mkdir()
        shutil.copyfile(self.study / "prereg-draft.json", kit / "prereg.json")
        (kit / "COMMIT").write_text(self.base + "\n")
        got = self.cli(f"{study.REVIEW_DIR}/rounds.py", "--add", "--kind", "prefreeze", "--folder", str(kit))
        if got.returncode != 0:
            raise AssertionError(f"the real rounds.py --add refused: {got.stdout[-800:]}{got.stderr[-800:]}")
        row = self.commit("the round's row")
        self.report = study.rel(study.REVIEW_DIR, f"prefreeze-{self.n}.md")
        digest = hashlib.sha256((self.study / "prereg-draft.json").read_bytes()).hexdigest()
        text = f"{freeze.REVIEW_DIGEST_PREFIX}{digest}\n\n{REPORT_WORDS}\n\n{freeze.RULING_LINE}\n"
        (self.repo / self.report).write_text(text)
        (self.study / study.REVIEW_DIR / f"prefreeze-{self.n}-blindness.txt").write_text(
            f"session id: {takes.session_id_for(row)}\n{freeze._blindness().REPORT_DIGEST}"
            f"{hashlib.sha256(text.encode()).hexdigest()}\n")
        self.review = self.commit("the review")
        claims = self.study / FRAGMENT
        doc = json.loads(claims.read_text())
        doc["files"] += [{"path": f"{study.REVIEW_DIR}/prefreeze-{self.n}{tail}", "status": "new", "reason": "synthetic"}
                         for tail in (".md", "-blindness.txt")]
        claims.write_text(json.dumps(doc, indent=2) + "\n")
        self.parent = self.commit("the review's claims")
        holdout = root / "digests.json"
        freeze.synthetic_holdout_source(self.study / "prereg-draft.json", holdout)
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", "-c", WRITER, str(self.study), "--review-commit",
                              self.review, "--rehearsal", "--write", "--holdout-digests", str(holdout)],
                             capture_output=True, text=True, env=self.env())
        if got.returncode != 0:
            raise AssertionError(f"the real freeze.main refused: {got.stdout[-1500:]}{got.stderr[-1500:]}")
        self.outputs = {p: (self.study / p).read_bytes() for p in OUTPUTS}
        self.frozen = json.loads(self.outputs["prereg.json"])
        self.commit_freeze()

    def env(self) -> dict:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            env.pop(name, None)
        return env

    def commit(self, message: str) -> str:
        run_git(self.repo, "add", "-A")
        run_git(self.repo, "commit", "-q", "--allow-empty", "-m", message)
        return run_git(self.repo, "rev-parse", "HEAD")

    def commit_freeze(self, edit=None, raw=None, also=None) -> str:
        """The freeze commit again, on the same parent, by hand: `edit` changes the frozen dict, `raw` replaces its bytes,
        `also` writes other paths {study-relative: bytes} into the same commit."""
        run_git(self.repo, "reset", "-q", "--hard", self.parent)
        # the gate reads every reflog: this rig's own earlier worlds, a merge or a root commit re-adding the report, are no
        # part of the next one
        run_git(self.repo, "reflog", "expire", "--expire=now", "--all")
        doc = copy.deepcopy(self.frozen)
        if edit:
            edit(doc)
        data = raw if raw is not None else freeze.json_bytes(doc)
        for rel, body in {**self.outputs, "prereg.json": data, **(also or {})}.items():
            (self.study / rel).write_bytes(body)
        run_git(self.repo, "add", "-A")
        with tempfile.NamedTemporaryFile("w", suffix=".txt") as m:
            m.write(MESSAGE)
            m.flush()
            run_git(self.repo, "commit", "-q", "-F", m.name)
        return run_git(self.repo, "rev-parse", "HEAD")

    def check(self, mode="plan", driver=DRIVER, *more) -> list[str]:
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", "-c", driver, str(self.study), mode, *more],
                             capture_output=True, text=True, env=self.env(), cwd=str(self.repo))
        found = re.findall(r"^PROBLEMS (.*)$", got.stdout, re.M)
        if not found:
            raise AssertionError(f"the check did not finish: {got.stdout[-1500:]}{got.stderr[-1500:]}")
        return json.loads(found[-1])

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        if args[0] == "check_results.py":     # the real main; the one gate this scratch's missing walks cannot hold is named
            launcher = ("import sys; sys.path.insert(0, sys.argv[1]); import freeze, check_results; "
                        "freeze.unrecorded_shapes_problem = lambda draft: None; "
                        "raise SystemExit(check_results.main(sys.argv[2:]))")
            return subprocess.run([sys.executable, "-B", "-W", "ignore", "-c", launcher, str(self.study), *args[1:]],
                                  capture_output=True, text=True, env=self.env(), cwd=str(self.repo))
        return subprocess.run([sys.executable, "-B", "-W", "ignore", str(self.study / args[0]), *args[1:]],
                              capture_output=True, text=True, env=self.env(), cwd=str(self.repo))


WORLD = None
TMP = None


def setUpModule():
    global WORLD, TMP
    TMP = tempfile.TemporaryDirectory(prefix="fold11-")
    mutate = None
    if SELECTED is not None:
        _, target, old, new = mutants()[SELECTED]

        def mutate(root: Path) -> None:
            text = (root / f"{target}.py").read_text()
            assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
            (root / f"{target}.py").write_text(text.replace(old, new))
    WORLD = World(Path(TMP.name), mutate)


def tearDownModule():
    TMP.cleanup()


def named(problems, needle, clause) -> str:
    """The one problem that names `needle`, or an assertion carrying the clause."""
    hits = [p for p in problems if needle in p]
    if not hits:
        raise AssertionError(f"{clause}: no problem names {needle!r}: {problems}")
    return hits[0]


class Base(unittest.TestCase):
    world: World

    def setUp(self):
        self.world = WORLD
        self.world.commit_freeze()


class DClean(Base):
    def test_the_clean_freeze_has_no_problem(self):
        self.assertEqual(self.world.check(), [], "D.clean")
        self.assertEqual(self.world.frozen.get("pre_freeze_review_file"), self.world.report, "D.clean: the writer's own")

    def test_the_clean_freeze_passes_unstubbed(self):
        self.assertEqual(self.world.check("plan", DRIVER, "unstubbed"), [], "D.clean")


class DDraft(Base):
    def test_a_recorded_digest_that_is_not_the_drafts_is_refused(self):
        def edit(doc):
            doc["draft_sha256_at_freeze"] = "0" * 64
        self.world.commit_freeze(edit)
        named(self.world.check(), "draft_sha256_at_freeze is not the sha256", "D.draft")

    def test_a_draft_edited_in_the_freeze_commit_with_its_digest_is_refused(self):
        draft = json.loads((self.world.study / "prereg-draft.json").read_text())
        draft["views"] = "edited"
        body = freeze.json_bytes(draft)

        def edit(doc):
            doc["draft_sha256_at_freeze"] = hashlib.sha256(body).hexdigest()
            doc["views"] = "edited"
        self.world.commit_freeze(edit, also={"prereg-draft.json": body})
        named(self.world.check(), "prereg-draft.json", "D.touch")

    def test_the_gates_on_the_draft_are_read(self):
        # the freeze's own two gates on the draft, on bytes committed in the freeze commit (D.touch names that too)
        draft = json.loads((self.world.study / "prereg-draft.json").read_text())
        for key, value, needle in ((freeze.ORDER_FUNCTION_HASH_KEY, "0" * 64, "order function"),
                                   ("holdout_salted_digests", {}, "before the freeze")):
            with self.subTest(key=key):
                body = freeze.json_bytes({**draft, key: value})

                def edit(doc, b=body):
                    doc["draft_sha256_at_freeze"] = hashlib.sha256(b).hexdigest()
                self.world.commit_freeze(edit, also={"prereg-draft.json": body})
                named(self.world.check(), needle, "D.gates")


class DKeys(Base):
    def test_a_design_key_edited_at_the_freeze_is_refused(self):
        def edit(doc):
            doc["views"] = "edited"
        self.world.commit_freeze(edit)
        self.assertIn("views", named(self.world.check(), "outside the freeze", "D.keys"), "D.keys")

    def test_every_key_the_freeze_writes_must_be_present(self):
        for key in ("frozen_at", "pre_freeze_review_commit", "take_order_witness", "rehearsed_study_tree_sha256",
                    "holdout_salted_digests", "pinned_files"):
            with self.subTest(key=key):
                def edit(doc, k=key):
                    del doc[k]
                self.world.commit_freeze(edit)
                self.assertIn(key, named(self.world.check(), "written keys are absent", "D.keys"), "D.keys")


class DLimit(Base):
    def test_the_limit_stripped_or_softened_at_the_freeze_is_refused(self):
        for value in (None, "", "softened"):
            with self.subTest(value=value):
                def edit(doc, v=value):
                    if v is None:
                        del doc["published_tip_residual"]
                    else:
                        doc["published_tip_residual"] = v
                self.world.commit_freeze(edit)
                named(self.world.check(), "is not freeze.PUBLISHED_TIP_LIMIT", "D.limit")

    def test_check_publication_holds_the_limit(self):
        # fold 10's review, m1: the real check_publication; only what surrounds the hold stands in (no takes here)
        driver = """
import json, sys
from unittest import mock
sys.path.insert(0, sys.argv[1])
import check_results as cr, result, run_builders, freeze
pipe = mock.Mock(); pipe.produce.return_value = {"records": []}
with mock.patch.object(cr, "pipeline", return_value=pipe), mock.patch.object(result, "from_records", return_value={}), \\
        mock.patch.object(result, "render", return_value="page"), mock.patch.object(cr, "original_values_problems", return_value=[]), \\
        mock.patch.object(run_builders, "order_problems", side_effect=lambda *a: []), mock.patch.object(cr.stats, "check_records"):
    out = {}
    for name, pre in (("held", {"published_tip_residual": freeze.PUBLISHED_TIP_LIMIT}), ("absent", {}),
                      ("soft", {"published_tip_residual": "softened"})):
        out[name] = cr.check_publication([], [], [], pre, "page", None)
print("PROBLEMS " + json.dumps(out))
"""
        got = self.world.check("plan", driver)
        self.assertEqual(got["held"], [], "D.publication")
        named(got["absent"], "published_tip_residual", "D.publication")
        named(got["soft"], "published_tip_residual", "D.publication")


class DReview(Base):
    def earlier_report(self) -> str:
        return study.rel(study.REVIEW_DIR, f"prefreeze-{self.world.earlier}.md")

    def test_a_recorded_digest_that_is_not_the_reports_is_refused(self):
        def edit(doc):
            doc["pre_freeze_review_sha256"] = "0" * 64
        self.world.commit_freeze(edit)
        named(self.world.check(), "pre_freeze_review_sha256 is not the sha256", "D.review")

    def test_the_named_report_must_exist_at_the_parent(self):
        def edit(doc):
            doc["pre_freeze_review_file"] = study.rel(study.REVIEW_DIR, "prefreeze-999.md")
        self.world.commit_freeze(edit)
        named(self.world.check(), "not committed at the freeze's parent", "D.review")

    def test_another_report_named_with_its_own_digest_is_refused(self):
        rel = self.earlier_report()
        body = (self.world.repo / rel).read_bytes()

        def edit(doc):
            doc["pre_freeze_review_file"] = rel
            doc["pre_freeze_review_sha256"] = hashlib.sha256(body).hexdigest()
        self.world.commit_freeze(edit)
        named(self.world.check(), "names another report", "D.review")

    def test_a_named_report_that_refused_is_refused_by_its_ruling(self):
        # review_file_problems stood in as clean, so the ruling clause is read alone. The report is the latest that refused,
        # by its ruling, never by its number: a head that freezes has an approving round as its latest
        reports = sorted((self.world.study / study.REVIEW_DIR).glob("prefreeze-[0-9]*.md"), key=lambda f: f.stat().st_size)
        refused = [f for f in reports if re.fullmatch(r"prefreeze-\d+\.md", f.name)
                   and freeze.read_ruling(f.read_text()) == "DO NOT FREEZE"]
        self.assertTrue(refused, "the fixture: a round that refused")
        rel = study.rel(study.REVIEW_DIR, refused[-1].name)
        body = refused[-1].read_bytes()

        def edit(doc):
            doc["pre_freeze_review_file"] = rel
            doc["pre_freeze_review_sha256"] = hashlib.sha256(body).hexdigest()
        self.world.commit_freeze(edit)
        driver = DRIVER.replace("import check_results as cr, freeze\n",
                                "import check_results as cr, freeze\n"
                                f"freeze.review_file_problems = lambda c: ([], {rel!r})\n")
        named(self.world.check("plan", driver), "as freeze approval", "D.ruling")

    def test_a_seed_commit_the_gate_refuses_is_refused(self):
        def edit(doc):
            doc["pre_freeze_review_commit"] = self.world.base
        self.world.commit_freeze(edit)
        named(self.world.check(), "review_file_problems", "D.gate")

    def test_the_gate_reads_the_parent_not_head(self):
        # a commit after the freeze changes a pinned path, which launch_binding_problem would read at HEAD
        self.world.commit_freeze()
        (self.world.study / "study.py").write_bytes((self.world.study / "study.py").read_bytes() + b"\n# later\n")
        self.world.commit("a later commit")
        self.assertEqual([p for p in self.world.check() if "review_file_problems" in p], [], "D.asof")


class DParent(Base):
    def test_an_edited_parent_is_refused_not_read_as_another_copy(self):
        def edit(doc):
            doc["frozen_at_commit_parent"] = self.world.base
        self.world.commit_freeze(edit)
        named(self.world.check(), "is not the freeze commit's parent", "D.parent")

    def test_a_merge_freeze_commit_is_refused(self):
        self.world.commit_freeze()
        head = run_git(self.world.repo, "rev-parse", "HEAD")
        side = run_git(self.world.repo, "commit-tree", f"{self.world.base}^{{tree}}", "-p", self.world.base, "-m", "side")
        merged = run_git(self.world.repo, "commit-tree", f"{head}^{{tree}}", "-p", self.world.parent, "-p", side,
                         "-m", "a merge carrying the frozen file")
        run_git(self.world.repo, "reset", "-q", "--hard", merged)
        named(self.world.check(), "has 2 parents", "D.parent")


class DTouch(Base):
    def test_a_freeze_commit_carrying_anything_else_is_refused(self):
        self.world.commit_freeze(also={"study.py": (self.world.study / "study.py").read_bytes() + b"\n# edited\n"})
        self.assertIn("study.py", named(self.world.check(), "changes other paths", "D.touch"), "D.touch")

    def test_an_edited_fragment_is_refused(self):
        self.world.commit_freeze(also={"COPIED.d/freeze.json": b'{"lane": "freeze", "files": []}\n'})
        named(self.world.check(), "COPIED.d/freeze.json is not what freeze.py writes", "D.touch")


class DBytes(Base):
    def assert_refused(self, edit, needle):
        self.world.commit_freeze(edit)
        self.assertIn(needle, named(self.world.check(), "byte for byte", "D.bytes"), "D.bytes")

    def test_a_pin_dropped_is_refused(self):
        def edit(doc):
            doc["pinned_files"] = doc["pinned_files"][1:]
        self.assert_refused(edit, "pinned_files")

    def test_a_pins_hash_removed_is_refused(self):
        # frozen_commit_problems skips a pin with no git_blob_sha, and check_pins one with no sha256
        def edit(doc):
            del doc["pinned_files"][0]["git_blob_sha"]
        self.assert_refused(edit, "pinned_files")

    def test_a_task_edit_the_allowlist_passes_is_refused(self):
        # tasks[].grader is in FREEZE_FILLED_INSIDE and nothing fills it, so keys_outside_the_freeze passes the edit
        def edit(doc):
            doc["tasks"][0]["grader"] = {"module": "graders/other.py"}
        self.assertEqual(freeze.keys_outside_the_freeze(json.loads(
            (self.world.study / "prereg-draft.json").read_text()), {**self.world.frozen, "tasks": [
                {**self.world.frozen["tasks"][0], "grader": {"module": "graders/other.py"}}, *self.world.frozen["tasks"][1:]]}),
            [], "the fixture: the allowlist does pass it")
        self.assert_refused(edit, "tasks")

    def test_a_task_dropped_is_refused(self):
        # changed_keys zips the two lists, so a dropped task names no key
        def edit(doc):
            doc["tasks"] = doc["tasks"][:-1]
        self.assert_refused(edit, "tasks")

    def test_a_key_nothing_writes_is_refused(self):
        def edit(doc):
            doc["nulls_at_freeze"] = {"anything": 1}
        self.assert_refused(edit, "nulls_at_freeze")

    def test_status_and_tree_edits_are_refused(self):
        for key, value in (("status", "DRAFT"), ("rehearsed_study_tree_sha256", "0" * 64)):
            with self.subTest(key=key):
                def edit(doc, k=key, v=value):
                    doc[k] = v
                self.assert_refused(edit, key)

    def test_the_same_keys_in_other_bytes_are_refused(self):
        raw = json.dumps(self.world.frozen, indent=1, ensure_ascii=False).encode() + b"\n"
        self.world.commit_freeze(raw=raw)
        named(self.world.check(), "byte for byte", "D.bytes")


class DHoldout(Base):
    def test_digests_the_validator_refuses_are_refused(self):
        def edit(doc):
            first = sorted(doc["holdout_salted_digests"])[0]
            doc["holdout_salted_digests"][first] = doc["holdout_salted_digests"][first][:-1]
        self.world.commit_freeze(edit)
        named(self.world.check(), "holdout digests", "D.holdout")

    def test_a_count_that_is_not_theirs_is_refused(self):
        def edit(doc):
            doc["holdout_wordings_per_task_version"] = 99
        self.world.commit_freeze(edit)
        named(self.world.check(), "holdout digests", "D.holdout")


class DReal(Base):
    """The check without --rehearsal-plan. A disposable freeze's own placeholders are refused there by name, so these read
    that those stay refused, and that each real-road field is read."""

    def green_record(self) -> dict:
        lines = [hashlib.sha256((self.world.study / "prereg-draft.json").read_bytes()).hexdigest(),
                 freeze.REHEARSAL_TREE_PREFIX + self.world.frozen["rehearsed_study_tree_sha256"]]
        for name in freeze.rehearsal_required_steps():
            lines += [f"[0] {name}", "    " + (LIVE_BOX_PASS if name == freeze_rehearsal.LIVE_BOX_STEP else "ok")]
        text = "\n".join(lines + [freeze.REHEARSAL_LAST_LINE]) + "\n"
        return {"name": "freeze-rehearsal-1.txt", "sha256": hashlib.sha256(text.encode()).hexdigest(), "text": text}

    def real_frozen(self, doc):
        """`doc` as a real freeze writes it: a non-synthetic reading, its seed and order, a green record, and the witness
        the freeze's own code derives from one push of the parent, stamped well before the round."""
        import order_beacon
        draft = json.loads((self.world.study / "prereg-draft.json").read_text())
        signature = "ab" * 48
        reading = dict(doc["take_order_beacon_reading"], signature=signature,
                       randomness=hashlib.sha256(bytes.fromhex(signature)).hexdigest())
        seed = order_beacon.seed(reading)
        doc.update(take_order_beacon_reading=reading, take_order_seed=seed, take_order=freeze.planned_order(draft, seed),
                   rehearsal_record=self.green_record(),
                   holdout_salted_digests={t["id"]: [hashlib.sha256(f"stand-in-{t['id']}-{i}".encode()).hexdigest()
                                                     for i in range(2)] for t in draft["tasks"]})
        registered = {"repo": order_beacon.WITNESS_REPO, "host": freeze.WITNESS_HOST}
        for name in ("registering", "draft"):
            registered[f"{name}_commit"] = self.world.base
            registered[f"{name}_push"] = {"sha": self.world.parent, "stamp": 1000000000}
        doc["take_order_witness"] = registered

    def no_swaps(self) -> str:
        # the scratch's one-commit history holds no registration or swap history, so those two reads stand in; the real
        # line's are driven on a scratch clone of the real history (the fold's report)
        return DRIVER.replace("import check_results as cr, freeze\n", "import check_results as cr, freeze\n"
                              "freeze.supersession_swaps = lambda history: []\n"
                              f"freeze.registering_commit = lambda round_no: {self.world.base!r}\n")

    def test_the_real_shape_passes_and_an_edited_witness_does_not(self):
        self.world.commit_freeze(self.real_frozen)
        self.assertEqual(self.world.check("real", self.no_swaps()), [], "D.real.witness")

        def edited(doc):
            self.real_frozen(doc)
            doc["take_order_witness"]["repo"] = "someone/else"
        self.world.commit_freeze(edited)
        named(self.world.check("real", self.no_swaps()), "take_order_witness", "D.real.witness")

    def test_a_placeholder_witness_is_refused(self):
        record = self.green_record()

        def edit(doc):
            doc["rehearsal_record"] = record
        self.world.commit_freeze(edit)
        named(self.world.check("real"), "take_order_witness", "D.real.witness")

    def test_a_witness_the_freeze_would_not_derive_is_refused(self):
        record = self.green_record()

        def edit(doc):
            doc["rehearsal_record"] = record
            doc["take_order_witness"] = {"repo": "someone/else", "host": "github.com"}
        self.world.commit_freeze(edit)
        named(self.world.check("real"), "take_order_witness", "D.real.witness")

    def test_a_synthetic_reading_is_refused(self):
        record = self.green_record()

        def edit(doc):
            doc["rehearsal_record"] = record
        self.world.commit_freeze(edit)
        named(self.world.check("real"), "beacon reading is the rehearsal's synthetic", "D.real.reading")

    def test_a_record_whose_digest_is_not_its_texts_is_refused(self):
        record = dict(self.green_record(), sha256="0" * 64)

        def edit(doc):
            doc["rehearsal_record"] = record
        self.world.commit_freeze(edit)
        named(self.world.check("real"), "rehearsal record's sha256", "D.real.record")

    def test_a_root_freeze_commit_is_refused_on_the_real_road_only(self):
        tree = run_git(self.world.repo, "rev-parse", "HEAD^{tree}")
        root = run_git(self.world.repo, "commit-tree", tree, "-m", "a copy with no history")
        run_git(self.world.repo, "reset", "-q", "--hard", root)
        named(self.world.check("real"), "has no parent", "D.real.root")
        self.assertEqual([p for p in self.world.check("plan") if "has no parent" in p], [], "D.real.root")


class DNetwork(Base):
    DRIVER = """
import json, sys
from unittest import mock
sys.path.insert(0, sys.argv[1])
import check_results as cr, order_beacon
frozen, _ = cr.frozen_bytes()
reading = frozen["take_order_beacon_reading"]
good = [(100, "a" * 40), (200, "b" * 40)]
frozen_witness = {"repo": "r", "host": "github.com", "registering_commit": "x", "registering_push": {"sha": "a" * 40, "stamp": 100},
                  "draft_commit": "y", "draft_push": {"sha": "b" * 40, "stamp": 200}}
out = {}
def run(pushes, answer, witness=frozen_witness):
    doc = dict(frozen, take_order_witness=witness)
    with mock.patch.object(cr, "frozen_bytes", return_value=(doc, "")), mock.patch.object(order_beacon, "read_relays", side_effect=answer):
        return cr.frozen_network_problems(pushes)
out["clean"] = run(good, lambda r: reading)
out["push_missing"] = run(good[:1], lambda r: reading)
out["stamp_moved"] = run([(100, "a" * 40), (201, "b" * 40)], lambda r: reading)
out["reading_forged"] = run(good, lambda r: dict(reading, signature="00", randomness="11"))
def refuse(r):
    raise order_beacon.BeaconRefused("a relay cannot be read")
out["relay_down"] = run(good, refuse)
out["not_rehearsed"] = run(good, lambda r: reading, witness="not witnessed")
print("PROBLEMS " + json.dumps(out))
"""

    def test_the_network_door_holds_the_witness_and_the_reading(self):
        got = self.world.check("plan", self.DRIVER)
        self.assertEqual(got["clean"], [], "D.network")
        named(got["push_missing"], "push record", "D.network")
        named(got["stamp_moved"], "push record", "D.network")
        named(got["reading_forged"], "the relays", "D.network")
        named(got["relay_down"], "cannot be read", "D.network")
        named(got["not_rehearsed"], "take_order_witness", "D.network")

    def test_witness_main_reads_the_door(self):
        driver = """
import json, sys
from unittest import mock
sys.path.insert(0, sys.argv[1])
import check_results as cr, freeze
with mock.patch.object(freeze, "push_records", return_value=[]), mock.patch.object(cr, "take_ledger_witness", return_value=([], [], [])), \\
        mock.patch.object(cr, "frozen_network_problems", return_value=["the door was read"]) as door:
    code = cr.witness_main()
print("PROBLEMS " + json.dumps([code, door.call_count]))
"""
        self.assertEqual(self.world.check("plan", driver), [1, 1], "D.network")


class DShapes(Base):
    def test_the_recheck_reads_the_shapes_gate(self):
        driver = DRIVER.replace("freeze.unrecorded_shapes_problem = lambda draft: None",
                                "freeze.unrecorded_shapes_problem = lambda draft: 'the shapes stand-in refuses'")
        named(self.world.check("plan", driver), "the shapes stand-in refuses", "D.shapes")

    def test_the_gate_holds_on_this_tree(self):
        # the real gate on this checkout's real walks; in a frozen rehearsal clone this reads the frozen state too
        code = ("import json, sys; sys.path.insert(0, sys.argv[1]); import freeze; "
                "print('SHAPES', freeze.unrecorded_shapes_problem(json.load(open(freeze.DRAFT))))")
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", "-c", code, str(HERE)], capture_output=True, text=True)
        self.assertIn("SHAPES None", got.stdout, f"D.shapes: {got.stdout[-800:]}{got.stderr[-800:]}")


class DPy39(Base):
    def test_the_check_needs_no_filter_argument(self):
        # The gate review's M2: freeze_as_of does not reach tar's extraction. This is all it shows. It runs on sys.executable
        # with the shapes gate stood in, and on 3.9 that gate's import of check_take fails closed: 3.12 is the interpreter.
        driver = DRIVER.replace("import check_results as cr, freeze\n", "import tarfile\n"
                                "tarfile.TarFile.extractall = lambda self, path='.', members=None, *, numeric_owner=False: None\n"
                                "import check_results as cr, freeze\n")
        try:
            got = self.world.check("plan", driver)
        except AssertionError as exc:
            raise AssertionError(f"D.py39: {exc}") from None
        self.assertEqual(got, [], "D.py39")


class DRounds(Base):
    def kit(self, tmp: str) -> Path:
        folder = Path(tmp) / "kit"
        folder.mkdir()
        shutil.copyfile(self.world.study / "prereg-draft.json", folder / "prereg.json")
        (folder / "COMMIT").write_text(run_git(self.world.repo, "rev-parse", "HEAD") + "\n")
        return folder

    def test_a_prefreeze_row_is_refused_once_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = self.world.cli(f"{study.REVIEW_DIR}/rounds.py", "--add", "--kind", "prefreeze", "--folder", str(self.kit(tmp)))
        self.assertEqual(got.returncode, 1, f"D.rounds: {got.stdout[-500:]}")
        self.assertIn("frozen", got.stdout, "D.rounds")
        self.assertEqual(run_git(self.world.repo, "status", "--porcelain"), "", "D.rounds: a refusal writes nothing")

    def test_a_verify_row_is_not_refused_for_the_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = self.world.cli(f"{study.REVIEW_DIR}/rounds.py", "--add", "--kind", "verify", "--folder", str(self.kit(tmp)))
        self.assertNotIn("is frozen", got.stdout, "D.rounds")
        run_git(self.world.repo, "reset", "-q", "--hard")


class DRoad(Base):
    """Pre-freeze review 8's fold, the gate review's m6: the road after a DO FREEZE report, on the real pinned files."""

    TOOL = f"{study.REVIEW_DIR}/claim_review.py"

    def walk_the_road(self):
        run_git(self.world.repo, "reset", "-q", "--hard", self.world.review)     # commit_review.py's commit is HEAD
        got = self.world.cli(self.TOOL, str(self.world.n))
        self.assertEqual(got.returncode, 0, f"D.road: {got.stdout[-800:]}{got.stderr[-800:]}")

    def binding(self):
        driver = ("import json, sys\nsys.path.insert(0, sys.argv[1])\nimport freeze\n"
                  f"print('PROBLEMS ' + json.dumps(freeze.review_file_problems({self.world.review!r})))\n")
        return self.world.check("plan", driver)

    def lints(self):
        return (self.world.cli("lint_language.py", str(self.world.study)), self.world.cli("lint_pooling.py", str(self.world.study)))

    def test_the_report_trips_both_lints_when_named(self):
        # the fixture is honest: these words do fail, so the rule below is what lets them through
        self.walk_the_road()
        for tool in ("lint_language.py", "lint_pooling.py"):
            got = self.world.cli(tool, str(self.world.repo / self.world.report))
            self.assertEqual(got.returncode, 1, f"D.road: {tool} passes the words: {got.stdout[-400:]}")

    def test_the_road_lands_with_no_edit_to_a_pinned_file_but_its_claims(self):
        self.walk_the_road()
        changed = set(run_git(self.world.repo, "diff", "--name-only", self.world.base, "HEAD").splitlines())
        want = {self.world.report, self.world.report[:-3] + "-blindness.txt", study.rel(study.REVIEW_DIR, "rounds.json"),
                study.rel(FRAGMENT)}
        self.assertEqual(changed, want, "D.road")
        for got in self.lints():
            self.assertEqual(got.returncode, 0, f"D.road: {got.stdout[-800:]}{got.stderr[-400:]}")
            self.assertIn("not scanned", got.stdout, "D.road: an exemption is named, never silent")
        self.assertEqual(self.binding(), [[], self.world.report], "D.road: the launch binding")

    def test_an_edited_report_is_scanned(self):
        self.walk_the_road()
        report = self.world.repo / self.world.report
        report.write_text(report.read_text() + "\nAn added sentence on pooling.\n")
        self.assertEqual(self.lints()[1].returncode, 1, "D.road.digest")

    def test_a_report_with_no_stated_digest_is_scanned(self):
        self.walk_the_road()
        blind = self.world.study / study.REVIEW_DIR / f"prefreeze-{self.world.n}-blindness.txt"
        blind.write_text(blind.read_text().split("report sha256")[0])
        self.assertEqual(self.lints()[1].returncode, 1, "D.road.digest")

    def test_the_rule_starts_at_round_nine_and_reads_only_review_reports(self):
        # the scratch's own lint, so a mutant of it is what runs
        driver = """
import hashlib, json, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import freeze, lint_language as ll
out = {"line": ll.REPORT_DIGEST_LINE == freeze._blindness().REPORT_DIGEST}
with tempfile.TemporaryDirectory() as tmp:
    kit = Path(tmp) / "review_kit"
    kit.mkdir()
    for name in ("prefreeze-8", "prefreeze-9", "prefreeze-12", "prefreeze-09"):
        (kit / f"{name}.md").write_bytes(b"words\\n")
        (kit / f"{name}-blindness.txt").write_text(ll.REPORT_DIGEST_LINE + hashlib.sha256(b"words\\n").hexdigest() + "\\n")
        out[name] = ll.is_bound_review_report(kit / f"{name}.md")
    other = Path(tmp) / "prefreeze-9.md"
    other.write_bytes(b"words\\n")
    out["elsewhere"] = ll.is_bound_review_report(other)
print("PROBLEMS " + json.dumps(out))
"""
        self.assertEqual(self.world.check("plan", driver), {"line": True, "prefreeze-8": False, "prefreeze-9": True, "prefreeze-12": True,
                                                            "prefreeze-09": False, "elsewhere": False}, "D.road.floor")

    def test_a_pinned_edit_after_the_review_breaks_the_binding(self):
        # why the cure cannot be made after the report: the road's whole reason
        self.walk_the_road()
        f = self.world.study / "lint_pooling.py"
        f.write_bytes(f.read_bytes() + b"\n# a late cure\n")
        self.world.commit("a late cure")
        bad = self.binding()[0]
        self.assertTrue(any("lint_pooling.py" in p for p in bad), f"D.road.pinned: {bad}")

    def test_the_claims_tool_refuses_anywhere_else(self):
        # HEAD lands nothing and nothing is claimed yet, so only the landing check can refuse this
        run_git(self.world.repo, "reset", "-q", "--hard", self.world.review)
        head = self.world.commit("a commit between the report and its claims")
        got = self.world.cli(self.TOOL, str(self.world.n))
        self.assertEqual(got.returncode, 1, f"D.road.tool: {got.stdout[-400:]}")
        self.assertIn("does not land exactly", got.stdout, "D.road.tool")
        self.assertEqual(run_git(self.world.repo, "rev-parse", "HEAD"), head, "D.road.tool")


class DPost(Base):
    """The gate review 2's m1, and the road after the freeze."""

    PINS = ("import json, sys\nsys.path.insert(0, sys.argv[1])\nimport check_results as cr\n"
            "print('PROBLEMS ' + json.dumps(cr.check_pins()))\n")

    def study_git(self, message="a post-freeze commit") -> str:
        return self.world.commit(message)

    def add_verify(self, tmp, words=REPORT_WORDS) -> int:
        kit = Path(tempfile.mkdtemp(dir=tmp))
        shutil.copyfile(self.world.study / "prereg-draft.json", kit / "prereg.json")
        (kit / "COMMIT").write_text(run_git(self.world.repo, "rev-parse", "HEAD") + "\n")
        got = self.world.cli(f"{study.REVIEW_DIR}/rounds.py", "--add", "--kind", "verify", "--folder", str(kit))
        self.assertEqual(got.returncode, 0, f"D.post: {got.stdout[-500:]}")
        row_commit = self.study_git("a verify row")
        n = json.loads(self.world.rounds.read_text())["rows"][-1]["n"]
        folder = self.world.study / study.VERIFY_DIR
        folder.mkdir(exist_ok=True)
        (folder / f"verify-{n}.md").write_text(f"# a synthetic verifier\n\n{words}\n")
        (folder / f"verify-{n}-blindness.txt").write_text(f"session id: {takes.session_id_for(row_commit)}\n")
        self.study_git("a verifier's report")
        return n

    def pins(self):
        return self.world.check("plan", self.PINS)

    def edit_register(self, change):
        doc = json.loads(self.world.rounds.read_text())
        change(doc)
        self.world.rounds.write_text(json.dumps(doc, indent=2) + "\n")
        self.study_git("the register edited")

    def test_a_valid_verify_row_holds_the_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.add_verify(tmp)
            self.assertEqual(self.pins(), [], "D.post.valid")
            self.add_verify(tmp)
            self.assertEqual(self.pins(), [], "D.post.valid")

    def test_a_changed_or_removed_row_refuses(self):
        def changed(doc):
            doc["rows"][0]["launch_commit"] = "0" * 40

        def removed(doc):
            del doc["rows"][0]
        for name, change in (("changed", changed), ("removed", removed)):
            with self.subTest(name=name):
                self.world.commit_freeze()
                self.edit_register(change)
                self.assertTrue(self.pins(), f"D.post.frozen-rows: {name}")

    def test_the_rows_of_the_freeze_must_survive_a_verify_row(self):
        # the prefix read, on its own: a valid verify row appended beside an edit of a row the freeze held
        with tempfile.TemporaryDirectory() as tmp:
            self.add_verify(tmp)

            def changed(doc):
                doc["rows"][0]["voids"] = 99
            self.edit_register(changed)
            self.assertTrue(self.pins(), "D.post.frozen-rows")

    def test_a_later_prefreeze_row_refuses(self):
        head = run_git(self.world.repo, "rev-parse", "HEAD")

        def later(doc):
            doc["rows"].append({"n": self.world.n + 1, "kind": "prefreeze", "launch_commit": head, "voids": None,
                                "prompt_sha256": "a" * 64, "input_sha256": "b" * 64})
        self.edit_register(later)
        self.assertTrue(self.pins(), "D.post.kind")

    def verify_row(self, **fields):
        row = {"n": 1, "kind": "verify", "launch_commit": run_git(self.world.repo, "rev-parse", "HEAD"), "voids": None,
               "prompt_sha256": "a" * 64, "input_sha256": "b" * 64}
        row.update(fields)
        return row

    def test_an_invalid_verify_row_refuses(self):
        cases = {"D.post.number": {"n": 7}, "D.post.launch": {"launch_commit": "0" * 40},
                 "D.post.launch-before": {"launch_commit": self.world.parent}, "D.post.digests": {"prompt_sha256": "short"}}
        for clause, fields in cases.items():
            with self.subTest(clause=clause):
                self.world.commit_freeze()
                row = self.verify_row(**fields)
                self.edit_register(lambda doc, r=row: doc["rows"].append(r))
                self.assertTrue(self.pins(), clause)

    def test_a_top_level_change_refuses(self):
        row = self.verify_row()

        def change(doc):
            doc["rows"].append(row)
            doc["another"] = 1
        self.edit_register(change)
        self.assertTrue(self.pins(), "D.post.top")

    def test_every_other_pinned_file_still_refuses(self):
        for rel in (FRAGMENT, "language-allowlist.json", "rehearsals/register.json", "owner_decisions.jsonl", "lint_pooling.py"):
            with self.subTest(rel=rel):
                self.world.commit_freeze()
                f = self.world.study / rel
                f.write_bytes(f.read_bytes() + b"\n")
                self.study_git("a pinned file edited")
                self.assertTrue(any(rel in p for p in self.pins()), f"D.post.others: {rel}")

    def test_the_cli_is_green_along_the_plans_road(self):
        cli = self.world.cli
        with tempfile.TemporaryDirectory() as tmp:
            row = Path(tmp) / "row.json"
            row.write_text(json.dumps(self.world.frozen["take_order"][0]))
            for command in (("takes.py", "--add", "--row", str(row), "--attempt", "1"), ("run.py", "--all"),
                            ("result.py", "--write")):
                got = cli(*command)
                self.assertEqual(got.returncode, 0, f"D.post.road: {command}: {got.stdout[-800:]}{got.stderr[-800:]}")
            self.study_git("a take's records and the page")
            for name in ("definitions.json", "labels.json"):      # Javier's files; no pin names these
                (self.world.study / "labelling" / name).write_text("{}\n")
            (self.world.study / "labelling" / "AGREEMENT.md").write_text("# a synthetic table\n")
            self.study_git("the labels and the agreement table")

            def ledger(when):
                got = cli("check_results.py", "--ledger", "--rehearsal-plan")
                self.assertEqual(got.returncode, 0, f"D.post.road: {when}: {got.stdout[-1200:]}{got.stderr[-400:]}")
            ledger("after the labels")
            self.add_verify(tmp)
            ledger("after one verify round")
            self.add_verify(tmp)
            ledger("after two")
            fragment = self.world.study / "COPIED.d" / "verify-records.json"
            fragment.write_text(json.dumps({"lane": "verify-records", "files": []}, indent=2) + "\n")
            self.study_git("a new copy-record fragment")
            ledger("after a new fragment")
            for command in (("result.py", "--check"), ("completeness.py", "--check"),
                            ("lint_language.py", str(self.world.study)), ("lint_pooling.py", str(self.world.study))):
                got = cli(*command)
                self.assertEqual(got.returncode, 0, f"D.post.road: {command}: {got.stdout[-900:]}{got.stderr[-400:]}")
            got = cli("check_results.py", "--regrade", "--rehearsal-plan")
            self.assertEqual(got.returncode, 0, f"D.post.regrade: {got.stdout[-500:]}{got.stderr[-300:]}")
            # The labelling frame and sample: a real frame needs graded takes of every design model, which this scratch has
            # not, and the page then refuses (result.py, by design). No pin names them, which is what is read here.
            for name in ("frame.json", "sample.json"):
                (self.world.study / "labelling" / name).write_text("[]\n")
            self.study_git("the frame and the sample")
            self.assertEqual(self.pins(), [], "D.post.road: the frame and the sample")


class DMain(Base):
    """fold 10's review, m5: the real CLI on a frozen file built by the real freeze."""

    def test_the_cli_passes_the_clean_state(self):
        got = self.world.cli("check_results.py", "--ledger", "--rehearsal-plan")
        self.assertEqual(got.returncode, 0, f"D.main: {got.stdout[-1500:]}{got.stderr[-500:]}")
        self.assertIn("no takes; frozen pins verified", got.stdout, "D.main")

    def test_the_cli_refuses_an_edited_state(self):
        def edit(doc):
            doc["views"] = "edited"
        self.world.commit_freeze(edit)
        got = self.world.cli("check_results.py", "--ledger", "--rehearsal-plan")
        self.assertEqual(got.returncode, 1, f"D.main: {got.stdout[-1500:]}")
        self.assertIn("outside the freeze", got.stdout, "D.main")

    def test_the_rehearsal_runtime_steps_run_on_the_real_shape(self):
        # the steps freeze_rehearsal runs after a green frozen state, with the row file it writes
        with tempfile.TemporaryDirectory() as tmp:
            row = Path(tmp) / "row.json"
            row.write_text(json.dumps(self.world.frozen["take_order"][0]))
            for command in (("takes.py", "--add", "--row", str(row), "--attempt", "1"), ("takes.py", "--session-id", "0"),
                            ("run.py", "--all"), ("result.py", "--write"),
                            ("check_results.py", "--ledger", "--rehearsal-plan"), ("completeness.py", "--check")):
                got = self.world.cli(*command)
                self.assertEqual(got.returncode, 0, f"D.main: {command}: {got.stdout[-1500:]}{got.stderr[-1500:]}")
        run_git(self.world.repo, "clean", "-fdqx")


def mutants() -> dict:
    """name -> (clause, module, anchor, replacement). Each anchor occurs once in the module's source."""
    cr = "check_results"
    return {
        "wired-off": ("D.main", cr, "    return problems + rehearsal + held + recheck\n", "    return problems + rehearsal + held\n"),
        "draft-digest": ("D.draft", cr, '    if hashlib.sha256(raw_draft).hexdigest() != frozen.get("draft_sha256_at_freeze"):\n', "    if False:\n"),
        "keys-outside": ("D.keys", cr, "        outside = freeze.keys_outside_the_freeze(draft, frozen)\n", "        outside = []\n"),
        "keys-present": ("D.keys", cr, "    if absent:\n", "    if False:\n"),
        "never-written": ("D.clean", cr, 'FREEZE_KEYS_NOT_WRITTEN = ("nulls_at_freeze",)\n', "FREEZE_KEYS_NOT_WRITTEN = ()\n"),
        "limit-at-freeze": ("D.limit", cr, "    out += tip_limit_problems(frozen)\n", ""),
        "limit-at-publication": ("D.publication", cr, "    problems += tip_limit_problems(pre)", "    problems += []"),
        "review-digest": ("D.review", cr, '        if review_sha != frozen.get("pre_freeze_review_sha256"):\n', "        if False:\n"),
        "review-absent": ("D.review", cr, "    if review is None:\n        out.append(f\"pre_freeze_review_file", "    if review is None:\n        str(f\"pre_freeze_review_file"),
        "ruling": ("D.ruling", cr, "        if ruling != freeze.DO_FREEZE:\n", "        if False:\n"),
        "gate": ("D.gate", cr, "        if bad:\n            out.append(\"review_file_problems", "        if False:\n            out.append(\"review_file_problems"),
        "gate-names": ("D.review", cr, "        elif named != review_file:\n", "        elif False:\n"),
        "gate-at-head": ("D.asof", cr, "    with freeze_as_of(parent) as fz:\n", "    with contextlib.nullcontext(freeze) as fz:\n"),
        "parent-edit": ("D.parent", cr, "    if want_parent != parent:\n", "    if False:\n"),
        "merge": ("D.parent", cr, "    if len(parents) != 1:\n", "    if False:\n"),
        "touch": ("D.touch", cr, "    if touched != want:\n", "    if False:\n"),
        "fragment": ("D.touch", cr, "    if committed_raw(commit, study.rel(FREEZE_OUTPUTS[2])) != freeze.json_bytes(freeze.output_fragment()):\n", "    if False:\n"),
        "bytes": ("D.bytes", cr, "        out += frozen_file_problems(frozen, draft, parent, commit, raw_draft, review_sha, fz)\n", ""),
        "draft-gates": ("D.gates", cr, "    out += [p for p in (freeze.draft_holdout_problem(draft), freeze.order_function_problem(draft)) if p]\n", ""),
        "holdout-validator": ("D.holdout", cr, "        count = build_draft.validate_digests(frozen.get(\"holdout_salted_digests\"), [t[\"id\"] for t in draft[\"tasks\"]])\n", "        count = frozen.get(\"holdout_wordings_per_task_version\")\n"),
        "holdout-count": ("D.holdout", cr, '        if count != frozen.get("holdout_wordings_per_task_version"):\n', "        if False:\n"),
        "witness-unread": ("D.real.witness", cr, "            out += witness_as_derived_problems(frozen, draft, fz)\n", "            pass\n"),
        "witness-compare": ("D.real.witness", cr, "    if again != witness:\n", "    if False:\n"),
        "reading-synthetic": ("D.real.reading", cr, '        if isinstance(reading, dict) and reading.get("signature") == freeze.SYNTHETIC_SIGNATURE:\n', "        if False:\n"),
        "record-digest": ("D.real.record", cr, '        if isinstance(text, str) and hashlib.sha256(text.encode("utf-8")).hexdigest() != record.get("sha256"):\n', "        if False:\n"),
        "root-passes": ("D.real.root", cr, "        return [] if rehearsal_plan else [f\"the freeze commit {commit[:12]} has no parent", "        return [] if True else [f\"the freeze commit {commit[:12]} has no parent"),
        "network-push": ("D.network", cr, '            if (push.get("stamp"), push.get("sha")) not in real:\n', "            if False:\n"),
        "network-reading": ("D.network", cr, '    if any(reading.get(k) != answer.get(k) for k in ("round", "randomness", "signature")):\n', "    if False:\n"),
        "shapes": ("D.shapes", cr, "    if shapes:\n", "    if False:\n"),
        "rounds-after-freeze": ("D.rounds", f"{study.REVIEW_DIR}/rounds", '    if kind == "prefreeze" and (STUDY_DIR / "prereg.json").is_file():\n', "    if False:\n"),
        "rounds-verify-too": ("D.rounds", f"{study.REVIEW_DIR}/rounds", '    if kind == "prefreeze" and (STUDY_DIR / "prereg.json").is_file():\n', '    if (STUDY_DIR / "prereg.json").is_file():\n'),
        "rule-off": ("D.road", "lint_language", "                        and not named_bound_report(f)\n", ""),
        "rule-any-bytes": ("D.road.digest", "lint_language", 'return len(stated) == 1 and stated[0] == hashlib.sha256(path.read_bytes()).hexdigest()', "return len(stated) == 1"),
        "rule-no-digest": ("D.road.digest", "lint_language", 'return len(stated) == 1 and stated[0] == hashlib.sha256(path.read_bytes()).hexdigest()', "return True"),
        "rule-floor": ("D.road.floor", "lint_language", "BOUND_RULE_FROM_ROUND = 9\n", "BOUND_RULE_FROM_ROUND = 1\n"),
        "tool-anywhere": ("D.road.tool", f"{study.REVIEW_DIR}/claim_review", "    if landed != want:\n", "    if False:\n"),
        "register-frozen": ("D.post.valid", cr, "                elif not pin_holds(path, node, raw):\n", '                elif hashlib.sha256(raw).hexdigest() != node["sha256"]:\n'),
        "register-prefix": ("D.post.frozen-rows", cr, "    if not isinstance(new, list) or new[:len(old)] != old:\n", "    if not isinstance(new, list):\n"),
        "register-kind": ("D.post.kind", cr, '        if not isinstance(row, dict) or row.get("kind") != "verify":\n', "        if not isinstance(row, dict):\n"),
        "register-number": ("D.post.number", cr, "        if row.get(\"n\") != last or type(row.get(\"n\")) is not int:\n", "        if False:\n"),
        "register-digests": ("D.post.digests", cr, '        if not all(isinstance(row.get(k), str) and HEX64.fullmatch(row[k]) for k in ("prompt_sha256", "input_sha256")):\n', "        if False:\n"),
        "register-launch": ("D.post.launch", cr, '                and git("merge-base", "--is-ancestor", commit, launch)[0] == 0\n                and git("merge-base", "--is-ancestor", launch, "HEAD")[0] == 0):\n', "                ):\n"),
        "register-top": ("D.post.top", cr, '    if {k: v for k, v in before.items() if k != "rows"} != {k: v for k, v in after.items() if k != "rows"}:\n', "    if False:\n"),
        "regrade-flag": ("D.post.regrade", cr, '    parser.add_argument("--regrade", action="store_true",', '    parser.add_argument("--regrade-off", action="store_true",'),
        "verifier-report-scanned": ("D.post.road", "lint_language", '    re.compile(r"^verify-[1-9]\\d*\\.md$"),', '    re.compile(r"^verify-never$"),'),
        "freeze-outputs-scanned": ("D.post.road", "lint_language", "                        and not is_freeze_output(f)\n", ""),
        "rule-leading-zero": ("D.road.floor", "lint_language", 'r"prefreeze-([1-9]\\d*)\\.md"', 'r"prefreeze-(\\d+)\\.md"'),
        "network-door": ("D.network", cr, "    return problems + frozen_network_problems(pushes), ledger, unwitnessed\n", "    return problems, ledger, unwitnessed\n"),
    }


METHOD = {
    "wired-off": "DMain.test_the_cli_refuses_an_edited_state",
    "draft-digest": "DDraft.test_a_recorded_digest_that_is_not_the_drafts_is_refused",
    "keys-outside": "DKeys.test_a_design_key_edited_at_the_freeze_is_refused",
    "keys-present": "DKeys.test_every_key_the_freeze_writes_must_be_present",
    "never-written": "DClean.test_the_clean_freeze_has_no_problem",
    "limit-at-freeze": "DLimit.test_the_limit_stripped_or_softened_at_the_freeze_is_refused",
    "limit-at-publication": "DLimit.test_check_publication_holds_the_limit",
    "review-digest": "DReview.test_a_recorded_digest_that_is_not_the_reports_is_refused",
    "review-absent": "DReview.test_the_named_report_must_exist_at_the_parent",
    "ruling": "DReview.test_a_named_report_that_refused_is_refused_by_its_ruling",
    "gate": "DReview.test_a_seed_commit_the_gate_refuses_is_refused",
    "gate-names": "DReview.test_another_report_named_with_its_own_digest_is_refused",
    "gate-at-head": "DReview.test_the_gate_reads_the_parent_not_head",
    "parent-edit": "DParent.test_an_edited_parent_is_refused_not_read_as_another_copy",
    "merge": "DParent.test_a_merge_freeze_commit_is_refused",
    "touch": "DTouch.test_a_freeze_commit_carrying_anything_else_is_refused",
    "fragment": "DTouch.test_an_edited_fragment_is_refused",
    "bytes": "DBytes.test_a_pin_dropped_is_refused",
    "draft-gates": "DDraft.test_the_gates_on_the_draft_are_read",
    "holdout-validator": "DHoldout.test_digests_the_validator_refuses_are_refused",
    "holdout-count": "DHoldout.test_a_count_that_is_not_theirs_is_refused",
    "witness-unread": "DReal.test_a_placeholder_witness_is_refused",
    "witness-compare": "DReal.test_the_real_shape_passes_and_an_edited_witness_does_not",
    "reading-synthetic": "DReal.test_a_synthetic_reading_is_refused",
    "record-digest": "DReal.test_a_record_whose_digest_is_not_its_texts_is_refused",
    "root-passes": "DReal.test_a_root_freeze_commit_is_refused_on_the_real_road_only",
    "network-push": "DNetwork.test_the_network_door_holds_the_witness_and_the_reading",
    "network-reading": "DNetwork.test_the_network_door_holds_the_witness_and_the_reading",
    "network-door": "DNetwork.test_witness_main_reads_the_door",
    "shapes": "DShapes.test_the_recheck_reads_the_shapes_gate",
    "rounds-after-freeze": "DRounds.test_a_prefreeze_row_is_refused_once_frozen",
    "rounds-verify-too": "DRounds.test_a_verify_row_is_not_refused_for_the_freeze",
    "rule-off": "DRoad.test_the_road_lands_with_no_edit_to_a_pinned_file_but_its_claims",
    "rule-any-bytes": "DRoad.test_an_edited_report_is_scanned",
    "rule-no-digest": "DRoad.test_a_report_with_no_stated_digest_is_scanned",
    "rule-floor": "DRoad.test_the_rule_starts_at_round_nine_and_reads_only_review_reports",
    "tool-anywhere": "DRoad.test_the_claims_tool_refuses_anywhere_else",
    "register-frozen": "DPost.test_a_valid_verify_row_holds_the_pin",
    "register-prefix": "DPost.test_the_rows_of_the_freeze_must_survive_a_verify_row",
    "register-kind": "DPost.test_a_later_prefreeze_row_refuses",
    "register-number": "DPost.test_an_invalid_verify_row_refuses",
    "register-digests": "DPost.test_an_invalid_verify_row_refuses",
    "register-launch": "DPost.test_an_invalid_verify_row_refuses",
    "register-top": "DPost.test_a_top_level_change_refuses",
    "regrade-flag": "DPost.test_the_cli_is_green_along_the_plans_road",
    "verifier-report-scanned": "DPost.test_the_cli_is_green_along_the_plans_road",
    "freeze-outputs-scanned": "DPost.test_the_cli_is_green_along_the_plans_road",
    "rule-leading-zero": "DRoad.test_the_rule_starts_at_round_nine_and_reads_only_review_reports",
}
WITNESSES = {name: (METHOD[name], clause) for name, (clause, _, _, _) in mutants().items()}
# One child builds its own scratch repository and reads one test: about a minute each on a loaded Mac, 3 Nov 2026.
CHILD_TIMEOUT_S = 1200


def run_witnesses(names) -> int:
    chosen = names or sorted(WITNESSES)
    red = 0
    import mutation_baseline  # the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_fold11 witnesses", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()),
                                    *sorted({WITNESSES[x][0] for x in chosen})], timeout=CHILD_TIMEOUT_S, tag="test_fold11")
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=CHILD_TIMEOUT_S)
        record = re.findall(r"^test_fold11 outcomes: (\{.*\})$", got.stdout, re.M)
        outcome = json.loads(record[-1]) if record else None
        attributed = re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w.-])", got.stderr) is not None
        clean = bool(outcome) and sorted(set(outcome["failures"])) == [method] and outcome["errors"] == []
        passed = attributed and clean and got.returncode != 0
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}", flush=True)
        if not passed:
            print(got.stdout[-2000:] + got.stderr[-2000:], flush=True)
            return 1
        red += 1
    print(f"test_fold11 witnesses: {red}/{len(chosen)} red; registry {len(WITNESSES)}", flush=True)
    return 0


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses(sys.argv[sys.argv.index("--witnesses") + 1:]))
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        if SELECTED not in WITNESSES:
            raise SystemExit(f"unknown mutant {SELECTED!r}")
        del sys.argv[index:index + 2]
    result = unittest.main(verbosity=2, exit=False).result
    ids = lambda pairs: [t.id().removeprefix("__main__.").split(" ")[0] for t, _ in pairs]  # noqa: E731
    print(f"test_fold11: {result.testsRun} run, {len(result.failures)} failures, {len(result.errors)} errors, "
          f"{len(result.skipped)} skipped")
    print("test_fold11 outcomes: " + json.dumps({"failures": ids(result.failures), "errors": ids(result.errors),
                                                 "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
