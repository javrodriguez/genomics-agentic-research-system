#!/usr/bin/env python3
"""The walk register: every pre-freeze walk is listed, and every listed walk has its folder.

    python3 evals/gap-study-4/walk_register.py --check     the register against rehearsals/; exit 1 on any problem

WHY A REGISTER. The round 4 plan's CP6 (lines 870-878) makes every pre-freeze walk a rehearsal: "graded but never
counted, each committed with its reason". A folder of walk records with no list beside it cannot show that nothing
was dropped, and a list with no folders cannot show the walks happened. So rehearsals/register.json lists the walks
and this check binds the two both ways:

  - every folder directly under rehearsals/ is a registered walk (an unregistered folder fails, and so does any
    file beside register.json and README.md, which is not a walk and is never skipped);
  - every registered walk has its folder, holding at least one file (git keeps no empty folder, so an empty one is
    a folder a clone would not have);
  - every entry is well formed: exactly the fields below, a one-segment walk id used once, a task, half and wording
    the design in force has (prereg-draft.json and tasks/<task>.json), a model of the arm it names, a non-empty
    reason, and `counted` exactly false. A walk is never a data take; an entry that says otherwise is refused.

THE EMPTY GATE IS SAID OUT LOUD. No walk has been run when this file is written, so the register is empty and
--check passes, printing "ok, having registered 0 walks", never a bare ok: an empty register is not evidence about
any walk.

WHAT THIS DOES NOT CHECK (open questions in rehearsals/README.md): what files a walk folder must hold, where a
walk's grader output lives, whether the walks cover what CP6 asks for (every wording on the smallest model, every
task and half on each model), and which driver road writes into rehearsals/<walk>/.

No model, no network, stdlib only. Read-only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REHEARSALS = HERE / "rehearsals"
REGISTER_NAME = "register.json"
TOP_FILES = ("README.md", REGISTER_NAME)
# Finder's folder file on the Mac; never tracked, never a walk.
IGNORED_NAMES = (".DS_Store",)
SCHEMA = 1
TOP_KEYS = ("schema", "walks")
FIELDS = ("walk", "task", "half", "wording", "arm", "model", "reason", "counted")
STRING_FIELDS = ("walk", "task", "half", "wording", "arm", "model", "reason")
WALK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class DuplicateKey(ValueError):
    pass


def no_duplicate_keys(pairs):
    """W7D-R1-3: json keeps the last of two equal keys, so `"counted": true, "counted": false` would read false."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise DuplicateKey(k)
        out[k] = v
    return out


def visible(text: str) -> str:
    """W7D-R1-6: the text without Unicode whitespace or format characters (a zero-width-only reason is empty)."""
    return "".join(c for c in text if not (c.isspace() or unicodedata.category(c) == "Cf"))


def design_in_force(study_dir: Path = HERE) -> dict:
    """What an entry is checked against: the draft's tasks and their wordings, each task's halves, each arm's
    models (the planned arms and the optional ones)."""
    draft = json.loads((study_dir / "prereg-draft.json").read_text())
    tasks = {}
    for t in draft["tasks"]:
        halves = list(json.loads((study_dir / "tasks" / f"{t['id']}.json").read_text())["halves"])
        tasks[t["id"]] = {"halves": halves, "wordings": list(t["wordings"])}
    arms = {arm: list(models) for arm, models in draft["models"].items()}
    for arm, spec in (draft.get("optional_arms") or {}).items():
        arms.setdefault(arm, []).append(spec["model"])
    return {"tasks": tasks, "arms": arms}


def entry_problems(i: int, entry, design: dict) -> list[str]:
    where = f"walk entry {i}"
    if not isinstance(entry, dict):
        return [f"{where} is not an object"]
    out = []
    if set(entry) != set(FIELDS):
        missing = sorted(set(FIELDS) - set(entry))
        extra = sorted(set(entry) - set(FIELDS))
        return [f"{where} has fields missing {missing} and unknown {extra}; an entry holds exactly {list(FIELDS)}"]
    for k in STRING_FIELDS:
        if not isinstance(entry.get(k), str) or not visible(entry[k]):
            out.append(f"{where}: {k} is not a non-empty string")
    if out:
        return out
    if entry["counted"] is not False:
        out.append(f"{where}: counted is {entry['counted']!r}; a walk is a rehearsal, graded but never counted "
                   f"(plan CP6), so counted is exactly false")
    if not WALK_ID.fullmatch(entry["walk"]):
        out.append(f"{where}: walk {entry['walk']!r} is not one path segment")
    task, design_tasks = entry["task"], design["tasks"]
    if task not in design_tasks:
        out.append(f"{where}: task {task!r} is not a task of the design in force")
    else:
        if entry["half"] not in design_tasks[task]["halves"]:
            out.append(f"{where}: half {entry['half']!r} is not a half of {task}")
        if entry["wording"] not in design_tasks[task]["wordings"]:
            out.append(f"{where}: wording {entry['wording']!r} is not a wording of {task}")
    if entry["arm"] not in design["arms"]:
        out.append(f"{where}: arm {entry['arm']!r} is not an arm of the design in force")
    elif entry["model"] not in design["arms"][entry["arm"]]:
        out.append(f"{where}: model {entry['model']!r} is not a model of arm {entry['arm']}")
    return out


