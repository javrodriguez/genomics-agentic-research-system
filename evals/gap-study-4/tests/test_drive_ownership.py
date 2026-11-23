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
  U1-uid-map   (queue item 2) a uid map handed as (take) -> lines is read at run time for that take, and the take is
               graded as with the lines themselves
  P2-machine   (P-2) a machine gate naming a problem, or no gate at all, refuses the launch before any folder or
               runtime call, through batch too (a launch failure, nothing run); a quiet gate lets the take run
  L1-ledger    (drive-wiring review MAJOR 1; the fake road is permission-faithful) the driver's ledger lines go to the
               host-owned take folder during the take and are copied byte-exact into the evidence folder after the
               restore, both sha256 recorded and the host copy removed; a held take keeps the host copy and gets no
               evidence copy
  N1-native    (review MAJOR 1) a native session in the agent's config folder (0000 to the host during the take, on the
               faithful road) is located through the box's operator_list and read through operator_read with root
               "config", never host-side: each turn's snapshot is retained with the bytes' sha256
  S4-executed  (review MINOR 2) a turn that changes the settings and whose record the harness then refuses (the
               executed-refusal road) still gets its post-n settings check: recorded, and the stop names the settings
  O9-early     (review MINOR 4) run_take.launch refusing before any container (not a LaunchError), after the grant: the
               grant is undone by a restore with no ids, and the take's records are not held
  R6-ruling    (review NOTE 6, glitch-06's ruling) a failed grant or a refused settings baseline is recorded BLOCKED
               before launch (drive_started false), stops the loop and needs a ruling; never re-driven on its own

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
            try:
                rig.driver.drive(r, cid)
            except mod.DriveRefused as e:            # read below by the order it left, never an ERROR line
                out.append(f"{p}: the clean take stopped: {e}")
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


@contextmanager
def config_refused_at(k: int):
    """B11 (lane vendor-b11 round 3): the fake turn k raises run_take.ConfigFolderRefused before anything of it runs,
    as run_take.run_turn does for an arm O or G turn whose config folder check refuses (tests/test_config_folder.py)."""
    real = tbi.FakeAdapter._turn

    def turn(self, line, *, first, budget_s):
        if self._turns + 1 == k:
            raise rt.ConfigFolderRefused(["extra.txt: neither placed nor on codex's allow-list"], k)
        return real(self, line, first=first, budget_s=budget_s)
    with mock.patch.object(tbi.FakeAdapter, "_turn", turn):
        yield


@tbi.guarded("C1-config-turn-one")
def c1_config_turn_one(mod, p):
    """B11 R-CF: a config folder refusal before turn 1 is routed as the settings guard's pre-1 problem is: no turn is
    sent, the take rehearses, and the refusal record names the config folder."""
    out = []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)
        with config_refused_at(1):
            b, got = tbi.run_batch(rig, [tbi.row(1)])
        o = got[0]
        if o["state"] != tbi.labels4.REHEARSAL:
            out.append(f"{p}: a config folder refusal before turn 1 is {o['state']} ({o['reason']})")
        if rig.adapters and rig.adapters[0].lines:
            out.append(f"{p}: turn 1 was sent: {rig.adapters[0].lines}")
        take = rig.driver.published_takes[0] if rig.driver.published_takes else None
        rec = read(os.path.join(take.folder, mod.REFUSAL_RECORD)) if take else None
        if not rec or rec.get("refused") != "ConfigFolderRefused" or "extra.txt" not in rec.get("why", ""):
            out.append(f"{p}: the refusal is not recorded with its problems: {rec}")
    return out


@tbi.guarded("C2-config-later")
def c2_config_later(mod, p):
    """B11 R-CF: a config folder refusal before turn k > 1 stops the take as the settings guard's pre-k problem does:
    nothing further is sent, and the take is kept for a ruling, never a re-run (harness-error's side, not graded)."""
    out = []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root, turns=[{"text": "a"}, {"text": "b"}, {"text": "c"}])
        with config_refused_at(2):
            b, got = tbi.run_batch(rig, [tbi.row(1)])
        o = got[0]
        if o["state"] != tbi.labels4.FAILED or o["drive_started"] is not True or "pre-2" not in (o["reason"] or "") \
                or "config folder" not in (o["reason"] or ""):
            out.append(f"{p}: a config folder refusal before turn 2 is {o['state']} (drive_started "
                       f"{o['drive_started']}): {o['reason']}")
        if len(rig.adapters[0].lines) != 1:
            out.append(f"{p}: {len(rig.adapters[0].lines)} lines were sent, not 1")
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


