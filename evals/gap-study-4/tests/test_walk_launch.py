#!/usr/bin/env python3
"""box/walk_launch.py: the CP6 walk's launch road (glitch-6b's ruling of 15 Oct 2026, item 3), on fakes. Local git runs
for real on temporary repositories; athena is a fake that keeps what was copied to it and answers each remote command
by its shape; gitleaks is a fake that writes the report it is told to. No ssh, no scp, no suite, no model.

  L1-ship     the Mac pre-check first, then the pinned history, the bundle and its verify, then athena_suite's own
              outward rule (scan_unpublished over every commit the public GARS remote does not serve, after its
              public fetch, with the push door's rulings and the committed allowlist), and only then anything on
              athena; a finding in a non-public commit, an unreadable or empty public-ref list and a secret-shaped
              file each keep the bundle on the Mac; the
              athena copy and athena-reserve are each read back by sha256; athena's clone must sit at the head
  L2-run      the one remote command: umask 0022 first; the reservation must be absent and the athena gate open before
              the hold; the walk runs under `athena-reserve hold --by gap4-walk-<id>` with exactly the gate's three
              variables, its own hold among them; nohup with its pid and exit recorded
  L3-fetch    nothing is fetched while the walk runs or when it made no commit; the back bundle is the new commits only
              (<head>..<ref>), read back by sha256, scanned with no allowance over exactly <head>..<tip>, then fetched
              into the records clone as walk/<child>; a finding fetches nothing
  L4-bounds   no argv anywhere carries push, a credential file or the walk's login file; the child is a neutral
              /home/javier/w-XXXXXXXX folder

Witnesses (each red by its own clause): scan-skipped, public-error-swallowed, public-subtraction-dropped,
no-umask, hold-dropped,
claim-dropped, claim-not-exclusive, claim-left-on-closed-gate, back-range-whole-history, back-scan-allowance,
back-scan-plain, and one per unexercised guard (MINOR 5).
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
import textwrap
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
        self.sha_override = {}          # a path whose sha256 athena misreports (the read-back guards)
        self.ancestor_rc = 0            # merge-base --is-ancestor's exit on athena
        self.listheads_override = None  # what `git bundle list-heads` prints, when set

    def local(self, argv, *, timeout=3600):
        argv = list(argv)
        self.calls.append(("local", argv))
        if argv[0] == "gitleaks":
            report = argv[argv.index("--report-path") + 1]
            found = self.back_findings if "--log-opts" in argv else self.findings
            Path(report).write_text(json.dumps([{"Fingerprint": f, "RuleID": "x"} for f in found]))
            return (1 if found else 0), "", ""
        if argv[0] == "git":
            if argv[1:3] == ["bundle", "list-heads"] and self.listheads_override is not None:
                return 0, self.listheads_override, ""
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
            if path in self.sha_override:
                return 0, self.sha_override[path] + "  " + path + "\n", ""
            return (0, hashlib.sha256(Path(src).read_bytes()).hexdigest() + "  " + path + "\n", "") if src else (1, "", "")
        if cmd.startswith("git clone -q -b"):
            return 0, "", ""
        if cmd.endswith("/repo rev-parse HEAD"):
            return 0, (self.athena_head or "") + "\n", ""
        if " rev-parse --verify " in cmd:
            return 0, (self.athena_tip or "") + "\n", ""
        if " merge-base --is-ancestor " in cmd:
            return self.ancestor_rc, "", ""
        if " bundle create " in cmd:
            self.files[f"{CHILD}/walk-back.bundle"] = self.back_bundle
            return 0, "", ""
        if cmd.startswith("if kill -0"):
            return 0, self.walk_state + "\n", ""
        if cmd.rstrip().endswith("/walk.pid") and "nohup sh -c" in cmd:
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


class FakeSuite:
    """athena_suite's functions as outward_scan calls them, logging into the runner's call list."""
    ALLOWLIST = "/fake/athena_suite_allowlist.json"
    PUBLIC_REFERENCE = {"gars": "https://example.invalid/gars.git"}

    def __init__(self, log, *, public=("a" * 40,), public_error=False, nonpublic_finding=False, hits=(), scanned=3):
        self.log, self.public, self.public_error = log, list(public), public_error
        self.scans, self.scanned = [], scanned
        self.nonpublic_finding, self.hits = nonpublic_finding, list(hits)

    def committed_allowlist(self, path):
        self.log.append(("suite", ["committed_allowlist", path]))
        return {"v": 1}, "f" * 64

    def validate_allowlist(self, doc, kind):
        self.log.append(("suite", ["validate_allowlist", kind]))
        return (), {"r": 1}, {"m": 1}

    def scratch_clone(self, bundle, dest, workdir):
        self.log.append(("suite", ["scratch_clone", bundle, dest]))

    def name_hits(self, repo, sha, allow):
        return list(self.hits)

    def exempt_reviewed(self, repo, sha, hits, reviewed):
        return list(hits), []

    def ignore_hits(self, repo, sha, workdir):
        return []

    def fetch_public_refs(self, repo, url, workdir):
        self.log.append(("suite", ["fetch_public_refs", url]))
        if self.public_error:
            raise RuntimeError("the public reference could not be read anonymously; nothing ships")
        return list(self.public)

    def binary_blobs_hashed(self, repo, sha, present):
        return nul_blobs(repo, sha, present)

    def rulings_file(self, repo):
        return os.path.join(repo, ".git", "hooks", "glitch-gitleaksignore")

    def scan_unpublished(self, repo, sha, workdir, gitleaks, public_shas, rulings, allow_blobs, ruled, ruled_used,
                         ruled_messages):
        self.log.append(("suite", ["scan_unpublished", sha, list(public_shas), rulings, ruled, ruled_messages]))
        self.scans.append({"repo": repo, "sha": sha, "public": list(public_shas), "rulings": rulings,
                           "allow_blobs": allow_blobs, "ruled": ruled, "ruled_messages": ruled_messages})
        if self.nonpublic_finding:
            raise RuntimeError("gitleaks found 1 item(s) in commits that are not public: x.txt:generic-api-key:1")
        return self.scanned


def ship_rig(mod, t, suite_kw=None, **kw):
    repo, root, head = make_repo(t)
    runner = FakeRunner(athena_head=head, **kw)
    suite = FakeSuite(runner.calls, **(suite_kw or {}))
    reserve = reserve_file(t)
    with mock.patch.object(mod, "PINNED_TREE", root), \
            mock.patch.object(mod, "RESERVE_SHA256", hashlib.sha256(Path(reserve).read_bytes()).hexdigest()):
        try:
            out = mod.ship(runner, repo=repo, ref="main", suite="/x/athena_suite.py", reserve=reserve,
                           gitleaks="gitleaks", work=os.path.join(t, "work"), precheck=lambda s: [],
                           suite_module=suite)
        except mod.LaunchRefused as e:
            out = e
    return runner, out, head, repo


def l1(mod) -> list:
    out = []
    with tempfile.TemporaryDirectory() as t:
        runner, got, head, repo = ship_rig(mod, t)
        if not isinstance(got, dict) or got.get("child") != CHILD or got.get("head") != head:
            return [f"L1-ship: a clean ship did not complete: {got}"]
        first_remote = next(i for i, c in enumerate(runner.calls) if c[0] in ("remote", "copy_to"))
        scans = [(i, c[1]) for i, c in enumerate(runner.calls) if c[0] == "suite" and c[1][0] == "scan_unpublished"]
        fetches = [i for i, c in enumerate(runner.calls) if c[0] == "suite" and c[1][0] == "fetch_public_refs"]
        if len(scans) != 1 or not fetches or not fetches[0] < scans[0][0] < first_remote:
            out.append("L1-ship: athena is touched before athena_suite's public fetch and outward scan")
        elif scans[0][1][1:] != [head, ["a" * 40], os.path.join(repo, ".git", "hooks", "glitch-gitleaksignore"),
                                 {"r": 1}, {"m": 1}]:
            out.append("L1-ship: the outward scan is not scan_unpublished(head, the public tips, the push door's "
                       "rulings, the committed allowlist)")
        if ["validate_allowlist", "gars"] not in [c[1] for c in runner.calls if c[0] == "suite"]:
            out.append("L1-ship: the committed allowlist is not read for the gars kind")
        locals_ = [c[1] for c in runner.calls if c[0] == "local"]
        if not any(a[3:5] == ["bundle", "verify"] for a in locals_):
            out.append("L1-ship: the bundle is not verified")
        reads = [c[1] for c in runner.calls if c[0] == "remote" and c[1].startswith("sha256sum ")]
        if reads != [f"sha256sum {CHILD}/walk-out.bundle", f"sha256sum {CHILD}/athena-reserve"]:
            out.append("L1-ship: the athena copies are not each read back by sha256")
    for why, suite_kw in (("a finding in a commit the public remote does not serve", {"nonpublic_finding": True}),
                          ("an unreadable public-ref list", {"public_error": True}),
                          ("a public remote advertising nothing", {"public": ()}),
                          ("a secret-shaped file", {"hits": [("x.pem", "pem")]})):
        with tempfile.TemporaryDirectory() as t:
            runner, got, _, _ = ship_rig(mod, t, suite_kw=suite_kw)
            if not isinstance(got, mod.LaunchRefused):
                out.append(f"L1-ship: {why} ships")
            elif any(c[0] in ("remote", "copy_to") for c in runner.calls):
                out.append(f"L1-ship: {why} refused only after athena was touched")
    with tempfile.TemporaryDirectory() as t:
        runner2 = FakeRunner(athena_head="0" * 40)
        quiet = FakeSuite([])
        repo, root, head = make_repo(t)
        reserve = reserve_file(t)
        with mock.patch.object(mod, "PINNED_TREE", root), \
                mock.patch.object(mod, "RESERVE_SHA256", hashlib.sha256(Path(reserve).read_bytes()).hexdigest()):
            try:
                mod.ship(runner2, repo=repo, ref="main", suite="/x", reserve=reserve, gitleaks="gitleaks",
                         work=os.path.join(t, "w2"), precheck=lambda s: [], suite_module=quiet)
                out.append("L1-ship: an athena clone off the head is admitted")
            except mod.LaunchRefused:
                pass
            try:
                mod.ship(FakeRunner(athena_head=head), repo=repo, ref="main", suite="/x", reserve=reserve,
                         gitleaks="gitleaks", work=os.path.join(t, "w3"), precheck=lambda s: ["a suite runs"],
                         suite_module=quiet)
                out.append("L1-ship: a closed Mac pre-check ships")
            except mod.LaunchRefused:
                pass
        with mock.patch.object(mod, "PINNED_TREE", "1" * 40), \
                mock.patch.object(mod, "RESERVE_SHA256", hashlib.sha256(Path(reserve).read_bytes()).hexdigest()):
            r4 = FakeRunner(athena_head=head)
            try:
                mod.ship(r4, repo=repo, ref="main", suite="/x", reserve=reserve, gitleaks="gitleaks",
                         work=os.path.join(t, "w4"), precheck=lambda s: [], suite_module=quiet)
                out.append("L1-ship: a head without the pinned tree's history ships")
            except mod.LaunchRefused:
                if any(c[0] != "local" for c in r4.calls):
                    out.append("L1-ship: athena is touched before the pinned-history check")
        try:
            mod.ship(FakeRunner(athena_head=head), repo=repo, ref="main", suite="/x", reserve=reserve,
                     gitleaks="gitleaks", work=os.path.join(t, "w5"), precheck=lambda s: [], suite_module=quiet)
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
    i_test = cmd.find("os.O_EXCL")
    i_gate = cmd.find("machine_gate.py athena-check")
    i_hold = cmd.find("athena-reserve hold --by gap4-walk-w-0001")
    if min(i_test, i_gate, i_hold) < 0 or not i_test < i_gate < i_hold:
        out.append("L2-run: the O_EXCL claim and the athena gate do not both come before the hold")
    if f"{mod.RESERVATION} gap4-walk-w-0001;" not in cmd[i_test:i_gate]:
        out.append("L2-run: the claim is not of the reservation under this walk's hold id")
    if f"|| {{ rm -f {mod.RESERVATION}; exit 1; }}" not in cmd[i_gate:i_hold]:
        out.append("L2-run: a closed gate leaves the claim behind")
    # The claim's own program, run here on a temporary path: a second claim refuses (O_EXCL), the first carries the id.
    toks = shlex.split(cmd[:i_gate])
    prog = toks[toks.index("-c") + 1] if "-c" in toks else ""
    with tempfile.TemporaryDirectory() as t:
        res = os.path.join(t, "reserved.json")
        first = subprocess.run([sys.executable, "-I", "-c", prog, res, "gap4-walk-w-0001"], capture_output=True)
        second = subprocess.run([sys.executable, "-I", "-c", prog, res, "gap4-walk-w-0001"], capture_output=True)
        try:
            by = json.loads(Path(res).read_text()).get("by")
        except (OSError, ValueError):
            by = None
        if first.returncode != 0 or by != "gap4-walk-w-0001" or second.returncode == 0:
            out.append("L2-run: the claim is not an O_EXCL create carrying the hold id")
    held = cmd[i_hold:]
    for name, value in ((mod.machine_gate.ENV_ACCOUNT, "athena-suite"),
                        (mod.machine_gate.ENV_RESERVATION, mod.RESERVATION),
                        (mod.machine_gate.ENV_HOLD, "gap4-walk-w-0001"),
                        (mod.machine_gate.ENV_SLOTS, "/home/javier/athena-suites/.slots")):
        if f"{name}={value}" not in held or f"{name}={value}" not in cmd[i_test:i_gate]:
            out.append(f"L2-run: {name} is not {value} for both the gate and the walk")
    toks = shlex.split(cmd)
    at = next((i for i in range(len(toks) - 2) if toks[i] == "sh" and toks[i + 1] == "-c"), None)
    body = shlex.split(toks[at + 2]) if at is not None else []
    want = ["walk_runner.py", "--walk", "w-0001", "--task", "plan-gate", "--half", "positive", "--wording", "w1",
            "--arm", "A", "--model", "claude-x", "--reason", "the first walk;"]
    tail = [os.path.basename(x) if x.endswith("walk_runner.py") else x for x in body]
    if not any(tail[i:i + len(want)] == want for i in range(len(tail))):
        out.append("L2-run: the walk's argv is not the cell's")
    if "nohup sh -c" not in cmd or "walk.pid" not in cmd or "walk.exit" not in cmd:
        out.append("L2-run: the walk is not detached with its pid and exit recorded")
    i_reserve = cmd.find(f"test -f {CHILD}/athena-reserve")
    if i_reserve < 0 or not i_reserve < i_test:
        out.append("L2-run: athena-reserve's presence is not checked before the claim")
    i_nohup = cmd.find("nohup sh -c")
    tail = cmd[i_nohup:]
    i_alive = tail.find(f"kill -0 $(cat {CHILD}/walk.pid)")
    i_pid = tail.rfind(f"cat {CHILD}/walk.pid")
    if i_alive < 0 or not i_alive < i_pid or f"rm -f {mod.RESERVATION}" not in tail[i_alive:i_pid] \
            or "exit 1" not in tail[i_alive:i_pid]:
        out.append("L2-run: a hold that exits before the walk starts can still print a pid")
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


def fetch_rig(mod, t, *, walk_state="exit=0", commit_on_athena=True, suite_kw=None, suite=None, gitleaks=None,
              make_commit=None, runner_kw=None, after_runner=None):
    """A Mac records clone at `head`, an athena clone with one walk commit (or make_commit(athena)), the real
    `<head>..main` bundle; fetch through the fake athena with a fake athena_suite (or the real one, `suite`)."""
    if gitleaks is None:
        gitleaks = fake_gitleaks(t)
    repo, root, head = make_repo(t)
    athena = os.path.join(t, "athena-repo")
    git("clone", "-q", repo, athena)
    if commit_on_athena:
        if make_commit is None:
            Path(athena, "walk.txt").write_text("walk\n")
            git("-C", athena, "add", "walk.txt")
            git("-C", athena, "commit", "-q", "-m", "walk")
        else:
            make_commit(athena)
    tip = git("-C", athena, "rev-parse", "HEAD").strip()
    back = os.path.join(t, "athena-back.bundle")
    if commit_on_athena:
        git("-C", athena, "bundle", "create", back, f"{head}..main")
    runner = FakeRunner(athena_tip=tip, walk_state=walk_state, back_bundle=back, **(runner_kw or {}))
    if after_runner is not None:
        after_runner(runner, tip)
    fake = FakeSuite(runner.calls, **(suite_kw or {})) if suite is None else None
    try:
        got = mod.fetch(runner, child=CHILD, head=head, ref="main", records=repo, gitleaks=gitleaks,
                        work=os.path.join(t, "work"), suite="/x/athena_suite.py",
                        suite_module=fake if suite is None else suite)
    except mod.LaunchRefused as e:
        got = e
    runner.fake_suite = fake
    return runner, got, repo, head, tip


def fake_gitleaks(t):
    path = os.path.join(t, "fake-gitleaks")
    if not os.path.exists(path):
        Path(path).write_text("#!" + sys.executable + "\n" + FAKE_GITLEAKS)
        os.chmod(path, 0o755)
    return path


def walk_branches(repo):
    return git("-C", repo, "for-each-ref", "refs/heads/walk/").strip()


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
        scans = runner.fake_suite.scans
        if len(scans) != 1 or {k: scans[0][k] for k in ("sha", "public", "rulings", "allow_blobs", "ruled",
                                                         "ruled_messages")} != {
                "sha": tip, "public": [head], "rulings": None, "allow_blobs": (), "ruled": None,
                "ruled_messages": None}:
            out.append("L3-fetch: the back scan is not athena_suite's scan_unpublished(tip, [head]) with no allowance")
        if any(c[0] == "local" and c[1][0] == "gitleaks" for c in runner.calls):
            out.append("L3-fetch: a plain gitleaks scan still runs on the way back")
        i_scan = next((i for i, c in enumerate(runner.calls) if c[0] == "suite" and c[1][0] == "scan_unpublished"),
                      None)
        i_rec = next(i for i, c in enumerate(runner.calls) if c[0] == "local" and c[1][:3] == ["git", "-C", repo]
                     and "fetch" in c[1])
        if i_scan is None or not i_scan < i_rec:
            out.append("L3-fetch: the records clone is fetched before the scan")
    with tempfile.TemporaryDirectory() as t:
        _, got, repo, _, _ = fetch_rig(mod, t, suite_kw={"nonpublic_finding": True})
        if not isinstance(got, mod.LaunchRefused):
            out.append("L3-fetch: a finding in the walk's commits is fetched (no allowance comes back)")
        elif walk_branches(repo):
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


def l5(mod) -> list:
    """MINOR 5: each guard the review found unexercised refuses by its own message."""
    out = []

    def ship_case(t, want, *, runner_set=None, pinned=True, reserve_pin=True):
        repo, root, head = make_repo(t)
        runner = FakeRunner(athena_head=head)
        if runner_set:
            runner_set(runner, head)
        reserve = reserve_file(t)
        pin = hashlib.sha256(Path(reserve).read_bytes()).hexdigest() if reserve_pin else mod.RESERVE_SHA256
        with mock.patch.object(mod, "PINNED_TREE", root if pinned else "1" * 40), \
                mock.patch.object(mod, "RESERVE_SHA256", pin):
            try:
                mod.ship(runner, repo=repo, ref="main", suite="/x", reserve=reserve, gitleaks="gitleaks",
                         work=os.path.join(t, "w"), precheck=lambda s: [], suite_module=FakeSuite([]))
                return f"shipped (wanted a refusal naming {want!r})"
            except mod.LaunchRefused as e:
                return None if want in str(e) else f"refused for another reason: {e}"

    cases = (
        ("the local athena-reserve pin", "athena-reserve is not the runbook's pinned bytes",
         {"reserve_pin": False}),
        ("list-heads", "the bundle's heads are not exactly the ref",
         {"runner_set": lambda r, h: setattr(r, "listheads_override", "0" * 40 + " refs/heads/main\n")}),
        ("the outward sha read-back", "walk-out.bundle's sha256 on athena is not the Mac's",
         {"runner_set": lambda r, h: r.sha_override.update({f"{CHILD}/walk-out.bundle": "0" * 64})}),
    )
    for name, want, kw in cases:
        with tempfile.TemporaryDirectory() as t:
            got = ship_case(t, want, **kw)
            if got:
                out.append(f"L5-guards: {name}: {got}")
    with tempfile.TemporaryDirectory() as t:
        _, got, repo, _, _ = fetch_rig(mod, t, suite_kw={"scanned": 0})
        if not isinstance(got, mod.LaunchRefused) or "scanned no commit" not in str(got) or walk_branches(repo):
            out.append(f"L5-guards: a return scan of no commit: {got}")
    for name, want, runner_kw, after in (
            ("merge-base head..tip", "athena's tip does not descend from the shipped head", None,
             lambda r, tip: setattr(r, "ancestor_rc", 1)),
            ("the back bundle sha", "the back bundle's sha256 on the Mac is not athena's", None,
             lambda r, tip: r.sha_override.update({f"{CHILD}/walk-back.bundle": "0" * 64})),
            ("got != tip", "the back bundle's tip is not athena's", None,
             lambda r, tip: setattr(r, "athena_tip", "f" * 40))):
        with tempfile.TemporaryDirectory() as t:
            _, got, repo, _, _ = fetch_rig(mod, t, runner_kw=runner_kw, after_runner=after)
            if not isinstance(got, mod.LaunchRefused) or want not in str(got):
                out.append(f"L5-guards: {name}: {got}")
            elif walk_branches(repo):
                out.append(f"L5-guards: {name}: a walk branch was left")
    return out


FAKE_RESERVE = {
    # exits at once, as athena-reserve does on a refusal: no walk ever starts
    "dead": "import sys\nsys.exit(3)\n",
    # holds: rewrites the reservation under its --by id, then stays up as the walk would
    "alive": ("import json, sys, time\nby = sys.argv[sys.argv.index('--by') + 1]\n"
              "open(sys.argv[-1], 'w').write(json.dumps({'by': by}))\ntime.sleep(8)\n"),
}


def l6(mod) -> list:
    """NIT C, driven for real with sh on this machine: the start's own command, its athena paths moved into a
    temporary folder, the athena gate replaced by `true`, and athena-reserve by a fake that dies at once or holds."""
    import signal
    out = []
    cell = {"task": "t", "half": "h", "wording": "w", "arm": "A", "model": "m"}
    for case in ("missing", "dead", "alive"):
        with tempfile.TemporaryDirectory() as t:
            child, res = os.path.join(t, "child"), os.path.join(t, "reserved.json")
            os.mkdir(child)
            if case != "missing":
                Path(child, "athena-reserve").write_text(FAKE_RESERVE[case])
            cmd = mod.run_command(child=CHILD, walk="w-0001", cell=cell, reason="r")
            gate = cmd[cmd.index("env GAP4_SUITE_ACCOUNT"):cmd.index(" > " + CHILD + "/gate.out")]
            cmd = cmd.replace(gate, "true", 1).replace(CHILD, child).replace(mod.RESERVATION, res)
            # the fake hold is told the reservation's path as its last argument
            cmd = cmd.replace("--reason r;", f"--reason r {res};")
            p = subprocess.run(["sh", "-c", cmd], capture_output=True, text=True, timeout=60)
            pid_file = Path(child, "walk.pid")
            if case == "alive":
                if p.returncode != 0 or not p.stdout.strip().isdigit():
                    out.append(f"L6-start: a live hold did not print its pid (exit {p.returncode}: {p.stderr[-120:]})")
                try:
                    os.kill(int(pid_file.read_text().strip()), signal.SIGTERM)   # by the recorded pid
                except (OSError, ValueError):
                    pass
            else:
                if p.returncode == 0 or p.stdout.strip().isdigit():
                    out.append(f"L6-start: the {case} hold's start printed a pid or exited 0")
                if os.path.exists(res):
                    out.append(f"L6-start: the {case} hold's start left the claim behind")
    return out


def l7(mod) -> list:
    """The walk's environment is complete (glitch-6b, 15 Oct 2026, after the box lane found GAP4_CONFIG_PARENT
    missing at 26dd61be): every GAP4_* name a study module reads reaches both the gate and the walk; the commit
    identity takes.require_commit_identity needs reaches the walk; each deliberately absent name is absent."""
    import takes
    out = []
    cell = {"task": "approval-scope", "half": "trap", "wording": "w1", "arm": "A", "model": "claude-haiku-4-5-20251001"}
    cmd = mod.run_command(child=CHILD, walk="w-0001", cell=cell, reason="r")
    i_gate, i_hold = cmd.find("machine_gate.py athena-check"), cmd.find("athena-reserve hold")
    gate_part, hold_part = cmd[:i_gate], cmd[i_hold:]
    read = set()
    for path in HERE.rglob("*.py"):
        if "tests" in path.relative_to(HERE).parts or "__pycache__" in path.parts:
            continue
        read |= set(re.findall(r'"(GAP4_[A-Z0-9_]+)"', path.read_text(encoding="utf-8", errors="replace")))
    read -= set(mod.RUN_ENV_ABSENT)
    if not read >= {"GAP4_CONFIG_PARENT", "GAP4_SUITE_ACCOUNT", "GAP4_RESERVATION", "GAP4_OWN_HOLD",
                    "GAP4_SUITE_SLOTS"}:
        out.append(f"L7-env: the tree's GAP4 names read {sorted(read)}: the scan found too few")
    for name in sorted(read):
        if f"{name}=" not in hold_part:
            out.append(f"L7-env: {name}, read by the tree, does not reach the walk")
        if name.startswith(("GAP4_SUITE", "GAP4_RESERVATION", "GAP4_OWN_HOLD")) and f"{name}=" not in gate_part:
            out.append(f"L7-env: {name}, read by the gate, does not reach the gate")
    if f"GAP4_CONFIG_PARENT={mod.CONFIG_PARENT}" not in hold_part or mod.CONFIG_PARENT != "/home/javier/gap4-walk-config":
        out.append("L7-env: the walk's config parent is not /home/javier/gap4-walk-config")
    for name in mod.RUN_ENV_ABSENT:
        if f"{name}=" in cmd:
            out.append(f"L7-env: {name}, deliberately absent, is passed")
    # The commit identity: athena's javier has no global git identity (read 05:23 EDT, 15 Oct 2026), and the walk's
    # clone has no local one, so WalkRepo's require_commit_identity reads it from the environment the walk gets.
    outer = shlex.split(cmd)
    at = next((i for i in range(len(outer) - 2) if outer[i] == "sh" and outer[i + 1] == "-c"), None)
    body = outer[at + 2] if at is not None else ""
    toks = shlex.split(body.split(" -- ", 1)[1].split(";", 1)[0]) if " -- " in body else []
    env = dict(tok.split("=", 1) for tok in toks[1:] if "=" in tok and re.fullmatch(r"[A-Z0-9_]+=.*", tok))
    with tempfile.TemporaryDirectory() as t:
        repo = os.path.join(t, "r")
        git("init", "-q", repo)
        clean = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        with mock.patch.dict(os.environ, clean, clear=True):
            try:
                takes.require_commit_identity(Path(repo))
                return out + ["L7-env: the test's own environment already carries an identity"]
            except ValueError:
                pass
        with mock.patch.dict(os.environ, {**clean, **env}, clear=True):
            try:
                takes.require_commit_identity(Path(repo))
            except ValueError as e:
                out.append(f"L7-env: the walk's environment carries no commit identity: {e}")
    if env.get("GIT_AUTHOR_EMAIL") != "28984720+javrodriguez@users.noreply.github.com" \
            or env.get("GIT_COMMITTER_EMAIL") != env.get("GIT_AUTHOR_EMAIL"):
        out.append("L7-env: the walk's commit identity is not the noreply one the box commits use")
    return out


def nul_blobs(repo, sha, present):
    """athena_suite.binary_blobs_hashed's rule, for the fakes: (path, blob id, sha256) of every blob reachable from
    sha and not from present whose first 8000 bytes hold a NUL."""
    objs = git("-C", repo, "rev-list", "--objects", sha, *(["--not"] + list(present) if present else [])).splitlines()
    out = []
    for line in objs:
        oid, _, path = line.partition(" ")
        if not path or git("-C", repo, "cat-file", "-t", oid).strip() != "blob":
            continue
        body = subprocess.run(["git", "-C", repo, "cat-file", "blob", oid], capture_output=True, env=GIT_ENV).stdout
        if b"\0" in body[:8000]:
            out.append((path, oid, hashlib.sha256(body).hexdigest()))
    return sorted(out)


FAKE_GITLEAKS = """import json, os, re, sys
a = sys.argv
src, report = a[-1], a[a.index("--report-path") + 1]
honour_allow = "--ignore-gitleaks-allow" not in a          # gitleaks' own rule: an allow comment hides its line
SIGS = (b"\\x1f\\x8b", b"BZh", b"\\x28\\xb5\\x2f\\xfd", b"7z\\xbc\\xaf\\x27\\x1c", b"PK\\x03\\x04")
TOKEN = re.compile(rb"ghp_[A-Za-z0-9]{36}")
found = []
for n in sorted(os.listdir(src)):
    data = open(os.path.join(src, n), "rb").read()
    if data.startswith(SIGS) or data[257:262] == b"ustar":      # gitleaks dir skips what looks like an archive
        continue
    for i, line in enumerate(data.splitlines(), 1):
        if honour_allow and b"gitleaks:allow" in line:
            continue
        if b"PLANTED" in line:
            found.append({"File": os.path.join(src, n), "RuleID": "x", "StartLine": i})
        if TOKEN.search(line):
            found.append({"File": os.path.join(src, n), "RuleID": "github-pat", "StartLine": i})
