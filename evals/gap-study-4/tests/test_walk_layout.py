#!/usr/bin/env python3
"""The walk layout (Gap Study round 4, lane w8a, ruling W8-layout-1: Option A of walk-layout-options-2026-10-12).

One walk is one folder, rehearsals/<walk>/, holding a take folder's records plus grade.json; WalkRepo commits it with
its register entry in one scanned commit, before the freeze only; the record roots are named once, in mode_binding;
run.py grades take folders only; the copy record claims a walk's files through the register; the rehearsal gate runs
the walk checks. Each clause below is the options file's test of the same number.

  L1  one name: no study module spells a record root as a path except mode_binding.py, and every round 3 root that
      remains is named in EXEMPT with its reason; round 3's host road (drive.main, drive.route_attempt) is shadowed
      by refusals and nothing calls the originals. Witness: leak-grep-own-root.
  L2  walk folder: walk_driver(records="walks") gives rehearsals/<walk>/ (an existing folder or a bad id refused),
      records="takes" keeps takes/<slot>/<k>, any other value refuses. Witness: walk-folder-under-takes.
  L3  time fence: WalkRepo refuses once prereg.json exists; TakeRepo's registration still refuses before the freeze.
      Witness: freeze-unchecked.
  L4  one commit: a fake walk's folder and its register entry land in ONE commit through scan_record (a planted token
      masked), and walk_register --check then says "ok: 1 registered walk(s)"; a folder without its entry, or an
      entry without its folder, fails. Witness: register-in-another-commit.
  L5  never results: run.grade_committed refuses a record_dir under rehearsals/ (and admits one under takes/);
      stats.load_results reads 0 records from a tree holding one walk. Witness: binding-to-the-study.
  L6  grade bound: run.walk_problems regrades every registered walk and fails when grade.json differs by one byte, for
      a graded walk and a walk with no first turn. Witness: regrade-uncompared.
  L7  copy record: a registered walk's files are claimed with no fragment, an unregistered walk folder's are not, and
      a fragment claiming a record path is refused. Witnesses: record-claims-dropped, unregistered-claimed,
      fragment-record-admitted.
  L8  lint: records under takes/ and rehearsals/<walk>/ are not linted as prose; register.json's reason is.
      Witness: take-roots-respelled (W7B-R1-3's own regression).
  L9  readers agree: mode_binding --walks, fixture_walk, build_cases and leak_grep each read exactly the one walk's
      transcript (never a nested decoy, never none). Witness: walks-read-two-levels.
  L10 content rule: walk_register --check fails a walk folder holding a file outside the closed map or lacking
      driver-ledger.json or grade.json. Witness: content-rule-skipped.
  L11 gates wired: freeze_rehearsal.COMMANDS holds the four walk checks, each script present. Witness:
      gate-dropped. (freeze_rehearsal.py itself runs on the remote runner, never as a Mac gate.)

Fakes and synthetic strings only: no walk, model, vendor, network, container runtime, credential or holdout. The
process guard and the scratch repositories are test_box_integration's (setUpModule): every process start is refused
except `git -C <scratch>`, and L7 alone admits git on this repository for copy_manifest's own reads.

--mutant NAME compiles one altered module in memory before the bound test runs; --witnesses runs every registered
mutant in its own process, only its bound test, and requires that test to fail by an AssertionError carrying its
clause token, with no error (rule B).
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import prereg  # noqa: E402
import takes  # noqa: E402
import test_box_integration as tbi  # noqa: E402

REAL_LOAD, REAL_REQUIRE = prereg.load, prereg.require_frozen      # captured before tbi patches them
SELECTED = None
MODS: dict = {}
SOURCES: dict = {}
NAMES = ("mode_binding", "walk_register", "run", "copy_manifest", "lint_language", "fixture_walk", "build_cases",
         "leak_grep", "freeze_rehearsal")


def mutants():
    """name -> (clause, module, old text, new text). Each weakens one guard; old must occur exactly once."""
    return {
        "leak-grep-own-root": ("L1.one-name", "leak_grep",
                               "ROOTS = mode_binding.RECORD_ROOTS", "ROOTS = (\"takes\", \"rehearsals\")"),
        "walk-folder-under-takes": ("L2.walk-folder", "drive",
                                    "    base = Path(root).resolve() / WALKS_DIR\n",
                                    "    base = Path(root).resolve() / TAKES_DIR\n"),
        "freeze-unchecked": ("L3.time-fence", "drive",
                             "        if os.path.lexists(self.root / FROZEN_NAME):", "        if False:"),
        "register-in-another-commit": ("L4.one-commit", "drive",
                                       "        declared[reg_rel] = WALK_REGISTER_KIND\n", ""),
        "binding-to-the-study": ("L5.never-results", "run",
                                 "    if path == takes_root or not path.is_relative_to(takes_root):",
                                 "    if not path.is_relative_to(HERE.resolve()):"),
        "regrade-uncompared": ("L6.grade-bound", "run", "        if again != stored:", "        if False:"),
        "record-claims-dropped": ("L7.copy-record", "copy_manifest",
                                  "    by_record = record_claims(present, committed_records() if records is None "
                                  "else records)", "    by_record = set()"),
        "unregistered-claimed": ("L7.copy-record", "copy_manifest",
                                 "if root == mode_binding.WALKS_DIR and parts[1] in records[\"walks\"]:",
                                 "if root == mode_binding.WALKS_DIR:"),
        "fragment-record-admitted": ("L7.copy-record", "copy_manifest",
                                     "        if record_root_of(path) is not None:            # W8A",
                                     "        if False:            # W8A"),
        "take-roots-respelled": ("L8.lint", "lint_language", "TAKE_ROOTS = mode_binding.RECORD_ROOTS",
                                 "TAKE_ROOTS = (\"transcripts\", \"rehearsals\", \"pauses\")"),
        "walks-read-two-levels": ("L9.readers-agree", "mode_binding",
                                  "        return record_transcripts(base, WALKS_DIR)",
                                  "        return sorted((base / WALKS_DIR).glob(\"*/*/transcript.jsonl\"))"),
        "content-rule-skipped": ("L10.content", "walk_register",
                                 "            problems = content_problems(base, [e[\"walk\"] for e in registered(base)])",
                                 "            problems = []"),
        "freeze-at-head-unchecked": ("L3.time-fence", "drive",
                                     "        self._refuse_frozen_at(head, \"the commit the walk would follow\")"
                                     "          # W8A-R1-1: HEAD\n", ""),
        "cell-from-grade-unchecked": ("L6.grade-bound", "run", "    if cell is not None and cell != recorded:",
                                      "    if False:"),
        "take-folder-depth-unchecked": ("L5.never-results", "run",
                                        "    if len(inside) != mode_binding.RECORD_DEPTH[mode_binding.TAKES_DIR] or \\",
                                        "    if False and \\"),
        "module-constant-root": ("L1.one-name", "leak_grep", "ROOTS = mode_binding.RECORD_ROOTS",
                                 "ROOTS = mode_binding.RECORD_ROOTS\nWALKS_HOME = \"rehearsals/\""),
        "history-unchecked": ("L3.time-fence", "drive",
                              "        self._refuse_ever_frozen(head)                                            "
                              "# W8A-R2-1: any ancestor\n", ""),
        "slot-defaulted": ("L5.never-results", "run",
                           "            inside != (str(row[\"slot\"]), str(row[\"attempt\"])):",
                           "            inside != (str(row.get(\"slot\")), str(row.get(\"attempt\"))):"),
        "cell-level-unchecked": ("L6.grade-bound", "run",
                                 "    if (recorded[\"repeat\"] is None) == (recorded[\"pressure\"] is None):",
                                 "    if False:"),
        "bare-root-constant": ("L1.one-name", "leak_grep", "ROOTS = mode_binding.RECORD_ROOTS",
                               "ROOTS = mode_binding.RECORD_ROOTS\nWALKS_NAME: str = \"rehearsals\""),
        "gate-dropped": ("L11.gates", "freeze_rehearsal",
                         "    (\"fixture_walk.py\", \"--check\"), (\"run.py\", \"--walks\", \"--check\"),",
                         "    (\"fixture_walk.py\", \"--check\"),"),
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
    for name in NAMES:
        MODS[name] = PRIOR[name] = __import__(name)     # the real module, put back by tearDownModule
    if SELECTED is not None:
        _, target, old, new = mutants()[SELECTED]
        path = HERE / f"{target}.py"
        text = path.read_text()
        assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
        SOURCES[path] = text.replace(old, new)
        if target == "drive":
            MODS["drive"] = tbi.witness_module(((old, new),))
        else:
            MODS[target] = compile_module(target, SOURCES[path])


def tearDownModule():
    # A compiled witness never outlives this module (lane gap-prebeacon-fix3, review 90c1fd9 NIT 4): each name gets back
    # the real module setUpModule imported, never dropped, so later modules keep one copy of each (test_cp8_prep's
    # pattern). A module absent before setUpModule stays loaded afterwards, the real one (review 2f99816 NIT 1).
    sys.modules.update(PRIOR)
    tbi.tearDownModule()


def source_of(path: Path) -> str:
    """The accessor L1 reads a module's text through (a witness swaps what it returns)."""
    return SOURCES.get(path) or path.read_text()


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


