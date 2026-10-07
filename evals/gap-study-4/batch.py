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
  rehearsal        re-run in the same slot until its half-cell has had its cap of rehearsals; then
                   the half-cell closes (THE CELL CAPS)
  harness-error    one re-run in the same slot, within the half-cell's cap; beyond it the slot is
                   final as harness-error (published in its own column, out of the denominator)
  pause            re-run in the same slot until its half-cell has had its cap of pauses, then the
                   half-cell closes (THE CELL CAPS); either way NO NEW DRIVE is launched until the
                   usage window resets (THE USAGE WINDOW); drives already running finish and are
                   routed as usual
  blocked, failed  the loop stops launching; the rest of the queue stays unstarted for a human

THE CELL CAPS (glitch-f3's ruling, in-plan, 6 Oct 2026; recorded as glitch-f3's, not the owner's).
Rehearsals and pauses are counted per half-cell, round 3's unit. Round 3 counted the rehearsals (or
the pauses) of a cell, (task, half, model), and once the count reached the cap registered nothing
more for it, which published `incomplete — mechanical` (evals/gap-study-3/takes.py:280-291 at
e2979b31). Round 4's half-cell is (arm, task, half, model), the registered row's `half_cell`, with
wording and repeat or pressure as the slot inside it; the loop keys its counts by that value and
never reads inside it. Every committed rehearsal (or pause) of a half-cell counts, the take that
brings the count to routing.json's cap among them. That take is its slot's last (final, never
re-run, beyond_cap), and it is committed with `cell_state` = labels4.INCOMPLETE_MECHANICAL and a
`cell_reason` before the loop moves on. From then on nothing more is registered for the half-cell:
its queued rows and re-runs are dropped, each listed in `skipped`. The loop goes on with the other
half-cells; it never stops for a human here. A drive of the same block that was already running
when its half-cell closed is committed as usual, never re-run, and carries the cell state too.
Harness-error's own caps and its beyond-cap fate are unchanged.

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
                                 True, fail-closed, whenever the records could not be read and on
                                 every blocked or failed take (review round 2, W1B2-2)
    mask_basis                   "annotations" or why the mask was set fail-closed
    leaked_container             the recorded id of a container remove() failed on (else None)
    final                        True when this record is the slot's final result
    rerun                        True when the slot is re-run (same slot, next attempt)
    beyond_cap                   True when a cap was reached
    stop                         why the loop stops after this block (else None)
    cell_state                   labels4.INCOMPLETE_MECHANICAL once the take's half-cell has closed at
                                 its rehearsal or pause cap, by this take or an earlier one (else None)
    cell_reason                  why the half-cell closed: its count and cap (else None)

The repo masks the take's text whenever `mask` is true; it never deletes it. The mask rule is
applied at the one place every outcome passes before its commit (`_seal`), so no road to a commit
can skip it.

A RESTART CONTINUES, never resets (review round 2, W1B2-3). The caps and attempt numbers live in
the committed outcomes, not in this process: `Batch` reads them from the repo (`repo.history()`,
every outcome committed so far, in commit order; or a `history` argument read from it) and
rebuilds, before anything runs, the re-runs spent per half-cell and per slot, the rehearsals and
pauses counted per half-cell, the closed half-cells (from their committed cell state), and each
slot's next attempt (one past its last committed attempt). It never registers a row of a closed
half-cell (each is listed in `skipped`, and the other rows run), refuses a row whose slot is
already final, and refuses a history it cannot trust (not a list, a missing key, an unknown state
or cell state, a cell state without its reason, a (slot, attempt) twice, a slot under two
half-cells, an attempt after the slot's final one, or a cell state that disagrees with the counts:
the take that brings a half-cell to a cap carries it, so does every later take of that half-cell,
no other take does, and none of them is re-run). Lane w1b decision: when any of the last BLOCK
committed outcomes is a pause, a restart waits for the usage window before its first launch.

