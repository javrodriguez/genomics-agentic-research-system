#!/usr/bin/env python3
"""Lane fold2-ld (Gap Study round 4, pre-freeze review 2's fold, lane L-D; FOLD-PLAN-prefreeze-2.md section 3's
MINORs table, approved by glitch-45 under Javier's delegation, Thu 29 Oct 2026): m8, m10, m13 and m16.

  M10-reach   (m10) result.py prints the outside-reach events per half-cell from every committed outcome: the takes,
              how many carry an outside-reach event, the events.outside_reach total, and the takes whose records give
              no count (named, never counted as none).

Synthetic outcomes in memory. No model, network, container or credential.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
_PATH = list(sys.path)
sys.path.insert(0, str(HERE))

import lint_language as ll  # noqa: E402
import result  # noqa: E402
from graders import labels4  # noqa: E402

sys.path[:] = _PATH

CLAUDE, CODEX = "claude-code", "codex"


def row(slot, attempt, *, arm="A", task="t1", half="trap", model="a1", harness=CLAUDE):
    return {"slot": slot, "attempt": attempt, "arm": arm, "task": task, "half": half, "model": model,
            "agent": {"harness": harness, "version": "v"}, "half_cell": f"{arm}-{task}-{half}-{model}"}


def outcome(slot, attempt, state, reach, events=None):
    """A committed outcome; reach is the routed records' events.outside_reach (None: records with no count)."""
    records = None if reach is Ellipsis else {"events": {"outside_reach": reach}}
    if events is None:
        events = ["outside-reach"] if isinstance(reach, int) and reach > 0 else []
    return {"slot": slot, "attempt": attempt, "state": state, "records": records, "events": events}


# ---- M10: outside-reach events per half-cell (m10) ------------------------------------------------------------------

class M10Reach(unittest.TestCase):
    rows = [row("s1", 1), row("s1", 2), row("s2", 1), row("s3", 1, half="normal"),
            row("s4", 1, arm="O", model="o1", harness=CODEX)]
    history = [outcome("s1", 1, labels4.HARNESS_ERROR, 2),          # a re-run attempt is a take too
               outcome("s1", 2, labels4.GRADED, 3),
               {"kind": labels4.RULING, "slot": "s1", "attempt": 1},   # a ruling is never an outcome
               outcome("s2", 1, labels4.GRADED, 0),
               outcome("s3", 1, labels4.ABORTED, Ellipsis, events=None),   # no records: no count to read
               outcome("s4", 1, labels4.GRADED, 0, events=["checker-event-reason"])]

    def test_counts_per_half_cell(self):
        got = result.outside_reach_counts(self.rows, self.history)
        by = {(c["arm"], c["half"]): c for c in got}
        self.assertEqual(len(got), 3)
        self.assertEqual({k: by[("A", "trap")][k] for k in ("takes", "with_event", "events", "unread")},
                         {"takes": 3, "with_event": 2, "events": 5, "unread": 0})
        self.assertEqual({k: by[("A", "normal")][k] for k in ("takes", "with_event", "events", "unread")},
                         {"takes": 1, "with_event": 0, "events": 0, "unread": 1})
        # a checker reason that reached routing as an event is an outside-reach take, though the count is 0
        self.assertEqual({k: by[("O", "trap")][k] for k in ("takes", "with_event", "events", "unread")},
                         {"takes": 1, "with_event": 1, "events": 0, "unread": 0})
        self.assertEqual([tuple(c[k] for k in ("arm", "task", "half", "model", "harness")) for c in got],
                         sorted(tuple(c[k] for k in ("arm", "task", "half", "model", "harness")) for c in got))

    def test_an_unregistered_outcome_refuses(self):
        with self.assertRaises(ValueError):
            result.outside_reach_counts(self.rows[:1], self.history[3:4])

    def test_rendered_and_in_the_page(self):
        got = result.outside_reach_counts(self.rows, self.history)
        text = result.render_outside_reach(got)
        self.assertIn("## Outside-reach events", text)
        self.assertIn("| A | `t1` | trap | `a1` | `claude-code` | 3 | 2 | 5 | 0 |", text)
        self.assertIn("| A | `t1` | normal | `a1` | `claude-code` | 1 | 0 | 0 | 1 |", text)
        self.assertIn("No take is committed", result.render_outside_reach([]))
        self.assertEqual(ll.scan_text(text, "reach.md", []), [])
        self.assertEqual(ll.scan_text(result.render_outside_reach([]), "reach.md", []), [])
        import stats
        base = {"stats": stats.derive([], {"tasks_that_run": ["t1"], "harness_models": {CLAUDE: ["a1"]}}),
                "completeness": {}, "pause_notes": [], "stopped": [], "outside_reach": got}
        from unittest import mock
        with mock.patch.object(result.completeness, "render", lambda c: "completeness"):
            self.assertIn("## Outside-reach events", result.render(base))

    def test_from_records_carries_it(self):
        from unittest import mock
        import stats
        design = {"tasks_that_run": ["t1"], "harness_models": {CLAUDE: ["a1"]}}
        with mock.patch.object(result.completeness, "summarize", lambda *a: {}), \
                mock.patch.object(result.check_results, "publication", lambda h, t: {"cells": {}, "attempts": []}), \
                mock.patch.object(result.completeness, "mechanical_states", lambda *a: {}), \
                mock.patch.object(result, "stopped_counts", lambda *a: []), \
                mock.patch.object(result.check_results, "pin_block_events", lambda *a: []):
            got = result.from_records([], {stats.DESIGN_KEY: design}, self.rows, self.history, go=[])
        self.assertEqual(got["outside_reach"], result.outside_reach_counts(self.rows, self.history))


if __name__ == "__main__":
    unittest.main()
