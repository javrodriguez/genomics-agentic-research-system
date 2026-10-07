#!/usr/bin/env python3
"""Build a blind reviewer's folder outside the Brain: the brief, the purpose, the bytes, and a remote-less clone.

    python3 evals/gap-study-2/review_kit/build_kit.py <folder> --n <N> [--previous <path to the bytes the last review read>]

The folder must not be under the Brain or this repository. It gets: BRIEF.md with N, COMMIT and the previous-bytes name
filled in; why.md; prereg.json (a copy of the committed draft); the previous review's bytes when given; COMMIT (the sha
the clone is at); and study/, a full-history `--no-local` clone of this repository at HEAD with its remote removed and
background git maintenance off. Refuses when the study has uncommitted changes, so the reviewer reads what is
committed.

stdlib only, no model.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_DIR = HERE.parent
REPO = STUDY_DIR.parent.parent
sys.path.insert(0, str(STUDY_DIR))
import scratch_git  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a blind reviewer's folder.")
    ap.add_argument("folder", type=Path)
    ap.add_argument("--n", required=True, type=int)
    ap.add_argument("--previous", type=Path, default=None)
    args = ap.parse_args()
    folder = args.folder.resolve()
    for root, name in ((REPO.resolve(), "this repository"), ((Path.home() / "glitch").resolve(), "the Brain")):
        try:
            folder.relative_to(root)
            print(f"refusing: the folder is under {name}")
            return 2
        except ValueError:
            pass
    dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", str(STUDY_DIR)],
                           capture_output=True, text=True).stdout
    if dirty.strip():
        print("refusing: the study has uncommitted changes; commit them so the reviewer reads what is committed:\n" + dirty)
        return 2
    if folder.exists():
        print(f"refusing: {folder} already exists")
        return 2
    folder.mkdir(parents=True)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "clone", "-q", "--no-local", str(REPO), str(folder / "study")], check=True)
    subprocess.run(["git", "-C", str(folder / "study"), "remote", "remove", "origin"], check=True)
    subprocess.run(["git", "-C", str(folder / "study"), "config", scratch_git.MAINTENANCE_KEY,
                    scratch_git.MAINTENANCE_VALUE], check=True)
    previous = "prereg-as-the-previous-review-read-it.json"
    brief = (HERE / "BRIEF.md").read_text().replace("{N}", str(args.n)).replace("{PREVIOUS}", previous)
    (folder / "BRIEF.md").write_text(brief)
    shutil.copy2(HERE / "why.md", folder / "why.md")
    shutil.copy2(STUDY_DIR / "prereg-draft.json", folder / "prereg.json")
    if args.previous:
        shutil.copy2(args.previous, folder / previous)
    (folder / "COMMIT").write_text(head + "\n")
    print(f"built {folder}: review {args.n} at {head[:12]}, clone without a remote, "
          f"{'previous bytes included' if args.previous else 'no previous bytes'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
