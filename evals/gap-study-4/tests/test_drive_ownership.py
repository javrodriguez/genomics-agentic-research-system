#!/usr/bin/env python3
"""The ownership road in drive.py: the box lane's call contract (live-box-2026-10-13.md at 81ede46d, routed by glitch-06
on 14 Oct 2026), driven on the shared fake box (test_box_integration's Rig) with its fake ownership road, since
box/ownership.py is the box lane's and may be absent from this tree.

  O1-grant     a clean take is granted once, after its run tree, config folder and evidence folder exist and before
               any runtime call of run_take.launch, by the take image's id, the three folders named exactly; the grant
               record is written and committed, and the driver ledger carries both steps as operator steps
  O2-restore   the restore follows the teardown (after the take container's removal) and comes before the postflight
               and before any scan, naming every container the take recorded
  O3-launch    a LaunchError's partial teardown is followed by a restore naming the launch's recorded ids; a failed
               restore there holds the take: its records are never read for a commit and its config folder is kept
  O4-held      a failed restore after a drive: DriveRefused naming the restore, no postflight, no scan, no commit of
               the take's records, no removal of its config folder, the restore record written ok false
  O5-grant-fails  a failed grant: nothing launched, a restore with no ids, the grant record ok false, DriveRefused
  O6-image     a tag (anything but the lock's sha256 id) is refused before the grant
  O7-road      the interface: the fake passes ownership_problems, a wrong signature or a missing road does not, and a
               driver with no road refuses at launch before any folder

Mutants (MUTANTS, each killed by its own check's line): grant skipped; restore moved after postflight; restore skipped
on a LaunchError; a scan running after a failed restore; a commit reading a held take's records.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import test_box_integration as tbi  # noqa: E402
from box import run_take as rt  # noqa: E402
from box import scan_record  # noqa: E402


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


@contextmanager
def watched(mod, order: list):
    """Record each postflight and each scan into `order`, beside the fake road's own events."""
    post, scan = mod.TakeDriver._postflight, scan_record.scan

    def postflight(self, take, row):
        order.append("postflight")
        return post(self, take, row)

    def scanning(*a, **kw):
        order.append("scan")
        return scan(*a, **kw)
    with mock.patch.object(mod.TakeDriver, "_postflight", postflight), mock.patch.object(scan_record, "scan", scanning):
        yield order


class OrderedOwnership(tbi.FakeOwnership):
    """The fake road, its calls also appended to a shared order list."""

    def __init__(self, order, box=None, **kw):
        super().__init__(box, **kw)
        self.order = order

    def grant(self, runtime, *, image, run_tree, config_dir, evidence_dir, caller_env=None):
        self.order.append("grant")
        return super().grant(runtime, image=image, run_tree=run_tree, config_dir=config_dir,
                             evidence_dir=evidence_dir, caller_env=caller_env)

    def restore(self, runtime, *, image, run_tree, config_dir, evidence_dir, ids, caller_env=None):
        self.order.append("restore")
        return super().restore(runtime, image=image, run_tree=run_tree, config_dir=config_dir,
                               evidence_dir=evidence_dir, ids=ids, caller_env=caller_env)


def launch_index(calls) -> int:
    """The index of run_take.launch's first runtime call (its network or a container created), len(calls) if none."""
    for i, a in enumerate(calls):
        if a[:3] == ["docker", "network", "create"] or a[:2] == ["docker", "create"]:
            return i
    return len(calls)


def read(path) -> dict | None:
    return json.loads(Path(path).read_text(encoding="utf-8")) if os.path.isfile(path) else None


