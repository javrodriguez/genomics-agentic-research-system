#!/usr/bin/env python3
"""box/preflight.py: every check of PREFLIGHT_CHECKS green on a passing world and red on its own break, every
probe's absence or failure read as a failed check, the PENDING refusals, the programs' Python floor and neutrality,
the record's place beside the evidence folder, and the after-take credential check.

A FakeRuntime answers the probes; no test reaches a real process (the guard below is armed after the one leak-word
read, interface 16). Each guard is also run against in-memory mutants, printed with their red results.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import inspect as pyinspect
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(HERE))
ROUND3 = "e2979b3143081824aadea73523ec41af30c1ddb1"
LANE_LEAD_WORDS = ("gap4", "round 4", "sidecar", "watcher", "evidence", "holdout", "sealed", "probe", "trap",
                   "grader")


def _round3_leak_words() -> tuple:
    """Round 3's pre-registration key leak_words, that key alone, read once (interface 16). Never committed."""
    shown = subprocess.run(["git", "-C", REPO, "show", f"{ROUND3}:evals/gap-study-3/prereg.json"],
                           capture_output=True, check=True)
    return tuple(json.loads(shown.stdout)["leak_words"])


ROUND3_WORDS = _round3_leak_words()
LEAK_WORDS = ROUND3_WORDS + LANE_LEAD_WORDS


class ProcessGuardTripped(AssertionError):
    pass


def _tripwire(name):
    def trip(*a, **k):
        raise ProcessGuardTripped(f"a test reached {name}")
    return trip


GUARDED = [(subprocess, n) for n in ("run", "Popen", "call", "check_call", "check_output", "getoutput",
                                     "getstatusoutput")]
GUARDED += [(os, n) for n in ("system", "popen", "kill", "killpg", "posix_spawn", "posix_spawnp", "fork", "forkpty")
            if hasattr(os, n)]
GUARDED += [(os, n) for n in dir(os) if re.fullmatch(r"(exec|spawn)[lvpe]*", n)]
for _mod, _name in GUARDED:
    setattr(_mod, _name, _tripwire(f"{_mod.__name__}.{_name}"))

from box import preflight as pf  # noqa: E402
from box import run_take as rt  # noqa: E402

ORIG_PROBES = pf.probes
ID = {k: (c * 64) for k, c in (("net", "a"), ("side", "c"), ("take", "d"))}
IMAGE = "sha256:" + "f" * 64
ARMS = (rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI)
HOSTS = {rt.CLAUDE_CODE: "api.anthropic.com", rt.CODEX: "api.openai.com", rt.GEMINI: "generativelanguage.googleapis.com"}
VERSION_OUT = {rt.CLAUDE_CODE: ("2.9.1 (Claude Code)\n", r"([0-9.]+) \(Claude Code\)", "2.9.1"),
               rt.CODEX: ("codex-cli 0.160.1\n", r"codex-cli ([0-9.]+)", "0.160.1"),
               rt.GEMINI: ("0.63.0\n", r"([0-9.]+)", "0.63.0")}
STUDY = ("notes-a", "notes-b/inner")
REFUSED_NAMES = {
    rt.CLAUDE_CODE: ["github.com", "huggingface.co", "api.openai.com", "generativelanguage.googleapis.com"],
    rt.CODEX: ["github.com", "huggingface.co", "api.anthropic.com", "generativelanguage.googleapis.com"],
    rt.GEMINI: ["github.com", "huggingface.co", "api.anthropic.com", "api.openai.com"],
}
CONFIG_HOME = {rt.CLAUDE_CODE: "CLAUDE_CONFIG_DIR", rt.CODEX: "CODEX_HOME", rt.GEMINI: "GEMINI_CLI_HOME"}
CAP_ADD = ["CAP_DAC_READ_SEARCH"]


class FakeRuntime:
    def __init__(self, script=()):
        self.script = list(script)
        self.calls = []
        self.unexpected = []

    def run(self, argv, *, env=None, timeout=None):
        self.calls.append((list(argv), None if env is None else dict(env)))
        if not self.script:
            self.unexpected.append(list(argv))
            raise AssertionError(f"unexpected runtime call {argv}")
        prefix, answer = self.script.pop(0)
        if list(argv[:len(prefix)]) != list(prefix):
            self.unexpected.append(list(argv))
            raise AssertionError(f"runtime call {argv} does not start with {prefix}")
        if isinstance(answer, BaseException):
            raise answer
        return answer


def ok(doc):
    return rt.Completed(0, doc if isinstance(doc, str) else json.dumps(doc), "")


@contextlib.contextmanager
def filled(harness=rt.CLAUDE_CODE):
    """Every PENDING constant evaluate needs, filled in memory only (interface 15)."""
    with mock.patch.object(rt, "INSPECT_STATUS", "confirmed-in-test"), \
            mock.patch.object(pf, "VERSION_PATTERNS", {h: VERSION_OUT[h][1] for h in ARMS}), \
            mock.patch.object(pf, "STUDY_PATHS", STUDY), \
            mock.patch.object(pf, "LEAK_WORDS", LEAK_WORDS):
        yield


