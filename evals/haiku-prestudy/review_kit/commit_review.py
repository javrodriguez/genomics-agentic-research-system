#!/usr/bin/env python3
"""Commit a finished pre-freeze review unedited, with its blindness record beside it.

    python3 evals/gap-study-2/review_kit/commit_review.py <review folder> <N>

Asserts before anything is copied: line 1 of the report is `prereg.json sha256: <the sha256 of the kit's prereg.json, the bytes the reviewer read>`; the
report carries no absolute path and names no person; a ruling line is present. Copies the report to
verification/prefreeze-<N>.md and the blindness record beside it, lints the commit message, and commits with
`git commit -F`. The commit lands exactly the two files, which is what freeze.py's review-commit rule reads.

Never pushes: the push goes through the scanned door, on the owner's grant.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_DIR = HERE.parent
REPO = STUDY_DIR.parent.parent
sys.path.insert(0, str(STUDY_DIR))
import study  # noqa: E402

ABS_PATH = re.compile(r"/(Users|private|var/folders|home)/")
PERSON = re.compile(r"javrodher|rodrij92|javier|@gmail", re.I)
RULING = re.compile(r"^\*\*Ruling: DO (NOT )?FREEZE\.\*\*$", re.M)


def report_problems(text: str, draft_sha: str) -> list[str]:
    problems = []
    first = text.splitlines()[0] if text else ""
    if first != f"prereg.json sha256: {draft_sha}":
        problems.append(f"line 1 is not the current draft's sha256 line: {first[:80]!r}")
    if ABS_PATH.search(text):
        problems.append("the report carries an absolute path")
    if PERSON.search(text):
        problems.append("the report names a person")
    if not RULING.search(text):
        problems.append("no ruling line (**Ruling: DO FREEZE.** or **Ruling: DO NOT FREEZE.**)")
    return problems


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.split("\n")[2].strip())
        return 2
    folder, n = Path(sys.argv[1]).resolve(), sys.argv[2]
    report = folder / f"prefreeze-{n}.md"
    side = folder.parent / (folder.name + "-launch")
    blind = side / "blindness.txt"
    for f in (report, blind):
        if not f.is_file():
            print(f"missing: {f.name}")
            return 2
    # ROUND 2, CP8: the report is bound to the bytes the reviewer was handed, the kit's prereg.json, not to the
    # draft in force at commit time. Review 1's fix moved the draft before its report was committed, and this refused
    # the report for it; whether the seed review read the CURRENT bytes is freeze.py's rule, which also requires the
    # seed to be the latest review committed.
    read_sha = hashlib.sha256((folder / "prereg.json").read_bytes()).hexdigest()
    draft_sha = hashlib.sha256((STUDY_DIR / "prereg-draft.json").read_bytes()).hexdigest()
    text = report.read_text()
    problems = report_problems(text, read_sha)
    if problems:
        print("refusing to commit the report: " + "; ".join(problems))
        return 1
    dest = STUDY_DIR / "verification" / f"prefreeze-{n}.md"
    dest_blind = STUDY_DIR / "verification" / f"prefreeze-{n}-blindness.txt"
    if dest.exists():
        print(f"refusing: {dest.relative_to(REPO)} already exists; a review is committed once")
        return 1
    shutil.copy2(report, dest)
    shutil.copy2(blind, dest_blind)
    ruling = RULING.search(text).group(0).strip("*")
    msg = folder.parent / f"prefreeze-{n}-commit-message.txt"
    msg.write_text(f"review: pre-freeze review {n}, committed as it stands\n\nOne fresh reviewer, launched headless "
                   f"outside the Brain with only the kit, read the draft at sha256 {read_sha[:12]} and ruled: {ruling} "
                   + ("" if read_sha == draft_sha else f"The draft in force at this commit is {draft_sha[:12]}: it moved after the review, so this review cannot seed a freeze. ")
                   + "The report and its blindness record are committed unedited.\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n")
    lint = subprocess.run([sys.executable, str(STUDY_DIR / "commit_msg.py"), str(msg)], capture_output=True, text=True)
    if lint.returncode != 0:
        print(lint.stdout)
        return 1
    rel = [str(dest.relative_to(REPO)), str(dest_blind.relative_to(REPO))]
    subprocess.run(["git", "-C", str(REPO), "add", "--", *rel], check=True)
    staged = subprocess.run(["git", "-C", str(REPO), "diff", "--cached", "--name-only"], capture_output=True,
                            text=True).stdout.split()
    if sorted(staged) != sorted(rel):
        print(f"refusing: the commit would land {staged}, not exactly the review and its blindness record")
        subprocess.run(["git", "-C", str(REPO), "reset", "-q"])
        return 1
    subprocess.run(["git", "-C", str(REPO), "commit", "-q", "-F", str(msg)], check=True)
    sha = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"committed {sha[:12]}: {ruling}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
