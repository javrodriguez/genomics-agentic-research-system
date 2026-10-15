#!/usr/bin/env python3
"""The CP6 walk's launch road, Mac to athena and back (box lane; glitch-6b's ruling of 15 Oct 2026, item 3: a git
bundle out and back). Run on the Mac. It pushes nothing, places no login and reads no secret: the walk's login file is
the Claude1 file already on athena (run_take.WALK_LOGIN_FILES), read there by the walk itself.

    python3 evals/gap-study-4/box/walk_launch.py ship  --repo <Mac clone> --ref <branch> --suite <athena_suite.py>
                                                       --reserve <athena-reserve> --gitleaks <binary> --work <Mac folder>
        1. the Mac pre-check (machine_gate.mac_precheck): no athena suite in progress, busy runs never ran;
        2. the ref's head carries the pinned tree's history (variants.PINNED_TREE is an ancestor);
        3. `git bundle create` of the ref (the whole history), `git bundle verify`;
        4. athena_suite's own outward rule over a scratch clone of the bundle (outward_scan): no secret-shaped file,
           and gitleaks over every carried commit the public GARS remote does not serve, else refuse;
        5. a new mode-700 neutral child on athena (`mktemp -d /home/javier/w-XXXXXXXX`), the bundle and athena-reserve
           copied there, each sha256 read back on athena; athena clones the bundle and its HEAD must be the head.
        Prints one JSON line: the child, the head, the bundle's sha256.

    python3 .../walk_launch.py run --child <athena child> --head <sha> --walk <id> --task <t> --half <h>
                                   --wording <w> --arm <a> --model <m> --reason <why>
        On athena, under umask 0022 (the box lane's run 7 finding: the evidence folder must stay host-readable):
        the athena gate (machine_gate athena-check, the reservation absent: a hold would overwrite another), then
        `nohup python3 <child>/athena-reserve hold --by <hold id> -- env GAP4_SUITE_ACCOUNT=athena-suite
        GAP4_RESERVATION=<reserved.json> GAP4_OWN_HOLD=<hold id> python3 -B <repo>/evals/gap-study-4/walk_runner.py
        ...`, so every athena suite launched during the walk is refused `reserved` and the walk's own gate admits its
        own hold only. Prints the pid.

    python3 .../walk_launch.py status --child <athena child>
        `running` while the recorded pid lives, else the walk's exit code from its exit file.

    python3 .../walk_launch.py fetch --child <athena child> --head <sha> --ref <branch> --records <Mac clone>
                                     --gitleaks <binary> --work <Mac folder> --suite <athena_suite.py>
        On athena, a bundle of the new commits only (`<head>..<ref>`); copied to the Mac, its sha256 read back;
        fetched into a scratch shared clone of the records clone, athena_suite's scan_unpublished at the tip with
        public_shas=[head] and no allowance at all (allow comments ignored, messages and binary blobs refused); then
        fetched into the records clone as refs/heads/walk/<child name>. A walk that made no
        commit has nothing to fetch and says so.

Every remote and local command goes through one Runner, so tests drive the whole road on fakes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import machine_gate  # noqa: E402

PINNED_TREE = "844a4ce0d89437ca043363981a86096f6383a141"      # variants.PINNED_TREE; a test binds the two
HOST = "athena"
SSH = ("ssh", "-a", "-x", "-o", "BatchMode=yes")
SCP = ("scp", "-q", "-o", "BatchMode=yes", "-o", "ForwardAgent=no", "-o", "ForwardX11=no")
CHILD_PARENT = "/home/javier"
CHILD = re.compile(r"/home/javier/w-[A-Za-z0-9]{8}")
UMASK = "0022"
SUITE_ACCOUNT = machine_gate.SUITE_ACCOUNT
RESERVATION = machine_gate.RESERVATION
# athena-reserve as the runbook pins it (FOREMAN-RUNBOOK section 13, `efeecb3a…`; aegis ops/node1/athena-reserve).
RESERVE_SHA256 = "efeecb3a606d6bb9a23c77b850b8ef1f61cb9aed0f4bcdb53c3ff3b9b039062e"
HEX40 = re.compile(r"[0-9a-f]{40}")
WALK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
CELL = ("task", "half", "wording", "arm", "model")
# The outward bundle's scan is athena_suite's own rule (glitch-6b, 15 Oct 2026), its code reused: every carried commit the
# PUBLIC GARS remote does not already serve is scanned (scan_unpublished, after fetch_public_refs of
# PUBLIC_REFERENCE["gars"] into a plain scratch clone of the bundle, with the push door's committed rulings and the
# committed allowlist exactly as cmd_run passes them), and nothing it does serve. Shipping an already-public commit to
# athena discloses nothing new; this is not a ruling on any finding. The new-commits bundle coming back gets no
# allowance at all.
SUITE_KIND = "gars"


class LaunchRefused(RuntimeError):
    """A step of the road refused; the message names the rule, never a secret."""


class Runner:
    """The one place a process starts. local(argv) and remote(cmd) return (code, stdout, stderr)."""

    def local(self, argv, *, timeout=3600):
        p = subprocess.run(list(argv), capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr

    def remote(self, cmd: str, *, timeout=3600):
        return self.local(list(SSH) + [HOST, "--", cmd], timeout=timeout)

    def copy_to(self, src: str, dst: str):
        return self.local(list(SCP) + [src, f"{HOST}:{dst}"])

    def copy_from(self, src: str, dst: str):
        return self.local(list(SCP) + [f"{HOST}:{src}", dst])


def _ok(res, what):
    code, out, err = res
    if code != 0:
        raise LaunchRefused(f"{what} failed (exit {code}): {(err or '').strip()[:200]}")
    return out


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _child(child: str) -> str:
    if not isinstance(child, str) or not CHILD.fullmatch(child):
        raise LaunchRefused(f"the athena child must be a new /home/javier/w-XXXXXXXX folder, not {child!r}")
    return child


def hold_id(walk: str) -> str:
    if not isinstance(walk, str) or not WALK_ID.fullmatch(walk):
        raise LaunchRefused(f"the walk id {walk!r} is not one path segment")
    hid = f"gap4-walk-{walk}"
    if not machine_gate.HOLD_ID.match(hid):
        raise LaunchRefused(f"the hold id {hid!r} is not one athena-reserve accepts (BY_RE, 64 characters)")
    return hid


# ------------------------------------------------------------------------------------------------ ship
def load_suite(suite: str):
    """athena_suite.py from the operator's aegis checkout, loaded by path (its module level only defines names)."""
    import importlib.util
    if not isinstance(suite, str) or not os.path.isabs(suite) or not os.path.isfile(suite):
        raise LaunchRefused("the athena_suite.py path is not an existing absolute file")
    spec = importlib.util.spec_from_file_location("athena_suite_for_walk_launch", suite)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def outward_scan(suite_mod, *, repo: str, bundle: str, head: str, gitleaks: str, work: str) -> int:
    """athena_suite.cmd_run's checks over a scratch clone of the bundle, its own functions: the secret-shaped names
    (less the reviewed exemptions) and ignore files, then gitleaks over every commit the public GARS remote does not
    serve. Returns how many commits were scanned; any refusal raises."""
    os.makedirs(work, exist_ok=True)
    check = os.path.join(work, "check-clone")
    doc, _ = suite_mod.committed_allowlist(suite_mod.ALLOWLIST)
    reviewed, ruled, ruled_msgs = suite_mod.validate_allowlist(doc, SUITE_KIND)
    suite_mod.scratch_clone(bundle, check, work)
    hits, _ = suite_mod.exempt_reviewed(check, head, suite_mod.name_hits(check, head, ()), reviewed)
    hits += suite_mod.ignore_hits(check, head, work)
    if hits:
        raise LaunchRefused(f"the bundle would carry {len(hits)} secret-shaped file(s); nothing ships")
    public = suite_mod.fetch_public_refs(check, suite_mod.PUBLIC_REFERENCE[SUITE_KIND], work)
    if not public:
        raise LaunchRefused("the public GARS remote advertised nothing; nothing ships")
    return suite_mod.scan_unpublished(check, head, work, gitleaks, public, suite_mod.rulings_file(repo), (), ruled,
                                      [], ruled_msgs)


