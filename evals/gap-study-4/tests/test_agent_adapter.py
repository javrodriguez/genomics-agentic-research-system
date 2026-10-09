#!/usr/bin/env python3
"""agent_adapter.py: the call order is enforced, text never reaches the harness records, every box
record is required and never coerced, every API error is carried, the first turn starts only with
agent output, and the turn ends are labels4's. Each check also runs against an in-memory mutation
of what it guards and must go red."""

from __future__ import annotations

import ast
import json
import os
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import agent_adapter as aa  # noqa: E402
from graders import labels4  # noqa: E402

PIN = {"model": "pinned-model", "permission_mode": "bypassPermissions", "version": "1.0.0"}
SECRET_TEXT = "AGENT-TEXT-MUST-NOT-LEAK-7f3a"
SIDECAR = {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False}
# Every box key, explicitly (none is defaulted by harness_records).
BOX = {"preflight_ok": True, "container_started": True, "container_exited": False, "sidecar": dict(SIDECAR),
       "unexplained_operator_diffs": 0, "checker_reasons": [], "quiescence_kill": False,
       "outside_reach_events": 0, "finalize_abort": False, "committed": False,
       "unreadable_consequential": [], "quiescence_cap_survivors": 0}


def turn(**kw) -> aa.TurnResult:
    base = dict(exit_code=0, text=SECRET_TEXT, stream_path="/host/stream.jsonl", end_reason=aa.END_TURN,
                init=dict(PIN), api_errors=[], counters={"oom_kill_delta": 0, "pids_max_delta": 0}, started_at=1.0, ended_at=2.0,
                agent_output=True)
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


def box_key_problems() -> list[str]:
    """Each box key whose absence harness_records did NOT refuse with BoxRecordError, and an
    unknown key it did not refuse."""
    p = []
    for key in sorted(BOX):
        b = dict(BOX)
        del b[key]
        try:
            aa.harness_records([turn()], pin=PIN, box=b)
        except aa.BoxRecordError:
            continue
        except Exception as e:  # noqa: BLE001 - a crash is not a refusal
            p.append(f"{key} dropped: {type(e).__name__}")
            continue
        p.append(f"{key} dropped: accepted")
    try:
        aa.harness_records([turn()], pin=PIN, box=dict(BOX, api_error={"status": 500, "type": "x", "text": None}))
        p.append("unknown box key accepted")
    except aa.BoxRecordError:
        pass
    return p


# Box key -> where its value lands in the records.
BOX_LANDS = {"preflight_ok": ("preflight", "ok"), "container_started": ("exit", "container_started"),
             "container_exited": ("exit", "container_exited"), "sidecar": ("sidecar", None),
             "unexplained_operator_diffs": ("operator", "unexplained_diffs"),
             "checker_reasons": ("checker_reasons", None), "quiescence_kill": ("quiescence_kill", None),
             "outside_reach_events": ("events", "outside_reach"), "finalize_abort": ("ledger", "finalize_abort"),
             "committed": ("ledger", "committed"),
             "unreadable_consequential": ("unreadable_consequential", None),
             "quiescence_cap_survivors": ("quiescence_cap_survivors", None)}


def coercion_problems() -> list[str]:
    """Each box key whose None value did not reach the records as None (a coercion would turn
    missing evidence into 'nothing happened')."""
    p = []
    for key, (head, tail) in BOX_LANDS.items():
        rec = aa.harness_records([turn()], pin=PIN, box=dict(BOX, **{key: None}))
        got = rec[head] if tail is None else rec[head][tail]
        if got is not None:
            p.append(f"{key}: None became {got!r}")
    return p


