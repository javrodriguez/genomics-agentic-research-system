#!/usr/bin/env python3
"""Codex 0.162.1 native reader candidate and exec-stream join (unregistered). SYNTHETIC FIXTURES ONLY, written by hand
from the pinned source the rollout audit retained (gap4-codex-rollout-audit-20261014/src, blob-verified); never a CLI
run. Enum value spellings the audit marks as placeholders (source, base_instructions, approval_policy, sandbox_policy)
are carried raw and never accepted as evidence.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

LABEL = "SYNTHETIC"
TID = "00000000-0000-7000-8000-000000000001"


def cn():
    import codex_native
    return codex_native


def line(ordinal, type_, payload, **extra):
    return dict({"timestamp": f"2026-10-14T05:00:{ordinal:02d}.000Z", "ordinal": ordinal, "type": type_,
                 "payload": payload}, **extra)


def rollout(*, turns=1, cli="0.162.1", mode="paginated"):
    recs = [line(0, "session_meta", {"session_id": TID, "id": TID, "timestamp": "2026-10-14T05:00:00.000Z",
                                     "cwd": "/work/synthetic", "originator": "codex_exec", "cli_version": cli,
                                     "source": "exec", "model_provider": "openai",
                                     "base_instructions": {"text": LABEL}, "history_mode": mode})]
    for k in range(1, turns + 1):
        tid = f"t{k}"
        for type_, payload in (
                ("event_msg", {"type": "task_started", "turn_id": tid, "model_context_window": None,
                               "collaboration_mode_kind": "default"}),
                ("turn_context", {"turn_id": tid, "cwd": "/work/synthetic", "approval_policy": "never",
                                  "sandbox_policy": {"type": "read-only"}, "model": "SYNTHETIC-MODEL"}),
                ("event_msg", {"type": "item_completed", "thread_id": TID, "turn_id": tid,
                               "item": {"type": "UserMessage", "id": f"u{k}",
                                        "content": [{"type": "text", "text": f"sent {k}", "text_elements": []}]},
                               "completed_at_ms": 0}),
                ("event_msg", {"type": "item_completed", "thread_id": TID, "turn_id": tid,
                               "item": {"type": "CommandExecution", "id": f"c{k}", "command": ["ls", "-la"],
                                        "cwd": "/work/synthetic", "parsed_cmd": [], "source": "agent",
                                        "status": "completed", "aggregated_output": "out", "exit_code": 0},
                               "completed_at_ms": 0}),
                ("event_msg", {"type": "item_completed", "thread_id": TID, "turn_id": tid,
                               "item": {"type": "AgentMessage", "id": f"m{k}",
                                        "content": [{"type": "Text", "text": "Done"}, {"type": "Text", "text": "."}],
                                        "phase": "final_answer"}, "completed_at_ms": 0}),
                ("event_msg", {"type": "task_complete", "turn_id": tid, "last_agent_message": "Done."})):
            recs.append(line(len(recs), type_, payload))
    return recs


def raw(records):
    return "".join(json.dumps(r) + "\n" for r in records).encode()


def exec_stream(*, terminal="completed", text="Done.", output="out", reroute=None):
    recs = [{"type": "thread.started", "thread_id": TID}, {"type": "turn.started"},
            {"type": "item.completed", "item": {"id": "item_0", "type": "command_execution", "command": "ls -la",
                                                "aggregated_output": output, "exit_code": 0, "status": "completed"}},
            {"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": text}}]
    if reroute:
        recs.insert(2, {"type": "item.completed", "item": {"id": "item_r", "type": "error",
                                                           "message": f"model rerouted: {reroute} (HighRiskCyber)"}})
    if terminal == "completed":
        recs.append({"type": "turn.completed", "usage": {"input_tokens": 0, "cached_input_tokens": 0,
                                                         "cache_write_input_tokens": 0, "output_tokens": 0,
                                                         "reasoning_output_tokens": 0}})
    elif terminal == "failed":
        recs.append({"type": "turn.failed", "error": {"message": "turn failed"}})
    return "".join(json.dumps(r) + "\n" for r in recs)


class Reader(unittest.TestCase):
    def test_a_paginated_rollout_projects_each_turn(self):
        m = cn()
        facts = m.project(raw(rollout(turns=2)))
        self.assertEqual(len(facts), 2)
        f = facts[0]
        self.assertEqual((f["session_id"], f["version"], f["cwd"], f["requested_model"]),
                         (TID, "0.162.1", "/work/synthetic", "SYNTHETIC-MODEL"))
        self.assertIsNone(f["permission_mode"], "approval/sandbox spellings are placeholders, never accepted")
        self.assertEqual(f["sent"], "sent 1")
        self.assertEqual(f["output"], [
            {"kind": "command", "status": "completed", "exit_code": 0, "output": "out", "truncated": False},
            {"kind": "agent-text", "text": "Done."}])
        self.assertEqual(m.read_rollout(raw(rollout()))["turns"][0]["terminal"], "complete")

    def test_every_unproven_or_broken_line_refuses(self):
        m = cn()
        cases = []

        def case(why, edit):
            recs = rollout()
            edit(recs)
            cases.append((why, recs))

        case("cli_version", lambda r: r[0]["payload"].__setitem__("cli_version", "0.161.0"))
        case("history_mode", lambda r: r[0]["payload"].__setitem__("history_mode", "legacy"))
        case("ordinal", lambda r: r[2].__setitem__("ordinal", 9))
        case("ordinal", lambda r: r[2].pop("ordinal"))
        case("rollout line type", lambda r: r[2].__setitem__("type", "brand_new_kind"))
        case("never persisted", lambda r: r.insert(2, line(2, "event_msg", {"type": "error", "message": "x"})))
        case("never persisted", lambda r: r.insert(2, line(2, "event_msg", {"type": "model_reroute"})))
        case("TurnItem", lambda r: r[3]["payload"]["item"].__setitem__("type", "BrandNewItem"))
        case("first record", lambda r: r.insert(0, r.pop(1)))
        case("unknown key", lambda r: r[1].__setitem__("extra", 1))
        case("turn", lambda r: r[3]["payload"].__setitem__("turn_id", "t9"))
        case("thread", lambda r: r[3]["payload"].__setitem__("thread_id", "other"))
        case("closes no open turn", lambda r: r.insert(1, line(1, "event_msg", {"type": "task_complete",
                                                                                 "turn_id": "t0",
                                                                                 "last_agent_message": None})))
        for why, recs in cases:
            for n, rec in enumerate(recs):            # renumber after an insert, so only the intended fault stays
                if "ordinal" in rec and why != "ordinal":
                    rec["ordinal"] = n
            with self.subTest(why=why), self.assertRaises(m.ReaderRefused) as cm:
                m.project(raw(recs))
            self.assertIn(why, str(cm.exception))

    def test_a_line_upstream_would_skip_aborts_the_read(self):
        m = cn()
        text = raw(rollout()).decode().replace('"type": "turn_context"', '"type": "turn_context"', 1)
        bad = text.split("\n")
        bad.insert(3, "{not json")
        with self.assertRaises(m.ReaderRefused):
            m.project("\n".join(bad).encode())

    def test_truncation_markers_are_kept_and_flagged(self):
        m = cn()
        recs = rollout()
        marked = "head" + m.TRUNCATION_MARKER + "tail"
        recs[4]["payload"]["item"]["aggregated_output"] = marked
        out = m.project(raw(recs))[0]["output"][0]
        self.assertEqual((out["output"], out["truncated"]), (marked, True))

    def test_an_interrupted_or_open_turn_is_incomplete(self):
        m = cn()
        recs = rollout()
        recs[-1] = line(recs[-1]["ordinal"], "event_msg", {"type": "turn_aborted", "turn_id": "t1",
                                                             "reason": "interrupted"})
        self.assertEqual(m.read_rollout(raw(recs))["turns"][0]["terminal"], "aborted")
        self.assertEqual(m.read_rollout(raw(rollout()[:-1]))["turns"][0]["terminal"], "incomplete")


class Join(unittest.TestCase):
    def test_a_matching_turn_joins_with_the_served_model_unknown(self):
        m = cn()
        got = m.join(m.read_rollout(raw(rollout()))["turns"][0], exec_stream(), exit_code=0, session_id=TID)
        self.assertEqual(got, {"complete": True, "terminal": "complete", "served_model": None,
                               "agent_texts": ["Done."], "commands": 1, "truncated": False,
                               "command_text": "presentation-derived, not compared"})

    def test_each_disagreement_refuses(self):
        m = cn()
        turn = m.read_rollout(raw(rollout()))["turns"][0]
        for why, text, code, sid in (("agent text", exec_stream(text="Other."), 0, TID),
                                     ("command output", exec_stream(output="other"), 0, TID),
                                     ("thread", exec_stream(), 0, "other-thread"),
                                     ("terminal", exec_stream(terminal="failed"), 1, TID),
                                     ("no terminal event with exit 0", exec_stream(terminal=None), 0, TID)):
            with self.subTest(why=why), self.assertRaises(m.JoinRefused) as cm:
                m.join(turn, text, exit_code=code, session_id=sid)
            self.assertIn(why, str(cm.exception))

    def test_interrupted_is_incomplete_and_a_reroute_is_served_model_evidence(self):
        m = cn()
        recs = rollout()
        recs[-1] = line(recs[-1]["ordinal"], "event_msg", {"type": "turn_aborted", "turn_id": "t1",
                                                             "reason": "interrupted"})
        got = m.join(m.read_rollout(raw(recs))["turns"][0], exec_stream(terminal=None), exit_code=1, session_id=TID)
        self.assertEqual((got["complete"], got["terminal"]), (False, "aborted"))
        got = m.join(m.read_rollout(raw(rollout()))["turns"][0],
                     exec_stream(reroute="SYNTHETIC-MODEL -> OTHER-MODEL"), exit_code=0, session_id=TID)
        self.assertEqual(got["served_model"], "OTHER-MODEL")

    def test_a_truncated_native_output_compares_by_prefix_and_suffix(self):
        m = cn()
        recs = rollout()
        recs[4]["payload"]["item"]["aggregated_output"] = "head" + m.TRUNCATION_MARKER + "tail"
        turn = m.read_rollout(raw(recs))["turns"][0]
        try:
            got = m.join(turn, exec_stream(output="head and the whole middle tail"), exit_code=0, session_id=TID)
        except m.JoinRefused as exc:
            self.fail(f"a truncated native output must compare by prefix and suffix: {exc}")
        self.assertTrue(got["truncated"])
        with self.assertRaises(m.JoinRefused):
            m.join(turn, exec_stream(output="other and tail"), exit_code=0, session_id=TID)

    def test_unregistered(self):
        import vendor_provenance
        self.assertEqual(dict(vendor_provenance.NATIVE_SESSION_READERS), {})


if __name__ == "__main__":
    unittest.main()
