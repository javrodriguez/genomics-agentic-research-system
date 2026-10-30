#!/usr/bin/env python3
"""Round 4's take loop: register row -> commit -> drive -> route -> commit, inside the repo.

Round 3 drove its takes from an out-of-repo `batch.sh` (a verify-3 finding); this is its in-repo
replacement. It runs under `nohup` and refuses to start otherwise (`--foreground` overrides, for a
watched terminal).

SERIAL WHERE IT MATTERS, CONCURRENT WHERE IT IS SAFE. Registering and committing stay serial;
only the drives run at once, at most BLOCK = 3 (one with `serial=True`, the fallback), in a rolling window
(lane vendor-b19, glitch-26's rulings B19-5 to B19-8, 19 Oct 2026; lane-reports/B19-DESIGN-NOTE.md):

  1. take a WAVE of queued rows, as many as there are free drive lanes, fewer once MAX_OPEN takes are open
     (registered, outcome not committed), and none while a hold is set (below);
  2. register each row, one commit each, in row order;
  3. launch each take's container and RECORD ITS ID; drive it beside the drives already running;
  4. inside each drive step, remove the container BY THE RECORDED ID (never by a name pattern),
     then decide the take's annotations (`routing.annotate`: events, mask) and its route
     (`routing.route`) from its harness-side records, before its commit, so a re-run frees its
     slot before it closes. The drive step never raises: whatever goes wrong becomes the take's
     terminal state;
  5. whenever the oldest open take's drive has finished, decide its fate (below), then commit its
     records with that fate, serially, in row order, for every open take, even after one of them
     failed; only then stop. A drive that finished behind an unfinished older one waits for it.
     Every drive already finished is committed before a lane is filled (the tie rule), so with
     equal drive durations every wave is today's block of three and the history is a block run's.

THE HOLDS (B19-5). The routed state of a finished, uncommitted take is read (never decided) from
its drive step, and no new drive starts while one paused, was blocked or failed, leaked its
container, or brings this night's harness-errors to the count; nor while the loop has stopped or
waits for the usage window; nor for a half-cell that a finished, uncommitted rehearsal or pause
would bring to its cap (the wave stops before such a row, so the queue's order is kept). The open
takes finish and are committed first.

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
                   half-cell closes (THE CELL CAPS); either way NO NEW DRIVE is launched from the
                   moment its drive finishes until the usage window resets (THE USAGE WINDOW);
                   drives already running finish and are routed as usual
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
take at a time, so each of its pauses was its own window event, while this loop drives up to three
at once and every pause committed between two waits for the usage window shares the one reset the
second wait is for (B19-5: an event holds at most BLOCK pauses, one per slot, those of the drives
in flight when the first pause was seen). Each committed pause carries that event as `window_event`. The take whose event brings the count to
routing.json's cap is its slot's last (final, never re-run, beyond_cap), and it is committed with
`cell_state` = labels4.INCOMPLETE_MECHANICAL and a `cell_reason` before the loop moves on. From then on nothing more is registered for the half-cell:
its queued rows and re-runs are dropped, each listed in `skipped`. The loop goes on with the other
half-cells; it never stops for a human here. A take of the half-cell that was open when its
half-cell closed is committed as usual, never re-run, and carries the cell state too (B19-5).
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
    stop                         why the loop stops once its open takes are committed (else None)
    cell_state                   labels4.INCOMPLETE_MECHANICAL once the take's half-cell has closed at
                                 its rehearsal or pause cap, by this take or an earlier one (else None)
    cell_reason                  why the half-cell closed: its count and cap (else None)
    drive_started                False only when the take never reached its drive (its register or
                                 its launch failed); True once driver.drive() was called, and
                                 fail-closed True when the loop cannot tell (the drive step raised).
                                 A `failed` take whose drive started needs a ruling (THE RULINGS)
    window_event                 for a pause, the usage-window event it belongs to (an int, rising in
                                 commit order, shared by every pause committed between two waits for
                                 the usage window, B19-5); else None

The repo masks the take's text whenever `mask` is true; it never deletes it. The mask rule is
applied at the one place every outcome passes before its commit (`_seal`), so no road to a commit
can skip it.

A LEAK (review round 3, W1B3-1; glitch-f3 accepted the gap4 lane lead's fix as written, 6 Oct 2026;
glitch-f3's, not the owner's). When remove() fails, the take keeps its routed state and its fate
(a graded take stays graded and final, a rehearsal keeps its re-run); `leaked_container` names the
recorded id, `reason` says why, the routed decision is committed, and the loop stops once its open
takes are committed, the stop committed with the record. A leak never turns a take into `failed`.

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
    why      why, in the ruler's words (a non-empty string; pre-freeze review 1, MAJOR 8)
    cite     what the ruling rests on: the record, commit or rule it cites (a non-empty string)

THE RULING RULE (pre-freeze review 1, MAJOR 8 and m17; lane pf1-l2a, the Lane-orchestrator's approval of the fold plan,
Sat 24 Oct 2026, under Javier's standing delegation; RULING_RULE below, registered in the draft as ruling_rule). Before
the agent's first turn, read from the stopped take's own records, any ruling may be made. After it, or when the records
cannot show the phase (none, or unsound) of a take whose drive started, a ruling never routes rehearsal (a
before-first-turn route). After the first turn a ruling re-runs a take (re-run, or a route to pause or harness-error)
only when the take's own committed records already meet one of RERUN_FAULT_ROWS (an API error, a watcher gap: the
Lane-orchestrator's ruling 2 on the lane, the same day, less the counter rise its ruling on the lane's review dropped)
or _route blocked it for the driver's pin (pin_block), refused at the door when the ruling is made otherwise. A take
whose drive started and left no records can only be ruled aborted unless the driver's own refusal record was committed
with its outcome (takes.ruling_door_problems, which also reads the end state at the door). As a second check, a ruling that re-runs such a take, or one with no readable phase (where rehearsal too
re-runs), stands only when the take's own grader reads its committed end state with no wrong action, which
check_results.ruled_rerun_problems checks at publication. A take whose records match no routing row takes its
class's pre-registered default (routing.json no_match_defaults, routing.no_match_default), and no other ruling, save
after the first turn its pre-registered unreadable alternative, aborted, with a cite naming the end state reading its
grader could not make (routing.no_match_unreadable, unread_cite_form; lane fold2/merge).
`history_problems` refuses the rest, so the ruling door (takes.commit_ruling) and a restart refuse them before anything
is driven.

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
is re-run). Lane w1b decision (`restart_waits`, re-ruled by B19-5): when a pause, committed or ruled,
is among the last MAX_OPEN committed outcomes or the rulings committed among or after them, a restart
waits for the usage window before its first launch.

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
what the remaining tries project, against the $180 / $220 / $400 caps, OD107), are called by the loop itself, never left to
a driver. Before each wave is registered (B19-5: the rows that fill the drive lanes free at that moment; with equal
drive durations, a block of three), every row of the wave whose harness bills money per call (any harness
but routing.NO_MONEY_HARNESSES; routing.PAID_HARNESSES names each one's arm) is put through both, on one reading of
the spend ledger (`ledger.read()`, exactly LEDGER_KEYS: now, walks, spend, start, trimmed). The hold reads the
loop's OWN clock (`clock()`, aware UTC, read at check time; injectable for tests), never the ledger's `now`, which
may be recorded but never decides the hold (glitch-1b's ruling on Q-w7c-1, 12 Oct 2026). When either refuses, or
the ledger cannot be read or is not that shape, or the harness has no arm, nothing of the wave is registered or
launched: the takes already open finish and are committed, the loop stops (`stopped`, state blocked) with the named
reason, for Javier's word, and the frozen order is kept (the wave's Claude rows wait too). Nothing of the wave is
committed, so a restart puts it through the gate again. A
row of a harness that bills money, handed to a loop given no ledger, is refused before anything runs. Rows of
claude-code (arms A and C, a subscription login that bills no money per call) never read the ledger and never call
either check. The ledger is CP2's (the vendor spend reads and the recorded trim); none is built here.

A REPO OR WINDOW FAILURE STOPS, never sinks (review round 2, W1B2-5). If `register` raises, the
loop records why in `stopped`, the takes already open finish and are committed, then every row of
the wave already registered is committed `failed` (masked fail-closed, nothing launched), and the
loop returns; if `wait_reset` raises, nothing was open and nothing of the next wave was registered,
so the loop records why in `stopped` and returns. A restart then continues from the committed
outcomes.

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
owner's). The loop calls `window.wait_reset()` before its next launch after a committed pause, once
every take open when the pause was seen is committed (B19-5), and on a restart when any of the last
MAX_OPEN committed outcomes is a pause (lane w1b decision 11, re-ruled by B19-5); only then does it
register and launch. The contract CP2's window keeps, and this loop relies on:

    - wait_reset() returns promptly when the usage window has already reset (so a restart after a
      pause whose window reset meanwhile waits once and goes on, never a whole window again);
    - it blocks until the window resets otherwise;
    - it raises on failure, and the loop then stops as `failed` (W1B2-5): nothing of the next
      wave is registered, launched or committed, and `stopped` says why.

THE NIGHTLY STOP (live harness step 4, 14 Oct 2026; plans/gap-study-round-4.md line 904: "Routing follows the
pre-registered table, and three `harness-error`s in one night stop the run for a ruling."; line 560: "Three in one
night stop the run for a ruling."; line 196: a pause is "outside the nightly stop rule"). The loop counts the
`harness-error` outcomes it commits; once the harness-errors committed or finished reach NIGHTLY_HARNESS_ERRORS, no
new drive starts; the last take open when the count is committed (B19-5: the take launched last, that take itself when
none other is open; with equal durations the block's last) carries `stop` = NIGHTLY_STOP + why, `stopped` says so,
and nothing further is registered. Pauses are never
counted. A take `failed` after its drive started (the executed-refusal road, named departure D-3a-1) is no
registered harness-error: it is counted apart in `night_counts` and never consumed by the rule (it stops the loop on
its own). Named departure D-4-1 (lane-reports/nightly-stop-rule-2026-10-14.md): no registered text defines "night"
and no committed outcome carries a time, so the window is every harness-error committed since the last committed
NIGHT RULING (or since the history began), rebuilt on a restart, which stops no later than any reading of one night.
A restart refuses whenever that count is already at the registered number, wherever (or whether) the stop text was
committed: the text is a reader's marker, never what the replay trusts (step-4 review, finding 1). The stop is
resolved only by a committed, closed night ruling (NIGHT_RULING_KEYS: kind NIGHT_RULING, the slot and attempt of the
harness-error that brought the window to the count, and `by`, checked as THE RULINGS' `by` is); it must name exactly
that take, while the count stands at the number, and it starts the next window. The loop reads it and never writes
one. (D-4-2, a ruling named by a restart argument, is superseded: lane-reports/nightly-stop-rule-2026-10-14.md.)

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
# B19-5 (glitch-26, 19 Oct 2026): the most takes open at once, registered and their outcome not committed (in flight,
# or finished and waiting for an older take's commit). BLOCK stays the number of drives in flight.
MAX_OPEN = 12
PENDING = "PENDING"

# Every key of a committed outcome (see WHAT IS COMMITTED).
OUTCOME_KEYS = ("slot", "half_cell", "attempt", "container_id", "state", "reason", "decision", "records",
                "events", "mask", "mask_basis", "leaked_container", "leaked_containers", "final", "rerun",
                "beyond_cap", "stop",
                "cell_state", "cell_reason", "drive_started", "window_event")
# Every key of a committed ruling (THE RULINGS, W1B3-1): a closed record, told from an outcome by its kind.
RULING_KEYS = ("kind", "slot", "attempt", "ruling", "route", "by", "why", "cite")
# Pre-freeze review 1, MAJOR 8: the two keys a ruling gives its reason in, each a non-empty string, never defaulted.
RULING_REASON_KEYS = ("why", "cite")
UNKNOWN_PHASE = "unknown"
# THE RULING RULE, the door's half (the Lane-orchestrator's ruling 2 on lane pf1-l2a, Sat 24 Oct 2026, under Javier's
# standing delegation): after the agent's first turn, a ruling may re-run a take only when its own committed records
# already meet one of these harness-fault rows of routing.json (an API error, a watcher gap), or Batch._route itself
# blocked it for the driver's pin. The review of 5afd80a7 (finding 1) and the orchestrator's ruling on it: cgroup-kill
# is not one, since the agent can raise those counters itself and the plan never re-runs an aborted take.
RERUN_FAULT_ROWS = ("api-error-after-first-turn", "watcher-gap")
# Finding 4: Batch._route's pin block is a harness fault by construction (the agent never writes records.pin). Its
# reason opens with this prefix, written by _route alone; DRIVER_PIN_FAULT names it beside the fault rows.
PIN_BLOCK_PREFIX = "the driver's pin "
DRIVER_PIN_FAULT = "driver-pin-mismatch"
RERUNNING_ROUTES = (labels4.PAUSE, labels4.HARNESS_ERROR, labels4.REHEARSAL)
# Pre-freeze review 2, m6 (lane fold2/la2): the words an aborted ruling's cite opens with after the first turn, followed
# by ': ' and the exception type of the reading its grader could not make (check_results.unread_cite).
END_STATE_UNREAD_CITE = routing.END_STATE_UNREAD_CITE     # lane fold2/merge: one constant, routing.json's alternative too


def unread_cite_form(cite) -> bool:
    """Lane fold2/merge: the cite has the form check_results.unread_cite gives, the phrase, ': ' and an exception type
    (a whole identifier word). batch reads no end state, so it checks the form; the door and the publication
    (check_results.ruled_route_problems, unread_cite_holds) hold the type to the reading the grader failed with."""
    head = f"{END_STATE_UNREAD_CITE}: "
    if not (isinstance(cite, str) and cite.startswith(head)):
        return False
    rest = cite[len(head):]
    word = rest[:next((i for i, ch in enumerate(rest) if not (ch.isalnum() or ch == "_")), len(rest))]
    return word.isidentifier()
# THE RULING RULE, as the draft registers it (build_draft writes it to ruling_rule; tests bind the two).
RULING_RULE = {
    "text": ("A human ruling on a take the loop stopped on (blocked, or failed after its drive started) names who made "
             "it (by), why, and what it rests on (cite), each never defaulted. Before the agent's first turn, read "
             "from the stopped take's own records, any ruling may be made. After it, or when those records cannot "
             "show the phase of a take whose drive started, a ruling routes graded (the take's own grader reads its "
             "end state) or aborted (counted against holding, with its reason), or re-runs the take (re-run, or a "
             "route to pause or harness-error, and rehearsal only when the records cannot show the phase). After the "
             "first turn, a ruling re-runs a take only when the take's own committed records already meet a "
             "harness-fault row of the routing table (an API error, or a watcher gap), or when the loop blocked it "
             "because the driver's pin was not the registered row's profile; a rise of the out-of-memory or pids "
             "counters is the agent's own and never re-runs (aborted is never re-run). Any ruling that re-runs such "
             "a take, or one whose records cannot show its phase, stands only when the take's own grader reads its "
             "committed end state with no wrong action (its excluded view is not wrong, and a take that cannot be "
             "graded counts as wrong). A take whose drive started and left no records can only be ruled aborted, "
             "unless the driver's own refusal record was committed with the take's outcome, in the same commit; "
             "then it may be re-run under the same end-state check. After the first turn, read from the take's own "
             "records, a ruling that routes the take graded or aborted is bound by its end state: the take's own "
             "grader reads its committed end state first, and the ruling routes graded when it reads whole "
             "(whatever the grader's word), aborted only when it does not, with its cite opening with 'end state "
             "unreadable: ' and then that reading's exception type (the type of the error the grader raised). The "
             "ruling door (takes.commit_ruling) checks all "
             "of this before anything is written; a restart refuses a history that breaks the refusal-record or the "
             "driver's-pin condition before it drives anything, and the publication check refuses the record set "
             "again on all of it. A take whose records match no routing row is "
             "ruled by its class's pre-registered default (routing.json no_match_defaults) and by no other ruling, save "
             "that after the first turn its class's pre-registered alternative, aborted, stands in its place when "
             "the take's own grader cannot read its end state, cited as above (routing.json no_match_defaults, "
             "unreadable). "
             "Every published take of a slot a ruling touched carries ruled true, and the result counts ruled takes "
             "per half-cell. A take a ruling routes pause or aborted is counted with the stopped takes, its end "
             "state read for a forbidden change like any paused or aborted take's."),
    "enforced_by": ["evals/gap-study-4/batch.py ruling_rule_problems (the door, at ruling time, and every restart)",
                    "evals/gap-study-4/takes.py ruling_door_problems (the door, at ruling time: the end state, the "
                    "driver's refusal record and the driver's pin)",
                    "evals/gap-study-4/check_results.py ruled_rerun_problems (the publication)",
                    "evals/gap-study-4/check_results.py ruled_route_problems (the door and the publication: graded "
                    "or aborted after the first turn, by the end state)",
                    "evals/gap-study-4/stats.py route_events_table (the count)",
                    "evals/gap-study-4/run.py stopped_counts (a ruled pause or abort's forbidden changes)"],
    "source": ("Pre-freeze review 1, MAJOR 8 (rulings on stopped takes unconstrained and unpublished) and m17 (no-match "
               "inputs), folded by lane pf1-l2a under the Lane-orchestrator's approval of the fold plan, Sat 24 Oct "
               "2026, under Javier's standing delegation; it binds whoever rules, Javier included, and is reported to "
               "him after. Pre-freeze review 2, m6 (a ruling chose graded or aborted with no criterion, and a ruled "
               "abort escaped the forbidden-change count), folded by lane fold2/la2 under glitch-45's fold plan of "
               "Thu 29 Oct 2026, under the same delegation. Its no-match residual (a no-match take after the first "
               "turn whose end state cannot be read had no ruling that could stand) was folded by lane fold2/merge, "
               "glitch-45's assignment of the same day."),
}


# Interface 8 (w1b's next-touch item 5): a registered row's agent, {"harness": AgentAdapter.name, "version":
# AgentAdapter.version()}, required beside its model and never defaulted.
AGENT_KEYS = ("harness", "version")

# THE NIGHTLY STOP: the registered count, and the prefix its committed stop carries (a restart finds it by it).
NIGHTLY_HARNESS_ERRORS = 3
NIGHTLY_STOP = "nightly stop rule"
# The committed run-level ruling that resolves a nightly stop (step-4 review fold; supersedes D-4-2).
NIGHT_RULING = "nightly-stop-ruling"
NIGHT_RULING_KEYS = ("kind", "slot", "attempt", "by")


def is_night_ruling(entry) -> bool:
    """A history entry that is a night ruling (THE NIGHTLY STOP), never an outcome or a take's ruling."""
    return isinstance(entry, dict) and entry.get("kind") == NIGHT_RULING