def retyped_turn_ends(source: str) -> list[str]:
    """String constants in a module's code (docstrings excluded) that retype a labels4 turn end."""
    tree = ast.parse(source)
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef)) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and id(n) not in docs
            and n.value in labels4.TURN_ENDS]


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
                    dict(counters={"oom_kill_delta": -1, "pids_max_delta": 0}),
                    dict(counters={"oom_kill_delta": True, "pids_max_delta": 0}),
                    dict(init={"model": "m"}), dict(started_at=3.0, ended_at=2.0),
                    dict(agent_output=None), dict(agent_output=1),
                    dict(api_errors=[{"status": 500}]), dict(api_errors="500"), dict(api_errors=None)):
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
        t1 = turn(api_errors=[], init=dict(PIN, cwd="/host/run"))
        t2 = turn(exit_code=1, end_reason=aa.END_ERROR, api_errors=[{"status": 429, "type": "rate_limit_error",
                                                                   "text": None, "message": "slow down"}],
                  counters={"oom_kill_delta": 1, "pids_max_delta": 0})
        r = aa.harness_records([t1, t2], pin=PIN, box=BOX)
        self.assertEqual(r["ledger"], {"first_turn_started": True, "turns": 2, "end": aa.END_ERROR,
                                       "turn_ends": [aa.END_TURN, aa.END_ERROR], "turn_outputs": [True, True],
                                       "committed": False, "finalize_abort": False})
        self.assertEqual(r["exit"]["exec_codes"], [0, 1])
        self.assertEqual(r["cgroup"], {"oom_kill_delta": 1, "pids_max_delta": 0})
        self.assertEqual(r["api_errors"], [{"status": 429, "type": "rate_limit_error", "text": None}])   # projected
        self.assertEqual(r["init"][0], PIN)                                                  # projected
        empty = aa.harness_records([], pin=PIN, box=BOX)
        self.assertEqual((empty["ledger"]["first_turn_started"], empty["ledger"]["end"], empty["api_errors"]),
                         (False, None, []))


class TestBoxRecords(unittest.TestCase):
    """W1B-2: every box record is required, and a None is carried as None, never coerced."""

    def test_every_box_key_required(self):
        self.assertEqual(box_key_problems(), [])

    def test_box_key_check_can_fail(self):
        with mock.patch.object(aa, "BOX_KEYS", tuple(k for k in aa.BOX_KEYS if k != "outside_reach_events")):
            self.assertIn("outside_reach_events dropped: KeyError", box_key_problems())
        with mock.patch.object(aa, "BOX_KEYS", aa.BOX_KEYS + ("api_error",)):
            self.assertIn("unknown box key accepted", box_key_problems())

    def test_box_lands_covers_every_key(self):
        self.assertEqual(set(BOX_LANDS), set(aa.BOX_KEYS))
        self.assertEqual(set(BOX), set(aa.BOX_KEYS))

    def test_no_coercion(self):
        self.assertEqual(coercion_problems(), [])

    def test_coercion_check_can_fail(self):
        real = aa.harness_records

        def coercing(turns, *, pin, box):   # the pre-fold fold: bool() and int() on the box
            out = real(turns, pin=pin, box=box)
            out["events"]["outside_reach"] = int(box["outside_reach_events"] or 0)
            return out
        with mock.patch.object(aa, "harness_records", coercing):
            self.assertIn("outside_reach_events: None became 0", coercion_problems())


