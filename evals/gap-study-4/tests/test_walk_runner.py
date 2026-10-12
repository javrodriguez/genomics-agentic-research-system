#!/usr/bin/env python3
"""The CP6 walk runner (Gap Study round 4, lane w10-walk-runner; glitch-2f's rulings D1, D2, D3 under Javier's
standing delegation, Mon 12 Oct 2026).

A walk is driven through the walk arm (walk_driver(records="walks"), so the W1 pre-launch check applies), checked by
check4's round-4 walk road, graded, and committed by WalkRepo with its register entry, one walk at a time
(walk_runner.run_walks). Each clause below was a probe variant first (lane-reports/w10-walk-runner.md).

  R1  the chain: one walk, end to end on the fake box (the REAL Claude Code adapter, the REAL check4 on the real
      design), committed under the walk subject with its register entry and reason; its folder holds the driver
      ledger, check.json and grade.json, and its identity is the walk's own (D2: session id
      uuid5(takes.namespace(), "walk/" + id), row and row_commit None); nothing is written under takes/;
      walk_register's check and run.py's regrade each count exactly one walk; the per-take config folder is deleted.
      Witnesses: walk-config-left (the runner never calls published), walk-check-unwritten (check.json not written).
  R2  D1, the walk road: before the freeze no takes.json row exists, and the walk is read with no session-binding
      reason (the take road would raise one); check_walk refuses the same transcript read as another walk's; a walk
      whose identity is a take's (row 0, a row commit) is refused at launch with nothing made, and the runner moves
      on to the next walk. Each session binding is shown alone (a copy whose ledger names another walk's session).
      Witnesses: walk-checked-as-take, walk-session-unbound, walk-ledger-session-unbound, walk-identity-unchecked,
      launch-refused-stops.
  R3  D3, a walk that dies before turn 1 (preflight fails): committed with no driver ledger, its grade.json "not
      graded, because ..." and its check.json; the register counts it, the regrade agrees, and the readers that need
      a session (mode_binding --walks, fixture_walk) skip it while the register still lists it; a folder without
      check.json breaks the content rule. Witnesses: dead-walk-ledger-required, dead-walk-ungraded,
      check-file-optional.
  R4  a walk whose drive raises is never committed: a postflight refusal (a credential-like file) keeps its walk
      folder and its config folder for a human, the register check goes red, and the runner stops before the next
      walk; a drive-scan refusal keeps its walk folder and deletes its config folder. Witnesses: held-committed,
      held-continues, postflight-config-deleted.
  R5  round 3's walk meaning is untouched: check_take.py at the base (f14ab57b) is a byte prefix of this one up to
      its `if __name__` block, no appended top-level name shadows a base name, and the base module and this one give
      the same problems and the same printed lines for one transcript read as a round-3 walk. Witness:
      round3-shadowed.
  R6  the CLI refuses, naming Q-w7b-3 (no production builder of walk_driver from the real box yet). Witness:
      cli-runs.
  R7  a walk row's slot is its walk id; any other slot is refused before launch, nothing made. Witness:
      slot-unchecked.
  R8  (review fold w10-R1-fold, W10-R1-1) D1's walk road, one binding at a time: a clean committed walk's folder is
      copied, one fact changed (a record that cross-binds it forged to agree), and check4_walk reads it; the lines it
      adds over the clean copy are exactly the bound guard's. One test and one witness per guard: the row-needed
      assertion, the ledger's task/half, row, row_commit, the environment record, its row, its row_commit, the
      model, a missing model, the constants, the checkout, the pinned instructions, the permission mode, the design
      tree and the arm. The machinery: the check_take the drive imports is this module's (a witness included), and a
      walk driven through the drive in another tree is readers-disagree in its check.json (witness
      walk-tree-unchecked-through-drive). R2 gains the walk's own session id with a row, and with a row commit, each
      refused alone (witnesses walk-identity-row-admitted, walk-identity-row-commit-admitted).
  R9  (Q-w10-1) the fake sidecar watches the half's planted paths, so the REAL v4 grader grades a fake walk end to
      end and run.py's regrade agrees. Witness: real-grader-bypassed.
  Fold W10-R1-2 (R4): the config folder is touched only once driver.launch was reached for the row (a walk refused
  before launch whose slot names a held walk leaves that walk's kept folder alone; witness published-before-launch)
  and kept whenever postflight.json exists and is not ok, even when teardown.json could not be written (witness
  keep-keyed-on-teardown). check.json says whether the checker ran (R1, R3; witness checked-always).

TEST DATA, NEVER PRODUCTION VALUES: test_walk_wiring's rig (its walk constants, routing pin, row and fixture record),
with the walk's own identity. Fakes and synthetic strings only: no model, vendor, network, container runtime,
credential, salt or holdout. The process guard and scratch repositories are test_box_integration's.

--mutant NAME compiles one altered module in memory before the bound test runs; --witnesses runs every registered
mutant in its own process, only its bound test, and requires that test to fail by an AssertionError carrying its
clause token, with no error (rule B).
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

BASE = "f14ab57b"                       # wave 9's head, this lane's base: round 3's check_take.py as it stood
_got = subprocess.run(["git", "-C", str(REPO), "show", f"{BASE}:evals/gap-study-4/check_take.py"],
                      capture_output=True)   # read before test_box_integration's process guard is armed
BASE_CHECK_TAKE = _got.stdout.decode("utf-8") if _got.returncode == 0 else None

import takes  # noqa: E402
import test_box_integration as tbi  # noqa: E402
import test_walk_wiring as tww  # noqa: E402
import variants  # noqa: E402
from box import run_take as rt  # noqa: E402

SELECTED = None
MODS: dict = {}
LANE = "w10-walk-runner"


def mutants():
    """name -> (clause, module, old text, new text). Each weakens one guard; old must occur exactly once."""
    return {
        "walk-config-left": ("R1.chain", "walk_runner",
                             "            kept = _publish(driver, row, folder)\n", "            kept = None\n"),
        "walk-check-unwritten": ("R1.chain", "walk_runner",
                                 "    write_check(folder, check_record(walk, records, table, route_fn, checked=checked))\n",
                                 ""),
        "checked-always": ("R3.dead-walk", "walk_runner", "\"checked\": checked is True", "\"checked\": True"),
        "walk-checked-as-take": ("R2.walk-check", "drive",
                                 "        if records == \"walks\":                    # D1: the round-4 walk road\n",
                                 "        if False:                    # D1: the round-4 walk road\n"),
        "walk-session-unbound": ("R2.walk-check", "check_take",
                                 "    if sid != want:                                  # D2",
                                 "    if False:                                  # D2"),
        "walk-ledger-session-unbound": ("R2.walk-check", "check_take",
                                        "    if ledger.get(\"session_id\") != want:", "    if False:"),
        "walk-identity-unchecked": ("R2.walk-check", "drive",
                                    "    walk_identity_problems(driver, row)           # D2, before anything is made\n",
                                    ""),
        "launch-refused-stops": ("R2.walk-check", "walk_runner",
                                 "            continue                                   # D3: reported, move on\n",
                                 "            break\n"),
        "dead-walk-ledger-required": ("R3.dead-walk", "drive",
                                      "    if LEDGER_FILE not in tops and not (tops & set(WALK_PRE_TURN)):",
                                      "    if LEDGER_FILE not in tops:"),
        "dead-walk-ungraded": ("R3.dead-walk", "run",
                               "    if not (folder / \"driver-ledger.json\").is_file():         # D3",
                               "    if False:         # D3"),
        "check-file-optional": ("R3.dead-walk", "drive",
                                "WALK_REQUIRED = (WALK_GRADE, WALK_CHECK)", "WALK_REQUIRED = (WALK_GRADE,)"),
        "held-committed": ("R4.held", "walk_runner",
                           "    if drive_error is not None or removal_error is not None:",
                           "    if False:"),
        "held-continues": ("R4.held", "walk_runner",
                           "            break                                      # D3: kept for a human, stop\n",
                           "            continue\n"),
        "postflight-config-deleted": ("R4.held", "walk_runner",
                                      "    if post.exists() and not postflight_ok(folder):", "    if False:"),
        "keep-keyed-on-teardown": ("R4.held", "walk_runner",
                                   "    if post.exists() and not postflight_ok(folder):",
                                   "    if (Path(folder) / TEARDOWN_FILE).is_file() and not postflight_ok(folder):"),
        "published-before-launch": ("R4.held", "walk_runner", "        if reached:\n", "        if True:\n"),
        "walk-identity-row-admitted": ("R2.walk-check", "drive", "ident.get(\"row\") is not None \\",
                                       "False \\"),
        "walk-identity-row-commit-admitted": ("R2.walk-check", "drive",
                                              "            or ident.get(\"row_commit\") is not None:",
                                              "            or False:"),
        "walk-row-needed-unasserted": ("R8.walk-road", "check_take",
                                       "    if not problems or problems[-1] != TAKE_ROW_NEEDED or "
                                       "problems.count(TAKE_ROW_NEEDED) != 1:", "    if False:"),
        "walk-ledger-cell-unbound": ("R8.walk-road", "check_take",
                                     "    if (ledger.get(\"task\"), ledger.get(\"half\")) != (task_id, half_name):",
                                     "    if False:"),
        "walk-ledger-row-unbound": ("R8.walk-road", "check_take", "ledger.get(\"row\") is not None or ", ""),
        "walk-ledger-row-commit-unbound": ("R8.walk-road", "check_take",
                                           " or ledger.get(\"row_commit\") is not None:", ":"),
        "walk-environment-unread": ("R8.walk-road", "check_take",
                                    "    problems += environment_problems(path, ledger, walk_pre, None)", "    pass"),
        "walk-environment-row-unbound": ("R8.walk-road", "check_take", "rec.get(\"row\") is not None or ", ""),
        "walk-environment-row-commit-unbound": ("R8.walk-road", "check_take",
                                                " or rec.get(\"row_commit\") is not None)", ")"),
        "walk-model-unbound": ("R8.walk-road", "check_take",
                               "        problems += model_problems(path, ledger[\"model_requested\"])\n",
                               "        pass\n"),
        "walk-model-missing-admitted": ("R8.walk-road", "check_take",
                                        "    if ledger.get(\"model_requested\"):", "    if True:"),
        "walk-constants-unread": ("R8.walk-road", "check_take",
                                  "    problems += constant_problems(ledger, walk_pre)", "    pass"),
        "walk-checkout-unread": ("R8.walk-road", "check_take",
                                 "    problems += checkout_problems(path, walk_pre)\n", ""),
        "walk-instructions-unread": ("R8.walk-road", "check_take",
                                     "    problems += pinned_instruction_problems(path, design)               # D1",
                                     "    pass               # D1"),
        "walk-mode-unread": ("R8.walk-road", "check_take",
                             "    problems += recorded_mode_problems(path, design.pre, arm)          # D1",
                             "    pass          # D1"),
        "walk-tree-unchecked": ("R8.walk-road", "check_take",
                                "    problems += design_tree_problems(path, design)                     # D1",
                                "    pass                     # D1"),
        "walk-tree-unchecked-through-drive": ("R8.walk-road", "check_take",
                                              "    problems += design_tree_problems(path, design)                     # D1",
                                              "    pass                     # D1"),
        "walk-arm-unbound": ("R8.walk-road", "check_take",
                             "    if isinstance(beside, dict) and beside.get(\"arm\") != arm:", "    if False:"),
        "real-grader-bypassed": ("R9.real-grade", "run",
                                 "(grade_walk_folder if grade is None else grade)(row, folder)",
                                 "(grade or (lambda r, f: {\"label\": \"synthetic-bypass\"}))(row, folder)"),
        "round3-shadowed": ("R5.round3", "check_take",
                            "\n\nif __name__ == \"__main__\":",
                            "\n\ndef fixture_binding_problems(path, half, is_walk=True):\n    return [], None\n"
                            "\n\nif __name__ == \"__main__\":"),
        "cli-runs": ("R6.cli", "walk_runner", "    print(f\"refused: {CLI_REFUSAL}\", file=sys.stderr)\n    return 2",
                     "    return 0"),
        "slot-unchecked": ("R7.slot", "walk_runner", "    if row.get(\"slot\") != walk:", "    if False:"),
    }


def compile_module(name: str, source: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(HERE / f"{name}.py")
    sys.modules[name] = mod
    exec(compile(source, mod.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


SOURCES: dict = {}


def setUpModule():
    tbi.setUpModule()
    MODS["drive"] = tbi.drive
    if SELECTED is not None:
        _, target, old, new = mutants()[SELECTED]
        path = HERE / f"{target}.py"
        text = path.read_text()
        assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
        SOURCES[target] = text.replace(old, new)
        if target == "drive":
            MODS["drive"] = tbi.witness_module(((old, new),))
        else:
            MODS[target] = compile_module(target, SOURCES[target])
    for name in ("check_take", "run", "walk_register", "mode_binding", "fixture_walk", "walk_runner", "routing"):
        if name not in MODS:
            try:
                MODS[name] = __import__(name)
            except ImportError:            # a module the slice must provide: its absence is a red by assertion
                MODS[name] = types.SimpleNamespace()


def tearDownModule():
    if SELECTED is not None:
        for name in ("check_take", "run", "walk_runner"):
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


# ------------------------------------------------------------------------------------------------- the rig
def walk_sid(walk: str) -> str:
    """D2, recomputed here from the ruling's words, never read from the module under test."""
    import uuid
    return str(uuid.uuid5(takes.namespace(), "walk/" + walk))


