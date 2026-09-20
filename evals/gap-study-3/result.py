#!/usr/bin/env python3
"""Write RESULT.md from the committed takes, by code, and re-derive it on demand.

    python3 evals/gap-study-3/result.py --write    write RESULT.md from what is committed
    python3 evals/gap-study-3/result.py --check    re-derive it; exit 1 on any difference

WHAT IT PUBLISHES. One count per planned cell, and nothing else about a model. No rate, no percentage, no
verb that characterises. A cell that was not measured is NAMED, with the reason it was not, rather than
left out: a table that quietly drops its empty cells reads as a smaller study that went well.

ROUND 2'S COUNTS PRINT BESIDE, NEVER JOINED. The same three tasks were measured in round 2 under a
different permission condition, and the single most attractive wrong sentence anyone could write about this
round is one that adds the two together. So round 2's counts are a SEPARATE table under a caption this file
writes -- naming, per column, the permission condition, the run date and the instrument -- and round 2's
incomplete cell is marked incomplete with its graded-take count rather than printed as a zero.

EVERY `k of n` HAS n = 3 AND BELONGS TO EXACTLY ONE ROUND'S TABLE. That is checked structurally here, over
the tables' own fields, because a text pattern cannot tell a cell count from `slice 4 of 20`. The words
that join two instruments in a sentence are lint_pooling.py's job; this is the other half of that rule.

IT REFUSES AGAINST A DRAFT. A number graded against a design that can still change was not pre-registered,
whatever the design says about itself. Before the freeze this file reports what it has graded -- zero -- and
says so in those words rather than printing a pass.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RESULT = HERE / "RESULT.md"
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE))

import mode_binding  # noqa: E402
import prereg  # noqa: E402
import round2  # noqa: E402
import study  # noqa: E402

N = 3


def planned_cells() -> list[tuple[str, str, str]]:
    """Every (task, half, model) the frozen design plans, in a fixed canonical order."""
    pre = prereg.load()
    out = []
    for t in pre["tasks"]:
        for half in round2.HALVES:
            if half in t:
                for m in pre["models"]:
                    out.append((t["id"], half, m))
    return sorted(out)


def graded() -> dict[tuple[str, str, str], dict]:
    """Per cell: the graded takes on disk, their labels, and the mode their sessions recorded."""
    out: dict[tuple[str, str, str], dict] = {}
    base = HERE / "transcripts"
    rows = {r["attempt"]: r for r in mode_binding.rows()}
    for t in sorted(base.glob("*/*/*/*/transcript.jsonl")) if base.is_dir() else []:
        task, half, model, take = t.parts[-5], t.parts[-4], t.parts[-3], t.parts[-2]
        cell = out.setdefault((task, half, model), {"takes": [], "modes": set()})
        cell["takes"].append(take)
        r = rows.get(str(t.parent.relative_to(HERE)))
        if r:
            cell["modes"].add(r["recorded"])
    return out


def attempts_by_kind(kind: str) -> dict[tuple[str, str, str], list[dict]]:
    """Rehearsals or pauses per cell, with the reasons each carries."""
    out: dict[tuple[str, str, str], list[dict]] = {}
    base = HERE / kind
    for led in sorted(base.rglob("driver-ledger.json")) if base.is_dir() else []:
        d = json.loads(led.read_text())
        key = (d.get("task"), d.get("half"), d.get("model_requested"))
        out.setdefault(key, []).append({
            "row": d.get("row"), "reasons": (d.get("attempt") or {}).get("reasons") or [],
            "outcome": d.get("outcome"),
        })
    return out


def held_counts() -> dict[tuple[str, str, str], dict]:
    """The HELD count per cell, read from the graders' own output, never from the takes on disk.

    REVIEW 1, BLOCKER 1. This file used to put the number of take folders under the column headed `held`
    and never opened results/. Every complete cell would have published `3 of 3` whatever the models did,
    the earlier round's column beside it prints a real held count, and the study's own question -- how many
    of three takes each cell holds -- would not have been answered by its own publication. Nothing went
    red, because the battery checked n, reasons and captions and never what the number meant.

    `k` is written by run.py from the graders' verdicts. It is read here and nowhere else in this file.
    """
    out: dict[tuple[str, str, str], dict] = {}
    for f in sorted(RESULTS.glob("*.json")) if RESULTS.is_dir() else []:
        rec = json.loads(f.read_text())
        task = rec.get("task") or f.stem
        for model, halves in (rec.get("cells") or {}).items():
            for half, c in halves.items():
                out[(task, half, model)] = {"k": c.get("k"), "n": c.get("n"),
                                            "state": c.get("state"),
                                            "labels": [l.get("label") for l in (c.get("labels") or [])]}
    return out


def cell_state(key, g, rehearsals, pauses, pre, held) -> dict:
    """Complete, or unmeasured with a reason. There is no third state and no silent one."""
    task, half, model = key
    takes = g.get(key, {}).get("takes", [])
    reh = rehearsals.get(key, [])
    pau = pauses.get(key, [])
    modes = sorted(g.get(key, {}).get("modes", set()))
    cap = int(pre["rehearsal_cap"])
    if len(takes) >= N:
        state, reason = "complete", None
    elif len(reh) >= cap:
        reasons = sorted({r for a in reh for r in a["reasons"]})
        state = "unmeasured"
        reason = (f"capped: {len(reh)} rehearsal(s) at the cap of {cap}, reason(s) {reasons}")
    elif not takes and not reh and not pau:
        state, reason = "unmeasured", "not run"
    else:
        state = "unmeasured"
        reason = (f"incomplete: {len(takes)} graded take(s) of {N}, {len(reh)} rehearsal(s), "
                  f"{len(pau)} pause(s)")
    h = held.get(key) or {}
    return {"task": task, "half": half, "model": model,
            "held": h.get("k"), "labels": h.get("labels") or [],
            "graded": len(takes), "n": N,
            "state": state, "reason": reason, "recorded_permission_mode": modes,
            "expected_permission_mode": (pre["driver_constants"].get("permission_mode_expected") or {})
                                        .get(model)}


def round_two_table() -> dict:
    """Round 2's counts for the same three tasks, with its incomplete cell marked as incomplete."""
    cells = round2.cells()
    modes = round2.cell_modes()
    rows = []
    for task in round2.TASKS:
        for model, halves in sorted(cells[task]["cells"].items()):
            for half, c in sorted(halves.items()):
                state = str(c.get("state") or "")
                rows.append({
                    "task": task, "half": half, "model": model,
                    "graded": int(c.get("k") or 0) if "incomplete" not in state.lower() else None,
                    "n": int(cells[task].get("n") or N),
                    "incomplete": "incomplete" in state.lower(),
                    "state": state,
                    "recorded_permission_mode": modes.get(task, {}).get(model, {}).get(half),
                })
    return {"rows": rows, "n": N}


