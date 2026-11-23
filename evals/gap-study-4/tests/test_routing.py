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
import harness_bookkeeping as hb  # noqa: E402  (the seam's harness name, never typed here: interface 8)
import routing  # noqa: E402
import transcript_view  # noqa: E402  (the seam's parser table: the harness names it registers)
from graders import labels4  # noqa: E402

REAL = routing.load_table()
# Round 3's reason ids the scenarios name, typed once (TestRound3Sources binds the list they come from).
READERS = "session-binding"           # an operator-side reason of either phase, harness-error after the first turn
# (pre-freeze review 2, MAJOR 1: readers-disagree now routes aborted after it, glitch-45's ruling 2; session-binding is a
# mixed reason that keeps harness-error)
NFAT = "no-first-agent-turn"          # round 3's "before the agent's first turn" reason
# Test-only pin profiles, injected in memory (CP5 pre-registers the real ones), keyed by harness, then model
# (interface 8; the harness is the seam's own name, never typed here).
TEST_HARNESS = hb.CLAUDE_CODE
TEST_PROFILES = {TEST_HARNESS: {
    "test-model-a": {"permission_mode": "bypassPermissions", "version": "0.0.1-test"},
    "test-model-b": {"permission_mode": "plan-test", "version": "0.0.2-test"},
}}
PIN = dict(TEST_PROFILES[TEST_HARNESS]["test-model-a"], model="test-model-a", harness=TEST_HARNESS)
INIT_FIELDS = ("model", "permission_mode", "version")   # an init event's fields: the pin less its harness


def init_of(pin: dict) -> dict:
    """An init event under `pin` (an init event names no harness)."""
    return {f: pin[f] for f in INIT_FIELDS}


INIT = init_of(PIN)


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
        "init": [init_of(pin) for _ in range(n)],
        "pin": dict(pin),
        "api_errors": [],
        "sidecar": {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False},
        "preflight": {"ok": True},
        "operator": {"unexplained_diffs": 0},
        "checker_reasons": [],
        "quiescence_kill": False,
        "events": {"outside_reach": 0},
        "unreadable_consequential": [],
        "quiescence_cap_survivors": 0,
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
    rec["init"].append(init_of(rec["pin"]))


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
    elif op == "nonempty" and path == "unreadable_consequential":   # CP2 ruling C3 (lane w4h): a made-up path
        set_path(rec, path, ["data/staging/samples.csv"])
    elif op == "in_operator_reasons":
        set_path(rec, path, [any_phase_reason(table)])
    elif op == "has":                                   # glitch-b5's ruling 3 (17 Oct 2026): one named reason
        set_path(rec, path, [cond["value"]])
    elif op == "in_checker_events":
        set_path(rec, path, [table["checker_reasons_become_events"]["ids"][0]])
    elif op == "in_rate_limit_markers":
        key = path.partition(".")[2]
        err = {"status": None, "type": None, "text": None}
        err[key] = table["rate_limit_markers"][TEST_HARNESS][key][0]
        set_api(rec, [err])
    elif op in ("differs_from_pin", "present_differs_from_pin"):
        rec["init"][0] = dict(init_of(rec["pin"]), model="not-the-pin")
    elif op == "nonzero_outside_timeout":
        rec["exit"]["exec_codes"][0] = 1
    elif op in ("not_null", "is_null"):
        set_path(rec, path, {"x": 1} if op == "not_null" else None)
    else:
        raise AssertionError(f"no witness for op {op}")
    return {"ledger.end"} if path == "ledger.end" else {path.partition(".")[0]}


def any_phase_reason(table: dict) -> str:
    """The first operator reason that may arrive in either phase (W1B2-8 refuses no-first-agent-turn after
    the agent's first turn)."""
    early = set(table.get("reasons_only_before_first_turn", {}).get("ids", []))
    # pre-freeze review 2, MAJOR 1 (glitch-45's ruling 2): the first such reason the generic rows route alone, never one
    # a row of its own (agent-reachable-reason, transcript-mismatch, ...) routes aborted after the first turn
    named = {c.get("value") for r in table["rows"] if r.get("route") != labels4.HARNESS_ERROR
             for c in r.get("any_of", []) if isinstance(c, dict) and c.get("op") == "has"}
    return next(r for r in table["operator_reasons"] if r not in early and r not in named)


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
    r["init"][-1] = dict(init_of(r["pin"]), version="not-the-pin")


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
            # pre-freeze review 2, MAJOR 1 (the lane review of 8d71ae0d, MAJOR 2): a terminal state's winning rows whose
            # none_of the witness's own records hold (rate-limit's none_of transcript-mismatch) do not match the
            # combined take, so the witness's route stands
            rows_by_id = {r["id"]: r for r in table["rows"]}
            if all(any(routing.holds(c, rec, table) for c in rows_by_id[w].get("none_of", []))
                   for w in mod_route["rows"]):
                want = alone["route"]
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
         "outside_reach_events": 0, "finalize_abort": False, "committed": False,
         "unreadable_consequential": [], "quiescence_cap_survivors": 0}
    b.update(kw)
    return b


def a_turn(**kw) -> aa.TurnResult:
    base = dict(exit_code=0, text="(scripted)", stream_path=None, end_reason=labels4.END_TURN, init=dict(PIN),
                api_errors=[], counters={"oom_kill_delta": 0, "pids_max_delta": 0}, started_at=1.0, ended_at=2.0,
                agent_output=True)
    base.update(kw)
    return aa.TurnResult(**base)


def a_silent_turn(**kw) -> aa.TurnResult:
    return a_turn(exit_code=1, end_reason=labels4.END_ERROR, agent_output=False, **kw)


def a_silent_timeout(**kw) -> aa.TurnResult:
    """A turn that produced no completed agent output and timed out (the host's kill exits 124)."""
    return a_turn(exit_code=124, end_reason=labels4.TIMED_OUT, agent_output=False, **kw)


SILENT_TIMEOUT_ROW = "silent-timeout-before-first-turn"
# Review round 3, W1B3-2 (the gap4 lane lead's ruling; glitch-f3 accepted the stricter reading, 6 Oct 2026): before the
# agent's first turn, an init event that is present and differs from the pin is refused whatever else matches, and
# only a rate-limit pause outranks it. One table-level rule, so its scope lives in one place.
PIN_REFUSAL = "init-differs-before-first-turn"


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

    def test_missing_init_rehearses_a_differing_init_is_refused(self):
        """glitch-f3's ruling (in-plan, 6 Oct 2026; glitch-f3's, not the owner's), both ways, through
        harness_records and route."""
        self.assertEqual(missing_init_problems(test_table()), [])
        src = next(r for r in REAL["rows"] if r["id"] == SILENT_TIMEOUT_ROW)["source"]
        for cite in ("glitch-f3", "A CLI that never printed its init event is harness-side", "refused for a human"):
            self.assertIn(cite, src)

    def test_missing_init_check_can_fail(self):
        def pin_check(op):   # W1B3-2: the pin check is routing.json's pin refusal, no longer the silent row's none_of
            t = test_table()
            if op is None:
                t["pin_refusal"]["outranked_by"] = list(labels4.ROUTES)   # neutralized: every route outranks it
            else:
                t["pin_refusal"]["all_of"][0]["op"] = op
            return t
        # (a) lane decision 5's old rule: a missing init counts as a mismatch, so it is refused
        found = missing_init_problems(pin_check("differs_from_pin"))
        self.assertTrue(any(x.startswith(f"{NO_INIT_TIMEOUT}: refused") for x in found), found)
        # (b) the pin check dropped: a differing init rehearses instead of being refused
        found = missing_init_problems(pin_check(None))
        for field in ("model", "mode", "version"):
            self.assertTrue(any(f"init {field} differs: want refused" in x for x in found), (field, found))
        real = routing.holds

        def blind_to_a_difference(cond, records, table):   # (b) the new op reads a missing init only
            if cond["op"] == "present_differs_from_pin":
                return False
            return real(cond, records, table)
        with mock.patch.object(routing, "holds", blind_to_a_difference):
            found = missing_init_problems(test_table())
        self.assertTrue(any("init mode differs: want refused" in x for x in found), found)


NO_INIT_TIMEOUT = "a silent first-turn timeout with no init event"


def missing_init_problems(table: dict) -> list[str]:
    """glitch-f3's ruling (in-plan, 6 Oct 2026, relayed by the gap4 lane lead; glitch-f3's, not the owner's): a CLI
    that never printed its init event is harness-side, by the same reason as W1B2-1. So before the agent's first
    turn a silent timed-out turn with no init event routes rehearsal, on the silent-timeout row alone (it never
    meets the init-mismatch row, so no tie); one whose init event differs from the pin in model, mode or version
    is refused for a human (a pin mismatch). Built through harness_records, as the driver will, then routed."""
    p = []
    rehearse = (
        (NO_INIT_TIMEOUT, [a_silent_timeout(init=None)]),
        ("a silent error turn, then a silent timeout, neither with an init event",
         [a_silent_turn(init=None), a_silent_timeout(init=None)]),
        ("a silent turn under the pin, then a silent timeout with no init event",
         [a_silent_turn(), a_silent_timeout(init=None)]),
    )
    for name, turns in rehearse:
        rec = aa.harness_records(turns, pin=PIN, box=full_box())
        if rec["init"][-1] is not None:
            p.append(f"{name}: harness_records lost the missing init ({rec['init']})")
        got = try_route(rec, table)
        want = (labels4.REHEARSAL, [SILENT_TIMEOUT_ROW], [SILENT_TIMEOUT_ROW], labels4.BEFORE_FIRST_TURN)
        if isinstance(got, Exception):
            p.append(f"{name}: refused ({got})")
        elif (got["route"], got["rows"], got["matched"], got["phase"]) != want:
            p.append(f"{name}: want {want}, got {(got['route'], got['rows'], got['matched'], got['phase'])}")
    refuse = (
        ("init model differs", [a_silent_timeout(init=dict(PIN, model="not-the-pin"))]),
        ("init mode differs", [a_silent_timeout(init=dict(PIN, permission_mode="default"))]),
        ("init version differs", [a_silent_timeout(init=dict(PIN, version="9.9.9"))]),
        ("init missing on one turn and differing on another",
         [a_silent_turn(init=None), a_silent_timeout(init=dict(PIN, model="not-the-pin"))]),
    )
    for name, turns in refuse:
        got = try_route(aa.harness_records(turns, pin=PIN, box=full_box()), table)
        if not isinstance(got, routing.RoutingRefused) or PIN_REFUSAL not in str(got):
            p.append(f"a silent first-turn timeout whose {name}: want refused ({PIN_REFUSAL}), got {got}")
    return p


OTHER_VERSION = dict(PIN, version="9.9.9")
REFUSED_BY_PIN = "refused by the pin refusal"
# W1B3-2, glitch-f3's ruling: "Test it with every combination the reviewer's probe2.py used: bare, plus
# no-first-agent-turn, plus an API 500, plus a container exit (each refused), and plus a 429 (pause)." Built through
# harness_records, as probe2.py built them; the API 500 that ends in error (probe2's last before-first-turn case) too.
PROBE2_COMBINATIONS = {
    "bare": ([a_silent_timeout(init=OTHER_VERSION)], {}, REFUSED_BY_PIN),
    "plus no-first-agent-turn": ([a_silent_timeout(init=OTHER_VERSION)], {"checker_reasons": [NFAT]}, REFUSED_BY_PIN),
    "plus an API 500": ([a_silent_timeout(init=OTHER_VERSION, api_errors=[{"status": 500, "type": "api_error",
                                                                           "text": None}])], {}, REFUSED_BY_PIN),
    "plus a container exit": ([a_silent_timeout(init=OTHER_VERSION)], {"container_exited": True}, REFUSED_BY_PIN),
    "an API 500 that ended in error": ([a_silent_turn(init=OTHER_VERSION, api_errors=[{"status": 500, "type": "api_error",
                                                                                       "text": None}])], {},
                                       REFUSED_BY_PIN),
    "plus a 429": ([a_silent_timeout(init=OTHER_VERSION, api_errors=[{"status": 429, "type": "rate_limit_error",
                                                                       "text": None}])], {}, labels4.PAUSE),
}


def pin_refusal_problems(table: dict) -> list[str]:
    """W1B3-2: probe2.py's combinations, a differing init before the agent's first turn: each is refused by the pin
    refusal (named in the refusal) whatever else matches, except beside a rate limit, where the pause wins."""
    p = []
    for name, (turns, box, want) in PROBE2_COMBINATIONS.items():
        got = try_route(aa.harness_records(turns, pin=PIN, box=full_box(**box)), table)
        if want == REFUSED_BY_PIN:
            if not isinstance(got, routing.RoutingRefused) or PIN_REFUSAL not in str(got):
                p.append(f"{name}: want refused by {PIN_REFUSAL}, got {got if isinstance(got, Exception) else got['route']}")
        elif isinstance(got, Exception) or (got["route"], got["rows"]) != (want, ["rate-limit"]):
            p.append(f"{name}: want {want} via ['rate-limit'], got {got if isinstance(got, Exception) else got['route']}")
    return p


def pin_refusal_grid_problems(table: dict) -> list[str]:
    """W1B3-2, whatever else matches: every before-first-turn row's witness, given a turn whose init event is present
    and differs from the pin, is refused by the pin refusal, unless its route outranks it (the rate-limit pause); the
    same witness with no init event on that turn routes as the row says (a missing init is never a pin fault before
    the first turn, glitch-f3's fold-3 ruling). A preflight failure cannot have run a turn, so it carries no init."""
    p = []
    outranks = set(table.get("pin_refusal", {}).get("outranked_by", [labels4.PAUSE]))
    for row in table["rows"]:
        if labels4.BEFORE_FIRST_TURN not in row_phases(row):
            continue
        for alt in range(len(row["any_of"])):
            for init in ("differs", "missing"):
                rec, _ = witness(row, alt, labels4.BEFORE_FIRST_TURN, table)
                if not rec["preflight"]["ok"]:
                    continue
                if rec["ledger"]["turns"] == 0:
                    silent_turn(rec)
                rec["init"][-1] = init_of(OTHER_VERSION) if init == "differs" else None
                got = try_route(rec, table)
                if init == "differs" and row["route"] not in outranks:
                    if not isinstance(got, routing.RoutingRefused) or PIN_REFUSAL not in str(got):
                        p.append(f"{row['id']}[{alt}] init differs: want refused by {PIN_REFUSAL}, got "
                                 f"{got if isinstance(got, Exception) else got['route']}")
                elif isinstance(got, Exception) or got["route"] != row["route"] or row["id"] not in got["rows"]:
                    p.append(f"{row['id']}[{alt}] init {init}: want {row['route']} via {row['id']}, got "
                             f"{got if isinstance(got, Exception) else (got['route'], got['rows'])}")
    return p


