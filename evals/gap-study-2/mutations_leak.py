"""Mutations for the read-outside-the-checkout control (CP3), registered by mutations.register_topic_modules.

Each runs TheCheckoutIsTheOnlyReadableTree unmutated first (Sandbox.control), breaks the control in the
throwaway copy, and requires the class to go red naming the read it let through (structural lessons 12 and 13).
"""

from __future__ import annotations

from mutations import Sandbox, _edit, _th

GUARD = "TheCheckoutIsTheOnlyReadableTree"


def m_outside_checkout_read_not_called(s: Sandbox) -> tuple[int, str]:
    """Lesson 12: the control intact and never called by the checker."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py", "    outside_reads = outside_checkout_reads(path)\n", "    outside_reads = []\n")
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "the sibling read went unrefused through the command line"),
            f"test_harness.py {GUARD}")


def m_sibling_and_parent_pattern_dropped(s: Sandbox) -> tuple[int, str]:
    """The folder beside the checkout and the `<repository>--<task>` naming both dropped: the siblings go unseen."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py",
          '            found.append(("<the folder holding the checkout and its siblings>", parent))\n',
          "            pass\n")
    _edit(s.study / "check_take.py", "                m = sibling.search(s)\n", "                m = None\n")
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "a sibling worktree's case-shaped file went unrefused"),
            f"test_harness.py {GUARD}")


def m_home_folder_whitelisted_wholesale(s: Sandbox) -> tuple[int, str]:
    """The home folder admitted whole: every build copy under it goes unseen."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py", "    allowed = interpreter_prefixes(home, repo)\n",
          "    allowed = interpreter_prefixes(home, repo) + [home.as_posix()]\n")
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "a build copy under the home folder went unrefused"),
            f"test_harness.py {GUARD}")


def m_home_rule_not_called(s: Sandbox) -> tuple[int, str]:
    """Lesson 12: the home rule intact and never called by the checker."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py", "    outside_reads += outside_home_reads(path)\n", "")
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "a read under the home folder went unrefused through the command line"),
            f"test_harness.py {GUARD}")


def m_interpreter_whitelist_widened_to_homes_parent(s: Sandbox) -> tuple[int, str]:
    """The interpreter's install recorded as the folder above home: home itself is then admitted."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py", "            out.append(prefix)\n", "            out.append(home.parent.as_posix())\n")
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "a build copy under the home folder went unrefused while the interpreter sits under it"),
            f"test_harness.py {GUARD}")


def m_temp_root_whitelisted_wholesale(s: Sandbox) -> tuple[int, str]:
    """The temp folder and /tmp admitted whole: every copy under them goes unseen."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py", "    allowed = sorted(tree_forms)\n", "    allowed = sorted(tree_forms) + list(roots)\n")
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "a copy under the temp folder went unrefused"), f"test_harness.py {GUARD}")


def m_temp_rule_not_called(s: Sandbox) -> tuple[int, str]:
    """Lesson 12: the temp-folder rule intact and never called by the checker."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py", "    outside_reads += outside_temp_reads(path)\n", "")
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "a read under the temp folder went unrefused through the command line"),
            f"test_harness.py {GUARD}")


def m_private_tmp_spelling_not_normalised(s: Sandbox) -> tuple[int, str]:
    """/tmp read without its /private/tmp spelling: the macOS form of the same path goes unseen."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py", '    tmp_forms = {TMP, "/private" + TMP}\n', "    tmp_forms = {TMP}\n")
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "a log under /private/tmp went unrefused"), f"test_harness.py {GUARD}")


def m_harness_slug_binding_dropped(s: Sandbox) -> tuple[int, str]:
    """The harness folder admitted for any project's slug: a sibling project's session folder goes unseen."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py",
          '    own_slug = "(?:" + "|".join(re.escape(x) for x in sorted(slugs)) + ")" if slugs else None\n',
          '    own_slug = "[^/]+" if slugs else None\n')
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "a sibling project's harness folder under this session's id went unrefused"),
            f"test_harness.py {GUARD}")


def m_harness_session_binding_dropped(s: Sandbox) -> tuple[int, str]:
    """The harness folder admitted for any session: another session's files under this take's slug go unseen."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py", "    own_session = re.escape(sid) if sid else None\n",
          '    own_session = "[^/]+" if sid else None\n')
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "the take's own harness folder under another session went unrefused"),
            f"test_harness.py {GUARD}")


def m_temp_variable_substitution_removed(s: Sandbox) -> tuple[int, str]:
    """$TMPDIR read as the OS temp root again: the take's own scratch under ruling C is refused."""
    s.control(_th(s, GUARD))
    _edit(s.study / "check_take.py",
          "    variable_real = f\"{wd.rstrip('/')}/{scratch[0]}\" if wd and scratch else written\n",
          "    variable_real = written\n")
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "a variable spelling of the take's own scratch folder was refused"),
            f"test_harness.py {GUARD}")


MUTATIONS = [
    ("the temp variables not resolved to the run tree's scratch folder", m_temp_variable_substitution_removed, False),
    ("the temp folder and /tmp whitelisted wholesale", m_temp_root_whitelisted_wholesale, False),
    ("the temp-folder rule not called", m_temp_rule_not_called, False),
    ("the /private/tmp spelling not normalised", m_private_tmp_spelling_not_normalised, False),
    ("the slug binding dropped from the harness whitelist", m_harness_slug_binding_dropped, False),
    ("the session-id binding dropped from the harness whitelist", m_harness_session_binding_dropped, False),
    ("the home folder whitelisted wholesale", m_home_folder_whitelisted_wholesale, False),
    ("the home-folder rule not called", m_home_rule_not_called, False),
    ("the interpreter whitelist widened to the home folder's parent", m_interpreter_whitelist_widened_to_homes_parent, False),
    ("the read-outside-the-checkout control not called", m_outside_checkout_read_not_called, False),
    ("the sibling and parent patterns dropped from the checkout control", m_sibling_and_parent_pattern_dropped, False),
]
