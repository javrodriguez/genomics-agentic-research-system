#!/usr/bin/env python3
"""Launch a blind pre-freeze reviewer, headless, from a review folder outside the Brain.

    python3 evals/gap-study-4/review_kit/launch.py <review folder> [<session id>]
    python3 evals/gap-study-4/review_kit/launch.py <review folder> <session id> --resume

The folder is built by build_kit.py: BRIEF.md, why.md, prereg.json, the previous review's bytes if any, and `study/`,
a full-history clone of this repository with NO remote, plus COMMIT and `athena/`. ROUND 4 (lane review-kit-port,
ruling F5 of the freeze path): `athena/` holds the remote runner's outputs of the heavy gates at the commit in COMMIT,
written by athena_outputs.py and copied in by build_kit.py --athena, whose refusals (a commit line equal to the head,
no dotfile, no absolute home path, person or operator marker) a folder filled by hand would skip. BRIEF.md has the
reviewer read them and run only the light checks; `rounds.py --add` hashes the whole folder, so the row binds them.
This launcher:

  - refuses a folder whose `study/` clone has a remote: the reviewer runs with no prompts and this machine's git
    credentials sit in the keychain, so a clone with a remote is a clone the reviewer could push from
    (TheReviewerCannotPush);
  - refuses a folder under the Brain or under this repository: the reviewer must not be able to see either;
  - refuses a folder with no `athena/` or no COMMIT: build_kit.py writes both, so their absence is a folder this
    kit did not build;
  - runs `claude -p` with the driver's own isolation flags (drive.ISOLATION_FLAGS), `--effort medium`, and an
    environment built from ALLOWED_ENV plus ENABLE_CLAUDEAI_MCP_SERVERS=false and CLAUDE_CODE_DISABLE_AUTO_MEMORY=1.
    ROUND 4 (the review of the port, MAJOR 1): round 3's reviewer took the driver's take environment, which stripped
    the operator pane's session names; round 4's driver strips nothing (its takes get their environment inside the
    container), so a reviewer launched from an operator pane inherited that pane's effort, session id and messaging
    socket and token. The environment is now an allowlist, default deny, and never the driver's or the caller's.
    Never an Agent sub-agent: those boot with the operator's memory.
  - passes `--disallowedTools Workflow` (lane prefreeze-road, the Lane-orchestrator's ruling 2, Sat 24 Oct 2026):
    the client offers the Workflow tool and bundled workflows such as deep-research, which the Skill tool cannot
    start but the Workflow tool can; the disallow flag is the narrower of the two closings;
  - records the session id it opened, the folder's listing at launch, the NAMES of the environment it passed
    (env-names.txt, never a value), the stream, stderr and the exit code beside the folder, so blindness.py can read
    the reviewer's own session file afterwards.

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

# ROUND 4 (lane review-kit-port, glitch-f1's fold 1, Wed 21 Oct 2026): round 3 launched another model. The reviewer is now
# claude-opus-5-5: the study plan's CP6 asks for fresh Opus reviewers, and the agent-engine policy waits on
# the owner's word for any other.
MODEL = "claude-opus-5-5"
# ROUND 4 (the review of the port, MAJOR 1; agent-engine policy OD56: Opus 5.5 at medium for reviewers). Passed on
# launch and on resume, so the effort is stated by the kit and recorded in the session, never left to the client's
# version or to an inherited CLAUDE_EFFORT (which ALLOWED_ENV no longer lets through).
EFFORT = "medium"
PROMPT = "Read BRIEF.md in this folder and follow it exactly."
RESUME_PROMPT = ("Your session was interrupted by a rate limit and has been resumed. Continue exactly where you "
                 "were: follow BRIEF.md in this folder to completion, and write the report it asks for.")
# Lane prefreeze-road (the Lane-orchestrator's ruling 2): the tools the reviewer is never offered, on launch and resume
DISALLOW = ("--disallowedTools", "Workflow")
REVIEWER_ENV = {"ENABLE_CLAUDEAI_MCP_SERVERS": "false", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
# The only names the reviewer's environment takes from the caller's, each with the reason the headless client needs
# it. Everything else is dropped: every CLAUDE* / CLAUDE_CODE_* name of the operator's session, any API key, any
# CLAUDE_CONFIG_DIR that would point the client at another config. If the skills smoke (README.md) shows the client
# cannot run without a further name, that name is added here with its reason, as a reviewed change.
ALLOWED_ENV = {
    "PATH": "finds the claude client and git",
    "HOME": "the client finds its own login and config under it; settings beyond project and local are excluded by "
            "--setting-sources",
    "USER": "the account name the client's login lookup and git read",
    "LOGNAME": "the same account name, as some system calls read it",
    "SHELL": "the shell the client's own command tool starts",
    "LANG": "the text encoding of the reviewer's commands and their output",
    "LC_ALL": "the same, when the machine sets it",
    "LC_CTYPE": "the same, when the machine sets it",
    "TMPDIR": "the per-user temporary folder the operating system assigns",
}


def load_drive():
    """This study's driver, by path: only its isolation flags reach the reviewer (its take environment does not)."""
    spec = importlib.util.spec_from_file_location("gap_study_4_drive_for_launch", STUDY_DIR / "drive.py")
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
    if not (folder / "athena").is_dir() or not any((folder / "athena").iterdir()):
        problems.append("no athena/ outputs in the folder (build_kit.py --athena copies them in)")
    if not (folder / "COMMIT").is_file():
        problems.append("no COMMIT in the folder (build_kit.py writes it)")
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
            *drive.ISOLATION_FLAGS, *DISALLOW, "--effort", EFFORT, "--output-format", "stream-json",
            "--verbose", "--session-id", session_id]


