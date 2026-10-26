#!/usr/bin/env python3
"""The CP6 walk list, and which of its walks the register covers (rehearsals/README.md question 3).

    python3 evals/gap-study-4/walk_plan.py --list                         the required walks, one line each, and a
                                                                          figure per arm and model
    python3 evals/gap-study-4/walk_plan.py --coverage                     each required walk covered or missing;
                                                                          exit 0 while walks are missing
    python3 evals/gap-study-4/walk_plan.py --coverage --require-complete  exit 1 on any missing walk

WHAT CP6 REQUIRES. The round 4 plan's CP6 (lines 874-876) lists the walks: every wording of every task, on Haiku,
and every task and half on each model, with at least one wording. Ruling Q-2 (next-slices plan of 12 Oct, section 3,
as glitch-2f applies it) reads that for arm A exactly, and for arms O and G as D8:448 says: every task and half once
per added model. Bring-up walks are registered like any walk and are not required; a retry is a new walk id and
covers its spec once (ruling W8-layout-1). The optional arm C (D2 A) runs no row and is not required.

DERIVED, NEVER TYPED. plan_walks() reads the figures from the design in force and from nothing else: the tasks and
their wordings from prereg-draft.json, each task's halves from tasks/<task>.json (both through
walk_register.design_in_force, the reading the register's own check uses), the planned arms and their models from
the draft's `models`, and each model's harness from the draft's rows. Drop a task, a half or a wording from the
design and the plan shrinks with it. The one rule taken from the plan's words is which model gets every wording:
EVERY_WORDING names the arm and the model family the plan names (plan 875), and the design must hold exactly one
such model on that arm, or the plan is refused.

ONE SPEC, THE REGISTER'S FIELDS. Each spec carries exactly the register entry's fields (walk_register.FIELDS) plus
`agent`, the harness the design's rows give the model. `walk` is None: the walk id is the runner's (no ruling names a
rule for it). `reason` is the plan's reason for the walk, which the runner may keep or replace. `counted` is false.
Every spec is checked by walk_register.entry_problems against the design in force (with a probe walk id in place of
the runner's), and its cell (arm, model, task, half, wording) must be a row of the design; any refusal refuses the
whole plan. On models other than the every-wording one the spec names the task's first wording as the one to run,
and any wording of the task covers it ("with at least one wording").

COVERAGE READS THE REGISTER, THROUGH THE REGISTER'S OWN CHECK, AND EACH REGISTERED WALK'S GRADE. --coverage opens
rehearsals/register.json and, for each walk it names, that walk's grade.json (and a pending walk's regrade.json): no walk
folder is listed, and binding the register to its folders stays walk_register.py --check's job. The register is read by one
code path, the register's own (review W11C-R1-1): its bytes are copied into a temporary folder beside a stand-in
folder for each walk id it names, walk_register.check runs there against the design in force, and only a register
that check accepts is read, by walk_register.registered. So everything the check refuses at the register level (a
walk id used twice, two ids that differ only by case, a wrong schema, keys other than schema and walks, a walks value
that is not a list, an entry that is not an object or that the design refuses, a duplicate JSON key) refuses the
coverage report too, exit 2, never an exit 0 over a malformed register. The stand-in folders mean only the folder
rules are left to walk_register.py --check, which the gates run. A register entry the check accepts and the plan
does not require (an arm C walk, a bring-up walk off the list), or whose cell is not a row of the design, is reported
by its walk id and never counted toward coverage. A missing or linked register exits 2: a missing register is not an
empty one. The temporary folder is the only thing this file writes, and it is removed before the report prints.

ONLY A GRADED WALK IS COVERAGE (batch-8 review finding 1 and the batch-8 fix ruling, glitch-06, 14 Oct 2026; CP6:
"Every walk is graded but never counted"). A walk covers its spec only when its grade.json is graded true, or when it is
a pending vendor walk (pending_walk.py) that a verified graded-true regrade supersedes and a vendor recheck under the
constants in force reads (lane vendor-admission T4 P5, R-9). Every other registered walk is reported with why and
never counted: "pending", "regrade refused", "pending: regraded, no checker reading under the constants in force",
"not graded" (a walk refused or failed before its first agent turn) and "grade unreadable" (missing or not JSON: fail
closed). pending_walk.uncounted_walks decides.

WALK-COVER STRICT (OD131, Javier, 25 Oct 2026: "walk-cover strict"; lane pf1-walk-cover-strict). A Claude walk counts
as covered only if it rechecks clean under the harness as it will be frozen, and (OD132, 26 Oct 2026: "walk-cover-o
strict") so does a Codex walk. strict_walks names the register's walks on the arms the rule covers
(WALK_COVER_STRICT: arms A and O, by the two rulings' wording), and pending_walk.uncounted_walks reports each one
whose effective checker reading carries a reason the routing table at HEAD routes to harness-error, or every one of
them when that table cannot be read; arm G, deferred, counts as before.

THE FREEZE'S GATE (pre-freeze review 1, MAJOR 4 part 3, lane L1). --require-run-arms exits 1 on any missing walk of
an arm the freeze runs and prints each deferred arm's coverage (the draft's deferred_arms) as recorded, not required;
freeze.py runs the same reading in process (coverage_report) before it prepares the frozen file, and
freeze_rehearsal.py runs --coverage --require-run-arms among its walk gates. --require-complete, every arm, is the
precondition of a deferred arm's later go.

WHAT THIS DOES NOT DO. It never runs a walk, and it says nothing about what a walk showed. Every figure it prints is
bound to one arm and one model; it states no figure across arms or models.

No model, no network, stdlib only. Read-only, apart from the temporary copy of the register.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import walk_register  # noqa: E402

# Plan 875: "every wording of every task, on Haiku". The arm and the family the plan names; the model id is the
# design's, and exactly one model of the arm must carry the family's name.
EVERY_WORDING = {"arm": "A", "family": "haiku", "source": "plan 875"}
ANY_WORDING = "*"
PROBE_WALK = "planned-walk"          # the id a spec is checked under; the runner names the real walk
FIELDS = walk_register.FIELDS
STAND_IN = "stand-in.txt"     # the one file of a scratch walk folder (read_register); never a walk record
REASON_EVERY = ("CP6 walk (plan 874-876, ruling Q-2): every wording of every task and half on this model; graded, "
                "never counted")
REASON_ONCE = ("CP6 walk (plan 874-876, D8:448, ruling Q-2): every task and half on this model, with at least one "
               "wording; graded, never counted")


class PlanRefused(ValueError):
    pass


class RegisterUnreadable(ValueError):
    pass


def resolve_every_wording(models_by_arm: dict) -> tuple:
    arm, family = EVERY_WORDING["arm"], EVERY_WORDING["family"]
    found = [m for m in models_by_arm.get(arm, []) if family in m.casefold()]
    if len(found) != 1:
        raise PlanRefused(f"{EVERY_WORDING['source']} names one {family} model on arm {arm} for every wording; the "
                          f"design holds {found!r}")
    return arm, found[0]


def design_in_force(study_dir: Path = HERE) -> dict:
    """What the plan is derived from: the register's design (tasks, halves, wordings, every arm's models), the
    planned arms' models, the harness of each planned model and the design's cells, all from the design files."""
    study_dir = Path(study_dir)
    register = walk_register.design_in_force(study_dir)
    draft = json.loads((study_dir / "prereg-draft.json").read_text())
    planned = {arm: list(models) for arm, models in draft["models"].items()}
    harnesses: dict = {}
    cells = set()
    for row in draft["rows"]:
        harnesses.setdefault((row["arm"], row["model"]), set()).add(row["agent"]["harness"])
        cells.add((row["arm"], row["model"], row["task"], row["half"], row["wording"]))
    agents = {}
    for arm, models in planned.items():
        for model in models:
            got = harnesses.get((arm, model), set())
            if len(got) != 1:
                raise PlanRefused(f"arm {arm}, {model}: the design's rows give the harnesses {sorted(got)!r}; a "
                                  f"planned model runs under exactly one")
            agents[(arm, model)] = next(iter(got))
    return {"register": register, "planned": planned, "agents": agents, "cells": cells,
            "every_wording": resolve_every_wording(planned)}


def plan_walks(design: dict) -> list[dict]:
    """The ordered list of required walk specs: arms and models in the draft's order, then tasks, halves and
    wordings in the design's order. Raises PlanRefused when any spec is refused by the design in force."""
    agents = design["agents"]
    specs = []
    for arm, models in design["planned"].items():
        for model in models:
            every = (arm, model) == design["every_wording"]
            for task_id, task in design["register"]["tasks"].items():
                wordings = list(task["wordings"]) if every else list(task["wordings"])[:1]
                for half in task["halves"]:
                    for wording in wordings:
                        specs.append({
                            "walk": None, "task": task_id, "half": half, "wording": wording, "arm": arm,
                            "model": model, "reason": REASON_EVERY if every else REASON_ONCE, "counted": False,
                            "agent": agents[(arm, model)],
                        })
    problems = []
    for i, spec in enumerate(specs):
        probe = {k: spec[k] for k in FIELDS}
        probe["walk"] = PROBE_WALK
        problems += [f"spec {i}: {p}" for p in walk_register.entry_problems(i, probe, design["register"])]
        cell = (spec["arm"], spec["model"], spec["task"], spec["half"], spec["wording"])
        if cell not in design["cells"]:
            problems.append(f"spec {i}: {cell!r} is not a row of the design")
    if problems:
        raise PlanRefused("the walk plan is refused by the design in force: " + "; ".join(problems[:5]) +
                          (f"; and {len(problems) - 5} more" if len(problems) > 5 else ""))
    return specs