def has_a_file(folder: Path) -> bool:
    """W7D-R1-2: a regular file, never a symlink (a link to a file outside the study is not a walk record)."""
    return any(p.is_file() and not p.is_symlink() and p.name not in IGNORED_NAMES for p in folder.rglob("*"))


def check(base: Path = REHEARSALS, design: dict | None = None) -> tuple[list[str], int]:
    """(problems, number of registered walks)."""
    design = design_in_force() if design is None else design
    problems: list[str] = []
    reg = base / REGISTER_NAME
    if reg.is_symlink():
        return [f"rehearsals/{REGISTER_NAME} is a symlink; the register is a file in this folder"], 0
    if not reg.is_file():
        return [f"rehearsals/{REGISTER_NAME} is missing; an empty register is {{\"schema\": {SCHEMA}, "
                f"\"walks\": []}}, and a missing one is not empty"], 0
    try:
        text = reg.read_text()
    except OSError as exc:
        return [f"rehearsals/{REGISTER_NAME} cannot be read: {exc}"], 0
    except UnicodeDecodeError as exc:
        return [f"rehearsals/{REGISTER_NAME} is not JSON: {exc}"], 0
    try:
        doc = json.loads(text, object_pairs_hook=no_duplicate_keys)
    except DuplicateKey as exc:
        return [f"rehearsals/{REGISTER_NAME} has a duplicate key {exc.args[0]!r}; each key is written once"], 0
    except ValueError as exc:
        return [f"rehearsals/{REGISTER_NAME} is not JSON: {exc}"], 0
    if not isinstance(doc, dict) or set(doc) != set(TOP_KEYS):
        return [f"rehearsals/{REGISTER_NAME}: the top-level keys are exactly {list(TOP_KEYS)}"], 0
    if type(doc["schema"]) is not int or doc["schema"] != SCHEMA:
        problems.append(f"rehearsals/{REGISTER_NAME}: schema is {doc['schema']!r}, not {SCHEMA}")
    walks = doc["walks"]
    if not isinstance(walks, list):
        return problems + [f"rehearsals/{REGISTER_NAME}: walks is not a list"], 0
    registered: list[str] = []
    seen_fold: dict[str, str] = {}
    for i, entry in enumerate(walks):
        bad = entry_problems(i, entry, design)
        problems.extend(bad)
        if isinstance(entry, dict) and isinstance(entry.get("walk"), str):
            walk = entry["walk"]
            folded = walk.casefold()
            if walk in registered:
                problems.append(f"walk entry {i}: walk {walk!r} is registered twice")
            elif folded in seen_fold:
                # W7D-R1-1: one folder on a case-blind filesystem (the Mac), two on athena
                problems.append(f"walk entry {i}: walk {walk!r} and {seen_fold[folded]!r} differ only by case")
            seen_fold.setdefault(folded, walk)
            registered.append(walk)
    # W7D-R1-1: folders are matched by their exact listed names, never by a path lookup, which ignores case on APFS
    names = {p.name: p for p in base.iterdir()}
    for walk in dict.fromkeys(registered):
        if not WALK_ID.fullmatch(walk):
            continue
        folder = names.get(walk)
        if folder is None or folder.is_symlink() or not folder.is_dir():
            problems.append(f"walk {walk!r} is registered and rehearsals/{walk}/ does not exist as a folder")
        elif not has_a_file(folder):
            problems.append(f"walk {walk!r} is registered and rehearsals/{walk}/ holds no file")
    for p in sorted(base.iterdir()):
        name = p.name
        if name in IGNORED_NAMES:
            continue
        if p.is_dir() and not p.is_symlink():
            if name not in registered:
                problems.append(f"rehearsals/{name}/ is a walk folder the register does not list; every walk is "
                                f"registered with its reason (plan CP6)")
        elif name not in TOP_FILES:
            problems.append(f"rehearsals/{name} is a file beside the register, not a walk folder; only "
                            f"{list(TOP_FILES)} sit there")
    return problems, len(walks)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check the walk register against rehearsals/.")
    ap.add_argument("--check", action="store_true", required=True)
    ap.add_argument("--base", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        problems, n = check(Path(args.base) if args.base else REHEARSALS)
    except OSError as exc:
        problems, n = [f"rehearsals/ cannot be read: {exc}"], 0
    for p in problems:
        print(f"FAIL {p}")
    if problems:
        return 1
    if n == 0:
        print(f"ok, having registered 0 walks: rehearsals/ holds no walk folder and the register lists none, "
              f"so nothing here is evidence about any walk.")
    else:
        print(f"ok: {n} registered walk(s), each with its folder, none counted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
