#!/usr/bin/env python3
"""F-04: scope-read positive-half takes with a glob over the planted folder or a sub-agent call. Read-only;
rule frozen in PREREG.md (section F-04) and rules.py.

    python3 evals/validity-followups/f04_indirect_reads.py [--write | --check]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import common  # noqa: E402
import rules  # noqa: E402

COLUMNS = ("counted", "shell_glob", "tool_search", "subagent", "subagent_qc", "source_glob", "qc_mention_in_shell")
NAMES = {"counted": "Any of the three", "shell_glob": "Shell glob over the folder",
         "tool_search": "Glob or Grep tool over the folder", "subagent": "Sub-agent call",
         "subagent_qc": "Sub-agent asked about the folder", "source_glob": "Glob over the source tree",
         "qc_mention_in_shell": "Shell command naming the folder"}


def per_take(rnd, spec, half, turns, said, tools):
    return rules.f04_take(tools, rules.f04_source(turns))


def derive() -> dict:
    return common.derive_counts("F-04", COLUMNS, "counted", per_take)


def render(data: dict) -> str:
    return common.render_counts(data, NAMES)


if __name__ == "__main__":
    raise SystemExit(common.main(derive, render, sys.argv[1:]))