def counts(specs: list[dict]) -> dict:
    """{arm: {model: required walks}}, in plan order."""
    out: dict = {}
    for spec in specs:
        per = out.setdefault(spec["arm"], {})
        per[spec["model"]] = per.get(spec["model"], 0) + 1
    return out


def cover_key(entry: dict, design: dict) -> tuple:
    """What a walk covers: on the every-wording model its own wording, elsewhere its task and half."""
    exact = (entry["arm"], entry["model"]) == design["every_wording"]
    return (entry["arm"], entry["model"], entry["task"], entry["half"], entry["wording"] if exact else ANY_WORDING)


def coverage(entries: list, specs: list[dict], design: dict, uncounted=None) -> dict:
    """covered: {spec key: [walk ids, in register order]}; missing: [spec]; outside: [(walk label, why)]; uncounted:
    [(walk label, why)] for the walks `uncounted` names ({walk id: why}), never counted."""
    uncounted = {} if uncounted is None else uncounted
    by_key = {}
    for spec in specs:
        key = cover_key(spec, design)
        if key in by_key:
            raise PlanRefused(f"two specs share the key {key!r}")
        by_key[key] = spec
    covered: dict = {}
    outside, held = [], []
    for i, entry in enumerate(entries):
        label = entry.get("walk") if isinstance(entry, dict) and isinstance(entry.get("walk"), str) \
            else f"entry {i}"
        bad = walk_register.entry_problems(i, entry, design["register"])
        if bad:
            outside.append((label, "; ".join(bad)))
            continue
        key = cover_key(entry, design)
        if key not in by_key:
            outside.append((label, f"not a walk the plan requires (arm {entry['arm']}, {entry['model']}, "
                                   f"{entry['task']} {entry['half']} {entry['wording']})"))
            continue
        cell = (entry["arm"], entry["model"], entry["task"], entry["half"], entry["wording"])
        if cell not in design["cells"]:
            outside.append((label, f"{cell!r} is not a row of the design, so it covers no required walk"))
            continue
        if entry["walk"] in uncounted:            # batch-8 rulings: only a graded walk covers its spec
            held.append((label, uncounted[entry["walk"]]))
            continue
        covered.setdefault(key, []).append(label)
    missing = [spec for spec in specs if cover_key(spec, design) not in covered]
    return {"covered": covered, "missing": missing, "outside": outside, "uncounted": held}


