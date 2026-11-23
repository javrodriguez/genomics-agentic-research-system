#!/usr/bin/env python3
"""Live harness slice 6: Codex parity for executed refusals (3a's rule on the Codex adapter).

The Codex adapter read its stream, checked the resumed thread and read the rollout before keeping anything of the
exec, so a refusal there lost the exit, timeout and times. Now it keeps the exec in executed_turns before any read,
and a refusal after the exec (an unreadable stream, another thread resumed, a rollout the reader refuses or cannot
get) is agent_adapter.ExecutedTurnRefused, still a codex StreamError for its own callers. A refusal before the exec
keeps nothing. No Codex identity-source table is added: an identity on a codex record stays refused.

Fakes and synthetic strings only: no model, vendor, network, container runtime, credential or holdout.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import agent_adapter as aa  # noqa: E402
import codex_adapter as ca  # noqa: E402
import routing  # noqa: E402
import test_codex_adapter as tca  # noqa: E402

FIELDS = set(aa.EXECUTED_FIELDS)


def setUpModule():
    tca.setUpModule()


def tearDownModule():
    tca.tearDownModule()


class CodexKeepsTheExec(unittest.TestCase):
    def refused(self, a, line, first):
        try:
            a.turn(line, first=first, budget_s=60)
        except Exception as exc:  # noqa: BLE001 - any escape is judged by the assertions below
            got = exc
        else:
            self.fail("the turn was not refused")
        self.assertIsInstance(got, aa.ExecutedTurnRefused, f"a post-exec failure escaped untyped: {got!r}")
        if isinstance(got.__cause__, (ca.StreamError, OSError, ValueError)):
            self.assertIsInstance(got, ca.StreamError, "a reader refusal stays a codex StreamError")
        else:
            self.assertNotIsInstance(got, ca.StreamError, "a defect is never dressed as a reader refusal")
        return got

    def test_a_refusal_after_the_exec_carries_the_runtime_outcome(self):
        ok = tca.fixture("turn1-tools.jsonl")
        for name, streams, rollouts, codes in (
                ("stream off the tables", [tca.fixture("unknown-event.jsonl")], None, [0]),
                ("rollout refused", [ok], ["{not a rollout record\n"], [1]),
                ("rollout not available", [ok], ["__raise__"], [0]),
                ("rollout callback defect", [ok], ["__defect__"], [0])):
            with self.subTest(name):
                box = tca.FakeRuntime(streams, exit_codes=codes)
                texts = rollouts or [tca.fixture("rollout-two-turns.jsonl")]

                def rollout(n, _t=texts):
                    if _t[n - 1] == "__raise__":
                        raise OSError("synthetic: the rollout file was not copied out")
                    if _t[n - 1] == "__defect__":
                        raise KeyError("synthetic defect after the exec")
                    return _t[n - 1]
                a = tca.adapter(ca, box)
                a.rollout_for = rollout
                a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
                e = self.refused(a, "one", True)
                got = e.executed
                self.assertEqual(set(got), FIELDS)
                self.assertEqual((got["n"], got["exit_code"], got["timed_out"]), (1, codes[0], False))
                self.assertTrue(Path(got["stream_path"]).is_file())
                self.assertTrue(isinstance(got["refused"], str) and got["refused"])
                self.assertEqual(a.executed_turns, [got])
                self.assertEqual(a.turn_records, [])

    def test_another_thread_resumed_is_an_executed_refusal(self):
        a, box = tca.take_with(ca, [tca.fixture("turn1-tools.jsonl"), tca.fixture("turn2-other-thread.jsonl")])
        a.turn("one", first=True, budget_s=60)
        e = self.refused(a, "two", False)
        self.assertEqual(e.executed["n"], 2)
        self.assertEqual([t["refused"] for t in a.executed_turns], [None, e.executed["refused"]])

    def test_a_refusal_before_the_exec_keeps_nothing(self):
        a, box = tca.take_with(ca, [tca.fixture("turn1-tools.jsonl")])
        with self.assertRaises(ca.StreamError) as cm:
            a.turn("-flag-shaped line", first=True, budget_s=60)
        self.assertNotIsInstance(cm.exception, aa.ExecutedTurnRefused)
        self.assertEqual(a.executed_turns, [])

    def test_an_interrupt_still_propagates(self):
        a, box = tca.take_with(ca, [tca.fixture("turn1-tools.jsonl")])
        a.rollout_for = lambda n: (_ for _ in ()).throw(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            a.turn("one", first=True, budget_s=60)

    def test_a_codex_identity_has_its_own_table(self):
        """Codex slice 2 superseded this slice's "no Codex identity": the table accepts only a reroute for the model
        (tests/test_codex_identity.py binds it)."""
        self.assertEqual(routing.ACCEPTED_IDENTITY_SOURCES["codex"]["model"], ("stream-reroute",))


if __name__ == "__main__":
    unittest.main()
