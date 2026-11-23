#!/usr/bin/env python3
"""Each Gap4 mutation runner that mutation_baseline.py lists as a user refuses a red baseline before it counts a kill
(lane t104-mutation-baseline, OrgOS T104). The exempt runners and why are listed there too.

    python3 -B -W ignore evals/gap-study-4/tests/test_mutation_baseline.py

The hazard: a runner counts a mutant KILLED (or a witness RED) when the tests over it fail. If the tests fail with no
mutant at all, every mutant looks killed and a witness bound to an already-red test is credited for a guard it never
exercised. Each runner below is driven with its children faked so that EVERY run, the unmutated one included, is red in
exactly the way a real kill looks (the bound method failing by an AssertionError carrying its clause). Before this lane
each runner counted those as kills; now each runs the unmutated selection first and raises mutation_baseline.BaselineRed
(exit 3) before it starts or counts a single mutant. The controls show a green baseline still lets the mutants run.

T104Round2 holds the round-1 review of fcf3401's findings: the runners it found unguarded (test_rehearsals is in
WITNESS_RUNNERS), each driven red with no mutant applied, and a check that raises on the unmutated code.

No model, no network, no real child process (subprocess.run is faked), stdlib only.
"""
from __future__ import annotations

import contextlib
import importlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import mutation_baseline as mb  # noqa: E402

MUTANT_FLAGS = ("--mutant", "--gen-mutant", "--mutant-source")


def done(stdout="", stderr="", rc=0):
    return subprocess.CompletedProcess(["fake"], rc, stdout, stderr)


def red_run(tag, method, clause):
    """A verbose unittest run in which `method` fails by an AssertionError carrying `clause`: what a mutant the bound
    test kills prints, and what an unmutated run prints when that test is already red."""
    cls, _, test = method.rpartition(".")
    cls = cls or "Cls"
    stderr = (f"{test} ({cls}.{test}) ... FAIL\n\n{'=' * 70}\nFAIL: {test} (__main__.{cls}.{test})\n{'-' * 70}\n"
              f"Traceback (most recent call last):\n  File \"x.py\", line 1, in {test}\n"
              f"AssertionError: False is not true : {clause}: red\n\n{'-' * 70}\nRan 1 test in 0.010s\n\n"
              f"FAILED (failures=1)\n")
    stdout = (f"{tag}: 1 run, 1 failures, 0 errors, 0 skipped\n"
              f"{tag} outcomes: " + json.dumps({"failures": [f"{cls}.{test}"], "errors": [], "skipped": []}) + "\n")
    return done(stdout, stderr, 1)


def green_run(tag):
    return done(f"{tag}: 3 run, 0 failures, 0 errors, 0 skipped\n"
                f"{tag} outcomes: " + json.dumps({"failures": [], "errors": [], "skipped": []}) + "\n",
                f"{'-' * 70}\nRan 3 tests in 0.010s\n\nOK\n", 0)


class Children:
    """A stand-in for subprocess.run: records each argv; a mutant child is red as a kill, an unmutated one is
    green or red as asked."""

    def __init__(self, tag, method, clause, baseline_red):
        self.tag, self.method, self.clause, self.baseline_red = tag, method, clause, baseline_red
        self.argvs = []

    def __call__(self, argv, *a, **k):
        self.argvs.append(list(argv))
        if self.is_mutant(argv) or self.baseline_red:
            return red_run(self.tag, self.method, self.clause)
        return green_run(self.tag)

    @staticmethod
    def is_mutant(argv):
        return any(flag in argv for flag in MUTANT_FLAGS)

    def mutant_runs(self):
        return [a for a in self.argvs if self.is_mutant(a)]


def first_witness(mod):
    name = sorted(mod.WITNESSES)[0]
    method, clause = mod.WITNESSES[name]
    return name, method, clause


# module -> how to call its subprocess runner for one witness or one generated mutant: (patches, call, method, clause)
def _named(modname):
    def make(mod):
        name, method, clause = first_witness(mod)
        return [], (lambda: mod.run_witnesses([name])), method, clause
    return modname, make


def _all(modname):
    def make(mod):
        name, method, clause = first_witness(mod)
        return [mock.patch.dict(mod.WITNESSES, {name: (method, clause)}, clear=True)], mod.run_witnesses, method, clause
    return modname, make


@contextlib.contextmanager
def module_set_up(mod):
    """test_ci_job's bindings read the workflow its setUpModule loads (its __main__ calls it before --witnesses)."""
    fresh = getattr(mod, "RAW", "") is None
    if fresh:
        mod.setUpModule()
    try:
        yield
    finally:
        if fresh:
            mod.tearDownModule()


