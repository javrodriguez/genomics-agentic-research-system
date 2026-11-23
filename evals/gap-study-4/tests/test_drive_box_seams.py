#!/usr/bin/env python3
"""Drive-to-box seams (box lane, 15 Oct 2026, after CP6 walk w013 refused at launch on ce818d85 with "the ownership
road's operator_read is not operator_read(runtime, *, image, root_kind, root, rel_path, caller_env)").

Proposed by the box lane, adopted into the harness lane's tests/ under glitch-6b's item D (15 Oct 2026): red on
ce818d85, green once drive.py takes the box's reviewed O-3 signature. Run in tests/ it reads this study; it still
takes another tree's evals/gap-study-4 folder as its first argument.

  S1  drive's own TakeDriver._operator_read reaches the REAL box/ownership.operator_read (fake runtime) and returns
      the box's None for an absent file, never a refusal; and (review of D, MINOR) on a runtime that answers from the
      folder it was handed, it reads the RUN TREE's file, never the config folder's file of the same name
  S2  drive's own TakeDriver.config_view reader and lister reach the REAL operator_read and operator_list, and read
      and list the CONFIG folder, never the run tree
  S3  drive.ownership_problems over the REAL box module (every step) is empty; drive.settings_guard_problems over the
      REAL box/settings_guard is empty
  S4  every drive.py call of a box function by name (_ownership, _settings_guard, _preflight, _sidecar, _run_take,
      self.ownership, self.settings_guard) binds to the real signature (ast + inspect.signature().bind)
"""
import ast
import base64
import hashlib
import inspect
import json
import os
import sys
import tempfile
import types
import unittest

STUDY = (os.path.abspath(sys.argv.pop(1)) if len(sys.argv) > 1 and os.path.isdir(sys.argv[1])
         else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))      # in tests/: this study
sys.path.insert(0, STUDY)
sys.path.insert(0, os.path.join(STUDY, "tests"))
import drive  # noqa: E402
from box import ownership, settings_guard, preflight, sidecar, run_take  # noqa: E402
from test_ownership import Fake  # noqa: E402   the box's own fake runtime

IMAGE = "sha256:" + "a" * 64


class RootedFake(Fake):
    """The box's fake runtime, answering an operator read or listing from the ONE folder the step mounted, as the
    container would: so a read sent to the wrong root reads the wrong folder's bytes (review of item D)."""

    def run(self, argv, *, env=None, timeout=None):
        src = [a for a in argv if a.startswith("type=bind,source=")]
        root = src[0].split("=")[2].split(",")[0] if src else None
        if root is not None and ownership.READ_PROGRAM in argv:
            f = os.path.join(root, argv[-2])
            data = open(f, "rb").read() if os.path.isfile(f) else None
            self.reply = json.dumps({"exists": False} if data is None else {
                "exists": True, "b64": base64.b64encode(data).decode("ascii"),
                "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        elif root is not None and ownership.LIST_PROGRAM in argv:
            d = root if argv[-2] == "." else os.path.join(root, argv[-2])
            out = sorted((os.fsencode(n), "dir" if os.path.isdir(os.path.join(d, n)) else "file")
                         for n in os.listdir(d)) if os.path.isdir(d) else None
            if out is None:
                self.reply = json.dumps({"exists": False})
            else:
                out = [[base64.b64encode(r).decode("ascii"), k] for r, k in out]
                canon = json.dumps(out, separators=(",", ":"))
                self.reply = json.dumps({"exists": True, "entries": out,
                                         "sha256": hashlib.sha256(canon.encode("ascii")).hexdigest()})
        return super().run(argv, env=env, timeout=timeout)


def rooted(t):
    """A take whose run tree and config folder each hold a file the other lacks, and one name with other bytes."""
    me, take = stub(t)
    me.runtime = RootedFake()
    for root, who in ((take.spec.run_tree, b"run-tree"), (take.config_dir, b"config")):
        os.makedirs(os.path.join(root, "plan"))
        with open(os.path.join(root, "plan", "same.json"), "wb") as fh:
            fh.write(who)
        with open(os.path.join(root, f"only-{who.decode()}.txt"), "wb") as fh:
            fh.write(who)
    return me, take


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

    def test_s1_operator_read_reads_the_run_tree(self):
        with tempfile.TemporaryDirectory() as t:
            me, take = rooted(t)
            self.assertEqual(drive.TakeDriver._operator_read(me, take, "op", "plan/same.json"), b"run-tree")
            self.assertEqual(drive.TakeDriver._operator_read(me, take, "op", "only-run-tree.txt"), b"run-tree")
            self.assertIsNone(drive.TakeDriver._operator_read(me, take, "op", "only-config.txt"))

    def test_s2_config_view_reads_and_lists_the_config_folder(self):
        with tempfile.TemporaryDirectory() as t:
            me, take = rooted(t)
            lister, reader = drive.TakeDriver.config_view(me, take)
            self.assertEqual(reader("plan/same.json"), b"config")
            self.assertEqual(reader("only-config.txt"), b"config")
            self.assertIsNone(reader("only-run-tree.txt"))
            self.assertEqual(sorted(n for n, _ in lister(".")), ["only-config.txt", "plan"])

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
