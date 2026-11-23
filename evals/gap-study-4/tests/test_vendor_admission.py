#!/usr/bin/env python3
"""Lane vendor-admission T1: a vendor take or walk is graded only through a registered reader and an agreed cross-check.

glitch-b5's lane vendor-admission (16 Oct 2026), task T1, defence in depth at the grading callers. A Codex or Gemini
take reaches endstate.Evidence.load (and so a grader) only when both hold: the reader registry the caller holds
(native_reader_registration.production_readers(), or `readers` handed in) includes that harness, and the native
cross-check handed in is exactly {"status": "agreed", "why": None} (drive.gemini_cross_check's and
drive.codex_cross_check's one agreed shape). The take road and the walk road read the cross-check from the driver
ledger's cross_check_status; claude-code is untouched.

  VA-walk     run.grade_walk on a synthetic vendor walk (test_walk_grade_seam's folder), with TEST-DATA vendor TABLE
              entries patched in so that only the guard stands between the walk and the reader: each case refuses
              naming its reason, and Evidence.load is never entered.
  VA-take     run.grade_committed on the same folder as a take folder takes/s1/1: the same cases, the same refusals.
  VA-control  a registered reader and the agreed cross-check reach Evidence.load and the grader on both roads, and a
              claude-code walk and take need neither.
  VA-ledger   the take road with its driver-ledger.json deleted or unparseable (a registered reader, the agreed
              shape otherwise): refused naming the cross-check, before Evidence.load (review bea6e50 finding 1).
  VA-witness  in-memory mutants of run.py, one per guard site (the guard's body, each road's call), go red: the
              unregistered-reader case reaches Evidence.load; and ledger_cross_check's unreadable-ledger fallback
              flipped to the agreed shape lets VA-ledger's cases reach it.

The regrade road (walk_regrade.regrade_doc's own `cross`) is tests/test_vendor_admission_regrade.py. Every fixture is
synthetic: no walk's records are read, nothing under rehearsals/ or native-readers/ is written.
"""

from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_walk_grade_seam as seam  # noqa: E402

run = variants = endstate = hb = None
VENDORS = ("codex", "gemini")
AGREED = {"status": "agreed", "why": None}


def setUpModule():
    global run, variants, endstate, hb
    seam.setUpModule()
    run, variants = seam.run, seam.variants
    from graders import endstate
    import harness_bookkeeping as hb


def stand_in_reader(raw, ordinal):
    raise AssertionError("the stand-in reader is never called by grading")


def other(harness: str) -> str:
    return "gemini" if harness == "codex" else "codex"


ABSENT = object()


def cases(harness: str) -> dict:
    """name -> (readers, cross-check in the ledger (ABSENT: no key), the words the refusal must carry)."""
    r = {harness: stand_in_reader}
    return {
        "unregistered reader, agreed": ({}, AGREED, "no registered"),
        "the other vendor's reader only": ({other(harness): stand_in_reader}, AGREED, "no registered"),
        "a reader of None": ({harness: None}, AGREED, "no registered"),
        "registered, cross-check refused": (r, {"status": "refused", "why": "a stand-in refusal"}, "cross-check"),
        "registered, cross-check missing": (r, ABSENT, "cross-check"),
        "registered, cross-check None": (r, None, "cross-check"),
        "registered, extra keys": (r, dict(AGREED, interactions=2), "cross-check"),
        "registered, why not None": (r, {"status": "agreed", "why": ""}, "cross-check"),
        "registered, status spelled otherwise": (r, {"status": "Agreed", "why": None}, "cross-check"),
        "registered, a list": (r, [["status", "agreed"], ["why", None]], "cross-check"),
    }


def vendor_walk(root: Path, harness: str, cross=ABSENT, task: str = "plan-gate"):
    """The seam's vendor walk (its ledger carries the agreed cross-check) with `cross` in its place, or none (ABSENT)."""
    entry, folder = seam.walk_folder(root, task, variants.cells(task)[0], harness)
    path = folder / "driver-ledger.json"
    ledger = json.loads(path.read_text())
    del ledger["cross_check_status"]
    if cross is not ABSENT:
        ledger["cross_check_status"] = cross
    path.write_text(json.dumps(ledger))
    return entry, folder


