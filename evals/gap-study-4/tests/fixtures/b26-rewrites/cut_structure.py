#!/usr/bin/env python3
"""Lane vendor-b26: cut STRUCTURE-ONLY fixtures of the Gemini history-rewrite roads from committed Gap Study round-4
walks (glitch-26's proof rule). It extends lane vendor-b25's cutter (../b25-real-shapes/cut_structure.py), whose
Table, kept keys and stream rule it reuses unchanged.

Run by hand, never by a test: `python3 -I cut_structure.py <walks folder> <out folder>`, where <walks folder> holds
`git archive` copies of the committed walk folders (w-g14 from walk/w-GDVAbBBf ef903feb, w-g32 from walk/w-j1pQgLS1
129ff0fe, w-g47 from walk/w-XsJlNcjC 1acd87cd). PROVENANCE.json records each source file's sha256.

Four rules on top of lane vendor-b25's, each needed so the re-record image check survives the cut:
  1. every string equal to a session-context text (any version of the context turn, as a record or a patch update)
     becomes B25's synthetic context block, wherever it sits (the first re-recorded user message carries it as its
     first part);
  2. a masked tool output keeps the pinned wrapper (chunk-NR7L3FXV.js:344871-344877) around a synthetic preview and a
     synthetic path;
  3. a string's leading "/" (B25's path rule) or "?" is kept, so the ignored-prompt predicate (:286096-286098) holds;
  4. a loop-recovery message keeps the pinned template (:348603) around a synthetic detail.
Every other string is "synthetic text <n>" from one table shared by every file of one run, so equal strings stay equal
(a re-recorded copy stays equal to its original) and no model text, prompt, tool output or OD57 byte survives. Each
snapshot is cut line by line, so a snapshot that was a byte prefix of the next one stays one.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

_B25 = Path(__file__).resolve().parent.parent / "b25-real-shapes" / "cut_structure.py"
_spec = importlib.util.spec_from_file_location("b25_cut_structure", _B25)
b25 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b25)

MASK_OPEN = "<tool_output_masked>\n"
MASK_MID = "\n\nOutput too large. Full output available at: "
MASK_CLOSE = "\n</tool_output_masked>"
LOOP_OPEN = "System: Potential loop detected. Details: "
LOOP_CLOSE = (". Please take a step back and confirm you're making forward progress. If not, take a step back, analyze "
              "your previous actions and rethink how you're approaching the problem. Avoid repeating the same tool calls "
              "or responses without new results.")
CONTEXT_TEXT = b25.CONTEXT[0]["text"]


class Table(b25.Table):
    def __init__(self, contexts):
        super().__init__()
        self.contexts = contexts

    def text(self, s: str) -> str:
        if s in self.contexts:
            return CONTEXT_TEXT
        if s.startswith(MASK_OPEN) and s.endswith(MASK_CLOSE) and MASK_MID in s:
            body = s[len(MASK_OPEN):-len(MASK_CLOSE)]
            preview, _, path = body.rpartition(MASK_MID)
            return MASK_OPEN + super().text(preview) + MASK_MID + self.path(path) + MASK_CLOSE
        if s.startswith(LOOP_OPEN) and s.endswith(LOOP_CLOSE) and len(s) > len(LOOP_OPEN) + len(LOOP_CLOSE):
            return LOOP_OPEN + super().text(s[len(LOOP_OPEN):-len(LOOP_CLOSE)]) + LOOP_CLOSE
        if s.startswith("?"):
            return "?" + super().text(s[1:])
        return super().text(s)


def context_texts(paths) -> set:
    """Every text the context turn ever held, as a record or as a patch update of its id."""
    out = set()
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            items = [rec] if rec.get("id") == b25.ENV_ID else []
            items += [u for u in (rec.get("$patch") or {}).get("updates") or [] if u.get("id") == b25.ENV_ID]
            for item in items:
                for part in item.get("content") or []:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        out.add(part["text"])
    return out


def skel(value, table, key=None):
    """B25's skel, but every string goes through this lane's table (B25's own maps a leading "/" to a path first)."""
    if isinstance(value, dict):
        return {k: skel(v, table, k) for k, v in value.items()}
    if isinstance(value, list):
        if key == "orderIds" or key == "removeIds":
            return list(value)
        return [skel(v, table, key) for v in value]
    if isinstance(value, str):
        if key in b25.KEEP_KEYS:
            return value
        if value.startswith("/"):
            return table.path(value)
        return table.text(value)
    return value


def gemini_native(src: Path, dst: Path, table) -> None:
    out = []
    for n, line in enumerate(src.read_text(encoding="utf-8").splitlines()):
        if line.strip():
            out.append(json.dumps(skel(json.loads(line), table), ensure_ascii=False))
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")


def gemini_stream(src: Path, dst: Path, table) -> None:
    b25.skel = skel                     # B25's stream rule, with this lane's skel for every non-delta record
    b25.gemini_stream(src, dst, table)


JOBS = [
    ("w-g47/session/native-turn-1.jsonl", "w-g47-native-turn-1.jsonl", gemini_native),
    ("w-g47/session/native-turn-2.jsonl", "w-g47-native-turn-2.jsonl", gemini_native),
    ("w-g14/session/native-turn-3.jsonl", "w-g14-native-turn-3.jsonl", gemini_native),
    ("w-g14/session/native-turn-4.jsonl", "w-g14-native-turn-4.jsonl", gemini_native),
    ("w-g32/session/native-turn-2.jsonl", "w-g32-native-turn-2.jsonl", gemini_native),
    ("w-g32/session/native-turn-3.jsonl", "w-g32-native-turn-3.jsonl", gemini_native),
] + [(f"w-g47/turn-{n}.jsonl", f"w-g47-turn-{n}.jsonl", gemini_stream) for n in (1, 2)] \
  + [(f"w-g14/turn-{n}.jsonl", f"w-g14-turn-{n}.jsonl", gemini_stream) for n in (1, 2, 3, 4)] \
  + [(f"w-g32/turn-{n}.jsonl", f"w-g32-turn-{n}.jsonl", gemini_stream) for n in (1, 2, 3)]


def main(walks: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    table = Table(context_texts([walks / rel for rel, _, fn in JOBS if fn is gemini_native]))
    sources = {}
    for rel, name, fn in JOBS:
        src = walks / rel
        sources[name] = {"source": rel, "sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
        fn(src, out / name, table)
    (out / "PROVENANCE.json").write_text(json.dumps({
        "schema": 1, "made_by": "cut_structure.py (lane vendor-b26)",
        "walks": {"w-g14": "walk/w-GDVAbBBf ef903feb", "w-g32": "walk/w-j1pQgLS1 129ff0fe",
                  "w-g47": "walk/w-XsJlNcjC 1acd87cd"},
        "files": sources, "synthetic_strings": len(table.seen)}, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