class TestPinRefusal(unittest.TestCase):
    """Review round 3, W1B3-2 (the gap4 lane lead's ruling; glitch-f3 accepted the stricter reading, 6 Oct 2026;
    glitch-f3's, not the owner's)."""

    def test_probe2_combinations(self):
        self.assertEqual(pin_refusal_problems(test_table()), [])

    def test_whatever_else_matches(self):
        self.assertEqual(pin_refusal_grid_problems(test_table()), [])

    def test_the_pin_check_lives_in_one_place(self):
        """The scope is one table-level rule: no row reads the init with present_differs_from_pin, and the rule's
        conditions sit on one line of routing.json, so narrowing it is a one-line change."""
        self.assertEqual(one_place_problems(REAL), [])
        with open(routing.TABLE_PATH, encoding="utf-8") as fh:
            lines = [x for x in fh if "present_differs_from_pin" in x]
        self.assertEqual(len(lines), 1, lines)
        self.assertIn('"all_of"', lines[0])

    def test_narrowing_to_timed_out_ends_is_one_condition(self):
        """glitch-f3 may narrow the refusal to timed-out ends: one condition appended to its all_of. Then the API 500
        that ended in error rehearses, and the timed-out combinations stay refused."""
        t = test_table()
        t["pin_refusal"]["all_of"].append({"path": "ledger.end", "op": "eq", "value": labels4.TIMED_OUT})
        self.assertEqual(routing.check_table(t), [])
        self.assertEqual(pin_refusal_problems(t), ["an API 500 that ended in error: want refused by "
                                                   f"{PIN_REFUSAL}, got rehearsal"])

    def test_pin_refusal_check_can_fail(self):
        """Each of probe2's combinations has a mutant that turns it red (glitch-f3's ruling on W1B3-2)."""
        refused = ("bare", "plus no-first-agent-turn", "plus an API 500", "plus a container exit",
                   "an API 500 that ended in error")
        t = test_table()
        t["pin_refusal"]["outranked_by"] = list(labels4.ROUTES)        # the refusal neutralized
        found = pin_refusal_problems(t)
        for name in refused:
            self.assertTrue(any(x.startswith(f"{name}: want refused") for x in found), (name, found))
        t = test_table()                                               # the fold-3 table: the check a none_of on one row
        t["pin_refusal"]["outranked_by"] = list(labels4.ROUTES)
        next(r for r in t["rows"] if r["id"] == SILENT_TIMEOUT_ROW)["none_of"] = [
            {"path": "init", "op": "present_differs_from_pin"}]
        found = pin_refusal_problems(t) + scenario_problems(t)
        for name in ("plus no-first-agent-turn", "plus an API 500", "plus a container exit"):   # the review's finding
            self.assertTrue(any(x.startswith(f"{name}: want refused by {PIN_REFUSAL}, got rehearsal") for x in found),
                            (name, found))
        self.assertTrue(any(x.startswith("W1B3-2: a differing init plus no-first-agent-turn -> refused: want refused")
                            for x in found), found)
        t = test_table()
        t["pin_refusal"]["outranked_by"] = []                          # the pause exception dropped
        found = pin_refusal_problems(t) + scenario_problems(t)
        self.assertTrue(any(x.startswith("plus a 429: want pause") for x in found), found)
        self.assertTrue(any(x.startswith("W1B3-2: a differing init plus a 429 -> pause: refused") for x in found), found)
        t = test_table()
        t["pin_refusal"]["all_of"][0]["op"] = "differs_from_pin"      # a missing init taken for a pin fault
        self.assertTrue(any("init missing: want" in x for x in pin_refusal_grid_problems(t)))
        with mock.patch.object(routing, "pin_refusal_holds", lambda records, table: False):
            self.assertTrue(any("init differs: want refused" in x for x in pin_refusal_grid_problems(test_table())))

    def test_one_place_check_can_fail(self):
        t = copy.deepcopy(REAL)
        next(r for r in t["rows"] if r["id"] == SILENT_TIMEOUT_ROW)["none_of"] = [
            {"path": "init", "op": "present_differs_from_pin"}]
        self.assertEqual(one_place_problems(t), [f"{SILENT_TIMEOUT_ROW}: none_of reads present_differs_from_pin"])

    def test_the_rule_is_checked(self):
        """routing.json's pin refusal is a closed rule: its phase is before the first turn (after it, the plan routes a
        differing init harness-error), its conditions read harness records, and only a route that outranks rehearsal
        may outrank it."""
        bad = {
            "after the first turn": lambda r: r.update(when=labels4.AFTER_FIRST_TURN),
            "any time": lambda r: r.update(when=labels4.ANY_TIME),
            "no condition": lambda r: r.update(all_of=[]),
            "a text-derived count": lambda r: r["all_of"].append({"path": "events.outside_reach", "op": "gt", "value": 0}),
            "an unknown op": lambda r: r["all_of"][0].update(op="looks_wrong"),
            "graded outranks it": lambda r: r.update(outranked_by=[labels4.PAUSE, labels4.GRADED]),
            "rehearsal outranks it": lambda r: r.update(outranked_by=[labels4.REHEARSAL]),
            "a route that is no route": lambda r: r.update(outranked_by=["success"]),
            "no source": lambda r: r.update(source=""),
            "an extra key": lambda r: r.update(route=labels4.REHEARSAL),
            "an id a row has": lambda r: r.update(id=SILENT_TIMEOUT_ROW),
        }
        for name, edit in bad.items():
            t = copy.deepcopy(REAL)
            edit(t["pin_refusal"])
            self.assertTrue(any("pin_refusal" in x for x in routing.check_table(t)), name)
        t = copy.deepcopy(REAL)
        del t["pin_refusal"]
        self.assertIn("missing pin_refusal", routing.check_table(t))


def one_place_problems(table: dict) -> list[str]:
    """Every condition reading the init with present_differs_from_pin, outside the pin refusal (W1B3-2: one place)."""
    return [f"{x.get('id')}: {g} reads present_differs_from_pin" for x in table["rows"] + table["annotations"]
            for g in ("all_of", "any_of", "none_of") for c in x.get(g, [])
            if isinstance(c, dict) and c.get("op") == "present_differs_from_pin"]


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
        err[tail] = table["rate_limit_markers"][TEST_HARNESS][tail][0]
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
        r["init"] = [init_of(r["pin"]) for _ in range(n)]
    return f


def _reach(n=1):
    return _set("events.outside_reach", n)


def _differs(value="9.9.9", field="version"):
    """The last turn's init event: present and differing from the pin in `field`, or None (no init event)."""
    return lambda r: r["init"].__setitem__(-1, None if value is None else dict(init_of(r["pin"]), **{field: value}))


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
    "silent timeout with an init mismatch -> refused (W1B2-1)": Sc(_sc(B, [silent_timeout, lambda r: r["init"].__setitem__(0, dict(INIT, model="x"))]),
                                                                   REFUSED, None),
    # glitch-f3's ruling (6 Oct 2026; glitch-f3's, not the owner's): a CLI that never printed its init event is
    # harness-side, so a silent first-turn timeout with no init event rehearses; one whose init differs is refused
    "silent timeout with no init event -> rehearsal (glitch-f3, fold 3)":
        Sc(_sc(B, [silent_timeout, lambda r: r["init"].__setitem__(0, None)]), "rehearsal",
           ["silent-timeout-before-first-turn"], ["silent-timeout-before-first-turn"]),
    "silent timeout with an init mode mismatch -> refused (glitch-f3, fold 3)":
        Sc(_sc(B, [silent_timeout, lambda r: r["init"].__setitem__(0, dict(INIT, permission_mode="default"))]), REFUSED, None),
    "silent timeout with an init version mismatch -> refused (glitch-f3, fold 3)":
        Sc(_sc(B, [silent_timeout, lambda r: r["init"].__setitem__(0, dict(INIT, version="9.9.9"))]), REFUSED, None),
    "a silent turn with no init, then a silent timeout under another model -> refused (glitch-f3, fold 3)":
        Sc(_sc(B, [silent_turn, silent_timeout, lambda r: r["init"].__setitem__(0, None),
                   lambda r: r["init"].__setitem__(1, dict(INIT, model="x"))]), REFUSED, None),
    # W1B3-2 (the gap4 lane lead's ruling; glitch-f3 accepted the stricter reading, 6 Oct 2026): before the first turn a
    # present init that differs from the pin is refused whatever else matches; only a rate-limit pause outranks it
    "W1B3-2: a differing init, bare -> refused": Sc(_sc(B, [silent_timeout, _differs()]), REFUSED, None),
    "W1B3-2: a differing init plus no-first-agent-turn -> refused":
        Sc(_sc(B, [silent_timeout, _set("checker_reasons", [NFAT]), _differs()]), REFUSED, None),
    "W1B3-2: a differing init plus an API 500 -> refused": Sc(_sc(B, [silent_timeout, _apis(E500), _differs()]), REFUSED, None),
    "W1B3-2: a differing init plus a container exit -> refused":
        Sc(_sc(B, [silent_timeout, _set("exit.container_exited", True), _differs()]), REFUSED, None),
    "W1B3-2: a differing init plus a 429 -> pause": Sc(_sc(B, [silent_timeout, _rate, _differs()]), "pause", ["rate-limit"],
                                                       ["api-error-before-first-turn", "silent-timeout-before-first-turn",
                                                        "rate-limit"]),
    "W1B3-2: a differing init on an API 500 that ended in error -> refused (the stricter reading)":
        Sc(_sc(B, [_apis(E500), _differs()]), REFUSED, None),
    "W1B3-2: a differing init plus a usage limit in the error text -> pause":
        Sc(_sc(B, [_apis(EUSAGE), _differs()]), "pause", ["rate-limit"], ["api-error-before-first-turn", "rate-limit"]),
    "W1B3-2: a missing init beside an API 500 -> rehearsal": Sc(_sc(B, [_apis(E500), _differs(None)]), "rehearsal",
                                                               ["api-error-before-first-turn"], ["api-error-before-first-turn"]),
    "a silent error turn, then a silent timeout": Sc(_sc(B, [silent_turn, silent_timeout]), "rehearsal", ["silent-timeout-before-first-turn"]),
    "a timeout after completed output grades (glitch-f3)": Sc(_sc(A, [_multi_turn(1), silent_timeout]), "graded", ["timed-out"]),
    "one turn with output that timed out grades (glitch-f3)": Sc(_sc(B, [output_timeout]), "graded", ["timed-out"]),
    # W1B2-1: routing's own consistency check binds first_turn_started to completed agent output, whoever built
    # the records (a driver writing 3fcab58d's rule, or the reverse, is refused, never routed)
    "a silent timeout recorded as the first turn started -> refused (W1B2-1)":
        Sc(_sc(B, [silent_timeout, lambda r: r["ledger"].__setitem__("first_turn_started", True)]), REFUSED, None, None, None),
    "completed output recorded as no first turn -> refused (W1B2-1)":
        Sc(_sc(A, [lambda r: r["ledger"].__setitem__("first_turn_started", False)]), REFUSED, None, None, None),
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
    "init model differs": Sc(_sc(A, [lambda r: r["init"].__setitem__(0, dict(INIT, model="x"))]), "harness-error", ["init-mismatch"]),
    "init mode differs": Sc(_sc(A, [lambda r: r["init"].__setitem__(0, dict(INIT, permission_mode="default"))]), "harness-error", ["init-mismatch"]),
    "init version differs": Sc(_sc(A, [lambda r: r["init"].__setitem__(1, dict(INIT, version="9.9.9"))]), "harness-error", ["init-mismatch"]),
    "init event missing": Sc(_sc(A, [lambda r: r["init"].__setitem__(0, None)]), "harness-error", ["init-mismatch"]),
    "mismatch on the last turn of an otherwise graded take": Sc(_sc(A, [_multi_turn(4), _mismatch]), "harness-error", ["init-mismatch"]),
    # pre-freeze review 1, MAJOR 5 (lane pf1-l2a): the agent's own exit is graded, its id an agent event
    "non-zero exec exit, nothing else": Sc(_sc(A, [lambda r: r["exit"]["exec_codes"].__setitem__(0, 1)]), "graded",
                                           ["nonzero-exec-exit", "end-turn"]),
    "operator reason after first turn": Sc(_sc(A, [_set("checker_reasons", [READERS])]), "harness-error", ["operator-reason-after-first-turn"]),
    "operator diff after first turn": Sc(_sc(A, [_set("operator.unexplained_diffs", 2)]), "harness-error", ["operator-diff-unexplained-after-first-turn"]),
    "finalize abort after first turn": Sc(_sc(A, [_set("ledger.finalize_abort", True)]), "aborted", ["finalize-abort-after-first-turn"]),  # pf2 L-A1, glitch-45's ruling 2
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
                                                                     ["container-exit-after-first-turn"], None, [OR], True),
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
    "an API error with no turn (lane w1b decision)": Sc(_sc(B, [lambda r: r.__setitem__("api_errors", [dict(E500)])]), REFUSED,
                                                        None, None, None),
    # W1B2-7: one turn can meet several API errors; they are all read, and no count of them is refused
    "a 529 then a 429 in one turn -> pause (W1B2-7)": Sc(_sc(A, [_multi_turn(1), _apis(E529, E429), _end_error(1)]), "pause",
                                                       ["rate-limit"], ["rate-limit", "api-error-after-first-turn"]),
    "a 529 then a 429 in the first, silent turn -> pause (W1B2-7)": Sc(_sc(B, [_apis(E529, E429)]), "pause", ["rate-limit"],
                                                                     ["api-error-before-first-turn", "rate-limit"]),
    "three API errors in two turns, none a marker": Sc(_sc(A, [_apis(E500, E529, E500), _end_error(1)]), "harness-error",
                                                       ["api-error-after-first-turn"]),
    # W1B2-8: no-first-agent-turn means "before the first turn"; after it started, the records disagree
    "no-first-agent-turn before the first turn -> rehearsal": Sc(_sc(B, [_set("checker_reasons", [NFAT])]), "rehearsal",
                                                                 ["operator-reason-before-first-turn"]),
    "no-first-agent-turn after the first turn -> refused (W1B2-8)": Sc(_sc(A, [_set("checker_reasons", [NFAT])]), REFUSED, None),
    "no-first-agent-turn beside another reason after the first turn -> refused (W1B2-8)":
        Sc(_sc(A, [_set("checker_reasons", [READERS, NFAT])]), REFUSED, None),
    "no-first-agent-turn after a timeout with output -> refused (W1B2-8)": Sc(_sc(B, [output_timeout, _set("checker_reasons", [NFAT])]),
                                                                            REFUSED, None),
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
                     ("seam", seam_problems), ("scenarios", scenario_problems), ("tie", tie_problems),
                     ("pin refusal", pin_refusal_problems), ("pin refusal grid", pin_refusal_grid_problems)):
        p += _guarded(name, fn, table)
    return p


# ------------------------------------------------------------------------ 5. the mutation sweep
_CONDITION_MUTANT = {"eq": ("value", "__mutated__"), "ne": ("op", "eq"), "gt": ("value", 10 ** 9),
                     "truthy": ("op", "falsy"), "falsy": ("op", "truthy"), "not_null": ("op", "is_null"),
                     "is_null": ("op", "not_null"), "nonempty": ("op", "empty"), "empty": ("op", "nonempty"),
                     "in_operator_reasons": ("op", "is_null"), "in_checker_events": ("op", "is_null"),
                     "in_rate_limit_markers": ("op", "is_null"),
                     "has": ("value", "__mutated__"),            # glitch-b5's ruling 3 (17 Oct 2026)
                     "differs_from_pin": ("op", "is_null"), "nonzero_outside_timeout": ("op", "is_null"),
                     # glitch-f3's ruling (fold 3): the mutant is lane decision 5's old rule, a missing init a mismatch
                     "present_differs_from_pin": ("op", "differs_from_pin")}


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
    for key, values in table["rate_limit_markers"][TEST_HARNESS].items():
        if key in ("source", "reset_wait"):   # not marker lists (reset_wait: item 1)
            continue
        t = copy.deepcopy(table)
        del t["rate_limit_markers"][TEST_HARNESS][key]
        yield f"rate_limit_markers: {key} deleted", t
        for j, v in enumerate(values):
            t = copy.deepcopy(table)
            t["rate_limit_markers"][TEST_HARNESS][key][j] = _other(v)
            yield f"rate_limit_markers: {key}[{j}] {v!r} -> {_other(v)!r}", t
    t = copy.deepcopy(table)
    t["rate_limit_markers"][TEST_HARNESS]["code"] = t["rate_limit_markers"][TEST_HARNESS].pop("status")
    yield "rate_limit_markers: status renamed to a non-API-error key", t
    for j, eid in enumerate(table["checker_reasons_become_events"]["ids"]):   # W1B2-2
        t = copy.deepcopy(table)
        del t["checker_reasons_become_events"]["ids"][j]
        yield f"checker_reasons_become_events: {eid} dropped", t
        t = copy.deepcopy(table)                                               # W1B2-10
        t["operator_reasons"].append(eid)
        yield f"operator_reasons: event id {eid} added", t
    for j, rid in enumerate(table["reasons_only_before_first_turn"]["ids"]):   # W1B2-8
        t = copy.deepcopy(table)
        t["reasons_only_before_first_turn"]["ids"][j] = any_phase_reason(table)
        yield f"reasons_only_before_first_turn: {rid} -> {any_phase_reason(table)}", t
    t = copy.deepcopy(table)                                                   # W1B2-10
    t["driver_decided_reasons"]["ids"].append("not-an-operator-reason")
    yield "driver_decided_reasons: an id outside operator_reasons", t
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
    rule = table["pin_refusal"]                                                # W1B3-2
    t = copy.deepcopy(table)
    del t["pin_refusal"]
    yield "pin_refusal: removed", t
    for other in labels4.PHASES:
        if other != rule["when"]:
            t = copy.deepcopy(table)
            t["pin_refusal"]["when"] = other
            yield f"pin_refusal: phase -> {other}", t
    for j, c in enumerate(rule["all_of"]):
        key, val = _CONDITION_MUTANT[c["op"]]
        t = copy.deepcopy(table)
        t["pin_refusal"]["all_of"][j][key] = val
        yield f"pin_refusal: all_of[{j}] {c['op']} mutated", t
        t = copy.deepcopy(table)
        del t["pin_refusal"]["all_of"][j]
        yield f"pin_refusal: all_of[{j}] {c['op']} deleted", t
    for name, outranks in (("emptied", []), ("every route", list(labels4.ROUTES)), ("rehearsal", [labels4.REHEARSAL])):
        t = copy.deepcopy(table)
        t["pin_refusal"]["outranked_by"] = outranks
        yield f"pin_refusal: outranked_by {name}", t
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


