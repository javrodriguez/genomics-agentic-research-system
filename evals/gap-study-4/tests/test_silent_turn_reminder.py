#!/usr/bin/env python3
"""The silent-turn reminder OFF, a parity condition on every claude-code take (glitch-b5's ruling, 16 Oct 2026; CP6
walks w126, w128 and w130, claude-opus-5-5, held on "unknown attachment type: 'silent_turn_reminder'").

The facts the ruling rests on (a read-only static read of the pinned 2.1.296 by a separate agent): Claude Code writes
an attachment {type: silent_turn_reminder, text: a fixed constant} on the main agent after 5 silent tool-only API
turns, at most 3 per stretch, DEFAULT-ON for models carrying the opus 5.5 prompt bundle (claude-opus-5-5); the switch
CLAUDE_CODE_SILENT_TURN_REMINDER is a triBool ("0", "false", "no", "off" read as false) checked before every gate.
Round 3 (2.1.267 and 2.1.280, which carry the path) never received one in 64 transcripts. So, as for the bash-first
steer, the study turns it off on every take and the checker proves it per turn:

  T-env      box/run_take sets CLAUDE_CODE_SILENT_TURN_REMINDER "0" in the take's exec env (TAKE_ENV) and in the one
             inline --settings env (claude_study_settings), so each turn's launch journal records it; no
             CLAUDE_CODE_MODEL_CAPABILITIES is set.
  T-check    check_take.steer_condition_problems refuses [harness-condition-violated] a turn whose journal does not set
             the switch to a string the triBool reads as false: unset, "1", a JSON boolean, or only a misspelled
             name; "0", "false", "no", "off" (any case, padded) pass.
  T-view     the transcript view still refuses a silent_turn_reminder attachment: a leak through the switch holds.
  T-draft    the draft records the switch as a parity condition, with its facts.
  T-witness  each clause dropped in memory turns a check red.

Synthetic fixtures only.
"""

from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "box"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_take as ct  # noqa: E402
import transcript_view as tv  # noqa: E402

SWITCH = "CLAUDE_CODE_SILENT_TURN_REMINDER"
DENY = ["RemoteTrigger", "SendMessage", "ListAgents"]
UNSET = object()


def settings(value="0", name=SWITCH):
    env = {"CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "1", "CLAUDE_CODE_THRIFTY_SONIC": "false"}
    if value is not UNSET:
        env[name] = value
    return json.dumps({"availableModels": ["m"], "crossSessionInbound": "refuse", "env": env, "fallbackModel": [],
                       "permissions": {"deny": DENY}, "switchModelsOnFlag": False}, sort_keys=True,
                      separators=(",", ":"))


def take(value="0", name=SWITCH) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "transcript.jsonl").write_text(json.dumps({"type": "user", "message": {"content": "Go."}}) + "\n")
    (d / "turn-1.jsonl").write_text("")
    (d / "turn-1.jsonl.launch.json").write_text(json.dumps({
        "schema": 1, "harness": "claude-code", "stream": str(d / "turn-1.jsonl"),
        "argv": ["claude", "-p", "x", "--model", "m", "--disallowedTools", *DENY, "--settings", settings(value, name)]}))
    return d / "transcript.jsonl"


def env_problems(rt=None) -> list:
    if rt is None:
        from box import run_take as rt
    out = []
    env = rt.TAKE_ENV[rt.CLAUDE_CODE]
    if env.get(SWITCH) != "0":
        out.append(f"T-env: TAKE_ENV sets {SWITCH} to {env.get(SWITCH)!r}")
    if json.loads(rt.claude_study_settings("claude-opus-5-5"))["env"].get(SWITCH) != "0":
        out.append("T-env: the inline settings do not set the switch off")
    if ct.STEER_REQUIRED != {**rt.BASH_FIRST_STEER_ENV, **rt.SILENT_TURN_REMINDER_ENV}:
        out.append("T-env: the checker's exact strings are not the ones run_take sets")
    if "CLAUDE_CODE_MODEL_CAPABILITIES" in env or "CLAUDE_CODE_MODEL_CAPABILITIES" in \
            json.loads(rt.claude_study_settings("claude-opus-5-5"))["env"]:
        out.append("T-env: CLAUDE_CODE_MODEL_CAPABILITIES is set; the ruling sets one switch")
    return out


