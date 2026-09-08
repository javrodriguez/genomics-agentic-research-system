#!/usr/bin/env python3
"""Run the pre-registered evaluation: grade every task whose transcripts are present.

WHAT THIS DOES, AND WHAT IT DELIBERATELY DOES NOT. It reads evals/prereg.json -- the frozen task
list, thresholds and transcript layout -- dispatches each task to the grader the pre-registration
names, and writes one results file per task. It decides nothing. Every threshold comes from the
frozen file, every verdict comes from a grader, and the only judgement this module makes is the
one the pre-registration already fixed: a paired task passes when BOTH of its halves pass.

    python evals/run.py --all              grade everything gradeable, write evals/results/
    python evals/run.py --check-declared   what is declared, and what is published

THE STATES, and why each is named rather than collapsed. Every task prints exactly one line:

    RAN                      both halves graded against committed transcripts
    SKIPPED-no-transcript    a half's transcript is not in the tree
    SKIPPED-<requirement>    a named requirement is missing (e.g. the de_results.csv a run wrote)

A SKIP is never a pass and is never counted as one. A task that RAN but whose grader could not
read an observed value is a FAIL, not a skip: "the agent said something I could not read" is a
result about the run, and scoring it as absent would let an unreadable answer escape the table.
That rule is the pre-registration's, not this file's, and it is why the graders publish an
explicit `unreadable` label rather than falling silent.

NO MODEL IS CALLED, here or anywhere below this line. Grading reads committed bytes: the
transcripts the runs wrote, and the results files those runs produced. The Python standard
library is the whole dependency list, so this runs in CI from a cold clone with nothing
installed -- which is the point of grading from transcripts rather than by re-running an agent.

`model_or_none` is read OFF the transcript: the model the run under test used, when the capture
records one, and null when it does not. It is never this process's model, because this process
has none.

stdlib only. Serves evals/prereg.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent
sys.path.insert(0, str(EVALS))
sys.path.insert(0, str(EVALS / "graders"))

import freeze  # noqa: E402
import confounded_refusal as t_confounded  # noqa: E402
import cross_run_repro as t_repro  # noqa: E402
import planted_effect as t_planted  # noqa: E402

PREREG = EVALS / "prereg.json"
NOT_RUN = EVALS / "not-run.json"
RESULTS = EVALS / "results"

STATE_RAN = "RAN"
STATE_NO_TRANSCRIPT = "SKIPPED-no-transcript"

HALVES = ("positive", "control")


# ---------------------------------------------------------------------------
# The frozen file, and the sha that anchors it.
# ---------------------------------------------------------------------------


def load_prereg() -> dict:
    if not PREREG.is_file():
        raise SystemExit(f"no pre-registration at {PREREG}: nothing can be graded without it")
    return json.loads(PREREG.read_text())


def prereg_ref() -> dict:
    """The freeze commit and whether this checkout can prove it -- evals/freeze.py's answer.

    Derived from git rather than written into the file, because a sha a file states about itself
    is a claim and one git can re-derive is a fact. When the checkout cannot prove it (a tarball,
    a shallow clone) the sha is None and the reason is recorded in the results file rather than a
    wrong sha being written there: see freeze.py for the shallow-clone defect this closes. The
    results file still carries prereg_sha256, which binds the bytes with no history at all.
    """
    return freeze.freeze_ref()


def prereg_sha256() -> str:
    return hashlib.sha256(PREREG.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Where a task's transcripts live. The layout is the pre-registration's, not this file's.
# ---------------------------------------------------------------------------


def not_run_declarations() -> dict:
    """Tasks declared unrunnable against the pinned system, with the reason and its evidence.

    Read here so a declared task never reaches a grader and never reads as a pass. The
    declaration is NOT trusted: check_results.py re-runs each evidence command, and a task
    declared not-run that turns out to run is a red there.
    """
    if not NOT_RUN.is_file():
        return {}
    return json.loads(NOT_RUN.read_text()).get("tasks", {})


def requirement_slug(text: str) -> str:
    """A named requirement, in the shape the pre-registration's criterion 3 fixed:
    exactly one of `RAN` or `SKIPPED-<named requirement>`."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words[:7]) or "unnamed-requirement"


def half_dir(task_id: str, half: str) -> Path:
    return EVALS / "transcripts" / task_id / half


def transcripts_for(prereg: dict, task_id: str, half: str) -> list[Path]:
    layout = prereg["transcript_layout"]
    d = half_dir(task_id, half)
    if task_id == "cross-run-repro":
        return [d / name for name in layout["cross_run_repro"]]
    return [d / layout["single_run_tasks"]]


