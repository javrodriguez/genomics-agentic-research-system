#!/usr/bin/env python3
"""The one door to the pre-registration. Every other module reads the study's design through here.

    python3 evals/gap-study-4/prereg.py --status        which file is in force, whether it is frozen, its arms
                                                        and their models, and the planned rows counted
    python3 evals/gap-study-4/prereg.py --task <id>     one task's design
    python3 evals/gap-study-4/prereg.py --order <sha>   the take order this seed produces (freeze.planned_order;
                                                        the seed is the full 40 lowercase hex characters)
    python3 evals/gap-study-4/prereg.py --order-from-beacon
                                                        the order the freeze writes: the seed order_beacon.seed
                                                        makes of the registered drand round, refused until that
                                                        round is published

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
of the design's whole planned rows, interleaved across arm, model, task and half. Anyone can
recompute it from the frozen seed with `--order <seed>`, which calls that same function (slice S3
replaced round 3's per-axis order here).

WHAT THE SEED BINDS, AND WHAT IT DOES NOT (pre-freeze review 1, MAJOR 9, lane L1). This docstring
used to say the review commit's sha alone made the order impossible to choose. It did not: an
operator holding the clone could commit the review, preview the order, reset and recommit, and
pick among as many orders as it cared to commit. The seed is now order_beacon.seed of one public
drand round the draft registers (take_order_beacon) and its randomness alone, read by the freeze
from two relays; nothing the operator commits enters it. The freeze also requires that the round
was registered once in its history (from None, never changed again), and GitHub's own push records
of that registering commit and of the draft's last commit, each an hour or more before the round is
published; `--order-from-beacon` refuses to preview an order before the round is published. What is
left is named in the draft (take_order_beacon.residual): a mirror whose history someone rewrites,
or GitHub itself, and the round's unverified signature; candidates on other pushed branches are
refused (freeze.mirror_problem).

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

    Round 4's design keys `models` by arm (arm -> its models): the list is every planned arm's models in the design's
    arm order, then each optional arm's model (`optional_arms`), which runs only if it is given rows. The arm letters
    themselves are never models (W6D-R1-1, W7A-R1-2).

    A model that never runs publishes as `not run — <reason>`, never as absent. Dropping it from
    this list would make the table read as though the axis had always been narrower, which is a
    quieter and less honest claim than the one the record supports. Callers that want only the
    models which actually run ask for running_models().
    """
    pre = load()
    table = pre["models"]
    if not isinstance(table, dict):
        return list(table)
    arms = list(pre.get("arms") or table)
    out = [m for arm in arms if arm in table for m in table[arm]]
    optional = pre.get("optional_arms") or {}
    out += [optional[arm]["model"] for arm in arms if arm not in table and isinstance(optional.get(arm), dict)
            and optional[arm].get("model") and optional[arm]["model"] not in out]
    return out


# Lane gemini-defer (rulings R2 and R5, glitch-f1 under Javier's standing delegation, 22 Oct 2026). An arm in the
# design's `deferred_arms` stays registered in full (its rows, models and counts are unchanged) and is not run: it
# prints as "deferred (<who>, <date>)", never as running and never as absent. Its run starts only on a committed go
# record (GO_RECORD, closed GO_KEYS, modelled on costs.month_turn_allowed's "caps trimmed" record), which batch.py
# reads before driving a row of the arm and labelling/sample.py reads before a follow-up draw.
DEFERRED = "deferred"
DEFERRAL_DATE = re.compile(r"\b(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4})\b")
GO_RECORD = HERE / "deferred-arm-go.json"
GO_KIND = "deferred arm go"
GO_KEYS = ("kind", "arm", "by", "decision", "ask", "at")
GO_BY = "Javier"


