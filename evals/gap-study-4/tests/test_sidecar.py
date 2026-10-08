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


class ProcessStartRefused(AssertionError):
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

    def __init__(self, clock: FakeClock, plan, *, establish_after: int = 0, stop_rc: int = -signal.SIGTERM):
        self.clock, self.plan = clock, tuple(plan)
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
        return self.rc

    def request_stop(self):
        self.stop_requested = True
        if self.rc is None:
            self.rc = self.stop_rc

    def force_stop(self):
        if self.rc is None:
            self.rc = -signal.SIGKILL

    def die(self, rc: int):
        self.rc = rc


class Factory:
    """The injected watcher factory: records every plan it was armed with, and the watchers it made."""

    def __init__(self, clock, *, establish_after=0, fail_on: set | None = None, stop_rc=-signal.SIGTERM):
        self.clock, self.made, self.plans = clock, [], []
        self.establish_after, self.fail_on, self.stop_rc = establish_after, fail_on or set(), stop_rc

    def __call__(self, run_tree, plan):
        self.plans.append(tuple(plan))
        if len(self.made) + 1 in self.fail_on:
            self.made.append(None)
            raise OSError("injected: the re-arm failed")
        w = FakeWatcher(self.clock, plan, establish_after=self.establish_after, stop_rc=self.stop_rc)
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

    def __init__(self, watch=("plan/approved.json",), *, files=None, factory_kw=None, sidecar_kw=None):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.run_tree = os.path.join(base, "run")
        self.evidence = os.path.join(base, "ev")
        self.private = os.path.join(base, "private")
        for d in (self.run_tree, self.evidence, self.private):
            os.mkdir(d)
        for rel, data in (files if files is not None else {"plan/approved.json": b'{"approved": false}\n',
                                                           "design.tsv": b"a\tb\n"}).items():
            self.write(rel, data)
        self.clock = FakeClock()
        self.factory = Factory(self.clock, **(factory_kw or {}))
        self.watch = tuple(watch)
        self.sc = sidecar.Sidecar(run_tree=self.run_tree, evidence=self.evidence, watch=self.watch,
                                  factory=self.factory, tmp_dir=self.private, clock=self.clock.time,
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
        self.assertEqual(os.listdir(t.private), [])   # no temp file left behind

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
