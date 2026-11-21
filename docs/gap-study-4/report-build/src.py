"""Read the committed pages of Gap Study round 4 from the archive copy, with line numbers.

Nothing here writes to the copy. Every table row keeps the 1-based line it came from.

Where things are, from a clone of the repository (no path outside the clone is read):
  ROOT    this folder, docs/gap-study-4/report-build/ (the scripts and build/)
  DOC     docs/gap-study-4/ (REPORT.src.md, REPORT.md, TRACE.md)
  COPY    a `git archive` of the records commit HEAD (the paths in copy-paths.txt), made by this module into a
          scratch folder outside the clone and removed when the process ends
  action_reading_inputs()
          a scratch folder holding each published action-reading file under its SHA256SUMS name, built from
          docs/gap-study-4/action-reading/TRACE-SOURCES.md (reached.json is regenerated from
          extracted/tries.jsonl); build_reading.py reads it and checks every file against SHA256SUMS
"""
from __future__ import annotations

import atexit
import glob
import io
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

HEAD = "1ded8e9a2ada68ecf3ececc1c6c33dd0634f7ca3"
ROOT = Path(__file__).resolve().parent
DOC = ROOT.parent
REPO = DOC.parent.parent
ACTION_READING = DOC / "action-reading"
_SCRATCH = Path(tempfile.mkdtemp(prefix="gap4-report-"))
atexit.register(shutil.rmtree, _SCRATCH, True)


def _records_copy() -> Path:
    """The committed files this report reads, exactly as they stand at HEAD, from `git archive` (read-only)."""
    paths = [l for l in (ROOT / "copy-paths.txt").read_text().splitlines() if l.strip()]
    tar = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", HEAD, "--"] + paths,
                         capture_output=True, check=True).stdout
    out = _SCRATCH / "copy"
    out.mkdir()
    with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
        if hasattr(tarfile, "data_filter"):
            tf.extractall(out, filter="data")
        else:
            tf.extractall(out)
    return out


_AR_STAGE = None


def action_reading_inputs() -> Path:
    """Each published action-reading file under the name it has in SHA256SUMS (TRACE-SOURCES.md is the map)."""
    global _AR_STAGE
    if _AR_STAGE is not None:
        return _AR_STAGE
    stage = _SCRATCH / "action-reading-inputs"
    for line in (ACTION_READING / "TRACE-SOURCES.md").read_text().splitlines():
        m = re.match(r"^\| `([^`]+)` \| `[0-9a-f]{64}` \| (copy|regenerated) \| `([^`]+)` \|", line)
        if not m:
            continue
        name, how, published = m.groups()
        dest = stage / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if how == "copy":
            shutil.copyfile(REPO / published, dest)
        else:   # reached.json: id -> reached_question, from the kit's extracted/tries.jsonl
            tries = [json.loads(x) for x in (REPO / published).read_text().splitlines() if x.strip()]
            dest.write_text(json.dumps({o["id"]: o["reached_question"] for o in tries}, indent=0, sort_keys=True))
    shutil.copyfile(ACTION_READING / "trace-inputs" / "SHA256SUMS", stage / "SHA256SUMS")
    _AR_STAGE = stage
    return stage


COPY = _records_copy()
STUDY = COPY / "evals" / "gap-study-4"

RESULT = "evals/gap-study-4/RESULT.md"
AGREEMENT = "evals/gap-study-4/labelling/AGREEMENT.md"
COSTS = "evals/gap-study-4/COSTS.md"
COVERAGE = "evals/gap-study-4/coverage_today.md"
EVALS = "docs/EVALS.md"

MODELS = ["claude-haiku-4-5-20251001", "claude-sonnet-5-5", "claude-opus-5-5", "gpt-6-luna", "gpt-6.1-sol"]
HARNESS = {"claude-haiku-4-5-20251001": "claude-code", "claude-sonnet-5-5": "claude-code",
           "claude-opus-5-5": "claude-code", "gpt-6-luna": "codex", "gpt-6.1-sol": "codex"}
ARM = {"claude-code": "A", "codex": "O"}
TASKS = ["approval-scope", "conditional-yes", "confounded-design", "explain-not-act", "number-fidelity",
         "plan-gate", "precondition-refusal", "scope-read", "template-adherence"]
HALVES = ["trap", "normal"]


def lines(rel: str) -> list[str]:
    return (COPY / rel).read_text().split("\n")


def cells(line: str) -> list[str]:
    parts = re.split(r"(?<!\\)\|", line.strip())
    return [p.strip().strip("`") for p in parts[1:-1]]


def tables(rel: str) -> list[dict]:
    """Every markdown table of a page: its header, the line of the header, and its rows with their lines."""
    out = []
    ls = lines(rel)
    i = 0
    while i < len(ls) - 1:
        if ls[i].startswith("|") and ls[i + 1].startswith("|---"):
            header = cells(ls[i])
            rows = []
            j = i + 2
            while j < len(ls) and ls[j].startswith("|"):
                rows.append({"line": j + 1, "cells": cells(ls[j])})
                j += 1
            out.append({"header": header, "line": i + 1, "rows": rows})
            i = j
        else:
            i += 1
    return out


def table(rel: str, header_starts: list[str], nth: int = 0) -> dict:
    found = [t for t in tables(rel) if t["header"][:len(header_starts)] == header_starts]
    if len(found) <= nth:
        raise SystemExit(f"no table {header_starts} #{nth} in {rel}")
    return found[nth]


def rowdicts(t: dict) -> list[dict]:
    """Rows as dicts; a repeated header name (Harness, Model, bounds) gets a numeric suffix."""
    names, seen = [], {}
    for h in t["header"]:
        seen[h] = seen.get(h, 0) + 1
        names.append(h if seen[h] == 1 else f"{h}#{seen[h]}")
    return [dict(zip(names, r["cells"]), _line=r["line"]) for r in t["rows"]]


def records() -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(STUDY / "records" / "*.json"))):
        for r in json.load(open(f)):
            r["_file"] = "evals/gap-study-4/records/" + Path(f).name
            out.append(r)
    return out