def caption() -> str:
    """Written here, not typed: per column, the condition, the run date and the instrument."""
    pre = prereg.load()
    r2 = round2.frozen()
    entries = len(pre["driver_change"]["allowed_tools"])
    return (
        "| | this round | the earlier round |\n|---|---|---|\n"
        f"| permission condition | `--permission-mode {pre['driver_constants']['permission_mode']}` "
        f"and a pre-registered list of {entries} admitted commands on every turn | "
        f"`--permission-mode {r2['driver_constants']['permission_mode']}` alone |\n"
        f"| mode the sessions recorded | per model, as each cell prints it | "
        f"per model, as the earlier round's own transcripts record it |\n"
        f"| run date | {date.today().isoformat()} | {r2.get('frozen_at', 'as its frozen file records')} |\n"
        f"| instrument | copied byte for byte from the earlier round's done commit "
        f"{round2.frozen().get('study', 'that round')}; the take checker, every grader and the label "
        f"reader are byte-identical | its own |\n\n"
        "The two tables are read separately. The instrument is the same and the permission condition is "
        "not, so a figure spanning them would describe neither.")


def derive() -> dict:
    pre = prereg.load()
    g, reh, pau, held = graded(), attempts_by_kind("rehearsals"), attempts_by_kind("pauses"), held_counts()
    cells = [cell_state(k, g, reh, pau, pre, held) for k in planned_cells()]
    return {
        "planned_cells": len(cells),
        "planned_takes": len(cells) * N,
        "graded_takes": sum(c["graded"] for c in cells),
        "complete_cells": sum(1 for c in cells if c["state"] == "complete"),
        "cells": cells,
        "round_two": round_two_table(),
        "amendments": pre.get("amendments") or [],
    }


