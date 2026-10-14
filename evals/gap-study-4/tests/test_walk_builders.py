#!/usr/bin/env python3
"""The walk runner's production builders and its command line (Gap Study round 4, lane w12b-walk-builders; next-slices
plan of 12 Oct, section 1 item 5, the half fakes can prove; Q-w7b-3; glitch-2f's assignment under Javier's standing
delegation, Tue 13 Oct 2026).

  B1  ruling D2, the identity: walk_builders.walk_identity gives exactly drive.IDENTITY_KEYS, its session id
      uuid5(takes.namespace(), "walk/" + id) recomputed here from the ruling's words, row and row_commit None, the
      source, a copy of the fixture record and the gars tree; drive.walk_identity_problems admits it for its own walk
      and refuses it for another; a relative or unnormalised source, a missing fixture record and a gars tree that is
      not 40 hex are refused. identity_for hands a copy each call and refuses a walk it was not given.
  B2  the login file, by NAME: an absolute path to a regular file (never a link), mode 600, owned by the reader,
      outside every repository, starting `CLAUDE_CODE_OAUTH_TOKEN=`; exactly that many bytes are read, in one read,
      the file closed, so a value that is not even text passes and the value is never read; each rule refuses alone,
      and no refusal carries the value; login_secrets reads the value only when the scan asks.
  B3  the counters reader: run_take.counters over the folder cgroup_dir_for(take) names, for that take; a folder that
      is not absolute or does not exist is refused; a counter file missing is run_take's refusal, never a zero.
  B4  the run tree: drive.clean_run_tree of the origin commit at the walk's own neutral name (one commit, the neutral
      subject, no remote, clean status, the exclusions absent); a second build of the walk, an unknown commit and a
      malformed commit or exclusion list are refused, leaving nothing; remove_run_tree says why it could not remove.
  B5  the fixture: drive.build_take_fixture inside the run tree (a stand-in generator in place of the real one, which
      the process guard never starts); the record and the template's source; a generated fixture off its pin, a
      generator that fails, a source the build did not make, and a project fixture with no stage 01 exit, another
      exit than its variant's, or another variant, are each refused by name.
  B6  the walk row: the design's first row for the cell, its walk and slot the walk id, its agent version the pinned
      one; the design's own rows untouched; a cell the design lacks and an empty version refused.
  B7  production refuses by name: production_builders() leaves exactly the values only the real box, the owner or a
      walk can give Missing, each with its reason; walk_runner.main, with or without a walk named, exits 2 naming
      each one, in order, and Q-w7b-3, before anything is parsed or built; missing() also names an absent name and
      one the set does not know.
  B8  a value once measured is no longer missing: routing.json's pin_profiles filled give pin_for, the checker's
      constants filled give design_for, a real rules scanner gives rules_scanner (patched here, never in a file).
  B9  the command line drives one walk end to end on the fake box: walk_runner.main(argv, builders=<the fake box's>)
      builds the row, the run tree, the fixture and the identity, drives the walk through drive.walk_driver(
      records="walks"), checks it, grades it with the REAL v4 grader (the fake sidecar watches the half's planted
      paths) and commits it with its reason: exit 0, one register entry, the walk's own session in its ledger, the
      run tree and the config folder removed, nothing under takes/. With one builder absent, Missing or unknown, a
      cell the design lacks, a row of another harness, or a login of another name: exit 2 and nothing built. A
      fixture refused: exit 2 and its run tree removed. A walk id already registered: launch-refused, exit 1. A
      held walk (a scan refusal): exit 1, its run tree kept for a human.
  G1  the generated mutants (tests/walk_mutation.py's generator over every top-level function of walk_builders.py and
      walk_runner.main): EQUIVALENT names only generated ids, each with a reason.

TEST DATA, NEVER PRODUCTION VALUES: test_walk_wiring's rig (its walk constants, routing pin, agent version, fake
session box) and test_box_integration's fake runtime, process guard, synthetic login value and scratch repositories.
Fakes and synthetic strings only: no model, vendor, network, container runtime, credential, salt or holdout. No
PENDING value is filled in any file; the ones a test needs are handed in or patched for that test alone.

--mutant NAME compiles one altered module in memory before the bound test runs; --witnesses runs every registered
mutant in its own process, only its bound test, and requires that test to fail by an AssertionError carrying its
clause token, with no error (rule B). --generated-mutants [--shard i/n] [--sample k] [--only id,id] [--timeout s]
runs each generated mutant in its own process over this whole module (failfast) and fails on a survivor not listed in
EQUIVALENT, a listed one killed, or an inconclusive run.
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import uuid
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import batch  # noqa: E402
import takes  # noqa: E402
import test_box_integration as tbi  # noqa: E402
import test_walk_wiring as tww  # noqa: E402
import variants  # noqa: E402
from box import run_take as rt  # noqa: E402

SELECTED = None          # --mutant NAME: one hand witness
GENERATED = None         # --gen-mutant ID: one generated mutant (tests/walk_mutation.py over ROAD)
MODS: dict = {}
LOGIN = "CLAUDE_CODE_OAUTH_TOKEN"
TARGETS = ("walk_builders", "walk_runner")
# The production values still missing, in walk_builders.NAMES' order: the real box's (item 4), the owner's login
# (item 7) and the walks' (pins, constants, budgets, exclusions). A value filled later turns this list red on purpose.
EXPECTED_MISSING = ["runtime", "config_parent", "take_spec", "sidecar_for", "proxy", "lock_path", "hosts", "uid_map",
                    "cgroup_dir_for", "rules_scanner", "login_path", "agent_version", "design_for",
                    "budgets", "run_tree_exclude"]
# CP5 (Javier, "CP5: all as recommended", 14 Oct 2026) registered arm A's pin profiles, so pin_for is no longer missing
# in production (B8's rule, on the real table); it is checked present in B7.production.
# The ownership road is the box lane's box/ownership.py (81ede46d): missing, by name, on a tree without that module, and
# present on the merged head (B7.production checks it is then drive's own `_ownership`).
OWNERSHIP_ON_TREE = (Path(__file__).resolve().parents[1] / "box" / "ownership.py").is_file()
EXPECTED_MISSING += [] if OWNERSHIP_ON_TREE else ["ownership"]
SETTINGS_GUARD_ON_TREE = (Path(__file__).resolve().parents[1] / "box" / "settings_guard.py").is_file()
EXPECTED_MISSING += [] if SETTINGS_GUARD_ON_TREE else ["settings_guard"]


def road() -> dict:
    """The generated sweep's road: every top-level function of walk_builders.py (read by AST, so a new one is in it)
    and walk_runner.main, whose body is this lane's departure w12b-1."""
    tree = ast.parse((HERE / "walk_builders.py").read_text())
    return {"walk_builders": tuple(n.name for n in tree.body if isinstance(n, ast.FunctionDef)),
            "walk_runner": ("main",)}


def generate():
    import walk_mutation
    with mock.patch.dict(walk_mutation.ROAD, road(), clear=True):
        return walk_mutation.generate()


def by_id() -> dict:
    return {m.id: m for m in generate()[0]}


