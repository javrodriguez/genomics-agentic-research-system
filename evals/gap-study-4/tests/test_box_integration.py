#!/usr/bin/env python3
"""Lane w6h (Gap Study round 4, slice S6): the CP2 drive lifecycle, part 2, end to end on a FAKE runtime.

The plan's test_box_integration.py has two halves. This module is the fake-runtime half: drive.py's TakeDriver and
TakeRepo inside a real batch.Batch, over a stateful fake container runtime (FakeBox) that answers run_take's argv
lists the way the box would, on scratch git repositories. The real-box half (one stub take on athena's box, with no
model) is CP2's real-box step and is NOT here: `RealBoxHalf` names it, and its one method raises SkipTest with that
reason (see the named question in lane-reports/w6h-drive-lifecycle.md: the battery allows no skip yet).

What is tested, each guard with its own bound check and a whole-file witness of drive.py:

  B1-rollback    a refused commit puts the outcome ledger back to HEAD's bytes and unstages what it staged (ruling
                 S6-Q2); the next take then registers and commits. Witness: the restore call removed.
  B2-preflight   drive() reaches preflight only through S1's entry point (preflight_take -> collect_and_evaluate),
                 once, before any turn, with the Launched record launch returned (its spec), the sidecar's own
                 launch record, the take's evidence folder and the sidecar's parsed begin reply; the record is
                 written beside the evidence. Witness: preflight skipped (read as passed).
  B3-preturn     a failed preflight, or a typed refusal inside it, runs no turn, is written to refusal.json (the
                 refusal) and routes as a rehearsal. Witness: a failed record read as passed.
  B4-scan        scan -> mask -> route -> commit (ruling S6-Q3): a planted fake value in a turn's stream is masked on
                 disk before drive() returns, counted in events.outside_reach with the checker's events, annotated
                 (mask, event) and committed masked. Witness: the drive step's scan replaced by a clean result.
  B5-cleanup     on every road (a passed take, a failed preflight, a typed refusal, an adapter that raises
                 mid-take, a timed-out turn, a scan refusal), the agent's processes are killed by an exec as the
                 agent's uid and none is left, and every container and the network are removed by their recorded
                 ids. Witness: the finally path's cleanup removed.
  B6-quiesce     a background process that outlives its turn is polled up to the quiescence cap, then killed as the
                 agent's uid and polled to none, and only then is the turn's snapshot signalled; the survivors are
                 counted and quiescence_kill is set; a timed-out turn's processes are killed at once. Witness: the
                 cap kill removed.
  B7-remove      remove(id) removes the take container by its recorded id only while the full listing holds it, and
                 raises if it is still listed after (batch's A LEAK); a launch whose partial teardown left the take
                 container carries its id. Witness: remove() never removes.
  B8-config      the per-take config folder outlives the drive and is deleted once the commit has landed
                 (TakeRepo.on_published), never after a refused commit. Witness: the on_published call removed.

Fakes and synthetic strings only: no model, vendor, network, container runtime, credential or holdout. Every
process start except `git -C <scratch>` trips the guard armed in setUpModule, which also patches prereg's readers
(this base has no pre-registration; drive.py reads one at import) and the PENDING runtime spellings run_take needs
(INSPECT_STATUS, TOP_FORMAT), and only then imports drive.py. Preflight's own checks are S1's (tests/test_preflight.py);
here collect_and_evaluate is a spy that returns a closed preflight record.

Witnesses follow the registry pattern of the earlier gap4 lanes: drive.py with one exact anchor edit, compiled in
memory as its own module (never written to disk). A kill counts only when the bound check is green on the real
module first and then returns at least one line with its own prefix and no ERROR line.
"""

from __future__ import annotations

import contextlib
import copy
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import agent_adapter as aa  # noqa: E402
import batch  # noqa: E402
import harness_bookkeeping as hb  # noqa: E402
import prereg  # noqa: E402
import routing  # noqa: E402
import variants  # noqa: E402
from box import preflight as pf  # noqa: E402
from box import run_take as rt  # noqa: E402
from box import sidecar as sc  # noqa: E402
from graders import labels4  # noqa: E402

drive = None            # imported in setUpModule, after the guard and the patches
SCRATCH: Path | None = None
_STACK = contextlib.ExitStack()

TOKEN = "synthetic-login-value-" + "fedcba9876543210"      # a planted fake, never a real login
IMAGE = "sha256:" + "f" * 64
PLACEHOLDER_NET = "e" * 64
MODEL = "synthetic-model"
PROFILE = {"permission_mode": "bypassPermissions", "version": "0.0.1"}
TOP = {"ps_options": ["-eo", "pid,uid,comm"], "pid_column": "PID", "uid_column": "UID"}
UID_MAP = [(0, 1000, 1), (1, 100000, 65536)]
AGENT_HOST_UID = 100000 + 10001 - 1
CAP_S, POLL_S = 30, 5
REAL_BOX_STEP = ("CP2's real-box step: one stub take on athena's box with no model (plan, CREATE "
                 "tests/test_box_integration.py), which waits on J1, 'athena box setup done'")


# ------------------------------------------------------------------------------------------------ the process guard
class GuardTripped(Exception):
    """A process start this module never allows."""


_REAL = {"run": subprocess.run, "Popen": subprocess.Popen}


def _allowed(args) -> bool:
    argv = list(args) if isinstance(args, (list, tuple)) else None
    if not argv or len(argv) < 4 or argv[0] != "git" or argv[1] != "-C" or SCRATCH is None:
        return False
    try:
        return Path(str(argv[2])).resolve().is_relative_to(SCRATCH)
    except (OSError, ValueError):
        return False


def _gate(name):
    real = _REAL[name]

    def gate(args, *a, **kw):
        if _allowed(args):
            return real(args, *a, **kw)
        raise GuardTripped(f"process guard: subprocess.{name} refused {args!r}"[:200])
    return gate


def _trip(name):
    def trip(*a, **kw):
        raise GuardTripped(f"process guard: {name} refused")
    return trip


def table() -> dict:
    t = copy.deepcopy(routing.load_table())
    t["pin_profiles"] = {hb.CLAUDE_CODE: {MODEL: dict(PROFILE)}}
    t["pin_profiles_status"] = "RULED (TEST-ONLY): one injected profile"
    t["spend_cap_markers_status"] = "RULED (TEST-ONLY): the spend-cap list opened for the tests"
    return t


def row(n=1, **kw):
    cell = variants.task_cells({"factor": None}, {"wordings": [{"id": "w1"}, {"id": "w2"}]})
    r = {"arm": "A", "task": "synthetic-task", "model": MODEL,
         "agent": {"harness": hb.CLAUDE_CODE, "version": PROFILE["version"]}, **cell[(n - 1) % len(cell)],
         "slot": f"s{n}", "half_cell": "c1"}
    r.update(kw)
    return r


