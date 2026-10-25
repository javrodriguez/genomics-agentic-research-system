#!/usr/bin/env python3
"""The bash-first steer OFF is a study condition the checker verifies on every turn, fail closed (glitch-6b's rulings,
15 Oct 2026, approved by Javier's "Your call sounds good"; proposed by the box lane, made fail closed by glitch-6b's
ruling of the same day).

Every claude-code take runs with CLAUDE_CODE_THRIFTY_SONIC=false (box/run_take.BASH_FIRST_STEER_ENV), in the exec's
pairs and in the one inline --settings env that each turn's launch journal (turn-N.jsonl.launch.json) records. Claude
Code 2.1.296 then never emits its auto_mode attachment (the Bash-first steer). So:

  S-violated   every turn sets the switch "false" and the transcript carries an auto_mode attachment: one
               `[transcript-mismatch]` refusal naming the count (lane pf1-l3: the transcript alone shows it, so the
               records disagree; review fb354328 finding 1, 24 Oct 2026).
  S-clean      every turn sets it to a string the binary reads as false ("false", "0", "no", "off", any case, padded)
               and no auto_mode record: nothing.
  S-closed     fail closed: a turn whose settings do not set the switch, set it on, set a JSON boolean or any other
               value; a turn stream with no journal; no journal at all; two inline --settings: each refuses; and an
               auto_mode record refuses whatever the journals say.
  S-prompt     a --settings that is the prompt after -p is never read as the settings.
  S-unreadable a launch journal that is not JSON, or a --settings value that is not a JSON object, raises
               CheckRefused rather than guess.
  S-wired      check4 and check4_walk both add these problems for the take.
  S-witness    each clause dropped in memory turns a check red.

Synthetic fixtures only.
"""

from __future__ import annotations

import ast
import contextlib
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

import check_take as ct  # noqa: E402

SWITCH = "CLAUDE_CODE_THRIFTY_SONIC"
DENY = ["RemoteTrigger", "SendMessage", "ListAgents"]
AUTO = {"type": "attachment", "isSidechain": False,
        "attachment": {"type": "auto_mode", "autoModeConsentFlow": False, "bashFirst": True,
                       "bashFirstSteer": "relaxed", "steerOnly": True, "bypass": True},
        "rendered": [{"content": "While bypass permissions mode is active:\n\nSynthetic steer."}],
        "renderedRole": "system"}
USER = {"type": "user", "message": {"content": "Run stage 00."}}
UNSET = object()


def settings(value=UNSET):
    """The study's inline settings as box/run_take.claude_study_settings writes them, the switch as given."""
    env = {"CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "1", SWITCH: "false", "CLAUDE_CODE_SILENT_TURN_REMINDER": "0"}   # + glitch-b5's parity switch
    if value is UNSET:
        pass
    elif value is None:
        del env[SWITCH]
    else:
        env[SWITCH] = value
    return json.dumps({"availableModels": ["m"], "crossSessionInbound": "refuse", "env": env, "fallbackModel": [],
                       "permissions": {"deny": DENY}, "switchModelsOnFlag": False},
                      sort_keys=True, separators=(",", ":"))


def journal(value=UNSET, extra=()):
    return {"schema": 1, "harness": "claude-code",
            "argv": ["claude", "-p", "x", "--model", "m", "--disallowedTools", *DENY, "--settings", settings(value),
                     *extra, "--session-id", "s"]}


def take(tmp: Path, records, switch_values, streams=None) -> Path:
    """A take folder: the transcript, one turn stream per value (or `streams`), one journal per value."""
    path = tmp / "transcript.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    for n in range(1, (len(switch_values) if streams is None else streams) + 1):
        (tmp / f"turn-{n}.jsonl").write_text("")
    for n, v in enumerate(switch_values, 1):
        doc = dict(v) if isinstance(v, dict) else journal(v)
        doc.setdefault("stream", f"/synthetic/host/take/turn-{n}.jsonl")   # r5 NIT (b): bound to its own turn
        (tmp / f"turn-{n}.jsonl.launch.json").write_text(json.dumps(doc))
    return path


@contextlib.contextmanager
def source_mutant(old: str, new: str):
    """check_take's steer_condition_problems taken from a copy of its source with one anchored edit, patched in."""
    src = Path(ct.__file__).read_text()
    assert src.count(old) == 1, f"anchor occurs {src.count(old)} times: {old!r}"
    m = types.ModuleType("check_take_witness")
    m.__file__ = ct.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), ct.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    with mock.patch.object(ct, "steer_condition_problems", m.steer_condition_problems):
        yield


