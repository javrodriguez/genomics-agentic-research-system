#!/usr/bin/env python3
"""Codex slice 2: the Codex identity-source table, as routing reads it.

model     stream-reroute only: exec's reroute item names the served model; the requested model (the argv's -m, the
          rollout's turn_context) is never proof, so without a reroute the model is unobserved;
version   version-exec (`codex --version` in the take container);
mode      submitted-argv (the turn's launch journal, the argv checked exactly by vendor_provenance.launch_facts).
An unobserved field, a source not accepted for it, or a value off the pin is a mismatch for the init-mismatch row
(differs_from_pin); the pin refusal (present_differs_from_pin) reads only an observed value that differs. So a Codex
turn with no reroute reads as a mismatch after the first turn: the consequence named for a ruling in the slice report.
Synthetic strings only.
"""
from __future__ import annotations

import sys
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import agent_adapter as aa  # noqa: E402
import routing  # noqa: E402

FIELDS = ("model", "permission_mode", "version")
PIN = {"harness": "codex", "model": "gpt-6-luna", "permission_mode": "bypass", "version": "0.162.1"}


def ident(model=("gpt-6-luna", "stream-reroute"), mode=("bypass", "submitted-argv"), version=("0.162.1", "version-exec")):
    return {"model": {"value": model[0], "source": model[1]},
            "permission_mode": {"value": mode[0], "source": mode[1]},
            "version": {"value": version[0], "source": version[1]}}


def differs(entry, present_only=False):
    return routing._identity_differs(entry, PIN, FIELDS, present_only=present_only)


class CodexTable(unittest.TestCase):
    def test_the_table(self):
        self.assertEqual(routing.ACCEPTED_IDENTITY_SOURCES["codex"],
                         {"model": ("stream-reroute",), "version": ("version-exec",),
                          "permission_mode": ("submitted-argv",)})
        self.assertIn("stream-reroute", aa.IDENTITY_SOURCES)
        self.assertEqual(tuple(aa.IDENTITY_SOURCES), tuple(routing.IDENTITY_SOURCES))
        self.assertIn("stream-reroute", routing.OBSERVED_IDENTITY_SOURCES)

    def test_the_init_mismatch_row(self):
        self.assertFalse(differs(ident()), "every field observed by its accepted source and on the pin")
        for why, entry in (("a reroute elsewhere", ident(model=("gpt-6-sol", "stream-reroute"))),
                           ("the requested model as if observed", ident(model=("gpt-6-luna", "stream-init"))),
                           ("the mode unobserved", ident(mode=(None, "unobserved"))),
                           ("a journal off the invocation",
                            ident(mode=("launch-differs-from-registered-invocation", "submitted-argv"))),
                           ("another version", ident(version=("0.161.0", "version-exec")))):
            with self.subTest(why=why):
                self.assertTrue(differs(entry))

    def test_d_int_2_an_unobserved_served_model_is_accepted_for_codex_only(self):
        """D-INT-2 (glitch-06, 14 Oct 2026; for Javier's review before the freeze): for arm O only, a served model that
        is unobserved (no reroute) is accepted in the init-mismatch row; the requested model is then assumed."""
        self.assertFalse(differs(ident(model=(None, "unobserved"))), "codex: no reroute, the requested model assumed")
        self.assertTrue(differs(ident(model=("gpt-6-sol", "stream-reroute"))), "a reroute elsewhere is a mismatch")
        self.assertTrue(differs(ident(mode=(None, "unobserved"))), "only the model is accepted unobserved")
        self.assertTrue(differs(ident(version=(None, "unobserved"))), "only the model is accepted unobserved")
        gem = dict(PIN, harness="gemini", model="gemini-3.8-flash", permission_mode="yolo", version="0.64.0")
        gem_ident = {"model": {"value": None, "source": "unobserved"},
                     "permission_mode": {"value": "yolo", "source": "submitted-argv"},
                     "version": {"value": "0.64.0", "source": "version-exec"}}
        self.assertTrue(routing._identity_differs(gem_ident, gem, FIELDS, present_only=False),
                        "Gemini's unobserved model stays a mismatch")
        self.assertEqual(routing.UNOBSERVED_ACCEPTED, {"codex": ("model",)})
        self.assertEqual(routing.SERVED_MODEL_LIMIT, "for the OpenAI arm, the served model is verified only when the "
                                                     "CLI reports a reroute; otherwise the requested model is assumed")

    def test_the_pin_refusal_reads_only_an_observed_difference(self):
        self.assertFalse(differs(ident(model=(None, "unobserved")), present_only=True))
        self.assertTrue(differs(ident(model=("gpt-6-sol", "stream-reroute")), present_only=True))
        self.assertTrue(differs(ident(version=("0.161.0", "version-exec")), present_only=True))


class ServedModelRecorded(unittest.TestCase):
    """D-INT-2: each Codex turn's served-model evidence is recorded per take in the driver ledger, as identity carried
    it ({value: null, source: unobserved} without a reroute); other harnesses' ledgers carry no such key."""

    def test_the_ledger_records_it(self):
        import dataclasses
        sys.path.insert(0, str(HERE / "tests"))
        import test_box_integration as tbi
        import test_vendor_take_records as tvr
        tbi.setUpModule()
        self.addCleanup(tbi.tearDownModule)
        unobserved = {"value": None, "source": "unobserved"}
        real = tbi.FakeAdapter._turn

        def turn(adapter, line, *, first, budget_s):
            got = real(adapter, line, first=first, budget_s=budget_s)
            if adapter.name != "codex":
                return got
            return dataclasses.replace(got, identity={"model": dict(unobserved),
                                                      "permission_mode": {"value": "bypass", "source": "submitted-argv"},
                                                      "version": {"value": "0.162.1", "source": "version-exec"}})
        with unittest.mock.patch.object(tbi.FakeAdapter, "_turn", turn):
            rig, ledger, refused = tvr.drive_vendor(self, "codex", native=False)
        self.assertEqual(ledger["served_model"], [unobserved, unobserved])
        rerouted = {"value": "gpt-6-sol", "source": "stream-reroute"}      # a turn the CLI reports rerouted

        def reroute(adapter, line, *, first, budget_s):
            got = turn(adapter, line, first=first, budget_s=budget_s)
            return got if first else dataclasses.replace(got, identity=dict(got.identity, model=dict(rerouted)))
        with unittest.mock.patch.object(tbi.FakeAdapter, "_turn", reroute):
            rig, ledger, refused = tvr.drive_vendor(self, "codex", native=False)
        self.assertEqual(ledger["served_model"], [unobserved, rerouted])
        rig, ledger, refused = tvr.drive_vendor(self, "gemini")
        self.assertNotIn("served_model", ledger)


if __name__ == "__main__":
    unittest.main()
