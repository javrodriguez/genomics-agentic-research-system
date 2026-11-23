#!/usr/bin/env python3
"""Live harness step 3a: a turn that executed and whose record the harness then refuses stays an executed turn.

Gemini's adapter parsed its stream and checked the resumed session before keeping anything of the exec, so a refusal
after the runtime call lost the exit, timeout and times, and the driver's loop died before its ledger, quiescence
record and scan. Here: the adapter keeps the runtime outcome before it reads anything and raises a typed
agent_adapter.ExecutedTurnRefused (still a StreamError for its own callers); the driver accounts for the turn as
launched (evidence line, quiescence, its ledger row, a driver ledger written even when it was turn 1), finishes the
take's cleanup, postflight and scan, and then refuses the take for a human: batch records it failed after its drive
started (a ruling, never a re-run, never a rehearsal). A walk folder with a launch journal and no driver ledger is
refused like one with a stream (orchestrator glitch-06's ruling, 14 Oct 2026).

Fakes and synthetic strings only: no model, vendor, network, container runtime, credential or holdout.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import agent_adapter as aa  # noqa: E402
import batch  # noqa: E402
import gemini_adapter as ga  # noqa: E402
import test_box_integration as tbi  # noqa: E402
import test_gemini_adapter as tga  # noqa: E402
from graders import labels4  # noqa: E402

EXECUTED_KEYS = {"n", "exit_code", "timed_out", "started_at", "ended_at", "stream_path", "counters", "refused"}


def setUpModule():
    tga.setUpModule()
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()
    tga.tearDownModule()


class AdapterKeepsTheExec(unittest.TestCase):
    def refused(self, a, line, first):
        with self.assertRaises(ga.StreamError) as cm:
            a.turn(line, first=first, budget_s=60)
        e = cm.exception
        self.assertIsInstance(e, getattr(aa, "ExecutedTurnRefused", ()), "an executed turn's refusal is not typed")
        return e

    def test_a_refusal_after_the_exec_carries_the_runtime_outcome(self):
        ok = tga.fixture("turn1-tools.jsonl")
        for name, streams, codes in (("served model", [tga.fixture("stats-other-model.jsonl")], [0]),
                                     ("unknown exit", [ok], [2]),
                                     ("init model", [tga.fixture("init-other-model.jsonl")], [1])):
            with self.subTest(name):
                a, _ = tga.take(ga, streams, exit_codes=codes)
                e = self.refused(a, "one", True)
                got = e.executed
                self.assertEqual(set(got), EXECUTED_KEYS)
                self.assertEqual((got["n"], got["exit_code"], got["timed_out"]), (1, codes[0], False))
                self.assertTrue(Path(got["stream_path"]).is_file())
                self.assertEqual(Path(got["stream_path"]).name, "turn-1.jsonl")
                self.assertLessEqual(got["started_at"], got["ended_at"])
                self.assertEqual(set(got["counters"]), {"oom_kill_delta", "pids_max_delta"})
                self.assertTrue(isinstance(got["refused"], str) and got["refused"])
                self.assertEqual(a.executed_turns, [got], "the exec was not kept before the read")
                self.assertEqual(a.turn_records, [], "a refused read never becomes a turn record")

    def test_any_exception_after_the_exec_is_an_executed_refusal(self):
        real = ga.read_stream
        ga.read_stream = lambda text, model: (_ for _ in ()).throw(KeyError("synthetic defect after the exec"))
        try:
            a, _ = tga.take(ga, [tga.fixture("turn1-tools.jsonl")])
            try:
                a.turn("one", first=True, budget_s=60)
            except Exception as exc:  # noqa: BLE001 - judged below
                got = exc
            else:
                self.fail("the turn was not refused")
        finally:
            ga.read_stream = real
        self.assertIsInstance(got, aa.ExecutedTurnRefused, f"escaped untyped: {got!r}")
        self.assertNotIsInstance(got, ga.StreamError, "a defect is never dressed as a reader refusal")
        self.assertEqual(a.executed_turns[-1]["refused"][:8], "KeyError")

    def test_a_resumed_other_session_is_an_executed_refusal_on_turn_two(self):
        ok, resume = tga.fixture("turn1-tools.jsonl"), tga.fixture("turn2-resume.jsonl")
        other = resume.replace(tga.SID, "other-session-1")
        self.assertNotEqual(other, resume)
        a, _ = tga.take(ga, [ok, other])
        a.turn("one", first=True, budget_s=60)
        e = self.refused(a, "two", False)
        self.assertEqual(e.executed["n"], 2)
        self.assertEqual([t["refused"] for t in a.executed_turns], [None, e.executed["refused"]])

    def test_a_timed_out_exec_keeps_its_timeout(self):
        a, _ = tga.take(ga, [tga.fixture("stats-other-model.jsonl")], timeout_at=1)
        e = self.refused(a, "one", True)
        self.assertEqual((e.executed["timed_out"], e.executed["exit_code"]), (True, None))

    def test_a_refusal_before_the_exec_is_not_an_executed_turn(self):
        a, box = tga.take(ga, [tga.fixture("turn1-tools.jsonl")])
        with self.assertRaises(ga.StreamError) as cm:
            a.turn("-flag-shaped line", first=True, budget_s=60)
        self.assertNotIsInstance(cm.exception, getattr(aa, "ExecutedTurnRefused", ()))
        self.assertEqual(getattr(a, "executed_turns", None), [])
        self.assertEqual(tga.turn_calls(box), [])

    def test_an_executed_refusal_is_never_a_pre_turn_refusal(self):
        import drive
        e = aa.ExecutedTurnRefused("synthetic", executed=dict.fromkeys(EXECUTED_KEYS, None))
        self.assertFalse(drive.pre_turn_refusal(e))
        both = type("Both", (aa.ExecutedTurnRefused, ValueError), {})("synthetic",
                                                                         executed=dict.fromkeys(EXECUTED_KEYS, None))
        self.assertFalse(drive.pre_turn_refusal(both))
        with self.assertRaises(TypeError):
            aa.ExecutedTurnRefused("synthetic", executed={"n": 1})


class RefusingAdapter(tbi.FakeAdapter):
    """FakeAdapter whose turn `refuse_at` executes (its stream written) and then refuses its own record."""

    def __init__(self, *a, refuse_at, timed_out=False, **kw):
        super().__init__(*a, **kw)
        self.refuse_at, self.timed_out = refuse_at, timed_out

    def _turn(self, line, *, first, budget_s):
        n = self._turns + 1
        if n != self.refuse_at:
            return super()._turn(line, first=first, budget_s=budget_s)
        import drive
        path = drive.stream_path(self.take, n)
        started = self.box.tick()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{\"type\": \"unreadable\"}\n")
        raise aa.ExecutedTurnRefused("synthetic: the stream is off the tables", executed={
            "n": n, "exit_code": None if self.timed_out else 0, "timed_out": self.timed_out,
            "started_at": started, "ended_at": self.box.tick(),
            "stream_path": path, "counters": {"oom_kill_delta": 0, "pids_max_delta": 0},
            "refused": "synthetic: the stream is off the tables"})


class DriverAccountsForTheTurn(unittest.TestCase):
    def drive_with(self, refuse_at, timed_out=False):
        tbi.need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        root_cm = tbi.scratch_repo()
        root = root_cm.__enter__()
        self.addCleanup(root_cm.__exit__, None, None, None)
        rig = tbi.Rig(tbi.drive, root)
        rig.adapter_for = lambda r, take: rig.adapters.append(
            RefusingAdapter(rig.box, take, rig.turns, refuse_at=refuse_at, timed_out=timed_out)) or rig.adapters[-1]
        rig.driver.adapter_for = rig.adapter_for
        b, got = tbi.run_batch(rig, [tbi.row(1)])
        return rig, got

    def check(self, refuse_at, timed_out=False):
        rig, got = self.drive_with(refuse_at, timed_out)
        self.assertEqual(len(got), 1)
        o = got[0]
        self.assertEqual(o["state"], labels4.FAILED)
        self.assertIn("executed", o["reason"])
        self.assertIs(o["drive_started"], True)
        self.assertTrue(batch.needs_ruling(o), "an executed refusal must wait for a ruling")
        self.assertIs(o["rerun"], False)
        self.assertEqual(rig.adapters[0].ended, 1)
        self.assertEqual(rig.box.empty(), [])
        self.assertEqual(rig.checked, [], "the checker never reads a take whose turn record was refused")
        ledger_path = Path(rig.take().folder) / "driver-ledger.json"
        self.assertTrue(ledger_path.is_file(), "a launched turn makes the driver ledger mandatory")
        ledger = json.loads(ledger_path.read_text())
        self.assertIsNone(ledger["first_agent_turn"], "unknown agent output must stay unknown, never False")
        self.assertIn("executed", ledger["outcome"])
        refusal = ledger["executed_refusal"]
        self.assertEqual((refusal["n"], refusal["exit_code"], refusal["timed_out"]),
                         (refuse_at, None if timed_out else 0, timed_out))
        self.assertIs(refusal["quiescence_kill"], timed_out, "a timed-out turn's processes are killed at once")
        self.assertEqual(ledger["turns"][-1]["exit"], 124 if timed_out else 0)
        self.assertEqual(refusal["stream"], f"turn-{refuse_at}.jsonl")
        self.assertIn(f"turn-{refuse_at}.jsonl", ledger["streams"])
        self.assertEqual(len(ledger["turns"]), refuse_at)
        self.assertEqual(ledger["turns"][-1]["refused"], refusal["refused"])
        self.assertIsNone(ledger["turns"][-1]["end"])
        return ledger

    def test_a_later_turn_refused_after_execution(self):
        self.check(2)

    def test_turn_one_refused_after_execution(self):
        self.check(1)

    def test_a_timed_out_turn_refused_after_execution(self):
        self.check(2, timed_out=True)


class WalkLaunchJournal(unittest.TestCase):
    def test_a_launch_journal_without_a_ledger_is_refused(self):
        import drive
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "walk"
            folder.mkdir()
            for name in ("grade.json", "check.json", "refusal.json", "turn-1.jsonl.launch.json"):
                (folder / name).write_text("{}\n")
            with self.assertRaises(drive.DriveRefused):
                drive.walk_files(folder)
            (folder / "driver-ledger.json").write_text("{}\n")
            kinds = dict((Path(p).name, k) for p, k in drive.walk_files(folder))
            self.assertEqual(kinds["turn-1.jsonl.launch.json"], "launch")


if __name__ == "__main__":
    unittest.main()
