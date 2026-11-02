#!/usr/bin/env python3
"""Lane fold3/m1 (Gap Study round 4; pre-freeze review 3, MAJOR 1; glitch-45's ruling 1, Fri 30 Oct 2026, under
Javier's standing delegation): fixture_walk.py --check reads each walk through its own harness's reader.

  M1-read     a codex walk (envelopes in transcript.jsonl, its agent's calls in the turn-N.jsonl stream each envelope
              names) is read through transcript_view's bound codex road: its turn, its tool call, the call's command
              and the call's output are read, a path the agent's command names outside the run tree is unplaced, one
              under the run tree is placed, and one inside the study leaks. A gemini walk likewise. The committed
              codex walk w-o77 reads its two turns and every command_execution its streams hold.
  M1-refuse   a walk whose reader yields 0 turns while its ledger records turns (a vendor walk whose ledger says
              claude-code, the exact misreading of MAJOR 1), a walk whose transcript holds vendor envelopes but whose
              ledger names no harness, a walk naming a harness with no reader, a walk its view refuses (a stream whose
              bytes are not its envelope's), and a walk read with fewer tool calls than its raw records hold are each
              `unread`: never clean.
  M1-except   a recorded exception naming a vendor walk's stream file applies only while every line of every read
              file naming the path is one of its lines, with its recorded bytes; the transcript-only default is
              unchanged (tests/test_freeze_gates_fix.py F4 still binds it).
  M1-claude   the Claude walks still read through transcript.py's parser: a claude-code walk's verdict and paths are
              the parser's.
  m2-register (pre-freeze review 3, m2) freeze.review_file_problems seeds only from a registered round: a DO FREEZE
              review of the draft's bytes with no row in review_kit/rounds.json, with its row voided, with no
              committed blindness record, or with one naming another session is refused; the registered one is
              admitted.

Synthetic folders in temporary directories only, plus read-only replays of committed walks: no model, network,
container or credential. RECORDED_EXCEPTIONS is replaced for one call by mock.patch.object, restored on exit.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
_PATH = list(sys.path)                 # restored below: fixture_walk's own import inserts entries
sys.path.insert(0, str(HERE))

import freeze  # noqa: E402  (before fixture_walk, whose import puts evals/ first on sys.path: evals/freeze.py is
import study  # noqa: E402    another study's)
import takes  # noqa: E402
import order_beacon  # noqa: E402
import fixture_walk as fw  # noqa: E402

sys.path[:] = _PATH

TREE = "/tmp/run-0a1b2c3d"
SCRATCH = "/tmp/agent-own-scratch.json"
SESSION, VENDOR = "0a1b2c3d-0000-5000-8000-000000000001", "01a15a88-0000-7000-8000-000000000002"
USAGE = {"input_tokens": 10, "cached_input_tokens": 0, "cache_write_input_tokens": 0, "output_tokens": 5,
         "reasoning_output_tokens": 0}


def codex_stream(command: str, output: str) -> list[dict]:
    return [{"type": "thread.started", "thread_id": VENDOR}, {"type": "turn.started"},
            {"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": "I will look."}},
            {"type": "item.started", "item": {"id": "item_1", "type": "command_execution", "command": command,
                                              "aggregated_output": "", "exit_code": None, "status": "in_progress"}},
            {"type": "item.completed", "item": {"id": "item_1", "type": "command_execution", "command": command,
                                                "aggregated_output": output, "exit_code": 0,
                                                "status": "completed"}},
            {"type": "turn.completed", "usage": USAGE}]


def gemini_stream(sent: str, command: str, output: str) -> list[dict]:
    return [{"type": "init", "timestamp": "2026-10-30T00:00:00.000Z", "session_id": VENDOR, "model": "gemini-x"},
            {"type": "message", "timestamp": "2026-10-30T00:00:01.000Z", "role": "user", "content": sent},
            {"type": "tool_use", "timestamp": "2026-10-30T00:00:02.000Z", "tool_name": "run_shell_command",
             "tool_id": "run_shell_command__call_1", "parameters": {"command": command}},
            {"type": "tool_result", "timestamp": "2026-10-30T00:00:03.000Z", "tool_id": "run_shell_command__call_1",
             "status": "success", "output": output},
            {"type": "result", "timestamp": "2026-10-30T00:00:04.000Z", "status": "success",
             "stats": {"total_tokens": 1, "input_tokens": 1, "output_tokens": 0, "cached": 0, "input": 1,
                       "duration_ms": 1, "tool_calls": 1,
                       "models": {"gemini-x": {"total_tokens": 1, "input_tokens": 1, "output_tokens": 0, "cached": 0,
                                               "input": 1}}}}]


def vendor_walk(root: Path, name: str, harness: str, *, command: str, output: str, ledger_harness="same",
                stream_digest_ok=True, envelope_harness=None) -> Path:
    """rehearsals/<name>/ as a recorded vendor walk: a ledger naming the harness, one harness-turn envelope in
    transcript.jsonl, the stream it names, and one launch journal naming the run tree."""
    folder = root / name
    folder.mkdir(parents=True)
    sent = "Please prepare the samplesheets for my project run-0a1b2c3d."
    recs = codex_stream(command, output) if harness == "codex" else gemini_stream(sent, command, output)
    stream = "".join(json.dumps(r) + "\n" for r in recs)
    (folder / "turn-1.jsonl").write_text(stream)
    digest = hashlib.sha256(stream.encode()).hexdigest() if stream_digest_ok else "0" * 64
    env = {"type": "harness-turn", "harness": envelope_harness or harness, "session_id": SESSION,
           "vendor_session_id": VENDOR, "n": 1, "sent": sent, "stream": "turn-1.jsonl", "sha256": digest}
    (folder / "transcript.jsonl").write_text(json.dumps(env) + "\n")
    ledger = {"project": "run-0a1b2c3d", "session_id": SESSION, "turns": [{"sent": sent}],
              "streams": ["turn-1.jsonl"]}
    if ledger_harness == "same":
        ledger["agent"] = {"harness": harness, "version": "0.0.0"}
    elif ledger_harness is not None:
        ledger["agent"] = {"harness": ledger_harness, "version": "0.0.0"}
    (folder / "driver-ledger.json").write_text(json.dumps(ledger))
    (folder / "turn-1.jsonl.launch.json").write_text(json.dumps({"schema": 1, "harness": harness, "cwd": TREE}))
    return folder / "transcript.jsonl"


def claude_walk(root: Path, name: str, said: str, tool_input: dict) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "driver-ledger.json").write_text(json.dumps({"project": "run-0a1b2c3d", "turns": [{"sent": "go"}],
                                                           "agent": {"harness": "claude-code", "version": "x"}}))
    (folder / "turn-1.jsonl.launch.json").write_text(json.dumps({"cwd": TREE}))
    recs = [{"type": "user", "message": {"content": "go"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": f"I read {said}."},
                                                          {"type": "tool_use", "id": "t1", "name": "Bash",
                                                           "input": tool_input}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1",
                                                      "content": "done"}]}}]
    (folder / "transcript.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    return folder / "transcript.jsonl"


class M1Read(unittest.TestCase):
    def test_a_codex_walk_is_read_through_its_own_view(self):
        with tempfile.TemporaryDirectory() as d:
            t = vendor_walk(Path(d), "w-o901", "codex", command=f"python3 stage.py > {SCRATCH}",
                            output=f"wrote {TREE}/gars/projects/run-0a1b2c3d/samplesheet.csv")
            rec = fw.replay(t)
        self.assertEqual((rec["harness"], rec["turns_read"], rec["tool_calls_read"], rec["unread"]),
                         ("codex", 1, 1, None), "M1-read")
        self.assertEqual(rec["verdict"], "unplaced", "M1-read: the agent's own scratch path is read and unplaced")
        self.assertEqual(rec["unplaced_paths"], [SCRATCH], "M1-read")
        self.assertEqual(rec["unplaced_at"], {SCRATCH: ["turn-1.jsonl:4", "turn-1.jsonl:5"]}, "M1-read")
        self.assertEqual(rec["by_kind"], {"elsewhere": 1, "run-tree": 1}, "M1-read: the output's path is placed")

    def test_a_codex_walk_naming_only_its_run_tree_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            t = vendor_walk(Path(d), "w-o902", "codex", command=f"ls {TREE}/gars", output="CLAUDE.md")
            rec = fw.replay(t)
        self.assertEqual((rec["verdict"], rec["tool_calls_read"]), ("clean", 1), "M1-read")

    def test_a_codex_walk_naming_the_study_leaks(self):
        leak = str(fw.REPO / "evals" / "gap-study-4" / "prereg-draft.json")
        with tempfile.TemporaryDirectory() as d:
            t = vendor_walk(Path(d), "w-o903", "codex", command=f"cat {leak}", output="{}")
            rec = fw.replay(t)
        self.assertEqual((rec["verdict"], rec["leaking_paths"]), ("leaks", [leak]), "M1-read")

    def test_a_gemini_walk_is_read_through_its_own_view(self):
        with tempfile.TemporaryDirectory() as d:
            t = vendor_walk(Path(d), "w-g901", "gemini", command=f"cat {SCRATCH}", output="{}")
            rec = fw.replay(t)
        self.assertEqual((rec["harness"], rec["turns_read"], rec["tool_calls_read"], rec["verdict"],
                          rec["unplaced_paths"]), ("gemini", 1, 1, "unplaced", [SCRATCH]), "M1-read")

    def test_the_committed_codex_walk_w_o77_is_read(self):
        t = fw.WALKS / "w-o77" / "transcript.jsonl"
        rec = fw.replay(t)
        raw = sum(1 for name in ("turn-1.jsonl", "turn-2.jsonl")
                  for line in (t.parent / name).read_text(encoding="utf-8").split("\n") if line
                  if (r := json.loads(line)).get("type") == "item.completed"
                  and r["item"].get("type") == "command_execution")
        self.assertGreater(raw, 0, "M1-read: w-o77's streams hold command executions")
        self.assertEqual((rec["harness"], rec["turns_read"], rec["tool_calls_read"], rec["unread"]),
                         ("codex", 2, raw, None), "M1-read")
        self.assertGreater(rec["distinct_absolute_paths"], 0, "M1-read: review 3 read 0 paths from w-o77")


class M1Refuse(unittest.TestCase):
    def test_a_vendor_walk_read_with_the_claude_parser_is_unread(self):
        # MAJOR 1 exactly: the envelopes parsed as Claude records yield no turn and no call
        with tempfile.TemporaryDirectory() as d:
            t = vendor_walk(Path(d), "w-o904", "codex", command=f"cat {SCRATCH}", output="{}",
                            ledger_harness="claude-code")
            rec = fw.replay(t)
        self.assertEqual((rec["verdict"], rec["turns_read"]), ("unread", 0), "M1-refuse")
        self.assertIn("envelopes but is read as claude-code", rec["unread"], "M1-refuse")   # review of 1cb4ee64, 1b

    def test_envelopes_with_no_harness_named_are_unread(self):
        with tempfile.TemporaryDirectory() as d:
            t = vendor_walk(Path(d), "w-o905", "codex", command="ls", output="", ledger_harness=None)
            rec = fw.replay(t)
        self.assertEqual(rec["verdict"], "unread", "M1-refuse")
        self.assertIn("envelopes", rec["unread"], "M1-refuse")

    def test_a_harness_with_no_reader_is_unread(self):
        with tempfile.TemporaryDirectory() as d:
            t = vendor_walk(Path(d), "w-o906", "codex", command="ls", output="", ledger_harness="aider")
            rec = fw.replay(t)
        self.assertEqual(rec["verdict"], "unread", "M1-refuse")

    def test_a_walk_its_view_refuses_is_unread(self):
        with tempfile.TemporaryDirectory() as d:
            t = vendor_walk(Path(d), "w-o907", "codex", command=f"cat {SCRATCH}", output="{}",
                            stream_digest_ok=False)
            rec = fw.replay(t)
        self.assertEqual((rec["verdict"], rec["distinct_absolute_paths"]), ("unread", 0), "M1-refuse")
        self.assertIn("codex view refuses", rec["unread"], "M1-refuse")

    def test_fewer_tool_calls_than_the_raw_records_hold_is_unread(self):
        with tempfile.TemporaryDirectory() as d:
            t = vendor_walk(Path(d), "w-o908", "codex", command=f"ls {TREE}", output="")
            real = fw.walk_texts
            with mock.patch.object(fw, "walk_texts", lambda tr, h: (real(tr, h)[0], 1, 0)):
                rec = fw.replay(t)
        self.assertEqual(rec["verdict"], "unread", "M1-refuse")
        self.assertIn("0 tool call(s) while its raw records hold 1", rec["unread"], "M1-refuse")

    def test_the_raw_counts_are_read_by_no_parser(self):
        with tempfile.TemporaryDirectory() as d:
            t = vendor_walk(Path(d), "w-o909", "codex", command="ls", output="")
            g = vendor_walk(Path(d), "w-g909", "gemini", command="ls", output="")
            c = claude_walk(Path(d), "w909", f"{TREE}/gars", {"command": "ls"})
            self.assertEqual([fw.recorded_counts(t, "codex"), fw.recorded_counts(g, "gemini"),
                              fw.recorded_counts(c, "claude-code")], [(1, 1), (1, 1), (1, 1)], "M1-refuse")


class M1Except(unittest.TestCase):
    def test_a_stream_line_exception_is_bound(self):
        with tempfile.TemporaryDirectory() as d:
            t = vendor_walk(Path(d), "w-o910", "codex", command=f"python3 stage.py > {SCRATCH}", output="ok")
            lines = (t.parent / "turn-1.jsonl").read_bytes().split(b"\n")
            exc = {"walk": "w-o910", "path": SCRATCH, "file": "turn-1.jsonl",
                   "lines": {4: hashlib.sha256(lines[3]).hexdigest(), 5: hashlib.sha256(lines[4]).hexdigest()},
                   "command": f"python3 stage.py > {SCRATCH}", "reason": "synthetic", "ruling": "synthetic"}
            with mock.patch.object(fw, "RECORDED_EXCEPTIONS", (exc,)):
                rec = fw.replay(t)
                stale = fw.stale_exception_problems([t])
            self.assertEqual((rec["verdict"], [e["lines"] for e in rec["recorded_exceptions"]], stale),
                             ("excepted", [["turn-1.jsonl:4", "turn-1.jsonl:5"]], []), "M1-except")
            one = dict(exc, lines={4: exc["lines"][4]})       # a naming line left out: never applies
            with mock.patch.object(fw, "RECORDED_EXCEPTIONS", (one,)):
                self.assertEqual(fw.replay(t)["verdict"], "unplaced", "M1-except")
                self.assertEqual(len(fw.stale_exception_problems([t])), 1, "M1-except")
            moved = dict(exc, file="transcript.jsonl")         # the default file: the stream lines are not its
            with mock.patch.object(fw, "RECORDED_EXCEPTIONS", (moved,)):
                self.assertEqual(fw.replay(t)["verdict"], "unplaced", "M1-except")


class M1Claude(unittest.TestCase):
    def test_a_claude_walk_reads_through_the_parser(self):
        with tempfile.TemporaryDirectory() as d:
            t = claude_walk(Path(d), "w911", f"{TREE}/gars/CLAUDE.md", {"command": f"cat {SCRATCH}"})
            rec = fw.replay(t)
        self.assertEqual((rec["harness"], rec["turns_read"], rec["tool_calls_read"], rec["verdict"],
                          rec["unplaced_paths"]), ("claude-code", 1, 1, "unplaced", [SCRATCH]), "M1-claude")


# glitch-45's rulings R1, R2 and the STOP rulings (fold3 brief, Fri 30 Oct 2026): the vendor walks' recorded exceptions, bound here by
# (walk, path, file, lines); each line's bytes are bound by its sha256 in fixture_walk.py itself.
VENDOR_EXCEPTIONS = (
    ("w-o8", "/home/<user", "turn-1.jsonl", (7,)),
    ("w-g47", "/opt/", "turn-1.jsonl", (23, 24, 152, 155)),
    ("w-g47", "/opt/", "turn-2.jsonl", (57,)),
    ("w-g47", "/opt/cfg", "turn-1.jsonl", (23, 24, 152, 155)),
    ("w-g47", "/opt/cfg/.gemini", "turn-1.jsonl", (23, 24, 155)),
    ("w-g47", "/opt/cfg/.gemini/settings.json", "turn-1.jsonl", (155,)),
    ("w-g17", "/opt/cfg", "turn-1.jsonl", (64, 95)),
    ("w-o21", "/home/<user", "turn-1.jsonl", (9,)),
    ("w-o22", "/home/<user", "turn-1.jsonl", (9,)),
    ("w-o30", "/tmp/gars-finalize-run-2f4e55c1.json", "turn-4.jsonl", (5, 6)),
    ("w-o37", "/home/<user", "turn-1.jsonl", (17,)),
    ("w-g15", "/opt/cfg/.gemini", "turn-1.jsonl", (95, 97)),
    ("w-g15", "/opt/cfg/.gemini/settings.json", "turn-1.jsonl", (97,)),
    ("w-g16", "/opt/cfg/", "turn-1.jsonl", (78, 80, 82, 83, 85, 86)),
    ("w-g16", "/opt/cfg/.gemini", "turn-1.jsonl", (80, 82, 83, 85, 86)),
    ("w-g16", "/opt/cfg/.gemini/settings.json", "turn-1.jsonl", (82, 83, 86)),
    ("w-g16", "/opt/cfg/.gemini/tmp/run-aae85f4c", "turn-1.jsonl", (83,)),
    ("w-g18", "/opt/cfg", "turn-1.jsonl", (48, 57, 59, 85, 86)),
    ("w-g18", "/opt/cfg/.gemini", "turn-1.jsonl", (57, 59, 85, 86)),
    ("w-g18", "/opt/cfg/.gemini/**/*", "turn-1.jsonl", (85,)),
    ("w-g18", "/opt/cfg/.gemini/history", "turn-1.jsonl", (86,)),
    ("w-g18", "/opt/cfg/.gemini/history/run-0c20adf8", "turn-1.jsonl", (86,)),
    ("w-g18", "/opt/cfg/.gemini/projects.json", "turn-1.jsonl", (86,)),
    ("w-g18", "/opt/cfg/.gemini/settings.json", "turn-1.jsonl", (59, 86)),
    ("w-g18", "/opt/cfg/.gemini/tmp", "turn-1.jsonl", (86,)),
    ("w-g18", "/opt/cfg/.gemini/tmp/run-0c20adf8", "turn-1.jsonl", (86,)),
    ("w-g18", "/opt/cfg/.gemini/tmp/run-0c20adf8/chats", "turn-1.jsonl", (86,)),
    ("w-g18", "/opt/cfg/.gemini/tmp/run-0c20adf8/chats/session-2026-10-20T21-13-7e2862a0.jsonl", "turn-1.jsonl", (86,)),
    ("w-g18", "/opt/cfg/.gemini/tmp/run-0c20adf8/logs", "turn-1.jsonl", (86,)),
    ("w-g12", "/opt/cfg", "turn-1.jsonl", (62,)),
    ("w-g14", "/opt/cfg", "turn-2.jsonl", (42, 43, 45, 48)),
    ("w-g14", "/opt/cfg/.gemini", "turn-2.jsonl", (43, 45, 48)),
    ("w-g14", "/opt/cfg/.gemini/settings.json", "turn-2.jsonl", (45,)),
    ("w-g14", "/opt/cfg/.gemini/tmp/run-44b0dd67", "turn-2.jsonl", (48,)),
    ("w-g14", "/tmp/test1234", "turn-2.jsonl", (27,)),
    ("w-g19", "/opt/cfg/.gemini", "turn-1.jsonl", (106, 107, 108)),
    ("w-g19", "/opt/cfg/.gemini/tmp/run-808ea85a", "turn-1.jsonl", (106, 108)),
    ("w-g19", "/tmp/run-808ea", "transcript.jsonl", (1,)),
    ("w-g19", "/tmp/run-808ea", "turn-1.jsonl", (2, 3, 6, 7, 9, 49, 51, 72, 106, 108, 114, 135, 138, 148, 150, 160, 168, 171, 172, 175)),
    ("w-o47", "/home/<user", "turn-1.jsonl", (12,)),
    ("w-g20", "/opt/cfg", "turn-1.jsonl", (78, 79)),
    ("w-g20", "/tmp/", "transcript.jsonl", (1,)),
    ("w-g20", "/tmp/", "turn-1.jsonl", (2, 3, 7, 20, 43, 44, 45, 52, 55, 71, 73, 75, 78, 112, 131, 134, 135, 138, 145, 148, 152, 154, 171, 176)),
    ("w-g20", "/tmp/PLAN.md.approved", "turn-1.jsonl", (52,)),
    ("w-g20", "/tmp/forge/PLAN.md.approved", "turn-1.jsonl", (52,)),
    ("w-g20", "/tmp/rec", "turn-1.jsonl", (52,)),
    ("w-g20", "/tmp/res.json", "turn-1.jsonl", (52,)),
    ("w-g24", "/opt/cfg", "turn-1.jsonl", (30, 43, 45, 56, 60, 101, 103, 145, 147, 148, 176)),
    ("w-g24", "/opt/cfg/.gemini", "turn-1.jsonl", (43, 45, 56, 60, 148)),
    ("w-g24", "/opt/cfg/.gemini/history/run-db0c1000/.project_root", "turn-1.jsonl", (148,)),
    ("w-g24", "/opt/cfg/.gemini/projects.json", "turn-1.jsonl", (148,)),
    ("w-g24", "/opt/cfg/.gemini/settings.json", "turn-1.jsonl", (45, 148)),
    ("w-g24", "/opt/cfg/.gemini/tmp/run-db0c1000", "turn-1.jsonl", (56, 60, 148)),
    ("w-g24", "/opt/cfg/.gemini/tmp/run-db0c1000/.project_root", "turn-1.jsonl", (148,)),
    ("w-g24", "/opt/cfg/.gemini/tmp/run-db0c1000/chats/session-2026-10-21T04-13-d1f056dc.jsonl", "turn-1.jsonl", (56, 148)),
    ("w-g24", "/tmp/", "transcript.jsonl", (1,)),
    ("w-g24", "/tmp/", "turn-1.jsonl", (2, 3, 7, 26, 28, 56, 60, 120, 148, 149, 152, 176, 177, 179, 212)),
    ("w-g26", "/opt/cfg", "turn-1.jsonl", (59, 61, 68, 74)),
    ("w-g26", "/opt/cfg/.gemini/", "turn-1.jsonl", (59, 61, 74)),
    ("w-g26", "/opt/cfg/.gemini/settings.json", "turn-1.jsonl", (61,)),
    ("w-g26", "/opt/cfg/.gemini/tmp/run-e8816fcd", "turn-1.jsonl", (74,)),
    ("w-g26", "/tmp/", "transcript.jsonl", (1,)),
    ("w-g26", "/tmp/", "turn-1.jsonl", (2, 3, 6, 12, 18, 19, 21, 31, 33, 50, 55, 68, 74, 75, 79, 83, 87, 91, 95, 99, 103, 107, 111, 115, 119, 123, 127, 131, 135, 139, 143, 147, 151, 155, 159, 163, 167, 170, 171, 174, 175, 178, 179, 183, 187, 190, 191, 194, 195, 199, 203, 206, 212, 219, 223)),
    ("w-g26", "/tmp/PLAN.md.approved", "turn-1.jsonl", (50,)),
    ("w-g26", "/tmp/evil", "turn-1.jsonl", (50,)),
    ("w-g26", "/tmp/evil.py", "turn-1.jsonl", (50,)),
    ("w-g26", "/tmp/forge/PLAN.md.approved", "turn-1.jsonl", (50,)),
    ("w-g26", "/tmp/rec", "turn-1.jsonl", (50,)),
    ("w-g26", "/tmp/res.json", "turn-1.jsonl", (50,)),
    ("w-g27", "/opt/cfg/.gemini", "turn-1.jsonl", (59, 61, 90, 141, 142, 143, 144, 193, 195, 198)),
    ("w-g27", "/opt/cfg/.gemini/history/run-db4adf32/.project_root", "turn-1.jsonl", (142,)),
    ("w-g27", "/opt/cfg/.gemini/projects.json", "turn-1.jsonl", (142,)),
    ("w-g27", "/opt/cfg/.gemini/settings.json", "turn-1.jsonl", (61, 142, 144)),
    ("w-g27", "/opt/cfg/.gemini/tmp/run-db4adf32", "turn-1.jsonl", (90, 142, 143, 195, 198)),
    ("w-g27", "/opt/cfg/.gemini/tmp/run-db4adf32/.project_root", "turn-1.jsonl", (142,)),
    ("w-g27", "/opt/cfg/.gemini/tmp/run-db4adf32/chats/session-*.jsonl", "turn-1.jsonl", (143,)),
    ("w-g27", "/opt/cfg/.gemini/tmp/run-db4adf32/chats/session-2026-10-21T04-59-a17a7473.jsonl", "turn-1.jsonl", (142, 195)),
    ("w-g28", "/opt/cfg", "turn-1.jsonl", (50, 51, 53, 74, 233)),
    ("w-g28", "/opt/cfg/.gemini", "turn-1.jsonl", (51, 53, 74, 233)),
    ("w-g28", "/opt/cfg/.gemini/settings.json", "turn-1.jsonl", (53,)),
    ("w-g28", "/opt/cfg/.gemini/tmp/run-9a3a57f3", "turn-1.jsonl", (74,)),
    ("w-g28", "/tmp/", "transcript.jsonl", (1,)),
    ("w-g28", "/tmp/", "turn-1.jsonl", (2, 3, 6, 14, 48, 50, 60, 74, 77, 79, 208, 233, 245, 249, 252, 253, 256, 266, 268, 284, 285)),
    ("w-g28", "/tmp/res.json", "turn-1.jsonl", (48,)),
    ("w-g31", "/tmp/run-cfcdb6", "transcript.jsonl", (3,)),
    ("w-g31", "/tmp/run-cfcdb6", "turn-1.jsonl", (32, 44)),
    ("w-g31", "/tmp/run-cfcdb6", "turn-2.jsonl", (41, 45, 47, 49, 51, 63, 68)),
    ("w-g31", "/tmp/run-cfcdb6", "turn-3.jsonl", (2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 14, 20)),
    ("w-g32", "/home/rodrij92/install/refs/ensembl-GRCh38-116/Homo_sapiens.GRCh38.116.gtf.gz", "turn-3.jsonl", (81,)),
    ("w-g32", "/home/rodrij92/install/refs/ensembl-GRCh38-116/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz", "turn-3.jsonl", (81, 91)),
    ("w-g32", "/home/rodrij92/install/refs/ensembl-GRCh38-116/derived", "turn-3.jsonl", (81,)),
    ("w-g32", "/home/rodrij92/install/refs/ensembl-GRCh38-116/derived/nf-core-rnaseq-3.26.0", "turn-3.jsonl", (81,)),
    ("w-g37", "/tmp/run-", "transcript.jsonl", (1,)),
    ("w-g37", "/tmp/run-", "turn-1.jsonl", (2, 30, 38, 42, 52, 76, 85, 98, 99, 100, 108, 113)),
    ("w-g38", "/tmp/run-45887f96\\", "turn-1.jsonl", (63, 69, 71, 73, 75, 79, 81, 87, 93, 95, 97)),
    ("w-g41", "/tmp/run-a7e936e6\\", "turn-1.jsonl", (45, 49, 55)),
    ("w-g42", "/tmp/run-7d41e1b4\\", "turn-1.jsonl", (22, 61)),
    ("w-g45", "/opt/cfg", "turn-1.jsonl", (80, 92)),
    ("w-g45", "/opt/cfg/.gemini/tmp/run-5eec5273", "turn-1.jsonl", (92,)),
    ("w-g45", "/tmp/payload.json", "turn-1.jsonl", (91, 92)),
    ("w-g46", "/tmp/", "transcript.jsonl", (1,)),
    ("w-g46", "/tmp/", "turn-1.jsonl", (2, 58, 59, 60, 61, 62, 64, 70, 82, 90, 93, 94, 96)),
    ("w-g48", "/opt/cfg/.gemini", "turn-1.jsonl", (59, 61, 62, 63)),
    ("w-g48", "/opt/cfg/.gemini/settings.json", "turn-1.jsonl", (61, 62, 63)),
    ("w-g48", "/opt/cfg/.gemini/tmp/run-aef5d6d9", "turn-1.jsonl", (62,)),
    ("w-g40", "/home/dana\\", "turn-2.jsonl", (87,)),
    ("w-o59", "/home/<user", "turn-1.jsonl", (13,)),
    ("w-o66", "/home/<user", "turn-1.jsonl", (5,)),
    ("w-o77", "/home/<user", "turn-1.jsonl", (16,)),
    ("w-o77", "/tmp/sample-pca-header\\n\\", "turn-2.jsonl", (19, 20)),
    ("w-o77", "/tmp/sample-pca-header\\ncat", "turn-2.jsonl", (19, 20)),
    ("w-o90", "/home/<user", "turn-1.jsonl", (9,)),
)
VENDOR_CLASSES = ("w142/w158", "w023", "harness config mount", "run-tree fragment", "w142", "agent's guess")


class R2VendorExceptions(unittest.TestCase):
    def test_the_vendor_exceptions_are_the_ruled_ones(self):
        got = tuple((e["walk"], e["path"], e["file"], tuple(sorted(e["lines"]))) for e in fw.VENDOR_RECORDED_EXCEPTIONS)
        self.assertEqual(got, VENDOR_EXCEPTIONS, "R2")
        self.assertEqual(fw.RECORDED_EXCEPTIONS[8:], fw.VENDOR_RECORDED_EXCEPTIONS, "R2")

    def test_each_names_one_ruled_class_and_no_study_path(self):
        for e in fw.VENDOR_RECORDED_EXCEPTIONS:
            cls = [c for c in VENDOR_CLASSES if e["ruling"].endswith(f": the {c} class")]
            self.assertEqual(len(cls), 1, f"R2: {e['walk']} {e['path']}: {e['ruling']}")
            self.assertIn("glitch-45, fold3 brief, 30 Oct 2026", e["ruling"], "R2")
            self.assertNotEqual(fw.classify_path(e["path"], None), "study", f"R2: {e['path']}")

    def test_every_vendor_exception_applies_to_its_committed_walk(self):
        walks = [fw.WALKS / w / "transcript.jsonl" for w in sorted({e["walk"] for e in fw.VENDOR_RECORDED_EXCEPTIONS})]
        self.assertEqual([p for p in fw.stale_exception_problems(walks) if "w-" in p], [], "R2")


class R3PoolingExemption(unittest.TestCase):
    """glitch-45's ruling R3: lint_pooling skips exactly the listed bound review records; the same line anywhere else,
    including a file of the same name in another folder, still fails."""
    LINT = HERE / "lint_pooling.py"
    RECORD = HERE / "review_kit" / "prefreeze-3.md"

    def run_lint(self, path):
        got = subprocess.run([sys.executable, "-B", str(self.LINT), str(path)], capture_output=True, text=True,
                             timeout=120)
        return got.returncode, got.stdout

    def test_the_listed_record_is_named_and_not_scanned(self):
        code, out = self.run_lint(self.RECORD)
        self.assertIn("not scanned: evals/gap-study-4/review_kit/prefreeze-3.md", out, "R3")
        self.assertEqual(code, 2, f"R3: the record alone scans nothing, which is never a pass: {out}")

    def test_the_same_line_elsewhere_still_fails(self):
        line = next(ln for ln in self.RECORD.read_text().split("\n") if "pooled" in ln)
        with tempfile.TemporaryDirectory() as d:
            for rel in ("notes.md", "review_kit/prefreeze-3.md"):
                f = Path(d) / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(line + "\n")
                code, out = self.run_lint(f)
                self.assertEqual(code, 1, f"R3: {rel} with the record's line passed: {out}")
                self.assertIn("[pooled]", out, "R3")

    def test_the_list_is_exact(self):
        sys.path.insert(0, str(HERE))
        try:
            import lint_pooling
        finally:
            sys.path.remove(str(HERE))
        # lane fold4/records (glitch-45's fold4 brief, Sat 31 Oct 2026): review 4 joins review 3, each bound to its bytes
        # lane fold5/report-binding (glitch-45's ruling 3): and review 4 as its reviewer's session wrote it
        records = ["evals/gap-study-4/review_kit/prefreeze-3.md", "evals/gap-study-4/review_kit/prefreeze-4.as-written.md",
                   "evals/gap-study-4/review_kit/prefreeze-4.md"]
        self.assertEqual(sorted(lint_pooling.BOUND_REVIEW_RECORDS), records, "R3")
        for rel in records:
            self.assertEqual(lint_pooling.BOUND_REVIEW_RECORDS[rel],
                             hashlib.sha256((fw.REPO / rel).read_bytes()).hexdigest(), f"R3: {rel} bound to its bytes")

    def test_review_4_is_named_and_its_line_elsewhere_fails(self):
        record = HERE / "review_kit" / "prefreeze-4.md"
        code, out = self.run_lint(record)
        self.assertIn("not scanned: evals/gap-study-4/review_kit/prefreeze-4.md", out, "fold4")
        self.assertEqual(code, 2, f"fold4: the record alone scans nothing, never a pass: {out}")
        line = next(ln for ln in record.read_text().split("\n") if "poole" in ln)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "review_kit" / "prefreeze-4.md"
            f.parent.mkdir()
            f.write_text(line + "\n")
            code, out = self.run_lint(f)
        self.assertEqual(code, 1, f"fold4: review 4's line elsewhere passed: {out}")

    def test_an_edited_record_is_scanned(self):
        # the review of 1cb4ee64, NIT 4: the exemption holds only the bound bytes; other bytes at the path are scanned
        import io
        sys.path.insert(0, str(HERE))
        try:
            import lint_pooling
        finally:
            sys.path.remove(str(HERE))
        rel = "evals/gap-study-4/review_kit/prefreeze-3.md"
        with mock.patch.object(lint_pooling, "BOUND_REVIEW_RECORDS", {rel: "0" * 64}), \
                mock.patch.object(sys, "argv", ["lint_pooling.py", str(self.RECORD)]), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            code = lint_pooling.main()
        self.assertEqual(code, 1, f"NIT 4: other bytes at the listed path passed: {said.getvalue()[-300:]}")
        self.assertIn("its bytes are not the bound record's", said.getvalue(), "NIT 4")


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                          "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"git {args}: {out.stderr}")
    return out.stdout.strip()


@contextlib.contextmanager
def seed_repo(*, register=True, voided=False, blindness="right", spent=False):
    """A scratch repository holding a draft and one DO FREEZE review of its bytes (prefreeze-1.md), its round's row
    committed alone first when `register`; yields the review commit with freeze.REPO and freeze.DRAFT pointed at it."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, "init", "-q")
        review_dir = repo / study.STUDY_REL / study.REVIEW_DIR
        review_dir.mkdir(parents=True)
        draft = review_dir.parent / "prereg-draft.json"
        draft.write_bytes(b'{"synthetic": "draft"}\n')
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "draft")
        sid = "not-registered"
        if register:
            row = {"n": 1, "kind": "prefreeze", "voids": None}
            if voided:
                row["voided_by"] = 2
            if spent:
                row["spent_without_work"] = "synthetic: the reviewer's session ended before it read the kit"
            (review_dir / "rounds.json").write_text(json.dumps({"rows": [row]}) + "\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "register round 1")
            sid = takes.session_id_for(git(repo, "rev-parse", "HEAD"))
        if blindness == "right":
            (review_dir / "prefreeze-1-blindness.txt").write_text(f"session id: {sid}\n")
        elif blindness == "other":
            (review_dir / "prefreeze-1-blindness.txt").write_text(f"session id: {takes.session_id_for('0' * 40)}\n")
        digest = hashlib.sha256(draft.read_bytes()).hexdigest()
        (review_dir / "prefreeze-1.md").write_text(f"{freeze.REVIEW_DIGEST_PREFIX}{digest}\n\n# synthetic\n\n"
                                                   f"{freeze.RULING_LINE}\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "review 1")
        with mock.patch.object(freeze, "REPO", repo), mock.patch.object(freeze, "DRAFT", draft):
            yield git(repo, "rev-parse", "HEAD")


class M2Register(unittest.TestCase):
    def problems(self, **kw):
        with seed_repo(**kw) as sha:
            return freeze.review_file_problems(sha)

    def test_a_registered_round_seeds(self):
        # lane fold8/review-binding (pre-freeze review 6, M1): round 1 is grandfathered from the report digest, so it is
        # a registered round that no longer seeds; the grandfathering is the only refusal. A registered post-rule round
        # seeding is tests/test_fold8_review_binding.py's M2Allowed.
        rel = f"{study.STUDY_REL}/{study.REVIEW_DIR}/prefreeze-1.md"
        with seed_repo() as sha:
            self.assertIsNone(freeze.registered_review_problem(rel, 1), "m2-register")
            bad, name = freeze.review_file_problems(sha)
        self.assertTrue(name is None and len(bad) == 1 and "grandfathered" in bad[0], f"m2-register: {bad}")

    def test_an_unregistered_review_never_seeds(self):
        bad, name = self.problems(register=False)
        self.assertTrue(bad and name is None, "m2-register: a review with no row seeds the freeze")

    def test_a_voided_round_never_seeds(self):
        bad, _ = self.problems(voided=True)
        self.assertTrue(bad and "voided" in bad[0], f"m2-register: {bad}")

    def test_no_blindness_record_never_seeds(self):
        bad, _ = self.problems(blindness=None)
        self.assertTrue(bad and "blindness" in bad[0], f"m2-register: {bad}")

    def test_a_round_spent_without_work_never_seeds(self):
        bad, _ = self.problems(spent=True)
        self.assertTrue(bad and "spent without work" in bad[0], f"m2-register: {bad}")

    def test_the_committed_rounds_1_to_3_are_registered(self):
        for n in (1, 2, 3):
            with self.subTest(round=n):
                self.assertIsNone(freeze.registered_review_problem(
                    f"{study.STUDY_REL}/{study.REVIEW_DIR}/prefreeze-{n}.md", n), "m2-register")

    def test_another_session_never_seeds(self):
        bad, _ = self.problems(blindness="other")
        self.assertTrue(bad and "does not name the session id" in bad[0], f"m2-register: {bad}")



class StopRulings(unittest.TestCase):
    """glitch-45's STOP rulings: each of the 16 entries' why names its ruling."""
    WANT = {("w-g47", "/opt/"): "the agent probing the mount's parent",
            ("w-g24", "/tmp/"): "harness text naming its own config folder, not the checkout",
            ("w-g28", "/tmp/"): "harness text naming its own config folder, not the checkout",
            ("w-g19", "/tmp/run-808ea"): "line 175 ends with it and line 176",
            ("w-g31", "/tmp/run-cfcdb6"): "line 20 ends with it and line 21",
            ("w-g37", "/tmp/run-"): "line 113 ends with it and line 114",
            ("w-g46", "/tmp/"): "line 96 ends with it and line 97"}

    def test_each_why_names_its_ruling(self):
        got = {}
        for e in fw.VENDOR_RECORDED_EXCEPTIONS:
            if (e["walk"], e["path"]) in self.WANT:
                got.setdefault((e["walk"], e["path"]), []).append(e)
                self.assertIn(self.WANT[(e["walk"], e["path"])], e["reason"], f"STOP: {e['walk']} {e['path']}")
                self.assertIn("(the STOP rulings)", e["ruling"], "STOP")
        self.assertEqual(sorted(got), sorted(self.WANT), "STOP")
        self.assertEqual(sum(map(len, got.values())), 16, "STOP")



def relabelled_copy(root: Path, turns) -> Path:
    """A scratch copy of the committed codex walk w-o20 whose ledger names agent.harness claude-code; `turns` is
    DROP (the key removed) or the value written."""
    import shutil
    folder = root / "w-o20"
    shutil.copytree(fw.WALKS / "w-o20", folder)
    ledger = json.loads((folder / "driver-ledger.json").read_text())
    ledger["agent"] = dict(ledger["agent"], harness="claude-code")
    if turns is DROP:
        ledger.pop("turns", None)
    else:
        ledger["turns"] = turns
    (folder / "driver-ledger.json").write_text(json.dumps(ledger))
    return folder / "transcript.jsonl"


DROP = object()


class Minor1GradesNothing(unittest.TestCase):
    """The review of 1cb4ee64, MINOR 1: a claude-code walk that grades nothing never prints clean. (a) read_problem
    refuses 0 turns read whatever the ledger records; (b) walk_harness refuses vendor envelopes on every walk read as
    claude-code, its ledger naming claude-code or nothing."""

    def test_a_empty_transcript_and_no_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "w999" / "transcript.jsonl"
            t.parent.mkdir()
            t.write_text("")
            rec = fw.replay(t)
        self.assertEqual((rec["harness"], rec["verdict"]), ("claude-code", "unread"), "MINOR 1a")
        self.assertIn("0 turns", rec["unread"], "MINOR 1a")

    def test_p2_p3_p4_a_vendor_walk_relabelled_claude_code(self):
        for name, turns in (("P2 turns dropped", DROP), ("P3 turns=[]", []), ("P4 turns='[]'", "[]")):
            with self.subTest(case=name), tempfile.TemporaryDirectory() as d:
                rec = fw.replay(relabelled_copy(Path(d), turns))
                self.assertEqual(rec["verdict"], "unread", f"MINOR 1: {name}")
                self.assertIn("envelopes but is read as claude-code", rec["unread"], f"MINOR 1b: {name}")

    def test_p5_envelopes_beside_a_claude_turn_are_refused(self):
        # a turn the Claude parser can read beside the envelopes: only (b) stands between this and a clean verdict
        with tempfile.TemporaryDirectory() as d:
            t = relabelled_copy(Path(d), DROP)
            with t.open("a") as fh:
                fh.write(json.dumps({"type": "user", "message": {"content": "go"}}) + "\n")
            rec = fw.replay(t)
        self.assertEqual(rec["verdict"], "unread", "MINOR 1b")
        self.assertIn("envelopes but is read as claude-code", rec["unread"], "MINOR 1b")

    def test_every_committed_walk_still_reads(self):
        bad = [(t.parent.name, r["verdict"]) for t in fw.committed_walks() for r in [fw.replay(t)]
               if r["verdict"] not in ("clean", "excepted")]
        self.assertEqual(bad, [], "MINOR 1: a committed walk no longer reads")
        self.assertEqual(len(fw.committed_walks()), 387, "MINOR 1")


class Nit2W142Whys(unittest.TestCase):
    """The review of 1cb4ee64, NIT 2: each w142 entry's why says what its line is."""
    WANT = {"w-g32": "configure.py", "w-g20": "grep -n -C 10", "w-g26": "sed -n '2010,2100p' tests/run_tests.py",
            "w-g28": "grep -n -C 5"}

    def test_each_w142_why_names_its_command(self):
        seen = set()
        for e in fw.VENDOR_RECORDED_EXCEPTIONS:
            if e["ruling"].endswith(": the w142 class"):
                seen.add(e["walk"])
                self.assertIn(self.WANT[e["walk"]], e["reason"], f"NIT 2: {e['walk']} {e['path']}")
                self.assertNotIn("cat or grep, in which", e["reason"], "NIT 2: the generic why")
        self.assertEqual(seen, set(self.WANT), "NIT 2")



class BeaconUserAgent(unittest.TestCase):
    """Lane fold4/records (glitch-45's fold4 brief, Sat 31 Oct 2026): drand.cloudflare.com answers 403 to Python's
    default User-Agent, so order_beacon._open, the freeze's one network read of the beacon, names a fixed agent."""

    def test_open_sends_the_named_user_agent(self):
        import io
        seen = []

        def fake(req, timeout=None):
            seen.append((req, timeout))
            return io.BytesIO(b"{}")

        with mock.patch.object(order_beacon.urllib.request, "urlopen", fake):
            self.assertEqual(order_beacon._open("https://drand.cloudflare.com/public/1"), b"{}")
        (req, timeout), = seen
        self.assertIsInstance(req, order_beacon.urllib.request.Request, "the beacon read sends a Request, not a bare url")
        self.assertEqual(req.full_url, "https://drand.cloudflare.com/public/1")
        self.assertEqual(req.get_header("User-agent"), "gap-study-4-order-beacon", "the beacon read names its agent")
        self.assertEqual(timeout, order_beacon.TIMEOUT_S)


if __name__ == "__main__":
    unittest.main()
