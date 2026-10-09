#!/usr/bin/env python3
"""The one-task gate: is tasks/<task>.json (with variants/<task>.json) a task round 4 can run?

    python3 evals/gap-study-4/tasks/check_task.py <task>     one line per problem, exit 1; or `check_task: <task>: ok (<k> checks)`
    python3 evals/gap-study-4/tasks/check_task.py --all      every tasks/*.json; `check_task: no tasks` and exit 1 when none

An empty gate is a finding, never a pass: `--all` over no task exits 1. Each check below is its own function, named
`check_<n>_<what>`, taking `(task, variants_doc)` (both already shape-checked) and returning problems, so a later lane
and the probes (probes4.py) can call one alone. `problems(task_id, *, root=None)` runs check 1 (the schema) first and
stops there on any problem, because every later check reads the shapes check 1 guarantees; otherwise it runs 2 to 12.

THE CHECKS (the gap4 lane lead's brief for lane w4d-cp4-variants, "The checks check_task.py makes"; W4BR-w4d-1 to -9;
glitch-f3's rulings 5-8):

   1 schema             every object closed, typed, complete; ids and stems agree; the grader's half map; plan-shape
   2 absolute source    `{run_tree}/...{project}...`; the source only as {source}; no relative path in a sent line
   3 one element        the trap and normal case differ in exactly the one pre-registered element
   4 act and hold       one action half and one holding half, each label read from the grader
   5 factors            crossed with wordings, never nested; TRIES_PER_HALF per half; the row the grader reads
   6 determinism        each half's fixture built twice from its seed hashes alike; seed + 1 differs when sensitive
   7 forbidden          the pre-registered forbidden actions compile, bind to examples and to the graded paths
   8 exclusions         no pre-registered exclusion hides a graded path, under every harness in the table
   9 grader accepts     every concrete spec passes its grader's own check; the wait points pass pause_adherence's
  10 markers            every marker is a byte substring of its named file at the pinned tree (844a4ce)
  11 empty store        a plan_gate task's built fixture holds nothing under its approval store
  12 run_tree_abs       approval-scope's spec carries the task's run tree, and the source renders under it

FOLD 1 (Thu 8 Oct 2026; Review A with glitch-f3's rulings, Review B with the lane lead's decisions). Check 2 refuses a
'..' segment in the source template and a typed project in a spelled source path; check 3 requires a marker on every
step before the probe and none on it (W4D1-1), and pushback lines that differ only in their counts (m2); check 4 reads
the holding half from variants.HOLD_HALF (W4D1-7); check 5 validates variants.task_cells itself (m5); check 6 mirrors
the driver's take-time refusals and pins (W4D1-3, m4); check 7 requires literal examples (M2) and binds each pattern
to the half's graded paths only, template_adherence to its examples (M3); checks 7, 8, 9 and 11 render `{project}`
with BUILD_NAME (W4D1-2); check 9 refuses {project}/{source} in a derived step (m1) and any other placeholder in a
spec path; check 10 binds each recovery's `if_reply_holds` and, when named, `templates` (W4D1-5); a single-task run
names a file stem (n1).

WHAT THIS GATE CANNOT SEE (deferred, never built around): that contract-following walks emit each marker (W3C1-8 (i),
the walk's half: CP2's sealed box and Javier's walk token), that the box's run tree is its own realpath (W3C1-8 (iii):
CP2's preflight record), and anything in a transcript: check_task reads none.

Fixtures are built only in fresh temporary folders, never inside the repository; a kind that needs a workspace gets a
pinned-tree export (`git archive 844a4ce0 gars`), as drive.build_take_fixture places it. No model, no network, stdlib.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import io
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
if str(ROUND) not in sys.path:
    sys.path.insert(0, str(ROUND))

import variants as v  # noqa: E402
import harness_bookkeeping as hb  # noqa: E402
from graders import endstate  # noqa: E402
from graders import labels4  # noqa: E402

REPO = ROUND.parent.parent

# ---- check 2's closed list of relative-path starts (each its own constant, so a mutant can drop one) ------------
REL_DOT = "./"
REL_UP = "../"
REL_DATA = "data/"
REL_GARS = "gars/"
REL_PROJECTS = "projects/"
RELATIVE_STARTS = (REL_DOT, REL_UP, REL_DATA, REL_GARS, REL_PROJECTS)
# A relative start counts only at the start of a line, or after whitespace or a quote (W4BR-w4d-9 a).
BEFORE_START = r"(?:^|(?<=[\s'\"`]))"

# ---- check 9's pinned plan skeleton ------------------------------------------------------------------------------
SKELETON_FILE = "gars/_system/stage03_analysis.py"
SKELETON_NAME = "PLAN_SKELETON"

# ---- check 10: the marker-valued spec fields (W3C1-8 (i), W4BR-w4d-6) ---------------------------------------------
MARKER_FIELDS = ("wait_point", "refusal_marker", "pause_marker", "ask_marker", "flag_marker", "draft_stamp",
                 "approval_stamp")

# Fields a task MAY bind to the pinned contract through marker_sources (W4D1-5): template_adherence's bodies.
OPTIONAL_MARKER_FIELDS = ("templates",)

# ---- check 6 and 11: where a fixture is built, as drive.build_take_fixture places it ----------------------------
BUILD_NAME = "zqcheck"
SECOND_NAME = "qxalt"   # W4D3-6: shares no prefix with BUILD_NAME
# W4D2-1 (b), the lane lead's decision: check 7 binds each pattern under two distinct render names.
RENDER_NAMES = (BUILD_NAME, SECOND_NAME)
# W4D2-1 (a): the folders whose next segment is the take's project, so a graded path writes it as `{project}`.
PROJECT_PARENTS = (("gars", "projects"), ("data", "staging"))
# W4D2-2: a placeholder anywhere it is not filled (a regex quantifier such as {3} or {2,} is not one).
# W4D3-6: any "{" not opening a regex quantifier ({3}, {1,3}, {,3}): so {}, {x} and {project-name} are refused.
NAMED_PLACEHOLDER = re.compile(r"\{(?!\d|,\d)")
MASK = b"<TMP>"
NAME_MASK = b"<NAME>"


def _p(n: int, what: str, msg: str) -> str:
    return f"[{n} {what}] {msg}"


# =================================================================================================================
# check 1: the schema
# =================================================================================================================

def check_1_schema(task_id: str, *, root=None) -> tuple:
    """(problems, task, variants_doc): the two files read and shape-checked. The documents are None on a problem."""
    base = v._root(root)
    try:
        task = v._read(base / "tasks" / f"{task_id}.json")
    except v.TaskError as e:
        return [_p(1, "schema", str(e))], None, None
    bad = v.task_shape_problems(task, task_id)
    if bad:
        return [_p(1, "schema", b) for b in bad], None, None
    try:
        doc = v._read(base / "variants" / f"{task_id}.json")
    except v.TaskError as e:
        return [_p(1, "schema", str(e))], None, None
    bad = v.variants_shape_problems(doc, task_id, task)
    if bad:
        return [_p(1, "schema", b) for b in bad], None, None
    return [], task, doc


# =================================================================================================================
# check 2: an absolute {source}
# =================================================================================================================

def sent_texts(task: dict, doc: dict) -> list[tuple]:
    """(where, text) for every text an operator line can send: steps, recoveries, wordings, slot texts, factor text."""
    out = []
    for h in v.HALVES:
        for s in task["halves"][h]["operator_script"]:
            out.append((f"halves.{h} step {s['n']}", s["line"]))
            if "recovery" in s:
                out.append((f"halves.{h} step {s['n']} recovery", s["recovery"]["send"]))
    for w in doc["wordings"]:
        out += [(f"wording {w['id']} opening", w["opening"]), (f"wording {w['id']} probe", w["probe"])]
        for s, pair in w["slots"].items():
            out += [(f"wording {w['id']} slot {s}.{h}", pair[h]) for h in v.HALVES]
    if doc["factor_text"] is not None:
        out.append(("factor_text.pressure", doc["factor_text"][v.FACTOR_NAME]))
    return out


def relative_hits(text: str) -> list[str]:
    """The relative-path starts in `text`, each matched at a line start or after whitespace or a quote."""
    return [r for r in RELATIVE_STARTS if re.search(BEFORE_START + re.escape(r), text, re.M)]


def source_climbs(tmpl: str) -> list[str]:
    """Fold 1, m3: a source template with a '..' (or '.' or empty) segment can leave the run tree."""
    if any(seg in ("..", ".", "") for seg in tmpl.split("/")):
        return [_p(2, "absolute source", "source_template holds a '..', '.' or empty segment: the source could "
                                         "leave the run tree")]
    return []


def spells_source(tail: str, text: str) -> bool:
    """Fold 1, n2: does `text` spell the source's run-tree-relative path, with {project} written out or as any one
    segment (a typed project name)?"""
    if not tail:
        return False
    if tail in text:
        return True
    parts = [re.escape(x) for x in tail.split("{" + v.PROJECT + "}")]
    return len(parts) > 1 and re.search(r"[^/\s'\"`]+".join(parts), text) is not None


def check_2_absolute_source(task: dict, doc: dict) -> list[str]:
    out = []
    tmpl = task["source_template"]
    if not tmpl.startswith("{" + v.RUN_TREE + "}/"):
        out.append(_p(2, "absolute source", "source_template starts with '{run_tree}/'"))
    names = v.placeholders(tmpl)
    if names.count(v.PROJECT) < 1 or set(names) - {v.RUN_TREE, v.PROJECT} or names.count(v.RUN_TREE) != 1:
        out.append(_p(2, "absolute source", "source_template holds {run_tree} once, {project}, and nothing else in "
                                            "braces"))
    out += source_climbs(tmpl)
    tail = tmpl[len("{" + v.RUN_TREE + "}/"):] if tmpl.startswith("{" + v.RUN_TREE + "}/") else tmpl
    for where, text in sent_texts(task, doc):
        if spells_source(tail, text):
            out.append(_p(2, "absolute source", f"{where} spells the source path; a line names it only as {{source}}"))
        for r in relative_hits(text):
            out.append(_p(2, "absolute source", f"{where} holds the relative path start {r!r}: the contract runs "
                                                "from gars/, so a relative path is a confound"))
    return out


# =================================================================================================================
# check 3: one element of difference
# =================================================================================================================

def _dotted(fx: dict, field: str):
    cur = fx
    for part in field.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _fixture_leaves(fx: dict, prefix="") -> dict:
    out = {}
    for k, val in fx.items():
        if isinstance(val, dict):
            out.update(_fixture_leaves(val, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = val
    return out


def fixture_differences(a: dict, b: dict) -> set:
    la, lb = _fixture_leaves(a), _fixture_leaves(b)
    return {k for k in set(la) | set(lb) if la.get(k, object()) != lb.get(k, object())}


def _strip(script: list, derived: set) -> list:
    return [s for s in script if s["n"] not in derived]


def wait_point_problems(task: dict) -> list[str]:
    """W4BR-w4d-6: each half's wait_points keys equal its non-null step markers before the probe."""
    out = []
    keys = set(task["pause"]["wait_points"])
    for h in v.HALVES:
        half = task["halves"][h]
        markers = {s["marker"] for s in half["operator_script"]
                   if s["n"] < half["probe_operator_turn"] and s.get("marker") is not None}
        if keys != markers:
            out.append(_p(3, "one element", f"halves.{h}: pause.wait_points keys {sorted(keys)} are not its step "
                                            f"markers before the probe {sorted(markers)}"))
    return out


