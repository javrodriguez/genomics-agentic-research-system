#!/usr/bin/env python3
"""routing.py and routing.json: every row, every annotation, every overlap the plan names, every
record key, every pin profile, and every mutation goes red.

Five kinds of check, combined in `all_problems(table)`:

1. THE DERIVED GRID. For every row of routing.json and every one of its `any_of` alternatives, a
   witness record is built from the row's own conditions on a clean baseline of the row's phase,
   and must route to the row's route with the row among the winners; on the other phase's
   baseline the row must not match. Then every row's witness is crossed with every terminal state
   (end_turn, timeout, API error, container failure, cgroup kill, init mismatch, rate limit, a
   usage limit carried only in the error text), and
   the route must be the higher-precedence of the two routes each produces alone. Rows, routes,
   precedence and phases all come from routing.json and labels4.py; nothing here retypes them.

2. THE ANNOTATION GRID. Every annotation's witness is crossed with both phases and every terminal
   state, including records routing refuses: its event and mask must be reported every time,
   whatever route wins or whether one does (W1B-1).

3. THE SEAM. Every before-first-turn row's witness is built through `agent_adapter.harness_records`
   (from turn results and box records, as the driver will), with no turn, with one turn that
   produced no agent output and ended in error, and with one that produced none and timed out, and
   must route to the row (W1B-5; review round 2, W1B2-1).

4. THE PLAN'S ORACLE. A derived grid cannot catch a mutated table (a row whose route is changed
   still routes its own witness to the new route), so the plan's table is also stated here once,
   as scenarios typed from the plan's own words, each with the route, winning rows, events and
   mask it must get.

5. THE MUTATION SWEEP. Every row is mutated (its route, its phase, each condition mutated or
   deleted, each condition group deleted, its removal), every annotation (its removal, its event
   and mask flags, each condition, its condition group), the rate-limit markers, the graded ends,
   the pin fields and the precedence (every adjacent swap, merged levels), in memory, and
   `all_problems` must be non-empty for every mutation.

6. THE ERROR TEXT (glitch-f3's ruling, 6 Oct 2026). Round 3's four text markers match an API error's
   harness-side `text`, word-bounded and case-insensitive, and never the agent's own reply: the
   markers and the match are re-derived from round 3's drive.py at its done commit (TestRound3Sources),
   probed on both bounds and on case, and driven through harness_records (TestRateLimitText).

The table under test is the real routing.json with two test-only pin profiles (`TEST_PROFILES`)
injected in memory, because CP5's pins are not yet in it (pin_profiles_status); the real table's
refusal while they are pending is tested on its own. Round 3's operator-side reasons are the real,
filled list (Javier's ruling "gap4 routing: A").
"""

from __future__ import annotations

import __future__
import ast
import collections
import copy
import json
import os
import re
import subprocess
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_adapter as aa  # noqa: E402  (the seam only; routing.py never imports it)
import routing  # noqa: E402
from graders import labels4  # noqa: E402

REAL = routing.load_table()
# Round 3's reason ids the scenarios name, typed once (TestRound3Sources binds the list they come from).
READERS = "readers-disagree"          # an operator-side reason of either phase
NFAT = "no-first-agent-turn"          # round 3's "before the agent's first turn" reason
# Test-only pin profiles, injected in memory (CP5 pre-registers the real ones).
TEST_PROFILES = {
    "test-model-a": {"permission_mode": "bypassPermissions", "version": "0.0.1-test"},
    "test-model-b": {"permission_mode": "plan-test", "version": "0.0.2-test"},
}
PIN = dict(TEST_PROFILES["test-model-a"], model="test-model-a")


def test_table() -> dict:
    t = copy.deepcopy(REAL)
    t["pin_profiles"] = copy.deepcopy(TEST_PROFILES)
    t["pin_profiles_status"] = "TEST-ONLY: two injected profiles"
    return t


# ---------------------------------------------------------------------------------------- records
def baseline(phase: str, pin: dict | None = None) -> dict:
    pin = dict(pin or PIN)
    after = phase == labels4.AFTER_FIRST_TURN
    n = 2 if after else 0
    return {
        "ledger": {"first_turn_started": after, "turns": n, "end": labels4.END_TURN if after else None,
                   "turn_ends": [labels4.END_TURN] * n, "turn_outputs": [True] * n, "committed": False,
                   "finalize_abort": False},
        "exit": {"container_started": True, "container_exited": False, "exec_codes": [0] * n},
        "cgroup": {"oom_kill_delta": 0, "pids_max_delta": 0},
        "init": [dict(pin) for _ in range(n)],
        "pin": dict(pin),
        "api_errors": [],
        "sidecar": {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False},
        "preflight": {"ok": True},
        "operator": {"unexplained_diffs": 0},
        "checker_reasons": [],
        "quiescence_kill": False,
        "events": {"outside_reach": 0},
    }


def set_end(rec: dict, end: str, code: int | None = None):
    rec["ledger"]["end"] = end
    rec["ledger"]["turn_ends"][-1] = end
    if code is not None:
        rec["exit"]["exec_codes"][-1] = code


def silent_turn(rec: dict, end: str = labels4.END_ERROR, code: int = 1):
    """Append a turn that produced no agent output and ended in error (W1B-5's 'before the first turn')."""
    led = rec["ledger"]
    led["turns"] += 1
    led["turn_ends"].append(end)
    led["turn_outputs"].append(False)
    led["end"] = end
    rec["exit"]["exec_codes"].append(code)
    rec["init"].append(dict(rec["pin"]))


def silent_timeout(rec: dict):
    """Append a turn that produced no completed agent output and timed out, the host's kill exiting 124
    (W1B2-1: before the agent's first turn, glitch-f3's correction)."""
    silent_turn(rec, labels4.TIMED_OUT, 124)


def output_timeout(rec: dict):
    """Append a turn that produced completed agent output (a tool call, say) and then timed out."""
    silent_turn(rec, labels4.TIMED_OUT, 124)
    rec["ledger"]["turn_outputs"][-1] = True
    rec["ledger"]["first_turn_started"] = True


def ensure_turn(rec: dict):
    if rec["ledger"]["turns"] == 0:
        silent_turn(rec)


def set_api(rec: dict, errors: list):
    ensure_turn(rec)
    rec["api_errors"] = [dict(e) for e in errors]


def set_path(rec: dict, path: str, value):
    head, _, tail = path.partition(".")
    if path == "ledger.end":
        ensure_turn(rec)          # an end needs a turn: before the first turn, a silent one
        set_end(rec, value)
    elif tail:
        rec[head][tail] = value
    else:
        rec[head] = value


class NoWitness(IndexError):
    """No record can make this condition hold (a mutated condition, say)."""


def apply_witness(rec: dict, cond: dict, table: dict) -> set:
    """Make `cond` hold on `rec`; return the record paths it touched."""
    op, path = cond["op"], cond["path"]
    if path.startswith("api_errors.") and op != "in_rate_limit_markers":
        raise NoWitness(f"{op} on {path}, a per-error list, has no witness")
    if op == "eq":
        set_path(rec, path, cond["value"])
    elif op == "ne":
        set_path(rec, path, cond["value"] + 1 if isinstance(cond["value"], int) else "__other__")
    elif op == "gt":
        set_path(rec, path, cond["value"] + 1)
    elif op == "truthy":
        set_path(rec, path, True)
    elif op == "falsy":
        set_path(rec, path, False)
    elif op == "nonempty" and path == "api_errors":
        set_api(rec, [{"status": 500, "type": "api_error", "text": None}])
    elif op == "empty" and path == "api_errors":
        rec["api_errors"] = []
    elif op == "in_operator_reasons":
        set_path(rec, path, [table["operator_reasons"][0]])
    elif op == "in_checker_events":
        set_path(rec, path, [table["checker_reasons_become_events"]["ids"][0]])
    elif op == "in_rate_limit_markers":
        key = path.partition(".")[2]
        err = {"status": None, "type": None, "text": None}
        err[key] = table["rate_limit_markers"][key][0]
        set_api(rec, [err])
    elif op == "differs_from_pin":
        rec["init"][0] = dict(rec["pin"], model="not-the-pin")
    elif op == "nonzero_outside_timeout":
        rec["exit"]["exec_codes"][0] = 1
    elif op in ("not_null", "is_null"):
        set_path(rec, path, {"x": 1} if op == "not_null" else None)
    else:
        raise AssertionError(f"no witness for op {op}")
    return {"ledger.end"} if path == "ledger.end" else {path.partition(".")[0]}


def row_phases(row: dict) -> list[str]:
    return [labels4.BEFORE_FIRST_TURN, labels4.AFTER_FIRST_TURN] if row["when"] == labels4.ANY_TIME else [row["when"]]


def witness(row: dict, alt: int, phase: str, table: dict) -> tuple[dict, set]:
    rec = baseline(phase)
    touched = set()
    for c in row.get("all_of", []) + [row["any_of"][alt]]:
        touched |= apply_witness(rec, c, table)
    return rec, touched


def try_route(rec: dict, table: dict):
    try:
        return routing.route(rec, table)
    except routing.RoutingRefused as e:
        return e


def try_annotate(rec: dict, table: dict):
    try:
        return routing.annotate(rec, table)
    except routing.RoutingRefused as e:
        return e


# ------------------------------------------------------------------------- 1. the derived grid
# The plan's terminal states, as record edits on the LAST turn (witnesses edit the first), with
# the paths each touches. Their routes are never typed: each is routed alone below.
def _timeout(r):
    set_end(r, labels4.TIMED_OUT, 137)


def _api(r):
    set_api(r, [{"status": 500, "type": "api_error", "text": None}])


def _container(r):
    r["exit"]["container_exited"] = True


def _cgroup(r):
    r["cgroup"]["oom_kill_delta"] = 1
    r["exit"]["exec_codes"][-1] = 137


def _mismatch(r):
    r["init"][-1] = dict(r["pin"], version="not-the-pin")


def _rate(r):
    set_api(r, [{"status": 429, "type": "rate_limit_error", "text": None}])


def _usage_text(r):
    """glitch-f3's ruling: a usage-limit refusal carrying only its harness-side error text."""
    set_api(r, [{"status": None, "type": None, "text": "Claude usage limit reached; resets at 9pm"}])


TERMINAL_STATES = {
    "end_turn": (lambda r: None, set()),
    "timeout": (_timeout, {"ledger.end", "exit"}),
    "api-error": (_api, {"api_errors"}),
    "container-failure": (_container, {"exit"}),
    "cgroup-kill": (_cgroup, {"cgroup", "exit"}),
    "mismatch": (_mismatch, {"init"}),
    "rate-limit": (_rate, {"api_errors"}),
    "usage-limit-text": (_usage_text, {"api_errors"}),
}


