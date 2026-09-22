#!/usr/bin/env python3
"""Launch a blind pre-freeze reviewer, headless, from a review folder outside the Brain.

    python3 evals/gap-study-3/review_kit/launch.py <review folder> [<session id>]
    python3 evals/gap-study-3/review_kit/launch.py <review folder> <session id> --resume

The folder is built by build_kit.py: BRIEF.md, why.md, prereg.json, the previous review's bytes if any, and `study/`,
a full-history clone of this repository with NO remote. This launcher:

  - refuses a folder whose `study/` clone has a remote: the reviewer runs with no prompts and this machine's git
    credentials sit in the keychain, so a clone with a remote is a clone the reviewer could push from
    (TheReviewerCannotPush);
  - refuses a folder under the Brain or under this repository: the reviewer must not be able to see either;
  - runs `claude -p` with the driver's own isolation flags and environment (drive.ISOLATION_FLAGS, drive.child_env()),
    plus ENABLE_CLAUDEAI_MCP_SERVERS=false and CLAUDE_CODE_DISABLE_AUTO_MEMORY=1, so what the reviewer is given is what
    a take is given (TheReviewKitMatchesTheDriver). Never an Agent sub-agent: those boot with the operator's memory.
  - records the session id it opened, the folder's listing at launch, the stream, stderr and the exit code beside
    the folder, so blindness.py can read the reviewer's own session file afterwards.

A SESSION CUT OFF AFTER ITS FIRST AGENT TURN AND BEFORE ITS REPORT IS RESUMED, NOT RE-LAUNCHED. The
subscription's session limit ended round 3's reviewer at its 39th turn with no report written. Its id is
a pure function of its row's commit and was already opened, so a fresh launch under it is refused by the
harness, and a fresh id would be a second reviewer on the same bytes -- which is exactly what the register
exists to make visible. `--resume` continues THE SAME session under the same id with the harness's own
`--resume`, the reviewer's context intact, and records the continuation beside the first launch
(stream-resume-<n>.jsonl, stderr-resume-<n>.txt, launch-resume-<n>.log); SESSION is unchanged. The goal
file names a rate limit a pause, and a pause is resumed. Nothing about the round's blindness changes:
blindness.py reads the session's own file, which the continuation appends to.

No model is called by this file itself; it starts the reviewer's session. stdlib only.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_DIR = HERE.parent
REPO = STUDY_DIR.parent.parent

MODEL = "claude-fable-5-1"
PROMPT = "Read BRIEF.md in this folder and follow it exactly."
RESUME_PROMPT = ("Your session was interrupted by a rate limit and has been resumed. Continue exactly where you "
                 "were: follow BRIEF.md in this folder to completion, and write the report it asks for.")
REVIEWER_ENV = {"ENABLE_CLAUDEAI_MCP_SERVERS": "false", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}


def load_drive():
    """This study's driver, by path: its isolation constants and child_env are the ones the reviewer inherits."""
    spec = importlib.util.spec_from_file_location("gap_study_2_drive_for_launch", STUDY_DIR / "drive.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def folder_problems(folder: Path) -> list[str]:
    problems = []
    if not (folder / "BRIEF.md").is_file():
        problems.append("no BRIEF.md in the folder")
    study = folder / "study"
    if not (study / ".git").exists():
        problems.append("no study/ clone in the folder")
    else:
        r = subprocess.run(["git", "-C", str(study), "remote"], capture_output=True, text=True)
        if r.returncode != 0 or r.stdout.strip():
            problems.append(f"the study clone has a remote ({r.stdout.strip() or 'unreadable'}); the reviewer could push")
    resolved = folder.resolve()
    for root, name in ((REPO.resolve(), "this repository"), (Path.home() / "glitch", "the Brain")):
        try:
            resolved.relative_to(root.resolve())
            problems.append(f"the folder is under {name}")
        except ValueError:
            pass
    return problems


def argv_for(session_id: str, drive) -> list[str]:
    return ["claude", "-p", PROMPT, "--model", MODEL, "--permission-mode", "auto", "--permission-prompts", "none",
            *drive.ISOLATION_FLAGS, "--output-format", "stream-json", "--verbose", "--session-id", session_id]


def resume_argv_for(session_id: str, drive) -> list[str]:
    """The same flags, the same model, the same id -- continued with the harness's --resume, never re-opened."""
    return ["claude", "-p", RESUME_PROMPT, "--model", MODEL, "--permission-mode", "auto", "--permission-prompts",
            "none", *drive.ISOLATION_FLAGS, "--output-format", "stream-json", "--verbose", "--resume", session_id]


def env_for(drive) -> dict:
    return {**drive.child_env(), **REVIEWER_ENV}


def resume(folder: Path, sid: str, drive) -> int:
    side = folder.parent / (folder.name + "-launch")
    recorded = (side / "SESSION").read_text().strip() if (side / "SESSION").is_file() else None
    if recorded != sid:
        print(f"refusing to resume: {side.name}/SESSION records {recorded!r}, not {sid!r}. A resume continues the "
              f"session this folder was launched under and no other.")
        return 2
    n = 1 + len(list(side.glob("stream-resume-*.jsonl")))
    env = env_for(drive)
    argv = resume_argv_for(sid, drive)
    t0 = time.time()
    with open(side / f"stream-resume-{n}.jsonl", "w") as out, open(side / f"stderr-resume-{n}.txt", "w") as err:
        code = subprocess.run(argv, cwd=str(folder), env=env, stdout=out, stderr=err).returncode
    reports = sorted(folder.glob("prefreeze-*.md"))
    (side / f"launch-resume-{n}.log").write_text(json.dumps({
        "resumed": sid, "exit": code, "minutes": round((time.time() - t0) / 60, 1),
        "report_written": [r.name for r in reports]}) + "\n")
    print((side / f"launch-resume-{n}.log").read_text())
    return 0 if code == 0 else 1


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--resume"]
    resuming = "--resume" in sys.argv[1:]
    if not 1 <= len(args) <= 2 or (resuming and len(args) != 2):
        print(__doc__.split("\n")[2].strip())
        print(__doc__.split("\n")[3].strip())
        return 2
    sys.argv = [sys.argv[0], *args]
    folder = Path(sys.argv[1]).resolve()
    problems = folder_problems(folder)
    if problems:
        print("refusing to launch: " + "; ".join(problems))
        return 2
    drive = load_drive()
    if resuming:
        return resume(folder, sys.argv[2], drive)
    # ROUND 3. The session id may be GIVEN, and for this round it always is: rounds.py derives it as
    # uuid5 of the commit that introduced the round's row, exactly as a take's is of its ledger row's
    # commit. Round 2 drew a fresh uuid4 here, so a reviewer's session was tied to nothing -- a run could
    # open four reviewers and commit the two it liked, and the record would look the same either way.
    # The uuid4 default is kept so this file still behaves as round 2's did when no id is passed; what
    # makes the binding hold is rounds.py --check, which refuses a committed report that does not record
    # the id its row derives.
    sid = sys.argv[2] if len(sys.argv) == 3 else str(uuid.uuid4())
    side = folder.parent / (folder.name + "-launch")
    side.mkdir(exist_ok=True)
    (side / "SESSION").write_text(sid + "\n")
    (side / "FOLDER").write_text(str(folder) + "\n")
    (side / "folder-at-launch.txt").write_text("\n".join(sorted(os.listdir(folder))) + "\n")
    env = env_for(drive)
    argv = argv_for(sid, drive)
    t0 = time.time()
    with open(side / "stream.jsonl", "w") as out, open(side / "stderr.txt", "w") as err:
        code = subprocess.run(argv, cwd=str(folder), env=env, stdout=out, stderr=err).returncode
    reports = sorted(folder.glob("prefreeze-*.md"))
    (side / "launch.log").write_text(json.dumps({"exit": code, "minutes": round((time.time() - t0) / 60, 1),
                                                 "report_written": [r.name for r in reports]}) + "\n")
    print((side / "launch.log").read_text())
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
