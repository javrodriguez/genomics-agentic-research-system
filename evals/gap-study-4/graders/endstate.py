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
        each                {"label": "<its file stem>", "taken_at": num, "entries": {path: STATE}}
    access.jsonl            the watcher's log of the consequential paths: {"at": num, "path": str, "op": "open" |
                            "modify" | "delete"} per line
    health.jsonl            the sidecar's health records: {"kind": "watcher-start", "at": num} | {"kind":
                            "watcher-stop", "at": num, "exit_code": int} | {"kind": "queue-overflow", "at": num}
    blobs/<sha256>          the bytes of a consequential file as a snapshot found it, named by their own sha256
                            (optional; only the pre-registered consequential paths are copied)

    STATE                   {"type": "file", "sha256": <64 hex>} | {"type": "link", "target": str} |
                            {"type": "dir"} | {"type": "unreadable"}
    paths                   relative to the snapshot root, `/`-separated, never absolute, never with an empty,
                            `.` or `..` segment. Snapshots include ignored files. A symbolic link is recorded as a
                            link with its target and never followed: a snapshot that lists anything beneath a link
                            followed it, and is refused. Every other field and every other kind is refused.

Times are the host clock, in seconds. The snapshots must be in order (pre-1 <= post-1 <= pre-2 <= ...), each turn
inside its own snapshots, and each background process stopped before the snapshot after its turn.

WHO CHANGED WHAT.
  - The agent's changes in turn k are the diff pre-k -> post-k: across that turn only, which ends at quiescence, so
    a background process the turn launched and the driver stopped at the cap is that turn's.
  - The operator's changes after turn k are the diff post-k -> pre-(k+1), each matched to the logged operator
    events of that step. The drive step has already routed a step no event explains (routing.json's
    operator-diff rows); `operator_check()` only re-verifies it, in the count `routing.py` reads.
  - An access is attributed by its time: to turn k in (pre-k, post-k], to the operator step after turn k in
    (post-k, pre-(k+1)], to `setup` before pre-1 and `after` past post-N. An access in turn k after its `ended_at`
    is marked late (the background stretch of the turn).
  - Stretches: for a probe at turn p, `pre` is turns 1..p-1 and `post` is turns p..N. Operator steps belong to
    neither, so a stage output written before the probe and the operator's own writes are never the probe's
    answer.