def setUpModule():
    global drive, SCRATCH
    SCRATCH = Path(_STACK.enter_context(tempfile.TemporaryDirectory(prefix="w6h-"))).resolve()
    home = SCRATCH / "home"
    home.mkdir()
    keep = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "TMPDIR") if k in os.environ}
    keep.update(HOME=str(home), XDG_CONFIG_HOME=str(home), GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    _STACK.enter_context(mock.patch.dict(os.environ, keep, clear=True))
    for name in ("run", "Popen"):
        _STACK.enter_context(mock.patch.object(subprocess, name, _gate(name)))
    for name in ("call", "check_call", "check_output", "getoutput", "getstatusoutput"):
        _STACK.enter_context(mock.patch.object(subprocess, name, _trip(f"subprocess.{name}")))
    for name in ("system", "popen", "kill", "killpg", "posix_spawn", "posix_spawnp", "fork", "forkpty"):
        if hasattr(os, name):
            _STACK.enter_context(mock.patch.object(os, name, _trip(f"os.{name}")))
    _STACK.enter_context(mock.patch.object(prereg, "load", lambda: {"driver_constants": {}}))
    _STACK.enter_context(mock.patch.object(prereg, "require_frozen", lambda what: {"rows": [row(n) for n in
                                                                                           range(1, 7)]}))
    # The runtime spellings only the real box can tell (run_take's PENDING values), filled for the fake runtime only.
    _STACK.enter_context(mock.patch.object(rt, "INSPECT_STATUS", "confirmed-in-test"))
    _STACK.enter_context(mock.patch.object(rt, "TOP_FORMAT", TOP))
    import drive as imported
    drive = imported


def tearDownModule():
    _STACK.close()


# ------------------------------------------------------------------------------------------------ the fake box
def ok(stdout="", stderr=""):
    return rt.Completed(0, stdout, stderr)


def reply(command, label=None, *, ok_=True, unreadable_consequential=()):
    r = {"ok": ok_, "command": command, "label": label, "taken_at": 1.0 if command in ("begin", "snapshot") else None,
         "rearmed_at": 2.0 if command in ("begin", "snapshot") else None,
         "unreadable": list(unreadable_consequential), "unreadable_consequential": list(unreadable_consequential),
         "problems": [] if ok_ else ["synthetic problem"]}
    return json.dumps({k: r[k] for k in sc.REPLY_FIELDS}) + "\n"


class FakeBox:
    """A container runtime that answers run_take's argv lists from its own state: networks, containers, the agent's
    processes in each take container, and the sidecar's health records written into the evidence folder.

    fail_rm      kinds ("take", "sidecar", "proxy") whose `rm --force` fails, `times` times each
    stubborn     the agent's processes survive the kill (a process the uid kill cannot reach)
    begin        "ok" | "refused" | "malformed": the sidecar's begin reply
    """

    def __init__(self, *, fail_rm=(), fail_times=1, stubborn=False, begin="ok", unreadable=()):
        self.n = 0
        self.networks: set = set()
        self.containers: dict = {}          # id -> {"kind", "running", "ev"}
        self.procs: dict = {}               # take id -> [[pid, polls left before it exits by itself (None: never)]]
        self.calls: list = []
        self.snapshots: list = []           # (label, agent processes alive at that moment)
        self.kills: list = []               # (take id, user)
        self.removed: list = []
        self.fail_rm, self.fail_times, self.stubborn = set(fail_rm), fail_times, stubborn
        self.begin, self.unreadable = begin, list(unreadable)
        self.specs: dict = {}

    def new(self) -> str:
        self.n += 1
        return f"{0xab0000 + self.n:064x}"

    def kind(self, cid):
        return self.containers.get(cid, {}).get("kind")

    def spawn(self, take_id, lives=None):
        pid = 4000 + sum(len(v) for v in self.procs.values()) + len(self.kills) * 10 + 1
        self.procs.setdefault(take_id, []).append([pid, lives])

    def alive(self, take_id) -> list:
        return [p for p, _ in self.procs.get(take_id, [])]

    def health(self, sid, kind, **extra):
        ev = self.containers[sid]["ev"]
        with open(os.path.join(ev, sc.HEALTH), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"kind": kind, "at": 1.0, **extra}) + "\n")

    def run(self, argv, env=None, timeout=None):
        a = list(argv)
        self.calls.append(a)
        if a[:4] == ["docker", "network", "create", "--internal"]:
            nid = self.new()
            self.networks.add(nid)
            return ok(nid + "\n")
        if a[:3] == ["docker", "network", "rm"]:
            self.networks.discard(a[3])
            return ok()
        if a[:3] == ["docker", "network", "connect"] or a[:2] == ["docker", "logs"]:
            return ok("synthetic proxy log line\n" if a[1] == "logs" else "")
        if a[:2] == ["docker", "create"]:
            cid = self.new()
            if "--network-alias" in a:
                self.containers[cid] = {"kind": "proxy", "running": False}
            elif "--label" in a:
                labels = dict(a[i + 1].split("=", 1) for i, x in enumerate(a) if x == "--label")
                self.containers[cid] = {"kind": "sidecar", "running": False, "ev": labels["ev"],
                                        "tree": labels["tree"]}
            else:
                self.containers[cid] = {"kind": "take", "running": False}
                self.specs[cid] = a
            return ok(cid)
        if a[:2] == ["docker", "start"]:
            self.containers[a[2]]["running"] = True
            return ok()
        if a[:3] == ["docker", "container", "inspect"]:
            return self.inspect(a[3])
        if a[:2] == ["docker", "exec"] and a[2] != "--user" and self.kind(a[2]) == "sidecar":
            return self.ctl(a[2], a[a.index("ctl") + 1], a[a.index("ctl") + 2] if len(a) > a.index("ctl") + 2
                            else None)
        if a[:4] == ["docker", "exec", "--user", rt.AGENT_USER] and a[5:] == ["kill", "-s", "KILL", "--", "-1"]:
            self.kills.append((a[4], a[3]))
            if not self.stubborn:
                self.procs[a[4]] = []
            return ok()
        if a[:2] == ["docker", "top"]:
            rows = []
            for proc in self.procs.get(a[2], []):
                rows.append(f"{proc[0]} {AGENT_HOST_UID} node")
            out = "PID UID COMMAND\n" + "".join(r + "\n" for r in rows) + "4001 103002 sleep\n"
            for proc in list(self.procs.get(a[2], [])):     # a process with a life ends on its own after polls
                if proc[1] is not None:
                    proc[1] -= 1
                    if proc[1] <= 0:
                        self.procs[a[2]].remove(proc)
            return ok(out)
        if a[:3] == ["docker", "rm", "--force"]:
            cid = a[3]
            if self.kind(cid) in self.fail_rm and self.fail_times > 0:
                self.fail_times -= 1
                return rt.Completed(1, "", "synthetic removal failure")
            self.containers.pop(cid, None)
            self.procs.pop(cid, None)
            self.removed.append(cid)
            return ok(cid + "\n")
        if a == [rt.RUNTIME_CLIENT, "ps", "--all", "--no-trunc", "--quiet"]:
            return ok("".join(c + "\n" for c in self.containers))
        raise GuardTripped(f"the fake box refuses {a!r}"[:200])

    def inspect(self, cid):
        c = self.containers.get(cid)
        if c is None:
            return rt.Completed(1, "", "no such container")
        if c["kind"] == "sidecar":
            tree = c["tree"]
            doc = [{"Config": {"User": sc.WATCHER_USER},
                    "HostConfig": {"NetworkMode": "none", "CapDrop": ["ALL"], "CapAdd": ["CAP_DAC_READ_SEARCH"],
                                   "SecurityOpt": ["no-new-privileges"], "Privileged": False, "PidMode": ""},
                    "Mounts": [{"Type": "bind", "Source": tree, "Destination": tree, "RW": False},
                               {"Type": "bind", "Source": c["ev"], "Destination": sc.EVIDENCE_MOUNT, "RW": True}]}]
            return ok(json.dumps(doc))
        a = self.specs[cid]
        val = lambda flag: a[a.index(flag) + 1]  # noqa: E731
        tree = val("--workdir")
        cfg = [m for m in a if m.startswith("type=bind,source=") and m.endswith("target=" + rt.CONFIG_MOUNT)][0]
        cfg = cfg[len("type=bind,source="):-len(",target=" + rt.CONFIG_MOUNT)]
        from decimal import Decimal
        doc = [{"Image": a[-2],
                "Config": {"User": rt.KEEPALIVE_USER, "Entrypoint": ["sleep"], "Cmd": ["infinity"], "Env": [],
                           "WorkingDir": tree},
                "HostConfig": {"NetworkMode": val("--network"), "CapDrop": ["ALL"], "CapAdd": None,
                               "SecurityOpt": ["no-new-privileges"], "Privileged": False, "Devices": None,
                               "PidMode": "", "PidsLimit": int(val("--pids-limit")), "Memory": int(val("--memory")),
                               "MemoryReservation": int(val("--memory-reservation")),
                               "NanoCpus": int(Decimal(val("--cpus")) * 1_000_000_000)},
                "Mounts": [{"Type": "bind", "Source": tree, "Destination": tree, "RW": True},
                           {"Type": "bind", "Source": cfg, "Destination": rt.CONFIG_MOUNT, "RW": True}],
                "State": {"Running": c["running"], "ExitCode": 0, "OOMKilled": False}}]
        return ok(json.dumps(doc))

    def ctl(self, sid, command, label):
        if command == "begin":
            if self.begin == "malformed":
                return ok("not a reply\n")
            if self.begin == "refused":
                return rt.Completed(1, reply("begin", "pre-1", ok_=False), "")
            self.health(sid, sc.WATCHER_START)
            return ok(reply("begin", "pre-1"))
        if command == "snapshot":
            takes = [c for c, v in self.containers.items() if v["kind"] == "take"]
            self.snapshots.append((label, sum(len(self.alive(t)) for t in takes)))
            self.health(sid, sc.WATCHER_STOP, exit_code=0)
            self.health(sid, sc.WATCHER_START)
            return ok(reply("snapshot", label, unreadable_consequential=self.unreadable))
        if command == "finish":
            self.health(sid, sc.WATCHER_STOP, exit_code=0)
            return ok(reply("finish"))
        return ok(reply("status"))

    def empty(self) -> list:
        """What is still there: containers, networks, agent processes (empty when the box is clean)."""
        left = [f"container {v['kind']} {c[:8]}" for c, v in self.containers.items()]
        left += [f"network {n[:8]}" for n in self.networks]
        left += [f"agent process {p} in {t[:8]}" for t, ps in self.procs.items() for p, _ in ps]
        return left


