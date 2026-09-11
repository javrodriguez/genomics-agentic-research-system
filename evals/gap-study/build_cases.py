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


# `confounded-design` is carried from the first study. Its probe messages live in that study's
# committed transcripts, so its cases come from there; and since slice 39 it is walked HERE too, and
# requirement 1 puts every message from every committed walk transcript into the suite. So a carried
# task reads BOTH sources. The first version returned after the carried source, which would have
# left this study's own walks of the task out of its suite without a word.
CARRIED_SOURCES = {
    "confounded-design": REPO / "evals" / "transcripts",
}


def _messages(transcript: Path, walk_name: str) -> list[dict]:
    out = []
    data = tx.load(transcript)
    idx = 0
    for turn in data["turns"]:
        if turn["role"] != "assistant" or not turn["text"].strip():
            continue
        idx += 1
        out.append({
            "walk": walk_name,
            "message_index": idx,
            "sha256": hashlib.sha256(turn["text"].encode()).hexdigest(),
            "first_line": turn["text"].strip().splitlines()[0][:110],
            "chars": len(turn["text"]),
            "_text": turn["text"],
            "_tools": turn["tool_uses"],
        })
    return out


def messages_for(task_id: str) -> list[dict]:
    """Every agent message from every committed walk of this task, in order.

    For a carried task, the study it was carried from first, then this study's own walks.
    """
    out: list[dict] = []
    carried = CARRIED_SOURCES.get(task_id)
    if carried and carried.is_dir():
        for t in sorted(carried.rglob("transcript.jsonl")):
            out += _messages(t, "first-study/" + str(t.parent.relative_to(carried)))
    root = WALKS / task_id
    if root.is_dir():
        for walk in sorted(root.glob("*/transcript.jsonl")):
            out += _messages(walk, str(walk.parent.relative_to(WALKS)))
    return out

def label_of(task_id: str, half: str, msg: dict) -> dict:
    """What the grader says when this message is the text it reads.

    THE PADDING IS NOT COSMETIC, AND THE FIRST VERSION GOT IT WRONG. Two reach conventions are in
    play. The five graders written here read from the PROBE OPERATOR TURN -- an index into the
    operator's lines. The carried grader reads from a RAW TURN INDEX into the normalised transcript,
    which is what the first study fixed and what this study must not restate.

    The first version padded to the probe turn only. For the carried task that produced a transcript
    shorter than its reach turn, so the grader read an empty string and every one of its 59 cases
    came back `did-not-reach`. Fifty-nine cases measuring nothing, reported as a suite.

    The transcript is now padded past BOTH, so the message is the text the grader reads whichever
    convention that grader uses.
    """
    grader = grader_for(task_id)
    spec = prereg.task(task_id)
    probe = spec[half].get("probe_operator_turn") or 1
    reach = spec[half].get("reach_turn") or 1
    pad = max(int(probe), int(reach))
    # The REAL script lines, because the graders locate the probe by matching its text. Placeholder
    # lines made every case unfindable and the whole suite report did-not-reach.
    script = spec[half].get("operator_script")
    lines = []
    if isinstance(script, list):
        for step in script:
            lines.append(step.get("line") or "")
    while len(lines) < pad:
        lines.append(f"line {len(lines) + 1}")
    turns = [{"role": "user", "text": ln, "tool_uses": []} for ln in lines[:pad]]
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
