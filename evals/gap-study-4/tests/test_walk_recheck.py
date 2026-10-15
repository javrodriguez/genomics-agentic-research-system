#!/usr/bin/env python3
"""walk_regrade's recheck: a committed Claude Code walk re-checked from its committed records under the constants in
force (glitch-6b's scheduled-wakeup ruling, 15 Oct 2026; freeze-gate ruling line 51).

The walks here are made by test_walk_runner's rig (the real walk runner, the real driver on test_box_integration's
fake box, the real check_take through drive.take_checker), committed into a scratch study by the real WalkRepo; no
real walk record is read.

  RC-same       a committed walk re-checked against the design it was checked under gives its own check.json's
                reasons and digest back, with no change, superseding check.json, route null.
  RC-files      write_recheck and commit_recheck add recheck-1.json then recheck-2.json (superseding recheck-1); every
                earlier file of the walk folder, committed and on disk, stays byte-identical; a second write before
                the commit is refused.
  RC-tamper     a walk record changed in a later commit (the transcript, check.json, the driver ledger), or a stray
                file added after the walk commit, refuses the recheck.
  RC-change     a recheck whose checker reads other reasons, under other constants, reports the old digest and the new,
                and the reasons added and removed.
  RC-machine    the walk's machine is named exactly {checkout, home, temp_root}, absolute; anything else refuses.
  RC-standing   pending_walk.checker_standing: a graded walk checked under other constants is stale; a committed
                recheck under the constants in force lifts it only while it re-derives to its exact bytes; an edited
                recheck counts nothing.
  RC-check      walk_regrade's --check road (regrade_problems) re-derives every committed recheck, and names an edited
                one.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_walk_runner as twr  # noqa: E402

WALK = "w-0001"
wr = None


def setUpModule():
    global wr
    twr.setUpModule()
    import walk_regrade as wr


def tearDownModule():
    twr.tearDownModule()


def git(root, *args):
    out = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    assert out.returncode == 0, out.stderr.decode()
    return out.stdout.decode()


def folder_bytes(root: Path, walk: str) -> dict:
    """{name: (bytes on disk, bytes at HEAD)} of every file in the walk folder."""
    import mode_binding as mb
    folder = root / mb.WALKS_DIR / walk
    out = {}
    for p in sorted(x for x in folder.rglob("*") if x.is_file()):
        rel = f"{mb.WALKS_DIR}/{walk}/{p.relative_to(folder).as_posix()}"
        head = subprocess.run(["git", "-C", str(root), "show", f"HEAD:{rel}"], capture_output=True)
        out[p.relative_to(folder).as_posix()] = (p.read_bytes(), head.stdout if head.returncode == 0 else None)
    return out


class Rig:
    """One committed walk in a scratch study, and the arguments a recheck of it takes there."""

    def __init__(self, w):
        self.w = w
        got = w.run_walks([w.walk(WALK)])
        assert [g.get("state") for g in got] == ["committed"], got
        import check_take as ct
        self.ct = ct
        self.machine = {"home": str(ct.CHECK_HOME or Path.home()), "checkout": str(ct.CHECKOUT_REPO),
                        "temp_root": str(ct.CHECK_TEMP or "/tmp")}

    def design_for(self, constants=None):
        w = self.w
        return lambda row, run_tree: self.ct.design_view(row, pin=w.pin_for(row), run_tree=str(w.tree),
                                                         constants=w.constants if constants is None else constants)

    def old(self) -> dict:
        import mode_binding as mb
        return json.loads((self.w.root / mb.WALKS_DIR / WALK / "check.json").read_bytes())

    def doc(self, n=1, **kw):
        kw.setdefault("design_for", self.design_for())
        return wr.recheck_doc(WALK, n, self.w.root, machine=self.machine, **kw)

    def write_and_commit(self, **kw):
        kw.setdefault("design_for", self.design_for())
        path = wr.write_recheck(WALK, self.w.root, machine=self.machine, **kw)
        n = int(path.name[len(wr.RECHECK_PREFIX):-5])
        wr.commit_recheck(WALK, n, self.w.root, secrets=lambda: [("token", twr.tbi.TOKEN)], rules_scanner=lambda paths: [])
        return path


class TheRecheck(twr.Case):
    def test_rc_same_a_walk_rechecks_to_its_own_reading(self):
        with twr.study() as w:
            r = Rig(w)
            doc = self.must("RC-same", r.doc)
            old = r.old()
            self.assertEqual(doc["checker_reasons"], old["checker_reasons"], "RC-same: the reasons moved")
            self.assertEqual(doc["checker_constants_sha256"], old["checker_constants_sha256"], "RC-same: the digest")
            self.assertEqual(doc["change"]["reasons_added"] + doc["change"]["reasons_removed"], [])
            self.assertEqual((doc["supersedes"], doc["route"], doc["n"], doc["machine"]),
                             ("check.json", None, 1, r.machine))
            import mode_binding as mb
            self.assertEqual(doc["walk_commit"], wr.walk_commit(w.root, f"{mb.WALKS_DIR}/{WALK}"))

    def test_rc_files_append_only_and_old_files_byte_identical(self):
        with twr.study() as w:
            r = Rig(w)
            before = folder_bytes(w.root, WALK)
            self.must("RC-files", r.write_and_commit)
            with self.assertRaises(wr.RegradeRefused):            # the next one is refused while one is loose
                p = wr.write_recheck(WALK, w.root, machine=r.machine, design_for=r.design_for())
                wr.write_recheck(WALK, w.root, machine=r.machine, design_for=r.design_for())
            p.unlink()
            self.must("RC-files", r.write_and_commit)
            after = folder_bytes(w.root, WALK)
            for name, got in before.items():
                self.assertEqual(after[name], got, f"RC-files: {name} changed")
            self.assertEqual(sorted(set(after) - set(before)), ["recheck-1.json", "recheck-2.json"])
            two = json.loads(after["recheck-2.json"][0])
            self.assertEqual((two["n"], two["supersedes"], two["was"]["file"]), (2, "recheck-1.json", "recheck-1.json"))
            log = git(w.root, "log", "--format=%s", "-2").splitlines()
            self.assertEqual(log, [wr.RECHECK_SUBJECT] * 2)

    def test_rc_tamper_a_record_changed_after_the_walk_commit_refuses(self):
        import mode_binding as mb
        for name, edit in (("transcript.jsonl", lambda b: b.replace(b'"user"', b'"user" ', 1)),
                           ("check.json", lambda b: b.replace(b'"checked": true', b'"checked": true ', 1)),
                           ("driver-ledger.json", lambda b: b + b"\n"),
                           ("stray.json", None)):
            with self.subTest(record=name), twr.study() as w:
                r = Rig(w)
                path = w.root / mb.WALKS_DIR / WALK / name
                if edit is None:
                    path.write_text("{}\n")
                else:
                    raw = path.read_bytes()
                    self.assertNotEqual(edit(raw), raw, f"RC-tamper: the edit of {name} changed nothing")
                    path.write_bytes(edit(raw))
                git(w.root, "add", "-A")
                git(w.root, "commit", "-q", "-m", "a later edit")
                with self.assertRaises(wr.RegradeRefused) as cm:
                    r.doc()
                self.assertIn("after its walk commit", str(cm.exception))

    def test_rc_tamper_a_working_tree_edit_is_never_read(self):
        import mode_binding as mb
        with twr.study() as w:
            r = Rig(w)
            want = self.must("RC-tamper", r.doc)
            path = w.root / mb.WALKS_DIR / WALK / "transcript.jsonl"
            path.write_bytes(b'{"type": "user"}\n' + path.read_bytes())
            self.assertEqual(self.must("RC-tamper", r.doc), want, "RC-tamper: the working tree was read")

    def test_rc_change_is_reported(self):
        with twr.study() as w:
            r = Rig(w)
            old = r.old()
            constants = copy.deepcopy(w.constants)
            constants["budgets"]["poll_s"] = constants["budgets"]["poll_s"] + 1

            def checker(row, design, base, ledger):
                return {"checker_reasons": ["operator-lines"], "checker_events": {"x": 0}}
            doc = self.must("RC-change", r.doc, design_for=r.design_for(constants), checker=checker)
            self.assertNotEqual(doc["checker_constants_sha256"], old["checker_constants_sha256"])
            self.assertEqual(doc["change"]["checker_constants_sha256"],
                             [old["checker_constants_sha256"], doc["checker_constants_sha256"]])
            self.assertEqual(doc["change"]["reasons_added"], sorted({"operator-lines"} - set(old["checker_reasons"])))
            self.assertEqual(doc["change"]["reasons_removed"], sorted(set(old["checker_reasons"]) - {"operator-lines"}))

    def test_rc_machine_is_named_never_guessed(self):
        with twr.study() as w:
            r = Rig(w)
            for bad in (None, {}, dict(r.machine, extra="/x"), {k: v for k, v in r.machine.items() if k != "home"},
                        dict(r.machine, home="relative/home")):
                with self.subTest(machine=bad), self.assertRaises(wr.RegradeRefused):
                    wr.recheck_doc(WALK, 1, w.root, machine=bad, design_for=r.design_for())

    def test_rc_standing_reads_only_a_verified_recheck(self):
        import mode_binding as mb
        import pending_walk
        with twr.study() as w:
            r = Rig(w)
            base = w.root / mb.WALKS_DIR
            stale = pending_walk.checker_standing(base, WALK)
            self.assertTrue(stale and stale.startswith("stale"), f"RC-standing: the rig's walk reads {stale!r}")
            def real(row, run_tree):                             # the constants in force (CHECKER_CONSTANTS)
                return r.ct.design_view(row, pin=w.pin_for(row), run_tree=str(w.tree))
            with mock.patch.object(wr, "production_design", real):
                self.must("RC-standing", r.write_and_commit, design_for=real)
                got = pending_walk.checker_standing(base, WALK)
                rec = json.loads((base / WALK / "recheck-1.json").read_bytes())
                self.assertEqual(rec["checker_constants_sha256"], r.ct.checker_constants_sha256())
                bound = [x for x in rec["checker_reasons"] if x in r.ct.CONSTANT_BOUND_REASONS]
                self.assertEqual(got, f"constant-bound checker reason: {', '.join(bound)}" if bound else None,
                                 "RC-standing: a verified recheck under the constants in force")
                # an edited recheck (committed) counts nothing
                p = base / WALK / "recheck-1.json"
                p.write_bytes(p.read_bytes().replace(b'"n": 1', b'"n": 1 ', 1))
                git(w.root, "commit", "-q", "-am", "an edited recheck")
                self.assertTrue(pending_walk.checker_standing(base, WALK).startswith("recheck unverifiable"))
                self.assertTrue(any("recheck-1.json" in x for x in wr.regrade_problems(w.root)),
                                "RC-check: --check did not name the edited recheck")

    def test_rc_check_re_derives_every_committed_recheck(self):
        with twr.study() as w:
            r = Rig(w)
            with mock.patch.object(wr, "production_design", r.design_for()):
                self.must("RC-check", r.write_and_commit)
                self.assertEqual(wr.regrade_problems(w.root), [])


if __name__ == "__main__":
    unittest.main()
