#!/usr/bin/env python3
"""The take's ownership road (stub-take review finding 9; glitch-06's assignment, 14 Oct 2026).

Under athena's rootless Docker the agent (container uid 10001) maps to a host uid the host user does not own (110000),
so the run tree and the per-take config folder must be GRANTED to the agent before launch, and the evidence folder to
the sidecar's watcher (10002, which must write it), and all three RESTORED to the host user (container uid 0, which
is the host user) after teardown, before postflight, the scan and remove_config_dir.
Without the restore, preflight.postflight reads the config folder as unreadable and fails closed, and the scan and
the removal cannot read or delete what the agent wrote (measured in the stub take, lane-reports/stub-take-20261014).

    grant(runtime, image=, run_tree=, config_dir=, evidence_dir=, caller_env=None) -> record    before run_take.launch
    restore(runtime, image=, run_tree=, config_dir=, evidence_dir=, ids=, caller_env=None) -> record
                                                       after run_take.teardown; before postflight, scan, removal

Each step is one one-shot root container of the take image (by its full id), with only CHOWN and DAC_OVERRIDE, no
network, no new privileges, the one folder bind-mounted at /scratch, running OWN_PROGRAM: measure_live.OWN's
reviewed descriptor walk (never follows a link: every open is O_NOFOLLOW; a socket, fifo or device refuses), with one
departure: a symbolic link the agent left is chowned itself (lchown, never followed) instead of refusing the whole
walk. The folders are named by exact, normalised absolute paths; nothing is resolved or globbed.

FAILING CLOSED. grant raises OwnershipError at the first failed step (the take must not launch). restore runs every
step, verifies host-side that every entry of the three folders is owned by the host user (lstat, links never followed),
and raises OwnershipError carrying the record when any step or check failed: the take's folders are then kept for a
human, never removed or scanned half-owned. restore refuses to start while any recorded container is still present
(run_take.leaked), since a live agent could write behind the restore.

No model, no login, no network. Standard library only (plus run_take's runtime protocol and checks).
"""

from __future__ import annotations

import os
import re

from box import run_take

HOST_UID = 0                                    # container uid 0 is the host user under rootless Docker
AGENT_UID = int(run_take.AGENT_USER.split(":")[0])
WATCHER_UID = 10002                             # merge binding 1: every image.lock's users.watcher.uid (test-bound)
MOUNT = "/scratch"
CAPS = ("CHOWN", "DAC_OVERRIDE")
STEP_TIMEOUT_S = 600
_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")

# measure_live.OWN (the reviewed walk), plus the link branch: a link is lchowned through its parent's descriptor and
# never opened. Every other non-folder, non-file entry still refuses.
OWN_PROGRAM = '''import os,stat,sys
uid=int(sys.argv[1])
def visit(fd):
 st=os.fstat(fd)
 if not (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)):raise RuntimeError("nonregular refused")
 if stat.S_ISDIR(st.st_mode):
  for name in os.listdir(fd):
   lst=os.stat(name,dir_fd=fd,follow_symlinks=False)
   if stat.S_ISLNK(lst.st_mode):
    os.chown(name,uid,uid,dir_fd=fd,follow_symlinks=False)
    continue
   child=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
   try:visit(child)
   finally:os.close(child)
 os.fchown(fd,uid,uid)
fd=os.open("/scratch",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
try:visit(fd)
finally:os.close(fd)
'''


class OwnershipError(RuntimeError):
    """A grant or restore step failed; `record` names each step and its outcome."""

    def __init__(self, message: str, record: dict):
        super().__init__(message)
        self.record = record


def _folders(run_tree, config_dir, evidence_dir) -> list:
    """(name, path, the uid it is granted to), run tree first; exact paths, none inside another, none a link."""
    out = [("run_tree", run_take._abs_path(run_tree, "run_tree"), AGENT_UID),
           ("config_dir", run_take._abs_path(config_dir, "config_dir"), AGENT_UID),
           ("evidence_dir", run_take._abs_path(evidence_dir, "evidence_dir"), WATCHER_UID)]
    for i, (n1, p1, _u) in enumerate(out):
        for n2, p2, _v in out[i + 1:]:
            if run_take._inside(p1, p2) or run_take._inside(p2, p1):
                raise run_take.Refused(f"{n1} and {n2} must not contain each other")
    for name, p, _u in out:
        if os.path.islink(p) or not os.path.isdir(p):
            raise run_take.Refused(f"{name} must be an existing folder, never a link")
    if not run_take.outside_every_repository(out[1][1]):
        raise run_take.Refused("the per-take config folder must sit outside every repository")
    return out


