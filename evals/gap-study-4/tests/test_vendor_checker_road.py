#!/usr/bin/env python3
"""Integration slice: a vendor take whose native cross-check is pending is neither graded nor readers-disagree.

Registered text (quoted in lane-reports/vendor-checker-road-2026-10-14.md): D8's table names each vendor's transcript
as the host-captured stream "cross-checked with" its native record (the Codex rollout file; the Gemini session file
under GEMINI_CLI_HOME), and the plan's graded record is the captured stream "cross-checked against the session file".
So the cross-check is part of what is graded, and a take whose cross-check cannot run yet is not gradable. Routing's
table has no pending row, and adding one would be a new rule, so the driver stops the take with a typed
NativeCrossCheckPending (a DriveRefused) after cleanup, ledger and scan: batch records it failed after its drive
started, a ruling, never graded, never a re-run, never readers-disagree, never a harness-error for the nightly count.
A refused native cross-check stays readers-disagree. Fakes only.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import batch  # noqa: E402
import test_box_integration as tbi  # noqa: E402
import test_vendor_take_records as tvr  # noqa: E402
from graders import labels4  # noqa: E402


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


class PendingStops(unittest.TestCase):
    def test_a_pending_vendor_take_is_stopped_typed_and_never_graded(self):
        for harness, native in (("gemini", True), ("codex", True)):     # Codex slice 3: Codex retains its rollout
            with self.subTest(harness=harness):
                rig, ledger, refused = tvr.drive_vendor(self, harness, native=native)
                self.assertIsInstance(refused, getattr(tbi.drive, "NativeCrossCheckPending", ()),
                                      f"a pending native cross-check did not stop the take: {refused!r}")
                self.assertIn("native cross-check pending", str(refused))
                self.assertEqual(rig.checked, [], "the checker never grades a take whose cross-check is pending")
                self.assertEqual(ledger["cross_check_status"]["status"], "pending")

    def test_through_batch_it_waits_for_a_ruling_and_counts_apart(self):
        patch = mock.patch.object(tbi.rt, "VENDOR_BILLING_ROUTE_VARIABLES", {tbi.rt.CODEX: (), tbi.rt.GEMINI: ()})
        patch.start()
        self.addCleanup(patch.stop)
        money = mock.patch.object(batch, "bills_money", lambda row: False)   # the money gate is W7C's, out of scope
        money.start()
        self.addCleanup(money.stop)
        root_cm = tbi.scratch_repo()
        root = root_cm.__enter__()
        self.addCleanup(root_cm.__exit__, None, None, None)
        rig = tbi.Rig(tbi.drive, root, turns=[{"text": "a"}])
        rig.driver.pin_for = lambda r: dict(tbi.PROFILE, model=r["model"], harness=r["agent"]["harness"])
        import tempfile
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        rig.adapter_for = rig.driver.adapter_for = lambda r, take: rig.adapters.append(       # Codex slice 3: native
            type("Vendor", (tvr.VendorAdapter,), {"name": "codex"})(rig.box, take, rig.turns, home=take.config_dir)) \
            or rig.adapters[-1]
        tvr.plant_lease(rig)                          # the box's lease postflight: the lease home holds one auth.json
        table = tbi.table()
        table["pin_profiles"]["codex"] = {tbi.MODEL: dict(tbi.PROFILE)}
        b = batch.Batch(rig.driver, rig.repo, tbi.Window(), table=table, serial=True)
        row = tbi.row(1, agent={"harness": "codex", "version": tbi.PROFILE["version"]})
        import prereg
        frozen = mock.patch.object(prereg, "require_frozen", lambda what: {"rows": [row]})   # the row, pre-registered
        frozen.start()
        self.addCleanup(frozen.stop)
        with tbi.spying(rig.spy):
            out = b.run([row])
        self.assertEqual(len(out), 1, f"the loop stopped before the take: {b.stopped}")
        self.assertEqual(out[0]["state"], labels4.FAILED)
        self.assertIn("native cross-check pending", out[0]["reason"])
        self.assertTrue(batch.needs_ruling(out[0]))
        self.assertIs(out[0]["rerun"], False)
        self.assertEqual(b.night_counts, {"harness_error": 0, "failed_after_drive_started": 1})


class GeminiThroughBatch(unittest.TestCase):
    def test_the_native_history_road_binds_to_the_batch_outcome(self):
        """Review batch 6 N8: a Gemini take with retained snapshots, through batch: its ledger's native history is
        pending, and the batch outcome is the typed stop waiting for a ruling."""
        import json
        import tempfile
        for name, value in (("VENDOR_BILLING_ROUTE_VARIABLES", {tbi.rt.CODEX: (), tbi.rt.GEMINI: ()}),):
            patch = mock.patch.object(tbi.rt, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        money = mock.patch.object(batch, "bills_money", lambda row: False)   # the money gate is W7C's, out of scope
        money.start()
        self.addCleanup(money.stop)
        root_cm = tbi.scratch_repo()
        root = root_cm.__enter__()
        self.addCleanup(root_cm.__exit__, None, None, None)
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        rig = tbi.Rig(tbi.drive, root, turns=[{"text": "a"}, {"text": "b"}])
        rig.driver.pin_for = lambda r: dict(tbi.PROFILE, model=r["model"], harness=r["agent"]["harness"])
        cls = type("Vendor", (tvr.VendorAdapter,), {"name": "gemini"})
        rig.adapter_for = rig.driver.adapter_for = lambda r, take: rig.adapters.append(
            cls(rig.box, take, rig.turns, home=take.config_dir)) or rig.adapters[-1]
        table = tbi.table()
        table["pin_profiles"]["gemini"] = {tbi.MODEL: dict(tbi.PROFILE)}
        row = tbi.row(1, agent={"harness": "gemini", "version": tbi.PROFILE["version"]})
        import prereg
        frozen = mock.patch.object(prereg, "require_frozen", lambda what: {"rows": [row]})
        frozen.start()
        self.addCleanup(frozen.stop)
        b = batch.Batch(rig.driver, rig.repo, tbi.Window(), table=table, serial=True)
        with tbi.spying(rig.spy):
            out = b.run([row])
        self.assertEqual(len(out), 1, f"the loop stopped before the take: {b.stopped}")
        self.assertEqual(out[0]["state"], labels4.FAILED)
        self.assertIn("native cross-check pending", out[0]["reason"])
        self.assertTrue(batch.needs_ruling(out[0]))
        ledger = json.loads((Path(rig.take().folder) / "driver-ledger.json").read_text())
        self.assertEqual(ledger["native_history"]["status"], "pending")
        self.assertEqual([r["file"] for r in ledger["native_snapshots"]], ["native-turn-1.jsonl", "native-turn-2.jsonl"])
        self.assertEqual(ledger["cross_check_status"]["status"], "pending")


class CheckerNeverReadsPendingAsAgreement(unittest.TestCase):
    def test_the_checker_refuses_a_pending_cross_check(self):
        import types
        checker = tbi.drive.take_checker(design_for=lambda r, t: None)
        take = types.SimpleNamespace(cross_check=None, folder="/nonexistent-take-folder")
        with self.assertRaises(tbi.drive.NativeCrossCheckPending):
            checker({}, take, [])
        take.cross_check = []
        got = checker({}, take, [])                     # a Claude take with no transcript: readers-disagree
        self.assertEqual(got["checker_reasons"], [tbi.drive.READERS_DISAGREE])


class RefusedStaysReadersDisagree(unittest.TestCase):
    def test_a_refused_native_cross_check_is_readers_disagree(self):
        rig, ledger, refused = tvr.drive_vendor(self, "gemini", fail_at=1)
        self.assertNotIsInstance(refused, getattr(tbi.drive, "NativeCrossCheckPending", ()))
        self.assertEqual(ledger["cross_check_status"]["status"], "refused")
        self.assertEqual(ledger["cross_check"], [ledger["cross_check_status"]["why"]])


if __name__ == "__main__":
    unittest.main()
