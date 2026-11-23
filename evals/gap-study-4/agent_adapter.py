#!/usr/bin/env python3
"""The only interface between round 4's runner and any agent (lane lead's interface 5).

The runner never talks to Claude Code, a container runtime or a model directly. It holds an
`AgentAdapter` and asks it, one take at a time, to start, to run turns, and to end. Every adapter
returns the same `TurnResult` record per turn, so the routing table (`routing.py`) and the take
loop (`batch.py`) never need to know which agent ran. The Claude Code adapter is built later, with
the sealed box (CP2); this module holds the base class, the record, the no-model `ScriptedAdapter`
used by tests and stub agents, and `harness_records`, which folds a take's turn results and the
box's own records into the record shape `routing.py` reads.

IMPLEMENTING ANOTHER HARNESS. Subclass `AgentAdapter` and provide:

    name                      class attribute: a short stable name ("claude-code", "stub", ...)
    version() -> str          the harness's own version string, recorded beside every take
    start_take(take) -> dict  prepare one take. `take` is the registered row (a dict: at least
                              `row_id`, `slot`, `half_cell`). Return a dict with at least
                              `container_id` (str, or None when the harness runs no container):
                              the runner records it at launch and removes the container by that
                              id only, never by a name pattern.
    turn(line, *, first, budget_s) -> TurnResult
                              send one operator line to the agent and wait for the turn to end,
                              at most `budget_s` seconds. `first` is True for the take's opening
                              request. Never raise for something the agent did: a timeout is
                              `end_reason="timed-out"`, an API error is an `api_errors` entry.
                              Raise only when the harness itself cannot go on.
    end_take() -> None        tear down what start_take made (the runner still removes the
                              recorded container itself).

Calls come in this order only: start_take, then one or more turn (the first with first=True),
then end_take. A turn outside a started take, a second start, or a second end is a harness error,
and the base class's `_enter`/`_check_turn`/`_leave` helpers raise `AdapterStateError` for it.

THE RECORD. `TurnResult` carries, for one turn:

    exit_code       the exec's exit code as the host saw it (None if it never returned one)
    text            the agent's text for the turn. Graders read it; routing NEVER does, and
                    `harness_record()` leaves it out. It is never copied into an API error's text.
    stream_path     path of the host-captured output stream for the turn (None if none)
    end_reason      how the host saw the turn end: one of `labels4.TURN_ENDS` ("end_turn",
                    "timed-out", "error"), never retyped here
    init            REQUIRED keyword: the turn's init event fields (model, permission_mode,
                    version), or an explicit None when the turn had no init event
    api_errors      REQUIRED keyword: a list of every API-error record the turn met, in the order
                    met ([] when none; review round 2, W1B2-7: one turn can meet a 529 and then a
                    429). Each is {"status": int or None, "type": str or None, "text": str or
                    None} (all three keys required; other keys are not carried to routing).
                    `text` is the harness-side error text: what Claude Code or the API reported as
                    the error, never the agent's reply (glitch-f3's ruling, 6 Oct 2026: routing
                    matches round 3's rate-limit text markers on it)
    counters        REQUIRED keyword: the turn's cgroup counter rises, read host-side:
                    {"oom_kill_delta": int, "pids_max_delta": int}, non-negative. Never defaulted:
                    an adapter that forgot them would turn an out-of-memory kill (aborted, never
                    re-run) into a harness-error re-run (review round 2, W1B2-4)
    started_at, ended_at   REQUIRED keywords: the host clock (seconds since the epoch, an int or a float) at the
                    turn's start and end; never defaulted (review round 3, W1B3-6: they defaulted to 0.0), and
                    finite (W1B4-4: NaN and the infinities are refused)
    agent_output    REQUIRED bool: True when the host-captured stream holds at least one completed
                    agent message (text or tool call) for this turn, or, for codex, a started tool
                    item (the call issued; pre-freeze review 2, m7). It is read from the stream's
                    event types, never from their content. A turn that produced no completed agent
                    output (an API error on the first call, a container that died first, a turn
                    that timed out silently) has not started the agent's first turn.

A required keyword left out raises TypeError naming it; None is never assumed for it.

Everything except `text` is a harness-side record: it comes from the host, the runtime or the API,
never from what the agent said or did.

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, asdict

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from graders import labels4  # noqa: E402

# The turn ends are labels4's (interface 4): imported, never retyped.
END_TURN = labels4.END_TURN
END_TIMED_OUT = labels4.TIMED_OUT
END_ERROR = labels4.END_ERROR
END_REASONS = labels4.TURN_ENDS

INIT_FIELDS = ("model", "permission_mode", "version")
# Live harness 3b (14 Oct 2026): typed identity evidence, for a harness whose stream has no init event carrying all
# three pin fields (Gemini: init names a model and a session id only, D8). Per INIT_FIELDS field: {"value", "source"},
# the source one of IDENTITY_SOURCES; "unobserved" carries value None, every other source a nonempty string. Routing
# decides which source it accepts for which field (routing.ACCEPTED_IDENTITY_SOURCES); nothing here enters `init`.
IDENTITY_SOURCES = ("stream-init", "stream-stats", "version-exec", "submitted-argv", "stream-reroute", "unobserved")
UNOBSERVED = "unobserved"


def identity_problems(identity) -> list:
    """Why a turn's typed identity evidence is malformed ([] when sound; None is no evidence and is sound)."""
    if identity is None:
        return []
    if not isinstance(identity, dict) or set(identity) != set(INIT_FIELDS):
        return [f"identity must be None or a dict of exactly {INIT_FIELDS}"]
    out = []
    for f in INIT_FIELDS:
        e = identity[f]
        if not isinstance(e, dict) or set(e) != {"value", "source"} or e["source"] not in IDENTITY_SOURCES:
            out.append(f"identity.{f} must be {{value, source}} with a source in {IDENTITY_SOURCES}")
        elif e["source"] == UNOBSERVED and e["value"] is not None:
            out.append(f"identity.{f} is unobserved and must carry no value")
        elif e["source"] != UNOBSERVED and not (isinstance(e["value"], str) and e["value"]):
            out.append(f"identity.{f} from {e['source']} must carry a nonempty string")
    return out
