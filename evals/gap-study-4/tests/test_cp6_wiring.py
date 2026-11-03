#!/usr/bin/env python3
"""CP6 wiring (Gap Study round 4, lane w9-cp6, glitch-2f's wave 9 ruling under Javier's standing delegation).

  K1  Q-w8d-1, K1-launch: the walk driver checks a take against its records BEFORE launch, never only at the commit
      after a paid run. WalkDriver.launch refuses (drive.LaunchRefused) before any take folder, config folder or
      container exists and before run_take.launch is reached, so nothing is spent. For a take (records "takes"): the
      slot's one open registration in the committed takes.json (registered, no committed outcome); every field of the
      allow-list drive.LAUNCH_FIELDS (stats.TAKE_FIELDS[:8], slot, half_cell) equal to the row's; the row the frozen
      pre-registration's planned row; the take folder <root>/takes/<slot>/<that attempt> (ruling w9-Q1: the folder is
      the registered attempt, never a count of folders on disk), refused by name when it already exists. Cases: a
      registered planned take passes and reaches run_take.launch; the stuck slot (attempt 1 refused before its folder,
      then attempt 2) launches into takes/<slot>/2; a registered attempt whose folder exists is refused by name; each
      allow-listed field changed, in turn, is refused naming that field; an unregistered slot; a row the frozen rows
      do not plan, and no freeze at all; and through a real batch.Batch with TakeRepo, a take whose folder exists is
      committed failed with drive_started false and nothing launched. Witnesses: launch-unchecked,
      launch-fields-unchecked, launch-prereg-unchecked, launch-folder-counted, launch-folder-exists-admitted,
      launch-unregistered-admitted. Fold w9-close-1 (W9-R1-1): an open attempt 1 under an outcome-closed attempt 2
      (a ledger appended by hand) is refused, the open registration not the slot's latest; witness
      launch-latest-unchecked.
  W1  K1-launch, the walk arm (records "walks"): a walk is refused before launch when prereg.json exists, when its
      task, half, wording, arm or model is not one the design in force admits (walk_register.entry_problems), and when
      its id is already in rehearsals/register.json (casefolded); a walk the design admits passes. Witnesses:
      walk-launch-unchecked, walk-freeze-admitted, walk-design-unchecked, walk-registered-admitted.
  S1  W8B-R2-2: check_results re-applies freeze.synthetic_tasks to the committed prereg.json, as its freeze commit
      wrote it and as it stands: the rehearsal's synthetic holdout digests are refused naming W8B-gap4-1, unless
      --rehearsal-plan (a disposable rehearsal), which prints them NOT CHECKED. Real-looking digests and an absent
      field pass. Witnesses: synthetic-unapplied, synthetic-rehearsal-everywhere, synthetic-now-unread.
  R1  freeze_rehearsal's holdout step, retargeted (S9b landed aegis holdout/tools/holdout.py at 76ec9f5): given
      --holdout-tool, the step runs that tool's --check (never --digests or --make-salt) on the clone's SYNTHETIC
      fixture fixtures/holdout-rehearsal against the clone at its HEAD, and passes when the tool does; without it the
      step stays OWED and the run is not all green; a relative tool, one not named holdout.py, a missing one, and one
      inside this repository are refused before anything runs; the parser has no holdout-folder option and takes no
      abbreviation. Fold w9-close-1: the step is labelled everywhere it is written (the report a freeze records, and
      stdout) "on the synthetic fixture evals/gap-study-4/fixtures/holdout-rehearsal, not the real holdout", so the
      fixture's counts are never read as the real pack's; witness tool-label-dropped. The fixture holds one file per draft task, ids h1-h3, every wording marked synthetic. Witnesses:
      tool-step-skipped, tool-digests, tool-real-folder, tool-in-repo-admitted, tool-owed-anyway.

Fakes and synthetic strings only: no walk, model, vendor, network, container runtime, credential, salt or holdout.
The process guard and scratch repositories are test_box_integration's (setUpModule): every process start is refused
except `git -C <scratch>`. No folder outside the scratch area and this study is read.

--mutant NAME compiles one altered module in memory before the bound test runs; --witnesses runs every registered
mutant in its own process, only its bound test, and requires that test to fail by an AssertionError carrying its
clause token, with no error (rule B).
"""
from __future__ import annotations

import contextlib
import hashlib
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
REPO = HERE.parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import prereg as _prereg  # noqa: E402
import test_box_integration as tbi  # noqa: E402

REAL_PREREG_LOAD = _prereg.load     # W10 (D2): captured before test_box_integration patches it; a walk's identity
                                    # derives its session id from the pre-registered namespace

SELECTED = None
EDITS: tuple = ()
MODS: dict = {}
LANE = "w9-cp6"
FIXTURE = HERE / "fixtures" / "holdout-rehearsal"


