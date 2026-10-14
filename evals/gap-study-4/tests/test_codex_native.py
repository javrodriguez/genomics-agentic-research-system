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
                                                           "message": f"model rerouted: {reroute} (HighRiskCyberActivity)"}})
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
            {"kind": "command", "status": "completed", "exit_code": 0, "output": "out", "marker_text": False},
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

    def test_the_marker_text_is_kept_and_named_never_read_as_truncation(self):
        m = cn()
        recs = rollout()
        marked = "head" + m.TRUNCATION_MARKER + "tail"
        recs[4]["payload"]["item"]["aggregated_output"] = marked
        out = m.project(raw(recs))[0]["output"][0]
        self.assertEqual((out["output"], out["marker_text"]), (marked, True))
        self.assertNotIn("truncated", out)

    def test_a_blank_interior_line_refuses(self):
        m = cn()
        for blank in ("", "   ", "\t"):
            with self.subTest(blank=blank):
                lines = raw(rollout()).decode().split("\n")
                lines.insert(3, blank)
                with self.assertRaises(m.ReaderRefused) as cm:
                    m.project("\n".join(lines).encode())
                self.assertIn("blank", str(cm.exception))
        self.assertEqual(len(m.project(raw(rollout()))), 1)          # the newline after the last record is no line
        with self.assertRaises(m.JoinRefused):
            m.read_exec(exec_stream().replace("\n", "\n  \n", 1))

    def test_a_whitespace_only_reasoning_summary_refuses_by_name(self):
        m = cn()
        recs = rollout()
        recs.insert(4, line(4, "event_msg", {"type": "item_completed", "thread_id": TID, "turn_id": "t1",
                                              "item": {"type": "Reasoning", "id": "r1", "summary_text": [" ", "\t"]},
                                              "completed_at_ms": 0}))
        for n, rec in enumerate(recs):
            rec["ordinal"] = n
        with self.assertRaises(m.ReaderRefused) as cm:
            m.project(raw(recs))
        self.assertIn("whitespace only", str(cm.exception))
        recs[4]["payload"]["item"]["summary_text"] = []                   # an empty summary: no output, as exec skips it
        self.assertEqual([o["kind"] for o in m.project(raw(recs))[0]["output"]], ["command", "agent-text"])

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
                               "agent_texts": ["Done."], "commands": 1, "marker_text": False,
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

    def test_an_agent_printed_marker_is_ordinary_text(self):
        """Review finding 3, the reviewer's witness: a short native output that merely contains the marker text is
        compared exactly; a disagreeing middle refuses, the same bytes join."""
        m = cn()
        recs = rollout()
        native = "A" + m.TRUNCATION_MARKER + "B"
        recs[4]["payload"]["item"]["aggregated_output"] = native
        turn = m.read_rollout(raw(recs))["turns"][0]
        with self.assertRaises(m.JoinRefused):
            m.join(turn, exec_stream(output="A<a different middle>B"), exit_code=0, session_id=TID)
        got = m.join(turn, exec_stream(output=native), exit_code=0, session_id=TID)
        self.assertTrue(got["complete"] and got["marker_text"])

    def test_an_output_over_the_limit_joins_only_as_the_writers_exact_truncation(self):
        """Addendum A: the writer keeps 32743 bytes of head and 32743 of tail around the 50-byte marker (budget 65486,
        the tail taking any odd byte), the head cut down and the tail start pushed up to a char boundary. Spelled
        here from the source's rule, never read from the module."""
        m = cn()
        marker = "\n... command output truncated for persistence ...\n"
        self.assertEqual(len(marker.encode()), 50)
        cases = [("x" * 70000, "x" * 32743 + marker + "x" * 32743),
                 ("a" + "x" * 69998 + "z", "a" + "x" * 32742 + marker + "x" * 32742 + "z"),
                 ("\u00e9" * 40000, "\u00e9" * 16371 + marker + "\u00e9" * 16371),     # 2-byte chars: both cuts round in
                 ("\u20ac" * 30000, "\u20ac" * 10914 + marker + "\u20ac" * 10914)]     # 3-byte chars
        for exec_out, writer in cases:
            with self.subTest(n=len(exec_out.encode())):
                recs = rollout()
                recs[4]["payload"]["item"]["aggregated_output"] = writer
                turn = m.read_rollout(raw(recs))["turns"][0]
                got = m.join(turn, exec_stream(output=exec_out), exit_code=0, session_id=TID)
                self.assertTrue(got["complete"] and got["marker_text"])
                for wrong in (writer[1:], writer[:-1], writer.replace(marker, marker.replace("output", "outputs")),
                              exec_out[:32744] + marker + exec_out[-32742:]):
                    recs[4]["payload"]["item"]["aggregated_output"] = wrong
                    turn = m.read_rollout(raw(recs))["turns"][0]
                    with self.assertRaises(m.JoinRefused):
                        m.join(turn, exec_stream(output=exec_out), exit_code=0, session_id=TID)

    def test_at_the_limit_the_output_is_kept_whole(self):
        m = cn()
        exact = "x" * (64 * 1024)
        marker = "\n... command output truncated for persistence ...\n"
        self.assertEqual(m.truncate_middle_with_marker(exact, 64 * 1024, marker), exact)      # truncate.rs:21-23
        self.assertEqual(m.truncate_middle_with_marker("abcdef", 4, "0123456789"), "abcd")   # :25-27, prefix that fits
        recs = rollout()
        recs[4]["payload"]["item"]["aggregated_output"] = exact
        turn = m.read_rollout(raw(recs))["turns"][0]
        self.assertTrue(m.join(turn, exec_stream(output=exact), exit_code=0, session_id=TID)["complete"])
        over = "x" * (64 * 1024 + 1)
        recs[4]["payload"]["item"]["aggregated_output"] = over
        turn = m.read_rollout(raw(recs))["turns"][0]
        with self.assertRaises(m.JoinRefused):              # the writer would have truncated it: never stored whole
            m.join(turn, exec_stream(output=over), exit_code=0, session_id=TID)

    def test_one_reroute_parser_and_two_different_reroutes_refuse(self):
        """Codex road review F2: read_exec reads reroutes with codex_adapter's one parser (the reason pinned, `from`
        the turn's requested model) and refuses two different reroutes in one exec."""
        m = cn()
        turn = m.read_rollout(raw(rollout()))["turns"][0]
        base = exec_stream(reroute="SYNTHETIC-MODEL -> OTHER-MODEL")
        self.assertEqual(m.join(turn, base, exit_code=0, session_id=TID)["served_model"], "OTHER-MODEL")
        for message in ("model rerouted: SYNTHETIC-MODEL -> OTHER-MODEL (HighRiskCyberActivity) trailing",
                        "model rerouted: SYNTHETIC MODEL -> OTHER-MODEL (HighRiskCyberActivity)",
                        "model rerouted: ANOTHER-MODEL -> OTHER-MODEL (HighRiskCyberActivity)",
                        "model rerouted: SYNTHETIC-MODEL -> OTHER-MODEL (Other)"):
            with self.subTest(message=message):
                text = base.replace("model rerouted: SYNTHETIC-MODEL -> OTHER-MODEL (HighRiskCyberActivity)", message)
                self.assertIsNone(m.join(turn, text, exit_code=0, session_id=TID)["served_model"])
        lines = base.splitlines(keepends=True)
        second = json.dumps({"type": "item.completed", "item": {"id": "item_s", "type": "error", "message":
                             "model rerouted: SYNTHETIC-MODEL -> THIRD-MODEL (HighRiskCyberActivity)"}}) + "\n"
        with self.assertRaises(m.JoinRefused) as cm:
            m.read_exec("".join(lines[:3] + [second] + lines[3:]), model="SYNTHETIC-MODEL")
        self.assertIn("two different models", str(cm.exception))
        import codex_adapter
        self.assertIs(codex_adapter.reroute_of, m.reroute_of)

    def test_unregistered(self):
        import vendor_provenance
        self.assertEqual(dict(vendor_provenance.NATIVE_SESSION_READERS), {})


if __name__ == "__main__":
    unittest.main()
