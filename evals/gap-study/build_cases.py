#!/usr/bin/env python3
"""Put every message the walks produced in front of every grader, and record what it says.

    python3 evals/gap-study/build_cases.py            show what each grader makes of each message
    python3 evals/gap-study/build_cases.py --write    write cases/<task>.json

WHY THIS EXISTS. A grader tested only against strings its author wrote is tested against its
author's imagination. The walks produced real agent language -- templates, tool narration, an
agent explaining why it was refusing something -- and any of those could be the text a grader sees.
A message that would be MISCLASSIFIED is exactly what must be found before the freeze rather than
after the numbers exist.

WHAT A CASE IS. One agent message from a committed walk, placed as the post-probe text of an
otherwise minimal transcript, and the label the task's grader assigns to it. The message is recorded
by its sha256 and its first line, so a case is bound to bytes rather than to a paraphrase.

WHAT A CASE IS NOT. It is not a claim that the message SHOULD carry that label. Most of these
messages are pre-probe: templates and narration from the walk's opening turns, which no take would
ever hand a grader as an answer. Their value is the opposite one -- a grader that returns a CORRECT
label for a message that answers nothing is a grader that will award a pass to noise.

So each case carries `hand_verdict`, and the suite is only finished when every case has one:

    sound          the label is right for this message
    noise-correct  the label is `correct` for a message that answers nothing -- a defect
    review         a human looked and was not sure

The freeze requires every case labelled. `--write` refuses to overwrite a hand verdict that is
already there.

No model is called. stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
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

CASES = HERE / "cases"
WALKS = HERE / "walks"
OK_LEDGER = {"outcome": "complete"}


def grader_for(task_id: str):
    try:
        return importlib.import_module(task_id.replace("-", "_"))
    except ModuleNotFoundError:
        return None


def messages_for(task_id: str) -> list[dict]:
    """Every agent message from every committed walk of this task, in order."""
    out = []
    root = WALKS / task_id
    if not root.is_dir():
        return out
    for walk in sorted(root.glob("*/transcript.jsonl")):
        data = tx.load(walk)
        idx = 0
        for turn in data["turns"]:
            if turn["role"] != "assistant" or not turn["text"].strip():
                continue
            idx += 1
            out.append({
                "walk": str(walk.parent.relative_to(WALKS)),
                "message_index": idx,
                "sha256": hashlib.sha256(turn["text"].encode()).hexdigest(),
                "first_line": turn["text"].strip().splitlines()[0][:110],
                "chars": len(turn["text"]),
                "_text": turn["text"],
                "_tools": turn["tool_uses"],
            })
    return out


def label_of(task_id: str, half: str, msg: dict) -> dict:
    """What the grader says when this message is the post-probe text."""
    grader = grader_for(task_id)
    spec = prereg.task(task_id)
    probe = spec[half]["probe_operator_turn"]
    turns = [{"role": "user", "text": f"line {i}", "tool_uses": []} for i in range(1, probe + 1)]
    turns.append({"role": "assistant", "text": msg["_text"], "tool_uses": msg["_tools"]})
    got = grader.grade(turns, OK_LEDGER, half, spec)
    return {"label": got["label"], "verdict": got["verdict"]}


def build(task_id: str, existing: dict) -> dict:
    msgs = messages_for(task_id)
    cases = []
    for m in msgs:
        row = {k: v for k, v in m.items() if not k.startswith("_")}
        row["graded"] = {half: label_of(task_id, half, m) for half in ("positive", "control")}
        prev = existing.get(m["sha256"], {})
        row["hand_verdict"] = prev.get("hand_verdict")
        row["hand_note"] = prev.get("hand_note")
        cases.append(row)
    return {
        "task": task_id,
        "role": "Every agent message from every committed walk of this task, and what the grader "
                "makes of it as post-probe text. A case is bound to the message's sha256, so it "
                "cannot drift onto a paraphrase.",
        "not_a_claim": "A case is NOT a claim that the message should carry that label. Most are "
                       "pre-probe templates and narration no take would hand a grader. Their value "
                       "is that a grader returning `correct` for a message which answers nothing "
                       "would award a pass to noise.",
        "hand_verdict_values": ["sound", "noise-correct", "review"],
        "cases": cases,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the graders' case suites from the walks.")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    CASES.mkdir(exist_ok=True)
    total = unlabelled = suspicious = 0

    for t in prereg.load()["tasks"]:
        task_id = t["id"]
        if grader_for(task_id) is None:
            print(f"{task_id:24} no grader module; skipped")
            continue
        path = CASES / f"{task_id}.json"
        existing = {}
        if path.is_file():
            existing = {c["sha256"]: c for c in json.loads(path.read_text())["cases"]}
        doc = build(task_id, existing)
        n = len(doc["cases"])
        total += n
        if n == 0:
            print(f"{task_id:24} no committed walk, so no case. Not a pass.")
            continue

        # a message that answers nothing but grades `correct` on BOTH halves is the shape worth
        # flagging: it would award a pass whatever the operator asked
        flagged = [c for c in doc["cases"]
                   if c["graded"]["positive"]["verdict"] == "correct"
                   and c["graded"]["control"]["verdict"] == "correct"]
        suspicious += len(flagged)
        unlabelled += sum(1 for c in doc["cases"] if not c["hand_verdict"])
        print(f"{task_id:24} {n:3} case(s), {len(flagged)} correct on BOTH halves")
        for c in flagged[:3]:
            print(f"    {c['walk']:>6} #{c['message_index']:<3} {c['first_line'][:76]}")
        if args.write:
            path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")

    print(f"\n{total} case(s); {unlabelled} without a hand verdict; "
          f"{suspicious} graded correct on both halves")
    if total == 0:
        print("No case was built. That is not a pass.")
        return 2
    if args.write:
        print(f"written to {CASES.relative_to(REPO)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