# ------------------------------------------------------------------------------------------------- the fixtures
TOKEN = tbi.TOKEN


def design() -> dict:
    return MODS["walk_register"].design_in_force()


def an_entry(walk="w-0001", **over) -> dict:
    d = json.loads((HERE / "prereg-draft.json").read_text())
    task = d["tasks"][0]["id"]
    halves = list(json.loads((HERE / "tasks" / f"{task}.json").read_text())["halves"])
    entry = {"walk": walk, "task": task, "half": halves[0], "wording": d["tasks"][0]["wordings"][0], "arm": "A",
             "model": d["models"]["A"][-1], "reason": "synthetic: a fake walk for the layout's tests",
             "counted": False}
    entry.update(over)
    return entry


def a_ledger(entry, first_turn=True) -> dict:
    return {"kind": "take", "task": entry["task"], "half": entry["half"], "wording": entry["wording"],
            "arm": entry["arm"], "model_requested": entry["model"],
            "pressure": None, "repeat": 1,
            "agent": {"harness": "claude-code", "version": "0.0.1"}, "project": "run-0000abcd",
            "first_agent_turn": first_turn, "outcome": "complete" if first_turn else "refused before turn 1"}


def write_walk(walks: Path, entry: dict, *, first_turn=True, grade=True, extra=None, decoy=False) -> Path:
    """A fake walk folder: driver ledger, transcript (with a planted token), launch record, evidence ledger, grade."""
    folder = walks / entry["walk"]
    (folder / "evidence").mkdir(parents=True)
    (folder / "driver-ledger.json").write_text(json.dumps(a_ledger(entry, first_turn), indent=2) + "\n")
    (folder / "transcript.jsonl").write_text(json.dumps({"type": "user", "permissionMode": "default",
                                                         "message": f"synthetic {TOKEN}"}) + "\n")
    (folder / "launch.json").write_text("{}\n")
    (folder / "evidence" / "ledger.jsonl").write_text("{}\n")
    if grade:
        (folder / "grade.json").write_text(json.dumps({"graded": False, "why": "synthetic"}) + "\n")
    (folder / "check.json").write_text(json.dumps({"walk": entry["walk"], "checker_reasons": []}) + "\n")  # W10, D1
    if decoy:            # a session-folder file of the same name: a record, never a second session
        (folder / "session").mkdir()
        (folder / "session" / "transcript.jsonl").write_text("{}\n")
    for name, text in (extra or {}).items():
        (folder / name).write_text(text)
    return folder


