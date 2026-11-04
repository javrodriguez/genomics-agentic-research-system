#!/usr/bin/env python3
"""The round register: a review is pre-registered before it opens, exactly as a take is.

    python3 evals/gap-study-4/review_kit/rounds.py --add --kind prefreeze --folder <review folder>
    python3 evals/gap-study-4/review_kit/rounds.py --add --kind verify --folder <verifier folder>
    python3 evals/gap-study-4/review_kit/rounds.py --session-id <row-index>   the uuid for a committed row
    python3 evals/gap-study-4/review_kit/rounds.py --audit                    every row, its commit, its uuid
    python3 evals/gap-study-4/review_kit/rounds.py --check                    open rounds, and what blocks

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
and a void is a row of its own, naming the row it voids (`voids`); the one later mark on the voided row is its
voided_by, admitted only as the index of that later row (in_place_problems), never any other edit to it.

A SESSION SPENT WITHOUT PRODUCING WORK IS RECORDED, NOT HIDDEN. A row's session id is a pure function of
its commit, so it can be opened exactly once: a launch that dies before the first agent turn -- a rate
limit, an interruption -- spends the id permanently, and the harness refuses to reuse it. The round is not
void (nothing about its blindness failed) and the goal file calls a rate limit a pause rather than a
refusal, so it does not count against the two-void rule. It is closed with `spent_without_work` and its
reason, and a fresh row re-runs it under a new commit and a new id. Deleting the dead session file to reuse
the id would work and is exactly what this register exists to make impossible: a run that could quietly
retire a session could quietly retire one that HAD produced work.

A SESSION CUT OFF AFTER ITS FIRST AGENT TURN AND BEFORE ITS REPORT IS A PAUSE, AND IS RESUMED. Round 3's
reviewer was ended by the subscription's session limit at its 39th turn with no report written. That is
neither spent-without-work (it had worked) nor void (nothing about its blindness failed), and no report
exists to commit or discard. The row stays OPEN and the same session is continued under the same id with
`launch.py <folder> <id> --resume`, which the harness supports; a fresh id would be a second reviewer on
the same bytes, and this register exists to make that visible. The report the resumed session writes
records the id its row derives, as any report must, and --check binds it exactly as before.

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


MANIFEST = "folder-manifest.txt"


def manifest_text(folder: Path) -> str:
    """Everything the reviewer is handed, one `<sha256>  <path>` line per file, in the order folder_sha256 reads.

    `study/.git` is left out: a clone's object files are not reproducible byte for byte, and what the
    reviewer reads from the clone is bound by `launch_commit` instead.
    """
    lines = []
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder).as_posix()
        if rel == "study/.git" or rel.startswith("study/.git/"):
            continue
        if not p.is_file():
            continue
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}\n")
    return "".join(lines)


def manifest_digest(text: str) -> str:
    """The row's input_sha256, from the manifest's own lines: each path, a NUL, then its file's sha256.

    Lane blindness-sidechains (the closure review of fff7e0d3, finding 4): the manifest is written beside the
    folder before the row is hashed, and the row's input_sha256 is this digest of it, so the committed row binds
    the per-file manifest with no new field. blindness.py reads the same digest back.
    """
    h = hashlib.sha256()
    for line in text.splitlines():
        sha, rel = line.split("  ", 1)
        h.update(rel.encode())
        h.update(b"\0")
        h.update(bytes.fromhex(sha))
    return h.hexdigest()


def folder_sha256(folder: Path) -> str:
    """One digest over everything the reviewer was handed, path and bytes, excluding its clone's history."""
    return manifest_digest(manifest_text(folder))


def write_manifest(folder: Path) -> str:
    """Write the folder's manifest beside it, `<folder>-launch/folder-manifest.txt`, and return its text."""
    text = manifest_text(folder)
    side = folder.parent / (folder.name + "-launch")
    side.mkdir(exist_ok=True)
    (side / MANIFEST).write_text(text)
    return text


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


