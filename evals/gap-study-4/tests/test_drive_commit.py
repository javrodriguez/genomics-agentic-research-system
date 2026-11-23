#!/usr/bin/env python3
"""Lane w6e (Gap Study round 4, slice S5): the CP2 drive lifecycle, part 1, the commit step, on fakes only.

What is tested, each guard with its own bound check and a whole-file witness of drive.py:

  C1-restage   the commit step stages the take's files, scans them (box/scan_record.py masks agent-text hits on
               disk), STAGES THEM AGAIN and commits the masked bytes (w4c Q3; CP2-requirements, "Re-stage and
               re-hash after masking"). Witness: the re-stage line removed.
  C2-rehash    every staged blob's sha256 must equal the scan's `sha256_after` before the commit; a file that moved
               after the scan refuses the commit. Witness: the comparison removed.
  C3-history   TakeRepo.history() returns the committed outcomes and rulings in commit order (takes.read_history),
               so a ruling committed after its outcome comes back after it (CP2-requirements, open question 10).
               Witness: history() concatenates outcomes.json and rulings.json instead.
  C4-restart   register() refuses while a container that the committed history records as leaked is still listed
               by the runtime, names it, and commits nothing (CP2-requirements, open question 11). Witness: the
               refusal call removed.
  C5-staged    every staged name must be one of the take's declared files or the outcome ledger; a stray staged
               file refuses the commit rather than riding it unscanned. Witness: the stray-name refusal removed.
  C6-preflight the driver's preflight road is S1's composition entry point (preflight.collect_and_evaluate), with
               every argument passed through; the driver never loads or flattens a lock itself. Witness: the road
               calls the pure evaluator directly, past the entry point.

Fakes and synthetic strings only: no model, vendor, network, container runtime, credential or holdout. Every git
call runs in a scratch repository under this module's own temporary folder, with an empty HOME and no global or
system git config. setUpModule arms a process guard that refuses every process start except `git -C <scratch>`,
patches prereg's readers (the base has no pre-registration; drive.py reads one at import) and only then imports
drive.py. tearDownModule restores everything.

Witnesses follow the w6a registry pattern: drive.py with one exact anchor edit, compiled in memory as its own module
(never written to disk). A kill counts only when the bound check is green on the real module first and then
returns at least one line with its own prefix and no ERROR line.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import batch  # noqa: E402
import harness_bookkeeping as hb  # noqa: E402
import prereg  # noqa: E402
import takes  # noqa: E402
import variants  # noqa: E402
from box import preflight as pf  # noqa: E402
from box import run_take as rt  # noqa: E402
from box import scan_record as sr  # noqa: E402
from graders import labels4  # noqa: E402

drive = None            # imported in setUpModule, after the guard and the prereg patch
SCRATCH: Path | None = None
_STACK = contextlib.ExitStack()

TOKEN = "synthetic-login-value-" + "0123456789abcdef"     # a planted fake, never a real login
LEAKED = "a" * 64
OTHER = "b" * 64
PS_ARGV = [rt.RUNTIME_CLIENT, "ps", "--all", "--no-trunc", "--quiet"]


# ------------------------------------------------------------------------------------------------ the process guard
class GuardTripped(Exception):
    """A process start this module never allows."""


_REAL = {"run": subprocess.run, "Popen": subprocess.Popen}
_TRIPPED: list = []


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
        _TRIPPED.append(repr(args)[:80])
        raise GuardTripped(f"process guard: subprocess.{name} refused {args!r}"[:200])
    return gate


def _trip(name):
    def trip(*a, **kw):
        _TRIPPED.append(name)
        raise GuardTripped(f"process guard: {name} refused")
    return trip


def setUpModule():
    global drive, SCRATCH
    SCRATCH = Path(_STACK.enter_context(tempfile.TemporaryDirectory(prefix="w6e-"))).resolve()
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
    # drive.py reads the pre-registration at import (STRIPPED_ENV); registration reads the frozen design. Neither
    # exists at this base, so both are synthetic here, and only here.
    _STACK.enter_context(mock.patch.object(prereg, "load", lambda: {"driver_constants": {}}))
    _STACK.enter_context(mock.patch.object(prereg, "require_frozen", lambda what: {"rows": [row(n) for n in
                                                                                           range(1, 7)]}))
    import drive as imported
    drive = imported


def tearDownModule():
    _STACK.close()


# ------------------------------------------------------------------------------------------------ synthetic records
def row(n=1, **kw):
    cell = variants.task_cells({"factor": None}, {"wordings": [{"id": "w1"}, {"id": "w2"}]})
    r = {"arm": "A", "task": "synthetic-task", "model": "synthetic-model",
         "agent": {"harness": hb.CLAUDE_CODE, "version": "0.0.1"}, **cell[(n - 1) % len(cell)],
         "slot": f"s{n}", "half_cell": "c1"}
    r.update(kw)
    return r


def outcome(r, attempt=1, state=labels4.GRADED, **kw):
    o = batch.Batch._outcome(r, attempt, None, state=state)
    o.update(batch.Batch._fate(final=True))
    o.update(kw)
    return o


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


class FakeRuntime:
    """The runtime protocol run_take uses (run(argv, env=, timeout=)), answering only the full container listing."""
    def __init__(self, listed=()):
        self.listed = list(listed)
        self.calls = []

    def run(self, argv, env=None, timeout=None):
        self.calls.append(list(argv))
        if list(argv) == PS_ARGV:
            return rt.Completed(0, "".join(i + "\n" for i in self.listed), "")
        raise GuardTripped(f"the fake runtime refuses {argv!r}")


class Records:
    """The take's record files, as the drive step will hand them to the repo: (absolute path, scan kind)."""
    def __init__(self, root: Path):
        self.root = root
        self.files: dict = {}

    def write(self, r, attempt, name, kind, text):
        p = self.root / "records" / f"{r['slot']}-{attempt}" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        self.files.setdefault((r["slot"], attempt), []).append((str(p), kind))
        return p

    def __call__(self, r, attempt):
        return list(self.files.get((r["slot"], attempt), []))