THE START GATE. The loop refuses to start (`BatchConfigError`, and `batch.py --check` exits 1)
while routing.json still lacks what only the owner or a later checkpoint can supply: round 3's
pause cap, round 3's operator-side reasons (an empty list, or a status starting PENDING), the
rate-limit markers' ruling (a status starting PENDING, W1B2-6), or the pre-registered pin
profiles (CP5). Every row must name a model that has a profile.

A REPO OR WINDOW FAILURE STOPS, never sinks (review round 2, W1B2-5). If `register` raises, every
row of the block already registered is committed `failed` (masked fail-closed, nothing launched),
the loop records why in `stopped` and returns; if `wait_reset` raises, nothing of the next block
was registered, so the loop records why in `stopped` and returns. A restart then continues from
the committed outcomes.

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
one commit, and `history()` (the committed outcomes), and a usage window with `wait_reset()`. CP2
supplies the real three.

THE USAGE WINDOW (glitch-f3's ruling, in-plan, 6 Oct 2026; recorded as glitch-f3's, not the
owner's). The loop calls `window.wait_reset()` before its next launch after a committed pause, and
on a restart when any of the last BLOCK committed outcomes is a pause (lane w1b decision 11); only
then does it register and launch. The contract CP2's window keeps, and this loop relies on:

    - wait_reset() returns promptly when the usage window has already reset (so a restart after a
      pause whose window reset meanwhile waits once and goes on, never a whole window again);
    - it blocks until the window resets otherwise;
    - it raises on failure, and the loop then stops as `failed` (W1B2-5): nothing of the next
      block is registered, launched or committed, and `stopped` says why.

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
                "events", "mask", "mask_basis", "leaked_container", "final", "rerun", "beyond_cap", "stop",
                "cell_state", "cell_reason")


# Routes that re-run a slot, whose spent re-runs a restart must count again.
RERUN_ROUTES = (labels4.REHEARSAL, labels4.HARNESS_ERROR, labels4.PAUSE)
# Routes counted per half-cell, round 3's unit, whose cap closes the half-cell (glitch-f3's ruling, THE CELL CAPS).
CELL_CAPPED_ROUTES = (labels4.REHEARSAL, labels4.PAUSE)


class BatchConfigError(RuntimeError):
    """The loop cannot start: pending data, an unhandled terminal state, a bad row, no nohup,
    untrustworthy history."""


# glitch-f3 (6 Oct 2026): the per-cell cap of a route counted per cell (rehearsal, pause) is named
# events_per_half_cell, the count of that route's committed outcomes, this one included (so at most cap-1 re-runs);
# harness-error keeps reruns_per_half_cell, the re-runs granted. A key whose meaning changed keeps no old name.
HALF_CELL_KEY = {labels4.REHEARSAL: "events_per_half_cell", labels4.PAUSE: "events_per_half_cell"}


def half_cell_key(route: str) -> str:
    return HALF_CELL_KEY.get(route, "reruns_per_half_cell")


def half_cell_cap(table: dict, route: str):
    return table["caps"][route].get(half_cell_key(route))


def pending_caps(table: dict) -> list[str]:
    """Routes that can re-run but whose half-cell cap is still null in routing.json."""
    out = []
    for r in (labels4.REHEARSAL, labels4.HARNESS_ERROR, labels4.PAUSE):
        if half_cell_cap(table, r) is None:
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
    if str(table.get("rate_limit_markers_status", PENDING)).startswith(PENDING):
        p.append("rate_limit_markers_status is PENDING in routing.json")
    return p


def expected_pin(row: dict, table: dict) -> dict:
    """The pin a take of this registered row must run under: its model and that model's profile."""
    return dict(table["pin_profiles"][row["model"]], model=row["model"])


