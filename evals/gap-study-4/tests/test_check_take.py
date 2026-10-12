#!/usr/bin/env python3
"""Lane w6h (Gap Study round 4, slice S6): check_take.py's round-4 edits (the plan's UPDATE check_take.py task), on
synthetic transcripts only.

What is tested, each edit with its own bound check and a whole-file witness of check_take.py:

  K1-arm      constant_problems binds the permission mode the take's ARM pins (driver_constants.
              permission_mode_by_arm), never round 3's single constant; an arm with no pin never binds. Witness:
              line 902 back to round 3's constant.
  K2-wording  check() requires the lines of the take's own wording (wording_script), not the half's script, and
              check4 refuses a take without one. Witness: line 1604 back to the half's script.
  K3-events   check4 lifts study-materials-reached, account-email and read-outside-the-checkout (routing.json's
              checker_reasons_become_events) out of the routable reasons and counts each instance as an event.
              Witness: nothing lifted.
  K4-mode     recorded_mode_problems: a transcript recording exactly the arm's pinned bypass mode passes, and the
              take routes graded; any other recorded mode carries constant-binding, so the take routes by the table
              (a rehearsal before the first turn, harness-error after it) and never grades. Witness: the recorded
              mode never compared.

Fakes and synthetic strings only: no model, vendor, network, credential or holdout. setUpModule arms a process guard
that refuses every process start, gives the checker a scratch home folder, patches prereg's readers with a synthetic
design (this base has no pre-registration), and only then imports check_take.py.

Witnesses follow the registry pattern of the earlier gap4 lanes: check_take.py with one exact anchor edit, compiled in
memory as its own module (never written to disk). A kill counts only when the bound check is green on the real
module first and then returns at least one line with its own prefix and no ERROR line.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import agent_adapter as aa  # noqa: E402
import harness_bookkeeping as hb  # noqa: E402
import prereg  # noqa: E402
import routing  # noqa: E402
from graders import labels4  # noqa: E402

ct = None               # imported in setUpModule, after the guard and the prereg patch
SCRATCH: Path | None = None
_STACK = contextlib.ExitStack()

SID = "12345678-aaaa-bbbb-cccc-1234567890ab"
BYPASS = "bypassPermissions"
TREE_SHA = "a" * 40
MODEL = "synthetic-model"
PRE = {"leak_words": ["synthetic-leak-word"], "run_location": {}, "source_by_fixture_kind": {},
       "budgets": {"turn_timeout_s": 600}, "system_under_test": {"gars_tree_sha": TREE_SHA},
       "driver_constants": {"permission_mode": BYPASS,
                            "permission_mode_by_arm": {"A": BYPASS, "C": BYPASS, "O": "synthetic-mode-o"}}}
HALF = {"operator_script": [{"n": 1, "line": "The half's own line for {project}."}], "probe_operator_turn": 9,
        "fixture": {}}
TASK = {"id": "synthetic-task", "positive": HALF, "control": copy.deepcopy(HALF)}
WORDING = [{"n": 1, "line": "The wording's own line for {project}."}]
EMAIL = "synthetic.account@example.invalid"


class GuardTripped(Exception):
    pass


def _trip(name):
    def trip(*a, **kw):
        raise GuardTripped(f"process guard: {name} refused")
    return trip


def setUpModule():
    global ct, SCRATCH
    # Wave 6 merge (binding W6M1, tests/test_wave6_bindings.py): check_take.py puts evals/ on sys.path when
    # imported; registered first, so the stack's close puts sys.path back, in place, last.
    _STACK.callback(sys.path.__setitem__, slice(None), list(sys.path))
    SCRATCH = Path(_STACK.enter_context(tempfile.TemporaryDirectory(prefix="w6h-ct-"))).resolve()
    for name in ("run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
        _STACK.enter_context(mock.patch.object(subprocess, name, _trip(f"subprocess.{name}")))
    for name in ("system", "popen", "kill", "killpg", "posix_spawn", "posix_spawnp", "fork", "forkpty"):
        if hasattr(os, name):
            _STACK.enter_context(mock.patch.object(os, name, _trip(f"os.{name}")))
    _STACK.enter_context(mock.patch.object(prereg, "load", lambda: copy.deepcopy(PRE)))
    _STACK.enter_context(mock.patch.object(prereg, "task", lambda task_id: copy.deepcopy(TASK)))
    import check_take as imported
    ct = imported
    (SCRATCH / "home").mkdir()
    _STACK.enter_context(mock.patch.object(ct, "CHECK_HOME", SCRATCH / "home"))


def tearDownModule():
    _STACK.close()


# ------------------------------------------------------------------------------------------------ synthetic records
def transcript(*, line=None, extra=(), mode=None) -> Path:
    project = "run-" + SID.replace("-", "")[:8]
    text = (line or WORDING[0]["line"]).replace("{project}", project)
    recs = [{"type": "user", "sessionId": SID, "message": {"role": "user", "content": text}},
            {"type": "assistant", "sessionId": SID, "message": {"role": "assistant",
                                                                "content": [{"type": "text", "text": "done"}]}}]
    if mode is not None:
        for r in recs:
            if r["type"] == "user":
                r["permissionMode"] = mode
    recs += list(extra)
    folder = Path(tempfile.mkdtemp(dir=SCRATCH))
    p = folder / "transcript.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return p


def tool_use(text: str) -> dict:
    return {"type": "assistant", "sessionId": SID, "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Read", "input": {"file_path": text}}]}}


def email_context() -> dict:
    return {"type": "attachment", "sessionId": SID, "attachment": {"type": "session_context",
                                                                   "context": {"userEmail": EMAIL}}}


def quiet(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **kw)


def ledger(arm, mode):
    led = {"budget_s": 600, "permission_mode": mode, "gars_tree_sha": TREE_SHA}
    if arm is not None:
        led["arm"] = arm
    return led


def test_table() -> dict:
    t = copy.deepcopy(routing.load_table())
    t["pin_profiles"] = {hb.CLAUDE_CODE: {MODEL: {"permission_mode": BYPASS, "version": "0.0.1"}}}
    t["pin_profiles_status"] = "RULED (TEST-ONLY): one injected profile"
    t["spend_cap_markers_status"] = "RULED (TEST-ONLY): the spend-cap list opened for the tests"
    return t


def records(reasons, *, first_turn: bool) -> dict:
    pin = {"model": MODEL, "permission_mode": BYPASS, "version": "0.0.1", "harness": hb.CLAUDE_CODE}
    turn = aa.TurnResult(exit_code=0, text="(synthetic)", stream_path=None, end_reason=labels4.END_TURN,
                         init={k: pin[k] for k in aa.INIT_FIELDS}, api_errors=[],
                         counters={"oom_kill_delta": 0, "pids_max_delta": 0}, started_at=1.0, ended_at=2.0,
                         agent_output=first_turn)
    box = {"preflight_ok": True, "container_started": True, "container_exited": False,
           "sidecar": {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False},
           "unexplained_operator_diffs": 0, "checker_reasons": list(reasons), "quiescence_kill": False,
           "outside_reach_events": 0, "finalize_abort": False, "committed": False, "unreadable_consequential": [],
           "quiescence_cap_survivors": 0}
    return aa.harness_records([turn], pin=pin, box=box)


def dsg(mod):
    """S6b (R4C-7): check4 reads a design view; S6's synthetic design as one, built from `mod`'s own Design so a
    witness module's isinstance check holds (the synthetic halves, PRE, claude-code, no wording script bound)."""
    return mod.Design(task_id="synthetic-task", spec=copy.deepcopy(TASK), pre=copy.deepcopy(PRE), harness="claude-code",
                      half="positive", script=copy.deepcopy(WORDING),   # W6I-R1-2: a whole view
                      run_tree="/work/run")   # W7B (Q-w6i-5): check4 refuses a view naming no run tree; these
                                              # synthetic sessions record no working directory to cross-check


