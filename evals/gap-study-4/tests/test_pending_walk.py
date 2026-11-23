#!/usr/bin/env python3
"""The acceptance-walk road (registration review finding 2): a Gemini walk driven by the real WalkDriver and the real
GeminiAdapter on a fake box, stopped by its pending native cross-check, committed ungraded by the real walk runner and
WalkRepo, then registered and regraded from its committed bytes.

Fakes only, in a throwaway scratch repository under test_box_integration's SCRATCH (its process guard admits only
`git -C <scratch>`): no model, container, network, credential or study-tree write. The fake box answers the Gemini
execs with streams and a growing native session file written by these tests; a wrapper around run_take.run_turn writes
each turn's launch journal in the box's schema (the box lane's run_turn writes it on the merged head). The fixture is
UNMARKED on purpose (glitch-06's order: a gate nothing can pass proves nothing); its label says it is a test fixture
without the marker word the registration gate refuses, and it lives only in the scratch folder.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_box_integration as tbi  # noqa: E402
from box import run_take as rt  # noqa: E402

UNMARKED = "TEST-ONLY FIXTURE in a scratch repository (never acceptance evidence)"
MODEL = "gemini-3.8-flash"
SID = "1a2b3c4d-0000-4000-8000-00000000abcd"
VERSION = "0.64.0"
WALK = "walk-g1"
LOGIN = "GEMINI_API_KEY"
LOGIN_VALUE = "synthetic-login-value-" + "0123456789abcdef"     # a planted fake, never a real key
TS = "2026-10-14T00:00:00.000Z"


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


def jl(records):
    return "".join(json.dumps(r) + "\n" for r in records)


def tool_call(cid):
    return {"id": cid, "name": "read_file", "args": {"file_path": "notes.txt"}, "status": "success",
            "resultDisplay": "display text",
            "result": [{"functionResponse": {"id": cid, "name": "read_file", "response": {"output": "x"}}}]}


def native(turns, summary=UNMARKED) -> bytes:
    recs = [{"sessionId": SID, "projectHash": "project-1", "summary": summary}]
    for k in range(1, turns + 1):
        recs += [{"id": f"u{k}", "type": "user", "content": [{"text": f"sent {k}"}]},
                 {"id": f"a{k}", "type": "gemini", "model": MODEL, "content": "I'll read it.",
                  "toolCalls": [tool_call(f"call-{k}")]},
                 {"id": f"rt{k}", "type": "user", "content": [
                     {"functionResponse": {"id": f"call-{k}", "name": "read_file", "response": {"output": "x"}}}]},
                 {"id": f"b{k}", "type": "gemini", "model": MODEL, "content": "Done."}]
    return jl(recs).encode()


STATS = {"total_tokens": 3, "input_tokens": 2, "output_tokens": 1, "cached": 0, "input": 2, "duration_ms": 5,
         "tool_calls": 1, "models": {MODEL: {"total_tokens": 3, "input_tokens": 2, "output_tokens": 1, "cached": 0,
                                             "input": 2}}}


def stream(k) -> str:
    ev = lambda t, **kw: dict({"type": t, "timestamp": TS}, **kw)  # noqa: E731
    return jl([ev("init", session_id=SID, model=MODEL), ev("message", role="user", content=f"sent {k}"),
               ev("message", role="assistant", content="I'll read it.", delta=True),
               ev("tool_use", tool_name="read_file", tool_id=f"call-{k}", parameters={"file_path": "notes.txt"}),
               ev("tool_result", tool_id=f"call-{k}", status="success", output="display text"),
               ev("message", role="assistant", content="Done.", delta=True),
               ev("result", status="success", stats=STATS)])


class GeminiBox(tbi.FakeBox):
    """FakeBox that also answers `gemini --version` and a Gemini turn: the turn's stream, and the session file the
    resumed session grows under the take's config folder (GEMINI_CLI_HOME), one interaction per turn."""

    def __init__(self, *a, summary=UNMARKED, **kw):
        super().__init__(*a, **kw)
        self.turn_n, self.summary = 0, summary

    def run(self, argv, env=None, timeout=None):
        a = list(argv)
        if a[:2] == ["docker", "exec"] and "gemini" in a:
            self.calls.append(a)
            if a[-1] == "--version":
                return rt.Completed(0, VERSION + "\n", "")
            take = [x for x in a if self.containers.get(x, {}).get("kind") == "take"][0]
            cfg = [m for m in self.specs[take] if m.startswith("type=bind,source=")
                   and m.endswith("target=" + rt.CONFIG_MOUNT)][0]
            cfg = cfg[len("type=bind,source="):-len(",target=" + rt.CONFIG_MOUNT)]
            self.turn_n += 1
            chats = Path(cfg) / ".gemini" / "tmp" / "project-1" / "chats"
            with tbi.FakeBox.as_container(cfg):          # the agent writes its own config folder (the P4 road)
                chats.mkdir(parents=True, exist_ok=True)
                (chats / f"session-2026-10-14T05-00-{SID[:8]}.jsonl").write_bytes(native(self.turn_n, self.summary))
            return rt.Completed(0, stream(self.turn_n), "")
        return super().run(argv, env=env, timeout=timeout)