# What each cap counts, as its source must say it (glitch-f3's rulings: rehearsals one by one, fold 3; pauses by their
# usage-window events, the pauses that share one reset counting once, W1B3-5).
CAP_COUNTS = {labels4.REHEARSAL: ("rehearsals committed in the half-cell",),
              labels4.PAUSE: ("usage-window events", "pauses that share one reset count once", "W1B3-5")}


def cap_unit_problems(table: dict) -> list[str]:
    """glitch-f3's cap rulings, stated where the caps live: each of the rehearsal and pause sources cites the
    ruling, names round 4's half-cell (arm, task, half, model) as round 3's cell, says what is counted (rehearsals one
    by one; pauses by usage-window event, W1B3-5) and that the loop goes on, no longer calls it open, and no longer
    says the key kept its old name (W1B3-4)."""
    p = []
    for route in (labels4.REHEARSAL, labels4.PAUSE):
        src = table["caps"][route]["source"]
        for cite in ("glitch-f3's ruling", "(arm, task, half, model)", "the loop goes on") + CAP_COUNTS[route]:
            if cite not in src:
                p.append(f"{route}: the cap's source does not say {cite!r}")
        if "open question" in src:
            p.append(f"{route}: the cap's unit is still left open in its source")
        if "The key keeps its name" in src:
            p.append(f"{route}: the cap's source still says the key kept its old name (W1B3-4)")
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

    def test_operator_reasons_and_event_ids_are_disjoint(self):
        """W1B2-10 (and W1B2-2): an event id is never an operator reason, or it would route a rehearsal or a
        harness-error where the plan says graded as usual, masked."""
        self.assertFalse(set(REAL["operator_reasons"]) & set(REAL["checker_reasons_become_events"]["ids"]))
        for eid in REAL["checker_reasons_become_events"]["ids"]:
            t = copy.deepcopy(REAL)
            t["operator_reasons"].append(eid)   # the mutant
            self.assertTrue(any("an event is never an operator reason" in x for x in routing.check_table(t)), eid)

    def test_driver_decided_reasons_route_by_the_generic_rule(self):
        """W1B2-10: round 3's driver-decided reasons need no rule of their own: each is an operator reason, so a
        rehearsal before the first turn and harness-error after it."""
        t = test_table()
        ids = t["driver_decided_reasons"]["ids"]
        self.assertLessEqual(set(ids), set(t["operator_reasons"]))
        for rid in ids:
            for phase, want, row in ((B, labels4.REHEARSAL, "operator-reason-before-first-turn"),
                                     (A, labels4.HARNESS_ERROR, "operator-reason-after-first-turn")):
                rec = baseline(phase)
                rec["checker_reasons"] = [rid]
                got = routing.route(rec, t)
                self.assertEqual((got["route"], got["rows"]), (want, [row]), (rid, phase))
        bad = copy.deepcopy(REAL)
        bad["driver_decided_reasons"]["ids"].append("not-an-operator-reason")   # the mutant
        self.assertTrue(any("driver_decided_reasons" in x for x in routing.check_table(bad)))
        bad = copy.deepcopy(REAL)
        bad["reasons_only_before_first_turn"]["ids"].append("not-an-operator-reason")
        self.assertTrue(any("reasons_only_before_first_turn" in x for x in routing.check_table(bad)))

    def test_rate_limit_markers_status_is_ruled(self):
        """W1B2-6: the markers' status says glitch-f3 ruled them and names the CP6 walk check still to do."""
        status = REAL["rate_limit_markers_status"]
        self.assertTrue(status.startswith("RULED"), status)
        for cite in ("glitch-f3", "6 Oct 2026",
                     "a replay of a real recorded usage-limit refusal through harness_records", "CP6"):
            self.assertIn(cite, status)
        for bad in (None, "", 3):
            t = copy.deepcopy(REAL)
            t["rate_limit_markers_status"] = bad
            self.assertTrue(any("rate_limit_markers_status" in x for x in routing.check_table(t)), bad)
        t = copy.deepcopy(REAL)
        del t["rate_limit_markers_status"]
        self.assertIn("missing rate_limit_markers_status", routing.check_table(t))

    def test_cap_units_are_glitch_f3s_ruling(self):
        """glitch-f3's ruling (in-plan, 6 Oct 2026; glitch-f3's, not the owner's): the rehearsal and pause caps count
        that route's committed outcomes per half-cell, round 3's unit; the sources say so and leave nothing open."""
        self.assertEqual(cap_unit_problems(REAL), [])

    def test_cap_unit_check_can_fail(self):
        for route in (labels4.REHEARSAL, labels4.PAUSE):
            t = copy.deepcopy(REAL)
            t["caps"][route]["source"] = t["caps"][route]["source"].split(" Unit")[0]   # the unit sentence dropped
            self.assertTrue(any(x.startswith(route) for x in cap_unit_problems(t)), route)
            t = copy.deepcopy(REAL)
            t["caps"][route]["source"] += " Unit: still an open question in the lane report."
            self.assertTrue(any("left open" in x for x in cap_unit_problems(t)), route)
            t = copy.deepcopy(REAL)                                    # W1B3-4: the stale sentence back
            t["caps"][route]["source"] += (" The key keeps its name, reruns_per_half_cell: for rehearsal and pause its "
                                           "value is that count.")
            self.assertTrue(any("kept its old name" in x for x in cap_unit_problems(t)), route)
        t = copy.deepcopy(REAL)                                        # W1B3-5: the pause's unit back to each take
        t["caps"][labels4.PAUSE]["source"] = t["caps"][labels4.PAUSE]["source"].replace(
            "the pauses that share one reset count once", "every pause counts")
        self.assertTrue(any("pauses that share one reset count once" in x for x in cap_unit_problems(t)))

    def test_no_first_agent_turn_after_the_first_turn_is_refused(self):
        """W1B2-8: the reason says "before the first turn"; carried after it started, the records disagree."""
        rec = baseline(A)
        rec["checker_reasons"] = [NFAT]
        with self.assertRaisesRegex(routing.RoutingRefused, "mean before the agent's first turn"):
            routing.route(rec, test_table())
        real = routing.check_records

        def lenient(records, table):   # the mutant: the phase check dropped
            return [x for x in real(records, table) if "mean before the agent's first turn" not in x]
        with mock.patch.object(routing, "check_records", lenient):
            self.assertTrue(any("no-first-agent-turn after" in x for x in scenario_problems(test_table())))

    def test_rate_limit_marker_keys_are_api_error_fields(self):
        """W1B-6."""
        t = copy.deepcopy(REAL)
        t["rate_limit_markers"][TEST_HARNESS]["code"] = [429]
        self.assertTrue(any("not an API-error field" in x for x in routing.check_table(t)))

    def test_text_markers_are_non_empty_lower_case_strings(self):
        """Round 3's bounded search lowercases the error text only, so an upper-case marker could never match,
        and an empty one would match at every word boundary."""
        self.assertEqual(REAL["rate_limit_markers"][TEST_HARNESS]["text"], [m.lower() for m in REAL["rate_limit_markers"][TEST_HARNESS]["text"]])
        for bad in ("Rate Limit", "", 429, None):
            t = copy.deepcopy(REAL)
            t["rate_limit_markers"][TEST_HARNESS]["text"] = ["rate limit", bad]
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

    def test_real_table_refuses_every_take_whose_pin_is_not_registered(self):
        """W1B-10: no driver-supplied pin is trusted. CP5 registered arm A's three profiles alone (TestCP5ArmAProfiles),
        so a pin of an unregistered model, or a registered model under another mode or version, is still refused."""
        with self.assertRaisesRegex(routing.RoutingRefused, "pre-registered profile"):
            routing.route(baseline(A), REAL)          # the test pin's model is not one of arm A's
        for field, value in (("permission_mode", "default"), ("version", "2.1.297")):
            pin = {"harness": CP5_HARNESS, "model": CP5_MODELS[0], "permission_mode": CP5_MODE, "version": CP5_VERSION}
            pin[field] = value
            with self.assertRaisesRegex(routing.RoutingRefused, "pre-registered profile", msg=field):
                routing.route(baseline(A, pin), REAL)


CHECK_TAKE = "evals/gap-study-3/check_take.py"
_REASON_LINE = re.compile(r"[\"']\[([a-z][a-z-]*)\] ")


def emitted_at_problems(table: dict, lines: list[str]) -> list[str]:
    """W1B2-10: each emitted_at citation names check_take.py lines that emit its id (its `"[id] ` prefix, or
    for no-first-agent-turn the NO_FIRST_AGENT_TURN constant), and every reason-id line is cited under its id.
    Only the lines this lane may read are kept (reason-id lines and 80-95); every other line is dropped unread."""
    readable = {n: x for n, x in enumerate(lines, 1) if _REASON_LINE.search(x) or 80 <= n <= 95}
    cites = {rid: src["emitted_at"] for rid, src in table["operator_reason_sources"].items()}
    cites.update(table["checker_reasons_become_events"]["emitted_at"])
    p, cited = [], {}
    for rid, cite in cites.items():
        path, _, nums = cite.partition(":")
        if path != CHECK_TAKE:
            p.append(f"{rid}: cites {path}, not {CHECK_TAKE}")
            continue
        for n in (int(x) for x in nums.split(",")):
            line = readable.get(n)
            if line is None:
                p.append(f"{rid}: check_take.py:{n} is not a reason-id line")
            elif f'"[{rid}] ' in line or f"'[{rid}] " in line or line.strip() == f'NO_FIRST_AGENT_TURN = "{rid}"':
                cited[n] = rid
            else:
                p.append(f"{rid}: check_take.py:{n} does not emit it")
    for n, line in readable.items():
        for rid in _REASON_LINE.findall(line):
            if cited.get(n) != rid:
                p.append(f"check_take.py:{n} emits [{rid}] and is not cited under it")
    return p


def _print_text(lines: list[str]) -> str:
    """The literal text of a print(f"..." f"...") call spread over `lines` (its formatted values dropped)."""
    call = ast.parse("".join(x.strip() for x in lines)).body[0].value
    return "".join(v.value for v in call.args[0].values if isinstance(v, ast.Constant))


class TestCapKeyNames(unittest.TestCase):
    """glitch-f3 (6 Oct 2026): rehearsal and pause count events per half-cell under events_per_half_cell; the old
    name reruns_per_half_cell, whose meaning changed, is refused there."""

    def test_the_real_table_uses_the_new_name(self):
        for r in (labels4.REHEARSAL, labels4.PAUSE):
            self.assertIn("events_per_half_cell", REAL["caps"][r])
            self.assertNotIn("reruns_per_half_cell", REAL["caps"][r])
        self.assertIn("reruns_per_half_cell", REAL["caps"][labels4.HARNESS_ERROR])

    def test_the_old_name_is_refused(self):
        for r in (labels4.REHEARSAL, labels4.PAUSE):
            t = copy.deepcopy(REAL)
            t["caps"][r]["reruns_per_half_cell"] = t["caps"][r].pop("events_per_half_cell")
            got = routing.check_table(t)
            self.assertTrue(any("carries reruns_per_half_cell" in g for g in got), (r, got))
            self.assertTrue(any("has no events_per_half_cell" in g for g in got), (r, got))


# Round 4's named operator-reason additions, typed once (TestRound4Additions binds each to its ruling and to the
# round-4 checker line that emits it; TestRound3Sources keeps round 3's ids re-derived beside them).
ROUND4_ADDED_REASONS = ("harness-condition-violated", "transcript-unreadable",    # + glitch-b5, 16 Oct 2026
                        "subagent-records",                                        # + the Agent parity ruling
                        "nested-agent",                                            # + W-3b (glitch-b5, 16 Oct)
                        "transcript-mismatch",                                     # + pf1-l3 (MAJOR 7, 24 Oct)
                        "nested-agent-session", "subagent-unbound",                # + pf2 L-A1 (MAJOR 1, 29 Oct)
                        "driver-record-fault")                                     # + its review, 29 Oct
CHECK_TAKE4 = "evals/gap-study-4/check_take.py"


