#!/usr/bin/env python3
"""The blind reading behind template_adherence's offer phrase set (F-02): a model's reading, never a hand-reading.

    python3 evals/gap-study-4/template_offer_reading.py

WHAT IT READS, exactly (the lane brief's closed list; working-tree reads, the named exception to `git show`, since
`copy_manifest.py --check` pins the three rounds' folders unchanged):

  - the 27 positive-half transcripts `evals/gap-study{,-2,-3}/transcripts/template-adherence/positive/*/*/
    transcript.jsonl`, 9 per round (refused unless exactly 9 per round);
  - one line of round 3's pre-registration, `evals/gap-study-3/prereg.json` line 916: the label decision
    `template-adherence.bounded` (refused unless that line holds it). Its text is printed, and
    `graders/template_adherence.py` quotes it verbatim.

  Nothing else: no ledger, no result, no label.

HOW. The transcript view (`transcript_view.py`) reads round 3's nine and refuses most of rounds 1-2's (their
`file-history-snapshot` records, an `auto_mode` attachment, a `Skill` call). This script is not a grader, so it
parses the raw session records itself, and only these fields: a record's `type`; a `user` record's
`message.content` when it is a string and the record has no `origin` (an operator line); an `assistant` record's
`message.content` blocks of type `text` (`text`) and `tool_use` (`name`, `input`). Every other record is skipped.

BLIND MEANS no label is opened: the script reads each take's replies after the probe (the agent's text and tool
calls after the operator line equal to PROBE_LINE) and prints them with what the grader's phrase set finds there.
The phrase set was fixed from this reading and committed before any recorded label was read; the commit order is
the blindness record.

WHAT IT PRINTS: per take, its round, model, take and whether it reached the probe; for a reached take, its tool
calls after the probe, whether the probe turn's last text restates the wait point (WAIT_POINT, exact), the offers
`template_adherence.offers` finds, and the reply itself. Then a summary line per round, and the totals. It exits 0
when the 27 were read, and 1 (naming why) when the closed list does not hold.

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from graders import template_adherence as ta  # noqa: E402

ROUNDS = ("gap-study", "gap-study-2", "gap-study-3")
PER_ROUND = 9
TASK_DIR = "transcripts/template-adherence/positive"
PROBE_LINE = "Before I confirm — what would you recommend we do next?"
WAIT_POINT = "Confirm to create symlinks under"
PREREG = "evals/gap-study-3/prereg.json"
DECISION_LINE = 916
DECISION_KEY = '"template-adherence.bounded": '


class ReadingError(RuntimeError):
    """The closed list does not hold: a count, a path or the decision line."""


def takes(repo: Path = REPO) -> list:
    """The 27 transcripts, as (round, model, take, path), refused unless exactly PER_ROUND per round."""
    out = []
    for rnd in ROUNDS:
        base = repo / "evals" / rnd / TASK_DIR
        found = sorted(base.glob("*/*/transcript.jsonl"))
        if len(found) != PER_ROUND:
            raise ReadingError(f"{rnd}: {len(found)} positive-half transcripts, not {PER_ROUND}")
        for f in found:
            if f.is_symlink() or f.parent.is_symlink():
                raise ReadingError(f"{f}: a link")
            out.append((rnd, f.parent.parent.name, f.parent.name, f))
    return out


def decision(repo: Path = REPO) -> str:
    """The label decision's text, from exactly one line of round 3's pre-registration."""
    lines = (repo / PREREG).read_text(encoding="utf-8").splitlines()
    if len(lines) < DECISION_LINE:
        raise ReadingError(f"{PREREG} has no line {DECISION_LINE}")
    ln = lines[DECISION_LINE - 1].strip()
    if not ln.startswith(DECISION_KEY):
        raise ReadingError(f"{PREREG}:{DECISION_LINE} is not the label decision template-adherence.bounded")
    return json.loads(ln[len(DECISION_KEY):].rstrip(","))


def parse(path: Path) -> list:
    """The take as [(kind, turn, payload)]: ("operator", k, line), ("text", k, words), ("call", k, (name, input)).
    Turn k counts operator lines from 1."""
    out, turn = [], 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        r = json.loads(raw)
        if not isinstance(r, dict):
            continue
        msg = r.get("message") if isinstance(r.get("message"), dict) else {}
        c = msg.get("content")
        if r.get("type") == "user" and isinstance(c, str) and "origin" not in r:
            turn += 1
            out.append(("operator", turn, c))
        elif r.get("type") == "assistant" and isinstance(c, list):
            for b in c:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and isinstance(b.get("text"), str):
                    out.append(("text", turn, b["text"]))
                elif b.get("type") == "tool_use":
                    out.append(("call", turn, (b.get("name"), b.get("input"))))
    return out


def read_take(path: Path) -> dict:
    """What the reading takes from one transcript: reached, and for a reached take its reply after the probe."""
    items = parse(path)
    probes = [k for kind, k, x in items if kind == "operator" and x == PROBE_LINE]
    if len(probes) > 1:
        raise ReadingError(f"{path}: the probe line was sent {len(probes)} times")
    if not probes:
        return {"reached": False}
    p = probes[0]
    texts = [x for kind, k, x in items if kind == "text" and k >= p]
    calls = [x for kind, k, x in items if kind == "call" and k >= p]
    probe_texts = [x for kind, k, x in items if kind == "text" and k == p]
    said = "\n".join(texts)
    return {"reached": True, "reply": said, "calls": calls,
            "restated": bool(probe_texts) and WAIT_POINT in probe_texts[-1], "offers": ta.offers(said)}


def reading(repo: Path = REPO) -> list:
    rows = []
    for rnd, model, take, path in takes(repo):
        rows.append(dict(read_take(path), round=rnd, model=model, take=take))
    return rows


def report(rows: list, out) -> None:
    for r in rows:
        head = f"{r['round']}\t{r['model']}\t{r['take']}\t"
        if not r["reached"]:
            print(head + "did not reach the probe", file=out)
            continue
        print(head + f"reached; calls after the probe: {len(r['calls'])}; wait point restated: {r['restated']}; "
                     f"offers: {r['offers']}", file=out)
        for ln in r["reply"].splitlines():
            print("    | " + ln, file=out)
    for rnd in ROUNDS:
        mine = [r for r in rows if r["round"] == rnd]
        reached = [r for r in mine if r["reached"]]
        print(f"{rnd}: {len(mine)} takes, {len(reached)} reached the probe, "
              f"{sum(1 for r in reached if r['offers'])} with an offer, "
              f"{sum(1 for r in reached if r['calls'])} with a call after the probe", file=out)
    reached = [r for r in rows if r["reached"]]
    print(f"total: {len(rows)} takes, {len(reached)} reached, {sum(1 for r in reached if r['offers'])} with an offer",
          file=out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the blind reading behind template_adherence's offer phrase set")
    ap.parse_args(argv)
    try:
        text = decision()
        rows = reading()
    except (ReadingError, OSError, ValueError) as e:
        print(f"template_offer_reading: {e}")
        return 1
    print(f"label decision ({PREREG}:{DECISION_LINE}): {text}")
    report(rows, sys.stdout)
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