def model_on_transcript(path: Path) -> str | None:
    """The model the RUN UNDER TEST used, read off its own capture. Never this process's."""
    try:
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            msg = rec.get("message") if isinstance(rec.get("message"), dict) else rec
            model = msg.get("model")
            if isinstance(model, str) and model:
                return model
    except OSError:
        return None
    return None


# ---------------------------------------------------------------------------
# Grading one task. Dispatch only -- the verdict is the grader's.
# ---------------------------------------------------------------------------


def grade_half(task_id: str, half: str, spec: dict, files: list[Path]) -> dict:
    if task_id == "confounded-refusal":
        return t_confounded.grade(files[0], half,
                                  expected_rank=spec.get("expected_design_rank"))
    if task_id == "planted-effect":
        d = half_dir(task_id, half)
        return t_planted.grade(files[0], half, d / "de_results.csv", d / "truth_planted.json")
    if task_id == "cross-run-repro":
        return t_repro.grade(files[0], files[1], half)
    raise SystemExit(f"no grader wired for task {task_id!r}; the pre-registration names it, "
                     f"so this runner is out of date with the frozen file")


def missing_requirement(task_id: str, half: str, files: list[Path]) -> str | None:
    """The NAMED thing that is absent, or None. A skip always says what it wanted."""
    for f in files:
        if not f.is_file():
            return STATE_NO_TRANSCRIPT
    if task_id == "planted-effect":
        d = half_dir(task_id, half)
        for name in ("de_results.csv", "truth_planted.json"):
            if not (d / name).is_file():
                return f"SKIPPED-no-{name}"
    return None


def relativise(result: dict) -> None:
    """Every transcript path a grader recorded becomes repository-relative.

    A fresh-context verifier found the published result carried an absolute path from the machine
    that graded it, so a reproduction run on any other machine dirtied the file in exactly one
    line while every verdict, label and sha reproduced byte for byte. The path is the only
    machine-dependent thing in the artifact, and it should not be: the result must be
    byte-identical to what the pinned graders re-produce from the pinned transcripts, on any
    machine, or the published file cannot be checked against them.
    """
    def rel(p: str) -> str:
        try:
            return str(Path(p).resolve().relative_to(REPO))
        except ValueError:
            return p
    if isinstance(result.get("transcript"), str):
        result["transcript"] = rel(result["transcript"])
    for t in result.get("transcripts") or []:
        if isinstance(t, dict) and isinstance(t.get("path"), str):
            t["path"] = rel(t["path"])


def run_task(prereg: dict, task: dict, ref: dict, declared: dict) -> dict:
    task_id = task["id"]
    halves: dict[str, dict] = {}
    state = STATE_RAN

    decl = declared.get(task_id)
    if decl:
        # Declared unrunnable against the pinned system. It is published with its missing
        # requirement named, and it is never graded: a task the system cannot accept has no
        # behaviour to score, and scoring it anyway would be inventing one.
        return {
            "task": task_id,
            "prereg_sha": ref["sha"],
            "prereg_sha_verifiable": ref["verifiable"],
            "prereg_sha_note": ref["why"],
            "prereg_sha256": prereg_sha256(),
            "state": f"SKIPPED-{requirement_slug(decl['missing_requirement'])}",
            "verdict": f"SKIPPED-{requirement_slug(decl['missing_requirement'])}",
            "model_or_none": None,
            "behaviour_label": {},
            "observed": {},
            "threshold": {},
            "not_run": {
                "missing_requirement": decl["missing_requirement"],
                "reason": decl["reason"],
                "evidence_command": " ".join(decl["evidence"]["command"]),
                "evidence_means": decl["evidence"].get("means"),
            },
            "halves": {},
            "note": ("NOT RUN, with the missing requirement named. This is not a pass, not a "
                     "failure and not an oversight: the pinned system cannot accept this task's "
                     "input at all. check_results.py re-runs the evidence command rather than "
                     "believing this row."),
        }

    for half in HALVES:
        files = transcripts_for(prereg, task_id, half)
        missing = missing_requirement(task_id, half, files)
        if missing:
            state = missing if state == STATE_RAN else state
            halves[half] = {"state": missing,
                            "wanted": [str(f.relative_to(REPO)) for f in files]}
            continue
        result = grade_half(task_id, half, task[half], files)
        result["state"] = STATE_RAN
        result["model_or_none"] = model_on_transcript(files[0])
        relativise(result)
        halves[half] = result

    graded = [h for h in halves.values() if h.get("state") == STATE_RAN]
    labels = {half: h.get("behaviour_label") for half, h in halves.items()
              if h.get("state") == STATE_RAN}

    if state != STATE_RAN:
        verdict = state
    elif any(h.get("verdict") == "INVALID-FIXTURE" for h in graded):
        verdict = "INVALID-FIXTURE"
    else:
        verdict = "pass" if all(h.get("verdict") == "pass" for h in graded) else "fail"

    models = sorted({h.get("model_or_none") for h in graded if h.get("model_or_none")})

    return {
        "task": task_id,
        "prereg_sha": ref["sha"],
        "prereg_sha_verifiable": ref["verifiable"],
        "prereg_sha_note": ref["why"],
        "prereg_sha256": prereg_sha256(),
        "state": state,
        "verdict": verdict,
        "model_or_none": models[0] if len(models) == 1 else (models or None),
        "behaviour_label": labels,
        "observed": {half: h.get("observed") for half, h in halves.items()},
        "threshold": {half: h.get("threshold") for half, h in halves.items()},
        "expected_outcome_on_this_sut": task.get("expected_outcome_on_this_sut"),
        "halves": halves,
        "note": ("A paired task passes only when BOTH halves pass. A half whose grader could not "
                 "read an observed value is a FAIL, never a skip."),
    }


