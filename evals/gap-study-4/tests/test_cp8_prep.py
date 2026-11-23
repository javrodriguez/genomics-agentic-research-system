#!/usr/bin/env python3
"""CP8 prep (Gap Study round 4, lane w8d, ruling W8D-gap4-1): the walk checks in CI and four carried items.

  H1  W8A-R2-2: walk_register --check binds each registered walk's folder to the ONE commit that wrote it. Exactly
      one non-merge commit in HEAD's history touches rehearsals/<walk>/; it is a walk commit (drive.WALK_SUBJECT, one
      parent, changing only that folder and the register, whose entry it adds); HEAD's tree at the folder is the tree
      that commit wrote; and the folder on disk is HEAD's. A shallow history refuses. Cases: the probe (a later
      ordinary commit edits the walk's driver ledger: refused), a later commit forged with the walk subject, a walk
      hand-committed under an ordinary subject, a merge that edits the ledger, an uncommitted edit, a shallow clone.
      Review fold W8D-close-1: the register is append-only over history (W8D-R1-1, W8D-R1-2): every entry a
      walk-subject commit's register lists is listed at HEAD, identical (a later commit editing a walk's reason or
      model, deleting a walk, or deleting and re-adding it refuses), and the register on disk is HEAD's; git is read
      even with an empty register (no walk-subject commit passes, a shallow clone refuses).
      Witnesses: history-unchecked, walk-commits-uncounted, walk-subject-unchecked, head-tree-uncompared,
      disk-unchecked, entry-uncompared, walk-dropped-admitted, register-disk-unchecked.
      Fold W8D-close-2 (W8D-R2-1): both history reads use --full-history, so a merge side git's default
      simplification would prune is still read: a walk dropped by `git merge -s ours` in either direction refuses
      (P4a: the walk on a side branch merged in with -s ours; P4b: a branch merges the walk's main with -s ours and
      main fast-forwards to it). Witness: register-log-simplified.
  A1  W7B-R1-4: the walk driver checks the CLASS of the adapter it builds (exactly
      claude_code_adapter.ClaudeCodeAdapter), not only its self-declared name: an object named claude-code of
      another class, and a subclass, are refused (AdapterIdentityRefused); a later assignment of adapter_for cannot
      lift the check. Fold W8D-close-1 (W8D-R1-3): the class is captured when drive.py is imported, so patching
      claude_code_adapter.ClaudeCodeAdapter later admits nothing, and its module must be claude_code_adapter (a fake
      captured by a drive imported under a patch is refused). Witnesses: adapter-class-unchecked,
      adapter-class-at-call-time, adapter-module-unchecked.
  K1  W7B-R1-5: the take folder's k is Batch's attempt: the walk driver hands TakeRepo a take's records only from
      <root>/takes/<slot>/<attempt>, the attempt TakeRepo.commit_records is called with; a folder whose k is not
      that attempt (a launch refused before its folder, then a restart) is refused, never committed under the
      wrong attempt. Witness: take-k-unbound.
  D1  Q-w8a-1: denials.py is round 3's reader, kept byte for byte (w1a's copy record says identical) and unreachable
      from round 4: no study module imports it or names it, no CI step, checks.d line or freeze-rehearsal command
      runs it, and the root it reads (transcripts/) is no record root of round 4. Witnesses: denials-imported,
      denials-in-gate.

The CI step itself (W8A-R1-5) is bound by tests/test_ci_job.py's contract (R38.command for walk_register --check;
its mutation walk-step-removed).

Fakes and synthetic strings only: no walk, model, vendor, network, container runtime, credential or holdout. The
process guard and the scratch repositories are test_box_integration's (setUpModule): every process start is refused
except `git -C <scratch>`.

--mutant NAME compiles one altered module (or swaps one read text) in memory before the bound test runs; --witnesses
runs every registered mutant in its own process, only its bound test, and requires that test to fail by an
AssertionError carrying its clause token, with no error (rule B).
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_box_integration as tbi  # noqa: E402

SELECTED = None
EDITS: tuple = ()          # the drive.py edits of the selected witness (A1 compiles a fresh drive with them)
MODS: dict = {}
TEXTS: dict = {}          # path -> text a witness swaps in (D1's accessor)
LANE = "w8d-cp8-prep"


def mutants():
    """name -> (clause, target, old text, new text). target is a module name, or "text:<study-relative path>" for a
    read text. Each weakens one guard; old must occur exactly once."""
    return {
        "history-unchecked": ("H1.walk-history", "walk_register",
                              "            problems = history_problems(base, walks, repo)   # W8A-R2-2\n", ""),
        "walk-commits-uncounted": ("H1.walk-history", "walk_register",
                                   # 4e0d64ac: a later commit is admitted only as a recheck or regrade commit
                                   "        if not commits or bad_later:", "        if False:"),
        "walk-subject-unchecked": ("H1.walk-history", "walk_register",
                                   "        if subject != drive.WALK_SUBJECT:", "        if False:"),
        "head-tree-uncompared": ("H1.walk-history", "walk_register",
                                 # 4e0d64ac: the trees are compared without the walk's recheck files
                                 "        if at_head is None or at_head != at_walk:", "        if False:"),
        "disk-unchecked": ("H1.walk-history", "walk_register",
                           "        if dirty:", "        if False:"),
        "entry-uncompared": ("H1.walk-history", "walk_register",
                             "            elif now != entry:", "            elif False:"),
        "walk-dropped-admitted": ("H1.walk-history", "walk_register",
                                  "            if now is None:", "            if False:"),
        "register-log-simplified": ("H1.walk-history", "walk_register",
                                    # the register entries' log (4e0d64ac's rechecks log spells the same call)
                                    '"--full-history", "--no-merges", "--format=%H%x1f%s", "HEAD", "--", reg_rel)\n'
                                    '    if log.returncode != 0:',
                                    '"--no-merges", "--format=%H%x1f%s", "HEAD", "--", reg_rel)\n'
                                    '    if log.returncode != 0:'),
        "register-disk-unchecked": ("H1.walk-history", "walk_register",
                                    "    if reg_dirty:", "    if False:"),
        # Re-anchored after c35fc915 (one table, PRODUCTION_ADAPTERS, for the three harnesses): the equivalent sites
        # are the class and module comparisons of adapter_class_problems against the class captured at import.
        "adapter-class-at-call-time": ("A1.adapter-class", "drive",
                                       "type(adapter) is not expected[0] or",
                                       "type(adapter) is not getattr(sys.modules[expected[1]], "
                                       "expected[0].__name__) or"),
        "adapter-module-unchecked": ("A1.adapter-class", "drive",
                                     " or type(adapter).__module__ != expected[1]:",
                                     ":"),
        "adapter-class-unchecked": ("A1.adapter-class", "drive",
                                    "            adapter_class_problems(adapter)          # W7B-R1-4\n", ""),
        "take-k-unbound": ("K1.take-k", "drive",
                           "            take_k_problems(self.records_root, row, attempt, take)    # W7B-R1-5\n",
                           "            pass\n"),
        "denials-imported": ("D1.round3-only", "text:result.py", "", "import denials\n"),
        "denials-in-gate": ("D1.round3-only", "text:checks.d/w8d-cp8-prep.txt", "",
                            "python3 -B -W ignore evals/gap-study-4/denials.py --check\n"),
    }


def compile_module(name: str, source: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(HERE / f"{name}.py")
    sys.modules[name] = mod
    exec(compile(source, mod.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


PRIOR = {}


def setUpModule():
    tbi.setUpModule()
    MODS["drive"] = tbi.drive
    # lane gap-prebeacon-fix3: the real modules a compiled witness may replace, so tearDownModule puts back the
    # same objects; popping walk_register left walk_plan's copy and sys.modules' copy apart for every later module of
    # the single-process round (athena gap4-prebeacon3-49c93d2, test_walk_counts WC7)
    for name in ("walk_register", "mode_binding", "claude_code_adapter", "freeze_rehearsal"):
        MODS[name] = PRIOR[name] = __import__(name)     # the real module, put back by tearDownModule
    if SELECTED is None:
        return
    _, target, old, new = mutants()[SELECTED]
    if target.startswith("text:"):
        path = HERE / target[len("text:"):]
        TEXTS[path] = path.read_text() + new         # an added line: the anchor is the file's end
        return
    path = HERE / f"{target}.py"
    text = path.read_text()
    assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
    if target == "drive":
        global EDITS
        EDITS = ((old, new),)
        MODS["drive"] = tbi.witness_module(EDITS)
    else:
        MODS[target] = compile_module(target, text.replace(old, new))


def tearDownModule():
    # A compiled witness never outlives this module: each name gets back the real module setUpModule imported. A
    # module absent before setUpModule stays loaded afterwards, the real one (review 2f99816 NIT 1).
    sys.modules.update(PRIOR)
    tbi.tearDownModule()


def read_text(path: Path) -> str:
    """The accessor D1 reads every text through (a witness swaps what it returns)."""
    return TEXTS.get(path) or path.read_text()


class Case(unittest.TestCase):
    def must(self, clause, fn, *args, **kwargs):
        """fn(*args, **kwargs), or a failure of `clause` naming what it raised: an interface the slice must provide
        that is missing is a red by assertion, never an error."""
        try:
            return fn(*args, **kwargs)
        except AssertionError:
            raise
        except (Exception, SystemExit) as e:  # noqa: BLE001
            self.fail(f"{clause}: {type(e).__name__}: {str(e)[:300]}")


# ------------------------------------------------------------------------------------------------- H1
def an_entry(walk="w-0001") -> dict:
    d = json.loads((HERE / "prereg-draft.json").read_text())
    task = d["tasks"][0]["id"]
    halves = list(json.loads((HERE / "tasks" / f"{task}.json").read_text())["halves"])
    return {"walk": walk, "task": task, "half": halves[0], "wording": d["tasks"][0]["wordings"][0], "arm": "A",
            "model": d["models"]["A"][-1], "reason": "synthetic: a fake walk for the CP8 history binding",
            "counted": False}


def write_walk(walks: Path, entry: dict) -> Path:
    """A fake walk folder: driver ledger, transcript, launch record, evidence ledger, grade."""
    folder = walks / entry["walk"]
    (folder / "evidence").mkdir(parents=True)
    ledger = {"kind": "take", "task": entry["task"], "half": entry["half"], "wording": entry["wording"],
              "arm": entry["arm"], "model_requested": entry["model"], "pressure": None, "repeat": 1,
              "agent": {"harness": "claude-code", "version": "0.0.1"}, "project": "run-0000abcd",
              "first_agent_turn": True, "outcome": "complete"}
    (folder / "driver-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    (folder / "transcript.jsonl").write_text(json.dumps({"type": "user", "message": "synthetic"}) + "\n")
    (folder / "launch.json").write_text("{}\n")
    (folder / "evidence" / "ledger.jsonl").write_text("{}\n")
    (folder / "grade.json").write_text(json.dumps({"graded": False, "why": "synthetic"}) + "\n")
    (folder / "check.json").write_text(json.dumps({"walk": entry["walk"], "checker_reasons": []}) + "\n")  # W10, D1
    return folder


class Study:
    """A scratch repository laid out as a study (root = repo): rehearsals/README.md and an empty register committed,
    then one walk committed by drive.WalkRepo (the real road)."""

    def __init__(self, stack, *, walk=True):
        self.root = stack.enter_context(tbi.scratch_repo())
        self.walks = self.root / MODS["mode_binding"].WALKS_DIR
        self.walks.mkdir()
        (self.walks / "README.md").write_text("synthetic\n")
        (self.walks / "register.json").write_text('{\n  "schema": 1,\n  "walks": []\n}\n')
        self.git("add", "--", self.walks.name)
        self.git("commit", "-q", "-m", "Add the synthetic register")
        self.entry = an_entry()
        if walk:
            write_walk(self.walks, self.entry)
            self.walk_repo().commit_walk(self.entry)

    def walk_repo(self):
        return MODS["drive"].WalkRepo(runtime=types.SimpleNamespace(run=lambda *a, **k: None),
                                      secrets=lambda: [("token", tbi.TOKEN)], rules_scanner=lambda paths: [],
                                      root=self.root, repo=self.root, design=MODS["walk_register"].design_in_force())

    def git(self, *args) -> str:
        return tbi.git(self.root, *args)

    def check(self, root=None) -> tuple[int, str]:
        root = self.root if root is None else root
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = MODS["walk_register"].main(["--check", "--base", str(Path(root) / self.walks.name),
                                               "--repo", str(root)])
        return code, out.getvalue()


class H1WalkHistory(Case):
    OK = "ok: 1 registered walk(s), each with its folder, none counted"

    def refused(self, study, why, root=None, line=r"(?m)^FAIL walk 'w-0001'"):
        code, out = self.must("H1.walk-history", study.check, root)
        self.assertEqual(code, 1, f"H1.walk-history: {why} passed: {out}")
        self.assertRegex(out, line, f"H1.walk-history: {why}: {out}")

    def test_a_walk_folder_is_its_walk_commit(self):
        drive = MODS["drive"]
        # the walk as WalkRepo committed it passes
        with contextlib.ExitStack() as stack:
            s = Study(stack)
            self.assertEqual(s.git("log", "-1", "--format=%s"), drive.WALK_SUBJECT, "H1.walk-history")
            code, out = self.must("H1.walk-history", s.check)
            self.assertEqual((code, out.strip()), (0, self.OK), "H1.walk-history")
        # THE PROBE (W8A-R2-2): a later ordinary commit edits the walk's driver ledger
        with contextlib.ExitStack() as stack:
            s = Study(stack)
            ledger = s.walks / "w-0001" / "driver-ledger.json"
            ledger.write_text(ledger.read_text().replace('"complete"', '"refused before turn 1"'))
            s.git("commit", "-q", "-am", "Tidy a ledger")
            self.refused(s, "a later ordinary commit that rewrote the walk's ledger")
        # a later ordinary commit edits the ledger and the next one reverts it: HEAD's tree is the walk's again,
        # so only the history (one walk commit, then recheck or regrade commits only) refuses it
        with contextlib.ExitStack() as stack:
            s = Study(stack)
            ledger = s.walks / "w-0001" / "driver-ledger.json"
            original = ledger.read_text()
            ledger.write_text(original.replace('"complete"', '"refused before turn 1"'))
            s.git("commit", "-q", "-am", "Tidy a ledger")
            ledger.write_text(original)
            s.git("commit", "-q", "-am", "Untidy a ledger")
            self.refused(s, "a later ordinary commit that rewrote the walk's ledger, then a revert")
        # a later commit forged with the walk subject, touching the folder and the register as a walk commit does
        with contextlib.ExitStack() as stack:
            s = Study(stack)
            ledger = s.walks / "w-0001" / "driver-ledger.json"
            ledger.write_text(ledger.read_text().replace('"complete"', '"refused before turn 1"'))
            reg = s.walks / "register.json"
            reg.write_text(reg.read_text() + "\n")
            s.git("commit", "-q", "-am", drive.WALK_SUBJECT)
            self.refused(s, "a second commit under the walk subject")
        # a walk committed by hand under an ordinary subject, never by WalkRepo
        with contextlib.ExitStack() as stack:
            s = Study(stack, walk=False)
            write_walk(s.walks, s.entry)
            (s.walks / "register.json").write_text(json.dumps({"schema": 1, "walks": [s.entry]}, indent=2) + "\n")
            s.git("add", "--", s.walks.name)
            s.git("commit", "-q", "-m", "Add a walk")
            self.refused(s, "a walk committed by hand under an ordinary subject")
        # a merge that edits the ledger (no non-merge commit after the walk touches it)
        with contextlib.ExitStack() as stack:
            s = Study(stack)
            s.git("checkout", "-q", "-b", "side")
            (s.root / "README").write_text("synthetic scratch repository, side\n")
            s.git("commit", "-q", "-am", "Side work")
            s.git("checkout", "-q", "-")
            s.git("merge", "-q", "--no-ff", "--no-commit", "side")
            ledger = s.walks / "w-0001" / "driver-ledger.json"
            ledger.write_text(ledger.read_text().replace('"complete"', '"refused before turn 1"'))
            s.git("add", "--", ledger.relative_to(s.root).as_posix())
            s.git("commit", "-q", "-m", "Merge side")
            self.assertEqual(len(s.git("log", "-1", "--format=%P").split()), 2, "H1.walk-history: no merge made")
            self.refused(s, "a merge commit that rewrote the walk's ledger")
        # an edit on disk, never committed
        with contextlib.ExitStack() as stack:
            s = Study(stack)
            (s.walks / "w-0001" / "grade.json").write_text('{"graded": true}\n')
            self.refused(s, "an uncommitted edit in the walk folder")
        # W8D-R1-1: a later ordinary commit rewrites the walk's register entry (its reason, its model)
        for field, value in (("reason", "synthetic: a reason rewritten after the walk"), ("model", None)):
            with contextlib.ExitStack() as stack:
                s = Study(stack)
                reg = json.loads((s.walks / "register.json").read_text())
                if value is None:
                    models = json.loads((HERE / "prereg-draft.json").read_text())["models"]["A"]
                    value = next(m for m in models if m != s.entry["model"])
                reg["walks"][0][field] = value
                (s.walks / "register.json").write_text(json.dumps(reg, indent=2) + "\n")
                s.git("commit", "-q", "-am", "Tidy the register")
                self.refused(s, f"a later commit that rewrote the walk's {field}")
        # W8D-R1-2: the register is append-only; a later commit deletes the walk (folder and entry)
        with contextlib.ExitStack() as stack:
            s = Study(stack)
            s.git("rm", "-q", "-r", "--", f"{s.walks.name}/w-0001")
            (s.walks / "register.json").write_text('{\n  "schema": 1,\n  "walks": []\n}\n')
            s.git("commit", "-q", "-am", "Drop a walk")
            self.refused(s, "a later commit that deleted the walk")
        # ... and deletes it, then re-adds it through WalkRepo with another reason
        with contextlib.ExitStack() as stack:
            s = Study(stack)
            s.git("rm", "-q", "-r", "--", f"{s.walks.name}/w-0001")
            (s.walks / "register.json").write_text('{\n  "schema": 1,\n  "walks": []\n}\n')
            s.git("commit", "-q", "-am", "Drop a walk")
            write_walk(s.walks, s.entry)
            s.walk_repo().commit_walk(dict(s.entry, reason="synthetic: re-added under another reason"))
            self.refused(s, "a walk deleted and re-added")
        # W8D-R2-1 (P4b): a walk on main; a branch from before it merges main with -s ours; main fast-forwards to it
        with contextlib.ExitStack() as stack:
            s = Study(stack)
            main = s.git("branch", "--show-current")
            s.git("checkout", "-q", "-b", "side", "HEAD~1")
            (s.root / "README").write_text("synthetic scratch repository, side\n")
            s.git("commit", "-q", "-am", "Side work")
            s.git("merge", "-q", "-s", "ours", "--no-edit", main)
            s.git("checkout", "-q", main)
            s.git("merge", "-q", "--ff-only", "side")
            self.assertFalse((s.walks / "w-0001").exists(), "H1.walk-history: P4b kept the walk")
            self.refused(s, "a walk dropped by a branch that merged main with -s ours (P4b)")
        # W8D-R2-1 (P4a): a walk committed on a side branch, merged into main with -s ours
        with contextlib.ExitStack() as stack:
            s = Study(stack, walk=False)
            main = s.git("branch", "--show-current")
            s.git("checkout", "-q", "-b", "side")
            write_walk(s.walks, s.entry)
            s.walk_repo().commit_walk(s.entry)
            s.git("checkout", "-q", main)
            s.git("merge", "-q", "-s", "ours", "--no-ff", "--no-edit", "side")
            self.assertFalse((s.walks / "w-0001").exists(), "H1.walk-history: P4a kept the walk")
            self.refused(s, "a side branch's walk merged into main with -s ours (P4a)")
        # an uncommitted edit of the register on disk
        with contextlib.ExitStack() as stack:
            s = Study(stack)
            reg = json.loads((s.walks / "register.json").read_text())
            reg["walks"][0]["reason"] = "synthetic: edited on disk only"
            (s.walks / "register.json").write_text(json.dumps(reg, indent=2) + "\n")
            self.refused(s, "an uncommitted edit of the register",
                         line=rf"(?m)^FAIL {MODS['mode_binding'].WALKS_DIR}/register\.json on disk differs from HEAD")
        # an empty register with no walk-subject commit in history passes, said out loud, git read
        with contextlib.ExitStack() as stack:
            s = Study(stack, walk=False)
            code, out = self.must("H1.walk-history", s.check)
            self.assertEqual(code, 0, f"H1.walk-history: {out}")
            self.assertRegex(out, r"(?m)^ok, having registered 0 walks: ", "H1.walk-history")
            shallow = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve() / "shallow"
            s.git("commit", "-q", "--allow-empty", "-m", "Later work")
            tbi.git(s.root, "clone", "-q", "--depth", "1", f"file://{s.root}", str(shallow))
            code, out = self.must("H1.walk-history", s.check, shallow)
            self.assertEqual(code, 1, f"H1.walk-history: a shallow clone with an empty register passed: {out}")
            self.assertIn("shallow", out, "H1.walk-history")
        # a shallow clone cannot show the walk's commit
        with contextlib.ExitStack() as stack:
            s = Study(stack)
            s.git("commit", "-q", "--allow-empty", "-m", "Later work")
            shallow = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve() / "shallow"
            tbi.git(s.root, "clone", "-q", "--depth", "1", f"file://{s.root}", str(shallow))
            self.assertEqual(tbi.git(shallow, "rev-parse", "--is-shallow-repository"), "true", "H1.walk-history")
            code, out = self.must("H1.walk-history", s.check, shallow)
            self.assertEqual(code, 1, f"H1.walk-history: a shallow clone passed: {out}")
            self.assertIn("shallow", out, "H1.walk-history")


# ------------------------------------------------------------------------------------------------- A1, K1
class Posing:
    """An adapter of another class that declares the production adapter's own name."""
    name = None


