#!/usr/bin/env python3
"""Put one neutral line to an agent in a freshly built checkout, and read back what it was given.

    python3 evals/gap-study/smoke_run_tree.py --out evals/gap-study/verification/run-tree-smoke/1

WHY THIS EXISTS. Review 11 found three defects in the driver's checkout, and all three sat in the
part no test drove: the checkout was verified against nothing, the leak check against a hand-built
string, the inheritance check against a temporary directory. This drives the driver's OWN functions
-- the same clean_run_tree, one_turn and session_file a take calls -- through one real session, then
reads the transcript Claude Code wrote with the same checks a take is held to.

IT IS NOT A WALK AND NOT A TAKE. The line names no task, the checkout holds no fixture, no operator
script is sent, and nothing it records is graded or used to fix a script. It measures the
environment, which is the operator's side of every take. Its transcript is committed so a reader can
see exactly what the agent was given, rather than a summary of it.

Exit 0 only when the session ran, its transcript was found by id, and every check came back empty.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402

LINE = "Reply with the single word: ready."
TREE_SWEEP = re.compile(r"gap-study|gap study|prereg|pre-registration|EVALS\.md|evals/", re.I)


def by_path(name: str, file: str):
    """This study's module, loaded by path: the first study has files of the same names."""
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description="One neutral turn in a built checkout, read back.")
    ap.add_argument("--model", default="claude-haiku-4-5-20251001")
    ap.add_argument("--out", required=True, help="where the transcript and report are written")
    args = ap.parse_args()

    drive = by_path("gap_drive", "drive.py")
    ct = by_path("gap_check_take", "check_take.py")
    pre = prereg.load()

    sid = str(uuid.uuid4())
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    exclude = drive.excluded_from_run_tree(pre)
    tree = drive.clean_run_tree(head, sid, exclude)
    drive.RUN_TREE = tree

    def git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(tree), *a], capture_output=True,
                              text=True).stdout.strip()

    report: dict = {
        "what": "a smoke of the driver's checkout: one neutral line, no task, no fixture, not graded",
        "line": LINE, "model_requested": args.model, "session_id": sid,
        "built_from": head, "excluded": exclude,
        "claude_version": subprocess.run(["claude", "--version"], capture_output=True,
                                         text=True).stdout.strip(),
        "argv_flags": list(getattr(drive, "ISOLATION_FLAGS", ())),
        "isolation_env": dict(getattr(drive, "ISOLATION_ENV", {})),
        "checkout": {
            "name": tree.name, "commits": git("rev-list", "--all", "--count"),
            "subject": git("log", "-1", "--format=%s"), "remote": git("remote"),
            "status": git("status", "--porcelain"), "git_user": git("config", "user.name"),
            "problems_before_the_turn": drive.run_tree_problems(tree, sid, exclude),
        },
    }

    # what a reader of the checkout could still find that mentions an evaluation; reported, not
    # judged -- the pre-registration names the residual it expects
    hits = []
    for f in sorted(tree.rglob("*")):
        if ".git" in f.relative_to(tree).parts or not f.is_file():
            continue
        try:
            text = f.read_text(errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        for i, ln in enumerate(text.splitlines(), start=1):
            if TREE_SWEEP.search(ln):
                hits.append(f"{f.relative_to(tree)}:{i}")
    report["checkout"]["sweep_hits"] = hits

    budget = int(pre["budgets"]["turn_timeout_s"])
    said, code, err, harness_said = drive.one_turn(LINE, sid, args.model, True, budget)
    report["turn"] = {"exit": code, "reply": said[:200], "stderr_tail": err.strip()[-400:]}

    src = drive.session_file(sid)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    failures = []
    if code != 0:
        failures.append(f"the turn exited {code}")
    if src is None:
        failures.append("no session file was found for the session id")
        report["transcript"] = None
    else:
        dest = out / "transcript.jsonl"
        shutil.copy2(src, dest)
        # never an absolute path from outside the repository: it names the operator's machine
        report["transcript"] = str(dest.relative_to(REPO)) if dest.is_relative_to(REPO) else dest.name
        ctx = ct.context_text(dest)
        report["context_leaks"] = sorted(ct.context_leaks(ctx, pre))
        report["inherited_context"] = ct.inherited_context(dest)
        report["study_paths_read"] = ct.study_paths_read(dest)
        kinds: dict[str, int] = {}
        for ln in dest.read_text(errors="replace").splitlines():
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and rec.get("type") == "attachment":
                k = (rec.get("attachment") or {}).get("type", "?")
                kinds[k] = kinds.get(k, 0) + 1
        report["attachment_kinds"] = kinds
        for key in ("context_leaks", "inherited_context", "study_paths_read"):
            if report[key]:
                failures.append(f"{key}: {report[key]}")
    failures += [f"checkout: {p}" for p in report["checkout"]["problems_before_the_turn"]]

    shutil.rmtree(tree, ignore_errors=True)
    report["failures"] = failures
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps({k: report[k] for k in ("checkout", "turn", "failures")}, indent=2))
    for key in ("context_leaks", "inherited_context", "attachment_kinds"):
        print(f"{key}: {report.get(key)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
