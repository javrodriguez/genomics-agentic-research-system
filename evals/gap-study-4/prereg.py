#!/usr/bin/env python3
"""The one door to the pre-registration. Every other module reads the study's design through here.

    python3 evals/gap-study-4/prereg.py --status        which file is in force, whether it is frozen, its arms
                                                        and their models, and the planned rows counted
    python3 evals/gap-study-4/prereg.py --task <id>     one task's design
    python3 evals/gap-study-4/prereg.py --order <sha>   the take order this seed produces (freeze.planned_order;
                                                        the sha is the full 40 lowercase hex characters)

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

THE TAKE ORDER IS A FUNCTION, NOT A LIST. In round 4 it is freeze.planned_order: ONE permutation
of the design's whole planned rows, interleaved across arm, model, task and half, seeded by the sha
of the pre-freeze review commit -- a sha that does not exist until the review has happened, so the
order cannot have been chosen to suit a result. Anyone can recompute it from the seed with
`--order <sha>`, which calls that same function (slice S3 replaced round 3's per-axis order here).

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
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

    Round 4's design keys `models` by arm (arm -> its models), so the list is every planned arm's models in the
    design's arm order; the arm letters themselves are never models (W6D-R1-1, lane w7a).

    A model that never runs publishes as `not run — <reason>`, never as absent. Dropping it from
    this list would make the table read as though the axis had always been three wide, which is a
    quieter and less honest claim than the one the record supports. Callers that want only the
    models which actually run ask for running_models().
    """
    pre = load()
    table = pre["models"]
    if isinstance(table, dict):
        return [m for arm in pre.get("arms", list(table)) if arm in table for m in table[arm]]
    return list(table)


def running_models() -> list[str]:
    """The models a take will actually be driven on."""
    status = load().get("model_status") or {}
    return [m for m in models() if status.get(m, {}).get("runs", True)]


def not_run_reason(model: str) -> str | None:
    return (load().get("model_status") or {}).get(model, {}).get("not_run_reason")


def n() -> int:
    return int(load()["n"])


ARMS_LABEL = "arms"


def planned_rows(pre: dict) -> list[dict]:
    """The design's planned rows themselves: --status counts these, never the draft's own `counts` field and never
    round 3's (task, half, model, take) shape (W6D-R1-1)."""
    rows = pre.get("rows")
    if not isinstance(rows, list):
        raise SystemExit(f"{pre.get('_source', 'the design')} has no planned rows: --status reads round 4's design")
    return rows


def status_lines(pre: dict) -> list[str]:
    """--status for round 4's design: the arms as arms, each arm's harness and models, and the planned rows."""
    rows = planned_rows(pre)
    table = pre["models"]
    arms = list(pre.get("arms") or table)
    optional = pre.get("optional_arms") or {}
    planned = [a for a in arms if a in table]
    by_arm = collections.Counter(r.get("arm") for r in rows)
    extra = [a for a in arms if a not in table and a in optional]
    out = [f"{ARMS_LABEL:9}: {len(planned)} planned ({', '.join(planned)})"
           + (f"; optional: {', '.join(extra)}" if extra else "")]
    for arm in arms:
        if arm in table:
            harnesses = sorted({str(r["agent"]["harness"]) for r in rows if r.get("arm") == arm}) or ["no rows"]
            out.append(f"  arm {arm}  {'/'.join(harnesses)}: {len(table[arm])} models, {by_arm[arm]} rows: "
                       f"{', '.join(table[arm])}")
        elif arm in optional:
            o = optional[arm]
            out.append(f"  arm {arm}  optional: {o.get('model')}, {by_arm[arm]} rows ({o.get('status')})")
        else:
            out.append(f"  arm {arm}  in the arm list with no models and {by_arm[arm]} rows")
    out.append(f"rows     : {len(rows)} planned rows (n = {pre['n']} tries per half), "
               f"{len({r.get('half_cell') for r in rows})} half-cells")
    return out


ORDER_FUNCTION = "freeze.planned_order"
SEED_SHAPE = re.compile(r"[0-9a-f]{40}")


def seed_problem(seed_sha: str) -> str | None:
    """Why this seed cannot name the frozen order, or None.

    The freeze hashes the review sha's exact string into every row's key, so an abbreviated or
    upper-case spelling of the same commit gives a different, confident-looking order. Only the
    full 40 lowercase hex characters are the seed.
    """
    if isinstance(seed_sha, str) and SEED_SHAPE.fullmatch(seed_sha):
        return None
    return (f"the take order needs the full sha of the pre-freeze review commit, exactly 40 lowercase hex "
            f"characters; got {seed_sha!r}")


def load_freeze():
    """freeze, imported on first use (freeze imports this module). main() calls it before reading the order,
    so a broken ownership record fails as itself, never as a refusal of the design."""
    import freeze
    return freeze


def order(seed_sha: str) -> list[dict]:
    """The take order the freeze writes for this seed: freeze.planned_order over the whole rows.

    One permutation of every planned row (arm, model, task, half, wording, repeat, agent, slot),
    not one per axis; the freeze calls the same function with the review commit's sha, so this is
    the order a frozen prereg.json carries as take_order. Each row's bytes, agent version included,
    feed the permutation, so a draft whose versions are still pending has no order yet: the
    freeze's own ledger check refuses it (ValueError), and this door does not fill or skip it.
    The seed must be the full 40 lowercase hex characters (seed_problem); anything else exits.
    """
    problem = seed_problem(seed_sha)
    if problem:
        raise SystemExit(problem)
    return load_freeze().planned_order(load(), seed_sha)


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
        for line in status_lines(pre):
            print(line)
        for m in models():
            reason = not_run_reason(m)
            if reason:
                print(f"  NOT RUN {m}: {reason}")
        print(f"take order: {'FIXED' if pre.get('take_order_seed') else 'not yet — seeded at the freeze'}")
        if not pre["_frozen"]:
            print("\nThis is a DRAFT. No take may run against it and no number may be graded from "
                  "it. The walks are what turn it into the frozen file.")
        return 0

    if args.task:
        print(json.dumps(task(args.task), indent=2))
        return 0

    if args.order:
        problem = seed_problem(args.order)
        if problem:
            print(f"take order: refused: {problem}")
            return 1
        load_freeze()  # outside the try: an ownership-record failure is not the design's refusal
        try:
            rows = order(args.order)
        except ValueError as e:
            print(f"take order: {ORDER_FUNCTION} refuses the design in force ({load()['_source']}): {e}")
            return 1
        print(f"take order: {ORDER_FUNCTION}, one permutation of {len(rows)} whole planned rows, "
              f"seeded by {args.order[:12]}")
        for i, r in enumerate(rows[:8]):
            print(f"  {i:3}  {r['arm']:2} {r['model']:28} {r['task']:22} {r['half']:8} "
                  f"{r['wording']} repeat {r['repeat']}  {r['slot']}")
        if len(rows) > 8:
            print(f"  ... {len(rows) - 8} more")
        return 0

    ap.error("give --status, --task <id> or --order <sha>")


if __name__ == "__main__":
    raise SystemExit(main())