def stand_in_grade(row, folder):
    return {"label": "synthetic-label", "views": {"strict": "right"}, "graded_by": "graders/synthetic.py"}


class WalkWired(tww.Wired):
    """test_walk_wiring's rig on the walk arm: walk_driver(records="walks"), each row's identity the walk's own (D2:
    session id from the walk id, row and row_commit None), and a WalkRepo over the scratch study."""

    def __init__(self, mod, ct, root: Path, *, take_identity=False, identity_over=None, opened_in=None,
                 watch_planted=False):
        self.take_identity, self.identity_over = take_identity, dict(identity_over or {})
        super().__init__(mod, ct, root, opened_in=opened_in)
        if watch_planted:                 # Q-w10-1: the fake sidecar watches what the v4 grader reads
            self.box.evidence = self._watching_planted(self.box.evidence)
        self.repo = mod.WalkRepo(runtime=self.box, secrets=lambda: [("token", tbi.TOKEN)],
                                 rules_scanner=lambda paths: [], root=root, repo=root)

    def _build(self, mod, login, root=None):
        root = self.root if root is None else root
        return mod.walk_driver(
            runtime=self.box, root=str(root), config_parent=str(self.cfg_parent), spec_for=self.spec_for,
            sidecar_for=self.sidecar_for, proxy=rt.ProxyLaunch(
                image="sha256:" + "9" * 64, conf_source=str(tbi.SCRATCH / "proxy.conf"),
                conf_target="/etc/squid/x.conf", command=("squid", "-N"), user="13:13", alias="proxy"),
            lock_path=str(tbi.SCRATCH / "synthetic.lock"), hosts={"api": "synthetic.invalid"}, login_file=str(login),
            counters_for=lambda take: {"oom_kill": 0, "pids_max": 0}, pin_for=self.pin_for,
            design_for=self.design_for, project_for=self.project_for, identity_for=self.identity_for,
            secrets=lambda: [("token", tbi.TOKEN)], rules_scanner=lambda paths: [], uid_map=tbi.UID_MAP,
            budget_s=600, finalize_wait_s=tbi.CAP_S, poll_s=tbi.POLL_S, clock=self.clock, sleep=self.clock.sleep,
            records="walks")

    def project_for(self, row):
        return self.mod.neutral_name(walk_sid(row["walk"]))

    def identity_for(self, row):
        if self.take_identity:
            return super().identity_for(row)
        source = variants.render_source(variants.load_task(row["task"])["source_template"], str(self.tree),
                                        self.project_for(row))
        return dict({"session_id": walk_sid(row["walk"]), "row": None, "row_commit": None, "source": source,
                     "fixture": tww.fixture_record(row), "gars_tree_sha": self.ct.GARS_TREE_SHA}, **self.identity_over)

    def _watching_planted(self, evidence):
        """The fake sidecar's evidence with watched.json listing the half's planted paths (variants.grader_spec's
        `planted`, the paths the v4 grader reads), written before test_box_integration's default synthetic list."""
        def ev(sid, label):
            row = self.row
            planted = variants.grader_spec(row["task"], row["half"], row["wording"], pressure=row["pressure"],
                                           project=self.project_for(dict(row, walk=self.current)))["planted"]
            path = Path(self.box.containers[sid]["ev"]) / "watched.json"
            if not path.exists():
                path.write_text(json.dumps({"paths": sorted(set(planted))}))
            return evidence(sid, label)
        return ev

    current = None

    def walk(self, walk: str, **over) -> dict:
        self.current = walk
        return {"row": dict(dict(self.row, walk=walk, slot=walk), **over), "reason": f"synthetic: walk {walk} of the tests"}

    def run_walks(self, walks, **kw):
        with tbi.spying(self.spy):
            return MODS["walk_runner"].run_walks(self.driver, self.repo, walks, table=self.table,
                                                 grade=stand_in_grade, **kw)


