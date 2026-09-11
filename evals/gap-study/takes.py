#!/usr/bin/env python3
"""The take ledger: a take is pre-registered before it runs, and the proof is arithmetic.

    python3 evals/gap-study/takes.py --plan                 what the pre-registration plans
    python3 evals/gap-study/takes.py --add --task <id> --half <h> --model <m> --take <k>
    python3 evals/gap-study/takes.py --session-id <row-index>    the uuid for a committed row
    python3 evals/gap-study/takes.py --audit                every row, its commit, its uuid

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

The environment class is recorded per row because a local take and a subscription take are not the
same experiment, and a reader should not have to infer which one a row was from the model id.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LEDGER = HERE / "takes.json"

sys.path.insert(0, str(HERE))
import prereg  # noqa: E402

ENVIRONMENT_CLASSES = ("claude-subscription-headless", "ollama-local", "ollama-local-control")


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



# The one rehearsal folder that predates attempt_layout: a walk's, named in its rule.
WALK_ERA_REHEARSALS = (("plan-gate", "1"),)


def unattributed_attempts() -> list[Path]:
    """Every folder under the three attempt roots that holds a driver ledger or a transcript and that
    no attempt's ledger ties to a session id (review 13, blocker 1).

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
            if f.name not in ("driver-ledger.json", "transcript.jsonl") or not f.is_file():
                continue
            d = f.parent
            if d in attributed:
                continue
            if folder == "rehearsals" and d.relative_to(root).parts in WALK_ERA_REHEARSALS:
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

    slot = [i for i, r in enumerate(rows) if (r["task"], r["half"], r["model"], r["take"])
            == (args.task, args.half, args.model, args.take)]
    live = [i for i in slot if outcome(i) not in ("rehearsal", "pause")]
    if live:
        state = "was graded" if outcome(live[0]) == "graded" else "has not been attempted"
        print(f"that cell's take {args.take} is already registered at row {live[0]}, and that row "
              f"{state}. A slot is registered again only after an attempt that became a rehearsal "
              f"or a pause; there are no retakes.")
        return 2

    cell = [i for i, r in enumerate(rows)
            if (r["task"], r["half"], r["model"]) == (args.task, args.half, args.model)]
    counted = [i for i in cell if outcome(i) not in ("rehearsal", "pause")]
    if len(counted) >= pre["n"]:
        print(f"that cell already has {len(counted)} registered takes and n is {pre['n']}")
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
    print(f"  python3 evals/gap-study/takes.py --session-id {len(rows) - 1}")
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

    local_status = (pre.get("local_tier") or {}).get("status")
    if local_status == "DROPPED":
        print("        the local control takes are dropped with the tier, same reason")
    print(f"registered so far: {len(load_rows())}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="The pre-registered take ledger.")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--add", action="store_true")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--session-id", type=int, metavar="ROW")
    ap.add_argument("--task"); ap.add_argument("--half", choices=("positive", "control"))
    ap.add_argument("--model"); ap.add_argument("--take", type=int)
    ap.add_argument("--order-index", type=int, default=-1)
    ap.add_argument("--fixture-sha", default="")
    ap.add_argument("--environment-class", choices=ENVIRONMENT_CLASSES,
                    default="claude-subscription-headless")
    ap.add_argument("--allow-draft", action="store_true")
    args = ap.parse_args()

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