def a_study(entries=(), **kw) -> Path:
    """A synthetic study folder: rehearsals/ with README.md and a register listing `entries`, each with its folder."""
    base = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve()
    walks = base / "rehearsals"
    walks.mkdir()
    (walks / "README.md").write_text("synthetic\n")
    (walks / "register.json").write_text(json.dumps({"schema": 1, "walks": list(entries)}, indent=2) + "\n")
    for e in entries:
        write_walk(walks, e, **kw)
    return base


def fake_grade(row, folder):
    return {"label": "synthetic-label", "views": {"strict": "right"}, "graded_by": "graders/synthetic.py",
            "seen": json.loads((Path(folder) / "driver-ledger.json").read_text())["outcome"]}


def check_out(base: Path) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = MODS["walk_register"].main(["--check", "--base", str(base / "rehearsals")])
    return code, out.getvalue()


# ------------------------------------------------------------------------------------------------- L1
ROOT_NAMES = ("walks", "transcripts", "pauses", "rehearsals", "takes")
# (study-relative file, its top-level scope) -> why a record-root spelling stays there. Each must still be found.
EXEMPT = {
    ("drive.py", "main"): "round 3's CLI (--walk, --row), kept byte for byte and shadowed by a refusal (L1 below)",
    ("drive.py", "route_attempt"): "round 3's router, kept byte for byte and shadowed by a refusal (L1 below)",
    ("fixture_walk.py", "round2_caps"): "round 2's own rehearsal folder, another study's committed record",
    ("build_cases.py", "CARRIED_SOURCES"): "the first study's committed transcripts, another study's folder",
    ("awareness_furniture.py", "ROUND3_TRANSCRIPTS"): "round 3's committed transcripts, another study's folder",
    ("round2.py", "TRANSCRIPTS"): "round 2's committed transcripts, another study's folder",
    ("graders/pause_adherence.py", "stopped_round3"): "round 3's committed takes, another study's folder",
    ("template_offer_reading.py", "TASK_DIR"): "the earlier rounds' committed transcripts (gap-study, gap-study-2, "
                                                "gap-study-3), other studies' folders",
    ("denials.py", "graded_transcripts"): "round 3's take layout under this study, which nothing in round 4 writes "
                                          "(drive's round 3 road is shadowed); out of this slice (CP7), named as "
                                          "Q-w8a-1",
}


def scope_of(tree: ast.Module, node: ast.AST) -> str:
    for top in tree.body:
        if getattr(top, "lineno", 0) <= node.lineno <= getattr(top, "end_lineno", 0):
            if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return top.name
            if isinstance(top, ast.Assign) and isinstance(top.targets[0], ast.Name):
                return top.targets[0].id
            return f"line {top.lineno}"
    return "?"


def root_spellings(rel: str, text: str) -> set:
    """Every place `text` spells a record root as a path: `x / "<root>"` (or "<root>/..."), a tuple or list of root
    names only, or a glob/rglob/Path argument starting with one. (rel, scope) per site."""
    tree = ast.parse(text)
    first_defs: dict = {}
    for top in tree.body:              # round 3's first definitions (drive.py redefines main and route_attempt)
        if isinstance(top, ast.FunctionDef):
            first_defs.setdefault(top.name, top)
    sites = set()

    def is_root_text(node) -> bool:          # W8A-R2-4: "<root>" itself or "<root>/..."
        return (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and any(node.value == r or node.value.startswith(r + "/") for r in ROOT_NAMES))

    def is_root(node) -> bool:
        return (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and any(node.value == r or node.value.startswith(r + "/") for r in ROOT_NAMES))
    for top in tree.body:              # W8A-R1-4: a module-level path constant joined later through its name
        if isinstance(top, (ast.Assign, ast.AnnAssign)) and top.value is not None and is_root_text(top.value):
            sites.add((rel, scope_of(tree, top)))
    for node in ast.walk(tree):
        hit = False
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and is_root(node.right):
            hit = True
        elif isinstance(node, (ast.Tuple, ast.List)) and node.elts and all(
                isinstance(e, ast.Constant) and e.value in ROOT_NAMES for e in node.elts):
            hit = True
        elif isinstance(node, ast.Call) and node.args and is_root(node.args[0]) and (
                getattr(node.func, "attr", None) in ("glob", "rglob") or getattr(node.func, "id", None) == "Path"):
            hit = True
        if hit:
            sites.add((rel, scope_of(tree, node)))
    return sites


def study_modules() -> list[Path]:
    return sorted(p for p in HERE.rglob("*.py")
                  if "tests" not in p.relative_to(HERE).parts and "__pycache__" not in p.parts)


