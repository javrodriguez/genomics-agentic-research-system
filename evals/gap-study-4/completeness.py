#!/usr/bin/env python3
"""Account for every planned half-cell, reading committed mechanical states.

The pre-registration's tasks list supplies the task-pair count. Its rows list
supplies planned identities (arm, task, half, model, agent, wording, repeat or
pressure, slot and half_cell). A registered subset never shrinks that plan.
Neither this reader nor result.py re-derives a mechanical cap from take counts.
When batch's strict replay closes earlier than publication, its own reason is
shown as a strict close; publication's existing committed states keep precedence.
No model, network or earlier-round data. Standard library only.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_results
import stats
import takes
import batch
import prereg
from graders import labels4


def pair_count(pre: dict) -> int:
    tasks = [t["id"] for t in pre["tasks"]]
    if not tasks or len(tasks) != len(set(tasks)):
        raise ValueError("the pre-registered task list must be nonempty and unique")
    return len(tasks)


def committed_state(cell, states):
    return states.get(cell)


def mechanical_states(history, published, table=None):
    """Read strict closures through batch's replay only; never drive or register."""
    states = dict(published)
    for cell, state in published.items():
        if state.get("note"):
            states[cell] = dict(state, state=f"{state['state']} ({state['note']})")
    if history:
        try:
            strict = batch.Batch(None, None, None, table=table, history=history).closed_cells
        except batch.BatchConfigError as exc:
            raise ValueError(str(exc)) from exc
        for cell, reason in strict.items():
            if cell not in states:
                states[cell] = {"state": f"{labels4.INCOMPLETE_MECHANICAL} (strict close: {reason})",
                                "reason": reason}
    return states


def summarize(pre: dict, records: list, states: dict, registered: list, go_records: list | None = None) -> dict:
    """All planned rows, with state from publication's committed outcomes/rulings.

    go_records: Javier's committed go records for deferred arms (prereg.committed_go_records when None, read only
    when the design defers an arm)."""
    count = pair_count(pre)
    planned = pre["rows"]
    if not isinstance(planned, list) or not planned:
        raise ValueError("the pre-registration must name its planned rows")
    check_results.validate_ledger([dict(r, attempt=1) for r in planned])
    check_results.validate_ledger(registered)
    stats.check_records(records)
    tasks = {t["id"] for t in pre["tasks"]}
    if {r["task"] for r in planned} != tasks:
        raise ValueError("planned rows must cover exactly the pre-registered task list")
    by_cell, plan_keys = collections.defaultdict(list), set()
    for r in planned:
        key = takes.try_key(r)
        if key in plan_keys:
            raise ValueError("a planned try occurs twice")
        plan_keys.add(key)
        by_cell[takes.half_cell_key(r)].append(r)
    if any(takes.try_key(r) not in plan_keys for r in records + registered):
        raise ValueError("a recorded or registered try is outside the plan")
    # Lane gemini-defer, ruling R3 (glitch-f1, 22 Oct 2026): a deferred arm's unmeasured half-cell reads its frozen
    # deferral (prereg.deferral_label: "deferred (Javier, 22 Oct 2026)"), never "no takes".
    # Review NIT-2 (glitch-f1, 22 Oct 2026): after Javier's committed go the arm is no longer deferred, so a half-cell
    # with no take yet reads "no takes", as any arm's does.
    deferred = {arm: prereg.deferral_label(entry) for arm, entry in prereg.deferred_arms(pre).items()}
    if deferred:
        go = prereg.committed_go_records() if go_records is None else go_records
        deferred = {arm: label for arm, label in deferred.items() if not prereg.deferred_arm_go(arm, go)}
    actual = collections.defaultdict(list)
    for r in records:
        actual[takes.half_cell_key(r)].append(r)
    cells = []
    for key, rows in sorted(by_cell.items()):
        r = rows[0]
        mechanical = committed_state(r["half_cell"], states)
        measured = actual[key]
        if mechanical is not None:
            state, reason = mechanical["state"], mechanical["reason"]
        elif len(measured) == len(rows):
            state, reason = "complete", None
        elif not measured and r["arm"] in deferred:
            state = deferred[r["arm"]]
            reason = f"arm {r['arm']}'s counted run is deferred in the frozen deferred_arms"
        else:
            state = stats.NO_TAKES if not measured else "incomplete"
            reason = "no committed graded take" if not measured else "planned takes remain unmeasured"
        cells.append({k: r[k] for k in ("arm", "task", "half", "model", "agent")} |
                     {"state": state, "reason": reason, "recorded": len(measured), "planned": len(rows)})
    return {"task_pairs": count, "cells": cells}


def render(summary: dict) -> str:
    lines = [f"Task pairs in the pre-registered task list: {summary['task_pairs']}", "",
             "| Arm | Task | Half | Model | Harness | Version | Recorded | Planned | State | Reason |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for c in summary["cells"]:
        agent = c["agent"]
        n = str(c["recorded"]) if c["recorded"] else stats.NO_TAKES
        state = c["state"].replace("|", "\\|").replace("\n", " ")
        reason = c["reason"] or ""
        if reason and reason in c["state"]:
            reason = ""
        reason = reason.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {c['arm']} | {c['task']} | {c['half']} | {c['model']} | {agent['harness']} | "
                     f"{agent['version']} | {n} | {c['planned']} | {state} | {reason} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    import result

    got = result.derive()
    if got is None:
        print("completeness: no takes; no cells measured")
        return 0
    summary = got["completeness"]
    print(json.dumps(summary, indent=2) if args.json else render(summary))
    print(f"completeness: {len(summary['cells'])} planned half-cells accounted for")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
