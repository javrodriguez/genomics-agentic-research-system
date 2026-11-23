#!/usr/bin/env python3
"""Every test class the goal's Done lines name must be listed in the draft's checklist_named_tests.

    python3 evals/gap-study-2/check_checklist_names.py <goal-file> [--draft <prereg-draft.json>]

WHY. Round 1's checklist named tests that did not exist (Ruling 30, structural lesson 5). The draft
lists the named tests in `checklist_named_tests`, TheChecklistNamedTestsExist proves each listed name
loads, and this closes the other half: a name the goal file's Done lines use but the draft never listed
would escape that test entirely. Operator-run; the goal file is read, never written.

HOW A NAME IS READ, derived from how the goal file writes them. Only the `## Done means` section is read
(up to the next `## ` heading). Inside it, every backtick code span is examined:
  * a span containing `test_harness.py` names the CamelCase tokens that follow it, up to the first token
    that is not one (`test_harness.py TwoMinuteRead` names TwoMinuteRead; `test_harness.py --mutations`
    names nothing);
  * a span that is a bare CamelCase identifier of at least two capitalised parts (`TwoMinuteRead`) is a
    name too.

WHAT COUNTS AS LISTED. The draft's `checklist_named_tests`, plus `checklist_named_tests_pending` when it
exists. Each may be a list of names, a list of objects carrying `name`, `class` or `test`, or an object
keyed by name (a `_pending` key inside it is read as a further list).

Both differences are printed. Exit 0 only when every Done-line name is listed; 1 when one is not, when the
section or the key is absent, or when the section names no test at all (reading nothing is not a pass);
2 usage or an unreadable file. stdlib only, no model.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DRAFT = HERE / "prereg-draft.json"

KEY, PENDING_KEY = "checklist_named_tests", "checklist_named_tests_pending"
CODE_SPAN = re.compile(r"`([^`\n]+)`")
CAMEL = re.compile(r"^[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)+$")


def done_section(text: str) -> str | None:
    m = re.search(r"^## Done means[^\n]*\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    return m.group(1) if m else None


def done_line_names(section: str) -> list[str]:
    names: list[str] = []
    for span in CODE_SPAN.findall(section):
        tokens = span.split()
        if any(t.endswith("test_harness.py") for t in tokens):
            after = tokens[next(i for i, t in enumerate(tokens) if t.endswith("test_harness.py")) + 1:]
            for t in after:
                if not CAMEL.match(t):
                    break
                names.append(t)
        elif CAMEL.match(span.strip()):
            names.append(span.strip())
    return sorted(set(names))


def _names_in(value) -> tuple[set[str], set[str]]:
    """(listed, pending) from one draft value, whichever of the accepted shapes it has."""
    listed, pending = set(), set()
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "_pending":
                pending |= _names_in(v)[0]
            else:
                listed.add(k)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                listed.add(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("class") or item.get("test")
                if isinstance(name, str):
                    listed.add(name)
    return listed, pending


def main() -> int:
    ap = argparse.ArgumentParser(description="Diff the goal's Done-line test names against the draft.")
    ap.add_argument("goal_file")
    ap.add_argument("--draft", default=str(DEFAULT_DRAFT))
    args = ap.parse_args()

    try:
        goal = Path(args.goal_file).read_text()
        draft = json.loads(Path(args.draft).read_text())
    except (OSError, ValueError) as exc:
        print(f"cannot read the inputs: {exc}")
        return 2

    section = done_section(goal)
    if section is None:
        print("[no-done-section] the goal file has no '## Done means' section, so no name could be read")
        return 1
    names = done_line_names(section)
    if not names:
        print("[no-names-read] the Done means section names no test class; reading nothing is not a pass")
        return 1
    if not isinstance(draft, dict) or KEY not in draft:
        print(f"[no-key] the draft has no '{KEY}' key yet, so no Done-line name can be matched against it")
        print(f"Done-line names ({len(names)}): {', '.join(names)}")
        return 1

    listed, pending = _names_in(draft[KEY])
    if PENDING_KEY in draft:
        more, more_pending = _names_in(draft[PENDING_KEY])
        pending |= more | more_pending
    known = listed | pending

    missing = [n for n in names if n not in known]
    extra = sorted(known - set(names))
    print(f"Done-line names ({len(names)}): {', '.join(names)}")
    print(f"listed in the draft: {len(listed)}, pending: {len(pending)}")
    print(f"named by a Done line but not listed ({len(missing)}): {', '.join(missing) or 'none'}")
    print(f"listed but named by no Done line ({len(extra)}): {', '.join(extra) or 'none'}")
    for n in names:
        if n in pending and n not in listed:
            print(f"  pending: {n}")
    if missing:
        print("[unlisted-name] every test a Done line names must be listed in the draft")
        return 1
    print("every Done-line name is listed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
