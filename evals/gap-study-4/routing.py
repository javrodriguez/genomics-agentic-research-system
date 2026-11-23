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
    checker_reasons  the checker's reason ids (strs), computed in the drive step: routing.json's
                     operator_reasons, or its agent_event_reasons (pre-freeze review 2, MAJOR 1). An id
                     listed in reasons_only_before_first_turn (no-first-agent-turn) after the agent's
                     first turn started is refused (W1B2-8), and so is an agent event reason before it
    quiescence_kill  (bool) the box stopped a background process at the quiescence cap
    unreadable_consequential   (CP2 ruling C3) the run-tree paths among the task's consequential ones
                     the sidecar could not read (non-empty strs), from the sidecar reply's field of
                     that name. After the agent's first turn a non-empty list routes harness-error
                     (unreadable-consequential-path); before it, it is refused (a preflight failure is
                     CP2's to fold into preflight.ok), never read as nothing
    quiescence_cap_survivors   (CP2 ruling C3; W2A2-6) the processes still alive at the quiescence cap
                     (int >= 0). After the first turn > 0 routes graded with an agent event
                     (quiescence-cap-reached; pre-freeze review 1, MAJOR 5, re-routed it from harness-error),
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
in any field, for every harness except those in EMPTY_SPEND_LIST_HARNESSES (claude-code alone: a subscription login,
D4 A, that bills no money per call, whose list may stay empty). Since round 17 B7-F4 (glitch-b5, 18 Oct 2026) codex's
list holds the pinned CLI's out-of-credits, spend-cap and quota-exceeded texts, so codex is not in that tuple. The
tuple is apart from NO_MONEY_HARNESSES, which batch.py's money gate reads. PAID_HARNESSES names the harnesses that
bill money (Codex CLI and Gemini CLI, D8 B2) with the arm each runs and the vendor whose cap it spends; batch.py's
money gate reads it. This check holds whatever spend_cap_markers_status says and is no ruling of that status: the
status is ruled by the owner or under his delegation, and its line says which (B7-F5).

ANNOTATING. `annotate()` decides the table's annotations (an outside reach: an event, and the
text masked before commit; a quiescence kill: an event; an event id arriving as a checker reason:
an event, and the text masked) on every take, in every phase, whatever route wins and even when
`route()` refuses the take. Rows never read the `events` record, so a text-derived count can never
route a take, and an annotation can never be lost to a route.

