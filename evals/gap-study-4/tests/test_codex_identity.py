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
        for why, entry in (("no reroute: the model is unobserved", ident(model=(None, "unobserved"))),
                           ("a reroute elsewhere", ident(model=("gpt-6-sol", "stream-reroute"))),
                           ("the requested model as if observed", ident(model=("gpt-6-luna", "stream-init"))),
                           ("the mode unobserved", ident(mode=(None, "unobserved"))),
                           ("a journal off the invocation",
                            ident(mode=("launch-differs-from-registered-invocation", "submitted-argv"))),
                           ("another version", ident(version=("0.161.0", "version-exec")))):
            with self.subTest(why=why):
                self.assertTrue(differs(entry))

    def test_the_pin_refusal_reads_only_an_observed_difference(self):
        self.assertFalse(differs(ident(model=(None, "unobserved")), present_only=True))
        self.assertTrue(differs(ident(model=("gpt-6-sol", "stream-reroute")), present_only=True))
        self.assertTrue(differs(ident(version=("0.161.0", "version-exec")), present_only=True))


if __name__ == "__main__":
    unittest.main()
