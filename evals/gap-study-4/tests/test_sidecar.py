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
                                                          "snapshots"])
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
        self.assertEqual(h[1], {"kind": "watcher-stop", "at": r["taken_at"], "exit_code": 0})
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
        self.assertEqual(r["unreadable"], sorted(["data/pipe", LOCKED]))
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
        self.assertEqual(post["data/pipe"], {"type": "unreadable"})
        self.assertEqual(post[LOCKED], {"type": "unreadable"})
        self.assertEqual(post["data/real/one.txt"]["type"], "file")
        self.assertEqual([a["op"] for a in ev.accesses(path=PLAN, turn=1)], ["open"])
        self.assertEqual([a["op"] for a in ev.accesses(path=PLAN, turn=2)], ["open", "modify", "modify"])
        self.assertEqual(ev.accesses(path="design.tsv"), [])           # not a consequential path
        self.assertEqual(ev.content("post-2", PLAN), b'{"approved": true}\n')
        self.assertEqual(ev.agent_changes(2)[PLAN].kind, "modified")
        # The named effect of persistently unreadable paths (W2A fold 1 question 3, W2A2-3): the FIFO and the
        # chmod-000 file read as unknown changes across the operator step, so the operator re-check counts them.
        unexplained = ev.operator_matches(1)["unexplained"]
        self.assertEqual(unexplained, sorted(["data/pipe", LOCKED]))
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
        self.assertEqual(entries["pipe"], {"type": "unreadable"})
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
        self.assertEqual(h[-1], {"kind": "watcher-stop", "at": died, "exit_code": 1})   # stamped at detection
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
        t.sc.handle("finish")
        self.assertEqual([a["op"] for a in t.load().accesses(path=PLAN, turn=1)], ["delete", "modify"])

    def test_an_rm_rf_of_a_chain_folder_logs_per_path_events_and_no_fault(self):
        t = self.take()
        t.sc.handle("begin")
        t.turn([(PLAN, ("DELETE",)), ("plan", ("DELETE_SELF",)), ("plan", ("DELETE", "ISDIR"))])
        r = t.sc.handle("snapshot", "post-1")
        self.assertTrue(r["ok"], r)
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
                self._health(sidecar.WATCHER_STOP, self.clock(), exit_code=0)
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
    for want in [("--network", "none"), ("--user", "10002:10002"), ("--cap-drop", "ALL"),
                 ("--cap-add", "DAC_READ_SEARCH"), ("--security-opt", "no-new-privileges")]:
        if want not in pairs:
            p.append(f"missing {want}")
    if "--pull=never" not in flags:
        p.append("missing --pull=never")
    if [f for f in flags if f == "--cap-add"] != ["--cap-add"]:
        p.append("not exactly one added capability")
    mounts = [b for a, b in pairs if a == "--mount"]
    if sorted(mounts) != sorted([f"type=bind,source={RUN_TREE},target={RUN_TREE},readonly",
                                 f"type=bind,source={EVIDENCE},target=/srv/ev"]):
        p.append(f"mounts {mounts}")
    for bad in ("--pid", "--ipc", "--volumes-from", "-p", "--publish", "--privileged", "--device", "-e", "--env",
                "--env-file", "-v", "--volume"):
        if any(f == bad or f.startswith(bad + "=") for f in flags):
            p.append(f"forbidden {bad}")
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
            "root user": [("0:0" if x == "10002:10002" else x) for x in base],
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
            "user": "10002:10002", "network_mode": "none", "cap_drop": ["ALL"], "cap_add": ["PENDING"],
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
                         ["docker", "exec", CID, "python3", "-I", "-B", "/opt/w/sidecar.py", "ctl", "begin"])
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
        self.assertEqual((sidecar.LEDGER, sidecar.ACCESS, sidecar.HEALTH), es.FILES)
        self.assertEqual((sidecar.SNAPSHOTS, sidecar.BLOBS), es.FOLDERS)
        self.assertEqual((sidecar.WATCHER_START, sidecar.WATCHER_STOP, sidecar.QUEUE_OVERFLOW),
                         (es.WATCHER_START, es.WATCHER_STOP, es.QUEUE_OVERFLOW))
        self.assertEqual((sidecar.OPEN, sidecar.MODIFY, sidecar.DELETE), es.ACCESS_OPS)
        self.assertEqual(sidecar.UNREADABLE, {"type": es.UNREADABLE})


# ------------------------------------------------------------------------------------------------- PENDING values
EXPECTED_PENDING = {"inotifywait_argv", "inotifywait_format", "inotifywait_subsecond", "inotifywait_events",
                    "inotify_watch_count", "watch_establish_s"}


