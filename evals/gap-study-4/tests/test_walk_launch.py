#!/usr/bin/env python3
"""box/walk_launch.py: the CP6 walk's launch road (glitch-6b's ruling of 15 Oct 2026, item 3), on fakes. Local git runs
for real on temporary repositories; athena is a fake that keeps what was copied to it and answers each remote command
by its shape; gitleaks is a fake that writes the report it is told to. No ssh, no scp, no suite, no model.

  L1-ship     the Mac pre-check first, then the pinned history, the bundle, its verify and its clone, the scan, and only
              then anything on athena; a finding outside the known public history keeps the bundle on the Mac; the
              athena copy and athena-reserve are each read back by sha256; athena's clone must sit at the head
  L2-run      the one remote command: umask 0022 first; the reservation must be absent and the athena gate open before
              the hold; the walk runs under `athena-reserve hold --by gap4-walk-<id>` with exactly the gate's three
              variables, its own hold among them; nohup with its pid and exit recorded
  L3-fetch    nothing is fetched while the walk runs or when it made no commit; the back bundle is the new commits only
              (<head>..<ref>), read back by sha256, scanned with no allowance over exactly <head>..<tip>, then fetched
              into the records clone as walk/<child>; a finding fetches nothing
  L4-bounds   no argv anywhere carries push, a credential file or the walk's login file; the child is a neutral
              /home/javier/w-XXXXXXXX folder; KNOWN_HISTORY_FINDINGS' commits are in this repository's history

Witnesses (each red by its own clause): scan-skipped, unknown-finding-admitted, no-umask, hold-dropped,
reservation-not-checked, back-range-whole-history, back-scan-allowance.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from box import walk_launch as wl  # noqa: E402

CHILD = "/home/javier/w-AbCd1234"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
           "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp")}


def git(*argv, cwd=None):
    return subprocess.run(["git", *argv], cwd=cwd, env=GIT_ENV, capture_output=True, text=True, check=True).stdout


def make_repo(t, commits=2):
    repo = os.path.join(t, "repo")
    os.mkdir(repo)
    git("init", "-q", "-b", "main", repo)
    git("-C", repo, "config", "maintenance.auto", "false")
    for i in range(commits):
        Path(repo, f"f{i}.txt").write_text(f"{i}\n")
        git("-C", repo, "add", f"f{i}.txt")
        git("-C", repo, "commit", "-q", "-m", f"c{i}")
    root = git("-C", repo, "rev-list", "--max-parents=0", "HEAD").strip()
    return repo, root, git("-C", repo, "rev-parse", "HEAD").strip()


class FakeRunner(wl.Runner):
    """Real local git (with GIT_ENV); a fake gitleaks; a fake athena keyed by command shape."""

    def __init__(self, *, findings=(), back_findings=(), athena_head=None, athena_tip=None, walk_state="exit=0",
                 back_bundle=None):
        self.calls = []
        self.findings, self.back_findings = list(findings), list(back_findings)
        self.athena_head, self.athena_tip, self.walk_state = athena_head, athena_tip, walk_state
        self.back_bundle = back_bundle
        self.files = {}

    def local(self, argv, *, timeout=3600):
        argv = list(argv)
        self.calls.append(("local", argv))
        if argv[0] == "gitleaks":
            report = argv[argv.index("--report-path") + 1]
            found = self.back_findings if "--log-opts" in argv else self.findings
            Path(report).write_text(json.dumps([{"Fingerprint": f, "RuleID": "x"} for f in found]))
            return (1 if found else 0), "", ""
        if argv[0] == "git":
            p = subprocess.run(argv, env=GIT_ENV, capture_output=True, text=True)
            return p.returncode, p.stdout, p.stderr
        return 0, "", ""

    def remote(self, cmd, *, timeout=3600):
        self.calls.append(("remote", cmd))
        if cmd.startswith("umask 077; mktemp -d"):
            return 0, CHILD + "\n", ""
        if cmd.startswith("sha256sum "):
            path = cmd.split()[1]
            src = self.files.get(path)
            return (0, hashlib.sha256(Path(src).read_bytes()).hexdigest() + "  " + path + "\n", "") if src else (1, "", "")
        if cmd.startswith("git clone -q -b"):
            return 0, "", ""
        if cmd.endswith("/repo rev-parse HEAD"):
            return 0, (self.athena_head or "") + "\n", ""
        if " rev-parse --verify " in cmd:
            return 0, (self.athena_tip or "") + "\n", ""
        if " merge-base --is-ancestor " in cmd:
            return 0, "", ""
        if " bundle create " in cmd:
            self.files[f"{CHILD}/walk-back.bundle"] = self.back_bundle
            return 0, "", ""
        if cmd.startswith("if kill -0"):
            return 0, self.walk_state + "\n", ""
        if "walk.pid; cat " in cmd:
            return 0, "4242\n", ""
        return 0, "", ""

    def copy_to(self, src, dst):
        self.calls.append(("copy_to", [src, dst]))
        self.files[dst] = src
        return 0, "", ""

    def copy_from(self, src, dst):
        self.calls.append(("copy_from", [src, dst]))
        Path(dst).write_bytes(Path(self.files[src]).read_bytes())
        return 0, "", ""


def reserve_file(t):
    p = os.path.join(t, "athena-reserve")
    Path(p).write_text("# synthetic\n")
    return p


def ship_rig(mod, t, **kw):
    repo, root, head = make_repo(t)
    runner = FakeRunner(athena_head=head, **kw)
    reserve = reserve_file(t)
    with mock.patch.object(mod, "PINNED_TREE", root), \
            mock.patch.object(mod, "RESERVE_SHA256", hashlib.sha256(Path(reserve).read_bytes()).hexdigest()):
        try:
            out = mod.ship(runner, repo=repo, ref="main", suite="/x/athena_suite.py", reserve=reserve,
                           gitleaks="gitleaks", work=os.path.join(t, "work"), precheck=lambda s: [])
        except mod.LaunchRefused as e:
            out = e
    return runner, out, head


def l1(mod) -> list:
    out = []
    with tempfile.TemporaryDirectory() as t:
        runner, got, head = ship_rig(mod, t)
        if not isinstance(got, dict) or got.get("child") != CHILD or got.get("head") != head:
            return [f"L1-ship: a clean ship did not complete: {got}"]
        first_remote = next(i for i, c in enumerate(runner.calls) if c[0] != "local")
        scan = next((i for i, c in enumerate(runner.calls) if c[0] == "local" and c[1][0] == "gitleaks"), None)
        if scan is None or scan > first_remote:
            out.append("L1-ship: athena is touched before the bundle is scanned")
        locals_ = [c[1] for c in runner.calls if c[0] == "local"]
        if not any(a[3:5] == ["bundle", "verify"] for a in locals_):
            out.append("L1-ship: the bundle is not verified")
        reads = [c[1] for c in runner.calls if c[0] == "remote" and c[1].startswith("sha256sum ")]
        if reads != [f"sha256sum {CHILD}/walk-out.bundle", f"sha256sum {CHILD}/athena-reserve"]:
            out.append("L1-ship: the athena copies are not each read back by sha256")
    with tempfile.TemporaryDirectory() as t:
        _, got, _ = ship_rig(mod, t, findings=["deadbeef:x.txt:generic-api-key:1"])
        if not isinstance(got, mod.LaunchRefused):
            out.append("L1-ship: a finding outside the known public history ships")
    with tempfile.TemporaryDirectory() as t:
        known = sorted(mod.KNOWN_HISTORY_FINDINGS)[:2]
        runner, got, _ = ship_rig(mod, t, findings=known)
        if not isinstance(got, dict):
            out.append(f"L1-ship: a known public finding refuses the bundle: {got}")
    with tempfile.TemporaryDirectory() as t:
        runner2 = FakeRunner(athena_head="0" * 40)
        repo, root, head = make_repo(t)
        reserve = reserve_file(t)
        with mock.patch.object(mod, "PINNED_TREE", root), \
                mock.patch.object(mod, "RESERVE_SHA256", hashlib.sha256(Path(reserve).read_bytes()).hexdigest()):
            try:
                mod.ship(runner2, repo=repo, ref="main", suite="/x", reserve=reserve, gitleaks="gitleaks",
                         work=os.path.join(t, "w2"), precheck=lambda s: [])
                out.append("L1-ship: an athena clone off the head is admitted")
            except mod.LaunchRefused:
                pass
            try:
                mod.ship(FakeRunner(athena_head=head), repo=repo, ref="main", suite="/x", reserve=reserve,
                         gitleaks="gitleaks", work=os.path.join(t, "w3"), precheck=lambda s: ["a suite runs"])
                out.append("L1-ship: a closed Mac pre-check ships")
            except mod.LaunchRefused:
                pass
        with mock.patch.object(mod, "PINNED_TREE", "1" * 40), \
                mock.patch.object(mod, "RESERVE_SHA256", hashlib.sha256(Path(reserve).read_bytes()).hexdigest()):
            r4 = FakeRunner(athena_head=head)
            try:
                mod.ship(r4, repo=repo, ref="main", suite="/x", reserve=reserve, gitleaks="gitleaks",
                         work=os.path.join(t, "w4"), precheck=lambda s: [])
                out.append("L1-ship: a head without the pinned tree's history ships")
            except mod.LaunchRefused:
                if any(c[0] != "local" for c in r4.calls):
                    out.append("L1-ship: athena is touched before the pinned-history check")
        try:
            mod.ship(FakeRunner(athena_head=head), repo=repo, ref="main", suite="/x", reserve=reserve,
                     gitleaks="gitleaks", work=os.path.join(t, "w5"), precheck=lambda s: [])
            out.append("L1-ship: athena-reserve bytes off the runbook's pin ship")
        except mod.LaunchRefused:
            pass
    return out


def l2(mod) -> list:
    out = []
    cell = {"task": "plan-gate", "half": "positive", "wording": "w1", "arm": "A", "model": "claude-x"}
    cmd = mod.run_command(child=CHILD, walk="w-0001", cell=cell, reason="the first walk")
    if not cmd.startswith("umask 0022;"):
        out.append("L2-run: the remote command does not open with umask 0022")
    i_test = cmd.find(f"test ! -e {mod.RESERVATION}")
    i_gate = cmd.find("machine_gate.py athena-check")
    i_hold = cmd.find("athena-reserve hold --by gap4-walk-w-0001")
    if min(i_test, i_gate, i_hold) < 0 or not i_test < i_gate < i_hold:
        out.append("L2-run: the reservation check and the athena gate do not both come before the hold")
    held = cmd[i_hold:]
    for name, value in ((mod.machine_gate.ENV_ACCOUNT, "athena-suite"),
                        (mod.machine_gate.ENV_RESERVATION, mod.RESERVATION),
                        (mod.machine_gate.ENV_HOLD, "gap4-walk-w-0001")):
        if f"{name}={value}" not in held or f"{name}={value}" not in cmd[i_test:i_gate]:
            out.append(f"L2-run: {name} is not {value} for both the gate and the walk")
    toks = shlex.split(cmd)
    body = shlex.split(toks[toks.index("-c") + 1]) if "-c" in toks else []
    want = ["walk_runner.py", "--walk", "w-0001", "--task", "plan-gate", "--half", "positive", "--wording", "w1",
            "--arm", "A", "--model", "claude-x", "--reason", "the first walk;"]
    tail = [os.path.basename(x) if x.endswith("walk_runner.py") else x for x in body]
    if not any(tail[i:i + len(want)] == want for i in range(len(tail))):
        out.append("L2-run: the walk's argv is not the cell's")
    if "nohup sh -c" not in cmd or "walk.pid" not in cmd or "walk.exit" not in cmd:
        out.append("L2-run: the walk is not detached with its pid and exit recorded")
    runner = FakeRunner()
    try:
        if mod.run(runner, child=CHILD, walk="w-0001", cell=cell, reason="r") != 4242:
            out.append("L2-run: the pid is not read")
    except mod.LaunchRefused as e:
        out.append(f"L2-run: the start refused on the fake athena: {e}")
    for bad in ({"child": "/home/javier/gap4-x", "walk": "w-0001"}, {"child": CHILD, "walk": "a/b"}):
        try:
            mod.run_command(cell=cell, reason="r", **bad)
            out.append(f"L2-run: {bad} is admitted")
        except mod.LaunchRefused:
            pass
    return out


def fetch_rig(mod, t, *, walk_state="exit=0", commit_on_athena=True, back_findings=()):
    repo, root, head = make_repo(t)
    athena = os.path.join(t, "athena-repo")
    git("clone", "-q", repo, athena)
    if commit_on_athena:
        Path(athena, "walk.txt").write_text("walk\n")
        git("-C", athena, "add", "walk.txt")
        git("-C", athena, "commit", "-q", "-m", "walk")
    tip = git("-C", athena, "rev-parse", "HEAD").strip()
    back = os.path.join(t, "athena-back.bundle")
    if commit_on_athena:
        git("-C", athena, "bundle", "create", back, f"{head}..main")
    runner = FakeRunner(athena_tip=tip, walk_state=walk_state, back_bundle=back, back_findings=back_findings)
    try:
        got = mod.fetch(runner, child=CHILD, head=head, ref="main", records=repo, gitleaks="gitleaks",
                        work=os.path.join(t, "work"))
    except mod.LaunchRefused as e:
        got = e
    return runner, got, repo, head, tip


def l3(mod) -> list:
    out = []
    with tempfile.TemporaryDirectory() as t:
        runner, got, repo, head, tip = fetch_rig(mod, t)
        if not isinstance(got, dict) or got.get("fetched") != tip:
            return [f"L3-fetch: a clean fetch did not complete: {got}"]
        if git("-C", repo, "rev-parse", "refs/heads/walk/w-AbCd1234").strip() != tip:
            out.append("L3-fetch: the records clone does not hold the walk's tip")
        creates = [c[1] for c in runner.calls if c[0] == "remote" and " bundle create " in c[1]]
        if creates != [f"git -C {CHILD}/repo bundle create {CHILD}/walk-back.bundle {head}..main"]:
            out.append("L3-fetch: the back bundle is not exactly the new commits")
        scans = [c[1] for c in runner.calls if c[0] == "local" and c[1][0] == "gitleaks"]
        if len(scans) != 1 or scans[0][scans[0].index("--log-opts") + 1] != f"{head}..{tip}":
            out.append("L3-fetch: the back scan is not exactly <head>..<tip>")
        i_scan = next(i for i, c in enumerate(runner.calls) if c[0] == "local" and c[1][0] == "gitleaks")
        i_rec = next(i for i, c in enumerate(runner.calls) if c[0] == "local" and c[1][:3] == ["git", "-C", repo]
                     and "fetch" in c[1])
        if not i_scan < i_rec:
            out.append("L3-fetch: the records clone is fetched before the scan")
    with tempfile.TemporaryDirectory() as t:
        _, got, repo, _, _ = fetch_rig(mod, t, back_findings=[sorted(mod.KNOWN_HISTORY_FINDINGS)[0]])
        if not isinstance(got, mod.LaunchRefused):
            out.append("L3-fetch: a finding in the walk's commits is fetched (no allowance comes back)")
        elif git("-C", repo, "for-each-ref", "refs/heads/walk/").strip():
            out.append("L3-fetch: a refused fetch left a walk branch")
    with tempfile.TemporaryDirectory() as t:
        _, got, _, _, _ = fetch_rig(mod, t, walk_state="running")
        if not isinstance(got, mod.LaunchRefused):
            out.append("L3-fetch: a running walk is fetched")
    with tempfile.TemporaryDirectory() as t:
        _, got, _, _, _ = fetch_rig(mod, t, commit_on_athena=False)
        if not isinstance(got, dict) or got.get("fetched") is not None:
            out.append("L3-fetch: a walk with no commit is not reported as nothing to fetch")
    return out


def l4(mod) -> list:
    out = []
    with tempfile.TemporaryDirectory() as t:
        r1, _, _ = ship_rig(mod, t)
    with tempfile.TemporaryDirectory() as t:
        r2, _, _, _, _ = fetch_rig(mod, t)
    cell = {"task": "t", "half": "h", "wording": "w", "arm": "A", "model": "m"}
    words = [json.dumps(c) for c in r1.calls + r2.calls] + [mod.run_command(child=CHILD, walk="w", cell=cell,
                                                                            reason="r")]
    for w in words:
        if re.search(r"\bpush\b", w) or re.search(r"claude-walk-token|gap4-secrets|auth\.json|\.env\b", w):
            out.append(f"L4-bounds: an argv carries a push or a login: {w[:120]}")
            break
    for bad in ("/home/javier/x", "/home/javier/w-abc", "/tmp/w-AbCd1234", CHILD + "/.."):
        try:
            mod._child(bad)
            out.append(f"L4-bounds: {bad!r} is admitted as a child")
        except mod.LaunchRefused:
            pass
    repo = HERE.parent.parent
    for fp in mod.KNOWN_HISTORY_FINDINGS:
        commit = fp.split(":")[0]
        p = subprocess.run(["git", "-C", str(repo), "cat-file", "-t", commit], capture_output=True, text=True)
        if p.returncode != 0 or p.stdout.strip() != "commit":
            out.append(f"L4-bounds: known finding commit {commit[:12]} is not in this repository's history")
    return out


CHECKS = {"L1-ship": l1, "L2-run": l2, "L3-fetch": l3, "L4-bounds": l4}


def witness(edits) -> types.ModuleType:
    src = Path(wl.__file__).read_text(encoding="utf-8")
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"witness not performed: {old[:60]!r} occurs {src.count(old)} times")
        src = src.replace(old, new)
    mod = types.ModuleType("walk_launch_witness")
    mod.__file__ = wl.__file__
    exec(compile(src, wl.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


WITNESSES = {
    "scan-skipped": ((("    unknown = sorted(set(scan_findings(runner, gitleaks, scan_clone, os.path.join(work, "
                       "\"out-scan.json\")))\n                     - KNOWN_HISTORY_FINDINGS)",
                       "    unknown = []"),), "L1-ship"),
    "unknown-finding-admitted": ((("    if unknown:\n        raise LaunchRefused(f\"gitleaks found",
                                   "    if False:\n        raise LaunchRefused(f\"gitleaks found"),), "L1-ship"),
    "no-umask": ((("    return (f\"umask {UMASK}; set -e;", "    return (f\"set -e;"),), "L2-run"),
    "hold-dropped": ((("    held = (f\"python3 {child}/athena-reserve hold --by {hid} -- {env} \"",
                       "    held = (f\"{env} \""),), "L2-run"),
    "reservation-not-checked": ((("set -e; test ! -e {RESERVATION}; {gate}", "set -e; {gate}"),), "L2-run"),
    "back-range-whole-history": ((("bundle create {child}/walk-back.bundle {head}..{shlex.quote(ref)}",
                                   "bundle create {child}/walk-back.bundle {shlex.quote(ref)}"),), "L3-fetch"),
    "back-scan-allowance": ((("    if found:\n        raise LaunchRefused(f\"gitleaks found {len(found)} finding(s) in "
                              "the walk's",
                              "    if set(found) - KNOWN_HISTORY_FINDINGS:\n        raise LaunchRefused(f\"gitleaks "
                              "found {len(found)} finding(s) in the walk's"),), "L3-fetch"),
}


class TestTheRoad(unittest.TestCase):
    def test_l1_ship(self):
        self.assertEqual(l1(wl), [])

    def test_l2_run(self):
        self.assertEqual(l2(wl), [])

    def test_l3_fetch(self):
        self.assertEqual(l3(wl), [])

    def test_l4_bounds(self):
        self.assertEqual(l4(wl), [])

    def test_pinned_tree_is_variants(self):
        import variants
        self.assertEqual(wl.PINNED_TREE, variants.PINNED_TREE)

    def test_reserve_pin_is_the_runbooks(self):
        self.assertTrue(wl.RESERVE_SHA256.startswith("efeecb3a"))


class TestWitnesses(unittest.TestCase):
    def test_every_witness_is_red_by_its_own_clause(self):
        for name, (edits, clause) in WITNESSES.items():
            with self.subTest(name=name):
                self.assertEqual(CHECKS[clause](wl), [], f"{name}: {clause} is not green on the tree")
                got = CHECKS[clause](witness(edits))
                self.assertTrue([x for x in got if x.startswith(clause + ":")], f"{name}: survived")


if __name__ == "__main__":
    unittest.main()