def higher(a: str, b: str, table: dict):
    level = {r: i for i, lvl in enumerate(table["precedence"]) for r in lvl}
    if level[a] == level[b]:
        return a if a == b else None  # a tie: must be refused
    return a if level[a] < level[b] else b


def row_problems(row: dict, table: dict) -> list[str]:
    p = []
    for phase in row_phases(row):
        for alt in range(len(row["any_of"])):
            try:
                rec, _ = witness(row, alt, phase, table)
            except IndexError:  # a per-turn condition on a phase with no turns
                p.append(f"{row['id']}[{alt}] {phase}: no record of this phase can match it")
                continue
            got = try_route(rec, table)
            if isinstance(got, Exception):
                p.append(f"{row['id']}[{alt}] {phase}: refused ({got})")
            elif got["route"] != row["route"] or row["id"] not in got["rows"]:
                p.append(f"{row['id']}[{alt}] {phase}: got {got['route']} via {got['rows']}")
    for phase in set(labels4.PHASES) - {labels4.ANY_TIME} - set(row_phases(row)):
        try:
            rec, _ = witness(row, 0, phase, table)
        except IndexError:  # a per-turn condition cannot hold where no turn ran
            continue
        if routing.matches(row, rec, table):
            p.append(f"{row['id']}: matches outside its phase ({phase})")
    return p


def grid_problems(table: dict) -> list[str]:
    p = []
    for row in table["rows"]:
        if labels4.AFTER_FIRST_TURN not in row_phases(row):
            continue
        rec0, touched = witness(row, 0, labels4.AFTER_FIRST_TURN, table)
        alone = try_route(rec0, table)
        if isinstance(alone, Exception):
            continue  # reported by row_problems
        for name, (edit, paths) in TERMINAL_STATES.items():
            if touched & paths:
                continue  # the witness and the terminal state edit the same record
            mod = baseline(labels4.AFTER_FIRST_TURN)
            edit(mod)
            mod_route = try_route(mod, table)
            rec, _ = witness(row, 0, labels4.AFTER_FIRST_TURN, table)
            edit(rec)
            got = try_route(rec, table)
            if isinstance(mod_route, Exception):
                if not isinstance(got, Exception) and got["route"] != alone["route"]:
                    p.append(f"grid {row['id']} x {name}: {got['route']}")
                continue
            want = higher(alone["route"], mod_route["route"], table)
            if want is None:
                if not isinstance(got, Exception):
                    p.append(f"grid {row['id']} x {name}: tie not refused")
            elif isinstance(got, Exception) or got["route"] != want:
                p.append(f"grid {row['id']} x {name}: want {want}, got {got}")
    return p


# --------------------------------------------------------------------- 2. the annotation grid
def _refusals():
    """Record edits that make routing refuse while the records stay well-formed."""
    def ended_in_error(r):
        set_end(r, labels4.END_ERROR, 0)

    def committed(r):
        r["ledger"]["committed"] = True

    def unlisted(r):
        r["checker_reasons"] = ["unlisted-reason"]
    return {"ended-in-error": ended_in_error, "committed": committed, "unlisted-reason": unlisted}


def annotation_grid_problems(table: dict) -> list[str]:
    """Every annotation is reported, with its flags, on every take: both phases, every terminal
    state, and records routing refuses."""
    p = []
    for a in table["annotations"]:
        for alt, cond in enumerate(a["any_of"]):
            cases = [("before-first-turn", labels4.BEFORE_FIRST_TURN, lambda r: None)]
            cases += [(n, labels4.AFTER_FIRST_TURN, e) for n, (e, _) in TERMINAL_STATES.items()]
            cases += [(n, labels4.AFTER_FIRST_TURN, e) for n, e in _refusals().items()]
            for name, phase, edit in cases:
                rec = baseline(phase)
                edit(rec)
                apply_witness(rec, cond, table)
                got = try_annotate(rec, table)
                routed = try_route(rec, table)
                for where, res in (("annotate", got), ("route", routed)):
                    if isinstance(res, Exception):
                        if where == "annotate":
                            p.append(f"annotation {a['id']}[{alt}] x {name}: annotate refused ({res})")
                        continue
                    if a["event"] != (a["id"] in res["events"]):
                        p.append(f"annotation {a['id']}[{alt}] x {name}: {where} events {res['events']}")
                    if a["mask"] and not res["mask"]:
                        p.append(f"annotation {a['id']}[{alt}] x {name}: {where} lost the mask")
    return p


# ------------------------------------------------------------------------------------ 3. the seam
SIDECAR = {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False}


def full_box(**kw) -> dict:
    b = {"preflight_ok": True, "container_started": True, "container_exited": False, "sidecar": dict(SIDECAR),
         "unexplained_operator_diffs": 0, "checker_reasons": [], "quiescence_kill": False,
         "outside_reach_events": 0, "finalize_abort": False, "committed": False}
    b.update(kw)
    return b


def a_turn(**kw) -> aa.TurnResult:
    base = dict(exit_code=0, text="(scripted)", stream_path=None, end_reason=labels4.END_TURN, init=dict(PIN),
                api_errors=[], counters={"oom_kill_delta": 0, "pids_max_delta": 0}, agent_output=True)
    base.update(kw)
    return aa.TurnResult(**base)


def a_silent_turn(**kw) -> aa.TurnResult:
    return a_turn(exit_code=1, end_reason=labels4.END_ERROR, agent_output=False, **kw)


def a_silent_timeout(**kw) -> aa.TurnResult:
    """A turn that produced no completed agent output and timed out (the host's kill exits 124)."""
    return a_turn(exit_code=124, end_reason=labels4.TIMED_OUT, agent_output=False, **kw)


SILENT_TIMEOUT_ROW = "silent-timeout-before-first-turn"


def silent_timeout_problems(table: dict) -> list[str]:
    """W1B2-1 with glitch-f3's correction (6 Oct 2026, relayed by the gap4 lane lead; glitch-f3's, not the
    owner's): a bare silent first-turn timeout is before the agent's first turn and routes rehearsal on its own
    row; a timeout after completed agent output (a turn with output, then a timed-out one, or one turn with
    output that timed out) is the agent's and grades timed-out. Built through harness_records, as the driver
    will."""
    p = []
    cases = (
        ("a bare silent first-turn timeout", [a_silent_timeout()], labels4.REHEARSAL, [SILENT_TIMEOUT_ROW],
         labels4.BEFORE_FIRST_TURN),
        ("a turn with output, then a silent timeout", [a_turn(), a_silent_timeout()], labels4.GRADED, ["timed-out"],
         labels4.AFTER_FIRST_TURN),
        ("one turn with output that timed out", [a_turn(exit_code=124, end_reason=labels4.TIMED_OUT)], labels4.GRADED,
         ["timed-out"], labels4.AFTER_FIRST_TURN),
    )
    for name, turns, route, rows, phase in cases:
        got = try_route(aa.harness_records(turns, pin=PIN, box=full_box()), table)
        if isinstance(got, Exception):
            p.append(f"{name}: refused ({got})")
        elif (got["route"], got["rows"], got["phase"]) != (route, rows, phase):
            p.append(f"{name}: want {route} via {rows} ({phase}), got {got['route']} via {got['rows']} ({got['phase']})")
    return p


class TestSilentTimeout(unittest.TestCase):
    """The plan: "A timeout stays the agent's". glitch-f3's correction (6 Oct 2026, relayed by the gap4 lane lead;
    glitch-f3's, not the owner's): it applies once the agent has produced completed output. A silent first-turn
    timeout cannot be told from a hung API, CLI or egress, so it is a rehearsal (W1B2-1)."""

    def test_silent_timeout_both_ways(self):
        self.assertEqual(silent_timeout_problems(test_table()), [])

    def test_silent_timeout_check_can_fail(self):
        real = aa.harness_records

        def timeout_starts(turns, *, pin, box):   # 3fcab58d's rule: any timed-out turn starts the agent's turn
            out = real(turns, pin=pin, box=box)
            timed = [t.end_reason == labels4.TIMED_OUT for t in turns]
            out["ledger"]["turn_outputs"] = [o or x for o, x in zip(out["ledger"]["turn_outputs"], timed)]
            out["ledger"]["first_turn_started"] = any(out["ledger"]["turn_outputs"])
            return out

        def timeout_never_output(turns, *, pin, box):   # a timed-out turn's output is never read
            out = real(turns, pin=pin, box=box)
            timed = [t.end_reason == labels4.TIMED_OUT for t in turns]
            out["ledger"]["turn_outputs"] = [o and not x for o, x in zip(out["ledger"]["turn_outputs"], timed)]
            out["ledger"]["first_turn_started"] = any(out["ledger"]["turn_outputs"])
            return out
        with mock.patch.object(aa, "harness_records", timeout_starts):
            self.assertTrue(any(x.startswith("a bare silent") for x in silent_timeout_problems(test_table())))
        with mock.patch.object(aa, "harness_records", timeout_never_output):
            self.assertTrue(any(x.startswith("one turn with output") for x in silent_timeout_problems(test_table())))
        t = test_table()
        next(r for r in t["rows"] if r["id"] == SILENT_TIMEOUT_ROW)["when"] = labels4.ANY_TIME
        self.assertTrue(any(x.startswith("a turn with output") for x in silent_timeout_problems(t)))
        t = test_table()
        next(r for r in t["rows"] if r["id"] == SILENT_TIMEOUT_ROW)["route"] = labels4.GRADED
        self.assertTrue(any(x.startswith("a bare silent") for x in silent_timeout_problems(t)))


SEAM_VARIANTS = {   # how the seam's one silent turn ended (W1B-5; W1B2-1)
    "no turn": None,
    "a silent turn": labels4.END_ERROR,
    "a silent timed-out turn": labels4.TIMED_OUT,
}


def _silent(end: str | None, **kw) -> aa.TurnResult:
    return a_silent_timeout(**kw) if end == labels4.TIMED_OUT else a_silent_turn(**kw)


