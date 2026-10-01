#!/usr/bin/env python3
"""F-07: precondition-refusal positive-half takes with no refusal text after the probe. Read-only; rule frozen
in PREREG.md (section F-07) and rules.py.

    python3 evals/validity-followups/f07_refusal_text.py [--write | --check]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import common  # noqa: E402
import rules  # noqa: E402

COLUMNS = ("no_marker", "no_marker_no_word", "nothing_said")
NAMES = {"no_marker": "No refusal marker after the probe", "no_marker_no_word": "…and no refusal word",
         "nothing_said": "No text at all after the probe"}


def per_take(rnd, spec, half, turns, said, tools):
    return rules.f07_take(said, rules.grader_of(rnd, "precondition-refusal").REFUSAL_MARKER)


def derive() -> dict:
    return common.derive_counts("F-07", COLUMNS, "no_marker", per_take)


def render(data: dict) -> str:
    return common.render_counts(data, NAMES)


if __name__ == "__main__":
    raise SystemExit(common.main(derive, render, sys.argv[1:]))
