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
            S10 (the lane review's m1 and m3): the Codex rollout's turns equal the walk's turn streams, with a
            two-snapshot walk; the Gemini journals are read by gemini_adapter.submitted_mode, so a journal that is not
            the registered invocation, names another harness or is a link is a problem (the adapter's own refusals, so
            no local copy of them is kept to mutate). Witness: first-snapshot.
            S11 (the closure check): a journal whose cwd or container differs from launch.json's take record, a
            ledger model other than the argv's, and a linked turn stream are each a problem. Witnesses: the
            reviewer's C5, C6, C10 and C11 verbatim (run-tree-from-journal, container-from-journal, model-fixed,
            linked-stream-counted).

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
                           "gemini": {"m-g": {"permission_mode": "yolo", "version": "0.0.1"},
                                      "m-g2": {"permission_mode": "yolo", "version": "0.0.1"}}}}


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


SESSION = "1a2b3c4d-0000-4000-8000-00000000abcd"
TAKE_ID, RUN_TREE = "c" * 64, "/tmp/run-synthetic"


def gemini_argv(k, model="m-g"):
    import gemini_adapter
    return gemini_adapter.argv(f"sent {k}", model=model, mode="yolo", session_id=SESSION, first=k == 1)


def stream_file(folder: Path, k: int, linked: bool) -> Path:
    """turn-k.jsonl, or a link to a file holding the same bytes."""
    stream = folder / f"turn-{k}.jsonl"
    if linked:
        (folder / f"real-turn-{k}.jsonl").write_text("{}\n")
        stream.symlink_to(folder / f"real-turn-{k}.jsonl")
    else:
        stream.write_text("{}\n")
    return stream