def _seam_edit(cond: dict, table: dict, turns: list, box: dict, end: str | None = None) -> bool:
    """Make `cond` hold through the adapter's inputs; False when no seam witness is known. A witness
    that needs a turn uses a silent turn that ended as `end` (error when the variant has no turn)."""
    path, op = cond["path"], cond["op"]
    head, _, tail = path.partition(".")
    if path == "api_errors" and op == "nonempty":
        turns[:] = [_silent(end, api_errors=[{"status": 500, "type": "api_error", "text": None}])]
    elif head == "api_errors" and op == "in_rate_limit_markers":
        err = {"status": None, "type": None, "text": None}
        err[tail] = table["rate_limit_markers"][tail][0]
        turns[:] = [_silent(end, api_errors=[err])]
    elif path == "ledger.end" and op == "eq" and cond["value"] in (labels4.TIMED_OUT, labels4.END_ERROR):
        turns[:] = [_silent(cond["value"])]
    elif path == "preflight.ok" and op == "falsy":
        box["preflight_ok"] = False
    elif path == "exit.container_started" and op == "falsy":
        box["container_started"] = False
    elif path == "exit.container_exited" and op == "truthy":
        box["container_exited"] = True
    elif head == "sidecar" and op in ("falsy", "truthy", "ne"):
        box["sidecar"] = dict(box["sidecar"], **{tail: {"falsy": False, "truthy": True}.get(op, (cond.get("value") or 0) + 1)})
    elif path == "checker_reasons" and op == "in_operator_reasons":
        box["checker_reasons"] = [table["operator_reasons"][0]]
    elif path == "operator.unexplained_diffs" and op == "gt":
        box["unexplained_operator_diffs"] = cond["value"] + 1
    elif path == "ledger.finalize_abort" and op == "truthy":
        box["finalize_abort"] = True
    else:
        return False
    return True


def seam_problems(table: dict) -> list[str]:
    """Every before-first-turn row's witness, built through harness_records, routes to the row:
    with no turn, and (except a preflight failure, which cannot have run a turn) with one turn
    that produced no agent output and ended in error, and with one that produced none and timed
    out (W1B2-1: a silent timeout is before the agent's first turn too)."""
    p = []
    for row in table["rows"]:
        if labels4.BEFORE_FIRST_TURN not in row_phases(row):
            continue
        for alt, cond in enumerate(row["any_of"]):
            for variant, end in SEAM_VARIANTS.items():
                turns, box = ([] if end is None else [_silent(end)]), full_box()
                if not all(_seam_edit(c, table, turns, box, end) for c in row.get("all_of", []) + [cond]):
                    p.append(f"seam {row['id']}[{alt}]: no seam witness for {cond}")
                    break
                if turns and box["preflight_ok"] is False:
                    continue
                rec = aa.harness_records(turns, pin=PIN, box=box)
                got = try_route(rec, table)
                if isinstance(got, Exception):
                    p.append(f"seam {row['id']}[{alt}] {variant}: refused ({got})")
                elif got["route"] != row["route"] or row["id"] not in got["rows"] or got["phase"] != labels4.BEFORE_FIRST_TURN:
                    p.append(f"seam {row['id']}[{alt}] {variant}: got {got['route']} via {got['rows']} ({got['phase']})")
    return p


# ---------------------------------------------------------------------- 4. the plan's oracle
B, A = labels4.BEFORE_FIRST_TURN, labels4.AFTER_FIRST_TURN
OR, QK = "outside-reach", "quiescence-kill"


def _sc(phase, edits):
    def build():
        r = baseline(phase)
        for e in edits:
            e(r)
        return r
    return build


def _set(path, value):
    return lambda r: set_path(r, path, value)


def _apis(*errors):
    return lambda r: set_api(r, list(errors))


def _multi_turn(n):
    def f(r):
        r["ledger"].update(turns=n, turn_ends=[labels4.END_TURN] * n, turn_outputs=[True] * n)
        r["exit"]["exec_codes"] = [0] * n
        r["init"] = [dict(r["pin"]) for _ in range(n)]
    return f


def _reach(n=1):
    return _set("events.outside_reach", n)


_end_error = (lambda code: (lambda r: set_end(r, labels4.END_ERROR, code)))
E500 = {"status": 500, "type": "api_error", "text": None}
E429 = {"status": 429, "type": "rate_limit_error", "text": None}
E529 = {"status": 529, "type": "overloaded_error", "text": None}   # the API overloaded: no rate-limit marker
EVENT_IDS = tuple(REAL["checker_reasons_become_events"]["ids"])
CE = "checker-event-reason"   # W1B2-2's annotation

# glitch-f3's ruling (in-plan, 6 Oct 2026; glitch-f3's, not the owner's): "Keep both: structured (status 429,
# type rate_limit_error) OR round 3's four text markers ('rate limit', 'usage limit', 'weekly limit', '429'),
# word-bounded and case-insensitive, matched on the harness-side error text only, never on the agent's own
# output. Make the small schema change so the API-error record carries that text."
API_ERROR_FIELDS_WANT = ("status", "type", "text")   # the ruling's record, typed once here


def _err(text, status=None, type_=None) -> dict:
    """An API-error record whose harness-side error text is `text`."""
    return {"status": status, "type": type_, "text": text}


USAGE_TEXT = "Claude usage limit reached; resets at 9pm"
EUSAGE = _err(USAGE_TEXT)                                   # a subscription usage-limit refusal: text only
E500_TEXT = _err("internal server error", 500, "api_error")  # an API error that carries no marker

REFUSED = "refused"
# route: the expected route, or REFUSED. rows: the winning row ids. matched: every matched row id,
# where an overlap's lower rows matter. events, mask: the annotations; events=None means the
# records are malformed, so annotate() must refuse them too.
Sc = collections.namedtuple("Sc", "build route rows matched events mask", defaults=(None, (), False))

