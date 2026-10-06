#!/usr/bin/env python3
"""agent_adapter.py: the call order is enforced, text never reaches the harness records, and the
scripted adapter replays exactly its script. Each check also runs against an in-memory mutation of
what it guards and must go red."""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_adapter as aa  # noqa: E402

PIN = {"model": "pinned-model", "permission_mode": "bypassPermissions", "version": "1.0.0"}
SECRET_TEXT = "AGENT-TEXT-MUST-NOT-LEAK-7f3a"
BOX = {"preflight_ok": True, "container_started": True,
       "sidecar": {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False}}


def turn(**kw) -> aa.TurnResult:
    base = dict(exit_code=0, text=SECRET_TEXT, stream_path="/host/stream.jsonl", end_reason=aa.END_TURN,
                init=dict(PIN), started_at=1.0, ended_at=2.0)
    base.update(kw)
    return aa.TurnResult(**base)


def order_violations(make) -> list[str]:
    """Each out-of-order call that did NOT raise AdapterStateError."""
    missed = []
    cases = {
        "turn before start": lambda a: a.turn("x", first=True, budget_s=1),
        "end before start": lambda a: a.end_take(),
        "second start": lambda a: (a.start_take({"row_id": 1}), a.start_take({"row_id": 1})),
        "first=False on first turn": lambda a: (a.start_take({"row_id": 1}), a.turn("x", first=False, budget_s=1)),
        "first=True on second turn": lambda a: (a.start_take({"row_id": 1}), a.turn("x", first=True, budget_s=1),
                                                a.turn("y", first=True, budget_s=1)),
        "second end": lambda a: (a.start_take({"row_id": 1}), a.end_take(), a.end_take()),
        "past the script": lambda a: (a.start_take({"row_id": 1}), a.turn("x", first=True, budget_s=1),
                                      a.turn("y", first=False, budget_s=1), a.turn("z", first=False, budget_s=1)),
    }
    for name, call in cases.items():
        try:
            call(make())
        except aa.AdapterStateError:
            continue
        missed.append(name)
    return missed


def text_leaks(records) -> bool:
    return SECRET_TEXT in json.dumps(records)


class TestAdapter(unittest.TestCase):
    def make(self):
        return aa.ScriptedAdapter([turn(), turn(end_reason=aa.END_TIMED_OUT)], container_id="c-123")

    def test_order_enforced(self):
        self.assertEqual(order_violations(self.make), [])

    def test_order_check_can_fail(self):
        with mock.patch.object(aa.AgentAdapter, "_check_turn", lambda self, first: None):
            self.assertIn("turn before start", order_violations(self.make))
        with mock.patch.object(aa.AgentAdapter, "_leave", lambda self: None):
            self.assertIn("second end", order_violations(self.make))

    def test_replays_script_and_records_lines(self):
        a = self.make()
        self.assertEqual(a.start_take({"row_id": 7}), {"container_id": "c-123"})
        r1 = a.turn("open", first=True, budget_s=5)
        r2 = a.turn("probe", first=False, budget_s=5)
        a.end_take()
        self.assertEqual((r1.end_reason, r2.end_reason), (aa.END_TURN, aa.END_TIMED_OUT))
        self.assertEqual(a.lines, ["open", "probe"])
        self.assertEqual((a.ended, a.remaining, a.version(), a.name), (1, 0, "scripted-1", "scripted"))

    def test_base_class_is_abstract(self):
        with self.assertRaises(NotImplementedError):
            aa.AgentAdapter().version()
        with self.assertRaises(NotImplementedError):
            aa.AgentAdapter().start_take({"row_id": 1})

    def test_start_take_must_name_container(self):
        class Bad(aa.ScriptedAdapter):
            def _start(self, take):
                return {}
        with self.assertRaises(aa.AdapterStateError):
            Bad([turn()]).start_take({"row_id": 1})

    def test_turnresult_validation(self):
        for bad in (dict(end_reason="done"), dict(counters={"oom_kill_delta": 0}),
                    dict(init={"model": "m"}), dict(started_at=3.0, ended_at=2.0)):
            with self.assertRaises(ValueError, msg=str(bad)):
                turn(**bad)

    def test_harness_record_has_no_text(self):
        rec = turn().harness_record()
        self.assertNotIn("text", rec)
        self.assertFalse(text_leaks(rec))
        records = aa.harness_records([turn(), turn()], pin=PIN, box=BOX)
        self.assertFalse(text_leaks(records))

    def test_text_check_can_fail(self):
        with mock.patch.object(aa.TurnResult, "harness_record", lambda self: aa.asdict(self)):
            self.assertTrue(text_leaks(turn().harness_record()))
        self.assertTrue(text_leaks({"leaked": SECRET_TEXT}))

    def test_harness_records_shape(self):
        t1 = turn(api_error=None)
        t2 = turn(exit_code=1, end_reason=aa.END_ERROR, api_error={"status": 429, "type": "rate_limit_error"},
                  counters={"oom_kill_delta": 1, "pids_max_delta": 0})
        r = aa.harness_records([t1, t2], pin=PIN, box=BOX)
        self.assertEqual(r["ledger"], {"first_turn_started": True, "turns": 2, "end": aa.END_ERROR,
                                       "turn_ends": [aa.END_TURN, aa.END_ERROR], "committed": False, "finalize_abort": False})
        self.assertEqual(r["exit"]["exec_codes"], [0, 1])
        self.assertEqual(r["cgroup"], {"oom_kill_delta": 1, "pids_max_delta": 0})
        self.assertEqual(r["api_error"]["status"], 429)
        empty = aa.harness_records([], pin=PIN, box=BOX)
        self.assertEqual((empty["ledger"]["first_turn_started"], empty["ledger"]["end"]), (False, None))


if __name__ == "__main__":
    unittest.main()
