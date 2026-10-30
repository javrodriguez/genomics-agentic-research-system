#!/usr/bin/env python3
"""Committed registrations and the human ruling door, with local round 4 identities.

The append-only takes.json holds {"rows": [...]}; one commit adds one row.
Every identity includes arm, task, half, model, agent, wording and repeat/pressure.
The row's commit determines its session UUID. CP2 calls guard_registration or a
process-local RegistrationGuard before registering; only that instance's live
set may have open rows, at most MAX_OPEN (B19-5): a row joins it at its
registration and leaves it at its commit. A restart never inherits its live set.
A registration needs a clean tree but for the untracked folders of the live
set's open takes, takes/<slot>/<attempt>/.

commit_registration writes and commits the complete planned row. commit_ruling
writes rulings.json, a closed batch record with the caller's explicit by, in one
commit. read_history merges outcomes.json and rulings.json in commit order.
Neither door drives a take. A failed commit remains for human reconciliation.
Commit identity must be supplied in repository-local user.name/user.email or
explicit GIT_AUTHOR_*/GIT_COMMITTER_* variables; global defaults are not used.
"""

from __future__ import annotations

import argparse
import collections
import copy
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LEDGER = HERE / "takes.json"

sys.path.insert(0, str(HERE))
import prereg  # noqa: E402
import study  # noqa: E402
import batch  # noqa: E402
from graders import labels4  # noqa: E402
import stats  # noqa: E402
import routing  # noqa: E402
import mode_binding  # noqa: E402  (TAKES_DIR: an open take's folder, B19-5)

OPEN_LIMIT = batch.MAX_OPEN      # B19-5: the most takes open at once (registered, outcome not committed)


def half_cell_key(row: dict) -> tuple:
    return stats.half_cell_key(row)


def try_key(row: dict) -> tuple:
    return half_cell_key(row) + (row["wording"], stats.level(row))


HISTORY_FILES = ("outcomes.json", "rulings.json")


def _git_at(repo: Path, *args: str, missing=False) -> str:
    got = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if got.returncode and not missing:
        raise ValueError(f"git {args[0]} failed: {got.stderr.strip()}")
    return got.stdout.strip() if got.returncode == 0 else ""


def require_commit_identity(repo: Path) -> None:
    """The caller supplies author and committer; refuse before writing a record."""
    local = {part: _git_at(repo, "config", "--local", "--get", f"user.{part}", missing=True)
             for part in ("name", "email")}
    missing = [f"GIT_{role}_{part.upper()}" for role in ("AUTHOR", "COMMITTER") for part in local
               if not (os.environ.get(f"GIT_{role}_{part.upper()}") or local[part]).strip()]
    if missing:
        raise ValueError("commit identity missing: supply repository-local user.name/user.email "
                         "or explicit " + ", ".join(missing))


def read_history(*, root=HERE, repo=REPO) -> list[dict]:
    """CP2 history(): outcomes.json and rulings.json, one append per commit, in commit order.

    Both files are JSON lists of batch's closed records. Reading commits rather
    than concatenating the two files preserves the ruling's position. Rewrites,
    deletions and a commit introducing more than one record are refused.
    """
    root, repo = Path(root).resolve(), Path(repo).resolve()
    paths = [(root / p).relative_to(repo).as_posix() for p in HISTORY_FILES]
    # glitch-45's review of fold2/lb, MJ-1 (ruled): no history simplification, so a merge that resets the ledger to an
    # earlier state, and the commits it hides, are read and refused as a rewrite, never followed past
    shas = _git_at(repo, "log", "--reverse", "--full-history", "--format=%H", "--", *paths).split()
    previous, history = {p: [] for p in paths}, []
    for sha in shas:
        added = []
        for path in paths:
            text = _git_at(repo, "show", f"{sha}:{path}", missing=True)
            now = json.loads(text) if text else []
            old = previous[path]
            if not isinstance(now, list) or now[:len(old)] != old:
                raise ValueError(f"{path} rewrote committed history")
            added.extend(now[len(old):])
            previous[path] = now
        if len(added) != 1:
            raise ValueError("one commit introduces exactly one outcome or ruling")
        history.extend(added)
    bad = batch.Batch.history_problems(history)
    if bad:
        raise ValueError("; ".join(bad))
    return history


