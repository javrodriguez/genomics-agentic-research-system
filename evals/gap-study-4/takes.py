#!/usr/bin/env python3
"""The take ledger: a take is pre-registered before it runs, and the proof is arithmetic.

    python3 evals/gap-study-2/takes.py --plan                 what the pre-registration plans
    python3 evals/gap-study-2/takes.py --add --task <id> --half <h> --model <m> --take <k>
    python3 evals/gap-study-2/takes.py --session-id <row-index>    the uuid for a committed row
    python3 evals/gap-study-2/takes.py --audit                every row, its commit, its uuid

THE PROBLEM THIS SOLVES. "Every take was pre-registered before it ran" is the load-bearing claim of
the whole study, and it is the one claim a reader cannot check by looking at a transcript. A run
that took four attempts and published the third can produce a ledger afterwards that says it always
meant to. Timestamps do not help: the run writes those too.

THE MECHANISM. A take's row is committed FIRST. The session the take runs in is then opened with
an id that is a pure function of that commit:

    session_id = uuid5(NAMESPACE, <the sha of the commit that introduced the row>)

The uuid is never stored in the row. It is recomputed from git at check time, and a transcript
whose session id does not equal it is not the take the row describes. Because a commit sha is not
known until the commit exists, and a session id must be chosen before the session opens, the order
is forced: row, commit, then session. A run cannot pick a take after seeing it.

WHAT MAKES IT ACTUALLY BIND, AND THE HOLE THAT HAD TO BE CLOSED. The formula keys on the commit
alone, so two rows committed together would share a session id -- and a run could then open two
sessions with one uuid and publish whichever it preferred, with the ledger still checking out. So
one commit introduces exactly one row. `--add` refuses while the previous row is uncommitted, and
`--audit` fails a commit that introduced more than one. That guard is the difference between a
rule and a proof.

The environment class is recorded per row, so a reader does not have to infer from the model id how a
row was meant to run. Round 2 has one class: the local tier was removed at CP0. What a take actually
ran under is not this field's to say; the driver's environment.json beside each take records it.

No model, no network, stdlib only.

Round 4's repo seam calls guard_registration before committing a row. A
RegistrationGuard holds only the registrations this process just committed in
its live block; a new instance holds none. A missing committed outcome therefore
refuses registration on every restart, including a lost commit after a pause.
CP2 calls registered only after its registration commit succeeds. After all of a
block's outcomes are committed, the next check starts a new block. The limit is
batch.BLOCK, and the committed final/cell state decides whether a slot is free.
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

OPEN_LIMIT = batch.BLOCK
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

# ROUND 2, CP3: the two ollama classes are gone with the local tier (CP0, amendment A5). Their only reader is
# --environment-class below, so a row can no longer be registered under a tier this study does not have.
ENVIRONMENT_CLASSES = ("claude-subscription-headless",)


def git(*args: str) -> str:
    out = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout.strip()


def namespace() -> uuid.UUID:
    """Fixed in the pre-registration, and recomputable by a reader from the string it names."""
    spec = prereg.load()["session_namespace"]
    derived = uuid.uuid5(uuid.NAMESPACE_URL, spec["derived_from"])
    if str(derived) != spec["uuid"]:
        raise SystemExit(
            f"the pre-registration's namespace uuid does not equal uuid5(NAMESPACE_URL, "
            f"{spec['derived_from']!r}). Recorded {spec['uuid']}, recomputed {derived}.")
    return derived


def session_id_for(row_commit_sha: str) -> str:
    return str(uuid.uuid5(namespace(), row_commit_sha))


def load_rows() -> list[dict]:
    if not LEDGER.is_file():
        return []
    return json.loads(LEDGER.read_text())["rows"]


def write_rows(rows: list[dict]) -> None:
    LEDGER.write_text(json.dumps({
        "role": "One row per pre-registered take, append-only. A row is committed before its take "
                "runs; the take's session id is uuid5(namespace, the sha of that row's commit) and "
                "is deliberately not stored here.",
        "rows": rows,
    }, indent=2) + "\n")


def uncommitted_ledger() -> bool:
    return bool(git("status", "--porcelain", "--", str(LEDGER.relative_to(REPO))))


def row_commits() -> dict[int, str]:
    """row index -> the sha of the commit that introduced it.

    Read by walking the ledger's history oldest-first and recording, for each commit, how many
    rows the file held afterwards. A row's commit is the first one at which it existed.
    """
    shas = git("log", "--reverse", "--format=%H", "--", str(LEDGER.relative_to(REPO))).split()
    seen: dict[int, str] = {}
    for sha in shas:
        blob = subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:{LEDGER.relative_to(REPO)}"],
                              capture_output=True, text=True)
        if blob.returncode != 0:
            continue
        try:
            n = len(json.loads(blob.stdout)["rows"])
        except Exception:
            continue
        for i in range(n):
            seen.setdefault(i, sha)
    return seen


# Where an attempt at a registered row can land (prereg attempt_layout). An attempt is found by the
# session id in its driver ledger, which is the only thing that ties it to a row.
ATTEMPT_KINDS = (("graded", "transcripts"), ("rehearsal", "rehearsals"), ("pause", "pauses"))
# The files the driver leaves in an attempt folder. ROUND 2, CP3: environment.json joins them, written before
# the first turn and routed with the attempt, so a folder holding only that record is still an attempt's.
TAKE_RECORD_FILES = ("driver-ledger.json", "transcript.jsonl", "environment.json")


def attempts_by_session() -> dict[str, list[tuple[str, Path]]]:
    """session id -> every take attempt folder whose driver ledger carries it, with its kind."""
    out: dict[str, list[tuple[str, Path]]] = {}
    for kind, folder in ATTEMPT_KINDS:
        root = HERE / folder
        if not root.is_dir():
            continue
        for led in sorted(root.glob("*/*/*/*/driver-ledger.json")):
            try:
                d = json.loads(led.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if d.get("kind") != "take" or not d.get("session_id"):
                continue
            out.setdefault(d["session_id"], []).append((kind, led.parent))
    return out


def unattributed_attempts() -> list[Path]:
    """Every folder under the three attempt roots that holds a driver ledger, a transcript or an environment
    record and that no attempt's ledger ties to a session id (review 13, blocker 1; the record, CP3).

    attempts_by_session() skips a ledger with no `kind: take` or no session id, so the ledger check
    that re-derives every attempt never saw such a folder, while the runner graded it. A folder a
    hand-written ledger put in a take's place is exactly that shape.
    """
    attributed = {d for hits in attempts_by_session().values() for _kind, d in hits}
    unattributed: list[Path] = []
    for _kind, folder in ATTEMPT_KINDS:
        root = HERE / folder
        if not root.is_dir():
            continue
        for f in sorted(root.rglob("*")):
            if f.name not in TAKE_RECORD_FILES or not f.is_file():
                continue
            d = f.parent
            # Round 1 excused one walk-era rehearsal folder here by name. Round 2 has no rehearsal
            # that predates attempt_layout, so no folder is excused: every one is attributed or named.
            if d in attributed:
                continue
            unattributed.append(d)
    return sorted(set(unattributed))


def attempt_kind(index: int, commits: dict[int, str], by_sid: dict) -> str | None:
    """graded, rehearsal or pause for a row that has been attempted; None if it has not."""
    sha = commits.get(index)
    if sha is None:
        return None
    hits = by_sid.get(session_id_for(sha), [])
    return hits[0][0] if hits else None


def cmd_add(args) -> int:
    pre = prereg.load()
    if prereg.is_frozen() is False and not args.allow_draft:
        print("the pre-registration is still a DRAFT. A take may not be registered against a file "
              "that can still change. Freeze it first, or pass --allow-draft for a dry run.")
        return 2

    if uncommitted_ledger():
        print("takes.json has uncommitted changes. One commit introduces exactly one row -- "
              "commit the previous row before adding another, or the two rows would share a "
              "session id and the binding would prove nothing.")
        return 2

    if args.task not in [t["id"] for t in pre["tasks"]]:
        print(f"unknown task {args.task!r}")
        return 2
    if args.model not in pre["models"]:
        print(f"unknown model {args.model!r}")
        return 2
    reason = prereg.not_run_reason(args.model)
    if reason:
        print(f"{args.model} does not run in this study:\n  {reason}\n"
              f"Its cells publish that reason. Registering a take against it would contradict the "
              f"record the study is going to publish.")
        return 2
    if not (1 <= args.take <= pre["n"]):
        print(f"take index {args.take} is outside 1..{pre['n']}; there are no retakes")
        return 2

    rows = load_rows()
    # A SLOT IS REGISTERED AGAIN ONLY AFTER A REHEARSAL OR A PAUSE (prereg attempt_layout).
    #
    # The first version refused any second row for a slot, so a slot whose attempt became a
    # rehearsal or a pause could never be retried, which requirement 4 says it is. A slot whose row
    # has not been attempted, or whose attempt was graded, still refuses: there are no retakes.
    commits = row_commits()
    by_sid = attempts_by_session()

    def outcome(i: int) -> str | None:
        return attempt_kind(i, commits, by_sid)

    def freeing_problems(i: int) -> list[str]:
        """REVIEW 17, F1. A rehearsal or a pause frees a slot, and --add asked only where the folder
        sat. So an attempt that `--ledger` refuses still freed its slot, and the retake would be
        driven before anything said no. The same check that guards publication guards the retake."""
        import contextlib
        import io
        import importlib.util
        spec = importlib.util.spec_from_file_location("gap_check_results_for_takes",
                                                      HERE / "check_results.py")
        cr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cr)
        hits = by_sid.get(session_id_for(commits[i]), []) if commits.get(i) else []
        if not hits:
            return []
        kind, d = hits[0]
        with contextlib.redirect_stdout(io.StringIO()):
            return cr.attempt_problems(kind, d, i, rows[i], cr._check_take())

    slot = [i for i, r in enumerate(rows) if (r["task"], r["half"], r["model"], r["take"])
            == (args.task, args.half, args.model, args.take)]
    for i in slot:
        if outcome(i) in ("rehearsal", "pause"):
            bad = freeing_problems(i)
            if bad:
                print(f"row {i}'s attempt freed this slot and the ledger check refuses it:")
                for b in bad:
                    print(f"  - {b}")
                print("A slot is registered again only behind an attempt that stands on its own "
                      "bytes. Fix the record, not the folder.")
                return 2
    live = [i for i in slot if outcome(i) not in ("rehearsal", "pause")]
    if live:
        state = "was graded" if outcome(live[0]) == "graded" else "has not been attempted"
        print(f"that cell's take {args.take} is already registered at row {live[0]}, and that row "
              f"{state}. A slot is registered again only after an attempt that became a rehearsal "
              f"or a pause; there are no retakes.")
        return 2

    # REVIEW 20, F4. The pre-registered order bound registration and not the order takes are driven:
    # every row could be registered first and driven in any order afterwards, and nothing a reader can
    # check would show it. A row is registered only once every committed row before it has been
    # attempted, so the registration order is the drive order.
    waiting = [i for i in range(len(rows)) if outcome(i) is None]
    if waiting:
        print(f"row(s) {waiting} are registered and not yet attempted. The pre-registered order is the "
              f"order takes are driven, so a row is registered only after every row before it has been "
              f"attempted.")
        return 2

    cell = [i for i, r in enumerate(rows)
            if (r["task"], r["half"], r["model"]) == (args.task, args.half, args.model)]
    counted = [i for i in cell if outcome(i) not in ("rehearsal", "pause")]
    if len(counted) >= pre["n"]:
        print(f"that cell already has {len(counted)} registered takes and n is {pre['n']}")
        return 2
    paused = [i for i in cell if outcome(i) == "pause"]
    if len(paused) >= int(pre["pause_cap"]):
        print(f"that cell has had {len(paused)} pauses and the cap is {pre['pause_cap']}. A pause frees a "
              f"slot on the driver's record alone, so it is capped like a rehearsal; the cell publishes "
              f"`incomplete — mechanical` and no further attempt is registered.")
        return 2
    rehearsed = [i for i in cell if outcome(i) == "rehearsal"]
    if len(rehearsed) >= int(pre["rehearsal_cap"]):
        print(f"that cell has had {len(rehearsed)} rehearsals and the cap is {pre['rehearsal_cap']}. "
              f"It publishes `incomplete — mechanical` with each reason, and no further attempt is "
              f"registered.")
        return 2

    rows.append({
        "task": args.task, "half": args.half, "model": args.model, "take": args.take,
        "order_index": args.order_index, "fixture_sha": args.fixture_sha,
        "environment_class": args.environment_class,
    })
    write_rows(rows)
    print(f"row {len(rows) - 1} written. Commit it, then the session id is:")
    print(f"  python3 {study.rel('takes.py')} --session-id {len(rows) - 1}")
    return 0


def cmd_session_id(index: int) -> int:
    rows = load_rows()
    if not (0 <= index < len(rows)):
        print(f"no row {index}")
        return 2
    commits = row_commits()
    if index not in commits:
        print(f"row {index} is not committed yet. Its session id does not exist until it is: "
              f"the uuid is a function of the commit that introduces it.")
        return 2
    sha = commits[index]
    print(f"row {index}: {rows[index]['task']} / {rows[index]['half']} / "
          f"{rows[index]['model']} / take {rows[index]['take']}")
    print(f"  row commit  {sha}")
    print(f"  session id  {session_id_for(sha)}")
    return 0


def cmd_audit() -> int:
    # The namespace is checked FIRST and unconditionally.
    #
    # It used to be checked only where a session id was computed, which meant an empty ledger
    # returned "nothing registered" and the namespace was never looked at -- a guard that could
    # not fire on the path most likely to reach it. Worse, the first tamper test on it passed for
    # the wrong reason and would have been recorded as a proof.
    namespace()

    rows = load_rows()
    commits = row_commits()
    problems: list[str] = []

    if not rows:
        print("the ledger is empty. No take has been registered, and that is not a pass.")
        return 2

    per_commit: dict[str, list[int]] = {}
    for i in range(len(rows)):
        sha = commits.get(i)
        if sha is None:
            problems.append(f"row {i} is not committed")
            continue
        per_commit.setdefault(sha, []).append(i)

    for sha, idxs in per_commit.items():
        if len(idxs) > 1:
            problems.append(
                f"commit {sha[:12]} introduced {len(idxs)} rows ({idxs}). They would share one "
                f"session id, so the pre-registration binding would prove nothing for any of them.")

    by_sid = attempts_by_session()
    print(f"{len(rows)} row(s), {len(per_commit)} commit(s)")
    for i, r in enumerate(rows):
        sha = commits.get(i, "")
        sid = session_id_for(sha) if sha else "(uncommitted)"
        print(f"  {i:3}  {r['task']:22} {r['half']:8} {r['model']:28} take {r['take']}  "
              f"{sha[:12] or '-':12}  {sid}  {attempt_kind(i, commits, by_sid) or 'not attempted'}")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nevery row is committed, and no commit introduced more than one")
    return 0


def cmd_plan() -> int:
    namespace()
    pre = prereg.load()
    tasks = [t["id"] for t in pre["tasks"]]

    # The planned count comes from prereg.cells(), the same function the take order permutes, so
    # the two can never disagree. An earlier version multiplied the numbers out here instead and
    # went on reporting 180 planned takes after two models had been marked not run -- the
    # second-source-of-truth problem again, this time between two of my own files.
    planned = prereg.cells()
    running = prereg.running_models()

    print(f"tasks   {len(tasks)}  {', '.join(tasks)}")
    print(f"models  {len(prereg.models())} in the fixed list, {len(running)} running")
    for m in prereg.models():
        reason = prereg.not_run_reason(m)
        print(f"        {m:28} {'runs' if not reason else 'NOT RUN — ' + reason[:60]}")
    print(f"n       {pre['n']} graded takes per half per model, no retakes")
    print(f"planned {len(planned)} takes")
    print(f"registered so far: {len(load_rows())}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="The pre-registered take ledger.")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--add", action="store_true")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--session-id", type=int, metavar="ROW")
    ap.add_argument("--ruling", choices=labels4.RULINGS)
    ap.add_argument("--slot")
    ap.add_argument("--attempt", type=int)
    ap.add_argument("--route", choices=labels4.ROUTES)
    ap.add_argument("--by")
    ap.add_argument("--task"); ap.add_argument("--half", choices=("positive", "control"))
    ap.add_argument("--model"); ap.add_argument("--take", type=int)
    ap.add_argument("--order-index", type=int, default=-1)
    ap.add_argument("--fixture-sha", default="")
    ap.add_argument("--environment-class", choices=ENVIRONMENT_CLASSES,
                    default="claude-subscription-headless")
    ap.add_argument("--allow-draft", action="store_true")
    args = ap.parse_args()

    if args.ruling is not None:
        if args.slot is None or args.attempt is None or args.by is None:
            ap.error("--ruling requires --slot, --attempt and --by")
        commit_ruling(slot=args.slot, attempt=args.attempt, word=args.ruling, route=args.route, by=args.by)
        print("one human ruling committed")
        return 0

    if args.plan:
        return cmd_plan()
    if args.audit:
        return cmd_audit()
    if args.session_id is not None:
        return cmd_session_id(args.session_id)
    if args.add:
        missing = [f for f in ("task", "half", "model", "take") if getattr(args, f) is None]
        if missing:
            ap.error(f"--add needs {', '.join('--' + m for m in missing)}")
        return cmd_add(args)
    ap.error("give --plan, --add, --audit or --session-id")


if __name__ == "__main__":
    raise SystemExit(main())
