#!/usr/bin/env python3
"""box/preflight.py: every check of PREFLIGHT_CHECKS green on a passing world and red on its own break, every
probe's absence or failure read as a failed check, the PENDING refusals, the programs' Python floor and neutrality,
the record's place beside the evidence folder, and the after-take credential check.

A FakeRuntime answers the probes; no test reaches a real process (the guard below is armed after the one leak-word
read, interface 16). Each guard is also run against in-memory mutants, printed with their red results.

Lane w6a (CP2-preflight-1 to -5, glitch-1b's rulings of 10 Oct): the lock reaches preflight only through
`load_take_lock` (the real image_lock.load and require_ready, then the harness's own take image), evaluate takes a
required `evidence_dir` and binds the sidecar's evidence mount source to it, and `collect_and_evaluate` composes the
probes on `Launched.spec`. Lock files are synthetic copies in a temporary stand-in for box/ (image_lock.BOX_DIR
patched, test_image's convention); a committed lock is only ever read. Six witnesses are whole-file mutants of
box/preflight.py compiled in memory (never written to disk); each must go red by its bound check's own assertion.
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
import types
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
    """Round 3's pre-registration key leak_words, that key alone, read once (interface 16). Never committed.
    The same one read also keeps run_location.excluded_from_the_run_tree's paths, in order, as ROUND3_EXCLUDED (the
    CP5 ruling binds preflight.STUDY_PATHS to them; this stays the module's one process site)."""
    global ROUND3_EXCLUDED
    shown = subprocess.run(["git", "-C", REPO, "show", f"{ROUND3}:evals/gap-study-3/prereg.json"],
                           capture_output=True, check=True)
    doc = json.loads(shown.stdout)
    ROUND3_EXCLUDED = tuple(e["path"] for e in doc["run_location"]["excluded_from_the_run_tree"])
    return tuple(doc["leak_words"])


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
_ORIGINALS = [(_mod, _name, getattr(_mod, _name)) for _mod, _name in GUARDED]
_TRIPS = {(id(_mod), _name): _tripwire(f"{_mod.__name__}.{_name}") for _mod, _name in GUARDED}


def _arm_guard():
    for mod, name in GUARDED:
        setattr(mod, name, _TRIPS[(id(mod), name)])


def _disarm_guard():
    for mod, name, original in _ORIGINALS:
        setattr(mod, name, original)


def _patched_now() -> list:
    """The guarded names that hold this module's tripwire right now."""
    return [f"{mod.__name__}.{name}" for mod, name in GUARDED if getattr(mod, name) is _TRIPS[(id(mod), name)]]


def setUpModule():
    """Arm the guard for every test of this module, never at import: test_round4 imports every test module in one
    process, and an import-time guard would trip in the others (the wave 4 merge's fix)."""
    _arm_guard()
    _module_set_up_extra()


def tearDownModule():
    _module_tear_down_extra()
    _disarm_guard()


def _module_set_up_extra():
    pass


def _module_tear_down_extra():
    pass

from box import image_lock as il  # noqa: E402
from box import preflight as pf  # noqa: E402
from box import run_take as rt  # noqa: E402

ORIG_PROBES = pf.probes
ID = {k: (c * 64) for k, c in (("net", "a"), ("side", "c"), ("take", "d"))}
IMAGE = "sha256:" + "f" * 64
MANIFEST = "sha256:" + "c" * 64           # the take image's platform manifest (lock-writer ruling (a), 14 Oct)
SIDE_MANIFEST = "sha256:" + "5" * 64      # the sidecar image's platform manifest (LW-7): never the take's
EGRESS_IMAGE_ID = "sha256:" + "6" * 64    # the egress proxy's image (O-1): its own id, never the take's
EGRESS_MANIFEST = "sha256:" + "7" * 64    # the egress image's platform manifest (O-1)
PROXY_ID = "b" * 64
ARMS = (rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI)
HOSTS = {rt.CLAUDE_CODE: "api.anthropic.com", rt.CODEX: "api.openai.com", rt.GEMINI: "generativelanguage.googleapis.com"}
VERSION_OUT = {rt.CLAUDE_CODE: ("2.9.1 (Claude Code)\n", r"([0-9.]+) \(Claude Code\)", "2.9.1"),
               rt.CODEX: ("codex-cli 0.160.1\n", r"codex-cli ([0-9.]+)", "0.160.1"),
               rt.GEMINI: ("0.63.0\n", r"([0-9.]+)", "0.63.0")}
STUDY = pf.STUDY_PATHS   # the ruled list (TestCP5Values binds it); the fixture answers every path absent
REFUSED_NAMES = {
    rt.CLAUDE_CODE: ["github.com", "huggingface.co", "api.openai.com", "generativelanguage.googleapis.com"],
    rt.CODEX: ["github.com", "huggingface.co", "api.anthropic.com", "generativelanguage.googleapis.com"],
    rt.GEMINI: ["github.com", "huggingface.co", "api.anthropic.com", "api.openai.com"],
}
CONFIG_HOME = {rt.CLAUDE_CODE: "CLAUDE_CONFIG_DIR", rt.CODEX: "CODEX_HOME", rt.GEMINI: "GEMINI_CLI_HOME"}
CAP_ADD = ["CAP_DAC_READ_SEARCH", "CAP_SETGID", "CAP_SETPCAP", "CAP_SETUID"]


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
def filled(harness=rt.CLAUDE_CODE, mod=None):
    """Every PENDING constant evaluate needs, filled in memory only (interface 15), on preflight or a witness copy."""
    mod = pf if mod is None else mod
    with mock.patch.object(rt, "INSPECT_STATUS", "confirmed-in-test"), \
            mock.patch.object(mod, "VERSION_PATTERNS", {h: VERSION_OUT[h][1] for h in ARMS}), \
            mock.patch.object(mod, "STUDY_PATHS", STUDY), \
            mock.patch.object(mod, "LEAK_WORDS", LEAK_WORDS):
        yield


class World:
    """A passing take: spec, lock, sidecar expectation and the raw records a FakeRuntime gave run().

    The run tree and the config folder are the test's own fixed fake paths, never under the host's temp root: their
    path is agent-visible and judged for leak words, and a host's temp root may carry one (athena's did). Only the
    evidence folder is a real temp folder, for the host-side health read; its path is never judged."""
    FAKE_TREE = True
    FAKE_ROOT = "/srv/w0/t1"

    def __init__(self, harness=rt.CLAUDE_CODE):
        self.tmp = tempfile.mkdtemp(prefix="w-")
        self.harness = harness
        root = self.FAKE_ROOT if self.FAKE_TREE else self.tmp
        self.tree = os.path.join(root, "tree")
        self.cfg = os.path.join(root, "cfg")
        self.ev = os.path.join(self.tmp, "rec", "ev")
        os.makedirs(self.ev)
        with open(os.path.join(self.ev, "health.jsonl"), "w") as fh:
            fh.write(json.dumps({"kind": "watcher-start", "at": 1.0}) + "\n")
        self.spec = rt.TakeSpec(image=IMAGE, run_tree=self.tree, config_dir=self.cfg, network=ID["net"],
                                memory_reservation=512 * 2 ** 20, memory=3 * 512 * 2 ** 20, cpus="2", pids_limit=256)
        self.lock = {"image_id": IMAGE, "harness.version": VERSION_OUT[harness][2], "users.agent.uid": 10001,
                     "users.watcher.uid": 10002, "users.keepalive.uid": 10003, "manifest_digest": MANIFEST}
        self.sidecar_lock = {"image_id": IMAGE, "manifest_digest": SIDE_MANIFEST}
        self.egress_lock = {"image_id": EGRESS_IMAGE_ID, "manifest_digest": EGRESS_MANIFEST}
        self.proxy_image = EGRESS_IMAGE_ID
        self.sidecar_expect = {
            "user": "0:0", "network_mode": "none", "cap_drop": ["ALL"], "cap_add": list(CAP_ADD),
            "security_opt": ["no-new-privileges"], "privileged": False, "pid_mode": "",
            "mounts": [{"source": self.tree, "destination": self.tree, "rw": False},
                       {"source": self.ev, "destination": "/srv/ev", "rw": True}]}
        self.sidecar_expect.update(image=IMAGE, entrypoint=[],
                                   cmd=[*pf.sidecar_contract.WATCHER_LAUNCHER, *pf.sidecar_contract.INTERPRETER,
                                        pf.sidecar_contract.PROGRAM, "serve", "--run-tree", self.tree,
                                        "--evidence", "/srv/ev", "--watch", "plan"])
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
                               "MemoryReservation": s.memory_reservation, "NanoCpus": 2_000_000_000,
                               "ReadonlyRootfs": True, "Tmpfs": {"/tmp": "rw,exec,nosuid,nodev,mode=1777", "/var/tmp": "rw,exec,nosuid,nodev,mode=1777"}},
                "Mounts": [{"Type": "bind", "Source": s.run_tree, "Destination": s.run_tree, "RW": True},
                           {"Type": "bind", "Source": s.config_dir, "Destination": "/opt/cfg", "RW": True}],
                # PF1-L3 (m9): the internal network's gateway, which the direct-egress probe must have tried
                "NetworkSettings": {"Networks": {"n": {"Gateway": GATEWAY}}}}],
            "take-image-manifest": json.dumps(MANIFEST) + "\n",
            "harness-version": VERSION_OUT[harness][0],
            "cgroup": {"cpu.max": "200000 100000", "memory.max": str(s.memory),
                       "memory.low": str(s.memory_reservation), "pids.max": "256"},
            "listing": {"/srv/ev": "FileNotFoundError", self.ev: "FileNotFoundError"},
            "processes": [{"pid": 1, "uid": 10003, "name": "sleep", "cap_eff": 0}],
            "sidecar-inspect": [{
                "Image": IMAGE, "Config": {"User": "0:0", "Entrypoint": [], "Cmd": self.sidecar_expect["cmd"]},
                "HostConfig": {"NetworkMode": "none", "CapDrop": ["ALL"], "CapAdd": list(CAP_ADD),
                               "SecurityOpt": ["no-new-privileges"], "Privileged": False, "PidMode": ""},
                "Mounts": [{"Type": "bind", "Source": self.tree, "Destination": self.tree, "RW": False},
                           {"Type": "bind", "Source": self.ev, "Destination": "/srv/ev", "RW": True}]}],
            "sidecar-image-manifest": json.dumps(SIDE_MANIFEST) + "\n",
            "proxy-inspect": [{"Image": EGRESS_IMAGE_ID, "Config": {"Image": EGRESS_IMAGE_ID}}],
            "egress-image-manifest": json.dumps(EGRESS_MANIFEST) + "\n",
            "watcher-caps": [{"pid": 1, "uid": 10002, "name": "python3", "cap_eff": 0},
                             {"pid": 9, "uid": 10002, "name": "inotifywait", "cap_eff": 4}],
            "sockets": {"present": [], "docker_host": False},
            "egress": {"via_proxy": {HOSTS[harness]: {"status": 200}, "github.com": {"status": 403}},
                       "direct": {"connected": False, "error": "gaierror"},
                       "resolves": {n: False for n in REFUSED_NAMES[harness]}},
            # Lane pf1-gateway: the host-side record of the take's network, `docker network inspect` of spec.network;
            # its IPAM gateway is the world's gateway (an --internal network's take inspect may name none)
            "take-network-inspect": [{"Name": "n", "Id": ID["net"], "Internal": True,
                                      "IPAM": {"Driver": "default", "Options": {},
                                               "Config": [{"Subnet": "172.30.0.0/16", "Gateway": GATEWAY}]}}],
            # PF1-L3 (m9): the direct-egress probe's record, nothing connected
            "direct-egress": {
                "routes": [{"iface": "eth0", "destination": "172.30.0.0", "gateway": "0.0.0.0",
                            "mask": "255.255.0.0"}],
                "gateway_candidates": [GATEWAY],
                "gateway": {GATEWAY: {str(port): {"address": f"{GATEWAY}:{port}", "connected": False,
                                                  "error": "TimeoutError"} for port in pf.GATEWAY_PORTS}},
                "targets": {label: {"address": f"{a}:{port}", "connected": False, "error": "OSError"}
                            for label, (a, port) in pf.DIRECT_TARGETS.items()}},
        }
        for row in self.answers["watcher-caps"]:
            row.update(uids=[10002] * 4, gids=[10002] * 4, groups=[], no_new_privs=1,
                       cap_eff=4, cap_prm=4, cap_inh=4, cap_bnd=4, cap_amb=4)

    def probes(self):
        return pf.probes(self.spec, take_id=ID["take"], sidecar_id=ID["side"], harness=self.harness, hosts=HOSTS,
                         evidence_dir=self.ev, sidecar_image=self.sidecar_expect["image"], proxy_id=PROXY_ID,
                         proxy_image=self.proxy_image)

    def script(self):
        out = []
        for p in self.probes():
            if p.argv is not None:
                out.append((list(p.argv[:2]), ok(self.answers[p.id])))
        return out

    def raw(self):
        fake = FakeRuntime(self.script())
        # The host-side study-folder read looks for the filled list in the fake run tree: answered by the fixture
        # (absent), never by whatever the host holds at that path.
        with mock.patch.object(pf, "STUDY_PATHS", STUDY), mock.patch.object(pf.os.path, "lexists", lambda p: False):
            raw = pf.run(fake, self.probes(), begin_reply=self.begin, caller_env={"PATH": "/bin"})
        assert not fake.unexpected and not fake.script, (fake.unexpected, fake.script)
        return raw

    def evaluate(self, raw=None, **kw):
        args = dict(spec=self.spec, lock=self.lock, sidecar_expect=self.sidecar_expect, harness=self.harness,
                    hosts=HOSTS, evidence_dir=self.ev, sidecar_lock=self.sidecar_lock, egress_lock=self.egress_lock)
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


