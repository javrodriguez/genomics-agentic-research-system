#!/usr/bin/env python3
"""Round 4's take loop: register row -> commit -> drive -> route -> commit, inside the repo.

Round 3 drove its takes from an out-of-repo `batch.sh` (a verify-3 finding); this is its in-repo
replacement. It runs under `nohup` and refuses to start otherwise (`--foreground` overrides, for a
watched terminal).

SERIAL WHERE IT MATTERS, CONCURRENT WHERE IT IS SAFE. Registering and committing stay serial;
only the drives run at once:

  1. take a block of up to three slots from the queue (one with `serial=True`, the fallback);
  2. register each row, one commit each, in row order;
  3. launch each take's container and RECORD ITS ID; drive the block concurrently;
  4. inside each drive step, remove the container BY THE RECORDED ID (never by a name pattern),
     then decide the take's annotations (`routing.annotate`: events, mask) and its route
     (`routing.route`) from its harness-side records, before its commit, so a re-run frees its
     slot before it closes. The drive step never raises: whatever goes wrong becomes the take's
     terminal state;
  5. decide each take's fate (below), then commit its records with that fate, serially, in row
     order, for every take of the block, even after one of them failed; only then stop.

EVERY TERMINAL STATE IS WATCHED, never success alone: the five routes, plus `blocked` (routing
refused the records, or the driver's pin is not the registered row's) and `failed` (the driver
raised, a container could not be removed, routing raised, or a commit failed). The handlers are
keyed by `labels4.TERMINAL_STATES`; a state with no handler stops the loop from starting.

  graded, aborted  final for the slot (aborted is never re-run)
  rehearsal        re-run in the same slot while the half-cell's rehearsal cap allows
  harness-error    one re-run in the same slot, within the half-cell's cap; beyond it the slot is
                   final as harness-error (published in its own column, out of the denominator)
  pause            the slot is re-run in the same slot within the pause cap, and NO NEW DRIVE is
                   launched until the usage window resets; drives already running finish and are
                   routed as usual
  blocked, failed  the loop stops launching; the rest of the queue stays unstarted for a human

A cap beyond which the plan names no fate (rehearsal, pause) stops the loop for a human.

WHAT IS COMMITTED. `repo.commit_records(row, attempt, outcome)` receives one outcome per take,
with every key below always present (None where it does not apply), decided BEFORE the commit:

    slot, half_cell, attempt     the registered row and its attempt
    container_id                 the id recorded at launch (None if the driver named none)
    state                        a labels4 terminal state
    reason                       why, for blocked and failed (else None)
    decision                     routing.route's return (None when the take was not routed)
    records                      the harness-side records the driver returned (None if none)
    events                       routing.annotate's events, or None when the records could not
                                 be read (then nothing can be counted, and a human must look)
    mask                         True when the take's text must be masked, never deleted, before
                                 this commit writes it. Decided on every take from the annotations;
                                 True, fail-closed, whenever the records could not be read
    mask_basis                   "annotations" or why the mask was set fail-closed
    leaked_container             the recorded id of a container remove() failed on (else None)
    final                        True when this record is the slot's final result
    rerun                        True when the slot is re-run (same slot, next attempt)
    beyond_cap                   True when a cap was reached
    stop                         why the loop stops after this block (else None)

The repo masks the take's text whenever `mask` is true; it never deletes it.

THE START GATE. The loop refuses to start (`BatchConfigError`, and `batch.py --check` exits 1)
while routing.json still lacks what only the owner or a later checkpoint can supply: round 3's
pause cap, round 3's operator-side reasons (an empty list, or a status starting PENDING), or the
pre-registered pin profiles (CP5). Every row must name a model that has a profile.

THE DRIVER. `Batch` never imports drive.py, Claude Code or any adapter: it receives a driver
object with three methods,

    launch(row) -> container_id      start the take's container; the id is recorded by the loop.
                                     If it raises after creating a container, the exception's
                                     `container_id` attribute (when set) is recorded and removed
    drive(row, container_id) -> dict the take's harness-side records, in routing.py's schema; its
                                     `pin` must be the registered row's model's pre-registered
                                     profile, or the take is blocked (the driver is never trusted
                                     for the pin)
    remove(container_id) -> None     remove exactly that container (never called with None)

and a repo object with `register(row, attempt)` and `commit_records(row, attempt, outcome)`, each
one commit, and a usage window with `wait_reset()`. CP2 supplies the real three.

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import json
import os
import signal
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import routing  # noqa: E402
from graders import labels4  # noqa: E402

BLOCK = 3
PENDING = "PENDING"

# Every key of a committed outcome (see WHAT IS COMMITTED).
OUTCOME_KEYS = ("slot", "half_cell", "attempt", "container_id", "state", "reason", "decision", "records",
                "events", "mask", "mask_basis", "leaked_container", "final", "rerun", "beyond_cap", "stop")


class BatchConfigError(RuntimeError):
    """The loop cannot start: pending data, an unhandled terminal state, a bad row, no nohup."""


def pending_caps(table: dict) -> list[str]:
    """Routes that can re-run but whose half-cell cap is still null in routing.json."""
    out = []
    for r in (labels4.REHEARSAL, labels4.HARNESS_ERROR, labels4.PAUSE):
        if table["caps"][r].get("reruns_per_half_cell") is None:
            out.append(r)
    return out


def start_problems(table: dict) -> list[str]:
    """Everything that keeps the loop from starting on this table (empty when it may start)."""
    p = [f"cap {r} is still pending in routing.json" for r in pending_caps(table)]
    if not table.get("operator_reasons"):
        p.append("operator_reasons is empty in routing.json (round 3's operator-side reasons)")
    if str(table.get("operator_reasons_status", PENDING)).startswith(PENDING):
        p.append("operator_reasons_status is PENDING in routing.json")
    if not table.get("pin_profiles"):
        p.append("pin_profiles is empty in routing.json (CP5 pre-registers them)")
    if str(table.get("pin_profiles_status", PENDING)).startswith(PENDING):
        p.append("pin_profiles_status is PENDING in routing.json")
    return p


def expected_pin(row: dict, table: dict) -> dict:
    """The pin a take of this registered row must run under: its model and that model's profile."""
    return dict(table["pin_profiles"][row["model"]], model=row["model"])


