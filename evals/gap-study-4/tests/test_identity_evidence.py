#!/usr/bin/env python3
"""Live harness step 3b: typed identity evidence beside the raw init, for harnesses whose stream has no init event
carrying model, mode and version.

Gemini CLI's stream init names a model and a session id only (D8), so its adapter states init=None, truthfully, and
routing's init-mismatch row read every such turn as a pin mismatch. Here each turn may also carry `identity`: for each
pin field a value and the closed source it came from (stream-init, stream-stats, version-exec, submitted-argv,
unobserved). routing accepts, per field, only the sources named in ACCEPTED_IDENTITY_SOURCES; an unobserved field, a
field from a source not accepted for it, or a value that differs is a mismatch exactly as a missing init was. A raw
init that is present is still compared, and an identity beside it must agree too. Records without identity are routed
exactly as before. Nothing is fabricated into init.

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
import gemini_adapter as ga  # noqa: E402
import routing  # noqa: E402
import test_gemini_adapter as tga  # noqa: E402

PIN = {"harness": "gemini", "model": tga.MODEL, "permission_mode": tga.MODE, "version": tga.VERSION}


def setUpModule():
    tga.setUpModule()


def tearDownModule():
    tga.tearDownModule()


def ident(model=tga.MODEL, mode=tga.MODE, version=tga.VERSION, *, model_source="stream-init",
          mode_source="submitted-argv", version_source="version-exec"):
    return {"model": {"value": model, "source": model_source},
            "permission_mode": {"value": mode, "source": mode_source},
            "version": {"value": version, "source": version_source}}


def turn(identity=None, init=None, output=True):
    return aa.TurnResult(exit_code=0, text="t", stream_path=None, end_reason=aa.END_TURN, init=init, api_errors=[],
                         counters={"oom_kill_delta": 0, "pids_max_delta": 0}, started_at=1.0, ended_at=2.0,
                         agent_output=output, identity=identity)


BOX = {"preflight_ok": True, "container_started": True, "container_exited": False,
       "sidecar": {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False},
       "unexplained_operator_diffs": 0, "checker_reasons": [], "quiescence_kill": False, "outside_reach_events": 0,
       "finalize_abort": False, "committed": False, "unreadable_consequential": [], "quiescence_cap_survivors": 0}


class TheRecord(unittest.TestCase):
    def test_identity_is_typed_and_closed(self):
        turn(ident())
        turn(ident(mode=None, mode_source="unobserved"))
        for bad in ({"model": ident()["model"]},                                  # a field missing
                    dict(ident(), extra={"value": "x", "source": "stream-init"}),  # a field outside the pin
                    ident(model_source="guessed"),                                  # a source off the list
                    ident(model=7),                                                 # a value that is not a string
                    ident(mode="yolo", mode_source="unobserved"),                   # unobserved with a value
                    ident(model=None),                                              # observed but no value
                    "not a dict"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                turn(bad)

    def test_harness_records_carry_identity_only_when_a_turn_states_it(self):
        plain = aa.harness_records([turn(init={"model": "m", "permission_mode": "p", "version": "v"})], pin=PIN, box=BOX)
        self.assertNotIn("identity", plain, "records without identity must stay exactly as before")
        recs = aa.harness_records([turn(ident()), turn(None)], pin=PIN, box=BOX)
        self.assertEqual(recs["identity"], [ident(), None])
        self.assertEqual(recs["init"], [None, None])
        self.assertEqual(routing.shape_problems(recs, routing.load_table()), [])

    def test_routing_refuses_a_malformed_identity_record(self):
        table = routing.load_table()
        recs = aa.harness_records([turn(ident())], pin=PIN, box=BOX)
        for bad in ([], [ident(), ident()], [dict(ident(), model={"value": "m", "source": "guessed"})], ["x"]):
            with self.subTest(bad=bad):
                self.assertTrue(routing.shape_problems(dict(recs, identity=bad), table))


class TheMismatchRow(unittest.TestCase):
    def differs(self, op, identity, init=None):
        recs = aa.harness_records([turn(identity, init=init)], pin=PIN, box=BOX)
        return routing.holds({"op": op, "path": "init"}, recs, routing.load_table())

    def test_a_typed_identity_that_matches_the_pin_is_not_a_mismatch(self):
        self.assertFalse(self.differs("differs_from_pin", ident()))
        self.assertFalse(self.differs("differs_from_pin", ident(model_source="stream-stats")))
        self.assertTrue(self.differs("differs_from_pin", None), "a missing init with no identity stays a mismatch")

    def test_every_real_mismatch_is_still_a_mismatch(self):
        for name, identity in (("model differs", ident(model="other-model")),
                               ("version differs", ident(version="9.9.9")),
                               ("mode differs", ident(mode="default")),
                               ("model unobserved", ident(model=None, model_source="unobserved")),
                               ("version unobserved", ident(version=None, version_source="unobserved")),
                               ("mode unobserved", ident(mode=None, mode_source="unobserved")),
                               ("model only submitted", ident(model_source="submitted-argv")),
                               ("version from the stream", ident(version_source="stream-init")),
                               ("mode from the stream", ident(mode_source="stream-init"))):
            with self.subTest(name):
                self.assertTrue(self.differs("differs_from_pin", identity))
        init = {"model": tga.MODEL, "permission_mode": tga.MODE, "version": tga.VERSION}
        self.assertFalse(self.differs("differs_from_pin", None, init=init))
        self.assertTrue(self.differs("differs_from_pin", ident(model="other-model"), init=init),
                        "an identity beside a present init must agree too")
        self.assertTrue(self.differs("differs_from_pin", ident(), init=dict(init, version="9.9.9")),
                        "a matching identity never hides a present init that differs")

    def test_the_pin_refusal_reads_observed_identity(self):
        self.assertTrue(self.differs("present_differs_from_pin", ident(model="other-model")))
        self.assertTrue(self.differs("present_differs_from_pin", ident(version="9.9.9")))
        self.assertFalse(self.differs("present_differs_from_pin", ident()))
        self.assertFalse(self.differs("present_differs_from_pin", ident(mode=None, mode_source="unobserved")))
        self.assertFalse(self.differs("present_differs_from_pin", None))


class TheGeminiAdapter(unittest.TestCase):
    def test_each_turn_states_where_its_identity_came_from(self):
        a, _ = tga.take(ga, [tga.fixture("turn1-tools.jsonl")])
        t = a.turn("one", first=True, budget_s=60)
        self.assertIsNone(t.init, "Gemini's init carries no mode or version: never fabricated")
        # The box's run_turn writes the actual-submission journal (0b6f60f9, merged with the harness lane in the
        # integration lane), so the mode is read from the submitted argv, never from the pin. A turn with no journal
        # stays unobserved: test_identity_mode_evidence.test_no_journal_is_an_unobserved_mode_never_the_pin.
        self.assertEqual(t.identity, ident())

    def test_without_an_init_the_model_comes_from_the_stats_or_stays_unobserved(self):
        a, _ = tga.take(ga, [tga.fixture("no-init.jsonl")])
        t = a.turn("one", first=True, budget_s=60)
        got = t.identity["model"]
        self.assertIn(got["source"], ("stream-stats", "unobserved"))
        if got["source"] == "stream-stats":
            self.assertEqual(got["value"], tga.MODEL)
        else:
            self.assertIsNone(got["value"])

    def test_the_two_vocabularies_are_one(self):
        self.assertEqual(tuple(aa.IDENTITY_SOURCES), tuple(routing.IDENTITY_SOURCES))
        gem = routing.ACCEPTED_IDENTITY_SOURCES["gemini"]
        self.assertEqual(set(gem), set(routing.PLAN_PIN_FIELDS))
        self.assertNotIn("unobserved", {s for v in gem.values() for s in v})
        self.assertNotIn("submitted-argv", gem["model"])


if __name__ == "__main__":
    unittest.main()