def fake_table():
    """TEST DATA, as E-vendor's: synthetic vendor entries, so production Evidence.load would read a vendor take."""
    return {h: hb.Entry(home_paths=(f"synthetic-{h}-home/*",), run_tree_paths=(), grounds=("TEST DATA",),
                        not_excluded=()) for h in VENDORS}


class Reached(Exception):
    """The road entered endstate.Evidence.load."""


def spying_load(log: list):
    real = endstate.Evidence.load

    def load(folder, table=None):
        log.append(str(folder))
        return real(folder, table)
    return load


def grader_spy(log: list):
    def regrade(name, row, spec, transcript, evidence):
        log.append(name)
        return {"label": "synthetic"}, str(HERE / "graders" / f"{name}.py")
    return regrade


def walk_road(mod, harness: str, readers, cross) -> tuple[list, object]:
    """(Evidence.load calls, the outcome: the returned document or the exception) of mod.grade_walk."""
    loads, graded = [], []
    with tempfile.TemporaryDirectory() as tmp:
        entry, folder = vendor_walk(Path(tmp), harness, cross)
        with mock.patch.dict(hb.TABLE, fake_table()), \
                mock.patch.object(endstate.Evidence, "load", spying_load(loads)), \
                mock.patch.object(mod, "regrade", grader_spy(graded)):
            try:
                got = mod.grade_walk(entry, folder, readers=readers)
            except Exception as e:  # noqa: BLE001 - the refusal is the outcome under test
                got = e
    return loads, got


LEDGER_DAMAGE = {
    "deleted": lambda path: path.unlink(),
    "unparseable": lambda path: path.write_text("{not json"),
}


def take_road(mod, harness: str, readers, cross, ledger: str | None = None) -> tuple[list, object]:
    """(Evidence.load calls, the outcome) of mod.grade_committed on the walk folder moved to takes/s1/1, its driver
    ledger then damaged as LEDGER_DAMAGE[ledger] says (None: left readable)."""
    loads, graded = [], []
    with tempfile.TemporaryDirectory() as tmp:
        entry, folder = vendor_walk(Path(tmp), harness, cross)
        row = dict(mod.walk_row(entry, json.loads((folder / "driver-ledger.json").read_text())),
                   record_dir="takes/s1/1", slot="s1", attempt=1)
        dest = Path(tmp) / "takes" / "s1" / "1"
        dest.parent.mkdir(parents=True)
        folder.rename(dest)
        if ledger is not None:
            LEDGER_DAMAGE[ledger](dest / "driver-ledger.json")
        committed = lambda repo, *args: "" if args[0] == "status" else "takes/s1/1/transcript.jsonl"  # noqa: E731
        with mock.patch.dict(hb.TABLE, fake_table()), \
                mock.patch.object(endstate.Evidence, "load", spying_load(loads)), \
                mock.patch.object(mod, "regrade", grader_spy(graded)), \
                mock.patch.object(mod, "HERE", Path(tmp)), mock.patch.object(mod, "REPO", Path(tmp)), \
                mock.patch.object(mod.takes, "_git_at", committed), \
                mock.patch.object(mod.mode_binding, "TAKES_DIR", "takes"):
            try:
                got = mod.grade_committed(row, {}, readers=readers)
            except Exception as e:  # noqa: BLE001 - the refusal is the outcome under test
                got = e
    return loads, got


ROADS = {"walk": walk_road, "take": take_road}


def ledger_problems(mod) -> list:
    """The take road with its driver ledger deleted or unparseable, a registered reader and an agreed cross-check
    otherwise: refused naming the cross-check, Evidence.load never entered (an unreadable ledger is never agreement)."""
    out = []
    for harness in VENDORS:
        for damage in LEDGER_DAMAGE:
            loads, got = take_road(mod, harness, {harness: stand_in_reader}, AGREED, ledger=damage)
            where = f"take {harness} ledger {damage}"
            if loads:
                out.append(f"{where}: reached Evidence.load")
            if not isinstance(got, Exception):
                out.append(f"{where}: was not refused ({str(got)[:80]})")
            elif type(got).__name__ != "VendorAdmissionRefused" or "cross-check" not in str(got):
                out.append(f"{where}: refused as {type(got).__name__}: {str(got)[:120]}")
    return out