PRIMES = []


def prime_stand_in():
    """walk_counts.prime_store in test_build_draft's runner (lane gap-prebeacon-fix3): it readies the covered-set store
    before the baseline, by git reads in this process and, on a miss, the isolated store child; neither is a test run,
    so it stands in here and records how many children had run when it was called. Unstubbed, its git reads were the
    first argv the fake recorded (athena gap4-prebeacon4-90c1fd9, T104.selection and T104.refused)."""
    PRIMES.append(len(getattr(subprocess.run, "argvs", [])))
    return "walk_counts: store stand-in (T104)"


def _grouped(modname, primes=False):
    def make(mod):
        held = module_set_up(mod)
        with module_set_up(mod):
            name = sorted(mod.witness_names())[0]
            method, clause = mod.witness_binding(name)
        extra = [mock.patch.object(importlib.import_module("walk_counts"), "prime_store", prime_stand_in)] if primes else []
        return ([held, mock.patch.object(mod, "witness_groups", return_value=[[name]] + [[]] * 5),
                 mock.patch.object(mod, "witness_names", return_value=[name]), *extra],
                (lambda: mod.run_witnesses(1)), method, clause)
    return modname, make


def _stub(modname):
    def make(mod):
        name = sorted(mod.MUTANTS)[0]
        bound = mod.MUTANTS[name][-1]
        return [mock.patch.dict(mod.MUTANTS, {name: mod.MUTANTS[name]}, clear=True)], mod.run_witnesses, bound, "x"
    return modname, make


# One stand-in mutant: the runners read only these fields, and generating the real ones costs minutes per module.
FAKE_MUTANT = SimpleNamespace(id="t104-stand-in-mutant", kind="delete", line=1, original="x = 1", replacement="pass")


def _generated(modname, owner):
    def make(mod):
        name, method, clause = first_witness(mod)
        return ([mock.patch.object(owner(mod), "generate", return_value=([FAKE_MUTANT], 0))],
                (lambda: mod.run_generated(None, None, 30, {FAKE_MUTANT.id})), method, clause)
    return modname, make


WITNESS_RUNNERS = (_named("test_walk_runner"), _named("test_walk_layout"), _named("test_env_allowlist"),
                   _named("test_walk_builders"), _named("test_holdout_digests"), _named("test_cp6_wiring"),
                   _named("test_walk_plan"), _named("test_cp8_prep"), _named("test_run_builders"),
                   _named("test_config_folder"), _all("test_prereg_order"), _all("test_prereg_status"), _all("test_rehearsals"),
                   _grouped("test_ci_job"), _grouped("test_build_draft", primes=True), _stub("test_stub_agents"))
GENERATED_RUNNERS = (_generated("test_walk_runner", lambda m: importlib.import_module("walk_mutation")),
                     _generated("test_walk_builders", lambda m: m),
                     _generated("test_run_builders", lambda m: m),
                     _generated("test_env_allowlist", lambda m: m))


def drive(modname, make, baseline_red):
    mod = importlib.import_module(modname)
    patches, call, method, clause = make(mod)
    kids = Children(modname, method, clause, baseline_red)
    out = io.StringIO()
    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        stack.enter_context(mock.patch.object(subprocess, "run", kids))
        stack.enter_context(contextlib.redirect_stdout(out))
        try:
            code = call()
        except mb.BaselineRed as e:
            code = e
    return code, kids, out.getvalue()


