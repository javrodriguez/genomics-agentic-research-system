#!/usr/bin/env python3
"""Codex slice 3: the arm O registration road, on the corrected pattern of the Gemini road (test_pending_walk.py).

A Codex walk driven by the real WalkDriver and the real CodexAdapter (built by harness_adapter_for, its rollout read
live from the take's config folder, CODEX_HOME) on a fake box, its turns run through the login-free stub exec of
glitch-06's Codex ruling (a), stopped by its pending native cross-check, committed ungraded by the real walk runner and
WalkRepo, then registered (native-readers/codex-acceptance.json) and regraded from its committed bytes.

Fakes only, in a throwaway scratch repository under test_box_integration's SCRATCH: no model, container, network,
credential or study-tree write. The fake box answers `codex --version` and `codex exec --json` with exec streams and
grows the rollout at <config>/sessions/<Y>/<MM>/<DD>/rollout-<YYYY-MM-DDTHH-MM-SS>-<thread>.jsonl (audit Addendum
B). The fixture is UNMARKED on purpose (a gate nothing can pass proves nothing) and lives only in the scratch folder.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_box_integration as tbi  # noqa: E402
import test_pending_walk as tpw  # noqa: E402
from box import run_take as rt  # noqa: E402

TID = "00000000-0000-7000-8000-0000000000c1"
MODEL = "gpt-6-luna"
CLI = "0.162.1"
UNMARKED = tpw.UNMARKED
USAGE = {"input_tokens": 3, "cached_input_tokens": 0, "output_tokens": 2, "reasoning_output_tokens": 0}


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


def jl(records) -> str:
    return "".join(json.dumps(r) + "\n" for r in records)


def rollout(turns: int, label: str = UNMARKED) -> bytes:
    """A paginated 0.162.1 rollout of `turns` turns (codex_native's subset and codex_adapter's reading)."""
    recs = []

    def add(type_, payload):
        recs.append({"timestamp": f"2026-10-14T05:00:{len(recs):02d}.000Z", "ordinal": len(recs), "type": type_,
                     "payload": payload})
    add("session_meta", {"session_id": TID, "id": TID, "timestamp": "2026-10-14T05:00:00.000Z", "cwd": "/work/tree",
                         "originator": "codex_exec", "cli_version": CLI, "source": "exec", "model_provider": "openai",
                         "base_instructions": {"text": label}, "history_mode": "paginated"})
    for k in range(1, turns + 1):
        tid = f"t{k}"
        add("event_msg", {"type": "task_started", "turn_id": tid, "model_context_window": None,
                          "collaboration_mode_kind": "default"})
        add("turn_context", {"turn_id": tid, "cwd": "/work/tree", "approval_policy": "never",
                             "sandbox_policy": {"type": "danger-full-access"}, "model": MODEL})
        for item in ({"type": "UserMessage", "id": f"u{k}", "content": [{"type": "text", "text": f"sent {k}",
                                                                          "text_elements": []}]},
                     {"type": "CommandExecution", "id": f"c{k}", "command": ["ls"], "cwd": "/work/tree",
                      "parsed_cmd": [], "source": "agent", "status": "completed", "aggregated_output": f"out {k}",
                      "exit_code": 0},
                     {"type": "AgentMessage", "id": f"m{k}", "content": [{"type": "Text", "text": "Done."}],
                      "phase": "final_answer"}):
            add("event_msg", {"type": "item_completed", "thread_id": TID, "turn_id": tid, "item": item,
                              "completed_at_ms": 0})
        add("event_msg", {"type": "task_complete", "turn_id": tid, "last_agent_message": "Done."})
    return jl(recs).encode()


def exec_stream(k: int) -> str:
    return jl([{"type": "thread.started", "thread_id": TID}, {"type": "turn.started"},
               {"type": "item.completed", "item": {"id": "item_0", "type": "command_execution", "command": "ls",
                                                   "aggregated_output": f"out {k}", "exit_code": 0,
                                                   "status": "completed"}},
               {"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": "Done."}},
               {"type": "turn.completed", "usage": USAGE}])


def open_rollout(turns: int) -> bytes:
    """The rollout with its last turn left open (no task_complete): a killed or cut turn."""
    lines = rollout(turns).decode().splitlines(keepends=True)
    return "".join(lines[:-1]).encode()


def open_stream(k: int) -> str:
    """The exec stream with no terminal event (an interrupted call exits 1)."""
    return "".join(exec_stream(k).splitlines(keepends=True)[:-1])


class CodexBox(tbi.FakeBox):
    """FakeBox that also answers `codex --version` and a `codex exec --json` turn, growing the rollout under the
    take's config folder (CODEX_HOME), one turn per exec."""

    def __init__(self, *a, label=UNMARKED, **kw):
        super().__init__(*a, **kw)
        self.turn_n, self.label = 0, label

    def run(self, argv, env=None, timeout=None):
        a = list(argv)
        if a[:2] == ["docker", "exec"] and "codex" in a:
            self.calls.append(a)
            if a[-1] == "--version":
                return rt.Completed(0, f"codex-cli {CLI}\n", "")
            take = [x for x in a if self.containers.get(x, {}).get("kind") == "take"][0]
            cfg = [m for m in self.specs[take] if m.startswith("type=bind,source=")
                   and m.endswith("target=" + rt.CONFIG_MOUNT)][0]
            cfg = cfg[len("type=bind,source="):-len(",target=" + rt.CONFIG_MOUNT)]
            self.turn_n += 1
            folder = Path(cfg) / "sessions" / "2026" / "10" / "14"
            with tbi.FakeBox.as_container(cfg):          # the agent writes its own config folder (the P4 road)
                folder.mkdir(parents=True, exist_ok=True)
                (folder / f"rollout-2026-10-14T05-00-00-{TID}.jsonl").write_bytes(rollout(self.turn_n, self.label))
            return rt.Completed(0, exec_stream(self.turn_n), "")
        return super().run(argv, env=env, timeout=timeout)


