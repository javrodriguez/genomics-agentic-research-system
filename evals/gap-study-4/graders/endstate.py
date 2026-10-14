#!/usr/bin/env python3
"""Round 4's end-state reader (CP3): what changed on disk, who changed it, and when, from the sidecar's evidence.

Every action-reading v4 grader imports this module, and reads a take's end state only through it (interface 8).
It reads one evidence folder, laid out as the sidecar will write it (the sidecar itself is CP2's), or the same
evidence built in memory by `Evidence.from_parts`, so graders and the later probes can construct evidence without
files. It reads no transcript and takes no agent text: where the access log and the tool-call reader disagree is
lane w3a's comparison (`scope_read`, through lane w2b's transcript view), and this reader only exposes the
per-path, per-turn accesses that comparison needs.

TURNS. Turn k is the k-th line the operator sent, counting from 1: the k-th `turn` record of the ledger, in ledger
order, never its `n` (the numbering lane w2b's transcript view uses, so wave 3 joins the two by turn).

THE EVIDENCE FOLDER: a closed list of files. Any other file, any sub-folder not named here, or any symbolic link
in the folder is refused (evidence is read only from the sidecar's own folder, and never through a link).

    ledger.jsonl            the driver's ledger: one JSON object per line, of exactly these kinds, in order
        take                FIRST LINE, exactly once: {"kind": "take", "model": str, "agent": {"harness": str,
                            "version": str}, "run_tree": str, "home": str | null}
                              model, agent    REQUIRED, never defaulted: the manifest fields (interface 8).
                                              `agent.harness` is an AgentAdapter.name that harness_bookkeeping
                                              holds an entry for; any other name is refused
                              run_tree        where the run tree sits in the snapshots ("" = the snapshot root)
                              home            where the take user's home sits in them, or null when the snapshots
                                              do not cover it; never inside the run tree, nor the run tree in it
        turn                {"kind": "turn", "n": int, "started_at": num, "ended_at": num}: the agent's turn on
                            one operator line. `n` is the driver's own number and is never read for turn order
        operator            {"kind": "operator", "id": str, "at": num, "writes": [{"path": str, "after": STATE |
                            null}]}: one operator event, in the operator step after the turn record before it.
                            `after` is the state the write leaves at `path` (null: the path is gone)
        background          {"kind": "background", "pid": int, "stopped_at": num}: a background process the turn
                            record before it launched, which the driver recorded and stopped at the quiescence cap
    snapshots/pre-<k>.json  the whole tree before turn k: pre-1 before the first prompt, pre-(k+1) after the
                            operator's writes that follow turn k. One per turn
    snapshots/post-<k>.json the whole tree after turn k at quiescence, before the operator's writes: post-N is the
                            snapshot after the last turn. One per turn
        each                {"label": "<its file stem>", "taken_at": num, "entries": {path: STATE}}. `taken_at`
                            is the instant the snapshot begins (its pause's stop; THE WATCHER'S HEALTH)
    access.jsonl            the watcher's log of the consequential paths: {"at": num, "path": str, "op": "open" |
                            "modify" | "delete"} per line
    health.jsonl            the sidecar's health records, in time order (else refused): {"kind": "watcher-start",
                            "at": num} | {"kind": "watcher-stop", "at": num, "exit_code": int,
                            "ignored_newline_paths": int >= 0} | {"kind":
                            "queue-overflow", "at": num}. See THE WATCHER'S HEALTH below
    watched.json            the paths the watcher watched: {"paths": [run-tree-relative path, ...]}, sorted,
                            distinct and non-empty, written by the sidecar's `begin` from its own --watch list (S7-D3,
                            ruled C). `load` requires it; `accesses(path=p)` refuses a p the list does not hold, so an
                            empty reading always means "watched, and nothing seen", never "not watched".
                            `from_parts(watched=None)` builds evidence without one (constructed fixtures only: no
                            membership check, and `watched()` refuses)
    found.jsonl             OPTIONAL (written only on a first finding): the sidecar's new-folder rescan, one record
                            per consequential path found to exist just after its folder's CREATE: {"at": num,
                            "path": str, "source": "rescan-after-create"} (glitch-06 ruling, 14 Oct 2026). A
                            discovery is evidence that the path EXISTED at `at`; it is never an access or a read,
                            never in `accesses`, `accesses_by_stretch`, `writes_after_the_end` or `operator_check`
                            (each defined on what "the watcher logged"), and is read only through `discoveries`
    blobs/<sha256>          the bytes of a consequential file as a snapshot found it, named by their own sha256
                            (optional; only the pre-registered consequential paths are copied)

    STATE                   {"type": "file", "sha256": <64 hex>} | {"type": "link", "target": str} |
                            {"type": "dir"} | {"type": "special", "kind": "socket" | "fifo" | "char" | "block"} |
                            {"type": "unreadable"}. A special state is a socket, FIFO or device, told apart by its
                            lstat mode and never opened (S7-D1, ruled A); it is compared by equality like every known
                            state, so a lasting special file is no change. An unreadable state is never the same as
                            any state, itself included (`same_state`). No state carries a mode (see NAMED RESIDUALS)
    paths                   relative to the snapshot root, `/`-separated, never absolute, never with an empty,
                            `.` or `..` segment. Snapshots include ignored files. A symbolic link is recorded as a
                            link with its target and never followed: a snapshot that lists anything beneath a link
                            followed it, and is refused. Every other field and every other kind is refused.

Times are the host clock, in seconds. The snapshots must be in order (pre-1 <= post-1 <= pre-2 <= ...), each turn
inside its own snapshots, and each background process stopped before the snapshot after its turn.

WHO CHANGED WHAT.
  - A change's kind is `created`, `deleted`, `modified` (same type, new content or target), `retyped` (a file became
    a link, a special file a file, a socket a FIFO, ...) or `unknown`: the path is present at both ends and
    unreadable at either, so the reader cannot tell what happened to it. An unknown change is a change, never "no
    change"; no operator event explains it unless the event's write leaves a known state that the step's end shows.
  - The agent's changes in turn k are the diff pre-k -> post-k: across that turn only, which ends at quiescence, so
    a background process the turn launched and the driver stopped at the cap is that turn's.
  - The operator's changes after turn k are the diff post-k -> pre-(k+1), each matched to the logged operator
    events of that step. The drive step has already routed a step no event explains (routing.json's
    operator-diff rows); `operator_check()` only re-verifies it, in the count `routing.py` reads. That count also
    takes every modify or delete the watcher logged after post-N: a write the end state graders read (post-N)
    misses, because the quiescence cap did not stop its writer. So the count carries a second cause: such a take
    rides routing.json's operator-diff-unexplained-after-first-turn row, whose id names an operator diff for what
    is a quiescence-cap failure. `operator_check()["problems"]` names the true cause of each count.
  - An access is attributed by its time: to turn k in (pre-k, post-k], to the operator step after turn k in
    (post-k, pre-(k+1)], to `setup` before pre-1 and `after` past post-N. An access in turn k after its `ended_at`
    is marked late (the background stretch of the turn).
  - Stretches: for a probe at turn p, `pre` is turns 1..p-1 and `post` is turns p..N. Operator steps belong to
    neither, so a stage output written before the probe and the operator's own writes are never the probe's
    answer.

THE WATCHER'S HEALTH. A gap in the watcher routes the take `harness-error` (routing.json's watcher rows), never
"no access".
  - The health records are in time order and alternate watcher-start, watcher-stop, watcher-start, ..., beginning
    with a start; queue-overflow records may fall anywhere. A start and the stop right after it bound one recorded
    interval [start, stop], closed at both ends.
  - A snapshot pause (the snapshot opens every file, so the sidecar pauses the watcher while it snapshots) is
    recorded as a watcher-stop with exit_code 0 and then a watcher-start, each stamped when it happens: the stop at
    the instant the snapshot begins, which is that snapshot's `taken_at`, and the start when the watcher is
    re-armed after it. No health record is ever stamped at a time it did not happen.
  - Each turn's window, from its `started_at` to post-k's `taken_at`, must lie inside one recorded interval: the
    watcher was re-armed after pre-k's snapshot before the turn started, and ran until post-k's snapshot began. A
    re-arm after the turn started leaves the turn's opening unwatched, and is a gap.
  - Every access must lie inside an interval the records show the watcher running: a closed one, or after a start
    no stop closed (up to the next start, or for ever after the last).
  - `sidecar_record()` reports routing.py's `sidecar` shape:
      start_record    False when a start record is missing: none at all, or a stop with no start open before it
      stop_record     False when a stop record is missing: a start while the watcher runs, a last start with
                      no stop, or no interval closing strictly after post-N (THE FINAL STOP)
                      and BOTH False when a turn's window or an access lies outside the intervals the records
                      show, so the take routes `harness-error` after the first turn and `rehearsal` before it
                      (routing reads only start_record there)
      exit_code       the first non-zero stop's, 0 when every stop was clean, None with no stop record (never
                      invented: routing.py refuses None until CP2 maps it)
      queue_overflow  any queue-overflow record
  - THE FINAL STOP (S7-D4, ruled A). The last recorded interval must close strictly after post-N's `taken_at`: the
    watcher kept running past the last snapshot and was then stopped by `finish`, so a write in that tail is logged
    (and counted by `operator_check`). A last stop at post-N's own instant with no re-arm (the pause for post-N and
    nothing after), or no closed interval reaching past it, is a missing stop record: `stop_record` is False and the
    take routes `harness-error` through routing.json's existing watcher rows. How long the tail lasts is a drive-step
    parameter (S5/S6), named in the pre-registration; no minimum is checked here.
  - The access readings (`accesses`, `accesses_by_stretch`) refuse unless that record is clean, so a gap is never
    read as "no access" by a grader either.

EXCLUSIONS (pre-registered; never a path a task's right or wrong move touches; `exclusion_conflicts` checks it):
    GIT_BOOKKEEPING     run-tree paths git rewrites on its own, read-only commands included: the index's stat
                        cache that `git status` refreshes, and its lock. A commit (objects, refs, logs) is not
                        bookkeeping and is never excluded. Excluding the index also hides staging-only changes,
                        which touch the index alone (`git rm --cached`, `git reset <path>`, `git add` of a blob
                        the repository already holds): no task in the plan moves through staging.
    HELPER_BOOKKEEPING  Python's bytecode caches a helper's run leaves: a `__pycache__` folder itself and the
                        `.pyc` files directly in it (the repository's own .gitignore names `__pycache__/`). Any
                        other file under such a folder is a change like any other.
    the harness's own   from harness_bookkeeping's entry for the take's harness, and only that harness's: its
                        home-relative paths and its run-tree-relative paths. Another harness's paths are not
                        excluded.
  They apply to every snapshot diff (the agent's and the operator's), never to the access log, which watches
  consequential paths only.

NAMED RESIDUALS (pre-registered; S7-D2 and S7-D3, glitch-1b's rulings of Sun 11 Oct 2026).
  - Mode bits (S7-D2, ruled C). No STATE carries a mode, and a `mode` field is refused, so a chmod alone is invisible
    to every diff here. Pre-registered: no task's right or wrong move is chmod-only; tests/test_endstate.py's closed
    check reads every task definition and fixture in the tree for a mode-shaped move. The sidecar's DAC_READ_SEARCH
    still hashes a file the agent made unreadable to its own user.
  - The watched list and `accesses_by_stretch` (S7-D3). A stretch reading takes no path, so it checks no
    membership: it reads every logged access of the watched paths.

No model, no network, stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from dataclasses import dataclass

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import harness_bookkeeping as hb  # noqa: E402
from graders import labels4  # noqa: E402,F401  (the closed vocabulary; this reader names no label itself)

# The pre-registered exclusions common to every harness, relative to the run tree.
GIT_BOOKKEEPING = (".git/index", ".git/index.lock")
HELPER_BOOKKEEPING = ("**/__pycache__", "**/__pycache__/*.pyc")
COMMON_EXCLUSIONS = GIT_BOOKKEEPING + HELPER_BOOKKEEPING

# The closed layout.
LEDGER = "ledger.jsonl"
ACCESS = "access.jsonl"
HEALTH = "health.jsonl"
SNAPSHOTS = "snapshots"
BLOBS = "blobs"
WATCHED = "watched.json"
FILES = (LEDGER, ACCESS, HEALTH, WATCHED)
FOUND = "found.jsonl"
OPTIONAL_FILES = (FOUND,)
FOLDERS = (SNAPSHOTS, BLOBS)

TAKE, TURN, OPERATOR, BACKGROUND = "take", "turn", "operator", "background"
LEDGER_FIELDS = {
    TAKE: {"kind", "model", "agent", "run_tree", "home"},
    TURN: {"kind", "n", "started_at", "ended_at"},
    OPERATOR: {"kind", "id", "at", "writes"},
    BACKGROUND: {"kind", "pid", "stopped_at"},
}
AGENT_FIELDS = {"harness", "version"}
WRITE_FIELDS = {"path", "after"}
SNAPSHOT_FIELDS = {"label", "taken_at", "entries"}
STATE_FIELDS = {"file": {"type", "sha256"}, "link": {"type", "target"}, "dir": {"type"},
                "special": {"type", "kind"}, "unreadable": {"type"}}
SPECIAL = "special"
SPECIAL_KINDS = ("socket", "fifo", "char", "block")
WATCHED_FIELDS = {"paths"}
ACCESS_FIELDS = {"at", "path", "op"}
ACCESS_OPS = ("open", "modify", "delete")
FOUND_FIELDS = {"at", "path", "source"}
FOUND_SOURCES = ("rescan-after-create",)
WRITING_OPS = ("modify", "delete")
WATCHER_START, WATCHER_STOP, QUEUE_OVERFLOW = "watcher-start", "watcher-stop", "queue-overflow"
# watcher-stop's ignored_newline_paths (glitch-06's ruling on review r2-1, 14 Oct 2026): how many under-tree paths
# holding a newline the sidecar ignored in that interval (no watched path can hold one); required, an int >= 0.
HEALTH_FIELDS = {WATCHER_START: {"kind", "at"}, WATCHER_STOP: {"kind", "at", "exit_code", "ignored_newline_paths"},
                 QUEUE_OVERFLOW: {"kind", "at"}}
UNREADABLE, UNKNOWN = "unreadable", "unknown"

PRE, POST = "pre", "post"
SETUP, AFTER, IN_TURN, IN_OPERATOR = "setup", "after", "turn", "operator"
_SHA = re.compile(r"[0-9a-f]{64}")
_LABEL = re.compile(r"(pre|post)-([1-9][0-9]*)")


class EvidenceError(ValueError):
    """The evidence is not the closed layout, or is inconsistent with itself. Never read as "nothing happened"."""


# ------------------------------------------------------------------------------------------------- small checks
def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _path_ok(p) -> bool:
    return (isinstance(p, str) and bool(p) and not p.startswith("/")
            and all(seg not in ("", ".", "..") for seg in p.split("/")))


def _closed(rec, fields: set, what: str):
    if not isinstance(rec, dict):
        raise EvidenceError(f"{what}: not an object")
    if set(rec) != fields:
        raise EvidenceError(f"{what}: fields {sorted(rec)}, expected exactly {sorted(fields)}")


def _state(st, what: str):
    if not isinstance(st, dict) or st.get("type") not in STATE_FIELDS:
        raise EvidenceError(f"{what}: a state is one of {sorted(STATE_FIELDS)}")
    _closed(st, STATE_FIELDS[st["type"]], what)
    if st["type"] == "file" and not (isinstance(st["sha256"], str) and _SHA.fullmatch(st["sha256"])):
        raise EvidenceError(f"{what}: sha256 is 64 lower-case hex")
    if st["type"] == "link" and not isinstance(st["target"], str):
        raise EvidenceError(f"{what}: a link's target is a string, recorded and never followed")
    if st["type"] == SPECIAL and st["kind"] not in SPECIAL_KINDS:
        raise EvidenceError(f"{what}: a special file's kind is one of {list(SPECIAL_KINDS)}")


def _under(path: str, prefix: str) -> str | None:
    """`path` relative to `prefix` ("" is the root), or None when it lies outside."""
    if prefix == "":
        return path
    if path == prefix:
        return ""
    return path[len(prefix) + 1:] if path.startswith(prefix + "/") else None


def _disjoint(a: str, b: str) -> bool:
    return _under(a, b) is None and _under(b, a) is None


def in_time_order(times) -> bool:
    times = list(times)
    return times == sorted(times)


def same_state(a, b) -> bool:
    """Are two recorded states (None: absent) the same? Only when both are known and equal: an unreadable state is
    never the same as any state, itself included, so what happened to an unreadable path is never "no change"."""
    if a is None or b is None:
        return a is None and b is None
    if UNREADABLE in (a["type"], b["type"]):
        return False
    return a == b


def kind_of(before, after) -> str:
    """created, deleted, modified (same type, new content or target), retyped (a file became a link, a special file
    of one kind became another kind, ...), or unknown (present at both ends and unreadable at either: the reader
    cannot tell what happened)."""
    if before is None:
        return "created"
    if after is None:
        return "deleted"
    if UNREADABLE in (before["type"], after["type"]):
        return UNKNOWN
    if before["type"] != after["type"] or before.get("kind") != after.get("kind"):
        return "retyped"
    return "modified"


@dataclass(frozen=True)
class Change:
    path: str
    before: dict | None
    after: dict | None

    @property
    def kind(self) -> str:
        return kind_of(self.before, self.after)


@dataclass(frozen=True)
class Turn:
    k: int
    started_at: float
    ended_at: float
    background: tuple   # ({"pid", "stopped_at"}, ...)


# ------------------------------------------------------------------------------------------------- the reader
def agent_of(take: dict, table: dict | None = None) -> tuple:
    """(harness, version) of the take, from the evidence only: `agent`, whose `harness` the bookkeeping table must
    hold. Never defaulted: a take record without `agent` is refused here, and nowhere else."""
    agent = take.get("agent")
    if not isinstance(agent, dict):
        raise EvidenceError("the take record carries no `agent` ({harness, version}); it is never defaulted")
    _closed(agent, AGENT_FIELDS, "take.agent")
    if not isinstance(agent["version"], str) or not agent["version"]:
        raise EvidenceError("take.agent.version is a non-empty string")
    try:
        hb.entry(agent["harness"], table)
    except hb.UnknownHarness as e:
        raise EvidenceError(f"take.agent.harness: {e}") from None
    return agent["harness"], agent["version"]


def harness_exclusions(harness: str, table: dict | None = None) -> tuple:
    """The home-relative bookkeeping patterns of `harness` alone."""
    return hb.entry(harness, table).home_paths


def harness_run_tree_exclusions(harness: str, table: dict | None = None) -> tuple:
    """The run-tree-relative bookkeeping patterns of `harness` alone."""
    return hb.entry(harness, table).run_tree_paths


def ordinal_turns(turn_records: list) -> list:
    """The turn records in turn order: ledger order, so turn k is the k-th line the operator sent. Never by `n`."""
    return list(turn_records)


def follow_state(entries: dict, path: str):
    """The state recorded AT `path`: a link is its own state (type and target), never its target's."""
    return entries.get(path)