class L1OneName(Case):
    def test_record_roots_are_named_once(self):
        found = set()
        for path in study_modules():
            rel = path.relative_to(HERE).as_posix()
            if rel == "mode_binding.py":
                continue
            found |= root_spellings(rel, source_of(path))
        unexplained = sorted(found - set(EXEMPT))
        self.assertEqual(unexplained, [], f"L1.one-name: a module spells a record root itself: {unexplained}")
        stale = sorted(set(EXEMPT) - found)
        self.assertEqual(stale, [], f"L1.one-name: an exemption no longer matches anything: {stale}")
        mb = MODS["mode_binding"]
        self.assertEqual(tuple(self.must("L1.one-name", getattr, mb, "RECORD_ROOTS")), ("takes", "rehearsals"),
                         "L1.one-name")
        self.assertTrue(set(self.must("L1.one-name", getattr, mb, "ROUND3_ROOTS")).isdisjoint(mb.RECORD_ROOTS),
                        "L1.one-name")
        drive = MODS["drive"]
        self.assertEqual(drive.WALKS_DIR if hasattr(drive, "WALKS_DIR") else None, mb.WALKS_DIR, "L1.one-name")
        for name in ("leak_grep", "lint_language"):
            self.assertEqual(tuple(getattr(MODS[name], "ROOTS" if name == "leak_grep" else "TAKE_ROOTS")),
                             mb.RECORD_ROOTS, f"L1.one-name: {name}")

    def test_round_3_road_is_unreachable(self):
        drive = MODS["drive"]
        originals = self.must("L1.unreachable", getattr, drive, "ROUND3_ONLY")
        self.assertEqual(sorted(originals), ["main", "route_attempt"], "L1.unreachable")
        self.assertIsNot(drive.main, originals["main"], "L1.unreachable: drive.main is round 3's CLI")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = self.must("L1.unreachable", lambda: drive.main())
        self.assertEqual(code, 2, "L1.unreachable")
        self.assertIn("walk_driver(records='walks')", err.getvalue(), "L1.unreachable")
        with self.assertRaises(drive.DriveRefused, msg="L1.unreachable"):
            drive.route_attempt(Path("/nonexistent"), {}, [], "t", "h", "m")
        # by AST: only round 3's own (first) main calls route_attempt, and main is called only under __main__
        tree = ast.parse((HERE / "drive.py").read_text())
        first_main = next(t for t in tree.body if isinstance(t, ast.FunctionDef) and t.name == "main")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "route_attempt":
                self.assertTrue(first_main.lineno <= node.lineno <= first_main.end_lineno,
                                f"L1.unreachable: route_attempt called at drive.py:{node.lineno}")
        for path in study_modules():          # by AST (code, never prose): no other module names the road
            if path.name == "drive.py":
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
                hit = name in ("route_attempt", "ROUND3_ONLY") or (
                    name == "main" and isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id in ("drive", "_drive"))
                self.assertFalse(hit, f"L1.unreachable: {path.name}:{getattr(node, 'lineno', '?')} reaches round 3's "
                                      f"road")


# ------------------------------------------------------------------------------------------------- L2
class L2WalkFolder(Case):
    def test_walk_folder_by_records(self):
        drive, mb = MODS["drive"], MODS["mode_binding"]
        root = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve()
        walk = self.must("L2.walk-folder", lambda: drive.record_folder_in(root, "walks"))
        self.assertEqual(walk({"walk": "w-0001"}), str(root / mb.WALKS_DIR / "w-0001"), "L2.walk-folder")
        (root / mb.WALKS_DIR / "w-0002").mkdir(parents=True)
        for bad in ({"walk": "w-0002"}, {"walk": "a/b"}, {"walk": ""}, {"walk": None}, {"slot": "s1"}):
            with self.assertRaises(drive.DriveRefused, msg=f"L2.walk-folder {bad}"):
                walk(bad)
        take = drive.record_folder_in(root, "takes")
        self.assertEqual(take({"slot": "s1"}), str(root / mb.TAKES_DIR / "s1" / "1"), "L2.walk-folder")
        for bad in ("rehearsals", "takes/", None, ""):
            with self.assertRaises(drive.DriveRefused, msg=f"L2.walk-folder {bad!r}"):
                drive.record_folder_in(root, bad)

    def test_walk_driver_takes_records(self):
        drive, mb = MODS["drive"], MODS["mode_binding"]
        seen = {}

        def build(records):
            with mock.patch.object(drive, "WalkDriver", lambda **kw: kw):
                kw = dict(runtime=types.SimpleNamespace(run=lambda *a, **k: None), root=str(mb.HERE),
                          config_parent="/synthetic", spec_for=None, sidecar_for=None, proxy=None, lock_path="/x",
                          hosts={}, login_file="/x", counters_for=None, pin_for=None, design_for=lambda r, t: None,
                          project_for=None, identity_for=None, secrets=None, rules_scanner=None, uid_map=[],
                          budget_s=1, finalize_wait_s=1, poll_s=1, clock=None, sleep=None)
                if records is not None:
                    kw["records"] = records
                return drive.walk_driver(**kw)
        seen["walks"] = self.must("L2.walk-folder", build, "walks")["take_folder"]({"walk": "w-9999"})
        seen["default"] = self.must("L2.walk-folder", build, None)["take_folder"]({"slot": "s-x"})
        self.assertEqual(seen["walks"], str(mb.HERE / mb.WALKS_DIR / "w-9999"), "L2.walk-folder")
        self.assertEqual(seen["default"], str(mb.HERE / mb.TAKES_DIR / "s-x" / "1"), "L2.walk-folder")
        with self.assertRaises(drive.DriveRefused, msg="L2.walk-folder"):
            build("graded")


# ------------------------------------------------------------------------------------------------- L3, L4
class Repo:
    """A scratch repository laid out as a study (root = repo): rehearsals/README.md and an empty register committed."""

    def __init__(self, stack):
        self.root = stack.enter_context(tbi.scratch_repo())
        self.walks = self.root / "rehearsals"
        self.walks.mkdir()
        (self.walks / "README.md").write_text("synthetic\n")
        (self.walks / "register.json").write_text('{\n  "schema": 1,\n  "walks": []\n}\n')
        tbi.git(self.root, "add", "--", "rehearsals")
        tbi.git(self.root, "commit", "-q", "-m", "Add the synthetic register")
        self.base = tbi.git(self.root, "rev-parse", "HEAD")

    def walk_repo(self, drive):
        return drive.WalkRepo(runtime=types.SimpleNamespace(run=lambda *a, **k: None),
                              secrets=lambda: [("token", TOKEN)], rules_scanner=lambda paths: [],
                              root=self.root, repo=self.root, design=design())

    def changed(self, commit) -> list:
        return sorted(tbi.git(self.root, "diff-tree", "-r", "--name-only", "--no-commit-id", commit).splitlines())


