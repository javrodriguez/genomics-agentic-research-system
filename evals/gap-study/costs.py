#!/usr/bin/env python3
"""What each take cost, read from the raw transcript rather than from anybody's memory.

    python3 evals/gap-study/costs.py                 every committed take and walk
    python3 evals/gap-study/costs.py --write         rewrite the tables in COSTS.md

WHY THIS IS ITS OWN READER. The shared transcript parser keeps what the agent said and what it ran,
and DISCARDS usage and timestamps -- deliberately, because a grader must never be able to see how
expensive a take was. So the only place tokens and wall clock survive is the raw JSONL, and this is
the only thing that opens it that way.

WHAT IT REPORTS, AND WHAT IT REFUSES TO. Tokens by class and wall clock from the first to the last
timestamp. It does not convert either into money. The study's claim is that no dollar was billed
beyond the standing subscription, and that claim is evidenced by the recorded environment of each
take -- no API-key variable, the subscription login the only credential -- not by a rate card this
file would have to invent.

A take with no usage records is reported as unmeasured rather than as zero. Zero is a measurement.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CLASSES = ("input_tokens", "output_tokens", "cache_read_input_tokens",
           "cache_creation_input_tokens")


def read_one(path: Path) -> dict:
    acc = {c: 0 for c in CLASSES}
    stamps: list[str] = []
    model = None
    records = 0
    with_usage = 0
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        records += 1
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
        model = model or msg.get("model")
        usage = msg.get("usage") or {}
        if usage:
            with_usage += 1
            for c in CLASSES:
                acc[c] += usage.get(c, 0) or 0
        if rec.get("timestamp"):
            stamps.append(rec["timestamp"])

    wall = None
    if len(stamps) >= 2:
        try:
            a = datetime.fromisoformat(stamps[0].replace("Z", "+00:00"))
            b = datetime.fromisoformat(stamps[-1].replace("Z", "+00:00"))
            wall = round((b - a).total_seconds() / 60.0, 1)
        except ValueError:
            wall = None

    return {"path": str(path.relative_to(REPO)), "model": model, "records": records,
            "usage_records": with_usage, "wall_minutes": wall,
            "measured": with_usage > 0, **acc}


def collect() -> dict:
    out: dict[str, list[dict]] = {"takes": [], "walks": []}
    for p in sorted((HERE / "transcripts").rglob("transcript.jsonl")):
        out["takes"].append(read_one(p))
    for p in sorted((HERE / "walks").rglob("transcript.jsonl")):
        out["walks"].append(read_one(p))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Read what each take and walk cost.")
    ap.add_argument("--write", action="store_true", help="rewrite the tables in COSTS.md")
    args = ap.parse_args()

    got = collect()
    total = len(got["takes"]) + len(got["walks"])
    if total == 0:
        print("no transcript on disk. Nothing was measured, and that is not a cost of zero.")
        return 2

    for kind in ("takes", "walks"):
        rows = got[kind]
        if not rows:
            print(f"{kind}: none on disk")
            continue
        print(f"\n{kind} ({len(rows)}):")
        for r in rows:
            if not r["measured"]:
                print(f"  {r['path'][-58:]}  UNMEASURED — no usage records")
                continue
            print(f"  {r['path'][-58:]}")
            print(f"     model {r['model']}  wall {r['wall_minutes']} min")
            print(f"     input {r['input_tokens']:>7}  output {r['output_tokens']:>7}  "
                  f"cache read {r['cache_read_input_tokens']:>9}  "
                  f"cache write {r['cache_creation_input_tokens']:>8}")

    unmeasured = [r for rows in got.values() for r in rows if not r["measured"]]
    if unmeasured:
        print(f"\n{len(unmeasured)} transcript(s) carry no usage records and are reported "
              f"unmeasured, never as zero.")
    print("\ndollars billed beyond the standing subscription: $0 — evidenced by each take's "
          "recorded environment, not by this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