@contextlib.contextmanager
def prefreeze():
    """The study as it stands before the freeze: takes.json holds no row, so the take road has nothing to bind to."""
    with mock.patch.object(takes, "load_rows", lambda **kw: tww.REAL_LOAD_ROWS(**kw) if kw else []), \
            mock.patch.object(takes, "row_commits", lambda **kw: tww.REAL_ROW_COMMITS(**kw) if kw else {}):
        yield


@contextlib.contextmanager
def study(**kw):
    """test_walk_wiring's world, before the freeze, over a scratch study: the draft, tasks/, rehearsals/ committed."""
    import mode_binding as mb
    with tww.world() as ct, prefreeze(), tbi.scratch_repo() as root:
        shutil.copy(HERE / "prereg-draft.json", root / "prereg-draft.json")
        shutil.copytree(HERE / "tasks", root / "tasks")
        (root / mb.WALKS_DIR).mkdir()
        (root / mb.WALKS_DIR / "README.md").write_text("synthetic\n")
        (root / mb.WALKS_DIR / "register.json").write_text('{\n  "schema": 1,\n  "walks": []\n}\n')
        tbi.git(root, "add", "-A")
        tbi.git(root, "commit", "-q", "-m", "A synthetic study skeleton")
        yield WalkWired(MODS["drive"], ct, root, **kw)


