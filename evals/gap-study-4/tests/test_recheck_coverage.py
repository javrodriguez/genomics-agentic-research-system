#!/usr/bin/env python3
"""Recheck coverage (glitch-6b's ruling, 15 Oct 2026): a walk's standing comes from its LATEST register recheck entry.

walk_regrade.py --recheck writes recheck-<n>.json and, in the same commit, an append-only register entry {walk, file,
n, checker_constants_sha256, sha256} (register schema 2 adds `rechecks`). pending_walk.checker_standing reads only the
register and the files, no git and no process (walk_plan's road, P7): the latest entry counts when its digest is the
constants in force and its file is the bytes it names; otherwise the walk counts nothing. walk_register --check binds
entries and files both ways. Re-derivation is walk_regrade.py --check's (checks.d), never coverage's.

  C-count     the latest entry under the constants in force, its file intact: the walk's standing is the recheck's.
  C-nofile    an entry whose file is missing refuses (standing and walk_register).
  C-sha       a file whose sha256 is not its entry's refuses (standing and walk_register).
  C-stale     an entry under an old digest is stale.
  C-latest    two entries: the latest wins, either way round.
  C-carry     a file carrying another digest, walk or ordinal than its entry refuses (C-walk, C-n; an ordinal that
              is not an int, True or 1.0, refuses; a file with a duplicated key refuses).
  C-register  walk_register: a recheck file with no entry, an entry out of order, a misnamed file, extra fields.
  C-witness   each check dropped in an in-memory mutant turns its case red.
Pure filesystem fixtures; no git.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

ct = pw = wr = None
OLD = "0" * 64


def setUpModule():
    global ct, pw, wr
    saved = list(sys.path)
    import check_take as ct
    import pending_walk as pw
    import walk_register as wr
    sys.path[:] = saved


def walk_entry() -> dict:
    d = wr.design_in_force()
    task = sorted(d["tasks"])[0]
    arm = sorted(d["arms"])[0]
    return {"walk": "w-0001", "task": task, "half": d["tasks"][task]["halves"][0],
            "wording": d["tasks"][task]["wordings"][0], "arm": arm, "model": d["arms"][arm][0],
            "reason": "synthetic", "counted": False}


def recheck_doc(n: int, digest: str, reasons=(), walk="w-0001") -> bytes:
    doc = {"schema": 1, "walk": walk, "n": n, "checker_constants_sha256": digest, "checker_reasons": list(reasons),
           "supersedes": "check.json" if n == 1 else f"recheck-{n - 1}.json",
           "no_output_nudges": 0,            # review r7 MINOR 2: a recheck carries the transcript's count
           "agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0}, "nested_cli_calls": 0}    # Agent parity, part 6
    return (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode()


class World:
    """A rehearsals folder: one graded walk whose check.json is stale, and the rechecks given as (n, digest, reasons)."""

    def __init__(self, rechecks, *, entries=None):
        self.tmp = Path(tempfile.mkdtemp(prefix="recheck-cov-"))
        self.base = self.tmp / "rehearsals"
        folder = self.base / "w-0001"
        folder.mkdir(parents=True)
        (folder / "grade.json").write_text('{"graded": true, "row": {}, "grade": {"label": "stand-in"}}\n')
        (folder / "check.json").write_text(json.dumps({
            "walk": "w-0001", "checked": True, "checker_reasons": [], "events": {"outside_reach": 0},
            "route": "graded", "route_refused": None, "checker_constants_sha256": OLD}))
        reg = []
        for n, digest, reasons in rechecks:
            raw = recheck_doc(n, digest, reasons)
            (folder / f"recheck-{n}.json").write_bytes(raw)
            reg.append({"walk": "w-0001", "file": f"recheck-{n}.json", "n": n, "checker_constants_sha256": digest,
                        "sha256": hashlib.sha256(raw).hexdigest()})
        self.write_register(reg if entries is None else entries)

    def write_register(self, rechecks):
        doc = {"schema": 2, "walks": [walk_entry()], "rechecks": rechecks}
        (self.base / "register.json").write_text(json.dumps(doc, indent=2) + "\n")

    def standing(self, mod=None):
        return (mod or pw).checker_standing(self.base, "w-0001")

    def register_problems(self, mod=None):
        return (mod or wr).recheck_problems(self.base, json.loads((self.base / "register.json").read_text())["rechecks"],
                                            {"w-0001"})

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def now() -> str:
    return ct.checker_constants_sha256()


def cases(pmod=None, rmod=None) -> list:
    """Every case's problem lines (empty when all hold)."""
    out = []

    def case(name, rechecks, want_standing, want_register_clean=True, entries=None, after=None):
        w = World(rechecks, entries=entries)
        try:
            if after:
                after(w)
            got = w.standing(pmod)
            ok = got == want_standing if not callable(want_standing) else want_standing(got)
            if not ok:
                out.append(f"{name}: standing {got!r}")
            reg = w.register_problems(rmod)
            if bool(reg) == want_register_clean:
                out.append(f"{name}: walk_register {'refused' if reg else 'passed'}: {reg[:1]}")
        finally:
            w.close()
    starts = lambda p: (lambda got: isinstance(got, str) and got.startswith(p))  # noqa: E731
    case("C-count", [(1, now(), [])], None)
    case("C-nofile", [(1, now(), [])], starts("recheck file missing"), False,
         after=lambda w: (w.base / "w-0001" / "recheck-1.json").unlink())
    case("C-sha", [(1, now(), [])], starts("recheck file differs"), False,
         after=lambda w: (w.base / "w-0001" / "recheck-1.json").write_bytes(recheck_doc(1, now(), ["operator-lines"])))
    case("C-stale", [(1, OLD, [])], starts("stale"))
    case("C-latest-clean", [(1, now(), ["readers-disagree"]), (2, now(), [])], None)
    case("C-latest-bound", [(1, now(), []), (2, now(), ["readers-disagree"])], starts("constant-bound"))
    case("C-latest-stale", [(1, now(), []), (2, OLD, [])], starts("stale"))

    def carry(w):                      # the file says another digest; the entry names the file's new sha256
        raw = recheck_doc(1, OLD, [])
        (w.base / "w-0001" / "recheck-1.json").write_bytes(raw)
        e = json.loads((w.base / "register.json").read_text())["rechecks"]
        e[0]["sha256"] = hashlib.sha256(raw).hexdigest()
        w.write_register(e)
    case("C-carry", [(1, now(), [])], starts("recheck file does not carry"), after=carry)

    def swap(raw):                     # the file becomes `raw`; its entry names raw's sha256 (so only the carry differs)
        def go(w):
            (w.base / "w-0001" / "recheck-1.json").write_bytes(raw)
            e = json.loads((w.base / "register.json").read_text())["rechecks"]
            e[0]["sha256"] = hashlib.sha256(raw).hexdigest()
            w.write_register(e)
        return go
    case("C-walk", [(1, now(), [])], starts("recheck file does not carry"),
         after=lambda w: swap(recheck_doc(1, now(), [], walk="w-0002"))(w))
    case("C-n", [(1, now(), [])], starts("recheck file does not carry"),
         after=lambda w: swap(recheck_doc(2, now(), []))(w))
    case("C-n-bool", [(1, now(), [])], starts("recheck file does not carry"),
         after=lambda w: swap(recheck_doc(True, now(), []))(w))
    case("C-n-float", [(1, now(), [])], starts("recheck file does not carry"),
         after=lambda w: swap(recheck_doc(1.0, now(), []))(w))
    dup = ('{"checker_constants_sha256": "%s", "checker_reasons": ["readers-disagree"], "checker_reasons": [], '
           '"n": 1, "walk": "w-0001"}\n' % now()).encode()
    case("C-dupkey", [(1, now(), [])], starts("recheck unreadable"), after=lambda w: swap(dup)(w))
    return out


