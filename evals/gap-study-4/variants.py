#!/usr/bin/env python3
"""Round 4's task specs and wordings: the schema every task lane writes, and the API that turns one task into its cells.

    import variants
    variants.cells("<task>")                                   every (half, wording, repeat or pressure level)
    variants.operator_steps("<task>", "trap", "w1", pressure=True)   the half's script, ready for the driver's render
    variants.grader_spec("<task>", "normal", "w3")             the concrete spec, in the grader's own shape

THE ONE-TASK GATE is `tasks/check_task.py`; this module holds the shapes it starts from (its check 1, the schema) and
the rendering every later lane (the driver, the batch, the probes) reads. Interface 10 of the gap4 lane lead's brief
for lane w4d-cp4-variants is the authority; glitch-f3's rulings 5-8 (Thu 8 Oct 2026, under Javier's delegation) bind.

CANONICAL HALVES. `HALVES = ("trap", "normal")`. Cells, rows and every later record use these two words. Each task maps
them onto its grader's own half names in `grader_halves`, fixed per grader, never chosen (ruling 5): `trap` is the
grader's first half and `normal` its second (`positive`/`control` for confounded_design and new_tasks), and the map is
null for number_fidelity, which takes no half and derives the trap from its counts.

THE TWO FILES. `tasks/<task>.json` (schema `gap4-task/1`) and `variants/<task>.json` (schema `gap4-variants/1`). Every
level is a closed object: an unknown key is refused, a missing key is refused, nothing is defaulted. The shapes are
the module constants below (TASK_KEYS, HALF_KEYS, STEP_KEYS, RECOVERY_KEYS, FIXTURE_KEYS, WORDING_KEYS, ...); the
brief's interface 10 states them in prose. The step and fixture objects keep round 3's field names, because the copied
driver and checker read them (`drive.py` 780-1046, `check_take.py` 731-732 and 1033-1070 and 1600-1660 at 48f10056;
`tests/test_variants.py` binds each name to those lines). One reading is this lane's own: interface 10 lists a step as
`{"n", "line", "marker"?, "recovery"?, "if_reply_holds"?}`, while the readers it cites read `if_reply_holds` inside the
recovery (`rec["if_reply_holds"]`, `rec["send"]`, `rec.get("at_most", 1)`); a step here carries `recovery` as
`{"if_reply_holds", "send", "at_most"?}`, the readers' shape, and no `if_reply_holds` of its own.

PLACEHOLDERS. In a scripted line: `{opening}` (only in step 1), `{probe}` (only in the probe step), `{pressure}` (only
in the probe step, written `{probe}{pressure}`, only with the factor), `{project}` and `{source}` (left for the driver's
render). In a wording: the element slot. Nothing else in braces. `{pressure}` misplaced is check 5's finding, so the
schema lets that one name through to it.

THE PRESSURE FACTOR (W4BR-w4d-4). Level `true` renders `PRESSURE_SEPARATOR + factor_text.pressure` where `{pressure}`
stands, level `false` the empty string. Factors are crossed with wordings, never nested: every wording meets every
level, so a factor task has `N_WORDINGS` x 2 cells per half and a task with none `N_WORDINGS` x `REPEATS`; both are
`TRIES_PER_HALF`.

GRADER SPECS. A per-half grader keeps its spec in each half (`halves.<h>.grader_spec`), a per-task grader one spec at
the top (`grader_spec`). The probe line is never typed into a spec: it is written `"{probe}"` (per half) or
`{"<grader half>": "{probe}", ...}` (per task) and `grader_spec()` fills it with the line as sent. approval-scope's
`run_tree_abs` is written `"{run_tree}"` and filled from the task's top-level `run_tree` (check 12).

FOLD 1 (Thu 8 Oct 2026). Spec path values (the GRADED_PATH_FIELDS fields) may hold `{project}`, and only that
placeholder: the take's project is a per-take neutral name, so `grader_spec(..., project=<name>)` fills it, and
without `project` the paths come back unrendered (the lane lead's decision W4D1-2). check_task renders with its
BUILD_NAME. `marker_sources` is keyed by field name for a marker-valued spec field (and for `templates`, optional),
so ONE source file must hold that field's value in every half and every wording (W4D1-6); a wait-point key, a step
marker and a recovery's `if_reply_holds` are keyed by their own text. Every step before the probe carries a marker
and the probe step carries none (W4D1-1). `HOLD_HALF` fixes which half holds, per grader (W4D1-7).

FOLD 2 (the lane lead's decisions W4D2-1 to -7). A graded path's segment after `gars/projects/` or `data/staging/` is
exactly `{project}` (the take's project is never typed), and a forbidden pattern names that segment as a pattern such
as `[^/]+` (check 7 binds it under two render names). No other spec string and no wait-point pattern holds a
`{name}` placeholder. Pushback lines differ only in digit runs that are that half's `pushback_counts` values. Where
HOLD_HALF is None (number_fidelity, confounded_design), the task's `act-hold` decision text opens `trap holds` or
`normal holds`, naming the half whose right move is hold. A project name is one segment, never `.` or `..`.

FOLD 3 (the lane lead's decisions W4D3-1 to -6). template_adherence's forbidden and template_changes patterns must
fully match the half's examples with their project segment rendered under both check_task render names. Each half's
pushback line carries every value of its own pushback_counts. `graded_paths(project=X)` renders the examples'
project segment to X; without a project they come back as written. A folder path is matched with the `(/.*)?` idiom
(`gars/projects/[^/]+/01_samplesheets(/.*)?`), since a pattern must fully match the graded folder itself. Check 6's
take-time refusals, per fixture kind: generated, the manifest's fixture_sha256 equals a set sha256 pin; first-study,
samples.csv matches design_table.md5, the generator's stdout is a JSON object, and a set sha256 pin equals
copy_project.tree_sha; project, gars/projects/<name> is a folder and the first stdout line reads
`exits N (expected M)`; copied-tree, stdout is a JSON object and its tree_sha256_name_invariant equals a set pin.

FOLD 4 (glitch-f3's ruling, under Javier's delegation: fold and close). template_adherence: on the normal half (right
label `template`), forbid the template change before the probe only; a forbidden.post pattern that matches the
reported change makes `template` unreachable and is refused. template_changes binds the rendered examples of both
halves; a pattern naming no example passes only when its project segment matches both render names. A wait-point
regex whose project segment types a name is refused. Named limits (W4D4-4, no code): `{0}` reads as a regex
quantifier and is not refused as a placeholder; a pushback count left equal by copy-paste passes when the line also
carries the half's value elsewhere ("14 files across 5 samples, 8 of them paired").

This module reads files only under its `root` (default: this folder) and loads the graders by file path from
`graders/` beside it, asserting each module's `__file__`. No model, no network, stdlib only.
"""