class World:
    """A passing take: spec, lock, sidecar expectation and the raw records a FakeRuntime gave run()."""

    def __init__(self, harness=rt.CLAUDE_CODE):
        self.tmp = tempfile.mkdtemp(prefix="w-")
        self.harness = harness
        self.tree = os.path.join(self.tmp, "tree")
        self.cfg = os.path.join(self.tmp, "cfg")
        self.ev = os.path.join(self.tmp, "rec", "ev")
        for d in (self.tree, self.cfg, self.ev):
            os.makedirs(d)
        with open(os.path.join(self.ev, "health.jsonl"), "w") as fh:
            fh.write(json.dumps({"kind": "watcher-start", "at": 1.0}) + "\n")
        self.spec = rt.TakeSpec(image=IMAGE, run_tree=self.tree, config_dir=self.cfg, network=ID["net"],
                                memory_reservation=512 * 2 ** 20, memory=3 * 512 * 2 ** 20, cpus="2", pids_limit=256)
        self.lock = {"image_id": IMAGE, "harness.version": VERSION_OUT[harness][2], "users.agent.uid": 10001,
                     "users.watcher.uid": 10002, "users.keepalive.uid": 10003}
        self.sidecar_expect = {
            "user": "10002:10002", "network_mode": "none", "cap_drop": ["ALL"], "cap_add": list(CAP_ADD),
            "security_opt": ["no-new-privileges"], "privileged": False, "pid_mode": "",
            "mounts": [{"source": self.tree, "destination": self.tree, "rw": False},
                       {"source": self.ev, "destination": "/srv/ev", "rw": True}]}
        self.begin = {"ok": True, "command": "begin", "label": None, "taken_at": 1.0, "rearmed_at": None,
                      "unreadable": [], "unreadable_consequential": [], "problems": []}
        s = self.spec
        self.answers = {
            "identity": {"uid": 10001, "gid": 10001, "status": {
                "Uid": ["10001"] * 4, "Gid": ["10001"] * 4, "CapEff": ["0000000000000000"],
                "CapPrm": ["0000000000000000"], "CapBnd": ["0000000000000000"], "NoNewPrivs": ["1"]}},
            "take-inspect": [{
                "Image": IMAGE,
                "Config": {"User": "10003:10003", "Entrypoint": ["sleep"], "Cmd": ["infinity"],
                           "Env": ["PATH=/usr/bin:/bin"],
                           "WorkingDir": s.run_tree},
                "HostConfig": {"NetworkMode": ID["net"], "CapDrop": ["ALL"], "CapAdd": None,
                               "SecurityOpt": ["no-new-privileges"], "Privileged": False, "Devices": [],
                               "PidMode": "", "PidsLimit": 256, "Memory": s.memory,
                               "MemoryReservation": s.memory_reservation, "NanoCpus": 2_000_000_000},
                "Mounts": [{"Type": "bind", "Source": s.run_tree, "Destination": s.run_tree, "RW": True},
                           {"Type": "bind", "Source": s.config_dir, "Destination": "/opt/cfg", "RW": True}]}],
            "harness-version": VERSION_OUT[harness][0],
            "cgroup": {"cpu.max": "200000 100000", "memory.max": str(s.memory),
                       "memory.low": str(s.memory_reservation), "pids.max": "256"},
            "listing": {"/srv/ev": "FileNotFoundError", self.ev: "FileNotFoundError"},
            "processes": [{"pid": 1, "uid": 10003, "name": "sleep", "cap_eff": 0}],
            "sidecar-inspect": [{
                "Config": {"User": "10002:10002"},
                "HostConfig": {"NetworkMode": "none", "CapDrop": ["ALL"], "CapAdd": list(CAP_ADD),
                               "SecurityOpt": ["no-new-privileges"], "Privileged": False, "PidMode": ""},
                "Mounts": [{"Type": "bind", "Source": self.tree, "Destination": self.tree, "RW": False},
                           {"Type": "bind", "Source": self.ev, "Destination": "/srv/ev", "RW": True}]}],
            "watcher-caps": [{"pid": 1, "uid": 10002, "name": "python3", "cap_eff": 0},
                             {"pid": 9, "uid": 10002, "name": "inotifywait", "cap_eff": 4}],
            "sockets": {"present": [], "docker_host": False},
            "egress": {"via_proxy": {HOSTS[harness]: {"status": 200}, "github.com": {"status": 403}},
                       "direct": {"connected": False, "error": "gaierror"},
                       "resolves": {n: False for n in REFUSED_NAMES[harness]}},
        }

    def probes(self):
        return pf.probes(self.spec, take_id=ID["take"], sidecar_id=ID["side"], harness=self.harness, hosts=HOSTS,
                         evidence_dir=self.ev)

    def script(self):
        out = []
        for p in self.probes():
            if p.argv is not None:
                out.append((list(p.argv[:2]), ok(self.answers[p.id])))
        return out

    def raw(self):
        fake = FakeRuntime(self.script())
        with mock.patch.object(pf, "STUDY_PATHS", STUDY):   # the host-side read looks for the filled list
            raw = pf.run(fake, self.probes(), begin_reply=self.begin, caller_env={"PATH": "/bin"})
        assert not fake.unexpected and not fake.script, (fake.unexpected, fake.script)
        return raw

    def evaluate(self, raw=None, **kw):
        args = dict(spec=self.spec, lock=self.lock, sidecar_expect=self.sidecar_expect, harness=self.harness,
                    hosts=HOSTS)
        args.update(kw)
        return pf.evaluate(self.raw() if raw is None else raw, **args)


def failing(record) -> list:
    return [c["id"] for c in record["checks"] if not c["ok"]]


def set_out(raw, pid, doc):
    raw[pid]["stdout"] = doc if isinstance(doc, str) else json.dumps(doc)


def edit_json(pid, fn):
    def apply(raw, w):
        doc = json.loads(raw[pid]["stdout"])
        fn(doc)
        set_out(raw, pid, doc)
    return apply


def edit_value(pid, fn):
    def apply(raw, w):
        fn(raw[pid]["value"])
    return apply


def edit_world(fn):
    def apply(raw, w):
        fn(w)
    return apply