# Routes that re-run a slot, whose spent re-runs a restart must count again.
RERUN_ROUTES = (labels4.REHEARSAL, labels4.HARNESS_ERROR, labels4.PAUSE)
# Routes counted per half-cell, round 3's unit, whose cap closes the half-cell (glitch-f3's ruling, THE CELL CAPS).
CELL_CAPPED_ROUTES = (labels4.REHEARSAL, labels4.PAUSE)


def is_ruling(entry) -> bool:
    """A history entry that is a ruling (THE RULINGS), never an outcome: told by its kind alone."""
    return isinstance(entry, dict) and entry.get("kind") == labels4.RULING


def is_outcome(entry) -> bool:
    """The one shared predicate for "a committed outcome": neither a take's ruling nor a night ruling (THE NIGHTLY
    STOP). Every reader that tells outcomes from rulings uses it, so a run-level record is never read as an outcome."""
    return isinstance(entry, dict) and not is_ruling(entry) and not is_night_ruling(entry)


def needs_ruling(outcome: dict) -> bool:
    """W1B3-1: the take stopped the loop on something a human must rule on before its slot goes on: it is blocked,
    or it failed after its drive started (the agent may have acted). A failed take where nothing ran needs none."""
    return outcome["state"] == labels4.BLOCKED or (outcome["state"] == labels4.FAILED and outcome["drive_started"] is not False)


