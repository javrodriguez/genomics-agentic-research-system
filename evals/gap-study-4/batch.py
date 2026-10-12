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
refused the records, or the driver's pin is not the registered row's) and `failed` (a register,
launch or drive failed, routing raised, or a commit failed). The handlers are keyed by
`labels4.TERMINAL_STATES`; a state with no handler stops the loop from starting. A container that
could not be removed is no terminal state of its own: the take keeps its route and fate (A LEAK).

  graded, aborted  final for the slot (aborted is never re-run)
  rehearsal        re-run in the same slot until its half-cell has had its cap of rehearsals; then
                   the half-cell closes (THE CELL CAPS)
  harness-error    one re-run in the same slot, within the half-cell's cap; beyond it the slot is
                   final as harness-error (published in its own column, out of the denominator)
  pause            re-run in the same slot until its half-cell has had its cap of pauses, then the
                   half-cell closes (THE CELL CAPS); either way NO NEW DRIVE is launched until the
                   usage window resets (THE USAGE WINDOW); drives already running finish and are
                   routed as usual
  blocked, failed  the loop stops launching; the rest of the queue stays unstarted for a human. A
                   restart never drives such a slot again without a committed ruling (THE RULINGS),
                   except a `failed` take where nothing ran (a register or launch failure)

THE CELL CAPS (glitch-f3's ruling, in-plan, 6 Oct 2026; recorded as glitch-f3's, not the owner's).
Rehearsals and pauses are counted per half-cell, round 3's unit. Round 3 counted the rehearsals (or
the pauses) of a cell, (task, half, model), and once the count reached the cap registered nothing
more for it, which published `incomplete — mechanical` (evals/gap-study-3/takes.py:280-291 at
e2979b31). Round 4's half-cell is (arm, task, half, model), the registered row's `half_cell`, with
wording and repeat or pressure as the slot inside it; the loop keys its counts by that value and
never reads inside it. What is counted is a half-cell's events of that route (`cell_event`): each
committed rehearsal is its own event; the pauses count by USAGE-WINDOW EVENT, so the pauses that
share one reset count once (glitch-f3's ruling on review round 3, W1B3-5, in-plan, 6 Oct 2026;
glitch-f3's, not the owner's). The cap bounds window events, round 3's own unit: round 3 drove one
take at a time, so each of its pauses was its own window event, while this loop drives a block of
up to three and every pause of one block shares the one reset it waits for before the next block.
Each committed pause carries that event as `window_event`. The take whose event brings the count to
routing.json's cap is its slot's last (final, never re-run, beyond_cap), and it is committed with
`cell_state` = labels4.INCOMPLETE_MECHANICAL and a `cell_reason` before the loop moves on. From then on nothing more is registered for the half-cell:
its queued rows and re-runs are dropped, each listed in `skipped`. The loop goes on with the other
half-cells; it never stops for a human here. A drive of the same block that was already running
when its half-cell closed is committed as usual, never re-run, and carries the cell state too.
Harness-error's own caps and its beyond-cap fate are unchanged.

WHAT IS COMMITTED. `repo.commit_records(row, attempt, outcome)` receives one outcome per take,
with every key below always present (None where it does not apply), decided BEFORE the commit:

    slot, half_cell, attempt     the registered row and its attempt
    container_id                 the id recorded at launch (None if the driver named none)
    state                        a labels4 terminal state
    reason                       why, for blocked and failed; and why a container leaked (else None)
    decision                     routing.route's return (None when the take was not routed)
    records                      the harness-side records the driver returned (None if none)
    events                       routing.annotate's events, or None when the records could not
                                 be read (then nothing can be counted, and a human must look)
    mask                         True when the take's text must be masked, never deleted, before
                                 this commit writes it. Decided on every take from the annotations;
                                 True, fail-closed, whenever the records could not be read and on
                                 every blocked or failed take (review round 2, W1B2-2)
    mask_basis                   "annotations" or why the mask was set fail-closed
    leaked_container             the recorded id of a container remove() failed on (else None): the
                                 take keeps its route and fate, and the loop stops (A LEAK)
    leaked_containers            every recorded container id still listed after that removal (the take,
                                 its sidecar, its proxy), from the exception's `leaked_ids`, else
                                 [leaked_container]; None when nothing leaked. A restart refuses while
                                 any of them is listed (ruling S6-gap4-2, glitch-1b, 11 Oct 2026)
    final                        True when this record is the slot's final result
    rerun                        True when the slot is re-run (same slot, next attempt)
    beyond_cap                   True when a cap was reached
    stop                         why the loop stops after this block (else None)
    cell_state                   labels4.INCOMPLETE_MECHANICAL once the take's half-cell has closed at
                                 its rehearsal or pause cap, by this take or an earlier one (else None)
    cell_reason                  why the half-cell closed: its count and cap (else None)
    drive_started                False only when the take never reached its drive (its register or
                                 its launch failed); True once driver.drive() was called, and
                                 fail-closed True when the loop cannot tell (the drive step raised).
                                 A `failed` take whose drive started needs a ruling (THE RULINGS)
    window_event                 for a pause, the usage-window event it belongs to (an int, rising in
                                 commit order, shared by every pause of one block); else None

The repo masks the take's text whenever `mask` is true; it never deletes it. The mask rule is
applied at the one place every outcome passes before its commit (`_seal`), so no road to a commit
can skip it.

