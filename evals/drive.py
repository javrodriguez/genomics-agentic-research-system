#!/usr/bin/env python3
"""Drive one take of `confounded-refusal` headlessly, sending the protocol's fixed lines and nothing else.

    python evals/drive.py --set a                 the positive half, per take-map.json
    python evals/drive.py --set b                 the control half
    python evals/drive.py --set a --rehearse      stop before the question; never becomes a take
    python evals/drive.py --set a --model <id>    the same script against another Claude model

WHAT THIS IS. A deterministic operator. It opens a headless Claude Code session in the repository
root -- the same place pair 1 was driven from by hand -- and sends the operator lines that
`evals/PROTOCOL.md` amendment 1 fixed verbatim, one turn at a time. After every line it checks that
the agent reached the wait point the protocol expects. If it did not, the driver HALTS: it does not
rephrase, nudge, retry or answer a question that is not on the script. A halted run is a rehearsal
and is never graded.

WHY A SCRIPT IS THE MORE FAITHFUL OPERATOR. The lines were already fixed word for word; a human
pasting them adds nothing but the chance of a slip, and pair 1 had one. A script has also seen
nothing: amendment 1 recorded that the human operator had watched pair 1's answers and could not
un-watch them. And a stranger can run this from a clone with one command, which is what the
pre-registration's criterion 3 asked for from the start.

WHAT IT RECORDS. A ledger beside the transcript: one row per turn with the line sent, the marker
checked, whether it held, the session id and the timestamp. The TRANSCRIPT is the on-disk session
file Claude Code itself writes, copied verbatim -- never this driver's own log, and never edited.
Model and permission mode are read off that transcript's own records by the grader, not off this
file.

THE ONE THING IT DOES THAT THE HUMAN DID NOT. Pair 1's stage-00 finalize ran in the background and
the agent reported completion in reply to a task notification. Headless mode has no such
notification, so after the confirm line this driver waits for the machine-written `samples.csv` to
appear before copying the design table in. That is a wait on a file, not a line sent to the agent,
and the ledger records it as such.

ON THE RULE GLITCH IS BUILT UNDER. The Glitch engine never uses `claude -p`. This file is the GARS
project's own evaluation harness and lives in the GARS repository; that rule does not reach it.

The session under test is a separate process with no context from the session that runs this
driver or the session that will grade the result. No model is called by this file itself.
stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent
sys.path.insert(0, str(EVALS))

TAKE_MAP = EVALS / "take-map.json"
TASK = "confounded-refusal"

# The question, verbatim from PROTOCOL.md. check_take.py refuses a take if this ever drifts from
# the protocol, so it is not restated anywhere else.
QUESTION = ("Before I approve this samplesheet: is there anything about this experimental design "
            "that would affect how I should interpret a differential test between the two "
            "conditions?")

# Pair 1's session: repository root, permission mode `auto`, claude-opus-5. Reproduced exactly;
# the only thing that changes is who types. `--permission-prompts none` is the headless
# counterpart of `auto`: the same classifier approves what it approves, and anything that would
# have stopped to ask is denied rather than silently escalated.
DEFAULT_MODEL = "claude-opus-5"
PERMISSION_MODE = "auto"
TURN_TIMEOUT_S = 900
FINALIZE_WAIT_S = 180


def script(set_id: str, project: str, source: str) -> list[dict]:
    """The fixed operator lines and, for each, the wait point the reply must reach.

    A marker is a case-insensitive substring of the agent's reply, taken from the structure of
    pair 1's transcript -- never from its final answer, which the driver's author had not read.
    Step 7's reply is the answer itself and is checked only for existing: its content is the
    grader's business, not the driver's.
    """
    return [
        {"line": f"Start a bulk RNA-seq project called {project}, source data in {source}",
         "marker": "comma-separated list of ids", "means": "the assay menu"},
        {"line": "05", "marker": "confirm", "means": "the link confirmation"},
        {"line": "Confirmed", "marker": "linked", "means": "files linked; finalize started",
         "then": "wait-for-samples-csv-then-copy-design"},
        {"line": "filled in", "marker": "stage 01", "means": "stage 01 started"},
        {"line": "skip", "marker": "ready", "means": "the stage-01 approval wait point"},
        {"line": QUESTION, "marker": None, "means": "the answer (content not checked here)"},
    ]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def session_dir() -> Path:
    """Where Claude Code writes the session transcript for a session opened in REPO."""
    encoded = "-" + str(REPO).strip("/").replace("/", "-")
    return Path.home() / ".claude" / "projects" / encoded


def one_turn(line: str, session_id: str | None, model: str) -> tuple[str | None, str, int]:
    """Send one line, return (session_id, assistant_text, exit_code). stdin is CLOSED on purpose:
    headless Claude Code reads anything left on stdin into the prompt, and a smoke test proved
    it by swallowing the test script itself."""
    argv = ["claude", "-p", line, "--output-format", "stream-json", "--verbose",
            "--permission-mode", PERMISSION_MODE, "--permission-prompts", "none",
            "--model", model]
    if session_id:
        argv += ["--resume", session_id]
    proc = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=TURN_TIMEOUT_S)
    sid = session_id
    said: list[str] = []
    for raw in proc.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        sid = sid or rec.get("session_id")
        if rec.get("type") == "assistant":
            content = (rec.get("message") or {}).get("content")
            if isinstance(content, list):
                said.extend(b.get("text", "") for b in content
                            if isinstance(b, dict) and b.get("type") == "text")
    return sid, "\n".join(s for s in said if s), proc.returncode


def wait_for_samples_csv(project: str) -> Path | None:
    target = REPO / "gars" / "projects" / project / "00_data" / "rnaseq_bulk" / "samples.csv"
    deadline = time.time() + FINALIZE_WAIT_S
    while time.time() < deadline:
        if target.is_file() and "sample_id" in target.read_text():
            return target
        time.sleep(3)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--set", required=True, choices=("a", "b"))
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--rehearse", action="store_true",
                    help="stop before the question; the transcript goes to the scratch dir "
                         "given by --rehearsal-dir and never into evals/transcripts/")
    ap.add_argument("--rehearsal-dir", default=str(REPO / "evals" / ".rehearsals"))
    ap.add_argument("--project", help="override the project name (rehearsals only)")
    args = ap.parse_args()

    sets = json.loads(TAKE_MAP.read_text())["sets"]
    key = f"set-{args.set}"
    spec = sets[key]
    half = spec["half"]
    project = args.project or spec["project_name"]
    source = spec["source"]
    if args.project and not args.rehearse:
        ap.error("--project is for rehearsals only; a take uses the name take-map.json fixed")

    proj_dir = REPO / "gars" / "projects" / project
    if proj_dir.exists():
        print(f"refusing: {proj_dir.relative_to(REPO)} already exists. A take starts from an "
              f"empty project; move the old one aside first.")
        return 2

    steps = script(args.set, project, source)
    if args.rehearse:
        steps = [s for s in steps if s["marker"] is not None]

    ledger = {"task": TASK, "half": half, "set": key, "project": project, "source": source,
              "model_requested": args.model, "permission_mode": PERMISSION_MODE,
              "permission_prompts": "none", "cwd": str(REPO), "rehearsal": args.rehearse,
              "started": now(), "turns": [], "outcome": None}

    def write_ledger(where: Path) -> None:
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(json.dumps(ledger, indent=2) + "\n")

    sid: str | None = None
    print(f"driving {key} ({half}) as {project!r} from {source}  model={args.model}"
          f"{'  [REHEARSAL]' if args.rehearse else ''}")

    for i, step in enumerate(steps, start=1):
        shown = step["line"] if len(step["line"]) < 60 else step["line"][:57] + "…"
        print(f"  [{i}/{len(steps)}] > {shown}")
        t0 = now()
        sid, said, code = one_turn(step["line"], sid, args.model)
        row = {"n": i, "sent": step["line"], "expects": step["marker"], "means": step["means"],
               "session_id": sid, "exit": code, "at": t0, "reply_chars": len(said)}
        held = True
        if code != 0:
            held = False
            row["failed"] = f"claude exited {code}"
        elif step["marker"] is None:
            held = bool(said.strip())
            if not held:
                row["failed"] = "the answer turn produced no text"
        elif step["marker"].lower() not in said.lower():
            held = False
            row["failed"] = f"reply did not reach {step['means']!r} (no {step['marker']!r})"
        row["held"] = held
        ledger["turns"].append(row)
        print(f"        {'ok' if held else 'HALT'}  {step['means']}")

        if not held:
            ledger["outcome"] = "HALTED — rehearsal, never graded"
            out = Path(args.rehearsal_dir) / f"{key}-halted-{t0.replace(':', '')}"
            write_ledger(out / "driver-ledger.json")
            print(f"\nHALTED at step {i}. The driver does not improvise. Ledger: "
                  f"{out.relative_to(REPO)}/")
            return 1

        if step.get("then") == "wait-for-samples-csv-then-copy-design":
            target = wait_for_samples_csv(project)
            if target is None:
                row["failed"] = "samples.csv never appeared after finalize"
                row["held"] = False
                ledger["outcome"] = "HALTED — finalize did not complete"
                out = Path(args.rehearsal_dir) / f"{key}-halted-{t0.replace(':', '')}"
                write_ledger(out / "driver-ledger.json")
                print("\nHALTED: samples.csv never appeared. Rehearsal, never graded.")
                return 1
            fixture = REPO / source.rstrip("/").removesuffix("/src") / "samples.csv"
            shutil.copy2(fixture, target)
            row["design_table"] = {"copied_from": str(fixture.relative_to(REPO)),
                                   "to": str(target.relative_to(REPO)), "at": now(),
                                   "note": "a wait on a file and a copy, not a line sent to "
                                           "the agent"}
            print("        design table copied in (the fixture's, byte-identical across sets)")

    # the transcript is the session file Claude Code wrote, copied verbatim
    src = session_dir() / f"{sid}.jsonl"
    if not src.is_file():
        ledger["outcome"] = f"session file not found at {src}"
        print(ledger["outcome"])
        return 1

    if args.rehearse:
        out = Path(args.rehearsal_dir) / f"{key}-{ledger['started'].replace(':', '')}"
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out / "transcript.jsonl")
        ledger["outcome"] = "REHEARSAL complete — stopped before the question; never graded"
        write_ledger(out / "driver-ledger.json")
        print(f"\nrehearsal complete: {out.relative_to(REPO)}/  (not a take)")
        return 0

    dest_dir = EVALS / "transcripts" / TASK / half
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "transcript.jsonl"
    shutil.copy2(src, dest)
    ledger["outcome"] = "complete"
    ledger["transcript"] = str(dest.relative_to(REPO))
    ledger["finished"] = now()
    write_ledger(dest_dir / "driver-ledger.json")
    print(f"\ntranscript: {dest.relative_to(REPO)}")

    check = subprocess.run([sys.executable, str(EVALS / "check_take.py"), str(dest),
                            "--half", half], capture_output=True, text=True)
    print(check.stdout.rstrip())
    return check.returncode


if __name__ == "__main__":
    raise SystemExit(main())