def renamed(w):
    """The entry names a file that is there with its bytes, but not as recheck-<n>.json."""
    (w.base / "w-0001" / "recheck-1.json").rename(w.base / "w-0001" / "recheck-x.json")
    w.write_register([dict(json.loads((w.base / "register.json").read_text())["rechecks"][0], file="recheck-x.json")])


def register_cases(rmod=None) -> list:
    out = []
    for name, rechecks, mutate in (
            ("C-register-unentried", [(1, now(), [])], lambda w: w.write_register([])),
            ("C-register-order", [(1, now(), [])], lambda w: w.write_register(        # n 2 for the first recheck
                [dict(json.loads((w.base / "register.json").read_text())["rechecks"][0], n=2)])),
            ("C-register-name", [(1, now(), [])], renamed),
            ("C-register-extra", [(1, now(), [])], lambda w: w.write_register(
                [dict(json.loads((w.base / "register.json").read_text())["rechecks"][0], extra=1)]))):
        w = World(rechecks)
        try:
            mutate(w)
            if not w.register_problems(rmod):
                out.append(f"{name}: walk_register passed")
        finally:
            w.close()
    return out


def mutant(mod, old: str, new: str):
    src = Path(mod.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutation site occurs {src.count(old)} times: {old!r}")
    m = types.ModuleType(mod.__name__ + "_mutant")
    m.__file__ = mod.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), mod.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    return m


