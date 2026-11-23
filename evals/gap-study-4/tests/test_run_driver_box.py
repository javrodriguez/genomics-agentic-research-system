#!/usr/bin/env python3
"""The counted run's driver on the fake box (Gap Study round 4, lane run-launcher, stage S2; glitch-f1's rulings on
DESIGN-run-launcher.md, 22 Oct 2026).

  S2.box  run_builders.RunDriver over a real drive.TakeDriver (test_box_integration's Rig, its fake box, adapter and
          checker) and the Rig's real drive.TakeRepo, driven by batch.Batch with its rolling window (not serial): the
          second take is launched while the first one's drive is still running (B19-16's shape, on fakes; the real
          proof is the rehearsal take on athena), both takes are registered and committed in row order, each take's
          prepared state is discarded once its commit lands, and every launch, drive and remove reached the sub-driver
          that launched the take. Witness: rd-published-keeps (run_published never discards).
  S4.box  (MAJOR-1 of the review of 122b559e) rehearse_takes over the same Rig, an arm A and an arm O take through the
          real batch.Batch and a real SpendLedger on the scratch repository's committed run-ledger.json: with the
          rehearsal's two zero reads the money gate admits the wave and both are registered, overlapping, driven and
          committed (the O take's route on this Claude-only fake box is `failed` at postflight: no Codex native session;
          its graded route is the athena rehearsal's proof); with none, batch's money gate stops the wave before
          anything is registered and the summary is refused:money-gate.

Fakes and synthetic strings only, inside test_box_integration's process guard: no model, vendor, network, container
runtime, credential or holdout.
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import batch  # noqa: E402
import test_box_integration as tbi  # noqa: E402

MODS: dict = {}


def setUpModule():
    tbi.setUpModule()
    import run_builders
    MODS["rb"] = run_builders


def tearDownModule():
    tbi.tearDownModule()


class S2Box(unittest.TestCase):
    def test_two_takes_overlap_through_the_run_driver(self):
        rb = MODS["rb"]
        with tbi.scratch_repo() as root:
            rig = tbi.Rig(tbi.drive, root)
            log, discarded = [], []
            road = rb.TakeRoad(prepare=lambda r: log.append(("prepare", r["slot"])) or {"tree": Path("/t/" + r["slot"])},
                               remove=lambda tree: discarded.append(str(tree)) or None)
            sub = rig.driver
            second_launched = threading.Event()
            overlapped = []
            real_launch, real_drive = sub.launch, sub.drive

            def launch(row):
                log.append(("launch", row["slot"]))
                if row["slot"] == "s2":
                    second_launched.set()
                return real_launch(row)

            def drive(row, cid):
                if row["slot"] == "s1":       # the first drive waits (bounded) for the second launch
                    overlapped.append(second_launched.wait(20))
                return real_drive(row, cid)
            sub.launch, sub.drive = launch, drive
            rd = rb.RunDriver(drivers={"claude-code": sub}, road=road, precheck=lambda d, r: None,
                              history=rig.repo.history)
            rig.repo.record_files = rd.record_files
            rig.repo.on_published = rd.published
            rows = [tbi.row(1), tbi.row(2)]
            with tbi.spying(rig.spy), tbi.planned(*rows):
                got = batch.Batch(rd, rig.repo, tbi.Window(), table=tbi.table()).run(rows)
            self.assertEqual(overlapped, [True], "S2.box: the second take was not launched during the first's drive")
            self.assertEqual([(o["slot"], o["state"]) for o in got], [("s1", "graded"), ("s2", "graded")],
                             f"S2.box: {[(o['slot'], o['state'], o['reason']) for o in got]}")
            self.assertEqual(log, [("prepare", "s1"), ("launch", "s1"), ("prepare", "s2"), ("launch", "s2")],
                             "S2.box: prepare before each launch")
            self.assertEqual(sorted(discarded), ["/t/s1", "/t/s2"], "S2.box: a committed take's state not discarded")
            self.assertEqual([o["slot"] for o in rig.repo.history() if batch.is_outcome(o)], ["s1", "s2"],
                             "S2.box: committed out of row order")


O_MODEL = "gpt-6.1-sol"          # a registered (arm O, model) pair of run_builders.COST_PER_TRY


def o_row(n):
    """An arm O row on the Codex harness under the Rig's injected profile (fakes only: no Codex binary or lease)."""
    return tbi.row(n, arm="O", model=O_MODEL, agent={"harness": "codex", "version": tbi.PROFILE["version"]})