def mutants():
    """name -> (clause, target module, old text, new text). Each weakens one guard; old must occur exactly once."""
    return {
        "launch-unchecked": ("K1.launch", "drive",
                             "        folder = launch_problems(self, row)          # W9 K1-launch (Q-w8d-1): before any "
                             "folder, container or spend\n", "        folder = None\n"),
        "launch-fields-unchecked": ("K1.launch", "drive", "    if wrong:\n        raise LaunchRefused(",
                                    "    if False:\n        raise LaunchRefused("),
        "launch-prereg-unchecked": ("K1.launch", "drive", "        takes_mod.require_planned_row(row, pre)\n",
                                    "        pass\n"),
        "launch-folder-counted": ("K1.launch", "drive",
                                  "    folder = root / TAKES_DIR / str(slot) / str(attempt)        # ruling w9-Q1",
                                  "    folder = Path(driver.take_folder(row))        # ruling w9-Q1"),
        "launch-folder-exists-admitted": ("K1.launch", "drive",
                                          "    if os.path.lexists(folder):\n        raise LaunchRefused(f\"{folder} already",
                                          "    if False:\n        raise LaunchRefused(f\"{folder} already"),
        "launch-latest-unchecked": ("K1.launch", "drive",
                                    "    if reg.get(\"attempt\") != max(r.get(\"attempt\") for r in mine):",
                                    "    if False:"),
        "launch-unregistered-admitted": ("K1.launch", "drive", "    if len(open_) != 1:\n",
                                         "    if len(open_) > 1:\n"),
        "walk-launch-unchecked": ("W1.walk-launch", "drive",
                                  "    elif driver.records == \"walks\":\n        walk_launch_problems(driver, row)\n",
                                  "    elif driver.records == \"walks\":\n        pass\n"),
        "walk-freeze-admitted": ("W1.walk-launch", "drive",
                                 "    if os.path.lexists(root / FROZEN_NAME):\n        raise LaunchRefused(",
                                 "    if False:\n        raise LaunchRefused("),
        "walk-design-unchecked": ("W1.walk-launch", "drive",
                                  "    if bad:\n        raise LaunchRefused(\"the walk is not one",
                                  "    if False:\n        raise LaunchRefused(\"the walk is not one"),
        "walk-registered-admitted": ("W1.walk-launch", "drive", "    if row[\"walk\"].casefold() in ids:",
                                     "    if False:"),
        "synthetic-unapplied": ("S1.synthetic", "check_results",
                                "    problems += synthetic_digest_problems(frozen, now, rehearsal_plan)     "
                                "# W8B-R2-2 (lane w9-cp6)\n", ""),
        "synthetic-rehearsal-everywhere": ("S1.synthetic", "check_results", "            if not rehearsal_plan:\n",
                                           "            if False:\n"),
        "synthetic-now-unread": ("S1.synthetic", "check_results",
                                 "(\"the freeze commit's prereg.json\", frozen), (\"prereg.json\", now))",
                                 "(\"the freeze commit's prereg.json\", frozen),)"),
        "tool-step-skipped": ("R1.holdout-tool", "freeze_rehearsal",
                              "            if command == HOLDOUT_GATE and args.holdout_tool is not None:",
                              "            if False:"),
        "tool-digests": ("R1.holdout-tool", "freeze_rehearsal",
                         "str(Path(tool).resolve()), \"--check\",", "str(Path(tool).resolve()), \"--digests\","),
        "tool-real-folder": ("R1.holdout-tool", "freeze_rehearsal",
                             "\"--holdout\", str(Path(clone) / study.rel(HOLDOUT_FIXTURE)),",
                             "\"--holdout\", str(Path(clone)),"),
        "tool-in-repo-admitted": ("R1.holdout-tool", "freeze_rehearsal",
                                  "    if path.resolve().is_relative_to(REPO.resolve()):", "    if False:"),
        "tool-label-dropped": ("R1.holdout-tool", "freeze_rehearsal",
                               "                step(HOLDOUT_STEP_LABEL, holdout_check_command(",
                               "                step(\" \".join(command), holdout_check_command("),
        "tool-owed-anyway": ("R1.holdout-tool", "freeze_rehearsal",
                             "if str(part).endswith(\".py\") and not Path(part).is_absolute()), None)",
                             "if str(part).endswith(\".py\")), None)"),
    }


