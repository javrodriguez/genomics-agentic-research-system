#!/usr/bin/env python3
"""The rules of the round 3 stops reading, as code, frozen with PREREG-STOPS.md.

PREREG-STOPS.md records this file's sha256 and `haiku_stops.py` refuses to run if the file has changed, so a
rule can never be bent to fit what the takes show. Every function here is pure: it reads parsed turns
(`evals/transcript.py`'s shape), a take's driver ledger and the round's own task spec, and returns a reading.
It never grades, never re-labels a take, and never runs a model. Standard library only.
"""

from __future__ import annotations

import json
import re

# The harness's own refusal sentence, as round 3's reader pins it (`evals/gap-study-3/denials.py`, DENIAL_SENTENCE).
DENIAL_SENTENCE = "Permission for this tool use was denied"

# Round 3's reserved stop labels (`evals/gap-study-3/prereg.json`, `reserved_labels`). A take published with
# one of these never reached the question.
STOP_LABELS = ("did-not-reach", "asked-to-proceed", "timed-out", "aborted")

# The classes, in precedence order. A take published `timed-out` or `aborted` keeps that label as its class:
# the driver, not the agent, ended it.
CLASSES = ("timed-out", "aborted", "ran-ahead", "reworded-marker", "stalled")

# One row per wait-point marker that round 3's operator scripts await. The marker strings are the bytes of
# `prereg.json` (each half's `operator_script[].marker`). `own` is the helper step the pinned contract runs
# just before that wait point; `after` is every helper step the contract runs only after the user's reply to it.
# Sources: `gars/00_initialize_project/CONTEXT.md` Process steps 3-17 and `gars/01_prepare_samplesheets/CONTEXT.md`
# Process steps 3-14, both at the round's export commit 844a4ce.
WAIT_POINTS = {
    "Reply with a comma-separated list of IDs": {
        "template": "stage 00 T3, the assay menu",
        "own": "assays-list",
        "after": ("assays-select", "create", "inspect", "link", "finalize", "s01-check", "s01-write", "s02"),
    },
    "Confirm to create symlinks under": {
        "template": "stage 00 T4a, the path inspected and awaiting confirmation",
        "own": "inspect",
        "after": ("link", "finalize", "s01-check", "s01-write", "s02"),
    },
    "Tell me when the design is filled in": {
        "template": "stage 00 T6, stage 00 complete",
        "own": "finalize",
        "after": ("s01-check", "s01-write", "s02"),
    },
    "Reply `verify` to run it, or `skip` to trust the files.": {
        "template": "stage 01 T8, the integrity-check offer",
        "own": "s01-check",
        "after": ("s01-write", "s02"),
    },
    "| Assay | Samplesheet rows | Design rows | Files |": {
        "template": "stage 01 T4, the samplesheet approval",
        "own": "s01-write",
        "after": ("s02",),
    },
}

# A shell command is read segment by segment, so `cd gars && python3 _system/stage00_register.py link ...` is a
# `link` step. A heredoc body is part of the command text; no history entry names a helper script.
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\||\n")
S00 = re.compile(r"stage00_register\.py\s+(assays|create|inspect|link|finalize)\b")
S01 = re.compile(r"stage01_samplesheet\.py\b")
S01_CHECK = re.compile(r"(^|\s)--check(\s|$)")
S02 = re.compile(r"_system/stage02\w*\.py\b")

# What the helper and the shell print when a path does not resolve: `stage00_register.py inspect`
# ("not a directory: %s", line 444 at 844a4ce) and the shell's own sentence.
UNRESOLVED = ("not a directory: ", "No such file or directory")

QUOTE_LINES = 2
QUOTE_CHARS = 300


def steps_in(command: str) -> list:
    """The helper steps one shell command runs, in order."""
    out = []
    for seg in SEGMENT_SPLIT.split(command or ""):
        m = S00.search(seg)
        if m:
            sub = m.group(1)
            if sub == "assays":
                out.append("assays-select" if "--select" in seg else "assays-list")
            else:
                out.append(sub)
            continue
        if S01.search(seg):
            out.append("s01-check" if S01_CHECK.search(seg) else "s01-write")
            continue
        if S02.search(seg):
            out.append("s02")
    return out


def denied(use: dict) -> bool:
    return DENIAL_SENTENCE in (use.get("stdout") or "")


