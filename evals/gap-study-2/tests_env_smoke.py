#!/usr/bin/env python3
"""The environment smoke records what it stripped (CP3, J4): loaded by test_harness.py.

    python3 evals/gap-study-2/test_harness.py TheEnvSmokeRecordsWhatItStripped

WHY IT EXISTS. The environment smoke is the evidence J4 rests on: one run with nothing stripped shows which
Claude Code session names a take driven from a pane inherits, one run with the draft's list shows headless login
still works without them, and --compare holds the two records to differing in those names alone. No test may
open a session, so every case runs smoke_run_tree.main() with the driver's clean_run_tree, one_turn, session_file
and run_tree_problems replaced in the driver module the smoke loads, and `claude --version` answered in the
smoke module. Everything else is the landed code: child_env(), environment_record, with_turns, the atomic write.

The environment is this process's own minus every name the record reads or the driver strips, plus planted
names whose values are sentinels. No assertion prints a value: environments are compared by name, or as a yes
or no, and every output file is searched for every sentinel.

No model, no network, stdlib only.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import prereg
import test_harness as th

HERE = th.HERE
VERSION = "0.0.0 (Claude Code)"
SOURCE = "a-source-the-harness-reports"
MODEL = "claude-haiku-4-5-20251001"


def sentinel(name: str) -> str:
    return "sentinel-" + hashlib.sha256(name.encode()).hexdigest()[:16]


def load_smoke():
    spec = importlib.util.spec_from_file_location(f"env_smoke_{id(object())}", HERE / "smoke_run_tree.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def draft_stripped() -> list[str]:
    return list(prereg.load()["driver_constants"]["stripped_env"])


def quiet_env(drive) -> dict:
    """This process's environment minus every name the record reads and every name the draft strips."""
    listed = set(draft_stripped())
    return {k: v for k, v in os.environ.items() if drive.matched_by(k) is None and k not in listed}


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


def transcript(path: Path, sid: str, cwd: Path) -> None:
    recs = [{"type": "attachment", "sessionId": sid, "cwd": str(cwd),
             "attachment": {"type": "environment", "snapshot": {"workingDirectory": str(cwd)}}},
            {"type": "user", "sessionId": sid, "cwd": str(cwd), "message": {"role": "user", "content": "ready?"}},
            {"type": "assistant", "sessionId": sid, "cwd": str(cwd),
             "message": {"role": "assistant", "content": [{"type": "text", "text": "ready"}]}}]
    path.write_text("\n".join(json.dumps(r) for r in recs) + "\n")


def run_smoke(test: unittest.TestCase, argv: list[str], planted: dict, *, patch_drive=None) -> types.SimpleNamespace:
    """smoke_run_tree.main(argv) with `planted` added to a quiet environment and no session opened."""
    smoke = load_smoke()
    drive = th.gap_drive()
    tmp = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, tmp, True)
    turns: list[dict] = []

    def clean_run_tree(commit, session_id, exclude, repo=None):
        tree = tmp / "tree"
        tree.mkdir()
        return tree

    def one_turn(line, session_id, model, first, budget_s):
        # names only: a turn's environment is kept as its name set and a yes or no against child_env()
        env = drive.child_env()
        turns.append({"names": sorted(env), "sid": session_id, "is_child_env": env == drive.child_env()})
        transcript(tmp / "session.jsonl", session_id, tmp / "tree")
        return "ready", 0, "", "", SOURCE

    drive.clean_run_tree = clean_run_tree
    drive.one_turn = one_turn
    drive.run_tree_problems = lambda tree, sid, exclude: []
    drive.session_file = lambda sid: tmp / "session.jsonl" if (tmp / "session.jsonl").is_file() else None
    drive.subprocess = no_claude(subprocess)
    if patch_drive:
        patch_drive(drive)
    smoke.subprocess = no_claude(subprocess)
    real_by_path = smoke.by_path
    smoke.by_path = lambda name, file: drive if file == "drive.py" else real_by_path(name, file)

    out = io.StringIO()
    env = {**quiet_env(drive), **planted}
    code = None
    expected = None
    with mock.patch.dict(os.environ, env, clear=True):
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try:
                code = smoke.main(argv)
            except SystemExit as exc:
                code = exc.code
        folder = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
        rec_path = folder / "environment.json" if folder else None
        if rec_path is not None and rec_path.is_file() and "--strip" in argv:
            # what the driver would write for this same environment, from a driver module the smoke never touched
            fresh = th.gap_drive()
            fresh.STRIPPED_ENV = tuple(draft_stripped()) if argv[argv.index("--strip") + 1] == "draft" else ()
            rec = json.loads(rec_path.read_text())
            row = {"n": 1, "exit": 0}
            expected = fresh.with_turns(
                fresh.environment_record(fresh.child_env(), os.environ, session_id=rec["session_id"], row=None,
                                         row_commit=None, task=smoke.SMOKE_TASK, half=smoke.SMOKE_HALF, model=MODEL,
                                         claude_version=VERSION),
                [row], {id(row): SOURCE})
    return types.SimpleNamespace(
        code=code, out=out.getvalue(), turns=turns, smoke=smoke, drive=drive, folder=folder, expected=expected,
        record=json.loads(rec_path.read_text()) if rec_path is not None and rec_path.is_file() else None,
        report=json.loads((folder / "report.json").read_text())
        if folder is not None and (folder / "report.json").is_file() else None)


