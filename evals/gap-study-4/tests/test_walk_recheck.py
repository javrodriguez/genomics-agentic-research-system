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
  RC-state      walk_regrade.recheck_state: the latest committed recheck, verified by re-deriving it; an edited one
                refuses. Coverage (pending_walk.checker_standing) reads the register's latest recheck entry.
  RC-check      walk_regrade's --check road (regrade_problems) re-derives every committed recheck, and names an edited
                one.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import types
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


def twr_mb():
    import mode_binding
    return mode_binding


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
            p.unlink()                                             # and the register goes back to HEAD's
            git(w.root, "checkout", "--", f"{twr_mb().WALKS_DIR}/register.json")
            self.must("RC-files", r.write_and_commit)
            after = folder_bytes(w.root, WALK)
            for name, got in before.items():
                self.assertEqual(after[name], got, f"RC-files: {name} changed")
            self.assertEqual(sorted(set(after) - set(before)), ["recheck-1.json", "recheck-2.json"])
            import walk_register
            reg = json.loads((w.root / twr_mb().WALKS_DIR / walk_register.REGISTER_NAME).read_text())
            self.assertEqual((reg["schema"], [(e["walk"], e["n"], e["file"]) for e in reg["rechecks"]]),
                             (2, [(WALK, 1, "recheck-1.json"), (WALK, 2, "recheck-2.json")]))
            base = w.root / twr_mb().WALKS_DIR
            self.assertEqual(walk_register.check(base, walk_register.design_in_force(w.root))[0], [])
            self.assertEqual(walk_register.history_problems(base, [WALK], w.root), [],
                             "RC-files: the register's history check admits the recheck commits")
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

    def test_rc_state_reads_only_a_verified_recheck(self):
        """recheck_state verifies the latest committed recheck by re-deriving it; coverage
        (pending_walk.checker_standing) reads the register's latest recheck entry and its file, never git."""
        import mode_binding as mb
        import pending_walk
        with twr.study() as w:
            r = Rig(w)
            base = w.root / mb.WALKS_DIR
            self.assertIsNone(wr.recheck_state(base, WALK), "RC-state: no recheck committed yet")

            def real(row, run_tree):                             # the constants in force (CHECKER_CONSTANTS)
                return r.ct.design_view(row, pin=w.pin_for(row), run_tree=str(w.tree))
            with mock.patch.object(wr, "production_design", real):
                self.must("RC-state", r.write_and_commit, design_for=real)
                rec = wr.recheck_state(base, WALK)
                self.assertEqual(rec["checker_constants_sha256"], r.ct.checker_constants_sha256())
                got = pending_walk.checker_standing(base, WALK)          # the register's latest recheck counts
                bound = [x for x in rec["checker_reasons"] if x in r.ct.CONSTANT_BOUND_REASONS]
                self.assertEqual(got, f"constant-bound checker reason: {', '.join(bound)}" if bound else None,
                                 "RC-state: the recheck under the constants in force sets the standing")
                p = base / WALK / "recheck-1.json"               # an edited recheck (committed) is refused
                p.write_bytes(p.read_bytes().replace(b'"n": 1', b'"n": 1 ', 1))
                git(w.root, "commit", "-q", "-am", "an edited recheck")
                with self.assertRaises(wr.RegradeRefused):
                    wr.recheck_state(base, WALK)
                self.assertTrue(any("recheck-1.json" in x for x in wr.regrade_problems(w.root)),
                                "RC-check: --check did not name the edited recheck")
                import walk_register
                self.assertTrue(walk_register.history_problems(base, [WALK], w.root),
                                "RC-state: a later commit editing a recheck passes the register's history check")

    def test_rc_check_re_derives_every_committed_recheck(self):
        with twr.study() as w:
            r = Rig(w)
            with mock.patch.object(wr, "production_design", r.design_for()):
                self.must("RC-check", r.write_and_commit)
                self.assertEqual(wr.regrade_problems(w.root), [])

    def test_rc_check_reads_only_the_latest_after_a_constants_change(self):
        """Review F: --check re-derives each walk's latest recheck only; an earlier one, made under earlier constants,
        is checked for its shape and its supersedes link, so a constants change is cleared by the next recheck."""
        import mode_binding as mb
        with twr.study() as w:
            r = Rig(w)
            with mock.patch.object(wr, "production_design", r.design_for()):
                self.must("RC-check", r.write_and_commit)
            moved = copy.deepcopy(w.constants)
            moved["budgets"]["poll_s"] = moved["budgets"]["poll_s"] + 1
            with mock.patch.object(wr, "production_design", r.design_for(moved)):
                red = wr.regrade_problems(w.root)
                self.assertTrue(any("recheck-1.json differs" in x for x in red), f"RC-check: before recheck-2: {red}")
                self.must("RC-check", r.write_and_commit, design_for=r.design_for(moved))
                self.assertEqual(wr.regrade_problems(w.root), [], "RC-check: recheck-2 does not clear the change")
                p = w.root / mb.WALKS_DIR / WALK / "recheck-1.json"       # an earlier link broken is still red
                p.write_bytes(p.read_bytes().replace(b'"supersedes": "check.json"', b'"supersedes": "grade.json"', 1))
                git(w.root, "commit", "-q", "-am", "an edited earlier recheck")
                self.assertTrue(any("recheck-1.json is not a recheck" in x for x in wr.regrade_problems(w.root)))
                self.assertFalse(any("checker_events" in json.loads(p.read_bytes()) for _ in [0]))

    def test_rc_history_keeps_the_rechecks_list_append_only(self):
        """walk_register.rechecks_append_only_problems: a later commit dropping a recheck entry from the register is
        red; a walk_register without that call says nothing about it (the witness)."""
        import walk_register
        with twr.study() as w:
            r = Rig(w)
            with mock.patch.object(wr, "production_design", r.design_for()):
                self.must("RC-append", r.write_and_commit)
                self.must("RC-append", r.write_and_commit)
            base = w.root / twr_mb().WALKS_DIR
            self.assertEqual(walk_register.history_problems(base, [WALK], w.root), [])
            reg = json.loads((base / walk_register.REGISTER_NAME).read_text())
            reg["rechecks"] = reg["rechecks"][1:]
            (base / walk_register.REGISTER_NAME).write_text(json.dumps(reg, indent=2) + "\n")
            git(w.root, "commit", "-q", "-am", "a register edit dropping a recheck")
            msg = "the rechecks list is append-only"
            self.assertTrue(any(msg in x for x in walk_register.history_problems(base, [WALK], w.root)))
            src = Path(walk_register.__file__).read_text()
            site = "    out += rechecks_append_only_problems(git, reg_rel)\n"
            self.assertEqual(src.count(site), 1)
            m = types.ModuleType("walk_register_witness")
            m.__file__ = walk_register.__file__
            sys.modules[m.__name__] = m
            try:
                exec(compile(src.replace(site, ""), walk_register.__file__, "exec"), m.__dict__)
            finally:
                del sys.modules[m.__name__]
            self.assertFalse(any(msg in x for x in m.history_problems(base, [WALK], w.root)),
                             "the witness: without the call the drop is not named")

    def test_rc_history_admits_a_regrade_commit(self):
        """A committed regrade.json (walk_regrade's REGRADE_SUBJECT, adding only that file) passes the register's
        history check; under another subject, or touching the register too, it does not."""
        import walk_register
        for subject, with_register, ok in ((walk_register.REGRADE_SUBJECT, False, True),
                                           ("Another subject", False, False),
                                           (walk_register.REGRADE_SUBJECT, True, False)):
            with self.subTest(subject=subject, with_register=with_register), twr.study() as w:
                Rig(w)
                base = w.root / twr_mb().WALKS_DIR
                (base / WALK / walk_register.REGRADE_FILE).write_text('{"schema": 1}\n')
                git(w.root, "add", "--", f"{twr_mb().WALKS_DIR}/{WALK}/{walk_register.REGRADE_FILE}")
                if with_register:
                    (base / walk_register.REGISTER_NAME).write_text(
                        (base / walk_register.REGISTER_NAME).read_text() + "\n")
                    git(w.root, "add", "--", f"{twr_mb().WALKS_DIR}/{walk_register.REGISTER_NAME}")
                git(w.root, "commit", "-q", "-m", subject)
                got = walk_register.history_problems(base, [WALK], w.root)
                self.assertEqual(got == [], ok, got)


