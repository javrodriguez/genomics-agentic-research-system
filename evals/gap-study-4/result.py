#!/usr/bin/env python3
"""Render the round's result from stats and committed completeness, without pooling.

Every statistical table, including the excluded view's three possible shapes,
is emitted by stats.render_md through render_block. This module never recomputes
one. Empty records print no takes, never a measured zero. The frozen task list
and planned rows are the denominator; committed outcomes and rulings carry the
mechanical states. No model, network or earlier-round table is read.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_results
import completeness
import prereg
import stats
import study
import takes

RECORDS = HERE / "records"
PAGE = HERE / "RESULT.md"


def empty_line() -> str:
    return stats.NO_TAKES


def prior_sections() -> str:
    """The not_poolable rule: no comparative section from any earlier round."""
    return ""


def stats_block(derived: dict) -> str:
    return stats.render_block(derived)


def from_records(records: list, pre: dict, rows: list, history: list, table=None) -> dict:
    published = check_results.publication(history, table)
    states = completeness.mechanical_states(history, published["cells"], table)
    return {"stats": stats.derive(records, pre[stats.DESIGN_KEY]),
            "completeness": completeness.summarize(pre, records, states, rows)}


def derive() -> dict | None:
    records = stats.load_results(RECORDS)
    rows, history = takes.load_rows(), takes.read_history()
    if not records and not rows and not history:
        return None
    pre = prereg.require_frozen("publishing the result")
    return from_records(records, pre, rows, history)


def render(rec: dict) -> str:
    lines = [f"# {study.STUDY_TITLE} — result", ""]
    if rec["stats"]["takes"] == 0:
        lines += [empty_line(), ""]
    lines += [completeness.render(rec["completeness"]), stats_block(rec["stats"]), prior_sections()]
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    got = derive()
    if got is None:
        print("result: no takes; no table measured or written")
        return 0
    wanted = render(got)
    if args.write:
        PAGE.write_text(wanted, encoding="utf-8")
    elif not PAGE.is_file() or PAGE.read_text(encoding="utf-8") != wanted:
        print("result: FAIL RESULT.md differs from the records and committed states")
        return 1
    print(f"result: {got['stats']['takes']} records; every stats table and planned half-cell rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