def set_value(pid, value):
    def apply(raw, w):
        raw[pid]["value"] = value
    return apply


def edit_world(fn):
    def apply(raw, w):
        fn(w)
    return apply


# Every check's own breaks: each must turn that check (and the record) red.
GATEWAY = "172.30.0.1"     # PF1-L3 (m9): the world's internal-network gateway


def _set_connected(label):
    return edit_json("direct-egress", lambda d: d["targets"][label].update(connected=True))


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
        # lock-writer ruling (a): the platform manifest is the content identity
        ("manifest-other", lambda raw, w: raw["take-image-manifest"].update(stdout=json.dumps("sha256:" + "0" * 64))),
        ("manifest-lock-other", edit_world(lambda w: w.lock.update(manifest_digest="sha256:" + "1" * 64))),
        ("manifest-lock-pending", edit_world(lambda w: w.lock.update(manifest_digest=pf.PENDING))),
        ("manifest-not-json", lambda raw, w: raw["take-image-manifest"].update(stdout="sha256:" + "c" * 64)),
        ("manifest-failed", lambda raw, w: raw["take-image-manifest"].update(returncode=1)),
        # LW-7: the sidecar's image, by its own lock's id and platform manifest
        ("sidecar-manifest-other", lambda raw, w: raw["sidecar-image-manifest"].update(stdout=json.dumps(MANIFEST))),
        ("sidecar-manifest-not-json", lambda raw, w: raw["sidecar-image-manifest"].update(stdout=SIDE_MANIFEST)),
        ("sidecar-manifest-failed", lambda raw, w: raw["sidecar-image-manifest"].update(returncode=1)),
        ("sidecar-lock-manifest-other", edit_world(lambda w: w.sidecar_lock.update(manifest_digest=MANIFEST))),
        ("sidecar-lock-manifest-pending", edit_world(lambda w: w.sidecar_lock.update(manifest_digest=pf.PENDING))),
        ("sidecar-lock-image-other", edit_world(lambda w: w.sidecar_lock.update(image_id="sha256:" + "1" * 64))),
        ("sidecar-lock-image-pending", edit_world(lambda w: w.sidecar_lock.update(image_id=pf.PENDING))),
        ("sidecar-running-image-other", edit_json("sidecar-inspect", lambda d: d[0].update(Image="sha256:" + "2" * 64))),
        # O-1: the egress proxy's image, by its own lock's id (launch and running) and platform manifest
        ("egress-manifest-other", lambda raw, w: raw["egress-image-manifest"].update(stdout=json.dumps(MANIFEST))),
        ("egress-manifest-not-json", lambda raw, w: raw["egress-image-manifest"].update(stdout=EGRESS_MANIFEST)),
        ("egress-manifest-failed", lambda raw, w: raw["egress-image-manifest"].update(returncode=1)),
        ("egress-lock-manifest-other", edit_world(lambda w: w.egress_lock.update(manifest_digest=SIDE_MANIFEST))),
        ("egress-lock-manifest-pending", edit_world(lambda w: w.egress_lock.update(manifest_digest=pf.PENDING))),
        ("egress-lock-image-other", edit_world(lambda w: w.egress_lock.update(image_id="sha256:" + "3" * 64))),
        ("egress-lock-image-pending", edit_world(lambda w: w.egress_lock.update(image_id=pf.PENDING))),
        ("egress-launch-image-other", set_value("egress-launch", "sha256:" + "4" * 64)),
        ("egress-running-image-other", edit_json("proxy-inspect", lambda d: d[0].update(Image="sha256:" + "4" * 64))),
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
        ("root-writable", edit_json("take-inspect", lambda d: d[0]["HostConfig"].update(ReadonlyRootfs=False))),
        ("root-unstated", edit_json("take-inspect", lambda d: d[0]["HostConfig"].pop("ReadonlyRootfs"))),
        ("tmpfs-dropped", edit_json("take-inspect", lambda d: d[0]["HostConfig"]["Tmpfs"].pop("/var/tmp"))),
        ("tmpfs-added", edit_json("take-inspect", lambda d: d[0]["HostConfig"]["Tmpfs"].update(
            {"/run/lock": "rw"}))),
        ("tmpfs-noexec", edit_json("take-inspect", lambda d: d[0]["HostConfig"]["Tmpfs"].update(
            {"/tmp": "rw,noexec"}))),
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
        # Lane w6a: the listing tried another host folder than the evidence folder preflight judges.
        ("other-folder", lambda raw, w: edit_json("listing", lambda d: (d.pop(w.ev), d.update(
            {"/srv/w9/ev": "FileNotFoundError"})))(raw, w)),
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
        # Review B-6 (14 Oct): the inspected command must equal the expected one in order and content.
        ("inspect-cmd-reordered", edit_json("sidecar-inspect", lambda d: d[0]["Config"].update(
            Cmd=d[0]["Config"]["Cmd"][:-2] + d[0]["Config"]["Cmd"][-2:][::-1]))),
        ("expect-network", edit_world(lambda w: w.sidecar_expect.update(network_mode="bridge"))),
        ("expect-user", edit_world(lambda w: w.sidecar_expect.update(user="10001:10001"))),
        ("expect-tree-rw", edit_world(lambda w: w.sidecar_expect["mounts"][0].update(rw=True))),
        ("expect-key-missing", edit_world(lambda w: w.sidecar_expect.pop("security_opt"))),
        ("both-bridge", lambda raw, w: (w.sidecar_expect.update(network_mode="bridge"), edit_json(
            "sidecar-inspect", lambda d: d[0]["HostConfig"].update(NetworkMode="bridge"))(raw, w))),
        ("both-wrong-bootstrap-user", lambda raw, w: (w.sidecar_expect.update(user="10001:10001"), edit_json(
            "sidecar-inspect", lambda d: d[0]["Config"].update(User="10001:10001"))(raw, w))),
        ("both-privileged", lambda raw, w: (w.sidecar_expect.update(privileged=True), edit_json(
            "sidecar-inspect", lambda d: d[0]["HostConfig"].update(Privileged=True))(raw, w))),
        ("both-host-pid", lambda raw, w: (w.sidecar_expect.update(pid_mode="host"), edit_json(
            "sidecar-inspect", lambda d: d[0]["HostConfig"].update(PidMode="host"))(raw, w))),
        ("both-no-secopt", lambda raw, w: (w.sidecar_expect.update(security_opt=[]), edit_json(
            "sidecar-inspect", lambda d: d[0]["HostConfig"].update(SecurityOpt=[]))(raw, w))),
        ("both-ev-elsewhere", lambda raw, w: (w.sidecar_expect["mounts"][1].update(destination="/srv/x"), edit_json(
            "sidecar-inspect", lambda d: d[0]["Mounts"][1].update(Destination="/srv/x"))(raw, w))),
        # Lane w6a (CP2-preflight-3): both agree on another evidence source than the folder preflight reads.
        ("both-ev-source-elsewhere", lambda raw, w: (w.sidecar_expect["mounts"][1].update(source="/srv/w9/ev"),
                                                     edit_json("sidecar-inspect", lambda d: d[0]["Mounts"][1].update(
                                                         Source="/srv/w9/ev"))(raw, w))),
    ],
    "watcher-started": [
        ("no-health", edit_value("health", lambda v: v.clear())),
        ("stopped", edit_value("health", lambda v: v.append({"kind": "watcher-stop", "at": 2.0, "exit_code": 0, "ignored_newline_paths": 0}))),
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
        ("present", edit_value("study-folders", lambda v: v.update({STUDY[0]: True}))),
        ("unlooked", edit_value("study-folders", lambda v: v.pop(STUDY[-1]))),
    ],
    "run-tree-path-neutral": [],   # driven by its own test (the path is the spec's)
    # PF1-L3 (pre-freeze review 1, m9; fold plan prefreeze-1, 24 Oct 2026): the three roads out the proxy does not take
    "egress-raw-ip-refused": [
        ("raw-ip-a-connected", _set_connected("raw-ip-a")),
        ("raw-ip-b-connected", _set_connected("raw-ip-b")),
        ("raw-ip-untried", edit_json("direct-egress", lambda d: d["targets"].pop("raw-ip-b"))),
        ("raw-ip-elsewhere", edit_json("direct-egress", lambda d: d["targets"]["raw-ip-a"].update(
            address="10.0.0.1:443"))),
        ("record-off-shape", edit_json("direct-egress", lambda d: d.pop("targets"))),
    ],
    "egress-metadata-refused": [
        ("metadata-connected", _set_connected("metadata")),
        ("metadata-untried", edit_json("direct-egress", lambda d: d["targets"].pop("metadata"))),
    ],
    "egress-gateway-refused": [
        ("gateway-connected", edit_json("direct-egress", lambda d: d["gateway"][GATEWAY]["22"].update(connected=True))),
        ("gateway-unknown", edit_json("direct-egress", lambda d: d["gateway"][GATEWAY]["2375"].pop("connected"))),
        ("port-untried", edit_json("direct-egress", lambda d: d["gateway"][GATEWAY].pop("8080"))),
        ("candidate-untried", edit_json("direct-egress", lambda d: d["gateway"].pop(GATEWAY))),
        ("nothing-tried", edit_json("direct-egress", lambda d: d.update(gateway_candidates=[], gateway={}))),
        ("inspect-gateway-untried", edit_json("take-inspect", lambda d: d[0]["NetworkSettings"]["Networks"]["n"].update(
            Gateway="172.30.0.254"))),
        ("inspect-names-no-network", edit_json("take-inspect", lambda d: d[0].pop("NetworkSettings"))),
        # Lane pf1-gateway: the host-side network record binds the gateway when the take inspect names none
        ("internal-host-gateway-untried", lambda raw, w: (
            edit_json("take-inspect", lambda d: d[0]["NetworkSettings"]["Networks"]["n"].update(Gateway=""))(raw, w),
            edit_json("take-network-inspect", lambda d: d[0]["IPAM"]["Config"][0].update(Gateway="172.30.0.254"))(
                raw, w))),
        ("internal-neither-names-one", lambda raw, w: (
            edit_json("take-inspect", lambda d: d[0]["NetworkSettings"]["Networks"]["n"].update(Gateway=""))(raw, w),
            edit_json("take-network-inspect", lambda d: d[0]["IPAM"].update(Config=[]))(raw, w))),
        ("host-gateway-untried", edit_json("take-network-inspect", lambda d: d[0]["IPAM"]["Config"].append(
            {"Subnet": "10.9.0.0/16", "Gateway": "10.9.0.1"}))),
        ("host-record-other-network", edit_json("take-network-inspect", lambda d: d[0].update(Id="9" * 64))),
        ("host-record-two-networks", edit_json("take-network-inspect", lambda d: d.append(dict(d[0])))),
    ],
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
    def test_the_guard_starts_no_patch_at_import(self):
        """Recorded at the very end of this module's import: no guarded name was patched then. Inside a test every
        guarded name holds the tripwire (setUpModule armed it), so the record can see a patch."""
        self.assertEqual(_PATCHED_AT_IMPORT, [])
        self.assertEqual(len(_patched_now()), len(GUARDED))

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
                            "users.keepalive.uid", "manifest_digest"):
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

    def test_an_internal_network_world_is_green_on_the_host_record(self):
        """Lane pf1-gateway: the take inspect names no Gateway (Docker on an --internal network, w-o48's live reading);
        the host-side network record names the gateway the probe tried, so every arm passes whole."""
        for h in ARMS:
            w = World(h)
            w.answers["take-inspect"][0]["NetworkSettings"]["Networks"]["n"]["Gateway"] = ""
            with filled():
                rec = w.evaluate()
            self.assertEqual(failing(rec), [], h)
            self.assertTrue(rec["ok"])

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
                                      harness=w.harness, hosts=HOSTS, evidence_dir=w.ev, sidecar_lock=w.sidecar_lock, egress_lock=w.egress_lock)
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


