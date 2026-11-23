#!/usr/bin/env python3
"""Lane vendor-b25: cut STRUCTURE-ONLY fixtures from committed Gap Study round-4 walks (glitch-26's proof rule).

Run by hand, never by a test: `python3 -I cut_structure.py <walks folder> <out folder>`, where <walks folder> holds
`git archive` copies of the committed walk folders (w-o46 from walk/w-kbm1P3ZO ae6bec92, w-g21 from walk/w-vNjKNXbo
e2c30e0c, w-g31 from walk/w-yQySFDuB). PROVENANCE.json records each source file's sha256.

Kept: every key, the record order, every id (session, message, call, `_response`, orderIds), numbers, booleans, null,
timestamps, tool names, tool statuses, model names, and the pinned sources' enum values. Every other string is
replaced by "synthetic text <n>", n counted from one table shared by every file of one run, so two equal strings stay
equal (a resumed duplicate stays byte-identical to its original; a call's args stay equal to its content functionCall
and its stream parameters) and no string is derived from the content: no model text, prompt, tool output or OD57 byte
survives. The session context turn keeps its pinned wrapper around a synthetic body. A stream's assistant deltas of one
model response are replaced by one delta holding the synthetic text of that response's recorded native text.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

KEEP_KEYS = {"id", "type", "name", "status", "model", "timestamp", "sessionId", "startTime", "lastUpdated", "kind",
             "tool_id", "tool_name", "role", "session_id", "displayName", "thread_id", "turn_id",
             "approval_policy", "approvals_reviewer", "mode", "reasoning_effort", "model_provider_id",
             "collaboration_mode_kind", "severity"}
ENV_OPEN = "<session_context>\nThis is the Gemini CLI. We are setting up the context for our chat.\n"
ENV_CLOSE = "</session_context>"
ENV_ID = hashlib.sha256(b"environment-context").hexdigest()[:32]


class Table:
    def __init__(self):
        self.seen = {}

    def text(self, s: str) -> str:
        if s == "":
            return ""
        if s not in self.seen:
            self.seen[s] = f"synthetic text {len(self.seen) + 1}"
        return self.seen[s]

    def path(self, s: str) -> str:
        return "/work/" + self.text(s).replace(" ", "-")


def skel(value, table: Table, key=None):
    if isinstance(value, dict):
        return {k: skel(v, table, k) for k, v in value.items()}
    if isinstance(value, list):
        if key == "orderIds":
            return list(value)
        return [skel(v, table, key) for v in value]
    if isinstance(value, str):
        if key in KEEP_KEYS:
            return value
        if value.startswith("/"):
            return table.path(value)
        return table.text(value)
    return value


CONTEXT = [{"text": ENV_OPEN + "synthetic context body\n" + ENV_CLOSE}]


def gemini_record(rec: dict, table: Table) -> dict:
    """The context turn keeps its pinned wrapper, as a record and in a resume patch's update of it (every real
    resume rewrites it; each rewrite keeps the wrapper)."""
    out = skel(rec, table)
    if rec.get("id") == ENV_ID and rec.get("type") == "user":
        out["content"] = list(CONTEXT)
    for k, update in enumerate((rec.get("$patch") or {}).get("updates") or []):
        if update.get("id") == ENV_ID and "content" in update:
            out["$patch"]["updates"][k]["content"] = list(CONTEXT)
    return out


def gemini_native(src: Path, dst: Path, table: Table) -> None:
    lines = src.read_text(encoding="utf-8").splitlines()
    out = []
    for n, line in enumerate(lines):
        rec = json.loads(line)
        out.append(json.dumps(skel(rec, table) if n == 0 else gemini_record(rec, table), ensure_ascii=False))
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")


def _normalize(text: str) -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    import gemini_projection
    return gemini_projection.recorder_normalize(text)


def gemini_stream(src: Path, dst: Path, table: Table) -> None:
    recs = [json.loads(x) for x in src.read_text(encoding="utf-8").splitlines() if x.strip()]
    out, pending = [], []

    def flush():
        if not pending:
            return
        full = _normalize("".join(r["content"] for r in pending))
        if full:
            if full not in table.seen:
                raise SystemExit(f"{src}: a stream response is not a native recorded text; refusing to cut it")
            out.append(dict(pending[0], content=table.text(full)))
        pending.clear()
    for r in recs:
        if r["type"] == "message" and r.get("role") == "assistant":
            pending.append(r)
            continue
        flush()
        out.append(skel(r, table))
    flush()
    dst.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")


def codex_records(src: Path, dst: Path, table: Table) -> None:
    recs = [json.loads(x) for x in src.read_text(encoding="utf-8").splitlines()]
    world = [r["payload"] for r in recs if r["type"] == "world_state"]
    settings = [r["payload"] for r in recs if r["type"] == "event_msg"
                and r["payload"].get("type") == "thread_settings_applied"]
    doc = {"world_state": [skel(p, table) for p in world],
           "thread_settings_applied": [skel(p, table) for p in settings[:2]]}
    dst.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main(walks: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    jobs = [("w-g21/session/native-turn-1.jsonl", "w-g21-native-turn-1.jsonl", gemini_native),
            ("w-g21/session/native-turn-2.jsonl", "w-g21-native-turn-2.jsonl", gemini_native),
            ("w-g31/session/native-turn-3.jsonl", "w-g31-native-turn-3.jsonl", gemini_native),
            ("w-g21/turn-1.jsonl", "w-g21-turn-1.jsonl", gemini_stream),
            ("w-g21/turn-2.jsonl", "w-g21-turn-2.jsonl", gemini_stream),
            ("w-o46/session/native-turn-3.jsonl", "w-o46-codex-records.json", codex_records)]
    table, sources = Table(), {}
    for rel, name, fn in jobs:
        src = walks / rel
        sources[name] = {"source": rel, "sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
        fn(src, out / name, table)
    (out / "PROVENANCE.json").write_text(json.dumps({
        "schema": 1, "made_by": "cut_structure.py (lane vendor-b25)",
        "walks": {"w-o46": "walk/w-kbm1P3ZO ae6bec92", "w-g21": "walk/w-vNjKNXbo e2c30e0c",
                  "w-g31": "walk/w-yQySFDuB"},
        "files": sources, "synthetic_strings": len(table.seen)}, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
