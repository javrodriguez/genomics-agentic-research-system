"""Mutations for the pre-registration's round-2 content (CP7), registered by mutations.register_topic_modules.

Each runs its guard unmutated first (Sandbox.control), plants one defect in the throwaway copy's draft or suites, and
requires the guard to go red naming it (structural lessons 12 and 13). The prediction guard reads round 1's results
files and the regrade records, and the file-list guard reads git history, so those mutations bring what they need:
round 1's results into the sandbox, and a git sandbox whose objects include the real repository's.
"""

from __future__ import annotations

import json
import shutil

import study
from mutations import NotYetApplicable, Sandbox

CLS = "ThePreRegistrationIsComplete"


def _guard(s: Sandbox, *tests: str) -> list[str]:
    return [str(s.study / "test_harness.py"), *tests]


def _round_one_results(s: Sandbox) -> None:
    src = study.ROUND1 / "results"
    if not src.is_dir():
        raise NotYetApplicable(f"round 1's results are not in this tree ({study.ROUND1_REL}/results)")
    dest = s.root / study.ROUND1_REL / "results"
    if not dest.exists():
        shutil.copytree(src, dest)


def _edit_draft(s: Sandbox, change) -> None:
    path = s.study / "prereg-draft.json"
    doc = json.loads(path.read_text())
    change(doc)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def _red(s: Sandbox, guard: list[str], phrase: str, what: str) -> tuple[int, str]:
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, phrase), f"test_harness.py {what}"


def m_prediction_flipped(s: Sandbox) -> tuple[int, str]:
    """One prediction says the opposite of what round 1's files give under the rule, its statement kept consistent."""
    _round_one_results(s)
    guard = _guard(s, f"{CLS}.test_every_prediction_re_derives_from_round_ones_files")
    s.control(guard)

    def flip(doc):
        p = doc["predictions"][0]
        p["predicted"] = "holds" if p["predicted"] == "does not hold" else "does not hold"
        p["statement"] = f"predicted {p['predicted']} · basis: informed by {' and '.join(p['informed_by'])}"
    _edit_draft(s, flip)
    return _red(s, guard, "is not what round 1's files give", f"{CLS} (a prediction flipped)")


def m_prediction_marked_blind(s: Sandbox) -> tuple[int, str]:
    """A prediction claims to be blind, which no round-2 prediction can be."""
    guard = _guard(s, f"{CLS}.test_eighteen_predictions_none_blind_each_in_the_fixed_form")
    s.control(guard)
    _edit_draft(s, lambda doc: doc["predictions"][0].__setitem__("basis", "blind"))
    return _red(s, guard, "a round-2 prediction is never blind", f"{CLS} (a prediction marked blind)")


def m_system_under_test_file_dropped(s: Sandbox) -> tuple[int, str]:
    """One changed file is dropped from the draft's list of what differs from round 1."""
    guard = _guard(s, f"{CLS}.test_the_system_under_test_difference_is_the_git_difference")
    s.control(guard)
    _edit_draft(s, lambda doc: doc["system_under_test"]["differs_from_round_1"]["files"].pop())
    return _red(s, guard, "the draft's file list is not what git reports", f"{CLS} (a changed file dropped)")


def m_fix_names_a_missing_record(s: Sandbox) -> tuple[int, str]:
    """A fix points at a regrade record that does not exist."""
    guard = _guard(s, f"{CLS}.test_every_fix_names_paths_that_exist")
    s.control(guard)
    _edit_draft(s, lambda doc: doc["fixes"][0].__setitem__("regrade_record",
                                                            doc["fixes"][0]["regrade_record"] + ".missing"))
    return _red(s, guard, "a fix names a record that does not exist", f"{CLS} (a fix pointing nowhere)")


def m_round_two_walk_message_left_out(s: Sandbox) -> tuple[int, str]:
    """A message from one of this study's own walks is dropped from its round-2 suite."""
    guard = _guard(s, "CaseSuitesOnRoundTwoWalksLive.test_every_walk_message_is_a_case")
    s.control(guard)
    path = s.study / "cases" / "round-2" / "plan-gate.json"
    doc = json.loads(path.read_text())
    doc["cases"].pop()
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return _red(s, guard, "is not in the case suite", "CaseSuitesOnRoundTwoWalksLive (a walk message left out)")


MUTATIONS = [
    ("a round-2 prediction that its round-1 files do not give", m_prediction_flipped, False),
    ("a round-2 prediction marked blind", m_prediction_marked_blind, False),
    ("a changed gars file dropped from the system under test's difference", m_system_under_test_file_dropped, "objects"),
    ("a fix naming a record that does not exist", m_fix_names_a_missing_record, False),
    ("a round-2 walk message left out of its suite", m_round_two_walk_message_left_out, False),
]