def has(problems, rid) -> bool:
    return any(p.startswith(f"[{rid}] ") for p in problems)


def guarded(prefix):
    def wrap(fn):
        def check(mod):
            try:
                return fn(mod, prefix)
            except Exception as e:  # noqa: BLE001
                return [f"ERROR {prefix}: {type(e).__name__}: {str(e)[:240]}"]
        check.__name__ = fn.__name__
        return check
    return wrap


# ------------------------------------------------------------------------------------------------ the bound checks
@guarded("K1-arm")
def k1_arm(mod, p):
    out = []
    pre = copy.deepcopy(PRE)
    pre["driver_constants"]["permission_mode_by_arm"]["C"] = "default"
    cases = {("A", BYPASS): False, ("C", BYPASS): True, ("C", "default"): False, ("G", BYPASS): True,
             (None, BYPASS): True, ("A", "default"): True}
    for (arm, mode), refused in cases.items():
        got = mod.constant_problems(ledger(arm, mode), pre)
        if has(got, "constant-binding") != refused:
            out.append(f"{p}: arm {arm!r} recording {mode!r}: constant-binding {'missing' if refused else 'raised'}")
    # W6H-R1-5: the ledger's arm must be the take's arm (the mode is read by the ledger's arm).
    for led_arm, refused in (("C", True), ("A", False), (None, True)):
        path = transcript()
        (path.parent / "driver-ledger.json").write_text(json.dumps({} if led_arm is None else {"arm": led_arm}))
        got = quiet(mod.check4, path, "synthetic-task", "positive", None, True, wording_script=WORDING, design=dsg(mod), arm="A")
        hit = any(q.startswith("[constant-binding] the driver ledger records arm") for q in got["problems"])
        if hit != refused:
            out.append(f"{p}: a ledger of arm {led_arm!r} checked as arm 'A': the arm binding "
                       f"{'missing' if refused else 'raised'}")
    return out


