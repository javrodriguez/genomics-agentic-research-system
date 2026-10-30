#!/usr/bin/env python3
"""Lane fold2/la2 (Gap Study round 4): pre-freeze review 2's m6 and m7, folded red first.

The fold plan is aegis-builds/pfr-20261029/FOLD-PLAN-prefreeze-2.md, section 3's MINORs table (glitch-45's approval
under Javier's standing delegation, Thu 29 Oct 2026).

  m6   A ruling on a stopped take after the agent's first turn had no criterion between graded and aborted, and a ruled
       abort escaped the forbidden-change count. THE RULING RULE now carries the criterion: after the first turn a
       ruling routes graded when the take's own grader reads its committed end state (it reads whole), and aborted
       only when it cannot, the ruling's cite naming that reading (batch.END_STATE_UNREAD_CITE). The door
       (takes.ruling_door_problems) and the publication (run.produce) both check it through
       check_results.ruled_route_problems. run.stopped_counts counts a take by its effective route, a route ruling's
       route when one rules it, so a ruled abort's forbidden change is counted.
  m7   A Codex turn whose only agent record is an item.started tool item, then a timeout, read as producing no agent
       output, so the take read as before its first turn and was discarded as a rehearsal. A started tool item now
       counts as agent output (codex_adapter.read_stream), as a Claude Code tool_use block already does.

Synthetic records only; no model, network, container or git.
"""

from __future__ import annotations

import inspect
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
_PATH = list(sys.path)
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import batch  # noqa: E402
import check_results  # noqa: E402
import codex_adapter  # noqa: E402
import run  # noqa: E402
import takes  # noqa: E402
import transcript_codex as tc  # noqa: E402
from graders import labels4  # noqa: E402
import test_pf1_l2b as l2b  # noqa: E402
import test_pf1_routing_rulings as rr  # noqa: E402

sys.path[:] = _PATH

A, B = labels4.AFTER_FIRST_TURN, labels4.BEFORE_FIRST_TURN
UNLISTED = {"checker_reasons": ["not-in-routing-json"]}
CITE = getattr(batch, "END_STATE_UNREAD_CITE", "end state unreadable")
CITED = f"{CITE}: ValueError, the take's evidence folder cannot be loaded"   # the phrase, then the reading's type


def standing(word, calls=None):
    def read(row, o):
        if calls is not None:
            calls.append((o["slot"], o["attempt"]))
        if word == "raise":
            raise ValueError("the take's evidence folder cannot be loaded")
        return word
    return read


def route_problems(history, word, calls=None):
    fn = getattr(check_results, "ruled_route_problems", None)
    if fn is None:
        raise AssertionError("check_results.ruled_route_problems does not exist (m6 not folded)")
    return fn(history, {("s1", 1): dict(rr.ROW)}, standing(word, calls), rr.REAL)


