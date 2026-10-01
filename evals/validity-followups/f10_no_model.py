#!/usr/bin/env python3
"""F-10: the no-model table. An oracle and three trivial replies per half of each task, through round 2's
pinned graders, built as docs/validity/probes.py builds its takes. Reads no take. Frozen in PREREG.md
(section F-10) and rules.py.

    python3 evals/validity-followups/f10_no_model.py [--write | --check]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import common  # noqa: E402
import rules  # noqa: E402


def derive() -> dict:
    rows = [rules.f10_row(task, half, kind)
            for task in rules.F10_TASKS for half in rules.HALVES for kind in rules.F10_REPLIES]
    return {"id": "F-10", "graders": "evals/gap-study-2/graders", "rows": rows}


def render(data: dict) -> str:
    lines = ["| Task | Half | Correct label | Reply | Label | Verdict |", "|---|---|---|---|---|---|"]
    for r in data["rows"]:
        lines.append(f"| {r['task']} | {r['half']} | `{r['correct_label']}` | {r['reply']} | `{r['label']}` "
                     f"| {r['verdict']} |")
    n = len(data["rows"])
    lines.append("")
    for kind in rules.F10_REPLIES:
        rs = [r for r in data["rows"] if r["reply"] == kind]
        lines.append(f"Reply `{kind}`: correct on {sum(r['verdict'] == 'correct' for r in rs)} of {len(rs)} halves.  ")
    lines.append(f"{n} rows, none pooled into any round.")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(common.main(derive, render, sys.argv[1:]))