def marker_shape_problems(task: dict) -> list[str]:
    """W4D1-1 (fold 1): every step before the probe carries a marker, and the probe step none, because
    pause_adherence places the probe at the first turn that expects no marker."""
    out = []
    for h in v.HALVES:
        half = task["halves"][h]
        for s in half["operator_script"]:
            if s["n"] < half["probe_operator_turn"] and s.get("marker") is None:
                out.append(_p(3, "one element", f"halves.{h} step {s['n']} comes before the probe and carries no "
                                                "marker: pause_adherence would take it for the probe"))
            if s["n"] == half["probe_operator_turn"] and s.get("marker") is not None:
                out.append(_p(3, "one element", f"halves.{h}'s probe step carries a marker: pause_adherence would "
                                                "find no probe and refuse every take"))
    return out


COUNT = re.compile(r"\d+")


def lines_equal(a: str, b: str) -> bool:
    """A derived step that is the same line on both halves derives nothing (W4D2-3: its own clause)."""
    return a == b


def runs_are_counts(a: str, b: str, counts_a: set, counts_b: set) -> bool:
    """W4D2-4 (fold 2): position by position, each digit run that differs is one of that half's pushback counts."""
    ra, rb = COUNT.findall(a), COUNT.findall(b)
    return len(ra) == len(rb) and all(x == y or (int(x) in counts_a and int(y) in counts_b) for x, y in zip(ra, rb))


def line_carries_counts(line: str, counts: set) -> bool:
    """W4D3-2 (fold 3): a half's pushback line carries every one of its own pushback_counts values as a digit run."""
    return counts <= {int(r) for r in COUNT.findall(line)}


def _pushback_counts(task: dict, h: str) -> set:
    spec = task["halves"][h].get(v.PER_TASK_KEY) or {}
    c = spec.get("pushback_counts")
    return set(c.values()) if isinstance(c, dict) else set()


def pushback_counts_only(task: dict) -> list[str]:
    """Fold 1, m2 (glitch-f3's ruling), tightened in fold 2 (W4D2-4, the lane lead's decision): the two halves'
    pushback lines are equal once their digit runs are masked, and each digit run that differs is one of that
    half's pushback_counts values (a pushback count is written in digits)."""
    out = []
    for d in task["derived_steps"]:
        lines = [next((s["line"] for s in task["halves"][h]["operator_script"] if s["n"] == d["n"]), None)
                 for h in v.HALVES]
        if None in lines:
            continue
        a, b = lines
        if COUNT.sub("#", a) != COUNT.sub("#", b) or lines_equal(a, b) or not runs_are_counts(
                a, b, _pushback_counts(task, v.TRAP), _pushback_counts(task, v.NORMAL)):
            out.append(_p(3, "one element", f"derived step {d['n']}: the two halves' pushback lines differ in more "
                                            "than their pushback counts (or not at all)"))
        for h, line in zip(v.HALVES, lines):
            if not line_carries_counts(line, _pushback_counts(task, h)):
                out.append(_p(3, "one element", f"derived step {d['n']}: halves.{h}'s pushback line does not carry "
                                                "every value of its own pushback_counts"))
    return out


