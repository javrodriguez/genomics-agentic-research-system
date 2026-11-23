#!/usr/bin/env python3
"""Every grader on a take that hands work to a sub-agent (glitch-b5's ruling on the d7107255 battery, 16 Oct 2026).

Since the Agent parity ruling the view reads Claude Code's Agent call, as its own tool kind `delegate`; its
sub-agent's own tool calls, words and results are not in the view's events (the checker reads them from the turn
stream and the copied subagents files). The ruling: a grader treats the sub-agent's actions exactly as the agent's
own where its rubric depends on them, or, if it cannot yet, refuses (GradeError) a take with any delegate call, by
a named reason (transcript_view.DELEGATED_REFUSAL), so nothing is mis-graded.

Each grader's own label cases are graded twice: as written, and with one delegate call added to the take's last
turn (transcript_view.events wrapped, so every grader reads the take through its own road).

  REFUSES   a grader whose label or flag reads the agent's tool calls (pause_adherence, plan_gate,
            precondition_refusal, and new_tasks wherever it reads a call) or words (awareness: a phrase the
            sub-agent wrote would go unscanned), handed the raw take, refuses by DELEGATED_REFUSAL (pause_adherence,
            new_tasks and awareness in their own code, the backstop; plan_gate and precondition_refusal, whose code a
            closing gate holds, nowhere but the seam). Since glitch-b5's pre-freeze ruling (16 Oct 2026) the grading
            roads hand them the PRESENTED take instead (graders/delegation.seam, delegated_take.present; parity in
            tests/test_delegated_presentation.py), and refuse only what cannot be presented.
  GRADES    a grader whose label reads only the end state (which holds the sub-agent's writes, and in the access
            log its reads, as the agent's own) and the agent's own reply grades the take as before:
            number_fidelity and confounded_design here; scope_read and template_adherence in their own modules
            (TheSubAgentRule, TheInputs), with a sub-agent's read and write shown to count as the agent's.
"""
from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import transcript_view as tv  # noqa: E402
from graders import awareness as aw  # noqa: E402
from graders import new_tasks as nt  # noqa: E402
from graders import pause_adherence as pa  # noqa: E402
from graders import plan_gate as pg  # noqa: E402
from graders import precondition_refusal as pr  # noqa: E402

_EVENTS = tv.events


def delegated_events(harness, transcript):
    """The view's events of the take, with one delegate call added to its last turn."""
    evs = list(_EVENTS(harness, transcript))
    turn = max((e.turn for e in evs), default=1)
    call = max((e.call for e in evs if e.call is not None), default=0) + 1
    return evs + [tv.AgentEvent(turn=turn, kind=tv.TOOL_CALL, text=None, tool=tv.DELEGATE, args={}, call=call)]


def outcome(fn, *a, **kw):
    """("graded", label) or ("refused", the error's words)."""
    try:
        got = fn(*a, **kw)
        return "graded", got.get("label", got.get("stop_class"))
    except (aw.GradeError, nt.GradeError, pa.GradeError, pg.GradeError) as e:
        return "refused", str(e)


def delegated(fn, *a, **kw):
    with mock.patch.object(tv, "events", delegated_events):
        return outcome(fn, *a, **kw)


REFUSED = ("refused", tv.DELEGATED_REFUSAL)


class TheView(unittest.TestCase):
    def test_the_agent_call_is_its_own_kind(self):
        self.assertEqual(tv.CC_TOOLS["Agent"][0], tv.DELEGATE)
        self.assertIn(tv.DELEGATE, tv.TOOL_KINDS)
        self.assertIn(tv.DELEGATE, tv.VOCABULARY)
        self.assertTrue(tv.DELEGATED_REFUSAL.startswith("delegated-work: "))


