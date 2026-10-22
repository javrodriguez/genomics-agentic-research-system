#!/usr/bin/env python3
"""Lane w6i (Gap Study round 4, slice S6b, Q2): mode_binding.py holds each take's recorded permission mode to the
take's routing pin, keyed by the harness and the model it ran, on synthetic take folders only.

  M1-pin    takes recording their (harness, model) pin's mode pass; a take recording another mode fails; one model
            id pinned differently under two harnesses is held to each harness's own pin. Witness: model-only (the
            expectation looked up by the model alone, round 3's key).
  M2-pending a PENDING (or absent) pin is never an expectation: the take is a problem naming it and --check exits 1;
            with no take committed the empty gate still says nothing was graded (exit 0).

Lane w7b (wave 7 P2, Q-w6i-1; this module moved from lane w6i to lane w7b under ruling W7B-gap4-1):
  M3-folder the takes are read from mode_binding.TAKES_DIR, the one name drive.py's production take folder reads
            (take_folder_in, bound in test_walk_wiring.py), laid out <TAKES_DIR>/<slot>/<k>; the harness is read from
            the driver ledger's own shape (driver-ledger.json's agent.harness), which every synthetic ledger here now
            carries. Witness: top-level-harness (round 3's top-level key, which the round-4 driver never writes).

Lane freeze-gates-fix (glitch-f1's ruling (2), Wed 21 Oct 2026, under Javier's standing delegation):
  M4-vendor a Codex walk is held to its pin by the CLI-written rollout (every turn_context's approval_policy and
            sandbox_policy.type, the ledger's last native snapshot, hash-checked), a Gemini walk by its launch argv,
            named input-side in the output; neither reads `unrecorded`, and a missing, altered or contradicting record
            is a problem, never a pass. Witnesses: approval-only (the sandbox policy unread, so `never` alone passes),
            argv-unread (the Gemini reading returns the pin without reading a journal).

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
        (folder / "driver-ledger.json").write_text(json.dumps({"agent": {"harness": harness, "version": "0.0.1"},
                                                               "model_requested": model,
                                                               "task": "synthetic-task", "half": "trap"}))
    return base


VTABLE = {"pin_profiles": {"codex": {"m-o": {"permission_mode": "bypass", "version": "0.0.1"}},
                           "gemini": {"m-g": {"permission_mode": "yolo", "version": "0.0.1"}}}}


def _rollout(pairs, settings=("never",), turns=None):
    """A synthetic Codex rollout: one task_started and one turn_context per (approval_policy, sandbox type) pair."""
    import hashlib
    recs = [{"type": "session_meta", "payload": {"id": "t-1"}}]
    for i, (approval, sandbox) in enumerate(pairs):
        recs.append({"type": "event_msg", "payload": {"type": "task_started", "turn_id": f"u{i}"}})
        recs.append({"type": "turn_context", "payload": {"turn_id": f"u{i}", "approval_policy": approval,
                                                          "sandbox_policy": {"type": sandbox}}})
    for _ in range((len(pairs) if turns is None else turns) - len(pairs)):
        recs.append({"type": "event_msg", "payload": {"type": "task_started", "turn_id": "extra"}})
    for a in settings:
        recs.append({"type": "event_msg", "payload": {"type": "thread_settings_applied",
                                                      "thread_settings": {"approval_policy": a}}})
    raw = "".join(json.dumps(r) + "\n" for r in recs).encode()
    return raw, hashlib.sha256(raw).hexdigest()


def vendor_walks(walks: list) -> Path:
    """A synthetic study folder of rehearsals/<walk>/ vendor walks. Each walk is (harness, model, spec): a Codex spec
    is {pairs, settings?, turns?, sha?, snapshot?}; a Gemini spec is {argvs: [argv per turn], journals?}."""
    base = Path(tempfile.mkdtemp(dir=SCRATCH))
    for i, (harness, model, spec) in enumerate(walks, 1):
        folder = base / "rehearsals" / f"w-v{i:02d}"     # zero-padded: rows() reads them sorted
        folder.mkdir(parents=True)
        (folder / "transcript.jsonl").write_text(json.dumps({"type": "turn", "text": "a synthetic line"}) + "\n")
        ledger = {"agent": {"harness": harness, "version": "0.0.1"}, "model_requested": model,
                  "permission_mode": "unrecorded", "permission_mode_recorded": "unrecorded"}
        if harness == "codex":
            raw, sha = _rollout(spec["pairs"], spec.get("settings", ("never",)), spec.get("turns"))
            if spec.get("snapshot", True):
                (folder / "session").mkdir()
                (folder / "session" / "native-turn-1.jsonl").write_bytes(raw)
            ledger["native_snapshots"] = [{"file": "native-turn-1.jsonl", "sha256": spec.get("sha", sha)}]
        else:
            for k, argv in enumerate(spec["argvs"], 1):
                (folder / f"turn-{k}.jsonl").write_text("{}\n")
                if k in spec.get("journals", range(1, len(spec["argvs"]) + 1)):
                    (folder / f"turn-{k}.jsonl.launch.json").write_text(json.dumps(
                        {"schema": 1, "harness": "gemini", "argv": argv, "cwd": "/tmp/run-synthetic"}))
        (folder / "driver-ledger.json").write_text(json.dumps(ledger))
    return base


GOOD_ARGV = ["gemini", "-p", "a synthetic line", "-o", "stream-json", "-m", "m-g", "--approval-mode", "yolo"]


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


@guarded("M3-folder")
def m3_folder(mod, p):
    """W7B (Q-w6i-1): one folder name, the driver ledger's own harness key."""
    out = []
    if getattr(mod, "TAKES_DIR", None) != "takes" or tuple(getattr(mod, "TAKE_ROOTS", ())) != ("takes",):
        out.append(f"{p}: mode_binding names no TAKES_DIR read by TAKE_ROOTS: "
                   f"{getattr(mod, 'TAKES_DIR', None)!r}, {getattr(mod, 'TAKE_ROOTS', None)!r}")
    base = base_with([("claude-code", "m-a", BYPASS)])
    found = mod.attempts(base=base)
    if [f.relative_to(base).as_posix() for f in found] != ["takes/s1/1/transcript.jsonl"]:
        out.append(f"{p}: the takes read are {found}")
    got = mod.rows(base=base, table=TABLE)
    if [r["harness"] for r in got] != ["claude-code"] or got[0]["problems"]:
        out.append(f"{p}: a driver ledger's agent.harness was read as {[r['harness'] for r in got]}: "
                   f"{[r['problems'] for r in got]}")
    return out


