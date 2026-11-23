#!/usr/bin/env python3
"""OD201 secondary analysis (branch analysis/reader-gap-secondary only): the patched claude-code parser that
transcript_view_secondary installs at runtime, on fakes. Each admitted shape reads; each near-miss is still refused; the
null mutant (no install: the frozen parser) refuses every admitted fake and turns the admitted suite red; on fakes
without the new shapes the two parsers give the same events; transcript_view.py is byte-identical to the frozen file;
and the install is undone on exit.

Run from this folder: python3 -B -m unittest test_reader_gap_secondary
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY))
import transcript_view as _tv  # noqa: E402
import transcript_view_secondary as sec  # noqa: E402

BASE = "1e097b2f5f99a4d5134234d5553dcb8cdaff45ca"     # the post-run head the branch starts from (the frozen reader)
REL = "evals/gap-study-4/transcript_view.py"


class Reader:
    """transcript_view's names, with every reading call made under the patched parser (patched=True) or the frozen one."""

    def __init__(self, patched: bool):
        self.patched = patched

    def __getattr__(self, name):
        return getattr(_tv, name)

    def _call(self, fn, *a):
        if self.patched:
            with sec.installed():
                return fn(*a)
        return fn(*a)

    def events(self, *a):
        return self._call(_tv.events, *a)

    def harness_types(self, *a):
        return self._call(_tv.harness_types, *a)

    @property
    def PARSERS(self):
        return {"claude-code": sec.SecondaryClaudeCodeParser() if self.patched else sec.FROZEN_PARSER}


tv = Reader(patched=True)
FROZEN = Reader(patched=False)


def j(o) -> str:
    return json.dumps(o)


OPERATOR = j({"type": "user", "message": {"role": "user", "content": "please do the task"}})


def assistant(*blocks) -> str:
    return j({"type": "assistant", "isSidechain": False, "message": {"model": "m", "content": list(blocks)}})


def call(cid, name, inp) -> dict:
    return {"type": "tool_use", "id": cid, "name": name, "input": inp}


def result(cid, text="ok") -> str:
    return j({"type": "user", "isSidechain": False,
              "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": cid, "content": text}]}})


def companion(sid, **over) -> str:
    rec = {"type": "user", "isMeta": True, "turnCompanion": True, "isSidechain": False, "sourceToolUseID": sid,
           "message": {"role": "user", "content": [{"type": "text", "text": "Base directory for this skill: /x"}]}}
    rec.update(over)
    return j({k: v for k, v in rec.items() if v is not DROP})


DROP = object()


def perms(**over) -> str:
    a = {"type": "command_permissions", "allowedTools": ["Bash(git:*)", "Read"]}
    a.update(over)
    return j({"type": "attachment", "isSidechain": False, "attachment": {k: v for k, v in a.items() if v is not DROP}})


SKILL = call("s1", "Skill", {"skill": "review", "args": "the diff"})

# name: lines that the patched reader must read (each holds one admitted shape)
ADMITTED = {
    "write-file_text": [OPERATOR, assistant(call("w1", "Write", {"file_path": "/w/a.txt", "file_text": "x"})),
                        result("w1")],
    "skill-call": [OPERATOR, assistant(SKILL), result("s1")],
    "skill-call-no-args": [OPERATOR, assistant(call("s1", "Skill", {"skill": "review"})), result("s1")],
    "skill-companion": [OPERATOR, assistant(SKILL), result("s1"), companion("s1")],
    "skill-companion-before-result": [OPERATOR, assistant(SKILL), companion("s1"), result("s1")],
    "command-permissions": [OPERATOR, assistant(SKILL), result("s1"), companion("s1"), perms()],
    "command-permissions-empty": [OPERATOR, perms(allowedTools=[])],
}