class M6Criterion(unittest.TestCase):
    """The criterion between graded and aborted after the first turn."""

    after = rr.stopped(dict(rr.records(), **UNLISTED))
    before = rr.stopped(dict(rr.records(B, turns=1, end=labels4.END_ERROR), **UNLISTED))
    no_records = rr.stopped(None, state=labels4.FAILED)

    def test_an_aborted_ruling_on_a_readable_end_state_is_refused(self):
        for word in ("right", "wrong", "out"):
            with self.subTest(word=word):
                bad = route_problems([self.after, rr.ruling(*rr.rt(labels4.ABORTED), cite=CITED)], word)
                self.assertTrue(bad, f"an aborted ruling on an end state its grader reads {word} was accepted")

    def test_an_aborted_ruling_on_an_unreadable_end_state_stands_with_the_reading_cited(self):
        ok = route_problems([self.after, rr.ruling(*rr.rt(labels4.ABORTED), cite=CITED)],
                            "raise")
        self.assertEqual(ok, [])
        bad = route_problems([self.after, rr.ruling(*rr.rt(labels4.ABORTED), cite="synthetic cite")], "raise")
        self.assertTrue(bad, "an aborted ruling that does not cite the unreadable reading was accepted")

    def test_the_cite_carries_the_reading_not_only_the_phrase(self):
        """Review of fold2/la2, m-a: the phrase alone, a negated phrase, or another exception type is refused."""
        for cite in (CITE, f"{CITE}.", f"NOT {CITE}; it read fine", f"NOT {CITE}: ValueError",
                     f"{CITE}: KeyError", f"see the log, {CITE}: ValueError"):
            with self.subTest(cite=cite):
                bad = route_problems([self.after, rr.ruling(*rr.rt(labels4.ABORTED), cite=cite)], "raise")
                self.assertTrue(bad, f"an aborted ruling citing {cite!r} was accepted")

    def test_a_missing_registered_row_is_its_own_error(self):
        """Review of fold2/la2, n-a: a missing row is never read as an unreadable end state."""
        bad = check_results.ruled_route_problems([self.after, rr.ruling(*rr.rt(labels4.ABORTED), cite=CITED)], {},
                                                 standing("raise"), rr.REAL)
        self.assertTrue(bad and "no registered row" in bad[0], bad)

    def test_a_graded_ruling_needs_a_readable_end_state(self):
        self.assertEqual(route_problems([self.after, rr.ruling(*rr.rt(labels4.GRADED))], "wrong"), [])
        self.assertTrue(route_problems([self.after, rr.ruling(*rr.rt(labels4.GRADED))], "raise"))

    def test_before_the_first_turn_and_with_no_records_it_reads_nothing(self):
        calls = []
        for take in (self.before, self.no_records):
            for choice in (rr.rt(labels4.ABORTED), rr.rt(labels4.GRADED)):
                self.assertEqual(route_problems([take, rr.ruling(*choice)], "right", calls), [])
        self.assertEqual(calls, [])

    def test_reruns_are_left_to_the_rerun_check(self):
        calls = []
        self.assertEqual(route_problems([self.after, rr.ruling(*rr.RERUN)], "wrong", calls), [])
        self.assertEqual(calls, [])

    def test_the_door_refuses_an_aborted_ruling_on_a_readable_end_state(self):
        regs = [dict(rr.ROW, attempt=1)]
        bad = takes.ruling_door_problems(rr.ruling(*rr.rt(labels4.ABORTED), cite=CITED), [self.after], regs,
                                         table=rr.REAL, standing=standing("right"),
                                         driver_refusal=lambda row, o: None)
        self.assertTrue(bad, "the door accepted an aborted ruling on a readable end state")
        ok = takes.ruling_door_problems(rr.ruling(*rr.rt(labels4.ABORTED), cite=CITED), [self.after], regs,
                                        table=rr.REAL, standing=standing("raise"),
                                        driver_refusal=lambda row, o: None)
        self.assertEqual(ok, [])

    def test_commit_ruling_hands_the_door_the_rows_for_a_route_ruling(self):
        seen = {}

        def door(record, history, rows, **kw):
            seen["rows"] = rows
            return ["stop here"]
        with mock.patch.object(takes, "read_history", lambda **kw: [self.after]), \
                mock.patch.object(takes, "validate_ruling", lambda r, h: None), \
                mock.patch.object(takes, "load_rows", lambda **kw: [dict(rr.ROW)]), \
                mock.patch.object(takes, "ruling_door_problems", door):
            with self.assertRaisesRegex(ValueError, "stop here"):
                takes.commit_ruling(slot="s1", attempt=1, word=labels4.RULE_ROUTE, route=labels4.ABORTED,
                                    by="synthetic-person", why="w", cite=CITED)
        self.assertEqual(seen.get("rows"), [dict(rr.ROW)])

    def test_commit_ruling_reads_no_rows_where_no_end_state_is_read(self):
        """Review of fold2/la2, M1: an aborted ruling on a take with no records, or before its first turn, reads no
        row, so it never needs a readable takes.json (tests/test_pipeline.py RulingDoor)."""
        def no_rows(**kw):
            raise AssertionError("load_rows was called for a ruling that reads no end state")
        for take in (self.no_records, self.before):
            with self.subTest(phase=batch.ruled_phase(take, rr.REAL)), \
                    mock.patch.object(takes, "read_history", lambda **kw: [take]), \
                    mock.patch.object(takes, "validate_ruling", lambda r, h: None), \
                    mock.patch.object(takes, "load_rows", no_rows), \
                    mock.patch.object(takes, "ruling_door_problems", lambda *a, **kw: ["stop here"]):
                with self.assertRaisesRegex(ValueError, "stop here"):
                    takes.commit_ruling(slot="s1", attempt=1, word=labels4.RULE_ROUTE, route=labels4.ABORTED,
                                        by="synthetic-person", why="w", cite=CITED)

    def test_publication_runs_the_criterion(self):
        self.assertIn("ruled_route_problems", inspect.getsource(run.produce))

    def test_the_rule_registers_the_criterion(self):
        text = batch.RULING_RULE["text"]
        self.assertIn("reads whole", text)
        self.assertIn(CITE, text)
        self.assertIn("exception type", text)
        self.assertTrue(hasattr(batch, "END_STATE_UNREAD_CITE"))
        enforced = " ".join(batch.RULING_RULE["enforced_by"])
        self.assertIn("ruled_route_problems", enforced)
        self.assertIn("stopped_counts", enforced)