def refusal_problems(mod) -> list:
    """Every case on every road and vendor: refused naming its reason, Evidence.load never entered."""
    out = []
    for road, drive_road in ROADS.items():
        for harness in VENDORS:
            for name, (readers, cross, words) in cases(harness).items():
                loads, got = drive_road(mod, harness, readers, cross)
                where = f"{road} {harness} {name}"
                if loads:
                    out.append(f"{where}: reached Evidence.load")
                if not isinstance(got, Exception):
                    out.append(f"{where}: was not refused ({str(got)[:80]})")
                elif type(got).__name__ != "VendorAdmissionRefused" or words not in str(got):
                    out.append(f"{where}: refused as {type(got).__name__}: {str(got)[:120]}")
    return out


class Refusals(unittest.TestCase):
    def test_va_every_unadmitted_vendor_case_refuses_before_the_reader(self):
        self.assertEqual(refusal_problems(run), [])

    def test_va_an_unreadable_take_ledger_refuses_before_the_reader(self):
        # review bea6e50 finding 1 (round-2 ruling 1): a deleted or unparseable driver-ledger.json is no agreement
        self.assertEqual(ledger_problems(run), [])

    def test_va_production_readers_on_this_tree_hold_the_accepted_readers(self):
        # Lane freeze-gates-fix S8 (glitch-f1's ruling 3, 21 Oct 2026): readers=None is the production registry. Since
        # Javier's acceptance commit (5457e75e) this tree registers both vendor readers; a harness the registry does
        # not hold still refuses before the reader, read through that same production call.
        import native_reader_registration as nrr
        self.assertEqual(nrr.production_readers(), {"codex": nrr.codex_reader, "gemini": nrr.gemini_reader})
        real = nrr.production_readers
        for harness in VENDORS:
            without = {h: r for h, r in real().items() if h != harness}
            with mock.patch.object(nrr, "production_readers", lambda study=None, without=without: dict(without)):
                for road, drive_road in ROADS.items():
                    loads, got = drive_road(run, harness, None, AGREED)
                    self.assertEqual(loads, [], f"{road} {harness}")
                    self.assertIsInstance(got, run.VendorAdmissionRefused, f"{road} {harness}: {got!r}")
                    self.assertIn("no registered", str(got))

    def test_va_a_refusing_registry_refuses_the_take(self):
        import native_reader_registration as nrr

        def refusing(study=None):
            raise nrr.RegistrationRefused("a stand-in refusal")
        with mock.patch.object(nrr, "production_readers", refusing):
            for road, drive_road in ROADS.items():
                loads, got = drive_road(run, "gemini", None, AGREED)
                self.assertEqual(loads, [], road)
                self.assertIsInstance(got, run.VendorAdmissionRefused, f"{road}: {got!r}")
                self.assertIn("a stand-in refusal", str(got))

    def test_va_a_pending_walk_stays_the_pending_document(self):
        # the walk road's pending walk is pending_walk.status's document, before any admission (unchanged)
        loads, got = walk_road(run, "gemini", {}, {"status": "pending", "why": "no reader yet"})
        self.assertEqual(loads, [])
        self.assertEqual((got["graded"], got["status"]), (False, "pending-native-reader"))
        loads, got = take_road(run, "gemini", {"gemini": stand_in_reader}, {"status": "pending", "why": "no reader"})
        self.assertEqual(loads, [])
        self.assertIsInstance(got, run.VendorAdmissionRefused, repr(got))


