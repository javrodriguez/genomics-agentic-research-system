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
        "keys-not-allowed": ("H6.allowed", "freeze", '    "holdout_salted_digests", "holdout_wordings_per_task_version",\n',
                             ""),
        "check-skips-draft": ("H7.check", "freeze", "            problem = draft_holdout_problem(json.loads(DRAFT.read_text()))\n",
                              "            problem = None\n"),
        "rehearsal-silent": ("H8.rehearsal", "freeze", "            print(HOLDOUT_NOT_REHEARSED)\n", "            pass\n"),
    }


def compile_module(name: str, source: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(HERE / f"{name}.py")
    sys.modules[name] = mod
    exec(compile(source, mod.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


def setUpModule():
    for name in ("build_draft", "freeze"):
        MODS[name] = __import__(name)
    if SELECTED is not None:
        _, target, old, new = mutants()[SELECTED]
        text = (HERE / f"{target}.py").read_text()
        assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
        MODS[target] = compile_module(target, text.replace(old, new))
        if target == "build_draft":      # freeze imports build_draft lazily; it must meet the compiled one
            MODS["freeze"] = compile_module("freeze", (HERE / "freeze.py").read_text())


def tearDownModule():
    for name in ("build_draft", "freeze"):  # a compiled witness never outlives this module
        sys.modules.pop(name, None)


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
    def prepare(draft, *, review, parent, pins, frozen_at):
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
        good = fake_source(per_task=3)["salted_sha256"]
        a, z = TASKS
        bad = {"salt": {"salted_sha256": good, "salt": "synthetic-salt"},
               "wordings": {"salted_sha256": good, "wordings": ["synthetic"]},
               "no-digests": {"salt": "synthetic-salt"},
               "repeated key": '{"salted_sha256": %s, "salted_sha256": %s}' % (json.dumps(good), json.dumps(good)),
               "uneven": {"salted_sha256": dict(good, **{z: good[z][:2]})},
               "empty lists": {"salted_sha256": {a: [], z: []}},
               "empty": {"salted_sha256": {}},
               "extra task": {"salted_sha256": dict(good, **{"synthetic-task-c": [fake("c", i) for i in range(3)]})},
               "missing task": {"salted_sha256": {a: good[a]}},
               "repeated digest": {"salted_sha256": dict(good, **{z: [good[a][0]] + good[z][1:]})},
               "upper case": {"salted_sha256": dict(good, **{z: [d.upper() for d in good[z]]})},
               "not json": "synthetic, not json"}
        f = fz()
        self.assertEqual(f.holdout_fields(self.source({"salted_sha256": good}), list(TASKS)),
                         {"holdout_salted_digests": good, "holdout_wordings_per_task_version": 3}, "H5.shape good")
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
        self.assertEqual(code, 0, f"H7.check clean {out}")
        for name, draft in (("digests", dict(synthetic_draft(), holdout_salted_digests="PENDING")),
                            ("count", dict(synthetic_draft(), holdout_wordings_per_task_version=3)),
                            ("rule-count", dict(synthetic_draft(), holdout_rule=dict(RULE, wordings_per_task_version=3)))):
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


BOUND = {"H1.draft": "H1Draft.test_no_pre_freeze_draft_carries_the_holdout",
         "H2.writer": "H2Writer.test_the_writer_refuses_the_freeze_fields",
         "H3.write": "H3Write.test_the_freeze_writes_digests_and_count",
         "H4.absent": "H4Absent.test_the_freeze_refuses_without_its_source",
         "H5.shape": "H5Shape.test_a_malformed_source_is_refused",
         "H6.allowed": "H6Allowed.test_the_fields_are_freeze_written",
         "H7.check": "H7Check.test_check_refuses_a_draft_carrying_the_fields",
         "H8.rehearsal": "H8Rehearsal.test_a_rehearsal_without_a_source_writes_neither_field_and_says_so"}
WITNESSES = {name: (BOUND[clause], clause) for name, (clause, _, _, _) in mutants().items()}


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=110)
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