def deferral_label(entry: dict) -> str:
    """"deferred (Javier, 22 Oct 2026)": who deferred the arm and the date of his words, read from the entry."""
    found = DEFERRAL_DATE.search(entry.get("words") or "") if isinstance(entry, dict) else None
    if not found or not isinstance(entry.get("by"), str) or not entry["by"].strip():
        raise ValueError(f"a deferred arm names who deferred it and the dated words: {entry!r}")
    return f"{DEFERRED} ({entry['by']}, {found.group(1)} {found.group(2)} {found.group(3)})"


def deferred_arms(pre: dict | None = None) -> dict:
    """arm -> its `deferred_arms` entry in the design in force; an entry that is not a deferral is refused."""
    pre = load() if pre is None else pre
    table = pre.get("deferred_arms") or {}
    if not isinstance(table, dict):
        raise ValueError("deferred_arms maps an arm to its deferral")
    for arm, entry in table.items():
        if not isinstance(entry, dict) or entry.get("status") != DEFERRED:
            raise ValueError(f"deferred_arms.{arm} is not a deferral (status {DEFERRED!r})")
        deferral_label(entry)
    return dict(table)


def deferred_models(pre: dict | None = None) -> dict:
    """model -> its arm's deferral label, for each model of a deferred arm (the design's `models`)."""
    pre = load() if pre is None else pre
    table = pre.get("models") if isinstance(pre.get("models"), dict) else {}
    out = {}
    for arm, entry in deferred_arms(pre).items():
        for model in table.get(arm) or entry.get("models") or []:
            out[model] = deferral_label(entry)
    return out


def go_record_problems(record, arm: str) -> list[str]:
    """Why this record is not Javier's committed go for the deferred arm (empty when it is)."""
    import datetime
    if not isinstance(record, dict) or set(record) != set(GO_KEYS):
        return [f"a go record holds exactly {GO_KEYS}"]
    p = []
    if record["kind"] != GO_KIND:
        p.append(f"kind is {record['kind']!r}, not {GO_KIND!r}")
    if record["arm"] != arm:
        p.append(f"arm is {record['arm']!r}, not {arm!r}")
    if record["by"] != GO_BY:
        p.append(f"by is {record['by']!r}, not {GO_BY!r}")
    for k in ("decision", "ask"):
        if not isinstance(record[k], str) or not record[k].strip():
            p.append(f"{k} names the record of his go")
    try:
        at = datetime.datetime.fromisoformat(str(record["at"]).replace("Z", "+00:00"))
        if at.tzinfo is None:
            p.append("at carries its UTC offset")
    except ValueError:
        p.append(f"at {record['at']!r} is not an ISO time")
    return p


def committed_go_records(root: Path | None = None) -> list:
    """The go records committed at HEAD (git show HEAD:./deferred-arm-go.json), never the working copy; none when
    the file is not committed or no git history can be read, so a deferred arm stays deferred (fail closed)."""
    import subprocess
    root = HERE if root is None else Path(root)
    got = subprocess.run(["git", "-C", str(root), "show", "HEAD:./" + GO_RECORD.name], capture_output=True)
    if got.returncode != 0:
        return []
    doc = json.loads(got.stdout)
    if not isinstance(doc, list):
        raise ValueError(f"{GO_RECORD.name} is a list of go records")
    return doc


def deferred_arm_go(arm: str, records: list | None = None) -> bool:
    """True when a committed go record for this arm passes go_record_problems."""
    records = committed_go_records() if records is None else records
    return any(not go_record_problems(r, arm) for r in records)


def running_models() -> list[str]:
    """The models a take will actually be driven on: those the design plans rows for (W7A-R1-2), less a deferred
    arm's (lane gemini-defer, R2). A design without rows (round 3's shape) falls back to its model_status."""
    pre = load()
    if isinstance(pre.get("rows"), list):
        planned = {r.get("model") for r in pre["rows"]}
        held = deferred_models(pre)
        return [m for m in models() if m in planned and m not in held]
    status = pre.get("model_status") or {}
    return [m for m in models() if status.get(m, {}).get("runs", True)]