@guarded("K2-wording")
def k2_wording(mod, p):
    out = []
    path = transcript()
    got = quiet(mod.check, path, "synthetic-task", "positive", None, True, wording_script=WORDING)
    if has(got, "operator-lines"):
        out.append(f"{p}: the wording's own line was refused as off the script: "
                   f"{[g for g in got if g.startswith('[operator-lines]')]}")
    other = transcript(line=HALF["operator_script"][0]["line"])
    got = quiet(mod.check, other, "synthetic-task", "positive", None, True, wording_script=WORDING)
    if not has(got, "operator-lines"):
        out.append(f"{p}: a take that sent the half's line instead of its wording's passed the operator lines")
    for bad in (None, []):
        try:
            quiet(mod.check4, path, "synthetic-task", "positive", None, True, wording_script=bad, design=dsg(mod), arm="A")
            out.append(f"{p}: check4 accepted a take with no wording script ({bad!r})")
        except mod.CheckRefused:
            pass
    return out


@guarded("K3-events")
def k3_events(mod, p):
    out = []
    path = transcript(extra=[tool_use("evals/gap-study-3/prereg.json"),
                             tool_use(str(mod.CHECKOUT_REPO) + "/README.md"), email_context()])
    raw = quiet(mod.check, path, "synthetic-task", "positive", None, True, wording_script=WORDING)
    ids = mod.event_ids()
    if not all(has(raw, eid) for eid in ids):
        return [f"{p}: the synthetic transcript does not raise all three event reasons: {mod.reason_ids(raw)}"]
    got = quiet(mod.check4, path, "synthetic-task", "positive", None, True, wording_script=WORDING, design=dsg(mod), arm="A")
    leaked = [r for r in got["reasons"] if r in ids]
    if leaked:
        out.append(f"{p}: event ids reached the routable reasons: {leaked}")
    if got["reasons"] != mod.reason_ids(got["problems"]):
        out.append(f"{p}: the reasons are not the kept problems' ids")
    counts = got["events"]
    if counts.get("study-materials-reached") != 1 or counts.get("account-email") != 1 \
            or not counts.get("read-outside-the-checkout"):
        out.append(f"{p}: the events are not counted one per instance: {counts}")
    if got["outside_reach"] != sum(counts.values()):
        out.append(f"{p}: outside_reach {got['outside_reach']} is not the events' sum {sum(counts.values())}")
    clean = quiet(mod.check4, transcript(), "synthetic-task", "positive", None, True, wording_script=WORDING, design=dsg(mod),
                  arm="A")
    if clean["outside_reach"] != 0 or any(clean["events"].values()):
        out.append(f"{p}: a transcript with no reach counted events: {clean['events']}")
    return out


