#!/usr/bin/env python3
"""Round 4's statistical tables, as functions of graded take records and a design, re-derived on demand.

    python3 evals/gap-study-4/stats.py --check    validate every results record, derive every table twice, and
                                                  compare the stats block of RESULT.md byte for byte

WHAT IT READS. Graded take records (interface 11, below) from `records/*.json`, each file a JSON list of
records, and a design (a closed dict). The design is passed in by the caller; the CLI reads it from the frozen
pre-registration, `prereg.json`, under the key `stats_design`, and never from the draft (a number derived from a
file that can still change was not pre-registered). It never reads `study.ARMS`. It writes nothing:
`result.py` (the pipeline lane) emits every table from these functions and never recomputes one.

THE TAKE RECORD (closed; an unknown, missing or mistyped key is refused with StatsError):

    {"arm": str, "task": str, "half": "trap" | "normal", "model": exact id,
     "agent": {"harness": str, "version": str},          required, never defaulted
     "wording": str, "repeat": int | None, "pressure": bool | None,     exactly one of the two is None
     "route": a labels4.ROUTES string, final (never rehearsal or pause),
     "cell_state": None | labels4.INCOMPLETE_MECHANICAL,
     "label": str,
     "views": {"failures": "right" | "wrong", "excluded": "right" | "wrong" | "out",
               "raw": "right" | "wrong" | "stop"}  (None exactly when route is harness-error),
     "agent_events": the agent event rows among a graded take's winning rows, in AGENT_EVENTS order ([] otherwise),
     "ruled": bool, true when a committed human ruling touched the take's slot,
     "human_sample": bool, "human_why": [HUMAN_WHY id, ...]}   MAJOR 6 (lane pf1-l2b): the grader's flag and why

Pre-freeze review 1 (lane pf1-l2a, the Lane-orchestrator's approval of the fold plan, Sat 24 Oct 2026, under
Javier's standing delegation): MAJOR 5 routes a take graded when the agent's own act ended its CLI with a non-zero
exit or left a process alive at the quiescence cap (routing.json agent_event_rows), and MAJOR 8 counts the takes a
ruling touched; both are counted per half-cell in table 1b, route_events_table, in their own columns.

The half words are `variants.HALVES` (lane w4d builds variants.py in parallel; it is not imported here, and a
later test binds the two). A stop (a label in labels4.RESERVED) is wrong under `failures` (the strict view),
`out` under `excluded` and `stop` under `raw`; any other label is right or wrong alike in all three. The
standing is the grader's own (`correct_in_view`), mapped by the pipeline lane; stats never re-grades.
This lane's decisions on the record: a `harness-error` record carries the label `harness-error` and views None
(it has no standing: it left the denominator); an `aborted` record carries the label `aborted` (graded, counted
against holding); `flagged-then-acted` is named unused in round 4 and refused; two records of one try are refused.

CELLS. The half-cell key is (arm, task, half, model, agent.harness); the try key adds (wording, repeat or
pressure). A Codex or Gemini arm is its own cell, never counted with another harness under one model name.
A model runs in one arm per harness (refused otherwise), and every record's task and model must be in the design.

THE DESIGN (closed): {"tasks_that_run", "harness_models", "stronger_weaker", "cross_vendor", "alpha", "bootstrap":
{"seed", "reps"}, "power": {"seed", "sims", "bootstrap_reps", "wordings", "repeats", "grid": [{"stronger", "weaker",
"task_spread", "wording_spread"}]}, "floors": None | {task: text from probes4}}. Until build_draft.py writes the
pre-registration, tests supply designs.

THE TABLES, each a function, each generated and never typed:
  1b route_events_table   per half-cell, the graded takes each agent event routed, and the ruled takes.
  1 bounds_table      x right of n graded per half-cell and stop view, with intervals.clopper_pearson's exact
                      two-sided 0.95 bounds, rounded outward (lower floored, upper ceiled on the 0.001 grid).
  2 holds_table       every graded try right on both halves under the strict view, of the cell's printed n (a
                      harness-error slot beyond its cap leaves it); chance_of_holding prints p to the n for each
                      p in intervals.HOLD_P, exact, on the 0.001 grid (p = 0.95, n = 20 gives 0.358).
  3 paired_table      units right per wording, descriptive, with the one-habit floor from design.floors (with
                      none: "one-habit floor: from probes4, not yet run", never a typed number).
  4 sensitivity_table x right of n per wording and half.
  5 comparisons       the pre-registered families (CP5-requirements, D8 B2), each row labelled from FAMILIES.
  6 across_tasks      the paired difference over matched slots, a nested bootstrap seeded from design.bootstrap.
  7 power_table       a seeded simulation over design.power's grid applying exactly tables 5 and 6's tests.
  8 "no takes"        no records: every table prints `no takes`, never a zero; a cell with 0 graded records
                      prints `no takes` for that cell.

THE TEST UNIT (glitch-f3's ruling 3, Thu 8 Oct 2026, under Javier's delegation; glitch-f3's ruling, not the
lane's and not Javier's words). TEST_UNIT = "pair" is the ruling's word, and it means the unit: the trap record
and the normal record sharing (arm, task, model, agent.harness, wording, repeat or pressure), right when both
halves are right under the strict view. Never a task pair nor a model pair. Each model's n is the number of
complete units in its records; a unit with a missing half, or a harness-error half beyond its cap, leaves n and
is counted as incomplete. Units are compared by intervals.fisher_two_sided, Holm-adjusted in exact arithmetic
over the tasks that run (family_size: len(design.tasks_that_run), read, never a typed 10). Why the unit and not
the try: tries counted together let a one-habit reply score half of every count. In round 3 a constant 'Sure.'
scored 9 of 18 tries, while 'tasks with all six tries right' read Opus 1/3, Sonnet 1/3, Haiku 0/3. (Those
figures live here and in the lane report only, never in rendered output.)

THE FAMILIES. Per model pair within each harness, one exact test per task, Holm over the tasks that run; the
within-harness stronger-against-weaker contrast over the tasks that run, one per harness, Holm over the
contrasts (this lane's reading: the stricter of "its own family"); between each harness's stronger model, an
agent-system comparison, tested per task as above; every other cross-harness pair descriptive, with no test.
check_families refuses any row that would present a cross-harness pair as a model comparison.
The contrast's Fisher table counts units over the tasks that run as one table and so ignores the clustering by
task; table 6's nested bootstrap is the clustered reading beside it. design.harness_models lists only the models
whose comparisons are pre-registered: a record of any other model (optional arm C's, unless the pre-registration
lists it) is refused, never compared unplanned. The bounds are at intervals.ALPHA, the pre-registered 0.95;
design.alpha drives the tests. Any sentence
comparing models stays Javier's: stats prints numbers and family labels only.

THE CHECK. `--check` with no results files prints "stats --check: no takes (0 results files); nothing was
compared" and exits 0: that is not a pass on data, only the statement that there is nothing yet to compare.
Results files that hold no record print "stats --check: no takes (k results files, 0 records); nothing was
compared", exit 0, never PASS. A results folder holding any entry that is not a top-level *.json file (a
subfolder, another suffix; dot-named files that are not .json, such as .DS_Store, are ignored) exits 1, named.
With any results file present it validates every record, reads the design from prereg.json (a missing
pre-registration or design exits 1, named), derives every table twice and compares (determinism), and compares
RESULT.md's block between STATS_START and STATS_END byte for byte with render_block (a missing page, a page
without the markers, or a different block each exits 1, named).

No model, no network, no BLAS, standard library only.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import math
import random
import re
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    """A round 4 module by file path: never another round's same-named module (graders is a namespace package)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Lane E1's interval code, copied byte-identical (COPIED.d/w4e-cp5-stats.json). Its round 1-3 constants
# (TAKES_PER_HALF, ROUNDS, OUT) are never used here.
intervals = _load("gap4_intervals", HERE / "intervals.py")
labels4 = _load("gap4_labels4", HERE / "graders" / "labels4.py")

RESULTS_DIR = HERE / "records"
PREREG = HERE / "prereg.json"          # the frozen pre-registration only; never the draft
RESULT_PAGE = HERE / "RESULT.md"        # result.py's page; stats only reads its stats block
DESIGN_KEY = "stats_design"
STATS_START = "<!-- gap-study-4:stats -->"
STATS_END = "<!-- /gap-study-4:stats -->"
NO_TAKES_LINE = "stats --check: no takes (0 results files); nothing was compared"
NO_TAKES = "no takes"


class StatsError(Exception):
    """A record, a results file or a design stats refuses to count."""