# Hand witnesses: name -> (clause, module, old text, new text). Each weakens one guard; old occurs exactly once.
def mutants() -> dict:
    return {
        "identity-another-session": ("B1.identity", "walk_builders", "    sid = check_take.walk_session_id(walk)\n"
                                     "    if not isinstance(source, str)",
                                     "    sid = check_take.walk_session_id(walk + 'x')\n"
                                     "    if not isinstance(source, str)"),
        "identity-row-set": ("B1.identity", "walk_builders", '    return {"session_id": sid, "row": None,',
                             '    return {"session_id": sid, "row": 0,'),
        "identity-source-unchecked": ("B1.identity", "walk_builders",
                                      "    if not isinstance(source, str) or not os.path.isabs(source) or "
                                      "os.path.normpath(source) != source:", "    if False:"),
        "identity-any-walk": ("B1.identity", "walk_builders", "        if walk not in prepared:",
                              "        if False:"),
        "login-reads-on": ("B2.login", "walk_builders", "        head = os.read(fd, len(want))",
                           "        head = os.read(fd, 4096)[:len(want)]"),
        "login-mode-unchecked": ("B2.login", "walk_builders", "    if stat.S_IMODE(st.st_mode) != 0o600:",
                                 "    if False:"),
        "login-in-repo": ("B2.login", "walk_builders", "    if not rt.outside_every_repository(path):",
                          "    if False:"),
        "login-link-admitted": ("B2.login", "walk_builders", "    if not stat.S_ISREG(st.st_mode):",
                                "    if stat.S_ISDIR(st.st_mode):"),
        "login-name-unchecked": ("B2.login", "walk_builders", "    if head != want:", "    if False:"),
        "login-fstat-unchecked": ("B2.login", "walk_builders",
                                  "        if (opened.st_dev, opened.st_ino, opened.st_mode) != (st.st_dev, st.st_ino, "
                                  "st.st_mode):", "        if False:"),
        "login-follows-links": ("B2.login", "walk_builders", "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK",
                                "os.O_RDONLY | os.O_NONBLOCK"),
        "login-blocks-on-fifo": ("B2.login", "walk_builders", "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK",
                                 "os.O_RDONLY | os.O_NOFOLLOW"),
        "missing-none-present": ("B7.production", "walk_builders",
                                 '    out += [(n, "present but None") for n in NAMES if n in builders and builders[n] '
                                 'is None]   # W12B-R1-2\n', ""),
        "table-error-raises": ("B7.production", "walk_builders",
                               "    except Exception as e:  # noqa: BLE001\n        print(f\"refused: the production "
                               "builders cannot be read", "    except KeyError as e:  # noqa: BLE001\n        "
                               "print(f\"refused: the production builders cannot be read"),
        "walk-id-unchecked": ("B9.cli", "walk_builders", "    if not walk_register.WALK_ID.fullmatch(args.walk):",
                              "    if False:"),
        "kept-tree-unnamed": ("B9.cli", "walk_builders",
                              '        print(f"kept run tree: {tree} (run_walks raised; left for a human)", '
                              'file=sys.stderr)', "        pass"),
        "secrets-read-early": ("B2.login", "walk_builders", "    name = login_name(harness)\n\n    def secrets():",
                               "    name = login_name(harness)\n    scan_record.read_login(login_file, name, "
                               "allowed=tuple(rt.LOGIN_VARIABLE.values()))\n\n    def secrets():"),
        "counters-folder-unchecked": ("B3.counters", "walk_builders",
                                      "        if not isinstance(folder, str) or not os.path.isabs(folder) or not "
                                      "os.path.isdir(folder):", "        if False:"),
        "counters-zero": ("B3.counters", "walk_builders", "        return rt.counters(folder)",
                          "        return {'oom_kill': 0, 'pids_max': 0}"),
        "run-tree-commit-unchecked": ("B4.run-tree", "walk_builders",
                                      "    if not isinstance(commit, str) or not HEX40.fullmatch(commit):",
                                      "    if False:"),
        "run-tree-session-another": ("B4.run-tree", "walk_builders",
                                     "        return drive.clean_run_tree(commit, sid, list(exclude), Path(repo))",
                                     "        return drive.clean_run_tree(commit, check_take.walk_session_id(walk + "
                                     "'x'), list(exclude), Path(repo))"),
        "run-tree-exclude-dropped": ("B4.run-tree", "walk_builders", "commit, sid, list(exclude), Path(repo))",
                                     "commit, sid, [], Path(repo))"),
        "fixture-stage01-unchecked": ("B5.fixture", "walk_builders",
                                      "        if not isinstance(got, int) or not isinstance(want, int) or got != want:",
                                      "        if False:"),
        "fixture-source-unchecked": ("B5.fixture", "walk_builders", "    if not os.path.exists(source):",
                                     "    if False:"),
        "fixture-nothing-admitted": ("B5.fixture", "walk_builders", "    if not isinstance(record, dict):",
                                     "    if False:"),
        "row-slot-not-walk": ("B6.row", "walk_builders", "row = dict(found[0], walk=walk, slot=walk)",
                              "row = dict(found[0], walk=walk)"),
        "row-version-kept": ("B6.row", "walk_builders",
                             '    row["agent"] = {"harness": row["agent"]["harness"], "version": agent_version}',
                             '    row["agent"]["version"] = agent_version'),
        "production-runtime-filled": ("B7.production", "walk_builders",
                                      '        "runtime": Missing(f"the DockerRuntime, built at {box}"),',
                                      '        "runtime": object(),'),
        "missing-absent-silent": ("B7.production", "walk_builders",
                                  '    out = [(n, "absent from the builder set") for n in NAMES if n not in builders]',
                                  "    out = []"),
        "cli-runs-with-gaps": ("B7.production", "walk_builders", "    if gaps:\n        for name, why in gaps:",
                               "    if False:\n        for name, why in gaps:"),
        "pin-never-present": ("B8.present", "walk_builders", "if not table.get(\"pin_profiles\") else",
                              "if True else"),
        "main-ignores-builders": ("B9.cli", "walk_runner",
                                  "    return walk_builders.cli(argv, builders, refusal=CLI_REFUSAL)",
                                  "    return walk_builders.cli(argv, None, refusal=CLI_REFUSAL)"),
        "held-tree-removed": ("B9.cli", "walk_builders",
                              "    kept = None if state == walk_runner.HELD else remove_run_tree(tree)",
                              "    kept = remove_run_tree(tree)"),
        "held-exits-zero": ("B9.cli", "walk_builders", "    return 0 if state == COMMITTED else 1", "    return 0"),
        "refused-tree-left": ("B9.cli", "walk_builders", "        left = remove_run_tree(tree)\n",
                              "        left = None\n"),
    }


METHOD = {
    "identity-another-session": "B1Identity.test_the_identity_is_the_walks_own",
    "identity-row-set": "B1Identity.test_the_identity_is_the_walks_own",
    "identity-source-unchecked": "B1Identity.test_a_bad_source_is_refused",
    "identity-any-walk": "B1Identity.test_identity_for_hands_a_copy_of_its_own_walk_only",
    "login-reads-on": "B2Login.test_only_the_name_is_read",
    "login-mode-unchecked": "B2Login.test_each_placement_rule_refuses",
    "login-in-repo": "B2Login.test_each_placement_rule_refuses",
    "login-link-admitted": "B2Login.test_each_placement_rule_refuses",
    "login-name-unchecked": "B2Login.test_another_name_is_refused_without_its_value",
    "secrets-read-early": "B2Login.test_the_secrets_read_the_value_only_when_asked",
    "login-fstat-unchecked": "B2Login.test_a_file_swapped_after_the_check_is_refused",
    "login-follows-links": "B2Login.test_a_file_swapped_after_the_check_is_refused",
    "login-blocks-on-fifo": "B2Login.test_a_file_swapped_after_the_check_is_refused",
    "missing-none-present": "B7Production.test_missing_names_absent_and_unknown",
    "table-error-raises": "B7Production.test_an_unreadable_table_is_refused_by_name",
    "walk-id-unchecked": "B9Cli.test_a_refused_row_or_login_builds_nothing",
    "kept-tree-unnamed": "B9Cli.test_a_runner_that_raises_names_its_kept_run_tree",
    "counters-folder-unchecked": "B3Counters.test_a_bad_folder_is_refused",
    "counters-zero": "B3Counters.test_the_take_s_own_counters",
    "run-tree-commit-unchecked": "B4RunTree.test_malformed_inputs_build_nothing",
    "run-tree-session-another": "B4RunTree.test_the_walk_s_own_checkout",
    "run-tree-exclude-dropped": "B4RunTree.test_the_walk_s_own_checkout",
    "fixture-stage01-unchecked": "B5Fixture.test_a_project_fixture_off_its_branch_is_refused",
    "fixture-source-unchecked": "B5Fixture.test_a_source_the_build_did_not_make_is_refused",
    "fixture-nothing-admitted": "B5Fixture.test_a_project_fixture_off_its_branch_is_refused",
    "row-slot-not-walk": "B6Row.test_the_design_s_row_as_a_walk_row",
    "row-version-kept": "B6Row.test_the_design_s_row_as_a_walk_row",
    "production-runtime-filled": "B7Production.test_production_leaves_exactly_these_missing",
    "missing-absent-silent": "B7Production.test_missing_names_absent_and_unknown",
    "cli-runs-with-gaps": "B7Production.test_main_refuses_by_name_before_anything",
    "pin-never-present": "B8Present.test_a_measured_pin_is_present",
    "main-ignores-builders": "B9Cli.test_one_walk_end_to_end",
    "held-tree-removed": "B9Cli.test_a_held_walk_keeps_its_run_tree",
    "held-exits-zero": "B9Cli.test_a_held_walk_keeps_its_run_tree",
    "refused-tree-left": "B9Cli.test_a_refused_fixture_removes_its_run_tree",
}
WITNESSES = {name: (METHOD[name], m[0]) for name, m in mutants().items()}

# Generated mutants this module does not kill that are equivalent, each with a reason a reviewer can check.
# `--generated-mutants` fails on a survivor not listed here and on a listed one that is killed; G1 fails on an entry
# that names no generated mutant or gives no reason.
EQUIVALENT: dict = {
    # athena run gap4-w12b-bc66fdf-20261013T101052Z, shard 16:
    "walk_builders.remove_run_tree:delete:L6:C4:e3e767f5":
        "the function's last statement `return None`; deleted, the function falls off its end and returns None",
}


