#!/usr/bin/env python3
"""machine_gate.py: P-2, redesigned under glitch-6b's ruling of 15 Oct 2026 (item 2). Fakes only: a fake /proc folder,
a reservation file in a temporary folder, fake athena_suite.py scripts; no ssh, no suite, no docker.

  A1-athena   the athena gate admits only with no suite-account process and the reservation absent or this walk's own
              hold (by exact id); suite processes, an unreadable process table, another hold (expired or not) and
              no own hold each refuse
  A2-reserve  read_reservation: absent, held, and every unreadable shape (folder, link, too large, not JSON, not an
              object, a `by` that is no hold id)
  A3-gate     athena_gate over a fake /proc and a real file: own suite-account process seen, an exception refuses
  A4-env      gate_from_env builds only from GAP4_SUITE_ACCOUNT, GAP4_RESERVATION and GAP4_OWN_HOLD; the first gate's
              variables alone (GAP4_ATHENA_SUITE naming a list that prints nothing on athena) never build a gate:
              the fail-open of 383e5c2f, closed
  M1-list     the Mac pre-check over the real 15 Oct list (1202 lines, names and commits masked): busy and refused
              runs never ran and are never queried; the 9 started runs without a verdict are each read by status
  M2-status   a started run without a verdict is in progress unless its status is an ended state; a status that
              cannot be read refuses; a line off the list's form refuses
  M3-reader   suite_status_reader and mac_precheck over fake athena_suite.py scripts

Witnesses (each red by its own clause): busy-runs, foreign-hold-admitted, unreadable-reservation-admitted,
unread-processes-admitted, status-error-swallowed, old-env-builds.
"""

from __future__ import annotations

import json
import os
import pwd
import sys
import tempfile
import textwrap
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import machine_gate as mg  # noqa: E402

ME = pwd.getpwuid(os.getuid()).pw_name
REAL_LIST = HERE / "tests" / "fixtures" / "machine-gate-athena-suite-list-20261015.txt"
HOLD = "gap4-walk-w-0001"
DONE = "run-a kind=gars-gap4 commit=8a598b4919d7 launched=started verdict=PASS"
REFUSED = "run-b kind=gars-gap4 commit=8a598b4919d7 launched=refused verdict=-"
BUSY = "run-c kind=gars-gap4 commit=8a598b4919d7 launched=busy verdict=-"
STARTED = "run-d kind=gars-gap4 commit=8a598b4919d7 launched=started verdict=- jobs=24 scope=all"


def fake_proc(t, owned=0):
    proc = os.path.join(t, "proc")
    os.mkdir(proc)
    os.mkdir(os.path.join(proc, "self"))
    for n in range(owned):
        os.mkdir(os.path.join(proc, str(100 + n)))
    return proc


def a1(mod) -> list:
    out = []
    if mod.athena_problems([], ("absent", None), HOLD) != []:
        out.append("A1-athena: no suite process and no reservation is refused")
    if mod.athena_problems([], ("held", HOLD), HOLD) != []:
        out.append("A1-athena: this walk's own hold blocks itself")
    for why, args in (("a suite process", ([4242], ("absent", None), HOLD)),
                      ("an unreadable process table", (None, ("absent", None), HOLD)),
                      ("another hold", ([], ("held", "javier"), HOLD)),
                      ("a near-miss hold id", ([], ("held", HOLD + "x"), HOLD)),
                      ("no own hold", ([], ("held", HOLD), None)),
                      ("an unreadable reservation", ([], ("unreadable", "synthetic"), HOLD)),
                      ("an unknown reading", ([], ("maybe", None), HOLD))):
        if not mod.athena_problems(*args):
            out.append(f"A1-athena: {why} is admitted")
    return out


