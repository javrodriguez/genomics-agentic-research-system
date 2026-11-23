#!/usr/bin/env python3
"""batch.py's rolling window (lane vendor-b19, glitch-26's rulings B19-1 and B19-3): red tests, no green yet.

B19-1: at most three drives at once, and a new row starts as soon as any drive finishes, in the frozen row order;
registration stays serial and in row order before each launch; commits stay serial and in row order (a drive that
finishes before an earlier row's drive waits for it); re-runs are requeued first, in row order; and with every drive's
duration equal, the rolling run drives, registers and commits exactly the rows, attempts and outcomes the block run
does, in the same order. The design note is lane-reports/B19-DESIGN-NOTE.md.

The drives are stubs on agent_adapter.ScriptedAdapter (test_batch's scenarios): no model, no container, no drive.py.
A drive's duration is a number of UNITs of sleep; one drive in three is ten times slower than the others. Equal
durations are modelled as drives of one launch wave that end together: the stub repo's commit waits (up to WAIT_S, a
hang detector) until every future in the loop's open deque is done (B19-13: no sleep), so a loop that commits every
drive that has ended, in row order, before it fills a slot sees the whole wave ended (the tie rule, design note
section 3). Equal durations here are drives the loop observes finished at one reading; real drives of equal length
may roll.

On today's code (blocks of three) the tests that pin the rolling start are red, by design: the block waits for its
slowest drive before it registers the next row. The rest are green today and pin what the rolling window keeps.

Round 2 (glitch-26's rulings B19-5 to B19-9): the equal-duration equivalence also compares check_results' window
events and pause counts per half-cell (B19-6); and, red on the block loop of 94963ea7, check_results' window span
and its ruled pause counted as its own event (proposal 7), takes.py's live set, MAX_OPEN and clean-tree registration
(proposal 6, on test_pipeline's scratch repositories), the open takes bounded by MAX_OPEN while three drives run, and
a run stopped with twelve takes open restarting owing exactly those takes, in row order (B19-9).

Round 3 (glitch-26's rulings B19-12 to B19-14): the holds read from a finished drive whose commit waits behind a slow
head (a stop, the nightly count, a half-cell closing at its cap), each pinned by a check that witnesses of batch.py
(WITNESSES, the review's mutants, each alone) turn red; and the nightly stop's carrier set once the wave is launched.
"""

from __future__ import annotations

import collections
import copy
import inspect
import itertools
import os
import sys
import threading
import time
import unittest

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agent_adapter as aa  # noqa: E402
import batch  # noqa: E402
import check_results as cr  # noqa: E402
import takes  # noqa: E402
from graders import labels4  # noqa: E402
import test_batch as tb  # noqa: E402  (its scenarios, rows, table, repo and window fakes)
import test_pipeline as tp  # noqa: E402  (its scratch repositories, rows, outcomes and records)

UNIT = 0.1         # one fast drive's duration, in seconds
SLOW = 10          # the slow drive's duration, in UNITs: ten times slower
WAIT_S = 30.0      # a hang detector, never a timing assumption
RUN_S = 120.0      # the whole run's hang detector


class TimedDriver:
    """launch / drive / remove, each drive taking `units` UNITs of sleep (slot -> UNITs for its first attempt; every
    other drive takes one). `plan` maps (slot, attempt) to a test_batch scenario (default clean). With `equal` (B19-13)
    a wave's drives other than its head end only once the head's commit has begun (test_batch's World.wait_head), so
    the loop observes the whole wave finished at one reading, never a part of it."""

    equal = False

    def __init__(self, world, plan=None, units=None):
        self.world, self.plan, self.units = world, plan or {}, units or {}
        self.wave_of = {}                              # slot -> the wave (World.block) it was launched in
        self.in_flight = self.max_in_flight = 0
        self.lock = threading.Lock()
        self.idle = threading.Condition(self.lock)
        self.attempts = collections.Counter()
        self.ids = itertools.count(1)

    def launch(self, row):
        cid = f"ctr-{next(self.ids):04d}"
        self.wave_of[row["slot"]] = self.world.block
        self.world.log("launch", row["slot"], cid)
        return cid

    def drive(self, row, cid):
        with self.lock:
            self.attempts[row["slot"]] += 1
            attempt = self.attempts[row["slot"]]
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            self.world.log("drive-start", row["slot"], attempt, self.in_flight)
        try:
            time.sleep(UNIT * (self.units.get(row["slot"], 1) if attempt == 1 else 1))
            if self.equal:                             # B19-13: the wave ends at one reading, its head first
                self.world.wait_head(self.wave_of[row["slot"]], row["slot"], WAIT_S)
            name = self.plan.get((row["slot"], attempt), "clean")
            turns, box = tb.ALL[name]
            adapter = aa.ScriptedAdapter(turns, container_id=cid)
            adapter.start_take(row)
            results = [adapter.turn(f"line {i}", first=(i == 0), budget_s=1) for i in range(len(turns))]
            adapter.end_take()
            self.world.texts[(row["slot"], attempt)] = "\n".join(r.text for r in results)
            harness = row["agent"]["harness"]
            pin = dict(tb.PROFILES[harness][row["model"]], model=row["model"], harness=harness)
            return aa.harness_records(results, pin=pin, box=box)
        finally:
            with self.lock:
                self.in_flight -= 1
                self.world.log("drive-end", row["slot"], attempt)
                self.idle.notify_all()

    def remove(self, cid):
        self.world.log("remove", cid)

    def wait_idle(self) -> None:
        with self.lock:
            if not self.idle.wait_for(lambda: self.in_flight == 0, WAIT_S):
                raise RuntimeError("a drive never ended (hang detector)")


