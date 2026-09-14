#!/usr/bin/env python3
"""The round-1 environment regrade record re-derives, and an edited record is refused.

    python3 evals/gap-study-2/test_harness.py TheRoundOneEnvironmentRegradeReDerives

WHY (round 2, CP3, fix 4). verification/round1-regrade/environment.json states what round 2's environment
instrument reads on round 1's 108 committed graded takes: every one refused `[environment-record]`, evidenced 0
of 108 by costs.py's dollar line, and round 1's effort keys read per model. A record that only states that is a
statement again, the thing Ruling 34 found. So the script that wrote it is committed beside it, `--check`
re-derives it byte for byte, and this class runs the check, reads the counts, and plants an edit in a copy to see
the check go red after a green control on the unedited copy.

Round 1's transcripts are read as data through study.ROUND1. They are committed, so the skip below should never
fire; if it does, it says why rather than passing.

No model, no network. stdlib only.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import study
import test_harness as th

HERE = th.HERE
REPO = th.REPO
REGRADE = HERE / "verification" / "round1-regrade"
SCRIPT = REGRADE / "regrade_environment.py"
RECORD = REGRADE / "environment.json"


def _run(*args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != th.POISON_ENV}
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          cwd=str(REPO), env=env)


class TheRoundOneEnvironmentRegradeReDerives(unittest.TestCase):

    def setUp(self):
        transcripts = study.ROUND1 / "transcripts"
        if not (study.ROUND1 / "takes.json").is_file() or not any(transcripts.glob("*/*/*/*/transcript.jsonl")):
            reason = (f"round 1's committed takes are not in this tree ({study.ROUND1_REL}/takes.json and its "
                      f"transcripts), so the regrade record cannot be re-derived here")
            print(reason)
            self.skipTest(reason)

    def test_the_committed_record_is_what_the_script_re_derives(self):
        r = _run("--check")
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-1500:])
        self.assertIn("is what the regrade re-derives", r.stdout)

    def test_every_round_one_take_is_refused_and_none_is_evidenced(self):
        record = json.loads(RECORD.read_text())
        self.assertEqual(record["record"], "what the round-2 instrument reads on round 1's committed transcripts "
                                           "— not round 1's result")
        self.assertEqual(record["counts"], {"graded": 108, "refused_environment_record": 108, "evidenced": 0})
        self.assertEqual(len(record["takes"]), 108, "the counts are not over the takes the record lists")
        for t in record["takes"]:
            self.assertTrue(t["refusals"] and t["refusals"][0].startswith("[environment-record] "), t)
        self.assertTrue(record["dollar_line"].startswith("$0 as the operator states it; evidenced by 0 of 108; "),
                        record["dollar_line"][:200])

    def test_the_record_names_no_machine_path(self):
        text = RECORD.read_text()
        temp = Path(tempfile.gettempdir())
        for needle in (str(REPO), str(Path.home()), str(Path.home().parent) + os.sep, str(temp), str(temp.resolve())):
            self.assertNotIn(needle, text, "the regrade record carries a machine path")

    def test_an_edited_copy_of_the_record_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "environment.json"
            shutil.copyfile(RECORD, copy)
            control = _run("--check", "--record", str(copy))
            self.assertEqual(control.returncode, 0, "the unedited copy is refused, so the planted edit proves "
                                                    "nothing:\n" + control.stdout[-1500:] + control.stderr[-1500:])
            record = json.loads(copy.read_text())
            record["counts"]["evidenced"] = 1
            copy.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
            r = _run("--check", "--record", str(copy))
            self.assertEqual(r.returncode, 1, "an edited record passed the re-derivation:\n" + r.stdout[-1500:])
            self.assertIn("is NOT what the regrade re-derives", r.stdout)


if __name__ == "__main__":
    unittest.main()