# Every check's own breaks: each must turn that check (and the record) red.
BREAKS = {
    "agent-non-root": [
        ("root-uid", edit_json("identity", lambda d: d.update(uid=0))),
        ("other-uid", edit_json("identity", lambda d: d.update(uid=10003))),
        ("cap-eff", edit_json("identity", lambda d: d["status"].update(CapEff=["0000000000000400"]))),
        ("cap-prm", edit_json("identity", lambda d: d["status"].update(CapPrm=["0000000000000001"]))),
        ("cap-bnd", edit_json("identity", lambda d: d["status"].update(CapBnd=["00000000a80425fb"]))),
        ("cap-missing", edit_json("identity", lambda d: d["status"].pop("CapBnd"))),
        ("new-privs", edit_json("identity", lambda d: d["status"].update(NoNewPrivs=["0"]))),
        ("lock-agent-uid", edit_world(lambda w: w.lock.update({"users.agent.uid": 1000}))),
        ("lock-agent-pending", edit_world(lambda w: w.lock.update({"users.agent.uid": pf.PENDING}))),
    ],
    "image-matches-lock": [
        ("other-image", edit_json("take-inspect", lambda d: d[0].update(Image="sha256:" + "0" * 64))),
        ("lock-other", edit_world(lambda w: w.lock.update(image_id="sha256:" + "1" * 64))),
        ("lock-pending", edit_world(lambda w: w.lock.update(image_id=pf.PENDING))),
    ],
    "harness-version-matches-lock": [
        ("other-version", lambda raw, w: raw["harness-version"].update(stdout="9.9.9 (Claude Code)\ncodex-cli 9.9.9\n")),
        ("lock-version", edit_world(lambda w: w.lock.update({"harness.version": "0.0.1"}))),
        ("lock-pending", edit_world(lambda w: w.lock.update({"harness.version": pf.PENDING}))),
        ("exit-1", lambda raw, w: raw["harness-version"].update(returncode=1)),
    ],
    "take-inspect-matches-spec": [
        ("third-mount", edit_json("take-inspect", lambda d: d[0]["Mounts"].append(
            {"Type": "bind", "Source": "/x", "Destination": "/x", "RW": False}))),
        ("socket-mount", edit_json("take-inspect", lambda d: d[0]["Mounts"].__setitem__(1, {
            "Type": "bind", "Source": "/run/docker.sock", "Destination": "/opt/cfg", "RW": True}))),
        ("tree-read-only", edit_json("take-inspect", lambda d: d[0]["Mounts"][0].update(RW=False))),
        ("cap-add", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(CapAdd=["NET_RAW"]))),
        ("cap-drop", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(CapDrop=[]))),
        ("security-opt", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(SecurityOpt=[]))),
        ("privileged", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(Privileged=True))),
        ("device", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(Devices=[{"PathOnHost": "/dev/x"}]))),
        ("pids", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(PidsLimit=0))),
        ("memory", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(Memory=0))),
        ("reservation", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(MemoryReservation=0))),
        ("cpus", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(NanoCpus=1))),
        ("network", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(NetworkMode="bridge"))),
        ("host-pid", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(PidMode="host"))),
        ("keepalive-user", edit_json("take-inspect", lambda d: d[0]["Config"].update(User="10001:10001"))),
        ("cmd", edit_json("take-inspect", lambda d: d[0]["Config"].update(Cmd=["sh"]))),
        ("entrypoint", edit_json("take-inspect", lambda d: d[0]["Config"].update(Entrypoint=["/bin/sh", "-c"]))),
        ("no-entrypoint", edit_json("take-inspect", lambda d: d[0]["Config"].pop("Entrypoint"))),
        ("workdir", edit_json("take-inspect", lambda d: d[0]["Config"].update(WorkingDir="/"))),
        ("no-hostconfig", edit_json("take-inspect", lambda d: d[0].pop("HostConfig"))),
    ],
    "limits-apply": [
        ("cpu-max", edit_json("cgroup", lambda d: d.update({"cpu.max": "max 100000"}))),
        ("memory-max", edit_json("cgroup", lambda d: d.update({"memory.max": "max"}))),
        ("memory-low", edit_json("cgroup", lambda d: d.update({"memory.low": "0"}))),
        ("pids-max", edit_json("cgroup", lambda d: d.update({"pids.max": "max"}))),
        ("missing", edit_json("cgroup", lambda d: d.update({"pids.max": {"error": "FileNotFoundError"}}))),
    ],
    "evidence-out-of-reach": [
        ("mount-listed", edit_json("listing", lambda d: d.update({"/srv/ev": "listed"}))),
        ("host-listed", lambda raw, w: edit_json("listing", lambda d: d.update({w.ev: "listed"}))(raw, w)),
        ("one-path", edit_json("listing", lambda d: d.pop("/srv/ev"))),
    ],
    "watcher-invisible": [
        ("unreadable-row", edit_json("processes", lambda d: d.append({"pid": 7, "unreadable": "PermissionError"}))),
        ("watcher-visible", edit_json("processes", lambda d: d.append({"pid": 9, "uid": 10002, "name": "x",
                                                                        "cap_eff": 0}))),
        ("agent-process", edit_json("processes", lambda d: d.append({"pid": 8, "uid": 10001, "name": "x",
                                                                      "cap_eff": 0}))),
        ("pid1-other-uid", edit_json("processes", lambda d: d[0].update(uid=0))),
        ("lock-watcher", edit_world(lambda w: w.lock.update({"users.watcher.uid": 10001}))),
        ("lock-keepalive", edit_world(lambda w: w.lock.update({"users.keepalive.uid": pf.PENDING}))),
    ],
    "sidecar-isolated": [
        ("network", edit_json("sidecar-inspect", lambda d: d[0]["HostConfig"].update(NetworkMode="bridge"))),
        ("pid-shared", edit_json("sidecar-inspect", lambda d: d[0]["HostConfig"].update(PidMode="container:x"))),
        ("tree-writable", edit_json("sidecar-inspect", lambda d: d[0]["Mounts"][0].update(RW=True))),
        ("two-caps", edit_json("sidecar-inspect", lambda d: d[0]["HostConfig"].update(CapAdd=CAP_ADD + ["KILL"]))),
        ("expect-pending", edit_world(lambda w: w.sidecar_expect.update(cap_add=pf.PENDING))),
        ("expect-network", edit_world(lambda w: w.sidecar_expect.update(network_mode="bridge"))),
        ("expect-user", edit_world(lambda w: w.sidecar_expect.update(user="0:0"))),
        ("expect-tree-rw", edit_world(lambda w: w.sidecar_expect["mounts"][0].update(rw=True))),
        ("expect-key-missing", edit_world(lambda w: w.sidecar_expect.pop("security_opt"))),
        ("both-bridge", lambda raw, w: (w.sidecar_expect.update(network_mode="bridge"), edit_json(
            "sidecar-inspect", lambda d: d[0]["HostConfig"].update(NetworkMode="bridge"))(raw, w))),
        ("both-root", lambda raw, w: (w.sidecar_expect.update(user="0:0"), edit_json(
            "sidecar-inspect", lambda d: d[0]["Config"].update(User="0:0"))(raw, w))),
        ("both-privileged", lambda raw, w: (w.sidecar_expect.update(privileged=True), edit_json(
            "sidecar-inspect", lambda d: d[0]["HostConfig"].update(Privileged=True))(raw, w))),
        ("both-host-pid", lambda raw, w: (w.sidecar_expect.update(pid_mode="host"), edit_json(
            "sidecar-inspect", lambda d: d[0]["HostConfig"].update(PidMode="host"))(raw, w))),
        ("both-no-secopt", lambda raw, w: (w.sidecar_expect.update(security_opt=[]), edit_json(
            "sidecar-inspect", lambda d: d[0]["HostConfig"].update(SecurityOpt=[]))(raw, w))),
        ("both-ev-elsewhere", lambda raw, w: (w.sidecar_expect["mounts"][1].update(destination="/srv/x"), edit_json(
            "sidecar-inspect", lambda d: d[0]["Mounts"][1].update(Destination="/srv/x"))(raw, w))),
    ],
    "watcher-started": [
        ("no-health", edit_value("health", lambda v: v.clear())),
        ("stopped", edit_value("health", lambda v: v.append({"kind": "watcher-stop", "at": 2.0, "exit_code": 0}))),
    ],
    "watcher-capability": [
        ("unreadable-row", edit_json("watcher-caps", lambda d: d.append({"pid": 12, "unreadable": "PermissionError"}))),
        ("no-watcher", edit_json("watcher-caps", lambda d: d.pop())),
        ("cap-missing", edit_json("watcher-caps", lambda d: d[1].update(cap_eff=0))),
        ("cap-extra", edit_json("watcher-caps", lambda d: d[1].update(cap_eff=4 | 32))),
        ("root-watcher", edit_json("watcher-caps", lambda d: d[1].update(uid=0))),
    ],
    "consequential-paths-readable": [
        ("unreadable", edit_value("sidecar-begin", lambda v: v.update(unreadable_consequential=["a/b.csv"]))),
        ("not-ok", edit_value("sidecar-begin", lambda v: v.update(ok=False))),
        ("no-field", edit_value("sidecar-begin", lambda v: v.pop("unreadable_consequential"))),
        ("no-reply", lambda raw, w: raw.update({"sidecar-begin": {"error": "no begin reply"}})),
    ],
    "no-container-socket": [
        ("socket", edit_json("sockets", lambda d: d.update(present=["/run/docker.sock"]))),
        ("docker-host", edit_json("sockets", lambda d: d.update(docker_host=True))),
        ("create-env", edit_json("take-inspect", lambda d: d[0]["Config"]["Env"].append("DOCKER_HOST=tcp://x"))),
        ("login-at-create", edit_json("take-inspect", lambda d: d[0]["Config"]["Env"].append(
            "CODEX_API_KEY=FAKEVALUE-0123456789abcdef-PLANTED"))),
    ],
    "egress-allowed-host": [
        ("refused", lambda raw, w: edit_json("egress", lambda d: d["via_proxy"][HOSTS[w.harness]].update(
            status=403))(raw, w)),
        ("unreachable", lambda raw, w: edit_json("egress", lambda d: d["via_proxy"].update(
            {HOSTS[w.harness]: {"error": "ConnectionRefusedError"}}))(raw, w)),
    ],
    "egress-other-host-refused": [
        ("allowed", edit_json("egress", lambda d: d["via_proxy"]["github.com"].update(status=200))),
        ("no-answer", edit_json("egress", lambda d: d["via_proxy"].update({"github.com": {"error": "x"}}))),
    ],
    "egress-direct-refused": [
        ("direct", edit_json("egress", lambda d: d.update(direct={"connected": True}))),
    ],
    "names-do-not-resolve": [
        ("github", edit_json("egress", lambda d: d["resolves"].update({"github.com": True}))),
        ("hf", edit_json("egress", lambda d: d["resolves"].update({"huggingface.co": True}))),
        ("other-vendor", lambda raw, w: edit_json("egress", lambda d: d["resolves"].update(
            {REFUSED_NAMES[w.harness][-1]: True}))(raw, w)),
        ("third-vendor", lambda raw, w: edit_json("egress", lambda d: d["resolves"].update(
            {REFUSED_NAMES[w.harness][-2]: True}))(raw, w)),
        ("name-untried", edit_json("egress", lambda d: d["resolves"].pop("huggingface.co"))),
    ],
    "study-folders-absent": [
        ("present", edit_value("study-folders", lambda v: v.update({"notes-a": True}))),
        ("unlooked", edit_value("study-folders", lambda v: v.pop("notes-b/inner"))),
    ],
    "run-tree-path-neutral": [],   # driven by its own test (the path is the spec's)
}