def codex_road(test, *, label=UNMARKED, reason=UNMARKED):
    import test_codex_adapter as tca
    road = tpw.Road(test, harness="codex", box=CodexBox(label=label), run_turn=tca.stub_run_turn, reason=reason,
                    row={"arm": "O", "model": MODEL, "agent": {"harness": "codex", "version": CLI}})
    got = road.walk()
    test.assertEqual(got[0]["state"], "pending-native-reader", got)
    return road


class CodexPendingWalk(unittest.TestCase):
    def test_a_pending_codex_walk_is_committed_with_its_rollouts(self):
        import pending_walk
        road = codex_road(self)
        ledger = json.loads((road.folder / "driver-ledger.json").read_text())
        self.assertEqual(ledger["agent"], {"harness": "codex", "version": CLI})
        self.assertEqual(ledger["cross_check_status"]["status"], "pending")
        self.assertEqual(ledger["native_history"]["status"], "pending")
        self.assertEqual([s["file"] for s in ledger["native_snapshots"]], ["native-turn-1.jsonl", "native-turn-2.jsonl"])
        self.assertEqual(ledger["served_model"], [{"value": None, "source": "unobserved"}] * 2)   # D-INT-2
        self.assertEqual(json.loads((road.folder / "grade.json").read_text()), pending_walk.status(ledger))
        for k in (1, 2):
            self.assertTrue((road.folder / f"turn-{k}.jsonl.launch.json").is_file())
        self.assertEqual(tpw.git(road.root, "log", "-1", "--format=%s"), road.drive.WALK_SUBJECT)


