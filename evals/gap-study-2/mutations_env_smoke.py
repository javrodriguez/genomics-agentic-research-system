#!/usr/bin/env python3
"""The call-site mutations for the environment smoke (CP3, J4), registered by mutations.py.

Each breaks smoke_run_tree.py where the smoke picks its stripped list, builds its record or compares two records,
in a throwaway copy, watches its guard green first, and requires it to go red naming what was planted
(structural lessons 12 and 13).
"""

from __future__ import annotations

from mutations import Sandbox, _edit

CLS = "TheEnvSmokeRecordsWhatItStripped"


def _tests(s: Sandbox, *methods: str) -> list[str]:
    return [str(s.study / "test_harness.py"), *[f"{CLS}.{m}" for m in methods]]


def m_strip_none_uses_the_draft_list(s: Sandbox) -> tuple[int, str]:
    """--strip none silently runs with the draft's list: the unstripped record would show nothing inherited."""
    guard = _tests(s, "test_strip_none_leaves_the_twelve_in_the_turns_environment")
    s.control(guard)
    _edit(s.study / "smoke_run_tree.py", 'if strip == "draft" else ()', 'if strip in ("draft", "none") else ()')
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, "--strip none:"), f"test_harness.py {CLS} (strip none)"


def m_smoke_record_not_built_from_child_env(s: Sandbox) -> tuple[int, str]:
    """The smoke's record built from this process's environment rather than child_env(): it names what was never
    passed, and the stripped names vanish from it."""
    guard = _tests(s, "test_the_record_written_is_environment_record_for_that_environment")
    s.control(guard)
    _edit(s.study / "smoke_run_tree.py", "drive.environment_record(drive.child_env(), os.environ,",
          "drive.environment_record(dict(os.environ), os.environ,")
    code, out = s.run_out(guard)
    return (Sandbox.expect(code, out, "is not drive.environment_record's for that environment"),
            f"test_harness.py {CLS} (record from child_env)")


def m_compare_ignores_a_non_stripped_difference(s: Sandbox) -> tuple[int, str]:
    """--compare skipping the name-to-state blocks: an API-key variable's state could differ and still pass."""
    guard = _tests(s, "test_compare_fails_on_any_other_difference")
    s.control(guard)
    _edit(s.study / "smoke_run_tree.py", "        if va == vb:\n            continue\n",
          "        if va == vb or isinstance(va, dict):\n            continue\n")
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, "--compare passed an api key state"), f"test_harness.py {CLS} (compare)"


MUTATIONS = [
    ("--strip none silently uses the draft list", m_strip_none_uses_the_draft_list, False),
    ("the smoke's record is not built from child_env()", m_smoke_record_not_built_from_child_env, False),
    ("--compare ignores a non-stripped difference", m_compare_ignores_a_non_stripped_difference, False),
]
