#!/usr/bin/env python3
"""Step 3b review fold (finding 1, MAJOR; finding 2): Gemini's mode is read from the argv actually submitted, never
echoed from the pin, and identity sources are accepted per harness.

The box's run_turn writes the turn's actual-submission journal at <stream>.launch.json (schema 1: harness,
container_id, argv, cwd, stream, started_at) before its exec; this head's run_turn does not write it yet. The adapter
reads that journal after the exec: no journal, or one it cannot read, is an unobserved mode (routing's
harness-error, as a missing init always was); a journal whose argv lacks, changes or contradicts the pinned mode's
flags, or disagrees with the registered invocation (vendor_provenance.launch_facts), states a value that is not the
pin's, so routing reads a mismatch. A claude-code record never carries identity: its mode must come from the init.

Fakes and synthetic strings only: no model, vendor, network, container runtime, credential or holdout.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import agent_adapter as aa  # noqa: E402
import gemini_adapter as ga  # noqa: E402
import routing  # noqa: E402
import test_gemini_adapter as tga  # noqa: E402
import test_identity_evidence as tie  # noqa: E402
from box import run_take as rt  # noqa: E402

FLAGS = ga.MODE_FLAGS[tga.MODE]


def setUpModule():
    tga.setUpModule()


def tearDownModule():
    tga.tearDownModule()


class Journal:
    """Around the box's own run_turn, which writes the journal before the exec (0b6f60f9; before the integration
    merge this fake wrote it, since the harness lane's box had none). After the real turn, `write=False` removes the
    box's journal (a turn with no journal) and `edit` rewrites the journal's argv (a submission that differs)."""

    def __init__(self, edit=None, write=True):
        self.edit, self.write, self.real = edit, write, rt.run_turn

    def __enter__(self):
        def run_turn(runtime, take_id, inner, *, harness, run_tree, login_file, stream_path, budget_s, clock,
                     caller_env=None, config_folder=None, turn=None):
            got = self.real(runtime, take_id, inner, harness=harness, run_tree=run_tree, login_file=login_file,
                            stream_path=stream_path, budget_s=budget_s, clock=clock, caller_env=caller_env,
                             config_folder=config_folder, turn=turn)
            path = stream_path + ".launch.json"
            if not self.write:
                os.unlink(path)
            elif self.edit is not None:
                with open(path, encoding="utf-8") as fh:
                    launch = json.load(fh)
                launch["argv"] = self.edit(list(launch["argv"]))
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(launch, fh)
            return got
        rt.run_turn = run_turn
        return self

    def __exit__(self, *exc):
        rt.run_turn = self.real


def mode_of(edit=None, write=True, streams=None):
    with Journal(edit, write):
        a, _ = tga.take(ga, streams or [tga.fixture("turn1-tools.jsonl")])
        return a.turn("one", first=True, budget_s=60).identity["permission_mode"]


def drop_flags(argv):
    i = argv.index(FLAGS[0])
    return argv[:i] + argv[i + len(FLAGS):]


class ModeFromTheSubmittedArgv(unittest.TestCase):
    def test_the_pinned_flags_on_the_journal_are_the_mode(self):
        self.assertEqual(mode_of(), {"value": tga.MODE, "source": "submitted-argv"})

    def test_no_journal_is_an_unobserved_mode_never_the_pin(self):
        self.assertEqual(mode_of(write=False), {"value": None, "source": "unobserved"})

    def test_missing_changed_or_doubled_flags_are_never_the_pin(self):
        for name, edit in (("missing", drop_flags),
                           ("changed", lambda a: [("default" if x == FLAGS[1] else x) for x in a]),
                           ("doubled", lambda a: a + list(FLAGS)),
                           ("other mode flag", lambda a: a + ["--yolo"]),
                           ("prompt changed", lambda a: [("other line" if x == "one" else x) for x in a])):
            with self.subTest(name):
                got = mode_of(edit)
                self.assertNotEqual(got.get("value"), tga.MODE)
                tie_rec = aa.harness_records([tie.turn(dict(tie.ident(), permission_mode=got))], pin=tie.PIN,
                                             box=tie.BOX)
                self.assertTrue(routing.holds({"op": "differs_from_pin", "path": "init"}, tie_rec,
                                              routing.load_table()))

    def test_a_journal_that_is_not_json_is_unobserved(self):
        with Journal():
            a, _ = tga.take(ga, [tga.fixture("turn1-tools.jsonl")])
            real = rt.run_turn
            def broken(runtime, take_id, inner, **kw):
                got = real(runtime, take_id, inner, **kw)
                path = kw["stream_path"] + ".launch.json"
                os.unlink(path)
                Path(path).write_text("not json")
                return got
            rt.run_turn = broken
            try:
                t = a.turn("one", first=True, budget_s=60)
            finally:
                rt.run_turn = real
        self.assertEqual(t.identity["permission_mode"], {"value": None, "source": "unobserved"})

    def test_a_wrong_argv_builder_is_caught_by_the_argv_itself(self):
        """launch_facts compares the journal with gemini_adapter.argv, so a regression in argv() would agree with
        itself; the flags are also read from the journal's argv on their own."""
        real_argv = ga.argv
        for name, wrong in (("doubled", lambda a: a + list(FLAGS)),):
            ga.argv = lambda line, _w=wrong, **kw: _w(real_argv(line, **kw))
            try:
                with self.subTest(name):
                    self.assertEqual(mode_of(), {"value": ga.MODE_CONTRADICTED, "source": "submitted-argv"})
            finally:
                ga.argv = real_argv

    def test_the_reviewer_witness_no_longer_holds(self):
        real_argv = ga.argv

        def argv_without_mode(line, *, model, mode, session_id, first):
            return drop_flags(real_argv(line, model=model, mode=mode, session_id=session_id, first=first))
        ga.argv = argv_without_mode
        try:
            for write in (False, True):
                with self.subTest(journal=write):
                    self.assertNotEqual(mode_of(write=write), {"value": tga.MODE, "source": "submitted-argv"})
        finally:
            ga.argv = real_argv


class AcceptancePerHarness(unittest.TestCase):
    def test_a_claude_record_never_carries_identity(self):
        table = routing.load_table()
        pin = dict(tie.PIN, harness="claude-code")
        recs = aa.harness_records([tie.turn(tie.ident())], pin=pin, box=tie.BOX)
        self.assertTrue(any("identity" in p for p in routing.shape_problems(recs, table)))
        gem = aa.harness_records([tie.turn(tie.ident())], pin=tie.PIN, box=tie.BOX)
        self.assertEqual(routing.shape_problems(gem, table), [])

    def test_the_table_is_keyed_by_harness(self):
        self.assertEqual(set(routing.ACCEPTED_IDENTITY_SOURCES), {"gemini", "codex"})     # Codex slice 2
        for harness in ("gemini", "codex"):
            self.assertEqual(set(routing.ACCEPTED_IDENTITY_SOURCES[harness]), set(routing.PLAN_PIN_FIELDS))


if __name__ == "__main__":
    unittest.main()
