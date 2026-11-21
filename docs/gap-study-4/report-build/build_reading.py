#!/usr/bin/env python3
"""Emit the action-reading tables of REPORT.md (revision 2) and the trace of each cell.

The action reading is EXPLORATORY and is not on the study's records line. Its page is read from the copy under
inputs/action-reading/ (sha256 in SHA256SUMS there, checked here). No number is typed: each cell is copied from a
line of that page, and the page's "As graded" column is compared, cell by cell, with the study's result page before
anything is written.

Run after tools/build_tables.py. Writes build/fragments/ar_*.md, build/trace_reading.tsv, build/facts_reading.json.
Exit 1 on any mismatch.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import src  # noqa: E402

IN = src.action_reading_inputs()
REL = "inputs/action-reading/ACTION-READING.md"
OUT = src.ROOT / "build"
FRAG = OUT / "fragments"
TRACE: list[tuple[str, str, str, str, str]] = []
PROBLEMS: list[str] = []

# the copies are the files the trace cites: refuse a changed one
for line in (IN / "SHA256SUMS").read_text().splitlines():
    digest, name = line.split()
    if hashlib.sha256((IN / name).read_bytes()).hexdigest() != digest:
        PROBLEMS.append(f"inputs/action-reading/{name} does not match SHA256SUMS")

LINES = (IN / "ACTION-READING.md").read_text().split("\n")


def tr(table, cell, value, where):
    TRACE.append((table, cell, str(value), REL, str(where)))


def write(name, text):
    (FRAG / f"{name}.md").write_text(text.rstrip("\n") + "\n")


def cells(line):
    return [p.strip() for p in line.strip().strip("|").split("|")]


def section(title):
    """(start, end) line indexes of a '## ' section."""
    start = next(i for i, l in enumerate(LINES) if l == f"## {title}")
    end = next((i for i in range(start + 1, len(LINES)) if LINES[i].startswith("## ")), len(LINES))
    return start, end


def task_tables(title):
    """{task: (header line index, [(line index, cells)])} for a section with one '### `task`' table per task."""
    start, end = section(title)
    out, task = {}, None
    for i in range(start, end):
        l = LINES[i]
        m = re.match(r"^### `([a-z-]+)`$", l)
        if m:
            task = m.group(1)
            continue
        if l.startswith("|") and task is not None:
            if task not in out:
                out[task] = (i, [])
            elif not l.startswith("|---"):
                out[task][1].append((i, cells(l)))
    return out


HALF = task_tables("Per half-cell")
UNIT = task_tables("Units right on both versions")
if sorted(HALF) != sorted(src.TASKS) or sorted(UNIT) != sorted(src.TASKS):
    PROBLEMS.append("the reading does not print the nine tasks in both sections")

COLS = ["As graded", "Exact wording", "Action (reg.)", "Content (reg.)", "Both (reg.)", "Action (contract)",
        "Content (contract)", "Both (contract)"]
H: dict[tuple[str, str, str], dict] = {}      # task, model, half -> {col: text, _line}
U: dict[tuple[str, str], dict] = {}
for task in src.TASKS:
    hl, rows = HALF[task]
    if cells(LINES[hl]) != ["Version", "Model"] + COLS:
        PROBLEMS.append(f"half-cell header differs for {task}")
    for i, c in rows:
        H[(task, c[1].strip("`"), c[0])] = dict(zip(COLS, c[2:]), _line=i + 1)
    hl, rows = UNIT[task]
    if cells(LINES[hl]) != ["Model"] + COLS:
        PROBLEMS.append(f"unit header differs for {task}")
    for i, c in rows:
        U[(task, c[0].strip("`"))] = dict(zip(COLS, c[1:]), _line=i + 1)
if len(H) != 90 or len(U) != 45:
    PROBLEMS.append(f"expected 90 half-cells and 45 unit rows in the reading, found {len(H)} and {len(U)}")

# ---------------------------------------------------------------------------------------------
# the reading's "As graded" column against the study's result page (the traced cells of build_tables.py)
study = {}
for line in (OUT / "trace_tables.tsv").read_text().splitlines():
    t, c, v, f, w = line.split("\t")
    study[(t, c)] = v
RAW = re.compile(r"^(\d+) right, (\d+) wrong, (\d+) stop, of (\d+)$")
match_half = match_unit = 0
for (task, model, half), row in H.items():
    tname = "raw_claude_code" if src.HARNESS[model] == "claude-code" else "raw_codex"
    m = RAW.match(study.get((tname, f"{task} / {model} / {half}"), ""))
    if not m or row["As graded"] != f"{m.group(1)} of {m.group(4)}":
        PROBLEMS.append(f"As graded differs from RESULT.md for {task} / {model} / {half}: reading {row['As graded']}")
    else:
        match_half += 1
for (task, model), row in U.items():
    if row["As graded"] != study.get(("units", f"{task} / {model}")):
        PROBLEMS.append(f"As graded units differ from RESULT.md for {task} / {model}: reading {row['As graded']}")
    else:
        match_unit += 1

COUNT = re.compile(r"^(\d+) of (\d+)")


def k(text):
    return int(COUNT.match(text).group(1))


LEGEND = {", not scored alone": " ‡", ", cannot separate versions": " †"}


def short(text):
    """A cell with the reading's two marks shortened; the unsettled note is kept in words."""
    for long_, mark in LEGEND.items():
        text = text.replace(long_, mark)
    text = text.replace(" (1 not yet settled: disputed or unread)", " (1 disputed)")
    if not re.match(r"^(\d+ of \d+( \(1 disputed\))?( [‡†])?|no key)$", text):
        PROBLEMS.append(f"unexpected cell text: {text}")
    return text


