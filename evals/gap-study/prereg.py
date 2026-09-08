#!/usr/bin/env python3
"""The one door to the pre-registration. Every other module reads the study's design through here.

    python3 evals/gap-study/prereg.py --status        which file is in force, and whether it is frozen
    python3 evals/gap-study/prereg.py --task <id>     one task's design
    python3 evals/gap-study/prereg.py --order <sha>   the take order this seed produces

WHY A LOADER RATHER THAN json.load IN EACH FILE. The first study dispatched graders by a hard-coded
id chain and kept each take's checks as module constants, so the definitions that decide a verdict
lived in the code rather than in the frozen file. Nothing was wrong with the answers; the problem is
that a stranger could not grade a cell from the frozen file alone, which is the thing criterion 6
asks for. Here the operator script, the leak words, the reach turn, the labels, the layout and the
model list are DATA. This module is the only thing that opens them.

THE DRAFT AND THE FROZEN FILE ARE NOT INTERCHANGEABLE, AND THIS IS WHERE THAT IS ENFORCED. Before
the freeze the design lives in prereg-draft.json and is expected to change -- that is what the walks
are for. After the freeze it lives in prereg.json and may not. A run that graded a take against a
draft would have published a number chosen after the fact without anybody lying.

So: prereg.json wins whenever it exists, the loader says which file it read every time it is asked
in anger, and `require_frozen()` is called by everything that produces a number. There is no flag
that lets a grading path read the draft.

THE TAKE ORDER IS A FUNCTION, NOT A LIST. It is one permutation per axis over every (task, half,
model, take), seeded by the sha of the pre-freeze review commit -- a sha that does not exist until
the review has happened, so the order cannot have been chosen to suit a result. Anyone can
recompute it from the seed with `--order <sha>`.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRAFT = HERE / "prereg-draft.json"
FROZEN = HERE / "prereg.json"

_cache: dict | None = None


def in_force() -> Path:
    """The frozen file if it exists, else the draft. Never both."""
    return FROZEN if FROZEN.is_file() else DRAFT


def is_frozen() -> bool:
    return FROZEN.is_file()


def load() -> dict:
    global _cache
    if _cache is None:
        path = in_force()
        if not path.is_file():
            raise SystemExit(
                "no pre-registration: neither prereg.json nor prereg-draft.json exists. "
                "Nothing in this study can be read without it.")
        _cache = json.loads(path.read_text())
        _cache["_source"] = path.name
        _cache["_frozen"] = path is FROZEN
    return _cache


def require_frozen(what: str) -> dict:
    """Called by anything that produces a published number."""
    pre = load()
    if not pre["_frozen"]:
        raise SystemExit(
            f"{what} needs a FROZEN pre-registration and found {pre['_source']}. A number graded "
            f"against a file that can still change was not pre-registered, whatever the file says. "
            f"Freeze the design first.")
    return pre


def task(task_id: str) -> dict:
    for t in load()["tasks"]:
        if t["id"] == task_id:
            return t
    known = ", ".join(t["id"] for t in load()["tasks"])
    raise SystemExit(f"unknown task {task_id!r}. Known: {known}")


def models() -> list[str]:
    """EVERY model in the fixed list, including any that will never produce a take.

    A model that never runs publishes as `not run — <reason>`, never as absent. Dropping it from
    this list would make the table read as though the axis had always been three wide, which is a
    quieter and less honest claim than the one the record supports. Callers that want only the
    models which actually run ask for running_models().
    """
    return list(load()["models"])


def running_models() -> list[str]:
    """The models a take will actually be driven on."""
    status = load().get("model_status") or {}
    return [m for m in models() if status.get(m, {}).get("runs", True)]


def not_run_reason(model: str) -> str | None:
    return (load().get("model_status") or {}).get(model, {}).get("not_run_reason")


def n() -> int:
    return int(load()["n"])


def cells() -> list[tuple[str, str, str, int]]:
    """Every (task, half, model, take) the plan calls for, in a fixed canonical order.

    Canonical means sorted, not shuffled: this is the SET the permutation is taken over, and it
    must not depend on dictionary ordering or on which machine built it.
    """
    out = []
    for t in sorted(x["id"] for x in load()["tasks"]):
        for half in ("positive", "control"):
            for m in sorted(running_models()):
                for k in range(1, n() + 1):
                    out.append((t, half, m, k))
    return out


def axis_of(model: str) -> str:
    return "local" if model in load()["local_models"] else "claude"


def order(seed_sha: str) -> dict[str, list[tuple[str, str, str, int]]]:
    """One permutation per axis, from a seed nobody controlled when the design was written.

    random.Random(int) with a fixed algorithm is reproducible across machines and Python versions
    for shuffle; the seed is the integer value of the sha, so the whole thing is a pure function of
    a commit that did not exist when this code was written.
    """
    if not seed_sha or len(seed_sha) < 7:
        raise SystemExit("the take order needs the full sha of the pre-freeze review commit")
    result: dict[str, list] = {}
    for axis in ("claude", "local"):
        members = [c for c in cells() if axis_of(c[2]) == axis]
        rng = random.Random(int(hashlib.sha256((axis + seed_sha).encode()).hexdigest(), 16))
        rng.shuffle(members)
        result[axis] = members
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Read the study's pre-registration.")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--task", metavar="ID")
    ap.add_argument("--order", metavar="SHA")
    args = ap.parse_args()

    if args.status:
        pre = load()
        print(f"in force : {pre['_source']}")
        print(f"frozen   : {pre['_frozen']}")
        print(f"status   : {pre.get('status', '?')}")
        print(f"tasks    : {len(pre['tasks'])}  ({', '.join(t['id'] for t in pre['tasks'])})")
        print(f"models   : {len(pre['models'])} in the fixed list, {len(running_models())} running")
        for m in models():
            reason = not_run_reason(m)
            print(f"           {m:28} {'runs' if not reason else 'NOT RUN'}")
            if reason:
                print(f"             {reason}")
        print(f"n        : {pre['n']}  -> {len(cells())} planned takes")
        print(f"take order: {'FIXED' if pre.get('take_order_seed') else 'not yet — seeded at the freeze'}")
        if not pre["_frozen"]:
            print("\nThis is a DRAFT. No take may run against it and no number may be graded from "
                  "it. The walks are what turn it into the frozen file.")
        return 0

    if args.task:
        print(json.dumps(task(args.task), indent=2))
        return 0

    if args.order:
        o = order(args.order)
        for axis, members in o.items():
            print(f"\n=== {axis} axis — {len(members)} takes, seeded by {args.order[:12]}")
            for i, (t, half, m, k) in enumerate(members[:8]):
                print(f"  {i:3}  {t:22} {half:8} {m:28} take {k}")
            if len(members) > 8:
                print(f"  ... {len(members) - 8} more")
        return 0

    ap.error("give --status, --task <id> or --order <sha>")


if __name__ == "__main__":
    raise SystemExit(main())
