#!/usr/bin/env python3
"""Every harness denial in every graded take, read from the transcripts by code, for the result to print beside each take.

    python3 evals/gap-study-3/denials.py --check      list per graded take the calls the harness denied, commands quoted
    python3 evals/gap-study-3/denials.py --replay <transcript>

WHY (review 2, blocker 2). The pre-registration says a denial of a command the allowlist does not admit is a
condition of the harness, published as such with the denied command quoted, and that a take's denials are
printed beside it. Until this file nothing pinned read one: a take whose route met a denial and stopped short
of the probe would have published `did-not-reach` -- a reading of the model -- with nothing beside it saying
the harness refused a command. That is the shape the pre-study found in round 2 and the reason this round
exists, and result.py is pinned at the freeze, so the reader had to exist before it.

WHAT IT READS. The harness writes its refusal into the tool result itself, opening with the sentence pinned
below (Claude Code 2.1.267, the version this study froze). Each tool call whose result carries it is a
denial, and the call's own input is carried beside the text, because a `harness denial` is the one reading
whose meaning depends on WHICH command was denied. The transcript is parsed by the shared parser, never
searched as text, so the sentence is only ever read out of a tool result.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "evals"))
sys.path.insert(0, str(HERE))

import transcript as tx  # noqa: E402

# The first words of the harness's own denial, as Claude Code 2.1.267 writes them into the tool result.
DENIAL_SENTENCE = "Permission for this tool use was denied"


def denials_in(transcript: Path) -> list[dict]:
    """Every denied tool call in this transcript, in order: the tool, the command, and the refusal's own text."""
    out = []
    for turn in tx.parse(transcript):
        for u in turn.get("tool_uses") or []:
            text = u.get("stdout") or ""
            if DENIAL_SENTENCE in text:
                inp = u.get("input") or {}
                out.append({"tool": u.get("name"), "command": inp.get("command") or inp.get("file_path") or "",
                            "text": text.strip()})
    return out


def graded_transcripts() -> list[Path]:
    base = HERE / "transcripts"
    return sorted(base.glob("*/*/*/*/transcript.jsonl")) if base.is_dir() else []


def per_take() -> list[dict]:
    """One row per graded take: where it sits, how many calls were denied, and the commands, quoted."""
    rows = []
    for t in graded_transcripts():
        task, half, model, take = t.parts[-5], t.parts[-4], t.parts[-3], t.parts[-2]
        d = denials_in(t)
        rows.append({"task": task, "half": half, "model": model, "take": take,
                     "denied": len(d), "commands": [x["command"] for x in d]})
    return rows


def per_cell() -> dict[tuple[str, str, str], dict]:
    """Per (task, half, model): the count of denied calls over its graded takes, and the commands."""
    out: dict[tuple[str, str, str], dict] = {}
    for r in per_take():
        cell = out.setdefault((r["task"], r["half"], r["model"]), {"denied": 0, "commands": []})
        cell["denied"] += r["denied"]
        cell["commands"] += r["commands"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--replay", type=Path, metavar="TRANSCRIPT")
    args = ap.parse_args()
    if args.replay:
        rec = denials_in(args.replay)
        print(json.dumps(rec, indent=2))
        print(f"{len(rec)} denied call(s)")
        return 0
    rows = per_take()
    if not rows:
        # An empty gate is said out loud, never logged as a pass.
        print("ok, having read 0 graded takes: none is committed yet, so nothing here is evidence about any "
              "denial. Not a pass.")
        return 0
    for r in rows:
        where = f"{r['task']}/{r['half']}/{r['model']}/{r['take']}"
        if r["denied"]:
            print(f"  {where}: {r['denied']} denied call(s): " + "; ".join(f"`{c}`" for c in r["commands"]))
        else:
            print(f"  {where}: no denial")
    hit = sum(1 for r in rows if r["denied"])
    print(f"ok: {len(rows)} graded take(s) read; {hit} carry a denial, each printed with its commands quoted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