class TestTurns(unittest.TestCase):
    def test_every_api_error_carried_in_order(self):
        """W1B-4: a 500 then a 429 keeps both, so the rate limit still reads as one."""
        t500 = turn(exit_code=1, end_reason=aa.END_ERROR, api_errors=[{"status": 500, "type": "api_error", "text": None}])
        t429 = turn(exit_code=1, end_reason=aa.END_ERROR, api_errors=[{"status": 429, "type": "rate_limit_error", "text": None}])
        r = aa.harness_records([turn(), t500, t429], pin=PIN, box=BOX)
        self.assertEqual([e["status"] for e in r["api_errors"]], [500, 429])

    def test_api_error_check_can_fail(self):
        t500 = turn(exit_code=1, end_reason=aa.END_ERROR, api_errors=[{"status": 500, "type": "api_error", "text": None}])
        t429 = turn(exit_code=1, end_reason=aa.END_ERROR, api_errors=[{"status": 429, "type": "rate_limit_error", "text": None}])
        real = aa.harness_records

        def first_only(turns, *, pin, box):   # the pre-fold fold kept only the first API error
            out = real(turns, pin=pin, box=box)
            out["api_errors"] = out["api_errors"][:1]
            return out
        with mock.patch.object(aa, "harness_records", first_only):
            r = aa.harness_records([turn(), t500, t429], pin=PIN, box=BOX)
        self.assertNotEqual([e["status"] for e in r["api_errors"]], [500, 429])

    def test_every_api_error_of_one_turn_carried_in_order(self):
        """W1B2-7: one turn can meet several API errors (a 529, then a 429); harness_records flattens every
        turn's list in order, so the 429 still reads as a rate limit."""
        e529 = {"status": 529, "type": "overloaded_error", "text": None}
        e429 = {"status": 429, "type": "rate_limit_error", "text": "Rate limit reached"}
        t500 = turn(exit_code=1, end_reason=aa.END_ERROR, api_errors=[{"status": 500, "type": "api_error", "text": None}])
        both = turn(exit_code=1, end_reason=aa.END_ERROR, api_errors=[e529, e429])
        self.assertEqual(api_error_order(aa.harness_records([turn(), t500, both], pin=PIN, box=BOX)), [500, 529, 429])
        real = aa.harness_records

        def first_per_turn(turns, *, pin, box):   # the mutant: the single api_error of before W1B2-7
            out = real(turns, pin=pin, box=box)
            out["api_errors"] = [{f: t.api_errors[0][f] for f in aa.API_ERROR_FIELDS} for t in turns if t.api_errors]
            return out
        with mock.patch.object(aa, "harness_records", first_per_turn):
            self.assertEqual(api_error_order(aa.harness_records([turn(), t500, both], pin=PIN, box=BOX)), [500, 529])

    def test_first_turn_starts_with_agent_output(self):
        """W1B-5 (gap4 lane lead's ruling): a turn with no completed agent output is before it."""
        silent = turn(exit_code=1, end_reason=aa.END_ERROR, agent_output=False,
                      api_errors=[{"status": 500, "type": "api_error", "text": None}])
        r = aa.harness_records([silent], pin=PIN, box=BOX)
        self.assertEqual((r["ledger"]["first_turn_started"], r["ledger"]["turns"], r["ledger"]["turn_outputs"]),
                         (False, 1, [False]))
        r = aa.harness_records([silent, turn()], pin=PIN, box=BOX)
        self.assertTrue(r["ledger"]["first_turn_started"])

    def test_first_turn_check_can_fail(self):
        silent = turn(exit_code=1, end_reason=aa.END_ERROR, agent_output=False)
        real = aa.harness_records

        def any_turn(turns, *, pin, box):   # the pre-fold rule: bool(turns)
            out = real(turns, pin=pin, box=box)
            out["ledger"]["first_turn_started"] = bool(turns)
            return out
        with mock.patch.object(aa, "harness_records", any_turn):
            self.assertTrue(aa.harness_records([silent], pin=PIN, box=BOX)["ledger"]["first_turn_started"])
        with mock.patch.object(aa, "harness_records", any_turn):
            self.assertNotEqual(first_turn_problems(), [])

        def timeout_starts(turns, *, pin, box):   # 3fcab58d's refinement, reverted by W1B2-1
            out = real(turns, pin=pin, box=box)
            out["ledger"]["first_turn_started"] = (any(t.agent_output for t in turns)
                                                   or any(t.end_reason == aa.END_TIMED_OUT for t in turns))
            return out
        with mock.patch.object(aa, "harness_records", timeout_starts):
            self.assertIn("a silent timed-out turn started the agent's first turn", first_turn_problems())

    def test_first_turn_rule(self):
        """W1B2-1: the agent's first turn starts only with completed agent output, a timed-out turn included."""
        self.assertEqual(first_turn_problems(), [])


def api_error_order(records) -> list:
    return [e["status"] for e in records["api_errors"]]


