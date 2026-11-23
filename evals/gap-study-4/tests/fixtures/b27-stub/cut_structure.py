#!/usr/bin/env python3
"""Lane vendor-b27 (glitch-f1's ruling 3, 21 Oct 2026): cut STRUCTURE-ONLY fixtures from the stub-model probe's
records. It extends lane vendor-b26's cutter (../b26-rewrites/cut_structure.py, which hard-codes its JOBS and is not
edited), whose Table, skel, native and stream rules it reuses unchanged.

Run by hand, never by a test: `python3 -I cut_structure.py <probe folder> <scenario> <out folder>`, where <probe
folder> is a fetched stub-probe-<id> folder (walk_launch fetch-probe) and <scenario> one of its scenario folders.
It cuts every session/native-turn-<n>.jsonl and turn-<n>.jsonl of that scenario into <out>/<scenario>-native-turn-
<n>.jsonl and <out>/<scenario>-turn-<n>.jsonl and writes PROVENANCE.json (each source file's sha256, the probe's
manifest sha256, the synthetic string count).

Two rules on top of lane vendor-b26's, so the readers' truncation and compression checks survive the cut:
  1. a content-truncated tool output keeps formatTruncatedToolOutput's wrapper (chunk-NR7L3FXV.js:254171-254185),
     its numbers and its path's place, around a synthetic head, a synthetic tail and a synthetic path;
  2. a chat-compression summary keeps its <state_snapshot> wrapper around a synthetic body, and the CLI's fixed
     acknowledgement "Got it. Thanks for the additional context!" (:337261) is kept verbatim.
Every other string goes through lane vendor-b26's table (so equal strings stay equal, a re-recorded copy stays equal to
its original, and each snapshot is cut line by line, so a snapshot that was a byte prefix of the next stays one). The
probe's records hold no study prompt, model text, tool output or credential to begin with (the stub's words, the
CLI's own strings and synthetic files only); the cut form exists for uniformity with the B25 and B26 fixtures.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

_B26 = Path(__file__).resolve().parent.parent / "b26-rewrites" / "cut_structure.py"
_spec = importlib.util.spec_from_file_location("b26_cut_structure", _B26)
b26 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b26)

ACKNOWLEDGEMENT = "Got it. Thanks for the additional context!"                                       # :337261
SNAPSHOT_OPEN, SNAPSHOT_CLOSE = "<state_snapshot>", "</state_snapshot>"
# formatTruncatedToolOutput (:254171-254185): the header line, the head, the omitted count, the tail
TRUNCATED = re.compile(r"Output too large\. Showing first ([0-9][0-9,]*) and last ([0-9][0-9,]*) characters\. "
                       r"For full output see: ([^\n]*)\n(.*)\n\n\.\.\. \[([0-9][0-9,]*) characters omitted\] \.\.\.\n\n(.*)",
                       re.DOTALL)


class Table(b26.Table):
    def text(self, s: str) -> str:
        if s == ACKNOWLEDGEMENT:
            return s
        m = TRUNCATED.fullmatch(s)
        if m:
            first, last, path, head, omitted, tail = m.groups()
            return (f"Output too large. Showing first {first} and last {last} characters. For full output see: "
                    f"{self.path(path)}\n{super().text(head)}\n\n... [{omitted} characters omitted] ...\n\n"
                    f"{super().text(tail)}")
        if s.startswith(SNAPSHOT_OPEN) and s.endswith(SNAPSHOT_CLOSE) and len(s) >= len(SNAPSHOT_OPEN + SNAPSHOT_CLOSE):
            return SNAPSHOT_OPEN + super().text(s[len(SNAPSHOT_OPEN):-len(SNAPSHOT_CLOSE)]) + SNAPSHOT_CLOSE
        return super().text(s)


def jobs(scenario_dir: Path, scenario: str) -> list:
    """(source, out name, cutter) for every snapshot and stream of one scenario folder, in turn order."""
    out = []
    for p in sorted((scenario_dir / "session").glob("native-turn-*.jsonl"), key=lambda p: int(p.stem.rsplit("-", 1)[1])):
        out.append((p, f"{scenario}-{p.name}", b26.gemini_native))
    for p in sorted(scenario_dir.glob("turn-*.jsonl"), key=lambda p: int(p.stem.rsplit("-", 1)[1])):
        out.append((p, f"{scenario}-{p.name}", b26.gemini_stream))
    return out


def main(probe: Path, scenario: str, out: Path) -> dict:
    src_dir = probe / scenario
    todo = jobs(src_dir, scenario)
    if not todo:
        raise SystemExit(f"{src_dir} holds no snapshot or stream")
    out.mkdir(parents=True, exist_ok=True)
    table = Table(b26.context_texts([p for p, _n, fn in todo if fn is b26.gemini_native]))
    sources = {}
    for src, name, fn in todo:
        sources[name] = {"source": str(src.relative_to(probe)), "sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
        fn(src, out / name, table)
    manifest = probe / "manifest.json"
    prov = {"schema": 1, "made_by": "cut_structure.py (lane vendor-b27)", "probe": probe.name, "scenario": scenario,
            "probe_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else None,
            "files": sources, "synthetic_strings": len(table.seen)}
    (out / "PROVENANCE.json").write_text(json.dumps(prov, indent=1) + "\n", encoding="utf-8")
    return prov


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]))