def validate_ruling(record: dict, history: list) -> None:
    if not batch.is_ruling(record) or set(record) != set(batch.RULING_KEYS):
        raise ValueError("a ruling must hold exactly batch.RULING_KEYS")
    bad = batch.Batch.history_problems(history + [record])
    if bad:
        raise ValueError("; ".join(bad))


# The review of 5afd80a7 (findings 2, 3 and 4) and the Lane-orchestrator's rulings on it (Sat 24 Oct 2026, under
# Javier's standing delegation): the door reads, before anything is written, what the publication check will read.
DRIVER_REFUSAL_RECORD = "refusal.json"      # drive.py's REFUSAL_RECORD, the driver's own refusal record (tests bind it)


def _introduces(repo: Path, sha: str, history_rel: str, outcome: dict) -> bool:
    """`sha` appends exactly `outcome` to outcomes.json (its parent's list is the new one's head)."""
    now = json.loads(_git_at(repo, "show", f"{sha}:{history_rel}", missing=True) or "[]")
    before = json.loads(_git_at(repo, "show", f"{sha}^:{history_rel}", missing=True) or "[]")
    return isinstance(now, list) and isinstance(before, list) and now[:len(before)] == before \
        and now[len(before):] == [outcome]


def driver_refusal_record(row: dict, outcome: dict, *, root=HERE, repo=REPO) -> dict | None:
    """Finding 3: the driver's own refusal record in the take's folder, counted only when the one commit that
    introduced it is the commit that committed the take's own outcome (the driver's commit road, guarded by its
    producer, never by the record's shape), and when it names its refusal ({refused, why}, non-empty strings)."""
    root, repo = Path(root).resolve(), Path(repo).resolve()
    rel = (root / mode_binding.TAKES_DIR / str(row["slot"]) / str(row["attempt"]) / DRIVER_REFUSAL_RECORD
           ).relative_to(repo).as_posix()
    history_rel = (root / HISTORY_FILES[0]).relative_to(repo).as_posix()
    shas = _git_at(repo, "log", "--format=%H", "--", rel, missing=True).split()
    if len(shas) != 1:
        return None
    try:
        if not _introduces(repo, shas[0], history_rel, outcome):
            return None
        doc = json.loads(_git_at(repo, "show", f"{shas[0]}:{rel}", missing=True) or "null")
    except ValueError:
        return None
    if not (isinstance(doc, dict) and all(isinstance(doc.get(k), str) and doc[k].strip() for k in ("refused", "why"))):
        return None
    return doc


TAKE_COMMIT_SUBJECT = "Record one take's outcome and its records"   # drive.py's COMMIT_SUBJECT (tests bind it)


def outcome_committed_by_take_road(outcome: dict, *, root=HERE, repo=REPO) -> bool:
    """The pin-block ruling: the commit that appended exactly `outcome` to outcomes.json is the take road's (drive's
    TakeRepo, whose subject is TAKE_COMMIT_SUBJECT and which commits only the outcomes batch hands it)."""
    root, repo = Path(root).resolve(), Path(repo).resolve()
    history_rel = (root / HISTORY_FILES[0]).relative_to(repo).as_posix()
    for sha in _git_at(repo, "log", "--format=%H", "--", history_rel, missing=True).split():
        try:
            if not _introduces(repo, sha, history_rel, outcome):
                continue
        except ValueError:
            return False
        subject = _git_at(repo, "show", "-s", "--format=%s", sha, missing=True)
        if subject != TAKE_COMMIT_SUBJECT:
            return False
        return True
    return False