class Controls(unittest.TestCase):
    def test_va_control_registered_and_agreed_reach_the_reader(self):
        for road, drive_road in ROADS.items():
            for harness in VENDORS:
                loads, got = drive_road(run, harness, {harness: stand_in_reader}, AGREED)
                self.assertEqual(len(loads), 1, f"{road} {harness}: {got!r}")
                self.assertNotIsInstance(got, Exception, f"{road} {harness}: {got!r}")

    def test_va_evidence_of_another_vendor_never_reaches_a_grader(self):
        # a walk admitted as gemini (its row, its ledger, its reader, its agreed cross-check) whose evidence names
        # codex: run.require_evidence_identity refuses it after the reader and before any grader
        loads, graded = [], []
        with tempfile.TemporaryDirectory() as tmp:
            entry, folder = vendor_walk(Path(tmp), "gemini", AGREED)
            ledger = folder / "evidence" / "ledger.jsonl"
            lines = ledger.read_text().splitlines()
            lines[0] = json.dumps(dict(json.loads(lines[0]), agent=dict(seam.VENDOR["codex"][1])))
            ledger.write_text("\n".join(lines) + "\n")
            with mock.patch.dict(hb.TABLE, fake_table()), \
                    mock.patch.object(endstate.Evidence, "load", spying_load(loads)), \
                    mock.patch.object(run, "regrade", grader_spy(graded)):
                with self.assertRaises(ValueError) as cm:
                    run.grade_walk(entry, folder, readers={"gemini": stand_in_reader})
        self.assertEqual(len(loads), 1)
        self.assertEqual(graded, [])
        self.assertIn("the evidence names another model or agent", str(cm.exception))

    def test_va_control_claude_code_needs_neither(self):
        loads, graded = [], []
        with tempfile.TemporaryDirectory() as tmp:
            entry, folder = seam.walk_folder(Path(tmp), "plan-gate", variants.cells("plan-gate")[0])
            with mock.patch.object(endstate.Evidence, "load", spying_load(loads)), \
                    mock.patch.object(run, "regrade", grader_spy(graded)):
                got = run.grade_walk(entry, folder)
        self.assertEqual(len(loads), 1)
        self.assertTrue(got["graded"])
        self.assertEqual(graded, ["plan_gate"])


def mutant(old: str, new: str):
    src = Path(run.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutation site occurs {src.count(old)} times in run.py: {old!r}")
    m = types.ModuleType("run_mutant")
    m.__file__ = run.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), run.__file__ + " (witness)", "exec"), m.__dict__)  # noqa: S102
    finally:
        del sys.modules[m.__name__]
    return m


WITNESSES = {
    "the guard's body": ("    if harness not in VENDOR_HARNESSES:\n        return\n",
                         "    if True:\n        return\n", ("walk", "take")),
    "the walk road's call": ("    vendor_admission(row[\"agent\"].get(\"harness\"), readers, "
                             "ledger.get(\"cross_check_status\"))\n", "", ("walk",)),
    "the take road's call": ("    vendor_admission((row.get(\"agent\") or {}).get(\"harness\"), readers, "
                             "ledger_cross_check(path))\n", "", ("take",)),
    "an unreadable ledger read as agreed": ("    except (OSError, ValueError):\n        return None\n",
                                            "    except (OSError, ValueError):\n"
                                            "        return {'status': 'agreed', 'why': None}\n", ()),
}


class Witnesses(unittest.TestCase):
    def test_va_witness_each_guard_site_removed_goes_red(self):
        for name, (old, new, roads) in WITNESSES.items():
            with self.subTest(witness=name):
                mod = mutant(old, new)
                for road in roads:
                    for harness in VENDORS:
                        loads, got = ROADS[road](mod, harness, {}, AGREED)
                        self.assertTrue(loads, f"witness {name}: {road} {harness} still refused: {got!r}")

    def test_va_witness_an_unreadable_ledger_read_as_agreed_goes_red(self):
        # round-2 ruling 1: ledger_cross_check's fallback flipped to the agreed shape reaches Evidence.load
        old, new, _ = WITNESSES["an unreadable ledger read as agreed"]
        problems = ledger_problems(mutant(old, new))
        self.assertEqual(len(problems), 2 * len(VENDORS) * len(LEDGER_DAMAGE), problems)


if __name__ == "__main__":
    unittest.main()