from __future__ import annotations

import copy
import importlib
import json
import os
import posixpath
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# ---- constants (interface 10) ---------------------------------------------------------------------------------------

TRAP, NORMAL = "trap", "normal"
HALVES = (TRAP, NORMAL)
ACT, HOLD = "act", "hold"
KINDS = (ACT, HOLD)
N_WORDINGS = 5
REPEATS = 2
TRIES_PER_HALF = 10
TASK_SCHEMA = "gap4-task/1"
VARIANTS_SCHEMA = "gap4-variants/1"
TASKS_DIR = HERE / "tasks"
VARIANTS_DIR = HERE / "variants"
# The full sha of 844a4ce, resolved once with `git rev-parse 844a4ce` (a test re-resolves it).
PINNED_TREE = "844a4ce0d89437ca043363981a86096f6383a141"
PRESSURE_SEPARATOR = " "

STATUSES = ("repaired", "repaired-pushback", "repaired-pressure", "rebuilt", "new", "candidate")
DECIDED_BY = ("lane", "glitch-f3", "lane-lead")
PUSHBACK_RULE = "number_fidelity.pushback"
DERIVED_RULES = (PUSHBACK_RULE,)
PLAN_SHAPE = "plan-shape"

# The graders a task may name, by module name, with the spec shape each one takes (fixed per grader: a per-half
# grader's spec holds one half; a per-task one holds both).
PER_HALF, PER_TASK = "per-half", "per-task"
SHAPES = (PER_HALF, PER_TASK)
GRADER_SHAPES = {
    "scope_read": PER_HALF,
    "template_adherence": PER_HALF,
    "number_fidelity": PER_HALF,
    "precondition_refusal": PER_HALF,
    "plan_gate": PER_HALF,
    "confounded_design": PER_TASK,
    "new_tasks": PER_TASK,
}
GRADERS = tuple(GRADER_SHAPES)
PAUSE_ADHERENCE = "pause_adherence"
LOADABLE = GRADERS + (PAUSE_ADHERENCE,)   # the task graders, and the wait-point checker every task's pause passes
NUMBER_FIDELITY = "number_fidelity"
PLAN_GATE = "plan_gate"
PRECONDITION = "precondition_refusal"
TEMPLATE = "template_adherence"
NEW_TASKS = "new_tasks"
ENTRY = "check_spec"
APPROVAL_SCOPE = "approval-scope"   # new_tasks.APPROVAL_SCOPE; a test binds the two

# Where each grader keeps its own half names (ruling 5): an attribute path read from the loaded module, never typed.
GRADER_HALVES_SOURCE = {
    "scope_read": ("HALVES",),
    "template_adherence": ("HALVES",),
    "plan_gate": ("HALVES",),
    "precondition_refusal": ("TRAP", "NORMAL"),
    "confounded_design": ("nt.HALVES",),
    "new_tasks": ("HALVES",),
    "number_fidelity": None,
}

# Which canonical half holds, per grader (W4D1-7, fold 1): a closed table, so act and hold cannot be swapped between
# the halves. None: the grader's two right moves are both replies (number_fidelity: correct or confirm;
# confounded_design: flag or invent none), so the task records its choice as decision ACT_HOLD_DECISION.
HOLD_HALF = {
    "scope_read": TRAP,
    "template_adherence": TRAP,
    "precondition_refusal": TRAP,
    "plan_gate": TRAP,
    "new_tasks": TRAP,
    "number_fidelity": None,
    "confounded_design": None,
}
ACT_HOLD_DECISION = "act-hold"

# The pressure factor (W4BR-w4d-4).
FACTOR_NAME = "pressure"
FACTOR_LEVELS = [False, True]
FACTOR_KEYS = ("name", "slot", "levels", "row_field")

# The closed shapes.
TASK_KEYS = ("schema", "task", "status", "grader", "grader_halves", "element", "factor", "source_template",
             "run_tree", "marker_sources", "pause", "decisions", "derived_steps", "halves")
PER_TASK_KEY = "grader_spec"
GRADER_KEYS = ("module", "entry", "shape")
HALF_KEYS = ("right_move", "forbidden", "operator_script", "probe_operator_turn", "fixture")
RIGHT_MOVE_KEYS = ("kind", "label", "why")
FORBIDDEN_KEYS = ("pre", "post", "examples", "why")
STEP_KEYS = ("n", "line")
STEP_OPTIONAL = ("marker", "recovery")
RECOVERY_KEYS = ("if_reply_holds", "send")
RECOVERY_OPTIONAL = ("at_most",)
DECISION_KEYS = ("id", "text", "by")
DERIVED_KEYS = ("n", "rule")
SOURCE_KEYS = ("file", "commit")
PAUSE_KEYS = ("wait_points",)
VARIANTS_KEYS = ("schema", "task", "wordings", "factor_text")
WORDING_KEYS = ("id", "opening", "probe", "slots")
WORDING_IDS = tuple(f"w{i}" for i in range(1, N_WORDINGS + 1))
SLOT_ELEMENT, FIXTURE_ELEMENT = "slot", "fixture"

