#!/usr/bin/env python3
"""One stub take end to end, graded by the task's own v4 grader exactly as probes4.py grades a constructed triple.

    python3 evals/gap-study-4/box/stub_agents/take.py --check            every stub, every half, every cell
    python3 evals/gap-study-4/box/stub_agents/take.py --check --task T   the same for one task

A take: a FakeRuntime on the half's fixture, a stub built for the half and the cell's operator lines, then
start_take, one turn per line (the first with first=True) and end_take through the adapter contract. The take's
transcript and evidence go to `probes4.run_grader` with the cell's own spec (`variants.render_grader_spec`).

WHAT EACH STUB MUST GRADE (the plan's CP6 block: "They must grade exactly as probes4.py requires for the matching
constructed triple"):
    the oracle, the writer      right on both halves, at probes4's oracle label for the cell
    the act-only stub                right on the act half and wrong on the hold half, at probes4's constant-act label
    the hold-only stub               right on the hold half and wrong on the act half, at probes4's constant-hold label
A take's label must also equal the label probes4 gives the matching case's own triple on the same cell, with the same
human-sample flag and check. A row probes4 routes to the human sample (probes4.ROUTED) is reported as routed and is
still held to probes4's label and check.

`--check` exits 1 on any take that misses, and prints one line per stub with its count. No model, no container, no
network, standard library only. Writes nothing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))
sys.dont_write_bytecode = True

import agent_adapter as aa  # noqa: E402
import probes4  # noqa: E402
import variants as V  # noqa: E402
from box.stub_agents import agents as ag  # noqa: E402
from box.stub_agents import runtime as rt  # noqa: E402

PIN = {"harness": ag.StubAgent.name, "model": ag.STUB_MODEL, "permission_mode": ag.STUB_MODE,
       "version": ag.STUB_VERSION}
# The probes4 case each stub's take is the take of.
MATCHING_CASE = {ag.ORACLE_NAME: probes4.ORACLE, ag.ACT_NAME: probes4.CONST_ACT, ag.HOLD_NAME: probes4.CONST_HOLD,
                 ag.WRITER_NAME: probes4.ORACLE}


class StubTake:
    """What one stub take leaves: the adapter, the runtime, the turn results, the transcript, the evidence."""

    def __init__(self, stub, runtime, results, h, cell):
        self.stub, self.runtime, self.results, self.half, self.cell = stub, runtime, results, h, cell
        self.transcript = runtime.transcript()
        self.evidence = runtime.evidence()

    def records(self) -> dict:
        """The take's harness-side records, folded as routing reads them (agent_adapter.harness_records)."""
        return aa.harness_records(self.results, pin=dict(PIN), box=self.runtime.box_records())

    def grade(self) -> dict:
        spec = V.render_grader_spec(self.half.task, self.half.vdoc, self.half.half, self.cell["wording"],
                                    self.cell["pressure"], probes4.PROJECT)
        return probes4.run_grader(self.half.task, self.half.half, self.cell, spec, self.transcript, self.evidence)


def cells(task_id: str, half: str) -> list:
    task, vdoc = V.load_task(task_id), V.load_variants(task_id)
    return [c for c in V.task_cells(task, vdoc) if c["half"] == half]


def run_stub_take(stub: str, task_id: str, half: str, cell: dict | None = None, *, stub_cls=None,
                  quiescence_cap_s: float = rt.FAKE_QUIESCENCE_CAP_S) -> StubTake:
    """Drive one take of `stub` (a STUBS name) on one cell (the half's first when None) through the adapter."""
    task, vdoc = V.load_task(task_id), V.load_variants(task_id)
    cell = cell if cell is not None else cells(task_id, half)[0]
    h = probes4.Half(task, vdoc, half)
    pr = probes4.PROBES[task_id]
    lines = probes4.operator_lines(task, vdoc, half, cell, h)
    operator = (lambda k: pr.operator(h, k)) if hasattr(pr, "operator") else None
    runtime = rt.FakeRuntime(pr.fixture(h), operator=operator, quiescence_cap_s=quiescence_cap_s)
    agent = (stub_cls or ag.STUBS[stub])(h, lines, runtime)
    agent.start_take({"row_id": f"stub-{stub}-{task_id}-{half}", "slot": 1, "half_cell": f"{task_id}/{half}"})
    results = [agent.turn(line, first=(i == 0), budget_s=ag.BUDGET_S) for i, (_k, line, _m) in enumerate(lines)]
    agent.end_take()
    return StubTake(agent, runtime, results, h, cell)


def expected_correct(stub: str, kind: str) -> bool:
    if stub in (ag.ORACLE_NAME, ag.WRITER_NAME):
        return True
    if stub == ag.ACT_NAME:
        return kind == V.ACT
    if stub == ag.HOLD_NAME:
        return kind == V.HOLD
    raise KeyError(stub)


def probes4_result(stub: str, task_id: str, half: str, cell: dict) -> dict:
    """What probes4 gives the matching case's own constructed triple on this cell."""
    task, vdoc = V.load_task(task_id), V.load_variants(task_id)
    h = probes4.Half(task, vdoc, half)
    pr = probes4.PROBES[task_id]
    mv = {probes4.ORACLE: probes4.oracle_move, probes4.CONST_ACT: probes4.act_move,
          probes4.CONST_HOLD: probes4.hold_move}[MATCHING_CASE[stub]](pr, h)
    return probes4.grade_cell(pr, task, vdoc, half, cell, mv)


def problems_of(stub: str, take: StubTake, want: dict) -> list:
    """Every way one graded take misses: its correctness for the stub, and probes4's label, flag and check."""
    got = take.grade()
    where = f"{stub} {take.half.task['task']}/{take.half.half}/{take.cell['wording']}"
    out = []
    if bool(got["correct"]) != expected_correct(stub, take.half.kind):
        out.append(f"{where}: graded {got['label']} (correct {got['correct']}); the stub must grade "
                   f"{'right' if expected_correct(stub, take.half.kind) else 'wrong'}")
    for k in ("label", "human_sample", "human_check"):
        if got.get(k) != want.get(k):
            out.append(f"{where}: {k} {got.get(k)!r}, and probes4's {MATCHING_CASE[stub]} triple gives {want.get(k)!r}")
    return out


def check(task_ids=None, stubs=None) -> tuple:
    """(takes graded, problems) over every stub, task, half and cell."""
    n, out = 0, []
    for tid in (task_ids or probes4.task_ids()):
        for half in V.HALVES:
            for cell in cells(tid, half):
                for stub in (stubs or ag.STUBS):
                    take = run_stub_take(stub, tid, half, cell)
                    out += problems_of(stub, take, probes4_result(stub, tid, half, cell))
                    n += 1
    return n, out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Stub takes through the adapter, graded by the v4 graders.")
    ap.add_argument("--check", action="store_true", help="exit 1 unless every stub take grades as it must")
    ap.add_argument("--task", action="append", help="limit to this task (repeatable)")
    args = ap.parse_args(argv)
    n, problems = check(args.task)
    for p in problems:
        print(f"PROBLEM {p}")
    print(f"stub_agents: {n} takes graded, {len(problems)} problems")
    return 1 if (args.check and (problems or not n)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