@guarded("M4-vendor")
def m4_vendor(mod, p):
    """Lane freeze-gates-fix: the vendor walks' own records, and the source named beside each reading."""
    out = []
    good = ("never", "danger-full-access")
    cases = {
        "codex recorded bypass": (("codex", "m-o", {"pairs": [good, good], "settings": ("never", "never")}), False),
        "codex approval never, sandbox read-only": (("codex", "m-o", {"pairs": [("never", "read-only")]}), True),
        "codex one turn of two in another mode": (("codex", "m-o", {"pairs": [good, ("on-request",
                                                                                     "danger-full-access")]}), True),
        "codex thread settings disagree": (("codex", "m-o", {"pairs": [good], "settings": ("on-request",)}), True),
        "codex a turn without its turn_context": (("codex", "m-o", {"pairs": [good], "turns": 2}), True),
        "codex snapshot hash differs": (("codex", "m-o", {"pairs": [good], "sha": "0" * 64}), True),
        "codex snapshot missing": (("codex", "m-o", {"pairs": [good], "snapshot": False}), True),
        "gemini argv submits yolo": (("gemini", "m-g", {"argvs": [GOOD_ARGV, GOOD_ARGV]}), False),
        "gemini argv without the flag": (("gemini", "m-g", {"argvs": [GOOD_ARGV[:-2]]}), True),
        "gemini argv with a second approval flag": (("gemini", "m-g", {"argvs": [GOOD_ARGV + ["--yolo"]]}), True),
        "gemini a turn's journal missing": (("gemini", "m-g", {"argvs": [GOOD_ARGV, GOOD_ARGV], "journals": (1,)}),
                                            True),
    }
    base = vendor_walks([w for w, _ in cases.values()])
    got = mod.rows(walks=True, base=base, table=VTABLE)
    if len(got) != len(cases):
        return [f"{p}: {len(got)} walks read, {len(cases)} committed"]
    for (what, (walk, refused)), r in zip(cases.items(), got):
        if bool(r["problems"]) != refused:
            out.append(f"{p}: {what}: {'passed' if refused else 'failed'} ({r['problems']})")
        if r.get("recorded") == "unrecorded":
            out.append(f"{p}: {what}: read as 'unrecorded', the Claude Code field's absence")
        want_source = {"codex": "codex rollout", "gemini": "input side"}[walk[0]]
        if want_source not in str(r.get("source")):
            out.append(f"{p}: {what}: the reading's source is {r.get('source')!r}")
    rc, text = run_main(mod, vendor_walks([cases["codex recorded bypass"][0], cases["gemini argv submits yolo"][0]]),
                        VTABLE, "--walks", "--check")
    if rc != 0 or "input-side" not in text or "1 by codex rollout" not in text:
        out.append(f"{p}: --check over one good walk per vendor arm gave exit {rc} and did not name the input-side "
                   f"reading: {text[-400:]!r}")
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

    def test_m3_the_take_folder_and_the_ledgers_harness(self):
        self.assertEqual(m3_folder(mb), [])

    def test_m4_the_vendor_walks_own_records(self):
        self.assertEqual(m4_vendor(mb), [])

    def test_the_codex_map_is_the_adapters_pin(self):
        import codex_adapter
        self.assertEqual(set(mb.CODEX_MODE_RECORD), set(codex_adapter.MODE_FLAGS), "M4-vendor")
        self.assertEqual(mb.CODEX_MODE_RECORD["bypass"], ("never", "danger-full-access"), "M4-vendor")

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
    path = list(sys.path)
    try:
        exec(compile(src, mb.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
        sys.path[:] = path             # lane freeze-gates-fix: the module's own top-level sys.path.insert, undone
    return mod


WITNESSES = {
    "model-only": ((("    want = exp.get((harness, model))",
                     "    want = {m: v for (h, m), v in exp.items()}.get(model)"),), m1_pin, "M1-pin"),
    # W7B (Q-w6i-1)
    "top-level-harness": ((("    harness = ledger_harness(ledger)           # W7B: the driver ledger's own shape, agent.harness",
                            "    harness = ledger.get(\"harness\") or \"?\""),), m1_pin, "M1-pin"),
    # lane freeze-gates-fix
    "approval-only": ((("    names = [pin for pin, pair in CODEX_MODE_RECORD.items() if pair == (approval, sandbox)]",
                        "    names = [pin for pin, pair in CODEX_MODE_RECORD.items() if pair[0] == approval]"),),
                      m4_vendor, "M4-vendor"),
    "argv-unread": ((("        value, problems = argv_mode(folder, harness)",
                      "        value, problems = \"yolo\", []"),), m4_vendor, "M4-vendor"),
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

    def test_witness_top_level_harness(self):
        self.kill("top-level-harness")

    def test_witness_approval_only(self):
        self.kill("approval-only")

    def test_witness_argv_unread(self):
        self.kill("argv-unread")

    def test_the_witnesses_are_named(self):
        self.assertEqual(sorted(WITNESSES), ["approval-only", "argv-unread", "model-only", "top-level-harness"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
