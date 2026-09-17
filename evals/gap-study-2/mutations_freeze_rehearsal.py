"""Mutations for CP8, the rehearsed freeze and the review kit, registered by mutations.register_topic_modules.

Each runs its guard unmutated first (Sandbox.control), plants one defect in the throwaway copy, and requires the guard
to go red naming it (structural lessons 12 and 13).
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys

from mutations import NotYetApplicable, Sandbox, _edit


def _guard(s: Sandbox, *tests: str) -> list[str]:
    return [str(s.study / "test_harness.py"), *tests]


def _red(s: Sandbox, guard: list[str], phrase: str, what: str) -> tuple[int, str]:
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, phrase), f"test_harness.py {what}"


def m_freeze_writes_without_a_rehearsal(s: Sandbox) -> tuple[int, str]:
    """freeze.py stops requiring a rehearsal record: the irreversible step runs on a state nothing exercised."""
    guard = _guard(s, "TheFreezeNeedsARehearsal.test_freeze_write_refuses_without_a_rehearsal_in_a_copy")
    s.control(guard)
    _edit(s.study / "freeze.py", "    if args.write and not args.rehearsal:\n",
          "    if False:\n")
    return _red(s, guard, "reached past the rehearsal gate", "TheFreezeNeedsARehearsal (no rehearsal gate)")


def m_rehearsal_record_for_other_bytes_admitted(s: Sandbox) -> tuple[int, str]:
    """A rehearsal of some other draft admits this one: the sha256 on line 1 is no longer compared."""
    guard = _guard(s, "TheFreezeNeedsARehearsal.test_a_record_for_other_bytes_refuses")
    s.control(guard)
    _edit(s.study / "freeze.py", "    matching = [f for f in files if f.read_text().splitlines()[:1] == [draft_sha256]]\n",
          "    matching = files\n")
    return _red(s, guard, "other draft bytes was admitted", "TheFreezeNeedsARehearsal (other bytes admitted)")


def m_freeze_may_edit_a_script_line(s: Sandbox) -> tuple[int, str]:
    """The freeze's allowed-keys list gains the operator script: an edit on the way out is no longer named."""
    guard = _guard(s, "TheFreezeNeedsARehearsal.test_the_commit_body_diff_names_only_freeze_written_keys")
    s.control(guard)
    _edit(s.study / "freeze.py", '    "tasks[].grader", "tasks[].grader_cases", "tasks[].positive.fixture", "tasks[].control.fixture",\n',
          '    "tasks[].grader", "tasks[].grader_cases", "tasks[].positive.fixture", "tasks[].control.fixture",\n'
          '    "tasks[].positive.operator_script",\n')
    return _red(s, guard, "a freeze that edits a script line must be named", "TheFreezeNeedsARehearsal (a script line allowed)")


def m_reviewer_launched_with_a_remote(s: Sandbox) -> tuple[int, str]:
    """launch.py stops refusing a clone with a remote: a reviewer with no prompts could push."""
    guard = _guard(s, "TheReviewerCannotPush.test_a_folder_whose_clone_has_a_remote_is_refused")
    s.control(guard)
    _edit(s.study / "review_kit" / "launch.py", "        if r.returncode != 0 or r.stdout.strip():\n",
          "        if False:\n")
    return _red(s, guard, "has a remote", "TheReviewerCannotPush")


def m_blindness_marker_dropped(s: Sandbox) -> tuple[int, str]:
    """The goal id leaves the blindness markers: a leak of the goal file would go unreported."""
    guard = _guard(s, "TheReviewKitMatchesTheDriver.test_blindness_markers_name_this_round_and_the_operator")
    s.control(guard)
    _edit(s.study / "review_kit" / "blindness.py", '    ("the goal id", "gars-eval-v3"),\n', "")
    return _red(s, guard, "gars-eval-v3", "TheReviewKitMatchesTheDriver (a marker dropped)")


def m_reviewer_inherits_a_stripped_name(s: Sandbox) -> tuple[int, str]:
    """launch.py builds its environment from os.environ instead of the driver's child_env: the reviewer inherits what a take does not."""
    guard = _guard(s, "TheReviewKitMatchesTheDriver.test_launch_flags_and_environment_are_the_drivers")
    s.control(guard)
    _edit(s.study / "review_kit" / "launch.py", "    return {**drive.child_env(), **REVIEWER_ENV}\n",
          "    return {**os.environ, **REVIEWER_ENV}\n")
    return _red(s, guard, "the reviewer inherits", "TheReviewKitMatchesTheDriver (os.environ)")


