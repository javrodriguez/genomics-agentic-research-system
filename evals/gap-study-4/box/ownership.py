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

import json
import os
import re

from box import run_take

HOST_UID = 0                                    # container uid 0 is the host user under rootless Docker
AGENT_UID = int(run_take.AGENT_USER.split(":")[0])
WATCHER_UID = 10002                             # merge binding 1: every image.lock's users.watcher.uid (test-bound)
MOUNT = "/scratch"
# Review minor 6, measured on athena (lane-reports/stub-take-20261014/ownership-caps-probe-20261014.json): the walk
# needs only CHOWN and DAC_READ_SEARCH (it opens read-only, lists folders and chowns), even over folders at 0700 and
# 0000 and files at 0600 and 0000 that the agent made; DAC_OVERRIDE is no longer granted.
CAPS = ("CHOWN", "DAC_READ_SEARCH")
STEP_TIMEOUT_S = 600
_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")

# measure_live.OWN (the reviewed walk), plus the link branch: a link is lchowned through its parent's descriptor and
# never opened. Every other non-folder, non-file entry still refuses. The STRICT block (review note 10, grant only):
# a regular file with another hard link, or any entry on another device, refuses, so a grant never chowns an inode
# that may also live outside the folder. A restore is not strict: links the agent made inside the tree are its own.
# The RESTORE block (glitch-06's ruling, 14 Oct 2026, on the athena probe's 0000 folder): after chowning, a restore
# adds the owner's rwx to every folder and the owner's rw to every file, never a group or other bit, never through a
# link, so the host user can verify, scan and remove what the agent left at any mode.
OWN_PROGRAM = '''import os,stat,sys
uid=int(sys.argv[1])
strict=sys.argv[2]=="strict"
restore=sys.argv[2]=="restore"
def visit(fd):
 st=os.fstat(fd)
 if not (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)):raise RuntimeError("nonregular refused")
 if strict and (st.st_dev!=root_dev or (stat.S_ISREG(st.st_mode) and st.st_nlink!=1)):raise RuntimeError("hard link or foreign device refused")
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
 if restore:os.fchmod(fd,stat.S_IMODE(os.fstat(fd).st_mode)|(0o700 if stat.S_ISDIR(st.st_mode) else 0o600))
fd=os.open("/scratch",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
root_dev=os.fstat(fd).st_dev
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


def own_argv(image: str, path: str, uid: int, *, strict: bool) -> list:
    """One one-shot root container that chowns the whole folder at `path` to container uid `uid` (strict: grant)."""
    if uid not in (AGENT_UID, WATCHER_UID, HOST_UID):
        raise run_take.Refused(f"a folder is owned by the agent ({AGENT_UID}), the watcher ({WATCHER_UID}) or the host "
                               f"user ({HOST_UID}) only")
    argv = [run_take.RUNTIME_CLIENT, "run", "--rm", "--pull=never", "--network", "none", "--user", "0:0",
            "--cap-drop", "ALL"]
    for cap in CAPS:
        argv += ["--cap-add", cap]
    argv += ["--security-opt", "no-new-privileges",
             "--mount", f"type=bind,source={run_take._abs_path(path, 'path')},target={MOUNT}",
             _image(image), "/usr/bin/python3", "-I", "-S", "-c", OWN_PROGRAM, str(uid),
             "strict" if strict is True else "restore"]
    return argv


def _run(runtime, name: str, argv: list, env: dict) -> dict:
    """One one-shot step, its container named by a cidfile (review minor 4): on a timeout it is removed by that id,
    and after every step no container of that id may be left. A step whose container is left, or whose id cannot
    be read, fails (returncode None)."""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="own-cid-")
    cidfile = os.path.join(tmp, "cid")
    argv = argv[:2] + ["--cidfile", cidfile] + argv[2:]
    try:
        try:
            c = runtime.run(argv, env=env, timeout=STEP_TIMEOUT_S)
            step = {"step": name, "returncode": c.returncode, "stderr": c.stderr[-500:] if c.returncode else "",
                    "stdout": c.stdout if name.startswith("operator-") else ""}
        except TimeoutError:
            step = {"step": name, "returncode": None, "timed_out": True}
        try:
            with open(cidfile, encoding="ascii") as fh:
                cid = fh.read().strip()
            run_take._check_id(cid, "the step's container id")
        except (OSError, UnicodeDecodeError, run_take.Refused):
            cid = None
        step["container_id"] = cid
        if cid is None:
            if step["returncode"] is None or step["returncode"] == 0:
                step["returncode"] = None
                step["left"] = "unknown: the step's container id could not be read"
            return step
        if step.get("timed_out"):
            runtime.run([run_take.RUNTIME_CLIENT, "rm", "--force", cid], env=env, timeout=run_take.STEP_TIMEOUT_S)
        try:
            left = run_take.leaked(runtime, [cid], caller_env=env)
        except run_take.Refused as e:
            left = [f"unknown ({e})"]
        if left:
            step["returncode"] = None
            step["left"] = left
        return step
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def grant(runtime, *, image: str, run_tree: str, config_dir: str, evidence_dir: str, caller_env=None) -> dict:
    """The run tree and config folder to the agent, the evidence folder to the watcher, in that order. The first
    failure raises (the take must not launch)."""
    folders = _folders(run_tree, config_dir, evidence_dir)
    _image(image)
    env = run_take.runtime_env(caller_env)
    steps = []
    for name, path, uid in folders:
        step = _run(runtime, f"grant-{name}", own_argv(image, path, uid, strict=True), env)
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
    """The three folders back to the host user, after teardown. Every step runs; any failure raises with the record.
    Every refusal is an OwnershipError (review minor 3), so the drive step routes one exception."""
    try:
        folders = _folders(run_tree, config_dir, evidence_dir)
        _image(image)
        still = run_take.leaked(runtime, list(ids), caller_env=caller_env)
    except run_take.Refused as e:
        raise OwnershipError(f"restore refused: {e}", {"ok": False, "steps": [], "refused": str(e)}) from None
    if still:
        raise OwnershipError("restore refused: a recorded container is still present",
                             {"ok": False, "steps": [], "present": still})
    env = run_take.runtime_env(caller_env)
    steps, problems = [], []
    for name, path, _uid in folders:
        step = _run(runtime, f"restore-{name}", own_argv(image, path, HOST_UID, strict=False), env)
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


# ------------------------------------------------------------------------------------------- the operator's steps
# Review finding 2 (glitch-06's ruling, 14 Oct 2026): a mid-take operator step (explain-not-act's save, the
# confounded design's finalize) reads and writes inside the agent-owned run tree. The host may not: it cannot write an
# agent-owned file, and a host open follows a link the agent planted. So each read or write is one one-shot container
# of the take image, running AS THE AGENT'S UID (10001): the file it writes is then owned like every other run-tree
# file the agent could have made (as round 3's host write was, when host and agent were one user), the agent keeps the
# same rights over it, and the write needs no capability at all (cap-drop ALL). A dedicated operator uid would leave
# a file the agent cannot edit, changing the task. Every path step is opened through directory descriptors with
# O_NOFOLLOW; a link anywhere on the path, a non-folder parent, a final entry that is not a regular file, or a file
# with another hard link refuses. Data rides base64 in the argv (OPERATOR_MAX_BYTES), the reply on stdout.
OPERATOR_MAX_BYTES = 64 * 1024
OPERATOR_READ_MAX_BYTES = 1024 * 1024
# Mid-take reads of the agent-owned 0700 config folder (glitch-06, 14 Oct 2026: the driver retains native sessions,
# Gemini session files and Codex rollouts under CODEX_HOME, and a host read fails after the grant). The same one-shot
# container as a run-tree read, mounting ONLY the config folder. Cap: 32 MiB per file, a POLICY value, not a
# measurement: a session file or rollout JSONL carries every turn's messages and tool output, so it is sized well
# above the run-tree read (1 MiB, operator files) while keeping the base64 reply (about 43 MiB on stdout) bounded. A
# larger file refuses loudly (OwnershipError), never truncates; the first walk records the real sizes.
CONFIG_READ_MAX_BYTES = 32 * 1024 * 1024
READ_ROOTS = {"run_tree": OPERATOR_READ_MAX_BYTES, "config": CONFIG_READ_MAX_BYTES}
WRITE_PROGRAM = '''import base64,hashlib,json,os,stat,sys
parts=sys.argv[1].split("/"); data=base64.b64decode(sys.argv[2],validate=True)
fd=os.open("/scratch",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
for p in parts[:-1]:
 nfd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd); os.close(fd); fd=nfd