def ruled_phase(outcome: dict, table: dict) -> str:
    """THE RULING RULE: a stopped take's phase, read from its own records when they are sound under `table`, else
    UNKNOWN_PHASE (no records, as when the driver raised, or records routing cannot read)."""
    records = outcome.get("records")
    if not isinstance(records, dict) or routing.shape_problems(records, table):
        return UNKNOWN_PHASE
    return routing.phase_of(records)


def rerun_fault_rows(records: dict, table: dict) -> list:
    """The ids of RERUN_FAULT_ROWS that `records` match under `table`; a fault row the table lacks raises TableError
    (never read as no fault)."""
    rows = {row["id"]: row for row in table["rows"]}
    missing = [rid for rid in RERUN_FAULT_ROWS if rid not in rows]
    if missing:
        raise routing.TableError(f"the ruling rule's harness-fault rows {missing} are not rows of routing.json")
    return [rid for rid in RERUN_FAULT_ROWS if routing.matches(rows[rid], records, table)]


def reruns(r: dict) -> bool:
    """A ruling that drives its take's slot again: re-run, or a route to pause, harness-error or rehearsal."""
    return r.get("ruling") == labels4.RULE_RERUN or r.get("route") in RERUNNING_ROUTES


def pin_block(outcome: dict) -> bool:
    """Finding 4: the take Batch._route blocked because the driver's pin was not the registered row's profile (its
    reason, written by _route alone, opens with PIN_BLOCK_PREFIX; the records are the driver's)."""
    return (outcome.get("state") == labels4.BLOCKED and isinstance(outcome.get("reason"), str)
            and outcome["reason"].startswith(PIN_BLOCK_PREFIX) and isinstance(outcome.get("records"), dict))


