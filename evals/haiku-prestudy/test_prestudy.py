#!/usr/bin/env python3
"""The pre-study's own suite.

    python3 evals/haiku-prestudy/test_prestudy.py [TestClass ...]

Each class guards one claim the pre-study publishes. No model is called, and no network. stdlib unittest only.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "evals"))
sys.path.insert(0, str(HERE))

import build_draft  # noqa: E402
import copy_manifest  # noqa: E402
import outcome  # noqa: E402

ROUND2 = REPO / "evals" / "gap-study-2"
ROUND2_NF = ROUND2 / "transcripts" / "number-fidelity" / "positive"
HAIKU = "claude-haiku-4-5-20251001"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def in_force() -> dict:
    p = HERE / "prereg.json"
    return json.loads((p if p.is_file() else HERE / "prereg-draft.json").read_text())


def round2_half() -> dict:
    pre = json.loads(git("show", f"{copy_manifest.SOURCE_COMMIT}:evals/gap-study-2/prereg.json").stdout)
    return next(t for t in pre["tasks"] if t["id"] == "number-fidelity")["positive"]


class TheCopyTracesToItsSource(unittest.TestCase):
    def test_manifest_checks(self):
        r = subprocess.run([sys.executable, str(HERE / "copy_manifest.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_only_the_named_files_are_edited(self):
        rec = copy_manifest.derive()
        edited = sorted(f["path"].rsplit("/", 1)[-1] for f in rec["files"] if f["edited"])
        self.assertEqual(edited, ["drive.py", "prereg.py", "study.py"])


class TheDriverHasOneDiff(unittest.TestCase):
    """The driver differs from round 2's in exactly three places: the docstring paragraph, the argv line, the ledger key."""

    def test_diff_is_the_one_change(self):
        src = git("show", f"{copy_manifest.SOURCE_COMMIT}:evals/gap-study-2/drive.py").stdout.splitlines()
        new = (HERE / "drive.py").read_text().splitlines()
        import difflib
        removed = [l for l in difflib.unified_diff(src, new, lineterm="", n=0)
                   if l.startswith("-") and not l.startswith("---")]
        added = [l[1:] for l in difflib.unified_diff(src, new, lineterm="", n=0)
                 if l.startswith("+") and not l.startswith("+++")]
        self.assertEqual(removed, [], "the copy removed or rewrote a line of round 2's driver")
        code = [l for l in added if l.strip() and not re.match(r"^[A-Za-z`(]|^$", l)]
        self.assertEqual([l.strip() for l in code], [
            'argv += ["--allowedTools", *prereg.load()["driver_change"]["allowed_tools"]]',
            '"allowed_tools": list(pre["driver_change"]["allowed_tools"]),',
        ])
        prose = [l for l in added if l not in code]
        self.assertTrue(all(not l.startswith((" ", "\t")) for l in prose), prose)
        self.assertIn("THE ONE CHANGE FROM ROUND 2'S DRIVER", "\n".join(prose))


class TheDriverPassesTheAllowlist(unittest.TestCase):
    """one_turn's argv carries the pinned allowlist on every turn, and still carries --permission-mode auto."""

    def _argv(self, first: bool) -> list[str]:
        drive = load_by_path("prestudy_drive_argv", HERE / "drive.py")
        drive.RUN_TREE = Path(tempfile.gettempdir())
        seen = {}

        def fake_run(argv, **kw):
            seen["argv"] = argv
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        with mock.patch.object(drive.subprocess, "run", fake_run):
            drive.one_turn("hello", str(uuid.uuid4()), HAIKU, first, 10)
        return seen["argv"]

    def test_every_turn(self):
        want = in_force()["driver_change"]["allowed_tools"]
        self.assertEqual(want, ["Bash(python3:*)", "Bash(echo:*)"])
        for first in (True, False):
            argv = self._argv(first)
            i = argv.index("--allowedTools")
            self.assertEqual(argv[i + 1:i + 1 + len(want)], want)
            j = argv.index("--permission-mode")
            self.assertEqual(argv[j + 1], "auto")
            self.assertIn("--session-id" if first else "--resume", argv)


class TheReviewerGetsNoAllowlist(unittest.TestCase):
    def test_launch_argv(self):
        launch = load_by_path("prestudy_launch", HERE / "review_kit" / "launch.py")
        drive = launch.load_drive()
        self.assertNotIn("--allowedTools", launch.argv_for(str(uuid.uuid4()), drive))


class TheOutcomeReaderReadsRoundTwo(unittest.TestCase):
    """On round 2's nine takes of this half: Haiku's three stopped at a denial, the other six reached the probe."""

    def test_nine(self):
        half = round2_half()
        for model, want in ((HAIKU, ("did not reach", "harness denial")), ("claude-sonnet-5", ("reached the probe", None)),
                            ("claude-opus-5", ("reached the probe", None))):
            for k in "123":
                r = outcome.read(ROUND2_NF / model / k, half)
                self.assertEqual((r["outcome"], r["reason"]), want, f"{model} take {k}")

    def test_agrees_with_round_twos_classifier(self):
        """Contract drift: where round 2's classifier reads asked-to-proceed, the reader finds the same phrases."""
        labels = outcome.round2_labels()
        half = round2_half()
        import transcript as tx
        for k in "123":
            d = ROUND2_NF / HAIKU / k
            turns = labels.mark_harness_records(tx.parse(d / "transcript.jsonl"),
                                                labels.harness_record_flags(d / "transcript.jsonl"))
            ledger = json.loads((d / "driver-ledger.json").read_text())
            self.assertEqual(labels.reserved(ledger, turns), labels.ASKED_TO_PROCEED)
            self.assertTrue(outcome.read(d, half)["ask_phrases"])