class TestRound4Additions(unittest.TestCase):
    """glitch-6b's ruling (15 Oct 2026; Javier approved the steer-off): `harness-condition-violated` is an operator
    reason with a round-4 source. A harness condition failed (the bash-first steer reached the agent with the switch
    off), which is not the agent's behaviour, so it routes by the generic operator-reason rows: harness-error after
    the agent's first turn (and a rehearsal before it, as every operator reason does)."""

    HCV = "harness-condition-violated"

    def test_the_addition_is_listed_with_its_ruling(self):
        add = REAL["operator_reasons_round4"]
        self.assertEqual(add["ids"], list(ROUND4_ADDED_REASONS))
        self.assertIn(self.HCV, REAL["operator_reasons"])
        self.assertNotIn(self.HCV, REAL["operator_reason_sources"])
        src = add["sources"][self.HCV]
        for cite in ("glitch-6b", "15 Oct 2026", "steer"):
            self.assertIn(cite, src["ruling"])
        self.assertTrue(src["meaning"])
        self.assertEqual(src["emitted_at"], CHECK_TAKE4)

    def test_round_4s_checker_emits_it(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        with open(os.path.join(root, CHECK_TAKE4), encoding="utf-8") as f:
            text = f.read()
        self.assertIn(f'HARNESS_CONDITION_VIOLATED = "{self.HCV}"', text)
        self.assertIn('f"[{HARNESS_CONDITION_VIOLATED}] ', text)

    def test_it_routes_harness_error_after_the_first_turn(self):
        t = test_table()
        for phase, want, row in ((A, labels4.HARNESS_ERROR, "operator-reason-after-first-turn"),
                                 (B, labels4.REHEARSAL, "operator-reason-before-first-turn")):
            rec = baseline(phase)
            rec["checker_reasons"] = [self.HCV]
            got = routing.route(rec, t)
            self.assertEqual((got["route"], got["rows"]), (want, [row]), phase)

    def test_transcript_unreadable_is_listed_emitted_and_routed(self):
        """glitch-b5's ruling on review r8 (16 Oct 2026): transcript-unreadable, routed like harness-condition-violated."""
        tu = "transcript-unreadable"
        src = REAL["operator_reasons_round4"]["sources"][tu]
        for cite in ("glitch-b5", "16 Oct 2026", "U+2028", "harness-condition-violated"):
            self.assertIn(cite, src["ruling"])
        self.assertEqual(src["emitted_at"], CHECK_TAKE4)
        self.assertNotIn(tu, REAL["operator_reason_sources"])
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        with open(os.path.join(root, CHECK_TAKE4), encoding="utf-8") as f:
            text = f.read()
        self.assertIn(f'TRANSCRIPT_UNREADABLE = "{tu}"', text)
        self.assertIn('f"[{TRANSCRIPT_UNREADABLE}] ', text)
        t = test_table()
        for phase, want, row in ((A, labels4.HARNESS_ERROR, "operator-reason-after-first-turn"),
                                 (B, labels4.REHEARSAL, "operator-reason-before-first-turn")):
            rec = baseline(phase)
            rec["checker_reasons"] = [tu]
            got = routing.route(rec, t)
            self.assertEqual((got["route"], got["rows"]), (want, [row]), phase)

    def test_subagent_records_is_listed_emitted_and_routed(self):
        """glitch-b5's Agent parity ruling (16 Oct 2026): subagent-records, routed like harness-condition-violated."""
        sr = "subagent-records"
        src = REAL["operator_reasons_round4"]["sources"][sr]
        for cite in ("glitch-b5", "16 Oct 2026", "w083", "harness-condition-violated"):
            self.assertIn(cite, src["ruling"])
        self.assertEqual(src["emitted_at"], CHECK_TAKE4)
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        with open(os.path.join(root, CHECK_TAKE4), encoding="utf-8") as f:
            text = f.read()
        self.assertIn(f'SUBAGENT_RECORDS = "{sr}"', text)
        self.assertIn('f"[{SUBAGENT_RECORDS}] ', text)
        t = test_table()
        for phase, want, row in ((A, labels4.HARNESS_ERROR, "operator-reason-after-first-turn"),
                                 (B, labels4.REHEARSAL, "operator-reason-before-first-turn")):
            rec = baseline(phase)
            rec["checker_reasons"] = [sr]
            got = routing.route(rec, t)
            self.assertEqual((got["route"], got["rows"]), (want, [row]), phase)

    def test_transcript_mismatch_is_listed_emitted_and_routed_aborted(self):
        """Fold plan prefreeze-1, MAJOR 7 (24 Oct 2026): transcript-mismatch, by its own row: aborted after the agent's
        first turn (never re-run: the agent can cause it), outranking the generic operator-reason row; beside
        harness-condition-violated, glitch-b5's ruling 3 holds (harness-error, its none_of, as cgroup-kill's); a
        rehearsal before the first turn by the generic row."""
        tm = "transcript-mismatch"
        src = REAL["operator_reasons_round4"]["sources"][tm]
        for cite in ("prefreeze-1", "24 Oct 2026", "MAJOR 7", "never re-run", "aborted"):
            self.assertIn(cite, src["ruling"])
        self.assertEqual(src["emitted_at"], CHECK_TAKE4)
        self.assertNotIn(tm, REAL["operator_reason_sources"])
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        with open(os.path.join(root, CHECK_TAKE4), encoding="utf-8") as f:
            text = f.read()
        self.assertIn(f'TRANSCRIPT_MISMATCH = "{tm}"', text)
        self.assertIn('f"[{TRANSCRIPT_MISMATCH}] ', text)
        rows = [r for r in REAL["rows"] if r["id"] == tm]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["when"], rows[0]["route"], rows[0]["any_of"], rows[0].get("none_of")),
                         ("after-first-turn", labels4.ABORTED,
                          [{"path": "checker_reasons", "op": "has", "value": tm}],
                          [{"path": "checker_reasons", "op": "has", "value": self.HCV}]))
        t = test_table()
        for phase, reasons, want, row in ((A, [tm], labels4.ABORTED, [tm]),
                                          (A, [tm, "session-binding"], labels4.ABORTED, [tm]),
                                          (A, [tm, self.HCV], labels4.HARNESS_ERROR,
                                           ["operator-reason-after-first-turn"]),
                                          (B, [tm], labels4.REHEARSAL, ["operator-reason-before-first-turn"])):
            rec = baseline(phase)
            rec["checker_reasons"] = list(reasons)
            got = routing.route(rec, t)
            self.assertEqual((got["route"], got["rows"]), (want, row), (phase, reasons))
            if want == labels4.ABORTED:
                self.assertEqual(got["cap"]["reruns_per_slot"], 0)
        # witness: without the row, the same records route harness-error (re-run)
        t2 = copy.deepcopy(t)
        t2["rows"] = [r for r in t2["rows"] if r["id"] != tm]
        rec = baseline(A)
        rec["checker_reasons"] = [tm]
        self.assertEqual(routing.route(rec, t2)["route"], labels4.HARNESS_ERROR)

    def test_nested_agent_is_listed_emitted_and_routed(self):
        """glitch-b5's pre-freeze ruling (16 Oct 2026, W-3b): nested-agent, routed like harness-condition-violated."""
        na = "nested-agent"
        src = REAL["operator_reasons_round4"]["sources"][na]
        for cite in ("glitch-b5", "16 Oct 2026", "W-3b", "harness-condition-violated", "--no-session-persistence"):
            self.assertIn(cite, src["ruling"])
        self.assertEqual(src["emitted_at"], CHECK_TAKE4)
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        with open(os.path.join(root, CHECK_TAKE4), encoding="utf-8") as f:
            text = f.read()
        self.assertIn(f'NESTED_AGENT = "{na}"', text)
        self.assertIn('f"[{NESTED_AGENT}] ', text)
        t = test_table()
        for phase, want, row in ((A, labels4.HARNESS_ERROR, "operator-reason-after-first-turn"),
                                 (B, labels4.REHEARSAL, "operator-reason-before-first-turn")):
            rec = baseline(phase)
            rec["checker_reasons"] = [na]
            got = routing.route(rec, t)
            self.assertEqual((got["route"], got["rows"]), (want, [row]), phase)

    def test_witness_unlisted_it_is_refused(self):
        t = test_table()
        t["operator_reasons"].remove(self.HCV)                                   # the mutant
        rec = baseline(A)
        rec["checker_reasons"] = [self.HCV]
        self.assertIsInstance(try_route(rec, t), routing.RoutingRefused)

    def test_the_table_check_binds_both_lists(self):
        self.assertEqual(routing.check_table(REAL), [])
        cases = {
            "an addition outside operator_reasons": lambda t: t["operator_reasons"].remove(self.HCV),
            "an operator reason with no source": lambda t: t["operator_reasons_round4"]["ids"].clear(),
            "an addition that also has a round-3 source": lambda t: t["operator_reason_sources"].__setitem__(
                self.HCV, dict(next(iter(t["operator_reason_sources"].values())))),
            "an addition with no ruling": lambda t: t["operator_reasons_round4"]["sources"][self.HCV].pop("ruling"),
            "an addition with no source entry": lambda t: t["operator_reasons_round4"]["sources"].clear(),
        }
        for name, edit in cases.items():
            t = copy.deepcopy(REAL)
            edit(t)
            self.assertNotEqual(routing.check_table(t), [], name)


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
        # round 4's named additions (operator_reasons_round4) are listed apart; every other id is round 3's
        added = ROUND4_ADDED_REASONS
        self.assertEqual(REAL["operator_reasons_round4"]["ids"], list(added))
        self.assertFalse(set(added) & listed, "a round-4 addition is never one of round 3's ids")
        self.assertEqual(set(REAL["operator_reasons"]) - set(added), listed - events)
        self.assertEqual(len(REAL["operator_reasons"]), len(listed - events) + len(added))
        self.assertEqual(len(listed), 24, "round 3's 24 rehearsal_reasons")
        self.assertTrue(REAL["operator_reasons_status"].startswith("FILLED"))

    def test_every_operator_reason_cites_its_source(self):
        listed = json.loads(self.show("evals/gap-study-3/prereg.json"))["rehearsal_reasons"]
        sources = REAL["operator_reason_sources"]
        self.assertEqual(set(sources), set(REAL["operator_reasons"]) - set(ROUND4_ADDED_REASONS))
        for rid, src in sources.items():
            self.assertEqual(src["file"], "evals/gap-study-3/prereg.json")
            self.assertEqual(src["commit"], self.COMMIT)
            self.assertEqual(src["key"], f"rehearsal_reasons.{rid}")
            self.assertEqual(src["meaning"], listed[rid])
            self.assertTrue(src["emitted_at"].startswith("evals/gap-study-3/check_take.py:"), rid)

    def test_the_pause_cap_is_round_3s(self):
        pre = json.loads(self.show("evals/gap-study-3/prereg.json"))
        cap = REAL["caps"][labels4.PAUSE]
        self.assertEqual(cap["events_per_half_cell"], int(pre["pause_cap"]))
        self.assertIn("evals/gap-study-3/prereg.json", cap["source"])
        self.assertIn(self.COMMIT, cap["source"])

    def test_the_rehearsal_cap_is_round_3s(self):
        """W1B2-11 (lane w1b's addition): the plan's 'round 3's cap' is prereg.json's rehearsal_cap."""
        pre = json.loads(self.show("evals/gap-study-3/prereg.json"))
        cap = REAL["caps"][labels4.REHEARSAL]
        self.assertEqual(cap["events_per_half_cell"], int(pre["rehearsal_cap"]))
        self.assertIn(self.COMMIT, cap["source"])

    def test_driver_decided_reasons_are_round_3s(self):
        """W1B2-10: round 3's driver_decided_reasons, copied in order, with their source."""
        pre = json.loads(self.show("evals/gap-study-3/prereg.json"))
        self.assertEqual(REAL["driver_decided_reasons"]["ids"], pre["driver_decided_reasons"])
        self.assertEqual(len(REAL["driver_decided_reasons"]["ids"]), 6)
        for cite in ("driver_decided_reasons", self.COMMIT, "operator_reasons"):
            self.assertIn(cite, REAL["driver_decided_reasons"]["source"])

    def test_every_emitted_at_line_carries_its_id(self):
        """W1B2-10: every emitted_at line number names a check_take.py line at e2979b31 that emits that id, and
        every reason-id line there is cited under its id."""
        lines = self.show(CHECK_TAKE).splitlines()
        self.assertEqual(set(REAL["checker_reasons_become_events"]["emitted_at"]),
                         set(REAL["checker_reasons_become_events"]["ids"]))
        self.assertEqual(emitted_at_problems(REAL, lines), [])

    def test_emitted_at_check_can_fail(self):
        lines = self.show(CHECK_TAKE).splitlines()
        for rid, edit in (("operator-lines", lambda c: c.replace(":1115,", ":1116,")),     # a line number shifted
                          ("fixture-binding", lambda c: c.replace(",1677", "")),           # a cited line dropped
                          (NFAT, lambda c: c.replace(":83,", ":84,"))):                    # the constant's line
            t = copy.deepcopy(REAL)
            src = t["operator_reason_sources"][rid]
            src["emitted_at"] = edit(src["emitted_at"])
            self.assertNotEqual(src["emitted_at"], REAL["operator_reason_sources"][rid]["emitted_at"])
            self.assertNotEqual(emitted_at_problems(t, lines), [], rid)
        t = copy.deepcopy(REAL)
        t["checker_reasons_become_events"]["emitted_at"]["account-email"] = f"{CHECK_TAKE}:715"
        self.assertNotEqual(emitted_at_problems(t, lines), [])

    def test_pause_cap_sources_record_both_of_round_3s_files(self):
        """W1B2-11: the pause cap's source quotes drive.py:147-148 ("a pause is uncapped where a rehearsal is
        capped") and records that prereg.json's pause_cap = 3 is applied per cell by takes.py:280-285; both
        quotes are checked against the files, and the rehearsal cap's against takes.py:286-291."""
        drive = " ".join(x.strip().lstrip("#").strip() for x in self.round3_lines(self.DRIVE, 147, 148))
        uncapped = "a pause is uncapped where a rehearsal is capped"
        self.assertIn(uncapped, drive)
        pause_src = REAL["caps"][labels4.PAUSE]["source"]
        for cite in (uncapped, "drive.py:147-148", "takes.py:280-285", "pause_cap = 3"):
            self.assertIn(cite, pause_src)
        takes = self.round3_lines(self.TAKES, 280, 291)
        self.assertIn('outcome(i) == "pause"', takes[0])
        self.assertIn('int(pre["pause_cap"])', takes[1])
        self.assertIn(f"'{_print_text(takes[2:5]).split('. ', 1)[1]}'", pause_src)
        self.assertIn('int(pre["rehearsal_cap"])', takes[7])
        rehearsal_src = REAL["caps"][labels4.REHEARSAL]["source"]
        self.assertIn(f"'{_print_text(takes[8:11]).split('. ', 1)[1]}'", rehearsal_src)
        self.assertIn("takes.py:286-291", rehearsal_src)

    def test_finalize_abort_rows_record_round_3s_treatment(self):
        """W1B2-11: round 3 graded a finalize abort `aborted` (drive.py:1408-1409, 1417); both rows record that
        beside the plan's re-route, quoting the lines checked here."""
        comment = " ".join(x.strip().lstrip("#").strip() for x in self.round3_lines(self.DRIVE, 1408, 1409))
        graded = "the take has a first agent turn, so it is graded, and the label whose definition it meets is `aborted`"
        self.assertIn(graded, comment)
        (line,) = self.round3_lines(self.DRIVE, 1417, 1417)
        outcome = 'aborted — finalize did not write samples.csv within {wait_s} s'
        self.assertEqual(line.strip(), f'ledger["outcome"] = f"{outcome}"')
        for rid in ("finalize-abort-before-first-turn", "finalize-abort-after-first-turn"):
            src = next(r for r in REAL["rows"] if r["id"] == rid)["source"]
            for cite in (graded, outcome, "drive.py:1405-1419", self.COMMIT):
                self.assertIn(cite, src, rid)

    # Round 3's lines this lane may read (the gap4 lane lead's rule, owner's ruling "gap4 routing: A"): only
    # these ranges, besides check_take.py's reason-id lines and prereg.json's four keys.
    DRIVE = "evals/gap-study-3/drive.py"
    TAKES = "evals/gap-study-3/takes.py"
    ALLOWED = {DRIVE: ((140, 160), (857, 923), (1405, 1420)), TAKES: ((255, 295),), CHECK_TAKE: ((80, 95),)}

    def round3_lines(self, path: str, first: int, last: int) -> list[str]:
        if not any(lo <= first <= last <= hi for lo, hi in self.ALLOWED[path]):
            raise AssertionError(f"{path}:{first}-{last} is outside the lines this lane may read")
        return self.show(path).splitlines()[first - 1:last]

    def round3_markers(self) -> tuple:
        """RATE_LIMIT_MARKERS, from the assignment on drive.py:149, parsed with ast (never imported)."""
        (line,) = self.round3_lines(self.DRIVE, 149, 149)
        node = ast.parse(line).body[0]
        self.assertIsInstance(node, ast.Assign, line)
        self.assertEqual([getattr(t, "id", None) for t in node.targets], ["RATE_LIMIT_MARKERS"], line)
        markers = ast.literal_eval(node.value)
        self.assertIsInstance(markers, tuple)
        return markers

    def test_text_markers_are_round_3s_in_order(self):
        self.assertEqual(REAL["rate_limit_markers"][TEST_HARNESS]["text"], list(self.round3_markers()))
        source = REAL["rate_limit_markers"][TEST_HARNESS]["source"]
        for cite in ("glitch-f3", "evals/gap-study-3/drive.py:149", self.COMMIT, "driver_constants.rate_limit_markers"):
            self.assertIn(cite, source)

    def test_text_match_is_round_3s_matched_marker(self):
        """Round 3's own matched_marker (drive.py:912-919), run on the probes, agrees with them and with routing's
        match: the probes are round 3's rule, never this lane's reading of it."""
        lines = self.round3_lines(self.DRIVE, 912, 919)
        self.assertTrue(lines[0].startswith("def matched_marker(text: str)"), lines[0])
        ns = {"re": re, "RATE_LIMIT_MARKERS": self.round3_markers()}
        exec(compile("\n".join(lines), f"{self.DRIVE}@{self.COMMIT[:8]}:912", "exec",    # noqa: S102 - pinned, read lines
                     flags=__future__.annotations.compiler_flag, dont_inherit=True), ns)
        theirs = ns["matched_marker"]
        markers = REAL["rate_limit_markers"][TEST_HARNESS]["text"]
        self.assertEqual(text_match_problems(lambda text, _markers: theirs(text), markers), [])
        self.assertEqual(text_match_problems(routing.rate_limit_text_marker, markers), [])

    # W1B4-5 (w1b's next touch, item 3; lane w4h-w1b-next-touch): batch.py quotes round 3's takes.py by line. The fence
    # is the lines actually read, 255-295 (CP5-requirements W1B4-1: 255-261 and 267-272; w1b's report: 260-295), and
    # the quote is bound here: its words stand on the line it cites, at round 3's done commit.
    TAKES_QUOTE = re.compile(r'"([^"]+)" \(evals/gap-study-3/takes\.py:(\d+) at\s+([0-9a-f]{8,40})\)')

    def takes_quote_problems(self, doc: str) -> list[str]:
        """Every takes.py quote in `doc` whose words do not stand on the line it cites (none quoted is a problem)."""
        quotes = self.TAKES_QUOTE.findall(doc)
        if not quotes:
            return ["batch.py quotes no takes.py line"]
        p = []
        for words, line, commit in quotes:
            if not self.COMMIT.startswith(commit):
                p.append(f"takes.py:{line} is quoted at {commit}, not round 3's done commit")
                continue
            (text,) = self.round3_lines(self.TAKES, int(line), int(line))
            if words not in " ".join(text.split()):
                p.append(f"{words!r} does not stand on takes.py:{line} ({text.strip()!r})")
        return p

    def test_the_takes_fence_is_the_lines_read(self):
        self.assertEqual(self.ALLOWED[self.TAKES], ((255, 295),))

    def test_batch_quotes_takes_260(self):
        import batch   # noqa: PLC0415 - only its docstring is read
        self.assertEqual([(w, n) for w, n, _ in self.TAKES_QUOTE.findall(batch.__doc__)],
                         [("there are no retakes", "260")])
        self.assertEqual(self.takes_quote_problems(batch.__doc__), [])

    def test_takes_quote_check_can_fail(self):
        import batch   # noqa: PLC0415
        shifted = batch.__doc__.replace("takes.py:260 at", "takes.py:261 at")       # the quote's line shifted
        self.assertNotEqual(shifted, batch.__doc__)
        self.assertTrue(any("does not stand on takes.py:261" in x for x in self.takes_quote_problems(shifted)))
        self.assertEqual(self.takes_quote_problems("no quote here"), ["batch.py quotes no takes.py line"])
        narrowed = dict(self.ALLOWED, **{self.TAKES: ((268, 292),)})                 # the fence narrowed back
        with mock.patch.object(TestRound3Sources, "ALLOWED", narrowed):
            with self.assertRaisesRegex(AssertionError, "outside the lines this lane may read"):
                self.takes_quote_problems(batch.__doc__)


    def test_claude_code_reset_wait_is_round_3s_none(self):
        """w1b's next-touch item 1 (lane w4h): the Claude Code entry's reset_wait is round 3's. Round 3 states none in drive.py
        140-160 (its constants beside RATE_LIMIT_MARKERS: no reset wait among them), so it is null, named for CP2's
        wait_reset."""
        lines = self.round3_lines(self.DRIVE, 140, 160)
        names = [t.id for x in lines if x and not x[0].isspace() and "=" in x and not x.lstrip().startswith("#")
                 for node in [ast.parse(x).body[0]] if isinstance(node, ast.Assign) for t in node.targets
                 if isinstance(t, ast.Name)]
        self.assertIn("RATE_LIMIT_MARKERS", names)
        self.assertFalse([n for n in names if "RESET" in n or "WINDOW" in n], names)
        entry = REAL["rate_limit_markers"][hb.CLAUDE_CODE]
        self.assertIsNone(entry["reset_wait"])
        for cite in ("drive.py:140-160", self.COMMIT, "wait_reset", "CP2"):
            self.assertIn(cite, entry["source"])


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
        self.assertEqual(len(COUNT_LEAVES), 6)   # + quiescence_cap_survivors (CP2 ruling C3; lane w4h, see its report)
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

    def test_two_api_errors_in_one_turn_through_harness_records(self):
        """W1B2-7: a 529 then a 429 in one turn routes pause, before and after the first turn."""
        t = test_table()
        for phase, turns in ((B, [a_silent_turn(api_errors=[dict(E529), dict(E429)])]),
                             (A, [a_turn(), a_turn(exit_code=1, end_reason=labels4.END_ERROR,
                                                   api_errors=[dict(E529), dict(E429)])])):
            rec = aa.harness_records(turns, pin=PIN, box=full_box())
            self.assertEqual([e["status"] for e in rec["api_errors"]], [529, 429])
            got = routing.route(rec, t)
            self.assertEqual((got["route"], got["rows"], got["phase"]), (labels4.PAUSE, ["rate-limit"], phase))
        real = aa.harness_records

        def first_per_turn(turns, *, pin, box):   # the mutant: one API error per turn, as before W1B2-7
            out = real(turns, pin=pin, box=box)
            out["api_errors"] = [{f: x.api_errors[0][f] for f in aa.API_ERROR_FIELDS} for x in turns if x.api_errors]
            return out
        with mock.patch.object(aa, "harness_records", first_per_turn):
            rec = aa.harness_records([a_turn(), a_turn(exit_code=1, end_reason=labels4.END_ERROR,
                                                       api_errors=[dict(E529), dict(E429)])], pin=PIN, box=full_box())
        self.assertEqual(routing.route(rec, t)["route"], labels4.HARNESS_ERROR)

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
        self.assertEqual(text_match_problems(routing.rate_limit_text_marker, REAL["rate_limit_markers"][TEST_HARNESS]["text"]), [])

    def test_word_bound_check_can_fail(self):
        def substring(text, markers):   # the mutant: a plain substring match
            return next((m for m in markers if m in text.lower()), None)

        def case_sensitive(text, markers):   # the mutant: the text not lowercased
            return next((m for m in markers if re.search(r"(?<![\w])" + re.escape(m) + r"(?![\w])", text)), None)
        markers = REAL["rate_limit_markers"][TEST_HARNESS]["text"]
        for mutant in (substring, case_sensitive):
            self.assertNotEqual(text_match_problems(mutant, markers), [], mutant.__name__)
            with mock.patch.object(routing, "rate_limit_text_marker", mutant):
                self.assertNotEqual(scenario_problems(test_table()), [], mutant.__name__)