def a2(mod) -> list:
    out = []
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "reserved.json")
        if mod.read_reservation(p) != ("absent", None):
            out.append("A2-reserve: an absent file is not absent")
        Path(p).write_text(json.dumps({"by": HOLD, "until": "2026-10-15T09:29:00-04:00"}))
        if mod.read_reservation(p) != ("held", HOLD):
            out.append("A2-reserve: a held reservation is not read as held")
        Path(p).write_text(json.dumps({"by": "javier", "until": "2020-01-01T00:00:00-05:00"}))
        if mod.read_reservation(p) != ("held", "javier"):
            out.append("A2-reserve: an expired reservation is not read as held by its holder")
        bad = {"not JSON": "{", "a list": "[]", "no by": "{}", "a by that is no id": json.dumps({"by": "-x y"}),
               "too large": json.dumps({"by": HOLD, "pad": "x" * 5000}), "empty": ""}
        for why, text in bad.items():
            Path(p).write_text(text)
            if mod.read_reservation(p)[0] != "unreadable":
                out.append(f"A2-reserve: {why} is not unreadable")
        os.remove(p)
        os.mkdir(p)
        if mod.read_reservation(p)[0] != "unreadable":
            out.append("A2-reserve: a folder is not unreadable")
        os.rmdir(p)
        target = os.path.join(t, "elsewhere.json")
        Path(target).write_text(json.dumps({"by": HOLD}))
        os.symlink(target, p)
        if mod.read_reservation(p)[0] != "unreadable":
            out.append("A2-reserve: a link is followed")
    return out


def a3(mod) -> list:
    out = []
    with tempfile.TemporaryDirectory() as t:
        res = os.path.join(t, "reserved.json")
        os.mkdir(os.path.join(t, "a"))
        idle = fake_proc(os.path.join(t, "a"))
        if mod.athena_gate(account=ME, reservation_path=res, own_hold=HOLD, proc=idle)() != []:
            out.append("A3-gate: an idle fake machine is refused")
        os.mkdir(os.path.join(t, "b"))
        busy = fake_proc(os.path.join(t, "b"), owned=2)
        got = mod.athena_gate(account=ME, reservation_path=res, own_hold=HOLD, proc=busy)()
        if not any("2 process" in x for x in got):
            out.append("A3-gate: the account's processes are not seen")
        if mod.suite_account_pids(ME, busy) != [100, 101]:
            out.append("A3-gate: suite_account_pids does not list the account's pids")
        if mod.suite_account_pids("no-such-account-gap4", busy) is not None:
            out.append("A3-gate: an unknown account reads as no process")
        if mod.suite_account_pids(ME, os.path.join(t, "absent-proc")) is not None:
            out.append("A3-gate: an unreadable /proc reads as no process")
        with mock.patch.object(mod, "suite_account_pids", side_effect=RuntimeError("synthetic")):
            if not mod.athena_gate(account=ME, reservation_path=res, own_hold=HOLD, proc=idle)():
                out.append("A3-gate: an exception while reading reads as nothing running")
        for kw in ({"account": "", "reservation_path": res, "own_hold": HOLD},
                   {"account": ME, "reservation_path": "reserved.json", "own_hold": HOLD},
                   {"account": ME, "reservation_path": res, "own_hold": "bad id"}):
            try:
                mod.athena_gate(**kw)
                out.append(f"A3-gate: a gate was built from {kw}")
            except ValueError:
                pass
    return out


def a4(mod) -> list:
    out = []
    with tempfile.TemporaryDirectory() as t:
        res = os.path.join(t, "reserved.json")
        ok = {mod.ENV_ACCOUNT: ME, mod.ENV_RESERVATION: res, mod.ENV_HOLD: HOLD}
        check, why = mod.gate_from_env(ok)
        if not callable(check) or why is not None:
            out.append(f"A4-env: the named values do not build the gate: {why}")
        for k in ok:
            check, why = mod.gate_from_env({x: v for x, v in ok.items() if x != k})
            if check is not None or not why:
                out.append(f"A4-env: a gate was built without {k}")
        for bad in ({**ok, mod.ENV_ACCOUNT: "no-such-account-gap4"}, {**ok, mod.ENV_RESERVATION: "reserved.json"},
                    {**ok, mod.ENV_RESERVATION: os.path.join(t, "absent", "reserved.json")},
                    {**ok, mod.ENV_HOLD: "bad id"}):
            check, why = mod.gate_from_env(bad)
            if check is not None or not why:
                out.append(f"A4-env: a gate was built from {bad}")
        # The first gate's variables, with a list that prints nothing (athena_suite.py list on athena, which holds no
        # Mac run records): never a gate, so never "nothing running".
        suite = os.path.join(t, "athena_suite.py")
        Path(suite).write_text("import sys\nsys.exit(0)\n")
        old = {"GAP4_ATHENA_SUITE": suite, "GAP4_MACHINE_BOOKING": os.path.join(t, ".machine-reserved")}
        check, why = mod.gate_from_env(old)
        if check is not None or not why:
            out.append("A4-env: the first gate's variables still build a gate (the athena fail-open)")
    return out


