"""The fake runtime a stub agent drives: one take's run tree, clock, watcher log, snapshots and ledger, in memory.

It stands in for the box (the take container, the sidecar's snapshots and watcher, the driver's ledger) and records
exactly the parts `graders/endstate.py`'s `Evidence.from_parts` takes, in probes4.py's construction (`build_take`):

    turn k runs from T = 100k: pre-k snapshot at T, start T+1, the agent's own reads and writes at T+2, end T+3;
    a background job's writes land after the end, it stops by T+5 (or is killed at the quiescence cap), post-k at T+6;
    the operator's pre-registered writes after turn k at T+7; the watcher runs from 50.0 to the last turn's T+8.

A background job is a process the agent's turn launches and that outlives the turn (GARS's stage 00 finalize is the
real case). The runtime waits for every job of a turn before that turn's post snapshot (quiescence): a job that ends
inside `FAKE_QUIESCENCE_CAP_S` has its writes in the snapshot and in the watcher log, stamped after the turn's end;
a job still running at the cap is killed there: the writes it made before the cap land (late, as any of its writes),
the writes it would have made after the cap never do, and the take's box record says so (`quiescence_kill`,
`quiescence_cap_survivors`). The cap here is a fake test value; the real cap is CP2's. A cap longer than the gap
between a turn's end and its post snapshot (POST - ENDED) is refused, so every landed write precedes the snapshot.

THE HARNESS NAME. The take record carries probes4's harness name (`probes4.HARNESS`, the parser table's one harness)
and probes4's constructed model name, never the stub's identity, because the graders parse the transcript through
that table. A stub take that is ever persisted (S6, the CP6 box run) must stamp the stub's identity into its own
evidence; this in-memory runtime does not (a named residual in the lane report).

No model, no container, no network, standard library only. Writes nothing to disk.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

import probes4  # noqa: E402
from graders import endstate as es  # noqa: E402

# The offsets inside a turn (seconds after T = 100k), as probes4.build_take and tests/test_endstate.py use them.
STARTED, AGENT, ENDED, POST, OPERATOR = 1, 2, 3, 6, 7
# FAKE TEST VALUES (glitch-1b's ruling R2 on lane w6b): how long the runtime waits after a turn's end for its
# background jobs before killing them, and a job's default run time. Both are fake values on this runtime's clock,
# for the stub tests only; the real cap is CP2's (the drive step's), never this one.
FAKE_QUIESCENCE_CAP_S = 2.5
# A job writes WRITE_LEAD_S before it exits, at end + run.
FAKE_BACKGROUND_RUN_S = 2.0
WRITE_LEAD_S = 1
WATCH_START = 50.0


class RuntimeStateError(RuntimeError):
    """A runtime call in the wrong order: a turn before begin, a turn number in the wrong sequence, or anything
    after finish."""


class FakeRuntime:
    """One take's box, faked. `begin`, then `run_turn` once per operator line in order, then `finish`."""

    def __init__(self, fixture: dict, *, model: str = probes4.MODEL, harness: str = probes4.HARNESS,
                 version: str = "0", operator=None, quiescence_cap_s: float = FAKE_QUIESCENCE_CAP_S):
        self.tree = dict(fixture)              # run-tree path -> probes4 value (blob, hashed, link, DIR)
        self.operator = operator               # callable(k) -> {path: value}: the operator's writes after turn k
        self.cap = float(quiescence_cap_s)
        if self.cap > POST - ENDED:
            raise ValueError(f"the quiescence cap ({self.cap}) must end by the post snapshot (at most {POST - ENDED})")
        self.blobs: dict = {}
        self.snapshots: dict = {}
        self.access: list = []
        self.records: list = []                # the session's records, in the harness's own shape
        self.ledger = [{"kind": "take", "model": model, "agent": {"harness": harness, "version": version},
                        "run_tree": "", "home": None}]
        self.turns = 0
        self.quiescence_kill = False
        self.cap_survivors = 0
        self.state = "new"
        self._calls = 0

    # ---- the take's order -----------------------------------------------------------------------------------------
    def begin(self) -> None:
        if self.state != "new":
            raise RuntimeStateError(f"begin while {self.state}")
        self.state = "open"

    def run_turn(self, k: int, line: str, mv: dict, *, background: dict | None = None, last: bool = False) -> dict:
        """Turn k: the operator's line, the agent's move `mv` (probes4.move shape) made at T+2, then `background`
        (a probes4.move of writes and deletes, with an optional "run_s") made by a job that outlives the turn.
        Returns the host's view of the turn: {started_at, ended_at, text, agent_output}."""
        if self.state != "open":
            raise RuntimeStateError(f"turn {k} while {self.state}")
        if k != self.turns + 1:
            raise RuntimeStateError(f"turn {k} after turn {self.turns}")
        T = 100.0 * k
        self.snapshots[f"pre-{k}"] = self._snapshot(f"pre-{k}", T)
        started, ended = T + STARTED, T + ENDED
        self.ledger.append({"kind": "turn", "n": k, "started_at": started, "ended_at": ended})
        self.records.append({"type": "user", "message": {"role": "user", "content": line}})
        for name, args, result in mv["calls"]:
            self._calls += 1
            ref = f"toolu_{self._calls:04d}"
            self.records.append({"type": "assistant", "message": {"model": self.ledger[0]["model"], "content": [
                {"type": "tool_use", "id": ref, "name": name, "input": args}]}})
            self.records.append({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": ref, "content": result}]}})
        for text in mv["texts"]:
            self.records.append({"type": "assistant", "message": {"model": self.ledger[0]["model"],
                                                                   "content": [{"type": "text", "text": text}]}})
        self._apply(mv, T + AGENT)
        if background:
            self._background(k, background, ended)
        self.snapshots[f"post-{k}"] = self._snapshot(f"post-{k}", T + POST)
        op = self.operator(k) if self.operator is not None and not last else {}
        if op:
            self.ledger.append({"kind": "operator", "id": f"operator-{k}", "at": T + OPERATOR,
                                "writes": [{"path": p, "after": probes4.state(v)} for p, v in op.items()]})
            self.tree.update(op)
        self.turns = k
        texts = mv["texts"]
        return {"started_at": started, "ended_at": ended, "text": texts[-1] if texts else "",
                "agent_output": bool(texts or mv["calls"])}

    def finish(self) -> None:
        if self.state != "open":
            raise RuntimeStateError(f"finish while {self.state}")
        self.state = "finished"

    # ---- what the take leaves -------------------------------------------------------------------------------------
    def transcript(self) -> list:
        return [json.dumps(r, sort_keys=True) for r in self.records]

    def health(self) -> list:
        return [{"kind": "watcher-start", "at": WATCH_START},
                {"kind": "watcher-stop", "at": 100.0 * self.turns + 8, "exit_code": 0, "ignored_newline_paths": 0}]

    def evidence(self):
        """The take's evidence, as endstate reads it (only after `finish`)."""
        if self.state != "finished":
            raise RuntimeStateError(f"evidence while {self.state}")
        return es.Evidence.from_parts(ledger=self.ledger, snapshots=self.snapshots, access=self.access,
                                      health=self.health(), blobs=self.blobs)

    def box_records(self) -> dict:
        """The box's own records for `agent_adapter.harness_records` (BOX_KEYS exactly): a clean fake box, with the
        quiescence outcome this runtime measured. The fake commits nothing."""
        return {"preflight_ok": True, "container_started": True, "container_exited": False,
                "sidecar": {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False},
                "unexplained_operator_diffs": 0, "checker_reasons": [], "quiescence_kill": self.quiescence_kill,
                "outside_reach_events": 0, "finalize_abort": False, "committed": False,
                "unreadable_consequential": [], "quiescence_cap_survivors": self.cap_survivors}

    # ---- inside -----------------------------------------------------------------------------------------------------
    def _snapshot(self, label: str, at: float) -> dict:
        entries = {}
        for p, v in self.tree.items():
            entries[p] = probes4.state(v)
            if v[0] == "bytes":
                self.blobs[entries[p]["sha256"]] = v[1]
        return {"label": label, "taken_at": at, "entries": entries}

    def _apply(self, mv: dict, at: float) -> None:
        for p in mv.get("reads", ()):
            self.access.append({"at": at, "path": p, "op": "open"})
        for p in mv.get("deletes", ()):
            self.access.append({"at": at, "path": p, "op": "delete"})
            self.tree.pop(p, None)
        for p, v in mv.get("writes", {}).items():
            self.access.append({"at": at, "path": p, "op": "delete" if v is None else "modify"})
            if v is None:
                self.tree.pop(p, None)
            else:
                self.tree[p] = v

    def _background(self, k: int, job: dict, ended: float) -> None:
        """Quiescence: wait for the job up to the cap. It writes WRITE_LEAD_S before it exits. A job still running
        at the cap is killed there: its writes land if it made them by the cap (run_s - WRITE_LEAD_S <= cap), and
        never if it would have made them after."""
        run = float(job.get("run_s", FAKE_BACKGROUND_RUN_S))
        if not run > WRITE_LEAD_S:
            raise ValueError(f"a background job must write after its turn's end: run_s must exceed {WRITE_LEAD_S} "
                             f"(got {run})")
        if run > self.cap:
            if run - WRITE_LEAD_S <= self.cap:
                self._apply(job, ended + run - WRITE_LEAD_S)
            self.quiescence_kill = True
            self.cap_survivors += 1
            self.ledger.append({"kind": "background", "pid": 4242 + k, "stopped_at": ended + self.cap})
            return
        self._apply(job, ended + run - WRITE_LEAD_S)
        self.ledger.append({"kind": "background", "pid": 4242 + k, "stopped_at": ended + run})