class TheRefusingGraders(unittest.TestCase):
    def test_pause_adherence(self):
        import test_pause_adherence as t
        for name, case in list(t.CASES.items())[:4]:
            with self.subTest(case=name):
                self.assertEqual(outcome(t.grade_case, case)[0], "graded")
                self.assertEqual(delegated(t.grade_case, case), REFUSED)

    def test_both_roads_present_a_delegated_take(self):
        """plan_gate's and precondition_refusal's code is held to its base by a closing gate, so the grader itself
        still grades a delegated take on its main thread alone; both grading roads hand plan_gate, precondition_refusal
        and new_tasks the presented take (graders/delegation.seam), refuse by a named reason what cannot be presented
        (a probe's unbound lines), and hand a take with no delegate call over as it is."""
        import probes4
        import run as run_mod
        import test_plan_gate as tg
        import test_precondition_refusal as tr
        from graders import delegation
        from test_delegated_presentation import delegated_folder
        half, kw, _, _ = next(iter(tg.CASES.values()))
        self.assertEqual(delegated(tg.g, half, **kw)[0], "graded")
        rhalf, rkw, *_ = next(iter(tr.CASES.values()))
        self.assertEqual(delegated(tr.g, rhalf, **rkw)[0], "graded")
        lines, ev = next((t for t in (tg.take(c[0], **c[1]) for c in tg.CASES.values()) if delegated_folder(t[0])))
        bound = delegated_folder(lines)
        unbound = [json.dumps(json.loads(x)) for x in bound]
        for name in ("plan_gate", "precondition_refusal", "new_tasks"):
            calls = []
            stub = types.SimpleNamespace(GradeError=pg.GradeError,
                                         grade=lambda *a, calls=calls, **k: calls.append(a) or {"label": "x"})
            roads = {
                "probes4.run_grader": lambda t, name=name: (
                    mock.patch.object(probes4.V, "grader_name", lambda task: name),
                    mock.patch.object(probes4.V, "load_grader", lambda n: stub),
                    mock.patch.object(probes4.V, "row_fields", lambda cell: {}),
                    lambda: probes4.run_grader({"grader_halves": None, "task": "x"}, "trap", {}, {}, t, ev)),
                "run.regrade": lambda t, name=name: (
                    mock.patch.object(run_mod, "grader_for", lambda n: stub),
                    mock.patch.object(run_mod.variants, "row_fields", lambda r: {}),
                    mock.patch.object(run_mod, "grader_for", lambda n: stub),
                    lambda: run_mod.regrade(name, {"half": "", "wording": "", "repeat": 0, "pressure": "",
                                                   "grader_half": None, "task": "x"}, {}, t, ev))}
            for road, build in roads.items():
                for transcript, want in ((bound, "presented"), (unbound, "refused"), (lines, "as it is")):
                    with self.subTest(grader=name, road=road, want=want):
                        calls.clear()
                        *patches, go = build(transcript)
                        with patches[0], patches[1], patches[2]:
                            try:
                                go()
                                got = None
                            except pg.GradeError as e:
                                got = str(e)
                            except Exception:  # noqa: BLE001 - a road's own bookkeeping after the grade
                                got = "after"
                        handed = [a for c in calls for a in c if isinstance(a, (list, tuple)) and a
                                  and isinstance(a[0], str)]
                        if want == "refused":
                            self.assertEqual(calls, [])
                            self.assertTrue(got.startswith(tv.DELEGATED_REFUSAL) and "not bound" in got, got)
                        elif want == "presented":
                            self.assertEqual(len(handed), 1, calls)
                            self.assertFalse(any('"Agent"' in x for x in handed[0]))
                            self.assertFalse(tv.delegated_calls(tv.events(tv.ROUND3_HARNESS, list(handed[0]))))
                            self.assertEqual(len([e for e in tv.events(tv.ROUND3_HARNESS, list(handed[0]))
                                                  if e.kind == tv.TOOL_CALL]),
                                             len([e for e in tv.events(tv.ROUND3_HARNESS, lines)
                                                  if e.kind == tv.TOOL_CALL]))
                        else:
                            self.assertEqual(len(handed), 1, calls)
                            self.assertIs(handed[0], transcript)
            with self.subTest(witness=f"{name}: the seam presents nothing"), \
                    mock.patch.object(delegation, "PRESENTED", {}), \
                    mock.patch.object(run_mod.variants, "row_fields", lambda r: {}), \
                    mock.patch.object(run_mod, "grader_for", lambda n: stub):
                calls.clear()
                try:
                    run_mod.regrade(name, {"half": "", "wording": "", "repeat": 0, "pressure": "",
                                           "grader_half": None, "task": "x"}, {}, bound, ev)
                except Exception:  # noqa: BLE001
                    pass
                self.assertTrue(calls and calls[0][0 if name != "new_tasks" else 1] is bound)

    def test_new_tasks_wherever_it_reads_a_call(self):
        """Every label case: refused exactly when its grader reads the take's tool calls (Take.post_calls), and
        graded to the same label otherwise."""
        import test_new_tasks as t
        refused = graded = 0
        real = nt.Take.post_calls
        for name, case in t.CASES.items():
            seen = []

            def spy(self, *tools, seen=seen):
                seen.append(tools)
                return real(self, *tools)
            with self.subTest(case=name), mock.patch.object(nt.Take, "post_calls", spy):
                plain = outcome(t.run_case, case)
                self.assertEqual(plain[0], "graded", plain)
                reads = bool(seen)
                got = delegated(t.run_case, case)
                if reads:
                    self.assertEqual(got, REFUSED)
                    refused += 1
                else:
                    self.assertEqual(got, plain)
                    graded += 1
        self.assertTrue(refused, "no new_tasks case reads a tool call: the refusal is untested")

    def test_awareness(self):
        import test_awareness as t
        for reply, want in t.LABEL_CASES[:4]:
            with self.subTest(reply=reply[:40]):
                self.assertEqual(outcome(t.grade, reply), ("graded", want))
                self.assertEqual(delegated(t.grade, reply), REFUSED)


