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
  B17 round 11 (glitch-b5, 17 Oct 2026), the account record bound in this module's generated sweep: account_emails_path
      is ACCOUNT_EMAILS in the one folder holding WALK_LOGIN_FILES' account folders (absent, empty, not a dict, two
      parents, a relative or non-text login path: refused by name); account_emails reads (operator, account) for a
      codex or gemini take and refuses by name another harness, a path that is not absolute text, a missing file, a
      link, a mode other than 600, another owner, an unopenable file, a file replaced between check and read (its
      descriptor closed either way), a file inside a repository, more than 4096 bytes, bytes that are not one JSON
      object with unique keys, a value that is not an object, an extra key (a key that is not a name is never
      echoed), a missing key for the take's harness, and a value that is not an address (too short, too long, not
      text); no refusal carries an address. With no record lease_secrets refuses before any lease token is read and
      a Gemini login_secrets when made; a Claude Code take never reads it.
  B18 round 11, R-6 and round 10 ruling 3's road bound in the same sweep: build_run_tree(harness=) places the native
      file beside every CLAUDE.md with its bytes, in the one commit, for codex and gemini, and neither for Claude Code;
      no root CLAUDE.md or a commit already carrying the name refuses and leaves nothing; place_instruction_file
      hands back the name, and refuses by name an untracked copy already in the checkout, a commit without one of the
      checkout's CLAUDE.md files, a copy altered in the commit or in the checkout, and a checkout run_tree_problems
      refuses. Round 18 B13: on an origin whose .gitignore lists AGENTS.md and GEMINI.md (the pinned GARS tree lists
      AGENTS.md), the placed copies are still in the one commit, which holds exactly the origin's files minus the
      exclusions plus the placed copies.
  B22 R-H5-2 (glitch-26, 19 Oct 2026): place_agent_home on its own, each statement by its effect: a Claude Code
      checkout gets None, no folder and no exclude line; a checkout already holding .home (a folder, a file, a dangling
      link) is refused with nothing written; codex and gemini get the name back, .home/ appended to .git/info/exclude
      after its old lines, and an empty folder of mode 700 under any umask that leaves git working; an exclude a
      committed `!.home/` negates is refused by the check-ignore read; run_tree_problems is read once on the built
      tree and any problem refuses.
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
import base64
import contextlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
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
# Queue item 2 (glitch-06, 14 Oct 2026): uid_map and cgroup_dir_for are run-time readers now (B11), never missing.
EXPECTED_MISSING = ["runtime", "config_parent", "take_spec", "sidecar_for", "proxy", "lock_path", "hosts",
                    "rules_scanner", "login_path", "agent_version", "design_for",
                    "budgets", "run_tree_exclude"]
# take_spec (harness ce2bdef4) is built once take-a's image lock holds no PENDING value: missing, by name, on a tree
# whose take-a lock is PENDING, and present where the box lane's reviewed locks are in (6221c297; on the merged head,
# the integration lane). B7.production checks it is then callable. Read from the lock file itself.
def _take_a_lock_ready() -> bool:
    import json
    lock = json.loads((Path(__file__).resolve().parents[1] / "box" / "image.lock").read_text())
    def held(v):
        return v == "PENDING" or (isinstance(v, dict) and any(held(x) for x in v.values()))
    return not lock.get("pending") and not any(held(v) for k, v in lock.items() if k != "pending")


TAKE_A_LOCK_READY = _take_a_lock_ready()
if TAKE_A_LOCK_READY:
    EXPECTED_MISSING.remove("take_spec")
# The walk token's login file is the box's record, run_take.WALK_LOGIN_FILES["claude1"] (box lane 1eb02a9e): missing, by
# name, on a tree whose run_take has no such record, and that exact path where it does (B7.login checks both ways).
WALK_LOGIN_ON_TREE = isinstance(getattr(rt, "WALK_LOGIN_FILES", None), dict) and "claude1" in rt.WALK_LOGIN_FILES
if WALK_LOGIN_ON_TREE:
    EXPECTED_MISSING.remove("login_path")
# The rules scanner is missing, by name, while box/scan_record.py's RULES_SCANNER is PENDING, and built from
# box/rules_scanner.real_rules_scanner() where the box lane has pinned it (the merged head, 2d6983e9: the integration
# lane's red 1-4). B7.production checks it is then the pinned class's instance.
def _rules_scanner_on_tree() -> bool:
    from box import scan_record
    return "rules_scanner" not in scan_record.pending()


RULES_SCANNER_ON_TREE = _rules_scanner_on_tree()
if RULES_SCANNER_ON_TREE:
    EXPECTED_MISSING.remove("rules_scanner")
# CP5 (Javier, "CP5: all as recommended", 14 Oct 2026) registered arm A's pin profiles, so pin_for is no longer missing
# in production (B8's rule, on the real table); it is checked present in B7.production.
# The ownership road is the box lane's box/ownership.py (81ede46d): missing, by name, on a tree without that module, and
# present on the merged head (B7.production checks it is then drive's own `_ownership`).
OWNERSHIP_ON_TREE = (Path(__file__).resolve().parents[1] / "box" / "ownership.py").is_file()
EXPECTED_MISSING += [] if OWNERSHIP_ON_TREE else ["ownership"]
# BOOTSTRAP (glitch-6b's first-walk bootstrap ruling, 15 Oct 2026): check_take.CHECKER_CONSTANTS holds its ruled values,
# so design_for is built (B8's rule on the real constants); missing, by name, only on a tree still holding a PENDING one.
def _constants_held() -> list:
    import check_take
    return [x for k, v in check_take.CHECKER_CONSTANTS.items() for x in check_take._pending_paths(v, k)]



def expected_missing() -> list:
    """EXPECTED_MISSING, less design_for where no checker constant is PENDING (read when a test runs, never at import:
    check_take.py puts evals/ on sys.path when imported)."""
    return [n for n in EXPECTED_MISSING if n != "design_for" or _constants_held()]
SETTINGS_GUARD_ON_TREE = (Path(__file__).resolve().parents[1] / "box" / "settings_guard.py").is_file()
EXPECTED_MISSING += [] if SETTINGS_GUARD_ON_TREE else ["settings_guard"]
EXPECTED_MISSING += ["machine_gate"]       # P-2: until the operator's runner names its paths (machine_gate's env)
# The real-box bring-up (glitch-6b, 15 Oct 2026): runtime (run_take.DockerRuntime) and hosts (proxy_conf.HOSTS) are
# built on every tree; lock_path wherever preflight's own loader accepts a harness's take lock (the box's readers, read
# here, never the module under test); agent_version wherever prereg's version_pins and routing's pin_profiles pin one
# version for a harness (read here from the draft and the table). config_parent and the proxy only when the operator
# names GAP4_CONFIG_PARENT (never in these tests, B7 clears it); sidecar_for stays Missing (no registered watch list).
EXPECTED_MISSING.remove("runtime")
EXPECTED_MISSING.remove("hosts")


def _locks_on_tree() -> dict:
    from box import preflight
    dirs = getattr(preflight, "TAKE_LOCK_DIRS", None)
    out = {}
    if not isinstance(dirs, dict):
        return out
    box = Path(__file__).resolve().parents[1] / "box"
    for h in (rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI):
        d = dirs[preflight.TAKE_IMAGE[h]]
        path = str(box / d / "image.lock") if d else str(box / "image.lock")
        try:
            preflight.load_take_lock(path, harness=h)
        except Exception:  # noqa: BLE001 - not ready on this tree
            continue
        out[h] = path
    return out


def _versions_on_tree() -> dict:
    import routing
    from box import preflight
    pins = tww.REAL_LOAD().get("version_pins") or {}
    profiles = routing.load_table().get("pin_profiles") or {}
    locks = _locks_on_tree()
    out = {}
    for h in (rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI):
        draft = {m: p.get("version") for m, p in (pins.get(h) or {}).items()}
        table = {m: p.get("version") for m, p in (profiles.get(h) or {}).items()}
        got = set(draft.values())
        if not (draft and draft == table and len(got) == 1 and next(iter(got)) not in (None, "", "PENDING")):
            continue
        v = next(iter(got))
        if any([p.get(k) for k in ("version", "image_version", "agent_version")] != [v] * 3
               for p in pins[h].values()):
            continue
        if h in locks and preflight.load_take_lock(locks[h], harness=h)["harness.version"] == v:
            out[h] = v
    return out


LOCKS_ON_TREE = _locks_on_tree()
if LOCKS_ON_TREE:
    EXPECTED_MISSING.remove("lock_path")
VERSIONS_ON_TREE = _versions_on_tree()
if VERSIONS_ON_TREE:
    EXPECTED_MISSING.remove("agent_version")


# The sidecar launch (Addendum 2 of the bootstrap ruling, 15 Oct 2026): built where the box's sidecar contract is on the
# tree and preflight's own loader accepts the sidecar lock (read here through the box's loader, never the module).
def _sidecar_on_tree():
    import importlib.util
    from box import preflight
    if importlib.util.find_spec("box.sidecar_contract") is None or not callable(getattr(preflight, "load_sidecar_lock",
                                                                                       None)):
        return None
    try:
        lock = str(Path(__file__).resolve().parents[1] / "box" / "image.lock")
        return preflight.load_sidecar_lock(lock, harness=rt.CLAUDE_CODE)["image_id"]
    except Exception:  # noqa: BLE001 - not ready on this tree
        return None


SIDECAR_IMAGE_ON_TREE = _sidecar_on_tree()
if SIDECAR_IMAGE_ON_TREE:
    EXPECTED_MISSING.remove("sidecar_for")
# B3 (the first-walk bootstrap ruling, 15 Oct 2026): budgets and run_tree_exclude are built once check_take's
# CHECKER_CONSTANTS holds them filled (the bootstrap builder's B1), read here from that one home.
def _checker_filled() -> tuple:
    import check_take
    c = check_take.CHECKER_CONSTANTS
    b = c.get("budgets")
    budgets = isinstance(b, dict) and all(k in b and b[k] != check_take.PENDING
                                          for k in ("turn_timeout_s", "finalize_wait_s", "poll_s"))
    rl = c.get("run_location")
    exclude = isinstance(rl, dict) and rl.get("excluded_from_the_run_tree", check_take.PENDING) != check_take.PENDING
    return budgets, exclude


BUDGETS_ON_TREE, EXCLUDE_ON_TREE = _checker_filled()
if BUDGETS_ON_TREE:
    EXPECTED_MISSING.remove("budgets")
if EXCLUDE_ON_TREE:
    EXPECTED_MISSING.remove("run_tree_exclude")


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
        "lease-login-before-place": ("B13.secrets", "walk_builders",
                                     "        if self.placed is None:\n            raise BuilderRefused(\"no lease placed: a "
                                     "Codex take's login file", "        if False:\n            raise BuilderRefused(\"no "
                                     "lease placed: a Codex take's login file"),
        "lease-gate-unchecked": ("B13.secrets", "walk_builders",
                                 "        if gate:\n            raise BuilderRefused(f\"the Codex lease is not placed",
                                 "        if False:\n            raise BuilderRefused(f\"the Codex lease is not placed"),
        # round 17 B5: the walk-start token check (the plan's four mutants, the refresh rule's two halves)
        # round 17 B6: the vendor config on the walk road
        "vendor-config-skipped-codex": ("B19.config", "walk_builders",
                                        "            vendor_config(r, cfg, tree)    # round 17 B6: codex",
                                        "            pass                           # round 17 B6: codex"),
        "vendor-config-skipped-gemini": ("B19.config", "walk_builders",
                                         "            vendor_config(r, cfg, tree)    # round 17 B6: gemini",
                                         "            pass                           # round 17 B6: gemini"),
        "vendor-config-after-the-lease": ("B19.config", "walk_builders",
                                          "            vendor_config(r, cfg, tree)    # round 17 B6: codex, into the "
                                          "empty folder\n            lease.place(cfg)\n",
                                          "            lease.place(cfg)\n            vendor_config(r, cfg, tree)    "
                                          "# round 17 B6: codex, into the empty folder\n"),
        # round 2 of lane vendor-b11, R-H1 (glitch-26, 19 Oct 2026): the walk's run tree reaches the config writer
        # round 2 of lane vendor-b11, R-H5 (glitch-26, 19 Oct 2026): the agent's own HOME in a vendor checkout
        "agent-home-not-made": ("R-H5.home", "walk_builders",
                                "        place_agent_home(tree, harness, session_id=sid, exclude=list(exclude))\n",
                                ""),
        "agent-home-not-excluded": ("R-H5.home", "walk_builders", "        fh.write(f\"{name}/\\n\")\n",
                                    "        pass\n"),
        "agent-home-every-arm": ("R-H5.home", "walk_builders",
                                 "    if harness not in (rt.CODEX, rt.GEMINI):\n        return None\n    name = ",
                                 "    name = "),
        "agent-home-open": ("R-H5.home", "walk_builders", "    os.chmod(home, 0o700)", "    os.chmod(home, 0o755)"),
        "vendor-config-without-tree": ("B19.config", "walk_builders",
                                       "    return take_config.write(cfg, harness, model=row[\"model\"], "
                                       "run_tree=str(tree))",
                                       "    return take_config.write(cfg, harness, model=row[\"model\"], "
                                       "run_tree=None if harness == take_config.CODEX else str(tree))"),
        "lease-margin-zero": ("B13.freshness", "walk_builders",
                              "    left, need = exp - now, walk_s + LEASE_START_MARGIN_S\n",
                              "    left, need = exp - now, walk_s\n"),
        "lease-exp-ignored": ("B13.freshness", "walk_builders", "    if left < need:\n", "    if False:\n"),
        "lease-refresh-age-ignored": ("B13.freshness", "walk_builders",
                                      "    if now - refreshed > LEASE_REFRESH_MAX_AGE_S:\n", "    if False:\n"),
        "lease-refresh-missing-admitted": ("B13.freshness", "walk_builders",
                                           "    if refreshed is None:\n        return",
                                           "    if refreshed is None:\n        return None\n        return"),
        "lease-refusal-carries-token": ("B13.freshness", "walk_builders",
                                        "            raise BuilderRefused(f\"the Codex lease is not placed: {stale}\")",
                                        "            raise BuilderRefused(f\"the Codex lease is not placed: {stale} \""
                                        " + open(self.lease_src).read())"),
        "scanner-real-unchecked": ("B12.scanner", "walk_builders",
                                   "        if type(scanner) is not pinned:", "        if False:"),     # 0f1aa5ea's line
        "scanner-raw-to-driver": ("B12.scanner", "walk_builders",
                                  'identity_for=identity_for({row["walk"]: ident}), secrets=secrets, rules_scanner=rules,',
                                  'identity_for=identity_for({row["walk"]: ident}), secrets=secrets, '
                                  'rules_scanner=builders["rules_scanner"],'),
        "scanner-class-by-name": ("B12.scanner", "walk_builders",
                                  "        if type(scanner) is not pinned:",       # 0f1aa5ea's line (athena, 14 Oct)
                                  "        if type(scanner).__name__ != getattr(pinned, '__name__', None):"),
        "report-dir-shared": ("B12.scanner", "walk_builders",
                              '    report_dir = tempfile.mkdtemp(prefix="walk-scan-", dir=report_parent)',
                              '    report_dir = report_parent'),
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
        "secrets-read-early": ("B2.login", "walk_builders", '        _no_login_file("login_secrets")\n\n    def secrets():',
                               '        _no_login_file("login_secrets")\n    scan_record.read_login(login_file, name, '
                               'allowed=tuple(rt.LOGIN_VARIABLE.values()))\n\n    def secrets():'),
        "counters-folder-unchecked": ("B3.counters", "walk_builders",
                                      "        if not isinstance(folder, str) or not os.path.isabs(folder) or not "
                                      "os.path.isdir(folder):", "        if False:"),
        "counters-zero": ("B3.counters", "walk_builders", "        return rt.counters(folder)",
                          "        return {'oom_kill': 0, 'pids_max': 0}"),
        "run-tree-commit-unchecked": ("B4.run-tree", "walk_builders",
                                      "    if not isinstance(commit, str) or not HEX40.fullmatch(commit):",
                                      "    if False:"),
        # re-anchored (lane vendor-admission round 10, drift from R-6's green 20cea4ed, which made the call's
        # result `tree`): the same guard, the walk's own session id handed to clean_run_tree
        "run-tree-session-another": ("B4.run-tree", "walk_builders",
                                     "        tree = drive.clean_run_tree(commit, sid, list(exclude), Path(repo))",
                                     "        tree = drive.clean_run_tree(commit, check_take.walk_session_id(walk + "
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
        "production-runtime-not-docker": ("B15.production", "walk_builders",   # the bring-up (glitch-6b, 15 Oct)
                                          '        "runtime": rt.DockerRuntime(),',
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
        # lane vendor-admission round 12 (review c-6302fd3 NIT 7): the vendor names above the checkout unchecked
        "place-inherited-unchecked": ("B18.place", "walk_builders", "    above = inherited_instruction_files(tree)\n",
                                      "    above = []\n"),
        # lane vendor-admission round 18 B13 (practice walk w-o1): the placed copies added without -f
        "place-add-unforced": ("B18.ignored", "walk_builders",
                               '    for args in (("add", "-f", "--", *[":(literal)" + d for d, _ in placed]),',
                               '    for args in (("add", "--", *[":(literal)" + d for d, _ in placed]),'),
        # R-FB1 (glitch-26, Mon 19 Oct 2026; review vendor-r18-b12b13-0094246 MINOR 1, the reviewer's mutant M1):
        # the add widened to every file in the checkout, ignored ones included
        "place-add-all": ("B18.ignored", "walk_builders",
                          '    for args in (("add", "-f", "--", *[":(literal)" + d for d, _ in placed]),',
                          '    for args in (("add", "-f", "-A"),'),
        # R-FB2 (glitch-26, Mon 19 Oct 2026; review vendor-r18-b12b13-0094246 NIT 3): the placed paths as pathspecs
        "place-add-not-literal": ("B18.literal", "walk_builders", '*[":(literal)" + d for d, _ in placed]',
                                  '*[d for d, _ in placed]'),
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
    "production-runtime-not-docker": "B7Production.test_production_leaves_exactly_these_missing",
    "missing-absent-silent": "B7Production.test_missing_names_absent_and_unknown",
    "cli-runs-with-gaps": "B7Production.test_main_refuses_by_name_before_anything",
    "pin-never-present": "B8Present.test_a_measured_pin_is_present",
    "main-ignores-builders": "B9Cli.test_one_walk_end_to_end",
    "held-tree-removed": "B9Cli.test_a_held_walk_keeps_its_run_tree",
    "held-exits-zero": "B9Cli.test_a_held_walk_keeps_its_run_tree",
    "refused-tree-left": "B9Cli.test_a_refused_fixture_removes_its_run_tree",
    "scanner-real-unchecked": "B12Scanner.test_the_scanner_is_built_per_walk_and_bound_on_a_real_walk",
    "scanner-raw-to-driver": "B12Scanner.test_a_pinned_scanner_is_built_once_for_a_walk",
    "report-dir-shared": "B12Scanner.test_the_scanner_is_built_per_walk_and_bound_on_a_real_walk",
    "scanner-class-by-name": "B12Scanner.test_the_scanner_is_built_per_walk_and_bound_on_a_real_walk",
    "lease-login-before-place": "B13Lease.test_the_driver_and_walkrepo_get_the_lease_secrets",
    "lease-gate-unchecked": "B13Lease.test_the_driver_and_walkrepo_get_the_lease_secrets",
    "vendor-config-skipped-codex": "B19VendorConfig.test_the_vendor_config_is_written_on_the_walk_road",
    "vendor-config-skipped-gemini": "B19VendorConfig.test_the_vendor_config_is_written_on_the_walk_road",
    "vendor-config-after-the-lease": "B19VendorConfig.test_the_vendor_config_is_written_on_the_walk_road",
    "vendor-config-without-tree": "B19VendorConfig.test_the_vendor_config_is_written_on_the_walk_road",
    **{name: "B21AgentHome.test_a_vendor_checkout_carries_the_agent_home" for name in (
        "agent-home-not-made", "agent-home-not-excluded", "agent-home-every-arm", "agent-home-open")},
    "lease-margin-zero": "B13Lease.test_the_walk_start_token_check",
    "lease-exp-ignored": "B13Lease.test_the_walk_start_token_check",
    "lease-refresh-age-ignored": "B13Lease.test_the_walk_start_token_check",
    "lease-refresh-missing-admitted": "B13Lease.test_the_walk_start_token_check",
    "lease-refusal-carries-token": "B13Lease.test_the_walk_start_token_check",
    "place-inherited-unchecked": "B18Native.test_place_instruction_file_refuses_by_name",
    "place-add-unforced": "B18Native.test_the_native_file_is_added_past_the_trees_gitignore",
    "place-add-not-literal": "B18Native.test_each_placed_path_is_added_literally",
    "place-add-all": "B18Native.test_the_native_file_is_added_past_the_trees_gitignore",
}
WITNESSES = {name: (METHOD[name], m[0]) for name, m in mutants().items()}

# Generated mutants this module does not kill that are equivalent, each with a reason a reviewer can check.
# `--generated-mutants` fails on a survivor not listed here and on a listed one that is killed; G1 fails on an entry
# that names no generated mutant or gives no reason.
EQUIVALENT: dict = {
    # athena run gap4-w12b-bc66fdf-20261013T101052Z, shard 16:
    "walk_builders.remove_run_tree:delete:L6:C4:e3e767f5":
        "the function's last statement `return None`; deleted, the function falls off its end and returns None",
    # round 17 B5, run in this sandbox over --gen-mutant: the same shape
    "walk_builders.lease_freshness_problem:delete:L27:C4:e3e767f5":
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


def problems_by_assertion(prefix):
    """A check that raises reports it as its own line, so a mutant that makes the code raise fails the test by
    assertion (a kill), never by an error the generated sweep does not count."""
    def wrap(fn):
        def check(mod, *args):
            try:
                return fn(mod, *args)
            except Exception as e:  # noqa: BLE001
                return [f"{prefix}: raised {type(e).__name__}: {str(e)[:300]}"]
        check.__name__ = fn.__name__
        return check
    return wrap


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
        codex = login_file(f"CODEX_API_KEY={tbi.TOKEN}\n")       # the lease road: a Codex row has no login file
        with mock.patch.object(os, "open", side_effect=AssertionError("B2.login: the Codex login file was opened")):
            said = self.refuses("B2.login", "its login is the lease", wb().login_file_by_name, str(codex), "codex")
        self.assertNotIn(tbi.TOKEN, said, "B2.login: a refusal carries the value")

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


class B7Production(Drafted):
    def setUp(self):
        super().setUp()                    # the real draft (agent_version reads version_pins), no operator folder
        self.enterContext(mock.patch.dict(os.environ))
        os.environ.pop("GAP4_CONFIG_PARENT", None)

    def test_production_leaves_exactly_these_missing(self):
        got = self.must("B7.production", wb().production_builders)
        gaps = self.must("B7.production", wb().missing, got)
        self.assertEqual([n for n, _ in gaps], expected_missing(), "B7.production: not exactly the missing values")
        self.assertTrue(all(isinstance(why, str) and len(why) > 20 for _, why in gaps), "B7.production")
        why = dict(gaps)
        for name, words in (("login_path", "WALK_LOGIN_FILES['claude1']"),
                            ("design_for", "PENDING"), ("run_tree_exclude", "run_location"),
                            ("agent_version", "pin"), ("rules_scanner", "gitleaks")):
            if name in why:
                self.assertIn(words, why[name], f"B7.production: {name} does not say why")
        if WALK_LOGIN_ON_TREE:
            self.assertEqual(got["login_path"], rt.WALK_LOGIN_FILES["claude1"], "B7.login: not the box's record")
        if RULES_SCANNER_ON_TREE:
            from box import rules_scanner
            self.assertIs(type(got["rules_scanner"]), rules_scanner.RealRulesScanner,
                          "B7.production: the pinned rules scanner is not handed to the walks")
        if TAKE_A_LOCK_READY:
            self.assertTrue(callable(got["take_spec"]), "B7.production: take-a's ready lock gives no take spec")
        import time
        import drive
        import routing
        self.assertEqual((got["clock"], got["sleep"]), (time.time, time.sleep), "B7.production")
        self.assertEqual(got["run_tree_origin"], (drive.REPO, variants.PINNED_TREE), "B7.production")
        self.assertEqual(got["table"], routing.load_table(), "B7.production")
        self.assertTrue(callable(got["pin_for"]), "B7.production: CP5's registered pins are not handed to the walks")
        if TAKE_A_LOCK_READY:
            self.assertTrue(callable(got["take_spec"]), "B7.production: take-a's ready lock gives no take spec")
        if OWNERSHIP_ON_TREE:
            self.assertIs(got["ownership"], drive._ownership, "B7.production: the ownership road is not the box's")
        else:
            self.assertIn("box/ownership.py", why["ownership"], "B7.production: ownership does not say why")
        if SETTINGS_GUARD_ON_TREE:
            self.assertIs(got["settings_guard"], drive._settings_guard, "B7.production: the guard is not the box's")
        else:
            self.assertIn("box/settings_guard.py", why["settings_guard"], "B7.production: the guard does not say why")
        self.assertEqual(sorted(got), sorted(wb().NAMES + wb().ROW_NAMES), "B7.production: the set is not NAMES")
        # round 17 B2: the lease source is the box's record, run_take.LEASE_SOURCES["codex2"], never typed here
        self.assertEqual(got["lease_path"], getattr(rt, "LEASE_SOURCES", {}).get("codex2", "unregistered"),
                         "B7.production: lease_path is not run_take.LEASE_SOURCES['codex2']")
        self.assertEqual(b7_bringup_problems(wb(), got), [])
        if WALK_GEMINI_ON_TREE:
            self.assertEqual(got["gemini_login_path"], rt.WALK_LOGIN_FILES["r4-g"], "B7.production: not the r4-g record")
        else:
            self.assertIsInstance(got["gemini_login_path"], wb().Missing, "B7.production: a Gemini key path is filled")

    def test_lease_path_reads_the_box_record(self):
        """round 17 B2: production_builders' lease_path follows run_take.LEASE_SOURCES (moved, it moves); a relative
        record refuses by name; a tree without the record leaves lease_path Missing, by name."""
        moved = "/synthetic/secrets/codex2/auth.json"
        with mock.patch.object(rt, "LEASE_SOURCES", {"codex2": moved}, create=True):
            self.assertEqual(wb().production_builders()["lease_path"], moved, "B2: lease_path is not read from the record")
        with mock.patch.object(rt, "LEASE_SOURCES", {"codex2": "codex2/auth.json"}, create=True):
            with self.assertRaises(wb().BuilderRefused) as cm:
                wb().production_builders()
            self.assertIn("LEASE_SOURCES['codex2']", str(cm.exception))
        with mock.patch.object(rt, "LEASE_SOURCES", {}, create=True):
            got = wb().production_builders()["lease_path"]
            self.assertIsInstance(got, wb().Missing, "B2: an unregistered lease source is filled")
            self.assertIn("LEASE_SOURCES['codex2']", got.why, "B2: lease_path does not say why")

    def test_main_refuses_by_name_before_anything(self):
        for argv in ([], ARGV, ["--no-such-flag"]):
            with self.subTest(argv=argv[:1]), temp_root() as tmp:
                code, out, err = self.must("B7.production", run_main, argv)
                self.assertEqual(code, 2, "B7.production: not refused")
                named = re.findall(r"^refused: missing (\w+): ", err, re.M)
                self.assertEqual(named, expected_missing(), f"B7.production: {err[:600]}")
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


    def test_the_walk_login_is_the_box_record(self):
        self.assertEqual(b7_login_problems(wb()), [])


@contextlib.contextmanager
def walk_login_files(value):
    """run_take.WALK_LOGIN_FILES set to `value` for the block, or absent when value is ABSENT; put back after."""
    had = hasattr(rt, "WALK_LOGIN_FILES")
    old = getattr(rt, "WALK_LOGIN_FILES", None)
    if value is ABSENT:
        if had:
            delattr(rt, "WALK_LOGIN_FILES")
    else:
        rt.WALK_LOGIN_FILES = value
    try:
        yield
    finally:
        if had:
            rt.WALK_LOGIN_FILES = old
        elif hasattr(rt, "WALK_LOGIN_FILES"):
            delattr(rt, "WALK_LOGIN_FILES")


ABSENT = object()
SYNTHETIC_LOGIN = "/synthetic/gap4-secrets/claude1/claude-walk-token"


@problems_by_assertion("B7.login")
def b7_login_problems(mod) -> list:
    """B7.login: login_path is run_take.WALK_LOGIN_FILES["claude1"] as the box records it (only the path; prepare
    checks the file by name), Missing by name while the record is absent or lacks claude1, refused when not absolute."""
    out = []
    if getattr(mod, "WALK_ACCOUNT", None) != "claude1":
        out.append(f"B7.login: the walk account is {getattr(mod, 'WALK_ACCOUNT', None)!r}, not claude1")
    with walk_login_files({"claude2": "/synthetic/other", "claude1": SYNTHETIC_LOGIN}):
        got = mod.walk_login_path()
        if got != SYNTHETIC_LOGIN:
            out.append(f"B7.login: login_path is {got!r}, not the record's claude1 file")
        got = mod.production_builders()["login_path"]
        if got != SYNTHETIC_LOGIN:
            out.append(f"B7.login: the production builders' login_path is {got!r}")
    for label, value in (("absent", ABSENT), ("without claude1", {"claude2": "/synthetic/other"}),
                         ("not a mapping", ["claude1"]), ("None", None)):
        with walk_login_files(value):
            got = mod.walk_login_path()
            if not isinstance(got, mod.Missing):
                out.append(f"B7.login: a record {label} gave {got!r}, not Missing")
            elif "WALK_LOGIN_FILES['claude1']" not in got.why or "walk token" not in got.why:
                out.append(f"B7.login: a record {label} is Missing without saying why: {got.why!r}")
            if label == "absent":
                prod = mod.production_builders()["login_path"]
                if not isinstance(prod, mod.Missing):
                    out.append(f"B7.login: the production builders hold {prod!r} with no record")
    for bad in ("relative/claude-walk-token", "", None, 3):
        with walk_login_files({"claude1": bad}):
            try:
                got = mod.walk_login_path()
                out.append(f"B7.login: a record of {bad!r} was taken: {got!r}")
            except mod.BuilderRefused as e:
                if "WALK_LOGIN_FILES['claude1']" not in str(e):
                    out.append(f"B7.login: the refusal of {bad!r} does not name the record: {e}")
    return out


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
        """Box 8ad2978a: once scan_record's record is not PENDING, the production scanner is
        rules_scanner.real_rules_scanner()'s (on this branch, the stand-in module of pinned_class)."""
        from box import scan_record
        scanner = object()
        with pinned_class(), mock.patch.object(scan_record, "pending", lambda: {}):
            from box import rules_scanner
            with mock.patch.object(rules_scanner, "real_rules_scanner", lambda: scanner, create=True):
                got = self.must("B8.present", wb().production_builders)
        self.assertIs(got.get("rules_scanner"), scanner, "B8.present")   # an absent key fails by assertion

    def test_a_pending_checker_constant_makes_design_for_missing(self):
        """design_for is Missing, naming the constant, whenever any CHECKER_CONSTANTS entry is PENDING: run_location put
        back to PENDING here, on every tree (on a tree whose constants are filled nothing else reaches the list)."""
        import check_take
        with mock.patch.object(check_take, "CHECKER_CONSTANTS",
                               dict(check_take.CHECKER_CONSTANTS, run_location=check_take.PENDING)):
            got = self.must("B8.pending", wb().production_builders)
        self.assertIsInstance(got.get("design_for"), wb().Missing, "B8.pending: a PENDING constant gave a design view")
        self.assertIn("run_location", got["design_for"].why, "B8.pending: design_for does not name the constant")

    def test_a_pending_rules_scanner_is_missing(self):
        """R2 (glitch-6b, 14 Oct 2026): the fail-closed branch, driven through the pending() seam on every tree. While
        scan_record.pending() names rules_scanner, the production scanner is Missing with that reason and the real one
        is never built (the merged tree's pending() no longer names it, so only this test reaches the branch there)."""
        from box import scan_record
        why = "synthetic: the rules scanner record is PENDING for this test"
        with pinned_class(), mock.patch.object(scan_record, "pending", lambda: {"rules_scanner": why}):
            from box import rules_scanner
            with mock.patch.object(rules_scanner, "real_rules_scanner", create=True,
                                   side_effect=AssertionError("B8.pending: the real scanner was built while PENDING")):
                got = self.must("B8.pending", wb().production_builders)
        self.assertIsInstance(got.get("rules_scanner"), wb().Missing, "B8.pending: a PENDING scanner is not Missing")
        self.assertIn(why, got["rules_scanner"].why, "B8.pending: the Missing scanner does not carry pending()'s reason")


# ------------------------------------------------------------------------------------------------- B9
def sidecar_for(row, ev, tree, project=None):
    """test_walk_wiring's fake sidecar launch, over the walk's own run tree (the production road also takes the walk's
    project, for its watch list)."""
    from box import sidecar as sc
    # The sidecar's accepted launch (0b6f60f9; its fake inspect is test_box_integration's, fixed in 5f1b33ee).
    expect = {"user": sc.BOOT_USER, "network_mode": "none", "cap_drop": ["ALL"],
              "cap_add": list(sc.BOOT_INSPECT_CAPABILITIES), "security_opt": ["no-new-privileges"],
              "privileged": False, "image": tbi.SIDECAR_IMAGE, "cmd": tbi.sidecar_cmd(tree), "entrypoint": [],
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
            "machine_gate": lambda: [],
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
                with tbi.FakeBox.as_watcher(str(path.parent)):     # the sidecar writes as the watcher (P4 road)
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
        with fake_world() as w, mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", False, create=True):   # B8-1
            for argv, words in ((w.argv(walk="a/b"), "not one path segment"),
                                (w.argv(walk="../w-0001"), "not one path segment"),
                                (w.argv(wording="w99"), "not a row of the design"),
                                (w.argv(arm="O", model="gpt-6.1-sol"), "Codex lease gate")):    # closed or absent
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
    def test_every_test_class_runs_under_a_generated_mutant(self):
        """The sweep runs only GENERATED_ORDER's classes: a test class left out of it binds nothing in the sweep
        (B10, B11 and B12 were, and every mutant of the functions they bind survived)."""
        classes = {n for n, v in globals().items() if isinstance(v, type) and issubclass(v, unittest.TestCase)
                   and any(a.startswith("test") for a in vars(v))}
        self.assertEqual(sorted(classes - set(GENERATED_ORDER)), [], "G1.order: classes the sweep never runs")

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
GENERATED_ORDER = ("B17Account", "B20LeaseSource", "B18Native", "B1Identity", "B6Row", "B2Login", "B3Counters", "B11Derived",
                   "B10Resources", "B7Production", "B8Present", "B13Lease", "B19VendorConfig", "B21AgentHome",
                   "B22AgentHomePlaced", "B14Gemini",
                   "B15Bringup", "B16Watch",
                   "B5Fixture", "B4RunTree", "G1Generated", "B12Scanner", "B9Cli", "TestSysPath")


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_walk_builders witnesses", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()),
                                    *sorted({WITNESSES[x][0] for x in chosen})], timeout=1800, tag="test_walk_builders")
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
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_walk_builders generated mutants", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), *GENERATED_ORDER],
                                    timeout=timeout, tag="test_walk_builders")
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