def first_turn_problems() -> list[str]:
    """W1B-5 and W1B2-1 (glitch-f3's correction, 6 Oct 2026): `first_turn_started` is exactly "some turn produced
    completed agent output", whatever the turns' ends."""
    p = []
    silent_error = turn(exit_code=1, end_reason=aa.END_ERROR, agent_output=False)
    silent_timeout = turn(exit_code=124, end_reason=aa.END_TIMED_OUT, agent_output=False)
    output_timeout = turn(exit_code=124, end_reason=aa.END_TIMED_OUT, agent_output=True)
    cases = (([silent_error], False, "a silent error turn"),
             ([silent_timeout], False, "a silent timed-out turn"),
             ([silent_error, silent_timeout], False, "two silent turns"),
             ([output_timeout], True, "a timed-out turn with output"),
             ([turn(), silent_timeout], True, "an output turn, then a silent timeout"),
             ([], False, "no turn"))
    for turns, want, name in cases:
        got = aa.harness_records(turns, pin=PIN, box=BOX)["ledger"]["first_turn_started"]
        if got is not want:
            p.append(f"{name} started the agent's first turn" if got else f"{name} did not start the agent's first turn")
    return p


# W1B2-4: the three harness-side records an adapter could forget, each a required keyword; review round 3 (W1B3-6)
# adds the turn's host clock at its start and end, which defaulted to 0.0 before.
REQUIRED_KW = ("counters", "init", "api_errors", "started_at", "ended_at")


def full_turn_kw(**kw) -> dict:
    """Every TurnResult keyword, explicitly."""
    base = dict(exit_code=0, text=SECRET_TEXT, stream_path=None, end_reason=aa.END_TURN, init=dict(PIN),
                api_errors=[], counters={"oom_kill_delta": 0, "pids_max_delta": 0}, started_at=1.0, ended_at=2.0,
                agent_output=True)
    base.update(kw)
    return base


def omission_problems() -> list[str]:
    """Each required keyword whose omission did NOT raise a TypeError naming it (W1B2-4: an adapter that omits
    counters would make an out-of-memory kill route harness-error, a re-run, instead of aborted)."""
    p = []
    for name in REQUIRED_KW:
        kw = full_turn_kw()
        del kw[name]
        try:
            aa.TurnResult(**kw)
        except TypeError as e:
            if f"`{name}` is a required keyword" not in str(e):
                p.append(f"{name} omitted: TypeError for another reason ({e})")
            continue
        except Exception as e:  # noqa: BLE001
            p.append(f"{name} omitted: {type(e).__name__} ({e})")
            continue
        p.append(f"{name} omitted: accepted")
    return p


class TestRequiredKeywords(unittest.TestCase):
    """W1B2-4: counters, init and api_errors are required keywords; None stays a legal explicit init. W1B3-6:
    started_at and ended_at are required keywords too."""

    def test_omission_raises(self):
        self.assertEqual(omission_problems(), [])

    def test_explicit_values(self):
        self.assertIsNone(aa.TurnResult(**full_turn_kw(init=None)).init)
        self.assertEqual(aa.TurnResult(**full_turn_kw(api_errors=[])).api_errors, [])
        for bad in (dict(api_errors=None), dict(counters=None), dict(api_errors={"status": 500}),
                    dict(api_errors=[{"status": 500, "type": "x"}]), dict(api_errors=["500"]),
                    # W1B3-6: the host clock is a number of seconds, never None, a string or a bool
                    dict(started_at=None), dict(ended_at=None), dict(started_at="1.0"), dict(ended_at=True)):
            with self.assertRaises(ValueError, msg=str(bad)):
                aa.TurnResult(**full_turn_kw(**bad))

    def test_omission_check_can_fail(self):
        real_init = aa.TurnResult.__init__

        def defaulting(self, *args, **kw):   # the pre-fold dataclass: counters defaulted to no rise
            kw.setdefault("counters", {"oom_kill_delta": 0, "pids_max_delta": 0})
            real_init(self, *args, **kw)
        with mock.patch.object(aa.TurnResult, "__init__", defaulting):
            self.assertIn("counters omitted: accepted", omission_problems())

        def clock_defaulted(self, *args, **kw):   # W1B3-6's mutant: the pre-fold-4 dataclass, the clock defaulted to 0.0
            kw.setdefault("started_at", 0.0)
            kw.setdefault("ended_at", 0.0)
            real_init(self, *args, **kw)
        with mock.patch.object(aa.TurnResult, "__init__", clock_defaulted):
            found = omission_problems()
        for name in ("started_at", "ended_at"):   # accepted, or refused for another reason: never the required keyword
            self.assertTrue(any(x.startswith(f"{name} omitted:") for x in found), (name, found))

    def test_clock_type_check_can_fail(self):
        """W1B3-6: with the clock's type check gone, None, a string or a bool is taken for the host clock."""
        with mock.patch.object(aa, "_clock", lambda v: True):
            accepted = []
            for bad in (dict(started_at=None), dict(ended_at=None), dict(started_at="1.0"), dict(ended_at=True)):
                try:
                    aa.TurnResult(**full_turn_kw(**bad))
                    accepted.append(bad)
                except ValueError:
                    pass
                except TypeError:   # None or a string compared with a number: a crash, not the refusal
                    accepted.append(bad)
        self.assertEqual(len(accepted), 4, accepted)