def compile_module(name: str, source: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(HERE / f"{name}.py")
    sys.modules[name] = mod
    exec(compile(source, mod.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


def setUpModule():
    tbi.setUpModule()
    MODS["drive"] = tbi.drive
    if SELECTED is not None:
        _, target, old, new = mutants()[SELECTED]
        text = (HERE / f"{target}.py").read_text()
        assert text.count(old) == 1, f"witness {SELECTED}: its anchor occurs {text.count(old)} times"
        MODS[target] = compile_module(target, text.replace(old, new))
    if GENERATED is not None:
        m = by_id()[GENERATED]
        MODS[m.module] = compile_module(m.module, m.source((HERE / f"{m.module}.py").read_text()))
    for name in TARGETS:
        if name not in MODS:
            try:
                MODS[name] = __import__(name)
            except ImportError:            # a module the slice must provide: its absence is a red by assertion
                MODS[name] = types.SimpleNamespace()


def tearDownModule():
    if SELECTED is not None or GENERATED is not None:
        for name in TARGETS:
            sys.modules.pop(name, None)       # a compiled witness never outlives this module
    tbi.tearDownModule()


class Case(unittest.TestCase):
    def must(self, clause, fn, *args, **kwargs):
        """fn(*args, **kwargs), or a failure of `clause` naming what it raised (a red by assertion, never an error)."""
        try:
            return fn(*args, **kwargs)
        except AssertionError:
            raise
        except (Exception, SystemExit) as e:  # noqa: BLE001
            self.fail(f"{clause}: {type(e).__name__}: {str(e)[:400]}")

    def refuses(self, clause, words, fn, *args, **kwargs):
        """fn refuses with walk_builders.BuilderRefused carrying `words` (a red by assertion otherwise)."""
        wb = MODS["walk_builders"]
        kind = getattr(wb, "BuilderRefused", None)
        self.assertIsNotNone(kind, f"{clause}: walk_builders has no BuilderRefused")
        try:
            fn(*args, **kwargs)
        except kind as e:
            self.assertIn(words, str(e), f"{clause}: refused for another reason: {e}")
            return str(e)
        except Exception as e:  # noqa: BLE001
            self.fail(f"{clause}: raised {type(e).__name__}, not BuilderRefused: {str(e)[:300]}")
        self.fail(f"{clause}: not refused ({words!r})")


def wb():
    """The module under test; while it is absent (the red run on the base), a failure by assertion, never an error."""
    mod = MODS["walk_builders"]
    if not hasattr(mod, "cli"):
        raise AssertionError("w12b: walk_builders.py, the module under test, is absent")
    return mod


class Drafted(Case):
    """A case that reads the real draft (the session namespace a walk's session id is derived in): test_box_integration
    stands prereg.load in for drive.py's import, so each test here puts the real reader back for itself."""

    def setUp(self):
        import prereg
        self.enterContext(mock.patch.object(prereg, "load", tww.REAL_LOAD))


def walk_sid(walk: str) -> str:
    """Ruling D2, recomputed here from the ruling's words, never read from the module under test."""
    return str(uuid.uuid5(takes.namespace(), "walk/" + walk))


def scratch(name: str) -> Path:
    path = Path(tempfile.mkdtemp(prefix=name + "-", dir=tbi.SCRATCH)).resolve()
    return path


def login_file(text: str, mode=0o600, folder=None) -> Path:
    path = (folder or scratch("login")) / "login.env"
    path.write_bytes(text.encode("latin-1") if isinstance(text, str) else text)
    os.chmod(path, mode)
    return path


GARS = "8a54e0f8cd91caf558d0d168f1b87e36d0bc0b74"


# ------------------------------------------------------------------------------------------------- B1
class B1Identity(Drafted):
    def ident(self, walk="w-0001", **over):
        kw = dict(source="/synthetic/run-tree/data/staging/run-x/src", fixture={"sha256": "a" * 64},
                  gars_tree_sha=GARS)
        kw.update(over)
        return wb().walk_identity(walk, **kw)

    def test_the_identity_is_the_walks_own(self):
        fixture = {"sha256": "a" * 64}
        got = self.must("B1.identity", self.ident, fixture=fixture)
        self.assertEqual(tuple(got), tuple(MODS["drive"].IDENTITY_KEYS), "B1.identity: not exactly IDENTITY_KEYS")
        self.assertEqual(got["session_id"], walk_sid("w-0001"), "B1.identity: the session is not D2's")
        self.assertEqual((got["row"], got["row_commit"]), (None, None), "B1.identity: a walk has no ledger row")
        self.assertEqual((got["source"], got["fixture"], got["gars_tree_sha"]),
                         ("/synthetic/run-tree/data/staging/run-x/src", fixture, GARS), "B1.identity")
        fixture["sha256"] = "b" * 64
        self.assertEqual(got["fixture"], {"sha256": "a" * 64}, "B1.identity: the fixture record is not a copy")
        drive = MODS["drive"]
        probe = types.SimpleNamespace(identity_for=self.must("B1.identity", wb().identity_for, {"w-0001": got}))
        self.must("B1.identity", drive.walk_identity_problems, probe, {"walk": "w-0001"})
        other = types.SimpleNamespace(identity_for=lambda row: got)
        with self.assertRaises(drive.LaunchRefused, msg="B1.identity: another walk's identity admitted"):
            drive.walk_identity_problems(other, {"walk": "w-0002"})

    def test_a_bad_source_is_refused(self):
        for source in ("relative/src", "/a/../b/src", "/a//b", None):
            with self.subTest(source=source):
                self.refuses("B1.identity", "absolute, normalised", self.ident, source=source)

    def test_a_missing_fixture_or_tree_is_refused(self):
        for fixture in ({}, None, ["sha256"]):
            with self.subTest(fixture=fixture):
                self.refuses("B1.identity", "fixture builder's record", self.ident, fixture=fixture)
        for tree in (GARS[:39], GARS.upper(), "g" * 40, None, GARS + "0"):
            with self.subTest(tree=tree):
                self.refuses("B1.identity", "40-hex tree id", self.ident, gars_tree_sha=tree)

    def test_identity_for_hands_a_copy_of_its_own_walk_only(self):
        got = self.must("B1.identity", self.ident)
        fn = self.must("B1.identity", wb().identity_for, {"w-0001": got})
        first = self.must("B1.identity", fn, {"walk": "w-0001"})
        first["row"] = 7
        self.assertEqual(self.must("B1.identity", fn, {"walk": "w-0001"})["row"], None, "B1.identity: not a copy")
        self.refuses("B1.identity", "no identity was prepared for walk 'w-0002'", fn, {"walk": "w-0002"})
        self.refuses("B1.identity", "no identity was prepared for walk None", fn, ["w-0001"])


# ------------------------------------------------------------------------------------------------- B2
class B2Login(Case):
    def good(self, value=tbi.TOKEN) -> Path:
        return login_file(f"{LOGIN}={value}\n")

    def test_only_the_name_is_read(self):
        path = self.good()
        reads, closes = [], []
        real_read, real_close = os.read, os.close
        with mock.patch.object(os, "read", lambda fd, n: reads.append(n) or real_read(fd, n)), \
                mock.patch.object(os, "close", lambda fd: closes.append(fd) or real_close(fd)):
            got = self.must("B2.login", wb().login_file_by_name, str(path), "claude-code")
        self.assertEqual(got, str(path), "B2.login: the reader hands back the path, nothing read from it")
        self.assertEqual(reads, [len(LOGIN) + 1], "B2.login: read more than the name and its '='")
        self.assertEqual(len(closes), 1, "B2.login: the file was not closed")
        odd = login_file(LOGIN.encode() + b"=\xff\xfe not a value at all")
        self.assertEqual(self.must("B2.login", wb().login_file_by_name, str(odd), "claude-code"), str(odd),
                         "B2.login: the value was read (a value that is not text refused)")

    def test_each_placement_rule_refuses(self):
        good = self.good()
        self.refuses("B2.login", "absolute path", wb().login_file_by_name, "login.env", "claude-code")
        self.refuses("B2.login", "absolute path", wb().login_file_by_name, None, "claude-code")
        self.refuses("B2.login", "does not exist", wb().login_file_by_name, str(good) + ".gone", "claude-code")
        link = good.parent / "link.env"
        link.symlink_to(good)
        self.refuses("B2.login", "regular file, never a link", wb().login_file_by_name, str(link), "claude-code")
        self.refuses("B2.login", "regular file, never a link", wb().login_file_by_name, str(good.parent),
                     "claude-code")
        loose = login_file(f"{LOGIN}={tbi.TOKEN}\n", mode=0o644)
        self.refuses("B2.login", "mode must be 600", wb().login_file_by_name, str(loose), "claude-code")
        with mock.patch.object(os, "getuid", lambda: os.geteuid() + 1):
            self.refuses("B2.login", "owned by the reading user", wb().login_file_by_name, str(good), "claude-code")
        with tbi.scratch_repo() as repo:
            inside = login_file(f"{LOGIN}={tbi.TOKEN}\n", folder=repo)
            self.refuses("B2.login", "outside every repository", wb().login_file_by_name, str(inside), "claude-code")
        with mock.patch.object(os, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("synthetic"))):
            self.refuses("B2.login", "cannot be opened", wb().login_file_by_name, str(good), "claude-code")
        self.refuses("B2.login", "no login variable", wb().login_file_by_name, str(good), "stub")

    def test_a_file_swapped_after_the_check_is_refused(self):
        """W12B-R1-1: the path is checked by lstat, then something else stands there when it is opened (lstat patched
        to answer the checked file's stat): a regular file of another inode and mode is refused by the descriptor's
        fstat; a link by O_NOFOLLOW; a FIFO opens without blocking (O_NONBLOCK) and is refused by the fstat."""
        good = self.good()
        checked = os.lstat(good)
        real_lstat, real_open = os.lstat, os.open
        other = login_file(f"{LOGIN}={tbi.TOKEN}\n", mode=0o644)
        link = good.parent / "swapped-link.env"
        link.symlink_to(good)
        fifo = good.parent / "swapped-fifo.env"
        os.mkfifo(fifo, 0o600)
        flags = []

        def opener(path, fl, *a, **k):
            flags.append(fl)
            if not fl & os.O_NONBLOCK:
                raise OSError("synthetic: an open without O_NONBLOCK would block on a FIFO")
            return real_open(path, fl, *a, **k)
        for path, words in ((other, "changed between its check and its read"), (link, "cannot be opened"),
                            (fifo, "changed between its check and its read")):
            with self.subTest(path=path.name), \
                    mock.patch.object(os, "lstat", lambda p, q=str(path): checked if p == q else real_lstat(p)), \
                    mock.patch.object(os, "open", opener):
                self.refuses("B2.login", words, wb().login_file_by_name, str(path), "claude-code")
        self.assertTrue(all(f & os.O_NOFOLLOW and f & os.O_NONBLOCK for f in flags) and flags,
                        f"B2.login: opened without O_NOFOLLOW or O_NONBLOCK: {flags}")

    def test_another_name_is_refused_without_its_value(self):
        for text in (f"CODEX_API_KEY={tbi.TOKEN}\n", f"{LOGIN[:-1]}={tbi.TOKEN}\n", LOGIN, f" {LOGIN}={tbi.TOKEN}\n",
                     ""):
            with self.subTest(text=text[:12]):
                path = login_file(text)
                said = self.refuses("B2.login", f"does not start with {LOGIN}=", wb().login_file_by_name, str(path),
                                    "claude-code")
                self.assertNotIn(tbi.TOKEN, said, "B2.login: a refusal carries the value")
        codex = login_file(f"CODEX_API_KEY={tbi.TOKEN}\n")
        self.assertEqual(self.must("B2.login", wb().login_file_by_name, str(codex), "codex"), str(codex),
                         "B2.login: the harness's own variable")

    def test_the_secrets_read_the_value_only_when_asked(self):
        from box import scan_record
        path = self.good()
        calls = []
        real = scan_record.read_login
        with mock.patch.object(scan_record, "read_login", lambda *a, **k: calls.append((a, k)) or real(*a, **k)):
            secrets = self.must("B2.login", wb().login_secrets, str(path), "claude-code")
            self.assertEqual(calls, [], "B2.login: the value was read before the scan asked")
            self.assertEqual(self.must("B2.login", secrets), [("token", tbi.TOKEN)], "B2.login")
        self.assertEqual(calls[0][0], (str(path), LOGIN), "B2.login: read under another name")
        self.assertEqual(set(calls[0][1]["allowed"]), set(rt.LOGIN_VARIABLE.values()), "B2.login")


# ------------------------------------------------------------------------------------------------- B3
def cgroup(memory="low 0\nhigh 0\nmax 0\noom 1\noom_kill 2\n", pids="max 3\n") -> Path:
    folder = scratch("cgroup")
    if memory is not None:
        (folder / "memory.events").write_text(memory)
    if pids is not None:
        (folder / "pids.events").write_text(pids)
    return folder


class B3Counters(Case):
    def test_the_take_s_own_counters(self):
        folder, take, seen = cgroup(), object(), []
        fn = self.must("B3.counters", wb().counters_reader, lambda t: seen.append(t) or str(folder))
        self.assertEqual(self.must("B3.counters", fn, take), {"oom_kill": 2, "pids_max": 3}, "B3.counters")
        self.assertEqual(seen, [take], "B3.counters: the folder was not asked for this take")

    def test_a_bad_folder_is_refused(self):
        self.refuses("B3.counters", "must be callable", wb().counters_reader, "/not/callable")
        here = os.path.relpath(str(cgroup()))        # athena W12B sweep: a relative folder that exists
        for folder in (None, "relative/cgroup", here, str(tbi.SCRATCH / "no-such-cgroup"), 7):
            with self.subTest(folder=folder):
                fn = self.must("B3.counters", wb().counters_reader, lambda t, f=folder: f)
                self.refuses("B3.counters", "absolute, existing folder", fn, object())

    def test_a_missing_counter_is_never_zero(self):
        fn = self.must("B3.counters", wb().counters_reader, lambda t: str(cgroup(pids=None)))
        with self.assertRaises(rt.Refused, msg="B3.counters: a missing counter read as a value"):
            fn(object())


# ------------------------------------------------------------------------------------------------- B4
@contextlib.contextmanager
def origin():
    """A scratch origin repository: one commit holding a README, src/ and evals/ (which the checkout leaves out)."""
    with tbi.scratch_repo() as repo:
        (repo / "src").mkdir()
        (repo / "src" / "a.txt").write_text("synthetic source\n")
        (repo / "evals").mkdir()
        (repo / "evals" / "hidden.txt").write_text("synthetic study file\n")
        tbi.git(repo, "add", "-A")
        tbi.git(repo, "commit", "-q", "-m", "A synthetic origin")
        yield repo, tbi.git(repo, "rev-parse", "HEAD")


@contextlib.contextmanager
def temp_root():
    """The machine's temporary folder, inside the scratch folder for this test (drive.run_tree_path reads it)."""
    folder = scratch("tmp")
    with mock.patch.object(tempfile, "tempdir", str(folder)):
        yield folder


class B4RunTree(Drafted):
    def test_the_walk_s_own_checkout(self):
        with origin() as (repo, sha), temp_root() as tmp:
            tree = self.must("B4.run-tree", wb().build_run_tree, "w-0001", repo=repo, commit=sha, exclude=["evals"])
            drive = MODS["drive"]
            self.assertIsInstance(tree, Path, "B4.run-tree: no checkout handed back")
            self.assertEqual(Path(tree), tmp.resolve() / drive.neutral_name(walk_sid("w-0001")),
                             "B4.run-tree: not the walk's own checkout")
            self.assertTrue((Path(tree) / "src" / "a.txt").is_file(), "B4.run-tree: the origin was not exported")
            self.assertFalse((Path(tree) / "evals").exists(), "B4.run-tree: an excluded path is in the checkout")
            self.assertEqual(tbi.git(tree, "rev-list", "--all", "--count"), "1", "B4.run-tree")
            self.assertEqual(tbi.git(tree, "log", "-1", "--format=%s"), drive.TREE_SUBJECT, "B4.run-tree")
            self.assertEqual((tbi.git(tree, "remote"), tbi.git(tree, "status", "--porcelain")), ("", ""),
                             "B4.run-tree")
            self.refuses("B4.run-tree", "already exists", wb().build_run_tree, "w-0001", repo=repo, commit=sha,
                         exclude=["evals"])
            self.assertTrue((Path(tree) / "src" / "a.txt").is_file(), "B4.run-tree: a refused rebuild touched it")

    def test_an_unknown_commit_leaves_nothing(self):
        with origin() as (repo, sha), temp_root() as tmp:
            self.refuses("B4.run-tree", "was not built", wb().build_run_tree, "w-0001", repo=repo, commit="0" * 40,
                         exclude=["evals"])
            self.assertEqual(list(tmp.iterdir()), [], "B4.run-tree: a failed build left its checkout")

    def test_malformed_inputs_build_nothing(self):
        with origin() as (repo, sha), temp_root() as tmp:
            for commit in (sha[:12], sha.upper(), None):
                self.refuses("B4.run-tree", "40-hex commit id", wb().build_run_tree, "w-0001", repo=repo,
                             commit=commit, exclude=["evals"])
            for exclude in ("evals", ["/evals"], [""], [None], [7], None):
                self.refuses("B4.run-tree", "list of relative paths", wb().build_run_tree, "w-0001", repo=repo,
                             commit=sha, exclude=exclude)
            self.assertEqual(list(tmp.iterdir()), [], "B4.run-tree: a refused build made something")

    def test_remove_run_tree_says_why(self):
        folder = scratch("tree")
        (folder / "f").write_text("x")
        self.assertIsNone(self.must("B4.run-tree", wb().remove_run_tree, folder), "B4.run-tree")
        self.assertFalse(folder.exists(), "B4.run-tree: not removed")
        with mock.patch.object(shutil, "rmtree", lambda p: (_ for _ in ()).throw(OSError("synthetic"))):
            said = self.must("B4.run-tree", wb().remove_run_tree, folder)
        self.assertIn(str(folder), said or "", "B4.run-tree: a failed removal says nothing")


# ------------------------------------------------------------------------------------------------- B5
def draft_row(task, half, arm="A") -> dict:
    import prereg
    with mock.patch.object(prereg, "load", tww.REAL_LOAD):
        rows = prereg.load()["rows"]
    return json.loads(json.dumps(next(r for r in rows if (r["task"], r["half"], r["arm"]) == (task, half, arm))))


@contextlib.contextmanager
def generator(*, sha=None, line=None, rc=0, make_source=True, make_project=True):
    """The fixture generators as subprocess sees them, replaced by a stand-in (the guard never starts the real ones):
    a generated fixture writes <out>/src and the manifest with `sha` (default: the half's pin); a project fixture
    prints `line` first and makes <workspace>/projects/<name> and <staging>/<name>/src. Any other process goes to the
    guard."""
    gate = subprocess.run

    def fake(args, *a, **kw):
        argv = [str(x) for x in args] if isinstance(args, (list, tuple)) else []
        if not argv or argv[0] != sys.executable:
            return gate(args, *a, **kw)
        opt = {argv[i]: argv[i + 1] for i in range(2, len(argv) - 1) if argv[i].startswith("--")}
        if "--manifest-out" in opt:
            if make_source:
                Path(opt["--out"], "src").mkdir(parents=True, exist_ok=True)
            Path(opt["--manifest-out"]).write_text(json.dumps({"fixture_sha256": sha}))
            if rc and kw.get("check"):
                raise subprocess.CalledProcessError(rc, args)
            return subprocess.CompletedProcess(args, rc, "", "")
        if make_project:
            Path(opt["--workspace"], "projects", opt["--name"]).mkdir(parents=True, exist_ok=True)
            Path(opt["--staging"], opt["--name"], "src").mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(args, rc, (line or "") + "\n", "")
    with mock.patch.object(subprocess, "run", fake):
        yield


def pin(task, half) -> str:
    return variants.load_task(task)["halves"][half]["fixture"]["sha256"]


class B5Fixture(Case):
    def built(self, row, **kw):
        tree = scratch("run-tree")
        with generator(**kw):
            return tree, self.must("B5.fixture", wb().build_walk_fixture, row, tree, "run-0000abcd")

    def test_a_generated_fixture_and_its_source(self):
        row = draft_row("scope-read", "trap")
        tree, (record, source) = self.built(row, sha=pin("scope-read", "trap"))
        spec = variants.load_task("scope-read")["halves"]["trap"]["fixture"]
        self.assertEqual(record, {"kind": "generated", "variant": spec["variant"], "seed": spec["seed"],
                                  "fixture_sha256": spec["sha256"]}, "B5.fixture")
        self.assertEqual(source, str(tree / "data" / "staging" / "run-0000abcd" / "src"), "B5.fixture")
        self.assertTrue(Path(source).is_dir(), "B5.fixture")

    def test_a_generated_fixture_off_its_pin_or_failing_is_refused(self):
        row = draft_row("scope-read", "trap")
        for kw, words in (({"sha": "0" * 64}, "was not built: SystemExit"),
                          ({"sha": pin("scope-read", "trap"), "rc": 1}, "was not built: CalledProcessError")):
            with self.subTest(kw=kw), generator(**kw):
                self.refuses("B5.fixture", words, wb().build_walk_fixture, row, scratch("run-tree"), "run-0000abcd")

    def test_a_source_the_build_did_not_make_is_refused(self):
        row = draft_row("scope-read", "trap")
        with generator(sha=pin("scope-read", "trap"), make_source=False):
            self.refuses("B5.fixture", "did not make the source", wb().build_walk_fixture, row, scratch("run-tree"),
                         "run-0000abcd")

    def test_a_project_fixture_reaching_its_branch(self):
        row = draft_row("precondition-refusal", "trap")
        variant = variants.load_task("precondition-refusal")["halves"]["trap"]["fixture"]["variant"]
        tree, (record, source) = self.built(row, line=f"{variant}: stage 01 --check exits 1 (expected 1)")
        self.assertEqual((record["kind"], record["variant"], record["stage01_check_exit"],
                          record["stage01_expected_exit"]), ("project", variant, 1, 1), "B5.fixture")
        self.assertEqual(source, str(tree / "gars" / "projects" / "run-0000abcd"), "B5.fixture")

    def test_a_project_fixture_off_its_branch_is_refused(self):
        row = draft_row("precondition-refusal", "trap")
        for kw, words in (({"line": "x: stage 01 --check exits 0 (expected 1)"}, "exit is 0, not the 1"),
                          ({"line": "x: the line drive.py cannot parse"}, "exit is None"),
                          ({"line": "x: exits 1 (expected 1)", "rc": 1}, "was not built (the builder said why"),
                          ({"line": "x: exits 1 (expected 1)", "make_project": False}, "was not built")):
            with self.subTest(kw=kw), generator(**kw):
                self.refuses("B5.fixture", words, wb().build_walk_fixture, row, scratch("run-tree"), "run-0000abcd")

    def test_another_variant_is_refused(self):
        row = draft_row("precondition-refusal", "trap")
        drive = MODS["drive"]
        made = {"kind": "project", "variant": "samplesheet-present", "seed": 1, "stage01_check_exit": 1,
                "stage01_expected_exit": 1}
        with mock.patch.object(drive, "build_take_fixture", lambda fx, tree, name: (made, tree)):
            self.refuses("B5.fixture", "not this half's", wb().build_walk_fixture, row, scratch("run-tree"),
                         "run-0000abcd")

    def test_an_exit_that_is_not_a_whole_number_is_refused(self):
        """Each exit must be an int on its own: 1.0 equals 1, and is still not an exit code stage 01 printed."""
        row = draft_row("precondition-refusal", "trap")
        variant = variants.load_task("precondition-refusal")["halves"]["trap"]["fixture"]["variant"]
        drive = MODS["drive"]
        for got, want in ((1.0, 1), (1, 1.0), ("1", "1")):
            made = {"kind": "project", "variant": variant, "seed": 1, "stage01_check_exit": got,
                    "stage01_expected_exit": want}
            with self.subTest(got=got, want=want), \
                    mock.patch.object(drive, "build_take_fixture", lambda fx, tree, name, m=made: (m, tree)):
                self.refuses("B5.fixture", "stage 01 exit", wb().build_walk_fixture, row, scratch("run-tree"),
                             "run-0000abcd")


# ------------------------------------------------------------------------------------------------- B6
class B6Row(Case):
    def test_the_design_s_row_as_a_walk_row(self):
        import prereg
        with mock.patch.object(prereg, "load", tww.REAL_LOAD):
            rows = prereg.load()["rows"]
        before = json.dumps(rows)
        first = next(r for r in rows if r["task"] == "scope-read" and r["arm"] == "A")
        cell = {k: first[k] for k in ("task", "half", "wording", "arm", "model")}
        got = self.must("B6.row", wb().walk_row, "w-0001", cell, "9.9.9-synthetic", rows)
        self.assertEqual((got["walk"], got["slot"]), ("w-0001", "w-0001"), "B6.row: a walk's slot is its id")
        self.assertEqual(got["agent"], {"harness": first["agent"]["harness"], "version": "9.9.9-synthetic"}, "B6.row")
        self.assertEqual({k: v for k, v in got.items() if k not in ("walk", "slot", "agent")},
                         {k: v for k, v in first.items() if k not in ("slot", "agent")}, "B6.row: not the design's")
        self.assertEqual(json.dumps(rows), before, "B6.row: the design's rows were changed")

    def test_the_whole_cell_picks_the_row(self):
        rows = [{"task": "t", "half": "trap", "wording": "w1", "arm": "A", "model": m, "repeat": 1,
                 "agent": {"harness": "claude-code", "version": None}} for m in ("m-other", "m-want")]
        for k in ("task", "half", "wording", "arm"):
            rows.insert(0, dict(rows[-1], **{k: "other"}, repeat=9))
        got = self.must("B6.row", wb().walk_row, "w-1", {"task": "t", "half": "trap", "wording": "w1", "arm": "A",
                                                           "model": "m-want"}, "v1", rows)
        self.assertEqual((got["model"], got["repeat"]), ("m-want", 1), "B6.row: another cell's row")

    def test_a_cell_the_design_lacks_or_no_version_is_refused(self):
        rows = [{"task": "t", "half": "trap", "wording": "w1", "arm": "A", "model": "m",
                 "agent": {"harness": "claude-code", "version": None}}]
        cell = {"task": "t", "half": "trap", "wording": "w1", "arm": "A", "model": "m"}
        self.refuses("B6.row", "not a row of the design", wb().walk_row, "w-1", dict(cell, wording="w2"), "v1", rows)
        for version in ("", None, 5):
            self.refuses("B6.row", "agent version", wb().walk_row, "w-1", cell, version, rows)


# ------------------------------------------------------------------------------------------------- B7
def run_main(argv, builders=None) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            kw = {} if builders is None else {"builders": builders}
            code = MODS["walk_runner"].main(argv, **kw)
    except BaseException as e:
        e.captured = (out.getvalue(), err.getvalue())     # what was printed before it raised
        raise
    return code, out.getvalue(), err.getvalue()


ARGV = ["--walk", "w-0001", "--task", "scope-read", "--half", "trap", "--wording", "w3", "--arm", "A", "--model",
        "claude-opus-5-5", "--reason", "synthetic: a CLI walk of the tests"]


class B7Production(Case):
    def test_production_leaves_exactly_these_missing(self):
        got = self.must("B7.production", wb().production_builders)
        gaps = self.must("B7.production", wb().missing, got)
        self.assertEqual([n for n, _ in gaps], EXPECTED_MISSING, "B7.production: not exactly the missing values")
        self.assertTrue(all(isinstance(why, str) and len(why) > 20 for _, why in gaps), "B7.production")
        why = dict(gaps)
        for name, words in (("runtime", "DockerRuntime"), ("proxy", "next-slices plan item 4"), ("uid_map", rt.CALLER_PENDING["uid_map"]),
                            ("cgroup_dir_for", rt.CALLER_PENDING["cgroup_dir"]), ("login_path", "walk token"),
                            ("design_for", "PENDING"), ("run_tree_exclude", "run_location"),
                            ("agent_version", "version_pins"), ("rules_scanner", "gitleaks")):
            self.assertIn(words, why[name], f"B7.production: {name} does not say why")
        import time
        import drive
        import routing
        self.assertEqual((got["clock"], got["sleep"]), (time.time, time.sleep), "B7.production")
        self.assertEqual(got["run_tree_origin"], (drive.REPO, variants.PINNED_TREE), "B7.production")
        self.assertEqual(got["table"], routing.load_table(), "B7.production")
        self.assertTrue(callable(got["pin_for"]), "B7.production: CP5's registered pins are not handed to the walks")
        if OWNERSHIP_ON_TREE:
            self.assertIs(got["ownership"], drive._ownership, "B7.production: the ownership road is not the box's")
        else:
            self.assertIn("box/ownership.py", why["ownership"], "B7.production: ownership does not say why")
        if SETTINGS_GUARD_ON_TREE:
            self.assertIs(got["settings_guard"], drive._settings_guard, "B7.production: the guard is not the box's")
        else:
            self.assertIn("box/settings_guard.py", why["settings_guard"], "B7.production: the guard does not say why")
        self.assertEqual(sorted(got), sorted(wb().NAMES), "B7.production: the set is not NAMES")

    def test_main_refuses_by_name_before_anything(self):
        for argv in ([], ARGV, ["--no-such-flag"]):
            with self.subTest(argv=argv[:1]), temp_root() as tmp:
                code, out, err = self.must("B7.production", run_main, argv)
                self.assertEqual(code, 2, "B7.production: not refused")
                named = re.findall(r"^refused: missing (\w+): ", err, re.M)
                self.assertEqual(named, EXPECTED_MISSING, f"B7.production: {err[:600]}")
                self.assertIn("Q-w7b-3", err, "B7.production")
                self.assertEqual(err.strip().splitlines()[-1], f"refused: {MODS['walk_runner'].CLI_REFUSAL}",
                                 "B7.production: the refusal line is not the last line")
                self.assertEqual((out, list(tmp.iterdir())), ("", []), "B7.production: something was built")

    def test_an_unreadable_table_is_refused_by_name(self):
        """W12B-R1-3: routing.json that load_table refuses is a refusal by name (exit 2), never a traceback."""
        import routing

        def unreadable():
            raise routing.TableError("synthetic: the table cannot be read")
        with mock.patch.object(routing, "load_table", unreadable):
            code, out, err = self.must("B7.production", run_main, ARGV)
        self.assertEqual(code, 2, "B7.production: not refused")
        self.assertIn("refused: the production builders cannot be read: TableError: synthetic", err, "B7.production")
        self.assertIn("Q-w7b-3", err, "B7.production")
        self.assertEqual(err.strip().splitlines()[-1], f"refused: {MODS['walk_runner'].CLI_REFUSAL}",
                         "B7.production: the refusal line is not the last line")

    def test_missing_names_absent_and_unknown(self):
        full = {n: object() for n in wb().NAMES}
        self.assertEqual(self.must("B7.production", wb().missing, full), [], "B7.production")
        partial = {n: v for n, v in full.items() if n not in ("proxy", "clock")}
        partial["uid_map"] = wb().Missing("synthetic: measured later")
        partial["hosts"] = None
        partial["extra"] = object()
        self.assertEqual(self.must("B7.production", wb().missing, partial),
                         [("proxy", "absent from the builder set"), ("hosts", "present but None"),
                          ("uid_map", "synthetic: measured later"),
                          ("clock", "absent from the builder set"), ("extra", "not a builder the command line knows")],
                         "B7.production")
        for why in ("", "   ", None):
            with self.assertRaises(TypeError, msg="B7.production: a Missing without its reason"):
                wb().Missing(why)
        self.assertEqual(repr(wb().Missing("x y")), "Missing('x y')", "B7.production")


# ------------------------------------------------------------------------------------------------- B8
class B8Present(Drafted):
    def test_a_measured_pin_is_present(self):
        import routing
        table = tww.the_table()
        with mock.patch.object(routing, "load_table", lambda: table):
            got = self.must("B8.present", wb().production_builders)
        row = tww.the_row()
        self.assertTrue(callable(got["pin_for"]), "B8.present: a filled pin is still missing")
        self.assertEqual(self.must("B8.present", got["pin_for"], row), batch.expected_pin(row, table), "B8.present")

    def test_measured_constants_give_the_design_view(self):
        import check_take
        import routing
        table = tww.the_table()
        constants = tww.walk_constants(check_take, MODS["drive"])
        with mock.patch.object(routing, "load_table", lambda: table), \
                mock.patch.object(check_take, "CHECKER_CONSTANTS", constants), \
                mock.patch.object(check_take, "design_view", lambda row, **kw: ("view", row["task"], kw)):
            got = self.must("B8.present", wb().production_builders)
        self.assertTrue(callable(got["design_for"]), "B8.present: filled constants are still missing")
        row = tww.the_row()
        with mock.patch.object(check_take, "design_view", lambda row, **kw: ("view", row["task"], kw)):
            view = self.must("B8.present", got["design_for"], row, "/synthetic/tree")
        self.assertEqual(view, ("view", row["task"], {"pin": batch.expected_pin(row, table),
                                                      "run_tree": "/synthetic/tree"}), "B8.present")

    def test_a_real_rules_scanner_is_present(self):
        from box import scan_record
        scanner = object()
        with mock.patch.object(scan_record, "pending", lambda: {}), \
                mock.patch.object(scan_record, "real_rules_scanner", lambda: scanner):
            got = self.must("B8.present", wb().production_builders)
        self.assertIs(got["rules_scanner"], scanner, "B8.present")


# ------------------------------------------------------------------------------------------------- B9
def sidecar_for(row, ev, tree):
    """test_walk_wiring's fake sidecar launch, over the walk's own run tree."""
    from box import sidecar as sc
    expect = {"user": sc.WATCHER_USER, "network_mode": "none", "cap_drop": ["ALL"],
              "cap_add": ["CAP_DAC_READ_SEARCH"], "security_opt": ["no-new-privileges"], "privileged": False,
              "pid_mode": "", "mounts": [{"source": tree, "destination": tree, "rw": False},
                                         {"source": ev, "destination": sc.EVIDENCE_MOUNT, "rw": True}]}
    return rt.SidecarLaunch(
        create_argv=("docker", "create", "--network", "none", "--label", "ev=" + ev, "--label", "tree=" + tree,
                     "side-image"),
        start_argv_for=lambda i: ["docker", "start", i],
        ctl_argv_for=lambda i, c, label=None: ["docker", "exec", i, "python3", "-I", "-B", "/opt/w/sidecar.py",
                                               "ctl", c] + ([label] if label else []),
        rm_argv_for=lambda i: ["docker", "rm", "--force", i], expect=expect)


class FakeWorld:
    """One scratch study (the draft, tasks/ and rehearsals/ committed), an origin repository for the run tree, and a
    builder set over test_walk_wiring's session box: every value the command line needs, as TEST DATA."""

    def __init__(self, ct, root: Path, origin_repo: Path, sha: str, tmp: Path):
        drive = MODS["drive"]
        self.ct, self.root, self.tmp = ct, root, tmp
        self.row = tww.the_row()
        self.table = tww.the_table()
        self.constants = tww.walk_constants(ct, drive)
        script = self.design_for(self.row, None).script
        self.box = tww.SessionBox(script, self.row["model"])
        self.clock = tbi.Clock()
        self.box.clock = self.clock
        self.box.evidence = self.watching_planted(self.box.evidence)
        self.cfg_parent = scratch("cfg")
        self.login = login_file(f"{LOGIN}={tbi.TOKEN}\n")
        self.cgroup = cgroup(memory="oom_kill 0\n", pids="max 0\n")
        self.builders = {
            "runtime": self.box, "config_parent": str(self.cfg_parent),
            "take_spec": lambda row, cfg, tree: rt.TakeSpec(
                image=tbi.IMAGE, run_tree=tree, config_dir=cfg, network=tbi.PLACEHOLDER_NET,
                memory_reservation=512 * 2 ** 20, memory=3 * 512 * 2 ** 20, cpus="2", pids_limit=256),
            "sidecar_for": sidecar_for,
            "proxy": rt.ProxyLaunch(image="sha256:" + "9" * 64, conf_source=str(tbi.SCRATCH / "proxy.conf"),
                                    conf_target="/etc/squid/x.conf", command=("squid", "-N"), user="13:13",
                                    alias="proxy"),
            "lock_path": str(tbi.SCRATCH / "synthetic.lock"), "hosts": {"api": "synthetic.invalid"},
            "uid_map": tbi.UID_MAP, "cgroup_dir_for": lambda take: str(self.cgroup),
            "rules_scanner": lambda paths: [], "login_path": str(self.login), "agent_version": tww.CC_VERSION,
            "table": self.table, "pin_for": self.pin_for, "design_for": self.design_for,
            "budgets": (600, tbi.CAP_S, tbi.POLL_S), "run_tree_origin": (origin_repo, sha),
            "run_tree_exclude": ["evals"], "clock": self.clock, "sleep": self.clock.sleep,
            "ownership": tbi.FakeOwnership(self.box), "settings_guard": tbi.FakeSettingsGuard(),
        }

    def pin_for(self, row):
        return batch.expected_pin(row, self.table)

    def design_for(self, row, run_tree):
        return self.ct.design_view(row, pin=self.pin_for(row), run_tree=run_tree, constants=self.constants)

    def watching_planted(self, evidence):
        """The fake sidecar's evidence with watched.json listing the half's planted paths (what the v4 grader reads),
        as test_walk_runner's R9 does."""
        def ev(sid, label):
            drive = MODS["drive"]
            row = self.row
            project = drive.neutral_name(walk_sid(self.current))
            planted = variants.grader_spec(row["task"], row["half"], row["wording"], pressure=row["pressure"],
                                           project=project)["planted"]
            path = Path(self.box.containers[sid]["ev"]) / "watched.json"
            if not path.exists():
                path.write_text(json.dumps({"paths": sorted(set(planted))}))
            return evidence(sid, label)
        return ev

    current = "w-0001"

    def argv(self, walk="w-0001", **over) -> list:
        self.current = walk
        cell = {k: self.row[k] for k in ("task", "half", "wording", "arm", "model")}
        cell.update(over)
        out = ["--walk", walk]
        for k in ("task", "half", "wording", "arm", "model"):
            out += [f"--{k}", cell[k]]
        return out + ["--reason", f"synthetic: walk {walk} through the command line"]

    def main(self, argv, builders=None):
        drive = MODS["drive"]
        with tbi.spying(tbi.Spy()), mock.patch.object(drive._mode_binding, "HERE", self.root), \
                generator(sha=pin(self.row["task"], self.row["half"])):
            return run_main(argv, self.builders if builders is None else builders)

    def run_tree(self, walk="w-0001") -> Path:
        return self.tmp / MODS["drive"].neutral_name(walk_sid(walk))

    def walk_folder(self, walk="w-0001") -> Path:
        return self.root / "rehearsals" / walk


@contextlib.contextmanager
def fake_world():
    """test_walk_wiring's world before the freeze (takes.json holds no row), over a scratch study."""
    import mode_binding as mb
    with tww.world() as ct, \
            mock.patch.object(takes, "load_rows", lambda **kw: tww.REAL_LOAD_ROWS(**kw) if kw else []), \
            mock.patch.object(takes, "row_commits", lambda **kw: tww.REAL_ROW_COMMITS(**kw) if kw else {}), \
            tbi.scratch_repo() as root, origin() as (repo, sha), temp_root() as tmp:
        shutil.copy(HERE / "prereg-draft.json", root / "prereg-draft.json")
        shutil.copytree(HERE / "tasks", root / "tasks")
        (root / mb.WALKS_DIR).mkdir()
        (root / mb.WALKS_DIR / "README.md").write_text("synthetic\n")
        (root / mb.WALKS_DIR / "register.json").write_text('{\n  "schema": 1,\n  "walks": []\n}\n')
        tbi.git(root, "add", "-A")
        tbi.git(root, "commit", "-q", "-m", "A synthetic study skeleton")
        yield FakeWorld(ct, root, repo, sha, tmp)


def register(w) -> list:
    return json.loads((w.root / "rehearsals" / "register.json").read_text())["walks"]


class B9Cli(Case):
    def doc(self, out: str) -> dict:
        """The command line's one JSON output line (athena W12B sweep: a deleted print must fail by assertion)."""
        lines = out.strip().splitlines()
        self.assertTrue(lines, "B9.cli: the command line printed no output line")
        doc = self.must("B9.cli", json.loads, lines[-1])
        self.assertEqual(sorted(doc), ["results", "run_tree", "run_tree_kept", "walk"], f"B9.cli: {doc}")
        return doc

    def test_one_walk_end_to_end(self):
        with fake_world() as w:
            code, out, err = self.must("B9.cli", w.main, w.argv())
            self.assertEqual(code, 0, f"B9.cli: exit {code}: {err[-800:]} {out[-800:]}")
            doc = self.doc(out)
            self.assertEqual([r["state"] for r in doc["results"]], ["committed"], f"B9.cli: {doc}")
            self.assertEqual(doc["walk"], "w-0001", "B9.cli")
            self.assertEqual([(e["walk"], e["reason"], e["counted"]) for e in register(w)],
                             [("w-0001", "synthetic: walk w-0001 through the command line", False)], "B9.cli")
            folder = w.walk_folder()
            led = json.loads((folder / "driver-ledger.json").read_text())
            self.assertEqual((led["session_id"], led["row"], led["row_commit"]), (walk_sid("w-0001"), None, None),
                             "B9.cli: the walk's identity")
            self.assertEqual(led["fixture"], {"kind": "generated", "variant": "with-planted-qc", "seed": 20260908,
                                              "fixture_sha256": pin(w.row["task"], w.row["half"])}, "B9.cli")
            check = json.loads((folder / "check.json").read_text())
            self.assertEqual((check["checked"], check["route"], check["checker_reasons"]), (True, "graded", []),
                             f"B9.cli: {check}")
            grade = json.loads((folder / "grade.json").read_text())
            self.assertTrue(grade["graded"], f"B9.cli: {grade}")
            self.assertEqual(grade["grade"].get("graded_by"), "graders/scope_read.py", f"B9.cli: {grade}")
            self.assertEqual(doc["run_tree"], str(w.run_tree()), "B9.cli")
            self.assertEqual((doc["run_tree_kept"], w.run_tree().exists()), (None, False),
                             "B9.cli: the run tree was left behind")
            self.assertEqual(list(w.cfg_parent.iterdir()), [], "B9.cli: the config folder was left behind")
            self.assertFalse((w.root / "takes").exists(), "B9.cli: something was written under takes/")
            self.assertEqual(tbi.git(w.root, "status", "--porcelain"), "", "B9.cli")

    def nothing_built(self, w, clause="B9.cli"):
        self.assertEqual(list(w.tmp.iterdir()), [], f"{clause}: a run tree was left")
        self.assertFalse(w.walk_folder().exists(), f"{clause}: a walk folder was made")
        self.assertEqual(register(w), [], f"{clause}: something was registered")
        self.assertEqual(w.box.containers, {}, f"{clause}: a container was made")

    def test_a_missing_builder_is_named_and_nothing_built(self):
        with fake_world() as w:
            for name in ("runtime", "budgets", "run_tree_exclude"):
                for gap, words in ((None, "absent from the builder set"),
                                   (wb().Missing("synthetic: not yet"), "synthetic: not yet")):
                    builders = dict(w.builders)
                    if gap is None:
                        del builders[name]
                    else:
                        builders[name] = gap
                    code, out, err = self.must("B9.cli", w.main, w.argv(), builders)
                    self.assertEqual(code, 2, "B9.cli")
                    self.assertEqual(re.findall(r"^refused: missing (\w+): (.*)$", err, re.M), [(name, words)],
                                     f"B9.cli: {err[-400:]}")
            code, out, err = self.must("B9.cli", w.main, w.argv(), dict(w.builders, grade=lambda r, f: {}))
            self.assertEqual((code, re.findall(r"^refused: missing (\w+): ", err, re.M)), (2, ["grade"]), "B9.cli")
            self.nothing_built(w)

    def test_a_refused_row_or_login_builds_nothing(self):
        with fake_world() as w:
            for argv, words in ((w.argv(walk="a/b"), "not one path segment"),
                                (w.argv(walk="../w-0001"), "not one path segment"),
                                (w.argv(wording="w99"), "not a row of the design"),
                                (w.argv(arm="O", model="gpt-6.1-sol"), "admits only Claude Code")):
                code, out, err = self.must("B9.cli", w.main, argv)
                self.assertEqual(code, 2, f"B9.cli: {err[-300:]}")
                self.assertIn(words, err, "B9.cli")
            wrong = login_file(f"CODEX_API_KEY={tbi.TOKEN}\n")
            code, out, err = self.must("B9.cli", w.main, w.argv(), dict(w.builders, login_path=str(wrong)))
            self.assertEqual(code, 2, "B9.cli")
            self.assertIn(f"does not start with {LOGIN}=", err, "B9.cli")
            self.assertNotIn(tbi.TOKEN, err + out, "B9.cli: the value was printed")
            self.nothing_built(w)
            with self.assertRaises(SystemExit, msg="B9.cli: a walk without its reason was parsed"):
                w.main(w.argv()[:-2])

    def test_a_refused_fixture_removes_its_run_tree(self):
        with fake_world() as w:
            drive = MODS["drive"]
            with mock.patch.object(drive, "build_take_fixture", lambda fx, tree, name: (None, None)):
                code, out, err = self.must("B9.cli", w.main, w.argv())
            self.assertEqual(code, 2, "B9.cli")
            self.assertIn("fixture was not built", err, "B9.cli")
            self.nothing_built(w)

    def test_a_driver_that_cannot_be_built_removes_its_run_tree(self):
        """Anything else the driver's construction raises goes on as itself, its run tree removed first."""
        with fake_world() as w:
            drive = MODS["drive"]
            with mock.patch.object(drive, "walk_driver", lambda **kw: (_ for _ in ()).throw(RuntimeError("synthetic"))):
                try:
                    w.main(w.argv())
                except RuntimeError as e:
                    self.assertEqual(str(e), "synthetic", "B9.cli")
                except Exception as e:  # noqa: BLE001
                    self.fail(f"B9.cli: raised {type(e).__name__}: {str(e)[:300]}")
                else:
                    self.fail("B9.cli: the construction's failure was swallowed")
            self.nothing_built(w)

    def test_a_runner_that_raises_names_its_kept_run_tree(self):
        """W12B-R1-3: an exception out of run_walks goes on as itself; the run tree is kept for a human and its path
        printed on its own `kept run tree:` line first."""
        with fake_world() as w:
            def raises(*a, **k):
                raise RuntimeError("synthetic: run_walks raised")
            with mock.patch.object(MODS["walk_runner"], "run_walks", raises):
                try:
                    w.main(w.argv())
                except RuntimeError as e:
                    err = getattr(e, "captured", ("", ""))[1]
                except Exception as e:  # noqa: BLE001
                    self.fail(f"B9.cli: raised {type(e).__name__}: {str(e)[:300]}")
                else:
                    self.fail("B9.cli: run_walks' exception was swallowed")
            self.assertIn(f"kept run tree: {w.run_tree()} ", err, f"B9.cli: {err[-400:]}")
            self.assertTrue(w.run_tree().is_dir(), "B9.cli: the run tree was not kept")

    def test_a_registered_walk_id_is_refused_at_launch(self):
        with fake_world() as w:
            self.assertEqual(self.must("B9.cli", w.main, w.argv())[0], 0, "B9.cli")
            code, out, err = self.must("B9.cli", w.main, w.argv())
            self.assertEqual(code, 1, f"B9.cli: {err[-300:]}")
            doc = self.doc(out)
            self.assertEqual([r["state"] for r in doc["results"]], ["launch-refused"], f"B9.cli: {doc}")
            self.assertEqual(len(register(w)), 1, "B9.cli")
            self.assertEqual((doc["run_tree_kept"], w.run_tree().exists()), (None, False), "B9.cli")

    def test_a_held_walk_keeps_its_run_tree(self):
        with fake_world() as w:
            scanner = dict(w.builders, rules_scanner=lambda paths: [{"path": paths[0], "line": 1,
                                                                     "rule": "synthetic-rule"}])
            code, out, err = self.must("B9.cli", w.main, w.argv(), scanner)
            self.assertEqual(code, 1, f"B9.cli: {err[-300:]}")
            doc = self.doc(out)
            self.assertEqual([r["state"] for r in doc["results"]], ["held"], f"B9.cli: {doc}")
            self.assertTrue(w.run_tree().is_dir(), "B9.cli: a held walk's run tree was removed")
            self.assertIsNone(doc["run_tree_kept"], "B9.cli")
            self.assertEqual(register(w), [], "B9.cli")


# ------------------------------------------------------------------------------------------------- G1
class G1Generated(Case):
    def test_the_equivalent_list_matches_the_generated_mutants(self):
        ids = set(self.must("G1.generated", by_id))
        self.assertGreater(len(ids), 0, "G1.generated: the generator produced nothing")
        self.assertEqual(sorted(set(EQUIVALENT) - ids), [], "G1.generated: EQUIVALENT entries that name no mutant")
        bare = sorted(k for k, why in EQUIVALENT.items() if not isinstance(why, str) or len(why.strip()) < 12)
        self.assertEqual(bare, [], "G1.generated: EQUIVALENT entries without a reason")
        modules = {m.split(".")[0] for m in ids}
        self.assertEqual(modules, set(TARGETS), "G1.generated: the road misses a module")


class TestSysPath(unittest.TestCase):
    def test_the_module_puts_sys_path_back(self):
        """Binding W6M1 (tests/test_wave6_bindings.py) for this module: it imports check_take.py through drive.py and
        test_walk_wiring, so its tearDownModule must leave sys.path exactly as it found it; the wave 6 probe, in a
        fresh interpreter."""
        import test_wave6_bindings as w6
        with mock.patch.object(subprocess, "run", tbi._REAL["run"]), \
                mock.patch.object(subprocess, "Popen", tbi._REAL["Popen"]):
            seen = w6.probe("test_walk_builders")
        self.assertNotIn(str(w6.EVALS), [x for x in seen["after"] if x not in seen["before"]], "W6M1.evals-left")
        self.assertEqual(seen["after"], seen["before"], "W6M1.restored")


# Under --gen-mutant the classes run cheapest first, so failfast meets a kill as early as it can.
GENERATED_ORDER = ("B1Identity", "B6Row", "B2Login", "B3Counters", "B7Production", "B8Present", "B5Fixture",
                   "B4RunTree", "G1Generated", "B9Cli", "TestSysPath")


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=110)
        record = re.findall(r"^test_walk_builders outcomes: (\{.*\})$", got.stdout, re.M)
        outcome = json.loads(record[-1]) if record else None
        blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", got.stderr,
                            re.M | re.S)
        attributed = any(f"{cls}.{test}" == method and "AssertionError" in body and
                         re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w.-])", body)
                         for test, cls, body in blocks)
        clean = bool(outcome) and set(outcome["failures"]) == {method} and outcome["errors"] == [] \
            and outcome["skipped"] == []
        passed = attributed and clean and got.returncode != 0
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}", flush=True)
        if not passed:
            print(got.stdout[-3000:] + got.stderr[-3000:], flush=True)
            return 1
        red += 1
    print(f"test_walk_builders witnesses: {red}/{len(chosen)} red; registry {len(WITNESSES)}", flush=True)
    return 0