def _synthetic_review(s: Sandbox) -> str:
    """A stand-in pre-freeze report for the sandbox's draft bytes, committed once; returns that commit's sha."""
    sha = hashlib.sha256((s.study / "prereg-draft.json").read_bytes()).hexdigest()
    # on a frozen tree the sandbox carries the frozen file; removing it puts the copy back into the state the freeze
    # runs from (the precedent is m_frozen_file_edited's note), committed so the tree the freeze reads is clean
    frozen = s.study / "prereg.json"
    if frozen.is_file():
        frozen.unlink()
        s.commit("the frozen file removed, so the freeze can be rehearsed in this copy")
    # a report name no earlier commit used: the review rule refuses a report path committed more than once
    n = 1 + len(list((s.study / "verification").glob("prefreeze-*.md")))
    report = s.study / "verification" / f"prefreeze-{n}.md"
    report.write_text(f"prereg.json sha256: {sha}\n\nSYNTHETIC: written by the mutation battery.\n\n**Ruling: DO FREEZE.**\n")
    return s.commit("verification: a synthetic pre-freeze review, battery")


def m_freeze_pins_a_generated_fixture_by_nothing(s: Sandbox) -> tuple[int, str]:
    """Review 20, F5: at the freeze a generator reports no manifest, so its fixture would be pinned by nothing and
    every take on it refused afterwards. The freeze must refuse rather than write. The guard is freeze.py's own
    refusal, run with --rehearsal in the sandbox's remote-less repository the way freeze_rehearsal.py runs it in a
    clone; the control is that same freeze writing in the unbroken copy. Before CP8 this sat in NOT_APPLICABLE as a
    fixture larger than the change; the rehearsal is that fixture."""
    if shutil.which("claude") is None:
        raise NotYetApplicable("`claude` is not on PATH here, so freeze.py refuses before it reaches the fixture "
                               "pins; the machine that rehearses the freeze has it")
    review = _synthetic_review(s)
    argv = [str(s.study / "freeze.py"), "--review-commit", review, "--rehearsal", "--write"]
    s.control(argv)
    (s.study / "prereg.json").unlink()
    # the generator answers --manifest-only with nothing, committed so the pin reads a committed blob
    _edit(s.study / "fixtures" / "gen_source.py", "    if args.manifest_only:\n        print(json.dumps(man, indent=2))\n",
          "    if args.manifest_only:\n        pass\n")
    s.commit("a generator that reports no manifest")
    code, out = s.run_out(argv)
    if (s.study / "prereg.json").is_file():
        return 0, "freeze.py --rehearsal --write wrote a frozen file whose fixture is pinned by nothing"
    return Sandbox.expect(code, out, "pinned by nothing"), "freeze.py --rehearsal --write (a generator with no manifest)"


def m_freeze_admits_another_study_tree(s: Sandbox) -> tuple[int, str]:
    """freeze.py stops comparing the rehearsed study tree with HEAD's: a code edit after the rehearsal passes the gate."""
    guard = _guard(s, "TheFreezeNeedsARehearsal.test_a_record_for_another_study_tree_refuses")
    s.control(guard)
    _edit(s.study / "freeze.py", "        bound = [f for f in green if recorded_tree(f) == study_tree]\n", "        bound = green\n")
    return _red(s, guard, "another study tree was admitted", "TheFreezeNeedsARehearsal (another tree admitted)")


def m_freeze_seeds_from_a_refusing_review(s: Sandbox) -> tuple[int, str]:
    """freeze.py stops requiring the DO FREEZE line in the seed report: a review that ruled against seeds the order."""
    guard = _guard(s, "TheSeedReviewIsCommittedOnce")
    s.control(guard)
    _edit(s.study / "freeze.py", "    if RULING_LINE not in body:\n", "    if False:\n")
    return _red(s, guard, "ruled against the freeze seeded it", "TheSeedReviewIsCommittedOnce (a refusing review seeds)")


MUTATIONS = [
    ("the freeze written without a rehearsal", m_freeze_writes_without_a_rehearsal, False),
    ("a rehearsal of other draft bytes admitted", m_rehearsal_record_for_other_bytes_admitted, False),
    ("the freeze allowed to edit a script line", m_freeze_may_edit_a_script_line, False),
    ("the reviewer launched from a clone with a remote", m_reviewer_launched_with_a_remote, False),
    ("a blindness marker dropped", m_blindness_marker_dropped, False),
    ("the reviewer inheriting a stripped session name", m_reviewer_inherits_a_stripped_name, False),
    ("a freeze that pins a generated fixture by nothing", m_freeze_pins_a_generated_fixture_by_nothing, True),
    ("the freeze admitting another study tree than the rehearsed one", m_freeze_admits_another_study_tree, False),
    ("the freeze seeded from a review that ruled against it", m_freeze_seeds_from_a_refusing_review, False),
]