def make_repo(mod, root, records, runtime=None, scanner=None):
    return mod.TakeRepo(runtime=runtime or FakeRuntime(), record_files=records,
                        secrets=lambda: [("token", TOKEN)], rules_scanner=scanner or (lambda paths: []),
                        root=root, repo=root)


def stream_line(text):
    return json.dumps({"type": "assistant", "text": text}) + "\n"


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
                return [f"ERROR {prefix}: {type(e).__name__}: {str(e)[:200]}"]
        check.__name__ = fn.__name__
        return check
    return wrap


# ------------------------------------------------------------------------------------------------ the bound checks
@guarded("C1-restage")
def c1_restage(mod, p):
    out = missing_api(mod, p, "TakeRepo", "CommitRefused")
    if out:
        return out
    with scratch_repo() as root:
        records = Records(root)
        repo = make_repo(mod, root, records)
        r = row(1)
        repo.register(r, 1)
        stream = records.write(r, 1, "stream.jsonl", "stream",
                               stream_line("plain") + stream_line(f"echo {TOKEN} done") + stream_line("after"))
        records.write(r, 1, "launch.json", "launch", json.dumps({"ok": True}) + "\n")
        o = outcome(r)
        try:
            got = repo.commit_records(r, 1, o)
        except mod.CommitRefused as e:
            return [f"{p}: the masked take was refused instead of committed: {e}"]
        rel = stream.relative_to(root).as_posix()
        committed = git_bytes(root, "show", f"HEAD:{rel}")
        if TOKEN.encode() in committed:
            out.append(f"{p}: the committed stream still holds the planted value")
        if sr.MARKERS["token"].encode() not in committed:
            out.append(f"{p}: the committed stream does not hold the mask marker")
        if committed != stream.read_bytes():
            out.append(f"{p}: the committed stream is not the masked bytes on disk")
        if any(not line or json.loads(line) is None for line in committed.decode().splitlines()):
            out.append(f"{p}: a committed stream line is not JSON")
        if git(root, "status", "--porcelain"):
            out.append(f"{p}: the tree is not clean after the commit")
        names = set(git(root, "show", "--format=", "--name-only", "HEAD").splitlines())
        if names != {rel, f"records/{r['slot']}-1/launch.json", "outcomes.json"}:
            out.append(f"{p}: the commit holds {sorted(names)}, not the take's two files and the ledger")
        if repo.history() != [o]:
            out.append(f"{p}: the history is not the one committed outcome")
        if not isinstance(got, dict) or got.get("events") != 1 or got.get("commit") != git(root, "rev-parse", "HEAD"):
            out.append(f"{p}: the commit step's return is not the commit and its one masked event: {got!r}")
    return out


