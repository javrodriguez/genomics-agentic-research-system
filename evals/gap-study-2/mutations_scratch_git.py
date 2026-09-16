#!/usr/bin/env python3
"""The mutations for scratch_git.py, registered by mutations.py: a throwaway repository that starts background git
maintenance again, and a `git init` that goes around the one road.

Each breaks one thing in a throwaway copy, watches its guard green first, and requires it to go red naming what
was planted (structural lessons 12 and 13).
"""

from __future__ import annotations

from mutations import Sandbox, _edit

CLS = "TheScratchRepositoriesStartNoBackgroundMaintenance"


def _tests(s: Sandbox, *methods: str) -> list[str]:
    return [str(s.study / "test_harness.py"), *[f"{CLS}.{m}" for m in methods]]


def m_scratch_repository_keeps_background_maintenance(s: Sandbox) -> tuple[int, str]:
    """scratch_git.init stops writing the setting: every scratch repository starts git 2.55's repack again."""
    guard = _tests(s, "test_init_writes_the_setting_into_the_repository_it_creates")
    s.control(guard)
    _edit(s.study / "scratch_git.py",
          '    subprocess.run(["git", "-C", str(path), "config", MAINTENANCE_KEY, MAINTENANCE_VALUE],\n'
          '                   check=True, capture_output=True)\n', "")
    code, out = s.run_out(guard)
    return (Sandbox.expect(code, out, "would start background maintenance"),
            f"test_harness.py {CLS} (the setting written by init)")


def m_battery_sandbox_initialised_around_the_road(s: Sandbox) -> tuple[int, str]:
    """The battery's own sandbox goes back to a bare git init, as it was before 16 September 2026."""
    guard = _tests(s, "test_the_battery_sandbox_creates_its_repository_through_the_one_road",
                   "test_no_source_creates_a_repository_around_the_one_road")
    s.control(guard)
    _edit(s.study / "mutations.py", "            scratch_git.init(self.root)\n",
          '            subprocess.run(["git", "init", "-q"], cwd=self.root, capture_output=True)\n')
    code, out = s.run_out(guard)
    return (Sandbox.expect(code, out, "does not go through scratch_git.init"),
            f"test_harness.py {CLS} (the battery sandbox)")


def m_test_repository_initialised_around_the_road(s: Sandbox) -> tuple[int, str]:
    """A test fixture's repository goes back to a bare git init: the scan must see it outside mutations.py too."""
    guard = _tests(s, "test_no_source_creates_a_repository_around_the_one_road")
    s.control(guard)
    _edit(s.study / "tests_tools.py", "        scratch_git.init(outer)\n", '        _git(outer, "init", "-q")\n')
    code, out = s.run_out(guard)
    return (Sandbox.expect(code, out, "tests_tools.py:"),
            f"test_harness.py {CLS} (a test fixture's repository)")


MUTATIONS = [
    ("a scratch repository that starts background git maintenance", m_scratch_repository_keeps_background_maintenance,
     False),
    ("the battery sandbox initialised around scratch_git", m_battery_sandbox_initialised_around_the_road, False),
    ("a test repository initialised around scratch_git", m_test_repository_initialised_around_the_road, False),
]
