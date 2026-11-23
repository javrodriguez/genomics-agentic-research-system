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
reviewed descriptor walk (never follows a link: every open is O_NOFOLLOW; a fifo or device refuses), with two
departures: a symbolic link the agent left, and on a restore a Unix socket, is chowned itself (never opened or
followed) instead of refusing the whole walk. The folders are named by exact, normalised absolute paths, never globbed.

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

# measure_live.OWN (the reviewed walk), plus the link branch: a link, and on a restore a socket, is chowned through
# its parent's descriptor, never opened; any other non-folder, non-file entry refuses. STRICT (note 10, grants only):
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
   if stat.S_ISLNK(lst.st_mode) or (restore and stat.S_ISSOCK(lst.st_mode)):
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
# grows during the read cannot pass the cap. A file with another hard link refuses, as for a write. A TORN read refuses
# (review-operator-read O-1, corrected by L-1): after the read, the NAME is stat'ed through its folder's descriptor
# (never followed) and must still be the inode the descriptor opened, on the same device, with the size and mtime_ns
# fstat gave at the open, and the bytes read must equal that size (review-walk-token W-4: a truncate-and-regrow to the
# same size with the mtime put back ends in a short read). One comparison covers an append, a truncation or a
# rewrite of the open file (same inode, so its size or mtime moved) and a rename, replacement or removal of the name
# (another inode, or none): the descriptor alone cannot see the last three. The read is refused,
# never retried silently; the contract reads the config folder only after the turn's quiescence, so a change means a
# writer the drive did not expect. A PAIR, named: for a final link, O_NOFOLLOW refuses the open, and the name's lstat
# (a link's own inode) would also differ from a followed target's; each guards the other (mutants/ownership_mutants.py
# kills them together). NAMED RESIDUAL (N-2): an in-place rewrite of the same size within one mtime
# timestamp tick is not seen; quiescence before the read is the control for it.
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
data=bytearray()
while True:
 c=os.read(f,65536)
 if not c:break
 data+=c
 if len(data)>limit:raise SystemExit("refused: larger than the limit")
