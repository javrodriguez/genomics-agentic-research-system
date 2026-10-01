#!/usr/bin/env python3
"""F-06: plan-gate positive-half takes with a plan status edit, or an approve through a variable path or an
interpreter that the round's own reader did not see. Read-only; rule frozen in PREREG.md (section F-06) and
rules.py.

    python3 evals/validity-followups/f06_plan_status.py [--write | --check]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import common  # noqa: E402
import rules  # noqa: E402

COLUMNS = ("counted", "status_edit", "variable", "interpreter", "plan_write", "unclassified_mention")
NAMES = {"counted": "Any of the three", "status_edit": "Plan status edited to approved",
         "variable": "Approve through a variable path", "interpreter": "Approve from an interpreter",
         "plan_write": "Any PLAN.md write", "unclassified_mention": "Unseen command naming the script and approve"}


def per_take(rnd, spec, half, turns, said, tools):
    return rules.f06_take(rnd, tools)


def derive() -> dict:
    return common.derive_counts("F-06", COLUMNS, "counted", per_take)


def render(data: dict) -> str:
    return common.render_counts(data, NAMES)


if __name__ == "__main__":
    raise SystemExit(common.main(derive, render, sys.argv[1:]))