class TheGradingGraders(unittest.TestCase):
    def test_number_fidelity(self):
        import test_number_fidelity as t
        for trap in (True, False):
            with self.subTest(trap=trap):
                plain = outcome(t.grade, trap, t.FIRST[trap])
                self.assertEqual(plain[0], "graded", plain)
                self.assertEqual(delegated(t.grade, trap, t.FIRST[trap]), plain)

    def test_confounded_design(self):
        import test_confounded_design as t
        for name, (half, reply, _, _, opts) in list(t.CASES.items())[:6]:
            with self.subTest(case=name):
                kw = {k: v for k, v in opts.items() if k in ("agent", "first", "before", "extra")}
                plain = outcome(t.run, half, reply, **kw)
                self.assertEqual(plain[0], "graded", plain)
                self.assertEqual(delegated(t.run, half, reply, **kw), plain)


class TheWitnesses(unittest.TestCase):
    """Each refusal removed, its grader grades the delegated take: the refusal is what refuses it."""

    @staticmethod
    def witness(mod, site, new=None):
        import types
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert src.count(site) == 1, f"{mod.__name__}: the refusal's anchor occurs {src.count(site)} times"
        m = types.ModuleType(mod.__name__ + "_witness")
        m.__file__ = mod.__file__
        sys.modules[m.__name__] = m
        try:
            mutated = site.replace("view.delegated_calls(", "False and (", 1) if new is None else new
            exec(compile(src.replace(site, mutated), mod.__file__, "exec"), m.__dict__)
        finally:
            del sys.modules[m.__name__]
        return m

    def test_each_refusal_is_load_bearing(self):
        import test_awareness as ta_
        import test_new_tasks as tn
        import test_pause_adherence as tp
        site = "    if view.delegated_calls(evs):           # the d7107255 battery ruling"
        for name, run in (
                ("pause_adherence", lambda: tp.grade_case(next(iter(tp.CASES.values())), mod=self.witness(pa, site))),
                ("awareness", lambda: ta_.grade(ta_.LABEL_CASES[0][0], mod=self.witness(
                    aw, "    if view.delegated_calls(evs):\n")))):
            with self.subTest(grader=name):
                self.assertEqual(delegated(run)[0], "graded", name)
        refused = [c for c in tn.CASES.values() if delegated(tn.run_case, c) == REFUSED]
        self.assertTrue(refused)
        m = self.witness(nt, "        if view.delegated_calls(self.evs):  # the d7107255 battery ruling")
        self.assertEqual(delegated(tn.run_case, refused[0], mod=m)[0], "graded", "new_tasks")


if __name__ == "__main__":
    unittest.main()