json.dump(found, open(report, "w"))
"""


def evidence_path(walk, data):
    return f"evals/gap-study-4/rehearsals/{walk}/evidence/blobs/" + hashlib.sha256(data).hexdigest()


def blob_rig(t, files):
    """A head commit, then one walk commit adding `files` ({path: bytes}); returns (repo, head, tip)."""
    repo, _, head = make_repo(t)
    for path, data in files.items():
        full = Path(repo, path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
        git("-C", repo, "add", path)
    git("-C", repo, "commit", "-q", "-m", "walk")
    return repo, head, git("-C", repo, "rev-parse", "HEAD").strip()


def make_gz(payload: bytes, *, extra=None, name=None, comment=None, fhcrc=False, reserved=0,
            mtime=b"\x00\x00\x00\x00", level=6) -> bytes:
    """One RFC 1952 member built by hand, so the header fields a test needs can be set."""
    import zlib
    flg = reserved | (0x04 if extra is not None else 0) | (0x08 if name is not None else 0) \
        | (0x10 if comment is not None else 0) | (0x02 if fhcrc else 0)
    head = b"\x1f\x8b\x08" + bytes([flg]) + mtime + b"\x00\xff"
    if extra is not None:
        head += len(extra).to_bytes(2, "little") + extra
    if name is not None:
        head += name + b"\x00"
    if comment is not None:
        head += comment + b"\x00"
    if fhcrc:
        head += (zlib.crc32(head) & 0xFFFF).to_bytes(2, "little")
    c = zlib.compressobj(level, zlib.DEFLATED, -zlib.MAX_WBITS)
    body = c.compress(payload) + c.flush()
    return head + body + (zlib.crc32(payload) & 0xFFFFFFFF).to_bytes(4, "little") \
        + (len(payload) & 0xFFFFFFFF).to_bytes(4, "little")


_BOMB = []


def _absolute_cap_bomb() -> bytes:
    """MINOR 3's bomb, made once per process: ~17.3 MiB of base64 text (no NUL), gzip level 1 (~1.3:1, far under
    256:1), so only the 16 MiB absolute cap refuses it."""
    if not _BOMB:
        import base64
        import gzip
        _BOMB.append(gzip.compress(base64.b64encode(os.urandom(13 * 1024 * 1024)), 1))
    return _BOMB[0]


def l8(mod) -> list:
    """glitch-6b's ruling (b) with the review of b1f5c952 folded: the watcher's gzip evidence blobs ship only parsed,
    decoded within the per-blob and per-walk bounds, and scanned clean, payload and header fields alike."""
    import gzip
    import io
    out = []
    text = json.dumps({"path": "plan/approved.json", "text": "ok"}).encode()
    clean = gzip.compress(text)

    def decode(data, limit=None):
        buf = io.BytesIO()
        limit = min(mod.BLOB_MAX_BYTES, len(data) * mod.BLOB_MAX_RATIO) if limit is None else limit
        return mod.gunzip_to(data, buf, limit), buf.getvalue()
    try:
        (n, fields), got = decode(clean)
        if got != text or n != len(text) or fields:
            out.append("L8-blobs: a clean gzip does not decode to its bytes")
        (_, fields), got = decode(make_gz(text, name=b"n.json", comment=b"c", extra=b"xx", fhcrc=True))
        if got != text or [k for k, _v in fields] != ["FEXTRA", "FNAME", "FCOMMENT"]:
            out.append("L8-blobs: the header fields are not returned for the scan")
    except mod.LaunchRefused as e:
        out.append(f"L8-blobs: a clean gzip is refused: {e}")
    big_gz = _absolute_cap_bomb()
    for why, data in (("a non-gzip binary", b"\x00\x01binary"), ("a 20 MiB zero bomb", gzip.compress(b"\0" * (20 << 20))),
                      ("a ratio bomb", gzip.compress(b"a" * (300 * 1024))),
                      ("an absolute-cap bomb (no NUL, under 256:1, over 16 MiB)", big_gz),
                      ("trailing bytes", clean + b"x"), ("a truncated stream", clean[:-6]),
                      ("a binary payload", gzip.compress(b"\x00\x00bin")),
                      ("a reserved flag bit", make_gz(text, reserved=0x20)),
                      ("a bad FHCRC", (lambda g: g[:10] + bytes([g[10] ^ 0xFF, g[11]]) + g[12:])(make_gz(text, fhcrc=True))),
                      ("a bad CRC32", clean[:-8] + b"\x00\x00\x00\x00" + clean[-4:])):
        try:
            decode(data)
            out.append(f"L8-blobs: {why} decodes")
        except mod.LaunchRefused:
            pass
    with tempfile.TemporaryDirectory() as t:
        fake = fake_gitleaks(t)
        suite = FakeSuite([])
        planted = gzip.compress(b"PLANTED synthetic marker")
        pad = b"x" * 257
        textlike = b"\x1f\x8b\x08\x01" + b"A" * 60                     # git reads it as text: no NUL
        second = gzip.compress(b"another clean record\n")
        cases = {
            "clean": ({evidence_path("w001", clean): clean}, True),
            "planted payload": ({evidence_path("w001", planted): planted}, False),
            "planted allow line": ((lambda g: {evidence_path("w001", g): g})(
                gzip.compress(b"PLANTED synthetic  # gitleaks:allow\n")), False),
            "planted FNAME": ((lambda g: {evidence_path("w001", g): g})(make_gz(text, name=b"PLANTED")), False),
            "planted FCOMMENT": ((lambda g: {evidence_path("w001", g): g})(make_gz(text, comment=b"PLANTED")), False),
            "planted FEXTRA": ((lambda g: {evidence_path("w001", g): g})(make_gz(text, extra=b"PLANTED")), False),
            "non-gzip": ({evidence_path("w001", b"\x00raw"): b"\x00raw"}, False),
            "bomb": ((lambda g: {evidence_path("w001", g): g})(gzip.compress(b"a" * (20 << 20))), False),
            "absolute-cap bomb": ({evidence_path("w001", big_gz): big_gz}, False),
            "outside": ({"evals/gap-study-4/rehearsals/w001/rec.json.gz": clean}, False),
            "also outside": ({evidence_path("w001", clean): clean,
                              "evals/gap-study-4/rehearsals/w001/copy.gz": clean}, False),
            "misnamed": ({"evals/gap-study-4/rehearsals/w001/evidence/blobs/" + "0" * 64: clean}, False),
            "text-looking gzip": ({"evals/gap-study-4/rehearsals/w001/notes.txt": textlike}, False),
            "long FNAME": ((lambda g: {evidence_path("w001", g): g})(make_gz(text, name=b"n" * 5000)), False),
        }
        for sig, payload in (("gzip", b"\x1f\x8b\x08y"), ("bzip2", b"BZh9"), ("zstd", b"\x28\xb5\x2f\xfd"),
                             ("7z", b"7z\xbc\xaf\x27\x1c"), ("zip", b"PK\x03\x04"),
                             ("tar", pad + b"ustar00")):
            g = gzip.compress(payload + b"\nfill\nPLANTED synthetic\n")
            cases[f"{sig}-signature payload"] = ({evidence_path("w001", g): g}, False)
        for name, (files, ok) in cases.items():
            d = os.path.join(t, name.replace(" ", "-"))
            os.mkdir(d)
            repo, head, tip = blob_rig(d, files)
            try:
                got = mod.admitted_evidence_blobs(suite, repo, head, tip, fake, os.path.join(d, "w"))
                if not ok:
                    out.append(f"L8-blobs: the {name} case is admitted")
                elif len(got) != 1:
                    out.append(f"L8-blobs: the clean case admits {len(got)} blob(s)")
            except mod.LaunchRefused as e:
                if ok:
                    out.append(f"L8-blobs: the clean case is refused: {e}")
                elif "PLANTED" in str(e) or "synthetic" in str(e):
                    out.append("L8-blobs: a refusal prints decompressed content")
            if os.path.exists(os.path.join(d, "w")) and any(n.startswith("blobs-") for n in os.listdir(os.path.join(d, "w"))):
                out.append(f"L8-blobs: the {name} case left its decompressed folder")
        # MAJOR 2: the per-walk total and count caps
        two = {evidence_path("w001", clean): clean, evidence_path("w001", second): second}
        for why, patch in (("the total cap", ("BLOB_TOTAL_MAX", len(text) + 5)), ("the count cap", ("BLOB_MAX_COUNT", 1))):
            d = os.path.join(t, why.replace(" ", "-"))
            os.mkdir(d)
            repo, head, tip = blob_rig(d, two)
            with mock.patch.object(mod, patch[0], patch[1]):
                try:
                    mod.admitted_evidence_blobs(suite, repo, head, tip, fake, os.path.join(d, "w"))
                    out.append(f"L8-blobs: {why} is not enforced")
                except mod.LaunchRefused:
                    pass
        # a blob already in the shipped head's history
        d = os.path.join(t, "inhead")
        os.mkdir(d)
        repo, _, _ = make_repo(d)
        pth = evidence_path("w001", clean)
        Path(repo, pth).parent.mkdir(parents=True)
        Path(repo, pth).write_bytes(clean)
        git("-C", repo, "add", pth)
        git("-C", repo, "commit", "-q", "-m", "in head")
        head = git("-C", repo, "rev-parse", "HEAD").strip()
        Path(repo, "n.txt").write_text("n\n")
        git("-C", repo, "add", "n.txt")
        git("-C", repo, "commit", "-q", "-m", "walk")
        tip = git("-C", repo, "rev-parse", "HEAD").strip()
        with mock.patch.object(mod, "evidence_candidates", lambda r, h, tp: {
                git("-C", repo, "rev-parse", f"HEAD~1:{pth}").strip(): {pth}}):
            try:
                mod.admitted_evidence_blobs(suite, repo, head, tip, fake, os.path.join(d, "w"))
                out.append("L8-blobs: a blob from the shipped head's history is admitted")
            except mod.LaunchRefused:
                pass
        # MAJOR B: a walk commit's message, tar-signed at offset 257 with a marker after it, and a plain one
        for why, msg, ok in (("a ustar-signed message", "x" * 257 + "ustar00\nPLANTED synthetic\n", False),
                             ("a planted message", "walk\nPLANTED synthetic\n", False),
                             ("a clean message", "Commit one walk; never counted\n", True)):
            d = os.path.join(t, why.replace(" ", "-"))
            os.mkdir(d)
            repo, _, head = make_repo(d)
            Path(repo, "w.txt").write_text("w\n")
            git("-C", repo, "add", "w.txt")
            git("-C", repo, "commit", "-q", "-m", msg)
            tip = git("-C", repo, "rev-parse", "HEAD").strip()
            try:
                mod.admitted_evidence_blobs(suite, repo, head, tip, fake, os.path.join(d, "w"))
                if not ok:
                    out.append(f"L8-blobs: {why} passes the walk's message scan")
            except mod.LaunchRefused as e:
                if ok:
                    out.append(f"L8-blobs: {why} is refused: {e}")
        # MAJOR E and F: a planted path, a planted author
        for why, kind in (("a planted path", "path"), ("a planted author", "author")):
            d = os.path.join(t, why.replace(" ", "-"))
            os.mkdir(d)
            repo, _, head = make_repo(d)
            fname = "evals/gap-study-4/rehearsals/w001/PLANTED-synthetic.txt" if kind == "path" else "w.txt"
            Path(repo, fname).parent.mkdir(parents=True, exist_ok=True)
            Path(repo, fname).write_text("w\n")
            git("-C", repo, "add", fname)
            if kind == "author":
                git("-C", repo, "commit", "-q", "--author", "PLANTED synthetic <a@invalid>", "-m", "w")
            else:
                git("-C", repo, "commit", "-q", "-m", "w")
            tip = git("-C", repo, "rev-parse", "HEAD").strip()
            try:
                mod.admitted_evidence_blobs(suite, repo, head, tip, fake, os.path.join(d, "w"))
                out.append(f"L8-blobs: {why} passes the walk's commit scan")
            except mod.LaunchRefused:
                pass
    return out


def l4(mod) -> list:
    out = []
    with tempfile.TemporaryDirectory() as t:
        r1, _, _, _ = ship_rig(mod, t)
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
    return out


CHECKS = {"L1-ship": l1, "L2-run": l2, "L3-fetch": l3, "L4-bounds": l4, "L5-guards": l5, "L6-start": l6,
          "L7-env": l7, "L8-blobs": l8}


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
    "scan-skipped": ((("    suite_mod = load_suite(suite) if suite_module is None else suite_module\n    try:\n"
                       "        scanned = outward_scan(", "    suite_mod = None\n    try:\n        scanned = 0 and outward_scan("),),
                     "L1-ship"),
    "public-error-swallowed": ((("    public = suite_mod.fetch_public_refs(check, suite_mod.PUBLIC_REFERENCE[SUITE_KIND], work)",
                                 "    try:\n        public = suite_mod.fetch_public_refs(check, suite_mod.PUBLIC_REFERENCE[SUITE_KIND], "
                                 "work)\n    except Exception:\n        public = ['x']"),), "L1-ship"),
    "public-subtraction-dropped": ((("return suite_mod.scan_unpublished(check, head, work, gitleaks, public,",
                                     "return suite_mod.scan_unpublished(check, head, work, gitleaks, (),"),), "L1-ship"),
    "no-umask": ((("    return (f\"umask {UMASK}; set -e;", "    return (f\"set -e;"),), "L2-run"),
    "hold-dropped": ((("    held = (f\"python3 {child}/athena-reserve hold --by {hid} -- {walk_env} \"",
                       "    held = (f\"{walk_env} \""),), "L2-run"),
    "claim-dropped": ((("python3 -I -c {shlex.quote(claim)} {RESERVATION} {hid}; ", ""),), "L2-run"),
    "claim-not-exclusive": ((("os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, ",
                              "os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT, "),), "L2-run"),
    "claim-left-on-closed-gate": ((("|| {{ rm -f {RESERVATION}; exit 1; }}", "|| exit 1"),), "L2-run"),
    "back-range-whole-history": ((("bundle create {child}/walk-back.bundle {head}..{shlex.quote(ref)}",
                                   "bundle create {child}/walk-back.bundle {shlex.quote(ref)}"),), "L3-fetch"),
    "back-scan-allowance": ((("        n = suite_mod.scan_unpublished(scratch, tip, os.path.join(work, \"back-scan-work\"), "
                              "gitleaks, [head], None,",
                              "        n = suite_mod.scan_unpublished(scratch, tip, os.path.join(work, \"back-scan-work\"), "
                              "gitleaks, [head], suite_mod.rulings_file(records),"),), "L3-fetch"),
    "reserve-pin-unchecked": ((("    if _sha256(reserve) != RESERVE_SHA256:", "    if False:"),), "L5-guards"),
    "list-heads-unchecked": ((("    if heads != [head, f\"refs/heads/{ref}\"]:", "    if False:"),), "L5-guards"),
    "outward-sha-unchecked": ((("        if got != [want]:", "        if False:"),), "L5-guards"),
    "back-ancestry-unchecked": ((("    if runner.remote(f\"git -C {child}/repo merge-base --is-ancestor {head} {tip}\")[0] != 0:",
                                  "    if False:"),), "L5-guards"),
    "back-sha-unchecked": ((("    if [_sha256(local)] != digest:", "    if False:"),), "L5-guards"),
    "back-tip-unchecked": ((("    if got != tip:", "    if False:"),), "L5-guards"),
    "back-scan-empty-admitted": ((("    if not isinstance(n, int) or n < 1:", "    if not isinstance(n, int):"),),
                                 "L5-guards"),
    "reserve-presence-unchecked": ((("test -f {child}/athena-reserve || exit 1; ", ""),), "L2-run"),
    "dead-hold-pid-printed": ((("if ! kill -0 $(cat {child}/walk.pid) 2>/dev/null; then ", "if false; then "),),
                              "L2-run"),
    "dead-hold-claim-kept": ((("then rm -f {RESERVATION}; \"\n             f\"tail -5", "then \"\n             f\"tail -5"),),
                             "L6-start"),
    "config-parent-dropped": (((" {machine_gate.ENV_SLOTS}={machine_gate.SLOTS} {CONFIG_PARENT_ENV}={CONFIG_PARENT}",
                                " {machine_gate.ENV_SLOTS}={machine_gate.SLOTS}"),), "L7-env"),
    "identity-dropped": ((("    walk_env = f\"{env} {COMMIT_IDENTITY}\"", "    walk_env = env"),), "L7-env"),
    "blob-bound-dropped": ((("            limit = min(BLOB_MAX_BYTES, len(data) * BLOB_MAX_RATIO, BLOB_TOTAL_MAX - total)",
                             "            limit = 1 << 40"),), "L8-blobs"),
    "absolute-cap-dropped": ((("            limit = min(BLOB_MAX_BYTES, len(data) * BLOB_MAX_RATIO, BLOB_TOTAL_MAX - total)",
                               "            limit = min(len(data) * BLOB_MAX_RATIO, BLOB_TOTAL_MAX - total)"),), "L8-blobs"),
    "count-cap-dropped": ((("    if len(cands) > BLOB_MAX_COUNT:", "    if False:"),), "L8-blobs"),
    "blob-path-unchecked": ((("            if not all(EVIDENCE_BLOB.fullmatch(p) and p.rsplit(\"/\", 1)[1] == name for p in where):",
                              "            if False:"),), "L8-blobs"),
    "blob-name-unbound": ((("EVIDENCE_BLOB.fullmatch(p) and p.rsplit(\"/\", 1)[1] == name for p in where",
                            "EVIDENCE_BLOB.fullmatch(p) for p in where"),), "L8-blobs"),
    "blob-head-history-unchecked": ((("            if oid in in_head:", "            if False:"),), "L8-blobs"),
    "decompressed-findings-ignored": ((("        if problems:\n            names = sorted(", "        if False:\n            names = sorted("),),
                                       "L8-blobs"),
    "header-fields-unscanned": ((("_write_private(os.path.join(src, oid + \".header\"),",
                                  "(lambda *x: None)(os.path.join(src, oid + \".header\"),"),), "L8-blobs"),
    "reserved-bits-admitted": ((("    if flg & GZ_RESERVED:", "    if False:"),), "L8-blobs"),
    "fhcrc-unchecked": ((("        if len(data) < i + 2 or int.from_bytes(data[i:i + 2], \"little\") != zlib.crc32(data[:i]) & 0xFFFF:",
                          "        if len(data) < i + 2:"),), "L8-blobs"),
    "trailer-unchecked": ((("    if int.from_bytes(trailer[:4], \"little\") != crc or", "    if False and int.from_bytes(trailer[:4], \"little\") != crc or"),), "L8-blobs"),
    "text-gzip-skipped": ((("        if head_bytes[:2] == b\"\\x1f\\x8b\" or b\"\\0\" in head_bytes:", "        if b\"\\0\" in head_bytes:"),), "L8-blobs"),
    "allow-comments-honoured": ((("\"--exit-code\", \"0\", \"--ignore-gitleaks-allow\",", "\"--exit-code\", \"0\","),),
                                "L8-blobs"),
    "canary-missing-ignored": ((("        if canaries.get(name, 0) != 1:", "        if False:"),), "L8-blobs"),
    "field-cap-dropped": ((("            if j - i > GZ_FIELD_MAX:", "            if False:"),), "L8-blobs"),
    "commit-object-unscanned": ((("_git_out(repo, \"cat-file\", \"commit\", commit,", "_git_out(repo, \"log\", \"-1\", \"--format=%B\", commit,"),),
                                "L8-blobs"),
    "commit-scan-dropped": ((("            _write_private(os.path.join(src, f\"commit-{commit}\"), ",
                              "            None and _write_private(os.path.join(src, f\"commit-{commit}\"), "),), "L8-blobs"),
    "paths-unscanned": ((("            _write_private(os.path.join(src, f\"paths-{commit}\"), _git_out(",
                          "            None and _write_private(os.path.join(src, f\"paths-{commit}\"), _git_out("),), "L8-blobs"),
    # Named equivalent, no witness: the 1f 8b magic check in gzip_header is the only gate before parsing; dropping it
    # leaves the method byte and zlib's raw inflate to refuse a non-gzip, so only the refusal's words change.
    "back-scan-plain": ((("        n = suite_mod.scan_unpublished(", "        n = 1 or suite_mod.scan_unpublished("),),
                        "L3-fetch"),
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

    def test_l5_guards(self):
        self.assertEqual(l5(wl), [])

    def test_l6_start(self):
        self.assertEqual(l6(wl), [])

    def test_l7_env(self):
        self.assertEqual(l7(wl), [])

    def test_l8_blobs(self):
        self.assertEqual(l8(wl), [])

    def test_pinned_tree_is_variants(self):
        import variants
        self.assertEqual(wl.PINNED_TREE, variants.PINNED_TREE)

    def test_reserve_pin_is_the_runbooks(self):
        self.assertTrue(wl.RESERVE_SHA256.startswith("efeecb3a"))


ATHENA_SUITE_PY = os.environ.get("GAP4_ATHENA_SUITE_PY", "/Users/javrodher/glitch/workspaces/aegis/ops/athena_suite.py")
# The one skip the battery allows (glitch-6b's ruling, closure review MINOR A; test_round4.SKIP_ALLOWED holds this exact
# text): fired ONLY when athena_suite.py (GAP4_ATHENA_SUITE_PY, else the operator's checkout path) or gitleaks is absent.
REAL_SCAN_SKIP = ("REAL RETURN SCAN NOT RUN: athena_suite.py (GAP4_ATHENA_SUITE_PY) or gitleaks is absent on this "
                  "machine; the real-scanner proof is the Mac run in the box lane report, the faked back-scan "
                  "witnesses run everywhere, and the first real walk's fetch is live proof")


def _real_gitleaks():
    import shutil
    for c in (shutil.which("gitleaks"), os.path.expanduser("~/.local/bin/gitleaks"),
              "/home/javier/gap4-tools/gitleaks-8.30.1/gitleaks"):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def _fake_token():
    import secrets
    import string
    return "ghp_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36))


class TestRealReturnScan(unittest.TestCase):
    """The review's MAJOR 1, on the REAL scanner: athena_suite.scan_unpublished and gitleaks themselves, through
    fetch. A `gitleaks:allow` line, a token in a commit message and a token inside a .json.gz blob each refuse, and
    nothing reaches the records clone; a clean walk commit is fetched. Synthetic tokens made at run time, never
    printed. Where athena_suite.py or gitleaks is not on this machine (the athena battery's clone has no aegis
    checkout), the class is skipped BY NAME, never passed: the lane report carries this machine's run."""

    def setUp(self):
        self.gitleaks = _real_gitleaks()
        if not os.path.isfile(ATHENA_SUITE_PY) or self.gitleaks is None:
            self.skipTest(REAL_SCAN_SKIP)
        self.suite = wl.load_suite(ATHENA_SUITE_PY)

    def case(self, make_commit):
        with tempfile.TemporaryDirectory() as t:
            _, got, repo, _, _ = fetch_rig(wl, t, suite=self.suite, gitleaks=self.gitleaks, make_commit=make_commit)
            return got, walk_branches(repo)

    def test_allow_comment_refuses(self):
        def commit(a):
            Path(a, "notes.txt").write_text(f"token = {_fake_token()}  # gitleaks:allow\n")
            git("-C", a, "add", "notes.txt")
            git("-C", a, "commit", "-q", "-m", "notes")
        got, branches = self.case(commit)
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertEqual(branches, "")

    def test_message_token_refuses(self):
        def commit(a):
            Path(a, "m.txt").write_text("m\n")
            git("-C", a, "add", "m.txt")
            git("-C", a, "commit", "-q", "-m", f"walk note: token {_fake_token()}")
        got, branches = self.case(commit)
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertEqual(branches, "")

    def test_binary_blob_refuses(self):
        """A gzip OUTSIDE rehearsals/<walk>/evidence/blobs/ refuses (it is not the watcher's evidence)."""
        import gzip

        def commit(a):
            Path(a, "rec.json.gz").write_bytes(gzip.compress(json.dumps({"token": _fake_token()}).encode()))
            git("-C", a, "add", "rec.json.gz")
            git("-C", a, "commit", "-q", "-m", "record")
        got, branches = self.case(commit)
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertEqual(branches, "")

    def evidence_commit(self, files):
        def commit(a):
            for path, data in files.items():
                Path(a, path).parent.mkdir(parents=True, exist_ok=True)
                Path(a, path).write_bytes(data)
                git("-C", a, "add", path)
            git("-C", a, "commit", "-q", "-m", "walk")
        return commit

    def test_evidence_gzip_with_a_token_refuses(self):
        import gzip
        data = gzip.compress(json.dumps({"text": f"token = {_fake_token()}"}).encode())
        got, branches = self.case(self.evidence_commit({evidence_path("w001", data): data}))
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertIn("private scan refused", str(got))
        self.assertEqual(branches, "")

    def test_clean_evidence_gzip_is_fetched(self):
        import gzip
        data = gzip.compress(json.dumps({"path": "plan/approved.json", "op": "open"}).encode())
        got, branches = self.case(self.evidence_commit({evidence_path("w001", data): data}))
        self.assertIsInstance(got, dict, got)
        self.assertIn("refs/heads/walk/w-AbCd1234", branches)

    def test_non_gzip_evidence_blob_refuses(self):
        data = b"\x00\x01raw evidence"
        got, branches = self.case(self.evidence_commit({evidence_path("w001", data): data}))
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertEqual(branches, "")

    def test_evidence_gzip_bomb_refuses(self):
        import gzip
        data = gzip.compress(b"\0" * (20 * 1024 * 1024))
        got, branches = self.case(self.evidence_commit({evidence_path("w001", data): data}))
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertEqual(branches, "")

    def header_case(self, **field):
        data = make_gz(json.dumps({"op": "open"}).encode(), **{k: f"token = {_fake_token()}".encode() for k in field})
        got, branches = self.case(self.evidence_commit({evidence_path("w001", data): data}))
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertIn("private scan refused", str(got))
        self.assertEqual(branches, "")

    def test_token_in_gzip_fextra_refuses(self):
        self.header_case(extra=True)

    def test_token_in_gzip_fname_refuses(self):
        self.header_case(name=True)

    def test_token_in_gzip_fcomment_refuses(self):
        self.header_case(comment=True)

    def test_allow_line_inside_evidence_gzip_refuses(self):
        import gzip
        data = gzip.compress(f"token = {_fake_token()}  # gitleaks:allow\n".encode())
        got, branches = self.case(self.evidence_commit({evidence_path("w001", data): data}))
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertIn("private scan refused", str(got))
        self.assertEqual(branches, "")

    def test_text_looking_gzip_is_not_skipped(self):
        data = b"\x1f\x8b\x08\x01" + b"A" * 60
        got, branches = self.case(self.evidence_commit({"evals/gap-study-4/rehearsals/w001/notes.txt": data}))
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertEqual(branches, "")

    def signature_case(self, prefix: bytes):
        import gzip
        data = gzip.compress(prefix + b"\nfill\n" + f"token = {_fake_token()}\n".encode())
        got, branches = self.case(self.evidence_commit({evidence_path("w001", data): data}))
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertIn("private scan refused", str(got))
        self.assertEqual(branches, "")

    def test_gzip_signature_payload_refuses(self):
        self.signature_case(b"\x1f\x8b\x08y")

    def test_bzip2_signature_payload_refuses(self):
        self.signature_case(b"BZh9")

    def test_zstd_signature_payload_refuses(self):
        self.signature_case(b"\x28\xb5\x2f\xfd")

    def test_7z_signature_payload_refuses(self):
        self.signature_case(b"7z\xbc\xaf\x27\x1c")

    def test_zip_signature_payload_refuses(self):
        self.signature_case(b"PK\x03\x04")

    def test_tar_ustar_at_257_payload_refuses(self):
        self.signature_case(b"x" * 257 + b"ustar00")

    def message_case(self, pad: int):
        def commit(a):
            Path(a, "w.txt").write_text("w\n")
            git("-C", a, "add", "w.txt")
            git("-C", a, "commit", "-q", "-m", "x" * pad + "ustar00\n" + f"token = {_fake_token()}\n")
        got, branches = self.case(commit)
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertEqual(branches, "")

    def test_ustar_at_257_of_the_message_refuses(self):
        self.message_case(257)

    def test_ustar_at_257_of_athena_suites_message_stream_refuses(self):
        # athena_suite's stdin stream is `%H%n%B`: 41 bytes (the id and its newline) come first, so ustar at 216 of
        # the message sits at 257 of that stream, where gitleaks skips it (the closure review's MAJOR B reproduction)
        self.message_case(257 - 41)

    def test_token_in_a_path_refuses(self):
        tok = _fake_token()

        def commit(a):
            path = f"evals/gap-study-4/rehearsals/w001/{tok}.txt"
            Path(a, path).parent.mkdir(parents=True, exist_ok=True)
            Path(a, path).write_text("w\n")
            git("-C", a, "add", path)
            git("-C", a, "commit", "-q", "-m", "walk")
        got, branches = self.case(commit)
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertEqual(branches, "")

    def test_token_in_the_author_refuses(self):
        tok = _fake_token()

        def commit(a):
            Path(a, "w.txt").write_text("w\n")
            git("-C", a, "add", "w.txt")
            git("-C", a, "commit", "-q", "--author", f"{tok} <a@invalid>", "-m", "walk")
        got, branches = self.case(commit)
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertEqual(branches, "")

    def test_clean_commit_is_fetched(self):
        got, branches = self.case(None)
        self.assertIsInstance(got, dict, got)
        self.assertIn("refs/heads/walk/w-AbCd1234", branches)


