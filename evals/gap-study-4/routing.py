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
    init, pin        the init event of every turn (None when a turn had none), and the pin: the
                     take's harness (`AgentAdapter.name`, interface 8) and its pinned model, mode
                     and version; the pin must be the pre-registered profile of its model under its
                     harness in routing.json's pin_profiles (keyed by harness, then model), never
                     whatever the driver supplied. An init event names no harness
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
    unreadable_consequential   (CP2 ruling C3) the run-tree paths among the task's consequential ones
                     the sidecar could not read (non-empty strs), from the sidecar reply's field of
                     that name. After the agent's first turn a non-empty list routes harness-error
                     (unreadable-consequential-path); before it, it is refused (a preflight failure is
                     CP2's to fold into preflight.ok), never read as nothing
    quiescence_cap_survivors   (CP2 ruling C3; W2A2-6) the processes still alive at the quiescence cap
                     (int >= 0). After the first turn > 0 routes harness-error (quiescence-cap-reached),
                     and the operator-diff row does not also match; before it, > 0 is refused (lane
                     w4h decision)
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
A CLI that never printed its init event is harness-side too, so a silent timeout with no init event
rehearses (glitch-f3's ruling, 6 Oct 2026; glitch-f3's, not the owner's). After the first turn the
init-mismatch row reads `differs_from_pin`, where a missing init event is a mismatch.
A row matches when the take is in the row's phase, every `all_of` condition holds, at least one
`any_of` condition holds, and no `none_of` condition holds.
The matched rows at the highest precedence level win. If none match, or the winners name more
than one route, `route()` raises `RoutingRefused`: never a default, never a pick. Records already
committed are refused too, since a route decided after the commit cannot free its slot.

THE PIN REFUSAL (review round 3, W1B3-2: the gap4 lane lead's ruling; glitch-f3 accepted its stricter
reading, 6 Oct 2026; glitch-f3's, not the owner's). routing.json's `pin_refusal` is one rule beside
the rows: when the take is in its phase (before the agent's first turn) and every `all_of` condition
holds (an init event that is present and differs from the pin, `present_differs_from_pin`), `route()`
refuses the take for a human, whatever rows match, unless the winning route is one the rule names in
`outranked_by` (the rate-limit pause: a usage limit is not a pin fault). It is one rule, not a
`none_of` on each before-first-turn row, so the scope lives in one place: narrowing it (to timed-out
ends, say) is one condition appended to its `all_of`.

RATE-LIMIT MARKERS (glitch-f3's ruling, 6 Oct 2026). An API error carries a rate-limit marker when
its status or type is one of routing.json's markers for that field (exact membership), or when its
`text` carries one of the text markers by round 3's bounded search (`rate_limit_text_marker`): each
marker word-bounded and case-insensitive. The text matched is only ever the API-error record's own
harness-side text; the agent's reply never reaches the records. The markers, and the reset wait CP2's
`wait_reset` reads, are keyed by harness (`AgentAdapter.name`; w1b's next-touch item 1): the take's
own harness's entry is read (`pin.harness`), and a harness with no entry is refused, never defaulted.

THE SPEND-CAP REFUSAL (w1b's next-touch item 1; glitch-f3's ruling 4, 8 Oct 2026; glitch-f3's, not
the owner's). A vendor spend cap is not a rate limit: it arrives as a 429 too, and as a pause the loop
would wait for a window that never resets. routing.json's `spend_cap_refusal` is one closed rule
beside the rows, shaped like the pin refusal: in every phase, when an API error's status, type or text
carries a spend-cap marker of the take's own harness (`spend_cap_markers`, exact membership, the text
by the same bounded search), `route()` refuses the take for a human ruling, whatever rows match. It is
outranked by nothing, so it is decided above pause and a spend-cap 429 never reaches the rate-limit
row; it never re-runs and never waits. No route is added to labels4.ROUTES.

NO EMPTY LIST WHERE MONEY IS BILLED (lane w7c, ruling W7C-gap4-1, glitch-1b under Javier's standing delegation,
12 Oct 2026). An empty spend-cap list would let a spent cap arrive as a bare 429 and pause, waiting for a window that
never resets. So `check_table` (and with it `load_table` and `--check`) refuses a spend-cap entry that names no marker
in any field, for every harness except those in NO_MONEY_HARNESSES (claude-code: a subscription login, D4 A, that
bills no money per call, whose list may stay empty). PAID_HARNESSES names the harnesses that bill money (Codex CLI and
Gemini CLI, D8 B2) with the arm each runs and the vendor whose cap it spends; batch.py's money gate reads it. This
check holds whatever spend_cap_markers_status says: it is no ruling of that status, which stays the owner's.

ANNOTATING. `annotate()` decides the table's annotations (an outside reach: an event, and the
text masked before commit; a quiescence kill: an event; an event id arriving as a checker reason:
an event, and the text masked) on every take, in every phase, whatever route wins and even when
`route()` refuses the take. Rows never read the `events` record, so a text-derived count can never
route a take, and an annotation can never be lost to a route.

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

import json
import math
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
    "unreadable_consequential": None,    # CP2 ruling C3
    "quiescence_cap_survivors": None,    # CP2 ruling C3 (W2A2-6)
}

# Live harness 3b (14 Oct 2026): a record key that may be present, beside the closed schema. `identity` is a list, one
# entry per turn: None, or typed identity evidence (agent_adapter.identity_problems' shape). Records without it route
# exactly as before.
OPTIONAL_RECORDS = ("identity",)
IDENTITY_SOURCES = ("stream-init", "stream-stats", "version-exec", "submitted-argv", "unobserved")
# Which source routing accepts as evidence for which pin field (D8's per-harness table: Gemini's requested model is
# read from init.model and every result.stats.models key, its version from `gemini --version` in the take container,
# and its mode has no record but the pinned mode's flags on the submitted argv, bound by vendor_provenance). Any other
# source, an unobserved field or a value off the pin is a mismatch, exactly as a missing init event is.
ACCEPTED_IDENTITY_SOURCES = {"model": ("stream-init", "stream-stats"), "version": ("version-exec",),
                             "permission_mode": ("submitted-argv",)}
OBSERVED_IDENTITY_SOURCES = ("stream-init", "stream-stats", "version-exec")

# The fields of one API-error record (all three required; status int or None, type str or None, text
# str or None: the harness-side error text, never the agent's reply). glitch-f3's ruling added text.
API_ERROR_KEYS = ("status", "type", "text")
# Item 1 (lane w4h): each harness's rate-limit entry, and its spend-cap list, in routing.json (closed key sets).
RATE_MARKER_KEYS = API_ERROR_KEYS + ("reset_wait", "source")
SPEND_MARKER_KEYS = API_ERROR_KEYS + ("source",)
SPEND_REFUSAL_KEYS = ("id", "when", "any_of", "outranked_by", "source")
SPEND_OP = "in_spend_cap_markers"
# W7C (ruling W7C-gap4-1): the harness that bills no money per call, whose spend-cap list alone may be empty, and the
# harnesses that bill money (D8 B2), each with its arm and the vendor whose cap it spends (box/run_take.py's names,
# build_draft.HARNESSES's arms and costs.CAPS's vendors; tests/test_spend_wiring.py binds all three).
NO_MONEY_HARNESSES = ("claude-code",)
PAID_HARNESSES = {
    "codex": {"arm": "O", "vendor": "openai"},
    "gemini": {"arm": "G", "vendor": "google"},
}
# API-error fields whose rate-limit markers match by round 3's bounded search, not exact membership.
TEXT_MARKER_FIELDS = ("text",)

# The plan's pin: "an init event whose model, mode or version differs from the pin".
PLAN_PIN_FIELDS = ("model", "permission_mode", "version")
# The routing pin's keys (interface 8, w1b's next-touch item 5): the take's harness beside the plan's fields. An init
# event carries the plan's fields only; the harness is the pin's, read from the registered row's agent.
PIN_KEYS = ("harness",) + PLAN_PIN_FIELDS

# Records only annotations may read: text-derived counts never route a take.
ANNOTATION_ONLY = ("events",)

OPS = ("eq", "ne", "gt", "truthy", "falsy", "not_null", "is_null", "nonempty", "empty",
       "in_operator_reasons", "in_checker_events", "in_rate_limit_markers", "differs_from_pin",
       "present_differs_from_pin", "nonzero_outside_timeout", SPEND_OP)
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
    # CP2 ruling C3: checked whole, never coerced
    "unreadable_consequential": (lambda v: isinstance(v, list) and all(_is_str(x) and x for x in v),
                                 "a list of run-tree paths (non-empty strs)"),
    "quiescence_cap_survivors": (_is_count, "a non-negative int"),
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


def _condition_problems(owner: str, conds: list, p: list, spend: bool = False):
    for c in conds:
        if not isinstance(c, dict):
            p.append(f"{owner}: a condition must be a dict")
            continue
        if c.get("op") not in OPS:
            p.append(f"{owner}: unknown op {c.get('op')!r}")
        elif (c.get("op") == SPEND_OP) != spend:
            # item 1: only the spend-cap refusal reads the spend-cap lists, and it reads nothing else
            p.append(f"{owner}: op {c.get('op')!r} " + ("is read by the spend_cap_refusal alone" if not spend else
                                                       f"is not {SPEND_OP}, the spend_cap_refusal's only op"))
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
                "checker_reasons_become_events", "pin_profiles", "pin_profiles_status", "pin_refusal", "rows",
                "annotations", "spend_cap_markers", "spend_cap_markers_status", "spend_cap_refusal"):
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
    for key in ("operator_reasons_status", "pin_profiles_status", "rate_limit_markers_status", "spend_cap_markers_status"):
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
        p.append("pin_profiles must map a harness (AgentAdapter.name) to its models' profiles")
    else:
        # Interface 8 (item 5): keyed by harness, then model.
        for harness, models in profiles.items():
            if not _is_str(harness) or not harness or not isinstance(models, dict) or not models:
                p.append(f"pin_profiles {harness!r} must map a harness to a non-empty map of model ids to profiles "
                         f"(keyed by harness, then model)")
                continue
            for model, prof in models.items():
                if (not _is_str(model) or not model or not isinstance(prof, dict)
                        or set(prof) != set(PLAN_PIN_FIELDS[1:]) or not all(_is_str(v) and v for v in prof.values())):
                    p.append(f"pin profile {harness!r} {model!r} must give exactly {list(PLAN_PIN_FIELDS[1:])} "
                             f"as strings")
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
    p += _marker_problems(table)
    p += _pin_refusal_problems(table["pin_refusal"], order)
    p += _spend_refusal_problems(table["spend_cap_refusal"])
    ids = [row.get("id") for row in table["rows"]] + [a.get("id") for a in table["annotations"]]
    for rule in ("pin_refusal", "spend_cap_refusal"):
        if isinstance(table[rule], dict):
            ids.append(table[rule].get("id"))
    if len(set(ids)) != len(ids):
        p.append("row, annotation, pin_refusal and spend_cap_refusal ids repeat")
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


def _marker_list_problems(where: str, k: str, v, nonempty: bool) -> list[str]:
    """One API-error field's marker list: a list (non-empty for the rate-limit markers); statuses are ints, types
    non-empty strings, and text markers non-empty lower-case strings (round 3's search lowercases the error text only:
    an upper-case marker could never match, and an empty one would match at every word boundary)."""
    if not isinstance(v, list) or (nonempty and not v):
        return [f"{where} {k!r} must be a {'non-empty ' if nonempty else ''}list"]
    p = []
    for m in v:
        if k == "status" and not _is_int(m):
            p.append(f"{where} {k!r}: status {m!r} must be an int")
        elif k == "type" and not (_is_str(m) and m):
            p.append(f"{where} {k!r}: type {m!r} must be a non-empty string")
        elif k in TEXT_MARKER_FIELDS and (not _is_str(m) or not m or m != m.lower()):
            p.append(f"{where} {k!r}: text marker {m!r} must be a non-empty lower-case string")
    return p


def _marker_problems(table: dict) -> list[str]:
    """Item 1: the rate-limit markers (with each harness's reset wait) and the spend-cap lists, each keyed by harness;
    both name the same harnesses, every pin profile's harness has both, and no spend-cap marker of a harness is also
    one of its rate-limit markers (a spend cap is never a rate limit)."""
    p = []
    rate, spend = table["rate_limit_markers"], table["spend_cap_markers"]
    for key, entries, keys in (("rate_limit_markers", rate, RATE_MARKER_KEYS),
                               ("spend_cap_markers", spend, SPEND_MARKER_KEYS)):
        if not isinstance(entries, dict) or not entries:
            p.append(f"{key} must map each harness (AgentAdapter.name) to its entry")
            continue
        for harness, e in entries.items():
            where = f"{key} {harness!r}"
            if not _is_str(harness) or not harness:
                p.append(f"{key}: harness {harness!r} must be a non-empty name")
                continue
            if not isinstance(e, dict):
                p.append(f"{where} must be a dict of {list(keys)}")
                continue
            p += [f"{where} key {k!r} is not an API-error field {list(API_ERROR_KEYS)}" for k in e if k not in keys]
            p += [f"{where} has no {k}" for k in keys if k not in e]
            for k in API_ERROR_KEYS:
                if k in e:
                    p += _marker_list_problems(where, k, e[k], nonempty=key == "rate_limit_markers")
            # A backstop (W4H1-7, the lane lead's decision): each rate-limit list is already refused when empty above.
            if key == "rate_limit_markers" and all(isinstance(e.get(k), list) for k in API_ERROR_KEYS) \
                    and not any(e[k] for k in API_ERROR_KEYS):
                p.append(f"{where} names no marker")
            # W7C: a harness that bills money never has an empty spend-cap list; only a no-money harness's may be
            if key == "spend_cap_markers" and harness not in NO_MONEY_HARNESSES \
                    and all(isinstance(e.get(k), list) for k in API_ERROR_KEYS) and not any(e[k] for k in API_ERROR_KEYS):
                p.append(f"{where} names no spend-cap marker: a harness that bills money per call needs at least one, "
                         f"or a spent cap would pause for a window that never resets (only {list(NO_MONEY_HARNESSES)} "
                         f"may be empty; W7C)")
            if "source" in e and not (_is_str(e["source"]) and e["source"]):
                p.append(f"{where}: no source cited")
            if "reset_wait" in e:
                w = e["reset_wait"]
                if w is not None and not (isinstance(w, (int, float)) and not isinstance(w, bool)
                                          and math.isfinite(w) and w > 0):
                    p.append(f"{where}: reset_wait must be null (none stated) or a positive number of seconds, "
                             f"got {w!r}")
    if p or not isinstance(rate, dict) or not isinstance(spend, dict):
        return p
    if set(rate) != set(spend):
        p.append(f"rate_limit_markers and spend_cap_markers must name the same harnesses, got {sorted(rate)} and "
                 f"{sorted(spend)}")
    for harness in sorted(set(rate) & set(spend)):
        for k in API_ERROR_KEYS:
            both = set(rate[harness][k]) & set(spend[harness][k])
            if both:
                p.append(f"spend_cap_markers {harness!r} {k}: {sorted(both, key=str)} are also its rate-limit markers: "
                         f"a spend cap is never a rate limit")
    if isinstance(table["pin_profiles"], dict):
        for harness in table["pin_profiles"]:
            if harness not in rate:
                p.append(f"pin_profiles harness {harness!r} has no rate_limit_markers or spend_cap_markers entry")
    return p


def _spend_refusal_problems(rule) -> list[str]:
    """Item 1 (glitch-f3's ruling 4; W4BR-w4h-7): the spend-cap refusal is a closed rule. It applies in every phase, is
    outranked by nothing (so it is decided above pause), and reads only the API-error fields, with in_spend_cap_markers
    alone."""
    if not isinstance(rule, dict) or set(rule) != set(SPEND_REFUSAL_KEYS):
        return [f"spend_cap_refusal must hold exactly {list(SPEND_REFUSAL_KEYS)}"]
    p = []
    if not _is_str(rule["id"]) or not rule["id"]:
        p.append("spend_cap_refusal: no id")
    if rule["when"] != labels4.ANY_TIME:
        p.append(f"spend_cap_refusal: phase {rule['when']!r}, not {labels4.ANY_TIME!r} (a spend cap stops the loop in "
                 f"every phase)")
    if rule["outranked_by"] != []:
        p.append(f"spend_cap_refusal: outranked by nothing (glitch-f3's ruling 4: it ranks above pause), got "
                 f"{rule['outranked_by']!r}")
    if not isinstance(rule["any_of"], list) or not rule["any_of"]:
        p.append("spend_cap_refusal: any_of must hold at least one condition")
    else:
        _condition_problems("spend_cap_refusal", rule["any_of"], p, spend=True)
        for c in rule["any_of"]:
            if isinstance(c, dict) and c.get("path") not in [f"api_errors.{k}" for k in API_ERROR_KEYS]:
                p.append(f"spend_cap_refusal reads {c.get('path')!r}: only the API-error record's fields")
    if not rule["source"]:
        p.append("spend_cap_refusal: no source cited")
    return p


PIN_REFUSAL_KEYS = ("id", "when", "all_of", "outranked_by", "source")


def _pin_refusal_problems(rule, order: dict) -> list[str]:
    """W1B3-2: the pin refusal is a closed rule. Its phase is before the agent's first turn (after it, the plan routes
    a differing init as harness-error, the init-mismatch row); its conditions read harness records only; and only a
    route that outranks rehearsal may outrank it (else a pin mismatch could rehearse or grade)."""
    if not isinstance(rule, dict) or set(rule) != set(PIN_REFUSAL_KEYS):
        return [f"pin_refusal must hold exactly {list(PIN_REFUSAL_KEYS)}"]
    p = []
    if not _is_str(rule["id"]) or not rule["id"]:
        p.append("pin_refusal: no id")
    if rule["when"] != labels4.BEFORE_FIRST_TURN:
        p.append(f"pin_refusal: phase {rule['when']!r}, not {labels4.BEFORE_FIRST_TURN!r} (after the first turn the "
                 f"plan routes a differing init as harness-error)")
    if not isinstance(rule["all_of"], list) or not rule["all_of"]:
        p.append("pin_refusal: all_of must hold at least one condition")
    else:
        _condition_problems("pin_refusal", rule["all_of"], p)
        for c in rule["all_of"]:
            if isinstance(c, dict) and c.get("path", "").partition(".")[0] in ANNOTATION_ONLY:
                p.append(f"pin_refusal reads {c.get('path')!r}, a text-derived count only annotations may read")
    outranks = rule["outranked_by"]
    if not isinstance(outranks, list) or not all(r in labels4.ROUTES for r in outranks):
        p.append(f"pin_refusal: outranked_by must list labels4 routes, got {outranks!r}")
    elif labels4.REHEARSAL in order and any(order.get(r, len(order)) >= order[labels4.REHEARSAL] for r in outranks):
        p.append(f"pin_refusal: only a route that outranks rehearsal may outrank it, got {outranks}")
    if not rule["source"]:
        p.append("pin_refusal: no source cited")
    return p


def load_table(path: str | None = None) -> dict:
    with open(path or TABLE_PATH, encoding="utf-8") as fh:   # W7C: TABLE_PATH read at call time
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


def _identity_problems(entry) -> list[str]:
    if entry is None:
        return []
    if not isinstance(entry, dict) or set(entry) != set(PLAN_PIN_FIELDS):
        return [f"must be None or exactly {list(PLAN_PIN_FIELDS)}"]
    out = []
    for f in PLAN_PIN_FIELDS:
        e = entry[f]
        if not isinstance(e, dict) or set(e) != {"value", "source"} or e["source"] not in IDENTITY_SOURCES:
            out.append(f"{f} must be {{value, source}} with a source in {list(IDENTITY_SOURCES)}")
        elif (e["value"] is not None) == (e["source"] == "unobserved") or not (e["value"] is None or _is_str(e["value"])):
            out.append(f"{f}: an unobserved field carries no value, an observed one a string")
    return out


def _identity_differs(entry, pin, fields, *, present_only: bool) -> bool:
    """3b: a typed identity entry against the pin. present_only (the pin refusal): only an observed value that differs.
    Otherwise (the init-mismatch row): any field unobserved, from a source not accepted for it, or off the pin."""
    for f in fields:
        e = entry[f]
        if present_only:
            if e["source"] in OBSERVED_IDENTITY_SOURCES and e["value"] != pin[f]:
                return True
        elif e["source"] not in ACCEPTED_IDENTITY_SOURCES.get(f, ()) or e["value"] != pin[f]:
            return True
    return False


def shape_problems(records: dict, table: dict) -> list[str]:
    """The records' closed schema, every leaf's type, and their consistency (empty when sound)."""
    p = []
    if not isinstance(records, dict):
        return ["records must be a dict"]
    extra = set(records) - set(RECORD_SCHEMA) - set(OPTIONAL_RECORDS)
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
    p += _pin_problems(records["pin"], PIN_KEYS, "pin")
    if "identity" in records:                  # live harness 3b: typed, one entry per turn when present
        ids = records["identity"]
        if not isinstance(ids, list) or not isinstance(records["init"], list) or len(ids) != len(records["init"]):
            p.append("identity must be a list with one entry per turn")
        else:
            for i, entry in enumerate(ids):
                p += [f"identity[{i}]: {x}" for x in _identity_problems(entry)]
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
    models = table["pin_profiles"].get(pin["harness"])        # interface 8: keyed by harness, then model
    profile = None if models is None else models.get(pin["model"])
    if models is None:
        p.append(f"pin harness {pin['harness']!r} has no pre-registered profile in routing.json's pin_profiles")
    elif profile is None:
        p.append(f"pin model {pin['model']!r} has no pre-registered profile under harness {pin['harness']!r} in "
                 f"routing.json's pin_profiles")
    elif any(pin[f] != profile[f] for f in profile):
        p.append(f"the pin is not {pin['model']!r}'s pre-registered profile: the driver is never trusted for it")
    for key, what in (("rate_limit_markers", "rate-limit markers"), ("spend_cap_markers", "spend-cap list")):
        if pin["harness"] not in table[key]:   # item 1: the take's own harness's entry, never a default
            p.append(f"pin harness {pin['harness']!r} has no {what} in routing.json's {key}: refused, never defaulted")
    if records["ledger"]["committed"]:
        p.append("the take is already committed: a route must be decided before the commit")
    if phase_of(records) == labels4.BEFORE_FIRST_TURN:
        # CP2 ruling C3: before the agent's first turn an unreadable consequential path is a preflight failure (CP2
        # folds it into preflight.ok), so one arriving here is refused, never read as nothing; and (lane w4h's
        # decision, default-deny) so are processes alive at the quiescence cap
        if records["unreadable_consequential"]:
            p.append(f"unreadable_consequential {records['unreadable_consequential']} before the agent's first turn: "
                     f"a preflight failure, refused for a human (never read as nothing)")
        if records["quiescence_cap_survivors"]:
            p.append(f"quiescence_cap_survivors {records['quiescence_cap_survivors']} before the agent's first turn: "
                     f"refused for a human")
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
    if op in ("in_rate_limit_markers", SPEND_OP):   # the take's own harness's entry (item 1)
        field = path.partition(".")[2]
        markers = harness_markers(table, "rate_limit_markers" if op == "in_rate_limit_markers" else "spend_cap_markers",
                                  records)[field]
        if field in TEXT_MARKER_FIELDS:
            return any(x is not None and rate_limit_text_marker(x, markers) is not None for x in v)
        return any(x is not None and x in markers for x in v)
    if op == "differs_from_pin":            # a missing init event counts as a mismatch (lane w1b decision 5)
        pin, fields = records["pin"], table["pin_fields"]
        ids = records.get("identity") or [None] * len(v)     # 3b: typed evidence stands in for a missing init only
        if path != "init" or len(ids) != len(v):
            raise RoutingRefused("differs_from_pin reads init with one identity entry per turn")
        return any((i is None and e is None)
                   or (i is not None and any(i.get(f) != pin[f] for f in fields))
                   or (e is not None and _identity_differs(e, pin, fields, present_only=False))
                   for i, e in zip(v, ids))
    if op == "present_differs_from_pin":    # only an init event that is there and differs (glitch-f3's ruling)
        pin, fields = records["pin"], table["pin_fields"]
        ids = records.get("identity") or [None] * len(v)
        if path != "init" or len(ids) != len(v):
            raise RoutingRefused("present_differs_from_pin reads init with one identity entry per turn")
        return any((i is not None and any(i.get(f) != pin[f] for f in fields))
                   or (e is not None and _identity_differs(e, pin, fields, present_only=True))
                   for i, e in zip(v, ids))
    if op == "nonzero_outside_timeout":
        ends = records["ledger"]["turn_ends"]
        return any(code != 0 for code, end in zip(v, ends) if end != labels4.TIMED_OUT)
    raise TableError(f"unknown op {op!r}")


def harness_markers(table: dict, key: str, records: dict) -> dict:
    """The take's own harness's entry of routing.json's `key` (rate_limit_markers or spend_cap_markers), read by its
    pin's harness (item 1). check_records refuses a harness with no entry before any condition is read."""
    return table[key][records["pin"]["harness"]]


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


def pin_refusal_holds(records: dict, table: dict) -> bool:
    """routing.json's pin refusal holds on these records (W1B3-2): its phase, and every all_of condition."""
    rule = table["pin_refusal"]
    if rule["when"] not in (labels4.ANY_TIME, phase_of(records)):
        return False
    return all(holds(c, records, table) for c in rule["all_of"])


def spend_cap_holds(records: dict, table: dict) -> bool:
    """routing.json's spend-cap refusal holds on these records (item 1): its phase, and any of its conditions."""
    rule = table["spend_cap_refusal"]
    if rule["when"] not in (labels4.ANY_TIME, phase_of(records)):
        return False
    return any(holds(c, records, table) for c in rule["any_of"])


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
    level = {r: i for i, lvl in enumerate(table["precedence"]) for r in lvl}
    top = min((level[row["route"]] for row in matched), default=None)
    winners = [row for row in matched if level[row["route"]] == top]
    routes = sorted({row["route"] for row in winners})
    spend = table["spend_cap_refusal"]
    if spend_cap_holds(records, table):
        # item 1 (glitch-f3's ruling 4): outranked by nothing, so above pause; a human rules, never a re-run or a wait.
        # Lane review round 1, W4H1-2: checked whatever the table's outranked_by says (check_table fixes it to []).
        raise RoutingRefused(f"{spend['id']}: an API error carries a spend-cap marker of harness "
                             f"{records['pin']['harness']!r}: a spend cap, not a rate limit; refused for a human ruling "
                             f"whatever else matches (matched {[m['id'] for m in matched]}): it never re-runs and never "
                             f"waits for a usage window")
    rule = table["pin_refusal"]
    if pin_refusal_holds(records, table) and not set(routes) & set(rule["outranked_by"]):
        # W1B3-2: whatever else matches; only a route the rule names (the rate-limit pause) outranks it
        raise RoutingRefused(f"{rule['id']}: before the agent's first turn an init event is present and differs from "
                             f"the pin: a pin mismatch, refused for a human whatever else matches "
                             f"(matched {[m['id'] for m in matched]}; only {rule['outranked_by']} outranks it)")
    if not matched:
        raise RoutingRefused(f"no row matches these records (phase {phase_of(records)})")
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