def _end_state_word(row: dict, outcome: dict) -> str:
    """The take's own grader's word for its committed end state in the excluded view (run.grade_committed)."""
    import run
    return run.grade_views(run.grade_committed(row, outcome))["excluded"]


def ruling_door_problems(record: dict, history: list, rows: list, *, table=None, standing=None,
                         driver_refusal=None) -> list[str]:
    """THE RULING RULE at the door (batch.py), beyond history_problems: (finding 2) a ruling that re-runs a take whose
    first turn started, or whose phase cannot be read, is refused unless its own grader reads its committed end state
    with no wrong action, the check publication runs (check_results.ruled_rerun_problems); (finding 3) a take whose
    drive started and left no records is ruled aborted, or re-run only on the driver's own refusal record committed
    with its outcome; (finding 4) a pin block whose pin is the registered row's own profile is no driver pin mismatch.
    `standing` and `driver_refusal` stand in for the real readers in tests."""
    import check_results
    table = routing.load_table() if table is None else table
    standing = _end_state_word if standing is None else standing
    driver_refusal = driver_refusal_record if driver_refusal is None else driver_refusal
    key = (record.get("slot"), record.get("attempt"))
    taken = next((o for o in reversed(history) if batch.is_outcome(o) and (o.get("slot"), o.get("attempt")) == key),
                 None)
    if taken is None or record.get("ruling") not in labels4.RULINGS:
        return []                                  # history_problems names both
    row = next((r for r in rows if (r.get("slot"), r.get("attempt")) == key), None)
    phase = batch.ruled_phase(taken, table)
    p = batch.door_rule_problems([taken, record], rows, table, driver_refusal)   # findings 3 and 4, shared
    if batch.reruns(record) and phase != labels4.BEFORE_FIRST_TURN:
        if row is None:
            p.append(f"slot {key[0]} attempt {key[1]}: no registered row, so its end state cannot be read")
        else:
            p += check_results.ruled_rerun_problems([taken, record], {key: row}, standing, table)
    final = record.get("ruling") == labels4.RULE_ROUTE and record.get("route") in check_results.FINAL_RULED_ROUTES
    if final and phase == labels4.AFTER_FIRST_TURN:    # pre-freeze review 2, m6: graded or aborted, by the end state
        if row is None:
            p.append(f"slot {key[0]} attempt {key[1]}: no registered row, so its end state cannot be read")
        else:
            p += check_results.ruled_route_problems([taken, record], {key: row}, standing, table)
    return p


def _ruling_reads_row(record: dict, history: list) -> bool:
    """Whether the door reads the ruled take's registered row: every re-running ruling does; a graded or aborted
    one only after the take's first turn, where its end state is read (pre-freeze review 2, m6; the review of
    fold2/la2, M1: a ruling that reads no end state needs no readable takes.json)."""
    if batch.reruns(record):
        return True
    if record.get("ruling") != labels4.RULE_ROUTE or record.get("route") not in (labels4.GRADED, labels4.ABORTED):
        return False
    key = (record.get("slot"), record.get("attempt"))
    taken = next((o for o in reversed(history) if batch.is_outcome(o) and (o.get("slot"), o.get("attempt")) == key),
                 None)
    return taken is not None and batch.ruled_phase(taken, routing.load_table()) == labels4.AFTER_FIRST_TURN


