#!/usr/bin/env python3
"""The holdout's salted digests and count enter at the freeze commit only (Gap Study round 4, lane w8b).

Ruling W8B-gap4-1 is Javier's own decision, typed Mon 12 Oct 2026 08:51 EDT: "holdout digests A". The holdout's
salted fingerprints, and its per-version count, enter this repository only in the freeze commit's frozen file; until
then nothing about the holdout leaves aegis. Each clause below is one guard, with its witness.

  H1 draft     the committed draft and the writer's output carry neither freeze-only field, no PENDING stand-in, no
               count inside holdout_rule and no pending entry for the holdout. Witness: pending-stand-in.
  H2 writer    build_draft refuses to write either field, or a holdout_rule with a count, into a pre-freeze draft,
               and leaves no file. Witnesses: writer-admits, rule-count-admitted.
  H3 write     freeze.main writes the digests and their per-version count from a supplied source into the frozen
               file. Witness: freeze-skips-write.
  H4 absent    freeze.main refuses by its named reason, writing nothing, when the source is not given or is not a
               file. Witnesses: absent-admitted, missing-file-admitted.
  H5 shape     a source holding a salt or any other key, a repeated key, an empty or uneven list, a repeated or
               malformed digest, or a task set other than the draft's is refused. Witnesses: salt-admitted,
               uneven-admitted.
  H6 allowed   both fields are freeze-written keys, so keys_outside_the_freeze does not call them a design edit, and
               freeze and build_draft name the same two fields. Witness: keys-not-allowed.
  H7 check     freeze.py --check refuses a committed draft that carries either field. Witness: check-skips-draft.
  H8 rehearsal a disposable rehearsal given no source writes neither field and says so. Witness: rehearsal-silent.

Fold (glitch-1b's rulings Q7 and Q8 at the w8b hand-back, Mon 12 Oct 2026 09:08 EDT): freeze_rehearsal.main, driven
with its clone, git and steps replaced by fakes:

  H9 rehearsal the rehearsal's freeze gets a synthetic digest file (hex digests of fake strings, one list per task of
               the cloned draft) and its "holdout digests" step passes; only --no-holdout-digests leaves the file out,
               and then the step fails with NOT REHEARSED and the run is never all green. Witnesses:
               rehearsal-skips-file, no-file-silent.
  H10 written  holdout_written_problems passes the real freeze's output for that synthetic file and names a missing
               or wrong field or count. Witness: written-unchecked.
  H12 synthetic a real (non-rehearsal) freeze refuses a digest file holding the rehearsal's synthetic digests
               (freeze.synthetic_digest of any task, index below SYNTHETIC_BOUND), naming W8B-gap4-1, and writes
               nothing; a rehearsal accepts them; the rehearsal deletes its file unless --keep (W8B-R1-1).
               Witnesses: synthetic-admitted, synthetic-file-kept.
  H11 owed     the holdout.py --check step is never run in the clone: it fails, naming itself OWED to aegis (C4,
               S9), so the rehearsal is not all green. Witnesses: owed-passes, owed-runs.

Synthetic strings only: every digest is the sha256 of an obviously fake string, and no holdout wording, digest, salt or
count is read or created. freeze.main runs against a temporary folder with git, the review, the pins and the writer
replaced by in-memory fakes; no process starts except --witnesses' own children.

--mutant NAME compiles one altered module in memory before the bound test runs; --witnesses runs every registered
mutant in its own process, only its bound test, and requires that test to fail by an AssertionError carrying its
clause token, with no error (rule B).
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

SELECTED = None
MODS: dict = {}
FIELDS = ("holdout_salted_digests", "holdout_wordings_per_task_version")
RULE = {"separate_author": True, "run_in_this_round": False, "publish": "salted_sha256", "salt_in_draft": False,
        "digests_and_count_enter": "the freeze commit only", "ruling": "W8B-gap4-1",
        "source": "plans/gap-study-round-4.md line 175"}
TASKS = ("synthetic-task-a", "synthetic-task-b")
ABSENT_WORDS = "the holdout digest source is absent"


def fake(task: str, i: int) -> str:
    return hashlib.sha256(f"synthetic-not-a-wording-{task}-{i}".encode()).hexdigest()


def fake_source(per_task: int = 2) -> dict:
    return {"salted_sha256": {task: [fake(task, i) for i in range(per_task)] for task in TASKS}}


def mutants() -> dict:
    """name -> (clause, module, anchor, replacement). Each anchor occurs once in the module's source."""
    return {
        "pending-stand-in": ("H1.draft", "build_draft", '    d["holdout_rule"] = copy.deepcopy(HOLDOUT_RULE)\n',
                             '    d["holdout_rule"] = copy.deepcopy(HOLDOUT_RULE)\n'
                             '    d["holdout_salted_digests"] = PENDING\n'),
        "writer-admits": ("H2.writer", "build_draft", "    early = prefreeze_holdout_problems(d)\n",
                          "    early = []\n"),
        "rule-count-admitted": ("H2.writer", "build_draft",
                                '    if "holdout_rule" in draft and draft["holdout_rule"] != HOLDOUT_RULE:\n',
                                "    if False:\n"),
        "freeze-skips-write": ("H3.write", "freeze", "        frozen.update(holdout)\n", "        pass\n"),
        "absent-admitted": ("H4.absent", "freeze", "    if source is None:\n        return None if rehearsal else",
                            "    if source is None:\n        return None if True else"),
        "missing-file-admitted": ("H4.absent", "freeze", "    if not Path(source).is_file():\n", "    if False:\n"),
        "salt-admitted": ("H5.shape", "freeze", "    if not isinstance(data, dict) or set(data) != {HOLDOUT_SOURCE_KEY}:\n",
                          "    if not isinstance(data, dict):\n"),
        "uneven-admitted": ("H5.shape", "build_draft", "    if len(counts) != 1 or min(counts) < 1:\n",
                            "    if min(counts) < 1:\n"),
        "keys-not-allowed": ("H6.allowed", "freeze", '    "holdout_salted_digests", "holdout_wordings_per_task_version", "published_tip_residual",\n',
                             '    "published_tip_residual",\n'),
        # lane pf1-l1-freeze-gates (pre-freeze review 1, m1): --check reads the holdout fields as one leg of check_legs
        "check-skips-draft": ("H7.check", "freeze", '    legs.append(("holdout fields", [problem] if problem else []))\n',
                              '    legs.append(("holdout fields", []))\n'),
        "rehearsal-silent": ("H8.rehearsal", "freeze", "            print(HOLDOUT_NOT_REHEARSED)\n", "            pass\n"),
        "rehearsal-skips-file": ("H9.rehearsal", "freeze_rehearsal",
                                 "        holdout_file = None if args.no_holdout_digests else scratch / HOLDOUT_FILE\n",
                                 "        holdout_file = None\n"),
        "no-file-silent": ("H9.rehearsal", "freeze_rehearsal",
                           '                steps.append(("holdout digests", 1, NO_FILE_LINE))\n',
                           "                pass\n"),
        "written-unchecked": ("H10.written", "freeze_rehearsal", "    return problems\n\n\ndef freeze_command",
                              "    return []\n\n\ndef freeze_command"),
        "owed-passes": ("H11.owed", "freeze_rehearsal", "    return (1, OWED[script]) if",
                        "    return (0, OWED[script]) if"),
        "synthetic-admitted": ("H12.synthetic", "freeze", "    if not rehearsal and synthetic:\n", "    if False:\n"),
        "synthetic-file-kept": ("H12.synthetic", "freeze_rehearsal",
                                "        if holdout_file is not None and not args.keep:\n", "        if False:\n"),
        "owed-runs": ("H11.owed", "freeze_rehearsal", "        owed = owed_step(command)\n", "        owed = None\n"),
    }


