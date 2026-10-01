#!/usr/bin/env python3
"""F-01: number-fidelity takes whose affirmation window carries an affirmation substring inside a negated or
larger word. Read-only; rule frozen in PREREG.md (section F-01) and rules.py.

    python3 evals/validity-followups/f01_affirmations.py            # print the table
    python3 evals/validity-followups/f01_affirmations.py --write    # write results/F-01.json and RESULTS.md's block
    python3 evals/validity-followups/f01_affirmations.py --check    # exit 1 unless both re-derive
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import common  # noqa: E402
import rules  # noqa: E402

COLUMNS = ("flawed", "flawed_only")
NAMES = {"flawed": "Negated or larger-word affirmation", "flawed_only": "…and no other affirmation"}


def per_take(rnd, spec, half, turns, said, tools):
    return rules.f01_take(said, rules.grader_of(rnd, "number-fidelity").AFFIRM)


def derive() -> dict:
    return common.derive_counts("F-01", COLUMNS, "flawed", per_take)


def render(data: dict) -> str:
    return common.render_counts(data, NAMES)


if __name__ == "__main__":
    raise SystemExit(common.main(derive, render, sys.argv[1:]))