def commit_ruling(*, slot: str, attempt: int, word: str, route, by: str, why: str, cite: str, root=HERE,
                  repo=REPO, standing=None) -> dict:
    """The human door: append the caller's closed ruling to rulings.json, one commit.

    by is a required argument. It is never read from git, an environment variable
    or a default. The door uses the same committed history CP2 reads. A failed
    commit leaves the file for a human to reconcile; nothing retries a ruling.
    why and cite (pre-freeze review 1, MAJOR 8) are required the same way, and
    batch's ruling rule is checked against the history before anything is written.
    """
    root, repo = Path(root).resolve(), Path(repo).resolve()
    record = dict(kind=labels4.RULING, slot=slot, attempt=attempt, ruling=word, route=route, by=by)
    record.update(why=why, cite=cite)
    history = read_history(root=root, repo=repo)
    validate_ruling(record, history)
    rows = load_rows(root=root, repo=repo) if _ruling_reads_row(record, history) else []
    bad = ruling_door_problems(record, history, rows, standing=standing,
                               driver_refusal=lambda r, o: driver_refusal_record(r, o, root=root, repo=repo))
    if bad:
        raise ValueError("; ".join(bad))
    if _git_at(repo, "status", "--porcelain"):
        raise ValueError("commit the existing changes before a ruling; one ruling per commit")
    require_commit_identity(repo)
    path = root / HISTORY_FILES[1]
    existing = json.loads(path.read_text()) if path.exists() else []
    path.write_text(json.dumps(existing + [record], indent=2) + "\n", encoding="utf-8")
    _git_at(repo, "add", "--", path.relative_to(repo).as_posix())
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as msg:
        msg.write("Record a human ruling\n")
        msg.flush()
        _git_at(repo, "commit", "-F", msg.name)
    return record


def commit_night_ruling(*, slot, attempt: int, by: str, root=HERE, repo=REPO) -> dict:
    """The human door for THE NIGHTLY STOP (batch.py): append the caller's closed night ruling to rulings.json, one
    commit, with commit_ruling's discipline. It names the harness-error that brought the night's count to the
    registered number (batch.Batch refuses a restart and names it); by is required and never read from git, an
    environment variable or a default. The record is checked against the same committed history CP2 reads, through
    batch.Batch.history_problems, before anything is written; a failed commit leaves the file for a human."""
    root, repo = Path(root).resolve(), Path(repo).resolve()
    record = {"kind": batch.NIGHT_RULING, "slot": slot, "attempt": attempt, "by": by}
    history = read_history(root=root, repo=repo)
    bad = batch.Batch.history_problems(history + [record])
    if bad:
        raise ValueError("; ".join(bad))
    if _git_at(repo, "status", "--porcelain"):
        raise ValueError("commit the existing changes before a ruling; one ruling per commit")
    require_commit_identity(repo)
    path = root / HISTORY_FILES[1]
    existing = json.loads(path.read_text()) if path.exists() else []
    path.write_text(json.dumps(existing + [record], indent=2) + "\n", encoding="utf-8")
    _git_at(repo, "add", "--", path.relative_to(repo).as_posix())
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as msg:
        msg.write("Record a human night ruling\n")
        msg.flush()
        _git_at(repo, "commit", "-F", msg.name)
    return record


def agent_problems(row: dict) -> list[str]:
    return batch.agent_problems(row)


def outside_live_block(waiting: list, live) -> list:
    return [key for key in waiting if key not in live]


def slot_final(outcome: dict) -> bool:
    return outcome["final"]


def cell_closed(history: list, cell) -> bool:
    return any(o["half_cell"] == cell and o["cell_state"] == labels4.INCOMPLETE_MECHANICAL
               for o in registration_outcomes(history))


