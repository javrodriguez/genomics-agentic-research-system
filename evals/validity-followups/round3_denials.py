#!/usr/bin/env python3
"""The round 3 denials reading: every tool call the harness refused in round 3, what the agent did next, and whether
the take still reached the question.

    python3 evals/validity-followups/round3_denials.py --check   re-derive results/round3-denials.json and DENIALS.md; fail on any difference
    python3 evals/validity-followups/round3_denials.py --write   write them

The rules are `denials_rules.py`, frozen with PREREG-DENIALS.md; this reader refuses to run if either file has
changed. Each take's refused calls are cross-checked against round 3's own reader (`evals/gap-study-3/denials.py`),
and the per-cell totals against the round's published RESULT.md, before anything is written. It re-grades nothing
and writes nothing under `evals/gap-study-3/`. No model, no network, standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "evals"))

import denials_rules as rules  # noqa: E402
import denials_rules_2 as rules2  # noqa: E402
import transcript as tx  # noqa: E402

ROUND = REPO / "evals" / "gap-study-3"
R3_READER = REPO / "evals" / "gap-study-3" / "denials.py"
HALVES = ("positive", "control")
RULES = HERE / "denials_rules.py"
RULES_SHA256 = "20932425bb1300ac907a8bab09295d6d79b1b29420c344c37ae8fe0817610264"
PREREG = HERE / "PREREG-DENIALS.md"
PREREG_SHA = HERE / "PREREG-DENIALS.sha256"
RULES_2 = HERE / "denials_rules_2.py"
RULES_2_SHA256 = "e0bdd282a3c072cb26a0d5703c704e7f343ed362b0439e2f1b8d4d259703cb85"
PREREG_2 = HERE / "PREREG-DENIALS-2.md"
PREREG_2_SHA = HERE / "PREREG-DENIALS-2.sha256"
# The first run's outputs, re-derived byte for byte by the first rules and the first render.
OUT_JSON = HERE / "results" / "round3-denials.json"
OUT_MD = HERE / "DENIALS.md"
# Amendment 2's outputs.
OUT_JSON_2 = HERE / "results" / "round3-denials-2.json"
OUT_MD_2 = HERE / "DENIALS-2.md"
# A research note's sort by eye, 6 October 2026. Printed beside the kind table; never compared, never a check.
NOTE_SPLIT = {"project-log-write": 18, "cd-into-run": 9, "echo-appended": 6, "script-form": 2}

CELL_ROW = re.compile(r"^\| `([^`]+)` \| (positive|control) \| `([^`]+)` \|(?:[^|]*\|){2}\s*(\d+)\s*\|")
TAKE_LINE = re.compile(r"^- `([^`]+)`/(positive|control)/`([^`]+)`/take (\d+): (?:(\d+) denied call\(s\)|no denial)")


def round3_reader():
    spec = importlib.util.spec_from_file_location("gap_study_3_denials", R3_READER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def integrity_problems() -> list:
    """Each rules file must hash to the sha256 its own pre-registration file quotes, and to this reader's constant;
    each pre-registration file must hash to its `.sha256` record; the refusal sentence must be round 3's reader's
    (amendment 2)."""
    problems = []
    for rules_path, constant, prereg, prereg_sha in ((RULES, RULES_SHA256, PREREG, PREREG_SHA),
                                                    (RULES_2, RULES_2_SHA256, PREREG_2, PREREG_2_SHA)):
        got = hashlib.sha256(rules_path.read_bytes()).hexdigest()
        if got not in set(re.findall(r"\b[0-9a-f]{64}\b", prereg.read_text())):
            problems.append(f"{rules_path.name} hashes to {got}, which {prereg.name} does not quote")
        if got != constant:
            problems.append(f"{rules_path.name} hashes to {got}, and this reader's constant is {constant}")
        want = prereg_sha.read_text().split()[0] if prereg_sha.is_file() else None
        got = hashlib.sha256(prereg.read_bytes()).hexdigest()
        if got != want:
            problems.append(f"{prereg.name} hashes to {got}, and {prereg_sha.name} records {want}")
    theirs = round3_reader().DENIAL_SENTENCE
    if theirs != rules.DENIAL_SENTENCE:
        problems.append(f"the refusal sentence differs from round 3's reader: {theirs!r}")
    return problems


def published_record() -> tuple:
    """(denied calls per cell, denied calls per take) as RESULT.md publishes them."""
    # Read only the round's own sections: the cell table under "## This round", and the take lines from
    # "## Denials, per graded take" to "## The earlier round" (a quoted heredoc inside the denials list carries
    # "## " lines of its own, so the next heading cannot end that section).
    cells, takes = {}, {}
    section = None
    for line in (ROUND / "RESULT.md").read_text().splitlines():
        if line.startswith("## This round"):
            section = "cells"
            continue
        if line.startswith("## Denials, per graded take"):
            section = "takes"
            continue
        if line.startswith("## The earlier round") or (section == "cells" and line.startswith("## ")):
            section = None
            continue
        if section == "cells":
            m = CELL_ROW.match(line)
            if m:
                cells[(m.group(1), m.group(2), m.group(3))] = int(m.group(4))
        elif section == "takes":
            m = TAKE_LINE.match(line)
            if m:
                takes[(m.group(1), m.group(2), m.group(3), m.group(4))] = int(m.group(5) or 0)
    return cells, takes


def derive() -> dict:
    reader = round3_reader()
    seen = read = crossed = 0
    takes = []
    per_cell = {}
    per_take = {}
    for res_path in sorted((ROUND / "results").glob("*.json")):
        res = json.loads(res_path.read_text())
        task = res.get("task") or res_path.stem
        for model in sorted(res.get("cells", {})):
            for half in HALVES:
                for entry in res["cells"][model].get(half, {}).get("labels", []):
                    seen += 1
                    where = f"{task}/{half}/{model}/{entry['take']}"
                    t = ROUND / "transcripts" / task / half / model / str(entry["take"]) / "transcript.jsonl"
                    if entry.get("transcript_sha256") is None:
                        continue
                    if not t.is_file():
                        raise SystemExit(f"{where}: the results publish a transcript hash and no transcript is on disk")
                    data = tx.load(t)
                    if data["sha256"] != entry["transcript_sha256"]:
                        raise SystemExit(f"{where}: the transcript does not hash to the published sha256")
                    read += 1
                    calls = rules.read_take(data["turns"])
                    theirs = [d["command"] for d in reader.denials_in(t)]
                    if [c["command"] for c in calls] != theirs:
                        raise SystemExit(f"{where}: the refused calls differ from round 3's own reader")
                    crossed += 1
                    key = (task, half, model)
                    per_cell[key] = per_cell.get(key, 0) + len(calls)
                    per_take[(task, half, model, str(entry["take"]))] = len(calls)
                    if calls:
                        takes.append({"task": task, "half": half, "model": model, "take": str(entry["take"]),
                                      "label": entry["label"], "transcript_sha256": entry["transcript_sha256"],
                                      "reached_question": entry["label"] not in rules.STOP_LABELS,
                                      "calls": calls})
    if seen == 0:
        raise SystemExit(f"{ROUND}: no results file publishes a take; refused rather than printed as zero")

    pub_cells, pub_takes = published_record()
    if {k: v for k, v in per_cell.items()} != pub_cells:
        raise SystemExit("the refused calls per cell differ from RESULT.md's `denied` column")
    if {k: v for k, v in per_take.items() if v} != {k: v for k, v in pub_takes.items() if v}:
        raise SystemExit("the takes carrying a refusal differ from RESULT.md's Denials lines")

    by_model = {}
    by_model_task = {}
    for t in takes:
        m = by_model.setdefault(t["model"], {"calls": 0, "takes": 0})
        m["calls"] += len(t["calls"])
        m["takes"] += 1
        mt = by_model_task.setdefault(f"{t['model']}/{t['task']}", {
            "calls": 0, "takes": 0, "takes_reached": 0,
            "kinds": {k: 0 for k in rules.KINDS}, "next": {n: 0 for n in rules.NEXT}})
        mt["calls"] += len(t["calls"])
        mt["takes"] += 1
        mt["takes_reached"] += 1 if t["reached_question"] else 0
        for c in t["calls"]:
            mt["kinds"][c["kind"]] += 1
            mt["next"][c["next"]] += 1
    all_calls = [c for t in takes for c in t["calls"]]
    return {
        "round": ROUND.name,
        "rules_sha256": RULES_SHA256,
        "seen": seen,
        "read": read,
        "cross_checked_with_round3_reader": crossed,
        "refused_calls": len(all_calls),
        "takes_with_refusals": len(takes),
        "takes_with_refusals_that_reached_the_question": sum(1 for t in takes if t["reached_question"]),
        "by_model": by_model,
        "by_model_task": by_model_task,
        "by_kind": {k: sum(1 for c in all_calls if c["kind"] == k) for k in rules.KINDS},
        "by_next": {n: sum(1 for c in all_calls if c["next"] == n) for n in rules.NEXT},
        "note_split": NOTE_SPLIT,
        "takes": takes,
    }


def cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ⏎ ")


def render(data: dict) -> str:
    K, N = rules.KINDS, rules.NEXT
    out = [
        "# The round 3 denials reading: result",
        "",
        "Generated by `evals/validity-followups/round3_denials.py --write` from round 3's committed records, under the "
        "rules frozen in `PREREG-DENIALS.md`; never typed. `--check` re-derives it.",
        "Nothing here re-grades a take or changes a published label, and nothing says what an unrefused run would "
        "have done.",
        "",
        f"Takes seen: {data['seen']}. Read: {data['read']}, each cross-checked against round 3's own reader "
        f"({data['cross_checked_with_round3_reader']} of {data['read']}). Refused calls: {data['refused_calls']}, in "
        f"{data['takes_with_refusals']} takes; {data['takes_with_refusals_that_reached_the_question']} of those "
        f"{data['takes_with_refusals']} takes still reached the question. The per-cell counts and the takes carrying "
        "a refusal equal `evals/gap-study-3/RESULT.md`'s, or this file would not have been written.",
        "",
        "## By model",
        "",
        "| model | refused calls | takes with a refusal |",
        "|---|---|---|",
    ]
    for m in sorted(data["by_model"]):
        out.append(f"| `{m}` | {data['by_model'][m]['calls']} | {data['by_model'][m]['takes']} |")
    out += [
        "",
        "## By model and task",
        "",
        "| model/task | calls | takes | takes that reached the question | " + " | ".join(f"`{k}`" for k in K)
        + " | " + " | ".join(f"`{n}`" for n in N) + " |",
        "|---|---|---|---|" + "---|" * (len(K) + len(N)),
    ]
    for key in sorted(data["by_model_task"]):
        r = data["by_model_task"][key]
        out.append(f"| `{key}` | {r['calls']} | {r['takes']} | {r['takes_reached']} | "
                   + " | ".join(str(r["kinds"][k]) for k in K) + " | " + " | ".join(str(r["next"][n]) for n in N) + " |")
    out.append("| **all** | **" + str(data["refused_calls"]) + "** | **" + str(data["takes_with_refusals"]) + "** | **"
               + str(data["takes_with_refusals_that_reached_the_question"]) + "** | "
               + " | ".join(f"**{data['by_kind'][k]}**" for k in K) + " | "
               + " | ".join(f"**{data['by_next'][n]}**" for n in N) + " |")
    out += [
        "",
        "Beside it, never compared: a research note of 6 October 2026 sorted the 35 by eye as "
        + ", ".join(f"{v} `{k}`" for k, v in data["note_split"].items()) + ".",
        "",
        "## Every refused call",
        "",
        "| take | label | reached the question | # | kind | refused call | next | how |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for t in data["takes"]:
        name = f"`{t['task']}/{t['half']}/{t['model']}/{t['take']}`"
        for i, c in enumerate(t["calls"], start=1):
            how = cell(c["worked_around_by"]["tool"] + ": " + c["worked_around_by"]["call"]) if c["worked_around_by"] else ""
            out.append(f"| {name} | `{t['label']}` | {'yes' if t['reached_question'] else 'no'} | {i} | `{c['kind']}` | "
                       f"`{cell(rules.first_line(c['command']))}` | `{c['next']}` | {how} |")
    return "\n".join(out) + "\n"


def dump(data: dict) -> str:
    return json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


# ------------------------------------------------------------------ amendment 2 (PREREG-DENIALS-2.md)

def prereg_section(path: Path, heading: str) -> str:
    """A section of a frozen pre-registration file, verbatim, from its heading to the next heading."""
    lines = path.read_text().splitlines()
    start = lines.index(heading)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start + 1:end]).strip()


def derive2() -> dict:
    first = derive()
    by_take = {(t["task"], t["half"], t["model"], t["take"]): t for t in first["takes"]}
    cross = {}
    sweep = []
    versions = {}
    takes = []
    for res_path in sorted((ROUND / "results").glob("*.json")):
        res = json.loads(res_path.read_text())
        task = res.get("task") or res_path.stem
        for model in sorted(res.get("cells", {})):
            for half in HALVES:
                for entry in res["cells"][model].get(half, {}).get("labels", []):
                    if entry.get("transcript_sha256") is None:
                        continue
                    d = ROUND / "transcripts" / task / half / model / str(entry["take"])
                    data = tx.load(d / "transcript.jsonl")
                    if data["sha256"] != entry["transcript_sha256"]:
                        raise SystemExit(f"{task}/{half}/{model}/{entry['take']}: the transcript does not hash to the "
                                         "published sha256")
                    ledger_path = d / "driver-ledger.json"
                    if not ledger_path.is_file():
                        raise SystemExit(f"{task}/{half}/{model}/{entry['take']}: no driver ledger beside the transcript")
                    version = json.loads(ledger_path.read_text()).get("claude_version") or "unrecorded"
                    turns = data["turns"]
                    calls = [u for t in turns if t["role"] == "assistant" for u in t["tool_uses"]]
                    for u in calls:
                        if u.get("name") == "Bash":
                            row = cross.setdefault(rules2.cross_tab_key(u), {"admitted": 0, "refused": 0})
                            row["refused" if rules.denied(u) else "admitted"] += 1
                        if rules2.refusal_like_without_sentence(u):
                            sweep.append({"take": f"{task}/{half}/{model}/{entry['take']}", "tool": u.get("name"),
                                          "result": rules.first_line(u.get("stdout") or "")})
                    v = versions.setdefault(version, {"takes": 0, "refused_calls": 0})
                    v["takes"] += 1
                    key = (task, half, model, str(entry["take"]))
                    if key not in by_take:
                        continue
                    t1 = by_take[key]
                    extra = rules2.read_take_2(turns)
                    v["refused_calls"] += len(extra)
                    row = dict(t1)
                    row["harness"] = version
                    row["calls"] = [dict(c, **x) for c, x in zip(t1["calls"], extra)]
                    row["project_log"] = rules2.project_log_reading(turns)
                    takes.append(row)
    all_calls = [c for t in takes for c in t["calls"]]
    helper = [c for c in all_calls if c["kind"] in ("cd-into-run", "echo-appended", "script-form")]
    log = [c for c in all_calls if c["kind"] == "project-log-write"]
    log_takes = [t for t in takes if t["project_log"]]
    never = [t for t in log_takes if not t["project_log"]["log_written_later"]]
    by_model_task = {}
    for t in takes:
        r = by_model_task.setdefault(f"{t['model']}/{t['task']}", {
            "calls": 0, "takes": 0, "takes_reached": 0,
            "kinds_2": {k: 0 for k in rules2.KINDS_2}, "next_2": {n: 0 for n in rules2.NEXT_2}})
        r["calls"] += len(t["calls"])
        r["takes"] += 1
        r["takes_reached"] += 1 if t["reached_question"] else 0
        for c in t["calls"]:
            r["kinds_2"][c["kind_2"]] += 1
            r["next_2"][c["next_2"]] += 1
    return {
        "round": first["round"], "rules_sha256": RULES_SHA256, "rules_2_sha256": RULES_2_SHA256,
        "seen": first["seen"], "read": first["read"],
        "refused_calls": first["refused_calls"], "takes_with_refusals": first["takes_with_refusals"],
        "takes_with_refusals_that_reached_the_question": first["takes_with_refusals_that_reached_the_question"],
        "by_model": first["by_model"], "by_harness_version": versions,
        "by_kind": first["by_kind"], "by_next": first["by_next"],
        "by_kind_2": {k: sum(1 for c in all_calls if c["kind_2"] == k) for k in rules2.KINDS_2},
        "by_next_2": {n: sum(1 for c in all_calls if c["next_2"] == n) for n in rules2.NEXT_2},
        "by_model_task": by_model_task,
        "helper_refusals": {"calls": len(helper), "worked_around": sum(1 for c in helper if c["next"] == "worked-around")},
        "project_log_refusals": {
            "calls": len(log), "next_2": {n: sum(1 for c in log if c["next_2"] == n) for n in rules2.NEXT_2},
            "takes": len(log_takes),
            "takes_whose_log_was_written_later": len(log_takes) - len(never),
            "takes_whose_log_was_never_written": len(never),
            "of_those_the_last_refused_attempt_ended_the_turn": sum(
                1 for t in never if t["project_log"]["last_refused_attempt_ended_the_turn"]),
        },
        "takes_with_refusals_that_did_not_reach_the_question": [
            {"take": f"{t['task']}/{t['half']}/{t['model']}/{t['take']}", "label": t["label"],
             "last_refused_call": {k: t["calls"][-1][k] for k in ("kind", "kind_2", "next", "next_2")}}
            for t in takes if not t["reached_question"]],
        "all_bash_calls_cross_tab": dict(sorted(cross.items())),
        "refusal_like_results_without_the_sentence": sweep,
        "note_split": NOTE_SPLIT,
        "takes": takes,
    }


def render2(data: dict) -> str:
    K2, N2 = rules2.KINDS_2, rules2.NEXT_2
    pl = data["project_log_refusals"]
    out = [
        "# The round 3 denials reading: result, with amendment 2",
        "",
        "Generated by `evals/validity-followups/round3_denials.py --write` from round 3's committed records; never "
        "typed. `--check` re-derives it. The first run's fields are those of `PREREG-DENIALS.md`; the second kind, the "
        "second \"next\" and every take-level figure are amendment 2's (`PREREG-DENIALS-2.md`), written after the first "
        "run and its review. The first run's own output is `DENIALS.md`, kept as it was. Nothing here re-grades a "
        "take, and nothing says what an unrefused run would have done or why the harness decided as it did.",
        "",
        "## The definitions (verbatim from the two pre-registration files)",
        "",
        "From `PREREG-DENIALS.md`:",
        "",
        prereg_section(PREREG, "## Definitions"),
        "",
        "From `PREREG-DENIALS-2.md`:",
        "",
        prereg_section(PREREG_2, "## What this adds (all in `denials_rules_2.py`, sha256 recorded below)"),
        "",
        "## Totals",
        "",
        f"Takes seen: {data['seen']}; read: {data['read']}. Refused calls: {data['refused_calls']}, in "
        f"{data['takes_with_refusals']} takes; {data['takes_with_refusals_that_reached_the_question']} of those "
        f"{data['takes_with_refusals']} takes still reached the question. The per-cell counts and the takes carrying a "
        "refusal equal `evals/gap-study-3/RESULT.md`'s, or this file would not have been written.",
        f"Refused helper calls (first-run kinds `cd-into-run`, `echo-appended`, `script-form`): "
        f"{data['helper_refusals']['calls']}, of which worked around: {data['helper_refusals']['worked_around']}.",
        f"Refused project-log writes: {pl['calls']} (" + ", ".join(f"{v} `{k}`" for k, v in pl["next_2"].items())
        + f"), in {pl['takes']} takes. The log was written by a later call in {pl['takes_whose_log_was_written_later']} "
        f"of those takes and never in {pl['takes_whose_log_was_never_written']}; in "
        f"{pl['of_those_the_last_refused_attempt_ended_the_turn']} of those "
        f"{pl['takes_whose_log_was_never_written']}, the agent's turn ended right after its last refused attempt.",
        "Takes with a refusal that did not reach the question: "
        + "; ".join(f"`{t['take']}` (`{t['label']}`; its last refused call `{t['last_refused_call']['kind_2']}`, "
                    f"`{t['last_refused_call']['next_2']}`)" for t in data["takes_with_refusals_that_did_not_reach_the_question"])
        + ".",
        "",
        "## By model, and by harness version",
        "",
        "| model | refused calls | takes with a refusal |",
        "|---|---|---|",
    ]
    for m in sorted(data["by_model"]):
        out.append(f"| `{m}` | {data['by_model'][m]['calls']} | {data['by_model'][m]['takes']} |")
    out += ["", "| Claude Code version | takes | refused calls |", "|---|---|---|"]
    for v in sorted(data["by_harness_version"]):
        r = data["by_harness_version"][v]
        out.append(f"| `{cell(v)}` | {r['takes']} | {r['refused_calls']} |")
    out += [
        "",
        "## By model and task (amendment 2's kind and next)",
        "",
        "| model/task | calls | takes | takes that reached the question | " + " | ".join(f"`{k}`" for k in K2)
        + " | " + " | ".join(f"`{n}`" for n in N2) + " |",
        "|---|---|---|---|" + "---|" * (len(K2) + len(N2)),
    ]
    for key in sorted(data["by_model_task"]):
        r = data["by_model_task"][key]
        out.append(f"| `{key}` | {r['calls']} | {r['takes']} | {r['takes_reached']} | "
                   + " | ".join(str(r["kinds_2"][k]) for k in K2) + " | "
                   + " | ".join(str(r["next_2"][n]) for n in N2) + " |")
    out.append(f"| **all** | **{data['refused_calls']}** | **{data['takes_with_refusals']}** | "
               f"**{data['takes_with_refusals_that_reached_the_question']}** | "
               + " | ".join(f"**{data['by_kind_2'][k]}**" for k in K2) + " | "
               + " | ".join(f"**{data['by_next_2'][n]}**" for n in N2) + " |")
    out += [
        "",
        "First run's kinds, for comparison: " + ", ".join(f"{v} `{k}`" for k, v in data["by_kind"].items())
        + ". First run's next: " + ", ".join(f"{v} `{k}`" for k, v in data["by_next"].items()) + ".",
        "Beside it, never compared: a research note of 6 October 2026 sorted the 35 by eye as "
        + ", ".join(f"{v} `{k}`" for k, v in data["note_split"].items()) + "; it read the `cd` as the refused part, as "
        "the first run's kinds did.",
        "",
        "## Every Bash call in round 3, admitted or refused",
        "",
        "| opens with `cd` / `echo` of `$?` / other `echo` | admitted | refused |",
        "|---|---|---|",
    ]
    for key, r in data["all_bash_calls_cross_tab"].items():
        out.append(f"| {key} | {r['admitted']} | {r['refused']} |")
    hits = data["refusal_like_results_without_the_sentence"]
    out += [
        "",
        f"Errored results worded like a refusal but without the pinned sentence: {len(hits)}"
        + (": " + "; ".join(f"`{h['take']}` ({h['tool']}): {cell(h['result'])}" for h in hits) if hits else "") + ".",
        "",
        "## Takes with a refused project-log write",
        "",
        "| take | label | refused log writes | log written by a later call | turn ended right after the last refused attempt |",
        "|---|---|---|---|---|",
    ]
    for t in data["takes"]:
        if t["project_log"]:
            p2 = t["project_log"]
            out.append(f"| `{t['task']}/{t['half']}/{t['model']}/{t['take']}` | `{t['label']}` | "
                       f"{p2['refused_log_writes']} | {'yes' if p2['log_written_later'] else 'no'} | "
                       f"{'yes' if p2['last_refused_attempt_ended_the_turn'] else 'no'} |")
    out += [
        "",
        "## Every refused call",
        "",
        "| take | harness | label | reached the question | # | kind (first run) | kind (amendment 2) | refused call | "
        "next (first run) | next (amendment 2) | dropped in the admitted retry | how |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t in data["takes"]:
        name = f"`{t['task']}/{t['half']}/{t['model']}/{t['take']}`"
        for i, c in enumerate(t["calls"], start=1):
            how = cell(c["worked_around_by"]["tool"] + ": " + c["worked_around_by"]["call"]) if c["worked_around_by"] else ""
            dropped = "; ".join(f"`{cell(x)}`" for x in c["dropped_in_the_admitted_retry"] or [])
            out.append(f"| {name} | {cell(t['harness'])} | `{t['label']}` | {'yes' if t['reached_question'] else 'no'} | "
                       f"{i} | `{c['kind']}` | `{c['kind_2']}` | `{cell(rules.first_line(c['command']))}` | "
                       f"`{c['next']}` | `{c['next_2']}` | {dropped} | {how} |")
    return "\n".join(out) + "\n"


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    problems = integrity_problems()
    if problems:
        for p in problems:
            print(f"refused: {p}", file=sys.stderr)
        return 2
    data = derive()
    data2 = derive2()
    outputs = ((OUT_JSON, dump(data)), (OUT_MD, render(data)), (OUT_JSON_2, dump(data2)), (OUT_MD_2, render2(data2)))
    if args.write:
        for path, body in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        print(f"wrote {', '.join(p.name for p, _ in outputs)}: {data['refused_calls']} refused calls in "
              f"{data['takes_with_refusals']} takes")
        return 0
    bad = [f"{p.name} differs from the re-derived reading" for p, body in outputs
           if not p.is_file() or p.read_text() != body]
    for b in bad:
        print(f"FAIL: {b}", file=sys.stderr)
    if bad:
        return 1
    print(f"ok: {data['refused_calls']} refused calls in {data['takes_with_refusals']} of {data['read']} takes "
          f"re-derived; by model " + ", ".join(f"{m} {v['calls']}" for m, v in sorted(data["by_model"].items()))
          + "; amendment 2 kinds " + ", ".join(f"{v} {k}" for k, v in data2["by_kind_2"].items())
          + "; next " + ", ".join(f"{v} {k}" for k, v in data2["by_next_2"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