class MutantCase(unittest.TestCase):
    def assert_green_then_red(self, check, mutants):
        got = _problems(check)
        self.assertEqual(got, [], "the guard is red on the real module")
        for name, ctx in mutants:
            with ctx():
                got = _problems(check)
            print(f"  mutant {name}: {'red' if got else 'GREEN (survived)'}{' - ' + got[0][:100] if got else ''}")
            self.assertNotEqual(got, [], f"mutant {name} survived")


def _problems(fn):
    try:
        return list(fn())
    except Exception as exc:
        return [f"raised {type(exc).__name__}: {exc}"]


def patched(obj, attr, value):
    return lambda: mock.patch.object(obj, attr, value)


class TestProcessGuard(unittest.TestCase):
    def test_guard_is_armed(self):
        with self.assertRaises(ProcessGuardTripped):
            subprocess.run(["true"])
        with self.assertRaises(ProcessGuardTripped):
            os.kill(0, 0)

    def test_module_is_this_rounds(self):
        self.assertTrue(os.path.abspath(pf.__file__).startswith(os.path.join(HERE, "box") + os.sep))


class TestShape(MutantCase):
    def check_shape(self):
        out = []
        if pf.PREFLIGHT_CHECKS != tuple(BREAKS):
            out.append("PREFLIGHT_CHECKS is not the tested ordered tuple")
        if set(pf.CHECKS) != set(pf.PREFLIGHT_CHECKS):
            out.append("CHECKS does not hold exactly one function per check")
        if pf.WATCHER_UID != 10002 or pf.WATCHER_CAP_EFF != 4:
            out.append("WATCHER_UID or the capability bit drifted")
        if pf.LOCK_KEYS != ("image_id", "harness.version", "users.agent.uid", "users.watcher.uid",
                            "users.keepalive.uid"):
            out.append("LOCK_KEYS drifted from w4a's schema paths")
        if pf.UNREADABLE_CONSEQUENTIAL_KEY != "unreadable_consequential" \
                or pf.UNREADABLE_CONSEQUENTIAL_ROW != "unreadable-consequential-path":
            out.append("the C3 names drifted")
        if pf.SIDECAR_EVIDENCE_MOUNT != "/srv/ev" or pf.BLOCKED_NAMES != ("github.com", "huggingface.co"):
            out.append("the evidence mount or the blocked names drifted")
        if pf.AGENT_UID != 10001 or pf.KEEPALIVE_UID != 10003:
            out.append("the uids drifted")
        return out

    def test_shape(self):
        self.assert_green_then_red(self.check_shape, [
            ("check-dropped", patched(pf, "PREFLIGHT_CHECKS", pf.PREFLIGHT_CHECKS[:-1])),
            ("check-reordered", patched(pf, "PREFLIGHT_CHECKS", pf.PREFLIGHT_CHECKS[::-1])),
            ("watcher-uid", patched(pf, "WATCHER_UID", 10001)),
            ("cap-bit", patched(pf, "WATCHER_CAP_EFF", 8)),
            ("lock-keys", patched(pf, "LOCK_KEYS", pf.LOCK_KEYS[:-1])),
            ("c3-key", patched(pf, "UNREADABLE_CONSEQUENTIAL_KEY", "unreadable")),
            ("c3-row", patched(pf, "UNREADABLE_CONSEQUENTIAL_ROW", "x")),
            ("ev-mount", patched(pf, "SIDECAR_EVIDENCE_MOUNT", "/srv/e")),
            ("blocked", patched(pf, "BLOCKED_NAMES", ("github.com",))),
            ("agent-uid", patched(pf, "AGENT_UID", 0)),
        ])