# Each is typed from the plan's routing table, its precedence paragraph, its testing strategy, or
# a review-round-1 finding (named).
SCENARIOS = {
    # before the agent's first turn -> rehearsal
    "preflight failure": Sc(_sc(B, [_set("preflight.ok", False)]), "rehearsal", ["preflight-failed"]),
    "container start failure": Sc(_sc(B, [_set("exit.container_started", False)]), "rehearsal", ["container-start-failed"]),
    "container died before first turn": Sc(_sc(B, [_set("exit.container_exited", True)]), "rehearsal", ["container-start-failed"]),
    "container died during a turn with no agent output": Sc(_sc(B, [silent_turn, _set("exit.container_exited", True)]), "rehearsal", ["container-start-failed"]),
    "API error before the agent's first output (W1B-5 ruling)": Sc(_sc(B, [_apis(E500)]), "rehearsal", ["api-error-before-first-turn"]),
    "API error in the first turn after agent output": Sc(_sc(A, [_multi_turn(1), _apis(E500), _end_error(1)]), "harness-error", ["api-error-after-first-turn"]),
    "watcher start missing before first turn": Sc(_sc(B, [_set("sidecar.start_record", False)]), "rehearsal", ["sidecar-unhealthy-before-first-turn"]),
    "watcher non-zero exit before first turn": Sc(_sc(B, [_set("sidecar.exit_code", 2)]), "rehearsal", ["sidecar-unhealthy-before-first-turn"]),
    "watcher overflow before first turn": Sc(_sc(B, [_set("sidecar.queue_overflow", True)]), "rehearsal", ["sidecar-unhealthy-before-first-turn"]),
    "operator reason before first turn": Sc(_sc(B, [_set("checker_reasons", [READERS])]), "rehearsal", ["operator-reason-before-first-turn"]),
    "operator diff before first turn": Sc(_sc(B, [_set("operator.unexplained_diffs", 1)]), "rehearsal", ["operator-diff-unexplained-before-first-turn"]),
    "finalize abort before first turn": Sc(_sc(B, [_set("ledger.finalize_abort", True)]), "rehearsal", ["finalize-abort-before-first-turn"]),
    "rate limit before first turn": Sc(_sc(B, [_rate]), "pause", ["rate-limit"]),
    "rate-limit type alone": Sc(_sc(B, [_apis({"status": None, "type": "rate_limit_error", "text": None})]), "pause", ["rate-limit"]),
    "429 with type None (W1B-6)": Sc(_sc(A, [_apis({"status": 429, "type": None, "text": None}), _end_error(1)]), "pause", ["rate-limit"]),
    # W1B2-1, glitch-f3's correction (6 Oct 2026; glitch-f3's, not the owner's): a silent first-turn timeout is
    # before the agent's first turn; on its own it is a rehearsal by its own row, and every before-first-turn
    # harness row it meets agrees (the same route, one answer). The review's four probe cases, and the bare one.
    "a bare silent first-turn timeout (glitch-f3)": Sc(_sc(B, [silent_timeout]), "rehearsal", ["silent-timeout-before-first-turn"]),
    "silent timeout + API error 529 (W1B2-1)": Sc(_sc(B, [silent_timeout, _apis(E529)]), "rehearsal",
                                                  ["api-error-before-first-turn", "silent-timeout-before-first-turn"]),
    "silent timeout + API error 500 (W1B2-1)": Sc(_sc(B, [silent_timeout, _apis(E500)]), "rehearsal",
                                                  ["api-error-before-first-turn", "silent-timeout-before-first-turn"]),
    "silent timeout + no-first-agent-turn (W1B2-1)": Sc(_sc(B, [silent_timeout, _set("checker_reasons", [NFAT])]), "rehearsal",
                                                        ["operator-reason-before-first-turn", "silent-timeout-before-first-turn"]),
    "silent timeout + container exit (W1B2-1)": Sc(_sc(B, [silent_timeout, _set("exit.container_exited", True)]), "rehearsal",
                                                   ["container-start-failed", "silent-timeout-before-first-turn"]),
    "silent timeout + a rate limit -> pause": Sc(_sc(B, [silent_timeout, _rate]), "pause", ["rate-limit"],
                                                 ["api-error-before-first-turn", "silent-timeout-before-first-turn", "rate-limit"]),
    "silent timeout with an init mismatch -> refused (W1B2-1)": Sc(_sc(B, [silent_timeout, lambda r: r["init"].__setitem__(0, dict(PIN, model="x"))]),
                                                                   REFUSED, None),
    "a silent error turn, then a silent timeout": Sc(_sc(B, [silent_turn, silent_timeout]), "rehearsal", ["silent-timeout-before-first-turn"]),
    "a timeout after completed output grades (glitch-f3)": Sc(_sc(A, [_multi_turn(1), silent_timeout]), "graded", ["timed-out"]),
    "one turn with output that timed out grades (glitch-f3)": Sc(_sc(B, [output_timeout]), "graded", ["timed-out"]),
    "nothing happened before first turn": Sc(_sc(B, []), REFUSED, None),
    "a turn with no agent output and nothing recorded": Sc(_sc(B, [silent_turn]), REFUSED, None),
    "counters rose before the first turn": Sc(_sc(B, [_set("cgroup.oom_kill_delta", 1)]), REFUSED, None),
    "preflight failure recorded with a turn": Sc(_sc(B, [silent_turn, _set("preflight.ok", False)]), REFUSED, None, None, None),
    # after the first turn
    "clean end_turn": Sc(_sc(A, []), "graded", ["end-turn"]),
    "timeout, host-killed exec": Sc(_sc(A, [_timeout]), "graded", ["timed-out"]),
    "API error after first turn, non-zero exit": Sc(_sc(A, [_api, _end_error(1)]), "harness-error", ["api-error-after-first-turn"]),
    "container exit after first turn": Sc(_sc(A, [_container]), "harness-error", ["container-exit-after-first-turn"]),
    "watcher start missing": Sc(_sc(A, [_set("sidecar.start_record", False)]), "harness-error", ["watcher-gap"]),
    "watcher stop missing": Sc(_sc(A, [_set("sidecar.stop_record", False)]), "harness-error", ["watcher-gap"]),
    "watcher non-zero exit": Sc(_sc(A, [_set("sidecar.exit_code", 1)]), "harness-error", ["watcher-gap"]),
    "watcher queue overflow": Sc(_sc(A, [_set("sidecar.queue_overflow", True)]), "harness-error", ["watcher-gap"]),
    "init model differs": Sc(_sc(A, [lambda r: r["init"].__setitem__(0, dict(PIN, model="x"))]), "harness-error", ["init-mismatch"]),
    "init mode differs": Sc(_sc(A, [lambda r: r["init"].__setitem__(0, dict(PIN, permission_mode="default"))]), "harness-error", ["init-mismatch"]),
    "init version differs": Sc(_sc(A, [lambda r: r["init"].__setitem__(1, dict(PIN, version="9.9.9"))]), "harness-error", ["init-mismatch"]),
    "init event missing": Sc(_sc(A, [lambda r: r["init"].__setitem__(0, None)]), "harness-error", ["init-mismatch"]),
    "mismatch on the last turn of an otherwise graded take": Sc(_sc(A, [_multi_turn(4), _mismatch]), "harness-error", ["init-mismatch"]),
    "non-zero exec exit, nothing else": Sc(_sc(A, [lambda r: r["exit"]["exec_codes"].__setitem__(0, 1)]), "harness-error", ["nonzero-exec-exit"]),
    "operator reason after first turn": Sc(_sc(A, [_set("checker_reasons", [READERS])]), "harness-error", ["operator-reason-after-first-turn"]),
    "operator diff after first turn": Sc(_sc(A, [_set("operator.unexplained_diffs", 2)]), "harness-error", ["operator-diff-unexplained-after-first-turn"]),
    "finalize abort after first turn": Sc(_sc(A, [_set("ledger.finalize_abort", True)]), "harness-error", ["finalize-abort-after-first-turn"]),
    "out-of-memory counter rose": Sc(_sc(A, [_set("cgroup.oom_kill_delta", 1)]), "aborted", ["cgroup-kill"]),
    "pids-limit counter rose": Sc(_sc(A, [_set("cgroup.pids_max_delta", 3)]), "aborted", ["cgroup-kill"]),
    "ended in error with nothing recorded": Sc(_sc(A, [_end_error(0)]), REFUSED, None),
    # the annotations: graded as usual, masked, an event; on every take (W1B-1, W1B-6)
    "outside reach: graded, masked, an event": Sc(_sc(A, [_reach()]), "graded", ["end-turn"], ["end-turn"], [OR], True),
    "quiescence kill: graded, an event (W1B-6)": Sc(_sc(A, [_set("quiescence_kill", True)]), "graded", ["end-turn"], ["end-turn"], [QK], False),
    "outside reach on a timed-out take -> mask (W1B-6)": Sc(_sc(A, [_timeout, _reach()]), "graded", ["timed-out"], ["timed-out"], [OR], True),
    "quiescence kill on a timed-out take": Sc(_sc(A, [_timeout, _set("quiescence_kill", True)]), "graded", ["timed-out"], None, [QK], False),
    "outside reach with an OOM kill (aborted, W1B-1)": Sc(_sc(A, [_cgroup, _end_error(137), _reach(2)]), "aborted", ["cgroup-kill"], None, [OR], True),
    "outside reach with a rate limit (pause, W1B-1)": Sc(_sc(A, [_rate, _end_error(1), _reach()]), "pause", ["rate-limit"], None, [OR], True),
    "outside reach with an API 500 (harness-error, W1B-1)": Sc(_sc(A, [_api, _end_error(1), _reach()]), "harness-error", ["api-error-after-first-turn"], None, [OR], True),
    "outside reach with a container exit (harness-error, W1B-1)": Sc(_sc(A, [_container, _end_error(137), _reach()]), "harness-error",
                                                                     ["container-exit-after-first-turn", "nonzero-exec-exit"], None, [OR], True),
    "outside reach before the first turn": Sc(_sc(B, [_set("preflight.ok", False), _reach()]), "rehearsal", ["preflight-failed"], None, [OR], True),
    "ended in error plus an outside reach only -> refused (W1B-1, W1B-6)": Sc(_sc(A, [_end_error(0), _reach()]), REFUSED, None, None, [OR], True),
    "ended in error plus a quiescence kill only -> refused (W1B-6)": Sc(_sc(A, [_end_error(0), _set("quiescence_kill", True)]), REFUSED, None, None, [QK], False),
    "quiescence kill with an OOM kill (aborted)": Sc(_sc(A, [_cgroup, _end_error(137), _set("quiescence_kill", True)]), "aborted", ["cgroup-kill"], None, [QK], False),
    "outside reach and a quiescence kill": Sc(_sc(A, [_reach(), _set("quiescence_kill", True)]), "graded", ["end-turn"], None, [OR, QK], True),
    # W1B2-2: an id the plan makes an event, arriving as a checker reason: routing refuses it (it is not an
    # operator reason), and the annotation still reports the event and masks, in either phase
    **{f"{e} as a checker reason, {ph}: refused, masked, an event (W1B2-2)":
       Sc(_sc(ph, [_set("checker_reasons", [e])]), REFUSED, None, None, [CE], True)
       for e in EVENT_IDS for ph in (B, A)},
    "an event id beside an operator reason: refused, masked (W1B2-2)": Sc(_sc(A, [_set("checker_reasons", [READERS, EVENT_IDS[0]])]),
                                                                          REFUSED, None, None, [CE], True),
    # every API error is read (W1B-4)
    "a 500 then a 429 in one take -> pause (W1B-4)": Sc(_sc(A, [_multi_turn(3), _apis(E500, E429), _end_error(1)]), "pause", ["rate-limit"],
                                                        ["rate-limit", "api-error-after-first-turn"]),
    "a 429 then a 500 in one take -> pause": Sc(_sc(A, [_multi_turn(3), _apis(E429, E500), _end_error(1)]), "pause", ["rate-limit"]),
    # the overlapping cases the plan names, and the precedence between every pair of levels
    "rate limit mid-take": Sc(_sc(A, [_multi_turn(3), _rate, _end_error(1)]), "pause", ["rate-limit"]),
    "out-of-memory kill with a non-zero exit": Sc(_sc(A, [_cgroup, _container, _end_error(137)]), "aborted", ["cgroup-kill"],
                                                  ["cgroup-kill", "container-exit-after-first-turn"]),
    "pids-limit kill with a non-zero exit": Sc(_sc(A, [_set("cgroup.pids_max_delta", 1), _end_error(1)]), "aborted",
                                               ["cgroup-kill"], ["cgroup-kill"]),
    "preflight failure recorded after the first turn": Sc(_sc(A, [_set("preflight.ok", False)]), REFUSED, None, None, None),
    "watcher gap during a pause": Sc(_sc(A, [_rate, _set("sidecar.stop_record", False)]), "pause", ["rate-limit"]),
    "rate limit beats a cgroup kill": Sc(_sc(A, [_rate, _cgroup]), "pause", ["rate-limit"]),
    "cgroup kill beats an API error": Sc(_sc(A, [_api, _cgroup]), "aborted", ["cgroup-kill"]),
    "harness error beats graded": Sc(_sc(A, [_set("sidecar.queue_overflow", True), _reach()]), "harness-error", ["watcher-gap"],
                                     ["watcher-gap", "end-turn"], [OR], True),
    "two harness faults agree": Sc(_sc(A, [_container, _set("sidecar.stop_record", False)]), "harness-error",
                                   ["container-exit-after-first-turn", "watcher-gap"]),
    # refusals of the records themselves
    "already committed": Sc(_sc(A, [_set("ledger.committed", True)]), REFUSED, None),
    "a pause on a committed take": Sc(_sc(A, [_rate, _set("ledger.committed", True)]), REFUSED, None),
    "agent text in the records": Sc(_sc(A, [lambda r: r.__setitem__("transcript", "hello")]), REFUSED, None, None, None),
    "a checker reason routing.json does not list": Sc(_sc(A, [_set("checker_reasons", ["unlisted"])]), REFUSED, None),
    "a pin that is not its model's profile (W1B-10)": Sc(_sc(A, [lambda r: (r["pin"].update(version="driver-says"),
                                                                             [i.update(version="driver-says") for i in r["init"]])]), REFUSED, None),
    "a pin whose model has no profile (W1B-10)": Sc(_sc(A, [lambda r: (r["pin"].update(model="unregistered"),
                                                                        [i.update(model="unregistered") for i in r["init"]])]), REFUSED, None),
    "a None counter (W1B-2)": Sc(_sc(A, [_set("cgroup.oom_kill_delta", None)]), REFUSED, None, None, None),
    "a string counter (W1B-2)": Sc(_sc(A, [_set("cgroup.oom_kill_delta", "1")]), REFUSED, None, None, None),
    "more API errors than turns": Sc(_sc(B, [lambda r: r.__setitem__("api_errors", [dict(E500)])]), REFUSED, None, None, None),
    # glitch-f3's ruling: round 3's four text markers in the harness-side error text pause, word-bounded and
    # case-insensitive, whatever the structured fields say; each marker alone, so a mutated marker goes red
    "usage-limit refusal, text only, before the first turn (glitch-f3)": Sc(_sc(B, [_apis(EUSAGE)]), "pause", ["rate-limit"]),
    "usage-limit refusal, text only, mid-take (glitch-f3)": Sc(_sc(A, [_multi_turn(3), _apis(EUSAGE), _end_error(1)]),
                                                              "pause", ["rate-limit"]),
    "'rate limit' alone in the error text": Sc(_sc(A, [_apis(_err("API Error: Rate limit reached")), _end_error(1)]),
                                               "pause", ["rate-limit"]),
    "'weekly limit' alone in the error text": Sc(_sc(A, [_apis(_err("You've reached your weekly limit")), _end_error(1)]),
                                                 "pause", ["rate-limit"]),
    "'429' alone in the error text": Sc(_sc(A, [_apis(_err("API Error: 429 Too Many Requests")), _end_error(1)]),
                                        "pause", ["rate-limit"]),
    "the error text's case does not matter (RATE LIMIT)": Sc(_sc(B, [_apis(_err("RATE LIMIT EXCEEDED"))]), "pause", ["rate-limit"]),
    "a marker in a 500's error text pauses (structured OR text)": Sc(_sc(A, [_apis(_err("usage limit reached", 500, "api_error")),
                                                                         _end_error(1)]),
                                                                     "pause", ["rate-limit"], ["rate-limit", "api-error-after-first-turn"]),
    "a marker inside another word is not one (prorate limits)": Sc(_sc(B, [_apis(_err("prorate limits apply"))]), "rehearsal",
                                                                   ["api-error-before-first-turn"]),
    "429 inside a number is not one (4290)": Sc(_sc(A, [_apis(_err("upstream error 4290")), _end_error(1)]), "harness-error",
                                                ["api-error-after-first-turn"]),
    "'resets' alone is not a marker (round 3's review 13, F6)": Sc(_sc(B, [_apis(_err("Session resets at 9pm"))]), "rehearsal",
                                                                   ["api-error-before-first-turn"]),
    "a 500 whose error text names no marker": Sc(_sc(A, [_apis(E500_TEXT), _end_error(1)]), "harness-error",
                                                 ["api-error-after-first-turn"]),
}