def structural_problems(rec: dict) -> list[str]:
    """Every k of n has n = 3 and belongs to exactly one round's table."""
    out = []
    for c in rec["cells"]:
        if c["n"] != N:
            out.append(f"{c['task']}/{c['half']}/{c['model']} publishes n = {c['n']}, not {N}")
        if c["graded"] > c["n"]:
            out.append(f"{c['task']}/{c['half']}/{c['model']} has {c['graded']} graded takes of {c['n']}")
        if c["state"] != "complete" and not c["reason"]:
            out.append(f"{c['task']}/{c['half']}/{c['model']} is not complete and names no reason")
        # REVIEW 1, BLOCKER 1. A complete cell must publish a HELD count read from the graders, and that
        # count is never the number of takes that ran -- that is the denominator, not the answer.
        if c["state"] == "complete":
            if c["held"] is None:
                out.append(f"{c['task']}/{c['half']}/{c['model']} is complete and publishes no held count "
                           f"read from the graders")
            elif not 0 <= c["held"] <= c["n"]:
                out.append(f"{c['task']}/{c['half']}/{c['model']} publishes a held count of {c['held']} "
                           f"outside 0..{c['n']}")
            elif len(c["labels"]) != c["graded"]:
                out.append(f"{c['task']}/{c['half']}/{c['model']} publishes {len(c['labels'])} grader "
                           f"label(s) for {c['graded']} graded take(s)")
    for r in rec["round_two"]["rows"]:
        if r["n"] != N:
            out.append(f"the earlier round's {r['task']}/{r['half']}/{r['model']} publishes n = {r['n']}")
        if r["incomplete"] and r["graded"] is not None:
            out.append(f"the earlier round's {r['task']}/{r['half']}/{r['model']} is incomplete and "
                       f"publishes a count")
    return out


def render(rec: dict) -> str:
    L = [f"# {study.STUDY_TITLE} — result", "",
         f"{rec['graded_takes']} graded take(s) of {rec['planned_takes']} planned; "
         f"{rec['complete_cells']} complete cell(s) of {rec['planned_cells']} planned.", "",
         "Every count below is a count of three takes. The `held` column is what the graders read from the "
         "transcripts; `takes graded` is how many takes the cell has, which is the denominator and never "
         "the answer. No cell is left out: a cell that was not measured is named with the reason.", "",
         "## This round", "",
         "| task | half | model | held | takes graded | recorded mode | state |",
         "|---|---|---|---|---|---|---|"]
    for c in rec["cells"]:
        h = f"{c['held']} of {c['n']}" if c["state"] == "complete" and c["held"] is not None else "—"
        modes = ", ".join(c["recorded_permission_mode"]) or "—"
        L.append(f"| `{c['task']}` | {c['half']} | `{c['model']}` | {h} | {c['graded']} of {c['n']} | "
                 f"{modes} | {c['state']}{'' if not c['reason'] else ' — ' + c['reason']} |")
    L += ["", "## The earlier round, beside — never joined", "", caption(), "",
          "| task | half | model | held | recorded mode |", "|---|---|---|---|---|"]
    for r in rec["round_two"]["rows"]:
        held = "incomplete" if r["incomplete"] else f"{r['graded']} of {r['n']}"
        L.append(f"| `{r['task']}` | {r['half']} | `{r['model']}` | {held} | "
                 f"{r['recorded_permission_mode'] or '—'} |")
    if rec["amendments"]:
        L += ["", "## Amendments", ""]
        for a in rec["amendments"]:
            L.append(f"- {json.dumps(a)}")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not prereg.is_frozen():
        rec = derive()
        print(f"not applicable — not frozen. graded {rec['graded_takes']} of {rec['planned_takes']}, "
              f"complete cells {rec['complete_cells']} of {rec['planned_cells']}. A number graded against "
              f"a design that can still change was not pre-registered, so nothing is published and this "
              f"green claims nothing.")
        return 0

    rec = derive()
    bad = structural_problems(rec)
    print(f"graded {rec['graded_takes']} of {rec['planned_takes']}")
    print(f"complete cells {rec['complete_cells']} of {rec['planned_cells']}")
    if args.write:
        if bad:
            print("refusing to write:\n  - " + "\n  - ".join(bad))
            return 1
        RESULT.write_text(render(rec))
        print(f"wrote {RESULT.name}")
        return 0
    if not RESULT.is_file():
        bad.append("no RESULT.md")
    elif RESULT.read_text() != render(rec):
        bad.append("RESULT.md is not what this file writes from the committed takes")
    for b in bad:
        print(f"FAIL {b}")
    if not bad:
        print("ok: the result re-derives from the committed takes")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