def _image(image) -> str:
    if not isinstance(image, str) or not _IMAGE_ID.fullmatch(image):
        raise run_take.Refused("the ownership step runs the take image by its full id, sha256:<64 hex>")
    return image


def own_argv(image: str, path: str, uid: int) -> list:
    """One one-shot root container that chowns the whole folder at `path` to container uid `uid`."""
    if uid not in (AGENT_UID, WATCHER_UID, HOST_UID):
        raise run_take.Refused(f"a folder is owned by the agent ({AGENT_UID}), the watcher ({WATCHER_UID}) or the host "
                               f"user ({HOST_UID}) only")
    argv = [run_take.RUNTIME_CLIENT, "run", "--rm", "--pull=never", "--network", "none", "--user", "0:0",
            "--cap-drop", "ALL"]
    for cap in CAPS:
        argv += ["--cap-add", cap]
    argv += ["--security-opt", "no-new-privileges",
             "--mount", f"type=bind,source={run_take._abs_path(path, 'path')},target={MOUNT}",
             _image(image), "/usr/bin/python3", "-I", "-S", "-c", OWN_PROGRAM, str(uid)]
    return argv


def _run(runtime, name: str, argv: list, env: dict) -> dict:
    try:
        c = runtime.run(argv, env=env, timeout=STEP_TIMEOUT_S)
    except TimeoutError:
        return {"step": name, "returncode": None, "timed_out": True}
    return {"step": name, "returncode": c.returncode, "stderr": c.stderr[-500:] if c.returncode else ""}


def grant(runtime, *, image: str, run_tree: str, config_dir: str, evidence_dir: str, caller_env=None) -> dict:
    """The run tree and config folder to the agent, the evidence folder to the watcher, in that order. The first
    failure raises (the take must not launch)."""
    folders = _folders(run_tree, config_dir, evidence_dir)
    _image(image)
    env = run_take.runtime_env(caller_env)
    steps = []
    for name, path, uid in folders:
        step = _run(runtime, f"grant-{name}", own_argv(image, path, uid), env)
        steps.append(step)
        if step["returncode"] != 0:
            raise OwnershipError(f"grant-{name} failed: the take is refused before launch",
                                 {"ok": False, "steps": steps})
    return {"ok": True, "steps": steps}


def owner_problems(path: str, uid: int) -> list:
    """Every entry under `path` (itself included) not owned by host uid `uid`, by lstat (links never followed)."""
    out = []
    try:
        if os.lstat(path).st_uid != uid:
            out.append(f"{path}: owner is not the host user")
    except OSError as e:
        return [f"{path}: unreadable ({type(e).__name__})"]

    def onerror(e):
        out.append(f"{getattr(e, 'filename', path)}: unreadable ({type(e).__name__})")
    for root, dirs, files in os.walk(path, onerror=onerror, followlinks=False):
        for n in dirs + files:
            p = os.path.join(root, n)
            try:
                if os.lstat(p).st_uid != uid:
                    out.append(f"{p}: owner is not the host user")
            except OSError as e:
                out.append(f"{p}: unreadable ({type(e).__name__})")
    return out


def restore(runtime, *, image: str, run_tree: str, config_dir: str, evidence_dir: str, ids, caller_env=None) -> dict:
    """The three folders back to the host user, after teardown. Every step runs; any failure raises with the record."""
    folders = _folders(run_tree, config_dir, evidence_dir)
    _image(image)
    still = run_take.leaked(runtime, list(ids), caller_env=caller_env)
    if still:
        raise OwnershipError("restore refused: a recorded container is still present",
                             {"ok": False, "steps": [], "present": still})
    env = run_take.runtime_env(caller_env)
    steps, problems = [], []
    for name, path, _uid in folders:
        step = _run(runtime, f"restore-{name}", own_argv(image, path, HOST_UID), env)
        steps.append(step)
        if step["returncode"] != 0:
            problems.append(f"restore-{name} exited {step['returncode']}")
    for name, path, _uid in folders:
        problems += owner_problems(path, os.getuid())
    record = {"ok": not problems, "steps": steps, "problems": problems[:50]}
    if problems:
        raise OwnershipError(f"restore failed ({len(problems)} problem(s)): the take's folders are kept for a human",
                             record)
    return record