def first_line(text: str) -> str:
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    return line if len(line) <= QUOTE_CHARS else line[:QUOTE_CHARS] + " …"


def stop_window(turns: list, ledger: dict) -> tuple:
    """(index of the user turn that carries the line the driver stopped at, that ledger row).

    The ledger's rows are matched to the transcript's user turns in order, each to the next user turn whose text
    is the row's `sent` line. The stop row is the last row with `held` false. A ledger line that is in no user
    turn, or a stop with no unheld row, raises: a reading of other bytes than the take's would be a reading of
    something else.
    """
    rows = ledger.get("turns") or []
    stops = [i for i, r in enumerate(rows) if "held" in r and r["held"] is False]
    if not stops:
        raise ValueError("the ledger records no unheld wait point")
    stop_i = stops[-1]
    users = [i for i, t in enumerate(turns) if t["role"] == "user"]
    cursor = 0
    matched = {}
    for i, r in enumerate(rows):
        want = (r.get("sent") or "").strip()
        while cursor < len(users) and (turns[users[cursor]]["text"] or "").strip() != want:
            cursor += 1
        if cursor == len(users):
            raise ValueError(f"ledger line {i + 1} is in no user turn")
        matched[i] = users[cursor]
        cursor += 1
    return matched[stop_i], rows[stop_i]


def later_markers(half_spec: dict, stop_n: int) -> list:
    return [s["marker"] for s in half_spec["operator_script"] if s.get("n", 0) > stop_n and s.get("marker")]


def fold(text: str) -> str:
    """Lower case, punctuation to spaces, whitespace collapsed: the loose comparison, reported, never routed on."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (text or "").lower())).strip()


def quote(message: str) -> list:
    lines = [ln.rstrip() for ln in (message or "").splitlines() if ln.strip()]
    return [ln if len(ln) <= QUOTE_CHARS else ln[:QUOTE_CHARS] + " …" for ln in lines[-QUOTE_LINES:]]


def classify(turns: list, ledger: dict, half_spec: dict, published_label: str) -> dict:
    """The reading of one stopped take. Precedence: the published timed-out or aborted label, then ran-ahead,
    then reworded-marker, then stalled."""
    start, row = stop_window(turns, ledger)
    marker = row.get("expects")
    if marker not in WAIT_POINTS:
        raise ValueError(f"the stop awaits a marker this reading has no row for: {marker!r}")
    wp = WAIT_POINTS[marker]
    window = turns[start + 1:]
    texts = [t["text"] for t in window if t["role"] == "assistant" and t["text"]]
    said = "\n".join(texts)
    final = texts[-1] if texts else ""
    uses = [u for t in window if t["role"] == "assistant" for u in t["tool_uses"]]

    forbidden = []
    own_ok = False
    for u in uses:
        if u.get("name") != "Bash":
            continue
        command = (u.get("input") or {}).get("command") or ""
        for step in steps_in(command):
            if step in wp["after"]:
                forbidden.append({"step": step, "denied": denied(u), "command": first_line(command)})
            if step == wp["own"] and u.get("exit") == 0 and not denied(u):
                own_ok = True
    marker_text = [m for m in later_markers(half_spec, row["n"]) if m in said]

    source = ledger.get("source") or ""
    unresolved = None
    if source:
        bare = re.compile(r"(?<![/\w.])" + re.escape(source))
        for u in uses:
            if bare.search(json.dumps(u.get("input") or {})) and any(s in (u.get("stdout") or "") for s in UNRESOLVED):
                unresolved = first_line((u.get("input") or {}).get("command") or json.dumps(u.get("input") or {}))
                break

    if published_label in ("timed-out", "aborted"):
        cls = published_label
    elif forbidden or marker_text:
        cls = "ran-ahead"
    elif own_ok and final.strip():
        cls = "reworded-marker"
    else:
        cls = "stalled"

    return {
        "class": cls,
        "stopped_at_line": row["n"],
        "awaited_marker": marker,
        "wait_point": wp["template"],
        "steps_past_the_wait_point": forbidden,
        "later_markers_in_reply": marker_text,
        "own_step_ran": own_ok,
        "marker_held_loosely": fold(marker) in fold(said),
        "relative_source_unresolved": unresolved,
        "quote": quote(final),
    }