class T104Helper(unittest.TestCase):
    """The verdict on one finished child run, and the refusal itself."""

    def test_a_green_run_is_green(self):
        self.assertIsNone(mb.child_problem(green_run("t"), "t"))

    def test_each_kind_of_red_is_named(self):
        for case, got in (("a failure", red_run("t", "A.test_a", "C1.x")),
                          ("an error", done("", f"{'=' * 70}\nERROR: test_a (__main__.A.test_a)\nRan 2 tests in 0.1s\n"
                                                "\nFAILED (errors=1)\n", 1)),
                          ("a non-zero exit alone", done("", "Ran 2 tests in 0.1s\n\nOK\n", 1)),
                          ("no test ran", done("", "Ran 0 tests in 0.0s\n\nOK\n", 0)),
                          ("no Ran line", done("", "", 0)),
                          ("an outcomes line naming a failure",
                           done('t outcomes: {"failures": ["A.test_a"], "errors": [], "skipped": []}\n',
                                "Ran 2 tests in 0.1s\n\nOK\n", 0))):
            with self.subTest(case=case):
                self.assertIsNotNone(mb.child_problem(got, "t"), f"T104.verdict: {case} read as green")

    def test_a_skip_is_not_red(self):
        self.assertIsNone(mb.child_problem(done('t outcomes: {"failures": [], "errors": [], "skipped": ["A.b"]}\n',
                                                "Ran 2 tests in 0.1s\n\nOK (skipped=1)\n", 0), "t"))

    def test_require_green_refuses_with_exit_3_and_one_line(self):
        out = io.StringIO()
        with mock.patch.object(subprocess, "run", return_value=red_run("t", "A.test_a", "C1.x")), \
                contextlib.redirect_stdout(out), self.assertRaises(mb.BaselineRed) as got:
            mb.require_green("t", ["x"], timeout=5, tag="t")
        self.assertEqual(got.exception.code, 3, "T104.exit")
        self.assertIsInstance(got.exception, SystemExit, "T104.exit")
        self.assertIn("t BASELINE RED: exit 1; 1 failing or erroring: FAIL __main__.A.test_a", out.getvalue(), "T104.exit")

    def test_a_timeout_refuses(self):
        def slow(*a, **k):
            raise subprocess.TimeoutExpired("x", 5)
        with mock.patch.object(subprocess, "run", slow), contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaises(mb.BaselineRed):
            mb.require_green("t", ["x"], timeout=5)

    def test_require_no_lines(self):
        with contextlib.redirect_stdout(io.StringIO()):
            mb.require_no_lines("t", [])
            with self.assertRaises(mb.BaselineRed):
                mb.require_no_lines("t", ["S1: red"])


class T104SubprocessRunners(unittest.TestCase):
    """Each subprocess runner, every child red as a kill: refused before any mutant child; green baseline: runs."""

    def refused(self, modname, make):
        code, kids, printed = drive(modname, make, baseline_red=True)
        self.assertIsInstance(code, mb.BaselineRed, f"T104.refused: {modname} counted over a red baseline "
                                                    f"(returned {code!r}): {printed[-600:]}")
        self.assertEqual(code.code, mb.BASELINE_RED_EXIT, "T104.refused")
        self.assertEqual(kids.mutant_runs(), [], f"T104.refused: {modname} ran a mutant over a red baseline")
        self.assertEqual(len(kids.argvs), 1, f"T104.refused: {modname} ran {len(kids.argvs)} children")
        self.assertNotRegex(printed, r"\bKILLED\b|: RED\b", f"T104.refused: {modname} credited a kill")
        self.assertIn(f"BASELINE RED", printed, "T104.refused")

    def test_every_witness_runner_refuses_a_red_baseline(self):
        for modname, make in WITNESS_RUNNERS:
            with self.subTest(runner=modname):
                self.refused(modname, make)

    def test_every_generated_runner_refuses_a_red_baseline(self):
        for modname, make in GENERATED_RUNNERS:
            with self.subTest(runner=modname):
                self.refused(modname, make)

    def test_a_green_baseline_lets_the_mutants_run(self):
        for modname, make in WITNESS_RUNNERS + GENERATED_RUNNERS:
            with self.subTest(runner=modname):
                code, kids, printed = drive(modname, make, baseline_red=False)
                self.assertNotIsInstance(code, mb.BaselineRed, f"T104.control: {modname}: {printed[-600:]}")
                self.assertFalse(Children.is_mutant(kids.argvs[0]), f"T104.control: {modname} ran a mutant first")
                self.assertTrue(kids.mutant_runs(), f"T104.control: {modname} ran no mutant over a green baseline")
                self.assertIn("baseline: green", printed, "T104.control")

    def test_the_baseline_runs_the_mutants_own_selection(self):
        """The unmutated run is the mutant command less its mutant flag (the same file and the same tests)."""
        for modname, make in WITNESS_RUNNERS + GENERATED_RUNNERS:
            with self.subTest(runner=modname):
                _, kids, _ = drive(modname, make, baseline_red=False)
                base, mutant = kids.argvs[0], kids.mutant_runs()[0]
                self.assertEqual(base[:5], mutant[:5], f"T104.selection: {modname}: {base} vs {mutant}")
                kept = [a for a in mutant[5:] if a not in ("--failfast",)]
                for flag in MUTANT_FLAGS:
                    if flag in kept:
                        i = kept.index(flag)
                        del kept[i:i + 2]
                for test in kept:
                    self.assertIn(test, base, f"T104.selection: {modname}: the mutant runs {test}, the baseline not")


