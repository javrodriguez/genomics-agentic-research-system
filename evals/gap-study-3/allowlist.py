#!/usr/bin/env python3
"""Derive the permission condition from round 2's own transcripts, by code, and say what it admits.

    python3 evals/gap-study-3/allowlist.py --derive   print every candidate entry with where it was quoted from
    python3 evals/gap-study-3/allowlist.py --write    record the derivation in allowlist-derivation.json
    python3 evals/gap-study-3/allowlist.py --check    re-derive it and exit 1 on any difference, including
                                                      against the entries the pre-registration pins

WHAT THIS IS FOR. Round 3's axis is the model, so the harness must not vary across it. Round 2 passed one
permission flag to all three models and the smallest model's sessions ran under a different mode anyway,
where its first command was refused before it could do anything: the published zeros for that model may
describe the harness. Round 3 therefore passes the same pre-registered list of admitted commands on every
turn of every take. What that list contains is the single most consequential thing about this round, so it
is derived here from bytes rather than chosen, and the derivation prints, per entry, the transcript and the
line the entry was quoted from.

THE TWO RULES THE ENTRIES MUST OBEY, AND WHY.

  1. NO BARE BINARY WILDCARD. `python3` alone would admit every program that interpreter can run,
     including ones no route has ever used. An entry is a binary AND at least one more token.
  2. NO ENTRY WIDER THAN A FORM QUOTED VERBATIM. Every entry must appear, character for character, at the
     START of at least one command an agent actually ran on that task before its probe. An entry nobody
     ran is a guess about the route, and a guess widens the condition without evidence.

Together those rules mean the list cannot be written by hand and cannot be widened by argument. It can only
be narrowed -- by the owner, at his gate -- and every narrowing is visible as calls this list would refuse.

WHAT THE DERIVATION CANNOT DO, SAID BEFORE ANYONE ASKS. A command whose first argument is a path unique to
the run that produced it -- `cd /…/run-9463df65 && …` -- has no verbatim prefix that would match another
run, so no legal entry admits it. Those calls are counted and printed as REFUSED BY CONSTRUCTION, not
quietly dropped. Whether the route still walks without them is a question for a probe, not for this file.

EVERY ENTRY IS CLASSIFIED, because "derived from a transcript" is not the same as "narrow":

  route      the second token names a program or subcommand of the system under test
  shape      the second token is a flag, so the entry admits that flag against any target
  arbitrary  the second token lets the caller supply the program text itself (`python3 -c`, `python3 -`)

An `arbitrary` entry is derived, legal by both rules above, and as wide in practice as the bare binary the
first rule forbids. The derivation says so in those words rather than letting the classification pass as
narrowness.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402
import round2  # noqa: E402
import study  # noqa: E402

DERIVATION = HERE / "allowlist-derivation.json"

# A first argument that cannot be part of an entry, because it names one run and no other.
RUN_SPECIFIC = re.compile(r"^(?:/|~|\.{1,2}/)|run-[0-9a-f]{8}")
# Shell punctuation: a command that opens with one of these has no form to quote.
PUNCTUATION = {"&&", "||", ";", "|", ">", ">>", "<", "<<", "(", "{", "&"}
# Second tokens that hand the interpreter its program on the command line or on stdin.
ARBITRARY_ARGS = {"-c", "-", "-m", "--command", "-e"}


def tokens(command: str) -> list[str]:
    """Split on whitespace WITHOUT shell parsing, so an entry is a literal prefix of the command string.

    shlex would strip quotes, and an entry built from stripped tokens would no longer be a prefix of the
    bytes the harness matches against. The rule is verbatim, so the split has to be verbatim too.
    """
    return command.split()


def candidate(command: str) -> tuple[str | None, str]:
    """The narrowest legal entry for this command, or None with the reason there is none."""
    toks = tokens(command)
    if not toks:
        return None, "empty command"
    if toks[0] in PUNCTUATION or toks[0].startswith(tuple(PUNCTUATION)):
        return None, f"opens with shell punctuation ({toks[0]!r}), so it has no form to quote"
    if len(toks) < 2:
        return None, f"{toks[0]!r} alone is a bare binary, and a bare binary wildcard is not an entry"
    arg = toks[1]
    if arg in PUNCTUATION:
        return None, f"the first argument is shell punctuation ({arg!r}); the entry would be a bare binary"
    if RUN_SPECIFIC.search(arg):
        return None, "the first argument is a path naming one run, so no verbatim prefix of it matches another"
    return f"{toks[0]} {arg}", ""


def classify(entry: str) -> str:
    arg = entry.split(" ", 1)[1]
    if arg in ARBITRARY_ARGS:
        return "arbitrary"
    if arg.startswith("-"):
        return "shape"
    return "route"


def derive() -> dict:
    rows = round2.pre_probe_commands()
    entries: dict[str, dict] = {}
    refused: list[dict] = []
    for r in rows:
        entry, why = candidate(r["command"])
        if entry is None:
            refused.append({**{k: r[k] for k in ("task", "half", "model", "take", "line")},
                            "command": r["command"][:200], "why": why})
            continue
        e = entries.setdefault(entry, {
            "entry": entry, "tool": f"Bash({entry}:*)", "class": classify(entry), "calls": 0,
            "tasks": set(), "quoted_from": {k: r[k] for k in ("task", "half", "model", "take", "line")}
            | {"command": r["command"][:200]}})
        e["calls"] += 1
        e["tasks"].add(r["task"])
    out_entries = []
    for e in sorted(entries.values(), key=lambda x: (-x["calls"], x["entry"])):
        e = dict(e)
        e["tasks"] = sorted(e["tasks"])
        out_entries.append(e)
    per_task = collections.Counter(r["task"] for r in rows)
    per_task_refused = collections.Counter(r["task"] for r in refused)
    return {
        "role": "Every entry the permission condition could legally carry, derived by code from round 2's "
                "committed transcripts. An entry is a verbatim prefix of a command an agent ran before its "
                "probe, is never a bare binary, and carries the transcript and line it was quoted from.",
        "source": {"round": study.ROUND1_REL, "transcripts": len(round2.transcripts()),
                   "tasks": list(round2.TASKS)},
        "calls_seen": len(rows),
        "calls_admitted": len(rows) - len(refused),
        "calls_refused_by_construction": len(refused),
        "per_task": {t: {"seen": per_task[t], "refused": per_task_refused[t]} for t in round2.TASKS},
        "by_class": dict(collections.Counter(e["class"] for e in out_entries)),
        "entries": out_entries,
        "refused_by_construction": refused,
    }


def pinned() -> list[str] | None:
    """The entries the pre-registration pins, if there is one to read yet."""
    try:
        pre = prereg.load()
    except SystemExit:
        return None
    return list((pre.get("driver_change") or {}).get("allowed_tools") or []) or None


def problems(rec: dict) -> list[str]:
    out = []
    if rec["calls_seen"] == 0:
        out.append("the derivation read 0 pre-probe commands: it has graded nothing and is not a pass")
    for e in rec["entries"]:
        if " " not in e["entry"]:
            out.append(f"{e['entry']!r} is a bare binary wildcard")
        if not e["quoted_from"]["command"].startswith(e["entry"]):
            out.append(f"{e['entry']!r} is not a verbatim prefix of the command it cites")
        if e["quoted_from"]["line"] == 0:
            out.append(f"{e['entry']!r} cites a transcript line the derivation could not find")
        if not (REPO / round2.transcript_rel(e["quoted_from"])).is_file():
            out.append(f"{e['entry']!r} cites a transcript that does not exist")
    chosen = pinned()
    if chosen is not None:
        legal = {e["tool"] for e in rec["entries"]}
        for tool in chosen:
            if tool not in legal:
                out.append(f"the pre-registration pins {tool!r}, which this derivation does not produce: "
                           f"an entry no route quoted is a guess about the route")
    return out


def report(rec: dict) -> str:
    L = [f"Derived from {rec['source']['transcripts']} committed transcript(s) of "
         f"{', '.join(rec['source']['tasks'])} in {rec['source']['round']}.",
         f"{rec['calls_seen']} pre-probe Bash call(s) seen; {rec['calls_admitted']} admitted by some legal "
         f"entry, {rec['calls_refused_by_construction']} refused by construction.", ""]
    for t, c in rec["per_task"].items():
        L.append(f"  {t:22} {c['seen']:>4} call(s) seen, {c['refused']:>3} with no legal entry")
    L += ["", f"{len(rec['entries'])} candidate entr(y/ies), by class {rec['by_class']}:", ""]
    for e in rec["entries"]:
        q = e["quoted_from"]
        L.append(f"  {e['tool']}")
        L.append(f"      class {e['class']}   {e['calls']} call(s)   tasks: {', '.join(e['tasks'])}")
        L.append(f"      quoted from {round2.transcript_rel(q)} line {q['line']}")
        L.append(f"      {q['command'][:110]}")
    if rec["refused_by_construction"]:
        L += ["", f"REFUSED BY CONSTRUCTION — {len(rec['refused_by_construction'])} call(s) no legal entry "
                  f"admits. These are printed, never dropped; whether a route walks without them is a "
                  f"question for a probe."]
        shown = collections.Counter(r["why"] for r in rec["refused_by_construction"])
        for why, n in shown.most_common():
            L.append(f"  {n:>4}  {why}")
        L.append("  first five, verbatim:")
        for r in rec["refused_by_construction"][:5]:
            L.append(f"      {round2.transcript_rel(r)} line {r['line']}: {r['command'][:100]}")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--derive", action="store_true")
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    args = ap.parse_args()
    rec = derive()
    bad = problems(rec)
    if args.derive:
        print(report(rec))
        for b in bad:
            print(f"FAIL {b}")
        return 1 if bad else 0
    if args.write:
        if bad:
            print("refusing to write:\n  - " + "\n  - ".join(bad))
            return 1
        DERIVATION.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"wrote {DERIVATION.name}: {len(rec['entries'])} candidate entries from "
              f"{rec['calls_seen']} call(s)")
        return 0
    if not DERIVATION.is_file():
        print("no allowlist-derivation.json")
        return 1
    if json.loads(DERIVATION.read_text()) != rec:
        bad.append("allowlist-derivation.json does not equal what round 2's transcripts derive")
    for b in bad:
        print(f"FAIL {b}")
    if not bad:
        chosen = pinned()
        print(f"ok: {len(rec['entries'])} candidate entries re-derive from {rec['calls_seen']} pre-probe "
              f"call(s) in {rec['source']['transcripts']} transcript(s); "
              + (f"the pre-registration pins {len(chosen)}, every one of them derived"
                 if chosen else "no pre-registration pins entries yet"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
