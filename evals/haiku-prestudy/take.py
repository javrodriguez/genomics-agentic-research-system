#!/usr/bin/env python3
"""Run one pre-registered take end to end: preflight, register and commit the row, drive, postflight, commit.

    python3 -u evals/haiku-prestudy/take.py --take <k>

Run it under nohup with its output outside the repository; a background command dies with the session that
started it, and a killed take leaves a partial attempt that reads as valid.

PREFLIGHT, each a refusal before anything is written:
  - the pre-registration is frozen, and `claude --version` reads the harness version it froze;
  - no live machine reservation (workspaces/.machine-reserved with an `until` still ahead): another goal is
    measuring this machine;
  - the repository's root CLAUDE.md is byte-identical at HEAD and at export_at: the take checker compares the
    instruction files the session loaded against the working tree, and the checkout the session runs in is
    exported from export_at;
  - the repository's status is clean and `main` is even with `origin/main`, so the row commit lands on what is
    pushed and nothing else rides in with it.
THE ROW: `takes.py --add` for this take, then a commit of takes.json alone. The session id is uuid5 of that commit.
DRIVE: the copied driver, `--row <i> --at <export_at>`, exactly as round 2 drove a take.
POSTFLIGHT: the repository's status may differ from the preflight only under this study's attempt folders
(transcripts/, rehearsals/, pauses/). Anything else changed means the session under test, which may run any
Python, wrote outside its run tree: the take is refused, nothing is committed, and the change is printed for a
person to read. Otherwise the attempt is read by outcome.py and committed unedited as `take:`.
Never pushes: the push goes through the scanned door.

No model is called by this file itself; the driver opens the session. stdlib only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
REL = "evals/haiku-prestudy"
ATTEMPT_DIRS = tuple(f"{REL}/{d}/" for d in ("transcripts", "rehearsals", "pauses"))
RESERVATION = REPO.parent / ".machine-reserved"
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402


def amended_attempt_paths(pre: dict) -> list[str]:
    """Attempt paths a recorded amendment moved, as repository-relative prefixes (amendment 3).

    The deleted-attempt guard reads history with --no-renames, so a move an amendment records reads there as a
    deletion. An amendment names where the attempt sat; only those paths are forgiven, and each is in the frozen
    file for a reader to check. Any other deletion under the attempt roots still refuses.
    """
    out = []
    for a in pre.get("amendments") or []:
        before = a.get("before")
        if isinstance(before, dict) and before.get("path"):
            out.append("evals/haiku-prestudy/" + before["path"].strip("/"))
    return out


def git(*args: str, check: bool = False) -> str:
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def status() -> set[str]:
    return {line for line in git("status", "--porcelain", "--untracked-files=all").splitlines() if line.strip()}


def reservation_live() -> str | None:
    if not RESERVATION.is_file():
        return None
    text = RESERVATION.read_text(errors="replace")
    for line in text.splitlines():
        if line.lower().startswith("until"):
            try:
                until = datetime.fromisoformat(line.split(":", 1)[1].strip())
            except ValueError:
                return f"a reservation whose until-line cannot be read: {line!r}"
            now = datetime.now(until.tzinfo) if until.tzinfo else datetime.now()
            return f"reserved until {until.isoformat()}" if until > now else None
    return "a reservation with no until-line"


def commit_file(message: str) -> Path:
    path = REPO.parent / f".haiku-prestudy-commit-message-{datetime.now().strftime('%H%M%S%f')}.txt"
    path.write_text(message)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--take", type=int, required=True)
    args = ap.parse_args()
    pre = prereg.require_frozen("running a take")
    model = pre["models"][0]
    task, half = pre["take_order"][args.take - 1][0], pre["take_order"][args.take - 1][1]

    problems = []
    graded = sorted(int(p.name) for p in (HERE / "transcripts" / task / half / model).glob("*") if p.name.isdigit())
    if graded != list(range(1, args.take)):
        problems.append(f"take {args.take} is not next in the pre-registered order: graded so far {graded}")
    import hashlib
    for f, sha in (pre.get("pinned_files") or {}).items():
        got = hashlib.sha256((HERE / f).read_bytes()).hexdigest() if (HERE / f).is_file() else None
        if got != sha:
            problems.append(f"{f} is not the file the freeze pinned")
    # --no-renames: git reads a graded folder moved into rehearsals/ as a rename, and a rename is not a deletion.
    import importlib.util
    _cm = importlib.util.spec_from_file_location("prestudy_copy_manifest", HERE / "copy_manifest.py")
    cm = importlib.util.module_from_spec(_cm)
    _cm.loader.exec_module(cm)
    problems += cm.problems(cm.derive())
    deleted = git("log", "--no-renames", "--diff-filter=D", "--name-only", "--format=", "--", *ATTEMPT_DIRS).split()
    amended = amended_attempt_paths(pre)
    deleted = [d for d in deleted if not any(d == m or d.startswith(m + "/") for m in amended)]
    if deleted:
        problems.append(f"an attempt file was deleted in this repository's history ({deleted[:3]}): its row would "
                        f"read as unattempted")
    version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    if not version.startswith(pre["harness"]["claude_version"]):
        problems.append(f"claude --version reads {version!r}, the freeze read {pre['harness']['claude_version']}")
    live = reservation_live()
    if live:
        problems.append(f"the machine is reserved by another goal ({live})")
    if subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", pre["export_at"], "HEAD", "--", "CLAUDE.md"]).returncode:
        problems.append("the root CLAUDE.md at HEAD differs from export_at's, and the checker reads HEAD's")
    before = status()
    if before:
        problems.append(f"the repository has uncommitted changes: {sorted(before)[:5]}")
    git("fetch", "-q", "origin")
    ahead_behind = git("rev-list", "--left-right", "--count", "HEAD...origin/main").split()
    if ahead_behind != ["0", "0"]:
        problems.append(f"main and origin/main differ (ahead, behind = {ahead_behind}); push or fast-forward first")
    if problems:
        print("refusing to start the take:\n  - " + "\n  - ".join(problems))
        return 2

    py = sys.executable
    add = subprocess.run([py, str(HERE / "takes.py"), "--add", "--task", task, "--half", half, "--model", model,
                          "--take", str(args.take)], capture_output=True, text=True)
    print(add.stdout.strip())
    if add.returncode != 0:
        return add.returncode
    row = len(json.loads((HERE / "takes.json").read_text())["rows"]) - 1
    msg = commit_file(f"take: row {row} registered -- {task} / {half} / {model} / take {args.take}\n\n"
                      f"Committed before its session opens; the session id is uuid5 of this commit.\n")
    git("add", "--", f"{REL}/takes.json", check=True)
    staged = git("diff", "--cached", "--name-only").split()
    if staged != [f"{REL}/takes.json"]:
        git("reset", "-q")
        print(f"refusing: the row commit would land {staged}")
        return 2
    git("commit", "-q", "-F", str(msg), check=True)
    msg.unlink()
    row_commit = git("rev-parse", "HEAD").strip()
    print(f"row {row} committed as {row_commit[:12]}")
    before = status()

    drive = subprocess.run([py, "-u", str(HERE / "drive.py"), "--task", task, "--half", half, "--row", str(row),
                            "--at", pre["export_at"]])
    print(f"driver exited {drive.returncode}")

    after = status()
    changed = sorted(after - before)
    # --untracked-files=all lists files, never folders, so a prefix test is exact.
    outside = [c for c in changed if not c[3:].startswith(ATTEMPT_DIRS)]
    if outside:
        print("REFUSING to file this take: the repository changed outside this study's attempt folders while it "
              "ran, and the session under test can run any Python. Nothing is committed. Read these:")
        for c in outside:
            print(f"  {c}")
        return 3
    attempt = [c[3:] for c in changed]
    if not attempt:
        print("the driver wrote no attempt folder; nothing to commit")
        return 1
    for d in sorted({(REPO / p).parent for p in attempt if p.endswith("driver-ledger.json")}):
        print(subprocess.run([py, str(HERE / "outcome.py"), str(d)], capture_output=True, text=True).stdout.strip())
    ledgers = [p for p in git("ls-files", "--others", "--exclude-standard", "--", *attempt).split()
               if p.endswith("driver-ledger.json")]
    kinds = [json.loads((REPO / p).read_text()).get("attempt", {}).get("kind") for p in ledgers]
    git("add", "--", *attempt, check=True)
    msg = commit_file(f"take: row {row} -- {task} / {half} / {model} / take {args.take}, {', '.join(map(str, kinds))}\n\n"
                      f"The attempt folder the driver routed, committed as it stands: transcript scrubbed of the "
                      f"account email only, driver ledger, environment record and scrub record. Its outcome is read "
                      f"by outcome.py and written into RESULT.md by result.py after the last take.\n")
    git("commit", "-q", "-F", str(msg), check=True)
    msg.unlink()
    print(f"committed {git('rev-parse', '--short', 'HEAD').strip()}: row {row}, {kinds}. Push through the door next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