def register_check(w) -> tuple[list, int]:
    import mode_binding as mb
    wr = MODS["walk_register"]
    return wr.check(w.root / mb.WALKS_DIR, wr.design_in_force(w.root))


def folder_of(w, walk) -> Path:
    import mode_binding as mb
    return w.root / mb.WALKS_DIR / walk


# ------------------------------------------------------------------------------------------------- R1
class R1Chain(Case):
    def test_one_walk_end_to_end(self):
        with study() as w:
            got = self.must("R1.chain", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R1.chain: {got}")
            self.assertEqual(tbi.git(w.root, "log", "-1", "--format=%s"), w.mod.WALK_SUBJECT, "R1.chain")
            reg = json.loads((w.root / "rehearsals" / "register.json").read_text())
            self.assertEqual([(e["walk"], e["reason"], e["counted"]) for e in reg["walks"]],
                             [("w-0001", "synthetic: walk w-0001 of the tests", False)], "R1.chain")
            folder = folder_of(w, "w-0001")
            for name in ("driver-ledger.json", "check.json", "grade.json", "transcript.jsonl"):
                self.assertTrue((folder / name).is_file(), f"R1.chain: no {name}")
            led = json.loads((folder / "driver-ledger.json").read_text())
            self.assertEqual((led["session_id"], led["row"], led["row_commit"]), (walk_sid("w-0001"), None, None),
                             "R1.chain: the walk's identity")
            self.assertTrue(json.loads((folder / "grade.json").read_text())["graded"], "R1.chain")
            self.assertIs(json.loads((folder / "check.json").read_text()).get("checked"), True, "R1.chain")
            self.assertFalse((w.root / "takes").exists(), "R1.chain: something was written under takes/")
            self.assertEqual(register_check(w), ([], 1), "R1.chain")
            self.assertEqual(MODS["run"].walk_problems(base=w.root, grade=stand_in_grade), ([], 1), "R1.chain")
            self.assertEqual(tbi.git(w.root, "status", "--porcelain"), "", "R1.chain")
            self.assertEqual(list(w.cfg_parent.iterdir()), [], "R1.chain: the config folder was left behind")


# ------------------------------------------------------------------------------------------------- R2
class R2WalkCheck(Case):
    def test_a_walk_is_read_as_a_walk(self):
        with study() as w:
            got = self.must("R2.walk-check", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R2.walk-check: {got}")
            folder = folder_of(w, "w-0001")
            check = json.loads((folder / "check.json").read_text())
            self.assertEqual(check["checker_reasons"], [], f"R2.walk-check: {check}")
            # the same transcript read as another walk's is refused by the session binding
            ct = MODS["check_take"]
            design = w.design_for(w.row, str(w.tree))
            other = self.must("R2.walk-check", ct.check_walk, folder / "transcript.jsonl", w.row["task"],
                              w.row["half"], "w-0002", wording_script=design.script, design=design)
            self.assertTrue(any(p.startswith("[session-binding]") for p in other), f"R2.walk-check: {other}")
            mine = self.must("R2.walk-check", ct.check_walk, folder / "transcript.jsonl", w.row["task"],
                             w.row["half"], "w-0001", wording_script=design.script, design=design)
            self.assertFalse(any(p.startswith("[session-binding]") for p in mine), f"R2.walk-check: {mine}")
            # each binding on its own: a copy whose ledger names w-0002's session, read as w-0002 (only the
            # transcript's session disagrees) and as w-0001 (only the ledger's does)
            copy = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-copy"
            shutil.copytree(folder, copy)
            led = json.loads((copy / "driver-ledger.json").read_text())
            (copy / "driver-ledger.json").write_text(json.dumps(dict(led, session_id=walk_sid("w-0002"))))
            for walk_id, says in (("w-0002", "[session-binding] the session id does not match its walk"),
                                  ("w-0001", "[session-binding] the driver ledger records session")):
                got = self.must("R2.walk-check", ct.check_walk, copy / "transcript.jsonl", w.row["task"],
                                w.row["half"], walk_id, wording_script=design.script, design=design)
                binding = [p for p in got if p.startswith("[session-binding]")]
                self.assertEqual([p.startswith(says) for p in binding], [True], f"R2.walk-check {walk_id}: {binding}")

    def test_a_take_identity_is_refused_at_launch(self):
        with study(take_identity=True) as w:
            got = self.must("R2.walk-check", w.run_walks, [w.walk("w-0001"), w.walk("w-0002")])
            self.assertEqual([g.get("state") for g in got], ["launch-refused", "launch-refused"],
                             f"R2.walk-check: {got}")
            self.assertIn("identity", got[0].get("why", ""), "R2.walk-check")
            self.assertEqual(sorted(p.name for p in (w.root / "rehearsals").iterdir()), ["README.md", "register.json"],
                             "R2.walk-check: a refused walk made its folder")
            self.assertEqual(w.spy.calls, [], "R2.walk-check: preflight was reached")


    def test_a_walk_identity_with_a_row_is_refused(self):
        """W10-R1-1: the walk's own session id with a ledger row, or with a row commit, each refused alone."""
        for over in ({"row": 0}, {"row_commit": "c" * 40}):
            with study(identity_over=over) as w:
                got = self.must("R2.walk-check", w.run_walks, [w.walk("w-0001")])
                self.assertEqual([g.get("state") for g in got], ["launch-refused"], f"R2.walk-check {over}: {got}")
                self.assertIn("identity", got[0].get("why", ""), f"R2.walk-check {over}")
                self.assertEqual(w.spy.calls, [], f"R2.walk-check {over}: preflight was reached")


# ------------------------------------------------------------------------------------------------- R3
class R3DeadWalk(Case):
    def test_a_walk_that_dies_before_turn_one_is_committed_with_its_reason(self):
        with study() as w:
            w.spy.result = tbi.preflight_record(False)
            got = self.must("R3.dead-walk", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R3.dead-walk: {got}")
            folder = folder_of(w, "w-0001")
            self.assertFalse((folder / "driver-ledger.json").exists(), "R3.dead-walk")
            grade = json.loads((folder / "grade.json").read_text())
            self.assertFalse(grade["graded"], "R3.dead-walk")
            self.assertTrue(grade["why"].startswith("not graded, because"), f"R3.dead-walk: {grade}")
            self.assertIn("preflight", grade["why"], "R3.dead-walk")
            self.assertTrue((folder / "check.json").is_file(), "R3.dead-walk")
            self.assertIs(json.loads((folder / "check.json").read_text()).get("checked"), False,
                          "R3.dead-walk: check.json passes an empty reading off as a clean one")
            self.assertEqual(register_check(w), ([], 1), "R3.dead-walk")
            self.assertEqual(MODS["run"].walk_problems(base=w.root, grade=stand_in_grade), ([], 1), "R3.dead-walk")
            self.assertEqual(len(MODS["walk_register"].registered(w.root / "rehearsals")), 1, "R3.dead-walk")
            self.assertEqual(MODS["mode_binding"].attempts(True, w.root), [], "R3.dead-walk")
            self.assertEqual(MODS["fixture_walk"].registered_walks(w.root), [], "R3.dead-walk")
            self.assertEqual(list(w.cfg_parent.iterdir()), [], "R3.dead-walk: the config folder was left behind")
            # check.json is required: without it the content rule breaks
            (folder / "check.json").rename(w.root / "aside.json")
            problems, _ = register_check(w)
            self.assertFalse(problems, "R3.dead-walk: check() itself is not the content rule")
            try:
                w.mod.walk_files(folder)
                self.fail("R3.dead-walk: a walk folder without check.json passes the closed map")
            except w.mod.DriveRefused as e:
                self.assertIn("check.json", str(e), "R3.dead-walk")
            rule = MODS["walk_register"].content_problems(w.root / "rehearsals", ["w-0001"])
            self.assertTrue(rule and "check.json" in rule[0], f"R3.dead-walk: {rule}")


# ------------------------------------------------------------------------------------------------- R4
class R4Held(Case):
    def test_a_postflight_refusal_is_never_committed(self):
        with study() as w:
            bad = {"ok": False, "checks": [{"id": "no-credential-file", "ok": False,
                                            "detail": "credential-like files present: ['synthetic']"}],
                   "recorded": {"listing": [], "credential_files": []}}
            with mock.patch.object(w.mod._preflight, "postflight", lambda cfg, harness: bad):
                got = self.must("R4.held", w.run_walks, [w.walk("w-0001"), w.walk("w-0002")])
            self.assertEqual([g.get("state") for g in got], ["held"], f"R4.held: {got}")
            self.assertIn("postflight", got[0].get("why", ""), "R4.held")
            self.assertTrue(folder_of(w, "w-0001").is_dir(), "R4.held: the walk folder was not kept")
            self.assertFalse(folder_of(w, "w-0002").exists(), "R4.held: the runner did not stop")
            self.assertEqual(json.loads((w.root / "rehearsals" / "register.json").read_text())["walks"], [],
                             "R4.held")
            self.assertTrue(register_check(w)[0], "R4.held: the register check is not red")
            self.assertEqual(len(list(w.cfg_parent.iterdir())), 1, "R4.held: the config folder was not kept")

    def test_a_scan_refusal_is_never_committed(self):
        with study() as w:
            w.driver.rules_scanner = lambda paths: [{"path": paths[0], "line": 1, "rule": "synthetic-rule"}]
            got = self.must("R4.held", w.run_walks, [w.walk("w-0001"), w.walk("w-0002")])
            self.assertEqual([g.get("state") for g in got], ["held"], f"R4.held: {got}")
            self.assertIn("scan", got[0].get("why", ""), "R4.held")
            self.assertTrue(folder_of(w, "w-0001").is_dir(), "R4.held")
            self.assertFalse(folder_of(w, "w-0002").exists(), "R4.held")
            self.assertEqual(tbi.git(w.root, "log", "-1", "--format=%s"), "A synthetic study skeleton", "R4.held")
            self.assertEqual(list(w.cfg_parent.iterdir()), [], "R4.held: the config folder was left behind")


    def test_a_refused_slot_leaves_a_kept_config_folder_alone(self):
        """W10-R1-2: the reviewer's probe. w-0001 is held with its config folder kept; a w-0002 refused before
        launch because its slot names w-0001 leaves that kept folder in place."""
        with study() as w:
            bad = {"ok": False, "checks": [{"id": "no-credential-file", "ok": False, "detail": "synthetic"}],
                   "recorded": {"listing": [], "credential_files": []}}
            with mock.patch.object(w.mod._preflight, "postflight", lambda cfg, harness: bad):
                got = self.must("R4.held", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["held"], f"R4.held: {got}")
            self.assertEqual(len(list(w.cfg_parent.iterdir())), 1, "R4.held")
            got = self.must("R4.held", w.run_walks, [w.walk("w-0002", slot="w-0001")])
            self.assertEqual([(g.get("state"), g.get("config")) for g in got], [("launch-refused", None)],
                             f"R4.held: {got}")
            self.assertEqual(len(list(w.cfg_parent.iterdir())), 1,
                             "R4.held: a walk refused before launch deleted another walk's kept config folder")

    def test_a_failed_teardown_write_still_keeps_the_config_folder(self):
        """W10-R1-2: the keep is keyed on postflight.json, not on teardown.json, whose write failure is recorded,
        never raised."""
        with study() as w:
            bad = {"ok": False, "checks": [{"id": "no-credential-file", "ok": False, "detail": "synthetic"}],
                   "recorded": {"listing": [], "credential_files": []}}
            write = w.driver._write

            def no_teardown(take, name, doc):
                if name == "teardown.json":
                    raise OSError("synthetic: the teardown record could not be written")
                return write(take, name, doc)
            w.driver._write = no_teardown
            with mock.patch.object(w.mod._preflight, "postflight", lambda cfg, harness: bad):
                got = self.must("R4.held", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["held"], f"R4.held: {got}")
            folder = folder_of(w, "w-0001")
            self.assertFalse((folder / "teardown.json").exists(), "R4.held: the teardown write did not fail")
            self.assertTrue((folder / "postflight.json").is_file(), "R4.held")
            self.assertEqual(len(list(w.cfg_parent.iterdir())), 1, "R4.held: the config folder was not kept")


# ------------------------------------------------------------------------------------------------- R5
def top_names(source: str) -> set:
    names = set()
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


class R5Round3(Case):
    def test_round_3_walks_are_untouched(self):
        self.assertIsNotNone(BASE_CHECK_TAKE, f"R5.round3: git cannot show {BASE}'s check_take.py")
        now = SOURCES.get("check_take") or (HERE / "check_take.py").read_text()
        cut = BASE_CHECK_TAKE.rindex("\nif __name__")
        self.assertTrue(now.startswith(BASE_CHECK_TAKE[:cut]), "R5.round3: the base's bytes are not a prefix")
        self.assertTrue(now.endswith(BASE_CHECK_TAKE[cut:]), "R5.round3: the __main__ block moved")
        added = now[cut:len(now) - (len(BASE_CHECK_TAKE) - cut)]
        shadow = top_names(added) & top_names(BASE_CHECK_TAKE[:cut])
        self.assertEqual(shadow, set(), f"R5.round3: appended names shadow the base's {sorted(shadow)}")
        # the same transcript read as a round-3 walk by the base module and by this one
        with study() as w:
            got = self.must("R5.round3", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R5.round3: {got}")
            path = folder_of(w, "w-0001") / "transcript.jsonl"
            base = compile_module("check_take_base_r5", BASE_CHECK_TAKE)
            sys.modules.pop("check_take_base_r5", None)
            outs = []
            for mod in (base, MODS["check_take"]):
                design = mod.design_view(w.row, pin=w.pin_for(w.row), run_tree=str(w.tree), constants=w.constants)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    problems = self.must("R5.round3", mod.check, path, w.row["task"], w.row["half"], None, True,
                                         wording_script=design.script, design=design)
                outs.append((problems, buf.getvalue()))
            self.assertEqual(outs[0], outs[1], "R5.round3: a round-3 walk reads differently")


# ------------------------------------------------------------------------------------------------- R6, R7
class R6Cli(Case):
    def test_the_cli_refuses(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = self.must("R6.cli", lambda: MODS["walk_runner"].main([]))
        self.assertEqual(code, 2, "R6.cli")
        self.assertIn("Q-w7b-3", err.getvalue(), "R6.cli")


class R7Slot(Case):
    def test_the_slot_is_the_walk_id(self):
        with study() as w:
            got = self.must("R7.slot", w.run_walks, [w.walk("w-0001", slot="s1")])
            self.assertEqual([g.get("state") for g in got], ["launch-refused"], f"R7.slot: {got}")
            self.assertIn("slot", got[0].get("why", ""), "R7.slot")
            self.assertEqual(sorted(p.name for p in (w.root / "rehearsals").iterdir()), ["README.md", "register.json"],
                             "R7.slot")
            self.assertEqual(w.spy.calls, [], "R7.slot")


# ------------------------------------------------------------------------------------------------- R8
def edit_json(path: Path, **changes) -> None:
    path.write_text(json.dumps(dict(json.loads(path.read_text()), **changes), indent=2) + "\n")


def edit_transcript(path: Path, fn) -> int:
    """Each transcript record through fn (record -> record); returns how many fn changed."""
    out, n = [], 0
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        new = fn(json.loads(line))
        n += new != rec
        out.append(json.dumps(new))
    path.write_text("\n".join(out) + "\n")
    return n


def attachment(kind, change):
    def fn(rec):
        att = rec.get("attachment") if rec.get("type") == "attachment" else None
        if isinstance(att, dict) and att.get("type") == kind:
            change(att)
        return rec
    return fn


def rebind_environment(folder: Path) -> None:
    """The driver ledger rebound to environment.json's new bytes, so a changed environment record is the one
    change (never also a ledger that no longer binds it)."""
    import hashlib
    led = folder / "driver-ledger.json"
    sha = hashlib.sha256((folder / "environment.json").read_bytes()).hexdigest()
    edit_json(led, environment=dict(json.loads(led.read_text())["environment"], sha256=sha))


class R8WalkRoad(Case):
    """D1's walk road, one binding at a time (W10-R1-1): a clean committed walk's folder is copied, ONE fact is
    changed (where another record cross-binds it, that record is forged to agree, so only the bound guard can see the
    change), and check_take.check4_walk (the module the drive imports, a witness included) reads the copy. The
    problems it adds over the clean copy are exactly the bound guard's lines."""
    stack = None

    @classmethod
    def setUpClass(cls):
        cls.stack = contextlib.ExitStack()
        cls.w = w = cls.stack.enter_context(study())
        got = w.run_walks([w.walk("w-0001")]) if hasattr(MODS["walk_runner"], "run_walks") else [{}]
        cls.ran = got
        cls.folder = folder_of(w, "w-0001")

    @classmethod
    def tearDownClass(cls):
        cls.stack.close()

    def read(self, folder: Path, walk="w-0001", arm=None) -> list:
        w = self.w
        design = w.design_for(w.row, str(w.tree))
        got = self.must("R8.walk-road", MODS["check_take"].check4_walk, folder / "transcript.jsonl", w.row["task"],
                        w.row["half"], walk, wording_script=design.script, arm=arm or w.row["arm"], design=design)
        return got["problems"]

    def copy(self) -> Path:
        self.assertEqual([g.get("state") for g in self.ran], ["committed"], f"R8.walk-road: {self.ran}")
        dst = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-0001"
        shutil.copytree(self.folder, dst)
        return dst

    def one_change(self, folder: Path, says: str, walk="w-0001"):
        base = self.read(self.copy(), walk)
        got = self.read(folder, walk)
        added = [p for p in got if p not in base]
        self.assertTrue(added, f"R8.walk-road: nothing caught ({says!r}); problems {got}")
        self.assertTrue(all(p.startswith(says) for p in added),
                        f"R8.walk-road: the change raised other lines than {says!r}: {added}")

    def test_the_clean_walk_reads_clean(self):
        self.assertEqual(self.read(self.copy()), [], "R8.walk-road: the clean walk is not clean")

    def test_the_row_needed_line_is_asserted(self):
        ct = MODS["check_take"]
        real = "[leak-in-operator-turn] synthetic: a real problem standing where the row-needed line was"
        design = self.w.design_for(self.w.row, str(self.w.tree))
        path = self.copy() / "transcript.jsonl"
        with mock.patch.object(ct, "check", lambda *a, **k: [real]):
            with self.assertRaises(ct.CheckRefused, msg="R8.walk-road: a stripped real problem passed"):
                ct.check_walk(path, self.w.row["task"], self.w.row["half"], "w-0001", wording_script=design.script,
                              design=design)

    def test_the_ledger_cell(self):
        f = self.copy()
        other = "normal" if self.w.row["half"] == "trap" else "trap"
        edit_json(f / "driver-ledger.json", half=other)
        edit_json(f / "environment.json", half=other)          # the forged ledger's own record agrees with it
        rebind_environment(f)
        self.one_change(f, "[session-binding] the driver ledger is ")

    def test_the_ledger_row(self):
        f = self.copy()
        edit_json(f / "driver-ledger.json", row=0)
        self.one_change(f, "[session-binding] the driver ledger records a ledger row")

    def test_the_ledger_row_commit(self):
        f = self.copy()
        edit_json(f / "driver-ledger.json", row_commit="c" * 40)
        self.one_change(f, "[session-binding] the driver ledger records a ledger row")

    def test_the_environment_record(self):
        f = self.copy()
        edit_json(f / "environment.json", written_before_first_turn=False)
        rebind_environment(f)
        self.one_change(f, "[environment-record] environment.json does not record that it was written before")

    def test_the_environment_row(self):
        f = self.copy()
        edit_json(f / "environment.json", row=0)
        rebind_environment(f)
        self.one_change(f, "[environment-record] the environment record names a ledger row")

    def test_the_environment_row_commit(self):
        f = self.copy()
        edit_json(f / "environment.json", row_commit="c" * 40)
        rebind_environment(f)
        self.one_change(f, "[environment-record] the environment record names a ledger row")

    def test_the_model(self):
        f = self.copy()
        edit_json(f / "driver-ledger.json", model_requested="claude-synthetic-other-model")
        edit_json(f / "environment.json", model_requested="claude-synthetic-other-model")
        rebind_environment(f)
        self.one_change(f, "[model-binding] ")

    def test_no_model(self):
        f = self.copy()
        led = json.loads((f / "driver-ledger.json").read_text())
        led.pop("model_requested")
        (f / "driver-ledger.json").write_text(json.dumps(led, indent=2) + "\n")
        edit_json(f / "environment.json", model_requested=None)
        rebind_environment(f)
        self.one_change(f, "[session-binding] the driver ledger names no model")

    def test_the_constants(self):
        f = self.copy()
        edit_json(f / "driver-ledger.json", budget_s=1)
        self.one_change(f, "[constant-binding] the take ran with a 1s turn budget")

    def test_the_checkout(self):
        f = self.copy()
        n = edit_transcript(f / "transcript.jsonl", attachment("session_context", lambda a: a["context"].update(
            gitStatus=a["context"]["gitStatus"].replace("(clean)", "M synthetic.txt"))))
        self.assertEqual(n, 1, "R8.walk-road")
        self.one_change(f, "[checkout-binding] the session's git status is not the driver's checkout")

    def test_the_instructions(self):
        f = self.copy()
        n = edit_transcript(f / "transcript.jsonl", attachment("instructions", lambda a: a["files"][0].update(
            content=a["files"][0]["content"] + "\nSynthetic: a line the pinned tree does not carry.")))
        self.assertEqual(n, 1, "R8.walk-road")
        self.one_change(f, "[checkout-binding] the session loaded ")

    def test_the_permission_mode(self):
        f = self.copy()
        n = edit_transcript(f / "transcript.jsonl",
                            lambda r: dict(r, permissionMode="default") if r.get("type") == "user" else r)
        self.assertTrue(n, "R8.walk-road")
        self.one_change(f, "[constant-binding] the session recorded permission mode(s)")

    def test_the_design_tree(self):
        f = self.copy()
        tree = str(self.w.tree)
        n = edit_transcript(f / "transcript.jsonl", attachment("environment", lambda a: a["snapshot"].update(
            workingDirectory="/synthetic/elsewhere")))
        n += edit_transcript(f / "transcript.jsonl", attachment("instructions", lambda a: [
            x.update(path=x["path"].replace(tree, "/synthetic/elsewhere", 1)) for x in a["files"]]))
        self.assertEqual(n, 2, "R8.walk-road")
        self.one_change(f, "[readers-disagree] the driver gave the take the run tree")

    def test_the_arm(self):
        f = self.copy()
        edit_json(f / "driver-ledger.json", arm="C")
        got = [p for p in self.read(f) if p not in self.read(self.copy())]
        self.assertTrue(any(p.startswith("[constant-binding] the walk's driver ledger records arm") for p in got),
                        f"R8.walk-road: {got}")

    def test_the_design_tree_through_the_drive(self):
        """The machinery (W10-R1-1, root cause 1): the check_take the drive imports is this module's MODS entry, a
        witness included, and a walk driven through the drive in another tree than its own is read by the walk road
        as readers-disagree, in its check.json."""
        import sys as _sys
        self.assertIs(_sys.modules.get("check_take"), MODS["check_take"],
                      "R8.walk-road: the drive would import another check_take than the one under test")
        with study(opened_in="/synthetic/elsewhere") as w:
            got = self.must("R8.walk-road", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R8.walk-road: {got}")
            check = json.loads((folder_of(w, "w-0001") / "check.json").read_text())
            self.assertIn("readers-disagree", check["checker_reasons"], f"R8.walk-road: {check}")


# ------------------------------------------------------------------------------------------------- R9
class R9RealGrade(Case):
    def test_the_real_grader_reads_a_fake_walk(self):
        """Q-w10-1: the fake sidecar watches the half's planted paths, and the REAL v4 grader grades the walk end to
        end; run.py's regrade (the real grader again) gives grade.json's bytes."""
        with study(watch_planted=True) as w:
            with tbi.spying(w.spy):
                got = self.must("R9.real-grade", MODS["walk_runner"].run_walks, w.driver, w.repo, [w.walk("w-0001")],
                                table=w.table)
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R9.real-grade: {got}")
            grade = json.loads((folder_of(w, "w-0001") / "grade.json").read_text())
            self.assertTrue(grade["graded"], "R9.real-grade")
            self.assertEqual(grade["grade"].get("graded_by"), f"graders/{w.row['task'].replace('-', '_')}.py",
                             f"R9.real-grade: {grade}")
            self.assertIn(grade["grade"].get("label"), ("misanswered", "declined", "complied", "answered"),
                          f"R9.real-grade: {grade}")
            self.assertEqual(MODS["run"].walk_problems(base=w.root), ([], 1), "R9.real-grade")


class TestSysPath(unittest.TestCase):
    def test_the_module_puts_sys_path_back(self):
        """Binding W6M1 (tests/test_wave6_bindings.py) for this module: it imports check_take.py through drive.py and
        test_walk_wiring, so its tearDownModule must leave sys.path exactly as it found it (test_round4 runs every
        module in one process); the wave 6 probe, in a fresh interpreter."""
        import test_wave6_bindings as w6
        with mock.patch.object(subprocess, "run", tbi._REAL["run"]), \
                mock.patch.object(subprocess, "Popen", tbi._REAL["Popen"]):   # the probe's one fresh interpreter
            seen = w6.probe("test_walk_runner")
        self.assertNotIn(str(w6.EVALS), [x for x in seen["after"] if x not in seen["before"]], "W6M1.evals-left")
        self.assertEqual(seen["after"], seen["before"], "W6M1.restored")


BOUND = {"R1.chain": "R1Chain.test_one_walk_end_to_end",
         "R2.walk-check": "R2WalkCheck",
         "R3.dead-walk": "R3DeadWalk.test_a_walk_that_dies_before_turn_one_is_committed_with_its_reason",
         "R4.held": "R4Held",
         "R5.round3": "R5Round3.test_round_3_walks_are_untouched",
         "R6.cli": "R6Cli.test_the_cli_refuses",
         "R7.slot": "R7Slot.test_the_slot_is_the_walk_id",
         "R8.walk-road": "R8WalkRoad",
         "R9.real-grade": "R9RealGrade.test_the_real_grader_reads_a_fake_walk"}
# R2's and R4's witnesses each name the one method they turn red
METHOD = {"walk-checked-as-take": "R2WalkCheck.test_a_walk_is_read_as_a_walk",
          "walk-session-unbound": "R2WalkCheck.test_a_walk_is_read_as_a_walk",
          "walk-ledger-session-unbound": "R2WalkCheck.test_a_walk_is_read_as_a_walk",
          "walk-identity-unchecked": "R2WalkCheck.test_a_take_identity_is_refused_at_launch",
          "launch-refused-stops": "R2WalkCheck.test_a_take_identity_is_refused_at_launch",
          "held-committed": "R4Held.test_a_postflight_refusal_is_never_committed",
          "held-continues": "R4Held.test_a_postflight_refusal_is_never_committed",
          "postflight-config-deleted": "R4Held.test_a_postflight_refusal_is_never_committed",
          "keep-keyed-on-teardown": "R4Held.test_a_failed_teardown_write_still_keeps_the_config_folder",
          "published-before-launch": "R4Held.test_a_refused_slot_leaves_a_kept_config_folder_alone",
          "walk-identity-row-admitted": "R2WalkCheck.test_a_walk_identity_with_a_row_is_refused",
          "walk-identity-row-commit-admitted": "R2WalkCheck.test_a_walk_identity_with_a_row_is_refused",
          "walk-row-needed-unasserted": "R8WalkRoad.test_the_row_needed_line_is_asserted",
          "walk-ledger-cell-unbound": "R8WalkRoad.test_the_ledger_cell",
          "walk-ledger-row-unbound": "R8WalkRoad.test_the_ledger_row",
          "walk-ledger-row-commit-unbound": "R8WalkRoad.test_the_ledger_row_commit",
          "walk-environment-unread": "R8WalkRoad.test_the_environment_record",
          "walk-environment-row-unbound": "R8WalkRoad.test_the_environment_row",
          "walk-environment-row-commit-unbound": "R8WalkRoad.test_the_environment_row_commit",
          "walk-model-unbound": "R8WalkRoad.test_the_model",
          "walk-model-missing-admitted": "R8WalkRoad.test_no_model",
          "walk-constants-unread": "R8WalkRoad.test_the_constants",
          "walk-checkout-unread": "R8WalkRoad.test_the_checkout",
          "walk-instructions-unread": "R8WalkRoad.test_the_instructions",
          "walk-mode-unread": "R8WalkRoad.test_the_permission_mode",
          "walk-tree-unchecked": "R8WalkRoad.test_the_design_tree",
          "walk-tree-unchecked-through-drive": "R8WalkRoad.test_the_design_tree_through_the_drive",
          "walk-arm-unbound": "R8WalkRoad.test_the_arm"}
WITNESSES = {name: (METHOD.get(name, BOUND[clause]), clause) for name, (clause, _, _, _) in mutants().items()}


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=110)
        record = re.findall(r"^test_walk_runner outcomes: (\{.*\})$", got.stdout, re.M)
        outcome = json.loads(record[-1]) if record else None
        blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", got.stderr,
                            re.M | re.S)
        attributed = any(f"{cls}.{test}" == method and "AssertionError" in body and
                         re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w.-])", body)
                         for test, cls, body in blocks)
        clean = bool(outcome) and outcome["failures"] == [method] and outcome["errors"] == [] \
            and outcome["skipped"] == []
        passed = attributed and clean and got.returncode != 0
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}", flush=True)
        if not passed:
            print(got.stdout[-3000:] + got.stderr[-3000:], flush=True)
            return 1
        red += 1
    print(f"test_walk_runner witnesses: {red}/{len(chosen)} red; registry {len(WITNESSES)}", flush=True)
    return 0


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses(sys.argv[sys.argv.index("--witnesses") + 1:]))
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        if SELECTED not in WITNESSES:
            raise SystemExit(f"unknown mutant {SELECTED!r}")
        del sys.argv[index:index + 2]
    result = unittest.main(verbosity=2, exit=False).result
    ids = lambda pairs: [t.id().removeprefix("__main__.").split(" ")[0] for t, _ in pairs]  # noqa: E731
    print(f"test_walk_runner: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_walk_runner outcomes: " + json.dumps({"failures": ids(result.failures), "errors": ids(result.errors),
                                                     "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