def _lock_user_names() -> tuple:
    """The box users' names in every committed take lock (users.agent.name, users.watcher.name); all must agree."""
    seen = set()
    for rel in ("image.lock", "codex/image.lock", "gemini/image.lock"):
        with open(os.path.join(HERE, "box", rel), encoding="utf-8") as fh:
            users = json.load(fh)["users"]
        seen.add((users["agent"]["name"], users["watcher"]["name"]))
    if len(seen) != 1:
        raise AssertionError(f"the take locks name different box users: {sorted(seen)}")
    return seen.pop()


class TestCodexCreateEnvironment(unittest.TestCase):
    """glitch-06's ruling 1: preflight refuses a Codex take whose create-time environment carries CODEX_API_KEY or
    OPENAI_API_KEY at all, naming the variable, never its value."""

    def test_codex_api_key_names_refused_at_create(self):
        for name in ("CODEX_API_KEY", "OPENAI_API_KEY"):
            w = World(rt.CODEX)
            raw = w.raw()
            edit_json("take-inspect", lambda d, n=name: d[0]["Config"]["Env"].append(
                f"{n}=FAKEVALUE-0123456789abcdef-PLANTED"))(raw, w)
            rec = w.evaluate(raw)
            check = [c for c in rec["checks"] if c["id"] == "no-container-socket"][0]
            self.assertFalse(check["ok"], name)
            self.assertIn(name, check["detail"])
            self.assertNotIn("PLANTED", json.dumps(rec))


class TestCreatePrefixRefusal(unittest.TestCase):
    """glitch-06 (14 Oct 2026): preflight's create-time environment check refuses a name with either of
    run_take.REFUSED_NAME_PREFIXES, for every arm, naming the variable, never its value."""

    def test_prefixed_names_refused_at_create(self):
        for harness in (rt.CLAUDE_CODE, rt.GEMINI):
            for name in ("CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_UNSET_HTTPS_PROXY",
                         "CODEX_NETWORK_PROXY_SNAPSHOT_BROKERED_VALUE_X"):
                w = World(harness)
                raw = w.raw()
                edit_json("take-inspect", lambda d, n=name: d[0]["Config"]["Env"].append(
                    f"{n}=FAKEVALUE-0123456789abcdef-PLANTED"))(raw, w)
                rec = w.evaluate(raw)
                check = [c for c in rec["checks"] if c["id"] == "no-container-socket"][0]
                self.assertFalse(check["ok"], f"{harness}: {name}")
                self.assertIn(name, check["detail"])
                self.assertNotIn("PLANTED", json.dumps(rec))