def registration_outcomes(history: list) -> list:
    """Replay batch's strict own-event count; publication ambiguity cannot block registration.

    Only rulings need new fates. Ordinary outcomes keep their committed state.
    This reader neither verifies drive records nor applies publication's PL-3
    deduplication: batch counts each ruled pause as its own event.
    """
    table = routing.load_table()
    effective, closed = {}, {}
    events = collections.defaultdict(set)
    spent_cell, spent_slot = collections.Counter(), collections.Counter()
    for entry in history:
        if batch.is_night_ruling(entry):      # a run-level ruling: no take's fate (THE NIGHTLY STOP)
            continue
        key = (entry["slot"], entry["attempt"])
        if batch.is_ruling(entry):
            taken = effective[key]
            if entry["ruling"] == labels4.RULE_RERUN:
                effective[key] = dict(taken, **batch.Batch._fate(rerun=True))
                continue
            o = dict(taken, state=entry["route"], window_event=None)
            cell, state = o["half_cell"], o["state"]
            if state in batch.CELL_CAPPED_ROUTES:
                count = len(events[(cell, state)] | {batch.cell_event(o)})
                closes = count >= batch.half_cell_cap(table, state)
                fate = batch.Batch._fate(final=closes, rerun=not closes, beyond_cap=closes,
                    cell_state=labels4.INCOMPLETE_MECHANICAL if closes else None,
                    cell_reason="committed ruling reaches the cell cap" if closes else None)
            elif state == labels4.HARNESS_ERROR:
                cap = table["caps"][state]
                free = (spent_cell[(cell, state)] < cap["reruns_per_half_cell"] and
                        spent_slot[(o["slot"], state)] < cap["reruns_per_slot"])
                fate = batch.Batch._fate(final=not free, rerun=free, beyond_cap=not free)
            else:
                fate = batch.Batch._fate(final=True)
            if cell in closed:
                fate.update(cell_state=labels4.INCOMPLETE_MECHANICAL, cell_reason=closed[cell])
                if state in batch.RERUN_ROUTES:
                    fate.update(final=True, rerun=False, beyond_cap=True)
            o.update(fate)
        else:
            o = copy.deepcopy(entry)
        cell, state = o["half_cell"], o["state"]
        if state in batch.CELL_CAPPED_ROUTES:
            events[(cell, state)].add(batch.cell_event(o))
        if o["rerun"] and state in batch.RERUN_ROUTES:
            spent_cell[(cell, state)] += 1
            spent_slot[(o["slot"], state)] += 1
        if o["cell_state"] is not None:
            closed[cell] = o["cell_reason"]
        effective[key] = o
    return list(effective.values())


def guard_registration(row: dict, attempt: int, rows: list, history: list, *, live=()) -> None:
    """CP2 register(row, attempt)'s required guard; all inputs describe committed bytes.

    rows holds registered rows with their attempt; history is batch's closed
    outcomes/rulings in commit order. live contains only (slot, attempt) pairs
    registered by this instance whose outcome is not yet committed (its open
    rows, at most OPEN_LIMIT), never restored on restart.
    An exception precedes every write and every launch.
    """
    bad = agent_problems(row)
    if bad:
        raise ValueError("; ".join(bad))
    if type(attempt) is not int or attempt < 1:
        raise ValueError("attempt must be a positive int")
    if any(not isinstance(row.get(k), str) or not row[k] for k in ("slot", "half_cell")):
        raise ValueError("slot and half_cell must be non-empty ids")
    bad = batch.Batch.history_problems(history)
    if bad:
        raise ValueError("; ".join(bad))
    key = (row["slot"], attempt)
    registered = [(r["slot"], r["attempt"]) for r in rows]
    if len(registered) != len(set(registered)):
        raise ValueError("a registration occurs twice")
    done = {(o["slot"], o["attempt"]): o for o in history if batch.is_outcome(o)}
    waiting = [k for k in registered if k not in done]
    if outside_live_block(waiting, live):
        raise ValueError("an earlier row is registered with no committed outcome; human reconciliation required")
    if key in registered:
        raise ValueError("this slot and attempt are already registered; no re-registration")
    if len(waiting) >= OPEN_LIMIT:
        raise ValueError(f"at most {OPEN_LIMIT} open rows (MAX_OPEN takes open in one live set)")
    if cell_closed(history, row["half_cell"]):
        raise ValueError("the half-cell is closed by its committed state")
    prior = [o for o in registration_outcomes(history) if o["slot"] == row["slot"]]
    if not prior:
        if attempt != 1:
            raise ValueError("the first attempt is 1")
        return
    last = prior[-1]
    if attempt != last["attempt"] + 1:
        raise ValueError("the next attempt follows the last committed attempt")
    if slot_final(last):
        raise ValueError("the slot has a final committed outcome")
    if batch.needs_ruling(last):
        ruled = [r for r in history if batch.is_ruling(r) and
                 (r["slot"], r["attempt"]) == (last["slot"], last["attempt"])]
        if not ruled or not last["rerun"]:
            raise ValueError("the stopped take needs a committed re-run ruling")
    elif last["state"] not in batch.RERUN_ROUTES and not (
            last["state"] == labels4.FAILED and last["drive_started"] is False):
        raise ValueError("the slot has no committed permission to re-run")