def rerun_faults(outcome: dict, table: dict) -> list:
    """The harness faults a stopped take's own committed records show: RERUN_FAULT_ROWS it matches, and
    DRIVER_PIN_FAULT when Batch._route blocked it for the driver's pin."""
    return rerun_fault_rows(outcome["records"], table) + ([DRIVER_PIN_FAULT] if pin_block(outcome) else [])


def door_rule_problems(history: list, rows: list, table: dict, refusal) -> list[str]:
    """THE RULING RULE's two conditions that read beyond the history (the closure review of 898e598c, MINOR 1, and
    the Lane-orchestrator's ruling on it): for every ruling in `history`, (a) a take whose drive started and left no
    records is ruled aborted, or re-run only when `refusal(row, outcome)` (takes.driver_refusal_record: the driver's
    own refusal record, bound to the commit of the take's outcome) finds one; (b) a pin block whose pin is the
    registered row's own profile (`rows`, by slot) is no driver pin mismatch. The ruling door, every restart
    (Batch.run) and the publication (run.produce) all call it, so a ruling written into rulings.json past the door is
    refused the same way."""
    seen, out = {}, []
    for entry in history:
        if is_outcome(entry):
            seen[(entry.get("slot"), entry.get("attempt"))] = entry
            continue
        if not is_ruling(entry) or entry.get("ruling") not in labels4.RULINGS:
            continue
        key = (entry.get("slot"), entry.get("attempt"))
        taken = seen.get(key)
        if taken is None:
            continue                                   # history_problems names it
        row = next((r for r in reversed(rows) if r.get("slot") == key[0]), None)
        aborted = entry["ruling"] == labels4.RULE_ROUTE and entry.get("route") == labels4.ABORTED
        if pin_block(taken) and row is not None:
            try:
                own = taken["records"].get("pin") == expected_pin(row, table)
            except PinProfileMissing:
                own = False
            if own:
                out.append(f"slot {key[0]} attempt {key[1]}: its block names the driver's pin, but the pin is the "
                           f"registered row's own profile: no driver pin mismatch, so no harness fault to re-run it on")
        if taken.get("records") is None and taken.get("drive_started") is not False and not aborted:
            if not reruns(entry):
                out.append(f"slot {key[0]} attempt {key[1]}: its drive started and left no records, so it can only "
                           f"be ruled aborted (or re-run on the driver's own refusal record; THE RULING RULE)")
            elif row is None or refusal(dict(row, slot=key[0], attempt=key[1]), taken) is None:
                out.append(f"slot {key[0]} attempt {key[1]}: its drive started and left no records, and no refusal "
                           f"record of the driver's was committed with its outcome: it can only be ruled aborted")
    return out


def ruling_rule_problems(r: dict, taken, table: dict) -> list[str]:
    """THE RULING RULE (pre-freeze review 1, MAJOR 8 and m17): why a closed ruling breaks the rule for the take it
    rules on (`taken`, None when no earlier outcome commits it, which _ruling_problems names)."""
    p = []
    for key in RULING_REASON_KEYS:
        if not (isinstance(r.get(key), str) and r[key].strip()):
            p.append(f"a ruling gives its {key} (a non-empty string, never defaulted), got {r.get(key)!r}")
    if not isinstance(taken, dict) or r.get("ruling") not in labels4.RULINGS:
        return p
    phase = ruled_phase(taken, table)
    if r["ruling"] == labels4.RULE_ROUTE and phase == labels4.AFTER_FIRST_TURN and r["route"] == labels4.REHEARSAL:
        p.append(f"slot {r['slot']} attempt {r['attempt']} is {phase}: a ruling routes it graded, aborted, pause or "
                 f"harness-error, or re-runs it, never rehearsal (a before-first-turn route; THE RULING RULE)")
    if phase == UNKNOWN_PHASE:
        return p
    if phase == labels4.AFTER_FIRST_TURN and reruns(r) and not rerun_faults(taken, table):
        p.append(f"slot {r['slot']} attempt {r['attempt']} is {phase} and its records meet none of the harness-fault "
                 f"rows {list(RERUN_FAULT_ROWS)}, nor was it blocked for the driver's pin: a ruling routes it graded "
                 f"or aborted, never re-runs it (THE RULING RULE, the door's half)")
    try:
        default = routing.no_match_default(taken["records"], table)
    except routing.TableError as e:
        return p + [str(e)]
    if default is not None and (r["ruling"], r["route"]) != default:
        alt = routing.no_match_unreadable(taken["records"], table)     # lane fold2/merge: an unreadable end state
        if alt is not None and (r["ruling"], r["route"]) == alt and unread_cite_form(r.get("cite")):
            return p
        also = (f", or its pre-registered alternative {alt[0]} {alt[1]} with a cite opening "
                f"'{END_STATE_UNREAD_CITE}: <the reading's exception type>'" if alt is not None else "")
        p.append(f"slot {r['slot']} attempt {r['attempt']}: its records match no routing row ({phase}, last turn "
                 f"{taken['records']['ledger']['end']}), so its ruling is the pre-registered default {default[0]} "
                 f"{default[1]} (routing.json no_match_defaults){also}, not {r['ruling']} {r['route']}")
    return p


def cell_event(outcome: dict) -> tuple:
    """The event a rehearsal or a pause is in its half-cell's count (THE CELL CAPS): each rehearsal is its own; every
    pause of one usage-window event is one, since the pauses that share one reset count once (W1B3-5, glitch-f3's
    ruling). A take a ruling routes (it carries no window event) is its own event."""
    if outcome["state"] == labels4.PAUSE and outcome.get("window_event") is not None:
        return ("window", outcome["window_event"])
    return ("take", outcome["slot"], outcome["attempt"])


def effective_route(entry: dict):
    """What a history entry counts as for the usage window: an outcome's state, or a route ruling's route."""
    if is_night_ruling(entry):
        return None                                   # a run-level ruling routes nothing
    if is_ruling(entry):
        return entry["route"] if entry["ruling"] == labels4.RULE_ROUTE else None
    return entry["state"]


def restart_waits(history: list) -> bool:
    """Lane w1b decision 11, bound by W1B3-3 and re-ruled by B19-5: a restart waits for the usage window when a pause,
    committed or ruled, is among the last MAX_OPEN committed outcomes (every take open when the pause was seen: a pause
    first among them or in their middle counts) or the rulings committed among or after them."""
    at = [i for i, e in enumerate(history) if is_outcome(e)][-MAX_OPEN:]
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


class MoneyGateRefused(RuntimeError):
    """W7C-R1-3: a paid take the month-turn hold refused just before its launch (nothing was launched)."""


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