def stand_in_ids(raw: bytes) -> list[str]:
    """The walk ids a register names that can be folder names, read leniently; [] when the bytes are not a register.
    These name the scratch folders only: whether the register is well formed is walk_register.check's to say."""
    try:
        doc = json.loads(raw, object_pairs_hook=walk_register.no_duplicate_keys)
    except (UnicodeDecodeError, ValueError):
        return []
    walks = doc.get("walks") if isinstance(doc, dict) else None
    if not isinstance(walks, list):
        return []
    return [e["walk"] for e in walks if isinstance(e, dict) and isinstance(e.get("walk"), str)
            and walk_register.WALK_ID.fullmatch(e["walk"])]


def read_register(base: Path, design: dict) -> list:
    """The register's entries, read only once walk_register.check accepts the register (W11C-R1-1). Raises
    RegisterUnreadable on a missing or linked register and on every problem the check reports."""
    path = Path(base) / walk_register.REGISTER_NAME
    if path.is_symlink() or not path.is_file():
        raise RegisterUnreadable(f"{path} is not a file; a missing register is not an empty one")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RegisterUnreadable(f"{path} cannot be read: {exc}") from exc
    with tempfile.TemporaryDirectory(prefix="walk-plan-register-") as tmp:
        scratch = Path(tmp)
        (scratch / walk_register.REGISTER_NAME).write_bytes(raw)
        for walk in stand_in_ids(raw):
            # an id that cannot be a folder here (register.json itself, a name too long for the filesystem) gets no
            # stand-in, so the check reports its folder missing and the register is refused: fail closed, by name
            try:
                (scratch / walk).mkdir(exist_ok=True)
                (scratch / walk / STAND_IN).write_text("a stand-in; coverage never reads a walk folder\n")
            except OSError:
                pass
        # the recheck-coverage ruling (15 Oct 2026): entries checked here, each file bound by coverage itself
        problems, _ = walk_register.check(scratch, design["register"], recheck_files=False)
        if problems:
            raise RegisterUnreadable(f"walk_register's check refuses {path}: " + "; ".join(problems[:5]) +
                                     (f"; and {len(problems) - 5} more" if len(problems) > 5 else ""))
        return walk_register.registered(scratch)


