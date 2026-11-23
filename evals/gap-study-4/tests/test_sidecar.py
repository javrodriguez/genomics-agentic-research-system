#!/usr/bin/env python3
"""box/sidecar.py: the host-side argv builders, and the in-container snapshotter, watcher and health writer, on fakes.

Nothing here starts a process or reaches a container runtime. The host half is driven through a FakeRuntime that
records every argv it is given; the in-container half is driven through a FakeWatcher (a made-up stream of watcher
events that follows inotify's coverage rules for the watch plan it is given), an injected clock and an injected
sleep. Nothing sleeps for real. A module guard (setUpModule) makes every process start and every signal raise for
the whole module, and a planted test proves it is armed.

Every guard is also run against an in-memory mutant, which must turn its check red; each mutant's red run is
printed by this file's own runner (MUTANT ... red), and the list is printed at the end.

The take content below is constructed: a plan file, a design table, a stage output. Nothing in it is a wording of
any task.
"""

from __future__ import annotations

import ast
import builtins
import errno
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass
from unittest import mock

sys.dont_write_bytecode = True
STUDY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, STUDY)

import harness_bookkeeping as hb  # noqa: E402
from box import sidecar  # noqa: E402
from graders import endstate as es  # noqa: E402

SIDECAR_SOURCE = os.path.join(STUDY, "box", "sidecar.py")
CLEAN = {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False}
IMAGE = "sha256:" + "ab" * 32
CID = "c0" * 32

# ------------------------------------------------------------------------------------------------- the process guard
_GUARD_NAMES = [("subprocess", "run"), ("subprocess", "Popen"), ("os", "system"), ("os", "kill"), ("os", "killpg"),
                ("os", "posix_spawn"), ("os", "posix_spawnp"), ("os", "fork")]
_GUARD_NAMES += [("os", n) for n in dir(os) if n.startswith(("exec", "spawn"))]
_PATCHES: list = []


class ProcessStartRefused(BaseException):
    """BaseException, so no `except Exception` in the code under test can swallow a guarded start."""
    pass


def _refuse(*a, **k):
    raise ProcessStartRefused("a test reached a process start or a signal; every runtime call goes to a fake")


def setUpModule():
    mods = {"subprocess": subprocess, "os": os}
    for mod, name in _GUARD_NAMES:
        if hasattr(mods[mod], name):
            p = mock.patch.object(mods[mod], name, _refuse)
            p.start()
            _PATCHES.append(p)


def tearDownModule():
    while _PATCHES:
        _PATCHES.pop().stop()
    print("\n".join(["", f"mutants run red in this file ({len(MUTANTS)}):"] + [f"  {m}" for m in MUTANTS]))


MUTANTS: list = []


def red(name: str):
    MUTANTS.append(name)
    print(f"\nMUTANT {name}: red", end=" ")


# ------------------------------------------------------------------------------------------------- the fakes
class FakeClock:
    """The host clock, injected: time() is the current instant; sleep(d) moves it on, and nothing else does."""

    def __init__(self, now: float = 1_000_000.0):
        self.now = now
        self.slept = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, d: float):
        self.now += d
        self.slept += d

    def tick(self, d: float = 1.0) -> float:
        self.now += d
        return self.now


class FakeWatcher:
    """A watcher process made up for these tests. It follows inotify's coverage: a folder watch sees events on the
    folder's direct children and on the folder itself; a recursive one sees everything beneath. `fs` reports a
    filesystem event; it reaches the stream only while the process runs and only when the plan covers it."""

    def __init__(self, clock: FakeClock, plan, *, establish_after: int = 0, stop_rc: int = -signal.SIGTERM,
                 stop_polls: int = 0):
        self.clock, self.plan = clock, tuple(plan)
        self._stop_polls = stop_polls
        self.exited_at = None
        self.queue: list = []
        self.rc = None
        self.stop_requested = False
        self.established_at = None
        self._polls = establish_after
        self.stop_rc = stop_rc

    def covers(self, path: str) -> bool:
        parent = path.rsplit("/", 1)[0] if "/" in path else ""
        for d, rec in self.plan:
            if d == parent or d == path:
                return True
            if rec and (d == "" or path.startswith(d + "/")):
                return True
        return False

    def fs(self, path, names, at=None):
        if self.rc is None and self.covers(path):
            self.queue.append(sidecar.WatchEvent(self.clock.time() if at is None else at, path, tuple(names)))

    def overflow(self, at=None):
        if self.rc is None:
            self.queue.append(sidecar.WatchEvent(self.clock.time() if at is None else at, "", (sidecar.OVERFLOW_EVENT,)))

    # the protocol the sidecar reads
    def established(self) -> bool:
        if self._polls > 0:
            self._polls -= 1
            return False
        if self.established_at is None:
            self.established_at = self.clock.time()
        return True

    def read_ready(self) -> list:
        out, self.queue = self.queue, []
        return out

    def poll(self):
        if self.rc is None and self.stop_requested:
            if self._stop_polls > 0:
                self._stop_polls -= 1
            else:
                self.rc, self.exited_at = self.stop_rc, self.clock.time()
        return self.rc

    def request_stop(self):
        self.stop_requested = True

    def force_stop(self):
        if self.rc is None:
            self.rc = -signal.SIGKILL

    def setup_failed(self) -> bool:
        return False

    def die(self, rc: int):
        self.rc, self.exited_at = rc, self.clock.time()


class Factory:
    """The injected watcher factory: records every plan it was armed with, and the watchers it made."""

    def __init__(self, clock, *, establish_after=0, fail_on: set | None = None, stop_rc=-signal.SIGTERM,
                 stop_polls=0):
        self.clock, self.made, self.plans = clock, [], []
        self.establish_after, self.fail_on, self.stop_rc = establish_after, fail_on or set(), stop_rc
        self.stop_polls = stop_polls

    def __call__(self, run_tree, plan):
        self.plans.append(tuple(plan))
        if len(self.made) + 1 in self.fail_on:
            self.made.append(None)
            raise OSError("injected: the re-arm failed")
        w = FakeWatcher(self.clock, plan, establish_after=self.establish_after, stop_rc=self.stop_rc,
                        stop_polls=self.stop_polls)
        self.made.append(w)
        return w

    @property
    def current(self) -> FakeWatcher:
        return self.made[-1]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Take:
    """One fake take: a run tree and an evidence folder in a temporary folder, a sidecar on fakes, and the ledger the
    test writes as the driver would."""

    def __init__(self, watch=("plan/approved.json",), *, files=None, factory_kw=None, sidecar_kw=None,
                 sidecar_cls=None):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.run_tree = os.path.join(base, "run")
        self.evidence = os.path.join(base, "ev")
        for d in (self.run_tree, self.evidence):
            os.mkdir(d)
        for rel, data in (files if files is not None else {"plan/approved.json": b'{"approved": false}\n',
                                                           "design.tsv": b"a\tb\n"}).items():
            self.write(rel, data)
        self.clock = FakeClock()
        self.factory = Factory(self.clock, **(factory_kw or {}))
        self.watch = tuple(watch)
        self.sc = (sidecar_cls or sidecar.Sidecar)(run_tree=self.run_tree, evidence=self.evidence, watch=self.watch,
                                  factory=self.factory, clock=self.clock.time,
                                  sleep=self.clock.sleep, **(sidecar_kw or {}))
        self.ledger = [{"kind": "take", "model": "a-test-model", "agent": {"harness": hb.CLAUDE_CODE,
                                                                          "version": "0.0.0-test"},
                        "run_tree": "", "home": None}]

    def close(self):
        for root, dirs, files in os.walk(self.run_tree):
            for n in dirs + files:
                p = os.path.join(root, n)
                if not os.path.islink(p):
                    os.chmod(p, 0o700)
        self._tmp.cleanup()

    def write(self, rel, data: bytes):
        p = os.path.join(self.run_tree, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(data)

    @property
    def w(self) -> FakeWatcher:
        return self.factory.current

    def turn(self, events=(), *, length=10.0, late=()):
        """One turn: started now, the fake stream's events inside it, ended after `length`; `late` events land after
        `ended_at` and before the post snapshot (a background writer)."""
        self.clock.tick(1.0)
        start = self.clock.time()
        for rel, names in events:
            self.clock.tick(1.0)
            self.w.fs(rel, names)
        self.clock.tick(length)
        end = self.clock.time()
        self.sc.pump()
        for rel, names in late:
            self.clock.tick(1.0)
            self.w.fs(rel, names)
        self.ledger.append({"kind": "turn", "n": len([r for r in self.ledger if r["kind"] == "turn"]) + 1,
                            "started_at": start, "ended_at": end})
        self.clock.tick(1.0)
        self.sc.pump()

    def write_ledger(self):
        with open(os.path.join(self.evidence, "ledger.jsonl"), "w", encoding="utf-8") as fh:
            for r in self.ledger:
                fh.write(json.dumps(r) + "\n")

    def load(self) -> es.Evidence:
        self.write_ledger()
        return es.Evidence.load(self.evidence)

    def health(self) -> list:
        with open(os.path.join(self.evidence, "health.jsonl"), encoding="utf-8") as fh:
            return [json.loads(x) for x in fh]

    def access(self) -> list:
        with open(os.path.join(self.evidence, "access.jsonl"), encoding="utf-8") as fh:
            return [json.loads(x) for x in fh]

    def snap(self, label) -> dict:
        with open(os.path.join(self.evidence, "snapshots", f"{label}.json"), encoding="utf-8") as fh:
            return json.load(fh)


class TakeCase(unittest.TestCase):
    def take(self, *a, **k) -> Take:
        t = Take(*a, **k)
        self.addCleanup(t.close)
        return t

    def one_turn(self, t: Take, events=(), late=()):
        r = t.sc.handle("begin")
        self.assertTrue(r["ok"], r)
        t.turn(events, late=late)
        r = t.sc.handle("snapshot", "post-1")
        self.assertTrue(r["ok"], r)
        t.clock.tick(1.0)   # the drive step's dwell after post-N (S7-D4: the final stop strictly after post-N)
        r = t.sc.handle("finish")
        self.assertTrue(r["ok"], r)
        return t


# ------------------------------------------------------------------------------------------------- the guard itself
class TestGuard(unittest.TestCase):
    def test_the_process_guard_is_armed(self):
        # identity first, so the calls below can never reach a real process start
        self.assertIs(subprocess.run, _refuse)
        self.assertIs(subprocess.Popen, _refuse)
        self.assertIs(os.kill, _refuse)
        self.assertIs(os.system, _refuse)
        for call in (lambda: subprocess.run(["true"]), lambda: subprocess.Popen(["true"]), lambda: os.kill(-1, 0),
                     lambda: os.system("true"), lambda: os.killpg(0, 0)):
            with self.assertRaises(ProcessStartRefused):
                call()

    def test_the_module_is_this_rounds_file(self):
        self.assertTrue(os.path.abspath(sidecar.__file__).endswith(os.path.join("evals", "gap-study-4", "box",
                                                                                "sidecar.py")), sidecar.__file__)


# ------------------------------------------------------------------------------------------------- the checkpoint
class TestEndstateRoundTrip(TakeCase):
    """The interface binds by construction: what the sidecar writes, endstate reads."""

    def test_one_turn_take_loads_clean(self):
        t = self.one_turn(self.take(), events=[("plan/approved.json", ("OPEN",))])
        ev = t.load()
        self.assertEqual(ev.sidecar_record(), CLEAN)
        acc = ev.accesses(path="plan/approved.json", turn=1)
        self.assertEqual([a["op"] for a in acc], ["open"])
        self.assertEqual(sorted(os.listdir(t.evidence)), ["access.jsonl", "blobs", "health.jsonl", "ledger.jsonl",
                                                          "snapshots", "watched.json"])   # S7-D3
        self.assertEqual(sorted(os.listdir(os.path.join(t.evidence, "snapshots"))), ["post-1.json", "pre-1.json"])
        self.assertEqual(temps_in(t.evidence), [])   # no temp file left behind

    def test_snapshot_entries_and_blobs(self):
        t = self.one_turn(self.take())
        s = t.snap("pre-1")
        self.assertEqual(set(s), {"label", "taken_at", "entries"})
        self.assertEqual(s["entries"]["plan"], {"type": "dir"})
        body = b'{"approved": false}\n'
        self.assertEqual(s["entries"]["plan/approved.json"], {"type": "file", "sha256": sha(body)})
        self.assertEqual(s["entries"]["design.tsv"], {"type": "file", "sha256": sha(b"a\tb\n")})
        with open(os.path.join(t.evidence, "blobs", sha(body)), "rb") as fh:
            self.assertEqual(fh.read(), body)
        # only consequential paths are copied
        self.assertEqual(os.listdir(os.path.join(t.evidence, "blobs")), [sha(body)])
        self.assertEqual(t.load().content("pre-1", "plan/approved.json"), body)

    def test_begin_order_and_stamps(self):
        t = self.take(factory_kw={"establish_after": 3})
        t0 = t.clock.time()
        r = t.sc.handle("begin")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["taken_at"], t0)                         # pre-1 taken first
        self.assertEqual(t.snap("pre-1")["taken_at"], t0)
        self.assertEqual(r["rearmed_at"], t.w.established_at)       # the start once the watches were established
        self.assertGreater(r["rearmed_at"], t0)
        self.assertEqual(t.health(), [{"kind": "watcher-start", "at": t.w.established_at}])
        self.assertEqual(t.access(), [])                              # created at begin, empty

    def test_pause_protocol_stamps(self):
        t = self.take(factory_kw={"establish_after": 2})
        t.sc.handle("begin")
        first = t.w
        t.turn()
        r = t.sc.handle("snapshot", "post-1")
        self.assertTrue(r["ok"], r)
        h = t.health()
        self.assertEqual([x["kind"] for x in h], ["watcher-start", "watcher-stop", "watcher-start"])
        self.assertTrue(first.stop_requested)
        self.assertEqual(h[1], {"kind": "watcher-stop", "at": r["taken_at"], "exit_code": 0, "ignored_newline_paths": 0})
        self.assertEqual(t.snap("post-1")["taken_at"], h[1]["at"])
        self.assertEqual(h[2]["at"], t.w.established_at)
        self.assertEqual(r["rearmed_at"], t.w.established_at)
        self.assertGreater(h[2]["at"], h[1]["at"])                   # the re-arm was delayed, and stamped as it was

    def test_reply_shape(self):
        t = self.take()
        r = t.sc.handle("begin")
        self.assertEqual(list(r), list(sidecar.REPLY_FIELDS))
        self.assertEqual(sidecar.parse_reply(json.dumps(r) + "\n"), r)


# ------------------------------------------------------------------------------------------------- the full round trip
PLAN = "plan/approved.json"
LOCKED = "plan/locked.json"


