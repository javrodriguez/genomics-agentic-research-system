#!/usr/bin/env python3
"""The call-site mutations for round 1's process lessons as guards (CP2), registered by mutations.py.

Each breaks one guard where it runs, in a throwaway copy, watches the guard green first, and requires it to go
red naming what was planted (structural lessons 12 and 13).
"""

from __future__ import annotations

import hashlib
import json

from mutations import Sandbox, _edit, _prereg, _th


def m_unlisted_head_reader(s: Sandbox) -> tuple[int, str]:
    """Lesson 7: a HEAD read added to the code with no line in the draft's head_readers."""
    s.control(_th(s, "EveryHeadReaderIsListed"))
    with (s.study / "takes.py").open("a") as fh:
        fh.write('\n_UNLISTED_READER = ["git", "rev-parse", "HEAD~1"]\n')
    code, out = s.run_out(_th(s, "EveryHeadReaderIsListed"))
    return Sandbox.expect(code, out, "takes.py names 'HEAD~1'"), "test_harness.py EveryHeadReaderIsListed"


def m_checklist_named_class_deleted(s: Sandbox) -> tuple[int, str]:
    """Lesson 5: a class the checklist names, deleted from the suite (Ruling 30's shape)."""
    s.control(_th(s, "TheChecklistNamedTestsExist"))
    _edit(s.study / "test_harness.py", "class TwoMinuteRead(unittest.TestCase):\n",
          "class TwoMinuteReadDeleted(unittest.TestCase):\n")
    code, out = s.run_out(_th(s, "TheChecklistNamedTestsExist"))
    return (Sandbox.expect(code, out, "TwoMinuteRead: does not load by name"),
            "test_harness.py TheChecklistNamedTestsExist")


def m_done_line_mutation_unregistered(s: Sandbox) -> tuple[int, str]:
    """Done-line 12: one mapped mutation dropped from the battery's registry."""
    s.control(_th(s, "EveryDoneLineMutationIsRegistered"))
    _edit(s.study / "mutations.py", '    ("a fourth graded take", m_fourth_graded_take, True),\n', "")
    code, out = s.run_out(_th(s, "EveryDoneLineMutationIsRegistered"))
    return (Sandbox.expect(code, out, "m_fourth_graded_take: no battery entry"),
            "test_harness.py EveryDoneLineMutationIsRegistered")


def m_not_applicable_predicate_stale(s: Sandbox) -> tuple[int, str]:
    """Lesson 6: a predicate forced to return its sentence whether or not its condition still holds."""
    s.control(_th(s, "EveryNotApplicableIsEvaluated"))
    # anchored on the predicate's own def line: two predicates now open with the same two lines (CP8)
    _edit(s.study / "mutations.py",
          "def _na_no_results_file(s: Sandbox) -> str | None:\n    if _has_results(s):\n        return None\n",
          "def _na_no_results_file(s: Sandbox) -> str | None:\n    if False:\n        return None\n")
    code, out = s.run_out(_th(s, "EveryNotApplicableIsEvaluated"))
    return (Sandbox.expect(code, out, "still returns its reason with the condition gone"),
            "test_harness.py EveryNotApplicableIsEvaluated")


def m_topic_class_name_collision_admitted(s: Sandbox) -> tuple[int, str]:
    """The tests_*.py loader letting a topic module's class replace one already defined under its name."""
    s.control(_th(s, "TheTopicTestModulesAreLoaded"))
    _edit(s.study / "test_harness.py", "            if hasattr(this, name):\n", "            if False:\n")
    return s.run(_th(s, "TheTopicTestModulesAreLoaded")), "test_harness.py TheTopicTestModulesAreLoaded"


def m_seed_review_committed_twice_admitted(s: Sandbox) -> tuple[int, str]:
    """Review 14, F5, at its call site: a pre-freeze report committed more than once seeding the take order.

    Round 1 listed this as not applicable, because the guard read this repository's own history. Since CP1 the
    test builds that history itself, and the predicate written for the entry at CP2 returned None: it applies.
    """
    s.control(_th(s, "TheSeedReviewIsCommittedOnce"))
    _edit(s.study / "freeze.py", "    if len(hist.split()) != 1:\n", "    if False:\n")
    return s.run(_th(s, "TheSeedReviewIsCommittedOnce")), "test_harness.py TheSeedReviewIsCommittedOnce"


def m_case_file_label_flipped(s: Sandbox) -> tuple[int, str]:
    """Done-line 12, "an edited case file": one hand label flipped in a committed case suite.

    Two guards must see it, and both are required red: the suite check (CaseSuites, which re-grades every case
    against its walk message) and the pin re-hash (check_results.py over the frozen file). Before the freeze no
    suite carries a sha256, so the frozen file here is the draft with this suite pinned exactly as freeze.py
    writes it: `tasks[].grader_cases.sha256`, the sha256 of the suite's bytes.
    """
    task = "number-fidelity"
    suite = s.study / "cases" / f"{task}.json"
    frozen = json.loads(_prereg(s).read_text())
    spec = next(t for t in frozen["tasks"] if t["id"] == task)["grader_cases"]
    spec["sha256"] = hashlib.sha256(suite.read_bytes()).hexdigest()
    (s.study / "prereg.json").write_text(json.dumps(frozen, indent=2, ensure_ascii=False) + "\n")
    pins = [str(s.study / "check_results.py")]
    s.control(_th(s, "CaseSuites"))
    s.control(pins)

    d = json.loads(suite.read_text())
    g = d["cases"][0]["graded"]["positive"]
    g["label"] = "corrected" if g["label"] != "corrected" else "agreed"
    suite.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")

    suite_code, suite_out = s.run_out(_th(s, "CaseSuites"))
    Sandbox.expect(suite_code, suite_out, "where the suite recorded")
    pin_code, pin_out = s.run_out(pins)
    Sandbox.expect(pin_code, pin_out, "does not match its pinned sha256")
    both = 1 if (suite_code != 0 and pin_code != 0) else 0
    return both, f"CaseSuites (exit {suite_code}) and check_results.py pin re-hash (exit {pin_code}), both required"


def m_rehearsal_counted_as_a_graded_take(s: Sandbox) -> tuple[int, str]:
    """Done-line 12, "a rehearsal counted as a take": run.py's refusal of a non-graded attempt removed at its call
    site, so a rehearsal filed where graded takes are read is graded (the guard drives a graded-take fixture)."""
    s.control(_th(s, "ARehearsalIsNeverGradedAsATake"))
    _edit(s.study / "run.py", '        if attempt != "graded" or outcome.startswith(("PAUSE", "REHEARSAL")):\n',
          "        if False:\n")
    return s.run(_th(s, "ARehearsalIsNeverGradedAsATake")), "test_harness.py ARehearsalIsNeverGradedAsATake"


MUTATIONS = [
    ("an unlisted HEAD reader", m_unlisted_head_reader, False),
    ("a checklist-named test class deleted", m_checklist_named_class_deleted, False),
    ("a done-line 12 mutation dropped from the registry", m_done_line_mutation_unregistered, False),
    ("a not-applicable predicate returning its stale sentence", m_not_applicable_predicate_stale, False),
    ("a topic test class replacing one of the same name", m_topic_class_name_collision_admitted, False),
    ("a seed review report committed more than once", m_seed_review_committed_twice_admitted, False),
    ("a flipped label in a committed case suite", m_case_file_label_flipped, False),
    ("a rehearsal counted as a graded take", m_rehearsal_counted_as_a_graded_take, False),
]
