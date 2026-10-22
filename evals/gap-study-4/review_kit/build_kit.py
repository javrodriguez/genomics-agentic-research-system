#!/usr/bin/env python3
"""Build a blind reviewer's folder outside the Brain: the brief, the purpose, the bytes, and a remote-less clone.

    python3 evals/gap-study-4/review_kit/build_kit.py <folder> --n <N> --athena <outputs folder> [--previous <path to the bytes the last review read>]

The folder must not be under the Brain or this repository. It gets: BRIEF.md with N, COMMIT and the previous-bytes name
filled in; why.md; prereg.json (a copy of the committed draft); the previous review's bytes when given; COMMIT (the sha
the clone is at); and study/, a full-history `--no-local` clone of this repository at HEAD with its remote removed and
background git maintenance off. Refuses when the study has uncommitted changes, so the reviewer reads what is
committed.

ROUND 4 (lane review-kit-port, glitch-f1's ruling F5 and fold 2, Wed 21 Oct 2026): the reviewer runs only light checks
and reads the heavy gates from `athena/` (BRIEF.md step 3). This builder takes that folder itself (--athena, required)
and copies it in, so the operator never adds it by hand and `rounds.py --add` hashes it with everything else. It is
checked before the kit folder is made and again as it is copied: regular files only, no subfolder or link, none
empty, and every file naming the full sha of the commit the clone is at. A gate run at another commit is not
evidence about this one.

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

ATHENA = "athena"


def copy_athena(src: Path, dest: Path | None, head: str) -> tuple[list[str], list[str]]:
    """(problems, names copied). With dest None, or with any problem, nothing is written."""
    problems: list[str] = []
    if not src.is_dir():
        return [f"the athena outputs folder {src.name!r} is not a folder"], []
    entries = sorted(src.iterdir())
    if not entries:
        problems.append("the athena outputs folder is empty: the heavy gates were not handed in")
    for p in entries:
        if p.is_symlink():
            problems.append(f"{p.name} is a link; only regular files are copied")
        elif p.is_dir():
            problems.append(f"{p.name} is a folder; athena/ is flat, one file per command")
        elif not p.is_file():
            problems.append(f"{p.name} is not a regular file")
        else:
            body = p.read_text(errors="replace")
            if not body.strip():
                problems.append(f"{p.name} is empty")
            elif head not in body:
                problems.append(f"{p.name} does not name the commit the clone is at ({head[:12]}); a gate run at "
                                f"another commit is not evidence about this one")
    if problems or dest is None:
        return problems, []
    out = dest / ATHENA
    out.mkdir()
    for p in entries:
        shutil.copy2(p, out / p.name)
    return [], [p.name for p in entries]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a blind reviewer's folder.")
    ap.add_argument("folder", type=Path)
    ap.add_argument("--n", required=True, type=int)
    ap.add_argument("--previous", type=Path, default=None)
    ap.add_argument("--athena", type=Path, required=True)
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
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    athena = args.athena.resolve()
    problems, _ = copy_athena(athena, None, head)
    if problems:
        print("refusing: " + "; ".join(problems))
        return 2
    folder.mkdir(parents=True)
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
    problems, copied = copy_athena(athena, folder, head)
    if problems:
        print("refusing: the athena outputs changed while the kit was built: " + "; ".join(problems))
        return 2
    print(f"built {folder}: review {args.n} at {head[:12]}, clone without a remote, "
          f"{'previous bytes included' if args.previous else 'no previous bytes'}, {len(copied)} athena file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
