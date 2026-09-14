#!/usr/bin/env python3
"""The call-site mutations for the environment record on the ledger side (CP3, fix 4), registered by mutations.py.

Each breaks one guard where it runs, in a throwaway copy, watches the guard green first, and requires it to go red
naming what was planted (structural lessons 12 and 13).
"""

from __future__ import annotations

from mutations import Sandbox, _edit, _th

CLASS = "TheLedgerCountsEnvironmentRecords"


def _test(s: Sandbox, method: str) -> list[str]:
    return _th(s, f"{CLASS}.{method}")


def m_rehearsal_founded_on_a_deleted_record(s: Sandbox) -> tuple[int, str]:
    """A rehearsal whose ledger names an environment record with none beside it, no longer refused."""
    guard = _test(s, "test_a_rehearsal_founded_on_a_deleted_record_is_refused")
    s.control(guard)
    _edit(s.study / "check_results.py",
          "        if bound is not None and not (isinstance(bound, dict) and bound.get(\"file\") == ENVIRONMENT_RECORD\n",
          "        if False and not (isinstance(bound, dict) and bound.get(\"file\") == ENVIRONMENT_RECORD\n")
    code, out = s.run_out(guard)
    return (Sandbox.expect(code, out, "a rehearsal founded on a deleted record was admitted"),
            f"test_harness.py {CLASS}.test_a_rehearsal_founded_on_a_deleted_record_is_refused")


def m_ledger_count_ignores_a_missing_record(s: Sandbox) -> tuple[int, str]:
    """The --ledger line counting every graded take as carrying a record, through the CLI."""
    guard = _test(s, "test_the_ledger_line_names_the_takes_that_carry_no_record")
    s.control(guard)
    _edit(s.study / "check_results.py",
          '    head = (f"{len(carried)} of {len(graded)} graded takes carry an environment record; "\n',
          '    head = (f"{len(graded)} of {len(graded)} graded takes carry an environment record; "\n')
    code, out = s.run_out(guard)
    return (Sandbox.expect(code, out, "3 of 3 graded takes carry an environment record"),
            f"test_harness.py {CLASS}.test_the_ledger_line_names_the_takes_that_carry_no_record (check_results.py --ledger)")


def m_run_grades_a_take_with_no_record(s: Sandbox) -> tuple[int, str]:
    """run.py's refusal of a graded take without a valid environment record, removed at its call site."""
    guard = _test(s, "test_run_refuses_to_grade_a_take_without_a_record")
    s.control(guard)
    _edit(s.study / "run.py", "        if env_problems:\n", "        if False:\n")
    code, out = s.run_out(guard)
    return (Sandbox.expect(code, out, "SystemExit not raised"),
            f"test_harness.py {CLASS}.test_run_refuses_to_grade_a_take_without_a_record")


def m_record_left_out_of_the_re_run(s: Sandbox) -> tuple[int, str]:
    """The ledger-made re-run run without the take's environment record beside its transcript."""
    guard = _test(s, "test_a_rehearsal_founded_on_a_take_carries_its_record_into_the_re_run")
    s.control(guard)
    _edit(s.study / "check_results.py", "        if env.is_file():\n", "        if False:\n")
    code, out = s.run_out(guard)
    return (Sandbox.expect(code, out, "the re-run did not carry the record"),
            f"test_harness.py {CLASS}.test_a_rehearsal_founded_on_a_take_carries_its_record_into_the_re_run")


MUTATIONS = [
    ("a rehearsal founded on a deleted environment record", m_rehearsal_founded_on_a_deleted_record, False),
    ("the --ledger count ignoring a missing environment record", m_ledger_count_ignores_a_missing_record, False),
    ("run.py grading a take with no environment record", m_run_grades_a_take_with_no_record, False),
    ("the environment record left out of the ledger-made re-run", m_record_left_out_of_the_re_run, False),
]