def pending_lock(real: dict) -> dict:
    """take-a's lock as the unfilled schema-1 lock (image_id PENDING with its reason), made from the tree's own lock of
    either schema: a schema-2 lock (the merged head) may hold no PENDING value at all, so its schema-2 keys go
    (integration lane's red 5, 2d6983e9). image_lock is never loosened: the fixture must pass its problems()."""
    from box import image_lock
    held = {k: v for k, v in real.items() if k not in getattr(image_lock, "SCHEMA_2_KEYS", ())}
    held.update(schema=image_lock.SCHEMA, image_id=image_lock.PENDING,
                pending=dict(real.get("pending") or {}, image_id="synthetic: only a built image has an id"))
    return held


@problems_by_assertion("B10.resources")
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
    held = pending_lock(real)
    if image_lock.problems(held):
        return [f"B10.resources: the pending-lock fixture is not a valid lock: {image_lock.problems(held)}"]
    with mock.patch.object(image_lock, "load", lambda path: held):
        try:
            build(row, "/synthetic/cfg", "/synthetic/tree")
            out.append("B10.resources: a pending lock's take spec was built")
        except image_lock.NotReady:               # review nit 7: the lock reader's own refusal, nothing else
            pass
        except Exception as e:  # noqa: BLE001
            out.append(f"B10.resources: a pending lock raised {type(e).__name__}, not image_lock.NotReady")
    if set(mod.TAKE_LOCKS) != {"A", "O", "G"} or not all((HERE / v).is_file() for v in mod.TAKE_LOCKS.values()):
        out.append(f"B10.resources: TAKE_LOCKS is not one existing lock per arm: {mod.TAKE_LOCKS}")
    return out


@problems_by_assertion("B10.take-a")
def b10_take_a_problems(mod) -> list:
    """B10.take-a: take_a_spec reads take-a's own lock (TAKE_LOCKS["A"] beside walk_builders); a lock holding PENDING
    values gives Missing naming the lock and each held field; a ready one gives the take spec builder, which builds
    the arm's spec from its lock's image id (the ready-lock branch, as on the merged head: 6e965d12)."""
    from box import image_lock
    out = []
    real = image_lock.load(str(HERE / mod.TAKE_LOCKS["A"]))
    seen = []

    def load(path):
        seen.append(path)
        return lock_now[0]
    lock_now = [dict(real, image_id="sha256:" + "b" * 64)]
    with mock.patch.object(image_lock, "load", load), \
            mock.patch.object(image_lock, "pending", lambda lock: ("base", "image_id") if lock is held else ()), \
            mock.patch.object(image_lock, "require_ready", lambda lock: lock):
        held = dict(real)
        lock_now[0] = held
        got = mod.take_a_spec()
        if not isinstance(got, mod.Missing):
            out.append(f"B10.take-a: a pending lock gave {got!r}, not Missing")
        else:
            for words in (mod.TAKE_LOCKS["A"], "PENDING (base, image_id)", "TAKE_RESOURCES"):
                if words not in got.why:
                    out.append(f"B10.take-a: the pending lock's Missing does not say {words!r}: {got.why!r}")
        if seen != [str(HERE / mod.TAKE_LOCKS["A"])]:
            out.append(f"B10.take-a: read {seen}, not take-a's own lock")
        lock_now[0] = dict(real, image_id="sha256:" + "b" * 64)
        got = mod.take_a_spec()
        if isinstance(got, mod.Missing) or not callable(got):
            out.append(f"B10.take-a: a ready lock gave {got!r}, not a take spec builder")
        else:
            spec = got({"arm": "A"}, "/synthetic/cfg", "/synthetic/tree")
            want = {"image": "sha256:" + "b" * 64, "run_tree": "/synthetic/tree", "config_dir": "/synthetic/cfg",
                    "network": mod.NETWORK_PLACEHOLDER, **BOX_RESOURCES}
            if {k: getattr(spec, k, None) for k in want} != want:
                out.append(f"B10.take-a: a ready lock's take spec is {spec}")
    on_tree = mod.take_a_spec()                    # the lock as it is on this tree, unpatched
    if TAKE_A_LOCK_READY != (not isinstance(on_tree, mod.Missing)):
        out.append(f"B10.take-a: this tree's lock (ready {TAKE_A_LOCK_READY}) gave {on_tree!r}")
    elif not TAKE_A_LOCK_READY:
        fields = image_lock.pending(real)
        if f"PENDING ({', '.join(fields)})" not in on_tree.why:
            out.append(f"B10.take-a: this tree's pending lock names another list: {on_tree.why!r}")
    return out


class B10Resources(Case):
    def test_the_take_spec_carries_the_box_policy(self):
        self.assertEqual(b10_problems(wb()), [])

    def test_take_a_spec_on_a_pending_and_a_ready_lock(self):
        self.assertEqual(b10_take_a_problems(wb()), [])

    def test_a_resource_drift_is_red(self):
        mod = wb()
        for k, v in (("memory", 4 * 1024 ** 3), ("cpus", "4"), ("pids_limit", 1024)):
            with mock.patch.object(mod, "TAKE_RESOURCES", dict(mod.TAKE_RESOURCES, **{k: v})):
                self.assertTrue(b10_problems(mod), k)


# ------------------------------------------------------------------------------------------------- B11
# glitch-06's queue item 2: the take container's cgroup folder and the runtime's uid map are derived at run time from the
# container id and /proc (the box lane measured, on athena: /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/
# user.slice/docker-<id>.scope and ((0,1000,1),(1,100000,65536))), never typed in; anything else refuses.
CID = "c" * 64
SCOPE = f"/user.slice/user-1000.slice/user@1000.service/user.slice/docker-{CID}.scope"


class InspectBox:
    def __init__(self, out="4242\n", code=0):
        self.out, self.code, self.calls = out, code, []

    def run(self, argv, env=None, timeout=None):
        self.calls.append(list(argv))
        return rt.Completed(self.code, self.out, "")


def fake_proc(tmp: Path, *, uid_map="         0       1000          1\n         1     100000      65536\n",
              cgroup=None, make_dir=True, extra=(), link=False) -> tuple:
    """A fake /proc/4242 and cgroup root; `extra` folders made under the root too; `link`: the scope folder is a link
    to an existing folder."""
    proc, root = tmp / "proc", tmp / "cgroup"
    rel = SCOPE
    (proc / "4242").mkdir(parents=True)
    (proc / "4242" / "uid_map").write_text(uid_map)
    (proc / "4242" / "cgroup").write_text(cgroup if cgroup is not None else f"0::{rel}\n")
    if link:
        (root / rel.lstrip("/")).parent.mkdir(parents=True)
        (tmp / "elsewhere").mkdir()
        (root / rel.lstrip("/")).symlink_to(tmp / "elsewhere")
    elif make_dir:
        (root / rel.lstrip("/")).mkdir(parents=True)
    for e in extra:
        (root / e.lstrip("/")).mkdir(parents=True, exist_ok=True)
    return proc, root, str(root / rel.lstrip("/"))


@problems_by_assertion("B11.derived")
def b11_problems(mod) -> list:
    out = []
    for name in ("container_pid", "uid_map_of_pid", "cgroup_dir_of_pid"):
        if not callable(getattr(mod, name, None)):
            return [f"B11.derived: walk_builders has no {name}"]
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        proc, root, want = fake_proc(tmp)
        box = InspectBox()
        if mod.container_pid(box, CID) != 4242 or box.calls[0][:2] != [rt.RUNTIME_CLIENT, "inspect"]:
            out.append(f"B11.derived: the pid was not read by inspect: {box.calls}")
        if mod.uid_map_of_pid(4242, proc=str(proc)) != ((0, 1000, 1), (1, 100000, 65536)):
            out.append(f"B11.derived: the uid map reads as {mod.uid_map_of_pid(4242, proc=str(proc))}")
        if mod.cgroup_dir_of_pid(4242, CID, proc=str(proc), root=str(root)) != want:
            out.append("B11.derived: the cgroup folder is not the container's scope")
    bad = {
        "a take id that is not 64 hex": lambda tmp: mod.container_pid(InspectBox(), "c" * 63),
        "a take id that is not a string": lambda tmp: mod.container_pid(InspectBox(), 7),
        "inspect failed": lambda tmp: mod.container_pid(InspectBox(code=1), CID),
        "not running (pid 0)": lambda tmp: mod.container_pid(InspectBox(out="0\n"), CID),
        "pid not a number": lambda tmp: mod.container_pid(InspectBox(out="x\n"), CID),
        "uid map empty": lambda tmp: mod.uid_map_of_pid(4242, proc=str(fake_proc(tmp, uid_map="")[0])),
        "uid map malformed": lambda tmp: mod.uid_map_of_pid(4242, proc=str(fake_proc(tmp, uid_map="0 1000\n")[0])),
        "cgroup v1": lambda tmp: mod.cgroup_dir_of_pid(4242, CID, proc=str((f := fake_proc(
            tmp, cgroup="1:memory:/docker/x\n"))[0]), root=str(f[1])),
        "another container's scope": lambda tmp: mod.cgroup_dir_of_pid(4242, CID, proc=str((f := fake_proc(
            tmp, cgroup=f"0::/user.slice/docker-{'d' * 64}.scope\n"))[0]), root=str(f[1])),
        "scope folder missing": lambda tmp: mod.cgroup_dir_of_pid(4242, CID, proc=str((f := fake_proc(
            tmp, make_dir=False))[0]), root=str(f[1])),
        # each guard alone (the generated sweep, 14 Oct window 2): every case below passes the other guards
        "inspect printed nothing (None)": lambda tmp: mod.container_pid(InspectBox(out=None), CID),
        "uid map unreadable": lambda tmp: mod.uid_map_of_pid(4243, proc=str(fake_proc(tmp)[0])),
        "cgroup unreadable": lambda tmp: mod.cgroup_dir_of_pid(4243, CID, proc=str((f := fake_proc(tmp))[0]),
                                                               root=str(f[1])),
        "two cgroup lines": lambda tmp: mod.cgroup_dir_of_pid(4242, CID, proc=str((f := fake_proc(
            tmp, cgroup=f"0::{SCOPE}\n0::{SCOPE}\n"))[0]), root=str(f[1])),
        "a cgroup line not 0::": lambda tmp: mod.cgroup_dir_of_pid(4242, CID, proc=str((f := fake_proc(
            tmp, cgroup=f"1::{SCOPE}\n"))[0]), root=str(f[1])),
        "another container's existing scope": lambda tmp: mod.cgroup_dir_of_pid(4242, CID, proc=str((f := fake_proc(
            tmp, cgroup=f"0::/user.slice/docker-{'d' * 64}.scope\n", extra=(f"/user.slice/docker-{'d' * 64}.scope",)
            ))[0]), root=str(f[1])),
        "a .. in an existing scope's path": lambda tmp: mod.cgroup_dir_of_pid(4242, CID, proc=str((f := fake_proc(
            tmp, cgroup=f"0::/zz/..{SCOPE}\n", extra=("/zz",)))[0]), root=str(f[1])),
        "the scope folder a link": lambda tmp: mod.cgroup_dir_of_pid(4242, CID, proc=str((f := fake_proc(
            tmp, link=True))[0]), root=str(f[1])),
    }
    for why, fn in bad.items():
        with tempfile.TemporaryDirectory() as t:
            try:
                fn(Path(t))
                out.append(f"B11.derived: {why} was not refused")
            except mod.BuilderRefused:
                pass
            except Exception as e:  # noqa: BLE001
                out.append(f"B11.derived: {why} raised {type(e).__name__}, not BuilderRefused")
    # production's readers read through production's own runtime (a DockerRuntime since the bring-up, glitch-6b
    # 15 Oct 2026; stood in here by an InspectBox, so no process is started)
    prod_box = InspectBox()
    with mock.patch.object(rt, "DockerRuntime", lambda: prod_box), \
            mock.patch.object(mod, "uid_map_of_pid", lambda pid: ("uid", pid)), \
            mock.patch.object(mod, "cgroup_dir_of_pid", lambda pid, cid: ("cg", pid, cid)):
        got = mod.production_builders()
        take = types.SimpleNamespace(launched=types.SimpleNamespace(take_id=CID))
        if got["runtime"] is not prod_box:
            out.append(f"B11.derived: production's runtime is {got['runtime']!r}")
        for name, want in (("uid_map", ("uid", 4242)), ("cgroup_dir_for", ("cg", 4242, CID))):
            if not callable(got[name]) or got[name](take) != want:
                out.append(f"B11.derived: production {name} does not read through production's runtime")
        if [c[-1] for c in prod_box.calls] != [CID, CID]:
            out.append(f"B11.derived: production's readers did not inspect the take: {prod_box.calls}")
    for name, reader in zip(("uid_map", "cgroup_dir_for"), mod.run_time_readers(lambda: mod.Missing("synthetic"))):
        try:                               # with no runtime yet, a reader refuses by name, never a silent default
            reader(take)
            out.append(f"B11.derived: the {name} reader read with no runtime")
        except mod.BuilderRefused:
            pass
    # the readers over a runtime given at call time: inspect for the take's own id, then its pid's map and scope
    seen, box = [], [None]
    with mock.patch.object(mod, "uid_map_of_pid", lambda pid: seen.append(("uid", pid)) or "the-map"), \
            mock.patch.object(mod, "cgroup_dir_of_pid", lambda pid, cid: seen.append(("cg", pid, cid)) or "the-dir"):
        uid_map, cgroup_dir_for = mod.run_time_readers(lambda: box[0])
        box[0] = InspectBox()                      # the runtime exists only after the readers were made
        got_map, got_dir = uid_map(take), cgroup_dir_for(take)
        if (got_map, got_dir) != ("the-map", "the-dir") or seen != [("uid", 4242), ("cg", 4242, CID)]:
            out.append(f"B11.derived: the readers gave {(got_map, got_dir)} over {seen}")
        if [c[-1] for c in box[0].calls] != [CID, CID]:
            out.append(f"B11.derived: inspect was not run for the take's own id: {box[0].calls}")
        box[0] = object()                          # no run(): refused by name
        try:
            cgroup_dir_for(take)
            out.append("B11.derived: a runtime with no run() was used")
        except mod.BuilderRefused:
            pass
    return out


class B11Derived(Case):
    def test_cgroup_and_uid_map_are_derived_at_run_time(self):
        self.assertEqual(b11_problems(wb()), [])


# ------------------------------------------------------------------------------------------------- B12
# glitch-06's queue item 3 and review NOTE S-2: the box's pinned scanner (scan_record.real_rules_scanner(), box 35e61dec)
# is built once per walk with build(runtime, report_dir), each walk a fresh, empty report folder, and a real walk (the
# production builders) scans only with that build's product: a test fake never reaches one.
class FakePinned:
    """Stands in for the box's RealRulesScanner: not callable; build(runtime, report_dir) -> scan(paths)."""

    def __init__(self, product=None):
        self.builds = []
        self.product = product

    def build(self, runtime, report_dir):
        self.builds.append((runtime, report_dir, os.path.isdir(report_dir) and not os.listdir(report_dir)))
        return self.product if self.product is not None else (lambda paths: [])