class TheNudgeRederivation(twr.Case):
    """Review r7 (glitch-b5, 16 Oct 2026), over committed fixture walks: a recheck carries check_take's count of the
    committed transcript (R7-2); a walk committed with a forged count is named by --check's re-derivation and refused
    by a recheck; a walk whose transcript is gone at HEAD is named (R7-3)."""

    def test_rn_a_recheck_carries_the_transcripts_count(self):
        import mode_binding as mb
        with twr.study() as w:
            r = Rig(w)
            doc = self.must("RN-count", r.doc)
            want = r.ct.no_output_nudges(w.root / mb.WALKS_DIR / WALK / "transcript.jsonl")
            self.assertIs(type(doc.get("no_output_nudges")), int, f"RN-count: {doc.get('no_output_nudges')!r}")
            self.assertEqual(doc["no_output_nudges"], want)
            self.assertEqual(wr.regrade_problems(w.root), [], "RN-count: a true count is named")

    def test_rn_a_forged_count_is_named_and_refused(self):
        with twr.study() as w:
            w.driver.no_output_nudges = lambda row: 5          # the walk is committed with a count its transcript lacks
            r = Rig(w)
            self.assertEqual(r.old()["no_output_nudges"], 5)
            got = wr.regrade_problems(w.root)
            self.assertTrue(any(WALK in p and "no_output_nudges is 5" in p for p in got), f"RN-forged: {got}")
            with self.assertRaises(wr.RegradeRefused) as cm:
                r.doc()
            self.assertIn("no_output_nudges is 5", str(cm.exception))

    def test_rn_a_walk_without_its_transcript_is_named(self):
        import mode_binding as mb
        with twr.study() as w:
            Rig(w)
            git(w.root, "rm", "-q", "--", f"{mb.WALKS_DIR}/{WALK}/transcript.jsonl")
            git(w.root, "commit", "-q", "-m", "drop the transcript (fixture)")
            got = wr.regrade_problems(w.root)
            self.assertTrue(any(WALK in p and "cannot be re-derived" in p for p in got), f"RN-gone: {got}")