def spec_line(spec: dict) -> str:
    return f"{spec['arm']} {spec['model']} {spec['task']} {spec['half']} {spec['wording']}"


def model_line(arm: str, model: str, agent: str) -> str:
    return f"arm {arm}, {model} ({agent})"


def list_lines(specs: list[dict], design: dict) -> list[str]:
    lines = ["# walk plan: CP6 (plan 874-876), arms O and G per D8:448 (ruling Q-2); one line per required walk",
             "# columns: arm, model, harness, task, half, wording to run"]
    for spec in specs:
        lines.append(f"walk  {spec['arm']} {spec['model']} {spec['agent']} {spec['task']} {spec['half']} "
                     f"{spec['wording']}")
    for arm, per in counts(specs).items():
        for model, n in per.items():
            rule = "every wording of each task and half" if (arm, model) == design["every_wording"] else \
                "each task and half, any one wording"
            lines.append(f"{model_line(arm, model, design['agents'][(arm, model)])}: {n} required walks, {rule}")
    return lines


def coverage_lines(got: dict, specs: list[dict], design: dict, n_entries: int) -> list[str]:
    lines = ["# walk coverage: CP6 (plan 874-876), arms O and G per D8:448 (ruling Q-2); read from the register only"]
    if n_entries == 0:
        lines.append("the register lists no walk: every required walk below is missing, and nothing here is "
                     "evidence about any walk")
    for spec in specs:
        walks = got["covered"].get(cover_key(spec, design))
        if walks:
            more = f" (also {', '.join(walks[1:])}, the same walk again)" if len(walks) > 1 else ""
            lines.append(f"covered  {spec_line(spec)} by {walks[0]}{more}")
        else:
            lines.append(f"missing  {spec_line(spec)}")
    for label, why in got["outside"]:
        lines.append(f"outside the plan, not counted: walk {label!r}: {why}")
    for label, why in got["uncounted"]:
        lines.append(f"{why}, not counted: walk {label!r}: only a graded walk covers its spec")
    for arm, per in counts(specs).items():
        for model, n in per.items():
            gap = sum(1 for s in got["missing"] if (s["arm"], s["model"]) == (arm, model))
            lines.append(f"{model_line(arm, model, design['agents'][(arm, model)])}: {n - gap} of {n} required walks "
                         f"covered, {gap} missing")
    return lines


# Pre-freeze review 1, MAJOR 4 part 3 (the lane orchestrator's fold plan of 24 Oct 2026, under OD105's "runs exactly
# as registered"): the freeze requires coverage of every arm that runs at it, and records a deferred arm's coverage
# without requiring it; complete coverage of a deferred arm is a precondition of its later go (--require-complete).
# Which arms are deferred is the draft's own deferred_arms (status "deferred"), never typed here.
DEFERRED_STATUS = "deferred"


def deferred_arms(study_dir: Path = HERE) -> dict:
    """{arm: its deferred_arms entry} for each arm the draft defers."""
    draft = json.loads((Path(study_dir) / "prereg-draft.json").read_text())
    return {arm: e for arm, e in (draft.get("deferred_arms") or {}).items()
            if isinstance(e, dict) and e.get("status") == DEFERRED_STATUS}


