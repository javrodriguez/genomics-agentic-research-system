#!/usr/bin/env python3
"""machine_gate.py: P-2 (glitch-06's ruling, 14 Oct 2026), no take starts while an athena suite runs or the machine is
booked. The list lines below are athena_suite.py cmd_list's own form ("%s kind=%s commit=%s launched=%s verdict=%s"
and its scope words). Fakes only: no process runs (run_list is handed in).

  G1-list     a run with no verdict that was not refused is in progress; finished and refused runs are not; a line
              off the command's form is a problem (fail closed); an empty list is nothing running
  G2-booking  a .machine-reserved that exists (an emptied one too) is booked; an absent one is not
  G3-gate     the list command's failure (exit or exception) is a problem, never "nothing running"
  G4-env      the gate is built only from GAP4_ATHENA_SUITE and GAP4_MACHINE_BOOKING naming real absolute paths

Witnesses (each red by its own clause): running-unseen, booking-ignored, list-exit-ignored, odd-line-passes.
"""

from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import machine_gate as mg  # noqa: E402

DONE = "gap4-a-20261014T0900Z kind=gars-gap4 commit=8a598b4919d7 launched=2026-10-14T09:00:00Z verdict=PASS"
REFUSED = "gap4-b-20261014T0901Z kind=gars-gap4 commit=8a598b4919d7 launched=refused verdict=-"
RUNNING = "gap4-c-20261014T0902Z kind=gars-gap4 commit=8a598b4919d7 launched=2026-10-14T09:02:00Z verdict=- (subset)"
PREPARED = "gap4-d-20261014T0903Z kind=gars kind=x commit= launched=- verdict=-"


def g1(mod) -> list:
    out = []
    if mod.problems("", False) != []:
        out.append("G1-list: an empty list reads as something running")
    if mod.problems("\n".join([DONE, REFUSED]), False) != []:
        out.append("G1-list: a finished or refused run reads as running")
    if not any("gap4-c" in x for x in mod.problems(RUNNING, False)):
        out.append("G1-list: a run with no verdict is not in progress")
    if not mod.problems("garbled output\n", False):
        out.append("G1-list: a line off the command's form passes")
    return out


def g2(mod) -> list:
    out = []
    with tempfile.TemporaryDirectory() as t:
        booking = os.path.join(t, ".machine-reserved")
        gate = mod.gate(run_list=lambda: (0, DONE + "\n"), booking_path=booking)
        if gate() != []:
            out.append("G2-booking: an absent booking reads as booked")
        Path(booking).write_text("")
        if not any("booked" in x for x in gate()):
            out.append("G2-booking: an emptied booking reads as free")
    return out


def g3(mod) -> list:
    out = []
    booking = "/nonexistent-gap4/.machine-reserved"

    def boom():
        raise OSError("synthetic")
    for why, run in (("a non-zero exit", lambda: (5, "")), ("an exception", boom)):
        if not mod.gate(run_list=run, booking_path=booking)():
            out.append(f"G3-gate: {why} of the list reads as nothing running")
    return out


def g4(mod) -> list:
    out = []
    with tempfile.TemporaryDirectory() as t:
        suite = os.path.join(t, "athena_suite.py")
        Path(suite).write_text("# synthetic\n")
        ok = {mod.ENV_SUITE: suite, mod.ENV_BOOKING: os.path.join(t, ".machine-reserved")}
        check, why = mod.gate_from_env(ok)
        if not callable(check) or why is not None:
            out.append(f"G4-env: named paths do not build the gate: {why}")
        for bad in ({}, {mod.ENV_SUITE: "relative.py", mod.ENV_BOOKING: ok[mod.ENV_BOOKING]},
                    {mod.ENV_SUITE: suite, mod.ENV_BOOKING: "/nonexistent-gap4/x/.machine-reserved"}):
            check, why = mod.gate_from_env(bad)
            if check is not None or not why:
                out.append(f"G4-env: {sorted(bad)} built a gate")
    return out


CHECKS = {"G1-list": g1, "G2-booking": g2, "G3-gate": g3, "G4-env": g4}


def witness(edits) -> types.ModuleType:
    src = Path(mg.__file__).read_text(encoding="utf-8")
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"witness not performed: {old[:60]!r} occurs {src.count(old)} times")
        src = src.replace(old, new)
    mod = types.ModuleType("machine_gate_witness")
    mod.__file__ = mg.__file__
    exec(compile(src, mg.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


WITNESSES = {
    "running-unseen": ((("        elif m[\"verdict\"] == \"-\" and m[\"launched\"] not in NOT_RUNNING_LAUNCH:",
                         "        elif False:"),), "G1-list"),
    "odd-line-passes": ((("            out.append(f\"an athena_suite list line is not that command's form: {line[:120]!r}\")",
                          "            pass"),), "G1-list"),
    "booking-ignored": ((("        return problems(text, os.path.lexists(booking_path))",
                          "        return problems(text, False)"),), "G2-booking"),
    "list-exit-ignored": ((("        if code != 0:\n", "        if False:\n"),), "G3-gate"),
}


class TestTheGate(unittest.TestCase):
    def test_g1_list(self):
        self.assertEqual(g1(mg), [])

    def test_g2_booking(self):
        self.assertEqual(g2(mg), [])

    def test_g3_gate(self):
        self.assertEqual(g3(mg), [])

    def test_g4_env(self):
        self.assertEqual(g4(mg), [])

    def test_prepared_run_is_in_progress_or_refused_as_odd(self):
        self.assertTrue(mg.problems(PREPARED, False))


class TestWitnesses(unittest.TestCase):
    def test_every_witness_is_red_by_its_own_clause(self):
        for name, (edits, clause) in WITNESSES.items():
            with self.subTest(name=name):
                self.assertEqual(CHECKS[clause](mg), [], f"{name}: {clause} is not green on the tree")
                got = CHECKS[clause](witness(edits))
                self.assertTrue([x for x in got if x.startswith(clause + ":")], f"{name}: survived")


if __name__ == "__main__":
    unittest.main()
