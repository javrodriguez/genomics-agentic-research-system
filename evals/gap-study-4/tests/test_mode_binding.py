#!/usr/bin/env python3
"""Lane w6i (Gap Study round 4, slice S6b, Q2): mode_binding.py holds each take's recorded permission mode to the
take's routing pin, keyed by the harness and the model it ran, on synthetic take folders only.

  M1-pin    takes recording their (harness, model) pin's mode pass; a take recording another mode fails; one model
            id pinned differently under two harnesses is held to each harness's own pin. Witness: model-only (the
            expectation looked up by the model alone, round 3's key).
  M2-pending a PENDING (or absent) pin is never an expectation: the take is a problem naming it and --check exits 1;
            with no take committed the empty gate still says nothing was graded (exit 0).

Fakes and synthetic strings only: no model, vendor, network, credential or holdout. setUpModule arms a process guard
that refuses every process start before mode_binding.py is imported.
"""

from __future__ import annotations

import contextlib
import inspect
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

import routing  # noqa: E402

mb = None
SCRATCH: Path | None = None
_STACK = contextlib.ExitStack()
BYPASS, OTHER = "bypassPermissions", "synthetic-other-mode"
TABLE = {"pin_profiles": {"claude-code": {"m-a": {"permission_mode": BYPASS, "version": "0.0.1"},
                                          "m-shared": {"permission_mode": BYPASS, "version": "0.0.1"}},
                          "synthetic-harness": {"m-shared": {"permission_mode": OTHER, "version": "0.0.1"}}}}


class GuardTripped(Exception):
    pass


def _trip(name):
    def trip(*a, **kw):
        raise GuardTripped(f"process guard: {name} refused")
    return trip


def setUpModule():
    global mb, SCRATCH
    SCRATCH = Path(_STACK.enter_context(tempfile.TemporaryDirectory(prefix="w6i-mb-"))).resolve()
    for name in ("run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
        _STACK.enter_context(mock.patch.object(subprocess, name, _trip(f"subprocess.{name}")))
    for name in ("system", "popen", "kill", "killpg", "posix_spawn", "posix_spawnp", "fork", "forkpty"):
        if hasattr(os, name):
            _STACK.enter_context(mock.patch.object(os, name, _trip(f"os.{name}")))
    import mode_binding as imported
    mb = imported


def tearDownModule():
    _STACK.close()


def base_with(takes: list) -> Path:
    """A synthetic study folder: takes/<slot>/<n>/transcript.jsonl and driver-ledger.json for each (harness, model,
    recorded mode)."""
    base = Path(tempfile.mkdtemp(dir=SCRATCH))
    for i, (harness, model, mode) in enumerate(takes, 1):
        folder = base / "takes" / f"s{i}" / "1"
        folder.mkdir(parents=True)
        recs = [{"type": "user", "permissionMode": mode, "message": {"role": "user", "content": "a synthetic line"}},
                {"type": "assistant", "message": {"role": "assistant", "content": "a synthetic reply"}}]
        (folder / "transcript.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
        (folder / "driver-ledger.json").write_text(json.dumps({"harness": harness, "model_requested": model,
                                                               "task": "synthetic-task", "half": "trap"}))
    return base


def run_main(mod, base, table, *argv):
    out = io.StringIO()
    with mock.patch.object(mod, "HERE", base), mock.patch.object(routing, "load_table", lambda: table), \
            mock.patch.object(sys, "argv", ["mode_binding.py", *argv]), contextlib.redirect_stdout(out):
        rc = mod.main()
    return rc, out.getvalue()


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


@guarded("M1-pin")
def m1_pin(mod, p):
    out = []
    cases = {("claude-code", "m-a", BYPASS): False, ("claude-code", "m-a", "default"): True,
             ("claude-code", "m-shared", BYPASS): False, ("synthetic-harness", "m-shared", OTHER): False,
             ("synthetic-harness", "m-shared", BYPASS): True, ("claude-code", "m-unpinned", BYPASS): True}
    got = mod.rows(base=base_with(list(cases)), table=TABLE)
    if len(got) != len(cases):
        return [f"{p}: {len(got)} takes read, {len(cases)} committed"]
    for (key, refused), r in zip(cases.items(), got):
        if bool(r["problems"]) != refused:
            out.append(f"{p}: {key}: {'passed' if refused else 'failed'} ({r['problems']})")
    return out


@guarded("M2-pending")
def m2_pending(mod, p):
    out = []
    table = {"pin_profiles": {"claude-code": {"m-a": {"permission_mode": "PENDING"}, "m-b": {}}}}
    for model in ("m-a", "m-b"):
        rc, text = run_main(mod, base_with([("claude-code", model, BYPASS)]), table, "--check")
        if rc != 1 or "PENDING" not in text:
            out.append(f"{p}: a take under {model}'s unmeasured pin gave exit {rc}: {text[-160:]!r}")
    rc, text = run_main(mod, base_with([]), table, "--check")
    if rc != 0 or "having graded 0" not in text:
        out.append(f"{p}: with no take committed the gate did not say it graded nothing: exit {rc}, {text!r}")
    rc, text = run_main(mod, base_with([("claude-code", "m-a", BYPASS)]), TABLE, "--check")
    if rc != 0:
        out.append(f"{p}: a take under its measured pin failed --check: {text[-160:]!r}")
    return out


class TestGuardArmed(unittest.TestCase):
    def test_a_process_start_trips(self):
        with self.assertRaises(GuardTripped):
            subprocess.run(["true"])


class TestModeBinding(unittest.TestCase):
    def test_m1_the_pin_is_keyed_by_harness_and_model(self):
        self.assertEqual(m1_pin(mb), [])

    def test_m2_a_pending_pin_is_never_an_expectation(self):
        self.assertEqual(m2_pending(mb), [])

    def test_the_expectation_comes_from_routings_pin_profiles(self):
        self.assertIn("table", inspect.signature(mb.expected).parameters, "expected() does not read a routing table")
        self.assertEqual(mb.expected(TABLE), {("claude-code", "m-a"): BYPASS, ("claude-code", "m-shared"): BYPASS,
                                              ("synthetic-harness", "m-shared"): OTHER})
        live = routing.load_table()
        self.assertEqual(set(mb.expected(live)), {(h, m) for h, ms in (live.get("pin_profiles") or {}).items()
                                                  for m in ms})


class WitnessNotPerformed(AssertionError):
    pass


def witness_module(edits: tuple) -> types.ModuleType:
    with open(mb.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    name = "mode_binding_w6i_witness"
    mod = types.ModuleType(name)
    mod.__file__ = mb.__file__
    sys.modules[name] = mod
    try:
        exec(compile(src, mb.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    return mod


WITNESSES = {
    "model-only": ((("    want = exp.get((harness, model))",
                     "    want = {m: v for (h, m), v in exp.items()}.get(model)"),), m1_pin, "M1-pin"),
}


class TestWitnesses(unittest.TestCase):
    def kill(self, name):
        edits, check, prefix = WITNESSES[name]
        self.assertEqual(check(mb), [], f"{name}: the bound check is not green on mode_binding.py")
        got = check(witness_module(edits))
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(prefix + ":")]
        collateral = [x for x in got if x not in own and x not in errors]
        print(f"\nWITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
              f"{len(collateral)} collateral, {len(errors)} errors)", end=" ", file=sys.stderr, flush=True)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_model_only(self):
        self.kill("model-only")

    def test_the_witnesses_are_named(self):
        self.assertEqual(sorted(WITNESSES), ["model-only"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