def journaling(real):
    """run_take.run_turn plus the box's per-turn launch journal (<stream>.launch.json), in its schema."""
    def run_turn(runtime, take_id, inner, *, harness, run_tree, login_file, stream_path, budget_s, clock,
                 caller_env=None, config_folder=None, turn=None):
        got = real(runtime, take_id, inner, harness=harness, run_tree=run_tree, login_file=login_file,
                   stream_path=stream_path, budget_s=budget_s, clock=clock, caller_env=caller_env,
                   config_folder=config_folder, turn=turn)
        Path(stream_path + ".launch.json").write_text(json.dumps(
            {"schema": 1, "harness": harness, "container_id": take_id, "argv": list(inner), "cwd": run_tree,
             "stream": stream_path, "started_at": got["started_at"]}))
        return got
    return run_turn


def git(root, *args):
    return tbi.git(root, *args)


def account_record_patch(walk_builders):
    """Round 10 ruling 2 (glitch-b5, Sat 17 Oct 2026; the T4 plan's section 9): every codex and gemini take refuses
    before launch without the account record, so a vendor walk here runs on a TEST DATA one (clearly fake .invalid
    addresses) under the scratch folder: a patch, not started, of walk_builders.account_emails_path to it."""
    import test_walk_builders as twb
    f = twb.account_record_file(Path(tempfile.mkdtemp(dir=tbi.SCRATCH, prefix="accounts-")))
    return mock.patch.object(walk_builders, "account_emails_path", lambda: str(f))