A LEAK (review round 3, W1B3-1; glitch-f3 accepted the gap4 lane lead's fix as written, 6 Oct 2026;
glitch-f3's, not the owner's). When remove() fails, the take keeps its routed state and its fate
(a graded take stays graded and final, a rehearsal keeps its re-run); `leaked_container` names the
recorded id, `reason` says why, the routed decision is committed, and the loop stops after the
block, the stop committed with the record. A leak never turns a take into `failed`.

THE RULINGS (W1B3-1, the same ruling). "Refused, never defaulted"; "no try is ever discarded or re-run
for something the agent did"; round 3: "there are no retakes" (evals/gap-study-3/takes.py:260 at
e2979b31). So a restart refuses (`BatchConfigError`, naming the slot and the attempt) a row whose
slot's last committed take is `blocked`, or `failed` after its drive started (`needs_ruling`), until
the repo's history holds an explicit ruling for that (slot, attempt): a record of kind
labels4.RULING with exactly RULING_KEYS,

    kind     labels4.RULING
    slot, attempt   the stopped take it rules on (committed before it, and needing a ruling)
    ruling   labels4.RULE_RERUN: the slot is driven once more, at the next attempt, outside every cap;
             labels4.RULE_ROUTE: the take gets `route`'s fate, decided on the restart by that route's
             own handler at the ruling's place in the history (graded or aborted: the slot is
             final; harness-error: a re-run within its caps; rehearsal or pause: counted in the
             half-cell, as its own event, and re-run until the cap closes it; a pause also holds
             the next launch for the usage window)
    route    a labels4 route for RULE_ROUTE, None for RULE_RERUN
    by       who ruled (a non-empty string), never inferred

One ruling per take; a ruling is spent by the drive it allows, so a later stopped take of the slot
needs its own. The loop reads rulings and never writes one (its repo interface has no road for it).
A `failed` take where nothing ran (drive_started false: a register failure, or a launch failure
with no records) is still re-driven automatically, with no ruling.

A RESTART CONTINUES, never resets (review round 2, W1B2-3). The caps and attempt numbers live in
the committed outcomes, not in this process: `Batch` reads them from the repo (`repo.history()`,
every outcome and ruling committed so far, in commit order; or a `history` argument read from it, which is
refused when it differs from `repo.history()`, naming the first difference, W1B4-6 (i))
and rebuilds, before anything runs, walking it in order, the re-runs spent per half-cell and per
slot, the rehearsal and pause events counted per half-cell, the closed half-cells (from their
committed cell state, or from a ruling whose event reaches a cap), the last window event, each
slot's next attempt (one past its last committed attempt), and what each slot is owed. It never
registers a row of a closed half-cell (each is listed in `skipped`, and the other rows run),
refuses a row whose slot is already final, refuses a row whose slot's last take awaits a ruling
(THE RULINGS), refuses rows that leave out a slot the history still owes a drive (a re-run, a ruled
re-run, or a failed take where nothing ran) in an open half-cell (review round 3, W1B3-6), and
refuses a history it cannot trust (not a list, a missing key, an unknown state or cell state, a
cell state without its reason, a (slot, attempt) twice, a slot under two half-cells, an attempt
after the slot's final one, a drive_started that is not a bool or is false beside records, a
window event on no pause or none on a pause or one reopened, a ruling that is not closed or rules
on a take never committed, committed after it, needing none, or twice, a stopped slot driven again
with no ruling, or a cell state that disagrees with the counts: the take that brings a half-cell to
a cap carries it, so does every later take of that half-cell, no other take does, and none of them
is re-run). Lane w1b decision (`restart_waits`): when a pause, committed or ruled, is among the last
BLOCK committed outcomes or the rulings committed among or after them, a restart waits for the usage
window before its first launch.

THE START GATE. The loop refuses to start (`BatchConfigError`, and `batch.py --check` exits 1)
while routing.json still lacks what only the owner or a later checkpoint can supply: round 3's
pause cap, round 3's operator-side reasons (an empty list, or a status not ruled), the rate-limit
markers' ruling (W1B2-6), the spend-cap lists' ruling (Claude Code's list is open, ruling 3 of
17:42), or the pre-registered pin profiles (CP5). A status is ruled only when, stripped and
upper-cased, it starts with RULED or FILLED and holds no PENDING anywhere (`is_pending`; lane
review round 2, W4H2-1); every other status keeps the loop from starting. Every row must name its agent ({harness, version}: interface 8, never defaulted)
and a model that has a profile under that harness, and its agent's version must be that profile's
(a row that fails any of these is refused before it is registered).