@guarded("C2-rehash")
def c2_rehash(mod, p):
    out = missing_api(mod, p, "TakeRepo", "CommitRefused")
    if out:
        return out
    real_scan = sr.scan

    def scan_then_move(files, secrets, **kw):
        result = real_scan(files, secrets, **kw)
        for path, kind in files:
            if kind == "stream":
                with open(path, "ab") as fh:          # a writer after the scan: these bytes were never scanned
                    fh.write(stream_line("late").encode())
        return result

    with scratch_repo() as root:
        records = Records(root)
        repo = make_repo(mod, root, records)
        r = row(1)
        repo.register(r, 1)
        records.write(r, 1, "stream.jsonl", "stream", stream_line(f"said {TOKEN}"))
        before = git(root, "rev-parse", "HEAD")
        with mock.patch.object(sr, "scan", scan_then_move):
            try:
                repo.commit_records(r, 1, outcome(r))
            except mod.CommitRefused as e:
                if "stream.jsonl" not in str(e):
                    out.append(f"{p}: the refusal does not name the file that moved: {e}")
                if TOKEN in str(e):
                    out.append(f"{p}: the refusal carries the planted value")
            else:
                out.append(f"{p}: a staged blob that is not the scanned bytes was committed")
        if git(root, "rev-parse", "HEAD") != before:
            out.append(f"{p}: a commit landed for the moved file")
    return out


@guarded("C3-history")
def c3_history(mod, p):
    out = missing_api(mod, p, "TakeRepo")
    if out:
        return out
    with scratch_repo() as root:
        records = Records(root)
        repo = make_repo(mod, root, records)
        r = row(1)
        repo.register(r, 1)
        records.write(r, 1, "stream.jsonl", "stream", stream_line("first"))
        # the review of 5afd80a7, finding 3: a take whose drive left no records is re-run only on the driver's own
        # refusal record, committed with its outcome (here by the commit road under test); the end state is stubbed
        refusal = root / takes.mode_binding.TAKES_DIR / str(r["slot"]) / "1" / takes.DRIVER_REFUSAL_RECORD
        refusal.parent.mkdir(parents=True)          # the take's own folder, where the driver writes the record
        refusal.write_text(json.dumps({"refused": "TimeoutError", "why": "synthetic begin exec timed out"}))
        records.files.setdefault((r["slot"], 1), []).append((str(refusal), "preflight"))
        o1 = outcome(r, state=labels4.FAILED, final=False)
        repo.commit_records(r, 1, o1)
        ruled = takes.commit_ruling(slot=r["slot"], attempt=1, word=labels4.RULE_RERUN, route=None,
                                    by="synthetic-person", why="synthetic", cite="synthetic", root=root, repo=root,
                                    standing=lambda row, o: "right")
        restarted = make_repo(mod, root, records)
        restarted.register(r, 2)
        records.write(r, 2, "stream.jsonl", "stream", stream_line("second"))
        o2 = outcome(r, attempt=2)
        restarted.commit_records(r, 2, o2)
        got = make_repo(mod, root, records).history()
        if got != [o1, ruled, o2]:
            kinds = [("ruling" if batch.is_ruling(e) else f"outcome {e['attempt']}") for e in got]
            out.append(f"{p}: the history is not in commit order: {kinds}")
        if not out and batch.Batch.history_problems(got):
            out.append(f"{p}: batch cannot trust the history: {batch.Batch.history_problems(got)}")
    return out


@guarded("C4-restart")
def c4_restart(mod, p):
    out = missing_api(mod, p, "TakeRepo")
    if out:
        return out
    with scratch_repo() as root:
        records = Records(root)
        repo = make_repo(mod, root, records)
        r1 = row(1)
        repo.register(r1, 1)
        records.write(r1, 1, "stream.jsonl", "stream", stream_line("leaky"))
        repo.commit_records(r1, 1, outcome(r1, container_id=LEAKED, leaked_container=LEAKED,
                                           reason=f"container {LEAKED} leaked: remove failed: synthetic",
                                           stop=f"container {LEAKED} leaked: remove failed: synthetic"))
        head, rows = git(root, "rev-parse", "HEAD"), takes.load_rows(root=root, repo=root)
        still = FakeRuntime(listed=[OTHER, LEAKED])
        restarted = make_repo(mod, root, records, runtime=still)
        try:
            restarted.register(row(2), 1)
        except rt.LeakedContainer as e:
            if LEAKED not in str(e):
                out.append(f"{p}: the refusal does not name the leaked container: {e}")
        else:
            out.append(f"{p}: a restart registered while a leaked container is still present")
        if git(root, "rev-parse", "HEAD") != head or takes.load_rows(root=root, repo=root) != rows:
            out.append(f"{p}: the refused restart committed a registration")
        if still.calls != [PS_ARGV]:
            out.append(f"{p}: the runtime was asked {still.calls}, not the one full listing")
        if out:
            return out
        gone = FakeRuntime(listed=[OTHER])
        make_repo(mod, root, records, runtime=gone).register(row(2), 1)
        if len(takes.load_rows(root=root, repo=root)) != len(rows) + 1 or gone.calls != [PS_ARGV]:
            out.append(f"{p}: with the leaked container gone, the restart did not register after one listing")
    return out


