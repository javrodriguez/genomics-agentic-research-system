#!/usr/bin/env python3
"""Fidelity: the takes the read-only counts read are the takes the rounds graded, read the way they were graded.

Added after the first run, by PREREG-2.md (not by PREREG.md). It changes no rule and no count. For every take
in the scope of F-01, F-07, F-06 and F-04, it loads the transcript exactly as the counts do (`rules.load_turns`,
which binds it to the published sha256), runs the round's own grader on those turns with the take's driver
ledger, as the round's run.py does, and compares the label with the one the round's results file publishes.
A count that read other turns than the graded ones, or none, cannot pass this.

    python3 evals/validity-followups/fidelity.py [--write | --check]
"""

from __future__ import annotations

import json
import sys

sys.dont_write_bytecode = True

import common  # noqa: E402
import rules  # noqa: E402

FOLLOW_UPS = ("F-01", "F-07", "F-06", "F-04")


def derive(follow_ups: tuple = FOLLOW_UPS) -> dict:
    rows = []
    for fid in follow_ups:
        task, rnds, halves = rules.SCOPE[fid]
        for rnd in rnds:
            spec = rules.spec_of(rnd, task)
            grader = rules.grader_of(rnd, task)
            lab = rules.labels_of(rnd)
            for half in halves:
                takes = rules.published_takes(rnd, task, half)
                same = read = tools_after = 0
                differ = []
                for t in takes:
                    turns, status = rules.load_turns(t)
                    if status != "read":
                        continue
                    read += 1
                    ledger = json.loads((t["dir"] / "driver-ledger.json").read_text())
                    if hasattr(lab, "mark_harness_records"):
                        turns = lab.mark_harness_records(turns, lab.harness_record_flags(t["dir"] / "transcript.jsonl"))
                    got = grader.grade(turns, ledger, half, spec)["label"]
                    if got == t["label"]:
                        same += 1
                    else:
                        differ.append(t["id"])
                    if rules.probe_found(turns, spec[half]):
                        tools_after += len(rules.after_probe(rnd, turns, spec[half])[1])
                rows.append({"follow_up": fid, "round": rnd, "half": half, "seen": len(takes), "read": read,
                             "same_label": same, "differ": differ, "tool_calls_after_probe": tools_after})
    return {"id": "fidelity", "rows": rows}


def render(data: dict) -> str:
    lines = ["| Follow-up | Round | Half | Published (M) | Read (N) | Re-graded to the published label | "
             "Tool calls after the probe, all read takes |", "|---|---|---|---|---|---|---|"]
    for r in data["rows"]:
        lines.append(f"| {r['follow_up']} | {r['round']} | {r['half']} | {r['seen']} | {r['read']} | "
                     f"{r['same_label']} of {r['read']} | {r['tool_calls_after_probe']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(common.main(derive, render, sys.argv[1:]))
