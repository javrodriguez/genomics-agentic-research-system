#!/usr/bin/env python3
"""Bind every contract sentence this study rests on to the bytes it was read from.

    python3 evals/gap-study/contracts.py --check          every quote, against its pinned blob
    python3 evals/gap-study/contracts.py --check --worktree   also against the working tree
    python3 evals/gap-study/contracts.py --show <task>    what a task's design quotes, and why

WHY THIS EXISTS. Six of this study's tasks are built out of sentences in the GARS contracts. The
positive half of `precondition-refusal` is only a fair probe if the contract really does say the
agent must refuse; the expected `silent` classification of `scope-read` is only honest if the deny
list really does deny no read. Every one of those is a claim about a file, and a claim about a file
goes stale the moment somebody edits the file.

Prose describing a file drifts silently -- the sentence keeps reading correctly while the thing it
describes has moved. So the sentence is not described here, it is STORED here, byte for byte, with
the git blob it came out of. The check re-reads that blob and asserts the stored text is a byte
substring of it.

WHY THE BLOB AND NOT THE PATH. Reading the working tree would pass in a dirty checkout and would
tell a reader nothing about what was true at the freeze. Reading the blob proves the pin itself:
the bytes are fetched by content hash, so they are the bytes or the fetch fails. `--worktree` adds
the second question -- is the live file still that blob -- and reports drift separately, because a
contract that has MOVED since the freeze is a limitations line, not a broken study.

LINE NUMBERS ARE RECORDED AND ARE NEVER THE TEST. A line number is the most fragile thing about a
quote; one inserted paragraph above it and every citation below is wrong while every sentence is
still present. The test is the byte substring. The line numbers are carried for a reader who wants
to go and look, and `--check` reports when one has moved without failing for it.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
QUOTES = HERE / "contract_quotes.json"


def load() -> dict:
    if not QUOTES.is_file():
        print(f"no quote table at {QUOTES.relative_to(REPO)}", file=sys.stderr)
        raise SystemExit(2)
    return json.loads(QUOTES.read_text())


def blob_bytes(sha: str) -> str | None:
    out = subprocess.run(["git", "-C", str(REPO), "cat-file", "blob", sha],
                         capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None


def head_blob(path: str) -> str | None:
    out = subprocess.run(["git", "-C", str(REPO), "rev-parse", f"HEAD:{path}"],
                         capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


def line_of(haystack: str, needle: str) -> int | None:
    """1-indexed line where the quote starts, for the drift note."""
    idx = haystack.find(needle)
    if idx < 0:
        return None
    return haystack.count("\n", 0, idx) + 1


def check(worktree: bool) -> int:
    doc = load()
    quotes = doc["quotes"]
    failures: list[str] = []
    moved: list[str] = []
    detached: list[str] = []

    if not quotes:
        print("the quote table is empty. Nothing was checked, and that is not a pass.")
        return 2

    for q in quotes:
        raw = blob_bytes(q["git_blob_sha"])
        if raw is None:
            failures.append(f"{q['id']}: blob {q['git_blob_sha'][:12]} is not in this repository "
                            f"(a shallow or partial clone cannot verify this study)")
            continue
        if q["text"] not in raw:
            failures.append(f"{q['id']}: the stored text is NOT a byte substring of "
                            f"{q['file']} at the pinned blob")
            continue

        at = line_of(raw, q["text"])
        if at is not None and at != q["line_start"]:
            moved.append(f"{q['id']}: recorded at line {q['line_start']}, found at {at} "
                         f"in the pinned blob")

        if worktree:
            live = head_blob(q["file"])
            if live is None:
                detached.append(f"{q['id']}: {q['file']} is not at HEAD")
            elif live != q["git_blob_sha"]:
                live_raw = blob_bytes(live) or ""
                still = "still present" if q["text"] in live_raw else "GONE"
                detached.append(f"{q['id']}: {q['file']} has changed since the pin "
                                f"({q['git_blob_sha'][:12]} -> {live[:12]}); the sentence is {still}")

    print(f"contract quotes: {len(quotes)} checked against their pinned blobs")
    print(f"  system under test tree: {doc.get('system_under_test_tree_sha', '?')[:12]}")
    print(f"  retrieved:              {doc.get('retrieved', '?')}")

    by_task: dict[str, int] = {}
    for q in quotes:
        by_task[q["task"]] = by_task.get(q["task"], 0) + 1
    for task, n in sorted(by_task.items()):
        print(f"  {task:22} {n} quote(s)")

    if moved:
        print("\nline numbers that have moved (recorded, not a failure):")
        for m in moved:
            print(f"  - {m}")

    if detached:
        print("\nfiles that changed since the pin (a limitations line, not a failure):")
        for d in detached:
            print(f"  - {d}")

    if failures:
        print(f"\n{len(failures)} BINDING FAILURE(S):")
        for f in failures:
            print(f"  - {f}")
        print("\nA quote that is no longer in its file means a task's design rests on a sentence "
              "that has been edited or removed. Do not update the stored text to match; find out "
              "what changed in the contract first.")
        return 1

    print("\nevery stored sentence is a byte substring of the blob it was pinned to")
    return 0


def show(task: str) -> int:
    doc = load()
    rows = [q for q in doc["quotes"] if q["task"] == task]
    if not rows:
        tasks = sorted({q["task"] for q in doc["quotes"]})
        print(f"no quotes for {task!r}. Tasks: {', '.join(tasks)}")
        return 2
    for q in rows:
        print(f"\n=== {q['id']} — {q['file']}:{q['line_start']}-{q['line_end']}")
        print(f"    blob {q['git_blob_sha']}")
        print(f"    why: {q['why']}\n")
        for line in q["text"].split("\n"):
            print(f"    | {line}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Bind the study's contract quotes to their bytes.")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--worktree", action="store_true",
                    help="also report whether each file has changed since it was pinned")
    ap.add_argument("--show", metavar="TASK")
    args = ap.parse_args()

    if args.show:
        return show(args.show)
    if args.check:
        return check(args.worktree)
    ap.error("give --check or --show <task>")


if __name__ == "__main__":
    raise SystemExit(main())