class RegistrationGuard:
    """One live set in one repo instance (B19-5): a row joins it at its registration and leaves it at its commit;
    never persist or restore this object."""
    def __init__(self):
        self.live = set()

    def check(self, row: dict, attempt: int, rows: list, history: list) -> None:
        done = {(o["slot"], o["attempt"]) for o in history if batch.is_outcome(o)}
        self.live -= done
        guard_registration(row, attempt, rows, history, live=self.live)

    def registered(self, row: dict, attempt: int) -> None:
        """Called only after a successful registration commit, before any drive."""
        self.live.add((row["slot"], attempt))


def git(*args: str) -> str:
    return _git_at(REPO, *args)


def namespace() -> uuid.UUID:
    spec = prereg.load()["session_namespace"]
    derived = uuid.uuid5(uuid.NAMESPACE_URL, spec["derived_from"])
    if str(derived) != spec["uuid"]:
        raise ValueError("the pre-registered session namespace does not recompute")
    return derived


def session_id_for(row_commit_sha: str) -> str:
    return str(uuid.uuid5(namespace(), row_commit_sha))


def load_rows(*, root=HERE, repo=None) -> list[dict]:
    root = Path(root).resolve()
    repo = Path(repo).resolve() if repo is not None else REPO.resolve()
    path = root / "takes.json"
    if not path.is_file():
        return []
    rel = path.relative_to(repo).as_posix()
    if _git_at(repo, "status", "--porcelain", "--", rel):
        raise ValueError("the ledger has uncommitted changes")
    doc = json.loads(path.read_text())
    if not isinstance(doc, dict) or set(doc) != {"rows"} or not isinstance(doc["rows"], list):
        raise ValueError("takes.json must contain exactly a rows list")
    import check_results
    check_results.validate_ledger(doc["rows"])
    row_commits(root=root, repo=repo)
    return doc["rows"]


def row_commits(*, root=HERE, repo=REPO) -> dict[int, str]:
    root, repo = Path(root).resolve(), Path(repo).resolve()
    rel = (root / "takes.json").relative_to(repo).as_posix()
    previous, commits = [], {}
    for sha in _git_at(repo, "log", "--reverse", "--format=%H", "--", rel).split():
        doc = json.loads(_git_at(repo, "show", f"{sha}:{rel}"))
        now = doc.get("rows") if isinstance(doc, dict) else None
        if not isinstance(now, list) or now[:len(previous)] != previous or len(now) != len(previous) + 1:
            raise ValueError("ledger history must append exactly one unchanged row per commit")
        commits[len(previous)] = sha
        previous = now
    return commits


def require_planned_row(row, pre):
    identity = (*stats.TAKE_FIELDS[:8], "slot", "half_cell")
    wanted = {k: row[k] for k in identity}
    matches = [r for r in pre["rows"] if {k: r[k] for k in identity} == wanted]
    if len(matches) != 1:
        raise ValueError("the row is not one unique pre-registered identity")
    # Driver metadata, where present in the design, is equally bound.
    if any(k != "attempt" and row.get(k) != v for k, v in matches[0].items()):
        raise ValueError("the row differs from its pre-registered metadata")