class EqualRepo(tb.FakeRepo):
    """Equal durations: a commit waits until every future in the loop's open deque is done (the tie rule, B19-13)."""

    driver = loop = None

    def commit_records(self, row, attempt, outcome):
        tb.wait_open(self.loop, WAIT_S)
        super().commit_records(row, attempt, outcome)


def drive_run(row_list, plan=None, units=None, equal=False, mod=batch, cls=None, driver=None, repo=None):
    """One run of batch.Batch on the stubs, under the hang detector: (loop, outcomes, world, driver, repo, window).
    Round 3: `mod` is batch.py or a witness of it; `cls`, `driver` and `repo` replace the loop, driver and repo."""
    w = tb.World()
    d = (driver or TimedDriver)(w, plan, units)
    d.equal = equal
    r = (repo or (EqualRepo if equal else tb.FakeRepo))(w)
    r.driver = d
    win = tb.FakeWindow(w)
    b = (cls or mod.Batch)(d, r, win, table=tb.test_table())
    r.loop = b                                         # EqualRepo reads the loop's open deque (B19-13)
    got = {}
    t = threading.Thread(target=lambda: got.setdefault("out", b.run(row_list)), daemon=True)
    t.start()
    t.join(RUN_S)
    if t.is_alive():
        raise AssertionError("the run never ended (hang detector)")
    return b, got["out"], w, d, r, win


def at(events, *head):
    """The log index of the first event that starts with `head`."""
    for e in events:
        if e[1:1 + len(head)] == head:
            return e[0]
    raise AssertionError(f"no event {head!r} in the log")


def trace(events, outcomes):
    """What B19-1's equivalence compares: the registrations, the launches, the commits (with every fate key) and the
    window waits (as the number of registrations before each), each in its order."""
    regs = [e[2:4] for e in events if e[1] == "register"]
    launches = [e[2] for e in events if e[1] == "launch"]
    commits = [(o["slot"], o["attempt"], o["state"], o["final"], o["rerun"], o["beyond_cap"], o["window_event"],
                o["stop"], o["cell_state"]) for o in outcomes]
    n, waits = 0, []
    for e in events:
        if e[1] == "register":
            n += 1
        elif e[1] == "reset":
            waits.append(n)
    return {"registrations": regs, "launches": launches, "commits": commits, "waits": waits, **published(outcomes)}


def published(outcomes):
    """B19-6: check_results' reading of the committed outcomes, compared too: its window problems, the window events
    each half-cell counts, and the pause count each half-cell publishes."""
    pub = cr.publication(outcomes, tb.test_table())
    return {"window_problems": cr.window_problems(outcomes), "window_events": pub["window_events"],
            "pause_counts": {cell: len(events) for cell, events in pub["window_events"].items()}}


