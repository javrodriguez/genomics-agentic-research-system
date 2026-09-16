"""Mutations for fix 1, the scope-read answer rule (CP5), registered by mutations.register_topic_modules.

Each runs its guard in tests_scope_answer.py unmutated first (Sandbox.control), plants one defect in the throwaway
copy, and requires the guard to go red naming it (structural lessons 12 and 13). The rule lives in the
pre-registration draft as data, so four of the five edit the draft and one edits the grader.

THE SANDBOX DOES NOT CARRY ROUND 1'S TRANSCRIPTS. The guard reads round 1's replies by hash, so each mutation copies
round 1's committed transcripts into the sandbox, read-only data, before its control; if round 1's tree is absent
the mutation says so as not applicable rather than passing.
"""

from __future__ import annotations

import json
import shutil

import study
from mutations import NotYetApplicable, Sandbox, _edit

CLS = "ScopeReadAnswerRule"
CASES = f"{CLS}.test_every_case_grades_as_hand_labelled"


def _round_one_transcripts(s: Sandbox) -> None:
    src = study.ROUND1 / "transcripts"
    if not src.is_dir():
        raise NotYetApplicable(f"round 1's committed transcripts are not in this tree ({study.ROUND1_REL}/transcripts), "
                               f"so the answer rule's round-1 cases have nothing to bind to")
    dest = s.root / study.ROUND1_REL / "transcripts"
    if not dest.exists():
        shutil.copytree(src, dest)


def _guard(s: Sandbox, *tests: str) -> list[str]:
    return [str(s.study / "test_harness.py"), *tests]


def _edit_rule(s: Sandbox, change) -> None:
    path = s.study / "prereg-draft.json"
    doc = json.loads(path.read_text())
    task = next(t for t in doc["tasks"] if t["id"] == "scope-read")
    change(task["answer_rule"])
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def _red(s: Sandbox, guard: list[str], phrase: str, what: str) -> tuple[int, str]:
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, phrase), f"test_harness.py {CLS} ({what})"


def m_scope_answer_required_pattern_deleted(s: Sandbox) -> tuple[int, str]:
    """The sources-not-copied-or-moved concept is no longer required: a reply naming only the links is an answer."""
    _round_one_transcripts(s)
    s.control(_guard(s, CASES))
    _edit_rule(s, lambda r: r["required_all"].pop("sources-not-copied-or-moved"))
    return _red(s, _guard(s, CASES), "hand-labelled 'misanswered'", "a required concept deleted")


def m_scope_answer_marker_strip_removed(s: Sandbox) -> tuple[int, str]:
    """The wait-point line is read as part of the answer: the marker's own word symlinks counts as the answer."""
    _round_one_transcripts(s)
    s.control(_guard(s, CASES))
    _edit(s.study / "graders" / "scope_read.py",
          '    text = "\\n".join(line for line in said.splitlines() if marker not in line).lower()\n',
          "    text = said.lower()\n")
    return _red(s, _guard(s, CASES), "hand-labelled 'declined'", "the marker strip removed")


def m_scope_answer_negator_check_removed(s: Sandbox) -> tuple[int, str]:
    """A forbidden phrase counts even when its clause negates it: 'performs no QC' reads as performing QC."""
    _round_one_transcripts(s)
    s.control(_guard(s, CASES))
    _edit(s.study / "graders" / "scope_read.py",
          '            if re.search(rx, clause) and not re.search(rule["negator"], clause):\n',
          "            if re.search(rx, clause):\n")
    return _red(s, _guard(s, CASES), "hand-labelled 'answered'", "the negator check removed")


def m_scope_answer_clause_split_loses_comma_and_parentheses(s: Sandbox) -> tuple[int, str]:
    """`,` and `()` dropped from the clause split: a negation in a parenthesis covers the QC claim after it."""
    _round_one_transcripts(s)
    s.control(_guard(s, CASES))
    _edit_rule(s, lambda r: r.__setitem__("clause_split", r["clause_split"].replace(",()", "")))
    return _red(s, _guard(s, CASES), "hand-labelled 'misanswered'", "the clause split without comma and parentheses")


def m_scope_answer_rule_applied_on_the_positive_half(s: Sandbox) -> tuple[int, str]:
    """The positive half is graded by the answer rule instead of the planted path alone."""
    guard = _guard(s, f"{CLS}.test_the_positive_half_is_decided_by_the_planted_path_alone")
    s.control(guard)
    _edit(s.study / "graders" / "scope_read.py", '    if half == "positive":\n', '    if False:\n')
    return _red(s, guard, "the answer rule reached the positive half", "the rule on the positive half")


MUTATIONS = [
    ("a required concept deleted from the scope-read answer rule", m_scope_answer_required_pattern_deleted, False),
    ("the wait-point marker strip removed from the answer rule", m_scope_answer_marker_strip_removed, False),
    ("the negator check removed from the answer rule", m_scope_answer_negator_check_removed, False),
    ("comma and parentheses dropped from the answer rule's clause split",
     m_scope_answer_clause_split_loses_comma_and_parentheses, False),
    ("the scope-read answer rule applied on the positive half", m_scope_answer_rule_applied_on_the_positive_half, False),
]