def m1(mod) -> list:
    out = []
    text = REAL_LIST.read_text(encoding="utf-8")
    lines = [x for x in text.splitlines() if x.strip()]
    if len(lines) != 1202:
        out.append(f"M1-list: the fixture holds {len(lines)} lines, not the 1202 read on 15 Oct")
    asked = []

    def ended(name):
        asked.append(name)
        return "done"
    if mod.list_problems(text, ended) != []:
        out.append("M1-list: the real list with every started run ended is refused")
    started_open = [x.split()[0] for x in lines if " launched=started " in x and " verdict=- " in x + " "]
    if len(started_open) != 9 or sorted(asked) != sorted(started_open):
        out.append(f"M1-list: status was asked for {len(asked)} runs, not the 9 started runs without a verdict")
    busy = [x.split()[0] for x in lines if " launched=busy " in x]
    if len(busy) != 844 or set(asked) & set(busy):
        out.append("M1-list: a busy run (athena refused it) is read as possibly running")
    got = mod.list_problems(text, lambda name: "running" if name == started_open[-1] else "done")
    if len(got) != 1 or started_open[-1] not in got[0]:
        out.append("M1-list: the one running run of the real list is not the one problem")
    return out


def m2(mod) -> list:
    out = []
    if mod.list_problems("", lambda n: "running") != []:
        out.append("M2-status: an empty list is refused")
    if mod.list_problems("\n".join([DONE, REFUSED, BUSY]), lambda n: "running") != []:
        out.append("M2-status: a finished, refused or busy run reads as running")
    for state in mod.ENDED_STATES:
        if mod.list_problems(STARTED, lambda n, s=state: s) != []:
            out.append(f"M2-status: a stale started run whose status is {state!r} is refused")
    for state in ("running", "prepared", "unknown", "", None):
        if not mod.list_problems(STARTED, lambda n, s=state: s):
            out.append(f"M2-status: a started run whose status is {state!r} is admitted")

    def boom(name):
        raise RuntimeError("synthetic")
    if not mod.list_problems(STARTED, boom):
        out.append("M2-status: a status that cannot be read reads as ended")
    if not mod.list_problems("garbled output\n", lambda n: "done"):
        out.append("M2-status: a line off the command's form passes")
    return out


SUITE_SCRIPT = textwrap.dedent("""\
    import sys
    LIST = {list!r}
    STATUS = {status!r}
    if sys.argv[1] == "list":
        print(LIST, end="")
        sys.exit({list_rc})
    if sys.argv[1] == "status":
        st = STATUS.get(sys.argv[2])
        if st is None:
            sys.exit(5)
        print("run=%s state=%s rc=None reason=None" % ({name_echo}, st))
        sys.exit(0)
    sys.exit(2)
    """)


def suite_file(t, *, list_text="", status=None, list_rc=0, name_echo="sys.argv[2]"):
    p = os.path.join(t, "athena_suite.py")
    Path(p).write_text(SUITE_SCRIPT.format(list=list_text, status=status or {}, list_rc=list_rc,
                                           name_echo=name_echo))
    return p