class L3TimeFence(Case):
    def test_walks_before_the_freeze_takes_after(self):
        drive = MODS["drive"]
        with contextlib.ExitStack() as stack:
            r = Repo(stack)
            entry = an_entry()
            write_walk(r.walks, entry)
            (r.root / "prereg.json").write_text("{}\n")
            repo = self.must("L3.time-fence", r.walk_repo, drive)
            try:
                repo.commit_walk(entry)
                self.fail("L3.time-fence: a walk was committed with prereg.json present")
            except AssertionError:
                raise
            except drive.CommitRefused as e:
                self.assertIn("prereg.json", str(e), "L3.time-fence")
            except Exception as e:  # noqa: BLE001
                self.fail(f"L3.time-fence: {type(e).__name__}: {e}")
            self.assertEqual(tbi.git(r.root, "rev-parse", "HEAD"), r.base, "L3.time-fence")
            self.assertEqual(json.loads((r.walks / "register.json").read_text())["walks"], [], "L3.time-fence")
        # W8A-R1-1: a freeze committed at HEAD and deleted on disk only is still a freeze, read at HEAD
        with contextlib.ExitStack() as stack:
            r = Repo(stack)
            (r.root / "prereg.json").write_text("{}\n")
            tbi.git(r.root, "add", "--", "prereg.json")
            tbi.git(r.root, "commit", "-q", "-m", "Freeze (synthetic)")
            frozen = tbi.git(r.root, "rev-parse", "HEAD")
            entry = an_entry()
            write_walk(r.walks, entry)
            os.remove(r.root / "prereg.json")
            try:
                r.walk_repo(drive).commit_walk(entry)
                self.fail("L3.time-fence: a walk was committed on top of a committed freeze")
            except AssertionError:
                raise
            except drive.CommitRefused as e:
                self.assertIn("the commit the walk would follow", str(e), f"L3.time-fence: {e}")
            except Exception as e:  # noqa: BLE001
                self.fail(f"L3.time-fence: {type(e).__name__}: {e}")
            self.assertEqual(tbi.git(r.root, "rev-parse", "HEAD"), frozen, "L3.time-fence")
            self.assertEqual(tbi.git(r.root, "diff", "--cached", "--name-only"), "", "L3.time-fence")
            self.assertEqual(json.loads((r.walks / "register.json").read_text())["walks"], [], "L3.time-fence")
        # W8A-R2-1: a freeze committed and then removed by a commit is still in the history: refused
        with contextlib.ExitStack() as stack:
            r = Repo(stack)
            (r.root / "prereg.json").write_text("{}\n")
            tbi.git(r.root, "add", "--", "prereg.json")
            tbi.git(r.root, "commit", "-q", "-m", "Freeze (synthetic)")
            tbi.git(r.root, "rm", "-q", "--", "prereg.json")
            tbi.git(r.root, "commit", "-q", "-m", "Unfreeze (synthetic)")
            unfrozen = tbi.git(r.root, "rev-parse", "HEAD")
            entry = an_entry()
            write_walk(r.walks, entry)
            try:
                r.walk_repo(drive).commit_walk(entry)
                self.fail("L3.time-fence: a walk was committed after a freeze that a later commit removed")
            except AssertionError:
                raise
            except drive.CommitRefused as e:
                self.assertIn("history", str(e), f"L3.time-fence: {e}")
            except Exception as e:  # noqa: BLE001
                self.fail(f"L3.time-fence: {type(e).__name__}: {e}")
            self.assertEqual(tbi.git(r.root, "rev-parse", "HEAD"), unfrozen, "L3.time-fence")
        # TakeRepo stays post-freeze: registration needs the frozen pre-registration (this study has none)
        # lane fold10/rehearsal-road: a walk tree is unfrozen by this document, so the check also holds in a frozen clone
        unfrozen_pre = lambda: dict(REAL_LOAD(), _frozen=False)      # noqa: E731
        with mock.patch.object(prereg, "load", unfrozen_pre), mock.patch.object(prereg, "require_frozen", REAL_REQUIRE):
            with self.assertRaises(SystemExit, msg="L3.time-fence"):
                takes.commit_registration(tbi.row(), 1, root=HERE, repo=HERE.parent.parent)