class TestEvaluate(MutantCase):
    def test_all_green_every_arm(self):
        for h in ARMS:
            w = World(h)
            with filled():
                rec = w.evaluate()
            self.assertEqual(failing(rec), [], h)
            self.assertTrue(rec["ok"])
            self.assertEqual([c["id"] for c in rec["checks"]], list(pf.PREFLIGHT_CHECKS))

    def undetected(self, harness):
        """Every break that leaves its own check green (the guard's problems)."""
        out = []
        for cid, breaks in BREAKS.items():
            for name, brk in breaks:
                w = World(harness)
                raw = w.raw()
                brk(raw, w)
                with filled():
                    rec = w.evaluate(raw)
                if cid not in failing(rec) or rec["ok"]:
                    out.append(f"{cid}/{name} was not caught")
        return out

    def test_each_check_catches_its_breaks(self):
        n = sum(len(b) for b in BREAKS.values())
        print(f"  {n} breaks over {len(BREAKS)} checks, per arm")
        for h in ARMS:
            self.assertEqual(self.undetected(h), [], h)

    def test_each_check_mutant_red(self):
        """Replacing a check with one that always passes leaves its breaks uncaught: red."""
        muts = [(f"{cid}-always-passes", (lambda c: lambda: mock.patch.dict(pf.CHECKS, {c: lambda *a: "passes"}))(cid))
                for cid, b in BREAKS.items() if b]
        self.assert_green_then_red(lambda: self.undetected(rt.CLAUDE_CODE), muts)

    def missing_or_failed(self):
        """Every probe missing, or failed to run, fails at least one check."""
        out = []
        w = World()
        base = w.raw()
        for pid in list(pf.PROBE_IDS) + ["sidecar-begin"]:
            for how in ("missing", "error", "exit"):
                raw = copy.deepcopy(base)
                if how == "missing":
                    raw.pop(pid)
                elif how == "error":
                    raw[pid] = {"error": "TimeoutError"}
                elif "returncode" in raw[pid]:
                    raw[pid]["returncode"] = 1
                else:
                    continue
                with filled():
                    rec = w.evaluate(raw)
                if rec["ok"] or not failing(rec):
                    out.append(f"probe {pid} {how} passed")
        return out

    def test_missing_probe_fails(self):
        def assume_missing(fn):
            def wrapped(*a):
                try:
                    return fn(*a)
                except pf._Fail as e:
                    if "missing" in str(e) or "failed" in str(e) or "exited" in str(e) or "no " in str(e):
                        return "assumed"
                    raise
            return wrapped
        self.assert_green_then_red(self.missing_or_failed, [
            ("missing-assumed-to-pass", lambda: mock.patch.dict(pf.CHECKS, {
                k: assume_missing(f) for k, f in pf.CHECKS.items()})),
            ("crash-passes", patched(pf, "evaluate", lambda raw, **k: {"ok": True, "checks": [], "recorded": {}})),
        ])

    def test_run_records_failures(self):
        w = World()
        probes = w.probes()
        script = w.script()
        script[0] = (script[0][0], TimeoutError("slow"))
        fake = FakeRuntime(script)
        with mock.patch.object(pf, "_read_health", lambda p: (_ for _ in ()).throw(OSError("gone"))):
            raw = pf.run(fake, probes, begin_reply=None, caller_env={"PATH": "/bin", "SECRET_X": "1"})
        self.assertEqual(raw["identity"], {"error": "TimeoutError"})
        self.assertEqual(raw["health"], {"error": "OSError"})
        self.assertEqual(raw["sidecar-begin"], {"error": "no begin reply"})
        self.assertEqual(fake.unexpected, [])
        self.assertTrue(all(env == {"PATH": "/bin"} for _, env in fake.calls))   # built from nothing
        with filled():
            rec = w.evaluate(raw)
        self.assertIn("agent-non-root", failing(rec))
        self.assertIn("watcher-started", failing(rec))
        self.assertIn("consequential-paths-readable", failing(rec))

    def test_run_tree_path_neutral(self):
        def check():
            out = []
            for word in (ROUND3_WORDS[0], ROUND3_WORDS[-1].upper(), "SIDECAR", "probe"):
                w = World()
                tree = os.path.join(w.tmp, f"x-{word}-y")
                os.makedirs(tree)
                w.spec = rt.TakeSpec(**dict(w.spec.__dict__, run_tree=tree))
                with filled():
                    rec = pf.evaluate(w.raw(), spec=w.spec, lock=w.lock, sidecar_expect=w.sidecar_expect,
                                      harness=w.harness, hosts=HOSTS)
                if "run-tree-path-neutral" not in failing(rec):
                    out.append(f"a run tree path carrying {word} passed")
            w = World()
            tree = os.path.join(w.tmp, "sidecarzz-x")   # word-bounded: a longer word is not a hit
            if pf.leak_hits(tree, ["sidecar"]):
                out.append("leak_hits is not word-bounded")
            return out
        self.assert_green_then_red(check, [
            ("no-leak-check", lambda: mock.patch.dict(pf.CHECKS, {"run-tree-path-neutral": lambda *a: "ok"})),
            ("substring-hits", patched(pf, "leak_hits", lambda t, ws: [w for w in ws if w.lower() in t.lower()])),
        ])