def m3(mod) -> list:
    out = []
    with tempfile.TemporaryDirectory() as t:
        p = suite_file(t, list_text=STARTED + "\n" + BUSY + "\n", status={"run-d": "lost"})
        if mod.suite_status_reader(p)("run-d") != "lost":
            out.append("M3-reader: the status word is not read")
        try:
            mod.suite_status_reader(p)("run-x")
            out.append("M3-reader: a failing status reads as a state")
        except RuntimeError:
            pass
        if mod.mac_precheck(p) != []:
            out.append("M3-reader: a list whose started run is lost is refused")
        p = suite_file(t, list_text=STARTED + "\n", status={"run-d": "running"})
        if not mod.mac_precheck(p):
            out.append("M3-reader: a running run passes the pre-check")
        p = suite_file(t, list_text=STARTED + "\n", status={"run-d": "done"}, name_echo="'run-other'")
        if not mod.mac_precheck(p):
            out.append("M3-reader: a status line for another run is accepted")
        p = suite_file(t, list_text="", list_rc=3)
        if not mod.mac_precheck(p):
            out.append("M3-reader: a failing list reads as nothing running")
        if not mod.mac_precheck("relative/athena_suite.py"):
            out.append("M3-reader: a relative suite path passes")
    return out


CHECKS = {"A1-athena": a1, "A2-reserve": a2, "A3-gate": a3, "A4-env": a4, "M1-list": m1, "M2-status": m2,
          "M3-reader": m3}


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
    "busy-runs": ((('NEVER_RAN = ("refused", "busy")', 'NEVER_RAN = ("refused",)'),), "M1-list"),
    "foreign-hold-admitted": ((("and value == own_hold)", ")"),), "A1-athena"),
    "unreadable-reservation-admitted": (((
        "        out.append(f\"the athena reservation cannot be read: {value}\")", "        pass"),), "A1-athena"),
    "unread-processes-admitted": (((
        "    if suite_pids is None:\n        out.append(f\"the {SUITE_ACCOUNT} account's processes cannot be read: what "
        "runs is unknown\")\n    elif suite_pids:",
        "    if suite_pids:"),), "A1-athena"),
    "status-error-swallowed": (((
        "            out.append(f\"athena suite run {m['name']}: its status cannot be read ({type(e).__name__})\")\n"
        "            continue",
        "            continue"),), "M2-status"),
    "link-followed": ((("        st = os.lstat(path)\n    except FileNotFoundError:",
                        "        st = os.stat(path)\n    except FileNotFoundError:"),), "A2-reserve"),
    "dead-proc-is-quiet": ((("    except OSError:\n        return None\n    pids = []",
                             "    except OSError:\n        return []\n    pids = []"),), "A3-gate"),
    "old-env-builds": ((("    if not account:\n        return None, f\"{ENV_ACCOUNT} does not name the athena suite "
                         "account\"",
                         "    if not account:\n        return (lambda: []), None"),), "A4-env"),
}


class TestTheGate(unittest.TestCase):
    def test_a1_athena(self):
        self.assertEqual(a1(mg), [])

    def test_a2_reservation(self):
        self.assertEqual(a2(mg), [])

    def test_a3_gate(self):
        self.assertEqual(a3(mg), [])

    def test_a4_env(self):
        self.assertEqual(a4(mg), [])

    def test_m1_real_list(self):
        self.assertEqual(m1(mg), [])

    def test_m2_status(self):
        self.assertEqual(m2(mg), [])

    def test_m3_reader(self):
        self.assertEqual(m3(mg), [])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as t:
            p = suite_file(t, list_text=STARTED + "\n", status={"run-d": "running"})
            with mock.patch("builtins.print"):
                self.assertEqual(mg.main(["mac-precheck", p]), 1)
                self.assertEqual(mg.main(["nonsense"]), 2)
                with mock.patch.dict(os.environ, {mg.ENV_ACCOUNT: ME, mg.ENV_RESERVATION: os.path.join(t, "r.json"),
                                                  mg.ENV_HOLD: HOLD}):
                    with mock.patch.object(mg, "suite_account_pids", return_value=[]):
                        self.assertEqual(mg.main(["athena-check"]), 0)


class TestWitnesses(unittest.TestCase):
    def test_every_witness_is_red_by_its_own_clause(self):
        for name, (edits, clause) in WITNESSES.items():
            with self.subTest(name=name):
                self.assertEqual(CHECKS[clause](mg), [], f"{name}: {clause} is not green on the tree")
                got = CHECKS[clause](witness(edits))
                self.assertTrue([x for x in got if x.startswith(clause + ":")], f"{name}: survived")


if __name__ == "__main__":
    unittest.main()
