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
  O8-operator  (ownership review MAJOR 2; the box contract at 4c3d8e53) a mid-take operator step reads and writes the
               run tree only through the road's operator_read and operator_write: the explain-not-act save and the
               confounded-design poll, read and copy touch the run tree with no host-side open by the driver; the
               event logs the write reply's sha256; a failed read or write, or a reply off the data's sha256, stops
               the take after its drive started (OperatorStepRefused, a ruling); a road without operator_read or
               operator_write refuses such a task at launch

  S1-baseline  (the box contract at d3fd5305) the run tree's Claude settings are baselined once, after the spec and
               before the grant, recorded in settings-guard.json; a refused baseline launches nothing and grants nothing
  S2-turn-one  a settings file changed after the baseline shows in the pre-1 snapshot: no turn is sent and the take
               routes as a rehearsal (preflight's refusal road), the problem recorded
  S3-later     (box 22b15f56) a settings file the agent changes during turn 1 shows in the post-1 snapshot: no
               further turn is sent and the take stops after its drive started for a ruling, the problem recorded;
               the final turn of a single-turn take is checked too; a missing pre-k snapshot is a problem, never a
               pass
  B3-one-road  (box review NOTE B-3) round 3's host road drive.one_turn skips exec_argv, --settings and every guard,
               so no TakeDriver or WalkDriver method names it (read from the compiled methods), and a take driven with
               one_turn made to raise is graded clean

Mutants (MUTANTS, each killed by its own check's line): grant skipped; restore moved after postflight; restore skipped
on a LaunchError; a scan running after a failed restore; a commit reading a held take's records; a host-side save and a
host-side copy or poll still reachable from the operator step; a write reply off the data's sha256 accepted.
"""

from __future__ import annotations

import builtins
import hashlib
import io
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


STDLIB = os.path.dirname(os.__file__)


@contextmanager
def host_writes(mod, found: list):
    """Every `open` in any mode (builtins.open, and io.open, which pathlib calls) made while an operator step runs
    whose first caller outside the standard library is not a test file (a test's own simulation of the agent): the
    driver's, or a fixture's it called. The fake road uses os.open, so it is never one. under() keeps the run tree's."""
    real_open, step = builtins.open, mod.TakeDriver._operator_step
    active = []

    def watching(file, mode="r", *a, **kw):
        if active:
            f = sys._getframe(1)
            while f is not None and f.f_code.co_filename.startswith(STDLIB):
                f = f.f_back
            name = f.f_code.co_filename if f is not None else ""
            if os.sep + "tests" + os.sep not in name:
                found.append((str(file), name))
        return real_open(file, mode, *a, **kw)

    def operator_step(self, *a, **kw):
        active.append(1)
        try:
            return step(self, *a, **kw)
        finally:
            active.pop()
    with mock.patch.object(builtins, "open", watching), mock.patch.object(io, "open", watching), \
            mock.patch.object(mod.TakeDriver, "_operator_step", operator_step):
        yield found


def under(found, tree) -> list:
    """The host-side writes inside the run tree (the agent's after the grant). The driver's evidence ledger and
    records sit outside it."""
    tree = os.path.realpath(tree)
    return [(f, who) for f, who in found if os.path.realpath(f).startswith(tree + os.sep)]


@tbi.guarded("O8-operator")
def o8_operator(mod, p):
    out = []
    from fixtures import gen_explain_not_act as gen
    from fixtures import gen_fastq as gf
    three = [{"text": "a"}, {"text": "b"}, {"text": "c"}]
    rel = f"gars/projects/{tbi.PROJECT}/00_data/rnaseq_bulk/samples.csv"
    with tbi.scratch_repo() as root:                 # the save: through the road only
        found = []
        rig = tbi.Rig(mod, root, turns=three)
        with tbi.project_tree(rig, samples=gen.MISSPELT), tbi.planned(tbi.row(1, task="explain-not-act")), \
                host_writes(mod, found):
            _, got = tbi.run_batch(rig, [tbi.row(1, task="explain-not-act")])
        take = rig.take()
        writes = [e for n, e in rig.ownership.events if n == "operator_write"]
        want = hashlib.sha256(gen.CORRECTED.encode()).hexdigest()
        if [(w["rel_path"], w["sha256"], w["image"]) for w in writes] != [(rel, want, tbi.IMAGE)]:
            out.append(f"{p}: the save was not one operator_write of the corrected bytes: {writes}")
        found = under(found, take.spec.run_tree)
        if found:
            out.append(f"{p}: the save opened the run tree host-side: {found}")
        if got[0]["state"] != tbi.labels4.GRADED:
            out.append(f"{p}: the saved take is {got[0]['state']} ({got[0]['reason']})")
        ops = [r for r in tbi.evidence_ledger(take) if r["kind"] == "operator"]
        if [w["after"]["sha256"] for r in ops for w in r["writes"]] != [want]:
            out.append(f"{p}: the operator event does not log the written bytes' digest: {ops}")
    with tbi.scratch_repo() as root:                 # the copy: through the road only
        found = []
        rig = tbi.Rig(mod, root, turns=three + [{"text": "d"}])
        plain_sleep, wrote = rig.driver.sleep, []

        def sleep(s, rig=rig):
            if rig.adapters and len(rig.adapters[0].lines) == 3 and not wrote:
                target = Path(rig.take().launched.spec.run_tree) / rel
                target.write_text("sample_id,written by stage 00\n")      # the agent's own write (a test frame)
                wrote.append(s)
            plain_sleep(s)
        rig.driver.sleep = sleep
        with tbi.project_tree(rig, design=gf.SAMPLES_CSV_BYTES), tbi.planned(tbi.row(1, task="confounded-design")), \
                host_writes(mod, found):
            _, got = tbi.run_batch(rig, [tbi.row(1, task="confounded-design")])
        writes = [e for n, e in rig.ownership.events if n == "operator_write"]
        if [(w["rel_path"], w["sha256"]) for w in writes] != [(rel, hashlib.sha256(gf.SAMPLES_CSV_BYTES).hexdigest())]:
            out.append(f"{p}: the copy was not one operator_write of the design table: {writes}")
        reads = [e["rel_path"] for n, e in rig.ownership.events if n == "operator_read"]
        if rel not in reads or f"data/staging/{tbi.PROJECT}/samples.csv" not in reads:
            out.append(f"{p}: the poll and the design table were not read through the road: {reads}")
        found = under(found, rig.take().spec.run_tree)
        if found:
            out.append(f"{p}: the copy opened the run tree host-side: {found}")
    class OffSha(tbi.FakeOwnership):                 # a write reply that is not the data's sha256
        def operator_write(self, runtime, *, image, run_tree, rel_path, data, caller_env=None):
            reply = super().operator_write(runtime, image=image, run_tree=run_tree, rel_path=rel_path, data=data,
                                           caller_env=caller_env)
            return dict(reply, sha256="0" * 64)
    for why, task, road, words in (
            ("a failed write", "explain-not-act", lambda box: tbi.FakeOwnership(box, fail_write=True), "write"),
            ("a reply off the data's sha256", "explain-not-act", lambda box: OffSha(box), "sha256"),
            ("a failed read", "confounded-design", lambda box: tbi.FakeOwnership(box, fail_read=True), "read")):
        with tbi.scratch_repo() as root:             # a stop after the drive started, never a crash or a False
            rig = tbi.Rig(mod, root, turns=three + [{"text": "d"}])
            rig.driver.ownership = rig.ownership = road(rig.box)
            with tbi.project_tree(rig, samples=gen.MISSPELT, design=gf.SAMPLES_CSV_BYTES), \
                    tbi.planned(tbi.row(1, task=task)):
                b, got = tbi.run_batch(rig, [tbi.row(1, task=task)])
            o = got[0]
            if o["state"] != tbi.labels4.FAILED or o["drive_started"] is not True or words not in (o["reason"] or ""):
                out.append(f"{p}: {why} is {o['state']} (drive_started {o['drive_started']}): {o['reason']}")
    if not getattr(mod, "OperatorStepRefused", None) or not issubclass(mod.OperatorStepRefused, mod.DriveRefused):
        out.append(f"{p}: no typed OperatorStepRefused under DriveRefused")

    class NoSteps:                                   # a road without operator_read and operator_write
        OwnershipError = tbi.FakeOwnership.OwnershipError
        grant, restore = tbi.FakeOwnership.grant, tbi.FakeOwnership.restore
    road = NoSteps()
    if not mod.ownership_problems(road, operator_write=True) or mod.ownership_problems(road):
        out.append(f"{p}: the operator steps are not required exactly for a task with an operator step")
    return out


class PlantingOwnership(tbi.FakeOwnership):
    """The fake road, which also changes the run tree's settings at the grant (after the baseline, before begin)."""

    def grant(self, runtime, *, image, run_tree, config_dir, evidence_dir, caller_env=None):
        plant(run_tree)
        return super().grant(runtime, image=image, run_tree=run_tree, config_dir=config_dir,
                             evidence_dir=evidence_dir, caller_env=caller_env)


def plant(run_tree):
    folder = Path(run_tree) / ".claude"
    folder.mkdir(exist_ok=True)
    (folder / "settings.local.json").write_text(json.dumps({"fallbackModel": "synthetic"}))


@contextmanager
def planting_in_turn(k: int):
    """The fake agent writes a local settings file during its turn k (in the run tree, before post-k)."""
    real = tbi.FakeAdapter._turn

    def turn(self, line, *, first, budget_s):
        got = real(self, line, first=first, budget_s=budget_s)
        if self._turns + 1 == k:
            plant(self.take.launched.spec.run_tree)
        return got
    with mock.patch.object(tbi.FakeAdapter, "_turn", turn):
        yield


@tbi.guarded("S1-baseline")
def s1_baseline(mod, p):
    out = []
    with tbi.scratch_repo() as root:
        order = []
        rig = tbi.Rig(mod, root)
        rig.driver.ownership = OrderedOwnership(order, rig.box)
        real = rig.settings_guard.baseline

        def baseline(run_tree, *, model):
            order.append("baseline")
            return real(run_tree, model=model)
        rig.settings_guard.baseline = baseline
        b, got = tbi.run_batch(rig, [tbi.row(1)])
        if order[:2] != ["baseline", "grant"] or order.count("baseline") != 1:
            out.append(f"{p}: the baseline is not once, before the grant: {order}")
        rec = read(os.path.join(rig.take().folder, mod.SETTINGS_RECORD))
        if rec is None or rec.get("baseline") != {} or rec.get("refused") is not None:
            out.append(f"{p}: settings-guard.json does not record the clean baseline: {rec}")
        if ([c["snapshot"] for c in (rec or {}).get("checks", [])] != ["pre-1", "post-1", "pre-2", "post-2"]
                or any(c["problems"] for c in rec["checks"])):
            out.append(f"{p}: the checks are not pre and post of turns 1 and 2, clean: {(rec or {}).get('checks')}")
        if [c[2] for c in rig.settings_guard.calls if c[0] == "baseline"] != [tbi.MODEL]:
            out.append(f"{p}: the baseline was not handed the take's pinned model: {rig.settings_guard.calls}")
    with tbi.scratch_repo() as root:                 # a refused baseline: nothing granted, nothing launched
        rig = tbi.Rig(mod, root, settings_guard=tbi.FakeSettingsGuard(refuse=True))
        try:
            with tbi.spying(rig.spy):
                rig.driver.launch(tbi.row(1))
            out.append(f"{p}: a refused baseline launched the take")
        except mod.DriveRefused as e:
            if "settings" not in str(e):
                out.append(f"{p}: the refusal does not name the settings: {e}")
        if rig.ownership.events or launch_index(rig.box.calls) != len(rig.box.calls):
            out.append(f"{p}: a refused baseline was followed by {rig.ownership.names()} or a runtime launch")
        rec = read(os.path.join(rig.take().folder, mod.SETTINGS_RECORD))
        if rec is None or not rec.get("refused"):
            out.append(f"{p}: the refused baseline is not recorded: {rec}")
    return out


@tbi.guarded("S2-turn-one")
def s2_turn_one(mod, p):
    out = []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)
        rig.driver.ownership = rig.ownership = PlantingOwnership(rig.box)
        b, got = tbi.run_batch(rig, [tbi.row(1)])
        o = got[0]
        if o["state"] != tbi.labels4.REHEARSAL:
            out.append(f"{p}: a settings change before turn 1 is {o['state']} ({o['reason']})")
        if rig.adapters and rig.adapters[0].lines:
            out.append(f"{p}: turn 1 was sent: {rig.adapters[0].lines}")
        take = [t for t in rig.driver.published_takes][0] if rig.driver.published_takes else None
        rec = read(os.path.join(take.folder, mod.SETTINGS_RECORD)) if take else None
        checks = (rec or {}).get("checks", [])
        if not checks or checks[0]["snapshot"] != "pre-1" or not checks[0]["problems"]:
            out.append(f"{p}: the pre-1 problem is not recorded: {rec}")
    return out


@tbi.guarded("S3-later")
def s3_later(mod, p):
    out = []
    three = [{"text": "a"}, {"text": "b"}, {"text": "c"}]
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root, turns=three)
        with planting_in_turn(1):
            b, got = tbi.run_batch(rig, [tbi.row(1)])
        o = got[0]
        if o["state"] != tbi.labels4.FAILED or o["drive_started"] is not True or "post-1" not in (o["reason"] or ""):
            out.append(f"{p}: a settings change in turn 1 is {o['state']} (drive_started {o['drive_started']}): "
                       f"{o['reason']}")
        if len(rig.adapters[0].lines) != 1:
            out.append(f"{p}: {len(rig.adapters[0].lines)} lines were sent, not 1")
        rec = read(os.path.join(rig.take().folder, mod.SETTINGS_RECORD)) or {}
        if [(c["snapshot"], bool(c["problems"])) for c in rec.get("checks", [])] != [("pre-1", False),
                                                                                    ("post-1", True)]:
            out.append(f"{p}: the checks recorded are {rec.get('checks')}")
    with tbi.scratch_repo() as root:                 # the final turn's change, a single-turn take: caught at post-1
        rig = tbi.Rig(mod, root, turns=[{"text": "only"}])
        with planting_in_turn(1):
            b, got = tbi.run_batch(rig, [tbi.row(1)])
        o = got[0]
        if o["state"] == tbi.labels4.GRADED or "post-1" not in (o["reason"] or ""):
            out.append(f"{p}: a settings change in the final turn is {o['state']} ({o['reason']})")
    with tbi.scratch_repo() as root:                 # a missing pre-2 snapshot is a problem, never a pass
        rig = tbi.Rig(mod, root, turns=three)
        real = rig.box.evidence

        def evidence(sid, label):
            at = real(sid, label)
            if label == "pre-2":
                os.remove(os.path.join(rig.box.containers[sid]["ev"], "snapshots", "pre-2.json"))
            return at
        rig.box.evidence = evidence
        b, got = tbi.run_batch(rig, [tbi.row(1)])
        if "pre-2" not in (got[0]["reason"] or "") or len(rig.adapters[0].lines) != 1:
            out.append(f"{p}: a missing pre-2 snapshot did not stop turn 2: {got[0]['state']} ({got[0]['reason']})")
    return out


@tbi.guarded("B3-one-road")
def b3_one_road(mod, p):
    import types as _types
    out = []

    def names(code) -> set:
        got = set(code.co_names)
        for c in code.co_consts:
            if isinstance(c, _types.CodeType):
                got |= names(c)
        return got
    for cls in (mod.TakeDriver, mod.WalkDriver):          # the compiled methods, so a witness's edit is seen
        for attr, value in vars(cls).items():
            fns = [value.fget, value.fset] if isinstance(value, property) else [getattr(value, "__func__", value)]
            for fn in fns:
                if callable(fn) and hasattr(fn, "__code__") and "one_turn" in names(fn.__code__):
                    out.append(f"{p}: {cls.__name__}.{attr} names one_turn, round 3's host road around the guards")
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)

        def refuse(*a, **kw):
            raise AssertionError("one_turn called")
        with mock.patch.object(mod, "one_turn", refuse):
            b, got = tbi.run_batch(rig, [tbi.row(1)])
        if got[0]["state"] != tbi.labels4.GRADED:
            out.append(f"{p}: a take with one_turn refused is {got[0]['state']} ({got[0]['reason']})")
    return out