class TestPending(MutantCase):
    EXPECT = {"VERSION_PATTERNS", "STUDY_PATHS", "LEAK_WORDS"}
    EXPECT_RT = {"FALLBACK_ENV", "VENDOR_BILLING_ROUTE_VARIABLES", "TOP_FORMAT", "INSPECT_STATUS",
                 "TakeSpec.resources"}
    GATED = {"image-matches-lock", "harness-version-matches-lock", "take-inspect-matches-spec",
             "sidecar-isolated", "study-folders-absent", "run-tree-path-neutral", "no-container-socket"}

    def check(self):
        out = []
        if set(pf.pending()) != self.EXPECT:
            out.append(f"preflight.pending() = {sorted(pf.pending())}")
        if set(rt.pending()) != self.EXPECT_RT:
            out.append(f"run_take.pending() = {sorted(rt.pending())}")
        w = World()
        rec = w.evaluate()   # nothing filled: every gated check fails, every other passes
        if set(failing(rec)) != self.GATED:
            out.append(f"unfilled failing set {sorted(failing(rec))}")
        if rec["ok"]:
            out.append("an unfilled preflight passed")
        if rec["recorded"]["token_visible_to_children"] != pf.PENDING:
            out.append("token visibility was judged, not recorded PENDING")
        g = World(rt.GEMINI)
        with filled():
            if g.evaluate()["recorded"]["google_project_tier"] != pf.PENDING:
                out.append("the Google tier was not recorded PENDING")
        return out

    def test_pending(self):
        self.assert_green_then_red(self.check, [
            ("never-pending", patched(rt, "_is_pending", lambda v: False)),
            ("version-filled", patched(pf, "VERSION_PATTERNS", {h: r"(.*)" for h in ARMS})),
            ("study-empty", patched(pf, "STUDY_PATHS", ())),
            ("leaks-empty", patched(pf, "LEAK_WORDS", ())),
            ("inspect-confirmed", patched(rt, "INSPECT_STATUS", "confirmed")),
        ])

    def test_no_parameter_overrides_a_pending_constant(self):
        def overriding(raw, *, study_paths=None):
            return None
        overriding.__module__ = pf.__name__
        self.assert_green_then_red(self.check_no_override, [
            ("override-parameter", lambda: mock.patch.object(pf, "evaluate_with", overriding, create=True)),
        ])

    def check_no_override(self):
        names = {n.lower() for n in self.EXPECT | (self.EXPECT_RT - {"TakeSpec.resources"})}
        names |= {"pattern", "patterns", "version_pattern", "study_paths", "leak_words", "inspect_status",
                  "fallback_env", "top_format", "billing_route"}
        found = []
        for mod in (pf, rt):
            for name, fn in vars(mod).items():
                if callable(fn) and not name.startswith("_") and getattr(fn, "__module__", "") == mod.__name__:
                    try:
                        params = pyinspect.signature(fn).parameters
                    except (TypeError, ValueError):
                        continue
                    found += [f"{mod.__name__}.{name}({p})" for p in params if p.lower() in names]
        return found