class Clock:
    def __init__(self):
        self.now = 1000.0
        self.slept: list = []

    def __call__(self):
        return self.now

    def sleep(self, s):
        self.slept.append(s)
        self.now += s


class FakeAdapter(aa.AgentAdapter):
    """No model: each scripted turn writes its stream into the take folder, may start background processes in the
    take container (a background writer), and returns its TurnResult. `raise_at` makes turn n raise (the harness
    cannot go on)."""

    name = hb.CLAUDE_CODE

    def __init__(self, box: FakeBox, take, turns, *, raise_at=None):
        super().__init__()
        self.box, self.take, self.turns, self.raise_at = box, take, list(turns), raise_at
        self.lines: list = []
        self.ended = 0

    def version(self):
        return PROFILE["version"]

    def _start(self, take):
        return {"container_id": self.take.launched.take_id}

    def _turn(self, line, *, first, budget_s):
        n = self._turns + 1
        if self.raise_at == n:
            raise RuntimeError("synthetic harness failure")
        self.lines.append(line)
        spec = self.turns[n - 1]
        path = drive.stream_path(self.take, n)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"type": "assistant", "text": spec.get("text", "plain")}) + "\n")
        for lives in spec.get("spawn", ()):
            self.box.spawn(self.take.launched.take_id, lives)
        end = spec.get("end", labels4.END_TURN)
        return aa.TurnResult(exit_code=0 if end == labels4.END_TURN else 137, text=spec.get("text", "plain"),
                             stream_path=path, end_reason=end,
                             init={"model": MODEL, "permission_mode": PROFILE["permission_mode"],
                                   "version": PROFILE["version"]},
                             api_errors=[], counters={"oom_kill_delta": 0, "pids_max_delta": 0},
                             started_at=1.0, ended_at=2.0, agent_output=True)

    def _end(self):
        self.ended += 1


def preflight_record(ok_=True) -> dict:
    checks = [{"id": c, "ok": True, "detail": "synthetic"} for c in pf.PREFLIGHT_CHECKS]
    if not ok_:
        checks[0] = dict(checks[0], ok=False, detail="synthetic failure")
    return {"ok": ok_, "checks": checks, "recorded": {}}


class Spy:
    """collect_and_evaluate's stand-in: records every call, returns a closed record or raises."""

    def __init__(self, result=None, raises=None):
        self.result, self.raises, self.calls = result, raises, []

    def __call__(self, runtime, **kw):
        self.calls.append(kw)
        if self.raises is not None:
            raise self.raises
        return copy.deepcopy(self.result if self.result is not None else preflight_record())


def git(root: Path, *args: str) -> str:
    got = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if got.returncode:
        raise RuntimeError(f"scratch git {args[0]} failed: {got.stderr.strip()}")
    return got.stdout.strip()


def git_bytes(root: Path, *args: str) -> bytes:
    got = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if got.returncode:
        raise RuntimeError(f"scratch git {args[0]} failed")
    return got.stdout


