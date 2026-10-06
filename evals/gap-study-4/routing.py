#!/usr/bin/env python3
"""Round 4's routing table, decided: one take's harness-side records in, one route out.

The table is pre-registered data in `routing.json`; this module is the only thing that decides it.
The drive step calls `route()` before the take's commit, so a re-run frees its slot before it
closes; `run.py` and `check_results.py` only re-verify the recorded route, never decide it.

`route()` is a pure function of the table and the records. It never reads the agent's text: the
records it accepts are a closed, type-checked schema (`RECORD_SCHEMA` below), and a record
carrying any other key (a transcript, a reply), missing a key, or holding a value of the wrong
type (None or a string where a count belongs) is refused, never read as "nothing happened". The
records are:

    ledger           first_turn_started (bool), turns (count), end (a labels4 turn end; None
                     only with no turns), turn_ends, turn_outputs (did each turn produce completed
                     agent output, read from the stream's event types), committed, finalize_abort
    exit             the runtime's exit record: container_started, container_exited (bools),
                     exec_codes (int or None per turn)
    cgroup           the take's out-of-memory and pids-limit counter rises (oom_kill_delta,
                     pids_max_delta: counts), read host-side
    init, pin        the init event of every turn (None when a turn had none), and the pinned
                     model, mode and version; the pin must be the pre-registered profile of its
                     model in routing.json's pin_profiles, never whatever the driver supplied
    api_errors       every API-error record of the take, in turn order: {status: int or None,
                     type: str or None}
    sidecar          the watcher's health: start_record, stop_record (bools), exit_code (int),
                     queue_overflow (bool)
    preflight        ok (bool)
    operator         unexplained_diffs (count): operator-step diffs no logged operator event explains
    checker_reasons  the checker's reason ids (strs), computed in the drive step
    quiescence_kill  (bool) the box stopped a background process at the quiescence cap
    events           outside_reach (count): the drive step's count of the agent reaching the
                     token, the account email, a study path or anything outside the run tree

`agent_adapter.harness_records()` builds this shape from an adapter's turn results; this module
does not import it, nor any driver or agent (lane lead's interface 5).

DECIDING. The agent's first turn has started once a turn produced completed agent output (the
gap4 lane lead's ruling on W1B-5); until then the take is `before-first-turn`, else
`after-first-turn` (`any` is both). A row matches when the take is in the row's phase, every
`all_of` condition holds, at least one `any_of` condition holds, and no `none_of` condition holds.
The matched rows at the highest precedence level win. If none match, or the winners name more
than one route, `route()` raises `RoutingRefused`: never a default, never a pick. Records already
committed are refused too, since a route decided after the commit cannot free its slot.

ANNOTATING. `annotate()` decides the table's annotations (an outside reach: an event, and the
text masked before commit; a quiescence kill: an event) on every take, in every phase, whatever
route wins and even when `route()` refuses the take. Rows never read the `events` record, so a
text-derived count can never route a take, and an annotation can never be lost to a route.

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
    "ledger": ("first_turn_started", "turns", "end", "turn_ends", "turn_outputs", "committed", "finalize_abort"),
    "exit": ("container_started", "container_exited", "exec_codes"),
    "cgroup": ("oom_kill_delta", "pids_max_delta"),
    "init": None,
    "pin": None,
    "api_errors": None,
    "sidecar": ("start_record", "stop_record", "exit_code", "queue_overflow"),
    "preflight": ("ok",),
    "operator": ("unexplained_diffs",),
    "checker_reasons": None,
    "quiescence_kill": None,
    "events": ("outside_reach",),
}

# The fields of one API-error record (both required; status int or None, type str or None).
API_ERROR_KEYS = ("status", "type")

# The plan's pin: "an init event whose model, mode or version differs from the pin".
PLAN_PIN_FIELDS = ("model", "permission_mode", "version")

# Records only annotations may read: text-derived counts never route a take.
ANNOTATION_ONLY = ("events",)

OPS = ("eq", "ne", "gt", "truthy", "falsy", "not_null", "is_null", "nonempty", "empty",
       "in_operator_reasons", "in_rate_limit_markers", "differs_from_pin", "nonzero_outside_timeout")
_VALUE_OPS = ("eq", "ne", "gt")


class TableError(ValueError):
    """routing.json is not a sound table."""


class RoutingRefused(ValueError):
    """The records cannot be routed: no row, a tie, a malformed or committed record."""


# --------------------------------------------------------------------------------------- types
def _is_bool(v) -> bool:
    return isinstance(v, bool)


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_count(v) -> bool:
    return _is_int(v) and v >= 0


def _is_str(v) -> bool:
    return isinstance(v, str)


# Leaf -> (type test, what it must be). Every scalar leaf of RECORD_SCHEMA's dict records is here
# except ledger.end, which is checked with the ledger's consistency below.
LEAF_TYPES = {
    "ledger.first_turn_started": (_is_bool, "a bool"),
    "ledger.turns": (_is_count, "a non-negative int"),
    "ledger.committed": (_is_bool, "a bool"),
    "ledger.finalize_abort": (_is_bool, "a bool"),
    "exit.container_started": (_is_bool, "a bool"),
    "exit.container_exited": (_is_bool, "a bool"),
    "cgroup.oom_kill_delta": (_is_count, "a non-negative int"),
    "cgroup.pids_max_delta": (_is_count, "a non-negative int"),
    "sidecar.start_record": (_is_bool, "a bool"),
    "sidecar.stop_record": (_is_bool, "a bool"),
    "sidecar.exit_code": (_is_int, "an int"),
    "sidecar.queue_overflow": (_is_bool, "a bool"),
    "preflight.ok": (_is_bool, "a bool"),
    "operator.unexplained_diffs": (_is_count, "a non-negative int"),
    "quiescence_kill": (_is_bool, "a bool"),
    "events.outside_reach": (_is_count, "a non-negative int"),
}
# Lists, element by element.
LIST_TYPES = {
    "ledger.turn_ends": (lambda v: v in labels4.TURN_ENDS, "a labels4 turn end"),
    "ledger.turn_outputs": (_is_bool, "a bool"),
    "exit.exec_codes": (lambda v: v is None or _is_int(v), "an int or None"),
    "checker_reasons": (_is_str, "a str"),
}


# --------------------------------------------------------------------------------------- the table
def _known_path(path: str) -> bool:
    head, _, tail = path.partition(".")
    if head not in RECORD_SCHEMA:
        return False
    if not tail:
        return True
    if head == "api_errors":
        return tail in API_ERROR_KEYS
    subs = RECORD_SCHEMA[head]
    return subs is not None and tail in subs


def _condition_problems(owner: str, conds: list, p: list):
    for c in conds:
        if not isinstance(c, dict):
            p.append(f"{owner}: a condition must be a dict")
            continue
        if c.get("op") not in OPS:
            p.append(f"{owner}: unknown op {c.get('op')!r}")
        if not _known_path(c.get("path", "")):
            p.append(f"{owner}: path {c.get('path')!r} is not a harness record")
        if c.get("op") in _VALUE_OPS and "value" not in c:
            p.append(f"{owner}: op {c.get('op')} needs a value")


def _graded_end_values(table: dict) -> set:
    """The ledger.end values the graded rows name."""
    return {c.get("value") for row in table["rows"] if row.get("route") == labels4.GRADED
            for g in ("all_of", "any_of") for c in row.get(g, [])
            if isinstance(c, dict) and c.get("path") == "ledger.end" and c.get("op") == "eq"}


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
    for key in ("pin_fields", "graded_ends", "rate_limit_markers", "operator_reasons", "operator_reasons_status",
                "pin_profiles", "pin_profiles_status", "rows", "annotations"):
        if key not in table:
            p.append(f"missing {key}")
    if p:
        return p
    if not isinstance(table["operator_reasons"], list) or not all(_is_str(r) for r in table["operator_reasons"]):
        p.append("operator_reasons must be a list of ids")
    elif len(set(table["operator_reasons"])) != len(table["operator_reasons"]):
        p.append("operator_reasons repeats an id")
    for key in ("operator_reasons_status", "pin_profiles_status"):
        if not _is_str(table[key]) or not table[key]:
            p.append(f"{key} must say where the data stands")
    if list(table["pin_fields"]) != list(PLAN_PIN_FIELDS):
        p.append(f"pin_fields must be the plan's {list(PLAN_PIN_FIELDS)}")
    profiles = table["pin_profiles"]
    if not isinstance(profiles, dict):
        p.append("pin_profiles must map a model id to its profile")
    else:
        for model, prof in profiles.items():
            if (not isinstance(prof, dict) or set(prof) != set(PLAN_PIN_FIELDS[1:])
                    or not all(_is_str(v) and v for v in prof.values())):
                p.append(f"pin profile {model!r} must give exactly {list(PLAN_PIN_FIELDS[1:])} as strings")
    # Graded ends are labels4's, and the graded rows name exactly them.
    if not isinstance(table["graded_ends"], list) or sorted(table["graded_ends"]) != sorted(labels4.GRADED_ENDS):
        p.append(f"graded_ends must be labels4.GRADED_ENDS {list(labels4.GRADED_ENDS)}")
    elif _graded_end_values(table) != set(table["graded_ends"]):
        p.append(f"the graded rows must name exactly the graded ends, got {sorted(map(str, _graded_end_values(table)))}")
    for row in table["rows"]:
        for g in ("all_of", "any_of", "none_of"):
            for c in row.get(g, []):
                if isinstance(c, dict) and c.get("path") == "ledger.end" and c.get("op") in ("eq", "ne") \
                        and c.get("value") not in labels4.TURN_ENDS:
                    p.append(f"{row.get('id')}: ledger.end compared with {c.get('value')!r}, not a labels4 turn end")
    # Rate-limit markers are API-error fields, each with a non-empty list of markers.
    markers = {k: v for k, v in table["rate_limit_markers"].items() if k != "source"}
    if not markers:
        p.append("rate_limit_markers names no marker")
    for k, v in markers.items():
        if k not in API_ERROR_KEYS:
            p.append(f"rate_limit_markers key {k!r} is not an API-error field {list(API_ERROR_KEYS)}")
        if not isinstance(v, list) or not v:
            p.append(f"rate_limit_markers {k!r} must be a non-empty list")
    ids = [row.get("id") for row in table["rows"]] + [a.get("id") for a in table["annotations"]]
    if len(set(ids)) != len(ids):
        p.append("row and annotation ids repeat")
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
        if "event" in row or "mask" in row:
            p.append(f"{rid}: event and mask are annotations, never routing rows")
        for group in ("all_of", "any_of", "none_of"):
            _condition_problems(rid, row.get(group, []), p)
            for c in row.get(group, []):
                if isinstance(c, dict) and c.get("path", "").partition(".")[0] in ANNOTATION_ONLY:
                    p.append(f"{rid}: a routing row reads {c.get('path')!r}, a text-derived count only annotations may read")
    for r in labels4.ROUTES:
        if r not in seen_routes:
            p.append(f"no row routes to {r}")
    for a in table["annotations"]:
        aid = a.get("id")
        if not a.get("source"):
            p.append(f"{aid}: no source cited")
        if set(a) - {"id", "event", "mask", "any_of", "source"}:
            p.append(f"{aid}: an annotation holds only id, event, mask, any_of and source")
        if not _is_bool(a.get("event")) or not _is_bool(a.get("mask")):
            p.append(f"{aid}: event and mask must be stated as bools")
        elif not (a["event"] or a["mask"]):
            p.append(f"{aid}: an annotation that is neither an event nor a mask does nothing")
        if not a.get("any_of"):
            p.append(f"{aid}: any_of must hold at least one condition")
        _condition_problems(aid, a.get("any_of", []), p)
    return p


def load_table(path: str = TABLE_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        table = json.load(fh)
    problems = check_table(table)
    if problems:
        raise TableError("; ".join(problems))
    return table


# ------------------------------------------------------------------------------------- the records
def _pin_problems(value, fields, what: str) -> list[str]:
    if not isinstance(value, dict) or set(value) != set(fields):
        return [f"{what} must hold exactly {list(fields)}"]
    if not all(_is_str(value[f]) for f in fields):
        return [f"{what} values must be strings"]
    return []


def shape_problems(records: dict, table: dict) -> list[str]:
    """The records' closed schema, every leaf's type, and their consistency (empty when sound)."""
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
    for path, (ok, what) in LEAF_TYPES.items():
        if not ok(_get(records, path)):
            p.append(f"{path} must be {what}, got {_get(records, path)!r}")
    for path, (ok, what) in LIST_TYPES.items():
        v = _get(records, path)
        if not isinstance(v, list):
            p.append(f"{path} must be a list")
        elif not all(ok(x) for x in v):
            p.append(f"every {path} entry must be {what}")
    if not isinstance(records["init"], list):
        p.append("init must be a list")
    else:
        for i, entry in enumerate(records["init"]):
            if entry is not None:
                p += _pin_problems(entry, table["pin_fields"], f"init[{i}]")
    p += _pin_problems(records["pin"], table["pin_fields"], "pin")
    if not isinstance(records["api_errors"], list):
        p.append("api_errors must be a list")
    else:
        for i, e in enumerate(records["api_errors"]):
            if not isinstance(e, dict) or set(e) != set(API_ERROR_KEYS):
                p.append(f"api_errors[{i}] must hold exactly {list(API_ERROR_KEYS)}")
            elif not (e["status"] is None or _is_int(e["status"])) or not (e["type"] is None or _is_str(e["type"])):
                p.append(f"api_errors[{i}]: status must be an int or None, type a str or None")
    if p:
        return p
    led = records["ledger"]
    n = led["turns"]
    if (len(led["turn_ends"]) != n or len(led["turn_outputs"]) != n or len(records["exit"]["exec_codes"]) != n
            or len(records["init"]) != n):
        p.append("per-turn records do not cover every turn")
    elif led["first_turn_started"] != any(led["turn_outputs"]):
        p.append("ledger.first_turn_started disagrees with ledger.turn_outputs")
    if n and led["end"] != led["turn_ends"][-1]:
        p.append("ledger.end is not the last turn's end")
    if not n and led["end"] is not None:
        p.append("ledger.end must be None when no turn ran")
    if len(records["api_errors"]) > n:
        p.append("more API-error records than turns: every API error belongs to a turn")
    if n and not records["preflight"]["ok"]:
        p.append("a take whose preflight failed cannot have run a turn")
    return p


def check_records(records: dict, table: dict) -> list[str]:
    """Everything that makes records unroutable: their shape, an unlisted checker reason, a pin
    that is not its model's pre-registered profile, an already committed take."""
    p = shape_problems(records, table)
    if p:
        return p
    unknown = [r for r in records["checker_reasons"] if r not in table["operator_reasons"]]
    if unknown:
        p.append(f"checker reason ids not in routing.json: {unknown}")
    pin = records["pin"]
    profile = table["pin_profiles"].get(pin["model"])
    if profile is None:
        p.append(f"pin model {pin['model']!r} has no pre-registered profile in routing.json's pin_profiles")
    elif any(pin[f] != profile[f] for f in profile):
        p.append(f"the pin is not {pin['model']!r}'s pre-registered profile: the driver is never trusted for it")
    if records["ledger"]["committed"]:
        p.append("the take is already committed: a route must be decided before the commit")
    return p


