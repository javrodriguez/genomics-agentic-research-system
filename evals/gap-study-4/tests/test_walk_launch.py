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


class FakeSuite:
    """athena_suite's functions as outward_scan calls them, logging into the runner's call list."""
    ALLOWLIST = "/fake/athena_suite_allowlist.json"
    PUBLIC_REFERENCE = {"gars": "https://example.invalid/gars.git"}

    def __init__(self, log, *, public=("a" * 40,), public_error=False, nonpublic_finding=False, hits=()):
        self.log, self.public, self.public_error = log, list(public), public_error
        self.scans = []
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

    def rulings_file(self, repo):
        return os.path.join(repo, ".git", "hooks", "glitch-gitleaksignore")

    def scan_unpublished(self, repo, sha, workdir, gitleaks, public_shas, rulings, allow_blobs, ruled, ruled_used,
                         ruled_messages):
        self.log.append(("suite", ["scan_unpublished", sha, list(public_shas), rulings, ruled, ruled_messages]))
        self.scans.append({"repo": repo, "sha": sha, "public": list(public_shas), "rulings": rulings,
                           "allow_blobs": allow_blobs, "ruled": ruled, "ruled_messages": ruled_messages})
        if self.nonpublic_finding:
            raise RuntimeError("gitleaks found 1 item(s) in commits that are not public: x.txt:generic-api-key:1")
        return 3


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


def fetch_rig(mod, t, *, walk_state="exit=0", commit_on_athena=True, suite_kw=None, suite=None, gitleaks="gitleaks",
              make_commit=None, runner_kw=None, after_runner=None):
    """A Mac records clone at `head`, an athena clone with one walk commit (or make_commit(athena)), the real
    `<head>..main` bundle; fetch through the fake athena with a fake athena_suite (or the real one, `suite`)."""
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


CHECKS = {"L1-ship": l1, "L2-run": l2, "L3-fetch": l3, "L4-bounds": l4, "L5-guards": l5}


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
    "hold-dropped": ((("    held = (f\"python3 {child}/athena-reserve hold --by {hid} -- {env} \"",
                       "    held = (f\"{env} \""),), "L2-run"),
    "claim-dropped": ((("python3 -I -c {shlex.quote(claim)} {RESERVATION} {hid}; ", ""),), "L2-run"),
    "claim-not-exclusive": ((("os.O_WRONLY | os.O_CREAT | os.O_EXCL, ", "os.O_WRONLY | os.O_CREAT, "),), "L2-run"),
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

    def test_pinned_tree_is_variants(self):
        import variants
        self.assertEqual(wl.PINNED_TREE, variants.PINNED_TREE)

    def test_reserve_pin_is_the_runbooks(self):
        self.assertTrue(wl.RESERVE_SHA256.startswith("efeecb3a"))


ATHENA_SUITE_PY = os.environ.get("GAP4_ATHENA_SUITE_PY", "/Users/javrodher/glitch/workspaces/aegis/ops/athena_suite.py")


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
        if not os.path.isfile(ATHENA_SUITE_PY):
            self.skipTest(f"REAL RETURN SCAN NOT RUN: no athena_suite.py at {ATHENA_SUITE_PY}")
        self.gitleaks = _real_gitleaks()
        if self.gitleaks is None:
            self.skipTest("REAL RETURN SCAN NOT RUN: no gitleaks binary on this machine")
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
        import gzip

        def commit(a):
            Path(a, "rec.json.gz").write_bytes(gzip.compress(json.dumps({"token": _fake_token()}).encode()))
            git("-C", a, "add", "rec.json.gz")
            git("-C", a, "commit", "-q", "-m", "record")
        got, branches = self.case(commit)
        self.assertIsInstance(got, wl.LaunchRefused)
        self.assertEqual(branches, "")

    def test_clean_commit_is_fetched(self):
        got, branches = self.case(None)
        self.assertIsInstance(got, dict, got)
        self.assertIn("refs/heads/walk/w-AbCd1234", branches)


class TestWitnesses(unittest.TestCase):
    def test_every_witness_is_red_by_its_own_clause(self):
        for name, (edits, clause) in WITNESSES.items():
            with self.subTest(name=name):
                self.assertEqual(CHECKS[clause](wl), [], f"{name}: {clause} is not green on the tree")
                got = CHECKS[clause](witness(edits))
                self.assertTrue([x for x in got if x.startswith(clause + ":")], f"{name}: survived")


if __name__ == "__main__":
    unittest.main()
