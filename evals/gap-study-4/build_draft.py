#!/usr/bin/env python3
"""Assemble the draft from this round's task files and pinned interfaces.

No owner inputs are accepted by the CLI. Pending values remain visible and the
closed statistical design is withheld until every pending item is supplied.
Only named frozen metadata is read from the prior round, through prior_metadata.
"""
from __future__ import annotations
import argparse
import collections
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import study
import variants
import harness_bookkeeping
from box import image_lock, run_take, take_config

PENDING = run_take.PENDING
CLAUDE = harness_bookkeeping.CLAUDE_CODE
CODEX, GEMINI = run_take.CODEX, run_take.GEMINI
MODELS = {"A": ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5-20251001"),
          "O": ("gpt-6.1-sol", "gpt-6-luna"),
          "G": ("gemini-3.8-flash", "gemini-3.5-flash-lite")}
HARNESSES = {"A": CLAUDE, "O": CODEX, "G": GEMINI}
DRAFT = HERE / "prereg-draft.json"
PRIOR_COMMIT = "e2979b3143081824aadea73523ec41af30c1ddb1"
PRIOR_FILE = "evals/gap-study-3/prereg.json"
PRIOR_KEYS = ("limitations_lines", "leak_words", "leak_word_dropped", "leak_context_excusals")


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prior_metadata():
    """The one old-round read: named frozen metadata, never results or modules."""
    got = subprocess.run(["git", "-C", str(REPO), "show", f"{PRIOR_COMMIT}:{PRIOR_FILE}"],
                         capture_output=True, check=True)
    source = json.loads(got.stdout)
    return {key: source[key] for key in PRIOR_KEYS}


def source_tasks(root):
    paths = sorted((root / "tasks").glob("*.json"))
    if not paths:
        raise ValueError("no tasks")
    ids = [p.stem for p in paths]
    if "confounded-design-unprompted" in ids:
        raise ValueError("the dropped task cannot run")
    if set(ids) != {p.stem for p in (root / "variants").glob("*.json")}:
        raise ValueError("task and wording files must pair exactly")
    result = []
    for path in paths:
        task = variants.load_task(path.stem, root=root)
        wording = variants.load_variants(path.stem, root=root)
        result.append({"id": path.stem, "task_sha256": sha(path.read_bytes()),
                       "variants_sha256": sha((root / "variants" / path.name).read_bytes()),
                       "grader": task["grader"], "factor": task["factor"],
                       "wordings": [w["id"] for w in wording["wordings"]],
                       "cells": variants.task_cells(task, wording)})
    return result


def source_locks(root):
    result = [{"path": str(p.relative_to(root)), "sha256": sha(p.read_bytes()),
               "lock": image_lock.load(str(p))} for p in sorted((root / "box").rglob("image.lock"))]
    if sorted(item["lock"]["image"] for item in result) != sorted(image_lock.IMAGES):
        raise ValueError("one lock for every image is required")
    return result


def version_pins(locks, table):
    result = {}
    profiles = table["pin_profiles"]
    for arm, harness in HARNESSES.items():
        lock = next(item["lock"] for item in locks if item["lock"]["image"] == "take-" + arm.lower())
        version = lock["harness"]["version"]
        result[harness] = {}
        for model in MODELS[arm]:
            pin = profiles.get(harness, {}).get(model, {"permission_mode": PENDING, "version": PENDING})
            if set(pin) != {"permission_mode", "version"} or any(not isinstance(v, str) or not v.strip() for v in pin.values()):
                raise ValueError("a pin is permission_mode and version, both non-empty strings")
            if pin["version"] != PENDING and version != PENDING and pin["version"] != version:
                raise ValueError("routing and image versions disagree")
            ready = PENDING not in pin.values() and version != PENDING
            result[harness][model] = {**pin, "image_version": version,
                                       "agent_version": version if ready else None}
    return result


def identity_id(prefix, values):
    # JSON arrays are unambiguous; full sha256, not truncated or based on order.
    return prefix + "-" + sha(json.dumps(values, separators=(",", ":"), ensure_ascii=True).encode())


def assemble(root=None):
    root = HERE if root is None else Path(root)
    tasks = source_tasks(root)
    locks = source_locks(root)
    table = json.loads((root / "routing.json").read_bytes())
    pins = version_pins(locks, table)
    rows = []
    for arm, models in MODELS.items():
        for model in models:
            harness = HARNESSES[arm]
            for task in tasks:
                for cell in task["cells"]:
                    identity = [arm, task["id"], cell["half"], model, harness]
                    rows.append({"arm": arm, "task": task["id"], **cell, "model": model,
                                 "agent": {"harness": harness, "version": pins[harness][model]["agent_version"]},
                                 "half_cell": identity_id("h", identity),
                                 "slot": identity_id("s", identity + [cell["wording"], cell["repeat"], cell["pressure"]])})
    return {"study": study.STUDY_TITLE, "status": "DRAFT", "tasks": tasks,
            "models": {a: list(ms) for a, ms in MODELS.items()}, "arms": list(study.ARMS),
            "optional_arms": {"C": {"model": "claude-fable-5-1", "status": "optional (D2 B)",
                                    "cut": "first cut if the freeze slips (plan 345)", "rows": 0, "tries": 0}},
            "amendments": {a: "Javier's letter \"D8: B2\", Tue 6 Oct 2026 23:43:50 EDT" for a in ("O", "G")},
            "n": variants.TRIES_PER_HALF, "wordings": variants.N_WORDINGS, "repeats": variants.REPEATS,
            "rows": rows, "counts": {"pairs": len(tasks), "by_arm": dict(collections.Counter(r["arm"] for r in rows)),
                                      "tries": len(rows), "half_cells": len({r["half_cell"] for r in rows})},
            "take_order": None, "take_order_seed": None, "take_order_function": "freeze.planned_order",
            "take_order_rule": "in one randomised order interleaved across arm, model, task and half, seeded from the review commit as round 3 seeded its order.",
            "order_carry": "prereg.py --order is the earlier per-axis positive/control order; CP2 must replace it.",
            "image_locks": locks, "version_pins": pins}
