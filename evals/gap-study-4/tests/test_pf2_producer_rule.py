#!/usr/bin/env python3
"""Pre-freeze review 2, MAJOR 1: glitch-45's ruling 2 (29 Oct 2026), the producer rule on the round-3 reasons, and the
lane review of 8d71ae0d (MAJOR 3, NIT 6).

"gap4 routing: A" copied round 3's values into routing.json; it did not fix their routes. Read by raise site:
  P.sites    every emission of each candidate reason in check_take.py, drive.py, native_reader_registration.py and
             run.py is found by an ast walk, keyed by its function and its words (the lane re-check, R1), and must be
             pinned below; each function is classified agent (reads a record the agent's uid can write) or driver
             (reads only the driver's or the box's records). A new emission, even inside an agent function, or a pinned
             one that is gone, turns this red; a temp-copy test shows it
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
# The lane re-check (R1): every emission of each candidate reason, pinned by its function AND its words (after its tag,
# up to 64 characters; "(the id)" where the id is handed to a helper that emits it). A line added to a classified
# function, driver-only or not, is a new emission and turns P.sites red until it is read and pinned here.
EMISSIONS = {
    ('checkout-binding', 'check_take.py:checkout_problems', 'the session recorded no git status, so the checkout it opened in'),
    ('checkout-binding', 'check_take.py:checkout_problems', "the session's git status is not the driver's checkout (git user "),
    ('checkout-binding', 'check_take.py:instruction_content_problems', "the session loaded {} with content other than the pinned tree's;"),
    ('checkout-binding', 'check_take.py:instruction_content_problems', 'the session loaded {}, which the pinned tree does not carry'),
    ('checkout-binding', 'check_take.py:instruction_content_problems', 'the session recorded no instruction file, so what it was told ca'),
    ('checkout-binding', 'check_take.py:instruction_content_problems', 'the session recorded no working directory, so its instruction fi'),
    ('checkout-binding', 'check_take.py:pinned_instruction_problems', "the session loaded {} with content other than the pinned tree's;"),
    ('checkout-binding', 'check_take.py:pinned_instruction_problems', 'the session loaded {}, which the pinned tree does not carry'),
    ('checkout-binding', 'check_take.py:pinned_instruction_problems', 'the session recorded no instruction file, so what it was told ca'),
    ('checkout-binding', 'check_take.py:pinned_instruction_problems', 'the session recorded no working directory, so its instruction fi'),
    ('checkout-binding', 'check_take.py:vendor_codex_checkout_partial', '(the id)'),
    ('checkout-binding', 'check_take.py:vendor_codex_checkout_partial', "the session opened on branch {}, not the driver's {} (drive.py:3"),
    ('checkout-binding', 'check_take.py:vendor_codex_checkout_partial', "the session's commit hash is not 40 lower-case hex characters"),
    ('checkout-binding', 'check_take.py:vendor_codex_checkout_partial', "the session_meta's git record is {} {}, not one {branch, commit_"),
    ('checkout-binding', 'check_take.py:vendor_codex_instruction_content_reads', '(the id)'),
    ('checkout-binding', 'check_take.py:vendor_codex_instruction_content_reads', 'the session loaded {}, and the pinned tree carries no {} beside '),
    ('checkout-binding', 'check_take.py:vendor_codex_instruction_content_reads', 'the session recorded no instruction file, so what it was told ca'),
    ('checkout-binding', 'check_take.py:vendor_codex_instruction_content_reads', '{} for {} carries no readable text'),
    ('checkout-binding', 'check_take.py:vendor_codex_instruction_content_reads', '{}: the session loaded {} with content other than the pinned tre'),
    ('checkout-binding', 'check_take.py:vendor_gemini_checkout_partial', '(the id)'),
    ('checkout-binding', 'check_take.py:vendor_gemini_checkout_partial', 'the session context ({}) lists the directory {}, not the launch '),
    ('checkout-binding', 'check_take.py:vendor_gemini_instruction_content_reads', '(the id)'),
    ('checkout-binding', 'check_take.py:vendor_gemini_instruction_content_reads', 'the session ({}) loaded {} with content other than the pinned tr'),
    ('checkout-binding', 'check_take.py:vendor_gemini_instruction_content_reads', 'the session ({}) loaded {}, which no pinned CLAUDE.md stands bes'),
    ('checkout-binding', 'check_take.py:vendor_gemini_instruction_content_reads', 'the session context ({}) records no loaded instruction file, so '),
    ('continued-past-unheld-marker', 'check_take.py:continuation_problems', 'operator turn {} was sent, and no reply to turn {} holds its mar'),
    ('continued-past-unheld-marker', 'check_take.py:continuation_problems', 'operator turn {} was sent, and the reply to turn {} does not hol'),
    ('continued-past-unheld-marker', 'check_take.py:continuation_problems', "operator turn {}'s recovery was sent after a reply that already "),
    ('continued-past-unheld-marker', 'check_take.py:continuation_problems', "operator turn {}'s recovery was sent, and the reply before it do"),
    ('leak-in-loaded-context', 'check_take.py:check', "the agent's loaded context contains {}. Nothing the operator typ"),
    ('leak-in-loaded-context', 'check_take.py:subagent_leak_problems', "for a leak word in a copied sub-agent file's attachment records "),
    ('leak-in-loaded-context', 'check_take.py:subagent_leak_problems', "sub-agent file {}'s loaded context contains {}"),
    ('leak-in-loaded-context', 'check_take.py:vendor_codex_loaded_context_reads', '(the id)'),
    ('leak-in-loaded-context', 'check_take.py:vendor_codex_loaded_context_reads', 'the context Codex loaded for the session contains {}, which tell'),
    ('leak-in-loaded-context', 'check_take.py:vendor_gemini_loaded_context_reads', '(the id)'),
    ('leak-in-loaded-context', 'check_take.py:vendor_gemini_loaded_context_reads', 'the context Gemini CLI loaded for the agent contains {}, which t'),
    ('operator-lines', 'check_take.py:operator_line_problems', 'operator turn {} is not on the script: {}. A line that is not on'),
    ('operator-lines', 'check_take.py:operator_line_problems', 'operator turn {} was never sent: {}'),
    ('operator-lines', 'check_take.py:operator_line_problems', 'operator turn {} was sent twice; it is sent once'),
    ('operator-lines', 'check_take.py:operator_line_problems', 'the recovery for operator turn {} was sent {} times and the froz'),
    ('readers-disagree', 'check_take.py:check', 'the transcript reader counts {} user turn(s) with text and the r'),
    ('readers-disagree', 'check_take.py:design_tree_problems', 'the driver gave the take the run tree {} and the session records'),
    ('readers-disagree', 'check_take.py:vendor_design_tree_problems', 'the driver gave the take the run tree {} and the rollout records'),
    ('readers-disagree', 'check_take.py:vendor_design_tree_problems', "turn {}'s launch journal records the working folder {}, not the "),
    ('readers-disagree', 'check_take.py:vendor_gemini_run_tree_reads', '(the id)'),
    ('readers-disagree', 'check_take.py:vendor_gemini_run_tree_reads', 'the driver gave the take the run tree {} and the session context'),
    ('readers-disagree', 'check_take.py:vendor_gemini_run_tree_reads', "turn {}'s launch journal records the working folder {}, not the "),
    ('readers-disagree', 'check_take.py:vendor_operator_problems', "the ledger's {} sent line(s) are not the envelopes' {}, in order"),
    ('readers-disagree', 'check_take.py:vendor_operator_problems', "{} are not the envelopes' sent line at turn(s) {}: which lines t"),
    ('readers-disagree', 'check_take.py:vendor_operator_problems', "{} hold {} turn(s) and the envelopes {}: the CLI's own record an"),
    ('readers-disagree', 'drive.py:checker', '(the id)'),
    ('readers-disagree', 'drive.py:take_checker', '(the id)'),
    ('readers-disagree', 'run.py:human_why', '(the id)'),
    ('stop-at-held-marker', 'check_take.py:required_steps', 'the driver stopped at operator turn {} because its marker was no'),
    ('stop-at-held-marker', 'check_take.py:required_steps', 'the driver stopped at operator turn {} with no recovery sent, an'),
    ('unknown-harness-origin', 'check_take.py:check', '{} user record(s) carry a harness origin the pre-registration do'),
    ('unknown-harness-origin', 'check_take.py:vendor_codex_origin_reads', '(the id)'),
    ('unknown-harness-origin', 'check_take.py:vendor_codex_origin_reads', 'a developer message part opens with {}, not one of the sections '),
    ('unknown-harness-origin', 'check_take.py:vendor_codex_origin_reads', "a user message part is neither the turn's operator line, the AGE"),
    ('unknown-harness-origin', 'check_take.py:vendor_codex_origin_reads', 'a user message part is not one input_text: content of unknown or'),
    ('unknown-harness-origin', 'check_take.py:vendor_codex_origin_reads', 'the rollout holds a {} message, a role no reader places'),
    ('unknown-harness-origin', 'check_take.py:vendor_codex_origin_reads', 'the rollout holds {} AGENTS.md part(s) and {} environment-contex'),
    ('unknown-harness-origin', 'check_take.py:vendor_codex_origin_reads', "the rollout's operator parts are {} of the envelopes' {} sent li"),
}
MIXED = ("readers-disagree", "no-session-id", "leak-in-operator-turn", "project-name", "inherited-context",
         "session-binding", "constant-binding", "outcome-binding", "environment-record", "transcript-unreadable",
         "model-binding")


def found_sites(study: Path = STUDY) -> set:
    return {(rid, site) for rid, site, _ in found_emissions(study)}


def _text(node) -> str:
    """A string expression's literal words, each formatted part as {} (a + of two parts joined)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else "{}"
                       for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _text(node.left) + _text(node.right)
    return "{}"