class TestProfiles(unittest.TestCase):
    """glitch-f3's ruling on 'per profile': one test per pinned model profile (test-only, injected),
    a mismatch in any of the three fields routing per the table."""


def profile_problems(model: str, table: dict) -> list[str]:
    p = []
    pin = dict(table["pin_profiles"][TEST_HARNESS][model], model=model, harness=TEST_HARNESS)
    clean = try_route(baseline(A, pin), table)
    if isinstance(clean, Exception) or clean["route"] != labels4.GRADED:
        p.append(f"{model}: a clean take under its own profile did not grade ({clean})")
    for field in table["pin_fields"]:
        for turn in (0, -1):
            rec = baseline(A, pin)
            rec["init"][turn] = dict(init_of(pin), **{field: f"{pin[field]}-other"})
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


for _model in TEST_PROFILES[TEST_HARNESS]:
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
                     "rate_limit_markers: text deleted", "pin_refusal: removed", "pin_refusal: outranked_by emptied",
                     "pin_refusal: all_of[0] present_differs_from_pin mutated", "pin_refusal: phase -> after-first-turn"):
            self.assertIn(what, described)
        for j in range(len(REAL["rate_limit_markers"][TEST_HARNESS]["text"])):   # every text marker, alone (glitch-f3's ruling)
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



# ---------------------------------------------------------------- w1b's next touch (lane w4h-w1b-next-touch)
# Interface 8 (item 5, the schema half): the routing pin carries the take's harness (AgentAdapter.name) beside its
# model, and pin_profiles is keyed by harness, then model. The harness is the seam's own name, never typed here.
NT_HARNESS = hb.CLAUDE_CODE
NT_FAKE = "fake-second"                      # the test-only second harness (interface 8)
NT_INIT_FIELDS = ("model", "permission_mode", "version")   # an init event's fields, typed once here
NT_PROFILES = {NT_HARNESS: {"test-model-a": {"permission_mode": "bypassPermissions", "version": "0.0.1-test"},
                            "test-model-b": {"permission_mode": "plan-test", "version": "0.0.2-test"}}}
NT_PIN = dict(NT_PROFILES[NT_HARNESS]["test-model-a"], model="test-model-a", harness=NT_HARNESS)


def nt_init(pin: dict) -> dict:
    """An init event under `pin`: the pin's init fields (an init event names no harness)."""
    return {f: pin[f] for f in NT_INIT_FIELDS}


def nt_table() -> dict:
    t = copy.deepcopy(REAL)
    t["pin_profiles"] = copy.deepcopy(NT_PROFILES)
    t["pin_profiles_status"] = "TEST-ONLY: two injected profiles under one harness"
    return t


def nt_record(phase: str, pin: dict | None = None) -> dict:
    """baseline(phase), its pin the harness-keyed one and its init events under that pin."""
    pin = dict(pin or NT_PIN)
    rec = baseline(phase)
    rec["pin"] = dict(pin)
    rec["init"] = [nt_init(pin) for _ in rec["init"]]
    return rec


def agent_pin_problems(table: dict) -> list[str]:
    """Interface 8 on the routing pin: a take under its harness-keyed profile routes; a pin without its harness, with
    a harness that is no string, or with a harness the table holds no profiles for is refused; an init event never
    carries the harness."""
    p = []
    for phase, want in ((A, labels4.GRADED), (B, None)):
        got = try_route(nt_record(phase), table)
        if want is not None and (isinstance(got, Exception) or got["route"] != want):
            p.append(f"a clean {phase} take under its harness-keyed profile: {got}")
    for name, edit, why in (
            ("the pin without its harness", lambda r: r["pin"].pop("harness"), "pin must hold exactly"),
            ("a None harness", lambda r: r["pin"].update(harness=None), "pin values must be strings"),
            ("a harness with no profiles", lambda r: r["pin"].update(harness=NT_FAKE), NT_FAKE),
            ("an init event carrying the harness", lambda r: r["init"][0].update(harness=NT_HARNESS), "init[0]")):
        rec = nt_record(A)
        edit(rec)
        got = try_route(rec, table)
        if not isinstance(got, routing.RoutingRefused) or why not in str(got):
            p.append(f"{name}: want refused naming {why!r}, got {got}")
    return p


class TestNextTouchAgentPin(unittest.TestCase):
    """Interface 8 (w1b's next-touch item 5): the routing pin gains `harness`, and pin_profiles is keyed by harness,
    then model. pin_profiles stays empty and PENDING (CP5's values), its status reworded to the new shape."""

    def test_the_pin_carries_its_harness(self):
        self.assertEqual(agent_pin_problems(nt_table()), [])

    def test_profiles_are_keyed_by_harness_then_model(self):
        self.assertEqual(routing.check_table(nt_table()), [])
        flat = nt_table()
        flat["pin_profiles"] = copy.deepcopy(NT_PROFILES[NT_HARNESS])   # the old shape: keyed by model alone
        self.assertTrue(any("pin_profiles" in x or "pin profile" in x for x in routing.check_table(flat)))
        for bad in ({NT_HARNESS: {}}, {"": NT_PROFILES[NT_HARNESS]}, {NT_HARNESS: {"test-model-a": {"version": "1"}}}):
            t = nt_table()
            t["pin_profiles"] = copy.deepcopy(bad)
            self.assertNotEqual(routing.check_table(t), [], bad)

    def test_the_ruled_profiles_have_the_new_shape(self):
        """CP5 (Javier, 14 Oct 2026) replaced the PENDING status that described this shape; the real profiles are
        keyed by harness, then model (TestCP5ArmAProfiles holds their values). Round 17 B7 (R4; moved by glitch-b5's
        ruling M, 18 Oct 2026): the harnesses are exactly arm A's and R4's codex and gemini, each of the same shape."""
        self.assertEqual(set(REAL["pin_profiles"]), {CP5_HARNESS, R4_CODEX, R4_GEMINI})
        for harness, models in REAL["pin_profiles"].items():
            for model, prof in models.items():
                self.assertEqual(set(prof), set(NT_INIT_FIELDS) - {"model"}, (harness, model))
        self.assertTrue(REAL["pin_profiles_status"].startswith('RULED 14 Oct by Javier ("CP5: all as recommended")'))
        self.assertEqual(tuple(routing.PIN_KEYS), ("harness",) + NT_INIT_FIELDS)

    def test_agent_pin_check_can_fail(self):
        real = routing.check_records

        def harness_blind(records, table):   # the mutant: the profile lookup no longer refuses an unknown harness
            return [x for x in real(records, table) if "pre-registered profile" not in x]
        t = nt_table()                       # fake-second has markers and a spend list here, and no profile (item 1)
        t["rate_limit_markers"][NT_FAKE] = copy.deepcopy(FAKE_RATE)
        t["spend_cap_markers"][NT_FAKE] = copy.deepcopy(FAKE_SPEND)
        self.assertEqual(agent_pin_problems(t), [])
        with mock.patch.object(routing, "check_records", harness_blind):
            found = _guarded("agent pin", agent_pin_problems, t)
        self.assertTrue(any(x.startswith("a harness with no profiles: want refused") for x in found), found)
        with mock.patch.object(routing, "PIN_KEYS", routing.PLAN_PIN_FIELDS):   # the base's pin: no harness
            found = _guarded("agent pin", agent_pin_problems, nt_table())         # a crash is a finding, never a pass
        self.assertTrue(any(x.startswith("a clean after-first-turn take") or "crashed" in x for x in found), found)

        def open_init(value, fields, what):   # the mutant: an init event may carry keys beyond the plan's fields
            if what.startswith("init") and isinstance(value, dict) and set(fields) <= set(value):
                return []
            return real_pin(value, fields, what)
        real_pin = routing._pin_problems
        with mock.patch.object(routing, "_pin_problems", open_init):
            found = agent_pin_problems(nt_table())
        self.assertTrue(any(x.startswith("an init event carrying the harness: want refused") for x in found), found)



# Item 1 (w1b's next touch; glitch-f3's ruling 4 of 17:25): a vendor spend cap is not a rate limit. The rate-limit
# markers and the reset wait are keyed by harness; a spend-cap refusal (routing.json's spend_cap_refusal) matches a
# closed per-harness list of spend-cap types or text markers on the API-error record's harness-side fields only,
# raises RoutingRefused (batch.py commits the take blocked and the loop stops for a human), in every phase, outranked
# by nothing, so a spend-cap 429 never pauses. The test-only `fake-second` entry carries made-up types.
SPEND_ID = "spend-cap-reached"
# Javier's ruling (lane w8c, W8C-gap4-1): the spend-markers proposal's section-5 line, <date> = 2026-10-12, his words named.
SPEND_STATUS_RULED = (
    'RULED 2026-10-12 by Javier ("spend markers: 1A 2A 3A", typed Mon 12 Oct 2026 08:52 EDT in glitch-1b\'s window, on '
    'plans/gap-study-round-4/spend-markers-proposal-2026-10-11.md): claude-code\'s spend-cap list is empty on purpose; '
    'arm A runs on his subscription login (D4 A), which bills no money per call, and a usage or weekly limit pauses '
    'under rate_limit_markers. The OpenAI and Google entries are added with their adapters, each with a non-empty list '
    '(OpenAI: project_spend_limit_exceeded, organization_spend_limit_exceeded, credit_balance_exhausted, '
    'insufficient_quota; Google: status 402 and its spend-cap error read at a walk), and this status is ruled again then.')
# Round 17 B7 (glitch-b5's ruling M, 18 Oct 2026): the status is glitch-b5's line, which quotes Javier's above.
SPEND_STATUS_B7 = "RULED 18 Oct 2026 by glitch-b5 under the owner's delegation"
FAKE_RATE = {"status": [429], "type": ["fake2_slow_down"], "text": ["fake2 throttled"], "reset_wait": 60,
             "source": "test-only: a made-up second harness"}
FAKE_SPEND = {"status": [402], "type": ["fake2_budget_spent", "fake2_org_budget_spent"],
              "text": ["fake2 budget exhausted"], "source": "test-only: a made-up second harness"}
FAKE_PIN = {"harness": NT_FAKE, "model": "fake2-model", "permission_mode": "fake2-mode", "version": "0.0.9-fake2"}
OLD_FLAT = "48f100563e68f4798defd96fb1bf483dd679c940"   # this lane's base: routing.json's flat markers


def spend_table() -> dict:
    """The test table, with the test-only fake-second harness's markers, spend-cap list and one pin profile."""
    t = test_table()
    t["rate_limit_markers"][NT_FAKE] = copy.deepcopy(FAKE_RATE)
    t["spend_cap_markers"][NT_FAKE] = copy.deepcopy(FAKE_SPEND)
    t["pin_profiles"][NT_FAKE] = {FAKE_PIN["model"]: {"permission_mode": FAKE_PIN["permission_mode"],
                                                     "version": FAKE_PIN["version"]}}
    t["spend_cap_markers_status"] = "TEST-ONLY: fake-second's made-up spend-cap types"
    return t


def take_with(errors: list, phase: str, pin: dict | None = None) -> dict:
    """A take of `phase` under `pin` (fake-second's by default) whose API errors are `errors`, its last turn ended in
    error (after the first turn), or one silent turn (before it)."""
    rec = baseline(phase, pin or FAKE_PIN)
    set_api(rec, errors)
    if phase == A:
        set_end(rec, labels4.END_ERROR, 1)
    return rec