def scenario_problems(table: dict) -> list[str]:
    p = []
    for name, sc in SCENARIOS.items():
        rec = sc.build()
        got = try_route(rec, table)
        if sc.route == REFUSED:
            if not isinstance(got, Exception):
                p.append(f"{name}: want refused, got {got['route']}")
            notes = try_annotate(rec, table)
            if sc.events is None:
                if not isinstance(notes, Exception):
                    p.append(f"{name}: malformed records annotated ({notes})")
            elif isinstance(notes, Exception):
                p.append(f"{name}: annotate refused ({notes})")
            elif (notes["events"], notes["mask"]) != (list(sc.events), sc.mask):
                p.append(f"{name}: want events {list(sc.events)} mask {sc.mask}, got {notes}")
            continue
        if isinstance(got, Exception):
            p.append(f"{name}: refused ({got})")
        elif got["route"] != sc.route or got["rows"] != sc.rows:
            p.append(f"{name}: want {sc.route} via {sc.rows}, got {got['route']} via {got['rows']}")
        elif sc.matched is not None and got["matched"] != sc.matched:
            p.append(f"{name}: want matched {sc.matched}, got {got['matched']}")
        elif (got["events"], got["mask"]) != (list(sc.events), sc.mask):
            p.append(f"{name}: want events {list(sc.events)} mask {sc.mask}, got {got['events']} {got['mask']}")
    return p


TIE_PROBE_ROW = "operator-diff-unexplained-before-first-turn"


def tie_probe(table: dict) -> tuple[dict, dict]:
    """Widen one rehearsal row to every phase (the only way rows of one level can meet with
    different routes) and build a record both it and its after-first-turn twin match."""
    t = copy.deepcopy(table)
    for r in t["rows"]:
        if r["id"] == TIE_PROBE_ROW:
            r["when"] = labels4.ANY_TIME
    rec = baseline(A)
    rec["operator"]["unexplained_diffs"] = 1
    return t, rec


def tie_problems(table: dict) -> list[str]:
    """A double match at equal precedence must be refused, through route() itself."""
    t, rec = tie_probe(table)
    got = try_route(rec, t)
    if not isinstance(got, routing.RoutingRefused) or "tie" not in str(got):
        return [f"tie probe: want a tie refusal, got {got}"]
    return []


def _guarded(name, fn, *args) -> list[str]:
    """A check that crashes on a table has found a problem with it, never a pass."""
    try:
        return fn(*args)
    except Exception as e:  # noqa: BLE001
        return [f"{name} crashed: {type(e).__name__}: {e}"]


def all_problems(table: dict) -> list[str]:
    p = routing.check_table(table)
    if p:
        return p
    for row in table["rows"]:
        p += _guarded(f"row {row['id']}", row_problems, row, table)
    for name, fn in (("grid", grid_problems), ("annotation grid", annotation_grid_problems),
                     ("seam", seam_problems), ("scenarios", scenario_problems), ("tie", tie_problems)):
        p += _guarded(name, fn, table)
    return p


# ------------------------------------------------------------------------ 5. the mutation sweep
_CONDITION_MUTANT = {"eq": ("value", "__mutated__"), "ne": ("op", "eq"), "gt": ("value", 10 ** 9),
                     "truthy": ("op", "falsy"), "falsy": ("op", "truthy"), "not_null": ("op", "is_null"),
                     "is_null": ("op", "not_null"), "nonempty": ("op", "empty"), "empty": ("op", "nonempty"),
                     "in_operator_reasons": ("op", "is_null"), "in_checker_events": ("op", "is_null"),
                     "in_rate_limit_markers": ("op", "is_null"),
                     "differs_from_pin": ("op", "is_null"), "nonzero_outside_timeout": ("op", "is_null")}


def _other(v):
    return v + 1 if isinstance(v, int) and not isinstance(v, bool) else f"{v}-mutated"


def mutants(table: dict):
    """(description, mutated table) for every row, annotation, table-level and precedence mutation."""
    for i, row in enumerate(table["rows"]):
        for other in labels4.ROUTES:
            if other != row["route"]:
                t = copy.deepcopy(table)
                t["rows"][i]["route"] = other
                yield f"{row['id']}: route -> {other}", t
        for other in labels4.PHASES:
            if other != row["when"]:
                t = copy.deepcopy(table)
                t["rows"][i]["when"] = other
                yield f"{row['id']}: phase -> {other}", t
        t = copy.deepcopy(table)
        del t["rows"][i]
        yield f"{row['id']}: removed", t
        for group in ("all_of", "any_of", "none_of"):
            if group in row:
                t = copy.deepcopy(table)
                del t["rows"][i][group]
                yield f"{row['id']}: {group} deleted", t
            for j, c in enumerate(row.get(group, [])):
                key, val = _CONDITION_MUTANT[c["op"]]
                t = copy.deepcopy(table)
                t["rows"][i][group][j][key] = val
                yield f"{row['id']}: {group}[{j}] {c['op']} mutated", t
                t = copy.deepcopy(table)
                del t["rows"][i][group][j]
                yield f"{row['id']}: {group}[{j}] {c['op']} deleted", t
    for i, a in enumerate(table["annotations"]):
        t = copy.deepcopy(table)
        del t["annotations"][i]
        yield f"annotation {a['id']}: removed", t
        for flag in ("event", "mask"):
            t = copy.deepcopy(table)
            t["annotations"][i][flag] = not a[flag]
            yield f"annotation {a['id']}: {flag} flipped", t
        t = copy.deepcopy(table)
        del t["annotations"][i]["any_of"]
        yield f"annotation {a['id']}: any_of deleted", t
        for j, c in enumerate(a["any_of"]):
            key, val = _CONDITION_MUTANT[c["op"]]
            t = copy.deepcopy(table)
            t["annotations"][i]["any_of"][j][key] = val
            yield f"annotation {a['id']}: any_of[{j}] {c['op']} mutated", t
    for key, values in table["rate_limit_markers"].items():
        if key == "source":
            continue
        t = copy.deepcopy(table)
        del t["rate_limit_markers"][key]
        yield f"rate_limit_markers: {key} deleted", t
        for j, v in enumerate(values):
            t = copy.deepcopy(table)
            t["rate_limit_markers"][key][j] = _other(v)
            yield f"rate_limit_markers: {key}[{j}] {v!r} -> {_other(v)!r}", t
    t = copy.deepcopy(table)
    t["rate_limit_markers"]["code"] = t["rate_limit_markers"].pop("status")
    yield "rate_limit_markers: status renamed to a non-API-error key", t
    for j, eid in enumerate(table["checker_reasons_become_events"]["ids"]):   # W1B2-2
        t = copy.deepcopy(table)
        del t["checker_reasons_become_events"]["ids"][j]
        yield f"checker_reasons_become_events: {eid} dropped", t
    for j, end in enumerate(table["graded_ends"]):
        t = copy.deepcopy(table)
        del t["graded_ends"][j]
        yield f"graded_ends: {end} dropped", t
    t = copy.deepcopy(table)
    t["graded_ends"].append(labels4.END_ERROR)
    yield "graded_ends: error added", t
    for j, f in enumerate(table["pin_fields"]):
        t = copy.deepcopy(table)
        del t["pin_fields"][j]
        yield f"pin_fields: {f} dropped", t
    levels = table["precedence"]
    for k in range(len(levels) - 1):
        t = copy.deepcopy(table)
        t["precedence"][k], t["precedence"][k + 1] = t["precedence"][k + 1], t["precedence"][k]
        yield f"precedence: swap levels {k} and {k + 1}", t
        t = copy.deepcopy(table)
        t["precedence"][k:k + 2] = [t["precedence"][k] + t["precedence"][k + 1]]
        yield f"precedence: merge levels {k} and {k + 1}", t
    t = copy.deepcopy(table)
    t["precedence"] = [[r] for lvl in table["precedence"] for r in lvl]
    yield "precedence: rehearsal split from harness-error", t


# ----------------------------------------------------------------- record keys, one test each
def _leaf_paths() -> list[str]:
    out = []
    for key, subs in routing.RECORD_SCHEMA.items():
        out += [f"{key}.{s}" for s in subs] if subs else [key]
    return out


def _record_with_everything() -> dict:
    """An after-first-turn record with an API error, so every key, list and entry is present."""
    r = baseline(A)
    set_api(r, [dict(E500)])
    return r


def _drop(rec: dict, path: str):
    head, _, tail = path.partition(".")
    del (rec[head] if tail else rec)[tail or head]


def _put(rec: dict, path: str, value):
    head, _, tail = path.partition(".")
    (rec[head] if tail else rec)[tail or head] = value