class Road:
    """One scratch study (the reader's sources, the draft and tasks, an empty register) and one Gemini walk through
    the real road: WalkDriver(records="walks") with harness_adapter_for, walk_runner.run_walks, WalkRepo."""

    def __init__(self, test, *, summary=UNMARKED, reason=UNMARKED, turns=2, fail_rm=(), harness="gemini", box=None,
                 run_turn=None, row=None, lease=None):
        import drive
        import native_reader_registration as nrr
        import walk_register
        self.test, self.drive, self.nrr, self.reason, self.harness = test, drive, nrr, reason, harness
        cm = tbi.scratch_repo()
        self.root = cm.__enter__()
        test.addCleanup(cm.__exit__, None, None, None)
        # A vendor's billing-route list is stubbed empty only while it is still PENDING on this tree; where the box
        # has filled it (Gemini: bea73659 / 3a0d7f5a; Codex: 9d4bfd40) the real list is checked (the Gemini walk wiring).
        routes = dict(rt.VENDOR_BILLING_ROUTE_VARIABLES)
        routes.update({h: () for h in (rt.CODEX, rt.GEMINI) if routes.get(h) == rt.PENDING})
        self.config_checks: list = []      # B11's per-turn check, recorded: its own tests are test_config_folder's
        for name, value in (("VENDOR_BILLING_ROUTE_VARIABLES", routes),
                            ("run_turn", journaling(run_turn or rt.run_turn)),
                            ("check_config_folder", lambda folder, **kw: self.config_checks.append((folder, kw)))):
            patch = mock.patch.object(rt, name, value)
            patch.start()
            test.addCleanup(patch.stop)
        import takes
        import uuid
        patch = mock.patch.object(takes, "namespace", lambda: uuid.UUID("00000000-0000-4000-8000-0000000000aa"))
        patch.start()                     # tbi's prereg stand-in names no session namespace; a fixed one for the walk
        test.addCleanup(patch.stop)
        self.study = self.root / "study"
        (self.study / "rehearsals").mkdir(parents=True)
        for name in sorted(set(nrr.READER_SOURCES) | set(nrr.CODEX_SOURCES)):     # every profile's sources
            shutil.copyfile(HERE / name, self.study / name)
        shutil.copyfile(HERE / "prereg-draft.json", self.study / "prereg-draft.json")
        shutil.copytree(HERE / "tasks", self.study / "tasks")
        (self.study / "rehearsals" / "README.md").write_text(UNMARKED + "\n")
        (self.study / "rehearsals" / "register.json").write_text('{\n  "schema": 1,\n  "walks": []\n}\n')
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "A study skeleton")
        design = walk_register.design_in_force(self.study)
        task = sorted(design["tasks"])[0]
        self.row = {"walk": WALK, "slot": WALK, "task": task, "half": design["tasks"][task]["halves"][0],
                    "wording": design["tasks"][task]["wordings"][0], "arm": "G", "model": MODEL,
                    "agent": {"harness": "gemini", "version": VERSION}, "pressure": None, "repeat": 1,
                    "half_cell": "c1"}
        self.row.update(row or {})
        self.rig = tbi.Rig(drive, self.root, box=box or GeminiBox(summary=summary, fail_rm=fail_rm))
        login = tbi.SCRATCH / f"login-{self.root.name}"
        login.write_text(f"{LOGIN}={LOGIN_VALUE}\n")
        os.chmod(login, 0o600)
        self.login = login
        r = self.rig
        self.driver = drive.WalkDriver(
            records_root=self.study, records="walks", runtime=r.box,
            take_folder=drive.record_folder_in(self.study, "walks"), config_parent=str(r.cfg_parent),
            spec_for=r.spec_for, sidecar_for=r.sidecar_for, proxy=rt.ProxyLaunch(
                image="sha256:" + "9" * 64, conf_source=str(tbi.SCRATCH / "proxy.conf"),
                conf_target="/etc/squid/x.conf", command=("squid", "-N"), user="13:13", alias="proxy"),
            lock_path=str(tbi.SCRATCH / "synthetic.lock"), hosts={"api": "synthetic.invalid"},
            adapter_for=drive.harness_adapter_for(runtime=r.box, login_file=str(login),
                                                  counters_for=lambda take: {"oom_kill": 0, "pids_max": 0},
                                                  pin_for=self.pin_for, clock=r.clock,
                                                  config_view=lambda take: self.driver.config_view(take),
                                                  config_folder=lambda take, lease: self.driver.config_folder(take,
                                                                                                             lease)),
            script_for=lambda row: [{"n": k, "line": f"sent {k}"} for k in range(1, turns + 1)],
            pin_for=self.pin_for, checker=self.never_checked, secrets=lambda: [("token", tbi.TOKEN)],
            rules_scanner=lambda paths: [], uid_map=tbi.UID_MAP, budget_s=600, finalize_wait_s=tbi.CAP_S,
            poll_s=tbi.POLL_S, clock=r.clock, sleep=r.clock.sleep, project_for=lambda row: tbi.PROJECT,
            identity_for=self.identity_for, ownership=r.ownership,
            settings_guard=r.settings_guard, machine_gate=r.machine_gate)
        self.repo = drive.WalkRepo(runtime=r.box, secrets=lambda: [("token", tbi.TOKEN)],
                                   rules_scanner=lambda paths: [], root=self.study, repo=self.root, design=design)
        self.lease = None
        from box import preflight
        if harness == "codex" and (lease or (lease is None and hasattr(preflight, "LEASE_CREDENTIAL"))):
            self._lease_road()

    def _lease_road(self):
        """A Codex walk on the lease road (walk_builders.CodexLeaseRoad): the lease placed in the driver's spec_for and
        its values in the driver's and WalkRepo's secrets. Where the box's lease postflight is on the tree it holds a
        Codex walk whose lease home lacks auth.json, so every Codex road walk there places one. The gate is opened for
        the test; the box's place_lease and lease_secrets are used where this tree has them, faked by their contract
        (test_walk_builders.lease_boundary's fakes) only where it does not."""
        import test_walk_builders as twb
        import walk_builders
        placed, reads = [], []
        patches = [mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", True, create=True)]
        if not callable(getattr(rt, "place_lease", None)):
            patches.append(mock.patch.object(rt, "place_lease", twb.fake_place_lease(placed), create=True))
        if not callable(getattr(walk_builders, "lease_secrets", None)):
            patches.append(mock.patch.object(walk_builders, "lease_secrets", twb.fake_lease_secrets(reads),
                                             create=True))
        patches.append(account_record_patch(walk_builders))     # round 10 ruling 2: a TEST DATA account record
        for patch in patches:
            patch.start()
            self.test.addCleanup(patch.stop)
        home = tbi.SCRATCH / f"lease-{self.root.name}"
        home.mkdir(mode=0o700)
        self.lease = walk_builders.CodexLeaseRoad(str(twb.lease_file(home)), walk_s=twb.RIG_WALK_S,
                                                  clock=time.time)
        spec_for, login = self.driver.spec_for, self.driver.secrets
        self.driver.spec_for = lambda row, cfg: (self.lease.place(cfg), spec_for(row, cfg))[1]
        self.driver.secrets = self.repo.secrets = lambda: list(login()) + list(self.lease.secrets())

    @staticmethod
    def pin_for(row):
        if row["agent"]["harness"] == "codex":
            return {"permission_mode": "bypass", "version": row["agent"]["version"], "model": row["model"],
                    "harness": "codex"}
        return {"permission_mode": "yolo", "version": VERSION, "model": row["model"], "harness": "gemini"}

    def never_checked(self, row, take, turns):
        raise AssertionError("the checker ran on a take whose native cross-check is pending")

    def identity_for(self, row):
        import check_take
        return {"session_id": check_take.walk_session_id(row["walk"]), "row": None, "row_commit": None,
                "source": "/synthetic/source", "fixture": {"sha256": "0" * 64},
                "gars_tree_sha": "8a54e0f8cd91caf558d0d168f1b87e36d0bc0b74"}

    def walk(self):
        import walk_runner
        with tbi.spying(self.rig.spy):
            return walk_runner.run_walks(self.driver, self.repo, [{"row": dict(self.row), "reason": self.reason}])

    @property
    def folder(self) -> Path:
        return self.study / "rehearsals" / WALK

    def accept(self, *, reviewer="a-fresh-reviewer", accepted_by="javier", review=UNMARKED, edit=None):
        """The review and Javier's acceptance record, each committed (the record as his own window would)."""
        nrr, h = self.nrr, self.harness
        prof = nrr.PROFILES[h]
        (self.study / nrr.READER_DIR).mkdir(exist_ok=True)
        (self.study / nrr.READER_DIR / f"{h}-review.md").write_text(f"# {review}\nVerdict: PASS\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "an independent review")
        ledger = json.loads((self.folder / "driver-ledger.json").read_text())
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
        last = ledger["native_snapshots"][-1]
        record = {"schema": 1, "harness": h, "cli_version": prof["cli"],
                  "reader_sources_sha256": nrr.reader_sources_sha256(self.study, sources=prof["sources"]), "walk": WALK,
                  "native": {"file": "session/" + last["file"], "sha256": last["sha256"]},
                  "streams": [{"file": s, "sha256": sha(self.folder / s)} for s in ledger["streams"]],
                  "join": {"status": "PASS", "interactions": len(ledger["streams"])},
                  "review": {"verdict": "PASS", "file": f"{h}-review.md",
                             "sha256": sha(self.study / nrr.READER_DIR / f"{h}-review.md"), "reviewer": reviewer},
                  "accepted_by": accepted_by}
        if edit:
            edit(record)
        self.commit_record(record)
        return record

    def commit_record(self, record, msg="acceptance"):
        (self.study / self.nrr.PROFILES[self.harness]["acceptance"]).write_text(json.dumps(record))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", msg)

    def refused(self) -> str:
        with self.test.assertRaises(self.nrr.RegistrationRefused) as cm:
            self.nrr.production_readers(self.study)
        return str(cm.exception)


def stand_in_grade(row, folder):
    return {"label": "stand-in-label", "views": {"strict": "right"}, "graded_by": "graders/stand_in.py"}


class PendingWalk(unittest.TestCase):
    def test_walk_driver_builds_each_harness_adapter(self):
        import drive
        import gemini_adapter
        import inspect
        src = inspect.getsource(drive.walk_driver)
        self.assertIn("adapter_for=harness_adapter_for(", src)
        self.assertNotIn("adapter_for=claude_code_adapter_for(", src)
        road = Road(self)
        got = road.walk()
        self.assertEqual([g["state"] for g in got], ["pending-native-reader"], got)
        turns = [c for c in road.rig.box.calls if c[:2] == ["docker", "exec"] and "gemini" in c and "-p" in c]
        self.assertEqual(len(turns), 2, "the production GeminiAdapter ran both turns through the box")
        self.assertEqual(gemini_adapter.GeminiAdapter, drive.PRODUCTION_ADAPTERS["gemini"][0])

    def test_a_pending_gemini_walk_is_committed_ungraded_and_regrades_to_its_bytes(self):
        import pending_walk
        import run
        import walk_register
        road = Road(self)
        got = road.walk()
        self.assertEqual(got[0]["state"], "pending-native-reader", got)
        self.assertFalse(got[0]["graded"])
        self.assertEqual(git(road.root, "log", "-1", "--format=%s"), road.drive.WALK_SUBJECT)
        self.assertEqual(got[0]["commit"], git(road.root, "rev-parse", "HEAD"))
        ledger = json.loads((road.folder / "driver-ledger.json").read_text())
        self.assertEqual(ledger["cross_check_status"]["status"], "pending")
        grade = json.loads((road.folder / "grade.json").read_text())
        self.assertEqual(grade, pending_walk.status(ledger))
        self.assertEqual((grade["graded"], grade["status"]), (False, "pending-native-reader"))
        check = json.loads((road.folder / "check.json").read_text())
        self.assertEqual(check, {"walk": WALK, "status": "pending-native-reader",
                                 "why": ledger["cross_check_status"]["why"]})
        for k in (1, 2):
            self.assertTrue((road.folder / f"turn-{k}.jsonl.launch.json").is_file())
            self.assertTrue((road.folder / "session" / f"native-turn-{k}.jsonl").is_file())
        # B11 (lane vendor-b11 round 3, R-CF): each turn reached run_take's config folder check with the take's record
        # from the driver's ownership road (TakeDriver.config_folder) and its number
        checks = [(kw["harness"], kw["turn"], folder.get("harness"), folder.get("model"), folder.get("lease"),
                   folder.get("uid_map")) for folder, kw in road.config_checks]
        self.assertEqual(checks, [("gemini", k, "gemini", MODEL, None, tbi.UID_MAP)
                                  for k in (1, 2)])
        self.assertEqual(walk_register.check(road.study / "rehearsals", walk_register.design_in_force(road.study))[0],
                         [])
        self.assertEqual(run.walk_problems(road.study)[0], [])
        self.assertEqual(git(road.root, "status", "--porcelain", "--", "study/rehearsals"), "")

    def test_a_pending_walk_whose_container_stays_is_held(self):
        road = Road(self)

        def remove(cid):
            raise RuntimeError("synthetic: the container could not be removed")
        road.driver.remove = remove
        got = road.walk()
        self.assertEqual(got[0]["state"], "held", got)
        self.assertIn("NativeCrossCheckPending", got[0]["why"])
        self.assertEqual(git(road.root, "log", "-1", "--format=%s"), "A study skeleton")


class RegistrationThroughTheRoad(unittest.TestCase):
    def setUp(self):
        self.road = Road(self)
        got = self.road.walk()
        self.assertEqual(got[0]["state"], "pending-native-reader", got)

    def test_it_registers_and_prints_the_commits(self):
        road, nrr = self.road, self.road.nrr
        road.accept()
        self.assertEqual(nrr.production_readers(road.study), {"gemini": nrr.gemini_reader})
        prov = nrr.acceptance_provenance(road.study)
        self.assertEqual(prov["acceptance_commit"], git(road.root, "rev-parse", "HEAD"))
        self.assertEqual(prov["walk_commit"], git(road.root, "rev-parse", "HEAD~2"))
        self.assertTrue(prov["walk_author"] and prov["walk_committer"])

    def test_each_single_mutation_unregisters(self):
        road = self.road
        road.accept()
        self.assertEqual(set(road.nrr.production_readers(road.study)), {"gemini"})
        (road.folder / "turn-1.jsonl").write_text(stream(1) + "\n")
        self.assertIn("differs from the committed tree", road.refused())

    def test_a_marked_session_refuses_last(self):
        road = Road(self, summary="a synthetic session")
        self.assertEqual(road.walk()[0]["state"], "pending-native-reader")
        road.accept()
        self.assertIn("synthetic marker", road.refused())

    def test_other_single_mutations(self):
        nrr = self.road.nrr
        cases = {
            "acceptor": lambda r: r.accept(accepted_by="glitch-06"),
            "reviewer and the acceptor": lambda r: r.accept(reviewer="javier"),
            "synthetic marker": lambda r: r.accept(review="a synthetic review"),
            "not the last one the walk's driver ledger names": lambda r: r.accept(edit=lambda rec: rec.__setitem__(
                "native", {"file": "session/native-turn-1.jsonl", "sha256": hashlib.sha256(
                    (r.folder / "session" / "native-turn-1.jsonl").read_bytes()).hexdigest()})),
            "reader's sources changed": lambda r: (r.accept(), _edit_source(r)),
        }
        for why, mutate in cases.items():
            with self.subTest(why=why):
                road = self.road if why == "acceptor" else Road(self)
                if road is not self.road:
                    self.assertEqual(road.walk()[0]["state"], "pending-native-reader")
                mutate(road)
                self.assertIn(why, road.refused())
        del nrr


def _edit_source(road):
    with open(road.study / "gemini_projection.py", "a") as fh:
        fh.write("# edited\n")
    git(road.root, "commit", "-q", "-am", "edit a source")


def walked(test, **kw) -> Road:
    road = Road(test, **kw)
    got = road.walk()
    test.assertEqual(got[0]["state"], "pending-native-reader", got)
    return road


class Gates(unittest.TestCase):
    """Each registration gate refuses for its own reason, on a walk made by the real road (the hand-built fixtures of
    fd4177e0 moved here: a hand-built walk now stops at the finding-1 gates first)."""

    def test_each_gate_refuses_for_its_own_reason(self):
        import native_reader_registration as nrr
        cases = {
            "uncommitted": lambda r: ((r.study / nrr.READER_DIR).mkdir(),
                                      (r.study / nrr.ACCEPTANCE_FILE).write_text("{}")),
            "differs from the committed tree": lambda r: (r.accept(), (r.folder / "turn-1.jsonl").write_text("x\n")),
            "asserted": lambda r: r.accept(edit=lambda rec: rec.__setitem__("evidence_label", "recorded-walk")),
            "reader's sources changed": lambda r: r.accept(edit=lambda rec: rec.__setitem__(
                "reader_sources_sha256", "1" * 64)),
            "driver ledger names": lambda r: r.accept(edit=lambda rec: rec.__setitem__("native", {
                "file": "session/native-turn-1.jsonl",
                "sha256": hashlib.sha256((r.folder / "session" / "native-turn-1.jsonl").read_bytes()).hexdigest()})),
            "streams the driver ledger names": lambda r: r.accept(edit=lambda rec: rec.__setitem__(
                "streams", rec["streams"][:1])),
            "native hash": lambda r: r.accept(edit=lambda rec: rec["native"].__setitem__("sha256", "0" * 64)),
            "review hash": lambda r: r.accept(edit=lambda rec: rec["review"].__setitem__("sha256", "0" * 64)),
            "join does not re-derive": lambda r: r.accept(edit=lambda rec: rec["join"].__setitem__("interactions", 3)),
            "arm-G walk": lambda r: r.accept(edit=lambda rec: rec.__setitem__("walk", "another-walk")),
            "is not a regrade commit": lambda r: (r.accept(), (r.folder / "check.json").write_text("{}\n"),
                                                  git(r.root, "commit", "-q", "-am", "a later hand edit")),
        }
        for why, mutate in cases.items():
            with self.subTest(why=why):
                road = walked(self)
                mutate(road)
                self.assertIn(why, road.refused())

    def test_the_coverage_floor(self):
        road = walked(self, turns=1)
        road.accept()
        self.assertIn("at least 2 interactions", road.refused())

    def test_synthetic_markers_anywhere_refuse_last(self):
        for kw, review in (({"summary": "a synthetic session"}, UNMARKED), ({"reason": "a synthetic walk"}, UNMARKED),
                           ({}, "a synthetic review")):
            with self.subTest(kw=kw, review=review):
                road = walked(self, **kw)
                road.accept(review=review)
                self.assertIn("synthetic marker", road.refused())

    def test_the_tool_prints_pass_with_the_shapes_on_the_walks_files(self):
        import io
        from contextlib import redirect_stdout
        import native_reader_registration as nrr
        road = walked(self)
        out = io.StringIO()
        with redirect_stdout(out), mock.patch.object(nrr, "_head", lambda: "(the scratch run's HEAD is not read)"):
            code = nrr.main(["check", "--native", str(road.folder / "session" / "native-turn-2.jsonl"),
                             "--stream", str(road.folder / "turn-1.jsonl"), "--stream", str(road.folder / "turn-2.jsonl")])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("acceptance floor met", out.getvalue())


def fabricate(test, change, *, extra=None, subject=None):
    """The reviewer's attack A1/A3: a second walk folder made by hand from the road's own bytes, one thing changed,
    committed by hand (under WalkRepo's subject unless `subject`), and an acceptance record naming it."""
    road = walked(test)
    src = road.folder
    dst = road.study / "rehearsals" / "walk-g2"
    shutil.copytree(src, dst)
    check = json.loads((dst / "check.json").read_text())         # the honest copy first: its own walk id
    (dst / "check.json").write_text(json.dumps(dict(check, walk="walk-g2"), indent=2, sort_keys=True) + "\n")
    change(dst)
    reg = road.study / "rehearsals" / "register.json"
    doc = json.loads(reg.read_text())
    doc["walks"].append(dict(doc["walks"][0], walk="walk-g2"))
    reg.write_text(json.dumps(doc, indent=2) + "\n")
    if extra:
        extra(road)
    git(road.root, "add", "-A")
    git(road.root, "commit", "-q", "-m", subject or road.drive.WALK_SUBJECT)
    road.accept(edit=lambda rec: rec.__setitem__("walk", "walk-g2"))
    return road


class FabricatedWalks(unittest.TestCase):
    """Each fabrication starts from the road's own bytes and changes one thing, so each refusal is its own."""

    def fabricate(self, change, *, extra=None, subject=None):
        return fabricate(self, change, extra=extra, subject=subject)

    def test_an_honest_copy_committed_by_hand_is_still_refused_only_by_what_differs(self):
        road = self.fabricate(lambda d: None, subject="a hand commit")
        self.assertIn("not a WalkRepo commit", road.refused())

    def test_a_walk_missing_its_grade_fails_walk_files(self):
        road = self.fabricate(lambda d: (d / "grade.json").unlink())
        self.assertIn("walk_files", road.refused())

    def test_each_fabrication_refuses(self):
        def ledger_edit(fn):
            def change(dst):
                L = json.loads((dst / "driver-ledger.json").read_text())
                fn(L)
                (dst / "driver-ledger.json").write_text(json.dumps(L, indent=2))
            return change

        def journal_field(k, key, value):
            def change(dst):
                j = json.loads((dst / f"turn-{k}.jsonl.launch.json").read_text())
                if key == "cwd":
                    j["argv"] = list(j["argv"])
                j[key] = value
                (dst / f"turn-{k}.jsonl.launch.json").write_text(json.dumps(j))
            return change

        def journal_edit(dst):
            j = json.loads((dst / "turn-2.jsonl.launch.json").read_text())
            j["argv"] = [a.replace("sent 2", "sent two") for a in j["argv"]]
            (dst / "turn-2.jsonl.launch.json").write_text(json.dumps(j))

        cases = {
            "check.json is not the walk runner's pending check record":
                lambda d: (d / "check.json").write_text("{}\n"),
            "grade.json is not run.grade_walk's pending document": lambda d: (d / "grade.json").write_text("{}\n"),
            "not the take schema": ledger_edit(lambda L: L.pop("cost")),
            "environment.json does not re-hash": lambda d: (d / "environment.json").write_text("{}\n"),
            "launch journal fails launch_facts": journal_edit,
            "agent": ledger_edit(lambda L: L.__setitem__("agent", {"harness": "gemini", "version": "0.63.0"})),
            "records no pending native cross-check": ledger_edit(lambda L: L.__setitem__(
                "cross_check_status", {"status": "agreed", "why": None})),
            "share one working folder": journal_field(2, "cwd", "/elsewhere"),
            "names another stream": journal_field(2, "stream", "/elsewhere/turn-9.jsonl"),
        }
        for why, change in cases.items():
            with self.subTest(why=why):
                road = self.fabricate(change)
                self.assertIn(why, road.refused())

    def test_a_walk_commit_that_rewrites_another_register_entry_refuses(self):
        def extra(road):
            reg = road.study / "rehearsals" / "register.json"
            doc = json.loads(reg.read_text())
            doc["walks"][0]["reason"] = UNMARKED + " (rewritten)"
            reg.write_text(json.dumps(doc, indent=2) + "\n")
        road = self.fabricate(lambda d: None, extra=extra)
        self.assertIn("exactly this entry appended", road.refused())

    def test_a_walk_commit_with_another_file_refuses(self):
        road = self.fabricate(lambda d: None, extra=lambda r: (r.study / "stray.txt").write_text("x\n"))
        self.assertIn("does not add exactly", road.refused())


class CoverageOfASecondPendingWalk(unittest.TestCase):
    """Batch-8 fix review finding 1 (the reviewer's witness_survivors): the acceptance walk is walk-g2, and walk-g1 is a
    second, non-acceptance pending walk, so the registration gate never reads walk-g1's regrade. Its coverage standing
    comes from _regrade_state alone: a hand-made regrade that does not re-derive leaves it pending, and an honest
    regrade whose cross-check refused leaves it uncounted as "regrade refused"."""

    def setUp(self):
        import run
        self.road = fabricate(self, lambda d: None)                       # walk-g2 accepted, walk-g1 still pending
        patch = mock.patch.object(run, "grade_walk_folder", stand_in_grade)
        patch.start()
        self.addCleanup(patch.stop)
        self.assertEqual(set(self.road.nrr.production_readers(self.road.study)), {"gemini"})

    def test_a_hand_made_regrade_on_another_pending_walk_stays_pending(self):
        import pending_walk
        (self.road.folder / "regrade.json").write_text('{"graded": true, "hand": "made"}\n')
        self.assertEqual(pending_walk.uncounted_walks(self.road.study / "rehearsals", [WALK]), {WALK: "pending"})

    def test_an_honest_refused_regrade_stays_uncounted(self):
        import drive
        import pending_walk
        import walk_regrade
        refused = lambda *a, **k: {"status": "refused", "why": "a stand-in refusal"}   # noqa: E731
        with mock.patch.object(drive, "gemini_cross_check", refused):
            doc = walk_regrade.regrade_doc(WALK, self.road.study)
            self.assertEqual((doc["cross_check"]["status"], doc["graded"]), ("refused", False))
            (self.road.folder / "regrade.json").write_bytes(walk_regrade.regrade_bytes(doc))
            self.assertEqual(pending_walk.uncounted_walks(self.road.study / "rehearsals", [WALK]),
                             {WALK: "regrade refused"})


class FixtureWalkCoverage(unittest.TestCase):
    """Batch-8 fix ruling item 3: fixture_walk.walk_coverage never counts a pending walk, even one holding a
    transcript (the road writes none today; this binds it rather than relying on that)."""

    def test_a_pending_walk_is_never_counted_there(self):
        road = walked(self)
        import fixture_walk               # after the walk: it puts round 3's evals/ on sys.path, ahead of check_take
        (road.folder / "transcript.jsonl").write_text("{}\n")
        task = road.row["task"]
        need = {task: {"walks_needed": 1, "one_walk_covers_both_halves": True}}   # tbi's prereg stand-in names no tasks
        patch = mock.patch.object(fixture_walk, "half_equivalence", lambda: need)
        patch.start()
        self.addCleanup(patch.stop)
        self.assertEqual(fixture_walk.walk_coverage(road.study)[task]["walks_committed"], 0)
        import walk_regrade
        import drive
        refused = lambda *a, **k: {"status": "refused", "why": "a stand-in refusal"}   # noqa: E731
        with mock.patch.object(drive, "gemini_cross_check", refused):
            doc = walk_regrade.regrade_doc(WALK, road.study, readers={"gemini": road.nrr.gemini_reader})
            (road.folder / "regrade.json").write_bytes(walk_regrade.regrade_bytes(doc))
            with mock.patch.object(road.nrr, "production_readers", lambda study=None: {"gemini": road.nrr.gemini_reader}):
                self.assertEqual(fixture_walk.walk_coverage(road.study)[task]["walks_committed"], 0,
                                 "a walk whose verified regrade refused is not counted either")
        (road.folder / "regrade.json").unlink()
        grade = road.folder / "grade.json"
        grade.write_text(json.dumps({"graded": True, "row": {}, "grade": {}}))
        # BOOTSTRAP B5 (15 Oct 2026): a graded walk counts only with a checked check.json under the constants in force.
        # Moved by lane vendor-admission T4 P5 (plan v4 section 6; glitch-b5 round 13): this gemini walk's constants in
        # force are the merged ones (its ledger's harness), so the Claude-only digest reads it stale
        import check_take
        (road.folder / "check.json").write_text(json.dumps({"walk": WALK, "checked": True, "checker_reasons": [],
                                                            "events": {"outside_reach": 0}, "route": "graded", "route_refused": None,
                                                            "checker_constants_sha256":
                                                                check_take.vendor_checker_constants_sha256("gemini"),
                                                            "no_output_nudges": 0,     # review r6 MINOR 2
                                                            "agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0}, "nested_cli_calls": 0}))   # Agent parity, part 6
        self.assertEqual(fixture_walk.walk_coverage(road.study)[task]["walks_committed"], 1, "the control counts")


class Regrade(unittest.TestCase):
    def test_only_a_pending_walk_is_regraded(self):
        import walk_regrade
        road = fabricate(self, lambda d: (d / "grade.json").write_text('{"graded": true}\n'))
        with self.assertRaises(walk_regrade.RegradeRefused) as cm:
            walk_regrade.regrade_doc("walk-g2", road.study, readers={"gemini": road.nrr.gemini_reader},
                                     grade=stand_in_grade)
        self.assertIn("not a pending walk", str(cm.exception))

    def test_a_registered_reader_regrades_the_committed_walk(self):
        import walk_regrade
        road = Road(self)
        self.assertEqual(road.walk()[0]["state"], "pending-native-reader")
        with self.assertRaises(walk_regrade.RegradeRefused):           # no reader yet: nothing to regrade with
            walk_regrade.regrade_doc(WALK, road.study, grade=stand_in_grade)
        road.accept()
        doc = walk_regrade.regrade_doc(WALK, road.study, grade=stand_in_grade)
        self.assertEqual(doc["cross_check"], {"status": "agreed", "why": None})
        self.assertTrue(doc["graded"])
        self.assertEqual(doc["grade"], stand_in_grade(None, None))
        self.assertEqual(doc["walk_commit"], git(road.root, "rev-parse", "HEAD~2"))
        walk_regrade.write_regrade(WALK, road.study, grade=stand_in_grade)
        with self.assertRaises(walk_regrade.RegradeRefused):           # written once
            walk_regrade.write_regrade(WALK, road.study, grade=stand_in_grade)
        commit = walk_regrade.commit_regrade(WALK, road.study, secrets=lambda: [("token", tbi.TOKEN)],
                                             rules_scanner=lambda paths: [])
        self.assertEqual(git(road.root, "log", "-1", "--format=%s"), walk_regrade.REGRADE_SUBJECT)
        self.assertEqual(git(road.root, "diff-tree", "-r", "--no-commit-id", "--name-only", commit),
                         "study/rehearsals/walk-g1/regrade.json")
        import run
        with mock.patch.object(run, "grade_walk_folder", stand_in_grade):     # the stand-in grader re-derives it
            self.assertEqual(set(road.nrr.production_readers(road.study)), {"gemini"})   # the regrade is admitted
        self.assertIn("regrade.json cannot be re-derived", road.refused())   # the real grader cannot grade a fake walk
        import pending_walk
        with mock.patch.object(run, "grade_walk_folder", stand_in_grade):
            self.assertEqual(walk_regrade.regrade_problems(road.study, grade=stand_in_grade), [])
            # moved by lane vendor-admission T4 P5, R-9 (plan v4 section 6 (c); glitch-b5 round 13): a verified graded
            # regrade supersedes the pending grade (batch-8 finding 1), and the walk counts only through a checker
            # reading under the constants in force (tests/test_vendor_walk_road.py R-9); it has none
            self.assertEqual(pending_walk.uncounted_walks(road.study / "rehearsals", [WALK]),
                             {WALK: pending_walk.PENDING_UNCHECKED},
                             "a verified graded regrade alone never counts the walk (R-9)")
        stored = json.loads((road.folder / "grade.json").read_text())
        self.assertEqual(stored["status"], "pending-native-reader")                  # the walk's own record stays
        refusing = {"gemini": lambda raw, n: (_ for _ in ()).throw(road.nrr.vp.ProvenanceRefused("a stand-in"))}
        doc = walk_regrade.regrade_doc(WALK, road.study, readers=refusing, grade=stand_in_grade)
        self.assertEqual((doc["cross_check"]["status"], doc["graded"]), ("refused", False))
        self.assertIn("not graded, because the native cross-check refused", doc["why"])
        path = road.folder / "regrade.json"
        path.write_text(path.read_text().replace('"graded": true', '"graded": false'))
        git(road.root, "commit", "-q", "-am", walk_regrade.REGRADE_SUBJECT)
        self.assertTrue(walk_regrade.regrade_problems(road.study, grade=stand_in_grade))
        with mock.patch.object(run, "grade_walk_folder", stand_in_grade):     # batch-8 finding 4: a hand-made
            self.assertIn("does not re-derive", road.refused())               # regrade refuses the registration
            self.assertEqual(pending_walk.uncounted_walks(road.study / "rehearsals", [WALK]), {WALK: "pending"},
                             "a regrade that does not re-derive supersedes nothing")


class KeyedGeminiBox(GeminiBox):
    """GeminiBox whose agent also writes the planted key's value into its own reply (the stream); the session carries
    it through the box's summary."""

    def run(self, argv, env=None, timeout=None):
        got = super().run(argv, env=env, timeout=timeout)
        a = list(argv)
        if a[:2] == ["docker", "exec"] and "gemini" in a and a[-1] != "--version":
            return rt.Completed(got.returncode, got.stdout.replace('"Done."', json.dumps(f"Done. {LOGIN_VALUE}")),
                                got.stderr)
        return got


class GeminiKeyMask(unittest.TestCase):
    """The Gemini walk wiring (glitch-06, 14 Oct 2026), item 2: the exact-value mask bound to the walk's key file. The
    walk's driver and its WalkRepo scan with walk_builders.login_secrets over the Gemini login file (GEMINI_API_KEY,
    the planted low-entropy LOGIN_VALUE), as walk_builders.walk_driver_for hands them. A pending Gemini walk has no
    transcript (no reviewed native reader), so the agent's text lives in its streams and its session snapshots."""

    def keyed_road(self, **kw):
        import walk_builders
        road = Road(self, box=KeyedGeminiBox(summary=f"a session naming {LOGIN_VALUE}"), **kw)
        patch = account_record_patch(walk_builders)             # round 10 ruling 2: a TEST DATA account record
        patch.start()
        self.addCleanup(patch.stop)
        road.driver.secrets = road.repo.secrets = walk_builders.login_secrets(str(road.login), rt.GEMINI)
        return road

    def committed(self, road) -> dict:
        names = git(road.root, "ls-tree", "-r", "--name-only", "HEAD", "--", "study/rehearsals/" + WALK).split()
        return {n: tbi.git_bytes(road.root, "show", f"HEAD:{n}") for n in names}

    def test_the_key_in_a_stream_or_a_session_is_masked_before_the_commit(self):
        road = self.keyed_road()
        got = road.walk()
        self.assertEqual(got[0]["state"], "pending-native-reader", got)
        self.assertNotIn(LOGIN_VALUE, json.dumps(got, default=str), "the key reached the result")
        files = self.committed(road)
        self.assertTrue(files, "nothing was committed")
        leaked = sorted(n for n, b in files.items() if LOGIN_VALUE.encode() in b)
        self.assertEqual(leaked, [], "the key reached the committed walk")
        masked = sorted(n.rsplit("/", 1)[-1] for n, b in files.items() if b"[masked: token]" in b)
        self.assertTrue(any(n.startswith("turn-") and n.endswith(".jsonl") for n in masked), masked)
        self.assertTrue(any(n.startswith("native-turn-") for n in masked), masked)

    def test_the_key_in_the_ledger_refuses_the_walk(self):
        road = self.keyed_road()
        road.driver.script_for = lambda row: [{"n": 1, "line": f"sent {LOGIN_VALUE}"}, {"n": 2, "line": "sent 2"}]
        head = git(road.root, "rev-parse", "HEAD")
        got = road.walk()
        self.assertEqual(got[0]["state"], "held", got)
        self.assertRegex(got[0]["why"], r"\(token\): a token value in a \w+ file, which cannot be masked", got)
        self.assertNotIn(LOGIN_VALUE, json.dumps(got, default=str), "the key reached the result")
        self.assertEqual(git(road.root, "rev-parse", "HEAD"), head, "a walk carrying the key was committed")


if __name__ == "__main__":
    unittest.main()