class TestPending(unittest.TestCase):
    def test_the_pending_set(self):
        self.assertEqual(set(sidecar.pending()), EXPECTED_PENDING)
        for f in EXPECTED_PENDING:
            self.assertEqual(getattr(sidecar, f.upper()), "PENDING")

    def test_the_real_factory_refuses_while_pending(self):
        with self.assertRaises(sidecar.NotReady):
            sidecar.inotifywait_factory("/srv/takes/t1/run", (("", False),))
        for f in EXPECTED_PENDING:   # each one alone still refuses
            others = {x.upper(): ["filled-in-memory"] for x in EXPECTED_PENDING - {f}}
            with mock.patch.multiple(sidecar, **others):
                self.assertEqual(set(sidecar.pending()), {f})
                with self.assertRaises(sidecar.NotReady):
                    sidecar.inotifywait_factory("/srv/takes/t1/run", (("", False),))

    def test_mutant_dropping_the_refusal_goes_red(self):
        with mock.patch.object(sidecar, "require_ready", lambda: None):
            with self.assertRaises(ProcessStartRefused):   # it reached the (guarded) process start, not NotReady
                sidecar.inotifywait_factory("/srv/takes/t1/run", (("", False),))
        red("the real factory without its PENDING refusal")

    def test_serve_refuses_while_pending(self):
        with self.assertRaises(sidecar.NotReady):
            sidecar.main(["serve", "--run-tree", "/srv/takes/t1/run", "--evidence", "/srv/ev", "--watch", PLAN])

    def test_no_parameter_overrides_a_pending_value(self):
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

    def __init__(self, out: bytes, err: bytes):
        self.fds = []
        self.stdout, self.stderr = self._pipe(out), self._pipe(err)

    def _pipe(self, data):
        r, w = os.pipe()
        os.write(w, data)
        os.close(w)
        self.fds.append(r)
        return type("F", (), {"fileno": lambda self_, fd=r: fd})()

    def close(self):
        for fd in self.fds:
            os.close(fd)


FORMAT = {"fields": ["at", "path", "events"], "separator": "\t", "established": "Watches established."}


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


# ------------------------------------------------------------------------------------------------- interface 10's ast check
# The lane's non-test box modules, each with its closed standard-library import allowlist (scan_record also imports
# the round's own scrub.py, for scrub.NOTE). Test files are out of this check's scope.
BOX_MODULES = {
    "box/sidecar.py": {"__future__", "argparse", "dataclasses", "errno", "hashlib", "json", "os", "re", "selectors",
                       "signal", "socket", "stat", "subprocess", "sys", "time"},
    "box/scan_record.py": {"__future__", "dataclasses", "hashlib", "json", "os", "re", "stat", "sys", "scrub"},
}
# The one subprocess call site of this lane's modules: (module, enclosing function, attribute).
SUBPROCESS_SITES = {"box/sidecar.py": [("inotifywait_factory", "Popen")]}
_FORBIDDEN_OS = ("kill", "killpg", "system", "fork", "forkpty")
_FORBIDDEN_OS_PREFIX = ("exec", "spawn", "posix_spawn")