@contextlib.contextmanager
def scratch_repo():
    root = Path(tempfile.mkdtemp(dir=SCRATCH)).resolve()
    git(root, "init", "-q")
    for key, value in (("user.name", "synthetic"), ("user.email", "synthetic@example.invalid"),
                       ("commit.gpgsign", "false"), ("maintenance.auto", "false"), ("gc.auto", "0"),
                       ("core.hooksPath", str(SCRATCH / "no-hooks"))):
        git(root, "config", key, value)
    (root / "README").write_text("synthetic scratch repository\n")
    git(root, "add", "--", "README")
    git(root, "commit", "-q", "-m", "Start a synthetic scratch repository")
    yield root


class Rig:
    """One scratch repository, one fake box, a TakeDriver and a TakeRepo wired the way the drive step runs them."""

    def __init__(self, mod, root: Path, *, box=None, turns=None, raise_at=None, checker=None, spy=None,
                 scanner=None, secrets=None):
        self.mod, self.root = mod, root
        self.box = box or FakeBox()
        self.clock = Clock()
        self.turns = turns if turns is not None else [{"text": "plain"}, {"text": "plain again"}]
        self.raise_at = raise_at
        self.adapters: list = []
        self.cfg_parent = Path(tempfile.mkdtemp(dir=SCRATCH)).resolve()
        self.count = 0
        self.spy = spy or Spy()
        self.checked: list = []
        self.checker = checker or self.clean_checker
        self.driver = mod.TakeDriver(
            runtime=self.box, take_folder=self.take_folder, config_parent=str(self.cfg_parent),
            spec_for=self.spec_for, sidecar_for=self.sidecar_for, proxy=rt.ProxyLaunch(
                image="sha256:" + "9" * 64, conf_source=str(SCRATCH / "proxy.conf"), conf_target="/etc/squid/x.conf",
                command=("squid", "-N"), user="13:13", alias="proxy"),
            lock_path=str(SCRATCH / "synthetic.lock"), hosts={"api": "synthetic.invalid"},
            adapter_for=self.adapter_for, script_for=lambda r: [f"line {i}" for i in range(1, len(self.turns) + 1)],
            pin_for=lambda r: batch.expected_pin(r, table()), checker=self.checker,
            secrets=secrets or (lambda: [("token", TOKEN)]), rules_scanner=scanner or (lambda paths: []),
            uid_map=UID_MAP, budget_s=600, finalize_wait_s=CAP_S, poll_s=POLL_S, clock=self.clock,
            sleep=self.clock.sleep)
        self.repo = mod.TakeRepo(runtime=self.box, record_files=self.driver.record_files,
                                 secrets=lambda: [("token", TOKEN)], rules_scanner=lambda paths: [], root=root,
                                 repo=root, on_published=self.driver.published)

    def take_folder(self, r):
        self.count += 1
        return str(self.root / "records" / f"{r['slot']}-{self.count}")

    def spec_for(self, r, cfg):
        tree = SCRATCH / f"tree-{self.root.name}-{self.count}"
        tree.mkdir(exist_ok=True)
        return rt.TakeSpec(image=IMAGE, run_tree=str(tree), config_dir=cfg, network=PLACEHOLDER_NET,
                           memory_reservation=512 * 2 ** 20, memory=3 * 512 * 2 ** 20, cpus="2", pids_limit=256)

    def sidecar_for(self, r, ev):
        tree = str(SCRATCH / f"tree-{self.root.name}-{self.count}")
        expect = {"user": sc.WATCHER_USER, "network_mode": "none", "cap_drop": ["ALL"],
                  "cap_add": ["CAP_DAC_READ_SEARCH"], "security_opt": ["no-new-privileges"], "privileged": False,
                  "pid_mode": "", "mounts": [{"source": tree, "destination": tree, "rw": False},
                                             {"source": ev, "destination": sc.EVIDENCE_MOUNT, "rw": True}]}
        return rt.SidecarLaunch(
            create_argv=("docker", "create", "--network", "none", "--label", "ev=" + ev, "--label", "tree=" + tree,
                         "side-image"),
            start_argv_for=lambda i: ["docker", "start", i],
            ctl_argv_for=lambda i, c, label=None: ["docker", "exec", i, "python3", "-I", "-B", "/opt/w/sidecar.py",
                                                   "ctl", c] + ([label] if label else []),
            rm_argv_for=lambda i: ["docker", "rm", "--force", i], expect=expect)

    def adapter_for(self, r, take):
        a = FakeAdapter(self.box, take, self.turns, raise_at=self.raise_at)
        self.adapters.append(a)
        return a

    def clean_checker(self, r, take, turns):
        self.checked.append((r["slot"], len(turns)))
        return {"checker_reasons": [], "checker_events": 0, "unexplained_operator_diffs": 0, "finalize_abort": False}

    def take(self, slot="s1"):
        return self.driver._by_slot.get(slot) or [t for t in self.driver.published_takes if t.row["slot"] == slot][-1]

    def batch(self, rows):
        return batch.Batch(self.driver, self.repo, Window(), table=table(), serial=True)


class Window:
    def wait_reset(self):
        return None


@contextlib.contextmanager
def spying(spy):
    with mock.patch.object(pf, "collect_and_evaluate", spy):
        yield spy


def missing_api(mod, prefix, *names):
    gone = [n for n in names if not hasattr(mod, n)]
    return [f"{prefix}: drive.py has no {', '.join(gone)}"] if gone else []


def guarded(prefix):
    """A bound check never raises: an unexpected exception is an ERROR line, never a kill."""
    def wrap(fn):
        def check(mod):
            try:
                return fn(mod, prefix)
            except Exception as e:  # noqa: BLE001
                return [f"ERROR {prefix}: {type(e).__name__}: {str(e)[:240]}"]
        check.__name__ = fn.__name__
        return check
    return wrap


def run_batch(rig, rows):
    with spying(rig.spy):
        b = rig.batch(rows)
        return b, b.run(rows)