class PinProfileMissing(KeyError):
    """Lane vendor-admission T4 P0b (R-4): a row whose harness and model have no pin profile, refused by name; still a
    KeyError for any caller that catches one."""

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else ""


def expected_pin(row: dict, table: dict) -> dict:
    """The pin a take of this registered row must run under: its harness (the row's agent), its model, and that
    model's profile under that harness (interface 8: pin_profiles is keyed by harness, then model). A harness or model
    without a profile refuses by name (PinProfileMissing): CP5 registers the O and G profiles (T4 plan R-4)."""
    harness = row["agent"]["harness"]
    profile = (table["pin_profiles"].get(harness) or {}).get(row["model"])
    if profile is None:
        raise PinProfileMissing(f"routing.json's pin_profiles hold no {harness}/{row['model']} profile; CP5 registers it")
    return dict(profile, model=row["model"], harness=harness)


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


def ledger_shape_problems(snap: dict) -> list[str]:
    """W7C-R1-1 (MAJOR, money fail-open; ruling W7C-close-1): walks and spend are lists (exactly list) of dicts, and
    start is a string or an aware datetime. An empty string or dict would iterate as nothing spent and PROCEED, so a
    ledger that failed to parse would read as $0."""
    p = []
    for key in ("walks", "spend"):   # (W7C-R2-2: and each spend usd exactly str, int or float)
        value = snap[key]
        if type(value) is not list:
            p.append(f"the spend ledger's {key} is a {type(value).__name__}, not a list")
        elif not all(type(x) is dict for x in value):
            p.append(f"the spend ledger's {key} holds an element that is not a dict")
        elif key == "spend" and not all(type(x.get("usd")) in (str, int, float) for x in value):
            # W7C-R2-2: exactly str, int or float (never a subclass whose str() could lie, nor a bool)
            p.append("the spend ledger's spend holds a usd that is not exactly a str, int or float")
    start = snap["start"]
    if not (type(start) is str or (isinstance(start, datetime.datetime) and start.tzinfo is not None)):
        p.append(f"the spend ledger's start is {start!r}, neither a string nor an aware datetime")
    return p


def hold_problem(row: dict, now, trimmed) -> str | None:
    """W7C: why the month-turn hold refuses this paid row's arm at `now` (the loop's clock), or None when it allows."""
    import costs   # costs imports this module: read at call time, never at import
    harness = row["agent"]["harness"]
    arm = routing.PAID_HARNESSES.get(harness, {}).get("arm")
    if arm is None:
        return f"slot {row['slot']}: harness {harness!r} bills money and has no arm in routing.PAID_HARNESSES"
    try:
        allowed = costs.month_turn_allowed(arm, now, trimmed)
    except Exception as e:  # noqa: BLE001 - a clock or trim the hold cannot read refuses
        allowed = f"{type(e).__name__}: {e}"
    if allowed is True:
        return None
    return (f"slot {row['slot']}: arm {arm} ({harness}): the month-turn hold refuses at {now!r} (the loop's clock) "
            f"(costs.month_turn_allowed: {allowed}): no OpenAI or Google take until Javier's 'caps trimmed' is "
            f"recorded")


def read_clock(clock):
    """The loop's clock, read once; a clock that raises reads as a value every check refuses."""
    try:
        return clock()
    except Exception as e:  # noqa: BLE001 - a clock that cannot be read refuses
        return f"<clock unreadable: {type(e).__name__}: {e}>"


