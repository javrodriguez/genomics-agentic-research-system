#!/usr/bin/env python3
"""The blindness of a review, read from the reviewer's own session file, written so the output can be committed.

    python3 evals/gap-study-2/review_kit/blindness.py <review folder>

Two questions, kept apart. (1) Did the operator's own material reach the reviewer's loaded context? Markers that
exist only in the operator's assistant tree are searched in the attachment records. (2) Did the reviewer read outside
its folder? Every absolute path in its tool inputs is listed unless it is inside the folder.

The markers name this round (`gars-eval-v3`, `gap-study-2`, `round 2`), the operator's open-items list, the
assistant's memory and identity files, the operator's objective line, and this repository's own path, taken from
this file's location rather than typed. The account email is matched by EMAIL, unit-tested in tests_review_kit.py.

stdlib only. Never prints a path or an address unmasked.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MARKERS = [
    ("the goal id", "gars-eval-v3"),
    ("the study's folder name", "gap-study-2"),
    ("the round's name", "round 2"),
    ("the operator's open-items list", "Waiting on Javier"),
    ("the assistant's memory folder", "glitch-mem"),
    ("the assistant's identity file", "SOUL.md"),
    ("the operator's objective line", "north star"),
    ("the operator's memory file", "MEMORY.md"),
]
ACCOUNT = re.compile(r"javrodher|rodrij92|javier", re.I)


def mask(s: str, folder: str) -> str:
    s = s.replace(folder, "<review folder>").replace("/private" + folder, "<review folder>")
    s = s.replace(str(REPO), "<repo>").replace(str(Path.home()), "<home>")
    s = re.sub(r"/private/tmp/claude-\d+/\S*", "<harness task folder>", s)
    s = EMAIL.sub("<account email>", s)
    return ACCOUNT.sub("<account>", s)


def session_file(sid: str) -> Path:
    hits = sorted((Path.home() / ".claude" / "projects").glob(f"*/{sid}.jsonl"))
    if len(hits) != 1:
        raise SystemExit(f"session file for the reviewer: {len(hits)} found, cannot read blindness")
    return hits[0]


def report(folder: Path, sid: str) -> str:
    path = session_file(sid)
    ctx, tool_inputs, n = [], [], 0
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        n += 1
        if rec.get("type") == "attachment":
            ctx.append(line)
        if rec.get("type") == "assistant":
            for b in (rec.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    tool_inputs.append(json.dumps(b.get("input") or {}))
    ctx_text = "\n".join(ctx)
    out = [f"blindness check, read from the reviewer's own session file ({n} records, {len(ctx)} attachment records, "
           f"{len(tool_inputs)} tool calls)", "",
           "1. Operator material in the loaded context (attachment records):"]
    for label, w in MARKERS:
        out.append(f"   {label:34} {ctx_text.lower().count(w.lower())}")
    out.append(f"   {'this repository, by path':34} {ctx_text.count(str(REPO))}")
    out.append(f"   {'the account email':34} {len(EMAIL.findall(ctx_text))}")
    outside = set()
    for t in tool_inputs:
        for m in re.finditer(r"(/(?:Users|private|var|tmp|home|etc|opt)[^\s\"'`]*)", t):
            p = m.group(1)
            if str(folder) in p or ("/private" + str(folder)) in p:
                continue
            if "\\" in p or "|" in p:
                outside.add("(a search pattern the reviewer used on its own report, not a path it read)")
                continue
            outside.add(mask(p, str(folder))[:120])
    out += ["", f"2. Absolute paths in the reviewer's tool inputs that are not inside its folder: {len(outside)}"]
    out += ["   - " + p for p in sorted(outside)[:20]]
    return "\n".join(out) + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.split("\n")[2].strip())
        return 2
    folder = Path(sys.argv[1]).resolve()
    side = folder.parent / (folder.name + "-launch")
    sid = (side / "SESSION").read_text().strip()
    text = report(folder, sid)
    (side / "blindness.txt").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