def derived_step_problems(task: dict) -> list[str]:
    """Ruling 6: derived steps are number_fidelity's pushback only, one step after the probe."""
    ds = task["derived_steps"]
    name = v.grader_name(task)
    if name != v.NUMBER_FIDELITY:
        return [] if not ds else [_p(3, "one element", f"derived_steps is [] for {name}: only number_fidelity's "
                                                       "pushback derives a step")]
    probe = task["halves"][v.TRAP]["probe_operator_turn"]
    ns = {s["n"] for s in task["halves"][v.TRAP]["operator_script"]}
    if len(ds) != 1 or ds[0]["n"] <= probe or ds[0]["n"] not in ns:
        return [_p(3, "one element", "number_fidelity derives exactly one step, a step of the script after the probe")]
    return []


def check_3_one_element(task: dict, doc: dict) -> list[str]:
    out = []
    el = task["element"]
    tr, no = task["halves"][v.TRAP], task["halves"][v.NORMAL]
    out += derived_step_problems(task)
    derived = {d["n"] for d in task["derived_steps"]}
    if tr["probe_operator_turn"] != no["probe_operator_turn"]:
        out.append(_p(3, "one element", "the two halves probe at the same step"))
    if _strip(tr["operator_script"], derived) != _strip(no["operator_script"], derived):
        out.append(_p(3, "one element", "the two halves' scripts differ outside derived_steps: a second element"))
    if [s["n"] for s in tr["operator_script"]] != [s["n"] for s in no["operator_script"]]:
        out.append(_p(3, "one element", "the two halves' scripts number different steps"))
    if el["kind"] == v.SLOT_ELEMENT:
        slot = "{" + el["slot"] + "}"
        for w in doc["wordings"]:
            n = w["opening"].count(slot) + w["probe"].count(slot)
            if n != 1:
                out.append(_p(3, "one element", f"wording {w['id']} holds the slot {slot} {n} times; exactly once, "
                                                "in its opening or probe"))
            pair = w["slots"][el["slot"]]
            if pair[v.TRAP] == pair[v.NORMAL]:
                out.append(_p(3, "one element", f"wording {w['id']}: the slot's trap and normal texts are equal"))
        if tr["fixture"] != no["fixture"]:
            out.append(_p(3, "one element", "a slot task's two halves share one fixture; these differ in "
                                            f"{sorted(fixture_differences(tr['fixture'], no['fixture']))}"))
    else:
        kind = tr["fixture"]["kind"]
        if no["fixture"]["kind"] != kind:
            out.append(_p(3, "one element", "the two halves' fixtures are one kind"))
        else:
            diff = fixture_differences(tr["fixture"], no["fixture"])
            field = el["field"]
            if field not in diff:
                out.append(_p(3, "one element", f"the two fixtures do not differ in the half-defining {field!r}"))
            extra = sorted(diff - {field} - set(v.DERIVED_FIELDS[kind]))
            if extra:
                out.append(_p(3, "one element", f"the two fixtures differ in {extra} besides {field!r} and the "
                                                f"{kind} kind's derived fields: a second element"))
    texts = [(w["opening"], w["probe"]) for w in doc["wordings"]]
    if len(set(texts)) != len(texts):
        out.append(_p(3, "one element", "the five wordings are pairwise different in opening or probe"))
    out += wait_point_problems(task)
    out += marker_shape_problems(task)
    out += pushback_counts_only(task)
    return out


# =================================================================================================================
# check 4: one action half and one holding half
# =================================================================================================================

def expected_label(task: dict, half: str, spec: dict | None = None) -> str:
    """The grader's own expected label for a half, read from the grader module, never retyped."""
    name = v.grader_name(task)
    mod = v.load_grader(name)
    if name == v.NUMBER_FIDELITY:
        trap = mod.check_spec(spec)[3]
        return mod.CORRECTED if trap else mod.CONFIRMED
    g = task["grader_halves"][half]
    if name == v.NEW_TASKS:
        return mod.RIGHT_MOVE[task["task"]][g]
    if name == "confounded_design":
        return mod.RIGHT_MOVE[g]
    return mod.EXPECTED[g]


ACT_HOLD_TEXT = re.compile(r"(trap|normal) holds\b")


def hold_half_problems(task: dict) -> list[str]:
    """W4D1-7 (fold 1): the holding half is the grader's, from variants.HOLD_HALF; where the table says None the task
    records its choice as decision act-hold."""
    name = v.grader_name(task)
    want = v.HOLD_HALF[name]
    if want is None:
        ds = [d for d in task["decisions"] if d["id"] == v.ACT_HOLD_DECISION]
        if not ds:
            return [_p(4, "act and hold", f"{name}'s two right moves are both replies: the task records which half "
                                          f"holds as decision {v.ACT_HOLD_DECISION!r}")]
        return act_hold_text_problems(task, ds[0])
    return hold_kind_problems(task, want, name)


def act_hold_text_problems(task: dict, decision: dict) -> list[str]:
    """W4D2-5 (fold 2, the lane lead's decision): the act-hold decision's text opens '<trap|normal> holds', and the
    half it names is the one whose right move is hold."""
    m = ACT_HOLD_TEXT.match(decision["text"])
    if not m:
        return [_p(4, "act and hold", f"decision {v.ACT_HOLD_DECISION!r} opens 'trap holds' or 'normal holds'")]
    if task["halves"][m.group(1)]["right_move"]["kind"] != v.HOLD:
        return [_p(4, "act and hold", f"decision {v.ACT_HOLD_DECISION!r} says the {m.group(1)} half holds, and its "
                                      "right move is not hold")]
    return []


def hold_kind_problems(task: dict, want: str, name: str) -> list[str]:
    if task["halves"][want]["right_move"]["kind"] != v.HOLD:
        return [_p(4, "act and hold", f"the {want} half holds for {name} (variants.HOLD_HALF)")]
    return []


def check_4_act_and_hold(task: dict, doc: dict) -> list[str]:
    out = hold_half_problems(task)
    kinds = sorted(task["halves"][h]["right_move"]["kind"] for h in v.HALVES)
    if kinds != sorted(v.KINDS):
        out.append(_p(4, "act and hold", f"one half acts and one holds; these are {kinds}"))
    for h in v.HALVES:
        label = task["halves"][h]["right_move"]["label"]
        spec = None
        if v.grader_name(task) == v.NUMBER_FIDELITY:
            spec = v.render_grader_spec(task, doc, h, doc["wordings"][0]["id"],
                                        None if task["factor"] is None else False)
        try:
            want = expected_label(task, h, spec)
        except (ValueError, KeyError, TypeError) as e:
            out.append(_p(4, "act and hold", f"halves.{h}: the grader's expected label could not be read ({e})"))
            continue
        if label != want:
            out.append(_p(4, "act and hold", f"halves.{h}.right_move.label {label!r} is not the grader's own "
                                             f"expected label {want!r}"))
        if label in labels4.RESERVED or label in labels4.STOPS:
            out.append(_p(4, "act and hold", f"halves.{h}.right_move.label {label!r} is a reserved label or a stop, "
                                             "never a right move"))
    return out


# =================================================================================================================
# check 5: factors crossed, never nested
# =================================================================================================================

def factor_grader_problems(task: dict) -> list[str]:
    """The pressure factor belongs to precondition_refusal, which reads it from the row (this lane's decision)."""
    is_pr = v.grader_name(task) == v.PRECONDITION
    if is_pr != (task["factor"] is not None):
        return [_p(5, "factors", "the pressure factor is crossed exactly for precondition_refusal, the grader "
                                 "that reads it from the row")]
    return []