# FIXTURE: one closed shape per kind (W4BR-w4d-2). Each row: its keys, its half-defining field (None: the element is
# a slot), and the fields besides it allowed to differ between halves (dotted for a nested field).
FIXTURE_NOTE = "note"
FIXTURE_KEYS = {
    "generated": ("kind", "generator", "variant", "seed", "sha256", "seed_sensitive"),
    "project": ("kind", "generator", "variant", "seed", "sha256", "seed_sensitive"),
    "first-study": ("kind", "generator", "half", "seed", "neutralise", "ground_truth", "design_table", "sha256",
                    "seed_sensitive"),
    "copied-tree": ("kind", "generator", "sha256", "seed_sensitive"),
}
FIXTURE_KINDS = tuple(FIXTURE_KEYS)
HALF_FIELD = {"generated": "variant", "project": "variant", "first-study": "half", "copied-tree": None}
DERIVED_FIELDS = {"generated": ("sha256",), "project": ("sha256",),
                  "first-study": ("ground_truth.design_matrix_rank", "design_table.md5", "sha256"),
                  "copied-tree": ("sha256",)}
NESTED_KEYS = {"neutralise": ("path",), "ground_truth": ("path", "design_matrix_rank", "of_columns"),
               "design_table": ("md5",)}
# Every generator and helper a fixture names is round 4's own file (this lane's decision: copies of the first study's
# builders live here as identical copies, so a fixture never runs a frozen round's file).
GENERATOR_DIR = "evals/gap-study-4/fixtures/"

# The placeholders (interface 10).
OPENING, PROBE, PRESSURE, PROJECT, SOURCE, RUN_TREE = "opening", "probe", "pressure", "project", "source", "run_tree"
LINE_PLACEHOLDERS = (OPENING, PROBE, PRESSURE, PROJECT, SOURCE)
RESERVED_SLOTS = LINE_PLACEHOLDERS + (RUN_TREE,)
_PLACEHOLDER = re.compile(r"\{([^{}]*)\}")
_SLOT_NAME = re.compile(r"[a-z][a-z0-9_]*\Z")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_HEX32 = re.compile(r"[0-9a-f]{32}\Z")

# GRADED_PATH_FIELDS (W4BR-w4d-1): the spec fields that name run-tree paths, per grader (and per new_tasks task).
# template_adherence names its paths as its `forbidden` regexes (bound through `forbidden.examples`); number_fidelity
# names none. `fixed_sha256`'s paths are its keys.
GRADED_PATH_FIELDS = {
    "scope_read": ("planted",),
    "precondition_refusal": ("required_inputs", "data_paths", "stage_outputs"),
    "plan_gate": ("plan_path", "approval_store"),
    "confounded_design": ("guarded",),
    "new_tasks": {
        "explain-not-act": ("guarded", "generated", "fixed_sha256"),
        "approval-scope": ("pre_existing", "link_paths"),
        "conditional-yes": ("link_paths",),
    },
    "template_adherence": (),
    "number_fidelity": (),
}
KEYED_PATH_FIELDS = ("fixed_sha256",)
# A wait-point `match` counts as a literal path when it holds none of these (a "." is kept: it is a path's own dot,
# and counting such a match makes the exclusion check stricter, never looser; this lane's decision).
REGEX_META = "^$*+?{}[]\\|()"


class TaskError(ValueError):
    """A task or variants file outside its closed shape, or a call outside the task's cells."""


# ---- small shape helpers --------------------------------------------------------------------------------------------

def _str(v) -> bool:
    return isinstance(v, str) and bool(v)


def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def run_path(v) -> bool:
    """A literal run-tree-relative path: no leading '/', no empty, '.' or '..' segment."""
    return _str(v) and not v.startswith("/") and all(s not in ("", ".", "..") for s in v.split("/"))


def abs_normal(v) -> bool:
    """An absolute, normalised path other than '/'."""
    return _str(v) and v.startswith("/") and v != "/" and posixpath.normpath(v) == v


def _closed(obj, keys, where: str, optional=()) -> list[str]:
    if not isinstance(obj, dict):
        return [f"{where} is an object"]
    out = []
    missing = [k for k in keys if k not in obj]
    extra = sorted(k for k in obj if k not in keys and k not in optional)
    if missing:
        out.append(f"{where} is missing {missing}")
    if extra:
        out.append(f"{where} holds unknown keys {extra}")
    return out


def placeholders(text: str) -> list[str]:
    """The names in braces in `text`, in order."""
    return _PLACEHOLDER.findall(text)


def _brace_problems(text: str, allowed, where: str) -> list[str]:
    stray = _PLACEHOLDER.sub("", text)
    out = []
    if "{" in stray or "}" in stray:
        out.append(f"{where} holds an unbalanced brace")
    bad = [p for p in placeholders(text) if p not in allowed]
    if bad:
        out.append(f"{where} holds placeholders outside {list(allowed)}: {bad}")
    return out


# ---- the graders ----------------------------------------------------------------------------------------------------

def grader_name(task: dict) -> str:
    """`graders/<name>.py` -> `<name>` (the schema has already refused anything else)."""
    return task["grader"]["module"][len("graders/"):-len(".py")]


def load_grader(name: str):
    """A round 4 grader, loaded from `graders/` beside this file; refused unless its `__file__` is there."""
    if name not in LOADABLE:
        raise TaskError(f"no grader {name!r}; one of {list(LOADABLE)}")
    mod = importlib.import_module(f"graders.{name}")
    where = Path(mod.__file__).resolve()
    if where.parent != HERE / "graders":
        raise TaskError(f"graders.{name} loaded from {where}, not from {HERE / 'graders'}")
    return mod


def _attr(mod, path: str):
    for part in path.split("."):
        mod = getattr(mod, part)
    return mod


def grader_halves_of(name: str):
    """The grader's own half names in order (trap first), read from the module; None for number_fidelity."""
    src = GRADER_HALVES_SOURCE[name]
    if src is None:
        return None
    mod = load_grader(name)
    if len(src) == 1:
        return tuple(_attr(mod, src[0]))
    return tuple(_attr(mod, s) for s in src)


def new_tasks_ids() -> tuple:
    return tuple(load_grader(NEW_TASKS).TASKS)


# ---- the schema (check 1) -------------------------------------------------------------------------------------------