def code(s):
    return f"`{s}`"


# ---------------------------------------------------------------------------------------------
# appendix copies, as the reading prints them (rows verbatim)
def copy_section(name, tables, first_cols):
    out = []
    for task in src.TASKS:
        hl, rows = tables[task]
        out += [f"**{code(task)}**", "", LINES[hl], LINES[hl + 1]]
        for i, c in rows:
            out.append(LINES[i])
            key = " / ".join([task] + [x.strip("`") for x in c[:first_cols]])
            tr(name, key, " · ".join(c[first_cols:]), i + 1)
        out.append("")
    write(name, "\n".join(out))


copy_section("ar_halfcells", HALF, 2)
copy_section("ar_units_full", UNIT, 1)

# reader agreement per task AND model. The reading's page prints it per task over the five models; a count over
# models is not printed in this report, so it is recounted here per model from the readers' label files with the
# page's own rule (merge.py: a try is "read by both" unless its route is aborted or harness-error; "agreed on the
# class" compares stall_cause for a try that never received the question and content_class otherwise; "agreed on
# every field" compares content_class, stall_cause, action_class, pushback and the four facts), and the per-task
# sums are compared with the page's rows before anything is written.
ids = json.loads((IN / "ids.json").read_text())
reached = json.loads((IN / "reached.json").read_text())      # id -> reached_question, from the kit's extracted/tries.jsonl


def load_labels(reader):
    out = {}
    for f in sorted((IN / "labels" / reader).glob("*.json")):
        for lab in json.loads(f.read_text())["labels"]:
            if lab["id"] in out:
                PROBLEMS.append(f"{reader}: {lab['id']} labelled twice")
            out[lab["id"]] = lab
    return out


RA, RB = load_labels("ra"), load_labels("rb")
FIELDS = ("content_class", "stall_cause", "action_class", "pushback")
AG = {}
for oid, kk in ids.items():
    if kk["route"] in ("harness-error", "aborted"):
        continue
    l1, l2 = RA.get(oid), RB.get(oid)
    if l1 is None or l2 is None:
        continue
    a = AG.setdefault((kk["task"], kk["model"]), [0, 0, 0])
    prim = "content_class" if reached[oid] else "stall_cause"
    a[0] += 1
    a[1] += int(l1.get(prim) == l2.get(prim))
    a[2] += int(all(l1.get(f) == l2.get(f) for f in FIELDS) and (l1.get("facts") or {}) == (l2.get("facts") or {}))