PW_MUTANTS = (
    ("standing-reads-no-recheck", "    latest = latest_recheck(base, walk)", "    latest = None"),
    ("latest-is-first", "    e = entries[-1]", "    e = entries[0]"),
    ("no-sha-check", "    if hashlib.sha256(raw).hexdigest() != e.get(\"sha256\"):", "    if False:"),
    ("no-missing-check", "    except OSError:\n        return f\"recheck file missing", "    except KeyError:\n        return f\"recheck file missing"),
    ("no-carry-check", "doc.get(\"checker_constants_sha256\") != e.get(\"checker_constants_sha256\") \\", "False \\"),
    ("no-walk-clause", "            or doc.get(\"walk\") != walk \\\n", "            or False \\\n"),
    ("no-n-clause", "or type(doc.get(\"n\")) is not int or type(e.get(\"n\")) is not int or doc[\"n\"] != e[\"n\"]:",
     "or False:"),
    ("no-n-int-clause", "type(doc.get(\"n\")) is not int or type(e.get(\"n\")) is not int or doc[\"n\"]",
     "doc.get(\"n\")"),
    ("no-duplicate-key-hook", "json.loads(raw, object_pairs_hook=walk_register.no_duplicate_keys)", "json.loads(raw)"),
)
WR_MUTANTS = (
    ("register-no-sha", "        elif hashlib.sha256(f.read_bytes()).hexdigest() != e[\"sha256\"]:", "        elif False:"),
    ("register-no-file", "        if f.is_symlink() or not f.is_file():", "        if False:"),
    ("register-unentried-file", "            if m and int(m.group(1)) > seen.get(walk, 0):", "            if False:"),
    ("register-order", "        if type(e[\"n\"]) is not int or e[\"n\"] != want:", "        if False:"),
    ("register-name", "        if e[\"file\"] != f\"recheck-{want}.json\":", "        if False:"),
    ("register-fields", "        if not isinstance(e, dict) or set(e) != set(RECHECK_FIELDS):", "        if not isinstance(e, dict):"),
)


class TheRecheckCoverage(unittest.TestCase):
    def test_every_case(self):
        self.assertEqual(cases(), [])
        self.assertEqual(register_cases(), [])

    def test_walk_plans_register_read_takes_a_schema_2_register(self):
        """walk_plan validates the register over stand-in folders (no walk folder read): a recheck entry is checked
        there without its file, so a schema-2 register is read, and a malformed entry still refuses it."""
        import walk_plan
        w = World([(1, now(), [])])
        try:
            design = walk_plan.design_in_force()
            self.assertTrue(walk_plan.read_register(w.base, design))
            e = json.loads((w.base / "register.json").read_text())["rechecks"]
            w.write_register([dict(e[0], n=2)])
            with self.assertRaises(walk_plan.RegisterUnreadable):
                walk_plan.read_register(w.base, design)
        finally:
            w.close()

    def test_freeze_rehearsal_re_derives_rechecks(self):
        """The ruling's item 2: a counted recheck has been re-derived at freeze (walk_regrade.py --check)."""
        import freeze_rehearsal
        self.assertIn(("walk_regrade.py", "--check"), freeze_rehearsal.WALK_COMMANDS)
        self.assertIn(("walk_regrade.py", "--check"), freeze_rehearsal.COMMANDS)

    def test_coverage_opens_no_process(self):
        import subprocess
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("a process was started")):
            self.assertEqual(cases(), [])

    def test_witnesses(self):
        for name, old, new in PW_MUTANTS:
            with self.subTest(witness=name):
                try:
                    got = cases(pmod=mutant(pw, old, new))
                except Exception as e:  # noqa: BLE001 - a mutant that crashes standing is red too
                    got = [f"raised {type(e).__name__}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} {got[:1]}", end=" ", file=sys.stderr)
                self.assertTrue(got, name)
        for name, old, new in WR_MUTANTS:
            with self.subTest(witness=name):
                m = mutant(wr, old, new)
                try:
                    got = cases(rmod=m) + register_cases(rmod=m)
                except Exception as e:  # noqa: BLE001 - a mutant that crashes the check is red too
                    got = [f"raised {type(e).__name__}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} {got[:1]}", end=" ", file=sys.stderr)
                self.assertTrue(got, name)


if __name__ == "__main__":
    unittest.main()