def slow_head_rows(n=9):
    return tb.rows_in(["hc-a", "hc-b", "hc-c"] * (n // 3))


class TestRollingStart(unittest.TestCase):
    """One drive in three is ten times slower: the next rows start before it ends (red on the block loop)."""

    def setUp(self):
        self.b, self.out, self.w, self.d, self.r, self.win = drive_run(slow_head_rows(), units={1: SLOW})

    def test_the_next_row_starts_before_the_slow_drive_ends(self):
        ev = self.w.events
        self.assertLess(at(ev, "drive-start", 4), at(ev, "drive-end", 1, 1),
                        "slot 4's drive starts only after slot 1's slow drive ends: the block waits for its slowest")

    def test_both_freed_slots_are_filled_while_the_slow_drive_runs(self):
        ev = self.w.events
        end1 = at(ev, "drive-end", 1, 1)
        for slot in (4, 5):
            self.assertLess(at(ev, "register", slot, 1), end1, f"slot {slot} is registered only after slot 1 ends")
            self.assertLess(at(ev, "drive-start", slot), end1, f"slot {slot}'s drive starts only after slot 1 ends")

    def test_three_drives_run_beside_the_slow_one_after_its_block_mates_end(self):
        ev = self.w.events
        end1 = at(ev, "drive-end", 1, 1)
        after_mates = max(at(ev, "drive-end", 2, 1), at(ev, "drive-end", 3, 1))
        full = [e for e in ev if e[1] == "drive-start" and after_mates < e[0] < end1 and e[4] == 3]
        self.assertTrue(full, "no third drive runs beside slot 1 once slots 2 and 3 have ended")

    def test_never_more_than_three_drives_at_once(self):
        self.assertLessEqual(self.d.max_in_flight, batch.BLOCK)
        self.assertEqual(self.d.max_in_flight, batch.BLOCK)

    def test_every_row_is_driven_once_and_graded(self):
        self.assertEqual([(o["slot"], o["attempt"], o["state"]) for o in self.out],
                         [(s, 1, labels4.GRADED) for s in range(1, 10)])
        self.assertIsNone(self.b.stopped)


class TestRowOrder(unittest.TestCase):
    """Registration before launch and commits, each serial and in row order, with a slow head (green today)."""

    def setUp(self):
        self.b, self.out, self.w, self.d, self.r, self.win = drive_run(slow_head_rows(), units={1: SLOW})

    def test_commits_in_row_order_and_a_finished_drive_waits_for_an_earlier_row(self):
        ev = self.w.events
        self.assertEqual([e[2:4] for e in ev if e[1] == "commit"], [(s, 1) for s in range(1, 10)])
        end1 = at(ev, "drive-end", 1, 1)
        self.assertLess(at(ev, "drive-end", 2, 1), end1)
        self.assertGreater(at(ev, "commit", 2, 1), at(ev, "commit", 1, 1))
        for e in ev:
            if e[1] == "commit":
                self.assertGreater(e[0], at(ev, "drive-end", e[2], e[3]), f"slot {e[2]} committed before its end")

    def test_registration_in_row_order_and_before_each_launch(self):
        ev = self.w.events
        self.assertEqual([e[2:4] for e in ev if e[1] == "register"], [(s, 1) for s in range(1, 10)])
        self.assertEqual([e[2] for e in ev if e[1] == "launch"], list(range(1, 10)))
        for s in range(1, 10):
            self.assertLess(at(ev, "register", s, 1), at(ev, "launch", s))

    def test_registrations_and_commits_never_overlap(self):
        self.assertEqual(self.r.overlaps, 0)


class TestRerunRequeue(unittest.TestCase):
    """A re-run is requeued first, in row order, before every row not yet registered, with a slow head."""

    def test_the_rerun_is_the_next_registration_after_its_commit(self):
        plan = {(2, 1): "preflight-fail"}                     # a rehearsal: re-run in the same slot
        self.assertEqual(tb.scenario_state("preflight-fail", tb.test_table()), labels4.REHEARSAL)
        b, out, w, d, r, win = drive_run(slow_head_rows(), plan=plan, units={1: SLOW})
        ev = w.events
        c = at(ev, "commit", 2, 1)
        nxt = [e[2:4] for e in ev if e[1] == "register" and e[0] > c]
        self.assertEqual(nxt[0], (2, 2), "the re-run is not the next row registered after its commit")
        self.assertEqual(sorted((o["slot"], o["attempt"]) for o in out),
                         sorted([(s, 1) for s in range(1, 10)] + [(2, 2)]))


# The block run's trace for each equal-duration scenario, read from batch.py at 7dc0cf9e (blocks of three): the rows,
# attempts and outcomes the rolling run must reproduce, in the same order (B19-1).
G, R, P, H, A = labels4.GRADED, labels4.REHEARSAL, labels4.PAUSE, labels4.HARNESS_ERROR, labels4.ABORTED
NIGHT = (f"{batch.NIGHTLY_STOP}: 3 harness-errors committed this night (D-4-1), the registered count is "
         f"{batch.NIGHTLY_HARNESS_ERRORS}; the run stops for a ruling")
EQUAL = {
    "reruns, a shared pause and an abort": (
        9,
        {(2, 1): "preflight-fail", (3, 1): "oom", (4, 1): "rate-limit", (5, 1): "usage-limit-text",
         (7, 1): "watcher-overflow"},
        {"registrations": [(1, 1), (2, 1), (3, 1), (2, 2), (4, 1), (5, 1), (4, 2), (5, 2), (6, 1), (7, 1), (8, 1),
                           (9, 1), (7, 2)],
         "launches": [1, 2, 3, 2, 4, 5, 4, 5, 6, 7, 8, 9, 7],
         "commits": [(1, 1, G, True, False, False, None, None, None),
                     (2, 1, R, False, True, False, None, None, None),
                     (3, 1, A, True, False, False, None, None, None),
                     (2, 2, G, True, False, False, None, None, None),
                     (4, 1, P, False, True, False, 1, None, None),
                     (5, 1, P, False, True, False, 1, None, None),
                     (4, 2, G, True, False, False, None, None, None),
                     (5, 2, G, True, False, False, None, None, None),
                     (6, 1, G, True, False, False, None, None, None),
                     (7, 1, H, False, True, False, None, None, None),
                     (8, 1, G, True, False, False, None, None, None),
                     (9, 1, G, True, False, False, None, None, None),
                     (7, 2, G, True, False, False, None, None, None)],
         "waits": [6],
         "window_problems": [], "window_events": {"hc-a": [("window", 1)], "hc-b": [("window", 1)]},
         "pause_counts": {"hc-a": 1, "hc-b": 1}}),
    "the nightly stop carried by the wave's last row": (
        6,
        {(1, 1): "watcher-overflow", (2, 1): "agent-says-rate-limit", (1, 2): "watcher-overflow"},
        {"registrations": [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (4, 1)],
         "launches": [1, 2, 3, 1, 2, 4],
         "commits": [(1, 1, H, False, True, False, None, None, None),
                     (2, 1, H, False, True, False, None, None, None),
                     (3, 1, G, True, False, False, None, None, None),
                     (1, 2, H, True, False, True, None, None, None),
                     (2, 2, G, True, False, False, None, None, None),
                     (4, 1, G, True, False, False, None, NIGHT, None)],
         "waits": [],
         "window_problems": [], "window_events": {}, "pause_counts": {}}),
}


class TestEqualDurations(unittest.TestCase):
    """With every drive's duration equal, the rolling run is the block run: rows, attempts, outcomes, in order."""

    def test_each_scenario_reproduces_the_block_run(self):
        for name, (n, plan, want) in EQUAL.items():
            with self.subTest(name):
                b, out, w, d, r, win = drive_run(tb.rows_in(["hc-a", "hc-b", "hc-c"] * (n // 3)), plan=plan,
                                                 equal=True)
                self.assertEqual(trace(w.events, out), want)
                self.assertEqual(r.overlaps, 0)

    def test_the_equivalence_check_can_fail(self):
        """A mutant that drives one row at a time (serial) breaks the waits' places, so the comparison goes red."""
        n, plan, want = EQUAL["reruns, a shared pause and an abort"]
        w = tb.World()
        d = TimedDriver(w, plan)
        d.equal = True
        r = EqualRepo(w)
        r.driver = d
        b = batch.Batch(d, r, tb.FakeWindow(w), table=tb.test_table(), serial=True)
        r.loop = b
        out = b.run(tb.rows_in(["hc-a", "hc-b", "hc-c"] * (n // 3)))
        self.assertNotEqual(trace(w.events, out), want)


# ------------------------------------------------------------------------------------------------- round 2
MAX_OPEN = getattr(batch, "MAX_OPEN", 12)     # B19-5; read from batch.py once the green lands
P = labels4.PAUSE


def minimal(slot, state=G, event=None, attempt=1, half_cell="hc-a"):
    """The fields check_results.window_problems reads from a committed outcome."""
    return {"slot": slot, "attempt": attempt, "state": state, "window_event": event, "half_cell": half_cell}


class TestWindowSpan(unittest.TestCase):
    """B19-5 (proposal 7), B19-8: a window event holds at most BLOCK pauses, no slot twice, within at most MAX_OPEN
    consecutive outcomes and with no other event's pause between them. A rolling run commits the takes that were open
    when the first pause was seen between its pauses."""

    def test_a_rolling_event_spanning_more_than_a_block_is_accepted(self):
        rolled = [minimal(1, P, 1), minimal(2), minimal(3), minimal(4), minimal(5, P, 1), minimal(6, P, 1)]
        self.assertEqual(cr.window_problems(rolled), [])
        widest = [minimal(1, P, 1)] + [minimal(s) for s in range(2, MAX_OPEN)] + [minimal(MAX_OPEN, P, 1)]
        self.assertEqual(len(widest), MAX_OPEN)
        self.assertEqual(cr.window_problems(widest), [])

    def test_what_no_rolling_run_commits_is_still_refused(self):
        refused = {
            "a span past MAX_OPEN": [minimal(1, P, 1)] + [minimal(s) for s in range(2, MAX_OPEN + 1)]
                                    + [minimal(MAX_OPEN + 1, P, 1)],
            "four pauses in one event": [minimal(1, P, 1), minimal(2), minimal(3, P, 1), minimal(4, P, 1),
                                         minimal(5, P, 1)],
            "a slot twice in the span": [minimal(1, P, 1), minimal(2), minimal(2, attempt=2), minimal(3, P, 1)],
            "another event between": [minimal(1, P, 1), minimal(2, P, 2), minimal(3, P, 1)],
        }
        for name, history in refused.items():
            with self.subTest(name):
                self.assertNotEqual(cr.window_problems(history), [])

    def test_a_rolling_run_shares_one_event_across_the_takes_committed_between(self):
        """Slot 1 pauses after six units; slots 6 and 7 start once 4 and 5 end and pause after it: every pause of the
        three drives in flight shares event 1, with slots 2 to 5 committed between them, and check_results accepts."""
        plan = {(1, 1): "rate-limit", (6, 1): "rate-limit", (7, 1): "rate-limit"}
        b, out, w, d, r, win = drive_run(slow_head_rows(), plan=plan, units={1: 6, 6: 8, 7: 8})
        first = [(o["slot"], o["state"], o["window_event"]) for o in out if o["attempt"] == 1]
        self.assertEqual(first, [(1, P, 1), (2, G, None), (3, G, None), (4, G, None), (5, G, None), (6, P, 1),
                                 (7, P, 1), (8, G, None), (9, G, None)])
        self.assertEqual(cr.window_problems(out), [])
        self.assertEqual(published(out)["pause_counts"], {"hc-a": 1, "hc-c": 1})
        self.assertEqual(win.resets, 1)
        ev = w.events
        self.assertLess(at(ev, "commit", 7, 1), at(ev, "reset"))
        self.assertGreater(at(ev, "register", 8, 1), at(ev, "reset"))


class TestRuledPauseOwnEvent(unittest.TestCase):
    """B19-5 (proposal 7) and B19-6: a pause a ruling routes counts as its own event in its half-cell, in publication
    as in batch's own count, where a block run would have merged it with its block's window event."""

    def test_publication_counts_the_ruled_pause_as_batch_does(self):
        stopped = tp.outcome(tp.row(2), state=labels4.FAILED, final=False)
        history = [tp.recorded(P, tp.row(1)), stopped, tp.recorded(P, tp.row(3)), tp.ruling(tp.row(2))]
        got = cr.publication(history, tp.table())
        strict = batch.Batch(None, None, None, table=tp.table(), history=history)
        self.assertEqual(set(got["window_events"]["c1"]), {("window", 1), ("take", "s2", 1)})
        self.assertEqual(set(got["window_events"]["c1"]), strict.cell_events[("c1", P)])
        self.assertEqual(next(o for o in got["attempts"] if o["slot"] == "s2").get("note"), cr.STRICT_PAUSE_NOTE)


class TestLiveSet(unittest.TestCase):
    """B19-5 (proposal 6), B19-8: takes.py's open-row rule. A row joins the live set at its registration and leaves it
    at its commit; at most MAX_OPEN rows are open; a restart never inherits the live set."""

    def test_max_open_is_the_open_row_limit(self):
        self.assertEqual(getattr(batch, "MAX_OPEN", None), 12)
        self.assertEqual(takes.OPEN_LIMIT, batch.MAX_OPEN)

    def test_a_registration_lands_while_other_rows_are_open(self):
        with tp.repository() as repo:
            for n in (1, 2, 3):
                repo.register(tp.row(n), 1)
            repo.commit_records(tp.row(1), 1, tp.outcome(tp.row(1)))
            repo.register(tp.row(4), 1)                        # slots 2 and 3 still open
            repo.commit_records(tp.row(2), 1, tp.outcome(tp.row(2)))
            repo.register(tp.row(5), 1)
            self.assertEqual(repo.guard.live, {("s3", 1), ("s4", 1), ("s5", 1)})

    def test_twelve_open_and_never_thirteen(self):
        with tp.repository() as repo:
            for n in range(1, MAX_OPEN + 1):
                repo.register(tp.row(n), 1)
            with self.assertRaisesRegex(ValueError, f"at most {MAX_OPEN} open"):
                repo.register(tp.row(MAX_OPEN + 1), 1)
            repo.commit_records(tp.row(1), 1, tp.outcome(tp.row(1)))
            repo.register(tp.row(MAX_OPEN + 1), 1)
            self.assertEqual(len(repo.guard.live), MAX_OPEN)

    def test_a_restart_never_inherits_the_live_set(self):
        with tp.repository() as repo:
            for n in (1, 2):
                repo.register(tp.row(n), 1)
            restarted = tp.FakeRepo(repo.root)
            with self.assertRaisesRegex(ValueError, "registered.*outcome"):
                restarted.register(tp.row(3), 1)


class TestCleanTreeRegistration(unittest.TestCase):
    """B19-5 (proposal 6), B19-8: a registration refuses an unclean tree except the untracked folders of the live set's
    open takes, each takes/<slot>/<attempt>/; anything else still refuses."""

    @staticmethod
    def planned(n):
        return tp.row(1, slot=f"s{n}")                         # one cell identity, distinct slots

    def registered(self, repo, guard, *ns):
        pre = {"rows": [self.planned(n) for n in range(1, 10)]}
        for n in ns:
            takes.commit_registration(self.planned(n), 1, guard=guard, root=repo.root, repo=repo.root, pre=pre)
        return pre

    def write(self, repo, rel, text="synthetic record\n"):
        path = repo.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def scratch(self):
        repo = tp.repository()
        got = repo.__enter__()
        self.addCleanup(repo.__exit__, None, None, None)
        (got.root / "prereg.json").write_text("{}\n")
        tp.commit(got.root, ["prereg.json"], "Record synthetic design")
        return got

    def test_an_open_takes_folder_does_not_refuse_the_next_registration(self):
        repo, guard = self.scratch(), takes.RegistrationGuard()
        pre = self.registered(repo, guard, 1)
        self.write(repo, "takes/s1/1/transcript.jsonl")
        self.write(repo, "takes/s1/1/nested/ledger.json")
        takes.commit_registration(self.planned(2), 1, guard=guard, root=repo.root, repo=repo.root, pre=pre)
        self.assertEqual(guard.live, {("s1", 1), ("s2", 1)})

    def test_anything_else_unclean_still_refuses(self):
        cases = {
            "a stray file": "stray.txt",
            "a take folder outside the live set": "takes/s9/1/transcript.jsonl",
            "another attempt of an open slot": "takes/s1/2/transcript.jsonl",
            "a file beside the take folders": "takes/s1/transcript.jsonl",
        }
        for name, rel in cases.items():
            with self.subTest(name):
                repo, guard = self.scratch(), takes.RegistrationGuard()
                pre = self.registered(repo, guard, 1)
                self.write(repo, rel)
                before = tp.git(repo.root, "rev-parse", "HEAD")
                with self.assertRaisesRegex(ValueError, "clean committed repository"):
                    takes.commit_registration(self.planned(2), 1, guard=guard, root=repo.root, repo=repo.root,
                                              pre=pre)
                self.assertEqual(tp.git(repo.root, "rev-parse", "HEAD"), before)

    def test_a_tracked_change_in_an_open_takes_folder_still_refuses(self):
        repo, guard = self.scratch(), takes.RegistrationGuard()
        pre = self.registered(repo, guard, 1)
        self.write(repo, "takes/s1/1/transcript.jsonl")
        tp.commit(repo.root, ["takes/s1/1/transcript.jsonl"], "Record synthetic file")
        self.write(repo, "takes/s1/1/transcript.jsonl", "changed\n")
        with self.assertRaisesRegex(ValueError, "clean committed repository"):
            takes.commit_registration(self.planned(2), 1, guard=guard, root=repo.root, repo=repo.root, pre=pre)

    def test_a_restart_or_a_committed_take_allows_no_folder(self):
        repo, guard = self.scratch(), takes.RegistrationGuard()
        pre = self.registered(repo, guard, 1)
        self.write(repo, "takes/s1/1/transcript.jsonl")
        with self.assertRaisesRegex(ValueError, "clean committed repository"):
            takes.commit_registration(self.planned(2), 1, guard=takes.RegistrationGuard(), root=repo.root,
                                      repo=repo.root, pre=pre)
        repo2, guard2 = self.scratch(), takes.RegistrationGuard()
        pre2 = self.registered(repo2, guard2, 1)
        repo2.commit_records(self.planned(1), 1, tp.outcome(self.planned(1)))
        self.write(repo2, "takes/s1/1/transcript.jsonl")
        with self.assertRaisesRegex(ValueError, "clean committed repository"):
            takes.commit_registration(self.planned(2), 1, guard=guard2, root=repo2.root, repo=repo2.root, pre=pre2)


class OpenRepo(tb.FakeRepo):
    """Counts the open takes (registered, outcome not committed) at every registration and commit."""

    def __init__(self, world, prior=None):
        super().__init__(world, prior)
        self.open = self.max_open = 0
        self.lock = threading.Lock()

    def register(self, row, attempt):
        super().register(row, attempt)
        with self.lock:
            self.open += 1
            self.max_open = max(self.max_open, self.open)

    def commit_records(self, row, attempt, outcome):
        super().commit_records(row, attempt, outcome)
        with self.lock:
            self.open -= 1


def run_open(row_list, plan=None, units=None, window=tb.FakeWindow, prior=None, driver=None):
    """One run of batch.Batch on the stubs with OpenRepo, under the hang detector."""
    w = tb.World()
    d = TimedDriver(w, plan, units) if driver is None else driver(w)
    r = OpenRepo(w, prior)
    win = window(w)
    b = batch.Batch(d, r, win, table=tb.test_table())
    got = {}
    t = threading.Thread(target=lambda: got.setdefault("out", b.run(row_list)), daemon=True)
    t.start()
    t.join(RUN_S)
    if t.is_alive():
        raise AssertionError("the run never ended (hang detector)")
    return b, got["out"], w, d, r, win


class TestOpenBound(unittest.TestCase):
    """B19-9: the open takes never exceed MAX_OPEN while the drives in flight never exceed three."""

    def test_open_takes_reach_max_open_and_no_more(self):
        b, out, w, d, r, win = run_open(tb.rows_in(["hc-a", "hc-b", "hc-c"] * 7), units={1: 30})
        self.assertEqual(r.max_open, MAX_OPEN)
        self.assertEqual(d.max_in_flight, batch.BLOCK)
        ev = w.events
        self.assertLess(at(ev, "register", MAX_OPEN, 1), at(ev, "drive-end", 1, 1))
        self.assertGreater(at(ev, "register", MAX_OPEN + 1, 1), at(ev, "commit", 1, 1),
                           "a thirteenth take opened while twelve were open")
        self.assertEqual([(o["slot"], o["attempt"], o["state"]) for o in out],
                         [(s, 1, G) for s in range(1, 22)])


class TestRestartOwesTheOpenTakes(unittest.TestCase):
    """B19-9: a run stopped with twelve takes open restarts owing exactly the open takes, in row order, under W1B3-6's
    owed-drive rule. Slot 1 drives long and pauses; slots 2 to 12, each in its own half-cell, rehearse (a re-run each)
    while it runs; the window then fails, so the loop stops once the twelve are committed."""

    ROWS = tb.rows_in([f"hc-{i}" for i in range(1, MAX_OPEN + 2)])
    PLAN = {(1, 1): "rate-limit", **{(s, 1): "preflight-fail" for s in range(2, MAX_OPEN + 1)}}

    def stopped(self):
        b, out, w, d, r, win = run_open(self.ROWS, plan=self.PLAN, units={1: 30}, window=tb.WindowFails)
        return b, out, r

    def test_the_stop_commits_twelve_open_takes_and_the_restart_owes_them_in_row_order(self):
        b, out, r = self.stopped()
        self.assertEqual(r.max_open, MAX_OPEN)
        self.assertIsNotNone(b.stopped)
        self.assertEqual([(o["slot"], o["state"], o["rerun"]) for o in out],
                         [(1, P, True)] + [(s, labels4.REHEARSAL, True) for s in range(2, MAX_OPEN + 1)])
        history = r.history()
        again = batch.Batch(TimedDriver(tb.World()), tb.FakeRepo(tb.World(), prior=history), tb.FakeWindow(tb.World()),
                            table=tb.test_table())
        self.assertEqual(sorted(again.owed), list(range(1, MAX_OPEN + 1)))
        self.assertEqual({s: a for s, (a, _) in again.owed.items()}, {s: 2 for s in range(1, MAX_OPEN + 1)})
        self.assertTrue(again.paused, "the restart does not wait for the usage window")
        problems = again.row_problems([x for x in self.ROWS if x["slot"] != 5])
        self.assertEqual([p for p in problems if "owes" in p],
                         ["the history owes slot 5 attempt 2 (its rehearsal is re-run), and the rows leave it out"])
        b2, out2, w2, d2, r2, win2 = run_open(self.ROWS, prior=history)
        ev = w2.events
        self.assertEqual([e[2:4] for e in ev if e[1] == "register"][:MAX_OPEN + 1],
                         [(s, 2) for s in range(1, MAX_OPEN + 1)] + [(MAX_OPEN + 1, 1)])
        self.assertLess(at(ev, "reset"), at(ev, "register", 1, 2))
        self.assertEqual({o["state"] for o in out2}, {G})

    def test_the_old_block_span_forgets_the_wait(self):
        """A mutant of restart_waits over the last BLOCK outcomes misses slot 1's pause, twelve back: red."""
        b, out, r = self.stopped()
        anchor = "[-MAX_OPEN:]" if "[-MAX_OPEN:]" in inspect.getsource(batch.restart_waits) else None
        self.assertIsNotNone(anchor, "restart_waits does not read the last MAX_OPEN outcomes")
        self.assertTrue(batch.restart_waits(r.history()))
        self.assertFalse(tb.restart_waits_mutant(anchor, "[-BLOCK:]")(r.history()))


# ------------------------------------------------------------------------------------------------- round 3
class RefusingRepo(tb.FakeRepo):
    """A register failure at slot 4: the wave it opens is never registered (W1B2-5)."""

    def register(self, row, attempt):
        if row["slot"] == 4:
            raise RuntimeError("synthetic register failure")
        super().register(row, attempt)


class RefusingBatch(batch.Batch):
    """The money gate refusing every wave from slot 4 on (W7C): the refusal's road in the loop, not its reasons."""

    def _money_gate(self, wave):
        row, attempt = wave[0]
        if row["slot"] < 4:
            return super()._money_gate(wave)
        self.stopped = {"slot": row["slot"], "attempt": attempt, "state": labels4.BLOCKED,
                        "reason": "synthetic money gate refusal"}
        return True


class TestNightlyCarrier(unittest.TestCase):
    """B19-14: the nightly stop's carrier is set once the wave is launched. Slots 1 to 3 end harness-errors, slot 1
    slow; the wave from slot 4 is refused by the money gate or fails to register while they are open; their commits
    bring the night's count to NIGHTLY_HARNESS_ERRORS, and the stop is carried by the last take launched, slot 3."""

    PLAN = {(s, 1): "watcher-overflow" for s in (1, 2, 3)}

    def test_a_refused_wave_leaves_no_carrier_on_an_uncommitted_row(self):
        self.assertEqual(batch.NIGHTLY_HARNESS_ERRORS, 3)
        for name, kw in {"the money gate refuses": dict(cls=RefusingBatch),
                         "a register failure": dict(repo=RefusingRepo)}.items():
            with self.subTest(name):
                b, out, w, d, r, win = drive_run(slow_head_rows(6), plan=self.PLAN, units={1: SLOW}, **kw)
                committed = [(o["slot"], o["attempt"]) for o in out]
                self.assertEqual(committed, [(1, 1), (2, 1), (3, 1)])
                self.assertIsNotNone(b.stopped)
                self.assertNotIn(4, [e[2] for e in w.events if e[1] == "launch"])
                self.assertIn(b._block_last, committed, "the nightly stop's carrier names a row never committed")
                self.assertEqual([(o["slot"], o["attempt"]) for o in out
                                  if (o["stop"] or "").startswith(batch.NIGHTLY_STOP)], [(3, 1)])


class StoppingDriver(TimedDriver):
    """TimedDriver whose drive raises for the slots in `fails` (the take fails) and whose container removal raises
    for the slots in `leaks` (A LEAK, W1B3-1)."""

    fails, leaks = (), ()

    def __init__(self, world, plan=None, units=None):
        super().__init__(world, plan, units)
        self.slot_of = {}

    def launch(self, row):
        cid = super().launch(row)
        self.slot_of[cid] = row["slot"]
        return cid

    def drive(self, row, cid):
        records = super().drive(row, cid)
        if row["slot"] in self.fails:
            raise RuntimeError("synthetic drive failure")
        return records

    def remove(self, cid):
        super().remove(cid)
        if self.slot_of[cid] in self.leaks:
            raise RuntimeError("synthetic removal failure")


class FailsTwo(StoppingDriver):
    fails = (2,)


class LeaksTwo(StoppingDriver):
    leaks = (2,)


def late(events, after, keep=lambda e: True):
    """The registrations (slot, attempt) logged after the event index `after`, those `keep` admits."""
    return [e[2:4] for e in events if e[1] == "register" and e[0] > after and keep(e)]


# B19-12 (the review's finding 1): the holds read from a finished drive whose commit waits behind a slow head. Each
# check returns problems, and each is run against witnesses of batch.py that must turn it red (WITNESSES).
STOPS = {"blocked": ({(2, 1): "unlisted-reason"}, None, labels4.BLOCKED),
         "failed": ({}, FailsTwo, labels4.FAILED),
         "leaking": ({}, LeaksTwo, labels4.GRADED)}


def stop_hold_problems(mod=batch) -> list:
    """Slot 2 ends blocked, failed or leaking behind slot 1's slow drive (slot 3 ends after it): nothing is registered
    after slot 2's drive ends, and the loop stops at its commit."""
    p = []
    for name, (plan, driver, state) in STOPS.items():
        b, out, w, d, r, win = drive_run(slow_head_rows(), plan=plan, units={1: SLOW, 3: 3}, mod=mod, driver=driver)
        ev, two = w.events, next(o for o in out if o["slot"] == 2)
        end = at(ev, "drive-end", 2, 1)
        if not end < at(ev, "drive-end", 3, 1) < at(ev, "drive-end", 1, 1):
            p.append(f"{name}: slot 2 does not end first, behind the slow head (the scenario did not happen)")
        if (two["state"], two["leaked_container"] is not None) != (state, name == "leaking") or b.stopped is None:
            p.append(f"{name}: slot 2 committed {two['state']} (leak {two['leaked_container']!r}), loop stopped "
                     f"{b.stopped is not None}")
        if late(ev, end):
            p.append(f"{name}: {late(ev, end)} registered after slot 2's drive ended {name} behind the slow head")
    return p


def nightly_hold_problems(mod=batch) -> list:
    """Slots 2, 3 and 4 end harness-errors behind slot 1's slow drive; slot 4's brings the night's count to
    NIGHTLY_HARNESS_ERRORS while slot 5, launched last, still runs: nothing is registered after slot 4's drive ends,
    and the stop is carried by slot 5, the last take launched."""
    plan = {(s, 1): "watcher-overflow" for s in (2, 3, 4)}
    b, out, w, d, r, win = drive_run(slow_head_rows(), plan=plan, units={1: SLOW, 3: 2, 4: 2, 5: 4}, mod=mod)
    ev, p = w.events, []
    end = at(ev, "drive-end", 4, 1)
    if not (at(ev, "drive-end", 3, 1) < end < at(ev, "drive-end", 5, 1) < at(ev, "drive-end", 1, 1)):
        p.append("slot 4 does not reach the count behind the slow head with slot 5 running (no scenario)")
    if late(ev, end):
        p.append(f"{late(ev, end)} registered after slot 4's harness-error reached the nightly count")
    last = [e[2] for e in ev if e[1] == "launch"][-1]
    carried = [(o["slot"], o["attempt"]) for o in out if (o["stop"] or "").startswith(batch.NIGHTLY_STOP)]
    if carried != [(last, 1)] or b.stopped is None:
        p.append(f"the nightly stop is carried by {carried}, not by the last take launched, slot {last}")
    return p


CLOSING_ROWS = tb.rows_in(["hc-a", "hc-b", "hc-b", "hc-b", "hc-b", "hc-c", "hc-b", "hc-c", "hc-a"])


def closing_hold_problems(mod=batch) -> list:
    """Slots 2, 3 and 4 of hc-b rehearse behind slot 1's slow drive; slot 4's is the third, hc-b's cap: no further
    row of hc-b is registered between slot 4's drive end and its commit, which closes the half-cell (slot 7 dropped).
    (A pause behind the slow head holds every launch already: test_batch's pause test.)"""
    cap = batch.half_cell_cap(tb.test_table(), labels4.REHEARSAL)
    plan = {(s, 1): "preflight-fail" for s in (2, 3, 4)}
    b, out, w, d, r, win = drive_run(CLOSING_ROWS, plan=plan, units={1: SLOW, 3: 2, 4: 3, 6: 5}, mod=mod)
    ev, p = w.events, []
    end, commit = at(ev, "drive-end", 4, 1), at(ev, "commit", 4, 1)
    if cap != 3 or not at(ev, "drive-end", 5, 1) < end < at(ev, "drive-end", 6, 1) < at(ev, "drive-end", 1, 1):
        p.append(f"slot 4 does not close hc-b (cap {cap}) behind the slow head with slot 6 running (no scenario)")
    early = late(ev, end, keep=lambda e: e[0] < commit and CLOSING_ROWS[e[2] - 1]["half_cell"] == "hc-b")
    if early:
        p.append(f"{early} of hc-b registered after slot 4's rehearsal closing it ended, before its commit")
    if b.closed_cells.get("hc-b") is None or 7 not in [s["slot"] for s in b.skipped]:
        p.append(f"hc-b not closed at slot 4's commit, or slot 7 not dropped: {b.closed_cells}, {b.skipped}")
    return p


CHECKS = {"stop-hold": stop_hold_problems, "nightly-hold": nightly_hold_problems,
          "closing-hold": closing_hold_problems}


class TestHoldsBehindASlowHead(unittest.TestCase):
    """B19-12: the stop, nightly and closing half-cell holds, read from finished drives behind a slow head."""

    def test_a_stop_behind_the_slow_head_registers_nothing_after_its_drive_end(self):
        self.assertEqual(stop_hold_problems(), [])

    def test_the_nightly_count_behind_the_slow_head_registers_nothing_after_it(self):
        self.assertEqual(nightly_hold_problems(), [])

    def test_a_half_cell_closing_behind_the_slow_head_registers_none_of_its_rows_before_its_commit(self):
        self.assertEqual(closing_hold_problems(), [])


# name: (edits to batch.py, the bound check). The review's mutants of finding 1, each alone.
HELD_STOPS = ('o["state"] in (labels4.PAUSE, labels4.BLOCKED, labels4.FAILED) or o["leaked_container"] is not None',
              'o["state"] in (labels4.PAUSE,)')
HELD_NIGHT = ('        return self.night_counts["harness_error"] + errors >= NIGHTLY_HARNESS_ERRORS\n',
              '        return False\n')
WITNESSES = {
    "held-stops-dropped": ((HELD_STOPS,), "stop-hold"),
    "held-nightly-dropped": ((HELD_NIGHT,), "nightly-hold"),
    "held-pause-only-stops": ((HELD_STOPS, HELD_NIGHT), "stop-hold"),
    "held-pause-only-nightly": ((HELD_STOPS, HELD_NIGHT), "nightly-hold"),
    "closing-cells-empty": ((("        closing = self._closing_cells(finished)\n", "        closing = set()\n"),),
                            "closing-hold"),
}


def compiled(edits):
    """batch.py with `edits`, compiled in memory as its own module (the real one stays in sys.modules)."""
    with open(batch.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"witness not performed: the anchor occurs {src.count(old)} times: {old[:70]!r}")
        src = src.replace(old, new)
    mod = type(sys)("batch")
    mod.__file__ = batch.__file__
    exec(compile(src, batch.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


class TestWitnesses(unittest.TestCase):
    """B19-12: each witness, alone, turns its bound check red; the check is green on the tree first."""

    def kill(self, name):
        edits, check = WITNESSES[name]
        self.assertEqual(CHECKS[check](batch), [], f"{name}: the bound check {check} is not green on the tree")
        got = CHECKS[check](compiled(edits))
        print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} by {check} ({len(got)} problems)", end=" ",
              file=sys.stderr, flush=True)
        self.assertTrue(got, f"{name}: survived {check}")

    def test_witness_held_stops_dropped(self):
        self.kill("held-stops-dropped")

    def test_witness_held_nightly_dropped(self):
        self.kill("held-nightly-dropped")

    def test_witness_held_pause_only_stops(self):
        self.kill("held-pause-only-stops")

    def test_witness_held_pause_only_nightly(self):
        self.kill("held-pause-only-nightly")

    def test_witness_closing_cells_empty(self):
        self.kill("closing-cells-empty")

    def test_the_witnesses_are_named_and_bound(self):
        self.assertEqual(sorted(WITNESSES), sorted(["held-stops-dropped", "held-nightly-dropped",
                                                    "held-pause-only-stops", "held-pause-only-nightly",
                                                    "closing-cells-empty"]))
        self.assertTrue(all(check in CHECKS for _, check in WITNESSES.values()))


if __name__ == "__main__":
    unittest.main()
