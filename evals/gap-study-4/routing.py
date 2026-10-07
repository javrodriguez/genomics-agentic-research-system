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
    api_errors       every API-error record of the take, in turn order and, within a turn, in the
                     order met (a turn can meet several, W1B2-7): {status: int or None,
                     type: str or None, text: str or None}. `text` is the harness-side error text
                     (what Claude Code or the API reported as the error), never the agent's reply
    sidecar          the watcher's health: start_record, stop_record (bools), exit_code (int),
                     queue_overflow (bool)
    preflight        ok (bool)
    operator         unexplained_diffs (count): operator-step diffs no logged operator event explains
    checker_reasons  the checker's reason ids (strs), computed in the drive step. An id listed in
                     routing.json's reasons_only_before_first_turn (no-first-agent-turn) after
                     the agent's first turn started is refused (W1B2-8)
    quiescence_kill  (bool) the box stopped a background process at the quiescence cap
    events           outside_reach (count, int >= 0): how many outside-reach EVENTS the drive step
                     recorded for the take, each one an instance of the agent's own text or actions
                     reaching the token, the account email, a study path or anything outside the run
                     tree. It counts what the drive step's own scans find and what round 4's checker
                     reports as events (the ids in routing.json's checker_reasons_become_events:
                     study-materials-reached, account-email, read-outside-the-checkout), one per
                     event, never per turn or per take; 0 means none was found. It does NOT count
                     those ids when they arrive in checker_reasons instead: the
                     `checker-event-reason` annotation covers that case (review round 2, W1B2-2).
                     It is derived from the agent's text and actions, so only annotations read it