class Steer(unittest.TestCase):
    def run_case(self, records, values, streams=None):
        with tempfile.TemporaryDirectory() as d:
            return ct.steer_condition_problems(take(Path(d), records, values, streams))

    def check_violated(self):
        got = self.run_case([USER, AUTO, USER, AUTO], [UNSET, UNSET])
        # lane pf1-l3 (the lane orchestrator's ruling on review fb354328 finding 1, 24 Oct 2026): the auto_mode record is
        # the agent-writable transcript's alone, so it is transcript-mismatch (aborted), never a harness condition
        if len(got) != 1 or not got[0].startswith("[transcript-mismatch] ") or "2 auto_mode" not in got[0]:
            return [f"S-violated: {got}"]
        if ct.reason_ids(got) != ["transcript-mismatch"]:
            return ["S-violated: not routable by its id"]
        return []

    def check_quiet(self):
        out = []
        # review r11 NIT (glitch-b5, 16 Oct 2026): only the exact string the study sets, "false", proves the switch off
        for name, records, values in (("S-clean", [USER], [UNSET]), ("S-clean two turns", [USER, USER], [UNSET] * 2)):
            got = self.run_case(records, values)
            if got:
                out.append(f"{name}: {got}")
        return out

    def check_closed(self):
        out = []
        cases = {
            "the switch not set": ([USER], [None], None),
            "the switch on": ([USER], ["1"], None),
            "the switch true": ([USER], ["true"], None),
            "a JSON false": ([USER], [False], None),
            "an empty string": ([USER], [""], None),
            "another off spelling, 0": ([USER], ["0"], None),
            "another off spelling, off": ([USER], ["off"], None),
            "another off spelling, no": ([USER], ["no"], None),
            "padded and upper case": ([USER], [" FALSE "], None),
            "capitalised": ([USER], ["False"], None),
            "auto_mode with no journal": ([USER, AUTO], [], 1),
            "auto_mode with the switch unset": ([USER, AUTO], [None], None),
            "one turn of two not set": ([USER], [UNSET, None], None),
            "a stream with no journal": ([USER], [UNSET], 2),
            "no journal at all": ([USER], [], 1),
            "no journal and no stream": ([USER], [], 0),
            "two inline settings": ([USER], [journal(extra=("--settings", settings()))], None),
        }
        for name, (records, values, streams) in cases.items():
            got = self.run_case(records, values, streams)
            if ct.reason_ids(got)[:1] != ["harness-condition-violated"]:
                out.append(f"S-closed {name}: {got}")
        return out

    def check_prompt(self):
        # the prompt is the word "--settings": the study's settings after it are the prompt's neighbour, not a value
        smuggled = journal()
        smuggled["argv"] = ["claude", "-p", "--settings", settings(), "--model", "m", "--disallowedTools", *DENY]
        got = self.run_case([USER], [smuggled])
        # glitch-b5's parity switch (16 Oct 2026): the smuggled settings set neither switch, so each is named
        return [] if set(ct.reason_ids(got)) == {"harness-condition-violated"} else [f"S-prompt: {got}"]

    def check_unreadable(self):
        out = []
        for name, text in (("not json", "{"), ("settings not an object", json.dumps(
                {"argv": ["claude", "-p", "x", "--settings", "[]"]})), ("argv not a list", json.dumps({"argv": "claude"}))):
            with tempfile.TemporaryDirectory() as d:
                path = take(Path(d), [AUTO], [])
                (Path(d) / "turn-1.jsonl.launch.json").write_text(text)
                try:
                    ct.steer_condition_problems(path)
                    out.append(f"S-unreadable: {name} was read")
                except ct.CheckRefused:
                    pass
        return out

    def check_wired(self):
        tree = ast.parse(Path(ct.__file__).read_text())
        out = []
        for fn in ("check4", "check4_walk"):
            body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn)
            calls = {c.func.id for c in ast.walk(body) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
            if "steer_condition_problems" not in calls:
                out.append(f"S-wired: {fn} does not add the steer condition's problems")
        return out

    def test_violated(self):
        self.assertEqual(self.check_violated(), [])

    def test_quiet(self):
        self.assertEqual(self.check_quiet(), [])

    def test_closed(self):
        self.assertEqual(self.check_closed(), [])

    def test_prompt(self):
        self.assertEqual(self.check_prompt(), [])

    def test_unreadable(self):
        self.assertEqual(self.check_unreadable(), [])

    def test_wired(self):
        self.assertEqual(self.check_wired(), [])

    def test_witnesses(self):
        all_checks = lambda: (self.check_violated() + self.check_quiet() + self.check_closed()  # noqa: E731
                              + self.check_prompt() + self.check_unreadable())
        mutants = (
            ("another required value", lambda: mock.patch.dict(ct.STEER_REQUIRED, {ct.STEER_SWITCH: "0"})),
            ("a stripped, case-folded compare", lambda: source_mutant(
                "value == STEER_REQUIRED[switch]):", "value.strip().lower() == STEER_REQUIRED[switch]):")),
            ("switch absent read as off", lambda: source_mutant(
                '            if not (isinstance(value, str) and value == STEER_REQUIRED[switch]):',
                '            if value is not None and not (isinstance(value, str) and value == STEER_REQUIRED[switch]):')),
            ("not a string read as off", lambda: source_mutant(
                '            if not (isinstance(value, str) and value == STEER_REQUIRED[switch]):',
                '            if not (str(value).lower() == STEER_REQUIRED[switch]):')),
            ("another switch name", lambda: mock.patch.object(ct, "STEER_SWITCH", "CLAUDE_CODE_OTHER")),
            ("another attachment type", lambda: mock.patch.object(ct, "AUTO_MODE_ATTACHMENT", "auto_mode_exit")),
            ("missing journal read as nothing", lambda: mock.patch.object(ct, "_journal_gaps", lambda *a: [])),
            ("auto_mode only under the switch", lambda: source_mutant(
                # lane pf1-l3: the anchor follows the host-shown split (the closure check of 8cf492b2, 24 Oct 2026)
                '    count = _auto_mode_records(path)\n    if count and steer_on:',
                '    count = _auto_mode_records(path) if journals and not bad else 0\n    if count and steer_on:')),
            ("the prompt read as flags", lambda: mock.patch.object(ct, "_JOURNAL_PRINT_FLAGS", ())),
        )
        for name, ctx in mutants:
            with ctx():
                try:
                    got = all_checks()
                except Exception as e:  # noqa: BLE001 - a mutant that crashes a check is red too
                    got = [f"raised {type(e).__name__}"]
            print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
            self.assertTrue(got, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