def register_at(rev: str) -> tuple[str, list | None]:
    """The confirm review of b968597e, NIT E: ("rows", rows), ("absent", None) when the register is not in that
    commit, or ("unreadable", None) when the commit or its blob cannot be read or is not the register's shape."""
    reg = str(REGISTER.relative_to(REPO))
    run = lambda *a: subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True)  # noqa: E731
    if run("cat-file", "-e", f"{rev}^{{commit}}").returncode:
        return "unreadable", None
    listed = run("ls-tree", "--name-only", rev, "--", reg)
    if listed.returncode:
        return "unreadable", None
    if reg not in listed.stdout.splitlines():
        return "absent", None
    blob = run("show", f"{rev}:{reg}")
    try:
        rows = json.loads(blob.stdout)["rows"] if blob.returncode == 0 else None
    except Exception:
        rows = None
    return ("rows", rows) if isinstance(rows, list) else ("unreadable", None)


def register_history() -> list[tuple[str, list[str]]] | None:
    """Every commit on any ref or reflog entry that touched the register, with full history (a merge that keeps one
    parent's register still lists the other side's commits), each with its parents; None when git cannot read it."""
    out = subprocess.run(["git", "-C", str(REPO), "log", "--all", "--reflog", "--full-history", "--format=%H %P",
                          "--", str(REGISTER.relative_to(REPO))], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return [(ln.split()[0], ln.split()[1:]) for ln in out.stdout.splitlines() if ln.strip()]


def introducers() -> tuple[dict[int, str], list[str]]:
    """The confirm review of b968597e, BLOCKER A: row index -> the one commit, on any ref or reflog and with full
    history, that holds the row while none of its parents does; and the problems: a row introduced by more than one
    commit (a side branch re-adding it, merged in), or a history git cannot read."""
    hist = register_history()
    if hist is None:
        return {}, ["the history of the register cannot be read, so no row's introducing commit is known"]
    found: dict[int, list[str]] = {}
    problems: list[str] = []
    for sha, parents in hist:
        state, rows = register_at(sha)
        if state == "unreadable":
            problems.append(f"the register at {sha[:12]} cannot be read")
            continue
        if rows is None:
            continue
        held = 0
        for parent in parents:
            pstate, prows = register_at(parent)
            if pstate == "unreadable":
                problems.append(f"the register at {parent[:12]} cannot be read")
            held = max(held, len(prows or []))
        for i in range(held, len(rows)):
            found.setdefault(i, []).append(sha)
    one = {i: shas[0] for i, shas in found.items() if len(shas) == 1}
    problems += [f"row {i} was introduced by {len(shas)} commits ({', '.join(s[:12] for s in shas)}): a row is added "
                 f"once, by one commit" for i, shas in sorted(found.items()) if len(shas) > 1]
    return one, problems


def row_commits() -> dict[int, str]:
    """row index -> the one commit that introduced it (introducers; the freeze reads it the same way)."""
    return introducers()[0]


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


def ever_committed(path: Path) -> bool:
    """Pre-freeze review 6, M1 (lane fold8/review-binding): whether any commit on any ref (git log --all) touched the
    file, so a report deleted from HEAD's tree still reads as committed. An unreadable history reads as committed."""
    out = subprocess.run(["git", "-C", str(REPO), "log", "--all", "--reflog", "--full-history", "--format=%H", "-1", "--",
                          str(path.relative_to(REPO))], capture_output=True, text=True)
    return out.returncode != 0 or bool(out.stdout.strip())


def add(kind: str, folder: Path, voids: int | None) -> int:
    # Lane fold11/freeze-recheck (the fold's gate review, m1): a prefreeze row after the freeze refuses publication for good,
    # whatever its state (freeze.later_review_problem, re-run by check_results). Verify rows are the study's later road.
    if kind == "prefreeze" and (STUDY_DIR / "prereg.json").is_file():
        print("refusing: this study is frozen, so a prefreeze row can only stop its publication. Nothing was written.")
        return 1
    if uncommitted():
        print("refusing: the register has an uncommitted row. One commit introduces exactly one row, or two "
              "rounds would share a session id. Commit the previous row first.")
        return 1
    if not folder.is_dir():
        print(f"refusing: {folder} is not a folder. The row binds the bytes the reviewer is handed, so the "
              f"folder must be built first (review_kit/build_kit.py).")
        return 1
    # Pre-freeze review 7, m-new-2 (lane fold9/round7-residual): launch_commit is HEAD here and the kit's COMMIT is HEAD
    # when the kit was built, and nothing compared them, so a commit between the two became the code the launch binding
    # holds, unread by the reviewer.
    commit_file = folder / "COMMIT"
    kit_commit = commit_file.read_text().strip() if commit_file.is_file() else None
    head = git("rev-parse", "HEAD")
    if kit_commit != head:
        print(f"refusing: {commit_file} names {kit_commit!r}, not HEAD {head}: a row binds the commit its reviewer is "
              f"handed, so build the kit at this commit (review_kit/build_kit.py).")
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
    manifest = write_manifest(folder)
    row = {"n": n, "kind": kind,
           "prompt_sha256": sha256_bytes(BRIEF.read_bytes()),
           "input_sha256": manifest_digest(manifest),
           "launch_commit": head,
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


CLOSING = {"spent_without_work", "spent_at", "voided_by"}


def in_place_problems(rows: list[dict], commits: dict[int, str]) -> list[str]:
    """The review of bc438542, BLOCKER 1: a row is append-only too. Each row at HEAD must be the row its introducing
    commit added, except the fields the kit's own writers set later, each only in its writer's shape:
    spent_without_work and spent_at together, as --close-spent writes them (a non-empty reason, an ISO UTC time); and
    voided_by, the index of a later row whose `voids` (written by --add --voids) names this row. No kit command writes
    voided_by today, so it is admitted only in the one shape the register itself can vouch for."""
    out = []
    reg = str(REGISTER.relative_to(REPO))
    for i, row in enumerate(rows):
        sha = commits.get(i)
        if sha is None:
            continue                             # an uncommitted row is reported by the open-round check
        blob = subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:{reg}"], capture_output=True, text=True)
        try:
            intro = json.loads(blob.stdout)["rows"][i]
        except Exception:
            out.append(f"row {i}'s introducing commit {sha[:12]} cannot be read, so the row cannot be shown unedited")
            continue
        if not isinstance(row, dict) or not isinstance(intro, dict) or CLOSING & set(intro):
            out.append(f"row {i} is not the row {sha[:12]} introduced")
            continue
        kept = {k: v for k, v in row.items() if k not in CLOSING}
        if kept != intro:
            names = sorted(k for k in set(kept) | set(intro) if kept.get(k) != intro.get(k))
            out.append(f"row {i} ({row.get('kind')} {row.get('n')}) was edited in place since {sha[:12]} introduced it "
                       f"({', '.join(names)}; launch_commit and every other field are written once, by --add)")
            continue
        added = set(row) & CLOSING
        spent = {"spent_without_work", "spent_at"}
        if added & spent:
            reason, at = row.get("spent_without_work"), row.get("spent_at")
            try:
                when = datetime.fromisoformat(at) if isinstance(at, str) else None
            except ValueError:
                when = None
            if not (spent <= added and isinstance(reason, str) and reason.strip() and when is not None
                    and when.utcoffset() is not None and not when.utcoffset()):
                out.append(f"row {i} carries spent fields that are not --close-spent's shape (a reason and an ISO UTC "
                           f"spent_at, both): edited in place by hand")
        if "voided_by" in added:
            j = row.get("voided_by")
            if not (type(j) is int and i < j < len(rows) and isinstance(rows[j], dict) and rows[j].get("voids") == i):
                out.append(f"row {i}'s voided_by {j!r} names no later row whose voids is {i}: edited in place by hand")
    return out


# Javier's word of Wed 4 Nov 2026 (OD186, "last-review yes"): round 10 is the last review, under a stop rule written into BRIEF.md.
# So the prompt is pinned in two named eras, and only these: prefreeze rounds 1-9 on the first, every later row on the second. A
# verify row counts its own n from 1 and comes after the freeze, so it is on the second whatever its n.
PROMPT_ROUNDS_1_TO_9 = "4246efa5b4093e30e23bf62966cda268e45b62101488189ceeb79373e48984cc"
PROMPT_FROM_ROUND_10 = "bd667a759ae3ce392447c5df8251e29b713ab1c03363a860a2771305b5f6af31"
LAST_ROUND_ON_THE_FIRST_PROMPT = 9


def prompt_problem(row: dict) -> str | None:
    """The prompt this row must have been launched on, by its kind and number; any other refuses."""
    first = row["kind"] == "prefreeze" and row["n"] <= LAST_ROUND_ON_THE_FIRST_PROMPT
    wanted = PROMPT_ROUNDS_1_TO_9 if first else PROMPT_FROM_ROUND_10
    if row.get("prompt_sha256") == wanted:
        return None
    return (f"{row['kind']} round {row['n']} was launched on a prompt whose sha256 is {str(row.get('prompt_sha256'))[:12]}; this "
            f"row's prompt is {wanted[:12]}. The prompt is pinned in two eras (OD186) and no third.")


def check() -> int:
    rows = load()
    problems, notes = [], []
    prompt = sha256_bytes(BRIEF.read_bytes()) if BRIEF.is_file() else None
    commits = row_commits()
    if prompt and prompt != PROMPT_FROM_ROUND_10:
        problems.append(f"review_kit/BRIEF.md hashes to {prompt[:12]}, not {PROMPT_FROM_ROUND_10[:12]}: the prompt is pinned in two "
                        f"eras (OD186) and no third.")
    for i, r in enumerate(rows):
        if r.get("voided_by") or r.get("spent_without_work"):
            # Pre-freeze review 6, M1 (lane fold8/review-binding): a closed row skips the open-round check, so one
            # commit deleting a report and marking its row spent dropped a registered review. A round whose report was
            # ever committed produced work and is never spent, and a void records no report.
            if ever_committed(report_path(r)):
                problems.append(f"{r['kind']} round {r['n']} is marked "
                                f"{'voided' if r.get('voided_by') else 'spent without work'}, and its report "
                                f"{report_path(r).relative_to(REPO)} was committed (git log --all): a registered "
                                f"review is never dropped")
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
        if prompt and prompt_problem(r):
            problems.append(prompt_problem(r))
    # Pre-freeze review 6, M1 (lane fold8/review-binding): the register is append-only, so no committed version of it
    # on any ref may hold more rows than HEAD's; a row cut out drops its round as surely as a report deleted.
    reg = str(REGISTER.relative_to(REPO))
    log = subprocess.run(["git", "-C", str(REPO), "log", "--all", "--reflog", "--full-history", "--format=%H", "--",
                          reg], capture_output=True, text=True)
    for sha in log.stdout.split() if log.returncode == 0 else []:
        state, version = register_at(sha)
        if state == "absent":
            continue                         # a commit that deleted the register holds no version of it
        if state == "unreadable":
            # the review of bc438542, NIT 2, and the confirm review of b968597e, NIT E: an unreadable version (a bad
            # blob, a missing object) is a problem, never zero rows and never skipped
            problems.append(f"{reg} at {sha[:12]} cannot be read as the register, so its rows cannot be shown "
                            f"append-only")
            break
        held = len(version)
        # the confirm review of b968597e, BLOCKER A: every version of every row equals HEAD's, closing fields aside
        strip = lambda r: {k: v for k, v in r.items() if k not in CLOSING} if isinstance(r, dict) else r  # noqa: E731
        moved = [i for i, old in enumerate(version[:len(rows)]) if strip(old) != strip(rows[i])]
        if moved:
            problems.append(f"row {moved[0]} of {reg} at {sha[:12]} is not HEAD's row {moved[0]} (closing fields "
                            f"aside): a row is written once, on every branch")
        if held > len(rows):
            problems.append(f"{reg} at {sha[:12]} holds {held} row(s) and HEAD's holds {len(rows)}: the register is "
                            f"append-only, so a registered round was cut out")
            break
    if log.returncode != 0:
        problems.append(f"the history of {reg} cannot be read, so its rows cannot be shown append-only")
    problems.extend(introducers()[1])                # the confirm review of b968597e, BLOCKER A
    problems.extend(in_place_problems(rows, commits))
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
                  f"{len(voided)} voided; prompt pinned at {(prompt or '-')[:12]}, rounds 1-{LAST_ROUND_ON_THE_FIRST_PROMPT} at {PROMPT_ROUNDS_1_TO_9[:12]}")
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
        if committed(report_path(r)) or ever_committed(report_path(r)):
            print(f"refusing: {r['kind']} round {r['n']} has a committed report (at HEAD or in any ref's history). "
                  f"A round that produced work is never closed as spent.")
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