@guarded("C5-staged")
def c5_staged(mod, p):
    out = missing_api(mod, p, "TakeRepo", "CommitRefused")
    if out:
        return out
    with scratch_repo() as root:
        records = Records(root)
        repo = make_repo(mod, root, records)
        r = row(1)
        repo.register(r, 1)
        records.write(r, 1, "stream.jsonl", "stream", stream_line("plain"))
        stray = root / "notes.txt"
        stray.write_text(f"an operator note holding {TOKEN}\n")
        git(root, "add", "--", "notes.txt")
        before = git(root, "rev-parse", "HEAD")
        try:
            repo.commit_records(r, 1, outcome(r))
        except mod.CommitRefused as e:
            if "notes.txt" not in str(e):
                out.append(f"{p}: the refusal does not name the stray staged file: {e}")
        else:
            out.append(f"{p}: a staged file outside the take rode the commit unscanned")
        if git(root, "rev-parse", "HEAD") != before:
            out.append(f"{p}: a commit landed after the refusal")
    return out


@guarded("C6-preflight")
def c6_preflight(mod, p):
    out = missing_api(mod, p, "preflight_take")
    if out:
        return out
    seen, sentinel = [], {"ok": True, "synthetic": "preflight record"}

    def spy(runtime, **kw):
        seen.append((runtime, kw))
        return sentinel

    def refuse(*a, **kw):
        raise GuardTripped("the driver reached past the composition entry point")

    args = dict(launched=object(), sidecar=object(), lock_path="/synthetic/box/image.lock", harness=hb.CLAUDE_CODE,
                hosts={"synthetic": "host"}, evidence_dir="/synthetic/evidence", begin_reply=object(),
                caller_env={"SYNTHETIC": "1"})
    runtime = FakeRuntime()
    with mock.patch.object(pf, "collect_and_evaluate", spy), mock.patch.object(pf, "evaluate", refuse), \
            mock.patch.object(pf, "load_take_lock", refuse), mock.patch.object(pf.image_lock, "load", refuse):
        try:
            got = mod.preflight_take(runtime, **args)
        except (GuardTripped, OSError, ValueError) as e:
            return [f"{p}: the driver did not take S1's entry point: {type(e).__name__}: {e}"]
    if got is not sentinel:
        out.append(f"{p}: the preflight record is not the entry point's own")
    if len(seen) != 1 or seen[0][0] is not runtime or seen[0][1] != args:
        out.append(f"{p}: the entry point was not called once with every argument passed through")
    if runtime.calls:
        out.append(f"{p}: the driver called the runtime itself: {runtime.calls}")
    return out


@guarded("C7-duplicate")
def c7_duplicate(mod, p):
    """W6E-R1-1: an outcome batch could not trust after the committed history refuses before the ledger is written."""
    out = missing_api(mod, p, "TakeRepo", "CommitRefused")
    if out:
        return out
    with scratch_repo() as root:
        repo = make_repo(mod, root, Records(root))
        r = row(1)
        repo.register(r, 1)
        o = outcome(r, state=labels4.FAILED, final=False, drive_started=False)
        repo.commit_records(r, 1, o)
        head, ledger = git(root, "rev-parse", "HEAD"), (root / "outcomes.json").read_bytes()
        try:
            repo.commit_records(r, 1, o)
        except mod.CommitRefused:
            pass
        else:
            out.append(f"{p}: the same slot and attempt were committed twice")
        if (root / "outcomes.json").read_bytes() != ledger:
            out.append(f"{p}: the ledger on disk was written for the refused outcome")
        if git(root, "rev-parse", "HEAD") != head and not out:
            out.append(f"{p}: a commit landed for the refused outcome")
        try:
            if make_repo(mod, root, Records(root)).history() != [o]:
                out.append(f"{p}: the history is not the one committed outcome")
        except ValueError as e:
            out.append(f"{p}: the history no longer reads: {str(e)[:120]}")
    return out


