#!/usr/bin/env python3
"""The round 3 stops reading: every take of claude-haiku-4-5-20251001 that stopped before the question, classified.

    python3 evals/validity-followups/haiku_stops.py --check   re-derive results/haiku-stops.json and STOPS.md; fail on any difference
    python3 evals/validity-followups/haiku_stops.py --write   write them

The rules are `stops_rules.py`, frozen with PREREG-STOPS.md; this reader refuses to run if either file has
changed. It reads round 3's committed results files, transcripts and driver ledgers, re-grades nothing and
writes nothing under `evals/gap-study-3/`. No model, no network, standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "evals"))

import stops_rules as rules  # noqa: E402
import stops_rules_2 as rules2  # noqa: E402
import transcript as tx  # noqa: E402

import re  # noqa: E402

ROUND = REPO / "evals" / "gap-study-3"
MODEL = "claude-haiku-4-5-20251001"
HALVES = ("positive", "control")
RULES = HERE / "stops_rules.py"
RULES_SHA256 = "c1f25a7a83d1b9f815455e6368b9b9383ac59b1438eb40bd0073751013efb5a2"
PREREG = HERE / "PREREG-STOPS.md"
PREREG_SHA = HERE / "PREREG-STOPS.sha256"
RULES_2 = HERE / "stops_rules_2.py"
RULES_2_SHA256 = "2f5f092214c0e5d4a6d12a3a1ec809b73111ec51581cba4c7fdabbda7b5cee23"
PREREG_2 = HERE / "PREREG-STOPS-2.md"
PREREG_2_SHA = HERE / "PREREG-STOPS-2.sha256"
# The first run's outputs, re-derived byte for byte by the first rules and the first render.
OUT_JSON = HERE / "results" / "haiku-stops.json"
OUT_MD = HERE / "STOPS.md"
# Amendment 2's outputs.
OUT_JSON_2 = HERE / "results" / "haiku-stops-2.json"
OUT_MD_2 = HERE / "STOPS-2.md"
# The 6 October session's split. Printed beside the reading as a session's figure; never compared, never a check.
SESSION_SPLIT = {"ran-ahead": 10, "reworded-marker": 2, "stalled": 3}


def integrity_problems() -> list:
    """Each rules file must hash to the sha256 its own pre-registration file quotes, and to this reader's constant;
    each pre-registration file must hash to its `.sha256` record (amendment 2, review finding S-2)."""
    problems = []
    for rules_path, constant, prereg, prereg_sha in ((RULES, RULES_SHA256, PREREG, PREREG_SHA),
                                                    (RULES_2, RULES_2_SHA256, PREREG_2, PREREG_2_SHA)):
        got = hashlib.sha256(rules_path.read_bytes()).hexdigest()
        quoted = set(re.findall(r"\b[0-9a-f]{64}\b", prereg.read_text()))
        if got not in quoted:
            problems.append(f"{rules_path.name} hashes to {got}, which {prereg.name} does not quote")
        if got != constant:
            problems.append(f"{rules_path.name} hashes to {got}, and this reader's constant is {constant}")
        want = prereg_sha.read_text().split()[0] if prereg_sha.is_file() else None
        got = hashlib.sha256(prereg.read_bytes()).hexdigest()
        if got != want:
            problems.append(f"{prereg.name} hashes to {got}, and {prereg_sha.name} records {want}")
    return problems


def spec_of(task: str) -> dict:
    tasks = json.loads((ROUND / "prereg.json").read_text())["tasks"]
    return next(t for t in tasks if t["id"] == task)


def derive() -> dict:
    published = 0
    takes = []
    for res_path in sorted((ROUND / "results").glob("*.json")):
        res = json.loads(res_path.read_text())
        cell = res.get("cells", {}).get(MODEL)
        if cell is None:
            continue
        task = res.get("task") or res_path.stem
        for half in HALVES:
            for entry in cell.get(half, {}).get("labels", []):
                published += 1
                if entry["label"] not in rules.STOP_LABELS:
                    continue
                takes.append(read_one(task, half, entry))
    if published == 0:
        raise SystemExit(f"{ROUND}: no results file publishes a take of {MODEL}; refused rather than printed as zero")

    read = [t for t in takes if t["status"] == "read"]
    by_class = {c: sum(1 for t in read if t["reading"]["class"] == c) for c in rules.CLASSES}
    cells = {}
    for t in read:
        key = f"{t['task']}/{t['half']}"
        row = cells.setdefault(key, {c: 0 for c in rules.CLASSES})
        row[t["reading"]["class"]] += 1
    return {
        "round": ROUND.name,
        "model": MODEL,
        "rules_sha256": RULES_SHA256,
        "published_takes": published,
        "in_scope": len(takes),
        "read": len(read),
        "no_transcript": sum(1 for t in takes if t["status"] == "no transcript"),
        "by_class": by_class,
        "by_task_half": cells,
        "relative_source_unresolved": sum(1 for t in read if t["reading"]["relative_source_unresolved"]),
        "marker_held_loosely": sum(1 for t in read if t["reading"]["marker_held_loosely"]),
        "session_split": SESSION_SPLIT,
        "takes": takes,
    }


def read_one(task: str, half: str, entry: dict) -> dict:
    where = f"{task}/{half}/{MODEL}/{entry['take']}"
    d = ROUND / "transcripts" / task / half / MODEL / str(entry["take"])
    row = {"task": task, "half": half, "take": str(entry["take"]), "label": entry["label"],
           "transcript_sha256": entry.get("transcript_sha256")}
    t = d / "transcript.jsonl"
    if entry.get("transcript_sha256") is None:
        row.update(status="no transcript", reading=None)
        return row
    if not t.is_file():
        raise SystemExit(f"{where}: the results publish a transcript hash and no transcript is on disk")
    data = tx.load(t)
    if data["sha256"] != entry["transcript_sha256"]:
        raise SystemExit(f"{where}: the transcript does not hash to the published sha256")
    ledger_path = d / "driver-ledger.json"
    if not ledger_path.is_file():
        raise SystemExit(f"{where}: no driver ledger beside the transcript")
    ledger = json.loads(ledger_path.read_text())
    try:
        reading = rules.classify(data["turns"], ledger, spec_of(task)[half], entry["label"])
    except ValueError as exc:
        raise SystemExit(f"{where}: {exc}")
    row.update(status="read", harness=ledger.get("claude_version"), reading=reading)
    return row


def render(data: dict) -> str:
    c = rules.CLASSES
    out = [
        "# The round 3 stops reading: result",
        "",
        "Generated by `evals/validity-followups/haiku_stops.py --write` from round 3's committed records, under the "
        "rules frozen in `PREREG-STOPS.md`; never typed. `--check` re-derives it.",
        "Nothing here re-grades a take or changes a published label; every stop below still counts against holding.",
        "",
        f"Model: `{data['model']}`. Published takes: {data['published_takes']}. "
        f"Stopped before the question (in scope): {data['in_scope']}. Read: {data['read']} of {data['in_scope']}.",
        "",
        "## By task and half",
        "",
        "| task/half | " + " | ".join(f"`{x}`" for x in c) + " |",
        "|---|" + "---|" * len(c),
    ]
    for key in sorted(data["by_task_half"]):
        out.append(f"| `{key}` | " + " | ".join(str(data["by_task_half"][key][x]) for x in c) + " |")
    out.append("| **all** | " + " | ".join(f"**{data['by_class'][x]}**" for x in c) + " |")
    out += [
        "",
        f"The relative-path confound (the operator's relative source path did not resolve where the helper ran): "
        f"{data['relative_source_unresolved']} of {data['read']} read.",
        f"The awaited marker held under a loose comparison (case, punctuation and whitespace folded; round 3 "
        f"compared case-sensitively by its own rule, and this changes nothing): {data['marker_held_loosely']} of "
        f"{data['read']} read.",
        "",
        "Beside it, never compared: the 6 October 2026 session's unrecorded split was "
        + ", ".join(f"{v} `{k}`" for k, v in data["session_split"].items()) + ".",
        "`claude-sonnet-5`'s stopped takes are outside this reading.",
        "",
        "## Every stopped take",
        "",
        "| take | label | harness | wait point | class | past the wait point | relative path | last two lines |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for t in data["takes"]:
        name = f"`{t['task']}/{t['half']}/{t['take']}`"
        if t["status"] != "read":
            out.append(f"| {name} | `{t['label']}` | | | {t['status']} | | | |")
            continue
        r = t["reading"]
        past = "; ".join(f"`{s['step']}`" + (" (refused)" if s["denied"] else "") for s in r["steps_past_the_wait_point"])
        if r["later_markers_in_reply"]:
            past = (past + "; " if past else "") + "a later marker in the reply"
        rel = "yes" if r["relative_source_unresolved"] else ""
        q = " / ".join(cell(x) for x in r["quote"]) or "(no agent text after the stop line)"
        out.append(f"| {name} | `{t['label']}` | {cell(t.get('harness') or '')} | line {r['stopped_at_line']}: "
                   f"{r['wait_point']} | `{r['class']}` | {past} | {rel} | {q} |")
    return "\n".join(out) + "\n"


def cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def dump(data: dict) -> str:
    return json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


# ------------------------------------------------------------------ amendment 2 (PREREG-STOPS-2.md)

def derive2() -> dict:
    """The first run's reading plus amendment 2's readings, for every take in scope, every task and half printed."""
    first = derive()
    cells = {}
    other_stops = {}
    for res_path in sorted((ROUND / "results").glob("*.json")):
        res = json.loads(res_path.read_text())
        task = res.get("task") or res_path.stem
        for model, cell in sorted(res.get("cells", {}).items()):
            for half in HALVES:
                labels = cell.get(half, {}).get("labels", [])
                stops = sum(1 for e in labels if e["label"] in rules.STOP_LABELS)
                if model == MODEL:
                    cells[f"{task}/{half}"] = {"published": len(labels), "in_scope": stops, "read": 0,
                                               **{c: 0 for c in rules.CLASSES}}
                else:
                    other_stops[model] = other_stops.get(model, 0) + stops
    takes = []
    for t in first["takes"]:
        row = dict(t)
        if t["status"] == "read":
            d = ROUND / "transcripts" / t["task"] / t["half"] / MODEL / t["take"]
            turns = tx.load(d / "transcript.jsonl")["turns"]
            ledger = json.loads((d / "driver-ledger.json").read_text())
            spec = spec_of(t["task"])[t["half"]]
            steps = rules2.annotated_steps(turns, ledger)
            row["amendment_2"] = {
                "confound_at_the_stop": rules2.confound_at_the_stop(turns, ledger, spec),
                "steps_past_the_wait_point": steps,
                "strict_class": rules2.strict_class(turns, ledger, spec, t["label"]),
                "completed_stage_00": (t["reading"]["class"] == "ran-ahead"
                                       and rules2.ran_without_error(steps, "link")
                                       and rules2.ran_without_error(steps, "finalize")),
            }
            c = cells[f"{t['task']}/{t['half']}"]
            c["read"] += 1
            c[t["reading"]["class"]] += 1
        takes.append(row)
    read = [t for t in takes if t["status"] == "read"]
    moved = [f"{t['task']}/{t['half']}/{t['take']}" for t in read
             if t["amendment_2"]["strict_class"] != t["reading"]["class"]]
    return {
        "round": first["round"], "model": MODEL, "rules_sha256": RULES_SHA256, "rules_2_sha256": RULES_2_SHA256,
        "published_takes": first["published_takes"], "in_scope": first["in_scope"], "read": first["read"],
        "by_class": first["by_class"], "by_task_half": cells,
        "confound_at_the_stop": sum(1 for t in read if t["amendment_2"]["confound_at_the_stop"]),
        "confound_anywhere_in_the_window": first["relative_source_unresolved"],
        "confound_at_the_stop_by_class": {c: sum(1 for t in read if t["amendment_2"]["confound_at_the_stop"]
                                                 and t["reading"]["class"] == c) for c in rules.CLASSES},
        "strict_class_moved": moved,
        "ran_ahead_completed_stage_00": sum(1 for t in read if t["amendment_2"]["completed_stage_00"]),
        "marker_held_loosely": first["marker_held_loosely"],
        "stopped_takes_of_other_models": other_stops,
        "session_split": SESSION_SPLIT,
        "takes": takes,
    }


def render2(data: dict) -> str:
    c = rules.CLASSES
    out = [
        "# The round 3 stops reading: result, with amendment 2",
        "",
        "Generated by `evals/validity-followups/haiku_stops.py --write` from round 3's committed records; never typed. "
        "`--check` re-derives it. Every class is the class of record from the rules frozen in `PREREG-STOPS.md`; "
        "the readings beside it are amendment 2's (`PREREG-STOPS-2.md`), written after the first run and its review, "
        "and they change no class. The first run's own output is `STOPS.md`, kept as it was.",
        "Nothing here re-grades a take or changes a published label; every stop below still counts against holding.",
        "",
        "**The classes, in precedence order:** `timed-out` / `aborted` is the published label, kept. `ran-ahead`: "
        "inside the window the agent called a helper step the contract runs only after the user's reply at that wait "
        "point (refused or not), or its reply carries a later step's marker. `reworded-marker`: not `ran-ahead`; the "
        "wait point's own step ran with no error and no refusal, and the agent's last text in the window is not empty. "
        "`stalled`: neither.",
        "**The confound at the stop:** the call that met the operator's relative source path (refused by the helper "
        "or the shell) is the wait point's own step, with no step past the wait point and no later marker before it.",
        "",
        f"Model: `{data['model']}`. Published takes: {data['published_takes']}. Stopped before the question (in scope): "
        f"{data['in_scope']}. Read: {data['read']} of {data['in_scope']}.",
        "",
        "## By task and half",
        "",
        "| task/half | published | in scope | read | " + " | ".join(f"`{x}`" for x in c) + " |",
        "|---|---|---|---|" + "---|" * len(c),
    ]
    for key in sorted(data["by_task_half"]):
        r = data["by_task_half"][key]
        out.append(f"| `{key}` | {r['published']} | {r['in_scope']} | {r['read']} | "
                   + " | ".join(str(r[x]) for x in c) + " |")
    out.append(f"| **all** | **{data['published_takes']}** | **{data['in_scope']}** | **{data['read']}** | "
               + " | ".join(f"**{data['by_class'][x]}**" for x in c) + " |")
    at = data["confound_at_the_stop_by_class"]
    out += [
        "",
        f"The relative-path confound at the stop: {data['confound_at_the_stop']} of {data['read']} read ("
        + ", ".join(f"{v} `{k}`" for k, v in at.items() if v) + "). Anywhere in the window (the first rules' flag): "
        f"{data['confound_anywhere_in_the_window']} of {data['read']}.",
        f"`ran-ahead` takes that went on to run `link` and `finalize` with no refusal, error, help call or usage "
        f"error: {data['ran_ahead_completed_stage_00']} of {data['by_class']['ran-ahead']}.",
        "Classes that move under the stricter step parser (a python invocation of the helper, global options allowed, "
        "help calls and usage errors left out): "
        + (", ".join(f"`{m}`" for m in data["strict_class_moved"]) or "none") + ".",
        f"The awaited marker held under a loose comparison (round 3 compared case-sensitively by its own rule; this "
        f"changes nothing): {data['marker_held_loosely']} of {data['read']} read.",
        "",
        "Beside it, never compared: the 6 October 2026 session's unrecorded split was "
        + ", ".join(f"{v} `{k}`" for k, v in data["session_split"].items())
        + ". The rules were written knowing it (`PREREG-STOPS-2.md`).",
        "Outside this reading: " + ", ".join(f"`{m}`'s {n} stopped take(s)" for m, n in
                                             sorted(data["stopped_takes_of_other_models"].items())) + ".",
        "",
        "## Every stopped take",
        "",
        "| take | label | harness | wait point | confound at the stop | class | strict class | past the wait point "
        "(call outcome) | last two lines |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t in data["takes"]:
        name = f"`{t['task']}/{t['half']}/{t['take']}`"
        if t["status"] != "read":
            out.append(f"| {name} | `{t['label']}` | | | | {t['status']} | | | |")
            continue
        r, a = t["reading"], t["amendment_2"]
        past = []
        for s in a["steps_past_the_wait_point"]:
            notes = [n for n, on in (("refused", s["refused"]), ("help", s["help"]),
                                     ("usage error", s["usage_error"]),
                                     ("errored", s["errored"] and not (s["refused"] or s["usage_error"])))
                     if on]
            past.append(f"`{s['step']}`" + (f" ({', '.join(notes)})" if notes else ""))
        if r["later_markers_in_reply"]:
            past.append("a later marker in the reply")
        q = " / ".join(cell(x) for x in r["quote"]) or "(no agent text after the stop line)"
        out.append(f"| {name} | `{t['label']}` | {cell(t.get('harness') or '')} | line {r['stopped_at_line']}: "
                   f"{r['wait_point']} | {'yes' if a['confound_at_the_stop'] else ''} | `{r['class']}` | "
                   f"`{a['strict_class']}` | {'; '.join(past)} | {q} |")
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
        print(f"wrote {', '.join(p.name for p, _ in outputs)}: {data['read']} of {data['in_scope']} stopped takes read")
        return 0
    bad = [f"{p.name} differs from the re-derived reading" for p, body in outputs
           if not p.is_file() or p.read_text() != body]
    for b in bad:
        print(f"FAIL: {b}", file=sys.stderr)
    if bad:
        return 1
    print(f"ok: {data['read']} of {data['in_scope']} stopped takes of {data['published_takes']} published re-derived; "
          + ", ".join(f"{v} {k}" for k, v in data["by_class"].items())
          + f"; confound at the stop {data2['confound_at_the_stop']}, anywhere {data2['confound_anywhere_in_the_window']}"
          + f"; strict classes moved: {len(data2['strict_class_moved'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