# ------------------------------------------------------------------------------------------------ the bound checks
@guarded("B1-rollback")
def b1_rollback(mod, p):
    out = missing_api(mod, p, "TakeDriver", "TakeRepo", "CommitRefused")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root)
        r1 = row(1)
        rig.repo.register(r1, 1)
        rig.repo.commit_records(r1, 1, outcome(r1))              # one committed outcome: the ledger is tracked
        head_ledger = git_bytes(root, "show", "HEAD:outcomes.json")
        r2 = row(2)
        rig.repo.register(r2, 1)
        bad = root / "records" / "bad"
        bad.mkdir(parents=True)
        (bad / "launch.json").write_text(json.dumps({"note": TOKEN}) + "\n")     # unmaskable: the commit refuses
        repo = mod.TakeRepo(runtime=rig.box, record_files=lambda r, a: [(str(bad / "launch.json"), "launch")],
                            secrets=lambda: [("token", TOKEN)], rules_scanner=lambda paths: [], root=root, repo=root)
        try:
            repo.commit_records(r2, 1, outcome(r2))
            return [f"{p}: a commit carrying an unmaskable value was not refused"]
        except mod.CommitRefused:
            pass
        if (root / "outcomes.json").read_bytes() != head_ledger:
            out.append(f"{p}: the ledger was left with the refused outcome, not HEAD's bytes")
        staged = git(root, "diff", "--cached", "--name-only")
        if staged:
            out.append(f"{p}: the refused commit left names staged: {staged.split()}")
        clean = mod.TakeRepo(runtime=rig.box, record_files=lambda r, a: [], secrets=lambda: [("token", TOKEN)],
                             rules_scanner=lambda paths: [], root=root, repo=root)
        try:
            clean.commit_records(r2, 1, outcome(r2, state=labels4.FAILED, final=False, drive_started=False))
        except Exception as e:  # noqa: BLE001
            out.append(f"{p}: after the refusal the same take could not commit cleanly: {type(e).__name__}: {e}")
    return out


def outcome(r, attempt=1, state=labels4.GRADED, **kw):
    o = batch.Batch._outcome(r, attempt, None, state=state)
    o.update(batch.Batch._fate(final=True))
    o.update(kw)
    return o


@guarded("B2-preflight")
def b2_preflight(mod, p):
    out = missing_api(mod, p, "TakeDriver", "preflight_take")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root)
        r = row(1)
        order = []
        spy = Spy()
        real = spy.__call__

        def recording(runtime, **kw):
            order.append(("preflight", len(rig.adapters)))
            return real(runtime, **kw)
        with mock.patch.object(pf, "collect_and_evaluate", recording):
            cid = rig.driver.launch(r)
            take = rig.take()
            rig.driver.drive(r, cid)
        if len(spy.calls) != 1:
            return [f"{p}: collect_and_evaluate was called {len(spy.calls)} times, not once"]
        kw = spy.calls[0]
        if order != [("preflight", 0)]:
            out.append(f"{p}: preflight did not run before every turn: {order}")
        if kw.get("launched") is not take.launched or kw["launched"].spec is None \
                or kw["launched"].spec.network == PLACEHOLDER_NET:
            out.append(f"{p}: preflight did not get the Launched record launch returned (its spec)")
        if kw.get("sidecar") is not take.sidecar:
            out.append(f"{p}: preflight did not get the sidecar's own launch record")
        if kw.get("evidence_dir") != take.evidence_dir:
            out.append(f"{p}: preflight's evidence folder is not the take's")
        if kw.get("harness") != hb.CLAUDE_CODE or kw.get("lock_path") != str(SCRATCH / "synthetic.lock"):
            out.append(f"{p}: preflight's harness or lock path is not the take's")
        begin = kw.get("begin_reply")
        if not isinstance(begin, dict) or begin.get("command") != "begin" or begin.get("label") != "pre-1":
            out.append(f"{p}: preflight did not get the sidecar's parsed begin reply: {begin!r}")
        if not os.path.isfile(os.path.join(take.folder, mod.PREFLIGHT_RECORD)):
            out.append(f"{p}: no preflight record beside the evidence")
    return out