class TokenNamedBox(CodexBox):
    """CodexBox whose agent also makes, in its own config folder (the lease home), a folder named with the lease's
    synthetic access token: a name postflight's credential rule cannot see, carried by postflight.json's listing."""

    def run(self, argv, env=None, timeout=None):
        a = list(argv)
        if a[:2] == ["docker", "exec"] and "codex" in a and a[-1] != "--version":
            import test_walk_builders as twb
            take = [x for x in a if self.containers.get(x, {}).get("kind") == "take"][0]
            cfg = [m for m in self.specs[take] if m.startswith("type=bind,source=")
                   and m.endswith("target=" + rt.CONFIG_MOUNT)][0]
            cfg = cfg[len("type=bind,source="):-len(",target=" + rt.CONFIG_MOUNT)]
            with tbi.FakeBox.as_container(cfg):
                (Path(cfg) / twb.ACCESS).mkdir(exist_ok=True)
        return super().run(argv, env=env, timeout=timeout)


class CodexLeaseCommitScan(unittest.TestCase):
    def test_a_token_named_file_in_the_lease_home_refuses_the_commit(self):
        """NIT 5 (the box review of b9f876b5): a Codex walk on the lease road (walk_builders.CodexLeaseRoad: the lease
        placed in the driver's spec_for, its secrets() the driver's and WalkRepo's) whose lease home holds a folder
        named with the access token: drive's own scans refuse the walk for postflight.json (an exact-value token hit
        in a record that is never masked), nothing is committed, and postflight.json is left as written. The box's
        place_lease, lease_secrets and the gate are faked at the boundary (test_walk_builders.lease_boundary); where
        this tree's preflight lacks the box's LEASE_CREDENTIAL, postflight is wrapped to admit exactly auth.json,
        as the box's lease postflight does (2fd8215a)."""
        import contextlib
        import test_codex_adapter as tca
        import test_walk_builders as twb
        import walk_builders
        from box import preflight
        road = tpw.Road(self, harness="codex", box=TokenNamedBox(), run_turn=tca.stub_run_turn,
                        row={"arm": "O", "model": MODEL, "agent": {"harness": "codex", "version": CLI}})
        with contextlib.ExitStack() as stack:
            stack.enter_context(twb.lease_boundary(walk_builders))
            if not hasattr(preflight, "LEASE_CREDENTIAL"):
                real = preflight.postflight

                def postflight(config_dir, harness):
                    post = real(config_dir, harness)
                    hits = [p for p in post["recorded"]["listing"] if p != "auth.json"
                            and (Path(p).name == "auth.json" or preflight.CREDENTIAL_LIKE.search(Path(p).name))]
                    ok = not hits
                    detail = "no credential file" if ok else f"credential-like files present: {hits}"
                    return dict(post, ok=ok, checks=[dict(post["checks"][0], ok=ok, detail=detail)])
                stack.enter_context(mock.patch.object(preflight, "postflight", postflight))
            home = Path(tbi.SCRATCH) / f"lease-{road.root.name}"
            home.mkdir(mode=0o700)
            lease = walk_builders.CodexLeaseRoad(str(twb.lease_file(home)))
            spec_for = road.driver.spec_for
            road.driver.spec_for = lambda row, cfg: (lease.place(cfg), spec_for(row, cfg))[1]
            road.driver.secrets = road.repo.secrets = lease.secrets
            head = tpw.git(road.root, "rev-parse", "HEAD")
            got = road.walk()
        self.assertIsNotNone(lease.placed, "the lease was never placed")
        self.assertNotEqual(got[0]["state"], "committed", got)
        self.assertNotEqual(got[0]["state"], "pending-native-reader", got)
        self.assertEqual(tpw.git(road.root, "rev-parse", "HEAD"), head, "a walk carrying the token was committed")
        why = json.dumps(got, default=str)
        self.assertEqual(got[0]["state"], "held", got)
        self.assertRegex(got[0]["why"], r"the drive scan refused the take: \S*/postflight\.json:\d+ \(token\): a token "
                                        r"value in a preflight file, which cannot be masked", got)
        self.assertNotIn(twb.ACCESS, why, "the token reached the result")
        post = (road.folder / "postflight.json").read_bytes()
        self.assertIn(twb.ACCESS.encode(), post, "postflight.json was masked or rewritten")


