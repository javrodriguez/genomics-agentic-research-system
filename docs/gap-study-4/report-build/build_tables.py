#!/usr/bin/env python3
"""Emit every table of REPORT.md from the committed pages, and the trace of each cell.

No number is typed here: each cell is read from a committed page (with its line) or recounted from
records/*.json, and each recount is compared with the page before anything is written.

Writes build/fragments/<name>.md and build/trace_tables.tsv. Exit 1 on any mismatch.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import src  # noqa: E402

OUT = src.ROOT / "build"
FRAG = OUT / "fragments"
FRAG.mkdir(parents=True, exist_ok=True)

TRACE: list[tuple[str, str, str, str, str]] = []   # table, cell, value, file, line-or-rule
PROBLEMS: list[str] = []


def tr(table: str, cell: str, value: str, file: str, where) -> None:
    TRACE.append((table, cell, str(value), file, str(where)))


def write(name: str, text: str) -> None:
    (FRAG / f"{name}.md").write_text(text.rstrip("\n") + "\n")


def code(s: str) -> str:
    return f"`{s}`"


def short(model: str) -> str:
    return code(model)


# ---------------------------------------------------------------------------------------------
# the result page's tables
bounds = src.rowdicts(src.table(src.RESULT, ["Arm", "Task", "Model", "Harness", "Half", "Stops as failures"]))
holds = src.rowdicts(src.table(src.RESULT, ["Arm", "Task", "Model", "Harness", "Tries right, both halves"]))
within = src.rowdicts(src.table(src.RESULT, ["Family", "Harness", "Model", "Harness", "Model", "Task"], 0))
between = src.rowdicts(src.table(src.RESULT, ["Family", "Harness", "Model", "Harness", "Model", "Task"], 1))
across = src.rowdicts(src.table(src.RESULT, ["Family", "Harness", "Model", "Harness", "Model", "Slots both completed"]))
power = src.rowdicts(src.table(src.RESULT, ["First model of the stronger-against-weaker pair"]))
stopped = src.table(src.RESULT, ["Arm", "Task", "Half", "Model", "Harness", "Pauses with a forbidden change"])
reach = src.rowdicts(src.table(src.RESULT, ["Arm", "Task", "Half", "Model", "Harness", "Takes", "Takes with an event"]))
flagged = src.rowdicts(src.table(src.RESULT, ["Arm", "Harness", "Model", "Task", "On the list"]))
chance = src.table(src.RESULT, ["Tries in the cell"])
routes = src.rowdicts(src.table(src.RESULT, ["Arm", "Task", "Model", "Harness", "Half", "Takes", "Non-zero exit (the agent's own exit)"]))
coverage_rows = src.rowdicts(src.table(src.RESULT, ["Arm", "Task", "Half", "Model", "Harness", "Version"]))

B = {(r["Task"], r["Model"], r["Half"]): r for r in bounds if r["Arm"] in ("A", "O")}
H = {(r["Task"], r["Model"]): r for r in holds if r["Arm"] in ("A", "O")}

# ---------------------------------------------------------------------------------------------
# recount from records/*.json and compare with the page, cell by cell
recs = src.records()
by_cell = collections.defaultdict(list)
for r in recs:
    by_cell[(r["task"], r["model"], r["half"])].append(r)

RAW = re.compile(r"^(\d+) right, (\d+) wrong, (\d+) stop, of (\d+)$")
for key, row in B.items():
    m = RAW.match(row["Stops raw"])
    if not m:
        PROBLEMS.append(f"raw cell unreadable at RESULT.md:{row['_line']}: {row['Stops raw']}")
        continue
    right, wrong, stop, n = map(int, m.groups())
    rr = [r for r in by_cell[key] if r["views"] is not None]
    c = collections.Counter(r["views"]["raw"] for r in rr)
    if (c["right"], c["wrong"], c["stop"], len(rr)) != (right, wrong, stop, n):
        PROBLEMS.append(f"recount differs at RESULT.md:{row['_line']} {key}: page {right, wrong, stop, n}, "
                        f"records {c['right'], c['wrong'], c['stop'], len(rr)}")
    if row["Stops as failures"] != f"{right} of {n}":
        PROBLEMS.append(f"strict view differs from raw at RESULT.md:{row['_line']}")
    he = sum(1 for r in by_cell[key] if r["views"] is None)
    page_he = row["Harness errors"]
    want = "none" if he == 0 else f"{he} left the denominator"
    if page_he != want:
        PROBLEMS.append(f"harness-error count differs at RESULT.md:{row['_line']}: page {page_he}, records {want}")
if len(B) != 90:
    PROBLEMS.append(f"expected 90 run half-cells on the page, found {len(B)}")
for (task, model), row in H.items():
    t, n_ = B[(task, model, "trap")], B[(task, model, "normal")]
    k = int(t["Stops as failures"].split(" of ")[0]) + int(n_["Stops as failures"].split(" of ")[0])
    n = int(t["Stops as failures"].split(" of ")[1]) + int(n_["Stops as failures"].split(" of ")[1])
    if row["Tries right, both halves"] != f"{k} of {n}":
        PROBLEMS.append(f"holds cell differs at RESULT.md:{row['_line']}")
    if (row["Holds"] == "yes") != (k == n):
        PROBLEMS.append(f"holds flag differs at RESULT.md:{row['_line']}")

# ---------------------------------------------------------------------------------------------
# T-raw: right, wrong, stop per half-cell, one table per harness
def raw_cell(task, model, half, tname):
    row = B[(task, model, half)]
    m = RAW.match(row["Stops raw"])
    right, wrong, stop, n = m.groups()
    text = f"{right} · {wrong} · {stop}"
    if n != "10":
        text += f" (of {n})"
    tr(tname, f"{task} / {model} / {half}", row["Stops raw"], src.RESULT, row["_line"])
    return text


for harness, name in (("claude-code", "raw_claude_code"), ("codex", "raw_codex")):
    models = [m for m in src.MODELS if src.HARNESS[m] == harness]
    head = "| Task | " + " | ".join(f"{short(m)} trap | normal" for m in models) + " |"
    sep = "|---|" + "---|---|" * len(models)
    body = []
    for task in src.TASKS:
        cellsx = []
        for m in models:
            for half in src.HALVES:
                cellsx.append(raw_cell(task, m, half, name))
        body.append(f"| {code(task)} | " + " | ".join(cellsx) + " |")
    write(name, "\n".join([head, sep] + body))

# T-holds: tries right on both halves added, and the holds flag
head = "| Task | " + " | ".join(short(m) for m in src.MODELS) + " |"
sep = "|---|" + "---|" * len(src.MODELS)
body = []
for task in src.TASKS:
    cellsx = []
    for m in src.MODELS:
        row = H[(task, m)]
        text = row["Tries right, both halves"]
        if row["Holds"] == "yes":
            text += ", **holds**"
        if row["Harness errors"] != "none":
            text += f" ({row['Harness errors']})"
        tr("holds", f"{task} / {m}", f"{row['Tries right, both halves']}; holds {row['Holds']}; "
           f"harness errors {row['Harness errors']}", src.RESULT, row["_line"])
        cellsx.append(text)
    body.append(f"| {code(task)} | " + " | ".join(cellsx) + " |")
write("holds", "\n".join([head, sep] + body))

# T-bounds: the strict count with its exact bounds, long form
head = ("| Task | Half | Model | Harness | Right, stops as failures | Exact 0.95 bounds | Right, stops excluded | "
        "Exact 0.95 bounds |")
body = []
for task in src.TASKS:
    for half in src.HALVES:
        for m in src.MODELS:
            row = B[(task, m, half)]
            tr("bounds", f"{task} / {half} / {m}", f"{row['Stops as failures']} [{row['bounds']}]; "
               f"{row['Stops excluded']} [{row['bounds#2']}]", src.RESULT, row["_line"])
            body.append(f"| {code(task)} | {half} | {short(m)} | {code(src.HARNESS[m])} | {row['Stops as failures']} | "
                        f"{row['bounds']} | {row['Stops excluded']} | {row['bounds#2'] or 'no bounds printed'} |")
write("bounds", "\n".join([head, "|---|---|---|---|---|---|---|---|"] + body))

# T-wrong: what the wrong moves were, from the records' grader labels
head = "| Task | Half | Model | Harness | Wrong at the probe | The grader's labels for them |"
body = []
for task in src.TASKS:
    for half in src.HALVES:
        for m in src.MODELS:
            rr = [r for r in by_cell[(task, m, half)] if r["views"] is not None and r["views"]["raw"] == "wrong"]
            if not rr:
                continue
            c = collections.Counter(r["label"] for r in rr)
            labels = ", ".join(f"{code(k)} {v}" for k, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))
            n = len([r for r in by_cell[(task, m, half)] if r["views"] is not None])
            tr("wrong_labels", f"{task} / {half} / {m}", f"{len(rr)} of {n}: " + "; ".join(f"{k} {v}" for k, v in sorted(c.items())),
               f"evals/gap-study-4/records/{task}.json",
               f"records with task, half, model as named and views.raw == wrong, counted by label; the count equals "
               f"the wrong count at {src.RESULT}:{B[(task, m, half)]['_line']}")
            body.append(f"| {code(task)} | {half} | {short(m)} | {code(src.HARNESS[m])} | {len(rr)} of {n} | {labels} |")
write("wrong_labels", "\n".join([head, "|---|---|---|---|---|---|"] + body))

# stop labels: every stop's grader label, checked to be one of two
stop_labels = collections.Counter()
for r in recs:
    if r["views"] is not None and r["views"]["raw"] == "stop":
        stop_labels[(r["route"], r["label"])] += 1
if set(stop_labels) - {("graded", "did-not-reach"), ("aborted", "aborted")}:
    PROBLEMS.append(f"a stop carries a label this report does not describe: {sorted(stop_labels)}")
aborted = [(r["task"], r["half"], r["model"]) for r in recs if r["route"] == "aborted"]
if sorted(aborted) != sorted([("plan-gate", "normal", "claude-opus-5-5")] * 2 + [("plan-gate", "normal", "claude-sonnet-5-5")]):
    PROBLEMS.append(f"aborted takes are not where the page says: {aborted}")

# T-units: units right on both halves, per task and model, from the tested rows
UNITS: dict[tuple[str, str], tuple[str, int]] = {}
for r in within + between:
    if r["Family"] == "descriptive, no test" or r["Task"] == "the tasks that run":
        continue
    for model, val in ((r["Model"], r["Units right (first)"]), (r["Model#2"], r["Units right (second)"])):
        if model not in src.MODELS or val == "no takes":
            continue
        key = (r["Task"], model)
        if key in UNITS and UNITS[key][0] != val:
            PROBLEMS.append(f"units differ between rows for {key}: {UNITS[key][0]} and {val} (RESULT.md:{r['_line']})")
        UNITS.setdefault(key, (val, r["_line"]))
head = "| Task | " + " | ".join(short(m) for m in src.MODELS) + " |"
body = []
for task in src.TASKS:
    cellsx = []
    for m in src.MODELS:
        val, line = UNITS[(task, m)]
        tr("units", f"{task} / {m}", val, src.RESULT, line)
        cellsx.append(val)
    body.append(f"| {code(task)} | " + " | ".join(cellsx) + " |")
write("units", "\n".join([head, sep] + body))

# T-tests: the rows at or under alpha, as printed
def test_row(r, tname):
    tr(tname, f"{r['Model']} against {r['Model#2']} / {r['Task']}",
       f"{r['Units right (first)']}; {r['Units right (second)']}; p {r['Fisher p']}; Holm {r['Holm-adjusted p']}; "
       f"{r['At or under alpha']}", src.RESULT, r["_line"])
    return (f"| {r['Family']} | {short(r['Model'])} in {code(r['Harness'])} | {short(r['Model#2'])} in {code(r['Harness#2'])} | "
            f"{code(r['Task']) if r['Task'] != 'the tasks that run' else r['Task']} | {r['Units right (first)']} | "
            f"{r['Units right (second)']} | {r['Incomplete units']} | {r['Fisher p']} | {r['Holm-adjusted p']} | "
            f"{r['At or under alpha']} |")


head = ("| Family | First | Second | Task | Units right (first) | Units right (second) | Incomplete units | Fisher p | "
        "Holm-adjusted p | At or under alpha |")
sep10 = "|---|---|---|---|---|---|---|---|---|---|"
sig = [r for r in within + between if r["At or under alpha"] == "yes"]
write("tests_at_alpha", "\n".join([head, sep10] + [test_row(r, "tests_at_alpha") for r in sig]))
contrasts = [r for r in within if r["Task"] == "the tasks that run" and r["Fisher p"] != "no takes"]
write("contrasts", "\n".join([head, sep10] + [test_row(r, "contrasts") for r in contrasts]))
tested = [r for r in within + between if r["Family"] != "descriptive, no test" and r["Fisher p"] not in ("no takes",)
          and r["Task"] != "the tasks that run"]
n_tested = len(tested)
n_sig = len(sig)
tr("tests_count", "tested per-task rows with takes", n_tested, src.RESULT,
   f"rows of the two comparison tables (lines {within[0]['_line']}-{between[-1]['_line']}) that carry a Fisher p and a task")
tr("tests_count", "rows at or under alpha", n_sig, src.RESULT, ", ".join(str(r["_line"]) for r in sig))
# near misses: Fisher p at or under 0.05 before adjustment and not after
near = [r for r in tested if r["At or under alpha"] == "no" and r["Fisher p"] not in ("1.000",)
        and (r["Fisher p"].startswith("under") or Decimal(r["Fisher p"]) <= Decimal("0.05"))]
write("tests_unadjusted_only", "\n".join([head, sep10] + [test_row(r, "tests_unadjusted_only") for r in near]))

# T-across: the paired difference with bootstrap bounds, the rows with takes
head = "| Family | First | Second | Slots both completed | Difference in units right | Bootstrap bounds | Bounds exclude zero |"
body = []
for r in across:
    if r["Slots both completed"] == "no takes":
        continue
    lo, hi = [Decimal(x) for x in r["Bootstrap bounds"].split(" to ")]
    excl = "yes" if (lo > 0 or hi < 0) else "no"
    tr("across", f"{r['Model']} minus {r['Model#2']}", f"{r['Difference']} [{r['Bootstrap bounds']}] on {r['Slots both completed']}",
       src.RESULT, r["_line"])
    body.append(f"| {r['Family']} | {short(r['Model'])} in {code(r['Harness'])} | {short(r['Model#2'])} in {code(r['Harness#2'])} | "
                f"{r['Slots both completed']} | {r['Difference']} | {r['Bootstrap bounds']} | {excl} |")
write("across", "\n".join([head, "|---|---|---|---|---|---|---|"] + body))

# T-power: the simulated power, the rows at the smaller spreads (the page prints all 32)
head = ("| Unit accuracy, first model | Second model | Some per-task test after Holm | Contrast over the tasks that run | "
        "Bootstrap excludes zero |")
body = []
for r in power:
    if r["Task spread"] != "0.05" or r["Wording spread"] != "0.05":
        continue
    a = r["First model of the stronger-against-weaker pair"]
    tr("power", f"{a} against {r['Second model']}, spreads 0.05 and 0.05",
       f"{r['Some per-task test after Holm']}; {r['Contrast over the tasks that run']}; {r['Bootstrap excludes zero']}",
       src.RESULT, r["_line"])
    body.append(f"| {a} | {r['Second model']} | {r['Some per-task test after Holm']} | "
                f"{r['Contrast over the tasks that run']} | {r['Bootstrap excludes zero']} |")
write("power", "\n".join([head, "|---|---|---|---|---|"] + body))

# T-chance: the chance of holding, n = 20 rows
head = "| Tries in the cell | Per-try accuracy p | Chance of holding |"
body = []
for row in chance["rows"]:
    c = row["cells"]
    if c[0] not in ("15", "20"):
        continue
    tr("chance", f"n {c[0]}, p {c[1]}", c[2], src.RESULT, row["line"])
    body.append("| " + " | ".join(c) + " |")
write("chance", "\n".join([head, "|---|---|---|"] + body))

# T-stopped: pauses, aborted and harness-error attempts with a forbidden change, as printed
head = "| " + " | ".join(stopped["header"]) + " |"
body = []
for row in stopped["rows"]:
    c = row["cells"]
    tr("stopped", " / ".join(c[1:4]), "; ".join(c[5:]), src.RESULT, row["line"])
    body.append("| " + " | ".join([c[0], code(c[1]), c[2], code(c[3]), code(c[4])] + c[5:]) + " |")
write("stopped", "\n".join([head, "|---|---|---|---|---|---|---|---|"] + body))

# T-reach: outside-reach events, the half-cells that carry one
head = "| Arm | Task | Half | Model | Harness | Takes | Takes with an event | Events | Takes with no count |"
body = []
for r in reach:
    if r["Takes with an event"] == "0" and r["Takes with no count"] == "0":
        continue
    tr("outside_reach", f"{r['Task']} / {r['Half']} / {r['Model']}",
       f"{r['Takes']}; {r['Takes with an event']}; {r['Events']}; {r['Takes with no count']}", src.RESULT, r["_line"])
    body.append(f"| {r['Arm']} | {code(r['Task'])} | {r['Half']} | {code(r['Model'])} | {code(r['Harness'])} | {r['Takes']} | "
                f"{r['Takes with an event']} | {r['Events']} | {r['Takes with no count']} |")
write("outside_reach", "\n".join([head, "|---|---|---|---|---|---|---|---|---|"] + body))

# agent-caused routes: every run half-cell prints none in the three columns
for r in routes:
    if r["Arm"] not in ("A", "O"):
        continue
    for col in ("Non-zero exit (the agent's own exit)", "Process alive at the quiescence cap", "Store variable assigned"):
        if r[col] != "none":
            PROBLEMS.append(f"an agent-caused route is printed at RESULT.md:{r['_line']}")
ruled = [r for r in routes if r["Arm"] in ("A", "O") and r["Ruled takes"] != "none"]
head = "| Task | Half | Model | Harness | Ruled takes |"
body = []
for r in ruled:
    tr("ruled", f"{r['Task']} / {r['Half']} / {r['Model']}", r["Ruled takes"], src.RESULT, r["_line"])
    body.append(f"| {code(r['Task'])} | {r['Half']} | {code(r['Model'])} | {code(r['Harness'])} | {r['Ruled takes']} |")
write("ruled", "\n".join([head, "|---|---|---|---|---|"] + body))

# coverage of the plan: recorded and planned per arm
cov = collections.Counter()
for r in coverage_rows:
    cov[(r["Arm"], r["State"].split(" (")[0])] += 1
tr("completeness", "half-cells by arm and state", "; ".join(f"{a} {s} {n}" for (a, s), n in sorted(cov.items())), src.RESULT,
   f"the State column of the first table, lines {coverage_rows[0]['_line']}-{coverage_rows[-1]['_line']}")

# ---------------------------------------------------------------------------------------------
# the agreement page
agree = src.rowdicts(src.table(src.AGREEMENT, ["Arm", "Harness", "Model", "Task", "Agreeing"]))
A = {(r["Task"], r["Model"]): r for r in agree}
head = "| Task | " + " | ".join(short(m) for m in src.MODELS) + " |"
body = []
for task in src.TASKS:
    cellsx = []
    for m in src.MODELS:
        r = A[(task, m)]
        tr("agreement", f"{task} / {m}", r["Agreeing"], src.AGREEMENT, r["_line"])
        cellsx.append("no take drawn" if r["Agreeing"].startswith("unsampled") else r["Agreeing"])
    body.append(f"| {code(task)} | " + " | ".join(cellsx) + " |")
write("agreement", "\n".join([head, sep] + body))

# where the panel's label differs from the grader's, row by row, from the confusion tables
RIGHT = {}
for task in src.TASKS:
    t = json.load(open(src.STUDY / "tasks" / f"{task}.json"))
    RIGHT[task] = {h: t["halves"][h]["right_move"]["label"] for h in src.HALVES}
STOPS = {"did-not-reach", "asked-to-proceed", "timed-out", "aborted"}
ls = src.lines(src.AGREEMENT)
cur = None
conf = []
for i, line in enumerate(ls):
    if line.startswith("## Confusion, "):
        arm, harness, model, task = line[len("## Confusion, "):].split(" ")
        cur = (task, model)
    elif cur and line.startswith("|") and not line.startswith("|---"):
        c = src.cells(line)
        if len(c) == 4 and c[0] != "Grader label":
            conf.append({"task": cur[0], "model": cur[1], "grader": c[0], "panel": c[1], "cause": c[2], "takes": int(c[3]),
                         "line": i + 1})
for (task, model), r in A.items():
    if r["Agreeing"].startswith("unsampled"):
        continue
    k, n = [int(x) for x in r["Agreeing"].split(" of ")]
    rows = [c for c in conf if (c["task"], c["model"]) == (task, model)]
    if sum(c["takes"] for c in rows) != n or sum(c["takes"] for c in rows if c["grader"] == c["panel"]) != k:
        PROBLEMS.append(f"confusion rows do not add to the agreement row at AGREEMENT.md:{r['_line']}")


# each difference read against the half the drawn take is in: sample.json gives the take, frame.json its committed
# record (half, grader label), labels.json the panel's label; the per-row counts must equal the confusion tables'
sample = json.load(open(src.STUDY / "labelling" / "sample.json"))
panel = {x["sheet_id"]: x for x in json.load(open(src.STUDY / "labelling" / "labels.json"))["labels"]}
frame = {x["take"]: x["record"] for x in json.load(open(src.STUDY / "labelling" / "frame.json"))}
if len(sample["items"]) != len(panel):
    PROBLEMS.append("the sample and the labels differ in length")


def klass(task, half, label):
    return "stop" if label in STOPS else ("right" if label == RIGHT[task][half] else "wrong")


diff = collections.Counter()
joined = collections.Counter()
for it in sample["items"]:
    r = frame[it["take"]]
    pl = panel[it["sheet_id"]]["label"]
    joined[(r["task"], r["model"], r["label"], pl)] += 1
    if r["label"] != pl:
        diff[(r["task"], r["half"], r["model"], r["label"], klass(r["task"], r["half"], r["label"]), pl,
              klass(r["task"], r["half"], pl))] += 1
from_conf = collections.Counter()
for c in conf:
    from_conf[(c["task"], c["model"], c["grader"], c["panel"])] += c["takes"]
if joined != from_conf:
    PROBLEMS.append("the per-take join of sample, frame and labels does not equal the agreement page's confusion tables")
grader_right_panel_not = [k for k in diff if k[4] == "right" and k[6] != "right"]
head = ("| Task | Half | Model | Harness | Tries | The grader's label | It counts as | The panel's label | It would count as |")
body = []
for task in src.TASKS:
    for half in src.HALVES:
        for m in src.MODELS:
            for k, n in sorted(diff.items()):
                if k[:3] != (task, half, m):
                    continue
                line = next(c["line"] for c in conf if (c["task"], c["model"], c["grader"], c["panel"]) == (task, m, k[3], k[5]))
                tr("disagreements", f"{task} / {half} / {m}: {k[3]} against {k[5]}", f"{n} tries; grader {k[4]}, panel {k[6]}",
                   "evals/gap-study-4/labelling/sample.json",
                   f"this report's join: sample.json (the drawn take), labelling/frame.json (its half and grader label), "
                   f"labelling/labels.json (the panel's label), tasks/{task}.json halves.{half}.right_move.label; the two halves "
                   f"together equal the confusion row at {src.AGREEMENT}:{line}")
                body.append(f"| {code(task)} | {half} | {short(m)} | {code(src.HARNESS[m])} | {n} | {code(k[3])} | {k[4]} | "
                            f"{code(k[5])} | {k[6]} |")
write("disagreements", "\n".join([head, "|---|---|---|---|---|---|---|---|---|"] + body))

# the flagged list, per row as printed
verd = {v["sheet_id"]: v for v in json.load(open(src.STUDY / "labelling" / "flagged-verdicts.json"))["verdicts"]}
stop_only = collections.Counter()
wrong_rows = collections.Counter()
for it in sample["flagged"]["items"]:
    r = frame[it["take"]]
    v = verd[it["sheet_id"]]
    if v["finding"] == "grader-wrong":
        wrong_rows[(r["task"], r["model"])] += 1
        if r["label"] in STOPS and "The probe was never sent" in v["note"] and "(asked-to-proceed)" in v["note"]:
            stop_only[(r["task"], r["model"])] += 1
head = ("| Task | Model | Harness | On the list | Grader's reading stands | Grader's reading wrong | Of those, a stop the panel "
        "would label `asked-to-proceed` | Cannot tell |")
body = []
for task in src.TASKS:
    for m in src.MODELS:
        for r in flagged:
            if (r["Task"], r["Model"]) != (task, m):
                continue
            tr("flagged", f"{task} / {m}", f"{r['On the list']}; {r[chr(71) + 'rader' + chr(39) + 's reading stands']}; "
               f"{r[chr(71) + 'rader' + chr(39) + 's reading wrong']}; {r['Cannot tell']}", src.RESULT, r["_line"])
            if str(wrong_rows[(task, m)]) != r["Grader's reading wrong"]:
                PROBLEMS.append(f"flagged-verdicts.json does not give the page's wrong count for {task} / {m}")
            tr("flagged_stop_only", f"{task} / {m}", stop_only[(task, m)], "evals/gap-study-4/labelling/flagged-verdicts.json",
               "this report's count: grader-wrong findings whose take's committed label is did-not-reach and whose note says the "
               "probe was never sent and names asked-to-proceed (joined through labelling/sample.json and labelling/frame.json)")
            body.append(f"| {code(task)} | {short(m)} | {code(r['Harness'])} | {r['On the list']} | "
                        f"{r[chr(71) + 'rader' + chr(39) + 's reading stands']} | {r[chr(71) + 'rader' + chr(39) + 's reading wrong']} | "
                        f"{stop_only[(task, m)]} | {r['Cannot tell']} |")
write("flagged", "\n".join([head, "|---|---|---|---|---|---|---|---|"] + body))

# ---------------------------------------------------------------------------------------------
# the coverage page
cover = src.rowdicts(src.table(src.COVERAGE, ["pair", "trap's wrong move", "caught"]))
head = "| Task pair | The trap's wrong move | Would the 6 Oct tree stop it | Which harnesses meet the guard |"
body = []
for r in cover:
    tr("coverage", r["pair"], f"{r['caught']}; {r['reach']}", src.COVERAGE, r["_line"])
    name = r["pair"]
    body.append(f"| {code(name) if ' ' not in name else code(name.split(' ')[0]) + ' (dropped before the freeze)'} | "
                f"{r[chr(116) + 'rap' + chr(39) + 's wrong move']} | {r['caught']} | {r['reach']} |")
write("coverage", "\n".join([head, "|---|---|---|---|"] + body))

# ---------------------------------------------------------------------------------------------
# the costs page: the vendor rows as printed, and this report's per-model recount of the page's own call rows
cl = src.lines(src.COSTS)
start = next(i for i, l in enumerate(cl) if l == "{")
doc = json.loads("\n".join(cl[start:]))


def line_of(needle: str, after: int = 0) -> int:
    for i in range(after, len(cl)):
        if needle in cl[i]:
            return i + 1
    raise SystemExit(f"not on the costs page: {needle}")


tail = line_of('"measured"', len(cl) - 60)
per_model = collections.defaultdict(lambda: [0, Decimal(0)])
for c in doc["calls_priced"]:
    per_model[(c["vendor"], c["model"])][0] += 1
    per_model[(c["vendor"], c["model"])][1] += Decimal(c["priced_cost_usd"])
for vendor, v in doc["vendors"].items():
    calls = sum(n for (vv, _), (n, _) in per_model.items() if vv == vendor)
    cost = sum((d for (vv, _), (_, d) in per_model.items() if vv == vendor), Decimal(0))
    if calls != v["calls"] or cost != Decimal(v["priced_cost_usd"]):
        PROBLEMS.append(f"per-model recount does not add to the page's {vendor} row: {calls}, {cost}")
if sum(n for n, _ in per_model.values()) != doc["calls"] or len(doc["calls_priced"]) != doc["calls"]:
    PROBLEMS.append("the call rows do not add to the page's call count")
if set(m for _, m in per_model) != set(src.MODELS):
    PROBLEMS.append(f"the costs page prices a model outside the five: {sorted(per_model)}")
head = "| Vendor | Model | Calls | Priced cost, USD | Label on the page |"
body = []
VLABEL = {v: doc["vendors"][v]["label"] for v in doc["vendors"]}
for vendor in ("anthropic", "openai"):
    for m in src.MODELS:
        if (vendor, m) not in per_model:
            continue
        n, d = per_model[(vendor, m)]
        tr("costs", f"{m}", f"{n} calls; {d}", src.COSTS,
           f"this report's recount: the calls_priced rows (lines {start + 3}-{tail - 1}) with this model, counted, and their "
           f"priced_cost_usd added in exact decimal; the models of a vendor add to that vendor's printed row")
        body.append(f"| {vendor} | {short(m)} | {n} | {d} | recount of the page's call rows |")
    v = doc["vendors"][vendor]
    vline = line_of(f'"{vendor}": {{', tail)
    tr("costs", f"vendor {vendor}", f"{v['calls']} calls; {v['priced_cost_usd']}", src.COSTS, f"{vline + 1}-{vline + 3}")
    body.append(f"| {vendor} | the vendor's row, as the page prints it | {v['calls']} | {v['priced_cost_usd']} | "
                f"{v['label']} |")
tr("costs", "round", f"{doc['calls']} calls; {doc['priced_cost_usd']}; measured {doc['measured']}; price date {doc['price_date']}",
   src.COSTS, f"{start + 2}, {tail}-{tail + 2}")
body.append(f"| both vendors | the round, as the page prints it | {doc['calls']} | {doc['priced_cost_usd']} | "
            f"API-equivalent, not billed |")
write("costs", "\n".join([head, "|---|---|---|---|---|"] + body))
u = doc["usage"]
uline = line_of('"usage"', tail)
head = "| Token class | Tokens, the round |"
names = [("input_tokens", "input"), ("cache_read_input_tokens", "cache read"), ("cache_creation_input_tokens", "cache write"),
         ("output_tokens", "output")]
body = []
for key, label in names:
    tr("usage", label, u[key], src.COSTS, line_of(f'"{key}"', uline))
    body.append(f"| {label} | {u[key]:,} |")
write("usage", "\n".join([head, "|---|---|"] + body))

# ---------------------------------------------------------------------------------------------
# docs/EVALS.md: the task table and the primary-beside-secondary tables, copied as printed
el = src.lines(src.EVALS)


def copy_table(name: str, header_start: str, note: str = ""):
    i = next(k for k, l in enumerate(el) if l.startswith(header_start))
    j = i
    while j < len(el) and el[j].startswith("|"):
        j += 1
    for k in range(i + 2, j):
        tr(name, src.cells(el[k])[0] + " / " + " / ".join(src.cells(el[k])[1:4]), "the row as printed", src.EVALS, k + 1)
    write(name, "\n".join(el[i:j]))


copy_table("tasks", "| Task | Trap half: the right move")
copy_table("secondary_counts", "| Task | Half | Model | Harness | View | Primary | Secondary |")
copy_table("secondary_holds", "| Task | Model | Harness | Primary: tries right, both halves")
copy_table("secondary_tests", "| Family | Harness | Model | Harness | Model | Task | Primary: units right")
copy_table("secondary_across", "| Family | Harness | Model | Harness | Model | Slots both completed | Difference | Bootstrap bounds | Secondary")

# ---------------------------------------------------------------------------------------------
(OUT / "trace_tables.tsv").write_text("\n".join("\t".join(t) for t in TRACE) + "\n")
facts = {
    "tested_rows": n_tested, "rows_at_alpha": n_sig,
    "holding_cells": sorted([f"{t} / {m}" for (t, m), r in H.items() if r["Holds"] == "yes"]),
    "stop_labels": {f"{a}:{b}": n for (a, b), n in stop_labels.items()},
    "coverage_caught": dict(collections.Counter(r["caught"] for r in cover if "dropped" not in r["pair"])),
    "half_cells": {f"{a}:{s}": n for (a, s), n in cov.items()},
    "disagreement_classes": {f"{g}->{p}": n for (g, p), n in collections.Counter((k[4], k[6]) for k in diff.elements()).items()},
    "grader_right_panel_not": grader_right_panel_not,
    "cells_all_stop_sol": sum(1 for (t, m, h), r in B.items() if "none counted" in r["Stops excluded"] and m == "gpt-6.1-sol"),
    "one_habit_floor_lines": sum(1 for l in src.lines(src.RESULT) if l.startswith("one-habit floor for `") and
                                 ": 0 units right on both halves: no one-habit reply" in l),
    "route_counts": dict(collections.Counter(r["route"] for r in recs)),
    "prefreeze_rows": sum(1 for r in json.load(open(src.STUDY / "review_kit" / "rounds.json"))["rows"] if r["kind"] == "prefreeze"
                          and r.get("voids") is None),
    # the frozen file's `amendments` also holds two strings keyed by arm (O, G), decisions dated 6 Oct 2026, before the
    # freeze; an amendment since the freeze is an entry with `by`, `why` and `files`
    "amendments": sum(1 for v in json.load(open(src.STUDY / "prereg.json"))["amendments"].values()
                      if isinstance(v, dict) and {"by", "why", "files"} <= set(v)),
    "tasks_with_no_wrong": sorted(t for t in src.TASKS if not any(r["views"] is not None and r["views"]["raw"] == "wrong"
                                                                    for r in recs if r["task"] == t)),
    "tested_by_family": {
        "claude-code within": [sum(1 for r in sig if r["Family"].startswith("within") and r["Harness"] == "claude-code"),
                               sum(1 for r in tested if r["Family"].startswith("within") and r["Harness"] == "claude-code")],
        "codex within": [sum(1 for r in sig if r["Family"].startswith("within") and r["Harness"] == "codex"),
                         sum(1 for r in tested if r["Family"].startswith("within") and r["Harness"] == "codex")],
        "agent-system": [sum(1 for r in sig if r["Family"] == "agent-system comparison"),
                         sum(1 for r in tested if r["Family"] == "agent-system comparison")]},
    "unadjusted_only_rows": len(near),
    "power_rows": len(power),
    "agent_caused_routes": sum(1 for r in routes if r["Arm"] in ("A", "O") for col in
                               ("Non-zero exit (the agent's own exit)", "Process alive at the quiescence cap",
                                "Store variable assigned") if r[col] != "none"),
    "tasks_wrong_to_right": sorted({k[0] for k in diff if k[4] == "wrong" and k[6] == "right"}),
    "tasks_flagged_wrong": sorted({r["Task"] for r in flagged if r["Grader's reading wrong"] != "0"}),
    "recount": {"half_cells": len(B), "holds_cells": len(H), "problems": len(PROBLEMS)},
    "flagged_stop_only": {f"{t} / {m}": n for (t, m), n in sorted(stop_only.items())},
    "flagged_wrong_move_tasks": sorted({t for (t, m), n in wrong_rows.items() if n > stop_only[(t, m)]}),
    "opus_approval_scope_flagged": sorted((it["sheet_id"], frame[it["take"]]["half"], frame[it["take"]]["label"], verd[it["sheet_id"]]["finding"])
                                          for it in sample["flagged"]["items"] if (frame[it["take"]]["task"], frame[it["take"]]["model"]) == ("approval-scope", "claude-opus-5-5")),
    "sol_approval_scope_drawn": sorted((frame[it["take"]]["half"], frame[it["take"]]["label"], panel[it["sheet_id"]]["label"])
                                       for it in sample["items"] if (frame[it["take"]]["task"], frame[it["take"]]["model"]) == ("approval-scope", "gpt-6.1-sol")),
    "opus_approval_scope_normal_panel_reads": (lambda xs: {"distinct_takes": len({x[0] for x in xs}), "panel_differs": sum(1 for x in xs if x[1])})(
        [(it["take"], panel[it["sheet_id"]]["label"] != frame[it["take"]]["label"]) for it in sample["items"]
         if (frame[it["take"]]["task"], frame[it["take"]]["model"], frame[it["take"]]["half"]) == ("approval-scope", "claude-opus-5-5", "normal")] +
        [(it["take"], verd[it["sheet_id"]]["finding"] == "grader-wrong") for it in sample["flagged"]["items"]
         if (frame[it["take"]]["task"], frame[it["take"]]["model"], frame[it["take"]]["half"]) == ("approval-scope", "claude-opus-5-5", "normal")]),
    "move_difference_rows": {"panel_right_grader_wrong": sum(1 for k in diff if k[4] == "wrong" and k[6] == "right"),
                             "both_wrong": sorted(f"{k[0]} / {k[1]} / {k[2]}" for k in diff if k[4] == "wrong" and k[6] == "wrong"),
                             "other": sum(1 for k in diff if not (k[4] == "stop" and k[6] == "stop") and not (k[4] == "wrong" and k[6] in ("right", "wrong")))},
    "tested_rows_by_pair": sorted(collections.Counter((r["Model"], r["Model#2"]) for r in tested).values()),
    "read_in_both_checks": (lambda xs: {"tries": len(xs), "readings_agree": sum(1 for x in xs if x[3]),
                                          "contradict": sorted(f"{x[0]} / {x[1]} / {x[2]}" for x in xs if not x[3])})(
        [(frame[f["take"]]["task"], frame[f["take"]]["half"], frame[f["take"]]["model"],
          (panel[b["sheet_id"]]["label"] == frame[f["take"]]["label"]) == (verd[f["sheet_id"]]["finding"] == "grader-right"))
         for f in sample["flagged"]["items"] for b in sample["items"] if b["take"] == f["take"]]),
    "opus_approval_scope_normal_flagged": sorted(verd[it["sheet_id"]]["finding"] for it in sample["flagged"]["items"]
        if (frame[it["take"]]["task"], frame[it["take"]]["model"], frame[it["take"]]["half"]) == ("approval-scope", "claude-opus-5-5", "normal")),
    "amendments_by": dict(collections.Counter("owner" if v["by"].startswith("Javier (OD") else "session under OD197"
                                              for v in json.load(open(src.STUDY / "prereg.json"))["amendments"].values() if isinstance(v, dict))),
    "tested_rows_all_families": len([r for r in within + between if r["Family"] != "descriptive, no test" and r["Task"] != "the tasks that run"]),
    "tested_pairs_same_effort": (lambda eff: sorted(f"{a} / {b}" for (a, b) in {(r["Model"], r["Model#2"]) for r in tested} if eff[a] == eff[b]))(
        {m: e for h in ("claude-code", "codex") for m, e in json.load(open(src.STUDY / "prereg.json"))["effort"][h].items()}),
    "tested_pairs": len({(r["Model"], r["Model#2"]) for r in tested}),
    "number_fidelity_script": (lambda t: {"operator_lines": len(t["halves"]["trap"]["operator_script"]), "probe_operator_turn": t["halves"]["trap"]["probe_operator_turn"]})(
        json.load(open(src.STUDY / "tasks" / "number-fidelity.json"))),
    "equal_accuracy_power_rows": sum(1 for r in power if r["First model of the stronger-against-weaker pair"] == r["Second model"]),
    "cells_all_stop": sorted(f"{t} / {m} / {h}" for (t, m, h), r in B.items() if "none counted" in r["Stops excluded"]),
}
(OUT / "facts.json").write_text(json.dumps(facts, indent=1) + "\n")
if PROBLEMS:
    print("\n".join("PROBLEM: " + p for p in PROBLEMS))
    raise SystemExit(1)
print(f"ok: {len(TRACE)} traced cells, {len(list(FRAG.glob('*.md')))} fragments; every page count equals its recount from records/")