# ------------------------------------------------------------------------------------------------ the bound checks
@tbi.guarded("O1-grant")
def o1_grant(mod, p):
    out = []
    with tbi.scratch_repo() as root:
        order = []
        rig = tbi.Rig(mod, root)
        rig.ownership = road = OrderedOwnership(order, rig.box)
        rig.driver.ownership = road
        with watched(mod, order):
            b, got = tbi.run_batch(rig, [tbi.row(1)])
        take = rig.take()
        grants = [e for n, e in road.events if n == "grant"]
        if len(grants) != 1:
            return [f"{p}: a clean take was granted {len(grants)} times, not once"]
        g = grants[0]
        if g["exist"] != [True, True, True]:
            out.append(f"{p}: the grant ran before its folders existed: {g['exist']}")
        if g["at"] > launch_index(rig.box.calls) or launch_index(rig.box.calls[:g["at"]]) != g["at"]:
            out.append(f"{p}: the grant did not come before run_take.launch's first runtime call")
        want = {"image": tbi.IMAGE, "run_tree": take.spec.run_tree, "config_dir": take.config_dir,
                "evidence_dir": take.evidence_dir}
        if {k: g[k] for k in want} != want:
            out.append(f"{p}: the grant does not name the take's image id and its three folders: {g}")
        rec = read(os.path.join(take.folder, mod.OWNERSHIP_GRANT_RECORD))
        if rec is None or rec.get("ok") is not True:
            out.append(f"{p}: no grant record with ok true")
        committed = tbi.git(root, "show", "--name-only", "--format=", "HEAD").splitlines()
        for name in (mod.OWNERSHIP_GRANT_RECORD, mod.OWNERSHIP_RESTORE_RECORD):
            if os.path.relpath(os.path.join(take.folder, name), root) not in committed:
                out.append(f"{p}: {name} was not committed with the take")
        ledger = read(os.path.join(take.folder, mod.LEDGER_FILE)) or {}
        steps = ledger.get("operator_steps")
        if [s.get("step") for s in steps or []] != list(mod.OWNERSHIP_STEPS) or not all(
                s.get("ok") is True for s in steps):
            out.append(f"{p}: the driver ledger does not carry both ownership steps as ok operator steps: {steps}")
        if b.stopped is not None:
            out.append(f"{p}: a clean take stopped the loop: {b.stopped}")
    return out


@tbi.guarded("O2-restore")
def o2_restore(mod, p):
    out = []
    with tbi.scratch_repo() as root:
        order = []
        rig = tbi.Rig(mod, root)
        rig.driver.ownership = road = OrderedOwnership(order, rig.box)
        r = tbi.row(1)
        with watched(mod, order), tbi.spying(rig.spy):
            cid = rig.driver.launch(r)
            rig.driver.drive(r, cid)
            rig.driver.remove(cid)
        take = rig.take()
        rest = [e for n, e in road.events if n == "restore"]
        if len(rest) != 1:
            return [f"{p}: a clean take was restored {len(rest)} times, not once"]
        if rest[0]["ids"] != list(take.launched.ids()):
            out.append(f"{p}: the restore does not name every recorded container: {rest[0]['ids']}")
        rms = [i for i, a in enumerate(rig.box.calls) if a[:3] == ["docker", "rm", "--force"]]
        if not rms or rest[0]["at"] < rms[0] + 1:
            out.append(f"{p}: the restore came before the teardown removed the take's containers")
        seq = [x for x in order if x in ("restore", "postflight", "scan")]
        if seq[:3] != ["restore", "postflight", "scan"]:
            out.append(f"{p}: the restore is not before the postflight and the scan: {seq}")
        rec = read(os.path.join(take.folder, mod.OWNERSHIP_RESTORE_RECORD))
        if rec is None or rec.get("ok") is not True:
            out.append(f"{p}: no restore record with ok true")
    return out


def failing_start(box):
    real = box.run

    def run(argv, env=None, timeout=None):
        if list(argv)[:2] == ["docker", "start"] and box.kind(argv[2]) == "take":
            return rt.Completed(1, "", "synthetic start failure")
        return real(argv, env=env, timeout=timeout)
    box.run = run


@tbi.guarded("O3-launch")
def o3_launch(mod, p):
    out = []
    for fail in (False, True):
        with tbi.scratch_repo() as root:
            rig = tbi.Rig(mod, root)
            rig.driver.ownership = road = tbi.FakeOwnership(rig.box, fail_restore=fail)
            failing_start(rig.box)
            r = tbi.row(1)
            try:
                with tbi.spying(rig.spy):
                    rig.driver.launch(r)
                out.append(f"{p}: a failed start did not raise")
                continue
            except rt.LaunchError as e:
                launched = e.launched
            rest = [e for n, e in road.events if n == "restore"]
            if len(rest) != 1 or rest[0]["ids"] != list(launched.ids()):
                out.append(f"{p}: a LaunchError was not followed by one restore of its recorded ids: {rest}")
            elif rest[0]["at"] < len(launched.torn_down):
                out.append(f"{p}: the restore came before the launch's partial teardown")
            take = rig.take()
            if fail:
                try:
                    rig.driver.record_files(r, 1)
                    out.append(f"{p}: a held take's records were handed to the commit")
                except mod.DriveRefused:
                    pass
                if not os.path.isdir(take.config_dir):
                    out.append(f"{p}: a held take's config folder was removed")
    return out


