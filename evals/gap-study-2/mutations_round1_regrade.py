"""Mutations for the round-1 environment regrade record (CP3), registered by mutations.register_topic_modules.

Each runs TheRoundOneEnvironmentRegradeReDerives unmutated first (Sandbox.control), breaks the regrade in the
throwaway copy, and requires the class to go red naming the planted defect (structural lessons 12 and 13).

THE SANDBOX DOES NOT CARRY WHAT THE GUARD READS, SO EACH MUTATION ADDS IT. Sandbox copies this study whole
(verification/round1-regrade/ included) and round 1's walks, but not round 1's takes.json or transcripts/. Without
them the class skips, a skip is green, and a mutation would come back green over a guard that never ran. So each
mutation copies those two paths of round 1's committed tree into the sandbox, read-only data, before its control.
If round 1's tree is absent here, the mutation says so as not applicable rather than passing.
"""

from __future__ import annotations

import shutil

import study
from mutations import NotYetApplicable, Sandbox, _edit, _th

GUARD = "TheRoundOneEnvironmentRegradeReDerives"


def _round_one_takes(s: Sandbox) -> None:
    takes, transcripts = study.ROUND1 / "takes.json", study.ROUND1 / "transcripts"
    if not takes.is_file() or not transcripts.is_dir():
        raise NotYetApplicable(f"round 1's committed takes are not in this tree ({study.ROUND1_REL}/takes.json and "
                               f"transcripts/), so the regrade has nothing to read")
    dest = s.root / study.ROUND1_REL
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(takes, dest / "takes.json")
    shutil.copytree(transcripts, dest / "transcripts")


def _script(s: Sandbox):
    return s.study / "verification" / "round1-regrade" / "regrade_environment.py"


def m_regrade_check_compares_nothing(s: Sandbox) -> tuple[int, str]:
    """--check reports a match whatever the record says; the planted-edit test must catch it."""
    _round_one_takes(s)
    s.control(_th(s, GUARD))
    _edit(_script(s), "        if committed == text:\n", "        if True:\n")
    code, out = s.run_out(_th(s, GUARD))
    return Sandbox.expect(code, out, "an edited record passed the re-derivation"), f"test_harness.py {GUARD}"


def m_regrade_never_calls_the_checker(s: Sandbox) -> tuple[int, str]:
    """The regrade stops calling check_take.environment_problems and the record is rewritten from it, so --check
    agrees with itself; the 108-refused count must catch it."""
    _round_one_takes(s)
    s.control(_th(s, GUARD))
    _edit(_script(s), "        refusals = check_take.environment_problems(t[\"dir\"], ledger, pre, None)\n",
          "        refusals = []\n")
    code, out = s.run_out([str(_script(s)), "--write"])
    if code != 0:
        raise RuntimeError(f"the mutated regrade could not rewrite its record (exit {code}): {out[-300:]}")
    code, out = s.run_out(_th(s, GUARD))
    return Sandbox.expect(code, out, "'refused_environment_record': 0"), f"test_harness.py {GUARD}"


MUTATIONS = [
    ("the round-1 regrade --check compares nothing", m_regrade_check_compares_nothing, False),
    ("the round-1 regrade never calls the environment checker", m_regrade_never_calls_the_checker, False),
]