class TestRoundTrip(TakeCase):
    """A fake take in a temporary run tree: files, a link to a folder holding files, a file made unreadable with
    chmod 000, a FIFO; begin, fake watcher events, post-1, an operator write, pre-2, post-2, finish; endstate loads
    it clean."""

    def build(self):
        t = self.take(watch=(PLAN, LOCKED))
        t.write("data/real/one.txt", b"1\n")
        t.write("data/real/two.txt", b"2\n")
        os.symlink("real", os.path.join(t.run_tree, "data", "alias"))
        t.write(LOCKED, b"secret-ish but constructed\n")
        os.chmod(os.path.join(t.run_tree, LOCKED), 0)
        os.mkfifo(os.path.join(t.run_tree, "data", "pipe"))
        return t

    def drive(self, t):
        self.assertNotEqual(os.geteuid(), 0, "this test runs as a non-root user (chmod 000 must bite)")
        r = t.sc.handle("begin")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["unreadable"], [LOCKED])   # S7-D1: the FIFO is a special state, never unreadable
        self.assertEqual(r["unreadable_consequential"], [LOCKED])
        t.turn([(PLAN, ("OPEN",)), ("design.tsv", ("OPEN",))])
        r = t.sc.handle("snapshot", "post-1")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["unreadable_consequential"], [LOCKED])
        t.clock.tick(1.0)
        new = b"a\tb\nc\td\n"
        t.write("design.tsv", new)
        t.ledger.append({"kind": "operator", "id": "op-1", "at": t.clock.time(),
                         "writes": [{"path": "design.tsv", "after": {"type": "file", "sha256": sha(new)}}]})
        t.clock.tick(1.0)
        r = t.sc.handle("snapshot", "pre-2")
        self.assertTrue(r["ok"], r)
        t.turn([(PLAN, ("OPEN",)), (PLAN, ("MODIFY",)), (PLAN, ("CLOSE_WRITE",))])
        t.write(PLAN, b'{"approved": true}\n')
        r = t.sc.handle("snapshot", "post-2")
        self.assertTrue(r["ok"], r)
        t.clock.tick(1.0)
        r = t.sc.handle("finish")
        self.assertTrue(r["ok"], r)
        return t.load()

    def test_round_trip_loads_clean(self):
        t = self.build()
        ev = self.drive(t)
        self.assertEqual(ev.sidecar_record(), CLEAN)
        post = ev.entries("post-1")
        self.assertEqual(post["data/alias"], {"type": "link", "target": "real"})
        self.assertFalse([p for p in post if p.startswith("data/alias/")])
        self.assertEqual(post["data/pipe"], {"type": "special", "kind": "fifo"})   # S7-D1
        self.assertEqual(post[LOCKED], {"type": "unreadable"})
        self.assertEqual(post["data/real/one.txt"]["type"], "file")
        self.assertEqual([a["op"] for a in ev.accesses(path=PLAN, turn=1)], ["open"])
        self.assertEqual([a["op"] for a in ev.accesses(path=PLAN, turn=2)], ["open", "modify", "modify"])
        # S7-D3 (ruled C): design.tsv is not watched, so reading its accesses is refused, never an empty "no access"
        with self.assertRaisesRegex(es.EvidenceError, "not a watched path"):
            ev.accesses(path="design.tsv")
        self.assertEqual(ev.watched(), tuple(sorted((PLAN, LOCKED))))
        self.assertEqual(ev.content("post-2", PLAN), b'{"approved": true}\n')
        self.assertEqual(ev.agent_changes(2)[PLAN].kind, "modified")
        # The named effect of persistently unreadable paths (W2A fold 1 question 3): the chmod-000 file reads as an
        # unknown change across the operator step, so the operator re-check counts it. The FIFO no longer does: it
        # is a special state, compared by equality (S7-D1, W2A2-3's fix), so a lasting FIFO is no change.
        unexplained = ev.operator_matches(1)["unexplained"]
        self.assertEqual(unexplained, [LOCKED])
        self.assertNotIn("data/pipe", ev.agent_changes(1))
        self.assertEqual(sorted(os.listdir(t.evidence)), sorted(es.FILES + es.FOLDERS))

    def test_mutant_following_a_link_goes_red(self):
        t = self.build()
        honest, _, _ = sidecar.snapshot_tree(t.run_tree, t.watch)
        with mock.patch.object(sidecar.os, "lstat", os.stat):   # mutant: the walk follows links
            followed, _, _ = sidecar.snapshot_tree(t.run_tree, t.watch)
        beneath = sorted(p for p in followed if p.startswith("data/alias/"))
        self.assertEqual(beneath, ["data/alias/one.txt", "data/alias/two.txt"])   # the check above goes red
        self.assertNotEqual(followed["data/alias"], {"type": "link", "target": "real"})
        # and endstate refuses a snapshot that records the link and lists what lies beneath it
        snap = {"label": "pre-1", "taken_at": 1.0, "entries": dict(honest, **{p: followed[p] for p in beneath})}
        with self.assertRaisesRegex(es.EvidenceError, "followed a link"):
            es.Evidence.from_parts(ledger=t.ledger + [{"kind": "turn", "n": 1, "started_at": 2.0, "ended_at": 3.0}],
                                   snapshots={"pre-1": snap, "post-1": dict(snap, label="post-1", taken_at=4.0)},
                                   access=[], health=[])
        red("the snapshot follows a link")


class TestSpecialFilesAndOpens(TakeCase):
    def recording_opener(self, clock, block_after_s=3600.0):
        seen = []

        def opener(path, flags):
            seen.append((path, flags))
            if stat.S_ISFIFO(os.lstat(path).st_mode):
                clock.tick(block_after_s)     # opening a FIFO for reading blocks: the injected clock runs out
                raise OSError("the open blocked (simulated)")
            return os.open(path, flags)
        return opener, seen

    BUDGET_S = 60.0

    def snap_with_fifo(self):
        t = self.take()
        os.mkfifo(os.path.join(t.run_tree, "pipe"))
        opener, seen = self.recording_opener(t.clock)
        t0 = t.clock.time()
        entries, special, _ = sidecar.snapshot_tree(t.run_tree, t.watch, opener=opener)
        return t, entries, special, seen, t.clock.time() - t0

    def test_a_fifo_is_never_opened(self):
        t, entries, special, seen, elapsed = self.snap_with_fifo()
        self.assertEqual(entries["pipe"], {"type": "special", "kind": "fifo"})   # S7-D1
        self.assertEqual(special, ["pipe"])
        self.assertLess(elapsed, self.BUDGET_S)
        self.assertNotIn(os.path.join(t.run_tree, "pipe"), [p for p, _ in seen])

    def test_mutant_a_fifo_opened_goes_red(self):
        real = sidecar._kind
        with mock.patch.object(sidecar, "_kind", lambda m: "file" if stat.S_ISFIFO(m) else real(m)):
            _, _, _, _, elapsed = self.snap_with_fifo()
        self.assertGreater(elapsed, self.BUDGET_S)        # the check above goes red
        red("a FIFO opened")

    def test_every_open_never_follows_and_never_blocks(self):
        t, _, _, seen, _ = self.snap_with_fifo()
        self.assertTrue(seen)
        for _, flags in seen:
            self.assertTrue(flags & os.O_NOFOLLOW and flags & os.O_NONBLOCK, flags)

    def race_open(self, t):
        """An opener that swaps the planted file for a link to another file between the lstat and the open."""
        target = os.path.join(t.run_tree, "design.tsv")
        p = os.path.join(t.run_tree, PLAN)

        def opener(path, flags):
            if path == p:
                os.unlink(p)
                os.symlink(target, p)
            return os.open(path, flags)
        return opener

    def test_a_lstat_then_open_race_never_follows(self):
        t = self.take()
        entries, _, blobs = sidecar.snapshot_tree(t.run_tree, t.watch, opener=self.race_open(t))
        self.assertEqual(entries[PLAN], {"type": "unreadable"})
        self.assertEqual(blobs, {})

    def test_mutant_no_nofollow_goes_red(self):
        t = self.take()
        with mock.patch.object(sidecar, "OPEN_FLAGS", sidecar.OPEN_FLAGS & ~os.O_NOFOLLOW):
            entries, _, _ = sidecar.snapshot_tree(t.run_tree, t.watch, opener=self.race_open(t))
        self.assertEqual(entries[PLAN], {"type": "file", "sha256": sha(b"a\tb\n")})   # it followed the link
        red("no O_NOFOLLOW")

    def fifo_race(self, t):
        """An opener that swaps the planted file for a FIFO between the lstat and the open. Opening a FIFO for
        reading without O_NONBLOCK blocks: simulated here by running the injected clock out."""
        p = os.path.join(t.run_tree, PLAN)

        def opener(path, flags):
            if path == p:
                os.unlink(p)
                os.mkfifo(p)
                if not flags & os.O_NONBLOCK:
                    t.clock.tick(3600.0)
                    raise OSError("the open blocked (simulated)")
            return os.open(path, flags)
        return opener

    def test_a_race_onto_a_fifo_never_blocks(self):
        t = self.take()
        t0 = t.clock.time()
        entries, _, _ = sidecar.snapshot_tree(t.run_tree, t.watch, opener=self.fifo_race(t))
        self.assertEqual(entries[PLAN], {"type": "unreadable"})       # fstat: not a regular file
        self.assertLess(t.clock.time() - t0, self.BUDGET_S)

    def test_mutant_no_nonblock_goes_red(self):
        t = self.take()
        t0 = t.clock.time()
        with mock.patch.object(sidecar, "OPEN_FLAGS", sidecar.OPEN_FLAGS & ~os.O_NONBLOCK):
            sidecar.snapshot_tree(t.run_tree, t.watch, opener=self.fifo_race(t))
        self.assertGreater(t.clock.time() - t0, self.BUDGET_S)
        red("no O_NONBLOCK (a race onto a FIFO blocks)")

    def test_the_host_clock_never_the_monotonic_one(self):
        t = self.take()
        sc = sidecar.Sidecar(run_tree=t.run_tree, evidence=t.evidence, watch=t.watch, factory=t.factory,
                             sleep=t.clock.sleep)
        r = sc.handle("begin")
        self.assertLess(abs(r["taken_at"] - __import__("time").time()), 60.0)

    def test_mutant_monotonic_clock_goes_red(self):
        import time as _t
        t = self.take()
        with mock.patch.object(sidecar, "CLOCK", _t.monotonic):
            sc = sidecar.Sidecar(run_tree=t.run_tree, evidence=t.evidence, watch=t.watch, factory=t.factory,
                                 sleep=t.clock.sleep)
            r = sc.handle("begin")
        self.assertGreater(abs(r["taken_at"] - _t.time()), 60.0)
        red("the monotonic clock")

    def test_no_temp_file_is_left_and_snapshots_never_overwrite(self):
        t = self.one_turn(self.take())
        self.assertEqual(temps_in(t.evidence), [])
        with self.assertRaises(FileExistsError):
            sidecar._write_atomic(os.path.join(t.evidence, "snapshots", "pre-1.json"), b"{}")
        self.assertEqual(temps_in(t.evidence), [])


def temps_in(folder: str) -> list:
    out = []
    for root, _dirs, files in os.walk(folder):
        out += [os.path.relpath(os.path.join(root, f), folder) for f in files if f.startswith(".tmp-")]
    return sorted(out)


# ------------------------------------------------------------------------------------------------- fold 1, Q1 (EXDEV)
REAL_RENAME = os.rename


def mount_rename(src, dst):
    """A rename that fails across "mounts", as Linux's rename(2) does across a bind mount (EXDEV): here every
    folder is its own mount, so a temp outside its destination's folder fails on the Mac too."""
    if os.path.dirname(os.path.abspath(src)) != os.path.dirname(os.path.abspath(dst)):
        raise OSError(errno.EXDEV, "Invalid cross-device link (simulated)")
    return REAL_RENAME(src, dst)


class TestCrossMount(TakeCase):
    """Fold 1, Q1 (glitch-f3's ruling): every temp sits in its destination's own folder, under a dot-name."""

    def test_the_temp_sits_beside_its_destination(self):
        ev = "/srv/ev"
        self.assertEqual(sidecar._temp_path(f"{ev}/snapshots/post-1.json", 0), f"{ev}/snapshots/.tmp-post-1-0")
        self.assertEqual(sidecar._temp_path(f"{ev}/blobs/{'a' * 64}", 2), f"{ev}/blobs/.tmp-{'a' * 64}-2")
        self.assertEqual(sidecar._temp_path(f"{ev}/x.json", 1), f"{ev}/.tmp-x-1")

    def test_a_take_under_the_cross_mount_rename_is_green(self):
        with mock.patch.object(sidecar.os, "rename", mount_rename):
            t = self.one_turn(self.take(), events=[(PLAN, ("OPEN",))])
        self.assertEqual(t.load().sidecar_record(), CLEAN)
        self.assertEqual(temps_in(t.evidence), [])

    def test_mutant_the_old_private_folder_layout_goes_red(self):
        priv = tempfile.mkdtemp()
        self.addCleanup(lambda: [os.unlink(os.path.join(priv, n)) for n in os.listdir(priv)] and os.rmdir(priv))
        with mock.patch.object(sidecar.os, "rename", mount_rename), \
                mock.patch.object(sidecar, "_temp_path", lambda dest, n: os.path.join(priv, f".tmp-{n}")):
            t = self.take()
            r = t.sc.handle("begin")
        self.assertFalse(r["ok"])                       # EXDEV: every begin would fail on a real box
        self.assertTrue(any("OSError" in x for x in r["problems"]), r)
        red("the temp in a private folder (the cross-mount rename fails)")

    def test_mutant_temp_in_tmp_goes_red(self):
        name = f".tmp-w4c-{os.getpid()}"
        target = os.path.join(tempfile.gettempdir(), name)
        self.addCleanup(lambda: os.path.lexists(target + "-0") and os.unlink(target + "-0"))
        with mock.patch.object(sidecar.os, "rename", mount_rename), \
                mock.patch.object(sidecar, "_temp_path", lambda dest, n: f"{target}-{n}"):
            t = self.take()
            r = t.sc.handle("begin")
        self.assertFalse(r["ok"])
        red("the temp written to /tmp")

    def test_a_planted_leftover_temp_makes_the_load_refuse(self):
        for where in (("snapshots", ".tmp-post-1-0"), (".tmp-ledger-0",), ("blobs", ".tmp-" + "a" * 64 + "-0")):
            with self.subTest(where):
                t = self.one_turn(self.take())
                with open(os.path.join(t.evidence, *where), "wb") as fh:
                    fh.write(b"{")
                with self.assertRaises(es.EvidenceError):
                    t.load()

    def leftover_take(self):
        """A snapshot write whose rename fails and whose own cleanup fails too: the temp stays on disk."""
        t = self.take()
        t.sc.handle("begin")
        t.turn()
        real_unlink = os.unlink

        def failing_rename(src, dst):
            raise OSError(errno.EIO, "injected")

        def failing_unlink(path):
            if os.path.basename(path).startswith(".tmp-"):
                raise OSError(errno.EIO, "injected")
            return real_unlink(path)
        with mock.patch.object(sidecar.os, "rename", failing_rename), \
                mock.patch.object(sidecar.os, "unlink", failing_unlink):
            self.assertFalse(t.sc.handle("snapshot", "post-1")["ok"])
        self.assertNotEqual(temps_in(t.evidence), [])
        return t

    def test_finish_removes_any_temp_it_made(self):
        t = self.leftover_take()
        t.sc.handle("finish")
        self.assertEqual(temps_in(t.evidence), [])

    def test_mutant_finish_without_the_sweep_goes_red(self):
        with mock.patch.object(sidecar.Sidecar, "_sweep_temps", lambda self: None):
            t = self.leftover_take()
            t.sc.handle("finish")
        self.assertNotEqual(temps_in(t.evidence), [])
        red("finish leaving the sidecar's own temp behind")


# ------------------------------------------------------------------------------------------------- the plan's stubs
class TestStubs(TakeCase):
    def test_a_take_that_reads_nothing_logs_zero_events(self):
        t = self.one_turn(self.take())
        self.assertEqual(t.access(), [])
        self.assertEqual(t.load().accesses(), [])
        self.assertEqual(os.path.getsize(os.path.join(t.evidence, "access.jsonl")), 0)

    def test_mutant_skipping_the_empty_log_goes_red(self):
        with mock.patch.object(sidecar, "CREATED_AT_BEGIN", (sidecar.HEALTH,)):
            t = self.one_turn(self.take())
        with self.assertRaisesRegex(es.EvidenceError, "access.jsonl is missing"):
            t.load()
        red("access.jsonl not created at begin")

    def test_a_take_that_reads_the_planted_file_logs_exactly_that_read(self):
        t = self.take()
        t.sc.handle("begin")
        t.turn()
        t.sc.handle("snapshot", "post-1")
        t.sc.handle("snapshot", "pre-2")
        t.turn([(PLAN, ("OPEN",))])
        t.sc.handle("snapshot", "post-2")
        t.clock.tick(1.0)   # S7-D4: the drive step's dwell, so the final stop falls strictly after post-N
        t.sc.handle("finish")
        ev = t.load()
        self.assertEqual(ev.accesses(turn=1), [])
        got = ev.accesses(path=PLAN, turn=2)
        self.assertEqual([(a["op"], a["late"]) for a in got], [("open", False)])
        self.assertEqual(len(ev.accesses()), 1)

    def test_a_background_writer_is_attributed_to_its_turn_and_marked_late(self):
        t = self.take()
        t.sc.handle("begin")
        t.turn(late=[(PLAN, ("MODIFY",))])
        t.sc.handle("snapshot", "post-1")
        t.clock.tick(1.0)   # S7-D4: the drive step's dwell, so the final stop falls strictly after post-N
        t.sc.handle("finish")
        got = t.load().accesses(path=PLAN, turn=1)
        self.assertEqual([(a["op"], a["late"]) for a in got], [("modify", True)])


# ------------------------------------------------------------------------------------------------- gaps
class Rearm(sidecar.Sidecar):
    pass