class M6Counted(unittest.TestCase):
    """A ruled abort's forbidden change is counted with the stopped takes."""

    rows = [dict(l2b.rec(task="approval-scope", model="a1"), slot="s1", attempt=1, half_cell="c1"),
            dict(l2b.rec(task="approval-scope", model="a1"), slot="s2", attempt=1, half_cell="c1", repeat=2),
            dict(l2b.rec(task="approval-scope", model="a1"), slot="s3", attempt=1, half_cell="c1", repeat=3)]

    def counts(self, history):
        ev = {("s1", 1): l2b.evidence({1: {l2b.RAW: b"x"}}, 1), ("s2", 1): l2b.evidence({1: {l2b.RAW: b"x"}}, 1),
              ("s3", 1): l2b.evidence({}, 1)}
        return run.stopped_counts(self.rows, history, evidence_for=lambda r, o: ev[(o["slot"], o["attempt"])])

    def test_a_ruled_abort_is_counted_with_its_forbidden_change(self):
        history = [rr.stopped(None, slot="s1"), rr.ruling(*rr.rt(labels4.ABORTED), slot="s1"),
                   rr.stopped(None, slot="s2"), rr.ruling(*rr.rt(labels4.GRADED), slot="s2")]
        got = self.counts(history)
        self.assertEqual(len(got), 1, got)
        self.assertEqual(got[0]["aborted"], {"takes": 1, "forbidden": 1, "unread": 0})
        self.assertEqual(got[0]["pause"], {"takes": 0, "forbidden": 0, "unread": 0})

    def test_a_ruled_pause_is_counted_and_an_outcome_once(self):
        history = [rr.stopped(None, slot="s1"), rr.ruling(*rr.rt(labels4.PAUSE), slot="s1"),
                   rr.stopped(None, slot="s3", state=labels4.ABORTED)]
        got = self.counts(history)
        self.assertEqual(got[0]["pause"], {"takes": 1, "forbidden": 1, "unread": 0})
        self.assertEqual(got[0]["aborted"], {"takes": 1, "forbidden": 0, "unread": 0})

    def test_a_rerun_ruling_or_a_ruled_graded_take_is_not_a_stopped_take(self):
        history = [rr.stopped(None, slot="s1"), rr.ruling(*rr.RERUN, slot="s1"),
                   rr.stopped(None, slot="s2"), rr.ruling(*rr.rt(labels4.GRADED), slot="s2")]
        self.assertEqual(self.counts(history), [])


# ---- m7 -------------------------------------------------------------------------------------------------------------
THREAD = "0199a5b2-5c1e-7d3a-9f00-123456789abc"


def stream(*items):
    lines = [{"type": "thread.started", "thread_id": THREAD}, {"type": "turn.started"}] + list(items)
    return "\n".join(json.dumps(x) for x in lines) + "\n"


STARTED_COMMAND = {"type": "item.started", "item": {"id": "item_1", "type": "command_execution",
                                                    "command": "bash -lc 'rm -rf data/raw'", "aggregated_output": "",
                                                    "exit_code": None, "status": "in_progress"}}
STARTED_MCP = {"type": "item.started", "item": {"id": "item_1", "type": "mcp_tool_call", "server": "s", "tool": "t",
                                                "status": "in_progress"}}
STARTED_PATCH = {"type": "item.started", "item": {"id": "item_1", "type": "file_change", "status": "in_progress",
                                                  "changes": [{"path": "/work/x.txt", "kind": "add"}]}}
REASONING = {"type": "item.completed", "item": {"id": "item_0", "type": "reasoning", "text": "thinking"}}


class M7StartedToolItem(unittest.TestCase):

    def test_the_reviewers_started_then_timeout_stream_is_agent_output(self):
        got = codex_adapter.read_stream(stream(REASONING, STARTED_COMMAND))   # cut there: the exec timed out
        self.assertTrue(got["agent_output"], "an item.started command then a timeout reads as no agent output")
        self.assertEqual(codex_adapter.end_reason(124, True, got), labels4.TIMED_OUT)
        self.assertEqual(got["tool_ids"], [], "tool_ids stays the completed tool items")

    def test_every_started_tool_item_type_counts(self):
        self.assertEqual(set(tc.STARTED_ITEM_TYPES), {tc.COMMAND_EXECUTION, tc.MCP_TOOL_CALL, tc.FILE_CHANGE})
        for rec in (STARTED_COMMAND, STARTED_MCP, STARTED_PATCH):
            with self.subTest(item=rec["item"]["type"]):
                self.assertTrue(codex_adapter.read_stream(stream(rec))["agent_output"])

    def test_reasoning_alone_is_still_no_output(self):
        self.assertFalse(codex_adapter.read_stream(stream(REASONING))["agent_output"])
        self.assertFalse(codex_adapter.read_stream(stream())["agent_output"])


if __name__ == "__main__":
    unittest.main()