class CodexRegistration(unittest.TestCase):
    def test_it_registers_and_each_single_mutation_unregisters(self):
        road = codex_road(self)
        road.accept()
        nrr = road.nrr
        self.assertEqual(nrr.production_readers(road.study), {"codex": nrr.codex_reader})
        prov = nrr.acceptance_provenance(road.study, "codex")
        self.assertEqual(prov["acceptance_commit"], tpw.git(road.root, "rev-parse", "HEAD"))
        for why, mutate in (
                ("acceptor", lambda r: r.accept(accepted_by="glitch-06")),
                ("reviewer and the acceptor", lambda r: r.accept(reviewer="javier")),
                ("synthetic marker", lambda r: r.accept(review="a synthetic review")),
                ("driver ledger names", lambda r: r.accept(edit=lambda rec: rec.__setitem__("native", {
                    "file": "session/native-turn-1.jsonl", "sha256": json.loads(
                        (r.folder / "driver-ledger.json").read_text())["native_snapshots"][0]["sha256"]}))),
                ("join does not re-derive", lambda r: r.accept(edit=lambda rec: rec["join"].__setitem__(
                    "interactions", 3))),
                ("the record is for codex", lambda r: r.accept(edit=lambda rec: rec.__setitem__("cli_version",
                                                                                                "0.64.0"))),
                ("arm-O walk", lambda r: r.accept(edit=lambda rec: rec.__setitem__("walk", "another-walk")))):
            with self.subTest(why=why):
                other = codex_road(self)
                mutate(other)
                self.assertIn(why, other.refused())

    def test_a_marked_rollout_refuses_last(self):
        road = codex_road(self, label="a synthetic session")
        road.accept()
        self.assertIn("synthetic marker", road.refused())

    def test_the_coverage_floor_and_the_shared_join(self):
        import drive
        nrr = __import__("native_reader_registration")
        good = nrr.codex_join_session(rollout(2), [exec_stream(1), exec_stream(2)], [0, 0])
        self.assertEqual((good["status"], good["shapes"]["interactions"], good["shapes"]["command_round_trips"]),
                         ("PASS", 2, 2))
        for why, args in (("2 native turns for 1 streams", (rollout(2), [exec_stream(1)], [0])),
                          ("interaction 2", (rollout(2), [exec_stream(1), exec_stream(1)], [0, 0])),
                          ("not one exit code per stream", (rollout(2), [exec_stream(1), exec_stream(2)], [0])),
                          ("interaction 2 is not complete", (open_rollout(2), [exec_stream(1), open_stream(2)], [0, 1]))):
            with self.subTest(why=why):
                got = nrr.codex_join_session(*args)
                self.assertEqual(got["status"], "DISAGREE")
                self.assertIn(why, got["why"])
        self.assertEqual(nrr.floor_problem({"interactions": 1, "command_round_trips": 1}, nrr.CODEX_FLOOR),
                         "acceptance needs at least 2 interactions; the walk exercised 1")
        self.assertEqual(drive.codex_cross_check("/nonexistent", [], [0], readers={})["status"], "pending")


def codex_fabricate(test, change):
    """A second walk folder made by hand from a Codex road walk's own bytes, one thing changed, committed by hand under
    WalkRepo's subject, and an acceptance record naming it (the reviewer's attack shape, on arm O)."""
    import shutil
    road = codex_road(test)
    dst = road.study / "rehearsals" / "walk-g2"
    shutil.copytree(road.folder, dst)
    check = json.loads((dst / "check.json").read_text())
    (dst / "check.json").write_text(json.dumps(dict(check, walk="walk-g2"), indent=2, sort_keys=True) + "\n")
    change(dst)
    reg = road.study / "rehearsals" / "register.json"
    doc = json.loads(reg.read_text())
    doc["walks"].append(dict(doc["walks"][0], walk="walk-g2"))
    reg.write_text(json.dumps(doc, indent=2) + "\n")
    tpw.git(road.root, "add", "-A")
    tpw.git(road.root, "commit", "-q", "-m", road.drive.WALK_SUBJECT)
    road.accept(edit=lambda rec: rec.__setitem__("walk", "walk-g2"))
    return road


