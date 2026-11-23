#!/usr/bin/env python3
"""Lane w6h (Gap Study round 4, slice S6): the CP2 drive lifecycle, part 2, end to end on a FAKE runtime.

The plan's test_box_integration.py has two halves. This module is the fake-runtime half: drive.py's TakeDriver and
TakeRepo inside a real batch.Batch, over a stateful fake container runtime (FakeBox) that answers run_take's argv
lists the way the box would, on scratch git repositories. The real-box half (one stub take on athena's box, with no
model) is CP2's real-box step and is NOT here: `RealBoxHalf` names it, and its one method raises SkipTest with that
reason (see the named question in lane-reports/w6h-drive-lifecycle.md: the battery allows no skip yet).

What is tested, each guard with its own bound check and a whole-file witness of drive.py:

  B1-rollback    a refused commit puts the outcome ledger back to HEAD's bytes and unstages what it staged (ruling
                 S6-Q2); the next take then registers and commits. Witness: the restore call removed.
  B2-preflight   drive() reaches preflight only through S1's entry point (preflight_take -> collect_and_evaluate),
                 once, before any turn, with the Launched record launch returned (its spec), the sidecar's own
                 launch record, the take's evidence folder and the sidecar's parsed begin reply; the record is
                 written beside the evidence. Witness: preflight skipped (read as passed).
  B3-preturn     a failed preflight, or a typed refusal inside it, runs no turn, is written to refusal.json (the
                 refusal) and routes as a rehearsal. Witness: a failed record read as passed.
  B4-scan        scan -> mask -> route -> commit (ruling S6-Q3): a planted fake value in a turn's stream is masked on
                 disk before drive() returns, counted in events.outside_reach with the checker's events, annotated
                 (mask, event) and committed masked. Witness: the drive step's scan replaced by a clean result.
  B5-cleanup     on every road (a passed take, a failed preflight, a typed refusal, an adapter that raises
                 mid-take, a timed-out turn, a scan refusal), the agent's processes are killed by an exec as the
                 agent's uid and none is left, and every container and the network are removed by their recorded
                 ids. Witness: the finally path's cleanup removed.
  B6-quiesce     a background process that outlives its turn is polled up to the quiescence cap, then killed as the
                 agent's uid and polled to none, and only then is the turn's snapshot signalled; the survivors are
                 counted and quiescence_kill is set; a timed-out turn's processes are killed at once. Witness: the
                 cap kill removed.
  B7-remove      remove(id) removes the take container by its recorded id only while the full listing holds it, and
                 raises if it is still listed after (batch's A LEAK); a launch whose partial teardown left the take
                 container carries its id. Witness: remove() never removes.
  B8-config      the per-take config folder outlives the drive and is deleted once the commit has landed
                 (TakeRepo.on_published), never after a refused commit. Witness: the on_published call removed.

Lane w6i (slice S6b, ruling S6b-gap4-1) adds the carried items, each with its own bound check and witness:

  B10-adapter-end  the driver ends the adapter by its own flag (set when start_take returned), so an adapter that
                   keeps its state under another spelling is still ended once on every road. Witness: the
                   adapter's private `_state` read again.
  B11-postflight   preflight.postflight runs after the cleanup and before the scan: a clean config folder gives a
                   committed postflight.json with ok true; a credential-named file left there stops the take
                   (DriveRefused naming it), records ok false and keeps the folder. Witness: postflight skipped.
  B12-publish      a config folder that could not be deleted after the commit is recorded, the commit stays, and
                   the next launch refuses naming the slot (ruling D5). Witness: launch ignores the record.
  B13-history      an outcome without leaked_container or leaked_containers is a typed HistoryRefused naming the
                   key, never a bare KeyError (W6H-R2-1). Witness: the key check removed.
  B14-net          a network the teardown failed to remove is committed as "network:<id>" and refuses the restart
                   while it is listed, naming it (R-S6-net). Witness: the restart lists containers only.

Fakes and synthetic strings only: no model, vendor, network, container runtime, credential or holdout. Every
process start except `git -C <scratch>` trips the guard armed in setUpModule, which also patches prereg's readers
(this base has no pre-registration; drive.py reads one at import) and the PENDING runtime spellings run_take needs
(INSPECT_STATUS, TOP_FORMAT), and only then imports drive.py. Preflight's own checks are S1's (tests/test_preflight.py);
here collect_and_evaluate is a spy that returns a closed preflight record.

Witnesses follow the registry pattern of the earlier gap4 lanes: drive.py with one exact anchor edit, compiled in
memory as its own module (never written to disk). A kill counts only when the bound check is green on the real
module first and then returns at least one line with its own prefix and no ERROR line.
"""

from __future__ import annotations

import contextlib
import stat
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import agent_adapter as aa  # noqa: E402
import batch  # noqa: E402
import harness_bookkeeping as hb  # noqa: E402
import prereg  # noqa: E402
import routing  # noqa: E402
import variants  # noqa: E402
from box import preflight as pf  # noqa: E402
from box import run_take as rt  # noqa: E402
from box import sidecar as sc  # noqa: E402
from graders import labels4  # noqa: E402

drive = None            # imported in setUpModule, after the guard and the patches
SCRATCH: Path | None = None
_STACK = contextlib.ExitStack()

TOKEN = "synthetic-login-value-" + "fedcba9876543210"      # a planted fake, never a real login
IMAGE = "sha256:" + "f" * 64
PLACEHOLDER_NET = "e" * 64
MODEL = "synthetic-model"
PROJECT = "run-0000abcd"                                   # S6b: the operator steps' project name (synthetic)
SESSION_ID = "0000abcd-1b3d-5c7e-9a1f-2b4d6f8a0c11"          # S6c: the take's imposed session id (synthetic)
PROFILE = {"permission_mode": "bypassPermissions", "version": "0.0.1"}
TOP = {"ps_options": ["-eo", "pid,uid,comm"], "pid_column": "PID", "uid_column": "UID",
       "uid_namespace": "host"}
UID_MAP = [(0, 1000, 1), (1, 100000, 65536)]
SIDECAR_IMAGE = "sha256:" + "5" * 64                       # synthetic sidecar image id


def sidecar_cmd(tree):
    """The sidecar's launch command as create_argv builds it (setpriv launcher, interpreter, program, serve)."""
    return [*sc.WATCHER_LAUNCHER, *sc.INTERPRETER, sc.PROGRAM, "serve", "--run-tree", tree,
            "--evidence", sc.EVIDENCE_MOUNT]
AGENT_HOST_UID = 100000 + 10001 - 1
CAP_S, POLL_S = 30, 5
REAL_BOX_STEP = ("CP2's real-box step: one stub take on athena's box with no model (plan, CREATE "
                 "tests/test_box_integration.py), which waits on J1, 'athena box setup done'")


# ------------------------------------------------------------------------------------------------ the process guard
class GuardTripped(Exception):
    """A process start this module never allows."""


_SWEEP_LOCK = threading.Lock()
_REAL = {"run": subprocess.run, "Popen": subprocess.Popen}


def _allowed(args) -> bool:
    argv = list(args) if isinstance(args, (list, tuple)) else None
    if not argv or len(argv) < 4 or argv[0] != "git" or argv[1] != "-C" or SCRATCH is None:
        return False
    try:
        return Path(str(argv[2])).resolve().is_relative_to(SCRATCH)
    except (OSError, ValueError):
        return False


def _gate(name):
    real = _REAL[name]

    def gate(args, *a, **kw):
        if _allowed(args):
            return real(args, *a, **kw)
        raise GuardTripped(f"process guard: subprocess.{name} refused {args!r}"[:200])
    return gate


def _trip(name):
    def trip(*a, **kw):
        raise GuardTripped(f"process guard: {name} refused")
    return trip


def table() -> dict:
    t = copy.deepcopy(routing.load_table())
    t["pin_profiles"] = {hb.CLAUDE_CODE: {MODEL: dict(PROFILE)}}
    t["pin_profiles_status"] = "RULED (TEST-ONLY): one injected profile"
    t["spend_cap_markers_status"] = "RULED (TEST-ONLY): the spend-cap list opened for the tests"
    return t


def row(n=1, **kw):
    cell = variants.task_cells({"factor": None}, {"wordings": [{"id": "w1"}, {"id": "w2"}]})
    r = {"arm": "A", "task": "synthetic-task", "model": MODEL,
         "agent": {"harness": hb.CLAUDE_CODE, "version": PROFILE["version"]}, **cell[(n - 1) % len(cell)],
         "slot": f"s{n}", "half_cell": "c1"}
    r.update(kw)
    return r