@tbi.guarded("U1-uid-map")
def u1_uid_map(mod, p):
    out = []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)
        seen = []

        def reader(take):
            seen.append(take.launched.take_id)
            return tbi.UID_MAP
        rig.driver.uid_map = reader
        b, got = tbi.run_batch(rig, [tbi.row(1)])
        if got[0]["state"] != tbi.labels4.GRADED:
            out.append(f"{p}: a take with a run-time uid map is {got[0]['state']} ({got[0]['reason']})")
        if not seen or set(seen) != {rig.take().launched.take_id}:
            out.append(f"{p}: the run-time uid map was not read for the take: {seen}")
    return out


@tbi.guarded("P2-machine")
def p2_machine(mod, p):
    out = []
    for why, gate in (("a suite in progress", lambda: ["athena suite run x is still in progress"]),
                      ("no gate", None)):
        with tbi.scratch_repo() as root:
            rig = tbi.Rig(mod, root)
            rig.driver.machine_gate = gate
            before = sorted(os.listdir(rig.cfg_parent))
            b, got = tbi.run_batch(rig, [tbi.row(1)])
            o = got[0]
            if o["state"] != tbi.labels4.FAILED or o["drive_started"] is not False or "P-2" not in (o["reason"] or ""):
                out.append(f"{p}: {why}: the take is {o['state']} (drive_started {o['drive_started']}): {o['reason']}")
            if (launch_index(rig.box.calls) != len(rig.box.calls) or rig.ownership.events
                    or sorted(os.listdir(rig.cfg_parent)) != before):
                out.append(f"{p}: {why}: something was made or run before the refusal")
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)
        b, got = tbi.run_batch(rig, [tbi.row(1)])
        if got[0]["state"] != tbi.labels4.GRADED:
            out.append(f"{p}: a quiet machine's take is {got[0]['state']} ({got[0]['reason']})")
    return out


@tbi.guarded("L1-ledger")
def l1_ledger(mod, p):
    out = []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)
        b, got = tbi.run_batch(rig, [tbi.row(1)])
        take = rig.take()
        if got[0]["state"] != tbi.labels4.GRADED:
            return [f"{p}: a clean take on the faithful road is {got[0]['state']} ({got[0]['reason']})"]
        ev = os.path.join(take.evidence_dir, "ledger.jsonl")
        host = os.path.join(take.folder, mod.EVIDENCE_LEDGER_HOST)
        rec = read(os.path.join(take.folder, mod.EVIDENCE_LEDGER_COPY))
        data = Path(ev).read_bytes() if os.path.isfile(ev) else None
        if data is None or not data.startswith(b'{"agent"') or os.path.lexists(host):
            out.append(f"{p}: the evidence ledger is {data[:40] if data else None!r}, the host copy "
                       f"{'left' if os.path.lexists(host) else 'removed'}")
        if (rec is None or rec["host_sha256"] != rec["evidence_sha256"]
                or rec["evidence_sha256"] != hashlib.sha256(data or b"").hexdigest()):
            out.append(f"{p}: the copy record does not bind both bytes: {rec}")
    with tbi.scratch_repo() as root:                 # a held take: the host copy stays, no evidence copy
        rig = tbi.Rig(mod, root)
        rig.driver.ownership = rig.ownership = tbi.FakeOwnership(rig.box, fail_restore=True)
        b, got = tbi.run_batch(rig, [tbi.row(1)])
        take = rig.take()
        if not os.path.isfile(os.path.join(take.folder, mod.EVIDENCE_LEDGER_HOST)) or os.path.lexists(
                os.path.join(take.evidence_dir, "ledger.jsonl")):
            out.append(f"{p}: a held take's ledger is not kept host-side alone")
    return out