def _refused_record(mod, p, root, repo, r, path, kind, why):
    """Commit r with `path` as its one record file; a refusal with nothing written and HEAD unmoved is green."""
    out = []
    repo.record_files = lambda rr, a: [(str(path), kind)]
    head = git(root, "rev-parse", "HEAD")
    try:
        repo.commit_records(r, 1, outcome(r))
    except mod.CommitRefused:
        pass
    else:
        out.append(f"{p}: {why} was committed as a take's record")
    if not out and (git(root, "rev-parse", "HEAD") != head or (root / "outcomes.json").exists()):
        out.append(f"{p}: {why} was refused only after something was written")
    return out


@guarded("C8-reserved")
def c8_reserved(mod, p):
    """W6E-R1-2: the study's ledgers are never a take's record file, tracked or not."""
    out = missing_api(mod, p, "TakeRepo", "CommitRefused")
    if out:
        return out
    with scratch_repo() as root:
        repo = make_repo(mod, root, Records(root))
        r = row(1)
        repo.register(r, 1)
        rulings = root / "rulings.json"
        rulings.write_text("[]\n")
        out += _refused_record(mod, p, root, repo, r, rulings, "ledger", "rulings.json (untracked)")
        if out:
            return out
        rulings.unlink()
        git(root, "reset", "-q")
        takes_json = root / "takes.json"
        takes_json.write_text(takes_json.read_text() + "\n")
        out += _refused_record(mod, p, root, repo, r, takes_json, "ledger", "takes.json")
    return out


@guarded("C9-tracked")
def c9_tracked(mod, p):
    """W6E-R1-2: a path already tracked at HEAD is never a take's record file."""
    out = missing_api(mod, p, "TakeRepo", "CommitRefused")
    if out:
        return out
    with scratch_repo() as root:
        repo = make_repo(mod, root, Records(root))
        r = row(1)
        repo.register(r, 1)
        source = root / "README"
        source.write_text(source.read_text() + "a take rewrote a tracked file\n")
        out += _refused_record(mod, p, root, repo, r, source, "evidence", "a tracked source file")
    return out


@guarded("C10-bound")
def c10_bound(mod, p):
    """W6E-R1-3: the commit is the checked tree. A file staged after the check never lands; a HEAD that moved after
    the check refuses the commit and is left where the other actor put it."""
    out = missing_api(mod, p, "TakeRepo", "CommitRefused")
    if out:
        return out
    if not callable(getattr(mod.TakeRepo, "_before_commit", None)):
        return [f"{p}: drive.py's TakeRepo has no _before_commit seam between the checked tree and the commit"]
    with scratch_repo() as root:
        records = Records(root)
        repo = make_repo(mod, root, records)
        r = row(1)
        repo.register(r, 1)
        records.write(r, 1, "stream.jsonl", "stream", stream_line("plain"))

        def interloper():
            (root / "stray.txt").write_text(f"staged after the check {TOKEN}\n")
            git(root, "add", "--", "stray.txt")
        repo._before_commit = interloper
        try:
            repo.commit_records(r, 1, outcome(r))
        except mod.CommitRefused:
            pass
        if "stray.txt" in git(root, "ls-tree", "-r", "--name-only", "HEAD").splitlines():
            out.append(f"{p}: a file staged after the check landed in the commit")
    with scratch_repo() as root:
        records = Records(root)
        repo = make_repo(mod, root, records)
        r = row(1)
        repo.register(r, 1)
        records.write(r, 1, "stream.jsonl", "stream", stream_line("plain"))
        moved = {}

        def mover():
            # another actor's commit on the same head: HEAD's own tree, a new commit that is not the checked one
            moved["sha"] = git(root, "commit-tree", git(root, "rev-parse", "HEAD^{tree}"),
                               "-p", git(root, "rev-parse", "HEAD"), "-m", "Another actor")
            git(root, "update-ref", "HEAD", moved["sha"])
        repo._before_commit = mover
        try:
            repo.commit_records(r, 1, outcome(r))
        except mod.CommitRefused:
            pass
        else:
            out.append(f"{p}: the commit landed although HEAD moved after the check")
        if moved and git(root, "rev-parse", "HEAD") != moved["sha"] and not out:
            out.append(f"{p}: the other actor's HEAD was overwritten")
    return out


