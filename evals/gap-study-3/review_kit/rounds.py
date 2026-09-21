#!/usr/bin/env python3
"""The round register: a review is pre-registered before it opens, exactly as a take is.

    python3 evals/gap-study-3/review_kit/rounds.py --add --kind prefreeze --folder <review folder>
    python3 evals/gap-study-3/review_kit/rounds.py --add --kind verify --folder <verifier folder>
    python3 evals/gap-study-3/review_kit/rounds.py --session-id <row-index>   the uuid for a committed row
    python3 evals/gap-study-3/review_kit/rounds.py --audit                    every row, its commit, its uuid
    python3 evals/gap-study-3/review_kit/rounds.py --check                    open rounds, and what blocks

THE PROBLEM THIS SOLVES. A round of blind review is only evidence if every round that ran is in the record.
A run that opened four reviewers and committed the two it liked can produce a folder of reports afterwards
that looks like two clean rounds. Round 2 and the pre-study relied on the run's own discipline for that.
Here the discipline is arithmetic, borrowed whole from takes.py:

    session_id = uuid5(NAMESPACE, <the sha of the commit that introduced the row>)

The row is committed FIRST, alone. The reviewer's session is then opened with an id that is a pure function
of that commit, and the reviewer's own report records it. A commit sha is not known until the commit exists
and a session id must be chosen before the session opens, so the order is forced: row, commit, then session.
One commit introduces exactly one row -- `--add` refuses while the previous row is uncommitted, and `--audit`
fails a commit that introduced more than one -- because two rows in one commit would share a session id, and
a run could then open two reviewers under one uuid and commit whichever it preferred.

WHAT A ROW BINDS. The round number, the sha256 of the prompt the reviewer was handed, the sha256 of the whole
input folder it was handed, and the commit the study was at when it launched. A report that reads bytes other
than the ones the row names is a report on a different study.

AN OPEN ROUND BLOCKS. A registered row whose report is not committed is an OPEN round: `--check` exits 1 and
names it. No report may be discarded, so an open round is either a report to commit or a void to record --
and a void is a row of its own, naming the row it voids, never an edit to that row.

A SESSION SPENT WITHOUT PRODUCING WORK IS RECORDED, NOT HIDDEN. A row's session id is a pure function of
its commit, so it can be opened exactly once: a launch that dies before the first agent turn -- a rate
limit, an interruption -- spends the id permanently, and the harness refuses to reuse it. The round is not
void (nothing about its blindness failed) and the goal file calls a rate limit a pause rather than a
refusal, so it does not count against the two-void rule. It is closed with `spent_without_work` and its
reason, and a fresh row re-runs it under a new commit and a new id. Deleting the dead session file to reuse
the id would work and is exactly what this register exists to make impossible: a run that could quietly
retire a session could quietly retire one that HAD produced work.

A SECOND VERIFIER RUN ON THE SAME COMMIT IS A MATERIAL FINDING. `--check` prints it as one; it does not fail
on it, because whether a re-run is warranted is the owner's call and the record's job is to show it happened.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_DIR = HERE.parent
REPO = STUDY_DIR.parent.parent
REGISTER = HERE / "rounds.json"
BRIEF = HERE / "BRIEF.md"

sys.path.insert(0, str(STUDY_DIR))
import prereg  # noqa: E402
import study  # noqa: E402
import takes as takes_mod  # noqa: E402

KINDS = ("prefreeze", "verify")
# Where each kind's report is committed, and under what name. The folders come from the binding.
REPORT = {"prefreeze": (study.REVIEW_DIR, "prefreeze-{n}.md"),
          "verify": (study.VERIFY_DIR, "verify-{n}.md")}


def git(*args: str) -> str:
    out = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout.strip()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def folder_sha256(folder: Path) -> str:
    """One digest over everything the reviewer was handed, path and bytes, excluding its clone's history.

    `study/.git` is left out: a clone's object files are not reproducible byte for byte, and what the
    reviewer reads out of the clone is bound by `launch_commit` instead.
    """
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder).as_posix()
        if rel == "study/.git" or rel.startswith("study/.git/"):
            continue
        if not p.is_file():
            continue
        h.update(rel.encode())
        h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def load() -> list[dict]:
    if not REGISTER.is_file():
        return []
    return json.loads(REGISTER.read_text())["rows"]


def write(rows: list[dict]) -> None:
    REGISTER.write_text(json.dumps({
        "role": "One row per round of blind review or final verification, append-only. A row is committed "
                "alone and before its reviewer opens; that reviewer's session id is "
                "uuid5(namespace, the sha of the row's commit) and is deliberately not stored here.",
        "rows": rows,
    }, indent=2) + "\n")


def uncommitted() -> bool:
    return bool(git("status", "--porcelain", "--", str(REGISTER.relative_to(REPO))))


def row_commits() -> dict[int, str]:
    """row index -> the sha of the commit that introduced it, read the way takes.py reads its ledger."""
    shas = git("log", "--reverse", "--format=%H", "--", str(REGISTER.relative_to(REPO))).split()
    seen: dict[int, str] = {}
    for sha in shas:
        blob = subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:{REGISTER.relative_to(REPO)}"],
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


def session_id_for(row_commit_sha: str) -> str:
    """The same namespace the takes use: one study, one namespace, recomputable from the frozen file."""
    return str(uuid.uuid5(takes_mod.namespace(), row_commit_sha))


def report_path(row: dict) -> Path:
    folder, name = REPORT[row["kind"]]
    return STUDY_DIR / folder / name.format(n=row["n"])


def blindness_path(row: dict) -> Path:
    """The blindness record committed beside the report, which names the session it read."""
    return report_path(row).with_name(report_path(row).stem + "-blindness.txt")


def committed(path: Path) -> bool:
    rel = str(path.relative_to(REPO))
    return subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"HEAD:{rel}"],
                          capture_output=True).returncode == 0


def add(kind: str, folder: Path, voids: int | None) -> int:
    if uncommitted():
        print("refusing: the register has an uncommitted row. One commit introduces exactly one row, or two "
              "rounds would share a session id. Commit the previous row first.")
        return 1
    if not folder.is_dir():
        print(f"refusing: {folder} is not a folder. The row binds the bytes the reviewer is handed, so the "
              f"folder must be built first (review_kit/build_kit.py).")
        return 1
    rows = load()
    open_rows = [r for r in rows if not r.get("voided_by") and not r.get("spent_without_work")
                 and not committed(report_path(r))]
    if open_rows:
        names = ", ".join(f"{r['kind']} {r['n']}" for r in open_rows)
        print(f"refusing: {len(open_rows)} open round(s) with no committed report ({names}). A report is "
              f"committed or a void is recorded before the next round opens; no report is discarded.")
        return 1
    n = max([r["n"] for r in rows if r["kind"] == kind], default=0) + 1
    row = {"n": n, "kind": kind,
           "prompt_sha256": sha256_bytes(BRIEF.read_bytes()),
           "input_sha256": folder_sha256(folder),
           "launch_commit": git("rev-parse", "HEAD"),
           "added": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "voids": voids}
    rows.append(row)
    write(rows)
    print(json.dumps(row, indent=2))
    print(f"\nrow {len(rows) - 1} written to {REGISTER.relative_to(REPO)}. Commit it ALONE, then read its "
          f"session id with:\n  python3 {study.rel('review_kit/rounds.py')} --session-id {len(rows) - 1}")
    return 0


def audit() -> int:
    rows, commits, bad = load(), row_commits(), []
    by_commit: dict[str, list[int]] = {}
    for i, _ in enumerate(rows):
        sha = commits.get(i)
        if sha is None:
            bad.append(f"row {i} is not committed")
            continue
        by_commit.setdefault(sha, []).append(i)
    for sha, idxs in by_commit.items():
        if len(idxs) > 1:
            bad.append(f"{sha[:12]} introduced rows {idxs}: they would share one session id")
    for i, r in enumerate(rows):
        sha = commits.get(i)
        sid = session_id_for(sha) if sha else "-"
        rep = report_path(r)
        state = ("VOIDED by row " + str(r["voided_by"])) if r.get("voided_by") else \
                ("SPENT without work — " + r["spent_without_work"]) if r.get("spent_without_work") else \
                ("report committed" if committed(rep) else "OPEN — no committed report")
        print(f"row {i}  {r['kind']} {r['n']}  commit {(sha or '-')[:12]}  session {sid}  "
              f"prompt {r['prompt_sha256'][:12]}  input {r['input_sha256'][:12]}  {state}")
    for b in bad:
        print(f"FAIL {b}")
    return 1 if bad else 0


def check() -> int:
    rows = load()
    problems, notes = [], []
    prompt = sha256_bytes(BRIEF.read_bytes()) if BRIEF.is_file() else None
    commits = row_commits()
    for i, r in enumerate(rows):
        if r.get("voided_by") or r.get("spent_without_work"):
            continue
        rep = report_path(r)
        if not committed(rep):
            problems.append(f"{r['kind']} round {r['n']} is OPEN: {rep.relative_to(REPO)} is not committed. "
                            f"An open round blocks the freeze and DONE.")
        else:
            # THE BINDING, ENFORCED HERE RATHER THAN AT LAUNCH. The launcher can be given any session id,
            # or none; what makes the row mean something is that the COMMITTED report records the id this
            # row derives. A reviewer opened under any other id did not review for this row, and a run
            # that opened four and kept two cannot produce a report that satisfies this.
            sha = commits.get(i)
            if sha is None:
                problems.append(f"{r['kind']} round {r['n']} has a committed report but its own row is not "
                                f"committed, so no session id can be derived for it")
            else:
                want = session_id_for(sha)
                blind = blindness_path(r)
                if not blind.is_file():
                    problems.append(f"{blind.relative_to(REPO)} is missing: the report is committed and "
                                    f"its blindness record is not, so nothing binds it to its row")
                elif want not in blind.read_text(errors="replace"):
                    problems.append(
                        f"{blind.relative_to(REPO)} does not name the session id this row derives "
                        f"({want}). The reviewer it read was not the one this row registered.")
        if prompt and r["prompt_sha256"] != prompt:
            problems.append(f"{r['kind']} round {r['n']} was launched on a prompt whose sha256 is "
                            f"{r['prompt_sha256'][:12]}; review_kit/BRIEF.md now hashes to {prompt[:12]}. The "
                            f"prompt is pinned byte-identical across rounds.")
    seen: dict[str, list[int]] = {}
    for r in rows:
        if r["kind"] == "verify" and not r.get("voided_by") and not r.get("spent_without_work"):
            seen.setdefault(r["launch_commit"], []).append(r["n"])
    for sha, ns in seen.items():
        if len(ns) > 1:
            notes.append(f"MATERIAL FINDING: verifier runs {ns} both launched at {sha[:12]}. A second verifier "
                         f"run on the same commit is itself a material finding and is reported as one.")
    voided = [r for r in rows if r.get("voided_by")]
    if len(voided) >= 2:
        problems.append(f"{len(voided)} voided rounds: two voids is BLOCKED by the goal file.")
    for n in notes:
        print(n)
    for p in problems:
        print(f"FAIL {p}")
    if not problems:
        live = [r for r in rows if not r.get("voided_by") and not r.get("spent_without_work")]
        spent = [r for r in rows if r.get("spent_without_work")]
        if spent:
            print(f"{len(spent)} row(s) closed as spent without work (a rate limit or an interruption "
                  f"before the first agent turn). Not voids: they do not count against the two-void rule.")
        if not live:
            # An empty gate is said out loud, never logged as a pass: nothing is registered yet, so this
            # check has graded nothing and its green means only that.
            print(f"ok, having graded 0 rounds: the register is empty, so nothing here is evidence about any "
                  f"round. Prompt pinned at {(prompt or '-')[:12]}.")
        else:
            print(f"ok: {len(live)} registered round(s) graded, every report committed, "
                  f"{len(voided)} voided; prompt pinned at {(prompt or '-')[:12]}")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--add", action="store_true")
    g.add_argument("--session-id", type=int, metavar="ROW")
    g.add_argument("--audit", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--close-spent", type=int, metavar="ROW",
                   help="close a row whose session was spent without producing work (a rate limit or an "
                        "interruption before the first agent turn). Not a void: it does not count against "
                        "the two-void rule, because nothing about the round's blindness failed")
    ap.add_argument("--kind", choices=KINDS)
    ap.add_argument("--folder", type=Path)
    ap.add_argument("--voids", type=int, default=None,
                    help="the row index this round re-runs after a void; the voided row records voided_by")
    ap.add_argument("--reason", help="with --close-spent: what spent it, in plain words")
    args = ap.parse_args()
    if args.close_spent is not None:
        if not args.reason:
            print("--close-spent needs --reason: a row closed with no reason is a row quietly retired")
            return 2
        rows = load()
        if not 0 <= args.close_spent < len(rows):
            print(f"no row {args.close_spent}; the register holds {len(rows)}")
            return 2
        r = rows[args.close_spent]
        if committed(report_path(r)):
            print(f"refusing: {r['kind']} round {r['n']} has a committed report. A round that produced "
                  f"work is never closed as spent.")
            return 1
        r["spent_without_work"] = args.reason
        r["spent_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        write(rows)
        print(json.dumps(r, indent=2))
        print(f"\nrow {args.close_spent} closed as spent. Commit it, then register the re-run with "
              f"--add --kind {r['kind']} --folder <a freshly built folder>.")
        return 0

    if args.add:
        if not args.kind or not args.folder:
            print("--add needs --kind and --folder")
            return 2
        return add(args.kind, args.folder.resolve(), args.voids)
    if args.session_id is not None:
        rows = load()
        if not 0 <= args.session_id < len(rows):
            print(f"no row {args.session_id}; the register holds {len(rows)}")
            return 2
        sha = row_commits().get(args.session_id)
        if sha is None:
            print(f"row {args.session_id} is not committed yet; a session id exists only once its row does")
            return 1
        print(session_id_for(sha))
        return 0
    if args.audit:
        return audit()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