@guarded("K4-mode")
def k4_mode(mod, p):
    out = []
    table = test_table()
    if mod.recorded_mode_problems(transcript(mode=BYPASS), PRE, "A") != []:
        out.append(f"{p}: a take recording arm A's pinned bypass mode was refused")
    if routing.route(records([], first_turn=True), table)["route"] != labels4.GRADED:
        out.append(f"{p}: a clean take after its first turn did not grade")
    for mode in ("default", "plan"):
        got = mod.recorded_mode_problems(transcript(mode=mode), PRE, "A")
        if not has(got, "constant-binding"):
            out.append(f"{p}: a take recording {mode!r} under arm A carried no constant-binding")
            continue
        reasons = mod.reason_ids(got)
        after = routing.route(records(reasons, first_turn=True), table)["route"]
        before = routing.route(records(reasons, first_turn=False), table)["route"]
        if (before, after) != (labels4.REHEARSAL, labels4.HARNESS_ERROR):
            out.append(f"{p}: a take recording {mode!r} routed {before!r} before and {after!r} after the first "
                       f"turn")
    for why, path, arm in (("no recorded mode", transcript(), "A"),
                           ("an arm with no pin", transcript(mode=BYPASS), "G")):
        if not has(mod.recorded_mode_problems(path, PRE, arm), "constant-binding"):
            out.append(f"{p}: {why} passed the recorded-mode binding")
    mixed = transcript(mode=BYPASS, extra=[{"type": "user", "sessionId": SID, "permissionMode": "default",
                                            "message": {"role": "user", "content": "x"}}])
    if not has(mod.recorded_mode_problems(mixed, PRE, "A"), "constant-binding"):
        out.append(f"{p}: a session recording two modes passed")
    return out


# ------------------------------------------------------------------------------------------------ the tests
def need(case, *names):
    """A round-4 name missing from check_take.py is this test's failure (an assertion), never an error."""
    gone = [n for n in names if not hasattr(ct, n)]
    case.assertEqual(gone, [], f"check_take.py has no {', '.join(gone)}")


class TestGuardArmed(unittest.TestCase):
    def test_a_process_start_trips(self):
        with self.assertRaises(GuardTripped):
            subprocess.run(["true"])
        with self.assertRaises(GuardTripped):
            os.system("true")


class TestRound4Edits(unittest.TestCase):
    def test_k1_the_mode_is_keyed_by_arm(self):
        self.assertEqual(k1_arm(ct), [])

    def test_k2_check_reads_the_wordings_script(self):
        self.assertEqual(k2_wording(ct), [])

    def test_k3_three_reasons_become_counted_events(self):
        self.assertEqual(k3_events(ct), [])

    def test_k4_the_recorded_mode_binds_and_routes(self):
        self.assertEqual(k4_mode(ct), [])

    def test_a_checker_and_reader_that_disagree_refuse(self):
        need(self, "check4", "event_ids", "CheckRefused")
        path = transcript(extra=[tool_use("evals/gap-study-3/prereg.json")])
        zero = {eid: 0 for eid in ct.event_ids()}
        with mock.patch.object(ct, "event_counts", lambda p: dict(zero)):
            with self.assertRaises(ct.CheckRefused):
                quiet(ct.check4, path, "synthetic-task", "positive", None, True, wording_script=WORDING, design=dsg(ct), arm="A")
        with mock.patch.object(ct, "check", lambda *a, **k: ["a refusal with no id"]):
            with self.assertRaises(ct.CheckRefused):
                ct.check4(transcript(), "synthetic-task", "positive", None, True, wording_script=WORDING, design=dsg(ct), arm="A")

    def test_the_event_ids_are_routings_never_retyped(self):
        need(self, "event_ids", "event_counts")
        self.assertEqual(set(ct.event_ids()), set(routing.load_table()["checker_reasons_become_events"]["ids"]))
        self.assertEqual(set(ct.event_ids()), set(ct.event_counts(transcript())))

    def test_an_unpinned_mode_equals_nothing(self):
        need(self, "mode_for_arm", "_Unpinned")
        u = ct.mode_for_arm(PRE, "Z")
        for v in (None, "", BYPASS, u):
            self.assertFalse(u == v)
            self.assertTrue(u != v)
        self.assertEqual(ct.mode_for_arm(PRE, "A"), BYPASS)
        self.assertIsInstance(ct.mode_for_arm({"driver_constants": {"permission_mode_by_arm": {"A": ""}}}, "A"),
                              ct._Unpinned)

    def test_only_three_lines_above_the_round4_section_changed(self):
        src = Path(ct.__file__).read_text(encoding="utf-8").splitlines()
        self.assertIn("mode_for_arm(pre, ledger.get(\"arm\"))", src[901])
        self.assertIn("wording_script: list | None = None", src[1566])
        self.assertIn("half[\"operator_script\"] if wording_script is None else wording_script", src[1603])
        for n, rid in ((714, "account-email"), (1682, "study-materials-reached"), (1691, "read-outside-the-checkout")):
            self.assertIn(f"[{rid}]", src[n - 1], n)