# ------------------------------------------------------------------------------------------------ the tests
class TestGuardArmed(unittest.TestCase):
    def test_a_process_start_outside_scratch_git_trips(self):
        for argv in (["true"], [rt.RUNTIME_CLIENT, "ps"], ["git", "-C", "/", "status"]):
            with self.subTest(argv=argv):
                with self.assertRaises(GuardTripped):
                    subprocess.run(argv, capture_output=True)
        with self.assertRaises(GuardTripped):
            os.system("true")

    def test_git_identity_comes_only_from_the_scratch_repo(self):
        self.assertEqual(os.environ.get("GIT_CONFIG_GLOBAL"), os.devnull)
        with scratch_repo() as root:
            self.assertEqual(takes._git_at(root, "config", "--get", "user.name"), "synthetic")


class TestCommitStep(unittest.TestCase):
    def test_c1_masked_files_are_restaged_and_committed_masked(self):
        self.assertEqual(c1_restage(drive), [])

    def test_c2_a_staged_blob_that_is_not_the_scanned_bytes_refuses(self):
        self.assertEqual(c2_rehash(drive), [])

    def test_c5_a_stray_staged_file_refuses(self):
        self.assertEqual(c5_staged(drive), [])

    def test_a_take_with_nothing_to_mask_commits_its_files_and_outcome(self):
        self.assertTrue(hasattr(drive, "TakeRepo"), "drive.py has no TakeRepo")
        with scratch_repo() as root:
            records = Records(root)
            repo = make_repo(drive, root, records)
            r = row(1)
            repo.register(r, 1)
            p = records.write(r, 1, "stream.jsonl", "stream", stream_line("nothing secret"))
            got = repo.commit_records(r, 1, outcome(r))
            self.assertEqual(got["events"], 0)
            self.assertEqual(git_bytes(root, "show", f"HEAD:{p.relative_to(root).as_posix()}"), p.read_bytes())
            self.assertEqual(git(root, "status", "--porcelain"), "")

    def test_a_failed_take_with_no_records_commits_the_outcome_alone(self):
        self.assertTrue(hasattr(drive, "TakeRepo"), "drive.py has no TakeRepo")
        with scratch_repo() as root:
            repo = make_repo(drive, root, Records(root))
            r = row(1)
            repo.register(r, 1)
            o = outcome(r, state=labels4.FAILED, final=False, drive_started=False)
            repo.commit_records(r, 1, o)
            self.assertEqual(git(root, "show", "--format=", "--name-only", "HEAD"), "outcomes.json")
            self.assertEqual(repo.history(), [o])

    def test_a_value_in_a_file_that_cannot_be_masked_refuses_and_commits_nothing(self):
        self.assertTrue(hasattr(drive, "CommitRefused"), "drive.py has no CommitRefused")
        with scratch_repo() as root:
            records = Records(root)
            repo = make_repo(drive, root, records)
            r = row(1)
            repo.register(r, 1)
            records.write(r, 1, "launch.json", "launch", json.dumps({"note": TOKEN}) + "\n")
            before = git(root, "rev-parse", "HEAD")
            with self.assertRaises(drive.CommitRefused) as cm:
                repo.commit_records(r, 1, outcome(r))
            self.assertIn("launch.json", str(cm.exception))
            self.assertNotIn(TOKEN, str(cm.exception))
            self.assertEqual(git(root, "rev-parse", "HEAD"), before)

    def test_a_rules_scanner_finding_refuses(self):
        self.assertTrue(hasattr(drive, "CommitRefused"), "drive.py has no CommitRefused")
        with scratch_repo() as root:
            records = Records(root)
            finding = lambda paths: [{"path": paths[0], "line": 1, "rule": "synthetic-rule"}]
            repo = make_repo(drive, root, records, scanner=finding)
            r = row(1)
            repo.register(r, 1)
            records.write(r, 1, "stream.jsonl", "stream", stream_line("plain"))
            before = git(root, "rev-parse", "HEAD")
            with self.assertRaises(drive.CommitRefused):
                repo.commit_records(r, 1, outcome(r))
            self.assertEqual(git(root, "rev-parse", "HEAD"), before)

    def test_bad_record_lists_and_outcomes_refuse_before_any_write(self):
        self.assertTrue(hasattr(drive, "CommitRefused"), "drive.py has no CommitRefused")
        with scratch_repo() as root:
            r = row(1)
            make_repo(drive, root, Records(root)).register(r, 1)
            (root / "records").mkdir()
            inside = root / "records" / "x.jsonl"
            inside.write_text(stream_line("x"))
            outside = SCRATCH / "outside.jsonl"
            outside.write_text(stream_line("x"))
            cases = {
                "relative path": [("records/x.jsonl", "stream")],
                "outside the repository": [(str(outside), "stream")],
                "unknown kind": [(str(inside), "diary")],
                "the ledger itself": [(str(root / "outcomes.json"), "ledger")],
                "twice": [(str(inside), "stream"), (str(inside), "stream")],
                "missing file": [(str(root / "records" / "absent.jsonl"), "stream")],
                "dotted path": [(str(root / "records" / ".." / "records" / "x.jsonl"), "stream")],
            }
            head = git(root, "rev-parse", "HEAD")
            for why, listed in cases.items():
                with self.subTest(why):
                    repo = make_repo(drive, root, lambda rr, a, listed=listed: listed)
                    with self.assertRaises(drive.CommitRefused):
                        repo.commit_records(r, 1, outcome(r))
                    self.assertFalse((root / "outcomes.json").exists(), why)
            repo = make_repo(drive, root, lambda rr, a: [])
            for why, o in {"another slot": outcome(row(2)), "another attempt": outcome(r, attempt=2),
                           "a key missing": {k: v for k, v in outcome(r).items() if k != "mask"}}.items():
                with self.subTest(why):
                    with self.assertRaises(drive.CommitRefused):
                        repo.commit_records(r, 1, o)
                    self.assertFalse((root / "outcomes.json").exists(), why)
            self.assertEqual(git(root, "rev-parse", "HEAD"), head)


