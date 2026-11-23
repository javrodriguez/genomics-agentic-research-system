#!/usr/bin/env python3
"""Lane vendor-b21 (glitch-26's rulings B21-2 to B21-7, Tue 20 Oct 2026): codex and gemini in harness_bookkeeping.TABLE.

    python3 tests/test_vendor_bookkeeping.py               the tests
    python3 tests/test_vendor_bookkeeping.py --witnesses   each mutant below, alone: its own check must go red

GPT walk w-o45 (gpt-6.1-sol, explain-not-act trap, on 28b46165) was held at its operator step: "drive raised
UnknownHarness: harness 'codex' has no bookkeeping entry (known: ['claude-code'])" (drive.py:2380 `_excluded`). The
design note lane-reports/vendor-b21-DESIGN.md measured 18 real walks (12 codex, 6 gemini; paths and counts only):
neither harness leaves run-tree furniture beyond endstate's COMMON_EXCLUSIONS, so each entry holds its native session
file (home-relative, inert while the evidence's home is null) and R4-4's `.home/**` (the agent HOME: snapshotted, not
graded), nothing else.

  B21-3a  w-o45: the drive's own operator step (TakeDriver._operator_step, the box road stubbed) on a codex and a gemini
          row, explain-not-act's save and confounded-design's finalize copy: each reaches the box write and logs its
          event (on 28b46165 each raised UnknownHarness).
  B21-3b  Evidence.load (production TABLE, no injected table) of a codex and a gemini evidence folder shaped like the
          measured walks (run_tree "", home null, .home and .tmp empty at pre-1, a __pycache__ write, .git/index and a
          gars/projects write in turn 1): it loads; the task write is the agent's, the helper's and git's are excluded;
          a write under .home is excluded (R4-4) and one under .tmp is the agent's (w-g5's .tmp/run_stage00.py).
  B21-3c  the operator step still refuses a write into an excluded path (.home/x) for each vendor, never logging it.
  B21-3d  MUTANTS: each pattern's removal, and each entry's, turns its own check red alone (--witnesses).
  B21-4   the claude-code entry's repr is byte-identical to 28b46165's (sha256 pinned).

Every fixture is synthetic: no walk's record, transcript or session is read.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import harness_bookkeeping as hb  # noqa: E402
from graders import endstate as es  # noqa: E402

VENDORS = {"codex": "0.162.1", "gemini": "0.64.0"}
PROJECT = "run-0a1b2c3d"
TASK_WRITE = f"gars/projects/{PROJECT}/01_samplesheets/rnaseq_bulk_samplesheet.csv"
PYC = "gars/_system/__pycache__/integrity.cpython-311.pyc"
GIT_INDEX = ".git/index"
HOME_WRITE = ".home/.cache/pip/http/x"
TMP_WRITE = ".tmp/run_stage00.py"
# repr(hb.TABLE["claude-code"]) at 28b46165 (B20), read before this lane changed the module.
CLAUDE_ENTRY_SHA256 = "cdc7989c1320b395a5e731b1e8af00aff092b42225d2f3f70e4bcac7231c23e4"

drive = None


def setUpModule():
    global drive
    import drive as imported
    drive = imported


def F(text: str) -> dict:
    return {"type": "file", "sha256": hashlib.sha256(text.encode()).hexdigest()}


# ------------------------------------------------------------------------------------------- B21-3a and 3c, the drive
class Box:
    """The box's operator road, stubbed: every write is recorded and replied to with the data's sha256."""

    def __init__(self, reads=None):
        self.writes, self.reads = [], dict(reads or {})

    def operator_write(self, runtime, *, image, run_tree, rel_path, data, caller_env):
        self.writes.append(rel_path)
        return {"ok": True, "sha256": hashlib.sha256(data).hexdigest()}

    def operator_read(self, runtime, *, image, root_kind, run_tree, config_dir, rel_path, caller_env):
        return self.reads.get(rel_path)


def operator_step(harness: str, action: str, tree: str):
    """TakeDriver._operator_step on one row of `harness`, as drive.py runs it after turn n: (logged events, box)."""
    task = "explain-not-act" if action == drive.OPERATOR_SAVE else "confounded-design"
    op_id = {drive.OPERATOR_SAVE: "operator-save",
             drive.OPERATOR_FINALIZE: "wait-for-samples-csv-then-copy-design"}[action]
    table = b"sample_id,condition\nS1,a\n"
    box = Box({f"gars/projects/{PROJECT}/00_data/rnaseq_bulk/samples.csv": b"sample_id,x\n",
               drive.DESIGN_TABLE.format(project=PROJECT): table})
    logged = []
    me = SimpleNamespace(
        project_for=lambda row: PROJECT, ownership=box, runtime=object(), caller_env={}, clock=lambda: 1.0,
        sleep=lambda s: None, finalize_wait_s=1.0, poll_s=0.1, _rel=drive.TakeDriver._rel,
        _excluded=drive.TakeDriver._excluded, _evidence_line=lambda take, rec: logged.append(rec))
    me._operator_read = lambda take, op, rel: drive.TakeDriver._operator_read(me, take, op, rel)
    take = SimpleNamespace(launched=SimpleNamespace(spec=SimpleNamespace(run_tree=tree)),
                           spec=SimpleNamespace(image="sha256:" + "0" * 64), config_dir=None)
    row = {"task": task, "half": "trap", "agent": {"harness": harness, "version": VENDORS.get(harness, "x")}}
    pinned = {"halves": {"trap": {"fixture": {"design_table": {"md5": hashlib.md5(table).hexdigest()}}}}}
    with mock.patch.object(drive._variants, "load_task", lambda name: pinned):
        drive.TakeDriver._operator_step(me, take, row, (op_id, action))
    return logged, box


def operator_problems() -> list:
    """B21-3a: each vendor's operator step, both actions, reaches the box write and logs one event of it."""
    out = []
    for harness in VENDORS:
        for action in (drive.OPERATOR_SAVE, drive.OPERATOR_FINALIZE):
            with tempfile.TemporaryDirectory() as tree:
                try:
                    logged, box = operator_step(harness, action, tree)
                except Exception as e:  # noqa: BLE001 - w-o45's UnknownHarness is the red this test reproduces
                    out.append(f"{harness} {action}: {type(e).__name__}: {e}")
                    continue
            want = f"gars/projects/{PROJECT}/00_data/rnaseq_bulk/samples.csv"
            if box.writes != [want] or [w["path"] for e in logged for w in e["writes"]] != [want]:
                out.append(f"{harness} {action}: wrote {box.writes}, logged {logged}")
    return out


