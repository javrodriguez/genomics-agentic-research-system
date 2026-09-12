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
import labels  # noqa: E402

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
    """Every graded take folder for this cell: each holding a driver ledger or a transcript.

    ENUMERATED BY LEDGER, NOT BY TRANSCRIPT. A take whose session file was never found has a ledger
    and no transcript, and its label is `aborted`; enumerating transcripts made it invisible, and the
    cell read as short a take rather than carrying the take it had.
    """
    root = TRANSCRIPTS / task_id / half / model
    if not root.is_dir():
        return []
    dirs = {p.parent for p in root.glob("*/driver-ledger.json")}
    dirs |= {p.parent for p in root.glob("*/transcript.jsonl")}
    return sorted(dirs)


def rehearsals_on_disk(task_id: str, half: str, model: str) -> int:
    """Take rehearsals for this cell, from their own layout (prereg attempt_layout).

    The first version counted every ledger under rehearsals/<task>/ by half and model, which would
    have charged the walk-era plan-gate rehearsal to a take cell. Only a take's rehearsal counts.
    """
    root = HERE / "rehearsals" / task_id / half / model
    if not root.is_dir():
        return 0
    n = 0
    for led in root.glob("*/driver-ledger.json"):
        try:
            row = json.loads(led.read_text())
        except json.JSONDecodeError:
            continue
        if row.get("kind") != "take":
            continue
        n += 1
    return n


_CT = None


def _gap_check_take():
    """This study's check_take, loaded once by path: the first study has a file of the same name."""
    global _CT
    if _CT is None:
        import importlib.util
        # BESIDE ITS OWN FILE, never HERE: the tests repoint HERE at a scratch tree, and a loader that
        # followed it raised rather than reading the checker. The same shape bit takes.py and
        # route_attempt before this.
        spec = importlib.util.spec_from_file_location(
            "gap_check_take_for_run", Path(__file__).resolve().parent / "check_take.py")
        _CT = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_CT)
    return _CT


def models_read(t: Path) -> list[str]:
    """The model ids the transcript's assistant records carry: what a cell is counted under (review 12)."""
    if not t.is_file():
        return []
    seen = set()
    for line in t.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        # REVIEW 20, F6. The harness writes an assistant record of its own when the API refuses a
        # request, carrying the model `<synthetic>`; the checker and the driver both exclude it, and
        # this published field did not.
        if isinstance(rec, dict) and rec.get("type") == "assistant" \
                and not (rec.get("isApiErrorMessage") or rec.get("is_api_error_message")):
            seen.add(str((rec.get("message") or {}).get("model")))
    return sorted(seen)


def pauses_on_disk(task_id: str, half: str, model: str) -> int:
    """Take pauses for this cell (review 14): published beside the rehearsals, both capped."""
    root = HERE / "pauses" / task_id / half / model
    if not root.is_dir():
        return 0
    n = 0
    for led in root.glob("*/driver-ledger.json"):
        try:
            row = json.loads(led.read_text())
        except json.JSONDecodeError:
            continue
        if row.get("kind") == "take":
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
    # REVIEW 16, F6. Every take records the harness version it ran under and nothing read it, so the
    # limitations line promising the versions was written by hand into a section this study says is
    # machine-derived. It is read here, from the same ledgers the labels come from.
    versions: set[str] = set()
    for d in paths:
        led_path = d / "driver-ledger.json"
        if not led_path.is_file():
            raise SystemExit(f"REFUSING to grade {d}: a transcript with no driver ledger was not "
                             f"produced by the driver, so it cannot be tied to a registered row")
        ledger = json.loads(led_path.read_text())
        # REVIEW 13, BLOCKER 1. A ledger that names no take, no session id or no attempt record was not
        # filed by the driver, and no committed row can be shown to own it; it used to default to graded.
        if ledger.get("kind") != "take" or not ledger.get("session_id") or not isinstance(ledger.get("attempt"), dict):
            raise SystemExit(f"REFUSING to grade {d}: its ledger does not name a take, a session id and the "
                             f"driver's attempt record, so no committed row can be shown to own it")
        attempt = ledger["attempt"].get("kind")
        outcome = ledger.get("outcome") or ""
        # REVIEW 19, BLOCKER 1. `labels.from_ledger` returns no reserved label for an outcome it does
        # not recognise, so a deleted or reworded outcome graded a cut take from its partial reply. The
        # checker refuses it; this is the belt on the grading side.
        shapes = tuple(prereg.load().get("driver_outcome_shapes") or ())
        if not outcome.startswith(shapes):
            raise SystemExit(f"REFUSING to grade {d}: its ledger records the outcome {outcome!r}, which "
                             f"is not one of the shapes the pinned driver writes. A take whose outcome "
                             f"the driver did not write cannot be graded from its transcript.")
        if attempt != "graded" or outcome.startswith(("PAUSE", "REHEARSAL")):
            raise SystemExit(f"REFUSING to grade {d}: it holds an attempt that is not a graded take "
                             f"({attempt}, {outcome.split(' ')[0]}), which belongs under rehearsals/ "
                             f"or pauses/ and is never graded")
        if ledger.get("claude_version"):
            versions.add(str(ledger["claude_version"]))
        t = d / "transcript.jsonl"
        if t.is_file():
            data = tx.load(t)
            got = grader.grade(data["turns"], ledger, half, spec)
            sha = data["sha256"]
        else:
            got = labels.result(labels.from_ledger(ledger) or labels.ABORTED,
                                spec[half]["correct_behaviour_label"],
                                [f"no transcript on disk; driver ledger outcome: {outcome}"])
            sha = None
        # REVIEW 21, F1. Limitations line 4 promises a reader that a take published as cut whose last
        # reply ended is named. It was named on the ledger check's screen and nowhere a reader of the
        # published files would meet it.
        cut_after_end_turn = bool(
            outcome.startswith(("timed-out", "aborted")) and t.is_file()
            and _gap_check_take().last_stop_reason(t) == "end_turn")
        out_labels.append({
            "take": d.name,
            "cut_after_end_turn": cut_after_end_turn,
            "transcript_sha256": sha,
            "model_read": models_read(t),
            "label": got["label"],
            "verdict": got["verdict"],
            "evidence": got["evidence"],
        })

    k = sum(1 for x in out_labels if x["verdict"] == "correct")
    rehearsed = rehearsals_on_disk(task_id, half, model)
    # REVIEW 17, F4. `incomplete — mechanical` was printed for any short cell, including one short
    # because its remaining rows were never registered, so a run abandoned partway would publish
    # "mechanical" where nothing mechanical happened. The reason comes from the record.
    paused = pauses_on_disk(task_id, half, model)
    pre = prereg.load()
    exhausted = rehearsed >= int(pre["rehearsal_cap"]) or paused >= int(pre["pause_cap"])
    if len(out_labels) == n:
        state = STATE_RAN
    elif exhausted:
        state = f"{STATE_INCOMPLETE}, {len(out_labels)} of {n}"
    else:
        state = (f"incomplete — {len(out_labels)} of {n}, and no mechanical reason is on record: "
                 f"{rehearsed} rehearsal(s), {paused} pause(s), neither at its cap")
    read = sorted({m for x in out_labels for m in x["model_read"]})
    return {"state": state, "labels": out_labels, "k": k, "n": n, "rehearsals": rehearsed,
            "pauses": paused, "models_read": read,
            "harness_versions": sorted(versions)}


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