def vendor_walks(walks: list) -> Path:
    """A synthetic study folder of rehearsals/<walk>/ vendor walks. Each walk is (harness, model, spec).
    Codex: {snapshots: [pairs per retained snapshot], settings?, turns?, sha?, snapshot?, streams?}; the walk holds
    `streams` turn streams (default: the last snapshot's turns). Gemini: {turns, argv?: {k: argv}, journals?,
    harness_field?, symlink?, cwd?, container?, argv_model?}, and either arm linked_stream?: launch.json (take_id,
    the take-inspect working folder), one harness-turn envelope and one
    journal per turn, each argv the adapter's own invocation unless `argv` replaces it."""
    base = Path(tempfile.mkdtemp(dir=SCRATCH))
    for i, (harness, model, spec) in enumerate(walks, 1):
        folder = base / "rehearsals" / f"w-v{i:02d}"     # zero-padded: rows() reads them sorted
        folder.mkdir(parents=True)
        ledger = {"agent": {"harness": harness, "version": "0.0.1"}, "model_requested": model,
                  "permission_mode": "unrecorded", "permission_mode_recorded": "unrecorded"}
        envs = []
        if harness == "codex":
            snaps = spec.get("snapshots") or [spec["pairs"]]
            ledger["native_snapshots"] = []
            if spec.get("snapshot", True):
                (folder / "session").mkdir()
            for n, pairs in enumerate(snaps, 1):
                last_turns = spec.get("turns") if n == len(snaps) else None
                raw, sha = _rollout(pairs, spec.get("settings", ("never",)), last_turns)
                if spec.get("snapshot", True):
                    (folder / "session" / f"native-turn-{n}.jsonl").write_bytes(raw)
                ledger["native_snapshots"].append({"file": f"native-turn-{n}.jsonl", "sha256": spec.get("sha", sha)})
            streams = spec.get("streams", spec.get("turns") or len(snaps[-1]))
            for k in range(1, streams + 1):
                stream_file(folder, k, k == spec.get("linked_stream"))
        else:
            (folder / "launch.json").write_text(json.dumps({"take_id": TAKE_ID, "steps": [
                {"step": "take-inspect", "inspect": {"Config": {"WorkingDir": RUN_TREE}}}]}))
            for k in range(1, spec["turns"] + 1):
                stream = stream_file(folder, k, k == spec.get("linked_stream"))
                envs.append({"type": "harness-turn", "n": k, "sent": f"sent {k}", "vendor_session_id": SESSION})
                if k not in spec.get("journals", range(1, spec["turns"] + 1)):
                    continue
                doc = {"schema": 1, "harness": spec.get("harness_field", "gemini"),
                       "container_id": spec.get("container", TAKE_ID),
                       "argv": spec.get("argv", {}).get(k) or gemini_argv(k, spec.get("argv_model", model)),
                       "cwd": spec.get("cwd", RUN_TREE),
                       "stream": str(stream), "started_at": 1.0}
                journal = folder / f"turn-{k}.jsonl.launch.json"
                if k == spec.get("symlink"):
                    (folder / f"real-{k}.json").write_text(json.dumps(doc))
                    journal.symlink_to(folder / f"real-{k}.json")
                else:
                    journal.write_text(json.dumps(doc))
        (folder / "transcript.jsonl").write_text("".join(json.dumps(e) + "\n" for e in envs)
                                                 or json.dumps({"type": "turn", "text": "a synthetic line"}) + "\n")
        (folder / "driver-ledger.json").write_text(json.dumps(ledger))
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
    no_flag = [a for a in gemini_argv(1) if a not in ("--approval-mode", "yolo")]
    cases = {
        "codex recorded bypass": (("codex", "m-o", {"pairs": [good, good], "settings": ("never", "never")}), False),
        "codex two snapshots, the last covering both turns": (("codex", "m-o", {"snapshots": [[good], [good, good]]}),
                                                             False),
        "codex the last snapshot short of the walk's turns": (("codex", "m-o", {"snapshots": [[good], [good, good]],
                                                                                "streams": 3}), True),
        "codex approval never, sandbox read-only": (("codex", "m-o", {"pairs": [("never", "read-only")]}), True),
        "codex one turn of two in another mode": (("codex", "m-o", {"pairs": [good, ("on-request",
                                                                                     "danger-full-access")]}), True),
        "codex thread settings disagree": (("codex", "m-o", {"pairs": [good], "settings": ("on-request",)}), True),
        "codex a turn without its turn_context": (("codex", "m-o", {"pairs": [good], "turns": 2}), True),
        "codex snapshot hash differs": (("codex", "m-o", {"pairs": [good], "sha": "0" * 64}), True),
        "codex snapshot missing": (("codex", "m-o", {"pairs": [good], "snapshot": False}), True),
        "gemini argv submits yolo": (("gemini", "m-g", {"turns": 2}), False),
        "gemini argv without the flag": (("gemini", "m-g", {"turns": 1, "argv": {1: no_flag}}), True),
        "gemini argv with a second approval flag": (("gemini", "m-g", {"turns": 1, "argv": {1: gemini_argv(1)
                                                                                         + ["--yolo"]}}), True),
        "gemini argv not the registered invocation": (("gemini", "m-g", {"turns": 1, "argv": {
            1: gemini_argv(1) + ["--include-directories", "/elsewhere"]}}), True),
        "gemini a turn's journal missing": (("gemini", "m-g", {"turns": 2, "journals": (1,)}), True),
        "gemini a journal naming another harness": (("gemini", "m-g", {"turns": 1, "harness_field": "codex"}), True),
        "gemini a symlinked journal": (("gemini", "m-g", {"turns": 2, "symlink": 2}), True),
        # S11 (closure C5, C6, C10, C11): the invocation is rebuilt from records other than the journal
        "gemini a journal cwd other than the take's working folder": (
            ("gemini", "m-g", {"turns": 1, "cwd": "/tmp/run-other"}), True),
        "gemini a journal container other than launch.json's take_id": (("gemini", "m-g", {"turns": 1,
                                                                                            "container": "d" * 64}),
                                                                         True),
        "gemini the ledger's model other than the argv's": (("gemini", "m-g2", {"turns": 1, "argv_model": "m-g"}),
                                                            True),
        "codex a linked turn stream": (("codex", "m-o", {"pairs": [good, good], "linked_stream": 2}), True),
        "gemini a linked turn stream": (("gemini", "m-g", {"turns": 2, "linked_stream": 2}), True),
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
    path, modules = list(sys.path), set(sys.modules)
    try:
        exec(compile(src, mb.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
        for added in set(sys.modules) - modules:    # lane freeze-gates-fix S14: an import the compile
            del sys.modules[added]                  # re-registered, undone
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
    "first-snapshot": ((("    last = snaps[-1] if", "    last = snaps[0] if"),), m4_vendor, "M4-vendor"),
    # S11: the lane review's closure mutants C5, C6, C10 and C11, verbatim
    "run-tree-from-journal": ((('"run_tree": run_tree,', '"run_tree": doc.get("cwd"),'),), m4_vendor, "M4-vendor"),
    "container-from-journal": ((('"container_id": take_id,', '"container_id": doc.get("container_id"),'),),
                               m4_vendor, "M4-vendor"),
    "model-fixed": ((('"model": ledger.get("model_requested"),', '"model": "m-g",'),), m4_vendor, "M4-vendor"),
    "linked-stream-counted": ((("if (m := _STREAM.fullmatch(p.name)) and not p.is_symlink() and p.is_file())",
                                "if (m := _STREAM.fullmatch(p.name)))"),), m4_vendor, "M4-vendor"),
    "argv-unread": ((("        value, problems = argv_mode(folder, ledger, pin)",
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

    def test_witness_first_snapshot(self):
        self.kill("first-snapshot")

    def test_witness_run_tree_from_journal(self):
        self.kill("run-tree-from-journal")

    def test_witness_container_from_journal(self):
        self.kill("container-from-journal")

    def test_witness_model_fixed(self):
        self.kill("model-fixed")

    def test_witness_linked_stream_counted(self):
        self.kill("linked-stream-counted")

    def test_the_witnesses_are_named(self):
        self.assertEqual(sorted(WITNESSES), ["approval-only", "argv-unread", "container-from-journal",
                                             "first-snapshot", "linked-stream-counted", "model-fixed", "model-only",
                                             "run-tree-from-journal", "top-level-harness"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