class TestLeasePostflight(MutantCase):
    """The Codex lease postflight (glitch-06, 14 Oct 2026): the lease home (the per-take config folder, CODEX_HOME)
    admits exactly its one registered credential file, auth.json at its root, mode 600, owned by the host user, one
    link; anything else credential-shaped refuses, and so does a home with no auth.json (glitch-06: exactly one), each
    refusal naming the file and the rule, never the contents.
    The planted value is a fake."""

    FAKE_AUTH = b'{"tokens": {"access_token": "FAKE-lease-0123456789abcdef-PLANTED"}}\n'

    def home(self, auth=True, mode=0o600):
        d = tempfile.mkdtemp(prefix="w-")
        os.makedirs(os.path.join(d, "sessions", "2026", "10", "14"))
        with open(os.path.join(d, "config.toml"), "w") as fh:
            fh.write('model = "m"\n')
        with open(os.path.join(d, "sessions", "2026", "10", "14", "rollout-1.jsonl"), "w") as fh:
            fh.write("{}\n")
        if auth:
            fd = os.open(os.path.join(d, "auth.json"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.write(fd, self.FAKE_AUTH)
            os.close(fd)
            os.chmod(os.path.join(d, "auth.json"), mode)
        return d

    def refused(self, out, label, d, path_word, rule_word, **patches):
        ctx = mock.patch.object(pf.os, "getuid", patches["uid"]) if "uid" in patches else contextlib.nullcontext()
        with ctx:
            r = pf.postflight(d, rt.CODEX)
        detail = r["checks"][0]["detail"]
        if r["ok"]:
            out.append(f"{label}: admitted")
        elif path_word not in detail or rule_word not in detail:
            out.append(f"{label}: refused without naming {path_word!r} and {rule_word!r}: {detail}")
        if "PLANTED" in json.dumps(r):
            out.append(f"{label}: the record carries the credential's contents")

    def check(self):
        out = []
        d = self.home()
        r = pf.postflight(d, rt.CODEX)
        if r["ok"] is not True or r["recorded"]["admitted_credential"] != ["auth.json"]:
            out.append(f"the clean lease home was refused: {r['checks'][0]['detail']}")
        if "PLANTED" in json.dumps(r):
            out.append("the clean record carries the credential's contents")
        # glitch-06's ruling (14 Oct 2026): "exactly one registered credential file" means exactly one, so a lease
        # home with no auth.json refuses, naming the file and the rule
        self.refused(out, "a lease home with no credential", self.home(auth=False), "auth.json",
                     "exactly one registered credential file")
        if pf.postflight(self.home(auth=False), rt.CODEX)["recorded"]["admitted_credential"] != []:
            out.append("a lease home with no credential records an admitted credential")
        # a second auth file
        d = self.home()
        with open(os.path.join(d, "sessions", "auth.json"), "wb") as fh:
            fh.write(b"{}")
        self.refused(out, "a second auth file", d, "sessions/auth.json", "credential-shaped")
        # a renamed copy, by a credential-shaped name and by an innocuous one
        d = self.home()
        with open(os.path.join(d, "auth.json.bak"), "wb") as fh:
            fh.write(self.FAKE_AUTH)
        self.refused(out, "a renamed copy (credential-shaped name)", d, "auth.json.bak", "credential-shaped")
        d = self.home()
        with open(os.path.join(d, "sessions", "notes.txt"), "wb") as fh:
            fh.write(self.FAKE_AUTH)
        self.refused(out, "a renamed copy (innocuous name)", d, "sessions/notes.txt", "copy of the registered")
        # a symlink to it, and the registered path as a link
        d = self.home()
        os.symlink(os.path.join(d, "auth.json"), os.path.join(d, "sessions", "plain-link"))
        self.refused(out, "a link to the registered credential", d, "sessions/plain-link", "a link to the registered")
        d = self.home(auth=False)
        with open(os.path.join(d, "elsewhere.json"), "wb") as fh:
            fh.write(b"{}")
        os.symlink(os.path.join(d, "elsewhere.json"), os.path.join(d, "auth.json"))
        self.refused(out, "the registered path as a link", d, "auth.json", "never a link")
        # wrong mode, wrong owner, a second hard link
        self.refused(out, "mode 644", self.home(mode=0o644), "auth.json", "mode must be 600")
        self.refused(out, "another owner", self.home(), "auth.json", "owned by the host user",
                     uid=lambda me=os.getuid(): me + 1)
        d = self.home()
        os.link(os.path.join(d, "auth.json"), os.path.join(d, "sessions", "hardlink"))
        self.refused(out, "a second hard link", d, "auth.json", "exactly one link")
        # review of 2fd8215a (14 Oct): the size and non-regular branches, a credential-named link to an innocuous
        # target, a link to a folder above auth.json, and an unreadable copy candidate (refused, never raised)
        d = self.home(auth=False)
        fd = os.open(os.path.join(d, "auth.json"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, b"x" * (pf.LEASE_CREDENTIAL_MAX_BYTES + 1))
        os.close(fd)
        self.refused(out, "an oversize registered file", d, "auth.json", "larger than")
        d = self.home(auth=False)
        os.mkfifo(os.path.join(d, "auth.json"), 0o600)
        self.refused(out, "a FIFO at the registered path", d, "auth.json", "must be a regular file")
        d = self.home(auth=False)
        os.mkdir(os.path.join(d, "auth.json"), 0o700)
        self.refused(out, "a folder at the registered path", d, "auth.json", "must be a regular file")
        d = self.home()
        os.symlink(os.path.join(d, "config.toml"), os.path.join(d, "sessions", "token-link"))
        self.refused(out, "a credential-named link to an innocuous file", d, "sessions/token-link", "a link")
        d = self.home()
        os.symlink(d, os.path.join(d, "sessions", "up"))
        self.refused(out, "a link to the folder holding the credential", d, "sessions/up", "a link")
        d = self.home()
        cand = os.path.join(d, "sessions", "notes.txt")
        with open(cand, "wb") as fh:
            fh.write(b"y" * len(self.FAKE_AUTH))
        os.chmod(cand, 0)
        try:
            try:
                self.refused(out, "an unreadable same-size file", d, "sessions/notes.txt", "unreadable")
            except OSError as e:
                out.append(f"an unreadable same-size file raised {type(e).__name__} instead of refusing")
        finally:
            os.chmod(cand, 0o600)
        # other harnesses keep the old rule: no credential file at all
        d = self.home()
        if pf.postflight(d, rt.CLAUDE_CODE)["ok"] or pf.postflight(d, rt.GEMINI)["ok"]:
            out.append("another harness admitted auth.json")
        return out

    def check_read(self):
        """glitch-06's NIT 5 ruling: the registered file read is the file checked. A swap between the lstat and the
        open (a FIFO, or another regular file with the same bytes) refuses, never hangs; and an unreadable registered
        file refuses, never raises."""
        out = []
        for label, swap in (("a same-bytes file with a second link", "relink"), ("a FIFO", "fifo"),
                            ("a fresh same-bytes file (one link, same mode and owner: only the inode differs)",
                             "fresh")):
            d = self.home()
            reg = os.path.join(d, "auth.json")
            real_lstat, done, calls = os.lstat, [], []

            def swapping(p, *a, _reg=reg, _swap=swap, _d=d, **k):
                st = real_lstat(p, *a, **k)
                if p == _reg:
                    calls.append(1)
                # the first lstat of auth.json is lexists; the second is the check, whose result the read must match
                if p == _reg and len(calls) == 2 and not done:
                    done.append(1)
                    if _swap == "fresh":                 # made beside it, then renamed over: a new inode for sure
                        tmp = os.path.join(_d, "fresh.tmp")
                        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                        os.write(fd, self.FAKE_AUTH)
                        os.close(fd)
                        os.chmod(tmp, 0o600)
                        os.replace(tmp, _reg)
                        new = real_lstat(_reg)
                        if (new.st_nlink, new.st_mode, new.st_uid) != (st.st_nlink, st.st_mode, st.st_uid) \
                                or new.st_ino == st.st_ino:
                            raise AssertionError("the fresh swap differs in more than the inode")
                        return st
                    os.unlink(_reg)
                    if _swap == "fifo":
                        os.mkfifo(_reg, 0o600)
                    else:
                        fd = os.open(_reg, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                        os.write(fd, self.FAKE_AUTH)
                        os.close(fd)
                        os.link(_reg, os.path.join(_d, "outside-link"))
                return st
            with mock.patch.object(pf.os, "lstat", swapping):
                r = pf.postflight(d, rt.CODEX)
            detail = r["checks"][0]["detail"]
            if not done:
                out.append(f"{label}: the swap never ran (the check did not lstat auth.json)")
            elif r["ok"] or "changed between its check and its read" not in detail or "auth.json" not in detail:
                out.append(f"{label} swapped in after the check was not refused by file and rule: {detail}")
            if "PLANTED" in json.dumps(r):
                out.append(f"{label}: the record carries the credential's contents")
        d = self.home()
        with mock.patch.object(pf, "_read_capped", side_effect=PermissionError("planted")):
            try:
                self.refused(out, "an unreadable registered file", d, "auth.json", "unreadable")
            except OSError as e:
                out.append(f"an unreadable registered file raised {type(e).__name__} instead of refusing")
        return out

    def test_the_registered_file_read_is_the_file_checked(self):
        self.assertEqual(_problems(self.check_read), [])

    def test_the_lease_admits_exactly_its_one_credential(self):
        self.assert_green_then_red(self.check, [
            ("no-lease", patched(pf, "LEASE_CREDENTIAL", {})),
            ("lease-for-every-harness", patched(pf, "LEASE_CREDENTIAL", {h: "auth.json" for h in rt.LOGIN_VARIABLE})),
        ])


class TestCP5Values(MutantCase):
    """Javier's ruling, "CP5: all as recommended" (08:11 EDT, 14 Oct 2026), on cp5-values-draft-2026-10-14.md:
    STUDY_PATHS is round 3's seven excluded paths verbatim; LEAK_WORDS is prereg-draft.json's leak_words, the box
    users' names from the committed locks, and gap4."""

    def check(self):
        out = []
        if pf.STUDY_PATHS != ROUND3_EXCLUDED or len(pf.STUDY_PATHS) != 7:
            out.append(f"STUDY_PATHS is not round 3's seven excluded paths: {pf.STUDY_PATHS!r}")
        with open(os.path.join(HERE, "prereg-draft.json"), encoding="utf-8") as fh:
            draft = tuple(json.load(fh)["leak_words"])
        want = draft + _lock_user_names() + ("gap4",)
        if len(draft) != 25 or tuple(draft[:23]) != ROUND3_WORDS:
            out.append("the prereg draft's leak words are not round 3's 23 plus two")
        if pf.LEAK_WORDS != want or len(pf.LEAK_WORDS) != 28 or len(set(pf.LEAK_WORDS)) != 28:
            out.append(f"LEAK_WORDS is not the ruled 28: {pf.LEAK_WORDS!r}")
        if not all(isinstance(w, str) and w for w in pf.LEAK_WORDS + pf.STUDY_PATHS):
            out.append("an entry is not a non-empty string")
        if pf.pending().keys() & {"STUDY_PATHS", "LEAK_WORDS"}:
            out.append("a ruled value still reads as PENDING")
        if pf.leak_hits("/srv/gars-gap4/run-1", pf.LEAK_WORDS) != ["gap4"] or \
                pf.leak_hits("/tmp/run-0a1b2c3d", pf.LEAK_WORDS):
            out.append("the path check does not read the ruled list as the draft's probe did")
        return out

    def test_the_ruled_values(self):
        self.assert_green_then_red(self.check, [
            ("study-entry-dropped", patched(pf, "STUDY_PATHS", pf.STUDY_PATHS[:-1])),
            ("study-reordered", patched(pf, "STUDY_PATHS", tuple(reversed(pf.STUDY_PATHS)))),
            ("leak-entry-dropped", patched(pf, "LEAK_WORDS", pf.LEAK_WORDS[1:])),
            ("gap4-removed", patched(pf, "LEAK_WORDS", tuple(w for w in pf.LEAK_WORDS if w != "gap4"))),
            ("box-user-dropped", patched(pf, "LEAK_WORDS", tuple(w for w in pf.LEAK_WORDS if w != "eli"))),
            ("box-user-drifted", patched(pf, "LEAK_WORDS", tuple("dora" if w == "dana" else w for w in pf.LEAK_WORDS))),
            ("lock-user-renamed", patched(sys.modules[__name__], "_lock_user_names", lambda: ("dora", "eli"))),
        ])


# `<harness> --version` as printed on athena (lane-reports/stub-take-20261014/stub-take-run2.json `versions`).
ATHENA_VERSION_OUT = {rt.CLAUDE_CODE: "2.1.296 (Claude Code)\n", rt.CODEX: "codex-cli 0.162.1\n",
                      rt.GEMINI: "0.64.0\n"}


class TestVersionPatterns(MutantCase):
    """The filled VERSION_PATTERNS read athena's measured outputs as each committed lock's version, exactly."""

    def check(self):
        out = []
        for h, rel in ((rt.CLAUDE_CODE, "image.lock"), (rt.CODEX, "codex/image.lock"), (rt.GEMINI, "gemini/image.lock")):
            with open(os.path.join(HERE, "box", rel), encoding="utf-8") as fh:
                want = json.load(fh)["harness"]["version"]
            m = re.fullmatch(pf.VERSION_PATTERNS[h], ATHENA_VERSION_OUT[h].strip())
            if m is None or m.group(1) != want:
                out.append(f"{h}: the pattern does not read {want} from athena's output")
            if re.fullmatch(pf.VERSION_PATTERNS[h], ATHENA_VERSION_OUT[h].strip() + " extra"):
                out.append(f"{h}: the pattern admits a trailing line")
        return out

    def test_patterns(self):
        self.assert_green_then_red(self.check, [
            ("claude-loose-tail", patched(pf, "VERSION_PATTERNS", dict(pf.VERSION_PATTERNS, **{
                rt.CLAUDE_CODE: r"([0-9.]+).*"}))),
            ("codex-no-prefix", patched(pf, "VERSION_PATTERNS", dict(pf.VERSION_PATTERNS, codex=r"([0-9.]+)"))),
        ])


class TestPending(MutantCase):
    # STUDY_PATHS and LEAK_WORDS are RULED (Javier, "CP5: all as recommended", 08:11 EDT 14 Oct 2026): TestCP5Values.
    # VERSION_PATTERNS, and run_take's TOP_FORMAT and INSPECT_STATUS, FILLED 14 Oct 2026 (stub-take review PASS).
    EXPECT = set()
    # FALLBACK_ENV FILLED; bypass RULED; VENDOR_BILLING_ROUTE_VARIABLES FILLED 14 Oct 2026 (the Codex and Gemini sweeps)
    EXPECT_RT = {"TakeSpec.resources"}
    # With the two filled values put back to PENDING, exactly these checks fail (the gate stays non-vacuous).
    GATED = {"image-matches-lock", "harness-version-matches-lock", "take-inspect-matches-spec",
             "sidecar-isolated", "no-container-socket"}

    def check(self):
        out = []
        if set(pf.pending()) != self.EXPECT:
            out.append(f"preflight.pending() = {sorted(pf.pending())}")
        if set(rt.pending()) != self.EXPECT_RT:
            out.append(f"run_take.pending() = {sorted(rt.pending())}")
        w = World()
        rec = w.evaluate()   # the committed values, nothing patched: a passing take passes every check
        if failing(rec) or not rec["ok"]:
            out.append(f"the filled values fail {sorted(failing(rec))}")
        with mock.patch.object(rt, "INSPECT_STATUS", rt.PENDING), \
                mock.patch.object(pf, "VERSION_PATTERNS", {h: pf.PENDING for h in ARMS}):
            rec = w.evaluate()   # the spellings and the version forms PENDING: every gated check fails
        if set(failing(rec)) != self.GATED:
            out.append(f"unfilled failing set {sorted(failing(rec))}")
        if rec["ok"]:
            out.append("an unfilled preflight passed")
        if rec["recorded"]["token_visible_to_children"] != pf.PENDING:
            out.append("token visibility was judged, not recorded PENDING")
        g = World(rt.GEMINI)
        # lane d8-furniture fold 2 (glitch-f1, 22 Oct 2026): the tier is the owner's recorded fact, with its source
        with filled():
            if g.evaluate()["recorded"]["google_project_tier"] != pf.GOOGLE_PROJECT_TIER or \
                    "Google Paid, cap $140" not in pf.GOOGLE_PROJECT_TIER or "google_project_tier" in pf.RECORDED_PENDING:
                out.append("the Google tier is not the owner's recorded fact")
        return out

    def test_pending(self):
        self.assert_green_then_red(self.check, [
            ("never-pending", patched(rt, "_is_pending", lambda v: False)),
            ("version-unfilled", patched(pf, "VERSION_PATTERNS", dict(pf.VERSION_PATTERNS, codex=pf.PENDING))),
            ("version-loose", patched(pf, "VERSION_PATTERNS", dict(pf.VERSION_PATTERNS, **{rt.CLAUDE_CODE: r"(x)"}))),
            ("study-empty", patched(pf, "STUDY_PATHS", ())),
            ("leaks-empty", patched(pf, "LEAK_WORDS", ())),
            ("inspect-unfilled", patched(rt, "INSPECT_STATUS", rt.PENDING)),
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
        derived = {"image": argv[-2], "entrypoint": [val("--entrypoint")], "user": val("--user"), "network_mode": val("--network"),
                   "pids_limit": int(val("--pids-limit")), "memory": int(val("--memory")),
                   "memory_reservation": int(val("--memory-reservation")),
                   "nano_cpus": int(float(val("--cpus")) * 1e9), "cap_drop": [val("--cap-drop")],
                   "security_opt": [val("--security-opt")], "working_dir": val("--workdir"), "cmd": argv[-1:]}
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
        with mock.patch.object(rt, "INSPECT_STATUS", rt.PENDING):
            self.assertTrue(pf.inspect_mismatches(obj, exp, kind="take"))     # spellings PENDING
        # the filled spellings (14 Oct 2026), unpatched: the passing inspect matches, a wrong fact or key does not
        self.assertEqual(pf.inspect_mismatches(obj, exp, kind="take"), [])
        self.assertTrue(pf.inspect_mismatches(obj, dict(exp, pids_limit=exp["pids_limit"] + 1), kind="take"))
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
        if len(built) != 9:      # R4-2 (lane vendor-b11 round 4): arms O's and G's version probe runs one too;
            out.append(f"{len(built)} probes run a program, not 9")   # PF1-L3 (m9): and the direct-egress probe
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
                image_read = p.id in ("take-image-manifest", "sidecar-image-manifest", "egress-image-manifest") and list(p.argv[1:5]) == [
                    "image", "inspect", "--platform", pf.IMAGE_PLATFORM]
                # Lane pf1-gateway: the host reads the take's own network, by its id and nothing else
                network_read = p.id == "take-network-inspect" and list(p.argv) == ["docker", "network", "inspect",
                                                                                    w.spec.network]
                if list(p.argv[:4]) != ["docker", "exec", "--user", rt.AGENT_USER] and p.argv[1] != "container" \
                        and not image_read and not network_read:
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
        for h in (rt.CODEX, rt.GEMINI):      # R4-2: their --version runs on a throwaway home, never the config mount
            argv = [q for q in World(h).probes() if q.id == "harness-version"][0].argv
            if "-e" in argv or any(rt.CONFIG_MOUNT in a for a in argv):
                out.append(f"the {h} version probe names the config mount or carries a variable")
            want = ["python3", "-I", "-B", "-c", pf.VERSION_PROBE_PROGRAM, "/tmp",
                    f"{CONFIG_HOME[h]},HOME", *pf.VERSION_COMMANDS[h]]
            if list(argv[-len(want):]) != want:
                out.append(f"the {h} version probe is not the throwaway-home program on /tmp with its config home "
                           f"and HOME")
        return out

    def test_programs(self):
        self.assert_green_then_red(self.check, [
            ("py312-feature", patched(pf, "IDENTITY_PROGRAM", "type X = int\n")),
            ("study-word", patched(pf, "IDENTITY_PROGRAM", pf.IDENTITY_PROGRAM + "# probe\n")),
            ("reads-tree", patched(pf, "CGROUP_PROGRAM", 'open("tree/x")\n')),
            ("version-without-config-home", patched(pf, "_config_home_values", lambda h: {})),
            ("version-probe-on-the-config-mount", patched(pf, "VERSION_PROBE_HOMES", {})),
            ("version-probe-root-moved", patched(pf, "VERSION_PROBE_ROOT", "/opt/cfg")),
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
        status = {"/proc/1/status": ("Name:\tsleep\nUid:\t10003\t10003\t10003\t10003\n"
                    "Gid:\t10003\t10003\t10003\t10003\nGroups:\t\nNoNewPrivs:\t1\n"
                    "CapEff:\t0\nCapPrm:\t0\nCapInh:\t0\nCapBnd:\t0\nCapAmb:\t0\n")}
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


@contextlib.contextmanager
def host_temp(kind):
    """A fake host temp root. "study-word": a folder whose name carries a lane lead word, as athena's battery folder
    did on Linux (gap4-wave4-merge-...); "neutral": a plain folder, as on the Mac. Nothing else of the host is read."""
    parent = tempfile.mkdtemp(prefix="w-")
    root = os.path.join(parent, "gap4-host" if kind == "study-word" else "plain-host")
    os.makedirs(root)
    with mock.patch.object(tempfile, "tempdir", root):
        yield root


class TestHostIndependence(MutantCase):
    """The athena red (Linux only): the World's run tree sat under the host's temp root, whose path carried a study
    word there, so run-tree-path-neutral failed in every world and the missing-probe mutant survived. The fixtures'
    agent-visible paths must come from the test's own fakes, whatever the host's temp root is called."""

    def check(self):
        out = []
        ev = TestEvaluate()
        for kind in ("study-word", "neutral"):
            with host_temp(kind):
                for h in ARMS:
                    with filled():
                        rec = World(h).evaluate()
                    if failing(rec):
                        out.append(f"{kind} host, {h}: a passing world fails {failing(rec)}")
                with mock.patch.dict(pf.CHECKS, {k: _assume_missing(f) for k, f in pf.CHECKS.items()}):
                    if not ev.missing_or_failed():
                        out.append(f"{kind} host: the missing-assumed-to-pass mutant survives")
        return out

    def test_host_temp_root_is_never_read(self):
        self.assert_green_then_red(self.check, [
            ("tree-under-host-temp", patched(World, "FAKE_TREE", False)),
        ])


def _assume_missing(fn):
    def wrapped(*a):
        try:
            return fn(*a)
        except pf._Fail as e:
            if "missing" in str(e) or "failed" in str(e) or "exited" in str(e) or "no " in str(e):
                return "assumed"
            raise
    return wrapped


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
            if h in pf.LEASE_CREDENTIAL:                 # a clean lease home holds its one registered credential
                fd = os.open(os.path.join(d, pf.LEASE_CREDENTIAL[h]), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.write(fd, b"{}")
                os.close(fd)
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


# ======================================================================= lane w6a: the lock and evidence seam
# CP2-preflight-1 to -5 (glitch-1b's rulings, 10 Oct 16:05 EDT). Fakes only: synthetic lock files in a temporary
# stand-in for box/, a FakeRuntime, the World above. No container, no model, no network.

FAKE_BASE = "registry.example/fake-base@sha256:" + "a" * 64
PLACEHOLDER_NET = "e" * 64                      # the pre-launch placeholder network id (W4B2-3), never the launched one
# Each harness's own take image, typed here (never read from preflight), so a swapped map in preflight shows.
HARNESS_IMAGE = {rt.CLAUDE_CODE: "take-a", rt.CODEX: "take-o", rt.GEMINI: "take-g"}
REFUSALS = (rt.Refused, rt.NotReady, il.LockError, il.NotReady, ValueError, TypeError, OSError)


def committed_lock(image: str) -> dict:
    """A committed lock, read through the real loader at its real path (read only, never edited)."""
    return il.load(os.path.join(il.BOX_DIR, os.path.dirname(il.DOCKERFILES[image]), "image.lock"))


def ready_lock(image: str, version: str = "9.8.7") -> dict:
    """The committed lock with every PENDING value replaced by an obviously fake pinned value (test_image's way)."""
    lock = copy.deepcopy(committed_lock(image))
    lock.update(schema=il.SCHEMA_2, manifest_digest=MANIFEST, config_digest="sha256:" + "d" * 64,
                source_commit="e" * 40)          # a filled lock is schema 2 (lock-writer ruling (b))
    lock["base"] = FAKE_BASE
    lock["image_id"] = IMAGE
    if lock["harness"] is not None:
        lock["harness"]["version"] = version
    if lock["python"] is not None:
        lock["python"] = "3.12.99"
    if "squid" in lock:
        lock["squid"] = "6.99-1+fake1"
    lock["pending"] = {}
    return lock


def ready_sidecar_lock() -> dict:
    """The committed sidecar lock, filled (schema 2) with the World's sidecar image and its own platform manifest."""
    lock = ready_lock("sidecar")
    lock["manifest_digest"] = SIDE_MANIFEST
    return lock


def ready_egress_lock() -> dict:
    """The committed egress lock, filled (schema 2) with the World's egress image and its own platform manifest."""
    lock = ready_lock("egress")
    lock.update(image_id=EGRESS_IMAGE_ID, manifest_digest=EGRESS_MANIFEST)
    return lock


def flat(lock: dict) -> dict:
    """The five values a ready nested lock projects to, by the schema paths typed here."""
    return {"image_id": lock["image_id"], "harness.version": lock["harness"]["version"],
            "users.agent.uid": lock["users"]["agent"]["uid"], "users.watcher.uid": lock["users"]["watcher"]["uid"],
            "users.keepalive.uid": lock["users"]["keepalive"]["uid"], "manifest_digest": lock["manifest_digest"]}


class LockBox:
    """A temporary stand-in for box/: each lock at its own relative path; image_lock.BOX_DIR is patched while active."""

    def __init__(self, sidecar=True, egress=True):
        self.root = tempfile.mkdtemp(prefix="w-")
        if sidecar:
            self.put("sidecar", ready_sidecar_lock())
        if egress:
            self.put("egress", ready_egress_lock())

    def path(self, image: str) -> str:
        return os.path.join(self.root, os.path.dirname(il.DOCKERFILES[image]), "image.lock")

    def put(self, image: str, doc=None, *, text=None, at=None) -> str:
        p = at or self.path(image)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text if text is not None else json.dumps(doc, indent=1))
        return p

    def active(self):
        return mock.patch.object(il, "BOX_DIR", self.root)


def launched_for(w, *, spec="launched", **edits):
    """The launch record run_take.launch returns, on the World's spec (its network is the one launch made)."""
    rec = rt.Launched(config_dir=w.cfg, spec=w.spec if spec == "launched" else spec, network_id=ID["net"],
                      proxy_id=PROXY_ID, sidecar_id=ID["side"], take_id=ID["take"], ok=True,
                      steps=[{"step": "proxy-create", "returncode": 0,
                              "argv": ["docker", "create", "--network", ID["net"], "--network-alias", "proxy",
                                       w.proxy_image, "squid", "-N"]}])
    for k, v in edits.items():
        setattr(rec, k, v)
    return rec


def sidecar_for(w):
    never = lambda cid: ("never",)  # noqa: E731
    return rt.SidecarLaunch(create_argv=("docker", "create"), start_argv_for=never, ctl_argv_for=never,
                            rm_argv_for=never, expect=w.sidecar_expect)


def compose(m, w, lock_path, *, launched=None, sidecar=None, evidence_dir=None, script=True):
    """collect_and_evaluate of module `m` over World `w`, with spies on the probes, the evaluator, the health read, the
    loader, the readiness gate and the launch lifecycle. Returns (("record", rec) | ("refused", exc), spies, fake).
    A refusal of the REFUSALS types is an outcome; anything else raises (an error, never a pass or a kill)."""
    fake = FakeRuntime(w.script() if script else ())
    spies = {k: [] for k in ("probes", "evaluate", "health", "load", "ready", "lifecycle")}
    real = {"probes": m.probes, "evaluate": m.evaluate, "health": m._read_health, "load": il.load,
            "ready": il.require_ready}

    def probes_spy(spec, **k):
        spies["probes"].append(dict(k, spec=spec))
        return real["probes"](spec, **k)

    def evaluate_spy(raw, **k):
        spies["evaluate"].append(k)
        return real["evaluate"](raw, **k)

    def health_spy(path):
        spies["health"].append(path)
        return real["health"](path)

    def load_spy(path):
        got = real["load"](path)
        spies["load"].append((path, got))
        return got

    def ready_spy(lock):
        spies["ready"].append(lock)
        return real["ready"](lock)

    def lifecycle(name):
        def trip(*a, **k):
            spies["lifecycle"].append(name)
            raise AssertionError(f"preflight reached run_take.{name}")
        return trip
    launched = launched_for(w) if launched is None else launched
    sidecar = sidecar_for(w) if sidecar is None else sidecar
    with filled(mod=m), mock.patch.object(m, "probes", probes_spy), mock.patch.object(m, "evaluate", evaluate_spy), \
            mock.patch.object(m, "_read_health", health_spy), mock.patch.object(il, "load", load_spy), \
            mock.patch.object(il, "require_ready", ready_spy), \
            mock.patch.object(os.path, "lexists", lambda p: False), \
            mock.patch.object(rt, "launch", lifecycle("launch")), \
            mock.patch.object(rt, "run_turn", lifecycle("run_turn")), \
            mock.patch.object(rt, "teardown", lifecycle("teardown")), \
            mock.patch.object(rt, "kill_agent", lifecycle("kill_agent")):
        try:
            out = ("record", m.collect_and_evaluate(
                fake, launched=launched, sidecar=sidecar, lock_path=lock_path, harness=w.harness, hosts=HOSTS,
                evidence_dir=w.ev if evidence_dir is None else evidence_dir, begin_reply=w.begin,
                caller_env={"PATH": "/bin"}))
        except REFUSALS as e:
            out = ("refused", e)
    return out, spies, fake


def run_case(problems: list, tag: str, case: str, fn):
    """One case of a check: its own assertions append `tag: ...` lines; an unexpected exception is an ERROR line,
    which never counts as a witness's kill."""
    try:
        fn()
    except Exception as e:  # recorded, never swallowed: the bound check is then not a clean kill
        problems.append(f"ERROR {tag} {case}: {type(e).__name__}: {str(e)[:120]}")


class LockSeam:
    """The bound checks (each returns [] on preflight). `m` is box/preflight.py or a witness's in-memory copy."""

    @staticmethod
    def c1_loader(m) -> list:
        """Criterion 1: for each take harness a valid, ready nested lock reaches evaluate as exactly the five values,
        and the real image_lock.load and require_ready were called on it."""
        out = []
        for h in ARMS:
            def case(h=h):
                w = World(h)
                box = LockBox()
                lock = ready_lock(HARNESS_IMAGE[h], VERSION_OUT[h][2])
                path = box.put(HARNESS_IMAGE[h], lock)
                with box.active():
                    (kind, got), spies, fake = compose(m, w, path)
                if [p for p, _ in spies["load"]] != [path, box.path("sidecar"), box.path("egress")]:
                    calls = [p for p, _ in spies["load"]]
                    out.append(f"C1-loader-spy {h}: image_lock.load calls {calls}, not [{path}, the sidecar lock]")
                if len(spies["ready"]) != 3 or len(spies["load"]) != 3 \
                        or [r is l for r, (_, l) in zip(spies["ready"], spies["load"])] != [True, True, True]:
                    out.append(f"C1-ready-spy {h}: require_ready was not called once on each load's own result")
                if kind != "record":
                    out.append(f"C1-values {h}: refused ({type(got).__name__}: {str(got)[:80]})")
                    return
                if [e["lock"] for e in spies["evaluate"]] != [flat(lock)]:
                    out.append(f"C1-values {h}: evaluate received {[e['lock'] for e in spies['evaluate']]}")
                if failing(got) or not got["ok"]:
                    out.append(f"C1-values {h}: the record fails {failing(got)}")
            run_case(out, "C1-loader", h, case)
        return out

    @staticmethod
    def c1_flat(m) -> list:
        """Criterion 1: a pre-flattened lock never reaches evaluate: not as a file, not as an argument."""
        out = []

        def case():
            w = World()
            box = LockBox()
            path = box.put("take-a", flat(ready_lock("take-a", VERSION_OUT[rt.CLAUDE_CODE][2])))
            for label, arg in (("a flattened lock file", path), ("a flattened dict", w.lock)):
                with box.active():
                    (kind, got), spies, fake = compose(m, w, arg, script=False)
                if kind != "refused" or fake.calls or spies["evaluate"]:
                    out.append(f"C1-flat {label}: {kind}, {len(fake.calls)} runtime calls, "
                               f"{len(spies['evaluate'])} evaluations")
        run_case(out, "C1-flat", "flat", case)
        return out

    @staticmethod
    def c1_relative(m) -> list:
        """Criterion 1 (W6A-R1-1): a relative path to a VALID, ready take lock refuses (run_take.Refused) before
        the loader and the runtime, so only the absolute-path rule can refuse it."""
        out = []

        def case():
            w = World()
            box = LockBox()
            path = box.put("take-a", ready_lock("take-a", VERSION_OUT[rt.CLAUDE_CODE][2]))
            rel = os.path.relpath(path)
            if os.path.isabs(rel) or not os.path.isfile(rel):
                out.append(f"C1-relative: the fixture is not a readable relative path ({rel})")
                return
            with box.active():
                (kind, got), spies, fake = compose(m, w, rel, script=False)
            if kind != "refused" or not isinstance(got, rt.Refused) or fake.calls or spies["load"] \
                    or spies["evaluate"]:
                out.append(f"C1-relative: {kind} ({type(got).__name__}), {len(spies['load'])} loads, "
                           f"{len(fake.calls)} runtime calls")
        run_case(out, "C1-relative", "relative", case)
        return out

    @staticmethod
    def c2_closed(m) -> list:
        """Criterion 2: the closed schema, duplicate keys and the neighbouring Dockerfile refuse before any runtime
        call, through the composition."""
        out = []
        dup = json.dumps(ready_lock("take-a", VERSION_OUT[rt.CLAUDE_CODE][2]), indent=1).replace(
            '"schema": 2,', '"schema": 2,\n "schema": 2,', 1)
        cases = {
            "missing key": (lambda lk: lk.pop("python"), il.LockError, None),
            "unknown key": (lambda lk: lk.update(extra=1), il.LockError, None),
            "wrong package": (lambda lk: lk["harness"].update(package="@openai/codex"), il.LockError, None),
            "wrong image": (lambda lk: lk.update(image="take-o"), il.LockError, None),
            "duplicate key": (None, il.LockError, dup),
            "wrong neighbouring Dockerfile": ("codex", il.LockError, None),
            "malformed JSON": (None, ValueError, '{"schema": 1,'),
        }
        for label, (edit, err, text) in cases.items():
            def case(label=label, edit=edit, err=err, text=text):
                w = World()
                box = LockBox()
                lock = ready_lock("take-a", VERSION_OUT[rt.CLAUDE_CODE][2])
                if callable(edit):
                    edit(lock)
                at = box.path("take-o") if edit == "codex" else None
                path = box.put("take-a", lock, text=text, at=at)
                with box.active():
                    (kind, got), spies, fake = compose(m, w, path, script=False)
                if kind != "refused" or not isinstance(got, err) or fake.calls or spies["probes"] \
                        or spies["evaluate"]:
                    out.append(f"C2-closed {label}: {kind} ({type(got).__name__}), {len(fake.calls)} runtime calls")
            run_case(out, "C2-closed", label, case)
        return out

    @staticmethod
    def c2_pending(m) -> list:
        """Criterion 2: every still-PENDING field refuses (image_lock.NotReady) before any runtime call."""
        out = []
        for field in ("base", "harness.version", "python", "image_id"):
            def case(field=field):
                w = World()
                box = LockBox()
                lock = ready_lock("take-a", VERSION_OUT[rt.CLAUDE_CODE][2])
                for k in il.SCHEMA_2_KEYS:            # a PENDING field lives only in the unfilled schema-1 lock
                    del lock[k]
                lock.update(schema=il.SCHEMA, image_id=il.PENDING)
                head, _, tail = field.partition(".")
                if tail:
                    lock[head][tail] = il.PENDING
                else:
                    lock[head] = il.PENDING
                lock["pending"] = {"image_id": "a synthetic reason (the build makes it)",
                                   field: "a synthetic reason (lane w6a's test)"}
                path = box.put("take-a", lock)
                with box.active():
                    (kind, got), spies, fake = compose(m, w, path, script=False)
                if kind != "refused" or not isinstance(got, il.NotReady) or fake.calls or spies["evaluate"]:
                    out.append(f"C2-pending {field}: {kind} ({type(got).__name__}), not NotReady before the runtime "
                               f"({len(fake.calls)} runtime calls, {len(spies['evaluate'])} evaluations)")
                    return
                # LW-5: image_id is PENDING in every schema-1 case, so the refusal must name this case's own field.
                named = str(got).partition("pending: ")[2].split(", ")
                if field not in named:
                    out.append(f"C2-pending {field}: the refusal names {named}, not {field}")
            run_case(out, "C2-pending", field, case)
        return out

    @staticmethod
    def c7_sidecar(m) -> list:
        """LW-7: the sidecar's lock is read through the loader (ready, its own image) before any runtime call, and its
        platform manifest is the content the probe must read: a lock whose manifest differs fails the record."""
        out = []
        h = rt.CLAUDE_CODE
        take = ready_lock("take-a", VERSION_OUT[h][2])

        def refused(label, edit, err):
            def case():
                w = World(h)
                box = LockBox(sidecar=False)
                side = ready_sidecar_lock()
                if edit == "absent":
                    pass
                elif isinstance(edit, str):
                    box.put("sidecar", text=edit)
                else:
                    edit(side)
                    box.put("sidecar", side)
                path = box.put("take-a", take)
                with box.active():
                    (kind, got), spies, fake = compose(m, w, path, script=False)
                if kind != "refused" or not isinstance(got, err) or fake.calls or spies["probes"] or spies["evaluate"]:
                    out.append(f"C7-sidecar {label}: {kind} ({type(got).__name__}), {len(fake.calls)} runtime calls")
            run_case(out, "C7-sidecar", label, case)

        def pend(lk):
            for k in il.SCHEMA_2_KEYS:
                del lk[k]
            lk.update(schema=il.SCHEMA, image_id=il.PENDING, pending={"image_id": "a synthetic reason"})
        refused("pending sidecar lock", pend, il.NotReady)
        refused("absent sidecar lock", "absent", OSError)
        refused("malformed sidecar lock", '{"schema": 2,', ValueError)
        refused("sidecar lock of another image", lambda lk: lk.update(image="take-a"), il.LockError)

        def accepted_or_failed(label, edit, want_ok):
            def case():
                w = World(h)
                box = LockBox(sidecar=False)
                side = ready_sidecar_lock()
                edit(side)
                box.put("sidecar", side)
                path = box.put("take-a", take)
                with box.active():
                    (kind, got), spies, fake = compose(m, w, path)
                if kind != "record":
                    out.append(f"C7-sidecar {label}: refused ({type(got).__name__}: {str(got)[:80]})")
                    return
                if [e.get("sidecar_lock") for e in spies["evaluate"]] != [
                        {"image_id": side["image_id"], "manifest_digest": side["manifest_digest"]}]:
                    out.append(f"C7-sidecar {label}: evaluate received {[e.get('sidecar_lock') for e in spies['evaluate']]}")
                sides = [p.get("sidecar_image") for p in spies["probes"]]
                if sides != [w.sidecar_expect["image"]]:
                    out.append(f"C7-sidecar {label}: the manifest probe read {sides}, not the launch's sidecar image")
                if got["ok"] != want_ok or (not want_ok and "image-matches-lock" not in failing(got)):
                    out.append(f"C7-sidecar {label}: ok={got['ok']}, failing {failing(got)}")
            run_case(out, "C7-sidecar", label, case)
        accepted_or_failed("matching sidecar lock", lambda lk: None, True)
        accepted_or_failed("sidecar lock of other content", lambda lk: lk.update(manifest_digest=MANIFEST), False)
        accepted_or_failed("sidecar lock of another build", lambda lk: lk.update(image_id="sha256:" + "1" * 64), False)
        return out

    @staticmethod
    def c8_egress(m) -> list:
        """O-1: the egress lock is read through the loader (ready, its own image) before any runtime call; the
        launch record's proxy image and the running proxy must be its id, and its manifest the probe's."""
        out = []
        h = rt.CLAUDE_CODE
        take = ready_lock("take-a", VERSION_OUT[h][2])

        def refused(label, edit, err, launched_edit=None):
            def case():
                w = World(h)
                box = LockBox(egress=False)
                eg = ready_egress_lock()
                if edit == "absent":
                    pass
                elif isinstance(edit, str):
                    box.put("egress", text=edit)
                else:
                    edit(eg)
                    box.put("egress", eg)
                path = box.put("take-a", take)
                launched = launched_for(w, **(launched_edit or {}))
                with box.active():
                    (kind, got), spies, fake = compose(m, w, path, launched=launched, script=False)
                if kind != "refused" or not isinstance(got, err) or fake.calls or spies["probes"] or spies["evaluate"]:
                    out.append(f"C8-egress {label}: {kind} ({type(got).__name__}), {len(fake.calls)} runtime calls")
            run_case(out, "C8-egress", label, case)

        def pend(lk):
            for k in il.SCHEMA_2_KEYS:
                del lk[k]
            lk.update(schema=il.SCHEMA, image_id=il.PENDING, pending={"image_id": "a synthetic reason"})
        refused("pending egress lock", pend, il.NotReady)
        refused("absent egress lock", "absent", OSError)
        refused("egress lock of another image", lambda lk: lk.update(image="take-a"), il.LockError)
        refused("no proxy-create step in the launch record", lambda lk: None, rt.Refused,
                {"steps": []})
        refused("a proxy-create step naming no image", lambda lk: None, rt.Refused,
                {"steps": [{"step": "proxy-create", "returncode": 0, "argv": ["docker", "create", "squid"]}]})

        def recorded(label, lock_edit, want_ok, launch_image=None):
            def case():
                w = World(h)
                if launch_image:
                    w.proxy_image = launch_image
                box = LockBox(egress=False)
                eg = ready_egress_lock()
                lock_edit(eg)
                box.put("egress", eg)
                path = box.put("take-a", take)
                with box.active():
                    (kind, got), spies, fake = compose(m, w, path)
                if kind != "record":
                    out.append(f"C8-egress {label}: refused ({type(got).__name__}: {str(got)[:80]})")
                    return
                if [e.get("egress_lock") for e in spies["evaluate"]] != [
                        {"image_id": eg["image_id"], "manifest_digest": eg["manifest_digest"]}]:
                    out.append(f"C8-egress {label}: evaluate received {[e.get('egress_lock') for e in spies['evaluate']]}")
                if [p.get("proxy_image") for p in spies["probes"]] != [w.proxy_image]:
                    out.append(f"C8-egress {label}: the probes read {[p.get('proxy_image') for p in spies['probes']]}")
                if got["ok"] != want_ok or (not want_ok and "image-matches-lock" not in failing(got)):
                    out.append(f"C8-egress {label}: ok={got['ok']}, failing {failing(got)}")
            run_case(out, "C8-egress", label, case)
        recorded("matching egress lock", lambda lk: None, True)
        recorded("egress lock of other content", lambda lk: lk.update(manifest_digest=MANIFEST), False)
        recorded("egress lock of another build", lambda lk: lk.update(image_id="sha256:" + "3" * 64), False)
        recorded("a launch image that is not the lock's", lambda lk: None, False, launch_image="sha256:" + "4" * 64)
        return out

    @staticmethod
    def c3_cross(m) -> list:
        """Criterion 3: a valid, ready lock of another take image refuses; each intended pair is accepted."""
        out = []
        pairs = [(rt.CLAUDE_CODE, "take-o", False), (rt.CODEX, "take-a", False), (rt.GEMINI, "take-o", False)]
        pairs += [(h, HARNESS_IMAGE[h], True) for h in ARMS]
        for h, image, accepted in pairs:
            def case(h=h, image=image, accepted=accepted):
                w = World(h)
                box = LockBox()
                path = box.put(image, ready_lock(image, VERSION_OUT[h][2]))
                with box.active():
                    (kind, got), spies, fake = compose(m, w, path, script=accepted)
                if accepted and (kind != "record" or not got["ok"]):
                    out.append(f"C3-cross {image} for {h}: the intended pair was not accepted ({kind})")
                if not accepted and (kind != "refused" or not isinstance(got, rt.Refused) or fake.calls):
                    out.append(f"C3-cross {image} for {h}: {kind} ({type(got).__name__}), {len(fake.calls)} calls")
            run_case(out, "C3-cross", f"{image}/{h}", case)
        return out

    @staticmethod
    def c3_non_take(m) -> list:
        """Criterion 3: the sidecar's and the egress proxy's locks never serve a take."""
        out = []
        for h in ARMS:
            for image in (il.SIDECAR_IMAGE, il.EGRESS_IMAGE):
                def case(h=h, image=image):
                    w = World(h)
                    box = LockBox()
                    path = box.put(image, ready_lock(image))
                    with box.active():
                        (kind, got), spies, fake = compose(m, w, path, script=False)
                    if kind != "refused" or not isinstance(got, rt.Refused) or fake.calls:
                        out.append(f"C3-non-take {image} for {h}: {kind} ({type(got).__name__})")
                run_case(out, "C3-non-take", f"{image}/{h}", case)
        return out

    @staticmethod
    def c4_mount(m) -> list:
        """Criterion 4: the sidecar's evidence mount source must be the folder preflight reads. Healthy data at A; a
        mount at B in either or both places, or probes at A judged as B, fails, and the record is not ok."""
        out = []

        def at_b(w, raw, where):
            b = tempfile.mkdtemp(prefix="w-")
            if where in ("both", "expect"):
                w.sidecar_expect["mounts"][1]["source"] = b
            if where in ("both", "inspect"):
                doc = json.loads(raw["sidecar-inspect"]["stdout"])
                doc[0]["Mounts"][1]["Source"] = b
                set_out(raw, "sidecar-inspect", doc)
            return b

        def case_baseline():
            w = World()
            with filled(mod=m):
                rec = m.evaluate(w.raw(), spec=w.spec, lock=w.lock, sidecar_expect=w.sidecar_expect,
                                 harness=w.harness, hosts=HOSTS, evidence_dir=w.ev, sidecar_lock=w.sidecar_lock, egress_lock=w.egress_lock)
            if failing(rec) or not rec["ok"]:
                out.append(f"C4-mount baseline: a world at A fails {failing(rec)}")
        run_case(out, "C4-mount", "baseline", case_baseline)
        for where in ("both", "expect", "inspect"):
            def case(where=where):
                w = World()
                raw = w.raw()
                at_b(w, raw, where)
                with filled(mod=m):
                    rec = m.evaluate(raw, spec=w.spec, lock=w.lock, sidecar_expect=w.sidecar_expect,
                                     harness=w.harness, hosts=HOSTS, evidence_dir=w.ev, sidecar_lock=w.sidecar_lock, egress_lock=w.egress_lock)
                if "sidecar-isolated" not in failing(rec) or rec["ok"]:
                    out.append(f"C4-mount {where} at B, probes at A: sidecar-isolated passed ({failing(rec)})")
            run_case(out, "C4-mount", where, case)

        def case_judged_b():
            w = World()
            raw = w.raw()
            b = at_b(w, raw, "both")
            with filled(mod=m):
                rec = m.evaluate(raw, spec=w.spec, lock=w.lock, sidecar_expect=w.sidecar_expect,
                                 harness=w.harness, hosts=HOSTS, evidence_dir=b, sidecar_lock=w.sidecar_lock, egress_lock=w.egress_lock)
            if "evidence-out-of-reach" not in failing(rec) or rec["ok"]:
                out.append(f"C4-probes mount at B, probes at A, judged as B: passed ({failing(rec)})")
        run_case(out, "C4-probes", "judged-b", case_judged_b)
        return out

    @staticmethod
    def c4_arg(m) -> list:
        """Criterion 4: evidence_dir is required and absolute; omitting it is never a compatibility bypass."""
        out = []
        w = World()
        raw = w.raw()
        base = dict(spec=w.spec, lock=w.lock, sidecar_expect=w.sidecar_expect, harness=w.harness, hosts=HOSTS,
                    sidecar_lock=w.sidecar_lock, egress_lock=w.egress_lock)
        for label, value in (("None", None), ("empty", ""), ("relative", "rec/ev"), ("dotted", w.ev + "/../ev"),
                             ("root", "/")):
            def case(label=label, value=value):
                with filled(mod=m):
                    try:
                        rec = m.evaluate(raw, evidence_dir=value, **base)
                    except rt.Refused:
                        return
                out.append(f"C4-arg {label}: accepted (ok={rec['ok']})")
            run_case(out, "C4-arg", label, case)

        def omitted():
            with filled(mod=m):
                try:
                    m.evaluate(raw, **base)
                except TypeError:
                    return
            out.append("C4-arg omitted: evaluate ran without evidence_dir")
        run_case(out, "C4-arg", "omitted", omitted)
        return out

    @staticmethod
    def c5_positive(m) -> list:
        """Criterion 5: expectation, inspect and probes all at A pass every check, and A itself (not a copy of the
        expectation) reaches the probes, the health read and evaluate."""
        out = []
        for h in ARMS:
            def case(h=h):
                w = World(h)
                box = LockBox()
                path = box.put(HARNESS_IMAGE[h], ready_lock(HARNESS_IMAGE[h], VERSION_OUT[h][2]))
                with box.active():
                    (kind, got), spies, fake = compose(m, w, path)
                if [p.get("evidence_dir") for p in spies["probes"]] != [w.ev]:
                    got_dirs = [p.get("evidence_dir") for p in spies["probes"]]
                    out.append(f"C5-probes-path {h}: probes received {got_dirs}")
                if [e.get("evidence_dir") for e in spies["evaluate"]] != [w.ev]:
                    out.append(f"C5-evaluate-path {h}: evaluate received "
                               f"{[e.get('evidence_dir') for e in spies['evaluate']]}")
                if spies["health"] != [os.path.join(w.ev, pf.HEALTH)]:
                    out.append(f"C5-health-path {h}: the health read was {spies['health']}")
                if [e.get("sidecar_expect") is w.sidecar_expect for e in spies["evaluate"]] != [True]:
                    out.append(f"C5-expect {h}: evaluate did not receive the sidecar's own expectation")
                if kind != "record" or failing(got) or not got["ok"]:
                    out.append(f"C5-record {h}: {kind}, failing {failing(got) if kind == 'record' else got}")
                if fake.unexpected or fake.script:
                    out.append(f"C5-record {h}: the runtime saw {len(fake.unexpected)} unexpected calls, "
                               f"{len(fake.script)} unasked")
            run_case(out, "C5", h, case)
        return out

    @staticmethod
    def c6_launched(m) -> list:
        """Criterion 6: Launched.spec (the network launch made) is the spec probed and evaluated, never the caller's
        pre-launch placeholder; the helper never launches, runs a turn or tears down."""
        out = []

        def case():
            w = World()
            self_check = rt.TakeSpec(**dict(w.spec.__dict__, network=PLACEHOLDER_NET))
            if self_check.network == w.spec.network:
                out.append("C6-launched-spec: the placeholder is the launched network (the test bites nothing)")
            box = LockBox()
            path = box.put("take-a", ready_lock("take-a", VERSION_OUT[rt.CLAUDE_CODE][2]))
            with box.active():
                (kind, got), spies, fake = compose(m, w, path)
            nets = [e["spec"].network for e in spies["evaluate"]] + [p["spec"].network for p in spies["probes"]]
            if nets != [ID["net"], ID["net"]]:
                out.append(f"C6-launched-spec: the probed/evaluated networks are {nets}, not the launched {ID['net']}")
            if kind != "record" or failing(got) or not got["ok"]:
                out.append(f"C6-launched-spec: {kind}, failing {failing(got) if kind == 'record' else got}")
            if spies["lifecycle"]:
                out.append(f"C6-lifecycle: reached {spies['lifecycle']}")
        run_case(out, "C6-launched-spec", "launched", case)
        return out

    @staticmethod
    def c6_absent(m) -> list:
        """Criterion 6: a launch record without spec or ids, not ok, or with its spec off its own network, refuses
        with no runtime call and no probe built."""
        out = []
        w0 = World()
        cases = {"no spec": dict(spec=None), "no take id": dict(take_id=None), "no sidecar id": dict(sidecar_id=None),
                 "not ok": dict(ok=False), "spec off its network": dict(network_id=PLACEHOLDER_NET),
                 "short take id": dict(take_id="d" * 12)}
        for label, edits in cases.items():
            def case(label=label, edits=edits):
                w = World()
                box = LockBox()
                path = box.put("take-a", ready_lock("take-a", VERSION_OUT[rt.CLAUDE_CODE][2]))
                with box.active():
                    (kind, got), spies, fake = compose(m, w, path, launched=launched_for(w, **edits), script=False)
                if kind != "refused" or not isinstance(got, rt.Refused) or fake.calls or spies["probes"] \
                        or spies["evaluate"]:
                    out.append(f"C6-absent {label}: {kind} ({type(got).__name__}), {len(fake.calls)} runtime calls")
            run_case(out, "C6-absent", label, case)

        def not_a_record():
            box = LockBox()
            path = box.put("take-a", ready_lock("take-a", VERSION_OUT[rt.CLAUDE_CODE][2]))
            with box.active():
                (kind, got), spies, fake = compose(m, w0, path, launched=launched_for(w0).to_record(), script=False)
            if kind != "refused" or not isinstance(got, rt.Refused) or fake.calls:
                out.append(f"C6-absent a dict for the record: {kind} ({type(got).__name__})")
        run_case(out, "C6-absent", "dict", not_a_record)
        return out


class TestLockSeam(unittest.TestCase):
    """Criteria 1-6, each green on box/preflight.py (the witnesses below turn each red)."""

    def test_c1_loader_really_used(self):
        self.assertEqual(LockSeam.c1_loader(pf), [])

    def test_c1_no_flattened_lock(self):
        self.assertEqual(LockSeam.c1_flat(pf), [])

    def test_c1_relative_path_to_a_valid_lock_refused(self):
        self.assertEqual(LockSeam.c1_relative(pf), [])

    def test_c2_closed_validation_survives(self):
        self.assertEqual(LockSeam.c2_closed(pf), [])

    def test_c2_pending_refused_before_the_runtime(self):
        self.assertEqual(LockSeam.c2_pending(pf), [])

    def test_c7_sidecar_lock_and_manifest(self):
        self.assertEqual(LockSeam.c7_sidecar(pf), [])

    def test_c8_egress_lock_and_manifest(self):
        self.assertEqual(LockSeam.c8_egress(pf), [])

    def test_o1_spelled_names_are_image_locks(self):
        """O-1: the egress names preflight spells are w4a's."""
        self.assertEqual(pf.EGRESS_LOCK_IMAGE, il.EGRESS_IMAGE)
        self.assertEqual(pf.EGRESS_LOCK_PATH, os.path.dirname(il.DOCKERFILES[il.EGRESS_IMAGE]) + "/image.lock")

    def test_lw7_spelled_names_are_image_locks(self):
        """LW-7: the names preflight spells (it reads image_lock only through load and require_ready) are w4a's."""
        self.assertEqual(pf.SIDECAR_LOCK_IMAGE, il.SIDECAR_IMAGE)
        self.assertEqual(pf.SIDECAR_LOCK_PATH, os.path.dirname(il.DOCKERFILES[il.SIDECAR_IMAGE]) + "/image.lock")
        self.assertEqual(pf.TAKE_LOCK_DIRS, {i: os.path.dirname(il.DOCKERFILES[i]) for i in il.TAKE_IMAGES})
        self.assertEqual(pf.IMAGE_ID_SHAPE.pattern, il.IMAGE_ID_RE.pattern)

    def test_c3_harness_image_binding(self):
        self.assertEqual(LockSeam.c3_cross(pf), [])

    def test_c3_no_sidecar_or_egress_lock_for_a_take(self):
        self.assertEqual(LockSeam.c3_non_take(pf), [])

    def test_c4_evidence_identity(self):
        self.assertEqual(LockSeam.c4_mount(pf), [])

    def test_c4_evidence_dir_required(self):
        self.assertEqual(LockSeam.c4_arg(pf), [])

    def test_c5_positive_composition(self):
        self.assertEqual(LockSeam.c5_positive(pf), [])

    def test_c6_launched_spec(self):
        self.assertEqual(LockSeam.c6_launched(pf), [])

    def test_c6_incomplete_launch_record(self):
        self.assertEqual(LockSeam.c6_absent(pf), [])

    def test_the_composition_names_no_lifecycle_or_adapter(self):
        """The helper's own source calls no launch, turn, teardown, subprocess or adapter (read by ast)."""
        src = open(pf.__file__, encoding="utf-8").read()
        fn = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)
              and n.name in ("collect_and_evaluate", "load_take_lock", "_launched_parts")]
        self.assertEqual(sorted(f.name for f in fn), ["_launched_parts", "collect_and_evaluate", "load_take_lock"])
        names = {n.attr if isinstance(n, ast.Attribute) else n.id for f in fn for n in ast.walk(f)
                 if isinstance(n, (ast.Attribute, ast.Name))}
        self.assertEqual(names & {"launch", "run_turn", "teardown", "kill_agent", "subprocess", "agent_adapter",
                                  "exec_argv", "DockerRuntime"}, set())


# ------------------------------------------------------------------------------------ criterion 7: nothing dropped
# Every test of this module at the base 89b54db4 (Ran 20, OK), by id: each must still exist and still run.
BASE_TESTS = (
    "TestEvaluate.test_all_green_every_arm", "TestEvaluate.test_each_check_catches_its_breaks",
    "TestEvaluate.test_each_check_mutant_red", "TestEvaluate.test_missing_probe_fails",
    "TestEvaluate.test_run_records_failures", "TestEvaluate.test_run_tree_path_neutral",
    "TestExpectedInspect.test_bound_to_create", "TestExpectedInspect.test_mismatch_refuses_pending_and_wrong_keys",
    "TestHostIndependence.test_host_temp_root_is_never_read",
    "TestPending.test_no_parameter_overrides_a_pending_constant", "TestPending.test_pending",
    "TestProcessGuard.test_guard_is_armed", "TestProcessGuard.test_module_is_this_rounds",
    "TestProcessGuard.test_the_guard_starts_no_patch_at_import", "TestProcessesProgram.test_literal_refused_names",
    "TestProcessesProgram.test_processes_program", "TestPrograms.test_programs",
    "TestRecordAndPostflight.test_postflight", "TestRecordAndPostflight.test_write_beside_evidence",
    "TestShape.test_shape",
)
# The breaks per check at the base: each check keeps at least these (a fold may add, never drop).
BASE_BREAKS = {"agent-non-root": 9, "image-matches-lock": 3, "harness-version-matches-lock": 4,
               "take-inspect-matches-spec": 20, "limits-apply": 5, "evidence-out-of-reach": 3,
               "watcher-invisible": 6, "sidecar-isolated": 15, "watcher-started": 2, "watcher-capability": 5,
               "consequential-paths-readable": 4, "no-container-socket": 4, "egress-allowed-host": 2,
               "egress-other-host-refused": 2, "egress-direct-refused": 1, "names-do-not-resolve": 5,
               "study-folders-absent": 2, "run-tree-path-neutral": 0,
               # PF1-L3 (m9, 24 Oct 2026): added, the base's eighteen kept
               "egress-raw-ip-refused": 5, "egress-metadata-refused": 2, "egress-gateway-refused": 7}


class TestNothingDropped(unittest.TestCase):
    def test_every_base_test_still_runs(self):
        loaded = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])

        def ids(suite):
            for t in suite:
                if isinstance(t, unittest.TestSuite):
                    yield from ids(t)
                else:
                    yield t
        tests = {f"{type(t).__name__}.{t._testMethodName}": t for t in ids(loaded)}
        self.assertEqual([b for b in BASE_TESTS if b not in tests], [])
        flagged = [k for k, t in tests.items()
                   if getattr(type(t), "__unittest_skip__", False)
                   or getattr(getattr(t, t._testMethodName), "__unittest_skip__", False)
                   or getattr(getattr(t, t._testMethodName), "__unittest_expecting_failure__", False)]
        self.assertEqual(flagged, [])

    def test_every_base_break_still_runs(self):
        self.assertEqual(list(BREAKS), list(BASE_BREAKS))
        self.assertEqual([c for c, n in BASE_BREAKS.items() if len(BREAKS[c]) < n], [])
        self.assertEqual(pf.PREFLIGHT_CHECKS, tuple(BASE_BREAKS))


# --------------------------------------------------------------------------------- criterion 8: the six witnesses
class WitnessNotPerformed(AssertionError):
    pass


def witness_module(edits: tuple, extra: dict | None = None) -> types.ModuleType:
    """box/preflight.py with `edits` applied, compiled in memory as its own module (never written to disk). Every
    anchor must occur exactly once, or the witness was not performed."""
    with open(pf.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    name = pf.__name__ + "_witness"
    mod = types.ModuleType(name)
    mod.__file__ = pf.__file__
    mod.__dict__.update(extra or {})
    sys.modules[name] = mod
    try:
        exec(compile(src, pf.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    return mod


PRE_LAUNCH_SPEC = rt.TakeSpec(image=IMAGE, run_tree=os.path.join(World.FAKE_ROOT, "tree"),
                              config_dir=os.path.join(World.FAKE_ROOT, "cfg"), network=PLACEHOLDER_NET,
                              memory_reservation=512 * 2 ** 20, memory=3 * 512 * 2 ** 20, cpus="2", pids_limit=256)

# name: (edits to box/preflight.py, the bound check, the line prefix that is its own assertion, injected names)
WITNESSES = {
    "omit-load": ((("    lock = image_lock.load(lock_path)\n",
                    "    with open(lock_path, encoding=\"utf-8\") as fh:\n        lock = json.loads(fh.read())\n"),),
                  LockSeam.c1_loader, "C1-loader-spy", None),
    "omit-absolute-path-rule": ((("    lock_path = run_take._abs_path(lock_path, \"lock_path\")\n", ""),),
                                LockSeam.c1_relative, "C1-relative", None),
    "omit-readiness": ((("    image_lock.require_ready(lock)\n", ""),), LockSeam.c2_pending, "C2-pending", None),
    "omit-harness-image-binding": ((("    if lock[\"image\"] != TAKE_IMAGE[harness]:\n", "    if False:\n"),),
                                   LockSeam.c3_cross, "C3-cross", None),
    "drop-mount-source-comparison": ((("    _need(not _evidence_source_problems(exp, evidence_dir), ",
                                       "    _need(True or not _evidence_source_problems(exp, evidence_dir), "),),
                                     LockSeam.c4_mount, "C4-mount", None),
    "probes-at-another-evidence-path": ((("evidence_dir=evidence_dir)\n    raw = run(",
                                          "evidence_dir=os.path.dirname(evidence_dir))\n    raw = run("),),
                                        LockSeam.c5_positive, "C5-probes-path", None),
    "pre-launch-spec": ((("    spec, take_id, sidecar_id = _launched_parts(launched)\n",
                          "    _, take_id, sidecar_id = _launched_parts(launched)\n    spec = PRE_LAUNCH_SPEC\n"),),
                        LockSeam.c6_launched, "C6-launched-spec", {"PRE_LAUNCH_SPEC": PRE_LAUNCH_SPEC}),
    # LW-7 (lock-writer review, 14 Oct 2026): the sidecar's lock and platform manifest.
    "lw7-sidecar-manifest-not-compared": ((("    _need(side == side_want, ", "    _need(True or side == side_want, "),),
                                          LockSeam.c7_sidecar, "C7-sidecar", None),
    "lw7-sidecar-readiness-omitted": ((("    image_lock.require_ready(side)\n", ""),),
                                      LockSeam.c7_sidecar, "C7-sidecar", None),
    "lw7-sidecar-lock-not-loaded": ((("    sidecar_lock = load_sidecar_lock(lock_path, harness=harness)\n",
                                      "    sidecar_lock = {\"image_id\": sidecar.expect[\"image\"], "
                                      "\"manifest_digest\": SIDE}\n"),),
                                    LockSeam.c7_sidecar, "C7-sidecar", {"SIDE": SIDE_MANIFEST}),
}
LW7_WITNESSES = ("lw7-sidecar-manifest-not-compared", "lw7-sidecar-readiness-omitted", "lw7-sidecar-lock-not-loaded")
# O-1 (glitch-06, 14 Oct 2026): the egress proxy's image, as LW-7 did the sidecar's.
WITNESSES.update({
    "o1-egress-manifest-not-compared": ((("    _need(egress == egress_want, ", "    _need(True or egress == egress_want, "),),
                                        LockSeam.c8_egress, "C8-egress", None),
    "o1-egress-launch-image-not-compared": ((("    _need(_value(raw, \"egress-launch\") == egress_id, ",
                                              "    _need(True or _value(raw, \"egress-launch\") == egress_id, "),),
                                            LockSeam.c8_egress, "C8-egress", None),
    "o1-egress-readiness-omitted": ((("    image_lock.require_ready(egress_lock)\n", ""),),
                                    LockSeam.c8_egress, "C8-egress", None),
})
O1_WITNESSES = ("o1-egress-manifest-not-compared", "o1-egress-launch-image-not-compared", "o1-egress-readiness-omitted")
WITNESS_LOG: list = []


class TestWitnesses(unittest.TestCase):
    """Criterion 8: each witness is killed only by its bound check's own assertion (a line with its prefix), with the
    bound check green on the real module first; an ERROR line, a raise, an unperformed edit or a skip is never a
    kill. Every other line the bound check prints under the witness is listed as collateral, never credited."""

    def kill(self, name):
        edits, check, prefix, extra = WITNESSES[name]
        self.assertEqual(check(pf), [], f"{name}: the bound check is not green on box/preflight.py")
        mod = witness_module(edits, extra)
        got = check(mod)
        errors = [p for p in got if p.startswith("ERROR")]
        own = [p for p in got if p.startswith(prefix + " ") or p.startswith(prefix + ":")]
        collateral = [p for p in got if p not in own and p not in errors]
        line = (f"WITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
                f"{len(collateral)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ")
        WITNESS_LOG.append(line)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_omit_load(self):
        self.kill("omit-load")

    def test_witness_omit_absolute_path_rule(self):
        self.kill("omit-absolute-path-rule")

    def test_witness_omit_readiness(self):
        self.kill("omit-readiness")

    def test_witness_omit_harness_image_binding(self):
        self.kill("omit-harness-image-binding")

    def test_witness_drop_mount_source_comparison(self):
        self.kill("drop-mount-source-comparison")

    def test_witness_probes_at_another_evidence_path(self):
        self.kill("probes-at-another-evidence-path")

    def test_witness_pre_launch_spec(self):
        self.kill("pre-launch-spec")

    def test_witness_lw7_sidecar_manifest_not_compared(self):
        self.kill("lw7-sidecar-manifest-not-compared")

    def test_witness_lw7_sidecar_readiness_omitted(self):
        self.kill("lw7-sidecar-readiness-omitted")

    def test_witness_lw7_sidecar_lock_not_loaded(self):
        self.kill("lw7-sidecar-lock-not-loaded")

    def test_witness_o1_egress_manifest_not_compared(self):
        self.kill("o1-egress-manifest-not-compared")

    def test_witness_o1_egress_launch_image_not_compared(self):
        self.kill("o1-egress-launch-image-not-compared")

    def test_witness_o1_egress_readiness_omitted(self):
        self.kill("o1-egress-readiness-omitted")

    def test_the_witnesses_are_named(self):
        """The readiness note's six, plus W6A-R1-1's absolute-path witness, each bound to its own check; plus the
        three LW-7 witnesses, all bound to the sidecar-lock check c7_sidecar."""
        self.assertEqual(sorted(WITNESSES), sorted(["omit-load", "omit-readiness", "omit-harness-image-binding",
                                                    "drop-mount-source-comparison",
                                                    "probes-at-another-evidence-path", "pre-launch-spec",
                                                    "omit-absolute-path-rule", *LW7_WITNESSES, *O1_WITNESSES]))
        bound = {n: w[1].__name__ for n, w in WITNESSES.items() if n not in LW7_WITNESSES + O1_WITNESSES}
        self.assertEqual(len(set(bound.values())), 7, bound)
        self.assertEqual({WITNESSES[n][1].__name__ for n in LW7_WITNESSES}, {"c7_sidecar"})
        self.assertEqual({WITNESSES[n][1].__name__ for n in O1_WITNESSES}, {"c8_egress"})


# Taken last, after every import-time statement of this module: must be empty (setUpModule arms the guard).
_PATCHED_AT_IMPORT = _patched_now()


if __name__ == "__main__":
    unittest.main(verbosity=2)