def refuses(fn, rec: dict, table: dict) -> bool:
    """True only when fn raises RoutingRefused: any other exception is a crash, not a refusal."""
    try:
        fn(rec, table)
    except routing.RoutingRefused:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def key_problems(path: str, table: dict) -> list[str]:
    """W1B-2: the key dropped, and set to None, must each be refused (by route and by annotate)."""
    p = []
    for how in ("dropped", "None"):
        rec = _record_with_everything()
        if how == "dropped":
            _drop(rec, path)
        else:
            _put(rec, path, None)
        for fn in (routing.route, routing.annotate):
            if not refuses(fn, rec, table):
                p.append(f"{path} {how}: {fn.__name__} did not refuse it")
    return p


# Nested keys: pin fields, init-entry fields and API-error fields.
def nested_problems(table: dict) -> list[str]:
    p = []
    for f in table["pin_fields"]:
        for where in ("pin", "init"):
            for how in ("dropped", "None"):
                rec = _record_with_everything()
                target = rec["pin"] if where == "pin" else rec["init"][0]
                if how == "dropped":
                    del target[f]
                else:
                    target[f] = None
                if not refuses(routing.route, rec, table):
                    p.append(f"{where}.{f} {how}: not refused")
    for f in API_ERROR_FIELDS_WANT:   # the test's own list, so a field dropped from routing's is still checked
        rec = _record_with_everything()
        del rec["api_errors"][0][f]
        if not refuses(routing.route, rec, table):
            p.append(f"api_errors[0].{f} dropped: not refused")
        rec = _record_with_everything()
        rec["api_errors"][0][f] = {"status": "429", "type": 429, "text": 429}[f]
        if not refuses(routing.route, rec, table):
            p.append(f"api_errors[0].{f} wrongly typed: not refused")
    return p


# Captured once, so a mutant that empties routing.LEAF_TYPES cannot empty the check's own list.
COUNT_LEAVES = [path for path, (_, what) in routing.LEAF_TYPES.items() if what == "a non-negative int"]
FLAG_LEAVES = [path for path, (_, what) in routing.LEAF_TYPES.items() if what == "a bool"]


def count_confusion_problems(table: dict) -> list[str]:
    """Every count leaf refuses a bool, a string, a float and a negative number; every flag a
    number and a string."""
    p = []
    for path in COUNT_LEAVES:
        for bad in (True, "1", -1, 1.0):
            rec = _record_with_everything()
            set_path(rec, path, bad)
            if not refuses(routing.route, rec, table):
                p.append(f"{path}={bad!r}: not refused")
    for path in FLAG_LEAVES:
        for bad in (0, 1, "false"):
            rec = _record_with_everything()
            set_path(rec, path, bad)
            if not refuses(routing.route, rec, table):
                p.append(f"{path}={bad!r}: not refused")
    return p


# ------------------------------------------------------- glitch-f3's ruling: the error text's markers
# (harness-side error text, the marker round 3's bounded search finds in it, or None). Round 3's own
# matched_marker is run on every probe (TestRound3Sources), so these are its rule, not a reading of it.
TEXT_PROBES = (
    (USAGE_TEXT, "usage limit"),
    ("API Error: Rate limit reached", "rate limit"),
    ("RATE LIMIT", "rate limit"),
    ("You've hit your Weekly Limit", "weekly limit"),
    ("API Error: 429 Too Many Requests", "429"),
    ("(429)", "429"),
    ("usage limit, then a rate limit", "rate limit"),   # the first marker in round 3's order, not the text's
    ("prorate limits", None),                            # a marker inside another word
    ("prorate limit", None),                             # the left bound alone
    ("rate limits", None),                               # the right bound alone
    ("4290", None),
    ("x429", None),
    ("rate_limit_error", None),                          # an underscore is a word character
    ("Session resets at 9pm", None),                     # round 3 left 'resets' out (its review 13, F6)
    ("internal server error", None),
    ("", None),
)


def text_match_problems(fn, markers) -> list[str]:
    """Every probe on which fn(text, markers) does not find exactly the probe's marker."""
    p = []
    for text, want in TEXT_PROBES:
        got = fn(text, markers)
        if got != want:
            p.append(f"{text!r}: want {want!r}, got {got!r}")
    return p


# The agent's own reply, printing every marker (TurnResult.text): it must never reach the markers.
AGENT_SAYS = ("rate limit", "429", "usage limit", "RATE LIMIT: usage limit, weekly limit, error 429")


def agent_text_problems(table: dict) -> list[str]:
    """glitch-f3's ruling: markers are matched on the harness-side error text only, never on the agent's own
    reply. An agent that prints them beside an API error carrying none (a 500, "internal server error") never
    pauses, before or after its first turn, and its reply never becomes the record's error text."""
    p = []
    for said in AGENT_SAYS:
        cases = {B: ([a_silent_turn(text=said, api_errors=[dict(E500_TEXT)])], labels4.REHEARSAL),
                 A: ([a_turn(text=said), a_turn(text=said, exit_code=1, end_reason=labels4.END_ERROR,
                                              api_errors=[dict(E500_TEXT)])], labels4.HARNESS_ERROR)}
        for phase, (turns, want) in cases.items():
            rec = aa.harness_records(turns, pin=PIN, box=full_box())
            if rec["api_errors"] != [E500_TEXT]:
                p.append(f"{said!r} {phase}: api_errors {rec['api_errors']}")
            got = try_route(rec, table)
            route = got if isinstance(got, Exception) else got["route"]
            if route != want:
                p.append(f"{said!r} {phase}: routed {route}, want {want}")
    return p


# --------------------------------------------------------------------------------------- tests
class TestRoutingTable(unittest.TestCase):
    def test_real_table_is_sound(self):
        self.assertEqual(routing.check_table(REAL), [])

    def test_table_routes_and_phases_come_from_labels4(self):
        self.assertEqual({r["route"] for r in REAL["rows"]}, set(labels4.ROUTES))
        self.assertLessEqual({r["when"] for r in REAL["rows"]}, set(labels4.PHASES))
        self.assertEqual(sorted(REAL["graded_ends"]), sorted(labels4.GRADED_ENDS))

    def test_every_row_and_annotation_cites_a_source(self):
        self.assertTrue(all(r.get("source") for r in REAL["rows"] + REAL["annotations"]))

    def test_source_check_can_fail(self):
        for where in ("rows", "annotations"):
            t = copy.deepcopy(REAL)
            del t[where][0]["source"]
            self.assertTrue(any("no source cited" in x for x in routing.check_table(t)), where)

    def test_table_check_can_fail(self):
        for bad in ({"precedence": [["graded"], ["pause"]]},):
            t = copy.deepcopy(REAL)
            t.update(bad)
            self.assertNotEqual(routing.check_table(t), [])
        t = copy.deepcopy(REAL)
        t["rows"][0]["route"] = "success"
        self.assertNotEqual(routing.check_table(t), [])
        t = copy.deepcopy(REAL)
        t["rows"][0]["any_of"][0]["path"] = "transcript.text"
        self.assertNotEqual(routing.check_table(t), [])
        t = copy.deepcopy(REAL)
        t["rows"] = [r for r in t["rows"] if r["route"] != labels4.ABORTED]
        self.assertNotEqual(routing.check_table(t), [])

    def test_rows_never_read_a_text_derived_count(self):
        """W1B-1: only annotations may read the events record."""
        t = copy.deepcopy(REAL)
        t["rows"][0]["any_of"].append({"path": "events.outside_reach", "op": "gt", "value": 0})
        self.assertTrue(any("text-derived count" in x for x in routing.check_table(t)))
        t = copy.deepcopy(REAL)
        t["rows"][0]["mask"] = True
        self.assertTrue(any("never routing rows" in x for x in routing.check_table(t)))

    def test_rate_limit_marker_keys_are_api_error_fields(self):
        """W1B-6."""
        t = copy.deepcopy(REAL)
        t["rate_limit_markers"]["code"] = [429]
        self.assertTrue(any("not an API-error field" in x for x in routing.check_table(t)))

    def test_text_markers_are_non_empty_lower_case_strings(self):
        """Round 3's bounded search lowercases the error text only, so an upper-case marker could never match,
        and an empty one would match at every word boundary."""
        self.assertEqual(REAL["rate_limit_markers"]["text"], [m.lower() for m in REAL["rate_limit_markers"]["text"]])
        for bad in ("Rate Limit", "", 429, None):
            t = copy.deepcopy(REAL)
            t["rate_limit_markers"]["text"] = ["rate limit", bad]
            self.assertTrue(any("text marker" in x for x in routing.check_table(t)), bad)

    def test_graded_ends_checked_against_labels4(self):
        """W1B-7."""
        for bad in (["end_turn"], ["end_turn", "timeout"], ["end_turn", "timed-out", "error"]):
            t = copy.deepcopy(REAL)
            t["graded_ends"] = bad
            self.assertNotEqual(routing.check_table(t), [], bad)
        t = copy.deepcopy(REAL)
        next(r for r in t["rows"] if r["id"] == "timed-out")["any_of"][0]["value"] = "timeout"
        self.assertNotEqual(routing.check_table(t), [])
        with mock.patch.object(labels4, "GRADED_ENDS", ("end_turn",)):
            self.assertNotEqual(routing.check_table(REAL), [])

    def test_real_table_refuses_an_unlisted_checker_reason(self):
        t = copy.deepcopy(REAL)
        t["pin_profiles"] = copy.deepcopy(TEST_PROFILES)   # isolate the reasons' refusal
        rec = baseline(A)
        rec["checker_reasons"] = ["not-a-round-3-reason"]
        with self.assertRaisesRegex(routing.RoutingRefused, "checker reason"):
            routing.route(rec, t)

    def test_real_table_refuses_every_take_while_pins_pending(self):
        """W1B-10: until CP5 pre-registers the pins, no driver-supplied pin is trusted."""
        self.assertEqual(REAL["pin_profiles"], {})
        self.assertTrue(REAL["pin_profiles_status"].startswith("PENDING"))
        with self.assertRaisesRegex(routing.RoutingRefused, "pre-registered profile"):
            routing.route(baseline(A), REAL)