def _get(records: dict, path: str):
    head, _, tail = path.partition(".")
    value = records[head]
    if not tail:
        return value
    if head == "api_errors":
        return [e.get(tail) for e in value]
    return None if value is None else value.get(tail)


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
    if op == "nonempty":
        return len(v) > 0
    if op == "empty":
        return len(v) == 0
    if op == "in_operator_reasons":
        return any(r in table["operator_reasons"] for r in v)
    if op == "in_rate_limit_markers":
        markers = table["rate_limit_markers"].get(path.partition(".")[2], [])
        return any(x is not None and x in markers for x in v)
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


def annotate(records: dict, table: dict | None = None) -> dict:
    """The take's annotations, on every take in every phase, whatever route wins (or none does).

    Returns {"events": [ids of holding event annotations], "mask": bool}. Raises RoutingRefused
    only when the records are malformed (their shape or a leaf's type), since then no count can
    be trusted; a caller must then mask fail-closed.
    """
    table = table if table is not None else load_table()
    problems = shape_problems(records, table)
    if problems:
        raise RoutingRefused("; ".join(problems))
    held = [a for a in table["annotations"] if any(holds(c, records, table) for c in a["any_of"])]
    return {"events": [a["id"] for a in held if a["event"]], "mask": any(a["mask"] for a in held)}


def route(records: dict, table: dict | None = None) -> dict:
    """The one route for these records, or RoutingRefused.

    Returns {"route", "rows" (winning row ids), "matched" (every matched row id), "phase",
    "events", "mask" (both from `annotate`, never from the rows), "cap"}.
    """
    table = table if table is not None else load_table()
    problems = check_records(records, table)
    if problems:
        raise RoutingRefused("; ".join(problems))
    notes = annotate(records, table)
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
        "events": notes["events"],
        "mask": notes["mask"],
        "cap": table["caps"][routes[0]],
    }


def main(argv: list[str]) -> int:
    """`routing.py --check` validates routing.json; `routing.py <records.json>` routes one take."""
    if argv[:1] == ["--check"]:
        table = load_table()
        print(f"routing.json: {len(table['rows'])} rows, {len(table['annotations'])} annotations, sound")
        return 0
    if len(argv) == 1:
        with open(argv[0], encoding="utf-8") as fh:
            print(json.dumps(route(json.load(fh)), indent=1))
        return 0
    print("usage: routing.py --check | routing.py <records.json>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
