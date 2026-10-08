#!/usr/bin/env python3
"""Round 4's statistical tables, as functions of graded take records and a design, re-derived on demand.

    python3 evals/gap-study-4/stats.py --check    validate every results record, derive every table twice, and
                                                  compare the stats block of RESULT.md byte for byte

WHAT IT READS. Graded take records (interface 11, below) from `results/*.json`, each file a JSON list of
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
               "raw": "right" | "wrong" | "stop"}  (None exactly when route is harness-error)}

The half words are `variants.HALVES` (lane w4d builds variants.py in parallel; it is not imported here, and a
later test binds the two). A stop (a label in labels4.RESERVED) is wrong under `failures` (the strict view),
`out` under `excluded` and `stop` under `raw`; any other label is right or wrong alike in all three. The
standing is the grader's own (`correct_in_view`), mapped by the pipeline lane; stats never re-grades.
This lane's decisions on the record: a `harness-error` record carries the label `harness-error` and views None
(it has no standing: it left the denominator); an `aborted` record carries the label `aborted` (graded, counted
against holding); `flagged-then-acted` is named unused in round 4 and refused; two records of one try are refused.

CELLS. The half-cell key is (arm, task, half, model, agent.harness); the try key adds (wording, repeat or
pressure). A Codex or Gemini arm is its own cell, never counted with another harness under one model name.

No model, no network, no BLAS, standard library only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
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

RESULTS_DIR = HERE / "results"
NO_TAKES = "no takes"


class StatsError(Exception):
    """A record, a results file or a design stats refuses to count."""


TAKE_FIELDS = ("arm", "task", "half", "model", "agent", "wording", "repeat", "pressure", "route", "cell_state",
               "label", "views")
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
    for f in ("arm", "task", "model", "wording", "label"):
        if not _text(r[f]):
            raise StatsError(f"{f} must be a non-empty string: {r[f]!r}")
    if r["half"] not in HALVES:
        raise StatsError(f"half {r['half']!r} is not one of {HALVES}")
    if "agent" in TAKE_FIELDS:   # the agent check is tied to the field list (a mutant drops both together)
        a = r["agent"]
        if not isinstance(a, dict) or set(a) != set(AGENT_FIELDS) or not all(_text(a[k]) for k in AGENT_FIELDS):
            raise StatsError(f"agent must be {{'harness': str, 'version': str}}, never defaulted: {a!r}")
    rep, pres = r["repeat"], r["pressure"]
    if rep is not None and (isinstance(rep, bool) or not isinstance(rep, int)):
        raise StatsError(f"repeat must be an int or None: {rep!r}")
    if pres is not None and not isinstance(pres, bool):
        raise StatsError(f"pressure must be a bool or None: {pres!r}")
    if not _one_level(r):
        raise StatsError("exactly one of repeat and pressure is None")
    route = r["route"]
    if route in NEVER_IN_RESULTS:
        raise StatsError(f"a {route} record never reaches results")
    if route not in labels4.ROUTES:
        raise StatsError(f"route {route!r} is not a labels4 route")
    if r["cell_state"] not in CELL_STATES:
        raise StatsError(f"cell_state {r['cell_state']!r} is not None or one of {labels4.CELL_STATES}")
    if r["label"] in UNUSED_LABELS:
        raise StatsError(f"{r['label']} is named unused in round 4's pre-registration")
    if route == labels4.HARNESS_ERROR:
        if r["label"] != labels4.HARNESS_ERROR or r["views"] is not None:
            raise StatsError("a harness-error record carries the label harness-error and views None")
        return r
    if r["label"] == labels4.HARNESS_ERROR:
        raise StatsError("the label harness-error belongs to the harness-error route only")
    if route == labels4.ABORTED and r["label"] != labels4.ABORTED:
        raise StatsError("an aborted record carries the reserved label aborted")
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


def level(r: dict):
    """The try's repeat or pressure level, tagged so a repeat and a pressure level never meet."""
    return ("repeat", r["repeat"]) if r["repeat"] is not None else ("pressure", r["pressure"])


def half_cell_key(r: dict) -> tuple:
    return (r["arm"], r["task"], r["half"], r["model"], r["agent"]["harness"])


def try_key(r: dict) -> tuple:
    return half_cell_key(r) + (r["wording"], level(r))


def check_records(records: list) -> list:
    """Every record valid, and no try twice."""
    seen = set()
    for r in records:
        validate_record(r)
        k = try_key(r)
        if k in seen:
            raise StatsError(f"two records of one try: {k}")
        seen.add(k)
    return records


def results_files(folder=RESULTS_DIR) -> list:
    folder = Path(folder)
    return sorted(folder.glob("*.json")) if folder.is_dir() else []


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
            return NO_TAKES
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


def _xn(c, word="right") -> str:
    return NO_TAKES if c == NO_TAKES else f"{c[word]} of {c['n']}"


def _iv(c) -> str:
    return "" if c == NO_TAKES else f"{c['lower']} to {c['upper']}"


def render_bounds(rows) -> str:
    out = ["### Counts with exact 0.95 bounds, per half-cell", ""]
    if rows == NO_TAKES:
        return "\n".join(out + [NO_TAKES, ""])
    out += ["Right of graded tries in each stop view, with the exact two-sided 0.95 Clopper-Pearson interval, "
            "each bound rounded outward to 0.001. A harness-error slot beyond its cap leaves the denominator.", "",
            "| Arm | Task | Model | Harness | Half | Stops as failures | bounds | Stops excluded | bounds "
            "| Stops raw (right, wrong, stop) | bounds | Harness errors | Cell state |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        raw = r["raw"]
        raw_txt = NO_TAKES if raw == NO_TAKES else f"{raw['right']}, {raw['wrong']}, {raw['stop']} of {raw['n']}"
        out.append(f"| {r['arm'] or NO_TAKES} | `{r['task']}` | `{r['model']}` | `{r['harness']}` | {r['half']} "
                   f"| {_xn(r['failures'])} | {_iv(r['failures'])} | {_xn(r['excluded'])} | {_iv(r['excluded'])} "
                   f"| {raw_txt} | {_iv(raw)} | {_left(r['harness_error'])} | {r['cell_state'] or ''} |")
    return "\n".join(out + [""])


def _left(k: int) -> str:
    return "none" if k == 0 else f"{k} left the denominator"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", required=True)
    ap.parse_args(argv)
    files = results_files()
    if not files:
        print("stats --check: no takes (0 results files); nothing was compared")
        return 0
    print("stats --check: the full check is not built yet")
    return 1


if __name__ == "__main__":
    sys.exit(main())