class TestExpectedInspect(MutantCase):
    def check(self):
        """The expected facts derive from the same spec as the create argv (interface 13)."""
        w = World()
        s = w.spec
        argv = rt.create_argv(s)
        exp = pf.expected_take_inspect(s)
        val = lambda flag: argv[argv.index(flag) + 1]  # noqa: E731
        derived = {"image": argv[-3], "user": val("--user"), "network_mode": val("--network"),
                   "pids_limit": int(val("--pids-limit")), "memory": int(val("--memory")),
                   "memory_reservation": int(val("--memory-reservation")),
                   "nano_cpus": int(float(val("--cpus")) * 1e9), "cap_drop": [val("--cap-drop")],
                   "security_opt": [val("--security-opt")], "working_dir": val("--workdir"), "cmd": argv[-2:]}
        out = [f"{k}: {exp[k]!r} != {v!r}" for k, v in derived.items() if exp[k] != v]
        mounts = sorted(({"type": "bind", "source": dict(p.split("=") for p in m.split(","))["source"],
                          "destination": dict(p.split("=") for p in m.split(","))["target"], "rw": True}
                         for m in (argv[i + 1] for i, a in enumerate(argv) if a == "--mount")),
                        key=lambda m: m["destination"])
        if mounts != exp["mounts"]:
            out.append("mounts differ")
        if exp["cap_add"] != [] or exp["privileged"] is not False or exp["devices"] != [] or exp["pid_mode"] != "":
            out.append("an absent fact is expected present")
        with filled():
            raw = w.raw()
            if pf.inspect_mismatches(json.loads(raw["take-inspect"]["stdout"])[0], exp, kind="take"):
                out.append("the passing inspect mismatches")
        return out

    def test_bound_to_create(self):
        orig = pf.expected_take_inspect
        self.assert_green_then_red(self.check, [
            ("memory-off", patched(pf, "expected_take_inspect", lambda s: dict(orig(s), memory=s.memory_reservation))),
            ("cap-add-allowed", patched(pf, "expected_take_inspect", lambda s: dict(orig(s), cap_add=["ALL"]))),
            ("user-agent", patched(pf, "expected_take_inspect", lambda s: dict(orig(s), user=rt.AGENT_USER))),
            ("one-mount", patched(pf, "expected_take_inspect", lambda s: dict(orig(s), mounts=orig(s)["mounts"][:1]))),
        ])

    def test_mismatch_refuses_pending_and_wrong_keys(self):
        w = World()
        obj = json.loads(w.raw()["take-inspect"]["stdout"])[0]
        exp = pf.expected_take_inspect(w.spec)
        self.assertTrue(pf.inspect_mismatches(obj, exp, kind="take"))         # spellings PENDING
        with filled():
            self.assertEqual(pf.inspect_mismatches(obj, exp, kind="take"), [])
            self.assertTrue(pf.inspect_mismatches(obj, dict(exp, memory=pf.PENDING), kind="take"))
            self.assertTrue(pf.inspect_mismatches(obj, {k: exp[k] for k in list(exp)[1:]}, kind="take"))
            self.assertTrue(pf.inspect_mismatches(obj, exp, kind="proxy"))


class TestPrograms(MutantCase):
    def check(self):
        """Every program is read from the argv each probe actually builds, never from a table beside it."""
        out = []
        built = {}
        for h in ARMS:
            for p in World(h).probes():
                if p.argv is not None and "-c" in p.argv:
                    built[p.id] = p.argv[list(p.argv).index("-c") + 1]
        if len(built) != 7:
            out.append(f"{len(built)} probes run a program, not 7")
        for name, src in built.items():
            try:
                ast.parse(src, feature_version=(3, 11))
            except SyntaxError as e:
                out.append(f"{name}: not 3.11 ({e.msg})")
            hits = [w for w in LEAK_WORDS if re.search(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])",
                                                       src, re.IGNORECASE)]
            if hits:
                out.append(f"{name}: carries {hits}")
            if "open(" in src and re.search(r"open\((?!\"/proc|sys\.argv\[1\])", src):
                out.append(f"{name}: opens something other than /proc or the cgroup root")
        w = World()
        for p in w.probes():
            if p.argv is None:
                continue
            if any(w.spec.run_tree in a for a in p.argv):
                out.append(f"probe {p.id} names the run tree")
            if p.id != "watcher-caps":
                if list(p.argv[:4]) != ["docker", "exec", "--user", rt.AGENT_USER] and p.argv[1] != "container":
                    out.append(f"probe {p.id} does not run as the agent")
                if "exec" in p.argv[:2] and list(p.argv[4:6]) != ["--workdir", "/"]:
                    out.append(f"probe {p.id} does not run with workdir /")
            if "-c" in p.argv and list(p.argv[p.argv.index("python3"):p.argv.index("-c")]) != ["python3", "-I", "-B"]:
                out.append(f"probe {p.id} is not python3 -I -B -c")
            if p.id == "harness-version":
                pairs = [p.argv[i + 1] for i, a in enumerate(p.argv) if a == "-e"]
                if pairs != [f"{CONFIG_HOME[w.harness]}=/opt/cfg"]:
                    out.append(f"the version probe carries {pairs}, not its config home alone")
            if p.id == "egress":
                with mock.patch.object(rt, "PROXY_URL", "http://proxy:3129"):
                    eg = [q for q in w.probes() if q.id == "egress"][0].argv
                if "3129" not in eg:
                    out.append("the egress probe's port is not derived from PROXY_URL")
            agent_visible = [a for a in p.argv if a != w.ev]
            for a in agent_visible:
                if [x for x in LEAK_WORDS if re.search(r"(?<![A-Za-z0-9])" + re.escape(x) + r"(?![A-Za-z0-9])", a,
                                                       re.IGNORECASE)]:
                    out.append(f"probe {p.id} argv carries a leak word")
        return out

    def test_programs(self):
        self.assert_green_then_red(self.check, [
            ("py312-feature", patched(pf, "IDENTITY_PROGRAM", "type X = int\n")),
            ("study-word", patched(pf, "IDENTITY_PROGRAM", pf.IDENTITY_PROGRAM + "# probe\n")),
            ("reads-tree", patched(pf, "CGROUP_PROGRAM", 'open("tree/x")\n')),
            ("version-without-config-home", patched(pf, "_config_home_values", lambda h: {})),
            ("port-typed", patched(pf, "_proxy_port", lambda: "3128")),
            ("tree-in-argv", patched(pf, "probes", lambda spec, **k: tuple(
                pf.Probe(p.id, p.argv + (spec.run_tree,) if p.argv else None, p.read) for p in ORIG_PROBES(spec, **k)))),
            ("no-isolation", patched(pf, "_py", lambda prog, *a: ["python3", "-c", prog, *a])),
            ("agent-root", patched(rt, "AGENT_USER", "0:0")),
        ])