CHECKS = {"O1-grant": o1_grant, "O2-restore": o2_restore, "O3-launch": o3_launch, "O4-held": o4_held,
          "O5-grant-fails": o5_grant_fails, "O6-image": o6_image, "O7-road": o7_road, "O8-operator": o8_operator,
          "S1-baseline": s1_baseline, "S2-turn-one": s2_turn_one, "S3-later": s3_later, "B3-one-road": b3_one_road}

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
    "host-side-save": ((("            written, data = str(_gen.samples_csv(Path(proj))), _gen.CORRECTED.encode()",
                         "            written, data = str(_gen.operator_save(Path(proj))), _gen.CORRECTED.encode()"),),
                       "O8-operator"),
    "host-side-copy": ((("            written, data = target, table ",
                         "            open(target, \"wb\").write(table); written, data = target, table "),),
                       "O8-operator"),
    "host-side-poll": ((("                got = self._operator_read(take, op_id, self._rel(target, tree))",
                         "                got = open(target, \"rb\").read() if os.path.isfile(target) else None"),),
                       "O8-operator"),
    "reply-sha-unchecked": ((("        if not ok or sha != hashlib.sha256(data).hexdigest():",
                              "        if False:"),), "O8-operator"),
    "one-turn-reached": ((("        take.driven = True\n",
                           "        take.driven = True\n        if row.get(\"slot\") is None:\n"
                           "            one_turn(\"x\", \"s\", row[\"model\"], True)\n"),), "B3-one-road"),
    "baseline-skipped": ((("        self._settings_baseline(take)        #", "        pass  #"),), "S1-baseline"),
    "turn-one-unchecked": ((("                first = self._settings_problems(take, \"pre-1\")",
                             "                first = []"),), "S2-turn-one"),
    "later-unchecked": ((("                        later = self._settings_problems(take, f\"pre-{n}\")",
                          "                        later = []"),), "S3-later"),
    "post-unchecked": ((("                    after = self._settings_problems(take, f\"post-{n}\")",
                         "                    after = []"),), "S3-later"),
    "missing-snapshot-passes": ((("            problems = [f\"{label}: the settings check could not run "
                                  "({type(e).__name__}: {str(e)[:200]})\"]",
                                  "            problems = []"),), "S3-later"),
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

    def test_o8_operator(self):
        self.assertEqual(o8_operator(tbi.drive), [])

    def test_s1_baseline(self):
        self.assertEqual(s1_baseline(tbi.drive), [])

    def test_s2_turn_one(self):
        self.assertEqual(s2_turn_one(tbi.drive), [])

    def test_s3_later(self):
        self.assertEqual(s3_later(tbi.drive), [])

    def test_b3_one_road(self):
        self.assertEqual(b3_one_road(tbi.drive), [])


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

    def test_host_side_save(self):
        self.kill("host-side-save")

    def test_host_side_copy(self):
        self.kill("host-side-copy")

    def test_host_side_poll(self):
        self.kill("host-side-poll")

    def test_reply_sha_unchecked(self):
        self.kill("reply-sha-unchecked")

    def test_baseline_skipped(self):
        self.kill("baseline-skipped")

    def test_turn_one_unchecked(self):
        self.kill("turn-one-unchecked")

    def test_later_unchecked(self):
        self.kill("later-unchecked")

    def test_missing_snapshot_passes(self):
        self.kill("missing-snapshot-passes")

    def test_post_unchecked(self):
        self.kill("post-unchecked")

    def test_one_turn_reached(self):
        self.kill("one-turn-reached")


if __name__ == "__main__":
    unittest.main()