@tbi.guarded("O4-held")
def o4_held(mod, p):
    out = []
    with tbi.scratch_repo() as root:
        order = []
        rig = tbi.Rig(mod, root)
        rig.driver.ownership = OrderedOwnership(order, rig.box, fail_restore=True)
        r = tbi.row(1)
        with watched(mod, order), tbi.spying(rig.spy):
            cid = rig.driver.launch(r)
            try:
                rig.driver.drive(r, cid)
                out.append(f"{p}: a failed restore did not stop the drive")
            except mod.DriveRefused as e:
                if "ownership restore" not in str(e):
                    out.append(f"{p}: the stop does not name the restore: {e}")
            rig.driver.remove(cid)
        if "postflight" in order or "scan" in order:
            out.append(f"{p}: a failed restore was followed by {[x for x in order if x in ('postflight', 'scan')]}")
        take = rig.take()
        rec = read(os.path.join(take.folder, mod.OWNERSHIP_RESTORE_RECORD))
        if rec is None or rec.get("ok") is not False:
            out.append(f"{p}: the restore record does not say ok false")
        try:
            files = rig.driver.record_files(r, 1)
            out.append(f"{p}: a held take's records were handed to the commit ({len(files)} files)")
        except mod.DriveRefused:
            pass
        try:
            rig.driver.published(r, 1)
            out.append(f"{p}: a held take was published")
        except mod.DriveRefused:
            pass
        if not os.path.isdir(take.config_dir):
            out.append(f"{p}: a held take's config folder was removed")
    with tbi.scratch_repo() as root:                 # through the loop: nothing of the take is committed, it stops
        order = []
        rig = tbi.Rig(mod, root)
        rig.driver.ownership = OrderedOwnership(order, rig.box, fail_restore=True)
        head = tbi.git(root, "rev-parse", "HEAD")
        with watched(mod, order):
            b, got = tbi.run_batch(rig, [tbi.row(1)])
        names = tbi.git(root, "log", "--name-only", "--format=", f"{head}..HEAD").splitlines()
        if any("/records/" in "/" + n for n in names):
            out.append(f"{p}: a held take's records were committed: {[n for n in names if 'records/' in n]}")
        if b.stopped is None:
            out.append(f"{p}: the loop did not stop on a held take")
    return out


@tbi.guarded("O5-grant-fails")
def o5_grant_fails(mod, p):
    out = []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)
        rig.driver.ownership = road = tbi.FakeOwnership(rig.box, fail_grant=True)
        try:
            with tbi.spying(rig.spy):
                rig.driver.launch(tbi.row(1))
            out.append(f"{p}: a failed grant launched the take")
        except mod.DriveRefused as e:
            if "grant" not in str(e):
                out.append(f"{p}: the refusal does not name the grant: {e}")
        if launch_index(rig.box.calls) != len(rig.box.calls):
            out.append(f"{p}: run_take.launch ran after a failed grant")
        if road.names() != ["grant", "restore"] or road.events[1][1]["ids"] != []:
            out.append(f"{p}: a failed grant was not undone by one restore with no ids: {road.events}")
        take = rig.take()
        rec = read(os.path.join(take.folder, mod.OWNERSHIP_GRANT_RECORD))
        if rec is None or rec.get("ok") is not False:
            out.append(f"{p}: the grant record does not say ok false")
    return out


@tbi.guarded("O6-image")
def o6_image(mod, p):
    out = []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)
        plain = rig.spec_for

        def tagged(r, cfg):
            spec = plain(r, cfg)
            return rt.TakeSpec(**{**spec.__dict__, "image": "take-a:latest"})
        rig.driver.spec_for = tagged
        try:
            rig.driver.launch(tbi.row(1))
            out.append(f"{p}: a tagged image was launched")
        except mod.DriveRefused:
            pass
        if rig.ownership.events:
            out.append(f"{p}: the road ran on a tag: {rig.ownership.names()}")
    return out