AGENT EVENT ROWS (pre-freeze review 1, MAJOR 5; lane pf1-l2a, the Lane-orchestrator's approval of the fold plan, Sat 24
Oct 2026, under Javier's standing delegation). After the first turn, a process alive at the quiescence cap
(quiescence-cap-reached) and a non-zero exec exit with no API error and no counter rise (nonzero-exec-exit) are the
agent's own acts as far as harness records can tell, so both rows route graded, never harness-error: the plan's graded
rule says no try is discarded or re-run for something the agent did. routing.json's agent_event_rows names them;
`check_table` refuses an id there that is not a graded after-first-turn row; run.py writes the winning ones into the
take record's agent_events, and stats counts each in its own column.

AGENT EVENT REASONS (pre-freeze review 2, MAJOR 1, F1-2; fold plan prefreeze-2, the lane orchestrator's approval, 29 Oct
2026, under Javier's standing delegation). A checker reason the agent's own ordinary command produces and that harms no
record (store-variable-assigned: a bare assignment of HOME or an agent CLI's store variable) is listed in routing.json's
agent_event_reasons, never in operator_reasons, so the generic operator-reason rows never read it: after the first turn
its own graded row (has) routes the take graded, an agent event of the record. `check_table` refuses an id in both lists
or with no such row, and `check_records` refuses one before the first turn.

THE CLASS TABLE (pre-freeze review 2, MAJOR 1, step 1; fold plan prefreeze-2, the lane orchestrator's approval, 29 Oct
2026). routing.json's agent_reach answers, for every row that does not route graded after the first turn, the two
refusal rules and every reason routing reads, whether the agent can produce the record it reads, and how. `check_table`
requires the key; `reach_problems` (load_table, and so --check, runs it after check_table) refuses a missing or extra
entry, a stated route
that is not the table's own (`reason_route` for a reason), and an agent-reachable entry whose route re-runs or refuses
its take with no stated call (a named exception or a ruling owed).

THE NO-MATCH PROOF (pre-freeze review 1, m17; the same approval). `--check` enumerates the table's closed input
classes for every pin harness (`no_match_classes`: each condition's truth read through PROOF_CONDITIONS, each variable
through PROOF_DOMAINS, a branch closed once a row surely matches) and lists every class no row matches by its phase and
the last turn's end; `no_match_problems` refuses a class with no entry in routing.json's no_match_defaults, an entry no
class reaches, and a condition outside PROOF_CONDITIONS. Such a take is still refused by `route()` (batch commits it
blocked, for a look), and `no_match_default` gives the one ruling batch.py accepts for it. After the first turn its
entry may carry an `unreadable` alternative (lane fold2/merge, the no-match residual of pre-freeze review 2's m6): a
route ruling to aborted, cited "end state unreadable", which batch.py accepts in place of the default only with a cite
naming the reading the grader could not make (`no_match_unreadable`); --check refuses it before the first turn, beside
any default but graded, and in any other shape.

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

import copy
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
IDENTITY_SOURCES = ("stream-init", "stream-stats", "version-exec", "submitted-argv", "stream-reroute", "unobserved")
# Which source routing accepts as evidence for which pin field, keyed by the pin's harness (D8's per-harness table).
# Gemini: requested model from init.model and every result.stats.models key, version from `gemini --version` in the
# take container, mode from the turn's actual-submission journal argv (gemini_adapter.submitted_mode; unobserved when
# no journal exists). Any other source, an unobserved field or a value off the pin is a mismatch, exactly as a
# missing init event is. A harness with no entry (claude-code, whose mode must come from its init event) carries no
# identity at all: shape_problems refuses it.
# Codex slice 2 (glitch-06, 14 Oct 2026): codex's served model is observed only by an exec reroute item
# (stream-reroute, codex_adapter.read_stream); the rollout's turn_context names the REQUESTED model and is never proof,
# so without a reroute the model is unobserved, and the init-mismatch row then reads a Codex turn as a mismatch (a
# consequence named for a ruling in lane-reports/codex-identity-table-2026-10-14.md). version: `codex --version` in the
# take container; mode: the turn's launch journal checked by vendor_provenance.launch_facts.
ACCEPTED_IDENTITY_SOURCES = {"gemini": {"model": ("stream-init", "stream-stats"), "version": ("version-exec",),
                                        "permission_mode": ("submitted-argv",)},
                             "codex": {"model": ("stream-reroute",), "version": ("version-exec",),
                                       "permission_mode": ("submitted-argv",)}}
OBSERVED_IDENTITY_SOURCES = ("stream-init", "stream-stats", "version-exec", "stream-reroute")
# Departure D-INT-2 (ruled by glitch-06 under the standing delegation, 14 Oct 2026; flagged first for Javier's review
# before the freeze): for arm O (codex) only, a served model that is unobserved (no reroute) is accepted by the
# init-mismatch row, so the requested model is assumed; an observed reroute to another model is still a mismatch, two
# reroutes still refuse (codex_adapter), and every other harness and field is unchanged. The study's limit, verbatim:
UNOBSERVED_ACCEPTED = {"codex": ("model",)}
SERVED_MODEL_LIMIT = ("for the OpenAI arm, the served model is verified only when the CLI reports a reroute; otherwise "
                      "the requested model is assumed")

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
# Round 17 B7 (glitch-b5's ruling (1) of CONTINUED (3), 18 Oct 2026): the harnesses whose spend-cap list alone may
# be empty, each with its reason. check_table reads this tuple, never NO_MONEY_HARNESSES (bills_money reads that one,
# unchanged). Round 17 B7-F4 (glitch-b5, 18 Oct 2026): codex left it; its list holds the pinned CLI's spend texts.
EMPTY_SPEND_LIST_HARNESSES = ("claude-code",)
EMPTY_SPEND_LIST_REASONS = {
    "claude-code": "a subscription login (D4 A) bills no money per call and names no spend-cap error; a usage or "
                   "weekly limit pauses under rate_limit_markers (the owner's 12 Oct 2026 ruling, choice 1A)",
}
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
       "present_differs_from_pin", "nonzero_outside_timeout", "has", SPEND_OP)
_VALUE_OPS = ("eq", "ne", "gt", "has")
# glitch-b5's ruling 3 (17 Oct 2026): `has` holds when checker_reasons carries its value, one named operator reason.
HAS_PATH = "checker_reasons"

# Pre-freeze review 1 (lane pf1-l2a, the Lane-orchestrator's approval of the fold plan, 24 Oct 2026): MAJOR 5's agent
# event rows and m17's pre-registered ruling defaults for the inputs no row matches (THE NO-MATCH PROOF, below).
AGENT_EVENTS_KEY = "agent_event_rows"
NO_MATCH_KEY = "no_match_defaults"
NO_MATCH_ENTRY_KEYS = ("when", "end", "ruling", "route", "why")
# Lane fold2/merge (glitch-45's assignment, Thu 29 Oct 2026, under Javier's standing delegation): the no-match take
# after the first turn whose end state its grader cannot read. Pre-freeze review 2's m6 refuses its graded default, so
# its entry may carry this one alternative, exactly these keys: a route ruling to aborted, cited with the phrase below
# (batch.END_STATE_UNREAD_CITE is this constant; check_results.unread_cite adds the reading's exception type).
NO_MATCH_UNREADABLE_KEY = "unreadable"
NO_MATCH_UNREADABLE_KEYS = ("ruling", "route", "cite", "why")
END_STATE_UNREAD_CITE = "end state unreadable"
# The review of 5afd80a7, finding 5, and the Lane-orchestrator's ruling on it: agent_event_rows is exactly these two.
AGENT_EVENT_IDS = ("nonzero-exec-exit", "quiescence-cap-reached", "store-variable-assigned")
# Pre-freeze review 2, MAJOR 1 (F1-2): the checker reasons that route graded with an agent event, apart from
# operator_reasons (AGENT EVENT REASONS, above).
AGENT_EVENT_REASONS_KEY = "agent_event_reasons"
# Pre-freeze review 2, MAJOR 1, step 1: the class table (THE CLASS TABLE, below).
AGENT_REACH_KEY = "agent_reach"
REACH_KINDS = ("row", "rule", "reason")
REACH_ENTRY_KEYS = ("reachable", "how", "route", "call")
REACH_REFUSED = "refused"
REACH_FINAL = ("aborted", "graded")


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
                "annotations", "spend_cap_markers", "spend_cap_markers_status", "spend_cap_refusal",
                AGENT_EVENTS_KEY, NO_MATCH_KEY, AGENT_EVENT_REASONS_KEY, AGENT_REACH_KEY):
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
    p += _agent_event_reason_problems(table, listed)
    readable = listed | set(agent_event_reasons(table))     # the reasons a `has` condition may name
    # glitch-6b (15 Oct 2026): every operator reason is round 3's, with its round-3 source, or a named round-4
    # addition with its own ruling (operator_reasons_round4); never both, never neither.
    r3 = table.get("operator_reason_sources")
    r4 = table.get("operator_reasons_round4")
    if not isinstance(r3, dict):
        p.append("operator_reason_sources must map each of round 3's operator reasons to its source")
        r3 = {}
    if (not isinstance(r4, dict) or not isinstance(r4.get("ids"), list) or not all(_is_str(r) and r for r in r4["ids"])
            or not isinstance(r4.get("sources"), dict) or set(r4["sources"]) != set(r4["ids"])
            or not all(isinstance(s, dict) and _is_str(s.get("ruling")) and s["ruling"] and _is_str(s.get("meaning"))
                       and s["meaning"] and _is_str(s.get("emitted_at")) and s["emitted_at"]
                       for s in r4["sources"].values())):
        p.append("operator_reasons_round4 must give its ids and, for each, a source naming its ruling, meaning and "
                 "emitted_at")
        r4 = {"ids": []}
    added = set(r4["ids"])
    if added & set(r3):
        p.append(f"operator reasons {sorted(added & set(r3))} carry both a round-3 source and a round-4 ruling")
    if not added <= listed:
        p.append(f"operator_reasons_round4 ids {sorted(added - listed)} are not in operator_reasons")
    if listed - added - set(r3):
        p.append(f"operator reasons {sorted(listed - added - set(r3))} have neither a round-3 source nor a round-4 "
                 f"ruling")
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
                if isinstance(c, dict) and c.get("op") == "has" and (c.get("path") != HAS_PATH
                                                                     or c.get("value") not in readable):
                    # glitch-b5's ruling 3 (17 Oct 2026): `has` names one operator reason of checker_reasons (or, since
                    # pre-freeze review 2's MAJOR 1, one agent event reason)
                    p.append(f"{rid}: op has reads {HAS_PATH} for one of operator_reasons or agent_event_reasons, got "
                             f"{c.get('path')!r} {c.get('value')!r}")
    for r in labels4.ROUTES:
        if r not in seen_routes:
            p.append(f"no row routes to {r}")
    p += _agent_event_problems(table)
    p += _no_match_default_problems(table)
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
        for c in a.get("any_of", []):
            if isinstance(c, dict) and c.get("op") == "has" and (c.get("path") != HAS_PATH or c.get("value") not in listed):
                p.append(f"{aid}: op has reads {HAS_PATH} for one of operator_reasons, got {c.get('path')!r} "
                         f"{c.get('value')!r}")
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
            if key == "spend_cap_markers" and harness not in EMPTY_SPEND_LIST_HARNESSES \
                    and all(isinstance(e.get(k), list) for k in API_ERROR_KEYS) and not any(e[k] for k in API_ERROR_KEYS):
                p.append(f"{where} names no spend-cap marker: a harness that bills money per call needs at least one, "
                         f"or a spent cap would pause for a window that never resets (only {list(EMPTY_SPEND_LIST_HARNESSES)} "
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


def agent_event_reasons(table: dict) -> tuple:
    """Pre-freeze review 2, MAJOR 1: routing.json's agent_event_reasons ids ((): a table check_table refuses)."""
    sub = table.get(AGENT_EVENT_REASONS_KEY)
    ids = sub.get("ids") if isinstance(sub, dict) else None
    return tuple(i for i in ids if _is_str(i)) if isinstance(ids, list) else ()


def _agent_event_reason_problems(table: dict, listed: set) -> list[str]:
    """MAJOR 1 of pre-freeze review 2: agent_event_reasons gives its ids and source; no id is an operator reason or a
    checker event; each is read by exactly one row, a graded after-first-turn row that names it with has alone, and that
    row is an agent event row."""
    sub = table[AGENT_EVENT_REASONS_KEY]
    if (not isinstance(sub, dict) or set(sub) != {"ids", "source"} or not isinstance(sub["ids"], list) or not sub["ids"]
            or not all(_is_str(i) and i for i in sub["ids"]) or len(set(sub["ids"])) != len(sub["ids"])
            or not (_is_str(sub["source"]) and sub["source"])):
        return [f"{AGENT_EVENT_REASONS_KEY} must give a non-empty list of distinct ids and its source"]
    p = []
    events = table["checker_reasons_become_events"].get("ids") if isinstance(
        table["checker_reasons_become_events"], dict) else None
    both = set(sub["ids"]) & (listed | set(events if isinstance(events, list) else []))
    if both:
        p.append(f"{AGENT_EVENT_REASONS_KEY} ids {sorted(both)} are also operator reasons or checker events: an agent "
                 f"event reason is read by its own graded row alone")
    agent_rows = table[AGENT_EVENTS_KEY].get("ids") if isinstance(table[AGENT_EVENTS_KEY], dict) else None
    for rid in sub["ids"]:
        readers = [r for r in table["rows"] if isinstance(r, dict) and any(
            isinstance(c, dict) and c.get("op") == "has" and c.get("value") == rid
            for g in ("all_of", "any_of", "none_of") for c in r.get(g, []))]
        good = (len(readers) == 1 and readers[0].get("route") == labels4.GRADED
                and readers[0].get("when") == labels4.AFTER_FIRST_TURN
                and readers[0].get("any_of") == [{"path": HAS_PATH, "op": "has", "value": rid}]
                and not readers[0].get("all_of") and not readers[0].get("none_of")
                and isinstance(agent_rows, list) and readers[0].get("id") in agent_rows)
        if not good:
            p.append(f"{AGENT_EVENT_REASONS_KEY} id {rid!r} must be read by exactly one row, a graded after-first-turn "
                     f"agent event row whose any_of is that has alone (got {[r.get('id') for r in readers]})")
    return p


def reason_route(table: dict, rid: str) -> str:
    """THE CLASS TABLE: the route a clean after-first-turn take (last turn end_turn) carrying the checker reason `rid`
    alone gets, read from the rows: REACH_REFUSED for a reason only before the first turn, else the highest-precedence
    route among the after-first-turn rows whose any_of reads it (has, or in_operator_reasons) and whose none_of does
    not, and graded (the end-turn row) when none does."""
    if rid in table["reasons_only_before_first_turn"]["ids"]:
        return REACH_REFUSED
    level = {r: i for i, lvl in enumerate(table["precedence"]) for r in lvl}

    def reads(c):
        return isinstance(c, dict) and c.get("path") == HAS_PATH and (
            (c.get("op") == "has" and c.get("value") == rid)
            or (c.get("op") == "in_operator_reasons" and rid in table["operator_reasons"]))
    routes = [r["route"] for r in table["rows"] if r.get("when") in (labels4.AFTER_FIRST_TURN, labels4.ANY_TIME)
              and not r.get("all_of") and any(reads(c) for c in r.get("any_of", []))
              and not any(reads(c) for c in r.get("none_of", []))]
    return min(routes, key=lambda x: level[x]) if routes else labels4.GRADED


def reach_required(table: dict) -> dict:
    """THE CLASS TABLE's keys ("<kind>:<id>") and the route each must state."""
    out = {f"row:{r['id']}": r["route"] for r in table["rows"]
           if r.get("when") in (labels4.AFTER_FIRST_TURN, labels4.ANY_TIME) and r.get("route") != labels4.GRADED}
    for rule in ("pin_refusal", "spend_cap_refusal"):
        out[f"rule:{table[rule]['id']}"] = REACH_REFUSED
    for rid in list(table["operator_reasons"]) + list(agent_event_reasons(table)):
        out[f"reason:{rid}"] = reason_route(table, rid)
    return out


def reach_problems(table: dict) -> list[str]:
    """THE CLASS TABLE against the table it sits in (load_table and --check run it after check_table). Kept out of
    check_table so a synthetic table built in memory from the live one (tests/test_walk_cover_strict.py's derivation
    cases) is checked for its routing alone; the table that routes takes is always read through load_table."""
    if AGENT_REACH_KEY not in table:
        return [f"missing {AGENT_REACH_KEY}"]
    sub = table[AGENT_REACH_KEY]
    if not isinstance(sub, dict) or set(sub) != {"source", "entries"} or not (_is_str(sub["source"]) and sub["source"]) \
            or not isinstance(sub["entries"], dict):
        return [f"{AGENT_REACH_KEY} must give its source and its entries"]
    want, got = reach_required(table), sub["entries"]
    p = [f"{AGENT_REACH_KEY}: no entry for {k}" for k in sorted(set(want) - set(got))]
    p += [f"{AGENT_REACH_KEY}: {k} is no row, rule or reason this table must answer" for k in sorted(set(got) - set(want))]
    for k in sorted(set(want) & set(got)):
        e = got[k]
        if not isinstance(e, dict) or set(e) != set(REACH_ENTRY_KEYS):
            p.append(f"{AGENT_REACH_KEY} {k} must hold exactly {list(REACH_ENTRY_KEYS)}")
            continue
        if not _is_bool(e["reachable"]) or not (_is_str(e["how"]) and e["how"].strip()):
            p.append(f"{AGENT_REACH_KEY} {k}: reachable is a bool and how says how, from code")
        if e["route"] != want[k]:
            p.append(f"{AGENT_REACH_KEY} {k} states route {e['route']!r}; the table gives {want[k]!r}")
        if e["call"] is not None and not (_is_str(e["call"]) and e["call"].strip()):
            p.append(f"{AGENT_REACH_KEY} {k}: call is None or a stated call")
        if e["reachable"] is True and want[k] not in REACH_FINAL and e["call"] is None:
            p.append(f"{AGENT_REACH_KEY} {k}: the agent can reach it and it routes {want[k]!r} (re-run or refused): "
                     f"a named exception or a ruling owed must be stated in call")
    return p


def agent_event_rows(table: dict) -> tuple:
    """MAJOR 5: the ids of the graded after-first-turn rows whose records the agent itself can produce, in table
    order (routing.json's agent_event_rows)."""
    return tuple(table[AGENT_EVENTS_KEY]["ids"])


def _agent_event_problems(table: dict) -> list[str]:
    """MAJOR 5: agent_event_rows names, once each and with its source, rows of this table that are after-first-turn
    and graded; a harness-error row named there would publish a harness fault as the agent's."""
    sub = table[AGENT_EVENTS_KEY]
    if (not isinstance(sub, dict) or set(sub) != {"ids", "source"} or not isinstance(sub["ids"], list) or not sub["ids"]
            or not all(_is_str(i) and i for i in sub["ids"]) or not (_is_str(sub["source"]) and sub["source"])):
        return [f"{AGENT_EVENTS_KEY} must give a non-empty list of row ids and its source"]
    if len(set(sub["ids"])) != len(sub["ids"]):
        return [f"{AGENT_EVENTS_KEY} repeats an id"]
    if list(sub["ids"]) != list(AGENT_EVENT_IDS):
        return [f"{AGENT_EVENTS_KEY} must be exactly {list(AGENT_EVENT_IDS)} (the agent's own exit and its process "
                f"alive at the quiescence cap), got {sub['ids']}"]
    rows = {r.get("id"): r for r in table["rows"] if isinstance(r, dict)}
    p = []
    for rid in sub["ids"]:
        row = rows.get(rid)
        if row is None:
            p.append(f"{AGENT_EVENTS_KEY} names {rid!r}, which is no row of the table")
        elif row.get("route") != labels4.GRADED or row.get("when") != labels4.AFTER_FIRST_TURN:
            p.append(f"{AGENT_EVENTS_KEY} names {rid!r}, which routes {row.get('route')!r} in phase {row.get('when')!r}: "
                     f"an agent event row is graded, after the first turn")
    return p


def _no_match_default_problems(table: dict) -> list[str]:
    """m17: the shape of the pre-registered ruling defaults (whether they cover the no-match classes is
    no_match_problems', which --check runs: it enumerates)."""
    sub = table[NO_MATCH_KEY]
    if (not isinstance(sub, dict) or set(sub) != {"source", "entries"} or not (_is_str(sub["source"]) and sub["source"])
            or not isinstance(sub["entries"], list) or not sub["entries"]):
        return [f"{NO_MATCH_KEY} must give its source and a non-empty list of entries"]
    p, keys = [], set()
    for i, e in enumerate(sub["entries"]):
        where = f"{NO_MATCH_KEY} entry {i}"
        if not isinstance(e, dict) or set(e) - {NO_MATCH_UNREADABLE_KEY} != set(NO_MATCH_ENTRY_KEYS):
            p.append(f"{where} must hold exactly {list(NO_MATCH_ENTRY_KEYS)}, and may hold {NO_MATCH_UNREADABLE_KEY!r}")
            continue
        if NO_MATCH_UNREADABLE_KEY in e:
            p += _no_match_unreadable_problems(e, where)
        if e["when"] not in (labels4.BEFORE_FIRST_TURN, labels4.AFTER_FIRST_TURN):
            p.append(f"{where}: phase {e['when']!r} is not before-first-turn or after-first-turn")
        if e["end"] is not None and e["end"] not in labels4.TURN_ENDS:
            p.append(f"{where}: end {e['end']!r} is not None or a labels4 turn end")
        if e["ruling"] != labels4.RULE_ROUTE or e["route"] not in labels4.ROUTES:
            p.append(f"{where}: a default is a {labels4.RULE_ROUTE} ruling to a labels4 route, got {e['ruling']!r} "
                     f"{e['route']!r}")
        elif e["when"] == labels4.AFTER_FIRST_TURN and e["route"] not in (labels4.GRADED, labels4.ABORTED):
            p.append(f"{where}: after the first turn a default is final (graded or aborted), never {e['route']!r}")
        if not (_is_str(e["why"]) and e["why"].strip()):
            p.append(f"{where}: no why")
        if (e.get("when"), e.get("end")) in keys:
            p.append(f"{where}: a second default for {e.get('when')} {e.get('end')}")
        keys.add((e.get("when"), e.get("end")))
    return p


def _no_match_unreadable_problems(e: dict, where: str) -> list[str]:
    """Lane fold2/merge: the `unreadable` alternative of a no-match entry, allowed after the first turn only, beside a
    graded default, as a route ruling to aborted cited END_STATE_UNREAD_CITE with its why."""
    alt, where = e[NO_MATCH_UNREADABLE_KEY], f"{where} {NO_MATCH_UNREADABLE_KEY}"
    p = []
    if e["when"] != labels4.AFTER_FIRST_TURN or e["route"] != labels4.GRADED:
        p.append(f"{where}: an unreadable alternative stands only after the first turn beside a graded default (an "
                 f"end state is read only then), not {e['when']!r} beside {e['route']!r}")
    if not isinstance(alt, dict) or set(alt) != set(NO_MATCH_UNREADABLE_KEYS):
        return p + [f"{where} must hold exactly {list(NO_MATCH_UNREADABLE_KEYS)}"]
    if (alt["ruling"], alt["route"], alt["cite"]) != (labels4.RULE_ROUTE, labels4.ABORTED, END_STATE_UNREAD_CITE):
        p.append(f"{where}: the alternative is a {labels4.RULE_ROUTE} ruling to {labels4.ABORTED} cited "
                 f"{END_STATE_UNREAD_CITE!r}, got {alt['ruling']!r} {alt['route']!r} {alt['cite']!r}")
    if not (_is_str(alt["why"]) and alt["why"].strip()):
        p.append(f"{where}: no why")
    return p


def load_table(path: str | None = None) -> dict:
    with open(path or TABLE_PATH, encoding="utf-8") as fh:   # W7C: TABLE_PATH read at call time
        table = json.load(fh)
    problems = check_table(table)
    problems = problems or reach_problems(table)        # THE CLASS TABLE, on the table as it stands
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
    accepted = ACCEPTED_IDENTITY_SOURCES.get(pin.get("harness"))
    if accepted is None:                       # never routed: shape_problems refuses it first
        raise RoutingRefused(f"identity on a {pin.get('harness')!r} record")
    for f in fields:
        e = entry[f]
        if present_only:
            if e["source"] in OBSERVED_IDENTITY_SOURCES and e["value"] != pin[f]:
                return True
        elif e["source"] == "unobserved" and f in UNOBSERVED_ACCEPTED.get(pin.get("harness"), ()):
            continue                           # D-INT-2: arm O's served model, unobserved without a reroute
        elif e["source"] not in accepted.get(f, ()) or e["value"] != pin[f]:
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
        harness = records["pin"].get("harness") if isinstance(records["pin"], dict) else None
        if harness not in ACCEPTED_IDENTITY_SOURCES:
            p.append(f"identity is accepted only for harnesses with a registered source table, not {harness!r}")
        elif not isinstance(ids, list) or not isinstance(records["init"], list) or len(ids) != len(records["init"]):
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
    events = agent_event_reasons(table)
    unknown = [r for r in records["checker_reasons"] if r not in table["operator_reasons"] and r not in events]
    if unknown:
        p.append(f"checker reason ids not in routing.json: {unknown}")
    early_events = [r for r in records["checker_reasons"] if r in events]
    if early_events and phase_of(records) == labels4.BEFORE_FIRST_TURN:
        # MAJOR 1 of pre-freeze review 2: an agent event reason reads a Bash command, which is completed agent output
        p.append(f"agent event reason(s) {early_events} before the agent's first turn: a Bash command is completed "
                 f"agent output, so the checker and the records disagree and a human must look")
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
    if op == "has":
        return cond["value"] in v
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


# ------------------------------------------------------------------------------- THE NO-MATCH PROOF (m17)
# Every condition the table may hold, by (path, op), and the input variables its truth reads. A condition outside this
# closed vocabulary refuses the proof: a new kind of condition needs its class here before --check can pass.
PROOF_CONDITIONS = {
    ("preflight.ok", "falsy"): ("preflight",),
    ("exit.container_started", "falsy"): ("started",),
    ("exit.container_exited", "truthy"): ("exited",),
    ("exit.exec_codes", "nonzero_outside_timeout"): ("exec", "end"),
    ("api_errors", "nonempty"): ("api",),
    **{(f"api_errors.{k}", op): ("api",) for k in API_ERROR_KEYS for op in ("in_rate_limit_markers", SPEND_OP)},
    ("sidecar.start_record", "falsy"): ("sidecar",),
    ("sidecar.stop_record", "falsy"): ("sidecar",),
    ("sidecar.exit_code", "ne"): ("sidecar",),
    ("sidecar.queue_overflow", "truthy"): ("sidecar",),
    ("checker_reasons", "in_operator_reasons"): ("checker",),
    ("checker_reasons", "has"): ("checker",),
    ("operator.unexplained_diffs", "gt"): ("opdiff",),
    ("ledger.finalize_abort", "truthy"): ("finalize",),
    ("ledger.end", "eq"): ("end",),
    ("cgroup.oom_kill_delta", "gt"): ("oom",),
    ("cgroup.pids_max_delta", "gt"): ("pids",),
    ("init", "differs_from_pin"): ("init",),
    ("init", "present_differs_from_pin"): ("init",),
    ("unreadable_consequential", "nonempty"): ("unreadable",),
    ("quiescence_cap_survivors", "gt"): ("survivors",),
}
# Each variable's classes. Every class is one value of the record field (or fields) it names, and the classes of a
# variable reach every combination of truth values its conditions can take: the sidecar's four fields as all sixteen
# combinations; API errors as none, an error with no marker, a rate limit, a spend cap and both (a condition reads any
# error of the list); the checker reasons as none, an operator reason, harness-condition-violated (an operator reason
# that cgroup-kill's none_of names), round 3's before-first-turn reason, an event id, an unlisted id and an agent event
# reason (pre-freeze review 2, MAJOR 1); init as the
# pin, a differing event and none. Counts are 0 or 1 because every condition on them is "gt 0". The end and phase are
# assigned first, so every class carries both.
PROOF_ORDER = ("survivors", "api", "oom", "pids", "checker", "unreadable", "init", "exec", "sidecar", "opdiff",
               "finalize", "started", "exited", "preflight")
_SIDECAR = tuple((s, t, x, q) for s in (True, False) for t in (True, False) for x in (0, 1) for q in (False, True))
PROOF_DOMAINS = {
    "survivors": (0, 1), "api": ("none", "error", "rate", "spend", "rate+spend"), "oom": (0, 1), "pids": (0, 1),
    "checker": ("none", "operator", "harness-condition-violated", "before-only", "event", "unlisted", "agent-event"),
    "unreadable": (False, True), "init": ("pin", "differs", "missing"), "exec": (0, 1), "sidecar": _SIDECAR,
    "opdiff": (0, 1), "finalize": (False, True), "started": (True, False), "exited": (False, True),
    "preflight": (True, False),
}
PROOF_ENDS = {labels4.BEFORE_FIRST_TURN: (None, labels4.END_TURN, labels4.TIMED_OUT, labels4.END_ERROR),
              labels4.AFTER_FIRST_TURN: (labels4.END_TURN, labels4.TIMED_OUT, labels4.END_ERROR)}


def _proof_api(table: dict, harness: str, cls: str) -> list:
    rate, spend = table["rate_limit_markers"][harness], table["spend_cap_markers"][harness]

    def marked(entry):
        for k in API_ERROR_KEYS:
            if entry[k]:
                return {"status": None, "type": None, "text": None, k: entry[k][0]}
        return None
    plain = {"status": 500, "type": "pf1-proof-unmarked", "text": None}
    out = {"none": [], "error": [plain], "rate": [marked(rate)], "spend": [marked(spend)],
           "rate+spend": [marked(rate), marked(spend)]}[cls]
    return None if None in out else out


def _proof_records(table: dict, harness: str, profile: dict, a: dict) -> dict | None:
    """The concrete records of one assignment; unassigned variables take the clean class (their first)."""
    v = {k: a.get(k, PROOF_DOMAINS[k][0]) for k in PROOF_DOMAINS}
    after = a["phase"] == labels4.AFTER_FIRST_TURN
    n = 0 if a["end"] is None else 1
    pin = dict(profile, harness=harness)
    init = {"pin": {f: pin[f] for f in PLAN_PIN_FIELDS}, "differs": dict({f: pin[f] for f in PLAN_PIN_FIELDS},
                                                                        version="pf1-proof-other"), "missing": None}
    api = _proof_api(table, harness, v["api"])
    if api is None:
        return None                       # this harness has no marker of that kind: the class does not exist for it
    ops = [r for r in table["operator_reasons"] if r != "harness-condition-violated"
           and r not in table["reasons_only_before_first_turn"]["ids"]]
    checker = {"none": [], "operator": ops[:1], "harness-condition-violated": ["harness-condition-violated"],
               "before-only": list(table["reasons_only_before_first_turn"]["ids"][:1]),
               "event": list(table["checker_reasons_become_events"]["ids"][:1]), "unlisted": ["pf1-proof-unlisted"],
               "agent-event": list(agent_event_reasons(table)[:1])}
    s, t, x, q = v["sidecar"]
    return {
        "ledger": {"first_turn_started": after, "turns": n, "end": a["end"], "turn_ends": [a["end"]] * n,
                   "turn_outputs": [after] * n, "committed": False, "finalize_abort": v["finalize"]},
        "exit": {"container_started": v["started"], "container_exited": v["exited"], "exec_codes": [v["exec"]] * n},
        "cgroup": {"oom_kill_delta": v["oom"], "pids_max_delta": v["pids"]},
        "init": [copy.deepcopy(init[v["init"]]) for _ in range(n)],
        "pin": pin,
        "api_errors": copy.deepcopy(api),
        "sidecar": {"start_record": s, "stop_record": t, "exit_code": x, "queue_overflow": q},
        "preflight": {"ok": v["preflight"]},
        "operator": {"unexplained_diffs": v["opdiff"]},
        "checker_reasons": list(checker[v["checker"]]),
        "quiescence_kill": bool(v["survivors"]),
        "events": {"outside_reach": 0},
        "unreadable_consequential": ["pf1-proof/path"] if v["unreadable"] else [],
        "quiescence_cap_survivors": v["survivors"],
    }


def _proof_vocabulary_problems(table: dict) -> list[str]:
    p = []
    groups = [(row.get("id"), row.get(g, [])) for row in table["rows"] for g in ("all_of", "any_of", "none_of")]
    groups += [("pin_refusal", table["pin_refusal"]["all_of"]), ("spend_cap_refusal", table["spend_cap_refusal"]["any_of"])]
    for owner, conds in groups:
        for c in conds:
            path, op = c.get("path"), c.get("op")
            if (path, op) not in PROOF_CONDITIONS:
                p.append(f"{owner}: condition {(path, op)} is outside the no-match proof's closed "
                         f"vocabulary (routing.PROOF_CONDITIONS): its class must be added before --check can prove "
                         f"the table exhaustive")
            elif op in ("gt", "ne") and c.get("value") != 0:
                p.append(f"{owner}: condition {(path, op, c.get('value'))} compares with {c.get('value')!r}; the "
                         f"no-match proof's classes are built for 0")
    return p


def _row_state(row: dict, a: dict, rec: dict, table: dict) -> str:
    """'match', 'nomatch' or 'open' for a row under a partial assignment (a condition is read once its variables are
    all assigned)."""
    if row["when"] not in (labels4.ANY_TIME, a["phase"]):
        return "nomatch"

    def val(c):
        return holds(c, rec, table) if all(x in a for x in PROOF_CONDITIONS[(c["path"], c["op"])]) else None
    alls = [val(c) for c in row.get("all_of", [])]
    anys = [val(c) for c in row["any_of"]]
    nones = [val(c) for c in row.get("none_of", [])]
    if False in alls or (anys and all(x is False for x in anys)) or True in nones:
        return "nomatch"
    if all(x is True for x in alls) and True in anys and all(x is False for x in nones):
        return "match"
    return "open"


def no_match_classes(table: dict) -> list[dict]:
    """m17: every input class no row matches, for every pin harness (its first registered model's profile), found by
    assigning the closed variables one by one and stopping a branch as soon as a row surely matches. Each class is
    {harness, when, end, assigned (the variables the class fixes), witness (its records, the rest clean)}; a class
    whose witness check_records refuses (a malformed or contradictory record) or a refusal rule holds on is not a
    no-match input and is left out."""
    if _proof_vocabulary_problems(table):
        raise TableError("; ".join(_proof_vocabulary_problems(table)))
    out = []
    for harness, models in sorted(table["pin_profiles"].items()):
        model, prof = sorted(models.items())[0]
        profile = dict(prof, model=model)
        for phase, ends in PROOF_ENDS.items():
            for end in ends:
                _proof_walk(table, harness, profile, {"phase": phase, "end": end}, 0, out)
    return out


def _proof_walk(table, harness, profile, a, i, out) -> None:
    rec = _proof_records(table, harness, profile, a)
    if rec is None:
        return
    states = [_row_state(row, a, rec, table) for row in table["rows"]]
    if "match" in states:
        return
    if all(s == "nomatch" for s in states) or i == len(PROOF_ORDER):
        if check_records(rec, table) or spend_cap_holds(rec, table) or pin_refusal_holds(rec, table):
            return
        if "open" in states:
            raise TableError(f"the no-match proof left rows open on a full assignment: {a}")
        out.append({"harness": harness, "when": a["phase"], "end": a["end"],
                    "assigned": {k: v for k, v in a.items() if k not in ("phase", "end")}, "witness": rec})
        return
    var = PROOF_ORDER[i]
    open_rows = [row for row, s in zip(table["rows"], states) if s == "open"]
    read = any(var in PROOF_CONDITIONS[(c["path"], c["op"])] for row in open_rows
               for g in ("all_of", "any_of", "none_of") for c in row.get(g, []))
    # A variable no open row reads cannot change whether a row matches: it takes its clean class, the one whose
    # records are soundest, so the class's witness is refused only when every completion of it would be.
    for value in PROOF_DOMAINS[var] if read else PROOF_DOMAINS[var][:1]:
        _proof_walk(table, harness, profile, dict(a, **{var: value}), i + 1, out)


def no_match_problems(table: dict) -> list[str]:
    """m17: the table is exhaustive up to its pre-registered defaults: every no-match class (phase, last turn's end)
    has exactly one entry in no_match_defaults, and every entry is reached by a class."""
    p = _no_match_default_problems(table) + _proof_vocabulary_problems(table)
    if p:
        return p
    reached = {(c["when"], c["end"]): c for c in no_match_classes(table)}
    entries = {(e["when"], e["end"]) for e in table[NO_MATCH_KEY]["entries"]}
    p += [f"no-match class {k[0]}, last turn {k[1]}: no pre-registered ruling default "
          f"(e.g. harness {reached[k]['harness']}, {reached[k]['assigned']}): add a row, or an entry to "
          f"{NO_MATCH_KEY}" for k in sorted(set(reached) - entries, key=str)]
    p += [f"{NO_MATCH_KEY} entry {k[0]}, last turn {k[1]}: no no-match class reaches it (a row matches every such "
          f"input): a stale default" for k in sorted(entries - set(reached), key=str)]
    return p


def _no_match_entry(records: dict, table: dict) -> dict | None:
    """m17: the no_match_defaults entry for records no row matches (sound records, no refusal rule holding, no row
    matching), else None. A no-match class with no entry raises TableError (--check refuses that table)."""
    if check_records(records, table) or spend_cap_holds(records, table) or pin_refusal_holds(records, table):
        return None
    if any(matches(row, records, table) for row in table["rows"]):
        return None
    key = (phase_of(records), records["ledger"]["end"])
    for e in table[NO_MATCH_KEY]["entries"]:
        if (e["when"], e["end"]) == key:
            return e
    raise TableError(f"records no row matches ({key[0]}, last turn {key[1]}) have no pre-registered ruling default")


def no_match_default(records: dict, table: dict) -> tuple | None:
    """m17: the pre-registered (ruling, route) for records no row matches, else None (`_no_match_entry`)."""
    e = _no_match_entry(records, table)
    return None if e is None else (e["ruling"], e["route"])


def no_match_unreadable(records: dict, table: dict) -> tuple | None:
    """Lane fold2/merge: the (ruling, route) of the no-match entry's `unreadable` alternative for these records, else
    None (no-match records whose entry carries none, or records some row matches). batch.py accepts it in place of the
    default only with a cite opening END_STATE_UNREAD_CITE and the reading's exception type; the door and the
    publication (check_results.ruled_route_problems) hold it to the reading the grader actually failed with."""
    e = _no_match_entry(records, table)
    alt = None if e is None else e.get(NO_MATCH_UNREADABLE_KEY)
    return None if alt is None else (alt["ruling"], alt["route"])


def main(argv: list[str]) -> int:
    """`routing.py --check` validates routing.json and runs the no-match proof; `routing.py <records.json>` routes one
    take."""
    if argv[:1] == ["--check"]:
        table = load_table()
        bad = no_match_problems(table)
        for b in bad:
            print(f"routing: FAIL {b}")
        if bad:
            return 1
        classes = no_match_classes(table)
        keys = sorted({(c["when"], c["end"]) for c in classes}, key=str)
        defaults = {(e["when"], e["end"]): e for e in table[NO_MATCH_KEY]["entries"]}
        print(f"routing.json: {len(table['rows'])} rows, {len(table['annotations'])} annotations, sound")
        print(f"routing.json: no-match proof over {len(table['pin_profiles'])} pin harness(es): {len(classes)} input "
              f"class(es) no row matches, in {len(keys)} phase and end pair(s), each with its pre-registered ruling "
              f"default:")
        for k in keys:
            e = defaults[k]
            alt = e.get(NO_MATCH_UNREADABLE_KEY)
            print(f"  {k[0]}, last turn {k[1] if k[1] is not None else 'none (no turn ran)'} -> {e['ruling']} "
                  f"{e['route']}" + (f" (end state unreadable: {alt['ruling']} {alt['route']}, cited)" if alt else ""))
        return 0
    if len(argv) == 1:
        with open(argv[0], encoding="utf-8") as fh:
            print(json.dumps(route(json.load(fh)), indent=1))
        return 0
    print("usage: routing.py --check | routing.py <records.json>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