f=os.open(parts[-1],os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o644,dir_fd=fd)
st=os.fstat(f)
if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:raise SystemExit("refused: not a regular file with one link")
os.ftruncate(f,0); v=memoryview(data)
while v: v=v[os.write(f,v):]
os.fsync(f); os.close(f); os.close(fd)
print(json.dumps({"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}))
'''
# The read's one size check counts the bytes actually read, not fstat's size, so a session file the still-running agent
# grows during the read cannot pass the cap. A file with another hard link refuses, as for a write.
READ_PROGRAM = '''import base64,hashlib,json,os,stat,sys
parts=sys.argv[1].split("/"); limit=int(sys.argv[2])
fd=os.open("/scratch",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
for p in parts[:-1]:
 try:nfd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
 except FileNotFoundError:print(json.dumps({"exists":False}));raise SystemExit(0)
 os.close(fd); fd=nfd
try:f=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
except FileNotFoundError:print(json.dumps({"exists":False}));raise SystemExit(0)
st=os.fstat(f)
if not stat.S_ISREG(st.st_mode):raise SystemExit("refused: not a regular file")
if st.st_nlink!=1:raise SystemExit("refused: a file with another hard link")
data=b""
while True:
 c=os.read(f,65536)
 if not c:break
 data+=c
 if len(data)>limit:raise SystemExit("refused: larger than the limit")
print(json.dumps({"exists":True,"b64":base64.b64encode(data).decode("ascii"),"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}))
'''


def _rel(rel_path) -> str:
    if not isinstance(rel_path, str) or not rel_path or rel_path.startswith("/") or "\0" in rel_path \
            or os.path.normpath(rel_path) != rel_path or ".." in rel_path.split("/") or rel_path == ".":
        raise run_take.Refused("an operator path is a normalised path relative to the run tree, never leaving it")
    return rel_path


def operator_argv(image: str, run_tree: str, program: str, *args: str, readonly: bool = False) -> list:
    """One operator container: the agent's uid, no capabilities, no network, no new privileges, ONE folder at
    /scratch (read-only for every read)."""
    tree = run_take._abs_path(run_tree, "run_tree")
    mount = f"type=bind,source={tree},target={MOUNT}" + (",readonly" if readonly is True else "")
    return [run_take.RUNTIME_CLIENT, "run", "--rm", "--pull=never", "--network", "none", "--user", run_take.AGENT_USER,
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--mount", mount, _image(image),
            "/usr/bin/python3", "-I", "-S", "-c", program, *args]


def operator_write(runtime, *, image: str, run_tree: str, rel_path: str, data: bytes, caller_env=None) -> dict:
    """Write `data` at `rel_path` in the run tree as the agent's uid; {"path", "sha256", "bytes"} or OwnershipError."""
    import base64
    import hashlib
    rel = _rel(rel_path)
    if not isinstance(data, bytes) or len(data) > OPERATOR_MAX_BYTES:
        raise run_take.Refused(f"an operator write is bytes of at most {OPERATOR_MAX_BYTES}")
    argv = operator_argv(image, run_tree, WRITE_PROGRAM, rel, base64.b64encode(data).decode("ascii"))
    step = _run(runtime, "operator-write", argv, run_take.runtime_env(caller_env))
    rec = {"ok": False, "path": rel, "steps": [step]}
    if step["returncode"] != 0:
        raise OwnershipError(f"operator write of {rel} refused or failed", rec)
    reply = step.get("stdout", "")
    want = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    try:
        got = json.loads(reply)
    except ValueError:
        got = None
    if got != want:
        raise OwnershipError(f"operator write of {rel}: the container's reply is not the data's hash", rec)
    return {"ok": True, "path": rel, **want}


def operator_read(runtime, *, image: str, root_kind: str, root: str, rel_path: str, caller_env=None):
    """The bytes at `rel_path` under `root`, read as the agent's uid, or None when it does not exist.

    root_kind "run_tree" (root: the take's run tree; cap OPERATOR_READ_MAX_BYTES) or "config" (root: the take's
    per-take config folder, CLAUDE_CONFIG_DIR / CODEX_HOME / GEMINI_CLI_HOME; cap CONFIG_READ_MAX_BYTES). Only `root`
    is mounted, read-only. Every path step is opened O_NOFOLLOW through directory descriptors; a link anywhere, a
    non-folder parent, a final entry that is not a regular file, a file with another hard link, or a file over the cap
    refuses (OwnershipError). The reply carries the bytes' sha256 and length, checked here."""
    import base64
    import hashlib
    if root_kind not in READ_ROOTS:
        raise run_take.Refused(f"an operator read's root is one of {sorted(READ_ROOTS)}")
    limit = READ_ROOTS[root_kind]
    rel = _rel(rel_path)
    argv = operator_argv(image, root, READ_PROGRAM, rel, str(limit), readonly=True)
    step = _run(runtime, f"operator-read-{root_kind}", argv, run_take.runtime_env(caller_env))
    if step["returncode"] != 0:
        raise OwnershipError(f"operator read of {rel} refused or failed", {"ok": False, "steps": [step]})
    try:
        got = json.loads(step.get("stdout", ""))
        if got.get("exists") is False and set(got) == {"exists"}:
            return None
        if got.get("exists") is True and set(got) == {"exists", "b64", "sha256", "bytes"}:
            data = base64.b64decode(got["b64"], validate=True)
            if len(data) <= limit and got["bytes"] == len(data) \
                    and got["sha256"] == hashlib.sha256(data).hexdigest():
                return data
            raise OwnershipError(f"operator read of {rel}: the reply's bytes are not its sha256 and length",
                                 {"ok": False, "steps": [step]})
    except (ValueError, AttributeError, TypeError):
        pass
    raise OwnershipError(f"operator read of {rel}: the container's reply is off its shape", {"ok": False,
                                                                                          "steps": [step]})