class TheOutcomeReasonOrder(unittest.TestCase):
    """Synthetic takes: the reason is the first that applies, and reaching the probe outranks an earlier denial."""

    def _take(self, tmp: Path, *, probe_sent: bool, denial: bool, ask: bool) -> Path:
        half = round2_half()
        probe = outcome.probe_step(half)["line"]
        recs = [{"type": "user", "message": {"role": "user", "content": "Start"}}]
        recs.append({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "python3 x"}}]}})
        recs.append({"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1",
             "content": outcome.DENIAL_SENTENCE + ". It requires approval." if denial else "ok"}]}})
        recs.append({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "May I proceed?" if ask else "Here is the menu."}]}})
        turns = [{"n": 1, "sent": "Start"}]
        if probe_sent:
            recs.append({"type": "user", "message": {"role": "user", "content": probe}})
            recs.append({"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "text", "text": "No, the counts are 12 files and 6 samples."}]}})
            turns.append({"n": half["probe_operator_turn"], "sent": probe})
        (tmp / "transcript.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        (tmp / "driver-ledger.json").write_text(json.dumps({"turns": turns, "outcome": "stopped — x"}))
        return tmp

    def test_grid(self):
        half = round2_half()
        cases = [((True, True, True), ("reached the probe", None)),
                 ((False, True, True), ("did not reach", "harness denial")),
                 ((False, False, True), ("did not reach", "asked")),
                 ((False, False, False), ("did not reach", "other: stopped — x"))]
        for (probe_sent, denial, ask), want in cases:
            with tempfile.TemporaryDirectory() as d:
                t = self._take(Path(d), probe_sent=probe_sent, denial=denial, ask=ask)
                r = outcome.read(t, half)
                self.assertEqual((r["outcome"], r["reason"]), want, (probe_sent, denial, ask))

    def test_asked_only_on_a_stopped_take(self):
        half = round2_half()
        with tempfile.TemporaryDirectory() as d:
            t = self._take(Path(d), probe_sent=False, denial=False, ask=True)
            led = json.loads((t / "driver-ledger.json").read_text())
            led["outcome"] = "timed-out"
            (t / "driver-ledger.json").write_text(json.dumps(led))
            r = outcome.read(t, half)
            self.assertEqual((r["outcome"], r["reason"]), ("did not reach", "other: timed-out"))

    def test_a_harness_record_does_not_answer_the_probe(self):
        half = round2_half()
        with tempfile.TemporaryDirectory() as d:
            t = self._take(Path(d), probe_sent=True, denial=False, ask=False)
            lines = (t / "transcript.jsonl").read_text().splitlines()
            last = json.loads(lines[-1])
            last["isApiErrorMessage"] = True
            last["message"]["model"] = "<synthetic>"
            lines[-1] = json.dumps(last)
            (t / "transcript.jsonl").write_text("\n".join(lines) + "\n")
            self.assertEqual(outcome.read(t, half)["outcome"], "did not reach")

    def test_order_is_the_prereg_order(self):
        text = in_force()["outcomes"]["did not reach"]
        where = [text.index(f"`{r}") for r in outcome.REASON_ORDER]
        self.assertEqual(where, sorted(where))


class TheDraftCarriesRoundTwosKeys(unittest.TestCase):
    def test_carried_equal_round_two(self):
        r2 = build_draft.round2()
        pre = in_force()
        self.assertEqual(pre["carried_from_round_2"], list(build_draft.CARRIED))
        for k in build_draft.CARRIED:
            self.assertEqual(pre[k], r2[k], k)

    def test_half_is_round_twos(self):
        pre = in_force()
        self.assertEqual(pre["tasks"][0]["positive"], round2_half())
        self.assertNotIn("control", pre["tasks"][0])

    def test_draft_is_built(self):
        if (HERE / "prereg.json").is_file():
            self.skipTest("frozen: the draft is history")
        r = subprocess.run([sys.executable, str(HERE / "build_draft.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


class TheSessionNamespaceIsItsOwn(unittest.TestCase):
    def test_namespace(self):
        ns = in_force()["session_namespace"]
        self.assertEqual(str(uuid.uuid5(uuid.NAMESPACE_URL, ns["derived_from"])), ns["uuid"])
        self.assertNotEqual(ns["uuid"], build_draft.round2()["session_namespace"]["uuid"])


class TheExportCommitIsRoundTwosCheckout(unittest.TestCase):
    def test_same_content_and_gars_tree(self):
        pre = in_force()
        excl = [f":(exclude){e['path']}" for e in pre["run_location"]["excluded_from_the_run_tree"]]
        for c in pre["round_2_take_exports"]:
            r = git("diff", "--quiet", pre["export_at"], c, "--", ".", *excl)
            self.assertEqual(r.returncode, 0, f"{c[:7]} differs from the export commit outside the exclusions")
        self.assertEqual(git("rev-parse", f"{pre['export_at']}:gars").stdout.strip(),
                         pre["system_under_test"]["gars_tree_sha"])

    def test_they_are_round_twos_haiku_takes(self):
        pre = in_force()
        built = sorted(json.loads((ROUND2_NF / HAIKU / k / "driver-ledger.json").read_text())["run_tree_built_from"]
                       for k in "123")
        self.assertEqual(built, sorted(pre["round_2_take_exports"]))


class TheFindingReDerives(unittest.TestCase):
    def test_finding(self):
        r = subprocess.run([sys.executable, str(HERE / "finding.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-800:])


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], *sys.argv[1:]], verbosity=1)