API_ERROR_FIELDS_WANT = ("status", "type", "text")   # glitch-f3's ruling, typed once here
USAGE = {"status": None, "type": None, "text": "Claude usage limit reached; resets at 9pm"}
E500_TEXT = {"status": 500, "type": "api_error", "text": "internal server error"}
AGENT_SAYS = ("rate limit", "429", "usage limit", SECRET_TEXT)


def agent_text_problems() -> list[str]:
    """The agent printing the markers (its TurnResult.text) beside a 500 whose own error text names none: the
    record's error text stays the harness's, and the agent's text reaches no record."""
    p = []
    for said in AGENT_SAYS:
        erred = turn(text=said, exit_code=1, end_reason=aa.END_ERROR, api_errors=[dict(E500_TEXT)])
        for turns in ([erred], [turn(text=said), erred]):
            r = aa.harness_records(turns, pin=PIN, box=BOX)
            if r["api_errors"] != [E500_TEXT]:
                p.append(f"{said!r} ({len(turns)} turns): api_errors {r['api_errors']}")
            if said == SECRET_TEXT and text_leaks(r):
                p.append(f"the agent's text leaked into the records ({len(turns)} turns)")
    return p


class TestApiErrorText(unittest.TestCase):
    """glitch-f3's ruling (in-plan, 6 Oct 2026; glitch-f3's, not the owner's): the API-error record carries a third
    required field, `text`, the harness-side error text (what Claude Code or the API reported as the error), never
    the agent's reply, so routing can match round 3's text markers on it."""

    def test_fields(self):
        self.assertEqual(aa.API_ERROR_FIELDS, API_ERROR_FIELDS_WANT)

    def test_text_is_required(self):
        with self.assertRaises(ValueError):
            turn(api_errors=[{"status": 500, "type": "api_error"}])
        for text in (None, "internal server error"):
            self.assertEqual(turn(api_errors=[dict(E500_TEXT, text=text)]).api_errors[0]["text"], text)

    def test_text_projected(self):
        silent = turn(exit_code=1, end_reason=aa.END_ERROR, agent_output=False, api_errors=[dict(USAGE, message="extra")])
        r = aa.harness_records([silent], pin=PIN, box=BOX)
        self.assertEqual(r["api_errors"], [USAGE])

    def test_agent_text_never_becomes_the_error_text(self):
        self.assertEqual(agent_text_problems(), [])

    def test_agent_text_check_can_fail(self):
        real = aa.harness_records

        def agent_text_in(turns, *, pin, box):   # the mutant: the agent's reply routed into the error text
            out = real(turns, pin=pin, box=box)
            erred = [t for t in turns for _ in t.api_errors]
            out["api_errors"] = [dict(e, text=t.text) for e, t in zip(out["api_errors"], erred)]
            return out
        with mock.patch.object(aa, "harness_records", agent_text_in):
            problems = agent_text_problems()
        self.assertTrue(any("leaked" in x for x in problems), problems)
        self.assertTrue(any("'rate limit'" in x for x in problems), problems)