def compile_module(name: str, source: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(HERE / f"{name}.py")
    sys.modules[name] = mod
    exec(compile(source, mod.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


def setUpModule():
    tbi.setUpModule()
    MODS["drive"] = tbi.drive
    for name in ("check_results", "freeze_rehearsal", "freeze", "takes", "batch", "walk_register", "mode_binding",
                 "study", "prereg", "stats"):
        MODS[name] = __import__(name)
    if SELECTED is None:
        return
    _, target, old, new = mutants()[SELECTED]
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
    for name in ("check_results", "freeze_rehearsal"):
        if SELECTED is not None:
            sys.modules.pop(name, None)       # a compiled witness never outlives this module
    tbi.tearDownModule()


class Case(unittest.TestCase):
    def must(self, clause, fn, *args, **kwargs):
        """fn(*args, **kwargs), or a failure of `clause` naming what it raised (a red by assertion, never an error)."""
        try:
            return fn(*args, **kwargs)
        except AssertionError:
            raise
        except (Exception, SystemExit) as e:  # noqa: BLE001
            self.fail(f"{clause}: {type(e).__name__}: {str(e)[:300]}")

    def refused(self, clause, fn, *args, words=()):
        """fn(*args) must raise drive.LaunchRefused, its message carrying every one of `words`."""
        try:
            fn(*args)
        except AssertionError:
            raise
        except MODS["drive"].LaunchRefused as e:
            for w in words:
                self.assertIn(w, str(e), f"{clause}: the refusal does not name {w!r}: {e}")
            return str(e)
        except (Exception, SystemExit) as e:  # noqa: BLE001
            self.fail(f"{clause}: {type(e).__name__} instead of LaunchRefused: {str(e)[:300]}")
        self.fail(f"{clause}: launched, and it should have been refused before launch ({words})")


# ------------------------------------------------------------------------------------------------- K1, W1 rigs
class Reached(Exception):
    """run_take.launch was reached: the launch got past every pre-launch check (where spend would start)."""


class LaunchSpy:
    def __init__(self):
        self.calls = 0

    def __call__(self, *a, **k):
        self.calls += 1
        raise Reached("run_take.launch reached")


def build_driver(drive, root: Path, records: str, cfg: Path, runtime=None):
    """A WalkDriver on fakes only, its record folder by `records` (drive.record_folder_in, as walk_driver builds it)."""
    return drive.WalkDriver(
        records_root=root, records=records, runtime=runtime or types.SimpleNamespace(run=lambda *a, **k: None),
        take_folder=drive.record_folder_in(root, records), config_parent=str(cfg),
        spec_for=lambda r, c: types.SimpleNamespace(image=tbi.IMAGE, run_tree=str(cfg)),   # read by the fake road
        sidecar_for=lambda r, e: None, proxy=None, lock_path="/synthetic.lock", hosts={},
        adapter_for=lambda r, t: None, script_for=lambda r: [], pin_for=lambda r: {}, checker=lambda r, t, n: {},
        secrets=lambda: [], rules_scanner=lambda p: [], uid_map=[], budget_s=1, finalize_wait_s=1, poll_s=1,
        clock=lambda: 0.0, sleep=lambda s: None, project_for=lambda r: tbi.PROJECT, identity_for=lambda r: {},
        ownership=tbi.FakeOwnership(), settings_guard=tbi.FakeSettingsGuard(), machine_gate=lambda: [])


def register(root: Path, row: dict, attempt: int, rows=None):
    """Through the ledger's own door, committed, against `rows` as the frozen plan (the row alone by default)."""
    MODS["takes"].commit_registration(row, attempt, root=root, repo=root, pre={"rows": list(rows or [row])})


def commit_outcome(root: Path, outcome: dict):
    """One outcome appended to outcomes.json in its own commit (read_history's shape: one record per commit)."""
    path = root / "outcomes.json"
    now = json.loads(path.read_text()) if path.is_file() else []
    path.write_text(json.dumps(now + [outcome], indent=2) + "\n")
    tbi.git(root, "add", "--", "outcomes.json")
    tbi.git(root, "commit", "-q", "-m", "Commit one synthetic outcome")


class Scene:
    """One scratch repository (root = repo), a config parent, a launch spy and a take driver."""

    def __init__(self, stack, records="takes"):
        self.root = stack.enter_context(tbi.scratch_repo())
        self.cfg = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve()
        self.spy = LaunchSpy()
        self.drive = MODS["drive"]
        stack.enter_context(mock.patch.object(self.drive._run_take, "launch", self.spy))
        self.driver = build_driver(self.drive, self.root, records, self.cfg)

    def launch(self, row):
        return self.driver.launch(row)

    def nothing_made(self, case, clause):
        tc = case
        tc.assertEqual(self.spy.calls, 0, f"{clause}: run_take.launch was reached")
        tc.assertFalse((self.root / MODS["mode_binding"].TAKES_DIR).exists() and
                       any((self.root / MODS["mode_binding"].TAKES_DIR).rglob("evidence")),
                       f"{clause}: a take folder was made")
        tc.assertEqual(sorted(os.listdir(self.cfg)), [], f"{clause}: a config folder was made")


CHANGED = {"arm": "Z", "task": "synthetic-other-task", "half": "normal", "model": "synthetic-other-model",
           "agent": {"harness": "claude-code", "version": "9.9.9"}, "wording": "w9", "repeat": 7, "pressure": "high",
           "slot": "s1", "half_cell": "c-other"}


class K1Launch(Case):
    def test_a_take_is_checked_against_its_records_before_launch(self):
        drive, stats = MODS["drive"], MODS["stats"]
        # the allow-list is the identity the ledger and the frozen rows bind, exactly
        self.assertEqual(tuple(self.must("K1.launch", getattr, drive, "LAUNCH_FIELDS")),
                         tuple(stats.TAKE_FIELDS[:8]) + ("slot", "half_cell"), "K1.launch: the allow-list")
        row = tbi.row(1)
        # 1. a registered, planned take passes every check and reaches run_take.launch, in takes/<slot>/1
        with contextlib.ExitStack() as st:
            sc = self.must("K1.launch", Scene, st)
            register(sc.root, row, 1)
            with tbi.planned(row):
                try:
                    sc.launch(row)
                    self.fail("K1.launch: the fake run_take.launch was not reached")
                except AssertionError:
                    raise
                except Reached:
                    pass
                except Exception as e:  # noqa: BLE001
                    self.fail(f"K1.launch: a registered planned take was refused: {type(e).__name__}: {e}")
            self.assertEqual(sc.spy.calls, 1, "K1.launch")
            self.assertTrue((sc.root / "takes" / "s1" / "1").is_dir(), "K1.launch: takes/s1/1")
        # 2. the stuck slot (ruling w9-Q1): attempt 1 refused before its folder existed, then attempt 2 registered.
        #    Counting folders on disk would give k = 1 for ever; the folder is the open registration's attempt, so
        #    attempt 2 launches into takes/s1/2, and takes/s1/1 is never made
        with contextlib.ExitStack() as st:
            sc = self.must("K1.launch", Scene, st)
            register(sc.root, row, 1)
            commit_outcome(sc.root, tbi.outcome(row, 1, state="failed", final=False,
                                                reason="synthetic: refused before its folder", drive_started=False))
            register(sc.root, row, 2)
            with tbi.planned(row):
                try:
                    sc.launch(row)
                    self.fail("K1.launch: the fake run_take.launch was not reached")
                except AssertionError:
                    raise
                except Reached:
                    pass
                except Exception as e:  # noqa: BLE001
                    self.fail(f"K1.launch: the stuck slot's attempt 2 was refused: {type(e).__name__}: {e}")
            self.assertEqual(sc.spy.calls, 1, "K1.launch: stuck slot")
            self.assertEqual(sorted(p.name for p in (sc.root / "takes" / "s1").iterdir()), ["2"],
                             "K1.launch: attempt 2's folder is takes/s1/2")
        # 2b. the registered attempt's folder already exists: refused by name, before anything is made
        with contextlib.ExitStack() as st:
            sc = self.must("K1.launch", Scene, st)
            register(sc.root, row, 1)
            (sc.root / "takes" / "s1" / "1").mkdir(parents=True)        # an empty folder: git sees nothing
            with tbi.planned(row):
                self.refused("K1.launch: existing folder", sc.launch, row,
                             words=("takes/s1/1", "already exists", "attempt 1"))
            self.assertEqual((sc.spy.calls, sorted(os.listdir(sc.cfg)),
                              list((sc.root / "takes" / "s1" / "1").iterdir())), (0, [], []),
                             "K1.launch: existing folder: something was made or launched")
        # 2c. W9-R1-1: an open attempt 1 under an outcome-closed attempt 2 (a ledger appended outside
        #     commit_registration; Batch cannot reach it): the open registration is not the slot's latest, refused
        with contextlib.ExitStack() as st:
            sc = self.must("K1.launch", Scene, st)
            ledger = sc.root / "takes.json"
            for n in (1, 2):                     # one row per commit, as row_commits requires, by hand
                rows = [dict(row, attempt=a) for a in range(1, n + 1)]
                ledger.write_text(json.dumps({"rows": rows}, indent=2) + "\n")
                tbi.git(sc.root, "add", "--", "takes.json")
                tbi.git(sc.root, "commit", "-q", "-m", "Register one synthetic row by hand")
            commit_outcome(sc.root, tbi.outcome(row, 2, state="failed", final=False,
                                                reason="synthetic: attempt 2 closed", drive_started=False))
            with tbi.planned(row):
                self.refused("K1.launch: open attempt under a later one", sc.launch, row,
                             words=("attempt 1", "not its latest"))
            sc.nothing_made(self, "K1.launch")
        # 3. each allow-listed field changed in turn is refused, naming that field (slot: the other slot has no
        #    registration, so it is refused as unregistered)
        with contextlib.ExitStack() as st:
            sc = self.must("K1.launch", Scene, st)
            register(sc.root, row, 1)
            for field in drive.LAUNCH_FIELDS:
                bad = dict(row, **{field: CHANGED[field] if field != "slot" else "s9"})
                with tbi.planned(row, bad):
                    words = ("slot 's9'", "0 open registrations") if field == "slot" else (field,)
                    self.refused(f"K1.launch: {field}", sc.launch, bad, words=words)
            sc.nothing_made(self, "K1.launch")
        # 4. an unregistered slot, a row the frozen rows do not plan, no freeze
        with contextlib.ExitStack() as st:
            sc = self.must("K1.launch", Scene, st)
            with tbi.planned(row):
                self.refused("K1.launch: unregistered", sc.launch, row, words=("0 open registrations",))
            register(sc.root, row, 1)
            with tbi.planned(tbi.row(2)):
                self.refused("K1.launch: unplanned", sc.launch, row, words=("planned row",))

            def unfrozen(what):
                raise SystemExit(f"{what} needs a FROZEN pre-registration (synthetic)")
            with mock.patch.object(MODS["prereg"], "require_frozen", unfrozen):
                self.refused("K1.launch: no freeze", sc.launch, row, words=("planned row", "FROZEN"))
            sc.nothing_made(self, "K1.launch")
        # 5. through a real batch.Batch and TakeRepo: a take whose registered folder already exists is committed failed, with
        #    drive_started false (a restart re-drives it), and nothing is launched
        with contextlib.ExitStack() as st:
            sc = self.must("K1.launch", Scene, st)
            box = tbi.FakeBox()
            sc.driver = build_driver(drive, sc.root, "takes", sc.cfg, runtime=box)
            (sc.root / "takes" / "s1" / "1").mkdir(parents=True)        # an empty folder: git sees nothing
            repo = drive.TakeRepo(runtime=box, record_files=sc.driver.record_files, secrets=lambda: [("token", tbi.TOKEN)],
                                  rules_scanner=lambda paths: [], root=sc.root, repo=sc.root,
                                  on_published=sc.driver.published)
            import batch
            with tbi.planned(row):
                b = self.must("K1.launch", batch.Batch, sc.driver, repo, tbi.Window(), table=tbi.table(), serial=True)
                got = self.must("K1.launch", b.run, [row])
            self.assertEqual(sc.spy.calls, 0, "K1.launch: Batch reached run_take.launch")
            self.assertEqual([(o["slot"], o["attempt"], o["state"], o["drive_started"]) for o in got],
                             [("s1", 1, "failed", False)], f"K1.launch: {got}")
            self.assertIn("already exists", got[0]["reason"], "K1.launch")
            history = MODS["takes"].read_history(root=sc.root, repo=sc.root)
            self.assertEqual([(o["slot"], o["attempt"], o["drive_started"]) for o in history],
                             [("s1", 1, False)], "K1.launch: the refusal is committed")


# ------------------------------------------------------------------------------------------------- W1
def study_copy(root: Path):
    """The design in force, copied into a scratch study: prereg-draft.json and its tasks/<task>.json; an empty
    register committed."""
    shutil.copyfile(HERE / "prereg-draft.json", root / "prereg-draft.json")
    (root / "tasks").mkdir()
    for t in json.loads((HERE / "prereg-draft.json").read_text())["tasks"]:
        shutil.copyfile(HERE / "tasks" / f"{t['id']}.json", root / "tasks" / f"{t['id']}.json")
    walks = root / MODS["mode_binding"].WALKS_DIR
    walks.mkdir()
    (walks / "register.json").write_text('{\n  "schema": 1,\n  "walks": []\n}\n')
    tbi.git(root, "add", "--", ".")
    tbi.git(root, "commit", "-q", "-m", "Add the synthetic design and register")


def a_walk(walk="w-0001") -> dict:
    d = json.loads((HERE / "prereg-draft.json").read_text())
    task = d["tasks"][0]["id"]
    halves = list(json.loads((HERE / "tasks" / f"{task}.json").read_text())["halves"])
    return {"walk": walk, "task": task, "half": halves[0], "wording": d["tasks"][0]["wordings"][0], "arm": "A",
            "model": d["models"]["A"][-1], "agent": {"harness": "claude-code", "version": "0.0.1"}, "slot": "s-walk"}


class W1WalkLaunch(Case):
    def test_a_walk_is_checked_before_launch(self):
        with contextlib.ExitStack() as st:
            sc = self.must("W1.walk-launch", Scene, st, records="walks")
            study_copy(sc.root)
            # W10 (ruling D2, lane w10-walk-runner): a walk launches only under its own identity (session id from its
            # walk id, no ledger row); the admitted walk is given it, so W1's refusals stay the ones named below
            st.enter_context(mock.patch.object(MODS["prereg"], "load", REAL_PREREG_LOAD))
            sc.driver.identity_for = lambda r: {"session_id": __import__("check_take").walk_session_id(r["walk"]),
                                                "row": None, "row_commit": None}
            walk = a_walk()
            try:
                sc.launch(walk)
                self.fail("W1.walk-launch: the fake run_take.launch was not reached")
            except AssertionError:
                raise
            except Reached:
                pass
            except Exception as e:  # noqa: BLE001
                self.fail(f"W1.walk-launch: a walk the design admits was refused: {type(e).__name__}: {e}")
            reg = sc.root / MODS["mode_binding"].WALKS_DIR / "register.json"
            for field, value, word in (("task", "synthetic-other-task", "task"), ("model", "synthetic-other-model",
                                                                                  "model"),
                                       ("half", "synthetic-half", "half"), ("wording", "w-none", "wording"),
                                       ("arm", "Q", "arm")):
                self.refused(f"W1.walk-launch: {field}", sc.launch, dict(walk, walk=f"w-{field}", **{field: value}),
                             words=(word,))
            entry = dict({k: walk[k] for k in ("walk", "task", "half", "wording", "arm", "model")},
                         walk="w-0002", reason="synthetic", counted=False)
            reg.write_text(json.dumps({"schema": 1, "walks": [entry]}, indent=2) + "\n")
            for walk_id in ("w-0002", "W-0002"):
                self.refused("W1.walk-launch: registered", sc.launch, dict(walk, walk=walk_id),
                             words=("already registered",))
            (sc.root / "prereg.json").write_text("{}\n")
            self.refused("W1.walk-launch: frozen", sc.launch, dict(walk, walk="w-0003"), words=("prereg.json",))
            self.assertEqual(sc.spy.calls, 1, "W1.walk-launch: only the admitted walk reached run_take.launch")
            made = sorted(p.name for p in (sc.root / MODS["mode_binding"].WALKS_DIR).iterdir())
            self.assertEqual(made, ["register.json", "w-0001"], "W1.walk-launch: a refused walk made its folder")


# ------------------------------------------------------------------------------------------------- S1
def synthetic(tasks, n=2) -> dict:
    f = MODS["freeze"]
    return {t: [f.synthetic_digest(t, i) for i in range(n)] for t in tasks}


def real_looking(tasks, n=2) -> dict:
    return {t: [hashlib.sha256(f"synthetic-salted-stand-in-{t}-{i}".encode()).hexdigest() for i in range(n)]
            for t in tasks}


class S1Synthetic(Case):
    def frozen_content(self, frozen, now, rehearsal_plan=False):
        cr = MODS["check_results"]
        with tempfile.TemporaryDirectory(dir=tbi.SCRATCH) as tmp:
            root = Path(tmp)
            (root / "prereg.json").write_text(json.dumps(now))
            out = io.StringIO()
            with mock.patch.object(cr, "HERE", root), \
                    mock.patch.object(cr, "frozen_bytes", return_value=(frozen, "")), \
                    mock.patch.object(cr, "freeze_commit", return_value="synthetic"), \
                    mock.patch.object(cr, "frozen_commit_problems", return_value=[]), \
                    mock.patch.object(cr, "rehearsal_record_problems", return_value=[]), \
                    mock.patch.object(cr, "take_order_problems", return_value=[]), \
                    mock.patch.object(cr, "freeze_recheck_problems", return_value=[]), \
                    contextlib.redirect_stdout(out):     # fold2/lb: the order recompute stood in (test_fold2_lb's)
                problems = self.must("S1.synthetic", cr.check_frozen_content, rehearsal_plan=rehearsal_plan)
        return problems, out.getvalue()

    def test_the_committed_prereg_is_reread_for_synthetic_digests(self):
        tasks = ("synthetic-task-a", "synthetic-task-b")
        base = {"rehearsal_record": "rehearsal or preview", "holdout_wordings_per_task_version": 2}
        fake = dict(base, holdout_salted_digests=synthetic(tasks))
        real = dict(base, holdout_salted_digests=real_looking(tasks))
        # the synthetic digests at the freeze commit and on disk: refused, naming the ruling
        problems, _ = self.frozen_content(fake, fake)
        hits = [p for p in problems if "synthetic holdout digests" in p]
        self.assertEqual(len(hits), 2, f"S1.synthetic: {problems}")
        self.assertTrue(all("W8B-gap4-1" in p and "synthetic-task-a" in p for p in hits), f"S1.synthetic: {hits}")
        # on disk only (the freeze commit clean): still refused, as prereg.json
        problems, _ = self.frozen_content(real, fake)
        self.assertTrue(any(p.startswith("prereg.json holds the rehearsal's synthetic") for p in problems),
                        f"S1.synthetic: an edit on disk was not re-read: {problems}")
        # one synthetic digest mixed into one task's list is enough
        mixed = dict(base, holdout_salted_digests=dict(real_looking(tasks),
                                                       **{"synthetic-task-b": [real_looking(tasks)["synthetic-task-b"][0],
                                                                               synthetic(tasks)["synthetic-task-a"][1]]}))
        problems, _ = self.frozen_content(mixed, mixed)
        self.assertTrue(any("synthetic-task-b" in p and "synthetic holdout" in p for p in problems),
                        f"S1.synthetic: a mixed list passed: {problems}")
        # real-looking digests and an absent field pass this check
        for name, doc in (("real", real), ("absent", base)):
            problems, out = self.frozen_content(doc, doc)
            self.assertEqual([p for p in problems if "synthetic" in p], [], f"S1.synthetic {name}: {problems}")
            self.assertIn("re-read for the rehearsal's synthetic ones: 0 problem(s)", out, f"S1.synthetic {name}")
        # a disposable rehearsal (--rehearsal-plan) prints them NOT CHECKED, never silently
        problems, out = self.frozen_content(fake, fake, rehearsal_plan=True)
        self.assertEqual([p for p in problems if "synthetic" in p], [], f"S1.synthetic rehearsal: {problems}")
        self.assertIn("NOT CHECKED: the rehearsal's synthetic holdout digests", out, "S1.synthetic rehearsal")


# ------------------------------------------------------------------------------------------------- R1
SHA = "d" * 40


class Rehearsal:
    """freeze_rehearsal.main with the clone, git, the review and every step replaced by fakes."""

    def __init__(self, tmp: Path):
        self.tmp, self.commands = tmp, []
        self.draft = tmp / "prereg-draft.json"
        self.draft.write_text((HERE / "prereg-draft.json").read_text())
        self.scratch = tmp / "scratch"

    def sh(self, argv, cwd, env=None, timeout=3600):
        if argv[:2] == ["git", "clone"]:
            target = Path(argv[-1])
            (target / "evals" / "gap-study-4").mkdir(parents=True)
            (target / "evals" / "gap-study-4" / "prereg-draft.json").write_bytes(self.draft.read_bytes())
        return 0, ""

    def git(self, clone, *args):
        return (0, SHA + "\n") if args[:2] == ("rev-parse", "HEAD") else (0, "")

    def run_step(self, command, clone):
        self.commands.append([str(c) for c in command])
        if str(command[4]).endswith("freeze.py"):
            r = MODS["freeze_rehearsal"]
            frozen = {"status": "FROZEN", "take_order": [{}]}
            # lane pf1-l1-freeze-gates (MAJOR 9): the fake freeze read a real-shaped beacon, as a freeze given one does
            frozen["take_order_beacon_reading"] = {"signature": "ab"}
            if "--holdout-digests" in command:
                source = json.loads(Path(command[command.index("--holdout-digests") + 1]).read_text())
                frozen.update(holdout_salted_digests=source["salted_sha256"],
                              holdout_wordings_per_task_version=len(next(iter(source["salted_sha256"].values()))))
            (Path(clone) / "evals" / "gap-study-4" / "prereg.json").write_text(json.dumps(frozen))
            assert r is not None
            return 0, "freeze: wrote prereg.json"
        if str(command[4]).endswith("live_box_cut.py"):   # lane gap-live-box: the clone's verifier, its closed pass line
            sha = hashlib.sha256(Path(command[-1]).read_bytes()).hexdigest()
            return 0, (f"live-box record {sha}: walk lb1, budget 20 s of 900 s, turn 1 cut (end timed-out, exit 124), "
                       f"stream 3 unit(s), session 3 unit(s), shape equal, content problems 0, session torn no; files 4 "
                       f"re-read equal; adapter, check_take and checker digests this tree's; within the bound")
        return 0, "ok"

    def run(self, argv):
        r = MODS["freeze_rehearsal"]
        self.scratch.mkdir()
        patches = ((r, "DRAFT", self.draft), (r, "git", self.git), (r, "sh", self.sh), (r, "run_step", self.run_step),
                   (r, "rehearsal_plan", lambda pre, row: ({}, ())),
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
        report = self.scratch / "freeze-rehearsal-1.txt"
        return code, (report.read_text() if report.is_file() else ""), out.getvalue()

    def tool_commands(self):
        return [c for c in self.commands if c[4].endswith("holdout.py")]


class R1HoldoutTool(Case):
    def tmpdir(self) -> Path:
        return Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve()

    def a_tool(self) -> Path:
        """A stand-in file named holdout.py outside this repository (the fakes never run it)."""
        tool = self.tmpdir() / "holdout.py"
        tool.write_text("# synthetic stand-in for aegis holdout/tools/holdout.py; never run here\n")
        return tool

    def test_the_holdout_step_runs_the_aegis_tool_on_the_synthetic_fixture(self):
        r = MODS["freeze_rehearsal"]
        tool = self.a_tool()
        h = Rehearsal(self.tmpdir())
        record = self.tmpdir() / "record.json"          # lane gap-live-box: a stand-in record, so the run can be all green
        record.write_text("{}\n")
        code, report, out = self.must("R1.holdout-tool", h.run, ["--review-commit", "a" * 40,
                                                                 "--holdout-tool", str(tool),
                                                                 "--live-box-record", str(record),
                                                                 "--live-box-sha256",
                                                                 hashlib.sha256(record.read_bytes()).hexdigest()])
        clone = h.scratch / "repo"
        want = [sys.executable, "-B", "-W", "ignore", str(tool.resolve()), "--check",
                "--holdout", str(clone / "evals" / "gap-study-4" / "fixtures" / "holdout-rehearsal"),
                "--gars", str(clone), "--sha", SHA]
        self.assertEqual(h.tool_commands(), [want], f"R1.holdout-tool: {h.tool_commands()}")
        flat = " ".join(" ".join(c) for c in h.commands)
        for word in ("--digests", "--make-salt", "--salt-file"):
            self.assertNotIn(word, flat, f"R1.holdout-tool: the rehearsal ran {word}")
        label = ("holdout.py --check on the synthetic fixture evals/gap-study-4/fixtures/holdout-rehearsal, "
                 "not the real holdout")
        self.assertIn(f"[0] {label}\n    ok", report, f"R1.holdout-tool: the record is not labelled: {report}")
        self.assertIn(f"[0] {label}: ok", out, f"R1.holdout-tool: the printed step is not labelled: {out}")
        self.assertEqual([line for line in report.splitlines() + out.splitlines()
                          if "holdout.py --check" in line and label not in line], [],
                         "R1.holdout-tool: a line names the holdout step without its label")
        self.assertNotIn("OWED", report, "R1.holdout-tool")
        self.assertEqual((code, report.rstrip().splitlines()[-1]), (0, "all green"), f"R1.holdout-tool {report}")
        # without the tool the step stays owed, and the run is not all green
        h = Rehearsal(self.tmpdir())
        code, report, _ = self.must("R1.holdout-tool", h.run, ["--review-commit", "a" * 40])
        self.assertEqual(h.tool_commands(), [], "R1.holdout-tool: holdout.py ran with no tool given")
        self.assertIn("[1] holdout.py --check\n    OWED: holdout.py --check lives in private aegis (ruling C4)", report,
                      "R1.holdout-tool: no tool, no owed line")
        self.assertEqual((code, report.rstrip().splitlines()[-1]), (1, "NOT all green"), "R1.holdout-tool")
        # refused before anything runs: relative, misnamed, missing, inside this repository
        other = self.tmpdir() / "check.py"
        other.write_text("# synthetic\n")
        inside = self.tmpdir()
        (inside / "holdout.py").write_text("# synthetic\n")
        for name, argv, patch in (("relative", ["--holdout-tool", "holdout.py"], None),
                                  ("misnamed", ["--holdout-tool", str(other)], None),
                                  ("missing", ["--holdout-tool", str(self.tmpdir() / "holdout.py")], None),
                                  ("in repo", ["--holdout-tool", str(inside / "holdout.py")], inside)):
            h = Rehearsal(self.tmpdir())
            with mock.patch.object(r, "REPO", patch) if patch else contextlib.nullcontext():
                code, report, out = self.must("R1.holdout-tool", h.run, ["--review-commit", "a" * 40, *argv])
            self.assertEqual((code, h.commands), (2, []), f"R1.holdout-tool {name}: {out}")
            self.assertIn("refusing: --holdout-tool", out, f"R1.holdout-tool {name}")
        # no holdout-folder option, and no abbreviation reaches one
        for argv in (["--holdout", str(FIXTURE)], ["--holdout-t", str(tool)]):
            h = Rehearsal(self.tmpdir())
            err = io.StringIO()
            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit, msg=f"R1.holdout-tool: {argv}"):
                h.run(["--review-commit", "a" * 40, *argv])
            self.assertEqual(h.commands, [], f"R1.holdout-tool: {argv}")

    def test_the_fixture_is_synthetic_and_one_file_per_task(self):
        tasks = sorted(t["id"] for t in json.loads((HERE / "prereg-draft.json").read_text())["tasks"])
        self.assertEqual(getattr(MODS["freeze_rehearsal"], "HOLDOUT_FIXTURE", None), "fixtures/holdout-rehearsal",
                         "R1.fixture")
        self.assertEqual(sorted(p.name for p in FIXTURE.iterdir()), [f"{t}.json" for t in tasks], "R1.fixture")
        for t in tasks:
            doc = json.loads((FIXTURE / f"{t}.json").read_text())
            self.assertEqual((set(doc), doc["task"]), ({"task", "wordings"}, t), f"R1.fixture {t}")
            self.assertEqual([w["id"] for w in doc["wordings"]], ["h1", "h2", "h3"], f"R1.fixture {t}")
            for w in doc["wordings"]:
                self.assertTrue(w["opening"].startswith("Synthetic rehearsal opening "), f"R1.fixture {t}")
                for per in (w.get("slots") or {}).values():
                    self.assertTrue(all(v.startswith("synthetic ") for v in per.values()), f"R1.fixture {t}")


BOUND = {"K1.launch": "K1Launch.test_a_take_is_checked_against_its_records_before_launch",
         "W1.walk-launch": "W1WalkLaunch.test_a_walk_is_checked_before_launch",
         "S1.synthetic": "S1Synthetic.test_the_committed_prereg_is_reread_for_synthetic_digests",
         "R1.holdout-tool": "R1HoldoutTool.test_the_holdout_step_runs_the_aegis_tool_on_the_synthetic_fixture"}
WITNESSES = {name: (BOUND[clause], clause) for name, (clause, _, _, _) in mutants().items()}


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_cp6_wiring witnesses", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()),
                                    *sorted({WITNESSES[x][0] for x in chosen})], timeout=1800, tag="test_cp6_wiring")
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=110)
        record = re.findall(r"^test_cp6_wiring outcomes: (\{.*\})$", got.stdout, re.M)
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
    print(f"test_cp6_wiring witnesses: {red}/{len(chosen)} red; registry {len(WITNESSES)}", flush=True)
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
    print(f"test_cp6_wiring: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_cp6_wiring outcomes: " + json.dumps({"failures": ids(result.failures), "errors": ids(result.errors),
                                                     "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