TAKE_FIELDS = ("arm", "task", "half", "model", "agent", "wording", "repeat", "pressure", "route", "cell_state",
               "label", "views", "agent_events", "ruled", "human_sample", "human_why")
# MAJOR 5 (pre-freeze review 1): routing.json's agent_event_rows, in its order; tests/test_pf1_routing_rulings.py
# binds the two (stats reads no routing table).
AGENT_EVENTS = ("nonzero-exec-exit", "quiescence-cap-reached", "store-variable-assigned")   # + pre-freeze review 2 M1
# Pre-freeze review 1, MAJOR 6 (lane pf1-l2b, Sat 24 Oct 2026, under the lane orchestrator's approval of the fold
# plan): a take its grader sent to the human sample carries that flag into its record, appended after the twelve
# base fields (and, at the L6a merge, after lane pf1-l2a's agent_events and ruled) so the first eight (the
# identity drive.LAUNCH_FIELDS and takes read as TAKE_FIELDS[:8]) never move.
# human_sample is True exactly when the grader's own result says so; human_why names why, as a sorted list of
# distinct ids from HUMAN_WHY (the grader's human_check, a nested agent CLI, the two readers disagreeing, or the
# grader's own flag), empty exactly when human_sample is False. A record with no grade (aborted, harness-error)
# carries False and []. The words the grader wrote about the flag stay in its grade, never in a record.
HUMAN_CHECKS = ("ask-check", "cause-check", "count-check", "fix-check", "flag-check")
HUMAN_WHY = HUMAN_CHECKS + ("nested-agent-cli", "readers-disagree") + tuple(
    f"{g}-flag" for g in ("confounded_design", "new_tasks", "number_fidelity", "plan_gate", "precondition_refusal",
                          "scope_read", "template_adherence"))
AGENT_FIELDS = ("harness", "version")
HALVES = ("trap", "normal")                 # variants.HALVES
VIEWS = ("failures", "excluded", "raw")
VIEW_WORDS = {"failures": ("right", "wrong"), "excluded": ("right", "wrong", "out"), "raw": ("right", "wrong", "stop")}
STOP_VIEWS = {"failures": "wrong", "excluded": "out", "raw": "stop"}
STOP_LABELS = labels4.RESERVED
NEVER_IN_RESULTS = (labels4.REHEARSAL, labels4.PAUSE)
LEAVES_DENOMINATOR = (labels4.HARNESS_ERROR,)
UNUSED_LABELS = (labels4.FLAGGED_THEN_ACTED,)
CELL_STATES = (None,) + tuple(labels4.CELL_STATES)


def _text(v) -> bool:
    return isinstance(v, str) and v != ""


# An id, never free text: a task, model, wording, arm or harness name is printed in the published tables, and a
# wording's own text (a holdout wording above all) must never reach a results record (review round 1, finding 9).
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def _id(v) -> bool:
    return isinstance(v, str) and ID.fullmatch(v) is not None


# An agent version is printed in the Agents table: id-like, no spaces, pipes or slashes (W4E1-7; CP2 to confirm).
VERSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}")


def _check_agent(a) -> None:
    """agent is {"harness": an id, "version": an id-like pin}, required and never defaulted."""
    if (not isinstance(a, dict) or set(a) != set(AGENT_FIELDS) or not all(_text(a[k]) for k in AGENT_FIELDS)
                or not _id(a.get("harness"))):
        raise StatsError(f"agent must be {{'harness': str, 'version': str}}, never defaulted: {a!r}")
    version = a.get("version")
    if version is not None and VERSION_ID.fullmatch(version) is None:
        raise StatsError(f"agent.version must match {VERSION_ID.pattern}: {version!r}")


def _one_level(r: dict) -> bool:
    """Exactly one of repeat and pressure is None (variants.cells)."""
    return (r["repeat"] is None) != (r["pressure"] is None)


def validate_record(r) -> dict:
    """The record, or StatsError naming what is wrong with it."""
    if not isinstance(r, dict):
        raise StatsError(f"a take record is a dict, not {type(r).__name__}")
    if set(r) != set(TAKE_FIELDS):
        raise StatsError(f"take record keys: missing {sorted(set(TAKE_FIELDS) - set(r))}, "
                         f"unknown {sorted(set(r) - set(TAKE_FIELDS))}")
    for f in ("arm", "task", "model", "wording"):
        if not _id(r[f]):
            raise StatsError(f"{f} must be an id ({ID.pattern}): {r[f]!r}")
    if not _text(r["label"]):
        raise StatsError(f"label must be a non-empty string: {r['label']!r}")
    if r["half"] not in HALVES:
        raise StatsError(f"half {r['half']!r} is not one of {HALVES}")
    _check_agent(r.get("agent"))
    rep, pres = r["repeat"], r["pressure"]
    if rep is not None and (isinstance(rep, bool) or not isinstance(rep, int)):
        raise StatsError(f"repeat must be an int or None: {rep!r}")
    if rep is not None and rep < 0:
        raise StatsError(f"repeat must not be negative: {rep!r}")
    if pres is not None and not isinstance(pres, bool):
        raise StatsError(f"pressure must be a bool or None: {pres!r}")
    if not _one_level(r):
        raise StatsError("exactly one of repeat and pressure is None")
    route = r["route"]
    if route in NEVER_IN_RESULTS:
        raise StatsError(f"a {route} record never reaches results")
    if route not in labels4.ROUTES:
        raise StatsError(f"route {route!r} is not a labels4 route")
    _check_route_notes(r)
    if r["cell_state"] not in CELL_STATES:
        raise StatsError(f"cell_state {r['cell_state']!r} is not None or one of {labels4.CELL_STATES}")
    if r["label"] in UNUSED_LABELS:
        raise StatsError(f"{r['label']} is named unused in round 4's pre-registration")
    _check_human(r)
    if route == labels4.HARNESS_ERROR:
        if r["label"] != labels4.HARNESS_ERROR or r["views"] is not None:
            raise StatsError("a harness-error record carries the label harness-error and views None")
        return r
    if r["label"] == labels4.HARNESS_ERROR:
        raise StatsError("the label harness-error belongs to the harness-error route only")
    if (route == labels4.ABORTED) != (r["label"] == labels4.ABORTED):
        raise StatsError("the label aborted and the route aborted come together")
    v = r["views"]
    if not isinstance(v, dict) or set(v) != set(VIEWS):
        raise StatsError(f"views must hold exactly {VIEWS}: {v!r}")
    for view in VIEWS:
        if v[view] not in VIEW_WORDS[view]:
            raise StatsError(f"views.{view} {v[view]!r} is not one of {VIEW_WORDS[view]}")
    if r["label"] in STOP_LABELS:
        if v != STOP_VIEWS:
            raise StatsError(f"a stop ({r['label']}) is wrong, out and stop in the three views: {v!r}")
    elif len(set(v.values())) != 1 or v["failures"] not in ("right", "wrong"):
        raise StatsError(f"a graded non-stop label is right or wrong alike in all three views: {v!r}")
    return r


def _check_route_notes(r: dict) -> None:
    """MAJOR 5 and 8: agent_events is a list of AGENT_EVENTS ids, each once and in that order, on a graded record
    only; ruled is a bool."""
    ev = r["agent_events"]
    if not isinstance(ev, list) or not all(isinstance(e, str) for e in ev):
        raise StatsError(f"agent_events must be a list of agent event row ids: {ev!r}")
    if [e for e in AGENT_EVENTS if e in ev] != ev:
        raise StatsError(f"agent_events must name AGENT_EVENTS {AGENT_EVENTS}, each once and in that order: {ev!r}")
    if ev and r["route"] != labels4.GRADED:
        raise StatsError(f"an agent event routes a take graded; a {r['route']} record carries none: {ev!r}")
    if not isinstance(r["ruled"], bool):
        raise StatsError(f"ruled must be a bool: {r['ruled']!r}")


def _check_human(r: dict) -> None:
    """MAJOR 6 (lane pf1-l2b): human_sample a bool; human_why the sorted distinct HUMAN_WHY ids, empty exactly when
    the flag is False; a record with no grade (aborted, harness-error) is never flagged."""
    flag, why = r["human_sample"], r["human_why"]
    if type(flag) is not bool:
        raise StatsError(f"human_sample must be a bool: {flag!r}")
    if not isinstance(why, list) or any(w not in HUMAN_WHY for w in why) or why != sorted(set(why)):
        raise StatsError(f"human_why must be a sorted list of distinct ids from {HUMAN_WHY}: {why!r}")
    if flag != bool(why):
        raise StatsError(f"human_why names a reason exactly when human_sample is True: {flag!r}, {why!r}")
    if flag and r["route"] != labels4.GRADED:
        raise StatsError(f"only a graded take is sent to the human sample by its grader, not a {r['route']} record")


