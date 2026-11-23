#!/usr/bin/env python3
"""Lane vendor-admission T1, the regrade road: walk_regrade.regrade_doc grades only through its own agreed cross-check.

A pending vendor walk's driver ledger still says pending, so the regrade passes the guard its OWN cross-check (the
one it re-derives from the committed bytes, walk_regrade.py's `cross`) and the registry it holds. The guard
(run.vendor_admission) refuses a cross-check that is not exactly {"status": "agreed", "why": None} and a registry
without the walk's harness, even when the cross-check itself was produced some other way.

  VA-regrade-shape     a cross-check of status agreed carrying an extra key refuses the regrade, naming it.
  VA-regrade-reader    an agreed cross-check under a registry without the walk's harness refuses, naming it.
  VA-regrade-control   the walk's own reader and agreed cross-check regrade it (the Regrade test's road).
  VA-regrade-witness   walk_regrade.py compiled in memory without its guard call goes red on both cases.

The walk is test_pending_walk's: a Gemini walk on the real road and a fake box, in a scratch repository, accepted by a
committed record there. No model, container, network or study-tree write.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_box_integration as tbi  # noqa: E402
import test_pending_walk as tpw  # noqa: E402

AGREED = {"status": "agreed", "why": None}
GUARD = "        admitted(harness, readers, cross)\n"


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


def mutant(old: str, new: str):
    import walk_regrade
    src = Path(walk_regrade.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutation site occurs {src.count(old)} times in walk_regrade.py: {old!r}")
    m = types.ModuleType("walk_regrade_mutant")
    m.__file__ = walk_regrade.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), walk_regrade.__file__ + " (witness)", "exec"), m.__dict__)  # noqa: S102
    finally:
        del sys.modules[m.__name__]
    return m


class RegradeAdmission(unittest.TestCase):
    def setUp(self):
        self.road = tpw.walked(self)
        self.road.accept()
        self.assertEqual(set(self.road.nrr.production_readers(self.road.study)), {"gemini"})

    def outcome(self, mod, *, cross=None, readers=None):
        import drive
        stand_in = (lambda *a, **k: dict(cross)) if cross is not None else drive.gemini_cross_check  # noqa: E731
        with mock.patch.object(drive, "gemini_cross_check", stand_in):
            try:
                return mod.regrade_doc(tpw.WALK, self.road.study, readers=readers, grade=tpw.stand_in_grade)
            except Exception as e:  # noqa: BLE001 - the refusal is the outcome under test
                return e

    def cases(self):
        return {"shape": dict(cross=dict(AGREED, interactions=2)),
                "reader": dict(cross=AGREED, readers={"codex": self.road.nrr.codex_reader})}

    def test_va_regrade_refuses_each_case_naming_it(self):
        import walk_regrade
        for name, kw in self.cases().items():
            with self.subTest(case=name):
                got = self.outcome(walk_regrade, **kw)
                self.assertIsInstance(got, walk_regrade.RegradeRefused, repr(got))
                self.assertIn("no registered gemini native reader" if name == "reader" else "cross-check", str(got))
                self.assertIn("vendor admission", str(got))

    def test_va_regrade_control(self):
        import walk_regrade
        got = self.outcome(walk_regrade)
        self.assertNotIsInstance(got, Exception, repr(got))
        self.assertEqual((got["cross_check"], got["graded"]), (AGREED, True))

    def test_va_regrade_witness_without_the_guard_goes_red(self):
        mod = mutant(GUARD, "")
        for name, kw in self.cases().items():
            with self.subTest(case=name):
                got = self.outcome(mod, **kw)
                self.assertFalse(isinstance(got, Exception), f"witness: {name} still refused: {got!r}")
                self.assertTrue(got["graded"], f"witness: {name}")


if __name__ == "__main__":
    unittest.main()