def compile_module(name: str, source: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(HERE / f"{name}.py")
    sys.modules[name] = mod
    exec(compile(source, mod.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


NAMES = ("build_draft", "freeze", "freeze_rehearsal")


PRIOR = {}


def setUpModule():
    for name in NAMES:
        MODS[name] = PRIOR[name] = __import__(name)     # the real module, put back by tearDownModule
    if SELECTED is not None:
        _, target, old, new = mutants()[SELECTED]
        text = (HERE / f"{target}.py").read_text()
        assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
        MODS[target] = compile_module(target, text.replace(old, new))
        if target == "build_draft":      # freeze imports build_draft lazily; it must meet the compiled one
            MODS["freeze"] = compile_module("freeze", (HERE / "freeze.py").read_text())
        if target in ("build_draft", "freeze"):  # freeze_rehearsal imports freeze at import
            MODS["freeze_rehearsal"] = compile_module("freeze_rehearsal", (HERE / "freeze_rehearsal.py").read_text())


def tearDownModule():
    # A compiled witness never outlives this module (lane gap-prebeacon-fix3, review 90c1fd9 NIT 4): each name gets back
    # the real module setUpModule imported, never dropped, so later modules keep one copy of each (test_cp8_prep's
    # pattern). A module absent before setUpModule stays loaded afterwards, the real one (review 2f99816 NIT 1).
    sys.modules.update(PRIOR)


def b():
    return MODS["build_draft"]


def fz():
    return MODS["freeze"]


class FreezeHarness:
    """freeze.main against a temporary folder: git, the review, the pins, the design checks and the writer are fakes."""

    def __init__(self, tmp: Path, draft: dict):
        self.tmp, self.written = tmp, []
        (tmp / "prereg-draft.json").write_text(json.dumps(draft))
        (tmp / "review").mkdir()
        (tmp / "review" / "prefreeze-1.md").write_text("synthetic review\n")

    @staticmethod
    def git(*args):
        return {("remote",): (0, ""), ("status", "--porcelain"): (0, ""),
                ("rev-parse", "HEAD"): (0, "b" * 40)}.get(args, (1, "no such fake git call"))

    @staticmethod
    def prepare(draft, *, review, parent, pins, frozen_at, beacon=None):
        return dict(copy.deepcopy(draft), status="FROZEN", frozen_at=frozen_at, frozen_at_commit_parent=parent,
                    pre_freeze_review_commit=review, take_order_seed=review, take_order=[], pinned_files=pins)

    def run(self, argv):
        f = fz()
        out = io.StringIO()
        patches = ((f, "HERE", self.tmp), (f, "REPO", self.tmp), (f, "DRAFT", self.tmp / "prereg-draft.json"),
                   (f, "PINNED", []), (f, "git", self.git), (f, "prepare", self.prepare),
                   (f, "review_file_problems", lambda commit: ([], "review/prefreeze-1.md")),
                   (f, "study_tree_sha", lambda *a, **k: "c" * 64),
                   (f, "rehearsal_evidence", lambda *a, **k: {"name": "synthetic", "sha256": "d" * 64, "text": ""}),
                   (f, "write_outputs", lambda frozen: self.written.append(frozen) or ()),
                   (f, "owned_paths", lambda *a, **k: []),
                   # lane pf1-l1-freeze-gates (pre-freeze review 1, MAJORs 4 and 9): the coverage gate and the beacon
                   # read stood in for, as the other gates here are; tests/test_pf1_freeze_gates.py binds both
                   (f, "coverage_problem", lambda *a, **k: None),
                   (f, "take_order_beacon_reading", lambda *a, **k: {"synthetic": "beacon reading"}),
                   (f, "take_order_witness", lambda *a, **k: {"synthetic": "push witness"}),
                   # lane fold2-lb (pre-freeze review 2, m3): the order-function gate stood in for on the synthetic
                   # draft, as the gates above are; tests/test_fold2_lb.py binds it
                   (f, "order_function_problem", lambda *a, **k: None),
                   (f.copy_manifest, "problems", lambda *a, **k: []))
        with contextlib.ExitStack() as stack:
            for module, name, value in patches:
                stack.enter_context(mock.patch.object(module, name, value))
            stack.enter_context(contextlib.redirect_stdout(out))
            code = f.main(argv)
        return code, out.getvalue()


def synthetic_draft() -> dict:
    return {"status": "DRAFT", "tasks": [{"id": t} for t in TASKS], "holdout_rule": copy.deepcopy(RULE)}


class Case(unittest.TestCase):
    def tmpdir(self) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        return Path(holder.name)

    def harness(self, draft=None):
        tmp = self.tmpdir()
        return FreezeHarness(tmp, synthetic_draft() if draft is None else draft)

    def source(self, value) -> Path:
        tmp = self.tmpdir()
        path = tmp / "synthetic-digests.json"
        path.write_text(value if isinstance(value, str) else json.dumps(value))
        return path


# ------------------------------------------------------------------------------------------------- H1
class H1Draft(Case):
    def test_no_pre_freeze_draft_carries_the_holdout(self):
        committed = json.loads((HERE / "prereg-draft.json").read_text())
        try:
            built = b().build()
        except ValueError as exc:
            self.fail(f"H1.draft: the builder refused its own draft: {exc}")
        for name, d in (("committed", committed), ("built", built)):
            self.assertEqual([k for k in FIELDS if k in d], [], f"H1.draft {name}: a freeze-only field")
            self.assertEqual(d.get("holdout_rule"), RULE, f"H1.draft {name}: holdout_rule")
            self.assertEqual([k for k in d.get("pending", {}) if "holdout" in k], [], f"H1.draft {name}: pending")
        self.assertEqual(json.loads(b().json_bytes(built)), committed, "H1.draft: committed bytes are the writer's")


# ------------------------------------------------------------------------------------------------- H2
class H2Writer(Case):
    def test_the_writer_refuses_the_freeze_fields(self):
        self.assertTrue(hasattr(b(), "prefreeze_holdout_problems"), "H2.writer: the pre-freeze guard is required")
        d = b().build()
        planted = {"digests": dict(d, holdout_salted_digests=fake_source()["salted_sha256"]),
                   "stand-in": dict(d, holdout_salted_digests="PENDING"),
                   "count": dict(d, holdout_wordings_per_task_version=2),
                   "rule-count": dict(d, holdout_rule=dict(RULE, wordings_per_task_version=2))}
        tmp = self.tmpdir()
        for name, draft in planted.items():
            with self.subTest(name=name):
                out = tmp / f"{name}.json"
                with self.assertRaises(ValueError, msg=f"H2.writer {name}") as caught:
                    b().write_draft(draft, out)
                self.assertIn("W8B-gap4-1", str(caught.exception), "H2.writer")
                self.assertFalse(out.exists(), f"H2.writer {name}: a file was written")


# ------------------------------------------------------------------------------------------------- H3
class H3Write(Case):
    def test_the_freeze_writes_digests_and_count(self):
        self.assertTrue(hasattr(fz(), "holdout_fields"), "H3.write: the freeze's holdout writer is required")
        h = self.harness()
        source = self.source(fake_source(per_task=2))
        code, out = h.run(["--review-commit", "a" * 40, "--write", "--rehearsal-record", "synthetic",
                           "--holdout-digests", str(source)])
        self.assertEqual(code, 0, f"H3.write {out}")
        self.assertEqual(len(h.written), 1, "H3.write: one frozen file")
        frozen = h.written[0]
        self.assertEqual(frozen.get("holdout_salted_digests"), fake_source()["salted_sha256"], "H3.write digests")
        self.assertEqual(frozen.get("holdout_wordings_per_task_version"), 2, "H3.write count")
        self.assertEqual(frozen.get("holdout_rule"), RULE, "H3.write: the rule is the draft's")


# ------------------------------------------------------------------------------------------------- H4
class H4Absent(Case):
    def test_the_freeze_refuses_without_its_source(self):
        self.assertTrue(hasattr(fz(), "holdout_source_problem"), "H4.absent: the freeze's source check is required")
        h = self.harness()
        missing = self.tmpdir() / "no-such-file.json"
        for name, extra in (("not given", []), ("not a file", ["--holdout-digests", str(missing)])):
            for mode in ([], ["--write", "--rehearsal-record", "synthetic"]):
                with self.subTest(name=name, mode=mode):
                    code, out = h.run(["--review-commit", "a" * 40, *mode, *extra])
                    self.assertEqual(code, 1, f"H4.absent {name} {out}")
                    self.assertIn(ABSENT_WORDS, out, f"H4.absent {name}")
                    self.assertIn("W8B-gap4-1", out, "H4.absent")
        self.assertEqual(h.written, [], "H4.absent: nothing written")


# ------------------------------------------------------------------------------------------------- H5
class H5Shape(Case):
    def test_a_malformed_source_is_refused(self):
        good = fake_source(per_task=7)["salted_sha256"]
        a, z = TASKS
        bad = {"salt": {"salted_sha256": good, "salt": "synthetic-salt"},
               "wordings": {"salted_sha256": good, "wordings": ["synthetic"]},
               "no-digests": {"salt": "synthetic-salt"},
               "repeated key": '{"salted_sha256": %s, "salted_sha256": %s}' % (json.dumps(good), json.dumps(good)),
               "uneven": {"salted_sha256": dict(good, **{z: good[z][:2]})},
               "empty lists": {"salted_sha256": {a: [], z: []}},
               "empty": {"salted_sha256": {}},
               "extra task": {"salted_sha256": dict(good, **{"synthetic-task-c": [fake("c", i) for i in range(7)]})},
               "missing task": {"salted_sha256": {a: good[a]}},
               "repeated digest": {"salted_sha256": dict(good, **{z: [good[a][0]] + good[z][1:]})},
               "upper case": {"salted_sha256": dict(good, **{z: [d.upper() for d in good[z]]})},
               "not json": "synthetic, not json"}
        f = fz()
        self.assertTrue(hasattr(f, "holdout_fields"), "H5.shape: the freeze's holdout reader is required")
        self.assertEqual(f.holdout_fields(self.source({"salted_sha256": good}), list(TASKS)),
                         {"holdout_salted_digests": good, "holdout_wordings_per_task_version": 7}, "H5.shape good")
        for name, value in bad.items():
            with self.subTest(name=name):
                try:
                    f.holdout_fields(self.source(value), list(TASKS))
                except ValueError:
                    continue
                except Exception as exc:  # the freeze refuses a malformed source by ValueError, never a crash
                    self.fail(f"H5.shape {name}: {type(exc).__name__}, not a refusal")
                self.fail(f"H5.shape {name}: accepted")


# ------------------------------------------------------------------------------------------------- H6
class H6Allowed(Case):
    def test_the_fields_are_freeze_written(self):
        f = fz()
        self.assertTrue(hasattr(f, "HOLDOUT_KEYS") and hasattr(b(), "HOLDOUT_FREEZE_KEYS"), "H6.allowed: the names")
        self.assertEqual(tuple(f.HOLDOUT_KEYS), FIELDS, "H6.allowed: freeze's names")
        self.assertEqual(tuple(b().HOLDOUT_FREEZE_KEYS), FIELDS, "H6.allowed: build_draft's names")
        draft = synthetic_draft()
        frozen = dict(draft, holdout_salted_digests=fake_source()["salted_sha256"],
                      holdout_wordings_per_task_version=2)
        self.assertEqual(f.keys_outside_the_freeze(draft, frozen), [], "H6.allowed")
        self.assertEqual(f.keys_outside_the_freeze(draft, dict(frozen, holdout_rule=dict(RULE, publish="synthetic"))),
                         ["holdout_rule.publish"], "H6.allowed: the rule is never freeze-written")


# ------------------------------------------------------------------------------------------------- H7
class H7Check(Case):
    def test_check_refuses_a_draft_carrying_the_fields(self):
        h = self.harness()
        code, out = h.run(["--check"])
        # lane pf1-l1-freeze-gates (pre-freeze review 1, m1): --check now reads every leg a freeze reads, and this
        # synthetic draft fails the others (PENDING inputs, no beacon); the holdout leg itself holds on it
        self.assertIn("freeze --check: holdout fields: ok", out, f"H7.check clean {out}")
        for name, draft in (("digests", dict(synthetic_draft(), holdout_salted_digests="PENDING")),
                            ("count", dict(synthetic_draft(), holdout_wordings_per_task_version=7)),
                            ("rule-count", dict(synthetic_draft(), holdout_rule=dict(RULE, wordings_per_task_version=7)))):
            with self.subTest(name=name):
                h = self.harness(draft)
                code, out = h.run(["--check"])
                self.assertEqual(code, 1, f"H7.check {name} {out}")
                self.assertIn("W8B-gap4-1", out, f"H7.check {name}")


# ------------------------------------------------------------------------------------------------- H8
class H8Rehearsal(Case):
    def test_a_rehearsal_without_a_source_writes_neither_field_and_says_so(self):
        h = self.harness()
        code, out = h.run(["--review-commit", "a" * 40, "--rehearsal", "--write"])
        self.assertEqual(code, 0, f"H8.rehearsal {out}")
        self.assertEqual([k for k in FIELDS if k in h.written[0]], [], "H8.rehearsal: a field written")
        self.assertIn("NOT REHEARSED: the holdout digests", out, "H8.rehearsal: said so")
        h = self.harness()
        code, out = h.run(["--review-commit", "a" * 40, "--rehearsal", "--write",
                           "--holdout-digests", str(self.source(fake_source(per_task=1)))])
        self.assertEqual(code, 0, f"H8.rehearsal with a source {out}")
        self.assertEqual(h.written[0].get("holdout_wordings_per_task_version"), 1, "H8.rehearsal with a source")
        self.assertNotIn("NOT REHEARSED", out, "H8.rehearsal with a source")


# ------------------------------------------------------------------------------------------------- H9-H11
class RehearsalHarness:
    """freeze_rehearsal.main with the clone, git, the review and every step replaced by fakes; the fake freeze step
    writes the frozen file from the digest file it is handed, as freeze.py does."""

    def __init__(self, tmp: Path):
        self.tmp, self.commands, self.sources = tmp, [], []
        self.draft = tmp / "prereg-draft.json"
        self.draft.write_text(json.dumps(synthetic_draft()))
        self.scratch = tmp / "scratch"

    def sh(self, argv, cwd, env=None, timeout=3600):
        if argv[:2] == ["git", "clone"]:
            target = Path(argv[-1])
            (target / "evals" / "gap-study-4").mkdir(parents=True)
            (target / "evals" / "gap-study-4" / "prereg-draft.json").write_bytes(self.draft.read_bytes())
        return 0, ""

    def run_step(self, command, clone):
        self.commands.append(list(command))
        if command[4].endswith("freeze.py"):
            frozen = dict(synthetic_draft(), status="FROZEN", take_order=[{}])
            # lane pf1-l1-freeze-gates (MAJOR 9): the fake freeze read a real-shaped beacon, as a freeze given one does
            frozen["take_order_beacon_reading"] = {"signature": "ab"}
            if "--holdout-digests" in command:
                source = json.loads(Path(command[command.index("--holdout-digests") + 1]).read_text())
                self.sources.append(source)       # read while the freeze runs: the rehearsal deletes it after
                counts = {len(v) for v in source["salted_sha256"].values()}
                frozen.update(holdout_salted_digests=source["salted_sha256"],
                              holdout_wordings_per_task_version=counts.pop())
            (Path(clone) / "evals" / "gap-study-4" / "prereg.json").write_text(json.dumps(frozen))
            return 0, "freeze: wrote prereg.json"
        if str(command[4]).endswith("live_box_cut.py"):   # lane gap-prebeacon-fix3: the clone's verifier, its closed pass line
            sha = hashlib.sha256(Path(command[-1]).read_bytes()).hexdigest()
            return 0, (f"live-box record {sha}: walk lb1, budget 20 s of 900 s, turn 1 cut (end timed-out, exit 124), "
                       f"stream 3 unit(s), session 3 unit(s), shape equal, content problems 0, session torn no; files 4 "
                       f"re-read equal; adapter, check_take and checker digests this tree's; within the bound")
        return 0, "ok"

    def run(self, argv):
        r, f = MODS["freeze_rehearsal"], MODS["freeze"]
        self.scratch.mkdir()
        patches = ((r, "DRAFT", self.draft), (r, "git", lambda *a, **k: (0, "")), (r, "sh", self.sh),
                   (r, "run_step", self.run_step), (r, "rehearsal_plan", lambda pre, row: ({}, ())),
                   (r.tempfile, "mkdtemp", lambda *a, **k: str(self.scratch)),
                   (r.freeze, "outputs_exist", lambda *a: False),
                   (r.freeze, "review_file_problems", lambda commit: ([], "review/prefreeze-1.md")),
                   (r.freeze, "study_tree_sha", lambda *a, **k: "c" * 64))
        out = io.StringIO()
        with contextlib.ExitStack() as stack:
            for module, name, value in patches:
                stack.enter_context(mock.patch.object(module, name, value))
            stack.enter_context(contextlib.redirect_stdout(out))
            code = r.main(argv)
        report = (self.scratch / "freeze-rehearsal-1.txt").read_text()
        return code, report

    def freeze_commands(self):
        return [c for c in self.commands if c[4].endswith("freeze.py")]


class H9Rehearsal(Case):
    def test_the_rehearsal_freeze_exercises_the_digest_path(self):
        self.assertTrue(hasattr(MODS["freeze_rehearsal"], "synthetic_holdout_source"), "H9.rehearsal: the fold")
        # lane gap-prebeacon-fix3: since the live-box merge a rehearsal without --live-box-record fails its live-box
        # step NOT REHEARSED (glitch-45's ruling); a stand-in record, verified by the fake clone verifier as
        # test_cp6_wiring does, keeps that step green, so no step but the digest step can say NOT REHEARSED here
        record = self.tmpdir() / "record.json"
        record.write_text("{}\n")
        live_box = ["--live-box-record", str(record), "--live-box-sha256", hashlib.sha256(record.read_bytes()).hexdigest()]
        h = RehearsalHarness(self.tmpdir())
        code, report = h.run(["--review-commit", "a" * 40, *live_box])
        self.assertIn(f"[0] live-box: forced-timeout claude-code take\n    live-box record {live_box[3]}: walk lb1, ",
                      report, "H9.rehearsal: the stand-in record")
        [command] = h.freeze_commands()
        self.assertIn("--holdout-digests", command, "H9.rehearsal: the freeze got no digest file")
        [source] = h.sources
        self.assertEqual(set(source), {"salted_sha256"}, "H9.rehearsal: digest-only file")
        self.assertEqual(sorted(source["salted_sha256"]), sorted(TASKS), "H9.rehearsal: one list per task")
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", d) for v in source["salted_sha256"].values() for d in v),
                        "H9.rehearsal: hex digests")
        self.assertIn("[0] holdout digests\n    both fields written from the synthetic digest file", report,
                      "H9.rehearsal: the step checks both fields")
        self.assertNotIn("NOT REHEARSED", report, "H9.rehearsal")
        h = RehearsalHarness(self.tmpdir())
        code, report = h.run(["--review-commit", "a" * 40, "--no-holdout-digests", *live_box])
        [command] = h.freeze_commands()
        self.assertNotIn("--holdout-digests", command, "H9.rehearsal: --no-holdout-digests passed a file")
        self.assertIn("[1] holdout digests\n    NOT REHEARSED: the holdout digests", report,
                      "H9.rehearsal: a no-file rehearsal must say so and fail its step")
        self.assertEqual((code, report.rstrip().splitlines()[-1]), (1, "NOT all green"), "H9.rehearsal")


class H10Written(Case):
    def test_the_written_check_reads_the_real_freeze(self):
        r = MODS["freeze_rehearsal"]
        self.assertTrue(hasattr(r, "holdout_written_problems"), "H10.written: the fold")
        h = self.harness()
        source_file = self.tmpdir() / "synthetic.json"
        source = r.synthetic_holdout_source(h.tmp / "prereg-draft.json", source_file)
        code, out = h.run(["--review-commit", "a" * 40, "--rehearsal", "--write", "--holdout-digests", str(source_file)])
        self.assertEqual(code, 0, f"H10.written {out}")
        self.assertEqual(r.holdout_written_problems(h.written[0], source), [], "H10.written: the real freeze's output")
        frozen = h.written[0]
        for name, bad in (("missing", {k: v for k, v in frozen.items() if k not in FIELDS}),
                          ("count", dict(frozen, holdout_wordings_per_task_version=7)),
                          ("digests", dict(frozen, holdout_salted_digests={t: [fake(t, 9)] * 2 for t in TASKS}))):
            with self.subTest(name=name):
                self.assertNotEqual(r.holdout_written_problems(bad, source), [], f"H10.written {name}")


class H11Owed(Case):
    def test_the_holdout_check_names_itself_owed(self):
        h = RehearsalHarness(self.tmpdir())
        code, report = h.run(["--review-commit", "a" * 40])
        self.assertEqual([c for c in h.commands if c[4].endswith("holdout.py")], [],
                         "H11.owed: holdout.py was run in the clone")
        self.assertIn("[1] holdout.py --check\n    OWED: holdout.py --check lives in private aegis (ruling C4)", report,
                      "H11.owed: the step must fail and name itself owed")
        self.assertEqual((code, report.rstrip().splitlines()[-1]), (1, "NOT all green"), "H11.owed")


class H12Synthetic(Case):
    def test_a_real_freeze_refuses_the_rehearsal_digests(self):
        f = fz()
        self.assertTrue(hasattr(f, "synthetic_holdout_source") and hasattr(f, "SYNTHETIC_BOUND"),
                        "H12.synthetic: the generator lives in freeze.py")
        h = self.harness()
        source = self.tmpdir() / "synthetic-holdout-digests.json"
        MODS["freeze_rehearsal"].synthetic_holdout_source(h.tmp / "prereg-draft.json", source)  # the probe's file
        code, out = h.run(["--review-commit", "a" * 40, "--write", "--rehearsal-record", "synthetic",
                           "--holdout-digests", str(source)])
        self.assertEqual((code, h.written), (1, []), f"H12.synthetic: a real freeze took them {out}")
        self.assertIn("synthetic", out, "H12.synthetic")
        self.assertIn("W8B-gap4-1", out, "H12.synthetic")
        # one synthetic digest, any task, at the last index below the bound, hidden among real-looking ones
        mixed = fake_source(per_task=2)
        mixed["salted_sha256"][TASKS[1]][1] = f.synthetic_digest(TASKS[0], f.SYNTHETIC_BOUND - 1)
        h = self.harness()
        code, out = h.run(["--review-commit", "a" * 40, "--write", "--rehearsal-record", "synthetic",
                           "--holdout-digests", str(self.source(mixed))])
        self.assertEqual((code, h.written), (1, []), f"H12.synthetic: one synthetic digest taken {out}")
        h = self.harness()
        code, out = h.run(["--review-commit", "a" * 40, "--rehearsal", "--write", "--holdout-digests", str(source)])
        self.assertEqual(code, 0, f"H12.synthetic: a rehearsal refused them {out}")
        for argv, kept in (([], False), (["--keep"], True)):
            with self.subTest(argv=argv):
                r = RehearsalHarness(self.tmpdir())
                r.run(["--review-commit", "a" * 40, *argv])
                self.assertEqual((r.scratch / "synthetic-holdout-digests.json").exists(), kept,
                                 "H12.synthetic: the rehearsal's synthetic file is deleted unless --keep")


BOUND = {"H1.draft": "H1Draft.test_no_pre_freeze_draft_carries_the_holdout",
         "H2.writer": "H2Writer.test_the_writer_refuses_the_freeze_fields",
         "H3.write": "H3Write.test_the_freeze_writes_digests_and_count",
         "H4.absent": "H4Absent.test_the_freeze_refuses_without_its_source",
         "H5.shape": "H5Shape.test_a_malformed_source_is_refused",
         "H6.allowed": "H6Allowed.test_the_fields_are_freeze_written",
         "H7.check": "H7Check.test_check_refuses_a_draft_carrying_the_fields",
         "H8.rehearsal": "H8Rehearsal.test_a_rehearsal_without_a_source_writes_neither_field_and_says_so",
         "H9.rehearsal": "H9Rehearsal.test_the_rehearsal_freeze_exercises_the_digest_path",
         "H10.written": "H10Written.test_the_written_check_reads_the_real_freeze",
         "H11.owed": "H11Owed.test_the_holdout_check_names_itself_owed",
         "H12.synthetic": "H12Synthetic.test_a_real_freeze_refuses_the_rehearsal_digests"}
WITNESSES = {name: (BOUND[clause], clause) for name, (clause, _, _, _) in mutants().items()}


# One mutant child's limit. 110 s timed out on a loaded athena (gap4-fold4-battery-eefd321, w8b-holdout-digests.txt:5).
# Measured on the Mac, 31 Oct 2026: the slowest child took 701 s (pending-stand-in), so the limit is 4x that, rounded up.
CHILD_TIMEOUT_S = 3000


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_holdout_digests witnesses", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()),
                                    *sorted({WITNESSES[x][0] for x in chosen})], timeout=1800, tag="test_holdout_digests")
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=CHILD_TIMEOUT_S)
        record = re.findall(r"^test_holdout_digests outcomes: (\{.*\})$", got.stdout, re.M)
        outcome = json.loads(record[-1]) if record else None
        blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", got.stderr,
                            re.M | re.S)
        attributed = any(f"{cls}.{test}" == method and "AssertionError" in body and
                         re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w.-])", body)
                         for test, cls, body in blocks)
        # a test's subtests repeat its id: the distinct failing methods must be exactly the bound one
        clean = bool(outcome) and sorted(set(outcome["failures"])) == [method] and outcome["errors"] == [] \
            and outcome["skipped"] == []
        passed = attributed and clean and got.returncode != 0
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}", flush=True)
        if not passed:
            print(got.stdout[-3000:] + got.stderr[-3000:], flush=True)
            return 1
        red += 1
    print(f"test_holdout_digests witnesses: {red}/{len(chosen)} red; registry {len(WITNESSES)}", flush=True)
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
    print(f"test_holdout_digests: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_holdout_digests outcomes: " + json.dumps({"failures": ids(result.failures),
                                                          "errors": ids(result.errors),
                                                          "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
