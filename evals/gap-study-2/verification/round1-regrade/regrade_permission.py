#!/usr/bin/env python3
"""What round 2's permission reading makes of round 1's stopped takes, written as a record that re-derives.

    python3 evals/gap-study-2/verification/round1-regrade/regrade_permission.py            print the reading
    python3 evals/gap-study-2/verification/round1-regrade/regrade_permission.py --write    write permission-stop.json
    python3 evals/gap-study-2/verification/round1-regrade/regrade_permission.py --check    exit 1 unless the
                                                                                           committed record is
                                                                                           what this re-derives

WHY IT EXISTS (round 2, CP4, fix 3). Round 1 published every take its driver stopped at an unheld marker as
`did-not-reach`, and reading its transcripts showed that most of `claude-haiku-4-5-20251001`'s stops ended on a
request for permission to run or proceed. Round 2 gives that stop a reserved label of its own, `asked-to-proceed`,
decided by labels.reserved over the take's final agent message. Run over round 1's committed stopped takes, this
records the label round 1 published beside the label round 2's reading gives, with the report-only group counted
(Javier's ruling J3) and not counted, so the ruling's effect is a number rather than a claim. It is a reading of
the round-2 instrument on round-1 bytes, never a re-grade of round 1's result, and the record opens by saying so.

WHAT IT CALLS, AND NOTHING ELSE. graders/labels.py (mark_harness_records, harness_record_flags, reserved,
permission_phrases_in, final_agent_message), loaded by path, and the first study's shared transcript parser that
run.py grades with. Round 1's takes are read from its committed ledger, results files and transcripts, as data,
through study.ROUND1; nothing there is imported or written.

WHAT THE RECORD NEVER CARRIES. No agent text: each take's final message is named by its sha256 and the phrases
found in it. The write is refused (exit 2) if the rendered text names this checkout, the home folder or a
temporary folder.

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

import study  # noqa: E402

RECORD = HERE / "permission-stop.json"
RECORD_SENTENCE = "what the round-2 permission reading makes of round 1's stopped takes — not round 1's result"


def _load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def instruments():
    """Round 2's labels.py and the shared parser run.py grades with, each loaded by path."""
    labels = _load_by_path("gap_study_2_regrade_labels", STUDY_DIR / "graders" / "labels.py")
    tx = _load_by_path("gap_study_2_regrade_transcript", study.REPO / "evals" / "transcript.py")
    return labels, tx


def round_one_stopped_takes() -> list[dict]:
    """Round 1's graded takes whose driver recorded a stop, in a fixed order; exit 2 if any record is absent."""
    try:
        rows = json.loads((study.ROUND1 / "takes.json").read_text())["rows"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise SystemExit(f"round 1's takes.json cannot be read ({type(exc).__name__}); nothing was measured")
    out = []
    for r in rows:
        folder = study.ROUND1 / "transcripts" / r["task"] / r["half"] / r["model"] / str(r["take"])
        try:
            ledger = json.loads((folder / "driver-ledger.json").read_text())
        except (OSError, json.JSONDecodeError):
            raise SystemExit(f"round 1's ledger lists a take with no readable driver ledger "
                             f"({r['task']} {r['half']} {r['model']} take {r['take']}); the reading would not "
                             f"cover what it names")
        if not (folder / "transcript.jsonl").is_file():
            raise SystemExit(f"a round-1 take has no committed transcript ({r['task']} {r['half']} {r['model']} "
                             f"take {r['take']}); the reading would not cover what it names")
        if str(ledger.get("outcome") or "").startswith("stopped"):
            out.append({"task": r["task"], "half": r["half"], "model": r["model"], "take": int(r["take"]),
                        "dir": folder, "ledger": ledger})
    out.sort(key=lambda t: (t["task"], t["half"], t["model"], t["take"]))
    if not out:
        raise SystemExit("round 1's ledger names no stopped take; the reading would measure nothing")
    return out


def round_one_label(task: str, half: str, model: str, take: int) -> str:
    """The label round 1 published for this take, from its committed results file."""
    doc = json.loads((study.ROUND1 / "results" / f"{task}.json").read_text())
    for lab in doc["cells"][model][half]["labels"]:
        if str(lab["take"]) == str(take):
            return lab["label"]
    raise SystemExit(f"round 1's results file for {task} has no label for {half} {model} take {take}")


def derive() -> dict:
    labels, tx = instruments()
    rows = []
    counts: dict[str, collections.Counter] = {}
    for t in round_one_stopped_takes():
        path = t["dir"] / "transcript.jsonl"
        turns = labels.mark_harness_records(tx.load(path)["turns"], labels.harness_record_flags(path))
        final = labels.final_agent_message(turns)
        with_ro = labels.reserved(t["ledger"], turns, True)
        without_ro = labels.reserved(t["ledger"], turns, False)
        rows.append({
            "task": t["task"], "half": t["half"], "model": t["model"], "take": t["take"],
            "round_1_label": round_one_label(t["task"], t["half"], t["model"], t["take"]),
            "round_2_label": with_ro,
            "round_2_label_report_only_not_counted": without_ro,
            "final_message_sha256": hashlib.sha256(final.encode()).hexdigest(),
            "phrases": labels.permission_phrases_in(final, True),
        })
        c = counts.setdefault(t["model"], collections.Counter())
        c["stopped"] += 1
        c["round_1_did_not_reach"] += rows[-1]["round_1_label"] == labels.DID_NOT_REACH
        c["asked_to_proceed"] += with_ro == labels.ASKED_TO_PROCEED
        c["did_not_reach"] += with_ro == labels.DID_NOT_REACH
        c["asked_to_proceed_report_only_not_counted"] += without_ro == labels.ASKED_TO_PROCEED
        c["did_not_reach_report_only_not_counted"] += without_ro == labels.DID_NOT_REACH

    keys = ("stopped", "round_1_did_not_reach", "asked_to_proceed", "did_not_reach",
            "asked_to_proceed_report_only_not_counted", "did_not_reach_report_only_not_counted")
    return {
        "record": RECORD_SENTENCE,
        "instrument": {
            "reader": study.rel("graders", "labels.py") + " reserved(driver ledger, turns, report_only_counts) over "
                      "turns marked by mark_harness_records",
            "parser": "evals/transcript.py load, as run.py grades",
            "script": study.rel("verification", "round1-regrade", "regrade_permission.py"),
            "report_only_counts_in_force": labels.REPORT_ONLY_COUNTS,
            "ruling": "J3, 13 September 2026: the report-only group counts",
            "round_1_takes": study.ROUND1_REL + "/takes.json",
            "round_1_labels": study.ROUND1_REL + "/results/<task>.json",
            "round_1_transcripts": study.ROUND1_REL + "/transcripts/<task>/<half>/<model>/<take>/",
        },
        "takes": rows,
        "counts_by_model": {m: {k: c.get(k, 0) for k in keys} for m, c in sorted(counts.items())},
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
    parts = []
    for m, c in record["counts_by_model"].items():
        parts.append(f"{m}: {c['stopped']} stopped, {c['asked_to_proceed']} asked-to-proceed and "
                     f"{c['did_not_reach']} did-not-reach ({c['asked_to_proceed_report_only_not_counted']} and "
                     f"{c['did_not_reach_report_only_not_counted']} without the report-only group)")
    return "; ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="Read round 1's stopped takes with round 2's permission reading.")
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
              f"{study.rel('verification', 'round1-regrade', 'regrade_permission.py')} --write")
        return 1
    print(summary(record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