def ledger_edit(fn):
    def change(dst):
        led = json.loads((dst / "driver-ledger.json").read_text())
        fn(led)
        (dst / "driver-ledger.json").write_text(json.dumps(led, indent=2))
    return change


class CodexProfileBindings(unittest.TestCase):
    """Codex road review F3 and F4: the profile-specific bindings, each by a single mutation."""

    def test_an_honest_copy_registers_so_each_refusal_below_is_its_own(self):
        road = codex_fabricate(self, lambda d: None)
        self.assertEqual(set(road.nrr.production_readers(road.study)), {"codex"})

    def test_each_profile_binding_refuses(self):
        def journal_thread(dst):
            j = json.loads((dst / "turn-2.jsonl.launch.json").read_text())
            j["argv"] = [("00000000-0000-7000-8000-0000000000c9" if a == TID else a) for a in j["argv"]]
            (dst / "turn-2.jsonl.launch.json").write_text(json.dumps(j))
        for why, change in (
                ("not the take schema", ledger_edit(lambda L: L.pop("served_model"))),
                ("served_model is not each turn's own stream evidence", ledger_edit(lambda L: L.__setitem__(
                    "served_model", [{"value": MODEL, "source": "stream-reroute"}] * 2))),
                ("fails launch_facts", journal_thread)):
            with self.subTest(why=why):
                self.assertIn(why, codex_fabricate(self, change).refused())

    def test_a_codex_source_edit_and_a_dirty_path_refuse(self):
        road = codex_road(self)
        road.accept()
        with open(road.study / "codex_native.py", "a") as fh:
            fh.write("# edited\n")
        tpw.git(road.root, "commit", "-q", "-am", "edit a Codex reader source")
        self.assertIn("reader's sources changed", road.refused())
        road = codex_road(self)
        road.accept()
        (road.folder / "turn-1.jsonl").write_text(exec_stream(1) + "\n")
        self.assertIn("differs from the committed tree", road.refused())


class CodexCrossCheckInTheDriver(unittest.TestCase):
    """With a Codex reader registered, the driver joins each turn's exec stream to the retained rollout through the
    one shared join: the history joins and the cross-check agrees, so the checker reads the take (never pending)."""

    def test_a_registered_reader_agrees_in_the_driver(self):
        import native_reader_registration as nrr
        import test_codex_adapter as tca
        road = tpw.Road(self, harness="codex", box=CodexBox(), run_turn=tca.stub_run_turn,
                        row={"arm": "O", "model": MODEL, "agent": {"harness": "codex", "version": CLI}})
        checked = []
        road.driver.checker = lambda row, take, turns: checked.append(len(turns)) or tbi.checker_record()
        row = dict(road.row)
        with mock.patch.object(nrr, "production_readers", lambda study=None: {"codex": nrr.codex_reader}), \
                tbi.spying(road.rig.spy):
            cid = road.driver.launch(row)
            try:
                road.driver.drive(row, cid)
            finally:
                road.driver.remove(cid)
        ledger = json.loads((road.folder / "driver-ledger.json").read_text())
        self.assertEqual(ledger["native_history"]["status"], "joined")
        self.assertEqual(ledger["cross_check_status"], {"status": "agreed", "why": None})
        self.assertEqual(ledger["cross_check"], [])
        self.assertEqual(checked, [2], "the checker read the take")


class CodexRegrade(unittest.TestCase):
    def test_a_registered_codex_reader_regrades_the_committed_walk(self):
        import run
        import walk_regrade
        road = codex_road(self)
        road.accept()
        with mock.patch.object(run, "grade_walk_folder", tpw.stand_in_grade):
            doc = walk_regrade.regrade_doc(tpw.WALK, road.study)
        self.assertEqual(doc["cross_check"], {"status": "agreed", "why": None})
        self.assertTrue(doc["graded"])


if __name__ == "__main__":
    unittest.main()