def setUpModule():
    global drive, SCRATCH
    # Wave 6 merge (binding W6M1, tests/test_wave6_bindings.py): check_take.py puts evals/ on sys.path when
    # imported; registered first, so the stack's close puts sys.path back, in place, last.
    _STACK.callback(sys.path.__setitem__, slice(None), list(sys.path))
    SCRATCH = Path(_STACK.enter_context(tempfile.TemporaryDirectory(prefix="w6h-"))).resolve()
    home = SCRATCH / "home"
    home.mkdir()
    keep = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "TMPDIR") if k in os.environ}
    keep.update(HOME=str(home), XDG_CONFIG_HOME=str(home), GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    _STACK.enter_context(mock.patch.dict(os.environ, keep, clear=True))
    for name in ("run", "Popen"):
        _STACK.enter_context(mock.patch.object(subprocess, name, _gate(name)))
    for name in ("call", "check_call", "check_output", "getoutput", "getstatusoutput"):
        _STACK.enter_context(mock.patch.object(subprocess, name, _trip(f"subprocess.{name}")))
    for name in ("system", "popen", "kill", "killpg", "posix_spawn", "posix_spawnp", "fork", "forkpty"):
        if hasattr(os, name):
            _STACK.enter_context(mock.patch.object(os, name, _trip(f"os.{name}")))
    _STACK.enter_context(mock.patch.object(prereg, "load", lambda: {"driver_constants": {}}))
    _STACK.enter_context(mock.patch.object(prereg, "require_frozen", lambda what: {"rows": [row(n) for n in
                                                                                           range(1, 7)]}))
    # The runtime spellings only the real box can tell (run_take's PENDING values), filled for the fake runtime only.
    _STACK.enter_context(mock.patch.object(rt, "INSPECT_STATUS", "confirmed-in-test"))
    _STACK.enter_context(mock.patch.object(rt, "TOP_FORMAT", TOP))
    # Lane w6j (S6c C8): Claude Code's fallback variables, PENDING until confirmed at the pinned version: none here.
    _STACK.enter_context(mock.patch.object(rt, "FALLBACK_ENV", {}))
    # The bypass acceptance is RULED not required in -p (glitch-06, 14 Oct 2026): no stand-in key.
    import drive as imported
    drive = imported
    # Lane freeze-gates-fix S8 (glitch-f1's ruling 3 on the lane's hand-back, Wed 21 Oct 2026, under Javier's
    # standing delegation): the production native-reader registry, read hermetically. Since Javier's acceptance commit
    # (5457e75e) the study holds committed acceptance records, so the registry's default read runs git on the study
    # tree, which this module's process guard refuses (git only under SCRATCH). Every fake-runtime road here drives a
    # scratch study, so a registry call naming no study, or the study tree itself, reads an empty scratch folder with no
    # acceptance record (the state those roads model: a harness no reader is registered for). A call naming a scratch
    # study (a road's own registration) is passed through unchanged. The real tree's registry, both accepted readers,
    # is asserted where no guard stands: test_native_reader_registration and test_vendor_admission.
    import native_reader_registration as nrr
    real_registry, study_tree = nrr.production_readers, nrr.HERE.resolve()
    unregistered = SCRATCH / "no-acceptance-record"
    unregistered.mkdir()

    def scratch_registry(study=None):
        if study is None or Path(study).resolve() == study_tree:
            study = unregistered
        return real_registry(study)
    _STACK.enter_context(mock.patch.object(nrr, "production_readers", scratch_registry))


def tearDownModule():
    _STACK.close()


# ------------------------------------------------------------------------------------------------ the fake box
def ok(stdout="", stderr=""):
    return rt.Completed(0, stdout, stderr)


def reply(command, label=None, *, ok_=True, unreadable_consequential=()):
    r = {"ok": ok_, "command": command, "label": label, "taken_at": 1.0 if command in ("begin", "snapshot") else None,
         "rearmed_at": 2.0 if command in ("begin", "snapshot") else None,
         "unreadable": list(unreadable_consequential), "unreadable_consequential": list(unreadable_consequential),
         "problems": [] if ok_ else ["synthetic problem"]}
    return json.dumps({k: r[k] for k in sc.REPLY_FIELDS}) + "\n"


class FakeOwnership:
    """The box lane's ownership road (box/ownership.py, 81ede46d) as drive's interface names it
    (drive.OWNERSHIP_GRANT_PARAMS, OWNERSHIP_RESTORE_PARAMS), on fakes only: each call is appended to `events` with
    the box's call count at that moment (so a test reads its order against the containers), and fails when told.

    fail_grant, fail_restore, fail_write, fail_read   raise OwnershipError (carrying its record) from that step

    Faithful to the host's access (drive-wiring review MAJOR 1, probe P4; glitch-06's ruling): the grant leaves the
    evidence folder unwritable by the host (0555, the watcher's 0755 as the host user sees it) and the restore gives
    it back, so any host write into a granted folder during the take fails here as it would on the box. Only the
    fake box, standing in for the containers, writes there (FakeBox.as_watcher).

    operator_write and operator_read stand in for the box's in-box steps (ownership review MAJOR 2; box contract at
    4c3d8e53): they write or read the bytes at the exact relative path with low-level calls that never follow a link
    (never `open`, so a test can tell a host-side access by drive.py from these)."""

    class OwnershipError(RuntimeError):
        def __init__(self, message: str, record: dict):
            super().__init__(message)
            self.record = record

    def __init__(self, box=None, *, fail_grant=False, fail_restore=False, fail_write=False, fail_read=False):
        self.box, self.fail_grant, self.fail_restore, self.fail_write = box, fail_grant, fail_restore, fail_write
        self.fail_read = fail_read
        self.events: list = []
        self.config_folders: list = []

    def config_folder(self, runtime, *, image, harness, run_tree, config_dir, model, lease, uid_map,
                      caller_env=None):
        """B11 (lane vendor-b11 round 3): the box's ownership.config_folder on fakes. The record's arguments are
        kept (config_folders, never `events`, whose order other checks read) and returned as the stand-in record an
        O or G turn hands run_turn; the real check and its census are tests/test_config_folder.py's."""
        rec = {"image": image, "harness": harness, "run_tree": run_tree, "config_dir": config_dir, "model": model,
               "lease": lease, "uid_map": uid_map}
        self.config_folders.append(rec)
        return rec

    def _at(self):
        return None if self.box is None else len(self.box.calls)

    def grant(self, runtime, *, image, run_tree, config_dir, evidence_dir, caller_env=None):
        got = self._grant(runtime, image=image, run_tree=run_tree, config_dir=config_dir, evidence_dir=evidence_dir)
        os.chmod(evidence_dir, 0o555)        # drive-wiring review P4: the watcher's 0755 folder, as the host sees it
        os.chmod(config_dir, 0o000)          # P4: the agent's 0700 folder, as the host sees it
        return got

    def _grant(self, runtime, *, image, run_tree, config_dir, evidence_dir):
        self.events.append(("grant", {"image": image, "run_tree": run_tree, "config_dir": config_dir,
                                      "evidence_dir": evidence_dir, "at": self._at(),
                                      "exist": [os.path.isdir(d) for d in (run_tree, config_dir, evidence_dir)]}))
        if self.fail_grant:
            raise self.OwnershipError("grant-run_tree failed: synthetic", {"ok": False, "steps": [
                {"step": "grant-run_tree", "returncode": 1, "stderr": "synthetic"}]})
        return {"ok": True, "steps": [{"step": f"grant-{n}", "returncode": 0, "stderr": ""}
                                      for n in ("run_tree", "config_dir", "evidence_dir")]}

    def restore(self, runtime, *, image, run_tree, config_dir, evidence_dir, ids, caller_env=None):
        if os.path.isdir(evidence_dir) and not os.path.islink(evidence_dir):
            os.chmod(evidence_dir, 0o755)    # P4: the host's own folder again, as a real restore leaves it
        if os.path.isdir(config_dir) and not os.path.islink(config_dir):
            os.chmod(config_dir, 0o700)
        self.events.append(("restore", {"image": image, "run_tree": run_tree, "config_dir": config_dir,
                                        "evidence_dir": evidence_dir, "ids": list(ids), "at": self._at()}))
        if self.fail_restore:
            raise self.OwnershipError("restore failed (1 problem(s)): synthetic", {"ok": False, "steps": [],
                                                                                  "problems": ["synthetic"]})
        return {"ok": True, "steps": [{"step": f"restore-{n}", "returncode": 0, "stderr": ""}
                                      for n in ("run_tree", "config_dir", "evidence_dir")], "problems": []}

    def _parent(self, run_tree, rel_path):
        """(the parent folder's descriptor, the last name), every step opened with O_NOFOLLOW."""
        parts = rel_path.split("/")
        if rel_path.startswith("/") or any(x in ("", ".", "..") for x in parts):
            raise self.OwnershipError(f"operator step refused: {rel_path!r} is not an exact relative path", {})
        fd = os.open(run_tree, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for name in parts[:-1]:
                nxt = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nxt
        except OSError as e:
            os.close(fd)
            if isinstance(e, FileNotFoundError):
                return None, parts[-1]
            raise self.OwnershipError(f"operator step refused: {type(e).__name__}", {}) from None
        return fd, parts[-1]

    def operator_write(self, runtime, *, image, run_tree, rel_path, data, caller_env=None):
        self.events.append(("operator_write", {"image": image, "run_tree": run_tree, "rel_path": rel_path,
                                               "sha256": hashlib.sha256(data).hexdigest(), "at": self._at()}))
        if self.fail_write:
            raise self.OwnershipError("operator-write failed: synthetic", {"ok": False, "steps": []})
        fd, name = self._parent(run_tree, rel_path)
        if fd is None:
            raise self.OwnershipError("operator-write refused: a missing parent", {})
        try:
            out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644, dir_fd=fd)
            try:
                os.write(out, data)
            finally:
                os.close(out)
        finally:
            os.close(fd)
        return {"ok": True, "path": rel_path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

    def operator_read(self, runtime, *, image, root_kind, run_tree, config_dir, rel_path, caller_env=None):
        # the box's O-3 signature (box 161d038d; item D, glitch-6b 15 Oct 2026): the root chosen by kind from the pair
        root = run_tree if root_kind == "run_tree" else config_dir if root_kind == "config" else None
        self.events.append(("operator_read", {"image": image, "root_kind": root_kind, "root": root,
                                              "run_tree": root if root_kind == "run_tree" else None,
                                              "rel_path": rel_path, "at": self._at()}))
        if self.fail_read:
            raise self.OwnershipError("operator-read failed: synthetic", {"ok": False, "steps": []})
        if root_kind not in ("run_tree", "config"):
            raise self.OwnershipError(f"operator-read refused: root kind {root_kind!r}", {})
        with FakeBox.as_container(root):
            fd, name = self._parent(root, rel_path)
            if fd is None:
                return None
            try:
                try:
                    f = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                except FileNotFoundError:
                    return None
                except OSError as e:
                    raise self.OwnershipError(f"operator-read refused: {type(e).__name__}", {}) from None
                try:
                    if not stat.S_ISREG(os.fstat(f).st_mode):
                        raise self.OwnershipError("operator-read refused: not a regular file", {})
                    chunks = []
                    while True:
                        b = os.read(f, 65536)
                        if not b:
                            return b"".join(chunks)
                        chunks.append(b)
                finally:
                    os.close(f)
            finally:
                os.close(fd)

    def operator_list(self, runtime, *, image, root_kind, run_tree, config_dir, rel_dir, caller_env=None):
        """One level of a folder, [(name, kind)] with kind file, dir, link or other; never follows a link. The box's
        O-3 signature (box 161d038d): the root chosen by kind from the take's run tree and config folder."""
        root = run_tree if root_kind == "run_tree" else config_dir if root_kind == "config" else None
        self.events.append(("operator_list", {"root_kind": root_kind, "root": root, "rel_dir": rel_dir,
                                              "at": self._at()}))
        if self.fail_read:
            raise self.OwnershipError("operator-list failed: synthetic", {"ok": False, "steps": []})
        if root_kind not in ("run_tree", "config"):
            raise self.OwnershipError(f"operator-list refused: root kind {root_kind!r}", {})
        with FakeBox.as_container(root):
            if rel_dir == ".":                  # the box's root (_rel_dir); "" refuses, as there (B16-1)
                fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            else:
                parent, name = self._parent(root, rel_dir)
                if parent is None:
                    return None
                try:
                    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                except FileNotFoundError:
                    return None
                except OSError as e:
                    raise self.OwnershipError(f"operator-list refused: {type(e).__name__}", {}) from None
                finally:
                    os.close(parent)
            try:
                out = []
                for entry in sorted(os.listdir(fd)):
                    m = os.stat(entry, dir_fd=fd, follow_symlinks=False).st_mode
                    out.append((entry, "link" if stat.S_ISLNK(m) else "dir" if stat.S_ISDIR(m)
                                else "file" if stat.S_ISREG(m) else "other"))
                return out
            finally:
                os.close(fd)

    def names(self) -> list:
        return [name for name, _ in self.events]


class FakeSettingsGuard:
    """The box lane's run-tree settings guard (box/settings_guard.py, d3fd5305) as drive's interface names it, on
    fakes only: baseline hashes every .claude/settings.json and .claude/settings.local.json in the run tree (or
    raises SettingsRefused when told); snapshot_problems names each such file whose snapshot entry differs."""

    class SettingsRefused(ValueError):
        pass

    SETTINGS = re.compile(r"(?:^|.*/)\.claude/settings(?:\.local)?\.json")

    def __init__(self, *, refuse=False):
        self.refuse = refuse
        self.calls: list = []

    def baseline(self, run_tree, *, model):
        self.calls.append(("baseline", run_tree, model))
        if self.refuse:
            raise self.SettingsRefused("synthetic: a settings file carries a forbidden key")
        out = {}
        for base, dirs, files in os.walk(run_tree):
            for f in files:
                rel = os.path.relpath(os.path.join(base, f), run_tree).replace(os.sep, "/")
                if self.SETTINGS.fullmatch(rel):
                    with open(os.path.join(base, f), "rb") as fh:
                        out[rel] = hashlib.sha256(fh.read()).hexdigest()
        return out

    def snapshot_problems(self, snapshot, base):
        self.calls.append(("snapshot", snapshot.get("label")))
        got = {k: v.get("sha256") for k, v in snapshot["entries"].items() if self.SETTINGS.fullmatch(k)}
        return [f"{k}: not the baseline's" for k in sorted(set(got) | set(base)) if got.get(k) != base.get(k)]


class FakeBox:
    """A container runtime that answers run_take's argv lists from its own state: networks, containers, the agent's
    processes in each take container, and the sidecar's health records written into the evidence folder.

    fail_rm      kinds ("take", "sidecar", "proxy") whose `rm --force` fails, `times` times each
    stubborn     the agent's processes survive the kill (a process the uid kill cannot reach)
    begin        "ok" | "refused" | "malformed": the sidecar's begin reply
    """

    def __init__(self, *, fail_rm=(), fail_times=1, stubborn=False, begin="ok", unreadable=(), fail_net=False):
        self.n = 0
        self.networks: set = set()
        self.containers: dict = {}          # id -> {"kind", "running", "ev"}
        self.procs: dict = {}               # take id -> [[pid, polls left before it exits by itself (None: never)]]
        self.calls: list = []
        self.snapshots: list = []           # (label, agent processes alive at that moment)
        self.kills: list = []               # (take id, user)
        self.removed: list = []
        self.fail_rm, self.fail_times, self.stubborn = set(fail_rm), fail_times, stubborn
        self.begin, self.unreadable, self.fail_net = begin, list(unreadable), fail_net
        self.specs: dict = {}
        self.spawned: list = []
        self.clock = None                   # S6b: the rig's clock, so evidence, turns and operator events share one
        self.gap = False                    # S6b: a watcher that never re-arms after a snapshot (a health gap)

    def tick(self) -> float:
        """S6b: the host clock moved on by a millisecond (never through sleep, whose calls B6 reads)."""
        if self.clock is None:
            return 1.0
        self.clock.now += 0.001
        return self.clock.now

    @staticmethod
    @contextlib.contextmanager
    def as_container(folder):
        """The fake box acts inside a granted folder as its owner would (the host user cannot during the take)."""
        mode = stat.S_IMODE(os.stat(folder).st_mode)
        need = stat.S_IRWXU
        if mode & need != need:
            os.chmod(folder, mode | need)
        try:
            yield
        finally:
            if mode & need != need:
                os.chmod(folder, mode)

    @staticmethod
    @contextlib.contextmanager
    def as_watcher(ev):
        """The fake sidecar writes the evidence folder as the watcher would (the host user cannot after the grant)."""
        mode = stat.S_IMODE(os.stat(ev).st_mode)
        if not mode & stat.S_IWUSR:
            os.chmod(ev, mode | stat.S_IWUSR)
        try:
            yield
        finally:
            if not mode & stat.S_IWUSR:
                os.chmod(ev, mode)

    def evidence(self, sid, label):
        with self.as_watcher(self.containers[sid]["ev"]):
            return self._evidence(sid, label)

    def _evidence(self, sid, label):
        """S6b: the sidecar's evidence as endstate reads it: the snapshot of the run tree under `label`, stamped at
        the pause's stop (begin also lays out watched.json and an empty access.jsonl)."""
        c = self.containers[sid]
        ev, tree = c["ev"], c["tree"]
        os.makedirs(os.path.join(ev, sc.SNAPSHOTS), exist_ok=True)
        for name, body in (("watched.json", json.dumps({"paths": ["synthetic/consequential.txt"]})),
                           ("access.jsonl", "")):
            if not os.path.exists(os.path.join(ev, name)):
                with open(os.path.join(ev, name), "w", encoding="utf-8") as fh:
                    fh.write(body)
        entries = {}
        for base, dirs, files in os.walk(tree):
            for d in dirs:
                entries[os.path.relpath(os.path.join(base, d), tree).replace(os.sep, "/")] = {"type": "dir"}
            for f in files:
                with open(os.path.join(base, f), "rb") as fh:
                    digest = hashlib.sha256(fh.read()).hexdigest()
                entries[os.path.relpath(os.path.join(base, f), tree).replace(os.sep, "/")] = {"type": "file",
                                                                                            "sha256": digest}
        at = self.tick()
        with open(os.path.join(ev, sc.SNAPSHOTS, f"{label}.json"), "w", encoding="utf-8") as fh:
            json.dump({"label": label, "taken_at": at, "entries": entries}, fh)
        return at

    def new(self) -> str:
        self.n += 1
        return f"{0xab0000 + self.n:064x}"

    def kind(self, cid):
        return self.containers.get(cid, {}).get("kind")

    def spawn(self, take_id, lives=None):
        pid = 4100 + len(self.spawned)
        self.spawned.append(pid)
        self.procs.setdefault(take_id, []).append([pid, lives])

    def alive(self, take_id) -> list:
        return [p for p, _ in self.procs.get(take_id, [])]

    def health(self, sid, kind, at=None, **extra):
        with self.as_watcher(self.containers[sid]["ev"]):
            return self._health(sid, kind, at, **extra)

    def _health(self, sid, kind, at=None, **extra):
        ev = self.containers[sid]["ev"]
        with open(os.path.join(ev, sc.HEALTH), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"kind": kind, "at": self.tick() if at is None else at, **extra}) + "\n")

    def run(self, argv, env=None, timeout=None):
        a = list(argv)
        self.calls.append(a)
        if a[:4] == ["docker", "network", "create", "--internal"]:
            nid = self.new()
            self.networks.add(nid)
            return ok(nid + "\n")
        if a[:3] == ["docker", "network", "rm"]:
            if self.fail_net:
                return rt.Completed(1, "", "synthetic network removal failure")
            self.networks.discard(a[3])
            return ok()
        if a[:3] == ["docker", "network", "connect"] or a[:2] == ["docker", "logs"]:
            return ok("synthetic proxy log line\n" if a[1] == "logs" else "")
        if a[:2] == ["docker", "create"]:
            cid = self.new()
            if "--network-alias" in a:
                self.containers[cid] = {"kind": "proxy", "running": False}
            elif "--label" in a:
                labels = dict(a[i + 1].split("=", 1) for i, x in enumerate(a) if x == "--label")
                self.containers[cid] = {"kind": "sidecar", "running": False, "ev": labels["ev"],
                                        "tree": labels["tree"]}
            else:
                self.containers[cid] = {"kind": "take", "running": False}
                self.specs[cid] = a
            return ok(cid)
        if a[:2] == ["docker", "start"]:
            self.containers[a[2]]["running"] = True
            return ok()
        if a[:3] == ["docker", "container", "inspect"]:
            return self.inspect(a[3])
        if a[:2] == ["docker", "exec"] and a[2] != "--user" and self.kind(a[2]) == "sidecar":
            return self.ctl(a[2], a[a.index("ctl") + 1], a[a.index("ctl") + 2] if len(a) > a.index("ctl") + 2
                            else None)
        if a[:4] == ["docker", "exec", "--user", rt.AGENT_USER] and a[5:] == ["/usr/bin/python3", "-I", "-S", "-c", "import os,signal\ntry:\n os.kill(-1, signal.SIGKILL)\nexcept ProcessLookupError:\n pass"]:
            self.kills.append((a[4], a[3]))
            if not self.stubborn:
                self.procs[a[4]] = []
            return ok()
        if a[:4] == ["docker", "exec", "--user", rt.AGENT_USER] and a[5:10] == ["/usr/bin/python3", "-I", "-S", "-c",
                                                                             rt.SWEEP_PROGRAM]:
            return self.sweep(a)                      # W-3b (review r14): the session sweep, run on the host's folders
        if a[:2] == ["docker", "top"]:
            rows = []
            for proc in self.procs.get(a[2], []):
                rows.append(f"{proc[0]} {AGENT_HOST_UID} node")
            out = "PID UID COMMAND\n" + "".join(r + "\n" for r in rows) + "4001 103002 sleep\n"
            for proc in list(self.procs.get(a[2], [])):     # a process with a life ends on its own after polls
                if proc[1] is not None:
                    proc[1] -= 1
                    if proc[1] <= 0:
                        self.procs[a[2]].remove(proc)
            return ok(out)
        if a[:3] == ["docker", "rm", "--force"]:
            cid = a[3]
            if self.kind(cid) in self.fail_rm and self.fail_times > 0:
                self.fail_times -= 1
                return rt.Completed(1, "", "synthetic removal failure")
            self.containers.pop(cid, None)
            self.procs.pop(cid, None)
            self.removed.append(cid)
            return ok(cid + "\n")
        if a == [rt.RUNTIME_CLIENT, "ps", "--all", "--no-trunc", "--quiet"]:
            return ok("".join(c + "\n" for c in self.containers))
        if a == [rt.RUNTIME_CLIENT, "network", "ls", "--no-trunc", "--quiet"]:     # S6b R-S6-net
            return ok("".join(n + "\n" for n in sorted(self.networks)))
        raise GuardTripped(f"the fake box refuses {a!r}"[:200])

    def sweep(self, a):
        """The session sweep's program run over the take's host folders, each container root mapped to its host folder
        (the run tree is mounted at its own path; the config mount at rt.CONFIG_MOUNT; the container's own /tmp and
        kin are empty here), its paths mapped back to the container's."""
        import contextlib as _cl
        import io as _io
        spec = self.specs[a[4]]
        mapping = {}
        for m in spec:                                   # every bind mount: container target -> host source
            if m.startswith("type=bind,source=") and ",target=" in m:
                src, tgt = m[len("type=bind,source="):].split(",target=", 1)
                mapping[tgt.split(",", 1)[0]] = src
        cfg, tree = mapping[rt.CONFIG_MOUNT], spec[spec.index("--workdir") + 1]
        tree = mapping.get(tree, tree)
        # the container's own mount table, as the fake's read-only root has it: the root read-only, the two binds
        # read-write (at their host paths here), and /proc (never entered)
        import tempfile as _tf
        ro = "--read-only" in spec
        table = _tf.NamedTemporaryFile("w", suffix=".mountinfo", delete=False)
        # the --tmpfs mounts (review r16 MINOR 3): one empty host folder per take for each, mapped back
        tmpfs = getattr(self, "tmpfs_dirs", {}).setdefault(a[4], {t.split(":", 1)[0]: _tf.mkdtemp(prefix="tmpfs-")
                                                                  for i, t in enumerate(spec)
                                                                  if i and spec[i - 1] == "--tmpfs"})
        self.tmpfs_dirs = getattr(self, "tmpfs_dirs", {})
        self.tmpfs_dirs[a[4]] = tmpfs
        table.write(f"1 0 0:1 / / {'ro' if ro else 'rw'},relatime - overlay overlay rw\n"
                    f"2 1 0:2 / {tree} rw,relatime - ext4 /dev/x rw\n3 1 0:3 / {cfg} rw,relatime - ext4 /dev/x rw\n"
                    f"4 1 0:4 / /proc rw,nosuid - proc proc rw\n"
                    + "".join(f"{5 + i} 1 0:{5 + i} / {host} rw,nosuid,nodev,relatime - tmpfs tmpfs rw,mode=1777\n"
                              for i, host in enumerate(tmpfs.values())))
        table.close()
        # sys.argv and sys.stdout are process-global: two takes swept at once (batch's rolling window) would
        # interleave the swaps and leave sys.stdout on a dead buffer, so one sweep at a time.
        with _SWEEP_LOCK:
            buf, saved = _io.StringIO(), sys.argv            # in process: the module's process guard spawns nothing
            sys.argv = ["-c", table.name, str(os.getuid()), a[12], a[13], a[14], a[15]]
            try:
                with _cl.redirect_stdout(buf), FakeBox.as_container(tree), FakeBox.as_container(cfg):   # as the agent
                    exec(compile(rt.SWEEP_PROGRAM, "<the session sweep>", "exec"), {"__name__": "__sweep__"})
            finally:
                sys.argv = saved
        doc = json.loads(buf.getvalue())
        hosts = {cfg: rt.CONFIG_MOUNT, **{host: path for path, host in tmpfs.items()}}

        def back(p):
            for host, inner in hosts.items():
                if p == host or p.startswith(host + "/"):
                    return inner + p[len(host):]
            return p
        doc["files"] = [[back(f[0])] + f[1:] for f in doc["files"]]
        doc["unreadable"] = [[back(u[0]), u[1]] for u in doc["unreadable"]]
        doc["escapes"] = [[back(u[0]), back(u[1])] for u in doc["escapes"]]
        doc["mounts"] = sorted(back(m) for m in doc["mounts"])
        os.unlink(table.name)
        self.sweeps = getattr(self, "sweeps", []) + [doc]
        return ok(json.dumps(doc))

    def inspect(self, cid):
        c = self.containers.get(cid)
        if c is None:
            return rt.Completed(1, "", "no such container")
        if c["kind"] == "sidecar":
            tree = c["tree"]
            # The sidecar's fixed privilege-drop launch (0b6f60f9's accepted delta): boot user, the four boot
            # capabilities as Docker 29.8.1 spells them, no entrypoint, setpriv's launcher in Cmd.
            doc = [{"Image": SIDECAR_IMAGE,
                    "Config": {"User": sc.BOOT_USER, "Entrypoint": [], "Cmd": sidecar_cmd(tree)},
                    "HostConfig": {"NetworkMode": "none", "CapDrop": ["ALL"],
                                   "CapAdd": list(sc.BOOT_INSPECT_CAPABILITIES),
                                   "SecurityOpt": ["no-new-privileges"], "Privileged": False, "PidMode": ""},
                    "Mounts": [{"Type": "bind", "Source": tree, "Destination": tree, "RW": False},
                               {"Type": "bind", "Source": c["ev"], "Destination": sc.EVIDENCE_MOUNT, "RW": True}]}]
            return ok(json.dumps(doc))
        a = self.specs[cid]
        val = lambda flag: a[a.index(flag) + 1]  # noqa: E731
        tree = val("--workdir")
        cfg = [m for m in a if m.startswith("type=bind,source=") and m.endswith("target=" + rt.CONFIG_MOUNT)][0]
        cfg = cfg[len("type=bind,source="):-len(",target=" + rt.CONFIG_MOUNT)]
        from decimal import Decimal
        doc = [{"Image": a[-2],
                "Config": {"User": rt.KEEPALIVE_USER, "Entrypoint": ["sleep"], "Cmd": ["infinity"], "Env": [],
                           "WorkingDir": tree},
                "HostConfig": {"NetworkMode": val("--network"), "CapDrop": ["ALL"], "CapAdd": None,
                               "SecurityOpt": ["no-new-privileges"], "Privileged": False, "Devices": None,
                               "PidMode": "", "PidsLimit": int(val("--pids-limit")), "Memory": int(val("--memory")),
                               "MemoryReservation": int(val("--memory-reservation")),
                               "NanoCpus": int(Decimal(val("--cpus")) * 1_000_000_000),
                               "ReadonlyRootfs": "--read-only" in a,       # derived from the create argv, as Docker does
                               "Tmpfs": {t.split(":", 1)[0]: t.split(":", 1)[1] for i, t in enumerate(a)
                                         if i and a[i - 1] == "--tmpfs"} or None},
                "Mounts": [{"Type": "bind", "Source": tree, "Destination": tree, "RW": True},
                           {"Type": "bind", "Source": cfg, "Destination": rt.CONFIG_MOUNT, "RW": True}],
                "State": {"Running": c["running"], "ExitCode": 0, "OOMKilled": False}}]
        return ok(json.dumps(doc))

    def ctl(self, sid, command, label):
        if command == "begin":
            if self.begin == "timeout":
                raise TimeoutError("synthetic: the begin exec timed out")
            if self.begin == "malformed":
                return ok("not a reply\n")
            if self.begin == "refused":
                return rt.Completed(1, reply("begin", "pre-1", ok_=False), "")
            ev = self.containers[sid]["ev"]
            self.at_begin = sorted(os.listdir(ev))                   # review MAJOR 1: empty; the ledger is host-side
            self.host_ledger_at_begin = os.path.isfile(os.path.join(os.path.dirname(ev), "evidence-ledger.jsonl"))
            self.evidence(sid, "pre-1")                              # S6b: snapshot pre-1, then arm the watcher
            self.health(sid, sc.WATCHER_START)
            return ok(reply("begin", "pre-1"))
        if command == "snapshot":
            takes = [c for c, v in self.containers.items() if v["kind"] == "take"]
            self.snapshots.append((label, sum(len(self.alive(t)) for t in takes)))
            at = self.evidence(sid, label)                           # S6b: the stop stamped at the snapshot's instant
            self.health(sid, sc.WATCHER_STOP, at=at, exit_code=0, ignored_newline_paths=0)
            if not self.gap:
                self.health(sid, sc.WATCHER_START)
            return ok(reply("snapshot", label, unreadable_consequential=self.unreadable))
        if command == "finish":
            self.health(sid, sc.WATCHER_STOP, exit_code=0, ignored_newline_paths=0)
            return ok(reply("finish"))
        return ok(reply("status"))

    def empty(self) -> list:
        """What is still there: containers, networks, agent processes (empty when the box is clean)."""
        left = [f"container {v['kind']} {c[:8]}" for c, v in self.containers.items()]
        left += [f"network {n[:8]}" for n in self.networks]
        left += [f"agent process {p} in {t[:8]}" for t, ps in self.procs.items() for p, _ in ps]
        return left


