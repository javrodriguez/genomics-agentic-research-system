#!/usr/bin/env python3
"""Fold 14 (Gap Study round 4): the reviewer's prompt is pinned in two named eras, OD186's one allowed change.

  P.real    the real register's nine rounds are on the first prompt, and the real BRIEF.md hashes to the second
  P.eras    round 9 on the first prompt and round 10 on the second pass the real rounds.check
  P.third   a BRIEF.md that hashes to a third prompt refuses
  P.early   a round 1-9 row on the new prompt refuses
  P.late    a round 10 row on the first prompt refuses
  P.other   a round 10 row on a third prompt refuses
  P.verify  a verify row is on the second prompt whatever its own n

A scratch repository from test_fold8's rig holds the real BRIEF.md. --witnesses runs each mutant against its bound test.
"""
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import test_fold8_review_binding as f8  # noqa: E402

RK = f8.RK
SOURCE = HERE / RK / "rounds.py"
SELECTED = None
THIRD = "c" * 64


def mutants() -> dict:
    """name -> (clause, test method, anchor, replacement). Each anchor occurs once in rounds.py."""
    return {
        "pin-third-brief": ("P.third", "Pin.test_a_third_brief_refuses", "    if prompt and prompt != PROMPT_FROM_ROUND_10:\n", "    if False:\n"),
        "pin-either-era": ("P.early", "Pin.test_a_round_1_to_9_row_on_the_new_prompt_refuses", '    if row.get("prompt_sha256") == wanted:\n',
                           '    if row.get("prompt_sha256") in (PROMPT_ROUNDS_1_TO_9, PROMPT_FROM_ROUND_10):\n'),
        "pin-either-era-late": ("P.late", "Pin.test_a_round_10_row_on_the_first_prompt_refuses", '    if row.get("prompt_sha256") == wanted:\n',
                                '    if row.get("prompt_sha256") in (PROMPT_ROUNDS_1_TO_9, PROMPT_FROM_ROUND_10):\n'),
        "pin-row-unread": ("P.other", "Pin.test_a_round_10_row_on_a_third_prompt_refuses", "        if prompt and prompt_problem(r):\n", "        if False:\n"),
        "pin-verify-first": ("P.verify", "Pin.test_a_verify_row_is_on_the_second_prompt", 'first = row["kind"] == "prefreeze" and row["n"]', 'first = row["n"]'),
    }


def load_rounds(repo: Path):
    """f8.load_rounds, on this run's text of rounds.py."""
    text = SOURCE.read_text()
    if SELECTED is not None:
        _, _, old, new = mutants()[SELECTED]
        assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
        text = text.replace(old, new)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rounds.py"
        path.write_text(text)
        spec = importlib.util.spec_from_file_location("fold14_rounds", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    mod.REPO = repo
    mod.STUDY_DIR = repo / f8.study.STUDY_REL
    mod.REGISTER = mod.STUDY_DIR / RK / "rounds.json"
    mod.BRIEF = mod.STUDY_DIR / RK / "BRIEF.md"
    return mod


f8.load_rounds = load_rounds
PIN = load_rounds(HERE.parent.parent)


class Pin(unittest.TestCase):
    def check(self, *rows: tuple, brief: bytes | None = None) -> tuple[int, str]:
        """rows are (n, prompt), each registered and reviewed on the rig, under the real BRIEF.md or `brief`."""
        with f8.rig() as r:
            r.path(f"{RK}/BRIEF.md").write_bytes((HERE / RK / "BRIEF.md").read_bytes() if brief is None else brief)
            r.commit("the brief")
            for n, prompt in rows:
                r.register(n, prompt_sha256=prompt)
                r.review(n)
            return r.rounds_check()

    def test_the_real_register_and_brief(self):
        rows = json.loads((HERE / RK / "rounds.json").read_text())["rows"]
        early = [r for r in rows if r["kind"] == "prefreeze" and r["n"] <= PIN.LAST_ROUND_ON_THE_FIRST_PROMPT]
        self.assertEqual(len(early), 9, "P.real")
        self.assertEqual({r["prompt_sha256"] for r in early}, {PIN.PROMPT_ROUNDS_1_TO_9}, "P.real")
        self.assertTrue(PIN.PROMPT_ROUNDS_1_TO_9.startswith("4246efa5b409"), "P.real")
        self.assertEqual(PIN.sha256_bytes((HERE / RK / "BRIEF.md").read_bytes()), PIN.PROMPT_FROM_ROUND_10, "P.real")

    def test_the_two_eras_pass(self):
        code, said = self.check((9, PIN.PROMPT_ROUNDS_1_TO_9), (10, PIN.PROMPT_FROM_ROUND_10))
        self.assertEqual(code, 0, f"P.eras: {said}")

    def test_a_third_brief_refuses(self):
        code, said = self.check((9, PIN.PROMPT_ROUNDS_1_TO_9), brief=b"a third prompt\n")
        self.assertEqual(code, 1, f"P.third: {said}")
        self.assertIn("no third", said, "P.third")

    def test_a_round_1_to_9_row_on_the_new_prompt_refuses(self):
        code, said = self.check((9, PIN.PROMPT_FROM_ROUND_10))
        self.assertEqual(code, 1, f"P.early: {said}")
        self.assertIn("prefreeze round 9 was launched", said, "P.early")

    def test_a_round_10_row_on_the_first_prompt_refuses(self):
        code, said = self.check((10, PIN.PROMPT_ROUNDS_1_TO_9))
        self.assertEqual(code, 1, f"P.late: {said}")
        self.assertIn("prefreeze round 10 was launched", said, "P.late")

    def test_a_round_10_row_on_a_third_prompt_refuses(self):
        code, said = self.check((10, THIRD))
        self.assertEqual(code, 1, f"P.other: {said}")
        self.assertIn("prefreeze round 10 was launched", said, "P.other")

    def test_a_verify_row_is_on_the_second_prompt(self):
        self.assertIsNone(PIN.prompt_problem({"kind": "verify", "n": 1, "prompt_sha256": PIN.PROMPT_FROM_ROUND_10}), "P.verify")
        self.assertIsNotNone(PIN.prompt_problem({"kind": "verify", "n": 1, "prompt_sha256": PIN.PROMPT_ROUNDS_1_TO_9}), "P.verify")


def run_witnesses() -> int:
    for name, (clause, method, _, _) in mutants().items():
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name, method],
                             capture_output=True, text=True, timeout=300)
        red = got.returncode != 0 and re.search(r"(?<![\w.])" + re.escape(clause) + r"(?![\w.])", got.stderr) is not None
        print(f"witness {name} -> {method} {clause}: {'RED' if red else 'FAIL'}", flush=True)
        if not red:
            print(got.stdout[-1500:] + got.stderr[-1500:], flush=True)
            return 1
    print(f"test_fold14 witnesses: {len(mutants())}/{len(mutants())} red", flush=True)
    return 0


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses())
    if "--mutant" in sys.argv:
        at = sys.argv.index("--mutant")
        SELECTED = sys.argv[at + 1]
        del sys.argv[at:at + 2]
        PIN = load_rounds(HERE.parent.parent)
    unittest.main(verbosity=1)