def build_walk_driver(drive, factory, root):
    """walk_driver on fakes only, with claude_code_adapter_for answering `factory` (the adapter maker)."""
    mb = MODS["mode_binding"]
    with mock.patch.object(drive, "claude_code_adapter_for", lambda **kw: factory), \
            mock.patch.object(mb, "HERE", Path(root)):
        return drive.walk_driver(
            runtime=types.SimpleNamespace(run=lambda *a, **k: None), root=str(root),
            config_parent=str(tbi.SCRATCH), spec_for=lambda r, c: None, sidecar_for=lambda r, e: None, proxy=None,
            lock_path="/synthetic.lock", hosts={}, login_file="/synthetic-login", counters_for=lambda t: {},
            pin_for=lambda r: {}, design_for=lambda r, t: None, project_for=lambda r: "run-0000abcd",
            identity_for=lambda r: {}, secrets=lambda: [], rules_scanner=lambda p: [], uid_map=[], budget_s=1,
            finalize_wait_s=1, poll_s=1, clock=lambda: 0.0, sleep=lambda s: None,
            ownership=tbi.FakeOwnership(), settings_guard=tbi.FakeSettingsGuard(), machine_gate=lambda: [])


class A1AdapterClass(Case):
    def test_walk_driver_checks_the_adapter_class(self):
        drive, cc = MODS["drive"], MODS["claude_code_adapter"]
        Posing.name = cc.ClaudeCodeAdapter.name
        real = object.__new__(cc.ClaudeCodeAdapter)       # the production class, never started here

        class Subclass(cc.ClaudeCodeAdapter):
            pass
        sub = object.__new__(Subclass)
        made = {"adapter": real}
        root = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve()
        drv = self.must("A1.adapter-class", build_walk_driver, drive, lambda row, take: made["adapter"], root)
        row = {"agent": {"harness": cc.ClaudeCodeAdapter.name}}
        self.assertIs(self.must("A1.adapter-class", drv.adapter_for, row, None), real, "A1.adapter-class")
        for posing, why in ((Posing(), "an object of another class named claude-code"), (sub, "a subclass")):
            made["adapter"] = posing
            try:
                drv.adapter_for(row, None)
                self.fail(f"A1.adapter-class: {why} was accepted by the walk driver")
            except AssertionError:
                raise
            except drive.AdapterIdentityRefused as e:
                self.assertIn("class", str(e), "A1.adapter-class")
            except Exception as e:  # noqa: BLE001
                self.fail(f"A1.adapter-class: {why}: {type(e).__name__}: {e}")
        # a later assignment cannot lift the check
        drv.adapter_for = lambda row, take: Posing()
        with self.assertRaises(drive.AdapterIdentityRefused, msg="A1.adapter-class: a reassigned maker"):
            drv.adapter_for(row, None)
        # W8D-R1-3: patching the module attribute after drive was imported admits nothing, even a fake that
        # claims the production module's name
        Disguised = type("ClaudeCodeAdapter", (), {"__module__": "claude_code_adapter",
                                                   "name": cc.ClaudeCodeAdapter.name})
        made["adapter"] = Disguised()
        drv.adapter_for = lambda row, take: made["adapter"]
        with mock.patch.object(cc, "ClaudeCodeAdapter", Disguised):
            with self.assertRaises(drive.AdapterIdentityRefused, msg="A1.adapter-class: a patched class"):
                drv.adapter_for(row, None)
        # and a drive imported under a patch captured a class from another module: refused by its module
        made["adapter"] = Posing()
        with mock.patch.object(cc, "ClaudeCodeAdapter", Posing):
            fresh = self.must("A1.adapter-class", tbi.witness_module, EDITS)
        drv2 = self.must("A1.adapter-class", build_walk_driver, fresh, lambda row, take: made["adapter"], root)
        with self.assertRaises(fresh.AdapterIdentityRefused, msg="A1.adapter-class: a class captured from __main__"):
            drv2.adapter_for(row, None)