def level(r: dict):
    """The try's repeat or pressure level, tagged so a repeat and a pressure level never meet."""
    return ("repeat", r["repeat"]) if r["repeat"] is not None else ("pressure", r["pressure"])


def half_cell_key(r: dict) -> tuple:
    return (r["arm"], r["task"], r["half"], r["model"], r["agent"]["harness"])


def try_key(r: dict) -> tuple:
    return half_cell_key(r) + (r["wording"], level(r))


def check_records(records: list) -> list:
    """Every record valid, no try twice, and one kind of level (repeat or pressure) per task (W4E1-10)."""
    seen, kinds = set(), {}
    for r in records:
        validate_record(r)
        k = try_key(r)
        if k in seen:
            raise StatsError(f"two records of one try: {k}")
        seen.add(k)
        kinds.setdefault(r["task"], set()).add(level(r)[0])
    for task, got in kinds.items():
        if len(got) != 1:
            raise StatsError(f"task {task!r} carries both repeat and pressure levels; one kind per task")
    return records


def _ignored(p: Path) -> bool:
    """A dot-named regular file that is not .json in any case (.DS_Store, .gitkeep) is ignored; a dot-named .json
    is read as records (W4E2-3), and a dot-named folder or a dot-named .JSON file is never skipped (W4E3-1; both
    the lane lead's decisions)."""
    return p.is_file() and p.name.startswith(".") and not p.name.lower().endswith(".json")


def _strays(folder: Path) -> list:
    """Every entry of the results folder that is not a top-level *.json file (a subfolder, another suffix)."""
    return sorted(p.name for p in folder.iterdir()
                  if not _ignored(p) and not (p.is_file() and p.suffix == ".json"))


def results_files(folder=RESULTS_DIR) -> list:
    """The top-level *.json files; StatsError when the folder holds anything else, so no record goes unseen."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    strays = _strays(folder)
    if strays:
        raise StatsError(f"the results folder holds entries that are not top-level *.json files: {strays}")
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix == ".json" and not _ignored(p))


def load_results(folder=RESULTS_DIR) -> list:
    """Every record of every results file, validated; [] for a missing or empty folder."""
    out = []
    for path in results_files(folder):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise StatsError(f"{path.name}: unreadable: {e}") from e
        if not isinstance(data, list):
            raise StatsError(f"{path.name}: a results file is a JSON list of take records")
        out.extend(data)
    return check_records(out)


def standing(r: dict, view: str) -> str | None:
    """The record's word in one view; None when it left the denominator. A record without standing reads wrong
    (fail-closed: it can never count right)."""
    if r["route"] in LEAVES_DENOMINATOR:
        return None
    v = r["views"]
    return v[view] if isinstance(v, dict) else "wrong"


# ---- table 1: bounds per half-cell ---------------------------------------------------------------------------

def bound(x: int, n: int) -> tuple:
    """The exact two-sided 0.95 Clopper-Pearson interval on x right of n, each bound rounded outward."""
    lo, hi = intervals.clopper_pearson(x, n)
    return intervals.fmt(lo), intervals.fmt(hi)


def _arm_of(records: list) -> dict:
    """(model, harness) -> the one arm its records ran in; two arms for one model and harness are refused."""
    out = {}
    for r in records:
        out.setdefault((r["model"], r["agent"]["harness"]), set()).add(r["arm"])
    for (model, harness), arms in out.items():
        if len(arms) != 1:
            raise StatsError(f"{model} in {harness} has records in arms {sorted(arms)}; a model runs in one arm")
    return {k: next(iter(v)) for k, v in out.items()}


def _design_cells(records: list, design: dict) -> list:
    """Every half-cell key: those the records reached, then each design (task, half, model, harness) none reached,
    with the model's arm (None when no record of that model exists)."""
    keys = {half_cell_key(r) for r in records}
    reached = {k[1:] for k in keys}
    arms = _arm_of(records)
    for harness, models in design["harness_models"].items():
        for model in models:
            for task in design["tasks_that_run"]:
                for half in HALVES:
                    if (task, half, model, harness) not in reached:
                        keys.add((arms.get((model, harness)), task, half, model, harness))
    return sorted(keys, key=lambda k: tuple("" if x is None else x for x in k))


def _view_counts(rs: list, view: str):
    words = [standing(r, view) for r in rs]
    words = [w for w in words if w is not None]
    right = words.count("right")
    if view == "failures":
        n = len(words)
        return NO_TAKES if n == 0 else dict(zip(("right", "n", "lower", "upper"), (right, n, *bound(right, n))))
    if view == "excluded":
        out = words.count("out")
        n = len(words) - out
        if n == 0:
            return f"{_say(out)} stops excluded, none counted" if out else NO_TAKES
        return dict(zip(("right", "n", "lower", "upper", "out"), (right, n, *bound(right, n), out)))
    n = len(words)
    if n == 0:
        return NO_TAKES
    return {"right": right, "wrong": words.count("wrong"), "stop": words.count("stop"), "n": n,
            "lower": bound(right, n)[0], "upper": bound(right, n)[1]}


def bounds_table(records: list, design: dict):
    """Table 1: per half-cell and stop view, x right of n graded with its exact bounds; NO_TAKES for no records."""
    if not records:
        return NO_TAKES
    by = {}
    for r in records:
        by.setdefault(half_cell_key(r), []).append(r)
    rows = []
    for key in _design_cells(records, design):
        rs = by.get(key, [])
        arm, task, half, model, harness = key
        states = sorted({r["cell_state"] for r in rs if r["cell_state"]})
        rows.append({"arm": arm, "task": task, "half": half, "model": model, "harness": harness,
                     "harness_error": sum(1 for r in rs if r["route"] in LEAVES_DENOMINATOR),
                     "cell_state": states[0] if states else None,
                     **{view: _view_counts(rs, view) for view in VIEWS}})
    return rows


def route_events_table(records: list, design: dict):
    """Table 1b (pre-freeze review 1, MAJOR 5 and 8): per half-cell, its takes, the graded takes each agent event
    routed (its own column each), and the takes of a slot a committed ruling touched; NO_TAKES for no records."""
    if not records:
        return NO_TAKES
    by = {}
    for r in records:
        by.setdefault(half_cell_key(r), []).append(r)
    rows = []
    for key in _design_cells(records, design):
        rs = by.get(key, [])
        arm, task, half, model, harness = key
        rows.append({"arm": arm, "task": task, "half": half, "model": model, "harness": harness, "takes": len(rs),
                     **{e: sum(1 for r in rs if e in r["agent_events"]) for e in AGENT_EVENTS},
                     "ruled": sum(1 for r in rs if r["ruled"])})
    return rows


def render_route_events(rows) -> str:
    out = [TABLE_HEADINGS["route_events"], ""]
    if rows == NO_TAKES:
        return "\n".join(out + [NO_TAKES, ""])
    out += ["Graded takes the routing table graded because the agent's own act ended its CLI with a non-zero exit, "
            "left a process of its own alive at the quiescence cap, or assigned HOME or an agent CLI's store variable "
            "in a shell command with no nested agent found, each in its own column beside the take's ordinary "
            "reading in the tables below; and the takes of a slot a committed human ruling touched. Counts of takes.",
            "", "| Arm | Task | Model | Harness | Half | Takes | Non-zero exit (the agent's own exit) "
            "| Process alive at the quiescence cap | Store variable assigned | Ruled takes |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"{_cellname(r)} | {r['half']} | {_none(r['takes'])} | {_none(r['nonzero-exec-exit'])} "
                   f"| {_none(r['quiescence-cap-reached'])} | {_none(r['store-variable-assigned'])} "
                   f"| {_none(r['ruled'])} |")
    return "\n".join(out + [""])


def _xn(c, word="right") -> str:
    return c if isinstance(c, str) else f"{c[word]} of {c['n']}"


def _iv(c) -> str:
    return "" if isinstance(c, str) else f"{c['lower']} to {c['upper']}"


