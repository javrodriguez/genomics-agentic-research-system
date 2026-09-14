#!/usr/bin/env python3
"""The bill (done-line 13, fix 4): the dollar line is written by costs.py and evidenced take by take, or its gap
is named take by take.

    python3 evals/gap-study-2/test_harness.py TheBillIsEvidencedTakeByTake

Round 1's COSTS.md carried a dollar line typed by hand and said the per-take environment records evidenced it,
while no such record existed (Ruling 34). Here the line is rendered by costs.py under its own heading, bound by
`--check`, and takes the evidenced form only when every graded take's environment record is valid (the checker
says so), records no API-key and no billing-route variable set, and reports the pre-registered subscription
source on every turn.

The unit cases read test-fixtures/bill/ (two synthetic graded takes, each with a transcript, a driver ledger and
a schema-1 environment record) in a temporary copy, with the checker, the row commits and the pre-registration
handed in, so each gap is planted alone. The command-line cases run costs.py as a subprocess in a copy of the
study, with the real checker and the real draft, and assert only what holds whichever state those are in.

No model, no network. stdlib only.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import test_harness as th

HERE = Path(__file__).resolve().parent
FIX = HERE / "test-fixtures" / "bill"
SUB = "fixture-subscription-source"
SENTINEL_COST = "0.4213"
A = ("scope-read", "positive", "claude-opus-5", "1")
B = ("template-adherence", "control", "claude-sonnet-5", "2")
SLOT_A = "scope-read positive claude-opus-5 take 1"
SLOT_B = "template-adherence control claude-sonnet-5 take 2"
COMMITS = {0: "a" * 40, 1: "b" * 40}
ENVIRONMENT_RECORD = {
    "api_key_variables": ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_FOUNDRY_API_KEY",
                          "ANTHROPIC_AWS_API_KEY", "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR", "AWS_BEARER_TOKEN_BEDROCK"],
    "billing_route_variables": ["CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
                                "ANTHROPIC_BASE_URL", "CLAUDE_CODE_API_BASE_URL"],
    "subscription_token_variables": ["CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
                                     "CLAUDE_CODE_SESSION_ACCESS_TOKEN"],
    "credential_source_key": "system/init.apiKeySource",
    "subscription_source": SUB,
}
EVIDENCED = (f"$0, evidenced by 2 of 2 environment records (no API-key variable set; the harness reported "
             f"credential source {SUB} on every turn)")
NOT_EVIDENCED = "$0 as the operator states it; evidenced by "
NO_SUB = "no subscription source is pre-registered to match its turns against"
HEADING = "## Dollars billed beyond the standing subscription"


def not_evidenced(n: int, *gaps: str) -> str:
    return f"{NOT_EVIDENCED}{n} of 2; not evidenced: " + "; ".join(gaps)


def dollar_line(text: str) -> str:
    """The line the script writes under the bill's heading (a blank line, the line, a blank line)."""
    lines = text.split("\n")
    return lines[lines.index(HEADING) + 2]


