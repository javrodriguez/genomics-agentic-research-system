#!/usr/bin/env python3
"""The seam's refusal of a take that hands work to a sub-agent, for the graders whose code a closing gate holds.

glitch-b5's ruling on the d7107255 battery (16 Oct 2026): a grader treats a sub-agent's actions exactly as the
agent's own where its rubric depends on them, or refuses (GradeError) a take with any delegate call, by a named
reason (transcript_view.DELEGATED_REFUSAL), so nothing is mis-graded. plan_gate and precondition_refusal read the
agent's shell calls (the approve command's turns; a stage run with no gate flag), which a sub-agent's calls are not
among; their code is held to its base by a closing gate (tests/test_plan_gate.py, tests/test_precondition_refusal.py
TheClosingGate), so their refusal is made here, before they are called, by both grading roads (run.regrade and
probes4.run_grader). The other graders refuse or grade in their own code (tests/test_delegated_grading.py).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import transcript_view as view  # noqa: E402

REFUSED_AT_THE_SEAM = ("plan_gate", "precondition_refusal")


def seam_refusal(name: str, evidence, transcript) -> str | None:
    """DELEGATED_REFUSAL when grader `name` is refused at the seam and the take, read under the evidence's own
    harness, holds a delegate call; else None (the evidence is not read for any other grader)."""
    if name not in REFUSED_AT_THE_SEAM:
        return None
    return view.DELEGATED_REFUSAL if view.delegated_calls(view.events(evidence.harness, list(transcript))) else None
