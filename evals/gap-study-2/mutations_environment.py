#!/usr/bin/env python3
"""The call-site mutations for the environment record and the stripped child environment (CP3, fix 4), registered
by mutations.py.

Each breaks the driver or the draft where it is read, in a throwaway copy, watches its guard green first, and
requires it to go red naming what was planted (structural lessons 12 and 13). The checker's own mutation for a
missing record (m_environment_record_missing) lives beside the checker's tests, not here.
"""

from __future__ import annotations

import json

from mutations import Sandbox, _edit, _prereg

CLS = "TheEnvironmentRecordIsWritten"


def _tests(s: Sandbox, *methods: str) -> list[str]:
    return [str(s.study / "test_harness.py"), *[f"{CLS}.{m}" for m in methods]]


def m_billing_route_left_out_of_its_list(s: Sandbox) -> tuple[int, str]:
    """A billing route dropped from the driver's list: set, it would no longer stop the driver or be recorded."""
    guard = _tests(s, "test_a_set_billing_route_stops_the_driver_before_any_session",
                   "test_the_draft_and_the_driver_carry_one_vocabulary")
    s.control(guard)
    _edit(s.study / "drive.py", '"ANTHROPIC_BASE_URL", "CLAUDE_CODE_API_BASE_URL")', '"ANTHROPIC_BASE_URL")')
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, "CLAUDE_CODE_API_BASE_URL"), f"test_harness.py {CLS} (billing route, vocabulary)"


def m_recorded_env_not_the_one_passed(s: Sandbox) -> tuple[int, str]:
    """one_turn back on os.environ: the record describes child_env() and the session is given something else."""
    guard = _tests(s, "test_stripped_names_leave_every_turns_environment_and_are_named")
    s.control(guard)
    _edit(s.study / "drive.py", "                              env=child_env())\n",
          "                              env={**os.environ, **ISOLATION_ENV})\n")
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, "a turn was passed stripped name(s)"), f"test_harness.py {CLS} (turn environment)"


def m_unreported_source_read_as_none(s: Sandbox) -> tuple[int, str]:
    """A turn whose init record carries no source recorded as the word "none", which reads as a value given."""
    guard = _tests(s, "test_an_unreported_source_is_null_never_the_word_none")
    s.control(guard)
    _edit(s.study / "drive.py", "            return src if isinstance(src, str) else None\n",
          '            return src if isinstance(src, str) else "none"\n')
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, "'none'"), f"test_harness.py {CLS} (unreported source)"


def m_stripped_name_left_in_child_env(s: Sandbox) -> tuple[int, str]:
    """One of the twelve inherited session names kept in the child environment: the effort level reaches the take."""
    guard = _tests(s, "test_stripped_names_leave_every_turns_environment_and_are_named")
    s.control(guard)
    _edit(s.study / "drive.py", "if k not in STRIPPED_ENV} | ISOLATION_ENV",
          'if k not in STRIPPED_ENV or k == "CLAUDE_EFFORT"} | ISOLATION_ENV')
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, "a turn was passed stripped name(s)"), f"test_harness.py {CLS} (stripped name)"


def m_billing_variable_added_to_stripped_env(s: Sandbox) -> tuple[int, str]:
    """A billing route written into the draft's stripped_env: stripped, it would be hidden from the money line."""
    guard = _tests(s, "test_no_stripped_name_may_hide_a_key_a_route_or_a_login")
    s.control(guard)
    path = _prereg(s)
    d = json.loads(path.read_text())
    d["driver_constants"]["stripped_env"].append("ANTHROPIC_BASE_URL")
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, "ANTHROPIC_BASE_URL"), f"test_harness.py {CLS} (never stripped)"


MUTATIONS = [
    ("a billing route dropped from its list", m_billing_route_left_out_of_its_list, True),
    ("the recorded environment is not the one passed", m_recorded_env_not_the_one_passed, True),
    ("an unreported credential source read as none", m_unreported_source_read_as_none, True),
    ("a stripped name left in the child environment", m_stripped_name_left_in_child_env, True),
    ("a billing variable added to stripped_env", m_billing_variable_added_to_stripped_env, False),
]