class TestHistoryAndRestart(unittest.TestCase):
    def test_c3_history_is_in_commit_order(self):
        self.assertEqual(c3_history(drive), [])

    def test_c4_a_leaked_container_still_present_refuses_the_restart(self):
        self.assertEqual(c4_restart(drive), [])

    def test_leaked_ids_come_from_the_committed_history_only(self):
        self.assertTrue(hasattr(drive, "TakeRepo"), "drive.py has no TakeRepo")
        with scratch_repo() as root:
            records = Records(root)
            repo = make_repo(drive, root, records)
            self.assertEqual(repo.leaked_ids(), [])
            r = row(1)
            repo.register(r, 1)
            repo.commit_records(r, 1, outcome(r, container_id=LEAKED, leaked_container=LEAKED,
                                               reason="leaked", stop="leaked"))
            self.assertEqual(make_repo(drive, root, records).leaked_ids(), [LEAKED])

    def test_a_listing_that_fails_refuses_the_restart_unread(self):
        self.assertTrue(hasattr(drive, "TakeRepo"), "drive.py has no TakeRepo")

        class Broken(FakeRuntime):
            def run(self, argv, env=None, timeout=None):
                self.calls.append(list(argv))
                return rt.Completed(1, "", "synthetic failure")
        with scratch_repo() as root:
            repo = make_repo(drive, root, Records(root), runtime=Broken())
            with self.assertRaises(rt.Refused):
                repo.register(row(1), 1)
            self.assertFalse((root / "takes.json").exists())


class TestFold(unittest.TestCase):
    """Review round 1's three MINORs (ruling W6E-close-1)."""
    def test_c7_the_same_slot_and_attempt_twice_refuses(self):
        self.assertEqual(c7_duplicate(drive), [])

    def test_c8_a_ledger_as_a_record_file_refuses(self):
        self.assertEqual(c8_reserved(drive), [])

    def test_c9_a_tracked_file_as_a_record_file_refuses(self):
        self.assertEqual(c9_tracked(drive), [])

    def test_c10_the_commit_is_the_checked_tree(self):
        self.assertEqual(c10_bound(drive), [])


