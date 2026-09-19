#!/usr/bin/env python3
"""Freeze the draft into prereg.json, once, and only behind everything a freeze needs.

    python3 evals/haiku-prestudy/freeze.py --review-commit <sha> --write     the freeze
    python3 evals/haiku-prestudy/freeze.py --rehearsal --write               the same, in a throwaway clone only

The freeze refuses unless every one of these holds, and prints each that does not:
  1. the owner's approval of the allowlist is on the draft (driver_change.approved_by_owner and approved_at);
  2. a rehearsal record verification/freeze-rehearsal-<n>.txt exists whose first line is the sha256 of these draft
     bytes and whose last line is `all green`;
  3. the study folder has no uncommitted change, so what is frozen is what is committed;
  4. the review commit lands exactly one verification/prefreeze-<n>.md and its blindness record, the report's line 1
     is these draft bytes' sha256 line, and its ruling line reads DO FREEZE;
  5. `claude --version` reads the harness version the draft carries.
A rehearsal skips 3 and 4, needs a folder with no git remote, and writes the frozen file only inside that clone.

What it writes: prereg.json = the draft, with `status` FROZEN, the freeze time, the review commit, the rehearsal
record's name, the draft's sha256, and `pinned_files`: the sha256 of every code file a take or the result depends on.
It never edits the draft, and it refuses when prereg.json already exists.

No model, no network. stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DRAFT = HERE / "prereg-draft.json"
FROZEN = HERE / "prereg.json"
VERIFICATION = HERE / "verification"
PINNED = ("drive.py", "prereg.py", "takes.py", "scrub.py", "check_take.py", "study.py", "outcome.py",
          "result.py", "lint_language.py", "build_draft.py", "copy_manifest.py", "finding.py", "check_results.py",
          "test_prestudy.py", "freeze.py", "freeze_rehearsal.py", "take.py")
RULING = re.compile(r"^\*\*Ruling: DO (NOT )?FREEZE\.\*\*$", re.M)
STUDY_REL = "evals/haiku-prestudy"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def rehearsal_record(draft_sha: str) -> Path | None:
    for rec in sorted(VERIFICATION.glob("freeze-rehearsal-*.txt")):
        lines = rec.read_text().splitlines()
        if lines and lines[0].strip() == draft_sha and lines[-1].strip() == "all green":
            return rec
    return None


def review_problems(commit: str, draft_sha: str) -> list[str]:
    files = git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).stdout.split()
    reports = [f for f in files if re.fullmatch(rf"{STUDY_REL}/verification/prefreeze-\d+\.md", f)]
    blinds = [f for f in files if re.fullmatch(rf"{STUDY_REL}/verification/prefreeze-\d+-blindness\.txt", f)]
    if len(files) != 2 or len(reports) != 1 or len(blinds) != 1:
        return [f"review commit {commit[:12]} lands {files}, not exactly one review and its blindness record"]
    text = git("show", f"{commit}:{reports[0]}").stdout
    out = []
    if (text.splitlines() or [""])[0] != f"prereg.json sha256: {draft_sha}":
        out.append("the review read other bytes than the draft on disk")
    m = RULING.search(text)
    if not m or m.group(1):
        out.append("the review's ruling is not DO FREEZE")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--review-commit", metavar="SHA")
    g.add_argument("--rehearsal", action="store_true")
    args = ap.parse_args()

    if FROZEN.exists():
        print("refusing: prereg.json exists; a study is frozen once")
        return 2
    raw = DRAFT.read_bytes()
    draft = json.loads(raw)
    draft_sha = sha256(raw)
    problems = []
    dc = draft.get("driver_change") or {}
    if not dc.get("approved_by_owner") or not dc.get("approved_at"):
        problems.append("the owner's approval of the allowlist is not on the draft")
    rec = rehearsal_record(draft_sha)
    if rec is None:
        problems.append(f"no green rehearsal record for these draft bytes ({draft_sha[:12]})")
    version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    if not version.startswith(draft["harness"]["claude_version"]):
        problems.append(f"claude --version reads {version!r}, not {draft['harness']['claude_version']}")
    if args.rehearsal:
        if git("remote").stdout.strip():
            problems.append("--rehearsal is refused where a git remote exists")
        review = None
    else:
        full = git("rev-parse", "--verify", f"{args.review_commit}^{{commit}}").stdout.strip()
        if not full:
            problems.append(f"{args.review_commit} names no commit")
        else:
            problems += review_problems(full, draft_sha)
        if git("status", "--porcelain", "--", STUDY_REL).stdout.strip():
            problems.append("the study folder has uncommitted changes")
        review = full
    if problems:
        print("refusing to freeze:\n  - " + "\n  - ".join(problems))
        return 2

    frozen = dict(draft)
    frozen["status"] = ("FROZEN. Read-only to the run. A later change is published as `amended`, with before and "
                        "after, never corrected in place.")
    frozen["frozen_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    frozen["pre_freeze_review_commit"] = review
    frozen["rehearsal_record"] = rec.name
    frozen["draft_sha256_at_freeze"] = draft_sha
    frozen["harness_at_freeze"] = version
    frozen["pinned_files"] = {f: sha256((HERE / f).read_bytes()) for f in PINNED if (HERE / f).is_file()}
    missing = [f for f in PINNED if not (HERE / f).is_file()]
    if missing:
        print(f"refusing: pinned file(s) missing: {missing}")
        return 2
    FROZEN.write_text(json.dumps(frozen, indent=2, ensure_ascii=False) + "\n")
    print(f"froze {FROZEN.name}: draft {draft_sha[:12]}, rehearsal {rec.name}, "
          f"review {review[:12] if review else '(rehearsal)'}, {len(frozen['pinned_files'])} files pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
