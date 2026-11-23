#!/usr/bin/env python3
"""The one commit after a pre-freeze review's report lands: its two records claimed, and nothing else.

    python3.12 evals/gap-study-4/review_kit/claim_review.py <N>

Lane fold11/freeze-recheck (the gate review of the fold, m6). Run it once, right after review_kit/commit_review.py <folder> <N>.
copy_manifest --check fails on an unclaimed file, and a claim cannot land before the file does, so this commit is on every
round's road. It appends the two entries to COPIED.d/review-records.json, the one pinned file freeze._record_only_change
admits for a claim, so the seed's launch binding still reads clean. A report from round 9 on needs no line in any other
file: lint_language.is_bound_review_report exempts it by rule. Editing any other pinned file now would need a new round.

It refuses, writing nothing, unless the working tree is clean, no frozen file exists, HEAD lands exactly the report and its
blindness record, the report's sha256 is the digest the record states, and neither file is claimed yet. Never pushes.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_DIR = HERE.parent
REPO = STUDY_DIR.parent.parent
sys.path.insert(0, str(STUDY_DIR))
import freeze  # noqa: E402
import study  # noqa: E402


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def problem(n: str) -> str | None:
    """Why round n's two records may not be claimed here, or None."""
    report, blind = HERE / f"prefreeze-{n}.md", HERE / f"prefreeze-{n}-blindness.txt"
    if (STUDY_DIR / "prereg.json").is_file():
        return "a frozen file exists: the review road is over"
    if git("status", "--porcelain").stdout.strip():
        return "the working tree is not clean"
    want = sorted(study.rel(study.REVIEW_DIR, p.name) for p in (report, blind))
    landed = sorted(x for x in git("show", "--name-only", "--format=", "HEAD").stdout.split("\n") if x)
    if landed != want:
        return f"HEAD does not land exactly {want}: run this right after commit_review.py"
    digest = freeze._blindness().recorded_report_digest(blind.read_text())
    if digest is None or digest != hashlib.sha256(report.read_bytes()).hexdigest():
        return f"{report.name}'s sha256 is not the digest its blindness record states"
    doc = json.loads((STUDY_DIR / freeze.REVIEW_CLAIMS_FRAGMENT).read_text())
    if {e["path"] for e in doc["files"]} & {f"{study.REVIEW_DIR}/{p.name}" for p in (report, blind)}:
        return "already claimed"
    return None


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print(__doc__.split("\n")[2].strip())
        return 2
    n = sys.argv[1]
    why = problem(n)
    if why:
        print(f"refusing: {why}")
        return 1
    path = STUDY_DIR / freeze.REVIEW_CLAIMS_FRAGMENT
    doc = json.loads(path.read_text())
    sha = git("rev-parse", "HEAD").stdout.strip()
    doc["files"] += [{"path": f"{study.REVIEW_DIR}/prefreeze-{n}{tail}", "status": "new",
                      "reason": f"Pre-freeze review {n}'s {what}, committed by {sha[:12]} through "
                                f"{study.REVIEW_DIR}/commit_review.py. A bound record, never edited."}
                     for tail, what in ((".md", "report"), ("-blindness.txt", "blindness record"))]
    path.write_text(json.dumps(doc, indent=2) + "\n")
    with tempfile.NamedTemporaryFile("w", suffix=".txt") as msg:
        msg.write(f"review: pre-freeze review {n}'s report and blindness record claimed\n\nWhat: {freeze.REVIEW_CLAIMS_FRAGMENT} "
                  "gains the two claims, appended. copy_manifest --check fails on an unclaimed file, and a claim cannot "
                  "land before the file does.\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n")
        msg.flush()
        lint = subprocess.run([sys.executable, str(STUDY_DIR / "commit_msg.py"), msg.name], capture_output=True, text=True)
        if lint.returncode != 0:
            git("checkout", "--", str(path.relative_to(REPO)))
            print(f"refusing: the commit message: {lint.stdout[-300:]}")
            return 1
        added = git("add", "--", str(path.relative_to(REPO)))
        out = git("commit", "-q", "-F", msg.name) if added.returncode == 0 else added
    if out.returncode != 0:
        print(f"commit failed: {out.stderr[-300:]}")
        return 1
    print("committed " + git("rev-parse", "HEAD").stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
