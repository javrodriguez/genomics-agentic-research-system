#!/usr/bin/env python3
"""routing.py and routing.json: every row, every overlap the plan names, and every mutation goes red.

Three kinds of check, combined in `all_problems(table)`:

1. THE DERIVED GRID. For every row of routing.json and every one of its `any_of` alternatives, a
   witness record is built from the row's own conditions on a clean baseline of the row's phase,
   and must route to the row's route with the row among the winners; on the other phase's
   baseline the row must not match. Then every row's witness is crossed with every terminal state
   (end_turn, timeout, API error, container failure, cgroup kill, init mismatch, rate limit), and
   the route must be the higher-precedence of the two routes each produces alone. Rows, routes,
   precedence and phases all come from routing.json and labels4.py; nothing here retypes them.

2. THE PLAN'S ORACLE. A derived grid cannot catch a mutated table (a row whose route is changed
   still routes its own witness to the new route), so the plan's table is also stated here once,
   as scenarios typed from the plan's own words, each with the route and winning rows it must get.

3. THE MUTATION SWEEP. Every row is mutated (its route, its phase, each of its conditions, its
   removal) and the precedence is mutated (every adjacent swap, merged levels), in memory, and
   `all_problems` must be non-empty for every mutation.

The table under test carries one test-only operator reason (`TEST_REASON`), because round 3's
reasons are not yet listed in routing.json (see its operator_reasons_status); the real table's
refusal of every checker reason is tested on its own.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import routing  # noqa: E402
from graders import labels4  # noqa: E402

TEST_REASON = "test-only-operator-reason"
REAL = routing.load_table()
PIN = {"model": "pinned-model", "permission_mode": "bypassPermissions", "version": "1.0.0"}


def test_table() -> dict:
    t = copy.deepcopy(REAL)
    t["operator_reasons"] = [TEST_REASON]
    return t


# ---------------------------------------------------------------------------------------- records
def baseline(phase: str) -> dict:
    after = phase == labels4.AFTER_FIRST_TURN
    n = 2 if after else 0
    return {
        "ledger": {"first_turn_started": after, "turns": n, "end": "end_turn" if after else None,
                   "turn_ends": ["end_turn"] * n, "committed": False, "finalize_abort": False},
        "exit": {"container_started": True, "container_exited": False, "exec_codes": [0] * n},
        "cgroup": {"oom_kill_delta": 0, "pids_max_delta": 0},
        "init": [dict(PIN) for _ in range(n)],
        "pin": dict(PIN),
        "api_error": None,
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


def set_path(rec: dict, path: str, value):
    head, _, tail = path.partition(".")
    if path == "ledger.end":
        set_end(rec, value)
    elif tail:
        if rec[head] is None:
            rec[head] = {}
        rec[head][tail] = value
    else:
        rec[head] = value


def apply_witness(rec: dict, cond: dict, table: dict) -> set:
    """Make `cond` hold on `rec`; return the record paths it touched."""
    op, path = cond["op"], cond["path"]
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
    elif op == "not_null":
        set_path(rec, path, {"status": 500, "type": "api_error"})
    elif op == "is_null":
        set_path(rec, path, None)
    elif op == "in_operator_reasons":
        set_path(rec, path, [table["operator_reasons"][0]])
    elif op == "in_rate_limit_markers":
        set_path(rec, path, table["rate_limit_markers"][path.partition(".")[2]][0])
    elif op == "in_graded_ends":
        set_end(rec, table["graded_ends"][0])
    elif op == "differs_from_pin":
        rec["init"][0] = dict(PIN, model="not-the-pin")
    elif op == "nonzero_outside_timeout":
        rec["exit"]["exec_codes"][0] = 1
    else:
        raise AssertionError(f"no witness for op {op}")
    return {"ledger.end"} if path == "ledger.end" or op == "in_graded_ends" else {path.partition(".")[0]}


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


# ------------------------------------------------------------------------- 1. the derived grid
# The plan's terminal states, as record edits on the LAST turn (witnesses edit the first), with
# the paths each touches. Their routes are never typed: each is routed alone below.
def _timeout(r):
    set_end(r, "timed-out", 137)


def _api(r):
    r["api_error"] = {"status": 500, "type": "api_error"}


def _container(r):
    r["exit"]["container_exited"] = True


def _cgroup(r):
    r["cgroup"]["oom_kill_delta"] = 1
    r["exit"]["exec_codes"][-1] = 137


def _mismatch(r):
    r["init"][-1] = dict(PIN, version="not-the-pin")


def _rate(r):
    r["api_error"] = {"status": 429, "type": "rate_limit_error"}


TERMINAL_STATES = {
    "end_turn": (lambda r: None, set()),
    "timeout": (_timeout, {"ledger.end", "exit"}),
    "api-error": (_api, {"api_error"}),
    "container-failure": (_container, {"exit"}),
    "cgroup-kill": (_cgroup, {"cgroup", "exit"}),
    "mismatch": (_mismatch, {"init"}),
    "rate-limit": (_rate, {"api_error"}),
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


# ---------------------------------------------------------------------- 2. the plan's oracle
B, A = labels4.BEFORE_FIRST_TURN, labels4.AFTER_FIRST_TURN


def _sc(phase, edits):
    def build():
        r = baseline(phase)
        for e in edits:
            e(r)
        return r
    return build


def _set(path, value):
    return lambda r: set_path(r, path, value)


def _multi_turn(n):
    def f(r):
        r["ledger"].update(turns=n, turn_ends=["end_turn"] * n)
        r["exit"]["exec_codes"] = [0] * n
        r["init"] = [dict(PIN) for _ in range(n)]
    return f


REFUSED = "refused"
# name -> (records builder, expected route, expected winning row ids or None for refused[, expected
# matched row ids, where an overlap's lower rows matter]).
# Each is typed from the plan's routing table, its precedence paragraph, or its testing strategy.
SCENARIOS = {
    # before the agent's first turn -> rehearsal
    "preflight failure": (_sc(B, [_set("preflight.ok", False)]), "rehearsal", ["preflight-failed"]),
    "container start failure": (_sc(B, [_set("exit.container_started", False)]), "rehearsal", ["container-start-failed"]),
    "container died before first turn": (_sc(B, [_set("exit.container_exited", True)]), "rehearsal", ["container-start-failed"]),
    "API error before first turn": (_sc(B, [_api]), "rehearsal", ["api-error-before-first-turn"]),
    "watcher start missing before first turn": (_sc(B, [_set("sidecar.start_record", False)]), "rehearsal", ["sidecar-unhealthy-before-first-turn"]),
    "watcher non-zero exit before first turn": (_sc(B, [_set("sidecar.exit_code", 2)]), "rehearsal", ["sidecar-unhealthy-before-first-turn"]),
    "watcher overflow before first turn": (_sc(B, [_set("sidecar.queue_overflow", True)]), "rehearsal", ["sidecar-unhealthy-before-first-turn"]),
    "operator reason before first turn": (_sc(B, [_set("checker_reasons", [TEST_REASON])]), "rehearsal", ["operator-reason-before-first-turn"]),
    "operator diff before first turn": (_sc(B, [_set("operator.unexplained_diffs", 1)]), "rehearsal", ["operator-diff-unexplained-before-first-turn"]),
    "finalize abort before first turn": (_sc(B, [_set("ledger.finalize_abort", True)]), "rehearsal", ["finalize-abort-before-first-turn"]),
    "rate limit before first turn": (_sc(B, [_rate]), "pause", ["rate-limit"]),
    "rate-limit type alone": (_sc(B, [_set("api_error", {"status": None, "type": "rate_limit_error"})]), "pause", ["rate-limit"]),
    "nothing happened before first turn": (_sc(B, []), REFUSED, None),
    # after the first turn
    "clean end_turn": (_sc(A, []), "graded", ["end-turn"]),
    "timeout, host-killed exec": (_sc(A, [_timeout]), "graded", ["timed-out"]),
    "API error after first turn, non-zero exit": (_sc(A, [_api, lambda r: set_end(r, "error", 1)]), "harness-error", ["api-error-after-first-turn"]),
    "container exit after first turn": (_sc(A, [_container]), "harness-error", ["container-exit-after-first-turn"]),
    "watcher start missing": (_sc(A, [_set("sidecar.start_record", False)]), "harness-error", ["watcher-gap"]),
    "watcher stop missing": (_sc(A, [_set("sidecar.stop_record", False)]), "harness-error", ["watcher-gap"]),
    "watcher non-zero exit": (_sc(A, [_set("sidecar.exit_code", 1)]), "harness-error", ["watcher-gap"]),
    "watcher queue overflow": (_sc(A, [_set("sidecar.queue_overflow", True)]), "harness-error", ["watcher-gap"]),
    "init model differs": (_sc(A, [lambda r: r["init"].__setitem__(0, dict(PIN, model="x"))]), "harness-error", ["init-mismatch"]),
    "init mode differs": (_sc(A, [lambda r: r["init"].__setitem__(0, dict(PIN, permission_mode="default"))]), "harness-error", ["init-mismatch"]),
    "init event missing": (_sc(A, [lambda r: r["init"].__setitem__(0, None)]), "harness-error", ["init-mismatch"]),
    "mismatch on the last turn of an otherwise graded take": (_sc(A, [_multi_turn(4), _mismatch]), "harness-error", ["init-mismatch"]),
    "non-zero exec exit, nothing else": (_sc(A, [lambda r: r["exit"]["exec_codes"].__setitem__(0, 1)]), "harness-error", ["nonzero-exec-exit"]),
    "operator reason after first turn": (_sc(A, [_set("checker_reasons", [TEST_REASON])]), "harness-error", ["operator-reason-after-first-turn"]),
    "operator diff after first turn": (_sc(A, [_set("operator.unexplained_diffs", 2)]), "harness-error", ["operator-diff-unexplained-after-first-turn"]),
    "finalize abort after first turn": (_sc(A, [_set("ledger.finalize_abort", True)]), "harness-error", ["finalize-abort-after-first-turn"]),
    "out-of-memory counter rose": (_sc(A, [_set("cgroup.oom_kill_delta", 1)]), "aborted", ["cgroup-kill"]),
    "pids-limit counter rose": (_sc(A, [_set("cgroup.pids_max_delta", 3)]), "aborted", ["cgroup-kill"]),
    "outside reach: graded, masked, an event": (_sc(A, [_set("events.outside_reach", 1)]), "graded", ["end-turn", "outside-reach"]),
    "quiescence kill: graded, an event": (_sc(A, [_set("quiescence_kill", True)]), "graded", ["end-turn", "quiescence-kill"]),
    "ended in error with nothing recorded": (_sc(A, [lambda r: set_end(r, "error")]), REFUSED, None),
    # the overlapping cases the plan names, and the precedence between every pair of levels
    "rate limit mid-take": (_sc(A, [_multi_turn(3), _rate, lambda r: set_end(r, "error", 1)]), "pause", ["rate-limit"]),
    "out-of-memory kill with a non-zero exit": (_sc(A, [_cgroup, _container, lambda r: set_end(r, "error", 137)]), "aborted", ["cgroup-kill"],
                                                ["cgroup-kill", "container-exit-after-first-turn"]),
    "pids-limit kill with a non-zero exit": (_sc(A, [_set("cgroup.pids_max_delta", 1), lambda r: set_end(r, "error", 1)]), "aborted",
                                             ["cgroup-kill"], ["cgroup-kill"]),
    "counters rose before the first turn": (_sc(B, [_set("cgroup.oom_kill_delta", 1)]), REFUSED, None),
    "preflight failure recorded after the first turn": (_sc(A, [_set("preflight.ok", False)]), REFUSED, None),
    "watcher gap during a pause": (_sc(A, [_rate, _set("sidecar.stop_record", False)]), "pause", ["rate-limit"]),
    "rate limit beats a cgroup kill": (_sc(A, [_rate, _cgroup]), "pause", ["rate-limit"]),
    "cgroup kill beats an API error": (_sc(A, [_api, _cgroup]), "aborted", ["cgroup-kill"]),
    "harness error beats graded": (_sc(A, [_set("sidecar.queue_overflow", True), _set("events.outside_reach", 1)]), "harness-error", ["watcher-gap"]),
    "two harness faults agree": (_sc(A, [_container, _set("sidecar.stop_record", False)]), "harness-error", ["container-exit-after-first-turn", "watcher-gap"]),
    # refusals of the records themselves
    "already committed": (_sc(A, [_set("ledger.committed", True)]), REFUSED, None),
    "a pause on a committed take": (_sc(A, [_rate, _set("ledger.committed", True)]), REFUSED, None),
    "agent text in the records": (_sc(A, [lambda r: r.__setitem__("transcript", "hello")]), REFUSED, None),
    "a checker reason routing.json does not list": (_sc(A, [_set("checker_reasons", ["unlisted"])]), REFUSED, None),
}


def scenario_problems(table: dict) -> list[str]:
    p = []
    for name, (build, want, rows, *matched) in SCENARIOS.items():
        got = try_route(build(), table)
        if want == REFUSED:
            if not isinstance(got, Exception):
                p.append(f"{name}: want refused, got {got['route']}")
        elif isinstance(got, Exception):
            p.append(f"{name}: refused ({got})")
        elif got["route"] != want or got["rows"] != rows:
            p.append(f"{name}: want {want} via {rows}, got {got['route']} via {got['rows']}")
        elif matched and got["matched"] != matched[0]:
            p.append(f"{name}: want matched {matched[0]}, got {got['matched']}")
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


def all_problems(table: dict) -> list[str]:
    p = routing.check_table(table)
    if p:
        return p
    for row in table["rows"]:
        p += row_problems(row, table)
    return p + grid_problems(table) + scenario_problems(table) + tie_problems(table)


# ------------------------------------------------------------------------ 3. the mutation sweep
_CONDITION_MUTANT = {"eq": ("value", "__mutated__"), "ne": ("op", "eq"), "gt": ("value", 10 ** 9),
                     "truthy": ("op", "falsy"), "falsy": ("op", "truthy"), "not_null": ("op", "is_null"),
                     "is_null": ("op", "not_null"), "in_operator_reasons": ("op", "is_null"),
                     "in_rate_limit_markers": ("op", "is_null"), "in_graded_ends": ("op", "is_null"),
                     "differs_from_pin": ("op", "is_null"), "nonzero_outside_timeout": ("op", "is_null")}


def mutants(table: dict):
    """(description, mutated table) for every row and precedence mutation."""
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
            for j, c in enumerate(row.get(group, [])):
                key, val = _CONDITION_MUTANT[c["op"]]
                t = copy.deepcopy(table)
                t["rows"][i][group][j][key] = val
                yield f"{row['id']}: {group}[{j}] {c['op']} mutated", t
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


# --------------------------------------------------------------------------------------- tests
class TestRoutingTable(unittest.TestCase):
    def test_real_table_is_sound(self):
        self.assertEqual(routing.check_table(REAL), [])

    def test_table_routes_and_phases_come_from_labels4(self):
        self.assertEqual({r["route"] for r in REAL["rows"]}, set(labels4.ROUTES))
        self.assertLessEqual({r["when"] for r in REAL["rows"]}, set(labels4.PHASES))

    def test_every_row_cites_a_source(self):
        self.assertTrue(all(r.get("source") for r in REAL["rows"]))

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

    def test_real_table_refuses_every_checker_reason_while_pending(self):
        self.assertEqual(REAL["operator_reasons"], [])
        rec = baseline(A)
        rec["checker_reasons"] = [TEST_REASON]
        with self.assertRaises(routing.RoutingRefused):
            routing.route(rec, REAL)

    def test_pause_cap_is_pending(self):
        # Round 3's pause_cap was not read by this lane; batch.py must refuse to start without it.
        self.assertIsNone(REAL["caps"][labels4.PAUSE]["reruns_per_half_cell"])


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
        build, want, rows, *matched = SCENARIOS[name]
        got = try_route(build(), test_table())
        if want == REFUSED:
            self.assertIsInstance(got, routing.RoutingRefused)
        else:
            self.assertNotIsInstance(got, Exception, str(got))
            self.assertEqual((got["route"], got["rows"]), (want, rows))
            if matched:
                self.assertEqual(got["matched"], matched[0])
    return test


for _name in SCENARIOS:
    setattr(TestScenarios, "test_" + "".join(c if c.isalnum() else "_" for c in _name), _scenario_test(_name))


class TestGridAndMutations(unittest.TestCase):
    def test_grid_derived_from_table(self):
        self.assertEqual(grid_problems(test_table()), [])

    def test_everything_green_on_the_real_table(self):
        self.assertEqual(all_problems(test_table()), [])

    def test_every_mutation_goes_red(self):
        survivors = [d for d, t in mutants(test_table()) if not all_problems(t)]
        self.assertEqual(survivors, [])

    def test_mutation_sweep_covers_every_row(self):
        described = " ".join(d for d, _ in mutants(test_table()))
        for row in REAL["rows"]:
            self.assertIn(row["id"] + ": removed", described)

    def test_outside_reach_masks_and_counts(self):
        rec = baseline(A)
        rec["events"]["outside_reach"] = 1
        got = routing.route(rec, test_table())
        self.assertTrue(got["mask"])
        self.assertEqual(got["events"], ["outside-reach"])
        self.assertFalse(routing.route(baseline(A), test_table())["mask"])

    def test_tie_at_equal_precedence_is_refused(self):
        t, rec = tie_probe(test_table())
        with self.assertRaisesRegex(routing.RoutingRefused, "tie"):
            routing.route(rec, t)
        self.assertEqual(tie_problems(test_table()), [])

    def test_route_is_pure(self):
        rec = baseline(A)
        before = json.dumps(rec, sort_keys=True)
        first = routing.route(rec, test_table())
        self.assertEqual(json.dumps(rec, sort_keys=True), before)
        self.assertEqual(first, routing.route(rec, test_table()))

    def test_cap_returned_from_table(self):
        rec = baseline(A)
        rec["sidecar"]["queue_overflow"] = True
        got = routing.route(rec, test_table())
        self.assertEqual(got["cap"], REAL["caps"][labels4.HARNESS_ERROR])


if __name__ == "__main__":
    unittest.main()
