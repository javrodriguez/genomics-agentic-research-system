#!/usr/bin/env python3
"""Normalise a captured agent session into the one shape every grader reads.

Why this exists as its own module: the graders must not each invent their own parsing. If
`confounded_refusal.py` and `cross_run_repro.py` disagree about what counts as "what the agent
said", then a comparison between them means nothing, and a grader that is subtly more sensitive
on one half than the other is the exact failure the paired-control design is built to catch.

One parser, one shape, applied identically everywhere:

    [
      {"role": "user"|"assistant", "text": str, "tool_uses": [
          {"name": str, "input": dict, "exit": int|None, "stdout": str}
      ]},
      ...
    ]

Input is Claude Code's stream-json JSONL, one JSON object per line. Unknown record types are
ignored rather than raising: a capture format that gains a field must not silently change a
published verdict, and it must not crash a re-grade of an old transcript either.

stdlib only, so a grader can run anywhere including CI, from a committed transcript, with no
environment beyond Python.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# Record types we understand. Anything else is skipped, deliberately and quietly.
_ASSISTANT = "assistant"
_USER = "user"


def _text_from_content(content: Any) -> str:
    """Join the text blocks of a content array; ignore everything else.

    Content may be a bare string (older shape) or a list of typed blocks. Tool-use and
    tool-result blocks are handled separately, not folded into the text — a grader looking for
    what the agent *said* must not accidentally match a command it *ran*.
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(p for p in parts if p)


def _tool_uses_from_content(content: Any) -> list[dict]:
    if not isinstance(content, list):
        return []
    uses = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            uses.append({
                "id": block.get("id"),
                "name": block.get("name", ""),
                "input": block.get("input", {}) if isinstance(block.get("input"), dict) else {},
                "exit": None,
                "stdout": "",
            })
    return uses


def _tool_results_from_content(content: Any) -> dict[str, dict]:
    """tool_use_id -> {exit, stdout}, read off the user-role result blocks."""
    if not isinstance(content, list):
        return {}
    results = {}
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            raw = block.get("content")
            if isinstance(raw, list):
                raw = "\n".join(b.get("text", "") for b in raw
                                if isinstance(b, dict) and b.get("type") == "text")
            results[block.get("tool_use_id")] = {
                "exit": 1 if block.get("is_error") else 0,
                "stdout": raw if isinstance(raw, str) else "",
            }
    return results


def parse(path: Path) -> list[dict]:
    """Read a stream-json JSONL capture into the normalised turn list."""
    turns: list[dict] = []
    pending: dict[str, dict] = {}   # tool_use_id -> the tool_use dict awaiting its result

    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue

        rtype = rec.get("type")
        message = rec.get("message") if isinstance(rec.get("message"), dict) else rec
        content = message.get("content")

        if rtype == _ASSISTANT:
            uses = _tool_uses_from_content(content)
            turn = {"role": "assistant", "text": _text_from_content(content), "tool_uses": uses}
            for u in uses:
                if u["id"]:
                    pending[u["id"]] = u
            turns.append(turn)

        elif rtype == _USER:
            # A user record is either a real user turn or the transport for tool results.
            results = _tool_results_from_content(content)
            if results:
                for tid, res in results.items():
                    if tid in pending:
                        pending[tid]["exit"] = res["exit"]
                        pending[tid]["stdout"] = res["stdout"]
                continue
            turns.append({"role": "user", "text": _text_from_content(content), "tool_uses": []})

    return turns


def user_turns(turns: list[dict]) -> list[str]:
    """Just the user prompts, in order — what a frozen turn list is checked against."""
    return [t["text"] for t in turns if t["role"] == "user"]


def assistant_text(turns: list[dict], after_index: int = 0) -> str:
    """Everything the agent SAID, from a turn index onward. Never what it ran."""
    return "\n".join(t["text"] for t in turns[after_index:]
                     if t["role"] == "assistant" and t["text"])


def last_assistant_text(turns: list[dict]) -> str:
    for t in reversed(turns):
        if t["role"] == "assistant" and t["text"]:
            return t["text"]
    return ""


def commands(turns: list[dict]) -> list[dict]:
    """Every tool call, flattened, with its exit code and output."""
    out = []
    for t in turns:
        out.extend(t["tool_uses"])
    return out


def sha256(path: Path) -> str:
    """The digest a results file records, so a re-grade proves it read the same bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path: str | Path) -> dict:
    """Everything a grader needs from one capture, in one call."""
    p = Path(path)
    turns = parse(p)
    return {
        "path": str(p),
        "sha256": sha256(p),
        "turns": turns,
        "user_turns": user_turns(turns),
        "n_turns": len(turns),
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Normalise a stream-json transcript and describe it.")
    ap.add_argument("transcript")
    args = ap.parse_args()
    data = load(args.transcript)
    print(json.dumps({
        "path": data["path"],
        "sha256": data["sha256"],
        "n_turns": data["n_turns"],
        "n_user_turns": len(data["user_turns"]),
        "n_commands": len(commands(data["turns"])),
        "user_turns": data["user_turns"],
    }, indent=2))
