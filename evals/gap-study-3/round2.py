#!/usr/bin/env python3
"""The one door to round 2's committed record. Nothing else in round 3 opens round 2's files.

    python3 evals/gap-study-3/round2.py --cells        every cell round 2 published for round 3's three tasks
    python3 evals/gap-study-3/round2.py --commands     every Bash command a route used BEFORE its probe turn
    python3 evals/gap-study-3/round2.py --probe-turns  the probe operator turn of each task and half

WHY A DOOR RATHER THAN A PATH IN EACH FILE. Round 3 reads round 2 for three different things -- the
command forms the allowlist is derived from, the counts that print beside round 3's, and the evidence each
prediction names -- and each of those would otherwise open `../gap-study-2/` for itself. Three readers of
one folder drift, and the one that drifts quietly is the one that decides what gets published. So there is
one reader, and it is read-only by construction: it opens files under round 2's folder and writes nothing,
anywhere.

ROUND 2 IS DATA, AND ITS BYTES ARE PINNED. copy_manifest.py holds `evals/gap-study-2` unchanged since
round 2's done commit, in the working tree as well as in history, so the folder this file reads is the
folder round 3 copied its instrument from. A reading taken here cannot quietly move.

WHAT "BEFORE THE PROBE" MEANS. A take's operator script is a fixed list of turns, and one of them is the
probe -- the turn that asks the question being measured. `--commands` collects the agent's Bash calls made
before the probe turn was sent, because those are the commands the ROUTE uses: getting to the question.
What the agent does after the probe is the thing under measurement and must never shape the conditions it
is measured under.

No model, no network, stdlib only. Read-only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "evals"))

import study  # noqa: E402
import transcript as tx  # noqa: E402

ROUND2 = REPO / study.ROUND1_REL          # the prior round, named by the binding
TRANSCRIPTS = ROUND2 / "transcripts"
FROZEN = ROUND2 / "prereg.json"
RESULTS = ROUND2 / "results"

# The three tasks round 2 published as covered by no model. Round 3 measures these and no others.
TASKS = ("scope-read", "template-adherence", "confounded-design")
HALVES = ("positive", "control")


FROZEN_REL = f"{study.ROUND1_REL}/prereg.json"


def frozen() -> dict:
    """Round 2's FROZEN file, never its draft. A design that could still change is not a record."""
    if not FROZEN.is_file():
        raise SystemExit(f"{FROZEN.relative_to(REPO)} does not exist: round 2's frozen file is the record "
                         f"round 3 reads, and there is no substitute for it.")
    return json.loads(FROZEN.read_text())


def frozen_at(commit: str) -> dict:
    """Round 2's frozen file AS OF a commit, read with `git show` rather than from the working tree.

    The draft builder carries round 2's rules forward, and a rule carried from a working-tree file is a
    rule that could have been edited between the carrying and the check. This read is bound to a commit,
    so what it returns is what that commit holds and nothing else. The door owns it for the same reason
    it owns every other read of round 2: one reader, or the readers drift.
    """
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{FROZEN_REL}"], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"git show {commit[:12]}:{FROZEN_REL} failed: {r.stderr.decode().strip()}")
    return json.loads(r.stdout)


def probe_turns() -> dict[tuple[str, str], int]:
    out = {}
    for t in frozen()["tasks"]:
        if t["id"] not in TASKS:
            continue
        for half in HALVES:
            if half in t:
                out[(t["id"], half)] = int(t[half]["probe_operator_turn"])
    return out


def transcripts() -> list[Path]:
    """Every committed graded transcript of round 3's three tasks, in a fixed order."""
    return sorted(p for p in TRANSCRIPTS.glob("*/*/*/*/transcript.jsonl") if p.parts[-5] in TASKS)


def _line_of(path: Path, needle: str) -> int:
    """The 1-indexed line of the transcript that carries this command, so a reader can go and look.

    Matched on the command's own JSON encoding, which is how it appears in the record. A command that
    spans several lines of shell -- a heredoc -- is matched on its first line, because that is the part
    a reader searches for; a command that appears on no line at all is reported as line 0 rather than
    guessed at, and the battery fails on a 0.
    """
    lines = path.read_text(errors="replace").splitlines()
    for probe in (needle, needle.split("\n", 1)[0]):
        encoded = json.dumps(probe)[1:-1]
        if not encoded:
            continue
        for i, line in enumerate(lines, start=1):
            if encoded in line:
                return i
    return 0


