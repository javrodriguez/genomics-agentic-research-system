#!/usr/bin/env python3
"""Pre-freeze review 2, MAJOR 1, step 1: the class table (fold plan prefreeze-2, section 3; lane L-A1, 29 Oct 2026).

routing.json's agent_reach answers, for every row that does not route graded after the agent's first turn, the two
rules above the rows and every checker reason routing reads, "can the agent produce the record this reads? how?", with
the route it then takes and, where the agent can reach a route that re-runs or refuses its take, the stated call
(a named exception, or a ruling owed). routing.reach_problems (run by load_table and --check) holds it to the table: its keys are exactly that set, each
stated route is the table's own, and a reachable re-running or refusing route carries its call.

  C.keys       the entries are exactly the rows, rules and reasons named above, derived here independently
  C.routes     each reason's stated route is what routing.route gives a clean after-first-turn take carrying it alone
  C.calls      a reachable entry whose route is not aborted or graded states its call; the plan's named entries read
               as the plan says (rate-limit, spend-cap and api-error reachable; watcher-gap a named exception;
               container-exit out of reach)
  C.forgery    a two-record forged rate limit beside nested-agent-session routes pause, and a forged spend-cap line is
               refused for a human, before and after the fold; the table names both roads reachable
  C.mutants    an entry dropped, a reachable re-running entry's call removed, a stated route changed, an extra key: each
               refused by check_table or reach_problems

Synthetic records only.
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import routing  # noqa: E402
import test_routing as tr  # noqa: E402
from graders import labels4  # noqa: E402

AFTER = labels4.AFTER_FIRST_TURN
KEY = "agent_reach"
FINAL = (labels4.ABORTED, labels4.GRADED)


def required(table) -> set:
    rows = {f"row:{r['id']}" for r in table["rows"] if r["when"] in (AFTER, labels4.ANY_TIME)
            and r["route"] != labels4.GRADED}
    rules = {f"rule:{table['pin_refusal']['id']}", f"rule:{table['spend_cap_refusal']['id']}"}
    return rows | rules | {f"reason:{r}" for r in table["operator_reasons"] + table["agent_event_reasons"]["ids"]}


def entries(table=None) -> dict:
    return (table or routing.load_table())[KEY]["entries"]


def routed(rid):
    rec = tr.baseline(AFTER)
    rec["checker_reasons"] = [rid]
    try:
        return routing.route(rec, tr.test_table())["route"]
    except routing.RoutingRefused:
        return "refused"


class ClassTable(unittest.TestCase):
    def test_c_keys(self):
        t = routing.load_table()
        self.assertIn(KEY, t)
        self.assertEqual(set(entries(t)), required(t))
        for rid, e in entries(t).items():
            with self.subTest(entry=rid):
                self.assertEqual(set(e), {"reachable", "how", "route", "call"})
                self.assertIsInstance(e["reachable"], bool)
                self.assertTrue(isinstance(e["how"], str) and e["how"].strip())

    def test_c_routes(self):
        t = routing.load_table()
        rows = {r["id"]: r for r in t["rows"]}
        for rid, e in entries(t).items():
            kind, _, name = rid.partition(":")
            with self.subTest(entry=rid):
                if kind == "row":
                    self.assertEqual(e["route"], rows[name]["route"])
                elif kind == "rule":
                    self.assertEqual(e["route"], "refused")
                else:
                    self.assertEqual(e["route"], routed(name))

    def test_c_calls(self):
        t = routing.load_table()
        for rid, e in entries(t).items():
            with self.subTest(entry=rid):
                if e["reachable"] and e["route"] not in FINAL:
                    self.assertTrue(isinstance(e["call"], str) and e["call"].strip(), rid)
        got = entries(t)
        for rid in ("row:rate-limit", "rule:spend-cap-reached", "row:api-error-after-first-turn", "row:init-mismatch",
                    "row:watcher-gap"):
            self.assertTrue(got[rid]["reachable"], rid)
        self.assertIn("named exception", got["row:watcher-gap"]["call"])
        # the lane review of b62445c4, finding 2: a forgeable two-record road to harness-condition-violated
        self.assertTrue(got["reason:harness-condition-violated"]["reachable"])
        self.assertIn("ruling 3", got["reason:harness-condition-violated"]["call"])
        self.assertIn("forbidden-change count", got["row:watcher-gap"]["call"])
        self.assertFalse(got["row:container-exit-after-first-turn"]["reachable"])
        self.assertIn("10003", got["row:container-exit-after-first-turn"]["how"])
        for rid in ("nested-agent-session", "subagent-unbound", "transcript-mismatch"):
            self.assertEqual(got[f"row:{rid}"]["route"], labels4.ABORTED)
            self.assertEqual(got[f"reason:{rid}"]["route"], labels4.ABORTED)
        self.assertEqual(got["reason:store-variable-assigned"]["route"], labels4.GRADED)
        # the lane re-check, R2: driver-record-fault names every source it reads, the driver ledger and its snapshot too
        how = got["reason:driver-record-fault"]["how"]
        for src in ("frozen script", "envelopes", "launch journals", "driver ledger", "snapshot", "_vc_driver_fault"):
            self.assertIn(src, how, src)

    def test_c_forgery(self):
        t = tr.test_table()
        marker = t["rate_limit_markers"][tr.TEST_HARNESS]["text"][0]
        rec = tr.baseline(AFTER)
        rec["checker_reasons"] = ["nested-agent-session"]
        rec["api_errors"] = [{"status": None, "type": None, "text": f"API Error: {marker}"}]
        self.assertEqual(routing.route(rec, t)["route"], labels4.PAUSE)
        self.assertTrue(entries()["row:rate-limit"]["reachable"])
        spend = {k: v for k, v in t["spend_cap_markers"].items()}
        spend[tr.TEST_HARNESS] = dict(spend[tr.TEST_HARNESS], text=["spend cap test"])
        t2 = dict(t, spend_cap_markers=spend)
        rec2 = tr.baseline(AFTER)
        rec2["api_errors"] = [{"status": None, "type": None, "text": "spend cap test reached"}]
        with self.assertRaises(routing.RoutingRefused):
            routing.route(rec2, t2)
        self.assertTrue(entries()["rule:spend-cap-reached"]["reachable"])

    def test_c_mutants(self):
        base = routing.load_table()
        self.assertEqual(routing.check_table(base) + routing.reach_problems(base), [])
        some = next(r for r, e in entries(base).items() if e["reachable"] and e["route"] not in FINAL)
        muts = {}
        t = copy.deepcopy(base)
        del t[KEY]["entries"]["row:watcher-gap"]
        muts["an entry dropped"] = t
        t = copy.deepcopy(base)
        t[KEY]["entries"][some]["call"] = None
        muts["a reachable re-running entry's call removed"] = t
        t = copy.deepcopy(base)
        t[KEY]["entries"]["row:nested-agent-session"]["route"] = labels4.HARNESS_ERROR
        muts["a stated route changed"] = t
        t = copy.deepcopy(base)
        t[KEY]["entries"]["row:no-such-row"] = dict(t[KEY]["entries"]["row:watcher-gap"])
        muts["an extra key"] = t
        t = copy.deepcopy(base)
        t[KEY]["entries"]["row:watcher-gap"]["reachable"] = "yes"
        muts["reachable not a bool"] = t
        t = copy.deepcopy(base)
        del t[KEY]
        muts["no table"] = t
        for name, t in muts.items():
            with self.subTest(mutant=name):
                self.assertTrue(routing.check_table(t) or routing.reach_problems(t), name)


if __name__ == "__main__":
    unittest.main()