def ship(runner: Runner, *, repo: str, ref: str, suite: str, reserve: str, gitleaks: str, work: str,
         precheck=None, suite_module=None) -> dict:
    precheck = machine_gate.mac_precheck if precheck is None else precheck
    problems = precheck(suite)
    if problems:
        raise LaunchRefused("the Mac pre-check refuses: " + "; ".join(problems))
    if _sha256(reserve) != RESERVE_SHA256:
        raise LaunchRefused("athena-reserve is not the runbook's pinned bytes")
    head = _ok(runner.local(["git", "-C", repo, "rev-parse", "--verify", f"{ref}^{{commit}}"]), "rev-parse").strip()
    if not HEX40.fullmatch(head):
        raise LaunchRefused(f"the ref {ref!r} does not name one commit")
    if runner.local(["git", "-C", repo, "merge-base", "--is-ancestor", PINNED_TREE, head])[0] != 0:
        raise LaunchRefused(f"the head {head[:12]} does not carry the pinned tree {PINNED_TREE[:12]}'s history")
    os.makedirs(work, exist_ok=True)
    bundle = os.path.join(work, "walk-out.bundle")
    if os.path.lexists(bundle):
        raise LaunchRefused(f"{bundle} exists: a bundle is never overwritten")
    _ok(runner.local(["git", "-C", repo, "bundle", "create", bundle, ref]), "git bundle create")
    _ok(runner.local(["git", "-C", repo, "bundle", "verify", bundle]), "git bundle verify")
    heads = _ok(runner.local(["git", "bundle", "list-heads", bundle]), "git bundle list-heads").split()
    if heads != [head, f"refs/heads/{ref}"]:
        raise LaunchRefused("the bundle's heads are not exactly the ref at its head")
    suite_mod = load_suite(suite) if suite_module is None else suite_module
    try:
        scanned = outward_scan(suite_mod, repo=repo, bundle=bundle, head=head, gitleaks=gitleaks,
                               work=os.path.join(work, "outward-scan"))
    except LaunchRefused:
        raise
    except Exception as e:  # noqa: BLE001 - athena_suite's Refused, a git failure: nothing ships unscanned
        raise LaunchRefused(f"the outward scan refused, the bundle stays on the Mac: {type(e).__name__}: "
                            f"{str(e)[:300]}") from None
    digest = _sha256(bundle)
    child = _child(_ok(runner.remote(f"umask 077; mktemp -d {CHILD_PARENT}/w-XXXXXXXX"), "the athena child").strip())
    for src, name, want in ((bundle, "walk-out.bundle", digest), (reserve, "athena-reserve", RESERVE_SHA256)):
        _ok(runner.copy_to(src, f"{child}/{name}"), f"copying {name}")
        got = _ok(runner.remote(f"sha256sum {child}/{name}"), f"reading {name}'s sha256").split()[:1]
        if got != [want]:
            raise LaunchRefused(f"{name}'s sha256 on athena is not the Mac's")
    _ok(runner.remote(f"git clone -q -b {shlex.quote(ref)} {child}/walk-out.bundle {child}/repo"), "the athena clone")
    if _ok(runner.remote(f"git -C {child}/repo rev-parse HEAD"), "the athena head").strip() != head:
        raise LaunchRefused("athena's clone is not at the head")
    return {"child": child, "head": head, "bundle_sha256": digest, "scanned_commits": scanned}


