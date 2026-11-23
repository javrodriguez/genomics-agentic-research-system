#!/usr/bin/env python3
"""Read CI's conclusion for one pushed commit, and say nothing is a pass only when it is one.

    python3 evals/gap-study-2/ci_conclusion.py <sha> [--repo owner/name] [--gh-json <file>]

WHY. Round 1's CI was red from slice 41 to slice 74 and nobody read it, and the freeze itself was pushed
red (structural lesson 4). A push is not done until its CI conclusion is read, so this runs after every
push and its exit code is the reading.

It first resolves <sha> with `git rev-parse --verify <sha>^{commit}` in this repository, because
`gh run list --commit` matches a full sha only: handed the short sha f7cf4d6, it listed nothing and this
printed "no CI run exists" beside a run that had succeeded. It then runs
`gh run list --commit <full sha> --json status,conclusion,name --limit 100` (from this repository, or
against --repo). With --gh-json it reads that same JSON from a file for tests, resolves nothing, and
<sha> is only a label.

EXIT CODES, decided in this order:
  4  <sha> does not resolve to a commit in this repository: refused by name, and gh is never run.
  1  any run completed with a conclusion other than `success` (failure, cancelled, timed_out, skipped,
     neutral, action_required, startup_failure, stale, or anything else). It wins over a run still in
     progress, because a run that already failed cannot make the commit green.
  3  any run not yet completed (queued, in_progress, waiting, requested, pending): read again later.
  2  no run exists for the commit. That is the absence of a measurement, never a pass.
  0  at least one run exists and every run is `completed` with conclusion `success`.
  4  gh could not be run or its output is not the expected JSON; usage errors.

Every run is printed as `status conclusion name`. stdlib only, no model.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

EXIT_SUCCESS, EXIT_FAILED, EXIT_NO_RUN, EXIT_PENDING, EXIT_UNREADABLE = 0, 1, 2, 3, 4
FULL_SHA = re.compile(r"[0-9a-f]{40}")


class Parser(argparse.ArgumentParser):
    def error(self, message):  # argparse's own exit 2 would read as "no run"
        self.print_usage(sys.stderr)
        print(f"ci_conclusion.py: {message}", file=sys.stderr)
        raise SystemExit(EXIT_UNREADABLE)


def resolve_commit(arg: str) -> str:
    """The full sha of <arg> in this repository, or ValueError. The ceiling stops git at this repository's
    own folder, so a copy that has no repository of its own never resolves against an enclosing one."""
    if not arg or arg.startswith("-"):
        raise ValueError("not a revision")
    env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(REPO.parent))
    r = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", "--quiet", f"{arg}^{{commit}}"],
                       capture_output=True, text=True, env=env)
    out = r.stdout.strip()
    if r.returncode != 0 or not FULL_SHA.fullmatch(out):
        raise ValueError(f"git rev-parse --verify exited {r.returncode}")
    return out


def read_runs(args, sha: str) -> list[dict]:
    if args.gh_json:
        raw = Path(args.gh_json).read_text()
    else:
        argv = ["gh", "run", "list", "--commit", sha, "--json", "status,conclusion,name", "--limit", "100"]
        if args.repo:
            argv += ["--repo", args.repo]
        r = subprocess.run(argv, capture_output=True, text=True, cwd=str(REPO))
        if r.returncode != 0:
            raise ValueError(f"gh exited {r.returncode}: {r.stderr.strip()[:300]}")
        raw = r.stdout
    runs = json.loads(raw)
    if not isinstance(runs, list) or not all(isinstance(x, dict) and "status" in x for x in runs):
        raise ValueError("expected a JSON list of runs, each with a status")
    return runs


def conclude(runs: list[dict]) -> tuple[int, str]:
    if not runs:
        return EXIT_NO_RUN, "no CI run exists for this commit; that is not a pass"
    failed = [r for r in runs if r.get("status") == "completed" and r.get("conclusion") != "success"]
    if failed:
        return EXIT_FAILED, f"{len(failed)} run(s) completed without success"
    pending = [r for r in runs if r.get("status") != "completed"]
    if pending:
        return EXIT_PENDING, f"{len(pending)} run(s) not yet completed; read again later"
    return EXIT_SUCCESS, f"{len(runs)} run(s), every one completed with success"


def main() -> int:
    ap = Parser(description="Read CI's conclusion for one commit.")
    ap.add_argument("sha")
    ap.add_argument("--repo", help="owner/name; default: this repository's own gh context")
    ap.add_argument("--gh-json", help="read gh's JSON from this file instead of running gh")
    args = ap.parse_args()
    sha = args.sha
    if not args.gh_json:
        try:
            sha = resolve_commit(args.sha)
        except (OSError, ValueError) as exc:
            print(f"refused: {args.sha!r} does not resolve to a commit in this repository ({exc}); "
                  f"gh was not run (exit {EXIT_UNREADABLE})")
            return EXIT_UNREADABLE
    try:
        runs = read_runs(args, sha)
    except (OSError, ValueError) as exc:  # json.JSONDecodeError is a ValueError
        print(f"cannot read CI runs for {sha}: {exc}")
        return EXIT_UNREADABLE
    for r in runs:
        print(f"  {r.get('status', '?'):12} {r.get('conclusion') or '-':16} {r.get('name', '?')}")
    code, sentence = conclude(runs)
    print(f"{sha[:12]}: {sentence} (exit {code})")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