class Batch:
    def __init__(self, driver, repo, window, *, table: dict | None = None, serial: bool = False,
                 route_fn=None, annotate_fn=None):
        self.driver, self.repo, self.window = driver, repo, window
        self.table = table if table is not None else routing.load_table()
        self.route_fn = route_fn or routing.route
        self.annotate_fn = annotate_fn or routing.annotate
        self.block = 1 if serial else BLOCK
        self.handlers = {
            labels4.GRADED: self._final,
            labels4.ABORTED: self._final,
            labels4.REHEARSAL: self._rerun_within_cap,
            labels4.HARNESS_ERROR: self._rerun_within_cap,
            labels4.PAUSE: self._pause,
            labels4.BLOCKED: self._stop,
            labels4.FAILED: self._stop,
        }
        missing = set(labels4.TERMINAL_STATES) - set(self.handlers)
        unknown = set(self.handlers) - set(labels4.TERMINAL_STATES)
        if missing or unknown:
            raise BatchConfigError(f"terminal states without a handler: {sorted(missing)}; "
                                   f"handlers for unknown states: {sorted(unknown)}")
        problems = start_problems(self.table)
        if problems:
            raise BatchConfigError("routing.json is not ready: " + "; ".join(problems))
        self.outcomes: list[dict] = []
        self.containers: dict = {}           # (slot, attempt) -> recorded container id
        self.reruns = collections.Counter()  # (half_cell, route) -> re-runs spent
        self.slot_reruns = collections.Counter()  # (slot, route) -> re-runs spent
        self.stopped = None
        self.paused = False

    # ------------------------------------------------------------------------------- the loop
    def row_problems(self, rows: list[dict]) -> list[str]:
        p = []
        for r in rows:
            if not isinstance(r, dict) or not all(k in r for k in ("slot", "half_cell", "model")):
                p.append(f"row {r!r} must name slot, half_cell and model")
            elif r["model"] not in self.table["pin_profiles"]:
                p.append(f"row {r['slot']}: model {r['model']!r} has no pre-registered pin profile")
        slots = [r.get("slot") for r in rows if isinstance(r, dict)]
        if len(set(slots)) != len(slots):
            p.append("slots repeat")
        return p

    def run(self, rows: list[dict]) -> list[dict]:
        problems = self.row_problems(rows)
        if problems:
            raise BatchConfigError("; ".join(problems))
        queue = collections.deque((dict(r), 1) for r in rows)
        while queue and self.stopped is None:
            if self.paused:
                self.window.wait_reset()
                self.paused = False
            block = [queue.popleft() for _ in range(min(self.block, len(queue)))]
            for row, attempt in block:                       # serial: one commit each
                self.repo.register(row, attempt)
            launched = [(row, attempt) + self._launch(row, attempt) for row, attempt in block]   # ids recorded
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(block)) as pool:
                futures = [pool.submit(self._drive_step, row, attempt, cid, err)
                           for row, attempt, cid, err in launched]
                results = [self._result(f, row, attempt, cid)              # row order
                           for (row, attempt, cid, _), f in zip(launched, futures)]
            requeue = []
            for (row, attempt, _, _), outcome in zip(launched, results):   # serial, row order, all of them
                outcome.update(self._decide(row, attempt, outcome))   # the fate, before the commit
                try:
                    self.repo.commit_records(row, attempt, outcome)
                except Exception as e:  # noqa: BLE001
                    outcome = dict(outcome, state=labels4.FAILED, reason=f"commit failed: {e}",
                                   final=False, rerun=False, stop=f"commit failed: {e}")
                    self._stop(row, attempt, outcome)
                self.outcomes.append(outcome)
                if outcome["rerun"]:
                    requeue.append((row, attempt + 1))
            queue.extendleft(reversed(requeue))              # same slots, first, in row order
        return self.outcomes

    @staticmethod
    def _outcome(row, attempt, cid, **kw) -> dict:
        out = dict.fromkeys(OUTCOME_KEYS)
        out.update(slot=row["slot"], half_cell=row["half_cell"], attempt=attempt, container_id=cid,
                   mask=True, mask_basis="no records: masked fail-closed", final=False, rerun=False,
                   beyond_cap=False)
        out.update(kw)
        return out

    def _launch(self, row, attempt) -> tuple:
        """Launch and record the container id: (id, None), or (id or None, the launch error). A
        driver that raises after creating a container names it on the exception's
        `container_id`; that id is recorded and removed like any other."""
        try:
            cid = self.driver.launch(row)
        except Exception as e:  # noqa: BLE001 - a launch failure is a terminal state
            cid, err = getattr(e, "container_id", None), e
        else:
            err = None
        if cid is not None:
            self.containers[(row["slot"], attempt)] = cid
        return cid, err

    def _result(self, future, row, attempt, cid) -> dict:
        """The drive step's outcome; if the step itself raised, `failed`, never a sunk block."""
        try:
            return future.result()
        except Exception as e:  # noqa: BLE001
            return self._outcome(row, attempt, cid, state=labels4.FAILED,
                                 reason=f"drive step raised: {type(e).__name__}: {e}")

    def _remove(self, cid):
        """Remove the container by its recorded id; the error, never raised, or None."""
        if cid is None:
            return None
        try:
            self.driver.remove(cid)
        except Exception as e:  # noqa: BLE001
            return e
        return None

    def _drive_step(self, row: dict, attempt: int, cid, launch_error) -> dict:
        """Drive, remove the container by its recorded id, then annotate and route before the
        commit. Never raises: every failure is this take's terminal state."""
        records, out = None, None
        if launch_error is not None:
            out = self._outcome(row, attempt, cid, state=labels4.FAILED, reason=f"launch failed: {launch_error}")
        else:
            try:
                records = self.driver.drive(row, cid)
            except Exception as e:  # noqa: BLE001
                out = self._outcome(row, attempt, cid, state=labels4.FAILED, reason=f"drive failed: {e}")
        removal_error = self._remove(cid)                  # by the recorded id, whatever happened
        if out is None:
            out = self._route(row, attempt, cid, records)
        out.update(self._annotations(records))
        if removal_error is not None:
            out.update(state=labels4.FAILED, leaked_container=cid,
                       reason=f"container {cid} leaked: remove failed: {removal_error}"
                              + (f" (after: {out['reason']})" if out["reason"] else ""))
        return out

    def _route(self, row, attempt, cid, records) -> dict:
        if not isinstance(records, dict) or records.get("pin") != expected_pin(row, self.table):
            got = records.get("pin") if isinstance(records, dict) else None
            return self._outcome(row, attempt, cid, state=labels4.BLOCKED, records=records,
                                 reason=f"the driver's pin {got!r} is not the registered row's pre-registered "
                                        f"profile {expected_pin(row, self.table)!r}")
        try:
            decision = self.route_fn(records, self.table)
        except routing.RoutingRefused as e:
            return self._outcome(row, attempt, cid, state=labels4.BLOCKED, reason=f"routing refused: {e}",
                                 records=records)
        except Exception as e:  # noqa: BLE001 - routing must never sink the block
            return self._outcome(row, attempt, cid, state=labels4.FAILED, records=records,
                                 reason=f"routing raised: {type(e).__name__}: {e}")
        if not isinstance(decision, dict) or decision.get("route") not in labels4.ROUTES:
            return self._outcome(row, attempt, cid, state=labels4.FAILED, records=records,
                                 reason=f"routing returned no labels4 route: {decision!r}")
        return self._outcome(row, attempt, cid, state=decision["route"], decision=decision, records=records)

    def _annotations(self, records) -> dict:
        """The mask and events for every take, whatever its state: fail-closed when unreadable."""
        if records is None:
            return {"events": None, "mask": True, "mask_basis": "no records: masked fail-closed"}
        try:
            notes = self.annotate_fn(records, self.table)
        except Exception as e:  # noqa: BLE001 - malformed records: nothing can be counted
            return {"events": None, "mask": True, "mask_basis": f"records unreadable, masked fail-closed: {e}"}
        return {"events": list(notes["events"]), "mask": bool(notes["mask"]), "mask_basis": "annotations"}

    # --------------------------------------------------------------------------- the handlers
    # Each returns the take's fate: {final, rerun, beyond_cap, stop}. It is decided before the
    # commit and committed with the take's records.
    def _decide(self, row, attempt, outcome) -> dict:
        return self.handlers[outcome["state"]](row, attempt, outcome)

    @staticmethod
    def _fate(final=False, rerun=False, beyond_cap=False, stop=None) -> dict:
        return {"final": final, "rerun": rerun, "beyond_cap": beyond_cap, "stop": stop}

    def _final(self, row, attempt, outcome):
        return self._fate(final=True)

    def _within_cap(self, row, route) -> bool:
        cap = self.table["caps"][route]
        per_cell = cap.get("reruns_per_half_cell")
        per_slot = cap.get("reruns_per_slot")
        if per_cell is not None and self.reruns[(row["half_cell"], route)] >= per_cell:
            return False
        if per_slot is not None and self.slot_reruns[(row["slot"], route)] >= per_slot:
            return False
        self.reruns[(row["half_cell"], route)] += 1
        self.slot_reruns[(row["slot"], route)] += 1
        return True

    def _rerun_within_cap(self, row, attempt, outcome):
        route = outcome["state"]
        if self._within_cap(row, route):
            return self._fate(rerun=True)
        if route == labels4.HARNESS_ERROR:
            return self._fate(final=True, beyond_cap=True)   # final: harness-error, its own column
        fate = self._fate(beyond_cap=True, stop=f"{route} cap reached")   # the plan names no fate
        self._stop(row, attempt, dict(outcome, **fate))
        return fate

    def _pause(self, row, attempt, outcome):
        self.paused = True
        if self._within_cap(row, labels4.PAUSE):
            return self._fate(rerun=True)
        fate = self._fate(beyond_cap=True, stop="pause cap reached")
        self._stop(row, attempt, dict(outcome, **fate))
        return fate

    def _stop(self, row, attempt, outcome):
        reason = outcome.get("stop") or outcome.get("reason") or outcome["state"]
        if self.stopped is None:
            self.stopped = {"slot": row["slot"], "attempt": attempt, "state": outcome["state"], "reason": reason}
        return self._fate(beyond_cap=bool(outcome.get("beyond_cap")), stop=reason)


# ------------------------------------------------------------------------------------- the CLI
def under_nohup() -> bool:
    return signal.getsignal(signal.SIGHUP) == signal.SIG_IGN


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--states", action="store_true", help="print the terminal states the loop watches")
    ap.add_argument("--check", action="store_true", help="check routing.json and what the loop needs to start")
    ap.add_argument("--foreground", action="store_true", help="allow running without nohup")
    ap.add_argument("--serial", action="store_true", help="one take at a time (the fallback)")
    args = ap.parse_args(argv)
    if args.states:
        print(json.dumps({"routes": list(labels4.ROUTES), "batch": list(labels4.BATCH_STATES)}))
        return 0
    table = routing.load_table()
    problems = start_problems(table)
    if args.check:
        for prob in problems:
            print(f"batch: not ready: {prob}")
        if not problems:
            print("batch: routing.json ready")
        return 1 if problems else 0
    if not (under_nohup() or args.foreground):
        print("batch: run under nohup (or pass --foreground)", file=sys.stderr)
        return 2
    print("batch: no driver exists yet; the sealed box's driver arrives in CP2", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