# ------------------------------------------------------------------------------------------------ run
def run_command(*, child: str, walk: str, cell: dict, reason: str) -> str:
    """The one remote command that starts the walk under the hold (see the module's `run`)."""
    _child(child)
    hid = hold_id(walk)
    if set(cell) != set(CELL) or not all(isinstance(v, str) and v for v in cell.values()):
        raise LaunchRefused(f"the cell needs exactly {CELL}")
    if not isinstance(reason, str) or not reason.strip():
        raise LaunchRefused("a walk is run for a reason")
    repo = f"{child}/repo"
    env = (f"env {machine_gate.ENV_ACCOUNT}={SUITE_ACCOUNT} {machine_gate.ENV_RESERVATION}={RESERVATION} "
           f"{machine_gate.ENV_HOLD}={hid}")
    walk_argv = ["python3", "-B", f"{repo}/evals/gap-study-4/walk_runner.py", "--walk", walk]
    for k in CELL:
        walk_argv += [f"--{k}", cell[k]]
    walk_argv += ["--reason", reason]
    gate = f"{env} python3 -B {repo}/evals/gap-study-4/machine_gate.py athena-check"
    held = (f"python3 {child}/athena-reserve hold --by {hid} -- {env} "
            + " ".join(shlex.quote(a) for a in walk_argv))
    # The exit file is written by the shell around the hold, so a walk that died still leaves its code.
    body = f"{held}; echo $? > {child}/walk.exit"
    return (f"umask {UMASK}; set -e; test ! -e {RESERVATION}; {gate} > {child}/gate.out 2>&1; "
            f"nohup sh -c {shlex.quote(body)} > {child}/walk.log 2>&1 < /dev/null & echo $! > {child}/walk.pid; "
            f"cat {child}/walk.pid")


def run(runner: Runner, *, child: str, walk: str, cell: dict, reason: str) -> int:
    out = _ok(runner.remote(run_command(child=child, walk=walk, cell=cell, reason=reason)), "starting the walk")
    pid = out.strip().splitlines()[-1] if out.strip() else ""
    if not pid.isdigit():
        raise LaunchRefused("the walk's pid was not recorded")
    return int(pid)


def status(runner: Runner, *, child: str) -> str:
    _child(child)
    code, out, _ = runner.remote(f"if kill -0 $(cat {child}/walk.pid) 2>/dev/null; then echo running; "
                                 f"elif test -f {child}/walk.exit; then echo exit=$(cat {child}/walk.exit); "
                                 f"else echo lost; fi")
    if code != 0 or not out.strip():
        raise LaunchRefused("the walk's state cannot be read")
    return out.strip()