class TestGaps(TakeCase):
    def test_a_watcher_that_dies_mid_turn(self):
        t = self.take()
        t.sc.handle("begin")
        t.clock.tick(1.0)
        t.ledger.append({"kind": "turn", "n": 1, "started_at": t.clock.time(), "ended_at": t.clock.time() + 5})
        t.clock.tick(2.0)
        t.w.die(1)
        died = t.clock.tick(1.0)
        t.sc.pump()
        t.clock.tick(5.0)
        h = t.health()
        self.assertEqual(h[-1], {"kind": "watcher-stop", "at": died, "exit_code": 1, "ignored_newline_paths": 0})   # stamped at detection
        r = t.sc.handle("snapshot", "post-1")
        self.assertFalse(r["ok"])
        self.assertTrue(any("exited on its own" in p for p in r["problems"]), r)
        self.assertEqual(len(t.factory.made), 1)                       # never re-armed
        self.assertFalse(t.sc.handle("status")["ok"])
        r = t.sc.handle("finish")
        self.assertFalse(r["ok"])
        self.assertEqual([x["kind"] for x in t.health()], ["watcher-start", "watcher-stop"])   # no second stop
        self.assertEqual(t.load().sidecar_record(),
                         {"start_record": False, "stop_record": False, "exit_code": 1, "queue_overflow": False})

    def test_a_self_exit_0_after_post_n_never_reads_clean(self):
        t = self.take()
        t.sc.handle("begin")
        t.turn()
        t.sc.handle("snapshot", "post-1")
        t.clock.tick(1.0)
        t.w.die(0)            # it exits 0 on its own after post-N; a late writer would go unlogged
        t.sc.pump()
        self.assertFalse(t.sc.handle("finish")["ok"])
        self.assertEqual(t.health()[-1]["exit_code"], 1)
        self.assertEqual(t.load().sidecar_record()["exit_code"], 1)

    def test_mutant_self_exit_0_read_clean_goes_red(self):
        real = sidecar.stop_exit_code
        with mock.patch.object(sidecar, "stop_exit_code",
                               lambda rc, requested, fault: 0 if rc == 0 else real(rc, requested=requested,
                                                                                    fault=fault)):
            t = self.take()
            t.sc.handle("begin")
            t.turn()
            t.sc.handle("snapshot", "post-1")
            t.clock.tick(1.0)   # S7-D4: the exit after post-N, as its sibling above has it
            t.w.die(0)
            t.sc.pump()
            t.sc.handle("finish")
        self.assertEqual(t.load().sidecar_record(), CLEAN)   # the test above goes red: the gap reads clean
        red("a self-exit 0 after post-N recorded clean")

    def moved_chain(self):
        # mv plan plan.old; mkdir plan; echo x > plan/approved.json; cat it (fold 1, Q2: glitch-f3's ruling)
        t = self.take()
        t.sc.handle("begin")
        t.turn([("plan", ("MOVED_FROM", "ISDIR")), ("plan.old", ("MOVED_TO", "ISDIR")),
                ("plan", ("CREATE", "ISDIR")), (PLAN, ("CREATE",)), (PLAN, ("OPEN",))])
        os.rename(os.path.join(t.run_tree, "plan"), os.path.join(t.run_tree, "plan.old"))
        t.write(PLAN, b"x\n")
        r1 = t.sc.handle("snapshot", "post-1")
        t.clock.tick(1.0)   # S7-D4: the drive step's dwell, so the final stop falls strictly after post-N
        r2 = t.sc.handle("finish")
        return t, r1, r2

    def test_a_chain_folder_moved_logs_per_path_events_and_no_fault(self):
        t, r1, r2 = self.moved_chain()
        self.assertTrue(r1["ok"] and r2["ok"], (r1, r2))
        ev = t.load()
        self.assertEqual(ev.sidecar_record(), CLEAN)
        self.assertEqual([a["op"] for a in ev.accesses(path=PLAN, turn=1)], ["delete", "modify", "open"])

    def test_mutant_a_moved_chain_folder_as_a_fault_goes_red(self):
        real = sidecar.Sidecar._event

        def faulting(self, ev):   # mutant: a rename of a chain folder stops the watcher
            if ev.path == "plan" and "MOVED_FROM" in ev.names:
                return False
            return real(self, ev)
        with mock.patch.object(sidecar.Sidecar, "_event", faulting):
            t, r1, _ = self.moved_chain()
        self.assertFalse(r1["ok"])
        red("a moved chain folder read as a watcher fault")

    def test_mutant_a_moved_chain_folder_unlogged_goes_red(self):
        with mock.patch.object(sidecar.Sidecar, "_beneath", lambda self, folder: []):
            t, _, _ = self.moved_chain()
        self.assertNotIn("delete", [a["op"] for a in t.access()])
        red("a moved chain folder logs no per-path delete")

    def test_a_folder_moved_onto_the_chain_logs_a_modify(self):
        t = self.take()
        t.sc.handle("begin")
        t.turn([("plan", ("MOVED_FROM", "ISDIR")), ("staged", ("MOVED_FROM", "ISDIR")),
                ("plan", ("MOVED_TO", "ISDIR"))])     # mv plan old; mv staged plan
        t.sc.handle("snapshot", "post-1")
        t.clock.tick(1.0)   # S7-D4: the drive step's dwell, so the final stop falls strictly after post-N
        t.sc.handle("finish")
        self.assertEqual([a["op"] for a in t.load().accesses(path=PLAN, turn=1)], ["delete", "modify"])

    def test_an_rm_rf_of_a_chain_folder_logs_per_path_events_and_no_fault(self):
        t = self.take()
        t.sc.handle("begin")
        t.turn([(PLAN, ("DELETE",)), ("plan", ("DELETE_SELF",)), ("plan", ("DELETE", "ISDIR"))])
        r = t.sc.handle("snapshot", "post-1")
        self.assertTrue(r["ok"], r)
        t.clock.tick(1.0)   # S7-D4: the drive step's dwell, so the final stop falls strictly after post-N
        t.sc.handle("finish")
        ev = t.load()
        self.assertEqual(ev.sidecar_record(), CLEAN)
        self.assertEqual([a["op"] for a in ev.accesses(path=PLAN, turn=1)], ["delete"])

    def test_mutant_an_rm_rf_as_a_fault_goes_red(self):
        real = sidecar.Sidecar._event

        def faulting(self, ev):   # mutant: a delete of a chain folder stops the watcher
            if ev.path == "plan" and {"DELETE", "DELETE_SELF"} & set(ev.names):
                return False
            return real(self, ev)
        with mock.patch.object(sidecar.Sidecar, "_event", faulting):
            t = self.take()
            t.sc.handle("begin")
            t.turn([(PLAN, ("DELETE",)), ("plan", ("DELETE", "ISDIR"))])
            self.assertFalse(t.sc.handle("snapshot", "post-1")["ok"])
        red("an rm -rf of a chain folder read as a watcher fault")

    def test_an_event_that_maps_to_no_path_is_a_fault(self):
        t = self.take()
        t.sc.handle("begin")
        t.w.queue.append(sidecar.WatchEvent(t.clock.time(), None, ("OPEN",)))
        t.sc.pump()
        self.assertEqual(t.health()[-1]["kind"], "watcher-stop")
        self.assertNotEqual(t.health()[-1]["exit_code"], 0)

    def test_mutant_an_unmapped_event_ignored_goes_red(self):
        with mock.patch.object(sidecar, "_mapped", lambda path: True):
            t = self.take()
            t.sc.handle("begin")
            t.w.queue.append(sidecar.WatchEvent(t.clock.time(), None, ("OPEN",)))
            t.sc.pump()
        self.assertEqual(t.health()[-1]["kind"], "watcher-start")
        red("an event mapped to no path read through")

    def test_the_plan_is_the_whole_tree_recursively(self):
        t = self.take()
        self.assertEqual(sidecar.watch_plan(t.run_tree, t.watch), (("", True),))

    def test_a_self_exit_0_just_before_the_stop_request_never_reads_clean(self):
        t = self.take()
        t.sc.handle("begin")
        t.turn()
        t.w.die(0)                 # between the last pump and the stop request
        t.sc._pause("post-1")
        self.assertEqual(t.health()[1]["exit_code"], 1)

    def test_mutant_an_exit_before_the_request_read_as_requested_goes_red(self):
        real = sidecar.stop_exit_code
        with mock.patch.object(sidecar, "stop_exit_code",
                               lambda rc, requested, fault: real(rc, requested=True, fault=fault)):
            t = self.take()
            t.sc.handle("begin")
            t.turn()
            t.w.die(0)
            t.sc._pause("post-1")
        self.assertEqual(t.health()[1]["exit_code"], 0)
        red("a self-exit before the stop request read as a clean stop")

    def future_stamp_take(self):
        t = self.take()
        t.sc.handle("begin")
        t.clock.tick(1.0)
        start = t.clock.time()
        t.w.queue.append(sidecar.WatchEvent(t.clock.time() + 100.0, PLAN, ("OPEN",)))
        t.sc.pump()
        t.clock.tick(1.0)
        t.ledger.append({"kind": "turn", "n": 1, "started_at": start, "ended_at": t.clock.time()})
        t.clock.tick(1.0)
        t.sc.handle("snapshot", "post-1")
        t.clock.tick(1.0)   # S7-D4: the drive step's dwell, so the final stop falls strictly after post-N
        t.sc.handle("finish")
        return t, start

    def test_a_stream_stamp_later_than_the_clock_is_capped(self):
        t, start = self.future_stamp_take()
        self.assertEqual(t.access()[0]["at"], start)
        self.assertEqual(t.load().sidecar_record(), CLEAN)

    def test_mutant_an_uncapped_future_stamp_goes_red(self):
        with mock.patch.object(sidecar.Sidecar, "_stamp", lambda self, at: max(at, self._floor)):
            t, _ = self.future_stamp_take()
        try:
            rec = t.load().sidecar_record()
        except es.EvidenceError:
            rec = "refused"
        self.assertNotEqual(rec, CLEAN)
        red("a stream stamp later than the clock kept")

    def test_a_stream_stamp_before_the_start_is_floored(self):
        t = self.take(factory_kw={"establish_after": 3})
        t.sc.handle("begin")
        start = t.health()[0]["at"]
        t.w.queue.append(sidecar.WatchEvent(start - 0.5, PLAN, ("OPEN",)))
        t.w.overflow(at=start - 0.4)
        t.sc.pump()
        self.assertEqual([a["at"] for a in t.access()], [start])
        self.assertEqual(t.health()[-1], {"kind": "queue-overflow", "at": start})

    def test_mutant_a_death_recorded_clean_goes_red(self):
        with mock.patch.object(sidecar, "stop_exit_code", lambda rc, **k: 0):
            t = self.take()
            t.sc.handle("begin")
            t.w.die(1)
            t.sc.pump()
        self.assertEqual(t.health()[-1]["exit_code"], 0)
        red("a death recorded with exit code 0")

    def test_mutant_a_second_stop_after_death_goes_red(self):
        class Twice(sidecar.Sidecar):
            def _finish(self):   # mutant: finish stamps a stop whatever happened before
                self._health(sidecar.WATCHER_STOP, self.clock(), exit_code=0, ignored_newline_paths=0)
                return self._reply("finish", None)
        t = self.take(sidecar_cls=Twice)
        t.sc.handle("begin")
        t.w.die(1)
        t.sc.pump()
        t.sc.handle("finish")
        self.assertEqual([x["kind"] for x in t.health()], ["watcher-start", "watcher-stop", "watcher-stop"])
        red("finish writes a second stop after a death")

    def test_a_queue_overflow(self):
        t = self.take()
        t.sc.handle("begin")
        t.clock.tick(1.0)
        start = t.clock.time()
        t.clock.tick(1.0)
        t.w.overflow()
        at = t.clock.time()
        t.clock.tick(1.0)
        t.ledger.append({"kind": "turn", "n": 1, "started_at": start, "ended_at": t.clock.time()})
        t.clock.tick(1.0)
        t.sc.handle("snapshot", "post-1")
        t.clock.tick(1.0)   # S7-D4: the drive step's dwell, so the final stop falls strictly after post-N
        t.sc.handle("finish")
        self.assertIn({"kind": "queue-overflow", "at": at}, t.health())
        self.assertEqual(t.load().sidecar_record(),
                         {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": True})

    def test_mutant_overflow_dropped_goes_red(self):
        real = sidecar.Sidecar._health

        def dropping(self, kind, at, **extra):   # mutant: the overflow record silently never written
            if kind != sidecar.QUEUE_OVERFLOW:
                real(self, kind, at, **extra)
        with mock.patch.object(sidecar.Sidecar, "_health", dropping):
            t = self.take()
            t.sc.handle("begin")
            t.w.overflow()
            t.sc.pump()
            t.turn()
            t.sc.handle("snapshot", "post-1")
            t.sc.handle("finish")
        self.assertEqual(t.load().sidecar_record()["queue_overflow"], False)   # the overflow test goes red
        red("the overflow event not written as queue-overflow")

    def test_a_missing_start_from_a_failed_rearm(self):
        t = self.take(factory_kw={"fail_on": {3}})       # begin arms 1, post-1 arms 2, pre-2's re-arm fails
        t.sc.handle("begin")
        t.turn()
        self.assertTrue(t.sc.handle("snapshot", "post-1")["ok"])
        r = t.sc.handle("snapshot", "pre-2")
        self.assertFalse(r["ok"])
        self.assertIsNone(r["rearmed_at"])
        kinds = [x["kind"] for x in t.health()]
        self.assertEqual(kinds, ["watcher-start", "watcher-stop", "watcher-start", "watcher-stop"])  # no 3rd start
        t.turn()
        self.assertFalse(t.sc.handle("snapshot", "post-2")["ok"])
        self.assertFalse(t.sc.handle("finish")["ok"])
        self.assertEqual(t.load().sidecar_record(),
                         {"start_record": False, "stop_record": False, "exit_code": 0, "queue_overflow": False})

    def test_a_missing_final_stop(self):
        t = self.take()
        t.sc.handle("begin")
        t.turn()
        t.sc.handle("snapshot", "post-1")             # the take ends here: finish is never called
        self.assertEqual(t.load().sidecar_record(),
                         {"start_record": True, "stop_record": False, "exit_code": 0, "queue_overflow": False})

    def test_finish_writes_the_final_stop(self):
        t = self.one_turn(self.take())
        self.assertEqual(t.health()[-1]["kind"], "watcher-stop")
        self.assertEqual(t.load().sidecar_record(), CLEAN)


class TestExitCodes(TakeCase):
    def test_a_stop_by_the_sidecars_signal_records_0(self):
        t = self.one_turn(self.take(factory_kw={"stop_rc": -signal.SIGTERM, "stop_polls": 2}))
        self.assertEqual([x.get("exit_code") for x in t.health() if x["kind"] == "watcher-stop"], [0, 0])

    def test_mutant_raw_signal_code_on_a_clean_stop_goes_red(self):
        with mock.patch.object(sidecar, "stop_exit_code", lambda rc, **k: 128 - rc if rc < 0 else rc):
            t = self.one_turn(self.take())
        self.assertEqual(t.health()[-1]["exit_code"], 128 + signal.SIGTERM)
        red("a clean deliberate stop recorded as 143")

    def test_a_watcher_that_exits_by_itself_at_stop_time_records_its_code(self):
        # it ended on its own (exit 3) before the stop signal reached it: never read as a clean stop
        t = self.take(factory_kw={"stop_rc": 3})
        t.sc.handle("begin")
        t.turn()
        t.sc.handle("snapshot", "post-1")
        self.assertEqual(t.health()[1]["exit_code"], 3)

    def test_mutant_any_requested_stop_reads_clean_goes_red(self):
        with mock.patch.object(sidecar, "stop_exit_code", lambda rc, requested, fault: 0 if requested else rc):
            t = self.take(factory_kw={"stop_rc": 3})
            t.sc.handle("begin")
            t.turn()
            t.sc.handle("snapshot", "post-1")
        self.assertEqual(t.health()[1]["exit_code"], 0)
        red("a requested stop that ended on its own read as clean")

    def test_the_exit_code_rule(self):
        f = sidecar.stop_exit_code
        self.assertEqual(f(-signal.SIGTERM, requested=True, fault=False), 0)
        self.assertEqual(f(-signal.SIGKILL, requested=True, fault=False), 128 + signal.SIGKILL)
        self.assertEqual(f(-signal.SIGTERM, requested=False, fault=False), 128 + signal.SIGTERM)
        self.assertEqual(f(-signal.SIGTERM, requested=True, fault=True), 128 + signal.SIGTERM)
        self.assertEqual(f(0, requested=True, fault=True), 1)
        self.assertEqual(f(1, requested=False, fault=False), 1)

    def test_an_unknown_event_name_is_a_fault(self):
        t = self.take()
        t.sc.handle("begin")
        t.w.queue.append(sidecar.WatchEvent(t.clock.time(), PLAN, ("ACCESS",)))
        t.sc.pump()
        stop = t.health()[-1]
        self.assertEqual(stop["kind"], "watcher-stop")
        self.assertNotEqual(stop["exit_code"], 0)
        self.assertFalse(t.sc.handle("status")["ok"])

    def test_mutant_unknown_names_ignored_goes_red(self):
        with mock.patch.dict(sidecar.EVENT_OPS, {"ACCESS": "open"}):
            t = self.take()
            t.sc.handle("begin")
            t.w.queue.append(sidecar.WatchEvent(t.clock.time(), PLAN, ("ACCESS",)))
            t.sc.pump()
        self.assertEqual(t.health()[-1]["kind"], "watcher-start")
        red("an event name outside the table read as an op")

    def test_the_event_table_is_exactly_the_plans(self):
        self.assertEqual(sidecar.EVENT_OPS, {"OPEN": "open", "MODIFY": "modify", "CLOSE_WRITE": "modify",
                                             "MOVED_TO": "modify", "CREATE": "modify", "DELETE": "delete",
                                             "MOVED_FROM": "delete", "DELETE_SELF": "delete"})
        self.assertEqual(set(sidecar.EVENT_OPS.values()), set(es.ACCESS_OPS))


# ------------------------------------------------------------------------------------------------- the pause stamps
class TestPauseStamps(TakeCase):
    def test_mutant_rearm_stamped_at_the_pause_goes_red(self):
        class Early(sidecar.Sidecar):
            def _arm(self):   # mutant: the start stamped when the re-arm begins, not when the watches are up
                at = self.clock()
                w = self.factory(self.run_tree, sidecar.watch_plan(self.run_tree, self.watch))
                while not w.established():
                    self.sleep(sidecar.POLL_S)
                self._health(sidecar.WATCHER_START, at)
                self.watcher = w
                return at
        t = self.take(factory_kw={"establish_after": 5}, sidecar_cls=Early)
        t.sc.handle("begin")
        t.turn()
        t.sc.handle("snapshot", "post-1")
        self.assertNotEqual(t.health()[-1]["at"], t.w.established_at)
        self.assertLess(t.health()[-1]["at"], t.w.established_at)
        red("the re-arm stamped at the pause's start (a false stamp)")

    def test_mutant_stop_stamped_after_taken_at_goes_red(self):
        class Late(sidecar.Sidecar):
            def _pause(self, label):   # mutant: taken_at read first, the stop stamped after it
                taken_at = self.clock()
                self._stop()
                u, uc, _ = self._snapshot(label, taken_at)
                return taken_at, u, uc
        t = self.take(factory_kw={"stop_polls": 4}, sidecar_cls=Late)
        t.sc.handle("begin")
        t.turn()
        r = t.sc.handle("snapshot", "post-1")
        stop = t.health()[1]
        self.assertGreater(stop["at"], r["taken_at"])
        red("the stop stamped after taken_at")

    def test_the_stop_is_stamped_after_the_watcher_exits_and_equals_taken_at(self):
        t = self.take(factory_kw={"stop_polls": 4})
        t.sc.handle("begin")
        first = t.w
        t.turn()
        r = t.sc.handle("snapshot", "post-1")
        stop = t.health()[1]
        self.assertEqual(stop["at"], r["taken_at"])
        self.assertGreaterEqual(stop["at"], first.exited_at)

    def snapshot_opens_seen(self, cls=None):
        t = self.take(sidecar_cls=cls)

        def opener(path, flags):
            rel = os.path.relpath(path, t.run_tree)
            if t.factory.made and t.w is not None:
                t.w.fs(rel, ("OPEN",))        # the snapshot's own open, fed into the running stream
            return os.open(path, flags)
        t.sc.opener = opener
        t.sc.handle("begin")
        t.turn()
        t.sc.handle("snapshot", "post-1")
        t.clock.tick(1.0)   # S7-D4: the drive step's dwell, so the final stop falls strictly after post-N
        t.sc.handle("finish")
        return t

    def test_the_snapshots_own_opens_are_never_logged(self):
        t = self.snapshot_opens_seen()
        self.assertEqual(t.access(), [])
        self.assertEqual(t.load().sidecar_record(), CLEAN)

    def test_mutant_watcher_left_running_through_a_snapshot_goes_red(self):
        class Running(sidecar.Sidecar):
            def _pause(self, label):   # mutant: the snapshot taken while the watcher runs, then the stop
                taken_at = self.clock()
                u, uc, _ = self._snapshot(label, taken_at)
                self._stop()
                return taken_at, u, uc
        t = self.snapshot_opens_seen(Running)
        self.assertIn(PLAN, [a["path"] for a in t.access()])
        red("the watcher left running through a snapshot")


# ------------------------------------------------------------------------------------------------- the watch plan
class TestWatchPlan(TakeCase):
    def test_a_path_created_mid_turn(self):
        t = self.take(watch=("out/new.txt",), files={"out/keep.txt": b"k\n"})
        t.sc.handle("begin")
        self.assertEqual(t.factory.plans[-1], (("", True),))
        t.turn([("out/new.txt", ("CREATE",)), ("out/new.txt", ("MODIFY",)), ("out/new.txt", ("OPEN",))])
        t.sc.handle("snapshot", "post-1")
        t.clock.tick(1.0)   # S7-D4: the drive step's dwell, so the final stop falls strictly after post-N
        t.sc.handle("finish")
        self.assertEqual([a["op"] for a in t.load().accesses(path="out/new.txt", turn=1)],
                         ["modify", "modify", "open"])

    def chain(self, plan_fn=None):
        t = self.take(watch=("a/b/c",), files={"a/keep": b"k\n"})
        if plan_fn:
            with mock.patch.object(sidecar, "watch_plan", plan_fn):
                t.sc.handle("begin")
        else:
            t.sc.handle("begin")
        t.turn([("a/b", ("CREATE", "ISDIR")), ("a/b/c", ("CREATE",)), ("a/b/c", ("OPEN",))])
        os.makedirs(os.path.join(t.run_tree, "a", "b"))
        t.write("a/b/c", b"c\n")
        t.sc.handle("snapshot", "post-1")
        t.clock.tick(1.0)   # S7-D4: the drive step's dwell, so the final stop falls strictly after post-N
        t.sc.handle("finish")
        return t

    def test_a_two_level_missing_chain(self):
        t = self.chain()
        self.assertEqual(t.factory.plans[0], (("", True),))
        self.assertEqual([a["op"] for a in t.load().accesses(path="a/b/c", turn=1)], ["modify", "open"])
        self.assertEqual(len(t.factory.plans), 2)                     # re-chosen at the re-arm

    def test_mutant_non_recursive_watch_goes_red(self):
        real = sidecar.watch_plan
        t = self.chain(lambda rt, w: tuple((d, False) for d, _ in real(rt, w)))
        self.assertEqual(t.load().accesses(path="a/b/c", turn=1), [])
        red("the missing chain watched non-recursively")

    def renames(self, table=None):
        t = self.take()
        ctx = mock.patch.object(sidecar, "EVENT_OPS", table) if table else mock.patch.object(sidecar, "POLL_S",
                                                                                            sidecar.POLL_S)
        with ctx:
            t.sc.handle("begin")
            t.turn([(PLAN, ("MOVED_TO",))])                   # a rename-replace onto the consequential path
            t.sc.handle("snapshot", "post-1")
            t.sc.handle("snapshot", "pre-2")
            t.turn([(PLAN, ("MOVED_FROM",))])                 # a rename away
            t.sc.handle("snapshot", "post-2")
            t.clock.tick(2.0)
            t.w.fs(PLAN, ("MOVED_TO",))                       # a rename-replace after post-N
            t.clock.tick(1.0)
            t.sc.handle("finish")
        return t

    def test_renames(self):
        t = self.renames()
        ev = t.load()
        self.assertEqual([a["op"] for a in ev.accesses(path=PLAN, turn=1)], ["modify"])
        self.assertEqual([a["op"] for a in ev.accesses(path=PLAN, turn=2)], ["delete"])
        self.assertEqual([a["op"] for a in ev.writes_after_the_end()], ["modify"])
        self.assertIn("past post-2", " ".join(ev.operator_check()["problems"]))

    def test_mutant_rename_onto_missed_goes_red(self):
        t = self.renames({k: v for k, v in sidecar.EVENT_OPS.items() if k != "MOVED_TO"})
        self.assertNotIn("modify", [a["op"] for a in t.access()])
        red("a rename-replace onto a consequential path missed")

    def test_mutant_rename_away_missed_goes_red(self):
        t = self.renames(dict(sidecar.EVENT_OPS, MOVED_FROM="open"))
        self.assertNotIn("delete", [a["op"] for a in t.access()])
        red("a rename away not read as a delete")

    def test_mutant_watcher_stopped_at_post_n_goes_red(self):
        class StopsAtPost(sidecar.Sidecar):
            def _snap_command(self, label):   # mutant: the watcher stopped for good at a post snapshot
                r = super()._snap_command(label)
                if label.startswith("post-") and self.watcher is not None:
                    self._stop()
                    self.state = "finished"
                return r
        t = self.take(sidecar_cls=StopsAtPost)
        t.sc.handle("begin")
        t.turn()
        t.sc.handle("snapshot", "post-1")
        t.clock.tick(2.0)
        t.w.fs(PLAN, ("MOVED_TO",))
        t.sc.handle("finish")
        self.assertEqual(t.access(), [])
        red("the watcher stopped at post-N (a late writer never logged)")

    def test_no_snapshot_before_begin_or_after_finish(self):
        t = self.take()
        self.assertFalse(t.sc.handle("snapshot", "post-1")["ok"])
        self.assertFalse(os.path.exists(os.path.join(t.evidence, "snapshots")))
        self.one_turn(t)
        r = t.sc.handle("snapshot", "pre-2")
        self.assertFalse(r["ok"])
        self.assertFalse(os.path.exists(os.path.join(t.evidence, "snapshots", "pre-2.json")))
        self.assertFalse(t.sc.handle("finish")["ok"])
        self.assertFalse(t.sc.handle("begin")["ok"])

    def test_snapshot_labels_follow_the_take(self):
        t = self.take()
        t.sc.handle("begin")
        r = t.sc.handle("snapshot", "pre-2")
        self.assertFalse(r["ok"])
        self.assertIn("out of order", r["problems"][0])
        self.assertFalse(os.path.exists(os.path.join(t.evidence, "snapshots", "pre-2.json")))
        self.assertTrue(t.sc.handle("snapshot", "post-1")["ok"])


# ------------------------------------------------------------------------------------------------- the host half
@dataclass(frozen=True)
class Completed:
    returncode: int
    stdout: str
    stderr: str


class FakeRuntime:
    """Records every (argv, env) it is given and answers from a script; an unexpected call fails the test."""

    def __init__(self, script):
        self.script, self.calls = list(script), []

    def run(self, argv, *, env=None, timeout=None):
        if not isinstance(argv, list):
            raise AssertionError("argv is a list, never a shell string")
        self.calls.append((list(argv), env))
        if not self.script:
            raise AssertionError(f"unexpected runtime call {argv}")
        want, answer = self.script.pop(0)
        if argv[:len(want)] != want:
            raise AssertionError(f"expected {want}, got {argv}")
        return answer


RUN_TREE, EVIDENCE = "/srv/takes/t1/run", "/srv/takes/t1/evidence"


def create(**k):
    kw = dict(image=IMAGE, run_tree=RUN_TREE, evidence=EVIDENCE, watch=[PLAN, "out/x"])
    kw.update(k)
    return sidecar.create_argv(**kw)


def create_problems(argv) -> list:
    """Every fact of the sidecar's create argv that does not hold (the plan's CP2 sidecar task; interfaces 11-12)."""
    p = []
    i = argv.index(IMAGE) if IMAGE in argv else len(argv)
    flags, cmd = argv[:i], argv[i + 1:]
    pairs = list(zip(flags, flags[1:]))
    if flags[:2] != ["docker", "create"]:
        p.append("not docker create")
    for want in [("--network", "none"), ("--user", "0:0"), ("--cap-drop", "ALL"),
                 ("--cap-add", "DAC_READ_SEARCH"), ("--security-opt", "no-new-privileges")]:
        if want not in pairs:
            p.append(f"missing {want}")
    if "--pull=never" not in flags:
        p.append("missing --pull=never")
    if sorted(b for a, b in pairs if a == "--cap-add") != sorted(["DAC_READ_SEARCH", "SETUID", "SETGID", "SETPCAP"]):
        p.append("not exactly the boot-only capability set")
    mounts = [b for a, b in pairs if a == "--mount"]
    if sorted(mounts) != sorted([f"type=bind,source={RUN_TREE},target={RUN_TREE},readonly",
                                 f"type=bind,source={EVIDENCE},target=/srv/ev"]):
        p.append(f"mounts {mounts}")
    for bad in ("--pid", "--ipc", "--volumes-from", "-p", "--publish", "--privileged", "--device", "-e", "--env",
                "--env-file", "-v", "--volume"):
        if any(f == bad or f.startswith(bad + "=") for f in flags):
            p.append(f"forbidden {bad}")
    launcher = list(sidecar.WATCHER_LAUNCHER)
    if cmd[:len(launcher)] != launcher:
        p.append("wrong privilege-drop launcher")
    cmd = cmd[len(launcher):]
    if cmd[:6] != ["python3", "-I", "-B", "/opt/w/sidecar.py", "serve", "--run-tree"]:
        p.append(f"command {cmd[:6]}")
    if cmd[6:9] != [RUN_TREE, "--evidence", "/srv/ev"] or cmd[9:] != ["--watch", PLAN, "--watch", "out/x"]:
        p.append(f"serve arguments {cmd[6:]}")
    return p


class TestHostHalf(unittest.TestCase):
    def test_create_on_a_fake_runtime(self):
        rt = FakeRuntime([(["docker", "create"], Completed(0, CID + "\n", ""))])
        argv = create()
        out = rt.run(argv)
        self.assertEqual(rt.calls, [(argv, None)])
        self.assertEqual(out.stdout.strip(), CID)
        self.assertEqual(create_problems(argv), [])

    def test_mutant_create_argvs_go_red(self):
        base = create()
        mutants = {
            "the run tree mounted read-write": [x.replace(",readonly", "") for x in base],
            "a network": [("bridge" if x == "none" else x) for x in base],
            "root watcher": [("--reuid=0" if x == "--reuid=10002" else x) for x in base],
            "no cap drop": [x for j, x in enumerate(base) if not (x == "--cap-drop" or (j and base[j - 1] ==
                                                                                       "--cap-drop"))],
            "a second capability": base[:3] + ["--cap-add", "SYS_ADMIN"] + base[3:],
            "no no-new-privileges": [("seccomp=unconfined" if x == "no-new-privileges" else x) for x in base],
            "a pulled image": [x for x in base if x != "--pull=never"],
            "a shared pid namespace": base[:3] + ["--pid", "host"] + base[3:],
            "an environment variable": base[:3] + ["-e", "X=1"] + base[3:],
            "privileged": base[:3] + ["--privileged"] + base[3:],
            "a device": base[:3] + ["--device", "/dev/fuse"] + base[3:],
            "a published port": base[:3] + ["-p", "80:80"] + base[3:],
            "a third mount": base[:3] + ["--mount", "type=bind,source=/x,target=/x"] + base[3:],
            "evidence elsewhere": [x.replace("target=/srv/ev", "target=/ev") for x in base],
            "an ipc namespace": base[:3] + ["--ipc", "host"] + base[3:],
            "volumes-from": base[:3] + ["--volumes-from", "x"] + base[3:],
            "another program": [("/opt/w/other.py" if x == "/opt/w/sidecar.py" else x) for x in base],
        }
        for name, argv in mutants.items():
            with self.subTest(name):
                self.assertNotEqual(create_problems(argv), [], name)
                red(f"create argv: {name}")

    def test_create_refuses_bad_inputs(self):
        for k in [dict(image="sidecar:latest"), dict(image="PENDING"), dict(run_tree="rel/run"),
                  dict(run_tree="/srv/ev"), dict(run_tree="/srv/takes/t1"), dict(evidence="/srv/takes/t1/run/ev"),
                  dict(run_tree="/opt"), dict(run_tree="/a,b"), dict(watch=[]), dict(watch=["/abs"]),
                  dict(watch=["a/../b"]), dict(watch=[PLAN, PLAN]), dict(user="0:0"), dict(user="watcher")]:
            with self.subTest(k):
                with self.assertRaises(ValueError):
                    create(**k)

    def test_the_default_user_and_the_shared_values(self):
        import inspect
        self.assertEqual(inspect.signature(sidecar.create_argv).parameters["user"].default, "10002:10002")
        self.assertEqual(sidecar.EVIDENCE_MOUNT, "/srv/ev")
        self.assertEqual(sidecar.PROGRAM, "/opt/w/sidecar.py")
        self.assertEqual(sidecar.UNREADABLE_CONSEQUENTIAL_KEY, "unreadable_consequential")
        self.assertEqual(sidecar.UNREADABLE_CONSEQUENTIAL_ROW, "unreadable-consequential-path")
        self.assertIn(sidecar.UNREADABLE_CONSEQUENTIAL_KEY, sidecar.REPLY_FIELDS)

    def test_expect_from_argv(self):
        self.assertEqual(sidecar.expect_from_argv(create()), {
            "user": "0:0", "network_mode": "none", "cap_drop": ["ALL"], "cap_add": ["PENDING"] * 4,
            "image": IMAGE, "cmd": create()[create().index(IMAGE) + 1:], "entrypoint": [],
            "security_opt": ["no-new-privileges"], "privileged": False, "pid_mode": "",
            "mounts": [{"source": RUN_TREE, "destination": RUN_TREE, "rw": False},
                       {"source": EVIDENCE, "destination": "/srv/ev", "rw": True}]})
        for bad in (create()[:3] + ["--privileged"] + create()[3:], create()[:3] + ["--pid", "host"] + create()[3:]):
            with self.assertRaises(ValueError):
                sidecar.expect_from_argv(bad)

    def test_start_ctl_rm(self):
        self.assertEqual(sidecar.start_argv(CID), ["docker", "start", CID])
        self.assertEqual(sidecar.rm_argv(CID), ["docker", "rm", "-f", CID])
        self.assertEqual(sidecar.ctl_argv(CID, "begin"),
                         ["docker", "exec", "--user", "10002:10002", CID, "python3", "-I", "-B", "/opt/w/sidecar.py", "ctl", "begin"])
        self.assertEqual(sidecar.ctl_argv(CID, "snapshot", "post-1")[-2:], ["snapshot", "post-1"])
        self.assertEqual(sidecar.ctl_argv(CID, "snapshot", "pre-2")[-1], "pre-2")
        for bad in [("snapshot", "post-01"), ("snapshot", "pre-1"), ("snapshot", "post-0"), ("snapshot", None),
                    ("snapshot", "post-1 "), ("snapshot", "mid-1"), ("begin", "pre-1"), ("finish", "post-1"),
                    ("kill", None)]:
            with self.subTest(bad):
                with self.assertRaises(ValueError):
                    sidecar.ctl_argv(CID, *bad)
        for name in ("sidecar-1", CID[:12], CID.upper()):
            for f in (sidecar.start_argv, sidecar.rm_argv, lambda c: sidecar.ctl_argv(c, "status")):
                with self.assertRaises(ValueError):
                    f(name)

    def test_mutant_label_rule_goes_red(self):
        with mock.patch.object(sidecar, "_LABEL", __import__("re").compile(r"(pre|post)-([0-9]+)")):
            self.assertTrue(sidecar.label_ok("post-01"))
        red("the label regex admitting post-01")
        with mock.patch.object(sidecar, "label_ok", lambda lb: bool(sidecar._LABEL.fullmatch(lb or ""))):
            self.assertEqual(sidecar.ctl_argv(CID, "snapshot", "pre-1")[-1], "pre-1")
        red("pre-1 signalled as a snapshot")

    def test_parse_reply(self):
        good = {"ok": True, "command": "snapshot", "label": "post-1", "taken_at": 1.0, "rearmed_at": 2.0,
                "unreadable": ["x"], "unreadable_consequential": ["x"], "problems": []}
        self.assertEqual(sidecar.parse_reply(json.dumps(good) + "\n"), good)
        self.assertEqual(sidecar.parse_completed(Completed(0, json.dumps(good) + "\n", "")), good)
        bads = [json.dumps(good), json.dumps(good) + "\n" + json.dumps(good) + "\n", "not json\n",
                json.dumps(dict(good, extra=1)) + "\n", json.dumps({k: good[k] for k in list(good)[:-1]}) + "\n",
                json.dumps(dict(good, ok="yes")) + "\n", json.dumps(dict(good, command="kill")) + "\n",
                json.dumps(dict(good, label="post-01")) + "\n", json.dumps(dict(good, problems=["p"])) + "\n",
                json.dumps(dict(good, ok=False)) + "\n", json.dumps(dict(good, unreadable=[])) + "\n",
                json.dumps(dict(good, unreadable=["/abs"], unreadable_consequential=[])) + "\n",
                json.dumps(dict(good, rearmed_at=None)) + "\n", json.dumps(dict(good, taken_at="1")) + "\n"]
        for b in bads:
            with self.subTest(b):
                with self.assertRaises(sidecar.ReplyError):
                    sidecar.parse_reply(b)
        with self.assertRaises(sidecar.ReplyError):
            sidecar.parse_completed(Completed(1, json.dumps(good) + "\n", ""))

    def test_endstate_binding(self):
        self.assertEqual(sidecar.LABEL_PATTERN, es._LABEL.pattern)
        self.assertEqual((sidecar.LEDGER, sidecar.ACCESS, sidecar.HEALTH, sidecar.WATCHED), es.FILES)
        self.assertEqual(sidecar.SPECIAL_KINDS, es.SPECIAL_KINDS)
        self.assertEqual((sidecar.SNAPSHOTS, sidecar.BLOBS), es.FOLDERS)
        # review nit 7 (14 Oct): the rescan's file and source are endstate's optional file and admitted source
        self.assertEqual((sidecar.FOUND,), es.OPTIONAL_FILES)
        self.assertIn(sidecar.FOUND_SOURCE, es.FOUND_SOURCES)
        self.assertEqual((sidecar.WATCHER_START, sidecar.WATCHER_STOP, sidecar.QUEUE_OVERFLOW),
                         (es.WATCHER_START, es.WATCHER_STOP, es.QUEUE_OVERFLOW))
        self.assertEqual((sidecar.OPEN, sidecar.MODIFY, sidecar.DELETE), es.ACCESS_OPS)
        self.assertEqual(sidecar.UNREADABLE, {"type": es.UNREADABLE})


# ------------------------------------------------------------------------------------------------- PENDING values
EXPECTED_PENDING = {"inotifywait_argv", "inotifywait_format", "inotifywait_subsecond", "inotifywait_events",
                    "inotify_watch_count", "watch_establish_s"}
# The production CANDIDATE values (box lane, 14 Oct 2026; under review): the no-model stub on Athena's provisional
# watcher image (inotifywait 3.22.6.0) and lane-reports/watch-constants-derivation-20261014-v2.json.
CANDIDATE = {
    "INOTIFYWAIT_ARGV": ("inotifywait", "--monitor", "--format", "%w%f%0%e%0", "--no-newline"),
    "INOTIFYWAIT_FORMAT": {"fields": ["path", "events"], "separator": "\x00", "established": "Watches established.",
                           "setup_lines": ["Setting up watches.  Beware: since -r was given, this may take a while!"]},
    "INOTIFYWAIT_SUBSECOND": False,
    "INOTIFYWAIT_EVENTS": ("OPEN", "MODIFY", "CLOSE_WRITE", "MOVED_TO", "CREATE", "DELETE", "MOVED_FROM",
                           "DELETE_SELF"),
    "INOTIFY_WATCH_COUNT": 696,
    "WATCH_ESTABLISH_S": 1.9,
}


def all_pending():
    """The readiness gate as it stood before the candidate: every watcher value PENDING again, in memory."""
    return mock.patch.multiple(sidecar, **{f.upper(): "PENDING" for f in EXPECTED_PENDING})


class TestPending(unittest.TestCase):
    def test_the_candidate_values_are_exactly_the_measured_ones(self):
        self.assertEqual(sidecar.pending(), {})
        for name, value in CANDIDATE.items():
            self.assertEqual(getattr(sidecar, name), value, name)
        self.assertEqual(set(sidecar.INOTIFYWAIT_EVENTS), set(sidecar.EVENT_OPS))
        self.assertLess(sidecar.WATCH_ESTABLISH_S, sidecar.ESTABLISH_TIMEOUT_S)

    def test_the_pending_set(self):
        with all_pending():
            self.assertEqual(set(sidecar.pending()), EXPECTED_PENDING)

    def test_the_real_factory_refuses_while_pending(self):
        with all_pending():
            with self.assertRaises(sidecar.NotReady):
                sidecar.inotifywait_factory("/srv/takes/t1/run", (("", False),))
            for f in EXPECTED_PENDING:   # each one alone still refuses
                others = {x.upper(): (FORMAT if x == "inotifywait_format" else ["filled-in-memory"])
                          for x in EXPECTED_PENDING - {f}}
                with mock.patch.multiple(sidecar, **others):
                    self.assertEqual(set(sidecar.pending()), {f})
                    with self.assertRaises(sidecar.NotReady):
                        sidecar.inotifywait_factory("/srv/takes/t1/run", (("", False),))

    def test_the_ready_factory_reaches_the_guarded_process_start(self):
        with self.assertRaises(ProcessStartRefused):   # filled values: past the gate, to the (guarded) start
            sidecar.inotifywait_factory("/srv/takes/t1/run", (("", False),))

    def test_mutant_dropping_the_refusal_goes_red(self):
        with all_pending(), mock.patch.object(sidecar, "require_ready", lambda: None):
            with self.assertRaises(ProcessStartRefused):   # it reached the (guarded) process start, not NotReady
                sidecar.inotifywait_factory("/srv/takes/t1/run", (("", False),))
        red("the real factory without its PENDING refusal")

    def test_serve_refuses_while_pending(self):
        with all_pending(), self.assertRaises(sidecar.NotReady):
            sidecar.main(["serve", "--run-tree", "/srv/takes/t1/run", "--evidence", "/srv/ev", "--watch", PLAN])

    def test_no_parameter_overrides_a_pending_value(self):
        with all_pending():
            self.assertEqual(pending_parameters(sidecar), [])
            fake = type(sys)("fake")
            exec("def f(inotifywait_argv=None):\n    pass\n", fake.__dict__)
            fake.pending = sidecar.pending
            self.assertEqual(pending_parameters(fake), ["f(inotifywait_argv)"])
        red("a public function taking a PENDING value")


def pending_parameters(mod) -> list:
    import inspect
    names = set(mod.pending()) | {n.upper() for n in mod.pending()}
    out = []
    for n, obj in vars(mod).items():
        targets = [obj] if inspect.isfunction(obj) else (
            [m for m in vars(obj).values() if inspect.isfunction(m)] if inspect.isclass(obj) else [])
        for fn in targets:
            for p in inspect.signature(fn).parameters:
                if p in names or p.lower() in names:
                    out.append(f"{fn.__name__}({p})")
    return out


# ------------------------------------------------------------------------------------------------- the real parser
class FakeProc:
    """Pipes standing in for the real watcher's stdout and stderr (no process)."""

    def __init__(self, out: bytes, err: bytes, *, keep_err_open: bool = False):
        self.fds, self.rc, self.err_w = [], None, None
        self.stdout = self._pipe(out)
        self.stderr = self._pipe(err, keep_open=keep_err_open)

    def _pipe(self, data, keep_open=False):
        r, w = os.pipe()
        os.set_blocking(r, False)
        os.write(w, data)
        if keep_open:
            self.err_w = w
            self.fds.append(w)
        else:
            os.close(w)
        self.fds.append(r)
        return type("F", (), {"fileno": lambda self_, fd=r: fd})()

    def poll(self):
        return self.rc

    def close(self):
        for fd in self.fds:
            os.close(fd)


FORMAT = {"fields": ["at", "path", "events"], "separator": "\t", "established": "Watches established.",
          "setup_lines": ["Setting up watches.", "Setting up watches.  Beware: since -r was given, this may take a while!"]}


class TestRealParser(unittest.TestCase):
    def parse(self, lines, err=b"Watches established.\n"):
        proc = FakeProc("".join(lines).encode(), err)
        self.addCleanup(proc.close)
        with mock.patch.multiple(sidecar, INOTIFYWAIT_FORMAT=FORMAT, INOTIFYWAIT_SUBSECOND=True):
            w = sidecar._InotifyWatcher(proc, "/srv/rt")
            return w.established(), w.read_ready()

    def test_paths_map_to_the_run_tree_or_to_none(self):
        ok, evs = self.parse(["1.5\t/srv/rt/plan/approved.json\tOPEN\n", "1.6\t/srv/rt/plan/\tDELETE_SELF\n",
                              "1.7\t/elsewhere/x\tOPEN\n", "1.8\t/srv/rt/\tDELETE_SELF\n"])
        self.assertTrue(ok)
        self.assertEqual([(e.at, e.path, e.names) for e in evs],
                         [(1.5, "plan/approved.json", ("OPEN",)), (1.6, "plan", ("DELETE_SELF",)),
                          (1.7, None, ("OPEN",)), (1.8, "", ("DELETE_SELF",))])

    def test_mutant_a_trailing_slash_kept_goes_red(self):
        with mock.patch.object(sidecar, "_strip_slash", lambda p: p):
            _, evs = self.parse(["1.6\t/srv/rt/plan/\tDELETE_SELF\n"])
        self.assertNotEqual(evs[0].path, "plan")
        red("a folder event's trailing slash kept")


# ------------------------------------------------------------------------------------------------- the source
STDLIB = set(sys.stdlib_module_names)


def source_problems(src: str) -> list:
    """The in-container code runs alone on the image's Python: it must parse at 3.11 and import the stdlib only."""
    try:
        tree = ast.parse(src, feature_version=(3, 11))
    except SyntaxError as e:
        return [f"does not parse at 3.11: {e.msg}"]
    out = []
    for node in ast.walk(tree):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
            [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
        if isinstance(node, ast.ImportFrom) and node.level:
            out.append("a relative import")
        for n in names:
            if n.split(".")[0] not in STDLIB:
                out.append(f"imports {n}")
    return out


class TestSource(unittest.TestCase):
    def src(self):
        with open(SIDECAR_SOURCE, encoding="utf-8") as fh:
            return fh.read()

    def test_parses_at_311_and_imports_the_stdlib_only(self):
        self.assertEqual(source_problems(self.src()), [])

    def test_mutants_go_red(self):
        self.assertNotEqual(source_problems(self.src() + "\ntype Alias = int\n"), [])
        red("a 3.12 feature in the in-container code")
        self.assertNotEqual(source_problems(self.src() + "\nimport graders.endstate\n"), [])
        red("an in-container import outside the standard library")

    def test_file_check(self):
        self.assertTrue(file_ok(sidecar.__file__))
        self.assertFalse(file_ok(os.path.join(STUDY, "box", "sidecar", "__init__.py")))
        red("a box/sidecar/__init__.py shadowing the module")


def file_ok(path: str) -> bool:
    return os.path.abspath(path) == os.path.join(STUDY, "box", "sidecar.py")


# ------------------------------------------------------------------------------------------------- fold 2 (lane review 1)
class TestFold2(TakeCase):
    """Lane review round 1's findings, folded on the lane lead's decisions (W4C1-2, -4, -5, -8, -9, -10)."""

    # W4C1-2: a stderr line after the watches are established is a watcher fault
    def stderr_events(self, err: bytes):
        proc = FakeProc(b"", err)
        self.addCleanup(proc.close)
        with mock.patch.multiple(sidecar, INOTIFYWAIT_FORMAT=FORMAT, INOTIFYWAIT_SUBSECOND=True):
            w = sidecar._InotifyWatcher(proc, "/srv/rt")
            self.assertTrue(w.established())
            return w.read_ready()

    LATE = b"Setting up watches.\nWatches established.\nCouldn't watch new directory /srv/rt/a/b: No space left\n"

    def test_a_stderr_line_after_established_is_a_fault(self):
        evs = self.stderr_events(self.LATE)
        self.assertEqual([(e.path, e.names) for e in evs], [("", (sidecar.STDERR_EVENT,))])
        self.assertNotIn("a/b", repr(evs))                       # the line's class only, never its path text
        t = self.take()
        t.sc.handle("begin")
        t.w.queue.extend(evs)
        t.sc.pump()
        self.assertEqual(t.health()[-1]["kind"], "watcher-stop")
        self.assertNotEqual(t.health()[-1]["exit_code"], 0)

    def test_a_stderr_line_before_established_is_not_a_fault(self):
        self.assertEqual(self.stderr_events(b"Setting up watches.\nWatches established.\n"), [])

    def test_mutant_stderr_ignored_goes_red(self):
        with mock.patch.object(sidecar._InotifyWatcher, "_stderr_events", lambda self: []):
            evs = self.stderr_events(self.LATE)
        self.assertEqual(evs, [])
        red("stderr ignored after the watches are established")

    def test_the_format_reason_names_stderr_and_the_forced_events(self):
        with all_pending():   # the candidate fills the values; the reasons stay the definitions they were measured by
            why = sidecar.pending()
        self.assertIn("stderr lines", why["inotifywait_format"])
        self.assertIn("IGNORED", why["inotifywait_events"])
        self.assertIn("UNMOUNT", why["inotifywait_events"])
        self.assertIn("new folder", why["watch_establish_s"])

    # W4C1-4 (a): the control channel lies outside the evidence folder and every run tree
    def test_the_control_folder(self):
        self.assertTrue(sidecar.ctl_dir_ok())
        self.assertTrue(sidecar.CTL_DIR.startswith(("/tmp/", "/run/")))

    def test_mutant_control_folder_in_the_evidence_goes_red(self):
        for bad in ("/srv/ev/ctl", "/srv/ctl", "/srv"):
            with mock.patch.object(sidecar, "CTL_DIR", bad):
                self.assertFalse(sidecar.ctl_dir_ok())
        red("the control channel inside the evidence folder")

    # W4C1-4 (b): an ok reply's re-arm is never before its snapshot
    GOOD = {"ok": True, "command": "snapshot", "label": "post-1", "taken_at": 2.0, "rearmed_at": 3.0,
            "unreadable": [], "unreadable_consequential": [], "problems": []}

    def test_a_rearm_before_its_snapshot_is_refused(self):
        with self.assertRaises(sidecar.ReplyError):
            sidecar.parse_reply(json.dumps(dict(self.GOOD, rearmed_at=1.5)) + "\n")

    def test_mutant_rearm_order_unchecked_goes_red(self):
        with mock.patch.object(sidecar, "_rearm_order_ok", lambda r: True):
            self.assertEqual(sidecar.parse_reply(json.dumps(dict(self.GOOD, rearmed_at=1.5)) + "\n")["rearmed_at"],
                             1.5)
        red("a re-arm stamped before its snapshot accepted")

    # W4C1-5: a consequential folder moved away also deletes the consequential paths beneath it
    def nested(self):
        t = self.take(watch=("out", "out/plan.json"), files={"out/plan.json": b"{}\n"})
        t.sc.handle("begin")
        t.turn([("out", ("MOVED_FROM", "ISDIR"))])
        t.sc.handle("snapshot", "post-1")
        t.sc.handle("finish")
        return sorted((a["path"], a["op"]) for a in t.access())

    def test_a_consequential_folder_moved_deletes_what_is_beneath(self):
        self.assertEqual(self.nested(), [("out", "delete"), ("out/plan.json", "delete")])

    def test_mutant_nested_paths_skipped_goes_red(self):
        real = sidecar.Sidecar._move_targets
        with mock.patch.object(sidecar.Sidecar, "_move_targets",
                               lambda self, path: [] if path in self.watch else real(self, path)):
            self.assertEqual(self.nested(), [("out", "delete")])
        red("a moved consequential folder skips the paths beneath it")

    # W4C1-8: a watch path segment starting with "-" is refused (serve's argparse would read it as an option)
    def test_a_dash_segment_is_refused(self):
        for bad in (["-x"], ["a/-b"], ["--run-tree"]):
            with self.subTest(bad):
                with self.assertRaises(ValueError):
                    create(watch=bad)
                with self.assertRaises(ValueError):
                    sidecar.Sidecar(run_tree="/x", evidence="/y", watch=bad, factory=None)

    def test_mutant_dash_segment_accepted_goes_red(self):
        with mock.patch.object(sidecar, "watch_path_ok", sidecar.rel_path_ok):
            self.assertIn("-x", create(watch=["-x"]))
        red("a watch path starting with - accepted")

    # W4C1-9: a request that is JSON but not an object gets an ok: false reply, never an uncaught error
    def test_a_non_object_request(self):
        t = self.take()
        for raw in (b"[1]\n", b"3\n", b"\"begin\"\n", b"not json\n"):
            with self.subTest(raw):
                r = sidecar._handle_request(t.sc, raw)
                self.assertFalse(r["ok"])
                self.assertEqual(r["command"], "status")
        self.assertTrue(sidecar._handle_request(t.sc, b'{"command": "begin", "label": null}\n')["ok"])

    def test_mutant_request_shape_unchecked_goes_red(self):
        t = self.take()
        with mock.patch.object(sidecar, "_request_ok", lambda req: True):
            with self.assertRaises(AttributeError):
                sidecar._handle_request(t.sc, b"[1]\n")
        red("a non-object request reaching the handler (PID 1 dies)")

    # W4C1-10: the stream is not logged after a fault
    def test_nothing_is_logged_after_a_fault(self):
        t = self.take()
        t.sc.handle("begin")
        t.w.queue.extend([sidecar.WatchEvent(t.clock.time(), PLAN, ("ACCESS",)),
                          sidecar.WatchEvent(t.clock.time(), PLAN, ("OPEN",))])
        t.sc.pump()
        self.assertEqual(t.access(), [])

    def test_mutant_logging_on_after_a_fault_goes_red(self):
        def logs_on(self, *, log=True):
            results = [self._event(ev) for ev in self.watcher.read_ready()] if log else []
            return all(results)
        with mock.patch.object(sidecar.Sidecar, "_drain", logs_on):
            t = self.take()
            t.sc.handle("begin")
            t.w.queue.extend([sidecar.WatchEvent(t.clock.time(), PLAN, ("ACCESS",)),
                              sidecar.WatchEvent(t.clock.time(), PLAN, ("OPEN",))])
            t.sc.pump()
        self.assertNotEqual(t.access(), [])
        red("the stream logged on after a fault")

    # W4C1-10: a watcher that dies before it is established is given up on at once, not at the timeout
    def dead_before_established(self):
        t = self.take(factory_kw={"establish_after": 10 ** 9})
        real = t.factory.__call__

        def dying(run_tree, plan):
            w = Factory.__call__(t.factory, run_tree, plan)
            w.die(1)
            return w
        t.sc.factory = dying
        t0 = t.clock.time()
        r = t.sc.handle("begin")
        self.assertFalse(r["ok"])
        del real
        return t.clock.time() - t0

    def test_a_death_before_established_is_seen_at_once(self):
        self.assertLess(self.dead_before_established(), 1.0)

    def test_mutant_death_while_arming_unseen_goes_red(self):
        with mock.patch.object(sidecar.Sidecar, "_arm_gave_up",
                               lambda self, w, t0: self.clock() - t0 > self.establish_timeout_s):
            self.assertGreater(self.dead_before_established(), sidecar.ESTABLISH_TIMEOUT_S)
        red("a death while arming seen only at the timeout")


# ------------------------------------------------------------------------------------------------- fold 3 (lane review 2)
class TestFold3(TakeCase):
    """Lane review round 2's findings, folded on the lane lead's decisions (W4C2-2 to W4C2-7). The ast check
    (W4C2-1) is in TestProcessCheck. No guard-evasion form is written here (glitch-f3's standing rule)."""

    def watcher(self, err: bytes, *, keep_err_open=False, out: bytes = b""):
        proc = FakeProc(out, err, keep_err_open=keep_err_open)
        self.addCleanup(proc.close)
        p = mock.patch.multiple(sidecar, INOTIFYWAIT_FORMAT=FORMAT, INOTIFYWAIT_SUBSECOND=True)
        p.start()
        self.addCleanup(p.stop)
        return proc, sidecar._InotifyWatcher(proc, "/srv/rt")

    # W4C2-2: a stderr line written after established and after a first read is still read
    def late(self):
        proc, w = self.watcher(b"Setting up watches.\nWatches established.\n", keep_err_open=True)
        self.assertTrue(w.established())
        self.assertEqual(w.read_ready(), [])
        os.write(proc.err_w, b"Couldn't watch new directory /srv/rt/a/b: No space left on device\n")
        return w.read_ready()

    def test_a_late_stderr_line_is_a_fault(self):
        self.assertEqual([(e.path, e.names) for e in self.late()], [("", (sidecar.STDERR_EVENT,))])

    def test_mutant_no_drain_loop_goes_red(self):
        with mock.patch.object(sidecar._InotifyWatcher, "_drain_stderr", lambda self: None):
            self.assertEqual(self.late(), [])
        red("stderr not drained after the first read (a late line reads clean)")

    # W4C2-3: only the format's closed setup lines may come before the marker
    PRE = b"Setting up watches.\nCouldn't watch /srv/rt/a: Permission denied\nWatches established.\n"

    def test_an_unknown_line_before_the_marker_fails_the_arm(self):
        _, w = self.watcher(self.PRE)
        self.assertFalse(w.established())
        self.assertTrue(w.setup_failed())
        _, w2 = self.watcher(b"something Watches established.\n")
        self.assertFalse(w2.established())
        self.assertTrue(w2.setup_failed())
        _, ok = self.watcher(b"Setting up watches.\nWatches established.\n")
        self.assertTrue(ok.established())
        self.assertFalse(ok.setup_failed())

    def test_mutant_any_line_before_the_marker_goes_red(self):
        with mock.patch.object(sidecar._InotifyWatcher, "_setup_line_ok", lambda self, line: True):
            _, w = self.watcher(self.PRE)
            self.assertTrue(w.established())
        red("any line before the marker accepted")

    def test_the_format_reason_names_the_setup_lines(self):
        with all_pending():
            self.assertIn("setup lines", sidecar.pending()["inotifywait_format"])

    def setup_failing_take(self):
        t = self.take(factory_kw={"establish_after": 10 ** 9})

        def failing(run_tree, plan):
            w = Factory.__call__(t.factory, run_tree, plan)
            w.setup_failed = lambda: True
            return w
        t.sc.factory = failing
        t0 = t.clock.time()
        r = t.sc.handle("begin")
        return t, r, t.clock.time() - t0

    def test_a_setup_failure_fails_the_arm_at_once(self):
        t, r, elapsed = self.setup_failing_take()
        self.assertFalse(r["ok"])
        self.assertIsNone(r["rearmed_at"])
        self.assertEqual(t.health(), [])               # no watcher-start
        self.assertLess(elapsed, 1.0)
        self.assertEqual(t.factory.made[-1].rc, -signal.SIGKILL)   # W4C3-3: the abandoned watcher is killed

    def test_mutant_setup_failure_unseen_goes_red(self):
        with mock.patch.object(sidecar.Sidecar, "_arm_gave_up",
                               lambda self, w, t0: w.poll() is not None or self.clock() - t0 > self.establish_timeout_s):
            _, _, elapsed = self.setup_failing_take()
        self.assertGreater(elapsed, sidecar.ESTABLISH_TIMEOUT_S)
        red("a setup failure seen only at the timeout")

    # W4C2-4: an exited watcher's unterminated last stderr line counts
    def tail(self, rc):
        proc, w = self.watcher(b"Watches established.\nFailed to watch /srv/rt/x; upper limit on inotify watches")
        self.assertTrue(w.established())
        proc.rc = rc
        return w.read_ready()

    def test_an_exited_watchers_tail_is_a_fault(self):
        self.assertEqual([e.names for e in self.tail(1)], [(sidecar.STDERR_EVENT,)])
        self.assertEqual(self.tail(None), [])         # still running: the line may yet complete

    def test_mutant_tail_never_counted_goes_red(self):
        with mock.patch.object(sidecar._InotifyWatcher, "_tail_counts", lambda self: False):
            self.assertEqual(self.tail(1), [])
        red("an exited watcher's unterminated stderr tail never counted")

    # W4C2-5: CTL_DIR is normalised, with a non-empty segment under /tmp/ or /run/
    def test_the_control_folder_is_normalised(self):
        for bad in ("/tmp/../srv/ev/ctl", "/tmp/", "/run/", "/tmp", "/tmp//w"):
            with self.subTest(bad):
                with mock.patch.object(sidecar, "CTL_DIR", bad):
                    self.assertFalse(sidecar.ctl_dir_ok())
        for good in ("/tmp/w-ctl", "/run/w"):
            with mock.patch.object(sidecar, "CTL_DIR", good):
                self.assertTrue(sidecar.ctl_dir_ok())

    def test_mutant_unnormalised_control_folder_goes_red(self):
        with mock.patch.object(sidecar, "CTL_DIR", "/tmp/../srv/ev/ctl"), \
                mock.patch.object(sidecar.os.path, "normpath", lambda p: p):
            self.assertTrue(sidecar.ctl_dir_ok())
        red("an unnormalised control folder accepted")

    # W4C2-6: a deeply nested request is an ok: false reply
    def test_a_deeply_nested_request(self):
        t = self.take()
        r = sidecar._handle_request(t.sc, b"[" * 100000)
        self.assertFalse(r["ok"])
        self.assertEqual(t.sc.state, "new")

    def test_mutant_recursion_uncaught_goes_red(self):
        t = self.take()
        with mock.patch.object(sidecar, "_REQUEST_ERRORS", (ValueError,)):
            with self.assertRaises(RecursionError):
                sidecar._handle_request(t.sc, b"[" * 100000)
        red("a deeply nested request kills PID 1")


class TestFold3Ast(unittest.TestCase):
    """W4C2-1 and W4C2-7: the ast check's attribute vocabulary and the factory's Popen shape, judged by
    construction (no evasion form is planted: glitch-f3's standing rule)."""

    REL = "box/sidecar.py"

    def problems(self, src, spec=None):
        return process_problems(src, self.REL, spec or BOX_MODULES[self.REL], SUBPROCESS_SITES[self.REL])

    def test_each_vocabulary_is_exactly_the_modules_own(self):
        for rel, spec in BOX_MODULES.items():
            with self.subTest(rel):
                used = {n.attr for n in ast.walk(ast.parse(_source(rel))) if isinstance(n, ast.Attribute)}
                self.assertEqual(spec["attrs"], used)
                self.assertFalse([a for a in spec["attrs"] if a.startswith("__")])

    def test_an_unlisted_method_name_is_still_refused(self):
        """glitch-06 ruling, 14 Oct: the rescan's two names are listed; any other new method name still refuses."""
        src = _source(self.REL) + "\n\ndef _planted(sc):\n    return sc._found_elsewhere()\n"
        got = [p for p in self.problems(src) if "_found_elsewhere" in p]
        self.assertEqual(got, [f"{self.REL}: the attribute _found_elsewhere, outside its vocabulary"])
        self.assertEqual([p for p in self.problems(_source(self.REL)) if "_found" in p or "_present_beneath" in p], [])

    def test_mutant_vocabulary_widened_goes_red(self):
        spec = dict(BOX_MODULES[self.REL])
        spec["attrs"] = spec["attrs"] | {"popen"}
        spec["imports"] = dict(spec["imports"], os=spec["imports"]["os"] | {"popen"})
        self.assertEqual(self.problems(PLANTED["os.popen"](_source(self.REL)), spec), [])
        red("the attribute vocabulary widened (os.popen through)")

    def test_mutant_vocabulary_emptied_goes_red(self):
        spec = dict(BOX_MODULES[self.REL], attrs=set())
        self.assertNotEqual(self.problems(_source(self.REL), spec), [])
        red("the attribute vocabulary emptied (the real module refused)")

    def test_a_dunder_attribute_is_refused_even_when_listed(self):
        spec = dict(BOX_MODULES[self.REL])
        spec["attrs"] = spec["attrs"] | {"__dict__"}
        spec["imports"] = dict(spec["imports"], os=spec["imports"]["os"] | {"__dict__"})
        got = self.problems(PLANTED["os.__dict__['kill']"](_source(self.REL)), spec)
        self.assertEqual(got, ["box/sidecar.py: the dunder attribute __dict__"])

    def test_the_popen_shape_holds_and_binds(self):
        src = _source(self.REL)
        self.assertEqual(self.problems(src), [])
        changed = src.replace("shell=False, close_fds=True)", "shell=False, close_fds=True, cwd=run_tree)", 1)
        self.assertNotEqual(changed, src)
        self.assertIn("box/sidecar.py: Popen's keywords are not exactly the pinned shape", self.problems(changed))

    def test_mutant_popen_shape_unpinned_goes_red(self):
        src = _source(self.REL)
        changed = src.replace("shell=False, close_fds=True)", "shell=False, close_fds=True, cwd=run_tree)", 1)
        with mock.patch.object(sys.modules[__name__], "POPEN_KEYWORDS",
                               dict(POPEN_KEYWORDS, cwd=None)):
            self.assertEqual(self.problems(changed), [])
        red("the Popen keyword shape widened (cwd accepted)")


# ------------------------------------------------------------------------------------------------- fold 4 (lane review 3)
class TestFold4(TakeCase):
    """Lane review round 3's findings, folded on the lane lead's decisions (W4C3-1 to W4C3-5). No guard-evasion
    form is written (glitch-f3's standing rule); the ast mutants only widen or empty this lane's own lists."""

    REL = "box/sidecar.py"

    # W4C3-1: free names are default-deny
    def test_each_names_set_is_exactly_the_modules_own(self):
        for rel, spec in BOX_MODULES.items():
            with self.subTest(rel):
                self.assertEqual(spec["names"], free_names(ast.parse(_source(rel))))

    def test_mutant_names_widened_goes_red(self):
        spec = dict(BOX_MODULES[self.REL], names=BOX_MODULES[self.REL]["names"] | {"eval"})
        with mock.patch.object(sys.modules[__name__], "REFUSED_BUILTINS", REFUSED_BUILTINS - {"eval"}):
            got = process_problems(PLANTED["eval"](_source(self.REL)), self.REL, spec, SUBPROCESS_SITES[self.REL])
        self.assertEqual(got, [])
        red("the free-name set widened (with the builtin denylist narrowed, eval through)")

    def test_a_free_name_outside_the_set_is_refused(self):
        with mock.patch.object(sys.modules[__name__], "REFUSED_BUILTINS", REFUSED_BUILTINS - {"eval"}):
            got = process_problems(PLANTED["eval"](_source(self.REL)), self.REL, BOX_MODULES[self.REL],
                                   SUBPROCESS_SITES[self.REL])
        self.assertIn("box/sidecar.py: the free name eval, outside its closed set", got)

    def test_mutant_names_emptied_goes_red(self):
        spec = dict(BOX_MODULES[self.REL], names=set())
        self.assertNotEqual(process_problems(_source(self.REL), self.REL, spec, SUBPROCESS_SITES[self.REL]), [])
        red("the free-name set emptied (the real module refused)")

    # W4C3-2: a filled format's shape
    def test_a_badly_filled_format_still_reads_pending(self):
        for bad in (dict(FORMAT, setup_lines="PENDING"), dict(FORMAT, setup_lines="Setting up watches."),
                    {k: v for k, v in FORMAT.items() if k != "setup_lines"}, dict(FORMAT, setup_lines=[""]),
                    dict(FORMAT, setup_lines=["PENDING"]), dict(FORMAT, extra=1), dict(FORMAT, established="PENDING"),
                    # fold 5, W4C4-2: the other three keys type-checked
                    dict(FORMAT, fields="PENDING"), dict(FORMAT, fields="x"), dict(FORMAT, fields=[]),
                    dict(FORMAT, fields=[""]), dict(FORMAT, fields={"path": 1, "events": 2}), dict(FORMAT, fields=None),
                    dict(FORMAT, fields=["at", "path"]), dict(FORMAT, fields=["path", "events", "path"]),
                    dict(FORMAT, fields=["path", "events", "PENDING"]),
                    dict(FORMAT, separator=""), dict(FORMAT, separator=None), dict(FORMAT, separator="PENDING"),
                    dict(FORMAT, established=""), dict(FORMAT, established=None)):
            with self.subTest(bad):
                with mock.patch.object(sidecar, "INOTIFYWAIT_FORMAT", bad):
                    self.assertIn("inotifywait_format", sidecar.pending())
        with mock.patch.object(sidecar, "INOTIFYWAIT_FORMAT", FORMAT):
            self.assertNotIn("inotifywait_format", sidecar.pending())

    def test_mutant_format_shape_unchecked_goes_red(self):
        with mock.patch.object(sidecar, "_format_ok", lambda fmt: True), \
                mock.patch.object(sidecar, "INOTIFYWAIT_FORMAT", dict(FORMAT, setup_lines="PENDING")):
            self.assertNotIn("inotifywait_format", sidecar.pending())
        red("a filled format with setup_lines still PENDING read as ready")

    # W4C3-3: an abandoned watcher is killed
    def test_mutant_abandoned_watcher_left_running_goes_red(self):
        with mock.patch.object(sidecar.Sidecar, "_abandon", lambda self, w: None):
            t, r, _ = TestFold3.setup_failing_take(self)
        self.assertIsNone(t.factory.made[-1].rc)
        red("a watcher given up on while arming left running")

    # W4C3-5: a fault in the last drain after a self-exit is a fault
    def died_with_a_fault(self):
        t = self.take()
        t.sc.handle("begin")
        w = t.w

        def dying_poll():   # it exits between the first drain and the poll, leaving a faulting line behind
            if w.rc is None:
                w.rc = 1
                w.queue.append(sidecar.WatchEvent(t.clock.time(), PLAN, ("ACCESS",)))
            return w.rc
        w.poll = dying_poll
        t.sc.pump()
        return t

    def test_a_fault_in_the_last_drain_is_named(self):
        t = self.died_with_a_fault()
        self.assertTrue(any("faulted" in p for p in t.sc.problems), t.sc.problems)
        self.assertEqual(t.health()[-1]["exit_code"], 1)

    def test_mutant_last_drain_fault_dropped_goes_red(self):
        real = sidecar.Sidecar._drain
        with mock.patch.object(sidecar.Sidecar, "_drain", lambda self, log=True: real(self, log=log) or True):
            t = self.died_with_a_fault()
        self.assertFalse(any("faulted" in p for p in t.sc.problems))
        red("a fault in the last drain after a self-exit dropped")


# ------------------------------------------------------------------------------------------------- fold 5 (lane review 4)
# A planted positive for W4C4-1 (the guarded case itself, on a two-line source of its own, never on a real module):
# a parameter named after a builtin, read elsewhere.
REBIND_POSITIVE = "def f(len):\n    return 1\n\ndef g(x):\n    return len(x)\n"
REBIND_SPEC = {"imports": {}, "from": set(), "attrs": set(), "rebinds": set(), "names": {"len"}}


class TestFold5(unittest.TestCase):
    """Lane review round 4's two MINORs, folded on the lane lead's decisions (W4C4-1, W4C4-2)."""

    def test_each_rebinds_set_is_exactly_the_modules_own(self):
        for rel, spec in BOX_MODULES.items():
            with self.subTest(rel):
                self.assertEqual(spec["rebinds"], set())
                self.assertEqual(shielded_bindings(ast.parse(_source(rel))), spec["rebinds"])

    def test_a_builtin_binding_is_refused_and_never_exempts_a_read(self):
        got = process_problems(REBIND_POSITIVE, "m", REBIND_SPEC, [])
        self.assertEqual(got, ["m: binds the builtin or dunder name len, outside its closed rebinds set"])
        self.assertIn("len", free_names(ast.parse(REBIND_POSITIVE)))

    def test_mutant_rebinds_widened_goes_red(self):
        self.assertEqual(process_problems(REBIND_POSITIVE, "m", dict(REBIND_SPEC, rebinds={"len"}), []), [])
        red("the rebinds set widened (a builtin binding accepted)")

    def test_mutant_rebind_rule_dropped_goes_red(self):
        with mock.patch.object(sys.modules[__name__], "shielded_bindings", lambda tree: set()), \
                mock.patch.object(sys.modules[__name__], "free_names", _old_free_names):
            got = process_problems(REBIND_POSITIVE, "m", dict(REBIND_SPEC, names=set()), [])
        self.assertEqual(got, [])
        red("a builtin binding exempting its reads (the module-wide exemption back)")

    def test_mutant_format_types_unchecked_goes_red(self):
        def old(fmt):   # fold 4's _format_ok: setup_lines typed, the rest compared as list(str)
            if not isinstance(fmt, dict) or sorted(fmt) != sorted(sidecar.FORMAT_KEYS):
                return False
            lines = fmt["setup_lines"]
            if not isinstance(lines, (list, tuple)) or not all(isinstance(x, str) and x for x in lines):
                return False
            return "PENDING" not in [fmt["separator"], fmt["established"]] + list(fmt["fields"]) + list(lines)
        with mock.patch.object(sidecar, "_format_ok", old), \
                mock.patch.object(sidecar, "INOTIFYWAIT_FORMAT", dict(FORMAT, fields="PENDING")):
            self.assertNotIn("inotifywait_format", sidecar.pending())
        red("a format whose fields is the string PENDING read as ready")


# ------------------------------------------------------------------------------------------------- interface 10's ast check
# Default-deny by construction (fold 2, W4C1-1, the lane lead's decision). For each of this lane's non-test box
# modules: the closed set of modules it may import, and for each, the closed set of attribute chains it may use
# (a module name is only ever the root of one of these chains: `x = os`, `socket.os`, `os.__dict__`, `os.popen` and
# `argparse._os` are all refused); the closed set of `from` imports; and its subprocess call sites. Test files are
# out of this check's scope.
BOX_MODULES = {
    "box/sidecar.py": {
        "imports": {
            "argparse": {"ArgumentParser"},
            "errno": {"EACCES", "ENOENT"},
            "hashlib": {"sha256"},
            "json": {"dumps", "loads"},
            "os": {"O_CLOEXEC", "O_CREAT", "O_EXCL", "O_NOFOLLOW", "O_NONBLOCK", "O_RDONLY", "O_WRONLY", "close",
                   "fdopen", "fstat", "fsync", "listdir", "lstat", "makedirs", "mkdir", "open", "path.basename",
                   "path.dirname", "path.join", "path.lexists", "path.normpath", "read", "readlink", "rename",
                   "scandir", "set_blocking", "unlink"},
            "re": {"compile"},
            "selectors": {"DefaultSelector", "EVENT_READ"},
            "signal": {"SIGKILL", "SIGTERM", "signal"},
            "socket": {"AF_UNIX", "SOCK_STREAM", "socket"},
            "stat": {"S_ISBLK", "S_ISCHR", "S_ISDIR", "S_ISFIFO", "S_ISLNK", "S_ISREG", "S_ISSOCK"},   # S7-D1
            "subprocess": {"PIPE", "Popen"},
            "sys": {"exit", "stdout.write"},
            "time": {"sleep", "time"},
        },
        "from": {("__future__", "annotations"), ("dataclasses", "dataclass")},
        # every free (unbound) Load name the module uses, derived once from its source (fold 4, W4C3-1)
        # builtin or dunder names the module may bind: closed and pinned, empty today (fold 5, W4C4-1)
        "rebinds": set(),
        "names": {
            'BaseException', 'BlockingIOError', 'Exception', 'FileExistsError', 'FileNotFoundError', 'OSError',
            'RecursionError', 'RuntimeError', 'ValueError', '__name__', 'all', 'any', 'bool', 'bytes', 'dict',
            'float', 'int', 'isinstance', 'len', 'list', 'max', 'min', 'open', 'range', 'repr', 'set', 'sorted',
            'str', 'tuple', 'type', 'zip'},
        # every Attribute.attr the module uses, derived once from its source (fold 3, W4C2-1)
        "attrs": {
            '_abandon', 'AF_UNIX', 'ArgumentParser', 'DefaultSelector', 'EACCES', 'ENOENT', 'EVENT_READ', 'O_CLOEXEC', 'O_CREAT',
            'O_EXCL', 'O_NOFOLLOW', 'O_NONBLOCK', 'O_RDONLY', 'O_WRONLY', 'PIPE', 'Popen', 'SIGKILL', 'SIGTERM',
            'SOCK_STREAM', 'S_ISBLK', 'S_ISCHR', 'S_ISDIR', 'S_ISFIFO', 'S_ISLNK', 'S_ISREG', 'S_ISSOCK', '_access', '_arm', '_arm_gave_up', '_begin', '_beneath',
            '_break', '_drain', '_drain_stderr', '_err', '_established', '_ev', '_event', '_finish', '_floor',
            '_health', '_move_targets', '_out',
            # glitch-06 ruling, 14 Oct 2026: exactly the new-folder rescan's two methods.
            '_found', '_present_beneath',
            # glitch-06's ruling on review r2-1 (14 Oct): the interval's ignored-newline count
            '_ignored_newline', '_pause', '_read', '_reply', '_setup_fault', '_setup_line_ok',
            '_snap_command', '_snapshot', '_stamp', '_stderr_events', '_stop', '_sweep_temps', '_tail_counts',
            '_temps', '_wait_exit', 'accept', 'add', 'add_argument', 'add_parser', 'add_subparsers', 'append', 'at',
            'basename', 'bind', 'clock', 'close', 'command', 'compile', 'connect', 'count', 'decode', 'dirname',
            'discard', 'dumps', 'encode', 'endswith', 'establish_timeout_s', 'established', 'evidence', 'exit',
            'factory', 'fdopen', 'fileno', 'flush', 'force_stop', 'fstat', 'fsync', 'fullmatch', 'get', 'group',
            'groups', 'handle', 'hexdigest', 'items', 'join', 'kill', 'label', 'lexists', 'listdir', 'listen',
            'loads', 'lstat', 'lstrip', 'makedirs', 'makefile', 'mkdir', 'mode', 'name', 'names', 'next_label',
            'normpath', 'open', 'opener', 'parse_args', 'partition', 'path', 'poll', 'problems', 'proc', 'pump',
            'read', 'read_ready', 'readline', 'readlink', 'register', 'rename', 'request_stop', 'returncode',
            'rpartition', 'rsplit', 'rstrip', 'run_tree', 'scandir', 'select', 'set_blocking', 'setdefault',
            'setup_failed', 'sha256', 'signal', 'sleep', 'socket', 'split', 'st_mode', 'startswith', 'state',
            'stderr', 'stdout', 'stop_timeout_s', 'terminate', 'time', 'unlink', 'update', 'values', 'watch',
            'watcher', 'write'},
    },
    "box/scan_record.py": {
        "imports": {
            "hashlib": {"sha256"},
            "json": {"loads"},
            # OD57's probe (16 Oct 2026): its own temporary folder and file, removed after the rules scanner reads it
            "os": {"O_NOFOLLOW", "O_NONBLOCK", "O_RDONLY", "close", "fsync", "getuid", "lstat", "open",
                   "path.abspath", "path.basename", "path.dirname", "path.isabs", "path.join", "path.lexists",
                   "path.realpath", "read", "rmdir", "unlink"},
            "re": {"compile"},
            "scrub": {"NOTE"},
            "stat": {"S_IMODE", "S_ISREG"},
            "sys": {"path", "path.insert"},
            "tempfile": {"mkdtemp"},
        },
        # lane vendor-b24 (B24-2 item 1): OD57's rule set lives in box/od57_rule.py, audited below
        # lane d8-furniture (glitch-f1's ruling, 22 Oct 2026): the per-harness furniture tables, data only
        "from": {("__future__", "annotations"), ("box", "od57_rule"), ("box", "harness_furniture")},
        # builtin or dunder names the module may bind: closed and pinned, empty today (fold 5, W4C4-1)
        "rebinds": set(),
        "names": {
            'OSError', 'RuntimeError', 'UnicodeDecodeError', 'ValueError', '__file__', 'all', 'any', 'bool', 'bytes',
            'callable', 'dict', 'enumerate', 'int', 'isinstance', 'len', 'list', 'open', 'set', 'sorted', 'str',
            'tuple', 'type', 'zip'},
        "attrs": {
            'NOTE', 'O_NOFOLLOW', 'O_NONBLOCK', 'O_RDONLY', 'S_IMODE', 'S_ISREG', 'abspath', 'add', 'append',
            'close', 'compile', 'count', 'decode', 'dirname', 'encode', 'endswith', 'fileno', 'find', 'flush',
            'fsync', 'fullmatch', 'getuid', 'group', 'hexdigest', 'insert', 'isabs', 'items', 'join', 'lexists',
            'realpath',
            'loads', 'lstat', 'open', 'path', 'read', 'setdefault', 'sha256', 'split', 'st_mode', 'st_uid',
            'truncate', 'write',
            # OD57's exact ruling (16 Oct 2026): the probe
            'basename', 'get', 'mkdtemp', 'replace', 'rmdir', 'rstrip', 'unlink',
            # lane vendor-b24: the names this module takes from box/od57_rule
            'CALL_KEYS', 'COPIES', 'GIT_KEYS', 'RESULT_KEYS', 'RULED_LINES', 'SHAPE_KEYS', 'TOOL_KEYS', 'TOOL_KINDS',
            '_CLAUDE_AT', '_ruled_bash', 'check_shapes', 'ruled_text',
            # lane d8-furniture: the names this module takes from box/harness_furniture
            'ACCOUNT_CLASSES', 'FURNITURE', 'FURNITURE_KEYS'},
    },
    # lane d8-furniture (glitch-f1's ruling, 22 Oct 2026): the per-harness furniture tables, data only
    "box/harness_furniture.py": {"imports": {}, "from": set(), "rebinds": set(), "names": set(), "attrs": set()},
    # lane vendor-b24 (B24-2 item 1): OD57's one rule set, shared with the aegis door: no process, no file, no import
    # but the standard library's text tools
    "box/od57_rule.py": {
        "imports": {
            "hashlib": {"sha256"},
            "json": {"dumps", "loads"},
            "posixpath": {"normpath"},
            "re": {"S", "compile", "fullmatch"},
            "shlex": {"shlex"},
        },
        "from": {("__future__", "annotations")},
        "rebinds": set(),
        "names": {
            'RuntimeError', 'ValueError', 'abs', 'all', 'any', 'bool', 'bytes', 'dict', 'enumerate', 'frozenset',
            'int', 'isinstance', 'len', 'list', 'next', 'range', 'set', 'sorted', 'str', 'sum', 'tuple', 'type',
            'zip'},
        "attrs": {
            'S', 'add', 'append', 'commenters', 'compile', 'count', 'decode', 'dumps', 'encode', 'endswith', 'find',
            'fullmatch', 'get', 'hexdigest', 'items', 'loads', 'normpath', 'pop', 'rstrip', 'setdefault', 'sha256',
            'shlex', 'split', 'startswith', 'values', 'whitespace_split',
            # round 3 (R3-3): T1 reads an apply_patch script's file headers
            'finditer', 'strip'},
    },
    # lane vendor-b24: OD57's read shapes, data only
    "box/od57_shapes.py": {"imports": {}, "from": set(), "rebinds": set(), "names": {"dict"}, "attrs": set()},
}
# The one subprocess call site of this lane's modules: (enclosing function, attribute).
SUBPROCESS_SITES = {"box/sidecar.py": [("inotifywait_factory", "Popen")]}
# The factory's Popen call shape (fold 3, W4C2-7): one positional argument, the name `argv`, and exactly these
# keywords, each with exactly this value ("PIPE" is subprocess.PIPE).
POPEN_ARG = "argv"
POPEN_KEYWORDS = {"stdout": "PIPE", "stderr": "PIPE", "shell": False, "close_fds": True}
# Builtins that reach a module or run code by name; refused anywhere, called or not.
REFUSED_BUILTINS = {"getattr", "setattr", "delattr", "vars", "globals", "locals", "__import__", "exec", "eval",
                    "compile", "__builtins__", "breakpoint"}


def _chain(node) -> tuple:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    return (node.id if isinstance(node, ast.Name) else None), ".".join(reversed(parts))


def process_problems(src: str, rel: str, spec: dict, sites: list) -> list:
    """Interface 10's default-deny over one module, by ast (see BOX_MODULES)."""
    tree = ast.parse(src)
    imports, froms = spec["imports"], spec["from"]
    out, aliases = [], {}
    parents, scope = {}, {}

    def walk(node, fn):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
            inner = child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
            scope[child] = fn
            walk(child, inner)
    walk(tree, None)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name not in imports:
                    out.append(f"{rel}: imports {a.name}, outside its allowlist")
                aliases[a.asname or a.name.split(".")[0]] = a.name
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                if node.level or (node.module, a.name) not in froms:
                    out.append(f"{rel}: from {node.module or '.'} import {a.name}, outside its allowlist")
    calls = []
    for name in sorted(shielded_bindings(tree) - spec["rebinds"]):
        out.append(f"{rel}: binds the builtin or dunder name {name}, outside its closed rebinds set")
    names = spec["names"]
    for name in sorted(free_names(tree)):
        if name not in names:
            out.append(f"{rel}: the free name {name}, outside its closed set")
    attrs = spec["attrs"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                out.append(f"{rel}: the dunder attribute {node.attr}")
            elif node.attr not in attrs:
                out.append(f"{rel}: the attribute {node.attr}, outside its vocabulary")
        if isinstance(node, ast.Name) and node.id in REFUSED_BUILTINS:
            out.append(f"{rel}: names the builtin {node.id}")
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg is None:
                    out.append(f"{rel}: a call with ** keywords")
                elif kw.arg == "shell" and not (isinstance(kw.value, ast.Constant) and kw.value.value is False):
                    out.append(f"{rel}: a call with shell= other than False")
        if isinstance(node, ast.Name) and node.id in aliases:
            top = node
            while isinstance(parents.get(top), ast.Attribute) and parents[top].value is top:
                top = parents[top]
            mod, chain = aliases[node.id], _chain(top)[1]
            if chain not in imports.get(mod, set()):
                out.append(f"{rel}: uses {mod}{'.' + chain if chain else ' itself'}, outside its allowlist")
                continue
            if mod == "subprocess":
                fn = scope.get(top)
                called = isinstance(parents.get(top), ast.Call) and parents[top].func is top
                if fn not in {f for f, _ in sites}:
                    out.append(f"{rel}: uses subprocess.{chain} outside the named call site")
                elif chain == "Popen" and not called:
                    out.append(f"{rel}: references subprocess.Popen without calling it")
                elif called:
                    calls.append((fn, chain))
                    if chain == "Popen":
                        out += popen_shape_problems(parents[top], aliases, rel)
    if sorted(calls) != sorted(sites):
        out.append(f"{rel}: subprocess calls {sorted(calls)}, expected exactly {sorted(sites)}")
    return out


BUILTIN_NAMES = frozenset(dir(builtins))


def _shielded(name: str) -> bool:
    """A builtin's name or a dunder bare name: binding one never exempts its reads (fold 5, W4C4-1)."""
    return name in BUILTIN_NAMES or name.startswith("__")


def bindings(tree) -> set:
    """Every name the module binds anywhere: Store or Del names, def and class names (methods directly in a class
    body excepted: they bind an attribute, not a bare name), parameters, import aliases and except-as names."""
    methods = {id(f) for c in ast.walk(tree) if isinstance(c, ast.ClassDef) for f in c.body
               if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
    bound = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load):
            bound.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and id(n) not in methods:
            bound.add(n.name)
        elif isinstance(n, ast.arg):
            bound.add(n.arg)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                bound.add(a.asname or a.name.split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
    return bound


def shielded_bindings(tree) -> set:
    """The builtin or dunder names the module binds; each must be in its closed `rebinds` set."""
    return {b for b in bindings(tree) if _shielded(b)}


def free_names(tree) -> set:
    """The free Load names of a module: every Name read that the module does not bind (fold 4, W4C3-1). A binding of
    a builtin's name or a dunder name never exempts a read (fold 5, W4C4-1): such a read stays free, so it must be
    pinned in the module's closed `names` set, and the binding itself must be in its closed `rebinds` set."""
    bound = {b for b in bindings(tree) if not _shielded(b)}
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} - bound


def _old_free_names(tree) -> set:   # kept only as the mutant below (the module-wide exemption of fold 4)
    bound = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load):
            bound.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(n.name)
        elif isinstance(n, ast.arg):
            bound.add(n.arg)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                bound.add(a.asname or a.name.split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} - bound


def popen_shape_problems(call, aliases, rel) -> list:
    """The factory's Popen call has exactly the pinned shape (POPEN_ARG, POPEN_KEYWORDS)."""
    out = []
    if len(call.args) != 1 or not (isinstance(call.args[0], ast.Name) and call.args[0].id == POPEN_ARG):
        out.append(f"{rel}: Popen's positional arguments are not exactly ({POPEN_ARG})")
    got = {}
    for kw in call.keywords:
        v = kw.value
        if isinstance(v, ast.Constant):
            got[kw.arg] = v.value
        elif isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and aliases.get(v.value.id) == \
                "subprocess":
            got[kw.arg] = v.attr
        else:
            got[kw.arg] = None
    if set(got) != set(POPEN_KEYWORDS) or any(got[k] != POPEN_KEYWORDS[k] or type(got[k]) is not
                                              type(POPEN_KEYWORDS[k]) for k in POPEN_KEYWORDS):
        out.append(f"{rel}: Popen's keywords are not exactly the pinned shape")
    return out


def _append(form):
    return lambda src: src + "\n" + form


# Every form a review found hollow, and the earlier planted positives; each, applied to the real box/sidecar.py,
# must be refused under that module's own allowlist and sites.
PLANTED = {
    "an alias rebound (x = os)": _append("x = os\n\ndef _p():\n    x.kill(1, 9)\n"),
    "getattr(os, 'kill')": _append("def _p():\n    getattr(os, 'kill')(1, 9)\n"),
    "vars(os)['system']": _append("def _p():\n    vars(os)['system']('x')\n"),
    "os.__dict__['kill']": _append("def _p():\n    os.__dict__['kill'](1, 9)\n"),
    "socket.os.kill": _append("def _p():\n    socket.os.kill(1, 9)\n"),
    "os.popen": _append("def _p():\n    os.popen('x')\n"),
    "__import__('subprocess')": _append("def _p():\n    __import__('subprocess').run(['x'])\n"),
    "r = subprocess.run; r()": _append("def _p():\n    r = subprocess.run\n    r(['x'])\n"),
    "exec('import subprocess')": _append("def _p():\n    exec('import subprocess')\n"),
    "signal.pidfd_send_signal": _append("def _p():\n    signal.pidfd_send_signal(3, 9)\n"),
    "**{'shell': True} in the factory": lambda src: src.replace("close_fds=True)",
                                                                "close_fds=True, **{'shell': True})", 1),
    "shell=True in the factory": lambda src: src.replace("shell=False, close_fds=True)",
                                                         "shell=True, close_fds=True)", 1),
    "Popen referenced, not called, in the factory": lambda src: src.replace(
        "    proc = subprocess.Popen(", "    p_ = subprocess.Popen\n    proc = subprocess.Popen(", 1),
    "subprocess elsewhere": _append("def helper():\n    subprocess.run(['x'])\n"),
    "os.posix_spawn": _append("def _p():\n    os.posix_spawn('/bin/x', ['x'], {})\n"),
    "import os as o; o.kill": _append("import os as o\n\ndef _p():\n    o.kill(1, 9)\n"),
    "from os import system": _append("from os import system\n"),
    "os.fork": _append("os.fork()\n"),
    "import pty": _append("import pty\npty.spawn(['x'])\n"),
    "import ctypes": _append("import ctypes\n"),
    "argparse._os": _append("def _p():\n    argparse._os.kill(1, 9)\n"),
    "os.path.os": _append("def _p():\n    os.path.os.kill(1, 9)\n"),
    "sys.modules['os']": _append("def _p():\n    sys.modules['os'].kill(1, 9)\n"),
    "globals()['os']": _append("def _p():\n    globals()['os'].kill(1, 9)\n"),
    "eval": _append("def _p():\n    eval('1')\n"),
    "compile": _append("def _p():\n    compile('1', 'f', 'eval')\n"),
    "__builtins__": _append("def _p():\n    __builtins__['exec']('1')\n"),
}


def _source(rel: str) -> str:
    with open(os.path.join(STUDY, rel), encoding="utf-8") as fh:
        return fh.read()


def planted_problems(name: str) -> list:
    rel = "box/sidecar.py"
    src = _source(rel)
    planted = PLANTED[name](src)
    if planted == src:
        return ["NOT PLANTED (the form's anchor is gone)"]
    return process_problems(planted, f"planted:{name}", BOX_MODULES[rel], SUBPROCESS_SITES[rel])


def process_check() -> int:
    """The checks file's entry point: planted positives first (each must be refused), then this lane's modules."""
    bad = 0
    for name in PLANTED:
        got = planted_problems(name)
        ok = bool(got) and got != ["NOT PLANTED (the form's anchor is gone)"]
        print(f"planted {name}: {'refused' if ok else 'NOT REFUSED'}")
        bad += not ok
    for rel, spec in BOX_MODULES.items():
        got = process_problems(_source(rel), rel, spec, SUBPROCESS_SITES.get(rel, []))
        print(f"{rel}: {'ok' if not got else '; '.join(got)}")
        bad += bool(got)
    print(f"process check: {'ok' if not bad else f'{bad} problem(s)'}")
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------- S7 (lane w6g)
class TestS7Sidecar(TakeCase):
    """glitch-1b's rulings S7-D1 (a special STATE by kind), S7-D2 (mode bits a named residual) and S7-D3 (begin writes
    watched.json), under ownership transfer S7-gap4-1. Each assertion carries its clause token, bound by
    tests/test_endstate.py's whole-file witnesses."""

    def test_special_files_are_recorded_by_kind(self):
        import socket
        t = self.take()
        os.mkfifo(os.path.join(t.run_tree, "pipe"))
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(s.close)
        try:
            s.bind(os.path.join(t.run_tree, "s.sock"))
        except OSError as e:   # a socket path too long for this host: the kinds below still bind by mode
            self.skipTest(f"no unix socket here: {e}")
        entries, special, _ = sidecar.snapshot_tree(t.run_tree, t.watch)
        self.assertEqual((entries["pipe"], entries["s.sock"]),
                         ({"type": "special", "kind": "fifo"}, {"type": "special", "kind": "socket"}), "S7-D1.sidecar")
        self.assertEqual(special, ["pipe", "s.sock"], "S7-D1.sidecar")
        modes = {stat.S_IFCHR | 0o600: "char", stat.S_IFBLK | 0o600: "block", stat.S_IFIFO: "fifo",
                 stat.S_IFSOCK: "socket", 0o160000: "special"}
        self.assertEqual({m: sidecar._kind(m) for m in modes}, modes, "S7-D1.sidecar")
        # what the sidecar writes, endstate reads: a lasting FIFO and socket are no change across the take
        t.write_ledger()
        r = t.sc.handle("begin")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["unreadable"], [], "S7-D1.sidecar")
        t.turn([])
        self.assertTrue(t.sc.handle("snapshot", "post-1")["ok"])
        t.clock.tick(1.0)
        self.assertTrue(t.sc.handle("finish")["ok"])
        e = t.load()
        self.assertEqual((e.agent_changes(1), e.kind("post-1", "pipe"), e.sidecar_record()), ({}, "special", CLEAN),
                         "S7-D1.sidecar")

    def test_begin_writes_the_watched_list(self):
        watch = ("z/b.json", "plan/approved.json", "plan/approved.json")
        t = self.take(watch=watch)
        r = t.sc.handle("begin")
        self.assertTrue(r["ok"], r)
        path = os.path.join(t.evidence, "watched.json")
        self.assertTrue(os.path.isfile(path), "S7-D3.begin - begin wrote no watched.json")
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"paths": ["plan/approved.json", "z/b.json"]}, "S7-D3.begin")
        t.turn([("plan/approved.json", ("OPEN",))])
        self.assertTrue(t.sc.handle("snapshot", "post-1")["ok"])
        t.clock.tick(1.0)
        self.assertTrue(t.sc.handle("finish")["ok"])
        e = t.load()
        self.assertEqual(e.watched(), ("plan/approved.json", "z/b.json"), "S7-D3.begin")
        self.assertEqual(e.accesses(path="z/b.json"), [], "S7-D3.begin")   # watched, nothing seen
        self.assertEqual(temps_in(t.evidence), [], "S7-D3.begin")

    def test_a_special_consequential_path_fails_begin(self):
        # S7-gap4-3 (glitch-1b's W6G-R1-2 fold): before the first turn a consequential path that is a special file is
        # a preflight problem, as it was while special files were recorded unreadable; nothing after begin changes.
        t = self.take(watch=(PLAN, "data/pipe"))
        os.makedirs(os.path.join(t.run_tree, "data"), exist_ok=True)
        os.mkfifo(os.path.join(t.run_tree, "data", "pipe"))
        os.mkfifo(os.path.join(t.run_tree, "side.fifo"))   # a special file at a path no one watches: no problem
        r = t.sc.handle("begin")
        self.assertEqual(sidecar.parse_reply(json.dumps(r) + "\n"), r, "S7-D1.begin")
        self.assertFalse(r["ok"], "S7-D1.begin - a special consequential path passed begin")
        self.assertEqual(len(r["problems"]), 1, "S7-D1.begin")
        self.assertIn("data/pipe", r["problems"][0], "S7-D1.begin")
        self.assertNotIn("side.fifo", r["problems"][0], "S7-D1.begin")
        self.assertEqual((r["unreadable"], r["unreadable_consequential"]), ([], []), "S7-D1.begin")
        # the take itself is not broken: the watcher runs, and a special consequential path made later is graded
        t.turn([])
        r1 = t.sc.handle("snapshot", "post-1")
        self.assertTrue(r1["ok"], r1)
        clean = self.take(watch=(PLAN, "data/pipe"))
        r0 = clean.sc.handle("begin")
        self.assertTrue(r0["ok"], r0)
        clean.turn([])
        os.makedirs(os.path.join(clean.run_tree, "data"), exist_ok=True)
        os.mkfifo(os.path.join(clean.run_tree, "data", "pipe"))
        r2 = clean.sc.handle("snapshot", "post-1")
        self.assertTrue(r2["ok"] and r2["problems"] == [], "S7-D1.begin - a special file after begin is a problem")

    def test_a_chmod_alone_is_invisible(self):
        # S7-D2 (ruled C): the named, pre-registered residual. A chmod that leaves the file readable changes no STATE.
        doc = " ".join((es.__doc__ or "").split())
        self.assertIn("Mode bits (S7-D2, ruled C).", doc, "S7-D2.residual")
        t = self.take()
        p = os.path.join(t.run_tree, "design.tsv")
        os.chmod(p, 0o600)
        before, _, _ = sidecar.snapshot_tree(t.run_tree, t.watch)
        os.chmod(p, 0o755)
        after, _, _ = sidecar.snapshot_tree(t.run_tree, t.watch)
        self.assertEqual(before, after, "S7-D2.residual")
        self.assertFalse([st for st in after.values() if "mode" in st], "S7-D2.residual")

    def test_the_final_stop_at_post_n_reads_as_a_gap(self):
        # S7-D4 (ruled A), through the real sidecar: finish at post-1's own instant leaves no interval past it.
        t = self.take()
        self.assertTrue(t.sc.handle("begin")["ok"])
        t.turn([])
        self.assertTrue(t.sc.handle("snapshot", "post-1")["ok"])
        self.assertTrue(t.sc.handle("finish")["ok"])       # no dwell: the final stop is stamped at post-1's instant
        e = t.load()
        self.assertEqual(e.sidecar_record(), dict(CLEAN, stop_record=False), "S7-D4.sidecar")