def _step_problems(step, where: str) -> list[str]:
    out = _closed(step, STEP_KEYS, where, STEP_OPTIONAL)
    if out:
        return out
    if not _int(step["n"]) or step["n"] < 1:
        out.append(f"{where}.n is a positive int")
    if not _str(step["line"]):
        out.append(f"{where}.line is a non-empty string")
    if "marker" in step and step["marker"] is not None and not _str(step["marker"]):
        out.append(f"{where}.marker is a non-empty string or null")
    if "recovery" in step:
        rec = step["recovery"]
        sub = _closed(rec, RECOVERY_KEYS, f"{where}.recovery", RECOVERY_OPTIONAL)
        out += sub
        if not sub:
            for k in RECOVERY_KEYS:
                if not _str(rec[k]):
                    out.append(f"{where}.recovery.{k} is a non-empty string")
            if "at_most" in rec and (not _int(rec["at_most"]) or rec["at_most"] < 1):
                out.append(f"{where}.recovery.at_most is a positive int")
    return out


def fixture_problems(fx, where: str) -> list[str]:
    """The fixture's keys are exactly its kind's row in the FIXTURE table, typed."""
    if not isinstance(fx, dict):
        return [f"{where} is an object"]
    kind = fx.get("kind")
    if kind not in FIXTURE_KEYS:
        return [f"{where}.kind {kind!r} is not one of {list(FIXTURE_KINDS)} (a new kind is named for CP2's driver)"]
    out = _closed(fx, FIXTURE_KEYS[kind], where, (FIXTURE_NOTE,))
    if out:
        return out
    g = fx["generator"]
    if not (run_path(g) and g.startswith(GENERATOR_DIR) and g.endswith(".py")):
        out.append(f"{where}.generator is a .py under {GENERATOR_DIR}")
    if fx["sha256"] is not None and not (isinstance(fx["sha256"], str) and _HEX64.match(fx["sha256"])):
        out.append(f"{where}.sha256 is null (until the freeze) or 64 lower-case hex")
    if not isinstance(fx["seed_sensitive"], bool):
        out.append(f"{where}.seed_sensitive is a bool")
    if FIXTURE_NOTE in fx and not _str(fx[FIXTURE_NOTE]):
        out.append(f"{where}.note is a non-empty string")
    if "seed" in fx and (not _int(fx["seed"]) or fx["seed"] < 0):
        out.append(f"{where}.seed is a non-negative int")
    if kind in ("generated", "project") and not _str(fx["variant"]):
        out.append(f"{where}.variant is a non-empty string")
    if kind == "copied-tree" and fx["seed_sensitive"] is not False:
        out.append(f"{where}.seed_sensitive is false for a copied tree (it takes no seed)")
    if kind == "first-study":
        if not _str(fx["half"]):
            out.append(f"{where}.half is a non-empty string")
        for k, keys in NESTED_KEYS.items():
            sub = _closed(fx[k], keys, f"{where}.{k}")
            out += sub
            if sub:
                continue
            if "path" in keys and not (run_path(fx[k]["path"]) and fx[k]["path"].startswith(GENERATOR_DIR)):
                out.append(f"{where}.{k}.path is a file under {GENERATOR_DIR}")
        if not out:
            gt = fx["ground_truth"]
            if not (_int(gt["design_matrix_rank"]) and _int(gt["of_columns"])
                    and 0 < gt["design_matrix_rank"] <= gt["of_columns"]):
                out.append(f"{where}.ground_truth holds a rank and a column count, 0 < rank <= columns")
            if not (isinstance(fx["design_table"]["md5"], str) and _HEX32.match(fx["design_table"]["md5"])):
                out.append(f"{where}.design_table.md5 is 32 lower-case hex")
    return out


def _forbidden_shape(fb, where: str) -> list[str]:
    out = _closed(fb, FORBIDDEN_KEYS, where)
    if out:
        return out
    for k in ("pre", "post", "examples"):
        if not isinstance(fb[k], list) or not all(_str(x) for x in fb[k]):
            out.append(f"{where}.{k} is a list of non-empty strings")
    if not _str(fb["why"]):
        out.append(f"{where}.why is a non-empty string")
    return out


def _probe_field_problems(spec, shape: str, ghalves, where: str) -> list[str]:
    """The probe line is written as the placeholder, never typed (so grader_spec fills it with the line as sent)."""
    if not isinstance(spec, dict):
        return [f"{where} is an object"]
    if "probe_line" not in spec:
        return [f"{where} holds no probe_line"]
    want = f"{{{PROBE}}}"
    if shape == PER_HALF and spec["probe_line"] != want:
        return [f"{where}.probe_line is written {want!r}, never typed"]
    if shape == PER_TASK and (not isinstance(spec["probe_line"], dict) or ghalves is None
                              or set(spec["probe_line"]) != set(ghalves)
                              or any(v != want for v in spec["probe_line"].values())):
        return [f"{where}.probe_line is {{<grader half>: {want!r}}} for both of the grader's halves"]
    return []


def grader_halves_problems(task) -> list[str]:
    """W4BR-w4d-7: grader_halves equals the grader's own HALVES in order (trap first), or null for number_fidelity."""
    name = grader_name(task)
    own = grader_halves_of(name)
    got = task["grader_halves"]
    if own is None:
        return [] if got is None else [f"grader_halves is null for {name} (it takes no half)"]
    want = {TRAP: own[0], NORMAL: own[1]}
    if got != want:
        return [f"grader_halves is {want} for {name} (trap -> its HALVES[0]); it is {got}"]
    return []


def plan_shape_problems(task) -> list[str]:
    """A plan_gate task records its plan shape (the pinned slug, or the pre-created skeleton) as decision plan-shape."""
    if grader_name(task) != PLAN_GATE:
        return []
    if not any(d.get("id") == PLAN_SHAPE for d in task["decisions"] if isinstance(d, dict)):
        return [f"a plan_gate task carries a decisions entry with id {PLAN_SHAPE!r} (W3B2-3 ii and iii)"]
    return []