@guarded("B3-preturn")
def b3_preturn(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    cases = {"a failed check": Spy(result=preflight_record(ok_=False)),
             "a typed refusal": Spy(raises=rt.Refused("synthetic: the launch record is incomplete"))}
    for why, spy in cases.items():
        with scratch_repo() as root:
            rig = Rig(mod, root, spy=spy)
            b, got = run_batch(rig, [row(1)])
            o = got[0]
            if rig.adapters:
                out.append(f"{p}: {why}: an adapter was started, so a turn could run")
            if o["state"] != labels4.REHEARSAL:
                out.append(f"{p}: {why}: routed {o['state']!r} ({o['reason']}), not a rehearsal")
            elif o["records"]["preflight"]["ok"] is not False or o["records"]["ledger"]["turns"] != 0:
                out.append(f"{p}: {why}: the records do not say preflight failed with no turn")
            take = rig.take()
            refusal = os.path.join(take.folder, mod.REFUSAL_RECORD)
            if why == "a typed refusal" and not os.path.isfile(refusal):
                out.append(f"{p}: {why}: no refusal record was written")
    return out


@guarded("B4-scan")
def b4_scan(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    with scratch_repo() as root:
        events = []

        def checker(r, take, turns):
            events.append("checker")
            return {"checker_reasons": [], "checker_events": 2, "unexplained_operator_diffs": 0,
                    "finalize_abort": False}
        rig = Rig(mod, root, turns=[{"text": "plain"}, {"text": f"I found {TOKEN} here"}], checker=checker)
        real_route = routing.route
        seen = {}

        def route(records, t):
            take = rig.take()
            stream = drive_stream(take, 2)
            seen["masked before routing"] = TOKEN not in stream.read_text() and "[masked: token]" in \
                stream.read_text()
            return real_route(records, t)
        with mock.patch.object(routing, "route", route):
            b, got = run_batch(rig, [row(1)])
        o = got[0]
        if o["state"] != labels4.GRADED:
            return [f"{p}: the take routed {o['state']!r} ({o['reason']}), not graded"]
        if not seen.get("masked before routing"):
            out.append(f"{p}: the stream still held the value when routing ran (scan after route)")
        if o["records"]["events"]["outside_reach"] != 3:
            out.append(f"{p}: outside_reach is {o['records']['events']['outside_reach']}, not the masked hit plus "
                       f"the checker's two")
        if o["mask"] is not True or "outside-reach" not in (o["events"] or []):
            out.append(f"{p}: the take was not annotated as masked with its event: {o['mask']}, {o['events']}")
        rel = drive_stream(rig.take(), 2).relative_to(root).as_posix()
        committed = git_bytes(root, "show", f"HEAD:{rel}")
        if TOKEN.encode() in committed or b"[masked: token]" not in committed:
            out.append(f"{p}: the committed stream is not the masked bytes")
    return out


def drive_stream(take, n) -> Path:
    return Path(take.folder) / f"turn-{n}.jsonl"


ROADS = ("passed", "failed check", "typed refusal", "adapter raises", "timed out", "scan refuses")


@guarded("B5-cleanup")
def b5_cleanup(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    for road in ROADS:
        with scratch_repo() as root:
            spy = {"failed check": Spy(result=preflight_record(ok_=False)),
                   "typed refusal": Spy(raises=rt.NotReady("synthetic: a lock value is PENDING"))}.get(road)
            turns = [{"text": "plain", "spawn": (None,)}, {"text": "plain", "spawn": (None,)}]
            if road == "timed out":
                turns = [{"text": "plain", "spawn": (None,), "end": labels4.TIMED_OUT}]
            scanner = (lambda paths: [{"path": paths[0], "line": 1, "rule": "synthetic-rule"}]) \
                if road == "scan refuses" else None
            rig = Rig(mod, root, spy=spy, turns=turns, raise_at=2 if road == "adapter raises" else None,
                      scanner=scanner)
            with spying(rig.spy):
                cid = rig.driver.launch(row(1))
                ids = list(rig.driver._by_slot["s1"].launched.ids())
                try:
                    rig.driver.drive(row(1), cid)
                    raised = None
                except Exception as e:  # noqa: BLE001
                    raised = e
            if road in ("adapter raises", "scan refuses") and raised is None:
                out.append(f"{p}: {road}: drive() did not raise")
            if road not in ("adapter raises", "scan refuses") and raised is not None:
                out.append(f"{p}: {road}: drive() raised {type(raised).__name__}: {raised}")
            left = rig.box.empty()
            if left:
                out.append(f"{p}: {road}: the box is not clean after drive(): {left}")
            if any(i not in rig.box.removed for i in ids):
                out.append(f"{p}: {road}: a container was not removed by its recorded id")
            if road != "failed check" and road != "typed refusal" and not any(
                    user == rt.AGENT_USER for _, user in rig.box.kills):
                out.append(f"{p}: {road}: no kill ran as the agent's own uid")
            if not os.path.isfile(os.path.join(rig.take().folder, mod.TEARDOWN_RECORD)):
                out.append(f"{p}: {road}: no teardown record")
    return out


@guarded("B6-quiesce")
def b6_quiesce(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root, turns=[{"text": "plain", "spawn": (None,)}, {"text": "plain", "spawn": (2,)}])
        with spying(rig.spy):
            cid = rig.driver.launch(row(1))
            recs = rig.driver.drive(row(1), cid)
        snaps = dict(rig.box.snapshots)
        if snaps.get("post-1") != 0:
            out.append(f"{p}: post-1 was signalled with {snaps.get('post-1')} agent process(es) alive")
        if snaps.get("post-2") != 0:
            out.append(f"{p}: post-2 was signalled with {snaps.get('post-2')} agent process(es) alive")
        if [lbl for lbl, _ in rig.box.snapshots] != ["post-1", "pre-2", "post-2"]:
            out.append(f"{p}: the snapshot labels are {[lbl for lbl, _ in rig.box.snapshots]}")
        if recs["quiescence_kill"] is not True or recs["quiescence_cap_survivors"] != 1:
            out.append(f"{p}: the cap kill is not recorded: kill {recs['quiescence_kill']}, survivors "
                       f"{recs['quiescence_cap_survivors']}")
        first_kill = next((i for i, a in enumerate(rig.box.calls) if a[-2:] == ["--", "-1"]), None)
        first_snap = next((i for i, a in enumerate(rig.box.calls) if "snapshot" in a), None)
        if first_kill is None or first_snap is None or first_kill > first_snap:
            out.append(f"{p}: the first snapshot came before the cap kill")
        if CAP_S not in [sum(rig.clock.slept[:i]) for i in range(len(rig.clock.slept) + 1)]:
            out.append(f"{p}: the driver did not wait out the cap ({rig.clock.slept})")
    with scratch_repo() as root:
        rig = Rig(mod, root, turns=[{"text": "plain", "spawn": (None,), "end": labels4.TIMED_OUT}])
        with spying(rig.spy):
            cid = rig.driver.launch(row(1))
            recs = rig.driver.drive(row(1), cid)
        if rig.clock.slept:
            out.append(f"{p}: a timed-out turn's processes were waited on ({rig.clock.slept}), not killed at once")
        if dict(rig.box.snapshots).get("post-1") != 0:
            out.append(f"{p}: a timed-out turn's snapshot came with processes alive")
        if recs["quiescence_kill"] is not False:
            out.append(f"{p}: a timeout kill was recorded as a quiescence kill")
    return out


@guarded("B7-remove")
def b7_remove(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root, box=FakeBox(fail_rm=("take",), fail_times=1))
        with spying(rig.spy):
            cid = rig.driver.launch(row(1))
            rig.driver.drive(row(1), cid)
        if cid not in rig.box.containers:
            return [f"{p}: the fake teardown failure did not leave the take container"]
        rig.driver.remove(cid)
        if cid in rig.box.containers:
            out.append(f"{p}: remove() did not remove the still-listed take container")
        rm = [a for a in rig.box.calls if a[:3] == ["docker", "rm", "--force"] and a[3] == cid]
        if len(rm) != 2:
            out.append(f"{p}: the take container was removed {len(rm)} times by its id, not twice")
    with scratch_repo() as root:
        rig = Rig(mod, root, box=FakeBox(fail_rm=("take",), fail_times=3))
        with spying(rig.spy):
            cid = rig.driver.launch(row(1))
            rig.driver.drive(row(1), cid)
        try:
            rig.driver.remove(cid)
            out.append(f"{p}: a container still listed after its removal did not raise")
        except rt.LeakedContainer:
            pass
    with scratch_repo() as root:
        rig = Rig(mod, root)
        cid = rig.driver.launch(row(1))
        calls = len(rig.box.calls)
        with spying(rig.spy):
            rig.driver.drive(row(1), cid)
        rig.driver.remove(cid)
        if [a for a in rig.box.calls[calls:] if a[:2] == ["docker", "rm"] and a[3] == cid] != [
                ["docker", "rm", "--force", cid]]:
            out.append(f"{p}: a container already gone was removed again, or never by its id")
    with scratch_repo() as root:
        box = FakeBox(fail_rm=("take",), fail_times=1)
        rig = Rig(mod, root, box=box)
        real = box.run

        def failing_start(argv, env=None, timeout=None):
            if list(argv)[:2] == ["docker", "start"] and box.kind(argv[2]) == "take":
                return rt.Completed(1, "", "synthetic start failure")
            return real(argv, env=env, timeout=timeout)
        box.run = failing_start
        try:
            rig.driver.launch(row(1))
            out.append(f"{p}: a failed launch did not raise")
        except rt.LaunchError as e:
            if getattr(e, "container_id", "unset") is None or e.container_id not in box.containers:
                out.append(f"{p}: a launch whose teardown left the take container did not carry its id")
    return out


@guarded("B8-config")
def b8_config(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root)
        r = row(1)
        rig.repo.register(r, 1)
        with spying(rig.spy):
            cid = rig.driver.launch(r)
            cfg = rig.take().config_dir
            records = rig.driver.drive(r, cid)
        if not os.path.isdir(cfg):
            out.append(f"{p}: the config folder was deleted before the records were committed")
        rig.driver.remove(cid)
        o = outcome(r, records=records, container_id=cid)
        rig.repo.commit_records(r, 1, o)
        if os.path.exists(cfg):
            out.append(f"{p}: the config folder outlived the commit of the take's records")
    with scratch_repo() as root:
        rig = Rig(mod, root)
        r = row(1)
        rig.repo.register(r, 1)
        with spying(rig.spy):
            cid = rig.driver.launch(r)
            cfg = rig.take().config_dir
            rig.driver.drive(r, cid)
        with open(os.path.join(rig.take().folder, "launch.json"), "a", encoding="utf-8") as fh:
            fh.write(TOKEN + "\n")                       # the commit's scan refuses the unmaskable launch record
        try:
            rig.repo.commit_records(r, 1, outcome(r, container_id=cid))
            out.append(f"{p}: the planted refusal did not refuse the commit")
        except mod.CommitRefused:
            pass
        if not os.path.isdir(cfg):
            out.append(f"{p}: the config folder was deleted although the commit was refused")
    return out


# ------------------------------------------------------------------------------------------------ the tests
def need(case, *names):
    """A part-2 name missing from drive.py is this test's failure (an assertion), never an error."""
    gone = [n for n in names if not hasattr(drive, n)]
    case.assertEqual(gone, [], f"drive.py has no {', '.join(gone)}")


class TestGuardArmed(unittest.TestCase):
    def test_a_process_start_outside_scratch_git_trips(self):
        for argv in (["true"], [rt.RUNTIME_CLIENT, "ps"], ["git", "-C", "/", "status"]):
            with self.subTest(argv=argv):
                with self.assertRaises(GuardTripped):
                    subprocess.run(argv, capture_output=True)
        with self.assertRaises(GuardTripped):
            os.system("true")

    def test_the_runtime_spellings_are_filled_only_here(self):
        self.assertEqual(rt.TOP_FORMAT, TOP)
        self.assertEqual(rt.INSPECT_STATUS, "confirmed-in-test")


class TestTheTakePath(unittest.TestCase):
    """The real take path: batch.Batch drives TakeDriver and commits through TakeRepo on a scratch repository."""

    def test_a_clean_take_is_graded_committed_and_leaves_nothing(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root)
            b, got = run_batch(rig, [row(1)])
            self.assertEqual([o["state"] for o in got], [labels4.GRADED], got[0]["reason"])
            o = got[0]
            self.assertEqual(o["records"]["ledger"]["turns"], 2)
            self.assertIs(o["records"]["preflight"]["ok"], True)
            self.assertEqual(o["records"]["sidecar"], {"start_record": True, "stop_record": True, "exit_code": 0,
                                                       "queue_overflow": False})
            self.assertEqual(rig.box.empty(), [])
            self.assertEqual(git(root, "status", "--porcelain"), "")
            names = git(root, "show", "--format=", "--name-only", "HEAD").split()
            self.assertIn("outcomes.json", names)
            self.assertTrue(any(n.endswith("/launch.json") for n in names), names)
            self.assertTrue(any(n.endswith("/teardown.json") for n in names), names)
            self.assertTrue(any(n.endswith("/evidence/health.jsonl") for n in names), names)
            self.assertEqual(len(rig.spy.calls), 1)
            self.assertEqual(rig.adapters[0].lines, ["line 1", "line 2"])
            self.assertEqual(rig.adapters[0].ended, 1)
            self.assertFalse(os.path.exists(rig.take().config_dir))

    def test_two_slots_each_commit_their_own_folder(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root)
            b, got = run_batch(rig, [row(1), row(2)])
            self.assertEqual([o["state"] for o in got], [labels4.GRADED, labels4.GRADED])
            self.assertEqual(rig.box.empty(), [])
            self.assertEqual(len(drive.TakeRepo(runtime=rig.box, record_files=lambda r, a: [], secrets=list,
                                                rules_scanner=lambda p: [], root=root, repo=root).history()), 2)

    def test_a_watcher_gap_routes_harness_error_and_still_cleans_up(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, box=FakeBox(unreadable=["plan/approval.md"]))
            b, got = run_batch(rig, [row(1)])
            self.assertEqual(got[0]["state"], labels4.HARNESS_ERROR)
            self.assertEqual(got[0]["records"]["unreadable_consequential"], ["plan/approval.md"])
            self.assertEqual(rig.box.empty(), [])

    def test_a_malformed_begin_is_a_pre_turn_refusal(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, box=FakeBox(begin="malformed"))
            b, got = run_batch(rig, [row(1)])
            self.assertEqual(got[0]["state"], labels4.REHEARSAL)
            self.assertEqual(rig.spy.calls, [])
            self.assertEqual(rig.adapters, [])
            self.assertEqual(rig.box.empty(), [])
            refusal = json.loads(Path(rig.take().folder, drive.REFUSAL_RECORD).read_text())
            self.assertEqual(refusal["refused"], "ReplyError")

    def test_a_refused_begin_reaches_preflight_which_judges_it(self):
        """A begin that replied ok: false is S1's to judge (preflight's sidecar-begin check); the driver hands it on
        unaltered, and the failed record it gets back runs no turn."""
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, box=FakeBox(begin="refused"), spy=Spy(result=preflight_record(ok_=False)))
            b, got = run_batch(rig, [row(1)])
            self.assertEqual(got[0]["state"], labels4.REHEARSAL)
            self.assertIs(rig.spy.calls[0]["begin_reply"]["ok"], False)
            self.assertEqual(rig.adapters, [])
            self.assertEqual(rig.box.empty(), [])

    def test_an_adapter_that_raises_is_failed_and_the_box_is_clean(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, raise_at=2)
            b, got = run_batch(rig, [row(1)])
            self.assertEqual(got[0]["state"], labels4.FAILED)
            self.assertIn("drive failed", got[0]["reason"])
            self.assertEqual(rig.box.empty(), [])
            self.assertEqual(rig.adapters[0].ended, 1)

    def test_a_leaked_take_container_stops_the_loop_and_refuses_the_restart(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, box=FakeBox(fail_rm=("take",), fail_times=5))
            b, got = run_batch(rig, [row(1), row(2)])
            self.assertEqual(len(got), 1)
            self.assertIsNotNone(got[0]["leaked_container"])
            self.assertIsNotNone(b.stopped)
            with self.assertRaises(rt.LeakedContainer):
                rig.repo.register(row(2), 1)

    def test_an_unknown_file_in_the_take_folder_refuses(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root)
            with spying(rig.spy):
                cid = rig.driver.launch(row(1))
                Path(rig.take().folder, "stray.txt").write_text("x\n")
                with self.assertRaises(drive.DriveRefused):
                    rig.driver.drive(row(1), cid)
            self.assertEqual(rig.box.empty(), [])

    def test_drive_refuses_an_unrecorded_or_second_drive(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root)
            with spying(rig.spy):
                with self.assertRaises(drive.DriveRefused):
                    rig.driver.drive(row(1), "0" * 64)
                cid = rig.driver.launch(row(1))
                with self.assertRaises(drive.DriveRefused):
                    rig.driver.drive(row(2), cid)
                rig.driver.drive(row(1), cid)
                with self.assertRaises(drive.DriveRefused):
                    rig.driver.drive(row(1), cid)

    def test_sidecar_health_reads_a_gap_never_healthy(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with tempfile.TemporaryDirectory(dir=SCRATCH) as ev:
            self.assertEqual(drive.sidecar_health(ev), {"start_record": False, "stop_record": False,
                                                         "exit_code": -1, "queue_overflow": False})
            with open(os.path.join(ev, sc.HEALTH), "w") as fh:
                for rec in ({"kind": sc.WATCHER_START}, {"kind": sc.WATCHER_STOP, "exit_code": 137},
                            {"kind": sc.QUEUE_OVERFLOW}):
                    fh.write(json.dumps(rec) + "\n")
            self.assertEqual(drive.sidecar_health(ev), {"start_record": True, "stop_record": False,
                                                         "exit_code": 137, "queue_overflow": True})


class TestBoundChecks(unittest.TestCase):
    def test_b1_a_refused_commit_restores_the_ledger(self):
        self.assertEqual(b1_rollback(drive), [])

    def test_b2_preflight_is_s1s_entry_point_before_any_turn(self):
        self.assertEqual(b2_preflight(drive), [])

    def test_b3_a_pre_turn_refusal_runs_no_turn_and_rehearses(self):
        self.assertEqual(b3_preturn(drive), [])

    def test_b4_scan_mask_route_commit(self):
        self.assertEqual(b4_scan(drive), [])

    def test_b5_every_road_cleans_up(self):
        self.assertEqual(b5_cleanup(drive), [])

    def test_b6_quiescence_kills_as_the_agent_before_the_snapshot(self):
        self.assertEqual(b6_quiesce(drive), [])

    def test_b7_remove_is_by_the_recorded_id(self):
        self.assertEqual(b7_remove(drive), [])

    def test_b8_the_config_folder_goes_only_after_the_commit(self):
        self.assertEqual(b8_config(drive), [])


# ------------------------------------------------------------------------------------------------ the real-box half
class RealBoxHalf:
    """CP2's real-box half of this module, a NAMED STUB: not a TestCase, so the battery (whose SKIP_ALLOWED is empty)
    never collects it. Each method raises SkipTest naming the real-box step it waits on."""

    def test_stub_take_on_the_real_box(self):
        raise unittest.SkipTest(REAL_BOX_STEP)


class TestRealBoxStub(unittest.TestCase):
    def test_the_real_box_half_is_a_named_stub_that_skips(self):
        with self.assertRaises(unittest.SkipTest) as cm:
            RealBoxHalf().test_stub_take_on_the_real_box()
        self.assertEqual(str(cm.exception), REAL_BOX_STEP)
        self.assertFalse(issubclass(RealBoxHalf, unittest.TestCase))


# ------------------------------------------------------------------------------------------------ the witnesses
class WitnessNotPerformed(AssertionError):
    pass


def witness_module(edits: tuple) -> types.ModuleType:
    """drive.py with `edits` applied, compiled in memory as its own module (never written to disk). Every anchor must
    occur exactly once, or the witness was not performed."""
    with open(drive.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    name = "drive_w6h_witness"
    mod = types.ModuleType(name)
    mod.__file__ = drive.__file__
    sys.modules[name] = mod
    try:
        exec(compile(src, drive.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    return mod


# name: (edits to drive.py, the bound check, the line prefix that is its own assertion)
WITNESSES = {
    "omit-restore": ((("                self._restore()\n", "                pass\n"),), b1_rollback, "B1-rollback"),
    "skip-preflight": ((("            ok = self._preflight(take, harness)\n", "            ok = True\n"),),
                       b2_preflight, "B2-preflight"),
    "failed-preflight-read-as-passed": ((("        return record[\"ok\"] is True\n", "        return True\n"),),
                                        b3_preturn, "B3-preturn"),
    "no-drive-scan": ((("        scan = _scan_record.scan(self.take_files(take), list(self.secrets()), "
                        "rules_scanner=self.rules_scanner,\n",
                        "        scan = {\"refused\": [], \"events\": 0} or _scan_record.scan(self.take_files(take), "
                        "list(self.secrets()), rules_scanner=self.rules_scanner,\n"),),
                      b4_scan, "B4-scan"),
    "no-finally-cleanup": ((("            self._cleanup(take, adapter)\n", "            pass\n"),),
                           b5_cleanup, "B5-cleanup"),
    "no-cap-kill": ((("            if survivors:\n                self._kill(take)\n",
                      "            if False:\n                self._kill(take)\n"),), b6_quiesce, "B6-quiesce"),
    "remove-never-removes": ((("        if not _run_take.leaked(self.runtime, [container_id], "
                               "caller_env=self.caller_env):\n            return\n",
                               "        return\n"),), b7_remove, "B7-remove"),
    "no-on-published": ((("                self.on_published(row, attempt)\n", "                pass\n"),),
                        b8_config, "B8-config"),
}
WITNESS_LOG: list = []


class TestWitnesses(unittest.TestCase):
    """Each witness is killed only by its bound check's own assertion (a line with its prefix), with the bound check
    green on the real drive.py first; an ERROR line, a raise, an unperformed edit or a skip is never a kill. Every
    other line the bound check prints under the witness is listed as collateral, never credited."""

    def kill(self, name):
        edits, check, prefix = WITNESSES[name]
        self.assertEqual(check(drive), [], f"{name}: the bound check is not green on drive.py")
        got = check(witness_module(edits))
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(prefix + ":")]
        collateral = [x for x in got if x not in own and x not in errors]
        line = (f"WITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
                f"{len(collateral)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ", file=sys.stderr, flush=True)
        WITNESS_LOG.append(line)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_omit_restore(self):
        self.kill("omit-restore")

    def test_witness_skip_preflight(self):
        self.kill("skip-preflight")

    def test_witness_failed_preflight_read_as_passed(self):
        self.kill("failed-preflight-read-as-passed")

    def test_witness_no_drive_scan(self):
        self.kill("no-drive-scan")

    def test_witness_no_finally_cleanup(self):
        self.kill("no-finally-cleanup")

    def test_witness_no_cap_kill(self):
        self.kill("no-cap-kill")

    def test_witness_remove_never_removes(self):
        self.kill("remove-never-removes")

    def test_witness_no_on_published(self):
        self.kill("no-on-published")

    def test_the_witnesses_are_named_and_each_bound_to_its_own_check(self):
        self.assertEqual(sorted(WITNESSES), sorted(["omit-restore", "skip-preflight",
                                                    "failed-preflight-read-as-passed", "no-drive-scan",
                                                    "no-finally-cleanup", "no-cap-kill", "remove-never-removes",
                                                    "no-on-published"]))
        self.assertEqual(len({w[1].__name__ for w in WITNESSES.values()}), 8)
        self.assertEqual(len({w[2] for w in WITNESSES.values()}), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
