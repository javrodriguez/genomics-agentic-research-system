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
# W8A (ruling W8-layout-1; this file moved from lane w5b to lane w8a under ruling W8A-gap4-1): the four walk checks,
# so the rehearsal proves the walks the freeze rests on are registered, held to their pins, clean of the checkout and
# graded as committed (README Q5).
WALK_COMMANDS = (
    ("walk_register.py", "--check"), ("mode_binding.py", "--walks", "--check"),
    ("fixture_walk.py", "--check"), ("run.py", "--walks", "--check"),
)
COMMANDS = (
    ("test_round4.py",), ("copy_manifest.py", "--check"),
    ("tests/test_box_integration.py",), ("tests/test_pipeline.py",),
    ("probes4.py", "--check"), ("build_draft.py", "--check"),
    ("leak_grep.py", "--check"), ("holdout.py", "--check"),
    ("review_kit/rounds.py", "--check"),
) + WALK_COMMANDS


# W8B fold (lane w8b-holdout-digests; glitch-1b's rulings Q7 and Q8 at the w8b hand-back, Mon 12 Oct 2026 09:08 EDT,
# under ruling W8B-gap4-1). Q7: the rehearsal's freeze exercises the digest path. A synthetic digest file (the sha256 of
# obviously fake strings, one list per task of the cloned draft, never a holdout) is written in the rehearsal's temporary
# folder, beside the clone so the clone stays committed, and handed to freeze.py --holdout-digests; the step "holdout
# digests" then checks that the frozen file carries both fields exactly. Only --no-holdout-digests leaves it out, and that
# rehearsal records NOT REHEARSED as a failing step, so it is never all green. Q8: holdout.py --check lives in private
# aegis (ruling C4) and is wired with S9's landing; until then its step names itself as owed and fails, never passes.
HOLDOUT_FILE = "synthetic-holdout-digests.json"
OWED = {"holdout.py": "OWED: holdout.py --check lives in private aegis (ruling C4) and is wired with S9's landing; "
                      "not run here, so this rehearsal is not all green"}
NO_FILE_LINE = ("NOT REHEARSED: the holdout digests (--no-holdout-digests: the freeze ran without a digest file, so "
                "this rehearsal is not all green)")


def synthetic_holdout_source(draft_file, out_file) -> dict:
    """freeze.synthetic_holdout_source (W8B-R1-1: the generator lives in freeze.py, so a real freeze refuses its
    digests); the file is deleted in main's finally unless --keep."""
    return freeze.synthetic_holdout_source(draft_file, out_file)


def holdout_written_problems(frozen: dict, source: dict) -> list[str]:
    """What the rehearsal's frozen file got wrong about the two freeze-written holdout fields; empty when both match."""
    problems = []
    if frozen.get("holdout_salted_digests") != source["salted_sha256"]:
        problems.append("holdout_salted_digests is not the digest file's")
    counts = {len(digests) for digests in source["salted_sha256"].values()}
    if [frozen.get("holdout_wordings_per_task_version")] != sorted(counts):
        problems.append("holdout_wordings_per_task_version is not the digest file's count")
    return problems


def freeze_command(review, holdout_file):
    return ("freeze.py", "--review-commit", review, "--rehearsal", "--write") + (
        () if holdout_file is None else ("--holdout-digests", str(holdout_file)))


def owed_step(command):
    """(1, why) for a gate that is owed elsewhere, or None for a gate this clone runs. `command` is the interpreter
    argv a step is handed; the script is the first argument that names a .py file."""
    script = next((Path(part).name for part in command if str(part).endswith(".py")), None)
    return (1, OWED[script]) if script in OWED else None


def rehearsal_plan(pre, row_file):
    """A full frozen row and the runtime commands; never another copy gate."""
    first = copy.deepcopy(pre["take_order"][0])
    import takes
    takes.require_planned_row(first, pre)
    return first, (
        ("takes.py", "--add", "--row", str(row_file), "--attempt", "1"),
        ("takes.py", "--session-id", "0"),
        ("run.py", "--all"), ("result.py", "--write"),
        ("check_results.py", "--ledger", "--rehearsal-plan"), ("completeness.py", "--check"),
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


def step_environment():
    """A fixed fake identity for subprocesses committing disposable records."""
    return dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1",
                OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                GIT_AUTHOR_NAME="rehearsal", GIT_AUTHOR_EMAIL="rehearsal@example.invalid",
                GIT_COMMITTER_NAME="rehearsal", GIT_COMMITTER_EMAIL="rehearsal@example.invalid")


def run_step(command, clone):
    return sh(command, clone, env=step_environment())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--review-commit")
    ap.add_argument("--no-holdout-digests", action="store_true")
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
    env = step_environment()
    steps = []
    holdout_file = None

    def step(name, command):
        owed = owed_step(command)
        code, output = owed if owed else run_step(command, clone)
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
        holdout_file = None if args.no_holdout_digests else scratch / HOLDOUT_FILE
        source = (None if holdout_file is None else
                  synthetic_holdout_source(clone / study.rel("prereg-draft.json"), holdout_file))
        fz = step("freeze", python_command(freeze_command(review, holdout_file)))
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
            if source is None:
                steps.append(("holdout digests", 1, NO_FILE_LINE))
            else:
                wrong = holdout_written_problems(json.loads((clone / study.rel("prereg.json")).read_text()), source)
                steps.append(("holdout digests", 1 if wrong else 0,
                              "; ".join(wrong) or "both fields written from the synthetic digest file"))
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
        # W8B-R1-1: the synthetic digest file never outlives the rehearsal unless --keep keeps its clone too
        if holdout_file is not None and not args.keep:
            holdout_file.unlink(missing_ok=True)
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