class Batch:
    def __init__(self, driver, repo, window, *, table: dict | None = None, serial: bool = False,
                 route_fn=None, annotate_fn=None, history: list | None = None):
        self.driver, self.repo, self.window = driver, repo, window
        self.table = table if table is not None else routing.load_table()
        self.route_fn = route_fn or routing.route
        self.annotate_fn = annotate_fn or routing.annotate
        self.block = 1 if serial else BLOCK
        self.handlers = {
            labels4.GRADED: self._final,
            labels4.ABORTED: self._final,
            labels4.REHEARSAL: self._count_in_cell,
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
        self.next_attempt: dict = {}         # slot -> the attempt its next drive registers
        self.slot_cell: dict = {}            # slot -> its half-cell, as committed
        self.closed: dict = {}               # slot -> why it is never driven again
        self.cell_counts = collections.Counter()  # (half_cell, route) -> that route's outcomes committed in it
        self.closed_cells: dict = {}         # half_cell -> why nothing more is registered for it (as committed)
        self.skipped: list = []              # rows of a closed half-cell, dropped unregistered
        self.stopped = None
        self.paused = False
        if history is None:
            read = getattr(repo, "history", None)
            if not callable(read):
                raise BatchConfigError("the repo gives no history(): the caps and attempts of earlier runs "
                                       "cannot be rebuilt, so a restart could spend re-runs twice")
            history = read()
        self._replay(history)

    # ---------------------------------------------------------------------------- the history
    @staticmethod
    def history_problems(history) -> list[str]:
        """Why the committed outcomes cannot be trusted (empty when they can)."""
        if not isinstance(history, list):
            return ["history must be a list of committed outcomes"]
        p, seen, cell, final_at = [], set(), {}, {}
        for i, o in enumerate(history):
            if not isinstance(o, dict) or set(o) != set(OUTCOME_KEYS):
                p.append(f"history[{i}] must hold exactly the committed outcome keys")
                continue
            if o["state"] not in labels4.TERMINAL_STATES:
                p.append(f"history[{i}]: state {o['state']!r} is not a labels4 terminal state")
            if not (isinstance(o["attempt"], int) and not isinstance(o["attempt"], bool) and o["attempt"] >= 1):
                p.append(f"history[{i}]: attempt {o['attempt']!r} is not a positive int")
                continue
            if not all(isinstance(o[k], bool) for k in ("final", "rerun", "beyond_cap")):
                p.append(f"history[{i}]: final, rerun and beyond_cap must be bools")
            if o["cell_state"] is not None and o["cell_state"] not in labels4.CELL_STATES:
                p.append(f"history[{i}]: cell state {o['cell_state']!r} is not a labels4 cell state")
            elif (o["cell_state"] is None) != (o["cell_reason"] is None) or not (
                    o["cell_reason"] is None or (isinstance(o["cell_reason"], str) and o["cell_reason"])):
                p.append(f"history[{i}]: a cell state comes with its reason, and a reason with its state")
            key = (o["slot"], o["attempt"])
            if key in seen:
                p.append(f"history[{i}]: slot {o['slot']} attempt {o['attempt']} committed twice")
            seen.add(key)
            if cell.setdefault(o["slot"], o["half_cell"]) != o["half_cell"]:
                p.append(f"history[{i}]: slot {o['slot']} committed under two half-cells")
        for i, o in enumerate(history):   # an attempt after the slot's final one
            if isinstance(o, dict) and o.get("final") is True and isinstance(o.get("attempt"), int):
                final_at[o.get("slot")] = min(final_at.get(o.get("slot"), o["attempt"]), o["attempt"])
        for i, o in enumerate(history):
            if (isinstance(o, dict) and o.get("slot") in final_at and isinstance(o.get("attempt"), int)
                    and o["attempt"] > final_at[o["slot"]]):
                p.append(f"history[{i}]: slot {o['slot']} attempt {o['attempt']} comes after its final attempt")
        return p

    def _replay(self, history) -> None:
        """Rebuild the re-runs spent, each slot's next attempt and the closed slots from the committed
        outcomes, so a restart continues where the stopped run committed (W1B2-3)."""
        problems = self.history_problems(history)
        if problems:
            raise BatchConfigError("the repo's history cannot be trusted: " + "; ".join(problems))
        problems = self.cell_history_problems(history)
        if problems:
            raise BatchConfigError("the repo's history cannot be trusted: " + "; ".join(problems))
        for o in history:
            if o["rerun"] and o["state"] in RERUN_ROUTES:
                self.reruns[(o["half_cell"], o["state"])] += 1
                self.slot_reruns[(o["slot"], o["state"])] += 1
            self._note_committed(o)
        # A restart after a pause launches nothing before the window resets (lane w1b decision).
        self.paused = any(o["state"] == labels4.PAUSE for o in history[-BLOCK:])

    def cell_history_problems(self, history) -> list[str]:
        """The committed cell states agree with the counts (glitch-f3's cap ruling): walking the history in commit
        order, the take that brings a half-cell's rehearsals (or pauses) to the cap carries the cell state, so does
        every later take of that half-cell, no other take does, and none of them is re-run. A restart closes a
        half-cell from its committed state, so a state that disagrees with the counts is refused, never read."""
        p, counts, closed = [], collections.Counter(), set()
        for i, o in enumerate(history):
            cell, state = o["half_cell"], o["state"]
            reaches = False
            if state in CELL_CAPPED_ROUTES:
                counts[(cell, state)] += 1
                reaches = counts[(cell, state)] >= half_cell_cap(self.table, state)
            should = cell in closed or reaches
            carries = o["cell_state"] == labels4.INCOMPLETE_MECHANICAL
            if should and not carries:
                p.append(f"history[{i}]: half-cell {cell!r} has reached a cap, and slot {o['slot']} attempt "
                         f"{o['attempt']} does not carry its cell state")
            elif carries and not should:
                p.append(f"history[{i}]: slot {o['slot']} attempt {o['attempt']} carries a cell state below the "
                         f"caps of half-cell {cell!r}")
            if should and o["rerun"]:
                p.append(f"history[{i}]: slot {o['slot']} attempt {o['attempt']} is re-run in a closed half-cell")
            if should:
                closed.add(cell)
        return p

    def _note_committed(self, o: dict) -> None:
        """What one committed outcome tells the loop about its slot and its half-cell."""
        slot = o["slot"]
        self.slot_cell.setdefault(slot, o["half_cell"])
        self.next_attempt[slot] = max(self.next_attempt.get(slot, 1), o["attempt"] + 1)
        if o["state"] in CELL_CAPPED_ROUTES:
            self.cell_counts[(o["half_cell"], o["state"])] += 1
        if o["cell_state"] == labels4.INCOMPLETE_MECHANICAL:   # closed from the committed record, never memory
            self.closed_cells.setdefault(o["half_cell"], o["cell_reason"])
        if o["final"]:
            self.closed[slot] = f"already final ({o['state']}, attempt {o['attempt']})"

    # ------------------------------------------------------------------------------- the loop
    def row_problems(self, rows: list[dict]) -> list[str]:
        p = []
        for r in rows:
            if not isinstance(r, dict) or not all(k in r for k in ("slot", "half_cell", "model")):
                p.append(f"row {r!r} must name slot, half_cell and model")
            elif r["model"] not in self.table["pin_profiles"]:
                p.append(f"row {r['slot']}: model {r['model']!r} has no pre-registered pin profile")
            elif self.slot_cell.get(r["slot"], r["half_cell"]) != r["half_cell"]:
                p.append(f"row {r['slot']}: committed under half-cell {self.slot_cell[r['slot']]!r}, "
                         f"not {r['half_cell']!r}")
            elif r["half_cell"] in self.closed_cells:
                pass   # a closed half-cell's row: run() drops it unregistered (glitch-f3's cap ruling)
            elif r["slot"] in self.closed:
                p.append(f"row {r['slot']}: the slot is {self.closed[r['slot']]}, never driven again")
        slots = [r.get("slot") for r in rows if isinstance(r, dict)]
        if len(set(slots)) != len(slots):
            p.append("slots repeat")
        return p

    def run(self, rows: list[dict]) -> list[dict]:
        problems = self.row_problems(rows)
        if problems:
            raise BatchConfigError("; ".join(problems))
        queue = collections.deque((dict(r), self.next_attempt.get(r["slot"], 1)) for r in rows)
        while self.stopped is None:
            queue = self._drop_closed(queue)                 # nothing more for a closed half-cell
            if not queue:
                break
            if self.paused:
                if not self._wait_window():
                    return self.outcomes
                self.paused = False
            block = [queue.popleft() for _ in range(min(self.block, len(queue)))]
            if not self._register(block):                    # serial: one commit each
                return self.outcomes
            launched = [(row, attempt) + self._launch(row, attempt) for row, attempt in block]   # ids recorded
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(block)) as pool:
                futures = [pool.submit(self._drive_step, row, attempt, cid, err)
                           for row, attempt, cid, err in launched]
                results = [self._result(f, row, attempt, cid)              # row order
                           for (row, attempt, cid, _), f in zip(launched, futures)]
            requeue = []
            for (row, attempt, _, _), outcome in zip(launched, results):   # serial, row order, all of them
                outcome = self._commit(row, attempt, outcome)
                if outcome["rerun"]:
                    requeue.append((row, attempt + 1))
            queue.extendleft(reversed(requeue))              # same slots, first, in row order
        return self.outcomes

    def _drop_closed(self, queue):
        """The queue without the rows (first drives and re-runs alike) of a half-cell that closed at its rehearsal or
        pause cap: they are never registered, and each is listed in `skipped` (glitch-f3's cap ruling)."""
        kept = collections.deque()
        for row, attempt in queue:
            if row["half_cell"] in self.closed_cells:
                self.skipped.append({"slot": row["slot"], "attempt": attempt, "half_cell": row["half_cell"],
                                     "why": self.closed_cells[row["half_cell"]]})
            else:
                kept.append((row, attempt))
        return kept

    def _wait_window(self) -> bool:
        """Wait for the usage window (THE USAGE WINDOW: wait_reset() returns at once if the window has already reset,
        blocks until it does otherwise, raises on failure); on a failure, stop with why (W1B2-5). True when it
        reset."""
        try:
            self.window.wait_reset()
        except Exception as e:  # noqa: BLE001 - a window failure is a stop, never a sunk loop
            self.stopped = {"slot": None, "attempt": None, "state": labels4.FAILED,
                            "reason": f"wait_reset failed: {type(e).__name__}: {e}"}
            return False
        return True

    def _register(self, block) -> bool:
        """Register the block's rows, one commit each, in row order. If one fails, commit every row
        already registered as `failed`, stop with why, and return False (W1B2-5)."""
        registered = []
        for row, attempt in block:
            try:
                self.repo.register(row, attempt)
            except Exception as e:  # noqa: BLE001 - a register failure is a stop, never a sunk loop
                reason = f"register failed for slot {row['slot']} attempt {attempt}: {type(e).__name__}: {e}"
                if self.stopped is None:
                    self.stopped = {"slot": row["slot"], "attempt": attempt, "state": labels4.FAILED, "reason": reason}
                for r, a in registered:
                    self._commit(r, a, self._outcome(r, a, None, state=labels4.FAILED, reason=reason))
                return False
            registered.append((row, attempt))
        return True

    def _commit(self, row, attempt, outcome) -> dict:
        """Decide the take's fate, seal its mask, commit it: the one road every outcome takes to the repo."""
        outcome.update(self._decide(row, attempt, outcome))   # the fate, before the commit
        self._seal(outcome)
        try:
            self.repo.commit_records(row, attempt, outcome)
        except Exception as e:  # noqa: BLE001
            closed = self.closed_cells.get(row["half_cell"])   # a cell closes only by a committed record
            outcome = dict(outcome, state=labels4.FAILED, reason=f"commit failed: {e}",
                           final=False, rerun=False, stop=f"commit failed: {e}",
                           cell_state=labels4.INCOMPLETE_MECHANICAL if closed else None, cell_reason=closed)
            self._seal(outcome)
            self._stop(row, attempt, outcome)
        else:
            self._note_committed(outcome)
        self.outcomes.append(outcome)
        return outcome

    @staticmethod
    def _seal(outcome) -> None:
        """The mask rule for stopped takes, at the commit (W1B2-2): a take that is blocked or failed is
        masked, fail-closed, whatever its annotations said. (A take whose records could not be read is
        masked fail-closed by `_annotations`, whatever its state.)"""
        if outcome["state"] in labels4.BATCH_STATES:
            outcome["mask"] = True
            if outcome["mask_basis"] == "annotations":
                outcome["mask_basis"] = f"the take is {outcome['state']}: masked fail-closed (annotations read)"

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
        """The take's fate, from its state's handler. In a half-cell that has already closed (a drive of the same
        block, running when it closed), never a re-run, and the cell state is carried (glitch-f3's cap ruling)."""
        cell = row["half_cell"]
        if cell not in self.closed_cells:
            return self.handlers[outcome["state"]](row, attempt, outcome)
        if outcome["state"] in RERUN_ROUTES:
            if outcome["state"] == labels4.PAUSE:
                self.paused = True                       # the window is still spent for every other half-cell
            fate = self._fate(final=True, beyond_cap=True)
        else:
            fate = self.handlers[outcome["state"]](row, attempt, outcome)
        return dict(fate, cell_state=labels4.INCOMPLETE_MECHANICAL, cell_reason=self.closed_cells[cell])

    @staticmethod
    def _fate(final=False, rerun=False, beyond_cap=False, stop=None, cell_state=None, cell_reason=None) -> dict:
        return {"final": final, "rerun": rerun, "beyond_cap": beyond_cap, "stop": stop,
                "cell_state": cell_state, "cell_reason": cell_reason}

    def _final(self, row, attempt, outcome):
        return self._fate(final=True)

    def _within_cap(self, row, route) -> bool:
        cap = self.table["caps"][route]
        per_cell = half_cell_cap(self.table, route)
        per_slot = cap.get("reruns_per_slot")
        if per_cell is not None and self.reruns[(row["half_cell"], route)] >= per_cell:
            return False
        if per_slot is not None and self.slot_reruns[(row["slot"], route)] >= per_slot:
            return False
        self.reruns[(row["half_cell"], route)] += 1
        self.slot_reruns[(row["slot"], route)] += 1
        return True

    def _rerun_within_cap(self, row, attempt, outcome):
        """harness-error: one re-run in the same slot within its per-slot and per-half-cell caps (re-runs granted);
        beyond them the slot is final as harness-error, published in its own column."""
        if self._within_cap(row, outcome["state"]):
            return self._fate(rerun=True)
        return self._fate(final=True, beyond_cap=True)

    def _count_in_cell(self, row, attempt, outcome):
        """glitch-f3's cap ruling (THE CELL CAPS): a rehearsal (or a pause) is re-run in the same slot until its
        half-cell has had routing.json's cap of them, this take counted. The take that brings the count to the cap
        is its slot's last, and it closes the half-cell `incomplete — mechanical`, with why, in its own committed
        record; the loop goes on with the other half-cells."""
        route, cell = outcome["state"], row["half_cell"]
        cap = half_cell_cap(self.table, route)
        count = self.cell_counts[(cell, route)] + 1          # every committed one, and this take
        if count < cap:
            return self._fate(rerun=True)
        return self._fate(final=True, beyond_cap=True, cell_state=labels4.INCOMPLETE_MECHANICAL,
                          cell_reason=f"half-cell {cell!r} has had {count} {route}s and its {route} cap is {cap} "
                                      f"(round 3's unit, glitch-f3's ruling): nothing more is registered for it")

    def _pause(self, row, attempt, outcome):
        self.paused = True   # no new drive until the usage window resets, whatever the count
        return self._count_in_cell(row, attempt, outcome)

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