BASE_TABLE = tbi.table


def ao_table() -> dict:
    """The Rig's table with a Codex profile for O_MODEL too (the Rig's pin_for reads tbi.table at call time)."""
    t = BASE_TABLE()
    t["pin_profiles"]["codex"] = {O_MODEL: dict(tbi.PROFILE)}
    return t


class CodexFake(tbi.FakeAdapter):
    """The Rig's fake adapter under the Codex harness's name, reporting the O row's model (no Codex binary)."""
    name = "codex"

    def _turn(self, line, *, first, budget_s):
        got = super()._turn(line, first=first, budget_s=budget_s)
        return dataclasses.replace(got, init=dict(got.init, model=O_MODEL))


class S4BoxRehearsal(unittest.TestCase):
    """MAJOR-1 (review of 122b559e): rehearse_takes drives an A and an O take through the real batch.Batch (rolling
    window, the real money gate) with a real SpendLedger over the scratch repository's committed run-ledger.json. With
    the rehearsal's two zero reads committed, both takes are committed, overlapping; with no read, the gate stops the
    wave before anything is registered and the summary is the one closed refusal refused:money-gate."""

    def rehearse(self, root, *, reads):
        import prereg
        rb = MODS["rb"]
        rig = tbi.Rig(tbi.drive, root)
        rows = [tbi.row(1), o_row(2)]
        if reads:
            for vendor in ("google", "openai"):
                rb.append_spend({"vendor": vendor, "at": "2026-10-22T12:00:00Z", "usd": "0",
                                 "source": "rehearsal clone, not a vendor read", "by": "rehearsal"},
                                root=root, repo=root)
        discarded = []
        road = rb.TakeRoad(prepare=lambda r: {"tree": Path("/t/" + r["slot"])},
                           remove=lambda tree: discarded.append(str(tree)) or None)
        sub = rig.driver
        second_launched = threading.Event()
        real_launch, real_drive = sub.launch, sub.drive

        def launch(row):
            if row["slot"] == "s2":
                second_launched.set()
            return real_launch(row)

        def drive(row, cid):
            if row["slot"] == "s1":
                second_launched.wait(20)
            return real_drive(row, cid)
        sub.launch, sub.drive = launch, drive
        claude_adapter = sub.adapter_for

        def adapter_for(r, take):                   # each take's adapter under its own row's harness
            if r["agent"]["harness"] != "codex":
                return claude_adapter(r, take)
            a = CodexFake(rig.box, take, rig.turns)
            rig.adapters.append(a)
            return a
        sub.adapter_for = adapter_for
        claude_spec = sub.spec_for

        def spec_for(r, cfg):                       # the Codex lease home's one credential file, synthetic
            if r["agent"]["harness"] == "codex":
                path = os.path.join(cfg, "auth.json")
                with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as fh:
                    fh.write('{"synthetic": "lease"}\n')
            return claude_spec(r, cfg)
        sub.spec_for = spec_for
        rd = rb.RunDriver(drivers={"claude-code": sub, "codex": sub}, road=road, precheck=lambda d, r: None,
                          history=rig.repo.history)
        rig.repo.record_files = rd.record_files
        rig.repo.on_published = rd.published
        pre = {"arms": ["A", "O"], "rows": rows, "take_order": rows}
        ledger = rb.SpendLedger(root=root, repo=root, pre=pre, history=rig.repo.history, arms=("A", "O"))
        built = {"driver": rd, "repo": rig.repo, "window": tbi.Window(), "ledger": ledger, "rows": rows,
                 "arms": ("A", "O"), "road": road, "table": ao_table()}
        out = Path(tempfile.mkdtemp(dir=tbi.SCRATCH))
        ticks = iter(range(10 ** 6)).__next__
        with tbi.spying(rig.spy), tbi.planned(*rows), \
                mock.patch.object(prereg, "require_frozen", lambda what: pre), \
                mock.patch.object(rb, "build_run", lambda **kw: built), \
                mock.patch.object(rb, "lease_problem", lambda b, r: None), \
                mock.patch.object(tbi, "table", ao_table):
            rc = rb.rehearse_takes(out, builders={}, root=root, repo=root, clock=lambda: float(ticks()))
        return rc, json.loads((out / "summary.json").read_text()), rig

    def test_an_a_and_an_o_take_through_the_real_batch_and_ledger(self):
        with tbi.scratch_repo() as root:
            rc, summary, rig = self.rehearse(root, reads=True)
            outs = [(o["slot"], o["state"], o["reason"]) for o in rig.repo.history() if batch.is_outcome(o)]
            # The money gate admitted the A+O wave: both takes registered, launched, driven at once and
            # committed in row order. The Rig fakes Claude Code's box only, so the O take ends `failed` at its
            # postflight (no Codex native session in the fake box: nested-agent); its graded route is the athena
            # rehearsal's proof.
            self.assertEqual([(t["arm"], t["state"]) for t in summary["takes"]],
                             [("A", "committed"), ("O", "committed")], f"S4.box: {outs}")
            a, o_ = summary["takes"]
            self.assertEqual(a["route"], "graded", f"S4.box: {summary}")
            # The two drives ran at once (each started before the other ended); batch.Batch launches the whole wave
            # before its drives start, and overlap is the drives intersecting (glitch-f1's ruling 2 on the fold).
            both = a["drive_started_at"] < o_["drive_ended_at"] and o_["drive_started_at"] < a["drive_ended_at"]
            self.assertTrue(both and summary["overlap"], f"S4.box: the two drives did not overlap: {summary}")
            self.assertFalse([k for k in summary["counts"] if k.startswith("refused:")], f"S4.box: refused: {summary}")
            self.assertEqual([o[0] for o in outs], ["s1", "s2"], "S4.box")
            self.assertTrue(all(o[2] is None or "money gate" not in o[2] for o in outs), f"S4.box: {outs}")

    def test_no_spend_read_is_the_closed_money_gate_refusal(self):
        with tbi.scratch_repo() as root:
            rc, summary, rig = self.rehearse(root, reads=False)
            self.assertEqual((rc, summary), (1, {"takes": [], "overlap": False, "pass": False,
                                                 "counts": {"refused:money-gate": 1}}), "S4.box")
            self.assertEqual([o for o in rig.repo.history() if batch.is_outcome(o)], [], "S4.box: a take committed")


WITNESSES = {"rd-published-keeps": ("    try:\n        run_sub(rd, row).published(row, attempt)\n    finally:\n"
                                    "        mine = [",
                                    "    try:\n        run_sub(rd, row).published(row, attempt)\n    finally:\n"
                                    "        return\n        mine = [")}


class S2BoxWitness(unittest.TestCase):
    def test_witness_published_keeps_is_red(self):
        import types
        old, new = WITNESSES["rd-published-keeps"]
        text = (HERE / "run_builders.py").read_text()
        self.assertEqual(text.count(old), 1, "S2.box: the witness anchor")
        mod = types.ModuleType("run_builders")
        mod.__file__ = str(HERE / "run_builders.py")
        exec(compile(text.replace(old, new), mod.__file__ + " (witness)", "exec"), mod.__dict__)
        saved = MODS["rb"]
        MODS["rb"] = mod
        try:
            with self.assertRaises(AssertionError, msg="S2.box: the witness survived"):
                S2Box("test_two_takes_overlap_through_the_run_driver").test_two_takes_overlap_through_the_run_driver()
        finally:
            MODS["rb"] = saved


if __name__ == "__main__":
    unittest.main(verbosity=2)