def run_tree_problems(task) -> list[str]:
    """`run_tree` is non-null exactly for approval-scope, and then absolute and normalised."""
    is_scope = task["grader"]["entry"] == f"{ENTRY}:{APPROVAL_SCOPE}"
    rt = task["run_tree"]
    if is_scope and not abs_normal(rt):
        return ["run_tree is an absolute, normalised path for approval-scope"]
    if not is_scope and rt is not None:
        return ["run_tree is null for every task but approval-scope"]
    return []


def _grader_problems(task) -> list[str]:
    g = task["grader"]
    out = _closed(g, GRADER_KEYS, "grader")
    if out:
        return out
    mod = g["module"]
    names = [f"graders/{n}.py" for n in GRADERS]
    if mod not in names:
        return [f"grader.module is one of {names}"]
    name = mod[len("graders/"):-len(".py")]
    if g["shape"] != GRADER_SHAPES[name]:
        out.append(f"grader.shape is {GRADER_SHAPES[name]!r} for {name}")
    if name == NEW_TASKS:
        if g["entry"] != f"{ENTRY}:{task.get('task')}" or task.get("task") not in new_tasks_ids():
            out.append(f"grader.entry is '{ENTRY}:<the task id>' for new_tasks, the id one of {list(new_tasks_ids())}")
    elif g["entry"] != ENTRY:
        out.append(f"grader.entry is {ENTRY!r} for {name}")
    return out


def task_shape_problems(task, stem: str) -> list[str]:
    """Every problem with a task file's shape (check 1's half for tasks/<stem>.json)."""
    if not isinstance(task, dict):
        return ["the task file holds an object"]
    shape = (task.get("grader") or {}).get("shape") if isinstance(task.get("grader"), dict) else None
    keys = TASK_KEYS + ((PER_TASK_KEY,) if shape == PER_TASK else ())
    out = _closed(task, keys, "task")
    if out:
        return out
    if task["schema"] != TASK_SCHEMA:
        out.append(f"schema is {TASK_SCHEMA!r}")
    if task["task"] != stem:
        out.append(f"task {task['task']!r} is not the file stem {stem!r}")
    if task["status"] not in STATUSES:
        out.append(f"status {task['status']!r} is not one of {list(STATUSES)}")
    gp = _grader_problems(task)
    out += gp
    if gp:
        return out
    name = grader_name(task)
    out += grader_halves_problems(task)
    ghalves = grader_halves_of(name)
    # element
    el = task["element"]
    if not isinstance(el, dict) or el.get("kind") not in (SLOT_ELEMENT, FIXTURE_ELEMENT):
        out.append("element is {kind: slot, slot} or {kind: fixture, field}")
    elif el["kind"] == SLOT_ELEMENT:
        out += _closed(el, ("kind", "slot"), "element")
        if "slot" in el and not (isinstance(el["slot"], str) and _SLOT_NAME.match(el["slot"])
                                 and el["slot"] not in RESERVED_SLOTS):
            out.append(f"element.slot is a lower-case name other than {list(RESERVED_SLOTS)}")
    else:
        out += _closed(el, ("kind", "field"), "element")
    # factor
    fac = task["factor"]
    if fac is not None:
        sub = _closed(fac, FACTOR_KEYS, "factor")
        out += sub
        if not sub:
            row_field = load_grader(PRECONDITION).ROW_FIELD
            if fac != {"name": FACTOR_NAME, "slot": PRESSURE, "levels": FACTOR_LEVELS, "row_field": row_field}:
                out.append(f"factor is exactly {{name: {FACTOR_NAME}, slot: {PRESSURE}, levels: {FACTOR_LEVELS}, "
                           f"row_field: {row_field}}}")
    # source_template (its content is check 2's)
    if not _str(task["source_template"]):
        out.append("source_template is a non-empty string")
    out += run_tree_problems(task)
    # marker_sources
    ms = task["marker_sources"]
    if not isinstance(ms, dict):
        out.append("marker_sources is an object")
    else:
        for k, v in ms.items():
            sub = _closed(v, SOURCE_KEYS, f"marker_sources[{k!r}]")
            out += sub
            if not sub and not (run_path(v["file"]) and v["file"].startswith("gars/")
                                and isinstance(v["commit"], str) and _HEX40.match(v["commit"])):
                out.append(f"marker_sources[{k!r}] is {{file: gars/<path>, commit: <40 hex>}}")
    # pause
    p = task["pause"]
    sub = _closed(p, PAUSE_KEYS, "pause")
    out += sub
    if not sub and not isinstance(p["wait_points"], dict):
        out.append("pause.wait_points is an object")
    # decisions
    ds = task["decisions"]
    if not isinstance(ds, list):
        out.append("decisions is a list")
    else:
        for i, d in enumerate(ds):
            sub = _closed(d, DECISION_KEYS, f"decisions[{i}]")
            out += sub
            if not sub and not (_str(d["id"]) and _str(d["text"]) and d["by"] in DECIDED_BY):
                out.append(f"decisions[{i}] holds a non-empty id and text, and by one of {list(DECIDED_BY)}")
        ids = [d.get("id") for d in ds if isinstance(d, dict)]
        if len(ids) != len(set(ids)):
            out.append("decision ids are distinct")
    out += plan_shape_problems(task)
    # derived_steps
    dv = task["derived_steps"]
    if not isinstance(dv, list):
        out.append("derived_steps is a list")
    else:
        for i, d in enumerate(dv):
            sub = _closed(d, DERIVED_KEYS, f"derived_steps[{i}]")
            out += sub
            if not sub and not (_int(d["n"]) and d["rule"] in DERIVED_RULES):
                out.append(f"derived_steps[{i}] holds an int n and a rule in {list(DERIVED_RULES)}")
    # the grader spec, per task
    shape = task["grader"]["shape"]
    if shape == PER_TASK:
        out += _probe_field_problems(task[PER_TASK_KEY], shape, ghalves, "grader_spec")
    # halves
    hs = task["halves"]
    sub = _closed(hs, HALVES, "halves")
    out += sub
    if sub:
        return out
    hkeys = HALF_KEYS + ((PER_TASK_KEY,) if shape == PER_HALF else ())
    for h in HALVES:
        half, where = hs[h], f"halves.{h}"
        sub = _closed(half, hkeys, where)
        out += sub
        if sub:
            continue
        rm = half["right_move"]
        sub = _closed(rm, RIGHT_MOVE_KEYS, f"{where}.right_move")
        out += sub
        if not sub and not (rm["kind"] in KINDS and _str(rm["label"]) and _str(rm["why"])):
            out.append(f"{where}.right_move holds kind in {list(KINDS)}, a label and a why")
        out += _forbidden_shape(half["forbidden"], f"{where}.forbidden")
        script = half["operator_script"]
        if not isinstance(script, list) or not script:
            out.append(f"{where}.operator_script is a non-empty list of steps")
        else:
            for i, s in enumerate(script):
                out += _step_problems(s, f"{where}.operator_script[{i}]")
        if not _int(half["probe_operator_turn"]):
            out.append(f"{where}.probe_operator_turn is an int")
        out += fixture_problems(half["fixture"], f"{where}.fixture")
        if shape == PER_HALF:
            out += _probe_field_problems(half[PER_TASK_KEY], shape, ghalves, f"{where}.grader_spec")
    if out:
        return out
    out += script_problems(task)
    if not out and el["kind"] == FIXTURE_ELEMENT:
        kind = hs[TRAP]["fixture"]["kind"]
        if HALF_FIELD.get(kind) is None or el["field"] != HALF_FIELD[kind]:
            out.append(f"element.field is the {kind} fixture's half-defining field ({HALF_FIELD.get(kind)}); "
                       f"a {kind} fixture defines no half")
    return out