def guard_problems() -> list:
    """B21-3c: a write the operator step would make into .home (excluded under each vendor) is refused, unlogged,
    never reaching the box."""
    out = []
    from fixtures import gen_explain_not_act as gen
    for harness in VENDORS:
        with tempfile.TemporaryDirectory() as tree:
            moved = lambda proj: Path(tree) / ".home" / "samples.csv"  # noqa: E731 - the save aimed at the HOME
            with mock.patch.object(gen, "samples_csv", moved):
                try:
                    logged, box = operator_step(harness, drive.OPERATOR_SAVE, tree)
                    out.append(f"{harness}: the write into .home was made ({box.writes}), logged {logged}")
                except drive.DriveRefused as e:
                    if "an excluded path" not in str(e):
                        out.append(f"{harness}: refused for another reason: {e}")
                except Exception as e:  # noqa: BLE001
                    out.append(f"{harness}: {type(e).__name__}: {e}")
    return out


# --------------------------------------------------------------------------------------------- B21-3b, the evidence
def write_evidence(folder: Path, harness: str) -> None:
    """One turn, shaped like the measured walks: run_tree "", home null, .home and .tmp empty at pre-1."""
    ev = folder
    (ev / "snapshots").mkdir(parents=True)
    (ev / "blobs").mkdir()
    pre = {".git": {"type": "dir"}, GIT_INDEX: F("index 0"), ".home": {"type": "dir"}, ".tmp": {"type": "dir"},
           "gars": {"type": "dir"}, "gars/_system": {"type": "dir"}, "gars/projects": {"type": "dir"}}
    post = dict(pre, **{GIT_INDEX: F("index 1"), "gars/_system/__pycache__": {"type": "dir"}, PYC: F("pyc"),
                        TASK_WRITE: F("sheet"), HOME_WRITE: F("pip cache"), TMP_WRITE: F("agent script")})
    for label, at, entries in (("pre-1", 100.0, pre), ("post-1", 106.0, post)):
        (ev / "snapshots" / f"{label}.json").write_text(json.dumps({"label": label, "taken_at": at,
                                                                    "entries": entries}))
    ledger = [{"kind": "take", "model": f"synthetic-{harness}-model",
               "agent": {"harness": harness, "version": VENDORS[harness]}, "run_tree": "", "home": None},
              {"kind": "turn", "n": 1, "started_at": 101.0, "ended_at": 103.0}]
    (ev / "ledger.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ledger))
    (ev / "access.jsonl").write_text("")
    (ev / "health.jsonl").write_text(json.dumps({"kind": "watcher-start", "at": 50.0}) + "\n" + json.dumps(
        {"kind": "watcher-stop", "at": 108.0, "exit_code": 0, "ignored_newline_paths": 0}) + "\n")
    (ev / "watched.json").write_text(json.dumps({"paths": [f"gars/projects/{PROJECT}/01_samplesheets"]}))


def load_problems() -> list:
    out = []
    for harness in VENDORS:
        with tempfile.TemporaryDirectory() as tmp:
            write_evidence(Path(tmp) / "evidence", harness)
            try:
                got = es.Evidence.load(Path(tmp) / "evidence")
            except es.EvidenceError as e:
                out.append(f"{harness}: Evidence.load refused: {e}")
                continue
        if (got.harness, got.version) != (harness, VENDORS[harness]):
            out.append(f"{harness}: read as {(got.harness, got.version)}")
        agent, excluded = sorted(got.agent_changes(1)), sorted(got.excluded_changes(1))
        if agent != sorted([TASK_WRITE, TMP_WRITE]):
            out.append(f"{harness}: the agent's changes are {agent}")
        if excluded != sorted([GIT_INDEX, "gars/_system/__pycache__", PYC, HOME_WRITE]):
            out.append(f"{harness}: the excluded changes are {excluded}")
    return out


# ------------------------------------------------------------------------------------------------------- B21-4
def claude_problems() -> list:
    got = hashlib.sha256(repr(hb.TABLE.get(hb.CLAUDE_CODE)).encode()).hexdigest()
    return [] if got == CLAUDE_ENTRY_SHA256 else [f"the claude-code entry moved: repr sha256 {got}"]


# ------------------------------------------------------------------------------------------------------- B21-3d
@contextmanager
def entry_replaced(name: str, **fields):
    with mock.patch.dict(hb.TABLE, {name: dataclasses.replace(hb.TABLE[name], **fields)}):
        yield


@contextmanager
def entry_removed(name: str):
    with mock.patch.dict(hb.TABLE):
        del hb.TABLE[name]
        yield


@contextmanager
def claude_moved():
    with entry_replaced(hb.CLAUDE_CODE, run_tree_paths=(".home/**",)):
        yield


# (name, the mutant, the check it must turn red alone)
MUTANTS = [(f"{h}-home-dropped", (lambda h=h: entry_replaced(h, run_tree_paths=())), c)
           for h in VENDORS for c in ("guard", "load")] + \
          [(f"{h}-home-narrowed", (lambda h=h: entry_replaced(h, run_tree_paths=(".home/*",))), "load")
           for h in VENDORS] + \
          [(f"{h}-tmp-excluded", (lambda h=h: entry_replaced(h, run_tree_paths=(".home/**", ".tmp/**"))), "load")
           for h in VENDORS] + \
          [(f"{h}-entry-removed", (lambda h=h: entry_removed(h)), c) for h in VENDORS for c in ("operator", "load")] + \
          [("claude-entry-moved", claude_moved, "claude")]
CHECKS = {"operator": operator_problems, "guard": guard_problems, "load": load_problems, "claude": claude_problems}


def witnesses() -> list:
    """Each mutant alone: (name, check, red?)."""
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_clean("test_vendor_bookkeeping witnesses",
                                    lambda: [f"{c}: {x}" for c in CHECKS for x in CHECKS[c]()])
    out = []
    for name, mutant, check in MUTANTS:
        with mutant():
            out.append((name, check, bool(CHECKS[check]())))
    return out


class TheW_o45OperatorStep(unittest.TestCase):
    def test_each_vendor_operator_step_reaches_the_box_write(self):
        self.assertEqual(operator_problems(), [])

    def test_the_excluded_path_guard_still_refuses_for_each_vendor(self):
        self.assertEqual(guard_problems(), [])


class TheEvidence(unittest.TestCase):
    def test_a_vendor_take_loads_on_the_production_table(self):
        self.assertEqual(load_problems(), [])


class TheClaudeEntry(unittest.TestCase):
    def test_byte_identical_to_b20(self):
        self.assertEqual(claude_problems(), [])


class Mutants(unittest.TestCase):
    def test_every_mutant_is_red_alone(self):
        got = witnesses()
        self.assertEqual(len(got), 13)
        self.assertEqual([(n, c) for n, c, red in got if not red], [])


if __name__ == "__main__":
    if sys.argv[1:] == ["--witnesses"]:
        setUpModule()
        got = witnesses()
        for n, c, red in got:
            print(f"{'red  ' if red else 'GREEN'} {n} ({c})")
        print(f"witnesses: {sum(r for _, _, r in got)}/{len(got)} red")
        raise SystemExit(0 if all(r for _, _, r in got) else 1)
    unittest.main(verbosity=2)