class NativeAdapter(tbi.FakeAdapter):
    """The fake adapter, which also writes a native session into the config folder each turn (as the agent would) and
    names it through the box's listing."""

    def _turn(self, line, *, first, budget_s):
        got = super()._turn(line, first=first, budget_s=budget_s)
        cfg = self.take.config_dir
        with tbi.FakeBox.as_container(cfg):
            folder = Path(cfg) / "native"
            folder.mkdir(exist_ok=True)
            with open(folder / "session.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"turn": self._turns + 1, "line": line}) + "\n")
        return got

    def native_session_rel(self, lister):
        if dict(lister(".")).get("native") != "dir" or dict(lister("native")).get("session.jsonl") != "file":
            raise AssertionError("the box's listing does not show the native session")
        return "native/session.jsonl"

    def native_session_path(self, home):
        return str(Path(home) / "native" / "session.jsonl")


@tbi.guarded("N1-native")
def n1_native(mod, p):
    out = []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)
        rig.driver.adapter_for = lambda r, take: NativeAdapter(rig.box, take, rig.turns)
        b, got = tbi.run_batch(rig, [tbi.row(1)])
        take = [t for t in rig.driver.published_takes] or [rig.take()]
        take = take[-1]
        if take.native_snapshot_refusal is not None or len(take.native_snapshots) != 2:
            out.append(f"{p}: the native sessions were not retained through the box: "
                       f"{take.native_snapshot_refusal}, {take.native_snapshots}")
        reads = [e for n, e in rig.ownership.events if n == "operator_read" and e["root_kind"] == "config"]
        lists = [e for n, e in rig.ownership.events if n == "operator_list" and e["root_kind"] == "config"]
        if len(reads) != 2 or not lists or any(e["root"] != take.config_dir for e in reads + lists):
            out.append(f"{p}: the config folder was not read through the box: {len(reads)} reads, {len(lists)} lists")
        for snap in take.native_snapshots:
            data = (Path(take.folder) / "session" / snap["file"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != snap["sha256"]:
                out.append(f"{p}: {snap['file']} is not the bytes its sha256 names")
    return out


@tbi.guarded("S4-executed")
def s4_executed(mod, p):
    import test_executed_turn_refusal as tet
    out = []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root, turns=[{"text": "a"}, {"text": "b"}])

        class Planting(tet.RefusingAdapter):
            def _turn(self, line, *, first, budget_s):
                plant(self.take.launched.spec.run_tree)
                return super()._turn(line, first=first, budget_s=budget_s)

        def make(r, take):
            rig.adapters.append(Planting(rig.box, take, rig.turns, refuse_at=1))
            return rig.adapters[-1]
        rig.adapter_for = rig.driver.adapter_for = make
        b, got = tbi.run_batch(rig, [tbi.row(1)])
        rec = read(os.path.join(rig.take().folder, mod.SETTINGS_RECORD)) or {}
        checks = [(c["snapshot"], bool(c["problems"])) for c in rec.get("checks", [])]
        if checks != [("pre-1", False), ("post-1", True)]:
            out.append(f"{p}: the executed-refusal road's checks are {checks}")
        if "post-1" not in (got[0]["reason"] or "") or got[0]["state"] != tbi.labels4.FAILED:
            out.append(f"{p}: the stop does not name the post-1 settings: {got[0]['state']} ({got[0]['reason']})")
    return out


@tbi.guarded("O9-early")
def o9_early(mod, p):
    out = []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)

        def refuse(*a, **kw):
            raise rt.NotReady("synthetic: launch refused before any container")
        with mock.patch.object(mod._run_take, "launch", refuse):
            try:
                rig.driver.launch(tbi.row(1))
                out.append(f"{p}: the refused launch did not raise")
            except rt.NotReady:
                pass
        if rig.ownership.names() != ["grant", "restore"] or rig.ownership.events[1][1]["ids"] != []:
            out.append(f"{p}: the early refusal was not followed by one restore with no ids: {rig.ownership.names()}")
        try:
            rig.driver.record_files(tbi.row(1), 1)
        except mod.DriveRefused as e:
            out.append(f"{p}: the restored take's records are held: {e}")
    return out