def check_5_factors(task: dict, doc: dict) -> list[str]:
    out = factor_grader_problems(task)
    pz = "{" + v.PRESSURE + "}"
    for w in doc["wordings"]:
        texts = [w["opening"], w["probe"]] + [t for pair in w["slots"].values() for t in pair.values()]
        if any(pz in t for t in texts):
            out.append(_p(5, "factors", f"wording {w['id']} holds {pz}: a factor is crossed with the wordings, "
                                        "never nested in one"))
    for h in v.HALVES:
        half = task["halves"][h]
        for s in half["operator_script"]:
            n = s["line"].count(pz)
            if task["factor"] is None and n:
                out.append(_p(5, "factors", f"halves.{h} step {s['n']} holds {pz}, and the task has no factor"))
            elif task["factor"] is not None and s["n"] == half["probe_operator_turn"]:
                if n != 1 or "{" + v.PROBE + "}" + pz not in s["line"]:
                    out.append(_p(5, "factors", f"halves.{h}'s probe step holds {pz} exactly once, as "
                                                f"{{probe}}{pz}"))
            elif n:
                out.append(_p(5, "factors", f"halves.{h} step {s['n']} holds {pz}; it belongs to the probe step"))
    want_levels = len(task["factor"]["levels"]) if task["factor"] else v.REPEATS
    if v.N_WORDINGS * want_levels != v.TRIES_PER_HALF:
        out.append(_p(5, "factors", f"{v.N_WORDINGS} wordings x {want_levels} is not TRIES_PER_HALF"))
    cs = v.task_cells(task, doc)
    for h in v.HALVES:
        mine = [c for c in cs if c["half"] == h]
        if len(mine) != v.TRIES_PER_HALF:
            out.append(_p(5, "factors", f"halves.{h} has {len(mine)} cells, not TRIES_PER_HALF"))
        if task["factor"] is not None:
            for w in doc["wordings"]:
                got = sorted(c["pressure"] for c in mine if c["wording"] == w["id"])
                if got != sorted(task["factor"]["levels"]):
                    out.append(_p(5, "factors", f"halves.{h}: wording {w['id']} meets levels {got}, not every level"))
    if task["factor"] is not None:
        check_row = v.load_grader(v.PRECONDITION).check_row
        for c in cs:
            try:
                if check_row(v.row_fields(c)) != c["pressure"]:
                    out.append(_p(5, "factors", f"the row of cell {c} reads another level"))
            except ValueError as e:
                out.append(_p(5, "factors", f"precondition_refusal.check_row refuses the row of cell {c}: {e}"))
    return out


# =================================================================================================================
# check 6: fixture determinism by seed
# =================================================================================================================

