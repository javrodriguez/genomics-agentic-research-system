#!/usr/bin/env python3
"""Tests for box/stub_agents/: each stub drives a fake runtime through the adapter contract and leaves the end state
its name promises, graded by the merged v4 graders through probes4's constructed triples.

    python3 -B -W ignore evals/gap-study-4/tests/test_stub_agents.py                  the tests
    python3 -B -W ignore evals/gap-study-4/tests/test_stub_agents.py --mutant NAME    the whole file under one mutant
    python3 -B -W ignore evals/gap-study-4/tests/test_stub_agents.py --witnesses      every mutant, each in its own run

WITNESSES. `MUTANTS` holds one in-memory mutant per stub's defining behaviour, each bound to the test method whose
own assertion must catch it. `--witnesses` runs this whole file once per mutant (a fresh process each) and counts a
witness RED only when its bound method FAILs with an AssertionError and does not ERROR. Failures or errors elsewhere
in the same run are collateral: printed, never credited and never hidden (the zero-error rule applies to the bound
method only, as gap4's witness rule B rules it). Mutants are armed in setUpModule, never at import.

Every take is built in memory on the half's first cell (`take.py --check` covers every cell). No model, no container,
no network, standard library only.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

STUDY = Path(__file__).resolve().parent.parent
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))
sys.dont_write_bytecode = True

import agent_adapter as aa  # noqa: E402
import probes4  # noqa: E402
import variants as V  # noqa: E402
from box.stub_agents import agents as ag  # noqa: E402
from box.stub_agents import runtime as rt  # noqa: E402
from box.stub_agents import take as tk  # noqa: E402

MUTANT = None
_patches: list = []
HALVES = [(t, h) for t in probes4.task_ids() for h in V.HALVES]


def _never_killed(self, k, job, ended):
    """Mutant body: the job is waited for whatever its run time, so nothing is ever killed at the cap."""
    run = float(job.get("run_s", rt.FAKE_BACKGROUND_RUN_S))
    self._apply(job, ended + min(run, self.cap) - rt.WRITE_LEAD_S)
    self.ledger.append({"kind": "background", "pid": 4242 + k, "stopped_at": ended + min(run, self.cap)})


def _kill_drops_made_writes(self, k, job, ended):
    """Mutant body (the behaviour before W6B-R1-1): a kill at the cap discards every write, even one made before it."""
    run = float(job.get("run_s", rt.FAKE_BACKGROUND_RUN_S))
    if run > self.cap:
        self.quiescence_kill = True
        self.cap_survivors += 1
        self.ledger.append({"kind": "background", "pid": 4242 + k, "stopped_at": ended + self.cap})
        return
    self._apply(job, ended + run - rt.WRITE_LEAD_S)
    self.ledger.append({"kind": "background", "pid": 4242 + k, "stopped_at": ended + run})


def _operator_on_last(self, line, *, first, budget_s):
    """Mutant body: the operator's writes are recorded after the take's last turn too."""
    k = self._turns + 1
    result = aa.ScriptedAdapter._turn(self, line, first=first, budget_s=budget_s)
    own, job = self.split(k, self.moves[k - 1])
    self.runtime.run_turn(k, line, own, background=job, last=False)
    return result


def _turn_without_runtime(self, line, *, first, budget_s):
    """Mutant body: the scripted record is replayed and the runtime never sees the turn."""
    return aa.ScriptedAdapter._turn(self, line, first=first, budget_s=budget_s)


# name -> (target, attribute, replacement, bound test "Class.method")
MUTANTS = {
    "oracle-acts": (ag.OracleStub, "probe_move", lambda self, pr, h: probes4.act_move(pr, h),
                    "TestOracle.test_oracle_grades_right_on_every_half"),
    "act-holds": (ag.ActOnlyStub, "probe_move", lambda self, pr, h: probes4.hold_move(pr, h),
                  "TestActOnly.test_act_only_is_right_on_the_act_half_and_wrong_on_the_hold_half"),
    "hold-acts": (ag.HoldOnlyStub, "probe_move", lambda self, pr, h: probes4.act_move(pr, h),
                  "TestHoldOnly.test_hold_only_is_right_on_the_hold_half_and_wrong_on_the_act_half"),
    "writer-in-turn": (ag.BackgroundWriterStub, "split", lambda self, k, mv: (mv, None),
                       "TestBackgroundWriter.test_late_writes_are_attributed_to_the_launching_turn"),
    "no-quiescence-wait": (rt.FakeRuntime, "_background", lambda self, k, job, ended: None,
                           "TestBackgroundWriter.test_the_end_state_waits_for_the_writer"),
    "no-cap-kill": (rt.FakeRuntime, "_background", _never_killed,
                    "TestBackgroundWriter.test_a_writer_past_the_cap_is_killed"),
    "turn-skips-runtime": (ag.StubAgent, "_turn", _turn_without_runtime,
                           "TestContract.test_each_stub_drives_the_runtime_once_per_line"),
    "kill-drops-made-writes": (rt.FakeRuntime, "_background", _kill_drops_made_writes,
                               "TestBackgroundWriter.test_writes_made_before_a_kill_land_late"),
    "operator-on-last": (ag.StubAgent, "_turn", _operator_on_last,
                         "TestContract.test_the_stub_take_is_probes4s_own_triple"),
}


def setUpModule():
    if MUTANT:
        target, name, replacement, _bound = MUTANTS[MUTANT]
        patch = mock.patch.object(target, name, replacement)
        patch.start()
        _patches.append(patch)


def tearDownModule():
    while _patches:
        _patches.pop().stop()


def first_cell(task_id, half):
    return tk.cells(task_id, half)[0]


def matching(stub, task_id, half):
    return tk.probes4_result(stub, task_id, half, first_cell(task_id, half))


def built_parts(pr, h, lines, mv):
    """probes4.build_take's own parts for one triple: its transcript and every part it hands Evidence.from_parts
    (captured by wrapping from_parts, which is then called as it was)."""
    real = probes4.es.Evidence.from_parts
    seen = {}

    def capture(**kw):
        seen.update(kw)
        return real(**kw)

    with mock.patch.object(probes4.es.Evidence, "from_parts", capture):
        transcript, _ev = probes4.build_take(pr, h, lines, mv)
    return dict(seen, transcript=transcript)


class EveryTurnOperator:
    """A task's probes, with an operator that writes one note after every turn (probes4 drops the last turn's)."""

    def __init__(self, pr):
        self._pr = pr

    def __getattr__(self, name):
        return getattr(self._pr, name)

    def operator(self, h, k):
        return {f"{probes4.P}/operator-note-{k}.txt": probes4.blob(b"note %d" % k)}


def writer_halves():
    """The halves whose oracle move writes or deletes in its probe turn (where the background writer launches)."""
    out = []
    for t, h in HALVES:
        task, vdoc = V.load_task(t), V.load_variants(t)
        half = probes4.Half(task, vdoc, h)
        mv = probes4.oracle_move(probes4.PROBES[t], half)
        if mv["writes"] or mv["deletes"]:
            out.append((t, h))
    return out


# --------------------------------------------------------------------------------------------- the three graded stubs
class TestOracle(unittest.TestCase):
    def test_oracle_grades_right_on_every_half(self):
        for t, h in HALVES:
            with self.subTest(task=t, half=h):
                got = tk.run_stub_take(ag.ORACLE_NAME, t, h).grade()
                self.assertTrue(got["correct"], f"oracle {t}/{h} graded {got['label']}")
                self.assertEqual(got["label"], matching(ag.ORACLE_NAME, t, h)["label"])


class TestActOnly(unittest.TestCase):
    def test_act_only_is_right_on_the_act_half_and_wrong_on_the_hold_half(self):
        seen = set()
        for t, h in HALVES:
            with self.subTest(task=t, half=h):
                take = tk.run_stub_take(ag.ACT_NAME, t, h)
                got = take.grade()
                self.assertEqual(bool(got["correct"]), take.half.kind == V.ACT,
                                 f"{ag.ACT_NAME} {t}/{h} ({take.half.kind} half) graded {got['label']}")
                self.assertEqual(got["label"], matching(ag.ACT_NAME, t, h)["label"])
                seen.add(take.half.kind)
        self.assertEqual(seen, {V.ACT, V.HOLD})


class TestHoldOnly(unittest.TestCase):
    def test_hold_only_is_right_on_the_hold_half_and_wrong_on_the_act_half(self):
        seen = set()
        for t, h in HALVES:
            with self.subTest(task=t, half=h):
                take = tk.run_stub_take(ag.HOLD_NAME, t, h)
                got = take.grade()
                self.assertEqual(bool(got["correct"]), take.half.kind == V.HOLD,
                                 f"{ag.HOLD_NAME} {t}/{h} ({take.half.kind} half) graded {got['label']}")
                self.assertEqual(got["label"], matching(ag.HOLD_NAME, t, h)["label"])
                seen.add(take.half.kind)
        self.assertEqual(seen, {V.ACT, V.HOLD})

    def test_the_two_constant_stubs_differ_on_every_task(self):
        for t in probes4.task_ids():
            with self.subTest(task=t):
                acts = [tk.run_stub_take(ag.ACT_NAME, t, h).grade()["correct"] for h in V.HALVES]
                holds = [tk.run_stub_take(ag.HOLD_NAME, t, h).grade()["correct"] for h in V.HALVES]
                self.assertNotEqual(acts, holds)
                self.assertEqual(sorted(map(bool, acts)), [False, True])


# --------------------------------------------------------------------------------------------- the background writer
class TestBackgroundWriter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.halves = writer_halves()

    def test_some_halves_launch_a_writer(self):
        self.assertGreaterEqual(len(self.halves), 5, self.halves)

    def test_late_writes_are_attributed_to_the_launching_turn(self):
        for t, h in self.halves:
            with self.subTest(task=t, half=h):
                take = tk.run_stub_take(ag.WRITER_NAME, t, h)
                probe = take.half.task["halves"][h]["probe_operator_turn"]
                mv = probes4.oracle_move(probes4.PROBES[t], take.half)
                paths = set(mv["writes"]) | set(mv["deletes"])
                got = [a for p in sorted(paths) for a in take.evidence.accesses(path=p)
                       if a["op"] in ("modify", "delete") and a["at"] > 100.0 * probe]   # earlier turns' own writes
                self.assertTrue(got, f"{t}/{h}: no write logged")
                self.assertEqual({(a["where"], a["late"]) for a in got}, {(("turn", probe), True)},
                                 f"{t}/{h}: the writer's writes are not the probe turn's late writes")
                stops = [r for r in take.runtime.ledger if r["kind"] == "background"]
                self.assertEqual(len(stops), 1)
                ended = next(r["ended_at"] for r in take.runtime.ledger if r["kind"] == "turn" and r["n"] == probe)
                self.assertGreater(min(a["at"] for a in got), ended)

    def test_the_end_state_waits_for_the_writer(self):
        for t, h in self.halves:
            with self.subTest(task=t, half=h):
                writer = tk.run_stub_take(ag.WRITER_NAME, t, h)
                oracle = tk.run_stub_take(ag.ORACLE_NAME, t, h)
                n = writer.runtime.turns
                self.assertEqual(writer.runtime.snapshots[f"post-{n}"]["entries"],
                                 oracle.runtime.snapshots[f"post-{n}"]["entries"],
                                 f"{t}/{h}: the closing end state lacks the writer's writes")
                got = writer.grade()
                self.assertTrue(got["correct"], f"background-writer {t}/{h} graded {got['label']}")
                self.assertEqual(got["label"], oracle.grade()["label"])
                rec = writer.records()
                self.assertFalse(rec["quiescence_kill"])
                self.assertEqual(rec["quiescence_cap_survivors"], 0)

    def test_a_writer_past_the_cap_is_killed(self):
        class Slow(ag.BackgroundWriterStub):
            run_s = rt.FAKE_QUIESCENCE_CAP_S + 5.0

        for t, h in self.halves:
            with self.subTest(task=t, half=h):
                take = tk.run_stub_take(ag.WRITER_NAME, t, h, stub_cls=Slow)
                rec = take.records()
                self.assertTrue(rec["quiescence_kill"], f"{t}/{h}: a job past the cap was not killed")
                self.assertEqual(rec["quiescence_cap_survivors"], 1)
                mv = probes4.oracle_move(probes4.PROBES[t], take.half)
                probe = take.half.task["halves"][h]["probe_operator_turn"]
                post = take.runtime.snapshots[f"post-{probe}"]["entries"]
                pre = take.runtime.snapshots[f"pre-{probe}"]["entries"]
                for p in mv["writes"]:
                    self.assertEqual(post.get(p), pre.get(p), f"{t}/{h}: a killed job's write to {p} landed")

    def test_writes_made_before_a_kill_land_late(self):
        class Killed(ag.BackgroundWriterStub):
            run_s = rt.FAKE_QUIESCENCE_CAP_S + 0.5     # writes at end + cap - 0.5, killed at end + cap

        for t, h in self.halves:
            with self.subTest(task=t, half=h):
                take = tk.run_stub_take(ag.WRITER_NAME, t, h, stub_cls=Killed)
                rec = take.records()
                self.assertTrue(rec["quiescence_kill"], f"{t}/{h}: the kill was not recorded")
                self.assertEqual(rec["quiescence_cap_survivors"], 1)
                probe = take.half.task["halves"][h]["probe_operator_turn"]
                mv = probes4.oracle_move(probes4.PROBES[t], take.half)
                post = take.runtime.snapshots[f"post-{probe}"]["entries"]
                for p, v in mv["writes"].items():
                    self.assertEqual(post.get(p), probes4.state(v), f"{t}/{h}: a write made before the kill is lost")
                got = [a for p in sorted(set(mv["writes"]) | set(mv["deletes"]))
                       for a in take.evidence.accesses(path=p)
                       if a["op"] in ("modify", "delete") and a["at"] > 100.0 * probe]
                self.assertTrue(got, f"{t}/{h}: no write logged")
                self.assertEqual({(a["where"], a["late"]) for a in got}, {(("turn", probe), True)})

    def test_a_cap_past_the_post_snapshot_is_refused(self):
        with self.assertRaises(ValueError):
            rt.FakeRuntime({}, quiescence_cap_s=rt.POST - rt.ENDED + 0.5)
        rt.FakeRuntime({}, quiescence_cap_s=rt.POST - rt.ENDED)

    def test_a_job_that_would_write_inside_its_turn_is_refused(self):
        class Early(ag.BackgroundWriterStub):
            run_s = rt.WRITE_LEAD_S

        t, h = self.halves[0]
        with self.assertRaises(ValueError):
            tk.run_stub_take(ag.WRITER_NAME, t, h, stub_cls=Early)


# ------------------------------------------------------------------------------------------------- the adapter contract
class TestContract(unittest.TestCase):
    def build(self, stub=ag.ORACLE_NAME, t="template-adherence", h=V.NORMAL, operator=None):
        task, vdoc = V.load_task(t), V.load_variants(t)
        cell = first_cell(t, h)
        half = probes4.Half(task, vdoc, h)
        pr = probes4.PROBES[t]
        lines = probes4.operator_lines(task, vdoc, h, cell, half)
        runtime = rt.FakeRuntime(pr.fixture(half),
                                 operator=None if operator is None else (lambda k: operator.operator(half, k)))
        return ag.STUBS[stub](half, lines, runtime), runtime, lines

    def test_each_stub_drives_the_runtime_once_per_line(self):
        for stub in ag.STUBS:
            with self.subTest(stub=stub):
                agent, runtime, lines = self.build(stub)
                self.assertIsInstance(agent, aa.ScriptedAdapter)
                agent.start_take({"row_id": "r", "slot": 1, "half_cell": "c"})
                results = [agent.turn(line, first=(i == 0), budget_s=ag.BUDGET_S)
                           for i, (_k, line, _m) in enumerate(lines)]
                agent.end_take()
                self.assertEqual(runtime.turns, len(lines), f"{stub}: the runtime saw {runtime.turns} turns")
                self.assertEqual(len([r for r in runtime.ledger if r["kind"] == "turn"]), len(lines))
                self.assertEqual(agent.lines, [line for _k, line, _m in lines])
                self.assertEqual(runtime.state, "finished")
                self.assertEqual(agent.ended, 1)
                self.assertTrue(all(isinstance(r, aa.TurnResult) for r in results))
                rec = aa.harness_records(results, pin=dict(tk.PIN), box=runtime.box_records())
                self.assertTrue(rec["ledger"]["first_turn_started"])
                self.assertEqual(rec["ledger"]["turns"], len(lines))
                self.assertEqual(rec["init"][0]["model"], ag.STUB_MODEL)
                self.assertNotIn("text", rec)

    def test_a_turn_past_the_script_or_out_of_order_is_refused(self):
        agent, runtime, lines = self.build()
        with self.assertRaises(aa.AdapterStateError):
            agent.turn(lines[0][1], first=True, budget_s=ag.BUDGET_S)       # before start_take
        agent.start_take({"row_id": "r", "slot": 1, "half_cell": "c"})
        with self.assertRaises(aa.AdapterStateError):
            agent.turn(lines[0][1], first=False, budget_s=ag.BUDGET_S)      # the first turn without first=True
        for i, (_k, line, _m) in enumerate(lines):
            agent.turn(line, first=(i == 0), budget_s=ag.BUDGET_S)
        with self.assertRaises(aa.AdapterStateError):
            agent.turn("one more", first=False, budget_s=ag.BUDGET_S)      # past the script
        self.assertEqual(runtime.turns, len(lines))
        agent.end_take()
        with self.assertRaises(rt.RuntimeStateError):
            runtime.run_turn(len(lines) + 1, "after", probes4.said("x"))

    def test_the_stub_take_is_probes4s_own_triple(self):
        for t, h in HALVES:
            with self.subTest(task=t, half=h):
                take = tk.run_stub_take(ag.ORACLE_NAME, t, h)
                task, vdoc = V.load_task(t), V.load_variants(t)
                pr = probes4.PROBES[t]
                lines = probes4.operator_lines(task, vdoc, h, take.cell, take.half)
                parts = built_parts(pr, take.half, lines, probes4.oracle_move(pr, take.half))
                self.assertEqual(take.transcript, parts["transcript"])
                for k in ("ledger", "snapshots", "access", "health", "blobs"):
                    self.assertEqual(getattr(take.runtime, k) if k != "health" else take.runtime.health(), parts[k],
                                     f"{t}/{h}: the stub take's {k} is not probes4's")
                writer = tk.run_stub_take(ag.WRITER_NAME, t, h)
                self.assertEqual([r for r in writer.runtime.ledger if r["kind"] != "background"], parts["ledger"],
                                 f"{t}/{h}: the writer's ledger differs beyond its background record")
                last = f"post-{writer.runtime.turns}"
                self.assertEqual(writer.runtime.snapshots[last], parts["snapshots"][last])
                want = matching(ag.ORACLE_NAME, t, h)
                got = take.grade()
                for k in ("label", "correct", "human_sample", "human_check"):
                    self.assertEqual(got.get(k), want.get(k), k)
        # On the real tasks the operator writes only after turn 2 of explain-not-act's three, never after a take's
        # last turn, so a constructed operator that writes after every turn binds probes4's "never after the last".
        t, h = "template-adherence", V.NORMAL
        everywhere = EveryTurnOperator(probes4.PROBES[t])
        with mock.patch.dict(probes4.PROBES, {t: everywhere}):
            agent, runtime, lines = self.build(ag.ORACLE_NAME, t, h, operator=everywhere)
            agent.start_take({"row_id": "r", "slot": 1, "half_cell": "c"})
            for i, (_k, line, _m) in enumerate(lines):
                agent.turn(line, first=(i == 0), budget_s=ag.BUDGET_S)
            agent.end_take()                       # the ledger is compared before endstate ever reads it
            parts = built_parts(everywhere, agent.half, lines, probes4.oracle_move(everywhere, agent.half))
        self.assertEqual(runtime.ledger, parts["ledger"], "the operator's writes after the last turn differ")
        self.assertEqual(len([r for r in parts["ledger"] if r["kind"] == "operator"]), len(lines) - 1)

    def test_the_check_command_passes_on_one_task(self):
        n, problems = tk.check(["template-adherence"])
        self.assertEqual(problems, [])
        self.assertEqual(n, len(tk.cells("template-adherence", V.NORMAL)) * len(ag.STUBS)
                         + len(tk.cells("template-adherence", V.TRAP)) * len(ag.STUBS))


# ------------------------------------------------------------------------------------------------- the witness registry
class TestWitnessRegistry(unittest.TestCase):
    def test_every_mutant_binds_a_method_of_this_file(self):
        for name, (_t, _a, _r, bound) in MUTANTS.items():
            with self.subTest(name):
                cls, meth = bound.split(".")
                self.assertTrue(callable(getattr(globals()[cls], meth, None)), bound)

    def test_every_stub_has_a_witness(self):
        bound = {b.split(".")[0] for *_x, b in MUTANTS.values()}
        self.assertLessEqual({"TestOracle", "TestActOnly", "TestHoldOnly", "TestBackgroundWriter"}, bound)

    def test_the_parser_reads_red_only_from_the_bound_methods_own_assertion(self):
        bound = "TestOracle.test_oracle_grades_right_on_every_half"
        fail = ("test_oracle_grades_right_on_every_half (__main__.TestOracle.test_oracle_grades_right_on_every_half) "
                "... FAIL\n\n" + "=" * 70 + "\nFAIL: test_oracle_grades_right_on_every_half "
                "(__main__.TestOracle.test_oracle_grades_right_on_every_half)\n" + "-" * 70 +
                "\nTraceback\nAssertionError: True is not false\n\n" + "-" * 70 + "\nRan 1 test\n")
        self.assertEqual(witness_verdict(fail, bound)[0], "RED")
        self.assertEqual(witness_verdict(fail.replace("FAIL", "ERROR").replace("AssertionError", "KeyError"),
                                         bound)[0], "NOT-RED")
        self.assertEqual(witness_verdict(fail.split("=" * 70)[0].replace("... FAIL", "... ok"), bound)[0], "NOT-RED")


# ------------------------------------------------------------------------------------------------- the witness runner
def _blocks(out: str) -> dict:
    """{(kind, Class.method): body} for every FAIL: and ERROR: block of a verbose unittest run."""
    got = {}
    parts = re.split(r"^={70}$", out, flags=re.M)
    for part in parts[1:]:
        m = re.match(r"\s*(FAIL|ERROR): (\w+) \([\w.]*?(\w+)\.(\w+)\)", part)
        if m:
            got[(m.group(1), f"{m.group(3)}.{m.group(4)}")] = part
    return got


def witness_verdict(out: str, bound: str) -> tuple:
    """("RED" or "NOT-RED", collateral): RED only when the bound method FAILs by an AssertionError and never ERRORs."""
    blocks = _blocks(out)
    fail = blocks.get(("FAIL", bound))
    red = fail is not None and "AssertionError" in fail and ("ERROR", bound) not in blocks
    collateral = sorted(f"{k} {m}" for (k, m) in blocks if m != bound)
    return ("RED" if red else "NOT-RED"), collateral


def run_witnesses() -> int:
    red = 0
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_stub_agents witnesses", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve())],
                                    timeout=1800, env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
    for name, (*_x, bound) in MUTANTS.items():
        p = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name],
                           capture_output=True, text=True,
                           env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
        verdict, collateral = witness_verdict(p.stdout + p.stderr, bound)
        red += verdict == "RED"
        print(f"witness {name}: {verdict} (bound {bound}; run exit {p.returncode}); collateral, not credited: "
              f"{', '.join(collateral) or 'none'}", flush=True)
    print(f"test_stub_agents witnesses: {red} of {len(MUTANTS)} red", flush=True)
    return 0 if red == len(MUTANTS) else 1


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        sys.exit(run_witnesses())
    if "--mutant" in sys.argv:
        at = sys.argv.index("--mutant")
        MUTANT = sys.argv[at + 1]
        if MUTANT not in MUTANTS:
            sys.exit(f"no mutant {MUTANT!r}; known: {', '.join(MUTANTS)}")
        del sys.argv[at:at + 2]
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"test_stub_agents: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped", flush=True)
    sys.exit(0 if result.wasSuccessful() else 1)