COUNTER_FIELDS = ("oom_kill_delta", "pids_max_delta")
API_ERROR_FIELDS = ("status", "type", "text")

# The box's own records, every one REQUIRED by `harness_records` (a missing one is never read as
# "nothing happened"): what no adapter produces. `outside_reach_events` is the drive step's count of
# outside-reach events (routing.py's docstring says exactly what it counts).
# CP2 ruling C3 (glitch-f3, 17:35; names fixed at 17:42) adds the last two: `unreadable_consequential`, the run-tree
# paths among the task's consequential ones that the sidecar could not read (a list of strings, from the sidecar
# reply's field of that name), and `quiescence_cap_survivors`, the processes still alive at the quiescence cap (an
# int >= 0, W2A2-6).
BOX_KEYS = ("preflight_ok", "container_started", "container_exited", "sidecar",
            "unexplained_operator_diffs", "checker_reasons", "quiescence_kill",
            "outside_reach_events", "finalize_abort", "committed",
            "unreadable_consequential", "quiescence_cap_survivors")


class AdapterStateError(RuntimeError):
    """A call out of the start_take / turn / end_take order."""


class BoxRecordError(ValueError):
    """The box's records given to `harness_records` miss a required key or carry an unknown one."""


# Live harness step 3a (14 Oct 2026): what an adapter kept of a turn's exec before it read anything of the turn.
EXECUTED_FIELDS = ("n", "exit_code", "timed_out", "started_at", "ended_at", "stream_path", "counters", "refused")


class ExecutedTurnRefused(Exception):
    """The turn's exec ran (the runtime returned or timed out), and then the harness refused its own record of it (an
    unreadable stream, an exit code off the table, a resumed session that is not the take's). Raised only after the
    exec, carrying `executed`: exactly EXECUTED_FIELDS, as kept before the read (refused: why). The driver accounts
    for the turn as launched and refuses the take for a human; it is never a pre-turn refusal, a rehearsal or a
    re-run. A harness adapter may mix this into its own error type so its existing callers still catch that."""

    def __init__(self, message, *, executed):
        if not isinstance(executed, dict) or set(executed) != set(EXECUTED_FIELDS):
            raise TypeError(f"executed must carry exactly {EXECUTED_FIELDS}")
        super().__init__(message)
        self.executed = dict(executed)