def script_problems(task) -> list[str]:
    """Each half's script: steps numbered 1..N, the probe one of them, and the placeholders in their places."""
    out = []
    for h in HALVES:
        half, where = task["halves"][h], f"halves.{h}.operator_script"
        ns = [s["n"] for s in half["operator_script"]]
        if ns != list(range(1, len(ns) + 1)):
            out.append(f"{where} numbers its steps 1..{len(ns)} in order; it numbers them {ns}")
            continue
        probe = half["probe_operator_turn"]
        if probe not in ns:
            out.append(f"halves.{h}.probe_operator_turn {probe} is no step of the script")
            continue
        for s in half["operator_script"]:
            sw = f"{where}[n={s['n']}].line"
            out += _brace_problems(s["line"], LINE_PLACEHOLDERS, sw)
            names = placeholders(s["line"])
            if s["n"] == 1 and names.count(OPENING) != 1:
                out.append(f"{sw} holds {{opening}} exactly once (step 1)")
            if s["n"] != 1 and OPENING in names:
                out.append(f"{sw} holds {{opening}}, which belongs to step 1 only")
            if s["n"] == probe and names.count(PROBE) != 1:
                out.append(f"{sw} holds {{probe}} exactly once (the probe step)")
            if s["n"] != probe and PROBE in names:
                out.append(f"{sw} holds {{probe}}, which belongs to the probe step only")
            if "recovery" in s:
                out += _brace_problems(s["recovery"]["send"], (PROJECT, SOURCE), f"{where}[n={s['n']}].recovery.send")
    return out


def variants_shape_problems(doc, stem: str, task) -> list[str]:
    """Every problem with a variants file's shape (check 1's half for variants/<stem>.json), against its task."""
    out = _closed(doc, VARIANTS_KEYS, "variants")
    if out:
        return out
    if doc["schema"] != VARIANTS_SCHEMA:
        out.append(f"variants schema is {VARIANTS_SCHEMA!r}")
    if doc["task"] != stem:
        out.append(f"variants task {doc['task']!r} is not the file stem {stem!r}")
    ws = doc["wordings"]
    if not isinstance(ws, list) or len(ws) != N_WORDINGS:
        out.append(f"wordings holds exactly {N_WORDINGS} wordings")
        return out
    el = task["element"]
    slot_keys = (el["slot"],) if el["kind"] == SLOT_ELEMENT else ()
    allowed = slot_keys + (PRESSURE,)   # {pressure} misplaced is check 5's finding
    for i, w in enumerate(ws):
        where = f"wordings[{i}]"
        sub = _closed(w, WORDING_KEYS, where)
        out += sub
        if sub:
            continue
        if w["id"] != WORDING_IDS[i]:
            out.append(f"{where}.id is {WORDING_IDS[i]!r} (ids w1..w{N_WORDINGS}, in order)")
        for k in ("opening", "probe"):
            if not _str(w[k]):
                out.append(f"{where}.{k} is a non-empty string")
            else:
                out += _brace_problems(w[k], allowed, f"{where}.{k}")
        sl = w["slots"]
        if not isinstance(sl, dict) or set(sl) != set(slot_keys):
            out.append(f"{where}.slots holds exactly {list(slot_keys)} (the element slot, for a slot task)")
            continue
        for s, v in sl.items():
            sub = _closed(v, HALVES, f"{where}.slots.{s}")
            out += sub
            if not sub:
                for h in HALVES:
                    if not _str(v[h]):
                        out.append(f"{where}.slots.{s}.{h} is a non-empty string")
                    else:
                        out += _brace_problems(v[h], (), f"{where}.slots.{s}.{h}")
    ft = doc["factor_text"]
    if ft is not None:
        sub = _closed(ft, (FACTOR_NAME,), "factor_text")
        out += sub
        if not sub:
            if not _str(ft[FACTOR_NAME]):
                out.append("factor_text.pressure is a non-empty string")
            else:
                out += _brace_problems(ft[FACTOR_NAME], (), "factor_text.pressure")
    if (ft is None) != (task["factor"] is None):
        out.append("factor_text is null exactly when the task has no factor")
    return out


# ---- loading --------------------------------------------------------------------------------------------------------

def _root(root) -> Path:
    return HERE if root is None else Path(root)


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise TaskError(f"{path.name}: unreadable ({e.strerror})") from None
    except ValueError as e:
        raise TaskError(f"{path.name}: not JSON ({e})") from None


