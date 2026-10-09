#!/usr/bin/env python3
"""Committed registrations and the human ruling door, with local round 4 identities.

The append-only takes.json holds {"rows": [...]}; one commit adds one row.
Every identity includes arm, task, half, model, agent, wording and repeat/pressure.
The row's commit determines its session UUID. CP2 calls guard_registration or a
process-local RegistrationGuard before registering; only that instance's current
block may have up to three open rows. A restart never inherits its live set.

commit_registration writes and commits the complete planned row. commit_ruling
writes rulings.json, a closed batch record with the caller's explicit by, in one
commit. read_history merges outcomes.json and rulings.json in commit order.
Neither door drives a take. A failed commit remains for human reconciliation.
"""

from __future__ import annotations

import argparse
import json
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

OPEN_LIMIT = batch.BLOCK


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


def read_history(*, root=HERE, repo=REPO) -> list[dict]:
    """CP2 history(): outcomes.json and rulings.json, one append per commit, in commit order.

    Both files are JSON lists of batch's closed records. Reading commits rather
    than concatenating the two files preserves the ruling's position. Rewrites,
    deletions and a commit introducing more than one record are refused.
    """
    root, repo = Path(root).resolve(), Path(repo).resolve()
    paths = [(root / p).relative_to(repo).as_posix() for p in HISTORY_FILES]
    shas = _git_at(repo, "log", "--reverse", "--format=%H", "--", *paths).split()
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


def commit_ruling(*, slot: str, attempt: int, word: str, route, by: str, root=HERE, repo=REPO) -> dict:
    """The human door: append the caller's closed ruling to rulings.json, one commit.

    by is a required argument. It is never read from git, an environment variable
    or a default. The door uses the same committed history CP2 reads. A failed
    commit leaves the file for a human to reconcile; nothing retries a ruling.
    """
    root, repo = Path(root).resolve(), Path(repo).resolve()
    record = dict(kind=labels4.RULING, slot=slot, attempt=attempt, ruling=word, route=route, by=by)
    history = read_history(root=root, repo=repo)
    validate_ruling(record, history)
    if _git_at(repo, "status", "--porcelain"):
        raise ValueError("commit the existing changes before a ruling; one ruling per commit")
    path = root / HISTORY_FILES[1]
    existing = json.loads(path.read_text()) if path.exists() else []
    path.write_text(json.dumps(existing + [record], indent=2) + "\n", encoding="utf-8")
    _git_at(repo, "add", "--", path.relative_to(repo).as_posix())
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as msg:
        msg.write("Record a human ruling\n\nCo-Authored-By: Codex (gpt-6-astra) <noreply@openai.com>\n")
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
    return any(not batch.is_ruling(o) and o["half_cell"] == cell and
               o["cell_state"] == labels4.INCOMPLETE_MECHANICAL for o in history)


def guard_registration(row: dict, attempt: int, rows: list, history: list, *, live=()) -> None:
    """CP2 register(row, attempt)'s required guard; all inputs describe committed bytes.

    rows holds registered rows with their attempt; history is batch's closed
    outcomes/rulings in commit order. live contains only (slot, attempt) pairs
    registered by this instance in its current block, never restored on restart.
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
    done = {(o["slot"], o["attempt"]): o for o in history if not batch.is_ruling(o)}
    waiting = [k for k in registered if k not in done]
    if outside_live_block(waiting, live):
        raise ValueError("an earlier row is registered with no committed outcome; human reconciliation required")
    if key in registered:
        raise ValueError("this slot and attempt are already registered; no re-registration")
    if len(waiting) >= OPEN_LIMIT:
        raise ValueError(f"at most {OPEN_LIMIT} open rows (three in one live block)")
    if cell_closed(history, row["half_cell"]):
        raise ValueError("the half-cell is closed by its committed state")
    prior = [o for o in done.values() if o["slot"] == row["slot"]]
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
        if not ruled or ruled[-1]["ruling"] != labels4.RULE_RERUN:
            raise ValueError("the stopped take needs a committed re-run ruling")
    elif last["state"] not in batch.RERUN_ROUTES and not (
            last["state"] == labels4.FAILED and last["drive_started"] is False):
        raise ValueError("the slot has no committed permission to re-run")


class RegistrationGuard:
    """One live block in one repo instance; never persist or restore this object."""
    def __init__(self):
        self.live = set()

    def check(self, row: dict, attempt: int, rows: list, history: list) -> None:
        done = {(o["slot"], o["attempt"]) for o in history if not batch.is_ruling(o)}
        if self.live <= done:
            self.live.clear()
        elif self.live & done:
            raise ValueError("a row is registered with no committed outcome in the finishing block")
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


def commit_registration(row, attempt, *, guard=None, root=HERE, repo=REPO, pre=None):
    root, repo = Path(root).resolve(), Path(repo).resolve()
    if pre is None:
        pre = prereg.require_frozen("registering a take")
    require_planned_row(row, pre)
    import check_results
    registered = dict(row, attempt=attempt)
    check_results.validate_ledger([registered])
    if _git_at(repo, "status", "--porcelain"):
        raise ValueError("registration requires a clean committed repository")
    rows, history = load_rows(root=root, repo=repo), read_history(root=root, repo=repo)
    guard = RegistrationGuard() if guard is None else guard
    guard.check(row, attempt, rows, history)
    path = root / "takes.json"
    path.write_text(json.dumps({"rows": rows + [registered]}, indent=2) + "\n")
    _git_at(repo, "add", "--", path.relative_to(repo).as_posix())
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as message:
        message.write("Register one planned take\n\nCo-Authored-By: Codex (gpt-6-astra) <noreply@openai.com>\n")
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
    args = parser.parse_args(argv)
    try:
        if args.ruling:
            commit_ruling(slot=args.slot, attempt=args.attempt, word=args.ruling, route=args.route, by=args.by)
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