# ------------------------------------------------------------------------------------------------ fetch
def fetch(runner: Runner, *, child: str, head: str, ref: str, records: str, gitleaks: str, work: str,
          suite: str, suite_module=None) -> dict:
    _child(child)
    if not HEX40.fullmatch(head or ""):
        raise LaunchRefused("the head is one full commit id")
    st = status(runner, child=child)
    if st == "running":
        raise LaunchRefused("the walk is still running; nothing is fetched")
    tip = _ok(runner.remote(f"git -C {child}/repo rev-parse --verify {shlex.quote(ref)}^{{commit}}"),
              "the athena tip").strip()
    if tip == head:
        return {"state": st, "fetched": None, "why": "the walk made no commit"}
    if runner.remote(f"git -C {child}/repo merge-base --is-ancestor {head} {tip}")[0] != 0:
        raise LaunchRefused("athena's tip does not descend from the shipped head")
    _ok(runner.remote(f"git -C {child}/repo bundle create {child}/walk-back.bundle {head}..{shlex.quote(ref)}"),
        "the back bundle")
    digest = _ok(runner.remote(f"sha256sum {child}/walk-back.bundle"), "the back bundle's sha256").split()[:1]
    os.makedirs(work, exist_ok=True)
    local = os.path.join(work, "walk-back.bundle")
    if os.path.lexists(local):
        raise LaunchRefused(f"{local} exists: a bundle is never overwritten")
    _ok(runner.copy_from(f"{child}/walk-back.bundle", local), "copying the back bundle")
    if [_sha256(local)] != digest:
        raise LaunchRefused("the back bundle's sha256 on the Mac is not athena's")
    scratch = os.path.join(work, "back-scan")
    _ok(runner.local(["git", "clone", "-q", "--shared", "--no-checkout", records, scratch]), "the scan clone")
    _ok(runner.local(["git", "-C", scratch, "fetch", "-q", local, f"{ref}:refs/walk/back"]), "the scan fetch")
    got = _ok(runner.local(["git", "-C", scratch, "rev-parse", "refs/walk/back"]), "the fetched tip").strip()
    if got != tip:
        raise LaunchRefused("the back bundle's tip is not athena's")
    # The review's MAJOR 1 (15 Oct 2026): athena_suite's own scan_unpublished over the scratch clone at the tip, every
    # commit past the shipped head and NO allowance (no rulings, no allowed or ruled blobs, no ruled messages): its
    # --ignore-gitleaks-allow, empty ignore file, remerge diffs, commit-message scan and binary-blob refusal.
    suite_mod = load_suite(suite) if suite_module is None else suite_module
    try:
        n = suite_mod.scan_unpublished(scratch, tip, os.path.join(work, "back-scan-work"), gitleaks, [head], None,
                                       (), None, None, None)
    except Exception as e:  # noqa: BLE001 - athena_suite's Refused, a git or scanner failure: nothing is fetched
        raise LaunchRefused(f"the return scan refused, nothing is fetched: {type(e).__name__}: {str(e)[:300]}") \
            from None
    if not isinstance(n, int) or n < 1:
        raise LaunchRefused("the return scan scanned no commit past the head; nothing is fetched")
    name = os.path.basename(child)
    _ok(runner.local(["git", "-C", records, "fetch", "-q", local, f"{ref}:refs/heads/walk/{name}"]),
        "the records fetch")
    return {"state": st, "fetched": tip, "branch": f"walk/{name}", "bundle_sha256": digest[0]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="walk_launch.py")
    sub = ap.add_subparsers(dest="verb", required=True)
    s = sub.add_parser("ship")
    for k in ("repo", "ref", "suite", "reserve", "gitleaks", "work"):
        s.add_argument(f"--{k}", required=True)
    r = sub.add_parser("run")
    for k in ("child", "walk", "reason") + CELL:
        r.add_argument(f"--{k}", required=True)
    t = sub.add_parser("status")
    t.add_argument("--child", required=True)
    f = sub.add_parser("fetch")
    for k in ("child", "head", "ref", "records", "gitleaks", "work", "suite"):
        f.add_argument(f"--{k}", required=True)
    a = ap.parse_args(argv)
    runner = Runner()
    try:
        if a.verb == "ship":
            out = ship(runner, repo=a.repo, ref=a.ref, suite=a.suite, reserve=a.reserve, gitleaks=a.gitleaks,
                       work=a.work)
        elif a.verb == "run":
            out = {"pid": run(runner, child=a.child, walk=a.walk, cell={k: getattr(a, k) for k in CELL},
                              reason=a.reason)}
        elif a.verb == "status":
            out = {"state": status(runner, child=a.child)}
        else:
            out = fetch(runner, child=a.child, head=a.head, ref=a.ref, records=a.records, gitleaks=a.gitleaks,
                        work=a.work, suite=a.suite)
    except LaunchRefused as e:
        print(json.dumps({"refused": str(e)}))
        return 1
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