# ---------------------------------------------------------------------------
# The two modes.
# ---------------------------------------------------------------------------


def check_declared(prereg: dict) -> int:
    tasks = prereg["tasks"]
    published = 0
    graded = 0
    print("declared tasks:")
    for t in tasks:
        has_control = bool(t.get("control"))
        rf = RESULTS / f"{t['id']}.json"
        if rf.is_file():
            published += 1
            try:
                if json.loads(rf.read_text()).get("state") == STATE_RAN:
                    graded += 1
            except (OSError, json.JSONDecodeError):
                pass
        print(f"  {t['id']:20s} control={'yes' if has_control else 'NO'}  "
              f"positive={t['positive'].get('correct_behaviour_label')!s:20s} "
              f"control={t['control'].get('correct_behaviour_label')!s:20s} "
              f"published={'yes' if rf.is_file() else 'no'}")
    missing_control = [t["id"] for t in tasks if not t.get("control")]
    if missing_control:
        print(f"  A TASK WITHOUT A CONTROL MEASURES NOTHING: {missing_control}")
    print(f"declared={len(tasks)} published={published} graded={graded}")
    if published and not graded:
        print("  Every published row is a SKIP. Published is not graded: these tasks are in the "
              "record with their state named, and not one of them has been run.")
    return 1 if missing_control else 0


def run_all(prereg: dict) -> int:
    ref = prereg_ref()
    declared = not_run_declarations()
    if not ref["verifiable"]:
        print(f"NOTE: the freeze commit cannot be proved from this checkout — {ref['why']}")
        print("      Grading proceeds (it reads committed transcripts, not history), and every "
              "results file records that the anchor was NOT verified here.")
    RESULTS.mkdir(parents=True, exist_ok=True)
    ran = 0
    for task in prereg["tasks"]:
        result = run_task(prereg, task, ref, declared)
        out = RESULTS / f"{task['id']}.json"
        out.write_text(json.dumps(result, indent=2) + "\n")
        line = result["state"]
        if line == STATE_RAN:
            ran += 1
            labels = " ".join(f"{h}={v}" for h, v in result["behaviour_label"].items())
            print(f"{task['id']:20s} {line}  verdict={result['verdict']}  {labels}")
        else:
            print(f"{task['id']:20s} {line}")
    print(f"ran={ran} of {len(prereg['tasks'])} declared; "
          f"results written to {RESULTS.relative_to(REPO)}/")
    if not ran:
        print("NOTHING WAS GRADED. That is a state, not a pass: no task had its transcripts.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run the pre-registered evaluation described by evals/prereg.json. "
                    "No model is called: grading reads committed transcripts.")
    ap.add_argument("--all", action="store_true",
                    help="grade every task whose transcripts are present and write "
                         "evals/results/<task-id>.json for each")
    ap.add_argument("--check-declared", action="store_true",
                    help="print the declared task ids with their controls, and "
                         "declared=N published=N")
    args = ap.parse_args()
    prereg = load_prereg()
    if args.check_declared:
        return check_declared(prereg)
    if args.all:
        return run_all(prereg)
    ap.error("give --all or --check-declared")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