def check_problems(mod=None) -> list:
    mod = mod or ct
    out = []
    got = mod.steer_condition_problems(take("0"))
    if got:
        out.append(f"T-check '0': refused {got}")
    # review r11 NIT (glitch-b5, 16 Oct 2026): exactly "0", the string the study sets; no strip, no other spelling
    for name, kw in (("padded", {"value": " 0"}), ("false", {"value": "false"}), ("off", {"value": "off"}),
                     ("unset", {"value": UNSET}), ("on", {"value": "1"}), ("true", {"value": "true"}),
                     ("a JSON boolean", {"value": False}), ("an empty string", {"value": ""}),
                     ("a misspelled name", {"name": SWITCH + "S"})):
        got = mod.steer_condition_problems(take(**kw))
        if mod.reason_ids(got)[:1] != ["harness-condition-violated"] or not any(SWITCH in g for g in got):
            out.append(f"T-check {name}: {got}")
    return out


def view_problems(view=tv) -> list:
    rec = {"type": "attachment", "attachment": {"type": "silent_turn_reminder", "text": "x"}}
    try:
        view.events(view.ROUND3_HARNESS, [json.dumps({"type": "user", "message": {"content": "Go."}}), json.dumps(rec)])
        return ["T-view: a silent_turn_reminder attachment was admitted"]
    except view.ViewError:
        return []


def draft_problems() -> list:
    draft = json.loads((HERE / "prereg-draft.json").read_text())
    notes = [n for n in draft["harness_furniture_ruling"].get("parity_notes", []) if n.get("of") == "silent_turn_reminder"]
    if len(notes) != 1:
        return ["T-draft: no single silent_turn_reminder parity note"]
    out = []
    for word in (SWITCH, '"0"', "Every claude-code take sets", "5 silent tool-only", "at most 3", "claude-opus-5-5",
                 "default-on", "0 of 64", "2.1.267 and 2.1.280", "harness-condition-violated", "still refuses",
                 "RULED 16 Oct (glitch-b5)", "w126"):
        if word not in notes[0]["text"]:
            out.append(f"T-draft: the note does not say {word!r}")
    return out


def mutant(mod, old, new):
    src = Path(mod.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutation site occurs {src.count(old)} times in {mod.__file__}: {old!r}")
    m = types.ModuleType(mod.__name__ + "_mutant")
    m.__file__ = mod.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), mod.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    return m


class TheSilentTurnReminder(unittest.TestCase):
    def test_t_env(self):
        self.assertEqual(env_problems(), [])

    def test_t_check(self):
        self.assertEqual(check_problems(), [])

    def test_t_view(self):
        self.assertEqual(view_problems(), [])

    def test_t_draft(self):
        self.assertEqual(draft_problems(), [])

    def test_t_witnesses(self):
        cases = (
            ("the switch unread", lambda: check_problems(mutant(
                ct, "    for switch in (STEER_SWITCH, SILENT_TURN_SWITCH):", "    for switch in (STEER_SWITCH,):"))),
            ("another switch name", lambda: check_problems(mutant(
                ct, 'SILENT_TURN_SWITCH = "CLAUDE_CODE_SILENT_TURN_REMINDER"',
                'SILENT_TURN_SWITCH = "CLAUDE_CODE_SILENT_TURN_REMINDERS"'))),
        )
        for name, run in cases:
            with self.subTest(witness=name):
                try:
                    got = run()
                except Exception as e:  # noqa: BLE001
                    got = [f"raised {type(e).__name__}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
                self.assertTrue(got, name)
        with mock.patch.object(tv, "CC_ATTACHMENT_TYPES", tv.CC_ATTACHMENT_TYPES + ("silent_turn_reminder",)):
            got = view_problems()
        print(f"\nWITNESS the view admits it: {'red' if got else 'NOT KILLED'}", end=" ", file=sys.stderr)
        self.assertTrue(got, "the view admits it")


if __name__ == "__main__":
    unittest.main()