`agent_adapter.harness_records()` builds this shape from an adapter's turn results; this module
does not import it, nor any driver or agent (lane lead's interface 5).

DECIDING. The agent's first turn has started once a turn produced completed agent output (the
gap4 lane lead's ruling on W1B-5), however that turn or any earlier one ended; until then the take
is `before-first-turn`, else `after-first-turn` (`any` is both). A turn that timed out without
completed output has not started it: glitch-f3's correction (6 Oct 2026; glitch-f3's, not the
owner's) routes a bare silent timeout as a rehearsal on its own row, because harness records
cannot tell it from a hung API, CLI or egress (review round 2, W1B2-1, reverting 3fcab58d).
That row reads the init events with `present_differs_from_pin`, not `differs_from_pin`: a CLI
that never printed its init event is harness-side too, so a silent timeout with no init event
rehearses, while one whose init event differs from the pin matches no row and is refused for a
human (glitch-f3's ruling, 6 Oct 2026; glitch-f3's, not the owner's). After the first turn the
init-mismatch row keeps `differs_from_pin`, where a missing init event is a mismatch.
A row matches when the take is in the row's phase, every `all_of` condition holds, at least one
`any_of` condition holds, and no `none_of` condition holds.
The matched rows at the highest precedence level win. If none match, or the winners name more
than one route, `route()` raises `RoutingRefused`: never a default, never a pick. Records already
committed are refused too, since a route decided after the commit cannot free its slot.

RATE-LIMIT MARKERS (glitch-f3's ruling, 6 Oct 2026). An API error carries a rate-limit marker when
its status or type is one of routing.json's markers for that field (exact membership), or when its
`text` carries one of the text markers by round 3's bounded search (`rate_limit_text_marker`): each
marker word-bounded and case-insensitive. The text matched is only ever the API-error record's own
harness-side text; the agent's reply never reaches the records.

ANNOTATING. `annotate()` decides the table's annotations (an outside reach: an event, and the
text masked before commit; a quiescence kill: an event; an event id arriving as a checker reason:
an event, and the text masked) on every take, in every phase, whatever route wins and even when
`route()` refuses the take. Rows never read the `events` record, so a text-derived count can never
route a take, and an annotation can never be lost to a route.

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

import json
import os
import re
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

# The fields of one API-error record (all three required; status int or None, type str or None, text
# str or None: the harness-side error text, never the agent's reply). glitch-f3's ruling added text.
API_ERROR_KEYS = ("status", "type", "text")
# API-error fields whose rate-limit markers match by round 3's bounded search, not exact membership.
TEXT_MARKER_FIELDS = ("text",)

# The plan's pin: "an init event whose model, mode or version differs from the pin".
PLAN_PIN_FIELDS = ("model", "permission_mode", "version")

# Records only annotations may read: text-derived counts never route a take.
ANNOTATION_ONLY = ("events",)

OPS = ("eq", "ne", "gt", "truthy", "falsy", "not_null", "is_null", "nonempty", "empty",
       "in_operator_reasons", "in_checker_events", "in_rate_limit_markers", "differs_from_pin",
       "present_differs_from_pin", "nonzero_outside_timeout")
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
    # glitch-f3 (6 Oct 2026): rehearsal and pause count events per half-cell, under a name that says so; the old
    # name, whose meaning changed, is refused there, so no reader can take it for re-runs.
    for r in (labels4.REHEARSAL, labels4.PAUSE):
        if r in caps and isinstance(caps[r], dict):
            if "reruns_per_half_cell" in caps[r]:
                p.append(f"caps.{r} carries reruns_per_half_cell; its per-half-cell cap is events_per_half_cell")
            if "events_per_half_cell" not in caps[r]:
                p.append(f"caps.{r} has no events_per_half_cell")
    for key in ("pin_fields", "graded_ends", "rate_limit_markers", "rate_limit_markers_status", "operator_reasons",
                "operator_reasons_status", "driver_decided_reasons", "reasons_only_before_first_turn",
                "checker_reasons_become_events", "pin_profiles", "pin_profiles_status", "rows", "annotations"):
        if key not in table:
            p.append(f"missing {key}")
    if p:
        return p
    if not isinstance(table["operator_reasons"], list) or not all(_is_str(r) for r in table["operator_reasons"]):
        p.append("operator_reasons must be a list of ids")
    elif len(set(table["operator_reasons"])) != len(table["operator_reasons"]):
        p.append("operator_reasons repeats an id")
    events = table["checker_reasons_become_events"]
    if (not isinstance(events, dict) or not isinstance(events.get("ids"), list) or not events["ids"]
            or not all(_is_str(r) and r for r in events["ids"]) or not events.get("source")):
        p.append("checker_reasons_become_events must give a non-empty list of ids and its source")
    elif set(events["ids"]) & set(table["operator_reasons"] if isinstance(table["operator_reasons"], list) else []):
        # W1B2-2/W1B2-10: an event id listed as an operator reason would route a rehearsal or harness-error
        # where the plan says "graded as usual, the text masked".
        p.append(f"operator_reasons and checker_reasons_become_events share ids "
                 f"{sorted(set(events['ids']) & set(table['operator_reasons']))}: an event is never an operator reason")
    for key in ("operator_reasons_status", "pin_profiles_status", "rate_limit_markers_status"):
        if not _is_str(table[key]) or not table[key]:
            p.append(f"{key} must say where the data stands")
    listed = set(table["operator_reasons"]) if isinstance(table["operator_reasons"], list) else set()
    for key, why in (("driver_decided_reasons", "each routes by the generic operator-reason rows"),
                     ("reasons_only_before_first_turn", "each is refused after the first turn, routed before it")):
        sub = table[key]
        if (not isinstance(sub, dict) or not isinstance(sub.get("ids"), list) or not sub["ids"]
                or not all(_is_str(r) and r for r in sub["ids"]) or not sub.get("source")):
            p.append(f"{key} must give a non-empty list of ids and its source")
        elif not set(sub["ids"]) <= listed:
            # W1B2-10, W1B2-8: an id outside operator_reasons would be refused as unlisted, never routed.
            p.append(f"{key} ids {sorted(set(sub['ids']) - listed)} are not in operator_reasons ({why})")
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
        elif k in TEXT_MARKER_FIELDS:
            # Round 3's search lowercases the error text only: an upper-case marker could never match,
            # and an empty one would match at every word boundary.
            for m in v:
                if not _is_str(m) or not m or m != m.lower():
                    p.append(f"rate_limit_markers {k!r}: text marker {m!r} must be a non-empty lower-case string")
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
            elif (not (e["status"] is None or _is_int(e["status"])) or not (e["type"] is None or _is_str(e["type"]))
                  or not (e["text"] is None or _is_str(e["text"]))):
                p.append(f"api_errors[{i}]: status must be an int or None, type and text a str or None")
    if p:
        return p
    led = records["ledger"]
    n = led["turns"]
    if (len(led["turn_ends"]) != n or len(led["turn_outputs"]) != n or len(records["exit"]["exec_codes"]) != n
            or len(records["init"]) != n):
        p.append("per-turn records do not cover every turn")
    elif led["first_turn_started"] != any(led["turn_outputs"]):
        # W1B-5 and W1B2-1: completed agent output, and nothing else, starts the agent's first turn.
        p.append("ledger.first_turn_started disagrees with ledger.turn_outputs")
    if n and led["end"] != led["turn_ends"][-1]:
        p.append("ledger.end is not the last turn's end")
    if not n and led["end"] is not None:
        p.append("ledger.end must be None when no turn ran")
    if records["api_errors"] and not n:
        # W1B2-7 dropped "no more API errors than turns" (one turn can meet several); an API error with no turn
        # at all still belongs to nothing (lane w1b decision).
        p.append("API-error records with no turn: every API error belongs to a turn")
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
    early = [r for r in records["checker_reasons"] if r in table["reasons_only_before_first_turn"]["ids"]]
    if early and phase_of(records) == labels4.AFTER_FIRST_TURN:
        # W1B2-8: the reason says "before the first turn" while the harness records say it started.
        p.append(f"checker reason(s) {early} mean before the agent's first turn, and the records show it started "
                 f"(completed agent output): the checker and the records disagree, so a human must look")
    return p


def _get(records: dict, path: str):
    head, _, tail = path.partition(".")
    value = records[head]
    if not tail:
        return value
    if head == "api_errors":
        return [e.get(tail) for e in value]
    return None if value is None else value.get(tail)


def rate_limit_text_marker(text: str, markers) -> str | None:
    """The first of `markers` that `text` carries, by round 3's bounded search (matched_marker,
    evals/gap-study-3/drive.py:912-919 at e2979b3143081824aadea73523ec41af30c1ddb1): each marker
    word-bounded and case-insensitive, the text lowercased (the markers are lower-case; check_table
    enforces it). Called only on an API-error record's harness-side `text`, never on the agent's."""
    low = text.lower()
    for m in markers:
        if re.search(r"(?<![\w])" + re.escape(m) + r"(?![\w])", low):
            return m
    return None


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
    if op == "in_checker_events":
        return any(r in table["checker_reasons_become_events"]["ids"] for r in v)
    if op == "in_rate_limit_markers":
        field = path.partition(".")[2]
        markers = table["rate_limit_markers"].get(field, [])
        if field in TEXT_MARKER_FIELDS:
            return any(x is not None and rate_limit_text_marker(x, markers) is not None for x in v)
        return any(x is not None and x in markers for x in v)
    if op == "differs_from_pin":            # a missing init event counts as a mismatch (lane w1b decision 5)
        pin = records["pin"]
        return any(i is None or any(i.get(f) != pin[f] for f in table["pin_fields"]) for i in v)
    if op == "present_differs_from_pin":    # only an init event that is there and differs (glitch-f3's ruling)
        pin = records["pin"]
        return any(i is not None and any(i.get(f) != pin[f] for f in table["pin_fields"]) for i in v)
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