class T104StorePrime(unittest.TestCase):
    """test_build_draft's runner readies the covered-set store once, before its baseline child, and the store's own
    work is never one of the children T104 counts (lane gap-prebeacon-fix3)."""

    def test_the_prime_runs_once_before_the_baseline(self):
        make = dict(WITNESS_RUNNERS)["test_build_draft"]
        for red in (False, True):
            with self.subTest(baseline_red=red):
                PRIMES.clear()
                _, kids, printed = drive("test_build_draft", make, baseline_red=red)
                self.assertEqual(PRIMES, [0], f"T104.prime: the prime ran {PRIMES}, wanted once before any child")
                self.assertIn("walk_counts: store stand-in (T104)", printed, "T104.prime: its line is printed")
                self.assertFalse(Children.is_mutant(kids.argvs[0]), "T104.prime")


class T104InProcessSweeps(unittest.TestCase):
    """The sweeps that run checks on modules built in memory: a check that is red on the unmutated files refuses."""

    def test_codex_adapter_sweep_refuses_a_red_baseline(self):
        mod = importlib.import_module("test_codex_adapter")
        red = lambda m: ["S9: red on any module"]  # noqa: E731
        with mock.patch.object(mod, "TC_CHECKS", ()), mock.patch.object(mod, "CA_CHECKS", (red,)), \
                mock.patch.object(mod, "mutant_killed", wraps=mod.mutant_killed) as killed, \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                code = mod.run_generated(1, 10 ** 6)
            except mb.BaselineRed as e:
                code = e
        self.assertIsInstance(code, mb.BaselineRed, f"T104.in-process: test_codex_adapter returned {code!r}")
        self.assertEqual(killed.call_count, 0, "T104.in-process: test_codex_adapter built a mutant first")

    def test_labelling_sweep_refuses_a_red_baseline(self):
        mod = importlib.import_module("test_labelling")
        with mock.patch.object(mod, "all_checks", return_value=["S9: red on any module"]), \
                mock.patch.object(mod, "run_mutant", wraps=mod.run_mutant) as ran, \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                got = mod.mutation_sweep(0, 10 ** 6)
            except mb.BaselineRed as e:
                got = e
        self.assertIsInstance(got, mb.BaselineRed, f"T104.in-process: test_labelling returned {got!r}")
        self.assertEqual(ran.call_count, 0, "T104.in-process: test_labelling ran a mutant first")

    def test_review_kit_witnesses_refuse_a_red_bound_test(self):
        mod = importlib.import_module("test_review_kit")
        name, entry = sorted(mod.mutants().items())[0]
        test_id, clause = entry[0], entry[1]
        cls, meth = test_id.split(".")

        def always_red(self):
            raise AssertionError(f"{clause}: red with no mutant")
        out = io.StringIO()
        with mock.patch.object(mod, "mutants", return_value={name: entry}), \
                mock.patch.object(getattr(mod, cls), meth, always_red), contextlib.redirect_stdout(out):
            try:
                code = mod.run_witnesses()
            except mb.BaselineRed as e:
                code = e
        self.assertIsInstance(code, mb.BaselineRed, f"T104.in-process: test_review_kit returned {code!r}: "
                                                    f"{out.getvalue()[-400:]}")
        self.assertNotIn(": RED", out.getvalue(), "T104.in-process: test_review_kit credited a witness")