class TestVocabulary(unittest.TestCase):
    """W1B-7: the turn ends are labels4's, imported and never retyped."""

    def test_turn_ends_are_labels4s(self):
        self.assertIs(aa.END_TIMED_OUT, labels4.TIMED_OUT)
        self.assertEqual(aa.END_REASONS, labels4.TURN_ENDS)
        with open(os.path.join(_ROOT, "agent_adapter.py"), encoding="utf-8") as fh:
            self.assertEqual(retyped_turn_ends(fh.read()), [])

    def test_retyping_check_can_fail(self):
        self.assertEqual(retyped_turn_ends('END_TIMED_OUT = "timed-out"'), ["timed-out"])
        self.assertEqual(retyped_turn_ends('"""end_turn in a docstring is prose"""\nx = 1'), [])



# ---------------------------------------------------------------- w1b's next touch (lane w4h-w1b-next-touch)
NAN, INF = float("nan"), float("inf")
# W1B4-4 (w1b's next-touch list, item 2): the host clock must be a finite number of seconds.
NON_FINITE = {"started_at=nan": dict(started_at=NAN), "started_at=inf": dict(started_at=INF, ended_at=INF),
              "started_at=-inf": dict(started_at=-INF), "ended_at=nan": dict(ended_at=NAN),
              "ended_at=inf": dict(ended_at=INF), "ended_at=-inf": dict(started_at=-INF, ended_at=-INF),
              # a NaN start compares False with every end, so it used to pass the start-before-end check
              "a NaN start before a finite end": dict(started_at=NAN, ended_at=2.0),
              "a NaN end after a finite start": dict(started_at=1.0, ended_at=NAN)}


def clock_problems() -> list[str]:
    """Each non-finite host clock TurnResult did NOT refuse with ValueError (W1B4-4)."""
    p = []
    for name, bad in NON_FINITE.items():
        try:
            aa.TurnResult(**full_turn_kw(**bad))
        except ValueError:
            continue
        except Exception as e:  # noqa: BLE001 - a crash is not the refusal
            p.append(f"{name}: {type(e).__name__} ({e})")
            continue
        p.append(f"{name}: accepted")
    return p


class TestNextTouchClock(unittest.TestCase):
    """W1B4-4: `_clock` also requires `math.isfinite`; NaN and both infinities are refused for started_at and
    ended_at, and a NaN start can no longer pass the start-before-end check."""

    def test_non_finite_clocks_refused(self):
        self.assertEqual(clock_problems(), [])

    def test_finite_clocks_still_accepted(self):
        for ok in (dict(started_at=0, ended_at=0), dict(started_at=1.0, ended_at=1.5), dict(started_at=1, ended_at=2)):
            self.assertEqual(aa.TurnResult(**full_turn_kw(**ok)).ended_at, ok["ended_at"])

    def test_clock_finite_check_can_fail(self):
        """The mutant: `_clock` without `math.isfinite` (the base's clause) lets every non-finite clock through."""
        def no_isfinite(v):
            return isinstance(v, (int, float)) and not isinstance(v, bool)
        with mock.patch.object(aa, "_clock", no_isfinite):
            found = clock_problems()
        self.assertEqual(found, [f"{name}: accepted" for name in NON_FINITE])



# CP2 ruling C3 (glitch-f3, 17:35; names fixed at 17:42): two more box keys, copied as given (never coerced).
C3_BOX = {"unreadable_consequential": ["data/staging/samples.csv"], "quiescence_cap_survivors": 2}


class TestNextTouchC3Box(unittest.TestCase):
    def test_the_c3_keys_are_box_keys_copied_as_given(self):
        self.assertEqual(aa.BOX_KEYS[-2:], ("unreadable_consequential", "quiescence_cap_survivors"))
        box = dict(BOX, **C3_BOX)
        r = aa.harness_records([turn()], pin=PIN, box=box)
        self.assertEqual(r["unreadable_consequential"], C3_BOX["unreadable_consequential"])
        self.assertIsNot(r["unreadable_consequential"], box["unreadable_consequential"])   # a copy of the list
        self.assertEqual(r["quiescence_cap_survivors"], 2)
        for key in C3_BOX:
            for bad in (None, "x", True):
                self.assertEqual(aa.harness_records([turn()], pin=PIN, box=dict(box, **{key: bad}))[key], bad)
            b = dict(box)
            del b[key]
            with self.assertRaises(aa.BoxRecordError):
                aa.harness_records([turn()], pin=PIN, box=b)


if __name__ == "__main__":
    unittest.main()