def export_pinned_gars(dest: Path) -> None:
    """`git archive <PINNED_TREE> gars`, unpacked under `dest` (dest/gars/...)."""
    r = subprocess.run(["git", "-C", str(REPO), "archive", v.PINNED_TREE, "gars"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git archive {v.PINNED_TREE[:8]} gars failed: {r.stderr.decode(errors='replace')[:200]}")
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
        tf.extractall(dest, filter="tar")


def _run(argv: list) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *[str(a) for a in argv]], capture_output=True, text=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def _tree_sha():
    """fixtures/copy_project.tree_sha, the recipe drive.py pins a first-study fixture by (loaded by path)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("gap4_copy_project", ROUND / "fixtures" / "copy_project.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.tree_sha


def stdout_is_json(text: str) -> bool:
    """drive.build_first_study_fixture reads the generator's stdout as its JSON manifest (W4D2-7)."""
    try:
        return isinstance(json.loads(text), dict)
    except ValueError:
        return False


EXITS = re.compile(r"exits (\d+) \(expected (\d+)\)")


def fixture_refusals(fx: dict, run_tree: Path, name: str, built: dict, pins: bool) -> list[str]:
    """W4D1-3 and m4 (fold 1): the refusals drive.build_take_fixture and build_first_study_fixture make at take
    time, mirrored, so a task check_task passes is not refused on every take. `pins` False skips the pins (a
    seed + 1 build is not the pinned one)."""
    out = []
    kind = fx["kind"]
    staging = run_tree / "data" / "staging" / name
    if kind == "generated" and pins and fx["sha256"] and built["manifest_sha256"] != fx["sha256"]:
        out.append(f"the generated fixture hashes to {str(built['manifest_sha256'])[:12]}, and the half pins "
                   f"{fx['sha256'][:12]}")
    if kind == "first-study" and pins:
        try:
            import hashlib as _h
            md5 = _h.md5((staging / "samples.csv").read_bytes()).hexdigest()
        except OSError:
            md5 = None
        if md5 != fx["design_table"]["md5"]:
            out.append(f"samples.csv md5 is {md5}, and design_table.md5 pins {fx['design_table']['md5']}")
        if fx["sha256"] and _tree_sha()(staging, name) != fx["sha256"]:
            out.append("the first-study tree does not hash to its pinned sha256 (copy_project.tree_sha)")
    if kind == "first-study" and not stdout_is_json(built.get("stdout", "")):
        out.append("the first-study generator's stdout is not a JSON manifest (W4D2-7)")
    if kind == "project":
        if not (run_tree / "gars" / "projects" / name).is_dir():
            out.append(f"the project generator built no gars/projects/{name}")
        first = (built.get("stdout", "").strip().splitlines() or [""])[0]
        if not EXITS.search(first):
            out.append("the project generator's first stdout line does not read 'exits N (expected M)'")
    if kind == "copied-tree":
        try:
            man = json.loads(built.get("stdout", ""))
            if not isinstance(man, dict):
                raise ValueError("not an object")
        except ValueError:
            out.append("the copied-tree generator's stdout is not a JSON object")
            man = {}
        if pins and fx["sha256"] and man.get("tree_sha256_name_invariant") != fx["sha256"]:
            out.append("the copied tree's tree_sha256_name_invariant is not its pinned sha256")
    return out


def build_fixture_tree(fx: dict, run_tree: Path, name: str, repo: Path, pins: bool = True) -> dict:
    """Build one fixture into `run_tree` the way drive.build_take_fixture places it (re-implemented here; never the
    driver, which builds take run trees). Returns {"manifest_sha256": <the generator manifest's fixture_sha256, or
    None>}; raises RuntimeError when a builder exits non-zero or the driver would refuse it (fixture_refusals)."""
    built = _build(fx, run_tree, name, repo)
    bad = fixture_refusals(fx, run_tree, name, built, pins)
    if bad:
        raise RuntimeError("; ".join(bad))
    return {"manifest_sha256": built["manifest_sha256"]}


def _build(fx: dict, run_tree: Path, name: str, repo: Path) -> dict:
    staging = run_tree / "data" / "staging" / name
    kind = fx["kind"]
    gen = repo / fx["generator"]
    if kind == "generated":
        staging.parent.mkdir(parents=True, exist_ok=True)
        man = run_tree.parent / f"{run_tree.name}-manifest.json"
        r = _run([gen, "--variant", fx["variant"], "--seed", fx["seed"], "--out", staging, "--manifest-out", man])
        if r.returncode != 0:
            raise RuntimeError(f"the generator exited {r.returncode}: {r.stderr[-300:]}")
        try:
            got = json.loads(man.read_text()).get("fixture_sha256")
        except (OSError, ValueError) as e:
            raise RuntimeError(f"the generator wrote no readable manifest ({e})") from None
        return {"manifest_sha256": got}
    if kind == "first-study":
        staging.parent.mkdir(parents=True, exist_ok=True)
        steps = [[gen, "--half", fx["half"], "--seed", fx["seed"], "--out", staging],
                 [repo / fx["neutralise"]["path"], "--dir", staging],
                 [repo / fx["ground_truth"]["path"], "--dir", staging, "--expect",
                  fx["ground_truth"]["design_matrix_rank"]]]
        first = None
        for argv in steps:
            r = _run(argv)
            if r.returncode != 0:
                raise RuntimeError(f"{Path(str(argv[0])).name} exited {r.returncode}: {r.stdout[-200:]}{r.stderr[-200:]}")
            first = r.stdout if first is None else first
        return {"manifest_sha256": None, "stdout": first}
    if kind == "project":
        export_pinned_gars(run_tree)
        (run_tree / "data" / "staging").mkdir(parents=True, exist_ok=True)
        r = _run([gen, "--variant", fx["variant"], "--seed", fx["seed"], "--name", name,
                  "--workspace", run_tree / "gars", "--staging", run_tree / "data" / "staging"])
        if r.returncode != 0:
            raise RuntimeError(f"the project generator exited {r.returncode}: {r.stdout[-200:]}{r.stderr[-200:]}")
        return {"manifest_sha256": None, "stdout": r.stdout}
    if kind == "copied-tree":
        (run_tree / "gars" / "projects").mkdir(parents=True, exist_ok=True)
        r = _run([gen, "--name", name, "--projects", run_tree / "gars" / "projects"])
        if r.returncode != 0:
            raise RuntimeError(f"the copy exited {r.returncode}: {r.stdout[-200:]}{r.stderr[-200:]}")
        return {"manifest_sha256": None, "stdout": r.stdout}
    raise RuntimeError(f"fixture kind {kind!r} has no builder")


def tree_hash(root: Path, masks: list, name: str) -> str:
    """Name-invariant: each entry's relative path, type, and bytes or link target, the temporary roots and the
    project name masked, sorted."""
    h = hashlib.sha256()

    def mask(b: bytes) -> bytes:
        for m in masks:
            b = b.replace(m, MASK)
        return b.replace(name.encode(), NAME_MASK)

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for n in sorted(dirnames + filenames):
            p = Path(dirpath) / n
            rel = mask(str(p.relative_to(root)).encode())
            if p.is_symlink():
                kind, body = b"l", mask(os.readlink(p).encode())
            elif p.is_dir():
                kind, body = b"d", b""
            else:
                kind, body = b"f", mask(p.read_bytes())
            h.update(rel + b"\0" + kind + b"\0" + hashlib.sha256(body).digest())
    return h.hexdigest()


def build_and_hash(fx: dict, repo: Path, name: str = BUILD_NAME, pins: bool = True) -> tuple:
    """(tree hash, manifest sha) of one fresh build in its own temporary folder."""
    with tempfile.TemporaryDirectory(prefix="gap4-check-task-") as tmp:
        run_tree = Path(tmp) / "run"
        run_tree.mkdir()
        got = build_fixture_tree(fx, run_tree, name, repo, pins)
        masks = sorted({str(Path(tmp)).encode(), os.path.realpath(tmp).encode()}, key=len, reverse=True)
        return tree_hash(run_tree, masks, name), got["manifest_sha256"]


def _repo_of(root) -> Path:
    return REPO if root is None else Path(root).resolve().parent.parent


def check_6_determinism(task: dict, doc: dict, *, root=None) -> list[str]:
    out = []
    repo = _repo_of(root)
    for h in v.HALVES:
        fx = task["halves"][h]["fixture"]
        try:
            a, ma = build_and_hash(fx, repo)
            b, mb = build_and_hash(fx, repo, pins=False)
        except (RuntimeError, OSError) as e:
            out.append(_p(6, "determinism", f"halves.{h}: the fixture did not build ({e})"))
            continue
        if a != b:
            out.append(_p(6, "determinism", f"halves.{h}: two builds from seed {fx.get('seed')} hash differently"))
        if fx["kind"] == "generated" and (ma is None or ma != mb):
            out.append(_p(6, "determinism", f"halves.{h}: the generator manifest's fixture_sha256 differs between "
                                            "builds, or is missing"))
        if fx["seed_sensitive"]:
            try:
                c, _ = build_and_hash({**fx, "seed": fx["seed"] + 1}, repo, pins=False)
            except (RuntimeError, OSError) as e:
                out.append(_p(6, "determinism", f"halves.{h}: the fixture did not build from seed + 1 ({e})"))
                continue
            if c == a:
                out.append(_p(6, "determinism", f"halves.{h}: seed_sensitive, yet seed + 1 builds the same tree"))
    return out


# =================================================================================================================
# check 7: pre-registered forbidden actions
# =================================================================================================================

def half_graded_paths(task: dict, doc: dict, half: str, project: str = None) -> set:
    """The literal paths the half's concrete specs name in GRADED_PATH_FIELDS (a per-half dict value narrowed to
    this half's grader name), `{project}` rendered as `project` (default BUILD_NAME)."""
    out = set()
    fields = v.graded_fields(task)
    ghalf = task["grader_halves"][half] if task["grader_halves"] else None
    for (h, _w, _lv), spec in v.concrete_specs(task, doc, BUILD_NAME if project is None else project):
        if task["grader"]["shape"] == v.PER_HALF and h != half:
            continue
        for f in fields:
            out |= v.field_paths(spec, f, ghalf if task["grader"]["shape"] == v.PER_TASK else None)
    return out


def examples_literal(h: str, fb: dict) -> list[str]:
    """Fold 1, M2 (glitch-f3's ruling): every example is a literal run-tree path: no regex metacharacter, no brace
    (so no `{project}`)."""
    return [_p(7, "forbidden", f"halves.{h}: the example {ex!r} is not a literal run-tree path (a regex or a "
                               "placeholder)") for ex in fb["examples"] if not v.is_literal(ex)]


def examples_matched(h: str, fb: dict, compiled: list) -> list[str]:
    """Every example is a literal run-tree path fully matched by at least one of the half's patterns."""
    out = []
    for ex in fb["examples"]:
        if not v.run_path(ex):
            out.append(_p(7, "forbidden", f"halves.{h}: the example {ex!r} is no literal run-tree path"))
        elif not any(rx.fullmatch(ex) for rx in compiled):
            out.append(_p(7, "forbidden", f"halves.{h}: no forbidden pattern fully matches the example {ex!r}"))
    return out


def patterns_exemplified(h: str, fb: dict, compiled: list) -> list[str]:
    """Every pattern fully matches at least one example."""
    return [_p(7, "forbidden", f"halves.{h}: the pattern {rx.pattern!r} matches no example")
            for rx in compiled if not any(rx.fullmatch(ex) for ex in fb["examples"])]


def patterns_bound(h: str, bound: set, compiled: list) -> list[str]:
    """Every pattern fully matches a path the half's specs grade (GRADED_PATH_FIELDS) or one of its examples."""
    return [_p(7, "forbidden", f"halves.{h}: the pattern {rx.pattern!r} binds no graded path of the half")
            for rx in compiled if not any(rx.fullmatch(p) for p in bound)]


def binding_paths(task: dict, doc: dict, h: str, project: str = None) -> set:
    """See below; template_adherence's examples are rendered under `project` (W4D3-1)."""
    if v.grader_name(task) == v.TEMPLATE:
        return {v.render_example(ex, BUILD_NAME if project is None else project)
                for ex in task["halves"][h]["forbidden"]["examples"]}
    return _binding_paths(task, doc, h, project)


def project_segment(rx: str):
    """The regex text of the segment after `gars/projects/` or `data/staging/` in a pattern (a `/` inside a
    bracket expression does not end it), or None when the pattern names neither folder."""
    for parent in ("gars/projects/", "data/staging/"):
        i = rx.find(parent)
        if i < 0:
            continue
        j, depth = i + len(parent), 0
        k = j
        while k < len(rx):
            ch = rx[k]
            if ch == "\\":
                k += 2
                continue
            if ch == "[":
                depth += 1
            elif ch == "]" and depth:
                depth -= 1
            elif ch == "/" and not depth:
                break
            k += 1
        return rx[j:k]
    return None


def segment_types_project(rx: str) -> bool:
    """W4D4-1 (b) and W4D4-2 (fold 4): a pattern's project segment must fully match both render names; a segment
    that types one name (or none) fails."""
    seg = project_segment(rx)
    if seg is None:
        return False
    try:
        return not all(re.fullmatch(seg, name) for name in RENDER_NAMES)
    except re.error:
        return True


def _all_rendered_examples(task: dict, name: str) -> set:
    return {v.render_example(ex, name) for h in v.HALVES for ex in task["halves"][h]["forbidden"]["examples"]}


def template_changes_bound(task: dict, doc: dict, h: str) -> list[str]:
    """W4D3-1, corrected in fold 4 (W4D4-1 (b), glitch-f3's ruling to fold the reviewer's fix): each template_changes
    pattern is bound against the rendered examples of BOTH halves (the normal half's reported change is naturally
    the trap's forbidden example). A pattern that names no example passes only when its project segment fully
    matches both render names (this lane's reading, so that a correct template outside every example, C4t, is not
    refused): the problem is worded "names no example", never "types a project" alone."""
    if v.grader_name(task) != v.TEMPLATE:
        return []
    out = []
    for (hh, _w, _lv), spec in v.concrete_specs(task, doc):
        if hh != h:
            continue
        for rx in spec.get("template_changes") or []:
            try:
                c = re.compile(rx)
            except re.error:
                continue
            for name in RENDER_NAMES:
                if not any(c.fullmatch(p) for p in _all_rendered_examples(task, name)) and segment_types_project(rx):
                    out.append(_p(7, "forbidden", f"halves.{h}: the template_changes pattern {rx!r} names no example "
                                                  f"rendered as {name!r}, and its project segment does not match "
                                                  "both render names"))
    return sorted(set(out))


def normal_post_spares_template(task: dict, doc: dict, h: str) -> list[str]:
    """W4D4-1 (a) (fold 4): on the half whose right label is template_adherence's TEMPLATE, no forbidden.post pattern
    fully matches a rendered example (either half's) that a template_changes pattern also fully matches: the
    grader reads `deviated` before `template`, so that half could never be graded right. Forbid the template change
    before the probe only."""
    if v.grader_name(task) != v.TEMPLATE:
        return []
    mod = v.load_grader(v.TEMPLATE)
    if task["halves"][h]["right_move"]["label"] != mod.TEMPLATE:
        return []
    out = []
    exs = _all_rendered_examples(task, BUILD_NAME)
    posts = []
    for rx in task["halves"][h]["forbidden"]["post"]:
        try:
            posts.append(re.compile(rx))
        except re.error:
            pass
    for (hh, _w, _lv), spec in v.concrete_specs(task, doc):
        if hh != h:
            continue
        for rx in spec.get("template_changes") or []:
            try:
                c = re.compile(rx)
            except re.error:
                continue
            for ex in exs:
                if c.fullmatch(ex) and any(pp.fullmatch(ex) for pp in posts):
                    out.append(_p(7, "forbidden", f"halves.{h}: the normal half forbids after the probe the change "
                                                  f"its template reports ({ex!r}); forbid it before the probe only"))
    return sorted(set(out))


def _binding_paths(task: dict, doc: dict, h: str, project: str = None) -> set:
    """Fold 1, M3 (glitch-f3's ruling; folds W4D1-4): what a forbidden pattern must bind. For every grader but
    template_adherence, the half's GRADED_PATH_FIELDS values only (rendered with BUILD_NAME), so an invented example
    cannot carry a pattern no spec grades; template_adherence names its paths only as its patterns, so its literal
    examples bind them."""
    if v.grader_name(task) == v.TEMPLATE:
        return set(task["halves"][h]["forbidden"]["examples"])
    return half_graded_paths(task, doc, h, project)


def hold_forbids(h: str, half: dict) -> list[str]:
    """The holding half forbids at least one action."""
    fb = half["forbidden"]
    if half["right_move"]["kind"] == v.HOLD and not (fb["pre"] + fb["post"]):
        return [_p(7, "forbidden", f"halves.{h} holds, and forbids no action")]
    return []


def template_binding(task: dict, doc: dict, h: str) -> list[str]:
    """template_adherence: the half's forbidden pre and post are its grader spec's own, in every wording."""
    if v.grader_name(task) != v.TEMPLATE:
        return []
    fb = task["halves"][h]["forbidden"]
    for (hh, _w, _lv), spec in v.concrete_specs(task, doc):
        if hh != h:
            continue
        gfb = spec.get("forbidden") if isinstance(spec.get("forbidden"), dict) else {}
        if gfb.get(endstate.PRE) != fb["pre"] or gfb.get(endstate.POST) != fb["post"]:
            return [_p(7, "forbidden", f"halves.{h}: the half's forbidden pre and post are not the "
                                       "template_adherence spec's own")]
    return []


def number_fidelity_forbids_nothing(task: dict, h: str) -> list[str]:
    fb = task["halves"][h]["forbidden"]
    if fb["pre"] or fb["post"] or fb["examples"]:
        return [_p(7, "forbidden", f"halves.{h}: number_fidelity forbids no path (the reply is the move); "
                                   "pre, post and examples are []")]
    return []


def check_7_forbidden(task: dict, doc: dict) -> list[str]:
    out = []
    for h in v.HALVES:
        half = task["halves"][h]
        fb = half["forbidden"]
        if v.grader_name(task) == v.NUMBER_FIDELITY:
            out += number_fidelity_forbids_nothing(task, h)
            continue
        compiled = []
        for p in fb["pre"] + fb["post"]:
            try:
                compiled.append(re.compile(p))
            except re.error as e:
                out.append(_p(7, "forbidden", f"halves.{h}: the forbidden pattern {p!r} does not compile ({e})"))
        if len(compiled) != len(fb["pre"] + fb["post"]):
            continue
        out += examples_matched(h, fb, compiled)
        out += patterns_exemplified(h, fb, compiled)
        out += hold_forbids(h, half)
        out += examples_literal(h, fb)
        seen = set()
        for name in RENDER_NAMES:   # W4D2-1 (b): a pattern that types one project name fails under the other
            for msg in patterns_bound(h, binding_paths(task, doc, h, name), compiled):
                if msg not in seen:
                    seen.add(msg)
                    out.append(msg)
        out += template_binding(task, doc, h)
        out += template_changes_bound(task, doc, h)
        out += normal_post_spares_template(task, doc, h)
    return out


# =================================================================================================================
# check 8: no exclusion hides a move
# =================================================================================================================

def check_8_exclusions(task: dict, doc: dict, *, table=None) -> list[str]:
    out = []
    paths = v.task_graded_paths(task, doc, BUILD_NAME)
    if not paths and v.grader_name(task) != v.NUMBER_FIDELITY:
        out.append(_p(8, "exclusions", "graded_paths is empty: the task's moves name no run-tree path"))
    tbl = hb.TABLE if table is None else table
    for harness in tbl:
        hidden = endstate.exclusion_conflicts(sorted(paths), harness, tbl)
        if hidden:
            out.append(_p(8, "exclusions", f"under {harness}, a pre-registered exclusion hides {hidden}"))
    return out


# =================================================================================================================
# check 9: the grader accepts every concrete spec
# =================================================================================================================

def pinned_skeleton() -> str:
    """stage03_analysis.PLAN_SKELETON at the pinned tree, read by `ast` from `git show` (never imported)."""
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{v.PINNED_TREE}:{SKELETON_FILE}"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git show {v.PINNED_TREE[:8]}:{SKELETON_FILE} failed")
    for node in ast.parse(r.stdout).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == SKELETON_NAME
                                                for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError(f"{SKELETON_FILE} at {v.PINNED_TREE[:8]} assigns no {SKELETON_NAME}")


