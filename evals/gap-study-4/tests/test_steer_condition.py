#!/usr/bin/env python3
"""The bash-first steer OFF is a study condition the checker verifies (glitch-6b's ruling, 15 Oct 2026, approved by
Javier's "Your call sounds good"; proposed by the box lane for the harness lane to route).

Every claude-code take runs with CLAUDE_CODE_THRIFTY_SONIC=false (box/run_take.BASH_FIRST_STEER_ENV), in the exec's
pairs and in the inline --settings env that each turn's launch journal (turn-N.jsonl.launch.json) records. Claude Code
2.1.296 then never emits its auto_mode attachment (the Bash-first steer). A silent failure of that switch must not
pass, so:

  S-violated   a take whose launch journals set the switch off and whose transcript carries an auto_mode
               attachment yields one `[harness-condition-violated]` refusal naming the count.
  S-clean      the switch off and no auto_mode record: nothing.
  S-not-set    no journal sets the switch (the product default, e.g. the 15 Oct walks): this rule says nothing;
               the switch on: nothing either (another condition, not this one's).
  S-disagree   turns that disagree on the switch refuse: the condition did not hold for the whole take.
  S-unreadable a launch journal that is not JSON, or a --settings value that is not a JSON object, raises
               CheckRefused rather than guess.
  S-wired      check4 and check4_walk both add these problems for the take.
  S-witness    each clause dropped in memory turns a check red.

Synthetic fixtures only.
"""

from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import check_take as ct  # noqa: E402

SWITCH = "CLAUDE_CODE_THRIFTY_SONIC"
AUTO = {"type": "attachment", "isSidechain": False,
        "attachment": {"type": "auto_mode", "autoModeConsentFlow": False, "bashFirst": True,
                       "bashFirstSteer": "relaxed", "steerOnly": True, "bypass": True},
        "rendered": [{"content": "While bypass permissions mode is active:\n\nSynthetic steer."}],
        "renderedRole": "system"}
USER = {"type": "user", "message": {"content": "Run stage 00."}}


def settings(value):
    env = {"CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "1"}
    if value is not None:
        env[SWITCH] = value
    return json.dumps({"availableModels": ["m"], "env": env, "fallbackModel": [], "switchModelsOnFlag": False},
                      sort_keys=True, separators=(",", ":"))


def journal(value):
    return {"schema": 1, "harness": "claude-code",
            "argv": ["claude", "-p", "x", "--model", "m", "--settings", settings(value), "--session-id", "s"]}


def take(tmp: Path, records, switch_values) -> Path:
    path = tmp / "transcript.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    for n, v in enumerate(switch_values, 1):
        (tmp / f"turn-{n}.jsonl").write_text("")
        (tmp / f"turn-{n}.jsonl.launch.json").write_text(json.dumps(journal(v)))
    return path


class Steer(unittest.TestCase):
    def run_case(self, records, values):
        with tempfile.TemporaryDirectory() as d:
            return ct.steer_condition_problems(take(Path(d), records, values))

    def check_violated(self):
        got = self.run_case([USER, AUTO, USER, AUTO], ["false", "false"])
        if len(got) != 1 or not got[0].startswith("[harness-condition-violated] ") or "2 auto_mode" not in got[0]:
            return [f"S-violated: {got}"]
        if ct.reason_ids(got) != ["harness-condition-violated"]:
            return ["S-violated: not routable by its id"]
        for off in ("0", "off", " FALSE "):
            if not self.run_case([AUTO], [off]):
                return [f"S-violated: {off!r} not read as off"]
        return []

    def check_quiet(self):
        out = []
        for name, records, values in (("S-clean", [USER], ["false"]), ("S-not-set", [AUTO], [None]),
                                      ("S-on", [AUTO], ["1"]), ("S-no-journal", [AUTO], [])):
            got = self.run_case(records, values)
            if got:
                out.append(f"{name}: {got}")
        return out

    def check_disagree(self):
        got = self.run_case([USER], ["false", None])
        return [] if ct.reason_ids(got) == ["harness-condition-violated"] else [f"S-disagree: {got}"]

    def check_unreadable(self):
        out = []
        for name, text in (("not json", "{"), ("settings not an object", json.dumps(
                {"argv": ["claude", "--settings", "[]"]})), ("argv not a list", json.dumps({"argv": "claude"}))):
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

    def test_disagree(self):
        self.assertEqual(self.check_disagree(), [])

    def test_unreadable(self):
        self.assertEqual(self.check_unreadable(), [])

    def test_wired(self):
        self.assertEqual(self.check_wired(), [])

    def test_witnesses(self):
        all_checks = lambda: (self.check_violated() + self.check_quiet() + self.check_disagree()  # noqa: E731
                              + self.check_unreadable())
        mutants = (
            ("no off values", lambda: mock.patch.object(ct, "STEER_OFF_VALUES", ())),
            ("another switch name", lambda: mock.patch.object(ct, "STEER_SWITCH", "CLAUDE_CODE_OTHER")),
            ("every value read as off", lambda: mock.patch.object(ct, "STEER_OFF_VALUES",
                                                                  ("0", "false", "no", "off", "1", ""))),
            ("another attachment type", lambda: mock.patch.object(ct, "AUTO_MODE_ATTACHMENT", "auto_mode_exit")),
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