def resume_argv_for(session_id: str, drive) -> list[str]:
    """The same flags, the same model, the same id -- continued with the harness's --resume, never re-opened."""
    return ["claude", "-p", RESUME_PROMPT, "--model", MODEL, "--permission-mode", "auto", "--permission-prompts",
            "none", *drive.ISOLATION_FLAGS, *DISALLOW, "--effort", EFFORT, "--output-format", "stream-json",
            "--verbose", "--resume", session_id]


def env_for(source=None) -> dict:
    """The reviewer's environment: the ALLOWED_ENV names present in `source` (the caller's environment by default),
    plus REVIEWER_ENV. Default deny: nothing else is passed."""
    source = os.environ if source is None else source
    env = {k: source[k] for k in ALLOWED_ENV if k in source}
    return {**env, **REVIEWER_ENV}


def record_env_names(side: Path, env: dict, name: str = "env-names.txt") -> None:
    """The names passed, one per line, sorted; never a value."""
    (side / name).write_text("".join(f"{k}\n" for k in sorted(env)))


def load_rounds():
    """The round register's module, by path: its manifest is what the round row hashed."""
    spec = importlib.util.spec_from_file_location("gap_study_4_rounds_for_launch", HERE / "rounds.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def manifest_problems(folder: Path, side: Path, rounds) -> list[str]:
    """The folder must still be what its round row hashed: rounds.py --add wrote the manifest beside it first
    (lane blindness-sidechains, the closure review of fff7e0d3, finding 4)."""
    m = side / rounds.MANIFEST
    if not m.is_file():
        return [f"no {rounds.MANIFEST} beside the folder (rounds.py --add writes it before it hashes the row)"]
    if rounds.manifest_text(folder) != m.read_text():
        return [f"the folder no longer matches {rounds.MANIFEST}, the manifest its round row hashed"]
    return []


def resume(folder: Path, sid: str, drive) -> int:
    side = folder.parent / (folder.name + "-launch")
    recorded = (side / "SESSION").read_text().strip() if (side / "SESSION").is_file() else None
    if recorded != sid:
        print(f"refusing to resume: {side.name}/SESSION records {recorded!r}, not {sid!r}. A resume continues the "
              f"session this folder was launched under and no other.")
        return 2
    n = 1 + len(list(side.glob("stream-resume-*.jsonl")))
    env = env_for()
    record_env_names(side, env, f"env-names-resume-{n}.txt")
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
    stale = manifest_problems(folder, side, load_rounds())
    if stale:
        print("refusing to launch: " + "; ".join(stale))
        return 2
    side.mkdir(exist_ok=True)
    (side / "SESSION").write_text(sid + "\n")
    (side / "FOLDER").write_text(str(folder) + "\n")
    (side / "folder-at-launch.txt").write_text("\n".join(sorted(os.listdir(folder))) + "\n")
    env = env_for()
    record_env_names(side, env)
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