def refused(call):
    """(the BaselineRed raised, or what the call returned, printed text)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            got = call()
        except mb.BaselineRed as e:
            got = e
    return got, out.getvalue()


def boom(*a, **k):
    raise RuntimeError("t104: a check that raises on the unmutated code")


class T104Round2(unittest.TestCase):
    """Round-1 review of fcf3401 (CHANGES): the runners it found unguarded, each driven red with no mutant applied."""

    def assertRefused(self, got, printed, who, why=None):
        self.assertIsInstance(got, mb.BaselineRed, f"T104.r2: {who} returned {got!r}: {printed[-500:]}")
        self.assertEqual(got.code, mb.BASELINE_RED_EXIT, f"T104.r2: {who}")
        self.assertIn(f"{who} BASELINE RED", printed, f"T104.r2: {who}")
        self.assertNotRegex(printed, r"(?m)^red |: RED\b|\bKILLED\b", f"T104.r2: {who} credited a kill")
        if why:
            self.assertIn(why, got.why, f"T104.r2: {who}")

    # finding 2, and 7 for the three in-process sweeps
    def test_gemini_adapter_sweep_refuses_a_red_baseline(self):
        mod = importlib.import_module("test_gemini_adapter")
        for case, fake in (("red", mock.Mock(return_value=["S9: red on any module"])), ("raises", boom)):
            with self.subTest(case=case), mock.patch.object(mod, "all_checks", fake), \
                    mock.patch.object(mod, "run_mutant", wraps=mod.run_mutant) as ran:
                got, printed = refused(lambda: mod.mutation_sweep(0, 10 ** 6))
                self.assertRefused(got, printed, "test_gemini_adapter generated mutants",
                                   "raised" if case == "raises" else None)
                self.assertEqual(ran.call_count, 0, "T104.r2: test_gemini_adapter ran a mutant first")

    def test_a_raising_check_is_a_red_baseline_in_every_in_process_sweep(self):
        ca = importlib.import_module("test_codex_adapter")
        with mock.patch.object(ca, "TC_CHECKS", ()), mock.patch.object(ca, "CA_CHECKS", (boom,)):
            got, printed = refused(lambda: ca.run_generated(1, 10 ** 6))
        self.assertRefused(got, printed, "test_codex_adapter generated mutants", "raised")
        lb = importlib.import_module("test_labelling")
        with mock.patch.object(lb, "all_checks", boom):
            got, printed = refused(lambda: lb.mutation_sweep(0, 10 ** 6))
        self.assertRefused(got, printed, "test_labelling generated mutants", "raised")

    # finding 3: the five in-process witness runners and native_snapshot
    def test_codex_agents_off(self):
        mod = importlib.import_module("test_codex_agents_off")
        fakes = {c: (lambda: []) for c in mod.CHECKS}
        fakes[mod.MUTANTS[0][2]] = lambda: ["red with no mutant"]
        with mock.patch.dict(mod.CHECKS, fakes):
            got, printed = refused(mod.witnesses)
        self.assertRefused(got, printed, "test_codex_agents_off witnesses")

    def test_vendor_bookkeeping(self):
        mod = importlib.import_module("test_vendor_bookkeeping")
        fakes = {c: (lambda: []) for c in mod.CHECKS}
        fakes[mod.MUTANTS[0][2]] = lambda: ["red with no mutant"]
        with mock.patch.dict(mod.CHECKS, fakes):
            got, printed = refused(mod.witnesses)
        self.assertRefused(got, printed, "test_vendor_bookkeeping witnesses")

    def test_codex_patch_reads(self):
        mod = importlib.import_module("test_codex_patch_reads")
        fakes = {c: (rel, lambda m: []) for c, (rel, _) in mod.CHECKS.items()}
        rel0 = mod.CHECKS[mod.MUTANTS[0][3]][0]
        fakes[mod.MUTANTS[0][3]] = (rel0, lambda m: ["red with no mutant"])
        with mock.patch.dict(mod.CHECKS, fakes):
            got, printed = refused(mod.witnesses)
        self.assertRefused(got, printed, "test_codex_patch_reads witnesses")

    def test_codex_started_file_change(self):
        mod = importlib.import_module("test_codex_started_file_change")
        fakes = {c: (lambda m: []) for c in mod.CHECKS}
        fakes[mod.MUTANTS[0][2]] = lambda m: ["red with no mutant"]
        with mock.patch.dict(mod.CHECKS, fakes):
            got, printed = refused(mod.witnesses)
        self.assertRefused(got, printed, "test_codex_started_file_change witnesses")

    def test_codex_usage_source(self):
        mod = importlib.import_module("test_codex_usage_source")
        with mock.patch.object(mod, "problems", return_value=["U1: red with no mutant"]):
            got, printed = refused(mod.witnesses)
        self.assertRefused(got, printed, "test_codex_usage_source witnesses")

    def test_native_snapshot_one_locator_red_alone(self):
        mod = importlib.import_module("test_native_snapshot")

        def refuses(self_, m=None):
            raise mod.ns().SnapshotRefused("red with no mutant (codex alone)")
        with mock.patch.object(mod.BoxRootNaming, "codex", refuses):
            got, printed = refused(mod.witnesses)
        self.assertRefused(got, printed, "test_native_snapshot witnesses", "SnapshotRefused")

    # finding 5: the endstate control refuses before any witness child
    def test_endstate_control_refuses_before_any_witness(self):
        mod = importlib.import_module("test_endstate")
        asked = []

        def child(arg):
            asked.append(arg)
            return (subprocess.CompletedProcess(["fake"], 1, "", ""),
                    {"run": 1, "failures": {"A.test_a": ["AssertionError: S7-D1.x"]}, "errors": [], "skipped": []})
        with mock.patch.object(mod, "_child", child):
            got, printed = refused(mod.run_witnesses)
        self.assertRefused(got, printed, "test_endstate S7 witnesses")
        self.assertTrue(asked and all(a.startswith("control:") for a in asked),
                        f"T104.r2: test_endstate ran a witness child over a red control: {asked}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
