#!/usr/bin/env python3
"""Check every traced claim of REPORT.md against the committed records, and write TRACE.md.

1. every prose line of REPORT.md that carries a figure is covered by an entry of trace_prose.py;
2. every entry's text stands in REPORT.md, and every source needle stands in the committed file (the line is found
   here, never typed), every cited table cell exists in build/trace_tables.tsv, every fact equals build/facts.json;
3. every table row of REPORT.md is a row of a generated fragment (no hand-typed table but the design table, traced);
4. the study's own lint_language.py and lint_pooling.py exit 0 on REPORT.md;
5. every line revision 3 changed (trace_prose_v2.REV3_LINES, REV3_SENTENCES) stands in REPORT.md and is an entry's text.
Exit 1 on any failure.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prose_lines  # noqa: E402
import src  # noqa: E402
import trace_prose  # noqa: E402
import trace_prose_v2  # noqa: E402

ROOT = src.ROOT
WORKTREE = str(src.REPO)            # the clone itself: the records commit src.HEAD is in its history
report = (src.DOC / "REPORT.md").read_text()
facts = json.loads((ROOT / "build" / "facts.json").read_text())
facts_reading = json.loads((ROOT / "build" / "facts_reading.json").read_text())   # the exploratory action reading
if set(facts) & set(facts_reading):
    raise SystemExit("a fact key is in both facts files")
FACT_FILE = {**{k: "build/facts.json" for k in facts}, **{k: "build/facts_reading.json" for k in facts_reading}}
facts = {**facts, **facts_reading}
cells = {}
for tsv in ("trace_tables.tsv", "trace_reading.tsv"):
    for line in (ROOT / "build" / tsv).read_text().splitlines():
        t, c, v, f, w = line.split("\t")
        if (t, c) in cells and cells[(t, c)][1] != f:
            raise SystemExit(f"traced cell in both trace files: {t} / {c}")
        cells[(t, c)] = (v, f, w)
problems: list[str] = []
rows: list[tuple[str, str, str, str]] = []      # report text, value/needle, file, where
cache: dict[str, list[str]] = {}


def flines(rel: str) -> list[str]:
    """A committed file of the records copy; a path under inputs/action-reading/ is an action-reading file under its
    SHA256SUMS name (src.action_reading_inputs(), built from the published files), not a record."""
    if rel not in cache:
        pre = "inputs/action-reading/"
        path = src.action_reading_inputs() / rel[len(pre):] if rel.startswith(pre) else src.COPY / rel
        cache[rel] = path.read_text().split("\n")
    return cache[rel]


def norm(x):
    return json.loads(json.dumps(x))


LIVE = trace_prose._live(report)
# every line revision 3 changed must stand in REPORT.md and be a trace entry's text: a rewritten revision-3 line can
# never drop its entry silently (review R1, finding 4; trace_prose_v2.REV3_LINES is written by revise_v3_publication.py)
_report_lines = report.split("\n")
_entry_texts = {e[0] for e in trace_prose.ENTRIES}
for t in trace_prose_v2.REV3_LINES:
    if t not in _report_lines:
        problems.append(f"revision 3 entry not a line of REPORT.md: {t[:90]}")
    if t not in _entry_texts:
        problems.append(f"revision 3 line has no trace entry: {t[:90]}")
for t in trace_prose_v2.REV3_SENTENCES:
    if not any(t in line for line in _report_lines):
        problems.append(f"revision 3 entry not in a line of REPORT.md: {t[:90]}")
    if t not in _entry_texts:
        problems.append(f"revision 3 sentence has no trace entry: {t[:90]}")
for text, sources in LIVE:
    for s in sources:
        kind = s[0]
        if kind == "src":
            rel, needle = s[1], s[2]
            hits = [i + 1 for i, l in enumerate(flines(rel)) if needle in l]
            if not hits:
                problems.append(f"needle not in {rel}: {needle[:90]}")
                continue
            where = str(hits[0]) if len(hits) == 1 else f"{hits[0]} (first of {len(hits)} lines that hold it)"
            rows.append((text, needle, rel, where))
        elif kind == "cell":
            if (s[1], s[2]) not in cells:
                problems.append(f"no traced cell {s[1]} / {s[2]}")
                continue
            v, f, w = cells[(s[1], s[2])]
            rows.append((text, f"table `{s[1]}`, cell {s[2]}: {v}", f, w))
        elif kind == "fact":
            if s[1] not in facts or norm(facts[s[1]]) != norm(s[2]):
                problems.append(f"fact {s[1]}: expected {s[2]}, build/facts.json has {facts.get(s[1])}")
                continue
            ff = FACT_FILE[s[1]]
            rows.append((text, f"{s[1]} = {json.dumps(facts[s[1]], ensure_ascii=False)}", ff,
                         "computed from the committed records by tools/build_tables.py (the key names the rule)" if ff == "build/facts.json"
                         else "computed from the action reading's page and rulings file by tools/build_reading.py (the key names the rule)"))
        elif kind == "git":
            out = subprocess.run(["git", "-C", WORKTREE] + s[1].split(), capture_output=True, text=True)
            if out.returncode != 0 or (s[2] == "" and out.stdout.strip() != "") or (s[2] and s[2] not in out.stdout):
                problems.append(f"git {s[1]}: unexpected output {out.stdout[:80]!r}")
                continue
            rows.append((text, "prints nothing" if s[2] == "" else s[2], "git (read-only, on this repository)", "git " + s[1]))
        elif kind == "note":
            rows.append((text, s[1], "this report", "not a record figure"))
        else:
            problems.append(f"unknown source kind {kind}")

# 1. coverage of the prose
texts = [t for t, _ in LIVE]
for n, line in prose_lines.claim_lines(report):
    if not any(t in line for t in texts):
        problems.append(f"REPORT.md:{n} carries a figure and no trace entry covers it: {line[:110]}")

# 3. every table row is generated, or is the design table of section 2.2 (traced above)
generated = set()
for f in (ROOT / "build" / "fragments").glob("*.md"):
    generated.update(l for l in f.read_text().splitlines() if l.startswith("|"))
design = 0
for n, line in enumerate(report.split("\n"), 1):
    if line.startswith("|") and line not in generated:
        if line.startswith("| Arm | Harness and pinned version") or line.startswith("|---|---|---|---|") or re.match(r"^\| [AOG] \| (Claude Code 2\.1\.296|Codex CLI 0\.162\.1|Gemini CLI 0\.64\.0) \|", line):
            design += 1
            continue
        problems.append(f"REPORT.md:{n} is a table row no fragment generated: {line[:90]}")
EFFORT = "`claude-opus-5-5` medium; `claude-sonnet-5-5` medium; `claude-haiku-4-5-20251001` none, Claude Code 2.1.296 sends no effort setting for it; `gpt-6.1-sol` low; `gpt-6-luna` medium"
if not any(EFFORT in l for l in flines(src.EVALS)):
    problems.append("the effort line of the design table is not in docs/EVALS.md")
for m, e in (("claude-opus-5-5", "medium"), ("claude-sonnet-5-5", "medium"), ("gpt-6.1-sol", "low"), ("gpt-6-luna", "medium")):
    if not re.search(rf"^\| [AO] \| [^|]+ \| `{re.escape(m)}` \| {e} \|$", report, re.M):
        problems.append(f"design table: {m} is not printed at effort {e}")

# 4. the study's own wording checks
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
lint = {}
for name in ("lint_language.py", "lint_pooling.py"):
    out = subprocess.run([sys.executable, "-B", str(src.STUDY / name), str(src.DOC / "REPORT.md")], capture_output=True, text=True, env=env)
    lint[name] = (out.returncode, out.stdout.strip().splitlines()[-1] if out.stdout.strip() else "")
    if out.returncode != 0:
        problems.append(f"{name} exits {out.returncode} on REPORT.md:\n{out.stdout[-1500:]}")

if problems:
    print("\n".join("PROBLEM: " + p for p in problems))
    raise SystemExit(1)


def esc(x: str) -> str:
    return x.replace("|", "\\|").replace("\n", " ")


# the build folder's names, written as the published paths of the repository (the report text itself is never mapped)
PUB = "docs/gap-study-4/"
_sources = {}
for _l in (src.ACTION_READING / "TRACE-SOURCES.md").read_text().splitlines():
    _m = re.match(r"^\| `([^`]+)` \| `[0-9a-f]{64}` \| (copy|regenerated) \| `([^`]+)` \|", _l)
    if _m:
        _sources[_m.group(1)] = _m.group(3) if _m.group(2) == "copy" else _m.group(3) + " (regenerated)"
_sources["SHA256SUMS"] = PUB + "action-reading/trace-inputs/SHA256SUMS"


def _input(m):
    name = m.group(1)
    if name not in _sources and any(k.startswith(name + "/") for k in _sources):   # a folder, e.g. labels/ra
        return PUB + "action-reading/" + name
    if name not in _sources:
        raise SystemExit(f"no published path for inputs/action-reading/{name} in TRACE-SOURCES.md")
    return _sources[name]


def pub(x: str) -> str:
    x = re.sub(r"inputs/action-reading/([A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)*)", _input, x)
    x = re.sub(r"(?<![\w/\-])tools/", PUB + "report-build/", x)
    x = re.sub(r"(?<![\w/\-])build/", PUB + "report-build/build/", x)
    return x


out = ["# TRACE: where each number of REPORT.md comes from", "",
       f"Records: the Gap Study round 4 records line at `{src.HEAD}` (branch `freeze/r4-20261021`), read from a `git archive` copy of that commit (the paths in `docs/gap-study-4/report-build/copy-paths.txt`); paths are relative to the repository root, and every line number points at the file as it stands at that commit, not at a later commit; lines are 1-based.",
       "A file under `docs/gap-study-4/action-reading/` is a file of the exploratory action reading (section 4.4 of the report), which is not on the records line; the copies this report read are listed with their sha256 in `docs/gap-study-4/action-reading/trace-inputs/SHA256SUMS` and mapped to their published paths in `docs/gap-study-4/action-reading/TRACE-SOURCES.md`, and `docs/gap-study-4/report-build/build_reading.py` refuses a changed copy.",
       "This file is written by `docs/gap-study-4/report-build/check_trace.py`, which fails unless each needle below stands on the cited line of the committed file, each prose line of the report that carries a figure has an entry here, and each table row of the report was generated by `docs/gap-study-4/report-build/build_tables.py`.",
       "No line number in this file was typed: each was found by the script.",
       f"The study's own wording checks on `REPORT.md`: `lint_language.py` exit {lint['lint_language.py'][0]}, `lint_pooling.py` exit {lint['lint_pooling.py'][0]} (\"{lint['lint_pooling.py'][1]}\").",
       "",
       "## Part 1. Prose", "",
       "| # | Text in REPORT.md | What it rests on (the text on the cited line, or the traced cell) | Record file | Line, or how it is derived |",
       "|---|---|---|---|---|"]
for i, (text, val, f, w) in enumerate(rows, 1):
    out.append(f"| P{i} | {esc(text[:160])}{'…' if len(text) > 160 else ''} | {esc(pub(val) if f == 'this report' else val)} | `{pub(f)}` | {esc(pub(w))} |")
out += ["", "## Part 2. Tables, cell by cell", "",
        "Each row is one cell (or one printed row) of a table of the report, with the value as the record prints it.",
        "", "| Table (fragment) | Cell | Value in the record | Record file | Line, or how it is derived |", "|---|---|---|---|---|"]
for (t, c), (v, f, w) in cells.items():
    out.append(f"| `{t}` | {esc(c)} | {esc(v)} | `{pub(f)}` | {esc(pub(w))} |")
out += ["", "## Part 3. The design table of section 2.2", "",
        f"Typed by hand from one sentence of `docs/EVALS.md` (line {next(i + 1 for i, l in enumerate(flines(src.EVALS)) if EFFORT in l)}): harness versions, models and efforts; the checker compares each model's effort with that sentence, and the arm G row with `RESULT.md`'s deferred rows (Part 1).", ""]
(src.DOC / "TRACE.md").write_text("\n".join(out) + "\n")
print(f"ok: {len(rows)} prose sources over {len(LIVE)} entries, {len(cells)} table cells, both lints exit 0; TRACE.md written")
