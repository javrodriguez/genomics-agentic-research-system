#!/usr/bin/env python3
"""What round 2's plan-gate grader makes of round 1's plan-gate takes, written as a record that re-derives.

    python3 evals/gap-study-2/verification/round1-regrade/regrade_plan_gate.py            print the reading
    python3 evals/gap-study-2/verification/round1-regrade/regrade_plan_gate.py --write    write plan-gate.json
    python3 evals/gap-study-2/verification/round1-regrade/regrade_plan_gate.py --check    exit 1 unless the
                                                                                           committed record is
                                                                                           what this re-derives

WHY IT EXISTS (round 2, CP6, J1). Round 1's plan-gate grader read an approve only when the subcommand followed
the script's name with nothing but spaces between, so round 1's control claude-opus-5 take 2, which ran the script
with `--workspace` before `approve` after the operator's yes and was stamped APPROVED, was labelled `held`. Round 2
reads the command as tokens. Run over round 1's 18 committed plan-gate takes, this records the label round 1
published beside the label round 2's grader gives, for both halves. It is never a re-grade of round 1's result, and
the record opens by saying so.

WHAT IT CALLS, AND NOTHING ELSE. graders/plan_gate.py `grade`, loaded by path with graders/labels.py beside it,
over the turns the shared parser returns with harness records flagged, against the plan-gate task of round 2's
pre-registration in force. Round 1's takes are read from its committed ledger, results files and transcripts, as
data, through study.ROUND1.

WHAT THE RECORD NEVER CARRIES. No agent text: each take's reply after the probe is named by its sha256, beside
the grader's evidence lines. The write is refused (exit 2) if the rendered text names this checkout, the home
folder or a temporary folder.

Exit 0 as stated, 1 when --check finds a difference, 2 when round 1's takes cannot be read or the record would
carry a machine path. stdlib only, no model, no network.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_DIR = HERE.parent.parent
sys.path.insert(0, str(STUDY_DIR))
sys.path.insert(0, str(STUDY_DIR / "graders"))

import prereg  # noqa: E402
import study  # noqa: E402

RECORD = HERE / "plan-gate.json"
RECORD_SENTENCE = "what the round-2 plan-gate grader makes of round 1's plan-gate takes — not round 1's result"
TASK = "plan-gate"


def _load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def round_one_takes() -> list[dict]:
    try:
        rows = json.loads((study.ROUND1 / "takes.json").read_text())["rows"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise SystemExit(f"round 1's takes.json cannot be read ({type(exc).__name__}); nothing was measured")
    out = []
    for r in rows:
        if r["task"] != TASK:
            continue
        folder = study.ROUND1 / "transcripts" / r["task"] / r["half"] / r["model"] / str(r["take"])
        if not (folder / "transcript.jsonl").is_file() or not (folder / "driver-ledger.json").is_file():
            raise SystemExit(f"a round-1 plan-gate take has no committed transcript or ledger ({r['half']} "
                             f"{r['model']} take {r['take']}); the reading would not cover what it names")
        out.append({"half": r["half"], "model": r["model"], "take": int(r["take"]), "dir": folder})
    out.sort(key=lambda t: (t["half"], t["model"], t["take"]))
    if not out:
        raise SystemExit("round 1's ledger names no plan-gate take; the reading would measure nothing")
    return out


def round_one_label(half: str, model: str, take: int) -> str:
    doc = json.loads((study.ROUND1 / "results" / f"{TASK}.json").read_text())
    for lab in doc["cells"][model][half]["labels"]:
        if str(lab["take"]) == str(take):
            return lab["label"]
    raise SystemExit(f"round 1's plan-gate results file has no label for {half} {model} take {take}")


def derive() -> dict:
    import labels
    grader = _load_by_path("gap_study_2_regrade_plan_gate", STUDY_DIR / "graders" / "plan_gate.py")
    tx = _load_by_path("gap_study_2_regrade_transcript", study.REPO / "evals" / "transcript.py")
    spec = prereg.task(TASK)
    rows = []
    counts: dict[str, collections.Counter] = {}
    for t in round_one_takes():
        path = t["dir"] / "transcript.jsonl"
        ledger = json.loads((t["dir"] / "driver-ledger.json").read_text())
        turns = labels.mark_harness_records(tx.load(path)["turns"], labels.harness_record_flags(path))
        said, _ = labels.text_after_probe(turns, spec[t["half"]])
        got = grader.grade(turns, ledger, t["half"], spec)
        r1 = round_one_label(t["half"], t["model"], t["take"])
        rows.append({"half": t["half"], "model": t["model"], "take": t["take"], "round_1_label": r1,
                     "round_2_label": got["label"], "round_2_verdict": got["verdict"],
                     "reply_after_probe_sha256": hashlib.sha256(said.encode()).hexdigest(),
                     "evidence": got["evidence"]})
        c = counts.setdefault(f"{t['half']} {t['model']}", collections.Counter())
        c[f"round 1 {r1}"] += 1
        c[f"round 2 {got['label']}"] += 1
    return {
        "record": RECORD_SENTENCE,
        "instrument": {
            "grader": study.rel("graders", "plan_gate.py") + " grade, over turns marked by labels.mark_harness_records",
            "parser": "evals/transcript.py load, as run.py grades",
            "rule": "plan_gate.approve_invoked, the approve detection J1 names",
            "script": study.rel("verification", "round1-regrade", "regrade_plan_gate.py"),
            "round_1_takes": study.ROUND1_REL + "/takes.json",
            "round_1_labels": study.ROUND1_REL + "/results/plan-gate.json",
            "round_1_transcripts": study.ROUND1_REL + "/transcripts/plan-gate/<half>/<model>/<take>/",
        },
        "takes": rows,
        "counts": {k: dict(sorted(v.items())) for k, v in sorted(counts.items())},
        # The approve detection changes only a take that ran an approve the old pattern missed. The one other difference
        # is CP4's: a stop round 1 published as did-not-reach whose final message asks permission is asked-to-proceed.
        "changed_takes": [{k: r[k] for k in ("half", "model", "take", "round_1_label", "round_2_label")} for r in rows
                          if r["round_1_label"] != r["round_2_label"]
                          and not (r["round_1_label"] == "did-not-reach" and r["round_2_label"] == "asked-to-proceed")],
    }


def render(record: dict) -> str:
    return json.dumps(record, indent=2, ensure_ascii=False) + "\n"


def machine_paths(text: str) -> list[str]:
    temp = Path(tempfile.gettempdir())
    probes = {"this checkout": str(study.REPO), "the home folder": str(Path.home()),
              "the folder above the home folder": str(Path.home().parent) + os.sep,
              "the temporary folder": str(temp), "the temporary folder, resolved": str(temp.resolve())}
    return [label for label, needle in probes.items() if len(needle) > 1 and needle in text]


def summary(record: dict) -> str:
    return "; ".join(f"{k}: {', '.join(f'{n} {lab}' for lab, n in v.items())}" for k, v in record["counts"].items()) + \
        f"; changed beyond the permission label: {[(c['half'], c['model'], c['take'], c['round_1_label'] + ' to ' + c['round_2_label']) for c in record['changed_takes']]}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Read round 1's plan-gate takes with round 2's grader.")
    ap.add_argument("--write", action="store_true", help="write the record")
    ap.add_argument("--check", action="store_true", help="exit 1 unless the record is what this re-derives")
    ap.add_argument("--record", type=Path, default=RECORD, help="the record --check compares")
    args = ap.parse_args()

    record = derive()
    text = render(record)
    leaked = machine_paths(text)
    if leaked:
        print(f"REFUSING: the reading names {', '.join(leaked)}; nothing was written and nothing compared")
        return 2
    if args.write:
        RECORD.write_text(text)
        print(f"wrote {RECORD.name}: {summary(record)}")
        return 0
    if args.check:
        try:
            committed = args.record.read_text()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"{args.record.name} cannot be read ({type(exc).__name__}); nothing matches the re-derivation")
            return 1
        if committed == text:
            print(f"{args.record.name} is what the regrade re-derives: {summary(record)}")
            return 0
        old, new = committed.splitlines(), text.splitlines()
        at = next((i for i, (a, b) in enumerate(zip(old, new)) if a != b), min(len(old), len(new)))
        print(f"{args.record.name} is NOT what the regrade re-derives: first difference at line {at + 1} "
              f"({len(old)} committed line(s), {len(new)} re-derived). Run: python3 "
              f"{study.rel('verification', 'round1-regrade', 'regrade_plan_gate.py')} --write")
        return 1
    print(summary(record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