def _count(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


class _Required:
    """The default of a keyword TurnResult requires: never a value, only "left out"."""

    def __repr__(self):
        return "<required>"


REQUIRED = _Required()
# W1B2-4: the harness-side records an adapter must state on every turn (None is a legal explicit init); W1B3-6: the
# turn's host clock too.
REQUIRED_KEYWORDS = ("init", "api_errors", "counters", "started_at", "ended_at")


def _clock(v) -> bool:
    # W1B4-4 (w1b's next touch, item 2): finite too. A NaN compares False with every number, so a NaN start used to
    # pass the start-before-end check; an infinity is no host clock either.
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


@dataclass(frozen=True)
class TurnResult:
    exit_code: int | None
    text: str
    stream_path: str | None
    end_reason: str
    init: dict | None = REQUIRED          # required keyword; an explicit None is legal
    api_errors: list = REQUIRED           # required keyword; [] when the turn met none
    counters: dict = REQUIRED             # required keyword
    started_at: float = REQUIRED          # required keyword (W1B3-6)
    ended_at: float = REQUIRED            # required keyword (W1B3-6)
    agent_output: bool | None = None   # required: see THE RECORD; None is refused
    identity: dict | None = None       # live harness 3b: typed identity evidence beside init (None: none stated)

    def __post_init__(self):
        for name in REQUIRED_KEYWORDS:
            if getattr(self, name) is REQUIRED:
                raise TypeError(f"TurnResult: `{name}` is a required keyword (state it, never leave it out)")
        if self.end_reason not in END_REASONS:
            raise ValueError(f"end_reason {self.end_reason!r} is not one of {END_REASONS}")
        if not isinstance(self.counters, dict) or set(self.counters) != set(COUNTER_FIELDS):
            raise ValueError(f"counters must name exactly {COUNTER_FIELDS}")
        if not all(_count(v) for v in self.counters.values()):
            raise ValueError("counter rises must be non-negative ints")
        if self.init is not None and (not isinstance(self.init, dict) or not set(INIT_FIELDS) <= set(self.init)):
            raise ValueError(f"init must be None or a dict carrying {INIT_FIELDS}")
        if not isinstance(self.api_errors, list) or not all(
                isinstance(e, dict) and set(API_ERROR_FIELDS) <= set(e) for e in self.api_errors):
            raise ValueError(f"api_errors must be a list ([] for none) of dicts carrying {API_ERROR_FIELDS}")
        if identity_problems(self.identity):
            raise ValueError("; ".join(identity_problems(self.identity)))
        if not isinstance(self.agent_output, bool):
            raise ValueError("agent_output must be a bool: did the turn's stream hold a completed agent message?")
        if not (_clock(self.started_at) and _clock(self.ended_at)):
            raise ValueError("started_at and ended_at must be the host clock in seconds (a finite int or float)")
        if self.ended_at < self.started_at:
            raise ValueError("a turn cannot end before it starts")

    def harness_record(self) -> dict:
        """Every field except the agent's text: what routing may read."""
        rec = asdict(self)
        del rec["text"]
        return rec


class AgentAdapter:
    """Base class. Subclasses implement `version`, `_start`, `_turn`, `_end` (or override the public
    methods and call the state helpers themselves)."""

    name = "abstract"

    def __init__(self):
        self._state = "idle"
        self._turns = 0

    # --- the interface -------------------------------------------------------------------------
    def version(self) -> str:
        raise NotImplementedError

    def start_take(self, take: dict) -> dict:
        self._enter()
        started = self._start(take)
        if not isinstance(started, dict) or "container_id" not in started:
            raise AdapterStateError("start_take must return a dict with container_id")
        return started

    def turn(self, line: str, *, first: bool, budget_s: float) -> TurnResult:
        self._check_turn(first)
        result = self._turn(line, first=first, budget_s=budget_s)
        if not isinstance(result, TurnResult):
            raise AdapterStateError("turn must return a TurnResult")
        self._turns += 1
        return result

    def end_take(self) -> None:
        self._leave()
        self._end()

    # --- for subclasses ------------------------------------------------------------------------
    def _start(self, take: dict) -> dict:
        raise NotImplementedError

    def _turn(self, line: str, *, first: bool, budget_s: float) -> TurnResult:
        raise NotImplementedError

    def _end(self) -> None:
        raise NotImplementedError

    # --- order checks --------------------------------------------------------------------------
    def _enter(self):
        if self._state != "idle":
            raise AdapterStateError(f"start_take while {self._state}")
        self._state, self._turns = "open", 0

    def _check_turn(self, first: bool):
        if self._state != "open":
            raise AdapterStateError(f"turn while {self._state}")
        if first != (self._turns == 0):
            raise AdapterStateError("first=True must be passed on, and only on, the take's first turn")

    def _leave(self):
        if self._state != "open":
            raise AdapterStateError(f"end_take while {self._state}")
        self._state = "idle"


class ScriptedAdapter(AgentAdapter):
    """No model: replays a fixed list of TurnResults, one per turn, and records the lines it got.

    Asking for more turns than were scripted raises AdapterStateError: a stub take that runs past
    its script is a broken test, never a silent empty turn.
    """

    name = "scripted"

    def __init__(self, turns: list[TurnResult], *, version: str = "scripted-1", container_id: str | None = None):
        super().__init__()
        self._script = list(turns)
        self._version = version
        self._container_id = container_id
        self.lines: list[str] = []
        self.takes: list[dict] = []
        self.ended = 0

    def version(self) -> str:
        return self._version

    def _start(self, take: dict) -> dict:
        self.takes.append(dict(take))
        return {"container_id": self._container_id}

    def _turn(self, line: str, *, first: bool, budget_s: float) -> TurnResult:
        if self._turns >= len(self._script):
            raise AdapterStateError(f"script has {len(self._script)} turns; turn {self._turns + 1} asked for")
        self.lines.append(line)
        return self._script[self._turns]

    def _end(self) -> None:
        self.ended += 1

    @property
    def remaining(self) -> int:
        return len(self._script) - self._turns


def harness_records(turns: list[TurnResult], *, pin: dict, box: dict) -> dict:
    """Fold one take's turn results and the box's own records into the shape `routing.py` reads.

    `box` must carry exactly `BOX_KEYS`: `preflight_ok`, `container_started`, `container_exited`
    (the runtime's exit record shows the container itself died), `sidecar` ({start_record,
    stop_record, exit_code, queue_overflow}), `unexplained_operator_diffs`, `checker_reasons`,
    `quiescence_kill`, `outside_reach_events`, `finalize_abort`, `committed`, and (CP2 ruling C3)
    `unreadable_consequential` and `quiescence_cap_survivors`. A missing key raises
    `BoxRecordError` (missing evidence is never read as "nothing happened"), and so does an unknown
    one. Values are copied as given, never coerced: `routing.check_records` type-checks them, so a
    None or a string counter is refused there instead of silently becoming 0 or True.

    The agent's first turn has started once a turn produced completed agent output
    (`agent_output`), and only then: a turn that produced none, such as one whose first API call
    failed or one that timed out silently, is still before it (gap4 lane lead's ruling on W1B-5;
    review round 2, W1B2-1, reverting 3fcab58d under glitch-f3's correction, 6 Oct 2026: a silent
    timeout cannot be told from a hung API, CLI or egress, so it is a rehearsal). Every API error
    of every turn is carried, flattened in turn order and, within a turn, in the order met (W1B-4,
    W1B2-7), so a rate limit after another error still reads as a rate limit; each is projected
    onto `API_ERROR_FIELDS`, its `text` the harness's own error text as the adapter recorded it.
    The agent's text is never copied in.
    """
    if not isinstance(box, dict):
        raise BoxRecordError("box must be a dict")
    missing = [k for k in BOX_KEYS if k not in box]
    unknown = sorted(set(box) - set(BOX_KEYS))
    if missing or unknown:
        raise BoxRecordError(f"box records missing {missing}, unknown {unknown}")
    outputs = [t.agent_output for t in turns]
    sidecar = box["sidecar"]
    reasons = box["checker_reasons"]
    unreadable = box["unreadable_consequential"]
    return {
        "ledger": {
            "first_turn_started": any(outputs),
            "turns": len(turns),
            "end": turns[-1].end_reason if turns else None,
            "turn_ends": [t.end_reason for t in turns],
            "turn_outputs": outputs,
            "committed": box["committed"],
            "finalize_abort": box["finalize_abort"],
        },
        "exit": {
            "container_started": box["container_started"],
            "container_exited": box["container_exited"],
            "exec_codes": [t.exit_code for t in turns],
        },
        "cgroup": {k: sum(t.counters[k] for t in turns) for k in COUNTER_FIELDS},
        "init": [None if t.init is None else {f: t.init[f] for f in INIT_FIELDS} for t in turns],
        # live harness 3b: only when some turn states typed identity evidence; otherwise the records are unchanged
        **({"identity": [None if t.identity is None else {f: dict(t.identity[f]) for f in INIT_FIELDS}
                         for t in turns]} if any(t.identity is not None for t in turns) else {}),
        "pin": dict(pin) if isinstance(pin, dict) else pin,
        "api_errors": [{f: e[f] for f in API_ERROR_FIELDS} for t in turns for e in t.api_errors],
        "sidecar": dict(sidecar) if isinstance(sidecar, dict) else sidecar,
        "preflight": {"ok": box["preflight_ok"]},
        "operator": {"unexplained_diffs": box["unexplained_operator_diffs"]},
        "checker_reasons": list(reasons) if isinstance(reasons, list) else reasons,
        "quiescence_kill": box["quiescence_kill"],
        "events": {"outside_reach": box["outside_reach_events"]},
        "unreadable_consequential": list(unreadable) if isinstance(unreadable, list) else unreadable,
        "quiescence_cap_survivors": box["quiescence_cap_survivors"],
    }