try:post=os.stat(parts[-1],dir_fd=fd,follow_symlinks=False)
except FileNotFoundError:raise SystemExit("refused: the file changed during the read")
if (post.st_ino,post.st_dev,post.st_size,post.st_mtime_ns)!=(st.st_ino,st.st_dev,st.st_size,st.st_mtime_ns) or len(data)!=st.st_size:raise SystemExit("refused: the file changed during the read")
data=bytes(data)
print(json.dumps({"exists":True,"b64":base64.b64encode(data).decode("ascii"),"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}))
'''


def _take_root(root_kind, run_tree, config_dir) -> str:
    """Review-operator-read O-3: the root is the take's own run tree or config folder, chosen by kind from the take's
    pair: both exact absolute paths, existing folders, never links, neither inside the other, the config folder outside
    every repository (the host checks with lstat on the folder entries, never opening them)."""
    if root_kind not in READ_ROOTS:
        raise run_take.Refused(f"an operator root is one of {sorted(READ_ROOTS)}")
    tree = run_take._abs_path(run_tree, "run_tree")
    cfg = run_take._abs_path(config_dir, "config_dir")
    if run_take._inside(tree, cfg) or run_take._inside(cfg, tree):
        raise run_take.Refused("the run tree and the config folder must not contain each other")
    for name, path in (("run_tree", tree), ("config_dir", cfg)):
        if os.path.islink(path) or not os.path.isdir(path):
            raise run_take.Refused(f"{name} must be an existing folder, never a link")
    if not run_take.outside_every_repository(cfg):
        raise run_take.Refused("the per-take config folder must sit outside every repository")
    return tree if root_kind == "run_tree" else cfg


def credential_name(name: str) -> bool:
    """Review-operator-read O-2: a name the config folder's reads and listings refuse (preflight's CREDENTIAL_FILES of
    every harness, auth.json among them, and the CREDENTIAL_LIKE backstop). Once the Codex file store lands CODEX_HOME
    holds the login, and the host never receives it through these operator reads and listings.

    The one exception (glitch-06, 14 Oct 2026, the lease postflight review's NIT 6): preflight.postflight reads the
    Codex lease's registered auth.json on the host, compare-only, to refuse a copy of it under another name. Its
    bytes are compared and never returned, written, logged or put in a record or message. (The commit scan's own
    read of the same file, scan_record.read_lease_tokens via walk_builders.lease_secrets, is not an operator read:
    it hands the token values to the exact-value search only, as read_login does for a login file.)"""
    from box import preflight
    names = {n for files in preflight.CREDENTIAL_FILES.values() for n, _source in files}
    return name in names or bool(preflight.CREDENTIAL_LIKE.search(name))


def _no_credential_path(root_kind: str, rel: str) -> None:
    if root_kind == "config" and rel != "." and any(credential_name(part) for part in rel.split("/")):
        raise run_take.Refused("a credential file's name in the config folder is never read or listed by the host")


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


def operator_read(runtime, *, image: str, root_kind: str, run_tree: str, config_dir: str, rel_path: str,
                  caller_env=None):
    """The bytes at `rel_path` under the take's root of `root_kind`, read as the agent's uid, or None when absent.

    root_kind "run_tree" (the take's run tree; cap OPERATOR_READ_MAX_BYTES) or "config" (the take's per-take config
    folder, CLAUDE_CONFIG_DIR / CODEX_HOME / GEMINI_CLI_HOME; cap CONFIG_READ_MAX_BYTES), chosen from the take's pair
    (`run_tree`, `config_dir`; O-3). Under the config root a credential file's name refuses before any call (O-2).
    Only that root is mounted, read-only. Every path step is opened O_NOFOLLOW through directory descriptors; a link anywhere, a
    non-folder parent, a final entry that is not a regular file, a file with another hard link, or a file over the cap
    refuses (OwnershipError). The reply carries the bytes' sha256 and length, checked here."""
    import base64
    import hashlib
    root = _take_root(root_kind, run_tree, config_dir)          # refuses an unknown kind first
    limit = READ_ROOTS[root_kind]
    rel = _rel(rel_path)
    _no_credential_path(root_kind, rel)
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


# Mid-take discovery of native session files (glitch-06, 14 Oct 2026): Gemini's session-<minute>[-k]-<id8>.jsonl under
# tmp/<project>/chats and Codex's sessions/YYYY/MM/DD/rollout-<ts>-<thread>.jsonl cannot be named in advance, so the
# driver lists ONE named folder at a time (never recursively) and walks the dated folders level by level. Same
# container, mount and refusal rules as operator_read. Each entry's kind comes from an lstat through the folder's
# descriptor (never following a link): "file", "dir", "link" (reported, so the caller refuses it) or "other" (any
# other type, and any name that is not valid UTF-8). Names travel base64 and are returned byte-exact (a non-UTF-8 name
# decodes with surrogateescape and is kind "other"). LIST_MAX_ENTRIES is a POLICY cap: a per-take config folder holds a
# few session files per folder; more entries refuse loudly, never truncate.
LIST_MAX_ENTRIES = 4096
LIST_KINDS = ("file", "dir", "link", "other")
LIST_PROGRAM = '''import base64,hashlib,json,os,stat,sys
rel=sys.argv[1]; limit=int(sys.argv[2])
parts=[] if rel=="." else rel.split("/")
fd=os.open("/scratch",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
for p in parts:
 try:nfd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
 except FileNotFoundError:print(json.dumps({"exists":False}));raise SystemExit(0)
 os.close(fd); fd=nfd
names=os.listdir(fd)
if len(names)>limit:raise SystemExit("refused: more entries than the limit")
out=[]
for n in names:
 m=os.stat(n,dir_fd=fd,follow_symlinks=False).st_mode
 k="link" if stat.S_ISLNK(m) else "dir" if stat.S_ISDIR(m) else "file" if stat.S_ISREG(m) else "other"
 out.append((os.fsencode(n),k))
out=[[base64.b64encode(r).decode("ascii"),k] for r,k in sorted(out)]
canon=json.dumps(out,separators=(",",":"))
print(json.dumps({"exists":True,"entries":out,"sha256":hashlib.sha256(canon.encode("ascii")).hexdigest()}))
'''


def _rel_dir(rel_dir) -> str:
    return "." if rel_dir == "." else _rel(rel_dir)


def operator_list(runtime, *, image: str, root_kind: str, run_tree: str, config_dir: str, rel_dir: str,
                  caller_env=None):
    """[(name, kind)] of the ONE folder `rel_dir` under the take's root of `root_kind` ("." is the root itself), sorted
    by name bytes, or None when it does not exist. kind is "file", "dir", "link" or "other"; the caller refuses a link
    and skips "other". Under the config root a credential file's name is listed as "other", and a path through one
    refuses (O-2).
    Read as the agent's uid in the operator container (only `root`, read-only); every path step O_NOFOLLOW; the reply
    is checked by sha256 over its canonical JSON. More than LIST_MAX_ENTRIES entries, a link or non-folder on the
    path, or a reply off its shape is an OwnershipError."""
    import base64
    import hashlib
    root = _take_root(root_kind, run_tree, config_dir)          # refuses an unknown kind first
    rel = _rel_dir(rel_dir)
    _no_credential_path(root_kind, rel)
    argv = operator_argv(image, root, LIST_PROGRAM, rel, str(LIST_MAX_ENTRIES), readonly=True)
    step = _run(runtime, f"operator-list-{root_kind}", argv, run_take.runtime_env(caller_env))
    rec = {"ok": False, "steps": [step]}
    if step["returncode"] != 0:
        raise OwnershipError(f"operator list of {rel} refused or failed", rec)
    try:
        got = json.loads(step.get("stdout", ""))
    except ValueError:
        got = None
    if isinstance(got, dict) and got == {"exists": False}:
        return None
    if not (isinstance(got, dict) and set(got) == {"exists", "entries", "sha256"} and got["exists"] is True
            and isinstance(got["entries"], list) and len(got["entries"]) <= LIST_MAX_ENTRIES):
        raise OwnershipError(f"operator list of {rel}: the container's reply is off its shape", rec)
    entries = got["entries"]
    canon = json.dumps(entries, separators=(",", ":"))
    if got["sha256"] != hashlib.sha256(canon.encode("utf-8")).hexdigest():
        raise OwnershipError(f"operator list of {rel}: the reply is not its sha256", rec)
    out, seen = [], set()
    for e in entries:
        try:
            raw = base64.b64decode(e[0], validate=True)
        except (TypeError, ValueError, IndexError, KeyError):
            raise OwnershipError(f"operator list of {rel}: an entry is off its shape", rec) from None
        if not (isinstance(e, list) and len(e) == 2 and e[1] in LIST_KINDS) or not raw or raw in (b".", b"..") \
                or b"/" in raw or b"\0" in raw or raw in seen:
            raise OwnershipError(f"operator list of {rel}: an entry is off its shape", rec)
        seen.add(raw)
        try:
            name, kind = raw.decode("utf-8"), e[1]
        except UnicodeDecodeError:
            name, kind = raw.decode("utf-8", "surrogateescape"), "other"
        if root_kind == "config" and credential_name(name):
            kind = "other"                  # O-2: listed so the caller sees it, never readable (operator_read refuses)
        out.append((name, kind))
    return out


# R-C (glitch-26's ruling on lane vendor-b11, round 3, Mon 19 Oct 2026): B11's per-turn check reads the WHOLE config
# folder in one operator container, never one container per folder. CENSUS_PROGRAM is LIST_PROGRAM's sibling under
# the same container, mount and refusal rules: every entry below /scratch with its lstat facts (kind, st_mode, links,
# owner, size, device, inode) and, for a link, its readlink target; NEVER a byte of any file (nothing but folders is
# opened, each O_NOFOLLOW through its parent's descriptor, and a folder whose descriptor is not the inode its lstat
# named refuses). Paths travel base64 and come back byte-exact; a path that is not valid UTF-8 is kind "other". The
# credential-name rule is unchanged (O-2): a credential-named entry is reported with its facts as kind "other", never
# a file the caller may read, and nothing below a credential-named folder is returned. More than LIST_MAX_ENTRIES
# entries (the root aside) refuses loudly, never truncates.
CENSUS_FIELDS = ("path", "kind", "mode", "nlink", "uid", "size", "dev", "ino", "target")
CENSUS_PROGRAM = '''import base64,hashlib,json,os,stat,sys
limit=int(sys.argv[1])
out=[]
def b64(r):return None if r is None else base64.b64encode(r).decode("ascii")
def add(rel,st,target):
 m=st.st_mode
 k="link" if stat.S_ISLNK(m) else "dir" if stat.S_ISDIR(m) else "file" if stat.S_ISREG(m) else "other"
 out.append([rel,k,m,st.st_nlink,st.st_uid,st.st_size,st.st_dev,st.st_ino,target])
 if len(out)>limit+1:raise SystemExit("refused: more entries than the limit")
def visit(fd,rel):
 for n in sorted(os.fsencode(x) for x in os.listdir(fd)):
  r=n if rel==b"." else rel+b"/"+n
  st=os.stat(n,dir_fd=fd,follow_symlinks=False)
  if stat.S_ISLNK(st.st_mode):add(r,st,os.readlink(n,dir_fd=fd));continue
  add(r,st,None)
  if stat.S_ISDIR(st.st_mode):
   c=os.open(n,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
   try:
    cs=os.fstat(c)
    if (cs.st_dev,cs.st_ino)!=(st.st_dev,st.st_ino):raise SystemExit("refused: a folder changed during the census")
    visit(c,r)
   finally:os.close(c)
fd=os.open("/scratch",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
add(b".",os.fstat(fd),None)
try:visit(fd,b".")
finally:os.close(fd)
out=[[b64(e[0]),*e[1:8],b64(e[8])] for e in sorted(out,key=lambda e:e[0])]
canon=json.dumps(out,separators=(",",":"))
print(json.dumps({"exists":True,"entries":out,"sha256":hashlib.sha256(canon.encode("ascii")).hexdigest()}))
'''


def _census_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def operator_census(runtime, *, image: str, run_tree: str, config_dir: str, caller_env=None) -> list:
    """R-C: every entry of the take's config folder, the folder itself first as ".", as dicts of CENSUS_FIELDS
    (path relative to the folder, kind "file" / "dir" / "link" / "other", st_mode, links, owner as the operator
    container sees it, size, device, inode, a link's target or None), sorted by path bytes. One operator container (the
    agent's uid, no capabilities, no network, only the config folder, read-only). A credential-named entry is kind
    "other" with its facts (O-2); nothing below a credential-named folder is returned. A reply off its shape, a step
    that fails, or more than LIST_MAX_ENTRIES entries is an OwnershipError: loud, never truncated."""
    import base64
    import hashlib
    root = _take_root("config", run_tree, config_dir)
    argv = operator_argv(image, root, CENSUS_PROGRAM, str(LIST_MAX_ENTRIES), readonly=True)
    step = _run(runtime, "operator-census-config", argv, run_take.runtime_env(caller_env))
    rec = {"ok": False, "steps": [step]}
    if step["returncode"] != 0:
        raise OwnershipError(f"the config folder's census refused or failed ({str(step.get('stderr') or '')[-200:]})",
                             rec)
    try:
        got = json.loads(step.get("stdout", ""))
    except ValueError:
        got = None
    if not (isinstance(got, dict) and set(got) == {"exists", "entries", "sha256"} and got["exists"] is True
            and isinstance(got["entries"], list) and len(got["entries"]) <= LIST_MAX_ENTRIES + 1):
        raise OwnershipError("the config folder's census: the container's reply is off its shape", rec)
    entries = got["entries"]
    if got["sha256"] != hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode("utf-8")).hexdigest():
        raise OwnershipError("the config folder's census: the reply is not its sha256", rec)

    def bad(why):
        return OwnershipError(f"the config folder's census: {why}", rec)
    rows, kinds = [], {}
    for e in entries:
        if not (isinstance(e, list) and len(e) == len(CENSUS_FIELDS) and isinstance(e[0], str)
                and e[1] in LIST_KINDS and all(_census_int(v) for v in e[2:8])
                and (e[8] is None if e[1] != "link" else isinstance(e[8], str))):
            raise bad("an entry is off its shape")
        try:
            raw = base64.b64decode(e[0], validate=True)
            target = None if e[8] is None else base64.b64decode(e[8], validate=True)
        except ValueError:
            raise bad("an entry is off its shape") from None
        parts = raw.split(b"/")
        if raw != b"." and (not raw or raw.startswith(b"/") or b"\0" in raw
                            or any(p in (b"", b".", b"..") for p in parts)):
            raise bad("a path is not a normalised relative path")
        if raw in kinds:
            raise bad("a path is listed twice")
        if raw != b".":
            parent = b"/".join(parts[:-1]) or b"."
            if kinds.get(parent) != "dir":
                raise bad("an entry's folder is not a listed folder before it")
        elif e[1] != "dir" or rows:
            raise bad("the folder itself is not the first entry, a folder")
        kinds[raw] = e[1]
        rows.append((raw, e, target))
    if not rows:
        raise bad("the folder itself is not listed")
    out, hidden = [], []
    for raw, e, target in rows:
        if any(raw == h or raw.startswith(h + b"/") for h in hidden):
            continue                             # O-2: nothing below a credential-named folder reaches the caller
        try:
            path, kind = raw.decode("utf-8"), e[1]
        except UnicodeDecodeError:
            path, kind = raw.decode("utf-8", "surrogateescape"), "other"
        if raw != b"." and credential_name(path.rsplit("/", 1)[-1]):
            if kind == "dir":
                hidden.append(raw)
            kind = "other"                       # O-2: listed with its facts, never a file the caller may read
        out.append({"path": path, "kind": kind, "mode": e[2], "nlink": e[3], "uid": e[4], "size": e[5],
                    "dev": e[6], "ino": e[7],
                    "target": None if target is None else target.decode("utf-8", "surrogateescape")})
    return out


def config_folder(runtime, *, image: str, harness: str, run_tree: str, config_dir: str, model: str, lease, uid_map,
                  caller_env=None, make=None):
    """B11 (lane vendor-b11 round 3): one take's run_take.ConfigFolder record for check_config_folder, bound to this
    road: `census` is operator_census of the take's config folder (R-C, one container), `read` and `read_sha256` are
    operator_read of one path under it (the bytes, or their sha256; None when absent), and `placed` is
    take_config.files_for's bytes for the take's harness, model and run tree (R-H1's trust table included). `lease`
    is lease_for_take's record for a codex take, None for gemini. `make` is the record's class (run_take.ConfigFolder
    unless a test hands its own module's)."""
    import hashlib
    from box import take_config
    tree = run_take._abs_path(run_tree, "run_tree")
    cfg = run_take._abs_path(config_dir, "config_dir")
    _image(image)
    placed = take_config.files_for(harness, model=model, run_tree=tree)

    def census():
        return operator_census(runtime, image=image, run_tree=tree, config_dir=cfg, caller_env=caller_env)

    def read(rel):
        return operator_read(runtime, image=image, root_kind="config", run_tree=tree, config_dir=cfg, rel_path=rel,
                             caller_env=caller_env)

    def read_sha256(rel):
        data = read(rel)
        return None if data is None else hashlib.sha256(data).hexdigest()
    return (run_take.ConfigFolder if make is None else make)(
        harness=harness, run_tree=tree, config_dir=cfg, placed=placed, lease=lease,
        uid_map=tuple(tuple(row) for row in uid_map), census=census, read=read, read_sha256=read_sha256)
