#!/usr/bin/env python3
"""The call-site mutations for each take's temp folder inside its run tree (Javier's ruling C, 14 Sep 2026),
registered by mutations.py.

Each breaks drive.py where the folder is pointed at, excluded or wired into the turn's environment, in a throwaway
copy, watches its guard green first, and requires it to go red naming what was planted (structural lessons 12
and 13).
"""

from __future__ import annotations

from mutations import Sandbox, _edit

CLS = "TheTakeScratchLandsInItsRunTree"


def _tests(s: Sandbox, *methods: str) -> list[str]:
    return [str(s.study / "test_harness.py"), *[f"{CLS}.{m}" for m in methods]]


def m_temp_folder_not_in_child_env(s: Sandbox) -> tuple[int, str]:
    """child_env() stops adding the run tree's temp folder: every turn's scratch goes back to the machine's temp root."""
    guard = _tests(s, "test_the_turn_environment_points_every_temp_variable_at_the_run_tree")
    s.control(guard)
    _edit(s.study / "drive.py", " | ISOLATION_ENV | run_tree_temp_env(RUN_TREE)", " | ISOLATION_ENV")
    code, out = s.run_out(guard)
    return (Sandbox.expect(code, out, "is not the run tree's temp folder"),
            f"test_harness.py {CLS} (temp folder in the turn's environment)")


def m_temp_folder_left_out_of_the_exclude(s: Sandbox) -> tuple[int, str]:
    """The temp folder no longer git-excluded: a file a tool writes there shows in the status the agent is shown."""
    guard = _tests(s, "test_git_status_stays_clean_with_a_file_in_the_temp_folder")
    s.control(guard)
    _edit(s.study / "drive.py", '            fh.write(f"{RUN_TREE_TMPDIR}/\\n")\n', "")
    code, out = s.run_out(guard)
    return (Sandbox.expect(code, out, "the take's temp folder broke the checkout's git status"),
            f"test_harness.py {CLS} (temp folder excluded)")


def m_temp_folder_is_the_os_temp_root(s: Sandbox) -> tuple[int, str]:
    """TMPDIR pointed at the machine's temp root: the take's scratch lands where the checker refuses reads."""
    guard = _tests(s, "test_child_env_points_the_temp_variables_at_the_run_tree_last")
    s.control(guard)
    _edit(s.study / "drive.py", "    folder = str(tree / RUN_TREE_TMPDIR)\n", "    folder = tempfile.gettempdir()\n")
    code, out = s.run_out(guard)
    return (Sandbox.expect(code, out, "is not the run tree's temp folder"),
            f"test_harness.py {CLS} (temp folder not the OS temp root)")


MUTATIONS = [
    ("child_env() leaves out the run tree's temp folder", m_temp_folder_not_in_child_env, True),
    ("the run tree's temp folder is not git-excluded", m_temp_folder_left_out_of_the_exclude, False),
    ("TMPDIR points at the machine's temp root", m_temp_folder_is_the_os_temp_root, False),
]