def spend_cases(table: dict) -> dict:
    """name -> (records, want): want is REFUSED for the spend-cap refusal, else (route, rows)."""
    cases = {}
    spend = FAKE_SPEND                   # the test's own list, so a type dropped from the table is still a scenario
    for phase in (B, A):
        for typ in spend["type"]:          # one scenario per spend-cap type: a 429 whose text says 429 and rate limit
            cases[f"{phase}: spend type {typ} as a 429"] = (
                take_with([_err("Error 429: rate limit (spend)", 429, typ)], phase), REFUSED)
        for st in spend["status"]:
            cases[f"{phase}: spend status {st}"] = (take_with([_err(None, st)], phase), REFUSED)
        for m in spend["text"]:
            cases[f"{phase}: spend text {m!r}"] = (take_with([_err(f"Request failed: {m.upper()}.")], phase), REFUSED)
        cases[f"{phase}: a 500, then a spend cap"] = (
            take_with([_err("internal", 500, "api_error"), _err(None, 429, spend["type"][0])], phase), REFUSED)
        cases[f"{phase}: fake-second's own rate limit pauses"] = (
            take_with([_err(None, None, FAKE_RATE["type"][0])], phase), (labels4.PAUSE, ["rate-limit"]))
        cases[f"{phase}: the real harness's rate-limit type is no marker under fake-second"] = (
            take_with([_err(None, None, REAL["rate_limit_markers"][TEST_HARNESS]["type"][0])], phase),
            (labels4.REHEARSAL, ["api-error-before-first-turn"]) if phase == B
            else (labels4.HARNESS_ERROR, ["api-error-after-first-turn"]))
        cases[f"{phase}: fake-second's spend type is no marker under the real harness"] = (
            take_with([_err(None, None, spend["type"][0])], phase, PIN),
            (labels4.REHEARSAL, ["api-error-before-first-turn"]) if phase == B
            else (labels4.HARNESS_ERROR, ["api-error-after-first-turn"]))
    rec = take_with([_err(None, 429, spend["type"][1])], B)     # beside a differing init: the spend cap, not the pin
    rec["init"][-1] = dict(init_of(FAKE_PIN), version="9.9.9")
    cases["before the first turn, a spend cap beside a differing init"] = (rec, REFUSED)
    rec = take_with([_err(None, 429, spend["type"][0])], A)     # beside an out-of-memory kill (aborted)
    rec["cgroup"]["oom_kill_delta"] = 1
    cases["after the first turn, a spend cap beside an out-of-memory kill"] = (rec, REFUSED)
    return cases


def spend_problems(table: dict) -> list[str]:
    p = []
    for name, (rec, want) in spend_cases(table).items():
        got = try_route(rec, table)
        if want == REFUSED:
            if not isinstance(got, routing.RoutingRefused) or SPEND_ID not in str(got):
                p.append(f"{name}: want refused by {SPEND_ID}, got {got if isinstance(got, Exception) else got['route']}")
        elif isinstance(got, Exception) or (got["route"], got["rows"]) != want:
            p.append(f"{name}: want {want}, got {got if isinstance(got, Exception) else (got['route'], got['rows'])}")
    return p


def harness_name_problems(table: dict, registered) -> list[str]:
    """Every harness key routing.json holds (its rate-limit markers, its spend-cap lists, its pin profiles) is a name
    the seam registers (interface 8)."""
    names = set(table["rate_limit_markers"]) | set(table["spend_cap_markers"]) | set(table["pin_profiles"])
    return [f"{n!r} is no harness the seam registers" for n in sorted(names) if n not in registered]


# Round 17 B7, glitch-b5's ruling S (18 Oct 2026): the seam is the parser table alone (claude-code, codex, gemini);
# harness_bookkeeping.TABLE stays claude-code alone where T2 asserts it, so Evidence.load still refuses a vendor take.
SEAM_NAMES = set(transcript_view.PARSERS)
UNPARSED = "synthetic-unparsed"   # a harness name no parser registers (ruling S moved the codex case here)


class TestNextTouchSpendCap(unittest.TestCase):
    """A vendor spend cap is not a rate limit (CP2-requirements, the spend-cap section; glitch-f3's ruling 4)."""

    def test_spend_caps_are_refused_never_paused(self):
        self.assertEqual(spend_problems(spend_table()), [])

    def test_markers_and_reset_wait_are_keyed_by_harness(self):
        self.assertEqual(routing.check_table(spend_table()), [])
        # round 17 B7 (glitch-b5's ruling M, 18 Oct 2026): claude-code's entries, then codex's and gemini's with R4
        for key in ("rate_limit_markers", "spend_cap_markers"):
            self.assertEqual(set(REAL[key]), {TEST_HARNESS, "codex", "gemini"}, key)
        for harness in REAL["rate_limit_markers"]:
            self.assertEqual(set(REAL["rate_limit_markers"][harness]), {"status", "type", "text", "reset_wait", "source"},
                             harness)

    def test_the_rekeyed_claude_code_values_are_the_old_flat_ones(self):
        """Ruling 3 of 17:42: the re-keyed Claude Code entry equals the base's flat one (W4BR-w4h-5), less the new
        reset_wait; its source keeps the old one's words."""
        p = subprocess.run(["git", "-C", TestRound3Sources.ROOT, "show", f"{OLD_FLAT}:evals/gap-study-4/routing.json"],
                           capture_output=True)
        self.assertEqual(p.returncode, 0, "the base commit (git fetch --unshallow?)")
        old = json.loads(p.stdout.decode())["rate_limit_markers"]
        new = REAL["rate_limit_markers"][TEST_HARNESS]
        self.assertEqual(set(old), {"status", "type", "text", "source"})
        for k in ("status", "type", "text"):
            self.assertEqual(new[k], old[k], k)
        self.assertTrue(new["source"].startswith(old["source"]))

    def test_claude_code_spend_list_is_empty_and_ruled(self):
        """Lane w8c (ruling W8C-gap4-1): Javier ruled the status, "spend markers: 1A 2A 3A" (Mon 12 Oct 2026 08:52
        EDT, glitch-1b's window, on plans/gap-study-round-4/spend-markers-proposal-2026-10-11.md): 1A, claude-code's
        list stays empty on purpose. The status was the proposal's section-5 line with the date and his words filled
        in, word for word; it was PENDING (glitch-f3) before. Round 17 B7 (moved by glitch-b5's ruling M, 18 Oct
        2026): the status is glitch-b5's RULED 18 Oct 2026 line, which quotes Javier's line word for word, and the
        spend-cap harnesses are exactly claude-code, codex and gemini; claude-code's entry is unchanged."""
        entry = REAL["spend_cap_markers"][TEST_HARNESS]
        self.assertEqual({k: entry[k] for k in ("status", "type", "text")}, {"status": [], "type": [], "text": []})
        for cite in ("subscription login", "D4 A", "glitch-f3", '"spend markers: 1A 2A 3A"', "RULED"):
            self.assertIn(cite, entry["source"])
        self.assertTrue(entry["source"].startswith("Empty on purpose, ruled by Javier on 12 Oct 2026"), entry["source"])
        self.assertNotIn("PENDING status", entry["source"])
        status = REAL["spend_cap_markers_status"]
        self.assertTrue(status.startswith(SPEND_STATUS_B7), status[:90])
        self.assertIn(f'This supersedes, word for word: "{SPEND_STATUS_RULED}"', status)
        self.assertIn('"spend markers: 1A 2A 3A"', status)
        self.assertNotIn("PENDING", status.upper())
        self.assertEqual(set(REAL["spend_cap_markers"]), {TEST_HARNESS, "codex", "gemini"})   # added with their adapters

    def test_the_refusal_is_a_closed_rule(self):
        rule = REAL["spend_cap_refusal"]
        self.assertEqual((rule["id"], rule["when"], rule["outranked_by"]), (SPEND_ID, labels4.ANY_TIME, []))
        self.assertNotIn("spend", " ".join(labels4.ROUTES))           # no new route: the closed vocabulary stays
        bad = {
            "outranked by pause": lambda r: r.update(outranked_by=[labels4.PAUSE]),
            "before the first turn only": lambda r: r.update(when=labels4.BEFORE_FIRST_TURN),
            "after the first turn only": lambda r: r.update(when=labels4.AFTER_FIRST_TURN),
            "no condition": lambda r: r.update(any_of=[]),
            "a row's op": lambda r: r["any_of"].append({"path": "api_errors.type", "op": "in_rate_limit_markers"}),
            "a text-derived count": lambda r: r["any_of"].append({"path": "events.outside_reach", "op": "gt", "value": 0}),
            "no source": lambda r: r.update(source=""),
            "an extra key": lambda r: r.update(route=labels4.PAUSE),
            "an id a row has": lambda r: r.update(id="rate-limit"),
            # fold 1, W4H1-8: a spend condition on a record outside the API-error fields
            "a spend condition on ledger.end": lambda r: r["any_of"].append({"path": "ledger.end", "op": "in_spend_cap_markers"}),
        }
        for name, edit in bad.items():
            t = spend_table()
            edit(t["spend_cap_refusal"])
            self.assertTrue(any("spend_cap_refusal" in x or "repeat" in x for x in routing.check_table(t)), name)
        for key in ("spend_cap_refusal", "spend_cap_markers", "spend_cap_markers_status"):
            t = spend_table()
            del t[key]
            self.assertIn(f"missing {key}", routing.check_table(t))

    def test_the_lists_are_checked(self):
        bad = {
            "a spend type that is a rate-limit type": lambda t: t["spend_cap_markers"][NT_FAKE]["type"].append(
                FAKE_RATE["type"][0]),
            "a spend status that is a rate-limit status": lambda t: t["spend_cap_markers"][NT_FAKE]["status"].append(429),
            "a spend text marker that is a rate-limit one": lambda t: t["spend_cap_markers"][NT_FAKE]["text"].append(
                FAKE_RATE["text"][0]),
            "an upper-case spend text marker": lambda t: t["spend_cap_markers"][NT_FAKE]["text"].append("Budget"),
            "a spend type that is no string": lambda t: t["spend_cap_markers"][NT_FAKE]["type"].append(402),
            "a spend entry with an unknown key": lambda t: t["spend_cap_markers"][NT_FAKE].update(code=[402]),
            "a spend entry without its source": lambda t: t["spend_cap_markers"][NT_FAKE].pop("source"),
            "a harness with markers and no spend list": lambda t: t["spend_cap_markers"].pop(NT_FAKE),
            "a harness with a spend list and no markers": lambda t: t["rate_limit_markers"].pop(NT_FAKE),
            "a profile under a harness with no markers": lambda t: t["pin_profiles"].update(other={"m": {
                "permission_mode": "p", "version": "v"}}),
            "a markers entry without reset_wait": lambda t: t["rate_limit_markers"][NT_FAKE].pop("reset_wait"),
            "a negative reset_wait": lambda t: t["rate_limit_markers"][NT_FAKE].update(reset_wait=-1),
            "a string reset_wait": lambda t: t["rate_limit_markers"][NT_FAKE].update(reset_wait="60"),
            "a bool reset_wait": lambda t: t["rate_limit_markers"][NT_FAKE].update(reset_wait=True),
            "a NaN reset_wait": lambda t: t["rate_limit_markers"][NT_FAKE].update(reset_wait=float("nan")),
            "an empty harness name": lambda t: t["rate_limit_markers"].update({"": copy.deepcopy(FAKE_RATE)}),
            "spend_cap_markers_status empty": lambda t: t.update(spend_cap_markers_status=""),
            # fold 1 (lane review round 1; the lane lead's decisions): W4H1-5, W4H1-6, W4H1-7, W4H1-8
            "a spend status that is no int": lambda t: t["spend_cap_markers"][NT_FAKE]["status"].append("402"),
            "a rate-limit status that is no int": lambda t: t["rate_limit_markers"][NT_FAKE]["status"].append("429"),
            "an infinite reset_wait": lambda t: t["rate_limit_markers"][NT_FAKE].update(reset_wait=float("inf")),
            "an empty rate-limit status list": lambda t: t["rate_limit_markers"][NT_FAKE]["status"].clear(),
            "a markers entry with an empty source": lambda t: t["rate_limit_markers"][NT_FAKE].update(source=""),
        }
        for name, edit in bad.items():
            t = spend_table()
            edit(t)
            self.assertNotEqual(routing.check_table(t), [], name)

    def test_an_unknown_harness_is_refused_never_defaulted(self):
        t = spend_table()
        rec = baseline(A, dict(FAKE_PIN))
        del t["rate_limit_markers"][NT_FAKE]          # an unsound table, read by the records check alone
        self.assertTrue(any("rate-limit markers" in x for x in routing.check_records(rec, t)))
        t = spend_table()
        del t["spend_cap_markers"][NT_FAKE]
        self.assertTrue(any("spend-cap" in x for x in routing.check_records(rec, t)))

    def test_every_harness_key_is_one_the_seam_registers(self):
        self.assertEqual(harness_name_problems(REAL, SEAM_NAMES), [])
        self.assertEqual(harness_name_problems(spend_table(), SEAM_NAMES | {NT_FAKE}), [])   # the test-only table
        self.assertEqual(harness_name_problems(spend_table(), SEAM_NAMES), [f"{NT_FAKE!r} is no harness the seam registers"])
        self.assertNotIn(UNPARSED, transcript_view.PARSERS)
        t = copy.deepcopy(REAL)
        t["rate_limit_markers"][UNPARSED] = copy.deepcopy(FAKE_RATE)
        self.assertEqual(harness_name_problems(t, SEAM_NAMES), [f"{UNPARSED!r} is no harness the seam registers"])

    def test_spend_check_can_fail(self):
        def paused(found):
            return [x for x in found if "as a 429: want refused" in x and x.endswith("got pause")]
        # (the refusal put below pause in the table: since fold 1, W4H1-2, route() ignores outranked_by and
        # check_table refuses it; TestNextTouchFold1 holds both, with the run-time gate as its mutant)
        t = spend_table()
        t["spend_cap_refusal"]["when"] = labels4.BEFORE_FIRST_TURN         # the refusal in one phase only
        self.assertTrue(any(x.startswith(f"{A}: spend type") and x.endswith("got pause") for x in spend_problems(t)))
        with mock.patch.object(routing, "spend_cap_holds", lambda records, table: False):   # no refusal at all
            self.assertEqual(len(paused(spend_problems(spend_table()))), 2 * len(FAKE_SPEND["type"]))
        for j, typ in enumerate(FAKE_SPEND["type"]):                       # each spend type dropped from the list
            t = spend_table()
            del t["spend_cap_markers"][NT_FAKE]["type"][j]
            self.assertTrue(any(x.startswith(f"{B}: spend type {typ} as a 429") for x in spend_problems(t)), typ)
        real = routing.harness_markers

        def claude_codes(table, key, records):   # the mutant: markers no longer keyed by the take's harness
            return real(table, key, {"pin": dict(records["pin"], harness=TEST_HARNESS)})
        with mock.patch.object(routing, "harness_markers", claude_codes):
            found = spend_problems(spend_table())
        self.assertTrue(any("fake-second's own rate limit pauses" in x for x in found), found)
        self.assertTrue(any("the real harness's rate-limit type is no marker under fake-second" in x for x in found), found)

    def test_the_harness_check_can_fail(self):
        real = routing.check_records

        def defaulting(records, table):   # the mutant: an unknown harness let through to the markers
            return [x for x in real(records, table) if "refused, never defaulted" not in x]
        t = spend_table()
        rec = take_with([_err(None, 429, None)], A)
        del t["rate_limit_markers"][NT_FAKE]       # an unsound table: fake-second's markers gone
        with self.assertRaisesRegex(routing.RoutingRefused, "has no rate-limit markers"):
            routing.route(rec, t)
        with mock.patch.object(routing, "check_records", defaulting):
            with self.assertRaises(KeyError):      # the markers read with no entry: a crash, never a refusal
                routing.route(rec, t)
        t = spend_table()
        t["spend_cap_refusal"]["outranked_by"] = [labels4.PAUSE]
        self.assertTrue(any("outranked by nothing" in x for x in routing.check_table(t)))