def _tag(node, names: dict):
    """The candidate reason a string expression opens with ("[id] ..."), resolving f"[{NAME}] ..." through module and
    local names, or None."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _tag(node.left, names)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        m = re.match(r"\[([a-z][a-z-]*)\] ", node.value)
        return m.group(1) if m else None
    if isinstance(node, ast.JoinedStr) and node.values:
        v0 = node.values[0]
        if isinstance(v0, ast.Constant) and isinstance(v0.value, str):
            m = re.match(r"\[([a-z][a-z-]*)\] ", v0.value)
            if m:
                return m.group(1)
            if v0.value == "[" and len(node.values) > 1 and isinstance(node.values[1], ast.FormattedValue) \
                    and isinstance(node.values[1].value, ast.Name):
                return names.get(node.values[1].value.id)
    return None


def found_emissions(study: Path = STUDY) -> set:
    """(reason, file:function, its words) for every emission of a candidate reason: each string expression that
    opens with the reason's tag (its words after the tag, up to 64 characters), and each bare use of the id handed to
    another function (its words "(the id)"). The lane re-check, R1: a site is keyed by its function and its message, so
    a driver-only line added inside an agent-reading function shows."""
    out = set()
    for fname in FILES:
        tree = ast.parse((Path(study) / fname).read_text(encoding="utf-8"))
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
            local = dict(names)
            for n in ast.walk(fn):
                if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            local[t.id] = n.value.value
            inner = set()
            for node in ast.walk(fn):
                if isinstance(node, (ast.JoinedStr, ast.BinOp)):
                    inner |= {id(c) for c in ast.walk(node) if c is not node}
            for node in ast.walk(fn):
                if id(node) in inner:
                    continue
                tag = _tag(node, local) if isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp)) else None
                if tag in CANDIDATES:
                    words = re.sub(r"^\[[^\]]*\] ", "", _text(node))[:64]
                    out.add((tag, f"{fname}:{fn.name}", words))
                    continue
                bare = (node.value if isinstance(node, ast.Constant) and isinstance(node.value, str)
                        else local.get(node.id) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                        else None)
                if bare in CANDIDATES and not (isinstance(node, ast.Constant) and _is_local_def(fn, node)):
                    out.add((bare, f"{fname}:{fn.name}", "(the id)"))
    return out


def _is_local_def(fn, const) -> bool:
    """A constant that is only the value of a local `reason = "<id>"` (its emissions are counted where they are)."""
    return any(isinstance(n, ast.Assign) and n.value is const for n in ast.walk(fn))


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
        self.assertEqual(found_emissions(), EMISSIONS)
        self.assertEqual({(r, site) for r, site, _ in EMISSIONS}, set(SITES))
        self.assertEqual(found_sites(), set(SITES))

    def test_p_a_line_added_inside_an_agent_function_turns_red(self):
        """The lane re-check, R1, shown on a temp copy: a driver-only line added inside continuation_problems (an agent
        site) is a new emission the pinned set does not hold, so P.sites goes red."""
        import shutil
        import tempfile
        d = Path(tempfile.mkdtemp())
        for f in FILES:
            shutil.copy(STUDY / f, d / f)
        src = (d / "check_take.py").read_text(encoding="utf-8")
        anchor = "def continuation_problems("
        i = src.index(anchor)
        j = src.index('"""', src.index('"""', i) + 3) + 3          # after the docstring
        line = '\n    _ = "[continued-past-unheld-marker] the driver ledger cannot be read"'
        (d / "check_take.py").write_text(src[:j] + line + src[j:], encoding="utf-8")
        got = found_emissions(d)
        self.assertEqual(got - EMISSIONS, {("continued-past-unheld-marker", "check_take.py:continuation_problems",
                                            "the driver ledger cannot be read")})
        self.assertEqual(found_sites(d), set(SITES))           # the function-level key alone would not have seen it

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
