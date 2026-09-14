"""Mutations for the environment record's checker (CP3, decision 4), registered by mutations.register_topic_modules.

Each runs TheEnvironmentRecordIsRequired unmutated first (Sandbox.control), plants one defect in the throwaway
copy, and requires the class to go red naming what was planted (structural lessons 12 and 13). Two defects are
in the checker (the check emptied, and its call removed from the graded-take path) and two in the record the
tests read (a hidden key and a value where a name belongs), each re-bound in its ledger so that only the
planted defect can be the reason.
"""

from __future__ import annotations

import hashlib
import json

from mutations import Sandbox, _edit, _th

GUARD = "TheEnvironmentRecordIsRequired"


def _guard(s: Sandbox) -> tuple[int, str]:
    return s.run_out(_th(s, GUARD))


def _plant_in_record(s: Sandbox, edit) -> tuple[int, str]:
    s.control(_th(s, GUARD))
    take = s.study / "test-fixtures" / "environment-check" / "take"
    rec = json.loads((take / "environment.json").read_text())
    edit(rec)
    body = (json.dumps(rec, indent=2) + "\n").encode("utf-8")
    (take / "environment.json").write_bytes(body)
    led = json.loads((take / "driver-ledger.json").read_text())
    led["environment"]["sha256"] = hashlib.sha256(body).hexdigest()
    (take / "driver-ledger.json").write_text(json.dumps(led, indent=2) + "\n")
    return _guard(s)


def m_environment_record_missing(s: Sandbox) -> tuple[int, str]:
    """Done-line 12: a graded take with no environment record is not refused (environment_problems returns [])."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py", "    out: list[str] = []\n\n    def refuse(sentence: str) -> None:\n",
          "    return []\n    out: list[str] = []\n\n    def refuse(sentence: str) -> None:\n")
    code, out = _guard(s)
    return (Sandbox.expect(code, out, "a take with no environment record was not refused"),
            f"test_harness.py {GUARD}")


def m_environment_check_not_called_for_a_graded_take(s: Sandbox) -> tuple[int, str]:
    """Lesson 12: the check intact and never called on the graded-take path."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py",
          "    problems += environment_problems(path, ledger, pre, commits.get(row_index))\n", "")
    code, out = _guard(s)
    return (Sandbox.expect(code, out, "a take with no environment record was not refused"),
            f"test_harness.py {GUARD}")


def m_no_transcript_accepts_any_session_id(s: Sandbox) -> tuple[int, str]:
    """A take graded from its ledger alone, its record's session id bound to nothing."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py", '    if rec["session_id"] != sid:\n',
          '    if transcript.is_file() and rec["session_id"] != sid:\n')
    code, out = _guard(s)
    return (Sandbox.expect(code, out, "a no-transcript take's record naming another session was not refused"),
            f"test_harness.py {GUARD}")


def m_never_stripped_widened_to_any_pattern(s: Sandbox) -> tuple[int, str]:
    """The checker's never-stripped rule widened back to any pattern group, which refuses J4's own twelve."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py", '    return matched_by(name, patterns) == "harness" or name in fixed\n',
          "    return matched_by(name, patterns) is not None or name in fixed\n")
    code, out = _guard(s)
    return (Sandbox.expect(code, out, "a record stripping exactly the twelve names was refused"),
            f"test_harness.py {GUARD}")


def m_api_key_set_edited_to_hide_a_key(s: Sandbox) -> tuple[int, str]:
    """A key recorded set, and the flag the driver stops on left false."""
    def hide(rec):
        rec["api_key_variables"]["ANTHROPIC_API_KEY"] = "set"
        rec["names_present"] = sorted(rec["names_present"] + [{"name": "ANTHROPIC_API_KEY", "matched_by": "harness"}],
                                      key=lambda e: e["name"])
    code, out = _plant_in_record(s, hide)
    return (Sandbox.expect(code, out, "records api_key_set False and its own api_key_variables has name set"),
            f"test_harness.py {GUARD} on a record hiding a set key")


def m_value_written_where_a_name_belongs(s: Sandbox) -> tuple[int, str]:
    code, out = _plant_in_record(s, lambda rec: rec["names_present"].append(
        {"name": "placeholder value 0123", "matched_by": "generic"}))
    return (Sandbox.expect(code, out, "a value written where a name belongs is refused unprinted"),
            f"test_harness.py {GUARD} on a record carrying a value as a name")


MUTATIONS = [
    ("the environment record never required", m_environment_record_missing, False),
    ("the environment check not called for a graded take", m_environment_check_not_called_for_a_graded_take, False),
    ("a no-transcript take accepting any session id", m_no_transcript_accepts_any_session_id, False),
    ("the never-stripped rule widened to any pattern group", m_never_stripped_widened_to_any_pattern, False),
    ("an api_key_set edited to hide a key", m_api_key_set_edited_to_hide_a_key, False),
    ("a value written where a variable name belongs", m_value_written_where_a_name_belongs, False),
]