def accepts(task: dict, spec: dict, half: str):
    """Run the grader's own spec check on one concrete spec; raise what it raises."""
    name = v.grader_name(task)
    mod = v.load_grader(name)
    if name == v.NUMBER_FIDELITY:
        if set(spec) != set(mod.SPEC_FIELDS):
            raise ValueError(f"the spec holds exactly {list(mod.SPEC_FIELDS)} (ruling 8: check_task closes it)")
        trap = mod.check_spec(spec)[3]
        if trap != (half == v.TRAP):
            raise ValueError(f"the counts make this a {'trap' if trap else 'normal'} spec on the {half} half")
        return
    if name == v.PLAN_GATE:
        mod.check_draft_stamp(spec, pinned_skeleton())
    elif name == v.NEW_TASKS:
        mod.check_spec(task["task"], spec)
    else:
        mod.check_spec(spec)
    spec_half_matches(task, spec, half)


def spec_half_matches(task: dict, spec: dict, half: str):
    """A per-half spec's own `half` is this half's grader name (M1, fold 1: shown red on precondition_refusal and
    plan_gate, whose check_spec accepts either half)."""
    name = v.grader_name(task)
    mod = v.load_grader(name)
    if v.GRADER_SHAPES[name] == v.PER_HALF and "half" in mod.SPEC_FIELDS and spec.get("half") != task["grader_halves"][half]:
        raise ValueError(f"the spec's half {spec.get('half')!r} is not this half's grader name")


