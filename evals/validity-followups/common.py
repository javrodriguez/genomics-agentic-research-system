#!/usr/bin/env python3
"""Shared machinery for the validity follow-ups' scripts: the frozen-file checks, the count loop, the tables.

The reading rules are not here; they are in `rules.py`, which PREREG.md quotes byte for byte. This file only
walks the takes `rules.published_takes` names, applies a rule, and prints or checks what it counted.
Standard library only; writes only under evals/validity-followups/.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

import rules  # noqa: E402

HERE = Path(__file__).resolve().parent
PREREG = HERE / "PREREG.md"
PREREG_SHA = HERE / "PREREG.sha256"
RULES = HERE / "rules.py"
RESULTS_MD = HERE / "RESULTS.md"
OUT = HERE / "results"
RULES_HEADING = "## The rules, as code"
HALF_ORDER = {"positive": 0, "control": 1}


# ------------------------------------------------------------------ the frozen files

def rules_block_problems(rules_text: str, prereg_text: str) -> list[str]:
    """Whether rules.py is byte-identical to the python block under PREREG.md's rules heading."""
    at = prereg_text.find(RULES_HEADING)
    if at < 0:
        return ["PREREG.md has no rules section"]
    start = prereg_text.find("```python\n", at)
    end = prereg_text.find("\n```", start + 10)
    if start < 0 or end < 0:
        return ["PREREG.md's rules section has no python block"]
    block = prereg_text[start + len("```python\n"):end + 1]
    return [] if block == rules_text else ["rules.py is not the text PREREG.md froze"]


def integrity_problems() -> list[str]:
    problems = []
    want = PREREG_SHA.read_text().split()[0]
    got = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    if got != want:
        problems.append(f"PREREG.md hashes to {got}, and PREREG.sha256 records {want}")
    problems += rules_block_problems(RULES.read_text(), PREREG.read_text())
    return problems


# ------------------------------------------------------------------ the count loop

BASE_COLUMNS = ("seen", "read", "no_transcript", "hash_unpublished", "probe_not_found")


def derive_counts(fid: str, columns: tuple, primary: str, per_take) -> dict:
    """Every published take in the follow-up's scope, read and matched by `per_take`; one row per round, half and
    published label. A round in scope that publishes no take, or a run that reads none, is refused rather than
    printed as zero."""
    task, rnds, halves = rules.SCOPE[fid]
    rows: dict[tuple, dict] = {}
    matched = []
    for rnd in rnds:
        spec = rules.spec_of(rnd, task)
        seen_round = read_round = 0
        for half in halves:
            for t in rules.published_takes(rnd, task, half):
                row = rows.setdefault((rnd, HALF_ORDER[half], t["label"]), {
                    "round": rnd, "half": half, "label": t["label"],
                    **{c: 0 for c in BASE_COLUMNS}, **{c: 0 for c in columns}})
                row["seen"] += 1
                seen_round += 1
                turns, status = rules.load_turns(t)
                if status == "no transcript":
                    row["no_transcript"] += 1
                    continue
                if status != "read":
                    row["hash_unpublished"] += 1
                    continue
                row["read"] += 1
                read_round += 1
                if not rules.probe_found(turns, spec[half]):
                    row["probe_not_found"] += 1
                    continue
                said, tools = rules.after_probe(rnd, turns, spec[half])
                got = per_take(rnd, spec, half, turns, said, tools)
                for c in columns:
                    row[c] += int(bool(got[c]))
                if got[primary]:
                    matched.append({"take": t["id"], "label": t["label"], "transcript_sha256": t["sha256"],
                                    **{c: bool(got[c]) for c in columns}})
        if seen_round == 0:
            raise SystemExit(f"{fid}: round {rnd} publishes no {task} take on {', '.join(halves)}; "
                             f"a count over nothing is refused")
        if read_round == 0:
            raise SystemExit(f"{fid}: round {rnd} publishes {seen_round} take(s) and none could be read")
    return {"id": fid, "task": task, "rounds": list(rnds), "halves": list(halves), "columns": list(columns),
            "primary": primary, "rows": [rows[k] for k in sorted(rows)], "matched": matched}


def render_counts(data: dict, names: dict) -> str:
    cols = data["columns"]
    head = ["Round", "Half", "Published label", "Published (M)", "Read (N)", "No transcript",
            "Probe not found"] + [names[c] for c in cols]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in data["rows"]:
        no_tx = r["no_transcript"] + r["hash_unpublished"]
        cells = [str(r["round"]), r["half"], f"`{r['label']}`", str(r["seen"]), str(r["read"]), str(no_tx),
                 f"{r['probe_not_found']} of {r['read']}"] + [f"{r[c]} of {r['read']}" for c in cols]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    for rnd in data["rounds"]:
        rs = [r for r in data["rows"] if r["round"] == rnd]
        k = sum(r[data["primary"]] for r in rs)
        n = sum(r["read"] for r in rs)
        m = sum(r["seen"] for r in rs)
        lines.append(f"Round {rnd}, {names[data['primary']]}, every published label: "
                     f"{k} of {n} takes read ({m} published).  ")
    return "\n".join(lines).rstrip()


# ------------------------------------------------------------------ output and --check

def dump(data: dict) -> str:
    return json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def render_block(fid: str, table: str) -> str:
    return f"<!-- vf:{fid} -->\n{table}\n<!-- /vf:{fid} -->"


def _block_in(text: str, fid: str) -> str | None:
    m = re.search(rf"<!-- vf:{re.escape(fid)} -->\n(?:.*?\n)?<!-- /vf:{re.escape(fid)} -->", text, re.S)
    return m.group(0) if m else None


def compare(data: dict, table: str, json_path: Path, results_md: Path) -> list[str]:
    problems = []
    if not json_path.is_file() or json_path.read_text() != dump(data):
        problems.append(f"{json_path.name} is not what the script derives")
    have = _block_in(results_md.read_text(), data["id"]) if results_md.is_file() else None
    if have != render_block(data["id"], table):
        problems.append(f"RESULTS.md's {data['id']} table is not what the script derives")
    return problems


def write(data: dict, table: str) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / f"{data['id']}.json").write_text(dump(data))
    if RESULTS_MD.is_file():
        text = RESULTS_MD.read_text()
        have = _block_in(text, data["id"])
        if have is not None:
            RESULTS_MD.write_text(text.replace(have, render_block(data["id"], table)))


def main(derive, render, argv: list[str]) -> int:
    problems = integrity_problems()
    if problems:
        print("\n".join(f"REFUSED: {p}" for p in problems))
        return 1
    data = derive()
    table = render(data)
    print(table)
    if "--write" in argv:
        write(data, table)
    if "--check" in argv:
        problems = compare(data, table, OUT / f"{data['id']}.json", RESULTS_MD)
        for p in problems:
            print(f"CHECK FAILED: {p}")
        print(f"{data['id']} --check: {'FAILED' if problems else 'the published table re-derives'}")
        return 1 if problems else 0
    return 0
