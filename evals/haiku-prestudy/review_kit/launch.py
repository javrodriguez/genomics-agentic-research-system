#!/usr/bin/env python3
"""Launch a blind pre-freeze reviewer, headless, from a review folder outside the Brain.

    python3 evals/gap-study-2/review_kit/launch.py <review folder>

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


def env_for(drive) -> dict:
    return {**drive.child_env(), **REVIEWER_ENV}


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.split("\n")[2].strip())
        return 2
    folder = Path(sys.argv[1]).resolve()
    problems = folder_problems(folder)
    if problems:
        print("refusing to launch: " + "; ".join(problems))
        return 2
    drive = load_drive()
    sid = str(uuid.uuid4())
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