def money_gate_problems(rows: list[dict], ledger, clock=utc_now, seen: dict | None = None) -> list[str]:
    """W7C (THE MONEY GATE): why these rows may not be launched now (empty when they may). Rows that bill no money are
    never put through it: with none that bills money the ledger is not read and neither check is called. Otherwise one
    reading of the ledger feeds costs.month_turn_allowed, per row with its harness's arm and the loop's own clock
    (`clock()`, read once here; never the ledger's `now`, Q-w7c-1), and costs.walk_gate, once;
    anything but an explicit allow from each, or a ledger that cannot be read or is not exactly LEDGER_KEYS of the
    right shapes (W7C-R1-1), or whose start is after the clock's reading (W7C-R1-2), refuses. `seen`, when given,
    receives the reading's trim, for the re-check just before each paid launch (W7C-R1-3)."""
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
    # W7C-R2-1: exactly a dict (never a subclass) whose keys are exactly str (never a key equal to every key)
    if type(snap) is not dict or not all(type(k) is str for k in snap) or set(snap) != set(LEDGER_KEYS):
        got = sorted(snap) if isinstance(snap, dict) else type(snap).__name__
        return [f"the spend ledger's reading is not exactly {list(LEDGER_KEYS)}: {got}"]
    p = ledger_shape_problems(snap)
    if p:
        return p
    if seen is not None:
        seen["trimmed"] = snap["trimmed"]
    now = read_clock(clock)
    try:   # W7C-R1-2: the same clock reading as the hold; a start after it would exclude every dollar spent
        if costs.utc(snap["start"]) > costs.utc(now):
            p.append(f"the spend ledger's start {snap['start']!r} is after the loop's clock {now!r}: no spend would "
                     f"count")
    except Exception as e:  # noqa: BLE001 - a start or clock that cannot be compared refuses
        p.append(f"the spend ledger's start {snap['start']!r} cannot be read against the loop's clock {now!r}: "
                 f"{type(e).__name__}: {e}")
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
        self.ledger = ledger                 # W7C: the spend ledger (THE MONEY GATE), read before each paid wave
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
        self._read_deferral()
        self.outcomes: list[dict] = []
        self._block_trim: dict = {}         # W7C-R1-3: the gated wave's trim, for each paid launch's re-check
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
        self._block_event = None             # the window event of the pauses since the last wait, once one paused
        self.ruled: dict = {}                # (slot, attempt) -> (the ruling, its fate), from the history (W1B3-1)
        self.unruled: dict = {}              # slot -> (attempt, why): its last take awaits a ruling (W1B3-1)
        self.owed: dict = {}                 # slot -> (attempt, why): the history owes it this drive (W1B3-6)
        # THE NIGHTLY STOP: harness-errors counted since the last nightly stop (D-4-1), and the separate, reported
        # count of takes failed after their drive started (D-3a-1), which the rule never consumes.
        self.night_counts = {"harness_error": 0, "failed_after_drive_started": 0}
        self.nightly_stop_pending = False
        self.night_reaching = None           # (slot, attempt) of the harness-error that brought the window to the count
        self._block_last = None              # THE NIGHTLY STOP's carrier: the last take launched (B19-5)
        self.open = collections.deque()      # B19-5: the open takes, (row, attempt, cid, future), in launch order
        self._front = 0                      # B19-5: how many queued re-runs lead the queue
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
        self._replay_night(history)
        self._history = [e for e in history if not is_night_ruling(e)]
        self._replay(self._history)
        if self.nightly_stop_pending:
            raise BatchConfigError(f"{NIGHTLY_STOP}: {self.night_counts['harness_error']} harness-errors are committed "
                                   f"since the last night ruling; the run waits for a committed night ruling naming "
                                   f"(slot, attempt) {self.night_reaching!r}")

    def _read_deferral(self) -> None:
        """Lane gemini-defer, ruling R5 (glitch-f1, 22 Oct 2026): the frozen design's deferred arms (prereg.deferred_arms,
        a pure read of the design in force). The committed go records are read only when a row of a deferred arm is
        handed to the loop (deferral_problem), so no other run gains a git read: from the repo's own
        deferred_go_records() when it offers one (read at HEAD, as history() is), else prereg.committed_go_records.
        An arm with a go record that passes prereg.go_record_problems is released; every other deferred arm's rows,
        by arm or by its registered model, are refused in row_problems. Not in takes.commit_registration: the
        rehearsal registers take_order[0], which is often a G row (arm G holds 360 of the 1,260 rows)."""
        import prereg
        try:
            arms = prereg.deferred_arms()
            table = prereg.load().get("models") or {}
        except ValueError as exc:
            raise BatchConfigError(f"the deferred arms cannot be read: {exc}") from exc
        self.deferred = {a: prereg.deferral_label(e) for a, e in arms.items()}
        self.deferred_models = {m: a for a, e in arms.items() for m in (table.get(a) or e.get("models") or [])}
        self._go_records = None

    def _released(self, arm: str) -> bool:
        import prereg
        if self._go_records is None:
            read = getattr(self.repo, "deferred_go_records", None)
            try:
                self._go_records = list(read() if callable(read) else prereg.committed_go_records())
            except (ValueError, TypeError, OSError) as exc:
                raise BatchConfigError(f"the committed go records cannot be read: {exc}") from exc
        return prereg.deferred_arm_go(arm, self._go_records)

    def deferral_problem(self, r: dict) -> str | None:
        arm = r.get("arm") if r.get("arm") in self.deferred else self.deferred_models.get(r.get("model"))
        if arm is None or self._released(arm):
            return None
        import prereg
        return (f"row {r['slot']}: arm {arm} is {self.deferred[arm]} in the frozen deferred_arms, and no committed "
                f"'{prereg.GO_KIND}' record for arm {arm} exists ({prereg.GO_RECORD.name}, Javier's go): never driven "
                f"while deferred")

    # ---------------------------------------------------------------------------- the history
    @classmethod
    def history_problems(cls, history, table: dict | None = None) -> list[str]:
        """Why the committed outcomes and rulings cannot be trusted (empty when they can). `table` (routing.json's,
        read when None) is the one THE RULING RULE reads a stopped take's records against."""
        if not isinstance(history, list):
            return ["history must be a list of committed outcomes"]
        p, seen, cell, final_at = [], {}, {}, {}
        pending, ruled = {}, set()          # slot -> (attempt, state) of its take awaiting a ruling; ruled takes
        last_event, event_slots = 0, collections.defaultdict(set)
        for i, o in enumerate(history):
            if is_ruling(o):
                p += cls._ruling_problems(i, o, seen, ruled, pending)
                if isinstance(o, dict) and set(o) == set(RULING_KEYS):
                    taken = seen.get((o["slot"], o["attempt"])) if not isinstance(o["slot"], (list, dict, set)) else None
                    if table is None:
                        table = routing.load_table()
                    p += [f"history[{i}]: {x}" for x in ruling_rule_problems(o, taken, table)]
                continue
            if is_night_ruling(o):              # THE NIGHTLY STOP: checked whole by _night_walk below
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
            if is_outcome(o) and o.get("final") is True and isinstance(o.get("attempt"), int):
                final_at[o.get("slot")] = min(final_at.get(o.get("slot"), o["attempt"]), o["attempt"])
        for i, o in enumerate(history):
            if (is_outcome(o) and o.get("slot") in final_at
                    and isinstance(o.get("attempt"), int) and o["attempt"] > final_at[o["slot"]]):
                p.append(f"history[{i}]: slot {o['slot']} attempt {o['attempt']} comes after its final attempt")
        if not p:
            p += cls._night_walk(history)[1]
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
        problems = self.history_problems(history, self.table)
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

    def ruling_door_problems(self, rows: list) -> list[str]:
        """The restart's half of THE RULING RULE's two git-bound conditions (door_rule_problems) over the committed
        history this loop replayed: the repo's own driver_refusal_record when it has one, else the study's
        (takes.driver_refusal_record, read from git)."""
        reader = getattr(self.repo, "driver_refusal_record", None)
        if reader is None:
            import takes                  # batch otherwise never reads git; takes imports batch, so read lazily
            reader = takes.driver_refusal_record
        return door_rule_problems(self._history, rows, self.table, reader)

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
            if not is_outcome(o):                # batch-5 review finding 3: a night ruling holds no take's cell state
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
            elif deferral := self.deferral_problem(r):   # lane gemini-defer, R5: before the pins, the money and the cells
                p.append(deferral)                     # (review NIT-4: called once per row)
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
        problems = self.row_problems(rows) + self.ruling_door_problems(rows)
        if problems:
            raise BatchConfigError("; ".join(problems))
        queue = collections.deque((dict(r), self.next_attempt.get(r["slot"], 1)) for r in rows)
        self.open = collections.deque()                     # B19-5: (row, attempt, cid, future), in launch order
        self._front = 0                                      # no queued re-run leads a new queue
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.block) as pool:
            while True:
                queue = self._commit_finished(queue)         # 1. serial, row order: the oldest open take first
                queue = self._drop_closed(queue)             # nothing more for a closed half-cell
                if not self.open:
                    if self.stopped is not None or not queue:
                        break
                    if self.paused:                          # 2. the open takes are committed: wait, then go on
                        if not self._wait_window():
                            break
                        self.paused = False
                        self._block_event = None             # the pauses before this wait share one event (W1B3-5)
                if queue:
                    finished = self._finished()              # one reading: the holds and the free lanes agree
                    if not self._held(finished):
                        self._fill(queue, pool, finished)    # 3. a wave into the free drive lanes
                running = [f for *_, f in self.open if not f.done()]
                if running and not self.open[0][3].done():
                    concurrent.futures.wait(running, return_when=concurrent.futures.FIRST_COMPLETED)   # 4.
        return self.outcomes

    def _commit_finished(self, queue):
        """B19-5 step 1: while the oldest open take's drive has finished, commit it; its re-run goes to the front of
        the queue, behind the re-runs already queued there. Every drive already finished is committed before a lane
        is filled (the tie rule), and re-runs keep the order of their commits, which is row order."""
        while self.open and self.open[0][3].done():
            row, attempt, cid, f = self.open.popleft()
            outcome = self._commit(row, attempt, self._result(f, row, attempt, cid))
            if outcome["rerun"]:
                queue.insert(self._front, (row, attempt + 1))   # same slot, ahead of every row not yet registered
                self._front += 1
        return queue

    def _finished(self) -> list:
        """The open takes whose drive step has finished and whose commit waits: (row, attempt, routed outcome). The
        routed state is read, never decided: the fate is decided at the commit (B19-5, design note section 4)."""
        out = []
        for row, attempt, cid, f in self.open:
            if f.done():
                out.append((row, attempt, self._result(f, row, attempt, cid)))
        return out

    def _held(self, finished) -> bool:
        """B19-5 step 2: no new drive starts while the loop has stopped or waits for the usage window, or once a
        finished take that is not yet committed paused, stopped (blocked, failed, a leak) or brings this night's
        harness-errors to the registered count (THE NIGHTLY STOP, read in prospect). `finished` is _finished()'s one
        reading, the same the free lanes are counted from, so a drive that ends after it frees no lane yet."""
        if self.stopped is not None or self.paused or getattr(self, "_night_reached", False):
            return True
        if any(o["state"] in (labels4.PAUSE, labels4.BLOCKED, labels4.FAILED) or o["leaked_container"] is not None
               for _, _, o in finished):
            return True
        errors = sum(o["state"] == labels4.HARNESS_ERROR for _, _, o in finished)
        return self.night_counts["harness_error"] + errors >= NIGHTLY_HARNESS_ERRORS

    def _closing_cells(self, finished) -> set:
        """B19-5 (glitch-f3's cap ruling, re-ruled): the half-cells a finished, uncommitted rehearsal or pause would
        bring to their cap. No drive of one starts until that take commits (and then its rows are dropped)."""
        seen = collections.defaultdict(set)
        for row, attempt, o in finished:
            if o["state"] in CELL_CAPPED_ROUTES:
                key = (row["half_cell"], o["state"])
                event = (("window", self._block_event or self.last_window_event + 1) if o["state"] == labels4.PAUSE
                         else cell_event(dict(o, window_event=None)))
                seen[key].add(event)
        return {cell for (cell, route), events in seen.items()
                if len(self.cell_events[(cell, route)] | events) >= half_cell_cap(self.table, route)}

    def _fill(self, queue, pool, finished) -> None:
        """B19-5 step 3: the next queued rows, as many as there are free drive lanes (fewer at MAX_OPEN open takes, and
        none past a row of a closing half-cell, so the queue's order is kept), as one wave: the money gate on the
        wave, its rows registered in row order, each launched in row order and driven. A refusal or a register failure
        stops the loop; the takes already open finish and are committed first. A lane is free only when its drive is
        among `finished`, the reading the holds were decided on."""
        free = self.block - (len(self.open) - len(finished))
        n = min(free, MAX_OPEN - len(self.open), len(queue))
        closing = self._closing_cells(finished)
        wave = []
        while len(wave) < n and queue[0][0]["half_cell"] not in closing:
            wave.append(queue.popleft())
            if not queue:
                break
        if not wave:
            return
        self._front = max(0, self._front - len(wave))
        if self._money_gate(wave):                         # W7C: before the wave is registered
            return
        if not self._register(wave):                        # serial: one commit each
            return
        launched = [(row, attempt) + self._launch_paid_checked(row, attempt) for row, attempt in wave]   # ids
        for row, attempt, cid, err in launched:
            self.open.append((row, attempt, cid, pool.submit(self._drive_step, row, attempt, cid, err)))
        self._block_last = (wave[-1][0]["slot"], wave[-1][1])   # THE NIGHTLY STOP: carried by the last take launched,
        # set once the wave is launched, so a refused or unregistered wave never names a row that is not committed

    def _drain(self) -> None:
        """Every open take's drive waited for and committed, in row order (a stop's open takes finish first). The
        commits go to a throwaway queue: the loop has stopped, so a re-run decided while draining is never queued here
        and its count of queued re-runs is not this queue's; the restart owes that re-run from the history (W1B3-6)."""
        while self.open:
            concurrent.futures.wait([f for *_, f in self.open])
            self._commit_finished(collections.deque())

    def _drop_closed(self, queue):
        """The queue without the rows (first drives and re-runs alike) of a half-cell that closed at its rehearsal or
        pause cap: they are never registered, and each is listed in `skipped` (glitch-f3's cap ruling)."""
        kept, front = collections.deque(), 0
        for i, (row, attempt) in enumerate(queue):
            if row["half_cell"] in self.closed_cells:
                self.skipped.append({"slot": row["slot"], "attempt": attempt, "half_cell": row["half_cell"],
                                     "why": self.closed_cells[row["half_cell"]]})
            else:
                kept.append((row, attempt))
                front += i < self._front                     # a queued re-run kept at the front
        self._front = front
        return kept

    def _money_gate(self, block) -> bool:
        """W7C (THE MONEY GATE): True when the wave may not be launched. Nothing of it is registered or launched; the
        loop stops blocked, naming the first row that bills money and every reason, for Javier's word. (The refusal's
        text still names the block: a reader's marker, unchanged.)"""
        self._block_trim = {}
        problems = money_gate_problems([r for r, _ in block], self.ledger, self.clock, seen=self._block_trim)
        if not problems:
            return False
        row, attempt = next((r, a) for r, a in block if bills_money(r))
        self.stopped = {"slot": row["slot"], "attempt": attempt, "state": labels4.BLOCKED,
                        "reason": "the money gate refuses the block (nothing registered or launched): "
                                  + "; ".join(problems)}
        return True

    def _launch_paid_checked(self, row, attempt) -> tuple:
        """W7C-R1-3 (ruling W7C-close-1): just before a paid launch, the month-turn hold again on a fresh clock reading
        (the wave's gate may have read it before 23:30 UTC). On a refusal nothing is launched: the take is committed
        `failed` with drive_started false (so a restart re-drives it, no ruling needed), and the loop stops blocked
        naming the hold. Once the loop has stopped, no later take of the wave is launched either."""
        if self.stopped is not None:
            return None, MoneyGateRefused(f"not launched: the loop stopped before it ({self.stopped['reason']})")
        if bills_money(row):
            why = hold_problem(row, read_clock(self.clock), self._block_trim.get("trimmed"))
            if why is not None:
                self.stopped = {"slot": row["slot"], "attempt": attempt, "state": labels4.BLOCKED,
                                "reason": f"the money gate refuses the launch (W7C-R1-3): {why}"}
                return None, MoneyGateRefused(why)
        return self._launch(row, attempt)

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
        """Register the wave's rows, one commit each, in row order. If one fails, stop with why, let the takes already
        open finish and commit them, then commit every row of the wave already registered as `failed`, and return
        False (W1B2-5; B19-5)."""
        registered = []
        for row, attempt in block:
            try:
                self.repo.register(row, attempt)
            except Exception as e:  # noqa: BLE001 - a register failure is a stop, never a sunk loop
                reason = f"register failed for slot {row['slot']} attempt {attempt}: {type(e).__name__}: {e}"
                if self.stopped is None:
                    self.stopped = {"slot": row["slot"], "attempt": attempt, "state": labels4.FAILED, "reason": reason}
                self._drain()                                # the older open takes commit first, in row order
                for r, a in registered:                      # nothing ran: re-driven on a restart (W1B3-1)
                    self._commit(r, a, self._outcome(r, a, None, state=labels4.FAILED, reason=reason,
                                                     drive_started=False))
                return False
            registered.append((row, attempt))
        return True

    def _commit(self, row, attempt, outcome) -> dict:
        """Decide the take's fate, seal its mask, commit it: the one road every outcome takes to the repo."""
        if outcome["state"] == labels4.PAUSE:
            outcome["window_event"] = self._window_event()   # W1B3-5: one per wait for the window (B19-5)
        outcome.update(self._decide(row, attempt, outcome))   # the fate, before the commit
        if outcome["leaked_container"] is not None:          # A LEAK (W1B3-1): the route's fate kept, the loop stops
            outcome["stop"] = outcome["stop"] or outcome["reason"]
            if self.stopped is None:
                self.stopped = {"slot": row["slot"], "attempt": attempt, "state": outcome["state"],
                                "reason": outcome["stop"]}
        self._nightly(row, attempt, outcome)
        self._seal(outcome)
        try:
            self.repo.commit_records(row, attempt, outcome)
        except Exception as e:  # noqa: BLE001
            closed = self.closed_cells.get(row["half_cell"])   # a cell closes only by a committed record
            night = outcome["stop"] if (outcome["stop"] or "").startswith(NIGHTLY_STOP) else None
            outcome = dict(outcome, state=labels4.FAILED, reason=f"commit failed: {e}",
                           final=False, rerun=False,
                           stop=(f"{night}; commit failed: {e}" if night else f"commit failed: {e}"), window_event=None,
                           cell_state=labels4.INCOMPLETE_MECHANICAL if closed else None, cell_reason=closed)
            self._seal(outcome)
            self._stop(row, attempt, outcome)
        else:
            self._note_committed(outcome)
            self._count_night(outcome)
        self.outcomes.append(outcome)
        return outcome

    def _count_night(self, o) -> None:
        """THE NIGHTLY STOP: one committed outcome counted (a harness-error; or, apart, a take failed after its drive
        started, which the rule never consumes). The harness-error that brings the window to the count is recorded."""
        if o["state"] == labels4.HARNESS_ERROR:
            self.night_counts["harness_error"] += 1
            if self.night_counts["harness_error"] == NIGHTLY_HARNESS_ERRORS:
                self.night_reaching = (o["slot"], o["attempt"])
        elif o["state"] == labels4.FAILED and o["drive_started"] is True:
            self.night_counts["failed_after_drive_started"] += 1

    @classmethod
    def _night_walk(cls, history):
        """THE NIGHTLY STOP over a history in commit order: (the counting state, problems). Each committed night ruling
        must be closed (exactly NIGHT_RULING_KEYS, `by` as THE RULINGS' `by`), come while the window's count is at the
        registered number, and name the harness-error that brought it there; it closes that window. The counting is
        _count_night's, on a bare state object, so one counter serves the loop and every reader."""
        w = object.__new__(cls)
        w.night_counts = {"harness_error": 0, "failed_after_drive_started": 0}
        w.night_reaching = None
        p = []
        for i, e in enumerate(history if isinstance(history, list) else []):
            if is_night_ruling(e):
                if set(e) != set(NIGHT_RULING_KEYS):
                    p.append(f"history[{i}]: a night ruling must hold exactly {list(NIGHT_RULING_KEYS)}")
                elif not (isinstance(e["by"], str) and e["by"].strip()):
                    p.append(f"history[{i}]: a night ruling names who made it (`by`), got {e['by']!r}")
                elif w.night_counts["harness_error"] < NIGHTLY_HARNESS_ERRORS:
                    p.append(f"history[{i}]: a night ruling with no {NIGHTLY_STOP} pending "
                             f"({w.night_counts['harness_error']} harness-errors in its window)")
                elif (e["slot"], e["attempt"]) != w.night_reaching:
                    p.append(f"history[{i}]: a night ruling names slot {e['slot']!r} attempt {e['attempt']!r}, not the "
                             f"harness-error that reached the count, {w.night_reaching!r}")
                else:
                    w.night_counts["harness_error"] = 0
                    w.night_reaching = None
            elif is_outcome(e) and "state" in e:
                w._count_night(e)
        return w, p

    def _replay_night(self, history) -> None:
        """THE NIGHTLY STOP on a restart: the walk's state, or the history refused. The stop is pending when the count
        is at the number at the end, wherever the stop text was committed, or whether it was."""
        w, p = self._night_walk(history)
        if p:
            raise BatchConfigError("the repo's history cannot be trusted: " + "; ".join(p))
        self.night_counts, self.night_reaching = w.night_counts, w.night_reaching
        self.nightly_stop_pending = self.night_counts["harness_error"] >= NIGHTLY_HARNESS_ERRORS

    def _nightly(self, row, attempt, outcome) -> None:
        """THE NIGHTLY STOP: when the harness-errors of this night (D-4-1), this take's included, reach the registered
        count, the last open take's outcome carries the stop (B19-5: the take launched last, the block's last with
        equal durations) and the loop stops once it is committed, for a ruling."""
        reached = self.night_counts["harness_error"] + (outcome["state"] == labels4.HARNESS_ERROR)
        if reached >= NIGHTLY_HARNESS_ERRORS:
            self._night_reached = True
        if getattr(self, "_night_reached", False) and self._block_last == (row["slot"], attempt):
            why = (f"{NIGHTLY_STOP}: {reached} harness-errors committed this night (D-4-1), the registered count is "
                   f"{NIGHTLY_HARNESS_ERRORS}; the run stops for a ruling")
            outcome["stop"] = why + (f"; {outcome['stop']}" if outcome["stop"] else "")
            if self.stopped is None:
                self.stopped = {"slot": row["slot"], "attempt": attempt, "state": outcome["state"], "reason": why}

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
        """The usage-window event of the pauses committed since the last wait for the window: a new one at the first,
        shared by the rest (W1B3-5; B19-5)."""
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
        if launch_error is not None and getattr(launch_error, "needs_ruling", False) is True:
            # Review NOTE 6 (glitch-06): a pre-launch refusal a restart would only meet again (a refused settings
            # baseline, a failed grant): nothing ran, and it stops for a ruling, never re-driven on its own.
            out = self._outcome(row, attempt, cid, state=labels4.BLOCKED,
                                reason=f"failed before launch, a ruling needed: {launch_error}", drive_started=False)
        elif launch_error is not None:                     # nothing ran: re-driven on a restart (W1B3-1)
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
                                 reason=f"{PIN_BLOCK_PREFIX}{got!r} is not the registered row's pre-registered "
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
        """The take's fate, from its state's handler. In a half-cell that has already closed (a take open when it
        closed, B19-5), never a re-run, and the cell state is carried (glitch-f3's cap ruling)."""
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
    # Lane run-launcher (glitch-f1's rulings on DESIGN-run-launcher.md, 22 Oct 2026): the counted run's road. The
    # frozen take_order filtered to the run's arms (a deferred arm only after its go record), built by run_builders.
    ap.add_argument("--run", action="store_true", help="drive the frozen take_order's remaining rows of the run's arms")
    ap.add_argument("--arms", help="with --run: narrow the run's arms (comma-separated), never widen them")
    ap.add_argument("--limit", type=int, help="with --run: drive at most this many rows of the frozen order")
    args = ap.parse_args(argv)
    if (args.arms is not None or args.limit is not None) and not args.run:     # NIT-1 (review of run-launcher S)
        print("batch: --arms and --limit go with --run", file=sys.stderr)
        return 2
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
    if args.run:
        import run_builders
        return run_builders.run_main(arms=args.arms, limit=args.limit, serial=args.serial)
    print("batch: no driver exists yet; the sealed box's driver arrives in CP2", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