def transcript_rel(row: dict) -> str:
    """A row's transcript path, rebuilt from its fields.

    WHY THE FIELDS AND NOT THE PATH. A committed record carrying
    `.../claude-opus-5/1/transcript.jsonl` carries the character sequence `5/1`, and the copied language
    linter's ratio-slash rule reads that as a rate -- the same false positive round 2 met on its neutral
    project names. That linter is pinned byte-identical by the goal file and is not this study's to
    soften, and 140 per-line excusals would be a way of switching a pattern off one line at a time. So
    the record carries the four fields and the path is built here, where no committed line holds it.
    """
    return f"{study.ROUND1_REL}/transcripts/{row['task']}/{row['half']}/{row['model']}/{row['take']}/transcript.jsonl"


def pre_probe_commands() -> list[dict]:
    """Every Bash command the agent ran before the probe turn, with where it came from.

    One row per call, never deduplicated here: how often a form was used is evidence, and a reader that
    deduplicates before counting has thrown the evidence away.
    """
    probes = probe_turns()
    rows: list[dict] = []
    for tr in transcripts():
        task, half, model, take = tr.parts[-5], tr.parts[-4], tr.parts[-3], tr.parts[-2]
        probe = probes.get((task, half))
        if probe is None:
            continue
        user_turns_seen = 0
        for turn in tx.parse(tr):
            if turn["role"] == "user":
                user_turns_seen += 1
                continue
            if user_turns_seen >= probe:
                break
            for tu in turn.get("tool_uses", []):
                if tu.get("name") != "Bash":
                    continue
                cmd = ((tu.get("input") or {}).get("command") or "").strip()
                if not cmd:
                    continue
                rows.append({"task": task, "half": half, "model": model, "take": take,
                             "line": _line_of(tr, cmd),
                             "operator_turn_before": user_turns_seen + 1, "command": cmd})
    return rows


MODE_RECORD = re.compile(r'"permissionMode":\s*"([A-Za-z]+)"')


def cell_modes() -> dict[str, dict[str, dict[str, str]]]:
    """The permission mode each of round 2's cells ACTUALLY recorded, read from its own transcripts.

    `default` if any take of the cell records default, else `auto` if any records auto, else `unrecorded`.
    The precedence is the pre-study's: a session recording `default` anywhere ran with no approval surface.

    WHY THIS IS DERIVED AND NOT CITED. Round 2 passed `--permission-mode auto` to all three models and
    recorded that constant in every ledger. Whether a cell's session actually ran in that mode is a fact
    about the transcripts, and round 3 leans on it for two things -- which of round 2's counts may inform a
    prediction, and which must be published as a recorded harness condition. A study that took that from
    another study's prose would be repeating a claim; this reads the bytes it is a claim about.
    """
    out: dict[str, dict[str, dict[str, str]]] = {}
    for tr in transcripts():
        task, half, model = tr.parts[-5], tr.parts[-4], tr.parts[-3]
        modes = set(MODE_RECORD.findall(tr.read_text(errors="replace")))
        seen = out.setdefault(task, {}).setdefault(model, {})
        mode = "default" if "default" in modes else "auto" if "auto" in modes else "unrecorded"
        prior = seen.get(half)
        # default wins across the cell's takes, then auto, then unrecorded
        rank = {"default": 0, "auto": 1, "unrecorded": 2}
        if prior is None or rank[mode] < rank[prior]:
            seen[half] = mode
    return out


def cells() -> dict:
    """Round 2's published count per (task, half, model) for round 3's three tasks, read from its own
    committed results files and never restated by hand."""
    out: dict[str, dict] = {}
    for task in TASKS:
        f = RESULTS / f"{task}.json"
        if not f.is_file():
            raise SystemExit(f"{f.relative_to(REPO)} does not exist: round 2's published counts are read "
                             f"from its own results files.")
        out[task] = json.loads(f.read_text())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--cells", action="store_true")
    g.add_argument("--modes", action="store_true")
    g.add_argument("--commands", action="store_true")
    g.add_argument("--probe-turns", action="store_true")
    args = ap.parse_args()
    if args.probe_turns:
        for (task, half), n in sorted(probe_turns().items()):
            print(f"{task:22} {half:9} probe operator turn {n}")
        return 0
    if args.modes:
        for task, models in sorted(cell_modes().items()):
            for model, halves in sorted(models.items()):
                for half, mode in sorted(halves.items()):
                    print(f"{task:22} {model:30} {half:9} recorded {mode}")
        return 0
    if args.cells:
        print(json.dumps(cells(), indent=2))
        return 0
    rows = pre_probe_commands()
    print(json.dumps(rows, indent=2))
    print(f"\n{len(rows)} pre-probe Bash call(s) across {len(transcripts())} committed transcript(s)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