class Clock:
    def __init__(self):
        self.now = 1000.0
        self.slept: list = []

    def __call__(self):
        return self.now

    def sleep(self, s):
        self.slept.append(s)
        self.now += s


class FakeAdapter(aa.AgentAdapter):
    """No model: each scripted turn writes its stream into the take folder, may start background processes in the
    take container (a background writer), and returns its TurnResult. `raise_at` makes turn n raise (the harness
    cannot go on)."""

    name = hb.CLAUDE_CODE

    def __init__(self, box: FakeBox, take, turns, *, raise_at=None):
        super().__init__()
        self.box, self.take, self.turns, self.raise_at = box, take, list(turns), raise_at
        self.lines: list = []
        self.ended = 0

    def version(self):
        return PROFILE["version"]

    def _start(self, take):
        return {"container_id": self.take.launched.take_id}

    def _turn(self, line, *, first, budget_s):
        n = self._turns + 1
        if self.raise_at == n:
            raise RuntimeError("synthetic harness failure")
        self.lines.append(line)
        spec = self.turns[n - 1]
        path = drive.stream_path(self.take, n)
        started = self.box.tick()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"type": "assistant", "text": spec.get("text", "plain")}) + "\n")
        for lives in spec.get("spawn", ()):
            self.box.spawn(self.take.launched.take_id, lives)
        end = spec.get("end", labels4.END_TURN)
        return aa.TurnResult(exit_code=0 if end == labels4.END_TURN else 137, text=spec.get("text", "plain"),
                             stream_path=path, end_reason=end,
                             init={"model": MODEL, "permission_mode": PROFILE["permission_mode"],
                                   "version": PROFILE["version"]},
                             api_errors=[], counters={"oom_kill_delta": 0, "pids_max_delta": 0},
                             started_at=started, ended_at=self.box.tick(), agent_output=True)

    def _end(self):
        self.ended += 1


