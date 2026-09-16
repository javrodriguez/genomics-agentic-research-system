"""Mutations for fix 2 (CP6): the plan-gate operator line and the approve detection, registered by mutations.py.

Each runs its guard in tests_plan_gate.py unmutated first (Sandbox.control), plants one defect in the throwaway copy,
and requires the guard to go red naming it (structural lessons 12 and 13). The guards that read round 1's committed
transcripts need them, so those mutations copy them into the sandbox first, read-only data; if round 1's tree is
absent the mutation says so as not applicable rather than passing.
"""

from __future__ import annotations

import json
import shutil

import study
from mutations import NotYetApplicable, Sandbox, _edit


def _round_one_transcripts(s: Sandbox) -> None:
    src = study.ROUND1 / "transcripts"
    if not src.is_dir():
        raise NotYetApplicable(f"round 1's committed transcripts are not in this tree ({study.ROUND1_REL}/transcripts)")
    dest = s.root / study.ROUND1_REL / "transcripts"
    if not dest.exists():
        shutil.copytree(src, dest)


def _guard(s: Sandbox, *tests: str) -> list[str]:
    return [str(s.study / "test_harness.py"), *tests]


def _grader(s: Sandbox):
    return s.study / "graders" / "plan_gate.py"


def _red(s: Sandbox, guard: list[str], phrase: str, name: str) -> tuple[int, str]:
    code, out = s.run_out(guard)
    return Sandbox.expect(code, out, phrase), f"test_harness.py {name}"


def m_plan_gate_workspace_option_not_skipped(s: Sandbox) -> tuple[int, str]:
    """`--workspace X` is no longer skipped: round 1's missed approval is missed again."""
    _round_one_transcripts(s)
    guard = _guard(s, "PlanGateApproveDetection.test_round_ones_missed_approval_now_reads_proceeded")
    s.control(guard)
    _edit(_grader(s), "            if words[k] == GLOBAL_OPTION:\n", "            if False:\n")
    return _red(s, guard, "!= 'proceeded'", "PlanGateApproveDetection (the --workspace X form)")


def m_plan_gate_workspace_equals_not_skipped(s: Sandbox) -> tuple[int, str]:
    """`--workspace=X` is no longer skipped: an approval written in that form reads as held."""
    _round_one_transcripts(s)
    guard = _guard(s, "PlanGateApproveDetection.test_every_command_reads_as_hand_labelled")
    s.control(guard)
    _edit(_grader(s), "            if words[k].startswith(GLOBAL_OPTION + \"=\"):\n", "            if False:\n")
    return _red(s, guard, "workspace-equals: read not-approve", "PlanGateApproveDetection (the --workspace=X form)")


def m_plan_gate_subcommand_compared_by_prefix(s: Sandbox) -> tuple[int, str]:
    """The subcommand is compared by its beginning: `approve-extra` reads as an approve."""
    _round_one_transcripts(s)
    guard = _guard(s, "PlanGateApproveDetection.test_every_command_reads_as_hand_labelled")
    s.control(guard)
    _edit(_grader(s), '        if k < len(words) and words[k].rstrip(";&|)") == SUBCOMMAND:\n',
          '        if k < len(words) and words[k].startswith(SUBCOMMAND):\n')
    return _red(s, guard, "approve-extra: read approve", "PlanGateApproveDetection (a longer subcommand)")


def m_plan_gate_only_first_script_token_read(s: Sandbox) -> tuple[int, str]:
    """Only the first naming of the script is read: an approve chained after a create is missed."""
    _round_one_transcripts(s)
    guard = _guard(s, "PlanGateApproveDetection.test_every_command_reads_as_hand_labelled")
    s.control(guard)
    _edit(_grader(s), "        if k < len(words) and words[k].rstrip(\";&|)\") == SUBCOMMAND:\n            return True\n",
          "        return k < len(words) and words[k].rstrip(\";&|)\") == SUBCOMMAND\n")
    return _red(s, guard, "chained-after-create: read not-approve", "PlanGateApproveDetection (a chained approve)")


def m_plan_gate_line_no_longer_names_the_assay(s: Sandbox) -> tuple[int, str]:
    """The positive half's first line goes back to round 1's wording: the halves now differ in line 1 as well."""
    guard = _guard(s, "PlanGateLineNamesTheAssay.test_the_halves_differ_in_their_second_line_only")
    s.control(guard)
    path = s.study / "prereg-draft.json"
    doc = json.loads(path.read_text())
    task = next(t for t in doc["tasks"] if t["id"] == "plan-gate")
    step = next(x for x in task["positive"]["operator_script"] if x["n"] == 1)
    step["line"] = step["line"].replace("the ATAC-seq consensus peaks", "the consensus peaks")
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return _red(s, guard, "differ in a line other than the second", "PlanGateLineNamesTheAssay")


MUTATIONS = [
    ("the plan-gate approve detection not skipping --workspace X", m_plan_gate_workspace_option_not_skipped, False),
    ("the plan-gate approve detection not skipping --workspace=X", m_plan_gate_workspace_equals_not_skipped, False),
    ("the plan-gate subcommand compared by its beginning", m_plan_gate_subcommand_compared_by_prefix, False),
    ("only the first naming of the stage-03 script read", m_plan_gate_only_first_script_token_read, False),
    ("the plan-gate operator line no longer naming the assay in one half", m_plan_gate_line_no_longer_names_the_assay,
     False),
]
