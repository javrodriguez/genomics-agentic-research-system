#!/usr/bin/env python3
"""What round 2's environment instrument reads on round 1's committed takes, written as a record that re-derives.

    python3 evals/gap-study-2/verification/round1-regrade/regrade_environment.py            print the reading
    python3 evals/gap-study-2/verification/round1-regrade/regrade_environment.py --write    write environment.json
    python3 evals/gap-study-2/verification/round1-regrade/regrade_environment.py --check    exit 1 unless the
                                                                                            committed record is
                                                                                            what this re-derives

WHY IT EXISTS (round 2, CP3, fix 4). Round 1 recorded no per-take environment (Ruling 34), so its $0 was the
operator's statement. Round 2's driver writes environment.json beside each transcript, its take checker refuses a
graded take without a valid one, and costs.py renders the dollar line from those records take by take. Run over
round 1's 108 graded takes, the instrument should refuse every one and evidence none. That is a reading of the
round-2 instrument on round-1 bytes, never a re-grade of round 1's result, and the record opens by saying so.

WHAT IT CALLS, AND NOTHING ELSE. check_take.environment_problems and costs.py's per-take evidence and dollar line,
each loaded by path from this study, against round 2's pre-registration as it is in force (the draft until the
freeze). Round 1's takes are enumerated from its committed takes.json and read from its transcripts folder, as
data, through study.ROUND1; nothing there is imported or written.

  - The checker is handed the transcript's folder, the round-1 driver ledger beside it, and no row commit. A
    missing record is refused before the row commit is bound, so no round-1 history is read; the record says so.
  - costs.read_environments is called as it stands, with its row-commit reader replaced by an empty map: round 2's
    row commits belong to round 2's ledger, and handing them to round 1's row numbers would bind the wrong rows.

THE EFFORT READING (data only). Decision 5: a take driven from a Claude Code pane may inherit that pane's effort
level. Each transcript's assistant records are read for a top-level `effort` and `perTurnEffort` key and counted
per model. The transcript cannot say where a value came from, and the record does not guess.

WHAT THE RECORD NEVER CARRIES. Round 1's transcripts hold machine paths. The record holds reason ids, the
checker's and costs.py's sentences, slot names and counts, and the write is refused (exit 2) if the rendered text
names this checkout, the home folder or a temporary folder.

Exit 0 as stated, 1 when --check finds a difference, 2 when round 1's takes cannot be read or the record would
carry a machine path. stdlib only, no model, no network.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_DIR = HERE.parent.parent
sys.path.insert(0, str(STUDY_DIR))

import prereg  # noqa: E402
import study  # noqa: E402

RECORD = HERE / "environment.json"
RECORD_SENTENCE = "what the round-2 instrument reads on round 1's committed transcripts — not round 1's result"
REASON = "environment-record"


def _load(name: str):
    """A module of this study by path, never by a sys.path lookup a first-study file of that name could win."""
    spec = importlib.util.spec_from_file_location(f"gap_study_2_round1_regrade_{name}", STUDY_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rel(path: Path) -> str:
    return path.resolve().relative_to(study.REPO).as_posix()


def round_one_takes() -> list[dict]:
    """Round 1's graded takes, from its committed ledger, in a fixed order; exit 2 if any transcript is absent."""
    ledger = study.ROUND1 / "takes.json"
    try:
        rows = json.loads(ledger.read_text())["rows"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise SystemExit(f"round 1's takes.json cannot be read ({type(exc).__name__}); nothing was measured")
    out = []
    for r in rows:
        folder = study.ROUND1 / "transcripts" / r["task"] / r["half"] / r["model"] / str(r["take"])
        out.append({"task": r["task"], "half": r["half"], "model": r["model"], "take": int(r["take"]),
                    "dir": folder})
    out.sort(key=lambda t: (t["task"], t["half"], t["model"], t["take"]))
    missing = [t for t in out if not (t["dir"] / "transcript.jsonl").is_file()]
    if not out or missing:
        raise SystemExit(f"round 1's ledger lists {len(out)} take(s) and {len(missing)} have no committed "
                         f"transcript; the reading would not cover what it names")
    return out


def effort_of(transcript: Path) -> dict:
    """The effort keys one transcript's assistant records carry, as flags."""
    efforts: list = []
    per_turn: list = []
    for line in transcript.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict) or rec.get("type") != "assistant":
            continue
        if "effort" in rec:
            efforts.append(rec["effort"])
        if "perTurnEffort" in rec:
            per_turn.append(rec["perTurnEffort"])
    return {"effort_high": "high" in efforts,
            "effort_other": any(e != "high" for e in efforts),
            "no_effort_key": not efforts,
            "per_turn_effort_null": bool(per_turn) and all(p is None for p in per_turn),
            "per_turn_effort_set": any(p is not None for p in per_turn),
            "no_per_turn_effort_key": not per_turn}