EVENT_IDS = tuple(routing.load_table()["checker_reasons_become_events"]["ids"])
EMAIL = "synthetic.account@example.invalid"      # a fake account email, never a real address


def checker_record(**events) -> dict:
    """A closed checker record: no reason, and check4's per-id event counts (0 unless given)."""
    counts = dict.fromkeys(EVENT_IDS, 0)
    counts.update({k.replace("_", "-"): v for k, v in events.items()})
    return {"checker_reasons": [], "checker_events": counts}


def preflight_record(ok_=True) -> dict:
    checks = [{"id": c, "ok": True, "detail": "synthetic"} for c in pf.PREFLIGHT_CHECKS]
    if not ok_:
        checks[0] = dict(checks[0], ok=False, detail="synthetic failure")
    return {"ok": ok_, "checks": checks, "recorded": {}}


class Spy:
    """collect_and_evaluate's stand-in: records every call, returns a closed record or raises."""

    def __init__(self, result=None, raises=None):
        self.result, self.raises, self.calls = result, raises, []

    def __call__(self, runtime, **kw):
        self.calls.append(kw)
        if self.raises is not None:
            raise self.raises
        return copy.deepcopy(self.result if self.result is not None else preflight_record())


def git(root: Path, *args: str) -> str:
    got = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if got.returncode:
        raise RuntimeError(f"scratch git {args[0]} failed: {got.stderr.strip()}")
    return got.stdout.strip()


def git_bytes(root: Path, *args: str) -> bytes:
    got = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if got.returncode:
        raise RuntimeError(f"scratch git {args[0]} failed")
    return got.stdout


@contextlib.contextmanager
def scratch_repo():
    root = Path(tempfile.mkdtemp(dir=SCRATCH)).resolve()
    git(root, "init", "-q")
    for key, value in (("user.name", "synthetic"), ("user.email", "synthetic@example.invalid"),
                       ("commit.gpgsign", "false"), ("maintenance.auto", "false"), ("gc.auto", "0"),
                       ("core.hooksPath", str(SCRATCH / "no-hooks"))):
        git(root, "config", key, value)
    (root / "README").write_text("synthetic scratch repository\n")
    git(root, "add", "--", "README")
    git(root, "commit", "-q", "-m", "Start a synthetic scratch repository")
    yield root


class Rig:
    """One scratch repository, one fake box, a TakeDriver and a TakeRepo wired the way the drive step runs them."""

    def __init__(self, mod, root: Path, *, box=None, turns=None, raise_at=None, checker=None, spy=None,
                 scanner=None, secrets=None, ownership=None, settings_guard=None):
        self.mod, self.root = mod, root
        self.box = box or FakeBox()
        self.ownership = ownership or FakeOwnership(self.box)   # the box lane's road, faked (81ede46d)
        self.settings_guard = settings_guard or FakeSettingsGuard()   # the box lane's guard, faked (d3fd5305)
        self.machine_gate = lambda: []                       # P-2: nothing runs on the fake machine
        self.clock = Clock()
        self.box.clock = self.clock                    # S6b: one host clock for the box, the turns and the driver
        self.turns = turns if turns is not None else [{"text": "plain"}, {"text": "plain again"}]
        self.raise_at = raise_at
        self.adapters: list = []
        self.cfg_parent = Path(tempfile.mkdtemp(dir=SCRATCH)).resolve()
        self.count = 0
        self.spy = spy or Spy()
        self.checked: list = []
        self.checker = checker or self.clean_checker
        self.driver = mod.TakeDriver(
            runtime=self.box, take_folder=self.take_folder, config_parent=str(self.cfg_parent),
            spec_for=self.spec_for, sidecar_for=self.sidecar_for, proxy=rt.ProxyLaunch(
                image="sha256:" + "9" * 64, conf_source=str(SCRATCH / "proxy.conf"), conf_target="/etc/squid/x.conf",
                command=("squid", "-N"), user="13:13", alias="proxy"),
            lock_path=str(SCRATCH / "synthetic.lock"), hosts={"api": "synthetic.invalid"},
            adapter_for=self.adapter_for, script_for=lambda r: [f"line {i}" for i in range(1, len(self.turns) + 1)],
            pin_for=lambda r: batch.expected_pin(r, table()), checker=self.checker,
            secrets=secrets or (lambda: [("token", TOKEN)]), rules_scanner=scanner or (lambda paths: []),
            uid_map=UID_MAP, budget_s=600, finalize_wait_s=CAP_S, poll_s=POLL_S, clock=self.clock,
            sleep=self.clock.sleep, project_for=lambda r: PROJECT, identity_for=self.identity_for,
            ownership=self.ownership, settings_guard=self.settings_guard, machine_gate=self.machine_gate)
        self.repo = mod.TakeRepo(runtime=self.box, record_files=self.driver.record_files,
                                 secrets=lambda: [("token", TOKEN)], rules_scanner=lambda paths: [], root=root,
                                 repo=root, on_published=self.driver.published)

    def identity_for(self, r):
        """Lane w6j (S6c C7): a synthetic identity (the row's registration and the run-tree builder's records)."""
        return {"session_id": SESSION_ID, "row": 0, "row_commit": "c" * 40, "source": "/synthetic/source",
                "fixture": {"sha256": "0" * 64}, "gars_tree_sha": "8a54e0f8cd91caf558d0d168f1b87e36d0bc0b74"}

    def take_folder(self, r):
        self.count += 1
        return str(self.root / "records" / f"{r['slot']}-{self.count}")

    def spec_for(self, r, cfg):
        tree = SCRATCH / f"tree-{self.root.name}-{self.count}"
        tree.mkdir(exist_ok=True)
        return rt.TakeSpec(image=IMAGE, run_tree=str(tree), config_dir=cfg, network=PLACEHOLDER_NET,
                           memory_reservation=512 * 2 ** 20, memory=3 * 512 * 2 ** 20, cpus="2", pids_limit=256)

    def sidecar_for(self, r, ev):
        tree = str(SCRATCH / f"tree-{self.root.name}-{self.count}")
        expect = {"user": sc.BOOT_USER, "network_mode": "none", "cap_drop": ["ALL"],
                  "cap_add": list(sc.BOOT_INSPECT_CAPABILITIES), "security_opt": ["no-new-privileges"],
                  "privileged": False, "image": SIDECAR_IMAGE, "cmd": sidecar_cmd(tree), "entrypoint": [],
                  "pid_mode": "", "mounts": [{"source": tree, "destination": tree, "rw": False},
                                             {"source": ev, "destination": sc.EVIDENCE_MOUNT, "rw": True}]}
        return rt.SidecarLaunch(
            create_argv=("docker", "create", "--network", "none", "--label", "ev=" + ev, "--label", "tree=" + tree,
                         "side-image"),
            start_argv_for=lambda i: ["docker", "start", i],
            ctl_argv_for=lambda i, c, label=None: ["docker", "exec", i, "python3", "-I", "-B", "/opt/w/sidecar.py",
                                                   "ctl", c] + ([label] if label else []),
            rm_argv_for=lambda i: ["docker", "rm", "--force", i], expect=expect)

    def adapter_for(self, r, take):
        a = FakeAdapter(self.box, take, self.turns, raise_at=self.raise_at)
        self.adapters.append(a)
        return a

    def clean_checker(self, r, take, turns):
        self.checked.append((r["slot"], len(turns)))
        return checker_record()

    def take(self, slot="s1"):
        return self.driver._by_slot.get(slot) or [t for t in self.driver.published_takes if t.row["slot"] == slot][-1]

    def batch(self, rows):
        return batch.Batch(self.driver, self.repo, Window(), table=table(), serial=True)


class Window:
    def wait_reset(self):
        return None


@contextlib.contextmanager
def spying(spy):
    with mock.patch.object(pf, "collect_and_evaluate", spy):
        yield spy


def missing_api(mod, prefix, *names):
    gone = [n for n in names if not hasattr(mod, n)]
    return [f"{prefix}: drive.py has no {', '.join(gone)}"] if gone else []


def guarded(prefix):
    """A bound check never raises: an unexpected exception is an ERROR line, never a kill."""
    def wrap(fn):
        def check(mod):
            try:
                return fn(mod, prefix)
            except Exception as e:  # noqa: BLE001
                return [f"ERROR {prefix}: {type(e).__name__}: {str(e)[:240]}"]
        check.__name__ = fn.__name__
        return check
    return wrap


def run_batch(rig, rows):
    with spying(rig.spy):
        b = rig.batch(rows)
        return b, b.run(rows)


# ------------------------------------------------------------------------------------------------ the bound checks
@guarded("B1-rollback")
def b1_rollback(mod, p):
    out = missing_api(mod, p, "TakeDriver", "TakeRepo", "CommitRefused")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root)
        r1 = row(1)
        rig.repo.register(r1, 1)
        rig.repo.commit_records(r1, 1, outcome(r1))              # one committed outcome: the ledger is tracked
        head_ledger = git_bytes(root, "show", "HEAD:outcomes.json")
        r2 = row(2)
        rig.repo.register(r2, 1)
        bad = root / "records" / "bad"
        bad.mkdir(parents=True)
        (bad / "launch.json").write_text(json.dumps({"note": TOKEN}) + "\n")     # unmaskable: the commit refuses
        repo = mod.TakeRepo(runtime=rig.box, record_files=lambda r, a: [(str(bad / "launch.json"), "launch")],
                            secrets=lambda: [("token", TOKEN)], rules_scanner=lambda paths: [], root=root, repo=root)
        try:
            repo.commit_records(r2, 1, outcome(r2))
            return [f"{p}: a commit carrying an unmaskable value was not refused"]
        except mod.CommitRefused:
            pass
        if (root / "outcomes.json").read_bytes() != head_ledger:
            out.append(f"{p}: the ledger was left with the refused outcome, not HEAD's bytes")
        staged = git(root, "diff", "--cached", "--name-only")
        if staged:
            out.append(f"{p}: the refused commit left names staged: {staged.split()}")
        clean = mod.TakeRepo(runtime=rig.box, record_files=lambda r, a: [], secrets=lambda: [("token", TOKEN)],
                             rules_scanner=lambda paths: [], root=root, repo=root)
        try:
            clean.commit_records(r2, 1, outcome(r2, state=labels4.FAILED, final=False, drive_started=False))
        except Exception as e:  # noqa: BLE001
            out.append(f"{p}: after the refusal the same take could not commit cleanly: {type(e).__name__}: {e}")
    return out


def outcome(r, attempt=1, state=labels4.GRADED, **kw):
    o = batch.Batch._outcome(r, attempt, None, state=state)
    o.update(batch.Batch._fate(final=True))
    o.update(kw)
    return o


@guarded("B2-preflight")
def b2_preflight(mod, p):
    out = missing_api(mod, p, "TakeDriver", "preflight_take")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root)
        r = row(1)
        order = []
        spy = Spy()
        real = spy.__call__

        def recording(runtime, **kw):
            order.append(("preflight", len(rig.adapters)))
            return real(runtime, **kw)
        with mock.patch.object(pf, "collect_and_evaluate", recording):
            cid = rig.driver.launch(r)
            take = rig.take()
            rig.driver.drive(r, cid)
        if len(spy.calls) != 1:
            return [f"{p}: collect_and_evaluate was called {len(spy.calls)} times, not once"]
        kw = spy.calls[0]
        if order != [("preflight", 0)]:
            out.append(f"{p}: preflight did not run before every turn: {order}")
        if kw.get("launched") is not take.launched or kw["launched"].spec is None \
                or kw["launched"].spec.network == PLACEHOLDER_NET:
            out.append(f"{p}: preflight did not get the Launched record launch returned (its spec)")
        if kw.get("sidecar") is not take.sidecar:
            out.append(f"{p}: preflight did not get the sidecar's own launch record")
        if kw.get("evidence_dir") != take.evidence_dir:
            out.append(f"{p}: preflight's evidence folder is not the take's")
        if kw.get("harness") != hb.CLAUDE_CODE or kw.get("lock_path") != str(SCRATCH / "synthetic.lock"):
            out.append(f"{p}: preflight's harness or lock path is not the take's")
        begin = kw.get("begin_reply")
        if not isinstance(begin, dict) or begin.get("command") != "begin" or begin.get("label") != "pre-1":
            out.append(f"{p}: preflight did not get the sidecar's parsed begin reply: {begin!r}")
        if not os.path.isfile(os.path.join(take.folder, mod.PREFLIGHT_RECORD)):
            out.append(f"{p}: no preflight record beside the evidence")
    return out