# name: lines the patched reader must still refuse
REFUSED = {
    "write-both-content-and-file_text": [OPERATOR, assistant(call("w1", "Write", {"file_path": "/w/a", "content": "x",
                                                                                  "file_text": "x"}))],
    "write-unknown-key": [OPERATOR, assistant(call("w1", "Write", {"file_path": "/w/a", "text": "x"}))],
    "skill-extra-key": [OPERATOR, assistant(call("s1", "Skill", {"skill": "r", "args": "a", "model": "m"}))],
    "companion-no-skill-call": [OPERATOR, companion("s1")],
    "companion-of-a-bash-call": [OPERATOR, assistant(call("b1", "Bash", {"command": "ls"})), result("b1"),
                                 companion("b1")],
    "companion-before-its-call": [OPERATOR, companion("s1"), assistant(SKILL), result("s1")],
    "companion-twice-for-one-call": [OPERATOR, assistant(SKILL), result("s1"), companion("s1"), companion("s1")],
    "companion-with-origin": [OPERATOR, assistant(SKILL), result("s1"), companion("s1", origin={"kind": "x"})],
    "companion-with-api-error-key": [OPERATOR, assistant(SKILL), result("s1"),
                                     companion("s1", isApiErrorMessage=False)],
    "companion-sidechain": [OPERATOR, assistant(SKILL), result("s1"), companion("s1", isSidechain=True)],
    "companion-not-turnCompanion": [OPERATOR, assistant(SKILL), result("s1"), companion("s1", turnCompanion=DROP)],
    "companion-string-content": [OPERATOR, assistant(SKILL), result("s1"),
                                 companion("s1", message={"role": "user", "content": "text"})],
    "companion-image-block": [OPERATOR, assistant(SKILL), result("s1"),
                              companion("s1", message={"role": "user", "content": [{"type": "image", "source": {}}]})],
    "companion-empty-content": [OPERATOR, assistant(SKILL), result("s1"),
                                companion("s1", message={"role": "user", "content": []})],
    "companion-id-not-str": [OPERATOR, assistant(SKILL), result("s1"), companion(7)],
    "other-isMeta-record": [OPERATOR, j({"type": "user", "isMeta": True, "message": {"content": "x"}})],
    "permissions-extra-key": [OPERATOR, perms(extra="x")],
    "permissions-missing-allowedTools": [OPERATOR, perms(allowedTools=DROP)],
    "permissions-allowedTools-not-list": [OPERATOR, perms(allowedTools="Read")],
    "permissions-allowedTools-non-str": [OPERATOR, perms(allowedTools=["Read", 3])],
    "unknown-attachment-still": [OPERATOR, j({"type": "attachment", "attachment": {"type": "command_permissionz"}})],
    "unknown-tool-still": [OPERATOR, assistant(call("x1", "SlashCommand", {"command": "/x"}))],
}

# fakes with none of the new shapes: the two readers must give the same events
PLAIN = {
    "bash-read-write": [OPERATOR, assistant({"type": "text", "text": "ok"},
                                            call("b1", "Bash", {"command": "ls", "run_in_background": False})),
                        result("b1"), assistant(call("r1", "Read", {"file_path": "/w/a"})), result("r1"),
                        assistant(call("w1", "Write", {"file_path": "/w/b", "content": "y"})), result("w1")],
    "nudge": [OPERATOR, j({"type": "user", "isMeta": True, "turnCompanion": True,
                           "message": {"role": "user", "content": tv.CC_NO_OUTPUT_NUDGE_TEXT}})],
}


class AdmittedShapes(unittest.TestCase):
    def test_each_admitted_shape_reads(self):
        for name, lines in ADMITTED.items():
            with self.subTest(name):
                tv.events("claude-code", lines)

    def test_write_file_text_is_a_write_with_its_path_only(self):
        evs = tv.events("claude-code", ADMITTED["write-file_text"])
        calls = [e for e in evs if e.kind == tv.TOOL_CALL]
        self.assertEqual([(e.tool, e.args) for e in calls], [(tv.WRITE, {"path": "/w/a.txt"})])

    def test_skill_is_other_with_no_args_and_its_result_pairs(self):
        evs = tv.events("claude-code", ADMITTED["skill-call"])
        self.assertEqual([(e.kind, e.tool, e.args, e.call) for e in evs if e.call],
                         [(tv.TOOL_CALL, tv.OTHER, {}, 1), (tv.TOOL_RESULT, tv.OTHER, None, 1)])

    def test_companion_is_harness_with_its_text_and_never_a_turn(self):
        evs = tv.events("claude-code", ADMITTED["skill-companion"])
        self.assertEqual(evs[-1].kind, tv.HARNESS)
        self.assertEqual(evs[-1].text, "Base directory for this skill: /x")
        self.assertEqual(tv.operator_lines(evs), ["please do the task"])
        self.assertEqual(evs[-1].turn, 1)
        self.assertEqual(tv.harness_types("claude-code", ADMITTED["command-permissions"]),
                         {"user:skill-companion": 1, "attachment:command_permissions": 1})

    def test_command_permissions_text(self):
        evs = tv.events("claude-code", ADMITTED["command-permissions"])
        self.assertEqual(evs[-1].text, "Bash(git:*)\nRead")
        self.assertIsNone(tv.events("claude-code", ADMITTED["command-permissions-empty"])[-1].text)