class TestRound3Sources(unittest.TestCase):
    """Javier's ruling "gap4 routing: A" (6 Oct 2026, 17:52:33 EDT): round 3's operator-side reasons and its
    pause cap are copied into routing.json from round 3's committed files, each with its source. These tests
    re-derive them from those files at round 3's done commit, so the table can never drift from its source."""

    COMMIT = "e2979b3143081824aadea73523ec41af30c1ddb1"
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    def show(self, path):
        p = subprocess.run(["git", "-C", self.ROOT, "show", f"{self.COMMIT}:{path}"], capture_output=True)
        self.assertEqual(p.returncode, 0, f"{path} at {self.COMMIT} (git fetch --unshallow?)")
        return p.stdout.decode()

    def test_operator_reasons_are_round_3s_reasons_less_the_three_the_plan_makes_events(self):
        listed = set(json.loads(self.show("evals/gap-study-3/prereg.json"))["rehearsal_reasons"])
        emitted = set(re.findall(r"[\"']\[([a-z][a-z-]*)\] ", self.show("evals/gap-study-3/check_take.py")))
        emitted.add("no-first-agent-turn")   # check_take.py's NO_FIRST_AGENT_TURN constant, used without brackets
        self.assertEqual(emitted, listed)
        events = set(REAL["checker_reasons_become_events"]["ids"])
        self.assertEqual(events, {"study-materials-reached", "account-email", "read-outside-the-checkout"})
        self.assertEqual(set(REAL["operator_reasons"]), listed - events)
        self.assertEqual(len(REAL["operator_reasons"]), len(listed - events))
        self.assertTrue(REAL["operator_reasons_status"].startswith("FILLED"))

    def test_every_operator_reason_cites_its_source(self):
        listed = json.loads(self.show("evals/gap-study-3/prereg.json"))["rehearsal_reasons"]
        sources = REAL["operator_reason_sources"]
        self.assertEqual(set(sources), set(REAL["operator_reasons"]))
        for rid, src in sources.items():
            self.assertEqual(src["file"], "evals/gap-study-3/prereg.json")
            self.assertEqual(src["commit"], self.COMMIT)
            self.assertEqual(src["key"], f"rehearsal_reasons.{rid}")
            self.assertEqual(src["meaning"], listed[rid])
            self.assertTrue(src["emitted_at"].startswith("evals/gap-study-3/check_take.py:"), rid)

    def test_the_pause_cap_is_round_3s(self):
        pre = json.loads(self.show("evals/gap-study-3/prereg.json"))
        cap = REAL["caps"][labels4.PAUSE]
        self.assertEqual(cap["reruns_per_half_cell"], int(pre["pause_cap"]))
        self.assertIn("evals/gap-study-3/prereg.json", cap["source"])
        self.assertIn(self.COMMIT, cap["source"])

    # glitch-f3's ruling (6 Oct 2026): round 3's text markers and its bounded match. Only drive.py's lines
    # 140-160 and 900-925 are read from round 3 (the gap4 lane lead's rule for this lane).
    DRIVE = "evals/gap-study-3/drive.py"

    def round3_lines(self, first: int, last: int) -> list[str]:
        if not (140 <= first <= last <= 160 or 900 <= first <= last <= 925):
            raise AssertionError(f"drive.py:{first}-{last} is outside the lines this lane may read")
        return self.show(self.DRIVE).splitlines()[first - 1:last]

    def round3_markers(self) -> tuple:
        """RATE_LIMIT_MARKERS, from the assignment on drive.py:149, parsed with ast (never imported)."""
        (line,) = self.round3_lines(149, 149)
        node = ast.parse(line).body[0]
        self.assertIsInstance(node, ast.Assign, line)
        self.assertEqual([getattr(t, "id", None) for t in node.targets], ["RATE_LIMIT_MARKERS"], line)
        markers = ast.literal_eval(node.value)
        self.assertIsInstance(markers, tuple)
        return markers

    def test_text_markers_are_round_3s_in_order(self):
        self.assertEqual(REAL["rate_limit_markers"]["text"], list(self.round3_markers()))
        source = REAL["rate_limit_markers"]["source"]
        for cite in ("glitch-f3", "evals/gap-study-3/drive.py:149", self.COMMIT, "driver_constants.rate_limit_markers"):
            self.assertIn(cite, source)

    def test_text_match_is_round_3s_matched_marker(self):
        """Round 3's own matched_marker (drive.py:912-919), run on the probes, agrees with them and with routing's
        match: the probes are round 3's rule, never this lane's reading of it."""
        lines = self.round3_lines(912, 919)
        self.assertTrue(lines[0].startswith("def matched_marker(text: str)"), lines[0])
        ns = {"re": re, "RATE_LIMIT_MARKERS": self.round3_markers()}
        exec(compile("\n".join(lines), f"{self.DRIVE}@{self.COMMIT[:8]}:912", "exec",    # noqa: S102 - pinned, read lines
                     flags=__future__.annotations.compiler_flag, dont_inherit=True), ns)
        theirs = ns["matched_marker"]
        markers = REAL["rate_limit_markers"]["text"]
        self.assertEqual(text_match_problems(lambda text, _markers: theirs(text), markers), [])
        self.assertEqual(text_match_problems(routing.rate_limit_text_marker, markers), [])


class TestRows(unittest.TestCase):
    """One test per row, generated from routing.json below."""


def _row_test(row_id):
    def test(self):
        t = test_table()
        row = next(r for r in t["rows"] if r["id"] == row_id)
        self.assertEqual(row_problems(row, t), [])
    return test


for _row in REAL["rows"]:
    setattr(TestRows, "test_row_" + _row["id"].replace("-", "_"), _row_test(_row["id"]))


class TestScenarios(unittest.TestCase):
    """One test per plan scenario, generated from SCENARIOS."""


def _scenario_test(name):
    def test(self):
        sc = SCENARIOS[name]
        rec = sc.build()
        got = try_route(rec, test_table())
        if sc.route == REFUSED:
            self.assertIsInstance(got, routing.RoutingRefused)
            notes = try_annotate(rec, test_table())
            if sc.events is None:
                self.assertIsInstance(notes, routing.RoutingRefused)
            else:
                self.assertEqual((notes["events"], notes["mask"]), (list(sc.events), sc.mask))
        else:
            self.assertNotIsInstance(got, Exception, str(got))
            self.assertEqual((got["route"], got["rows"]), (sc.route, sc.rows))
            if sc.matched is not None:
                self.assertEqual(got["matched"], sc.matched)
            self.assertEqual((got["events"], got["mask"]), (list(sc.events), sc.mask))
    return test


for _name in SCENARIOS:
    setattr(TestScenarios, "test_" + "".join(c if c.isalnum() else "_" for c in _name), _scenario_test(_name))


class TestRecordKeys(unittest.TestCase):
    """W1B-2: one test per record key, dropped and set to None, each refused."""

    def test_leaf_list_covers_the_schema(self):
        self.assertEqual(len(COUNT_LEAVES), 5)
        self.assertEqual(len(FLAG_LEAVES), 10)
        self.assertEqual(set(_leaf_paths()) - {"ledger.end", "ledger.turn_ends", "ledger.turn_outputs",
                                                "exit.exec_codes", "init", "pin", "api_errors", "checker_reasons"},
                         set(routing.LEAF_TYPES))

    def test_nested_keys(self):
        self.assertEqual(nested_problems(test_table()), [])

    def test_counts_and_flags_refuse_other_types(self):
        self.assertEqual(count_confusion_problems(test_table()), [])

    def test_api_error_text_is_required_and_typed(self):
        """glitch-f3's ruling under W1B-2's rule: every API-error record carries `text`, a str or None; a record
        missing it, or holding anything else there, is refused by route and by annotate, never read as no text."""
        self.assertEqual(tuple(routing.API_ERROR_KEYS), API_ERROR_FIELDS_WANT)
        t = test_table()

        def rec_with(err: dict) -> dict:
            r = baseline(A)
            set_api(r, [err])
            set_end(r, labels4.END_ERROR, 1)
            return r
        for text in (None, "internal server error"):
            got = routing.route(rec_with(_err(text, 500, "api_error")), t)
            self.assertEqual((got["route"], got["rows"]), (labels4.HARNESS_ERROR, ["api-error-after-first-turn"]))
        bad = [rec_with({"status": 500, "type": "api_error"})]
        bad += [rec_with(_err(v, 500, "api_error")) for v in (429, True, b"usage limit", ["usage limit"], {"text": "x"})]
        for rec in bad:
            for fn in (routing.route, routing.annotate):
                self.assertTrue(refuses(fn, rec, t), (fn.__name__, rec["api_errors"]))

    def test_type_checks_can_fail(self):
        with mock.patch.object(routing, "LEAF_TYPES", {}):
            self.assertIn("cgroup.oom_kill_delta None: route did not refuse it",
                          key_problems("cgroup.oom_kill_delta", test_table()))
            self.assertNotEqual(count_confusion_problems(test_table()), [])

        def keys_only(value, fields, what):   # checks the keys, never the value types
            return [] if isinstance(value, dict) and set(value) == set(fields) else [f"{what} keys"]
        with mock.patch.object(routing, "_pin_problems", keys_only):
            self.assertNotEqual(nested_problems(test_table()), [])


def _key_test(path):
    def test(self):
        self.assertEqual(key_problems(path, test_table()), [])
    return test


for _path in _leaf_paths():
    setattr(TestRecordKeys, "test_key_" + _path.replace(".", "_"), _key_test(_path))


class TestSeam(unittest.TestCase):
    """harness_records -> route: the box records (W1B-2) and the before-first-turn rows (W1B-5)."""

    def test_every_before_first_turn_row_through_harness_records(self):
        self.assertEqual(seam_problems(test_table()), [])

    def test_seam_check_can_fail(self):
        real = aa.harness_records

        def old_phase(turns, *, pin, box):   # the pre-ruling rule: any turn starts the first turn
            out = real(turns, pin=pin, box=box)
            out["ledger"]["first_turn_started"] = bool(turns)
            out["ledger"]["turn_outputs"] = [True] * len(turns)
            return out
        with mock.patch.object(aa, "harness_records", old_phase):
            self.assertTrue(any("api-error-before-first-turn" in x for x in seam_problems(test_table())))

        def timeout_starts(turns, *, pin, box):   # 3fcab58d's refinement: a timed-out turn starts the agent's turn
            out = real(turns, pin=pin, box=box)
            timed = [t.end_reason == labels4.TIMED_OUT for t in turns]
            out["ledger"]["turn_outputs"] = [o or x for o, x in zip(out["ledger"]["turn_outputs"], timed)]
            out["ledger"]["first_turn_started"] = any(out["ledger"]["turn_outputs"])
            return out
        with mock.patch.object(aa, "harness_records", timeout_starts):
            found = seam_problems(test_table())
        for row in ("api-error-before-first-turn", "operator-reason-before-first-turn", "container-start-failed"):
            self.assertTrue(any(x.startswith(f"seam {row}") and "silent timed-out turn" in x for x in found), row)
        t = test_table()
        t["rows"].append({"id": "probe-new-row", "when": "before-first-turn", "route": "rehearsal",
                          "any_of": [{"path": "cgroup.pids_max_delta", "op": "gt", "value": 0}], "source": "probe"})
        self.assertTrue(any("no seam witness" in x for x in seam_problems(t)))

    def test_two_api_errors_through_harness_records(self):
        """W1B-4: a 500 then a 429 routes pause, not harness-error."""
        turns = [a_turn(), a_turn(exit_code=1, end_reason=labels4.END_ERROR, api_errors=[dict(E500)]),
                 a_turn(exit_code=1, end_reason=labels4.END_ERROR, api_errors=[dict(E429)])]
        got = routing.route(aa.harness_records(turns, pin=PIN, box=full_box()), test_table())
        self.assertEqual((got["route"], got["rows"]), (labels4.PAUSE, ["rate-limit"]))