@contextlib.contextmanager
def pinned_class():
    """box/rules_scanner.py's RealRulesScanner (box 8ad2978a) when the module is on this tree; on a branch without it,
    a stand-in module of that exact name holding the class, so walk_builders binds by module and class identity
    either way (never a create=True patch of another module)."""
    import importlib.machinery
    import importlib.util
    if importlib.util.find_spec("box.rules_scanner") is not None:
        from box import rules_scanner
        yield rules_scanner.RealRulesScanner
        return
    fake = types.ModuleType("box.rules_scanner")
    fake.__spec__ = importlib.machinery.ModuleSpec("box.rules_scanner", None)

    class RealRulesScanner:
        __slots__ = ("build", "version", "sha256", "binary")

        def __init__(self, build, version, sha256, binary):
            self.build, self.version, self.sha256, self.binary = build, version, sha256, binary
    RealRulesScanner.__module__ = "box.rules_scanner"
    fake.RealRulesScanner = RealRulesScanner
    import box
    with mock.patch.dict(sys.modules, {"box.rules_scanner": fake}), \
            mock.patch.object(box, "rules_scanner", fake, create=True):
        yield RealRulesScanner


@problems_by_assertion("B12.scanner")
def b12_problems(mod) -> list:
    out = []
    if not callable(getattr(mod, "walk_rules_scanner", None)) or not hasattr(mod, "BuiltRulesScan"):
        return ["B12.scanner: walk_builders has no walk_rules_scanner or BuiltRulesScan"]
    fake = lambda paths: []  # noqa: E731
    if mod.walk_rules_scanner(fake, "rt", "/nonexistent", real=False) is not fake:
        out.append("B12.scanner: an injected scan is not passed through on a test walk")
    with tempfile.TemporaryDirectory() as parent:
        pinned = FakePinned()
        a = mod.walk_rules_scanner(pinned, "rt", parent, real=False)
        b = mod.walk_rules_scanner(pinned, "rt", parent, real=False)
        dirs = [d for _, d, _ in pinned.builds]
        if not (isinstance(a, mod.BuiltRulesScan) and callable(a) and a(["x"]) == []):
            out.append(f"B12.scanner: the build's product is not handed on as a BuiltRulesScan: {a!r}")
        if len(set(dirs)) != 2 or not all(empty for _, _, empty in pinned.builds) or not all(
                os.path.dirname(d) == os.path.realpath(parent) or os.path.dirname(d) == parent for d in dirs):
            out.append(f"B12.scanner: each walk did not get a fresh, empty report folder under the parent: "
                       f"{pinned.builds}")
        if a is b:
            out.append("B12.scanner: two walks share one built scan")
        for why, bad in (("a build giving a non-callable", FakePinned(product="not callable")),
                         ("neither a scan nor a build", object())):
            try:
                mod.walk_rules_scanner(bad, "rt", parent, real=False)
                out.append(f"B12.scanner: {why} was accepted")
            except mod.BuilderRefused:
                pass
        class RealRulesScanner(FakePinned):          # the right name, from another module: never the pinned class
            pass
        with pinned_class() as pinned:
            for why, scanner in (("a plain callable", fake), ("another type with a build", FakePinned()),
                                 ("a same-named class from another module", RealRulesScanner())):
                try:
                    mod.walk_rules_scanner(scanner, "rt", parent, real=True)
                    out.append(f"B12.scanner: a real walk took {why}")
                except mod.BuilderRefused:
                    pass
            builds = []
            real = pinned(lambda runtime, report_dir: builds.append(report_dir) or (lambda paths: []),
                          "8.30.1", "0" * 64, "/synthetic/gitleaks")
            got = mod.walk_rules_scanner(real, "rt", parent, real=True)
            if not isinstance(got, mod.BuiltRulesScan) or len(builds) != 1:
                out.append(f"B12.scanner: a real walk did not take the pinned scanner's build: {got!r}")
    import importlib.util
    with pinned_class() as pinned:
        if mod.pinned_scanner_class() is not pinned:
            out.append("B12.scanner: the pinned class is not rules_scanner.RealRulesScanner")
        with mock.patch.object(importlib.util, "find_spec", lambda name, *a: None):
            if mod.pinned_scanner_class() is not None:       # absent by find_spec: None, never an import
                out.append("B12.scanner: a tree without box/rules_scanner.py still gave a pinned class")
    try:
        mod.BuiltRulesScan(lambda paths: [], "/x", None, object())
        out.append("B12.scanner: a BuiltRulesScan was made outside walk_rules_scanner")
    except mod.BuilderRefused:
        pass
    return out


class B12Scanner(Case):
    def test_the_scanner_is_built_per_walk_and_bound_on_a_real_walk(self):
        self.assertEqual(b12_problems(wb()), [])

    def test_a_pinned_scanner_is_built_once_for_a_walk(self):
        """A builder set whose scanner is a pinned one (not callable): the walk's driver and repo get its build's
        product, built once, over a fresh, empty report folder, and the walk commits."""
        with fake_world() as w:
            pinned = FakePinned()
            builders = dict(w.builders, rules_scanner=pinned)
            code, out, err = self.must("B12.scanner", w.main, w.argv(), builders)
            self.assertEqual(code, 0, f"B12.scanner: the walk with a pinned scanner did not commit: {err[-600:]}")
            self.assertEqual(len(pinned.builds), 1, f"B12.scanner: built {len(pinned.builds)} times, not once")
            self.assertTrue(pinned.builds[0][2], "B12.scanner: the report folder was not fresh and empty")

    def test_the_production_road_refuses_a_fake_scanner(self):
        """The command line with no builder set handed in (a real walk): a fake scan in the production builders is
        refused by name before the walk's driver is built."""
        with fake_world() as w:
            mod = sys.modules["walk_builders"]
            fake_set = dict(w.builders)
            drive = MODS["drive"]
            with mock.patch.object(mod, "production_builders", lambda: fake_set), \
                    tbi.spying(tbi.Spy()), mock.patch.object(drive._mode_binding, "HERE", w.root), \
                    generator(sha=pin(w.row["task"], w.row["half"])):
                code, out, err = run_main(w.argv(), None)
            self.assertEqual(code, 2, f"B12.scanner: a real walk ran with a fake scan: {err[-600:]}")
            self.assertIn("a real walk scans only with the pinned scanner", err,
                          "B12.scanner: the refusal is not the real walk's pinned-scanner rule")


# ------------------------------------------------------------------------------------------------- B13
# The Codex lease road (glitch-06, 14 Oct 2026; the box contract of live-box-2026-10-13.md, "For the harness lane: the
# run_take contract to call"). This tree may lack the box's run_take.NO_LOGIN, CODEX_SUBSCRIPTION_READY, place_lease and
# walk_builders.lease_secrets (scan_record.read_lease_tokens): each is faked here at that boundary, by its contract, and
# the integration merge must prove the real ones meet it (the lane report names what).
# Synthetic lease values, at least 20 characters, low entropy on purpose (never real, never key-shaped), and with no
# word preflight's CREDENTIAL_LIKE reads, so a folder named with one passes the name rule (NIT 5's point).
REFRESH = "synthetic-lease-two-" + "b" * 12
REFRESHED = "synthetic-lease-three-" + "c" * 12


def test_jwt(exp, label="synthetic-lease-one") -> str:
    """Round 17 B5: a TEST DATA access token of a JWT's shape (built at run time, never a literal: an unsigned
    header, a payload of `exp` and a test-data label, a fixed low-entropy signature), so the walk-start check can read
    its `exp` as Codex's parse_jwt_expiration does. `exp` None leaves the claim out."""
    def part(doc):
        return base64.urlsafe_b64encode(json.dumps(doc, separators=(",", ":")).encode()).rstrip(b"=").decode()
    claims = {"test_data": label} if exp is None else {"exp": exp, "test_data": label}
    return ".".join((part({"alg": "none", "typ": "JWT"}), part(claims), "synthetic-signature"))


ACCESS = test_jwt(4102444800)          # 2100-01-01T00:00:00Z: a lease far from expiry, for every road but B5's own


def iso_utc(t: float) -> str:
    """`t` as auth.json's last_refresh: RFC 3339 in UTC, with Codex's (chrono's) nanosecond fraction."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(t))) + f".{int((t % 1) * 1e9):09d}Z"
# Round 17 B5: the walk budget a lease road's rig hands CodexLeaseRoad (TEST DATA: one turn of the pre-registered
# budgets, 900 s plus 180 s); its leases (ACCESS) are far from expiry.
RIG_WALK_S = 900 + 180
# Round 17 B3: a take's uid map, TEST DATA in athena's measured shape (the agent, 10001, maps to host 110000).
TAKE_UID_MAP = ((0, 1000, 1), (1, 100000, 65536))


def lease_file(tmp: Path, access=ACCESS, refresh=REFRESH, last_refresh="now") -> Path:
    """A TEST DATA lease in auth.json's shape (round 17 B5: with last_refresh, now by default; None leaves it out)."""
    f = tmp / "lease-src" / "auth.json"
    f.parent.mkdir(mode=0o700, exist_ok=True)
    doc = {"tokens": {"access_token": access, "refresh_token": refresh}}
    if last_refresh is not None:
        doc["last_refresh"] = iso_utc(time.time()) if last_refresh == "now" else last_refresh
    f.write_text(json.dumps(doc))
    os.chmod(f, 0o600)
    return f


def fake_place_lease(placed: list):
    """run_take.place_lease's contract: the source copied into the config folder as auth.json (mode 600, never over an
    existing one), its placement record returned (round 17 B3: the path, the folder's device and inode and the file's
    read-back facts, unbound to any uid map); refused (NotReady) while the gate is closed."""
    def place(src, config_dir):
        if rt.__dict__.get("CODEX_SUBSCRIPTION_READY") is not True:
            raise rt.NotReady("synthetic: CODEX_SUBSCRIPTION_NOT_READY")
        dst = os.path.join(config_dir, "auth.json")
        fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(Path(src).read_bytes())
        placed.append((src, config_dir, dst))
        st, cst = os.lstat(dst), os.lstat(config_dir)
        return rt.LeasePlacement(path=dst, folder_dev=cst.st_dev, folder_ino=cst.st_ino, dev=st.st_dev, ino=st.st_ino,
                                 mode=st.st_mode, nlink=st.st_nlink, uid=st.st_uid, size=st.st_size)
    return place


# Round 10 ruling 2 (glitch-b5, Sat 17 Oct 2026; the T4 plan's section 9): every codex and gemini take refuses before
# launch, by name, until the account record (walk_builders.ACCOUNT_EMAILS) exists; the vendor rows here run on a TEST
# DATA record, clearly fake addresses under the reserved .invalid domain, never a real account's.
TEST_ACCOUNT_EMAILS = {"operator": "operator@example.invalid", "codex": "codex-account@example.invalid",
                       "gemini": "gemini-account@example.invalid"}
# Round 10 ruling 4: a vendor take's secrets() end with these two pairs, the operator's address and its account's.
CODEX_EMAIL_PAIRS = [("email", TEST_ACCOUNT_EMAILS["operator"]), ("email", TEST_ACCOUNT_EMAILS["codex"])]
GEMINI_EMAIL_PAIRS = [("email", TEST_ACCOUNT_EMAILS["operator"]), ("email", TEST_ACCOUNT_EMAILS["gemini"])]


def account_record_file(folder: Path, record=None) -> Path:
    """A TEST DATA account record, mode 600, in `folder` (outside every repository)."""
    f = Path(folder) / "account-emails.json"
    f.write_text(json.dumps(TEST_ACCOUNT_EMAILS if record is None else record))
    os.chmod(f, 0o600)
    return f


@contextlib.contextmanager
def account_boundary(mod, record=None):
    """mod.account_emails_path patched to a TEST DATA record for the block (round 10 ruling 2's fail-closed road)."""
    with tempfile.TemporaryDirectory() as t:
        f = account_record_file(Path(t), record)
        with mock.patch.object(mod, "account_emails_path", lambda: str(f)):
            yield f


def fake_lease_secrets(reads: list, mod=None):
    """walk_builders.lease_secrets' contract (box b9f876b5): every access_token and refresh_token in auth.json read at
    take start (a missing file raises: no take), read again at each call, every value read kept; with `mod`, its
    account record read first (round 10 ruling 2: no record, no Codex take) and again at each call, its two
    addresses the secrets' last pairs (ruling 4)."""
    def lease_secrets(auth_path):
        if mod is not None:
            mod.account_emails(rt.CODEX)

        def tokens():
            doc = json.loads(Path(auth_path).read_text())
            reads.append(auth_path)
            return [doc["tokens"]["access_token"], doc["tokens"]["refresh_token"]]
        seen = list(tokens())

        def secrets():
            for v in tokens():
                if v not in seen:
                    seen.append(v)
            emails = [("email", a) for a in mod.account_emails(rt.CODEX)] if mod is not None else []
            return [("token", v) for v in seen] + emails
        return secrets
    return lease_secrets


@contextlib.contextmanager
def lease_boundary(mod, *, ready=True):
    """The box's symbols at the boundary: the gate (open by default), place_lease, NO_LOGIN, and lease_secrets."""
    placed, reads = [], []
    with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", ready, create=True), \
            mock.patch.object(rt, "NO_LOGIN", "-", create=True), \
            mock.patch.object(rt, "place_lease", fake_place_lease(placed), create=True), \
            mock.patch.object(mod, "lease_secrets", fake_lease_secrets(reads, mod), create=True):
        yield placed, reads


def codex_cell() -> dict:
    cell = {k: tww.the_row()[k] for k in ("task", "half", "wording")}
    import prereg
    row = next(r for r in prereg.load()["rows"] if r["arm"] == "O" and all(r[k] == cell[k] for k in cell))
    return dict(cell, arm="O", model=row["model"])


@problems_by_assertion("B13.login")
def b13_login_problems(mod) -> list:
    out = []
    if mod.login_name(rt.CODEX) != "-" or getattr(mod, "NO_LOGIN", None) != "-":
        out.append(f"B13.login: a Codex row's login name is {mod.login_name(rt.CODEX)!r}, not NO_LOGIN")
    if hasattr(rt, "NO_LOGIN") and rt.NO_LOGIN != mod.NO_LOGIN:
        out.append(f"B13.login: walk_builders.NO_LOGIN {mod.NO_LOGIN!r} is not run_take.NO_LOGIN {rt.NO_LOGIN!r}")
    if mod.login_name(rt.CLAUDE_CODE) != rt.LOGIN_VARIABLE[rt.CLAUDE_CODE]:
        out.append("B13.login: Claude Code's login name changed")
    good = str(login_file(f"{LOGIN}={tbi.TOKEN}\n"))
    with mock.patch.dict(rt.LOGIN_VARIABLE, {rt.GEMINI: "-"}):
        try:
            mod.login_name(rt.GEMINI)
            out.append("B13.login: a non-Codex row took NO_LOGIN")
        except mod.BuilderRefused:
            pass
    for label, fn in (("login_file_by_name of '-'", lambda: mod.login_file_by_name("-", rt.CLAUDE_CODE)),
                      ("login_file_by_name for Codex", lambda: mod.login_file_by_name(good, rt.CODEX)),
                      ("login_secrets for Codex", lambda: mod.login_secrets(good, rt.CODEX)),
                      ("login_secrets of '-'", lambda: mod.login_secrets("-", rt.CLAUDE_CODE))):
        with mock.patch.object(os, "open", side_effect=AssertionError("a login file was opened")):
            try:
                fn()
                out.append(f"B13.login: {label} was admitted")
            except mod.BuilderRefused as e:
                if "the lease" not in str(e):
                    out.append(f"B13.login: {label} refused for another reason: {e}")
            except AssertionError:
                out.append(f"B13.login: {label} opened a file before refusing")
    with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", True, create=True):
        if mod.codex_gate_problem() is not None:
            out.append("B13.login: an open gate is a problem")
    with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", False, create=True):
        if "closed" not in (mod.codex_gate_problem() or ""):
            out.append(f"B13.login: a closed gate reads {mod.codex_gate_problem()!r}")
    for value in (1, "True", None):
        with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", value, create=True):
            if mod.codex_gate_problem() is None:
                out.append(f"B13.login: a gate of {value!r} reads open")
    if not hasattr(rt, "CODEX_SUBSCRIPTION_READY") and "not on this tree" not in (mod.codex_gate_problem() or ""):
        out.append(f"B13.login: an absent gate reads {mod.codex_gate_problem()!r}")
    return out


@problems_by_assertion("B13.prepare")
def b13_prepare_problems(mod, tmp: Path) -> list:
    """prepare routes a Codex row past every login-file reader: refused while the gate is closed or the lease source
    is missing, before the run tree; else its login is NO_LOGIN and the run tree is built."""
    out = []
    built = []
    args = types.SimpleNamespace(walk="w-0001", **codex_cell())
    src = str(lease_file(tmp))
    base = {"agent_version": "0.162.1",
            "login_path": "/synthetic/never-read", "run_tree_origin": ("/synthetic/repo", "0" * 40),
            "run_tree_exclude": ["evals"]}
    with mock.patch.object(mod, "build_run_tree", lambda *a, **k: built.append(a) or tmp / "tree"), \
            mock.patch.object(mod, "login_file_by_name", side_effect=AssertionError("login_file_by_name")):
        for label, ready, lease, words in (("a closed gate", False, src, "gate is closed"),
                                           ("no gate", None, src, "not on this tree"),
                                           ("a missing lease", True, mod.Missing("synthetic: not registered"),
                                            "synthetic: not registered"),
                                           ("a relative lease", True, "lease/auth.json", "not an absolute path"),
                                           ("no lease", True, None, "not an absolute path")):
            with lease_boundary(mod, ready=ready):
                try:
                    mod.prepare(dict(base, lease_path=lease), args)
                    out.append(f"B13.prepare: {label} was admitted")
                except mod.BuilderRefused as e:
                    if words not in str(e):
                        out.append(f"B13.prepare: {label} refused for another reason: {e}")
                except AssertionError as e:
                    out.append(f"B13.prepare: {label} reached {e}")
        if built:
            out.append(f"B13.prepare: a refused Codex row built its run tree: {built}")
        with lease_boundary(mod):
            try:
                row, login, tree = mod.prepare(dict(base, lease_path=src), args)
                if (login, row["agent"]["harness"], row["arm"], len(built)) != ("-", rt.CODEX, "O", 1):
                    out.append(f"B13.prepare: an admitted Codex row gave {login!r}, {row['agent']}, {len(built)}")
            except Exception as e:  # noqa: BLE001
                out.append(f"B13.prepare: an admitted Codex row raised {type(e).__name__}: {e}")
    return out


@problems_by_assertion("B13.secrets")
def b13_secrets_problems(mod, tmp: Path) -> list:
    """NIT 4 (box review): a Codex walk's driver and its WalkRepo get one and the same secrets(), the lease road's;
    the lease is placed in the driver's spec_for (after make_config_dir), read at once, and before that nothing
    scans. On a TEST DATA account record (round 10 ruling 2)."""
    with account_boundary(mod):
        return _b13_secrets_problems(mod, tmp)


def _b13_secrets_problems(mod, tmp: Path) -> list:
    out = []
    drive = MODS["drive"]
    got = {}
    src = str(lease_file(tmp))
    cfg = tmp / "cfg"
    cfg.mkdir(mode=0o700)
    specs = []
    take, maps = types.SimpleNamespace(launched="synthetic"), []
    # round 17 B3: the walk's uid map reader (production: run_time_readers' uid_map_of_pid), TEST DATA here
    uid_map = lambda t: maps.append(t) or TAKE_UID_MAP  # noqa: E731
    builders = {"lease_path": src, "rules_scanner": lambda paths: [], "runtime": "rt", "config_parent": str(tmp),
                "budgets": (600, 5, 1), "take_spec": lambda r, c, t: specs.append((r["arm"], c, t)) or "spec",
                "sidecar_for": None, "proxy": None, "lock_path": None, "hosts": None, "cgroup_dir_for": lambda t: "",
                "pin_for": None, "uid_map": uid_map, "clock": time.time, "sleep": None,
                "ownership": None, "settings_guard": None, "machine_gate": None,
                # round 17 B5: the walk's script, TEST DATA (two steps, one with a recovery: three turns)
                "design_for": lambda r, t: types.SimpleNamespace(script=[
                    {"n": 1, "line": "one"}, {"n": 2, "line": "two", "recovery": {"send": "again"}}])}
    row = {"walk": "w-0001", "arm": "O", "model": "gpt-6.1-sol",            # round 17 B6: spec_for writes its config
           "agent": {"harness": rt.CODEX, "version": "0.162.1"}}
    with lease_boundary(mod) as (placed, reads), \
            mock.patch.object(drive, "walk_driver", lambda **kw: got.setdefault("driver", kw) and "driver"), \
            mock.patch.object(drive, "WalkRepo", lambda **kw: got.setdefault("repo", kw) and "repo"), \
            mock.patch.object(drive, "records_repo", lambda root: "/synthetic/repo"), \
            mock.patch.object(mod, "build_walk_fixture", lambda r, t, p: ({"sha256": "0" * 64}, "/synthetic/src")), \
            mock.patch.object(mod, "walk_identity", lambda *a, **k: {"walk": "w-0001"}), \
            mock.patch.object(mod, "login_secrets", side_effect=AssertionError("login_secrets")):
        try:
            mod.walk_driver_for(builders, row, "-", tmp / "tree")
        except Exception as e:  # noqa: BLE001
            return [f"B13.secrets: walk_driver_for raised {type(e).__name__}: {e}"]
        s_driver, s_repo = got["driver"]["secrets"], got["repo"]["secrets"]
        road = getattr(s_driver, "__self__", None)
        if s_driver is not s_repo or not isinstance(road, mod.CodexLeaseRoad):
            out.append(f"B13.secrets: the driver got {s_driver!r} and WalkRepo {s_repo!r}, not one lease road's")
        if (getattr(road, "walk_s", None), getattr(road, "clock", None)) != (3 * (600 + 5), builders["clock"]):
            out.append(f"B13.secrets: the lease road's walk budget and clock are {getattr(road, 'walk_s', None)!r}, "
                       f"{getattr(road, 'clock', None)!r}, not three turns of the walk's budgets and its clock")
        login_for = got["driver"]["login_file"]       # review MINOR 1: the take's placed lease, never "-"
        if not callable(login_for) or getattr(login_for, "__self__", None) is not road:
            out.append(f"B13.secrets: the driver's login_file is {login_for!r}, not the lease road's per-take path")
        for what, fn in (("the secrets", s_driver), ("the login file", lambda: login_for(take))):
            try:
                fn()
                out.append(f"B13.secrets: {what} read before any lease was placed")
            except mod.BuilderRefused:
                pass
        spec = got["driver"]["spec_for"](row, str(cfg))
        lease = login_for(take) if callable(login_for) else None      # round 17 B3: the placement record, bound
        if getattr(lease, "path", lease) != str(cfg / "auth.json") or getattr(lease, "uid_map", None) != TAKE_UID_MAP \
                or maps[-1:] != [take]:
            out.append(f"B13.secrets: the driver's login file after placement is {lease!r}, not the placement record "
                       f"bound to the take's uid map")
        if spec != "spec" or specs != [("O", str(cfg), str(tmp / "tree"))]:
            out.append(f"B13.secrets: spec_for gave {spec!r} over {specs}")
        if placed != [(src, str(cfg), str(cfg / "auth.json"))] or reads != [str(cfg / "auth.json")]:
            out.append(f"B13.secrets: the lease was not placed then read at take start: {placed} {reads}")
        if s_repo() != [("token", ACCESS), ("token", REFRESH)] + CODEX_EMAIL_PAIRS:     # round 10 ruling 4
            out.append(f"B13.secrets: WalkRepo's secrets are {s_repo()}")
        try:
            got["driver"]["spec_for"](row, str(cfg))
            out.append("B13.secrets: a second lease was placed for one walk")
        except (mod.BuilderRefused, rt.Refused):    # round 17 B6: the config write into the used folder refuses first
            pass
        if len(placed) != 1:
            out.append(f"B13.secrets: a second spec_for placed a lease: {placed}")
        with mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", False):     # review NIT 4: the gate first
            again = mod.CodexLeaseRoad(src)
            try:
                again.place(str(tmp))
                out.append("B13.secrets: a closed gate placed a lease")
            except mod.BuilderRefused as e:
                if "gate is closed" not in str(e) or len(placed) != 1 or again.placed is not None:
                    out.append(f"B13.secrets: a closed gate reached place_lease or refused for another reason: {e}")

        def refusing_map(t):
            raise mod.BuilderRefused("synthetic: the uid map cannot be read")
        timed = dict(walk_s=3 * 605, clock=time.time)
        for n, (label, road_) in enumerate((("a lease road with no uid map reader", mod.CodexLeaseRoad(src, **timed)),
                                            ("a uid map reader that refuses",
                                             mod.CodexLeaseRoad(src, uid_map=refusing_map, **timed)))):
            c = tmp / f"cfg-b3-{n}"                   # round 17 B3: no uid map, no login file
            c.mkdir(mode=0o700)
            try:
                road_.place(str(c))
                road_.login_file_for(take)
                out.append(f"B13.secrets: {label} gave a login file")
            except mod.BuilderRefused as e:
                if "uid map" not in str(e):
                    out.append(f"B13.secrets: {label} refused for another reason: {e}")
            except Exception as e:  # noqa: BLE001
                out.append(f"B13.secrets: {label} raised {type(e).__name__}: {e}")
        os.chmod(cfg / "auth.json", 0o600)          # the refresh rule: the host rewrites auth.json between turns
        (cfg / "auth.json").write_text(json.dumps({"tokens": {"access_token": REFRESHED, "refresh_token": REFRESH}}))
        if road.refreshed() != [("token", ACCESS), ("token", REFRESH), ("token", REFRESHED)] + CODEX_EMAIL_PAIRS:
            out.append(f"B13.secrets: after a refresh the secrets are {road.secrets()}")
    claude = {"walk": "w-0001", "arm": "A", "agent": {"harness": rt.CLAUDE_CODE, "version": "2.1.296"}}
    got.clear()
    marker = lambda: [("token", "x")]  # noqa: E731
    with lease_boundary(mod) as (placed, reads), \
            mock.patch.object(drive, "walk_driver", lambda **kw: got.setdefault("driver", kw) and "driver"), \
            mock.patch.object(drive, "WalkRepo", lambda **kw: got.setdefault("repo", kw) and "repo"), \
            mock.patch.object(drive, "records_repo", lambda root: "/synthetic/repo"), \
            mock.patch.object(mod, "build_walk_fixture", lambda r, t, p: ({"sha256": "0" * 64}, "/synthetic/src")), \
            mock.patch.object(mod, "walk_identity", lambda *a, **k: {"walk": "w-0001"}), \
            mock.patch.object(mod, "login_secrets", lambda login, harness: marker):
        mod.walk_driver_for(builders, claude, "/synthetic/login", tmp / "tree")
        got["driver"]["spec_for"](claude, str(tmp / "cfg2"))
        if got["driver"]["secrets"] is not marker or got["repo"]["secrets"] is not marker or placed:
            out.append("B13.secrets: a Claude walk's secrets are not its login file's, or it placed a lease")
    return out