def _check_id(task_id) -> None:
    if not isinstance(task_id, str) or not re.match(r"[a-z0-9][a-z0-9-]*\Z", task_id):
        raise TaskError(f"task id {task_id!r} is a lower-case file stem")


def load_task(task_id: str, *, root=None) -> dict:
    """tasks/<task_id>.json, read and shape-checked (check 1); TaskError on any problem."""
    _check_id(task_id)
    doc = _read(_root(root) / "tasks" / f"{task_id}.json")
    bad = task_shape_problems(doc, task_id)
    if bad:
        raise TaskError("; ".join(bad))
    return doc


def load_variants(task_id: str, *, root=None) -> dict:
    """variants/<task_id>.json, read and shape-checked against its task (check 1); TaskError on any problem."""
    task = load_task(task_id, root=root)
    doc = _read(_root(root) / "variants" / f"{task_id}.json")
    bad = variants_shape_problems(doc, task_id, task)
    if bad:
        raise TaskError("; ".join(bad))
    return doc


# ---- cells (check 5) ------------------------------------------------------------------------------------------------

def cells(task_id: str, *, root=None) -> list[dict]:
    """Every (half, wording, repeat or factor level): `TRIES_PER_HALF` per half. A task with no factor repeats each
    wording `REPEATS` times (`repeat` 1..REPEATS, `pressure` None); a factor task crosses each wording with every level
    (`repeat` None, `pressure` the level)."""
    return task_cells(load_task(task_id, root=root), load_variants(task_id, root=root))


def task_cells(task: dict, variants_doc: dict) -> list[dict]:
    """cells on loaded documents (check 5 validates exactly this, never a copy of it; fold 1, m5)."""
    ws = [w["id"] for w in variants_doc["wordings"]]
    out = []
    for h in HALVES:
        for w in ws:
            if task["factor"] is None:
                out += [{"half": h, "wording": w, "repeat": r, "pressure": None} for r in range(1, REPEATS + 1)]
            else:
                out += [{"half": h, "wording": w, "repeat": None, "pressure": lv} for lv in task["factor"]["levels"]]
    return out


def row_fields(cell: dict) -> dict:
    """The row fields a grader reads: {"pressure": <bool>} for a factor task's cell, {} otherwise."""
    if not isinstance(cell, dict) or set(cell) != {"half", "wording", "repeat", "pressure"}:
        raise TaskError("a cell is {half, wording, repeat, pressure}")
    p = cell["pressure"]
    if p is None:
        return {}
    if not isinstance(p, bool):
        raise TaskError("a cell's pressure is a bool or None")
    return {FACTOR_NAME: p}


# ---- rendering ------------------------------------------------------------------------------------------------------

def _wording(doc: dict, wording: str) -> dict:
    for w in doc["wordings"]:
        if w["id"] == wording:
            return w
    raise TaskError(f"no wording {wording!r}; one of {[w['id'] for w in doc['wordings']]}")


def _args(task: dict, half, pressure) -> None:
    if half not in HALVES:
        raise TaskError(f"half is one of {HALVES}")
    if task["factor"] is None and pressure is not None:
        raise TaskError("this task has no factor: pressure is None")
    if task["factor"] is not None and not isinstance(pressure, bool):
        raise TaskError("this task crosses the pressure factor: pressure is True or False")


def fill_slot(text: str, task: dict, wording: dict, half: str) -> str:
    """A wording's text with the element slot filled for `half` (a fixture task's wordings hold no slot)."""
    el = task["element"]
    if el["kind"] != SLOT_ELEMENT:
        return text
    return text.replace("{" + el["slot"] + "}", wording["slots"][el["slot"]][half])


def pressure_text(variants_doc: dict, pressure) -> str:
    if not pressure:
        return ""
    return PRESSURE_SEPARATOR + variants_doc["factor_text"][FACTOR_NAME]


def render_steps(task: dict, variants_doc: dict, half: str, wording: str, pressure=None) -> list[dict]:
    """operator_steps on loaded documents (the checks call it on their own copies)."""
    _args(task, half, pressure)
    w = _wording(variants_doc, wording)
    opening, probe = fill_slot(w["opening"], task, w, half), fill_slot(w["probe"], task, w, half)
    out = []
    for s in copy.deepcopy(task["halves"][half]["operator_script"]):
        s["line"] = (s["line"].replace("{" + OPENING + "}", opening).replace("{" + PROBE + "}", probe)
                     .replace("{" + PRESSURE + "}", pressure_text(variants_doc, pressure)))
        out.append(s)
    return out


def operator_steps(task_id: str, half: str, wording: str, *, pressure=None, root=None) -> list[dict]:
    """The half's script with {opening}, {probe}, {pressure} and the element slot filled; {project} and {source} are
    left for the driver's render."""
    return render_steps(load_task(task_id, root=root), load_variants(task_id, root=root), half, wording, pressure)


def render_probe(task: dict, variants_doc: dict, half: str, wording: str, pressure=None) -> str:
    n = task["halves"][half]["probe_operator_turn"]
    return next(s["line"] for s in render_steps(task, variants_doc, half, wording, pressure) if s["n"] == n)


def probe_line(task_id: str, half: str, wording: str, *, pressure=None, root=None) -> str:
    """The probe step's rendered line, exactly as sent."""
    return render_probe(load_task(task_id, root=root), load_variants(task_id, root=root), half, wording, pressure)


def render_project(spec: dict, task: dict, project: str) -> dict:
    """The spec with `{project}` filled in every GRADED_PATH_FIELDS value (keys of a keyed field included); the only
    placeholder a spec path may hold (W4D1-2, the lane lead's decision)."""
    if not _str(project) or "/" in project or "{" in project or "}" in project or project in (".", ".."):
        raise TaskError(f"project {project!r} is one path segment")
    tok = "{" + PROJECT + "}"

    def fill(x):
        if isinstance(x, str):
            return x.replace(tok, project)
        if isinstance(x, list):
            return [fill(y) for y in x]
        if isinstance(x, dict):
            return {k: fill(y) for k, y in x.items()}
        return x
    for f in graded_fields(task):
        if f not in spec:
            continue
        if f in KEYED_PATH_FIELDS and isinstance(spec[f], dict):
            spec[f] = {k.replace(tok, project): y for k, y in spec[f].items()}
        else:
            spec[f] = fill(spec[f])
    return spec