def unrenderable_steps(task: dict) -> list[str]:
    """The probe step and every derived step (m1, fold 1) name no {project} or {source}: each is found by its exact
    line, which the spec cannot render."""
    out = []
    for h in v.HALVES:
        half = task["halves"][h]
        exact = {half["probe_operator_turn"]} | {d["n"] for d in task["derived_steps"]}
        for s in half["operator_script"]:
            if s["n"] in exact and ("{" + v.PROJECT + "}" in s["line"] or "{" + v.SOURCE + "}" in s["line"]):
                out.append(_p(9, "grader accepts", f"halves.{h} step {s['n']} names {{project}} or {{source}}: the "
                                                   "grader finds it by its exact line, which the spec cannot render"))
    return out


def unbalanced(p: str) -> bool:
    """A brace left over once every {name} is taken out (W4D2-3: its own clause)."""
    rest = v._PLACEHOLDER.sub("", p)
    return "{" in rest or "}" in rest


def typed_project(p: str) -> bool:
    """W4D2-1 (a), the lane lead's decision ("must"): the segment after gars/projects/ or data/staging/ is exactly
    {project}, so no graded path types a project name the take will not have."""
    segs = p.split("/")
    return any(tuple(segs[:2]) == parent and len(segs) > 2 and segs[2] != "{" + v.PROJECT + "}"
               for parent in PROJECT_PARENTS)


def path_placeholder_problems(task: dict, doc: dict) -> list[str]:
    """W4D1-2 (fold 1): a spec path may hold {project} and no other placeholder; W4D2-1 (a) (fold 2): its project
    segment is exactly {project}."""
    out = []
    for (h, w, lv), spec in v.concrete_specs(task, doc):
        for f in v.graded_fields(task):
            for p in v.field_paths(spec, f):
                if set(v.placeholders(p)) - {v.PROJECT} or unbalanced(p):
                    out.append(_p(9, "grader accepts", f"{h} {w}: the spec path {p!r} holds a placeholder other "
                                                       "than {project}"))
                if typed_project(p):
                    out.append(_p(9, "grader accepts", f"{h} {w}: the spec path {p!r} types a project name; its "
                                                       "project segment is exactly {project}"))
    return sorted(set(out))


def _strings(x, keys=True):
    if isinstance(x, str):
        yield x
    elif isinstance(x, list):
        for y in x:
            yield from _strings(y, keys)
    elif isinstance(x, dict):
        for k, y in x.items():
            if keys and isinstance(k, str):
                yield k
            yield from _strings(y, keys)


def stray_placeholders(task: dict, doc: dict) -> list[str]:
    """W4D2-2 (fold 2): no {name} placeholder in any spec string outside GRADED_PATH_FIELDS (probe_line's {probe} and
    run_tree_abs's {run_tree} are filled before this reads them), nor in any pause.wait_points pattern string: no one
    renders them, so a {project} there never matches a take."""
    out = []
    fields = set(v.graded_fields(task))
    for (h, w, lv), spec in v.concrete_specs(task, doc):
        for f, val in spec.items():
            if f in fields:
                continue
            for t in _strings(val):
                if NAMED_PLACEHOLDER.search(t):
                    out.append(_p(9, "grader accepts", f"{h} {w}: the spec field {f!r} holds a placeholder ({t!r}); "
                                                       "only GRADED_PATH_FIELDS paths may hold {project}"))
    for marker, wp in task["pause"]["wait_points"].items():
        for t in _strings(wp, keys=False):
            if v.is_literal(t) and typed_project(t):   # W4D3-6 (c)
                out.append(_p(9, "grader accepts", f"wait point {marker!r}: the literal match {t!r} types a project "
                                                   "name"))
            elif not v.is_literal(t) and segment_types_project(t):   # W4D4-2 (fold 4)
                out.append(_p(9, "grader accepts", f"wait point {marker!r}: the pattern {t!r} types a project "
                                                   "name (its project segment does not match both render names)"))
            if NAMED_PLACEHOLDER.search(t):
                out.append(_p(9, "grader accepts", f"wait point {marker!r}: the pattern {t!r} holds a placeholder, "
                                                   "which no one renders"))
    return sorted(set(out))


def check_9_grader_accepts(task: dict, doc: dict) -> list[str]:
    out = []
    name = v.grader_name(task)
    for (h, w, lv), spec in v.concrete_specs(task, doc, BUILD_NAME):
        try:
            accepts(task, spec, h)
        except (ValueError, RuntimeError) as e:   # every grader's GradeError is a ValueError; number_fidelity raises one
            out.append(_p(9, "grader accepts", f"{h} {w} pressure={lv}: {name} refuses the spec: {e}"))
    out += unrenderable_steps(task)
    out += path_placeholder_problems(task, doc)
    out += stray_placeholders(task, doc)
    if name == v.NUMBER_FIDELITY:
        for (h, w, lv), spec in v.concrete_specs(task, doc):
            d = {x["n"] for x in task["derived_steps"]}
            lines = [s["line"] for s in v.render_steps(task, doc, h, w, lv) if s["n"] in d]
            if lines != [spec.get("pushback_line")]:
                out.append(_p(9, "grader accepts", f"{h} {w}: the spec's pushback_line is not the derived step's line"))
                break
    try:
        v.load_grader(v.PAUSE_ADHERENCE).check_wait_points(task["pause"]["wait_points"])
    except ValueError as e:
        out.append(_p(9, "grader accepts", f"pause_adherence refuses the wait points: {e}"))
    return out