THE MONEY GATE (lane w7c, ruling W7C-gap4-1, glitch-1b under Javier's standing delegation, 12 Oct 2026). The
round's two money checks, costs.month_turn_allowed (the month-turn hold: no OpenAI or Google take from 23:30 UTC on a
month's last day until Javier's "caps trimmed" is recorded) and costs.walk_gate (spend since the round began, plus
what the remaining tries project, against the $260 / $140 / $400 caps), are called by the loop itself, never left to
a driver. Before each block is registered, every row of the block whose harness bills money per call (any harness
but routing.NO_MONEY_HARNESSES; routing.PAID_HARNESSES names each one's arm) is put through both, on one reading of
the spend ledger (`ledger.read()`, exactly LEDGER_KEYS: now, walks, spend, start, trimmed). The hold reads the
loop's OWN clock (`clock()`, aware UTC, read at check time; injectable for tests), never the ledger's `now`, which
may be recorded but never decides the hold (glitch-1b's ruling on Q-w7c-1, 12 Oct 2026). When either refuses, or
the ledger cannot be read or is not that shape, or the harness has no arm, nothing of the block is registered or
launched: the loop stops (`stopped`, state blocked) with the named reason, for Javier's word, and the frozen order is
kept (the block's Claude rows wait too). Nothing is committed, so a restart puts the block through the gate again. A
row of a harness that bills money, handed to a loop given no ledger, is refused before anything runs. Rows of
claude-code (arms A and C, a subscription login that bills no money per call) never read the ledger and never call
either check. The ledger is CP2's (the vendor spend reads and the recorded trim); none is built here.

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
                                     `pin` must be the registered row's harness, model and that
                                     model's pre-registered profile under that harness, or the take
                                     is blocked (the driver is never trusted for the pin)
    remove(container_id) -> None     remove exactly that container (never called with None)

and a repo object with `register(row, attempt)` and `commit_records(row, attempt, outcome)`, each
one commit, and `history()` (the committed outcomes and rulings), and a usage window with
`wait_reset()`, and (for arms O and G only) a spend ledger with `read()` (THE MONEY GATE). CP2 supplies the real
four; CP5's tooling commits the rulings a human makes.

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
import datetime
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
                "events", "mask", "mask_basis", "leaked_container", "leaked_containers", "final", "rerun",
                "beyond_cap", "stop",
                "cell_state", "cell_reason", "drive_started", "window_event")
# Every key of a committed ruling (THE RULINGS, W1B3-1): a closed record, told from an outcome by its kind.
RULING_KEYS = ("kind", "slot", "attempt", "ruling", "route", "by")


# Interface 8 (w1b's next-touch item 5): a registered row's agent, {"harness": AgentAdapter.name, "version":
# AgentAdapter.version()}, required beside its model and never defaulted.
AGENT_KEYS = ("harness", "version")

# Routes that re-run a slot, whose spent re-runs a restart must count again.
RERUN_ROUTES = (labels4.REHEARSAL, labels4.HARNESS_ERROR, labels4.PAUSE)
# Routes counted per half-cell, round 3's unit, whose cap closes the half-cell (glitch-f3's ruling, THE CELL CAPS).
CELL_CAPPED_ROUTES = (labels4.REHEARSAL, labels4.PAUSE)


def is_ruling(entry) -> bool:
    """A history entry that is a ruling (THE RULINGS), never an outcome: told by its kind alone."""
    return isinstance(entry, dict) and entry.get("kind") == labels4.RULING


def needs_ruling(outcome: dict) -> bool:
    """W1B3-1: the take stopped the loop on something a human must rule on before its slot goes on: it is blocked,
    or it failed after its drive started (the agent may have acted). A failed take where nothing ran needs none."""
    return outcome["state"] == labels4.BLOCKED or (outcome["state"] == labels4.FAILED and outcome["drive_started"] is not False)


def cell_event(outcome: dict) -> tuple:
    """The event a rehearsal or a pause is in its half-cell's count (THE CELL CAPS): each rehearsal is its own; every
    pause of one usage-window event is one, since the pauses that share one reset count once (W1B3-5, glitch-f3's
    ruling). A take a ruling routes (it carries no window event) is its own event."""
    if outcome["state"] == labels4.PAUSE and outcome.get("window_event") is not None:
        return ("window", outcome["window_event"])
    return ("take", outcome["slot"], outcome["attempt"])


def effective_route(entry: dict):
    """What a history entry counts as for the usage window: an outcome's state, or a route ruling's route."""
    if is_ruling(entry):
        return entry["route"] if entry["ruling"] == labels4.RULE_ROUTE else None
    return entry["state"]


def restart_waits(history: list) -> bool:
    """Lane w1b decision 11, bound by W1B3-3: a restart waits for the usage window when a pause, committed or ruled, is
    among the last BLOCK committed outcomes (a block's worth: a pause first in it or in its middle counts) or the
    rulings committed among or after them."""
    at = [i for i, e in enumerate(history) if not is_ruling(e)][-BLOCK:]
    tail = history[at[0]:] if at else history
    return any(effective_route(e) == labels4.PAUSE for e in tail)


def history_difference(given, held):
    """W1B4-6 (i): where a `history` argument first differs from the repo's own `history()`, or None when they agree:
    the first entry that differs (and its first differing key, when both are records), or the first entry one of
    them lacks."""
    if not isinstance(given, list) or not isinstance(held, list):
        return None if given == held else f"the argument is {type(given).__name__}, repo.history() {type(held).__name__}"
    for i, (a, b) in enumerate(zip(given, held)):
        if a != b:
            if isinstance(a, dict) and isinstance(b, dict):
                keys = sorted((k for k in set(a) | set(b) if a.get(k, a) != b.get(k, b)), key=str)
                return f"history[{i}] differs first at key {keys[0]!r}"
            return f"history[{i}] differs"
    if len(given) != len(held):
        n = min(len(given), len(held))
        more = "the argument" if len(given) > len(held) else "repo.history()"
        return f"history[{n}] is held by {more} only ({len(given)} entries given, {len(held)} in repo.history())"
    return None


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


# The words a ruled status starts with (lane review round 2, W4H2-1, the lane lead's decision): an allow-list.
RULED_WORDS = ("RULED", "FILLED")


def is_pending(status) -> bool:
    """True unless the status is ruled. A status is ruled only when, stripped and upper-cased, it starts with one of
    RULED_WORDS and holds no PENDING anywhere (lane review round 2, W4H2-1, the lane lead's decision). Everything else
    is pending: "PENDING (x)", "pending", a zero-width space before PENDING, "Status: PENDING", "RULED for codex;
    PENDING for claude-code", "TBD", "not yet ruled". All four start_problems status lines read a status this way
    (glitch-f3's ruling on W4H1-1, under Javier's delegation, relayed by the lane lead)."""
    s = str(status).strip().upper()
    return not (s.startswith(RULED_WORDS) and PENDING not in s)


def start_problems(table: dict) -> list[str]:
    """Everything that keeps the loop from starting on this table (empty when it may start)."""
    p = [f"cap {r} is still pending in routing.json" for r in pending_caps(table)]
    if not table.get("operator_reasons"):
        p.append("operator_reasons is empty in routing.json (round 3's operator-side reasons)")
    if is_pending(table.get("operator_reasons_status", PENDING)):
        p.append("operator_reasons_status is not ruled in routing.json (RULED or FILLED, with no PENDING)")
    if not table.get("pin_profiles"):
        p.append("pin_profiles is empty in routing.json (CP5 pre-registers them)")
    if is_pending(table.get("pin_profiles_status", PENDING)):
        p.append("pin_profiles_status is not ruled in routing.json (RULED or FILLED, with no PENDING)")
    if is_pending(table.get("rate_limit_markers_status", PENDING)):
        p.append("rate_limit_markers_status is not ruled in routing.json (RULED or FILLED, with no PENDING)")
    if is_pending(table.get("spend_cap_markers_status", PENDING)):
        # item 1 (ruling 3 of 17:42): an unruled spend-cap list never lets the loop start
        p.append("spend_cap_markers_status is not ruled in routing.json (RULED or FILLED, with no PENDING): a spend "
                 "cap stops for a human ruling")
    return p


def expected_pin(row: dict, table: dict) -> dict:
    """The pin a take of this registered row must run under: its harness (the row's agent), its model, and that
    model's profile under that harness (interface 8: pin_profiles is keyed by harness, then model)."""
    harness = row["agent"]["harness"]
    return dict(table["pin_profiles"][harness][row["model"]], model=row["model"], harness=harness)


def agent_problems(row: dict) -> list[str]:
    """Interface 8: the row's agent is exactly {harness, version}, non-empty strings, never defaulted."""
    agent = row.get("agent")
    if (not isinstance(agent, dict) or set(agent) != set(AGENT_KEYS)
            or not all(isinstance(agent[k], str) and agent[k] for k in AGENT_KEYS)):
        return [f"row {row.get('slot')}: agent must be exactly {list(AGENT_KEYS)} as non-empty strings (interface 8; "
                f"never defaulted), got {agent!r}"]
    return []


def version_problems(row: dict, table: dict) -> list[str]:
    """Interface 8 (item 5): a row whose agent.version is not its pin's version cannot run under its pin. Lane w4h's
    decision: it is refused before it is registered (nothing is driven), never driven and then blocked."""
    want = expected_pin(row, table)["version"]
    if row["agent"]["version"] != want:
        return [f"row {row['slot']}: agent version {row['agent']['version']!r} is not its pin's version {want!r}"]
    return []


# THE MONEY GATE (W7C, ruling W7C-gap4-1): one reading of the spend ledger, a closed key set.
LEDGER_KEYS = ("now", "walks", "spend", "start", "trimmed")


def bills_money(row: dict) -> bool:
    """W7C: a row whose harness bills money per call: every harness but routing's no-money one (claude-code)."""
    return row["agent"]["harness"] not in routing.NO_MONEY_HARNESSES


def utc_now() -> datetime.datetime:
    """W7C (Q-w7c-1): the loop's own clock, aware UTC."""
    return datetime.datetime.now(datetime.timezone.utc)


def money_gate_problems(rows: list[dict], ledger, clock=utc_now) -> list[str]:
    """W7C (THE MONEY GATE): why these rows may not be launched now (empty when they may). Rows that bill no money are
    never put through it: with none that bills money the ledger is not read and neither check is called. Otherwise one
    reading of the ledger feeds costs.month_turn_allowed, per row with its harness's arm and the loop's own clock
    (`clock()`, read once here; never the ledger's `now`, Q-w7c-1), and costs.walk_gate, once;
    anything but an explicit allow from each, or a ledger that cannot be read or is not exactly LEDGER_KEYS, refuses."""
    paid = [r for r in rows if bills_money(r)]
    if not paid:
        return []
    if ledger is None:
        return [f"the loop was given no spend ledger, and slot {paid[0]['slot']}'s harness "
                f"{paid[0]['agent']['harness']!r} bills money per call"]
    import costs   # costs imports this module: read at call time, never at import
    try:
        snap = ledger.read()
    except Exception as e:  # noqa: BLE001 - an unreadable ledger refuses, never lets a paid take run
        return [f"the spend ledger could not be read: {type(e).__name__}: {e}"]
    if not isinstance(snap, dict) or set(snap) != set(LEDGER_KEYS):
        got = sorted(snap) if isinstance(snap, dict) else type(snap).__name__
        return [f"the spend ledger's reading is not exactly {list(LEDGER_KEYS)}: {got}"]
    try:
        now = clock()
    except Exception as e:  # noqa: BLE001 - a clock that cannot be read refuses
        now = f"<clock unreadable: {type(e).__name__}: {e}>"
    p = []
    for r in paid:
        harness = r["agent"]["harness"]
        arm = routing.PAID_HARNESSES.get(harness, {}).get("arm")
        if arm is None:
            p.append(f"slot {r['slot']}: harness {harness!r} bills money and has no arm in routing.PAID_HARNESSES")
            continue
        try:
            allowed = costs.month_turn_allowed(arm, now, snap["trimmed"])
        except Exception as e:  # noqa: BLE001 - a clock or trim the hold cannot read refuses
            allowed = f"{type(e).__name__}: {e}"
        if allowed is not True:
            p.append(f"slot {r['slot']}: arm {arm} ({harness}): the month-turn hold refuses at {now!r} (the loop's clock) "
                     f"(costs.month_turn_allowed: {allowed}): no OpenAI or Google take until Javier's 'caps trimmed' "
                     f"is recorded")
    try:
        gate = costs.walk_gate(snap["walks"], snap["spend"], snap["start"])
    except Exception as e:  # noqa: BLE001 - inputs the gate refuses refuse the takes
        return p + [f"the walk gate refused its inputs: {type(e).__name__}: {e}"]
    if not isinstance(gate, dict):
        return p + [f"the walk gate returned no decision: {gate!r}"]
    if gate.get("decision") != costs.PROCEED:
        p.append(f"the walk gate says {gate.get('decision')!r}, not {costs.PROCEED!r} (spent and projected against "
                 f"the round caps: {gate.get('projected')})")
    return p


class Batch:
    def __init__(self, driver, repo, window, *, table: dict | None = None, serial: bool = False,
                 route_fn=None, annotate_fn=None, history: list | None = None, ledger=None,
                 clock=utc_now):
        self.driver, self.repo, self.window = driver, repo, window
        self.ledger = ledger                 # W7C: the spend ledger (THE MONEY GATE), read before each paid block
        self.clock = clock                   # W7C (Q-w7c-1): the loop's own UTC clock, the one the hold reads
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
        self.cell_events = collections.defaultdict(set)   # (half_cell, route) -> its committed events (cell_event)
        self.closed_cells: dict = {}         # half_cell -> why nothing more is registered for it (as committed)
        self.skipped: list = []              # rows of a closed half-cell, dropped unregistered
        self.stopped = None
        self.paused = False
        self.last_window_event = 0           # the highest window event committed (W1B3-5)
        self._block_event = None             # the window event of the block being committed, once one paused
        self.ruled: dict = {}                # (slot, attempt) -> (the ruling, its fate), from the history (W1B3-1)
        self.unruled: dict = {}              # slot -> (attempt, why): its last take awaits a ruling (W1B3-1)
        self.owed: dict = {}                 # slot -> (attempt, why): the history owes it this drive (W1B3-6)
        read = getattr(repo, "history", None)
        if history is None:
            if not callable(read):
                raise BatchConfigError("the repo gives no history(): the caps and attempts of earlier runs "
                                       "cannot be rebuilt, so a restart could spend re-runs twice")
            history = read()
        elif callable(read):
            # W1B4-6 (i): a history argument is only ever the repo's own; one that differs is refused, never trusted
            # over the committed record. A repo without history() (a test double) may still be handed one.
            diff = history_difference(history, read())
            if diff is not None:
                raise BatchConfigError(f"the history argument differs from repo.history(): {diff}")
        self._replay(history)

    # ---------------------------------------------------------------------------- the history
    @classmethod
    def history_problems(cls, history) -> list[str]:
        """Why the committed outcomes and rulings cannot be trusted (empty when they can)."""
        if not isinstance(history, list):
            return ["history must be a list of committed outcomes"]
        p, seen, cell, final_at = [], {}, {}, {}
        pending, ruled = {}, set()          # slot -> (attempt, state) of its take awaiting a ruling; ruled takes
        last_event, event_slots = 0, collections.defaultdict(set)
        for i, o in enumerate(history):
            if is_ruling(o):
                p += cls._ruling_problems(i, o, seen, ruled, pending)
                continue
            if not isinstance(o, dict) or set(o) != set(OUTCOME_KEYS):
                p.append(f"history[{i}] must hold exactly the committed outcome keys")
                continue
            if o["state"] not in labels4.TERMINAL_STATES:
                p.append(f"history[{i}]: state {o['state']!r} is not a labels4 terminal state")
            if not (isinstance(o["attempt"], int) and not isinstance(o["attempt"], bool) and o["attempt"] >= 1):
                p.append(f"history[{i}]: attempt {o['attempt']!r} is not a positive int")
                continue
            if not all(isinstance(o[k], bool) for k in ("final", "rerun", "beyond_cap", "drive_started")):
                p.append(f"history[{i}]: final, rerun, beyond_cap and drive_started must be bools")
            elif not o["drive_started"] and (o["records"] is not None or o["decision"] is not None):
                p.append(f"history[{i}]: drive_started is false, but its records or decision show the drive ran")
            we = o["window_event"]
            if o["state"] == labels4.PAUSE:
                if not (isinstance(we, int) and not isinstance(we, bool) and we >= 1):
                    p.append(f"history[{i}]: a pause carries its window_event, a positive int, not {we!r}")
                elif we < last_event:
                    p.append(f"history[{i}]: window event {we} reopened after window event {last_event}")
                elif o["slot"] in event_slots[we]:
                    p.append(f"history[{i}]: slot {o['slot']} paused twice in window event {we}")
                else:
                    last_event = we
                    event_slots[we].add(o["slot"])
            elif we is not None:
                p.append(f"history[{i}]: a {o['state']} take carries window_event {we!r}; only a pause does")
            if o["cell_state"] is not None and o["cell_state"] not in labels4.CELL_STATES:
                p.append(f"history[{i}]: cell state {o['cell_state']!r} is not a labels4 cell state")
            elif (o["cell_state"] is None) != (o["cell_reason"] is None) or not (
                    o["cell_reason"] is None or (isinstance(o["cell_reason"], str) and o["cell_reason"])):
                p.append(f"history[{i}]: a cell state comes with its reason, and a reason with its state")
            key = (o["slot"], o["attempt"])
            if key in seen:
                p.append(f"history[{i}]: slot {o['slot']} attempt {o['attempt']} committed twice")
            if cell.setdefault(o["slot"], o["half_cell"]) != o["half_cell"]:
                p.append(f"history[{i}]: slot {o['slot']} committed under two half-cells")
            waiting = pending.get(o["slot"])
            if waiting and o["attempt"] > waiting[0]:
                p.append(f"history[{i}]: slot {o['slot']} attempt {o['attempt']} was driven after attempt {waiting[0]} "
                         f"ended {waiting[1]}, with no ruling for it (W1B3-1)")
            seen.setdefault(key, o)
            if o["state"] in labels4.TERMINAL_STATES and isinstance(o["drive_started"], bool) and needs_ruling(o):
                pending[o["slot"]] = (o["attempt"], o["state"])
        for i, o in enumerate(history):   # an attempt after the slot's final one
            if isinstance(o, dict) and not is_ruling(o) and o.get("final") is True and isinstance(o.get("attempt"), int):
                final_at[o.get("slot")] = min(final_at.get(o.get("slot"), o["attempt"]), o["attempt"])
        for i, o in enumerate(history):
            if (isinstance(o, dict) and not is_ruling(o) and o.get("slot") in final_at
                    and isinstance(o.get("attempt"), int) and o["attempt"] > final_at[o["slot"]]):
                p.append(f"history[{i}]: slot {o['slot']} attempt {o['attempt']} comes after its final attempt")
        return p

    @staticmethod
    def _ruling_problems(i, r, seen, ruled, pending) -> list[str]:
        """A ruling is closed (THE RULINGS), and rules on a take committed before it that needs one, once."""
        if set(r) != set(RULING_KEYS):
            return [f"history[{i}]: a ruling must hold exactly the ruling keys {list(RULING_KEYS)}"]
        p = []
        if not (isinstance(r["attempt"], int) and not isinstance(r["attempt"], bool) and r["attempt"] >= 1):
            p.append(f"history[{i}]: a ruling's attempt {r['attempt']!r} is not a positive int")
        if r["ruling"] not in labels4.RULINGS:
            p.append(f"history[{i}]: ruling {r['ruling']!r} is not a labels4 ruling {list(labels4.RULINGS)}")
        elif r["ruling"] == labels4.RULE_RERUN and r["route"] is not None:
            p.append(f"history[{i}]: a {labels4.RULE_RERUN} ruling names no route, got {r['route']!r}")
        elif r["ruling"] == labels4.RULE_ROUTE and r["route"] not in labels4.ROUTES:
            p.append(f"history[{i}]: a {labels4.RULE_ROUTE} ruling names a labels4 route, got {r['route']!r}")
        if not (isinstance(r["by"], str) and r["by"].strip()):
            p.append(f"history[{i}]: a ruling names who made it (`by`), got {r['by']!r}")
        key = (r["slot"], r["attempt"])
        taken = seen.get(key) if not isinstance(r["slot"], (list, dict, set)) else None
        if taken is None:
            p.append(f"history[{i}]: a ruling for slot {r['slot']} attempt {r['attempt']}, which no earlier outcome "
                     f"commits")
        elif not (isinstance(taken["drive_started"], bool) and needs_ruling(taken)):
            p.append(f"history[{i}]: slot {r['slot']} attempt {r['attempt']} is {taken['state']} and needs no ruling")
        elif key in ruled:
            p.append(f"history[{i}]: slot {r['slot']} attempt {r['attempt']} ruled twice")
        else:
            ruled.add(key)
            if pending.get(r["slot"], (None,))[0] == r["attempt"]:
                del pending[r["slot"]]
        return p

    def _replay(self, history) -> None:
        """Rebuild the re-runs spent, the half-cells' events, each slot's next attempt, the closed slots and half-cells,
        and what each slot is owed or awaits, from the committed outcomes and rulings, walked in commit order, so a
        restart continues where the stopped run committed (W1B2-3, W1B3-1, W1B3-5, W1B3-6)."""
        problems = self.history_problems(history)
        if problems:
            raise BatchConfigError("the repo's history cannot be trusted: " + "; ".join(problems))
        problems = self.cell_history_problems(history)
        if problems:
            raise BatchConfigError("the repo's history cannot be trusted: " + "; ".join(problems))
        outcome_at, last, ruled_final = {}, {}, {}
        for i, o in enumerate(history):
            if is_ruling(o):
                fate = self._apply_ruling(o, outcome_at[(o["slot"], o["attempt"])])
                if fate["final"]:
                    ruled_final[o["slot"]] = self.closed[o["slot"]]
                continue
            if o["slot"] in ruled_final:   # after a ruled final (after an outcome's final, history_problems refuses it)
                problems.append(f"history[{i}]: slot {o['slot']} attempt {o['attempt']} comes after its final attempt "
                                f"({ruled_final[o['slot']]})")
            if o["rerun"] and o["state"] in RERUN_ROUTES:
                self.reruns[(o["half_cell"], o["state"])] += 1
                self.slot_reruns[(o["slot"], o["state"])] += 1
            self._note_committed(o)
            outcome_at[(o["slot"], o["attempt"])] = o
            if o["attempt"] >= last.get(o["slot"], {"attempt": 0})["attempt"]:
                last[o["slot"]] = o
            self.last_window_event = max(self.last_window_event, o["window_event"] or 0)
        if problems:
            raise BatchConfigError("the repo's history cannot be trusted: " + "; ".join(problems))
        for slot, o in last.items():                         # what each slot's last committed take leaves it
            if o["half_cell"] in self.closed_cells or slot in self.closed:
                continue                                     # nothing more for it
            nxt, key = o["attempt"] + 1, (slot, o["attempt"])
            if needs_ruling(o):
                if key not in self.ruled:
                    why = "was blocked" if o["state"] == labels4.BLOCKED else "failed after its drive started"
                    self.unruled[slot] = (o["attempt"], why)
                elif self.ruled[key][1]["rerun"]:
                    r = self.ruled[key][0]
                    self.owed[slot] = (nxt, f"{r['ruling']}{' ' + r['route'] if r['route'] else ''}, ruled by {r['by']}")
            elif o["rerun"]:
                self.owed[slot] = (nxt, f"its {o['state']} is re-run")
            elif o["state"] == labels4.FAILED:
                self.owed[slot] = (nxt, "it failed before its drive started, and is re-driven")
        self.paused = restart_waits(history)

    def _apply_ruling(self, r: dict, o: dict) -> dict:
        """W1B3-1: a ruling's fate for the take it rules on, decided at its place in the history. `re-run`: the slot is
        driven once more, outside every cap. `route`: the route's own handler decides, as the loop would have, and a
        rehearsal or pause counts in its half-cell as its own event (a rehearsal, or pause, that reaches the cap closes
        it, the ruling being its committed record)."""
        row = {"slot": o["slot"], "half_cell": o["half_cell"]}
        if r["ruling"] == labels4.RULE_RERUN:
            fate = self._fate(rerun=True)
        else:
            routed = dict(o, state=r["route"], window_event=None)
            fate = self._decide(row, o["attempt"], routed)
            if r["route"] in CELL_CAPPED_ROUTES:
                self.cell_events[(o["half_cell"], r["route"])].add(cell_event(routed))
            if fate["cell_state"] is not None:
                self.closed_cells.setdefault(o["half_cell"], f"{fate['cell_reason']} (its last event ruled "
                                                             f"{r['route']} by {r['by']}, slot {o['slot']} "
                                                             f"attempt {o['attempt']})")
        self.ruled[(o["slot"], o["attempt"])] = (r, fate)
        if fate["final"]:
            self.closed[o["slot"]] = f"ruled final ({r['route']} by {r['by']}, attempt {o['attempt']})"
        return fate

    def cell_history_problems(self, history) -> list[str]:
        """The committed cell states agree with the counts (glitch-f3's cap ruling): walking the history in commit
        order, the take that brings a half-cell's rehearsal (or pause) events to the cap carries the cell state, so
        does every later take of that half-cell, no other take does, and none of them is re-run. A pause counts by
        its window event (W1B3-5); a take a ruling routes rehearsal or pause counts as its own event at the ruling's
        place (W1B3-1). A restart closes a half-cell from its committed state, so a state that disagrees with the
        counts is refused, never read."""
        p, events, closed, outcome_at = [], collections.defaultdict(set), set(), {}
        for i, o in enumerate(history):
            if is_ruling(o):
                taken = outcome_at.get((o["slot"], o["attempt"]))
                if taken is not None and o["ruling"] == labels4.RULE_ROUTE and o["route"] in CELL_CAPPED_ROUTES:
                    routed = dict(taken, state=o["route"], window_event=None)
                    events[(taken["half_cell"], o["route"])].add(cell_event(routed))
                    if len(events[(taken["half_cell"], o["route"])]) >= half_cell_cap(self.table, o["route"]):
                        closed.add(taken["half_cell"])
                continue
            outcome_at[(o["slot"], o["attempt"])] = o
            cell, state = o["half_cell"], o["state"]
            reaches = False
            if state in CELL_CAPPED_ROUTES:
                events[(cell, state)].add(cell_event(o))
                reaches = len(events[(cell, state)]) >= half_cell_cap(self.table, state)
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
            self.cell_events[(o["half_cell"], o["state"])].add(cell_event(o))
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
            elif agent_problems(r):
                p += agent_problems(r)
            elif r["model"] not in self.table["pin_profiles"].get(r["agent"]["harness"], {}):
                p.append(f"row {r['slot']}: model {r['model']!r} has no pre-registered pin profile under harness "
                         f"{r['agent']['harness']!r}")
            elif version_problems(r, self.table):
                p += version_problems(r, self.table)
            elif bills_money(r) and self.ledger is None:
                p.append(f"row {r['slot']}: harness {r['agent']['harness']!r} bills money per call, and the loop was "
                         f"given no spend ledger: refused before anything runs (W7C, THE MONEY GATE)")
            elif self.slot_cell.get(r["slot"], r["half_cell"]) != r["half_cell"]:
                p.append(f"row {r['slot']}: committed under half-cell {self.slot_cell[r['slot']]!r}, "
                         f"not {r['half_cell']!r}")
            elif r["half_cell"] in self.closed_cells:
                pass   # a closed half-cell's row: run() drops it unregistered (glitch-f3's cap ruling)
            elif r["slot"] in self.closed:
                p.append(f"row {r['slot']}: the slot is {self.closed[r['slot']]}, never driven again")
            elif r["slot"] in self.unruled:      # W1B3-1: refused, never defaulted
                attempt, why = self.unruled[r["slot"]]
                p.append(f"row {r['slot']}: slot {r['slot']} attempt {attempt} {why}, and the repo holds no ruling "
                         f"for it ({labels4.RULE_RERUN}, or {labels4.RULE_ROUTE} <route>, with `by`): it is never driven "
                         f"again without one")
        slots = [r.get("slot") for r in rows if isinstance(r, dict)]
        if len(set(slots)) != len(slots):
            p.append("slots repeat")
        for slot, (attempt, why) in self.owed.items():   # W1B3-6: an owed drive is never silently left undone
            if slot not in slots:
                p.append(f"the history owes slot {slot} attempt {attempt} ({why}), and the rows leave it out")
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
            if self._money_gate(block):                     # W7C: before the block is registered
                return self.outcomes
            if not self._register(block):                    # serial: one commit each
                return self.outcomes
            launched = [(row, attempt) + self._launch(row, attempt) for row, attempt in block]   # ids recorded
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(block)) as pool:
                futures = [pool.submit(self._drive_step, row, attempt, cid, err)
                           for row, attempt, cid, err in launched]
                results = [self._result(f, row, attempt, cid)              # row order
                           for (row, attempt, cid, _), f in zip(launched, futures)]
            self._block_event = None                         # the block's pauses share one window event (W1B3-5)
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

    def _money_gate(self, block) -> bool:
        """W7C (THE MONEY GATE): True when the block may not be launched. Nothing of it is registered or launched; the
        loop stops blocked, naming the first row that bills money and every reason, for Javier's word."""
        problems = money_gate_problems([r for r, _ in block], self.ledger, self.clock)
        if not problems:
            return False
        row, attempt = next((r, a) for r, a in block if bills_money(r))
        self.stopped = {"slot": row["slot"], "attempt": attempt, "state": labels4.BLOCKED,
                        "reason": "the money gate refuses the block (nothing registered or launched): "
                                  + "; ".join(problems)}
        return True

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
                for r, a in registered:                      # nothing ran: re-driven on a restart (W1B3-1)
                    self._commit(r, a, self._outcome(r, a, None, state=labels4.FAILED, reason=reason,
                                                     drive_started=False))
                return False
            registered.append((row, attempt))
        return True

    def _commit(self, row, attempt, outcome) -> dict:
        """Decide the take's fate, seal its mask, commit it: the one road every outcome takes to the repo."""
        if outcome["state"] == labels4.PAUSE:
            outcome["window_event"] = self._window_event()   # W1B3-5: one per block that paused
        outcome.update(self._decide(row, attempt, outcome))   # the fate, before the commit
        if outcome["leaked_container"] is not None:          # A LEAK (W1B3-1): the route's fate kept, the loop stops
            outcome["stop"] = outcome["stop"] or outcome["reason"]
            if self.stopped is None:
                self.stopped = {"slot": row["slot"], "attempt": attempt, "state": outcome["state"],
                                "reason": outcome["stop"]}
        self._seal(outcome)
        try:
            self.repo.commit_records(row, attempt, outcome)
        except Exception as e:  # noqa: BLE001
            closed = self.closed_cells.get(row["half_cell"])   # a cell closes only by a committed record
            outcome = dict(outcome, state=labels4.FAILED, reason=f"commit failed: {e}",
                           final=False, rerun=False, stop=f"commit failed: {e}", window_event=None,
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

    def _window_event(self) -> int:
        """The usage-window event of the block being committed: a new one at its first pause, shared by the rest."""
        if self._block_event is None:
            self.last_window_event += 1
            self._block_event = self.last_window_event
        return self._block_event

    @staticmethod
    def _outcome(row, attempt, cid, **kw) -> dict:
        """An outcome with every key. drive_started is fail-closed true: only the roads where nothing ran (a register
        or launch failure) say false."""
        out = dict.fromkeys(OUTCOME_KEYS)
        out.update(slot=row["slot"], half_cell=row["half_cell"], attempt=attempt, container_id=cid,
                   mask=True, mask_basis="no records: masked fail-closed", final=False, rerun=False,
                   beyond_cap=False, drive_started=True)
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
        if launch_error is not None:                       # nothing ran: re-driven on a restart (W1B3-1)
            out = self._outcome(row, attempt, cid, state=labels4.FAILED, reason=f"launch failed: {launch_error}",
                                drive_started=False)
        else:
            try:
                records = self.driver.drive(row, cid)
            except Exception as e:  # noqa: BLE001
                out = self._outcome(row, attempt, cid, state=labels4.FAILED, reason=f"drive failed: {e}")
        removal_error = self._remove(cid)                  # by the recorded id, whatever happened
        if out is None:
            out = self._route(row, attempt, cid, records)
        out.update(self._annotations(records))
        if removal_error is not None:                      # A LEAK (W1B3-1): the take keeps its state, the loop stops
            out.update(leaked_container=cid,       # S6-gap4-2: and every surviving recorded id
                       leaked_containers=list(getattr(removal_error, "leaked_ids", None) or [cid]),
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
        half-cell has had routing.json's cap of their events, this take's counted (a pause sharing a window event
        already counted adds none, W1B3-5). The take that brings the count to the cap is its slot's last, and it
        closes the half-cell `incomplete — mechanical`, with why, in its own committed record; the loop goes on with
        the other half-cells."""
        route, cell = outcome["state"], row["half_cell"]
        cap = half_cell_cap(self.table, route)
        count = len(self.cell_events[(cell, route)] | {cell_event(outcome)})   # every committed event, and this one
        if count < cap:
            return self._fate(rerun=True)
        unit = (f"{count} usage-window events of pause (the pauses that share one reset count once, W1B3-5)"
                if route == labels4.PAUSE else f"{count} {route}s")
        return self._fate(final=True, beyond_cap=True, cell_state=labels4.INCOMPLETE_MECHANICAL,
                          cell_reason=f"half-cell {cell!r} has had {unit} and its {route} cap is {cap} "
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
