#!/usr/bin/env python3
"""Stage 1b (Javier's "1 add", Fri 20 Nov 2026 22:01): the figures of the section 9 sentence on arm O's connector tools,
recounted read-only with git from the records at the verified head, -> build/facts_connectors.json.
Run from a clone of the repository that holds that head (a full clone does); it reads the clone's own git.

check_trace.py merges this file with build/facts.json and build/facts_reading.json (keys must be disjoint), so each
figure of that sentence is a ("fact", key, expected) source checked like every other fact.
Nothing here writes to a repository: only `git ls-tree`, `git show`, `git cat-file --batch` and `git grep` at H.

Usage: connector_facts.py [--git-dir <repo>] [--print]   (--git-dir defaults to this clone)   (--print writes nothing and prints the facts)
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import re
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent              # docs/gap-study-4/report-build (build/)
WORKTREE = str(ROOT.parent.parent.parent)           # the clone itself: the records commit H is in its history
H = "1ded8e9a2ada68ecf3ececc1c6c33dd0634f7ca3"
S = "evals/gap-study-4/"
T = S + "takes/"
CACHE = "cache/codex_apps_tools/"
TOOL = "mcp__codex_apps__"
CONN = re.compile(r"codex_apps|gmail|google_drive|google_calendar|calendar_|contacts_|chatgpt_|sites_", re.I)

ap = argparse.ArgumentParser()
ap.add_argument("--git-dir", default=WORKTREE)
ap.add_argument("--print", action="store_true")
ARGS = ap.parse_args()


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", ARGS.git_dir, *a], capture_output=True, text=True, check=True).stdout


def blobs(paths: list[str]) -> dict[str, str | None]:
    out = subprocess.run(["git", "-C", ARGS.git_dir, "cat-file", "--batch"], capture_output=True, check=True,
                         input="".join(f"{H}:{p}\n" for p in paths).encode()).stdout
    res, i = {}, 0
    for p in paths:
        nl = out.index(b"\n", i)
        hdr = out[i:nl].split()
        if hdr[-1] == b"missing":
            res[p], i = None, nl + 1
            continue
        n = int(hdr[2])
        res[p], i = out[nl + 1:nl + 1 + n].decode(), nl + 1 + n + 1
    return res


def day(t: float, tz) -> str:
    d = datetime.datetime.fromtimestamp(t, tz)
    return f"{d.day} {d:%b %Y}"


outcomes = json.loads(git("show", f"{H}:{S}outcomes.json"))
base = [f"{T}{o['slot']}/{o['attempt']}/" for o in outcomes]
ledgers = blobs([b + "driver-ledger.json" for b in base])
post = blobs([b + "postflight.json" for b in base])
launch = blobs([b + "turn-1.jsonl.launch.json" for b in base])

arm_o, graded, with_cache, graded_with_cache, names, starts = [], [], 0, 0, set(), []
for o, b in zip(outcomes, base):
    if json.loads(ledgers[b + "driver-ledger.json"])["arm"] != "O":
        continue
    arm_o.append(b)
    listing = [ln.strip().strip('",') for ln in (post[b + "postflight.json"] or "").split("\n") if CACHE in ln]
    names.update(n for n in listing if n != CACHE.rstrip("/"))
    has = bool(listing)
    with_cache += has
    if o["state"] == "graded":
        graded.append(b)
        graded_with_cache += has
        starts.append(json.loads(launch[b + "turn-1.jsonl.launch.json"])["started_at"])

utc = (day(min(starts), datetime.timezone.utc), day(max(starts), datetime.timezone.utc))
ny = (day(min(starts), ZoneInfo("America/New_York")), day(max(starts), ZoneInfo("America/New_York")))
assert utc == ny, (utc, ny)

hits = [ln.split(":", 1)[1] for ln in git("grep", "-l", "-e", TOOL, H, "--", S + "takes", S + "rehearsals").split("\n") if ln]
take_files = [p for p in hits if p.startswith(T)]
takes = sorted({"/".join(p.split("/")[:5]) + "/" for p in take_files})   # takes/<slot>/<attempt>/
reh_files = [p for p in hits if p.startswith(S + "rehearsals/")]
rehearsals = sorted({p.split("/")[3] for p in reh_files})
tool_names = sorted(set(re.findall(TOOL + r"[A-Za-z0-9_]+", git("grep", "-h", "-o", "-e", TOOL + "[A-Za-z0-9_]*", H, "--",
                                                                 S + "takes", S + "rehearsals"))))

tree = git("ls-tree", "-r", "--name-only", H, "--", S + "takes", S + "rehearsals").split("\n")
session_files = [p for p in tree if p.endswith(".jsonl") and "/session/" in p
                 and (any(p.startswith(b) for b in arm_o) or p.startswith(S + "rehearsals/w-o"))]
calls, naming = collections.Counter(), 0
for p, body in blobs(session_files).items():
    for line in (body or "").split("\n"):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        pl = rec.get("payload") if isinstance(rec, dict) else None
        if isinstance(pl, dict) and pl.get("type") in ("function_call", "custom_tool_call", "mcp_tool_call", "tool_search",
                                                        "local_shell_call"):
            calls[f"{pl['type']} {pl.get('name')}"] += 1
            naming += bool(CONN.search(json.dumps({k: v for k, v in pl.items() if k != "output"})))

short = [n[len(TOOL):] for n in tool_names]
facts = {
    "o_connector_cache": {"arm_o_attempts": len(arm_o), "attempts_with_cache": with_cache, "graded": len(graded),
                          "graded_with_cache": graded_with_cache, "cache_file_names": len(names)},
    "o_connector_run_days": {"first": utc[0], "last": utc[1]},
    "o_connector_listings": {"files": len(hits), "take_files": len(take_files), "takes": len(takes),
                             "takes_graded_arm_o": sum(t in graded for t in takes), "rehearsal_files": len(reh_files),
                             "rehearsals": rehearsals},
    "o_connector_tools": {"names": len(short), "gmail_send": "gmail_send_email" in short,
                          "gmail_forward": "gmail_forward_emails" in short, "drive_delete": "google_drive_delete_file" in short,
                          "drive_share": "google_drive_share_file" in short,
                          "calendar": any(n.startswith("google_calendar_") for n in short),
                          "contacts": any(n.startswith("google_contacts_") for n in short),
                          "chatgpt_workspace": any(n.startswith("chatgpt_space_") for n in short),
                          "sites": any(n.startswith("sites_") for n in short)},
    "o_connector_calls": {"session_files": len(session_files), "exec": calls["custom_tool_call exec"],
                          "function_call": sum(v for k, v in calls.items() if k.startswith("function_call ")),
                          "kinds": sorted(calls), "naming_a_connector": naming},
}
text = json.dumps(facts, indent=1, ensure_ascii=False) + "\n"
if ARGS.print:
    print(text, end="")
else:
    (ROOT / "build" / "facts_connectors.json").write_text(text)
    print(f"build/facts_connectors.json written from {ARGS.git_dir} at {H[:12]}")