class StillRefused(unittest.TestCase):
    def test_a_line_read_outside_a_pass_admits_no_companion(self):
        with self.assertRaises(_tv.ViewError):
            tv.PARSERS["claude-code"].items(companion("s1"))

    def test_each_near_miss_is_refused(self):
        for name, lines in REFUSED.items():
            with self.subTest(name), self.assertRaises(_tv.ViewError):
                tv.events("claude-code", lines)


class TheFrozenFileAndTheInstall(unittest.TestCase):
    def test_transcript_view_is_byte_identical_to_the_frozen_file(self):
        repo = STUDY.parent.parent
        frozen = subprocess.run(["git", "-C", str(repo), "show", f"{BASE}:{REL}"], check=True,
                                capture_output=True).stdout
        self.assertEqual((STUDY / "transcript_view.py").read_bytes(), frozen)

    def test_the_install_is_undone_and_touches_no_other_table(self):
        before = (dict(_tv.PARSERS), dict(_tv.CC_TOOLS), _tv.CC_ATTACHMENT_TYPES)
        with sec.installed() as p:
            self.assertIs(_tv.PARSERS["claude-code"], p)
            self.assertIsInstance(p, sec.SecondaryClaudeCodeParser)
            self.assertEqual({k: v for k, v in _tv.PARSERS.items() if k != "claude-code"},
                             {k: v for k, v in before[0].items() if k != "claude-code"})
        self.assertEqual((dict(_tv.PARSERS), dict(_tv.CC_TOOLS), _tv.CC_ATTACHMENT_TYPES), before)
        self.assertIs(_tv.PARSERS["claude-code"], sec.FROZEN_PARSER)


class NullMutant(unittest.TestCase):
    """No install (the frozen parser) must refuse every admitted fake: the admitted tests then go red on it."""

    def test_the_frozen_parser_refuses_every_admitted_fake(self):
        for name, lines in ADMITTED.items():
            with self.subTest(name), self.assertRaises(_tv.ViewError):
                FROZEN.events("claude-code", lines)

    def test_the_frozen_parser_refuses_every_near_miss_too(self):
        for name, lines in REFUSED.items():
            with self.subTest(name), self.assertRaises(_tv.ViewError):
                FROZEN.events("claude-code", lines)

    def test_the_admitted_suite_goes_red_on_the_frozen_parser(self):
        """Run AdmittedShapes itself with this module's reader swapped for the frozen one: every test must fail."""
        global tv
        patched = tv
        tv = FROZEN
        try:
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(AdmittedShapes)
            ids = {t.id() for t in suite}                 # a suite drops its tests once run
            res = unittest.TestResult()
            suite.run(res)
        finally:
            tv = patched
        red = {getattr(t, "test_case", t).id() for t, _ in res.failures + res.errors}
        self.assertEqual(red, ids)
        self.assertGreater(len(ids), 0)

    def test_on_plain_fakes_the_two_parsers_agree(self):
        for name, lines in PLAIN.items():
            with self.subTest(name):
                a = [tuple(vars(e).values()) for e in tv.events("claude-code", lines)]
                b = [tuple(vars(e).values()) for e in FROZEN.events("claude-code", lines)]
                self.assertEqual(a, b)
                self.assertEqual(tv.harness_types("claude-code", lines), FROZEN.harness_types("claude-code", lines))


if __name__ == "__main__":
    unittest.main()