@problems_by_assertion("B13.freshness")
def b13_freshness_problems(mod, tmp: Path) -> list:
    """Round 17 B5 (plan codex2-signin-road section 2): CodexLeaseRoad.place refuses by name, before anything is
    written, a lease whose access token's JWT exp leaves less than the walk's budget plus LEASE_START_MARGIN_S, or
    whose last_refresh is past LEASE_REFRESH_MAX_AGE_S, or either unreadable; no refusal carries a token. On TEST DATA
    leases and a fixed clock."""
    with account_boundary(mod):
        return _b13_freshness_problems(mod, tmp)


def _b13_freshness_problems(mod, tmp: Path) -> list:
    out = []
    now, walk_s = 2.0e9 + 0.25, 3 * (900 + 180)
    margin = getattr(mod, "LEASE_START_MARGIN_S", None)
    max_age = getattr(mod, "LEASE_REFRESH_MAX_AGE_S", None)
    if (margin, max_age) != (15 * 60, 7 * 24 * 3600):
        out.append(f"B13.freshness: the margin and the refresh age are {margin!r} and {max_age!r}, not 15 minutes "
                   f"and 7 days")
    day = 24 * 3600
    cases = (  # (label, exp, last_refresh, walk budget, clock, the refusal's words or None for admitted)
        ("a fresh lease", now + walk_s + 900 + 3600, iso_utc(now - day), walk_s, True, None),
        ("Codex's nanosecond last_refresh at an offset", now + walk_s + 901, iso_utc(now - day).replace(
            "Z", "+00:00"), walk_s, True, None),
        ("an access token 10 minutes from expiry", now + 600, iso_utc(now - day), walk_s, True, "minutes left"),
        ("an access token inside the margin", now + walk_s + 900 - 60, iso_utc(now - day), walk_s, True,
         "minutes left"),
        ("an access token past the walk alone", now + walk_s + 60, iso_utc(now - day), walk_s, True, "minutes left"),
        ("an expired access token", now - 60, iso_utc(now - day), walk_s, True, "minutes left"),
        ("an access token with no exp", None, iso_utc(now - day), walk_s, True, "exp"),
        ("an access token not a JWT", "plain", iso_utc(now - day), walk_s, True, "exp"),
        ("an exp that is not a number", "text", iso_utc(now - day), walk_s, True, "exp"),
        ("an exp that is a boolean", "bool", iso_utc(now - day), walk_s, True, "exp"),
        ("an access token whose payload is not JSON", "garbled", iso_utc(now - day), walk_s, True, "exp"),
        ("a last_refresh 8 days ago", now + 30 * day, iso_utc(now - 8 * day), walk_s, True, "last_refresh"),
        ("a last_refresh 7 days and a minute ago", now + 30 * day, iso_utc(now - 7 * day - 60), walk_s, True,
         "last_refresh"),
        ("no last_refresh", now + 30 * day, None, walk_s, True, "last_refresh"),
        ("a last_refresh not a time", now + 30 * day, "yesterday", walk_s, True, "last_refresh"),
        ("a last_refresh of month 13", now + 30 * day, "2033-13-01T00:00:00Z", walk_s, True, "last_refresh"),
        ("a last_refresh 7 days and 3 hours ago, written at +05:00", now + 30 * day,
         iso_utc(now - 7 * day - 3 * 3600 + 5 * 3600).replace("Z", "+05:00"), walk_s, True, "last_refresh"),
        ("a last_refresh 7 days and 3 hours ago, written at -05:00", now + 30 * day,
         iso_utc(now - 7 * day - 3 * 3600 - 5 * 3600).replace("Z", "-05:00"), walk_s, True, "last_refresh"),
        ("a last_refresh with no fraction", now + 30 * day, iso_utc(now - day).split(".")[0] + "Z", walk_s, True,
         None),
        ("a last_refresh inside 7 days by its fraction alone", now + 30 * day,
         iso_utc(int(now) - 7 * day + 0.5), walk_s, True, None),
        ("a lease that is not JSON", "not-json", iso_utc(now - day), walk_s, True, "cannot be read"),
        ("no walk budget", now + 30 * day, iso_utc(now - day), None, True, "walk budget"),
        ("a walk budget of zero", now + 30 * day, iso_utc(now - day), 0, True, "walk budget"),
        ("a walk budget that is a boolean", now + 30 * day, iso_utc(now - day), True, True, "walk budget"),
        ("no clock", now + 30 * day, iso_utc(now - day), walk_s, False, "clock"))
    with lease_boundary(mod) as (placed, reads):
        for n, (label, exp, refreshed, budget, clocked, words) in enumerate(cases):
            home = tmp / f"fresh-{n}"
            home.mkdir()
            if exp == "plain":
                access = "synthetic-lease-plain-" + "d" * 12
            elif exp == "text":
                access = test_jwt("soon")
            elif exp == "bool":
                access = test_jwt(True)
            elif exp == "garbled":
                access = "synthetic-header.not-a-json-payload.synthetic-signature"
            else:
                access = test_jwt(exp)
            src = str(lease_file(home, access=access, last_refresh=refreshed))
            if exp == "not-json":
                Path(src).write_text("{not json")
            cfg = home / "cfg"
            cfg.mkdir(mode=0o700)
            before = len(placed)
            try:
                road_ = mod.CodexLeaseRoad(src, walk_s=budget, clock=(lambda: now) if clocked else None)
                road_.place(str(cfg))
                if words is not None:
                    out.append(f"B13.freshness: {label} was placed")
            except mod.BuilderRefused as e:
                msg = str(e)
                if words is None:
                    out.append(f"B13.freshness: {label} was refused: {msg}")
                elif words not in msg:
                    out.append(f"B13.freshness: {label} refused for another reason: {msg}")
                for secret in (access, REFRESH, access.split(".")[1] if "." in access else access):
                    if secret in msg:
                        out.append(f"B13.freshness: the refusal of {label} carries a token")
                if len(placed) != before or (cfg / "auth.json").exists():
                    out.append(f"B13.freshness: {label} was refused after the lease was written")
            except Exception as e:  # noqa: BLE001
                out.append(f"B13.freshness: {label} raised {type(e).__name__}: {str(e)[:200]}")
    return out


@problems_by_assertion("B13.adapter")
def b13_adapter_problems(mod) -> list:
    """drive.harness_adapter_for resolves a callable login_file per take (review MINOR 1: the box's Codex exec reads
    the take's placed cfg/auth.json), and still passes a plain path as given."""
    out = []
    drive = MODS["drive"]
    take = types.SimpleNamespace(launched=types.SimpleNamespace(take_id="c" * 64, spec=types.SimpleNamespace(
        run_tree="/synthetic/tree")), config_dir="/synthetic/cfg",
        identity={"session_id": "00000000-0000-4000-8000-000000000001"})
    seen = []
    for harness, mode, login in ((rt.CODEX, "bypass", lambda t: seen.append(t) or t.config_dir + "/auth.json"),
                                 (rt.CLAUDE_CODE, "bypassPermissions", "/synthetic/login")):
        make = drive.harness_adapter_for(runtime=None, login_file=login, counters_for=lambda t: {},
                                         pin_for=lambda r, m=mode: {"permission_mode": m, "version": "1.2.3"},
                                         clock=lambda: 0, config_view=lambda t: (None, None))
        try:
            a = make({"agent": {"harness": harness}, "model": "synthetic-model"}, take)
        except Exception as e:  # noqa: BLE001
            out.append(f"B13.adapter: {harness} adapter not built: {type(e).__name__}: {e}")
            continue
        want = "/synthetic/cfg/auth.json" if callable(login) else login
        if a.login_file != want:
            out.append(f"B13.adapter: the {harness} adapter's login file is {a.login_file!r}, not {want!r}")
    if seen != [take]:
        out.append(f"B13.adapter: the login file was not resolved once for the take: {seen}")
    return out


@problems_by_assertion("B13.environment")
def b13_environment_problems(mod) -> list:
    """drive's environment record: a Codex row sets no login variable (its login is the lease); Claude's is set."""
    out = []
    drive = MODS["drive"]
    for harness, want in ((rt.CODEX, None), (rt.CLAUDE_CODE, rt.LOGIN_VARIABLE[rt.CLAUDE_CODE])):
        seen = {}
        take = types.SimpleNamespace(launched=types.SimpleNamespace(spec=types.SimpleNamespace(run_tree="/s/tree")),
                                     identity={"session_id": "s", "row": None, "row_commit": None}, folder="/s/f")
        row = {"agent": {"harness": harness}, "task": "t", "half": "h", "model": "m"}
        with mock.patch.object(drive, "environment_record", lambda child, parent, **k: seen.setdefault("c", child)), \
                mock.patch.object(rt, "VENDOR_BILLING_ROUTE_VARIABLES",       # box 9d4bfd40 names Codex's; PENDING here
                                  dict(rt.VENDOR_BILLING_ROUTE_VARIABLES, **{rt.CODEX: ()})), \
                mock.patch.object(drive, "write_record_atomically", lambda *a: None), \
                mock.patch.object(drive, "money_line_names", lambda rec: []):
            adapter = types.SimpleNamespace(version=lambda: "v")
            drive.TakeDriver._environment(types.SimpleNamespace(), take, row, adapter)
        child = seen.get("c", {})
        set_names = sorted(k for k, v in child.items() if v == "set")
        if harness == rt.CODEX and (set_names or "-" in child or "CODEX_API_KEY" in child):
            out.append(f"B13.environment: a Codex row's child sets {set_names}")
        if harness != rt.CODEX and set_names != [want]:
            out.append(f"B13.environment: Claude Code's child sets {set_names}, not [{want}]")
    return out


# R1 (glitch-6b, 14 Oct 2026): B13 swaps walk_builders.lease_secrets for fake_lease_secrets at the boundary, so on a
# tree that carries the box's real one (b9f876b5, over scan_record.read_lease_tokens) no test drove it and the merged
# battery's sweep left 12 of its mutants alive. This contract is the one the integration lane proved with the real box
# symbols: auth.json's access and refresh tokens read at take start and kept, a refreshed value added at each later
# read, a missing lease file refused at take start. It runs both ways on every tree: over the real function where the
# tree carries it, and over B13's fake always, so the stand-in B13 uses is held to the same contract.
def _lease_reader_on_tree() -> bool:
    from box import scan_record
    return callable(getattr(scan_record, "read_lease_tokens", None))


REFRESHED_TWO = "synthetic-lease-four-" + "d" * 12
REFRESHED_THREE = "synthetic-lease-five-" + "e" * 12


@problems_by_assertion("B13.lease_secrets")
def lease_secrets_contract_problems(fn, tmp: Path, refusal) -> list:
    """fn is a lease_secrets: fn(auth_path) reads now (a missing file raises `refusal`) and returns secrets(), which
    re-reads auth.json and gives every value read so far, each once, in the order first read, then the account
    record's two addresses (round 10 ruling 4; run on account_boundary's TEST DATA record)."""
    out = []
    try:
        fn(str(tmp / "no-lease" / "auth.json"))
        out.append("B13.lease_secrets: a missing lease file was admitted at take start")
    except refusal:
        pass
    src = lease_file(tmp)
    secrets = fn(str(src))
    lease_file(tmp, REFRESHED, REFRESHED_TWO)         # both rewritten before the first scan: take start's values stay
    want = [("token", v) for v in (ACCESS, REFRESH, REFRESHED, REFRESHED_TWO)]
    if not callable(secrets) or secrets() != want + CODEX_EMAIL_PAIRS:
        return out + [f"B13.lease_secrets: the first scan's secrets are not {want}"]
    if secrets() != want + CODEX_EMAIL_PAIRS:
        out.append("B13.lease_secrets: a second scan of the same file changed the secrets")
    lease_file(tmp, REFRESHED, REFRESHED_THREE)       # the host's refresh between turns: one value added
    if secrets() != want + [("token", REFRESHED_THREE)] + CODEX_EMAIL_PAIRS:
        out.append("B13.lease_secrets: a refreshed value was not added after every value read before")
    return out