@tbi.guarded("O7-road")
def o7_road(mod, p):
    out = []
    if mod.ownership_problems(tbi.FakeOwnership()) != []:
        out.append(f"{p}: the fake road fails the interface: {mod.ownership_problems(tbi.FakeOwnership())}")

    class Wrong(tbi.FakeOwnership):
        def restore(self, runtime, *, image, run_tree, config_dir, evidence_dir, caller_env=None):   # no ids
            return {}
    if not mod.ownership_problems(Wrong()) or not mod.ownership_problems(None):
        out.append(f"{p}: a road without ids, or no road, passes the interface")
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)
        rig.driver.ownership = None
        before = sorted(os.listdir(rig.cfg_parent))
        try:
            rig.driver.launch(tbi.row(1))
            out.append(f"{p}: a driver with no road launched")
        except mod.DriveRefused:
            pass
        if sorted(os.listdir(rig.cfg_parent)) != before or rig.box.calls:
            out.append(f"{p}: a driver with no road made a folder or called the runtime before refusing")
    return out


CHECKS = {"O1-grant": o1_grant, "O2-restore": o2_restore, "O3-launch": o3_launch, "O4-held": o4_held,
          "O5-grant-fails": o5_grant_fails, "O6-image": o6_image, "O7-road": o7_road}

# name: (edits to drive.py, the check whose own line must go red)
MUTANTS = {
    "grant-skipped": ((("        self._grant_ownership(take)          #", "        pass  #"),), "O1-grant"),
    "restore-after-postflight": (
        (("        self._restore_ownership(take)    # the ownership road: after teardown",
          "        pass    # the ownership road: after teardown"),
         ("            post = self._postflight(take, row) if not take.ownership_hold else None",
          "            post = self._postflight(take, row) if not take.ownership_hold else None\n"
          "            self._restore_ownership(take)")), "O2-restore"),
    "restore-skipped-on-launch-error": ((("            self._restore_ownership(take)    # after the launch's",
                                          "            pass    # after the launch's"),), "O3-launch"),
    "scan-after-failed-restore": (
        (("            post = self._postflight(take, row) if not take.ownership_hold else None",
          "            post = self._postflight(take, row)"),
         ("        if take.ownership_hold:                               # the ownership road: no postflight",
          "        if False:                               # the ownership road: no postflight")), "O4-held"),
    "commit-reads-a-held-take": ((("        if take is not None and self._unrestored(take):",
                                   "        if False:"),), "O4-held"),
}


class TestOwnershipRoad(unittest.TestCase):
    def test_o1_grant(self):
        self.assertEqual(o1_grant(tbi.drive), [])

    def test_o2_restore(self):
        self.assertEqual(o2_restore(tbi.drive), [])

    def test_o3_launch(self):
        self.assertEqual(o3_launch(tbi.drive), [])

    def test_o4_held(self):
        self.assertEqual(o4_held(tbi.drive), [])

    def test_o5_grant_fails(self):
        self.assertEqual(o5_grant_fails(tbi.drive), [])

    def test_o6_image(self):
        self.assertEqual(o6_image(tbi.drive), [])

    def test_o7_road(self):
        self.assertEqual(o7_road(tbi.drive), [])


class TestOwnershipMutants(unittest.TestCase):
    """Each mutant is killed by its own check's line (an ERROR line or an unperformed edit is never a kill)."""

    def kill(self, name):
        edits, clause = MUTANTS[name]
        self.assertEqual(CHECKS[clause](tbi.drive), [], f"{name}: {clause} is not green on the tree")
        got = CHECKS[clause](tbi.witness_module(edits))
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(clause + ":")]
        print(f"\nMUTANT {name}: {'red' if own and not errors else 'NOT KILLED'} by {clause} ({len(own)} own, "
              f"{len(errors)} errors)", end=" ", file=sys.stderr, flush=True)
        self.assertEqual(errors, [], f"{name}: {errors}")
        self.assertTrue(own, f"{name}: survived: {got}")

    def test_grant_skipped(self):
        self.kill("grant-skipped")

    def test_restore_after_postflight(self):
        self.kill("restore-after-postflight")

    def test_restore_skipped_on_launch_error(self):
        self.kill("restore-skipped-on-launch-error")

    def test_scan_after_failed_restore(self):
        self.kill("scan-after-failed-restore")

    def test_commit_reads_a_held_take(self):
        self.kill("commit-reads-a-held-take")


if __name__ == "__main__":
    unittest.main()
