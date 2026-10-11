"""The four stub agents, each on the ScriptedAdapter seam (agent_adapter.py), each driving a FakeRuntime.

A stub is built for one half of one task (`probes4.Half`) and the take's operator lines. Its moves are probes4's own
(`PROBES[task]`): every turn before the probe ends on its step's marker and makes the step's pre-registered actions
(`pre`), the probe turn makes the stub's one move (`probe_move`), and every later turn repeats that move's reply
(`later`), exactly as probes4.build_take constructs a triple. What differs between stubs is only `probe_move` and,
for the background-writer, who makes the probe turn's writes.

The adapter contract is the base class's: start_take, then one turn per operator line (the first with first=True),
then end_take; a turn past the script raises AdapterStateError. Each turn's TurnResult is scripted up front from the
same timing the runtime uses (ScriptedAdapter replays it); `_turn` then makes that turn happen in the runtime.

No model, no container, no network, standard library only.
"""

from __future__ import annotations

import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

import agent_adapter as aa  # noqa: E402
import probes4  # noqa: E402
from box.stub_agents import runtime as rt  # noqa: E402

STUB_VERSION = "stub-0"
STUB_MODEL = "stub-no-model"
STUB_MODE = "stub"
BUDGET_S = 900.0
# The four stubs' names, as the plan's CP6 block names them.
ORACLE_NAME, ACT_NAME, HOLD_NAME, WRITER_NAME = "oracle", "act-only", "hold-only", "background-writer"
COUNTERS = {"oom_kill_delta": 0, "pids_max_delta": 0}


def turn_moves(pr, h: probes4.Half, lines: list, probe_mv: dict) -> list:
    """The move of every turn of the take, as probes4.build_take makes it."""
    probe = h.task["halves"][h.half]["probe_operator_turn"]
    out = []
    for k, _line, marker in lines:
        if k < probe:
            writes, calls = pr.pre(h, k) if hasattr(pr, "pre") else ({}, [])
            out.append(probes4.move(texts=[marker or "ok"], calls=calls, writes=writes))
        elif k == probe:
            out.append(probe_mv)
        else:
            later = probe_mv["later"] if probe_mv["later"] is not None else probe_mv["texts"]
            out.append(probes4.move(texts=later))
    return out


class StubAgent(aa.ScriptedAdapter):
    """Base: a ScriptedAdapter whose turns also happen in a FakeRuntime."""

    name = "stub"
    stub = "abstract"

    def __init__(self, h: probes4.Half, lines: list, runtime: rt.FakeRuntime):
        self.half, self.runtime, self.lines_planned = h, runtime, list(lines)
        self.pr = probes4.PROBES[h.task["task"]]
        self.probe = h.task["halves"][h.half]["probe_operator_turn"]
        self.moves = turn_moves(self.pr, h, lines, self.probe_move(self.pr, h))
        super().__init__([self.scripted(k, mv) for (k, _l, _m), mv in zip(lines, self.moves)],
                         version=STUB_VERSION, container_id=None)

    # ---- what a stub decides ---------------------------------------------------------------------------------------
    def probe_move(self, pr, h: probes4.Half) -> dict:
        raise NotImplementedError

    def split(self, k: int, mv: dict) -> tuple:
        """(the move the turn makes itself, the background job it launches or None)."""
        return mv, None

    # ---- the record the host would see -----------------------------------------------------------------------------
    def scripted(self, k: int, mv: dict) -> aa.TurnResult:
        T = 100.0 * k
        texts = mv["texts"]
        return aa.TurnResult(exit_code=0, text=texts[-1] if texts else "", stream_path=None, end_reason=aa.END_TURN,
                             init={"model": STUB_MODEL, "permission_mode": STUB_MODE, "version": STUB_VERSION},
                             api_errors=[], counters=dict(COUNTERS), started_at=T + rt.STARTED, ended_at=T + rt.ENDED,
                             agent_output=bool(texts or mv["calls"]))

    # ---- the seam -------------------------------------------------------------------------------------------------
    def _start(self, take: dict) -> dict:
        started = super()._start(take)
        self.runtime.begin()
        return started

    def _turn(self, line: str, *, first: bool, budget_s: float) -> aa.TurnResult:
        k = self._turns + 1
        result = super()._turn(line, first=first, budget_s=budget_s)   # raises past the script
        own, job = self.split(k, self.moves[k - 1])
        seen = self.runtime.run_turn(k, line, own, background=job, last=k == len(self.moves))
        # Defensive: the runtime and the scripted record share one timing, so this cannot fire today; it refuses a
        # future drift between them rather than reading it (W6B-R1-4; no witness).
        if (seen["started_at"], seen["ended_at"]) != (result.started_at, result.ended_at):
            raise aa.AdapterStateError(f"turn {k}: the runtime's clock and the scripted record disagree")
        return result

    def _end(self) -> None:
        self.runtime.finish()
        super()._end()


class OracleStub(StubAgent):
    """The half's right move: the act half's act, the hold half's hold."""

    stub = ORACLE_NAME

    def probe_move(self, pr, h):
        return probes4.oracle_move(pr, h)


class ActOnlyStub(StubAgent):
    """The act half's move on every half (on the hold half, carried out against that half's fixture)."""

    stub = ACT_NAME

    def probe_move(self, pr, h):
        return probes4.act_move(pr, h)


class HoldOnlyStub(StubAgent):
    """The hold half's move on every half: no action, the hold reply."""

    stub = HOLD_NAME

    def probe_move(self, pr, h):
        return probes4.hold_move(pr, h)


class BackgroundWriterStub(OracleStub):
    """The oracle's move, with the probe turn's writes and deletes made by a process that outlives the turn.

    The turn itself makes the calls, reads and texts; the launched job makes every write and delete after the turn's
    end. `run_s` is the job's run time after the end (the runtime kills it at its quiescence cap)."""

    stub = WRITER_NAME
    run_s = rt.FAKE_BACKGROUND_RUN_S

    def split(self, k, mv):
        if k != self.probe or not (mv["writes"] or mv["deletes"]):
            return mv, None
        own = dict(mv, writes={}, deletes=[])
        return own, {"writes": dict(mv["writes"]), "deletes": list(mv["deletes"]), "reads": [], "run_s": self.run_s}


STUBS = {cls.stub: cls for cls in (OracleStub, ActOnlyStub, HoldOnlyStub, BackgroundWriterStub)}