def run_generated(shard=None, sample=None, timeout=600, only=None) -> int:
    """Every generated mutant (or shard i of n, or every k-th, or the ids named), each in its own process running the
    whole module with failfast: killed when a test fails by assertion. Exit 0 only when every survivor is listed in
    EQUIVALENT, no listed one was killed and every run finished."""
    mutants_all, dropped = generate()
    chosen = list(enumerate(mutants_all))
    if shard:
        i, n = shard
        chosen = [(k, m) for k, m in chosen if k % n == i - 1]
    if sample:
        chosen = chosen[::sample]
    if only is not None:
        chosen = [(k, m) for k, m in chosen if m.id in only]
    killed, survived, equivalent, listed_killed, inconclusive = [], [], [], [], []

    def one(mid, fast):
        argv = [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--gen-mutant", mid]
        got = subprocess.run(argv + (["--failfast"] if fast else []), capture_output=True, text=True,
                             timeout=timeout)
        record = re.findall(r"^test_walk_builders outcomes: (\{.*\})$", got.stdout, re.M)
        return got, (json.loads(record[-1]) if record else None)

    for _, m in chosen:
        try:
            got, outcome = one(m.id, True)
            if outcome is not None and not outcome["failures"] and outcome["errors"]:
                got, outcome = one(m.id, False)    # failfast stopped at an error: run the whole module
        except subprocess.TimeoutExpired:
            inconclusive.append(m.id)
            print(f"generated {m.id}: TIMEOUT (inconclusive)", flush=True)
            continue
        if outcome is None:
            inconclusive.append(m.id)
            print(f"generated {m.id}: NO OUTCOME (rc {got.returncode})\n{got.stderr[-1500:]}", flush=True)
            continue
        is_killed = bool(outcome["failures"])
        state = "KILLED" if is_killed else "SURVIVED"
        if is_killed:
            killed.append(m.id)
            if m.id in EQUIVALENT:
                listed_killed.append(m.id)
        elif m.id in EQUIVALENT:
            equivalent.append(m.id)
            state = "EQUIVALENT"
        else:
            survived.append(m.id)
        print(f"generated {m.id}: {state} by {outcome['failures'][:1]} (errors {len(outcome['errors'])}) "
              f"[{m.kind} at line {m.line}: {m.original[:60]!r} -> {m.replacement[:40]!r}]", flush=True)
    print(f"test_walk_builders generated mutants: {len(mutants_all)} generated ({dropped} dropped, not compiling), "
          f"{len(chosen)} run, {len(killed)} killed, {len(equivalent)} equivalent (listed), {len(survived)} "
          f"survived unlisted, {len(listed_killed)} listed but killed, {len(inconclusive)} inconclusive", flush=True)
    for name, ids in (("SURVIVED (unlisted)", survived), ("LISTED BUT KILLED", listed_killed),
                      ("INCONCLUSIVE", inconclusive)):
        for x in ids:
            print(f"  {name}: {x}", flush=True)
    return 0 if not survived and not listed_killed and not inconclusive else 1


# ------------------------------------------------------------------------------------------------- B10
# glitch-06's queue item 1 (14 Oct 2026): TakeSpec.resources are the box lane's capacity POLICY (live-box report,
# "TakeSpec.resources: values only, for walk_builders' take_spec": memory_reservation 2147483648, memory 6442450944,
# cpus "8", pids_limit 4096), typed here once from that line.
BOX_RESOURCES = {"memory_reservation": 2147483648, "memory": 6442450944, "cpus": "8", "pids_limit": 4096}


def b10_problems(mod) -> list:
    """B10.resources: the policy values, run_take's own spec check passing them, and the take spec built by the row's
    arm's lock (a pending lock refuses at call time; a ready one gives its image id and the policy values)."""
    from box import image_lock
    out = []
    if getattr(mod, "TAKE_RESOURCES", None) != BOX_RESOURCES:
        return [f"B10.resources: TAKE_RESOURCES is {getattr(mod, 'TAKE_RESOURCES', None)!r}, not the box's policy"]
    spec = rt.TakeSpec(image=tbi.IMAGE, run_tree="/synthetic/tree", config_dir="/synthetic/cfg",
                       network=mod.NETWORK_PLACEHOLDER, **mod.TAKE_RESOURCES)
    try:
        rt.check_spec(spec)
    except Exception as e:  # noqa: BLE001
        out.append(f"B10.resources: run_take refuses the policy spec: {type(e).__name__}: {e}")
    build = mod.take_spec_builder()
    row = {"arm": "A"}
    real = image_lock.load(str(HERE / mod.TAKE_LOCKS["A"]))
    ready = dict(real, image_id="sha256:" + "a" * 64)
    with mock.patch.object(image_lock, "load", lambda path: ready), \
            mock.patch.object(image_lock, "require_ready", lambda lock: lock):
        got = build(row, "/synthetic/cfg", "/synthetic/tree")
    want = {"image": "sha256:" + "a" * 64, "run_tree": "/synthetic/tree", "config_dir": "/synthetic/cfg",
            **BOX_RESOURCES}
    if {k: getattr(got, k) for k in want} != want:
        out.append(f"B10.resources: a ready lock's take spec is {got}")
    with mock.patch.object(image_lock, "load", lambda path: dict(real, image_id=image_lock.PENDING)):
        try:
            build(row, "/synthetic/cfg", "/synthetic/tree")
            out.append("B10.resources: a pending lock's take spec was built")
        except Exception:  # noqa: BLE001 - NotReady, by the lock reader
            pass
    if set(mod.TAKE_LOCKS) != {"A", "O", "G"} or not all((HERE / v).is_file() for v in mod.TAKE_LOCKS.values()):
        out.append(f"B10.resources: TAKE_LOCKS is not one existing lock per arm: {mod.TAKE_LOCKS}")
    return out


class B10Resources(Case):
    def test_the_take_spec_carries_the_box_policy(self):
        self.assertEqual(b10_problems(wb()), [])

    def test_a_resource_drift_is_red(self):
        mod = wb()
        for k, v in (("memory", 4 * 1024 ** 3), ("cpus", "4"), ("pids_limit", 1024)):
            with mock.patch.object(mod, "TAKE_RESOURCES", dict(mod.TAKE_RESOURCES, **{k: v})):
                self.assertTrue(b10_problems(mod), k)


if __name__ == "__main__":
    if "--generated-mutants" in sys.argv:
        shard = sample = None
        if "--shard" in sys.argv:
            a, b = sys.argv[sys.argv.index("--shard") + 1].split("/")
            shard = (int(a), int(b))
            if not 1 <= shard[0] <= shard[1]:
                raise SystemExit("--shard i/n with 1 <= i <= n")
        if "--sample" in sys.argv:
            sample = int(sys.argv[sys.argv.index("--sample") + 1])
        per = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 600
        only = None
        if "--only" in sys.argv:                 # a comma-separated list of generated ids (targeted Mac runs)
            only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
        raise SystemExit(run_generated(shard, sample, per, only))
    failfast = "--failfast" in sys.argv
    if failfast:
        sys.argv.remove("--failfast")
    if "--gen-mutant" in sys.argv:
        index = sys.argv.index("--gen-mutant")
        GENERATED = sys.argv[index + 1]
        del sys.argv[index:index + 2]
        if len(sys.argv) == 1:
            sys.argv += list(GENERATED_ORDER)
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses(sys.argv[sys.argv.index("--witnesses") + 1:]))
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        if SELECTED not in WITNESSES:
            raise SystemExit(f"unknown mutant {SELECTED!r}")
        del sys.argv[index:index + 2]
    result = unittest.main(verbosity=2, exit=False, failfast=failfast).result
    ids = lambda pairs: [t.id().removeprefix("__main__.").split(" ")[0] for t, _ in pairs]  # noqa: E731
    print(f"test_walk_builders: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_walk_builders outcomes: " + json.dumps({"failures": ids(result.failures),
                                                       "errors": ids(result.errors),
                                                       "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