# The arms whose walks are judged by pending_walk's strict rule. OD131 (Javier, 25 Oct 2026: "walk-cover strict") names
# a Claude walk, so arm A; OD132 (Javier, 26 Oct 2026: "walk-cover-o strict") a Codex walk, so arm O. Arm G is deferred
# and named by neither: it counts as before.
WALK_COVER_STRICT = {"arms": ("A", "O"), "source": "OD131 (Javier, 25 Oct 2026: \"walk-cover strict\"), OD132 "
                                                   "(Javier, 26 Oct 2026: \"walk-cover-o strict\")"}


def strict_walks(entries: list) -> list:
    """The walk ids of the register entries on an arm WALK_COVER_STRICT names, in register order."""
    return [e["walk"] for e in entries if e["arm"] in WALK_COVER_STRICT["arms"]]


def run_arm_gaps(got: dict, deferred) -> list[dict]:
    """The missing specs of every arm the freeze runs (the deferred arms' left out, never counted as covered)."""
    return [s for s in got["missing"] if s["arm"] not in deferred]


def deferred_lines(got: dict, specs: list[dict], deferred) -> list[str]:
    lines = []
    for arm, per in counts(specs).items():
        if arm not in deferred:
            continue
        for model, n in per.items():
            gap = sum(1 for s in got["missing"] if (s["arm"], s["model"]) == (arm, model))
            lines.append(f"deferred arm {arm}, {model}: {n - gap} of {n} required walks covered, {gap} missing; "
                         f"recorded, not required at this freeze (the draft's deferred_arms); complete coverage is a "
                         f"precondition of its later go (--require-complete)")
    return lines


def coverage_report(base=None, study_dir: Path = HERE) -> dict:
    """The --coverage reading in process: {"design", "specs", "entries", "got", "deferred"}; raises PlanRefused,
    RegisterUnreadable and the design readers' errors as --coverage refuses them."""
    design = design_in_force(study_dir)
    specs = plan_walks(design)
    base = Path(base) if base else walk_register.REHEARSALS
    entries = read_register(base, design)
    import pending_walk
    got = coverage(entries, specs, design,
                   pending_walk.uncounted_walks(base, [e["walk"] for e in entries], strict_walks(entries)))
    return {"design": design, "specs": specs, "entries": entries, "got": got, "deferred": deferred_arms(study_dir)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="The CP6 walk list, and which of its walks the register covers.",
                                 allow_abbrev=False)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="print the required walks")
    mode.add_argument("--coverage", action="store_true", help="print each required walk covered or missing")
    ap.add_argument("--require-complete", action="store_true", help="with --coverage: exit 1 on any missing walk")
    ap.add_argument("--require-run-arms", action="store_true",
                    help="with --coverage: exit 1 on any missing walk of an arm the freeze runs (deferred arms recorded)")
    ap.add_argument("--base", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.require_complete and not args.coverage:
        ap.error("--require-complete goes with --coverage")
    if args.require_run_arms and (not args.coverage or args.require_complete):
        ap.error("--require-run-arms goes with --coverage, without --require-complete")
    try:
        design = design_in_force()
        specs = plan_walks(design)
    except (PlanRefused, OSError, ValueError, KeyError) as exc:
        print(f"FAIL the walk plan cannot be derived: {exc}")
        return 2
    if args.list:
        print("\n".join(list_lines(specs, design)))
        return 0
    base = Path(args.base) if args.base else walk_register.REHEARSALS
    try:
        entries = read_register(base, design)
    except RegisterUnreadable as exc:
        print(f"FAIL {exc}")
        return 2
    import pending_walk
    got = coverage(entries, specs, design,
                   pending_walk.uncounted_walks(base, [e["walk"] for e in entries], strict_walks(entries)))
    print("\n".join(coverage_lines(got, specs, design, len(entries))))
    missing = got["missing"]
    if args.require_complete and missing:
        print("FAIL --require-complete: required walks are missing (the lines above name each)")
        return 1
    if args.require_complete:
        print("ok: every required walk is covered")
    if not args.require_run_arms:
        return 0
    deferred = deferred_arms()
    print("\n".join(deferred_lines(got, specs, deferred)))
    gaps = run_arm_gaps(got, deferred)
    if gaps:
        print(f"FAIL --require-run-arms: {len(gaps)} required walk(s) of the arms the freeze runs are missing "
              f"(the lines above name each)")
        return 1
    print("ok: every required walk of the arms the freeze runs is covered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
