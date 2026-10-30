#!/usr/bin/env python3
"""Pre-freeze review 2, MAJOR 1, step 5 (glitch-45's ruling (a), 29 Oct 2026): a stream-only API error.

The facts the check rests on (read, not run): Claude Code 2.1.296 writes an API error into its session file as an
assistant record {isApiErrorMessage: true, message.model "<synthetic>", error, apiErrorStatus, its words in text
blocks}, seen in three real 2.1.296 records on the Mac (the L-A1 report cites them by path and line); the stream's
API-error record is the same message (claude_code_adapter.read_stream). So after the first turn every stream API-error
record of the main thread must have a session-file API-error record with the same words in the same turn, every
sub-agent stream API-error record one in its sub-agent file, and a stream result record that is an error a session-file
API-error record in its turn; otherwise [transcript-mismatch], aborted.

  E.inject     the reviewer's one-line injection into a copy of rehearsals/w001's turn stream: transcript_content_problems
               was [] before the fold, is transcript-mismatch after, and routes aborted
  E.both       the same line also written into the session file (the two-record road the draft names) passes
  E.result     a forged error result line with no session-file API-error record in its turn is transcript-mismatch
  E.walks      every committed claude-code walk still reads clean (no walk carries an API error)
  E.vendor     drive.vendor_nested_problems no longer refuses a vendor take for a bare store-variable assignment (the
               checker's vendor road grades it with its agent event); a foreign session still refuses

Synthetic copies only; the committed walk is never written.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(HERE))

import check_take as ct  # noqa: E402
import drive  # noqa: E402
import test_routing as tr  # noqa: E402
import routing  # noqa: E402
from graders import labels4  # noqa: E402

W001 = STUDY / "rehearsals" / "w001"
WORDS = "API Error: rate limit reached"


def copy_w001() -> Path:
    d = Path(tempfile.mkdtemp()) / "w001"
    shutil.copytree(W001, d, ignore=shutil.ignore_patterns("evidence"))
    return d / "transcript.jsonl"


def api_line(sid: str, **over) -> str:
    rec = {"type": "assistant", "message": {"id": "msg_x", "type": "message", "role": "assistant", "model": "<synthetic>",
                                            "content": [{"type": "text", "text": WORDS}]},
           "parent_tool_use_id": None, "session_id": sid, "is_api_error_message": True, "error": "rate_limit"}
    rec.update(over)
    return json.dumps(rec)


def inject_stream(path: Path, line: str, turn: int = 1) -> None:
    s = path.parent / f"turn-{turn}.jsonl"
    lines = s.read_text().split("\n")
    at = max(i for i, x in enumerate(lines) if '"type":"result"' in x or '"type": "result"' in x)
    lines.insert(at, line)
    s.write_text("\n".join(lines))


def session_line(path: Path) -> str:
    recs = [json.loads(x) for x in path.read_text().split("\n") if x.strip()]
    sid = next(r.get("sessionId") for r in recs if r.get("sessionId"))
    return json.dumps({"type": "assistant", "isApiErrorMessage": True, "error": "rate_limit", "apiErrorStatus": 429,
                       "isSidechain": False, "sessionId": sid, "uuid": "u-x", "parentUuid": None,
                       "message": {"id": "msg_x", "role": "assistant", "model": "<synthetic>",
                                   "content": [{"type": "text", "text": WORDS}]}})


def sid_of(path: Path) -> str:
    first = json.loads((path.parent / "turn-1.jsonl").read_text().split("\n")[0])
    return first["session_id"]


def route_ids(ids):
    rec = tr.baseline(labels4.AFTER_FIRST_TURN)
    rec["checker_reasons"] = sorted(set(ids))
    return routing.route(rec, tr.test_table())["route"]


class StreamOnlyApiError(unittest.TestCase):
    def test_e_inject(self):
        path = copy_w001()
        self.assertEqual(ct.transcript_content_problems(path), [])
        inject_stream(path, api_line(sid_of(path)))
        got = ct.transcript_content_problems(path)
        self.assertEqual(set(ct.reason_ids(got)), {ct.TRANSCRIPT_MISMATCH}, got)
        self.assertEqual(route_ids(ct.reason_ids(got)), labels4.ABORTED)

    def test_e_both(self):
        path = copy_w001()
        inject_stream(path, api_line(sid_of(path)))
        lines = path.read_text().rstrip("\n").split("\n")
        lines.append(session_line(path))                         # the last turn is turn 1's or later: put it in turn 1
        ops = [i for i, x in enumerate(lines) if ct._cca._is_operator_line(json.loads(x))]
        lines.insert(ops[1] if len(ops) > 1 else len(lines) - 1, lines.pop())
        path.write_text("\n".join(lines) + "\n")
        self.assertEqual(ct.transcript_content_problems(path), [])

    def test_e_result(self):
        path = copy_w001()
        res = json.dumps({"type": "result", "subtype": "success", "is_error": True, "result": WORDS,
                          "session_id": sid_of(path), "api_error_status": 429})
        s = path.parent / "turn-1.jsonl"
        s.write_text(s.read_text().rstrip("\n") + "\n" + res + "\n")
        got = ct.transcript_content_problems(path)
        self.assertIn(ct.TRANSCRIPT_MISMATCH, ct.reason_ids(got), got)

    def test_e_walks(self):
        reg = json.loads((STUDY / "rehearsals" / "register.json").read_text())
        n = 0
        for w in sorted(p.parent for p in (STUDY / "rehearsals").glob("w[0-9]*/transcript.jsonl")):
            if not (w / "turn-1.jsonl").is_file() or json.loads((w / "turn-1.jsonl").read_text().split("\n")[0]).get(
                    "subtype") != "init":
                continue
            got = ct.api_error_record_problems(w / "transcript.jsonl")
            self.assertEqual(got, [], w.name)
            n += 1
        self.assertGreater(n, 100)
        self.assertTrue(reg)


class VendorRoad(unittest.TestCase):
    def test_e_vendor(self):
        own = "sessions/2026/10/16/rollout-2026-10-16T10-00-00-t1.jsonl"
        listing = [{"at": "post-1", "entries": [["sessions/2026", "dir"], ["sessions/2026/10", "dir"],
                                               ["sessions/2026/10/16", "dir"], [own, "file"]]}]
        mine = {"at": "post-1", "files": [[f"/opt/cfg/{own}", "codex", "t1"]], "unreadable": [], "escapes": [],
                "mounts": ["/opt/cfg", "/run/t"], "scanned": 4, "truncated": False,
                "expected": ct.sweep_expected("/run/t")}
        self.assertEqual(drive.vendor_nested_problems(listing, [mine], "codex", own, ["HOME=/tmp git status"], [],
                                                      "/run/t"), [])
        self.assertEqual(ct.reason_ids(ct.command_problems(["HOME=/tmp git status"], "codex")),
                         [ct.STORE_VARIABLE_ASSIGNED])               # the checker's vendor road still records it
        foreign = dict(mine, files=mine["files"] + [["/tmp/r.jsonl", "codex", "t2"]])
        self.assertTrue(drive.vendor_nested_problems(listing, [foreign], "codex", own, ["HOME=/tmp git status"], [],
                                                     "/run/t"))
        self.assertTrue(drive.vendor_nested_problems(listing, [mine], "codex", own, ["codex exec --ephemeral x"], [],
                                                     "/run/t"))


if __name__ == "__main__":
    unittest.main()