class TestProcessesProgram(MutantCase):
    def check(self):
        import builtins
        import contextlib as cl
        import io
        src = [q for q in World().probes() if q.id == "processes"][0].argv
        src = src[list(src).index("-c") + 1]
        status = {"/proc/1/status": "Name:\tsleep\nUid:\t10003\t10003\t10003\t10003\nCapEff:\t0\n"}
        real_open = builtins.open

        def fake_open(path, *a, **k):
            if path in status:
                return io.StringIO(status[path])
            if str(path).startswith("/proc/"):
                raise PermissionError(path)
            return real_open(path, *a, **k)
        buf = io.StringIO()
        with mock.patch.object(os, "listdir", lambda p: ["1", "7", "self", "99"]), \
                mock.patch.object(os, "getpid", lambda: 99), mock.patch.object(builtins, "open", fake_open), \
                cl.redirect_stdout(buf):
            exec(compile(src, "<program>", "exec"), {"__name__": "__main__"})
        rows = json.loads(buf.getvalue())
        out = []
        if [r.get("pid") for r in rows] != [1, 7]:
            out.append(f"rows {rows}")
        elif rows[1].get("unreadable") != "PermissionError" or rows[0].get("uid") != 10003:
            out.append(f"the unreadable row is not recorded: {rows}")
        return out

    def test_processes_program(self):
        skipping = pf.PROCESSES_PROGRAM.replace('rows.append({"pid": int(name), "unreadable": type(e).__name__})',
                                                "continue")
        self.assert_green_then_red(self.check, [
            ("skips-unreadable", patched(pf, "PROCESSES_PROGRAM", skipping)),
        ])

    def test_literal_refused_names(self):
        self.assert_green_then_red(lambda: [h for h in ARMS if pf.refused_names(h, HOSTS) != REFUSED_NAMES[h]], [
            ("other-vendors-dropped", patched(pf, "BLOCKED_NAMES", ("github.com", "huggingface.co", "x.example"))),
        ])


class TestRecordAndPostflight(MutantCase):
    def test_write_beside_evidence(self):
        w = World()
        with filled():
            rec = w.evaluate()
        rec_dir = os.path.dirname(w.ev)
        path = pf.write(rec, os.path.join(rec_dir, "preflight.json"))
        with open(path) as fh:
            self.assertEqual(json.load(fh), rec)
        for bad in (os.path.join(w.ev, "preflight.json"), path, os.path.join(rec_dir, "pre.json")):
            with self.assertRaises(rt.Refused):
                pf.write(rec, bad)
        evdir = os.path.join(w.tmp, "evidence")
        os.makedirs(evdir)
        with self.assertRaises(rt.Refused):
            pf.write(rec, os.path.join(evdir, "preflight.json"))
        with self.assertRaises(rt.Refused):
            pf.write(dict(rec, ok=True, checks=[dict(c, ok=False) for c in rec["checks"]]),
                     os.path.join(w.tmp, "preflight.json"))

    def check_postflight(self):
        out = []
        for h, name in ((rt.CODEX, "auth.json"), (rt.CLAUDE_CODE, ".credentials.json"),
                        (rt.GEMINI, "oauth_creds.json"), (rt.GEMINI, "google_accounts.json"),
                        (rt.CODEX, "token-cache")):
            d = tempfile.mkdtemp(prefix="w-")
            os.makedirs(os.path.join(d, "sessions"))
            open(os.path.join(d, "config.toml"), "w").close()
            if pf.postflight(d, h)["ok"] is not True:
                out.append(f"{h}: a clean folder failed")
            open(os.path.join(d, "sessions", name), "w").close()
            r = pf.postflight(d, h)
            if r["ok"] or f"sessions/{name}" not in r["recorded"]["listing"]:
                out.append(f"{h}: {name} passed")
        d = tempfile.mkdtemp(prefix="w-")
        locked = os.path.join(d, "locked")
        os.makedirs(locked)
        os.chmod(locked, 0)
        try:
            if pf.postflight(d, rt.CODEX)["ok"]:
                out.append("an unreadable folder passed")
        finally:
            os.chmod(locked, 0o700)
        if pf.postflight(os.path.join(d, "nope"), rt.CODEX)["ok"]:
            out.append("a missing folder passed")
        for h in rt.LOGIN_VARIABLE:
            if not all(src for _, src in pf.CREDENTIAL_FILES[h]):
                out.append(f"{h}: a credential name without its source")
        if {h: [n for n, _ in v] for h, v in pf.CREDENTIAL_FILES.items()} != {
                rt.CLAUDE_CODE: [], rt.CODEX: ["auth.json"], rt.GEMINI: []}:
            out.append("an unsourced credential name is used as a real value")
        recalled = pf.RECORDED_PENDING.get("credential_file_names", "")
        for n in (".credentials.json", "oauth_creds.json", "google_accounts.json"):
            if n not in recalled:
                out.append(f"{n} is not recorded pending its walk")
            if not pf.CREDENTIAL_LIKE.search(n):
                out.append(f"the backstop does not catch {n}")
        return out

    def test_postflight(self):
        self.assert_green_then_red(self.check_postflight, [
            ("no-names", patched(pf, "CREDENTIAL_FILES", {h: () for h in rt.LOGIN_VARIABLE})),
            ("no-pattern", patched(pf, "CREDENTIAL_LIKE", re.compile(r"(?!x)x"))),
        ])


if __name__ == "__main__":
    unittest.main(verbosity=2)
