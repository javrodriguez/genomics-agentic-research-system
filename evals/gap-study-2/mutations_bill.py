#!/usr/bin/env python3
"""The call-site mutations for the bill (CP3, done-line 13), registered by mutations.py.

Each breaks costs.py where the dollar line is decided or bound, in a throwaway copy, watches
TheBillIsEvidencedTakeByTake green first, and requires it to go red naming what was planted.
"""

from __future__ import annotations

from mutations import Sandbox, _edit, _th

GUARD = "TheBillIsEvidencedTakeByTake"


def m_bill_evidenced_with_a_record_missing(s: Sandbox) -> tuple[int, str]:
    """The $0 claimed evidenced with a take's environment record missing: the absent file read as no gap."""
    s.control(_th(s, GUARD))
    _edit(s.study / "costs.py", '        return ["no environment record"]\n', "        return []\n")
    code, out = s.run_out(_th(s, GUARD))
    return Sandbox.expect(code, out, "no environment record"), f"test_harness.py {GUARD}"


def m_null_turn_source_counted_as_evidence(s: Sandbox) -> tuple[int, str]:
    """A turn whose credential source is null (or unreported) skipped, so the turns that did report carry the take."""
    s.control(_th(s, GUARD))
    _edit(s.study / "costs.py",
          '        if src is None:\n            gaps.append(f"{label} reported no credential source")\n'
          '            turn_gaps += 1\n            continue\n',
          "        if src is None:\n            continue\n")
    code, out = s.run_out(_th(s, GUARD))
    return Sandbox.expect(code, out, "reported no credential source"), f"test_harness.py {GUARD}"


def m_dollar_line_unbound_by_check(s: Sandbox) -> tuple[int, str]:
    """The dollar line left out of render, at its call site: --check compares the tables only, and a typed line stands."""
    s.control(_th(s, GUARD))
    _edit(s.study / "costs.py", '    lines = _section(lines, BILL, ["", got["bill"], ""])\n', "")
    code, out = s.run_out(_th(s, GUARD))
    return Sandbox.expect(code, out, "a hand-edited dollar line went unseen"), f"test_harness.py {GUARD}"


MUTATIONS = [
    ("the $0 claimed evidenced with a record missing", m_bill_evidenced_with_a_record_missing, False),
    ("a null per-turn credential source counted as evidence", m_null_turn_source_counted_as_evidence, False),
    ("the dollar line no longer bound by costs.py --check", m_dollar_line_unbound_by_check, False),
]