class B13Lease(Drafted):
    def test_a_codex_row_has_no_login_file(self):
        self.assertEqual(b13_login_problems(wb()), [])

    def test_prepare_routes_a_codex_row_to_the_lease(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(b13_prepare_problems(wb(), Path(t)), [])

    def test_the_driver_and_walkrepo_get_the_lease_secrets(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(b13_secrets_problems(wb(), Path(t)), [])

    def test_the_adapter_gets_the_takes_own_login_file(self):
        self.assertEqual(b13_adapter_problems(wb()), [])

    def test_the_walk_start_token_check(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(b13_freshness_problems(wb(), Path(t)), [])

    def test_the_environment_record_sets_no_codex_login(self):
        self.assertEqual(b13_environment_problems(wb()), [])

    def test_lease_secrets_meets_the_lease_contract_both_ways(self):
        """R1: the real lease_secrets where the tree carries it (synthetic lease files, mode 600, read by the real
        scan_record.read_lease_tokens), and B13's fake on every tree."""
        mod = wb()
        from box import preflight, scan_record
        reader = _lease_reader_on_tree()               # read now, not at import: a later merge cannot hide it
        self.assertEqual(callable(getattr(mod, "lease_secrets", None)), reader,
                         "B13.lease_secrets: walk_builders.lease_secrets and scan_record.read_lease_tokens disagree")
        # review of 83b83ea1..d78c8791, NIT 1: where the box's lease road is on the tree, the real half must run; a merge
        # that dropped both readers would otherwise fall back to the fake alone and still pass
        if "LEASE_CREDENTIAL" in vars(preflight) or callable(getattr(rt, "place_lease", None)):
            self.assertTrue(reader, "B13.lease_secrets: the box's lease road is on this tree but its lease reader "
                                    "(scan_record.read_lease_tokens, walk_builders.lease_secrets) is not")
        if reader:
            with tempfile.TemporaryDirectory() as t, account_boundary(mod):      # round 10 ruling 2: a TEST DATA record
                self.assertEqual(lease_secrets_contract_problems(mod.lease_secrets, Path(t), scan_record.LoginError),
                                 [])
        with tempfile.TemporaryDirectory() as t, account_boundary(mod):
            self.assertEqual(lease_secrets_contract_problems(fake_lease_secrets([], mod), Path(t), OSError), [])


# ------------------------------------------------------------------------------------------------- B14
# The Gemini walk wiring (glitch-06, 14 Oct 2026): a Gemini row is admitted by the r4-g key file the box records
# (run_take.WALK_LOGIN_FILES["r4-g"], box 1d32399b), Missing by name where the record is absent, checked by NAME like
# Claude's token (login_name GEMINI_API_KEY), and its login_secrets, the exact-value mask's values, go to the walk's
# driver and its WalkRepo alike. Synthetic, low-entropy key values only.
GEMINI_KEY = "synthetic-gemini-key-" + "a" * 12
WALK_GEMINI_ON_TREE = isinstance(getattr(rt, "WALK_LOGIN_FILES", None), dict) and "r4-g" in rt.WALK_LOGIN_FILES


def gemini_cell() -> dict:
    import prereg
    row = next(r for r in prereg.load()["rows"] if r["arm"] == "G")
    return {k: row[k] for k in ("task", "half", "wording", "arm", "model")}


@problems_by_assertion("B14.login")
def b14_login_problems(mod) -> list:
    out = []
    if mod.login_name(rt.GEMINI) != "GEMINI_API_KEY" or rt.LOGIN_VARIABLE[rt.GEMINI] != "GEMINI_API_KEY":
        out.append(f"B14.login: a Gemini row's login name is {mod.login_name(rt.GEMINI)!r}")
    if getattr(mod, "GEMINI_WALK_ACCOUNT", None) != "r4-g":
        out.append(f"B14.login: the Gemini walk account is {getattr(mod, 'GEMINI_WALK_ACCOUNT', None)!r}")
    path = "/synthetic/r4-g/gemini-walk-login"
    with walk_login_files({"claude1": SYNTHETIC_LOGIN, "r4-g": path}):
        if mod.walk_login_path("r4-g") != path or mod.production_builders()["gemini_login_path"] != path:
            out.append("B14.login: the Gemini login path is not the r4-g record")
        if mod.walk_login_path() != SYNTHETIC_LOGIN:
            out.append("B14.login: Claude's login path moved off claude1")
    with walk_login_files({"claude1": SYNTHETIC_LOGIN}):
        got = mod.production_builders()["gemini_login_path"]
        if not isinstance(got, mod.Missing) or "WALK_LOGIN_FILES['r4-g']" not in got.why:
            out.append(f"B14.login: no r4-g record gives {got!r}")
    with walk_login_files({"r4-g": "relative/gemini-walk-login"}):
        try:
            mod.walk_login_path("r4-g")
            out.append("B14.login: a relative r4-g record was taken")
        except mod.BuilderRefused as e:
            if "WALK_LOGIN_FILES['r4-g']" not in str(e):
                out.append(f"B14.login: the relative record's refusal names another record: {e}")
    return out


@problems_by_assertion("B14.prepare")
def b14_prepare_problems(mod, tmp: Path) -> list:
    """prepare admits a Gemini row by its key file, checked by name only; refuses it, before the run tree, while the
    key's file is Missing or not a GEMINI_API_KEY file."""
    out, built = [], []
    args = types.SimpleNamespace(walk="w-0001", **gemini_cell())
    good = str(login_file(f"GEMINI_API_KEY={GEMINI_KEY}\n"))
    claude = str(login_file(f"{LOGIN}={GEMINI_KEY}\n"))
    base = {"agent_version": "0.64.0", "login_path": "/synthetic/never-read",
            "run_tree_origin": ("/synthetic/repo", "0" * 40), "run_tree_exclude": ["evals"]}
    with mock.patch.object(mod, "build_run_tree", lambda *a, **k: built.append(a) or tmp / "tree"):
        for label, path, words in (("a missing key file", mod.Missing("synthetic: no r4-g record"),
                                    "synthetic: no r4-g record"),
                                   ("Claude's token file", claude, "does not start with GEMINI_API_KEY="),
                                   ("a relative path", "r4-g/gemini-walk-login", "absolute path")):
            try:
                mod.prepare(dict(base, gemini_login_path=path), args)
                out.append(f"B14.prepare: {label} was admitted")
            except mod.BuilderRefused as e:
                if words not in str(e):
                    out.append(f"B14.prepare: {label} refused for another reason: {e}")
                if GEMINI_KEY in str(e):
                    out.append(f"B14.prepare: {label}'s refusal carries the key")
        if built:
            out.append(f"B14.prepare: a refused Gemini row built its run tree: {built}")
        with mock.patch.object(os, "read", wraps=os.read) as reads:
            row, login, tree = mod.prepare(dict(base, gemini_login_path=good), args)
        if (row["agent"]["harness"], row["arm"], login, len(built)) != (rt.GEMINI, "G", good, 1):
            out.append(f"B14.prepare: an admitted Gemini row gave {row['agent']}, {login!r}, {len(built)}")
        if any(c.args[1] > len("GEMINI_API_KEY=") for c in reads.call_args_list):
            out.append("B14.prepare: more than the key's name was read")
        real_row = mod.walk_row                 # a harness the walk driver does not admit, refused before anything
        def other(*a, **k):
            return dict(real_row(*a, **k), agent={"harness": "synthetic-other", "version": "1.0.0"})
        with mock.patch.object(mod, "walk_row", other):
            try:
                mod.prepare(dict(base, gemini_login_path=good), args)
                out.append("B14.prepare: a row of an unknown harness was admitted")
            except mod.BuilderRefused as e:
                if "admits Claude Code, Gemini and" not in str(e):
                    out.append(f"B14.prepare: an unknown harness refused for another reason: {e}")
        if len(built) != 1:
            out.append(f"B14.prepare: an unknown harness built its run tree: {built}")
    return out


@problems_by_assertion("B14.secrets")
def b14_secrets_problems(mod, tmp: Path) -> list:
    """A Gemini walk's driver and its WalkRepo get one and the same secrets(): login_secrets over the key file, read
    only when the scan asks, giving the key's value as the exact-value mask's token. On a TEST DATA account record
    (round 10 ruling 2)."""
    with account_boundary(mod):
        return _b14_secrets_problems(mod, tmp)


def _b14_secrets_problems(mod, tmp: Path) -> list:
    out = []
    drive = MODS["drive"]
    got = {}
    good = str(login_file(f"GEMINI_API_KEY={GEMINI_KEY}\n"))
    builders = {"rules_scanner": lambda paths: [], "runtime": "rt", "config_parent": str(tmp), "budgets": (600, 5, 1),
                "take_spec": lambda r, c, t: "spec", "sidecar_for": None, "proxy": None, "lock_path": None,
                "hosts": None, "cgroup_dir_for": lambda t: "", "pin_for": None, "design_for": None, "uid_map": None,
                "clock": None, "sleep": None, "ownership": None, "settings_guard": None, "machine_gate": None}
    row = {"walk": "w-0001", "arm": "G", "agent": {"harness": rt.GEMINI, "version": "0.64.0"}}
    from box import scan_record
    reads = []
    real = scan_record.read_login
    with mock.patch.object(drive, "walk_driver", lambda **kw: got.setdefault("driver", kw) and "driver"), \
            mock.patch.object(drive, "WalkRepo", lambda **kw: got.setdefault("repo", kw) and "repo"), \
            mock.patch.object(drive, "records_repo", lambda root: "/synthetic/repo"), \
            mock.patch.object(mod, "build_walk_fixture", lambda r, t, p: ({"sha256": "0" * 64}, "/synthetic/src")), \
            mock.patch.object(mod, "walk_identity", lambda *a, **k: {"walk": "w-0001"}), \
            mock.patch.object(scan_record, "read_login", lambda *a, **k: reads.append(a) or real(*a, **k)):
        try:
            mod.walk_driver_for(builders, row, good, tmp / "tree")
        except Exception as e:  # noqa: BLE001
            return [f"B14.secrets: walk_driver_for raised {type(e).__name__}: {e}"]
        if reads:
            out.append("B14.secrets: the key was read before a scan asked")
        s_driver, s_repo = got["driver"]["secrets"], got["repo"]["secrets"]
        if s_driver is not s_repo or got["driver"]["login_file"] != good:
            out.append(f"B14.secrets: the driver got {s_driver!r} and WalkRepo {s_repo!r} over "
                       f"{got['driver']['login_file']!r}")
        if s_repo() != [("token", GEMINI_KEY)] + GEMINI_EMAIL_PAIRS \
                or [a[:2] for a in reads] != [(good, "GEMINI_API_KEY")]:                  # round 10 ruling 4
            out.append(f"B14.secrets: the scan's secrets read {[a[:2] for a in reads]}")
    return out


class B14Gemini(Drafted):
    def test_a_gemini_row_logs_in_by_its_r4g_key_file(self):
        self.assertEqual(b14_login_problems(wb()), [])

    def test_prepare_admits_a_gemini_row_by_name(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(b14_prepare_problems(wb(), Path(t)), [])

    def test_the_driver_and_walkrepo_get_the_key_secrets(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(b14_secrets_problems(wb(), Path(t)), [])


# ------------------------------------------------------------------------------------------------- B15
# The real-box bring-up (glitch-6b, 15 Oct 2026): runtime, hosts, lock_path, config_parent and the proxy from the box
# functions the stub take drives and the box lane's measured records; agent_version from the pin (prereg's version_pins
# and routing's pin_profiles). sidecar_for stays Missing: no registered per-task watch list is on the tree.
@problems_by_assertion("B15.production")
def b7_bringup_problems(mod, got) -> list:
    """What production_builders gives for the bring-up, both ways: present where the tree carries its source (B7's
    LOCKS_ON_TREE and VERSIONS_ON_TREE, read from the box's loader and the two pin files), Missing by name where not."""
    from box.egress import proxy_conf
    out = []
    if type(got["runtime"]) is not rt.DockerRuntime:
        out.append(f"B15.production: the runtime is {got['runtime']!r}, not a run_take.DockerRuntime")
    if got["hosts"] != dict(proxy_conf.HOSTS) or got["hosts"] is proxy_conf.HOSTS:
        out.append(f"B15.production: hosts is {got['hosts']!r}, not a copy of proxy_conf.HOSTS")
    for name, want in (("lock_path", LOCKS_ON_TREE), ("agent_version", VERSIONS_ON_TREE)):
        v = got[name]
        if not want:
            if not isinstance(v, mod.Missing):
                out.append(f"B15.production: {name} is {v!r} on a tree without its source")
            continue
        if not isinstance(v, mod.PerHarness):
            out.append(f"B15.production: {name} is {v!r}, not a PerHarness")
            continue
        given = {h: x for h, x in v.values.items() if not isinstance(x, mod.Missing)}
        if given != want or set(v.values) != {rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI}:
            out.append(f"B15.production: {name} gives {given}, not {want}")
    for name, words in (("config_parent", "GAP4_CONFIG_PARENT"), ("proxy", "config parent")):
        if not isinstance(got[name], mod.Missing) or words not in got[name].why:
            out.append(f"B15.production: {name} is {got[name]!r}, not Missing naming {words!r}")
    if SIDECAR_IMAGE_ON_TREE:
        if not callable(got["sidecar_for"]) or isinstance(got["sidecar_for"], mod.Missing):
            out.append(f"B15.production: sidecar_for is {got['sidecar_for']!r} where the sidecar lock is ready")
    elif not isinstance(got["sidecar_for"], mod.Missing) or "sidecar" not in got["sidecar_for"].why:
        out.append(f"B15.production: sidecar_for is {got['sidecar_for']!r} on a tree without the sidecar contract")
    return out


def owned_folder() -> Path:
    path = Path(tempfile.mkdtemp(prefix="cfgparent-")).resolve()    # outside every repository (the system temp)
    return path


def raising_is_a_failure(cls):
    """Every test_ method of `cls` fails by assertion when its body raises anything else (the generated sweep counts a
    failure as a kill and an error as nothing)."""
    def wrap(fn):
        def test(self):
            try:
                return fn(self)
            except AssertionError:
                raise
            except Exception as e:  # noqa: BLE001
                self.fail(f"{fn.__name__}: raised {type(e).__name__}: {str(e)[:300]}")
        test.__name__, test.__doc__ = fn.__name__, fn.__doc__
        return test
    for name in [n for n in vars(cls) if n.startswith("test_")]:
        setattr(cls, name, wrap(vars(cls)[name]))
    return cls


@raising_is_a_failure
class B15Bringup(Drafted):
    def test_per_harness_resolves_or_refuses_by_name(self):
        mod = wb()
        v = mod.PerHarness("the synthetic value", {rt.CLAUDE_CODE: "a", rt.CODEX: mod.Missing("synthetic: not yet"),
                                                   rt.GEMINI: None})
        self.assertEqual(v.for_harness(rt.CLAUDE_CODE), "a", "B15.per_harness")
        self.refuses("B15.per_harness", "synthetic: not yet", v.for_harness, rt.CODEX)
        self.refuses("B15.per_harness", "is missing: None", v.for_harness, rt.GEMINI)
        self.refuses("B15.per_harness", "no value for harness 'other'", v.for_harness, "other")
        for what, values in (("", {"x": 1}), ("w", {}), (None, {"x": 1}), ("w", None)):
            with self.assertRaises(TypeError, msg="B15.per_harness: an empty or unnamed PerHarness"):
                mod.PerHarness(what, values)
        self.assertIn("the synthetic value", repr(v), "B15.per_harness")
        self.assertEqual(mod.for_row(v, rt.CLAUDE_CODE), "a", "B15.for_row")
        self.assertEqual(mod.for_row("plain", rt.CODEX), "plain", "B15.for_row")
        road = mod.ProxyRoad("/synthetic", "sha256:" + "1" * 64)
        with mock.patch.object(mod.ProxyRoad, "for_harness", lambda self, h: ("launch", h)):
            self.assertEqual(mod.for_row(road, rt.GEMINI), ("launch", rt.GEMINI), "B15.for_row")

    def test_the_config_parent_is_the_operator_s_owned_folder(self):
        mod = wb()
        got = mod.config_parent_from_env({})
        self.assertIsInstance(got, mod.Missing, "B15.config_parent")
        self.assertIn("GAP4_CONFIG_PARENT", got.why, "B15.config_parent")
        self.assertIsInstance(mod.config_parent_from_env({"GAP4_CONFIG_PARENT": ""}), mod.Missing,
                              "B15.config_parent")
        good = owned_folder()
        self.assertEqual(mod.config_parent_from_env({"GAP4_CONFIG_PARENT": str(good)}), str(good),
                         "B15.config_parent")
        with mock.patch.dict(os.environ, {"GAP4_CONFIG_PARENT": str(good)}):
            self.assertEqual(mod.config_parent_from_env(), str(good), "B15.config_parent: the process environment")
        loose = owned_folder()
        for mode in (0o777, 0o720, 0o702):
            os.chmod(loose, mode)
            with self.subTest(mode=oct(mode)):
                self.refuses("B15.config_parent", "writable by its group or by others", mod.config_parent_from_env,
                             {"GAP4_CONFIG_PARENT": str(loose)})
        os.chmod(loose, 0o755)
        self.assertEqual(mod.config_parent_from_env({"GAP4_CONFIG_PARENT": str(loose)}), str(loose),
                         "B15.config_parent: a 0755 parent")
        afile = good / "a-file"
        afile.write_text("x")
        link = good / "a-link"
        os.symlink(str(good), link)
        for label, value, words in (("relative", "relative/folder", "normalised absolute"),
                                    ("not normalised", str(good) + "/./", "normalised absolute"),
                                    ("a file", str(afile), "not a folder"), ("a link", str(link), "not a folder"),
                                    ("absent", str(good / "absent"), "not a folder"),
                                    ("inside a repository", str(HERE), "inside a repository")):
            with self.subTest(label=label):
                self.refuses("B15.config_parent", words, mod.config_parent_from_env, {"GAP4_CONFIG_PARENT": value})
        real_stat = os.stat

        def stat_of_another(p, *a, **k):
            r = real_stat(p, *a, **k)
            if p != str(good):
                return r
            return os.stat_result((r.st_mode, r.st_ino, r.st_dev, r.st_nlink, r.st_uid + 1, r.st_gid, r.st_size,
                                   int(r.st_atime), int(r.st_mtime), int(r.st_ctime)))
        with mock.patch.object(os, "stat", stat_of_another):
            self.refuses("B15.config_parent", "not owned by the caller", mod.config_parent_from_env,
                         {"GAP4_CONFIG_PARENT": str(good)})

    def test_take_locks_through_preflight_s_loader(self):
        mod = wb()
        from box import preflight
        dirs = {"take-a": "", "take-o": "codex", "take-g": "gemini"}
        images = {rt.CLAUDE_CODE: "take-a", rt.CODEX: "take-o", rt.GEMINI: "take-g"}
        seen = []

        def loader(path, *, harness):
            seen.append((path, harness))
            if harness == rt.GEMINI:
                raise rt.NotReady("synthetic: the gemini lock is PENDING")
            return {}
        with mock.patch.object(preflight, "TAKE_LOCK_DIRS", dirs, create=True), \
                mock.patch.object(preflight, "TAKE_IMAGE", images, create=True), \
                mock.patch.object(preflight, "load_take_lock", loader):
            got = mod.take_lock_paths("/synthetic/box")
        self.assertEqual(seen, [("/synthetic/box/image.lock", rt.CLAUDE_CODE),
                                ("/synthetic/box/codex/image.lock", rt.CODEX),
                                ("/synthetic/box/gemini/image.lock", rt.GEMINI)], "B15.locks: not the loader's paths")
        self.assertEqual(got.values[rt.CLAUDE_CODE], "/synthetic/box/image.lock", "B15.locks")
        self.assertEqual(got.values[rt.CODEX], "/synthetic/box/codex/image.lock", "B15.locks")
        self.assertIsInstance(got.values[rt.GEMINI], mod.Missing, "B15.locks: a refused lock was given")
        self.assertIn("synthetic: the gemini lock is PENDING", got.values[rt.GEMINI].why, "B15.locks")
        self.assertIn("gemini/image.lock", got.values[rt.GEMINI].why, "B15.locks")
        with mock.patch.object(preflight, "TAKE_LOCK_DIRS", None, create=True):
            absent = mod.take_lock_paths("/synthetic/box")
        self.assertTrue(all(isinstance(v, mod.Missing) and "not on this tree" in v.why for v in absent.values.values())
                        and len(absent.values) == 3, f"B15.locks: no TAKE_LOCK_DIRS gives {absent!r}")
        real = mod.take_lock_paths()                  # the tree's own box folder, its own loader
        self.assertEqual({h: v for h, v in real.values.items() if not isinstance(v, mod.Missing)}, LOCKS_ON_TREE,
                         "B15.locks: the tree's ready locks")

    def test_the_proxy_road_writes_the_walk_s_checked_configuration(self):
        mod = wb()
        from box.egress import proxy_conf
        parent = owned_folder()
        image = "sha256:" + "7" * 64
        road = mod.ProxyRoad(str(parent), image)
        a = road.for_harness(rt.CLAUDE_CODE)
        b = road.for_harness(rt.GEMINI)
        self.assertIsInstance(a, rt.ProxyLaunch, "B15.proxy")
        self.assertEqual((a.image, a.conf_target, a.command, a.user, a.alias),
                         (image, proxy_conf.CONF_PATH, tuple(proxy_conf.COMMAND), proxy_conf.USER, rt.PROXY_ALIAS),
                         "B15.proxy: not the stub take's ProxyLaunch")
        for launch, harness in ((a, rt.CLAUDE_CODE), (b, rt.GEMINI)):
            path = Path(launch.conf_source)     # review MINOR 2: proxy.conf in a fresh 0700 folder, as the stub take's
            self.assertEqual(path.parent.parent, parent, "B15.proxy: the configuration's folder is not the parent's")
            self.assertEqual(path.name, "proxy.conf", "B15.proxy: the file's name")
            self.assertTrue(path.parent.name.startswith(f"proxy-{harness}-"), "B15.proxy: the folder's name")
            self.assertEqual(stat.S_IMODE(os.lstat(path.parent).st_mode), 0o700, "B15.proxy: the folder's mode")
            self.assertEqual(path.read_text(), proxy_conf.render(harness), "B15.proxy: not the harness's rendering")
            self.assertEqual(stat.S_IMODE(os.lstat(path).st_mode), 0o644, "B15.proxy: mode")
            self.assertEqual(os.listdir(path.parent), ["proxy.conf"], "B15.proxy: other files in its folder")
        self.assertNotEqual(Path(a.conf_source).parent, Path(b.conf_source).parent, "B15.proxy: one folder twice")
        self.assertEqual(sorted(p.name for p in parent.iterdir()),
                         sorted([Path(a.conf_source).parent.name, Path(b.conf_source).parent.name]),
                         "B15.proxy: other files")
        if not rt._is_pending(proxy_conf.USER):
            self.must("B15.proxy", rt._check_proxy, a)      # run_take's own check admits it where USER is measured
        self.assertEqual(road.text_for(rt.CODEX), proxy_conf.render(rt.CODEX), "B15.proxy: text_for")
        with mock.patch.object(proxy_conf, "check", lambda text, harness: ["synthetic: two hosts"]):
            self.refuses("B15.proxy", "synthetic: two hosts", road.for_harness, rt.CLAUDE_CODE)
            self.refuses("B15.proxy", "synthetic: two hosts", road.text_for, rt.CLAUDE_CODE)
        self.assertEqual(len(list(parent.iterdir())), 2, "B15.proxy: a refused configuration was written")
        road.discard(a)                                  # review NIT 2: a refused walk's folder goes
        self.assertEqual([p.name for p in parent.iterdir()], [Path(b.conf_source).parent.name], "B15.proxy: discard")
        stranger = owned_folder()
        (stranger / "proxy.conf").write_text("x")
        road.discard(types.SimpleNamespace(conf_source=str(stranger / "proxy.conf")))   # never outside its parent
        self.assertTrue((stranger / "proxy.conf").exists(), "B15.proxy: discard removed a folder not its own")
        other = parent / "not-a-proxy-folder"
        other.mkdir()
        (other / "proxy.conf").write_text("x")
        road.discard(types.SimpleNamespace(conf_source=str(other / "proxy.conf")))      # nor one not named proxy-*
        self.assertTrue((other / "proxy.conf").exists(), "B15.proxy: discard removed another folder of the parent")

    def test_the_proxy_road_needs_its_folder_its_user_and_its_lock(self):
        mod = wb()
        from box import preflight
        from box.egress import proxy_conf
        locks = mod.PerHarness("the take lock", {rt.CLAUDE_CODE: "/synthetic/box/image.lock",
                                                 rt.CODEX: mod.Missing("x"), rt.GEMINI: mod.Missing("y")})
        egress = "sha256:" + "6" * 64
        calls = []

        def loader(path, *, harness):
            calls.append((path, harness))
            return {"image_id": egress}
        got = mod.proxy_road(mod.Missing("synthetic: no folder named"), locks)
        self.assertIsInstance(got, mod.Missing, "B15.proxy_road")
        self.assertIn("synthetic: no folder named", got.why, "B15.proxy_road")
        with mock.patch.object(proxy_conf, "USER", "13:13"), \
                mock.patch.object(preflight, "load_egress_lock", loader, create=True):
            got = mod.proxy_road("/synthetic/parent", locks)
            self.assertIsInstance(got, mod.ProxyRoad, "B15.proxy_road")
            self.assertEqual((got.config_parent, got.image), ("/synthetic/parent", egress), "B15.proxy_road")
            self.assertEqual(calls, [("/synthetic/box/image.lock", rt.CLAUDE_CODE)], "B15.proxy_road: the lock")
            none = mod.PerHarness("the take lock", {rt.CLAUDE_CODE: mod.Missing("synthetic: claude lock PENDING")})
            got = mod.proxy_road("/synthetic/parent", none)
            self.assertIsInstance(got, mod.Missing, "B15.proxy_road")
            self.assertIn("synthetic: claude lock PENDING", got.why, "B15.proxy_road")
        with mock.patch.object(proxy_conf, "USER", "PENDING"), \
                mock.patch.object(preflight, "load_egress_lock", loader, create=True):
            got = mod.proxy_road("/synthetic/parent", locks)
            self.assertIsInstance(got, mod.Missing, "B15.proxy_road: a PENDING squid user")
            self.assertIn("proxy_conf.USER", got.why, "B15.proxy_road")

        def refusing(path, *, harness):
            raise rt.NotReady("synthetic: the egress lock is PENDING")
        with mock.patch.object(proxy_conf, "USER", "13:13"), \
                mock.patch.object(preflight, "load_egress_lock", refusing, create=True):
            got = mod.proxy_road("/synthetic/parent", locks)
            self.assertIsInstance(got, mod.Missing, "B15.proxy_road")
            self.assertIn("synthetic: the egress lock is PENDING", got.why, "B15.proxy_road")
        with mock.patch.object(preflight, "load_egress_lock", None, create=True):
            got = mod.proxy_road("/synthetic/parent", locks)
            self.assertIsInstance(got, mod.Missing, "B15.proxy_road")
            self.assertIn("not on this tree", got.why, "B15.proxy_road")

    def test_production_builds_the_proxy_once_the_folder_is_named(self):
        mod = wb()
        parent = owned_folder()
        with mock.patch.dict(os.environ, {"GAP4_CONFIG_PARENT": str(parent)}):
            got = self.must("B15.production", mod.production_builders)
        self.assertEqual(got["config_parent"], str(parent), "B15.production: the operator's folder")
        from box import preflight
        from box.egress import proxy_conf
        if LOCKS_ON_TREE.get(rt.CLAUDE_CODE) and callable(getattr(preflight, "load_egress_lock", None)) \
                and not rt._is_pending(proxy_conf.USER):
            self.assertIsInstance(got["proxy"], mod.ProxyRoad, "B15.production: the proxy road")
            want = preflight.load_egress_lock(LOCKS_ON_TREE[rt.CLAUDE_CODE], harness=rt.CLAUDE_CODE)["image_id"]
            self.assertEqual((got["proxy"].config_parent, got["proxy"].image), (str(parent), want), "B15.production")
        else:
            self.assertIsInstance(got["proxy"], mod.Missing, "B15.production: a proxy without its egress lock")

    def test_agent_versions_come_from_both_pins(self):
        mod = wb()
        import prereg
        import routing
        from box import preflight
        real = mod.agent_versions()
        self.assertEqual({h: v for h, v in real.values.items() if not isinstance(v, mod.Missing)}, VERSIONS_ON_TREE,
                         "B15.version: the tree's pins")
        lock_seen = []

        def lock_at(version):
            def load(path, *, harness):
                lock_seen.append((path, harness))
                return {"harness.version": version}
            return mock.patch.object(preflight, "load_take_lock", load)
        locks = mod.PerHarness("the take lock", {rt.CLAUDE_CODE: "/synthetic/box/image.lock",
                                                 rt.CODEX: mod.Missing("synthetic: no codex lock"),
                                                 rt.GEMINI: mod.Missing("synthetic: no gemini lock")})

        def pins(draft, table):
            return (mock.patch.object(prereg, "load", lambda: {"version_pins": draft}),
                    mock.patch.object(routing, "load_table", lambda: {"pin_profiles": table}))

        def pin(v, image=None, agent=None):
            return {"version": v, "image_version": v if image is None else image,
                    "agent_version": v if agent is None else agent}
        same_draft = {"m1": pin("1.2.3"), "m2": pin("1.2.3")}
        same = {"m1": {"version": "1.2.3"}, "m2": {"version": "1.2.3"}}
        cases = (("one version in both", {rt.CLAUDE_CODE: same_draft}, {rt.CLAUDE_CODE: same}, "1.2.3"),
                 ("the draft's image_version differs",
                  {rt.CLAUDE_CODE: dict(same_draft, m2=pin("1.2.3", image="1.2.4"))}, {rt.CLAUDE_CODE: same},
                  "image_version"),
                 ("the draft's agent_version is None",
                  {rt.CLAUDE_CODE: dict(same_draft, m1=dict(pin("1.2.3"), agent_version=None))},
                  {rt.CLAUDE_CODE: same}, "agent_version"),
                 ("routing differs", {rt.CLAUDE_CODE: same},
                  {rt.CLAUDE_CODE: {"m1": {"version": "1.2.3"}, "m2": {"version": "1.2.4"}}}, "differ"),
                 ("a model only in the draft", {rt.CLAUDE_CODE: same},
                  {rt.CLAUDE_CODE: {"m1": {"version": "1.2.3"}}}, "differ"),
                 ("two versions in both", {rt.CLAUDE_CODE: {"m1": {"version": "1"}, "m2": {"version": "2"}}},
                  {rt.CLAUDE_CODE: {"m1": {"version": "1"}, "m2": {"version": "2"}}}, "not one measured version"),
                 ("PENDING in both", {rt.CLAUDE_CODE: {"m1": {"version": "PENDING"}}},
                  {rt.CLAUDE_CODE: {"m1": {"version": "PENDING"}}}, "not one measured version"),
                 ("None in both", {rt.CLAUDE_CODE: {"m1": {"version": None}}},
                  {rt.CLAUDE_CODE: {"m1": {"version": None}}}, "not one measured version"),
                 ("empty in both", {rt.CLAUDE_CODE: {"m1": {"version": ""}}},
                  {rt.CLAUDE_CODE: {"m1": {"version": ""}}}, "not one measured version"),
                 ("a version that is not a string", {rt.CLAUDE_CODE: {"m1": {"version": 5}}},
                  {rt.CLAUDE_CODE: {"m1": {"version": 5}}}, "not one measured version"),
                 ("a model pinned None in both", {rt.CLAUDE_CODE: {"m1": None}}, {rt.CLAUDE_CODE: {"m1": None}},
                  "not one measured version"),
                 ("a model pinned None in the draft", {rt.CLAUDE_CODE: {"m1": None}}, {rt.CLAUDE_CODE: same},
                  "differ"),
                 ("a model pinned None in routing", {rt.CLAUDE_CODE: same}, {rt.CLAUDE_CODE: {"m1": None}},
                  "differ"),
                 ("absent from routing", {rt.CLAUDE_CODE: same}, {}, "both must pin it"),
                 ("absent from the draft", {}, {rt.CLAUDE_CODE: same}, "both must pin it"))
        for label, draft, table, want in cases:
            a, b = pins(draft, table)
            with self.subTest(label=label), a, b, lock_at("1.2.3"):
                got = self.must("B15.version", mod.agent_versions, locks).values[rt.CLAUDE_CODE]
                if want == "1.2.3":
                    self.assertEqual(got, "1.2.3", "B15.version")
                else:
                    self.assertIsInstance(got, mod.Missing, f"B15.version: {label} gave {got!r}")
                    self.assertIn(want, got.why, f"B15.version: {label}")
        self.assertIn(("/synthetic/box/image.lock", rt.CLAUDE_CODE), lock_seen, "B15.version: the lock was not read")
        # review MINOR 1: a draft and routing pin of 2.1.297 against a take lock at 2.1.296 is Missing
        a, b = pins({rt.CLAUDE_CODE: {"m1": pin("2.1.297")}}, {rt.CLAUDE_CODE: {"m1": {"version": "2.1.297"}}})
        with a, b, lock_at("2.1.296"):
            got = self.must("B15.version", mod.agent_versions, locks)
        self.assertIsInstance(got.values[rt.CLAUDE_CODE], mod.Missing, "B15.version: a pin off the take lock")
        self.assertIn("'2.1.296'", got.values[rt.CLAUDE_CODE].why, "B15.version: the lock's version is not named")
        for harness in (rt.CODEX, rt.GEMINI):          # pinned alike, but their take locks are missing
            a, b = pins({harness: {"m1": pin("1.2.3")}}, {harness: {"m1": {"version": "1.2.3"}}})
            with a, b, lock_at("1.2.3"):
                got = self.must("B15.version", mod.agent_versions, locks).values[harness]
            self.assertIsInstance(got, mod.Missing, f"B15.version: {harness} with no take lock")
            self.assertIn("synthetic: no", got.why, f"B15.version: {harness}'s lock reason")

        def refusing(path, *, harness):
            raise rt.NotReady("synthetic: the lock is PENDING")
        a, b = pins({rt.CLAUDE_CODE: same_draft}, {rt.CLAUDE_CODE: same})
        with a, b, mock.patch.object(preflight, "load_take_lock", refusing):
            got = self.must("B15.version", mod.agent_versions, locks).values[rt.CLAUDE_CODE]
        self.assertIsInstance(got, mod.Missing, "B15.version: a refused lock")
        self.assertIn("synthetic: the lock is PENDING", got.why, "B15.version: the loader's reason")
        a, b = pins({}, {})
        with a, b:
            got = mod.agent_versions(locks)
        self.assertEqual(set(got.values), {rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI}, "B15.version: the harnesses")
        # neither file carrying its block at all (no version_pins key, no pin_profiles key): Missing, never a crash
        with mock.patch.object(prereg, "load", lambda: {}), mock.patch.object(routing, "load_table", lambda: {}):
            got = mod.agent_versions(locks)
        self.assertTrue(all(isinstance(v, mod.Missing) and "both must pin it" in v.why for v in got.values.values()),
                        f"B15.version: no blocks gave {got!r}")

    def test_walk_row_takes_the_row_s_own_harness_version(self):
        mod = wb()
        rows = [{"task": "t", "half": "trap", "wording": "w1", "arm": arm, "model": "m",
                 "agent": {"harness": h, "version": None}} for arm, h in (("A", rt.CLAUDE_CODE), ("G", rt.GEMINI))]
        cell = {"task": "t", "half": "trap", "wording": "w1", "model": "m"}
        v = mod.PerHarness("the agent version", {rt.CLAUDE_CODE: "2.0.0", rt.GEMINI: mod.Missing("synthetic: PENDING")})
        got = self.must("B15.walk_row", mod.walk_row, "w-1", dict(cell, arm="A"), v, rows)
        self.assertEqual(got["agent"], {"harness": rt.CLAUDE_CODE, "version": "2.0.0"}, "B15.walk_row")
        self.refuses("B15.walk_row", "synthetic: PENDING", mod.walk_row, "w-1", dict(cell, arm="G"), v, rows)
        self.refuses("B15.walk_row", "not a row of the design", mod.walk_row, "w-1", dict(cell, arm="Z"), v, rows)

    def test_budgets_come_from_the_checker_constants_both_ways(self):
        """B3: PENDING (or not there yet) gives Missing; filled gives the tuple, equal, in drive's order."""
        mod = wb()
        import check_take
        P = check_take.PENDING
        filled = {"turn_timeout_s": 900, "finalize_wait_s": 180, "poll_s": 3}
        self.assertEqual(mod.checker_budgets({"budgets": filled}), (900, 180, 3), "B3.budgets: filled")
        self.assertEqual(mod.checker_budgets({"budgets": dict(filled, poll_s=0.5)}), (900, 180, 0.5), "B3.budgets")
        for label, c, words in (("the block PENDING", {"budgets": P}, "['budgets']"),
                                ("no block", {}, "['budgets']"),
                                ("turn PENDING", {"budgets": dict(filled, turn_timeout_s=P)}, "budgets.turn_timeout_s"),
                                ("cap PENDING", {"budgets": dict(filled, finalize_wait_s=P)}, "budgets.finalize_wait_s"),
                                ("poll PENDING", {"budgets": dict(filled, poll_s=P)}, "budgets.poll_s"),
                                ("today's tree", {"budgets": {"turn_timeout_s": P}}, "budgets.poll_s"),
                                ("the cap absent", {"budgets": {"turn_timeout_s": 900, "poll_s": 3}},
                                 "budgets.finalize_wait_s")):
            with self.subTest(label=label):
                got = self.must("B3.budgets", mod.checker_budgets, c)
                self.assertIsInstance(got, mod.Missing, f"B3.budgets: {label} gave {got!r}")
                self.assertIn(words, got.why, f"B3.budgets: {label}")
                self.assertIn("CHECKER_CONSTANTS", got.why, f"B3.budgets: {label}")
        for label, b in (("zero", dict(filled, poll_s=0)), ("negative", dict(filled, turn_timeout_s=-1)),
                         ("a bool", dict(filled, poll_s=True)), ("a string", dict(filled, finalize_wait_s="180")),
                         ("not a mapping", [900, 180, 3])):
            with self.subTest(label=label):
                self.refuses("B3.budgets", "budgets", mod.checker_budgets, {"budgets": b})
        with mock.patch.object(check_take, "CHECKER_CONSTANTS", dict(check_take.CHECKER_CONSTANTS, budgets=filled)):
            self.assertEqual(mod.checker_budgets(), (900, 180, 3), "B3.budgets: the module's own constants")
            self.assertEqual(self.must("B3.budgets", mod.production_builders)["budgets"], (900, 180, 3),
                             "B3.budgets: production")
        got = mod.checker_budgets()
        self.assertEqual(not isinstance(got, mod.Missing), BUDGETS_ON_TREE, f"B3.budgets: this tree gives {got!r}")

    def test_run_tree_exclude_comes_from_run_location_both_ways(self):
        mod = wb()
        import check_take
        P = check_take.PENDING
        paths = ["evals", "docs/private", ".github"]           # the bootstrap's shape (af1e7fc6): [{"path": p}, ...]
        rl = {"excluded_from_the_run_tree": [{"path": p} for p in paths], "checkout_identity": "gars"}
        got = mod.checker_run_tree_exclude({"run_location": rl})
        self.assertEqual(got, paths, "B3.exclude: filled")
        for label, c in (("run_location PENDING", {"run_location": P}), ("no run_location", {}),
                         ("the list PENDING", {"run_location": dict(rl, excluded_from_the_run_tree=P)}),
                         ("the list absent", {"run_location": {"checkout_identity": "gars"}}),
                         ("a PENDING inside", {"run_location": dict(rl, excluded_from_the_run_tree={"a": P})})):
            with self.subTest(label=label):
                got = self.must("B3.exclude", mod.checker_run_tree_exclude, c)
                self.assertIsInstance(got, mod.Missing, f"B3.exclude: {label} gave {got!r}")
                self.assertIn("run_location.excluded_from_the_run_tree", got.why, f"B3.exclude: {label}")
        for label, v in (("empty", []), ("absolute", [{"path": "/etc"}]), ("dot-dot", [{"path": "a/../b"}]),
                         ("repeated", [{"path": "a"}, {"path": "a"}]), ("not a string", [{"path": 3}]),
                         ("an empty path", [{"path": ""}]), ("no path", [{"name": "evals"}]),
                         ("a bare string entry", ["evals"]), ("one bare entry among good", [{"path": "a"}, "b"]),
                         ("a string", "evals"), ("a mapping", {"path": "evals"})):
            with self.subTest(label=label):
                self.refuses("B3.exclude", "excluded_from_the_run_tree", mod.checker_run_tree_exclude,
                             {"run_location": dict(rl, excluded_from_the_run_tree=v)})
        with mock.patch.object(check_take, "CHECKER_CONSTANTS", dict(check_take.CHECKER_CONSTANTS, run_location=rl)):
            self.assertEqual(mod.checker_run_tree_exclude(), paths, "B3.exclude: the module's own constants")
            self.assertEqual(self.must("B3.exclude", mod.production_builders)["run_tree_exclude"], paths,
                             "B3.exclude: production")
        got = mod.checker_run_tree_exclude()
        self.assertEqual(not isinstance(got, mod.Missing), EXCLUDE_ON_TREE, f"B3.exclude: this tree gives {got!r}")

    def test_production_wraps_an_all_missing_per_harness_value(self):
        """review MINOR 3: a lock or a version no harness has is one top-level Missing (cli refuses by name)."""
        mod = wb()
        none = {h: mod.Missing(f"synthetic: no {h}") for h in (rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI)}
        with mock.patch.object(mod, "take_lock_paths", lambda *a: mod.PerHarness("the take lock", none)), \
                mock.patch.object(mod, "agent_versions", lambda *a: mod.PerHarness("the agent version", none)):
            got = self.must("B15.production", mod.production_builders)
        for name in ("lock_path", "agent_version"):
            self.assertIsInstance(got[name], mod.Missing, f"B15.production: an all-Missing {name} is {got[name]!r}")
            self.assertIn("synthetic: no gemini", got[name].why, f"B15.production: {name} does not say why")
        one = dict(none, **{rt.CLAUDE_CODE: "/synthetic/box/image.lock"})
        with mock.patch.object(mod, "take_lock_paths", lambda *a: mod.PerHarness("the take lock", one)), \
                mock.patch.object(mod, "agent_versions", lambda *a: mod.PerHarness("the agent version", one)):
            got = self.must("B15.production", mod.production_builders)
        for name in ("lock_path", "agent_version"):
            self.assertIsInstance(got[name], mod.PerHarness, f"B15.production: one harness's {name} is {got[name]!r}")

    def test_prepare_refuses_a_missing_per_harness_value_before_the_checkout(self):
        """review NIT 1: the row's lock_path and proxy are checked in prepare, before build_run_tree."""
        mod = wb()
        built = []
        args = types.SimpleNamespace(walk="w-0001", **{k: tww.the_row()[k] for k in ("task", "half", "wording",
                                                                                         "arm", "model")})
        good = str(login_file(f"{LOGIN}={tbi.TOKEN}\n"))
        base = {"agent_version": "2.1.296", "login_path": good, "run_tree_origin": ("/synthetic/repo", "0" * 40),
                "run_tree_exclude": ["evals"]}
        harness = mod.walk_row("w-0001", vars(args), "2.1.296", tww.REAL_LOAD()["rows"])["agent"]["harness"]
        lockless = mod.PerHarness("the take lock", {harness: mod.Missing("synthetic: this row's lock is PENDING")})
        road = mod.ProxyRoad(str(owned_folder()), "sha256:" + "1" * 64)
        with mock.patch.object(mod, "build_run_tree", lambda *a, **k: built.append(a) or "/synthetic/tree"):
            self.refuses("B15.prepare", "synthetic: this row's lock is PENDING", mod.prepare,
                         dict(base, lock_path=lockless), args)
            with mock.patch.object(mod.ProxyRoad, "text_for", side_effect=mod.BuilderRefused("synthetic: no render")):
                self.refuses("B15.prepare", "synthetic: no render", mod.prepare, dict(base, proxy=road), args)
            self.assertEqual(built, [], "B15.prepare: a checkout was built for a refused row")
            self.assertEqual(os.listdir(road.config_parent), [], "B15.prepare: prepare wrote a configuration")
            ok = mod.PerHarness("the take lock", {harness: "/synthetic/box/image.lock"})
            self.must("B15.prepare", mod.prepare, dict(base, lock_path=ok, proxy=road), args)
            self.assertEqual(len(built), 1, "B15.prepare: an admitted row built no checkout")
            self.assertEqual(os.listdir(road.config_parent), [], "B15.prepare: prepare wrote a configuration")

    def test_walk_driver_for_resolves_the_row_s_lock_and_proxy(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(b15_driver_problems(wb(), Path(t)), [])


@problems_by_assertion("B15.driver")
def b15_driver_problems(mod, tmp: Path) -> list:
    """walk_driver_for hands drive.walk_driver the row's own harness's lock path and its ProxyRoad's launch, and refuses
    a row whose harness has no lock before anything is built (no fixture, no proxy configuration written)."""
    out = []
    drive = MODS["drive"]
    got, built, made = {}, [], []
    proxy = "the-proxy-launch"

    class Road(mod.ProxyRoad):
        def for_harness(self, harness):
            made.append(harness)
            return proxy
    locks = mod.PerHarness("the take lock", {rt.CLAUDE_CODE: "/synthetic/box/image.lock",
                                             rt.GEMINI: mod.Missing("synthetic: the gemini lock is PENDING")})
    builders = {"rules_scanner": lambda paths: [], "runtime": "rt", "config_parent": str(tmp), "budgets": (600, 5, 1),
                "take_spec": lambda r, c, t: "spec", "sidecar_for": None, "proxy": Road(str(tmp), "sha256:" + "1" * 64),
                "lock_path": locks, "hosts": {"h": "x"}, "cgroup_dir_for": lambda t: "", "pin_for": None,
                "design_for": None, "uid_map": None, "clock": None, "sleep": None, "ownership": None,
                "settings_guard": None, "machine_gate": None}
    with mock.patch.object(drive, "walk_driver", lambda **kw: got.setdefault("driver", kw) and "driver"), \
            mock.patch.object(drive, "WalkRepo", lambda **kw: got.setdefault("repo", kw) and "repo"), \
            mock.patch.object(drive, "records_repo", lambda root: "/synthetic/repo"), \
            mock.patch.object(mod, "build_walk_fixture",
                              lambda r, t, p: built.append(r["walk"]) or ({"sha256": "0" * 64}, "/synthetic/src")), \
            mock.patch.object(mod, "walk_identity", lambda *a, **k: {"walk": "w-0001"}), \
            mock.patch.object(mod, "login_secrets", lambda login, harness: (lambda: [])):
        claude = {"walk": "w-0001", "arm": "A", "agent": {"harness": rt.CLAUDE_CODE, "version": "2.1.296"}}
        mod.walk_driver_for(builders, claude, "/synthetic/login", tmp / "tree")
        kw = got.get("driver", {})
        if (kw.get("lock_path"), kw.get("proxy"), kw.get("hosts")) != ("/synthetic/box/image.lock", proxy, {"h": "x"}):
            out.append(f"B15.driver: the driver got lock {kw.get('lock_path')!r}, proxy {kw.get('proxy')!r}")
        if made != [rt.CLAUDE_CODE] or built != ["w-0001"]:
            out.append(f"B15.driver: the proxy was made for {made}, the fixture built {built}")
        got.clear()
        gemini = {"walk": "w-0002", "arm": "G", "agent": {"harness": rt.GEMINI, "version": "0.64.0"}}
        try:
            mod.walk_driver_for(builders, gemini, "/synthetic/login", tmp / "tree")
            out.append("B15.driver: a row whose harness has no lock was driven")
        except mod.BuilderRefused as e:
            if "synthetic: the gemini lock is PENDING" not in str(e):
                out.append(f"B15.driver: refused for another reason: {e}")
        if built != ["w-0001"] or made != [rt.CLAUDE_CODE] or got:
            out.append(f"B15.driver: a refused row built {built} or made a proxy {made}")
    # review NIT 2: when drive.walk_driver refuses, the walk's proxy folder is removed with it
    parent = tmp / "cfg-parent"
    parent.mkdir(mode=0o700)
    real_road = mod.ProxyRoad(str(parent), "sha256:" + "1" * 64)

    def refusing(**kw):
        got["proxy"] = kw["proxy"]
        raise RuntimeError("synthetic: the driver refused")
    with mock.patch.object(drive, "walk_driver", refusing), \
            mock.patch.object(drive, "records_repo", lambda root: "/synthetic/repo"), \
            mock.patch.object(mod, "build_walk_fixture", lambda r, t, p: ({"sha256": "0" * 64}, "/synthetic/src")), \
            mock.patch.object(mod, "walk_identity", lambda *a, **k: {"walk": "w-0003"}), \
            mock.patch.object(mod, "login_secrets", lambda login, harness: (lambda: [])):
        claude = {"walk": "w-0003", "arm": "A", "agent": {"harness": rt.CLAUDE_CODE, "version": "2.1.296"}}
        try:
            mod.walk_driver_for(dict(builders, proxy=real_road), claude, "/synthetic/login", tmp / "tree")
            out.append("B15.driver: a refusing driver was not raised through")
        except RuntimeError as e:
            if "synthetic: the driver refused" not in str(e):
                out.append(f"B15.driver: another error: {e}")
    if "proxy" not in got or os.listdir(parent):
        out.append(f"B15.driver: the refused walk's proxy folder stayed: {os.listdir(parent)}")
    return out


# ------------------------------------------------------------------------------------------------- B16
# The sidecar's watch list and launch (glitch-6b's ruling, Addendum 2 of first-walk-bootstrap-ruling-2026-10-15.md):
# W1 watches sorted(variants.graded_paths(task, project)); only a task with no graded path (number-fidelity) watches its
# own source folder, a named departure; the production sidecar launch is the stub take's, cap_add its named departure.
WATCH_PROJECT = "run-0000abcd"
WATCH_TREE = "/synthetic/run-tree"
# The fields the graders read from the access log or the blobs (Addendum 2's binding list), per task.
GRADER_READ_FIELDS = {"scope-read": ("planted",), "plan-gate": ("plan_path", "approval_store"),
                      "approval-scope": ("pre_existing", "link_paths")}


def draft_tasks() -> list:
    return sorted({r["task"] for r in tww.REAL_LOAD()["rows"]})


@problems_by_assertion("B16.rule")
def watch_rule_problems(mod, watch_for) -> list:
    """(i): every task in the draft watches exactly sorted(graded_paths(task, project)), or, for a task with no graded
    path, exactly its rendered source folder; the tasks that fall back are exactly {number-fidelity}."""
    out, fallback = [], set()
    for task in draft_tasks():
        graded = sorted(variants.graded_paths(task, project=WATCH_PROJECT))
        got = watch_for({"task": task}, WATCH_PROJECT, WATCH_TREE)
        if graded:
            if got != graded:
                out.append(f"B16.rule: {task} watches {got}, not its graded paths {graded}")
            continue
        fallback.add(task)
        src = os.path.relpath(variants.render_source(variants.load_task(task)["source_template"], WATCH_TREE,
                                                     WATCH_PROJECT), WATCH_TREE)
        if got != [src]:
            out.append(f"B16.rule: {task} (no graded path) watches {got}, not its source folder {src}")
    if fallback != {"number-fidelity"}:
        out.append(f"B16.rule: the tasks that fall back to their source folder are {sorted(fallback)}")
    return out


@problems_by_assertion("B16.read")
def watch_read_problems(mod, watch_for) -> list:
    """(ii) and (iii): every path a grader reads from the access log or the blobs is watched, in every half, wording
    and pressure cell; approval-scope watches exactly pre_existing and link_paths, never more."""
    out = []
    for task, fields in GRADER_READ_FIELDS.items():
        watch = set(watch_for({"task": task}, WATCH_PROJECT, WATCH_TREE))
        doc, vd = variants.load_task(task), variants.load_variants(task)
        read = set()
        cells = variants.concrete_specs(doc, vd, WATCH_PROJECT)
        if not cells:
            out.append(f"B16.read: {task} has no concrete cell")
        for cell, spec in cells:
            for f in fields:
                paths = variants._flatten(spec.get(f))
                if not paths:
                    out.append(f"B16.read: {task} {cell} names no {f}")
                read |= paths
                if paths - watch:
                    out.append(f"B16.read: {task} {cell} {f} not watched: {sorted(paths - watch)[:3]}")
        if task == "approval-scope" and watch != read:
            out.append(f"B16.read: approval-scope watches {len(watch)} paths, not exactly pre_existing and link_paths "
                       f"({len(read)}): extra {sorted(watch - read)[:3]}")
    return out


@raising_is_a_failure
class B16Watch(Drafted):
    def test_the_rule_and_its_one_departure(self):
        self.assertEqual(watch_rule_problems(wb(), wb().watch_list), [])

    def test_every_read_path_is_watched_and_approval_scope_exactly(self):
        self.assertEqual(watch_read_problems(wb(), wb().watch_list), [])

    def test_the_checks_go_red_on_their_mutations(self):
        """(iv): dropping one planted path turns (ii) red; a fallback for a task with graded paths turns (i) red; one
        extra watched path for approval-scope turns (iii) red."""
        mod = wb()
        real = mod.watch_list

        def drop_planted(row, project, tree):
            got = real(row, project, tree)
            return got[1:] if row["task"] == "scope-read" else got

        def fallback_everywhere(row, project, tree):
            if row["task"] != "scope-read":
                return real(row, project, tree)
            return [os.path.relpath(variants.render_source(variants.load_task("scope-read")["source_template"],
                                                           tree, project), tree)]

        def over_watch(row, project, tree):
            got = real(row, project, tree)
            return got + [f"gars/projects/{project}/extra"] if row["task"] == "approval-scope" else got
        self.assertTrue(watch_read_problems(mod, drop_planted), "B16.mutation: a dropped planted path passed (ii)")
        self.assertTrue(watch_rule_problems(mod, fallback_everywhere), "B16.mutation: a needless fallback passed (i)")
        self.assertTrue(watch_read_problems(mod, over_watch), "B16.mutation: an over-watched approval-scope passed")

    def test_the_watch_list_refuses_by_name(self):
        mod = wb()
        row = {"task": "scope-read"}
        for label, graded, words in (("a repeated path", ["a/b", "a/b"], "repeats"),
                                     ("an absolute path", ["/etc/passwd"], "watch_path_ok"),
                                     ("a dot-dot path", ["a/../b"], "watch_path_ok")):
            with self.subTest(label=label), mock.patch.object(variants, "graded_paths", lambda t, **k: list(graded)):
                self.refuses("B16.refuse", words, mod.watch_list, row, WATCH_PROJECT, WATCH_TREE)
        nf = {"task": "number-fidelity"}
        real_load = variants.load_task
        with mock.patch.object(variants, "graded_paths", lambda t, **k: set()), \
                mock.patch.object(variants, "load_task", lambda t, **k: {k2: v for k2, v in real_load(t).items()
                                                                          if k2 != "source_template"}):
            self.refuses("B16.refuse", "watch list is empty", mod.watch_list, nf, WATCH_PROJECT, WATCH_TREE)
        got = self.must("B16.refuse", mod.watch_list, nf, WATCH_PROJECT, WATCH_TREE)
        self.assertEqual(got, [f"data/staging/{WATCH_PROJECT}/src"], "B16.fallback: not the rendered source folder")
        self.assertEqual(mod.WATCH_FALLBACK_TASKS, frozenset({"number-fidelity"}), "B16.fallback: the ruled set")
        # review MINOR 2: the code binds the fallback set; a task with graded paths emptied is refused, not fallen back
        for task in ("precondition-refusal", "scope-read"):
            with self.subTest(task=task), mock.patch.object(variants, "graded_paths", lambda t, **k: set()):
                self.refuses("B16.refuse", "not a ruled fallback task", mod.watch_list, {"task": task},
                             WATCH_PROJECT, WATCH_TREE)

    def test_the_production_sidecar_is_the_stub_take_s_launch(self):
        mod = wb()
        from box import sidecar
        road = mod.sidecar_road()
        if not SIDECAR_IMAGE_ON_TREE:
            self.assertIsInstance(road, mod.Missing, "B16.launch: a sidecar launch without its contract or lock")
            return
        from box import sidecar_contract
        tmp = owned_folder()
        tree, ev = str(tmp / "tree"), str(tmp / "ev")
        got = self.must("B16.launch", road, {"task": "plan-gate"}, ev, tree, WATCH_PROJECT)
        self.assertIsInstance(got, rt.SidecarLaunch, "B16.launch")
        want = sidecar.create_argv(image=SIDECAR_IMAGE_ON_TREE, run_tree=tree, evidence=ev,
                                   watch=mod.watch_list({"task": "plan-gate"}, WATCH_PROJECT, tree))
        self.assertEqual(list(got.create_argv), want, "B16.launch: not create_argv over the lock's image and the list")
        watched = [got.create_argv[i + 1] for i, a in enumerate(got.create_argv) if a == "--watch"]
        self.assertEqual(watched, sorted(variants.graded_paths("plan-gate", project=WATCH_PROJECT)), "B16.launch")
        expect = sidecar.expect_from_argv(want)
        expect["cap_add"] = list(sidecar_contract.BOOT_INSPECT_CAPABILITIES)
        self.assertEqual(got.expect, expect, "B16.launch: not expect_from_argv with the measured cap_add")
        self.assertEqual((got.start_argv_for, got.ctl_argv_for, got.rm_argv_for),
                         (sidecar.start_argv, sidecar.ctl_argv, sidecar.rm_argv), "B16.launch: not sidecar's argv")
        self.must("B16.launch", rt._check_sidecar, got)

    def test_the_sidecar_road_is_missing_without_its_lock(self):
        mod = wb()
        import importlib.util
        from box import preflight
        contract = importlib.util.find_spec("box.sidecar_contract") is not None   # both ways: absent, its own reason
        with mock.patch.object(preflight, "load_sidecar_lock", None, create=True):
            got = mod.sidecar_road()
        self.assertIsInstance(got, mod.Missing, "B16.missing: no loader")
        self.assertIn("load_sidecar_lock" if contract else "sidecar_contract", got.why, "B16.missing")

        def refusing(path, *, harness):
            raise rt.NotReady("synthetic: the sidecar lock is PENDING")
        with mock.patch.object(preflight, "load_sidecar_lock", refusing, create=True):
            got = mod.sidecar_road()
        self.assertIsInstance(got, mod.Missing, "B16.missing: a refused lock")
        self.assertIn("synthetic: the sidecar lock is PENDING" if contract else "sidecar_contract", got.why,
                      "B16.missing")
        with mock.patch.dict(sys.modules, {"box.sidecar_contract": None}):
            got = mod.sidecar_road()
        self.assertIsInstance(got, mod.Missing, "B16.missing: no contract")
        self.assertIn("sidecar_contract", got.why, "B16.missing")
        seen = []

        def loader(path, *, harness):
            seen.append((path, harness))
            return {"image_id": "sha256:" + "4" * 64}
        if contract:
            with mock.patch.object(preflight, "load_sidecar_lock", loader, create=True):
                self.assertTrue(callable(mod.sidecar_road("/synthetic/box")), "B16.missing: a ready lock")
            self.assertEqual(seen, [("/synthetic/box/image.lock", rt.CLAUDE_CODE)], "B16.missing: the lock read")

    def test_walk_driver_for_hands_the_walk_s_project_to_the_sidecar(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(b16_project_problems(wb(), Path(t)), [])


@problems_by_assertion("B16.project")
def b16_project_problems(mod, tmp: Path) -> list:
    out = []
    drive = MODS["drive"]
    got, calls = {}, []
    builders = {"rules_scanner": lambda paths: [], "runtime": "rt", "config_parent": str(tmp), "budgets": (600, 5, 1),
                "take_spec": lambda r, c, t: "spec", "sidecar_for": lambda *a: calls.append(a) or "launch",
                "proxy": None, "lock_path": None, "hosts": None, "cgroup_dir_for": lambda t: "", "pin_for": None,
                "design_for": None, "uid_map": None, "clock": None, "sleep": None, "ownership": None,
                "settings_guard": None, "machine_gate": None}
    row = {"walk": "w-0001", "arm": "A", "agent": {"harness": rt.CLAUDE_CODE, "version": "2.1.296"}}
    with mock.patch.object(drive, "walk_driver", lambda **kw: got.setdefault("driver", kw) and "driver"), \
            mock.patch.object(drive, "WalkRepo", lambda **kw: "repo"), \
            mock.patch.object(drive, "records_repo", lambda root: "/synthetic/repo"), \
            mock.patch.object(mod, "build_walk_fixture", lambda r, t, p: ({"sha256": "0" * 64}, "/synthetic/src")), \
            mock.patch.object(mod, "walk_identity", lambda *a, **k: {"walk": "w-0001"}), \
            mock.patch.object(mod, "login_secrets", lambda login, harness: (lambda: [])):
        mod.walk_driver_for(builders, row, "/synthetic/login", tmp / "tree")
        launched = got["driver"]["sidecar_for"](row, "/synthetic/ev")
    project = MODS["drive"].neutral_name(walk_sid("w-0001"))
    if launched != "launch" or calls != [(row, "/synthetic/ev", str(tmp / "tree"), project)]:
        out.append(f"B16.project: the sidecar got {calls}, not the walk's row, evidence, tree and project {project}")
    return out


# ------------------------------------------------------------------------------------------------- B17
# Round 11 (glitch-b5, Sat 17 Oct 2026): the round 10 battery's generated sweep of this module left the account record's
# reader (round 10 rulings 1, 2 and 4) without a binding here: its rules were bound only in test_vendor_roads, which the
# sweep does not run. B17 binds each rule in this module, every value TEST DATA under the reserved .invalid domain.
B17_OTHER = "claude-account@example.invalid"


@contextlib.contextmanager
def b17_folder(record=None, *, raw=None):
    """A private folder laid out as the box's: claude1/ and r4-g/ account folders, run_take.WALK_LOGIN_FILES patched to
    them, and the account record beside them holding `record` (default TEST_ACCOUNT_EMAILS) as JSON, or `raw` bytes,
    mode 600. Yields the record's path."""
    with tempfile.TemporaryDirectory() as t:
        top = Path(t).resolve() / "secrets"
        top.mkdir(mode=0o700)
        files = {}
        for account in ("claude1", "r4-g"):
            (top / account).mkdir(mode=0o700)
            files[account] = str(top / account / "login")
        f = top / "account-emails.json"
        if raw is not None:
            f.write_bytes(raw)
            os.chmod(f, 0o600)
        else:
            account_record_file(top, record)
        with mock.patch.object(rt, "WALK_LOGIN_FILES", files, create=True):
            yield f


@problems_by_assertion("B17.record")
def b17_path_problems(mod) -> list:
    """account_emails_path: the one folder holding WALK_LOGIN_FILES' account folders, or a refusal by name."""
    out = []

    def refused(label, words, files):
        with mock.patch.object(rt, "WALK_LOGIN_FILES", files, create=True):
            try:
                got = mod.account_emails_path()
            except mod.BuilderRefused as e:
                if words not in str(e) or "account-emails.json" not in str(e):
                    out.append(f"B17.record: {label} refused for another reason: {e}")
                return
            except Exception as e:  # noqa: BLE001
                out.append(f"B17.record: {label} raised {type(e).__name__}, not BuilderRefused: {e}")
                return
            out.append(f"B17.record: {label} was admitted ({got!r})")

    with b17_folder() as f:
        got = mod.account_emails_path()
        if got != str(f):
            out.append(f"B17.record: the record's path is {got!r}, not {str(f)!r}")
        top = str(f.parent)
    for label, files in (("no WALK_LOGIN_FILES", None), ("an empty WALK_LOGIN_FILES", {}),
                         ("a WALK_LOGIN_FILES that is a list", [top + "/claude1/login"])):
        refused(label, "records no WALK_LOGIN_FILES", files)
    one = "do not sit in one private folder"
    for label, files in (("account folders under two parents",
                          {"claude1": top + "/claude1/login", "r4-g": top + "/elsewhere/r4-g/login"}),
                         ("a relative login path", {"claude1": "claude1/login"}),
                         ("a login path that is not text", {"claude1": 7}),
                         ("one absolute and one relative login path",
                          {"claude1": top + "/claude1/login", "r4-g": "r4-g/login"})):
        refused(label, one, files)
    return out


@problems_by_assertion("B17.record")
def b17_record_problems(mod) -> list:
    """account_emails on TEST DATA records: the two addresses read for a vendor take, every rule refusing by name."""
    out, said = [], []
    want = {"codex": (TEST_ACCOUNT_EMAILS["operator"], TEST_ACCOUNT_EMAILS["codex"]),
            "gemini": (TEST_ACCOUNT_EMAILS["operator"], TEST_ACCOUNT_EMAILS["gemini"])}

    def refused(label, words, harness="codex", path=None):
        try:
            got = mod.account_emails(harness) if path is None else mod.account_emails(harness, path)
        except mod.BuilderRefused as e:
            said.append(str(e))
            for w in (words if isinstance(words, tuple) else (words,)) + ("account-emails.json",):
                if w not in str(e):
                    out.append(f"B17.record: {label} refused without naming {w!r}: {e}")
            return
        except Exception as e:  # noqa: BLE001
            out.append(f"B17.record: {label} raised {type(e).__name__}, not BuilderRefused: {e}")
            return
        out.append(f"B17.record: {label} was admitted ({got!r})")

    def admitted(label, harness, path=None):
        try:
            got = tuple(mod.account_emails(harness) if path is None else mod.account_emails(harness, path))
        except Exception as e:  # noqa: BLE001
            out.append(f"B17.record: {label} refused: {type(e).__name__}: {e}")
            return
        if got != want[harness]:
            out.append(f"B17.record: {label} read {got!r}, not the operator's and its account's addresses")

    with b17_folder() as f:
        for harness in ("codex", "gemini"):
            admitted(f"a complete record ({harness}, by its path)", harness)
            admitted(f"a complete record ({harness}, named)", harness, str(f))
        for harness in ("claude-code", "synthetic-harness"):
            refused(f"a {harness} take", ("sweeps no account address", repr(harness)), harness)
        refused("a relative path", "is named by an absolute path", path="account-emails.json")
        refused("a path that is not text", "is named by an absolute path", path=7)
        refused("no record", "does not exist", path=str(f.parent / "absent" / "account-emails.json"))
        link = f.parent / "account-emails-link.json"
        link.symlink_to(f)
        refused("a link to the record", "regular file, never a link", path=str(link))
        for mode in (0o644, 0o640, 0o700, 0o400):
            os.chmod(f, mode)
            refused(f"a record of mode {mode:o}", "mode must be 600")
        os.chmod(f, 0o600)
        real_uid = os.getuid()
        with mock.patch.object(os, "getuid", lambda: real_uid + 1):
            refused("a record another user owns", "owned by the reading user")
        real_open, real_close, real_lstat = os.open, os.close, os.lstat
        opened, closed = [], []

        def spy_open(p, *a, **k):
            fd = real_open(p, *a, **k)
            if os.fspath(p) == str(f):
                opened.append(fd)
            return fd

        def spy_close(fd):
            closed.append(fd)
            return real_close(fd)
        with mock.patch.object(os, "open", spy_open), mock.patch.object(os, "close", spy_close):
            admitted("a complete record (its descriptor watched)", "codex")
        if not opened or [fd for fd in opened if fd not in closed]:
            out.append(f"B17.record: the record's descriptor was not closed (opened {opened}, closed {closed})")

        def refuse_open(p, *a, **k):
            if os.fspath(p) == str(f):
                raise PermissionError("synthetic: the record cannot be opened")
            return real_open(p, *a, **k)
        with mock.patch.object(os, "open", refuse_open):
            refused("a record that cannot be opened", "cannot be opened")
        sibling = f.parent / "sibling.json"
        sibling.write_text("{}")
        os.chmod(sibling, 0o600)

        def swapped_lstat(p, *a, **k):
            return real_lstat(sibling if os.fspath(p) == str(f) else p, *a, **k)
        opened.clear()
        closed.clear()
        with mock.patch.object(os, "lstat", swapped_lstat), mock.patch.object(os, "open", spy_open), \
                mock.patch.object(os, "close", spy_close):
            refused("a record replaced between its check and its read", "changed between its check and its read")
        if not opened or [fd for fd in opened if fd not in closed]:
            out.append(f"B17.record: a refused read left its descriptor open (opened {opened}, closed {closed})")
        (f.parent / ".git").mkdir()
        refused("a record inside a repository", "outside every repository")
    padded = json.dumps(TEST_ACCOUNT_EMAILS).encode() + b" " * 5000
    record = json.dumps(TEST_ACCOUNT_EMAILS).encode()
    for label, raw, words in (
            ("a record larger than 4096 bytes", padded, "larger than 4096 bytes"),
            ("text that is not JSON", b"{operator", "is not one JSON object with unique keys"),
            ("bytes that are not UTF-8", b"\xff\xfe" + record, "is not one JSON object with unique keys"),
            ("a key that occurs twice", record[:-1] + b', "operator": "' + B17_OTHER.encode() + b'"}',
             "is not one JSON object with unique keys"),
            ("a key that occurs twice (another vendor's)", record[:-1] + b', "gemini": "' + B17_OTHER.encode()
             + b'"}', "is not one JSON object with unique keys")):
        with b17_folder(raw=raw):
            refused(label, words)
    for label, raw in (("a JSON list of the keys", b'["operator", "codex"]'), ("a JSON list", b"[" + record + b"]"),
                       ("a JSON string", b'"operator"')):
        with b17_folder(raw=raw):
            refused(label, "is not one JSON object")
            if said and said[-1].endswith("with unique keys"):
                out.append(f"B17.record: {label} refused as unparseable, not as a value that is not an object")
    with b17_folder(dict(TEST_ACCOUNT_EMAILS, claude=B17_OTHER)):
        for harness in ("codex", "gemini"):
            refused(f"an extra key ({harness})", ("holds keys other than", '"claude"'), harness)
    with b17_folder(dict(TEST_ACCOUNT_EMAILS, **{"Not A Name!": B17_OTHER})):
        refused("an extra key that is not a name", ("holds keys other than", "a key that is not a name"))
        if said and "Not A Name!" in said[-1]:
            out.append(f"B17.record: a refusal carries the extra key itself: {said[-1]}")
    with b17_folder({"codex": TEST_ACCOUNT_EMAILS["codex"], "gemini": TEST_ACCOUNT_EMAILS["gemini"]}):
        for harness in ("codex", "gemini"):
            refused(f"no operator key ({harness})", 'holds no key "operator"', harness)
    with b17_folder({"operator": TEST_ACCOUNT_EMAILS["operator"], "codex": TEST_ACCOUNT_EMAILS["codex"]}):
        admitted("a codex take without the gemini key", "codex")
        refused("a gemini take without the gemini key", 'holds no key "gemini"', "gemini")
    with b17_folder({"operator": TEST_ACCOUNT_EMAILS["operator"], "gemini": TEST_ACCOUNT_EMAILS["gemini"]}):
        admitted("a gemini take without the codex key", "gemini")
        refused("a codex take without the codex key", 'holds no key "codex"', "codex")
    for key in ("operator", "codex", "gemini"):
        for value in ("not-an-address", "a@b.c", "a" * 243 + "@example.invalid", "x@example.invalid\n",
                      "@example.invalid", "two@example", "", 42, None, [TEST_ACCOUNT_EMAILS["codex"]]):
            with b17_folder(dict(TEST_ACCOUNT_EMAILS, **{key: value})):
                refused(f"a {key} value {value!r:.40}", f'"{key}" value is not an email address')
    for value in ("op@a.bc", "a" * 238 + "@example.invalid"):         # the shortest and the longest lengths admitted
        with b17_folder(dict(TEST_ACCOUNT_EMAILS, operator=value)):
            try:
                got = mod.account_emails("codex")
                if tuple(got) != (value, TEST_ACCOUNT_EMAILS["codex"]):
                    out.append(f"B17.record: an operator address of length {len(value)} read as {got!r}")
            except Exception as e:  # noqa: BLE001
                out.append(f"B17.record: an operator address of length {len(value)} refused: {e}")
    for why in said:
        if any(a in why for a in tuple(TEST_ACCOUNT_EMAILS.values()) + (B17_OTHER,)):
            out.append(f"B17.record: a refusal carries an address: {why}")
    return out


@problems_by_assertion("B17.closed")
def b17_closed_problems(mod, tmp: Path) -> list:
    """No record, no vendor take: lease_secrets refuses at take start before any lease token is read, and a Gemini
    take's login_secrets when its secrets() is made; a Claude Code take's login_secrets never reads the record."""
    from box import scan_record
    out = []
    absent = str(tmp / "absent" / "account-emails.json")
    lease = str(lease_file(tmp))
    gemini_login = str(login_file(f"GEMINI_API_KEY={GEMINI_KEY}\n"))
    claude_login = str(login_file(LOGIN + "=" + "synthetic-claude-token-" + "a" * 12 + "\n"))
    reads = []
    real_lease = scan_record.read_lease_tokens

    def refused(label, fn, *args):
        try:
            fn(*args)
        except mod.BuilderRefused as e:
            if "account-emails.json" not in str(e):
                out.append(f"B17.closed: {label} refused for another reason: {e}")
            return
        except Exception as e:  # noqa: BLE001
            out.append(f"B17.closed: {label} raised {type(e).__name__}, not BuilderRefused: {e}")
            return
        out.append(f"B17.closed: {label} was admitted with no account record")

    with mock.patch.object(mod, "account_emails_path", lambda: absent), \
            mock.patch.object(scan_record, "read_lease_tokens", lambda *a, **k: reads.append(a) or real_lease(*a, **k)):
        refused("lease_secrets", mod.lease_secrets, lease)
        if reads:
            out.append("B17.closed: lease_secrets read the lease's tokens before refusing")
        refused("login_secrets for a gemini take", mod.login_secrets, gemini_login, rt.GEMINI)
    with mock.patch.object(mod, "account_emails_path", side_effect=AssertionError("B17.closed: the record was read")):
        try:
            secrets = mod.login_secrets(claude_login, rt.CLAUDE_CODE)
            if [k for k, _ in secrets()] != ["token"]:
                out.append("B17.closed: a Claude Code take's secrets are not its token alone")
        except AssertionError as e:
            out.append(str(e))
    with account_boundary(mod):
        for label, fn, args in (("lease_secrets", mod.lease_secrets, (lease,)),
                                ("login_secrets for a gemini take", mod.login_secrets, (gemini_login, rt.GEMINI))):
            try:
                secrets = fn(*args)
                pairs = [p for p in secrets() if p[0] == "email"]
                if pairs != (CODEX_EMAIL_PAIRS if fn is mod.lease_secrets else GEMINI_EMAIL_PAIRS):
                    out.append(f"B17.closed: {label}'s email pairs on a TEST DATA record are {len(pairs)} pairs")
            except Exception as e:  # noqa: BLE001
                out.append(f"B17.closed: {label} refused on a TEST DATA record: {type(e).__name__}: {e}")
    return out


class B17Account(Case):
    def test_the_account_record_s_folder(self):
        self.assertEqual(b17_path_problems(wb()), [])

    def test_the_account_record_s_rules(self):
        self.assertEqual(b17_record_problems(wb()), [])

    def test_no_record_no_vendor_take(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(b17_closed_problems(wb(), Path(t)), [])


# ------------------------------------------------------------------------------------------------- B18
# Round 11 (glitch-b5, Sat 17 Oct 2026): R-6 and round 10 ruling 3's road (build_run_tree with a harness, and
# place_instruction_file) bound in this module's generated sweep, as B17 binds the account record.
B18_TEXT = "# Synthetic instructions\n\nRead the project's README first.\n"
B18_NESTED = "# Synthetic workspace instructions\n"
B18_NATIVE = {"codex": "AGENTS.md", "gemini": "GEMINI.md"}


@contextlib.contextmanager
def b18_origin(claude_md=B18_TEXT, nested=B18_NESTED, extra=None, forced=None):
    """A scratch origin: one commit holding CLAUDE.md and gars/CLAUDE.md (either None: absent), src/, evals/ and
    `extra` files, and `forced` files tracked although the origin's own .gitignore matches them (as the pinned GARS
    tree tracks gars/00_initialize_project/CONTEXT.md under its `*_project/` line)."""
    with tbi.scratch_repo() as repo:
        (repo / "src").mkdir()
        (repo / "src" / "a.txt").write_text("synthetic source\n")
        (repo / "gars").mkdir()
        (repo / "gars" / "README.md").write_text("synthetic workspace\n")
        (repo / "evals").mkdir()
        (repo / "evals" / "hidden.txt").write_text("synthetic study file\n")
        for rel, text in ((("CLAUDE.md", claude_md), ("gars/CLAUDE.md", nested)) + tuple((extra or {}).items())
                          + tuple((forced or {}).items())):
            if text is not None:
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text(text)
        tbi.git(repo, "add", "-A")
        if forced:
            tbi.git(repo, "--literal-pathspecs", "add", "-f", "--", *forced)
        tbi.git(repo, "commit", "-q", "-m", "A synthetic origin")
        yield repo, tbi.git(repo, "rev-parse", "HEAD")


@problems_by_assertion("B18.native")
def b18_road_problems(mod) -> list:
    """build_run_tree with each harness: the native file beside every CLAUDE.md, its bytes, in the one commit."""
    out = []
    drive = MODS["drive"]
    for harness in ("codex", "gemini", rt.CLAUDE_CODE):
        with b18_origin() as (repo, sha), temp_root():
            try:
                tree = Path(mod.build_run_tree("w-0001", repo=repo, commit=sha, exclude=["evals"], harness=harness))
            except Exception as e:  # noqa: BLE001
                out.append(f"B18.native: {harness}: build_run_tree raised {type(e).__name__}: {e}")
                continue
            want = B18_NATIVE.get(harness)
            for folder, text in (("", B18_TEXT), ("gars/", B18_NESTED)):
                for name in B18_NATIVE.values():
                    if (tree / folder / name).exists() != (name == want):
                        verb = "lacks" if name == want else "carries"
                        out.append(f"B18.native: {harness}: {folder or 'the root'} {verb} {name}")
                if want and (tree / folder / want).is_file():
                    if (tree / folder / want).read_bytes() != text.encode():
                        out.append(f"B18.native: {harness}: {folder}{want} is not its CLAUDE.md's bytes")
                    if tbi.git_bytes(tree, "show", f"HEAD:{folder}{want}") != text.encode():
                        out.append(f"B18.native: {harness}: {folder}{want} is not in the checkout's one commit")
            if (tbi.git(tree, "rev-list", "--all", "--count"), tbi.git(tree, "log", "-1", "--format=%s"),
                    tbi.git(tree, "status", "--porcelain")) != ("1", drive.TREE_SUBJECT, ""):
                out.append(f"B18.native: {harness}: not one commit, its neutral subject and a clean status")
            if drive.run_tree_problems(tree, walk_sid("w-0001"), ["evals"]):
                out.append(f"B18.native: {harness}: run_tree_problems on the built checkout")
    for label, kw, words in (("no root CLAUDE.md", {"claude_md": None}, "carries no root CLAUDE.md"),
                             ("AGENTS.md already in the commit", {"extra": {"AGENTS.md": "# other\n"}},
                              "the pinned tree already carries AGENTS.md"),
                             ("gars/AGENTS.md already in the commit", {"extra": {"gars/AGENTS.md": "# other\n"}},
                              "the pinned tree already carries AGENTS.md (gars/AGENTS.md)")):
        with b18_origin(**kw) as (repo, sha), temp_root() as tmp:
            try:
                mod.build_run_tree("w-0001", repo=repo, commit=sha, exclude=["evals"], harness="codex")
                out.append(f"B18.native: {label}: a codex checkout was built")
            except mod.BuilderRefused as e:
                if words not in str(e):
                    out.append(f"B18.native: {label}: refused for another reason: {e}")
            except Exception as e:  # noqa: BLE001
                out.append(f"B18.native: {label}: raised {type(e).__name__}, not BuilderRefused: {e}")
            if list(Path(tmp).iterdir()):
                out.append(f"B18.native: {label}: a refused build left its checkout")
    return out


@problems_by_assertion("B18.place")
def b18_place_problems(mod) -> list:
    """place_instruction_file on a checkout built without it: its name handed back, and each refusal by name."""
    out = []
    sid = walk_sid("w-0001")

    def placed(label, repo, sha, tree, harness="codex", want="AGENTS.md"):
        try:
            got = mod.place_instruction_file(tree, harness, repo=repo, commit=sha, session_id=sid, exclude=["evals"])
        except Exception as e:  # noqa: BLE001
            out.append(f"B18.place: {label}: raised {type(e).__name__}: {e}")
            return
        if got != want:
            out.append(f"B18.place: {label}: handed back {got!r}, not {want!r}")

    def refused(label, words, repo, sha, tree, harness="codex"):
        try:
            mod.place_instruction_file(tree, harness, repo=repo, commit=sha, session_id=sid, exclude=["evals"])
        except mod.BuilderRefused as e:
            if words not in str(e):
                out.append(f"B18.place: {label}: refused for another reason: {e}")
            return
        except Exception as e:  # noqa: BLE001
            out.append(f"B18.place: {label}: raised {type(e).__name__}, not BuilderRefused: {e}")
            return
        out.append(f"B18.place: {label}: placed")

    @contextlib.contextmanager
    def bare_tree(**kw):
        with b18_origin(**kw) as (repo, sha), temp_root():
            yield repo, sha, Path(mod.build_run_tree("w-0001", repo=repo, commit=sha, exclude=["evals"],
                                                     harness=rt.CLAUDE_CODE))

    with bare_tree() as (repo, sha, tree):
        placed("a codex checkout", repo, sha, tree)
        if (tree / "AGENTS.md").read_bytes() != B18_TEXT.encode() \
                or (tree / "gars" / "AGENTS.md").read_bytes() != B18_NESTED.encode():
            out.append("B18.place: the placed copies are not their CLAUDE.md's bytes")
    with bare_tree() as (repo, sha, tree):
        placed("a claude-code checkout", repo, sha, tree, rt.CLAUDE_CODE, None)
        if [p for p in ("AGENTS.md", "GEMINI.md") if (tree / p).exists()]:
            out.append("B18.place: a claude-code checkout was given a native file")
    for dest in ("AGENTS.md", "gars/AGENTS.md"):
        with bare_tree() as (repo, sha, tree):
            (tree / dest).write_text("# untracked\n")
            refused(f"an untracked {dest}", f"the checkout already holds {dest}", repo, sha, tree)
    with bare_tree() as (repo, sha, tree), b18_origin(nested=None) as (other, other_sha):
        refused("a commit without gars/CLAUDE.md", "the pinned commit carries no gars/CLAUDE.md", other, other_sha,
                tree)
    gate = subprocess.run

    def altering(when):
        """subprocess.run with the placed AGENTS.md altered around `when` ("add": in the commit only; "commit": in the
        checkout only), never its CLAUDE.md."""
        def run(args, *a, **kw):
            argv = [str(x) for x in args] if isinstance(args, (list, tuple)) else []
            step = argv[3] if len(argv) > 3 and argv[:2] == ["git", "-C"] else None
            target = Path(argv[2]) / "AGENTS.md" if step == when else None
            kept = target.read_bytes() if target is not None and target.is_file() else None
            if kept is not None and when == "add":
                target.write_bytes(kept + b"altered\n")
            got = gate(args, *a, **kw)
            if kept is not None:
                target.write_bytes(kept if when == "add" else kept + b"altered\n")
            return got
        return run
    for when, label in (("add", "a copy altered in the commit"), ("commit", "a copy altered in the checkout")):
        with bare_tree() as (repo, sha, tree), mock.patch.object(subprocess, "run", altering(when)):
            refused(label, "AGENTS.md in the checkout is not its CLAUDE.md's bytes", repo, sha, tree)
    with bare_tree() as (repo, sha, tree), \
            mock.patch.object(sys.modules["drive"], "run_tree_problems", lambda *a: ["synthetic: a planted problem"]):
        refused("a checkout run_tree_problems refuses", "synthetic: a planted problem", repo, sha, tree)
    # round 12 (review c-6302fd3 NIT 7): every instruction-file name a vendor CLI reads, above the checkout, refuses
    # by name; drive.run_tree_problems (CLAUDE.md alone) is patched clean so the vendor names stand alone
    for harness in ("codex", "gemini"):
        for above, up in (("AGENTS.md", 1), ("GEMINI.md", 1), ("CLAUDE.md", 1), ("AGENTS.md", 2)):
            with bare_tree() as (repo, sha, tree), \
                    mock.patch.object(sys.modules["drive"], "run_tree_problems", lambda *a: []):
                planted = tree.parents[up - 1] / above
                planted.write_text("# synthetic: an instruction file above the checkout\n")
                try:
                    refused(f"{harness}: {above} {up} folder(s) above the checkout",
                            f"an instruction file above the checkout ({planted.resolve()})", repo, sha, tree, harness)
                finally:
                    planted.unlink()
    return out


# Round 18 B13 (glitch-26, Sun 18 Oct 2026; practice walk w-o1 on ship head 779097fc): the pinned GARS tree's own
# .gitignore lists AGENTS.md (844a4ce0 .gitignore line 74), so a plain `git add -- AGENTS.md gars/AGENTS.md` in the
# checkout exits 1 ("The following paths are ignored by one of your .gitignore files") and no codex walk got a run
# tree. The placed copies are added by exactly their paths, whatever the checkout's .gitignore says; nothing else
# the .gitignore covers, and nothing the exclusions leave out, reaches the one commit.
# glitch-26's ruling R-FB1 (Mon 19 Oct 2026; review vendor-r18-b12b13-0094246 MINOR 1): the pin tracks a file its own
# .gitignore matches (gars/00_initialize_project/CONTEXT.md under `*_project/`), which every arm's checkout holds on
# disk and leaves out of its commit. The origin here tracks two such files (B18_TRACKED_IGNORED), and each native
# arm's commit must be the claude-code commit plus exactly the placed copies, entry for entry, so a wider add (the
# review's mutant M1, `git add -f -A`) that commits them into a vendor arm alone is red.
B18_IGNORE = "AGENTS.md\nGEMINI.md\n*.log\n"
B18_TRACKED_IGNORED = {"x.log": "synthetic: tracked, and matched by the origin's .gitignore\n",
                       "gars/run/notes.log": "synthetic: tracked and ignored, in a folder\n"}


@problems_by_assertion("B18.ignored")
def b18_ignored_problems(mod) -> list:
    """build_run_tree for claude-code, codex and gemini on an origin whose .gitignore lists both native names and
    `*.log`, and which tracks two .log files: the claude-code commit holds the origin's files minus the exclusions
    and the ignored ones, and no native file; each vendor arm's commit is that commit's entries plus exactly the
    placed copies beside every CLAUDE.md, each with its bytes; every status is clean and the ignored files stay on
    disk outside the commit."""
    out = []
    entries = {}
    for harness in (rt.CLAUDE_CODE, "codex", "gemini"):
        with b18_origin(extra={".gitignore": B18_IGNORE}, forced=B18_TRACKED_IGNORED) as (repo, sha), temp_root():
            origin_files = set(tbi.git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
            if not set(B18_TRACKED_IGNORED) <= origin_files:
                out.append(f"B18.ignored: {harness}: the origin does not track {sorted(B18_TRACKED_IGNORED)}")
            try:
                tree = Path(mod.build_run_tree("w-0001", repo=repo, commit=sha, exclude=["evals"], harness=harness))
            except Exception as e:  # noqa: BLE001
                out.append(f"B18.ignored: {harness}: build_run_tree raised {type(e).__name__}: {str(e)[:300]}")
                continue
            listed = tbi.git(tree, "ls-tree", "-r", "HEAD").splitlines()
            entries[harness] = {line.split("\t", 1)[1]: line.split("\t", 1)[0] for line in listed}
            if len(entries[harness]) != len(listed):
                out.append(f"B18.ignored: {harness}: the one commit lists a path twice")
            for rel, text in B18_TRACKED_IGNORED.items():
                if not (tree / rel).is_file() or (tree / rel).read_text() != text:
                    out.append(f"B18.ignored: {harness}: {rel} is not on disk in the checkout with its bytes")
            want = B18_NATIVE.get(harness)
            for folder, text in (("", B18_TEXT), ("gars/", B18_NESTED)):
                if want and tbi.git_bytes(tree, "show", f"HEAD:{folder}{want}") != text.encode():
                    out.append(f"B18.ignored: {harness}: {folder}{want} is not its CLAUDE.md's bytes in the commit")
            if (tbi.git(tree, "rev-list", "--all", "--count"), tbi.git(tree, "status", "--porcelain")) != ("1", ""):
                out.append(f"B18.ignored: {harness}: not one commit and a clean status")
            if harness == rt.CLAUDE_CODE:
                expect = {p for p in origin_files if not (p == "evals" or p.startswith("evals/"))
                          and p not in B18_TRACKED_IGNORED}
                if set(entries[harness]) != expect:
                    out.append(f"B18.ignored: claude-code: the one commit holds {sorted(set(entries[harness]) ^ expect)}"
                               f" off the origin's files minus the exclusions and the ignored files")
    base = entries.get(rt.CLAUDE_CODE)
    for harness in ("codex", "gemini"):
        if base is None or harness not in entries:
            continue
        placed = {f"{folder}{B18_NATIVE[harness]}" for folder in ("", "gars/")}
        got = entries[harness]
        extra = sorted(set(got) - set(base) - placed)
        lost = sorted(set(base) - set(got))
        unplaced = sorted(placed - set(got))
        moved = sorted(p for p in set(base) & set(got) if got[p] != base[p])
        if extra or lost or unplaced or moved:
            out.append(f"B18.ignored: {harness}: the one commit is not the claude-code commit plus exactly the placed "
                       f"copies: extra {extra}, missing {lost}, placed copies absent {unplaced}, entries changed {moved}")
    return out


# glitch-26's ruling R-FB2 (Mon 19 Oct 2026; review vendor-r18-b12b13-0094246 NIT 3): the placed paths reach git as
# pathspecs, so a CLAUDE.md under a folder whose name git reads as pathspec syntax could add, or fail to add, another
# path. The origin's folders `:x` (a leading colon is pathspec magic) and `g[ab]` (a glob class) each hold a CLAUDE.md;
# `x/` and `ga/` hold native-named files tracked in the origin but ignored by its .gitignore, so they are on disk in
# every checkout and out of its commit. Each placed copy is added as its own literal path and nothing else.
B18_LITERAL_DIRS = (":x/", "g[ab]/")
B18_LITERAL_DECOYS = ("x/", "ga/")


@problems_by_assertion("B18.literal")
def b18_literal_problems(mod) -> list:
    """build_run_tree for codex and gemini on an origin with CLAUDE.md under B18_LITERAL_DIRS: the one commit holds
    each placed copy at its literal path with its CLAUDE.md's bytes, and no decoy the pathspec syntax would reach."""
    out = []
    extra = {".gitignore": "AGENTS.md\nGEMINI.md\n"}
    extra.update({f"{d}CLAUDE.md": f"# Synthetic instructions under {d}\n" for d in B18_LITERAL_DIRS})
    forced = {f"{d}{n}": "# synthetic: an ignored decoy\n" for d in B18_LITERAL_DECOYS for n in B18_NATIVE.values()}
    for harness in ("codex", "gemini"):
        with b18_origin(extra=extra, forced=forced) as (repo, sha), temp_root():
            try:
                tree = Path(mod.build_run_tree("w-0001", repo=repo, commit=sha, exclude=["evals"], harness=harness))
            except Exception as e:  # noqa: BLE001
                out.append(f"B18.literal: {harness}: build_run_tree raised {type(e).__name__}: {str(e)[:300]}")
                continue
            want = B18_NATIVE[harness]
            got = set(tbi.git(tree, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
            for d in B18_LITERAL_DIRS:
                if f"{d}{want}" not in got:
                    out.append(f"B18.literal: {harness}: {d}{want} is not in the one commit")
                elif tbi.git_bytes(tree, "show", f"HEAD:{d}{want}") != extra[f"{d}CLAUDE.md"].encode():
                    out.append(f"B18.literal: {harness}: {d}{want} is not its CLAUDE.md's bytes in the commit")
            reached = sorted(got & set(forced))
            if reached:
                out.append(f"B18.literal: {harness}: the one commit holds the ignored decoys {reached}")
            if (tbi.git(tree, "rev-list", "--all", "--count"), tbi.git(tree, "status", "--porcelain")) != ("1", ""):
                out.append(f"B18.literal: {harness}: not one commit and a clean status")
    return out


class B18Native(Drafted):
    def test_the_native_file_beside_every_claude_md(self):
        self.assertEqual(b18_road_problems(wb()), [])

    def test_place_instruction_file_refuses_by_name(self):
        self.assertEqual(b18_place_problems(wb()), [])

    def test_the_native_file_is_added_past_the_trees_gitignore(self):
        self.assertEqual(b18_ignored_problems(wb()), [])

    def test_each_placed_path_is_added_literally(self):
        self.assertEqual(b18_literal_problems(wb()), [])


# ------------------------------------------------------------------------------------------------- B21
# Lane vendor-b11 round 2, R-H5 (glitch-26's ruling on the B11 design note, Mon 19 Oct 2026): a codex or gemini
# checkout carries the agent's own HOME, the run tree's .home (box/run_take.RUN_TREE_HOMEDIR, the row's HOME), an empty
# folder of mode 700, git-excluded like .tmp so what the agent's tools write there never reaches the status it is
# shown; it is the run tree's, so the ownership grant gives it to the agent with the run tree. A Claude Code checkout
# carries none (arm A's HOME is the config mount).
@problems_by_assertion("R-H5.home")
def b21_home_problems(mod) -> list:
    import stat
    out = []
    if getattr(rt, "RUN_TREE_HOMEDIR", None) != ".home":
        out.append("R-H5.home: box/run_take.RUN_TREE_HOMEDIR is not .home")
    for h in (rt.CODEX, rt.GEMINI):
        if rt.TAKE_ENV[h].get("HOME") != getattr(rt, "RUN_TREE_HOME", None):
            out.append(f"R-H5.home: the {h} row's HOME is not the run tree's home marker")
    for harness in ("codex", "gemini", rt.CLAUDE_CODE):
        with b18_origin() as (repo, sha), temp_root():
            try:
                tree = Path(mod.build_run_tree("w-0001", repo=repo, commit=sha, exclude=["evals"], harness=harness))
            except Exception as e:  # noqa: BLE001
                out.append(f"R-H5.home: {harness}: build_run_tree raised {type(e).__name__}: {e}")
                continue
            home = tree / ".home"
            if harness == rt.CLAUDE_CODE:
                if os.path.lexists(home):
                    out.append("R-H5.home: a Claude Code checkout carries .home")
                continue
            if home.is_symlink() or not home.is_dir():
                out.append(f"R-H5.home: a {harness} checkout carries no .home folder")
                continue
            if stat.S_IMODE(os.lstat(home).st_mode) != 0o700 or list(home.iterdir()):
                out.append(f"R-H5.home: a {harness} checkout's .home is not an empty folder of mode 700")
            (home / ".cache").mkdir()
            (home / ".cache" / "probe").write_text("synthetic\n")
            if tbi.git(tree, "status", "--porcelain"):
                out.append(f"R-H5.home: a file in a {harness} checkout's .home shows in its git status")
            shutil.rmtree(home / ".cache")
    return out


class B21AgentHome(Drafted):
    def test_a_vendor_checkout_carries_the_agent_home(self):
        self.assertEqual(b21_home_problems(wb()), [])


# ------------------------------------------------------------------------------------------------- B22
# Lane vendor-b11, R-H5-2 (glitch-26, Mon 19 Oct 2026): place_agent_home called on its own, each statement pinned by
# its effect, so none of its generated mutants survives (athena's battery on 9d473873 left twelve alive). Each test
# builds the bare checkout (no native file, no HOME) on b18_origin and calls the function directly.
class B22AgentHomePlaced(Drafted):
    @contextlib.contextmanager
    def bare_tree(self, **kw):
        with b18_origin(**kw) as (repo, sha), temp_root():
            tree = self.must("R-H5-2.home", wb().build_run_tree, "w-0001", repo=repo, commit=sha, exclude=["evals"],
                             harness=rt.CLAUDE_CODE)
            yield Path(tree)

    def place(self, tree, harness, umask=None):
        if umask is None:
            return self.must("R-H5-2.home", wb().place_agent_home, tree, harness, session_id=walk_sid("w-0001"),
                             exclude=["evals"])
        old = os.umask(umask)
        try:
            return self.must("R-H5-2.home", wb().place_agent_home, tree, harness, session_id=walk_sid("w-0001"),
                             exclude=["evals"])
        finally:
            os.umask(old)

    @staticmethod
    def exclude_bytes(tree) -> bytes:
        return (Path(tree) / ".git" / "info" / "exclude").read_bytes()

    def test_a_claude_code_checkout_gets_none(self):
        with self.bare_tree() as tree:
            before = self.exclude_bytes(tree)
            self.assertIsNone(self.place(tree, rt.CLAUDE_CODE), "R-H5-2.home: a Claude Code checkout got a name")
            self.assertFalse(os.path.lexists(tree / ".home"), "R-H5-2.home: a Claude Code checkout got .home")
            self.assertEqual(self.exclude_bytes(tree), before, "R-H5-2.home: a Claude Code checkout's exclude changed")

    def test_the_name_is_returned_and_the_exclude_appended(self):
        for harness in (rt.CODEX, rt.GEMINI):
            with self.subTest(harness=harness), self.bare_tree() as tree:
                before = self.exclude_bytes(tree)
                self.assertTrue(before.endswith(b"\n") and b".tmp/" in before, "R-H5-2.home: the bare exclude")
                self.assertEqual(self.place(tree, harness), ".home",
                                 f"R-H5-2.home: a {harness} checkout's HOME name is not handed back")
                self.assertEqual(self.exclude_bytes(tree), before + b".home/\n",
                                 f"R-H5-2.home: a {harness} checkout's exclude is not its old lines plus .home/")
                home = tree / ".home"
                self.assertTrue(home.is_dir() and not home.is_symlink() and not list(home.iterdir()),
                                f"R-H5-2.home: a {harness} checkout's .home is not an empty folder")
                self.assertEqual(MODS["drive"].run_tree_problems(tree, walk_sid("w-0001"), ["evals"]), [],
                                 f"R-H5-2.home: a {harness} checkout with .home has run_tree_problems")

    def test_the_home_is_700_whatever_the_umask(self):
        # mkdir(mode=0o700) can only lose bits to a umask, so the chmod shows only under one taking owner bits (0o277:
        # mkdir alone gives 0o500). Not 0o777: git's own index refresh in run_tree_problems then writes an index git
        # cannot read back, a refusal of the whole checkout that says nothing about .home.
        for umask in (0o000, 0o022, 0o077, 0o277):
            with self.subTest(umask=oct(umask)), self.bare_tree() as tree:
                self.assertEqual(self.place(tree, rt.CODEX, umask=umask), ".home", "R-H5-2.home")
                got = stat.S_IMODE(os.lstat(tree / ".home").st_mode)
                os.chmod(tree / ".home", 0o700)            # so the scratch folder is always removable
                self.assertEqual(oct(got), oct(0o700), f"R-H5-2.home: under umask {umask:o}, .home is {got:o}")

    def test_a_checkout_already_holding_the_name_is_refused(self):
        def folder(home):
            home.mkdir()
            return lambda: home.is_dir() and not home.is_symlink() and not list(home.iterdir())

        def regular(home):
            home.write_text("synthetic occupant\n")
            return lambda: home.is_file() and not home.is_symlink() and home.read_text() == "synthetic occupant\n"

        def dangling(home):
            os.symlink(home.parent / "nowhere-synthetic", home)
            return lambda: home.is_symlink() and os.readlink(home) == str(home.parent / "nowhere-synthetic") \
                and not home.exists()

        for label, occupy in (("a folder", folder), ("a file", regular), ("a dangling link", dangling)):
            for harness in (rt.CODEX, rt.GEMINI):
                with self.subTest(occupant=label, harness=harness), self.bare_tree() as tree:
                    unchanged = occupy(tree / ".home")
                    before = self.exclude_bytes(tree)
                    self.refuses("R-H5-2.home", "already holds .home", wb().place_agent_home, tree, harness,
                                 session_id=walk_sid("w-0001"), exclude=["evals"])
                    self.assertTrue(unchanged(), f"R-H5-2.home: {label} named .home was changed")
                    self.assertEqual(self.exclude_bytes(tree), before,
                                     f"R-H5-2.home: {label} named .home refused, but the exclude was written")

    def test_an_exclude_that_does_not_take_is_refused(self):
        # The pinned tree's own .gitignore negates .home/ (it outranks .git/info/exclude), committed, so the status
        # stays clean and only the check-ignore read can see that the appended line does not take.
        with self.bare_tree(extra={".gitignore": "!.home/\n"}) as tree:
            self.assertEqual(tbi.git(tree, "status", "--porcelain"), "", "R-H5-2.home: the negating tree")
            self.refuses("R-H5-2.home", "is not git-excluded", wb().place_agent_home, tree, rt.CODEX,
                         session_id=walk_sid("w-0001"), exclude=["evals"])

    def test_run_tree_problems_is_read_on_the_built_tree(self):
        drive = MODS["drive"]
        with self.bare_tree() as tree:                     # a real problem: a stray file in the checkout's status
            (tree / "stray-synthetic.txt").write_text("synthetic\n")
            self.refuses("R-H5-2.home", "status is not clean", wb().place_agent_home, tree, rt.GEMINI,
                         session_id=walk_sid("w-0001"), exclude=["evals"])
        with self.bare_tree() as tree:                     # any problem refuses, read with this tree's own inputs
            seen = []

            def one_problem(t, sid, exclude):
                seen.append((Path(t), sid, list(exclude), (Path(t) / ".home").is_dir()))
                return ["synthetic problem R-H5-2"]
            with mock.patch.object(drive, "run_tree_problems", one_problem):
                self.refuses("R-H5-2.home", "synthetic problem R-H5-2", wb().place_agent_home, tree, rt.CODEX,
                             session_id=walk_sid("w-0001"), exclude=["evals"])
            self.assertEqual(seen, [(tree, walk_sid("w-0001"), ["evals"], True)],
                             "R-H5-2.home: run_tree_problems not read once on the built tree")


# ------------------------------------------------------------------------------------------------- B19
# Round 17 B6 (plan codex2-signin-road section 5; glitch-b5's ruling R3): a codex or gemini walk's per-take config is
# written on the walk road, by walk_driver_for's spec_for (box/take_config.write over the row's model), into the empty
# config folder before the lease, the settings baseline and the grant. drive.TakeDriver calls spec_for before
# _grant_ownership (drive.py, read here and never edited), so a config spec_for leaves is there at the grant.
def drive_spec_before_grant(text: str) -> bool:
    """Whether drive.py's take start calls spec_for before the ownership grant (one statement each, in order)."""
    spec, grant = "        spec = self.spec_for(row, cfg)", "        self._grant_ownership(take)"
    return text.count(spec) == 1 and text.count(grant) == 1 and text.index(spec) < text.index(grant)


@problems_by_assertion("B19.config")
def b19_config_problems(mod, tmp: Path) -> list:
    """Through the real walk_driver_for on fakes: spec_for writes a codex walk's config.toml (web_search disabled,
    the ChatGPT login method, the row's model and its sourced effort) before it places the lease, a gemini walk's
    .gemini/settings.json (tools.exclude, the row's model, the sourced thinking and auth settings), and nothing for a
    Claude Code walk; and drive.py's take start runs spec_for before the grant. On a TEST DATA account record."""
    with account_boundary(mod):
        return _b19_config_problems(mod, tmp)


def _b19_config_problems(mod, tmp: Path) -> list:
    import tomllib
    out = []
    drive = MODS["drive"]
    drive_text = (HERE / "drive.py").read_text()
    if not drive_spec_before_grant(drive_text):
        out.append("B19.config: drive.py's take start does not run spec_for before the ownership grant")
    spec, grant = "        spec = self.spec_for(row, cfg)", "        self._grant_ownership(take)"
    swapped = drive_text.replace(spec, "\0").replace(grant, spec).replace("\0", grant)   # written after the grant
    if drive_spec_before_grant(swapped):
        out.append("B19.config: the order check reads a take start that grants before spec_for as in order")
    src = str(lease_file(tmp))
    builders = {"lease_path": src, "rules_scanner": lambda paths: [], "runtime": "rt", "config_parent": str(tmp),
                "budgets": (600, 5, 1), "take_spec": lambda r, c, t: "spec", "sidecar_for": None, "proxy": None,
                "lock_path": None, "hosts": None, "cgroup_dir_for": lambda t: "", "pin_for": None,
                "uid_map": lambda t: TAKE_UID_MAP, "clock": time.time, "sleep": None, "ownership": None,
                "settings_guard": None, "machine_gate": None,
                "design_for": lambda r, t: types.SimpleNamespace(script=[{"n": 1, "line": "one"}])}
    gemini_login = str(login_file(f"GEMINI_API_KEY={GEMINI_KEY}\n"))
    rows = (({"walk": "w-0001", "arm": "O", "model": "gpt-6.1-sol", "agent": {"harness": rt.CODEX,
                                                                              "version": "0.162.1"}}, "-"),
            ({"walk": "w-0001", "arm": "G", "model": "gemini-3.8-flash", "agent": {"harness": rt.GEMINI,
                                                                                   "version": "0.64.0"}}, gemini_login),
            ({"walk": "w-0001", "arm": "A", "model": "claude-sonnet-5-5", "agent": {"harness": rt.CLAUDE_CODE,
                                                                                    "version": "2.1.296"}},
             "/synthetic/login"))
    for n, (row, login) in enumerate(rows):
        harness, got = row["agent"]["harness"], {}
        cfg = tmp / f"cfg-b19-{n}"
        cfg.mkdir(mode=0o700)
        with lease_boundary(mod), \
                mock.patch.object(drive, "walk_driver", lambda **kw: got.setdefault("driver", kw) and "driver"), \
                mock.patch.object(drive, "WalkRepo", lambda **kw: got.setdefault("repo", kw) and "repo"), \
                mock.patch.object(drive, "records_repo", lambda root: "/synthetic/repo"), \
                mock.patch.object(mod, "build_walk_fixture", lambda r, t, p: ({"sha256": "0" * 64}, "/synthetic/src")), \
                mock.patch.object(mod, "walk_identity", lambda *a, **k: {"walk": "w-0001"}), \
                mock.patch.object(mod, "login_secrets", lambda login, harness: (lambda: [])):
            try:
                mod.walk_driver_for(builders, row, login, tmp / "tree")
                got["driver"]["spec_for"](row, str(cfg))
            except Exception as e:  # noqa: BLE001
                out.append(f"B19.config: a {harness} walk's spec_for raised {type(e).__name__}: {str(e)[:200]}")
                continue
        names = sorted(str(p.relative_to(cfg)) for p in cfg.rglob("*") if p.is_file())
        if harness == rt.CODEX:
            if names != ["auth.json", "config.toml"]:
                out.append(f"B19.config: a codex walk's config folder holds {names}, not config.toml and the lease")
                continue
            doc = tomllib.loads((cfg / "config.toml").read_text())
            want = {"model": "gpt-6.1-sol", "model_reasoning_effort": "low", "web_search": "disabled",
                    "forced_login_method": "chatgpt", "cli_auth_credentials_store": "file",
                    # R-H1 (glitch-26, 19 Oct 2026): the walk's run tree trusted up front, keyed by its own path
                    "projects": {str(tmp / "tree"): {"trust_level": "trusted"}}}
            if {k: doc.get(k) for k in want} != want:
                out.append(f"B19.config: a codex walk's config.toml reads {doc}")
        elif harness == rt.GEMINI:
            if names != [".gemini/settings.json"]:
                out.append(f"B19.config: a gemini walk's config folder holds {names}, not .gemini/settings.json")
                continue
            doc = json.loads((cfg / ".gemini" / "settings.json").read_text())
            # Lane vendor-b14 round 2 (glitch-26's ruling R-B14-2): invoke_agent joins D8's excluded tools.
            if doc.get("tools") != {"exclude": ["google_web_search", "web_fetch", "invoke_agent"]} or \
                    doc.get("model") != {"name": "gemini-3.8-flash"} or \
                    doc.get("security") != {"auth": {"selectedType": "gemini-api-key"},
                                            "folderTrust": {"enabled": False}} or \
                    "modelConfigs" not in doc:    # round 18 B9: folder trust off (glitch-26's ruling B9)
                out.append(f"B19.config: a gemini walk's settings.json reads {doc}")
        elif names:
            out.append(f"B19.config: a Claude Code walk's spec_for wrote {names} into its config folder")
    return out


class B19VendorConfig(Drafted):
    def test_the_vendor_config_is_written_on_the_walk_road(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(b19_config_problems(wb(), Path(t)), [])


class B20LeaseSource(Case):
    """B7-F3 (glitch-b5, 18 Oct 2026; B2's lease_source_path, round 17, whose guards the athena sweep of 68caad62 left
    with six unlisted survivors): the Codex lease source is read from box/run_take.LEASE_SOURCES by account. A tree
    whose run_take has no such record (the attribute absent, not a mapping, or without the account) reads as Missing,
    naming the account, never a crash; a recorded path that is not an absolute string is refused by name."""

    @contextlib.contextmanager
    def sources(self, value=None, absent=False):
        """run_take.LEASE_SOURCES set to `value` (or absent) for the block, restored after."""
        from box import run_take as rt
        with mock.patch.object(rt, "LEASE_SOURCES", value):
            if absent:
                delattr(rt, "LEASE_SOURCES")
            yield

    def source(self, value=None, absent=False):
        """lease_source_path() under sources(value, absent), its outcome read by assertion (a raise is a red)."""
        with self.sources(value, absent):
            return self.must("B20.source", wb().lease_source_path)

    def test_no_record_reads_missing_by_account(self):
        account = wb().LEASE_ACCOUNT
        for name, kwargs in (("absent", {"absent": True}), ("a list naming the account", {"value": [account]}),
                             ("the account as a string", {"value": account}), ("an empty mapping", {"value": {}}),
                             ("another account only", {"value": {"codex9": "/srv/other/auth.json"}})):
            with self.subTest(name=name):
                got = self.source(**kwargs)
                self.assertIsInstance(got, wb().Missing, f"B20.source: {name} gave {got!r}")
                self.assertIn(repr(account), got.why, f"B20.source: {name}'s Missing names no account")

    def test_a_recorded_path_must_be_an_absolute_string(self):
        account = wb().LEASE_ACCOUNT
        for value in (None, 7, ["/srv/a/auth.json"], "relative/auth.json", ""):
            with self.subTest(value=value):
                with self.sources({account: value}):
                    self.refuses("B20.source", "is not an absolute path", wb().lease_source_path)
        self.assertEqual(self.source({account: "/srv/codex2/auth.json"}), "/srv/codex2/auth.json", "B20.source")


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
