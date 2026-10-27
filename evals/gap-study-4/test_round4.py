#!/usr/bin/env python3
"""Round 4's test battery: every tests/test_*.py, discovered with unittest.

    python3 -W ignore evals/gap-study-4/test_round4.py

Round 3's battery is round 3's record and is not copied. Each module's tests live in their own
tests/test_<module>.py, so parallel lanes never edit one file, and each test that guards something mutates
what it guards and watches its check go red. A battery that discovers no test is a defect, not a pass.

Home fold of review round 1 (W1A-2): the count is per module, not per battery. Every tests/test_*.py is loaded
on its own and must hold at least one test, and a test_*.py anywhere deeper under tests/ (which discovery would
not load) fails the battery, so no module rides on another's tests.

Review round 2: a skipped test fails the battery unless its reason is named in SKIP_ALLOWED (one reason, the
box lane's real-scanner return-scan proof; ruled 15 Oct 2026), whatever the form (a skip decorator, skipUnless, a module-level SkipTest, a SkipTest in
setUpClass); a .py file in tests/ that discovery would never run fails it too; and the battery always ends with
one line, `test_round4: <n> run, <m> skipped, <x> expected failures`, which run_checks requires and prints.
Review round 3 (W1A3-2): an @expectedFailure test turns a red guard green, so every expected failure fails the
battery too (no allowance), and it is counted on the closing line.
Run-launcher fix A2 (freeze-final battery on 0e6b6633): a test that leaves sys.stdout or sys.argv changed fails
the battery by name, and both are put back first, so the closing line still reaches the real stdout.

No model, no network, stdlib only.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = HERE / "tests"
PATTERN = "test_*.py"
sys.path.insert(0, str(HERE))

# Skip reasons a test may give and still pass the battery. Each entry needs a review that it measures nothing the
# round relies on.
#   The real-scanner return-scan proof (tests/test_walk_launch.py TestRealReturnScan, REAL_SCAN_SKIP, the same text):
#   ruled by glitch-6b on the box lane's closure review (15 Oct 2026, MINOR A). It fires only where athena_suite.py
#   (GAP4_ATHENA_SUITE_PY, else the operator's checkout) or gitleaks is absent, as on the athena battery's clone. The
#   real-scanner proof is a Mac run recorded in the box lane report; the faked back-scan witnesses run everywhere; the
#   first real walk's fetch is itself live proof. Every other skip stays banned (TestSkipRule shows one).
SKIP_ALLOWED: tuple[str, ...] = (
    "REAL RETURN SCAN NOT RUN: athena_suite.py (GAP4_ATHENA_SUITE_PY) or gitleaks is absent on this machine; the "
    "real-scanner proof is the Mac run in the box lane report, the faked back-scan witnesses run everywhere, and the "
    "first real walk's fetch is live proof",
)
# Python files in tests/ that are helpers, not test modules. Each entry names the test module that runs it.
#   walk_mutation.py: the generator of tests/test_walk_runner.py's generated mutants (lane w10-walk-runner, ruling
#   w10-R3-fold); it holds no test and is imported and run by test_walk_runner (G1, --generated-mutants).
#   Departure w10-7 (lane w10-walk-runner, athena fold of run gap4-w10-5ff8b2e-20261013T003648Z).
#   check_vendor_sources.py: lane vendor-admission T4's source-list check (plan v4 section 9, NIT 7), run by
#   checks.d/vendor-admission.txt once per piece and imported by tests/test_vendor_check.py (SourceLists).
#   vendor_check_fixtures.py: lane vendor-admission T4's writer of F1 and F2 (plan v4 section 8), imported by
#   tests/test_vendor_check.py and tests/test_vendor_body.py and run as --check by checks.d/vendor-admission.txt.
# lane vendor-settle stage K: the plant helper and the two per-harness settlement tables test_vendor_check.py runs
#   mutation_baseline.py: lane t104-mutation-baseline's shared unmutated-baseline gate, imported by every mutation
#   runner (--witnesses, --generated-mutants) and bound by tests/test_mutation_baseline.py.
HELPERS: tuple[str, ...] = ("walk_mutation.py", "check_vendor_sources.py", "vendor_check_fixtures.py",
                            "vendor_plant.py", "vendor_settle_codex.py", "vendor_settle_gemini.py",
                            "mutation_baseline.py")


def suite(folder: Path | None = None) -> unittest.TestSuite:
    folder = TESTS if folder is None else folder
    return unittest.defaultTestLoader.discover(str(folder), pattern=PATTERN, top_level_dir=str(folder))


def module_problems(folder: Path | None = None) -> list[str]:
    """Every test module that would add nothing: one holding no test, one that fails to load, and one deeper than
    tests/ itself."""
    folder = TESTS if folder is None else folder
    out = []
    for f in sorted(folder.glob("*.py")):
        if f.name != "__init__.py" and not f.name.startswith("test_") and f.name not in HELPERS:
            out.append(f"{f.name} is not test_*.py; the battery would never run it")
    for f in sorted(folder.rglob(PATTERN)):
        if "__pycache__" in f.parts:
            continue
        if f.parent != folder:
            out.append(f"{f.relative_to(folder)} is below {folder.name}/; discovery would not load it (keep tests flat)")
            continue
        loaded = unittest.defaultTestLoader.discover(str(folder), pattern=f.name, top_level_dir=str(folder))
        failed = [t for t in _leaves(loaded) if type(t).__name__ == "_FailedTest"]
        if failed:
            out.append(f"{f.name} does not load")
        elif loaded.countTestCases() == 0:
            out.append(f"{f.name} holds no test; a module that runs nothing is not a pass")
    return out


def _leaves(s):
    for t in s:
        if isinstance(t, unittest.TestSuite):
            yield from _leaves(t)
        else:
            yield t


def main(folder: Path | None = None) -> int:
    folder = TESTS if folder is None else folder
    s = suite(folder)
    if s.countTestCases() == 0:
        print(f"test_round4: no test found under {folder}/{PATTERN}; a battery that runs nothing is not a pass")
        return 1
    bad = module_problems(folder)
    for b in bad:
        print(f"test_round4: {b}")
    entry_out, entry_argv = sys.stdout, list(sys.argv)
    result = unittest.TextTestRunner(verbosity=2).run(s)
    leaked = leaked_globals(entry_out, entry_argv)
    for b in leaked:
        print(f"test_round4: {b}")
    banned = [(str(t), why) for t, why in result.skipped if why not in SKIP_ALLOWED]
    for test, why in banned:
        print(f"test_round4: skipped, and its reason is not in SKIP_ALLOWED: {test}: {why}")
    for test, _trace in result.expectedFailures:
        print(f"test_round4: an expected failure, which the battery never allows: {test}")
    xfail = len(result.expectedFailures)
    print(f"test_round4: {result.testsRun - len(result.skipped)} run, {len(result.skipped)} skipped, "
          f"{xfail} expected failures", flush=True)
    return 0 if result.wasSuccessful() and not bad and not banned and not xfail and not leaked else 1


def leaked_globals(entry_out, entry_argv: list[str]) -> list[str]:
    """The process-global state a test left changed: sys.stdout not the stream the battery started on, or sys.argv
    not the list it started with. Each is put back first, so the reason and the closing line still reach the real
    stdout; a hijack is then a named red, never a missing closing line (the freeze-final battery on 0e6b6633: two
    fake-box sweeps on batch's rolling pool left sys.stdout on a dead StringIO)."""
    out = []
    if sys.stdout is not entry_out:
        out.append(f"a test left sys.stdout replaced (a {type(sys.stdout).__name__}, not the stream the battery "
                   f"started on); the battery put it back")
        sys.stdout = entry_out
    if sys.argv != entry_argv:
        out.append(f"a test left sys.argv changed ({sys.argv!r}, not {entry_argv!r}); the battery put it back")
        sys.argv = list(entry_argv)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