def render_bounds(rows) -> str:
    out = ["### Counts with exact 0.95 bounds, per half-cell", ""]
    if rows == NO_TAKES:
        return "\n".join(out + [NO_TAKES, ""])
    out += ["Right of graded tries in each stop view, with the exact two-sided 0.95 Clopper-Pearson interval, "
            "each bound rounded outward to 0.001. A harness-error slot beyond its cap leaves the denominator.", "",
            "| Arm | Task | Model | Harness | Half | Stops as failures | bounds | Stops excluded | bounds "
            "| Stops raw | bounds | Harness errors | Cell state |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        raw = r["raw"]
        raw_txt = (NO_TAKES if raw == NO_TAKES else
                   f"{raw['right']} right, {raw['wrong']} wrong, {raw['stop']} stop, of {raw['n']}")
        out.append(f"| {r['arm'] or NO_TAKES} | `{r['task']}` | `{r['model']}` | `{r['harness']}` | {r['half']} "
                   f"| {_xn(r['failures'])} | {_iv(r['failures'])} | {_xn(r['excluded'])} | {_iv(r['excluded'])} "
                   f"| {raw_txt} | {_iv(raw)} | {_left(r['harness_error'])} | {r['cell_state'] or ''} |")
    return "\n".join(out + [""])


def _left(k: int) -> str:
    return "none" if k == 0 else f"{k} left the denominator"



# ---- the design ------------------------------------------------------------------------------------------------

DESIGN_FIELDS = ("tasks_that_run", "harness_models", "stronger_weaker", "cross_vendor", "alpha", "bootstrap",
                 "power", "floors")
BOOTSTRAP_FIELDS = ("seed", "reps")
POWER_FIELDS = ("seed", "sims", "bootstrap_reps", "wordings", "repeats", "grid")
GRID_FIELDS = ("stronger", "weaker", "task_spread", "wording_spread")


def _int(v, least=0) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= least


def _texts(v, nonempty=True) -> bool:
    return (isinstance(v, list) and (v or not nonempty) and all(_text(x) for x in v) and len(set(v)) == len(v))


def _on_grid(v) -> Fraction:
    """A decimal string on the 0.001 grid between 0 and 1, as a Fraction."""
    if not isinstance(v, str):
        raise StatsError(f"a design probability is a decimal string, not {v!r}")
    try:
        f = Fraction(v)
    except (ValueError, ZeroDivisionError) as e:
        raise StatsError(f"not a decimal: {v!r}") from e
    if not 0 <= f <= 1 or (f * intervals.GRID).denominator != 1:
        raise StatsError(f"{v!r} is not on the 0.001 grid between 0 and 1")
    return f


def _closed(d, fields, what):
    if not isinstance(d, dict) or set(d) != set(fields):
        got = sorted(d) if isinstance(d, dict) else type(d).__name__
        raise StatsError(f"{what} must hold exactly {fields}: {got}")


def _canonical(f: Fraction) -> str:
    """The shortest decimal spelling of a grid value: 0.05, never 0.050000."""
    text = intervals.fmt(f).rstrip("0")
    return text + "0" if text.endswith(".") else text


def validate_design(d) -> dict:
    """The design, or StatsError naming what is wrong with it. Closed, like the record."""
    _closed(d, DESIGN_FIELDS, "the design")
    if not _texts(d["tasks_that_run"]) or not all(_id(t) for t in d["tasks_that_run"]):
        raise StatsError("tasks_that_run is a non-empty list of distinct task ids")
    hm = d["harness_models"]
    if not isinstance(hm, dict) or not hm or not all(_id(h) and _texts(m) and all(_id(x) for x in m)
                                                      for h, m in hm.items()):
        raise StatsError("harness_models maps each harness to a non-empty list of distinct model ids")
    sw = d["stronger_weaker"]
    if not isinstance(sw, dict):
        raise StatsError("stronger_weaker maps a harness to [stronger, weaker]")
    for h, pair in sw.items():
        if h not in hm or not _texts(pair) or len(pair) != 2 or not set(pair) <= set(hm[h]):
            raise StatsError(f"stronger_weaker[{h!r}] must be two distinct models of that harness: {pair!r}")
    for h, models in hm.items():
        if len(models) >= 2 and h not in sw:
            raise StatsError(f"harness {h!r} has {len(models)} models and no stronger_weaker entry (D8 B2: one "
                             f"contrast per harness)")
    cv = d["cross_vendor"]
    if not _texts(cv, nonempty=False) or sorted(cv) != sorted(pair[0] for pair in sw.values()):
        raise StatsError(f"cross_vendor is the stronger model of each harness: {cv!r}")
    if not isinstance(d["alpha"], str):
        raise StatsError("alpha is a decimal string")
    alpha = _on_grid(d["alpha"])
    if not 0 < alpha < 1:
        raise StatsError("alpha lies strictly between 0 and 1")
    if d["alpha"] != _canonical(alpha):
        raise StatsError(f"alpha is written in its shortest spelling, {_canonical(alpha)!r}, not {d['alpha']!r}")
    b = d["bootstrap"]
    _closed(b, BOOTSTRAP_FIELDS, "bootstrap")
    if not (_int(b["seed"]) and _int(b["reps"], 1)):
        raise StatsError("bootstrap seed is an int and reps a positive int")
    pw = d["power"]
    _closed(pw, POWER_FIELDS, "power")
    if not (_int(pw["seed"]) and all(_int(pw[k], 1) for k in ("sims", "bootstrap_reps", "wordings", "repeats"))):
        raise StatsError("power seed is an int; sims, bootstrap_reps, wordings and repeats positive ints")
    if not isinstance(pw["grid"], list) or not pw["grid"]:
        raise StatsError("power grid is a non-empty list")
    for point in pw["grid"]:
        _closed(point, GRID_FIELDS, "a power grid point")
        for k in GRID_FIELDS:
            _on_grid(point[k])
    fl = d["floors"]
    if fl is not None and (not isinstance(fl, dict) or not set(fl) <= set(d["tasks_that_run"])
                           or not all(_text(v) for v in fl.values())):
        raise StatsError("floors is None or maps tasks that run to the probes table's text")
    return d


def check_against_design(records: list, design: dict) -> None:
    """Every record's task runs, and its model is one of its harness's models in the design."""
    for r in records:
        h = r["agent"]["harness"]
        if r["task"] not in design["tasks_that_run"]:
            raise StatsError(f"task {r['task']!r} is not one of the tasks that run")
        if r["model"] not in design["harness_models"].get(h, ()):
            raise StatsError(f"model {r['model']!r} is not a design model of harness {h!r}")
    _arm_of(records)
    check_versions(records)


def check_versions(records: list) -> dict:
    """(harness, model) -> the one agent version its records carry; two versions for one model are refused."""
    out = {}
    for r in records:
        out.setdefault((r["agent"]["harness"], r["model"]), set()).add(r["agent"]["version"])
    for (harness, model), versions in out.items():
        if len(versions) != 1:
            raise StatsError(f"{model} in {harness} carries agent versions {sorted(versions)}; one pin per model")
    return {k: next(iter(v)) for k, v in out.items()}


def agents_table(records: list):
    """The agent field of every table: each (harness, model) with its pinned version."""
    if not records:
        return NO_TAKES
    return [{"harness": h, "model": m, "version": v} for (h, m), v in sorted(check_versions(records).items())]


def render_agents(rows) -> str:
    out = ["### Agents", ""]
    if rows == NO_TAKES:
        return "\n".join(out + [NO_TAKES, ""])
    out += ["Every cell below is keyed by its harness; each model ran at one pinned agent version.", "",
            "| Harness | Model | Agent version |", "|---|---|---|"]
    for r in rows:
        out.append(f"| `{r['harness']}` | `{r['model']}` | `{r['version']}` |")
    return "\n".join(out + [""])


def family_size(design: dict) -> int:
    """The per-task family: the tasks that run, read from the design, never typed."""
    return len(design["tasks_that_run"])


def _cells(records: list, design: dict) -> list:
    """Every (arm, task, model, harness), reached or in the design."""
    return sorted({(k[0], k[1], k[3], k[4]) for k in _design_cells(records, design)},
                  key=lambda k: tuple("" if x is None else x for x in k))


def _by_cell(records: list) -> dict:
    out = {}
    for r in records:
        out.setdefault((r["arm"], r["task"], r["model"], r["agent"]["harness"]), []).append(r)
    return out


def _counted(rs: list, view: str) -> list:
    """The words of the records that count in this view: harness-error left, `out` left."""
    return [w for w in (standing(r, view) for r in rs) if w is not None and w != "out"]


# ---- table 2: holds, beside the chance of holding -------------------------------------------------------------

HOLDS_VIEW = "failures"     # the strict view: stops count as failures
STATE_OVERRIDES_HOLDS = True   # a cell at its rehearsal or pause cap publishes its state, never yes or no


def holds_table(records: list, design: dict):
    """Per cell: every graded try right on both halves under the strict view, of the cell's printed n."""
    if not records:
        return NO_TAKES
    by = _by_cell(records)
    rows = []
    for key in _cells(records, design):
        rs = by.get(key, [])
        arm, task, model, harness = key
        halves = {half: _counted([r for r in rs if r["half"] == half], HOLDS_VIEW) for half in HALVES}
        words = halves["trap"] + halves["normal"]
        right, n = words.count("right"), len(words)
        if n == 0:
            verdict, right, n = NO_TAKES, None, None
        elif not all(halves.values()):
            empty = [h for h in HALVES if not halves[h]][0]
            verdict = f"cannot hold: the {empty} half has no graded try"
        else:
            verdict = "yes" if right == n else "no"
        states = sorted({r["cell_state"] for r in rs if r["cell_state"]})
        if states and STATE_OVERRIDES_HOLDS:
            verdict = states[0]
        rows.append({"arm": arm, "task": task, "model": model, "harness": harness, "right": right, "n": n,
                     "holds": verdict, "harness_error": sum(1 for r in rs if r["route"] in LEAVES_DENOMINATOR),
                     "cell_state": states[0] if states else None})
    return rows


def printed_ns(rows) -> list:
    return [] if rows == NO_TAKES else sorted({r["n"] for r in rows if isinstance(r["n"], int)})


def chance_of_holding(ns: list) -> list:
    """p to the n for each p in intervals.HOLD_P and each printed n: exact, then printed on the 0.001 grid."""
    return [{"n": n, "p": p, "chance": intervals.fmt_p(Fraction(p) ** n)} for n in ns for p in intervals.HOLD_P]


# ---- tables 3 and 4: per wording -------------------------------------------------------------------------------

SENSITIVITY_VIEW = "failures"
FLOOR_NOT_RUN = "one-habit floor: from probes4, not yet run"


def unit_right(trap_r: dict, normal_r: dict) -> bool:
    """The unit is right when both halves are right under the strict view."""
    return standing(trap_r, "failures") == "right" and standing(normal_r, "failures") == "right"


def _slots(records: list) -> dict:
    """(arm, task, model, harness) -> {(wording, level): {half: record}}."""
    out = {}
    for r in records:
        k = (r["arm"], r["task"], r["model"], r["agent"]["harness"])
        out.setdefault(k, {}).setdefault((r["wording"], level(r)), {})[r["half"]] = r
    return out


def _complete(halves: dict) -> bool:
    return set(halves) == set(HALVES) and all(r["route"] not in LEAVES_DENOMINATOR for r in halves.values())


def _lkey(item):
    (wording, (kind, value)), _ = item
    return (wording, kind, str(value))


def paired_table(records: list, design: dict):
    """Table 3: per cell and wording, the units right on both halves, of the complete units. Descriptive only."""
    if not records:
        return NO_TAKES
    slots = _slots(records)
    rows = []
    for key in _cells(records, design):
        arm, task, model, harness = key
        cell = slots.get(key, {})
        if not cell:
            rows.append({"arm": arm, "task": task, "model": model, "harness": harness, "wording": None,
                         "units_right": None, "units": NO_TAKES, "incomplete": 0})
            continue
        for wording in sorted({w for w, _ in cell}):
            items = [h for (w, _), h in sorted(cell.items(), key=_lkey) if w == wording]
            done = [h for h in items if _complete(h)]
            rows.append({"arm": arm, "task": task, "model": model, "harness": harness, "wording": wording,
                         "units_right": sum(1 for h in done if unit_right(h["trap"], h["normal"])),
                         "units": len(done) if done else NO_TAKES, "incomplete": len(items) - len(done)})
    return rows


def sensitivity_table(records: list, design: dict):
    """Table 4: per cell, wording and half, x right of n graded under the strict view."""
    if not records:
        return NO_TAKES
    by = _by_cell(records)
    rows = []
    for key in _cells(records, design):
        arm, task, model, harness = key
        rs = by.get(key, [])
        if not rs:
            rows.append({"arm": arm, "task": task, "model": model, "harness": harness, "wording": None,
                         "half": None, "right": None, "n": NO_TAKES})
            continue
        for wording in sorted({r["wording"] for r in rs}):
            for half in HALVES:
                words = _counted([r for r in rs if r["wording"] == wording and r["half"] == half], SENSITIVITY_VIEW)
                rows.append({"arm": arm, "task": task, "model": model, "harness": harness, "wording": wording,
                             "half": half, "right": words.count("right"), "n": len(words) if words else NO_TAKES})
    return rows


# ---- table 5: the pre-registered comparison families ---------------------------------------------------------

TEST_UNIT = "pair"   # glitch-f3's ruling 3: the word means the unit (one try's trap and normal record), see above
FAMILIES = ("within-harness model comparison",
            "within-harness stronger against weaker, over the tasks that run",
            "agent-system comparison",
            "descriptive, no test")
# The contrast family's short name in this module's prose (pre-freeze review 1, m14; lane pf1-l2b): a registered name,
# which lint_language excuses inside its exact spelling only, as it excuses the four labels above.
CONTRAST_NAME = "stronger-against-weaker"
# m14: table 5 splits by family so the agent-system rows (between harnesses) never sit under a model-comparison
# heading: the two within-harness families under TABLE_HEADINGS["comparisons"], the cross-harness ones under
# TABLE_HEADINGS["agent_system"].
WITHIN_HARNESS_FAMILIES = FAMILIES[:2]


def fisher(x1: int, n1: int, x2: int, n2: int) -> Fraction:
    """Table 5's one exact test (intervals.fisher_two_sided), the accessor every table and the power simulation call."""
    return intervals.fisher_two_sided(x1, n1, x2, n2)


def holm(ps: dict, m: int) -> dict:
    """Holm's step-down adjustment in exact rational arithmetic over a family of m; an untested member (None)
    still counts in m. Ties keep the given order."""
    tested = [(p, i, k) for i, (k, p) in enumerate(ps.items()) if p is not None]
    if len(tested) > m:
        raise StatsError(f"{len(tested)} tests in a family of {m}")
    out = {k: None for k in ps}
    running = Fraction(0)
    for rank, (p, _, k) in enumerate(sorted(tested)):
        running = max(running, min(Fraction(1), (m - rank) * p))
        out[k] = running
    return out


def unit_counts(records: list) -> dict:
    """(arm, task, model, harness) -> units right, complete units (n) and incomplete units (a half missing, or a
    harness-error half that left the denominator)."""
    out = {}
    for key, cell in _slots(records).items():
        done = [h for h in cell.values() if _complete(h)]
        out[key] = {"right": sum(1 for h in done if unit_right(h["trap"], h["normal"])), "n": len(done),
                    "incomplete": len(cell) - len(done)}
    return out


def family_of(ha: str, ma: str, hb: str, mb: str, design: dict) -> str:
    if ha == hb:
        return FAMILIES[0]
    sw = design["stronger_weaker"]
    if (ha in sw and hb in sw and sw[ha][0] == ma and sw[hb][0] == mb
            and ma in design["cross_vendor"] and mb in design["cross_vendor"]):
        return FAMILIES[2]
    return FAMILIES[3]


def _flat_models(design: dict) -> list:
    return [(h, m) for h, models in design["harness_models"].items() for m in models]


def _count(uc: dict, task, model: str, harness: str) -> dict:
    got = {"right": 0, "n": 0, "incomplete": 0}
    for (arm, t, m, h), c in uc.items():
        if m == model and h == harness and (task is None or t == task):
            for k in got:
                got[k] += c[k]
    return got


def _test(a: dict, b: dict):
    return fisher(a["right"], a["n"], b["right"], b["n"]) if a["n"] and b["n"] else None


def comparisons(records: list, design: dict):
    """Table 5: per model pair, one exact test per task on the unit, Holm over the tasks that run (within a
    harness, and between the stronger models as agent-system comparisons); one stronger-against-weaker contrast
    per harness over the tasks that run, Holm over the contrasts; every other cross-harness pair descriptive."""
    if not records:
        return NO_TAKES
    uc = unit_counts(records)
    alpha = Fraction(design["alpha"])
    m = family_size(design)
    rows = []
    for (ha, ma), (hb, mb) in itertools.combinations(_flat_models(design), 2):
        fam = family_of(ha, ma, hb, mb, design)
        pair_rows = []
        for task in design["tasks_that_run"]:
            row = {"family": fam, "harness_a": ha, "model_a": ma, "harness_b": hb, "model_b": mb, "task": task,
                   "a": _count(uc, task, ma, ha), "b": _count(uc, task, mb, hb)}
            pair_rows.append(row)
        if fam in (FAMILIES[0], FAMILIES[2]):
            ps = {i: _test(r["a"], r["b"]) for i, r in enumerate(pair_rows)}
            adj = holm(ps, m)
            for i, r in enumerate(pair_rows):
                r.update(_tested(ps[i], adj[i], m, alpha))
        rows += pair_rows
    contrasts = []
    for h, (strong, weak) in design["stronger_weaker"].items():
        contrasts.append({"family": FAMILIES[1], "harness_a": h, "model_a": strong, "harness_b": h,
                          "model_b": weak, "task": None, "a": _count(uc, None, strong, h),
                          "b": _count(uc, None, weak, h)})
    ps = {i: _test(r["a"], r["b"]) for i, r in enumerate(contrasts)}
    adj = holm(ps, len(contrasts))
    for i, r in enumerate(contrasts):
        r.update(_tested(ps[i], adj[i], len(contrasts), alpha))
    return rows + contrasts


def _tested(p, adjusted, m: int, alpha: Fraction) -> dict:
    if p is None:
        return {"p": NO_TAKES, "adjusted": NO_TAKES, "at_alpha": None, "family_size": m}
    return {"p": intervals.fmt_p(p), "adjusted": intervals.fmt_p(adjusted), "at_alpha": adjusted <= alpha,
            "family_size": m}


def check_families(rows, design: dict) -> None:
    """No table can present a cross-harness pair as a model comparison, nor test a descriptive pair."""
    if rows == NO_TAKES:
        return
    sw = design["stronger_weaker"]
    for r in rows:
        fam, ha, hb = r["family"], r["harness_a"], r["harness_b"]
        if fam not in FAMILIES:
            raise StatsError(f"family {fam!r} is not one of the four labels")
        if ha != hb and fam in FAMILIES[:2]:
            raise StatsError(f"a cross-harness pair ({ha}, {hb}) carries the label {fam!r}")
        if ha == hb and fam not in FAMILIES[:2]:
            raise StatsError(f"a within-harness pair carries the label {fam!r}")
        if fam == FAMILIES[2] and not (sw.get(ha, [None])[0] == r["model_a"] and sw.get(hb, [None])[0] == r["model_b"]):
            raise StatsError(f"an agent-system comparison is between each harness's stronger model: {r['model_a']}, "
                             f"{r['model_b']}")
        if fam == FAMILIES[3] and "p" in r:
            raise StatsError("a descriptive pair carries a test")


# ---- table 6: across tasks, the nested bootstrap -----------------------------------------------------------------

def _rng(seed) -> random.Random:
    """Every random draw comes from here, seeded from the design."""
    return random.Random(seed)


def _resample(rng: random.Random, tree: dict) -> list:
    """Tasks with replacement, then wordings within each drawn task, then levels within each drawn wording."""
    out = []
    tasks = list(tree)
    for t in rng.choices(tasks, k=len(tasks)):
        wordings = list(tree[t])
        for w in rng.choices(wordings, k=len(wordings)):
            values = list(tree[t][w].values())
            out.extend(rng.choices(values, k=len(values)))
    return out


def bootstrap_interval(rng: random.Random, tree: dict, reps: int, alpha: Fraction) -> tuple:
    """The alpha/2 and 1 - alpha/2 order statistics of the resampled paired difference, as Fractions."""
    draws = []
    for _ in range(reps):
        v = _resample(rng, tree)
        draws.append(Fraction(sum(v), len(v)))
    draws.sort()
    k = math.ceil(alpha / 2 * reps)            # the k-th order statistic from each end, outward
    lo = draws[max(0, k - 1)]
    hi = draws[min(reps - 1, reps - k)]
    return lo, hi


def _ceil3(v: Fraction) -> Fraction:
    return Fraction(math.ceil(v * intervals.GRID), intervals.GRID)


def signed(v: Fraction) -> str:
    """A Fraction on the 0.001 grid, with its sign."""
    return ("-" if v < 0 else "") + intervals.fmt(abs(v))


def _unit_tree(records: list) -> dict:
    """(harness, model) -> {task: {wording: {level: 1 or 0}}} over complete units."""
    out = {}
    for (arm, task, model, harness), cell in _slots(records).items():
        for (wording, lv), halves in cell.items():
            if _complete(halves):
                out.setdefault((harness, model), {}).setdefault(task, {}).setdefault(wording, {})[lv] = \
                    int(unit_right(halves["trap"], halves["normal"]))
    return out


def across_tasks(records: list, design: dict):
    """Table 6: for every tested pair, the paired difference in units right (first model minus second) over the
    slots both completed, with a nested bootstrap interval seeded from design.bootstrap.seed."""
    if not records:
        return NO_TAKES
    trees = _unit_tree(records)
    alpha = Fraction(design["alpha"])
    seed, reps = design["bootstrap"]["seed"], design["bootstrap"]["reps"]
    rows = []
    for (ha, ma), (hb, mb) in itertools.combinations(_flat_models(design), 2):
        fam = family_of(ha, ma, hb, mb, design)
        if fam not in (FAMILIES[0], FAMILIES[2]):
            continue
        ta, tb = trees.get((ha, ma), {}), trees.get((hb, mb), {})
        tree, unmatched = {}, 0
        for task in sorted(set(ta) | set(tb)):
            for wording in sorted(set(ta.get(task, {})) | set(tb.get(task, {}))):
                la, lb = ta.get(task, {}).get(wording, {}), tb.get(task, {}).get(wording, {})
                unmatched += len(set(la) ^ set(lb))
                for lv in sorted(set(la) & set(lb), key=lambda x: (x[0], str(x[1]))):
                    tree.setdefault(task, {}).setdefault(wording, {})[lv] = la[lv] - lb[lv]
        slots = sum(len(levels) for task in tree.values() for levels in task.values())
        row = {"family": fam, "harness_a": ha, "model_a": ma, "harness_b": hb, "model_b": mb, "slots": slots,
               "unmatched": unmatched}
        if slots == 0:
            row.update({"difference": NO_TAKES, "lower": NO_TAKES, "upper": NO_TAKES})
        else:
            observed = Fraction(sum(d for t in tree.values() for w in t.values() for d in w.values()), slots)
            lo, hi = bootstrap_interval(_rng(f"{seed}|{ha}|{ma}|{hb}|{mb}"), tree, reps, alpha)
            row.update({"difference": signed(intervals.round3(observed)), "lower": signed(intervals.floor3(lo)),
                        "upper": signed(_ceil3(hi))})
        rows.append(row)
    return rows


# ---- table 7: power for the clustered design ---------------------------------------------------------------

def power_table(design: dict) -> list:
    """For each pre-registered grid point, simulated pairs of models in one harness over the tasks that run: unit
    probabilities share a task offset and a wording offset (the clustering), drawn on the 0.001 grid with
    random.Random seeded from design.power.seed. Each simulation applies table 5's per-task exact tests with Holm
    over the tasks that run, table 5's stronger-against-weaker contrast (Holm over the design's contrasts, this
    one ranked first: the most demanding step), and table 6's nested bootstrap; the counts are the simulations in
    which each rejected at alpha (the bootstrap: its interval excludes zero). One process, exact integers."""
    pw = design["power"]
    alpha = Fraction(design["alpha"])
    tasks, wordings, repeats = family_size(design), pw["wordings"], pw["repeats"]
    per_task = wordings * repeats
    contrasts = max(1, len(design["stronger_weaker"]))
    grid = intervals.GRID
    rows = []
    for i, point in enumerate(pw["grid"]):
        rng = _rng(f"{pw['seed']}|power|{i}")
        ps_, pw_ = (int(_on_grid(point[k]) * grid) for k in ("stronger", "weaker"))
        ts, ws = (int(_on_grid(point[k]) * grid) for k in ("task_spread", "wording_spread"))
        cache = {}

        def exact(*a):
            if a not in cache:
                cache[a] = fisher(*a)
            return cache[a]

        any_task = contrast = boot = 0
        for _ in range(pw["sims"]):
            tree, ps, tot_a, tot_b = {}, {}, 0, 0
            for t in range(tasks):
                toff = rng.randint(-ts, ts)
                xa = xb = 0
                tree[t] = {}
                for w in range(wordings):
                    off = toff + rng.randint(-ws, ws)
                    qa, qb = min(grid, max(0, ps_ + off)), min(grid, max(0, pw_ + off))
                    tree[t][w] = {}
                    for r in range(repeats):
                        ua, ub = int(rng.randrange(grid) < qa), int(rng.randrange(grid) < qb)
                        xa, xb = xa + ua, xb + ub
                        tree[t][w][r] = ua - ub
                ps[t] = exact(xa, per_task, xb, per_task)
                tot_a, tot_b = tot_a + xa, tot_b + xb
            any_task += any(v <= alpha for v in holm(ps, tasks).values())
            contrast += holm({"c": exact(tot_a, tasks * per_task, tot_b, tasks * per_task)}, contrasts)["c"] <= alpha
            lo, hi = bootstrap_interval(rng, tree, pw["bootstrap_reps"], alpha)
            boot += lo > 0 or hi < 0
        rows.append({"point": dict(point), "sims": pw["sims"], "per_task_any": any_task, "contrast": contrast,
                     "bootstrap": boot})
    return rows


# ---- derive and render -----------------------------------------------------------------------------------------

TABLES = ("bounds", "route_events", "holds", "chance_of_holding", "paired", "per_wording", "comparisons", "across_tasks", "power")
TABLE_HEADINGS = {
    "bounds": "### Counts with exact 0.95 bounds, per half-cell",
    "route_events": "### Agent-caused routes and ruled takes, per half-cell",
    "holds": "### Holds, under the strict view",
    "chance_of_holding": "### The chance of holding at a given per-try accuracy",
    "paired": "### Paired results per wording (descriptive)",
    "per_wording": "### Per-wording sensitivity",
    "comparisons": "### Model comparisons within each harness, the pre-registered families",
    "agent_system": "### Agent-system comparisons between harnesses, the pre-registered families",
    "across_tasks": "### Across tasks: the paired difference, resampled by task, wording and repeat",
    "power": "### Power for the clustered design (simulated)",
}


def derive(records: list, design: dict) -> dict:
    """Every table from validated records and a validated design; NO_TAKES for every table when there are none."""
    validate_design(design)
    check_records(records)
    check_against_design(records, design)
    if not records:
        return {"takes": 0, "design": design, "agents": NO_TAKES, "tables": {t: NO_TAKES for t in TABLES}}
    holds = holds_table(records, design)
    comps = comparisons(records, design)
    check_families(comps, design)
    tables = {"bounds": bounds_table(records, design), "route_events": route_events_table(records, design),
              "holds": holds,
              "chance_of_holding": chance_of_holding(printed_ns(holds)),
              "paired": paired_table(records, design), "per_wording": sensitivity_table(records, design),
              "comparisons": comps, "across_tasks": across_tasks(records, design), "power": power_table(design)}
    return {"takes": len(records), "design": design, "agents": agents_table(records), "tables": tables}


def _say(k) -> str:
    """A bare count, never written as the digits a linter reads as a rate."""
    return "a hundred" if k == 100 else str(k)


def _cellname(r) -> str:
    return f"| {r['arm'] or NO_TAKES} | `{r['task']}` | `{r['model']}` | `{r['harness']}`"


def render_holds(rows) -> str:
    out = [TABLE_HEADINGS["holds"], ""]
    if rows == NO_TAKES:
        return "\n".join(out + [NO_TAKES, ""])
    out += ["Holds means every graded try right on both halves, stops counted as failures, of the cell's printed n "
            "(a harness-error slot beyond its cap leaves it).", "",
            "| Arm | Task | Model | Harness | Tries right, both halves | Holds | Harness errors | Cell state |",
            "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        xn = NO_TAKES if r["n"] is None else f"{r['right']} of {r['n']}"
        out.append(f"{_cellname(r)} | {xn} | {r['holds']} | {_left(r['harness_error'])} | {r['cell_state'] or ''} |")
    return "\n".join(out + [""])


def render_chance(rows) -> str:
    out = [TABLE_HEADINGS["chance_of_holding"], ""]
    if rows == NO_TAKES:
        return "\n".join(out + [NO_TAKES, ""])
    out += ["If every try were an independent draw with one per-try accuracy p, a cell of n tries would hold with "
            "chance p to the n, exact, printed on the 0.001 grid.", "",
            "| Tries in the cell | Per-try accuracy p | Chance of holding |", "|---|---|---|"]
    for r in rows:
        out.append(f"| {_say(r['n'])} | {r['p']} | {r['chance']} |")
    return "\n".join(out + [""])


def render_paired(rows, design: dict) -> str:
    out = [TABLE_HEADINGS["paired"], ""]
    if rows == NO_TAKES:
        return "\n".join(out + [NO_TAKES, ""])
    out += ["A unit is one try's trap and normal record (same wording and repeat or pressure level); it is right when "
            "both halves are right under the strict view. Descriptive only, no test.", ""]
    if design["floors"] is None:
        out.append(FLOOR_NOT_RUN)
    else:
        for task in design["tasks_that_run"]:
            text = design["floors"].get(task, "from probes4, not yet run")
            out.append(f"one-habit floor for `{task}`: {text}")
    out += ["", "| Arm | Task | Model | Harness | Wording | Units right on both halves | Incomplete units |",
            "|---|---|---|---|---|---|---|"]
    for r in rows:
        xn = NO_TAKES if r["units"] == NO_TAKES else f"{r['units_right']} of {r['units']}"
        inc = NO_TAKES if r["wording"] is None else _none(r["incomplete"])
        wording = f"`{r['wording']}`" if r["wording"] else ""
        out.append(f"{_cellname(r)} | {wording} | {xn} | {inc} |")
    return "\n".join(out + [""])


def render_sensitivity(rows) -> str:
    out = [TABLE_HEADINGS["per_wording"], ""]
    if rows == NO_TAKES:
        return "\n".join(out + [NO_TAKES, ""])
    out += ["Right of graded tries per wording and half, stops counted as failures.", "",
            "| Arm | Task | Model | Harness | Wording | Half | Right |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        xn = NO_TAKES if r["n"] == NO_TAKES else f"{r['right']} of {r['n']}"
        wording = f"`{r['wording']}`" if r["wording"] else ""
        out.append(f"{_cellname(r)} | {wording} | {r['half'] or ''} | {xn} |")
    return "\n".join(out + [""])


def _none(k: int) -> str:
    return "none" if k == 0 else _say(k)


def _side_incomplete(c) -> str:
    return NO_TAKES if not c["n"] and not c["incomplete"] else _none(c["incomplete"])


def _units_txt(c) -> str:
    return NO_TAKES if not c["n"] else f"{c['right']} of {c['n']}"


COMPARISON_HEADER = ("| Family | Harness | Model | Harness | Model | Task | Units right (first) | Units right (second) "
                     "| Incomplete units | Fisher p | Holm-adjusted p | At or under alpha |",
                     "|---|---|---|---|---|---|---|---|---|---|---|---|")


def render_comparisons(rows, design: dict) -> str:
    """Table 5 in two parts (m14): the within-harness families, then the agent-system rows between harnesses."""
    if rows == NO_TAKES:
        return "\n".join([TABLE_HEADINGS["comparisons"], "", NO_TAKES, "", TABLE_HEADINGS["agent_system"], "",
                          NO_TAKES, ""])
    out = [TABLE_HEADINGS["comparisons"], ""]
    out += [f"The test unit is one try's trap and normal record, right when both halves are right under the strict "
            f"view, compared by the two-sided Fisher exact test; per-task families are Holm-adjusted over the "
            f"{_say(family_size(design))} tasks that run, and each stronger-against-weaker contrast over the "
            f"{_say(len(design['stronger_weaker']))} stronger-against-weaker contrasts, in exact arithmetic, at "
            f"alpha {design['alpha']}. "
            f"Each row names its family; a descriptive row carries no test.", "", *COMPARISON_HEADER]
    out += [_comparison_line(r) for r in rows if r["family"] in WITHIN_HARNESS_FAMILIES]
    out += ["", TABLE_HEADINGS["agent_system"], "",
            "Between harnesses each row compares two agent systems, a model inside its own harness, never two models: "
            "the first model of each harness's stronger-against-weaker pair against another's, tested per task and "
            "Holm-adjusted over the tasks that run as above, and every other pair between harnesses descriptive, "
            "with no test.", "", *COMPARISON_HEADER]
    out += [_comparison_line(r) for r in rows if r["family"] not in WITHIN_HARNESS_FAMILIES]
    return "\n".join(out + [""])


def _comparison_line(r) -> str:
    task = "the tasks that run" if r["task"] is None else f"`{r['task']}`"
    inc = f"{_side_incomplete(r['a'])} and {_side_incomplete(r['b'])}"
    if "p" in r:
        at = "" if r["at_alpha"] is None else ("yes" if r["at_alpha"] else "no")
        tail = f"{r['p']} | {r['adjusted']} | {at}"
    else:
        tail = "no test | no test | no test"
    return (f"| {r['family']} | `{r['harness_a']}` | `{r['model_a']}` | `{r['harness_b']}` | `{r['model_b']}` "
            f"| {task} | {_units_txt(r['a'])} | {_units_txt(r['b'])} | {inc} | {tail} |")


def render_across(rows) -> str:
    out = [TABLE_HEADINGS["across_tasks"], ""]
    if rows == NO_TAKES:
        return "\n".join(out + [NO_TAKES, ""])
    out += ["For each tested pair, the difference in units right on both halves (first model minus second) over the "
            "slots both completed, with the 0.025 and 0.975 order statistics of a nested bootstrap (tasks with "
            "replacement, then wordings within a task, then repeats within a wording), seeded as pre-registered, "
            "each bound rounded outward.", "",
            "| Family | Harness | Model | Harness | Model | Slots both completed | Difference | Bootstrap bounds |",
            "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        slots = f"{r['slots']} of {r['slots'] + r['unmatched']}" if r["slots"] else NO_TAKES
        iv = "" if r["difference"] == NO_TAKES else f"{r['lower']} to {r['upper']}"
        out.append(f"| {r['family']} | `{r['harness_a']}` | `{r['model_a']}` | `{r['harness_b']}` | `{r['model_b']}` "
                   f"| {slots} | {r['difference']} | {iv} |")
    return "\n".join(out + [""])


def render_power(rows, design: dict) -> str:
    out = [TABLE_HEADINGS["power"], ""]
    if rows == NO_TAKES:
        return "\n".join(out + [NO_TAKES, ""])
    pw = design["power"]
    out += [f"Simulated pairs of models in one harness, {_say(family_size(design))} tasks, {_say(pw['wordings'])} "
            f"wordings and {_say(pw['repeats'])} repeats per task, unit accuracies sharing a task and a wording "
            f"offset; each simulation applies table 5's tests and table 6's bootstrap at alpha {design['alpha']}.", "",
            "| First model of the stronger-against-weaker pair | Second model | Task spread | Wording spread "
            "| Some per-task test after Holm | Contrast over the tasks that run | Bootstrap excludes zero |",
            "|---|---|---|---|---|---|---|"]
    for r in rows:
        pt = r["point"]
        k = lambda v: f"{v} of {r['sims']} simulations"
        out.append(f"| {pt['stronger']} | {pt['weaker']} | {pt['task_spread']} | {pt['wording_spread']} "
                   f"| {k(r['per_task_any'])} | {k(r['contrast'])} | {k(r['bootstrap'])} |")
    return "\n".join(out + [""])


def render_md(derived: dict) -> str:
    """The stats block's text (without its markers). Counts are written `x of n` and bounds as decimals."""
    t = derived["tables"]
    d = derived["design"]
    out = ["## Statistics", ""]
    out.append(render_agents(derived["agents"]))
    out.append(render_bounds(t["bounds"]))
    out.append(render_route_events(t["route_events"]))
    out.append(render_holds(t["holds"]))
    out.append(render_chance(t["chance_of_holding"]))
    out.append(_or_no_takes(t["paired"], lambda: render_paired(t["paired"], d), "paired"))
    out.append(render_sensitivity(t["per_wording"]))
    out.append(render_comparisons(t["comparisons"], d))                       # m14: both parts, no takes or not
    out.append(render_across(t["across_tasks"]))
    out.append(_or_no_takes(t["power"], lambda: render_power(t["power"], d), "power"))
    return "\n".join(out)


def _or_no_takes(rows, fn, table) -> str:
    return "\n".join([TABLE_HEADINGS[table], "", NO_TAKES, ""]) if rows == NO_TAKES else fn()


def render_block(derived: dict) -> str:
    return STATS_START + "\n" + render_md(derived) + STATS_END


# ---- the deferred arm's registered analysis (pre-freeze review 1, MAJOR 10; lane pf1-l2b, Sat 24 Oct 2026) --------
# deferred_arms.G.analysis (OD105, as registered): the original report adjusts the three per-harness contrasts with Holm
# at m = 3, arm G's contrast untested and still counted in m, and those values stand as published. So the original
# report's tables are derived from the records of the arms that are not deferred, under the full design (whose
# stronger_weaker still lists arm G's pair, so m stays 3); arm G's records, which exist only after Javier's committed
# go, reach only result.py's follow-up section, never these tables.

def original_records(records: list, deferred_arms) -> list:
    """The records the original report is derived from: every record whose arm is not a deferred arm."""
    held = set(deferred_arms)
    return [r for r in records if r["arm"] not in held]


def read_deferred_arms(prereg_path) -> set:
    """The deferred arms of the frozen pre-registration (its `deferred_arms` keys); none when it carries none. An
    unreadable file, or a `deferred_arms` that is not a map of arm to deferral, is refused, as prereg.deferred_arms
    refuses it (lane review 10), never read as no deferral."""
    try:
        pre = json.loads(Path(prereg_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise StatsError(f"the pre-registration cannot be read for its deferred arms: {e}") from e
    if not isinstance(pre, dict):
        raise StatsError("the pre-registration is not an object")
    table = pre.get("deferred_arms", {})
    table = {} if table is None else table
    if not isinstance(table, dict) or not all(isinstance(e, dict) and e.get("status") == "deferred"
                                              for e in table.values()):
        raise StatsError("deferred_arms maps an arm to its deferral")
    return set(table)


# ---- the check -------------------------------------------------------------------------------------------------

def read_design(prereg_path):
    """(design, None) from the frozen pre-registration, or (None, the named problem)."""
    path = Path(prereg_path)
    if not path.is_file():
        return None, f"no frozen pre-registration ({path.name}) to read the design from"
    try:
        pre = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, f"{path.name} is unreadable: {e}"
    if not isinstance(pre, dict) or DESIGN_KEY not in pre:
        return None, f"{path.name} carries no {DESIGN_KEY}"
    return pre[DESIGN_KEY], None


def _first_difference(a: str, b: str) -> str:
    for i, (x, y) in enumerate(zip(a.splitlines(), b.splitlines()), 1):
        if x != y:
            return f"line {i}"
    return f"length ({len(a.splitlines())} against {len(b.splitlines())} lines)"


def check(results_dir=RESULTS_DIR, prereg_path=PREREG, page_path=RESULT_PAGE):
    """(exit code, lines). With no results files: the no-takes line and 0, which is not a pass on data."""
    try:
        files = results_files(results_dir)
    except StatsError as e:
        return 1, [f"stats --check: FAIL results folder: {e}"]
    if not files:
        return 0, [NO_TAKES_LINE]
    try:
        records = load_results(results_dir)
    except StatsError as e:
        return 1, [f"stats --check: FAIL record: {e}"]
    if not records:   # W4E1-9: files that hold no record are no takes, never a pass
        return 0, [f"stats --check: no takes ({len(files)} results files, 0 records); nothing was compared"]
    design, problem = read_design(prereg_path)
    if problem:
        return 1, [f"stats --check: FAIL no design: {problem}"]
    try:
        original = original_records(records, read_deferred_arms(prereg_path))  # MAJOR 10: the original report's
        first, second = derive(original, design), derive(original, design)
    except StatsError as e:
        return 1, [f"stats --check: FAIL record or design: {e}"]
    block = render_block(first)
    if json.dumps(first, sort_keys=True) != json.dumps(second, sort_keys=True) or block != render_block(second):
        return 1, ["stats --check: FAIL not deterministic: two derivations of the same records differ"]
    page = Path(page_path)
    if not page.is_file():
        return 1, [f"stats --check: FAIL no RESULT.md: {len(records)} records and no page to compare"]
    text = page.read_text(encoding="utf-8")
    if text.count(STATS_START) != 1 or text.count(STATS_END) != 1 or text.index(STATS_START) > text.index(STATS_END):
        return 1, [f"stats --check: FAIL no stats block: RESULT.md must carry {STATS_START} ... {STATS_END} once"]
    have = text[text.index(STATS_START):text.index(STATS_END) + len(STATS_END)]
    if have != block:
        return 1, [f"stats --check: FAIL the stats block differs from what stats derives, first at "
                   f"{_first_difference(have, block)}"]
    return 0, [f"stats --check: PASS ({len(records)} records from {len(files)} results files; the stats block "
               f"matches)"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", required=True)
    ap.parse_args(argv)
    code, lines = check()
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
