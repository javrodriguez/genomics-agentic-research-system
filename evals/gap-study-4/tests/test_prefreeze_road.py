#!/usr/bin/env python3
"""Lane prefreeze-road (Gap Study round 4): fixture_walk places a /home path the same way on the Mac and on Linux.

The Lane-orchestrator's ruling 1 on the lane's hand-back (Sat 24 Oct 2026, under Javier's standing delegation), after
the first pre-freeze outputs run through the aegis suite road read fixture_walk.py --check red on athena and green on
the Mac. Walks w142 and w158 quote the GARS fixture's own text `/gpfs/home/<user>` and `/gpfs/data/abl/home/<user>`,
in which the path pattern reads `/home/<user`. On Linux that path is unplaced. On the Mac `/home` is a link to
`/System/Volumes/Data/home`, and under()'s resolved arm placed it under the system root `/System`, so the Mac's green
was an accident that would have placed any /home path. The ruling: (c) the gate behaves the same on both, with no
/home path resolved through /System, written red first; (a) one exact recorded exception per walk, binding each line
that names the quoted placeholder, with its reason; no general rule for `<` segments.

  F5-home   classify_path reads a system root by the path's own spelling only: `/home/<user` and a real /home path
            are `elsewhere` on every machine, a path under /usr is still `system`; w142 and w158 read unplaced with
            no exception of theirs and `excepted` (their two lines each) with them; a real /home path added to a copy
            of w142 still refuses; the placeholder named on one more line, or in a copy under another walk's name,
            is not excused; and no committed exception is stale.
            Witnesses: home-through-system (the resolved arm restored for system roots), walk-unbound (an
            exception applied to any walk).

Reads committed walk records and copies them into temporary folders only; no model, network or container.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
_PATH = list(sys.path)
sys.path.insert(0, str(HERE))

import fixture_walk as fw  # noqa: E402

sys.path[:] = _PATH

PLACEHOLDER = "/home/<user"
WALKS = {"w142": [11, 86], "w158": [11, 49]}
REAL_HOME = "/home/alice/projects/rnaseq/counts.tsv"


def mac_realpath(real):
    """os.path.realpath as the Mac resolves /home (a link to /System/Volumes/Data/home), on any machine: the closure
    review's MAJOR M1, so the home-through-system witness reads red on Linux too, where /home resolves to itself."""
    def resolve(path):
        path = os.fspath(path)
        if path == "/home" or path.startswith("/home/"):
            return "/System/Volumes/Data" + path
        return real(path)
    return resolve


def f5_home(mod, p="F5-home"):
    with mock.patch.object(os.path, "realpath", mac_realpath(os.path.realpath)):
        return _f5_home(mod, p)


def _f5_home(mod, p):
    out = []
    try:
        for path, want in ((PLACEHOLDER, "elsewhere"), (REAL_HOME, "elsewhere"), ("/home", "elsewhere"),
                           ("/usr/bin/python3", "system"), ("/etc/hosts", "system")):
            got = mod.classify_path(path, None)
            if got != want:
                out.append(f"{p}: {path} classified {got!r}, wanted {want!r}")
        others = tuple(e for e in mod.RECORDED_EXCEPTIONS if e["walk"] not in WALKS)
        for walk, lines in WALKS.items():
            t = mod.WALKS / walk / "transcript.jsonl"
            with mock.patch.object(mod, "RECORDED_EXCEPTIONS", others):
                rec = mod.replay(t)
            if rec["verdict"] != "unplaced" or rec["unplaced_paths"] != [PLACEHOLDER]:
                out.append(f"{p}: {walk} without its exception: {rec['verdict']} {rec['unplaced_paths']}")
            rec = mod.replay(t)
            got = [(e["path"], e["lines"]) for e in rec["recorded_exceptions"]]
            if rec["verdict"] != "excepted" or got != [(PLACEHOLDER, lines)]:
                out.append(f"{p}: {walk} with its exception: {rec['verdict']} {got}")
        with tempfile.TemporaryDirectory() as d:
            src = mod.WALKS / "w142"

            def copy(name, extra):
                folder = Path(d) / name / "w142" if name == "w142" else Path(d) / name
                shutil.copytree(src, folder)
                if extra is not None:
                    rec = {"type": "assistant", "message": {"content": [{"type": "text", "text": extra}]}}
                    with open(folder / "transcript.jsonl", "a") as f:
                        f.write(json.dumps(rec) + "\n")
                return mod.replay(folder / "transcript.jsonl")

            rec = copy("w142", f"then I read {REAL_HOME} for the counts")
            if rec["verdict"] != "unplaced" or REAL_HOME not in rec["unplaced_paths"]:
                out.append(f"{p}: a real /home path in w142: {rec['verdict']} {rec['unplaced_paths']}")
            shutil.rmtree(Path(d) / "w142")
            rec = copy("w142", f"the work area {PLACEHOLDER}> again")
            if rec["verdict"] != "unplaced":
                out.append(f"{p}: the placeholder on a third line of w142: {rec['verdict']}")
            rec = copy("w999", None)
            if rec["verdict"] != "unplaced":
                out.append(f"{p}: w142's lines under another walk's name: {rec['verdict']}")
        stale = mod.stale_exception_problems(sorted(str(t) for t in mod.WALKS.glob("*/transcript.jsonl")))
        if stale:
            out.append(f"{p}: stale exceptions: {stale}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


def witness_module(real: types.ModuleType, edits: tuple) -> types.ModuleType:
    src = Path(real.__file__).read_text(encoding="utf-8")
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"witness anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    mod = types.ModuleType(real.__name__ + "_pfr_witness")
    mod.__file__ = real.__file__
    path, modules = list(sys.path), set(sys.modules)
    try:
        exec(compile(src, real.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.path[:] = path
        for name in set(sys.modules) - modules:
            del sys.modules[name]
    return mod


WITNESSES = {
    "home-through-system": (("    if any(spelled_under(p, r) for r in SYSTEM_ROOTS):",
                             "    if any_under(p, SYSTEM_ROOTS):"),),
    "walk-unbound": (('        if exc["walk"] != walk or exc["path"] != path:',
                      '        if exc["path"] != path:'),),
}


class TestPrefreezeRoad(unittest.TestCase):
    def test_f5_a_home_path_is_placed_the_same_on_every_machine(self):
        self.assertEqual(f5_home(fw), [])

    def test_witnesses(self):
        self.assertEqual(sorted(WITNESSES), ["home-through-system", "walk-unbound"])
        for name, edits in WITNESSES.items():
            with self.subTest(witness=name):
                modules = set(sys.modules)
                got = f5_home(witness_module(fw, edits))
                self.assertEqual(set(sys.modules) - modules, set(), f"{name}: registered a module")
                errors = [x for x in got if x.startswith("ERROR")]
                self.assertEqual(errors, [], f"{name}: errored: {errors}")
                self.assertTrue([x for x in got if x.startswith("F5-home:")], f"{name}: survived")
                print(f"\nWITNESS {name}: red by F5-home", end=" ", file=sys.stderr, flush=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