def not_run_reason(model: str) -> str | None:
    """Why a listed model does not run, or None when it does (W7A-R1-2)."""
    pre = load()
    if isinstance(pre.get("rows"), list):
        if model in running_models():
            return None
        held = deferred_models(pre)
        if model in held:
            return held[model]
        why = [f"{o.get('status')}, {o.get('cut')}" for o in (pre.get("optional_arms") or {}).values()
               if isinstance(o, dict) and o.get("model") == model]
        return "; ".join(why + [f"no planned rows in {pre.get('_source', 'the design')}"])
    return (pre.get("model_status") or {}).get(model, {}).get("not_run_reason")


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
    held = deferred_arms(pre)
    shown = [a for a in planned if a in held]          # review NIT-3: never an empty "; deferred: "
    out = [f"{ARMS_LABEL:9}: {len(planned)} planned ({', '.join(planned)})"
           + (f"; optional: {', '.join(extra)}" if extra else "")
           + (f"; deferred: {', '.join(shown)}" if shown else "")]
    for arm in arms:
        if arm in table:
            harnesses = sorted({str(r["agent"]["harness"]) for r in rows if r.get("arm") == arm}) or ["no rows"]
            out.append(f"  arm {arm}  {'/'.join(harnesses)}: {len(table[arm])} models, {by_arm[arm]} rows: "
                       f"{', '.join(table[arm])}" + (f"; {deferral_label(held[arm])}" if arm in held else ""))
        elif arm in optional:
            o = optional[arm]
            out.append(f"  arm {arm}  optional: {o.get('model')}, {by_arm[arm]} rows; {o.get('status')}")
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


def order_from_beacon(*, opener=None, now=None) -> list[dict]:
    """The take order the freeze writes (MAJOR 9): on the frozen file, from its recorded beacon reading; on the draft,
    only once the registered drand round is published, read from both relays. Raises order_beacon.BeaconRefused when
    no order can exist yet."""
    import order_beacon
    pre = load()
    round_no = order_beacon.registered_round(pre.get("take_order_beacon"))
    reading = pre.get("take_order_beacon_reading") if pre.get("_frozen") else None
    if pre.get("_frozen"):
        bad = order_beacon.reading_problems(reading, round_no)
        if bad:
            raise order_beacon.BeaconRefused("the frozen file's beacon reading is refused: " + "; ".join(bad))
    else:
        reading = order_beacon.read_relays(round_no, opener=opener, now=now)
    return load_freeze().planned_order(pre, order_beacon.seed(reading))


def main() -> int:
    ap = argparse.ArgumentParser(description="Read the study's pre-registration.")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--task", metavar="ID")
    ap.add_argument("--order", metavar="SHA")
    ap.add_argument("--order-from-beacon", action="store_true")
    args = ap.parse_args()

    if args.status:
        pre = load()
        print(f"in force : {pre['_source']}")
        print(f"frozen   : {pre['_frozen']}")
        print(f"status   : {pre.get('status', '?')}")
        print(f"tasks    : {len(pre['tasks'])}  ({', '.join(t['id'] for t in pre['tasks'])})")
        for line in status_lines(pre):
            print(line)
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

    if args.order_from_beacon:
        import order_beacon
        load_freeze()
        try:
            rows = order_from_beacon()
        except (order_beacon.BeaconRefused, ValueError) as e:
            print(f"take order: refused: {e}")
            return 1
        print(f"take order: {ORDER_FUNCTION}, one permutation of {len(rows)} whole planned rows, seeded by "
              f"order_beacon.seed of the registered drand round")
        for i, r in enumerate(rows[:8]):
            print(f"  {i:3}  {r['arm']:2} {r['model']:28} {r['task']:22} {r['half']:8} "
                  f"{r['wording']} repeat {r['repeat']}  {r['slot']}")
        return 0

    ap.error("give --status, --task <id>, --order <sha> or --order-from-beacon")


if __name__ == "__main__":
    raise SystemExit(main())