class TheBillIsEvidencedTakeByTake(unittest.TestCase):

    def setUp(self):
        self.costs = th.gap_module("costs")
        self.fresh()

    def fresh(self):
        self.study = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.study, True)
        shutil.copytree(FIX / "transcripts", self.study / "transcripts")
        self.calls: list[tuple] = []
        self.refusals: dict[Path, list[str]] = {}
        self.pre = {"environment_record": dict(ENVIRONMENT_RECORD)}
        self.costs.HERE = self.study
        self.costs.environment_checker = lambda: self.checker
        self.costs.row_commits = lambda: dict(COMMITS)

    def checker(self, path, ledger, pre, row_commit):
        self.calls.append((path.parent.relative_to(self.study / "transcripts").parts, ledger.get("row"),
                           row_commit, pre is self.pre))
        return list(self.refusals.get(path.parent, []))

    def take(self, slot) -> Path:
        return self.study / "transcripts" / Path(*slot)

    def edit_record(self, slot, change) -> None:
        p = self.take(slot) / "environment.json"
        d = json.loads(p.read_text())
        change(d)
        p.write_text(json.dumps(d, indent=2) + "\n")

    def bill(self) -> dict:
        with th.injected_prereg(self.pre):
            return self.costs.collect()

    def environment_cells(self, got) -> list[str]:
        return [row.rsplit("|", 2)[1].strip() for row in self.costs.tables(got)["Per take"][2:]]

    # ------------------------------------------------------------------ the evidenced form

    def test_every_valid_record_evidences_the_bill(self):
        got = self.bill()
        self.assertEqual(got["bill"], EVIDENCED)
        self.assertEqual(self.environment_cells(got), ["evidenced", "evidenced"])
        # every take judged by the checker, with its own ledger row's commit and the pre-registration in force
        self.assertEqual(sorted(self.calls), [(A, 0, COMMITS[0], True), (B, 1, COMMITS[1], True)])

    # ------------------------------------------------------------------ each gap, named on its take

    def test_each_gap_is_named_on_its_take(self):
        def api_key(d):
            d["api_key_variables"]["ANTHROPIC_API_KEY"] = "set"
            d["api_key_set"] = True

        def route(d):
            d["billing_route_variables"]["CLAUDE_CODE_USE_BEDROCK"] = "set"
            d["billing_route_set"] = True

        def null_turn(d):
            d["credential_source"]["per_turn"][1]["apiKeySource"] = None

        def unreported_turn(d):
            del d["credential_source"]["per_turn"][0]["apiKeySource"]

        def other_source(d):
            d["credential_source"]["per_turn"][0]["apiKeySource"] = "ANTHROPIC_API_KEY"

        def no_turns(d):
            d["credential_source"]["per_turn"] = []

        def flag_left_out(d):
            del d["api_key_set"]

        def value_as_name(d):
            d["api_key_variables"]["sk-fixture-not-a-name"] = "set"

        cases = {
            "a missing record": (None, "no environment record"),
            "an API-key variable set": (api_key, "an API-key variable is set (ANTHROPIC_API_KEY)"),
            "a billing route set": (route, "a billing-route variable is set (CLAUDE_CODE_USE_BEDROCK)"),
            "a turn with a null source": (null_turn, "turn 2 reported no credential source"),
            "a turn with no source key": (unreported_turn, "turn 1 reported no credential source"),
            "a non-subscription source": (other_source,
                                          f"turn 1 reported credential source ANTHROPIC_API_KEY, not {SUB}"),
            "a record with no turn": (no_turns, "no turn's credential source is recorded"),
            "api_key_set left out": (flag_left_out, "its record does not say api_key_set false"),
            "a value where a name belongs": (value_as_name,
                                             "an API-key variable is set (1 key(s) that are not variable names)"),
            "a record the checker refuses": ("refuse", "the checker refuses its record ([environment-record] the "
                                                       "session id is not the transcript's, it is another)"),
        }
        for kind, (plant, gap) in cases.items():
            with self.subTest(kind):
                self.fresh()
                if plant is None:
                    (self.take(A) / "environment.json").unlink()
                elif plant == "refuse":
                    self.refusals[self.take(A)] = ["[environment-record] the session id is not the transcript's; "
                                                   "it is another"]
                else:
                    self.edit_record(A, plant)
                got = self.bill()
                self.assertEqual(got["bill"], not_evidenced(1, f"{SLOT_A}: {gap}"))
                self.assertEqual(self.environment_cells(got), ["not evidenced", "evidenced"])
                self.assertNotIn("sk-fixture-not-a-name", got["bill"])

    def test_no_subscription_source_means_no_evidence(self):
        """While the pre-registration names no subscription source the evidenced form is impossible, on every take."""
        for kind, spec in {"subscription_source null": {**ENVIRONMENT_RECORD, "subscription_source": None},
                           "no environment_record in the draft": None}.items():
            with self.subTest(kind):
                self.fresh()
                self.pre = {} if spec is None else {"environment_record": spec}
                got = self.bill()
                self.assertEqual(got["bill"], not_evidenced(0, f"{SLOT_A}: {NO_SUB}", f"{SLOT_B}: {NO_SUB}"))
        with self.subTest("a missing record as well"):
            self.fresh()
            self.pre = {"environment_record": {**ENVIRONMENT_RECORD, "subscription_source": None}}
            (self.take(B) / "environment.json").unlink()
            self.assertEqual(self.bill()["bill"], not_evidenced(
                0, f"{SLOT_A}: {NO_SUB}", f"{SLOT_B}: no environment record, {NO_SUB}"))

    def test_no_checker_means_no_record_is_valid(self):
        self.costs.environment_checker = lambda: None
        gap = "no record checker exists (check_take.environment_problems), so no record is judged valid"
        self.assertEqual(self.bill()["bill"], not_evidenced(0, f"{SLOT_A}: {gap}", f"{SLOT_B}: {gap}"))

    # ------------------------------------------------------------------ bound by --check

    def test_check_refuses_a_hand_edited_dollar_line(self):
        (self.take(A) / "environment.json").unlink()
        got = self.bill()
        # The file as the script should write it, with the line placed under its heading here rather than by
        # render, so the binding below is tested on its own: a render that stopped writing the line would leave
        # every edit unseen, and that is the refusal this test names.
        placed = self.costs.TEMPLATE.replace(HEADING + "\n", f"{HEADING}\n\n{got['bill']}\n", 1)
        text = self.costs.render(placed, got)
        lines = text.split("\n")
        at = lines.index(HEADING) + 2
        edits = {
            "the line typed into the evidenced form": lines[:at] + [EVIDENCED] + lines[at + 1:],
            "a count changed": lines[:at] + [got["bill"].replace("evidenced by 1 of 2", "evidenced by 2 of 2")]
            + lines[at + 1:],
            "a note typed under the heading": lines[:at + 1] + ["The operator confirms this."] + lines[at + 1:],
            "the line deleted": lines[:at] + lines[at + 1:],
        }
        for kind, edited in edits.items():
            with self.subTest(kind):
                edited = "\n".join(edited)
                self.assertNotEqual(edited, text)
                self.assertNotEqual(self.costs.render(edited, got), edited, "a hand-edited dollar line went unseen")
                self.assertEqual(self.costs.render(edited, got), text)
        self.assertEqual(dollar_line(text), got["bill"])
        self.assertEqual(self.costs.render(text, got), text, "the file the script writes is not what it checks")
        self.assertEqual(self.costs.render(self.costs.TEMPLATE, got), text, "--write from the template is not the file")

    def test_the_cost_figure_and_the_environment_class_are_never_read(self):
        transcript = (self.take(A) / "transcript.jsonl").read_text()
        self.assertIn(f'"total_cost_usd": {SENTINEL_COST}', transcript, "the fixture carries no cost figure; "
                                                                        "that is not a pass")
        text = self.costs.render(self.costs.TEMPLATE, self.bill())
        self.assertNotIn("total_cost_usd", text)
        self.assertNotIn(SENTINEL_COST, text)
        source = (HERE / "costs.py").read_text()
        self.assertNotIn("total_cost_usd", source)
        self.assertNotIn("environment_class", source)

    # ------------------------------------------------------------------ through the command line

    def test_write_on_the_empty_study_writes_nothing_and_says_no_takes_yet(self):
        root, dest = th.study_copy(self, files=("costs.py",))
        r = th.run_py(dest / "costs.py", "--write", cwd=root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no takes yet", r.stdout)
        self.assertFalse((dest / "COSTS.md").exists(), "--write wrote a file on the empty study")
        r = th.run_py(dest / "costs.py", "--check", cwd=root)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "no takes yet"), r.stderr)

    def test_the_bill_end_to_end_through_the_command_line(self):
        """A copy of the study with the fixture's takes planted and no COSTS.md: --write creates it, --check binds
        it, and a hand edit of the dollar line fails --check. Neither takes' record can be evidence here (no row
        commit exists in the copy, and the draft's checker and subscription source are what they are), so the line
        is the not-evidenced form naming both takes."""
        root, dest = th.study_copy(self)
        shutil.copytree(FIX / "transcripts", dest / "transcripts")
        costs = dest / "costs.py"

        r = th.run_py(costs, "--write", cwd=root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = (dest / "COSTS.md").read_text()
        line = dollar_line(text)
        self.assertTrue(line.startswith(NOT_EVIDENCED + "0 of 2; not evidenced: "), line)
        self.assertIn(f"{SLOT_A}: ", line)
        self.assertIn(f"{SLOT_B}: ", line)
        self.assertEqual(text.count("| not evidenced |"), 2, text)

        r = th.run_py(costs, "--check", cwd=root)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "COSTS.md is what the reader writes"), r.stderr)

        (dest / "COSTS.md").write_text(text.replace(line, EVIDENCED))
        r = th.run_py(costs, "--check", cwd=root)
        self.assertEqual(r.returncode, 1, "a hand-edited dollar line went unseen: " + r.stdout + r.stderr)
        self.assertIn("is NOT what the reader writes", r.stdout)

        (dest / "COSTS.md").write_text(text)
        r = th.run_py(costs, cwd=root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"dollars billed beyond the standing subscription: {line}", r.stdout)
        for out in (r.stdout, text):
            self.assertNotIn("total_cost_usd", out)
            self.assertNotIn(SENTINEL_COST, out)


if __name__ == "__main__":
    unittest.main()
