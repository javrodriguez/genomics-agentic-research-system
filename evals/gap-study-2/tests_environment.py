#!/usr/bin/env python3
"""The environment record and the stripped child environment (CP3, fix 4): loaded by test_harness.py.

    python3 evals/gap-study-2/test_harness.py TheEnvironmentRecordIsWritten

WHY IT EXISTS (structural lesson 14). Round 1 stated that its takes ran on the subscription, and nothing beside a
transcript showed it (Ruling 34); its driver passed its own environment to every session wholesale, so a take
driven from a Claude Code pane inherited that pane's session variables. The driver now passes child_env() to every
turn, writes environment.json from that same environment before the first turn, stops before any session opens
when an API key or a billing route is set, and binds the record's bytes in the ledger.

Every case drives the real loop: a real checkout, a real fixture, the real one_turn, and a `claude` answered by
a canned stream inside the driver module only. The environment each case gives the driver is built here, from
this process's own minus every name the record reads or the driver strips, plus planted names whose values are
sentinels. No value is printed by any assertion: environments are compared by name, or as a yes or no.

No model, no network, stdlib only.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import prereg
import test_harness as th

HERE = th.HERE

# Markers the number-fidelity positive walk reads (the same replies TheDriverLoopRecordsEveryTurnItEnds sends).
REPLY_TITLE = "Project title?"          # holds the step-1 recovery's own marker, not the step's
REPLY_IDS = "Reply with a comma-separated list of IDs"
REPLY_CONFIRM = "Confirm to create symlinks under"
# A stand-in for what the harness reports. The observed subscription value is the smoke's to record.
SOURCE = "a-source-the-harness-reports"
UNREPORTED = object()

RECORD_KEYS = ["record", "schema", "session_id", "row", "row_commit", "task", "half", "model_requested",
               "claude_version", "written_before_first_turn", "name_patterns", "names_present", "stripped_names",
               "api_key_variables", "api_key_set", "billing_route_variables", "billing_route_set",
               "subscription_token_variables", "credential_source"]


def sentinel(name: str) -> str:
    return "sentinel-" + hashlib.sha256(name.encode()).hexdigest()[:16]


def quiet_env(drive) -> dict:
    """This process's environment minus every name the record reads or the driver strips.

    What remains (the search path, the home folder, the poison switch when the suite is run poisoned) is passed
    through untouched so git and the generators run; none of it is ever printed.
    """
    return {k: v for k, v in os.environ.items() if drive.matched_by(k) is None and k not in drive.STRIPPED_ENV}


def stream(text: str, source) -> str:
    """The records a headless turn writes to stdout, as far as the driver reads them."""
    init = {"type": "system", "subtype": "init", "session_id": "canned"}
    if source is not UNREPORTED:
        init["apiKeySource"] = source
    recs = [init, {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}},
            {"type": "result", "subtype": "success"}]
    return "\n".join(json.dumps(r) for r in recs) + "\n"


def drive_walk(test: unittest.TestCase, planted: dict, replies: list, *, prepare=None,
               patch_drive=None) -> types.SimpleNamespace:
    """One number-fidelity positive walk through drive.main(), with `planted` added to a quiet environment.

    `replies` are (text, exit code, reported source or UNREPORTED); exit 124 raises the timeout the real
    subprocess raises, carrying the stream up to the cut. Returns the exit code, what the driver printed, the
    study root it wrote into, every `claude` call with the environment it was passed, the child environment
    the driver computes for that same process environment, and the walk's ledger and record when written.
    """
    drive = th.gap_drive()
    tmp = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, tmp, True)
    drive.HERE = tmp
    if prepare:
        prepare(tmp)
    if patch_drive:
        patch_drive(drive)

    pre = copy.deepcopy(prereg.load())
    pre["harness"]["claude_version_at_freeze"] = pre["harness"]["claude_version"] + " (Claude Code)"
    frozen_version = pre["harness"]["claude_version_at_freeze"]
    test.enterContext(th.injected_prereg(pre))

    real = subprocess
    calls: list[dict] = []

    def run(argv, *a, **k):
        if list(argv[:1]) != ["claude"]:
            return real.run(argv, *a, **k)
        calls.append({"argv": list(argv), "env": k.get("env")})
        if list(argv[:2]) == ["claude", "--version"]:
            return real.CompletedProcess(argv, 0, frozen_version + "\n", "")
        i = sum(1 for c in calls if c["argv"][1] == "-p") - 1
        if i >= len(replies):
            return real.CompletedProcess(argv, 1, "", "no more replies")
        text, code, source = replies[i]
        if code == 124:
            raise real.TimeoutExpired(argv, k.get("timeout"), output=stream("", source))
        return real.CompletedProcess(argv, code, stream(text, source), "")

    drive.subprocess = types.SimpleNamespace(**{n: getattr(real, n) for n in dir(real) if not n.startswith("__")})
    drive.subprocess.run = run

    env = {**quiet_env(drive), **planted}
    saved = sys.argv
    sys.argv = ["drive.py", "--task", "number-fidelity", "--half", "positive", "--walk", "--model", "claude-opus-5"]
    out = io.StringIO()
    try:
        with mock.patch.dict(os.environ, env, clear=True):
            with contextlib.redirect_stdout(out):
                code = drive.main()
            child = drive.child_env()
            parent_names = sorted(os.environ)
    finally:
        sys.argv = saved
        if drive.RUN_TREE is not None:
            shutil.rmtree(drive.RUN_TREE, ignore_errors=True)
    folder = tmp / "walks" / "number-fidelity" / "1"
    ledger = folder / "driver-ledger.json"
    record = folder / "environment.json"
    return types.SimpleNamespace(
        code=code, out=out.getvalue(), tmp=tmp, drive=drive, calls=calls, child=child, parent_names=parent_names,
        turn_calls=[c for c in calls if c["argv"][1:2] == ["-p"]], record_path=record,
        ledger=json.loads(ledger.read_text()) if ledger.is_file() else None,
        record=json.loads(record.read_text()) if record.is_file() else None)


CLEAN_WALK = [(REPLY_IDS, 0, SOURCE), (REPLY_CONFIRM, 0, SOURCE)]


class TheEnvironmentRecordIsWritten(unittest.TestCase):
    """Fix 4, driver side: environment.json is written from the environment every turn is passed, before the
    first turn, names and never values; the money line stops the driver before any session; the ledger binds it."""

    def block(self) -> dict:
        return prereg.load()["environment_record"]

    # ---- the record: names, never values --------------------------------------------------------------

    def test_the_record_holds_names_never_a_value_and_no_home_path(self):
        drive = th.gap_drive()
        planted = {"ANTHROPIC_MODEL": sentinel("ANTHROPIC_MODEL"),
                   "AWS_PROFILE": str(Path.home() / sentinel("AWS_PROFILE")),
                   "CLAUDE_CODE_OAUTH_TOKEN": sentinel("CLAUDE_CODE_OAUTH_TOKEN"),
                   "GH_TOKEN": sentinel("GH_TOKEN"),
                   "MY_SERVICE_SECRET": sentinel("MY_SERVICE_SECRET"),
                   "ANTHROPIC_API_KEY": "",
                   "UNRELATED_SETTING": sentinel("UNRELATED_SETTING")}
        planted.update({n: sentinel(n) for n in drive.STRIPPED_ENV})
        r = drive_walk(self, planted, CLEAN_WALK)
        self.assertEqual(r.code, 0, r.out)
        self.assertIsNotNone(r.record, "the walk wrote no environment record")
        text = r.record_path.read_text()
        leaked = sorted(n for n, v in planted.items() if v and v in text)
        self.assertEqual(leaked, [], "the record carries the value of these variables")
        self.assertNotIn(str(Path.home()), text, "the record names the operator's home folder")

        rec = r.record
        self.assertEqual(list(rec), RECORD_KEYS)
        self.assertEqual(rec["schema"], 1)
        self.assertTrue(rec["record"].strip())
        self.assertIs(rec["written_before_first_turn"], True)
        self.assertEqual(rec["name_patterns"], self.block()["name_patterns"])
        self.assertEqual(rec["names_present"], [
            {"name": "ANTHROPIC_API_KEY", "matched_by": "harness"},
            {"name": "ANTHROPIC_MODEL", "matched_by": "harness"},
            {"name": "AWS_PROFILE", "matched_by": "harness"},
            {"name": "CLAUDE_CODE_OAUTH_TOKEN", "matched_by": "harness"},
            {"name": "GH_TOKEN", "matched_by": "generic"},
            {"name": "MY_SERVICE_SECRET", "matched_by": "generic"}])
        # A walk is bound to no row, and to the session and version its own ledger records.
        self.assertIsNone(rec["row"])
        self.assertIsNone(rec["row_commit"])
        for key in ("session_id", "task", "half", "model_requested", "claude_version"):
            self.assertEqual(rec[key], r.ledger[key], key)
        self.assertEqual(rec["credential_source"]["key"], "system/init.apiKeySource")

    def test_the_three_lists_are_complete_and_an_empty_key_is_not_a_set_one(self):
        r = drive_walk(self, {"ANTHROPIC_API_KEY": "", "CLAUDE_CODE_OAUTH_TOKEN": sentinel("oauth"),
                              "CLAUDE_CODE_USE_VERTEX": ""}, CLEAN_WALK)
        self.assertEqual(r.code, 0, r.out)
        rec, block = r.record, self.block()
        for field in ("api_key_variables", "billing_route_variables", "subscription_token_variables"):
            self.assertEqual(sorted(rec[field]), sorted(block[field]), f"{field} is not the draft's list, complete")
            self.assertTrue(set(rec[field].values()) <= {"absent", "empty", "set"}, field)
        self.assertEqual(rec["api_key_variables"]["ANTHROPIC_API_KEY"], "empty")
        self.assertIs(rec["api_key_set"], False, "an empty API-key variable is not a set one")
        self.assertEqual(rec["billing_route_variables"]["CLAUDE_CODE_USE_VERTEX"], "empty")
        self.assertIs(rec["billing_route_set"], False)
        # A subscription token is recorded and is never a stop.
        self.assertEqual(rec["subscription_token_variables"]["CLAUDE_CODE_OAUTH_TOKEN"], "set")
        self.assertEqual(rec["subscription_token_variables"]["CLAUDE_CODE_SESSION_ACCESS_TOKEN"], "absent")

    # ---- the money line ----------------------------------------------------------------------------------

    def assert_stopped_before_any_session(self, r, name: str, value: str) -> None:
        self.assertEqual(r.code, 2, f"{name} set did not stop the driver")
        self.assertEqual(r.calls, [], f"{name} set: `claude` was run before the refusal")
        self.assertIn(name, r.out, f"{name} set: the refusal does not name the variable")
        self.assertNotIn(value, r.out, f"{name} set: the refusal prints its value")
        self.assertIsNone(r.drive.RUN_TREE, f"{name} set: a checkout was built before the refusal")
        self.assertFalse((r.tmp / "walks").exists(), f"{name} set: a walk folder was written")

    def test_a_set_api_key_stops_the_driver_before_any_session(self):
        names = self.block()["api_key_variables"]
        self.assertEqual(len(names), 6)
        for name in names:
            with self.subTest(name=name):
                self.assert_stopped_before_any_session(drive_walk(self, {name: sentinel(name)}, CLEAN_WALK),
                                                       name, sentinel(name))

    def test_a_set_billing_route_stops_the_driver_before_any_session(self):
        names = self.block()["billing_route_variables"]
        self.assertEqual(len(names), 5)
        for name in names:
            with self.subTest(name=name):
                self.assert_stopped_before_any_session(drive_walk(self, {name: sentinel(name)}, CLEAN_WALK),
                                                       name, sentinel(name))

    def test_an_unwritable_record_stops_the_driver_before_any_line(self):
        def a_file_where_the_walks_go(tmp: Path) -> None:
            (tmp / "walks").mkdir()
            (tmp / "walks" / "number-fidelity").write_text("not a folder\n")

        r = drive_walk(self, {}, CLEAN_WALK, prepare=a_file_where_the_walks_go)
        self.assertEqual(r.code, 2, r.out)
        self.assertIn("environment record could not be written", r.out)
        self.assertEqual(r.turn_calls, [], "a line was sent with no environment record written")
        self.assertIsNotNone(r.drive.RUN_TREE)
        self.assertFalse(r.drive.RUN_TREE.exists(), "the refused checkout was left behind")

    def test_the_driver_refuses_a_stripped_list_that_hides_a_route(self):
        def strip_a_route(drive) -> None:
            drive.STRIPPED_ENV = drive.STRIPPED_ENV + ("ANTHROPIC_BASE_URL",)

        r = drive_walk(self, {}, CLEAN_WALK, patch_drive=strip_a_route)
        self.assertEqual(r.code, 2, r.out)
        self.assertIn("ANTHROPIC_BASE_URL", r.out)
        self.assertEqual(r.calls, [])

    def test_the_money_line_through_the_cli(self):
        """Lesson 12: the refusal driven through `python3 drive.py`, in a copy of the study.

        The copy is not a git repository, so a driver that let a key through would refuse at `--at` before any
        `claude` call: the case cannot open a session whichever way it goes, and it goes red on the wording.
        """
        root, dest = th.study_copy(self)
        base = quiet_env(th.gap_drive())
        for name in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_USE_VERTEX"):
            with self.subTest(name=name):
                env = {**base, name: sentinel(name), "GIT_CEILING_DIRECTORIES": str(root.parent)}
                p = subprocess.run([sys.executable, str(dest / "drive.py"), "--task", "number-fidelity", "--half",
                                    "positive", "--walk", "--model", "claude-opus-5"],
                                   capture_output=True, text=True, cwd=str(root), env=env)
                said = p.stdout + p.stderr
                self.assertEqual(p.returncode, 2, f"{name} set: exit {p.returncode}")
                self.assertIn(f"refusing: {name} set in the environment", said,
                              f"{name} set: the CLI did not refuse on the money line")
                self.assertNotIn(sentinel(name), said)
                self.assertFalse((dest / "walks").exists())

    # ---- the stripped child environment --------------------------------------------------------------

    def test_stripped_names_leave_every_turns_environment_and_are_named(self):
        drive = th.gap_drive()
        stripped = sorted(prereg.load()["driver_constants"]["stripped_env"])
        self.assertEqual(len(stripped), 12)
        self.assertEqual(sorted(drive.STRIPPED_ENV), stripped)
        r = drive_walk(self, {n: sentinel(n) for n in stripped}, CLEAN_WALK)
        self.assertEqual(r.code, 0, r.out)
        self.assertEqual(len(r.turn_calls), 2)
        for c in r.turn_calls:
            env = c["env"] or {}
            leaked = sorted(n for n in stripped if n in env)
            self.assertEqual(leaked, [], "a turn was passed stripped name(s)")
            # Compared as a yes or no, so no value reaches the output.
            self.assertTrue(env == r.child, "the environment a turn was passed is not child_env(): names differ "
                                            f"{sorted(set(env) ^ set(r.child))}")
            for k, v in drive.ISOLATION_ENV.items():
                self.assertEqual(env.get(k), v, f"the isolation variable {k} is not applied")
        self.assertEqual(r.record["stripped_names"], stripped)
        self.assertFalse({x["name"] for x in r.record["names_present"]} & set(stripped))
        self.assertTrue(set(stripped) <= set(r.parent_names), "the planted names never reached the driver")

    # ---- the credential source, turn by turn ----------------------------------------------------------

    def per_turn(self, r) -> list[tuple]:
        return [(t["n"], t["recovery"], t["exit"]) for t in r.record["credential_source"]["per_turn"]]

    def test_per_turn_is_one_to_one_with_the_ledger_turns_recovery_included(self):
        r = drive_walk(self, {}, [(REPLY_TITLE, 0, SOURCE), (REPLY_IDS, 0, SOURCE), (REPLY_CONFIRM, 0, SOURCE)])
        self.assertEqual(r.code, 0, r.out)
        rows = [(t["n"], bool(t.get("recovery")), t["exit"]) for t in r.ledger["turns"]]
        self.assertEqual(rows, [(1, False, 0), (1, True, 0), (2, False, 0)], "the walk did not send its recovery")
        self.assertEqual(self.per_turn(r), rows)
        self.assertEqual([t["apiKeySource"] for t in r.record["credential_source"]["per_turn"]], [SOURCE] * 3)
        self.assertEqual(r.record["credential_source"]["reported"], SOURCE)

    def test_a_recovery_cut_by_the_budget_is_on_the_record_with_what_it_reported(self):
        r = drive_walk(self, {}, [(REPLY_TITLE, 0, SOURCE), ("", 124, SOURCE)])
        self.assertEqual(r.code, 0, r.out)
        self.assertEqual(self.per_turn(r), [(1, False, 0), (1, True, 124)])
        self.assertEqual(self.per_turn(r), [(t["n"], bool(t.get("recovery")), t["exit"]) for t in r.ledger["turns"]])
        self.assertEqual(r.record["credential_source"]["reported"], SOURCE)

    def test_an_unreported_source_is_null_never_the_word_none(self):
        drive = th.gap_drive()
        self.assertIsNone(drive.stream_init_source(""))
        self.assertIsNone(drive.stream_init_source(stream("x", UNREPORTED)))
        self.assertIsNone(drive.stream_init_source(stream("x", None)))
        self.assertIsNone(drive.stream_init_source("not json\n" + json.dumps({"type": "assistant"})))
        self.assertEqual(drive.stream_init_source("not json\n" + stream("x", SOURCE)), SOURCE)

        r = drive_walk(self, {}, [(REPLY_IDS, 0, SOURCE), (REPLY_CONFIRM, 0, UNREPORTED)])
        self.assertEqual(r.code, 0, r.out)
        got = [t["apiKeySource"] for t in r.record["credential_source"]["per_turn"]]
        self.assertEqual(got, [SOURCE, None])
        self.assertIsNone(r.record["credential_source"]["reported"], "a turn that reported nothing was papered over")

    def test_two_turns_that_report_different_sources_report_none_in_common(self):
        r = drive_walk(self, {}, [(REPLY_IDS, 0, "one-source"), (REPLY_CONFIRM, 0, "another-source")])
        self.assertEqual(r.code, 0, r.out)
        self.assertIsNone(r.record["credential_source"]["reported"])

    # ---- the ledger binds the bytes ----------------------------------------------------------------------

    def test_the_ledger_binds_the_record_by_its_bytes(self):
        r = drive_walk(self, {}, CLEAN_WALK)
        self.assertEqual(r.code, 0, r.out)
        self.assertEqual(r.ledger["environment"],
                         {"file": "environment.json",
                          "sha256": hashlib.sha256(r.record_path.read_bytes()).hexdigest()})
        self.assertEqual(len(r.record["credential_source"]["per_turn"]), len(r.ledger["turns"]))
        self.assertEqual(sorted(p.name for p in r.record_path.parent.iterdir() if p.name.startswith(".")), [],
                         "a partial record was left beside the record")

    # ---- one vocabulary, and what may never be stripped ----------------------------------------------

    def test_the_draft_and_the_driver_carry_one_vocabulary(self):
        drive = th.gap_drive()
        b = self.block()
        self.assertEqual(b["file"], drive.ENVIRONMENT_RECORD_FILE)
        self.assertEqual(b["schema"], drive.ENVIRONMENT_SCHEMA)
        self.assertEqual(b["name_patterns"]["harness"], list(drive.HARNESS_NAME_PATTERNS))
        self.assertEqual(b["name_patterns"]["generic"], list(drive.GENERIC_NAME_PATTERNS))
        self.assertEqual(b["api_key_variables"], list(drive.API_KEY_VARIABLES))
        self.assertEqual(b["billing_route_variables"], list(drive.BILLING_ROUTE_VARIABLES))
        self.assertEqual(b["subscription_token_variables"], list(drive.SUBSCRIPTION_TOKEN_VARIABLES))
        self.assertEqual(b["credential_source_key"], drive.CREDENTIAL_SOURCE_KEY)
        self.assertEqual(list(prereg.load()["driver_constants"]["stripped_env"]), list(drive.STRIPPED_ENV))

    def test_no_stripped_name_may_hide_a_key_a_route_or_a_login(self):
        drive = th.gap_drive()
        stripped = prereg.load()["driver_constants"]["stripped_env"]
        self.assertTrue(stripped, "no stripped name to check; this test measured nothing")
        self.assertEqual(drive.never_stripped_problems(stripped), [])
        # Not vacuous: every name on the three lists fires, and so does a name only a harness pattern matches.
        b = self.block()
        for planted in (b["api_key_variables"] + b["billing_route_variables"] + b["subscription_token_variables"]
                        + ["AWS_REGION", "CLAUDE_CODE_SKIP_BEDROCK_AUTH", "ANTHROPIC_MODEL"]):
            with self.subTest(planted=planted):
                got = drive.never_stripped_problems(list(stripped) + [planted])
                self.assertEqual(len(got), 1, got)
                self.assertIn(planted, got[0])
        # The rule's stated scope: the generic shape alone does not keep a name. One of the twelve has it.
        self.assertEqual(drive.matched_by("CLAUDE_CODE_MESSAGING_TOKEN"), "generic")
        self.assertIn("CLAUDE_CODE_MESSAGING_TOKEN", stripped)


if __name__ == "__main__":
    unittest.main()
