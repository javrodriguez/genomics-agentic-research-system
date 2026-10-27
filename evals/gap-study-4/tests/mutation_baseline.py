#!/usr/bin/env python3
"""The unmutated baseline every Gap4 mutation runner reads before it counts a kill (lane t104-mutation-baseline,
OrgOS T104). Stdlib only; it holds no test (tests/test_mutation_baseline.py binds it).

A runner counts a mutant KILLED, or a witness RED, when the tests run over the mutant fail. Over a baseline that is
already red, every mutant looks killed and a witness bound to a red test is credited for a guard it never exercised.
So each runner first runs the very selection its mutant children run (the same file, the same tests, the same cwd and
environment), with no mutant applied, and when that run is not green it refuses with BASELINE_RED_EXIT before it runs
or counts any mutant: BaselineRed is a SystemExit, so no `except Exception` in a runner can swallow it, and a
`python3 tests/test_x.py --witnesses` line exits 3 with one `BASELINE RED` line naming why.

Green means all of: exit 0; unittest's own `Ran N tests` line with N >= 1; no `FAIL:` or `ERROR:` block; and, when
the runner prints a `<tag> outcomes: {...}` line, its failures and errors both empty. A skip is not red here (a skipped
test kills nothing); each runner's own rules on skips stay as they were.

In-process sweeps (the ones that run checks on modules built in memory) hand require_no_lines the lines their checks
print over the unmutated files; any line refuses the same way.
"""
from __future__ import annotations

import json
import re
import subprocess

BASELINE_RED_EXIT = 3


class BaselineRed(SystemExit):
    """The unmutated baseline is not green: nothing was counted. code == BASELINE_RED_EXIT."""

    def __init__(self, runner: str, why: str):
        super().__init__(BASELINE_RED_EXIT)
        self.runner, self.why = runner, why


def child_problem(got, tag: str | None = None) -> str | None:
    """Why one finished child test run is not a green baseline, or None when it is."""
    out, err = got.stdout or "", got.stderr or ""
    text = out + "\n" + err
    problems = []
    if got.returncode != 0:
        problems.append(f"exit {got.returncode}")
    ran = [int(n) for n in re.findall(r"^Ran (\d+) tests? in ", text, re.M)]
    if not ran or ran[-1] < 1:
        problems.append("no `Ran N tests` line with N >= 1 (no test ran)")
    reds = re.findall(r"^(FAIL|ERROR): (\S+) \(([^)\n]*)\)", text, re.M)
    if reds:
        named = ", ".join(f"{kind} {where}" for kind, _, where in reds[:8])
        problems.append(f"{len(reds)} failing or erroring: {named}" + (" ..." if len(reds) > 8 else ""))
    if tag:
        record = re.findall(r"^" + re.escape(tag) + r" outcomes: (\{.*\})$", out, re.M)
        if record:
            try:
                outcome = json.loads(record[-1])
                red = list(outcome.get("failures") or []) + list(outcome.get("errors") or [])
            except (ValueError, AttributeError, TypeError):
                red = ["(an unreadable outcomes line)"]
            if red:
                problems.append(f"the outcomes line names {sorted(set(red))[:8]}")
    return "; ".join(problems) or None


def refuse(runner: str, why: str, tail: str = ""):
    """Print the one refusal line (and the child's tail, when there is one) and raise BaselineRed."""
    print(f"{runner} BASELINE RED: {why}. No mutant was run or counted: over a red baseline every mutant looks "
          f"killed. Make the unmutated run green first (exit {BASELINE_RED_EXIT}).", flush=True)
    if tail:
        print(tail, flush=True)
    raise BaselineRed(runner, why)


def require_green(runner: str, argv: list, *, timeout: float, tag: str | None = None, cwd=None, env=None) -> None:
    """Run `argv` (the runner's own mutant command, less the mutant) once; return when it is green, else refuse."""
    try:
        got = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env)
    except subprocess.TimeoutExpired:
        refuse(runner, f"the unmutated run did not finish in {timeout} s")
    why = child_problem(got, tag)
    if why is not None:
        refuse(runner, why, ((got.stdout or "")[-2000:] + (got.stderr or "")[-2000:]).strip())
    ran = re.findall(r"^Ran (\d+) tests? in ", (got.stdout or "") + "\n" + (got.stderr or ""), re.M)
    print(f"{runner} baseline: green, unmutated ({ran[-1]} tests ran)", flush=True)


def require_no_lines(runner: str, lines: list) -> None:
    """In-process sweeps: the checks' lines over the unmutated files. Any line refuses."""
    if lines:
        refuse(runner, f"{len(lines)} check line(s) over the unmutated files: "
                       + "; ".join(str(x)[:160] for x in lines[:5]) + (" ..." if len(lines) > 5 else ""))
    print(f"{runner} baseline: green, unmutated (no check line)", flush=True)
