"""Mutations for the CP2 process tools: each guard in tests_tools.py watched green, then broken.

Registered by mutations.register_topic_modules. Each mutation runs its guard class unmutated first
(Sandbox.control), plants one defect in the tool's source inside the throwaway copy, and runs the guard
again. The guard is the tests_tools.py class run as a script, so it does not depend on test_harness.py's
loader; once that lands, `test_harness.py <Class>` runs the same class.
"""

from __future__ import annotations

from mutations import Sandbox, _edit


def _guard(s: Sandbox, cls: str) -> list[str]:
    return [str(s.study / "tests_tools.py"), cls]


def _break(s: Sandbox, cls: str, tool: str, old: str, new: str) -> tuple[int, str]:
    argv = _guard(s, cls)
    s.control(argv)
    _edit(s.study / tool, old, new)
    return s.run(argv), cls


def m_commit_msg_without_the_solidus_check(s: Sandbox) -> tuple[int, str]:
    return _break(s, "CommitMsgRefusesASolidusCount", "commit_msg.py",
                  "        m = SOLIDUS_COUNT.search(line)\n", "        m = None\n")


def m_commit_msg_prefix_whitelist_accepts_anything(s: Sandbox) -> tuple[int, str]:
    return _break(s, "CommitMsgRefusesAnUnlistedPrefix", "commit_msg.py",
                  "    if not SUBJECT_PREFIX.match(subject):\n", "    if False:\n")


def m_commit_msg_language_guard_not_called(s: Sandbox) -> tuple[int, str]:
    return _break(s, "CommitMsgRunsTheLanguageGuard", "commit_msg.py",
                  "    findings = language_findings(text)\n", "    findings = []\n")


def m_ci_conclusion_no_run_read_as_success(s: Sandbox) -> tuple[int, str]:
    return _break(s, "CiConclusionReadsEveryOutcome", "ci_conclusion.py",
                  "return EXIT_NO_RUN, ", "return EXIT_SUCCESS, ")


def m_ci_conclusion_in_progress_read_as_success(s: Sandbox) -> tuple[int, str]:
    return _break(s, "CiConclusionReadsEveryOutcome", "ci_conclusion.py",
                  "return EXIT_PENDING, ", "return EXIT_SUCCESS, ")


def m_ci_conclusion_sha_handed_to_gh_unresolved(s: Sandbox) -> tuple[int, str]:
    cls = ("CiConclusionResolvesTheCommitFirst."
           "test_a_short_sha_reaches_gh_as_its_full_sha_and_reads_as_the_full_sha_does")
    return _break(s, cls, "ci_conclusion.py",
                  "            sha = resolve_commit(args.sha)\n", "            sha = args.sha\n")


def m_clean_clone_missing_expected_skip_admitted(s: Sandbox) -> tuple[int, str]:
    return _break(s, "CleanCloneBatteryChecksItsSkips.test_each_expected_skip_missing_or_repeated_fails_by_name",
                  "clean_clone_battery.sh", '    if [ "$n" != 1 ]; then\n', '    if [ "$n" -gt 1 ]; then\n')


def m_clean_clone_skip_reason_unread(s: Sandbox) -> tuple[int, str]:
    return _break(s, "CleanCloneBatteryChecksItsSkips.test_an_expected_name_skipping_for_another_reason_fails",
                  "clean_clone_battery.sh", '        "$ORIGIN_REASON"?*")"*) echo', "        *) echo")


def m_checklist_name_dropped_from_the_comparison(s: Sandbox) -> tuple[int, str]:
    return _break(s, "CheckChecklistNamesReadsTheDoneLines", "check_checklist_names.py",
                  "    names = done_line_names(section)\n", "    names = done_line_names(section)[:-1]\n")


MUTATIONS = [
    ("commit_msg.py without its solidus-count refusal", m_commit_msg_without_the_solidus_check, False),
    ("commit_msg.py prefix whitelist accepting anything", m_commit_msg_prefix_whitelist_accepts_anything, False),
    ("commit_msg.py never calling the language guard", m_commit_msg_language_guard_not_called, False),
    ("ci_conclusion.py reading no run as success", m_ci_conclusion_no_run_read_as_success, False),
    ("ci_conclusion.py reading a run in progress as success", m_ci_conclusion_in_progress_read_as_success, False),
    ("ci_conclusion.py handing gh the sha unresolved", m_ci_conclusion_sha_handed_to_gh_unresolved, False),
    ("clean_clone_battery.sh admitting an expected skip that is missing", m_clean_clone_missing_expected_skip_admitted,
     False),
    ("clean_clone_battery.sh not reading an expected skip's reason", m_clean_clone_skip_reason_unread, False),
    ("check_checklist_names.py dropping a Done-line name", m_checklist_name_dropped_from_the_comparison, False),
]
