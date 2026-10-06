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
  4. inside each drive step, route the take's harness-side records (`routing.route`) before its
     commit, so a re-run frees its slot before it closes; remove the container BY THE RECORDED
     ID, never by a name pattern;
  5. commit the block's records serially, in row order.

EVERY TERMINAL STATE IS WATCHED, never success alone: the five routes, plus `blocked` (routing
refused the records) and `failed` (the driver raised, or the loop could not go on). The handlers
are keyed by `labels4.TERMINAL_STATES`; a state with no handler stops the loop from starting.

  graded, aborted  final for the slot (aborted is never re-run)
  rehearsal        re-run in the same slot while the half-cell's rehearsal cap allows
  harness-error    one re-run in the same slot, within the half-cell's cap; beyond it the slot is
                   final as harness-error (published in its own column, out of the denominator)
  pause            the slot is re-run in the same slot within the pause cap, and NO NEW DRIVE is
                   launched until the usage window resets; drives already running finish and are
                   routed as usual
  blocked, failed  the loop stops launching; the rest of the queue stays unstarted for a human

A cap beyond which the plan names no fate (rehearsal, pause) ends the slot as `blocked`. The caps
are read from routing.json; while round 3's pause cap is still pending there (null), the loop
refuses to start.

THE DRIVER. `Batch` never imports drive.py, Claude Code or any adapter: it receives a driver
object with three methods,

    launch(row) -> container_id      start the take's container; the id is recorded by the loop
    drive(row, container_id) -> dict the take's harness-side records, in routing.py's schema
    remove(container_id) -> None     remove exactly that container

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


class BatchConfigError(RuntimeError):
    """The loop cannot start: a pending cap, an unhandled terminal state, no nohup."""


def pending_caps(table: dict) -> list[str]:
    """Routes that can re-run but whose half-cell cap is still null in routing.json."""
    out = []
    for r in (labels4.REHEARSAL, labels4.HARNESS_ERROR, labels4.PAUSE):
        if table["caps"][r].get("reruns_per_half_cell") is None:
            out.append(r)
    return out


class Batch:
    def __init__(self, driver, repo, window, *, table: dict | None = None, serial: bool = False,
                 route_fn=None):
        self.driver, self.repo, self.window = driver, repo, window
        self.table = table if table is not None else routing.load_table()
        self.route_fn = route_fn or routing.route
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
        pend = pending_caps(self.table)
        if pend:
            raise BatchConfigError(f"caps still pending in routing.json: {pend}")
        self.outcomes: list[dict] = []
        self.containers: dict = {}           # (slot, attempt) -> recorded container id
        self.reruns = collections.Counter()  # (half_cell, route) -> re-runs spent
        self.slot_reruns = collections.Counter()  # (slot, route) -> re-runs spent
        self.stopped = None
        self.paused = False

    # ------------------------------------------------------------------------------- the loop
    def run(self, rows: list[dict]) -> list[dict]:
        queue = collections.deque((dict(r), 1) for r in rows)
        while queue and self.stopped is None:
            if self.paused:
                self.window.wait_reset()
                self.paused = False
            block = [queue.popleft() for _ in range(min(self.block, len(queue)))]
            for row, attempt in block:                       # serial: one commit each
                self.repo.register(row, attempt)
            launched = []
            for row, attempt in block:                       # record every id at launch
                try:
                    cid = self.driver.launch(row)
                except Exception as e:  # noqa: BLE001 - a launch failure is a terminal state
                    launched.append((row, attempt, None, e))
                    continue
                self.containers[(row["slot"], attempt)] = cid
                launched.append((row, attempt, cid, None))
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(block)) as pool:
                futures = [pool.submit(self._drive_step, row, attempt, cid, err)
                           for row, attempt, cid, err in launched]
                results = [f.result() for f in futures]      # row order, whatever finished first
            requeue = []
            for (row, attempt, cid, _), outcome in zip(launched, results):   # serial, row order
                try:
                    self.repo.commit_records(row, attempt, outcome)
                except Exception as e:  # noqa: BLE001
                    outcome = dict(outcome, state=labels4.FAILED, reason=f"commit failed: {e}")
                self.outcomes.append(outcome)
                again = self.handlers[outcome["state"]](row, attempt, outcome)
                if again:
                    requeue.append((row, attempt + 1))
            queue.extendleft(reversed(requeue))              # same slots, first, in row order
        return self.outcomes

    def _drive_step(self, row: dict, attempt: int, cid, launch_error) -> dict:
        """Drive, then route before the commit; the container is removed by its recorded id."""
        base = {"slot": row["slot"], "half_cell": row["half_cell"], "attempt": attempt, "container_id": cid}
        if launch_error is not None:
            return dict(base, state=labels4.FAILED, reason=f"launch failed: {launch_error}")
        try:
            records = self.driver.drive(row, cid)
        except Exception as e:  # noqa: BLE001
            return dict(base, state=labels4.FAILED, reason=f"drive failed: {e}")
        finally:
            self.driver.remove(cid)
        try:
            decision = self.route_fn(records, self.table)
        except routing.RoutingRefused as e:
            return dict(base, state=labels4.BLOCKED, reason=f"routing refused: {e}", records=records)
        return dict(base, state=decision["route"], decision=decision, records=records)

    # --------------------------------------------------------------------------- the handlers
    def _final(self, row, attempt, outcome):
        return False

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
            return True
        if route == labels4.HARNESS_ERROR:
            outcome["beyond_cap"] = True   # final: harness-error, its own column
            return False
        outcome["beyond_cap"] = True       # the plan names no fate: a human decides
        self._stop(row, attempt, dict(outcome, reason=f"{route} cap reached"))
        return False

    def _pause(self, row, attempt, outcome):
        self.paused = True
        if self._within_cap(row, labels4.PAUSE):
            return True
        outcome["beyond_cap"] = True
        self._stop(row, attempt, dict(outcome, reason="pause cap reached"))
        return False

    def _stop(self, row, attempt, outcome):
        if self.stopped is None:
            self.stopped = {"slot": row["slot"], "attempt": attempt, "state": outcome["state"],
                            "reason": outcome.get("reason")}
        return False


# ------------------------------------------------------------------------------------- the CLI
def under_nohup() -> bool:
    return signal.getsignal(signal.SIGHUP) == signal.SIG_IGN


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--states", action="store_true", help="print the terminal states the loop watches")
    ap.add_argument("--check", action="store_true", help="check routing.json and the caps the loop needs")
    ap.add_argument("--foreground", action="store_true", help="allow running without nohup")
    ap.add_argument("--serial", action="store_true", help="one take at a time (the fallback)")
    args = ap.parse_args(argv)
    if args.states:
        print(json.dumps({"routes": list(labels4.ROUTES), "batch": list(labels4.BATCH_STATES)}))
        return 0
    table = routing.load_table()
    pend = pending_caps(table)
    if args.check:
        print(f"batch: caps pending in routing.json: {pend}" if pend else "batch: routing.json ready")
        return 1 if pend else 0
    if not (under_nohup() or args.foreground):
        print("batch: run under nohup (or pass --foreground)", file=sys.stderr)
        return 2
    print("batch: no driver exists yet; the sealed box's driver arrives in CP2", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