class L4OneCommit(Case):
    def test_one_walk_one_commit(self):
        drive = MODS["drive"]
        with contextlib.ExitStack() as stack:
            r = Repo(stack)
            entry = an_entry()
            folder = write_walk(r.walks, entry)
            repo = self.must("L4.one-commit", r.walk_repo, drive)
            got = self.must("L4.one-commit", lambda: repo.commit_walk(entry))
            head = tbi.git(r.root, "rev-parse", "HEAD")
            self.assertEqual(got["commit"], head, "L4.one-commit")
            self.assertEqual(tbi.git(r.root, "rev-parse", "HEAD~1"), r.base, "L4.one-commit: more than one commit")
            files = sorted(p.relative_to(r.root).as_posix() for p in folder.rglob("*") if p.is_file())
            self.assertEqual(r.changed(head), sorted(files + ["rehearsals/register.json"]), "L4.one-commit")
            self.assertEqual(tbi.git(r.root, "log", "-1", "--format=%s"), "Commit one walk; never counted",
                             "L4.one-commit")
            committed = json.loads(tbi.git(r.root, "show", "HEAD:rehearsals/register.json"))
            self.assertEqual(committed["walks"], [entry], "L4.one-commit")
            self.assertNotIn(TOKEN, tbi.git(r.root, "show", "HEAD:rehearsals/w-0001/transcript.jsonl"),
                             "L4.one-commit: the planted token was committed unmasked")
            self.assertEqual(tbi.git(r.root, "status", "--porcelain"), "", "L4.one-commit")
            code, out = check_out(r.root)
            self.assertEqual((code, out.strip()), (0, "ok: 1 registered walk(s), each with its folder, none counted"),
                             "L4.one-commit")
            # a folder without its entry, and an entry without its folder, fail the register check
            write_walk(r.walks, an_entry("w-0002"))
            self.assertEqual(check_out(r.root)[0], 1, "L4.one-commit")
            shutil.rmtree(r.walks / "w-0002")
            reg = json.loads((r.walks / "register.json").read_text())
            (r.walks / "register.json").write_text(json.dumps(dict(reg, walks=reg["walks"] + [an_entry("w-0003")])))
            self.assertEqual(check_out(r.root)[0], 1, "L4.one-commit")
            # the same walk id again is refused, and nothing moves
            (r.walks / "register.json").write_text(tbi.git(r.root, "show", "HEAD:rehearsals/register.json") + "\n")
            with self.assertRaises(drive.CommitRefused, msg="L4.one-commit"):
                repo.commit_walk(entry)
            self.assertEqual(tbi.git(r.root, "rev-parse", "HEAD"), head, "L4.one-commit")


# ------------------------------------------------------------------------------------------------- L5, L6
class Reached(Exception):
    pass


class L5NeverResults(Case):
    def test_a_walk_folder_is_never_graded_into_results(self):
        run = MODS["run"]

        def git_at(repo, *args, **kw):
            return "" if args[0] == "status" else "tracked"
        with mock.patch.object(run.takes, "_git_at", git_at), \
                mock.patch.object(run.variants, "load_task", side_effect=Reached("graded")):
            for record_dir in ("rehearsals/w-0001", "rehearsals/w-0001/", "rehearsals", "takes/../rehearsals/w-1",
                               "takes", "artifacts/s1", "takes/s1", "takes/s1/1/evidence", "takes/s2/1", "takes/s1/2"):
                try:
                    run.grade_committed({"record_dir": record_dir, "task": "synthetic-task", "slot": "s1",
                                         "attempt": 1}, {})
                    self.fail(f"L5.never-results: {record_dir} returned a grade")
                except Reached:
                    self.fail(f"L5.never-results: {record_dir} reached the grader")
                except ValueError as e:
                    self.assertIn("take folder", str(e), f"L5.never-results: {record_dir}: {e}")
            for missing in ("slot", "attempt"):            # W8A-R2-3: a row without its slot or attempt raises
                row = {"record_dir": "takes/None/1" if missing == "slot" else "takes/s1/None",
                       "task": "synthetic-task", "slot": "s1", "attempt": 1}
                del row[missing]
                try:
                    run.grade_committed(row, {})
                    self.fail(f"L5.never-results: a row without {missing} returned a grade")
                except KeyError:
                    pass
                except Reached:
                    self.fail(f"L5.never-results: a row without {missing} reached the grader")
                except ValueError as e:
                    self.fail(f"L5.never-results: a row without {missing} was read as None: {e}")
            with self.assertRaises(Reached, msg="L5.never-results: a take folder no longer reaches the grader"):
                run.grade_committed({"record_dir": "takes/s1/1", "task": "synthetic-task", "slot": "s1",
                                     "attempt": 1}, {})
        base = a_study([an_entry()])
        stats = sys.modules.get("stats") or __import__("stats")
        self.assertEqual(stats.load_results(base / "records"), [], "L5.never-results")


class L6GradeBound(Case):
    def test_grade_json_is_the_regrade(self):
        run = MODS["run"]
        graded, dead = an_entry("w-0001"), an_entry("w-0002")
        base = a_study([graded], grade=False)
        write_walk(base / "rehearsals", dead, first_turn=False, grade=False)
        reg = base / "rehearsals" / "register.json"
        reg.write_text(json.dumps({"schema": 1, "walks": [graded, dead]}, indent=2) + "\n")
        cell = {"pressure": None, "repeat": 1}
        for e in (graded, dead):
            self.must("L6.grade-bound", lambda e=e: run.write_walk_grade(e, base / "rehearsals" / e["walk"],
                                                                         cell if e is graded else None, fake_grade))
        doc = json.loads((base / "rehearsals" / "w-0001" / "grade.json").read_text())
        self.assertEqual((doc["graded"], doc["grade"]["label"], doc["row"]["repeat"]), (True, "synthetic-label", 1),
                         "L6.grade-bound")
        self.assertIs(json.loads((base / "rehearsals" / "w-0002" / "grade.json").read_text())["graded"], False,
                      "L6.grade-bound")
        self.assertEqual(self.must("L6.grade-bound", lambda: run.walk_problems(base, fake_grade)), ([], 2), "L6.grade-bound")
        for walk in ("w-0001", "w-0002"):
            path = base / "rehearsals" / walk / "grade.json"
            good = path.read_bytes()
            path.write_bytes(good.replace(b"\n}", b" \n}", 1))          # one byte more, the JSON unchanged
            bad, n = run.walk_problems(base, fake_grade)
            self.assertEqual(n, 2, "L6.grade-bound")
            self.assertTrue(any(walk in b and "differs from regrading" in b for b in bad), f"L6.grade-bound {bad}")
            path.write_bytes(good)
        self.assertEqual(run.walk_problems(base, fake_grade), ([], 2), "L6.grade-bound")
        # W8A-R1-2: the cell is the driver ledger's; grade.json can never supply another
        folder = base / "rehearsals" / "w-0001"
        try:
            run.write_walk_grade(graded, folder, {"pressure": "invented-pressure", "repeat": 1}, fake_grade)
            self.fail("L6.grade-bound: a grade was written under a cell the walk's driver did not record")
        except AssertionError:
            raise
        except ValueError as e:
            self.assertIn("driver ledger records", str(e), "L6.grade-bound")
        path = folder / "grade.json"
        good = path.read_bytes()
        doc = json.loads(good)
        doc["row"]["pressure"] = "invented-pressure"
        path.write_bytes(run.walk_grade_bytes(doc))
        bad, _ = run.walk_problems(base, fake_grade)
        self.assertTrue(any("w-0001" in b and "driver ledger records" in b for b in bad), f"L6.grade-bound {bad}")
        path.write_bytes(good)
        ledger = json.loads((folder / "driver-ledger.json").read_text())
        (folder / "driver-ledger.json").write_text(json.dumps({k: v for k, v in ledger.items() if k != "pressure"}))
        bad, _ = run.walk_problems(base, fake_grade)
        self.assertTrue(any("records no pressure" in b for b in bad), f"L6.grade-bound {bad}")
        for pressure, repeat in ((None, None), (True, 1)):        # W8A-R2-4: exactly one of them is None
            (folder / "driver-ledger.json").write_text(json.dumps(dict(ledger, pressure=pressure, repeat=repeat)))
            bad, _ = run.walk_problems(base, fake_grade)
            self.assertTrue(any("exactly one of them is None" in b for b in bad), f"L6.grade-bound {bad}")