# ------------------------------------------------------------------------------------------------ the witnesses
class WitnessNotPerformed(AssertionError):
    pass


def witness_module(edits: tuple) -> types.ModuleType:
    """check_take.py with `edits` applied, compiled in memory as its own module (never written to disk)."""
    with open(ct.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    name = "check_take_w6h_witness"
    mod = types.ModuleType(name)
    mod.__file__ = ct.__file__
    sys.modules[name] = mod
    try:
        exec(compile(src, ct.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    mod.CHECK_HOME = ct.CHECK_HOME
    return mod


WITNESSES = {
    "one-mode-constant": ((("    want_mode = mode_for_arm(pre, ledger.get(\"arm\"))",
                            "    want_mode = pre[\"driver_constants\"][\"permission_mode\"]"),), k1_arm, "K1-arm"),
    "ledger-arm-unbound": ((("    if led is not None and led.get(\"arm\") != arm:\n", "    if False:\n"),),
                           k1_arm, "K1-arm"),
    "the-halfs-script": ((("    script = half[\"operator_script\"] if wording_script is None else wording_script",
                           "    script = half[\"operator_script\"]"),), k2_wording, "K2-wording"),
    # Two layers, both off: the lift, and the agreement check that refuses a reason its reader did not count (either
    # alone fails closed; neither is credited alone).
    "nothing-lifted": ((("        if rid[0] in ids:\n            lifted.add(rid[0])",
                         "        if False:\n            lifted.add(rid[0])"),
                        ("        if (eid in lifted) != (counts[eid] > 0):\n", "        if False:\n")),
                       k3_events, "K3-events"),
    "recorded-mode-unchecked": ((("    if len(got) == 1 and next(iter(got)) == want:\n",
                                  "    if True:\n"),), k4_mode, "K4-mode"),
}
WITNESS_LOG: list = []


class TestWitnesses(unittest.TestCase):
    def kill(self, name):
        edits, check, prefix = WITNESSES[name]
        self.assertEqual(check(ct), [], f"{name}: the bound check is not green on check_take.py")
        got = check(witness_module(edits))
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(prefix + ":")]
        collateral = [x for x in got if x not in own and x not in errors]
        line = (f"WITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
                f"{len(collateral)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ", file=sys.stderr, flush=True)
        WITNESS_LOG.append(line)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_one_mode_constant(self):
        self.kill("one-mode-constant")

    def test_witness_ledger_arm_unbound(self):
        self.kill("ledger-arm-unbound")

    def test_witness_the_halfs_script(self):
        self.kill("the-halfs-script")

    def test_witness_nothing_lifted(self):
        self.kill("nothing-lifted")

    def test_witness_recorded_mode_unchecked(self):
        self.kill("recorded-mode-unchecked")

    def test_the_witnesses_are_named_and_each_bound_to_its_own_check(self):
        self.assertEqual(sorted(WITNESSES), sorted(["one-mode-constant", "the-halfs-script", "nothing-lifted",
                                                    "recorded-mode-unchecked", "ledger-arm-unbound"]))
        # Five witnesses over four bound checks: W6H-R1-5's is bound to K1.
        self.assertEqual(len({w[1].__name__ for w in WITNESSES.values()}), 4)
        self.assertEqual(len({w[2] for w in WITNESSES.values()}), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