def open_take_folders(guard, history, *, root=HERE, repo=REPO) -> set:
    """B19-5: the folders of this instance's open takes (its live set, less every take the history commits), each
    takes/<slot>/<attempt>/ under the study folder, repo-relative with a trailing slash."""
    root, repo = Path(root).resolve(), Path(repo).resolve()
    done = {(o["slot"], o["attempt"]) for o in history if batch.is_outcome(o)}
    return {(root / mode_binding.TAKES_DIR / str(slot) / str(attempt)).relative_to(repo).as_posix() + "/"
            for slot, attempt in guard.live - done}


def unclean_paths(repo, allowed=frozenset()) -> list:
    """Every `git status` line but an untracked file inside one of the `allowed` folders (B19-5: an open take's
    folder is written from its launch to its commit). A modified, staged or quoted path is never allowed."""
    lines = _git_at(Path(repo), "status", "--porcelain", "--untracked-files=all").splitlines()
    return [line for line in lines
            if not (line.startswith("?? ") and any(line[3:].startswith(folder) for folder in allowed))]


def commit_registration(row, attempt, *, guard=None, root=HERE, repo=REPO, pre=None):
    root, repo = Path(root).resolve(), Path(repo).resolve()
    if pre is None:
        pre = prereg.require_frozen("registering a take")
    require_planned_row(row, pre)
    import check_results
    registered = dict(row, attempt=attempt)
    check_results.validate_ledger([registered])
    guard = RegistrationGuard() if guard is None else guard
    history = read_history(root=root, repo=repo)
    if unclean_paths(repo, open_take_folders(guard, history, root=root, repo=repo)):
        raise ValueError("registration requires a clean committed repository (but the open takes' folders)")
    require_commit_identity(repo)
    rows = load_rows(root=root, repo=repo)
    guard.check(row, attempt, rows, history)
    path = root / "takes.json"
    path.write_text(json.dumps({"rows": rows + [registered]}, indent=2) + "\n")
    _git_at(repo, "add", "--", path.relative_to(repo).as_posix())
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as message:
        message.write("Register one planned take\n")
        message.flush()
        _git_at(repo, "commit", "-F", message.name)
    guard.registered(row, attempt)
    return _git_at(repo, "rev-parse", "HEAD")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--add", action="store_true")
    group.add_argument("--ruling", choices=labels4.RULINGS)
    group.add_argument("--audit", "--check", action="store_true")
    group.add_argument("--plan", action="store_true")
    group.add_argument("--session-id", type=int)
    parser.add_argument("--row", help="JSON file containing the full pre-registered row")
    parser.add_argument("--slot")
    parser.add_argument("--attempt", type=int)
    parser.add_argument("--route", choices=labels4.ROUTES)
    parser.add_argument("--by")
    parser.add_argument("--why", help="with --ruling: why, in the ruler's words (required)")
    parser.add_argument("--cite", help="with --ruling: the record, commit or rule the ruling rests on (required)")
    args = parser.parse_args(argv)
    try:
        if args.ruling:
            commit_ruling(slot=args.slot, attempt=args.attempt, word=args.ruling, route=args.route, by=args.by,
                          why=args.why, cite=args.cite)
            print("takes: 1 human ruling committed")
        elif args.add:
            if not args.row or args.attempt is None:
                raise ValueError("--add requires --row and --attempt")
            print(commit_registration(json.loads(Path(args.row).read_text()), args.attempt))
        elif args.plan:
            print(json.dumps(prereg.require_frozen("listing planned takes")["rows"], indent=2))
        elif args.session_id is not None:
            print(session_id_for(row_commits()[args.session_id]))
        else:
            rows, history = load_rows(), read_history()
            print(f"takes: {len(rows)} committed rows; {len(history)} outcomes and rulings" if rows or history
                  else "takes: no takes; no registration or outcome measured")
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f"takes: REFUSE: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
