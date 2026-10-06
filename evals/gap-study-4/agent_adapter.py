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
                              `end_reason="timed-out"`, an API error is an `api_error` record.
                              Raise only when the harness itself cannot go on.
    end_take() -> None        tear down what start_take made (the runner still removes the
                              recorded container itself).

Calls come in this order only: start_take, then one or more turn (the first with first=True),
then end_take. A turn outside a started take, a second start, or a second end is a harness error,
and the base class's `_enter`/`_check_turn`/`_leave` helpers raise `AdapterStateError` for it.

THE RECORD. `TurnResult` carries, for one turn:

    exit_code       the exec's exit code as the host saw it (None if it never returned one)
    text            the agent's text for the turn. Graders read it; routing NEVER does, and
                    `harness_record()` leaves it out.
    stream_path     path of the host-captured output stream for the turn (None if none)
    end_reason      "end_turn", "timed-out" or "error": how the host saw the turn end
    init            the turn's init event fields (model, permission_mode, version), or None
    api_error       the API-error record for the turn ({"status": int, "type": str, ...}), or None
    counters        the turn's cgroup counter rises, read host-side: {"oom_kill_delta": int,
                    "pids_max_delta": int}
    started_at, ended_at   host clock (seconds since the epoch) at the turn's start and end

Everything except `text` is a harness-side record: it comes from the host, the runtime or the API,
never from what the agent said or did.

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

END_TURN = "end_turn"
END_TIMED_OUT = "timed-out"
END_ERROR = "error"
END_REASONS = (END_TURN, END_TIMED_OUT, END_ERROR)

INIT_FIELDS = ("model", "permission_mode", "version")
COUNTER_FIELDS = ("oom_kill_delta", "pids_max_delta")


class AdapterStateError(RuntimeError):
    """A call out of the start_take / turn / end_take order."""


@dataclass(frozen=True)
class TurnResult:
    exit_code: int | None
    text: str
    stream_path: str | None
    end_reason: str
    init: dict | None = None
    api_error: dict | None = None
    counters: dict = field(default_factory=lambda: {k: 0 for k in COUNTER_FIELDS})
    started_at: float = 0.0
    ended_at: float = 0.0

    def __post_init__(self):
        if self.end_reason not in END_REASONS:
            raise ValueError(f"end_reason {self.end_reason!r} is not one of {END_REASONS}")
        if set(self.counters) != set(COUNTER_FIELDS):
            raise ValueError(f"counters must name exactly {COUNTER_FIELDS}")
        if self.init is not None and not set(INIT_FIELDS) <= set(self.init):
            raise ValueError(f"init must carry {INIT_FIELDS}")
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

    `box` carries the records no adapter produces: `preflight_ok`, `container_started`,
    `container_exited` (the runtime's exit record shows the container itself died),
    `sidecar` ({start_record, stop_record, exit_code, queue_overflow}), `unexplained_operator_diffs`,
    `checker_reasons`, `quiescence_kill`, `outside_reach_events`, `finalize_abort`, `committed`.
    The agent's text is never copied in.
    """
    api_errors = [t.api_error for t in turns if t.api_error is not None]
    return {
        "ledger": {
            "first_turn_started": bool(turns),
            "turns": len(turns),
            "end": turns[-1].end_reason if turns else None,
            "turn_ends": [t.end_reason for t in turns],
            "committed": bool(box.get("committed", False)),
            "finalize_abort": bool(box.get("finalize_abort", False)),
        },
        "exit": {
            "container_started": bool(box["container_started"]),
            "container_exited": bool(box.get("container_exited", False)),
            "exec_codes": [t.exit_code for t in turns],
        },
        "cgroup": {k: sum(t.counters[k] for t in turns) for k in COUNTER_FIELDS},
        "init": [t.init for t in turns],
        "pin": dict(pin),
        "api_error": api_errors[0] if api_errors else None,
        "sidecar": dict(box["sidecar"]),
        "preflight": {"ok": bool(box["preflight_ok"])},
        "operator": {"unexplained_diffs": int(box.get("unexplained_operator_diffs", 0))},
        "checker_reasons": list(box.get("checker_reasons", [])),
        "quiescence_kill": bool(box.get("quiescence_kill", False)),
        "events": {"outside_reach": int(box.get("outside_reach_events", 0))},
    }
