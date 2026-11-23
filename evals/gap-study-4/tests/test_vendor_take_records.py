#!/usr/bin/env python3
"""Integration slice: the driver's records for a non-Claude take read the harness's own native evidence.

_take_records looked for Claude Code's session file on every take, so a Gemini or Codex take always recorded "no
session file" in its cross-check and outcome, as if its own evidence were missing. Now a vendor take never looks for
Claude's file: its cross-check status comes from its own native evidence. Gemini: the retained snapshots' history
record (pending while no reviewed reader is registered; refused, with the reason as a cross-check problem, when the
snapshots are missing or inconsistent). Codex: pending until the rollout source audit lands. Pending is recorded as
pending (cross_check None), never as an empty problem list (a fabricated pass) and never as a missing file.
Claude takes are unchanged. Fakes and synthetic strings only.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_box_integration as tbi  # noqa: E402
import test_native_snapshot as tns  # noqa: E402


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


class VendorAdapter(tns.NativeAdapter):
    """NativeAdapter under a vendor harness name (the driver checks the adapter's name against the row's harness)."""


# The box's Codex lease postflight (box 34b1a3d2, glitch-06's ruling) refuses a lease home without exactly one registered
# auth.json, so a Codex stub take models the real road: a synthetic registered lease file planted in the take's config
# folder before the grant (mode 600, the reading user's, JSON with synthetic access and refresh tokens of 20+
# characters and no vendor prefix), its values in the take's secrets as lease_secrets puts them. On a tree without that
# postflight (no preflight.LEASE_CREDENTIAL) an auth.json is a credential-file refusal, so nothing is planted there.
LEASE_ACCESS = "synthetic-stub-lease-one-" + "a" * 12
LEASE_REFRESH = "synthetic-stub-lease-two-" + "b" * 12


def plant_lease(rig) -> bool:
    """Wrap the rig's driver so a Codex take's config folder holds the synthetic registered lease; True when planted."""
    from box import preflight
    if not hasattr(preflight, "LEASE_CREDENTIAL"):
        return False
    spec_for, secrets = rig.driver.spec_for, rig.driver.secrets

    def spec(row, cfg):
        if row["agent"]["harness"] == tbi.rt.CODEX:
            fd = os.open(os.path.join(cfg, preflight.LEASE_CREDENTIAL[tbi.rt.CODEX]),
                         os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w") as fh:
                json.dump({"tokens": {"access_token": LEASE_ACCESS, "refresh_token": LEASE_REFRESH}}, fh)
        return spec_for(row, cfg)
    rig.driver.spec_for = spec
    rig.driver.secrets = rig.repo.secrets = lambda: list(secrets()) + [("token", LEASE_ACCESS),
                                                                        ("token", LEASE_REFRESH)]
    return True


def drive_vendor(test, harness, *, native=True, fail_at=None):
    tbi.need(test, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
    root_cm = tbi.scratch_repo()
    root = root_cm.__enter__()
    test.addCleanup(root_cm.__exit__, None, None, None)
    home = tempfile.TemporaryDirectory()
    test.addCleanup(home.cleanup)
    # The vendors' own billing-route names are PENDING until named at the pinned version: none, for the fake only.
    patch = mock.patch.object(tbi.rt, "VENDOR_BILLING_ROUTE_VARIABLES", {tbi.rt.CODEX: (), tbi.rt.GEMINI: ()})
    patch.start()
    test.addCleanup(patch.stop)
    rig = tbi.Rig(tbi.drive, root, turns=[{"text": "a"}, {"text": "b"}])
    rig.driver.pin_for = lambda r: dict(tbi.PROFILE, model=r["model"], harness=r["agent"]["harness"])

    def make(r, take):
        cls = type("Vendor", (VendorAdapter if native else tbi.FakeAdapter,), {"name": harness})
        kw = {"home": take.config_dir, "fail_at": fail_at} if native else {}   # review MAJOR 1: the config folder
        rig.adapters.append(cls(rig.box, take, rig.turns, **kw))
        return rig.adapters[-1]
    rig.adapter_for = rig.driver.adapter_for = make
    plant_lease(rig)
    row = tbi.row(1, agent={"harness": harness, "version": tbi.PROFILE["version"]})
    with tbi.spying(rig.spy):
        cid = rig.driver.launch(row)
        try:
            rig.driver.drive(row, cid)
            refused = None
        except tbi.drive.DriveRefused as e:
            refused = e
        rig.driver.remove(cid)
    ledger = json.loads((Path(rig.take().folder) / "driver-ledger.json").read_text())
    return rig, ledger, refused


class VendorRecords(unittest.TestCase):
    def test_a_gemini_take_reads_its_own_evidence_and_records_pending(self):
        rig, ledger, refused = drive_vendor(self, "gemini")
        self.assertIsInstance(refused, tbi.drive.NativeCrossCheckPending)   # the checker road slice: never graded
        self.assertNotIn("no session file", json.dumps(ledger))
        self.assertIsNone(ledger["cross_check"], "pending is never an empty problem list")
        self.assertEqual(ledger["cross_check_status"]["status"], "pending")
        self.assertIn("no reviewed native-session reader", ledger["cross_check_status"]["why"])
        self.assertEqual(ledger["native_history"]["status"], "pending")
        self.assertIsNone(ledger["transcript"])
        self.assertIsNone(rig.take().cross_check)

    def test_a_codex_take_reads_its_own_rollouts_and_records_pending(self):
        """Codex slice 3: a Codex take retains its rollout per turn and stays pending until a Codex reader is
        registered, exactly as a Gemini take does; a Codex adapter that retained none is a real disagreement."""
        rig, ledger, refused = drive_vendor(self, "codex")
        self.assertIsInstance(refused, tbi.drive.NativeCrossCheckPending)   # the checker road slice: never graded
        self.assertNotIn("no session file", json.dumps(ledger))
        self.assertIsNone(ledger["cross_check"])
        self.assertEqual(ledger["cross_check_status"]["status"], "pending")
        self.assertEqual(ledger["native_history"]["status"], "pending")
        rig, ledger, refused = drive_vendor(self, "codex", native=False)
        self.assertEqual(ledger["cross_check_status"]["status"], "refused")
        self.assertIn("retained no native snapshot record", ledger["cross_check_status"]["why"])

    def test_missing_native_evidence_is_a_real_disagreement(self):
        rig, ledger, refused = drive_vendor(self, "gemini", fail_at=1)
        self.assertIsNotNone(refused, "a snapshot that was not retained still stops the take")
        self.assertEqual(ledger["cross_check_status"]["status"], "refused")
        self.assertEqual(ledger["cross_check"], [ledger["cross_check_status"]["why"]])
        self.assertTrue(rig.take().cross_check)

    def test_a_claude_take_is_unchanged(self):
        rig = tbi.Rig(tbi.drive, Path(tempfile.mkdtemp()), turns=[{"text": "a"}])
        case = tns.DriverRetains("test_an_adapter_without_a_native_session_is_unchanged")
        rig, o, folder, ledger = case.drive(plain=True)
        self.assertNotIn("cross_check_status", ledger)
        self.assertIsInstance(ledger["cross_check"], list)


if __name__ == "__main__":
    unittest.main()
