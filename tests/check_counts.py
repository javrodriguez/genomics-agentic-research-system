#!/usr/bin/env python3
"""Guard: the test count this repository STATES must equal the count it HAS.

Run:  python3 tests/check_counts.py           (from the repo root)
      python3 tests/check_counts.py --run     also run the suite, and cross-check the fast path

WHY THIS EXISTS. On 5 September 2026 the suite said 103 and three documents said 99. The wrong
number had already been copied into eleven job-application files before anyone noticed, and it
was fixed by hand -- which fixes the instance and not the class. Nothing stopped it recurring,
so this does. It is prevention, not repair.

WHERE THE NUMBER COMES FROM. The runner, never a grep. `grep -c 'def test_'` undercounts a
parametrized suite and overcounts a commented-out one; the only honest source is the loader that
actually collects the tests. By default this asks unittest's loader for the count without paying
for a full run, which is what makes it cheap enough to sit in CI; `--run` executes the suite and
asserts the loader agreed with `Ran N tests`, so the cheap path is itself checked rather than
trusted.

THIS FILE CONTAINS NO LITERAL COUNT. A guard that hard-codes the number it is checking has to be
edited every time the suite grows, and an edit is exactly the step that goes wrong. Search this
file for the current total and you will not find it.

WHAT COUNTS AS A CLAIM, and the part that took the thinking. DEVELOPMENT.md's changelog is full
of test counts -- 46, 44, 42, 25 -- and every one of them is TRUE: they record what the suite was
at that time, or what one wrapper's own tests number. Forcing those to equal today's total would
be wrong, and the naive guard that does it gets deleted the first time it fires. So each claim is
classified:

    historical   a changelog row (a `| MM-DD |` table row) or a "Previous milestone" line. These
                 record the past and are reported, never enforced.
    exempt       a claim carrying the marker below, for a real count that is not the suite total
                 (one wrapper's own tests, say). Explicit, so it is a decision someone made and
                 can be read back.
    current      everything else -- and these MUST equal the derived total.

Anything the classifier cannot place is not silently skipped: it is reported and the guard exits
non-zero, demanding that someone decide which kind it is. Fail-closed, because a new unmarked
claim is precisely how the next 99 gets written.

AND IT REFUSES TO PASS VACUOUSLY. If no current claim was found at all, this exits non-zero. A
guard that enforces nothing prints the same green as a guard that enforces everything, and the
whole point of this file is that a green means something.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TESTS = REPO / "tests"

# The documents that state the count, and which this guard keeps honest.
DOCUMENTS = ["README.md", "DEVELOPMENT.md"]

# A count-shaped claim: "<n> tests", or "run_tests.py (<n>)". The example is deliberately not
# written with the real total: a comment carrying the number this file exists to avoid
# hard-coding would go stale in exactly the way it is here to prevent.
CLAIM_PATTERNS = [
    re.compile(r"(?<![\w.])(\d[\d,]*)\s+tests?\b", re.I),
    re.compile(r"run_tests\.py[^)\n]{0,40}\((\d[\d,]*)\)"),
]

# A changelog row, which records what was true then.
HISTORICAL_LINE = [
    re.compile(r"^\s*\|\s*\d{2}-\d{2}\s*\|"),
    re.compile(r"Previous milestone", re.I),
]

# The marker that exempts a real count which is not the suite total. Kept as an HTML comment so
# it is invisible in the rendered document and obvious in the source.
EXEMPT_MARKER = "<!-- not-the-suite-total -->"

RAN_LINE = re.compile(r"^Ran (\d+) tests?", re.M)


def derive_from_loader() -> int:
    """The number of tests the runner would run, asked of the loader that collects them."""
    sys.path.insert(0, str(TESTS))
    import run_tests  # noqa: E402 -- located by the line above

    suite = unittest.defaultTestLoader.loadTestsFromModule(run_tests)
    if unittest.defaultTestLoader.errors:
        raise SystemExit("the loader could not import part of the suite:\n  "
                         + "\n  ".join(unittest.defaultTestLoader.errors))
    return suite.countTestCases()


def derive_from_run() -> int:
    """The number the runner itself reports. Slow, and the thing the fast path is checked against."""
    sys.path.insert(0, str(TESTS))
    import run_tests  # noqa: E402

    suite = unittest.defaultTestLoader.loadTestsFromModule(run_tests)
    buf = io.StringIO()
    with redirect_stderr(buf):
        unittest.TextTestRunner(stream=buf, verbosity=1).run(suite)
    m = RAN_LINE.search(buf.getvalue())
    if not m:
        raise SystemExit("the runner printed no 'Ran N tests' line; nothing can be derived")
    return int(m.group(1))


def classify(line: str) -> str:
    if any(p.search(line) for p in HISTORICAL_LINE):
        return "historical"
    if EXEMPT_MARKER in line:
        return "exempt"
    return "current"


def claims() -> list[dict]:
    found: list[dict] = []
    for name in DOCUMENTS:
        path = REPO / name
        if not path.is_file():
            found.append({"document": name, "line_no": 0, "kind": "missing",
                          "stated": None, "line": ""})
            continue
        for line_no, line in enumerate(path.read_text().splitlines(), start=1):
            seen: set[int] = set()
            for pattern in CLAIM_PATTERNS:
                for m in pattern.finditer(line):
                    stated = int(m.group(1).replace(",", ""))
                    if stated in seen:
                        continue
                    seen.add(stated)
                    found.append({"document": name, "line_no": line_no,
                                  "kind": classify(line), "stated": stated,
                                  "line": line.strip()})
    return found


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Check that the test count stated in the documents equals the count the "
                    "suite actually has. Contains no literal count.")
    ap.add_argument("--run", action="store_true",
                    help="also execute the suite and assert the loader agreed with it")
    args = ap.parse_args()

    derived = derive_from_loader()
    print(f"suite: {derived} tests, from unittest's loader")

    if args.run:
        ran = derive_from_run()
        print(f"suite: {ran} tests, from a real run")
        if ran != derived:
            print(f"\nFAIL: the loader says {derived} and the runner ran {ran}. The cheap path "
                  f"this guard uses in CI does not agree with the suite, so nothing it says "
                  f"about the documents can be trusted.")
            return 1

    problems: list[str] = []
    enforced = 0
    for c in claims():
        if c["kind"] == "missing":
            problems.append(f"{c['document']} is not in the tree, so its claim cannot be checked")
            print(f"  MISSING   {c['document']}")
            continue
        where = f"{c['document']}:{c['line_no']}"
        if c["kind"] == "historical":
            print(f"  history   {where:22s} states {c['stated']} — a record of what was true "
                  f"then, not enforced")
            continue
        if c["kind"] == "exempt":
            print(f"  exempt    {where:22s} states {c['stated']} — marked as not the suite total")
            continue
        enforced += 1
        if c["stated"] != derived:
            problems.append(
                f"{where} states {c['stated']} tests; the suite has {derived}. "
                f"Line: {c['line'][:120]}")
            print(f"  DRIFT     {where:22s} states {c['stated']}, suite has {derived}")
        else:
            print(f"  ok        {where:22s} states {c['stated']}")

    print(f"enforced={enforced}")
    if not enforced:
        print("\nFAIL: no current claim was found in any document. This guard just checked "
              "nothing and would have printed green forever. Either a document lost its count, "
              "or every claim was classified away.")
        return 1

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        print("\nFix the DOCUMENT if the suite is right, or the suite if the document is. Do not "
              "fix this guard.")
        return 1

    print("clean — every current claim matches the suite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