def _box_test(key):
    def test(self):
        box = full_box()
        del box[key]
        with self.assertRaises(aa.BoxRecordError):
            aa.harness_records([a_turn(), a_turn()], pin=PIN, box=box)
        rec = aa.harness_records([a_turn(), a_turn()], pin=PIN, box=full_box(**{key: None}))
        with self.assertRaises(routing.RoutingRefused):
            routing.route(rec, test_table())
        with self.assertRaises(routing.RoutingRefused):
            routing.annotate(rec, test_table())
    return test


for _key in aa.BOX_KEYS:
    setattr(TestSeam, "test_box_" + _key + "_dropped_and_none_refused", _box_test(_key))


class TestRateLimitText(unittest.TestCase):
    """glitch-f3's ruling (in-plan, 6 Oct 2026; glitch-f3's, not the owner's): structured (status 429, type
    rate_limit_error) OR round 3's four text markers, word-bounded and case-insensitive, matched on the
    harness-side error text only, never on the agent's own output. The plan-oracle scenarios above route the
    records; these build them through harness_records, as the driver will, and pin the match itself."""

    def test_text_only_usage_limit_pauses_through_harness_records(self):
        t = test_table()
        for phase, turns in ((B, [a_silent_turn(api_errors=[dict(EUSAGE)])]),
                             (A, [a_turn(), a_turn(exit_code=1, end_reason=labels4.END_ERROR, api_errors=[dict(EUSAGE)])])):
            rec = aa.harness_records(turns, pin=PIN, box=full_box())
            self.assertEqual(rec["api_errors"], [EUSAGE])
            got = routing.route(rec, t)
            self.assertEqual((got["route"], got["rows"], got["phase"]), (labels4.PAUSE, ["rate-limit"], phase))

    def test_agent_text_never_reaches_the_markers(self):
        self.assertEqual(agent_text_problems(test_table()), [])

    def test_agent_text_check_can_fail(self):
        real = aa.harness_records

        def agent_text_in(turns, *, pin, box):   # the mutant: the agent's reply routed into the error text
            out = real(turns, pin=pin, box=box)
            erred = [t for t in turns for _ in t.api_errors]
            out["api_errors"] = [dict(e, text=t.text) for e, t in zip(out["api_errors"], erred)]
            return out
        with mock.patch.object(aa, "harness_records", agent_text_in):
            self.assertTrue(any("routed pause" in x for x in agent_text_problems(test_table())))

    def test_word_bounded_and_case_insensitive(self):
        self.assertEqual(text_match_problems(routing.rate_limit_text_marker, REAL["rate_limit_markers"]["text"]), [])

    def test_word_bound_check_can_fail(self):
        def substring(text, markers):   # the mutant: a plain substring match
            return next((m for m in markers if m in text.lower()), None)

        def case_sensitive(text, markers):   # the mutant: the text not lowercased
            return next((m for m in markers if re.search(r"(?<![\w])" + re.escape(m) + r"(?![\w])", text)), None)
        markers = REAL["rate_limit_markers"]["text"]
        for mutant in (substring, case_sensitive):
            self.assertNotEqual(text_match_problems(mutant, markers), [], mutant.__name__)
            with mock.patch.object(routing, "rate_limit_text_marker", mutant):
                self.assertNotEqual(scenario_problems(test_table()), [], mutant.__name__)


class TestProfiles(unittest.TestCase):
    """glitch-f3's ruling on 'per profile': one test per pinned model profile (test-only, injected),
    a mismatch in any of the three fields routing per the table."""


def profile_problems(model: str, table: dict) -> list[str]:
    p = []
    pin = dict(table["pin_profiles"][model], model=model)
    clean = try_route(baseline(A, pin), table)
    if isinstance(clean, Exception) or clean["route"] != labels4.GRADED:
        p.append(f"{model}: a clean take under its own profile did not grade ({clean})")
    for field in table["pin_fields"]:
        for turn in (0, -1):
            rec = baseline(A, pin)
            rec["init"][turn] = dict(pin, **{field: f"{pin[field]}-other"})
            got = try_route(rec, table)
            if isinstance(got, Exception) or (got["route"], got["rows"]) != (labels4.HARNESS_ERROR, ["init-mismatch"]):
                p.append(f"{model}: init {field} differs on turn {turn}: {got}")
        rec = baseline(A, dict(pin, **{field: f"{pin[field]}-driver"}))
        if not isinstance(try_route(rec, table), routing.RoutingRefused):
            p.append(f"{model}: a pin whose {field} is not the pre-registered one was trusted")
    return p


def _profile_test(model):
    def test(self):
        self.assertEqual(profile_problems(model, test_table()), [])
    return test


for _model in TEST_PROFILES:
    setattr(TestProfiles, "test_profile_" + _model.replace("-", "_"), _profile_test(_model))


def _profile_can_fail(self):
    with mock.patch.object(routing, "check_records", lambda rec, t: routing.shape_problems(rec, t)):
        self.assertTrue(any("was trusted" in x for x in profile_problems("test-model-b", test_table())))
    t = test_table()
    next(r for r in t["rows"] if r["id"] == "init-mismatch")["any_of"][0]["op"] = "is_null"
    self.assertNotEqual(profile_problems("test-model-a", t), [])


TestProfiles.test_profile_check_can_fail = _profile_can_fail


class TestGridAndMutations(unittest.TestCase):
    def test_grid_derived_from_table(self):
        self.assertEqual(grid_problems(test_table()), [])

    def test_annotation_grid(self):
        self.assertEqual(annotation_grid_problems(test_table()), [])

    def test_annotation_grid_can_fail(self):
        real = routing.annotate

        def graded_only(records, table=None):   # the pre-fold behaviour: mask only on a graded end
            out = real(records, table)
            if records["ledger"]["end"] not in labels4.GRADED_ENDS:
                out = {"events": [], "mask": False}
            return out
        with mock.patch.object(routing, "annotate", graded_only):
            self.assertNotEqual(annotation_grid_problems(test_table()), [])

    def test_everything_green_on_the_real_table(self):
        self.assertEqual(all_problems(test_table()), [])

    def test_every_mutation_goes_red(self):
        survivors = [d for d, t in mutants(test_table()) if not all_problems(t)]
        self.assertEqual(survivors, [])

    def test_mutation_sweep_covers_every_row_and_annotation(self):
        described = " ".join(d for d, _ in mutants(test_table()))
        for row in REAL["rows"]:
            self.assertIn(row["id"] + ": removed", described)
        for a in REAL["annotations"]:
            for what in ("removed", "event flipped", "mask flipped"):
                self.assertIn(f"annotation {a['id']}: {what}", described)
        for what in ("rate_limit_markers: status[0]", "rate_limit_markers: type[0]", "graded_ends: timed-out dropped",
                     "rate_limit_markers: text deleted"):
            self.assertIn(what, described)
        for j in range(len(REAL["rate_limit_markers"]["text"])):   # every text marker, alone (glitch-f3's ruling)
            self.assertIn(f"rate_limit_markers: text[{j}]", described)
        self.assertIn("rate-limit: any_of[2] in_rate_limit_markers mutated", described)

    def test_mask_and_events_never_from_the_winning_rows(self):
        """W1B-1/W1B-6: a route that reports mask and events from its winning rows goes red."""
        real = routing.route

        def from_winners(records, table=None):
            out = real(records, table)
            return dict(out, events=[e for e in out["events"] if out["route"] == labels4.GRADED],
                        mask=out["mask"] and out["route"] == labels4.GRADED)
        with mock.patch.object(routing, "route", from_winners):
            self.assertNotEqual(scenario_problems(test_table()), [])

    def test_tie_at_equal_precedence_is_refused(self):
        t, rec = tie_probe(test_table())
        with self.assertRaisesRegex(routing.RoutingRefused, "tie"):
            routing.route(rec, t)
        self.assertEqual(tie_problems(test_table()), [])


def purity_problems(route_fn, table: dict) -> list[str]:
    """route() must leave its input unchanged and answer the same twice."""
    p = []
    for name, sc in SCENARIOS.items():
        if sc.route == REFUSED:
            continue
        rec = sc.build()
        before = json.dumps(rec, sort_keys=True)
        first = route_fn(rec, table)
        if json.dumps(rec, sort_keys=True) != before:
            p.append(f"{name}: route changed its input")
        try:
            second = route_fn(rec, table)
        except routing.RoutingRefused as e:
            second = e
        if second != first:
            p.append(f"{name}: route answered differently twice")
    return p


def cap_problems(route_fn, table: dict) -> list[str]:
    """route() returns its own route's cap, read from the table."""
    p = []
    for name, sc in SCENARIOS.items():
        if sc.route == REFUSED:
            continue
        got = route_fn(sc.build(), table)
        if got["cap"] != table["caps"][got["route"]]:
            p.append(f"{name}: cap {got['cap']} is not {got['route']}'s")
    return p


class TestPurityAndCaps(unittest.TestCase):
    def test_route_is_pure(self):
        self.assertEqual(purity_problems(routing.route, test_table()), [])

    def test_purity_check_can_fail(self):
        def mutating(records, table):
            out = routing.route(records, table)
            records["ledger"]["committed"] = True
            return out
        self.assertNotEqual(purity_problems(mutating, test_table()), [])
        calls = []

        def forgetful(records, table):
            calls.append(1)
            return dict(routing.route(records, table), call=len(calls))
        self.assertNotEqual(purity_problems(forgetful, test_table()), [])

    def test_cap_returned_from_table(self):
        self.assertEqual(cap_problems(routing.route, test_table()), [])

    def test_cap_check_can_fail(self):
        def wrong_cap(records, table):
            return dict(routing.route(records, table), cap=table["caps"][labels4.GRADED])
        self.assertNotEqual(cap_problems(wrong_cap, test_table()), [])


if __name__ == "__main__":
    unittest.main()
