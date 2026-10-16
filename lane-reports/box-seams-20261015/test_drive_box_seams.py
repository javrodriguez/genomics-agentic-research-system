#!/usr/bin/env python3
"""Drive-to-box seams (box lane, 15 Oct 2026, after CP6 walk w013 refused at launch on ce818d85 with "the ownership
road's operator_read is not operator_read(runtime, *, image, root_kind, root, rel_path, caller_env)").

PROPOSED for the harness lane's tests/ (drive.py is theirs): it is red on ce818d85 and green once drive.py takes the
box's reviewed O-3 signature. Until then it lives here, outside the battery. Run it against a tree:
    python3 -B test_drive_box_seams.py <evals/gap-study-4 folder>

  S1  drive's own TakeDriver._operator_read reaches the REAL box/ownership.operator_read (fake runtime) and returns
      the box's None for an absent file, never a refusal
  S2  drive's own TakeDriver.config_view reader and lister reach the REAL operator_read and operator_list
  S3  drive.ownership_problems over the REAL box module (every step) is empty; drive.settings_guard_problems over the
      REAL box/settings_guard is empty
  S4  every drive.py call of a box function by name (_ownership, _settings_guard, _preflight, _sidecar, _run_take,
      self.ownership, self.settings_guard) binds to the real signature (ast + inspect.signature().bind)
"""
import ast
import inspect
import os
import sys
import tempfile
import types
import unittest

STUDY = os.path.abspath(sys.argv.pop(1)) if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else None
sys.path.insert(0, STUDY)
sys.path.insert(0, os.path.join(STUDY, "tests"))
import drive  # noqa: E402
from box import ownership, settings_guard, preflight, sidecar, run_take  # noqa: E402
from test_ownership import Fake  # noqa: E402   the box's own fake runtime

IMAGE = "sha256:" + "a" * 64


def stub(t):
    run_tree, cfg = os.path.join(t, "tree"), os.path.join(t, "cfg")
    os.mkdir(run_tree)
    os.mkdir(cfg)
    spec = types.SimpleNamespace(image=IMAGE, run_tree=run_tree)
    take = types.SimpleNamespace(spec=spec, launched=types.SimpleNamespace(spec=spec), config_dir=cfg)
    me = types.SimpleNamespace(ownership=ownership, runtime=Fake(reply='{"exists": false}'), caller_env={})
    return me, take


class TestSeams(unittest.TestCase):
    def test_s1_operator_read_from_drive(self):
        with tempfile.TemporaryDirectory() as t:
            me, take = stub(t)
            self.assertIsNone(drive.TakeDriver._operator_read(me, take, "op", "plan/approved.json"))

    def test_s2_config_view_from_drive(self):
        with tempfile.TemporaryDirectory() as t:
            me, take = stub(t)
            lister, reader = drive.TakeDriver.config_view(me, take)
            self.assertIsNone(reader("sessions/x.jsonl"))
            self.assertIsNone(lister("sessions"))

    def test_s3_interface_checks_over_the_real_box(self):
        self.assertEqual(drive.ownership_problems(ownership, operator_write=True, native=True), [])
        self.assertEqual(drive.settings_guard_problems(settings_guard), [])

    def test_s4_every_named_call_binds(self):
        aliases = {"_ownership": ownership, "_settings_guard": settings_guard, "_preflight": preflight,
                   "_sidecar": sidecar, "_run_take": run_take}
        attrs = {"ownership": ownership, "settings_guard": settings_guard}
        bad = []
        for node in ast.walk(ast.parse(open(drive.__file__).read())):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            v = node.func.value
            mod = aliases.get(v.id) if isinstance(v, ast.Name) else (
                attrs.get(v.attr) if isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name)
                and v.value.id == "self" else None)
            fn = getattr(mod, node.func.attr, None) if mod else None
            if fn is None or not callable(fn) or isinstance(fn, type):
                continue
            if any(isinstance(a, ast.Starred) for a in node.args) or any(k.arg is None for k in node.keywords):
                continue
            try:
                inspect.signature(fn).bind(*([None] * len(node.args)), **{k.arg: None for k in node.keywords})
            except TypeError as e:
                bad.append(f"drive.py:{node.lineno} {node.func.attr}: {e}")
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