class TestSkipRule(unittest.TestCase):
    """The battery allows exactly REAL_SCAN_SKIP, and any other skip reason still fails it (closure review MINOR A)."""

    def test_only_the_real_scan_skip_is_allowed(self):
        import test_round4
        self.assertEqual(test_round4.SKIP_ALLOWED, (REAL_SCAN_SKIP,))

    def run_battery(self, body):
        import contextlib
        import io
        import test_round4
        with tempfile.TemporaryDirectory() as t:
            Path(t, "test_skipping.py").write_text(textwrap.dedent(body))
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                rc = test_round4.main(Path(t))
            sys.modules.pop("test_skipping", None)
            return rc, out.getvalue()

    def test_the_allowed_skip_passes_and_another_is_banned(self):
        allowed = f"""
            import unittest
            class T(unittest.TestCase):
                def test_runs(self):
                    pass
                def test_allowed(self):
                    self.skipTest({REAL_SCAN_SKIP!r})
            """
        rc, out = self.run_battery(allowed)
        self.assertEqual(rc, 0, out)
        other = allowed + """
                def test_other(self):
                    self.skipTest("REAL RETURN SCAN NOT RUN: for another reason")
            """
        rc, out = self.run_battery(other)
        self.assertEqual(rc, 1, out)
        self.assertIn("skipped, and its reason is not in SKIP_ALLOWED", out)
        self.assertIn("for another reason", out)


class TestWitnesses(unittest.TestCase):
    def test_every_witness_is_red_by_its_own_clause(self):
        for name, (edits, clause) in WITNESSES.items():
            with self.subTest(name=name):
                self.assertEqual(CHECKS[clause](wl), [], f"{name}: {clause} is not green on the tree")
                got = CHECKS[clause](witness(edits))
                self.assertTrue([x for x in got if x.startswith(clause + ":")], f"{name}: survived")


if __name__ == "__main__":
    unittest.main()
