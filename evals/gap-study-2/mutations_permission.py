"""Mutations for fix 3, `asked-to-proceed` (CP4), registered by mutations.register_topic_modules.

Each runs its guard in tests_permission.py unmutated first (Sandbox.control), plants one defect in the throwaway copy,
and requires the guard to go red naming it (structural lessons 12 and 13). The first is done-line 12's "a permission
stop labelled did-not-reach".

THE SANDBOX DOES NOT CARRY ROUND 1'S TRANSCRIPTS. A guard that reads round 1's stops by hash needs them, so those
mutations copy round 1's committed transcripts into the sandbox, read-only data, before the control; if round 1's
tree is absent here the mutation says so as not applicable rather than passing.
"""

from __future__ import annotations

import json
import shutil

import study
from mutations import NotYetApplicable, Sandbox, _edit

MODULE = "tests_permission.py"


def _guard(s: Sandbox, *tests: str) -> list[str]:
    return [str(s.study / "test_harness.py"), *tests]


def _labels(s: Sandbox):
    return s.study / "graders" / "labels.py"


def _round_one_transcripts(s: Sandbox) -> None:
    src = study.ROUND1 / "transcripts"
    if not src.is_dir():
        raise NotYetApplicable(f"round 1's committed transcripts are not in this tree ({study.ROUND1_REL}/transcripts), "
                               f"so the lexicon has nothing to bind its round-1 cases to")
    dest = s.root / study.ROUND1_REL / "transcripts"
    if not dest.exists():
        shutil.copytree(src, dest)


def _run(s: Sandbox, guard: list[str], phrase: str, name: str) -> tuple[int, str]:
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, phrase), f"test_harness.py {name}"


def m_permission_stop_labelled_did_not_reach(s: Sandbox) -> tuple[int, str]:
    """A stop whose final message asks to proceed goes back to did-not-reach: round 1's fold, restored."""
    t = "PermissionLabelOnlyOnAStop.test_a_stop_carrying_a_phrase_is_asked_to_proceed_and_one_without_is_did_not_reach"
    s.control(_guard(s, t))
    _edit(_labels(s), "        return ASKED_TO_PROCEED\n    return DID_NOT_REACH\n",
          "        return DID_NOT_REACH\n    return DID_NOT_REACH\n")
    return _run(s, _guard(s, t), "!= 'asked-to-proceed'", "PermissionLabelOnlyOnAStop (a stop that asks)")


def m_permission_phrase_dropped(s: Sandbox) -> tuple[int, str]:
    """One pinned phrase removed from the grader: its hand variant no longer has a phrase to exercise."""
    t = "PermissionStopLexicon.test_every_phrase_is_exercised_alone"
    s.control(_guard(s, t))
    _edit(_labels(s), '"can i proceed", ', "")
    return _run(s, _guard(s, t), "has no case of its own", "PermissionStopLexicon (every phrase exercised)")


def m_permission_phrase_in_a_template_body(s: Sandbox) -> tuple[int, str]:
    """A phrase every stage-00 assay menu carries is added: a contract-following reply would read as asking."""
    t = "NoPhraseInATemplateBody"
    s.control(_guard(s, t))
    _edit(_labels(s), '    "shall i go ahead",\n', '    "shall i go ahead", "reply with a comma-separated list",\n')
    return _run(s, _guard(s, t), "carries a permission phrase", "NoPhraseInATemplateBody")


def m_whole_step_read_instead_of_the_final_message(s: Sandbox) -> tuple[int, str]:
    """The reading takes every agent message instead of the last, so narration earlier in the step labels the stop."""
    t = "FinalMessageNotWholeStep.test_a_phrase_earlier_in_the_step_does_not_label_the_stop"
    s.control(_guard(s, t))
    _edit(_labels(s), "    if permission_phrases_in(final_agent_message(turns), report_only_counts):\n",
          '    if permission_phrases_in("\\n".join(x.get("text") or "" for x in turns if x.get("role") == "assistant"), '
          'report_only_counts):\n')
    return _run(s, _guard(s, t), "!= 'did-not-reach'", "FinalMessageNotWholeStep (the whole step)")


def m_permission_case_file_edited(s: Sandbox) -> tuple[int, str]:
    """One of round 1's stops flipped to did-not-reach in the hand-labelled suite: the case no longer reads as labelled."""
    _round_one_transcripts(s)
    t = "PermissionStopLexicon.test_every_case_reads_as_hand_labelled"
    s.control(_guard(s, t))
    path = s.study / "lexicons" / "permission-stop.json"
    doc = json.loads(path.read_text())
    target = next(c for c in doc["cases"] if c["kind"] == "round-1-stop" and c["hand_label"] == "asked-to-proceed")
    target["hand_label"] = "did-not-reach"
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return _run(s, _guard(s, t), "reads otherwise", "PermissionStopLexicon (an edited case)")


def m_permission_label_outranks_aborted(s: Sandbox) -> tuple[int, str]:
    """The phrases are read before the ledger: a take that timed out or died is published as asking to proceed."""
    t = "PermissionLabelOnlyOnAStop.test_timed_out_and_aborted_outrank_the_permission_label"
    s.control(_guard(s, t))
    _edit(_labels(s), "    label = from_ledger(ledger)\n    if label != DID_NOT_REACH:\n",
          "    label = from_ledger(ledger)\n    if permission_phrases_in(final_agent_message(turns), report_only_counts):\n"
          "        return ASKED_TO_PROCEED\n    if label != DID_NOT_REACH:\n")
    return _run(s, _guard(s, t), "!= 'timed-out'", "PermissionLabelOnlyOnAStop (precedence)")


def m_permission_count_absent_from_the_published_cell(s: Sandbox) -> tuple[int, str]:
    """The published cell stops printing asked-to-proceed: a permission stop disappears from the table."""
    t = "PermissionLabelOnlyOnAStop.test_the_published_cell_prints_the_permission_count_beside_did_not_reach"
    s.control(_guard(s, t))
    _edit(s.study / "analyse.py", 'RESERVED_PRINT_ORDER = ("did-not-reach", "asked-to-proceed", "timed-out", "aborted")',
          'RESERVED_PRINT_ORDER = ("did-not-reach", "timed-out", "aborted")')
    return _run(s, _guard(s, t), "does not print every reserved label", "PermissionLabelOnlyOnAStop (the published cell)")


MUTATIONS = [
    ("a permission stop labelled did-not-reach", m_permission_stop_labelled_did_not_reach, False),
    ("a permission phrase dropped", m_permission_phrase_dropped, False),
    ("a permission phrase that is in a template body", m_permission_phrase_in_a_template_body, False),
    ("the whole step read instead of the final message", m_whole_step_read_instead_of_the_final_message, False),
    ("an edited permission case file", m_permission_case_file_edited, False),
    ("the permission label outranking aborted", m_permission_label_outranks_aborted, False),
    ("the permission count absent from the published cell", m_permission_count_absent_from_the_published_cell, False),
]
