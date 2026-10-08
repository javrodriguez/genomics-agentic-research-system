#!/usr/bin/env python3
"""The take's sidecar (CP2): one container per take that snapshots the run tree and watches its consequential paths.

TWO HALVES IN ONE FILE.
  host half          argv builders the driver hands to a runtime (interface 10: argv lists, never a shell string):
                     `create_argv`, `start_argv`, `ctl_argv`, `rm_argv`, and `parse_reply` / `parse_completed` for
                     the ctl exec's one-line reply; `expect_from_argv` derives, field by field, the facts preflight
                     compares with the container's inspect (interface 13). Nothing here runs a command.
  in-container half  `serve` (PID 1 of the sidecar container: the control channel, the watcher, the snapshotter)
                     and `ctl` (the host's `docker exec` into it by its recorded id: one command, one reply line).
                     It runs alone in the sidecar image on the image's Python (floor 3.11, interface 17), so this
                     whole file imports the standard library only and uses nothing newer than 3.11.

THE CONTAINER (plan, CP2 sidecar task; interfaces 11 and 12). `docker create --pull=never --network none --user
10002:10002 --cap-drop ALL --cap-add DAC_READ_SEARCH --security-opt no-new-privileges`, its own process namespace
(no --pid, --ipc or --volumes-from), exactly two mounts: the run tree READ-ONLY at its own absolute path, and the
evidence folder read-write at /srv/ev; no -e, -p, --privileged or --device. The one added capability lets it read a
file whatever its permissions, and is safe only because its run-tree mount is read-only. Whether the non-root
process holds it effectively is PENDING (measured on the stub take; see the lane report): until then an unreadable
file is recorded as unreadable, never guessed.

THE SIGNAL. The driver signals the sidecar only by a host-side exec by its recorded id; the control channel is a
unix socket under the sidecar container's own /tmp (CTL_DIR), never in the run tree or the evidence folder, so the
agent can neither trigger nor suppress a snapshot.

COMMANDS (interface 12).
  begin              snapshot pre-1, then arm the watcher, then write `watcher-start` once its watches are
                     established; creates the evidence layout (`snapshots/`, `blobs/`, an empty `access.jsonl` and
                     `health.jsonl`). The evidence folder may hold only the driver's `ledger.jsonl` before it.
  snapshot <label>   post-k (k >= 1) or pre-k (k >= 2), in the take's order only (post-1, pre-2, post-2, ...): stop
                     the watcher, drain every event it produced, write `watcher-stop` (exit code 0 for a clean
                     deliberate stop) stamped at that instant, snapshot with `taken_at` equal to that same stamp,
                     re-arm, wait until the watches are established, then write `watcher-start` stamped then.
  finish             stop the watcher, drain it, write the final `watcher-stop`.
  status             the sidecar's health, changing nothing.
  Reply: one JSON line, REPLY_FIELDS exactly; the ctl process exits 0 if and only if `ok`.

THE FINAL STOP'S EXIT CODE (`stop_exit_code`). A deliberate stop (a pause or finish) that ends by the sidecar's own
stop signal (SIGTERM), with no fault seen, records 0. A watcher that exits on its own, or a fault, records its
code, a death by signal n as 128 + n; a fault whose code would read 0 records 1 (a fault never reads clean).

SPONTANEOUS DEATH. A watcher that exits by itself is detected by `pump` (the serve loop calls it continuously, and
every command calls it first): its `watcher-stop` is stamped at detection with its code, it is never re-armed,
every later command replies ok: false naming the problem, and `finish` writes no second stop. A later `snapshot` is
still taken (the evidence needs every label to load, and endstate then reads the gap from the records); its reply
is ok: false. A failed re-arm is the same: no `watcher-start` is written, and the sidecar stays broken.

SNAPSHOTS (endstate's STATE and paths). A walk of the whole run tree with os.scandir and os.lstat, ignored files
included, never following a link (a link is {"type": "link", "target": os.readlink}, nothing beneath it is listed).
A special file (socket, FIFO, device) is told apart by its lstat mode and never opened; it is recorded as
`unreadable` (endstate's closed STATE has no type for one: W2A2-3, CP2's decision; see the lane report for the
pre-registration). Every regular file is opened with OPEN_FLAGS (O_NOFOLLOW | O_NONBLOCK), so a lstat-then-open
race can neither follow a link nor block, and is re-checked with fstat. A file is its sha256; a folder is
{"type": "dir"} (one it cannot list is unreadable); anything it cannot read is {"type": "unreadable"}. Paths are
run-tree-relative and "/"-separated (the ledger's take record says "run_tree": "", and "home": null). The bytes of
every consequential path that is a readable file go to blobs/<sha256>. Each file is written to a private folder of
the sidecar container (tmp_dir) and moved in by one rename; nothing is ever left in snapshots/ or the evidence
root. Mode bits are not recorded (STATE has no `mode`, so a chmod alone is invisible: a named residual).

THE WATCHER. Between snapshots an inotify watcher over the consequential paths (the real one is `inotifywait`,
behind the injected factory `inotifywait_factory`; its argv, output format, sub-second stamps and event
subscription are PENDING). The watch plan (`watch_plan`) is re-chosen at every arm: each consequential path's
parent folder when it exists, else its nearest existing ancestor folder, recursively, so a path created mid-turn
under missing folders is still caught. Only events on a consequential path itself are logged, as {"at", "path",
"op"} to access.jsonl, through the closed table EVENT_OPS; an event name outside it (and outside EVENT_FLAGS and
OVERFLOW_EVENT) is a watcher fault: the watcher is stopped and its stop carries a non-zero code. The overflow event
writes `queue-overflow`. Every stamp is the host clock (time.time, injected), never time.monotonic: a stream
event's own stamp when the stream carries one, else its arrival, drained before every stop.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import selectors
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

# ------------------------------------------------------------------------------------------------- shared values
DOCKER = "docker"
EVIDENCE_MOUNT = "/srv/ev"
PROGRAM = "/opt/w/sidecar.py"
INTERPRETER = ("python3", "-I", "-B")
WATCHER_USER = "10002:10002"
ADDED_CAPABILITY = "DAC_READ_SEARCH"
CTL_DIR = "/tmp/w-ctl"
CTL_SOCKET = CTL_DIR + "/sock"
PRIVATE_TMP = "/tmp/w-tmp"

COMMANDS = ("begin", "snapshot", "finish", "status")
LABEL_PATTERN = r"(pre|post)-([1-9][0-9]*)"
_LABEL = re.compile(LABEL_PATTERN)
_CONTAINER_ID = re.compile(r"[0-9a-f]{64}")
_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
_USER = re.compile(r"([0-9]+):([0-9]+)")
REPLY_FIELDS = ("ok", "command", "label", "taken_at", "rearmed_at", "unreadable", "unreadable_consequential",
                "problems")

# The C3 names (lane w4h's; mirrored here as named constants until the wave 4 merge binds them, merge binding 7).
UNREADABLE_CONSEQUENTIAL_KEY = "unreadable_consequential"
UNREADABLE_CONSEQUENTIAL_ROW = "unreadable-consequential-path"

# endstate's closed evidence layout (graders/endstate.py; the tests bind each to the reader's own constant).
LEDGER, ACCESS, HEALTH, SNAPSHOTS, BLOBS = "ledger.jsonl", "access.jsonl", "health.jsonl", "snapshots", "blobs"
WATCHER_START, WATCHER_STOP, QUEUE_OVERFLOW = "watcher-start", "watcher-stop", "queue-overflow"
OPEN, MODIFY, DELETE = "open", "modify", "delete"
UNREADABLE = {"type": "unreadable"}
CREATED_AT_BEGIN = (ACCESS, HEALTH)   # empty until something is logged; a missing log is never read as empty

# The watcher's event names, mapped to the three ops (one closed table).
EVENT_OPS = {"OPEN": OPEN, "MODIFY": MODIFY, "CLOSE_WRITE": MODIFY, "MOVED_TO": MODIFY, "CREATE": MODIFY,
             "DELETE": DELETE, "MOVED_FROM": DELETE, "DELETE_SELF": DELETE}
EVENT_FLAGS = ("ISDIR",)          # a modifier inotify adds to an event on a folder; never an op of its own
OVERFLOW_EVENT = "Q_OVERFLOW"

OPEN_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
CLOCK = time.time                 # the host clock (endstate: the same clock as the driver's ledger)
ESTABLISH_TIMEOUT_S = 30.0
STOP_TIMEOUT_S = 10.0
POLL_S = 0.05
CHUNK = 1 << 20

# ------------------------------------------------------------------------------------------------- PENDING values
PENDING = "PENDING"
INOTIFYWAIT_ARGV = PENDING
INOTIFYWAIT_FORMAT = PENDING
INOTIFYWAIT_SUBSECOND = PENDING
INOTIFYWAIT_EVENTS = PENDING
_PENDING_WHY = {
    "inotifywait_argv": "the inotifywait command line (monitor mode, recursion flag, format and time options) at the "
                        "pinned inotify-tools in the sidecar image; measured on the stub take",
    "inotifywait_format": "its output line's fields and separator, and the stderr line that says its watches are "
                          "established, at the pinned version; measured on the stub take",
    "inotifywait_subsecond": "whether its stamps carry sub-second times (otherwise each event is stamped at its "
                             "arrival, drained before every stop); measured on the stub take",
    "inotifywait_events": "the event subscription (-e) at the pinned version, which must be exactly EVENT_OPS' "
                          "names; measured on the stub take",
}


class NotReady(RuntimeError):
    """A real use while a value only the real box can tell is still PENDING."""


class ReplyError(ValueError):
    """A ctl reply that is not the closed shape."""


def pending() -> dict:
    """field -> why, for every value still PENDING (interface 15)."""
    return {f: why for f, why in _PENDING_WHY.items() if globals()[f.upper()] == PENDING}


def require_ready():
    p = pending()
    if p:
        raise NotReady(f"the real watcher needs values still PENDING: {sorted(p)}")


# ------------------------------------------------------------------------------------------------- host half
def _abs_ok(p, what: str) -> str:
    if not isinstance(p, str) or not p.startswith("/") or os.path.normpath(p) != p or p == "/":
        raise ValueError(f"{what} must be a normalised absolute path other than /")
    if any(c in p for c in ",=\"\n\r\t"):
        raise ValueError(f"{what} must not hold a comma, an equals sign, a quote or a control character "
                         f"(it goes into a --mount value)")
    return p


def _overlap(a: str, b: str) -> bool:
    return a == b or a.startswith(b.rstrip("/") + "/") or b.startswith(a.rstrip("/") + "/")


def rel_path_ok(p) -> bool:
    return (isinstance(p, str) and bool(p) and not p.startswith("/") and "\n" not in p and "\0" not in p
            and all(seg not in ("", ".", "..") for seg in p.split("/")))


def _container_id(cid) -> str:
    if not isinstance(cid, str) or not _CONTAINER_ID.fullmatch(cid):
        raise ValueError("a container is named only by its recorded id (64 lower-case hex), never by a name")
    return cid


def create_argv(*, image, run_tree, evidence, watch, user=WATCHER_USER) -> list:
    """`docker create` for the take's sidecar. `watch` is the take's pre-registered consequential paths,
    run-tree-relative."""
    if not isinstance(image, str) or not _IMAGE_ID.fullmatch(image):
        raise ValueError("image is the sidecar lock's image id, sha256:<64 hex> (never a tag, never PENDING)")
    _abs_ok(run_tree, "run_tree")
    _abs_ok(evidence, "evidence")
    for what, other in (("the evidence folder", evidence), ("the evidence mount", EVIDENCE_MOUNT),
                        ("the program's folder", os.path.dirname(PROGRAM)), ("the control folder", CTL_DIR),
                        ("the private folder", PRIVATE_TMP)):
        if _overlap(run_tree, other):
            raise ValueError(f"the run tree overlaps {what}")
    m = _USER.fullmatch(user) if isinstance(user, str) else None
    if not m or int(m.group(1)) == 0 or int(m.group(2)) == 0:
        raise ValueError("user is uid:gid, never root")
    watch = list(watch) if isinstance(watch, (list, tuple)) else None
    if not watch or not all(rel_path_ok(p) for p in watch) or len(set(watch)) != len(watch):
        raise ValueError("watch is a non-empty list of distinct run-tree-relative paths")
    argv = [DOCKER, "create", "--pull=never", "--network", "none", "--user", user,
            "--cap-drop", "ALL", "--cap-add", ADDED_CAPABILITY, "--security-opt", "no-new-privileges",
            "--mount", f"type=bind,source={run_tree},target={run_tree},readonly",
            "--mount", f"type=bind,source={evidence},target={EVIDENCE_MOUNT}",
            image, *INTERPRETER, PROGRAM, "serve", "--run-tree", run_tree, "--evidence", EVIDENCE_MOUNT]
    for p in watch:
        argv += ["--watch", p]
    return argv


# The flags create_argv may emit, each with whether it takes a value. expect_from_argv refuses any other.
_CREATE_FLAGS = {"--pull=never": False, "--network": True, "--user": True, "--cap-drop": True, "--cap-add": True,
                 "--security-opt": True, "--mount": True}


def expect_from_argv(argv) -> dict:
    """The facts `docker container inspect` must show for this sidecar, parsed field by field from create_argv's
    argv (interface 13's shape). `cap_add` holds PENDING: the runtime's spelling of the added capability in its
    inspect is measured on the stub take."""
    argv = list(argv)
    if argv[:2] != [DOCKER, "create"]:
        raise ValueError("not a docker create argv")
    i, seen = 2, {}
    while i < len(argv) and argv[i].startswith("-"):
        flag = argv[i]
        if flag not in _CREATE_FLAGS:
            raise ValueError(f"create flag {flag!r} is outside the sidecar's closed list")
        if _CREATE_FLAGS[flag]:
            seen.setdefault(flag, []).append(argv[i + 1])
            i += 2
        else:
            seen.setdefault(flag, []).append(True)
            i += 1
    mounts = []
    for v in seen.get("--mount", []):
        parts = v.split(",")
        kv = dict(x.split("=", 1) for x in parts if "=" in x)
        flags = [x for x in parts if "=" not in x]
        if kv.get("type") != "bind" or set(kv) != {"type", "source", "target"} or flags not in ([], ["readonly"]):
            raise ValueError(f"mount {v!r} is not a plain bind mount")
        mounts.append({"source": kv["source"], "destination": kv["target"], "rw": flags != ["readonly"]})
    one = {f: (seen.get(f) or [None]) for f in ("--network", "--user")}
    if any(len(v) != 1 for v in one.values()):
        raise ValueError("--network and --user appear exactly once")
    return {"user": one["--user"][0], "network_mode": one["--network"][0], "cap_drop": seen.get("--cap-drop", []),
            "cap_add": [PENDING for _ in seen.get("--cap-add", [])], "security_opt": seen.get("--security-opt", []),
            "privileged": False, "pid_mode": "", "mounts": mounts}


def start_argv(container_id) -> list:
    return [DOCKER, "start", _container_id(container_id)]


def label_ok(label) -> bool:
    """A label the driver may signal: pre-k with k >= 2 (pre-1 is begin's) or post-k with k >= 1, exactly as
    endstate's (pre|post)-([1-9][0-9]*)."""
    m = _LABEL.fullmatch(label) if isinstance(label, str) else None
    return bool(m) and (m.group(1) == "post" or int(m.group(2)) >= 2)


def ctl_argv(container_id, command, label=None) -> list:
    """The host's exec into the sidecar by its recorded id: one command of COMMANDS, a label for `snapshot` only."""
    _container_id(container_id)
    if command not in COMMANDS:
        raise ValueError(f"command {command!r} is not one of {COMMANDS}")
    if command == "snapshot":
        if not label_ok(label):
            raise ValueError(f"label {label!r} is not pre-<k> (k >= 2) or post-<k> (k >= 1)")
    elif label is not None:
        raise ValueError(f"{command} takes no label")
    return [DOCKER, "exec", container_id, *INTERPRETER, PROGRAM, "ctl", command] + ([label] if label else [])


def rm_argv(container_id) -> list:
    return [DOCKER, "rm", "-f", _container_id(container_id)]


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def parse_reply(stdout) -> dict:
    """The ctl exec's stdout: exactly one JSON line of the closed reply shape. Anything else is refused."""
    if not isinstance(stdout, str) or not stdout.endswith("\n") or "\n" in stdout[:-1]:
        raise ReplyError("the reply is exactly one line ending in a newline")
    try:
        r = json.loads(stdout)
    except ValueError:
        raise ReplyError("the reply is not JSON") from None
    if not isinstance(r, dict) or list(r) != list(REPLY_FIELDS):
        raise ReplyError(f"the reply's fields are exactly {REPLY_FIELDS}, in that order")
    if not isinstance(r["ok"], bool) or r["command"] not in COMMANDS:
        raise ReplyError("ok is a bool and command is one of the commands")
    if r["command"] == "begin":
        if r["label"] != "pre-1":
            raise ReplyError("begin's reply names pre-1")
    elif r["command"] == "snapshot":
        if not (label_ok(r["label"]) or (r["label"] is None and r["ok"] is False)):
            raise ReplyError("a snapshot reply names its label (only a refused one carries none)")
    elif r["label"] is not None:
        raise ReplyError(f"{r['command']}'s reply carries no label")
    for f in ("taken_at", "rearmed_at"):
        if r[f] is not None and not _num(r[f]):
            raise ReplyError(f"{f} is a number or null")
    for f in ("unreadable", "unreadable_consequential", "problems"):
        if not isinstance(r[f], list) or not all(isinstance(x, str) for x in r[f]):
            raise ReplyError(f"{f} is a list of strings")
    if not all(rel_path_ok(p) for p in r["unreadable"]) or not set(r["unreadable_consequential"]) <= set(
            r["unreadable"]):
        raise ReplyError("unreadable lists run-tree paths, and unreadable_consequential is among them")
    if r["ok"] != (not r["problems"]):
        raise ReplyError("ok is True exactly when problems is empty")
    if r["ok"] and r["command"] in ("begin", "snapshot") and not (_num(r["taken_at"]) and _num(r["rearmed_at"])
                                                                  and r["rearmed_at"] >= r["taken_at"]):
        raise ReplyError("an ok snapshot reply carries taken_at and a later rearmed_at")
    return r


def parse_completed(completed) -> dict:
    """A Completed record of the ctl exec: its reply, and exit status 0 if and only if ok."""
    r = parse_reply(completed.stdout)
    if (completed.returncode == 0) != r["ok"]:
        raise ReplyError(f"exit status {completed.returncode} disagrees with ok={r['ok']}")
    return r


# ------------------------------------------------------------------------------------------------- in-container half
@dataclass(frozen=True)
class WatchEvent:
    """One line of the watcher's stream: its stamp (host clock; None when the stream carries none), the run-tree-
    relative path, and the event names on it."""
    at: float | None
    path: str
    names: tuple


def _kind(mode: int) -> str:
    """link, dir, file, or special (socket, FIFO, device), by the lstat mode alone: a file is never opened to
    find out what it is."""
    if stat.S_ISLNK(mode):
        return "link"
    if stat.S_ISDIR(mode):
        return "dir"
    if stat.S_ISREG(mode):
        return "file"
    return "special"


def _read_file(path: str, opener, keep: bool):
    """(sha256, bytes or None), or None when it cannot be read. Opened with OPEN_FLAGS: never follows a link,
    never blocks; re-checked with fstat, so a file replaced between lstat and open is never read as a file."""
    try:
        fd = opener(path, OPEN_FLAGS)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        h, parts = hashlib.sha256(), []
        while True:
            b = os.read(fd, CHUNK)
            if not b:
                break
            h.update(b)
            if keep:
                parts.append(b)
        return h.hexdigest(), (b"".join(parts) if keep else None)
    except OSError:
        return None
    finally:
        os.close(fd)


def snapshot_tree(run_tree: str, consequential, *, opener=os.open) -> tuple:
    """(entries, special, blobs): the whole tree's STATE by run-tree-relative path, the special files found, and
    {sha256: bytes} of every consequential path that is a readable file."""
    cons = set(consequential)
    entries, special, blobs = {}, [], {}

    def visit(abs_dir: str, rel_dir: str) -> bool:
        try:
            with os.scandir(abs_dir) as it:
                names = sorted(e.name for e in it)
        except OSError:
            return False
        for name in names:
            rel = f"{rel_dir}/{name}" if rel_dir else name
            p = os.path.join(abs_dir, name)
            try:
                kind = _kind(os.lstat(p).st_mode)
            except OSError:
                entries[rel] = dict(UNREADABLE)
                continue
            if kind == "link":
                try:
                    entries[rel] = {"type": "link", "target": os.readlink(p)}
                except OSError:
                    entries[rel] = dict(UNREADABLE)
            elif kind == "dir":
                entries[rel] = {"type": "dir"}
                if not visit(p, rel):
                    entries[rel] = dict(UNREADABLE)
            elif kind == "file":
                got = _read_file(p, opener, rel in cons)
                if got is None:
                    entries[rel] = dict(UNREADABLE)
                else:
                    entries[rel] = {"type": "file", "sha256": got[0]}
                    if got[1] is not None:
                        blobs[got[0]] = got[1]
            else:
                entries[rel] = dict(UNREADABLE)
                special.append(rel)
        return True

    if not visit(run_tree, ""):
        raise OSError(errno.EACCES, "the run tree itself cannot be listed")
    return entries, sorted(special), blobs


def _real_dir(run_tree: str, rel: str) -> bool:
    """Is `rel` ("" is the root) a folder, reached through folders only (no link on the way)?"""
    p = run_tree
    for seg in ([] if rel == "" else rel.split("/")):
        p = os.path.join(p, seg)
        try:
            if not stat.S_ISDIR(os.lstat(p).st_mode):
                return False
        except OSError:
            return False
    return True


def _parent(rel: str) -> str:
    return rel.rsplit("/", 1)[0] if "/" in rel else ""


def watch_plan(run_tree: str, watch) -> tuple:
    """((folder, recursive), ...): for each consequential path, its parent folder when it exists (a folder watch
    sees a create, a rename onto it and a rename away, which a watch on the file's own inode would miss), else its
    nearest existing ancestor folder, recursively (so a path whose folders appear mid-turn is still caught)."""
    out = set()
    for p in watch:
        parent = _parent(p)
        if _real_dir(run_tree, parent):
            out.add((parent, False))
            continue
        anc = parent
        while anc and not _real_dir(run_tree, anc):
            anc = _parent(anc)
        out.add((anc, True))
    # a folder watched recursively covers the same folder watched alone
    rec = {d for d, r in out if r}
    return tuple(sorted((d, r) for d, r in out if r or d not in rec))


def stop_exit_code(returncode: int, *, requested: bool, fault: bool) -> int:
    """The code a `watcher-stop` records (interface 12)."""
    code = 128 - returncode if returncode < 0 else returncode
    if fault:
        return code if code != 0 else 1
    if requested and returncode == -signal.SIGTERM:
        return 0
    return code


def _write_atomic(dest: str, data: bytes, tmp_dir: str):
    """Write `data` to `dest` so a reader never sees half a file: a temp file in the private folder, moved in by
    one rename. `dest` must not exist yet."""
    if os.path.lexists(dest):
        raise FileExistsError(f"{os.path.basename(dest)} already exists")
    fd, tmp = tempfile.mkstemp(dir=tmp_dir)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.rename(tmp, dest)
    except BaseException:
        if os.path.lexists(tmp):
            os.unlink(tmp)
        raise


def _append_line(path: str, rec: dict):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


class Sidecar:
    """The sidecar's state machine: one take's snapshots, watcher and health, driven by `handle` and `pump`.

    factory(run_tree, plan) -> a watcher process: established() -> bool, read_ready() -> [WatchEvent],
    poll() -> returncode | None (Popen's: -n for a death by signal n), request_stop() (SIGTERM),
    force_stop() (SIGKILL, after STOP_TIMEOUT_S). The real one is `inotifywait_factory`; tests inject fakes."""

    def __init__(self, *, run_tree, evidence, watch, factory, tmp_dir, clock=None, sleep=None, opener=None,
                 establish_timeout_s=ESTABLISH_TIMEOUT_S, stop_timeout_s=STOP_TIMEOUT_S):
        self.run_tree, self.evidence, self.tmp_dir = run_tree, evidence, tmp_dir
        self.watch = tuple(watch)
        if not self.watch or not all(rel_path_ok(p) for p in self.watch):
            raise ValueError("watch is a non-empty list of run-tree-relative paths")
        self.factory = factory
        self.clock = CLOCK if clock is None else clock
        self.sleep = time.sleep if sleep is None else sleep
        self.opener = os.open if opener is None else opener
        self.establish_timeout_s, self.stop_timeout_s = establish_timeout_s, stop_timeout_s
        self.watcher = None
        self.state = "new"          # new -> running -> finished, or broken
        self.problems = []          # why the sidecar is broken (sticky)
        self.next_label = None

    # --------------------------------------------------------------------------------------------- records
    def _ev(self, *parts) -> str:
        return os.path.join(self.evidence, *parts)

    def _health(self, kind: str, at: float, **extra):
        _append_line(self._ev(HEALTH), {"kind": kind, "at": at, **extra})

    def _access(self, at: float, path: str, op: str):
        _append_line(self._ev(ACCESS), {"at": at, "path": path, "op": op})

    def _break(self, problem: str):
        self.state = "broken"
        self.problems.append(problem)

    # --------------------------------------------------------------------------------------------- the watcher
    def _event(self, ev: WatchEvent) -> bool:
        """Log one stream event. False on a fault (an event name outside the closed table)."""
        names = tuple(ev.names)
        unknown = [n for n in names if n not in EVENT_OPS and n not in EVENT_FLAGS and n != OVERFLOW_EVENT]
        if unknown or not names:
            return False
        at = self.clock() if ev.at is None else ev.at
        if OVERFLOW_EVENT in names:
            self._health(QUEUE_OVERFLOW, at)
        if ev.path in self.watch:
            for op in [o for o in (OPEN, MODIFY, DELETE) if o in {EVENT_OPS[n] for n in names if n in EVENT_OPS}]:
                self._access(at, ev.path, op)
        return True

    def _drain(self) -> bool:
        ok = True
        for ev in self.watcher.read_ready():
            if ok:
                ok = self._event(ev)
            # after a fault, the rest of the stream is not read as accesses
        return ok

    def _wait_exit(self):
        t0 = self.clock()
        while self.watcher.poll() is None:
            if self.clock() - t0 > self.stop_timeout_s:
                self.watcher.force_stop()
                t1 = self.clock()
                while self.watcher.poll() is None and self.clock() - t1 <= self.stop_timeout_s:
                    self.sleep(POLL_S)
                return self.watcher.poll() if self.watcher.poll() is not None else -signal.SIGKILL, True
            self.sleep(POLL_S)
        return self.watcher.poll(), False

    def _stop(self, *, fault: bool = False) -> float:
        """Stop the watcher, drain every event it produced, then write watcher-stop stamped at that instant.
        Returns the stamp."""
        self.watcher.request_stop()
        rc, forced = self._wait_exit()
        clean = self._drain()
        fault = fault or forced or not clean
        at = self.clock()
        self._health(WATCHER_STOP, at, exit_code=stop_exit_code(rc, requested=True, fault=fault))
        self.watcher = None
        if fault:
            self._break(f"the watcher faulted ({'it did not stop' if forced else 'an event outside the closed table'})"
                        f" and was stopped; it is not re-armed")
        return at

    def _arm(self) -> float | None:
        """Arm a watcher on a freshly chosen plan, wait until its watches are established, then write
        watcher-start stamped at that instant. None (and broken, with no start written) when the re-arm fails."""
        try:
            w = self.factory(self.run_tree, watch_plan(self.run_tree, self.watch))
        except Exception as e:  # noqa: BLE001  (any failure of the factory is a failed re-arm)
            self._break(f"the watcher could not be armed ({type(e).__name__}); no watcher-start was written")
            return None
        t0 = self.clock()
        while not w.established():
            if w.poll() is not None or self.clock() - t0 > self.establish_timeout_s:
                if w.poll() is None:
                    w.force_stop()
                self._break("the watcher never reported its watches established; no watcher-start was written")
                return None
            self.sleep(POLL_S)
        at = self.clock()
        self._health(WATCHER_START, at)
        self.watcher = w
        return at

    def pump(self):
        """Drain the running watcher's stream into the log, and detect a watcher that died by itself (stamped at
        detection, with its code; never re-armed) or a fault (stopped)."""
        if self.state != "running" or self.watcher is None:
            return
        clean = self._drain()
        if not clean:
            self._stop(fault=True)
            return
        rc = self.watcher.poll()
        if rc is not None:
            self._drain()
            at = self.clock()
            code = stop_exit_code(rc, requested=False, fault=False)
            self._health(WATCHER_STOP, at, exit_code=code)
            self.watcher = None
            self._break(f"the watcher exited on its own (exit code {code}); it is not re-armed")

    # --------------------------------------------------------------------------------------------- snapshots
    def _snapshot(self, label: str, taken_at: float) -> tuple:
        entries, special, blobs = snapshot_tree(self.run_tree, self.watch, opener=self.opener)
        for name, data in sorted(blobs.items()):
            dest = self._ev(BLOBS, name)
            if not os.path.lexists(dest):
                _write_atomic(dest, data, self.tmp_dir)
        body = json.dumps({"label": label, "taken_at": taken_at, "entries": entries}, sort_keys=False,
                          separators=(",", ":")) + "\n"
        _write_atomic(self._ev(SNAPSHOTS, f"{label}.json"), body.encode("utf-8"), self.tmp_dir)
        unreadable = sorted(p for p, st in entries.items() if st["type"] == "unreadable")
        return unreadable, sorted(p for p in unreadable if p in self.watch), special

    # --------------------------------------------------------------------------------------------- commands
    def handle(self, command, label=None) -> dict:
        try:
            self.pump()
            if command == "begin" and label is None:
                return self._begin()
            if command == "snapshot":
                return self._snap_command(label)
            if command == "finish" and label is None:
                return self._finish()
            if command == "status" and label is None:
                return self._reply("status", None, problems=[] if self.state == "running"
                                   else (list(self.problems) or [f"the sidecar is {self.state}"]))
            return self._reply(command if command in COMMANDS else "status", None,
                               problems=[f"unknown command or label: {command!r}"])
        except Exception as e:  # noqa: BLE001  (a reply is always one line; the error's type names it)
            self._break(f"{command}: {type(e).__name__}: {e}")
            return self._reply(command if command in COMMANDS else "status",
                               "pre-1" if command == "begin" else (label if label_ok(label) else None),
                               problems=list(self.problems))

    def _reply(self, command, label, *, taken_at=None, rearmed_at=None, unreadable=(), uc=(), problems=()) -> dict:
        probs = list(problems)
        if command == "snapshot" and not label_ok(label):
            label = None          # a refused label is never echoed as if it were one
        return {"ok": not probs, "command": command, "label": label, "taken_at": taken_at,
                "rearmed_at": rearmed_at, "unreadable": list(unreadable), "unreadable_consequential": list(uc),
                "problems": probs}

    def _begin(self) -> dict:
        if self.state != "new":
            return self._reply("begin", "pre-1", problems=[f"begin twice (the sidecar is {self.state})"])
        present = sorted(os.listdir(self.evidence))
        if [n for n in present if n != LEDGER]:
            self._break(f"the evidence folder is not empty at begin: {present}")
            return self._reply("begin", "pre-1", problems=list(self.problems))
        os.mkdir(self._ev(SNAPSHOTS))
        os.mkdir(self._ev(BLOBS))
        for n in CREATED_AT_BEGIN:
            os.close(os.open(self._ev(n), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644))
        taken_at = self.clock()
        unreadable, uc, _ = self._snapshot("pre-1", taken_at)
        self.state = "running"
        self.next_label = "post-1"
        rearmed = self._arm()
        return self._reply("begin", "pre-1", taken_at=taken_at, rearmed_at=rearmed, unreadable=unreadable,
                           uc=uc, problems=list(self.problems))

    def _snap_command(self, label) -> dict:
        if not label_ok(label):
            return self._reply("snapshot", None, problems=["the label is not pre-<k> (k >= 2) or post-<k> (k >= 1)"])
        if label != self.next_label:
            return self._reply("snapshot", label, problems=[f"{label} out of order: the next snapshot is "
                                                            f"{self.next_label}"])
        if self.state == "running":
            taken_at, unreadable, uc = self._pause(label)
            rearmed = self._arm() if self.state == "running" else None
        else:
            taken_at = self.clock()
            unreadable, uc, _ = self._snapshot(label, taken_at)
            rearmed = None
        side, k = _LABEL.fullmatch(label).groups()
        self.next_label = f"pre-{int(k) + 1}" if side == "post" else f"post-{k}"
        return self._reply("snapshot", label, taken_at=taken_at, rearmed_at=rearmed, unreadable=unreadable,
                           uc=uc, problems=list(self.problems))

    def _pause(self, label: str) -> tuple:
        """The pause: the watcher stopped and drained, the stop stamped, then the snapshot taken at that stamp (the
        snapshot opens every file, so the watcher must not see it)."""
        taken_at = self._stop()
        unreadable, uc, _ = self._snapshot(label, taken_at)
        return taken_at, unreadable, uc

    def _finish(self) -> dict:
        if self.state == "running":
            self._stop()
            if self.state == "running":
                self.state = "finished"
            return self._reply("finish", None, problems=list(self.problems))
        return self._reply("finish", None, problems=list(self.problems) or [f"the sidecar is {self.state}"])


# ------------------------------------------------------------------------------------------------- the real watcher
class _InotifyWatcher:
    """The real watcher process (inotifywait), parsed by the PENDING format. Never run in tests."""

    def __init__(self, proc, run_tree: str):
        self.proc, self.run_tree = proc, run_tree
        self._out, self._err, self._established = b"", b"", False
        os.set_blocking(proc.stdout.fileno(), False)
        os.set_blocking(proc.stderr.fileno(), False)

    def _read(self, fh) -> bytes:
        try:
            return os.read(fh.fileno(), CHUNK) or b""
        except BlockingIOError:
            return b""

    def established(self) -> bool:
        self._err += self._read(self.proc.stderr)
        if INOTIFYWAIT_FORMAT["established"].encode() in self._err:
            self._established = True
        return self._established

    def read_ready(self) -> list:
        while True:
            b = self._read(self.proc.stdout)
            if not b:
                break
            self._out += b
        lines, _, self._out = self._out.rpartition(b"\n")
        out = []
        fmt = INOTIFYWAIT_FORMAT
        for raw in (lines.split(b"\n") if lines else []):
            fields = dict(zip(fmt["fields"], raw.decode("utf-8", "surrogateescape").split(fmt["separator"])))
            path = fields.get("path", "")
            rel = path[len(self.run_tree) + 1:] if path.startswith(self.run_tree + "/") else ""
            at = float(fields["at"]) if INOTIFYWAIT_SUBSECOND is True and "at" in fields else None
            out.append(WatchEvent(at, rel, tuple(fields.get("events", "").split(","))))
        return out

    def poll(self):
        return self.proc.poll()

    def request_stop(self):
        self.proc.terminate()

    def force_stop(self):
        self.proc.kill()


def inotifywait_factory(run_tree: str, plan) -> _InotifyWatcher:
    """The one process start of the sidecar: inotifywait over the plan's folders. Refused while any of its values
    is PENDING."""
    require_ready()
    argv = list(INOTIFYWAIT_ARGV) + ["-e", ",".join(INOTIFYWAIT_EVENTS)]
    for d, rec in plan:
        argv += (["-r"] if rec else []) + ["--", os.path.join(run_tree, d) if d else run_tree]
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, close_fds=True)
    return _InotifyWatcher(proc, run_tree)


# ------------------------------------------------------------------------------------------------- serve and ctl
def _serve(args) -> int:
    require_ready()
    os.makedirs(PRIVATE_TMP, mode=0o700)
    os.makedirs(CTL_DIR, mode=0o700)
    sc = Sidecar(run_tree=args.run_tree, evidence=args.evidence, watch=args.watch, factory=inotifywait_factory,
                 tmp_dir=PRIVATE_TMP)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(CTL_SOCKET)
    srv.listen(1)
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    sel = selectors.DefaultSelector()
    sel.register(srv, selectors.EVENT_READ)
    while True:
        for _key, _ in sel.select(timeout=POLL_S):
            conn, _ = srv.accept()
            with conn, conn.makefile("rwb") as fh:
                try:
                    req = json.loads(fh.readline())
                    reply = sc.handle(req.get("command"), req.get("label"))
                except ValueError:
                    reply = sc._reply("status", None, problems=["a request that is not one JSON line"])
                fh.write((json.dumps(reply) + "\n").encode())
                fh.flush()
        sc.pump()


def _ctl(args) -> int:
    label = args.label
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(CTL_SOCKET)
            with s.makefile("rwb") as fh:
                fh.write((json.dumps({"command": args.command, "label": label}) + "\n").encode())
                fh.flush()
                line = fh.readline().decode()
        reply = json.loads(line)
    except (OSError, ValueError) as e:
        reply = {"ok": False, "command": args.command, "label": label if label_ok(label) else None,
                 "taken_at": None, "rearmed_at": None, "unreadable": [], "unreadable_consequential": [],
                 "problems": [f"no reply from the sidecar's control channel ({type(e).__name__})"]}
    sys.stdout.write(json.dumps(reply) + "\n")
    return 0 if reply.get("ok") is True else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sidecar")
    sub = ap.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--run-tree", required=True)
    s.add_argument("--evidence", required=True)
    s.add_argument("--watch", action="append", required=True)
    c = sub.add_parser("ctl")
    c.add_argument("command", choices=COMMANDS)
    c.add_argument("label", nargs="?")
    args = ap.parse_args(argv)
    return _serve(args) if args.mode == "serve" else _ctl(args)


if __name__ == "__main__":
    sys.exit(main())