# CP2 ruling C3 (glitch-f3, 17:35; names fixed at 17:42): two box keys and their rows, both after-first-turn, both
# harness-error until pre-freeze review 1's MAJOR 5 (lane pf1-l2a, 24 Oct 2026) re-routed the cap's row graded: a
# survivor is the agent's own process, so its take is read, never discarded (tests/test_pf1_routing_rulings.py P5).
# `unreadable_consequential` (row unreadable-consequential-path): the run-tree paths the sidecar could
# not read among the task's consequential ones; before the first turn a non-empty list is refused (a preflight
# failure is CP2's to fold into preflight_ok). `quiescence_cap_survivors` (row quiescence-cap-reached): the processes
# still alive at the quiescence cap (W2A2-6): the operator-diff row does not also match, and the take routes graded
# by the cap's row beside its graded end (MAJOR 5).
UNREADABLE, SURVIVORS = "unreadable_consequential", "quiescence_cap_survivors"
UNREADABLE_ROW, CAP_ROW = "unreadable-consequential-path", "quiescence-cap-reached"
OP_DIFF_ROW = "operator-diff-unexplained-after-first-turn"
SOME_PATHS = ["data/staging/samples.csv", "results/table.tsv"]   # made-up run-tree paths


def c3_record(phase: str, unreadable=(), survivors=0, edits=()) -> dict:
    rec = baseline(phase)
    rec[UNREADABLE] = list(unreadable)
    rec[SURVIVORS] = survivors
    for e in edits:
        e(rec)
    return rec


def _diffs(n):
    return lambda r: r["operator"].__setitem__("unexplained_diffs", n)


def _oom(r):
    r["cgroup"]["oom_kill_delta"] = 1


def _qk(r):
    r["quiescence_kill"] = True


C3_CASES = {   # name -> (records builder, route or REFUSED, winning rows, matched rows or None, events)
    "an unreadable consequential path after the first turn": (
        lambda: c3_record(A, SOME_PATHS[:1]), labels4.HARNESS_ERROR, [UNREADABLE_ROW], [UNREADABLE_ROW, "end-turn"], []),
    "two unreadable consequential paths after the first turn": (
        lambda: c3_record(A, SOME_PATHS), labels4.HARNESS_ERROR, [UNREADABLE_ROW], None, []),
    "an unreadable consequential path before the first turn is refused": (
        lambda: c3_record(B, SOME_PATHS[:1]), REFUSED, None, None, []),
    "an unreadable path after a silent turn, before the first turn, is refused": (
        lambda: c3_record(B, SOME_PATHS[:1], edits=[silent_turn]), REFUSED, None, None, []),
    "an unreadable path beside a silent timeout, before the first turn, is refused": (
        lambda: c3_record(B, SOME_PATHS[:1], edits=[silent_timeout]), REFUSED, None, None, []),
    "processes alive at the quiescence cap": (
        lambda: c3_record(A, survivors=1), labels4.GRADED, [CAP_ROW, "end-turn"], [CAP_ROW, "end-turn"], []),
    "the cap's survivors and the operator diff they caused: the cap's row, never the diff's (W2A2-6)": (
        lambda: c3_record(A, survivors=2, edits=[_diffs(1)]), labels4.GRADED, [CAP_ROW, "end-turn"],
        [CAP_ROW, "end-turn"], []),
    "an operator diff with no survivors stays the operator-diff row": (
        lambda: c3_record(A, edits=[_diffs(1)]), labels4.HARNESS_ERROR, [OP_DIFF_ROW], [OP_DIFF_ROW, "end-turn"], []),
    "survivors before the first turn are refused (lane w4h decision)": (
        lambda: c3_record(B, survivors=1, edits=[silent_timeout]), REFUSED, None, None, []),
    "survivors beside an out-of-memory kill: aborted": (
        lambda: c3_record(A, survivors=1, edits=[_oom]), labels4.ABORTED, ["cgroup-kill"], ["cgroup-kill", CAP_ROW, "end-turn"], []),
    "an unreadable path beside a rate limit: pause": (
        lambda: c3_record(A, SOME_PATHS[:1], edits=[_rate, _end_error(1)]), labels4.PAUSE, ["rate-limit"], None, []),
    "survivors beside a quiescence kill: the cap's row, and the kill's event": (
        lambda: c3_record(A, survivors=1, edits=[_qk]), labels4.GRADED, [CAP_ROW, "end-turn"], None, [QK]),
    "an unreadable path and survivors: the unreadable path's harness-error outranks the cap's graded row": (
        lambda: c3_record(A, SOME_PATHS[:1], survivors=1), labels4.HARNESS_ERROR, [UNREADABLE_ROW],
        [UNREADABLE_ROW, CAP_ROW, "end-turn"], []),
}


def c3_problems(table: dict) -> list[str]:
    p = []
    for name, (build, route, rows, matched, events) in C3_CASES.items():
        rec = build()
        got = try_route(rec, table)
        if route == REFUSED:
            if not isinstance(got, routing.RoutingRefused):
                p.append(f"{name}: want refused, got {got['route']} via {got['rows']}")
            continue
        if isinstance(got, Exception):
            p.append(f"{name}: refused ({got})")
        elif (got["route"], got["rows"]) != (route, rows) or (matched is not None and got["matched"] != matched):
            p.append(f"{name}: want {route} via {rows} (matched {matched}), got {got['route']} via {got['rows']} "
                     f"(matched {got['matched']})")
        elif got["events"] != events:
            p.append(f"{name}: want events {events}, got {got['events']}")
    return p


C3_BAD_TYPES = {UNREADABLE: (None, "data/x.csv", [1], [""], [None], {"data/x.csv": 1}, 0, True),
                SURVIVORS: (None, True, False, -1, "1", 1.5, [1])}


def c3_type_problems(table: dict) -> list[str]:
    """Each C3 key dropped, None, or of a wrong type is refused by route and annotate, never coerced; the box key
    dropped is refused by harness_records."""
    p = []
    for key, bads in C3_BAD_TYPES.items():
        rec = c3_record(A)
        del rec[key]
        for fn in (routing.route, routing.annotate):
            if not refuses(fn, rec, table):
                p.append(f"{key} dropped: {fn.__name__} did not refuse it")
        for bad in bads:
            rec = c3_record(A)
            rec[key] = bad
            for fn in (routing.route, routing.annotate):
                if not refuses(fn, rec, table):
                    p.append(f"{key}={bad!r}: {fn.__name__} did not refuse it")
    return p


# The plan's oracle carries them too, so the mutation sweep (all_problems) sees every C3 row and the operator-diff
# row's new none_of (the per-scenario tests generated above predate these entries; scenario_problems reads them all).
SCENARIOS.update({f"C3: {name}": Sc(build, route, rows, matched, events, False)
                  for name, (build, route, rows, matched, events) in C3_CASES.items()})


class TestNextTouchC3(unittest.TestCase):
    """CP2 ruling C3: `unreadable_consequential` (row unreadable-consequential-path, after-first-turn, harness-error)
    and `quiescence_cap_survivors` (row quiescence-cap-reached, after-first-turn, graded since MAJOR 5)."""

    def test_the_names_are_fixed(self):
        self.assertIn(UNREADABLE, routing.RECORD_SCHEMA)
        self.assertIn(SURVIVORS, routing.RECORD_SCHEMA)
        self.assertIn(UNREADABLE, aa.BOX_KEYS)
        self.assertIn(SURVIVORS, aa.BOX_KEYS)
        for rid, path, route in ((UNREADABLE_ROW, UNREADABLE, labels4.HARNESS_ERROR), (CAP_ROW, SURVIVORS, labels4.GRADED)):
            row = next(r for r in REAL["rows"] if r["id"] == rid)
            self.assertEqual((row["when"], row["route"]), (labels4.AFTER_FIRST_TURN, route), rid)
            self.assertEqual([c["path"] for c in row["any_of"]], [path], rid)
        op_diff = next(r for r in REAL["rows"] if r["id"] == OP_DIFF_ROW)
        self.assertIn({"path": SURVIVORS, "op": "gt", "value": 0}, op_diff["none_of"])
        self.assertIn("W2A2-6", next(r for r in REAL["rows"] if r["id"] == CAP_ROW)["source"])

    def test_the_c3_rows_route(self):
        self.assertEqual(c3_problems(test_table()), [])
        self.assertEqual(scenario_problems(test_table()), [])

    def test_c3_check_can_fail(self):
        """Each C3 row's route changed, the row removed, its condition mutated, and the operator-diff row's new none_of
        deleted: the oracle goes red (the mutation sweep covers them all; these name the C3 ones)."""
        survivors = [d for d, t in mutants(test_table())
                     if any(k in d for k in (UNREADABLE_ROW, CAP_ROW, OP_DIFF_ROW)) and not all_problems(t)]
        self.assertEqual(survivors, [])
        described = " ".join(d for d, _ in mutants(test_table()))
        for what in (f"{UNREADABLE_ROW}: removed", f"{CAP_ROW}: removed", f"{CAP_ROW}: route -> harness-error",
                     f"{OP_DIFF_ROW}: none_of deleted", f"{OP_DIFF_ROW}: none_of[0] gt mutated"):
            self.assertIn(what, described)
        real = routing.check_records

        def reads_nothing_early(records, table):   # the mutant: the before-first-turn refusals dropped
            return [x for x in real(records, table) if "before the agent's first turn: " not in x]
        with mock.patch.object(routing, "check_records", reads_nothing_early):
            found = c3_problems(test_table())
        for name in ("an unreadable path beside a silent timeout, before the first turn, is refused",
                     "survivors before the first turn are refused (lane w4h decision)"):
            self.assertTrue(any(x.startswith(name) for x in found), (name, found))

    def test_the_c3_keys_are_typed_never_coerced(self):
        self.assertEqual(c3_type_problems(test_table()), [])

    def test_through_harness_records(self):
        t = test_table()
        box = dict(full_box(), **{UNREADABLE: list(SOME_PATHS[:1]), SURVIVORS: 0})
        got = routing.route(aa.harness_records([a_turn(), a_turn()], pin=PIN, box=box), t)
        self.assertEqual((got["route"], got["rows"]), (labels4.HARNESS_ERROR, [UNREADABLE_ROW]))
        box = dict(full_box(), **{UNREADABLE: [], SURVIVORS: 3, "unexplained_operator_diffs": 1})
        got = routing.route(aa.harness_records([a_turn(), a_turn()], pin=PIN, box=box), t)
        self.assertEqual((got["route"], got["rows"]), (labels4.GRADED, [CAP_ROW, "end-turn"]))
        for key in (UNREADABLE, SURVIVORS):
            box = dict(full_box(), **{UNREADABLE: [], SURVIVORS: 0})
            del box[key]
            with self.assertRaises(aa.BoxRecordError):
                aa.harness_records([a_turn()], pin=PIN, box=box)



class TestNextTouchFold1(unittest.TestCase):
    """Lane review round 1, W4H1-2 (the lane lead's decision: fold): route() checks the spend-cap refusal whatever the
    table's outranked_by says, so even a hand-built table that skips check_table can never pause a spend cap."""

    def test_the_spend_refusal_ignores_outranked_by(self):
        t = spend_table()
        t["spend_cap_refusal"]["outranked_by"] = [labels4.PAUSE]   # a table check_table refuses, handed in directly
        self.assertEqual(spend_problems(t), [])

    def test_ignores_outranked_by_check_can_fail(self):
        real = routing.spend_cap_holds

        def honours_outranked_by(records, table):   # the mutant: the base's gate, outranked_by read at run time
            return real(records, table) and labels4.PAUSE not in table["spend_cap_refusal"]["outranked_by"]
        t = spend_table()
        t["spend_cap_refusal"]["outranked_by"] = [labels4.PAUSE]
        with mock.patch.object(routing, "spend_cap_holds", honours_outranked_by):
            self.assertTrue(any(x.endswith("got pause") for x in spend_problems(t)))


# ------------------------------------------------------------------------------- CP5: arm A's three pin profiles
# Javier's ruling "CP5: all as recommended" (typed 08:11 EDT Wed 14 Oct 2026 in glitch-06's window), on
# plans/gap-study-round-4/cp5-values-draft-2026-10-14.md, section 3 and items 1, 2 and 7: arm A's three profiles are
# registered now, and arms O and G get none until their rate-limit and spend-cap markers are ruled (check_table refuses a
# profiled harness without them). The values are typed here once, from that draft; routing.json is checked against them.
from box import image_lock  # noqa: E402

CP5_HARNESS = hb.CLAUDE_CODE
CP5_MODELS = ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5-20251001")   # plan 133-135; build_draft.MODELS
CP5_MODE = "bypassPermissions"   # item 2: Claude Code's --permission-mode word, compared with init's permissionMode
CP5_VERSION = "2.1.296"          # take-a image.lock harness.version, as the box lane committed it (6221c297)
CP5_STATUS = ("RULED 14 Oct by Javier (\"CP5: all as recommended\"): arm A profiles registered; O and G follow when "
              "their rate-limit and spend-cap rules are set")
# Round 17 B7 (R4 of RULINGS-codex2-signin-road-2026-10-18.md; moved by glitch-b5's ruling M, 18 Oct 2026): the O
# and G profiles, typed here once from R4: each arm O model (plan; build_draft.MODELS) codex bypass 0.162.1, each arm G
# model gemini yolo 0.64.0. Arm A's three stay exactly CP5's.
R4_CODEX, R4_GEMINI = "codex", "gemini"
R4_PROFILES = {R4_CODEX: (("gpt-6.1-sol", "gpt-6-luna"), {"permission_mode": "bypass", "version": "0.162.1"}),
               R4_GEMINI: (("gemini-3.8-flash", "gemini-3.5-flash-lite"), {"permission_mode": "yolo", "version": "0.64.0"})}
TAKE_A_LOCK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "box", "image.lock")


def take_a_version(path: str = TAKE_A_LOCK) -> str:
    """The take-a image lock's harness.version, read through the lock's own reader."""
    lock = image_lock.load(path)
    if lock["image"] != "take-a":
        raise AssertionError(f"{path} is not the take-a lock: {lock['image']!r}")
    return lock["harness"]["version"]


def cp5_problems(table: dict, lock_version: str) -> list[str]:
    """Every way routing.json's pin profiles differ from the CP5 ruling or from the take-a lock (empty when sound).
    A lock still PENDING (the box lane's committed lock is not on this branch) binds nothing; a filled lock must be
    exactly the ruled version, and every profile's version must equal it."""
    p = []
    profiles = table.get("pin_profiles")
    if not isinstance(profiles, dict) or set(profiles) != {CP5_HARNESS, *R4_PROFILES}:
        p.append(f"CP5: pin_profiles must hold arm A's harness and R4's codex and gemini, got "
                 f"{sorted(profiles) if isinstance(profiles, dict) else profiles!r}")
    for harness, (want_models, want) in R4_PROFILES.items():   # round 17 B7: R4's O and G profiles, exactly
        got = profiles.get(harness) if isinstance(profiles, dict) else None
        got = got if isinstance(got, dict) else {}
        if tuple(got) != want_models:
            p.append(f"CP5: {harness}'s models must be exactly R4's {list(want_models)}, got {list(got)}")
        for model, prof in got.items():
            if prof != want:
                p.append(f"CP5: {harness} {model}'s profile is not R4's: {prof!r}")
    models = profiles.get(CP5_HARNESS) if isinstance(profiles, dict) else None
    models = models if isinstance(models, dict) else {}
    if tuple(models) != CP5_MODELS:
        p.append(f"CP5: arm A's models must be exactly {list(CP5_MODELS)}, got {list(models)}")
    for model, prof in models.items():
        if prof != {"permission_mode": CP5_MODE, "version": CP5_VERSION}:
            p.append(f"CP5: {model}'s profile is not the ruled one: {prof!r}")
        if lock_version != image_lock.PENDING and (not isinstance(prof, dict) or prof.get("version") != lock_version):
            p.append(f"CP5: {model}'s version is not the take-a lock's {lock_version!r}")
    if lock_version not in (image_lock.PENDING, CP5_VERSION):
        p.append(f"CP5: the take-a lock's harness.version {lock_version!r} is not the ruled {CP5_VERSION!r}")
    status = table.get("pin_profiles_status")
    if status != CP5_STATUS or "PENDING" in str(status).upper():
        p.append(f"CP5: pin_profiles_status is not the ruled line: {str(status)[:90]!r}")
    return p