start, end = section("Reader agreement per task")
page_rows = {cells(LINES[i])[0].strip("`"): (i + 1, cells(LINES[i])[1:]) for i in range(start, end) if LINES[i].startswith("| `")}
body = []
for task in src.TASKS:
    line, (both, klass, every) = page_rows[task]
    mine = [sum(AG[(task, m)][j] for m in src.MODELS) for j in range(3)]
    if [str(mine[0]), f"{mine[1]} of {mine[0]}", f"{mine[2]} of {mine[0]}"] != [both, klass, every]:
        PROBLEMS.append(f"reader agreement recount differs from the page for {task}: {mine} against {both, klass, every}")
    row = []
    for m in src.MODELS:
        n, c, f = AG[(task, m)]
        text = f"{c} · {f}" + ("" if n == 20 else f" (of {n})")
        tr("ar_agreement", f"{task} / {m}", f"class {c} of {n}, every field {f} of {n}", f"recounted per model from inputs/action-reading/labels/ra and labels/rb with ids.json and reached.json by tools/build_reading.py; the five models' counts add to the page's row on line {line}")
        row.append(text)
    body.append(f"| {code(task)} | " + " | ".join(row) + " |")
write("ar_agreement", "\n".join(["| Task | " + " | ".join(code(m) for m in src.MODELS) + " |", "|---|" + "---|" * len(src.MODELS)] + body))

# stall causes, copied
for name, title, keycols in (("ar_stalls", "Stall causes", 2),):
    start, end = section(title)
    rows = [(i, LINES[i]) for i in range(start, end) if LINES[i].startswith("|")]
    for i, l in rows[2:]:
        c = cells(l)
        tr(name, " / ".join(x.strip("`") for x in c[:keycols]), " · ".join(c[keycols:]), i + 1)
    write(name, "\n".join(l for _, l in rows))

# ---------------------------------------------------------------------------------------------
# body table 1: units, as graded beside the reading's two "both" columns
head = "| Task | " + " | ".join(code(m) for m in src.MODELS) + " |"
sep = "|---|" + "---|" * len(src.MODELS)
body = []
for task in src.TASKS:
    row = []
    for m in src.MODELS:
        u = U[(task, m)]
        g, r, c = u["As graded"], short(u["Both (reg.)"]), short(u["Both (contract)"])
        n = g.split(" of ")[1]
        if not (r.split(" of ")[1].split()[0] == n and c.split(" of ")[1].split()[0] == n):
            PROBLEMS.append(f"unit n differs within {task} / {m}")
        text = f"{k(g)} · {k(r)} · {k(c)}"
        if n != "10":
            text += f" (of {n})"
        if "(1 disputed)" in r or "(1 disputed)" in c:
            text += " (1 disputed)"
        if "†" in c:
            text += " †"
        tr("ar_units", f"{task} / {m}", f"{g} · {u['Both (reg.)']} · {u['Both (contract)']}", u["_line"])
        row.append(text)
    body.append(f"| {code(task)} | " + " | ".join(row) + " |")
write("ar_units", "\n".join([head, sep] + body))

# body table 2: every half-cell where the reading's count of the whole move differs from the graded count
head = "| Task | Half | Model | As graded | Action (registered) | Content (registered) | Both (registered) | Both (contract) |"
body = []
ndiff = 0
for task in src.TASKS:
    for half in src.HALVES:
        for m in src.MODELS:
            h = H[(task, m, half)]
            if k(h["Both (reg.)"]) == k(h["As graded"]) and k(h["Both (contract)"]) == k(h["As graded"]):
                continue
            ndiff += 1
            vals = [h["As graded"], short(h["Action (reg.)"]), short(h["Content (reg.)"]),
                    short(h["Both (reg.)"]), short(h["Both (contract)"])]
            tr("ar_diff", f"{task} / {half} / {m}", " · ".join(h[c] for c in ("As graded", "Action (reg.)", "Content (reg.)", "Both (reg.)", "Both (contract)")), h["_line"])
            body.append(f"| {code(task)} | {half} | {code(m)} | " + " | ".join(vals) + " |")
write("ar_diff", "\n".join([head, "|---|---|---|---|---|---|---|---|"] + body))

# ---------------------------------------------------------------------------------------------
# facts the prose leans on, each computed from the copied page or the rulings file
rulings = json.loads((IN / "rulings.json").read_text())
ids_tasks = {}
dec = (IN / "DECISIVE.md").read_text().split("\n")
for l in dec:
    m = re.match(r"^## `(t[0-9a-f]+)` · `([a-z-]+)`$", l)
    if m:
        ids_tasks[m.group(1)] = m.group(2)


