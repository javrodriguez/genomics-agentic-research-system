#!/usr/bin/env python3
"""Rehearse the freeze and its gate in a disposable, full-depth local clone.

The default review is the latest committed pre-freeze review; --review-commit
can name it explicitly. It must already satisfy freeze.py's review rule and
be claimed by its writing lane. No synthetic review is added to the build.
The frozen-state COMMANDS include every Level 3 gate, even files not yet built.
Only after those checks does rehearsal register the first full planned row and
exercise the publication readers. The copy gate never runs on runtime outputs
(w5b-4). No take is driven, and no graded observation is manufactured.

All outputs, including the rehearsal report, stay under a temporary directory,
outside the source tree. --keep retains the clone too. Pass the report to the
real freeze with --rehearsal-record; the frozen file retains its content and
hash. Its tree line names the committed source tree that was cloned. This program runs on the
remote runner, never as a Mac gate. No vendor executable, model or container.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import freeze  # noqa: E402
import scratch_git  # noqa: E402
import study  # noqa: E402

DRAFT = HERE / "prereg-draft.json"

# Frozen-state gates only. Missing files are interpreter failures, never dropped.
COMMANDS = (
    ("test_round4.py",), ("copy_manifest.py", "--check"),
    ("tests/test_box_integration.py",), ("tests/test_pipeline.py",),
    ("probes4.py", "--check"), ("build_draft.py", "--check"),
    ("leak_grep.py", "--check"), ("holdout.py", "--check"),
    ("review_kit/rounds.py", "--check"),
)


def rehearsal_plan(pre, row_file):
    """A full frozen row and the runtime commands; never another copy gate."""
    first = copy.deepcopy(pre["take_order"][0])
    import takes
    takes.require_planned_row(first, pre)
    return first, (
        ("takes.py", "--add", "--row", str(row_file), "--attempt", "1"),
        ("takes.py", "--session-id", "0"),
        ("run.py", "--all"), ("result.py", "--write"),
        ("check_results.py", "--ledger"), ("completeness.py", "--check"),
    )


def sh(argv, cwd, env=None, timeout=3600):
    try:
        got = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                             env=env, timeout=timeout)
        return got.returncode, got.stdout + got.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def git(clone, *args):
    return sh(["git", "-C", str(clone), "-c", "user.name=rehearsal",
               "-c", "user.email=rehearsal@example.invalid", "-c",
               f"{scratch_git.MAINTENANCE_KEY}={scratch_git.MAINTENANCE_VALUE}", *args], clone)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--review-commit")
    args = ap.parse_args(argv)
    if freeze.outputs_exist(HERE):
        print("refusing: a freeze output already exists here")
        return 2
    code, dirty = git(REPO, "status", "--porcelain")
    if code or dirty.strip():
        print("refusing: commit the complete source repository before rehearsal")
        return 2
    review = args.review_commit
    if not review:
        code, review = git(REPO, "log", "-1", "--format=%H", "--",
                           study.rel(study.REVIEW_DIR, "prefreeze-*.md"))
        review = review.strip()
    problems, _ = freeze.review_file_problems(review or "")
    if problems:
        print("refusing: " + "; ".join(problems))
        return 2
    digest = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
    tree = freeze.study_tree_sha()
    scratch = Path(tempfile.mkdtemp(prefix="rehearsal-"))
    clone = scratch / "repo"
    report = scratch / "freeze-rehearsal-1.txt"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    steps = []

    def step(name, command):
        code, output = sh(command, clone, env=env)
        tail = " | ".join(output.strip().splitlines()[-3:])
        steps.append((name, code, tail))
        print(f"[{code}] {name}: {tail}", flush=True)
        return code

    def python_command(command):
        return [sys.executable, "-B", "-W", "ignore", study.rel(command[0]), *command[1:]]

    try:
        code, output = sh(["git", "clone", "-q", "--no-local", str(REPO), str(clone)], REPO, env)
        if code:
            raise ValueError("local clone failed: " + output)
        code, output = git(clone, "remote", "remove", "origin")
        if code:
            raise ValueError("cannot remove clone remote: " + output)
        fz = step("freeze", python_command(("freeze.py", "--review-commit", review,
                                               "--rehearsal", "--write")))
        if fz == 0:
            code, output = git(clone, "add", "--", *(study.rel(p) for p in
                                   ("prereg.json", "COPIED.json", "COPIED.d/freeze.json")))
            if code:
                raise ValueError("freeze staging failed: " + output)
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as message:
                message.write("Rehearse the frozen state\n\nCo-Authored-By: Codex (gpt-6-astra) <noreply@openai.com>\n")
                message.flush()
                code, output = git(clone, "commit", "-F", message.name)
            if code:
                raise ValueError("freeze commit failed: " + output)
        for command in COMMANDS:
            step(" ".join(command), python_command(command))
        if fz == 0 and all(code == 0 for _, code, _ in steps):
            pre = json.loads((clone / study.rel("prereg.json")).read_text())
            row_file = scratch / "row.json"
            first, commands = rehearsal_plan(pre, row_file)
            row_file.write_text(json.dumps(first))
            for command in commands:
                if step(" ".join(command), python_command(command)):
                    break
    except (ValueError, KeyError, OSError) as exc:
        steps.append(("rehearsal", 1, str(exc)))
    finally:
        if not args.keep and clone.exists():
            shutil.rmtree(clone)
    green = bool(steps) and all(code == 0 for _, code, _ in steps)
    lines = [digest, "Disposable rehearsal; no takes driven.", freeze.REHEARSAL_TREE_PREFIX + tree]
    for name, code, tail in steps:
        lines.extend((f"[{code}] {name}", "    " + tail))
    lines.append("all green" if green else "NOT all green")
    text = "\n".join(lines).replace(str(REPO), "<repo>").replace(str(scratch), "<scratch>") + "\n"
    report.write_text(text)
    print(f"report: {report}")
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