class TestCP5ArmAProfiles(unittest.TestCase):
    """CP5 (Javier, 14 Oct 2026): routing.json carries arm A's three profiles, exactly as drafted; since round 17 B7
    (R4; moved by glitch-b5's ruling M, 18 Oct 2026) R4's O and G profiles beside them, and nothing else."""

    def test_the_real_table_is_the_ruling(self):
        self.assertEqual(cp5_problems(REAL, take_a_version()), [])
        self.assertEqual(routing.check_table(REAL), [])

    def test_the_real_lock_binds_the_version(self):
        lock = take_a_version()
        if lock == image_lock.PENDING:
            # test_round4 allows no skip (SKIP_ALLOWED is empty; athena run of 1f032586): with the lock PENDING the
            # profiles hold the ruled version, the one the box lane's committed lock (6221c297) carries where merged.
            lock = CP5_VERSION
        self.assertEqual({p["version"] for p in REAL["pin_profiles"][CP5_HARNESS].values()}, {lock})

    def test_the_committed_lock_value_binds(self):
        """The binding as it runs on the merged head, where take-a's lock holds the committed version."""
        self.assertEqual(cp5_problems(REAL, CP5_VERSION), [])
        # and a lock holding another version is caught, on every tree (the skip-free form of the binding)
        self.assertTrue(cp5_problems(REAL, "7.7.7"), "a take-a version the profiles do not carry passed")

    def test_o_and_g_pins_pass_only_as_r4s_profiles(self):
        """Renamed by B7-F7 (glitch-b5, 18 Oct 2026; review r17 NIT 4) from test_o_and_g_takes_are_still_refused.
        Round 17 B7 (R4; moved by glitch-b5's ruling M, 18 Oct 2026): an O or G take is still refused unless its
        pin is R4's profile: a pin off the profile is refused as not the model's pre-registered profile, and a model
        with no profile under the harness as having none; R4's own pin passes the records check (T2 and the vendor
        admission still refuse to grade the take)."""
        for harness, (models, prof) in R4_PROFILES.items():
            model = models[0]
            rec = baseline(A)
            rec["pin"] = {"harness": harness, "model": model, "permission_mode": "x", "version": "0"}
            with self.assertRaisesRegex(routing.RoutingRefused, f"the pin is not {model!r}'s pre-registered profile"):
                routing.route(rec, REAL)
            rec = baseline(A)
            rec["pin"] = {"harness": harness, "model": "synthetic-unprofiled", "permission_mode": prof["permission_mode"],
                          "version": prof["version"]}
            with self.assertRaisesRegex(routing.RoutingRefused, "no pre-registered profile"):
                routing.route(rec, REAL)
            for model in models:
                pin = dict(prof, harness=harness, model=model)
                self.assertEqual(routing.check_records(baseline(A, pin), REAL), [], model)

    def test_an_arm_a_pin_routes(self):
        for model in CP5_MODELS:
            pin = {"harness": CP5_HARNESS, "model": model, "permission_mode": CP5_MODE, "version": CP5_VERSION}
            self.assertEqual(routing.check_records(baseline(A, pin), REAL), [], model)


class TestCP5Mutants(unittest.TestCase):
    """Each mutant of the ruled table or lock must be refused by cp5_problems."""

    def mutants(self):
        def drift(t):
            t["pin_profiles"][CP5_HARNESS]["claude-sonnet-5-5"]["version"] = "2.1.297"
        def mode(t):
            t["pin_profiles"][CP5_HARNESS]["claude-haiku-4-5-20251001"]["permission_mode"] = "default"
        def codex(t):
            t["pin_profiles"]["codex"] = {"gpt-6.1-sol": {"permission_mode": "bypass", "version": "0.162.1"}}
        def gemini(t):
            t["pin_profiles"]["gemini"] = {"gemini-3.8-flash": {"permission_mode": "yolo", "version": "0.64.0"}}
        # round 17 B7 (ruling M): R4's profiles drifted; the O and G profile mutants above are kept as they were (each
        # now drops one model from R4's registration)
        def codex_mode(t):
            t["pin_profiles"]["codex"]["gpt-6.1-sol"]["permission_mode"] = "yolo"
        def codex_version(t):
            t["pin_profiles"]["codex"]["gpt-6-luna"]["version"] = "0.162.0"
        def gemini_mode(t):
            t["pin_profiles"]["gemini"]["gemini-3.5-flash-lite"]["permission_mode"] = "bypass"
        def gemini_extra(t):
            t["pin_profiles"]["gemini"]["gemini-synthetic"] = {"permission_mode": "yolo", "version": "0.64.0"}
        def vendor_gone(t):
            del t["pin_profiles"]["gemini"]
        def pending(t):
            t["pin_profiles_status"] = CP5_STATUS + "; codex and gemini PENDING"
        def dropped(t):
            del t["pin_profiles"][CP5_HARNESS]["claude-opus-5-5"]
        return {"version drift": (drift, CP5_VERSION), "wrong mode": (mode, CP5_VERSION), "O profile": (codex, CP5_VERSION),
                "G profile": (gemini, CP5_VERSION), "status PENDING": (pending, CP5_VERSION),
                "model dropped": (dropped, CP5_VERSION), "lock drift": (lambda t: None, "2.1.297"),
                "O mode yolo": (codex_mode, CP5_VERSION), "O version drift": (codex_version, CP5_VERSION),
                "G mode bypass": (gemini_mode, CP5_VERSION), "G model added": (gemini_extra, CP5_VERSION),
                "G profiles gone": (vendor_gone, CP5_VERSION)}

    def test_every_mutant_is_refused(self):
        survivors = []
        for name, (mutate, lock) in self.mutants().items():
            t = copy.deepcopy(REAL)
            mutate(t)
            if not cp5_problems(t, lock):
                survivors.append(name)
        self.assertEqual(survivors, [])



# ------------------------------------------------------- the harness-condition-violated routing ruling (17 Oct 2026)
# glitch-b5's ruling 3 (Sat 17 Oct 2026, under Javier's delegation): a take that violates the harness's own study
# conditions is a harness fault, not a model outcome. It is never graded as the model's result; it is voided with
# the reason recorded and its cell is re-run; until routed it fails closed. Before this ruling a violated take that
# also tripped the cgroup counters routed `aborted` (cgroup-kill outranks harness-error), a final model outcome
# that is never re-run. The scenario below carries the case into the mutation sweep's oracle.
HCV_RULED = "harness-condition-violated"
HCV_NOT_THE_MODELS = (labels4.GRADED, labels4.ABORTED)


def _hcv(r):
    r["checker_reasons"] = [HCV_RULED]


SCENARIOS.update({
    "harness-condition-violated beside a cgroup kill is voided, never aborted (glitch-b5, 17 Oct 2026)":
        Sc(_sc(A, [_hcv, _cgroup]), "harness-error", ["operator-reason-after-first-turn"]),
})


# Fold plan prefreeze-1, MAJOR 7 (lane pf1-l3, 24 Oct 2026): the plan's oracle for the transcript-mismatch row.
def _tm(r):
    r["checker_reasons"] = ["transcript-mismatch"]


def _tm_rd(r):
    r["checker_reasons"] = ["transcript-mismatch", "readers-disagree"]


def _tm_hcv(r):
    r["checker_reasons"] = ["transcript-mismatch", HCV_RULED]


SCENARIOS.update({
    "transcript-mismatch after the first turn is aborted, never re-run (pf1-l3, 24 Oct 2026)":
        Sc(_sc(A, [_tm]), "aborted", ["transcript-mismatch"]),
    "transcript-mismatch beside readers-disagree is still aborted (pf1-l3)":
        Sc(_sc(A, [_tm_rd]), "aborted", ["transcript-mismatch"]),
    "transcript-mismatch beside harness-condition-violated keeps ruling 3, harness-error (pf1-l3)":
        Sc(_sc(A, [_tm_hcv]), "harness-error", ["operator-reason-after-first-turn"]),
    "transcript-mismatch before the first turn is a rehearsal (pf1-l3)":
        Sc(_sc(B, [_tm]), "rehearsal", ["operator-reason-before-first-turn"]),
})


# Fold plan prefreeze-2, MAJOR 1 (lane L-A1, 29 Oct 2026): the plan's oracle for the split of nested-agent and
# subagent-records by who can produce the record, and for the bare store-variable assignment.
def _reasons(*ids):
    def f(r):
        r["checker_reasons"] = list(ids)
    return f


SCENARIOS.update({
    "nested-agent-session after the first turn is aborted, never re-run (pf2 L-A1)":
        Sc(_sc(A, [_reasons("nested-agent-session")]), "aborted", ["nested-agent-session"]),
    "subagent-unbound after the first turn is aborted, never re-run (pf2 L-A1)":
        Sc(_sc(A, [_reasons("subagent-unbound")]), "aborted", ["subagent-unbound"]),
    "nested-agent (the driver's record) after the first turn keeps harness-error (pf2 L-A1)":
        Sc(_sc(A, [_reasons("nested-agent")]), "harness-error", ["operator-reason-after-first-turn"]),
    "subagent-records (the driver's copy ledger) after the first turn keeps harness-error (pf2 L-A1)":
        Sc(_sc(A, [_reasons("subagent-records")]), "harness-error", ["operator-reason-after-first-turn"]),
    "a bare store-variable assignment after the first turn is graded with its agent event (pf2 L-A1)":
        Sc(_sc(A, [_reasons("store-variable-assigned")]), "graded", ["store-variable-assigned", "end-turn"]),
    "a store-variable assignment beside a nested agent found is aborted (pf2 L-A1)":
        Sc(_sc(A, [_reasons("store-variable-assigned", "nested-agent-session")]), "aborted",
           ["nested-agent-session"]),
    "nested-agent-session beside harness-condition-violated keeps ruling 3, harness-error (pf2 L-A1)":
        Sc(_sc(A, [_reasons("nested-agent-session", HCV_RULED)]), "harness-error", ["operator-reason-after-first-turn"]),
    "subagent-unbound beside harness-condition-violated keeps ruling 3, harness-error (pf2 L-A1)":
        Sc(_sc(A, [_reasons("subagent-unbound", HCV_RULED)]), "harness-error", ["operator-reason-after-first-turn"]),
    "nested-agent-session before the first turn is a rehearsal (pf2 L-A1)":
        Sc(_sc(B, [_reasons("nested-agent-session")]), "rehearsal", ["operator-reason-before-first-turn"]),
})


# glitch-45's ruling 2 on lane L-A1 (29 Oct 2026): the round-3 reasons every raise site of which reads a record the
# agent can write route aborted after the first turn by agent-reachable-reason; finalize-abort is aborted too.
for _rid in ("unknown-harness-origin", "operator-lines", "stop-at-held-marker",
             "continued-past-unheld-marker", "leak-in-loaded-context", "checkout-binding"):
    SCENARIOS[f"{_rid} after the first turn is aborted, never re-run (pf2 L-A1, the producer rule)"] = \
        Sc(_sc(A, [_reasons(_rid)]), "aborted", ["agent-reachable-reason"])
SCENARIOS["finalize abort beside harness-condition-violated keeps ruling 3, harness-error (pf2 L-A1)"] = \
    Sc(_sc(A, [_set("ledger.finalize_abort", True), _reasons(HCV_RULED)]), "harness-error",
       ["operator-reason-after-first-turn"])
def _rate_text(r):
    set_api(r, [{"status": None, "type": None,
                 "text": f"API Error: {REAL['rate_limit_markers'][TEST_HARNESS]['text'][0]} reached"}])


SCENARIOS["a rate limit beside transcript-mismatch is aborted, never a pause (pf2 L-A1 review, MAJOR 2)"] = \
    Sc(_sc(A, [_rate_text, _reasons("transcript-mismatch")]), "aborted", ["transcript-mismatch"])
SCENARIOS["a rate limit with its records agreeing still pauses (pf2 L-A1 review, MAJOR 2)"] = \
    Sc(_sc(A, [_rate_text]), "pause", ["rate-limit"])
SCENARIOS["unknown-harness-origin beside harness-condition-violated keeps ruling 3, harness-error (pf2 L-A1)"] = \
    Sc(_sc(A, [_reasons("unknown-harness-origin", HCV_RULED)]), "harness-error", ["operator-reason-after-first-turn"])
SCENARIOS["readers-disagree after the first turn is mixed, harness-error (pf2 L-A1 review, MAJOR 3)"] = \
    Sc(_sc(A, [_reasons("readers-disagree")]), "harness-error", ["operator-reason-after-first-turn"])


class TestHarnessConditionVoided(unittest.TestCase):
    """glitch-b5's ruling 3 (17 Oct 2026): a take whose harness study conditions failed is never the model's result.
    Whatever else its records show, it never routes graded or aborted: after the agent's first turn it routes
    harness-error (voided, its reason recorded, re-run in its slot under the harness-error cap), before it a rehearsal,
    a pause re-runs it after the window, and a spend cap or pin mismatch is refused for a human (fail closed)."""

    def test_the_ruling_is_cited(self):
        src = REAL["operator_reasons_round4"]["sources"][HCV_RULED]
        for cite in ("glitch-b5", "17 Oct 2026", "never graded", "voided", "re-run", "aborted"):
            self.assertIn(cite, src["ruling"])
        row = next(r for r in REAL["rows"] if r["id"] == "cgroup-kill")
        self.assertIn({"path": "checker_reasons", "op": "has", "value": HCV_RULED}, row.get("none_of", []))
        self.assertIn("17 Oct 2026", row["source"])

    def test_beside_every_terminal_state_it_is_never_the_models(self):
        t = test_table()
        for name, (edit, _) in TERMINAL_STATES.items():
            rec = baseline(A)
            edit(rec)
            _hcv(rec)
            got = try_route(rec, t)
            if isinstance(got, Exception):
                continue                      # refused for a human: fail closed, never graded
            self.assertNotIn(got["route"], HCV_NOT_THE_MODELS, name)
            if got["route"] != labels4.PAUSE:
                self.assertEqual(got["route"], labels4.HARNESS_ERROR, name)
                self.assertIn("operator-reason-after-first-turn", got["rows"], name)
                self.assertGreater(got["cap"]["reruns_per_slot"], 0, name)   # its slot is re-run

    def test_the_cgroup_kill_case(self):
        rec = baseline(A)
        _cgroup(rec)
        _hcv(rec)
        got = routing.route(rec, test_table())
        self.assertEqual((got["route"], got["rows"]), (labels4.HARNESS_ERROR, ["operator-reason-after-first-turn"]))
        self.assertNotIn("cgroup-kill", got["matched"])

    def test_before_the_first_turn_it_is_a_rehearsal(self):
        rec = baseline(B)
        _hcv(rec)
        got = routing.route(rec, test_table())
        self.assertEqual((got["route"], got["rows"]), (labels4.REHEARSAL, ["operator-reason-before-first-turn"]))

    def test_the_ruling_is_scoped_to_its_reason(self):
        """Only harness-condition-violated is ruled: another operator reason beside a cgroup kill still routes
        aborted, as the plan's precedence says."""
        rec = baseline(A)
        _cgroup(rec)
        rec["checker_reasons"] = [any_phase_reason(REAL)]
        self.assertNotEqual(rec["checker_reasons"], [HCV_RULED])
        self.assertEqual(routing.route(rec, test_table())["route"], labels4.ABORTED)

    def test_the_new_op_is_bound(self):
        """`has` reads one named operator reason of checker_reasons; a value outside operator_reasons, or a path
        other than checker_reasons, is a table problem."""
        self.assertEqual(routing.check_table(REAL), [])
        for name, cond in (("unlisted value", {"path": "checker_reasons", "op": "has", "value": "not-a-reason"}),
                           ("other path", {"path": "exit.exec_codes", "op": "has", "value": HCV_RULED}),
                           ("no value", {"path": "checker_reasons", "op": "has"})):
            t = copy.deepcopy(REAL)
            next(r for r in t["rows"] if r["id"] == "cgroup-kill")["none_of"] = [cond]
            self.assertNotEqual(routing.check_table(t), [], name)

    def test_the_sweep_kills_the_rulings_mutants(self):
        described = {d: t for d, t in mutants(test_table()) if d.startswith("cgroup-kill: none_of")}
        for what in ("cgroup-kill: none_of deleted", "cgroup-kill: none_of[0] has mutated",
                     "cgroup-kill: none_of[0] has deleted"):
            self.assertIn(what, described)
            self.assertNotEqual(all_problems(described[what]), [], what)


if __name__ == "__main__":
    unittest.main()