def render_grader_spec(task: dict, variants_doc: dict, half: str, wording: str, pressure=None, project=None) -> dict:
    """grader_spec on loaded documents."""
    _args(task, half, pressure)
    if task["grader"]["shape"] == PER_HALF:
        spec = copy.deepcopy(task["halves"][half][PER_TASK_KEY])
        spec["probe_line"] = render_probe(task, variants_doc, half, wording, pressure)
    else:
        spec = copy.deepcopy(task[PER_TASK_KEY])
        by_grader = {g: c for c, g in task["grader_halves"].items()}
        spec["probe_line"] = {g: render_probe(task, variants_doc, by_grader[g], wording, pressure)
                              for g in spec["probe_line"]}
    if task["run_tree"] is not None and "run_tree_abs" in spec:
        if spec["run_tree_abs"] == "{" + RUN_TREE + "}":
            spec["run_tree_abs"] = task["run_tree"]
    if project is not None:
        spec = render_project(spec, task, project)
    return spec


def grader_spec(task_id: str, half: str, wording: str, *, pressure=None, project=None, root=None) -> dict:
    """The concrete spec in the grader's own shape, ready for its check_spec (a per-task spec is the whole spec, its
    probe_line filled for both grader halves of this wording). With `project`, every `{project}` in a spec path is
    filled with it (the take's own project name); without it the paths are returned unrendered, and the caller must
    render them before grading: the graders read `{project}` as an ordinary path segment (W4D1-2)."""
    return render_grader_spec(load_task(task_id, root=root), load_variants(task_id, root=root), half, wording,
                              pressure, project)


def render_source(template: str, run_tree: str, project: str) -> str:
    """The absolute source path: `template` with {run_tree} and {project} filled. Refuses a run tree that is not
    absolute and normalised, and a template that does not start with '{run_tree}/'."""
    if not abs_normal(run_tree):
        raise TaskError(f"run_tree {run_tree!r} is an absolute, normalised path")
    if not isinstance(template, str) or not template.startswith("{" + RUN_TREE + "}/"):
        raise TaskError("the source template starts with '{run_tree}/'")
    if not _str(project) or "/" in project or "{" in project or project in (".", ".."):
        raise TaskError(f"project {project!r} is one path segment")
    return template.replace("{" + RUN_TREE + "}", run_tree).replace("{" + PROJECT + "}", project)


# ---- graded paths ---------------------------------------------------------------------------------------------------

def graded_fields(task: dict) -> tuple:
    """The GRADED_PATH_FIELDS entry for this task's grader (by new_tasks task for new_tasks)."""
    f = GRADED_PATH_FIELDS[grader_name(task)]
    return f[task["task"]] if isinstance(f, dict) else f


def _flatten(v) -> set:
    if isinstance(v, str):
        return {v}
    if isinstance(v, list):
        return set().union(*[_flatten(x) for x in v]) if v else set()
    if isinstance(v, dict):
        return set().union(*[_flatten(x) for x in v.values()]) if v else set()
    return set()


def field_paths(spec: dict, field: str, ghalf=None) -> set:
    """The literal paths one spec field names; `ghalf` narrows a per-half dict value to that grader half."""
    v = spec.get(field)
    if field in KEYED_PATH_FIELDS:
        return set(v) if isinstance(v, dict) else set()
    if ghalf is not None and isinstance(v, dict) and isinstance(spec.get("probe_line"), dict) \
            and set(v) == set(spec["probe_line"]):
        v = v[ghalf]
    return _flatten(v)


def concrete_specs(task: dict, variants_doc: dict, project=None) -> list[tuple]:
    """(cell, spec) for every cell of the task, `{project}` filled when `project` is given."""
    out = []
    for w in variants_doc["wordings"]:
        for h in HALVES:
            levels = [None] if task["factor"] is None else task["factor"]["levels"]
            for lv in levels:
                out.append(((h, w["id"], lv), render_grader_spec(task, variants_doc, h, w["id"], lv, project)))
    return out


def is_literal(match) -> bool:
    return isinstance(match, str) and run_path(match) and not any(c in REGEX_META for c in match)


PROJECT_PARENTS = (("gars", "projects"), ("data", "staging"))


def render_example(ex: str, project: str) -> str:
    """A literal example with its project segment (after gars/projects/ or data/staging/) swapped for `project`
    (W4D3-1, W4D3-5); any other path unchanged."""
    segs = ex.split("/")
    if len(segs) > 2 and tuple(segs[:2]) in PROJECT_PARENTS:
        segs[2] = project
    return "/".join(segs)


def task_graded_paths(task: dict, variants_doc: dict, project=None) -> set:
    """See graded_paths. With `project`, the examples' project segments are rendered to it too (W4D3-5); without
    it, the examples come back as written (their project typed)."""
    out = set()
    fields = graded_fields(task)
    for _cell, spec in concrete_specs(task, variants_doc, project):
        for f in fields:
            out |= field_paths(spec, f)
    for h in HALVES:
        out |= {ex if project is None else render_example(ex, project)
                for ex in task["halves"][h]["forbidden"]["examples"]}
    for wp in task["pause"]["wait_points"].values():
        for side in wp.values() if isinstance(wp, dict) else ():
            for pat in side if isinstance(side, list) else ():
                if isinstance(pat, dict) and is_literal(pat.get("match")):
                    out.add(pat["match"])
    return out


def graded_paths(task_id: str, *, project=None, root=None) -> set:
    """Every literal run-tree path the task's right and wrong moves name: the GRADED_PATH_FIELDS values of every
    concrete spec, every half's forbidden.examples, and every literal-path `match` in pause.wait_points; spec paths
    with `{project}` filled when `project` is given (check 8 passes check_task.BUILD_NAME)."""
    return task_graded_paths(load_task(task_id, root=root), load_variants(task_id, root=root), project)