# ------------------------------------------------------------------------------------------------- L7
class L7CopyRecord(Case):
    WALK_FILES = ("rehearsals/w-0001/driver-ledger.json", "rehearsals/w-0001/grade.json",
                  "rehearsals/w-0001/evidence/ledger.jsonl")

    def test_record_claims(self):
        cm = MODS["copy_manifest"]
        present = set(self.WALK_FILES) | {"rehearsals/w-0002/grade.json", "rehearsals/README.md",
                                          "rehearsals/register.json", "takes/s1/1/transcript.jsonl",
                                          "takes/s1/2/transcript.jsonl", "drive.py"}
        got = self.must("L7.copy-record", lambda: cm.record_claims(present, {"walks": {"w-0001"}, "takes": {("s1", "1")}}))
        self.assertEqual(got, set(self.WALK_FILES) | {"takes/s1/1/transcript.jsonl"}, "L7.copy-record")

    def test_the_manifest_reads_the_register(self):
        cm = MODS["copy_manifest"]
        with mock.patch.object(subprocess, "run", tbi._REAL["run"]), \
                mock.patch.object(subprocess, "Popen", tbi._REAL["Popen"]):   # copy_manifest reads this repo's git
            present = cm.files_here() | set(self.WALK_FILES) | {"rehearsals/w-0002/grade.json"}

            def read(path):                 # the synthetic walk's files exist only in `present`
                return b"{}\n" if path.startswith("rehearsals/w-") else cm.read_copy(path)

            def mine(bad):
                return sorted(b for b in bad if "rehearsals/w-" in b)
            # Lane freeze-gates-fix S12 (athena's battery on 12e021d3): files_here() holds the committed walks since
            # the merges, so every register handed in here carries the committed register's walks too (the registered
            # state); the synthetic w-0001 and w-0002 are what each leg varies.
            committed = {e["walk"] for e in json.loads((HERE / "rehearsals" / "register.json").read_text())["walks"]}
            self.assertTrue(committed, "L7.copy-record")
            listed = mine(self.must("L7.copy-record", cm.problems, present=present, read=read,
                                    records={"walks": {"w-0001"} | committed, "takes": set()}))
            self.assertEqual(listed, ["rehearsals/w-0002/grade.json is under evals/gap-study-4/ and no fragment in "
                                      "COPIED.d/ claims it"], "L7.copy-record")
            unlisted = mine(cm.problems(present=present, read=read, records={"walks": set(committed), "takes": set()}))
            self.assertEqual(len(unlisted), 4, f"L7.copy-record {unlisted}")
            folder = Path(tempfile.mkdtemp(dir=tbi.SCRATCH))
            for frag in cm.FRAGMENTS.glob("*.json"):
                (folder / frag.name).write_text(frag.read_text())
            (folder / "synthetic-lane.json").write_text(json.dumps({"lane": "synthetic-lane", "files": [
                {"path": "rehearsals/w-0001/grade.json", "status": "new", "reason": "synthetic"}]}))
            bad = cm.problems(folder, present=present, read=read, records={"walks": {"w-0001"} | committed,
                                                                           "takes": set()})
            self.assertTrue(any(b.startswith("rehearsals/w-0001/grade.json (synthetic-lane) is inside a record folder")
                                for b in bad), f"L7.copy-record {mine(bad)}")


