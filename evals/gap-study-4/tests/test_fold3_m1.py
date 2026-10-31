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
        self.assertIn("0 turns while its ledger records 1", rec["unread"], "M1-refuse")

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


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                          "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"git {args}: {out.stderr}")
    return out.stdout.strip()


@contextlib.contextmanager
def seed_repo(*, register=True, voided=False, blindness="right"):
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
            (review_dir / "rounds.json").write_text(json.dumps({"rows": [row]}) + "\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "register round 1")
            sid = takes.session_id_for(git(repo, "rev-parse", "HEAD"))
        if blindness == "right":
            (review_dir / "prefreeze-1-blindness.txt").write_text(f"session {sid}\n")
        elif blindness == "other":
            (review_dir / "prefreeze-1-blindness.txt").write_text(f"session {takes.session_id_for('0' * 40)}\n")
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
        self.assertEqual(self.problems(), ([], f"{study.STUDY_REL}/{study.REVIEW_DIR}/prefreeze-1.md"), "m2-register")

    def test_an_unregistered_review_never_seeds(self):
        bad, name = self.problems(register=False)
        self.assertTrue(bad and name is None, "m2-register: a review with no row seeds the freeze")

    def test_a_voided_round_never_seeds(self):
        bad, _ = self.problems(voided=True)
        self.assertTrue(bad and "voided" in bad[0], f"m2-register: {bad}")

    def test_no_blindness_record_never_seeds(self):
        bad, _ = self.problems(blindness=None)
        self.assertTrue(bad and "blindness" in bad[0], f"m2-register: {bad}")

    def test_another_session_never_seeds(self):
        bad, _ = self.problems(blindness="other")
        self.assertTrue(bad and "does not name the session id" in bad[0], f"m2-register: {bad}")


if __name__ == "__main__":
    unittest.main()
