#!/usr/bin/env python3
"""What this study copied from round 2, from which commit, and what it changed.

    python3 evals/haiku-prestudy/copy_manifest.py --write     record COPIED.json from the files as they stand
    python3 evals/haiku-prestudy/copy_manifest.py --check     re-derive all of it; exit 1 on any difference

Every copied file is read from round 2's done commit with `git show`, never from a working tree. For each one
COPIED.json records its source path and blob, the sha256 of the source bytes and of the copy, and whether the
copy differs. A copy that differs must carry a reason in EDITS below; a reason for a file that does not differ,
or a difference with no reason, is refused. `--check` also confirms that round 2's folder, round 1's folder and
the shared transcript parser are unchanged since the source commit, so nothing here can have been edited there.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MANIFEST = HERE / "COPIED.json"

SOURCE_COMMIT = "bf065feedccc0392f69e95a6d674288bb861a2b0"
SOURCE_DIR = "evals/gap-study-2"
FILES = ("drive.py", "prereg.py", "takes.py", "scrub.py", "check_take.py", "study.py",
         "lint_language.py", "commit_msg.py", "scratch_git.py", "check_results.py",
         "review_kit/launch.py", "review_kit/build_kit.py", "review_kit/blindness.py",
         "review_kit/commit_review.py")
UNCHANGED_SINCE_SOURCE = ("evals/gap-study-2", "evals/gap-study", "evals/transcript.py")

# The only copies allowed to differ from their source, and why. Anything not named here must be byte-identical.
EDITS = {
    "study.py": "The binding: this study's name, folder, title and published-section markers. Round 2's harness "
                "builds every path and marker from this file, so no other copied file needs to name this study.",
    "prereg.py": "cells() counts only the halves a task lists. Round 2 listed both halves for every task; this "
                 "study lists one, and the unedited loader would plan six takes for a design of three. The loader "
                 "is not the driver; no take-time behaviour depends on it.",
    "review_kit/blindness.py": "The goal-id marker names this study's goal, gars-haiku-prestudy; round 2's goal id "
                               "stays as a second marker, since operator memory that names round 2 is still a leak.",
    "drive.py": "THE ONE CHANGE (Ruling 1, 19 September 2026): every turn passes --allowedTools with the "
                "pre-registration's driver_change.allowed_tools, the ledger records them, and a docstring "
                "paragraph says so. Nothing else in the driver moves.",
}


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def derive() -> dict:
    files = []
    for f in FILES:
        src = f"{SOURCE_DIR}/{f}"
        shown = git("show", f"{SOURCE_COMMIT}:{src}")
        if shown.returncode != 0:
            raise SystemExit(f"{src} does not exist at {SOURCE_COMMIT[:12]}")
        blob = git("rev-parse", f"{SOURCE_COMMIT}:{src}").stdout.decode().strip()
        copy = (HERE / f).read_bytes()
        files.append({"path": f"evals/haiku-prestudy/{f}", "source": src, "source_blob": blob,
                      "source_sha256": sha256(shown.stdout), "copy_sha256": sha256(copy),
                      "edited": copy != shown.stdout, "why": EDITS.get(f)})
    return {"role": "Every file this study copied from round 2, read from the source commit with git show.",
            "source_commit": SOURCE_COMMIT, "files": files}


def problems(rec: dict) -> list[str]:
    out = []
    for f in rec["files"]:
        name = f["path"].split("evals/haiku-prestudy/", 1)[1]
        if f["edited"] and not f["why"]:
            out.append(f"{name} differs from {f['source']} at the source commit and no reason is recorded")
        if not f["edited"] and f["why"]:
            out.append(f"{name} carries an edit reason but is byte-identical to its source")
    for p in UNCHANGED_SINCE_SOURCE:
        if git("diff", "--quiet", SOURCE_COMMIT, "HEAD", "--", p).returncode != 0:
            out.append(f"{p} has changed since {SOURCE_COMMIT[:12]}; the source this study copied is not intact")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    args = ap.parse_args()
    rec = derive()
    bad = problems(rec)
    if args.write:
        if bad:
            print("refusing to write:\n  - " + "\n  - ".join(bad))
            return 1
        MANIFEST.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"wrote {MANIFEST.name}: {len(rec['files'])} files, "
              f"{sum(f['edited'] for f in rec['files'])} edited")
        return 0
    if not MANIFEST.is_file():
        print("no COPIED.json")
        return 1
    if json.loads(MANIFEST.read_text()) != rec:
        bad.append("COPIED.json does not equal what the files and the source commit derive")
    for b in bad:
        print(f"FAIL {b}")
    if not bad:
        print(f"ok: {len(rec['files'])} files trace to {SOURCE_COMMIT[:12]}, "
              f"{sum(f['edited'] for f in rec['files'])} edited with a reason; round 2, round 1 and the parser unchanged")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
