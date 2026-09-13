#!/usr/bin/env python3
"""Round 2 is a copy of round 1's harness. This proves which bytes were copied, and that round 1 did not move.

    python3 evals/gap-study-2/copy_manifest.py            summary
    python3 evals/gap-study-2/copy_manifest.py --check    exit 1 on any disagreement

COPIED.json holds one entry per copied file:

  path               where the copy lives in this study
  round_1_path       the file it was copied from
  round_1_blob       that file's git blob sha at the base commit (re-derived here from git, never trusted)
  copy_sha256        the sha256 of the bytes AS COPIED, before any edit. It is not the file's current hash:
                     it must equal the sha256 of round 1's blob, which this check re-derives
  edited_after_copy  true once a checkpoint has edited the copy. A false flag over changed bytes, or a
                     true flag over unchanged bytes, is refused: the flag is a claim, and it is checked

and `git diff --stat <base> -- <round 1>/` must be empty, with nothing untracked there either.

WHY. Round 1's result stands on its own bytes, and round 2's claims about "round 1's harness, fixed"
stand on this copy being what it says. A copy nobody can re-derive is a statement, not a record.

Needs full git history (the base commit must resolve). No model, no network, stdlib only.
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
sys.path.insert(0, str(HERE))

import study  # noqa: E402

COPIED = HERE / "COPIED.json"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)


def problems() -> tuple[list[str], int]:
    doc = json.loads(COPIED.read_text())
    base = doc["base_commit"]
    files = doc["files"]
    out: list[str] = []
    if git("cat-file", "-e", f"{base}^{{commit}}").returncode != 0:
        return [f"the base commit {base[:12]} does not resolve here (a shallow clone?); nothing could be checked"], 0
    if not files:
        return ["COPIED.json lists no file, so this check measured nothing. That is not a pass."], 0
    if len(files) != doc["classification"]["copy"]:
        out.append(f"COPIED.json lists {len(files)} file(s) but its classification says {doc['classification']['copy']} were copied")
    seen = set()
    for e in files:
        p, r1 = e["path"], e["round_1_path"]
        if p in seen:
            out.append(f"{p}: listed twice")
        seen.add(p)
        if not r1.startswith(study.ROUND1_REL + "/") or p != study.STUDY_REL + r1[len(study.ROUND1_REL):]:
            out.append(f"{p}: is not the round-2 twin of {r1}")
        blob = git("rev-parse", f"{base}:{r1}")
        got_blob = blob.stdout.decode().strip()
        if blob.returncode != 0 or got_blob != e["round_1_blob"]:
            out.append(f"{r1}: blob at {base[:12]} is {got_blob or 'absent'}, COPIED.json says {e['round_1_blob']}")
            continue
        content = git("cat-file", "blob", got_blob)
        if content.returncode != 0 or hashlib.sha256(content.stdout).hexdigest() != e["copy_sha256"]:
            out.append(f"{p}: copy_sha256 is not the sha256 of round 1's bytes, so it is not what was copied")
        f = REPO / p
        if not f.is_file():
            out.append(f"{p}: listed as copied and missing")
            continue
        unchanged = hashlib.sha256(f.read_bytes()).hexdigest() == e["copy_sha256"]
        if e["edited_after_copy"] is not True and e["edited_after_copy"] is not False:
            out.append(f"{p}: edited_after_copy is {e['edited_after_copy']!r}, not true or false")
        elif e["edited_after_copy"] and unchanged:
            out.append(f"{p}: marked edited_after_copy and its bytes are still the copy's")
        elif not e["edited_after_copy"] and not unchanged:
            out.append(f"{p}: its bytes changed and edited_after_copy is false")
    diff = git("diff", "--stat", base, "--", study.ROUND1_REL + "/")
    if diff.returncode != 0 or diff.stdout.strip():
        out.append(f"round 1 moved since {base[:12]}:\n{diff.stdout.decode()}{diff.stderr.decode()}")
    untracked = git("status", "--porcelain", "--untracked-files=all", "--", study.ROUND1_REL + "/")
    if untracked.stdout.strip():
        out.append(f"round 1's tree carries uncommitted or untracked files:\n{untracked.stdout.decode()}")
    return out, len(files)


def main() -> int:
    ap = argparse.ArgumentParser(description="Check the copy of round 1's harness.")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    found, n = problems()
    doc = json.loads(COPIED.read_text())
    edited = sum(1 for e in doc["files"] if e["edited_after_copy"])
    print(f"{n} copied file(s) checked against {doc['base_commit'][:12]}; {edited} edited after the copy")
    for p in found:
        print(f"  PROBLEM {p}")
    if found:
        return 1
    print(f"clean: every blob re-derives, every copy hash is round 1's bytes, every edit flag agrees with "
          f"the bytes, and {study.ROUND1_REL}/ is unchanged")
    return 0 if args.check or not found else 1


if __name__ == "__main__":
    raise SystemExit(main())
