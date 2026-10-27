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

In-process runners (the ones that run checks on modules built in memory) hand require_clean a function computing the
lines their checks print over the unmutated code; any line refuses the same way, and so does a check that raises.

WHO USES IT (round 2 of the lane, after the round-1 review of fcf3401; tests/test_mutation_baseline.py drives each):
  subprocess --witnesses, the bound methods' union or the whole file first (require_green): build_draft, ci_job,
    config_folder, cp6_wiring, cp8_prep, env_allowlist, holdout_digests, prereg_order, prereg_status, rehearsals,
    run_builders, stub_agents, walk_builders, walk_layout, walk_plan, walk_runner;
  subprocess --generated-mutants, GENERATED_ORDER first (require_green): env_allowlist, run_builders, walk_builders,
    walk_runner;
  in-process --generated-mutants (require_clean): codex_adapter, gemini_adapter, labelling;
  in-process --witnesses (require_clean): codex_agents_off, codex_patch_reads, codex_started_file_change,
    codex_usage_source, native_snapshot (both locators on the real module), review_kit (each bound test, unmutated),
    vendor_bookkeeping;
  test_endstate --witnesses: its own unmutated control runs first, and a control that is not clean now refuses (refuse)
    before any witness child.
EXEMPT, each already controlled by its own code:
  test_walk_plan --generated-mutants: re-emits the unmutated module and returns 1, before any mutant, when it fails;
  test_gemini_tool_registry and test_gemini_undeclared_args --witnesses: return 1, before any witness, when the
    unmutated table or reader is not green;
  the TestWitnesses classes of codex_adapter, gemini_adapter and labelling (--witnesses): each witness asserts its
    bound check green on the real module before mutating it;
  test_pf1_freeze_gates TestWitnesses: in-suite only (no --witnesses command, though its docstring names one); each
    clause's own test runs green on the unmutated code in the same battery, so a red clause fails the battery;
  walk_mutation.py generates mutants and runs none; test_pipeline.py's --mutant has no runner of its own.
These exempt runners exit 1, not BASELINE_RED_EXIT, on a red baseline; fail-closed, recorded, not changed here.

RESIDUAL (review finding 6, recorded, not fixed): a witness baseline runs the union of its bound methods in one
process, while each mutant child runs one method alone (or the whole file); a test green in the union but red alone
(order or shared-state dependent) would still be credited, and one baseline run cannot catch a flaky test. A red in
the union only ever refuses, so nothing is over-counted the other way.
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


def require_clean(runner: str, compute) -> None:
    """In-process runners: `compute()` returns the lines their checks print over the unmutated code. Any line refuses,
    and so does an exception raised while computing them (a crash on the unmutated code is a red baseline, named as
    one with exit 3, never a traceback)."""
    try:
        lines = list(compute())
    except Exception as e:  # noqa: BLE001 - any failure on the unmutated code is red
        refuse(runner, f"a check raised on the unmutated code: {type(e).__name__}: {str(e)[:300]}")
    require_no_lines(runner, lines)


def require_no_lines(runner: str, lines: list) -> None:
    """In-process sweeps: the checks' lines over the unmutated files. Any line refuses."""
    if lines:
        refuse(runner, f"{len(lines)} check line(s) over the unmutated files: "
                       + "; ".join(str(x)[:160] for x in lines[:5]) + (" ..." if len(lines) > 5 else ""))
    print(f"{runner} baseline: green, unmutated (no check line)", flush=True)
