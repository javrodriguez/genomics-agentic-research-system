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
  D.holdout   the frozen digests pass the freeze's own validator and the count is theirs
  D.real      outside a disposable rehearsal: the rehearsal record's sha256 is its text's, the beacon reading is no
              synthetic one, the witness is one and is what the freeze derives from its own stamps
  D.network   check_results.py --witness holds the frozen witness to the push records and the reading to the relays
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
import study  # noqa: E402
import takes  # noqa: E402

SELECTED = None
OUTPUTS = ("prereg.json", "COPIED.json", "COPIED.d/freeze.json")
FRAGMENT = "COPIED.d/review-records.json"
MESSAGE = "Freeze\n\nCo-Authored-By: synthetic <synthetic@example.invalid>\n"

# The check as the battery reads a broken freeze: frozen_commit_problems (880 pins, two processes each, unchanged by this
# lane, and driven unstubbed by D.main) is the only stand-in. `plan` is the --rehearsal-plan flag.
DRIVER = """
import json, sys
sys.path.insert(0, sys.argv[1])
import check_results as cr
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
        self.earlier = max(r["n"] for r in register["rows"] if r.get("kind") == "prefreeze")
        self.n = self.earlier + 1
        register["rows"].append({"n": self.n, "kind": "prefreeze", "launch_commit": self.base, "voids": None})
        self.rounds.write_text(json.dumps(register, indent=2) + "\n")
        row = self.commit("the round's row")
        self.report = study.rel(study.REVIEW_DIR, f"prefreeze-{self.n}.md")
        digest = hashlib.sha256((self.study / "prereg-draft.json").read_bytes()).hexdigest()
        text = f"{freeze.REVIEW_DIGEST_PREFIX}{digest}\n\n# a synthetic review\n\n{freeze.RULING_LINE}\n"
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
        named(self.world.check(), "draft_sha256_at_freeze", "D.draft")

    def test_a_draft_edited_in_the_freeze_commit_with_its_digest_is_refused(self):
        draft = json.loads((self.world.study / "prereg-draft.json").read_text())
        draft["views"] = "edited"
        body = freeze.json_bytes(draft)

        def edit(doc):
            doc["draft_sha256_at_freeze"] = hashlib.sha256(body).hexdigest()
            doc["views"] = "edited"
        self.world.commit_freeze(edit, also={"prereg-draft.json": body})
        named(self.world.check(), "prereg-draft.json", "D.touch")


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
                named(self.world.check(), "published_tip_residual", "D.limit")

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
        mock.patch.object(run_builders, "order_problems", return_value=[]), mock.patch.object(cr.stats, "check_records"):
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
        named(self.world.check(), "pre_freeze_review_sha256", "D.review")

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
        # review_file_problems stood in as clean, so the ruling clause is read alone; round 8 ruled DO NOT FREEZE
        rel = self.earlier_report()
        body = (self.world.repo / rel).read_bytes()
        self.assertNotEqual(freeze.read_ruling(body.decode()), freeze.DO_FREEZE, "the fixture: the earlier round refused")

        def edit(doc):
            doc["pre_freeze_review_file"] = rel
            doc["pre_freeze_review_sha256"] = hashlib.sha256(body).hexdigest()
        self.world.commit_freeze(edit)
        driver = DRIVER.replace("import check_results as cr\n",
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
        named(self.world.check(), "frozen_at_commit_parent", "D.parent")

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
        named(self.world.check(), "COPIED.d/freeze.json", "D.touch")


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
            lines += [f"[0] {name}", "    ok"]
        text = "\n".join(lines + [freeze.REHEARSAL_LAST_LINE]) + "\n"
        return {"name": "freeze-rehearsal-1.txt", "sha256": hashlib.sha256(text.encode()).hexdigest(), "text": text}

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
    return {}


BOUND = {}
WITNESSES = {name: (BOUND[clause], clause) for name, (clause, _, _, _) in mutants().items()}
# One child builds its own scratch repository and reads one test. Measured on the Mac: see the fold's report.
CHILD_TIMEOUT_S = 1200


def run_witnesses(names) -> int:
    chosen = names or sorted(WITNESSES)
    red = 0
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
