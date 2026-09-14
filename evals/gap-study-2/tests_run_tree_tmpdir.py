#!/usr/bin/env python3
"""Each take's scratch lands inside its own run tree (Javier's ruling C, 14 Sep 2026): loaded by test_harness.py.

    python3 evals/gap-study-2/test_harness.py TheTakeScratchLandsInItsRunTree

WHY IT EXISTS. The take checker is to refuse reads of the machine's temp root outside a take's run tree, because
other copies of this project have sat there. Round 1 showed an agent writing its own scratch into that root and
reading it back, so the refusal is only fair once the take is given a temp folder of its own. The driver makes
`<run tree>/.tmp/` in clean_run_tree, git-excludes it beside `data/staging/`, and child_env() sets TMPDIR, TMP and
TEMP to it for every turn. These tests hold each part on the code a take runs, and hold the environment record
unchanged by the three names, since the record carries names only.

No session is opened: the walk answers `claude` inside the driver module (tests_environment.drive_walk), and the
smoke's one_turn is replaced. Checkouts are real, built by the driver's own clean_run_tree.

No model, no network, stdlib only.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import types
import unittest
import uuid
from pathlib import Path
from unittest import mock

import prereg
import test_harness as th

HERE = th.HERE
VERSION = "0.0.0 (Claude Code)"
SOURCE = "a-source-the-harness-reports"


def by_path(name: str, file: str):
    """A module of this study, loaded by path under a name of its own."""
    spec = importlib.util.spec_from_file_location(f"{name}_{id(object())}", HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def synthetic_repo(td: Path) -> tuple[Path, str]:
    """A one-commit repository to export a run tree from, so a test never exports this repository.

    TheRunTreeCarriesNothing's own builder, called rather than copied: it is the one listed head reader for a
    synthetic checkout source, and it uses nothing of its instance.
    """
    return th.TheRunTreeCarriesNothing._repo(None, td)


def no_claude(real):
    """A subprocess stand-in that answers `claude --version` and refuses any other `claude` call."""
    ns = types.SimpleNamespace(**{n: getattr(real, n) for n in dir(real) if not n.startswith("__")})

    def run(argv, *a, **k):
        if list(argv[:1]) == ["claude"]:
            if list(argv[:2]) == ["claude", "--version"]:
                return real.CompletedProcess(argv, 0, VERSION + "\n", "")
            raise AssertionError("a test tried to open a session")
        return real.run(argv, *a, **k)

    ns.run = run
    return ns


class TheTakeScratchLandsInItsRunTree(unittest.TestCase):
    """Ruling C: every turn's TMPDIR, TMP and TEMP name `<run tree>/.tmp`, which exists before the first turn, stays
    out of the checkout's git status, and changes nothing the environment record carries."""

    VARS = ("TMPDIR", "TMP", "TEMP")

    def tmp(self) -> Path:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def assert_points_at(self, env: dict, tree: Path) -> None:
        want = str(tree / ".tmp")
        for n in self.VARS:
            # compared as a yes or no, as every environment in this suite is
            self.assertTrue(env.get(n) == want, f"a turn's {n} is not the run tree's temp folder")

    # ---- the environment a turn is passed ------------------------------------------------------------

    def test_child_env_points_the_temp_variables_at_the_run_tree_last(self):
        drive = th.gap_drive()
        self.assertEqual(drive.RUN_TREE_TMPDIR, ".tmp")
        self.assertEqual(drive.RUN_TREE_TMPDIR_VARIABLES, self.VARS)
        tree = self.tmp() / "run-00000000"
        drive.RUN_TREE = None
        base = drive.child_env()
        self.assertTrue(all(base.get(n) == os.environ.get(n) for n in self.VARS),
                        "before a run tree exists, child_env() changes a temp variable it has no folder for")
        drive.RUN_TREE = tree
        self.assert_points_at(drive.child_env(), tree)
        # applied after the strip, so a stripped list naming them cannot take them out of a take's environment
        drive.STRIPPED_ENV = self.VARS
        self.assert_points_at(drive.child_env(), tree)

    def test_the_turn_environment_points_every_temp_variable_at_the_run_tree(self):
        env_tests = by_path("run_tree_tmpdir_env", "tests_environment.py")
        seen: list[dict] = []

        def watch(drive) -> None:
            real = drive.one_turn

            def one_turn(*a, **k):
                tree = drive.RUN_TREE
                folder = tree / ".tmp"
                exists = folder.is_dir()
                if exists:
                    (folder / "scratch.txt").write_text("a tool's scratch\n")
                status = subprocess.run(["git", "-C", str(tree), "status", "--porcelain"], capture_output=True,
                                        text=True).stdout
                seen.append({"tree": tree, "exists": exists, "tmp_in_status": ".tmp" in status})
                return real(*a, **k)

            drive.one_turn = one_turn

        r = env_tests.drive_walk(self, {}, env_tests.CLEAN_WALK, patch_drive=watch)
        self.assertEqual(r.code, 0, r.out)
        self.assertEqual(len(r.turn_calls), 2, "the walk did not send its two turns")
        self.assertEqual(len(seen), 2)
        for c, s in zip(r.turn_calls, seen):
            self.assertTrue(s["exists"], "the run tree's temp folder did not exist when a turn was sent")
            self.assertFalse(s["tmp_in_status"], "the take's temp folder broke the checkout's git status")
            self.assert_points_at(c["env"] or {}, s["tree"])
            self.assertTrue(c["env"] == r.child, "the environment a turn was passed is not child_env()")

        # the record: identical to one built with the three names taken out, and no temp path in its bytes
        drive = r.drive
        turn_env = r.turn_calls[0]["env"]
        parent = env_tests.quiet_env(drive)
        without = {k: v for k, v in turn_env.items() if k not in self.VARS}
        kw = dict(session_id=r.record["session_id"], row=None, row_commit=None, task=r.record["task"],
                  half=r.record["half"], model=r.record["model_requested"],
                  claude_version=r.record["claude_version"])
        with_vars = drive.environment_record(turn_env, parent, **kw)
        self.assertEqual(with_vars, drive.environment_record(without, parent, **kw),
                         "the three temp variables changed the environment record")
        written = {k: v for k, v in r.record.items() if k != "credential_source"}
        self.assertEqual(written, {k: v for k, v in with_vars.items() if k != "credential_source"},
                         "the written record is not environment_record's for the environment the turns were passed")
        self.assertEqual(sorted(r.record), sorted(env_tests.RECORD_KEYS))
        for n in self.VARS:
            self.assertIsNone(drive.matched_by(n), f"{n} matches a published name pattern")
            for block in ("api_key_variables", "billing_route_variables", "subscription_token_variables"):
                self.assertNotIn(n, r.record[block], f"{n} is on the record's {block}")
        self.assertFalse({e["name"] for e in r.record["names_present"]} & set(self.VARS))
        text = r.record_path.read_text()
        tree = seen[0]["tree"]
        for value in {str(tree), str(tree / ".tmp"), tempfile.gettempdir(), os.path.realpath(tempfile.gettempdir())}:
            self.assertNotIn(value, text, "environment.json carries a temp path")
        self.assertNotIn(".tmp", text, "environment.json names the take's temp folder")

    # ---- the checkout ---------------------------------------------------------------------------------

    def test_git_status_stays_clean_with_a_file_in_the_temp_folder(self):
        drive = th.gap_drive()
        repo, head = synthetic_repo(self.tmp())
        sid = str(uuid.uuid4())
        exclude = drive.excluded_from_run_tree(prereg.load())
        try:
            tree = drive.clean_run_tree(head, sid, exclude, repo=repo)
        except SystemExit as exc:
            shutil.rmtree(drive.run_tree_path(sid), ignore_errors=True)
            self.fail(f"the take's temp folder broke the checkout's git status: clean_run_tree refused ({exc})")
        self.addCleanup(shutil.rmtree, tree, True)
        self.assertTrue((tree / ".tmp").is_dir(), "clean_run_tree made no temp folder")
        (tree / ".tmp" / "scratch.txt").write_text("a tool's scratch\n")
        (tree / ".tmp" / "nested").mkdir()
        (tree / ".tmp" / "nested" / "more.txt").write_text("more\n")
        status = subprocess.run(["git", "-C", str(tree), "status", "--porcelain", "--untracked-files=all"],
                                capture_output=True, text=True).stdout
        self.assertEqual(status, "", "the take's temp folder broke the checkout's git status")
        self.assertEqual(drive.run_tree_problems(tree, sid, exclude), [])
        excluded = (tree / ".git" / "info" / "exclude").read_text().splitlines()
        self.assertIn("data/staging/", excluded)
        self.assertIn(".tmp/", excluded)

    def test_a_built_tree_without_the_folder_or_its_exclusion_is_a_problem(self):
        drive = th.gap_drive()
        repo, head = synthetic_repo(self.tmp())
        sid = str(uuid.uuid4())
        tree = drive.clean_run_tree(head, sid, [], repo=repo)
        self.addCleanup(shutil.rmtree, tree, True)
        exclude = tree / ".git" / "info" / "exclude"
        exclude.write_text(exclude.read_text().replace(".tmp/\n", ""))
        self.assertTrue(any("not git-excluded" in p for p in drive.run_tree_problems(tree, sid, [])),
                        "a temp folder left out of the exclusion is not reported")
        shutil.rmtree(tree / ".tmp")
        self.assertTrue(any("is missing" in p for p in drive.run_tree_problems(tree, sid, [])),
                        "a missing temp folder is not reported")

    # ---- the smoke measures a take's environment ------------------------------------------------------

    def test_the_smoke_turn_gets_the_same_temp_folder(self):
        smoke = by_path("run_tree_tmpdir_smoke", "smoke_run_tree.py")
        drive = th.gap_drive()
        td = self.tmp()
        repo, head = synthetic_repo(td)
        real_build = drive.clean_run_tree
        built: list[Path] = []
        seen: list[dict] = []

        def clean_run_tree(commit, session_id, exclude, repo_=None):
            tree = real_build(head, session_id, exclude, repo=repo)
            built.append(tree)
            self.addCleanup(shutil.rmtree, tree, True)
            return tree

        def one_turn(line, session_id, model, first, budget_s):
            env = drive.child_env()
            tree = drive.RUN_TREE
            seen.append({"tree": tree, "env": {n: env.get(n) for n in self.VARS},
                         "exists": (tree / ".tmp").is_dir()})
            (tree / ".tmp" / "scratch.txt").write_text("a tool's scratch\n")
            recs = [{"type": "attachment", "sessionId": session_id, "cwd": str(tree),
                     "attachment": {"type": "environment", "snapshot": {"workingDirectory": str(tree)}}},
                    {"type": "user", "sessionId": session_id, "cwd": str(tree),
                     "message": {"role": "user", "content": "ready?"}},
                    {"type": "assistant", "sessionId": session_id, "cwd": str(tree),
                     "message": {"role": "assistant", "content": [{"type": "text", "text": "ready"}]}}]
            (td / "session.jsonl").write_text("\n".join(json.dumps(x) for x in recs) + "\n")
            return "ready", 0, "", "", SOURCE

        drive.clean_run_tree = clean_run_tree
        drive.one_turn = one_turn
        drive.session_file = lambda sid: td / "session.jsonl" if (td / "session.jsonl").is_file() else None
        drive.subprocess = no_claude(subprocess)
        smoke.subprocess = no_claude(subprocess)
        real_by_path = smoke.by_path
        smoke.by_path = lambda name, file: drive if file == "drive.py" else real_by_path(name, file)

        out_dir = td / "smoke"
        quiet = {k: v for k, v in os.environ.items() if drive.matched_by(k) is None}
        buf = io.StringIO()
        with mock.patch.dict(os.environ, quiet, clear=True):
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                code = smoke.main(["--strip", "none", "--out", str(out_dir)])
        self.assertEqual(len(built), 1, f"the smoke did not build its checkout with clean_run_tree: {buf.getvalue()[-600:]}")
        self.assertEqual(len(seen), 1, "the smoke sent no turn")
        self.assertTrue(seen[0]["exists"], "the smoke's checkout had no temp folder when its turn was sent")
        self.assert_points_at(seen[0]["env"], built[0])
        self.assertEqual(code, 0, buf.getvalue()[-600:])
        report = json.loads((out_dir / "report.json").read_text())
        self.assertEqual(report["checkout"]["problems_before_the_turn"], [])
        self.assertEqual(report["scratch"]["run_tree_tmp_files"], 1,
                         "the smoke did not count the file its turn left in the run tree's temp folder")
        self.assertNotIn(".tmp/", json.dumps(report), "the smoke's report names a path inside the temp folder")

    # ---- the draft and the driver carry one constant -------------------------------------------------

    def test_the_draft_carries_the_drivers_temp_folder(self):
        drive = th.gap_drive()
        dc = prereg.load()["driver_constants"]
        block = dc.get("run_tree_tmpdir")
        self.assertIsInstance(block, dict, "driver_constants.run_tree_tmpdir is missing from the draft")
        self.assertEqual(sorted(block), ["path", "variables", "why"])
        self.assertEqual(block["path"], drive.RUN_TREE_TMPDIR, "the draft's temp folder is not the driver's")
        self.assertEqual(tuple(block["variables"]), drive.RUN_TREE_TMPDIR_VARIABLES,
                         "the draft's temp variables are not the driver's")
        self.assertTrue(block["why"].strip())
        self.assertFalse(set(dc.get("stripped_env") or ()) & set(self.VARS),
                         "driver_constants.stripped_env lists a temp variable the driver sets")


if __name__ == "__main__":
    unittest.main()