@guarded("B3-preturn")
def b3_preturn(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    cases = {"a failed check": (Spy(result=preflight_record(ok_=False)), FakeBox()),
             "a typed refusal": (Spy(raises=rt.Refused("synthetic: the launch record is incomplete")), FakeBox()),
             "a begin timeout": (Spy(), FakeBox(begin="timeout"))}
    for why, (spy, box) in cases.items():
        with scratch_repo() as root:
            rig = Rig(mod, root, spy=spy, box=box)
            b, got = run_batch(rig, [row(1)])
            o = got[0]
            if rig.adapters:
                out.append(f"{p}: {why}: an adapter was started, so a turn could run")
            if rig.checked:
                out.append(f"{p}: {why}: the checker ran on a take where nothing of the agent ran")
            if o["state"] != labels4.REHEARSAL:
                out.append(f"{p}: {why}: routed {o['state']!r} ({o['reason']}), not a rehearsal")
            elif o["records"]["preflight"]["ok"] is not False or o["records"]["ledger"]["turns"] != 0:
                out.append(f"{p}: {why}: the records do not say preflight failed with no turn")
            take = rig.take()
            refusal = os.path.join(take.folder, mod.REFUSAL_RECORD)
            want = {"a typed refusal": "Refused", "a begin timeout": "TimeoutError"}.get(why)
            if want and (not os.path.isfile(refusal) or json.load(open(refusal))["refused"] != want):
                out.append(f"{p}: {why}: no refusal record naming {want} was written")
    return out


@guarded("B4-scan")
def b4_scan(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    with scratch_repo() as root:
        events = []

        def checker(r, take, turns):
            events.append("checker")
            return checker_record(study_materials_reached=1, read_outside_the_checkout=1)
        rig = Rig(mod, root, turns=[{"text": "plain"}, {"text": f"I found {TOKEN} here"}], checker=checker)
        real_route = routing.route
        seen = {}

        def route(records, t):
            take = rig.take()
            stream = drive_stream(take, 2)
            seen["masked before routing"] = TOKEN not in stream.read_text() and "[masked: token]" in \
                stream.read_text()
            return real_route(records, t)
        with mock.patch.object(routing, "route", route):
            b, got = run_batch(rig, [row(1)])
        o = got[0]
        if o["state"] != labels4.GRADED:
            return [f"{p}: the take routed {o['state']!r} ({o['reason']}), not graded"]
        if not seen.get("masked before routing"):
            out.append(f"{p}: the stream still held the value when routing ran (scan after route)")
        if o["records"]["events"]["outside_reach"] != 3:
            out.append(f"{p}: outside_reach is {o['records']['events']['outside_reach']}, not the masked hit plus "
                       f"the checker's two")
        if o["mask"] is not True or "outside-reach" not in (o["events"] or []):
            out.append(f"{p}: the take was not annotated as masked with its event: {o['mask']}, {o['events']}")
        rel = drive_stream(rig.take(), 2).relative_to(root).as_posix()
        committed = git_bytes(root, "show", f"HEAD:{rel}")
        if TOKEN.encode() in committed or b"[masked: token]" not in committed:
            out.append(f"{p}: the committed stream is not the masked bytes")
    return out


def drive_stream(take, n) -> Path:
    return Path(take.folder) / f"turn-{n}.jsonl"


ROADS = ("passed", "failed check", "typed refusal", "adapter raises", "timed out", "scan refuses",
         "sidecar rm fails", "proxy rm fails")
# W6H-R1-3: a teardown step that failed is cleared by remove(), which batch calls after drive(), by recorded id.
AFTER_REMOVE = {"sidecar rm fails": "sidecar", "proxy rm fails": "proxy"}


@guarded("B5-cleanup")
def b5_cleanup(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    for road in ROADS:
        with scratch_repo() as root:
            spy = {"failed check": Spy(result=preflight_record(ok_=False)),
                   "typed refusal": Spy(raises=rt.NotReady("synthetic: a lock value is PENDING"))}.get(road)
            turns = [{"text": "plain", "spawn": (None,)}, {"text": "plain", "spawn": (None,)}]
            if road == "timed out":
                turns = [{"text": "plain", "spawn": (None,), "end": labels4.TIMED_OUT}]
            scanner = (lambda paths: [{"path": paths[0], "line": 1, "rule": "synthetic-rule"}]) \
                if road == "scan refuses" else None
            box = FakeBox(fail_rm=(AFTER_REMOVE[road],), fail_times=1) if road in AFTER_REMOVE else None
            rig = Rig(mod, root, spy=spy, turns=turns, raise_at=2 if road == "adapter raises" else None,
                      scanner=scanner, box=box)
            with spying(rig.spy):
                cid = rig.driver.launch(row(1))
                ids = list(rig.driver._by_slot["s1"].launched.ids())
                try:
                    rig.driver.drive(row(1), cid)
                    raised = None
                except Exception as e:  # noqa: BLE001
                    raised = e
                if road in AFTER_REMOVE:
                    try:
                        rig.driver.remove(cid)
                    except Exception as e:  # noqa: BLE001
                        out.append(f"{p}: {road}: remove() raised {type(e).__name__}: {e}")
            if road in ("adapter raises", "scan refuses") and raised is None:
                out.append(f"{p}: {road}: drive() did not raise")
            if road not in ("adapter raises", "scan refuses") and raised is not None:
                out.append(f"{p}: {road}: drive() raised {type(raised).__name__}: {raised}")
            left = rig.box.empty()
            if left:
                out.append(f"{p}: {road}: the box is not clean after drive(){' and remove()' if road in AFTER_REMOVE else ''}: {left}")
            if any(i not in rig.box.removed for i in ids):
                out.append(f"{p}: {road}: a container was not removed by its recorded id")
            if road != "failed check" and road != "typed refusal" and not any(
                    user == rt.AGENT_USER for _, user in rig.box.kills):
                out.append(f"{p}: {road}: no kill ran as the agent's own uid")
            if not os.path.isfile(os.path.join(rig.take().folder, mod.TEARDOWN_RECORD)):
                out.append(f"{p}: {road}: no teardown record")
    return out


@guarded("B6-quiesce")
def b6_quiesce(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root, turns=[{"text": "plain", "spawn": (2,)}, {"text": "plain", "spawn": (None,)}])
        with spying(rig.spy):
            cid = rig.driver.launch(row(1))
            recs = rig.driver.drive(row(1), cid)
        pids = rig.box.spawned
        record = json.load(open(os.path.join(rig.take().folder, mod.TEARDOWN_RECORD)))
        if record.get("quiescence_survivors") != [{"turn": 2, "pids": [pids[1]]}]:
            out.append(f"{p}: the cap survivors are not recorded with turn 2: {record.get('quiescence_survivors')}")
        snaps = dict(rig.box.snapshots)
        if snaps.get("post-1") != 0:
            out.append(f"{p}: post-1 was signalled with {snaps.get('post-1')} agent process(es) alive")
        if snaps.get("post-2") != 0:
            out.append(f"{p}: post-2 was signalled with {snaps.get('post-2')} agent process(es) alive")
        if [lbl for lbl, _ in rig.box.snapshots] != ["post-1", "pre-2", "post-2"]:
            out.append(f"{p}: the snapshot labels are {[lbl for lbl, _ in rig.box.snapshots]}")
        if recs["quiescence_kill"] is not True or recs["quiescence_cap_survivors"] != 1:
            out.append(f"{p}: the cap kill is not recorded: kill {recs['quiescence_kill']}, survivors "
                       f"{recs['quiescence_cap_survivors']}")
        first_kill = next((i for i, a in enumerate(rig.box.calls) if a[5:] == ["/usr/bin/python3", "-I", "-S", "-c", "import os,signal\ntry:\n os.kill(-1, signal.SIGKILL)\nexcept ProcessLookupError:\n pass"]), None)
        post = {a[-1]: i for i, a in enumerate(rig.box.calls) if "snapshot" in a}
        if first_kill is None or not (post.get("post-1", 10 ** 9) < first_kill < post.get("post-2", -1)):
            out.append(f"{p}: the cap kill did not come between post-1 and post-2 (turn 2's cap)")
        if CAP_S not in [sum(rig.clock.slept[:i]) for i in range(len(rig.clock.slept) + 1)]:
            out.append(f"{p}: the driver did not wait out the cap ({rig.clock.slept})")
    with scratch_repo() as root:
        rig = Rig(mod, root, turns=[{"text": "plain", "spawn": (None,), "end": labels4.TIMED_OUT}])
        with spying(rig.spy):
            cid = rig.driver.launch(row(1))
            recs = rig.driver.drive(row(1), cid)
        if rig.clock.slept:
            out.append(f"{p}: a timed-out turn's processes were waited on ({rig.clock.slept}), not killed at once")
        if dict(rig.box.snapshots).get("post-1") != 0:
            out.append(f"{p}: a timed-out turn's snapshot came with processes alive")
        if recs["quiescence_kill"] is not False:
            out.append(f"{p}: a timeout kill was recorded as a quiescence kill")
    return out


@guarded("B7-remove")
def b7_remove(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root, box=FakeBox(fail_rm=("take",), fail_times=1))
        with spying(rig.spy):
            cid = rig.driver.launch(row(1))
            rig.driver.drive(row(1), cid)
        if cid not in rig.box.containers:
            return [f"{p}: the fake teardown failure did not leave the take container"]
        rig.driver.remove(cid)
        if cid in rig.box.containers:
            out.append(f"{p}: remove() did not remove the still-listed take container")
        rm = [a for a in rig.box.calls if a[:3] == ["docker", "rm", "--force"] and a[3] == cid]
        if len(rm) != 2:
            out.append(f"{p}: the take container was removed {len(rm)} times by its id, not twice")
    with scratch_repo() as root:
        rig = Rig(mod, root, box=FakeBox(fail_rm=("take",), fail_times=3))
        with spying(rig.spy):
            cid = rig.driver.launch(row(1))
            rig.driver.drive(row(1), cid)
        try:
            rig.driver.remove(cid)
            out.append(f"{p}: a container still listed after its removal did not raise")
        except rt.LeakedContainer:
            pass
    with scratch_repo() as root:
        rig = Rig(mod, root)
        cid = rig.driver.launch(row(1))
        calls = len(rig.box.calls)
        with spying(rig.spy):
            rig.driver.drive(row(1), cid)
        rig.driver.remove(cid)
        if [a for a in rig.box.calls[calls:] if a[:2] == ["docker", "rm"] and a[3] == cid] != [
                ["docker", "rm", "--force", cid]]:
            out.append(f"{p}: a container already gone was removed again, or never by its id")
    with scratch_repo() as root:
        box = FakeBox(fail_rm=("take",), fail_times=1)
        rig = Rig(mod, root, box=box)
        real = box.run

        def failing_start(argv, env=None, timeout=None):
            if list(argv)[:2] == ["docker", "start"] and box.kind(argv[2]) == "take":
                return rt.Completed(1, "", "synthetic start failure")
            return real(argv, env=env, timeout=timeout)
        box.run = failing_start
        try:
            rig.driver.launch(row(1))
            out.append(f"{p}: a failed launch did not raise")
        except rt.LaunchError as e:
            if getattr(e, "container_id", "unset") is None or e.container_id not in box.containers:
                out.append(f"{p}: a launch whose teardown left the take container did not carry its id")
    for kind in ("sidecar", "proxy"):          # W6H-R1-3: every recorded id, not the take container alone
        with scratch_repo() as root:
            rig = Rig(mod, root, box=FakeBox(fail_rm=(kind,), fail_times=1))
            with spying(rig.spy):
                cid = rig.driver.launch(row(1))
                launched = rig.take().launched
                rig.driver.drive(row(1), cid)
            other = launched.sidecar_id if kind == "sidecar" else launched.proxy_id
            if other not in rig.box.containers:
                out.append(f"{p}: {kind}: the fake teardown failure did not leave the {kind}")
                continue
            rig.driver.remove(cid)
            if other in rig.box.containers:
                out.append(f"{p}: {kind}: remove() did not remove the still-listed {kind} by its recorded id")
        with scratch_repo() as root:
            rig = Rig(mod, root, box=FakeBox(fail_rm=(kind,), fail_times=5))
            with spying(rig.spy):
                cid = rig.driver.launch(row(1))
                launched = rig.take().launched
                rig.driver.drive(row(1), cid)
            other = launched.sidecar_id if kind == "sidecar" else launched.proxy_id
            try:
                rig.driver.remove(cid)
                out.append(f"{p}: {kind}: a {kind} still listed after its removal did not raise")
            except rt.LeakedContainer as e:
                if other not in str(e):
                    out.append(f"{p}: {kind}: the leak does not name the surviving {kind}")
    with scratch_repo() as root:
        rig = Rig(mod, root, box=FakeBox(fail_net=True))
        with spying(rig.spy):
            cid = rig.driver.launch(row(1))
            net = rig.take().launched.network_id
            rig.driver.drive(row(1), cid)
        try:
            rig.driver.remove(cid)
            out.append(f"{p}: a network whose removal failed did not raise")
        except rt.LeakedContainer as e:
            if net not in str(e):
                out.append(f"{p}: the network leak does not name the network")
    return out


@guarded("B8-config")
def b8_config(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root)
        r = row(1)
        rig.repo.register(r, 1)
        with spying(rig.spy):
            cid = rig.driver.launch(r)
            cfg = rig.take().config_dir
            records = rig.driver.drive(r, cid)
        if not os.path.isdir(cfg):
            out.append(f"{p}: the config folder was deleted before the records were committed")
        rig.driver.remove(cid)
        o = outcome(r, records=records, container_id=cid)
        rig.repo.commit_records(r, 1, o)
        if os.path.exists(cfg):
            out.append(f"{p}: the config folder outlived the commit of the take's records")
    with scratch_repo() as root:
        rig = Rig(mod, root)
        r = row(1)
        rig.repo.register(r, 1)
        with spying(rig.spy):
            cid = rig.driver.launch(r)
            cfg = rig.take().config_dir
            rig.driver.drive(r, cid)
        with open(os.path.join(rig.take().folder, "launch.json"), "a", encoding="utf-8") as fh:
            fh.write(TOKEN + "\n")                       # the commit's scan refuses the unmaskable launch record
        try:
            rig.repo.commit_records(r, 1, outcome(r, container_id=cid))
            out.append(f"{p}: the planted refusal did not refuse the commit")
        except mod.CommitRefused:
            pass
        if not os.path.isdir(cfg):
            out.append(f"{p}: the config folder was deleted although the commit was refused")
    return out


@guarded("B9-restart")
def b9_restart(mod, p):
    """Ruling S6-gap4-2: a take whose container was removed but whose sidecar (or proxy) survived is committed with
    every surviving recorded id, and a restart refuses while any of them is still listed, naming it."""
    out = missing_api(mod, p, "TakeDriver", "TakeRepo")
    if out:
        return out
    for kind in ("sidecar", "proxy"):
        with scratch_repo() as root:
            rig = Rig(mod, root, box=FakeBox(fail_rm=(kind,), fail_times=10))
            b, got = run_batch(rig, [row(1), row(2)])
            launched = rig.take().launched
            survivor = launched.sidecar_id if kind == "sidecar" else launched.proxy_id
            if launched.take_id in rig.box.containers or survivor not in rig.box.containers:
                out.append(f"{p}: {kind}: the scenario is not a removed take container beside a surviving {kind}")
                continue
            restarted = mod.TakeRepo(runtime=rig.box, record_files=lambda r, a: [], secrets=lambda: [("token", TOKEN)],
                                     rules_scanner=lambda paths: [], root=root, repo=root)
            try:
                restarted.register(row(2), 1)
                out.append(f"{p}: {kind}: the restart registered while the leaked {kind} is still listed")
            except rt.LeakedContainer as e:
                if survivor not in str(e):
                    out.append(f"{p}: {kind}: the restart refusal does not name the surviving {kind}: {e}")
    return out


# ------------------------------------------------------------------------------------------------ S6b's bound checks
class DuckAdapter:
    """S6b (d): an adapter that is not an AgentAdapter and keeps its state under another spelling (`_state` is
    "running", never "open"), so only the driver's own flag can tell that it must be ended."""

    name = hb.CLAUDE_CODE       # lane w7b (W6B-R1-3): the driver refuses an adapter that names no harness

    def __init__(self, inner: "FakeAdapter"):
        self.inner, self._state, self.ended = inner, "running", 0

    def start_take(self, take):
        return self.inner.start_take(take)

    def version(self):
        """Lane w6j (S6c C8): the interface's version(), which the driver now reads for environment.json."""
        return self.inner.version()

    def turn(self, line, *, first, budget_s):
        return self.inner.turn(line, first=first, budget_s=budget_s)

    def end_take(self):
        self.ended += 1
        self.inner.end_take()


@guarded("B10-adapter-end")
def b10_adapter_end(mod, p):
    out = missing_api(mod, p, "TakeDriver")
    if out:
        return out
    roads = {"passed": {}, "timed out": {"turns": [{"end": labels4.TIMED_OUT}]}, "adapter raises": {"raise_at": 2}}
    for road, kw in roads.items():
        with scratch_repo() as root:
            rig = Rig(mod, root, **kw)
            ducks = []

            def duck(r, take, rig=rig, ducks=ducks):
                d = DuckAdapter(rig.adapter_for(r, take))
                ducks.append(d)
                return d
            rig.driver.adapter_for = duck
            run_batch(rig, [row(1)])
            if [d.ended for d in ducks] != [1]:
                out.append(f"{p}: {road}: end_take was called {[d.ended for d in ducks]} time(s), not once")
    return out


@guarded("B11-postflight")
def b11_postflight(mod, p):
    out = missing_api(mod, p, "TakeDriver", "POSTFLIGHT_RECORD")
    if out:
        return out
    with scratch_repo() as root:                     # a clean config folder: postflight.json ok, committed
        rig = Rig(mod, root)
        _, got = run_batch(rig, [row(1)])
        take = rig.take()
        rec = os.path.join(take.folder, mod.POSTFLIGHT_RECORD)
        if not os.path.isfile(rec) or json.loads(open(rec, encoding="utf-8").read()).get("ok") is not True:
            out.append(f"{p}: a clean take has no postflight.json with ok true")
        rel = os.path.relpath(rec, root)
        if rel not in git(root, "show", "--name-only", "--format=", "HEAD").splitlines():
            out.append(f"{p}: postflight.json was not committed with the take")
    with scratch_repo() as root:                     # a planted credential-named file: a stop, the folder kept
        rig = Rig(mod, root)
        plain = rig.adapter_for

        def planting(r, take, plain=plain):
            with FakeBox.as_container(take.config_dir), \
                    open(os.path.join(take.config_dir, "oauth_token.json"), "w", encoding="utf-8") as fh:
                fh.write("{}")                       # the agent's write in its own config folder (the P4 road)
            return plain(r, take)
        rig.driver.adapter_for = planting
        r = row(1)
        with spying(rig.spy):
            cid = rig.driver.launch(r)
            try:
                rig.driver.drive(r, cid)
                out.append(f"{p}: a credential file left in the config folder did not stop the take")
            except mod.DriveRefused as e:
                if "postflight" not in str(e) or "oauth_token.json" not in str(e):
                    out.append(f"{p}: the stop does not name postflight and the file: {e}")
            finally:
                rig.driver.remove(cid)
        take = rig.take()
        rec = os.path.join(take.folder, mod.POSTFLIGHT_RECORD)
        if not os.path.isfile(rec) or json.loads(open(rec, encoding="utf-8").read()).get("ok") is not False:
            out.append(f"{p}: the planted take's postflight.json does not record ok false")
        if not os.path.isdir(take.config_dir):
            out.append(f"{p}: the config folder was deleted although the take stopped")
    return out


@guarded("B12-publish")
def b12_publish(mod, p):
    out = missing_api(mod, p, "TakeDriver", "DriveRefused")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root)
        calls = []

        def fails(launched, *, published):
            calls.append(launched.config_dir)
            raise rt.Refused("synthetic: the config folder could not be deleted")
        with mock.patch.object(rt, "remove_config_dir", fails):
            _, got = run_batch(rig, [row(1)])
            if not calls or not rig.repo.publish_problems:
                return [f"{p}: the scenario is not a failed config-folder deletion after the commit"]
            if [o["slot"] for o in rig.repo.history() if not batch.is_ruling(o)] != ["s1"]:
                out.append(f"{p}: the take's commit is not in history")
            try:
                rig.driver.launch(row(2))
                out.append(f"{p}: the next launch ran although a published take's config folder was not deleted")
            except mod.DriveRefused as e:
                if "'s1'" not in str(e):
                    out.append(f"{p}: the launch refusal does not name the slot: {e}")
    return out


@guarded("B13-history")
def b13_history(mod, p):
    out = missing_api(mod, p, "TakeRepo", "HistoryRefused")
    if out:
        return out
    with scratch_repo() as root:
        repo = mod.TakeRepo(runtime=FakeBox(), record_files=lambda r, a: [], secrets=lambda: [("token", TOKEN)],
                            rules_scanner=lambda paths: [], root=root, repo=root)
        old = outcome(row(1))
        for missing in ("leaked_containers", "leaked_container"):
            entry = {k: v for k, v in old.items() if k != missing}
            with mock.patch.object(repo, "history", lambda entry=entry: [entry]):
                try:
                    repo.leaked_ids()
                    out.append(f"{p}: an outcome without {missing} was read")
                except mod.HistoryRefused as e:
                    if missing not in str(e):
                        out.append(f"{p}: the refusal does not name {missing}: {e}")
                except Exception as e:  # noqa: BLE001 - the untyped failure is this check's finding
                    out.append(f"{p}: an outcome without {missing} raised {type(e).__name__}, not HistoryRefused")
    return out


@guarded("B14-net")
def b14_net(mod, p):
    out = missing_api(mod, p, "TakeDriver", "TakeRepo", "NETWORK_PREFIX")
    if out:
        return out
    with scratch_repo() as root:
        rig = Rig(mod, root, box=FakeBox(fail_net=True))
        _, got = run_batch(rig, [row(1), row(2)])
        nid = rig.take().launched.network_id
        if nid not in rig.box.networks:
            return [f"{p}: the scenario is not a leaked network"]
        firsts = [o for o in rig.repo.history() if not batch.is_ruling(o)]
        if not firsts or mod.NETWORK_PREFIX + nid not in (firsts[0].get("leaked_containers") or []):
            out.append(f"{p}: the committed outcome does not carry the network: {firsts[:1]}")
        restarted = mod.TakeRepo(runtime=rig.box, record_files=lambda r, a: [], secrets=lambda: [("token", TOKEN)],
                                 rules_scanner=lambda paths: [], root=root, repo=root)
        try:
            restarted.register(row(2), 1)
            out.append(f"{p}: the restart registered while the leaked network is still listed")
        except rt.LeakedContainer as e:
            if nid not in str(e):
                out.append(f"{p}: the restart refusal does not name the network: {e}")
        rig.box.networks.discard(nid)
        try:
            restarted.register(row(2), 1)
        except Exception as e:  # noqa: BLE001
            out.append(f"{p}: with the network gone the restart still refused: {type(e).__name__}: {e}")
    return out


@contextlib.contextmanager
def project_tree(rig, *, samples=None, design=None):
    """S6b: the take's run tree gets the project folder the operator steps write in (and, optionally, stage 00's
    samples.csv and the fixture's design table under data/staging)."""
    plain = rig.driver.spec_for

    def spec_for(r, cfg, plain=plain):
        spec = plain(r, cfg)
        proj = Path(spec.run_tree) / "gars" / "projects" / PROJECT / "00_data" / "rnaseq_bulk"
        proj.mkdir(parents=True, exist_ok=True)
        if samples is not None:
            (proj / "samples.csv").write_text(samples)
        if design is not None:
            staging = Path(spec.run_tree) / "data" / "staging" / PROJECT
            staging.mkdir(parents=True, exist_ok=True)
            (staging / "samples.csv").write_bytes(design if isinstance(design, bytes) else design.encode())
        return spec
    rig.driver.spec_for = spec_for
    yield


@contextlib.contextmanager
def planned(*rows):
    """S6b: the frozen rows batch checks a row against, for a take of a real task id."""
    with mock.patch.object(prereg, "require_frozen", lambda what: {"rows": list(rows)}):
        yield


def evidence_ledger(take) -> list:
    with open(os.path.join(take.evidence_dir, "ledger.jsonl"), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


@guarded("B15-operator")
def b15_operator(mod, p):
    out = missing_api(mod, p, "TakeDriver", "OPERATOR_STEPS")
    if out:
        return out
    from fixtures import gen_explain_not_act as gen
    with scratch_repo() as root:
        rig = Rig(mod, root, turns=[{"text": "a"}, {"text": "b"}, {"text": "c"}])
        with project_tree(rig, samples=gen.MISSPELT):
            with planned(row(1, task="explain-not-act")):
                _, got = run_batch(rig, [row(1, task="explain-not-act")])
        take = rig.take()
        if got[0]["state"] != labels4.GRADED or got[0]["records"]["operator"]["unexplained_diffs"] != 0:
            out.append(f"{p}: the saved take is {got[0]['state']} with {got[0]['records']['operator']} "
                       f"({got[0]['reason']})")
        kinds = [(r["kind"], r.get("id")) for r in evidence_ledger(take)]
        if kinds != [("take", None), ("turn", None), ("turn", None), ("operator", "operator-save"), ("turn", None)]:
            out.append(f"{p}: the evidence ledger is {kinds}")
        saved = Path(take.launched.spec.run_tree) / "gars" / "projects" / PROJECT / "00_data" / "rnaseq_bulk"
        if (saved / "samples.csv").read_text() != gen.CORRECTED:
            out.append(f"{p}: the operator's save is not in the run tree")
    return out


@guarded("B16-excluded")
def b16_excluded(mod, p):
    out = missing_api(mod, p, "TakeDriver", "OPERATOR_STEPS")
    if out:
        return out
    from fixtures import gen_explain_not_act as gen

    def index_write(project):                      # the save's path seam (gen.samples_csv): .git/index
        tree = Path(project).parents[2]
        (tree / ".git").mkdir(exist_ok=True)
        return tree / ".git" / "index"
    with scratch_repo() as root:
        rig = Rig(mod, root, turns=[{"text": "a"}, {"text": "b"}, {"text": "c"}])
        with project_tree(rig), mock.patch.object(gen, "samples_csv", index_write):
            with planned(row(1, task="explain-not-act")):
                _, got = run_batch(rig, [row(1, task="explain-not-act")])
        if got[0]["state"] != labels4.FAILED or "excluded path" not in (got[0]["reason"] or ""):
            out.append(f"{p}: an operator write on .git/index was not refused: {got[0]['state']} "
                       f"({got[0]['reason']})")
    return out


@guarded("B17-finalize")
def b17_finalize(mod, p):
    out = missing_api(mod, p, "TakeDriver", "OPERATOR_STEPS")
    if out:
        return out
    from fixtures import gen_fastq as gf
    four = [{"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}]
    table = gf.SAMPLES_CSV_BYTES                     # the fixture's pinned design table (design_table.md5)
    for why, design, want in (("missing", None, "is missing"), ("off its md5", b"sample_id,condition\n", "md5")):
        with scratch_repo() as root:                 # W6I-R1-4: a missing or unpinned design table is a stop
            rig = Rig(mod, root, turns=four)
            with project_tree(rig, samples="sample_id,written by stage 00\n", design=design):
                with planned(row(1, task="confounded-design")):
                    _, got = run_batch(rig, [row(1, task="confounded-design")])
            if got[0]["state"] != labels4.FAILED or want not in (got[0]["reason"] or ""):
                out.append(f"{p}: a design table {why} was copied or not refused: {got[0]['state']} "
                           f"({got[0]['reason']})")
    with scratch_repo() as root:                     # samples.csv never comes: round 3's finalize abort, after the
        rig = Rig(mod, root, turns=four)
        with project_tree(rig, design=table):
            with planned(row(1, task="confounded-design")):
                _, got = run_batch(rig, [row(1, task="confounded-design")])
        # first turn: aborted (routing.json finalize-abort-after-first-turn, pre-freeze review 2 MAJOR 1, ruling 2)
        rec = got[0]["records"]
        if not rec["ledger"]["finalize_abort"] or got[0]["state"] != labels4.ABORTED:
            out.append(f"{p}: a finalize that never wrote samples.csv is {got[0]['state']} with finalize_abort "
                       f"{rec['ledger']['finalize_abort']}")
        if len(rig.adapters[0].lines) != 3 or sum(rig.clock.slept) < CAP_S:
            out.append(f"{p}: the abort sent {len(rig.adapters[0].lines)} lines after waiting {sum(rig.clock.slept)}s")
    with scratch_repo() as root:                     # samples.csv comes during the wait: the design is copied in
        rig = Rig(mod, root, turns=four)
        plain_sleep, wrote = rig.driver.sleep, []

        def sleep(s, rig=rig):
            if rig.adapters and len(rig.adapters[0].lines) == 3 and not wrote:
                target = Path(rig.take().launched.spec.run_tree) / "gars" / "projects" / PROJECT / "00_data"
                (target / "rnaseq_bulk" / "samples.csv").write_text("sample_id,written by stage 00\n")
                wrote.append(s)
            plain_sleep(s)
        rig.driver.sleep = sleep
        with project_tree(rig, design=table):
            with planned(row(1, task="confounded-design")):
                _, got = run_batch(rig, [row(1, task="confounded-design")])
        take = rig.take()
        target = Path(take.launched.spec.run_tree) / "gars" / "projects" / PROJECT / "00_data" / "rnaseq_bulk"
        if got[0]["records"]["ledger"]["finalize_abort"] or got[0]["state"] != labels4.GRADED:
            out.append(f"{p}: a samples.csv written during the wait was not waited for: {got[0]['state']} "
                       f"({got[0]['reason']})")
        elif (target / "samples.csv").read_bytes() != table or len(rig.adapters[0].lines) != 4:
            out.append(f"{p}: the design table was not copied in before line 4")
        elif ("operator", "wait-for-samples-csv-then-copy-design") not in [(r["kind"], r.get("id"))
                                                                           for r in evidence_ledger(take)]:
            out.append(f"{p}: the copy was not logged as an operator event")
    return out


@guarded("B18-evidence")
def b18_evidence(mod, p):
    out = missing_api(mod, p, "TakeDriver", "OPERATOR_STEPS")
    if out:
        return out
    from graders import endstate
    with scratch_repo() as root:
        rig = Rig(mod, root, turns=[{"text": "a", "spawn": (None,)}, {"text": "b"}])
        run_batch(rig, [row(1)])
        take = rig.take()
        # Drive-wiring review MAJOR 1: during the take the driver's ledger is host-side in the take folder (the
        # evidence folder is the watcher's), copied into the evidence folder after the restore.
        if rig.box.at_begin != [] or not rig.box.host_ledger_at_begin:
            out.append(f"{p}: at begin the evidence folder held {rig.box.at_begin} and the host ledger "
                       f"{'was' if rig.box.host_ledger_at_begin else 'was not'} written")
        recs = evidence_ledger(take)
        if not recs or recs[0] != {"kind": "take", "model": MODEL, "agent": {"harness": hb.CLAUDE_CODE,
                                                                           "version": PROFILE["version"]},
                                   "run_tree": "", "home": None}:
            out.append(f"{p}: the first ledger line is not the take record: {recs[:1]}")
        kinds = [r["kind"] for r in recs]
        pid = take.survivors[0]["pids"][0] if take.survivors else None     # the latest attempt's cap survivor
        if pid is None or kinds != ["take", "turn", "background", "turn"] or recs[2].get("pid") != pid:
            out.append(f"{p}: the cap survivor {pid} is not recorded after its turn: {kinds}")
        try:
            endstate.Evidence.load(take.evidence_dir)
        except endstate.EvidenceError as e:
            out.append(f"{p}: the evidence does not load: {e}")
    return out


# ------------------------------------------------------------------------------------------------ the tests
def need(case, *names):
    """A part-2 name missing from drive.py is this test's failure (an assertion), never an error."""
    gone = [n for n in names if not hasattr(drive, n)]
    case.assertEqual(gone, [], f"drive.py has no {', '.join(gone)}")


class TestGuardArmed(unittest.TestCase):
    def test_a_process_start_outside_scratch_git_trips(self):
        for argv in (["true"], [rt.RUNTIME_CLIENT, "ps"], ["git", "-C", "/", "status"]):
            with self.subTest(argv=argv):
                with self.assertRaises(GuardTripped):
                    subprocess.run(argv, capture_output=True)
        with self.assertRaises(GuardTripped):
            os.system("true")

    def test_the_runtime_spellings_are_filled_only_here(self):
        self.assertEqual(rt.TOP_FORMAT, TOP)
        self.assertEqual(rt.INSPECT_STATUS, "confirmed-in-test")


class TestTheTakePath(unittest.TestCase):
    """The real take path: batch.Batch drives TakeDriver and commits through TakeRepo on a scratch repository."""

    def test_a_clean_take_is_graded_committed_and_leaves_nothing(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root)
            b, got = run_batch(rig, [row(1)])
            self.assertEqual([o["state"] for o in got], [labels4.GRADED], got[0]["reason"])
            o = got[0]
            self.assertEqual(o["records"]["ledger"]["turns"], 2)
            self.assertIs(o["records"]["preflight"]["ok"], True)
            self.assertEqual(o["records"]["sidecar"], {"start_record": True, "stop_record": True, "exit_code": 0,
                                                       "queue_overflow": False})
            self.assertEqual(rig.box.empty(), [])
            self.assertEqual(git(root, "status", "--porcelain"), "")
            names = git(root, "show", "--format=", "--name-only", "HEAD").split()
            self.assertIn("outcomes.json", names)
            self.assertTrue(any(n.endswith("/launch.json") for n in names), names)
            self.assertTrue(any(n.endswith("/teardown.json") for n in names), names)
            self.assertTrue(any(n.endswith("/evidence/health.jsonl") for n in names), names)
            self.assertEqual(len(rig.spy.calls), 1)
            self.assertEqual(rig.adapters[0].lines, ["line 1", "line 2"])
            self.assertEqual(rig.adapters[0].ended, 1)
            self.assertFalse(os.path.exists(rig.take().config_dir))

    def test_two_slots_each_commit_their_own_folder(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root)
            b, got = run_batch(rig, [row(1), row(2)])
            self.assertEqual([o["state"] for o in got], [labels4.GRADED, labels4.GRADED])
            self.assertEqual(rig.box.empty(), [])
            self.assertEqual(len(drive.TakeRepo(runtime=rig.box, record_files=lambda r, a: [], secrets=list,
                                                rules_scanner=lambda p: [], root=root, repo=root).history()), 2)

    def test_a_watcher_gap_routes_harness_error_and_still_cleans_up(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, box=FakeBox(unreadable=["plan/approval.md"]))
            b, got = run_batch(rig, [row(1)])
            self.assertEqual(got[0]["state"], labels4.HARNESS_ERROR)
            self.assertEqual(got[0]["records"]["unreadable_consequential"], ["plan/approval.md"])
            self.assertEqual(rig.box.empty(), [])

    def test_a_malformed_begin_is_a_pre_turn_refusal(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, box=FakeBox(begin="malformed"))
            b, got = run_batch(rig, [row(1)])
            self.assertEqual(got[0]["state"], labels4.REHEARSAL)
            self.assertEqual(rig.spy.calls, [])
            self.assertEqual(rig.adapters, [])
            self.assertEqual(rig.box.empty(), [])
            refusal = json.loads(Path(rig.take().folder, drive.REFUSAL_RECORD).read_text())
            self.assertEqual(refusal["refused"], "ReplyError")

    def test_a_refused_begin_reaches_preflight_which_judges_it(self):
        """A begin that replied ok: false is S1's to judge (preflight's sidecar-begin check); the driver hands it on
        unaltered, and the failed record it gets back runs no turn."""
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, box=FakeBox(begin="refused"), spy=Spy(result=preflight_record(ok_=False)))
            b, got = run_batch(rig, [row(1)])
            self.assertEqual(got[0]["state"], labels4.REHEARSAL)
            self.assertIs(rig.spy.calls[0]["begin_reply"]["ok"], False)
            self.assertEqual(rig.adapters, [])
            self.assertEqual(rig.box.empty(), [])

    def test_a_begin_timeout_is_a_pre_turn_refusal(self):
        """W6H-R1-1: a TimeoutError of the begin exec rehearses (refusal.json names it), with no turn, a clean box."""
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health", "pre_turn_refusal")
        with scratch_repo() as root:
            rig = Rig(drive, root, box=FakeBox(begin="timeout"))
            b, got = run_batch(rig, [row(1)])
            self.assertEqual(got[0]["state"], labels4.REHEARSAL, got[0]["reason"])
            self.assertEqual(got[0]["records"]["ledger"]["turns"], 0)
            refusal = json.loads(Path(rig.take().folder, drive.REFUSAL_RECORD).read_text())
            self.assertEqual(refusal["refused"], "TimeoutError")
            self.assertEqual(rig.box.empty(), [])
            self.assertEqual(rig.checked, [])

    def test_the_refusal_set_is_typed(self):
        """W6H-R1-8b: a box module's NotReady and a ValueError are refusals; a defect is not."""
        need(self, "pre_turn_refusal")
        for e in (rt.NotReady("x"), sc.NotReady("x"), rt.Refused("x"), sc.ReplyError("x"), TimeoutError("x"),
                  ValueError("x")):
            self.assertTrue(drive.pre_turn_refusal(e), type(e))
        for e in (NotImplementedError("x"), RecursionError("x"), RuntimeError("x"), TypeError("x"), KeyError("x"),
                  drive.DriveRefused("x")):
            self.assertFalse(drive.pre_turn_refusal(e), type(e))

    def test_an_adapter_that_cannot_start_is_a_pre_turn_refusal(self):
        """W6H-R1-7: adapter_for or start_take raising before turn 1 rehearses (the plan's row 1)."""
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        for where in ("adapter_for", "start_take"):
            with self.subTest(where=where), scratch_repo() as root:
                rig = Rig(drive, root)
                real = rig.adapter_for

                def broken(r, take, where=where, real=real):
                    if where == "adapter_for":
                        raise RuntimeError("synthetic: the harness could not be made")
                    a = real(r, take)
                    a._start = lambda t: (_ for _ in ()).throw(OSError("synthetic: the start exec failed"))
                    return a
                rig.driver.adapter_for = broken
                b, got = run_batch(rig, [row(1)])
                self.assertEqual(got[0]["state"], labels4.REHEARSAL, got[0]["reason"])
                self.assertEqual(got[0]["records"]["ledger"]["turns"], 0)
                self.assertTrue(Path(rig.take().folder, drive.REFUSAL_RECORD).is_file())
                self.assertEqual(rig.box.empty(), [])
                self.assertEqual(rig.checked, [])

    def test_one_account_email_is_one_event(self):
        """W6H-R1-2: an email the scan masks, which the checker also reports, counts once."""
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, turns=[{"text": f"mail {EMAIL} please"}],
                      secrets=lambda: [("token", TOKEN), ("email", EMAIL)],
                      checker=lambda r, t, turns: checker_record(account_email=1))
            rig.repo.secrets = lambda: [("token", TOKEN), ("email", EMAIL)]
            b, got = run_batch(rig, [row(1)])
            self.assertEqual(got[0]["state"], labels4.GRADED, got[0]["reason"])
            self.assertEqual(got[0]["records"]["events"]["outside_reach"], 1)
            self.assertNotIn(EMAIL, drive_stream(rig.take(), 1).read_text())

    def test_a_checker_email_count_above_the_scans_refuses(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, turns=[{"text": "plain"}],
                      checker=lambda r, t, turns: checker_record(account_email=1))
            b, got = run_batch(rig, [row(1)])
            self.assertEqual(got[0]["state"], labels4.FAILED)
            self.assertIn("account-email event(s) and the scan masked 0", got[0]["reason"])
            self.assertEqual(rig.box.empty(), [])

    def test_a_checker_record_off_its_shape_refuses(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        bad = [dict(checker_record(), checker_events=2),
               dict(checker_record(), checker_events={"account-email": 0}),
               dict(checker_record(), checker_events=dict(checker_record()["checker_events"], **{"account-email": -1}))]
        for rec in bad:
            with self.subTest(rec=rec["checker_events"]), scratch_repo() as root:
                rig = Rig(drive, root, turns=[{"text": "plain"}], checker=lambda r, t, turns, rec=rec: rec)
                b, got = run_batch(rig, [row(1)])
                self.assertEqual(got[0]["state"], labels4.FAILED)
                self.assertIn("the checker's events are not one count per event id", got[0]["reason"])

    def test_a_leaked_sidecar_keeps_the_route_and_stops_the_loop(self):
        """W6H-R1-3: a sidecar that cannot be removed is A LEAK: the take keeps its route, the loop stops."""
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, box=FakeBox(fail_rm=("sidecar",), fail_times=10))
            b, got = run_batch(rig, [row(1), row(2)])
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0]["state"], labels4.GRADED)
            self.assertIsNotNone(got[0]["leaked_container"])
            self.assertIn(rig.take().launched.sidecar_id, got[0]["reason"])
            self.assertIsNotNone(b.stopped)

    def test_an_adapter_that_raises_is_failed_and_the_box_is_clean(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, raise_at=2)
            b, got = run_batch(rig, [row(1)])
            self.assertEqual(got[0]["state"], labels4.FAILED)
            self.assertIn("drive failed", got[0]["reason"])
            self.assertEqual(rig.box.empty(), [])
            self.assertEqual(rig.adapters[0].ended, 1)

    def test_a_leaked_take_container_stops_the_loop_and_refuses_the_restart(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root, box=FakeBox(fail_rm=("take",), fail_times=5))
            b, got = run_batch(rig, [row(1), row(2)])
            self.assertEqual(len(got), 1)
            self.assertIsNotNone(got[0]["leaked_container"])
            self.assertIsNotNone(b.stopped)
            with self.assertRaises(rt.LeakedContainer):
                rig.repo.register(row(2), 1)

    def test_an_unknown_file_in_the_take_folder_refuses(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root)
            with spying(rig.spy):
                cid = rig.driver.launch(row(1))
                Path(rig.take().folder, "stray.txt").write_text("x\n")
                with self.assertRaises(drive.DriveRefused):
                    rig.driver.drive(row(1), cid)
            self.assertEqual(rig.box.empty(), [])

    def test_drive_refuses_an_unrecorded_or_second_drive(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with scratch_repo() as root:
            rig = Rig(drive, root)
            with spying(rig.spy):
                with self.assertRaises(drive.DriveRefused):
                    rig.driver.drive(row(1), "0" * 64)
                cid = rig.driver.launch(row(1))
                with self.assertRaises(drive.DriveRefused):
                    rig.driver.drive(row(2), cid)
                rig.driver.drive(row(1), cid)
                with self.assertRaises(drive.DriveRefused):
                    rig.driver.drive(row(1), cid)

    def test_sidecar_health_reads_a_gap_never_healthy(self):
        need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        with tempfile.TemporaryDirectory(dir=SCRATCH) as ev:
            self.assertEqual(drive.sidecar_health(ev), {"start_record": False, "stop_record": False,
                                                         "exit_code": -1, "queue_overflow": False})
            with open(os.path.join(ev, sc.HEALTH), "w") as fh:
                for rec in ({"kind": sc.WATCHER_START}, {"kind": sc.WATCHER_STOP, "exit_code": 137},
                            {"kind": sc.QUEUE_OVERFLOW}):
                    fh.write(json.dumps(rec) + "\n")
            self.assertEqual(drive.sidecar_health(ev), {"start_record": True, "stop_record": False,
                                                         "exit_code": 137, "queue_overflow": True})


class TestBoundChecks(unittest.TestCase):
    def test_b1_a_refused_commit_restores_the_ledger(self):
        self.assertEqual(b1_rollback(drive), [])

    def test_b2_preflight_is_s1s_entry_point_before_any_turn(self):
        self.assertEqual(b2_preflight(drive), [])

    def test_b3_a_pre_turn_refusal_runs_no_turn_and_rehearses(self):
        self.assertEqual(b3_preturn(drive), [])

    def test_b4_scan_mask_route_commit(self):
        self.assertEqual(b4_scan(drive), [])

    def test_b5_every_road_cleans_up(self):
        self.assertEqual(b5_cleanup(drive), [])

    def test_b6_quiescence_kills_as_the_agent_before_the_snapshot(self):
        self.assertEqual(b6_quiesce(drive), [])

    def test_b7_remove_is_by_the_recorded_id(self):
        self.assertEqual(b7_remove(drive), [])

    def test_b8_the_config_folder_goes_only_after_the_commit(self):
        self.assertEqual(b8_config(drive), [])

    def test_b10_the_driver_ends_the_adapter_by_its_own_flag(self):
        self.assertEqual(b10_adapter_end(drive), [])

    def test_b11_postflight_runs_and_a_credential_file_stops(self):
        self.assertEqual(b11_postflight(drive), [])

    def test_b12_a_failed_publish_cleanup_refuses_the_next_launch(self):
        self.assertEqual(b12_publish(drive), [])

    def test_b13_an_outcome_without_its_leak_keys_is_a_typed_refusal(self):
        self.assertEqual(b13_history(drive), [])

    def test_b14_the_restart_lists_networks_too(self):
        self.assertEqual(b14_net(drive), [])

    def test_b15_the_operator_save_is_logged_and_explained(self):
        self.assertEqual(b15_operator(drive), [])

    def test_b16_an_operator_write_on_an_excluded_path_is_refused(self):
        self.assertEqual(b16_excluded(drive), [])

    def test_b17_the_finalize_wait_and_its_abort(self):
        self.assertEqual(b17_finalize(drive), [])

    def test_b18_the_evidence_ledger_loads(self):
        self.assertEqual(b18_evidence(drive), [])

    def test_the_design_table_path_is_the_generators_layout(self):
        """W6I-R1-4: gen_confounded_seed2 writes <out>/src/... and <out>/samples.csv, and the task's source is
        <out>/src, so the operator step's table is the source template's folder above src, plus samples.csv; the
        generator's table is the fixture's pinned md5."""
        import hashlib
        import posixpath
        from fixtures import gen_confounded_seed2 as gen
        need(self, "DESIGN_TABLE")
        task = variants.load_task("confounded-design")
        fx = task["halves"]["trap"]["fixture"]
        files = gen.build_half(fx["half"], fx["seed"])
        self.assertIn("samples.csv", files)
        self.assertTrue(all(p == "samples.csv" or p.startswith("src/") for p in files), sorted(files)[:3])
        src = task["source_template"]
        self.assertTrue(src.startswith("{run_tree}/") and src.endswith("/src"), src)
        out = posixpath.dirname(src[len("{run_tree}/"):])
        self.assertEqual(drive.DESIGN_TABLE, out + "/samples.csv")
        self.assertEqual(hashlib.md5(files["samples.csv"]).hexdigest(), fx["design_table"]["md5"])

    def test_b9_a_leaked_sidecar_or_proxy_refuses_the_restart(self):
        self.assertEqual(b9_restart(drive), [])


# ------------------------------------------------------------------------------------------------ the real-box half
class RealBoxHalf:
    """CP2's real-box half of this module, a NAMED STUB: not a TestCase, so the battery (whose SKIP_ALLOWED is empty)
    never collects it. Each method raises SkipTest naming the real-box step it waits on."""

    def test_stub_take_on_the_real_box(self):
        raise unittest.SkipTest(REAL_BOX_STEP)


class TestRealBoxStub(unittest.TestCase):
    def test_the_real_box_half_is_a_named_stub_that_skips(self):
        with self.assertRaises(unittest.SkipTest) as cm:
            RealBoxHalf().test_stub_take_on_the_real_box()
        self.assertEqual(str(cm.exception), REAL_BOX_STEP)
        self.assertFalse(issubclass(RealBoxHalf, unittest.TestCase))


# ------------------------------------------------------------------------------------------------ the witnesses
class WitnessNotPerformed(AssertionError):
    pass


def witness_module(edits: tuple) -> types.ModuleType:
    """drive.py with `edits` applied, compiled in memory as its own module (never written to disk). Every anchor must
    occur exactly once, or the witness was not performed."""
    with open(drive.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    name = "drive_w6h_witness"
    mod = types.ModuleType(name)
    mod.__file__ = drive.__file__
    sys.modules[name] = mod
    try:
        exec(compile(src, drive.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    return mod


# name: (edits to drive.py, the bound check, the line prefix that is its own assertion)
WITNESSES = {
    "omit-restore": ((("                self._restore()\n", "                pass\n"),), b1_rollback, "B1-rollback"),
    "skip-preflight": ((("            ok = self._preflight(take, row[\"agent\"][\"harness\"])", "            ok = True"),),
                       b2_preflight, "B2-preflight"),
    "failed-preflight-read-as-passed": ((("        return record[\"ok\"] is True\n", "        return True\n"),),
                                        b3_preturn, "B3-preturn"),
    "no-drive-scan": ((("        scan = _scan_record.scan(self.take_files(take), list(self.secrets()), "
                        "rules_scanner=self.rules_scanner,\n",
                        "        scan = {\"refused\": [], \"events\": 0} or _scan_record.scan(self.take_files(take), "
                        "list(self.secrets()), rules_scanner=self.rules_scanner,\n"),),
                      b4_scan, "B4-scan"),
    "no-finally-cleanup": ((("            self._cleanup(take, adapter)\n", "            pass\n"),),
                           b5_cleanup, "B5-cleanup"),
    "no-cap-kill": ((("            if survivors:\n                self._kill(take)\n",
                      "            if False:\n                self._kill(take)\n"),), b6_quiesce, "B6-quiesce"),
    "remove-never-removes": ((("        for cid in _run_take.leaked(self.runtime, ids, caller_env=self.caller_env):\n",
                               "        for cid in []:\n"),
                              ("        still = _run_take.leaked(self.runtime, ids, caller_env=self.caller_env)\n",
                               "        still = []\n")), b7_remove, "B7-remove"),
    "remove-checks-the-take-alone": ((("        ids = launched.ids() if launched is not None else [container_id]\n",
                                       "        ids = [container_id]\n"),), b7_remove, "B7-remove"),
    "leaked-take-id-only": ((("            for cid in [entry[\"leaked_container\"], *(entry[\"leaked_containers\"] or [])]:\n",
                              "            for cid in [entry[\"leaked_container\"]]:\n"),), b9_restart, "B9-restart"),
    "timeout-not-a-refusal": ((("    if isinstance(e, (ValueError, TimeoutError)):\n",
                                "    if isinstance(e, ValueError):\n"),), b3_preturn, "B3-preturn"),
    "no-on-published": ((("                self.on_published(row, attempt)\n", "                pass\n"),),
                        b8_config, "B8-config"),
    # S6b (lane w6i)
    "adapter-private-state": ((("        if adapter is not None and take.adapter_open:",
                                "        if adapter is not None and getattr(adapter, \"_state\", None) == \"open\":"),),
                              b10_adapter_end, "B10-adapter-end"),
    "no-postflight": ((("            post = self._postflight(take, row)",
                        "            post = {\"ok\": True, \"checks\": [{\"detail\": \"\"}]}"),),
                      b11_postflight, "B11-postflight"),
    "launch-ignores-publish-problems": ((("        if self.publish_problems:      ", "        if False:      "),),
                                        b12_publish, "B12-publish"),
    "bare-keyerror": ((("            if missing:          # W6H-R2-1", "            if False:          # W6H-R2-1"),),
                      b13_history, "B13-history"),
    "restart-lists-containers-only": ((("        nets = leaked_networks(self.runtime, ids, caller_env=self.caller_env)",
                                        "        nets = []"),), b14_net, "B14-net"),
    "unlogged-save": ((("        self._evidence_line(take, {\"kind\": \"operator\", \"id\": op_id, \"at\": self.clock(),\n"
                        "                                   \"writes\": [{\"path\": rel, \"after\": {\"type\": \"file\", "
                        "\"sha256\": sha}}]})\n",
                        "        pass\n"),), b15_operator, "B15-operator"),
    "log-excluded-write": ((("        if self._excluded(rel, row[\"agent\"][\"harness\"]):", "        if False:"),),
                           b16_excluded, "B16-excluded"),
    "no-finalize-wait": ((("                if self.clock() >= deadline:\n", "                if True:\n"),),
                         b17_finalize, "B17-finalize"),
    "design-unbound": ((("            if not want or got != want:", "            if False:"),), b17_finalize,
                       "B17-finalize"),
    "no-background-line": ((("                            self._evidence_line(take, {\"kind\": \"background\", "
                             "\"pid\": pid, \"stopped_at\": stopped})\n", "                            pass\n"),),
                           b18_evidence, "B18-evidence"),
}
WITNESS_LOG: list = []


class TestWitnesses(unittest.TestCase):
    """Each witness is killed only by its bound check's own assertion (a line with its prefix), with the bound check
    green on the real drive.py first; an ERROR line, a raise, an unperformed edit or a skip is never a kill. Every
    other line the bound check prints under the witness is listed as collateral, never credited."""

    def kill(self, name):
        edits, check, prefix = WITNESSES[name]
        self.assertEqual(check(drive), [], f"{name}: the bound check is not green on drive.py")
        got = check(witness_module(edits))
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(prefix + ":")]
        collateral = [x for x in got if x not in own and x not in errors]
        line = (f"WITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
                f"{len(collateral)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ", file=sys.stderr, flush=True)
        WITNESS_LOG.append(line)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_omit_restore(self):
        self.kill("omit-restore")

    def test_witness_skip_preflight(self):
        self.kill("skip-preflight")

    def test_witness_failed_preflight_read_as_passed(self):
        self.kill("failed-preflight-read-as-passed")

    def test_witness_no_drive_scan(self):
        self.kill("no-drive-scan")

    def test_witness_no_finally_cleanup(self):
        self.kill("no-finally-cleanup")

    def test_witness_no_cap_kill(self):
        self.kill("no-cap-kill")

    def test_witness_remove_never_removes(self):
        self.kill("remove-never-removes")

    def test_witness_no_on_published(self):
        self.kill("no-on-published")

    def test_witness_remove_checks_the_take_alone(self):
        self.kill("remove-checks-the-take-alone")

    def test_witness_leaked_take_id_only(self):
        self.kill("leaked-take-id-only")

    def test_witness_timeout_not_a_refusal(self):
        self.kill("timeout-not-a-refusal")

    def test_witness_unlogged_save(self):
        self.kill("unlogged-save")

    def test_witness_log_excluded_write(self):
        self.kill("log-excluded-write")

    def test_witness_no_finalize_wait(self):
        self.kill("no-finalize-wait")

    def test_witness_design_unbound(self):
        self.kill("design-unbound")

    def test_witness_no_background_line(self):
        self.kill("no-background-line")

    def test_witness_adapter_private_state(self):
        self.kill("adapter-private-state")

    def test_witness_no_postflight(self):
        self.kill("no-postflight")

    def test_witness_launch_ignores_publish_problems(self):
        self.kill("launch-ignores-publish-problems")

    def test_witness_bare_keyerror(self):
        self.kill("bare-keyerror")

    def test_witness_restart_lists_containers_only(self):
        self.kill("restart-lists-containers-only")

    def test_the_witnesses_are_named_and_each_bound_to_its_own_check(self):
        self.assertEqual(sorted(WITNESSES), sorted(["omit-restore", "skip-preflight",
                                                    "failed-preflight-read-as-passed", "no-drive-scan",
                                                    "no-finally-cleanup", "no-cap-kill", "remove-never-removes",
                                                    "no-on-published", "remove-checks-the-take-alone",
                                                    "timeout-not-a-refusal", "leaked-take-id-only",
                                                    "adapter-private-state", "no-postflight",
                                                    "launch-ignores-publish-problems", "bare-keyerror",
                                                    "restart-lists-containers-only", "unlogged-save",
                                                    "log-excluded-write", "no-finalize-wait", "no-background-line",
                                                    "design-unbound"]))
        # Twenty-one witnesses over eighteen bound checks: W6H-R1-1's, R1-3's and W6I-R1-4's share B3, B7 and B17.
        self.assertEqual(len({w[1].__name__ for w in WITNESSES.values()}), 18)
        self.assertEqual(len({w[2] for w in WITNESSES.values()}), 18)


if __name__ == "__main__":
    unittest.main(verbosity=2)