class TheEnvSmokeRecordsWhatItStripped(unittest.TestCase):
    """J4's evidence: the smoke says which environment it ran, builds it with child_env(), writes the driver's own
    record of it, and --compare passes two records only when they differ in the stripped names alone."""

    def out_dir(self) -> Path:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        return d / "smoke"

    def planted(self) -> dict:
        names = draft_stripped()
        self.assertEqual(len(names), 12, "the draft's stripped_env is not the twelve names")
        return {n: sentinel(n) for n in names}

    def assert_no_sentinel(self, r, planted: dict) -> None:
        texts = {"stdout": r.out}
        if r.folder is not None and r.folder.is_dir():
            texts.update({p.name: p.read_text(errors="replace") for p in r.folder.iterdir() if p.is_file()})
        leaked = sorted(f"{where}:{n}" for where, text in texts.items() for n, v in planted.items() if v and v in text)
        self.assertEqual(leaked, [], "an output carries the value of these planted variables")

    # ---- --strip is required ---------------------------------------------------------------------------

    def test_strip_is_required_and_has_no_default(self):
        out = self.out_dir()
        r = run_smoke(self, ["--out", str(out)], {})
        self.assertEqual(r.code, 2, r.out)
        self.assertIn("--strip", r.out)
        self.assertEqual(r.turns, [], "a turn was sent with no --strip")
        self.assertFalse(out.exists(), "a smoke with no --strip wrote an output")
        r = run_smoke(self, ["--strip", "some", "--out", str(out)], {})
        self.assertEqual(r.code, 2, r.out)
        self.assertEqual(r.turns, [])
        self.assertIn("--strip", load_smoke_help())

    # ---- none: nothing stripped ----------------------------------------------------------------------

    def test_strip_none_leaves_the_twelve_in_the_turns_environment(self):
        planted = self.planted()
        r = run_smoke(self, ["--strip", "none", "--out", str(self.out_dir())], planted)
        self.assertEqual(len(r.turns), 1, f"--strip none: no turn was sent (exit {r.code}): {r.out[-600:]}")
        missing = sorted(n for n in planted if n not in r.turns[0]["names"])
        self.assertEqual(missing, [], "--strip none: the turn was not given the inherited name(s)")
        self.assertEqual(r.code, 0, r.out)
        self.assertEqual(r.record["stripped_names"], [])
        self.assertEqual(r.report["strip"], "none")
        self.assert_no_sentinel(r, planted)

    # ---- draft: the draft's list stripped ----------------------------------------------------------------

    def test_strip_draft_removes_the_twelve_and_names_them(self):
        planted = self.planted()
        r = run_smoke(self, ["--strip", "draft", "--out", str(self.out_dir())], planted)
        self.assertEqual(r.code, 0, r.out)
        self.assertEqual(len(r.turns), 1)
        left = sorted(n for n in planted if n in r.turns[0]["names"])
        self.assertEqual(left, [], "--strip draft: the turn was given stripped name(s)")
        self.assertTrue(r.turns[0]["is_child_env"])
        self.assertEqual(r.record["stripped_names"], sorted(planted))
        self.assertFalse({e["name"] for e in r.record["names_present"]} & set(planted))
        self.assertEqual(r.report["strip"], "draft")
        self.assert_no_sentinel(r, planted)

    def test_the_smoke_refuses_a_child_env_that_is_not_the_strip_it_asked_for(self):
        planted = self.planted()

        def keep_one(drive) -> None:
            real = drive.child_env
            drive.child_env = lambda: {**real(), "CLAUDE_EFFORT": "x"}

        r = run_smoke(self, ["--strip", "draft", "--out", str(self.out_dir())], planted, patch_drive=keep_one)
        self.assertEqual(r.code, 2, r.out)
        self.assertIn("child_env() still carries ['CLAUDE_EFFORT']", r.out)
        self.assertEqual(r.turns, [])
        self.assert_no_sentinel(r, planted)

    # ---- the record is the driver's ---------------------------------------------------------------------

    def test_the_record_written_is_environment_record_for_that_environment(self):
        planted = {**self.planted(), "GH_TOKEN": sentinel("GH_TOKEN"), "ANTHROPIC_API_KEY": ""}
        for strip in ("none", "draft"):
            with self.subTest(strip=strip):
                r = run_smoke(self, ["--strip", strip, "--out", str(self.out_dir())], planted)
                self.assertEqual(r.code, 0, r.out)
                self.assertIsNotNone(r.expected, "no environment.json was written")
                self.assertTrue(r.record == r.expected, "the environment.json the smoke wrote is not "
                                "drive.environment_record's for that environment: keys differ "
                                f"{sorted(k for k in set(r.record) | set(r.expected) if r.record.get(k) != r.expected.get(k))}")
                raw = (r.folder / "environment.json").read_bytes()
                self.assertEqual(r.report["environment"],
                                 {"file": "environment.json", "sha256": hashlib.sha256(raw).hexdigest()})
                self.assertEqual(r.record["credential_source"]["reported"], SOURCE)
                self.assert_no_sentinel(r, planted)

    def test_the_real_checker_accepts_both_records_and_the_smoke_labels(self):
        # Both strips, the twelve planted. On 13 Sep the checker refused the stripped record for
        # CLAUDE_CODE_MESSAGING_TOKEN (the generic shape), which drive.never_stripped_problems deliberately allows;
        # the checker was brought to the driver's rule, and this is the case that caught it.
        planted = self.planted()
        for strip in ("none", "draft"):
            with self.subTest(strip=strip):
                r = run_smoke(self, ["--strip", strip, "--out", str(self.out_dir())], planted)
                self.assertEqual(r.code, 0, r.out)
                self.assertEqual(r.record["stripped_names"], sorted(planted) if strip == "draft" else [])
                ct = th.gap_check_take()
                ledger = {"environment": r.report["environment"], "claude_version": VERSION,
                          "task": r.smoke.SMOKE_TASK, "half": r.smoke.SMOKE_HALF, "model_requested": MODEL,
                          "session_id": r.record["session_id"], "turns": [{"n": 1, "exit": 0}]}
                self.assertEqual(
                    ct.environment_problems(r.folder / "transcript.jsonl", ledger, prereg.load(), None), [])

    # ---- --compare -----------------------------------------------------------------------------------

    def two_smokes(self) -> tuple[Path, Path]:
        planted = self.planted()
        a = run_smoke(self, ["--strip", "none", "--out", str(self.out_dir())], planted)
        b = run_smoke(self, ["--strip", "draft", "--out", str(self.out_dir())], planted)
        self.assertEqual((a.code, b.code), (0, 0), a.out + b.out)
        return a.folder, b.folder

    def compare(self, a: Path, b: Path):
        return run_smoke(self, ["--compare", str(a), str(b)], {})

    def rewrite(self, folder: Path, edit) -> None:
        """Edit a smoke's record and re-bind the report to its bytes, so only the edit is under test."""
        rec = json.loads((folder / "environment.json").read_text())
        edit(rec)
        (folder / "environment.json").write_text(json.dumps(rec, indent=2) + "\n")
        rep = json.loads((folder / "report.json").read_text())
        rep["environment"]["sha256"] = hashlib.sha256((folder / "environment.json").read_bytes()).hexdigest()
        (folder / "report.json").write_text(json.dumps(rep, indent=2) + "\n")

    def test_compare_passes_two_records_differing_only_by_the_stripped_names(self):
        a, b = self.two_smokes()
        self.rewrite(b, lambda rec: rec["credential_source"]["per_turn"][0].update(apiKeySource="another-source")
                     or rec["credential_source"].update(reported="another-source"))
        r = self.compare(a, b)
        self.assertEqual(r.code, 0, r.out)
        self.assertEqual(r.turns, [], "--compare opened a session")
        self.assertIn("CLAUDE_CODE_MESSAGING_TOKEN", r.out, "the names that differ are not printed")
        self.assertIn(f"reported {SOURCE!r}", r.out)
        self.assertIn("reported 'another-source'", r.out)

    def test_compare_fails_on_any_other_difference(self):
        cases = {
            "an api key state": (lambda rec: rec["api_key_variables"].update(ANTHROPIC_API_KEY="empty"),
                                 "api_key_variables differs on ['ANTHROPIC_API_KEY']"),
            "an extra non-stripped name": (lambda rec: rec["names_present"].append(
                {"name": "ZZ_EXTRA_TOKEN", "matched_by": "generic"}), "names_present differs on ZZ_EXTRA_TOKEN"),
            "a model": (lambda rec: rec.update(model_requested="claude-opus-5"), "model_requested differs"),
            "a turn's n": (lambda rec: rec["credential_source"]["per_turn"][0].update(n=2),
                           "per_turn entry 0 differs in more than its exit and source"),
        }
        for label, (edit, phrase) in cases.items():
            with self.subTest(case=label):
                a, b = self.two_smokes()
                self.rewrite(b, edit)
                r = self.compare(a, b)
                self.assertEqual(r.code, 1, f"--compare passed {label}: {r.out}")
                self.assertIn(phrase, r.out, f"--compare ignored a non-stripped difference ({label})")

    def test_compare_fails_when_nothing_was_stripped_or_a_record_is_unbound(self):
        a, _b = self.two_smokes()
        c, _d = self.two_smokes()
        r = self.compare(a, c)
        self.assertEqual(r.code, 1, r.out)
        self.assertIn("strip the same names", r.out)
        a, b = self.two_smokes()
        (b / "environment.json").write_text((b / "environment.json").read_text().replace('"none"', '"x"', 1))
        r = self.compare(a, b)
        self.assertEqual(r.code, 1, r.out)
        self.assertIn("does not record the sha256", r.out)


def load_smoke_help() -> str:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            load_smoke().main(["--help"])
        except SystemExit:
            pass
    return out.getvalue()


if __name__ == "__main__":
    unittest.main()