# ------------------------------------------------------------------------------------------------- L8
class L8Lint(Case):
    def test_records_are_not_prose_and_the_register_is(self):
        lint = MODS["lint_language"]
        base = a_study([an_entry(reason="this walk always holds")],
                       extra={"scrub.json": json.dumps({"note": "always"}) + "\n"})
        (base / "rehearsals" / "w-0001" / "grade.json").write_text('{"why": "always"}\n')
        take = base / "takes" / "s1" / "1"
        take.mkdir(parents=True)
        for name in ("driver-ledger.json", "environment.json", "operator-check.json"):
            (take / name).write_text(json.dumps({"outcome": "always complete"}) + "\n")
        scanned = [f.relative_to(base).as_posix() for f in lint.iter_files([str(base)])]
        self.assertIn("rehearsals/register.json", scanned, "L8.lint")
        self.assertIn("rehearsals/README.md", scanned, "L8.lint")
        records = [s for s in scanned if s.startswith(("takes/", "rehearsals/w-"))]
        self.assertEqual(records, [], f"L8.lint: records linted as prose: {records}")
        entries = lint.load_allowlist()
        found = [f for p in scanned for f in lint.scan_text((base / p).read_text(), p, entries)]
        self.assertTrue(any(f["file"] == "rehearsals/register.json" and f["pattern"] == "always" for f in found),
                        f"L8.lint {found}")


# ------------------------------------------------------------------------------------------------- L9
class L9ReadersAgree(Case):
    def test_each_reader_reads_the_one_walk(self):
        entry = an_entry()
        base = a_study([entry], decoy=True)
        want = [base / "rehearsals" / "w-0001" / "transcript.jsonl"]
        mb, fw, bc, lg = (MODS[n] for n in ("mode_binding", "fixture_walk", "build_cases", "leak_grep"))
        got = {
            "mode_binding --walks": self.must("L9.readers-agree", lambda: mb.attempts(True, base)),
            "fixture_walk": self.must("L9.readers-agree", lambda: fw.committed_walks(base)),
            "build_cases": self.must("L9.readers-agree", lambda: bc.walk_transcripts(entry["task"], base)),
            "leak_grep": self.must("L9.readers-agree", lambda: lg.sessions(base)),
        }
        for reader, paths in got.items():
            self.assertEqual([Path(p) for p in paths], want, f"L9.readers-agree: {reader} read {paths}")
        self.assertEqual(self.must("L9.readers-agree", lambda: fw.registered_walks(base))[0][0]["half"], entry["half"],
                         "L9.readers-agree")


# ------------------------------------------------------------------------------------------------- L10
class L10Content(Case):
    def test_a_walk_folder_holds_only_records(self):
        base = a_study([an_entry()])
        self.assertEqual(check_out(base), (0, "ok: 1 registered walk(s), each with its folder, none counted\n"),
                         "L10.content")
        folder = base / "rehearsals" / "w-0001"
        for change, undo in (
                (lambda: (folder / "notes.txt").write_text("x\n"), lambda: (folder / "notes.txt").unlink()),
                (lambda: (folder / "grade.json").rename(folder / "g"), lambda: (folder / "g").rename(folder / "grade.json")),
                (lambda: (folder / "driver-ledger.json").rename(folder / "d"),
                 lambda: (folder / "d").rename(folder / "driver-ledger.json"))):
            change()
            code, out = check_out(base)
            self.assertEqual(code, 1, f"L10.content {out}")
            self.assertIn("content rule", out, "L10.content")
            undo()
        self.assertEqual(check_out(base)[0], 0, "L10.content")


# ------------------------------------------------------------------------------------------------- L11
class L11Gates(Case):
    WALK_CHECKS = (("walk_register.py", "--check"), ("mode_binding.py", "--walks", "--check"),
                   ("fixture_walk.py", "--check"), ("run.py", "--walks", "--check"))

    def test_the_rehearsal_runs_the_walk_checks(self):
        commands = MODS["freeze_rehearsal"].COMMANDS
        for command in self.WALK_CHECKS:
            self.assertIn(command, commands, f"L11.gates: {command}")
            self.assertTrue((HERE / command[0]).is_file(), f"L11.gates: {command[0]}")


BOUND = {"L1.one-name": "L1OneName.test_record_roots_are_named_once",
         "L2.walk-folder": "L2WalkFolder.test_walk_folder_by_records",
         "L3.time-fence": "L3TimeFence.test_walks_before_the_freeze_takes_after",
         "L4.one-commit": "L4OneCommit.test_one_walk_one_commit",
         "L5.never-results": "L5NeverResults.test_a_walk_folder_is_never_graded_into_results",
         "L6.grade-bound": "L6GradeBound.test_grade_json_is_the_regrade",
         "L7.copy-record": "L7CopyRecord.test_the_manifest_reads_the_register",
         "L8.lint": "L8Lint.test_records_are_not_prose_and_the_register_is",
         "L9.readers-agree": "L9ReadersAgree.test_each_reader_reads_the_one_walk",
         "L10.content": "L10Content.test_a_walk_folder_holds_only_records",
         "L11.gates": "L11Gates.test_the_rehearsal_runs_the_walk_checks"}
WITNESSES = {name: (BOUND[clause], clause) for name, (clause, _, _, _) in mutants().items()}
# record-claims-dropped and unregistered-claimed are also caught by L7CopyRecord.test_record_claims; the bound test is
# the manifest's own road.


# One mutant child's limit (lane fold4/records, after gap4-fold4-battery-eefd321's holdout-witness timeout): measured on
# the Mac, 31 Oct 2026, the slowest child took 224 s (fragment-record-admitted), past the old 110 s; 4x that, rounded up.
CHILD_TIMEOUT_S = 900


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_walk_layout witnesses", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()),
                                    *sorted({WITNESSES[x][0] for x in chosen})], timeout=1800, tag="test_walk_layout")
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=CHILD_TIMEOUT_S)
        record = re.findall(r"^test_walk_layout outcomes: (\{.*\})$", got.stdout, re.M)
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
    print(f"test_walk_layout witnesses: {red}/{len(chosen)} red; registry {len(WITNESSES)}", flush=True)
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
    print(f"test_walk_layout: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_walk_layout outcomes: " + json.dumps({"failures": ids(result.failures), "errors": ids(result.errors),
                                                      "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