EXCLUSIONS (pre-registered; never a path a task's right or wrong move touches; `exclusion_conflicts` checks it):
    GIT_BOOKKEEPING     run-tree paths git rewrites on its own, read-only commands included: the index's stat
                        cache that `git status` refreshes, and its lock. A commit (objects, refs, logs) is not
                        bookkeeping and is never excluded.
    HELPER_BOOKKEEPING  Python's bytecode caches a helper's run leaves (the repository's own .gitignore names
                        `__pycache__/`).
    the harness's own   home-relative paths from harness_bookkeeping's entry for the take's harness, and only
                        that harness's: another harness's paths are not excluded.
  They apply to every snapshot diff (the agent's and the operator's), never to the access log, which watches
  consequential paths only.

No model, no network, stdlib only.
"""

from __future__ import annotations

import hashlib
import json
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
HELPER_BOOKKEEPING = ("**/__pycache__/**",)
COMMON_EXCLUSIONS = GIT_BOOKKEEPING + HELPER_BOOKKEEPING

# The closed layout.
LEDGER = "ledger.jsonl"
ACCESS = "access.jsonl"
HEALTH = "health.jsonl"
SNAPSHOTS = "snapshots"
BLOBS = "blobs"
FILES = (LEDGER, ACCESS, HEALTH)
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
STATE_FIELDS = {"file": {"type", "sha256"}, "link": {"type", "target"}, "dir": {"type"}, "unreadable": {"type"}}
ACCESS_FIELDS = {"at", "path", "op"}
ACCESS_OPS = ("open", "modify", "delete")
WRITING_OPS = ("modify", "delete")
HEALTH_FIELDS = {"watcher-start": {"kind", "at"}, "watcher-stop": {"kind", "at", "exit_code"},
                 "queue-overflow": {"kind", "at"}}

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


def _under(path: str, prefix: str) -> str | None:
    """`path` relative to `prefix` ("" is the root), or None when it lies outside."""
    if prefix == "":
        return path
    if path == prefix:
        return ""
    return path[len(prefix) + 1:] if path.startswith(prefix + "/") else None


def _disjoint(a: str, b: str) -> bool:
    return _under(a, b) is None and _under(b, a) is None


def kind_of(before, after) -> str:
    """created, deleted, modified (same type, new content or target) or retyped (a file became a link, ...)."""
    if before is None:
        return "created"
    if after is None:
        return "deleted"
    return "modified" if before["type"] == after["type"] else "retyped"


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
                   table: dict | None = None) -> "Evidence":
        """The same evidence as a folder holds, from in-memory parts: the ledger's records in order, snapshots by
        label, the access log's and health records' lines, and blobs (sha256 -> bytes). `table` is the
        bookkeeping table (harness_bookkeeping.TABLE when None)."""
        self = object.__new__(cls)
        self._table = table
        self._read_ledger(ledger)
        self._read_snapshots(snapshots)
        self._read_access(access)
        self._read_health(health)
        self._read_blobs(blobs or {})
        return self

    @classmethod
    def load(cls, folder, table: dict | None = None) -> "Evidence":
        """Read an evidence folder (the closed layout above)."""
        folder = os.fspath(folder)
        if os.path.islink(folder) or not os.path.isdir(folder):
            raise EvidenceError(f"{folder}: not a folder (or a link to one)")
        names = sorted(os.listdir(folder))
        unknown = [n for n in names if n not in FILES + FOLDERS]
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
            if (n in FILES) != os.path.isfile(p) or (n in FOLDERS) != os.path.isdir(p):
                raise EvidenceError(f"{n} is not a {'file' if n in FILES else 'folder'}")
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
        return cls.from_parts(ledger=_jsonl(os.path.join(folder, LEDGER)), snapshots=snaps,
                              access=_jsonl(os.path.join(folder, ACCESS)), health=_jsonl(os.path.join(folder, HEALTH)),
                              blobs=blobs, table=table)

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

    def _read_health(self, health):
        if not isinstance(health, list):
            raise EvidenceError("the health records are a list")
        for i, h in enumerate(health, 1):
            kind = h.get("kind") if isinstance(h, dict) else None
            if kind not in HEALTH_FIELDS:
                raise EvidenceError(f"health line {i}: kind {kind!r} is not one of {sorted(HEALTH_FIELDS)}")
            _closed(h, HEALTH_FIELDS[kind], f"health line {i}")
            if not _num(h["at"]) or (kind == "watcher-stop" and not _int(h["exit_code"])):
                raise EvidenceError(f"health line {i}: a time (and a stop's int exit code)")
        self._health = [dict(h) for h in health]

    def _read_blobs(self, blobs):
        if not isinstance(blobs, dict):
            raise EvidenceError("blobs map a sha256 to bytes")
        for name, data in blobs.items():
            if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != name:
                raise EvidenceError(f"blob {name!r} is not named by its own sha256")
        self._blobs = dict(blobs)

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

    def unreadable(self, label: str) -> list:
        return sorted(p for p, st in self._snaps[label]["entries"].items() if st["type"] == "unreadable")

    def tree(self, path: str) -> str:
        """A run-tree-relative path as a snapshot path."""
        return path if self.run_tree == "" else f"{self.run_tree}/{path}"

    # --------------------------------------------------------------------------------------------- exclusions
    def is_excluded(self, path: str) -> bool:
        """Is this snapshot path git's, a helper's, or the take's own harness's bookkeeping?"""
        rel = _under(path, self.run_tree)
        if rel is not None and rel != "" and any(hb.matches(p, rel) for p in COMMON_EXCLUSIONS):
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
            if before != after and self.is_excluded(p) == excluded:
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
        A write explains a path when the step changed that path to exactly the write's `after`. An event is
        explained when every one of its writes is; an event whose write left no such change is not."""
        changes = self.operator_changes(k)
        claimed, events = {}, []
        for e in self._ops.get(k, []):
            ok = True
            for w in e["writes"]:
                c = changes.get(w["path"])
                if c is None or c.after != w["after"]:
                    ok = False
                else:
                    claimed[w["path"]] = e["id"]
            events.append({"id": e["id"], "paths": [w["path"] for w in e["writes"]], "explained": ok})
        unexplained = sorted(p for p in changes if p not in claimed)
        for a in self.accesses():
            if a["where"] == (IN_OPERATOR, k) and a["op"] in WRITING_OPS and a["path"] not in claimed and \
                    not any(a["path"] == w["path"] for e in self._ops.get(k, []) for w in e["writes"]):
                if a["path"] not in unexplained:
                    unexplained.append(a["path"])
        return {"events": events, "unexplained": sorted(unexplained)}

    def operator_check(self) -> dict:
        """Re-verifies that every operator-step diff is explained by a logged operator event.
        {"unexplained_diffs": int, "problems": [str]}: the count is routing.py's `operator.unexplained_diffs`
        (a changed path no event explains, a written path the watcher saw no event for, and an event whose write
        is not in the diff each count one)."""
        problems = []
        for k in self.operator_steps():
            m = self.operator_matches(k)
            problems += [f"operator step after turn {k}: {p} changed and no logged event explains it"
                         for p in m["unexplained"]]
            problems += [f"operator step after turn {k}: event {e['id']} logged writes the step does not show"
                         for e in m["events"] if not e["explained"]]
        return {"unexplained_diffs": len(problems), "problems": problems}

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

    def accesses(self, *, path: str | None = None, turn: int | None = None) -> list:
        """Every access, time-ordered, with `where` and `late` (in turn k after its ended_at: the background
        stretch). Filtered to one path and/or one turn when given."""
        out = []
        for a in sorted(self._access, key=lambda a: a["at"]):
            w = self.where(a["at"])
            late = w[0] == IN_TURN and a["at"] > self.turns[w[1] - 1].ended_at
            rec = dict(a, where=w, late=late)
            if path is not None and a["path"] != path:
                continue
            if turn is not None and w != (IN_TURN, turn):
                continue
            out.append(rec)
        return out

    def accesses_by_stretch(self, probe_turn: int) -> dict:
        """{"pre": [...], "post": [...]}: the agent's turns' accesses only; operator steps, setup and after are
        in neither."""
        s = self.stretches(probe_turn)
        return {side: [a for a in self.accesses() if a["where"][0] == IN_TURN and a["where"][1] in ks]
                for side, ks in s.items()}

    # --------------------------------------------------------------------------------------------- health
    def sidecar_record(self) -> dict:
        """The watcher's health in routing.py's `sidecar` shape. `exit_code` is the first non-zero stop's, 0 when
        every stop was clean, and None when there is no stop record (never invented: the caller routes the gap)."""
        starts = [h for h in self._health if h["kind"] == "watcher-start"]
        stops = [h for h in self._health if h["kind"] == "watcher-stop"]
        codes = [h["exit_code"] for h in stops]
        return {"start_record": bool(starts), "stop_record": bool(stops) and len(stops) == len(starts),
                "exit_code": next((c for c in codes if c != 0), 0) if codes else None,
                "queue_overflow": any(h["kind"] == "queue-overflow" for h in self._health)}

    def box_records(self) -> dict:
        """The two box records this reader re-verifies, under agent_adapter.BOX_KEYS' names."""
        return {"sidecar": self.sidecar_record(),
                "unexplained_operator_diffs": self.operator_check()["unexplained_diffs"]}


def exclusion_conflicts(paths, harness: str, table: dict | None = None) -> list:
    """The run-tree paths a task names (its right and wrong moves) that a pre-registered exclusion would hide.
    Must be empty for every task. Home-relative harness paths never reach the run tree (the take record keeps
    the two disjoint), so the common list is what is checked; `harness` must still be known."""
    hb.entry(harness, table)
    return sorted(p for p in paths if any(hb.matches(x, p) for x in COMMON_EXCLUSIONS))


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
