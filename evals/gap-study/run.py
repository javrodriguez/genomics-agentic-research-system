#!/usr/bin/env python3
"""Grade every committed take, and say what state each cell is in.

    python3 evals/gap-study/run.py --all
    python3 evals/gap-study/run.py --task scope-read

WHAT IT PRODUCES. One `results/<task>.json` per task, holding, per model per half, the n labels and
`k of n`, and a state per cell in {RAN, incomplete — mechanical, not run — <reason>}. A second run
is byte-identical, because every field is re-derived from committed transcripts and the frozen file
and nothing is carried over from the last run.

IT REFUSES AGAINST A DRAFT. This is the file that turns transcripts into numbers, so it is the file
that most needs the pre-registration to be frozen. A number graded against a design that can still
change was not pre-registered, whatever the design says about itself. `prereg.require_frozen` is
called before anything is read.

NO MODEL, NO NETWORK. The graders are stdlib and read committed bytes. A cell's state is decided
from what is on disk and from the ledger, never from what a label looks like -- a runner that could
decide a cell was `incomplete` after seeing its labels could decide it whenever the labels were
disappointing.

EVERY MODEL IN THE FIXED LIST GETS A ROW, including one that will never produce a take. A model that
does not run publishes `not run` with its reason from the pre-registration. Dropping it from the
output would make the table read as though the axis had been narrower from the start.

A CELL WITH NO TRANSCRIPTS IS NOT A PASS AND NOT A FAILURE. It is `not run — no transcript`, and it
says so. This study has been bitten before by a gate that reported zero findings over zero inputs.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "graders"))
sys.path.insert(0, str(REPO / "evals"))

import prereg  # noqa: E402
import transcript as tx  # noqa: E402

RESULTS = HERE / "results"
TRANSCRIPTS = HERE / "transcripts"

STATE_RAN = "RAN"
STATE_INCOMPLETE = "incomplete — mechanical"


def grader_for(task_id: str):
    """The module the frozen file names for this task, imported by that name and no other."""
    mod = task_id.replace("-", "_")
    try:
        return importlib.import_module(mod)
    except ModuleNotFoundError:
        return None


def takes_on_disk(task_id: str, half: str, model: str) -> list[Path]:
    root = TRANSCRIPTS / task_id / half / model
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob("*/transcript.jsonl"))


def rehearsals_on_disk(task_id: str, half: str, model: str) -> int:
    root = HERE / "rehearsals" / task_id
    if not root.is_dir():
        return 0
    n = 0
    for led in root.glob("*/driver-ledger.json"):
        try:
            row = json.loads(led.read_text())
        except json.JSONDecodeError:
            continue
        if row.get("half") == half and row.get("model_requested") == model:
            n += 1
    return n


def grade_cell(task_id: str, half: str, model: str, spec: dict, n: int) -> dict:
    reason = prereg.not_run_reason(model)
    if reason:
        # The recorded reason already opens with "not run — ", because that is the phrase the
        # protocol fixes for a cell that never ran. Prefixing it again produced
        # "not run — not run — the local tier was dropped…" in every dropped cell of every table.
        state = reason if reason.startswith("not run") else f"not run — {reason}"
        return {"state": state, "labels": [], "k": 0, "n": n}

    paths = takes_on_disk(task_id, half, model)
    if not paths:
        return {"state": "not run — no transcript on disk", "labels": [], "k": 0, "n": n}

    grader = grader_for(task_id)
    if grader is None:
        return {"state": f"not run — no grader module for {task_id}", "labels": [], "k": 0, "n": n}

    out_labels: list[dict] = []
    for p in paths:
        led_path = p.parent / "driver-ledger.json"
        ledger = json.loads(led_path.read_text()) if led_path.is_file() else {}
        data = tx.load(p)
        got = grader.grade(data["turns"], ledger, half, spec)
        out_labels.append({
            "take": p.parent.name,
            "transcript_sha256": data["sha256"],
            "label": got["label"],
            "verdict": got["verdict"],
            "evidence": got["evidence"],
        })

    k = sum(1 for x in out_labels if x["verdict"] == "correct")
    rehearsed = rehearsals_on_disk(task_id, half, model)
    state = STATE_RAN if len(out_labels) == n else f"{STATE_INCOMPLETE}, {len(out_labels)} of {n}"
    return {"state": state, "labels": out_labels, "k": k, "n": n, "rehearsals": rehearsed}


def run_task(task_id: str) -> dict:
    spec = prereg.task(task_id)
    n = prereg.n()
    cells: dict[str, dict] = {}
    for model in prereg.models():
        cells[model] = {half: grade_cell(task_id, half, model, spec, n)
                        for half in ("positive", "control")}
    return {
        "task": task_id,
        "n": n,
        "correct_labels": {h: spec[h]["correct_behaviour_label"] for h in ("positive", "control")},
        # THE VERDICT, not the expectation. `expected` is what the run guessed before any control
        # ran; `observed_for_probed_behaviour` is what the scripted attempts and the reviewers
        # established. They diverge on precondition-refusal, which EXPECTED enforced and is silent
        # for the behaviour its probe elicits -- so an analysis reading `expected` would publish
        # that task as enforced beside every reviewer's ruling, and a model holding all six tasks
        # would publish as covering five.
        "layer": {"expected": spec["layer"]["expected"],
                  "probed_behaviour": spec["layer"].get("probed_behaviour"),
                  "observed_for_probed_behaviour":
                      spec["layer"].get("observed_for_probed_behaviour"),
                  "evidence": spec["layer"].get("evidence")},
        "grader": spec["grader"].get("path"),
        "cells": cells,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Grade every committed take.")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--task")
    args = ap.parse_args()

    prereg.require_frozen("run.py")

    tasks = [t["id"] for t in prereg.load()["tasks"]] if args.all else ([args.task] if args.task else [])
    if not tasks:
        ap.error("give --all or --task <id>")

    RESULTS.mkdir(parents=True, exist_ok=True)
    graded = 0
    for task_id in tasks:
        res = run_task(task_id)
        (RESULTS / f"{task_id}.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
        ran = sum(1 for m in res["cells"].values()
                  for c in m.values() if c["state"] == STATE_RAN)
        graded += sum(len(c["labels"]) for m in res["cells"].values() for c in m.values())
        print(f"{task_id:24} cells RAN {ran} of {len(res['cells']) * 2}")

    print(f"\n{graded} graded take(s) across {len(tasks)} task(s)")
    if graded == 0:
        print("No take has been graded. That is the honest state of this study, not a pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