@tbi.guarded("R6-ruling")
def r6_ruling(mod, p):
    import batch
    out = []
    for why, kw in (("a failed grant", {"ownership": "grant"}), ("a refused baseline", {"settings_guard": "refuse"})):
        with tbi.scratch_repo() as root:
            rig = tbi.Rig(mod, root)
            if "ownership" in kw:
                rig.driver.ownership = rig.ownership = tbi.FakeOwnership(rig.box, fail_grant=True)
            else:
                rig.driver.settings_guard = rig.settings_guard = tbi.FakeSettingsGuard(refuse=True)
            b, got = tbi.run_batch(rig, [tbi.row(1)])
            o = got[0]
            if (o["state"] != tbi.labels4.BLOCKED or o["drive_started"] is not False or not batch.needs_ruling(o)
                    or "ruling" not in (o["reason"] or "") or b.stopped is None):
                out.append(f"{p}: {why} is {o['state']} (drive_started {o['drive_started']}, needs a ruling "
                           f"{batch.needs_ruling(o)}): {o['reason']}")
    return out


CHECKS = {"O1-grant": o1_grant, "O2-restore": o2_restore, "O3-launch": o3_launch, "O4-held": o4_held,
          "O5-grant-fails": o5_grant_fails, "O6-image": o6_image, "O7-road": o7_road, "O8-operator": o8_operator,
          "S1-baseline": s1_baseline, "S2-turn-one": s2_turn_one, "S3-later": s3_later, "B3-one-road": b3_one_road,
          "U1-uid-map": u1_uid_map, "P2-machine": p2_machine,
          "L1-ledger": l1_ledger, "N1-native": n1_native,
          "S4-executed": s4_executed, "O9-early": o9_early, "R6-ruling": r6_ruling,
          "C1-config-turn-one": c1_config_turn_one, "C2-config-later": c2_config_later}

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
    "machine-gate-unchecked": ((("        if busy:                                              # P-2: before any folder",
                                 "        if False:                                              # P-2: before any folder"),),
                               "P2-machine"),
    "ledger-into-evidence": ((("        with open(os.path.join(take.folder, EVIDENCE_LEDGER_HOST), \"a\", encoding=\"utf-8\") as fh:",
                               "        with open(os.path.join(take.evidence_dir, \"ledger.jsonl\"), \"a\", "
                               "encoding=\"utf-8\") as fh:"),), "L1-ledger"),
    "ledger-copy-skipped": ((("            self._copy_evidence_ledger(take)\n", "            pass\n"),), "L1-ledger"),
    "native-read-host-side": ((("            take.native_snapshots.append(_native_snapshot.retain_bytes(take.folder, n, "
                                "reader(rel)))",
                                "            take.native_snapshots.append(_native_snapshot.retain(take.folder, n, "
                                "os.path.join(take.config_dir, rel)))"),), "N1-native"),
    "executed-post-unchecked": ((("                        after = self._settings_problems(take, f\"post-{n}\")   "
                                  "# review MINOR 2: this road too",
                                  "                        after = []   # review MINOR 2: this road too"),),
                                "S4-executed"),
    "early-launch-unrestored": ((("        except Exception:                    # review MINOR 4: refused before any "
                                  "container, after the grant\n            if take.launched is None:",
                                  "        except Exception:                    # review MINOR 4: refused before any "
                                  "container, after the grant\n            if False:"),), "O9-early"),
    "grant-refusal-redriven": ((("            raise LaunchNeedsRuling(f\"ownership grant failed, the take is not launched: {e}\") "
                                 "from e",
                                 "            raise DriveRefused(f\"ownership grant failed, the take is not launched: {e}\") "
                                 "from e"),), "R6-ruling"),
    "baseline-refusal-redriven": ((("            raise LaunchNeedsRuling(f\"the run tree's Claude settings refused before "
                                    "launch: {e}\") from e",
                                    "            raise DriveRefused(f\"the run tree's Claude settings refused before "
                                    "launch: {e}\") from e"),), "R6-ruling"),
    "uid-map-unread": ((("        uid_map = self.uid_map(take) if callable(self.uid_map) else self.uid_map",
                         "        uid_map = self.uid_map"),), "U1-uid-map"),
    "one-turn-reached": ((("        take.driven = True\n",
                           "        take.driven = True\n        if row.get(\"slot\") is None:\n"
                           "            one_turn(\"x\", \"s\", row[\"model\"], True)\n"),), "B3-one-road"),
    "baseline-skipped": ((("        self._settings_baseline(take)        #", "        pass  #"),), "S1-baseline"),
    "turn-one-unchecked": ((("                first = self._settings_problems(take, \"pre-1\")",
                             "                first = []"),), "S2-turn-one"),
    "later-unchecked": ((("                        later = self._settings_problems(take, f\"pre-{n}\")",
                          "                        later = []"),), "S3-later"),
    "post-unchecked": ((("                    after = self._settings_problems(take, f\"post-{n}\")   # the settings guard, "
                         "the last turn's too",
                         "                    after = []"),), "S3-later"),
    "config-turn-one-not-rehearsed": ((("                        if n == 1:                                # routed as "
                                        "the settings guard is: a rehearsal",
                                        "                        if False:                                # routed as "
                                        "the settings guard is: a rehearsal"),), "C1-config-turn-one"),
    "config-later-unstopped": ((("        if take.config_stop is not None:          # B11 after turn 1",
                                 "        if False:          # B11 after turn 1"),), "C2-config-later"),
    "missing-snapshot-passes": ((("            problems = [f\"{label}: the settings check could not run "
                                  "({type(e).__name__}: {str(e)[:200]})\"]",
                                  "            problems = []"),), "S3-later"),
}


