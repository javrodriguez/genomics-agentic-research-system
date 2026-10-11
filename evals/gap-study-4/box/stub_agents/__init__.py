"""Round 4's stub agents (CP6): no-model agents that stand in for the harness and drive a take through the adapter seam.

    runtime.py   FakeRuntime: a take's run tree, clock, watcher log, snapshots and ledger, all in memory
    agents.py    the four stubs, each a `ScriptedAdapter` (agent_adapter.py) that also drives a FakeRuntime: the
                 oracle, the act-only stub, the hold-only stub and the background writer (their names: agents.STUBS)
    take.py      one stub take end to end (start_take, every operator line, end_take), graded by the task's own v4
                 grader exactly as probes4.py grades a constructed triple; `--check` runs every stub on every cell

What each stub promises (the plan's CP6 block and its sidecar GOTCHA):
    oracle             the half's right move on every half: it grades right on both halves.
    act-only stub      the act half's move on both halves: right on the act half, wrong on the hold half.
    hold-only stub     the hold half's move on both halves: right on the hold half, wrong on the act half.
    background-writer  the oracle's move, with its writes made by a process that outlives its turn: they land after
                       the turn's end, are attributed to the turn that launched it (marked late), the runtime waits
                       for it before the turn's closing snapshot, and one that outlives the quiescence cap is killed.

These run with fakes only: no model, no container, no network, no real box. The real-box run of the same stubs waits
for the box itself (the CP6 walks).

No model, no network, standard library only.
"""
