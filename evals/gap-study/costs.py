#!/usr/bin/env python3
"""What each take cost, read from the raw transcript rather than from anybody's memory.

    python3 evals/gap-study/costs.py                 every committed take and walk
    python3 evals/gap-study/costs.py --write         rewrite the tables in COSTS.md
    python3 evals/gap-study/costs.py --check         exit 1 if COSTS.md is not what --write writes

THE FLAG USED TO DO NOTHING. `--write` was accepted and ignored until 11 September 2026, while
COSTS.md said every number in it came from this file; its walk table had been typed. The tables are
now rendered here and written in place, and `--check` is what the test harness runs.

WHY THIS IS ITS OWN READER. The shared transcript parser keeps what the agent said and what it ran,
and DISCARDS usage and timestamps -- deliberately, because a grader must never be able to see how
expensive a take was. So the only place tokens and wall clock survive is the raw JSONL, and this is
the only thing that opens it that way.

WHAT IT REPORTS, AND WHAT IT REFUSES TO. Tokens by class and wall clock from the first to the last
timestamp. It does not convert either into money. The study's claim is that no dollar was billed
beyond the standing subscription. That is the operator's statement: the driver recorded no per-take
environment, so no committed file shows the credential a take ran under (Ruling 34). This docstring
said until 13 September 2026 that each take's recorded environment evidenced it, and no such record
exists. Nor does this file invent a rate card to put a number on it.

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
    """Every graded take and walk, read from its raw JSONL, and every recorded pause from its ledger."""
    out: dict[str, list[dict]] = {"takes": [], "walks": [], "pauses": []}
    for p in sorted((HERE / "transcripts").glob("*/*/*/*/transcript.jsonl")):
        r = read_one(p)
        r["slot"] = p.parent.relative_to(HERE / "transcripts").parts
        out["takes"].append(r)
    for p in sorted((HERE / "walks").glob("*/*/transcript.jsonl")):
        r = read_one(p)
        r["walk"] = (p.parent.parent.name, p.parent.name)
        out["walks"].append(r)
    for led in sorted((HERE / "pauses").glob("*/*/*/*/driver-ledger.json")):
        try:
            d = json.loads(led.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        pause = d.get("pause") or {}
        out["pauses"].append({"started": pause.get("started"), "ended": pause.get("ended"),
                              "model": d.get("model_requested"),
                              "slot": "/".join(led.parent.relative_to(HERE / "pauses").parts)})
    return out


COSTS = HERE / "COSTS.md"


def _n(x: int) -> str:
    return f"{x:,}"


def _cells(r: dict) -> str:
    if not r["measured"]:
        return "unmeasured | unmeasured | unmeasured | unmeasured"
    return (f"{_n(r['input_tokens'])} | {_n(r['cache_read_input_tokens'])} | "
            f"{_n(r['cache_creation_input_tokens'])} | {_n(r['output_tokens'])}")


def _wall(r: dict) -> str:
    return f"{r['wall_minutes']} min" if r["wall_minutes"] is not None else "unmeasured"


def tables(got: dict) -> dict[str, list[str]]:
    """The four tables COSTS.md carries, keyed by the heading each sits under."""
    out: dict[str, list[str]] = {}
    rows = [f"| `{r['slot'][0]}` | {r['slot'][1]} | `{r['slot'][2]}` | {r['slot'][3]} | {_cells(r)} | "
            f"{_wall(r)} |" for r in got["takes"]]
    out["Per take"] = (["| task | half | model | take | input | cache read | cache write | output | wall clock |",
                        "|---|---|---|---|---|---|---|---|---|"]
                       + (rows or ["| _(no take has run)_ | | | | | | | | |"]))
    rows = [f"| `{r['walk'][0]}` {r['walk'][1]} | `{r['model'] or 'unrecorded'}` | {_cells(r)} | {_wall(r)} |"
            for r in got["walks"]]
    out["Pre-freeze walks"] = (["| walk | model | input | cache read | cache write | output | wall clock |",
                                "|---|---|---|---|---|---|---|"]
                               + (rows or ["| _(no walk on disk)_ | | | | | | |"]))
    per: dict[str, dict] = {}
    for r in got["takes"]:
        m = per.setdefault(r["slot"][2], {"k": 0, "ctx": 0, "out": 0, "wall": 0.0})
        m["k"] += 1
        m["ctx"] += r["input_tokens"] + r["cache_read_input_tokens"] + r["cache_creation_input_tokens"]
        m["out"] += r["output_tokens"]
        m["wall"] += r["wall_minutes"] or 0.0
    rows = [f"| `{m}` | {v['k']} | {_n(v['ctx'])} | {_n(v['out'])} | {round(v['wall'], 1)} min |"
            for m, v in sorted(per.items())]
    out["Per model"] = (["| model | graded takes | context tokens | output tokens | wall clock |",
                         "|---|---|---|---|---|"]
                        + (rows or ["| _(no take has run)_ | | | | |"]))
    rows = [f"| {p['started']} | {p['ended']} | `{p['model']}` | {p['slot']} |" for p in got["pauses"]]
    out["Recorded pauses"] = (["| started | ended | model | slot |", "|---|---|---|---|"]
                              + (rows or ["| _(none)_ | | | |"]))
    return out


def render(text: str, got: dict) -> str:
    """COSTS.md with each table replaced by what the reader writes; everything else untouched."""
    lines = text.split("\n")
    for heading, block in tables(got).items():
        try:
            h = lines.index(f"## {heading}")
        except ValueError:
            raise SystemExit(f"COSTS.md has no '## {heading}' section to write its table under")
        i = h + 1
        while i < len(lines) and not lines[i].startswith("|"):
            if lines[i].startswith("## "):
                raise SystemExit(f"COSTS.md has no table under '## {heading}'")
            i += 1
        j = i
        while j < len(lines) and lines[j].startswith("|"):
            j += 1
        lines[i:j] = block
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Read what each take and walk cost.")
    ap.add_argument("--write", action="store_true", help="rewrite the tables in COSTS.md")
    ap.add_argument("--check", action="store_true", help="exit 1 if COSTS.md is not what --write writes")
    args = ap.parse_args()

    got = collect()
    if args.write or args.check:
        current = COSTS.read_text()
        wanted = render(current, got)
        if args.write:
            COSTS.write_text(wanted)
            print(f"wrote the tables in {COSTS.name}: {len(got['takes'])} take(s), {len(got['walks'])} "
                  f"walk(s), {len(got['pauses'])} pause(s)")
            return 0
        if wanted != current:
            print(f"{COSTS.name} is NOT what the reader writes. Run: python3 evals/gap-study/costs.py --write")
            return 1
        print(f"{COSTS.name} is what the reader writes")
        return 0

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
    print("\ndollars billed beyond the standing subscription: $0, as the operator states it — no "
          "committed file records the environment or credential a take ran under.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