@tbi.guarded("E1-evidence-mode")
def e1_evidence_mode(mod, p):
    """The box lane (15 Oct 2026): the take's evidence folder took its mode from the process umask, and umask 077 made
    it unreadable to the host. drive makes it 0755 itself, whatever the umask, before the grant reads it."""
    import stat as _stat
    out, modes = [], []

    class Spy(tbi.FakeOwnership):
        def grant(self, runtime, *, image, run_tree, config_dir, evidence_dir, caller_env=None):
            modes.append(_stat.S_IMODE(os.lstat(evidence_dir).st_mode))
            return super().grant(runtime, image=image, run_tree=run_tree, config_dir=config_dir,
                                 evidence_dir=evidence_dir, caller_env=caller_env)
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root)
        rig.ownership = road = Spy(rig.box)
        rig.driver.ownership = road
        old = os.umask(0o077)
        try:
            tbi.run_batch(rig, [tbi.row(1)])
        finally:
            os.umask(old)
    if modes != [0o755]:
        out.append(f"{p}: under umask 077 the evidence folder reached the grant with mode "
                   f"{[oct(m) for m in modes]}, not 0o755")
    return out


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

    def test_c1_config_turn_one(self):
        self.assertEqual(c1_config_turn_one(tbi.drive), [])

    def test_c2_config_later(self):
        self.assertEqual(c2_config_later(tbi.drive), [])

    def test_b3_one_road(self):
        self.assertEqual(b3_one_road(tbi.drive), [])

    def test_u1_uid_map(self):
        self.assertEqual(u1_uid_map(tbi.drive), [])

    def test_p2_machine(self):
        self.assertEqual(p2_machine(tbi.drive), [])

    def test_e1_evidence_mode(self):
        self.assertEqual(e1_evidence_mode(tbi.drive), [])

    def test_l1_ledger(self):
        self.assertEqual(l1_ledger(tbi.drive), [])

    def test_n1_native(self):
        self.assertEqual(n1_native(tbi.drive), [])

    def test_s4_executed(self):
        self.assertEqual(s4_executed(tbi.drive), [])

    def test_o9_early(self):
        self.assertEqual(o9_early(tbi.drive), [])

    def test_r6_ruling(self):
        self.assertEqual(r6_ruling(tbi.drive), [])


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

    def test_config_turn_one_not_rehearsed(self):
        self.kill("config-turn-one-not-rehearsed")

    def test_config_later_unstopped(self):
        self.kill("config-later-unstopped")

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

    def test_uid_map_unread(self):
        self.kill("uid-map-unread")

    def test_machine_gate_unchecked(self):
        self.kill("machine-gate-unchecked")

    def test_ledger_into_evidence(self):
        self.kill("ledger-into-evidence")

    def test_ledger_copy_skipped(self):
        self.kill("ledger-copy-skipped")

    def test_native_read_host_side(self):
        self.kill("native-read-host-side")

    def test_executed_post_unchecked(self):
        self.kill("executed-post-unchecked")

    def test_early_launch_unrestored(self):
        self.kill("early-launch-unrestored")

    def test_grant_refusal_redriven(self):
        self.kill("grant-refusal-redriven")

    def test_baseline_refusal_redriven(self):
        self.kill("baseline-refusal-redriven")


if __name__ == "__main__":
    unittest.main()