class TestProcessCheck(unittest.TestCase):
    def test_every_planted_form_is_refused(self):
        for name in PLANTED:
            with self.subTest(name):
                got = planted_problems(name)
                self.assertTrue(got)
                self.assertNotEqual(got, ["NOT PLANTED (the form's anchor is gone)"])

    def test_both_modules_pass(self):
        for rel, spec in BOX_MODULES.items():
            with self.subTest(rel):
                self.assertEqual(process_problems(_source(rel), rel, spec, SUBPROCESS_SITES.get(rel, [])), [])

    def test_mutants_go_red(self):
        rel, spec = "box/sidecar.py", BOX_MODULES["box/sidecar.py"]
        src = _source(rel)
        moved = src.replace("def inotifywait_factory(", "def _helper_factory(")
        self.assertNotEqual(process_problems(moved, rel, spec, SUBPROCESS_SITES[rel]), [])
        red("the Popen call moved out of the named factory")
        extra = src + "\ndef again():\n    subprocess.run(['x'])\n"
        self.assertNotEqual(process_problems(extra, rel, spec, SUBPROCESS_SITES[rel]), [])
        red("a second subprocess call site")
        sr_rel = "box/scan_record.py"
        sr_spec = BOX_MODULES[sr_rel]
        self.assertNotEqual(process_problems("import subprocess\n" + _source(sr_rel), sr_rel, sr_spec, []), [])
        red("scan_record importing subprocess")
        # the check itself, made a deny-list again (aliases unchecked), lets the hollow forms through
        with mock.patch.dict(BOX_MODULES["box/sidecar.py"]["imports"],
                             {"os": spec["imports"]["os"] | {"", "__dict__", "popen"},
                              "socket": spec["imports"]["socket"] | {"os.kill"}}), \
                mock.patch.dict(BOX_MODULES["box/sidecar.py"], {"attrs": spec["attrs"] | {"popen"}}):
            self.assertEqual(process_problems(PLANTED["os.popen"](src), rel, BOX_MODULES[rel],
                                              SUBPROCESS_SITES[rel]), [])
        red("an attribute allowlist widened (os.popen through)")
        with mock.patch.object(sys.modules[__name__], "REFUSED_BUILTINS", set()):
            wide = dict(spec, names=spec["names"] | {"eval"})   # the free-name layer widened too (fold 4)
            self.assertEqual(process_problems(PLANTED["eval"](src), rel, wide, SUBPROCESS_SITES[rel]), [])
        red("the refused builtins dropped (eval through)")


if __name__ == "__main__":
    if sys.argv[1:] == ["--process-check"]:
        sys.exit(process_check())
    unittest.main(verbosity=2)