def process_problems(src: str, rel: str, allowed: set, sites: list) -> list:
    """Interface 10's default-deny over one module, by ast: its imports are within `allowed`; every reference to
    os.kill, os.killpg, os.system, os.exec*, os.spawn*, os.posix_spawn*, os.fork*, pty.spawn or
    asyncio.create_subprocess_* is refused; no call passes shell=True; subprocess is imported only where `sites`
    names a call, and its only calls are exactly `sites` (function, attribute)."""
    tree = ast.parse(src)
    out, aliases, calls = [], {}, []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = a.name.split(".")[0]
                aliases[a.asname or top] = a.name if a.asname else top
                if top not in allowed:
                    out.append(f"{rel}: imports {a.name}, outside its allowlist")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level or mod.split(".")[0] not in allowed:
                out.append(f"{rel}: imports from {mod or '.'}, outside its allowlist")
            if mod in ("os", "subprocess", "pty", "asyncio") or mod.startswith(("os.", "subprocess.", "asyncio.")):
                out.append(f"{rel}: from {mod} import {', '.join(a.name for a in node.names)} (name the module)")
    if "subprocess" in aliases.values() and not sites:
        out.append(f"{rel}: imports subprocess")

    def scopes(node, fn=None):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from scopes(child, child.name)
            else:
                yield child, fn
                yield from scopes(child, fn)

    for node, fn in scopes(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            mod, attr = aliases.get(node.value.id), node.attr
            if mod == "os" and (attr in _FORBIDDEN_OS or attr.startswith(_FORBIDDEN_OS_PREFIX)):
                out.append(f"{rel}: names os.{attr}")
            if mod == "pty" and attr == "spawn":
                out.append(f"{rel}: names pty.spawn")
            if mod == "asyncio" and attr.startswith("create_subprocess"):
                out.append(f"{rel}: names asyncio.{attr}")
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "shell" and not (isinstance(kw.value, ast.Constant) and kw.value.value is False):
                    out.append(f"{rel}: a call with shell= other than False")
            f = node.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and aliases.get(f.value.id) == \
                    "subprocess":
                calls.append((fn, f.attr))
    if sorted(calls) != sorted(sites):
        out.append(f"{rel}: subprocess calls {sorted(calls)}, expected exactly {sorted(sites)}")
    return out


PLANTED = {
    "posix_spawn": "import os\ndef f():\n    os.posix_spawn('/bin/x', ['x'], {})\n",
    "aliased kill": "import os as o\ndef f():\n    o.kill(1, 9)\n",
    "from os import": "from os import system\n",
    "subprocess elsewhere": "import subprocess\ndef helper():\n    subprocess.run(['x'])\n",
    "shell true": "import subprocess\ndef inotifywait_factory():\n    subprocess.Popen('x', shell=True)\n",
    "outside allowlist": "import ctypes\n",
    "fork": "import os\nos.fork()\n",
    "pty": "import pty\npty.spawn(['x'])\n",
}


def process_check() -> int:
    """The checks file's entry point: planted positives first (each must be refused), then this lane's modules."""
    bad = 0
    for name, src in PLANTED.items():
        sites = [("inotifywait_factory", "Popen")] if name == "shell true" else []
        got = process_problems(src, f"planted:{name}", {"os", "subprocess", "pty"}, sites)
        print(f"planted {name}: {'refused' if got else 'NOT REFUSED'}")
        bad += not got
    for rel, allowed in BOX_MODULES.items():
        with open(os.path.join(STUDY, rel), encoding="utf-8") as fh:
            got = process_problems(fh.read(), rel, allowed, SUBPROCESS_SITES.get(rel, []))
        print(f"{rel}: {'ok' if not got else '; '.join(got)}")
        bad += bool(got)
    print(f"process check: {'ok' if not bad else f'{bad} problem(s)'}")
    return 1 if bad else 0


class TestProcessCheck(unittest.TestCase):
    def test_the_planted_positives_are_refused(self):
        self.assertEqual(process_problems(PLANTED["posix_spawn"], "m", {"os"}, []), ["m: names os.posix_spawn"])
        for name, src in PLANTED.items():
            sites = [("inotifywait_factory", "Popen")] if name == "shell true" else []
            allowed = {"os", "subprocess", "pty"}
            with self.subTest(name):
                self.assertNotEqual(process_problems(src, "m", allowed, sites), [])

    def test_the_sidecar_passes(self):
        with open(SIDECAR_SOURCE, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(process_problems(src, "box/sidecar.py", BOX_MODULES["box/sidecar.py"],
                                          SUBPROCESS_SITES["box/sidecar.py"]), [])
        moved = src.replace("def inotifywait_factory(", "def _helper_factory(")
        self.assertNotEqual(process_problems(moved, "box/sidecar.py", BOX_MODULES["box/sidecar.py"],
                                             SUBPROCESS_SITES["box/sidecar.py"]), [])
        red("the Popen call moved out of the named factory")
        extra = src + "\ndef again():\n    subprocess.run(['x'])\n"
        self.assertNotEqual(process_problems(extra, "box/sidecar.py", BOX_MODULES["box/sidecar.py"],
                                             SUBPROCESS_SITES["box/sidecar.py"]), [])
        red("a second subprocess call site")

    def test_scan_record_passes_and_may_not_import_subprocess(self):
        path = os.path.join(STUDY, "box", "scan_record.py")
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        allowed = BOX_MODULES["box/scan_record.py"]
        self.assertEqual(process_problems(src, "box/scan_record.py", allowed, []), [])
        self.assertNotEqual(process_problems("import subprocess\n" + src, "box/scan_record.py",
                                             allowed | {"subprocess"}, []), [])
        red("scan_record importing subprocess")


if __name__ == "__main__":
    if sys.argv[1:] == ["--process-check"]:
        sys.exit(process_check())
    unittest.main(verbosity=2)