class TestPreflightRoad(unittest.TestCase):
    def test_c6_the_driver_takes_s1s_entry_point(self):
        self.assertEqual(c6_preflight(drive), [])

    def test_drive_never_reads_a_lock_itself(self):
        src = Path(drive.__file__).read_text(encoding="utf-8")
        self.assertEqual(src.count("_preflight.collect_and_evaluate("), 1, "one road to preflight")
        for needle in ("image_lock", "LOCK_KEYS", "_preflight.evaluate(", "load_take_lock("):
            self.assertNotIn(needle, src, needle)


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
    name = "drive_w6e_witness"
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
    "omit-restage": ((("        _git_bytes(self.repo, \"add\", \"--\", *staged)\n", ""),), c1_restage, "C1-restage"),
    "omit-rehash": ((("            if hashlib.sha256(blob).hexdigest() != after.get(paths[name]):\n",
                      "            if False:\n"),), c2_rehash, "C2-rehash"),
    "concatenated-history": ((("        return takes_mod.read_history(root=self.root, repo=self.repo)\n",
                               "        return [e for f in takes_mod.HISTORY_FILES if (self.root / f).exists()\n"
                               "                for e in json.loads((self.root / f).read_text())]\n"),),
                             c3_history, "C3-history"),
    "omit-restart-refusal": ((("        self.refuse_restart()\n", ""),), c4_restart, "C4-restart"),
    # Two layers since the W6E-R1-3 fold, both off: the staged-set refusal before the scan, and the written tree's
    # change set before the commit (each alone still refuses the stray; neither is credited alone).
    "admit-stray-staged": ((("        if extra:\n            raise CommitRefused(",
                             "        if False:\n            raise CommitRefused("),
                            ("        if changed != sorted(declared):\n", "        if False:\n")), c5_staged, "C5-staged"),
    "bypass-entry-point": ((("    return _preflight.collect_and_evaluate(\n", "    return _preflight.evaluate(\n"),),
                           c6_preflight, "C6-preflight"),
    "admit-duplicate-outcome": ((("        if bad:\n            raise CommitRefused(\"the outcome cannot follow",
                                  "        if False:\n            raise CommitRefused(\"the outcome cannot follow"),),
                                c7_duplicate, "C7-duplicate"),
    "admit-reserved-names": ((("            if name in reserved:\n", "            if False:\n"),),
                             c8_reserved, "C8-reserved"),
    "admit-tracked-paths": ((("            if _git_bytes(self.repo, \"ls-tree\", \"--name-only\", \"HEAD\", \"--\", name)"
                              ".strip():\n", "            if False:\n"),), c9_tracked, "C9-tracked"),
    "commit-the-index": ((("        commit = self._bind(head, tree)\n",
                           "        with tempfile.NamedTemporaryFile(mode=\"w\", suffix=\".txt\") as message:\n"
                           "            message.write(COMMIT_SUBJECT + \"\\n\")\n"
                           "            message.flush()\n"
                           "            _git_bytes(self.repo, \"commit\", \"-q\", \"-F\", message.name)\n"
                           "        commit = _git_bytes(self.repo, \"rev-parse\", \"HEAD\").decode().strip()\n"),),
                         c10_bound, "C10-bound"),
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

    def test_witness_omit_restage(self):
        self.kill("omit-restage")

    def test_witness_omit_rehash(self):
        self.kill("omit-rehash")

    def test_witness_concatenated_history(self):
        self.kill("concatenated-history")

    def test_witness_omit_restart_refusal(self):
        self.kill("omit-restart-refusal")

    def test_witness_admit_stray_staged(self):
        self.kill("admit-stray-staged")

    def test_witness_bypass_entry_point(self):
        self.kill("bypass-entry-point")

    def test_witness_admit_duplicate_outcome(self):
        self.kill("admit-duplicate-outcome")

    def test_witness_admit_reserved_names(self):
        self.kill("admit-reserved-names")

    def test_witness_admit_tracked_paths(self):
        self.kill("admit-tracked-paths")

    def test_witness_commit_the_index(self):
        self.kill("commit-the-index")

    def test_the_witnesses_are_named_and_each_bound_to_its_own_check(self):
        self.assertEqual(sorted(WITNESSES), sorted(["omit-restage", "omit-rehash", "concatenated-history",
                                                    "omit-restart-refusal", "admit-stray-staged",
                                                    "bypass-entry-point", "admit-duplicate-outcome",
                                                    "admit-reserved-names", "admit-tracked-paths",
                                                    "commit-the-index"]))
        self.assertEqual(len({w[1].__name__ for w in WITNESSES.values()}), 10)
        self.assertEqual(len({w[2] for w in WITNESSES.values()}), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