class K1TakeK(Case):
    def test_take_folder_k_is_batch_attempt(self):
        drive, mb = MODS["drive"], MODS["mode_binding"]
        root = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve()
        drv = self.must("K1.take-k", build_walk_driver, drive, lambda row, take: None, root)
        row = {"slot": "s-k"}
        # the production take folder: k is the next unused folder (take_folder_in), here 1
        folder = drv.take_folder(row)
        self.assertEqual(folder, str(root / mb.TAKES_DIR / "s-k" / "1"), "K1.take-k")
        os.makedirs(folder)
        Path(folder, "launch.json").write_text("{}\n")
        drv._by_slot["s-k"] = drive._Take(row, folder, str(root / "cfg"))
        got = self.must("K1.take-k", drv.record_files, row, 1)
        self.assertEqual(got, [(str(Path(folder, "launch.json")), "launch")], "K1.take-k")
        # Batch's attempt 2 (attempt 1 refused before its folder was made, then a restart): folder 1 is refused
        try:
            drv.record_files(row, 2)
            self.fail("K1.take-k: a take in takes/s-k/1 was handed over as attempt 2")
        except AssertionError:
            raise
        except drive.DriveRefused as e:
            self.assertIn("attempt 2", str(e), "K1.take-k")
        except Exception as e:  # noqa: BLE001
            self.fail(f"K1.take-k: {type(e).__name__}: {e}")
        # a folder outside takes/<slot>/ (a walk folder, another slot, another root) is refused for any attempt
        for other in (root / mb.WALKS_DIR / "w-0001", root / mb.TAKES_DIR / "s-other" / "1",
                      root / "elsewhere" / mb.TAKES_DIR / "s-k" / "1"):
            drv._by_slot["s-k"] = drive._Take(row, str(other), str(root / "cfg"))
            with self.assertRaises(drive.DriveRefused, msg=f"K1.take-k: {other}"):
                drv.record_files(row, 1)