def both_rows(pred):
    return sorted(f"{t} / {m} / {h}" for (t, m, h), r in H.items() if pred(r))


def dirs(col):
    """Per model: half-cells where the column is above, and below, the graded count."""
    return {m: [sum(1 for (t, mm, h), r in H.items() if mm == m and k(r[col]) > k(r["As graded"])),
                sum(1 for (t, mm, h), r in H.items() if mm == m and k(r[col]) < k(r["As graded"]))] for m in src.MODELS}


def stall_rows():
    start, end = section("Stall causes")
    return {(c[0].strip("`"), c[1].strip("`")): c for c in (cells(LINES[i]) for i in range(start, end) if LINES[i].startswith("| `"))}


S = stall_rows()
facts = {
    "ar_as_graded_matches": {"half_cells": match_half, "unit_rows": match_unit},
    "ar_diff_rows": ndiff,
    "ar_rulings": {"count": len(rulings),
                   "by_task": sorted(ids_tasks[i] for i in rulings),
                   "matches_reader": sorted(v["_by"].rsplit(" ", 1)[1] for v in rulings.values())},
    "ar_decisive": {"count": len(ids_tasks), "open": sorted(i for i in ids_tasks if i not in rulings),
                    "open_task": sorted(ids_tasks[i] for i in ids_tasks if i not in rulings)},
    "ar_disputed_half_cells": both_rows(lambda r: "disputed" in r["Both (reg.)"] or "disputed" in r["Both (contract)"]),
    "ar_no_wording_key_half_cells": sum(1 for r in H.values() if r["Exact wording"] == "no key"),
    "ar_both_reg_dirs": dirs("Both (reg.)"),
    "ar_both_contract_dirs": dirs("Both (contract)"),
    "ar_action_not_scored_alone_reg": sorted({t for (t, m, h), r in H.items() if "not scored alone" in r["Action (reg.)"]}),
    "ar_action_not_scored_alone_contract": sorted({t for (t, m, h), r in H.items() if "not scored alone" in r["Action (contract)"]}),
    "ar_cannot_separate": sorted({t for (t, m, h), r in H.items() if "cannot separate" in r["Both (contract)"]}),
    "ar_units_graded_zero_reading_more": sorted(f"{t} / {m}" for (t, m), r in U.items() if k(r["As graded"]) == 0 and k(r["Both (reg.)"]) > 0),
    "ar_units_reading_below_graded": sorted(f"{t} / {m}" for (t, m), r in U.items() if k(r["Both (reg.)"]) < k(r["As graded"])),
    "ar_units_reading_above_graded": {m: sorted(t for (t, mm), r in U.items() if mm == m and k(r["Both (reg.)"]) > k(r["As graded"])) for m in src.MODELS},
    "ar_units_dirs": {m: [sum(1 for (t, mm), r in U.items() if mm == m and k(r["Both (reg.)"]) > k(r["As graded"])),
                          sum(1 for (t, mm), r in U.items() if mm == m and k(r["Both (reg.)"]) < k(r["As graded"]))] for m in src.MODELS},
    "ar_agreement_lowest_class": min((v[1] / v[0], f"{t} / {m}: {v[1]} of {v[0]}") for (t, m), v in AG.items())[1],
    "ar_agreement_class_all": sorted(f"{t} / {m}" for (t, m), v in AG.items() if v[1] == v[0]).__len__(),
    "ar_agreement_cells": len(AG),
    "ar_stall_rows": len(S),
    "ar_sol_stall_tasks_all_20": sorted(t for (t, m), c in S.items() if m == "gpt-6.1-sol" and c[2] == "20"),
    "ar_tasks_exact_wording_all_no_key_units": sorted({t for (t, m), r in U.items() if r["Exact wording"] == "no key"}),
}
(OUT / "facts_reading.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False) + "\n")
(OUT / "trace_reading.tsv").write_text("".join("\t".join(r) + "\n" for r in TRACE))
if PROBLEMS:
    print("\n".join("PROBLEM: " + p for p in PROBLEMS))
    raise SystemExit(1)
print(f"ok: {len(TRACE)} traced cells of the action reading; As graded equals the result page in {match_half} of 90 half-cells and {match_unit} of 45 unit rows; {ndiff} half-cells differ")
