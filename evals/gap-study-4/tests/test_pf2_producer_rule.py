#!/usr/bin/env python3
"""Pre-freeze review 2, MAJOR 1: glitch-45's ruling 2 (29 Oct 2026), the producer rule on the round-3 reasons, and the
lane review of 8d71ae0d (MAJOR 3, NIT 6).

"gap4 routing: A" copied round 3's values into routing.json; it did not fix their routes. Read by raise site:
  P.sites    every raise site (function) of each candidate reason in check_take.py, drive.py,
             native_reader_registration.py and run.py is found by an ast walk and must be classified below, agent
             (reads a record the agent's uid can write) or driver (reads only the driver's or the box's records); a new
             site, or a classified site that is gone, turns this red
  P.pure     the pure reasons are DERIVED from that table (every site agent) and must be exactly the ones the
             agent-reachable-reason row names; each routes aborted after the first turn, a rehearsal before it, and
             harness-error beside harness-condition-violated (glitch-b5's ruling 3)
  P.mixed    a reason with a driver site keeps harness-error, and the class table says "mixed, kept harness-error,
             counted in STOPPED_ROUTES"; driver-record-fault, the driver-only sites' own id, routes harness-error
  P.finalize finalize-abort-after-first-turn routes aborted (an operator step that fails on a run tree the agent
             shaped; round 3's own reading)
  P.hcv      harness-condition-violated keeps its precedence; the table says "reachable, kept, counted"
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(HERE))

import routing  # noqa: E402
import test_routing as tr  # noqa: E402
from graders import labels4  # noqa: E402

FILES = ("check_take.py", "drive.py", "native_reader_registration.py", "run.py")
CANDIDATES = ("readers-disagree", "unknown-harness-origin", "operator-lines", "stop-at-held-marker",
              "continued-past-unheld-marker", "leak-in-loaded-context", "checkout-binding")
AGENT, DRIVER, NOT_RAISED = "agent", "driver", "not a raise site"
# (reason, file:function) -> its side, read at the site (the lane review of 8d71ae0d checked each; L-A1, 29 Oct 2026)
SITES = {
    ("checkout-binding", "check_take.py:checkout_problems"): AGENT,               # the session file's session_context
    ("checkout-binding", "check_take.py:instruction_content_problems"): AGENT,    # the session file's attachments
    ("checkout-binding", "check_take.py:pinned_instruction_problems"): AGENT,     # the same, against the pinned bytes
    ("checkout-binding", "check_take.py:vendor_codex_checkout_partial"): AGENT,   # the rollout's session_meta.git
    ("checkout-binding", "check_take.py:vendor_codex_instruction_content_reads"): AGENT,   # the rollout's AGENTS.md
    ("checkout-binding", "check_take.py:vendor_gemini_checkout_partial"): AGENT,  # the native listing root
    ("checkout-binding", "check_take.py:vendor_gemini_instruction_content_reads"): AGENT,  # the native context bodies
    ("continued-past-unheld-marker", "check_take.py:continuation_problems"): AGENT,   # the session replies
    ("leak-in-loaded-context", "check_take.py:check"): AGENT,                     # the session file's context
    ("leak-in-loaded-context", "check_take.py:subagent_leak_problems"): AGENT,    # the sub-agent files
    ("leak-in-loaded-context", "check_take.py:vendor_codex_loaded_context_reads"): AGENT,  # the rollout
    ("leak-in-loaded-context", "check_take.py:vendor_gemini_loaded_context_reads"): AGENT,  # the native session
    ("operator-lines", "check_take.py:operator_line_problems"): AGENT,            # the session operator lines
    ("stop-at-held-marker", "check_take.py:required_steps"): AGENT,               # the session replies after the stop
    ("unknown-harness-origin", "check_take.py:check"): AGENT,                     # the session file's origins
    ("unknown-harness-origin", "check_take.py:vendor_codex_origin_reads"): AGENT,  # the rollout's parts
    ("readers-disagree", "check_take.py:check"): AGENT,
    ("readers-disagree", "check_take.py:design_tree_problems"): AGENT,
    ("readers-disagree", "check_take.py:vendor_design_tree_problems"): DRIVER,    # a launch journal's cwd (box)
    ("readers-disagree", "check_take.py:vendor_gemini_run_tree_reads"): DRIVER,   # a launch journal's cwd (box)
    ("readers-disagree", "check_take.py:vendor_operator_problems"): DRIVER,       # the ledger against the envelopes
    ("readers-disagree", "drive.py:checker"): DRIVER,      # any cross-check problem, the driver's snapshot record too
    ("readers-disagree", "drive.py:take_checker"): DRIVER,
    ("readers-disagree", "run.py:human_why"): NOT_RAISED,  # the human sample's why, never a checker reason
}
MIXED = ("readers-disagree", "no-session-id", "leak-in-operator-turn", "project-name", "inherited-context",
         "session-binding", "constant-binding", "outcome-binding", "environment-record", "transcript-unreadable",
         "model-binding")


def found_sites() -> set:
    out = set()
    for fname in FILES:
        tree = ast.parse((STUDY / fname).read_text(encoding="utf-8"))
        names = {}
        for n in tree.body:
            if isinstance(n, ast.Assign):
                pairs = ([(t, n.value) for t in n.targets] if isinstance(n.value, ast.Constant)
                         else list(zip(n.targets[0].elts, n.value.elts))
                         if isinstance(n.value, ast.Tuple) and isinstance(n.targets[0], ast.Tuple) else [])
                for t, v in pairs:
                    if isinstance(t, ast.Name) and isinstance(v, ast.Constant) and isinstance(v.value, str):
                        names[t.id] = v.value
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            for node in ast.walk(fn):
                got = None
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    m = re.match(r"\[([a-z][a-z-]*)\] ", node.value)
                    got = m.group(1) if m else (node.value if node.value in CANDIDATES else None)
                elif isinstance(node, ast.JoinedStr) and node.values:
                    v0 = node.values[0]
                    if isinstance(v0, ast.Constant) and isinstance(v0.value, str):
                        m = re.match(r"\[([a-z][a-z-]*)\] ", v0.value)
                        got = m.group(1) if m else None
                        if v0.value == "[" and len(node.values) > 1 and isinstance(node.values[1], ast.FormattedValue) \
                                and isinstance(node.values[1].value, ast.Name):
                            got = names.get(node.values[1].value.id)
                elif isinstance(node, ast.Name) and names.get(node.id) in CANDIDATES:
                    got = names[node.id]
                if got in CANDIDATES:
                    out.add((got, f"{fname}:{fn.name}"))
    return out


def route(ids, phase=labels4.AFTER_FIRST_TURN, edit=None):
    rec = tr.baseline(phase)
    if phase == labels4.BEFORE_FIRST_TURN:
        tr.silent_turn(rec)
    rec["checker_reasons"] = list(ids)
    if edit:
        edit(rec)
    return routing.route(rec, tr.test_table())


def derived_pure() -> tuple:
    return tuple(r for r in CANDIDATES if all(side == AGENT for (rid, _), side in SITES.items()
                                               if rid == r and side != NOT_RAISED))


class ProducerRule(unittest.TestCase):
    def test_p_sites(self):
        self.assertEqual(found_sites(), set(SITES))

    def test_p_pure(self):
        pure = derived_pure()
        row = next(r for r in routing.load_table()["rows"] if r["id"] == "agent-reachable-reason")
        self.assertEqual(tuple(c["value"] for c in row["any_of"]), pure)
        self.assertNotIn("readers-disagree", pure)
        entries = routing.load_table()["agent_reach"]["entries"]
        for rid in pure:
            with self.subTest(reason=rid):
                self.assertEqual(route([rid])["route"], labels4.ABORTED)
                self.assertEqual(route([rid])["rows"], ["agent-reachable-reason"])
                self.assertEqual(route([rid], labels4.BEFORE_FIRST_TURN)["route"], labels4.REHEARSAL)
                self.assertEqual(route([rid, "harness-condition-violated"])["route"], labels4.HARNESS_ERROR)
                self.assertIsNone(entries[f"reason:{rid}"]["call"], rid)

    def test_p_mixed_and_driver(self):
        entries = routing.load_table()["agent_reach"]["entries"]
        for rid in MIXED + ("script-not-a-list", "fixture-binding", "invocation", "stop-without-a-wait-point",
                            "driver-record-fault"):
            with self.subTest(reason=rid):
                self.assertEqual(route([rid])["route"], labels4.HARNESS_ERROR)
        for rid in MIXED:
            with self.subTest(reason=rid):
                self.assertIn("mixed, kept harness-error, counted in STOPPED_ROUTES", entries[f"reason:{rid}"]["call"])
                self.assertNotIn("OWED", entries[f"reason:{rid}"]["call"])
        self.assertFalse(entries["reason:driver-record-fault"]["reachable"])

    def test_p_finalize(self):
        got = route([], edit=lambda r: r["ledger"].__setitem__("finalize_abort", True))
        self.assertEqual(got["route"], labels4.ABORTED)
        self.assertEqual(got["rows"], ["finalize-abort-after-first-turn"])

    def test_p_hcv(self):
        e = routing.load_table()["agent_reach"]["entries"]["reason:harness-condition-violated"]
        self.assertTrue(e["reachable"])
        self.assertIn("reachable, kept, counted", e["call"])
        self.assertEqual(route(["harness-condition-violated", "subagent-unbound"])["route"], labels4.HARNESS_ERROR)

    def test_p_driver_sites_raise_the_driver_id(self):
        """NIT 6 and MAJOR 3: the frozen-script line, a codex envelope or ledger read failure and the Gemini launch
        journals' missing working folder raise driver-record-fault, never the agent's reason."""
        import check_take as ct
        src = (STUDY / "check_take.py").read_text(encoding="utf-8")
        self.assertIn('f"[{DRIVER_RECORD_FAULT}] operator turn {step[\'n\']} renders to nothing', src)
        self.assertIn('f"[{DRIVER_RECORD_FAULT}] the envelopes cannot be read', src)
        self.assertIn('f"[{DRIVER_RECORD_FAULT}] the launch journals record no one working folder', src)
        import tempfile
        d = Path(tempfile.mkdtemp())
        (d / "driver-ledger.json").write_text("{not json")
        got = ct._vc_driver_fault(d / "transcript.jsonl")
        self.assertEqual(ct.reason_ids(got), [ct.DRIVER_RECORD_FAULT], got)
        for fn in (ct.vendor_codex_checkout_partial, ct.vendor_codex_instruction_content_reads):
            self.assertEqual(ct.reason_ids(fn(d / "transcript.jsonl") if fn is ct.vendor_codex_checkout_partial
                                           else fn(d / "transcript.jsonl", None)), [ct.DRIVER_RECORD_FAULT])


if __name__ == "__main__":
    unittest.main()