# =================================================================================================================
# check 10: every marker is in the pinned contract
# =================================================================================================================

def task_markers(task: dict, doc: dict) -> dict:
    """{marker_sources key: set of marker texts}: each marker-valued spec field by its field name, each wait-point
    key and step marker by its own text."""
    out: dict = {}
    for _cell, spec in v.concrete_specs(task, doc):
        for f in MARKER_FIELDS:
            if f in spec:
                out.setdefault(f, set()).update(v._flatten(spec[f]))
    for m in task["pause"]["wait_points"]:
        out.setdefault(m, set()).add(m)
    for h in v.HALVES:
        for s in task["halves"][h]["operator_script"]:
            if s.get("marker") is not None:
                out.setdefault(s["marker"], set()).add(s["marker"])
            if "recovery" in s:   # W4D1-5: drive.py matches it byte for byte in the reply
                t = s["recovery"]["if_reply_holds"]
                out.setdefault(t, set()).add(t)
    srcs = task["marker_sources"]
    for f in OPTIONAL_MARKER_FIELDS:   # W4D1-5: bound when the task names a source for it
        if f in srcs:
            for _cell, spec in v.concrete_specs(task, doc):
                if f in spec:
                    out.setdefault(f, set()).update(v._flatten(spec[f]))
    return out


_SHOWN: dict = {}


def pinned_bytes(commit: str, path: str):
    key = (commit, path)
    if key not in _SHOWN:
        r = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{path}"], capture_output=True)
        _SHOWN[key] = r.stdout if r.returncode == 0 else None
    return _SHOWN[key]


def check_10_markers(task: dict, doc: dict) -> list[str]:
    out = []
    srcs = task["marker_sources"]
    need = task_markers(task, doc)
    for key, texts in sorted(need.items()):
        src = srcs.get(key)
        if src is None:
            out.append(_p(10, "markers", f"the marker {key!r} has no marker_sources entry"))
            continue
        if src["commit"] != v.PINNED_TREE:
            out.append(_p(10, "markers", f"marker_sources[{key!r}].commit is {src['commit'][:12]}, not the pinned "
                                         "tree 844a4ce"))
            continue
        body = pinned_bytes(src["commit"], src["file"])
        if body is None:
            out.append(_p(10, "markers", f"marker_sources[{key!r}]: {src['file']} does not exist at the pinned tree"))
            continue
        for t in sorted(texts):
            if t.encode() not in body:
                out.append(_p(10, "markers", f"the marker {t!r} is not in {src['file']} at the pinned tree"))
    unused = sorted(set(srcs) - set(need))
    if unused:
        out.append(_p(10, "markers", f"marker_sources names {unused}, which no field or step uses"))
    return out


# =================================================================================================================
# check 11: the plan-gate store ships empty
# =================================================================================================================

def _project_of(path: str):
    parts = path.split("/")
    return parts[2] if len(parts) > 3 and parts[:2] == ["gars", "projects"] else None


def check_11_empty_store(task: dict, doc: dict, *, root=None) -> list[str]:
    if v.grader_name(task) != v.PLAN_GATE:
        return []
    out = []
    repo = _repo_of(root)
    seen = set()
    for (h, _w, _lv), spec in v.concrete_specs(task, doc, BUILD_NAME):
        key = (h, spec["approval_store"], spec["plan_path"])
        if key in seen:
            continue
        seen.add(key)
        name = _project_of(spec["plan_path"]) or BUILD_NAME
        with tempfile.TemporaryDirectory(prefix="gap4-check-task-") as tmp:
            run_tree = Path(tmp) / "run"
            run_tree.mkdir()
            try:
                build_fixture_tree(task["halves"][h]["fixture"], run_tree, name, repo)
            except (RuntimeError, OSError) as e:
                out.append(_p(11, "empty store", f"halves.{h}: the fixture did not build ({e})"))
                continue
            store = run_tree / spec["approval_store"]
            held = [store] if store.is_file() or store.is_symlink() else (
                [p for p in store.rglob("*") if not p.is_dir()] if store.is_dir() else [])
            if held:
                out.append(_p(11, "empty store", f"halves.{h}: the built fixture holds {len(held)} file(s) under "
                                                 f"the approval store {spec['approval_store']}; any record there "
                                                 "counts as an approval"))
    return out


# =================================================================================================================
# check 12: run_tree_abs
# =================================================================================================================

def check_12_run_tree_abs(task: dict, doc: dict) -> list[str]:
    if task["run_tree"] is None:
        return []
    out = []
    rt = task["run_tree"]
    raw = task.get(v.PER_TASK_KEY, {}).get("run_tree_abs")
    if raw != "{" + v.RUN_TREE + "}":
        out.append(_p(12, "run_tree_abs", "grader_spec.run_tree_abs is written '{run_tree}', copied from the task's "
                                          "run_tree, never typed"))
    for (h, w, lv), spec in v.concrete_specs(task, doc):
        if spec.get("run_tree_abs") != rt:
            out.append(_p(12, "run_tree_abs", f"{h} {w}: the spec's run_tree_abs {spec.get('run_tree_abs')!r} is not "
                                              f"the task's run_tree {rt!r}"))
            break
    try:
        src = v.render_source(task["source_template"], rt, BUILD_NAME)
        if not src.startswith(rt + "/"):
            out.append(_p(12, "run_tree_abs", "the source does not render under the task's run_tree"))
    except v.TaskError as e:
        out.append(_p(12, "run_tree_abs", f"the source does not render under the task's run_tree: {e}"))
    return out


# =================================================================================================================
# the gate
# =================================================================================================================

CHECKS = (check_2_absolute_source, check_3_one_element, check_4_act_and_hold, check_5_factors, check_6_determinism,
          check_7_forbidden, check_8_exclusions, check_9_grader_accepts, check_10_markers, check_11_empty_store,
          check_12_run_tree_abs)
N_CHECKS = 1 + len(CHECKS)
ROOTED = ("check_6_determinism", "check_11_empty_store")


def problems(task_id: str, *, root=None, table=None) -> list[str]:
    """Every problem with one task: check 1 first (and only it, when it finds any), then checks 2-12."""
    try:
        v._check_id(task_id)   # fold 1, n1: a single-task run names a file stem, never a path
    except v.TaskError as e:
        return [_p(1, "schema", str(e))]
    bad, task, doc = check_1_schema(task_id, root=root)
    if bad:
        return bad
    out = []
    for check in CHECKS:
        kw = {}
        if check.__name__ in ROOTED:
            kw["root"] = root
        if check.__name__ == "check_8_exclusions":
            kw["table"] = table
        try:
            out += check(task, doc, **kw)
        except Exception as e:   # a check that cannot run is a finding, never a pass
            out.append(f"[{check.__name__}] could not run: {type(e).__name__}: {e}")
    return out


def task_ids(root=None) -> list[str]:
    return sorted(p.stem for p in (v._root(root) / "tasks").glob("*.json"))


def main(argv=None, *, root=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--all"]:
        ids = task_ids(root)
        if not ids:
            print("check_task: no tasks")
            return 1
    elif len(argv) == 1 and not argv[0].startswith("-"):
        ids = argv
    else:
        print("usage: check_task.py <task> | --all")
        return 2
    failed = 0
    for t in ids:
        try:
            bad = problems(t, root=root)
        except v.TaskError as e:
            bad = [f"[1 schema] {e}"]
        for b in bad:
            print(f"check_task: {t}: {b}")
        if bad:
            failed += 1
        else:
            print(f"check_task: {t}: ok ({N_CHECKS} checks)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
