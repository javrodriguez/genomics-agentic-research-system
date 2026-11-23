#!/usr/bin/env python3
"""The grading roads' seam for a take that hands work to a sub-agent (run.regrade and probes4.run_grader).

glitch-b5's ruling on the d7107255 battery (16 Oct 2026) made a delegated take refuse where a grader's label reads
the agent's tool calls or words. His pre-freeze ruling (16 Oct 2026) replaced the refusal with a presentation: a
refused take leaves its label missing exactly where a model delegates, a bias in the measured run. So the seam hands
plan_gate, precondition_refusal and new_tasks the take as the agent did it (delegated_take.present: each Agent call
replaced by its sub-agent's own records, its text presented as the agent's reasoning, since these graders read the
operator-facing reply), and the graders run unchanged (plan_gate's and precondition_refusal's code is held to its
base by a closing gate). What the adapter cannot present is refused by a named reason (DELEGATED_REFUSAL, then the
adapter's why), never graded on the main thread alone.

The other graders on the roads take the take as it is: scope_read (the access log holds the sub-agent's reads, and a
delegated take goes to its human sample), template_adherence, number_fidelity and confounded_design (each reads the
end state and the agent's own reply). awareness and pause_adherence, on no road yet, take
delegated_take.presented_events (awareness with words "text", pause_adherence with "reasoning").
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import delegated_take  # noqa: E402
import transcript_view as view  # noqa: E402

PRESENTED = {"plan_gate": "reasoning", "precondition_refusal": "reasoning", "new_tasks": "reasoning"}


def seam(name: str, evidence, transcript) -> tuple:
    """(the transcript grader `name` is handed, None) or (None, the refusal). A grader outside PRESENTED, and a take
    with no delegate call, is handed `transcript` itself; the evidence is read only for a presented grader."""
    if name not in PRESENTED:
        return transcript, None
    try:
        return delegated_take.present(transcript, evidence.harness, words=PRESENTED[name]), None
    except delegated_take.NotPresented as e:
        return None, f"{view.DELEGATED_REFUSAL} ({e})"


def sampled(got: dict, transcript) -> dict:
    """W-3b (glitch-b5's pre-freeze ruling, 16 Oct 2026): the grader's result, sent to the human sample (human_sample
    true, the count named in its evidence) when the take's Bash commands ran one of the box's agent CLIs
    (delegated_take.nested_cli_count); unchanged otherwise."""
    n = delegated_take.nested_cli_count(transcript)
    if not n:
        return got
    return dict(got, human_sample=True, evidence=list(got.get("evidence") or []) + [
        f"the take's Bash commands ran an agent CLI {n} time(s) (a nested agent, W-3b): for the human sample"])