def derive() -> dict:
    pre = prereg.load()
    in_force = prereg.in_force()
    check_take = _load("check_take")
    costs = _load("costs")
    takes = round_one_takes()

    rows = []
    effort: dict[str, collections.Counter] = {}
    for t in takes:
        try:
            ledger = json.loads((t["dir"] / "driver-ledger.json").read_text())
        except (OSError, json.JSONDecodeError):
            ledger = None
        refusals = check_take.environment_problems(t["dir"], ledger, pre, None)
        rows.append({"task": t["task"], "half": t["half"], "model": t["model"], "take": t["take"],
                     "refusals": refusals})
        counter = effort.setdefault(t["model"], collections.Counter())
        counter["transcripts"] += 1
        counter.update(k for k, v in effort_of(t["dir"] / "transcript.jsonl").items() if v)

    # costs.py's own reading, per take and for the bill. Its row-commit reader is round 2's ledger history, which
    # is not round 1's; an empty map binds no row, and a missing record is judged before any row is bound.
    costs.row_commits = lambda: {}
    slots = [{"slot": (t["task"], t["half"], t["model"], str(t["take"])), "dir": t["dir"]} for t in takes]
    sub = costs.read_environments(slots)
    dollar_line = costs.bill_line(slots, sub)

    flags = ("transcripts", "effort_high", "effort_other", "no_effort_key", "per_turn_effort_null",
             "per_turn_effort_set", "no_per_turn_effort_key")
    return {
        "record": RECORD_SENTENCE,
        "instrument": {
            "checker": study.rel("check_take.py") + " environment_problems(transcript folder, round 1's driver "
                       "ledger, the pre-registration in force, row_commit null)",
            "bill": study.rel("costs.py") + " read_environments and bill_line, with row_commits replaced by an "
                    "empty map",
            "script": study.rel("verification", "round1-regrade", "regrade_environment.py"),
            "pre_registration": _rel(in_force),
            "pre_registration_sha256": hashlib.sha256(in_force.read_bytes()).hexdigest(),
            "round_1_takes": study.ROUND1_REL + "/takes.json",
            "round_1_transcripts": study.ROUND1_REL + "/transcripts/<task>/<half>/<model>/<take>/",
            "row_commit": "not bound: a missing record is refused before the row commit is compared, so no "
                          "round-1 history is read",
        },
        "takes": rows,
        "counts": {
            "graded": len(rows),
            "refused_environment_record": sum(1 for r in rows if REASON in check_take.reason_ids(r["refusals"])),
            "evidenced": sum(1 for s in slots if not s["environment"]),
        },
        "dollar_line": dollar_line,
        "effort_read": {
            "reads": "per model, how many of its round-1 transcripts carry each flag, read from the top-level "
                     "effort and perTurnEffort keys of assistant records. effort_high: some record says high. "
                     "effort_other: some record carries another value. no_effort_key: no record carries the key. "
                     "per_turn_effort_null: the key is present and null on every record that carries it. "
                     "per_turn_effort_set: some record carries a value. no_per_turn_effort_key: no record "
                     "carries the key. The transcript does not say where a value came from.",
            "by_model": {m: {f: c.get(f, 0) for f in flags} for m, c in sorted(effort.items())},
        },
    }


def render(record: dict) -> str:
    return json.dumps(record, indent=2, ensure_ascii=False) + "\n"


def machine_paths(text: str) -> list[str]:
    """The machine locations the text names, as labels only; the record is refused if there are any."""
    temp = Path(tempfile.gettempdir())
    probes = {"this checkout": str(study.REPO), "the home folder": str(Path.home()),
              "the folder above the home folder": str(Path.home().parent) + os.sep,
              "the temporary folder": str(temp), "the temporary folder, resolved": str(temp.resolve())}
    return [label for label, needle in probes.items() if len(needle) > 1 and needle in text]


def main() -> int:
    ap = argparse.ArgumentParser(description="Read round 1's committed takes with round 2's environment instrument.")
    ap.add_argument("--write", action="store_true", help="write the record")
    ap.add_argument("--check", action="store_true", help="exit 1 unless the record is what this re-derives")
    ap.add_argument("--record", type=Path, default=RECORD, help="the record --check compares (default: the "
                                                                "committed one)")
    args = ap.parse_args()

    record = derive()
    text = render(record)
    leaked = machine_paths(text)
    if leaked:
        print(f"REFUSING: the reading names {', '.join(leaked)}; nothing was written and nothing compared")
        return 2
    c = record["counts"]
    summary = (f"{c['graded']} graded, {c['refused_environment_record']} refused [{REASON}], "
               f"evidenced {c['evidenced']} of {c['graded']}")

    if args.write:
        RECORD.write_text(text)
        print(f"wrote {RECORD.name}: {summary}")
        return 0
    if args.check:
        try:
            committed = args.record.read_text()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"{args.record.name} cannot be read ({type(exc).__name__}); nothing matches the re-derivation")
            return 1
        if committed == text:
            print(f"{args.record.name} is what the regrade re-derives: {summary}")
            return 0
        old, new = committed.splitlines(), text.splitlines()
        at = next((i for i, (a, b) in enumerate(zip(old, new)) if a != b), min(len(old), len(new)))
        print(f"{args.record.name} is NOT what the regrade re-derives: first difference at line {at + 1} "
              f"({len(old)} committed line(s), {len(new)} re-derived). Run: python3 "
              f"{study.rel('verification', 'round1-regrade', 'regrade_environment.py')} --write")
        return 1

    print(summary)
    print(f"dollar line: {record['dollar_line'][:300]}{'...' if len(record['dollar_line']) > 300 else ''}")
    for m, flags in record["effort_read"]["by_model"].items():
        print(f"effort {m}: {flags}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