def register_source_mutant(old: str, new: str):
    """walk_register compiled with one anchored edit, never placed in sys.modules under its own name."""
    import walk_register
    src = Path(walk_register.__file__).read_text()
    assert src.count(old) == 1, f"anchor occurs {src.count(old)} times: {old!r}"
    m = types.ModuleType("walk_register_witness")
    m.__file__ = walk_register.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), walk_register.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    return m


class TheRechecksHistory(unittest.TestCase):
    """glitch-6b (15 Oct 2026): the two clauses of walk_register.rechecks_append_only_problems that had no witness.

      RA-dupkey   a recheck commit's register is read with no_duplicate_keys: one that carries a duplicate key (or is
                  not JSON) cannot show the list append-only and is named, never read as empty or as its last value.
      RA-history  the register's log is read with --full-history: a recheck commit on a side branch that a merge
                  -s ours dropped is still read, and the drop is named.
      RA-rc       (r5 NIT (d)) a register log that fails is named, never read as an empty history.
    Each has a witness: the clause edited out, the case passes silently. Plain scratch repositories, no walk."""

    REG = "rehearsals/register.json"

    def repo(self) -> Path:
        import tempfile
        root = Path(tempfile.mkdtemp(dir=twr.tbi.SCRATCH)).resolve() / "r"
        root.mkdir()
        git(root, "init", "-q", "-b", "main")
        git(root, "config", "user.email", "scratch@example.invalid")
        git(root, "config", "user.name", "scratch")
        git(root, "config", "maintenance.auto", "false")
        (root / "rehearsals").mkdir()
        return root

    def commit(self, root: Path, text: str, subject: str):
        (root / self.REG).write_text(text)
        git(root, "add", "--", self.REG)
        git(root, "commit", "-q", "-m", subject)

    @staticmethod
    def problems(mod, root: Path):
        def g(*args):
            return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return mod.rechecks_append_only_problems(g, TheRechecksHistory.REG)

    def test_ra_dupkey_a_recheck_commits_register_with_a_duplicate_key_is_named(self):
        import walk_register
        root = self.repo()
        self.commit(root, '{"schema": 2, "walks": [], "rechecks": [{"n": 1}], "rechecks": [{"n": 2}]}\n',
                    walk_register.RECHECK_SUBJECT)
        self.commit(root, '{"schema": 2, "walks": [], "rechecks": [{"n": 2}]}\n', "a later register")
        got = self.problems(walk_register, root)
        self.assertTrue(any("cannot be read" in p for p in got), f"RA-dupkey: {got}")
        m = register_source_mutant(
            "            return rechecks_of(json.loads(shown.stdout, object_pairs_hook=no_duplicate_keys))",
            "            return rechecks_of(json.loads(shown.stdout, object_pairs_hook=dict))")
        self.assertEqual(self.problems(m, root), [], "RA-dupkey witness: read as its last value, nothing is named")

    def test_ra_history_a_recheck_dropped_by_a_merge_ours_is_named(self):
        import walk_register
        root = self.repo()
        self.commit(root, '{"schema": 1, "walks": []}\n', "the register")
        git(root, "checkout", "-q", "-b", "side")
        self.commit(root, '{"schema": 2, "walks": [], "rechecks": [{"n": 1}]}\n', walk_register.RECHECK_SUBJECT)
        git(root, "checkout", "-q", "main")
        git(root, "merge", "-q", "-s", "ours", "--no-ff", "--no-edit", "side")
        self.assertEqual(json.loads((root / self.REG).read_text()), {"schema": 1, "walks": []})
        got = self.problems(walk_register, root)
        self.assertTrue(any("append-only" in p for p in got), f"RA-history: {got}")
        m = register_source_mutant(
            '    log = git("log", "--full-history", "--no-merges", "--format=%H%x1f%s", "HEAD", "--", reg_rel)\n'
            '    out = []',
            '    log = git("log", "--no-merges", "--format=%H%x1f%s", "HEAD", "--", reg_rel)\n'
            '    out = []')
        self.assertEqual(self.problems(m, root), [], "RA-history witness: the side branch is pruned, nothing is named")

    def test_ra_rc_a_register_log_that_fails_is_named(self):
        """r5 review NIT (d) (glitch-6b's queue, 16 Oct 2026): the register's `git log --full-history` exit status is
        read. A log that fails (here a repository with no commit: rc 128) cannot show the rechecks list append-only and
        is named, never read as an empty history."""
        import walk_register
        root = self.repo()
        got = self.problems(walk_register, root)
        self.assertTrue(any("history cannot be read" in p for p in got), f"RA-rc: {got}")
        m = register_source_mutant(
            "    if log.returncode != 0:\n        return [f\"the register's history cannot be read ({log.stderr.strip()[:200]}): "
            "the rechecks list cannot be shown append-only\"]\n",
            "")
        self.assertEqual(self.problems(m, root), [], "RA-rc witness: the failed log reads as no history, nothing named")


if __name__ == "__main__":
    unittest.main()