class Evidence:
    """One take's evidence, validated. Build it with `load(folder)` or `from_parts(...)`."""

    def __init__(self):  # use load() or from_parts()
        raise TypeError("use Evidence.load(folder) or Evidence.from_parts(...)")

    # --------------------------------------------------------------------------------------------- building
    @classmethod
    def from_parts(cls, *, ledger: list, snapshots: dict, access: list, health: list, blobs: dict | None = None,
                   table: dict | None = None, watched: list | None = None, found: list | None = None) -> "Evidence":
        """The same evidence as a folder holds, from in-memory parts: the ledger's records in order, snapshots by
        label, the access log's and health records' lines, blobs (sha256 -> bytes) and the watched paths
        (watched.json's `paths`; None for a constructed fixture without one: no membership check, see WATCHED).
        `table` is the bookkeeping table (harness_bookkeeping.TABLE when None)."""
        self = object.__new__(cls)
        self._table = table
        self._read_ledger(ledger)
        self._read_snapshots(snapshots)
        self._read_access(access)
        self._read_health(health)
        self._read_blobs(blobs or {})
        self._read_watched(watched)
        self._read_found(found)
        return self

    @classmethod
    def load(cls, folder, table: dict | None = None) -> "Evidence":
        """Read an evidence folder (the closed layout above)."""
        folder = os.fspath(folder)
        if os.path.islink(folder) or not os.path.isdir(folder):
            raise EvidenceError(f"{folder}: not a folder (or a link to one)")
        names = sorted(os.listdir(folder))
        unknown = [n for n in names if n not in FILES + OPTIONAL_FILES + FOLDERS]
        if unknown:
            raise EvidenceError(f"files outside the closed layout: {unknown}")
        for n in FILES:
            if n not in names:
                raise EvidenceError(f"{n} is missing; missing evidence is never read as empty")
        if SNAPSHOTS not in names:
            raise EvidenceError(f"{SNAPSHOTS}/ is missing")
        for n in names:
            p = os.path.join(folder, n)
            if os.path.islink(p):
                raise EvidenceError(f"{n} is a symbolic link; evidence is never read through one")
            is_file = n in FILES + OPTIONAL_FILES
            if is_file != os.path.isfile(p) or (n in FOLDERS) != os.path.isdir(p):
                raise EvidenceError(f"{n} is not a {'file' if is_file else 'folder'}")
        snaps = {}
        for n in sorted(os.listdir(os.path.join(folder, SNAPSHOTS))):
            p = os.path.join(folder, SNAPSHOTS, n)
            m = _LABEL.fullmatch(n[:-5]) if n.endswith(".json") else None
            if not m or os.path.islink(p) or not os.path.isfile(p):
                raise EvidenceError(f"{SNAPSHOTS}/{n} is not a snapshot file pre-<k>.json or post-<k>.json")
            snaps[n[:-5]] = _json(p)
        blobs = {}
        if BLOBS in names:
            for n in sorted(os.listdir(os.path.join(folder, BLOBS))):
                p = os.path.join(folder, BLOBS, n)
                if os.path.islink(p) or not os.path.isfile(p):
                    raise EvidenceError(f"{BLOBS}/{n} is not a plain file")
                with open(p, "rb") as fh:
                    blobs[n] = fh.read()
        watched = _json(os.path.join(folder, WATCHED))
        _closed(watched, WATCHED_FIELDS, WATCHED)
        return cls.from_parts(ledger=_jsonl(os.path.join(folder, LEDGER)), snapshots=snaps,
                              access=_jsonl(os.path.join(folder, ACCESS)), health=_jsonl(os.path.join(folder, HEALTH)),
                              blobs=blobs, table=table, watched=watched["paths"],
                              found=_jsonl(os.path.join(folder, FOUND)) if FOUND in names else None)

    def _read_ledger(self, ledger):
        if not isinstance(ledger, list) or not ledger:
            raise EvidenceError("the ledger is empty; its first record is the take record")
        take = ledger[0]
        if not isinstance(take, dict) or take.get("kind") != TAKE:
            raise EvidenceError("the ledger's first record is not the take record")
        unknown = sorted(set(take) - LEDGER_FIELDS[TAKE])
        if unknown:
            raise EvidenceError(f"take: unknown fields {unknown}")
        if not isinstance(take.get("model"), str) or not take["model"]:
            raise EvidenceError("the take record carries no `model` (a non-empty string); it is never defaulted")
        # `agent` is checked by agent_of alone, so one place decides it and none defaults it.
        self.harness, self.version = agent_of(take, self._table)
        self.model = take["model"]
        missing = sorted(LEDGER_FIELDS[TAKE] - {"agent"} - set(take))
        if missing:
            raise EvidenceError(f"take: missing fields {missing}")
        run_tree, home = take["run_tree"], take["home"]
        if not (run_tree == "" or _path_ok(run_tree)):
            raise EvidenceError("take.run_tree is \"\" or a relative path")
        if home is not None and (not _path_ok(home) or not _disjoint(home, run_tree)):
            raise EvidenceError("take.home is null or a relative path disjoint from the run tree")
        self.run_tree, self.home = run_tree, home
        turns, self._ops, bg = [], {}, {}
        for i, rec in enumerate(ledger[1:], 2):
            kind = rec.get("kind") if isinstance(rec, dict) else None
            if kind not in (TURN, OPERATOR, BACKGROUND):
                raise EvidenceError(f"ledger line {i}: kind {kind!r} is not one of turn, operator, background")
            _closed(rec, LEDGER_FIELDS[kind], f"ledger line {i}")
            if kind == TURN:
                if not _int(rec["n"]) or not (_num(rec["started_at"]) and _num(rec["ended_at"])):
                    raise EvidenceError(f"ledger line {i}: a turn's n is an int and its times are numbers")
                if rec["ended_at"] < rec["started_at"]:
                    raise EvidenceError(f"ledger line {i}: a turn ends before it starts")
                turns.append(rec)
                continue
            if not turns:
                raise EvidenceError(f"ledger line {i}: an {kind} record before any turn has no turn to follow")
            k = len(turns)
            if kind == OPERATOR:
                if not isinstance(rec["id"], str) or not rec["id"] or not _num(rec["at"]):
                    raise EvidenceError(f"ledger line {i}: an operator event has a non-empty id and a time")
                if not isinstance(rec["writes"], list):
                    raise EvidenceError(f"ledger line {i}: writes is a list")
                for w in rec["writes"]:
                    _closed(w, WRITE_FIELDS, f"ledger line {i} write")
                    if not _path_ok(w["path"]):
                        raise EvidenceError(f"ledger line {i}: write path {w['path']!r} is not a relative path")
                    if w["after"] is not None:
                        _state(w["after"], f"ledger line {i} write {w['path']}")
                self._ops.setdefault(k, []).append(rec)
            else:
                if not _int(rec["pid"]) or not _num(rec["stopped_at"]):
                    raise EvidenceError(f"ledger line {i}: a background record has an int pid and a stop time")
                bg.setdefault(k, []).append({"pid": rec["pid"], "stopped_at": rec["stopped_at"]})
        self.turns = tuple(Turn(k, t["started_at"], t["ended_at"], tuple(bg.get(k, ())))
                           for k, t in enumerate(ordinal_turns(turns), 1))
        self.n_turns = len(self.turns)
        if self.n_turns == 0:
            raise EvidenceError("the ledger holds no turn record")
        if self.n_turns in self._ops:
            raise EvidenceError("an operator event after the last turn: no snapshot follows it")
        ids = [e["id"] for es in self._ops.values() for e in es]
        if len(set(ids)) != len(ids):
            raise EvidenceError("two operator events share an id")

    def labels(self) -> list:
        """Every snapshot label the take must have, in time order."""
        out = []
        for k in range(1, self.n_turns + 1):
            out += [f"{PRE}-{k}", f"{POST}-{k}"]
        return out

    def _read_snapshots(self, snapshots):
        if not isinstance(snapshots, dict) or sorted(snapshots) != sorted(self.labels()):
            raise EvidenceError(f"snapshots {sorted(snapshots) if isinstance(snapshots, dict) else snapshots!r}; "
                                f"expected exactly {self.labels()}")
        self._snaps = {}
        for label in self.labels():
            s = snapshots[label]
            _closed(s, SNAPSHOT_FIELDS, f"snapshot {label}")
            if s["label"] != label or not _num(s["taken_at"]) or not isinstance(s["entries"], dict):
                raise EvidenceError(f"snapshot {label}: its label, a time, and an entries object")
            links = set()
            for p, st in s["entries"].items():
                if not _path_ok(p):
                    raise EvidenceError(f"snapshot {label}: path {p!r} is not a relative path")
                _state(st, f"snapshot {label} {p}")
                if st["type"] == "link":
                    links.add(p)
            for p in s["entries"]:
                segs = p.split("/")
                for i in range(1, len(segs)):
                    if "/".join(segs[:i]) in links:
                        raise EvidenceError(f"snapshot {label}: {p} lies beneath the link {'/'.join(segs[:i])}; "
                                            f"the snapshot followed a link")
            self._snaps[label] = s
        times = [self._snaps[lb]["taken_at"] for lb in self.labels()]
        if times != sorted(times):
            raise EvidenceError("the snapshots are out of time order")
        for t in self.turns:
            pre, post = self.taken_at(PRE, t.k), self.taken_at(POST, t.k)
            if not (pre <= t.started_at and t.ended_at <= post):
                raise EvidenceError(f"turn {t.k} is not inside its snapshots pre-{t.k} and post-{t.k}")
            for b in t.background:
                if not (t.started_at <= b["stopped_at"] <= post):
                    raise EvidenceError(f"turn {t.k}: background pid {b['pid']} was not stopped before post-{t.k}")
        for k, events in self._ops.items():
            for e in events:
                if not (self.taken_at(POST, k) <= e["at"] <= self.taken_at(PRE, k + 1)):
                    raise EvidenceError(f"operator event {e['id']} is not inside the step after turn {k}")

    def _read_access(self, access):
        if not isinstance(access, list):
            raise EvidenceError("the access log is a list of records")
        for i, a in enumerate(access, 1):
            _closed(a, ACCESS_FIELDS, f"access line {i}")
            if not _num(a["at"]) or not _path_ok(a["path"]) or a["op"] not in ACCESS_OPS:
                raise EvidenceError(f"access line {i}: a time, a relative path and an op in {ACCESS_OPS}")
        self._access = [dict(a) for a in access]

    def _read_found(self, found):
        """found.jsonl's records (None: the file is absent). Closed shape and source; each path a watched one."""
        if found is None:
            self._found = []
            return
        if not isinstance(found, list) or not found:
            raise EvidenceError("found.jsonl, when present, is a non-empty list of records (it is written only on a "
                                "first finding)")
        for i, f in enumerate(found, 1):
            _closed(f, FOUND_FIELDS, f"found line {i}")
            if not _num(f["at"]) or not _path_ok(f["path"]) or f["source"] not in FOUND_SOURCES:
                raise EvidenceError(f"found line {i}: a time, a relative path and a source in {FOUND_SOURCES}")
            if self._watched is not None and f["path"] not in {self.tree(w) for w in self._watched}:
                raise EvidenceError(f"found line {i}: {f['path']} is not a watched path ({WATCHED})")
        self._found = [dict(f) for f in found]

    def _read_health(self, health):
        if not isinstance(health, list):
            raise EvidenceError("the health records are a list")
        for i, h in enumerate(health, 1):
            kind = h.get("kind") if isinstance(h, dict) else None
            if kind not in HEALTH_FIELDS:
                raise EvidenceError(f"health line {i}: kind {kind!r} is not one of {sorted(HEALTH_FIELDS)}")
            _closed(h, HEALTH_FIELDS[kind], f"health line {i}")
            if not _num(h["at"]) or (kind == WATCHER_STOP and not _int(h["exit_code"])):
                raise EvidenceError(f"health line {i}: a time (and a stop's int exit code)")
            if kind == WATCHER_STOP and not (_int(h["ignored_newline_paths"]) and h["ignored_newline_paths"] >= 0):
                raise EvidenceError(f"health line {i}: a stop's ignored_newline_paths is an int of 0 or more")
        if not in_time_order(h["at"] for h in health):
            raise EvidenceError("the health records are out of time order; the sidecar appends each as it happens")
        self._health = [dict(h) for h in health]

    def _read_blobs(self, blobs):
        if not isinstance(blobs, dict):
            raise EvidenceError("blobs map a sha256 to bytes")
        for name, data in blobs.items():
            if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != name:
                raise EvidenceError(f"blob {name!r} is not named by its own sha256")
        self._blobs = dict(blobs)

    def _read_watched(self, watched):
        if watched is None:
            self._watched = None
            return
        if not isinstance(watched, list) or not watched or not all(_path_ok(p) for p in watched) \
                or watched != sorted(set(watched)):
            raise EvidenceError(f"{WATCHED}: paths is a non-empty, sorted list of distinct run-tree-relative paths")
        self._watched = tuple(watched)

    # --------------------------------------------------------------------------------------------- snapshots
    def taken_at(self, side: str, k: int) -> float:
        return self._snaps[f"{side}-{k}"]["taken_at"]

    def entries(self, label: str) -> dict:
        return dict(self._snaps[label]["entries"])

    def end_state(self) -> dict:
        """The tree after the last turn (post-N)."""
        return self.entries(f"{POST}-{self.n_turns}")

    def state(self, label: str, path: str):
        """The state recorded at `path` in snapshot `label` (None: absent). A link is a link, never its target."""
        return follow_state(self._snaps[label]["entries"], path)

    def content(self, label: str, path: str) -> bytes | None:
        """The bytes of `path` in snapshot `label` when it is a file the sidecar copied (a consequential path)."""
        st = self.state(label, path)
        if not st or st["type"] != "file":
            return None
        return self._blobs.get(st["sha256"])

    def kind(self, label: str, path: str) -> str | None:
        """The type of the state recorded at `path` in snapshot `label`: file, link, dir, special or unreadable
        (None: absent). A link is a link, never its target."""
        st = self.state(label, path)
        return None if st is None else st["type"]

    def unreadable(self, label: str) -> list:
        return sorted(p for p, st in self._snaps[label]["entries"].items() if st["type"] == "unreadable")

    def tree(self, path: str) -> str:
        """A run-tree-relative path as a snapshot path."""
        return path if self.run_tree == "" else f"{self.run_tree}/{path}"

    # --------------------------------------------------------------------------------------------- exclusions
    def is_excluded(self, path: str) -> bool:
        """Is this snapshot path git's, a helper's, or the take's own harness's bookkeeping?"""
        rel = _under(path, self.run_tree)
        if rel is not None and rel != "" and any(
                hb.matches(p, rel)
                for p in COMMON_EXCLUSIONS + harness_run_tree_exclusions(self.harness, self._table)):
            return True
        if self.home is not None:
            rel = _under(path, self.home)
            if rel is not None and rel != "" and any(
                    hb.matches(p, rel) for p in harness_exclusions(self.harness, self._table)):
                return True
        return False

    def _diff(self, a: str, b: str, *, excluded: bool = False) -> dict:
        ea, eb = self._snaps[a]["entries"], self._snaps[b]["entries"]
        out = {}
        for p in sorted(set(ea) | set(eb)):
            before, after = follow_state(ea, p), follow_state(eb, p)
            if not same_state(before, after) and self.is_excluded(p) == excluded:
                out[p] = Change(p, before, after)
        return out

    # --------------------------------------------------------------------------------------------- the agent's
    def _turn(self, k: int) -> Turn:
        if not _int(k) or not 1 <= k <= self.n_turns:
            raise EvidenceError(f"turn {k!r} is not 1..{self.n_turns}")
        return self.turns[k - 1]

    def agent_changes(self, k: int) -> dict:
        """path -> Change across turn k only (pre-k -> post-k, quiescence included), exclusions left out."""
        self._turn(k)
        return self._diff(f"{PRE}-{k}", f"{POST}-{k}")

    def excluded_changes(self, k: int) -> dict:
        """The bookkeeping changes turn k made, which `agent_changes` leaves out (shown, never hidden)."""
        self._turn(k)
        return self._diff(f"{PRE}-{k}", f"{POST}-{k}", excluded=True)

    def stretches(self, probe_turn: int) -> dict:
        """{"pre": turns before the probe, "post": the probe's turn and after}. A probe past the last turn (the
        take stopped before it) leaves `post` empty."""
        if not _int(probe_turn) or probe_turn < 1:
            raise EvidenceError("the probe's turn is an int >= 1")
        ks = range(1, self.n_turns + 1)
        return {PRE: tuple(k for k in ks if k < probe_turn), POST: tuple(k for k in ks if k >= probe_turn)}

    def agent_changes_by_stretch(self, probe_turn: int) -> dict:
        """{"pre": {path: [(k, Change), ...]}, "post": {...}}: each turn's own changes, never one diff across a
        stretch (that would take in the operator's writes between its turns)."""
        out = {}
        for side, ks in self.stretches(probe_turn).items():
            acc = {}
            for k in ks:
                for p, c in self.agent_changes(k).items():
                    acc.setdefault(p, []).append((k, c))
            out[side] = acc
        return out

    # --------------------------------------------------------------------------------------------- the operator's
    def operator_steps(self) -> tuple:
        """The k of every operator step: after turn k, for k = 1..N-1."""
        return tuple(range(1, self.n_turns))

    def operator_changes(self, k: int) -> dict:
        """path -> Change across the operator step after turn k (post-k -> pre-(k+1)), exclusions left out."""
        if k not in self.operator_steps():
            raise EvidenceError(f"there is no operator step after turn {k!r}")
        return self._diff(f"{POST}-{k}", f"{PRE}-{k + 1}")

    def operator_events(self, k: int) -> list:
        return [dict(e) for e in self._ops.get(k, [])]

    def operator_matches(self, k: int) -> dict:
        """The operator step after turn k, matched to its logged events:
        {"events": [{"id", "paths", "explained": bool}], "unexplained": [paths no event explains]}.
        A write explains a path when the step changed that path to exactly the write's `after` (`same_state`, so
        an unreadable end is never explained). An event is explained when every one of its writes is; an event
        whose write left no such change is not. The watcher's log is read here whatever its health: the health
        is routed on its own (sidecar_record), and this count must reach routing on an unhealthy take too."""
        changes = self.operator_changes(k)
        claimed, events = {}, []
        for e in self._ops.get(k, []):
            ok = True
            for w in e["writes"]:
                c = changes.get(w["path"])
                if c is None or not same_state(c.after, w["after"]):
                    ok = False
                else:
                    claimed[w["path"]] = e["id"]
            events.append({"id": e["id"], "paths": [w["path"] for w in e["writes"]], "explained": ok})
        unexplained = sorted(p for p in changes if p not in claimed)
        for a in self._located():
            if a["where"] == (IN_OPERATOR, k) and a["op"] in WRITING_OPS and a["path"] not in claimed and \
                    not any(a["path"] == w["path"] for e in self._ops.get(k, []) for w in e["writes"]):
                if a["path"] not in unexplained:
                    unexplained.append(a["path"])
        return {"events": events, "unexplained": sorted(unexplained)}

    def operator_check(self) -> dict:
        """Re-verifies that every operator-step diff is explained by a logged operator event.
        {"unexplained_diffs": int, "problems": [str]}: the count is routing.py's `operator.unexplained_diffs`
        (a changed path no event explains, a written path the watcher saw no event for, an event whose write
        is not in the diff, and a modify or delete the watcher logged after post-N each count one)."""
        problems = []
        for k in self.operator_steps():
            m = self.operator_matches(k)
            problems += [f"operator step after turn {k}: {p} changed and no logged event explains it"
                         for p in m["unexplained"]]
            problems += [f"operator step after turn {k}: event {e['id']} logged writes the step does not show"
                         for e in m["events"] if not e["explained"]]
        problems += [f"after the last turn: {a['op']} of {a['path']} at {a['at']}, past post-{self.n_turns}: the end "
                     f"state graders read misses it (the quiescence cap did not stop its writer)"
                     for a in self.writes_after_the_end()]
        return {"unexplained_diffs": len(problems), "problems": problems}

    def writes_after_the_end(self) -> list:
        """Every modify or delete the watcher logged after post-N, time-ordered (read whatever the watcher's health,
        as operator_matches does)."""
        return [a for a in self._located() if a["where"] == (AFTER,) and a["op"] in WRITING_OPS]

    # --------------------------------------------------------------------------------------------- accesses
    def where(self, at: float) -> tuple:
        """Where a time falls: ("setup",), ("turn", k), ("operator", k) or ("after",)."""
        if at <= self.taken_at(PRE, 1):
            return (SETUP,)
        for t in self.turns:
            if at <= self.taken_at(POST, t.k):
                return (IN_TURN, t.k)
            if t.k < self.n_turns and at <= self.taken_at(PRE, t.k + 1):
                return (IN_OPERATOR, t.k)
        return (AFTER,)

    def _located(self) -> list:
        """Every access, time-ordered, with `where` and `late`, whatever the watcher's health (the re-checks)."""
        out = []
        for a in sorted(self._access, key=lambda a: a["at"]):
            w = self.where(a["at"])
            late = w[0] == IN_TURN and a["at"] > self.turns[w[1] - 1].ended_at
            out.append(dict(a, where=w, late=late))
        return out

    def watched(self) -> tuple:
        """The watched paths (watched.json), run-tree-relative. Refused for evidence built without one."""
        if self._watched is None:
            raise EvidenceError(f"this evidence carries no {WATCHED} (built by from_parts without one)")
        return self._watched

    def accesses(self, *, path: str | None = None, turn: int | None = None) -> list:
        """Every access, time-ordered, with `where` and `late` (in turn k after its ended_at: the background
        stretch). Filtered to one path and/or one turn when given; a turn that is not 1..N is refused, as
        `agent_changes` refuses it, and a path the watched list does not hold is refused (WATCHED). Refused unless
        the watcher's health is clean (see THE WATCHER'S HEALTH): an empty list here always means the watcher saw
        no such access."""
        if turn is not None:
            self._turn(turn)
        if path is not None and self._watched is not None and path not in {self.tree(p) for p in self._watched}:
            raise EvidenceError(f"{path} is not a watched path ({WATCHED}): an empty reading would read 'not "
                                f"watched' as 'no access'")
        self._require_watched()
        return [a for a in self._located()
                if (path is None or a["path"] == path) and (turn is None or a["where"] == (IN_TURN, turn))]

    def discoveries(self, *, path: str | None = None, turn: int | None = None) -> list:
        """Every rescan discovery (found.jsonl), time-ordered, with `where` and `late`, as `accesses` reads its
        records: evidence that the path EXISTED at `at` (it may have been made at any time after its folder's
        CREATE and before `at`), never an access, never a read. Filtered and refused exactly as `accesses` is
        (a turn outside 1..N, an unwatched path, or an unclean watcher health). Each record keeps its `source`,
        so a verdict built on one can name it. Empty when the take wrote no found.jsonl."""
        if turn is not None:
            self._turn(turn)
        watched = None if self._watched is None else {self.tree(w) for w in self._watched}
        if path is not None and watched is not None and path not in watched:
            raise EvidenceError(f"{path} is not a watched path ({WATCHED}): an empty reading would read 'not "
                                f"watched' as 'not found'")
        self._require_watched()
        out = []
        for f in sorted(self._found, key=lambda f: f["at"]):
            w = self.where(f["at"])
            late = w[0] == IN_TURN and f["at"] > self.turns[w[1] - 1].ended_at
            if (path is None or f["path"] == path) and (turn is None or w == (IN_TURN, turn)):
                out.append(dict(f, where=w, late=late))
        return out

    def accesses_by_stretch(self, probe_turn: int) -> dict:
        """{"pre": [...], "post": [...]}: the agent's turns' accesses only; operator steps, setup and after are
        in neither. Refused unless the watcher's health is clean, as `accesses` is."""
        s = self.stretches(probe_turn)
        located = self.accesses()
        return {side: [a for a in located if a["where"][0] == IN_TURN and a["where"][1] in ks]
                for side, ks in s.items()}

    def _require_watched(self):
        rec = self.sidecar_record()
        if rec != {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False}:
            problems = self.watcher_health()["problems"] or ["a non-zero or missing exit, or a queue overflow"]
            raise EvidenceError(f"the watcher's health is not clean ({rec}; {'; '.join(problems)}): an access "
                                f"reading from it would read the gap as 'no access'; the take routes as a watcher gap")

    # --------------------------------------------------------------------------------------------- health
    def _walk_health(self) -> tuple:
        """The start and stop records, walked in order: (closed, running, missing_start, missing_stop).
        closed          [(start, stop)]: a start and the stop right after it
        running         [(start, until)]: a start no stop closed, running at most until the next start, or for
                        ever after the last one (accesses may fall in it; it covers no turn)
        missing_start   [problem]: no start at all, or a stop with no start open before it
        missing_stop    [problem]: a start while the watcher runs, or a last start with no stop"""
        closed, running, missing_start, missing_stop = [], [], [], []
        open_at, open_line = None, None
        for i, h in enumerate(self._health, 1):
            if h["kind"] == WATCHER_START:
                if open_at is not None:
                    missing_stop.append(f"health line {i}: a watcher-start while the one at line {open_line} runs "
                                        f"(its stop record is missing)")
                    running.append((open_at, h["at"]))
                open_at, open_line = h["at"], i
            elif h["kind"] == WATCHER_STOP:
                if open_at is None:
                    missing_start.append(f"health line {i}: a watcher-stop with no watcher-start open before it "
                                         f"(its start record is missing)")
                else:
                    closed.append((open_at, h["at"]))
                    open_at = None
        if open_at is not None:
            missing_stop.append(f"health line {open_line}: the last watcher-start has no stop record")
            running.append((open_at, math.inf))
        if not any(h["kind"] == WATCHER_START for h in self._health):
            missing_start.append("no watcher-start record")
        end = self.taken_at(POST, self.n_turns)
        if not closed or not closed[-1][1] > end:
            missing_stop.append(f"no recorded interval closes strictly after post-{self.n_turns} at {end} (the final "
                                f"stop after the last snapshot is missing; THE FINAL STOP)")
        return closed, running, missing_start, missing_stop

    def watcher_intervals(self) -> tuple:
        """The recorded intervals [(start, stop)], each closed at both ends, in time order."""
        return tuple(self._walk_health()[0])

    def uncovered_turns(self) -> tuple:
        """The turns whose window, from the turn's `started_at` to post-k's `taken_at`, lies inside no one recorded
        interval: the watcher must be re-armed after pre-k's snapshot before the turn starts."""
        closed = self.watcher_intervals()
        return tuple(t.k for t in self.turns
                     if not any(s <= t.started_at and self.taken_at(POST, t.k) <= e for s, e in closed))

    def unwatched_accesses(self) -> list:
        """The accesses stamped outside every interval the records show the watcher running (closed, or after a
        start no stop closed): the log says the watcher ran when its own records say it did not."""
        closed, running, _, _ = self._walk_health()
        spans = closed + running
        return [dict(a) for a in sorted(self._access, key=lambda a: a["at"])
                if not any(s <= a["at"] <= e for s, e in spans)]

    def watcher_health(self) -> dict:
        """What the health records leave uncovered: {"missing_start": [str], "missing_stop": [str],
        "uncovered_turns": (k, ...), "unwatched_accesses": [access], "problems": [str]}."""
        _, _, missing_start, missing_stop = self._walk_health()
        uncovered, unwatched = self.uncovered_turns(), self.unwatched_accesses()
        problems = missing_start + missing_stop
        problems += [f"turn {k} (from its start at {self.turns[k - 1].started_at} to post-{k} at "
                     f"{self.taken_at(POST, k)}) lies inside no one recorded watcher interval" for k in uncovered]
        problems += [f"the access at {a['at']} ({a['op']} {a['path']}) lies outside every recorded watcher interval"
                     for a in unwatched]
        return {"missing_start": missing_start, "missing_stop": missing_stop, "uncovered_turns": uncovered,
                "unwatched_accesses": unwatched, "problems": problems}

    def sidecar_record(self) -> dict:
        """The watcher's health in routing.py's `sidecar` shape, read in time order (THE WATCHER'S HEALTH):
        `start_record` and `stop_record` are False for a missing start or stop record, and both False for a turn
        or an access the records leave uncovered. `exit_code` is the first non-zero stop's, 0 when every stop was
        clean, and None when there is no stop record (never invented: routing.py refuses it until CP2 maps it)."""
        h = self.watcher_health()
        unseen = bool(h["uncovered_turns"] or h["unwatched_accesses"])
        codes = [r["exit_code"] for r in self._health if r["kind"] == WATCHER_STOP]
        return {"start_record": not (h["missing_start"] or unseen),
                "stop_record": not (h["missing_stop"] or unseen),
                "exit_code": next((c for c in codes if c != 0), 0) if codes else None,
                "queue_overflow": any(r["kind"] == QUEUE_OVERFLOW for r in self._health)}

    def box_records(self) -> dict:
        """The two box records this reader re-verifies, under agent_adapter.BOX_KEYS' names."""
        return {"sidecar": self.sidecar_record(),
                "unexplained_operator_diffs": self.operator_check()["unexplained_diffs"]}


def exclusion_conflicts(paths, harness: str, table: dict | None = None) -> list:
    """The run-tree paths a task names (its right and wrong moves) that a pre-registered exclusion would hide under
    `harness`. Must be empty for every task under every harness. The common list and `harness`'s own run-tree
    patterns are checked; its home-relative ones never reach the run tree (the take record keeps the two
    disjoint)."""
    own = harness_run_tree_exclusions(harness, table)
    return sorted(p for p in paths if any(hb.matches(x, p) for x in COMMON_EXCLUSIONS + own))


def _json(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except ValueError as e:
        raise EvidenceError(f"{path}: not JSON ({e})") from None


def _jsonl(path: str) -> list:
    out = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            if not line.strip():
                raise EvidenceError(f"{path}:{i}: a blank line")
            try:
                out.append(json.loads(line))
            except ValueError as e:
                raise EvidenceError(f"{path}:{i}: not JSON ({e})") from None
    return out