# ------------------------------------------------------------------------------------------------- D1
def study_modules() -> dict:
    """{study-relative path: text} for every non-test .py of round 4, denials.py itself aside."""
    out = {}
    for path in sorted(HERE.rglob("*.py")):
        rel = path.relative_to(HERE).as_posix()
        if rel.startswith("tests/") or rel == "denials.py" or "__pycache__" in rel:
            continue
        out[rel] = read_text(path)
    return out


def names_denials(text: str) -> bool:
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(a.name.split(".")[-1] == "denials" for a in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[-1] == "denials":
            return True
        if isinstance(node, ast.ImportFrom) and any(a.name == "denials" for a in node.names):
            return True
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and \
                (node.value == "denials" or re.search(r"(?<![\w.-])denials\.py(?![\w])", node.value)):
            return True       # importlib.import_module("denials"), __import__("denials"), a path to the file
    return False


class D1Denials(Case):
    def test_denials_is_round3_only_and_unreachable(self):
        mb = MODS["mode_binding"]
        # the mark: the copy record holds denials.py as round 3's file, byte for byte
        frag = json.loads((HERE / "COPIED.d" / "w1a-cp1-scaffold.json").read_text())
        entry = [e for e in frag["files"] if e["path"] == "denials.py"]
        self.assertEqual(entry, [{"path": "denials.py", "status": "identical",
                                  "source": "evals/gap-study-3/denials.py"}], "D1.round3-only")
        self.assertIn("evals/gap-study-3/denials.py --check", (HERE / "denials.py").read_text(), "D1.round3-only")
        # no study module imports or names it
        named = sorted(rel for rel, text in study_modules().items() if names_denials(text))
        self.assertEqual(named, [], "D1.round3-only: round 4 modules reach denials.py")
        # no gate runs it: the CI job, every checks.d line, the freeze rehearsal's commands
        ci = read_text(REPO / ".github" / "workflows" / "ci.yml")
        job = ci[ci.index("  gap-study-4:\n"):]
        gates = {"ci.yml": job}
        for path in sorted((HERE / "checks.d").glob("*.txt")):
            gates[f"checks.d/{path.name}"] = read_text(path)
        gates["freeze_rehearsal.COMMANDS"] = "\n".join(" ".join(c) for c in MODS["freeze_rehearsal"].COMMANDS)
        ran = sorted(name for name, text in gates.items() if "denials.py" in text)
        self.assertEqual(ran, [], "D1.round3-only: a gate runs denials.py")
        # the root it reads is no record root of round 4, and the round 3 road that wrote it is shadowed
        self.assertNotIn("transcripts", mb.RECORD_ROOTS, "D1.round3-only")
        drive = MODS["drive"]
        self.assertIsNot(drive.main, drive.ROUND3_ONLY["main"], "D1.round3-only")


BOUND = {"H1.walk-history": "H1WalkHistory.test_a_walk_folder_is_its_walk_commit",
         "A1.adapter-class": "A1AdapterClass.test_walk_driver_checks_the_adapter_class",
         "K1.take-k": "K1TakeK.test_take_folder_k_is_batch_attempt",
         "D1.round3-only": "D1Denials.test_denials_is_round3_only_and_unreachable"}
WITNESSES = {name: (BOUND[clause], clause) for name, (clause, _, _, _) in mutants().items()}


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_cp8_prep witnesses", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()),
                                    *sorted({WITNESSES[x][0] for x in chosen})], timeout=1800, tag="test_cp8_prep")
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=110)
        record = re.findall(r"^test_cp8_prep outcomes: (\{.*\})$", got.stdout, re.M)
        outcome = json.loads(record[-1]) if record else None
        blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", got.stderr,
                            re.M | re.S)
        attributed = any(f"{cls}.{test}" == method and "AssertionError" in body and
                         re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w.-])", body)
                         for test, cls, body in blocks)
        clean = bool(outcome) and outcome["failures"] == [method] and outcome["errors"] == [] \
            and outcome["skipped"] == []
        passed = attributed and clean and got.returncode != 0
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}", flush=True)
        if not passed:
            print(got.stdout[-3000:] + got.stderr[-3000:], flush=True)
            return 1
        red += 1
    print(f"test_cp8_prep witnesses: {red}/{len(chosen)} red; registry {len(WITNESSES)}", flush=True)
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
    print(f"test_cp8_prep: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_cp8_prep outcomes: " + json.dumps({"failures": ids(result.failures), "errors": ids(result.errors),
                                                   "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
