#!/usr/bin/env python3
"""Round 4's routing table, decided: one take's harness-side records in, one route out.

The table is pre-registered data in `routing.json`; this module is the only thing that decides it.
The drive step calls `route()` before the take's commit, so a re-run frees its slot before it
closes; `run.py` and `check_results.py` only re-verify the recorded route, never decide it.

`route()` is a pure function of the table and the records. It never reads the agent's text: the
records it accepts are a closed schema (`RECORD_SCHEMA` below), and a record carrying any other
top-level key (a transcript, a reply) is refused. The records are:

    ledger           first_turn_started, turns, end, turn_ends, committed, finalize_abort
    exit             the runtime's exit record: container_started, container_exited, exec_codes
    cgroup           the take's out-of-memory and pids-limit counter rises (oom_kill_delta,
                     pids_max_delta), read host-side
    init, pin        the init event of every turn, and the pinned model, mode and version
    api_error        the API-error record (None when there was none)
    sidecar          the watcher's health: start_record, stop_record, exit_code, queue_overflow
    preflight        ok
    operator         unexplained_diffs: operator-step diffs no logged operator event explains
    checker_reasons  the checker's reason ids, computed in the drive step
    quiescence_kill  the box stopped a background process at the quiescence cap
    events           outside_reach: the drive step's count of the agent reaching the token, the
                     account email, a study path or anything outside the run tree

`agent_adapter.harness_records()` builds this shape from an adapter's turn results; this module
does not import it, nor any driver or agent (lane lead's interface 5).

DECIDING. A row matches when the take is in the row's phase (`before-first-turn` when no agent
turn has started, else `after-first-turn`; `any` is both), every `all_of` condition holds, at least
one `any_of` condition holds, and no `none_of` condition holds. The matched rows at the highest
precedence level win. If none match, or the winners name more than one route, `route()` raises
`RoutingRefused`: never a default, never a pick. Records already committed are refused too, since a
route decided after the commit cannot free its slot.

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from graders import labels4  # noqa: E402

TABLE_PATH = os.path.join(_HERE, "routing.json")

# The closed record schema: top-level key -> sub-keys (None for a leaf or list).
RECORD_SCHEMA = {
    "ledger": ("first_turn_started", "turns", "end", "turn_ends", "committed", "finalize_abort"),
    "exit": ("container_started", "container_exited", "exec_codes"),
    "cgroup": ("oom_kill_delta", "pids_max_delta"),
    "init": None,
    "pin": None,
    "api_error": None,
    "sidecar": ("start_record", "stop_record", "exit_code", "queue_overflow"),
    "preflight": ("ok",),
    "operator": ("unexplained_diffs",),
    "checker_reasons": None,
    "quiescence_kill": None,
    "events": ("outside_reach",),
}

# Optional sub-keys of a record that may itself be None (the API-error record).
_API_ERROR_KEYS = ("status", "type")

OPS = ("eq", "ne", "gt", "truthy", "falsy", "not_null", "is_null", "in_operator_reasons",
       "in_rate_limit_markers", "in_graded_ends", "differs_from_pin", "nonzero_outside_timeout")
_VALUE_OPS = ("eq", "ne", "gt")


class TableError(ValueError):
    """routing.json is not a sound table."""


class RoutingRefused(ValueError):
    """The records cannot be routed: no row, a tie, a malformed or committed record."""


# --------------------------------------------------------------------------------------- the table
def _known_path(path: str) -> bool:
    head, _, tail = path.partition(".")
    if head not in RECORD_SCHEMA:
        return False
    if not tail:
        return True
    if head == "api_error":
        return tail in _API_ERROR_KEYS
    subs = RECORD_SCHEMA[head]
    return subs is not None and tail in subs


def check_table(table: dict) -> list[str]:
    """Every problem with the table, as a list (empty when sound)."""
    p = []
    levels = table.get("precedence")
    if not isinstance(levels, list) or not all(isinstance(l, list) and l for l in levels):
        return ["precedence must be a non-empty list of non-empty levels"]
    flat = [r for level in levels for r in level]
    if sorted(flat) != sorted(labels4.ROUTES):
        p.append(f"precedence must name every route in labels4.ROUTES exactly once, got {flat}")
    order = {r: i for i, level in enumerate(levels) for r in level}
    # The plan's order is fixed: pause, then aborted, then harness-error, then graded.
    plan = (labels4.PAUSE, labels4.ABORTED, labels4.HARNESS_ERROR, labels4.GRADED)
    if all(r in order for r in plan) and not all(order[a] < order[b] for a, b in zip(plan, plan[1:])):
        p.append("precedence must be pause, then aborted, then harness-error, then graded")
    caps = table.get("caps", {})
    for r in labels4.ROUTES:
        if r not in caps:
            p.append(f"no cap for route {r}")
    for key in ("pin_fields", "graded_ends", "rate_limit_markers", "operator_reasons", "rows"):
        if key not in table:
            p.append(f"missing {key}")
    if p:
        return p
    if len(set(table["operator_reasons"])) != len(table["operator_reasons"]):
        p.append("operator_reasons repeats an id")
    ids = [row.get("id") for row in table["rows"]]
    if len(set(ids)) != len(ids):
        p.append("row ids repeat")
    seen_routes = set()
    for row in table["rows"]:
        rid = row.get("id")
        if row.get("route") not in labels4.ROUTES:
            p.append(f"{rid}: route {row.get('route')!r} not in labels4.ROUTES")
        seen_routes.add(row.get("route"))
        if row.get("when") not in labels4.PHASES:
            p.append(f"{rid}: phase {row.get('when')!r} not in labels4.PHASES")
        if not row.get("source"):
            p.append(f"{rid}: no source cited")
        if not row.get("any_of"):
            p.append(f"{rid}: any_of must hold at least one condition")
        for group in ("all_of", "any_of", "none_of"):
            for c in row.get(group, []):
                if c.get("op") not in OPS:
                    p.append(f"{rid}: unknown op {c.get('op')!r}")
                if not _known_path(c.get("path", "")):
                    p.append(f"{rid}: path {c.get('path')!r} is not a harness record")
                if c.get("op") in _VALUE_OPS and "value" not in c:
                    p.append(f"{rid}: op {c.get('op')} needs a value")
    for r in labels4.ROUTES:
        if r not in seen_routes:
            p.append(f"no row routes to {r}")
    return p


def load_table(path: str = TABLE_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        table = json.load(fh)
    problems = check_table(table)
    if problems:
        raise TableError("; ".join(problems))
    return table


# ------------------------------------------------------------------------------------- the records
def check_records(records: dict, table: dict) -> list[str]:
    p = []
    if not isinstance(records, dict):
        return ["records must be a dict"]
    extra = set(records) - set(RECORD_SCHEMA)
    if extra:
        p.append(f"keys outside the harness-side schema: {sorted(extra)}")
    for key, subs in RECORD_SCHEMA.items():
        if key not in records:
            p.append(f"missing record {key}")
            continue
        if subs is not None:
            if not isinstance(records[key], dict) or set(records[key]) != set(subs):
                p.append(f"record {key} must hold exactly {subs}")
    if p:
        return p
    for path in ("ledger.turn_ends", "exit.exec_codes", "init", "checker_reasons"):
        if not isinstance(_get(records, path), list):
            p.append(f"{path} must be a list")
    if not isinstance(records["ledger"]["turns"], int):
        p.append("ledger.turns must be an int")
    if p:
        return p
    led = records["ledger"]
    if bool(led["first_turn_started"]) != (led["turns"] > 0):
        p.append("ledger.first_turn_started disagrees with ledger.turns")
    if len(led["turn_ends"]) != led["turns"] or len(records["exit"]["exec_codes"]) != led["turns"]:
        p.append("per-turn records do not cover every turn")
    if len(records["init"]) != led["turns"]:
        p.append("init must hold one entry (or None) per turn")
    if led["turns"] and led["end"] != led["turn_ends"][-1]:
        p.append("ledger.end is not the last turn's end")
    if led["first_turn_started"] and not records["preflight"]["ok"]:
        p.append("a take whose preflight failed cannot have started a turn")
    if not isinstance(records["pin"], dict) or not set(table["pin_fields"]) <= set(records["pin"]):
        p.append("pin must carry every pin field")
    if records["api_error"] is not None and not isinstance(records["api_error"], dict):
        p.append("api_error must be a dict or None")
    unknown = [r for r in records["checker_reasons"] if r not in table["operator_reasons"]]
    if unknown:
        p.append(f"checker reason ids not in routing.json: {unknown}")
    if led["committed"]:
        p.append("the take is already committed: a route must be decided before the commit")
    return p


def _get(records: dict, path: str):
    head, _, tail = path.partition(".")
    value = records[head]
    if tail:
        value = None if value is None else value.get(tail)
    return value


def holds(cond: dict, records: dict, table: dict) -> bool:
    op, path = cond["op"], cond["path"]
    v = _get(records, path)
    if op == "eq":
        return v == cond["value"]
    if op == "ne":
        return v != cond["value"]
    if op == "gt":
        return v is not None and v > cond["value"]
    if op == "truthy":
        return bool(v)
    if op == "falsy":
        return not v
    if op == "not_null":
        return v is not None
    if op == "is_null":
        return v is None
    if op == "in_operator_reasons":
        return any(r in table["operator_reasons"] for r in v)
    if op == "in_rate_limit_markers":
        return v is not None and v in table["rate_limit_markers"].get(path.partition(".")[2], [])
    if op == "in_graded_ends":
        return v in table["graded_ends"]
    if op == "differs_from_pin":
        pin = records["pin"]
        return any(i is None or any(i.get(f) != pin[f] for f in table["pin_fields"]) for i in v)
    if op == "nonzero_outside_timeout":
        ends = records["ledger"]["turn_ends"]
        return any(code != 0 for code, end in zip(v, ends) if end != labels4.TIMED_OUT)
    raise TableError(f"unknown op {op!r}")


def phase_of(records: dict) -> str:
    return labels4.AFTER_FIRST_TURN if records["ledger"]["first_turn_started"] else labels4.BEFORE_FIRST_TURN


def matches(row: dict, records: dict, table: dict) -> bool:
    if row["when"] not in (labels4.ANY_TIME, phase_of(records)):
        return False
    if not all(holds(c, records, table) for c in row.get("all_of", [])):
        return False
    if not any(holds(c, records, table) for c in row["any_of"]):
        return False
    return not any(holds(c, records, table) for c in row.get("none_of", []))


def route(records: dict, table: dict | None = None) -> dict:
    """The one route for these records, or RoutingRefused.

    Returns {"route", "rows" (winning row ids), "matched" (every matched row id), "phase",
    "events" (matched event rows), "mask" (a matched row says mask before commit), "cap"}.
    Event and mask rows are reported even when a higher level wins, since an event is counted
    whatever the route.
    """
    table = table if table is not None else load_table()
    problems = check_records(records, table)
    if problems:
        raise RoutingRefused("; ".join(problems))
    matched = [row for row in table["rows"] if matches(row, records, table)]
    if not matched:
        raise RoutingRefused(f"no row matches these records (phase {phase_of(records)})")
    level = {r: i for i, lvl in enumerate(table["precedence"]) for r in lvl}
    top = min(level[row["route"]] for row in matched)
    winners = [row for row in matched if level[row["route"]] == top]
    routes = sorted({row["route"] for row in winners})
    if len(routes) > 1:
        raise RoutingRefused(f"tie at equal precedence: {routes} from {[w['id'] for w in winners]}")
    return {
        "route": routes[0],
        "rows": [w["id"] for w in winners],
        "matched": [m["id"] for m in matched],
        "phase": phase_of(records),
        "events": [m["id"] for m in matched if m.get("event")],
        "mask": any(m.get("mask") for m in matched),
        "cap": table["caps"][routes[0]],
    }


def main(argv: list[str]) -> int:
    """`routing.py --check` validates routing.json; `routing.py <records.json>` routes one take."""
    if argv[:1] == ["--check"]:
        table = load_table()
        print(f"routing.json: {len(table['rows'])} rows, sound")
        return 0
    if len(argv) == 1:
        with open(argv[0], encoding="utf-8") as fh:
            print(json.dumps(route(json.load(fh)), indent=1))
        return 0
    print("usage: routing.py --check | routing.py <records.json>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
